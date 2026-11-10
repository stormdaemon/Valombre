"""VALOMBRE nature pack - shared helpers (mesh builder, tubes, foliage cards, AO, puffy normals, previews).

Vertex colour contract (COLOR_0, linear) for nature meshes:
  R = ambient occlusion (1 = open sky, ~0.35 = deep inside the crown / under the canopy / rock underside)
  G = wind flutter weight (0 = rigid, 1 = leaf card tips)
  B = random phase per branch / leaf cluster (0..1)
Exceptions: flowers_a (M_flowers) and mushrooms (M_mushroom): COLOR_0.rgb = actual linear colour.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
from blcommon import _bounds
from mathutils import noise as mnoise
from mathutils.bvhtree import BVHTree

NATURE = os.path.join(MODELS, 'nature')
os.makedirs(NATURE, exist_ok=True)
LEAVES_A = os.path.join(TEXTURES, 'leaves_a.png')
LEAVES_N = os.path.join(TEXTURES, 'leaves_n.png')
IMPOSTORS_A = os.path.join(TEXTURES, 'impostors_a.png')
ATLAS_GRID = 4
ATLAS_PX = 2048

# name -> (col, row, kind, description). row 0 = TOP row of the image.
# kind 'twig'   : twig base at the bottom centre of the cell, foliage grows upward in the image.
# kind 'curtain': attached along the whole bottom edge, grows upward in the image (the card hangs: V axis = world down).
ATLAS_CELLS = {
    'oak_twig_a':     (0, 0, 'twig', 'oak branchlet, ~55 lobed leaves'),
    'oak_twig_b':     (1, 0, 'twig', 'oak branchlet, variant'),
    'birch_twig':     (2, 0, 'twig', 'birch twig fan, small serrated leaves'),
    'willow_strands': (3, 0, 'curtain', 'hanging willow strands (narrow leaves)'),
    'pine_spray_a':   (0, 1, 'twig', 'flat conifer bough seen from above'),
    'pine_spray_b':   (1, 1, 'curtain', 'conifer branch with drooping needle twigs (branch along the bottom edge)'),
    'bush_sprig_a':   (2, 1, 'twig', 'broad-leaf bush sprig'),
    'bush_sprig_b':   (3, 1, 'twig', 'small-leaf bush sprig with red berries'),
    'fern_frond':     (0, 2, 'twig', 'fern frond'),
    'reed_blades':    (1, 2, 'twig', 'reed blades + cattail heads'),
    'flower_heads':   (2, 2, 'twig', 'wild flowers: green stems/leaves (lower half), WHITE heads (upper half, tinted by vertex colour)'),
    'weed_tuft':      (3, 2, 'twig', 'tall grass / weed tuft (spare cell, not used by a mesh of this pack)'),
    'oak_dense':      (0, 3, 'twig', 'dense oak foliage mass (LOD1 cards)'),
    'pine_dense':     (1, 3, 'twig', 'dense conifer bough (LOD1 cards)'),
    'birch_dense':    (2, 3, 'twig', 'dense birch foliage mass (LOD1 cards)'),
    'willow_dense':   (3, 3, 'curtain', 'dense willow curtain (LOD1 cards)'),
}

_rects = None


def atlas_rects():
    """Measure the opaque content of every atlas cell. Returns name -> dict:
      u0, v0, cw, ch : Blender UV of the cell's bottom-left corner and its size (0.25)
      cx0, cx1, cy0, cy1 : content box inside the cell (0..1, y up from the cell bottom), 3 px padding
      ax : anchor x inside the cell (0.5)"""
    global _rects
    if _rects is not None:
        return _rects
    img = load_image(LEAVES_A)
    S = img.shape[0]
    cs = S // ATLAS_GRID
    out = {}
    for name, (c, r, kind, desc) in ATLAS_CELLS.items():
        a = img[r * cs:(r + 1) * cs, c * cs:(c + 1) * cs, 3] > 0.3
        ys = np.where(a.any(axis=1))[0]
        xs = np.where(a.any(axis=0))[0]
        pad = 3
        x0, x1 = max(xs[0] - pad, 0), min(xs[-1] + 1 + pad, cs)
        y0, y1 = max(ys[0] - pad, 0), min(ys[-1] + 1 + pad, cs)      # rows from the top
        out[name] = dict(u0=c / ATLAS_GRID, v0=1.0 - (r + 1) / ATLAS_GRID, cw=1.0 / ATLAS_GRID, ch=1.0 / ATLAS_GRID,
                         cx0=x0 / cs, cx1=x1 / cs, cy0=1.0 - y1 / cs, cy1=1.0 - y0 / cs, ax=0.5, kind=kind,
                         col=c, row=r, coverage=float(a.mean()))
        if kind == 'curtain':
            out[name]['cy0'] = 0.0
        else:
            out[name]['cy0'] = max(0.0, out[name]['cy0'] - 0.004)
    _rects = out
    return out


def unit(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


UP = np.array([0.0, 0.0, 1.0])


# ----------------------------------------------------------------------------- mesh builder
class MB:
    """Accumulates per-vertex attributes (verts are duplicated at UV seams) + faces, then builds a Blender mesh
    with UVs, COLOR_0 and custom split normals."""

    def __init__(self):
        self.pos, self.nrm, self.uv, self.col = [], [], [], []
        self.kind, self.card, self.clump = [], [], []
        self.faces, self.fmat = [], []
        self.nv = 0
        self.cards = []          # (center xyz, radius)

    def add(self, pos, nrm, uv, col, kind=0, card=-1, clump=None):
        pos = np.asarray(pos, np.float64).reshape(-1, 3)
        n = len(pos)
        self.pos.append(pos)
        self.nrm.append(np.asarray(nrm, np.float64).reshape(-1, 3))
        self.uv.append(np.asarray(uv, np.float64).reshape(-1, 2))
        self.col.append(np.asarray(col, np.float64).reshape(-1, 3))
        self.kind.append(np.full(n, kind, np.int32))
        self.card.append(np.full(n, card, np.int32))
        self.clump.append(np.tile(np.asarray(clump if clump is not None else (0, 0, 0), np.float64), (n, 1)))
        b = self.nv
        self.nv += n
        return b

    def face(self, idx, mat=0):
        self.faces.append(tuple(int(i) for i in idx))
        self.fmat.append(mat)

    def arrays(self):
        if isinstance(self.pos, list):
            self.pos = np.concatenate(self.pos) if self.pos else np.zeros((0, 3))
            self.nrm = np.concatenate(self.nrm) if self.nrm else np.zeros((0, 3))
            self.uv = np.concatenate(self.uv) if self.uv else np.zeros((0, 2))
            self.col = np.concatenate(self.col) if self.col else np.zeros((0, 3))
            self.kind = np.concatenate(self.kind) if self.kind else np.zeros(0, np.int32)
            self.card = np.concatenate(self.card) if self.card else np.zeros(0, np.int32)
            self.clump = np.concatenate(self.clump) if self.clump else np.zeros((0, 3))
        return self

    def tri_count(self):
        return sum(len(f) - 2 for f in self.faces)

    def auto_normals(self, angle=60.0):
        """Smooth normals computed from the faces; vertices sharing a position are merged unless their own
        normals differ by more than `angle` degrees (keeps hard edges where verts are duplicated)."""
        self.arrays()
        P = self.pos
        vn = np.zeros((len(P), 3))
        for f in self.faces:
            for k in range(1, len(f) - 1):
                a, b, c = f[0], f[k], f[k + 1]
                n = np.cross(P[b] - P[a], P[c] - P[a])
                vn[a] += n
                vn[b] += n
                vn[c] += n
        ln = np.maximum(np.linalg.norm(vn, axis=1), 1e-12)
        vu = vn / ln[:, None]
        keys = {}
        for i, p in enumerate(np.round(P / 1e-4).astype(np.int64)):
            keys.setdefault((int(p[0]), int(p[1]), int(p[2])), []).append(i)
        ca = math.cos(math.radians(angle))
        out = vu.copy()
        for g in keys.values():
            if len(g) == 1:
                continue
            for v in g:
                acc = np.zeros(3)
                for w in g:
                    if float(vu[w] @ vu[v]) >= ca:
                        acc += vn[w]
                out[v] = unit(acc)
        self.nrm = out
        return self

    def build(self, name, materials):
        self.arrays()
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.pos.tolist(), [], self.faces)
        me.update()
        npoly = len(me.polygons)
        me.polygons.foreach_set('use_smooth', np.ones(npoly, bool))
        me.polygons.foreach_set('material_index', np.asarray(self.fmat, np.int32))
        nl = len(me.loops)
        vi = np.empty(nl, np.int32)
        me.loops.foreach_get('vertex_index', vi)
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', self.uv[vi].astype(np.float32).ravel())
        attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        c4 = np.ones((nl, 4), np.float32)
        c4[:, :3] = np.clip(self.col[vi], 0, 1)
        attr.data.foreach_set('color', c4.ravel())
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = 0
        for m in materials:
            me.materials.append(m)
        nr = self.nrm.copy()
        ln = np.linalg.norm(nr, axis=1)
        bad = ln < 1e-6
        nr[bad] = (0, 0, 1)
        ln[bad] = 1
        nr /= ln[:, None]
        me.normals_split_custom_set_from_vertices(nr.tolist())
        ob = bpy.data.objects.new(name, me)
        link(ob)
        return ob


# ----------------------------------------------------------------------------- tubes
def frames(pts):
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    T = np.zeros((n, 3))
    for i in range(n):
        T[i] = unit(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
    N = np.zeros((n, 3))
    ref = np.array([1.0, 0, 0]) if abs(T[0][0]) < 0.9 else np.array([0, 1.0, 0])
    N[0] = unit(ref - T[0] * np.dot(ref, T[0]))
    for i in range(1, n):
        v = N[i - 1] - T[i] * np.dot(N[i - 1], T[i])
        N[i] = unit(v)
    B = np.cross(T, N)
    return T, N, B


def auto_uspan(r):
    c = 2 * math.pi * r
    if c >= 0.75:
        return float(max(1, round(c)))
    return 0.5 if c >= 0.33 else 0.25


def tube(mb, pts, rad, sides, mat=0, g=0.0, phase=0.0, v0=0.0, tip='cone', rad_fn=None, uspan=None, ao=1.0,
         uoff=0.0, base_cap=False):
    """Tapered tube along a polyline. UV: u = around (uspan texture repeats... in metres of circumference when
    possible), v = length along the branch in metres. tip: 'cone' (last node = apex), 'flat' (capped), 'open'.
    rad_fn(angles, i) -> per-vertex radius multiplier (root flare)."""
    pts = np.asarray(pts, np.float64)
    rad = np.asarray(rad, np.float64)
    n = len(pts)
    g = np.full(n, g, np.float64) if np.isscalar(g) else np.asarray(g, np.float64)
    ao = np.full(n, ao, np.float64) if np.isscalar(ao) else np.asarray(ao, np.float64)
    T, N, B = frames(pts)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if uspan is None:
        uspan = auto_uspan(rad[min(1, n - 1)])
    ang = np.linspace(0, 2 * math.pi, sides + 1)
    ca, sa = np.cos(ang), np.sin(ang)
    nr = n - 1 if tip == 'cone' else n
    rings = []
    for i in range(nr):
        radial = ca[:, None] * N[i][None, :] + sa[:, None] * B[i][None, :]
        r = rad[i] * (rad_fn(ang, i) if rad_fn else np.ones(sides + 1))
        pos = pts[i][None, :] + radial * r[:, None]
        # slope-corrected normal for tapering tubes
        nrm = radial.copy()
        if i + 1 < n and seg[min(i, n - 2)] > 1e-6:
            slope = (rad[i] - rad[min(i + 1, n - 1)]) / seg[min(i, n - 2)]
            nrm = nrm + T[i][None, :] * min(max(slope, -0.8), 0.8)
        uv = np.stack([uoff + ang / (2 * math.pi) * uspan, np.full(sides + 1, v0 + cum[i])], axis=1)
        col = np.tile([ao[i], g[i], phase], (sides + 1, 1))
        rings.append(mb.add(pos, nrm, uv, col))
    for i in range(nr - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(sides):
            mb.face((a + j, a + j + 1, b + j + 1, b + j), mat)
    last = rings[-1]
    if tip == 'cone':
        radial = ca[:sides, None] * N[-1][None, :] + sa[:sides, None] * B[-1][None, :]
        mid = (ang[:sides] + ang[1:]) / 2
        radial_m = np.cos(mid)[:, None] * N[-1][None, :] + np.sin(mid)[:, None] * B[-1][None, :]
        pos = np.tile(pts[-1], (sides, 1))
        nrm = radial_m * 0.8 + T[-1][None, :] * 0.6
        uv = np.stack([uoff + mid / (2 * math.pi) * uspan, np.full(sides, v0 + cum[-1])], axis=1)
        col = np.tile([ao[-1], g[-1], phase], (sides, 1))
        t0 = mb.add(pos, nrm, uv, col)
        for j in range(sides):
            mb.face((last + j, last + j + 1, t0 + j), mat)
    elif tip == 'flat':
        cap_ring(mb, pts[-1], T[-1], N[-1], B[-1], rad[-1], sides, mat, ao[-1], g[-1], phase, rad_fn, n - 1)
    if base_cap:
        cap_ring(mb, pts[0], -T[0], N[0], -B[0], rad[0], sides, mat, ao[0], g[0], phase, None, 0)
    return cum[-1]


def cap_ring(mb, c, T, N, B, r, sides, mat, ao, g, phase, rad_fn=None, i=0, dome=0.0, uvscale=1.0):
    ang = np.linspace(0, 2 * math.pi, sides + 1)[:sides]
    rr = r * (rad_fn(ang, i) if rad_fn else np.ones(sides))
    radial = np.cos(ang)[:, None] * N[None, :] + np.sin(ang)[:, None] * B[None, :]
    pos = c[None, :] + radial * rr[:, None]
    uv = np.stack([0.5 + np.cos(ang) * rr * uvscale, 0.5 + np.sin(ang) * rr * uvscale], axis=1)
    b = mb.add(pos, np.tile(T, (sides, 1)) + radial * 0.25, uv, np.tile([ao, g, phase], (sides, 1)))
    cc = mb.add(c + T * dome, T, (0.5, 0.5), (ao * 0.9, g, phase))
    for j in range(sides):
        mb.face((b + j, b + (j + 1) % sides, cc), mat)


# ----------------------------------------------------------------------------- foliage cards
def card(mb, rect, anchor, d, r, S, nseg=1, droop=0.0, tent=0.0, flip=False, g0=0.3, phase=0.0, mat=1,
         clump=None, cols=2, ao=1.0, width=1.0, kind=1, col_fn=None, g1=1.0, curl=0.0, lscale=1.0, ortho=True):
    """One alpha-tested card showing the atlas cell `rect` (see atlas_rects). The cell would be S metres wide if
    shown entirely; only its content box is meshed. anchor = world position of the twig base (bottom centre of
    the cell), d = growth direction, r = right direction. droop: per-segment pull toward -Z. tent: side droop
    (cols=3 -> ridge along the middle). curl: per-segment rotation of the growth direction around r."""
    anchor = np.asarray(anchor, np.float64)
    d = unit(d)
    r = unit(np.asarray(r, np.float64) - d * np.dot(r, d)) if ortho else unit(r)
    xs = [rect['cx0'], rect['cx1']] if cols == 2 else [rect['cx0'], rect['ax'], rect['cx1']]
    xs = [rect['ax'] + (x - rect['ax']) * width for x in xs]
    y0, y1 = rect['cy0'], rect['cy1']
    seglen = (y1 - y0) * S * lscale / nseg
    cid = len(mb.cards)
    rows = []
    p = anchor.copy()
    dk = d.copy()
    allpos = []
    for k in range(nseg + 1):
        t = k / nseg
        row_pos, row_uv, row_col = [], [], []
        for x in xs:
            off = (x - rect['ax']) * S * (-1.0 if flip else 1.0)
            q = p + r * off
            if tent:
                q = q + np.array([0, 0, -1.0]) * tent * abs(off)
            row_pos.append(q)
            row_uv.append((rect['u0'] + x * rect['cw'], rect['v0'] + (y0 + (y1 - y0) * t) * rect['ch']))
            gg = g0 + (g1 - g0) * t
            if tent:
                gg = min(1.0, gg + 0.3 * abs(x - rect['ax']) / max(1e-6, rect['cx1'] - rect['ax']))
            c = (ao, gg, phase) if col_fn is None else col_fn(t, x)
            row_col.append(c)
        nrm = np.cross(r, dk)
        b = mb.add(row_pos, np.tile(nrm, (len(xs), 1)), row_uv, row_col, kind=kind, card=cid, clump=clump)
        rows.append(b)
        allpos += row_pos
        if k < nseg:
            p = p + dk * seglen
            dk = unit(dk + np.array([0, 0, -droop]))
            if curl:
                nn = np.cross(r, dk)
                dk = unit(dk + nn * curl)
    nc = len(xs)
    for k in range(nseg):
        for j in range(nc - 1):
            a, b = rows[k], rows[k + 1]
            mb.face((a + j, a + j + 1, b + j + 1, b + j), mat)
    allpos = np.array(allpos)
    cen = allpos.mean(axis=0)
    mb.cards.append((cen, float(np.linalg.norm(allpos - cen, axis=1).max()) * 0.62))
    return cid


# ----------------------------------------------------------------------------- AO + normals for trees
def _hemi_dirs():
    dirs, w = [(0, 0, 1.0)], [1.0]
    for el, n, ww in ((55, 6, 0.85), (25, 8, 0.5), (-5, 6, 0.18)):
        for k in range(n):
            az = 2 * math.pi * (k + 0.5 * (el == 25)) / n
            e = math.radians(el)
            dirs.append((math.cos(e) * math.cos(az), math.cos(e) * math.sin(az), math.sin(e)))
            w.append(ww)
    return np.array(dirs), np.array(w) / np.sum(w)


def canopy_ao(P, own, cards, kappa=0.42, lo=0.33, gamma=0.8):
    """Sky visibility of points P (Nx3) under a cloud of foliage cards [(center, radius)]. own = per-point card id
    (-1 = none) which is ignored for that point."""
    if not cards:
        return np.ones(len(P))
    C = np.array([c for c, r in cards])
    R = np.array([r for c, r in cards])
    dirs, w = _hemi_dirs()
    out = np.zeros(len(P))
    ids = np.arange(len(cards))
    for s in range(0, len(P), 512):
        p = P[s:s + 512]
        q = C[None, :, :] - p[:, None, :]                 # (n, M, 3)
        q2 = np.einsum('nmk,nmk->nm', q, q)
        notown = own[s:s + 512, None] != ids[None, :]
        acc = np.zeros(len(p))
        for dvec, ww in zip(dirs, w):
            al = q @ dvec                                   # (n, M)
            perp2 = np.maximum(q2 - al * al, 0)
            k = np.clip(1.0 - perp2 / (R[None, :] ** 2), 0, 1) * (al > 0.05) * notown
            acc += ww * np.exp(-kappa * k.sum(axis=1))
        out[s:s + 512] = acc
    return lo + (1 - lo) * np.power(out, gamma)


def finish_tree(mb, ground_ao=True, crown=None, w_global=0.20, w_local=0.10, w_up=0.70, ao_mul=1.0, lo=0.33,
                kappa=0.42, ground_h=1.3, ground_lo=0.62):
    """Bake AO into R for every vertex, and puffy normals for foliage vertices:
    n = normalize(w_global * outward(crown ellipsoid) + w_local * outward(local clump) + w_up * up).
    Default = 30% puffy outward blended with 70% up (soft shading). Raise w_global / w_local for rounder shading."""
    mb.arrays()
    P = mb.pos
    ao = canopy_ao(P, mb.card, mb.cards, lo=lo, kappa=kappa)
    if ground_ao:
        ao = ao * (ground_lo + (1.0 - ground_lo) * smoothstep(0.0, ground_h, P[:, 2]))
    mb.col[:, 0] = np.clip(mb.col[:, 0] * ao * ao_mul, 0.0, 1.0)
    leaf = mb.kind == 1
    if leaf.any():
        L = P[leaf]
        if crown is None:
            mn, mx = L.min(axis=0), L.max(axis=0)
            cen = (mn + mx) / 2
            cen[2] = mn[2] + (mx[2] - mn[2]) * 0.42
            radii = np.maximum((mx - mn) / 2, 0.5)
        else:
            cen, radii = np.asarray(crown[0], float), np.asarray(crown[1], float)
        og = (L - cen) / radii
        og /= np.maximum(np.linalg.norm(og, axis=1), 1e-6)[:, None]
        ol = L - mb.clump[leaf]
        ol /= np.maximum(np.linalg.norm(ol, axis=1), 1e-6)[:, None]
        n = og * w_global + ol * w_local + UP[None, :] * w_up
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-6)[:, None]
        mb.nrm[leaf] = n
        return cen, radii
    return None, None


# ----------------------------------------------------------------------------- generic AO by ray casting (rocks, props)
def _cos_dirs(n, seed=7):
    rng = np.random.RandomState(seed)
    out = []
    for i in range(n):
        u, v = (i + 0.5) / n, (i * 0.61803398875) % 1.0
        r = math.sqrt(u)
        th = 2 * math.pi * v
        out.append((r * math.cos(th), r * math.sin(th), math.sqrt(max(0.0, 1 - u))))
    return np.array(out)


def bake_ao_raycast(obj, dist=None, ground=True, rays=48, lo=0.3, gamma=0.85, ground_grad=0.0, ground_z=0.0,
                    sky_bias=0.35):
    """Per-vertex AO by BVH ray casting against the mesh itself (+ an infinite ground plane at ground_z).
    Returns array (nverts,) in lo..1. Hits further than `dist` do not occlude (soft falloff)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    bvh = BVHTree.FromBMesh(bm)
    P = np.array([v.co[:] for v in bm.verts])
    Nn = np.array([v.normal[:] for v in bm.verts])
    ext = P.max(axis=0) - P.min(axis=0)
    if dist is None:
        dist = float(max(ext)) * 0.9
    dirs = _cos_dirs(rays)
    ao = np.zeros(len(P))
    for i in range(len(P)):
        n = unit(Nn[i])
        # bias the hemisphere a little toward the sky: undersides get darker
        n2 = unit(n + UP * sky_bias)
        t = unit(np.cross(n2, (1, 0, 0) if abs(n2[0]) < 0.9 else (0, 1, 0)))
        b = np.cross(n2, t)
        o = P[i] + n * 0.01
        acc = 0.0
        for dl in dirs:
            dv = t * dl[0] + b * dl[1] + n2 * dl[2]
            occ = 0.0
            hit = bvh.ray_cast(Vector(o), Vector(dv), dist)
            if hit[0] is not None:
                occ = 1.0 - (hit[3] / dist) ** 2 * 0.7
            elif ground and dv[2] < -1e-3:
                tg = (ground_z - o[2]) / dv[2]
                if 0 < tg < dist:
                    occ = 1.0 - (tg / dist) ** 2 * 0.7
                elif tg <= 0:
                    occ = 1.0
            acc += 1.0 - occ
        ao[i] = acc / len(dirs)
    bm.free()
    ao = lo + (1 - lo) * np.power(np.clip(ao, 0, 1), gamma)
    if ground_grad > 0:
        ao *= 0.7 + 0.3 * smoothstep(ground_z - 0.02, ground_z + ground_grad, P[:, 2])
    return ao


