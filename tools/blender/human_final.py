"""Final assembly helpers of the VALOMBRE base human: mouth interior, shape keys, UVs, region split,
preview tiles, export + manifest. Used by human_build.py."""
import json
from human_util import *
import human_glb as hglb

REGIONS = ['body_head', 'body_torso', 'body_arms', 'body_hands', 'body_legs', 'body_feet']
REGION_TAG = {'body_head': 'head', 'body_torso': 'torso', 'body_arms': 'arms', 'body_hands': 'hands',
              'body_legs': 'legs', 'body_feet': 'feet'}
X_EAR = 0.0935           # UV1: u = 0.5 + x / (2 * X_EAR)
UV1_Z0, UV1_Z1 = 1.5725, 1.7600


# ----------------------------------------------------------------------------- mouth interior + teeth
def make_mouth():
    m = np.array(LM['mouth'])
    mc = np.array(LM['mouth_corner'])
    HW = hm.MOUTH_HW
    P, F, C = [], [], []
    NS = 12

    def arc_y(x):
        t = min(abs(x) / HW, 1.0)
        return m[1] + (mc[1] - m[1]) * t ** 2.2

    def ring(dy, hw, hh, dz, col, col_low):
        r = []
        for k in range(NS):
            a = 2 * math.pi * k / NS
            x, z = hw * math.cos(a), m[2] + dz + hh * math.sin(a)
            if abs(math.sin(a)) < 1e-6:
                z = float(hm.slit_z(min(abs(x), HW)))
            r.append(len(P))
            P.append((x, arc_y(x) + dy, z))
            C.append(col_low if math.sin(a) < -0.3 else col)
        return r

    r0 = ring(0.0070, HW + 0.0015, 0.0080, 0.0, (0.22, 0.045, 0.045), (0.26, 0.06, 0.06))
    r1 = ring(0.0200, HW + 0.0010, 0.0150, 0.0, (0.11, 0.02, 0.02), (0.36, 0.11, 0.11))
    r2 = ring(0.0420, HW * 0.75, 0.0130, -0.002, (0.035, 0.006, 0.006), (0.16, 0.04, 0.04))
    cb = len(P)
    P.append((0.0, m[1] + 0.058, m[2] - 0.003))
    C.append((0.015, 0.003, 0.003))
    cav = np.array((0.0, m[1] + 0.028, m[2]))
    bag_faces = []
    for ra, rb in ((r0, r1), (r1, r2)):
        for k in range(NS):
            k2 = (k + 1) % NS
            bag_faces.append((ra[k], ra[k2], rb[k2], rb[k]))
    for k in range(NS):
        bag_faces.append((r2[k], r2[(k + 1) % NS], cb))

    def orient(f, toward, inward):
        pts = np.array([P[i] for i in f])
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        d = float(n @ (toward - pts.mean(0)))
        return f if (d > 0) == inward else tuple(reversed(f))

    for f in bag_faces:
        F.append(orient(f, cav, True))
    # teeth
    NT = 11
    xs = np.linspace(-0.0220, 0.0220, NT)
    ay = lambda x: m[1] + 0.0105 + 0.030 * (abs(x) / 0.024) ** 2.0
    tooth, gum = (0.50, 0.47, 0.40), (0.34, 0.13, 0.12)
    arch_c = np.array((0.0, m[1] + 0.040, m[2]))
    for upper in (True, False):
        rows = []
        for x in xs:
            zs = float(hm.slit_z(abs(x)))
            if upper:
                pts = [((x, ay(x) + 0.0008, zs + 0.0092), gum), ((x, ay(x), zs + 0.0006), tooth),
                       ((x * 0.92, ay(x) + 0.0036, zs + 0.0010), tooth)]
            else:
                pts = [((x * 0.96, ay(x) + 0.0030, zs - 0.0102), gum), ((x * 0.96, ay(x) + 0.0022, zs - 0.0008), tooth),
                       ((x * 0.88, ay(x) + 0.0056, zs - 0.0012), tooth)]
            row = []
            for q, c in pts:
                row.append(len(P))
                P.append(q)
                C.append(c)
            rows.append(row)
        for i in range(NT - 1):
            for k in range(2):
                f = (rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1])
                if k == 0:
                    F.append(orient(f, arch_c, False))
                else:      # biting edge: faces the other jaw
                    pts = np.array([P[j] for j in f])
                    n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                    want = -1.0 if upper else 1.0
                    F.append(f if n[2] * want > 0 else tuple(reversed(f)))
    ob = mesh_from('mouth', P, F)
    me = ob.data
    uvl = me.uv_layers.new(name='UVMap')
    li = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', li)
    Pa = np.array(P)
    uv = np.stack([0.5 + Pa[li, 0] / 0.06, (Pa[li, 2] - m[2]) / 0.06 + 0.5], 1)
    uvl.data.foreach_set('uv', uv.astype(np.float32).ravel())
    col = np.concatenate([np.array(C), np.ones((len(C), 1))], 1)
    set_vcol_array(ob, col)
    assign_mat(ob, make_mat('M_mouth', (1.0, 1.0, 1.0), rough=0.45, use_vertex_color=True))
    return ob


