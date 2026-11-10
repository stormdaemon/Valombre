"""VALOMBRE - settlements pack: parametric architecture toolkit (Blender 5.1, headless).

Everything is built into one bmesh per asset through `Kit`:
  * every primitive writes world-scale UVs (tile size looked up by material name) and a base vertex colour
  * `Kit.bake()` multiplies the colours by ray-cast ambient occlusion (incl. the ground), a ground-dirt
    gradient, moss on roofs / north faces and soot near chimneys
  * `Kit.finish()` returns the Blender objects (main mesh, ROT_ sub meshes, COL_/WALK_ boxes, empties)

Coordinates: Blender Z up, front = -Y, origin = centre of the footprint on the ground.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
from blcommon import _bounds
from mathutils import noise as mnoise
from mathutils.bvhtree import BVHTree

OUT = os.path.join(MODELS, 'arch')
os.makedirs(OUT, exist_ok=True)
V = Vector
WHITE = (1.0, 1.0, 1.0)
NOAO = 1          # face flag: keep the authored colour (emissive, tintable cloth)
PI = math.pi

# ----------------------------------------------------------------------------- materials / palette
TILE = {'M_stone_wall': 2.0, 'M_stone_brick': 2.0, 'M_cobble': 2.0, 'M_plaster': 2.0, 'M_wood_planks': 2.0,
        'M_roof_tiles': 2.0, 'M_thatch': 2.0, 'M_rock': 4.0, 'M_bark_oak': 1.0, 'M_bark_pine': 1.0,
        'M_bark_birch': 1.0}
# preview-only look: (srgb hex, roughness, metallic, emissive strength)
PREV = {
    # (colours = rough average of the engine textures seen in tools/previews/tex_*.png)
    'M_stone_wall': ('#857e70', 0.9, 0, 0), 'M_stone_brick': ('#8d8778', 0.9, 0, 0),
    'M_cobble': ('#78736a', 0.9, 0, 0), 'M_plaster': ('#d2c8b0', 0.9, 0, 0),
    'M_wood_planks': ('#7d6c59', 0.8, 0, 0), 'M_roof_tiles': ('#8f5c49', 0.8, 0, 0),
    'M_thatch': ('#948557', 0.95, 0, 0), 'M_rock': ('#8b8880', 0.9, 0, 0),
    'M_bark_oak': ('#7a6753', 0.95, 0, 0), 'M_bark_pine': ('#806650', 0.95, 0, 0),
    'M_metal_iron': ('#ffffff', 0.55, 0.2, 0), 'M_metal_steel': ('#ffffff', 0.35, 0.3, 0),
    'M_metal_bronze': ('#ffffff', 0.4, 0.3, 0), 'M_metal_gold': ('#ffffff', 0.35, 0.3, 0),
    'M_cloth': ('#ffffff', 0.95, 0, 0), 'M_rope': ('#ffffff', 0.95, 0, 0), 'M_leather': ('#ffffff', 0.7, 0, 0),
    'M_bone': ('#ffffff', 0.6, 0, 0),
    'M_ember': ('#ff5a14', 0.6, 0, 4.0), 'M_window_glow': ('#ffc070', 0.4, 0, 1.6),
}


def L(h):
    return lin(h)


PAL = dict(
    # wood: the M_wood_planks texture is already a mid grey-brown, so planks stay near white and the
    # dark-oak frame multiplies it down to ~#39281a
    beam=L('#7f6c5c'), beam_d=L('#6b5647'), beam_l=L('#9a8876'),
    plank=L('#e4d8c4'), plank_l=L('#fff6e6'), plank_d=L('#b8a790'), door=L('#c8b69c'),
    plaster=L('#f4eddc'), plaster_o=L('#ecdcb9'), plaster_g=L('#ddd7c9'), plaster_r=L('#e8cdb8'),
    stone=L('#eeeae2'), stone_d=L('#c9c4ba'), stone_w=L('#efe6d6'),
    thatch=L('#e9dec0'), thatch_old=L('#c2b89d'), thatch_new=L('#f6e9ba'), hay=L('#f2e3a8'),
    tile=L('#f2e3d8'), tile_d=L('#cfb9aa'), slate=(0.30, 0.60, 0.88),   # slate = tint that greys the clay texture
    iron=L('#353230'), iron_l=L('#56514d'), steel=L('#9a9ea3'), bronze=L('#8c6a3a'),
    rope=L('#a98f62'), canvas=L('#cfc19f'), sack=L('#b49c72'), leather=L('#6a4a34'),
    red=L('#8c2f26'), blue=L('#33506e'), green=L('#4f6a3b'), yellow=L('#c49a3c'), white=L('#e6dfd0'),
    ember=L('#ff7a2a'), glow=L('#ffd08a'), soot=L('#2c2825'), dark=L('#1c1a18'),
    bark=L('#d9d0c4'), bread=L('#b98a4e'), fish=L('#8fa0a8'), cabbage=L('#6f8f4a'), carrot=L('#c8702a'),
    apple=L('#a83a2a'), paper=L('#d8cfb4'), clay=L('#a56a48'),
)


def mulc(c, f):
    return (c[0] * f, c[1] * f, c[2] * f)


def mixc(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def mul2(a, b):
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def sstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    hexc, rough, metal, emis = PREV.get(name, ('#ffffff', 0.8, 0, 0))
    c = lin(hexc)
    if emis:
        m = make_mat(name, c, rough, metal, emissive=c, emissive_strength=emis, use_vertex_color=False)
    else:
        m = make_mat(name, c, rough, metal, use_vertex_color=True)
    m.use_backface_culling = True
    return m


# ----------------------------------------------------------------------------- the builder
class _Ctx:
    def __init__(self, kit, M):
        self.kit, self.Mx = kit, M

    def __enter__(self):
        self.kit._stack.append(self.kit.M)
        self.kit.M = self.kit.M @ self.Mx
        return self.kit

    def __exit__(self, *a):
        self.kit.M = self.kit._stack.pop()


class Kit:
    SEP = 0.004      # half distance between the two sides of double-sided sheets

    def __init__(self, name, seed=7, origin=(0, 0, 0)):
        self.name = name
        self.origin = V(origin)
        self.bm = bmesh.new()
        self.uvl = self.bm.loops.layers.uv.new('UVMap')
        self.cl = self.bm.loops.layers.float_color.new('Col')
        self.fl = self.bm.faces.layers.int.new('flag')
        self.ml = self.bm.loops.layers.float.new('moss')
        self.mats = []
        self.rng = random.Random(seed)
        self.M = Matrix.Identity(4)
        self._stack = []
        self.cols, self.walks, self.empties, self.subs = [], [], [], []
        self.soot = []          # (point, radius, strength)
        self.person = None      # preview-only 1.8 m figure position (x, y)
        self.bake_args = {}
        self.notes = None

    # -- transforms -------------------------------------------------------
    def at(self, loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0, scale=None):
        M = Matrix.Translation(V(loc)) @ Euler((rx, ry, rz), 'XYZ').to_matrix().to_4x4()
        if scale is not None:
            if isinstance(scale, (int, float)):
                scale = (scale, scale, scale)
            M = M @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
        return _Ctx(self, M)

    def xf(self, M):
        return _Ctx(self, M)

    def W(self, p):
        """local point -> world (through the current transform stack)"""
        return self.M @ V(p)

    # -- helpers -------------------------------------------------------
    def r(self, a=-1.0, b=1.0):
        return self.rng.uniform(a, b)

    def jit(self, col, amt=0.08, hue=0.03):
        f = 1.0 + self.rng.uniform(-amt, amt)
        return (col[0] * f * (1 + self.rng.uniform(-hue, hue)), col[1] * f,
                col[2] * f * (1 + self.rng.uniform(-hue, hue)))

    def mi(self, name):
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    def v(self, p):
        return self.bm.verts.new(self.M @ V(p))

    def _auto_uvo(self, mat):
        if mat in ('M_wood_planks', 'M_bark_oak', 'M_bark_pine', 'M_thatch'):
            return (self.rng.random() * 2.0, self.rng.random() * 2.0)
        return (0.0, 0.0)

    def f(self, vs, mat, col=WHITE, uv='box', smooth=False, flag=0, uvo=(0.0, 0.0), moss=0.0):
        """Create one face from BMVerts (CCW seen from outside). Returns the BMFace (or None)."""
        out = []
        for x in vs:
            if not out or x is not out[-1]:
                out.append(x)
        if len(out) > 1 and out[0] is out[-1]:
            out.pop()
        if len(out) < 3:
            return None
        if self.M.determinant() < 0:
            out.reverse()
        try:
            face = self.bm.faces.new(out)
        except ValueError:
            return None
        face.material_index = self.mi(mat)
        face.smooth = smooth
        face[self.fl] = flag
        face.normal_update()
        if face.calc_area() < 1e-9:
            self.bm.faces.remove(face)
            return None
        tile = TILE.get(mat, 0.5)
        n = face.normal
        uvl, cl, ml = self.uvl, self.cl, self.ml
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        isdict_c = isinstance(col, dict)
        iscall_c = callable(col)
        for l in face.loops:
            p = l.vert.co
            if uv == 'box' or uv == 'swap':
                if az >= ax and az >= ay:
                    u, w = p.x, p.y
                elif ax >= ay:
                    u, w = (p.y if n.x > 0 else -p.y), p.z
                else:
                    u, w = (-p.x if n.y > 0 else p.x), p.z
                if uv == 'swap':
                    u, w = w, u
            elif isinstance(uv, dict):
                u, w = uv[l.vert]
            elif callable(uv):
                u, w = uv(p)
            else:  # (uaxis, vaxis) world-space vectors
                u, w = p.dot(uv[0]), p.dot(uv[1])
            l[uvl].uv = ((u + uvo[0]) / tile, (w + uvo[1]) / tile)
            c = col[l.vert] if isdict_c else (col(p) if iscall_c else col)
            l[cl] = (c[0], c[1], c[2], 1.0)
            l[ml] = moss[l.vert] if isinstance(moss, dict) else moss
        return face

    def quad(self, pts, mat, col=WHITE, double=False, back_col=None, nh=None, **kw):
        """Face from local points (CCW from outside). nh = optional outward direction hint (local)."""
        pts = [V(p) for p in pts]
        if nh is not None:
            nrm = V((0, 0, 0))
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                nrm += V(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
            if nrm.dot(V(nh)) < 0:
                pts.reverse()
        if double:
            # the two sides are 2 x SEP apart, each pushed along its own normal (no coincident faces ->
            # no shadow acne / z-fighting between the twins)
            nrm = V((0, 0, 0))
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                nrm += V(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
            if nrm.length > 1e-9:
                nrm.normalize()
            vs = [self.v(p + nrm * self.SEP) for p in pts]
            fa = self.f(vs, mat, col, **kw)
            vs2 = [self.v(p - nrm * self.SEP) for p in reversed(pts)]
            self.f(vs2, mat, back_col or col, **kw)
            return fa
        vs = [self.v(p) for p in pts]
        fa = self.f(vs, mat, col, **kw)
        return fa

    # -- loft: the generic closed primitive -----------------------------------
    def loft(self, r0, r1, mat, col=WHITE, caps=(True, True), skip=(), smooth=False, uv='box', uvo=None,
             col1=None, flag=0, moss=0.0, cap_col=None, cap_mat=None):
        """Two rings with the same point count, each CCW around the direction ring0 -> ring1."""
        n = len(r0)
        v0 = [self.v(p) for p in r0]
        v1 = [self.v(p) for p in r1]
        if uvo is None:
            uvo = self._auto_uvo(mat)
        cmap = None
        if col1 is not None:
            cmap = {}
            for a in v0:
                cmap[a] = col
            for b in v1:
                cmap[b] = col1
        cc = cmap if cmap is not None else col
        if uv in ('along', 'around'):
            c0 = sum((a.co for a in v0), V((0, 0, 0))) / n
            c1 = sum((b.co for b in v1), V((0, 0, 0))) / n
            axis = (c1 - c0)
            if axis.length < 1e-9:
                axis = V((0, 0, 1))
            axis.normalize()
            cum = 0.0
        for i in range(n):
            j = (i + 1) % n
            quad = [v0[i], v0[j], v1[j], v1[i]]
            if i in skip:
                if uv in ('along', 'around'):
                    e = v0[j].co - v0[i].co
                    cum += (e - axis * e.dot(axis)).length
                continue
            if uv in ('along', 'around'):
                e = v0[j].co - v0[i].co
                e = e - axis * e.dot(axis)
                if e.length < 1e-6:
                    e = v1[j].co - v1[i].co
                    e = e - axis * e.dot(axis)
                el = e.length
                ua = e.normalized() if el > 1e-9 else V((1, 0, 0))
                d = {}
                for q in quad:
                    uu = cum + (q.co - v0[i].co).dot(ua)
                    ww = (q.co - c0).dot(axis)
                    d[q] = (uu, ww) if uv == 'along' else (ww, uu)
                cum += el
                self.f(quad, mat, cc, uv=d, smooth=smooth, flag=flag, uvo=uvo, moss=moss)
            else:
                self.f(quad, mat, cc, uv=uv, smooth=smooth, flag=flag, uvo=uvo, moss=moss)
        cm = cap_mat or mat
        cuv = 'box' if uv in ('along', 'around') else uv
        if caps[0]:
            self.f(list(reversed(v0)), cm, cap_col or col, uv=cuv, flag=flag, uvo=uvo, moss=moss)
        if caps[1]:
            self.f(v1, cm, cap_col or (col1 if col1 is not None else col), uv=cuv, flag=flag, uvo=uvo, moss=moss)
        return v0, v1

    def box(self, mn, mx, mat, col=WHITE, skip=(), taper=(1.0, 1.0), shift=(0.0, 0.0), uv='box', **kw):
        """Axis-aligned box. skip: any of '-x','+x','-y','+y','-z','+z'. taper = top scale (x, y)."""
        x0, x1 = min(mn[0], mx[0]), max(mn[0], mx[0])
        y0, y1 = min(mn[1], mx[1]), max(mn[1], mx[1])
        z0, z1 = min(mn[2], mx[2]), max(mn[2], mx[2])
        cx, cy = (x0 + x1) / 2 + shift[0], (y0 + y1) / 2 + shift[1]
        hx, hy = (x1 - x0) / 2 * taper[0], (y1 - y0) / 2 * taper[1]
        r0 = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
        r1 = [(cx - hx, cy - hy, z1), (cx + hx, cy - hy, z1), (cx + hx, cy + hy, z1), (cx - hx, cy + hy, z1)]
        names = ['-y', '+x', '+y', '-x']
        sk = [i for i, nme in enumerate(names) if nme in skip]
        return self.loft(r0, r1, mat, col, caps=('-z' not in skip, '+z' not in skip), skip=sk, uv=uv, **kw)

    def cbox(self, c, s, mat, col=WHITE, **kw):
        return self.box((c[0] - s[0] / 2, c[1] - s[1] / 2, c[2] - s[2] / 2),
                        (c[0] + s[0] / 2, c[1] + s[1] / 2, c[2] + s[2] / 2), mat, col, **kw)

    def beam(self, p0, p1, w, h, mat='M_wood_planks', col=None, up=(0, 0, 1), skip=(), taper=1.0, uv='along',
             **kw):
        """Oriented box from p0 to p1; w = size across (side = up x dir), h = size along `up`.
        skip: any of '-u','+s','+u','-s','c0','c1'."""
        if col is None:
            col = self.jit(PAL['beam'])
        p0, p1 = V(p0), V(p1)
        d = p1 - p0
        if d.length < 1e-6:
            return
        d.normalize()
        up = V(up)
        if abs(d.dot(up)) > 0.999:
            up = V((0, 1, 0)) if abs(d.y) < 0.9 else V((1, 0, 0))
        s = up.cross(d).normalized()
        u = d.cross(s)
        a, b = s * (w / 2), u * (h / 2)
        r0 = [p0 - a - b, p0 + a - b, p0 + a + b, p0 - a + b]
        a, b = a * taper, b * taper
        r1 = [p1 - a - b, p1 + a - b, p1 + a + b, p1 - a + b]
        names = ['-u', '+s', '+u', '-s']
        sk = [i for i, nme in enumerate(names) if nme in skip]
        return self.loft(r0, r1, mat, col, caps=('c0' not in skip, 'c1' not in skip), skip=sk, uv=uv, **kw)

    def cyl(self, p0, p1, r0, r1=None, n=8, mat='M_wood_planks', col=WHITE, caps=(True, True), smooth=True,
            uv='along', phase=0.0, sx=1.0, **kw):
        """Cylinder / cone frustum between two points (r1 = 0 -> cone)."""
        if r1 is None:
            r1 = r0
        p0, p1 = V(p0), V(p1)
        d = (p1 - p0).normalized()
        ref = V((0, 0, 1)) if abs(d.z) < 0.9 else V((1, 0, 0))
        s = ref.cross(d).normalized()
        u = d.cross(s)
        ring0, ring1 = [], []
        for i in range(n):
            a = phase + 2 * PI * i / n
            o = s * (math.cos(a) * sx) + u * math.sin(a)
            ring0.append(p0 + o * r0)
            ring1.append(p1 + o * r1)
        if r1 < 1e-6:
            v0 = [self.v(p) for p in ring0]
            apex = self.v(p1)
            uvo = kw.pop('uvo', None) or self._auto_uvo(mat)
            for i in range(n):
                self.f([v0[i], v0[(i + 1) % n], apex], mat, col, smooth=smooth, uvo=uvo, flag=kw.get('flag', 0))
            if caps[0]:
                self.f(list(reversed(v0)), mat, col, uvo=uvo, flag=kw.get('flag', 0))
            return
        return self.loft(ring0, ring1, mat, col, caps=caps, smooth=smooth, uv=uv, **kw)

    def lathe(self, c, prof, n=10, mat='M_wood_planks', col=WHITE, smooth=True, cap0=False, cap1=False, split=(),
              sx=1.0, sy=1.0, phase=0.0, colfn=None, deform=None, flag=0, uvo=None):
        """Revolve a profile [(r, z), ...] (bottom to top = outward normals) around the vertical axis at c.
        split: profile indices that get a hard edge. colfn(k, r, z) -> colour per profile point."""
        c = V(c)
        if uvo is None:
            uvo = self._auto_uvo(mat)
        rmax = max(p[0] for p in prof) or 1.0

        def ring(k):
            rr, zz = prof[k]
            if rr < 1e-6:
                p = c + V((0, 0, zz))
                if deform:
                    p = deform(p)
                vv = self.v(p)
                return [vv] * n
            out = []
            for i in range(n):
                a = phase + 2 * PI * i / n
                p = c + V((math.cos(a) * rr * sx, math.sin(a) * rr * sy, zz))
                if deform:
                    p = deform(p)
                out.append(self.v(p))
            return out

        rings = [ring(0)]
        plen = [0.0]
        for k in range(1, len(prof)):
            plen.append(plen[-1] + math.hypot(prof[k][0] - prof[k - 1][0], prof[k][1] - prof[k - 1][1]))
        first = rings[0]
        prev = first
        last = first
        for k in range(1, len(prof)):
            nxt = ring(k)
            ca = colfn(k - 1, *prof[k - 1]) if colfn else col
            cb = colfn(k, *prof[k]) if colfn else col
            for i in range(n):
                j = (i + 1) % n
                quad = [prev[i], prev[j], nxt[j], nxt[i]]
                cm = {prev[i]: ca, prev[j]: ca, nxt[j]: cb, nxt[i]: cb}
                u0 = 2 * PI * rmax * i / n
                u1 = 2 * PI * rmax * (i + 1) / n
                d = {prev[i]: (u0, plen[k - 1]), prev[j]: (u1, plen[k - 1]), nxt[j]: (u1, plen[k]),
                     nxt[i]: (u0, plen[k])}
                # collapsed rings share one vert: give it the mean u
                self.f(quad, mat, cm, uv=d, smooth=smooth, flag=flag, uvo=uvo)
            last = nxt
            prev = ring(k) if (k in split and k < len(prof) - 1) else nxt
        if cap0 and prof[0][0] > 1e-6:
            self.f(list(reversed(first)), mat, colfn(0, *prof[0]) if colfn else col, flag=flag, uvo=uvo)
        if cap1 and prof[-1][0] > 1e-6:
            self.f(last, mat, colfn(len(prof) - 1, *prof[-1]) if colfn else col, flag=flag, uvo=uvo)

    def blob(self, c, rad, nu=6, nv=4, mat='M_cloth', col=WHITE, deform=None, zmin=-1.0, **kw):
        """Low-poly ellipsoid (sacks, loaves, cabbages...). zmin (-1..1) cuts the bottom flat."""
        prof = []
        a0 = math.asin(clamp(zmin, -1, 1))
        for i in range(nv + 1):
            a = a0 + (PI / 2 - a0) * i / nv
            prof.append((math.cos(a) if i < nv else 0.0, math.sin(a) * rad[2]))
        if zmin <= -0.999:
            prof[0] = (0.0, -rad[2])
        self.lathe(c, prof, n=nu, mat=mat, col=col, sx=rad[0], sy=rad[1], deform=deform,
                   cap0=(zmin > -0.999), **kw)

    def grid(self, rows, mat, col=WHITE, double=False, smooth=True, flip=False, uv='box', flag=0, colfn=None,
             uvo=(0.0, 0.0), moss=0.0, back_col=None):
        """Sheet from a 2D array of local points rows[j][i]. Normal = i-dir x j-dir (flip to reverse)."""
        rows = [[V(p) for p in row] for row in rows]
        nj = len(rows)

        def nrm_at(j, i):
            ni = len(rows[j])
            a = rows[j][min(i + 1, ni - 1)] - rows[j][max(i - 1, 0)]
            b = rows[min(j + 1, nj - 1)][min(i, len(rows[min(j + 1, nj - 1)]) - 1)] -                 rows[max(j - 1, 0)][min(i, len(rows[max(j - 1, 0)]) - 1)]
            n = a.cross(b)
            return n.normalized() if n.length > 1e-9 else V((0, 0, 0))

        def build(fl, cc):
            if double:
                sg = -self.SEP if fl else self.SEP
                vg = [[self.v(p + nrm_at(j, i) * sg) for i, p in enumerate(row)] for j, row in enumerate(rows)]
            else:
                vg = [[self.v(p) for p in row] for row in rows]
            for j in range(len(rows) - 1):
                for i in range(len(rows[j]) - 1):
                    q = [vg[j][i], vg[j][i + 1], vg[j + 1][i + 1], vg[j + 1][i]]
                    if fl:
                        q.reverse()
                    c = cc
                    if colfn:
                        c = {x: colfn(x.co) for x in q}
                    self.f(q, mat, c, uv=uv, smooth=smooth, flag=flag, uvo=uvo, moss=moss)
            return vg
        vg = build(flip, col)
        if double:
            build(not flip, back_col or col)
        return vg

    def prism(self, poly, off, mat, col=WHITE, **kw):
        """Extrude a planar polygon (local points) by the vector `off`."""
        poly = [V(p) for p in poly]
        off = V(off)
        nrm = V((0, 0, 0))
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            nrm += V(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        if nrm.dot(off) < 0:
            poly.reverse()
        return self.loft(poly, [p + off for p in poly], mat, col, **kw)

    def tube(self, pts, rad, n=4, mat='M_rope', col=None, caps=True, smooth=True, flag=0):
        """Thin tube along a polyline (ropes, chains, curved branches). rad: number or list."""
        col = col or PAL['rope']
        pts = [V(p) for p in pts]
        if not isinstance(rad, (list, tuple)):
            rad = [rad] * len(pts)
        rings = []
        ref = None
        cum = 0.0
        cums = []
        for k, p in enumerate(pts):
            if k == 0:
                d = pts[1] - pts[0]
            elif k == len(pts) - 1:
                d = pts[-1] - pts[-2]
            else:
                d = (pts[k + 1] - pts[k - 1])
                cum += (pts[k] - pts[k - 1]).length
            if k == len(pts) - 1:
                cum += (pts[k] - pts[k - 1]).length
            cums.append(cum)
            d.normalize()
            if ref is None:
                ref = V((0, 0, 1)) if abs(d.z) < 0.9 else V((1, 0, 0))
            s = ref.cross(d)
            if s.length < 1e-6:
                s = V((1, 0, 0)).cross(d)
            s.normalize()
            u = d.cross(s)
            ref = u
            rings.append([self.v(p + (s * math.cos(2 * PI * i / n) + u * math.sin(2 * PI * i / n)) * rad[k])
                          for i in range(n)])
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            for i in range(n):
                j = (i + 1) % n
                per = 2 * PI * rad[k]
                d = {a[i]: (per * i / n, cums[k]), a[j]: (per * (i + 1) / n, cums[k]),
                     b[j]: (per * (i + 1) / n, cums[k + 1]), b[i]: (per * i / n, cums[k + 1])}
                self.f([a[i], a[j], b[j], b[i]], mat, col, uv=d, smooth=smooth, flag=flag)
        if caps:
            self.f(list(reversed(rings[0])), mat, col, flag=flag)
            self.f(rings[-1], mat, col, flag=flag)

    def boards(self, o, ua, va, length, width, count, thick=0.03, mat='M_wood_planks', col=None, gap=0.012,
               jit=0.02, skip=('-u',), lj=0.0, cj=0.08):
        """`count` boards running along `ua` (length), laid side by side along `va` (total `width`),
        thickness along ua x va... (normal = va x ua flipped so that it equals `ua` x `va`)."""
        o, ua, va = V(o), V(ua).normalized(), V(va).normalized()
        nrm = ua.cross(va).normalized()
        col = col or PAL['plank']
        bw = width / count
        for i in range(count):
            c0 = o + va * (bw * (i + 0.5)) + nrm * (thick / 2 + self.r(0, jit) * 0.3)
            l0 = self.r(0, lj)
            l1 = length - self.r(0, lj)
            self.beam(c0 + ua * l0, c0 + ua * l1, bw - gap, thick, mat, self.jit(col, cj), up=nrm, skip=skip)

    # -- special nodes -------------------------------------------------------
    def col(self, name, mn, mx, rz=0.0):
        """Collider from min/max corners (before the optional Z rotation around its centre)."""
        c = ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2)
        s = (abs(mx[0] - mn[0]), abs(mx[1] - mn[1]), abs(mx[2] - mn[2]))
        self.cols.append((name, c, s, rz))

    def walk(self, name, mn, mx, rz=0.0):
        c = ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2)
        s = (abs(mx[0] - mn[0]), abs(mx[1] - mn[1]), abs(mx[2] - mn[2]))
        self.walks.append((name, c, s, rz))

    def empty(self, name, pos):
        self.empties.append((name, tuple(pos)))

    def sub(self, name, origin, seed=11):
        k = Kit(name, seed=seed, origin=origin)
        self.subs.append(k)
        return k

    # -- bake: AO + dirt + moss + soot ------------------------------------------
    def bake(self, ao_dist=1.5, ao_min=0.32, ground=True, dirt_h=0.7, dirt=0.3, moss=1.0, samples=14,
             ao_pow=1.0, north_moss=0.0):
        bm = self.bm
        bm.normal_update()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        vs = [v.co.copy() for v in bm.verts]
        polys = [[v.index for v in f.verts] for f in bm.faces]
        if ground:
            b = len(vs)
            R = 200.0
            vs += [V((-R, -R, -0.002)), V((R, -R, -0.002)), V((R, R, -0.002)), V((-R, R, -0.002))]
            polys.append([b, b + 1, b + 2, b + 3])
        bvh = BVHTree.FromPolygons(vs, polys, all_triangles=False)
        # cosine-weighted hemisphere directions (z = normal)
        dirs = []
        for i in range(samples):
            u = (i + 0.5) / samples
            ph = i * 2.399963
            rr = math.sqrt(u)
            dirs.append(V((rr * math.cos(ph), rr * math.sin(ph), math.sqrt(1 - u))))
        cl, ml, fl = self.cl, self.ml, self.fl
        roofm = set(self.mi(m) for m in ('M_roof_tiles', 'M_thatch') if m in self.mats)
        emis = set(self.mi(m) for m in ('M_ember', 'M_window_glow', 'M_crystal') if m in self.mats)
        vcache = {}
        dirt_c = (0.62, 0.55, 0.45)
        moss_c = (0.62, 0.82, 0.42)
        north_c = (0.80, 0.90, 0.70)
        soot_c = (0.22, 0.20, 0.19)

        def ao_at(p, n):
            ref = V((0, 0, 1)) if abs(n.z) < 0.9 else V((1, 0, 0))
            t = ref.cross(n).normalized()
            b2 = n.cross(t)
            occ = 0.0
            for d in dirs:
                w = t * d.x + b2 * d.y + n * d.z
                loc, hn, idx, dist = bvh.ray_cast(p, w, ao_dist)
                if loc is not None and hn.dot(w) < 0.0:
                    q = 1.0 - dist / ao_dist
                    occ += q
            return 1.0 - occ / len(dirs)

        for f in bm.faces:
            if f[fl] & NOAO or f.material_index in emis:
                continue
            n = f.normal
            cen = f.calc_center_median()
            isroof = f.material_index in roofm
            for l in f.loops:
                co = l.vert.co
                if f.smooth:
                    key = l.vert.index
                    a = vcache.get(key)
                    if a is None:
                        vn = l.vert.normal
                        a = ao_at(co + vn * 0.03, vn)
                        vcache[key] = a
                else:
                    tc = cen - co
                    dl = tc.length
                    if dl > 1e-6:
                        tc = tc * (min(dl * 0.3, 0.07) / dl)
                    a = ao_at(co + tc + n * 0.025, n)
                a = a ** ao_pow
                m = ao_min + (1.0 - ao_min) * a
                c = l[cl]
                r, g, b = c[0] * m, c[1] * m, c[2] * m
                # ground dirt
                if dirt > 0 and co.z < dirt_h:
                    t = (1.0 - sstep(0.0, dirt_h, co.z)) * dirt
                    r, g, b = r * lerp(1, dirt_c[0], t), g * lerp(1, dirt_c[1], t), b * lerp(1, dirt_c[2], t)
                # moss (authored weight * orientation * noise)
                mw = l[ml] * moss
                if mw > 0.0:
                    nz = mnoise.noise(co * 0.9) * 0.5 + 0.5
                    ori = 0.45 + 0.55 * clamp(n.y * 1.4 + 0.3)
                    t = clamp(mw * ori * (0.35 + 1.1 * nz))
                    r, g, b = r * lerp(1, moss_c[0], t), g * lerp(1, moss_c[1], t), b * lerp(1, moss_c[2], t)
                if north_moss > 0 and n.y > 0.3 and not isroof:
                    t = north_moss * clamp(n.y) * (1.0 - sstep(0.2, 2.5, co.z))
                    r, g, b = r * lerp(1, north_c[0], t), g * lerp(1, north_c[1], t), b * lerp(1, north_c[2], t)
                for sp, sr, ss in self.soot:
                    dd = (co - sp).length
                    if dd < sr:
                        t = (1.0 - dd / sr) ** 1.3 * ss
                        r, g, b = r * lerp(1, soot_c[0], t), g * lerp(1, soot_c[1], t), b * lerp(1, soot_c[2], t)
                l[cl] = (r, g, b, 1.0)

    def warp(self, amp=0.02, freq=0.35, zfree=0.4):
        """Low-frequency wobble so nothing is perfectly straight (keeps the ground contact)."""
        for vtx in self.bm.verts:
            p = vtx.co
            d = mnoise.noise_vector(p * freq + V((3.1, 7.7, 1.3)))
            k = sstep(0.0, zfree, p.z)
            vtx.co = p + V((d.x * amp, d.y * amp, d.z * amp * 0.6 * k)) * (0.35 + 0.65 * k)

    def to_object(self):
        bm = self.bm
        bm.faces.layers.int.remove(self.fl)
        bm.loops.layers.float.remove(self.ml)
        if self.origin.length > 0:
            bmesh.ops.translate(bm, verts=bm.verts[:], vec=-self.origin)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(self.name, me)
        link(ob)
        ob.location = self.origin
        for m in self.mats:
            me.materials.append(get_mat(m))
        attr = me.color_attributes.get('Col')
        if attr is not None:
            me.color_attributes.active_color = attr
            me.color_attributes.render_color_index = list(me.color_attributes).index(attr)
        return ob

    def finish(self):
        """bake + create objects. Returns (main object, all export objects)."""
        args = dict(self.bake_args)
        wamp = args.pop('warp', 0.0)
        if wamp:
            self.warp(wamp)
        self.bake(**args)
        main = self.to_object()
        objs = [main]
        for s in self.subs:
            a2 = dict(s.bake_args)
            a2.pop('warp', None)
            a2.setdefault('ground', False)
            s.bake(**a2)
            so = s.to_object()
            so.parent = main
            objs.append(so)
        for name, c, s, rz in self.cols:
            objs.append(add_collider_box(name, c, s, rz, parent=main))
        for name, c, s, rz in self.walks:
            o = add_collider_box(name, c, s, rz, parent=main)
            o.name = 'WALK_' + name
            o.data.name = 'WALK_' + name
            objs.append(o)
        for name, pos in self.empties:
            objs.append(add_empty(name, pos, parent=main))
        return main, objs


# ----------------------------------------------------------------------------- walls
class Wall:
    """Vertical wall plane from 2D point a to b (exterior on the RIGHT when walking a -> b, i.e. list the
    walls counter-clockwise seen from above), between heights z0 and z1."""

    def __init__(self, a, b, z0, z1):
        self.a = V((a[0], a[1], 0.0))
        self.b = V((b[0], b[1], 0.0))
        d = self.b - self.a
        self.L = d.length
        self.d = d.normalized()
        self.n = V((self.d.y, -self.d.x, 0.0))
        self.z0, self.z1 = z0, z1

    def P(self, s, t, off=0.0):
        return self.a + self.d * s + self.n * off + V((0, 0, t))


def wbeam(k, w, s0, t0, s1, t1, bw=0.15, proud=0.035, depth=0.07, col=None, caps=(False, False), mat='M_wood_planks',
          sides=True):
    """Timber lying on a wall face (back face never built)."""
    skip = ['-u']
    if not caps[0]:
        skip.append('c0')
    if not caps[1]:
        skip.append('c1')
    if not sides:
        skip += ['+s', '-s']
    off = proud - depth / 2
    k.beam(w.P(s0, t0, off), w.P(s1, t1, off), bw, depth, mat, col or k.jit(PAL['beam']), up=w.n, skip=skip)


def wall_surface(k, w, scuts=None, tcuts=None, mat='M_plaster', col=None, off=0.0, uv='box', tint=0.07):
    """Plain wall surface as a grid (vertices carry AO + stain variation)."""
    base = col or PAL['plaster']
    if scuts is None:
        n = max(1, int(round(w.L / 1.5)))
        scuts = [w.L * i / n for i in range(n + 1)]
    if tcuts is None:
        h = w.z1 - w.z0
        tcuts = [w.z0, w.z0 + min(0.5, h * 0.3), w.z1 - min(0.5, h * 0.3), w.z1] if h > 1.3 else [w.z0, w.z1]
    rows = [[w.P(s, t, off) for s in scuts] for t in tcuts]

    def cf(p):
        nz = mnoise.noise(p * 0.7 + V((5.0, 1.0, 2.0)))
        return mulc(base, 1.0 + tint * nz)
    k.grid(rows, mat, base, smooth=False, colfn=cf, uv=uv)


def frame_wall(k, w, posts=None, bay=1.25, rails=(), braces=(), openings=(), bw=0.15, proud=0.035, pcol=None,
               bcol=None, sill=True, plate=True, infill='M_plaster', ends=False, studs=True):
    """Half-timbered wall: infill grid + sill, plate, studs, rails and braces (all avoiding `openings`,
    a list of (s0, s1, t0, t1) rectangles returned by window()/door())."""
    bcol = bcol or PAL['beam']
    z0, z1, Lw = w.z0, w.z1, w.L
    if posts is None:
        n = max(1, int(round(Lw / bay)))
        posts = [Lw * i / n for i in range(1, n)]
    posts = sorted(posts)
    scuts = [0.0] + list(posts) + [Lw]
    tc = sorted(set([z0, z1] + [t for t in rails if z0 + 0.2 < t < z1 - 0.2]))
    if len(tc) == 2 and (z1 - z0) > 1.3:
        tc = [z0, z0 + 0.5, z1 - 0.5, z1]
    wall_surface(k, w, scuts, tc, mat=infill, col=pcol, uv='box')

    def col():
        return k.jit(bcol, 0.1)

    def hsegs(t, s0, s1, half):
        """horizontal beam at height t from s0 to s1, cut by openings"""
        segs = [(s0, s1)]
        for (a, b, c, d) in openings:
            if c - half < t < d + half:
                nseg = []
                for (x0, x1) in segs:
                    if b <= x0 or a >= x1:
                        nseg.append((x0, x1))
                    else:
                        if a - x0 > 0.05:
                            nseg.append((x0, a))
                        if x1 - b > 0.05:
                            nseg.append((b, x1))
                segs = nseg
        return segs

    def vsegs(s, t0, t1, half):
        segs = [(t0, t1)]
        for (a, b, c, d) in openings:
            if a - half < s < b + half:
                nseg = []
                for (x0, x1) in segs:
                    if d <= x0 or c >= x1:
                        nseg.append((x0, x1))
                    else:
                        if c - x0 > 0.15:
                            nseg.append((x0, c))
                        if x1 - d > 0.15:
                            nseg.append((d, x1))
                segs = nseg
        return segs

    if sill:
        for (a, b) in hsegs(z0 + bw / 2, 0, Lw, bw / 2):
            wbeam(k, w, a, z0 + bw / 2, b, z0 + bw / 2, bw, proud, col=col())
    if plate:
        for (a, b) in hsegs(z1 - bw / 2, 0, Lw, bw / 2):
            wbeam(k, w, a, z1 - bw / 2, b, z1 - bw / 2, bw, proud, col=col())
    lo = z0 + (bw if sill else 0)
    hi = z1 - (bw if plate else 0)
    if studs:
        plist = list(posts)
        if ends:
            plist = [bw / 2] + plist + [Lw - bw / 2]
        for s in plist:
            for (a, b) in vsegs(s, lo, hi, bw / 2):
                wbeam(k, w, s, a, s, b, bw * k.r(0.9, 1.05), proud - 0.003, col=col())
    for t in rails:
        for (a, b) in hsegs(t, 0, Lw, bw / 2):
            wbeam(k, w, a, t, b, t, bw * 0.85, proud - 0.007, col=col())
    for br in braces:
        bi, kind = br[0], br[1]
        tlo, thi = (br[2], br[3]) if len(br) > 2 else (lo, hi)
        s0, s1 = scuts[bi] + bw * 0.3, scuts[bi + 1] - bw * 0.3
        bwid = bw * 0.8
        pr = proud - 0.012
        if kind in ('/', 'X'):
            wbeam(k, w, s0, tlo, s1, thi, bwid, pr, col=col())
        if kind in ('\\', 'X'):
            wbeam(k, w, s0, thi, s1, tlo, bwid, pr - (0.004 if kind == 'X' else 0), col=col())
        if kind == '^':
            sm = (s0 + s1) / 2
            wbeam(k, w, s0, tlo, sm, thi, bwid, pr, col=col())
            wbeam(k, w, s1, tlo, sm, thi, bwid, pr, col=col())
        if kind == 'v':
            sm = (s0 + s1) / 2
            wbeam(k, w, s0, thi, sm, tlo, bwid, pr, col=col())
            wbeam(k, w, s1, thi, sm, tlo, bwid, pr, col=col())
        if kind == 'k':     # short knee braces in the upper corners
            hh = min(0.9, (thi - tlo) * 0.45)
            wbeam(k, w, s0, thi - hh, s0 + hh, thi, bwid, pr, col=col())
            wbeam(k, w, s1, thi - hh, s1 - hh, thi, bwid, pr, col=col())
    return scuts


def frame_gable(k, w, rise, bw=0.15, proud=0.035, pcol=None, bcol=None, pattern='king', infill='M_plaster',
                tie=True, apex_s=None):
    """Triangular gable above w.z0 (w.z1 is ignored); apex at mid span, `rise` above z0."""
    bcol = bcol or PAL['beam']
    base = pcol or PAL['plaster']
    Lw, z0 = w.L, w.z0
    sm = Lw / 2 if apex_s is None else apex_s

    def zr(s):      # underside of the roof at s
        return z0 + rise * (s / sm if s <= sm else (Lw - s) / (Lw - sm))

    def cf(p):
        return mulc(base, 1.0 + 0.07 * mnoise.noise(p * 0.7 + V((5.0, 1.0, 2.0))))
    # infill: fan of quads/triangles (4 columns)
    cuts = [0.0, sm * 0.5, sm, sm + (Lw - sm) * 0.5, Lw]
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        pts = [w.P(a, z0), w.P(b, z0), w.P(b, zr(b)), w.P(a, zr(a))]
        vs = [k.v(p) for p in pts]
        k.f(vs, infill, {x: cf(x.co) for x in vs})

    def col():
        return k.jit(bcol, 0.1)
    th = math.atan2(rise, sm)
    dz = bw / 2 / math.cos(th)
    if tie:
        wbeam(k, w, 0, z0 + bw / 2, Lw, z0 + bw / 2, bw, proud, col=col())
    # rakes
    wbeam(k, w, 0, z0 - dz * 0.2, sm, z0 + rise - dz * 1.2, bw, proud - 0.004, col=col())
    wbeam(k, w, Lw, z0 - dz * 0.2, sm, z0 + rise - dz * 1.2, bw, proud - 0.004, col=col())
    lo = z0 + (bw if tie else 0)
    if pattern in ('king', 'fan', 'grid'):
        wbeam(k, w, sm, lo, sm, z0 + rise - dz * 2, bw, proud - 0.006, col=col())
    if pattern == 'king':
        # collar + two struts
        tcol = z0 + rise * 0.52
        sx = sm * (1 - 0.52) + bw
        wbeam(k, w, sm - sx, tcol, sm + sx, tcol, bw * 0.85, proud - 0.009, col=col())
        wbeam(k, w, sm * 0.45, lo, sm * 0.45, zr(sm * 0.45) - dz, bw * 0.85, proud - 0.006, col=col())
        s2 = Lw - (Lw - sm) * 0.45
        wbeam(k, w, s2, lo, s2, zr(s2) - dz, bw * 0.85, proud - 0.006, col=col())
    elif pattern == 'fan':
        for fr in (0.3, 0.62):
            wbeam(k, w, sm - bw * 0.3, lo, sm * (1 - fr), zr(sm * (1 - fr)) - dz, bw * 0.8, proud - 0.011, col=col())
            wbeam(k, w, sm + bw * 0.3, lo, sm + (Lw - sm) * fr, zr(sm + (Lw - sm) * fr) - dz, bw * 0.8,
                  proud - 0.011, col=col())
    elif pattern == 'grid':
        tcol = z0 + rise * 0.45
        sx = sm * (1 - 0.45) + bw
        wbeam(k, w, sm - sx, tcol, sm + sx, tcol, bw * 0.85, proud - 0.009, col=col())
        for fr in (0.33, 0.66):
            for s in (sm * fr, Lw - (Lw - sm) * fr):
                wbeam(k, w, s, lo, s, zr(s) - dz, bw * 0.85, proud - 0.006, col=col())
    elif pattern == 'window':
        # two queen posts framing an attic window, collar above, king post on top, outer struts
        qw = min(0.62, sm * 0.3)
        tcol = min(z0 + rise * 0.62, zr(sm - qw) - dz - 0.05)
        wbeam(k, w, sm - qw, lo, sm - qw, tcol, bw * 0.9, proud - 0.006, col=col())
        wbeam(k, w, sm + qw, lo, sm + qw, tcol, bw * 0.9, proud - 0.006, col=col())
        sx = (z0 + rise - tcol) / rise * sm
        wbeam(k, w, sm - sx, tcol, sm + sx, tcol, bw * 0.85, proud - 0.009, col=col())
        wbeam(k, w, sm, tcol, sm, z0 + rise - dz * 2, bw * 0.9, proud - 0.006, col=col())
        for sgn in (-1, 1):
            s2 = sm + sgn * sm * 0.6
            wbeam(k, w, sm + sgn * (qw + bw * 0.4), lo, s2, zr(s2) - dz, bw * 0.8, proud - 0.011, col=col())
    elif pattern == 'collar':
        tcol = z0 + rise * 0.5
        sx = sm * 0.5 + bw
        wbeam(k, w, sm - sx, tcol, sm + sx, tcol, bw * 0.85, proud - 0.009, col=col())
        wbeam(k, w, sm, tcol, sm, z0 + rise - dz * 2, bw, proud - 0.006, col=col())


def window(k, w, s, t, ww=0.7, hh=0.9, fw=0.09, proud=0.065, shutters=2, bars=(1, 1), fcol=None, scol=None,
           off=0.0, glow=None, sill=True):
    """Surface-mounted window: glowing pane, timber frame, glazing bars, open shutters.
    s = centre along the wall, t = bottom of the pane. Returns the opening rectangle (s0, s1, t0, t1)."""
    fcol = fcol or PAL['beam_d']
    scol = scol or PAL['plank_d']
    glow = glow or PAL['glow']
    s0, s1, t0, t1 = s - ww / 2, s + ww / 2, t, t + hh
    # pane
    pts = [w.P(s0, t0, off + 0.012), w.P(s1, t0, off + 0.012), w.P(s1, t1, off + 0.012), w.P(s0, t1, off + 0.012)]
    k.quad(pts, 'M_window_glow', glow, flag=NOAO)
    # frame
    pr = off + proud
    wbeam(k, w, s0 - fw - (0.05 if sill else 0), t0 - fw / 2, s1 + fw + (0.05 if sill else 0), t0 - fw / 2, fw,
          pr + (0.035 if sill else 0), depth=0.1 if sill else 0.07, col=k.jit(fcol), caps=(True, True))
    wbeam(k, w, s0 - fw, t1 + fw / 2, s1 + fw, t1 + fw / 2, fw, pr, col=k.jit(fcol), caps=(True, True))
    wbeam(k, w, s0 - fw / 2, t0, s0 - fw / 2, t1, fw, pr, col=k.jit(fcol))
    wbeam(k, w, s1 + fw / 2, t0, s1 + fw / 2, t1, fw, pr, col=k.jit(fcol))
    # glazing bars
    bc = mulc(fcol, 0.8)
    for i in range(bars[0]):
        sb = s0 + ww * (i + 1) / (bars[0] + 1)
        wbeam(k, w, sb, t0, sb, t1, 0.03, off + 0.035, depth=0.03, col=bc)
    for i in range(bars[1]):
        tb = t0 + hh * (i + 1) / (bars[1] + 1)
        wbeam(k, w, s0, tb, s1, tb, 0.03, off + 0.032, depth=0.03, col=bc)
    # shutters (opened flat against the wall)
    lw = ww / 2 + 0.02
    sides = []
    if shutters in (2, 'l', 'L'):
        sides.append(-1)
    if shutters in (2, 'r', 'R'):
        sides.append(1)
    for sd in sides:
        a = (s0 - fw - lw - 0.01) if sd < 0 else (s1 + fw + 0.01)
        sc = k.jit(scol, 0.12)
        sag = k.r(-0.02, 0.02)
        c0 = w.P(a + lw / 2, t0 - 0.02 + sag, off + 0.062)
        c1 = w.P(a + lw / 2, t1 + 0.02 + sag * 0.3, off + 0.062)
        k.beam(c0, c1, lw, 0.03, 'M_wood_planks', sc, up=w.n, skip=('-u',))
        for fr in (0.2, 0.8):
            tt = t0 + hh * fr + sag
            wbeam(k, w, a + 0.02, tt, a + lw - 0.02, tt, 0.05, off + 0.088, depth=0.02, col=PAL['iron'],
                  mat='M_metal_iron', sides=False)
    return (s0 - fw, s1 + fw, t0 - fw, t1 + fw)


def door(k, w, s, t0=0.0, ww=1.0, hh=2.0, fw=0.14, proud=0.08, planks=5, col=None, fcol=None, iron=True, step=True,
         off=0.0, hinge=-1, handle=True, double=False):
    """Closed plank door with frame, strap hinges and ring pull. s = centre. Returns the opening rect."""
    col = col or PAL['door']
    fcol = fcol or PAL['beam_d']
    s0, s1, t1 = s - ww / 2, s + ww / 2, t0 + hh
    pwid = ww / planks
    for i in range(planks):
        a, b = s0 + pwid * i, s0 + pwid * (i + 1)
        o = off + 0.02 + k.r(0, 0.008)
        c = k.jit(col, 0.14)
        pts = [w.P(a + 0.004, t0, o), w.P(b - 0.004, t0, o), w.P(b - 0.004, t1, o), w.P(a + 0.004, t1, o)]
        k.quad(pts, 'M_wood_planks', c, uvo=(k.rng.random() * 2, k.rng.random() * 2))
    # dark backing (gaps between planks)
    k.quad([w.P(s0, t0, off + 0.012), w.P(s1, t0, off + 0.012), w.P(s1, t1, off + 0.012), w.P(s0, t1, off + 0.012)],
           'M_wood_planks', mulc(col, 0.25))
    pr = off + proud
    wbeam(k, w, s0 - fw / 2, t0, s0 - fw / 2, t1, fw, pr, depth=0.1, col=k.jit(fcol))
    wbeam(k, w, s1 + fw / 2, t0, s1 + fw / 2, t1, fw, pr, depth=0.1, col=k.jit(fcol))
    wbeam(k, w, s0 - fw - 0.08, t1 + fw / 2, s1 + fw + 0.08, t1 + fw / 2, fw * 1.15, pr + 0.01, depth=0.11,
          col=k.jit(fcol), caps=(True, True))
    if iron:
        leaves = [(s0, s1, hinge)] if not double else [(s0, s, -1), (s, s1, 1)]
        for (a, b, hg) in leaves:
            for fr in (0.2, 0.78):
                tt = t0 + hh * fr
                x0, x1 = (a + 0.01, a + (b - a) * 0.72) if hg < 0 else (b - (b - a) * 0.72, b - 0.01)
                wbeam(k, w, x0, tt, x1, tt, 0.07, off + 0.045, depth=0.02, col=PAL['iron'], mat='M_metal_iron',
                      caps=(True, True))
            if handle:
                hs = (b - 0.12) if hg < 0 else (a + 0.12)
                c = w.P(hs, t0 + hh * 0.5, off + 0.03)
                k.cyl(c, c + w.n * 0.05, 0.035, 0.03, n=6, mat='M_metal_iron', col=PAL['iron_l'], caps=(False, True))
    if step:
        c = w.P(s, 0, 0)
        d, n = w.d, w.n
        hw = ww / 2 + fw + 0.12
        r0 = [c - d * hw, c - d * hw + n * 0.55, c + d * hw + n * 0.55, c + d * hw]
        r0 = [V((p.x, p.y, 0.0)) for p in r0]
        if V((0, 0, 1)).dot((r0[1] - r0[0]).cross(r0[2] - r0[1])) < 0:
            r0.reverse()
        zt = max(t0, 0.08)
        cen = sum(r0, V((0, 0, 0))) / 4
        r1 = [V((cen.x + (p.x - cen.x) * 0.96, cen.y + (p.y - cen.y) * 0.96, zt)) for p in r0]
        k.loft(r0, r1, 'M_stone_wall', PAL['stone_d'], caps=(False, True))
    return (s0 - fw, s1 + fw, t0 - 0.01, t1 + fw * 1.15)


def corner_posts(k, x0, y0, x1, y1, z0, z1, bw=0.17, proud=0.04, col=None):
    """Full-height posts on the four corners of a rectangular storey."""
    col = col or PAL['beam']
    for (cx, cy, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x1, y1, 1, 1), (x0, y1, -1, 1)):
        ax, bx = sorted((cx + sx * proud, cx - sx * (bw - proud)))
        ay, by = sorted((cy + sy * proud, cy - sy * (bw - proud)))
        k.box((ax, ay, z0), (bx, by, z1), 'M_wood_planks', k.jit(col), skip=('-z', '+z'), uv='along')


def plinth(k, x0, y0, x1, y1, h=0.45, out=0.07, batter=0.05, col=None, mat='M_stone_wall', stones=6, z0=0.0,
           gaps=(), sides=(0, 1, 2, 3)):
    """Rubble-stone plinth (slightly battered) with a top ledge + a few proud stones.
    gaps: list of (side, s0, s1) left open (doors); side 0 = front (-Y), 1 = +X, 2 = back, 3 = -X,
    s measured along the wall (counter-clockwise)."""
    col = col or PAL['stone']
    a, b = out + batter, out
    z1 = z0 + h
    per = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    walls = []
    for si, (pa, pb) in enumerate(per):
        w = Wall(pa, pb, z0, z1)
        walls.append(w)
        if si not in sides:
            continue
        iv = [(0.0, w.L)]
        for (gs, g0, g1) in gaps:
            if gs != si:
                continue
            niv = []
            for (u0, u1) in iv:
                if g1 <= u0 or g0 >= u1:
                    niv.append((u0, u1))
                else:
                    if g0 > u0:
                        niv.append((u0, g0))
                    if g1 < u1:
                        niv.append((g1, u1))
            iv = niv
        for (u0, u1) in iv:
            e0a, e0b = (-a, -b) if u0 <= 0 else (0.0, 0.0)
            e1a, e1b = (a, b) if u1 >= w.L else (0.0, 0.0)
            n = max(1, int(round((u1 - u0) / 2.2)))
            for i in range(n):
                fa, fb = i / n, (i + 1) / n
                sb0, sb1 = lerp(u0 + e0a, u1 + e1a, fa), lerp(u0 + e0a, u1 + e1a, fb)
                st0, st1 = lerp(u0 + e0b, u1 + e1b, fa), lerp(u0 + e0b, u1 + e1b, fb)
                si0, si1 = lerp(u0, u1, fa), lerp(u0, u1, fb)
                k.quad([w.P(sb0, z0, a), w.P(sb1, z0, a), w.P(st1, z1, b), w.P(st0, z1, b)], mat, col)
                k.quad([w.P(st0, z1, b), w.P(st1, z1, b), w.P(si1, z1, 0), w.P(si0, z1, 0)], mat, col)
            if u0 > 0:
                k.quad([w.P(u0, z0, 0), w.P(u0, z0, a), w.P(u0, z1, b), w.P(u0, z1, 0)], mat, mulc(col, 0.9))
            if u1 < w.L:
                k.quad([w.P(u1, z0, a), w.P(u1, z0, 0), w.P(u1, z1, 0), w.P(u1, z1, b)], mat, mulc(col, 0.9))
    for i in range(stones):
        si = i % 4
        if si not in sides:
            continue
        w = walls[si]
        sl = k.r(0.25, 0.55)
        s = k.r(0.0, w.L - sl) if i >= 4 else (0.0 if k.rng.random() < 0.5 else w.L - sl)
        if any(gs == si and g0 - sl < s < g1 for (gs, g0, g1) in gaps):
            continue
        sh = k.r(0.16, 0.26)
        t = z0 + k.r(0.02, max(0.03, h - sh - 0.02))
        o = a + k.r(0.0, 0.03) - 0.02
        p = w.P(s + sl / 2, t + sh / 2, o)
        k.beam(p - w.d * sl / 2, p + w.d * sl / 2, sh, 0.1, mat, k.jit(mulc(col, 0.95), 0.06, 0.0), up=w.n,
               skip=('-u',), uv='box')


def chimney(k, x, y, z0, z1, wx=0.75, wy=0.6, taper=0.9, cap='slab', smoke='SMOKE_chimney', mat='M_stone_wall',
            col=None, soot=1.0, band=True):
    """Stone stack from z0 to z1 with a projecting band, a dark flue and an optional raised cap slab."""
    col = col or PAL['stone']
    tx = taper
    k.box((x - wx / 2, y - wy / 2, z0), (x + wx / 2, y + wy / 2, z1), mat, col, skip=('-z',), taper=(tx, tx))
    hx, hy = wx / 2 * tx, wy / 2 * tx
    if band:
        k.box((x - hx - 0.06, y - hy - 0.06, z1 - 0.32), (x + hx + 0.06, y + hy + 0.06, z1 - 0.2), mat,
              k.jit(col, 0.05, 0), skip=())
    # flue
    k.quad([(x - hx + 0.1, y - hy + 0.1, z1 + 0.004), (x + hx - 0.1, y - hy + 0.1, z1 + 0.004),
            (x + hx - 0.1, y + hy - 0.1, z1 + 0.004), (x - hx + 0.1, y + hy - 0.1, z1 + 0.004)], mat, PAL['dark'],
           flag=NOAO)
    top = z1
    if cap == 'slab':
        for sx in (-1, 1):
            for sy in (-1, 1):
                k.cbox((x + sx * (hx - 0.07), y + sy * (hy - 0.07), z1 + 0.09), (0.14, 0.14, 0.18), mat,
                       mulc(col, 0.9), skip=('-z', '+z'))
        k.box((x - hx - 0.05, y - hy - 0.05, z1 + 0.18), (x + hx + 0.05, y + hy + 0.05, z1 + 0.26), mat,
              mulc(col, 0.92))
        top = z1 + 0.26
    elif cap == 'pots':
        for sx in (-0.5, 0.5):
            k.cyl((x + sx * hx, y, z1), (x + sx * hx, y, z1 + 0.3), 0.11, 0.09, n=6, mat='M_roof_tiles',
                  col=PAL['tile_d'], caps=(False, True))
        top = z1 + 0.3
    if soot:
        k.soot.append((V((x, y, z1 + 0.1)), 1.5, 0.75 * soot))
    if smoke:
        k.empty(smoke, (x, y, top + 0.05))
    return top


# ----------------------------------------------------------------------------- roofs
def roof_plane(k, e0, e1, r1, r0, tv=0.14, nu=4, nv=3, mat='M_roof_tiles', col=None, under_mat='M_wood_planks',
               under_col=None, sag=0.0, wob=0.0, undercut=0.0, edges=('eave', 'v0', 'v1'), moss=1.0,
               under=True, lip=0.0, bulge=0.0, round_eave=0.0):
    """One roof slope with thickness. e0 -> e1 = eave edge of the UNDERSIDE plane (running counter-clockwise
    around the building seen from above), r0/r1 = ridge ends above e0/e1. tv = vertical thickness.
    edges: which rim faces to build: 'eave', 'v0' (verge at e0), 'v1', 'top' (ridge side, for lean-tos)."""
    e0, e1, r0, r1 = V(e0), V(e1), V(r0), V(r1)
    col = col or (PAL['thatch'] if mat == 'M_thatch' else PAL['tile'])
    under_col = under_col or (PAL['thatch_old'] if under_mat == 'M_thatch' else PAL['beam_d'])
    up = V((0, 0, tv))

    def P(fu, fv, top):
        a = e0.lerp(e1, fu)
        b = r0.lerp(r1, fu)
        p = a.lerp(b, fv)
        p.z -= sag * 4 * fu * (1 - fu) * (0.3 + 0.7 * fv)
        if top:
            p = p + up
            if bulge:
                p.z += bulge * math.sin(PI * min(1.0, fv * 1.15)) ** 0.8
            if wob:
                q = k.W(p)
                p.z += wob * mnoise.noise(V((q.x * 1.1, q.y * 1.1, q.z * 0.5)))
            if lip and fv == 0.0:
                p.z += lip
            if round_eave and fv == 0.0:
                p.z -= round_eave
        return p

    uax = (e1 - e0).normalized()
    sl = ((r0 + r1) * 0.5 - (e0 + e1) * 0.5)
    sl = (sl - uax * sl.dot(uax)).normalized()
    R = k.M.to_3x3()
    uaxw, slw = (R @ uax).normalized(), (R @ sl).normalized()
    uvt = (uaxw, slw)
    base_col = col

    def cf(p):
        nz = mnoise.noise(p * 0.6 + V((1.7, 9.2, 4.4)))
        nz2 = mnoise.noise(p * 2.3)
        return mulc(base_col, 1.0 + 0.10 * nz + 0.05 * nz2)

    # top grid (smooth, shared verts)
    fvs = [j / nv for j in range(nv + 1)]
    if round_eave:
        fvs.insert(1, min(0.09, 0.4 / nv))
    nv = len(fvs) - 1
    tg = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            p = P(i / nu, fvs[j], True)
            if row and (p - V(row[-1][1])).length < 1e-6:
                row.append(row[-1])
            else:
                row.append((k.v(p), p))
        tg.append(row)
    for j in range(nv):
        for i in range(nu):
            q = [tg[j][i][0], tg[j][i + 1][0], tg[j + 1][i + 1][0], tg[j + 1][i][0]]
            m0, m1 = (1 - fvs[j]) ** 1.6 * moss, (1 - fvs[j + 1]) ** 1.6 * moss
            mw = {tg[j][i][0]: m0, tg[j][i + 1][0]: m0, tg[j + 1][i + 1][0]: m1, tg[j + 1][i][0]: m1}
            k.f(q, mat, {x: cf(x.co) for x in set(q)}, uv=uvt, smooth=True, moss=mw)
    ucf = undercut / max((((r0 + r1) * 0.5) - ((e0 + e1) * 0.5)).length, 1e-6)
    # underside
    ub = [P(i / nu, ucf, False) for i in range(nu + 1)]
    ut = [P(i / nu, 1.0, False) for i in range(nu + 1)]
    if under:
        for i in range(nu):
            k.quad([ub[i], ut[i], ut[i + 1], ub[i + 1]], under_mat, under_col, uv=uvt)
    if 'eave' in edges:
        for i in range(nu):
            vs = [k.v(ub[i]), k.v(ub[i + 1]), tg[0][i + 1][0], tg[0][i][0]]
            k.f(vs, mat, {vs[0]: mulc(col, 0.72), vs[1]: mulc(col, 0.72), vs[2]: cf(vs[2].co), vs[3]: cf(vs[3].co)},
                uv='box', moss=moss * 0.8)
    for name, i, flip in (('v0', 0, False), ('v1', nu, True)):
        if name not in edges:
            continue
        fu = i / nu
        for j in range(nv):
            fa = max(fvs[j], ucf)
            fb = max(fvs[j + 1], ucf)
            pu0, pu1 = P(fu, fa, False), P(fu, fb, False)
            vs = [k.v(pu0), tg[j][i][0], tg[j + 1][i][0], k.v(pu1)]
            if flip:
                vs.reverse()
            k.f(vs, mat, mulc(col, 0.85), uv='box', moss=moss * 0.3)
    if 'top' in edges:
        for i in range(nu):
            vs = [tg[nv][i][0], tg[nv][i + 1][0], k.v(ut[i + 1]), k.v(ut[i])]
            k.f(vs, mat, mulc(col, 0.85), uv='box')
    return tg


def roof_gable(k, x0, x1, y0, y1, z_eave, rise, oe=0.45, og=0.35, tv=0.14, sag=0.1, nu=5, nv=3,
               mat='M_roof_tiles', col=None, ridge=True, barge=None, axis='x', og2=None, **kw):
    """Gabled roof over the wall rectangle (x0..x1, y0..y1). Ridge along `axis`. The underside touches the
    outer wall faces at z_eave and reaches z_eave + rise at the ridge."""
    if axis == 'y':
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
        with k.at((cx, cy, 0), rz=PI / 2):
            return roof_gable(k, -hy, hy, -hx, hx, z_eave, rise, oe, og, tv, sag, nu, nv, mat, col, ridge, barge,
                              'x', og2, **kw)
    if og2 is None:
        og2 = og
    thatch = (mat == 'M_thatch')
    if barge is None:
        barge = not thatch
    ym = (y0 + y1) / 2
    half = (y1 - y0) / 2
    slope = rise / half
    ze = z_eave - oe * slope
    zr = z_eave + rise
    xa, xb = x0 - og, x1 + og2
    kw2 = dict(tv=tv, nu=nu, nv=nv, mat=mat, col=col, sag=sag)
    kw2.update(kw)
    roof_plane(k, (xa, y0 - oe, ze), (xb, y0 - oe, ze), (xb, ym, zr), (xa, ym, zr), **kw2)
    roof_plane(k, (xb, y1 + oe, ze), (xa, y1 + oe, ze), (xa, ym, zr), (xb, ym, zr), **kw2)
    Ltot = xb - xa

    def zs(x):
        fu = (x - xa) / Ltot
        return zr + tv - sag * 4 * fu * (1 - fu)
    if ridge:
        ridge_roll(k, xa, xb, ym, zs, slope, thatch, col, nu,
                   ends=ridge if isinstance(ridge, (tuple, list)) else (True, True))
    if barge:
        bc = PAL['beam_d']
        bh = tv / math.sqrt(1 + slope * slope) + 0.1
        ends_ = barge if isinstance(barge, (tuple, list)) else (True, True)
        for x, sg in [e for e, on in zip(((xa, -1), (xb, 1)), ends_) if on]:
            for sy, ye in ((-1, y0 - oe), (1, y1 + oe)):
                p0 = V((x + sg * 0.015, ye - sy * 0.02, ze + tv * 0.42))
                p1 = V((x + sg * 0.015, ym, zr + tv * 0.42))
                k.beam(p0, p1, 0.05, bh, 'M_wood_planks', k.jit(bc), up=(0, -sy * slope, 1.0))
    return dict(ze=ze, zr=zr, slope=slope, zs=zs, xa=xa, xb=xb)


def ridge_roll(k, xa, xb, ym, zs, slope, thatch=False, col=None, nu=5, ends=(True, True)):
    """Ridge tiles / thatch ridge block along local X from xa to xb at y = ym; zs(x) = top of the roof."""
    rw = 0.62 if thatch else 0.17
    rh = 0.13 if thatch else 0.05
    rstep = 0.09 if thatch else 0.005
    mat = 'M_thatch' if thatch else 'M_roof_tiles'
    rc = PAL['thatch_new'] if thatch else PAL['tile_d']
    rc = col and mulc(col, 0.85) or rc
    n = nu * 2 if thatch else nu
    Ltot = xb - xa
    xs = [xa - 0.03 + (Ltot + 0.06) * i / n for i in range(n + 1)]
    R = k.M.to_3x3()
    for sgn in (-1, 1):
        rows = [[(x, ym + sgn * rw, zs(x) - rw * slope + rh * 0.6 + (k.r(-0.02, 0.02) if thatch else 0))
                 for x in xs], [(x, ym, zs(x) + rh) for x in xs]]
        k.grid(rows, mat, mulc(rc, 0.95), flip=(sgn > 0), smooth=True,
               uv=((R @ V((1, 0, 0))).normalized(), (R @ V((0, -sgn, slope))).normalized()), moss=0.25)
        rows2 = [[(x, ym + sgn * (rw - 0.02), zs(x) - rw * slope + rh * 0.6 - rstep) for x in xs], rows[0]]
        k.grid(rows2, mat, mulc(rc, 0.7), flip=(sgn > 0), smooth=False)
    for x, sg, on in ((xs[0], -1, ends[0]), (xs[-1], 1, ends[1])):
        if not on:
            continue
        a = (x, ym - rw, zs(x) - rw * slope + rh * 0.6 - rstep)
        b = (x, ym + rw, zs(x) - rw * slope + rh * 0.6 - rstep)
        c = (x, ym, zs(x) + rh)
        k.quad([a, c, b] if sg < 0 else [b, c, a], mat, mulc(rc, 0.8))


def roof_hip(k, x0, x1, y0, y1, z_eave, rise, ridge_len=0.0, oh=0.4, tv=0.14, mat='M_roof_tiles', col=None,
             nu=3, nv=2, sag=0.0, finial=False, **kw):
    """Hipped / pyramid roof over the wall rectangle. ridge along X with length ridge_len (0 = pyramid)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hy = (y1 - y0) / 2
    hx = (x1 - x0) / 2
    slope_y = rise / hy
    run_x = hx - ridge_len / 2
    slope_x = rise / max(run_x, 1e-6)
    # keep one eave height: use the gentler drop, extend overhangs accordingly
    drop = oh * min(slope_x, slope_y)
    ohy, ohx = drop / slope_y, drop / slope_x
    ze, zr = z_eave - drop, z_eave + rise
    A = (x0 - ohx, y0 - ohy, ze)
    B = (x1 + ohx, y0 - ohy, ze)
    C = (x1 + ohx, y1 + ohy, ze)
    D = (x0 - ohx, y1 + ohy, ze)
    R0 = (cx - ridge_len / 2, cy, zr)
    R1 = (cx + ridge_len / 2, cy, zr)
    kw2 = dict(tv=tv, mat=mat, col=col, nu=nu, nv=nv, sag=sag, edges=('eave',))
    kw2.update(kw)
    roof_plane(k, A, B, R1, R0, **kw2)
    roof_plane(k, B, C, R1, R1, **kw2)
    roof_plane(k, C, D, R0, R1, **kw2)
    roof_plane(k, D, A, R0, R0, **kw2)
    if finial:
        k.cyl((cx, cy, zr + tv - 0.05), (cx, cy, zr + tv + 0.45), 0.05, 0.02, n=5, mat='M_wood_planks',
              col=PAL['beam_d'])
    return dict(ze=ze, zr=zr)