def set_colors_per_vertex(obj, cols):
    """cols: (nverts, 3) linear -> per-corner FLOAT_COLOR 'Col' (exported as COLOR_0)."""
    me = obj.data
    attr = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    nl = len(me.loops)
    vi = np.empty(nl, np.int32)
    me.loops.foreach_get('vertex_index', vi)
    c4 = np.ones((nl, 4), np.float32)
    c4[:, :3] = np.clip(np.asarray(cols)[vi], 0, 1)
    attr.data.foreach_set('color', c4.ravel())
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = list(me.color_attributes).index(attr)


# ----------------------------------------------------------------------------- materials
BARK_PREVIEW = {
    'M_bark_oak': (lin('#3b2f24'), lin('#6e5d49')),
    'M_bark_pine': (lin('#3a261b'), lin('#7a5540')),
    'M_bark_birch': (lin('#bfbcb0'), lin('#e6e3d8')),
    'M_rock': (lin('#55524b'), lin('#8f8a7d')),
    'M_mushroom': (lin('#ffffff'), lin('#ffffff')),
    'M_leaves': (lin('#4c6a2a'), lin('#4c6a2a')),
    'M_flowers': (lin('#ffffff'), lin('#ffffff')),
}


def nat_mat(name):
    """Plain material (no textures) used for the export; the NAME is the engine contract."""
    c = BARK_PREVIEW.get(name, ((0.5, 0.5, 0.5),) * 2)[1]
    m = bpy.data.materials.get(name)
    if m is None:
        m = make_mat(name, c, rough=0.85)
    return m