# ----------------------------------------------------------------------------- shape keys
def object_points(ob):
    n = len(ob.data.vertices)
    P = np.empty(n * 3, dtype=np.float32)
    ob.data.vertices.foreach_get('co', P)
    return P.reshape(n, 3).astype(np.float64)


def add_shape_keys(ob, names=None, deltas=None):
    """names: morphs this object follows (None = all). deltas: optional precomputed {name: (N,3)}."""
    P = object_points(ob)
    ob.shape_key_add(name='Basis', from_mix=False)
    base = P.astype(np.float32).ravel()
    for nm in hm.MORPH_ORDER:
        k = ob.shape_key_add(name=nm, from_mix=False)
        meta = hm.MORPH_META[nm]
        k.slider_min = float(meta['min'])
        k.slider_max = float(meta['max'])
        k.value = 0.0
        if names is not None and nm not in names:
            k.data.foreach_set('co', base)
            continue
        d = deltas[nm] if deltas is not None else hm.MORPHS[nm](P)
        k.data.foreach_set('co', (P + d).astype(np.float32).ravel())
    ob.active_shape_key_index = 0
    ob.data.update()


def set_morphs(objs, weights):
    for ob in objs:
        if ob.type != 'MESH' or ob.data.shape_keys is None:
            continue
        for k in ob.data.shape_keys.key_blocks[1:]:
            k.value = float(weights.get(k.name, 0.0))


def render_tiles(path, objs, tiles, res=384, cols=4, arm=None):
    """tiles: dicts(center, half, view, morphs={}, pose={})."""
    cam = setup_preview(res)
    imgs = []
    for t in tiles:
        set_morphs(objs, t.get('morphs', {}))
        if arm is not None:
            set_pose(arm, t.get('pose', {}))
        bpy.context.view_layer.update()
        c = Vector(t['center'])
        h = t['half'] / 1.12 / math.sqrt(3.0)
        frame_camera(cam, c - Vector((h, h, h)), c + Vector((h, h, h)), t.get('view', 'front'))
        imgs.append(render_to_array())
    set_morphs(objs, {})
    if arm is not None:
        set_pose(arm, {})
    save_png(path, montage(imgs, cols=cols))
    print('PREVIEW', path)