def gable_tri(k, w, rise, mat='M_stone_wall', col=None, uv='box', apex_s=None):
    """Plain (stone / plank) gable triangle above w.z0."""
    col = col or PAL['stone']
    sm = w.L / 2 if apex_s is None else apex_s
    cuts = [0.0, sm * 0.5, sm, sm + (w.L - sm) * 0.5, w.L]

    def zr(s):
        return w.z0 + rise * (s / sm if s <= sm else (w.L - s) / (w.L - sm))
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        k.quad([w.P(a, w.z0), w.P(b, w.z0), w.P(b, zr(b)), w.P(a, zr(a))], mat, col, uv=uv)


# ----------------------------------------------------------------------------- small shared props
def barrel(k, c, r=0.3, h=0.8, n=10, col=None, lid=True, hoops=True, tilt=None):
    col = col or PAL['plank']
    cx, cy, cz = c
    prof = [(r * 0.84, 0.0), (r * 0.97, h * 0.25), (r, h * 0.5), (r * 0.97, h * 0.75), (r * 0.84, h)]
    k.lathe(c, prof, n=n, mat='M_wood_planks', col=k.jit(col), cap0=False)
    if lid:
        k.lathe(c, [(r * 0.84, h), (r * 0.80, h), (r * 0.80, h - 0.035), (0.0, h - 0.035)], n=n,
                mat='M_wood_planks', col=mulc(col, 0.8), smooth=False)
    if hoops:
        for fz in (0.12, 0.88):
            rr = r * (0.84 + 0.16 * math.sin(fz * PI)) + 0.006
            k.lathe(c, [(rr, h * fz - 0.03), (rr, h * fz + 0.03)], n=n, mat='M_metal_iron', col=PAL['iron'])


