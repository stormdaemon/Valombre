"""Shared toolkit of the VALOMBRE outfit / hair artist (Blender 5.1, headless).

Everything here works on top of the body kit made by the body artist (tools/blender/build/human.blend,
opened READ ONLY):
  * Body      : numpy copy of `body_full` + BVH trees (ray casts, nearest point, skin weight transfer).
  * Prof      : radius tables of the skin around the torso / one leg / one arm / foot / hand / head
                (garment shells are swept around those profiles with an offset = the cloth thickness).
  * Piece     : accumulates quad grids / strips with per vertex colour, per corner UV, weight rules and
                morph anchors, then becomes a skinned Blender object carrying the body morphs
                (deltas evaluated with human_morphs.MORPHS at the nearest skin point).
  * preview helpers (poses, visibility, contact sheets).
"""
import sys, os, math, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
from humanoid_rig import DEFORM_BONES, bone_table
import human_morphs as hm
from mathutils.bvhtree import BVHTree

BUILD = os.path.join(ROOT, 'tools', 'blender', 'build')
BLEND_HUMAN = os.path.join(BUILD, 'human.blend')
CHAR_DIR = os.path.join(MODELS, 'char')
NB = len(DEFORM_BONES)
BI = {n: i for i, n in enumerate(DEFORM_BONES)}
ARM_Z = 1.469
YC = 0.012
TAU = 2.0 * math.pi
REGIONS = ('body_head', 'body_torso', 'body_arms', 'body_hands', 'body_legs', 'body_feet')
SIDE = {1: 'L', -1: 'R'}
MIRX = np.array([-1.0, 1.0, 1.0])


# ----------------------------------------------------------------------------- small math
def sstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def dirxy(a):
    """horizontal direction of azimuth a: 0 = front (-Y), +90 deg = character's left (+X)."""
    a = np.asarray(a, float)
    return np.stack([np.sin(a), -np.cos(a), np.zeros_like(a)], -1)


def diryz(b):
    """direction around the arm axis: 0 = up (+Z), +90 deg = front (-Y)."""
    b = np.asarray(b, float)
    return np.stack([np.zeros_like(b), -np.sin(b), np.cos(b)], -1)


def dirxz(c):
    """direction around the foot axis: 0 = up (+Z), +90 deg = +X."""
    c = np.asarray(c, float)
    return np.stack([np.sin(c), np.zeros_like(c), np.cos(c)], -1)


def angles(n, phase=0.0):
    return (np.arange(n) + phase) * TAU / n


def vnoise(P, scale=0.05, seed=0):
    """smooth value noise in [0, 1] (vectorised, deterministic)."""
    q = np.asarray(P, float) / scale + 1000.0
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3.0 - 2.0 * f)

    def h(ix, iy, iz):
        n = ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144269
        n = (n ^ (n >> 13)) * 1274126177
        n = n ^ (n >> 16)
        return (n & 0xffff) / 65535.0

    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * h(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz)
    return out


def col(c):
    return np.array(lin(c) if isinstance(c, str) else c, float)


def mottle(P, base, amount=0.12, scale=0.06, seed=0):
    """base colour with value noise variation (worn cloth / leather)."""
    n = vnoise(P, scale, seed) * 0.65 + vnoise(P, scale * 0.37, seed + 7) * 0.35
    return np.asarray(base, float) * (1.0 - amount + 2.0 * amount * n)[..., None]


def gauss_blur_rows(R, sig):
    """blur a (stations, angles) table along the stations (sig in stations)."""
    if sig <= 0:
        return R.copy()
    k = int(math.ceil(3 * sig))
    x = np.arange(-k, k + 1)
    w = np.exp(-(x / sig) ** 2 / 2)
    w /= w.sum()
    pad = np.concatenate([np.repeat(R[:1], k, 0), R, np.repeat(R[-1:], k, 0)], 0)
    out = np.zeros_like(R)
    for j, wj in enumerate(w):
        out += wj * pad[j:j + len(R)]
    return out


def hull_polar(r, A):
    """radius of the convex hull of the polar curve r(A) (NaN = missing) seen from the origin."""
    ok = ~np.isnan(r)
    if ok.sum() < 3:
        return np.where(ok, r, 0.004)
    pts = np.stack([r[ok] * np.sin(A[ok]), -r[ok] * np.cos(A[ok])], 1)
    P = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in P:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in P[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    H = np.array(lower[:-1] + upper[:-1])
    out = np.zeros(len(A))
    E1, E2 = H, np.roll(H, -1, 0)
    ex, ey = (E2 - E1)[:, 0], (E2 - E1)[:, 1]
    for k, a in enumerate(A):
        dx, dy = math.sin(a), -math.cos(a)
        det = -dx * ey + dy * ex
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)
        t = (-E1[:, 0] * ey + E1[:, 1] * ex) / det
        s = (dx * E1[:, 1] - dy * E1[:, 0]) / det
        m = (t > 0) & (s >= -1e-6) & (s <= 1 + 1e-6)
        out[k] = t[m].max() if m.any() else np.nan
    if np.isnan(out).any():
        good = ~np.isnan(out)
        if good.sum() >= 2:
            out = np.interp(A, A[good], out[good], period=TAU)
        else:
            out = np.where(ok, r, 0.004)
    return out


