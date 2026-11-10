"""VALOMBRE world pack - citadel hero pieces 2: great keep, royal throne, knight statues (uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *
from world_castle2 import sun_emblem, crack, BLUE

PBW = dict(ao_dist=0.9, ao_min=0.34, dirt_h=0.4, dirt=0.3)


# ----------------------------------------------------------------------------- great keep
def lancet_ops(ss, z0=8.0, hs=10.9, ha=11.9, w=1.0):
    return [Op(s, w, z0, hs, ha, n=2) for s in ss]


def turret_top(k, x0, y0, x1, y1, z, h=0.75, missing=()):
    """corner + mid merlons on a square turret"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    m = 0.8
    spots = [(x0, y0, x0 + m, y0 + m), (x1 - m, y0, x1, y0 + m), (x1 - m, y1 - m, x1, y1), (x0, y1 - m, x0 + m, y1),
             (cx - 0.4, y0, cx + 0.4, y0 + 0.5), (x1 - 0.5, cy - 0.4, x1, cy + 0.4), (cx - 0.4, y1 - 0.5, cx + 0.4, y1),
             (x0, cy - 0.4, x0 + 0.5, cy + 0.4)]
    for i, (a, b, c, d) in enumerate(spots):
        if i in missing:
            continue
        k.box((a, b, z), (c, d, z + h * (1.0 if i < 4 else 0.8)), SB, k.jit(ST, 0.04, 0.0), skip=('-z',))


@asset('castle_keep', 'Ruined great keep of Aubeclair, 16 x 14 m, walls 14 m (parapet 15.7 m), square corner turrets '
       'up to 18 m; the front-right corner and its turret have collapsed into a rubble mound, hollow shell with tall '
       'empty lancet windows, big pointed doorway (front, -Y) sealed with rubble', 6000, footprint=[20.0, 17.0],
       bake=dict(ao_dist=3.0, ao_min=0.26, dirt_h=1.2, dirt=0.35, samples=12), res=512)