def crate(k, c, s=(0.6, 0.6, 0.5), col=None, rz=0.0, slats=True):
    col = col or PAL['plank']
    with k.at(c, rz=rz):
        sx, sy, sz = s
        k.box((-sx / 2, -sy / 2, 0), (sx / 2, sy / 2, sz), 'M_wood_planks', k.jit(col), skip=('-z',))
        if slats:
            t = 0.02
            bc = k.jit(mulc(col, 0.8))
            for sgn in (-1, 1):
                # corner battens on the two long faces (thin proud strips)
                for x in (-sx / 2 + 0.04, sx / 2 - 0.04):
                    k.beam((x, sgn * (sy / 2 + t / 2), 0), (x, sgn * (sy / 2 + t / 2), sz), 0.07, t, 'M_wood_planks',
                           bc, up=(0, sgn, 0), skip=('-u', 'c0'))


def sack(k, c, r=0.28, h=0.55, col=None, rz=0.0, lying=False, n=7):
    col = col or k.jit(PAL['sack'], 0.1)
    with k.at(c, rz=rz, rx=(PI / 2 * 0.92 if lying else 0.0)):
        z0 = 0.0 if not lying else -h * 0.0
        prof = [(r * 0.75, 0.0), (r, h * 0.22), (r * 0.95, h * 0.55), (r * 0.55, h * 0.82), (r * 0.22, h * 0.9),
                (r * 0.36, h)]
        k.lathe((0, 0, z0), prof, n=n, mat='M_cloth', col=col, cap0=True, cap1=True, sy=0.85)