# ----------------------------------------------------------------------------- the body
class Body:
    def __init__(self):
        ob = bpy.data.objects['body_full']
        me = ob.data
        n = len(me.vertices)
        P = np.empty(n * 3, np.float32)
        me.shape_keys.key_blocks['Basis'].data.foreach_get('co', P)
        self.P = P.reshape(n, 3).astype(np.float64)
        me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        T = np.empty(nt * 3, np.int32)
        me.loop_triangles.foreach_get('vertices', T)
        self.T = T.reshape(nt, 3)
        a, b, c = self.P[self.T[:, 0]], self.P[self.T[:, 1]], self.P[self.T[:, 2]]
        fn = np.cross(b - a, c - a)
        N = np.zeros_like(self.P)
        for k in range(3):
            np.add.at(N, self.T[:, k], fn)
        self.N = unit(N)
        self.TC = (a + b + c) / 3.0
        names = [g.name for g in ob.vertex_groups]
        W = np.zeros((n, NB))
        for v in me.vertices:
            for g in v.groups:
                W[v.index, BI[names[g.group]]] = g.weight
        self.W = W / np.maximum(W.sum(1, keepdims=True), 1e-9)
        self._trees = {}

    def mask(self, src):
        c = self.TC
        ax = np.abs(c[:, 0])
        if src == 'all':
            return np.ones(len(c), bool)
        if src == 'trunk':                  # torso + hips + neck, no arms
            return (ax < 0.232) & (c[:, 2] > 0.80) & (c[:, 2] < 1.60)
        if src == 'body':                   # everything but arms and head (skirts, capes)
            return (ax < 0.232) & (c[:, 2] < 1.56)
        if src in ('arm_L', 'arm_R'):
            s = 1.0 if src.endswith('L') else -1.0
            return (c[:, 0] * s > 0.15) & (c[:, 2] > 1.36)
        if src in ('hand_L', 'hand_R'):
            s = 1.0 if src.endswith('L') else -1.0
            return (c[:, 0] * s > 0.66)
        if src in ('leg_L', 'leg_R'):
            s = 1.0 if src.endswith('L') else -1.0
            return (c[:, 0] * s > -0.004) & (c[:, 2] < 1.03)
        if src == 'legs':
            return c[:, 2] < 1.03
        if src == 'head':
            return (c[:, 2] > 1.47) & (ax < 0.14)
        if src == 'skull':                  # head without the neck / shoulders
            return (c[:, 2] > 1.56) & (ax < 0.14)
        if src == 'upper':                  # torso above the waist + head, no arms (hair, capes, hoods)
            return (ax < 0.232) & (c[:, 2] > 1.05)
        raise KeyError(src)

    def tree(self, src='all'):
        if src not in self._trees:
            idx = np.where(self.mask(src))[0]
            self._trees[src] = (BVHTree.FromPolygons(self.P.tolist(), self.T[idx].tolist()), idx)
        return self._trees[src]

    def nearest(self, pts, src='all'):
        tree, idx = self.tree(src)
        pts = np.asarray(pts, float).reshape(-1, 3)
        Q = np.empty((len(pts), 3))
        TI = np.empty(len(pts), np.int64)
        for i, p in enumerate(pts):
            co, nrm, k, d = tree.find_nearest(Vector(p))
            Q[i] = co
            TI[i] = idx[k]
        return Q, TI

    def bary(self, Q, TI):
        tri = self.T[TI]
        a, b, c = self.P[tri[:, 0]], self.P[tri[:, 1]], self.P[tri[:, 2]]
        v0, v1, v2 = b - a, c - a, Q - a
        d00 = (v0 * v0).sum(1)
        d01 = (v0 * v1).sum(1)
        d11 = (v1 * v1).sum(1)
        d20 = (v2 * v0).sum(1)
        d21 = (v2 * v1).sum(1)
        den = np.maximum(d00 * d11 - d01 * d01, 1e-18)
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        bw = np.clip(np.stack([1 - v - w, v, w], 1), 0, 1)
        return bw / bw.sum(1, keepdims=True)

    def transfer(self, pts, src='all'):
        """skin weights, nearest skin point and smooth skin normal for arbitrary points."""
        Q, TI = self.nearest(pts, src)
        bw = self.bary(Q, TI)
        tri = self.T[TI]
        W = (self.W[tri] * bw[:, :, None]).sum(1)
        Nq = unit((self.N[tri] * bw[:, :, None]).sum(1))
        return W, Q, Nq

    def sdist(self, pts, src='all'):
        """signed distance to the skin (positive outside), nearest point, normal."""
        pts = np.asarray(pts, float).reshape(-1, 3)
        W, Q, Nq = self.transfer(pts, src)
        return ((pts - Q) * Nq).sum(1), Q, Nq

    def push_out(self, pts, clearance, src='all'):
        """move points that are closer than `clearance` to the skin (or inside) out along the skin normal."""
        shp = np.asarray(pts).shape
        pts = np.asarray(pts, float).reshape(-1, 3).copy()
        d, Q, Nq = self.sdist(pts, src)
        cl = np.broadcast_to(np.asarray(clearance, float), d.shape)
        m = d < cl
        pts[m] = Q[m] + Nq[m] * cl[m, None]
        return pts.reshape(shp)

    def cast_in(self, c, d, rstart, src='all'):
        """outside-in ray toward c. radius of the first hit, rstart if the start is inside, NaN if no hit."""
        tree, idx = self.tree(src)
        o = Vector(c + d * rstart)
        hit = tree.ray_cast(o, Vector(-d), rstart)
        if hit[0] is None:
            return float('nan')
        if hit[1].dot(Vector(-d)) > 0:
            return rstart
        return rstart - hit[3]

    def cast_out(self, c, d, rmax, src='all'):
        tree, idx = self.tree(src)
        hit = tree.ray_cast(Vector(c), Vector(d), rmax)
        return hit[3] if hit[0] is not None else rmax


# ----------------------------------------------------------------------------- skin profiles
class Prof:
    """Radius table R[station, angle] of the skin around an axis. RH = convex hull version (cloth spans
    the concavities). pts() returns points at radius + off."""

    def __init__(self, S, A, R, RH, center, direc):
        self.S, self.A, self.R, self.RH = S, A, R, (R if RH is None else RH)
        self.center, self.direc = center, direc

    def blur(self, sig_m):
        ds = self.S[1] - self.S[0]
        return self.__class__(self.S, self.A, gauss_blur_rows(self.R, sig_m / ds), gauss_blur_rows(self.RH, sig_m / ds),
                              self.center, self.direc)

    def rad(self, s, a, hull=0.0):
        s, a = np.broadcast_arrays(np.asarray(s, float), np.asarray(a, float))
        S, A = self.S, self.A
        fs = np.clip((s - S[0]) / (S[1] - S[0]), 0, len(S) - 1.0001)
        i0 = np.floor(fs).astype(int)
        ts = fs - i0
        n = len(A)
        fa = (a % TAU) / TAU * n
        j0 = np.floor(fa).astype(int) % n
        j1 = (j0 + 1) % n
        ta = fa - np.floor(fa)

        def samp(R):
            return (R[i0, j0] * (1 - ta) + R[i0, j1] * ta) * (1 - ts) + (R[i0 + 1, j0] * (1 - ta) + R[i0 + 1, j1] * ta) * ts

        r = samp(self.R)
        if np.any(np.asarray(hull) != 0):
            r = lerp(r, samp(self.RH), hull)
        return r

    def pts(self, s, a, off=0.0, hull=0.0, side=1, r=None):
        s, a = np.broadcast_arrays(np.asarray(s, float), np.asarray(a, float))
        rr = (self.rad(s, a, hull) if r is None else r) + off
        p = self.center(s) + self.direc(a) * rr[..., None]
        if side < 0:
            p = p * MIRX
        return p


def leg_center(z):
    z = np.asarray(z, float)
    zz = np.minimum(z, 0.93)
    x = np.where(zz >= 0.50, 0.10 + (0.095 - 0.10) * (zz - 0.50) / 0.43, 0.10)
    y = np.where(zz >= 0.50, -0.005 + 0.005 * (zz - 0.50) / 0.43, -0.005 + 0.020 * (0.50 - zz) / 0.41)
    return np.stack([x, y, z], -1)


def torso_center(z):
    z = np.asarray(z, float)
    return np.stack([np.zeros_like(z), np.full_like(z, YC), z], -1)


def arm_center(x):
    x = np.asarray(x, float)
    return np.stack([x, np.zeros_like(x), np.full_like(x, ARM_Z)], -1)


def foot_center(y):
    y = np.asarray(y, float)
    z = np.where(y > -0.06, 0.040, 0.040 + (0.013 - 0.040) * (-0.06 - y) / 0.15)
    return np.stack([np.full_like(y, 0.10), y, z], -1)


def hand_center(x):
    x = np.asarray(x, float)
    return np.stack([x, np.full_like(x, 0.001), np.full_like(x, 1.466)], -1)


XCLAMP = 0.186


def make_torso_prof(body, z0=0.06, z1=1.46, dz=0.01, n=72, xclamp=XCLAMP):
    Z = np.arange(z0, z1 + 1e-6, dz)
    A = angles(n)
    R = np.zeros((len(Z), n))
    RH = np.zeros((len(Z), n))
    D = dirxy(A)
    for i, z in enumerate(Z):
        c = np.array([0.0, YC, z])
        xcl = xclamp if z > 1.355 else 0.30
        rr = np.full(n, np.nan)
        for k in range(n):
            rs = min(0.40, xcl / max(abs(D[k, 0]), 1e-9))
            rr[k] = body.cast_in(c, D[k], rs)
        h = hull_polar(rr, A)
        RH[i] = h
        R[i] = np.where(np.isnan(rr), h, rr)
    return Prof(Z, A, R, RH, torso_center, dirxy)