def castle_keep(k):
    ZT, TH = 14.0, 1.8
    zc = [0.0, 0.9, 2.5, 5.0, 8.0, 11.0]
    bat = (0.45, 2.5)
    kw = dict(zc=zc, ds=2.6, batter=bat, ends=(False, False))
    # ---- front wall (-Y): door + two lancets, broken down towards the collapsed corner (+X)
    door = Op(5.3, 3.0, 0.9, 3.9, 5.7, n=4)
    f_zt = [(0, ZT), (6.0, ZT), (6.0, 12.7), (6.7, 13.0), (6.7, 11.3), (7.6, 10.7), (7.6, 9.2), (8.4, 8.6), (8.4, 7.1),
            (9.3, 6.6), (9.3, 5.4), (10.6, 4.6)]
    wf = masonry(k, (-5.3, -6), (5.3, -6), -0.9, f_zt, TH, ops=[door] + lancet_ops((2.9, 7.7)),
                 top_core=lambda s: s > 6.0, **kw)
    # ---- right wall (+X): rises from the collapsed corner to full height
    r_zt = [(0, 4.4), (0.9, 5.2), (0.9, 6.5), (1.8, 7.0), (1.8, 8.6), (2.7, 9.2), (2.7, 10.9), (3.6, 11.5), (3.6, 13.1),
            (4.5, ZT), (8.6, ZT)]
    wr = masonry(k, (7, -4.3), (7, 4.3), -0.9, r_zt, TH, ops=lancet_ops((2.75, 6.1)), top_core=lambda s: s < 4.5, **kw)
    # ---- back (+Y) and left (-X) walls: intact
    wb = masonry(k, (5.3, 6), (-5.3, 6), -0.9, ZT, TH, ops=lancet_ops((2.3, 5.3, 8.3)), top_core=False, **kw)
    wl = masonry(k, (-7, 4.3), (-7, -4.3), -0.9, ZT, TH, ops=lancet_ops((2.5, 6.1)), top_core=False, **kw)
    for w_, ops in ((wf, lancet_ops((2.9,))), (wr, lancet_ops((6.1,))), (wb, lancet_ops((2.3, 5.3, 8.3))),
                    (wl, lancet_ops((2.5, 6.1)))):
        for o in ops:
            archivolt(k, w_, o, band=0.16, proud=0.05, sill=0.12)
    # ---- parapets on the intact stretches
    def par(a, b, ln, crs, zt=None, **kq):
        ops = [Op(c, 0.8, ZT + 0.9, ZT + 0.9, None) for c in crs]
        masonry(k, a, b, ZT, zt or (ZT + 1.7), 0.5, ops=ops, zc=[], ds=9, ends=(False, False),
                top_core=None if zt else False, **kq)
    par((-5, -6), (1.0, -6), 6.0, (1.0, 3.0), zt=[(0, ZT + 1.7), (5.0, ZT + 1.7), (5.0, ZT + 0.9), (5.6, ZT + 0.4),
                                                   (6.0, ZT + 0.1)])
    par((7, 0.5), (7, 4), 3.5, (1.6,), zt=[(0, ZT + 0.2), (0.6, ZT + 0.7), (0.6, ZT + 1.7), (3.5, ZT + 1.7)])
    par((5, 6), (-5, 6), 10.0, (1.0, 3.0, 5.0, 7.0, 9.0))
    par((-7, 4), (-7, -4), 8.0, (1.0, 3.0, 5.0, 7.0))
    # string courses + pilaster buttresses
    for z in (7.72, 13.35):
        k.box((-5, -6.07, z), (0.5 if z > 10 else 2.6, -6.0, z + 0.16), SB, ST_L, skip=('+y', '-x'))
        k.box((-5, 6.0, z), (5, 6.07, z + 0.16), SB, ST_L, skip=('-y', '-x', '+x'))
        k.box((-7.07, -4, z), (-7.0, 4, z + 0.16), SB, ST_L, skip=('+x', '-y', '+y'))
        if z < 10:
            k.box((7.0, 1.2, z), (7.07, 4, z + 0.16), SB, ST_L, skip=('-x', '+y'))
    k.box((-0.8, 6.0, -0.9), (0.8, 6.35, 7.72), SB, ST, skip=('-y', '-z'), taper=(1.0, 0.3), shift=(0, -0.12))
    k.box((-7.35, -0.8, -0.9), (-7.0, 0.8, 12.6), SB, ST, skip=('+x', '-z'), taper=(0.3, 1.0), shift=(0.12, 0))
    # ---- corner turrets (front-right one collapsed)
    tz = [0.0, 0.9, 2.5, 5.0, 8.0, 11.0, 14.0]
    tk = dict(zc=tz, batter=(0.4, 2.5), ds=1.5)
    pier(k, -8, -7, -5, -4, -0.9, 16.9, **tk)                   # front-left
    turret_top(k, -8, -7, -5, -4, 16.9, missing=(1, 5))
    pier(k, 5, 4, 8, 7, -0.9, 17.4, **tk)                       # back-right
    turret_top(k, 5, 4, 8, 7, 17.4, missing=(4,))
    pier(k, -8, 4, -5, 7, -0.9, 18.0 - 0.75, **tk)              # back-left (tallest)
    turret_top(k, -8, 4, -5, 7, 18.0 - 0.75)
    # collapsed turret: stepped stump (three broken stages)
    pier(k, 5, -7, 8, -4, -0.9, 3.0, tops=(2.7, 1.5, 2.4, 3.3), top_mat=SW, top_col=CORE, **tk)
    pier(k, 5, -6.1, 7.2, -4, 2.0, 5.0, tops=(4.3, 3.2, 4.4, 5.3), top_mat=SW, top_col=CORE, zc=[3.2], ds=1.5)
    pier(k, 5, -5.2, 6.3, -4, 3.8, 7.0, tops=(6.2, 5.0, 6.4, 7.6), top_mat=SW, top_col=CORE, zc=[5.4], ds=1.5)
    for (x0, y0, x1, y1, faces) in ((-8, -7, -5, -4, 'fl'), (5, 4, 8, 7, 'br'), (-8, 4, -5, 7, 'bl')):
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        ws = []
        if 'f' in faces:
            ws.append(Wall((x0, y0), (x1, y0), 0, 0))
        if 'b' in faces:
            ws.append(Wall((x1, y1), (x0, y1), 0, 0))
        if 'l' in faces:
            ws.append(Wall((x0, y1), (x0, y0), 0, 0))
        if 'r' in faces:
            ws.append(Wall((x1, y0), (x1, y1), 0, 0))
        for i, w_ in enumerate(ws):
            slit(k, w_, 1.5, 9.3 + i * 0.6, h=1.3, cross=(i == 0))
            slit(k, w_, 1.5, 13.6 + i * 0.4, h=1.1, ww=0.11)
            slit(k, w_, 1.5, 4.6 - i * 0.5, h=1.2, ww=0.11)
    # ---- sealed doorway: steps, rubble wall inside the arch, blocks spilling out
    for i in range(3):
        k.box((-2.4 + i * 0.25, -7.5 + i * 0.4, -0.3), (2.4 - i * 0.25, -6.0, 0.3 * (i + 1)), SB, k.jit(ST_D, 0.04),
              skip=('+y', '-z'))
    archivolt(k, wf, door, band=0.34, proud=0.12)
    archivolt(k, wf, Op(5.3, 3.68, 0.9, 3.9, 6.0, n=4), band=0.16, proud=0.06, jambs=False)
    arch_decal(k, wf, 5.3, 0.9, 3.0, 3.9, 5.7, off=-0.55, col=mulc(CORE, 0.75), mat=SW, n=4, flag=0)
    rng = random.Random(5)
    for i in range(12):
        x = rng.uniform(-1.25, 1.25)
        z = 1.0 + (i / 12.0) ** 1.2 * 3.3
        if abs(x) > 1.5 - max(0.0, z - 3.9) * 0.75:
            x *= 0.4
        block(k, (x, -5.5 + rng.uniform(-0.12, 0.1), z), (rng.uniform(0.5, 0.95), 0.45, rng.uniform(0.3, 0.5)),
              rz=rng.uniform(-0.25, 0.25), rx=rng.uniform(-0.15, 0.15), ry=rng.uniform(-0.2, 0.2))
    rubble(k, (0.3, -6.6, 0.75), (1.5, 0.75), 0.5, blocks=6, seed=3, nu=8)
    sun_emblem(k, (0, -6.0, 6.95), 0.62, broken=(0, 1, 7, 8, 9), proud=0.09, ray_mat='M_metal_gold', ray_col=GOLD_D)
    # ---- interior: floor, debris, remains of a timber floor
    k.quad([(-5.2, -4.2, 0.45), (5.2, -4.2, 0.45), (5.2, 4.2, 0.45), (-5.2, 4.2, 0.45)], SW, mulc(CORE, 0.7))
    rock(k, (3.9, -3.2, 0.3), (2.6, 2.3, 2.6), seed=7, nu=9, nv=3, mat=SW, col=CORE, rough=0.22, zmin=0.0)
    for (p0, p1) in (((-5.2, 1.5, 9.4), (0.8, 1.5, 9.4)), ((-5.2, 3.0, 9.4), (2.6, 3.0, 9.4)),
                     ((-5.2, -0.2, 9.4), (-2.2, -0.2, 9.4)), ((-1.5, 2.2, 9.3), (3.4, -1.9, 1.6)),
                     ((0.4, -0.4, 0.6), (4.6, 3.4, 5.6))):
        k.beam(p0, p1, 0.3, 0.32, WD, k.jit(CHAR, 0.12))
    k.box((-5.2, 1.6, 9.56), (-1.2, 4.2, 9.62), WD, mulc(PAL['plank_d'], 0.7), skip=('+y', '-x'))
    # ---- the collapse: rubble mound over the front-right corner
    rubble(k, (6.9, -5.9, 0), (3.6, 3.2), 3.0, blocks=16, seed=11, bs=(0.6, 1.3), nu=11, nv=4)
    rubble(k, (9.6, -3.2, 0), (2.0, 2.4), 1.0, blocks=8, seed=13, bs=(0.5, 1.0))
    rubble(k, (4.2, -8.6, 0), (2.4, 1.6), 0.9, blocks=8, seed=17, bs=(0.5, 1.0))
    for (c, rz, rx, ry, s) in (((9.3, -7.4, 0.5), 0.6, 0.4, 0.3, (2.3, 1.2, 1.3)),
                               ((6.2, -9.3, 0.4), 1.9, -0.3, 0.25, (1.8, 1.0, 1.0)),
                               ((10.6, -5.0, 0.35), 2.6, 0.2, -0.3, (1.5, 0.9, 0.9)),
                               ((2.6, -7.6, 0.25), 0.3, 0.2, 0.1, (1.2, 0.6, 0.6))):
        block(k, c, s, rz=rz, rx=rx, ry=ry, col=ST)
    # cracks + weathering details
    crack(k, Panel((-4.5, -6.02, 6.0), (-1.5, -6.02, 6.0), (-1.5, -6.02, 13.0), (-4.5, -6.02, 13.0)),
          [(0.75, 0.0), (0.7, 0.2), (0.78, 0.3)], w=0.07)
    proud_stones(k, Wall((-5, -6), (-1.9, -6), 0, 0), 5, 2.7, 6.7, seed=2)
    proud_stones(k, wb, 9, 2.7, 7.6, seed=4, s0=0.5, s1=10.0)
    proud_stones(k, wl, 7, 2.7, 7.6, seed=6, s0=0.5, s1=8.0)
    # ---- nodes
    k.col('body', (-7, -6, 0), (7, 6, ZT + 1.7))
    k.col('turret_fl', (-8, -7, 0), (-5, -4, 17.6))
    k.col('turret_bl', (-8, 4, 0), (-5, 7, 18.0))
    k.col('turret_br', (5, 4, 0), (8, 7, 18.0))
    k.col('collapse', (4.4, -8.6, 0), (9.6, -3.6, 3.2))
    k.col('steps', (-2.4, -7.5, 0), (2.4, -6.0, 0.9))
    k.person = (-1.8, -8.4)


