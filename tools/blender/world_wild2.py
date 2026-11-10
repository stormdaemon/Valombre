"""VALOMBRE world pack - biome set dressing 2: burnt village ruins, ruined watchtower, lighthouse, drowned chapel,
swamp hut, wrecks (uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *
from world_sacred import candle

BIG = dict(ao_dist=1.8, ao_min=0.3, dirt_h=0.8, dirt=0.35)
RUB = dict(mat=SW, core=SW, col=PAL['stone'], core_col=mulc(CORE, 0.92))     # village rubble masonry
VERDI = L('#5f8f7c')


def lean(pivot, rx=0.0, ry=0.0):
    """transform that tilts geometry around a pivot point (walls leaning out of plumb)"""
    T = Matrix.Translation(V(pivot))
    return T @ Euler((rx, ry, 0.0), 'XYZ').to_matrix().to_4x4() @ T.inverted()


def charred(k, p0, p1, w=0.2, h=0.22, **kw):
    k.beam(p0, p1, w, h, WD, k.jit(CHAR, 0.14), **kw)


# ----------------------------------------------------------------------------- burnt house
@asset('ruin_house', 'Burnt, roofless house shell, 7 x 6 m: rubble-stone walls broken at 1 - 3 m, one gable still '
       'standing to 5.3 m with its chimney stack, charred roof timbers, passable doorway in the front wall',
       2000, footprint=[8.6, 7.6], bake=dict(ao_dist=1.6, ao_min=0.3, dirt_h=0.8, dirt=0.35), res=448)
def ruin_house(k):
    x0, x1, y0, y1, th, zb = -3.5, 3.5, -3.0, 3.0, 0.5, -0.7
    zc = [0.0, 0.9, 2.0, 3.3]
    kw = dict(zc=zc, ds=1.8, **RUB)
    door = Op(2.2, 1.2, zb, 2.1, 2.1)
    f_zt = [(0, 2.9), (0.9, 3.15), (0.9, 2.7), (1.6, 2.55), (1.6, 2.75), (2.9, 2.6), (2.9, 2.3), (4.0, 2.5), (4.0, 2.9),
            (5.8, 2.7), (5.8, 2.3), (7, 2.6)]
    masonry(k, (x0, y0), (x1, y0), zb, f_zt, th, ops=[door, Op(5.1, 0.9, 1.0, 2.0, 2.0)], **kw)
    b_zt = [(0, 2.5), (1.4, 2.75), (1.4, 2.2), (2.6, 2.05), (2.6, 1.2), (3.4, 0.7), (4.4, 0.9), (4.4, 1.6), (5.2, 1.9),
            (5.2, 2.6), (7, 2.85)]
    masonry(k, (x1, y1), (x0, y1), zb, b_zt, th, ops=[Op(6.0, 0.8, 1.0, 1.95, 1.95)], **kw)
    r_zt = [(0, 2.45), (0.6, 3.0), (1.3, 3.7), (1.3, 4.1), (2.0, 4.8), (2.5, 5.3), (2.9, 5.0), (2.9, 4.5), (3.7, 3.8),
            (3.7, 3.3), (4.4, 2.9), (5, 2.6)]
    masonry(k, (x1, y0 + th), (x1, y1 - th), zb, r_zt, th, **kw)
    l_zt = [(0, 2.8), (0.8, 3.1), (1.5, 3.9), (1.5, 3.3), (2.4, 3.6), (2.4, 2.7), (3.4, 2.3), (3.4, 1.5), (4.2, 1.3),
            (5, 2.5)]
    masonry(k, (x0, y1 - th), (x0, y0 + th), zb, l_zt, th, ops=[Op(3.3, 0.7, 1.05, 1.9, 1.9)], **kw)
    # chimney breast + broken stack on the standing gable, hearth inside
    k.box((x1, -0.7, zb), (x1 + 0.55, 0.7, 3.3), SW, PAL['stone'], skip=('-x', '-z'), taper=(0.85, 0.75),
          shift=(-0.04, 0))
    pier(k, x1 - 0.05, -0.42, x1 + 0.45, 0.42, 3.3, 6.4, mat=SW, col=PAL['stone'], tops=(6.1, 6.5, 6.0, 5.6),
         top_mat=SW, top_col=PAL['soot'], zc=[4.8])
    wi = Wall((x1 - th, 2.5), (x1 - th, -2.5), 0, 0)
    arch_decal(k, wi, 2.5, 0.0, 1.2, 0.85, 1.25, off=0.012, col=DARK, mat=SW)
    k.box((x1 - th - 0.25, -0.75, 0.0), (x1 - th, 0.75, 0.14), SW, PAL['stone_d'], skip=('+x', '-z'))
    # charred timbers: door lintel, fallen tie beam, rafters on the gable, fallen ridge, debris
    charred(k, (x0 + 1.5, y0 - 0.04, 2.2), (x0 + 2.9, y0 - 0.04, 2.2), 0.14, 0.2)
    charred(k, (-0.2, y0 + 0.2, 2.75), (-0.6, y1 - 0.2, 1.95), 0.22, 0.24)
    charred(k, (x1 - 0.3, -2.55, 2.6), (x1 - 0.3, -0.25, 5.05), 0.14, 0.18)
    charred(k, (x1 - 0.32, 2.5, 2.75), (x1 - 0.32, 1.3, 3.95), 0.14, 0.18)
    charred(k, (x1 - 0.25, 0.0, 5.15), (-1.4, 0.7, 0.12), 0.2, 0.22)
    charred(k, (1.6, -2.6, 2.65), (2.1, -0.4, 0.15), 0.13, 0.16)
    for (p0, p1) in (((-2.6, 1.2, 0.1), (-0.4, 1.9, 0.16)), ((0.2, -1.6, 0.08), (2.2, -1.9, 0.12)),
                     ((-2.4, -0.9, 0.08), (-1.2, 0.5, 0.3)), ((1.0, 1.0, 0.1), (2.4, 2.2, 0.1))):
        charred(k, p0, p1, 0.16, 0.14)
    charred(k, (x0 + 1.52, y0 + 0.5, 0.0), (x0 + 1.75, y0 + 0.55, 1.75), 0.5, 0.05)        # burnt door leaf
    for (c, r, sd) in (((-1.6, 1.6, 0.0), (1.2, 0.9, 0.3), 3), ((1.3, -0.6, 0.0), (1.4, 1.1, 0.35), 5),
                       ((-0.2, -2.0, 0.0), (0.8, 0.5, 0.2), 7)):
        rock(k, c, r, seed=sd, nu=7, nv=2, mat=RK, col=mulc(ROCK, 0.25), zmin=0.0, rough=0.2)
    rubble(k, (-0.5, 3.6, 0), (1.3, 0.8), 0.45, blocks=5, seed=4, bmat=SW)
    rubble(k, (-3.9, -1.4, 0), (0.7, 1.1), 0.35, blocks=4, seed=6, bmat=SW)
    k.soot.append((V((0.6, 0.0, 2.6)), 5.2, 0.6))
    k.soot.append((V((x1, 0.0, 5.5)), 2.5, 0.7))
    k.empty('ANCHOR_door', (-1.3, -3.8, 0))
    k.col('front_l', (x0, y0, 0), (-1.9, y0 + th, 2.9))
    k.col('front_r', (-0.7, y0, 0), (x1, y0 + th, 2.7))
    k.col('right', (x1 - th, y0, 0), (x1, y1, 5.0))
    k.col('back', (x0, y1 - th, 0), (x1, y1, 2.6))
    k.col('left', (x0, y0, 0), (x0 + th, y1, 3.5))
    k.col('chimney', (x1, -0.7, 0), (x1 + 0.55, 0.7, 6.3))
    k.person = (-1.3, -3.9)


@asset('ruin_wall_a', 'Free-standing corner fragment of a burnt house: 4.5 m wall with a window, 2.3 m return, '
       'broken from 4.4 m down to 1.3 m', 500, footprint=[5.4, 4.0], bake=BIG)
def ruin_wall_a(k):
    kw = dict(zc=[0.0, 0.9, 2.2], ds=1.6, **RUB)
    win = Op(2.2, 0.8, 1.2, 2.1, 2.55, n=2)
    w = masonry(k, (-2.6, -0.3), (1.9, -0.3), -0.7, [(0, 1.4), (0.7, 1.9), (0.7, 2.6), (1.4, 2.9), (1.4, 3.5),
                                                    (2.9, 3.7), (2.9, 4.3), (3.7, 4.45), (4.5, 4.2)], 0.6, ops=[win],
                end_core=(True, False), **kw)
    masonry(k, (1.9, 0.3), (1.9, 2.6), -0.7, [(0, 4.1), (0.6, 3.9), (0.6, 3.1), (1.4, 2.7), (1.4, 1.9), (2.3, 1.3)], 0.6,
            end_core=(False, True), **kw)
    archivolt(k, w, win, band=0.13, proud=0.04, mat=SW, col=PAL['stone_w'], sill=0.1)
    k.box((1.55, -0.62, -0.7), (2.22, -0.3, 2.6), SW, PAL['stone'], skip=('+y', '-z'), taper=(1.0, 0.25),
          shift=(0, 0.12))
    for x in (-1.9, -0.9):
        k.quad([(x, 0.312, 2.35), (x + 0.2, 0.312, 2.35), (x + 0.2, 0.312, 2.55), (x, 0.312, 2.55)], SW, DARK,
               flag=NOAO, nh=(0, 1, 0))
    k.beam((0.2, 0.3, 2.45), (0.5, 1.5, 0.15), 0.16, 0.18, WD, k.jit(CHAR, 0.12))
    rubble(k, (-1.0, 1.0, 0), (1.1, 0.8), 0.4, blocks=5, seed=5, bmat=SW)
    k.soot.append((V((0.5, 0.8, 3.0)), 3.0, 0.5))
    k.col('wall', (-2.6, -0.3, 0), (1.9, 0.3, 3.8))
    k.col('return', (1.3, 0.3, 0), (1.9, 2.6, 3.4))
    k.person = (-0.6, -1.0)


@asset('ruin_wall_b', 'Free-standing 6 m wall fragment with a half-collapsed pointed doorway (passable), 5 m high at '
       'one end, buttress', 500, footprint=[6.6, 3.2], bake=BIG)
def ruin_wall_b(k):
    kw = dict(zc=[0.0, 0.9, 2.2, 3.6], ds=1.6, **RUB)
    op = Op(3.5, 1.2, -0.7, 1.9, 2.6, n=3)
    zt = [(0, 2.2), (0.8, 2.6), (0.8, 3.4), (1.9, 3.8), (1.9, 4.6), (2.9, 5.0), (3.3, 4.7), (3.3, 3.6), (3.9, 2.9),
          (4.1, 2.2), (4.1, 1.6), (5.0, 1.3), (5.0, 0.8), (6, 1.0)]
    w = masonry(k, (-3, -0.3), (3, -0.3), -0.7, zt, 0.6, ops=[op], end_core=(True, True), **kw)
    k.box((-1.95, -0.75, -0.7), (-1.25, -0.3, 3.4), SW, PAL['stone'], skip=('+y', '-z'), taper=(1.0, 0.2),
          shift=(0, 0.18))
    k.box((-1.95, 0.3, -0.7), (-1.25, 0.6, 2.4), SW, PAL['stone'], skip=('-y', '-z'), taper=(1.0, 0.2),
          shift=(0, -0.12))
    k.beam((-0.2, 0.36, 3.2), (-0.2, 1.6, 0.1), 0.16, 0.18, WD, k.jit(CHAR, 0.12))
    rubble(k, (1.9, 0.9, 0), (1.2, 0.8), 0.45, blocks=6, seed=3, bmat=SW)
    rubble(k, (2.2, -1.0, 0), (0.8, 0.6), 0.3, blocks=3, seed=8, bmat=SW)
    k.soot.append((V((-0.5, 0.5, 3.5)), 2.6, 0.45))
    k.col('left', (-3, -0.3, 0), (-0.1, 0.3, 4.6))
    k.col('right', (1.1, -0.3, 0), (3, 0.3, 1.5))
    k.person = (0.5, -1.0)


@asset('ruin_tower', 'Collapsed watchtower base, 6 m across: hollow round shell of rubble masonry 1 m thick, 6.2 m '
       'at its highest and broken down to 0.9 m on the -X side, doorway on -Y, charred beams, rubble spill', 1800,
       footprint=[9.0, 7.6], bake=BIG, res=448)
def ruin_tower(k):
    n = 16
    zt = [5.8, 6.2, 5.0, 4.3, 4.6, 3.2, 2.4, 1.2, 0.9, 1.5, 2.6, 2.9, 3.4, 4.4, 4.1, 5.2]
    prof = [(3.28, -0.8), (3.12, 0.0), (3.0, 1.2), (3.0, 2.2), (3.0, 3.4), (3.0, 4.8), (3.0, 6.3)]
    ph = PI / 16
    ring_wall(k, (0, 0, 0), n, prof, th=1.0, zt=zt, zin=-0.6, phase=ph, door=(11, 2.2), mat=SW, col=PAL['stone'],
              core_col=mulc(CORE, 0.92))
    charred(k, (-0.75, -3.04, 2.3), (0.75, -3.04, 2.3), 0.2, 0.22)
    k.box((-0.8, -3.5, -0.3), (0.8, -2.9, 0.06), SW, PAL['stone_d'], skip=('+y', '-z'))
    for (deg, z) in ((-20, 2.6), (48, 3.3), (95, 2.4)):
        with k.at((0, 0, 0), rz=math.radians(deg) + PI / 2):
            slit(k, tangent_wall(3.0), 1.0, z, h=1.05, ww=0.11, off=0.012, mat=SW, col=PAL['stone_w'])
    # inside: debris, burnt floor beams, ladder remains
    rock(k, (0.3, 0.4, -0.1), (1.6, 1.5, 0.55), seed=5, nu=9, nv=3, mat=SW, col=mulc(CORE, 0.9), zmin=0.0, rough=0.25)
    for (p0, p1) in (((1.9, 0.3, 3.3), (-1.2, 0.9, 0.35)), ((1.6, -1.1, 3.3), (1.2, 1.6, 3.35)),
                     ((0.9, 1.7, 3.3), (-0.6, -0.3, 0.5)), ((-0.9, -1.2, 0.15), (0.9, -1.5, 0.3))):
        charred(k, p0, p1, 0.2, 0.22)
    # rubble spill on the collapsed side
    rubble(k, (-3.5, 0.2, 0), (2.0, 2.3), 0.9, blocks=11, seed=7, bs=(0.4, 0.85), bmat=SW)
    rubble(k, (-2.2, -2.9, 0), (1.3, 1.0), 0.5, blocks=6, seed=9, bmat=SW)
    rubble(k, (-1.4, 0.2, 0.1), (0.9, 1.3), 0.5, blocks=5, seed=11, bmat=SW, heap=False)
    block(k, (2.9, -3.2, 0.2), (0.8, 0.5, 0.45), rz=0.5, rx=0.2, mat=SW)
    for m in range(8):
        secs = [2 * m, 2 * m + 1]
        if 11 in secs:
            secs = [10]
        a = ph + 2 * PI * (secs[0] + len(secs) / 2.0) / n
        ln = 2.4 if len(secs) == 2 else 1.25
        h = max(zt[s] for s in secs + [(secs[-1] + 1) % n])
        k.col('wall_%d' % (m + 1), (2.5 * math.cos(a) - ln / 2, 2.5 * math.sin(a) - 0.55, 0),
              (2.5 * math.cos(a) + ln / 2, 2.5 * math.sin(a) + 0.55, h), rz=a + PI / 2)
    k.person = (1.4, -3.9)


# ----------------------------------------------------------------------------- lighthouse
@asset('lighthouse', 'Weathered stone lighthouse, 18 m: battered round tower 6 m across at the base, gallery on '
       'corbels with an iron railing, glazed lantern room under a verdigris cap, lean-to store, door on -Y', 3000,
       footprint=[9.0, 7.4], bake=dict(ao_dist=2.4, ao_min=0.3, dirt_h=1.0, dirt=0.3), res=512,
       weather=dict(top=0.3, base=0.75, base_h=2.5, streak=0.16))
def lighthouse(k):
    n = 16
    prof = [(3.4, -0.9), (3.15, 0.0), (3.0, 0.8), (2.95, 0.9), (2.75, 4.0), (2.55, 7.5), (2.35, 11.0), (2.25, 12.1)]
    r_at, _ = ring_wall(k, (0, 0, 0), n, prof, split=(3,))
    for z in (4.0, 7.5):
        r = r_at(z)
        k.lathe((0, 0, 0), [(r, z - 0.1), (r + 0.08, z - 0.05), (r + 0.08, z + 0.07), (r, z + 0.12)], n=n, mat=SB,
                col=ST_L, split=(1, 2))
    # gallery on corbels
    for i in range(n):
        with k.at((0, 0, 0), rz=2 * PI * (i + 0.5) / n):
            k.loft([(-0.14, -2.27, 11.75), (0.14, -2.27, 11.75), (0.14, -2.27, 11.8), (-0.14, -2.27, 11.8)],
                   [(-0.14, -2.95, 12.3), (0.14, -2.95, 12.3), (0.14, -2.95, 12.42), (-0.14, -2.95, 12.42)], SB, ST_D,
                   caps=(False, True), skip=(2,))
    k.lathe((0, 0, 0), [(2.25, 12.1), (2.3, 12.42), (3.0, 12.42), (3.0, 12.6), (1.55, 12.6)], n=n, mat=SB, col=ST,
            split=(1, 2, 3))
    RI = L('#3d3a37')
    for i in range(n):
        if i in (5, 6):
            continue
        a = 2 * PI * i / n
        tilt = 0.25 if i == 7 else 0.0
        k.beam((2.9 * math.cos(a), 2.9 * math.sin(a), 12.6), ((2.9 + tilt) * math.cos(a), (2.9 + tilt) * math.sin(a), 13.5),
               0.045, 0.045, IR, RI, skip=('c0',), uv='box')
    ring = [(2.9 * math.cos(2 * PI * j / n), 2.9 * math.sin(2 * PI * j / n), 13.5) for j in range(7, n + 6)]
    k.tube(ring[1:-1], 0.03, n=3, mat=IR, col=RI, caps=True)
    ring = [(2.9 * math.cos(2 * PI * j / n), 2.9 * math.sin(2 * PI * j / n), 13.05) for j in range(8, n + 5)]
    k.tube(ring, 0.02, n=3, mat=IR, col=RI, caps=True)
    # lantern room
    k.lathe((0, 0, 0), [(1.55, 12.6), (1.55, 13.25), (1.62, 13.3), (1.62, 13.38), (1.45, 13.38)], n=8, mat=SB, col=ST,
            split=(1, 2, 3), phase=PI / 8)
    for i in range(8):
        a0, a1 = PI / 8 + 2 * PI * i / 8, PI / 8 + 2 * PI * (i + 1) / 8
        p0, p1 = V((1.45 * math.cos(a0), 1.45 * math.sin(a0), 0)), V((1.45 * math.cos(a1), 1.45 * math.sin(a1), 0))
        broken = i in (2,)
        if not broken:
            k.quad([p0 + V((0, 0, 13.38)), p1 + V((0, 0, 13.38)), p1 + V((0, 0, 15.0)), p0 + V((0, 0, 15.0))],
                   'M_window_glow', PAL['glow'], flag=NOAO)
            k.quad([p1 * 0.99 + V((0, 0, 13.38)), p0 * 0.99 + V((0, 0, 13.38)), p0 * 0.99 + V((0, 0, 15.0)),
                    p1 * 0.99 + V((0, 0, 15.0))], 'M_window_glow', mulc(PAL['glow'], 0.8), flag=NOAO)
        k.beam(p0 * 1.03 + V((0, 0, 13.38)), p0 * 1.03 + V((0, 0, 15.0)), 0.09, 0.09, IR, RI, skip=('c0', 'c1'),
               uv='box')
        mid = (p0 + p1) * 0.5 * 1.02
        k.beam(p0 * 1.02 + V((0, 0, 14.2)), p1 * 1.02 + V((0, 0, 14.2)), 0.05, 0.05, IR, RI, skip=('c0', 'c1'),
               uv='box')
    k.lathe((0, 0, 0), [(1.5, 14.95), (1.78, 14.98), (1.74, 15.1), (1.25, 15.75), (0.55, 16.35), (0.16, 16.6),
                        (0.13, 16.95)], n=8, mat='M_metal_bronze', col=VERDI, split=(1, 2, 5), phase=PI / 8,
            colfn=lambda i, r, z: mulc(VERDI, 0.75 + 0.3 * (z - 15.0) / 2.0))
    k.blob((0, 0, 17.08), (0.2, 0.2, 0.2), nu=6, nv=3, mat='M_metal_bronze', col=mulc(VERDI, 1.1))
    k.cyl((0, 0, 17.2), (0, 0, 18.0), 0.03, 0.012, n=4, mat=IR, col=RI, caps=(False, False))
    k.quad([(0.02, 0, 17.55), (0.55, 0, 17.62), (0.4, 0, 17.74), (0.55, 0, 17.86), (0.02, 0, 17.8)], IR, RI, double=True)
    k.empty('FIRE_top', (0, 0, 14.2))
    # door case with a plank door, steps
    pier(k, -1.0, -3.55, 1.0, -2.6, -0.9, 2.9, skip=('+y', '+z'), zc=[0.0, 1.4])
    k.loft([(-1.0, -3.55, 2.9), (1.0, -3.55, 2.9), (1.0, -2.6, 2.9), (-1.0, -2.6, 2.9)],
           [(-1.0, -2.85, 3.5), (1.0, -2.85, 3.5), (1.0, -2.6, 3.5), (-1.0, -2.6, 3.5)], SB, ST_L, caps=(False, True),
           skip=(2,))
    wd = Wall((-1.0, -3.55), (1.0, -3.55), 0, 0)
    arch_decal(k, wd, 1.0, 0.3, 1.1, 1.75, 2.45, off=0.012, col=mulc(PAL['door'], 0.55), mat=WD, flag=0)
    archivolt(k, wd, Op(1.0, 1.1, 0.3, 1.75, 2.45), band=0.16, proud=0.05)
    for z in (0.85, 1.6):
        k.quad([wd.P(0.47, z, 0.02), wd.P(1.2, z, 0.02), wd.P(1.2, z + 0.07, 0.02), wd.P(0.47, z + 0.07, 0.02)], IR,
               RI, nh=(0, -1, 0))
    k.box((-0.85, -4.3, -0.3), (0.85, -3.55, 0.15), SB, ST_D, skip=('+y', '-z'))
    k.box((-0.7, -3.95, 0.15), (0.7, -3.55, 0.3), SB, ST_D, skip=('+y', '-z'))
    # windows climbing round the shaft
    for (deg, z, lit) in ((-25, 3.0, False), (70, 5.4, True), (165, 8.3, False), (-105, 10.2, False), (20, 9.6, False)):
        with k.at((0, 0, 0), rz=math.radians(deg)):
            w = tangent_wall(r_at(z + 0.4) + 0.02)
            slit(k, w, 1.0, z, h=0.85, ww=0.3, frame=0.14, off=0.02)
            if lit:
                k.quad([w.P(0.86, z + 0.01, 0.045), w.P(1.14, z + 0.01, 0.045), w.P(1.14, z + 0.84, 0.045),
                        w.P(0.86, z + 0.84, 0.045)], 'M_window_glow', PAL['glow'], flag=NOAO)
    # lean-to store on the +X side
    ax0, ax1, ay0, ay1 = 2.3, 5.1, -1.2, 1.3
    pier(k, ax0, ay0, ax1, ay1, -0.9, 2.2, mat=SW, col=PAL['stone'], skip=('-x', '+z'), zc=[0.0, 1.1], ds=1.4)
    for (ya, yb, nh) in ((ay0, ay0, (0, -1, 0)), (ay1, ay1, (0, 1, 0))):
        k.quad([(ax0 + 0.3, ya, 2.2), (ax1, ya, 2.2), (ax0 + 0.3, ya, 3.25)], SW, PAL['stone'], nh=nh)
    roof_plane(k, (ax1 + 0.25, ay0 - 0.2, 2.1), (ax1 + 0.25, ay1 + 0.2, 2.1), (ax0 + 0.2, ay1 + 0.2, 3.4),
               (ax0 + 0.2, ay0 - 0.2, 3.4), tv=0.12, nu=3, nv=2, mat='M_roof_tiles', col=SLATE, sag=0.05, moss=0.8)
    wa = Wall((ax0, ay0), (ax1, ay0), 0, 0)
    k.quad([wa.P(1.3, 0.0, 0.012), wa.P(2.2, 0.0, 0.012), wa.P(2.2, 1.8, 0.012), wa.P(1.3, 1.8, 0.012)], WD,
           mulc(PAL['door'], 0.6))
    wbeam(k, wa, 1.2, 1.87, 2.3, 1.87, 0.14, 0.05, col=PAL['beam_d'], caps=(True, True))
    for (c, r, sd) in (((-3.4, -2.2, 0.0), (1.1, 0.9, 0.7), 3), ((3.0, -3.0, 0.0), (1.0, 0.8, 0.55), 6),
                       ((-3.2, 2.6, 0.0), (1.2, 1.0, 0.8), 9), ((1.4, 3.6, 0.0), (0.9, 0.8, 0.5), 12)):
        rock(k, c, r, seed=sd, nu=8, nv=3, zmin=-0.4)
    for i in range(4):
        k.col('tower_%d' % (i + 1), (-3.15, -1.31, 0), (3.15, 1.31, 13.5), rz=i * PI / 4)
    k.col('annex', (2.3, -1.2, 0), (5.1, 1.3, 3.3))
    k.col('door', (-1.0, -3.6, 0), (1.0, -2.6, 3.4))
    k.person = (1.6, -4.6)


# ----------------------------------------------------------------------------- drowned chapel
def bell(k, n=10, col=None):
    """bronze bell, mouth radius 0.62, 1.0 high, mouth at z = 0, axis +Z (inside modelled)"""
    col = col or mixc(PAL['bronze'], VERDI, 0.45)
    prof = [(0.0, 0.9), (0.26, 0.84), (0.33, 0.5), (0.42, 0.2), (0.56, 0.0), (0.62, 0.0), (0.58, 0.08), (0.45, 0.25),
            (0.38, 0.5), (0.345, 0.8), (0.28, 0.97), (0.0, 1.0)]
    k.lathe((0, 0, 0), prof, n=n, mat='M_metal_bronze', col=col, split=(4, 5, 10),
            colfn=lambda i, r, z: mulc(col, 0.35) if i < 5 else col)
    k.lathe((0, 0, 0), [(0.46, 0.2), (0.48, 0.22), (0.47, 0.27)], n=n, mat='M_metal_bronze', col=mulc(col, 1.15))
    k.cyl((0, 0, 1.0), (0, 0, 1.16), 0.1, 0.08, n=5, mat='M_metal_bronze', col=col, caps=(False, True))
    k.cyl((0.05, 0, 0.85), (0.22, 0.05, 0.02), 0.03, 0.06, n=4, mat=IR, col=PAL['iron'], caps=(False, True))


@asset('drowned_chapel', 'Chapelle Engloutie: half-sunken ruined chapel, 14 x 9 m. Leaning north wall with lancet '
       'windows and buttresses, broken west gable with a pointed doorway, polygonal apse reduced to stumps on the '
       'south, south wall almost gone (open nave), flagged floor, altar, toppled bronze bell, fallen timbers', 4000,
       footprint=[15.4, 10.6], bake=dict(ao_dist=2.6, ao_min=0.26, dirt_h=1.3, dirt=0.4, samples=12), res=512,
       weather=dict(top=0.5, base=0.95, base_h=2.4, damp=0.3, streak=0.14))
def drowned_chapel(k):
    zb, th = -1.0, 0.9
    zc = [0.25, 1.2, 2.4, 4.0, 5.6, 7.4]
    kw = dict(zc=zc, ds=1.8)
    X0, X1, YN = -7.0, 3.5, 4.3
    # ---- north wall, leaning outwards
    with k.xf(lean((0, YN, zb), rx=-0.055)):
        n_zt = [(0, 6.2), (1.0, 6.6), (1.0, 7.4), (4.2, 7.4), (4.2, 6.9), (5.0, 6.6), (5.0, 7.4), (8.6, 7.4), (8.6, 6.4),
                (9.4, 5.9), (9.4, 6.8), (10.5, 7.0)]
        nops = [Op(s, 0.95, 2.4, 5.0, 6.0, n=3) for s in (2.25, 5.3, 8.35)]
        wn = masonry(k, (X1, YN), (X0, YN), zb, n_zt, th, ops=nops, **kw)
        for o in nops:
            archivolt(k, wn, o, band=0.15, proud=0.05, sill=0.12)
        for s in (0.55, 3.78, 6.83, 9.9):
            x = X1 - s
            k.box((x - 0.4, YN, zb), (x + 0.4, YN + 0.85, 3.6), SB, ST, skip=('-y', '-z'), taper=(1.0, 0.62),
                  shift=(0, -0.16))
            k.box((x - 0.36, YN, 3.6), (x + 0.36, YN + 0.5, 6.2), SB, ST, skip=('-y', '-z'), taper=(1.0, 0.2),
                  shift=(0, -0.2))
        k.box((X0, YN - 0.02, 7.02), (X1 - 1.0, YN + 0.1, 7.2), SB, ST_L, skip=('-y',))
    # ---- west gable with the doorway, leaning west
    with k.xf(lean((X0, 0, zb), ry=-0.045)):
        door = Op(4.3, 1.8, zb, 2.6, 3.9, n=4)
        rose = Op(4.3, 1.2, 5.6, 7.0, 8.0, n=3)
        g_zt = [(0, 6.6), (0.8, 7.3), (1.6, 8.0), (1.6, 8.5), (2.6, 9.4), (3.3, 10.0), (3.3, 10.9), (3.9, 11.3), (3.9, 10.2),
                (4.9, 9.9), (4.9, 9.3), (5.6, 8.9), (6.4, 8.1), (6.4, 7.3), (7.3, 6.6), (7.3, 5.2), (8.0, 4.6), (8.6, 3.9)]
        wg = masonry(k, (X0, YN), (X0, -YN), zb, g_zt, th, ops=[door, rose], end_core=(False, True), **kw)
        archivolt(k, wg, door, band=0.28, proud=0.1, zb=0.0)
        archivolt(k, wg, Op(4.3, 2.36, zb, 2.6, 4.15, n=4), band=0.14, proud=0.05, jambs=False)
        archivolt(k, wg, rose, band=0.16, proud=0.06, sill=0.12)
        for s in (0.45, 8.15):
            y = YN - s
            k.box((X0 - 0.8, y - 0.42, zb), (X0, y + 0.42, 4.2 if s < 4 else 2.6), SB, ST, skip=('+x', '-z'),
                  taper=(0.3, 1.0), shift=(0.22, 0))
        k.box((X0 - 0.5, -1.5, -0.4), (X0, 1.5, 0.05), SB, ST_D, skip=('+x', '-z'))
    # ---- south wall: three stumps
    s_zt = [(0, 3.6), (0.9, 3.0), (0.9, 1.9), (1.8, 1.4), (1.8, 0.7), (2.6, 0.5), (2.6, zb), (5.2, zb), (5.2, 0.9),
            (5.9, 1.6), (5.9, 2.4), (6.6, 2.1), (6.6, 1.2), (7.4, 0.8), (7.4, zb), (9.0, zb), (9.0, 1.0), (9.8, 1.7),
            (9.8, 2.8), (10.5, 3.4)]
    masonry(k, (X0, -YN), (X1, -YN), zb, s_zt, th, end_core=(False, False), **kw)
    # ---- polygonal apse (5 sides), tall on the north, stumps on the south
    R = YN
    angs = [math.radians(a) for a in (-90, -54, -18, 18, 54, 90)]
    P = [(X1 + R * math.cos(a), R * math.sin(a)) for a in angs]
    a_zt = [[(0, 3.4), (0.9, 2.6), (0.9, 1.5), (2.66, 0.9)], [(0, 0.9), (1.2, 1.3), (1.2, 2.3), (2.66, 2.9)],
            [(0, 2.9), (0.6, 3.6), (0.6, 4.9), (1.9, 5.2), (1.9, 6.0), (2.66, 6.3)], [(0, 6.3), (1.4, 6.9), (2.66, 6.9)],
            [(0, 6.9), (2.66, 6.5)]]
    for i in range(5):
        ops = [Op(1.33, 0.85, 2.4, 4.6, 5.5, n=2)] if i >= 2 else []
        wa = masonry(k, P[i], P[i + 1], zb, a_zt[i], th, ops=ops, zc=zc, ds=3.0, end_core=(False, False))
        for o in ops:
            archivolt(k, wa, o, band=0.14, proud=0.05, sill=0.12)
    for i in range(1, 6):
        h = (2.0, 2.2, 3.6, 5.0, 5.2, 5.2)[i]
        with k.at((P[i][0], P[i][1], 0), rz=angs[i] - PI / 2):
            k.box((-0.35, -0.75, zb), (0.35, 0.1, h), SB, ST, skip=('-z',), taper=(1.0, 0.35), shift=(0, 0.25))
    # ---- floor (z = 0.25): flagged nave + apse, broken patches with dark water
    ri = R - th
    poly = [(X0 + th, -ri), (X1, -ri)] + [(X1 + ri * math.cos(a), ri * math.sin(a)) for a in angs[1:-1]] + \
           [(X1, ri), (X0 + th, ri)]
    k.prism([(x, y, zb) for x, y in poly], (0, 0, 0.25 - zb), SB, ST_D, caps=(False, True), cap_mat=CB,
            cap_col=mulc(ST, 0.92))
    for (c, r, sd) in (((-2.0, -2.2), 1.1, 1), ((1.5, 1.3), 0.8, 2), ((-4.6, 1.6), 0.7, 3), ((2.6, -2.4), 0.9, 4)):
        k.quad([(c[0] + r * (1 + 0.3 * math.sin(3 * a + sd)) * math.cos(a), c[1] + r * 0.7 * (1 + 0.25 * math.cos(2 * a + sd))
                 * math.sin(a), 0.288) for a in [2 * PI * j / 8 for j in range(8)]], CB, mulc(ST, 0.16), flag=NOAO)
    for x in (-4.0, -0.9, 2.2):
        k.quad([(x, -ri, 0.273), (x + 0.07, -ri, 0.273), (x + 0.07, ri, 0.273), (x, ri, 0.273)], CB, mulc(ST, 0.35),
               flag=NOAO)
    for y in (-1.2, 1.1):
        k.quad([(X0 + th, y, 0.273), (X1 + 1.0, y, 0.273), (X1 + 1.0, y + 0.07, 0.273), (X0 + th, y + 0.07, 0.273)], CB,
               mulc(ST, 0.35), flag=NOAO)
    # ---- altar in the apse, broken cross
    k.box((4.6, -1.0, 0.25), (5.9, 1.0, 0.45), SB, ST_D, skip=('-z',))
    k.box((4.85, -0.8, 0.45), (5.65, 0.8, 1.25), SB, ST, skip=('-z', '+z'), taper=(0.92, 0.95))
    k.box((4.75, -0.92, 1.25), (5.75, 0.92, 1.4), SB, ST_L)
    k.box((5.18, -0.09, 1.4), (5.36, 0.09, 2.15), SB, ST, skip=('-z',), cap_mat=SW, cap_col=CORE)
    k.box((5.19, -0.32, 1.78), (5.35, 0.09, 1.94), SB, ST)
    for (y, h) in ((-0.7, 0.16), (0.65, 0.22), (0.45, 0.1)):
        candle(k, (5.05, y, 1.4), h, lit=False)
    # ---- toppled bell with its broken yoke
    with k.at((-3.3, -0.9, 0.25 + 0.6), rx=PI / 2 - 0.12, rz=0.65):
        bell(k)
    charred(k, (-2.2, -1.9, 0.38), (-4.3, -0.2, 0.45), 0.24, 0.26)
    # ---- fallen roof timbers, rubble, drums
    for (p0, p1, w) in (((-5.5, 3.3, 5.6), (-1.6, -2.6, 0.45), 0.26), ((0.6, 3.3, 6.6), (1.4, -0.6, 0.5), 0.24),
                        ((-0.6, 2.9, 0.45), (2.9, 2.2, 0.55), 0.22), ((-5.9, -2.9, 0.4), (-4.2, -3.2, 2.9), 0.2),
                        ((2.2, -3.0, 0.4), (4.9, -1.5, 0.5), 0.22)):
        k.beam(p0, p1, w, w + 0.02, WD, k.jit(mulc(PAL['beam_d'], 0.7), 0.15))
    rubble(k, (-3.2, -4.6, -0.2), (1.9, 1.2), 0.9, blocks=7, seed=5, bs=(0.4, 0.85))
    rubble(k, (1.6, -4.7, -0.2), (1.5, 1.1), 0.8, blocks=5, seed=8, bs=(0.4, 0.8))
    rubble(k, (6.4, -3.4, -0.2), (1.6, 1.4), 0.9, blocks=6, seed=12, bs=(0.4, 0.85))
    rubble(k, (-0.3, -2.9, 0.25), (1.2, 0.6), 0.35, blocks=3, seed=14)
    rubble(k, (-6.0, 2.6, 0.25), (0.7, 0.9), 0.4, blocks=4, seed=16)
    for (c, rz) in (((0.8, -1.6, 0.52), 0.4), ((-5.2, -1.9, 0.5), 1.3)):
        d = V((math.cos(rz), math.sin(rz), 0))
        k.cyl(V(c) - d * 0.4, V(c) + d * 0.4, 0.27, n=8, mat=SB, col=ST, cap_mat=SW, cap_col=CORE)
    # ---- nodes
    k.walk('floor', (X0 + th, -ri, zb), (X1, ri, 0.25))
    k.walk('floor_apse', (X1, -2.3, zb), (X1 + 2.9, 2.3, 0.25))
    k.col('north', (X0, YN - th, 0), (X1, YN + 0.7, 7.4))
    k.col('west_n', (X0 - 0.4, 0.9, 0), (X0 + th, YN, 9.0))
    k.col('west_s', (X0 - 0.4, -YN, 0), (X0 + th, -0.9, 6.0))
    k.col('south_w', (X0, -YN, 0), (X0 + 2.6, -YN + th, 3.0))
    k.col('south_m', (X0 + 5.2, -YN, 0), (X0 + 7.4, -YN + th, 2.2))
    k.col('south_e', (X0 + 9.0, -YN, 0), (X1 + 0.4, -YN + th, 3.2))
    for i, nm in ((1, 'apse_se'), (2, 'apse_e'), (3, 'apse_ne'), (4, 'apse_n')):
        mx_, my_ = (P[i][0] + P[i + 1][0]) / 2, (P[i][1] + P[i + 1][1]) / 2
        am = (angs[i] + angs[i + 1]) / 2
        cx, cy = mx_ - 0.45 * math.cos(am), my_ - 0.45 * math.sin(am)
        k.col(nm, (cx - 1.4, cy - 0.5, 0), (cx + 1.4, cy + 0.5, (2.9, 6.3, 6.9, 6.9)[i - 1]), rz=am + PI / 2)
    k.col('altar', (4.6, -1.0, 0), (5.9, 1.0, 1.5))
    k.col('bell', (-4.1, -1.6, 0), (-2.6, -0.2, 1.5))
    k.person = (-0.5, -1.0, 0.25)