def make_leg_prof(body, z0=0.05, z1=0.97, dz=0.01, n=48):
    Z = np.arange(z0, z1 + 1e-6, dz)
    A = angles(n)
    R = np.zeros((len(Z), n))
    D = dirxy(A)
    C = leg_center(Z)
    for i, z in enumerate(Z):
        for k in range(n):
            rm = 0.17
            if D[k, 0] < -1e-6:
                rm = min(rm, (C[i, 0] + 0.003) / -D[k, 0])
            R[i, k] = body.cast_out(C[i], D[k], rm)
    RH = np.stack([hull_polar(R[i], A) for i in range(len(Z))])
    return Prof(Z, A, R, RH, leg_center, dirxy)


def make_arm_prof(body, x0=0.10, x1=0.76, dx=0.01, n=36):
    X = np.arange(x0, x1 + 1e-6, dx)
    B = angles(n)
    R = np.zeros((len(X), n))
    D = diryz(B)
    for i, x in enumerate(X):
        c = np.array([x, 0.0, ARM_Z])
        for k in range(n):
            R[i, k] = body.cast_out(c, D[k], 0.10)
    iref = int(round((0.225 - x0) / dx))
    for i in range(iref):
        R[i] = np.minimum(R[i], R[iref] + 0.002)
    RH = np.stack([hull_polar(R[i], B) for i in range(len(X))])
    return Prof(X, B, R, RH, arm_center, diryz)


def make_foot_prof(body, n=40):
    """left foot, stations along Y (toe tip -0.206 ... heel +0.062), envelope (toes merged), cut flat at
    z = 0.112 inside the ankle."""
    Y = np.arange(-0.206, 0.0621, 0.004)
    Cc = angles(n)
    D = dirxz(Cc)
    C = foot_center(Y)
    R = np.zeros((len(Y), n))
    for i in range(len(Y)):
        rr = np.full(n, np.nan)
        for k in range(n):
            rs = 0.13
            if D[k, 2] > 1e-6:
                rs = min(rs, (0.112 - C[i, 2]) / D[k, 2])
            rr[k] = body.cast_in(C[i], D[k], rs, 'leg_L')
        R[i] = hull_polar(rr, Cc)
    return Prof(Y, Cc, R, R, foot_center, dirxz)


def make_hand_prof(body, n=36):
    """left hand as a mitten: palm + four fingers envelope, the thumb is cut off by the plane y = -0.046."""
    X = np.arange(0.700, 0.9161, 0.004)
    B = angles(n)
    D = diryz(B)
    C = hand_center(X)
    R = np.zeros((len(X), n))
    for i in range(len(X)):
        rr = np.full(n, np.nan)
        for k in range(n):
            rs = 0.10
            if D[k, 1] < -1e-6:
                rs = min(rs, (C[i, 1] + 0.046) / -D[k, 1])
            rr[k] = body.cast_in(C[i], D[k], rs, 'hand_L')
        R[i] = hull_polar(rr, B)
    return Prof(X, B, R, R, hand_center, diryz)


HEAD_C = np.array([0.0, 0.012, 1.690])


def head_axis(z):
    z = np.asarray(z, float)
    return np.stack([np.zeros_like(z), np.full_like(z, YC), z], -1)


def skull_half_width(z):
    return np.interp(z, [1.60, 1.62, 1.64, 1.72, 1.74], [0.062, 0.064, 0.066, 0.076, 0.074])


def make_head_profs(body, n=72):
    """cylindrical tables around the vertical axis through the head (z 1.46 .. 1.80).
    head : R = skin seen from the axis (ears, nose included), RH = convex hull of the outer envelope.
    skull: same with the ears flattened onto the side of the skull (hair, tight caps)."""
    Z = np.arange(1.46, 1.8001, 0.005)
    A = angles(n)
    D = dirxy(A)
    R = np.zeros((len(Z), n))
    RS = np.zeros((len(Z), n))
    RH = np.zeros((len(Z), n))
    for i, z in enumerate(Z):
        c = np.array([0.0, YC, z])
        env = np.full(n, np.nan)
        for k in range(n):
            R[i, k] = body.cast_out(c, D[k], 0.17, 'all')
            e = body.cast_in(c, D[k], 0.21, 'all')
            env[k] = e if not np.isnan(e) else R[i, k]
        env = np.minimum(env, 0.20)
        RH[i] = hull_polar(env, A) if z < 1.797 else env
        xs = float(skull_half_width(z))
        RS[i] = R[i]
        if 1.625 < z < 1.725:
            for k in range(n):
                p = c + D[k] * R[i, k]
                if abs(p[0]) > xs + 0.0015 and -0.03 < p[1] < 0.06:
                    RS[i, k] = min(R[i, k], xs / max(abs(D[k, 0]), 1e-6))
    head = Prof(Z, A, R, RH, head_axis, dirxy)
    skull = Prof(Z, A, RS, np.stack([hull_polar(RS[i], A) for i in range(len(Z))]), head_axis, dirxy)
    return head, skull


class DomeProf(Prof):
    """spherical table around the head centre HEAD_C: stations = elevation (rad), angles = azimuth."""

    def pts(self, s, a, off=0.0, hull=0.0, side=1, r=None):
        s, a = np.broadcast_arrays(np.asarray(s, float), np.asarray(a, float))
        rr = (self.rad(s, a, hull) if r is None else r) + off
        d = dirxy(a) * np.cos(s)[..., None]
        d[..., 2] = np.sin(s)
        p = HEAD_C + d * rr[..., None]
        if side < 0:
            p = p * MIRX
        return p


def make_dome_prof(body, n=72, e0=-62.5):
    """skull seen from the head centre, elevations e0 .. 90 deg. The ears are flattened (hair / caps)."""
    E = np.radians(np.arange(e0, 90.01, 2.5))
    A = angles(n)
    R = np.zeros((len(E), n))
    for i, e in enumerate(E):
        for k in range(n):
            d = dirxy(A[k]) * math.cos(e)
            d[2] = math.sin(e)
            r = body.cast_out(HEAD_C, d, 0.15, 'all')
            p = HEAD_C + d * r
            xs = float(skull_half_width(p[2]))
            if 1.625 < p[2] < 1.73 and abs(p[0]) > xs + 0.0015 and -0.03 < p[1] < 0.06:
                r = min(r, xs / max(abs(d[0]), 1e-6))
            R[i, k] = r
    return DomeProf(E, A, R, R, None, None)


def collar_loop(body):
    """lower boundary of body_head (the collar line), as a function of azimuth about (0, YC)."""
    o = bpy.data.objects['body_head']
    bm = bmesh.new()
    bm.from_mesh(o.data)
    pts = []
    for e in bm.edges:
        if len(e.link_faces) == 1:
            for v in e.verts:
                if v.co.z < 1.56:
                    pts.append(tuple(v.co))
    bm.free()
    pts = np.array(sorted(set(pts)))
    ang = np.arctan2(pts[:, 0], -(pts[:, 1] - YC)) % TAU
    o = np.argsort(ang)
    return ang[o], pts[o]


def _offs(off, xs, A):
    """offset spec -> (len(xs), len(A)) array. off: scalar, (n,), (n, na) or callable(x, A)."""
    if callable(off):
        off = np.stack([np.broadcast_to(off(x, A), A.shape) for x in xs])
    off = np.asarray(off, float)
    if off.ndim == 1:
        off = off[:, None]
    return np.broadcast_to(off, (len(xs), len(A))).copy()