def _nodes(m):
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return nt, nt.nodes, nt.links


def _ao_node(nodes, links):
    vc = nodes.new('ShaderNodeVertexColor')       # empty layer name = the render colour attribute
    sep = nodes.new('ShaderNodeSeparateColor')
    links.new(vc.outputs['Color'], sep.inputs['Color'])
    return vc, sep


def _mul(nodes, links, a, b):
    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    links.new(a, mix.inputs[6])
    links.new(b, mix.inputs[7])
    return mix.outputs[2]


def _surface(nodes, links, color, unlit, rough=0.8, alpha=None, true_normals=False):
    out = nodes.new('ShaderNodeOutputMaterial')
    if unlit:
        em = nodes.new('ShaderNodeEmission')
        links.new(color, em.inputs['Color'])
        sh = em.outputs[0]
        if alpha is not None:
            tr = nodes.new('ShaderNodeBsdfTransparent')
            mx = nodes.new('ShaderNodeMixShader')
            links.new(alpha, mx.inputs[0])
            links.new(tr.outputs[0], mx.inputs[1])
            links.new(em.outputs[0], mx.inputs[2])
            sh = mx.outputs[0]
        links.new(sh, out.inputs['Surface'])
    else:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Roughness'].default_value = rough
        try:
            bsdf.inputs['Specular IOR Level'].default_value = 0.15
        except Exception:
            pass
        links.new(color, bsdf.inputs['Base Color'])
        if alpha is not None:
            links.new(alpha, bsdf.inputs['Alpha'])
        if true_normals:
            # the engine must NOT flip foliage normals on back faces: emulate that in the preview
            geo = nodes.new('ShaderNodeNewGeometry')
            m1 = nodes.new('ShaderNodeMath')
            m1.operation = 'MULTIPLY_ADD'
            links.new(geo.outputs['Backfacing'], m1.inputs[0])
            m1.inputs[1].default_value = -2.0
            m1.inputs[2].default_value = 1.0
            vm = nodes.new('ShaderNodeVectorMath')
            vm.operation = 'SCALE'
            links.new(geo.outputs['Normal'], vm.inputs[0])
            links.new(m1.outputs[0], vm.inputs['Scale'])
            links.new(vm.outputs['Vector'], bsdf.inputs['Normal'])
        links.new(bsdf.outputs[0], out.inputs['Surface'])