def person(k, x, y, col=(0.75, 0.42, 0.25)):
    """1.8 m reference figure (preview only)."""
    with k.at((x, y, 0)):
        k.lathe((0, 0, 0), [(0.13, 0.0), (0.16, 0.5), (0.2, 0.95), (0.24, 1.4), (0.13, 1.5), (0.07, 1.54), (0.11, 1.6),
                            (0.115, 1.7), (0.07, 1.8), (0.0, 1.8)], n=8, mat='M_cloth', col=col, sy=0.6, cap0=True)


# ----------------------------------------------------------------------------- registry / build / preview
REG = {}


def asset(name, desc, budget, footprint=None, **opts):
    def deco(fn):
        REG[name] = dict(fn=fn, desc=desc, budget=budget, footprint=footprint, opts=opts)
        return fn
    return deco


def construct(name):
    """reset the scene and build one registered asset. Returns (kit, main object, export objects)."""
    reg = REG[name]
    reset_scene()
    k = Kit(name, seed=reg['opts'].get('seed', 7))
    k.bake_args = dict(reg['opts'].get('bake', {}))
    reg['fn'](k)
    main, objs = k.finish()
    return k, main, objs


def stage(k, objs, person_ok=True):
    """Preview-only extras (1.8 m figure + ground). Returns the list of objects to frame."""
    vis = [o for o in objs if o.type == 'MESH' and not o.name.startswith(('COL_', 'WALK_'))]
    mn, mx = _bounds(vis)
    show = list(vis)
    if k.person is not False and person_ok:
        pk = Kit('pv_person')
        pp = k.person if k.person else (mx.x + 0.45, mn.y - 0.3)
        with pk.at((0, 0, pp[2] if len(pp) > 2 else 0.0)):
            person(pk, pp[0], pp[1])
        pk.bake(ao_dist=0.5, dirt=0)
        show.append(pk.to_object())
    gk = Kit('pv_ground')
    R = max(mx.x - mn.x, mx.y - mn.y) * 3 + 6
    zg = min(-0.01, mn.z - 0.01) if REG[k.name]['opts'].get('ground_low') else -0.01
    gk.quad([(-R, -R, zg), (R, -R, zg), (R, R, zg), (-R, R, zg)], 'M_pv_ground', (0.10, 0.12, 0.07))
    gk.to_object()
    if REG[k.name]['opts'].get('show_col') or os.environ.get('ARCH_SHOWCOL'):
        for o in objs:
            if o.name.startswith(('COL_', 'WALK_')):
                o.hide_render = False
                o.display_type = 'TEXTURED'
                m = bpy.data.materials.get('M_pv_col') or make_mat('M_pv_col', (0.1, 0.8, 0.9) , 0.5)
                o.data.materials.clear()
                o.data.materials.append(m)
    return show


