"""Procedural mesh-building library shared by the gear_*.py and mon_*.py scripts of VALOMBRE.

MB = a small mesh builder: parts are appended as (positions, per-vertex linear colors, optional skin
weights) + faces carrying a material name, per-corner UVs and a smoothing threshold. `MB.build()` turns
the lot into ONE Blender mesh object with material slots, a `Col` color attribute (-> COLOR_0), a UV map,
sharp edges and (optionally) vertex groups.

Everything is authored directly in final coordinates (meters, Blender Z up).
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
import blcommon as _blc

mesh_bounds = _blc._bounds
XA, YA, ZA = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


# ----------------------------------------------------------------------------- colors / noise
def C(h):
    """'#rrggbb' (sRGB, picked by eye) -> linear tuple."""
    return tuple(lin(h))


def mix(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def mul(a, k):
    return (min(1.0, a[0] * k), min(1.0, a[1] * k), min(1.0, a[2] * k))


def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def smooth01(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def sstep(a, b, x):
    if a == b:
        return 1.0 if x >= a else 0.0
    return smooth01((x - a) / (b - a))


def _h(ix, iy, iz, seed):
    n = (ix * 374761393 + iy * 668265263 + iz * 1274126177 + seed * 974711 + 0x9e3779b9) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1103515245) & 0xffffffff
    n = n ^ (n >> 16)
    return (n & 0xffff) / 65535.0


def vnoise(p, scale=1.0, seed=0):
    """Smooth value noise 0..1."""
    x, y, z = p[0] * scale, p[1] * scale, p[2] * scale
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)

    def L(a, b, t):
        return a + (b - a) * t

    c = [[[_h(ix + i, iy + j, iz + k, seed) for k in (0, 1)] for j in (0, 1)] for i in (0, 1)]
    return L(L(L(c[0][0][0], c[1][0][0], fx), L(c[0][1][0], c[1][1][0], fx), fy),
             L(L(c[0][0][1], c[1][0][1], fx), L(c[0][1][1], c[1][1][1], fx), fy), fz)


def fbm(p, scale=1.0, seed=0, octaves=3):
    s, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s += a * vnoise(p, scale * (2 ** o), seed + o * 17)
        tot += a
        a *= 0.5
    return s / tot


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def tr(x, y=None, z=None):
    if y is None:
        return Matrix.Translation(Vector(x))
    return Matrix.Translation(Vector((x, y, z)))


def sc(x, y=None, z=None):
    if y is None:
        y = z = x
    return Matrix.Diagonal((x, y, z, 1.0))


# ----------------------------------------------------------------------------- mesh builder
class MB:
    def __init__(self):
        self.P, self.C, self.W = [], [], []
        self.F, self.FM, self.FUV, self.FS, self.FUS, self.FK = [], [], [], [], [], []
        self.keep = False          # True: faces added keep their winding (no normal recalculation)
        self.bone = None           # current skin weights for new verts: None | 'bone' | {bone: w}
        self.fn_w = None           # optional function(Vector) -> {bone: w} (overrides self.bone)

    # -- low level
    def add(self, p, c):
        p = Vector(p)
        self.P.append(p)
        self.C.append((c[0], c[1], c[2]))
        self.W.append(self.fn_w(p) if self.fn_w else self.bone)
        return len(self.P) - 1

    def face(self, idx, mat, uv=None, sharp=35.0, uvs=2.0):
        idx = tuple(idx)
        if len(set(idx)) < 3:
            return
        if len(set(idx)) != len(idx):       # drop repeated indices
            seen, keep, kuv = set(), [], []
            for k, i in enumerate(idx):
                if i not in seen:
                    seen.add(i)
                    keep.append(i)
                    if uv:
                        kuv.append(uv[k])
            idx, uv = tuple(keep), (tuple(kuv) if uv else None)
        self.F.append(idx)
        self.FM.append(mat)
        self.FUV.append(uv)
        self.FS.append(sharp)
        self.FUS.append(uvs)
        self.FK.append(self.keep)

    def mark(self):
        return (len(self.P), len(self.F))

    def xform(self, mark, M):
        for i in range(mark[0], len(self.P)):
            self.P[i] = M @ self.P[i]
        if self.fn_w:
            for i in range(mark[0], len(self.P)):
                self.W[i] = self.fn_w(self.P[i])

    def recolor(self, mark, fn):
        """fn(position, color) -> color, on every vertex added since `mark`."""
        for i in range(mark[0], len(self.P)):
            self.C[i] = tuple(fn(self.P[i], self.C[i]))[:3]

    def displace(self, mark, fn):
        """fn(position) -> new position."""
        for i in range(mark[0], len(self.P)):
            self.P[i] = Vector(fn(self.P[i]))

    def set_weights(self, mark, w):
        for i in range(mark[0], len(self.P)):
            self.W[i] = w(self.P[i]) if callable(w) else w

    def set_mat(self, mark, mat):
        for i in range(mark[1], len(self.F)):
            self.FM[i] = mat

    def tris(self, mark=None):
        f0 = mark[1] if mark else 0
        return sum(len(f) - 2 for f in self.F[f0:])

    @staticmethod
    def _col(cols, p, i, j):
        if callable(cols):
            return cols(p, i, j)
        if isinstance(cols, list):
            c = cols[i]
            if isinstance(c, list):
                return c[j]
            return c
        return cols

    # -- primitives
    def loft(self, rings, cols, mat, closed=True, cap0=None, cap1=None, sharp=35.0, uv=(2.0, 0.0, 0.0),
             capcol0=None, capcol1=None):
        """rings: list of rings (same vertex count). cols: color tuple | list per ring (color or list per
        point) | fn(p, ring_i, j). cap0 / cap1: None | 'fan' | 'ngon' | Vector (apex).
        uv = (scale per meter, u offset, v offset)."""
        n = len(rings[0])
        idx = []
        for i, ring in enumerate(rings):
            idx.append([self.add(p, self._col(cols, Vector(p), i, j)) for j, p in enumerate(ring)])
        us, u0, v0 = uv
        U = []
        for ring in rings:
            acc, row = 0.0, [0.0]
            for j in range(n):
                a, b = Vector(ring[j]), Vector(ring[(j + 1) % n])
                acc += (b - a).length
                row.append(acc)
            U.append(row)
        cen = [sum((Vector(p) for p in ring), Vector()) / n for ring in rings]
        Vv, acc = [0.0], 0.0
        for i in range(1, len(rings)):
            d = (cen[i] - cen[i - 1]).length
            if d < 1e-6:
                d = max((Vector(rings[i][0]) - Vector(rings[i - 1][0])).length, 1e-4)
            acc += d
            Vv.append(acc)
        m = n if closed else n - 1
        for i in range(len(rings) - 1):
            for j in range(m):
                j2 = (j + 1) % n
                uvq = ((u0 + U[i][j] * us, v0 + Vv[i] * us), (u0 + U[i][j + 1] * us, v0 + Vv[i] * us),
                       (u0 + U[i + 1][j + 1] * us, v0 + Vv[i + 1] * us), (u0 + U[i + 1][j] * us, v0 + Vv[i + 1] * us))
                self.face((idx[i][j], idx[i][j2], idx[i + 1][j2], idx[i + 1][j]), mat, uvq, sharp)
        for cap, ring, ri, vv, ccol, back in ((cap0, idx[0], 0, Vv[0], capcol0, True),
                                              (cap1, idx[-1], len(rings) - 1, Vv[-1], capcol1, False)):
            if cap is None:
                continue
            if isinstance(cap, str) and cap == 'ngon':
                self.face(ring[::-1] if back else ring, mat, None, sharp, us)
                continue
            if isinstance(cap, str):
                apex = cen[ri]
            else:
                apex = Vector(cap)
            if ccol is None:
                cs = [self.C[k] for k in ring]
                ccol = (sum(c[0] for c in cs) / n, sum(c[1] for c in cs) / n, sum(c[2] for c in cs) / n)
            a = self.add(apex, ccol)
            d = (apex - cen[ri]).length
            rad = sum((Vector(self.P[k]) - cen[ri]).length for k in ring) / n
            va = v0 + (vv + (-1 if back else 1) * math.hypot(d, rad)) * us
            for j in range(m):
                j2 = (j + 1) % n
                uvt = ((u0 + U[ri][j] * us, v0 + vv * us), (u0 + U[ri][j + 1] * us, v0 + vv * us),
                       (u0 + (U[ri][j] + U[ri][j + 1]) * 0.5 * us, va))
                if back:
                    self.face((ring[j2], ring[j], a), mat, (uvt[1], uvt[0], uvt[2]), sharp)
                else:
                    self.face((ring[j], ring[j2], a), mat, uvt, sharp)
        return idx

    def lathe(self, prof, segs, mat, M=None, cols=None, sx=1.0, sy=1.0, phase=0.0, sharp=35.0,
              uv=(2.0, 0.0, 0.0), cap0=None, cap1=None):
        """Revolve a profile [(r, z[, color])...] around Z. A radius of 0 at either end makes an apex."""
        prof = list(prof)
        M = M or Matrix.Identity(4)
        tip0 = tip1 = None
        c0 = c1 = None
        if prof[0][0] <= 1e-9:
            tip0 = M @ Vector((0, 0, prof[0][1]))
            c0 = prof[0][2] if len(prof[0]) > 2 else None
            prof = prof[1:]
        if prof[-1][0] <= 1e-9:
            tip1 = M @ Vector((0, 0, prof[-1][1]))
            c1 = prof[-1][2] if len(prof[-1]) > 2 else None
            prof = prof[:-1]
        rings, rc = [], []
        for pr in prof:
            r, z = pr[0], pr[1]
            rings.append([M @ Vector((r * sx * math.cos(phase + 2 * math.pi * j / segs),
                                      r * sy * math.sin(phase + 2 * math.pi * j / segs), z)) for j in range(segs)])
            rc.append(pr[2] if len(pr) > 2 else None)
        if cols is None:
            cols = rc
        return self.loft(rings, cols, mat, True, tip0 if tip0 is not None else cap0,
                         tip1 if tip1 is not None else cap1, sharp, uv, c0, c1)

    def tube(self, path, radii, segs, mat, cols, up=(0, 1, 0), cap0='fan', cap1='fan', sharp=35.0,
             uv=(2.0, 0.0, 0.0), phase=0.0, closed_path=False, miter=True):
        """Sweep an ellipse along a path. radii: r | [r...] | [(ra, rb)...] (ra along `up`, rb across)."""
        path = [Vector(p) for p in path]
        n = len(path)
        tang = []
        for i in range(n):
            if closed_path:
                t = path[(i + 1) % n] - path[(i - 1) % n]
            else:
                t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
            tang.append(t.normalized())
        nrm_ = Vector(up) - tang[0] * Vector(up).dot(tang[0])
        if nrm_.length < 1e-5:
            nrm_ = tang[0].orthogonal()
        nrm_.normalize()
        rings = []
        for i in range(n):
            if i > 0:
                q = tang[i - 1].rotation_difference(tang[i])
                nrm_ = (q @ nrm_)
                nrm_ = (nrm_ - tang[i] * nrm_.dot(tang[i])).normalized()
            b = tang[i].cross(nrm_)
            r = radii[i] if isinstance(radii, (list, tuple)) else radii
            ra, rb = (r if isinstance(r, (list, tuple)) else (r, r))
            offs = [nrm_ * (ra * math.cos(phase + 2 * math.pi * j / segs))
                    + b * (rb * math.sin(phase + 2 * math.pi * j / segs)) for j in range(segs)]
            if miter and (closed_path or 0 < i < n - 1):
                d0 = (path[i] - path[i - 1]).normalized()
                d1 = (path[(i + 1) % n] - path[i]).normalized()
                m = d1 - d0
                if m.length > 1e-4:
                    m.normalize()
                    ch_ = math.sqrt(max(0.0, (1 + d0.dot(d1)) * 0.5))
                    k = 1.0 / max(ch_, 0.4) - 1.0
                    offs = [o + m * (o.dot(m) * k) for o in offs]
            rings.append([path[i] + o for o in offs])
        if closed_path:
            rings.append([p.copy() for p in rings[0]])
            cap0 = cap1 = None
            if isinstance(cols, list):
                cols = cols + [cols[0]]
        return self.loft(rings, cols, mat, True, cap0, cap1, sharp, uv)

    def cbox(self, size, mat, cols, M=None, ch=0.0, sharp=35.0, uv=(2.0, 0.0, 0.0), taper=1.0):
        """Chamfered box centered on the origin (then transformed by M). taper scales the +Z end."""
        M = M or Matrix.Identity(4)
        hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5

        def outline(ax, ay, c):
            if c <= 1e-6:
                return [(ax, ay), (-ax, ay), (-ax, -ay), (ax, -ay)]
            return [(ax, ay - c), (ax - c, ay), (-ax + c, ay), (-ax, ay - c), (-ax, -ay + c), (-ax + c, -ay),
                    (ax - c, -ay), (ax, -ay + c)]

        rings = []
        lv = [(-hz, ch, 1.0), (-hz + ch, 0.0, 1.0), (hz - ch, 0.0, taper), (hz, ch, taper)] if ch > 1e-6 else \
            [(-hz, 0.0, 1.0), (hz, 0.0, taper)]
        for z, inset, k in lv:
            rings.append([M @ Vector((x, y, z)) for x, y in outline((hx - inset) * k, (hy - inset) * k, ch * k)])
        return self.loft(rings, cols, mat, True, 'ngon', 'ngon', sharp, uv)

    def ngon(self, pts, cols, mat, sharp=35.0, uvs=2.0, double=False):
        idx = [self.add(p, self._col(cols, Vector(p), 0, j)) for j, p in enumerate(pts)]
        self.face(idx, mat, None, sharp, uvs)
        if double:
            idx2 = [self.add(p, self._col(cols, Vector(p), 1, j)) for j, p in enumerate(pts)]
            self.face(idx2[::-1], mat, None, sharp, uvs)
        return idx

    def hull(self, pts, cols, mat, sharp=28.0, uvs=2.0):
        """Convex hull of a point cloud (angular rocks, crystals). cols: color | fn(p, 0, i)."""
        bm = bmesh.new()
        vs = [bm.verts.new(Vector(p)) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
        drop = list({e for e in list(res.get('geom_interior', [])) + list(res.get('geom_unused', []))
                     if isinstance(e, bmesh.types.BMVert)})
        if drop:
            bmesh.ops.delete(bm, geom=drop, context='VERTS')
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.verts.ensure_lookup_table()
        remap = {}
        for v in bm.verts:
            if not v.link_faces:
                continue
            remap[v.index] = self.add(v.co, self._col(cols, v.co.copy(), 0, v.index))
        m0 = len(self.F)
        for f in bm.faces:
            self.face([remap[v.index] for v in f.verts], mat, None, sharp, uvs)
        bm.free()
        return m0

    def sphere(self, c, r, mat, cols, segs=8, rings=5, M=None, sharp=60.0, uv=(2.0, 0.0, 0.0)):
        """UV sphere / ellipsoid (r = radius or (rx, ry, rz))."""
        rx, ry, rz = (r if isinstance(r, (list, tuple)) else (r, r, r))
        prof = []
        for i in range(rings + 1):
            a = math.pi * i / rings
            prof.append((max(0.0, math.sin(a)), -math.cos(a)))
        prof[0] = (0.0, -1.0)
        prof[-1] = (0.0, 1.0)
        T = tr(c) @ sc(rx, ry, rz)
        if M is not None:
            T = M @ T
        return self.lathe(prof, segs, mat, T, cols, sharp=sharp, uv=uv)

    def spike(self, base, tip, r, mat, cols, segs=4, sharp=35.0, phase=0.0, tipcol=None, up=(0, 0, 1)):
        base, tip = Vector(base), Vector(tip)
        ax = (tip - base).normalized()
        u = Vector(up) - ax * Vector(up).dot(ax)
        if u.length < 1e-4:
            u = ax.orthogonal()
        u.normalize()
        v = ax.cross(u)
        ring = [base + u * (r * math.cos(phase + 2 * math.pi * j / segs)) + v * (r * math.sin(phase + 2 * math.pi * j / segs))
                for j in range(segs)]
        return self.loft([ring], cols, mat, True, None, tip, sharp, capcol1=tipcol)

    # -- finish
    def build(self, name, mats=None, recalc=True, weld=0.0):
        """-> Blender mesh object. mats: {material name: bpy material} (created with make_mat when missing)."""
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.P], [], self.F)
        me.update()
        order = []
        for m in self.FM:
            if m not in order:
                order.append(m)
        for m in order:
            mat = (mats or {}).get(m) or bpy.data.materials.get(m) or make_mat(m, (1, 1, 1), use_vertex_color=True)
            me.materials.append(mat)
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        uvl = me.uv_layers.new(name='UVMap')
        for pi, poly in enumerate(me.polygons):
            poly.material_index = order.index(self.FM[pi])
            poly.use_smooth = True
            fuv = self.FUV[pi]
            if fuv is None:
                n = poly.normal
                ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
                s = self.FUS[pi]
            for k, li in enumerate(poly.loop_indices):
                vi = me.loops[li].vertex_index
                c = self.C[vi]
                ca.data[li].color = (c[0], c[1], c[2], 1.0)
                if fuv is not None:
                    uvl.data[li].uv = fuv[k]
                else:
                    p = self.P[vi]
                    if az >= ax and az >= ay:
                        uvl.data[li].uv = (p.x * s, p.y * s)
                    elif ax >= ay:
                        uvl.data[li].uv = (p.y * s, p.z * s)
                    else:
                        uvl.data[li].uv = (p.x * s, p.z * s)
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = 0
        ob = bpy.data.objects.new(name, me)
        link(ob)
        # normals + sharp edges
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if not self.FK[f.index]])
        bm.faces.ensure_lookup_table()
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) == 2:
                thr = min(self.FS[lf[0].index], self.FS[lf[1].index])
                try:
                    ang = math.degrees(e.calc_face_angle())
                except Exception:
                    ang = 0.0
                e.smooth = ang < thr
            else:
                e.smooth = True
        bm.to_mesh(me)
        bm.free()
        me.update()
        # skin weights
        if any(w is not None for w in self.W):
            groups = {}
            for i, w in enumerate(self.W):
                if w is None:
                    continue
                if isinstance(w, str):
                    w = {w: 1.0}
                tot = sum(w.values()) or 1.0
                for b, x in w.items():
                    if x > 1e-4:
                        groups.setdefault(b, []).append((i, x / tot))
            for b, lst in groups.items():
                vg = ob.vertex_groups.new(name=b)
                for i, x in lst:
                    vg.add([i], x, 'REPLACE')
        return ob


def skin_to(ob, arm):
    mod = ob.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    return ob


# ----------------------------------------------------------------------------- preview materials
PREVIEW_MATS = {
    # name: (rough, metal, emissive strength)
    'M_metal_steel': (0.34, 0.75, 0), 'M_metal_iron': (0.6, 0.55, 0), 'M_metal_gold': (0.3, 0.8, 0),
    'M_metal_bronze': (0.45, 0.7, 0), 'M_leather': (0.7, 0, 0), 'M_wood_planks': (0.8, 0, 0),
    'M_bone': (0.55, 0, 0), 'M_rope': (0.9, 0, 0), 'M_cloth': (0.9, 0, 0), 'M_fur': (0.95, 0, 0),
    'M_hide': (0.8, 0, 0), 'M_rock': (0.9, 0, 0), 'M_crystal': (0.15, 0, 3.0), 'M_ice': (0.12, 0, 0.6),
    'M_ember': (0.6, 0, 2.0), 'M_eye_glow': (0.4, 0, 4.0),
}


def preview_mat(name):
    """Preview-only material named after the engine material (the engine replaces it by name).
    White base color multiplied by the vertex color, emissive for the glowing ones."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    rough, metal, emi = PREVIEW_MATS.get(name, (0.7, 0, 0))
    m = make_mat(name, (1, 1, 1), rough=rough, metal=metal, use_vertex_color=True)
    if emi > 0:
        nt = m.node_tree
        bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
        vc = [n for n in nt.nodes if n.type == 'VERTEX_COLOR'][0]
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = emi
    return m