# ----------------------------------------------------------------------------- throne
@asset('throne', "Ruined royal throne of Aubeclair on a three-step dais 5 m wide: stone seat with armrests, 3.9 m "
       "carved back with pinnacles and a shattered golden sun, Astre crystal shards growing through seat, back and "
       "steps, the fallen crown on a step", 1800, footprint=[5.4, 6.6], bake=dict(ao_dist=1.4, ao_min=0.3, dirt_h=0.5,
                                                                                  dirt=0.25), res=512,
       weather=dict(top=0.18, base=0.3))
def throne(k):
    # ---- dais (3 steps of 0.2 m)
    steps = [(-2.5, -2.0, 2.5, 1.7, 0.2), (-2.08, -1.55, 2.08, 1.62, 0.4), (-1.66, -1.1, 1.66, 1.54, 0.6)]
    for i, (x0, y0, x1, y1, z) in enumerate(steps):
        k.box((x0, y0, -0.3 if i == 0 else z - 0.2), (x1, y1, z), SB, k.jit(ST, 0.03, 0.0), skip=('-z',))
        # nosing line
        k.box((x0 - 0.03, y0 - 0.03, z - 0.06), (x1 + 0.03, y1, z - 0.015), SB, ST_L, skip=('+y', '-z', '+z'))
    k.quad([(-0.6, -1.11, 0.616), (0.6, -1.11, 0.616), (0.6, 0.1, 0.616), (-0.6, 0.1, 0.616)], CL, L('#5e1f1c'))
    # ---- seat, armrests
    k.box((-0.62, 0.12, 0.6), (0.62, 1.05, 1.14), SB, ST, skip=('-z', '+y'))
    k.box((-0.66, 0.08, 1.14), (0.66, 1.05, 1.22), SB, ST_L, skip=('+y',))
    k.blob((0.0, 0.52, 1.22), (0.5, 0.36, 0.07), nu=8, nv=2, mat=CL, col=L('#6e2420'), zmin=0.0)
    for sx in (-1, 1):
        x0, x1 = (sx * 0.62, sx * 0.9) if sx > 0 else (sx * 0.9, sx * 0.62)
        k.box((x0, 0.1, 0.6), (x1, 1.05, 1.58), SB, ST, skip=('-z', '+y'))
        k.box((x0 - 0.03, 0.05, 1.58), (x1 + 0.03, 1.05, 1.66), SB, ST_L, skip=('+y',))
        k.blob((sx * 0.76, 0.08, 1.66), (0.16, 0.15, 0.14), nu=6, nv=3, mat=SB, col=ST_L, zmin=-0.3)
        arch_decal(k, Wall((sx * 0.9, 0.1), (sx * 0.9, 1.05), 0, 0) if sx > 0 else Wall((sx * 0.9, 1.05), (sx * 0.9, 0.1), 0, 0),
                   0.475, 0.75, 0.5, 1.2, 1.45, off=0.012, col=mulc(ST, 0.55), n=2, flag=0)
    # ---- tall back with pointed head, pinnacles, carved panel
    yb0, yb1 = 1.05, 1.38
    out = [(-0.92, 0.6), (0.92, 0.6), (0.92, 2.75), (0.62, 2.75), (0.62, 2.95), (0.3, 3.45), (0.0, 3.72), (-0.3, 3.45),
           (-0.62, 2.95), (-0.62, 2.75), (-0.92, 2.75)]
    k.prism([(x, yb0, z) for x, z in out], (0, yb1 - yb0, 0), SB, ST)
    wbk = Wall((-0.92, yb0), (0.92, yb0), 0, 0)
    arch_decal(k, wbk, 0.92, 1.3, 1.1, 2.35, 2.95, off=0.01, col=mulc(ST, 0.6), n=3, flag=0)
    archivolt(k, wbk, Op(0.92, 1.1, 1.3, 2.35, 2.95, n=3), band=0.1, proud=0.035)
    for sx in (-1, 1):
        x = sx * 0.98
        k.box((x - 0.15, yb0 - 0.04, 0.6), (x + 0.15, yb1 + 0.03, 3.05), SB, ST_L, skip=('-z',), taper=(0.85, 0.85))
        k.cyl((x, (yb0 + yb1) / 2, 3.05), (x, (yb0 + yb1) / 2, 3.9 if sx < 0 else 3.42), 0.17, 0.0 if sx < 0 else 0.1,
              n=4, mat=SB, col=ST, phase=PI / 4, smooth=False, caps=(False, True), cap_mat=SW, cap_col=CORE)
    # shattered sun (gold): right half broken away + crack down the back
    sun_emblem(k, (0, yb0, 3.2), 0.4, broken=(0, 1, 2, 10, 11), proud=0.05, mat='M_metal_gold', col=GOLD_D,
               ray_col=GOLD, disc=0.5)
    crack(k, Panel((-0.92, yb0 - 0.002, 0.6), (0.92, yb0 - 0.002, 0.6), (0.92, yb0 - 0.002, 3.6), (-0.92, yb0 - 0.002, 3.6)),
          [(0.62, 0.86), (0.68, 0.74), (0.63, 0.62), (0.72, 0.5), (0.69, 0.36), (0.78, 0.22)], w=0.035)
    # ---- Astre crystals growing through the throne
    C = [((0.72, 1.1, 1.0), (0.35, -0.25, 1.0), 2.5, 0.24, 2), ((0.95, 1.2, 0.7), (0.75, -0.1, 0.8), 1.5, 0.17, 1),
         ((0.45, 0.75, 1.1), (0.15, -0.5, 1.0), 0.95, 0.11, 1), ((0.6, 1.3, 1.6), (0.2, 0.5, 1.0), 1.5, 0.15, 1),
         ((1.25, 0.8, 0.55), (0.9, -0.5, 0.6), 0.9, 0.11, 1), ((-1.5, -1.2, 0.3), (-0.5, -0.35, 1.0), 1.25, 0.15, 1),
         ((-1.2, -1.45, 0.3), (0.2, -0.7, 0.8), 0.7, 0.09, 1), ((-1.85, -1.0, 0.2), (-0.9, 0.1, 0.7), 0.75, 0.1, 1),
         ((-0.7, 1.2, 2.3), (-0.6, -0.5, 0.8), 0.6, 0.08, 1), ((1.6, -0.2, 0.55), (0.5, 0.3, 1.0), 0.6, 0.08, 1)]
    for i, (p, ax, ln, r, seg) in enumerate(C):
        shard(k, p, ax, ln, r, n=6, phase=i * 0.9, seg=seg, tipf=0.26, slant=0.08, seed=i, jit=0.07)
    for (c, s, rz, rx, ry) in (((-1.45, -1.25, 0.42), (0.8, 0.5, 0.2), 0.4, 0.35, -0.3),
                               ((-1.0, -1.7, 0.25), (0.6, 0.4, 0.2), -0.3, -0.3, 0.2),
                               ((1.2, 1.0, 1.75), (0.5, 0.4, 0.3), 0.2, 0.3, 0.4)):
        block(k, c, s, rz=rz, rx=rx, ry=ry, col=ST)
    # ---- fallen crown on the second step, torn cloth over the left arm
    cz = 0.4
    with k.at((0.75, -1.3, cz + 0.085), rx=1.35, rz=0.6):
        k.lathe((0, 0, -0.06), [(0.1, 0.0), (0.105, 0.05), (0.1, 0.05)], n=8, mat='M_metal_gold', col=GOLD, split=(1,))
        for i in range(8):
            a = 2 * PI * i / 8
            k.quad([(0.105 * math.cos(a - 0.2), 0.105 * math.sin(a - 0.2), -0.01),
                    (0.105 * math.cos(a + 0.2), 0.105 * math.sin(a + 0.2), -0.01),
                    (0.11 * math.cos(a), 0.11 * math.sin(a), 0.07)], 'M_metal_gold', GOLD, double=True)
    rag(k, (-0.95, 0.2, 1.67), (0, 1, 0), (-0.25, 0, -1), 0.7, 0.9, nu=2, nv=4, col=L('#6e2420'), wave=0.05, seed=5)
    # back of the throne: two pilasters and a blind arch
    wbb = Wall((0.92, yb1), (-0.92, yb1), 0, 0)
    arch_decal(k, wbb, 0.92, 0.9, 1.0, 2.2, 2.8, off=0.01, col=mulc(ST, 0.6), n=3, flag=0)
    for sx in (-1, 1):
        k.box((sx * 0.62 - 0.12, yb1, 0.6), (sx * 0.62 + 0.12, yb1 + 0.16, 2.7), SB, ST_L, skip=('-y', '-z'),
              taper=(1.0, 0.3), shift=(0, -0.05))
    # iron candle stands: one standing, one toppled
    def stand(top, base, lit=False):
        top, base = V(top), V(base)
        d = (top - base).normalized()
        k.cyl(base, top, 0.03, 0.022, n=5, mat=IR, col=PAL['iron'], caps=(False, False))
        s = d.cross(V((0, 1, 0)) if abs(d.y) < 0.9 else V((1, 0, 0))).normalized()
        u = d.cross(s)
        for i in range(3):
            a = 2 * PI * i / 3
            o = (s * math.cos(a) + u * math.sin(a)) * 0.24
            k.beam(base + d * 0.3, base + o, 0.03, 0.03, IR, PAL['iron'], skip=('c0', 'c1'), uv='box')
            k.beam(top - d * 0.25, top + o * 0.85, 0.022, 0.022, IR, PAL['iron_l'], skip=('c0', 'c1'), uv='box')
            if lit:
                k.cyl(top + o * 0.85, top + o * 0.85 + d * 0.16, 0.022, 0.02, n=4, mat='M_bone', col=L('#e6dcc2'),
                      caps=(False, True))
    stand((-1.42, 1.05, 2.45), (-1.42, 1.05, 0.6), lit=True)
    stand((2.1, -0.6, 0.52), (1.5, 0.75, 0.66))
    # hairline cracks in the steps (dark, 1.5 cm proud)
    for (pts, z) in (([(-1.3, -2.0), (-1.05, -1.84), (-1.3, -1.7), (-1.15, -1.57)], 0.2),
                     ([(0.4, -1.55), (0.62, -1.4), (0.45, -1.26), (0.7, -1.12)], 0.4),
                     ([(1.9, -0.9), (2.2, -0.5), (2.0, -0.1), (2.3, 0.4)], 0.2)):
        for (a, b) in zip(pts[:-1], pts[1:]):
            a3, b3 = V((a[0], a[1], z + 0.015)), V((b[0], b[1], z + 0.015))
            s = (b3 - a3).cross(V((0, 0, 1))).normalized() * 0.022
            k.quad([a3 - s, b3 - s, b3 + s, a3 + s], SB, mulc(ST, 0.22), flag=NOAO, nh=(0, 0, 1))
    for i, (p, ax, ln, r) in enumerate((((-0.8, 0.5, 1.5), (-0.7, -0.3, 0.9), 0.75, 0.085),
                                        ((0.2, -1.75, 0.2), (0.3, -0.6, 1.0), 0.6, 0.075),
                                        ((2.0, 0.9, 0.2), (0.7, 0.4, 0.9), 0.8, 0.1),
                                        ((-2.2, 0.6, 0.15), (-0.8, 0.2, 0.8), 0.65, 0.08),
                                        ((1.05, 1.5, 0.3), (0.4, 0.9, 0.9), 1.3, 0.13))):
        shard(k, p, ax, ln, r, n=6, phase=i * 1.3, tipf=0.3, slant=0.08, seed=20 + i, jit=0.07)
    k.empty('ANCHOR_boss', (0, -3.3, 0))
    k.empty('ANCHOR_seat', (0, 0.5, 1.22))
    k.empty('GLOW_crystal', (0.85, 0.9, 2.3))
    k.walk('dais_1', (-2.5, -2.0, -0.3), (2.5, 1.7, 0.2))
    k.walk('dais_2', (-2.08, -1.55, 0.0), (2.08, 1.62, 0.4))
    k.walk('dais', (-1.66, -1.1, 0.2), (1.66, 1.54, 0.6))
    k.col('throne', (-1.1, 0.1, 0.0), (1.2, 1.45, 3.7))
    k.person = (-1.2, -0.5, 0.6)


