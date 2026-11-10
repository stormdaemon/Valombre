"""VALOMBRE nature pack - rocks: rock_a..rock_e (LOD0 + LOD1), cliff_a, cliff_b, pebbles (LOD0 only).

  blender -b --factory-startup -P tools/blender/nat_rocks.py [-- name ...]

Pipeline: icosphere -> lumpy noise -> fracture planes (flat facets) -> weathering smooth -> detail displacement
-> (cliffs: union of several blocks by voxel remesh) -> collapse decimation -> sharp edges by angle
-> box_uv(4 m) -> ray-cast AO baked into COLOR_0.R (G = B = 0).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nat_common import *

TAU = 2 * math.pi


def vnoise(V, freq, off):
    return np.array([mnoise.noise(Vector((v[0] * freq + off[0], v[1] * freq + off[1], v[2] * freq + off[2])))
                     for v in V])


def fnoise(V, freq, off, octaves=4):
    out = np.zeros(len(V))
    a, f = 1.0, freq
    for o in range(octaves):
        out += a * vnoise(V, f, off + o * 17.3)
        a *= 0.5
        f *= 2.05
    return out


def rock_points(seed, subdiv=4, scale=(1, 1, 1), lumps=0.2, planes=10, plane_range=(0.55, 0.9), smooth=2,
                smooth_fac=0.5, detail=0.03, detail_freq=2.5, strata=0.0, strata_freq=7.0, bias='free',
                lump_freq=1.2):
    """Returns a bmesh of one weathered, fractured rock (unit-ish size times `scale`), centred on the origin."""
    rng = np.random.RandomState(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts])
    off = rng.uniform(0, 100, 3)
    V *= (1 + lumps * vnoise(V, lump_freq, off))[:, None]
    V *= np.array(scale, float)
    ext = np.abs(V).max(axis=0)
    for k in range(planes):
        n = rng.normal(size=3)
        if bias == 'vertical':            # mostly vertical faces (columns, slab sides)
            n[2] *= 0.25
        elif bias == 'slab':              # sides + flat top
            n[2] *= 0.2
            if k < 2:
                n = np.array([rng.normal() * 0.08, rng.normal() * 0.08, 1.0 if k == 0 else -1.0])
        n = unit(n / np.maximum(ext, 1e-6) * ext.max()) if bias != 'free' else unit(n)
        h = V @ n
        d = h.max() * rng.uniform(*plane_range)
        m = h > d
        V[m] -= np.outer(h[m] - d, n)
    for v, p in zip(bm.verts, V):
        v.co = p
    for i in range(smooth):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=smooth_fac, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    V = np.array([v.co[:] for v in bm.verts])
    Nn = np.array([v.normal[:] for v in bm.verts])
    size = float(np.abs(V).max())
    disp = detail * size * fnoise(V / size, detail_freq, off + 31.0)
    if strata > 0:
        zz = V[:, 2] / size * strata_freq + 0.6 * vnoise(V / size, 1.5, off + 5.0)
        ridges = np.abs((zz % 1.0) - 0.5) * 2.0          # 0 at layer boundary, 1 mid layer
        disp += strata * size * (np.clip(ridges * 3.0, 0, 1) - 0.7) * np.clip(1.0 - np.abs(Nn[:, 2]) * 1.4, 0, 1)
    V = V + Nn * disp[:, None]
    for v, p in zip(bm.verts, V):
        v.co = p
    return bm


def block_points(seed, w, d, h, taper=0.75, cuts=7, planes=12, plane_range=(0.74, 0.97), lumps=0.05, smooth=1,
                 roof=0.5):
    """Blocky crag element: a tapered, sheared box with chamfering fracture planes (flat faces, hard edges)."""
    rng = np.random.RandomState(seed)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts])
    z01 = V[:, 2] + 0.5
    k = 1.0 - (1.0 - taper) * np.power(z01, 1.4)
    V[:, 0] *= w * k
    V[:, 1] *= d * k
    V[:, 2] *= h
    V[:, 0] += z01 * rng.uniform(-0.10, 0.10) * w
    V[:, 1] += z01 * rng.uniform(-0.10, 0.10) * d
    ext = np.array([w, d, h]) / 2
    for i in range(planes):
        n = rng.normal(size=3)
        n[2] = abs(n[2]) * roof if i % 3 == 0 else n[2] * 0.12
        n = unit(n / ext * ext.max())
        hh = V @ n
        dd = hh.max() * rng.uniform(*plane_range)
        m = hh > dd
        V[m] -= np.outer(hh[m] - dd, n)
    for v, p in zip(bm.verts, V):
        v.co = p
    for i in range(smooth):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.3, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    V = np.array([v.co[:] for v in bm.verts])
    Nn = np.array([v.normal[:] for v in bm.verts])
    size = float(max(w, d, h)) / 2
    off = rng.uniform(0, 100, 3)
    V = V + Nn * (lumps * size * fnoise(V / size, 1.6, off, octaves=3))[:, None]
    for v, p in zip(bm.verts, V):
        v.co = p
    return bm


def bm_xform(bm, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
    M = Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal(Vector((*scale, 1.0)))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def bm_join(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new('tmp')
        b.to_mesh(me)
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
        b.free()
    return out


def ground_it(bm, sink_frac=0.12, flat=True):
    """Flatten what goes too deep and put the ground plane at z = 0 with `sink_frac` of the height buried."""
    zs = np.array([v.co.z for v in bm.verts])
    z0, z1 = zs.min(), zs.max()
    cut = z0 + (z1 - z0) * sink_frac * 0.5
    for v in bm.verts:
        if flat and v.co.z < cut:
            v.co.z = cut
        v.co.z -= z0 + (z1 - z0) * sink_frac
    xs = np.array([v.co.x for v in bm.verts])
    ys = np.array([v.co.y for v in bm.verts])
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    for v in bm.verts:
        v.co.x -= cx
        v.co.y -= cy


def finish_rock(bm, name, target, sharp_deg=40.0, ao_dist=None, remesh=None, post_smooth=0, ao_lo=0.3):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if remesh:
        m = ob.modifiers.new('rm', 'REMESH')
        m.mode = 'VOXEL'
        m.voxel_size = remesh
        m.use_smooth_shade = True
        apply_modifiers(ob)
    if post_smooth:
        b2 = bmesh.new()
        b2.from_mesh(ob.data)
        for i in range(post_smooth):
            bmesh.ops.smooth_vert(b2, verts=b2.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        b2.to_mesh(ob.data)
        b2.free()
    n0 = tri_count(ob)
    ratio = min(1.0, target / max(n0, 1))
    for attempt in range(6):
        m = ob.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = ratio
        m.use_collapse_triangulate = True
        apply_modifiers(ob)
        n = tri_count(ob)
        if n <= target:
            break
        ratio = (target / n) * 0.97
    # clean + sharp edges by angle
    b2 = bmesh.new()
    b2.from_mesh(ob.data)
    bmesh.ops.remove_doubles(b2, verts=b2.verts, dist=1e-4)
    b2.normal_update()
    thr = math.radians(sharp_deg)
    for e in b2.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > thr)
    for f in b2.faces:
        f.smooth = True
    b2.to_mesh(ob.data)
    b2.free()
    ob.data.update()
    assign_mat(ob, nat_mat('M_rock'))
    box_uv(ob, 4.0)
    ext = max(ob.dimensions)
    ao = bake_ao_raycast(ob, dist=ao_dist or ext * 0.55, rays=56, lo=ao_lo, ground_grad=min(0.5, ext * 0.12))
    set_colors_per_vertex(ob, np.stack([ao, np.zeros_like(ao), np.zeros_like(ao)], axis=1))
    return ob


def copy_bm(bm):
    return bm.copy()


# ----------------------------------------------------------------------------- boulders
def rock_a():      # rounded, weathered boulder ~1.4 m
    bm = rock_points(11, scale=(0.84, 0.72, 0.62), lumps=0.24, planes=10, plane_range=(0.62, 0.9), smooth=3,
                     smooth_fac=0.55, detail=0.04)
    bm_xform(bm, rot=(0.1, 0.05, 0.4))
    ground_it(bm, 0.13)
    return bm, dict(description='rounded weathered boulder', sink=0.13)


def rock_b():      # angular chunk ~1.9 m, tall-ish
    bm = rock_points(23, scale=(1.30, 1.15, 1.55), lumps=0.16, planes=16, plane_range=(0.5, 0.86), smooth=1,
                     smooth_fac=0.35, detail=0.03)
    bm_xform(bm, rot=(0.12, -0.2, 1.1))
    ground_it(bm, 0.1)
    return bm, dict(description='angular fractured boulder', sink=0.1)


def rock_c():      # flat slab ~2.5 m wide
    bm = rock_points(37, scale=(1.60, 1.22, 0.38), lumps=0.10, planes=12, plane_range=(0.62, 0.9), smooth=1,
                     smooth_fac=0.4, detail=0.018, strata=0.03, strata_freq=3.0, bias='slab')
    bm_xform(bm, rot=(0.07, -0.05, 0.3))
    ground_it(bm, 0.16)
    return bm, dict(description='flat layered slab', sink=0.16)


def rock_d():      # split boulder ~2.2 m: two halves with a crack
    base = rock_points(41, scale=(1.05, 0.9, 0.8), lumps=0.18, planes=10, plane_range=(0.6, 0.9), smooth=2,
                       smooth_fac=0.5, detail=0.028)
    rng = np.random.RandomState(5)
    n = unit((1.0, 0.25, 0.12))
    halves = []
    for sgn in (1.0, -1.0):
        b = base.copy()
        V = np.array([v.co[:] for v in b.verts])
        rough = 0.035 * vnoise(V, 2.2, (3.0, 7.0, 11.0 + sgn))
        h = (V @ n) * sgn
        lim = -0.05 + rough
        m = h < lim
        V[m] += np.outer((lim - h)[m], n * sgn)
        for v, p in zip(b.verts, V):
            v.co = p
        halves.append(b)
    base.free()
    bm_xform(halves[1], rot=(0.0, 0.16, -0.08), loc=(-0.10, 0.03, -0.08))
    bm_xform(halves[0], rot=(0.0, -0.05, 0.03), loc=(0.07, 0.0, 0.0))
    bm = bm_join(halves)
    ground_it(bm, 0.12)
    return bm, dict(description='split boulder: two halves with an open crack', sink=0.12)


def rock_e():      # small stone ~0.6 m
    bm = rock_points(59, subdiv=3, scale=(0.40, 0.32, 0.27), lumps=0.2, planes=11, plane_range=(0.55, 0.88),
                     smooth=1, smooth_fac=0.5, detail=0.04)
    bm_xform(bm, rot=(0.2, 0.1, 0.9))
    ground_it(bm, 0.15)
    return bm, dict(description='small lumpy stone', sink=0.15)


# ----------------------------------------------------------------------------- cliffs
def crag(seed, blocks, voxel):
    rng = np.random.RandomState(seed)
    parts = []
    for i, (x, y, w, d, h, lean) in enumerate(blocks):
        b = block_points(seed * 7 + i, w, d, h, taper=rng.uniform(0.5, 0.82), planes=18, plane_range=(0.64, 0.96),
                         roof=0.75, lumps=0.07)
        bm_xform(b, rot=(lean[0] * 1.5, lean[1] * 1.5, rng.uniform(-0.9, 0.9)), loc=(x, y, h / 2 - 1.0))
        parts.append(b)
    return bm_join(parts)


def cliff_a():     # wide crag wall, ~11 x 5 x 8.5 m
    blocks = [(-3.5, 0.3, 4.4, 3.8, 6.6, (0.04, 0.05)), (-0.9, 0.0, 4.6, 4.4, 9.6, (-0.03, -0.03)),
              (1.9, 0.4, 4.2, 4.0, 8.0, (0.03, 0.06)), (4.0, 0.0, 3.6, 3.4, 5.4, (0.05, -0.06)),
              (-2.3, -1.7, 3.4, 2.6, 3.8, (0.08, 0.0)), (1.8, -1.8, 3.8, 2.6, 3.4, (-0.06, 0.04)),
              (0.3, 1.8, 5.6, 2.6, 5.4, (0.0, 0.0)), (-4.6, -0.8, 2.6, 2.6, 3.2, (0.0, 0.08))]
    bm = crag(3, blocks, 0.16)
    return bm, dict(description='wide crag wall of stacked fractured blocks, tallest in the middle', sink=1.0)


def cliff_b():     # tall pinnacle outcrop, ~6.5 x 5.5 x 10 m
    blocks = [(0.0, 0.0, 3.6, 3.4, 11.4, (0.04, -0.05)), (-1.4, 0.6, 3.4, 3.2, 8.2, (-0.06, 0.04)),
              (1.3, -0.6, 3.2, 3.2, 6.6, (0.08, 0.06)), (0.4, 1.6, 3.2, 2.8, 5.0, (0.0, 0.08)),
              (-0.9, -1.5, 3.2, 2.6, 4.2, (0.08, -0.04)), (1.9, 1.0, 2.6, 2.4, 3.2, (0.0, 0.0))]
    bm = crag(5, blocks, 0.15)
    return bm, dict(description='tall rock pinnacle with buttresses', sink=1.0)


def build_pebbles(name):
    rng = np.random.RandomState(7)
    mb = MB()
    stones = [(0.0, 0.05, 0.19), (0.42, -0.2, 0.13), (-0.38, 0.28, 0.11), (-0.3, -0.36, 0.15), (0.3, 0.42, 0.09),
              (0.62, 0.2, 0.07)]
    ang = np.linspace(0, TAU, 6)
    for (x, y, r) in stones:
        yaw = rng.uniform(0, TAU)
        ex = rng.uniform(0.7, 1.0)
        h = r * rng.uniform(0.5, 0.8)
        j1 = 1 + rng.uniform(-0.18, 0.18, 6)
        j1[-1] = j1[0]
        j2 = 1 + rng.uniform(-0.15, 0.15, 6)
        j2[-1] = j2[0]
        ca, sa = np.cos(ang + yaw), np.sin(ang + yaw)
        base = np.stack([x + ca * r * j1, y + sa * r * ex * j1, np.full(6, -0.02)], axis=1)
        mid = np.stack([x + ca * r * 0.72 * j2, y + sa * r * ex * 0.72 * j2, np.full(6, h * 0.62)], axis=1)
        a = mb.add(base, np.zeros((6, 3)), np.zeros((6, 2)), np.tile([0.5, 0, 0], (6, 1)))
        b = mb.add(mid, np.zeros((6, 3)), np.zeros((6, 2)), np.tile([0.92, 0, 0], (6, 1)))
        for k in range(5):
            mb.face((a + k, a + k + 1, b + k + 1, b + k), 0)
        c = mb.add([[x + rng.uniform(-0.2, 0.2) * r, y + rng.uniform(-0.2, 0.2) * r, h]], [[0, 0, 1]], [[0, 0]],
                   [[1.0, 0, 0]])
        for k in range(5):
            mb.face((b + k, b + k + 1, c), 0)
    mb.auto_normals(angle=75.0)
    ob = mb.build(name + '_LOD0', [nat_mat('M_rock')])
    box_uv(ob, 4.0)
    return ob


ROCKS = {
    'rock_a': (rock_a, 340, 96, 38.0),
    'rock_b': (rock_b, 340, 96, 34.0),
    'rock_c': (rock_c, 340, 96, 36.0),
    'rock_d': (rock_d, 345, 98, 36.0),
    'rock_e': (rock_e, 300, 90, 38.0),
}
CLIFFS = {'cliff_a': (cliff_a, 890, 0.16), 'cliff_b': (cliff_b, 890, 0.15)}


def collider_for(name, st):
    mn, mx = st['min'], st['max']
    sx, sy, sz = mx[0] - mn[0], mx[1] - mn[1], mx[2]
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
    if name in ('rock_a', 'rock_e'):
        r = round((sx + sy) / 4 * 0.9, 3)
        return {'type': 'sphere', 'radius': r, 'center': [round(cx, 3), round(min(r, sz) * 0.7, 3), round(-cy, 3)]}
    k = 0.8 if name.startswith('cliff') else 0.86
    return {'type': 'box', 'size': [round(sx * k, 3), round(sz * (0.9 if name.startswith('cliff') else 0.95), 3),
                                    round(sy * k, 3)],
            'center': [round(cx, 3), round(sz * 0.45, 3), round(-cy, 3)]}


def main():
    only = cli_only()
    names = list(ROCKS) + list(CLIFFS) + ['pebbles']
    for name in names:
        if only and name not in only:
            continue
        reset_scene()
        objs = []
        if name in ROCKS:
            fn, t0, t1, sharp = ROCKS[name]
            bm, meta = fn()
            bm1 = bm.copy()
            objs.append(finish_rock(bm, name + '_LOD0', t0, sharp_deg=sharp))
            objs.append(finish_rock(bm1, name + '_LOD1', t1, sharp_deg=sharp + 6))
            budgets = (350, 100)
        elif name in CLIFFS:
            fn, t0, vox = CLIFFS[name]
            bm, meta = fn()
            ob = finish_rock(bm, name + '_LOD0', t0, sharp_deg=36.0, remesh=vox, post_smooth=1, ao_dist=3.0)
            # centre the footprint
            b = bmesh.new()
            b.from_mesh(ob.data)
            xs = [v.co.x for v in b.verts]
            ys = [v.co.y for v in b.verts]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            bmesh.ops.translate(b, verts=b.verts, vec=Vector((-cx, -cy, 0)))
            b.to_mesh(ob.data)
            b.free()
            box_uv(ob, 4.0)
            objs.append(ob)
            budgets = (900,)
        else:
            objs.append(build_pebbles(name))
            meta = dict(description='flat scatter of 6 small stones', sink=0.02)
            budgets = (100,)
        meta['vertex_color'] = 'R=AO, G=0, B=0'
        path = os.path.join(NATURE, name + '.glb')
        export_glb(path, objs)
        st = glb_mesh_stats(path)
        meta['collider'] = collider_for(name, st[name + '_LOD0']) if name != 'pebbles' else None
        objs[0]['valombre'] = json.dumps(meta)
        export_glb(path, objs)
        for (k, v), bud in zip(sorted(glb_mesh_stats(path).items()), budgets):
            flag = '' if v['tris'] <= bud else '  !!! OVER BUDGET'
            print('STATS', k, 'tris', v['tris'], 'size', v['size'], 'min', v['min'], 'max', v['max'], flag)
        preview_materials()
        nat_sheet(os.path.join(PREVIEWS, 'nat_%s.png' % name), [[o] for o in objs], views=('front', 'left', 'persp'),
                  res=256, same_bounds=True)
    stack_images([os.path.join(PREVIEWS, 'nat_%s.png' % n) for n in names], os.path.join(PREVIEWS, 'nat_rocks.png'),
                 cols=2)


main()