def all_preview_mats():
    return {n: preview_mat(n) for n in PREVIEW_MATS}


# ----------------------------------------------------------------------------- contact sheets
def render_items(path, items, views=('front', 'left'), res=(160, 448), cols=12, margin=1.06, also=()):
    """One group of tiles per item (item = object or list of objects); every other mesh is hidden while an
    item is rendered. `also` = objects always visible (not used for framing)."""
    items = [it if isinstance(it, (list, tuple)) else [it] for it in items]
    allobjs = [o for it in items for o in it]
    cam = setup_preview(res)
    prev = {o: o.hide_render for o in bpy.data.objects}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    imgs = []
    for it in items:
        for o in meshes:
            o.hide_render = (o not in it) and (o not in also)
        bpy.context.view_layer.update()
        mn, mx = mesh_bounds(it)
        for v in views:
            frame_camera(cam, mn, mx, v, margin)
            imgs.append(render_to_array())
    for o, h in prev.items():
        try:
            o.hide_render = h
        except Exception:
            pass
    save_png(path, montage(imgs, cols=cols))
    print('PREVIEW', path)
    return path


def bounds_of(ob):
    mn, mx = mesh_bounds([ob])
    return [round(mn.x, 4), round(mn.y, 4), round(mn.z, 4)], [round(mx.x, 4), round(mx.y, 4), round(mx.z, 4)]