def build(name, preview=True, res=448, zoom=False):
    reg = REG[name]
    k, main, objs = construct(name)
    path = os.path.join(OUT, name + '.glb')
    info = export_glb(path, objs)
    tris = sum(p['tris'] for m in info['meshes'] if not (m['name'] or '').startswith(('COL_', 'WALK_'))
               for p in m['prims'])
    mn, mx = _bounds([o for o in objs if o.type == 'MESH' and not o.name.startswith(('COL_', 'WALK_'))])
    flag = 'OK' if tris <= reg['budget'] else 'OVER BUDGET'
    attrs = sorted(set(a for m in info['meshes'] for p in m['prims'] for a in p['attrs']))
    print('ASSET %s tris=%d/%d %s size=(%.2f, %.2f, %.2f) min=(%.2f, %.2f, %.2f) max=(%.2f, %.2f, %.2f) attrs=%s'
          % (name, tris, reg['budget'], flag, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, mn.x, mn.y, mn.z,
             mx.x, mx.y, mx.z, attrs))
    if preview:
        show = stage(k, objs)
        small = reg['budget'] <= 1500
        views = reg['opts'].get('views', ('front', 'left', 'back', 'persp') if small else
                                ('front', 'left', 'back', 'right', 'persp', 'persp_back'))
        render_sheet(os.path.join(PREVIEWS, 'arch_%s.png' % name), show, views=views,
                     res=reg['opts'].get('res', 384 if small else res), cols=reg['opts'].get('cols', 4 if small else 3))
        if zoom:
            render_sheet(os.path.join(PREVIEWS, 'arch_%s_zoom.png' % name), show,
                         views=zoom if isinstance(zoom, (list, tuple)) else ('persp', (0.45, 0.85, -0.16)), res=760,
                         cols=2)
    return info, tris