# ----------------------------------------------------------------------------- UVs
def compute_uvs(P, F, ft, vt):
    """UV0: low distortion projections, 0.5 m per UV unit. UV1 (head only): planar from the front."""
    uv0, uv1 = [], []
    vt = np.array(vt)
    for f, tag in zip(F, ft):
        idx = np.array(f)
        p = P[idx]
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        tags = vt[idx]
        if tag == 'head':
            if np.all(np.isin(tags, ('ear', 'ear_root'))):
                u, v = y / 0.5 + (4.0 if x.mean() > 0 else 6.0), z / 0.5
            elif z.mean() > 1.772:
                u, v = x / 0.5 + 8.0, y / 0.5
            else:
                ang = np.arctan2(x, -(y - 0.005))
                if ang.max() - ang.min() > math.pi:
                    ang = np.where(ang < 0, ang + 2 * math.pi, ang)
                u, v = ang * (0.085 / 0.5), z / 0.5
        elif tag in ('torso', 'legs') and not np.all(tags == 'leg') and abs(x.mean()) < 0.19 and not np.any(tags == 'arm'):
            ang = np.arctan2(x, -(y - 0.01))
            if ang.max() - ang.min() > math.pi:
                ang = np.where(ang < 0, ang + 2 * math.pi, ang)
            u, v = ang * (0.13 / 0.5), z / 0.5
        elif tag == 'legs':
            sx = 1.0 if x.mean() > 0 else -1.0
            ang = np.arctan2((x - sx * 0.10) * sx, -(y - 0.005))
            if ang.max() - ang.min() > math.pi:
                ang = np.where(ang < 0, ang + 2 * math.pi, ang)
            u, v = ang * (0.065 / 0.5) + (10.0 if sx > 0 else 12.0), z / 0.5
        elif tag == 'feet':
            up = 0.0 if z.mean() > 0.012 else 1.0
            u, v = x / 0.5 + 14.0 + up, y / 0.5
        elif tag in ('arms', 'torso'):
            sx = 1.0 if x.mean() > 0 else -1.0
            ang = np.arctan2(z - ARM_Z, -y)
            if ang.max() - ang.min() > math.pi:
                ang = np.where(ang < 0, ang + 2 * math.pi, ang)
            u, v = ang * (0.042 / 0.5) + (16.0 if sx > 0 else 18.0), x * sx / 0.5
        else:   # hands
            up = 0.0 if (np.cross(p[1] - p[0], p[2] - p[0])[2] > 0) else 1.0
            u, v = x / 0.5 + 20.0 + 2 * up, y / 0.5
        uv0.append(np.stack([u, v], 1))
        uv1.append(np.stack([0.5 + x / (2 * X_EAR), (z - UV1_Z0) / (UV1_Z1 - UV1_Z0)], 1))
    return uv0, uv1


ARM_Z = 1.469


# ----------------------------------------------------------------------------- body objects from arrays
def build_body_object(name, D, faces_sel, arm, with_uv1):
    """D: dict(P, F, W, COL, UV0, UV1, DELTAS). faces_sel: list of face indices (None = all)."""
    P, F = D['P'], D['F']
    if faces_sel is None:
        faces_sel = list(range(len(F)))
    used = sorted(set(int(v) for fi in faces_sel for v in F[fi]))
    mp = {v: i for i, v in enumerate(used)}
    idx = np.array(used)
    faces = [tuple(mp[int(v)] for v in F[fi]) for fi in faces_sel]
    ob = mesh_from(name, P[idx], faces)
    me = ob.data
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', np.concatenate([D['UV0'][fi] for fi in faces_sel], 0).astype(np.float32).ravel())
    if with_uv1:
        uv2 = me.uv_layers.new(name='UVFace')
        uv2.data.foreach_set('uv', np.concatenate([D['UV1'][fi] for fi in faces_sel], 0).astype(np.float32).ravel())
    me.uv_layers.active = uvl
    uvl.active_render = True
    set_vcol_array(ob, D['COL'][idx])
    add_skin(ob, D['W'][idx], arm)
    add_shape_keys(ob, deltas={k: v[idx] for k, v in D['DELTAS'].items()})
    assign_mat(ob, skin_preview_material())
    return ob