# ----------------------------------------------------------------------------- knight statue
def knight(k, parts='all', n=10, mat=RK, col=None):
    """Armoured knight, human units (1.86 m to the top of the great helm), feet on z = 0, facing -Y, both hands
    on the pommel of a sword planted in front of him. parts: 'all' | 'lower' | 'upper'."""
    col = col or ROCK
    E = dict(mat=mat, col=col)
    lo, up = parts in ('all', 'lower'), parts in ('all', 'upper')
    cy = 0.02
    if lo:
        for sx in (-1, 1):
            k.box((sx * 0.14 - 0.058, -0.21, 0.0), (sx * 0.14 + 0.058, 0.09, 0.095), mat, col, skip=('-z',),
                  taper=(0.8, 0.82))
            k.cyl((sx * 0.14, 0.02, 0.07), (sx * 0.145, 0.0, 0.5), 0.064, 0.08, n=7, caps=(False, False), **E)
            k.blob((sx * 0.145, -0.025, 0.52), (0.078, 0.09, 0.075), nu=6, nv=3, **E)
            k.cyl((sx * 0.145, 0.0, 0.52), (sx * 0.125, 0.02, 0.9), 0.086, 0.115, n=7, caps=(False, False), **E)
        k.lathe((0, cy, 0), [(0.2, 0.75), (0.245, 0.73), (0.236, 0.84), (0.218, 0.84), (0.21, 0.95), (0.195, 0.95),
                             (0.188, 1.045)], n=n, sy=0.74, split=(1, 2, 3, 4, 5), **E)
        # tabard between the legs
        k.grid([[(-0.1, -0.175, 0.98), (0.1, -0.175, 0.98)], [(-0.11, -0.2, 0.7), (0.11, -0.2, 0.7)],
                [(-0.1, -0.19, 0.42), (0.1, -0.19, 0.42)]], mat, mulc(col, 0.95), double=True, flip=False)
    if up:
        k.lathe((0, cy, 0), [(0.2, 1.02), (0.205, 1.035), (0.205, 1.075), (0.19, 1.09), (0.2, 1.17), (0.228, 1.3),
                             (0.218, 1.41), (0.165, 1.495), (0.105, 1.53), (0.095, 1.575)], n=n, sy=0.7,
                split=(1, 2, 3, 8), **E)
        for sx in (-1, 1):
            k.blob((sx * 0.268, cy, 1.455), (0.118, 0.125, 0.09), nu=7, nv=3, zmin=-0.45, **E)
            k.blob((sx * 0.29, cy, 1.375), (0.085, 0.105, 0.075), nu=6, nv=2, zmin=-0.3, **E)
            k.cyl((sx * 0.28, cy, 1.4), (sx * 0.305, -0.07, 1.17), 0.062, 0.056, n=6, caps=(False, False), **E)
            k.blob((sx * 0.308, -0.075, 1.165), (0.066, 0.072, 0.062), nu=5, nv=2, **E)
            k.cyl((sx * 0.3, -0.085, 1.165), (sx * 0.06, -0.3, 1.205), 0.056, 0.047, n=6, caps=(False, False), **E)
            k.blob((sx * 0.036, -0.315, 1.22), (0.056, 0.062, 0.05), nu=6, nv=2, **E)
        # great helm with eye slits, nasal bar and brow band
        hr, hsy = 0.122, 1.12
        k.lathe((0, 0, 0), [(0.105, 1.555), (0.118, 1.6), (hr, 1.72), (0.113, 1.8), (0.086, 1.845), (0.0, 1.857)], n=n,
                sy=hsy, split=(3, 4), **E)
        k.lathe((0, 0, 0), [(hr + 0.002, 1.742), (hr + 0.012, 1.748), (hr + 0.012, 1.772), (hr + 0.002, 1.778)], n=n,
                sy=hsy, **E)
        for sx in (-1, 1):
            a0, a1 = -PI / 2 + sx * 0.14, -PI / 2 + sx * 0.72
            rr = hr + 0.012
            k.quad([(rr * math.cos(a0), hsy * rr * math.sin(a0), 1.7), (rr * math.cos(a1), hsy * rr * math.sin(a1), 1.7),
                    (rr * math.cos(a1), hsy * rr * math.sin(a1), 1.728), (rr * math.cos(a0), hsy * rr * math.sin(a0), 1.728)],
                   mat, DARK, flag=NOAO, nh=(0, -1, 0))
        k.box((-0.014, -hsy * hr - 0.012, 1.6), (0.014, -hsy * hr + 0.01, 1.8), mat, mulc(col, 1.03), skip=('+y',))
        # cape
        rows = []
        for z in (1.5, 1.25, 0.9, 0.5, 0.14) if parts == 'all' else (1.5, 1.3, 1.1):
            t = (1.5 - z) / 1.36
            row = []
            for i in range(13):
                a = -0.16 * PI + 1.32 * PI * i / 12
                rp = 1.0 + (0.035 + 0.1 * t) * math.sin(a * 7.0 + 0.6) * (0.3 + 0.7 * math.sin(i * PI / 12))
                row.append((lerp(0.25, 0.42, t) * rp * math.cos(a), 0.05 + lerp(0.17, 0.36, t) * rp * math.sin(a), z))
            rows.append(row)
        k.grid(rows, mat, mulc(col, 0.97), double=True, flip=True)
    if parts == 'all':
        sword_stone(k, 0.0, 0.98, mat, col)