def preview_materials(unlit=False):
    """Upgrade the plain export materials to textured preview versions (call AFTER export_glb)."""
    img = None
    for m in list(bpy.data.materials):
        base = m.name.split('.')[0]
        if base in ('M_leaves', 'M_flowers'):
            if img is None:
                img = bpy.data.images.load(LEAVES_A, check_existing=True)
            nt, nodes, links = _nodes(m)
            tex = nodes.new('ShaderNodeTexImage')
            tex.image = img
            vc, sep = _ao_node(nodes, links)
            if base == 'M_flowers':
                col = _mul(nodes, links, tex.outputs['Color'], vc.outputs['Color'])
            else:
                comb = nodes.new('ShaderNodeCombineColor')
                for k in range(3):
                    links.new(sep.outputs[0], comb.inputs[k])
                col = _mul(nodes, links, tex.outputs['Color'], comb.outputs[0])
            gt = nodes.new('ShaderNodeMath')
            gt.operation = 'GREATER_THAN'
            gt.inputs[1].default_value = 0.5
            links.new(tex.outputs['Alpha'], gt.inputs[0])
            _surface(nodes, links, col, unlit, rough=0.6, alpha=gt.outputs[0], true_normals=True)
            try:
                m.surface_render_method = 'DITHERED'
                m.use_transparent_shadow = True
            except Exception as e:
                print('mat flags', e)
            m.use_backface_culling = False
        elif base.startswith('M_bark') and os.path.exists(os.path.join(TEXTURES, base[2:] + '_a.png')):
            # the engine's own bark albedo exists: use it so that previews / impostors match the game
            nt, nodes, links = _nodes(m)
            tex = nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(os.path.join(TEXTURES, base[2:] + '_a.png'), check_existing=True)
            vc, sep = _ao_node(nodes, links)
            comb = nodes.new('ShaderNodeCombineColor')
            for k in range(3):
                links.new(sep.outputs[0], comb.inputs[k])
            col = _mul(nodes, links, tex.outputs['Color'], comb.outputs[0])
            _surface(nodes, links, col, unlit, rough=0.9)
        elif base.startswith('M_bark') or base == 'M_rock':
            dark, light = BARK_PREVIEW.get(base, BARK_PREVIEW['M_bark_oak'])
            nt, nodes, links = _nodes(m)
            tc = nodes.new('ShaderNodeTexCoord')
            mp = nodes.new('ShaderNodeMapping')
            nz = nodes.new('ShaderNodeTexNoise')
            ramp = nodes.new('ShaderNodeValToRGB')
            if base == 'M_rock':
                links.new(tc.outputs['Object'], mp.inputs['Vector'])
                mp.inputs['Scale'].default_value = (1.2, 1.2, 2.2)
                nz.inputs['Scale'].default_value = 2.2
                nz.inputs['Detail'].default_value = 8.0
                ramp.color_ramp.elements[0].position = 0.3
                ramp.color_ramp.elements[1].position = 0.72
            elif base == 'M_bark_birch':
                links.new(tc.outputs['UV'], mp.inputs['Vector'])
                mp.inputs['Scale'].default_value = (2.0, 9.0, 1.0)
                nz.inputs['Scale'].default_value = 3.0
                nz.inputs['Detail'].default_value = 3.0
                ramp.color_ramp.elements[0].position = 0.36
                ramp.color_ramp.elements[1].position = 0.44
                dark, light = lin('#2a2622'), light
            else:
                links.new(tc.outputs['UV'], mp.inputs['Vector'])
                mp.inputs['Scale'].default_value = (7.0, 0.9, 1.0)
                nz.inputs['Scale'].default_value = 4.0
                nz.inputs['Detail'].default_value = 5.0
                ramp.color_ramp.elements[0].position = 0.35
                ramp.color_ramp.elements[1].position = 0.7
            ramp.color_ramp.elements[0].color = (dark[0], dark[1], dark[2], 1)
            ramp.color_ramp.elements[1].color = (light[0], light[1], light[2], 1)
            links.new(mp.outputs['Vector'], nz.inputs['Vector'])
            links.new(nz.outputs[0], ramp.inputs['Fac'])
            vc, sep = _ao_node(nodes, links)
            comb = nodes.new('ShaderNodeCombineColor')
            for k in range(3):
                links.new(sep.outputs[0], comb.inputs[k])
            col = _mul(nodes, links, ramp.outputs['Color'], comb.outputs[0])
            _surface(nodes, links, col, unlit, rough=0.9)
        elif base == 'M_mushroom':
            nt, nodes, links = _nodes(m)
            vc, sep = _ao_node(nodes, links)
            _surface(nodes, links, vc.outputs['Color'], unlit, rough=0.6)


