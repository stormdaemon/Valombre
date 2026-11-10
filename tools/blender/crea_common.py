"""Creature toolkit of VALOMBRE (shared by crea_wolf.py and crea_spider.py).

  * lofted cross-section tubes ("loft"), blobs and fur tufts with ANALYTIC skin weights / colours,
  * voxel union + smoothing + decimation of the organic parts, attribute transfer to the new surface,
  * a tiny FK / planar-IK pose solver that works on the armature rest matrices (no constraints),
  * keyframed tracks, clip baking (bone rotations + root location), preview strips and reports.

Blender coords: creature faces -Y, +X = its left, +Z up, feet on z = 0.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
import blcommon as _blc
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

FPS = 30
CREA_DIR = os.path.join(MODELS, 'creatures')
os.makedirs(CREA_DIR, exist_ok=True)
V = Vector
XA, YA, ZA = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


# ----------------------------------------------------------------------------- small math
def rad(d):
    return d * math.pi / 180.0


def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def lerp(a, b, t):
    return a + (b - a) * t


def sstep(x):
    x = clamp(x)
    return x * x * (3.0 - 2.0 * x)


def ramp(x, a, b):
    """0 below a, 1 above b, smoothstep in between."""
    if a == b:
        return 1.0 if x >= b else 0.0
    return sstep((x - a) / (b - a))


def bump(x, a, b, p=1.0):
    """0 outside [a, b], smooth hump (sin^2) peaking at 1 in the middle."""
    if x <= a or x >= b:
        return 0.0
    return math.sin(math.pi * (x - a) / (b - a)) ** (2.0 * p)


def frac(x):
    return x - math.floor(x)


def RX(deg):
    return Quaternion(XA, rad(deg))


def RY(deg):
    return Quaternion(YA, rad(deg))


def RZ(deg):
    return Quaternion(ZA, rad(deg))


def tr(t, keys, mode='s'):
    """Keyframed track. keys = [(time, value[, mode]), ...] sorted by time; value = float or tuple.
    The easing of a segment is the mode of the key ENDING it (default `mode`):
      's' smoothstep  'l' linear  'i' ease-in (slow start)  'o' ease-out (slow end)
      'I' / 'O' stronger cubic versions  'c' C1 cubic through the keys (overshoots a little)  'h' hold."""
    n = len(keys)
    if t <= keys[0][0]:
        v = keys[0][1]
        return float(v) if np.isscalar(v) else np.asarray(v, float)
    if t >= keys[-1][0]:
        v = keys[-1][1]
        return float(v) if np.isscalar(v) else np.asarray(v, float)
    i = 0
    while i < n - 2 and t > keys[i + 1][0]:
        i += 1
    t0, t1 = keys[i][0], keys[i + 1][0]
    v0, v1 = np.asarray(keys[i][1], float), np.asarray(keys[i + 1][1], float)
    m = keys[i + 1][2] if len(keys[i + 1]) > 2 else mode
    x = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
    if m == 'c':
        def tang(j):
            if j <= 0 or j >= n - 1:
                return np.zeros_like(v0)
            return (np.asarray(keys[j + 1][1], float) - np.asarray(keys[j - 1][1], float)) / (keys[j + 1][0] - keys[j - 1][0])
        dt = t1 - t0
        m0, m1 = tang(i), tang(i + 1)
        x2, x3 = x * x, x * x * x
        out = (2 * x3 - 3 * x2 + 1) * v0 + (x3 - 2 * x2 + x) * dt * m0 + (-2 * x3 + 3 * x2) * v1 + (x3 - x2) * dt * m1
    else:
        if m == 'l':
            w = x
        elif m == 'i':
            w = x * x
        elif m == 'o':
            w = 1 - (1 - x) ** 2
        elif m == 'I':
            w = x ** 3
        elif m == 'O':
            w = 1 - (1 - x) ** 3
        elif m == 'h':
            w = 0.0
        else:
            w = x * x * (3 - 2 * x)
        out = v0 + (v1 - v0) * w
    return float(out) if out.ndim == 0 else out


def hermite(x, p0, p1, m0, m1):
    x2, x3 = x * x, x * x * x
    return (2 * x3 - 3 * x2 + 1) * p0 + (x3 - 2 * x2 + x) * m0 + (-2 * x3 + 3 * x2) * p1 + (x3 - x2) * m1


# ----------------------------------------------------------------------------- lofts
def cr_resample(P, sub):
    """Catmull-Rom resampling of the rows of P (m, k). Returns (rows, params in row-index units)."""
    P = np.asarray(P, float)
    m = len(P)
    rows, us = [], []
    for i in range(m - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, m - 1)]
        for j in range(sub):
            t = j / sub
            t2, t3 = t * t, t * t * t
            rows.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
            us.append(i + t)
    rows.append(P[-1])
    us.append(float(m - 1))
    return np.array(rows), np.array(us)


def S(c, rx, ry, ex=2.0, tap=0.0):
    """One loft section: centre, half width, half height (float or (positive side, negative side)),
    superellipse exponent, taper (>0 narrows the negative-`up` side, <0 the positive side)."""
    if isinstance(ry, (tuple, list)):
        ryp, ryn = ry
    else:
        ryp = ryn = ry
    return (c[0], c[1], c[2], rx, ryp, ryn, ex, tap)


def loft(secs, n=16, sub=3, caps=(0.6, 0.6), side=(1, 0, 0), cup=0.0, phase=0.0):
    """Tube through the sections `secs` (list of S(...)). Ring frame: right = `side` made perpendicular to
    the path tangent, up = tangent x right (path going -Y -> up = +Z; path going -Z -> up = -Y (front)).
    caps = (start, end) dome roundness (0 = flat fan, None = open). cup > 0 makes the +up side concave
    (ears). Returns (verts (N,3), faces, u (path param in section-index units), theta)."""
    R, U = cr_resample(np.array(secs, float), sub)
    C = R[:, :3]
    T = np.gradient(C, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    side = Vector(side)
    verts, vu, vth, rings = [], [], [], []

    def ring(c, t, rx, ryp, ryn, ex, tap, u):
        t = Vector(t)
        r = side - t * side.dot(t)
        r.normalize()
        up = t.cross(r)
        idx = []
        for j in range(n):
            th = 2 * math.pi * (j + phase) / n
            cs, sn = math.cos(th), math.sin(th)
            cx = math.copysign(abs(cs) ** (2.0 / ex), cs)
            sy = math.copysign(abs(sn) ** (2.0 / ex), sn)
            fx = 1.0
            if tap > 0:
                fx = 1 - tap * (1 - sy) * 0.5
            elif tap < 0:
                fx = 1 + tap * (1 + sy) * 0.5
            if cup and sn > 0:
                y = -cup * ryn * sn
            else:
                y = (ryp if sy >= 0 else ryn) * sy
            p = Vector(c) + r * (rx * cx * fx) + up * y
            idx.append(len(verts))
            verts.append(p)
            vu.append(u)
            vth.append(th)
        return idx

    def dome(row, t, sgn, k, u):
        """extra shrinking rings + pole beyond an end ring; returns list of rings (outer->inner) and pole."""
        c = Vector(row[:3])
        rx, ryp, ryn, ex, tap = row[3], row[4], row[5], row[6], row[7]
        rm = min(rx, 0.5 * (ryp + ryn))
        out = []
        if k and k > 0:
            for sc, off in ((0.80, 0.30), (0.45, 0.52)):
                out.append(ring(c + Vector(t) * (sgn * off * k * rm), t, max(rx * sc, 1e-4), ryp * sc, ryn * sc, ex, tap, u))
            pole = c + Vector(t) * (sgn * 0.62 * k * rm)
        else:
            pole = c
        pi = len(verts)
        verts.append(pole)
        vu.append(u)
        vth.append(0.0)
        return out, pi

    start = None
    if caps[0] is not None:
        start = dome(R[0], T[0], -1.0, caps[0], U[0])
        for rg in reversed(start[0]):
            rings.append(rg)
    for i, row in enumerate(R):
        rings.append(ring(row[:3], T[i], max(row[3], 1e-4), max(row[4], 1e-4), max(row[5], 1e-4), row[6], row[7], U[i]))
    end = None
    if caps[1] is not None:
        end = dome(R[-1], T[-1], 1.0, caps[1], U[-1])
        for rg in end[0]:
            rings.append(rg)
    faces = []
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            faces.append((a[j], a[k], b[k], b[j]))
    if start is not None:
        a = rings[0]
        for j in range(n):
            faces.append((start[1], a[(j + 1) % n], a[j]))
    if end is not None:
        a = rings[-1]
        for j in range(n):
            faces.append((end[1], a[j], a[(j + 1) % n]))
    return np.array([tuple(v) for v in verts], float), faces, np.array(vu), np.array(vth)


def blob(c, r, rot=None, n=12, m=6):
    """Ellipsoid (radii r = (x, y, z)), optionally rotated by a 3x3 Matrix / Euler tuple in degrees."""
    secs = []
    for i in range(m + 1):
        ph = math.pi * (0.10 + 0.80 * i / m)
        secs.append(S((0, -r[1] * math.cos(ph), 0), r[0] * math.sin(ph), r[2] * math.sin(ph)))
    v, f, u, th = loft(secs, n=n, sub=1, caps=(1.0, 1.0))
    if rot is not None:
        Rm = rot if isinstance(rot, Matrix) else Euler([rad(a) for a in rot]).to_matrix()
        v = v @ np.array(Rm).T
    v = v + np.array(c, float)
    return v, f, u, th


def tuft(base, d, L, r, n=7, bend=(0, 0, 0), flat=1.0, side=(1, 0, 0), sub=2):
    """Teardrop fur spike / bristle from `base` along `d`, curving toward `bend` (vector, fraction of L).
    The root is sunk behind the base so that it fuses with the body in the union."""
    d = Vector(d).normalized()
    b = Vector(bend)
    base = Vector(base)
    secs = []
    for t, k in ((-0.30, 0.75), (0.0, 1.0), (0.30, 0.86), (0.60, 0.58), (0.85, 0.28), (1.0, 0.04)):
        c = base + d * (L * t) + b * (L * t * abs(t))
        secs.append(S(c, r * k, r * k * flat))
    sd = Vector(side)
    if abs(sd.dot(d)) > 0.9:
        sd = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
    return loft(secs, n=n, sub=sub, caps=(0.5, 0.3), side=sd)


def cone(base, tip, r, n=5, curve=(0, 0, 0), flat=1.0, side=(1, 0, 0), segs=1, capped=False):
    """Low-poly (optionally curved) cone: teeth, claws, spikes. `segs` rings then ONE apex vertex."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    L = d.length
    t = d.normalized()
    sd = Vector(side)
    if abs(sd.dot(t)) > 0.9:
        sd = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
    rgt = (sd - t * sd.dot(t)).normalized()
    up = t.cross(rgt)
    verts, faces, rings = [], [], []
    for i in range(segs):
        s = i / segs
        c = base + d * s + Vector(curve) * (L * math.sin(math.pi * s) * 0.5)
        k = 1.0 - s * 0.8
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            ring.append(len(verts))
            verts.append(c + rgt * (r * k * math.cos(a)) + up * (r * k * flat * math.sin(a)))
        rings.append(ring)
    apex = len(verts)
    verts.append(tip)
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            faces.append((a[j], a[k], b[k], b[j]))
    last = rings[-1]
    for j in range(n):
        faces.append((last[j], last[(j + 1) % n], apex))
    if capped:
        ci = len(verts)
        verts.append(base)
        for j in range(n):
            faces.append((ci, rings[0][(j + 1) % n], rings[0][j]))
    nv = len(verts)
    return np.array([tuple(v) for v in verts], float), faces, np.zeros(nv), np.zeros(nv)