def sword_stone(k, z0, z1, mat, col, broken=False):
    y = -0.315
    k.loft([(-0.022, y - 0.012, z0), (0.022, y - 0.012, z0), (0.022, y + 0.012, z0), (-0.022, y + 0.012, z0)],
           [(-0.04, y - 0.016, z1), (0.04, y - 0.016, z1), (0.04, y + 0.016, z1), (-0.04, y + 0.016, z1)], mat,
           mulc(col, 1.04), caps=(False, broken))
    if not broken:
        k.box((-0.21, y - 0.024, z1), (0.21, y + 0.024, z1 + 0.05), mat, col)
        k.cyl((0, y, z1 + 0.05), (0, y, z1 + 0.2), 0.024, n=5, mat=mat, col=col, caps=(False, False))
        k.blob((0, y, z1 + 0.215), (0.042, 0.042, 0.04), nu=5, nv=2, mat=mat, col=col)


def plinth_block(k, h=0.85):
    k.box((-0.8, -0.8, -0.35), (0.8, 0.8, 0.2), SB, ST_D, skip=('-z',), taper=(0.96, 0.96))
    k.box((-0.66, -0.66, 0.2), (0.66, 0.66, h - 0.14), SB, ST, skip=('-z', '+z'))
    k.box((-0.76, -0.76, h - 0.14), (0.76, 0.76, h), SB, ST_L)
    w = Wall((-0.66, -0.66), (0.66, -0.66), 0, 0)
    k.quad([w.P(0.2, 0.3, 0.008), w.P(1.12, 0.3, 0.008), w.P(1.12, h - 0.24, 0.008), w.P(0.2, h - 0.24, 0.008)], SB,
           mulc(ST, 0.62))
    pan = Panel(w.P(0.2, 0.3, 0.008), w.P(1.12, 0.3, 0.008), w.P(1.12, h - 0.24, 0.008), w.P(0.2, h - 0.24, 0.008))
    for i, g in enumerate(('tyr', 'sun', 'ash', 'bar')):
        glyph(k, pan, g, 0.2 + i * 0.2, 0.5, size=0.17, w=0.022, off=0.014, col=mulc(ST, 0.25), mat=SB)