# ----------------------------------------------------------------------------- the kit (body + profiles)
class Kit:
    def __init__(self):
        t0 = time.time()
        self.body = Body()
        self.torso = make_torso_prof(self.body)
        self.leg = make_leg_prof(self.body)
        self.arm = make_arm_prof(self.body)
        self.foot = make_foot_prof(self.body)
        self.hand = make_hand_prof(self.body)
        self.head, self.skull = make_head_profs(self.body)
        self.dome = make_dome_prof(self.body)
        self.col_a, self.col_p = collar_loop(self.body)
        self.rig = bpy.data.objects['Armature']
        print('KIT ready in %.1fs' % (time.time() - t0))

    # -- collar / yoke --------------------------------------------------------------------------
    def collar(self, A):
        A = np.asarray(A, float) % TAU
        return np.stack([np.interp(A, self.col_a, self.col_p[:, k], period=TAU) for k in range(3)], -1)

    def yoke(self, A, ks, off, z0=1.40, xclamp=XCLAMP):
        """rings between the horizontal torso ring at z0 (k = 0) and the collar line (k = 1), hugging the
        shoulders. off: scalar or one value per k. Returns (len(ks), len(A), 3)."""
        body = self.body
        C = np.array([0.0, YC, z0])
        cp = self.collar(A)
        D0 = dirxy(A)
        D1 = unit(cp - C)
        off = np.broadcast_to(np.asarray(off, float), (len(ks),))
        out = np.zeros((len(ks), len(A), 3))
        for i, k in enumerate(ks):
            for j in range(len(A)):
                om = math.acos(float(np.clip(D0[j] @ D1[j], -1, 1)))
                d = (math.sin((1 - k) * om) * D0[j] + math.sin(k * om) * D1[j]) / max(math.sin(om), 1e-9)
                rs = min(0.45, xclamp / max(abs(d[0]), 1e-9))
                r = body.cast_in(C, d, rs)
                if np.isnan(r):
                    r = rs
                p = C + d * r
                if r >= rs - 1e-9:           # clamped (inside the arm root): push along the ray
                    out[i, j] = p + d * off[i]
                else:
                    W, Q, Nq = body.transfer(p[None], 'trunk')
                    nn = unit(Nq[0] + d)      # between the surface normal and the ray: no spikes
                    out[i, j] = p + nn * off[i] / max(float(nn @ Nq[0]), 0.6)
        return out

    def neck(self, A, dzs, off, rmax=0.13):
        """rings on the neck above the collar line (dz above the collar point of the same azimuth),
        offset along the skin normal."""
        body = self.body
        cp = self.collar(A)
        D = dirxy(A)
        off = np.broadcast_to(np.asarray(off, float), (len(dzs),))
        out = np.zeros((len(dzs), len(A), 3))
        for i, dz in enumerate(dzs):
            P = np.zeros((len(A), 3))
            for j in range(len(A)):
                c = np.array([0.0, 0.015, cp[j, 2] + dz])
                r = body.cast_out(c, D[j], rmax, 'head')
                P[j] = c + D[j] * r
            W, Q, Nq = body.transfer(P, 'head')
            out[i] = P + Nq * off[i]
        return out

    # -- garment rows ---------------------------------------------------------------------------
    def torso_rows(self, zs, A, off, hull=0.7, prof=None):
        """(len(zs), len(A), 3). off: scalar, (nz,), (nz, na) or callable(z, A) -> (na,)."""
        prof = prof or self.torso
        zs = np.asarray(zs, float)
        hull = np.asarray(hull, float)
        if hull.ndim == 1:
            hull = hull[:, None]
        return prof.pts(zs[:, None], A[None, :], off=_offs(off, zs, A), hull=hull)

    def drape(self, A, z_top, zs, off_top, min_off=0.014, flare=0.03, power=1.3, folds=(0, 0.0, 0.0), hull_top=0.7,
              r_top=None):
        """skirt rows hanging from the ring at z_top (radius = skin + off_top): the cloth never comes
        closer than min_off to the hips / legs envelope, hangs straight from the widest point above and
        flares toward the hem. zs: heights below z_top (returned in the same order)."""
        zs = np.asarray(zs, float)
        r0 = self.torso.rad(z_top, A, hull_top) + off_top if r_top is None else np.asarray(r_top, float)
        zmin = float(zs.min())
        fine = np.arange(z_top, zmin - 0.011, -0.01)
        hang = np.zeros((len(fine), len(A)))
        cur = r0.copy()
        for i, z in enumerate(fine):
            cur = np.maximum(cur, self.torso.rad(z, A, 1.0) + min_off * min(1.0, (z_top - z) / 0.04 + 0.3))
            hang[i] = cur
        out = np.zeros((len(zs), len(A), 3))
        nf, amp, ph = folds
        for i, z in enumerate(zs):
            k = min(max(int(round((z_top - z) / 0.01)), 0), len(fine) - 1)
            s = max(z_top - z, 0.0) / max(z_top - zmin, 1e-6)
            r = hang[k] + flare * s ** power
            if nf:
                r = r + amp * s * np.cos(nf * A + ph + 1.7 * s)
            out[i] = torso_center(z) + dirxy(A) * r[:, None]
        return out

    def sleeve_rows(self, xs, B, off, side=1, cap=True, hull=0.0, prof=None):
        """rows along the arm (shoulder -> wrist). With cap=True the first row is shrunk inside the body
        so that the sleeve head is hidden inside the torso shell (set-in sleeve)."""
        prof = prof or self.arm
        xs = np.asarray(xs, float)
        off = _offs(off, xs, B)
        if cap:
            off[0] = -0.014
        return prof.pts(xs[:, None], B[None, :], off=off, hull=hull, side=side)

    def leg_rows(self, zs, A, off, side=1, hull=0.0, prof=None):
        prof = prof or self.leg
        zs = np.asarray(zs, float)
        return prof.pts(zs[:, None], A[None, :], off=_offs(off, zs, A), hull=hull, side=side)


def face_az(ns, af, jf):
    """azimuths of the ns columns of a head row whose face opening has the half angle af (rad): the
    columns -jf .. +jf lie inside the opening, column +-jf exactly on its edge."""
    out = np.zeros(ns)
    h = ns // 2
    for j in range(ns):
        m = j if j <= h else j - ns
        s = 1.0 if m >= 0 else -1.0
        m = abs(m)
        if jf > 0 and m <= jf:
            a = af * m / jf
        else:
            a = af + (math.pi - af) * (m - jf) / (h - jf)
        out[j] = s * a
    return out % TAU


def head_rows(K, spec, ns, jf=0, hull=1.0, prof=None):
    """rows of a head covering. spec: list of (kind, value, off, af_deg):
        kind 'e' : spherical row at elevation `value` (deg) around HEAD_C (skull cap)
        kind 'z' : cylindrical row at height z (head envelope incl. ears with hull, see `prof`)
        off      : scalar or callable(az) -> (ns,) offsets;  af_deg: face opening half angle for that row.
    Returns G (rows, ns, 3) and AZ (rows, ns)."""
    prof = prof or K.head
    G = np.zeros((len(spec), ns, 3))
    AZ = np.zeros((len(spec), ns))
    for i, (kind, val, off, af) in enumerate(spec):
        az = face_az(ns, math.radians(af), jf)
        o = off(az) if callable(off) else off
        if kind == 'e':
            G[i] = K.dome.pts(math.radians(val), az, off=o)
        else:
            G[i] = prof.pts(val, az, off=o, hull=hull)
        AZ[i] = az
    return G, AZ


