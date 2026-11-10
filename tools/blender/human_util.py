"""Blender side helpers of the VALOMBRE base human pipeline (objects, preview materials, vertex colours,
skin weights, shape keys, UVs, preview sheets). Used by human_build.py."""
import sys, os, time, math
from blcommon import *
from humanoid_rig import *
import numpy as np
import human_morphs as hm
from human_mesh import *
import human_mesh as hmesh
import human_body as hmesh_body

LM = hm.LM


# ============================================================================= blender objects
def mesh_from(name, P, F):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in P], [], [tuple(int(v) for v in f) for f in F])
    me.update()
    ob = bpy.data.objects.new(name, me)
    link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def recalc_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def skin_preview_material():
    m = bpy.data.materials.get('M_skin') or bpy.data.materials.new('M_skin')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    vc = nt.nodes.new('ShaderNodeVertexColor')
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(vc.outputs['Color'], sep.inputs['Color'])

    def mix(c1, c2, fac_socket, fac_mul):
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = fac_mul
        nt.links.new(fac_socket, mul.inputs[0])
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MIX'
        nt.links.new(mul.outputs[0], mx.inputs[0])
        if isinstance(c1, tuple):
            mx.inputs[6].default_value = (*c1, 1)
        else:
            nt.links.new(c1, mx.inputs[6])
        mx.inputs[7].default_value = (*c2, 1)
        return mx.outputs[2]

    skin = lin('#c9a184')
    c = mix(skin, lin('#a8554c'), sep.outputs[2], 0.80)       # lips (B)
    c = mix(c, lin('#c0624f'), sep.outputs[0], 0.55)          # blush (R)
    ao = nt.nodes.new('ShaderNodeMapRange')
    ao.inputs[1].default_value = 0.0
    ao.inputs[2].default_value = 1.0
    ao.inputs[3].default_value = 0.22
    ao.inputs[4].default_value = 1.0
    nt.links.new(sep.outputs[1], ao.inputs[0])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    nt.links.new(c, mx.inputs[6])
    nt.links.new(ao.outputs[0], mx.inputs[7])
    nt.links.new(mx.outputs[2], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.55
    try:
        bsdf.inputs['Subsurface Weight'].default_value = 0.0
    except Exception:
        pass
    return m


def eye_preview_material():
    m = bpy.data.materials.get('M_eye') or bpy.data.materials.new('M_eye')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    uv = nt.nodes.new('ShaderNodeUVMap')
    sub = nt.nodes.new('ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    nt.links.new(uv.outputs[0], sub.inputs[0])
    ln = nt.nodes.new('ShaderNodeVectorMath')
    ln.operation = 'LENGTH'
    nt.links.new(sub.outputs[0], ln.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.interpolation = 'LINEAR'
    iris = lin('#5b7a86')
    stops = [(0.0, (0.01, 0.01, 0.01)), (0.085, (0.01, 0.01, 0.01)), (0.100, tuple(x * 0.9 for x in iris)),
             (0.205, iris), (0.232, tuple(x * 0.25 for x in iris)), (0.250, lin('#e9e2da')), (0.5, lin('#d8cdc4'))]
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = (*stops[0][1], 1)
    cr.elements[1].position = stops[1][0]
    cr.elements[1].color = (*stops[1][1], 1)
    for pos, col in stops[2:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    nt.links.new(ln.outputs['Value'], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.12
    return m


def make_eye(name, c):
    bm = bmesh.new()
    rot = Matrix.Rotation(math.radians(90), 4, 'X')
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=E_R, matrix=rot)
    uvl = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = (0.5 + l.vert.co.x / (2 * E_R), 0.5 + l.vert.co.z / (2 * E_R))
    for v in bm.verts:
        v.co += Vector(c)
    ob = bmesh_to_object(bm, name)
    assign_mat(ob, eye_preview_material())
    set_vertex_colors(ob, lambda p, n, i: (1, 1, 1, 1))
    return ob


BROW_PTS = [  # x, z, half width (z)
    (0.0100, 1.7012, 0.0026), (0.0170, 1.7040, 0.0036), (0.0250, 1.7060, 0.0036), (0.0330, 1.7070, 0.0033),
    (0.0410, 1.7068, 0.0028), (0.0480, 1.7052, 0.0021), (0.0535, 1.7028, 0.0013), (0.0575, 1.7002, 0.0005)]


LASH_S = [0.03, 0.085, 0.24, 0.40, 0.56, 0.71, 0.85, 0.94, 0.985]


def make_brows():
    """Eyebrows (curved strips slightly raised off the skin) + upper eyelashes (thin double sided strips).
    One mesh, material M_hair, vertex colour white. UV: u along the strip, v across (0 = root)."""
    H = SDFS['head']
    P, F, UV = [], [], []
    hc = np.array(LM['head_center'])

    def outward(f):
        pts = np.array([P[i] for i in f])
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        return f if float(n @ (pts.mean(0) - hc)) > 0 else tuple(reversed(f))

    for sx in (1, -1):
        base = len(P)
        nb = len(BROW_PTS)
        for s, (x, z, hw) in enumerate(BROW_PTS):
            hw = hw * 0.85
            for k, (dz, lift) in enumerate(((-hw, 0.0002), (0.0, 0.0011), (hw, 0.0002))):
                o = np.array([[x * 0.2, -0.02, z + dz]])
                d = np.array([[x * 0.8, -0.075, 0.0]])
                p, ok = H.ray(o, d, 0.14)
                g = H.grad(p)[0]
                g /= np.linalg.norm(g)
                q = p[0] + g * lift
                P.append((q[0] * sx, q[1], q[2]))
                UV.append((s / float(nb - 1), k / 2.0))
        for s in range(nb - 1):
            for k in range(2):
                F.append(outward((base + s * 3 + k, base + (s + 1) * 3 + k, base + (s + 1) * 3 + k + 1, base + s * 3 + k + 1)))
        # upper eyelashes
        base = len(P)
        nl = len(LASH_S)
        for i, s in enumerate(LASH_S):
            b = lid_pt(s, True, off=0.0013)
            ln = 0.0024 * max(math.sin(math.pi * s), 0.0) ** 0.5 + 0.0005
            dr = nrm((0.55 * (s - 0.35), -0.80, 0.55))
            t = b + dr * ln
            # 4 vertices per sample: top side (root, tip) and underside (root, tip), 0.05 mm apart
            for dzs in (0.0, -0.00005):
                P.append((b[0] * sx, b[1], b[2] + dzs))
                UV.append((i / float(nl - 1), 0.0))
                P.append((t[0] * sx, t[1], t[2] + dzs))
                UV.append((i / float(nl - 1), 1.0))
        for i in range(nl - 1):
            a = base + 4 * i
            f = (a, a + 4, a + 5, a + 1)
            pts = np.array([P[j] for j in f])
            up = np.cross(pts[1] - pts[0], pts[2] - pts[0])[2] > 0
            F.append(f if up else tuple(reversed(f)))
            g = (a + 2, a + 6, a + 7, a + 3)
            F.append(tuple(reversed(g)) if up else g)
    ob = mesh_from('brows', P, F)
    uvl = ob.data.uv_layers.new(name='UVMap')
    li = np.empty(len(ob.data.loops), dtype=np.int32)
    ob.data.loops.foreach_get('vertex_index', li)
    uvl.data.foreach_set('uv', np.array(UV)[li].astype(np.float32).ravel())
    assign_mat(ob, make_mat('M_hair', lin('#3a2a1f'), rough=0.6, use_vertex_color=True))
    set_vertex_colors(ob, lambda p, n, i: (1, 1, 1, 1))
    return ob


def mesh_arrays(ob):
    me = ob.data
    n = len(me.vertices)
    P = np.empty(n * 3)
    me.vertices.foreach_get('co', P)
    N = np.empty(n * 3)
    me.vertices.foreach_get('normal', N)
    E = np.empty(len(me.edges) * 2, dtype=np.int32)
    me.edges.foreach_get('vertices', E)
    return P.reshape(n, 3), N.reshape(n, 3), E.reshape(-1, 2)


slit_z = hm.slit_z


def lip_mask(P):
    ax, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    t = np.clip(ax / MOUTH_HW, 0, 1)
    hu = 0.0084 * (1 - t ** 2.2) ** 0.8 - 0.0011 * np.exp(-(ax / 0.0035) ** 2)
    hl = 0.0100 * (1 - t ** 2.0) ** 0.75
    dz = z - slit_z(ax)
    up = 1.0 - sstep(hu - 0.0010, hu + 0.0012, dz)
    lo = 1.0 - sstep(hl - 0.0010, hl + 0.0012, -dz)
    m = np.where(dz >= 0, up, lo)
    m = m * (1.0 - sstep(MOUTH_HW - 0.0005, MOUTH_HW + 0.0015, ax)) * sstep(0.070, 0.078, -y)
    return m * (np.abs(dz) < 0.02)


def gauss(P, c, s):
    q = np.array(P, dtype=np.float64)
    q[:, 0] = np.abs(q[:, 0])
    s = np.broadcast_to(np.asarray(s, float), (3,))
    return np.exp(-(((q - np.asarray(c, float)) / s) ** 2).sum(1))


def set_vcol_array(ob, col, name='Col'):
    me = ob.data
    attr = me.color_attributes.get(name) or me.color_attributes.new(name, 'FLOAT_COLOR', 'CORNER')
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = list(me.color_attributes).index(attr)
    li = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', li)
    attr.data.foreach_set('color', col[li].astype(np.float32).ravel())


def skin_colors(ob, M):
    """COLOR_0 on the skin (linear): R blush, G ambient occlusion / cavity, B lips, A 1."""
    P, N, E = mesh_arrays(ob)
    n = len(P)
    S = np.zeros((n, 3))
    C = np.zeros(n)
    L = np.zeros(n)
    el = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
    for a, b in ((0, 1), (1, 0)):
        np.add.at(S, E[:, a], P[E[:, b]])
        np.add.at(C, E[:, a], 1.0)
        np.add.at(L, E[:, a], el)
    C = np.maximum(C, 1)
    cav = (((S / C[:, None]) - P) * N).sum(1) / np.maximum(L / C, 1e-6)
    ax, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    R = np.zeros(n)
    G = np.ones(n)
    G -= np.clip(cav * 1.2, -0.05, 0.30)
    B = lip_mask(P)
    front = sstep(0.050, 0.068, -y)
    # ---- head AO
    G -= 0.20 * np.exp(-((ax - 0.0318) / 0.019) ** 2 - ((z - 1.6895) / 0.011) ** 2) * front
    G -= 0.14 * np.exp(-((ax - 0.0200) / 0.006) ** 2 - ((z - 1.6900) / 0.009) ** 2) * front      # inner corner
    G -= 0.16 * gauss(P, (0.0068, -0.1038, 1.6455), 0.0042)
    G -= 0.08 * gauss(P, (0.0, -0.0990, 1.6405), (0.013, 0.006, 0.003))
    G -= 0.14 * gauss(P, (LM['mouth_corner'][0] + 0.001, LM['mouth_corner'][1], LM['mouth_corner'][2]), 0.0045)
    under = sstep(0.25, 0.85, -N[:, 2]) * sstep(1.53, 1.56, z) * (1 - sstep(1.60, 1.615, z)) * (ax < 0.07)
    G -= 0.28 * under
    # ---- blush
    R += 0.35 * gauss(P, (0.046, -0.066, 1.648), (0.019, 0.030, 0.017))
    R += 0.25 * gauss(P, LM['nose_tip'], (0.010, 0.010, 0.008))
    R += 0.12 * gauss(P, (0.0125, -0.1005, 1.648), 0.007)
    # ---- body AO
    G -= 0.30 * gauss(P, (0.165, 0.000, 1.392), (0.035, 0.055, 0.030))          # armpits
    G -= 0.30 * gauss(P, (0.000, 0.010, 0.845), (0.045, 0.075, 0.040))          # crotch
    G -= 0.22 * gauss(P, (0.000, 0.105, 0.915), (0.012, 0.030, 0.060))          # between the glutes
    G -= 0.10 * gauss(P, (0.085, 0.060, 0.855), (0.060, 0.050, 0.018))          # gluteal fold
    G -= 0.25 * sstep(0.012, 0.002, z) * (z < 0.02)                             # soles
    G -= 0.10 * gauss(P, (0.100, 0.035, 0.500), (0.040, 0.025, 0.030))          # back of the knee
    G -= 0.10 * gauss(P, (0.470, -0.030, 1.468), (0.030, 0.020, 0.030))         # inside of the elbow
    G -= 0.08 * gauss(P, (0.000, -0.045, 1.470), (0.030, 0.020, 0.015))         # pit of the neck
    # ---- body blush: knees, elbows, (knuckles are set by the hand builder)
    R += 0.25 * gauss(P, (0.100, -0.060, 0.500), (0.035, 0.030, 0.035))
    R += 0.25 * gauss(P, (0.470, 0.040, 1.468), (0.030, 0.025, 0.030))
    R += 0.10 * gauss(P, (0.100, 0.060, 0.040), (0.03, 0.03, 0.03))             # heels
    for i, c in M['col'].items():
        if c[0] is not None:
            R[i] = c[0]
        if c[1] is not None:
            G[i] = min(G[i], c[1])
        if c[2] is not None:
            B[i] = c[2]
    col = np.stack([np.clip(R, 0, 1), np.clip(G, 0.03, 1), np.clip(B, 0, 1), np.ones(n)], 1)
    set_vcol_array(ob, col)
    return col


def wire_overlay(ob):
    w = ob.copy()
    w.data = ob.data.copy()
    link(w)
    w.name = ob.name + '_wire'
    md = w.modifiers.new('w', 'WIREFRAME')
    md.thickness = 0.0005
    md.use_even_offset = False
    assign_mat(w, make_mat('M_wire', (0.02, 0.02, 0.02), rough=1.0))
    return w


def preview_lights(shadows=False):
    """Soft studio lighting for close-ups (the default hard sun shadows crackle on low-poly skin)."""
    setup_preview(64)
    for nm, energy in (('pv_key', 2.6), ('pv_fill', 1.0), ('pv_rim', 1.3)):
        lo = bpy.data.objects.get(nm)
        if lo is None:
            continue
        lo.data.energy = energy
        lo.data.use_shadow = bool(shadows) and nm == 'pv_key'
        try:
            lo.data.angle = math.radians(14)
            lo.data.use_shadow_jitter = True
            lo.data.shadow_jitter_overblur = 12
        except Exception:
            pass


def shots(path, objs, center, half, views, res=512, cols=3):
    c = Vector(center)
    h = half / 1.12 / math.sqrt(3.0)
    render_sheet(path, objs, views=views, res=res, cols=cols,
                 fixed_bounds=(c - Vector((h, h, h)), c + Vector((h, h, h))))


V34 = (-0.62, 0.78, -0.06)
VPROF = (-1, 0.0001, 0)

# ============================================================================= skin weights
MIRROR_BONE = {}
for _n in DEFORM_BONES:
    if _n.endswith('_L'):
        MIRROR_BONE[_n] = _n[:-2] + '_R'
    elif _n.endswith('_R'):
        MIRROR_BONE[_n] = _n[:-2] + '_L'
    else:
        MIRROR_BONE[_n] = _n
BI = {n: i for i, n in enumerate(DEFORM_BONES)}
HEAD_TAGS = ('head', 'lid', 'lid_in', 'lipline', 'lip_in', 'nostril', 'ear', 'ear_root')


def compute_weights(M, arm):
    P = M['P']
    n = len(P)
    tmp = mesh_from('tmp_skin', P, M['F'])
    recalc_normals(tmp)
    ok = auto_weights(tmp, arm)
    print('AUTO_WEIGHTS bone heat ok:', ok)
    nb = len(DEFORM_BONES)
    W = np.zeros((n, nb))
    gi = {g.index: BI.get(g.name, -1) for g in tmp.vertex_groups}
    for v in tmp.data.vertices:
        for g in v.groups:
            b = gi[g.group]
            if b >= 0:
                W[v.index, b] = g.weight
    E = np.empty(len(tmp.data.edges) * 2, dtype=np.int32)
    tmp.data.edges.foreach_get('vertices', E)
    E = E.reshape(-1, 2)
    bpy.data.objects.remove(tmp, do_unlink=True)

    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    vt = np.array(M['vt'])
    side = M['side']
    zone = np.zeros(n, int)          # 0 torso, 1 head, 2 neck, 3 arm, 4 hand, 5 leg, 6 foot
    zone[np.isin(vt, HEAD_TAGS)] = 1
    zone[np.isin(vt, ('neck', 'collar'))] = 2
    zone[vt == 'arm'] = 3
    zone[vt == 'hand'] = 4
    zone[vt == 'leg'] = 5
    zone[vt == 'foot'] = 6

    def cols(names):
        return [BI[k] for k in names]

    L = [i for i, k in enumerate(DEFORM_BONES) if k.endswith('_L')]
    R = [i for i, k in enumerate(DEFORM_BONES) if k.endswith('_R')]
    limb = np.isin(zone, (3, 4, 5, 6))
    # ---- no cross-body influences
    W[np.ix_(limb & (side > 0), R)] = 0.0
    W[np.ix_(limb & (side < 0), L)] = 0.0
    sl = sstep(-0.03, 0.03, x)
    W[:, L] *= np.where(limb, 1.0, sl)[:, None]
    W[:, R] *= np.where(limb, 1.0, 1.0 - sl)[:, None]
    # ---- allowed bones per zone
    allow = np.zeros((7, nb), bool)
    spine = ['hips', 'spine_01', 'spine_02', 'spine_03']
    for sfx in ('_L', '_R'):
        allow[0, cols(spine + ['neck', 'clavicle' + sfx, 'upper_arm' + sfx, 'thigh' + sfx])] = True
        allow[2, cols(['spine_02', 'spine_03', 'neck', 'head', 'clavicle' + sfx])] = True
        allow[3, cols(['spine_02', 'spine_03', 'clavicle' + sfx, 'upper_arm' + sfx, 'forearm' + sfx, 'hand' + sfx])] = True
        allow[4, cols(['forearm' + sfx, 'hand' + sfx])] = True
        allow[5, cols(['hips', 'spine_01', 'thigh' + sfx, 'shin' + sfx, 'foot' + sfx])] = True
        allow[6, cols(['shin' + sfx, 'foot' + sfx, 'toe' + sfx])] = True
    allow[1, cols(['head', 'neck'])] = True
    W *= allow[zone]
    ax = np.abs(x)
    far_arm = (zone == 3) & (ax > 0.30)
    W[np.ix_(far_arm, cols(['spine_02', 'spine_03', 'clavicle_L', 'clavicle_R']))] = 0.0
    low_leg = (zone == 5) & (z < 0.74)
    W[np.ix_(low_leg, cols(['hips', 'spine_01']))] = 0.0
    up_arm = (zone == 3) & (ax < 0.40)
    W[np.ix_(up_arm, cols(['hand_L', 'hand_R']))] = 0.0

    def norm(W):
        s = W.sum(1)
        bad = s < 1e-6
        W[bad] = 0
        return W / np.maximum(s, 1e-6)[:, None], bad

    W, bad = norm(W)
    if bad.any():
        print('WARN: %d vertices without weights after cleanup' % int(bad.sum()), set(vt[bad]))
        W[bad & (zone == 1), BI['head']] = 1.0
        W[bad & (zone == 0), BI['spine_02']] = 1.0
    # ---- smoothing (body only)
    sm = np.where(np.isin(zone, (0, 2, 3, 5, 6)), 1.0, 0.0)
    for _ in range(3):
        S = np.zeros_like(W)
        C = np.zeros(n)
        for a, b in ((0, 1), (1, 0)):
            np.add.at(S, E[:, a], W[E[:, b]])
            np.add.at(C, E[:, a], 1.0)
        avg = S / np.maximum(C, 1)[:, None]
        W = W + (0.5 * sm)[:, None] * (avg - W)
    W *= allow[zone]
    W[np.ix_(limb & (side > 0), R)] = 0.0
    W[np.ix_(limb & (side < 0), L)] = 0.0
    W, _ = norm(W)
    # ---- shoulders: analytic blend of the upper arm (cleaner than bone heat when the arm goes down)
    ang = np.arctan2(z - 1.469, -y)
    top = np.sin(ang)
    x0 = 0.150 - 0.012 * top
    x1 = x0 + 0.090 - 0.012 * top
    wu = sstep(x0, x1, ax)
    sh = np.isin(zone, (0, 3)) & (z > 1.33) & (ax > 0.10) & (ax < 0.33)
    for sfx, sgn in (('_L', 1), ('_R', -1)):
        sel = sh & (side * sgn >= 0) & (x * sgn > 0)
        armb = cols(['upper_arm' + sfx, 'forearm' + sfx, 'hand' + sfx])
        rest = W[sel].copy()
        armw = rest[:, armb].copy()
        rest[:, armb] = 0.0
        rs = rest.sum(1)
        e = rs < 1e-5
        rest[e] = 0.0
        rest[e, BI['clavicle' + sfx]] = 0.6
        rest[e, BI['spine_03']] = 0.4
        rest /= rest.sum(1)[:, None]
        sa = armw.sum(1)
        ea = sa < 1e-5
        armw[ea] = (1.0, 0.0, 0.0)
        armw /= armw.sum(1)[:, None]
        new = rest * (1.0 - wu[sel])[:, None]
        new[:, armb] += armw * wu[sel][:, None]
        W[sel] = new
    # ---- head / neck: analytic
    hz = np.isin(zone, (1, 2))
    zmid = lerp(1.555, 1.590, sstep(-0.05, 0.07, y))
    wh = sstep(zmid - 0.028, zmid + 0.022, z)
    wh = np.where(zone == 1, np.maximum(wh, sstep(1.60, 1.63, z)), wh)
    rest = W.copy()
    rest[:, BI['head']] = 0.0
    rs = rest.sum(1)
    empty = rs < 1e-5
    rest[empty] = 0
    rest[empty, BI['neck']] = 1.0
    rest /= rest.sum(1)[:, None]
    Wh = rest * (1 - wh)[:, None]
    Wh[:, BI['head']] += wh
    W[hz] = Wh[hz]
    # ---- hands: analytic
    for i, (part, f) in M['hand'].items():
        sfx = '_L' if side[i] > 0 else '_R'
        w = {}
        if part == 'palm':
            wf = 0.5 * (1.0 - min(f / 0.35, 1.0))
            w = {'forearm' + sfx: wf, 'hand' + sfx: 1.0 - wf}
        elif part == 'thumb':
            w01 = float(sstep(0.0, 0.2, f))
            w2 = float(sstep(0.44, 0.56, f))
            w = {'hand' + sfx: 1 - w01, 'thumb_01' + sfx: w01 * (1 - w2), 'thumb_02' + sfx: w01 * w2}
        else:
            k = int(part[1])
            b1, b2 = ('index_01', 'index_02') if k == 0 else ('fingers_01', 'fingers_02')
            xk = (0.810, 0.813, 0.808, 0.798)[k]
            xp = hmesh_body.F_XPIP[k]
            w01 = float(sstep(xk - 0.006, xk + 0.010, ax[i]))
            w2 = float(sstep(xp - 0.006, xp + 0.006, ax[i]))
            w = {'hand' + sfx: 1 - w01, b1 + sfx: w01 * (1 - w2), b2 + sfx: w01 * w2}
        W[i] = 0.0
        for k2, val in w.items():
            W[i, BI[k2]] = val
    # ---- max 4 influences, normalised
    W[W < 0.004] = 0.0
    order = np.argsort(-W, axis=1)
    drop = order[:, 4:]
    np.put_along_axis(W, drop, 0.0, axis=1)
    W, _ = norm(W)
    # ---- symmetrise (left half is the reference)
    mi = M['mirror']
    perm = [BI[MIRROR_BONE[k]] for k in DEFORM_BONES]
    nh = M['nhalf']
    src = np.arange(nh)
    off = mi[:nh] != src
    W[mi[:nh][off]] = W[src[off]][:, perm]
    cen = src[~off]
    W[cen] = 0.5 * (W[cen] + W[cen][:, perm])
    # centre line: still at most 4 influences (drop the weakest, as symmetric pairs)
    for i in cen:
        while (W[i] > 0).sum() > 4:
            nzb = np.where(W[i] > 0)[0]
            b = nzb[np.argmin(W[i, nzb])]
            W[i, b] = 0.0
            W[i, perm[b]] = 0.0
        W[i] /= W[i].sum()
    return W


def make_skinned(name, P, F, W, arm, mat=None):
    ob = mesh_from(name, P, F)
    recalc_normals(ob)
    add_skin(ob, W, arm)
    if mat:
        assign_mat(ob, mat)
    return ob


def add_skin(ob, W, arm):
    for b, bn in enumerate(DEFORM_BONES):
        idx = np.where(W[:, b] > 0)[0]
        if len(idx) == 0:
            continue
        vg = ob.vertex_groups.new(name=bn)
        for i in idx:
            vg.add([int(i)], float(W[i, b]), 'REPLACE')
    md = ob.modifiers.new('Armature', 'ARMATURE')
    md.object = arm
    ob.parent = arm


def rigid_skin(ob, arm, bone='head'):
    rigid_weights(ob, arm, bone)


def set_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    for bn, v in pose.items():
        pb = arm.pose.bones[bn]
        if bn == 'root' or len(v) == 6:
            pb.location = v[3:6] if len(v) == 6 else v
            if len(v) != 6:
                continue
        pb.rotation_quaternion = Euler([math.radians(a) for a in v[:3]]).to_quaternion()
    bpy.context.view_layer.update()


POSES = {
    'a_pose': {'upper_arm_L': (-55, 0, 0), 'upper_arm_R': (-55, 0, 0), 'forearm_L': (0, 0, -12), 'forearm_R': (0, 0, 12)},
    'arms_down': {'upper_arm_L': (-78, 0, 0), 'upper_arm_R': (-78, 0, 0)},
    'elbows_knees_90': {'upper_arm_L': (-40, 0, 0), 'upper_arm_R': (-40, 0, 0), 'forearm_L': (0, 0, -90),
                        'forearm_R': (0, 0, 90), 'thigh_L': (-90, 0, 0), 'shin_L': (90, 0, 0)},
    'crouch': {'hips': (20, 0, 0, 0, 0, -0.42), 'thigh_L': (-115, 0, 0), 'thigh_R': (-115, 0, 0), 'shin_L': (125, 0, 0),
               'shin_R': (125, 0, 0), 'foot_L': (-30, 0, 0), 'foot_R': (-30, 0, 0), 'spine_02': (15, 0, 0),
               'upper_arm_L': (-60, 0, -40), 'upper_arm_R': (-60, 0, 40), 'forearm_L': (0, 0, -60), 'forearm_R': (0, 0, 60)},
    'arms_up': {'upper_arm_L': (75, 0, 0), 'upper_arm_R': (75, 0, 0), 'clavicle_L': (15, 0, 0), 'clavicle_R': (15, 0, 0)},
    'head_turn': {'head': (0, 40, 0), 'neck': (0, 20, 0), 'upper_arm_L': (-78, 0, 0), 'upper_arm_R': (-78, 0, 0)},
    'fist': {'upper_arm_L': (-30, 0, -30), 'forearm_L': (0, 0, -70), 'fingers_01_L': (-80, 0, 0), 'fingers_02_L': (-95, 0, 0),
             'index_01_L': (-80, 0, 0), 'index_02_L': (-95, 0, 0), 'thumb_01_L': (-25, 0, -30), 'thumb_02_L': (-40, 0, 0),
             'upper_arm_R': (-78, 0, 0)},
}