@asset('statue_knight', 'Stone statue of a knight of Aubeclair, 3.6 m with its plinth: great helm, pauldrons, cape, '
       'both gauntlets resting on the pommel of a sword planted between his feet', 2500, footprint=[1.9, 1.9],
       bake=dict(ao_dist=0.8, ao_min=0.3, dirt_h=0.4, dirt=0.3), res=512, weather=dict(top=0.5, base=0.25))
def statue_knight(k):
    plinth_block(k)
    with k.at((0, 0.05, 0.85), scale=1.485):
        knight(k, 'all', n=12)
    k.col('statue', (-0.7, -0.7, 0), (0.7, 0.7, 3.6))
    k.person = (1.5, -0.5)


@asset('statue_broken', 'The same knight statue broken at the waist: legs and half a sword still on the plinth, '
       'torso and helm lying face up in front, fragments', 1200, footprint=[4.0, 4.4],
       bake=dict(ao_dist=0.8, ao_min=0.3, dirt_h=0.4, dirt=0.3), weather=dict(top=0.5, base=0.25))
def statue_broken(k):
    plinth_block(k)
    S = 1.485
    with k.at((0, 0.05, 0.85), scale=S):
        knight(k, 'lower', n=8)
        sword_stone(k, 0.0, 0.52, RK, ROCK, broken=True)
        k.quad([(0.188 * math.cos(2 * PI * i / 8), 0.02 + 0.74 * 0.188 * math.sin(2 * PI * i / 8),
                 1.045 + 0.04 * math.sin(i * 2.4)) for i in range(8)], SW, CORE)
    with k.at((1.75, 0.15, 0.3), rx=-PI / 2 + 0.1, rz=2.55, ry=0.12, scale=S):
        knight(k, 'upper', n=8)
        k.quad([(0.2 * math.cos(2 * PI * i / 8), 0.02 + 0.7 * 0.2 * math.sin(2 * PI * i / 8), 1.02) for i in
                reversed(range(8))], SW, CORE)
    with k.at((-1.2, -1.1, 0.08), rz=0.8, rx=PI / 2 - 0.05, scale=S):
        sword_stone(k, 0.55, 0.98, RK, ROCK)
    rubble(k, (0.9, -0.9, 0), (0.7, 0.5), 0.2, blocks=4, seed=3, heap=False, bs=(0.2, 0.42), bmat=RK)
    block(k, (-0.9, 0.9, 0.12), (0.5, 0.35, 0.25), rz=0.4, rx=0.3, mat=RK, col=ROCK)
    k.col('statue', (-0.7, -0.7, 0), (0.7, 0.7, 2.4))
    k.col('torso', (0.0, -2.35, 0), (1.25, -0.95, 0.6))
    k.person = (-1.7, 0.4)