# ----------------------------------------------------------------------------- export + manifest
def export_human(glb_path, arm, regions, extras):
    objs = [arm] + regions + extras
    set_morphs(objs, {})
    set_pose(arm, {})
    info = export_glb(glb_path, objs, anims=False, morphs=True)
    js, arrays = hglb.read_glb(glb_path)
    fix = hglb.fix_body_normals(js, arrays, set(REGIONS))
    size = hglb.write_glb(glb_path, js, arrays)
    print('NORMALS_FIX', json.dumps(fix), 'bytes', size)
    js, arrays = hglb.read_glb(glb_path)
    desc = hglb.describe(js, arrays)
    for d in desc:
        print('GLB_MESH', json.dumps(d))
    info = glb_info(glb_path)
    print('EXPORTED', os.path.relpath(glb_path, ROOT), json.dumps(info['summary']))
    return info, desc, js, arrays


def border_check(js, arrays):
    """Border vertices duplicated between body regions must be identical in every attribute."""
    recs = []
    for m in js['meshes']:
        if m['name'] not in REGIONS:
            continue
        for p in m['primitives']:
            at = p['attributes']
            d = {'mesh': m['name'], 'P': arrays[at['POSITION']], 'N': arrays[at['NORMAL']],
                 'J': arrays[at['JOINTS_0']], 'W': arrays[at['WEIGHTS_0']].astype(np.float64),
                 'C': arrays[at['COLOR_0']].astype(np.float64),
                 'T': [arrays[t['POSITION']] for t in p.get('targets', [])],
                 'TN': [arrays[t['NORMAL']] for t in p.get('targets', []) if 'NORMAL' in t]}
            recs.append(d)
    allp = np.ascontiguousarray(np.concatenate([r['P'] for r in recs], 0).astype(np.float32))
    owner = np.concatenate([np.full(len(r['P']), i) for i, r in enumerate(recs)])
    local = np.concatenate([np.arange(len(r['P'])) for r in recs])
    key = allp.view(np.dtype((np.void, 12))).ravel()
    uniq, first, inv = np.unique(key, return_index=True, return_inverse=True)
    inv = inv.ravel()
    order = np.argsort(inv, kind='stable')
    res = {'border_vertices': 0, 'max_normal_diff': 0.0, 'max_weight_diff': 0.0, 'max_morph_diff': 0.0,
           'max_morph_normal_diff': 0.0, 'max_color_diff': 0.0}

    def wvec(r, i):
        v = np.zeros(64)
        for j, w in zip(r['J'][i], r['W'][i]):
            v[int(j)] += w
        return v

    grp = {}
    for o in order:
        grp.setdefault(int(inv[o]), []).append(int(o))
    for g in grp.values():
        own = set(int(owner[o]) for o in g)
        if len(own) < 2:
            continue
        res['border_vertices'] += 1
        a = g[0]
        ra, ia = recs[owner[a]], local[a]
        for b in g[1:]:
            rb, ib = recs[owner[b]], local[b]
            res['max_normal_diff'] = max(res['max_normal_diff'], float(np.abs(ra['N'][ia] - rb['N'][ib]).max()))
            res['max_weight_diff'] = max(res['max_weight_diff'], float(np.abs(wvec(ra, ia) - wvec(rb, ib)).max()))
            res['max_color_diff'] = max(res['max_color_diff'], float(np.abs(ra['C'][ia] / max(ra['C'].max(), 1) - rb['C'][ib] / max(rb['C'].max(), 1)).max()))
            for ta, tb in zip(ra['T'], rb['T']):
                res['max_morph_diff'] = max(res['max_morph_diff'], float(np.abs(ta[ia] - tb[ib]).max()))
            for ta, tb in zip(ra['TN'], rb['TN']):
                res['max_morph_normal_diff'] = max(res['max_morph_normal_diff'], float(np.abs(ta[ia] - tb[ib]).max()))
    return res