# ----------------------------------------------------------------------------- previews
def nat_sheet(path, groups, views=('front', 'left', 'persp'), res=384, same_bounds=False, cols=None, margin=None):
    """Contact sheet: one row per group (list of objects), each rendered ALONE with the given views."""
    cam = setup_preview(res)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    imgs = []
    ref = None
    for g in groups:
        if not isinstance(g, (list, tuple)):
            g = [g]
        for o in meshes:
            o.hide_render = o not in g
        mn, mx = _bounds(g)
        if same_bounds:
            if ref is None:
                ref = (mn, mx)
            mn, mx = ref
        ext = mx - mn
        mg = margin or min(1.0, max(0.6, 1.14 * max(ext.z, max(ext.x, ext.y)) / max(ext.length, 1e-6)))
        for v in views:
            frame_camera(cam, mn, mx, v, margin=mg)
            imgs.append(render_to_array())
    for o in meshes:
        o.hide_render = False
    save_png(path, montage(imgs, cols=cols or len(views)))
    print('PREVIEW', path)
    return path


# ----------------------------------------------------------------------------- glb reading / verification
def glb_arrays(path):
    """-> (json, [ {name, prims: [ {material, POSITION, NORMAL, COLOR_0, TEXCOORD_0, indices} ]} ])  (glTF space, +Y up)"""
    with open(path, 'rb') as f:
        data = f.read()
    clen = struct.unpack_from('<I', data, 12)[0]
    js = json.loads(data[20:20 + clen].decode('utf8'))
    bin0 = 20 + clen + 8

    def acc(i):
        a = js['accessors'][i]
        bv = js['bufferViews'][a['bufferView']]
        nc = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a['componentType']]
        off = bin0 + bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        arr = np.frombuffer(data, dt, a['count'] * nc, off).reshape(a['count'], nc).astype(np.float64)
        if a.get('normalized'):
            arr = arr / float(np.iinfo(dt).max)
        return arr

    meshes = []
    for m in js.get('meshes', []):
        prims = []
        for p in m['primitives']:
            d = {'material': js['materials'][p['material']]['name'] if 'material' in p else None}
            for k, v in p['attributes'].items():
                d[k] = acc(v)
            d['indices'] = acc(p['indices']).astype(np.int64).ravel()
            prims.append(d)
        meshes.append({'name': m.get('name'), 'prims': prims})
    return js, meshes