def family(names, path, views=('persp', 'persp_back'), res=320, per_row=3, export=False):
    """Contact sheet of several assets (each rebuilt from its script): len(views) tiles per asset."""
    imgs = []
    for name in names:
        k, main, objs = construct(name)
        if export:
            export_glb(os.path.join(OUT, name + '.glb'), objs)
        show = stage(k, objs)
        cam = setup_preview(res)
        bpy.context.view_layer.update()
        mn, mx = _bounds(show)
        for v in views:
            frame_camera(cam, mn, mx, v)
            imgs.append(render_to_array())
    save_png(path, montage(imgs, cols=per_row * len(views)))
    print('PREVIEW', path)


# ----------------------------------------------------------------------------- more wall types
def plank_wall(k, w, col=None, battens=0.5, posts=None, rails=(), openings=(), bw=0.14, frame=True, proud=0.04,
               bcol=None, horizontal=False):
    """Board-and-batten wall (barns, sheds, forge): plank surface + cover strips + optional sill/plate/posts."""
    col = col or PAL['plank']
    bcol = bcol or PAL['beam']
    wall_surface(k, w, mat='M_wood_planks', col=col, uv='swap' if horizontal else 'box', tint=0.16)
    z0, z1 = w.z0, w.z1

    def clear(s, t0, t1):
        for (a, b, c, d) in openings:
            if a - 0.03 < s < b + 0.03 and not (t1 <= c or t0 >= d):
                return False
        return True
    if battens and not horizontal:
        n = max(1, int(round(w.L / battens)))
        for i in range(1, n):
            s = w.L * i / n + k.r(-0.03, 0.03)
            if clear(s, z0, z1):
                wbeam(k, w, s, z0, s, z1, 0.055, 0.018, depth=0.03, col=k.jit(mulc(col, 0.85), 0.12))
    if frame:
        wbeam(k, w, 0, z0 + bw / 2, w.L, z0 + bw / 2, bw, proud, col=k.jit(bcol))
        wbeam(k, w, 0, z1 - bw / 2, w.L, z1 - bw / 2, bw, proud, col=k.jit(bcol))
    for s in (posts or ()):
        if clear(s, z0, z1):
            wbeam(k, w, s, z0, s, z1, bw, proud - 0.004, col=k.jit(bcol))
    for t in rails:
        wbeam(k, w, 0, t, w.L, t, bw * 0.85, proud - 0.008, col=k.jit(bcol))