def face_skip(ns, jf, r0, r1):
    """skip function for Piece.grid: removes the cells of the face opening (rows r0 .. r1-1)."""
    def fn(i, j):
        return (r0 <= i < r1) and (j < jf or j >= ns - jf)
    return fn


# ----------------------------------------------------------------------------- grids helpers
def grid_normals(G, closed=True):
    G = np.asarray(G, float)
    if closed:
        du = np.roll(G, -1, 1) - np.roll(G, 1, 1)
    else:
        du = np.gradient(G, axis=1)
    dv = np.gradient(G, axis=0) if G.shape[0] > 1 else np.zeros_like(G)
    return unit(np.cross(du, dv))


def smooth_ring(G, it=1, k=0.5, closed=True):
    G = np.asarray(G, float).copy()
    for _ in range(it):
        if closed:
            G = G * (1 - k) + k * 0.5 * (np.roll(G, 1, -2) + np.roll(G, -1, -2))
        else:
            H = G.copy()
            H[..., 1:-1, :] = G[..., 1:-1, :] * (1 - k) + k * 0.5 * (G[..., :-2, :] + G[..., 2:, :])
            G = H
    return G


AO_DIRS = []
for _th, _n, _w in ((28.0, 4, 1.0), (62.0, 6, 0.6)):
    for _k in range(_n):
        _ph = TAU * (_k + 0.5 * (_th > 40)) / _n
        AO_DIRS.append((math.sin(math.radians(_th)) * math.cos(_ph), math.sin(math.radians(_th)) * math.sin(_ph),
                        math.cos(math.radians(_th)), _w))


def bake_ao(V, N, F, dist=0.07):
    """cheap ray cast ambient occlusion per vertex (0 = open, 1 = fully occluded)."""
    tree = BVHTree.FromPolygons(V.tolist(), [list(f) for f in F])
    occ = np.zeros(len(V))
    up = np.array([0.0, 0.0, 1.0])
    wsum = sum(d[3] for d in AO_DIRS)
    for i in range(len(V)):
        n = N[i]
        t = np.cross(n, up)
        if t @ t < 1e-6:
            t = np.cross(n, np.array([1.0, 0.0, 0.0]))
        t = t / math.sqrt(t @ t)
        b = np.cross(n, t)
        o = Vector(V[i] + n * 0.004)
        s = 0.0
        for dx, dy, dz, w in AO_DIRS:
            d = t * dx + b * dy + n * dz
            hit = tree.ray_cast(o, Vector(d), dist)
            if hit[0] is not None:
                s += w * (1.0 - hit[3] / dist)
        occ[i] = s / wsum
    return occ


# ----------------------------------------------------------------------------- preview materials
MAT_PREVIEW = {
    'M_cloth': dict(rough=0.9, metal=0.0),
    'M_leather': dict(rough=0.6, metal=0.0),
    'M_metal_steel': dict(rough=0.38, metal=0.7),
    'M_metal_iron': dict(rough=0.55, metal=0.55),
    'M_metal_gold': dict(rough=0.35, metal=0.75),
    'M_metal_bronze': dict(rough=0.4, metal=0.75),
    'M_fur': dict(rough=1.0, metal=0.0),
    'M_rope': dict(rough=0.95, metal=0.0),
    'M_hair': dict(rough=0.5, metal=0.0, color='#5a3d28'),
    'M_bone': dict(rough=0.6, metal=0.0),
}


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is not None and m.get('outfit_pv'):
        return m
    d = MAT_PREVIEW.get(name, dict(rough=0.8, metal=0.0))
    c = lin(d['color']) if 'color' in d else (1.0, 1.0, 1.0)
    m = make_mat(name, c, rough=d['rough'], metal=d['metal'], use_vertex_color=True)
    m['outfit_pv'] = True
    return m


# ----------------------------------------------------------------------------- piece builder
BODY_MORPHS = ['feminine', 'muscular', 'heavy', 'thin', 'shoulder_width', 'chest_size', 'breast_size', 'waist_size',
               'hip_size', 'belly', 'glutes', 'arm_size', 'leg_size', 'neck_size']
HEAD_MORPHS = ['head_size', 'head_width', 'head_depth', 'forehead_height', 'forehead_slope', 'ear_size', 'jaw_width',
               'jaw_height', 'chin_length', 'chin_width', 'chin_forward', 'cheek_fullness', 'cheekbone_width',
               'neck_size', 'feminine', 'heavy', 'age']
FACE_MORPHS = ['brow_ridge', 'nose_length', 'nose_width', 'nose_bridge', 'nose_tip', 'nostril_width', 'cheekbone_height',
               'mouth_width', 'mouth_height', 'lip_upper', 'lip_lower', 'ear_point', 'thin', 'muscular']