def dome(center, normal, r, n=8, rings=2, flat=1.0):
    """Hemisphere facing `normal` (eyes): equator ring + `rings` rings + pole."""
    c, nr = Vector(center), Vector(normal).normalized()
    sd = XA if abs(nr.dot(XA)) < 0.9 else ZA
    rgt = (sd - nr * sd.dot(nr)).normalized()
    up = nr.cross(rgt)
    verts, faces, rg = [], [], []
    for i in range(rings + 1):
        ph = (math.pi / 2) * i / (rings + 1)
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            ring.append(len(verts))
            verts.append(c + (rgt * math.cos(a) + up * math.sin(a)) * (r * math.cos(ph)) + nr * (r * flat * math.sin(ph)))
        rg.append(ring)
    apex = len(verts)
    verts.append(c + nr * (r * flat))
    for a, b in zip(rg[:-1], rg[1:]):
        for j in range(n):
            k = (j + 1) % n
            faces.append((a[j], a[k], b[k], b[j]))
    for j in range(n):
        faces.append((rg[-1][j], rg[-1][(j + 1) % n], apex))
    nv = len(verts)
    u = np.array([i // n for i in range(nv - 1)] + [rings + 1], float)
    return np.array([tuple(v) for v in verts], float), faces, u, np.zeros(nv)


def mesh_obj(name, v, f, smooth=True):
    ob = new_mesh_object(name, [tuple(p) for p in v], f, smooth=smooth)
    return ob


def recalc_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


# ----------------------------------------------------------------------------- weights helpers
def seqw(first, steps):
    """Sequential hand-over along a chain: steps = [(t1, bone1), (t2, bone2), ...] where t_i in 0..1 says
    how far the point is past joint i. Returns {bone: weight}."""
    out = {}
    rem = 1.0
    names = [first] + [b for _, b in steps]
    ts = [t for t, _ in steps] + [0.0]
    # weight(b_i) = t_i * (1 - t_{i+1}), with t_0 = 1
    tprev = 1.0
    for i, nm in enumerate(names):
        w = tprev * (1.0 - ts[i])
        if w > 1e-5:
            out[nm] = out.get(nm, 0.0) + w
        tprev = tprev * ts[i] if i < len(ts) else 0.0
    return out


def chainw(x, bones, joints, blend):
    """1D chain weights: bones[i-1] hands over to bones[i] around coordinate joints[i-1] (half width blend)."""
    if not isinstance(blend, (list, tuple)):
        blend = [blend] * len(joints)
    return seqw(bones[0], [(ramp(x, j - b, j + b), bones[i + 1]) for i, (j, b) in enumerate(zip(joints, blend))])


def planew(p, first, joints):
    """joints = [(bone, point, normal, half_width_before, half_width_after), ...]: bone takes over when the
    point passes the plane (point, normal)."""
    steps = []
    for bone, J, nrm, b0, b1 in joints:
        s = (Vector(p) - Vector(J)).dot(Vector(nrm).normalized())
        steps.append((ramp(s, -b0, b1), bone))
    return seqw(first, steps)


def bisector(a, j, b):
    """Normal of the plane splitting the joint j between segments a->j and j->b."""
    d = (Vector(j) - Vector(a)).normalized() + (Vector(b) - Vector(j)).normalized()
    return d.normalized()


# ----------------------------------------------------------------------------- builder
class Builder:
    """Collects source parts with per-vertex weights (dense matrix over `bones`) and colours."""

    def __init__(self, bones):
        self.bones = list(bones)
        self.bi = {b: i for i, b in enumerate(self.bones)}
        self.parts = []

    def add(self, part, wfn, cfn=1.0, group='union', mat='M_fur', name='p'):
        v, f, u, th = part
        nb = len(self.bones)
        W = np.zeros((len(v), nb), np.float32)
        C = np.ones((len(v), 3), np.float32)
        for i in range(len(v)):
            p = Vector(v[i])
            w = wfn(p, u[i], th[i]) if callable(wfn) else wfn
            if isinstance(w, str):
                W[i, self.bi[w]] = 1.0
            else:
                for k, x in w.items():
                    W[i, self.bi[k]] += x
            c = cfn(p, u[i], th[i]) if callable(cfn) else cfn
            C[i] = c if hasattr(c, '__len__') else (c, c, c)
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
        d = dict(name=name, group=group, mat=mat, v=np.asarray(v, float), f=list(f), W=W, C=C)
        self.parts.append(d)
        return d

    def group(self, g):
        return [p for p in self.parts if p['group'] == g]

    def object(self, g, name=None, smooth=True):
        """Merge the parts of group g into ONE object (plain concatenation, topology kept).
        Returns (object, W, C)."""
        ps = self.group(g)
        vs, fs, Ws, Cs, off = [], [], [], [], 0
        for p in ps:
            vs.append(p['v'])
            fs += [tuple(i + off for i in f) for f in p['f']]
            Ws.append(p['W'])
            Cs.append(p['C'])
            off += len(p['v'])
        v = np.concatenate(vs)
        ob = mesh_obj(name or g, v, fs, smooth=smooth)
        recalc_normals_islands(ob)
        return ob, np.concatenate(Ws), np.concatenate(Cs)

    def union(self, name, voxel=0.008, smooth=(1, 5), tris=4500, keep_fn=None, sym=True, group='union',
              keep_factor=3e-4):
        """Voxel-union the parts of `group`, smooth, decimate to ~tris, transfer weights / colours."""
        t0 = time.time()
        objs = []
        for p in self.group(group):
            ob = mesh_obj('u_' + p['name'], p['v'], p['f'])
            recalc_normals(ob)
            objs.append(ob)
        ob = join(objs, name)
        m = ob.modifiers.new('rm', 'REMESH')
        m.mode = 'VOXEL'
        m.voxel_size = voxel
        m.adaptivity = 0.0
        m.use_smooth_shade = True
        apply_modifiers(ob)
        keep_largest_island(ob)
        smooth_mesh(ob, plain=smooth[0], taubin=smooth[1])
        n0 = tri_count(ob)
        decimate_to(ob, tris, keep_fn, sym, keep_factor)
        src_v = np.concatenate([p['v'] for p in self.group(group)])
        src_W = np.concatenate([p['W'] for p in self.group(group)])
        src_C = np.concatenate([p['C'] for p in self.group(group)])
        W, C = transfer(ob, src_v, src_W, src_C)
        for pl in ob.data.polygons:
            pl.use_smooth = True
        print('UNION %s: remesh %d tris -> %d tris, %d verts (%.1fs)' % (name, n0, tri_count(ob), len(ob.data.vertices), time.time() - t0))
        return ob, W, C


def recalc_normals_islands(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def keep_largest_island(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    islands = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        seen.add(v.index)
        isl = []
        while stack:
            x = stack.pop()
            isl.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    if len(islands) > 1:
        print('  islands:', [len(i) for i in islands[:6]])
        dead = [v for isl in islands[1:] for v in isl]
        bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()


def _mesh_arrays(me):
    n = len(me.vertices)
    co = np.empty(n * 3, np.float64)
    me.vertices.foreach_get('co', co)
    ed = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ed)
    return co.reshape(n, 3), ed.reshape(-1, 2)


def smooth_mesh(ob, plain=1, taubin=5, lam=0.5, mu=-0.53, fac=None):
    me = ob.data
    co, ed = _mesh_arrays(me)
    deg = np.maximum(np.bincount(ed.ravel(), minlength=len(co)), 1)[:, None]

    def lap(c):
        s = np.zeros_like(c)
        np.add.at(s, ed[:, 0], c[ed[:, 1]])
        np.add.at(s, ed[:, 1], c[ed[:, 0]])
        return s / deg - c
    f = 1.0 if fac is None else fac[:, None]
    for _ in range(plain):
        co = co + lam * f * lap(co)
    for _ in range(taubin):
        co = co + lam * f * lap(co)
        co = co + mu * f * lap(co)
    me.vertices.foreach_set('co', co.ravel())
    me.update()


def decimate_to(ob, tris, keep_fn=None, sym=True, factor=3e-4):
    """Quadric collapse to ~tris. keep_fn(co) -> 0..1: detail priority (1 = collapse ~5x later).
    Blender adds edge_length * (1/f1 + 1/f2) * factor to the quadric cost (f = group weight), so the
    factor must stay tiny or the shape error is ignored."""
    me = ob.data
    cur = tri_count(ob)
    if keep_fn is not None:
        vg = ob.vertex_groups.new(name='keep')
        for v in me.vertices:
            vg.add([v.index], 1.0 - 0.8 * clamp(keep_fn(v.co)), 'REPLACE')
    m = ob.modifiers.new('dec', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = min(1.0, tris / max(cur, 1))
    m.use_collapse_triangulate = True
    if sym:
        m.use_symmetry = True
        m.symmetry_axis = 'X'
    if keep_fn is not None:
        m.vertex_group = 'keep'
        m.vertex_group_factor = factor
        m.invert_vertex_group = False
    apply_modifiers(ob)
    if keep_fn is not None:
        ob.vertex_groups.remove(ob.vertex_groups['keep'])


def transfer(ob, src_v, src_W, src_C, k=4):
    kd = KDTree(len(src_v))
    for i, p in enumerate(src_v):
        kd.insert(p, i)
    kd.balance()
    me = ob.data
    W = np.zeros((len(me.vertices), src_W.shape[1]), np.float32)
    C = np.zeros((len(me.vertices), 3), np.float32)
    for v in me.vertices:
        res = kd.find_n(v.co, k)
        ws = np.array([1.0 / (d * d + 1e-7) for _, _, d in res])
        ws /= ws.sum()
        idx = [i for _, i, _ in res]
        W[v.index] = (src_W[idx] * ws[:, None]).sum(0)
        C[v.index] = (src_C[idx] * ws[:, None]).sum(0)
    return W, C


def smooth_weights(ob, W, iters=3, lam=0.5, lock=None):
    """Laplacian smoothing of the weight matrix over mesh edges. lock: bool mask of vertices kept as is."""
    co, ed = _mesh_arrays(ob.data)
    deg = np.maximum(np.bincount(ed.ravel(), minlength=len(co)), 1)[:, None]
    for _ in range(iters):
        s = np.zeros_like(W)
        np.add.at(s, ed[:, 0], W[ed[:, 1]])
        np.add.at(s, ed[:, 1], W[ed[:, 0]])
        Wn = W + lam * (s / deg - W)
        if lock is not None:
            Wn[lock] = W[lock]
        W = Wn
    return W


def write_weights(ob, W, bones, arm=None, maxinf=4, thresh=0.015):
    """Keep the `maxinf` strongest influences per vertex, normalise, write vertex groups (+ armature mod)."""
    W = W.copy()
    W[W < thresh] = 0.0
    order = np.argsort(-W, axis=1)
    mask = np.zeros_like(W, bool)
    np.put_along_axis(mask, order[:, :maxinf], True, axis=1)
    W[~mask] = 0.0
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    for vg in list(ob.vertex_groups):
        ob.vertex_groups.remove(vg)
    for bi, b in enumerate(bones):
        col = W[:, bi]
        nz = np.nonzero(col > 0)[0]
        if len(nz) == 0:
            continue
        vg = ob.vertex_groups.new(name=b)
        for i in nz:
            vg.add([int(i)], float(col[i]), 'REPLACE')
    if arm is not None:
        if not any(m.type == 'ARMATURE' for m in ob.modifiers):
            mod = ob.modifiers.new('Armature', 'ARMATURE')
            mod.object = arm
        ob.parent = arm
    return W


def write_colors(ob, C, name='Col'):
    me = ob.data
    attr = me.color_attributes.get(name) or me.color_attributes.new(name, 'FLOAT_COLOR', 'CORNER')
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    col = np.ones((len(me.loops), 4), np.float32)
    col[:, :3] = np.clip(C, 0, 1)[vi]
    attr.data.foreach_set('color', col.ravel())
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = list(me.color_attributes).index(attr)


def activate_colors(ob, name='Col'):
    me = ob.data
    attr = me.color_attributes.get(name)
    if attr:
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = list(me.color_attributes).index(attr)


def _fib_dirs(n):
    out = []
    for i in range(n):
        z = (i + 0.5) / n                 # hemisphere
        r = math.sqrt(1 - z * z)
        a = i * 2.399963
        out.append((r * math.cos(a), r * math.sin(a), z))
    return out


def bake_ao(objs, rays=28, dist=0.35, bias=0.004, ground=None):
    """Per-vertex ambient occlusion (1 = open) of every object against all of them. Returns list of arrays."""
    verts, polys, off = [], [], 0
    for ob in objs:
        me = ob.data
        mw = ob.matrix_world
        verts += [mw @ v.co for v in me.vertices]
        polys += [tuple(i + off for i in p.vertices) for p in me.polygons]
        off += len(me.vertices)
    if ground is not None:
        g = ground
        verts += [Vector((-9, -9, g)), Vector((9, -9, g)), Vector((9, 9, g)), Vector((-9, 9, g))]
        polys.append((off, off + 1, off + 2, off + 3))
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = _fib_dirs(rays)
    out = []
    for ob in objs:
        me = ob.data
        ao = np.ones(len(me.vertices), np.float32)
        for v in me.vertices:
            nrm = v.normal
            if nrm.length < 1e-6:
                continue
            q = Vector((0, 0, 1)).rotation_difference(nrm)
            o = v.co + nrm * bias
            occ = 0.0
            for d in dirs:
                dv = q @ Vector(d)
                hit = bvh.ray_cast(o, dv, dist)
                if hit[0] is not None:
                    occ += (1.0 - hit[3] / dist) * d[2] * 1.6 + 0.2
            ao[v.index] = 1.0 - min(1.0, occ / rays)
        out.append(ao)
    return out


def vnoise(p, f=6.0, seed=0.0):
    """Cheap smooth pseudo noise in -1..1."""
    x, y, z = p[0] * f + seed, p[1] * f + seed * 1.7, p[2] * f - seed
    return (math.sin(x * 1.7 + math.sin(y * 2.3 + 1.3) * 1.5) * math.cos(z * 1.9 + math.sin(x * 1.1) * 1.2)
            + 0.5 * math.sin(y * 3.1 + z * 2.7 + math.sin(x * 2.9))) / 1.5


# ----------------------------------------------------------------------------- rig + pose solver
class Rig:
    def __init__(self):
        self.defs = []

    def bone(self, name, head, tail, parent=None, zref=None, deform=True):
        self.defs.append(dict(name=name, head=Vector(head), tail=Vector(tail), parent=parent, zref=zref, deform=deform))

    def mirror(self, name, head, tail, parent=None, zref=None, deform=True):
        """Adds name_L (as given, +X) and name_R (mirrored). A parent ending with '_S' is mirrored too."""
        for sfx, sx in (('_L', 1.0), ('_R', -1.0)):
            par = parent[:-2] + sfx if parent and parent.endswith('_S') else parent
            zr = None if zref is None else (zref[0] * sx, zref[1], zref[2])
            self.bone(name + sfx, (head[0] * sx, head[1], head[2]), (tail[0] * sx, tail[1], tail[2]), par, zr, deform)

    def build(self, name='Armature'):
        ad = bpy.data.armatures.new(name)
        ob = bpy.data.objects.new(name, ad)
        link(ob)
        select_only(ob)
        bpy.ops.object.mode_set(mode='EDIT')
        for b in self.defs:
            eb = ad.edit_bones.new(b['name'])
            eb.head, eb.tail = b['head'], b['tail']
            d = (b['tail'] - b['head']).normalized()
            if b['zref'] is not None:
                eb.align_roll(Vector(b['zref']))
            else:
                # default: local X = armature +X whenever the bone lies in a sagittal plane
                z = XA.cross(d)
                eb.align_roll(z if z.length > 1e-3 else Vector((0, -1, 0)))
            eb.use_deform = b['deform']
            if b['parent']:
                eb.parent = ad.edit_bones[b['parent']]
                eb.use_connect = False
        bpy.ops.object.mode_set(mode='OBJECT')
        for pb in ob.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        ad.display_type = 'STICK'
        self.obj = ob
        self.names = [b['name'] for b in self.defs]
        self.parent = {b['name']: b['parent'] for b in self.defs}
        self.rest = {n: ad.bones[n].matrix_local.copy() for n in self.names}
        self.rest_inv = {n: self.rest[n].inverted() for n in self.names}
        self.rest_rot = {n: self.rest[n].to_3x3() for n in self.names}
        self.rel = {n: (self.rest_inv[self.parent[n]] @ self.rest[n]) if self.parent[n] else self.rest[n].copy()
                    for n in self.names}
        self.rel_rot = {n: self.rel[n].to_3x3() for n in self.names}
        self.length = {n: ad.bones[n].length for n in self.names}
        self.h = {b['name']: b['head'].copy() for b in self.defs}
        self.t = {b['name']: b['tail'].copy() for b in self.defs}
        return ob


class Pose:
    def __init__(self, rig):
        self.rig = rig
        self.q = {n: Quaternion() for n in rig.names}
        self.loc = {}
        self.world = {}
        self.clamped = 0
        self.clamp_log = []

    def fk(self):
        rig = self.rig
        for n in rig.names:
            basis = self.q[n].to_matrix().to_4x4()
            if n in self.loc:
                basis = Matrix.Translation(self.loc[n]) @ basis
            p = rig.parent[n]
            self.world[n] = (self.world[p] @ rig.rel[n] @ basis) if p else (rig.rel[n] @ basis)
        return self

    def head(self, n):
        return self.world[n].translation.copy()

    def tail(self, n):
        return self.world[n] @ Vector((0, self.rig.length[n], 0))

    def rot(self, n):
        return self.world[n].to_3x3()

    def carry(self, n, p_rest):
        """Rest-space point carried rigidly by bone n."""
        return self.world[n] @ (self.rig.rest_inv[n] @ Vector(p_rest))

    def carry_dir(self, n, d_rest):
        return (self.world[n].to_3x3() @ self.rig.rest_inv[n].to_3x3()) @ Vector(d_rest)

    def delta(self, n, Q):
        """Rotate bone n by Q (expressed in armature axes, relative to its parent-carried rest orientation)."""
        R = self.rig.rest_rot[n].to_quaternion()
        self.q[n] = R.inverted() @ Q @ R

    def move(self, n, d):
        """Translate bone n by d (armature axes, as carried by the parent)."""
        self.loc[n] = self.rig.rest_rot[n].inverted() @ Vector(d)

    def set_world_rot(self, n, Rw, parent_rot=None):
        p = self.rig.parent[n]
        Rp = parent_rot if parent_rot is not None else (self.world[p].to_3x3() if p else Matrix.Identity(3))
        self.q[n] = ((Rp @ self.rig.rel_rot[n]).inverted() @ Rw).to_quaternion()

    def blend(self, other, w, bones=None):
        """self <- slerp(self, other, w) for the given bones (default all)."""
        for n in (bones or self.rig.names):
            self.q[n] = self.q[n].slerp(other.q[n], w)
        return self


def frame_mat(d, n):
    """3x3 whose columns are (n, d, n x d), n re-orthogonalised against d."""
    d = d.normalized()
    n = (n - d * n.dot(d)).normalized()
    z = n.cross(d)
    return Matrix((n, d, z)).transposed()


class PlanarLeg:
    """Leg solved in a plane: bones[0:2] = analytic 2-bone IK, the following bones are driven by absolute
    in-plane angles (measured from straight DOWN, positive toward the plane's `f` axis).
    plane='x'      (mammal): plane normal stays as close as possible to the body's lateral axis; f = forward.
    plane='radial' (spider): vertical plane through the leg root and the foot; f = horizontal outward."""

    def __init__(self, rig, bones, plane='x'):
        self.rig, self.bones, self.plane = rig, bones, plane
        J = [rig.h[b] for b in bones] + [rig.t[bones[-1]]]
        self.J0 = J
        self.L = [(J[i + 1] - J[i]).length for i in range(len(bones))]
        self.S0, self.tip0 = J[0], J[-1]
        n0, f0, u0 = self.basis(self.S0, self.tip0, XA, ZA)
        self.n0 = n0
        self.O, self.th0 = {}, []
        for i, b in enumerate(bones):
            d = (J[i + 1] - J[i]).normalized()
            assert abs(d.dot(n0)) < 2e-3, ('leg not planar', b, d.dot(n0))
            self.O[b] = frame_mat(d, n0).inverted() @ rig.rest_rot[b]
            self.th0.append(math.atan2(d.dot(f0), -d.dot(u0)))
        a = (J[2] - J[0]).normalized()
        self.bend = 1.0 if (J[1] - J[0]).dot(n0.cross(a)) >= 0 else -1.0
        a = self.tip0 - self.S0
        self.beta0 = math.atan2(a.dot(f0), -a.dot(u0))
        self.len0 = a.length

    def basis(self, Sp, tip, xref, zref):
        if self.plane == 'x':
            a = (tip - Sp).normalized()
            n = (xref - a * xref.dot(a)).normalized()
            u = (zref - n * zref.dot(n)).normalized()
            f = n.cross(u)
        else:
            h = tip - Sp
            h = h - zref * h.dot(zref)
            f = h.normalized()
            u = zref.normalized()
            n = u.cross(f)
        return n, f, u

    def beta(self, pose, tip, xref=XA, zref=ZA):
        """Angle of the root->tip line from straight down (positive toward f), and its length."""
        Sp = pose.head(self.bones[0])
        n, f, u = self.basis(Sp, tip, xref, zref)
        a = tip - Sp
        return math.atan2(a.dot(f), -a.dot(u)), a.length

    def solve(self, pose, tip, angles, xref=XA, zref=ZA):
        """angles: absolute in-plane angles (radians) of bones[2:]. pose.fk() must be up to date for the
        parent of bones[0]. Returns the reached tip position."""
        b = self.bones
        L = self.L
        Sp = pose.head(b[0])
        n, f, u = self.basis(Sp, Vector(tip), xref, zref)
        dirs = [None] * len(b)
        P = Vector(tip)
        for i in range(len(b) - 1, 1, -1):
            th = angles[i - 2]
            d = f * math.sin(th) - u * math.cos(th)
            dirs[i] = d
            P = P - d * L[i]
        a = P - Sp
        dist = a.length
        maxd = (L[0] + L[1]) * 0.9992
        mind = abs(L[0] - L[1]) * 1.02 + 1e-4
        if dist > maxd:
            pose.clamped += 1
            pose.clamp_log.append((b[0], round(dist - maxd, 3)))
            dist = maxd
        if dist < mind:
            dist = mind
        ah = a.normalized()
        x = (L[0] ** 2 - L[1] ** 2 + dist * dist) / (2 * dist)
        hh = math.sqrt(max(L[0] ** 2 - x * x, 0.0))
        ph = n.cross(ah)
        E = Sp + ah * x + ph * (hh * self.bend)
        Wp = Sp + ah * dist
        dirs[0] = (E - Sp).normalized()
        dirs[1] = (Wp - E).normalized()
        par = self.rig.parent[b[0]]
        Rp = pose.world[par].to_3x3()
        P = Wp
        for i, bn in enumerate(b):
            Rw = frame_mat(dirs[i], n) @ self.O[bn]
            pose.set_world_rot(bn, Rw, Rp)
            Rp = Rw
            if i >= 2:
                P = P + dirs[i] * L[i]
        return P


# ----------------------------------------------------------------------------- baking / previews
def bake_clip(arm, rig, name, duration, fn, loop=False, loc_bones=('hips',)):
    """fn(t seconds) -> Pose. Keys every bone rotation (+ location of loc_bones) on every frame 0..N."""
    act = new_action(arm, name)
    n = int(round(duration * FPS))
    prev = {}
    clamped = 0
    log = []
    pbs = {b: arm.pose.bones[b] for b in rig.names}
    for fr in range(n + 1):
        t = 0.0 if (loop and fr == n) else fr / FPS
        pose = fn(t)
        clamped += pose.clamped
        log += [(fr,) + c for c in pose.clamp_log]
        for b in rig.names:
            q = pose.q[b].normalized()
            if b in prev and prev[b].dot(q) < 0:
                q = -q
            prev[b] = q
            pb = pbs[b]
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=fr)
            if b in loc_bones:
                pb.location = pose.loc.get(b, Vector((0, 0, 0)))
                pb.keyframe_insert('location', frame=fr)
    if clamped:
        print('  [%s] IK clamped %d times (frame, leg, missing m):' % (name, clamped), log[:14])
    return act, n


def eval_verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    oe.to_mesh_clear()
    return co.reshape(-1, 3)


def clip_report(name, mesh, nfr):
    """Lowest / highest point of the deformed mesh over the clip (ground penetration check)."""
    sc = bpy.context.scene
    zmin, zmin_f, zmin_v, lows = 1e9, 0, 0, []
    for fr in range(nfr + 1):
        sc.frame_set(fr)
        co = eval_verts(mesh)
        vi = int(co[:, 2].argmin())
        z = float(co[vi, 2])
        lows.append(z)
        if z < zmin:
            zmin, zmin_f, zmin_v = z, fr, vi
    who = ''
    if zmin < -0.012 and zmin_v < len(mesh.data.vertices):
        gs = sorted(mesh.data.vertices[zmin_v].groups, key=lambda g: -g.weight)
        who = ' <- ' + ', '.join('%s %.2f' % (mesh.vertex_groups[g.group].name, g.weight) for g in gs[:3])
        who += ' rest co (%.3f, %.3f, %.3f)' % tuple(mesh.data.vertices[zmin_v].co)
    print('  [%s] lowest vertex z: min %.3f (frame %d), max-of-min %.3f%s' % (name, zmin, zmin_f, max(lows), who))
    return zmin, max(lows)


def ensure_ground(size=8.0, z=0.0):
    ob = bpy.data.objects.get('pv_ground')
    if ob is None:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        ob = bmesh_to_object(bm, 'pv_ground', smooth=False)
        ob.scale = (size, size, 0.04)
        ob.location = (0, 0, z - 0.02)
        assign_mat(ob, make_mat('pv_ground_mat', (0.035, 0.04, 0.035), rough=0.95))
    return ob


def render_strip(path, objs, nfr, count=8, loop=False, views=('left',), res=(400, 320), bounds=None, cols=4):
    """Contact sheet: one row per view, `count` evenly spaced frames per row."""
    if loop:
        frames = [int(round(i * nfr / count)) for i in range(count)]
    else:
        frames = [int(round(i * nfr / (count - 1))) for i in range(count)]
    cam = setup_preview(res)
    sc = bpy.context.scene
    imgs = []
    for v in views:
        for fr in frames:
            sc.frame_set(fr)
            bpy.context.view_layer.update()
            mn, mx = bounds if bounds else _blc._bounds(objs)
            fit_camera(cam, Vector(mn), Vector(mx), v, margin=1.03)
            imgs.append(render_to_array())
    save_png(path, montage(imgs, cols=min(cols, count)))
    print('PREVIEW', path)


def fit_camera(cam, mn, mx, view, margin=1.06):
    """Perspective camera fitted on the PROJECTED bounding box (tighter than blcommon.frame_camera)."""
    d = VIEW_DIRS[view].normalized() if isinstance(view, str) else Vector(view).normalized()
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    q = d.to_track_quat('-Z', 'Y')
    right, up = q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0))
    c = (Vector(mn) + Vector(mx)) * 0.5
    hx = hy = hz = 0.0
    for ix in (mn[0], mx[0]):
        for iy in (mn[1], mx[1]):
            for iz in (mn[2], mx[2]):
                p = Vector((ix, iy, iz)) - c
                hx, hy, hz = max(hx, abs(p.dot(right))), max(hy, abs(p.dot(up))), max(hz, abs(p.dot(d)))
    tx = 18.0 / cam.data.lens
    if aspect < 1:
        tx *= aspect
    ty = tx / aspect
    dist = max(hx / tx, hy / ty) * margin + hz
    cam.location = c - d * dist
    cam.rotation_euler = q.to_euler()


def render_views(path, objs, views=('left', 'front', 'top', 'persp'), res=448, cols=2, bounds=None, frame=None):
    cam = setup_preview(res)
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    bpy.context.view_layer.update()
    mn, mx = bounds if bounds else _blc._bounds(objs)
    imgs = []
    for v in views:
        fit_camera(cam, mn, mx, v)
        imgs.append(render_to_array())
    save_png(path, montage(imgs, cols=cols))
    print('PREVIEW', path)


def args_after_dashes():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def render_tiles(path, objs, tiles, res=448, cols=4):
    """Model sheet with per-tile framing. tiles = [(view, bounds or None, callable or None), ...];
    the callable (if any) is run just before that tile is rendered (e.g. to open a jaw)."""
    cam = setup_preview(res)
    imgs = []
    for view, bounds, fn in tiles:
        if fn is not None:
            fn()
        bpy.context.view_layer.update()
        mn, mx = bounds if bounds else _blc._bounds(objs)
        fit_camera(cam, mn, mx, view)
        imgs.append(render_to_array())
    save_png(path, montage(imgs, cols=cols))
    print('PREVIEW', path)