def stone_wall(k, w, col=None, mat='M_stone_wall', quoins=0, tint=0.06, scuts=None, tcuts=None):
    """Plain masonry wall surface (grid for AO) + optional proud stones."""
    col = col or PAL['stone']
    wall_surface(k, w, scuts=scuts, tcuts=tcuts, mat=mat, col=col, tint=tint)
    for i in range(quoins):
        sl = k.r(0.3, 0.6)
        sh = k.r(0.18, 0.3)
        s = k.r(0.1, w.L - sl - 0.1)
        t = k.r(w.z0 + 0.1, w.z1 - sh - 0.2)
        p = w.P(s + sl / 2, t + sh / 2, 0.0)
        k.beam(p - w.d * sl / 2, p + w.d * sl / 2, sh, 0.07, mat, k.jit(mulc(col, 0.94), 0.06, 0.0), up=w.n,
               skip=('-u',), uv='box')


def post(k, x, y, z0, z1, w=0.18, col=None, taper=1.0, base=True):
    """Square timber post with an optional stone pad."""
    col = col or k.jit(PAL['beam'])
    k.box((x - w / 2, y - w / 2, z0), (x + w / 2, y + w / 2, z1), 'M_wood_planks', col, skip=('-z',), uv='along',
          taper=(taper, taper))
    if base:
        k.box((x - w / 2 - 0.07, y - w / 2 - 0.07, z0), (x + w / 2 + 0.07, y + w / 2 + 0.07, z0 + 0.14),
              'M_stone_wall', PAL['stone_d'], skip=('-z',), taper=(0.85, 0.85))


def knee(k, p, d_h, size=0.6, w=0.11, col=None):
    """Diagonal knee brace from a post (point p on the post at the TOP corner) going down the post and
    out along the horizontal direction d_h."""
    d_h = V(d_h).normalized()
    p = V(p)
    a = p + V((0, 0, -size))
    b = p + d_h * size
    k.beam(a, b, w, w, 'M_wood_planks', col or k.jit(PAL['beam']), up=d_h.cross(V((0, 0, 1))))