def glb_mesh_stats(path):
    """name -> dict(tris, size (x, y, z in BLENDER axes), min, max, materials) for every mesh of the glb."""
    js, meshes = glb_arrays(path)
    node_of = {}
    for n in js.get('nodes', []):
        if 'mesh' in n:
            node_of[n['mesh']] = n
    out = {}
    for mi, m in enumerate(meshes):
        node = node_of.get(mi, {})
        P = np.concatenate([p['POSITION'] for p in m['prims']])
        mn, mx = P.min(axis=0), P.max(axis=0)
        # glTF (x, y, z) = Blender (x, z, -y)
        bmn = (mn[0], -mx[2], mn[1])
        bmx = (mx[0], -mn[2], mx[1])
        out[node.get('name', m['name'])] = dict(
            tris=int(sum(len(p['indices']) // 3 for p in m['prims'])),
            verts=int(sum(len(p['POSITION']) for p in m['prims'])),
            min=[round(float(x), 3) for x in bmn], max=[round(float(x), 3) for x in bmx],
            size=[round(float(b - a), 3) for a, b in zip(bmn, bmx)],
            materials=[p['material'] for p in m['prims']],
            tris_by_material={p['material']: int(len(p['indices']) // 3) for p in m['prims']},
            extras=node.get('extras', {}))
    return out


def check_leaf_normals(path, tag=''):
    """Verify that the custom foliage normals survived the export: they must NOT be the card face normals."""
    js, meshes = glb_arrays(path)
    for m in meshes:
        for p in m['prims']:
            if p['material'] not in ('M_leaves',):
                continue
            P, Nn, idx = p['POSITION'], p['NORMAL'], p['indices'].reshape(-1, 3)
            fn = np.cross(P[idx[:, 1]] - P[idx[:, 0]], P[idx[:, 2]] - P[idx[:, 0]])
            fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-9)[:, None]
            dots = np.abs(np.einsum('ij,ij->i', fn, Nn[idx[:, 0]]))
            cen = P.mean(axis=0)
            out = P - cen
            out /= np.maximum(np.linalg.norm(out, axis=1), 1e-9)[:, None]
            print('NORMALCHECK %s %s: |face.n| mean %.2f (1.0 would mean plain face normals), outward dot mean %.2f, '
                  'up (glTF +Y) mean %.2f' % (tag, m['name'], float(dots.mean()),
                                              float(np.einsum('ij,ij->i', out, Nn).mean()), float(Nn[:, 1].mean())))


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def rot_about(v, axis, ang):
    axis = unit(axis)
    c, s = math.cos(ang), math.sin(ang)
    v = np.asarray(v, np.float64)
    return v * c + np.cross(axis, v) * s + axis * np.dot(axis, v) * (1 - c)


def stack_images(paths, out, pad=6, bg=0.1, cols=1):
    """Tile preview PNGs into one sheet (cols columns, row-major, left/top aligned)."""
    ims = [load_image(p)[:, :, :3] for p in paths if os.path.exists(p)]
    if not ims:
        return None
    W = max(i.shape[1] for i in ims)
    Hc = max(i.shape[0] for i in ims)
    rows = int(math.ceil(len(ims) / cols))
    sheet = np.full((rows * (Hc + pad) + pad, cols * (W + pad) + pad, 3), bg, np.float32)
    for k, i in enumerate(ims):
        r, c = divmod(k, cols)
        y, x = pad + r * (Hc + pad), pad + c * (W + pad)
        sheet[y:y + i.shape[0], x:x + i.shape[1]] = i
    save_png(out, sheet)
    print('PREVIEW', out)
    return out


def cli_only():
    if '--' in sys.argv:
        s = set(sys.argv[sys.argv.index('--') + 1:])
        return s or None
    return None
