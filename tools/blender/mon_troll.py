"""VALOMBRE mountain troll -> assets/models/creatures/troll.glb (~3.0 m, shared humanoid rig with brute_warp).

The body is sculpted as an implicit surface (mon_sdf.py: smooth unions of ellipsoids / round cones, cuts for
folds and eye sockets, noise for the lumpy hide), polygonised with surface nets, decimated to budget and skinned
with bone-heat weights. Tusks, nails, eyes and the fur loincloth are small rigid / hand-weighted parts.

Run:  blender -b --factory-startup -P tools/blender/mon_troll.py [-- --sculpt]
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mon_lib import *
from mon_sdf import Field, Ell, Sph, Cone, rot_xyz

HIDE, HIDE_DK, HIDE_BELLY, MOSS, MUD, HIDE_PINK = C('#687058'), C('#3a4234'), C('#9a9676'), C('#4f6226'), C('#3a3226'), C('#84705c')
FUR, FUR_DK, FUR_TIP = C('#4a382a'), C('#261c15'), C('#8a7252')
TUSK, TUSK_DK = C('#d8cba4'), C('#7c6a48')
EYE = C('#ffc640')
BODY_TRIS = 8150


def sculpt():
    f = Field((-2.56, -0.82, -0.06), (2.56, 0.78, 3.12), 0.02)
    f.tagged = []
    Cc = f.cut

    def A(prim, k=0.05, mirror=False, tag=None):
        f.add(prim, k, mirror)
        if tag:
            f.tagged.append((prim, mirror, tag))
    # ---- trunk
    A(Ell((0, 0.03, 1.16), (0.44, 0.34, 0.27)), 0.0, False, 'TRUNK')
    A(Ell((0, -0.13, 1.47), (0.50, 0.44, 0.40)), 0.12, False, 'TRUNK')                        # pot belly
    A(Ell((0, -0.27, 1.28), (0.37, 0.25, 0.2)), 0.10, False, 'TRUNK')                         # sagging lower belly
    A(Ell((0, -0.03, 1.98), (0.60, 0.42, 0.40)), 0.15, False, 'TRUNK')                        # rib cage
    A(Ell((0, 0.20, 2.40), (0.57, 0.37, 0.40)), 0.15, False, 'TRUNK')                         # hunched upper back
    A(Ell((0, 0.21, 2.67), (0.37, 0.28, 0.30)), 0.12, False, 'TRUNK')                         # hump
    A(Sph((0.66, 0.03, 2.37), 0.30), 0.12, True, 'clavicle_S')                              # shoulders
    A(Ell((0.27, -0.33, 2.08), (0.27, 0.15, 0.20)), 0.08, True, 'TRUNK')               # slab pecs
    A(Ell((0.48, 0.06, 1.90), (0.20, 0.30, 0.35)), 0.12, True, 'TRUNK')                # flanks
    A(Ell((0.21, 0.22, 1.12), (0.24, 0.20, 0.22)), 0.10, True, 'hips')                # buttocks
    for y, z, r in ((0.585, 2.52, 0.06), (0.60, 2.34, 0.065), (0.565, 2.16, 0.06), (0.49, 1.98, 0.055), (0.42, 1.80, 0.05), (0.385, 1.62, 0.045)):
        A(Sph((0, y, z), r), 0.05)                                            # knobs of the spine
    # ---- neck and head (low, thrust forward)
    A(Cone((0, -0.06, 2.27), (0, -0.26, 2.45), 0.25, 0.20), 0.12, False, 'neck')
    A(Ell((0, -0.30, 2.59), (0.185, 0.22, 0.185)), 0.08, False, 'head')                      # skull
    A(Ell((0, -0.43, 2.455), (0.175, 0.17, 0.115)), 0.06, False, 'head')                     # heavy jaw
    A(Sph((0, -0.545, 2.405), 0.075), 0.05)                                   # chin
    A(Cone((-0.14, -0.505, 2.645), (0.14, -0.505, 2.645), 0.064), 0.04)       # brow ridge
    A(Ell((0, -0.575, 2.55), (0.082, 0.085, 0.085)), 0.04)                    # bulbous nose
    A(Cone((-0.12, -0.585, 2.45), (0.12, -0.585, 2.45), 0.04), 0.03)          # lower lip
    A(Sph((0.135, -0.445, 2.545), 0.07), 0.05, True)                          # cheekbones
    A(Cone((0.16, -0.27, 2.60), (0.37, -0.15, 2.70), 0.065, 0.016), 0.04, True, 'head')   # ears
    A(Cone((0.0, -0.36, 2.76), (0.0, -0.12, 2.74), 0.05, 0.04), 0.05)         # crest
    # ---- arms
    A(Cone((0.66, 0.0, 2.31), (1.30, 0.0, 2.28), 0.225, 0.165), 0.10, True, 'upper_arm_S')
    A(Ell((0.98, 0.0, 2.305), (0.28, 0.20, 0.215)), 0.08, True, 'upper_arm_S')               # upper arm mass
    A(Sph((1.30, 0.05, 2.265), 0.15), 0.06, True)                             # elbow
    A(Cone((1.30, 0, 2.28), (1.90, 0, 2.28), 0.175, 0.118), 0.08, True, 'forearm_S')
    A(Ell((1.50, 0.0, 2.29), (0.20, 0.185, 0.18)), 0.08, True, 'forearm_S')                # forearm mass
    A(Ell((2.035, 0.04, 2.275), (0.155, 0.205, 0.078)), 0.05, True, 'hand_S')           # palm
    for fb, a, b, c, r0, r1, r2 in (('index', (2.14, -0.09, 2.28), (2.27, -0.108, 2.28), (2.405, -0.125, 2.272), 0.06, 0.052, 0.042),
                                    ('fingers', (2.15, 0.04, 2.28), (2.29, 0.046, 2.28), (2.43, 0.052, 2.272), 0.062, 0.054, 0.044),
                                    ('fingers', (2.14, 0.172, 2.28), (2.265, 0.195, 2.28), (2.39, 0.218, 2.272), 0.058, 0.05, 0.04),
                                    ('thumb', (1.99, -0.10, 2.255), (2.09, -0.17, 2.23), (2.185, -0.212, 2.213), 0.066, 0.056, 0.044)):
        A(Cone(a, b, r0, r1), 0.02, True, fb + '_01_S')
        A(Cone(b, c, r1, r2), 0.012, True, fb + '_02_S')
        A(Sph(b, r1 + 0.008), 0.012, True)                                    # knuckle
    # ---- legs (bowed) and feet
    A(Cone((0.27, 0.02, 1.08), (0.31, -0.02, 0.62), 0.275, 0.175), 0.10, True, 'thigh_S')
    A(Sph((0.31, -0.06, 0.61), 0.165), 0.06, True)                            # knee
    A(Cone((0.31, -0.01, 0.60), (0.27, 0.02, 0.19), 0.18, 0.128), 0.08, True, 'shin_S')
    A(Ell((0.31, 0.09, 0.45), (0.155, 0.145, 0.19)), 0.08, True, 'shin_S')              # calf
    A(Ell((0.27, -0.08, 0.08), (0.17, 0.265, 0.09)), 0.06, True, 'foot_S')              # foot
    A(Sph((0.27, 0.12, 0.09), 0.11), 0.06, True, 'foot_S')                              # heel
    for a, b, r0, r1 in (((0.15, -0.27, 0.065), (0.132, -0.43, 0.058), 0.07, 0.06), ((0.275, -0.29, 0.065), (0.275, -0.465, 0.058), 0.074, 0.062),
                         ((0.395, -0.26, 0.065), (0.42, -0.405, 0.058), 0.066, 0.056)):
        A(Cone(a, b, r0, r1), 0.03, True, 'toe_S')
    # ---- folds, sockets, mouth
    Cc(Cone((0.04, -0.455, 1.925), (0.50, -0.33, 1.965), 0.022), 0.04, True)          # crease under the pecs
    Cc(Cone((0.0, -0.50, 2.02), (0.0, -0.47, 2.22), 0.018), 0.035)                    # sternum groove
    Cc(Cone((-0.42, -0.46, 1.20), (0.42, -0.46, 1.20), 0.022), 0.05)                  # fold under the belly
    Cc(Cone((0.25, -0.50, 1.62), (0.52, -0.28, 1.70), 0.018), 0.04, True)             # side roll
    Cc(Sph((0, -0.60, 1.44), 0.04), 0.03)                                             # navel
    Cc(Sph((0.088, -0.522, 2.59), 0.037), 0.02, True)                                 # eye sockets
    Cc(Ell((0, -0.58, 2.492), (0.15, 0.13, 0.016)), 0.018)                            # mouth slit
    Cc(Sph((0.034, -0.655, 2.535), 0.02), 0.012, True)                                # nostrils
    Cc(Cone((1.03, -0.21, 2.26), (1.25, -0.16, 2.24), 0.018), 0.04, True)             # arm creases
    Cc(Cone((1.88, -0.13, 2.30), (1.90, 0.14, 2.30), 0.016), 0.03, True)              # wrist fold
    # ---- warts and lumps (not mirrored: asymmetric)
    rnd = random.Random(7)
    spots = [((0.55, 0.1, 2.45), (0.5, 0.3, 0.8)), ((-0.6, 0.1, 2.4), (-0.6, 0.2, 0.8)), ((0.2, 0.3, 2.6), (0.3, 0.7, 0.6)),
             ((-0.25, 0.3, 2.55), (-0.3, 0.8, 0.5)), ((0.9, 0.0, 2.3), (0.1, 0.5, 0.9)), ((-1.0, 0.0, 2.3), (-0.1, 0.4, 0.9)),
             ((1.5, 0.0, 2.28), (0.0, 0.6, 0.8)), ((-1.55, 0.0, 2.28), (0.1, -0.2, 1.0)), ((0, -0.3, 2.6), (0.5, -0.2, 0.9)),
             ((0, -0.3, 2.6), (-0.6, 0.1, 0.8)), ((0.3, 0.1, 2.0), (0.6, 0.8, 0.1)), ((-0.3, 0.1, 1.9), (-0.5, 0.85, 0.0)),
             ((0.0, 0.2, 2.4), (0.2, 1.0, 0.3)), ((0.0, 0.2, 2.3), (-0.35, 1.0, 0.1)), ((0.66, 0.03, 2.37), (0.7, -0.3, 0.7)),
             ((-0.66, 0.03, 2.37), (-0.8, 0.1, 0.6)), ((0.3, 0, 0.85), (0.9, -0.3, 0.2)), ((-0.3, 0, 0.8), (-0.9, 0.3, 0.1)),
             ((1.2, 0, 2.28), (0.2, -0.3, 0.95)), ((-1.75, 0, 2.28), (0.0, 0.5, 0.9)), ((0.0, -0.1, 1.5), (0.75, -0.6, 0.2)),
             ((0.0, -0.1, 1.45), (-0.8, -0.5, -0.1))]
    for o, d in spots:
        for _ in range(3):
            dd = (d[0] + rnd.uniform(-0.3, 0.3), d[1] + rnd.uniform(-0.25, 0.25), d[2] + rnd.uniform(-0.25, 0.25))
            p = f.surface_from(o, dd)
            if p is not None:
                A(Sph(p, rnd.uniform(0.035, 0.07)), 0.025)
    f.noise(0.24, 0.022, 3)
    f.noise(0.10, 0.011, 5)
    f.floor(0.0)
    return f


def body_mesh(f):
    t0 = time.time()
    V, Q = f.mesh()
    me = bpy.data.meshes.new('troll_body')
    me.from_pydata(V.tolist(), [], Q.tolist())
    me.update()
    ob = bpy.data.objects.new('troll_body', me)
    link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    seen, comps = set(), []
    for v0 in bm.verts:
        if v0 in seen:
            continue
        comp, stack = [], [v0]
        seen.add(v0)
        while stack:
            v = stack.pop()
            comp.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o not in seen:
                    seen.add(o)
                    stack.append(o)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    junk = [v for c in comps[1:] for v in c]
    if junk:
        print('TROLL: dropped %d floating islands (%d verts)' % (len(comps) - 1, len(junk)))
        bmesh.ops.delete(bm, geom=junk, context='VERTS')
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    n0 = tri_count(ob)
    for _ in range(2):
        cur = tri_count(ob)
        if cur <= BODY_TRIS:
            break
        mod = ob.modifiers.new('dec', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = BODY_TRIS / cur * 0.998
        apply_modifiers(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    print('TROLL body: surface nets %d tris -> %d tris (%.1fs)' % (n0, tri_count(ob), time.time() - t0))
    return ob


def skin_body(ob, f, arm, smooth_iters=7):
    """Skin weights from the sculpt itself: every vertex belongs to the bone of the primitive that forms the
    surface there (smallest signed distance), trunk primitives are blended by height down the spine, then the
    weights are relaxed over the mesh (soft joints), cut to 4 influences and normalised."""
    me = ob.data
    n = len(me.vertices)
    P = np.array([v.co[:] for v in me.vertices], np.float32)
    names = [b.name for b in arm.data.bones if b.use_deform]
    bi = {nm: i for i, nm in enumerate(names)}
    best = np.full(n, 1e9, np.float32)
    owner = np.zeros(n, np.int32)
    owners = []
    for prim, mirror, tag in f.tagged:
        for sx in ((1.0, -1.0) if mirror else (1.0,)):
            d = prim.dist(P[:, 0] * sx, P[:, 1], P[:, 2]).astype(np.float32)
            t = tag.replace('_S', '_L' if sx > 0 else '_R') if tag.endswith('_S') else tag
            owners.append(t)
            m = d < best
            best[m] = d[m]
            owner[m] = len(owners) - 1
    W = np.zeros((n, len(names)), np.float32)
    knots = [('hips', 1.22), ('spine_01', 1.47), ('spine_02', 1.76), ('spine_03', 2.06)]
    for i in range(n):
        t = owners[owner[i]]
        if t != 'TRUNK':
            W[i, bi[t]] = 1.0
            continue
        z = float(P[i, 2])
        if z <= knots[0][1]:
            W[i, bi['hips']] = 1.0
        elif z >= knots[-1][1]:
            W[i, bi['spine_03']] = 1.0
        else:
            for (n0, z0), (n1, z1) in zip(knots[:-1], knots[1:]):
                if z0 <= z <= z1:
                    u = (z - z0) / (z1 - z0)
                    W[i, bi[n0]] = 1 - u
                    W[i, bi[n1]] = u
    E = np.array([e.vertices[:] for e in me.edges], np.int32)
    deg = np.zeros(n, np.float32)
    np.add.at(deg, E[:, 0], 1.0)
    np.add.at(deg, E[:, 1], 1.0)
    deg = np.maximum(deg, 1.0)
    for _ in range(smooth_iters):
        acc = np.zeros_like(W)
        np.add.at(acc, E[:, 0], W[E[:, 1]])
        np.add.at(acc, E[:, 1], W[E[:, 0]])
        W = 0.45 * W + 0.55 * acc / deg[:, None]
    idx = np.argsort(-W, axis=1)[:, :4]
    for nm in names:
        if nm not in ob.vertex_groups:
            ob.vertex_groups.new(name=nm)
    for i in range(n):
        ws = W[i, idx[i]]
        tot = float(ws.sum()) or 1.0
        for j, w in zip(idx[i], ws):
            if w / tot > 0.01:
                ob.vertex_groups[names[int(j)]].add([i], float(w / tot), 'REPLACE')
    skin_to(ob, arm)


def paint_body(ob, f):
    me = ob.data
    n = len(me.vertices)
    P = np.array([v.co[:] for v in me.vertices], np.float32)
    N = np.array([v.normal[:] for v in me.vertices], np.float32)
    ao1 = np.clip(f.sample(P + N * 0.05) / 0.05, 0, 1)
    ao2 = np.clip(f.sample(P + N * 0.14) / 0.14, 0, 1)
    ao = 0.58 + 0.42 * (ao1 ** 0.8) * (0.4 + 0.6 * ao2)
    cols = []
    for i in range(n):
        p, nn = Vector(P[i]), Vector(N[i])
        c = mix(HIDE_DK, HIDE, 0.25 + 0.75 * fbm(p, 2.2, 1, 3))
        # pale belly / chest / throat / inner limbs (front-facing, low on the trunk)
        fr = sstep(0.1, 0.8, -nn.y) * sstep(0.62, 0.2, abs(p.x)) * sstep(0.95, 1.2, p.z) * sstep(2.35, 2.0, p.z)
        c = mix(c, HIDE_BELLY, 0.8 * fr)
        # dark weathered back and top
        bk = sstep(0.0, 0.7, nn.y) * sstep(1.2, 1.7, p.z)
        c = mix(c, HIDE_DK, 0.7 * bk)
        # moss on the hump, shoulders and the top of the arms
        ms = sstep(0.25, 0.85, nn.z) * sstep(1.9, 2.3, p.z) * sstep(0.42, 0.62, fbm(p, 3.5, 9, 3))
        c = mix(c, mix(MOSS, mul(MOSS, 1.4), vnoise(p, 14.0, 4)), 0.85 * ms)
        # pinkish worn skin: knuckles, palms, face
        pk = max(sstep(1.95, 2.2, abs(p.x)) * 0.5, sstep(0.25, 0.1, (p - Vector((0, -0.5, 2.5))).length) * 0.45)
        c = mix(c, HIDE_PINK, pk)
        # mud up the legs
        c = mix(c, MUD, 0.75 * sstep(0.55, 0.05, p.z) * (0.6 + 0.4 * vnoise(p, 8.0, 2)))
        c = mul(c, (0.8 + 0.4 * vnoise(p, 22.0, 6)) * float(ao[i]))
        cols.append(c)
    set_vertex_colors(ob, lambda p, nrm, i: cols[i])
    assign_mat(ob, preview_mat('M_hide'))
    box_uv(ob, 0.5)
    if ob.data.uv_layers:
        ob.data.uv_layers[0].name = 'UVMap'


def extras(f, body=None):
    """Tusks, nails, eyes (rigid) and the fur loincloth."""
    mb = MB()
    # eyes
    mb.bone = 'head'
    for sx in (1, -1):
        mb.sphere((sx * 0.088, -0.512, 2.59), 0.024, 'M_eye_glow', EYE, segs=6, rings=4)
    # tusks from the lower jaw (the right one is broken)
    for sx, ln in ((1, 1.0), (-1, 0.55)):
        base = Vector((sx * 0.118, -0.575, 2.46))
        mid = base + Vector((sx * 0.026, -0.04, 0.06 * ln))
        tip = base + Vector((sx * 0.036, -0.045, 0.135 * ln))
        cols = [TUSK_DK, mix(TUSK_DK, TUSK, 0.7), TUSK]
        if ln > 0.9:
            mb.tube([base, mid, base.lerp(tip, 0.82) + Vector((0, -0.012, 0))], [0.036, 0.027, 0.014], 6, 'M_bone', cols, up=(0, 1, 0), cap0=None,
                    cap1=None, sharp=60.0)
            k = len(mb.P)
            ring = list(range(k - 6, k))
            a = mb.add(tip, TUSK)
            for j in range(6):
                mb.face((ring[j], ring[(j + 1) % 6], a), 'M_bone', None, 60.0)
        else:
            mb.tube([base, mid, tip], [0.036, 0.03, 0.022], 6, 'M_bone', cols, up=(0, 1, 0), cap0=None, cap1='fan', sharp=60.0)
    # upper fangs
    for sx in (1, -1):
        mb.spike((sx * 0.055, -0.635, 2.505), (sx * 0.057, -0.65, 2.455), 0.015, 'M_bone', TUSK, segs=4, tipcol=TUSK)
    # finger nails / claws
    for S, sx in (('L', 1.0), ('R', -1.0)):
        for bone, tip in (('index_02_', (2.405, -0.125, 2.272)), ('fingers_02_', (2.43, 0.052, 2.272)), ('fingers_02_', (2.39, 0.218, 2.272)),
                          ('thumb_02_', (2.185, -0.212, 2.213))):
            mb.bone = bone + S
            t = Vector((sx * tip[0], tip[1], tip[2]))
            d = Vector((sx * 1.0, (-0.45 if bone.startswith('thumb') else (0.12 if tip[1] > 0.1 else -0.1)), -0.05)).normalized()
            mb.spike(t + Vector((0, 0, 0.018)) - d * 0.02, t + d * 0.085 + Vector((0, 0, -0.012)), 0.03, 'M_bone', TUSK_DK, segs=5, tipcol=TUSK,
                     up=(0, 0, 1))
        mb.bone = 'toe_' + S
        for tx, ty in ((0.132, -0.43), (0.275, -0.465), (0.42, -0.405)):
            t = Vector((sx * tx, ty, 0.075))
            mb.spike(t + Vector((0, 0.03, 0.02)), t + Vector((sx * (tx - 0.275) * 0.12, -0.085, -0.045)), 0.04, 'M_bone', TUSK_DK, segs=5, tipcol=TUSK)
    # fur loincloth: a belt under the belly, long ragged flaps front and back, short skirt on the sides
    rnd = random.Random(11)
    ncol = 18
    cols_pts, wts = [], []
    for k in range(ncol):
        a = 2 * math.pi * k / ncol
        d = Vector((math.sin(a), -math.cos(a), 0.0))                      # a = 0 -> front
        front, back = max(0.0, -d.y), max(0.0, d.y)
        zb = 1.33 - 0.11 * front ** 2 + 0.05 * back
        zend = 0.98 - 0.36 * front ** 3 - 0.30 * back ** 3 + rnd.uniform(-0.05, 0.05)
        col = []
        rb = f.radius((0, 0, zb), d) + 0.05
        for j, t in enumerate((0.0, 0.14, 0.5, 1.0)):
            z = zb + (zend - zb) * t + (0.035 if j == 0 else 0.0)
            r = max(rb + 0.02 * j, f.radius((0, 0, z), d) + 0.05 + 0.018 * j) if j > 0 else rb - 0.012
            if j == 3:
                r += rnd.uniform(-0.02, 0.03)
            col.append(Vector((d.x * r, d.y * r, z)))
        cols_pts.append(col)
    cols_pts.append(cols_pts[0])

    kd = None
    if body is not None:
        from mathutils import kdtree
        kd = kdtree.KDTree(len(body.data.vertices))
        for v in body.data.vertices:
            kd.insert(v.co, v.index)
        kd.balance()
        gname = {g.index: g.name for g in body.vertex_groups}

    def fur_w(p):
        if kd is not None:
            # follow the skin underneath (3 nearest body vertices), anchored to the pelvis
            w = {'hips': 0.3}
            near = kd.find_n(p, 3)
            for co, idx, dist in near:
                for g in body.data.vertices[idx].groups:
                    w[gname[g.group]] = w.get(gname[g.group], 0.0) + g.weight * 0.7 / len(near)
            top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
            return dict(top)
        if p.z > 1.2:
            return {'hips': 0.75, 'spine_01': 0.25}
        k = sstep(1.2, 0.85, p.z) * 0.6
        if p.x > 0.14:
            return {'hips': 1 - k, 'thigh_L': k}
        if p.x < -0.14:
            return {'hips': 1 - k, 'thigh_R': k}
        return {'hips': 1 - k * 0.7, 'thigh_L': k * 0.35, 'thigh_R': k * 0.35}

    def fur_c(p, sidek, j):
        c = mix(FUR_DK, FUR, vnoise(p, 9.0, 3))
        c = mix(c, FUR_TIP, (0.15, 0.1, 0.35, 0.8)[j] * (0.5 + 0.5 * vnoise(p, 20.0, 8)))
        if j == 0:
            c = mul(FUR_DK, 0.9)
        return mul(c, 0.6) if sidek else c

    mb.keep = True
    mb.fn_w = fur_w
    for sidek in (0, 1):
        ids = [[mb.add(p, fur_c(p, sidek, j)) for j, p in enumerate(col)] for col in cols_pts]
        for i in range(ncol):
            for j in range(3):
                q = (ids[i][j], ids[i][j + 1], ids[i + 1][j + 1], ids[i + 1][j])
                if j == 2 and i % 3 == 2:
                    q = (ids[i][j], ids[i][j + 1], ids[i + 1][j])              # torn notch between tatters
                mb.face(q if sidek == 0 else q[::-1], 'M_fur', None, 60.0)
    mb.fn_w = None
    mb.keep = False
    mb.bone = None
    return mb.build('troll_extras', all_preview_mats())


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    reset_scene()
    warp = brute_warp(1.0)
    arm = build_humanoid_armature('Armature', warp=warp)
    t0 = time.time()
    f = sculpt()
    print('TROLL sculpt field %s in %.1fs' % (tuple(f.n), time.time() - t0))
    body = body_mesh(f)
    paint_body(body, f)
    if '--sculpt' in argv:
        ex = extras(f)
        render_rest('troll', [body, ex])
        render_closeups('troll', [body, ex], [((-0.5, -0.8, 2.15), (0.5, 0.2, 3.0), (-0.2, 0.97, -0.05)), ((-0.5, -0.8, 2.15), (0.5, 0.2, 3.0), (-0.85, 0.5, -0.05)),
                                               ((-0.9, -0.7, 1.0), (0.9, 0.6, 2.5), (0, 1, 0)), ((1.7, -0.4, 1.95), (2.5, 0.4, 2.6), (0.2, 0.5, -0.85)),
                                               ((-0.7, -0.6, 0.0), (0.7, 0.5, 1.3), (-0.5, 0.8, -0.2))])
        return
    skin_body(body, f, arm)
    ex = extras(f, body)
    skin_to(ex, arm)
    ob = join([body, ex], 'troll')
    while len([m for m in ob.modifiers if m.type == 'ARMATURE']) > 1:
        ob.modifiers.remove([m for m in ob.modifiers if m.type == 'ARMATURE'][-1])
    clips = None
    try:
        clips = Clips()
    except Exception as e:
        print('NO CLIPS', e)
    export_monster('troll', arm, ob, clips, max_tris=9000,
                   extra=dict(description='mountain troll: warty hide, pot belly, tusks, ragged fur loincloth',
                              warp='brute_warp(S=1.0) in tools/blender/mon_lib.py', handScale=2.7))
    if '--nopreview' in argv:
        return
    render_rest('troll', [ob])
    render_closeups('troll', [ob], [((-0.5, -0.8, 2.15), (0.5, 0.2, 3.0), (-0.2, 0.97, -0.05)), ((-0.5, -0.8, 2.15), (0.5, 0.2, 3.0), (-0.85, 0.5, -0.05)),
                                     ((-0.9, -0.7, 1.0), (0.9, 0.6, 2.5), (0, 1, 0)), ((1.7, -0.4, 1.95), (2.5, 0.4, 2.6), (0.2, 0.5, -0.85)),
                                     ((-0.7, -0.6, 0.0), (0.7, 0.5, 1.3), (-0.5, 0.8, -0.2))])
    if clips:
        ratio = arm.data.bones['hips'].head_local.z / HUMAN_HIPS
        shots = [('m_idle', 0.5), ('m_walk', 0.25), ('m_swipe_R', None), ('m_smash', None), ('m_stomp', None), ('m_roar', 0.8),
                 ('hit_heavy', 0.2), ('death', -0.02)]
        render_poses('troll', arm, [ob], clips, shots, ratio, res=336)
        if '--inspect' in argv:
            render_poses('troll', arm, [ob], clips, [('idle', 0.5), ('kneel', 0.5), ('atk2h_heavy', 0.4), ('m_swipe_L', None), ('m_smash', 0.3)], ratio,
                         res=448, views=((-0.5, 0.82, -0.18), (0.6, -0.7, -0.3)), suffix='inspect')


if __name__ == '__main__':
    main()