class Piece:
    def __init__(self, name, kit):
        self.name = name
        self.kit = kit
        self.body = kit.body
        self.V, self.C, self.F, self.FM, self.FUV, self.chunks = [], [], [], [], [], []
        self.nv = 0

    # -- raw add -----------------------------------------------------------------------------------
    def add(self, V, F, mat, color, uv=None, w=None, src='all', anchor='near', ao=1.0, mscale=1.0, weld=False):
        V = np.asarray(V, float).reshape(-1, 3)
        color = np.broadcast_to(np.asarray(color, float), (len(V), 3))
        F = [list(f) for f in F]
        if weld:
            key = np.round(V / 2e-5).astype(np.int64)
            _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
            remap = first[np.asarray(inv).ravel()]
            F2, U2 = [], []
            for fi, f in enumerate(F):
                g, gu = [], []
                for k, vi in enumerate(f):
                    r = int(remap[vi])
                    if g and r == g[-1]:
                        continue
                    g.append(r)
                    gu.append(uv[fi][k] if uv is not None else None)
                if len(g) > 1 and g[0] == g[-1]:
                    g.pop()
                    gu.pop()
                if len(set(g)) >= 3:
                    F2.append(g)
                    U2.append(gu)
            F = F2
            uv = U2 if uv is not None else None
        used = sorted(set(i for f in F for i in f))
        if len(used) < len(V):
            mp = {v: i for i, v in enumerate(used)}
            F = [[mp[i] for i in f] for f in F]
            V = V[used]
            color = color[used]
        k = len(V)
        b = self.nv
        self.V.append(V)
        self.nv += k
        self.C.append(np.array(color, float))
        for fi, f in enumerate(F):
            self.F.append(tuple(int(i) + b for i in f))
            self.FM.append(mat)
            self.FUV.append(uv[fi] if uv is not None else None)
        self.chunks.append(dict(a=b, b=b + k, w=w, src=src, anchor=anchor, ao=ao, mscale=mscale))
        return b

    def grid(self, G, mat, color, closed=True, flip=False, uv_scale=2.0, uv_fit=False, cap0=False, cap1=False,
             split=(), uv_swap=False, skip=None, **kw):
        """G: (rows, segs, 3). Outward normals when the rows go UP and the segments go front -> left
        (counter clockwise seen from above); pass flip=True otherwise. split: rows where the surface is
        cut into separate vertex sets (hard edge). color: (3,), (rows, segs, 3) or callable(P) -> (n, 3)."""
        G = np.asarray(G, float)
        nr, ns = G.shape[:2]
        if callable(color):
            color = color(G.reshape(-1, 3)).reshape(nr, ns, 3)
        color = np.broadcast_to(np.asarray(color, float), (nr, ns, 3))
        Gu = np.concatenate([G, G[:, :1]], 1) if closed else G
        du = np.linalg.norm(np.diff(Gu, axis=1), axis=2).mean(0)
        U = np.concatenate([[0.0], np.cumsum(du)])
        dv = np.linalg.norm(np.diff(G, axis=0), axis=2).mean(1)
        Vv = np.concatenate([[0.0], np.cumsum(dv)])
        if uv_fit:
            U = U / max(U[-1], 1e-9)
            Vv = Vv / max(Vv[-1], 1e-9)
        else:
            U = U * uv_scale
            Vv = Vv * uv_scale
        rows = [0] + sorted(split) + [nr - 1]
        for ra, rb in zip(rows[:-1], rows[1:]):
            m = rb - ra + 1
            F, UV = [], []
            for i in range(m - 1):
                for j in range(ns if closed else ns - 1):
                    if skip is not None and skip(ra + i, j):
                        continue
                    j2 = (j + 1) % ns
                    q = [i * ns + j, i * ns + j2, (i + 1) * ns + j2, (i + 1) * ns + j]
                    uq = [(U[j], Vv[ra + i]), (U[j + 1], Vv[ra + i]), (U[j + 1], Vv[ra + i + 1]), (U[j], Vv[ra + i + 1])]
                    if uv_swap:
                        uq = [(b_, a_) for a_, b_ in uq]
                    if flip:
                        q, uq = q[::-1], uq[::-1]
                    F.append(q)
                    UV.append(uq)
            Vs = G[ra:rb + 1].reshape(-1, 3)
            Cs = color[ra:rb + 1].reshape(-1, 3)
            for cap, row, last in ((cap0 and ra == 0, 0, False), (cap1 and rb == nr - 1, m - 1, True)):
                if not cap:
                    continue
                ci = len(Vs)
                Vs = np.concatenate([Vs, G[ra + row].mean(0, keepdims=True)], 0)
                Cs = np.concatenate([Cs, color[ra + row].mean(0, keepdims=True)], 0)
                for j in range(ns if closed else ns - 1):
                    j2 = (j + 1) % ns
                    t = [ci, row * ns + j, row * ns + j2] if last else [ci, row * ns + j2, row * ns + j]
                    uq = [(0.5 * (U[j] + U[j + 1]), Vv[ra + row]), (U[j], Vv[ra + row]), (U[j + 1], Vv[ra + row])]
                    if not last:
                        uq = [uq[0], uq[2], uq[1]]
                    if flip:
                        t, uq = t[::-1], uq[::-1]
                    F.append(t)
                    UV.append(uq)
            self.add(Vs, F, mat, Cs, UV, **kw)

    def lining(self, G, mat, color, inset=0.004, closed=True, flip=False, **kw):
        """inner faces for the rows G (same layout as grid): shows the inside of hems, hoods, sleeves."""
        Nn = grid_normals(G, closed)
        if flip:
            Nn = -Nn
        kw.setdefault('ao', 0.3)
        self.grid(np.asarray(G) - Nn * inset, mat, color, closed=closed, flip=not flip, **kw)

    def box(self, c, ax, ay, az, mat, color, **kw):
        """oriented box: centre c, half axes vectors ax, ay, az (hard edges)."""
        c, ax, ay, az = (np.asarray(v, float) for v in (c, ax, ay, az))
        if np.cross(ax, ay) @ az < 0:
            az = -az
        for a, b, n in ((ax, ay, az), (ay, az, ax), (az, ax, ay)):
            for s in (1.0, -1.0):
                q = [c + n * s - a - b, c + n * s + a * s - b * s, c + n * s + a + b, c + n * s - a * s + b * s]
                self.add(q, [[0, 1, 2, 3]], mat, color, **kw)

    # -- finalize ----------------------------------------------------------------------------------
    def build(self, morphs, thr=0.0005, ao_strength=0.75, extra_morphs=()):
        body = self.body
        V = np.concatenate(self.V)
        C = np.concatenate(self.C)
        n = len(V)
        W = np.zeros((n, NB))
        AN = V.copy()
        MS = np.ones(n)
        AOS = np.ones(n)
        for ch in self.chunks:
            a, b = ch['a'], ch['b']
            if b <= a:
                continue
            P = V[a:b]
            Wa, Q, Nq = body.transfer(P, ch['src'])
            w = ch['w']
            if w is None:
                Wc = Wa
            elif isinstance(w, dict):
                Wc = np.zeros((b - a, NB))
                for k, v in w.items():
                    Wc[:, BI[k]] = v
            elif isinstance(w, tuple) and w[0] == 'rigid':
                kk = np.broadcast_to(np.asarray(w[2], float), (b - a,))[:, None]
                Wc = Wa * (1 - kk)
                Wc[:, BI[w[1]]] += kk[:, 0]
            else:
                Wc = w(P, Wa)
            W[a:b] = Wc
            an = ch['anchor']
            if isinstance(an, str) and an == 'near':
                AN[a:b] = Q
            elif isinstance(an, str) and an == 'self':
                AN[a:b] = P
            elif callable(an):
                AN[a:b] = an(P, Q)
            else:
                AN[a:b] = np.broadcast_to(np.asarray(an, float), (b - a, 3))
            MS[a:b] = ch['mscale'] if not callable(ch['mscale']) else ch['mscale'](P)
            AOS[a:b] = ch['ao']
        # 4 influences
        order = np.argsort(-W, axis=1)[:, :4]
        W4 = np.take_along_axis(W, order, 1)
        W4[W4 < 0.01] = 0.0
        W4 /= np.maximum(W4.sum(1, keepdims=True), 1e-9)
        # mesh
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(V.tolist(), [], [list(f) for f in self.F])
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        link(ob)
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        mats = []
        for mname in self.FM:
            if mname not in mats:
                mats.append(mname)
        for mname in mats:
            me.materials.append(get_mat(mname))
        me.polygons.foreach_set('material_index', [mats.index(m) for m in self.FM])
        uvl = me.uv_layers.new(name='UVMap')
        uv = np.zeros((len(me.loops), 2), np.float32)
        li = 0
        for fi, f in enumerate(self.F):
            fu = self.FUV[fi]
            for k, vi in enumerate(f):
                if fu is None or fu[k] is None:
                    p = V[vi]
                    uv[li] = ((p[0] + p[1]) * 2.0, p[2] * 2.0)
                else:
                    uv[li] = fu[k]
                li += 1
        uvl.data.foreach_set('uv', uv.ravel())
        me.update()
        # ambient occlusion
        Nv = np.empty(n * 3, np.float32)
        me.vertices.foreach_get('normal', Nv)
        Nv = Nv.reshape(n, 3).astype(np.float64)
        me.calc_loop_triangles()
        tri = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get('vertices', tri)
        tri = tri.reshape(-1, 3)
        if ao_strength > 0:
            occ = bake_ao(V, Nv, tri)
            C = C * (1.0 - ao_strength * AOS * np.clip(occ * 1.25, 0, 1))[:, None]
        loops_v = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', loops_v)
        attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        rgba = np.concatenate([np.clip(C[loops_v], 0, 1), np.ones((len(loops_v), 1))], 1).astype(np.float32)
        attr.data.foreach_set('color', rgba.ravel())
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = 0
        # skin
        for bidx, bn in enumerate(DEFORM_BONES):
            sel = np.where(order == bidx)
            if len(sel[0]) == 0:
                continue
            vg = None
            for vi, slot in zip(*sel):
                wv = float(W4[vi, slot])
                if wv > 0:
                    if vg is None:
                        vg = ob.vertex_groups.new(name=bn)
                    vg.add([int(vi)], wv, 'REPLACE')
        md = ob.modifiers.new('Armature', 'ARMATURE')
        md.object = self.kit.rig
        ob.parent = self.kit.rig
        # morphs
        kept = []
        fac = np.where(np.abs(AN[:, 0]) > np.abs(V[:, 0]) + 0.01, np.clip(np.abs(V[:, 0]) / 0.03, 0, 1), 1.0)
        deltas = {}
        for mname in list(morphs) + [m for m in extra_morphs if m not in morphs]:
            d = hm.MORPHS[mname](AN) * MS[:, None]
            d[:, 0] *= fac
            if np.abs(d).max() >= thr:
                deltas[mname] = d
                kept.append(mname)
        if kept:
            ob.shape_key_add(name='Basis', from_mix=False)
            for mname in kept:
                kb = ob.shape_key_add(name=mname, from_mix=False)
                kb.slider_min = float(hm.MORPH_META[mname]['min'])
                kb.slider_max = float(hm.MORPH_META[mname]['max'])
                kb.value = 0.0
                kb.data.foreach_set('co', (V + deltas[mname]).astype(np.float32).ravel())
            ob.active_shape_key_index = 0
        me.update()
        self.ob = ob
        self.morphs = kept
        self.materials = mats
        self.tris = len(tri)
        self.Vfinal = V
        print('PIECE %-18s tris=%5d verts=%5d mats=%s morphs=%d' % (self.name, self.tris, n, mats, len(kept)))
        return ob


