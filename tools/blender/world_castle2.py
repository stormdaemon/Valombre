"""VALOMBRE world pack - citadel hero pieces: round tower (intact / collapsed), gatehouse, great keep
(uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *

WB = dict(ao_dist=2.2, ao_min=0.3, dirt_h=1.0, dirt=0.35)
BLUE = L('#3f5a7c')          # faded royal blue of Aubeclair

# ----------------------------------------------------------------------------- round tower
TOWER_PROF = [(3.5, -0.9), (3.34, 0.0), (3.06, 2.4), (3.0, 2.6), (3.0, 5.0), (3.0, 7.3), (3.0, 9.5)]


def crack(k, pan, pts, w=0.05, col=None, mat=SB):
    col = col or mulc(ST, 0.2)
    for a, b in zip(pts[:-1], pts[1:]):
        stroke(k, pan, a, b, w=w, off=0.014, col=col, mat=mat)


def tower_details(k, zmax=99.0, ruin=False):
    """slits, back door case, cracks shared by the intact and the ruined tower"""
    for (deg, z, cross) in ((0, 3.3, True), (-58, 6.0, False), (62, 5.9, False), (32, 7.6, True), (118, 3.6, False),
                            (-125, 3.9, False)):
        if z + 1.3 > zmax:
            continue
        with k.at((0, 0, 0), rz=math.radians(deg)):
            slit(k, tangent_wall(3.0), 1.0, z, h=1.25, ww=0.12, cross=cross, off=0.012)
    with k.at((0, 0, 0), rz=PI):                                    # door case on the courtyard side (+Y)
        pier(k, -1.0, -3.72, 1.0, -2.9, -0.9, 2.75, skip=('+y', '+z'), zc=[0.0, 1.4])
        k.loft([(-1.0, -3.72, 2.75), (1.0, -3.72, 2.75), (1.0, -2.9, 2.75), (-1.0, -2.9, 2.75)],
               [(-1.0, -3.02, 3.25), (1.0, -3.02, 3.25), (1.0, -2.9, 3.25), (-1.0, -2.9, 3.25)], SB, ST_L,
               caps=(False, True), skip=(2,))
        w = Wall((-1.0, -3.72), (1.0, -3.72), 0, 0)
        arch_decal(k, w, 1.0, 0.0, 1.15, 1.55, 2.3, off=0.012, col=DARK)
        archivolt(k, w, Op(1.0, 1.15, 0.0, 1.55, 2.3), band=0.16, proud=0.05)
        k.box((-0.8, -4.1, -0.3), (0.8, -3.72, 0.0), SB, ST_D, skip=('+y', '-z'))
    with k.at((0, 0, 0), rz=math.radians(-28)):
        pan = Panel((-1.0, -3.0, 2.8), (1.0, -3.0, 2.8), (1.0, -3.0, 8.8), (-1.0, -3.0, 8.8))
        pts = [(0.42, 0.0), (0.5, 0.13), (0.45, 0.27), (0.56, 0.4), (0.5, 0.52), (0.58, 0.66), (0.53, 0.8), (0.6, 0.95)]
        crack(k, pan, pts if not ruin else pts[:3])


def tower_cols(k, z1):
    for i in range(4):
        k.col('tower_%d' % (i + 1), (-3.2, -1.33, 0), (3.2, 1.33, z1), rz=i * PI / 4)


@asset('castle_tower', 'Round tower, 6 m diameter, 14.3 m high: battered base, arrow slits, machicolated crenellated '
       'parapet on corbels, half-collapsed conical slate roof showing its rafters, door case on the courtyard side '
       '(+Y), tattered banner', 2500, footprint=[7.4, 7.6], bake=WB, res=512)
def castle_tower(k):
    n = 16
    ring_wall(k, (0, 0, 0), n, TOWER_PROF, split=(3,))
    k.lathe((0, 0, 0), [(3.0, 4.88), (3.08, 4.93), (3.08, 5.05), (3.0, 5.1)], n=n, mat=SB, col=ST_L, split=(1, 2))
    # machicolated gallery
    for i in range(n):
        with k.at((0, 0, 0), rz=2 * PI * (i + 0.5) / n):
            k.loft([(-0.17, -3.0, 8.95), (0.17, -3.0, 8.95), (0.17, -3.0, 9.0), (-0.17, -3.0, 9.0)],
                   [(-0.17, -3.5, 9.38), (0.17, -3.5, 9.38), (0.17, -3.5, 9.5), (-0.17, -3.5, 9.5)], SB, ST_D,
                   caps=(False, True), skip=(2,))
    k.lathe((0, 0, 0), [(3.0, 9.5), (3.54, 9.5), (3.54, 10.4), (3.04, 10.4), (3.04, 9.75), (2.3, 9.75), (2.3, 10.82)],
            n=n, mat=SB, col=ST, split=(1, 2, 3, 4, 5))
    nm = 10
    for i in range(nm):
        if i in (6,):
            continue
        with k.at((0, 0, 0), rz=2 * PI * i / nm + 0.2):
            hh = 0.85 if i != 7 else 0.4
            k.box((-0.6, -3.53, 10.4), (0.6, -3.03, 10.4 + hh), SB, k.jit(ST, 0.04, 0.0), skip=('-z',),
                  cap_mat=SW if i == 7 else None, cap_col=CORE if i == 7 else None)
    present = [1, 1, 1, 2, 0, 0, 0, 0, 2, 1, 1, 1]
    cone_roof(k, (0, 0, 10.82), 2.75, 3.5, n=12, present=present, phase=0.3)
    k.cyl((0, 0, 14.25), (0, 0, 14.9), 0.035, 0.012, n=4, mat=IR, col=PAL['iron'], caps=(False, False))
    # hoarding beam stubs under the parapet
    for deg in (20, 65, 110, 200, 245, 335):
        a = math.radians(deg)
        d = V((math.cos(a), math.sin(a), 0))
        k.beam(d * 2.9 + V((0, 0, 8.72)), d * (3.75 + k.r(0, 0.5)) + V((0, 0, 8.72)), 0.16, 0.18, WD,
               k.jit(PAL['beam_d']), skip=('c0',))
    tower_details(k)
    # faded royal banner on the front
    k.beam((-0.75, -3.62, 8.5), (0.75, -3.62, 8.5), 0.07, 0.07, WD, PAL['beam_d'])
    for x in (-0.6, 0.6):
        k.beam((x, -3.0, 8.5), (x, -3.66, 8.5), 0.06, 0.06, IR, PAL['iron'], skip=('c0',), uv='box')
    rag(k, (-0.62, -3.63, 8.47), (1, 0, 0), (0, -0.03, -1), 1.24, 3.2, nu=3, nv=6, col=BLUE, wave=0.07, ragged=0.4,
        seed=4)
    rubble(k, (2.6, -2.9, 0), (1.5, 1.1), 0.55, blocks=7, seed=5)
    block(k, (-3.2, -2.6, 0.2), (1.2, 0.5, 0.5), rz=0.6, rx=0.2)
    block(k, (-3.9, -1.5, 0.15), (0.6, 0.45, 0.35), rz=1.9, ry=0.3)
    tower_cols(k, 11.3)
    k.person = (1.2, -4.6)


@asset('castle_tower_ruin', 'The same round tower collapsed at half height: jagged hollow shell 4 - 8.3 m with an '
       'exposed rubble core, filled with debris and broken beams, big rubble spill on the front-left side', 2000,
       footprint=[10.0, 9.4], bake=WB, res=512)
def castle_tower_ruin(k):
    n = 16
    zt = [7.9, 8.3, 7.5, 7.9, 7.0, 6.2, 6.5, 5.5, 4.6, 4.9, 4.0, 4.3, 5.1, 5.0, 6.2, 7.2]
    prof = TOWER_PROF[:5] + [(3.0, 6.2), (3.0, 7.3), (3.0, 8.4)]
    ring_wall(k, (0, 0, 0), n, prof, th=1.15, zt=zt, zin=3.4, split=(3,))
    # debris fill inside + broken floor beams
    rock(k, (0, 0, 3.3), (2.0, 2.0, 0.9), seed=3, nu=10, nv=3, mat=SW, col=mulc(CORE, 1.0), rough=0.25, zmin=0.0)
    for (p0, p1) in (((-1.6, 0.4, 3.7), (1.2, 1.1, 5.4)), ((0.9, -1.5, 3.6), (-0.6, 0.9, 4.4)),
                     ((1.5, 0.2, 3.9), (1.9, -0.3, 6.1))):
        k.beam(p0, p1, 0.2, 0.22, WD, k.jit(CHAR, 0.1))
    for i in range(5):
        a = 0.5 + i * 1.3
        block(k, (1.2 * math.cos(a), 1.2 * math.sin(a), 3.95 + 0.1 * (i % 3)), (0.7, 0.5, 0.4), rz=a, rx=0.3, ry=0.2)
    tower_details(k, zmax=5.0, ruin=True)
    # rubble spill (front-left = low side of the break)
    rubble(k, (-3.4, -2.9, 0), (2.6, 2.0), 1.3, blocks=12, seed=7, bs=(0.45, 1.0), nu=10)
    rubble(k, (-1.0, -4.3, 0), (1.6, 1.1), 0.6, blocks=6, seed=9)
    rubble(k, (-4.6, 0.3, 0), (1.3, 1.3), 0.5, blocks=5, seed=12)
    # big fallen wall chunks
    for (c, rz, rx, ry, s) in (((-4.3, -3.9, 0.45), 0.5, 0.5, 0.2, (1.9, 0.9, 1.1)),
                               ((-2.0, -5.0, 0.3), 2.1, -0.4, 0.3, (1.4, 0.8, 0.8)),
                               ((2.9, -3.3, 0.3), 1.0, 0.3, -0.3, (1.2, 0.7, 0.7))):
        block(k, c, s, rz=rz, rx=rx, ry=ry, col=ST)
    tower_cols(k, 6.0)
    k.col('spill', (-5.2, -4.4, 0), (-2.2, -1.4, 1.3))
    k.person = (1.6, -4.4)


# ----------------------------------------------------------------------------- gatehouse
def sun_emblem(k, c, r, nrm=(0, -1, 0), rays=12, broken=(), mat=SB, col=None, ray_col=None, proud=0.07, disc=0.55,
               ray_mat=None):
    """Carved sun of Aubeclair on a vertical face: disc + triangular rays; `broken` = missing ray indices."""
    col = col or ST_L
    c = V(c)
    nrm = V(nrm).normalized()
    ux = V((0, 0, 1)).cross(nrm).normalized()
    uz = V((0, 0, 1))
    rd = r * disc

    def P(a, rr, o=0.0):
        return c + (ux * math.cos(a) + uz * math.sin(a)) * rr + nrm * o
    m = 10
    k.quad([P(2 * PI * i / m, rd, proud) for i in range(m)], mat, col, nh=nrm)
    for i in range(m):
        a0, a1 = 2 * PI * i / m, 2 * PI * (i + 1) / m
        k.quad([P(a0, rd, proud), P(a1, rd, proud), P(a1, rd * 1.08, 0), P(a0, rd * 1.08, 0)], mat, mulc(col, 0.85),
               nh=P((a0 + a1) / 2, 1, 0) - c)
    for i in range(rays):
        if i in broken:
            continue
        a = 2 * PI * (i + 0.5) / rays
        da = PI / rays * 0.62
        ln = r if i % 2 == 0 else r * 0.82
        k.quad([P(a - da, rd * 1.12, proud * 0.6), P(a + da, rd * 1.12, proud * 0.6), P(a, ln, proud * 0.35)],
               ray_mat or mat, ray_col or col, nh=nrm)


@asset('castle_gate', 'Gatehouse of the citadel, 10 m wide, 9 m high, 5.7 m deep: pointed archway 3.6 m wide x 4.5 m '
       'high (open, passable), raised iron portcullis, twin buttress-turrets, machicolated lintel, crenellated top, '
       'shattered sun emblem, banners', 3000, footprint=[10.4, 7.6],
       bake=dict(ao_dist=2.6, ao_min=0.28, dirt_h=1.0, dirt=0.35), res=512)
def castle_gate(k):
    ZR = 7.3
    op = Op(5.0, 3.6, -0.8, 2.7, 4.5, n=4)
    w = masonry(k, (-5, -2.5), (5, -2.5), -0.8, ZR, 5.0, ops=[op], tsub=3, zc=[0.0, 0.9, 2.7, 4.6, 6.2], ds=1.7,
                top_core=False)
    archivolt(k, w, op, band=0.3, proud=0.09)
    archivolt(k, w, op, band=0.26, proud=0.07, side=-1, th=5.0)
    # buttress-turrets flanking the gate + bridging lintel on corbels (deep shadow over the arch)
    for sx in (-1, 1):
        x0, x1 = (-5.0, -2.3) if sx < 0 else (2.3, 5.0)
        pier(k, x0, -3.2, x1, -2.5, -0.8, ZR, skip=('+y',), batter=(0.28, 2.0), zc=[0.0, 0.9, 2.0, 4.6, 6.2], ds=1.4,
             top=False)
        k.box((x0 - 0.05, -3.27, 6.12), (x1 + 0.05, -2.5, 6.3), SB, ST_L, skip=('+y',))
        wt = Wall((x0, -3.2), (x1, -3.2), 0, 0)
        slit(k, wt, 1.35, 2.9, h=1.35, cross=True)
        slit(k, wt, 1.35, 4.45, h=1.1, ww=0.11)
        proud_stones(k, wt, 3, 2.2, 5.8, seed=3 + sx)
    k.box((-2.3, -3.2, 6.3), (2.3, -2.5, ZR), SB, ST, skip=('+y', '-x', '+x', '+z', '-z'))
    k.quad([(-2.3, -3.2, 6.3), (2.3, -3.2, 6.3), (2.3, -2.5, 6.3), (-2.3, -2.5, 6.3)], SB, mulc(ST, 0.4),
           nh=(0, 0, -1))
    for i in range(5):
        x = -1.84 + i * 0.92
        k.loft([(x - 0.16, -2.5, 5.75), (x + 0.16, -2.5, 5.75), (x + 0.16, -2.5, 5.8), (x - 0.16, -2.5, 5.8)],
               [(x - 0.16, -3.15, 6.15), (x + 0.16, -3.15, 6.15), (x + 0.16, -3.15, 6.3), (x - 0.16, -3.15, 6.3)],
               SB, ST_D, caps=(False, True), skip=(2,))
    # parapet with crenels (front / back), plain on the sides; the rear left corner has collapsed
    fr_ops = [Op(s, 0.8, ZR + 0.85, ZR + 0.85, None) for s in (1.0, 3.0, 5.0, 7.0, 9.0)]
    masonry(k, (-5, -3.2), (5, -3.2), ZR, ZR + 1.7, 0.5, ops=fr_ops, zc=[], ds=9, top_core=False)
    bk_ops = [Op(s, 0.8, ZR + 0.85, ZR + 0.85, None) for s in (1.0, 3.0, 5.0, 7.0)]
    masonry(k, (5, 2.5), (-5, 2.5), ZR, [(0, ZR + 1.7), (7.6, ZR + 1.7), (7.6, ZR + 1.1), (8.3, ZR + 0.6),
                                         (8.3, ZR + 0.2), (10, ZR + 0.1)], 0.5, ops=bk_ops, zc=[], ds=9,
            top_core=lambda s: s > 7.6)
    masonry(k, (5, -2.7), (5, 2.0), ZR, ZR + 0.95, 0.5, zc=[], ds=9, ends=(False, False), top_core=False)
    masonry(k, (-5, 2.0), (-5, -2.7), ZR, [(0, ZR + 0.1), (1.2, ZR + 0.35), (1.2, ZR + 0.95), (4.7, ZR + 0.95)], 0.5,
            zc=[], ds=9, ends=(True, False), end_core=(True, False), top_core=lambda s: s < 1.2)
    k.quad([(-5, -3.2, ZR), (5, -3.2, ZR), (5, -2.5, ZR), (-5, -2.5, ZR)], SB, ST_D, nh=(0, 0, 1))
    # raised portcullis
    yp = -1.75
    zb = 3.2
    for i in range(7):
        x = -1.5 + i * 0.5
        zt_ = op.arch(5.0 + x) - 0.02
        k.beam((x, yp, zb), (x, yp, zt_), 0.075, 0.05, IR, PAL['iron'], up=(0, 1, 0), skip=('c0', 'c1'), uv='box')
        k.cyl((x, yp, zb), (x, yp, zb - 0.22), 0.045, 0.0, n=4, mat=IR, col=PAL['iron_l'], caps=(False, False),
              smooth=False)
    for z in (3.42, 3.92, 4.28):
        xh = 1.8
        while op.arch(5.0 + xh) < z + 0.04 and xh > 0.1:
            xh -= 0.05
        k.beam((-xh, yp - 0.03, z), (xh, yp - 0.03, z), 0.05, 0.075, IR, PAL['iron_l'], up=(0, 0, 1),
               skip=('c0', 'c1'), uv='box')
    # gate leaves swung open against the passage walls (left one intact, right one broken)
    for sx, zt_ in ((-1, 3.5), (1, 1.5)):
        x = sx * 1.74
        k.box((x - 0.05, 0.25, 0.05), (x + 0.05, 2.05, zt_), WD, k.jit(PAL['door']), skip=('-z',))
        for z in (0.6, 2.7):
            if z < zt_:
                k.box((x - 0.065, 0.3, z), (x + 0.065, 1.9, z + 0.1), IR, PAL['iron'], skip=('-z', '+z'))
    block(k, (1.1, 0.9, 0.08), (1.3, 0.2, 0.06), rz=0.5, mat=WD, col=PAL['plank_d'])
    block(k, (0.9, 1.7, 0.07), (1.0, 0.22, 0.06), rz=-0.3, mat=WD, col=PAL['plank_d'])
    # shattered sun of Aubeclair above the arch
    sun_emblem(k, (0, -3.2, 6.82), 0.46, broken=(1, 2, 3, 9), proud=0.07, ray_mat='M_metal_gold', ray_col=GOLD_D)
    # banners on the turrets
    for sx, col, sd in ((-1, BLUE, 2), (1, mulc(BLUE, 0.9), 6)):
        x = sx * 3.65
        k.beam((x - 0.6, -3.3, 5.95), (x + 0.6, -3.3, 5.95), 0.06, 0.06, WD, PAL['beam_d'])
        rag(k, (x - 0.5, -3.31, 5.92), (1, 0, 0), (0, -0.02, -1), 1.0, 2.9 if sx < 0 else 1.9, nu=2, nv=5, col=col,
            wave=0.06, ragged=0.45, seed=sd)
    # back (courtyard) side: two small windows
    wb = Wall((5, 2.5), (-5, 2.5), 0, 0)
    for s in (1.6, 8.4):
        arch_decal(k, wb, s, 4.6, 0.6, 5.5, 5.95, off=0.012, col=DARK)
        archivolt(k, wb, Op(s, 0.6, 4.6, 5.5, 5.95, n=2), band=0.12, proud=0.04, sill=0.1)
    proud_stones(k, wb, 6, 0.5, 4.2, seed=9, s0=0.3, s1=3.0)
    proud_stones(k, Wall((5, -2.5), (5, 2.5), 0, 0), 5, 0.6, 6.6, seed=4)
    proud_stones(k, Wall((-5, 2.5), (-5, -2.5), 0, 0), 5, 0.6, 6.6, seed=8)
    rubble(k, (-5.6, 3.0, 0), (1.3, 1.1), 0.6, blocks=7, seed=4)
    block(k, (4.1, -3.9, 0.2), (0.9, 0.5, 0.5), rz=0.4, rx=0.2)
    k.empty('ANCHOR_gate', (0, 0, 0))
    k.col('left', (-5, -3.2, -0.8), (-1.8, 2.5, 9.0))
    k.col('right', (1.8, -3.2, -0.8), (5, 2.5, 9.0))
    k.person = (0.9, -3.6)
