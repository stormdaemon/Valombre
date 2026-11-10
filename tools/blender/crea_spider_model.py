"""VALOMBRE giant forest spider: skeleton + procedural model (module used by crea_spider.py).

Hard-surface arthropod: every segment is a clean lofted tube (no remesh), skinned analytically:
cephalothorax rigid on `body`, abdomen on `abdomen`, legs = 3 bones each with short blends at the joints."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crea_common import *

NAME = 'spider'
CEPH = V((0, -0.14, 0.56))                  # cephalothorax centre = pivot of the `body` bone
COXA_Z = 0.50
# leg name, coxa (x, y), azimuth of the leg plane (deg from straight ahead), length scale, knee height
LEGDEF = [
    ('leg1', (0.100, -0.300), 24.0, 1.10, 1.04),
    ('leg2', (0.165, -0.200), 62.0, 1.00, 1.00),
    ('leg3', (0.170, -0.080), 108.0, 0.93, 0.96),
    ('leg4', (0.140, 0.000), 140.0, 1.08, 1.02),
]
LEGKEYS = [s + str(i) for i in (1, 2, 3, 4) for s in ('L', 'R')]


def leg_joints(i, sx):
    """Rest joints (coxa, knee, tibia-tarsus joint, foot) of leg i (0..3) on side sx, plus plane axes."""
    name, (cx, cy), az, sc, kz = LEGDEF[i]
    f = V((math.sin(rad(az)) * sx, -math.cos(rad(az)), 0.0))          # horizontal outward direction
    C = V((cx * sx, cy, COXA_Z))
    K = C + f * (0.42 * sc) + ZA * (kz - COXA_Z)
    J = C + f * (0.86 * sc) + ZA * 0.12
    F = C + f * (1.00 * sc) - ZA * COXA_Z
    n = ZA.cross(f)
    return C, K, J, F, f, n


JT = dict(
    body=CEPH, body_t=V((0, -0.40, 0.56)),
    abd=V((0, 0.07, 0.585)), abd_t=V((0, 0.80, 0.64)),
    head=V((0, -0.30, 0.60)), head_t=V((0, -0.42, 0.60)),
    mouth=V((0, -0.47, 0.43)), mouth_t=V((0, -0.60, 0.43)),
    chel=V((0.062, -0.375, 0.530)), chel_t=V((0.062, -0.445, 0.365)), fang_t=V((0.020, -0.405, 0.235)),
    palp=V((0.120, -0.350, 0.500)), palp_m=V((0.190, -0.500, 0.550)), palp_t=V((0.160, -0.600, 0.360)),
)


# ----------------------------------------------------------------------------- rig
def build_rig():
    r = Rig()
    r.bone('root', (0, 0, 0), (0, 0, 0.2), None, zref=(0, -1, 0), deform=False)
    r.bone('body', JT['body'], JT['body_t'], 'root')
    r.bone('abdomen', JT['abd'], JT['abd_t'], 'body')
    r.bone('head', JT['head'], JT['head_t'], 'body')
    r.bone('mouth', JT['mouth'], JT['mouth_t'], 'head', deform=False)
    r.mirror('chel', JT['chel'], JT['chel_t'], 'head')
    r.mirror('fang', JT['chel_t'], JT['fang_t'], 'chel_S', zref=(0, -1, 0))
    r.mirror('palp1', JT['palp'], JT['palp_m'], 'head', zref=(0, 0, 1))
    r.mirror('palp2', JT['palp_m'], JT['palp_t'], 'palp1_S', zref=(0, 0, 1))
    for i in range(4):
        nm = LEGDEF[i][0]
        for sx, sfx in ((1, '_L'), (-1, '_R')):
            C, K, J, F, f, n = leg_joints(i, sx)
            r.bone(nm + 'a' + sfx, C, K, 'body', zref=tuple(n.cross((K - C).normalized())))
            r.bone(nm + 'b' + sfx, K, J, nm + 'a' + sfx, zref=tuple(n.cross((J - K).normalized())))
            r.bone(nm + 'c' + sfx, J, F, nm + 'b' + sfx, zref=tuple(n.cross((F - J).normalized())))
    return r


# ----------------------------------------------------------------------------- colours (LINEAR multipliers)
def chit(v, warm=0.5):
    v = min(1.0, v * 1.22)
    return (v, v * (1 - 0.07 * warm), v * (1 - 0.16 * warm))


def c_ceph(p, u, th):
    s = math.sin(th)
    v = lerp(0.72, 0.58, ramp(abs(p.x), 0.03, 0.16))                       # paler median band
    v = lerp(v, 0.80, ramp(-s, 0.2, 0.9) * 0.6)                            # paler sternum
    v *= 1.0 - 0.22 * bump(math.atan2(p.x, p.y + 0.10) * 3.0 % 1.0, 0.0, 0.5) * ramp(s, 0.0, 0.6) * ramp(abs(p.x), 0.05, 0.12)  # radial grooves
    v = lerp(v, 0.50, ramp(-p.y, 0.30, 0.38) * ramp(s, -0.2, 0.3))         # dark face around the eyes
    return chit(clamp(v * (1 + 0.05 * vnoise(p, 14, 1.0)), 0.46, 1.0))


def c_abd(p, u, th):
    s = math.sin(th)
    v = lerp(0.72, 0.50, ramp(s, -0.6, 0.1))
    v *= 1.0 + 0.08 * vnoise(p, 13, 2.0)
    v = lerp(v, 0.46, ramp(p.y, 0.64, 0.80) * 0.8)                         # darker rear
    if s > 0.0:
        v = min(1.0, v * 1.22)                                                            # pale dorsal folium: chain of diamonds
        ang = abs(math.degrees(th) % 360.0 - 90.0)                         # degrees away from the dorsal line
        lobe = max(0.0, math.sin(PI_ * (p.y - 0.155) / 0.19)) if 0.155 < p.y < 0.725 else 0.0
        width = (9.0 + 30.0 * lobe ** 0.8) * ramp(p.y, 0.12, 0.20) * ramp(-p.y, -0.74, -0.66)
        m = ramp(-ang, -width - 5.0, -width + 3.0)
        edge = ramp(-ang, -width - 22.0, -width - 6.0) * (1 - m)
        v = lerp(v * (1 - 0.14 * edge), 1.0, m)
        return (v, v * (1 - 0.035 * (1 + m)), v * (1 - 0.09 * (1 + 1.3 * m)))
    return chit(clamp(v, 0.46, 1.0))


PI_ = math.pi

# ----------------------------------------------------------------------------- model
def ray_surface(bvh, target, direction, dist=0.6):
    """point + normal of the surface seen from outside along -direction toward target."""
    d = V(direction).normalized()
    hit = bvh.ray_cast(V(target) + d * dist, -d)
    return hit[0], hit[1]


def build_model(rig, arm):
    B = Builder(rig.names)
    mats = [make_mat('M_chitin', (0.24, 0.21, 0.18), 0.7, use_vertex_color=True),
            make_mat('M_bone', (0.9, 0.9, 0.9), 0.4, use_vertex_color=True),
            make_mat('M_eye_glow', (1, 1, 1), 0.15, emissive=(1.0, 0.15, 0.05), emissive_strength=1.2, use_vertex_color=True)]

    # ---- cephalothorax (rear -> front), (y, zc, rx, ry_top, ry_bot, taper)
    cs = [(0.085, 0.565, 0.085, 0.055, 0.050, 0.0), (0.020, 0.565, 0.170, 0.100, 0.080, 0.1), (-0.080, 0.565, 0.218, 0.128, 0.098, 0.15),
          (-0.180, 0.565, 0.212, 0.132, 0.102, 0.15), (-0.270, 0.570, 0.178, 0.126, 0.098, 0.1), (-0.335, 0.575, 0.146, 0.116, 0.090, 0.05),
          (-0.385, 0.575, 0.118, 0.092, 0.076, 0.0)]
    ceph = loft([S((0, y, zc), rx, (rt, rb), 2.3, tap) for y, zc, rx, rt, rb, tap in cs], n=16, sub=2, caps=(0.7, 0.9))
    B.add(ceph, 'body', c_ceph, group='body', name='ceph')

    # ---- abdomen (rear tip -> pedicel)
    ab = [(0.830, 0.570, 0.050, 0.050, 0.050), (0.770, 0.610, 0.170, 0.160, 0.135), (0.650, 0.655, 0.268, 0.250, 0.205),
          (0.510, 0.680, 0.312, 0.275, 0.235), (0.370, 0.680, 0.298, 0.262, 0.232), (0.230, 0.660, 0.225, 0.205, 0.195),
          (0.125, 0.625, 0.135, 0.125, 0.125), (0.065, 0.595, 0.065, 0.058, 0.058)]

    def w_abd(p, u, th):
        t = ramp(p.y, 0.05, 0.14)
        return {'abdomen': t, 'body': 1 - t}
    abd = loft([S((0, y, zc), rx, (rt, rb), 2.1, 0.12) for y, zc, rx, rt, rb in ab], n=24, sub=3, caps=(0.8, 0.5))
    B.add(abd, w_abd, c_abd, group='body', name='abdomen')
    # spinnerets
    for sx in (1, -1):
        B.add(cone((0.030 * sx, 0.815, 0.545), (0.040 * sx, 0.885, 0.500), 0.026, n=5, segs=2), 'abdomen', chit(0.5), group='body', name='spin')

    # ---- legs
    def leg_parts(i, sx, sfx):
        nm = LEGDEF[i][0]
        C, K, J, F, f, n = leg_joints(i, sx)
        a, b, c = nm + 'a' + sfx, nm + 'b' + sfx, nm + 'c' + sfx
        d1, d2, d3 = (K - C).normalized(), (J - K).normalized(), (F - J).normalized()
        k = 1.06 if i in (0, 3) else 1.0
        secs = [
            (C - d1 * 0.07, 0.050, {'body': 1}), (C + d1 * 0.04, 0.054, {a: 1}), (C + d1 * 0.13, 0.041, {a: 1}),
            (C.lerp(K, 0.42), 0.048, {a: 1}), (K - d1 * 0.09, 0.037, {a: 1}), (K - d1 * 0.022, 0.043, {a: 0.75, b: 0.25}),
            (K + d2 * 0.030, 0.042, {a: 0.25, b: 0.75}), (K + d2 * 0.085, 0.033, {b: 1}), (K.lerp(J, 0.5), 0.035, {b: 1}),
            (J - d2 * 0.07, 0.027, {b: 1}), (J - d2 * 0.016, 0.031, {b: 0.75, c: 0.25}), (J + d3 * 0.028, 0.030, {b: 0.25, c: 0.75}),
            (J + d3 * 0.085, 0.022, {c: 1}), (J.lerp(F, 0.5), 0.020, {c: 1}), (J.lerp(F, 0.86), 0.012, {c: 1}), (F + ZA * 0.004, 0.004, {c: 1}),
        ]
        shade = [0.50, 0.48, 0.56, 0.92, 0.60, 0.45, 0.45, 0.58, 0.95, 0.60, 0.45, 0.45, 0.62, 0.85, 0.55, 0.42]

        def wfn(p, u, th, secs=secs):
            return secs[int(round(u))][2]

        def cfn(p, u, th):
            v = shade[int(round(u))] * (0.92 + 0.16 * (math.sin(th) > 0))        # paler on top
            return chit(v, 0.8)
        B.add(loft([S(cn, r * k, r * k) for cn, r, _ in secs], n=8, sub=1, caps=(None, 0.0), side=tuple(n)), wfn, cfn, group='body', name=nm)
        # bristles / spikes: dorsal side of each segment (+ lateral ones on the tibia)
        up1, up2, up3 = n.cross(d1) * -1, n.cross(d2) * -1, n.cross(d3) * -1
        if up1.z < 0:
            up1, up2, up3 = -up1, -up2, -up3
        dark = chit(0.44, 0.3)
        for t, L in ((0.30, 0.085), (0.55, 0.095), (0.80, 0.075)):
            P = C.lerp(K, t)
            B.add(cone(P + up1 * 0.030, P + up1 * (0.030 + L * 0.85) + d1 * (L * 0.55), 0.013, n=3), a, dark, group='body', name='spk')
        B.add(cone(K + (up1 + up2).normalized() * 0.025, K + (up1 + up2).normalized() * 0.12, 0.016, n=4), {a: 0.5, b: 0.5}, dark, group='body', name='spk')
        for t, L in ((0.30, 0.080), (0.62, 0.070)):
            P = K.lerp(J, t)
            B.add(cone(P + up2 * 0.022, P + up2 * (0.022 + L * 0.85) + d2 * (L * 0.55), 0.011, n=3), b, dark, group='body', name='spk')
            for sg in (1, -1):
                B.add(cone(P + n * (0.022 * sg), P + n * ((0.022 + L * 0.7) * sg) + d2 * (L * 0.6), 0.009, n=3), b, dark, group='body', name='spk')
        P = J.lerp(F, 0.30)
        B.add(cone(P + up3 * 0.014, P + up3 * 0.06 + d3 * 0.05, 0.008, n=3), c, dark, group='body', name='spk')
        # two little claws at the tip
        for sg in (1, -1):
            B.add(cone(F + ZA * 0.030 + n * (0.006 * sg), F + f * 0.035 + n * (0.016 * sg) + ZA * 0.002, 0.007, n=3), c, (0.10, 0.08, 0.07),
                  group='hard', name='claw')

    for i in range(4):
        for sx, sfx in ((1, '_L'), (-1, '_R')):
            leg_parts(i, sx, sfx)

    # ---- chelicerae, fangs, pedipalps
    for sx, sfx in ((1, '_L'), (-1, '_R')):
        c0, c1, ft = [V((p.x * sx, p.y, p.z)) for p in (JT['chel'], JT['chel_t'], JT['fang_t'])]
        d = (c1 - c0).normalized()
        secs = [S(c0 - d * 0.05, 0.050, 0.052), S(c0 + d * 0.03, 0.058, 0.062), S(c0.lerp(c1, 0.6), 0.054, 0.060), S(c1 - d * 0.01, 0.040, 0.046), S(c1 + d * 0.02, 0.022, 0.026)]
        B.add(loft(secs, n=8, sub=1, caps=(None, 0.5)), 'chel' + sfx,
              lambda p, u, th: chit(lerp(0.50, 0.66, clamp(u / 4.0)) * (1 + 0.06 * vnoise(p, 20, 5.0)), 0.9), group='body', name='chel')
        # bristles on the chelicera front
        for t in (0.35, 0.7):
            P = c0.lerp(c1, t)
            B.add(cone(P + V((0, -0.05, 0)), P + V((0.012 * sx, -0.105, -0.03)), 0.009, n=3), 'chel' + sfx, chit(0.44, 0.3), group='body', name='spk')
        B.add(cone(c1 - d * 0.015, ft, 0.021, n=5, segs=3, curve=(-0.22 * sx, -0.55, 0.0), capped=True), 'fang' + sfx,
              lambda p, u, th, c1=c1, ft=ft: lerp(np.array((0.42, 0.16, 0.08)), np.array((0.05, 0.03, 0.03)), clamp((p - c1).length / (ft - c1).length * 1.2)),
              group='hard', name='fang')
        p0, p1, p2 = [V((p.x * sx, p.y, p.z)) for p in (JT['palp'], JT['palp_m'], JT['palp_t'])]
        e1, e2 = (p1 - p0).normalized(), (p2 - p1).normalized()
        pa, pb = 'palp1' + sfx, 'palp2' + sfx
        ps = [(p0 - e1 * 0.05, 0.030, {'head': 1}), (p0 + e1 * 0.03, 0.032, {pa: 1}), (p0.lerp(p1, 0.55), 0.028, {pa: 1}), (p1 - e1 * 0.02, 0.027, {pa: 0.7, pb: 0.3}),
              (p1 + e2 * 0.025, 0.027, {pa: 0.3, pb: 0.7}), (p1.lerp(p2, 0.5), 0.022, {pb: 1}), (p1.lerp(p2, 0.82), 0.026, {pb: 1}), (p2, 0.008, {pb: 1})]
        pshade = [0.52, 0.56, 0.74, 0.48, 0.48, 0.70, 0.56, 0.44]
        B.add(loft([S(cn, r, r) for cn, r, _ in ps], n=6, sub=1, caps=(None, 0.0), side=(0, 0, 1)),
              lambda p, u, th, ps=ps: ps[int(round(u))][2], lambda p, u, th: chit(pshade[int(round(u))], 0.8), group='body', name='palp')

    # ---- abdomen + carapace spikes
    def abd_point(y, ang):
        ys = [s[0] for s in ab][::-1]
        vals = [np.interp(y, ys, [s[k] for s in ab][::-1]) for k in (1, 2, 3, 4)]
        zc, rx, rt, rb = vals
        cs_, sn = math.cos(rad(ang)), math.sin(rad(ang))
        p = V((rx * cs_, y, zc + (rt if sn > 0 else rb) * sn))
        nrm = V((cs_ / max(rx, 1e-3), 0, sn / max(rt, 1e-3))).normalized()
        return p, nrm
    dark = chit(0.44, 0.3)
    rnd = random.Random(7)
    for y in (0.20, 0.30, 0.41, 0.52, 0.63, 0.73):
        for ang in (90, 58, 122, 26, 154, -8, 188):
            if ang == 90 and y < 0.60:
                continue                                      # keep the pale mark readable
            yy = y + rnd.uniform(-0.02, 0.02) + (0.05 if ang in (58, 122, -8, 188) else 0.0)
            if yy > 0.78:
                continue
            p, nrm = abd_point(yy, ang + rnd.uniform(-5, 5))
            L = rnd.uniform(0.055, 0.095) * (1.25 if y > 0.6 else 1.0)
            B.add(cone(p - nrm * 0.012, p + nrm * L * 0.8 + V((0, L * 0.75, 0)), 0.015, n=4), 'abdomen', dark, group='body', name='spk')
    for sx in (1, -1):
        for (x, y, z, L) in ((0.20, -0.06, 0.62, 0.07), (0.185, -0.20, 0.64, 0.07), (0.12, 0.02, 0.64, 0.06)):
            B.add(cone((x * sx, y, z), (x * sx * 1.25, y + 0.03, z + L), 0.014, n=4), 'body', dark, group='body', name='spk')

    body, W, C = B.object('body', 'spider_body')
    body.data.materials.append(mats[0])
    pieces = [(body, W, C)]
    hard, Wh, Ch = B.object('hard', 'spider_hard')
    hard.data.materials.append(mats[1])
    pieces.append((hard, Wh, Ch))

    # ---- eyes on the carapace surface (2 big front median, 2 front lateral, 2 rear median, 2 rear lateral)
    co = ceph[0]
    cob = mesh_obj('tmp_ceph', co, ceph[1])
    bvh = BVHTree.FromObject(cob, bpy.context.evaluated_depsgraph_get())
    D = Builder(rig.names)
    for sx in (1, -1):
        for (tx, ty, tz, dirv, r) in ((0.045, -0.36, 0.615, (0.25, -1.0, 0.45), 0.036), (0.105, -0.33, 0.610, (0.75, -0.8, 0.40), 0.024),
                                      (0.050, -0.30, 0.640, (0.25, -0.55, 1.0), 0.026), (0.115, -0.27, 0.630, (0.85, -0.35, 0.8), 0.021)):
            pos, nrm = ray_surface(bvh, (tx * sx, ty, tz), (dirv[0] * sx, dirv[1], dirv[2]))
            if pos is None:
                continue
            D.add(dome(pos - nrm * (r * 0.35), nrm, r, n=7, rings=1, flat=0.85), 'body',
                  lambda p, u, th: (1.0, 0.55, 0.40) if u >= 2 else (0.75, 0.08, 0.05), group='eye', name='eye')
    bpy.data.objects.remove(cob)
    eyes, Wy, Cy = D.object('eye', 'spider_eyes')
    eyes.data.materials.append(mats[2])
    pieces.append((eyes, Wy, Cy))

    objs = [p[0] for p in pieces]
    aos = bake_ao(objs, rays=20, dist=0.30)
    for (ob, Wp, Cp), ao in zip(pieces, aos):
        if ob.name != 'spider_eyes':
            Cp = Cp * lerp(0.72, 1.0, ao)[:, None]
        write_colors(ob, Cp)
        write_weights(ob, Wp, rig.names, arm)
    mesh = join(objs, NAME)
    activate_colors(mesh)
    box_uv(mesh, 0.5)
    for pl in mesh.data.polygons:
        pl.use_smooth = True
    return mesh