# ----------------------------------------------------------------------------- sweeps
def band(piece, ring, radial, up, h, t, mat, color, inset=0.004, closed=True, flip=False, bevel=True, **kw):
    """belt-like band around a ring of surface points: bottom / outer / top faces (hard edges).
    ring (n,3): points on the supporting surface, radial (n,3): outward directions, up: (3,) or (n,3)."""
    ring = np.asarray(ring, float)
    up = np.broadcast_to(np.asarray(up, float), ring.shape)
    rows = [ring - radial * inset - up * h * 0.5, ring + radial * t - up * h * 0.5,
            ring + radial * t + up * h * 0.5, ring - radial * inset + up * h * 0.5]
    G = np.stack(rows)
    color = np.asarray(color, float)
    cc = np.stack([np.broadcast_to(color * 0.7, ring.shape), np.broadcast_to(color, ring.shape),
                   np.broadcast_to(color, ring.shape), np.broadcast_to(color * 0.85, ring.shape)])
    piece.grid(G, mat, cc, closed=closed, flip=flip, split=(1, 2) if bevel else (), **kw)


def roll(piece, ring, radial, up, r, mat, color, nseg=4, closed=True, flip=False, squash=1.0, **kw):
    """torus-like roll around a ring (rolled sleeve, fur trim, padded rim). r = tube radius."""
    ring = np.asarray(ring, float)
    up = np.broadcast_to(np.asarray(up, float), ring.shape)
    rows = []
    for k in range(nseg + 1):
        th = lerp(-0.62 * math.pi, 0.62 * math.pi, k / nseg)
        rows.append(ring + radial * (r * math.cos(th) * squash + r * 0.35) + up * (r * math.sin(th)))
    piece.grid(np.stack(rows), mat, color, closed=closed, flip=flip, **kw)


def ring_frame(G_row, center):
    """radial unit vectors of a ring of points about a centre (3,) (in the plane of the ring)."""
    return unit(np.asarray(G_row, float) - np.asarray(center, float))


def tube_path(path, radius, nseg=6, up_hint=(0, 0, 1), twist=0.0, squash=None):
    """rings (len(path), nseg, 3) of a tube along a polyline; radius scalar or per point.
    Outward normals with Piece.grid(flip=False)."""
    path = np.asarray(path, float)
    n = len(path)
    rad = np.broadcast_to(np.asarray(radius, float), (n,))
    T = unit(np.gradient(path, axis=0))
    uh = np.asarray(up_hint, float)
    rings = np.zeros((n, nseg, 3))
    prev_u = None
    for i in range(n):
        u = uh - T[i] * (uh @ T[i]) if prev_u is None else prev_u - T[i] * (prev_u @ T[i])
        if u @ u < 1e-8:
            u = np.cross(T[i], np.array([1.0, 0.0, 0.0]))
        u = u / math.sqrt(u @ u)
        v = np.cross(T[i], u)
        prev_u = u
        for k in range(nseg):
            a = TAU * k / nseg + twist * i
            cu, cv = math.cos(a), math.sin(a)
            if squash is not None:
                cu *= squash
            rings[i, k] = path[i] + (u * cu + v * cv) * rad[i]
    return rings


def shoe(piece, side, off, mat, color, ys=None, ns=10, sole=None, src=None, toe=0.0, **kw):
    """closed foot shell (heel -> toe) from the foot envelope. color: (3,) or callable(P) -> (n,3)."""
    K = piece.kit
    if ys is None:
        ys = np.array([0.060, 0.048, 0.022, -0.012, -0.045, -0.085, -0.125, -0.160, -0.188, -0.204])
    ys = np.asarray(ys, float)
    Cc = angles(ns, 0.5)
    G = K.foot.pts(ys[:, None], Cc[None, :], off=_offs(off, ys, Cc))
    if toe:
        G[..., 1] -= toe * sstep(-0.12, -0.20, G[..., 1])
    G[..., 2] = np.maximum(G[..., 2], 0.0015)
    cc = color(G.reshape(-1, 3)).reshape(G.shape) if callable(color) else np.broadcast_to(np.asarray(color, float), G.shape).copy()
    if sole is not None:
        m = (G[..., 2] < 0.012)[..., None]
        cc = np.where(m, np.asarray(sole, float), cc)
    if side < 0:
        G = G * MIRX
    piece.grid(G, mat, cc, flip=(side > 0), cap0=True, cap1=True, src=src or ('leg_' + SIDE[side]), **kw)
    return G


THUMB_PATH = np.array([[0.746, -0.020, 1.4635], [0.768, -0.040, 1.4585], [0.790, -0.056, 1.4520],
                       [0.810, -0.066, 1.4490], [0.827, -0.0735, 1.4455]])


def glove(piece, side, off, mat, color, xs=None, ns=10, thumb_seg=6, x0=0.705, **kw):
    """mitten: palm + merged fingers shell and a thumb tube (closed at the tips, open at the wrist)."""
    K = piece.kit
    if xs is None:
        xs = np.array([x0, 0.728, 0.752, 0.780, 0.806, 0.832, 0.858, 0.882, 0.902, 0.913])
    xs = np.asarray(xs, float)
    B = angles(ns, 0.5)
    G = K.hand.pts(xs[:, None], B[None, :], off=_offs(off, xs, B))
    src = 'hand_' + SIDE[side]
    M = np.array([float(side), 1.0, 1.0])
    piece.grid(G * M, mat, color, flip=(side < 0), cap1=True, src=src, **kw)
    o = off if np.isscalar(off) else 0.004
    rad = np.array([0.0150, 0.0142, 0.0130, 0.0120, 0.0100]) + o
    T = tube_path(THUMB_PATH, rad, thumb_seg)
    piece.grid(T * M, mat, color, flip=(side < 0), cap1=True, src=src, **kw)
    return G


