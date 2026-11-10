"""VALOMBRE nature pack - foliage atlas generator (numpy only, run through Blender's python).

Writes:
  assets/textures/leaves_a.png   2048x2048 RGBA, straight alpha, colour bled into transparent texels
  assets/textures/leaves_n.png   same layout, RG = tangent-space normal (OpenGL, +Y up), B = roughness, A = 255
  tools/previews/nat_leaves_atlas.png   contact sheet (albedo on dark bg | alpha | normal)

Layout: 4x4 cells of 512 px, cell (col, row) with row 0 = TOP of the image (see ATLAS_CELLS in nat_common).
Every "twig" cell has its twig base at the bottom centre of the cell and grows upward.
"Curtain" cells (willow_*, pine_spray_b) attach along the whole bottom edge and grow upward: the card is
placed with its bottom edge on the branch and its V axis pointing DOWN in the world.

  blender -b --factory-startup -P tools/blender/nat_atlas.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
import colorsys

SS = 2
CELL = 512
N = CELL * SS
GRID = 4


def hsv(h, s, v):
    return np.array(colorsys.hsv_to_rgb(h % 1.0, min(max(s, 0.0), 1.0), min(max(v, 0.0), 1.0)), np.float32)


def rad(a):
    return a * math.pi / 180.0


def dirv(a):
    return np.array([math.cos(rad(a)), math.sin(rad(a))], np.float64)


# ----------------------------------------------------------------------------- leaf outlines (u in 0..1 -> half width 0..1)
def sh_oak(u):
    u = np.clip(u, 0, 1)
    env = np.power(u, 0.8) * np.power(1 - u, 0.5) / 0.42
    lob = 1.0 - 0.40 * np.power(0.5 - 0.5 * np.cos(2 * np.pi * (u * 3.8 + 0.12)), 1.2)
    return env * lob


def sh_birch(u):
    u = np.clip(u, 0, 1)
    env = np.power(u, 0.42) * np.power(1 - u, 0.9) / 0.44
    saw = 1.0 - 0.10 * np.abs(((u * 10.0) % 1.0) - 0.5) * 2
    return env * saw


def sh_lance(u):
    u = np.clip(u, 0, 1)
    return np.power(np.sin(np.pi * np.power(u, 0.85)), 0.8)


def sh_ovate(u):
    u = np.clip(u, 0, 1)
    env = np.power(u, 0.5) * np.power(1 - u, 0.65) / 0.47
    saw = 1.0 - 0.07 * np.abs(((u * 12.0) % 1.0) - 0.5) * 2
    return env * saw


def sh_ellip(u):
    u = np.clip(u, 0, 1)
    return np.power(np.sin(np.pi * u), 0.62)


def sh_pinna(u):
    u = np.clip(u, 0, 1)
    env = np.power(u, 0.25) * np.power(1 - u, 0.8) / 0.62
    saw = 1.0 - 0.22 * np.abs(((u * 7.0) % 1.0) - 0.5) * 2
    return env * saw


def sh_blade(u):
    u = np.clip(u, 0, 1)
    return np.power(1 - u, 0.55) * np.minimum(1.0, u * 25 + 0.55)


def sh_petal(u):
    u = np.clip(u, 0, 1)
    return np.power(np.sin(np.pi * np.power(u, 1.5)), 0.7)


# ----------------------------------------------------------------------------- raster cell
def noise_field(rng, n, cell):
    g = rng.rand(n // cell + 3, n // cell + 3).astype(np.float32)
    ys = np.arange(n, dtype=np.float32) / cell
    i0 = ys.astype(np.int32)
    f = ys - i0
    f = f * f * (3 - 2 * f)
    a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i0 + 1] * f[None, :]
    b = g[i0 + 1][:, i0] * (1 - f)[None, :] + g[i0 + 1][:, i0 + 1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


class Cell:
    def __init__(self, seed):
        self.P = np.zeros((N, N, 3), np.float32)   # premultiplied colour
        self.A = np.zeros((N, N), np.float32)
        self.NX = np.zeros((N, N), np.float32)     # premultiplied normal xy (tangent space, +Y up)
        self.NY = np.zeros((N, N), np.float32)
        self.R = np.zeros((N, N), np.float32)      # premultiplied roughness
        rng = np.random.RandomState(seed + 977)
        self.noise = (noise_field(rng, N, 24) * 0.6 + noise_field(rng, N, 7) * 0.4) * 2 - 1

    def win(self, cx, cy, r):
        x0 = int(max(0, math.floor(cx - r)))
        x1 = int(min(N, math.ceil(cx + r) + 1))
        y0 = int(max(0, math.floor(cy - r)))
        y1 = int(min(N, math.ceil(cy + r) + 1))
        if x1 <= x0 or y1 <= y0:
            return None
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        return x0, x1, y0, y1, xx + 0.5, yy + 0.5

    def paint(self, x0, x1, y0, y1, cov, rgb, nx, ny, rough, shadow=None):
        s = (slice(y0, y1), slice(x0, x1))
        if shadow is not None:
            self.P[s] *= (1.0 - shadow)[..., None]
        inv = 1.0 - cov
        self.P[s] = self.P[s] * inv[..., None] + rgb * cov[..., None]
        self.A[s] = self.A[s] * inv + cov
        self.NX[s] = self.NX[s] * inv + nx * cov
        self.NY[s] = self.NY[s] * inv + ny * cov
        self.R[s] = self.R[s] * inv + rough * cov

    # p in cell units (y up), radii in cell units
    def capsule(self, p0, p1, r0, r1, col, rough=0.85, shade=0.35, shadow=0.0):
        ax, ay = p0[0] * N, (1 - p0[1]) * N
        bx, by = p1[0] * N, (1 - p1[1]) * N
        r0p, r1p = max(r0 * N, 0.6), max(r1 * N, 0.6)
        cx, cy = (ax + bx) / 2, (ay + by) / 2
        w = self.win(cx, cy, math.hypot(bx - ax, by - ay) / 2 + max(r0p, r1p) + 3)
        if w is None:
            return
        x0, x1, y0, y1, xx, yy = w
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 < 1e-6:
            t = np.zeros_like(xx)
        else:
            t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / L2, 0, 1)
        qx, qy = xx - (ax + t * dx), yy - (ay + t * dy)
        dist = np.sqrt(qx * qx + qy * qy)
        r = r0p + (r1p - r0p) * t
        cov = np.clip(r - dist + 0.5, 0, 1)
        k = np.clip(dist / np.maximum(r, 1e-3), 0, 1)
        c = col[None, None, :] * (1.0 - shade * k * k)[..., None]
        c = c * (1 + 0.10 * self.noise[y0:y1, x0:x1])[..., None]
        inv = 1.0 / np.maximum(dist, 1e-3)
        nx = qx * inv * k * 0.75
        ny = -qy * inv * k * 0.75
        sh = None
        if shadow > 0:
            S = max(2.0, r0p * 1.2)
            sh = shadow * np.clip((r - dist + S) / S, 0, 1) * (1 - cov)
        self.paint(x0, x1, y0, y1, cov, c, nx, ny, rough, sh)

    def leaf(self, p, ang, L, W, shape, col, vein, bend=0.0, fold=0.25, tilt=(0.0, 0.0), curl=0.0, nveins=6,
             rough=0.5, shadow=0.3, hs=1.0, vein_amt=1.0):
        bx, by = p[0] * N, (1 - p[1]) * N
        a = rad(ang)
        ca, sa = math.cos(a), math.sin(a)
        tx, ty = ca, -sa                 # pixel space tangent
        nx_, ny_ = -sa, -ca              # pixel space left normal
        Lp = L * N
        r = Lp * (0.56 + W * 1.05 + abs(bend) * 1.1) + 8
        w = self.win(bx + tx * Lp * 0.5, by + ty * Lp * 0.5, r)
        if w is None:
            return
        x0, x1, y0, y1, xx, yy = w
        dx, dy = xx - bx, yy - by
        u = (dx * tx + dy * ty) / Lp
        v = (dx * nx_ + dy * ny_) / Lp
        v = v - bend * 4 * u * (1 - u)
        hw = shape(u) * W
        inside_u = (u > 0) & (u < 1)
        edge = (hw - np.abs(v)) * Lp
        cov = np.clip(edge + 0.5, 0, 1) * inside_u
        S = max(3.0, Lp * 0.07)
        sh = shadow * np.clip((edge + S) / S, 0, 1) * ((u > -0.04) & (u < 1.04)) * (1 - cov)
        side = np.tanh(v / (0.3 * W + 1e-6))
        c = col[None, None, :] * (0.86 + 0.24 * np.clip(u, 0, 1))[..., None]
        c = c * (1 + 0.07 * hs * side)[..., None]
        edgef = np.clip(edge / (Lp * 0.04 + 1.0), 0, 1)
        c = c * (0.80 + 0.20 * edgef)[..., None]
        vn = np.abs(v) / np.maximum(hw, 1e-4)
        mw = max(1.3, Lp * 0.014)
        mid = np.exp(-np.square(np.abs(v) * Lp / mw)) * np.clip(1.15 - u, 0, 1)
        ph = u * nveins - vn * 0.55
        sv = np.exp(-np.square((ph - np.floor(ph) - 0.5) / 0.11)) * (vn > 0.04) * np.clip(1 - vn, 0, 1)
        vm = np.clip(mid * 0.75 + sv * 0.30, 0, 1) * vein_amt
        c = c * (1 - vm)[..., None] + vein[None, None, :] * vm[..., None]
        c = c * (1 + 0.09 * self.noise[y0:y1, x0:x1])[..., None]
        s_n = tilt[1] + fold * side - sv * 0.25 * side
        s_t = tilt[0] + 2 * curl * (u - 0.5)
        nx = -(s_t * ca + s_n * (-sa))
        ny = -(s_t * sa + s_n * ca)
        ln = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
        self.paint(x0, x1, y0, y1, cov, c, nx * ln, ny * ln, rough, sh)

    def finish(self):
        """-> (rgb straight HxWx3, alpha HxW, normal rgb, rough) at CELL resolution."""
        def down(a):
            if a.ndim == 3:
                return a.reshape(CELL, SS, CELL, SS, a.shape[2]).mean(axis=(1, 3))
            return a.reshape(CELL, SS, CELL, SS).mean(axis=(1, 3))
        P, A, NX, NY, R = down(self.P), down(self.A), down(self.NX), down(self.NY), down(self.R)
        rgb = bleed(P, A)
        Am = np.maximum(A, 1e-4)
        nx = np.where(A > 0.02, NX / Am, 0)
        ny = np.where(A > 0.02, NY / Am, 0)
        rough = bleed(R[..., None], A)[..., 0]
        nxb = bleed((nx * A)[..., None], A)[..., 0]
        nyb = bleed((ny * A)[..., None], A)[..., 0]
        # fade the bled normal towards flat away from the leaves
        return rgb, A, np.dstack([nxb, nyb]), rough


def bleed(P, A):
    """Pull-push dilation. P = premultiplied colour, A = weight. Returns straight colour defined everywhere."""
    Ps, As = [P.astype(np.float32)], [A.astype(np.float32)]
    while Ps[-1].shape[0] > 1:
        p, a = Ps[-1], As[-1]
        h = p.shape[0] // 2
        Ps.append(p.reshape(h, 2, h, 2, p.shape[2]).sum(axis=(1, 3)))
        As.append(a.reshape(h, 2, h, 2).sum(axis=(1, 3)))
    col = Ps[-1] / np.maximum(As[-1], 1e-6)[..., None]
    for lvl in range(len(Ps) - 2, -1, -1):
        up = np.repeat(np.repeat(col, 2, axis=0), 2, axis=1)
        # light blur of the upsampled level to avoid blocks
        up = (up + np.roll(up, 1, 0) + np.roll(up, -1, 0) + np.roll(up, 1, 1) + np.roll(up, -1, 1)) / 5.0
        a = As[lvl]
        k = np.clip(a * (8.0 if lvl == 0 else 3.0), 0, 1)
        own = Ps[lvl] / np.maximum(a, 1e-6)[..., None]
        col = up * (1 - k)[..., None] + own * k[..., None]
    return col


# ----------------------------------------------------------------------------- sketch (primitive list, fitted then rasterised)
class Sketch:
    def __init__(self, seed):
        self.rng = np.random.RandomState(seed)
        self.seed = seed
        self.items = []

    def cap(self, p0, p1, r0, r1, col, z=-1.0, rough=0.85, shade=0.35, shadow=0.0):
        self.items.append(dict(k='cap', p0=np.array(p0, float), p1=np.array(p1, float), r0=r0, r1=r1, col=col,
                               z=z, rough=rough, shade=shade, shadow=shadow))

    def leaf(self, p, ang, L, W, shape, col, vein, z=None, **kw):
        if z is None:
            z = self.rng.rand()
        self.items.append(dict(k='leaf', p=np.array(p, float), ang=ang, L=L, W=W, shape=shape, col=col, vein=vein,
                               z=z, kw=kw))

    def path(self, p, ang, length, n, wig=7.0, trop=0.0, r0=0.006, r1=0.002, col=None, z=-1.0, draw=True):
        """Wiggly twig. Returns (points, angles)."""
        pts = [np.array(p, float)]
        angs = []
        a = ang
        for i in range(n):
            a += self.rng.uniform(-wig, wig) + trop
            angs.append(a)
            pts.append(pts[-1] + (length / n) * dirv(a))
        if draw and col is not None:
            for i in range(n):
                ra = r0 + (r1 - r0) * i / n
                rb = r0 + (r1 - r0) * (i + 1) / n
                self.cap(pts[i], pts[i + 1], ra, rb, col * (0.9 + 0.2 * self.rng.rand()), z=z)
        return pts, angs

    @staticmethod
    def along(pts, angs, t):
        n = len(angs)
        f = min(max(t, 0.0), 0.9999) * n
        i = int(f)
        return pts[i] + (pts[i + 1] - pts[i]) * (f - i), angs[i]

    def extents(self):
        xs, ys = [], []
        for it in self.items:
            if it['k'] == 'cap':
                for p, r in ((it['p0'], it['r0']), (it['p1'], it['r1'])):
                    xs += [p[0] - r, p[0] + r]
                    ys += [p[1] - r, p[1] + r]
            else:
                p, L, W = it['p'], it['L'], it['W']
                t = dirv(it['ang'])
                n = np.array([-t[1], t[0]])
                bend = it['kw'].get('bend', 0.0)
                for q in (p, p + t * L, p + t * L * 0.5 + n * L * (W + bend), p + t * L * 0.5 - n * L * (W - bend),
                          p + t * L * 0.3 + n * L * W, p + t * L * 0.3 - n * L * W,
                          p + t * L * 0.75 + n * L * W * 0.8, p + t * L * 0.75 - n * L * W * 0.8):
                    xs.append(q[0])
                    ys.append(q[1])
        return min(xs), min(ys), max(xs), max(ys)

    def fit(self, anchor=(0.5, 0.022), halfw=0.465, top=0.972, max_scale=10.0):
        """Uniformly scale around the sketch origin (0, 0) so everything fits the cell. The origin lands on
        anchor (x = cell centre); if parts hang below the origin the anchor is raised just enough."""
        x0, y0, x1, y1 = self.extents()
        lo = min(y0, 0.0)
        s = min(halfw / max(abs(x0), abs(x1), 1e-6), (top - anchor[1]) / max(y1 - lo, 1e-6), max_scale)
        self.anchor = (anchor[0], anchor[1] - lo * s)
        self.xform(s, self.anchor)
        return s

    def xform(self, s, off):
        off = np.array(off, float)
        for it in self.items:
            if it['k'] == 'cap':
                it['p0'] = it['p0'] * s + off
                it['p1'] = it['p1'] * s + off
                it['r0'] *= s
                it['r1'] *= s
            else:
                it['p'] = it['p'] * s + off
                it['L'] *= s

    def render(self, zshade=(0.60, 1.06)):
        cell = Cell(self.seed)
        for it in sorted(self.items, key=lambda i: i['z']):
            zc = min(max(it['z'], 0.0), 1.0)
            k = zshade[0] + (zshade[1] - zshade[0]) * zc
            if it['k'] == 'cap':
                kk = k if it['z'] >= 0 else 1.0
                cell.capsule(it['p0'], it['p1'], it['r0'], it['r1'], it['col'] * kk, it['rough'], it['shade'],
                             it['shadow'])
            else:
                cell.leaf(it['p'], it['ang'], it['L'], it['W'], it['shape'], it['col'] * k, it['vein'] * min(1.0, k + 0.1),
                          **it['kw'])
        return cell.finish()


# ----------------------------------------------------------------------------- foliage builders
def leaf_kw(rng, fold=0.28, tilt=0.22, curl=0.25, bend=0.05):
    return dict(bend=rng.uniform(-bend, bend), fold=fold * rng.uniform(0.5, 1.3),
                tilt=(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt)), curl=rng.uniform(-curl, curl),
                hs=rng.choice([-1.0, 1.0]))


def shoot(sk, p, ang, length, spec, r0=0.0055, nseg=5, rosette=5, tip_scale=1.0, trop=0.0, start=0.18):
    """A twig with alternate leaves along it and a terminal rosette."""
    rng = sk.rng
    pts, angs = sk.path(p, ang, length, nseg, wig=spec.get('wig', 8.0), trop=trop, r0=r0, r1=r0 * 0.35,
                        col=spec['twig'])
    n_along = max(0, int(round(length * (1 - start) / spec['spacing'])))
    side = rng.choice([-1, 1])
    for i in range(n_along):
        t = start + (1 - start) * (i + rng.uniform(0.2, 0.8)) / max(n_along, 1)
        q, a = Sketch.along(pts, angs, t)
        side = -side
        la = a + side * rng.uniform(*spec['angle'])
        L = rng.uniform(*spec['L']) * (0.85 + 0.15 * t)
        pet = spec.get('petiole', 0.0) * L
        b = q + dirv(la) * pet
        if pet > 0:
            sk.cap(q, b, 0.0016, 0.0012, spec['twig'] * 1.2, z=-0.5)
        sk.leaf(b, la + rng.uniform(-8, 8), L, spec['W'] * rng.uniform(0.85, 1.15), spec['shape'], spec['col'](rng),
                spec['vein'], nveins=spec.get('nveins', 6), rough=spec.get('rough', 0.5), **leaf_kw(rng))
    q, a = pts[-1], angs[-1]
    for i in range(rosette):
        f = (i / max(rosette - 1, 1)) * 2 - 1 if rosette > 1 else 0.0
        la = a + f * spec.get('fan', 70.0) + rng.uniform(-10, 10)
        L = rng.uniform(*spec['L']) * tip_scale * (1.0 - 0.18 * abs(f))
        sk.leaf(q, la, L, spec['W'] * rng.uniform(0.85, 1.15), spec['shape'], spec['col'](rng), spec['vein'],
                z=0.35 + 0.65 * rng.rand(), nveins=spec.get('nveins', 6), rough=spec.get('rough', 0.5), **leaf_kw(rng))
    return pts, angs


def twig_cluster(sk, spec, p=(0, 0), ang=90.0, length=0.55, n_side=5, side_len=(0.34, 0.2), side_ang=(42, 62),
                 first=0.22, rosette=5, r0=0.009, nseg=7, sub=False):
    rng = sk.rng
    pts, angs = shoot(sk, p, ang, length, spec, r0=r0, nseg=nseg, rosette=rosette, start=max(first, 0.12))
    side = rng.choice([-1, 1])
    for i in range(n_side):
        t = first + (0.9 - first) * (i + rng.uniform(-0.15, 0.15)) / max(n_side - 1, 1)
        q, a = Sketch.along(pts, angs, t)
        side = -side
        sl = side_len[0] + (side_len[1] - side_len[0]) * i / max(n_side - 1, 1)
        sl *= rng.uniform(0.85, 1.15)
        sa = a + side * rng.uniform(*side_ang)
        spts, sangs = shoot(sk, q, sa, sl, spec, r0=r0 * 0.6, nseg=4, rosette=max(3, rosette - 1),
                            trop=-side * 3.0)
        if sub and sl > 0.2:
            for tt, sg in ((0.42, -1), (0.68, 1)):
                q2, a2 = Sketch.along(spts, sangs, tt)
                shoot(sk, q2, a2 + sg * side * rng.uniform(35, 55), sl * rng.uniform(0.38, 0.52), spec, r0=r0 * 0.4,
                      nseg=3, rosette=4)


def col_fn(h, s, v, dh=0.025, ds=0.10, dv=0.07, alt=None, alt_p=0.0):
    def f(rng):
        if alt is not None and rng.rand() < alt_p:
            hh, ss_, vv = alt
            return hsv(hh + rng.uniform(-dh, dh), ss_ + rng.uniform(-ds, ds), vv + rng.uniform(-dv, dv))
        return hsv(h + rng.uniform(-dh, dh), s + rng.uniform(-ds, ds), v + rng.uniform(-dv, dv))
    return f


TWIG_OAK = np.array([0.30, 0.23, 0.16], np.float32)
TWIG_BIRCH = np.array([0.26, 0.17, 0.13], np.float32)
TWIG_WILLOW = np.array([0.42, 0.40, 0.20], np.float32)
TWIG_PINE = np.array([0.33, 0.24, 0.16], np.float32)

OAK = dict(shape=sh_oak, L=(0.135, 0.178), W=0.31, col=col_fn(0.245, 0.58, 0.44, alt=(0.19, 0.55, 0.50), alt_p=0.14),
           vein=hsv(0.21, 0.42, 0.62), spacing=0.058, angle=(35, 65), twig=TWIG_OAK, nveins=5, petiole=0.04,
           fan=75.0, rough=0.46)
BIRCH = dict(shape=sh_birch, L=(0.085, 0.115), W=0.36, col=col_fn(0.225, 0.60, 0.56, alt=(0.165, 0.62, 0.66), alt_p=0.16),
             vein=hsv(0.19, 0.45, 0.74), spacing=0.05, angle=(40, 75), twig=TWIG_BIRCH, nveins=7, petiole=0.22,
             fan=60.0, wig=10.0, rough=0.5)
BUSH_A = dict(shape=sh_ovate, L=(0.15, 0.20), W=0.36, col=col_fn(0.27, 0.56, 0.47, alt=(0.22, 0.55, 0.52), alt_p=0.12),
              vein=hsv(0.24, 0.40, 0.66), spacing=0.075, angle=(35, 65), twig=TWIG_OAK * 0.9, nveins=7, petiole=0.07,
              fan=70.0, rough=0.52)
BUSH_B = dict(shape=sh_ellip, L=(0.085, 0.115), W=0.27, col=col_fn(0.30, 0.50, 0.36, alt=(0.06, 0.55, 0.42), alt_p=0.07),
              vein=hsv(0.27, 0.35, 0.52), spacing=0.042, angle=(35, 60), twig=TWIG_BIRCH * 1.1, nveins=5, petiole=0.05,
              fan=65.0, rough=0.42)


def cell_oak_a(seed):
    sk = Sketch(seed)
    twig_cluster(sk, OAK, length=0.62, n_side=8, side_len=(0.40, 0.20), rosette=6, first=0.08, sub=True)
    sk.fit()
    return sk.render()


def cell_oak_b(seed):
    sk = Sketch(seed)
    twig_cluster(sk, OAK, ang=85.0, length=0.66, n_side=7, side_len=(0.44, 0.22), side_ang=(46, 70), rosette=6,
                 first=0.06, sub=True)
    sk.fit()
    return sk.render()


def cell_blob(seed, spec, n=16, rx=0.40, ry=0.33, slen=(0.20, 0.32), zshade=(0.55, 1.06)):
    """Dense roundish foliage mass (for the big LOD1 cards): twigs scattered in an ellipse, pointing outward."""
    sk = Sketch(seed)
    rng = sk.rng
    cy = 0.46
    # hidden carrier branches from the anchor
    for a in (90, 60, 120):
        sk.path((0, 0), a + rng.uniform(-6, 6), 0.42, 5, wig=8.0, r0=0.010, r1=0.004, col=spec['twig'])
    for i in range(n):
        if i == 0:
            px, py = 0.0, 0.0
        else:
            aa = 2.399963 * i
            rr = math.sqrt((i + 0.5) / n)
            px, py = math.cos(aa) * rr * rx, math.sin(aa) * rr * ry
        out = math.degrees(math.atan2(py + 0.18, px)) if i else 90.0
        ang = out + rng.uniform(-45, 45)
        ln = rng.uniform(*slen)
        p0 = np.array([px, cy + py]) - dirv(ang) * ln * 0.55
        shoot(sk, p0, ang, ln, spec, r0=0.005, nseg=4, rosette=5, start=0.1)
    sk.fit()
    return sk.render(zshade=zshade)


def cell_oak_dense(seed):
    spec = dict(OAK)
    spec['L'] = (0.105, 0.135)
    spec['spacing'] = 0.05
    return cell_blob(seed, spec, n=30, slen=(0.2, 0.3))


def cell_birch(seed, dense=False):
    sk = Sketch(seed)
    rng = sk.rng
    spec = dict(BIRCH)
    fans = (90, 62, 118, 38, 142) if not dense else (90, 68, 112, 47, 133, 30, 150)
    if dense:
        spec['wig'] = 5.0
        spec['L'] = (0.07, 0.092)
        spec['spacing'] = 0.04
    for i, a in enumerate(fans):
        ln = (0.86 if not dense else 0.80) * (1.0 - 0.22 * abs(a - 90) / 60.0) * rng.uniform(0.9, 1.05)
        pts, angs = shoot(sk, (0, 0), a + rng.uniform(-5, 5), ln, spec, r0=0.0042, nseg=8, rosette=3,
                          trop=(1.6 if a < 90 else -1.6) * rng.uniform(0.3, 1.2), start=0.16)
        for t in ((0.38, 0.62) if not dense else (0.22, 0.4, 0.58, 0.76)):
            q, aa = Sketch.along(pts, angs, t + rng.uniform(-0.05, 0.05))
            sd = rng.choice([-1, 1])
            shoot(sk, q, aa + sd * rng.uniform(28, 48), ln * rng.uniform(0.28, 0.42), spec, r0=0.0026, nseg=4,
                  rosette=3, start=0.2)
    sk.fit()
    return sk.render(zshade=(0.66, 1.06))


def cell_birch_dense(seed):
    spec = dict(BIRCH)
    spec['L'] = (0.066, 0.086)
    spec['spacing'] = 0.036
    spec['wig'] = 7.0
    return cell_blob(seed, spec, n=40, rx=0.38, ry=0.36, slen=(0.2, 0.3), zshade=(0.62, 1.06))


def cell_willow(seed, dense=False):
    """Curtain cell: strands attached along the bottom edge, growing upward."""
    sk = Sketch(seed)
    rng = sk.rng
    colf = col_fn(0.215, 0.46, 0.55, dh=0.02, alt=(0.17, 0.5, 0.62), alt_p=0.12)
    vein = hsv(0.19, 0.30, 0.74)
    n = 10 if not dense else 13
    xs = np.linspace(0.07, 0.93, n) + rng.uniform(-0.02, 0.02, n)
    for i, x in enumerate(xs):
        ln = rng.uniform(0.62, 0.93) if not dense else rng.uniform(0.70, 0.94)
        if i in (0, n - 1):
            ln *= 0.82
        pts, angs = sk.path((x, 0.0), 90 + rng.uniform(-4, 4), ln, 10, wig=4.0, r0=0.0030, r1=0.0012,
                            col=TWIG_WILLOW, z=-1)
        nl = int(ln / (0.021 if not dense else 0.019))
        sd = 1
        for j in range(nl):
            t = (j + rng.uniform(0.1, 0.9)) / nl
            q, a = Sketch.along(pts, angs, t)
            sd = -sd
            L = rng.uniform(0.070, 0.098) * (1.0 - 0.25 * t)
            sk.leaf(q, a + sd * rng.uniform(14, 34), L, 0.115 * rng.uniform(0.85, 1.2), sh_lance, colf(rng), vein,
                    nveins=0, rough=0.5, shadow=0.22, **leaf_kw(rng, fold=0.35, tilt=0.3, bend=0.10))
    # no fit: already in cell coordinates; shift up a hair so the bottom edge stays clean
    sk.xform(0.972, (0.014, 0.012))
    return sk.render(zshade=(0.66, 1.05))


def needle_twig(sk, p, ang, length, nlen, rng, colf, under, z0, dens=1.0, r0=0.0035, slant=42.0, sides=(-1, 1)):
    """A conifer twig: dark solid under-shape + needles."""
    t = dirv(ang)
    sk.leaf(np.array(p) - t * nlen * 0.2, ang, length + nlen * 0.9, (nlen * 0.78) / (length + nlen * 0.9), sh_ellip,
            under, under, z=z0, nveins=0, fold=0.5, shadow=0.25, vein_amt=0.0, rough=0.62)
    sk.cap(p, np.array(p) + t * length, r0, r0 * 0.4, TWIG_PINE, z=z0 + 0.01, shadow=0.0)
    n = max(3, int(length / (0.0062 / dens)))
    for i in range(n):
        f = (i + rng.rand()) / n
        q = np.array(p) + t * length * f
        for sd in sides:
            a = ang + sd * (slant + rng.uniform(-12, 12))
            nl = nlen * rng.uniform(0.75, 1.1) * (1.0 - 0.35 * f * f)
            sk.cap(q, q + dirv(a) * nl, 0.0021, 0.0012, colf(rng), z=z0 + 0.02 + 0.2 * rng.rand(), rough=0.55,
                   shade=0.5)
    # tip tuft
    q = np.array(p) + t * length
    for a in np.linspace(-40, 40, 5):
        sk.cap(q, q + dirv(ang + a + rng.uniform(-6, 6)) * nlen * 0.85, 0.0021, 0.0012, colf(rng), z=z0 + 0.3,
               rough=0.55, shade=0.5)


def cell_pine_flat(seed, dense=False):
    """Flat conifer bough seen from above: base at the bottom centre, tip at the top."""
    sk = Sketch(seed)
    rng = sk.rng
    colf = col_fn(0.335, 0.50, 0.40, dh=0.03, ds=0.08, dv=0.07, alt=(0.27, 0.50, 0.47), alt_p=0.18)
    under = hsv(0.35, 0.48, 0.21)
    L = 0.93
    pts, angs = sk.path((0, 0), 90, L, 9, wig=3.0, r0=0.010, r1=0.003, col=TWIG_PINE, z=0.05)
    n = 13 if not dense else 16
    for i in range(n):
        f = 0.10 + 0.86 * i / (n - 1)
        q, a = Sketch.along(pts, angs, f)
        prof = math.sin(math.pi * min(1.0, (f + 0.05) ** 0.62)) ** 0.9
        sl = (0.40 if not dense else 0.46) * max(0.12, prof) * rng.uniform(0.82, 1.1)
        for sd in (-1, 1):
            sa = a + sd * rng.uniform(46, 62) * (1.0 - 0.25 * f)
            z0 = 0.1 + 0.5 * rng.rand()
            needle_twig(sk, q, sa, sl, 0.036, rng, colf, under, z0, r0=0.0042)
            if sl > 0.16:
                m = 2 if sl < 0.3 else 3
                for k in range(m):
                    ff = 0.3 + 0.5 * k / max(m - 1, 1)
                    q2 = q + dirv(sa) * sl * ff
                    for sd2 in ((-1, 1) if dense or k % 2 == 0 else (sd,)):
                        needle_twig(sk, q2, sa + sd2 * rng.uniform(40, 55), sl * rng.uniform(0.3, 0.45) * (1 - 0.4 * ff),
                                    0.032, rng, colf, under, z0 + 0.1, r0=0.003)
    needle_twig(sk, pts[-1], angs[-1], 0.05, 0.036, rng, colf, under, 0.6)
    sk.fit(top=0.975)
    return sk.render(zshade=(0.62, 1.08))


def cell_pine_hang(seed):
    """Curtain cell: branch along the bottom edge (base at left, tip at right), drooping twigs growing upward."""
    sk = Sketch(seed)
    rng = sk.rng
    colf = col_fn(0.335, 0.50, 0.39, dh=0.03, ds=0.08, dv=0.07, alt=(0.27, 0.50, 0.46), alt_p=0.16)
    under = hsv(0.35, 0.48, 0.20)
    sk.cap((0.02, 0.03), (0.97, 0.03), 0.011, 0.004, TWIG_PINE, z=0.9)
    n = 15
    for i in range(n):
        x = 0.05 + 0.90 * (i + rng.uniform(-0.25, 0.25)) / (n - 1)
        x = min(max(x, 0.04), 0.96)
        prof = math.sin(math.pi * min(1.0, (x * 0.92 + 0.08) ** 0.75)) ** 0.7
        ln = (0.18 + 0.72 * prof) * rng.uniform(0.7, 1.05)
        a = 90 + rng.uniform(-9, 9) - (x - 0.5) * 14
        z0 = 0.1 + 0.6 * rng.rand()
        needle_twig(sk, (x, 0.03), a, ln, 0.034, rng, colf, under, z0, r0=0.004, slant=36.0)
        m = int(ln / 0.16)
        for k in range(m):
            ff = (k + 0.6) / (m + 0.6)
            q = np.array((x, 0.03)) + dirv(a) * ln * ff
            sd = rng.choice([-1, 1])
            needle_twig(sk, q, a + sd * rng.uniform(22, 38), ln * rng.uniform(0.22, 0.34), 0.030, rng, colf, under,
                        z0 + 0.1, r0=0.003, slant=36.0)
    # needles on the branch itself
    for i in range(70):
        x = 0.03 + 0.93 * rng.rand()
        sk.cap((x, 0.03), np.array((x, 0.03)) + dirv(rng.uniform(40, 140)) * 0.03, 0.0021, 0.0012, colf(rng),
               z=0.95, rough=0.55)
    x0, y0, x1, y1 = sk.extents()
    s = min(1.0, 0.955 / (y1 - 0.0))
    sk.xform(s, (0.5 - 0.5 * s, 0.006))
    return sk.render(zshade=(0.62, 1.08))


def cell_bush_a(seed):
    sk = Sketch(seed)
    twig_cluster(sk, BUSH_A, length=0.60, n_side=5, side_len=(0.36, 0.2), rosette=5, side_ang=(40, 62))
    sk.fit()
    return sk.render()


def cell_bush_b(seed):
    sk = Sketch(seed)
    rng = sk.rng
    for a, ln in ((90, 0.80), (58, 0.66), (122, 0.66), (30, 0.46), (150, 0.46)):
        pts, angs = shoot(sk, (0, 0), a + rng.uniform(-6, 6), ln, BUSH_B, r0=0.0055, nseg=7, rosette=4, start=0.12)
        for t in (0.35, 0.58, 0.8):
            q, aa = Sketch.along(pts, angs, t + rng.uniform(-0.06, 0.06))
            sd = rng.choice([-1, 1])
            sp, sa_ = shoot(sk, q, aa + sd * rng.uniform(35, 60), ln * rng.uniform(0.22, 0.36), BUSH_B, r0=0.003,
                            nseg=3, rosette=3, start=0.15)
            if rng.rand() < 0.65:      # berry cluster
                bq = sp[-1]
                for k in range(rng.randint(2, 5)):
                    c = bq + rng.uniform(-0.022, 0.022, 2)
                    bc = hsv(0.985 + rng.uniform(-0.02, 0.02), 0.72, 0.50 + rng.uniform(-0.08, 0.08))
                    sk.cap(c, c + np.array([0.0005, 0.0005]), 0.0105, 0.0105, bc, z=0.9 + 0.1 * rng.rand(),
                           rough=0.25, shade=0.55, shadow=0.3)
                    sk.cap(c + np.array([-0.003, 0.0035]), c + np.array([-0.0025, 0.0035]), 0.0028, 0.0028,
                           bc * 1.5 + 0.15, z=1.2, rough=0.2, shade=0.0)
    sk.fit()
    return sk.render(zshade=(0.6, 1.06))


def cell_fern(seed):
    sk = Sketch(seed)
    rng = sk.rng
    colf = col_fn(0.262, 0.60, 0.46, dh=0.015, ds=0.06, dv=0.05)
    vein = hsv(0.235, 0.45, 0.62)
    stem = hsv(0.20, 0.45, 0.40)
    pts, angs = sk.path((0, 0), 90, 0.955, 12, wig=1.6, trop=0.0, r0=0.0075, r1=0.002, col=stem, z=0.99)
    n = 21
    for i in range(n):
        f = 0.10 + 0.88 * i / (n - 1)
        q, a = Sketch.along(pts, angs, f)
        prof = (min(1.0, f / 0.28) ** 0.7) * (max(0.0, 1 - f) ** 0.62) / 0.82
        L = max(0.022, 0.33 * prof)
        for sd in (-1, 1):
            la = a + sd * (72 - 30 * f) + rng.uniform(-4, 4)
            sk.leaf(q, la, L * rng.uniform(0.92, 1.06), 0.165 + 0.05 * f, sh_pinna, colf(rng), vein,
                    z=0.2 + 0.6 * rng.rand(), nveins=7, rough=0.55, shadow=0.25,
                    **leaf_kw(rng, fold=0.3, tilt=0.18, bend=0.06))
    sk.leaf(pts[-1], angs[-1], 0.05, 0.3, sh_lance, colf(rng), vein, z=0.9, nveins=0)
    sk.fit(halfw=0.47)
    return sk.render(zshade=(0.74, 1.05))


def cell_reeds(seed):
    sk = Sketch(seed)
    rng = sk.rng
    colf = col_fn(0.185, 0.50, 0.52, dh=0.03, ds=0.10, dv=0.07, alt=(0.125, 0.45, 0.60), alt_p=0.22)
    vein = hsv(0.16, 0.35, 0.70)
    n = 11
    for i in range(n):
        x = (i / (n - 1) - 0.5) * 0.42 + rng.uniform(-0.02, 0.02)
        a = 90 - x * 62 + rng.uniform(-6, 6)
        L = rng.uniform(0.60, 0.99)
        sk.leaf((x, 0.0), a, L, 0.032 / L * rng.uniform(0.75, 1.3), sh_blade, colf(rng), vein, nveins=0,
                rough=0.5, shadow=0.2, fold=0.35, bend=rng.uniform(-0.08, 0.08) - x * 0.25,
                tilt=(0.0, rng.uniform(-0.3, 0.3)), curl=0.0, hs=rng.choice([-1.0, 1.0]))
    # cattail heads
    for x, h, a in ((-0.07, 0.80, 96.0), (0.09, 0.90, 86.0), (0.01, 0.68, 91.0)):
        st = hsv(0.17, 0.45, 0.50)
        tip = np.array((x, 0.0)) + dirv(a) * h
        sk.cap((x, 0.0), tip, 0.0055, 0.004, st, z=0.5, rough=0.6)
        h0 = tip - dirv(a) * 0.20
        h1 = tip - dirv(a) * 0.05
        sk.cap(h0, h1, 0.021, 0.019, hsv(0.065, 0.62, 0.30), z=1.0, rough=0.9, shade=0.5, shadow=0.25)
    sk.fit(halfw=0.46)
    return sk.render(zshade=(0.68, 1.05))


def cell_flowers(seed):
    """Stems + leaves in true greens (lower half), heads in WHITE (upper half) so the vertex colour tints them."""
    sk = Sketch(seed)
    rng = sk.rng
    stem = hsv(0.26, 0.55, 0.36)
    colf = col_fn(0.265, 0.55, 0.42, dh=0.02)
    vein = hsv(0.24, 0.4, 0.58)
    heads = []
    n = 7
    for i in range(n):
        f = (i / (n - 1) - 0.5)
        a = 90 - f * 64 + rng.uniform(-6, 6)
        ln = rng.uniform(0.62, 0.93) * (1.0 - 0.25 * abs(f))
        pts, angs = sk.path((f * 0.10, 0.0), a, ln, 6, wig=5.0, r0=0.0055, r1=0.0035, col=stem, z=0.02)
        for t in (0.12, 0.25, 0.38):
            q, aa = Sketch.along(pts, angs, t + rng.uniform(-0.04, 0.04))
            sd = rng.choice([-1, 1])
            sk.leaf(q, aa + sd * rng.uniform(30, 55), rng.uniform(0.12, 0.17), 0.16, sh_lance, colf(rng), vein,
                    z=0.1 + 0.3 * rng.rand(), nveins=4, **leaf_kw(rng))
        heads.append((pts[-1], angs[-1], rng.rand()))
    # basal leaves
    for i in range(8):
        a = 90 + rng.uniform(-70, 70)
        sk.leaf((rng.uniform(-0.03, 0.03), 0.0), a, rng.uniform(0.2, 0.3), 0.14, sh_lance, colf(rng), vein,
                z=0.05 + 0.2 * rng.rand(), nveins=5, **leaf_kw(rng))
    sk.fit()
    return sk, heads


def finish_flowers(seed):
    sk, heads = cell_flowers(seed)
    rng = np.random.RandomState(seed + 5)
    # recover the fitted head positions: the last cap of each stem path
    stems = [it for it in sk.items if it['k'] == 'cap' and abs(it['z'] - 0.02) < 1e-6]
    tips = [stems[i * 6 + 5]['p1'] for i in range(len(stems) // 6)]
    white = np.array([0.97, 0.97, 0.95], np.float32)
    for i, p in enumerate(tips):
        p = np.array(p)
        if p[1] < 0.56:
            p = p + np.array([0, 0.56 - p[1]])
        kind = i % 3
        R = rng.uniform(0.058, 0.074)
        if kind == 0:      # daisy: many narrow petals
            npet = 13
            for k in range(npet):
                a = 360.0 * k / npet + rng.uniform(-6, 6)
                sk.leaf(p, a, R * rng.uniform(0.9, 1.08), 0.20, sh_petal, white * rng.uniform(0.9, 1.0),
                        white * 0.86, z=0.8 + 0.1 * rng.rand(), nveins=0, fold=0.3, shadow=0.18, vein_amt=0.5)
            sk.cap(p, p + 1e-4, R * 0.27, R * 0.27, np.array([0.92, 0.80, 0.42], np.float32), z=1.0, rough=0.8,
                   shade=0.45, shadow=0.2)
        elif kind == 1:    # 5 broad petals
            for k in range(5):
                a = 90 + 72.0 * k + rng.uniform(-8, 8)
                sk.leaf(p, a, R * 1.05, 0.46, sh_petal, white * rng.uniform(0.9, 1.0), white * 0.84,
                        z=0.8 + 0.1 * rng.rand(), nveins=0, fold=0.35, shadow=0.2, vein_amt=0.6)
            sk.cap(p, p + 1e-4, R * 0.2, R * 0.2, np.array([0.95, 0.86, 0.55], np.float32), z=1.0, rough=0.8,
                   shade=0.45, shadow=0.2)
        else:              # bell cluster: 3 small cups
            for k in range(3):
                c = p + np.array([(k - 1) * 0.036, -abs(k - 1) * 0.02 + rng.uniform(-0.01, 0.01)])
                for a in (60, 90, 120):
                    sk.leaf(c - np.array([0, 0.02]), a + rng.uniform(-6, 6), R * 0.95, 0.36, sh_petal,
                            white * rng.uniform(0.88, 1.0), white * 0.84, z=0.8 + 0.1 * rng.rand(), nveins=0,
                            fold=0.3, shadow=0.2, vein_amt=0.5)
    return sk.render(zshade=(0.72, 1.04))


def cell_weeds(seed):
    sk = Sketch(seed)
    rng = sk.rng
    colf = col_fn(0.225, 0.52, 0.47, dh=0.03, ds=0.10, dv=0.08, alt=(0.14, 0.42, 0.56), alt_p=0.2)
    vein = hsv(0.2, 0.35, 0.62)
    n = 26
    for i in range(n):
        x = rng.uniform(-0.2, 0.2)
        a = 90 - x * 150 + rng.uniform(-12, 12)
        L = rng.uniform(0.35, 0.97) * (1.0 - 0.6 * abs(x))
        sk.leaf((x, 0.0), a, L, 0.021 / L * rng.uniform(0.7, 1.4), sh_blade, colf(rng), vein, nveins=0, rough=0.55,
                shadow=0.18, fold=0.35, bend=rng.uniform(-0.14, 0.14) - x * 0.3, tilt=(0.0, rng.uniform(-0.3, 0.3)),
                curl=0.0, hs=rng.choice([-1.0, 1.0]))
    # a few seed spikes
    for i in range(4):
        x = rng.uniform(-0.12, 0.12)
        a = 90 - x * 120 + rng.uniform(-8, 8)
        h = rng.uniform(0.75, 0.98)
        tip = np.array((x, 0.0)) + dirv(a) * h
        sk.cap((x, 0.0), tip, 0.0035, 0.002, hsv(0.15, 0.4, 0.55), z=0.4)
        for k in range(9):
            q = tip - dirv(a) * (0.02 + 0.018 * k)
            sd = 1 if k % 2 else -1
            sk.cap(q, q + dirv(a + sd * 28) * 0.03, 0.0045, 0.002, hsv(0.12, 0.42, 0.58 + 0.08 * rng.rand()),
                   z=0.95, rough=0.8)
    sk.fit(halfw=0.46)
    return sk.render(zshade=(0.66, 1.05))


CELLS = [
    # (col, row, name, fn)
    (0, 0, 'oak_twig_a', lambda: cell_oak_a(11)),
    (1, 0, 'oak_twig_b', lambda: cell_oak_b(23)),
    (2, 0, 'birch_twig', lambda: cell_birch(31)),
    (3, 0, 'willow_strands', lambda: cell_willow(41)),
    (0, 1, 'pine_spray_a', lambda: cell_pine_flat(51)),
    (1, 1, 'pine_spray_b', lambda: cell_pine_hang(61)),
    (2, 1, 'bush_sprig_a', lambda: cell_bush_a(71)),
    (3, 1, 'bush_sprig_b', lambda: cell_bush_b(81)),
    (0, 2, 'fern_frond', lambda: cell_fern(91)),
    (1, 2, 'reed_blades', lambda: cell_reeds(101)),
    (2, 2, 'flower_heads', lambda: finish_flowers(111)),
    (3, 2, 'weed_tuft', lambda: cell_weeds(121)),
    (0, 3, 'oak_dense', lambda: cell_oak_dense(131)),
    (1, 3, 'pine_dense', lambda: cell_pine_flat(141, dense=True)),
    (2, 3, 'birch_dense', lambda: cell_birch_dense(151)),
    (3, 3, 'willow_dense', lambda: cell_willow(161, dense=True)),
]


def main():
    only = None
    if '--' in sys.argv:
        only = set(sys.argv[sys.argv.index('--') + 1:])
    S = CELL * GRID
    path_a = os.path.join(TEXTURES, 'leaves_a.png')
    path_n = os.path.join(TEXTURES, 'leaves_n.png')
    if only and os.path.exists(path_a) and os.path.exists(path_n):
        alb = load_image(path_a)
        nrm = load_image(path_n)
    else:
        only = None
        alb = np.zeros((S, S, 4), np.float32)
        nrm = np.zeros((S, S, 4), np.float32)
        nrm[..., 0:2] = 0.5
        nrm[..., 2] = 0.6
        nrm[..., 3] = 1.0
    for (c, r, name, fn) in CELLS:
        if only and name not in only:
            continue
        rgb, A, nxy, rough = fn()
        ys, xs = slice(r * CELL, (r + 1) * CELL), slice(c * CELL, (c + 1) * CELL)
        alb[ys, xs, 0:3] = np.clip(rgb, 0, 1)
        alb[ys, xs, 3] = np.clip(A, 0, 1)
        fade = np.clip(A * 4.0, 0, 1)
        nrm[ys, xs, 0] = 0.5 + 0.5 * np.clip(nxy[..., 0] * fade, -1, 1)
        nrm[ys, xs, 1] = 0.5 + 0.5 * np.clip(nxy[..., 1] * fade, -1, 1)
        nrm[ys, xs, 2] = np.clip(rough, 0.2, 1.0)
        nrm[ys, xs, 3] = 1.0
        print('CELL %-16s coverage %.1f%%' % (name, 100.0 * float((A > 0.5).mean())))
    save_png(path_a, alb)
    save_png(path_n, nrm)
    print('WROTE', path_a)
    print('WROTE', path_n)
    # preview sheet: albedo over a dark background | alpha | normal (half res)
    def half(a):
        return a.reshape(S // 2, 2, S // 2, 2, a.shape[2]).mean(axis=(1, 3))
    bg = np.array([0.12, 0.13, 0.16], np.float32)
    comp = alb[..., :3] * alb[..., 3:4] + bg * (1 - alb[..., 3:4])
    # grid lines
    for k in range(1, GRID):
        comp[k * CELL - 1:k * CELL + 1, :, :] = 0.35
        comp[:, k * CELL - 1:k * CELL + 1, :] = 0.35
    raw = alb[..., :3].copy()        # shows the colour bleed
    sheet = montage([half(comp), half(raw), half(np.repeat(alb[..., 3:4], 3, axis=2)), half(nrm[..., :3])], cols=2)
    save_png(os.path.join(PREVIEWS, 'nat_leaves_atlas.png'), sheet)
    print('PREVIEW', os.path.join(PREVIEWS, 'nat_leaves_atlas.png'))


main()