# ----------------------------------------------------------------------------- weights rules
def w_bones(P, table):
    W = np.zeros((len(P), NB))
    for k, v in table.items():
        W[:, BI[k]] = v
    return W / np.maximum(W.sum(1, keepdims=True), 1e-9)


def w_move(Wa, src_bones, dst):
    """copy of Wa with the weight of src_bones moved to dst (e.g. keep a plate off the arm bones)."""
    W = Wa.copy()
    for bn in src_bones:
        W[:, BI[dst]] += W[:, BI[bn]]
        W[:, BI[bn]] = 0.0
    return W


def w_trunk(P, Wa):
    """trunk only weights (cuirass, vest): the arm / leg bones are folded into the spine / hips."""
    W = w_move(Wa, ('clavicle_L', 'clavicle_R', 'upper_arm_L', 'upper_arm_R', 'forearm_L', 'forearm_R'), 'spine_03')
    return w_move(W, ('thigh_L', 'thigh_R'), 'hips')


def skirt_weights(z_free=0.97, z_full=0.74, follow=0.82, shin=0.0, z_knee=0.50, xw=0.075, back_relax=0.0):
    """weights rule for loose skirts: body weights above z_free, then hips / thigh_L / thigh_R by the
    side (x) of the vertex, optionally a share of the shins below the knee."""
    def fn(P, Wa):
        z = P[:, 2]
        t = sstep(z_free, z_full, z) * follow
        if back_relax:
            t = t * (1.0 - back_relax * sstep(0.0, 0.08, P[:, 1]))
        sl = sstep(-xw, xw, P[:, 0])
        base = w_move(Wa, ('thigh_L', 'thigh_R', 'shin_L', 'shin_R', 'foot_L', 'foot_R', 'toe_L', 'toe_R'), 'hips')
        base = w_move(base, ('clavicle_L', 'clavicle_R', 'upper_arm_L', 'upper_arm_R', 'forearm_L', 'forearm_R'), 'spine_03')
        W = base * (1.0 - t)[:, None]
        sh = shin * sstep(z_knee + 0.02, z_knee - 0.18, z)
        W[:, BI['thigh_L']] += t * sl * (1 - sh)
        W[:, BI['thigh_R']] += t * (1 - sl) * (1 - sh)
        W[:, BI['shin_L']] += t * sl * sh
        W[:, BI['shin_R']] += t * (1 - sl) * sh
        return W
    return fn


# ----------------------------------------------------------------------------- scene / preview
def open_human():
    bpy.ops.wm.open_mainfile(filepath=BLEND_HUMAN)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = False
    return bpy.data.objects['Armature']


def set_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    for bn, v in (pose or {}).items():
        pb = arm.pose.bones[bn]
        if len(v) == 6:
            pb.location = v[3:6]
        pb.rotation_quaternion = Euler([math.radians(a) for a in v[:3]]).to_quaternion()
    bpy.context.view_layer.update()


POSES = {
    'tpose': {},
    'apose': {'upper_arm_L': (-50, 0, 0), 'upper_arm_R': (-50, 0, 0), 'forearm_L': (0, 0, -10), 'forearm_R': (0, 0, 10)},
    'arms_down': {'upper_arm_L': (-78, 0, 0), 'upper_arm_R': (-78, 0, 0), 'forearm_L': (0, 0, -8), 'forearm_R': (0, 0, 8)},
    'run': {'thigh_L': (-50, 0, 0), 'shin_L': (55, 0, 0), 'thigh_R': (30, 0, 0), 'shin_R': (70, 0, 0), 'foot_R': (25, 0, 0),
            'spine_01': (8, 0, 0), 'spine_02': (4, -8, 0),
            'upper_arm_L': (-72, 0, 35), 'forearm_L': (0, 0, -75), 'upper_arm_R': (-72, 0, 45), 'forearm_R': (0, 0, 80)},
    'crouch': {'hips': (20, 0, 0, 0, 0, -0.42), 'thigh_L': (-115, 0, 0), 'thigh_R': (-115, 0, 0), 'shin_L': (125, 0, 0),
               'shin_R': (125, 0, 0), 'foot_L': (-30, 0, 0), 'foot_R': (-30, 0, 0), 'spine_02': (15, 0, 0),
               'upper_arm_L': (-60, 0, -40), 'upper_arm_R': (-60, 0, 40), 'forearm_L': (0, 0, -60), 'forearm_R': (0, 0, 60)},
    'sword_up': {'upper_arm_R': (70, 0, 0), 'clavicle_R': (15, 0, 0), 'forearm_R': (0, 0, 45), 'upper_arm_L': (-70, 0, -15),
                 'forearm_L': (0, 0, -40), 'spine_02': (-6, 0, 0)},
    'twist': {'spine_01': (0, 15, 0), 'spine_02': (0, 15, 0), 'spine_03': (0, 15, 0), 'upper_arm_L': (-70, 0, 0),
              'upper_arm_R': (-70, 0, 0), 'forearm_L': (0, 0, -25), 'forearm_R': (0, 0, 25)},
    'head_turn': {'head': (0, 40, 0), 'neck': (0, 20, 0), 'upper_arm_L': (-78, 0, 0), 'upper_arm_R': (-78, 0, 0)},
}


def set_morphs(weights):
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.data.shape_keys is None:
            continue
        for k in ob.data.shape_keys.key_blocks[1:]:
            k.value = float((weights or {}).get(k.name, 0.0))


BODY_EXTRAS = ('eye_L', 'eye_R', 'brows', 'mouth')


def show_only(names, hides=()):
    """render visibility: body regions (minus `hides`) + eyes/brows/mouth + the listed objects."""
    names = set(names)
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        if ob.name in REGIONS:
            ob.hide_render = ob.name in hides
        elif ob.name in BODY_EXTRAS:
            ob.hide_render = False
        else:
            ob.hide_render = ob.name not in names


def render_tiles(path, tiles, res=384, cols=4):
    """tiles: dicts(show=[object names], hides=[body regions], pose={}|name, morphs={}, view=, center=, half=)."""
    cam = setup_preview(res)
    arm = bpy.data.objects['Armature']
    head = bpy.data.objects.get('pv_head')
    if head is None:
        ld = bpy.data.lights.new('pv_head', 'SUN')
        ld.energy = 1.3
        head = bpy.data.objects.new('pv_head', ld)
        link(head)
    imgs = []
    for t in tiles:
        show_only(t.get('show', ()), t.get('hides', ()))
        set_morphs(t.get('morphs'))
        p = t.get('pose', {})
        set_pose(arm, POSES[p] if isinstance(p, str) else p)
        c = Vector(t.get('center', (0, 0, 0.92)))
        h = t.get('half', 1.0) / 1.12 / math.sqrt(3.0)
        frame_camera(cam, c - Vector((h, h, h)), c + Vector((h, h, h)), t.get('view', 'front'))
        head.rotation_euler = (cam.rotation_euler.to_matrix() @ Euler((math.radians(18), math.radians(-22), 0)).to_matrix()).to_euler()
        imgs.append(render_to_array(os.path.join(tempfile.gettempdir(), 'outfit_pv_%d.png' % os.getpid())))
    set_morphs({})
    set_pose(arm, {})
    save_png(path, montage(imgs, cols=cols))
    print('PREVIEW', path)


def save_blend(name):
    p = os.path.join(BUILD, name)
    assert os.path.basename(p).startswith('outfit_')
    bpy.ops.wm.save_as_mainfile(filepath=p, copy=True)
    return p
