"""VALOMBRE world pack - the citadel of Aubeclair: curtain walls, towers, gate, keep, stairs, pillars, throne,
statues, ceremonial brazier (uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *

WB = dict(ao_dist=2.2, ao_min=0.3, dirt_h=1.0, dirt=0.35)        # big masonry
PBW = dict(ao_dist=0.9, ao_min=0.34, dirt_h=0.4, dirt=0.3)       # props
ZW = 5.3            # wall-walk level of the curtain wall
WZC = [0.0, 0.9, 2.6, 3.9]
YF, YB = -1.0, 1.0  # curtain wall faces


# ----------------------------------------------------------------------------- curtain walls
def corbels(k, x0, x1, y, z, n, w=0.26, d=0.26, h=0.38, col=None):
    """Row of corbels under a projecting parapet (wall face at y, facing -Y)."""
    col = col or ST_D
    for i in range(n):
        x = lerp(x0, x1, (i + 0.5) / n)
        k.loft([(x - w / 2, y, z - h), (x + w / 2, y, z - h), (x + w / 2, y, z - h + 0.02), (x - w / 2, y, z - h + 0.02)],
               [(x - w / 2, y - d, z - 0.12), (x + w / 2, y - d, z - 0.12), (x + w / 2, y - d, z), (x - w / 2, y - d, z)],
               SB, col, caps=(False, True), skip=(2,))


def parapets(k, x0, x1, crenel_at, front_zt=None, back_zt=None, end_core=(False, False), back=True, bx1=None):
    """Projecting crenellated front parapet on corbels + plain rear parapet, from x0 to x1."""
    Lp = x1 - x0
    ops = [Op(c - x0, 0.8, ZW + 0.85, ZW + 0.85, None) for c in crenel_at]
    masonry(k, (x0, YF - 0.25), (x1, YF - 0.25), ZW, front_zt or (ZW + 1.7), 0.5, ops=ops, zc=[], ds=9,
            end_core=end_core, top_core=(lambda s: False) if front_zt is None else None)
    k.quad([(x0, YF - 0.25, ZW), (x1, YF - 0.25, ZW), (x1, YF, ZW), (x0, YF, ZW)], SB, mulc(ST, 0.6), nh=(0, 0, -1))
    corbels(k, x0, x1, YF, ZW, max(1, int(round(Lp / 0.5))))
    k.box((x0, YF - 0.06, ZW - 0.52), (x1, YF, ZW - 0.4), SB, ST_L, skip=('+y',))
    if back:
        bx1 = x1 if bx1 is None else bx1
        masonry(k, (bx1, YB), (x0, YB), ZW, back_zt or (ZW + 0.8), 0.35, zc=[], ds=9,
                end_core=(end_core[1], end_core[0]), top_core=False if back_zt is None else None)


def putlogs(k, xs, z, y=YF, s=0.16):
    for x in xs:
        k.quad([(x - s / 2, y - 0.012, z), (x + s / 2, y - 0.012, z), (x + s / 2, y - 0.012, z + s),
                (x - s / 2, y - 0.012, z + s)], SB, DARK, flag=NOAO, nh=(0, -1, 0))


def buttress_f(k, x, w, z1, d=0.35, y=YF, z0=-0.8):
    """Shallow pilaster buttress with a sloped head on the front face."""
    k.box((x - w / 2, y - d, z0), (x + w / 2, y, z1 - 0.5), SB, ST, skip=('+y', '-z', '+z'))
    k.loft([(x - w / 2, y - d, z1 - 0.5), (x + w / 2, y - d, z1 - 0.5), (x + w / 2, y, z1 - 0.5), (x - w / 2, y, z1 - 0.5)],
           [(x - w / 2, y - 0.03, z1), (x + w / 2, y - 0.03, z1), (x + w / 2, y, z1), (x - w / 2, y, z1)], SB, ST_L,
           caps=(False, False), skip=(2,))


@asset('castle_wall', 'Curtain wall segment, 8 m long (along X, tiles end to end), 2 m thick, wall-walk at 5.3 m, '
       'crenellated parapet on corbels to 7 m, battered base, outside = -Y', 900, footprint=[8.0, 2.8],
       bake=WB)
def castle_wall(k):
    masonry(k, (-4, YF), (4, YF), -0.8, ZW, 2.0, batter=(0.35, 1.8), zc=WZC, ds=1.34, top_core=False)
    parapets(k, -4, 4, [-4, -2, 0, 2, 4])
    buttress_f(k, 0.0, 1.3, 4.3, d=0.3)
    putlogs(k, (-2.9, -1.1, 1.3, 3.1), 3.55)
    proud_stones(k, Wall((-4, YF), (-0.7, YF), 0, 0), 4, 1.9, 4.6, seed=2)
    proud_stones(k, Wall((0.7, YF), (4, YF), 0, 0), 4, 1.9, 4.6, seed=5)
    proud_stones(k, Wall((4, YB), (-4, YB), 0, 0), 6, 0.4, 4.9, seed=7)
    w = Wall((-4, YF - 0.25), (4, YF - 0.25), 0, 0)
    for s in (3.0, 7.0):
        slit(k, w, s, ZW + 0.95, h=0.6, ww=0.09, frame=0)
    k.col('wall', (-4, YF - 0.2, -0.8), (4, YB, ZW))
    k.col('parapet_front', (-4, YF - 0.25, ZW), (4, YF + 0.25, ZW + 1.7))
    k.col('parapet_back', (-4, YB - 0.35, ZW), (4, YB, ZW + 0.8))
    k.walk('walk', (-4, YF + 0.25, ZW - 0.3), (4, YB - 0.35, ZW))
    k.person = (2.6, -2.2)


@asset('castle_wall_ruin_a', 'Ruined curtain wall, 8 m (along X): full height with parapet at the -X end, broken down '
       'in steps to 2 m at the +X end, rubble at its foot. Tiles with castle_wall (-X) and castle_wall_ruin_b (+X)',
       1200, footprint=[8.0, 5.0], bake=WB)
def castle_wall_ruin_a(k):
    zt = [(0, ZW), (1.7, ZW), (1.7, 4.7), (2.1, 4.45), (2.1, 3.95), (2.95, 4.2), (2.95, 3.3), (3.35, 3.1), (3.9, 3.55),
          (3.9, 2.8), (5.0, 3.1), (5.0, 2.3), (5.5, 1.95), (6.3, 2.5), (6.3, 1.75), (7.2, 2.2), (8, 2.0)]
    masonry(k, (-4, YF), (4, YF), -0.8, zt, 2.0, batter=(0.35, 1.8), zc=WZC, top_core=lambda s: s > 1.7,
            end_core=(False, True))
    proud_stones(k, Wall((-4, YF), (0.5, YF), 0, 0), 4, 1.9, 3.4, seed=3)
    proud_stones(k, Wall((4, YB), (-4, YB), 0, 0), 5, 0.4, 1.9, seed=4)
    parapets(k, -4, -2.2, [-4], front_zt=[(0, ZW + 1.7), (1.25, ZW + 1.7), (1.25, ZW + 1.05), (1.8, ZW + 0.5)],
             back_zt=[(0, ZW + 0.25), (0.5, ZW + 0.8), (1.7, ZW + 0.8)], end_core=(False, True), bx1=-2.3)
    putlogs(k, (-2.9, -1.1), 3.55)
    rubble(k, (1.6, -2.3, 0), (2.3, 1.3), 0.75, blocks=9, seed=3, bs=(0.4, 0.85))
    rubble(k, (2.6, 2.0, 0), (1.7, 1.0), 0.5, blocks=5, seed=5)
    block(k, (-1.2, -2.0, 0.22), (1.15, 0.5, 0.55), rz=0.4, rx=0.2, col=ST)
    block(k, (3.4, 0.1, 2.25), (0.8, 0.6, 0.4), rz=0.3, ry=0.25)
    block(k, (0.9, 0.3, 3.35), (0.7, 0.5, 0.4), rz=-0.5, rx=0.2)
    k.col('wall', (-4, YF - 0.2, -0.8), (4, YB, 3.2))
    k.col('wall_high', (-4, YF - 0.25, 3.2), (-1.4, YB, ZW + 1.7))
    k.person = (2.6, -3.9)


@asset('castle_wall_ruin_b', 'Ruined curtain wall, 8 m (along X): 2 m stump at the -X end, walkable breach '
       '(x = -1.7 .. 0.6) over a rubble ramp, rising back to full height with parapet at the +X end', 1200,
       footprint=[8.0, 6.0], bake=WB)
def castle_wall_ruin_b(k):
    zt = [(0, 2.0), (0.9, 2.45), (0.9, 1.6), (1.7, 1.25), (2.2, 0.45), (3.4, 0.3), (4.5, 0.42), (4.7, 1.5),
          (5.3, 2.3), (5.3, 3.3), (6.0, 3.7), (6.0, 4.6), (6.55, ZW), (8, ZW)]
    masonry(k, (-4, YF), (4, YF), -0.8, zt, 2.0, batter=(0.35, 1.8), zc=WZC, top_core=lambda s: s < 6.55,
            end_core=(True, False))
    proud_stones(k, Wall((1.6, YF), (4, YF), 0, 0), 3, 1.9, 4.4, seed=6)
    proud_stones(k, Wall((4, YB), (1.0, YB), 0, 0), 3, 0.4, 4.4, seed=8)
    parapets(k, 2.75, 4, [4], front_zt=[(0, ZW + 0.4), (0.35, ZW + 1.0), (0.35, ZW + 1.7), (1.25, ZW + 1.7)],
             back_zt=[(0, ZW + 0.8), (0.9, ZW + 0.8), (1.25, ZW + 0.3)], end_core=(True, False))
    putlogs(k, (3.1,), 3.55)
    # rubble ramp through the breach (walkable) + scattered blocks
    rock(k, (-0.55, 0.0, -0.1), (1.55, 2.9, 0.62), seed=4, nu=10, nv=3, mat=SW, col=mulc(CORE, 1.08), rough=0.2,
         zmin=0.0)
    rubble(k, (-2.6, -1.9, 0), (1.2, 0.9), 0.4, blocks=4, seed=2, heap=False)
    rubble(k, (1.5, -2.0, 0), (1.4, 1.0), 0.55, blocks=6, seed=8)
    rubble(k, (1.3, 1.9, 0), (1.3, 0.9), 0.45, blocks=4, seed=9)
    block(k, (-2.5, 1.7, 0.2), (0.9, 0.6, 0.45), rz=0.7, rx=0.15)
    block(k, (-0.9, -2.6, 0.12), (0.6, 0.45, 0.3), rz=1.1, ry=0.2)
    block(k, (0.1, 2.5, 0.12), (0.55, 0.4, 0.3), rz=0.3, rx=-0.2)
    k.col('left', (-4, YF - 0.2, -0.8), (-1.75, YB, 2.5))
    k.col('right', (0.65, YF - 0.2, -0.8), (4, YB, 4.0))
    k.col('right_high', (2.0, YF - 0.25, 4.0), (4, YB, ZW + 1.7))
    k.walk('breach_a', (-1.75, -2.6, -0.4), (0.65, 2.6, 0.2))
    k.walk('breach_b', (-1.75, -1.3, -0.2), (0.65, 1.3, 0.45))
    k.person = (-0.5, -0.2, 0.45)


# ----------------------------------------------------------------------------- stairs / slab / pillars / arch
@asset('castle_stairs', 'Stone stairs, 4 m wide (Y), rising 3 m over 6 m along +X (12 steps of 0.25 m), low side '
       'walls with sloped copings', 700, footprint=[6.0, 4.0], bake=WB,
       views=('front', 'right', (0.6, 0.7, -0.4), 'persp'))
def castle_stairs(k):
    n, rise, run = 12, 0.25, 0.5
    for i in range(n):
        x0 = -3 + i * run
        z = (i + 1) * rise
        wear = k.r(-0.012, 0.012)
        c = k.jit(ST, 0.05, 0.01)
        k.quad([(x0, -1.65, z + wear), (x0 + run, -1.65, z), (x0 + run, 1.65, z), (x0, 1.65, z - wear)], SB, c)
        k.quad([(x0, -1.65, z - rise), (x0, 1.65, z - rise), (x0, 1.65, z - wear), (x0, -1.65, z + wear)], SB,
               mulc(c, 0.9), nh=(-1, 0, 0))
    # side walls (string walls) with sloped top, 0.35 thick, 0.75 above the nosing line
    for sy in (-1, 1):
        y0, y1 = (-2.0, -1.65) if sy < 0 else (1.65, 2.0)
        a, b = ((-3, y0), (3, y0)) if sy < 0 else ((3, y1), (-3, y1))
        zt = [(0, 0.95), (6, 3.9)] if sy < 0 else [(0, 3.9), (6, 0.95)]
        masonry(k, a, b, -0.8, zt, 0.35, zc=[0.0, 1.2, 2.4], ds=2.0, top_core=False)
        # coping
        k.loft([(-3.06, y0 - 0.05, 0.93), (-3.06, y1 + 0.05, 0.93), (-3.06, y1 + 0.05, 1.05), (-3.06, y0 - 0.05, 1.05)],
               [(3.0, y0 - 0.05, 3.88), (3.0, y1 + 0.05, 3.88), (3.0, y1 + 0.05, 4.0), (3.0, y0 - 0.05, 4.0)],
               SB, ST_L)
    # back (high end) closing wall under the top landing edge + underside fill
    k.quad([(3, -1.65, -0.8), (3, 1.65, -0.8), (3, 1.65, 3.0), (3, -1.65, 3.0)], SB, ST, nh=(1, 0, 0))
    block(k, (-3.25, -1.2, 0.08), (0.45, 0.35, 0.22), rz=0.5, rx=0.2)
    block(k, (-0.4, 0.9, 1.4), (0.3, 0.24, 0.16), rz=0.9, ry=0.3)
    for i in range(n):
        x0 = -3 + i * run
        k.walk('step_%02d' % (i + 1), (x0, -1.65, (i + 1) * rise - 0.5), (x0 + run, 1.65, (i + 1) * rise))
    for sy, nm in ((-1, 'l'), (1, 'r')):
        y0, y1 = (-2.0, -1.65) if sy < 0 else (1.65, 2.0)
        for j in range(3):
            xa, xb = -3 + j * 2, -1 + j * 2
            k.col('side_%s%d' % (nm, j + 1), (xa, y0, -0.8), (xb, y1, 1.0 + (j + 1) * 1.0))
    k.person = (-3.9, -0.4)


@asset('floor_slab', 'Paved platform 8 x 8 m, 0.3 m thick: cracked, uneven flagstones on a rubble bed '
       '(skirt goes down to z = -0.6)', 300, footprint=[8.0, 8.0], bake=dict(ao_dist=0.5, ao_min=0.45, dirt=0),
       weather=dict(top=0.16, base=0.0, tint=0.14))
def floor_slab(k):
    k.box((-4, -4, -0.6), (4, 4, 0.255), SW, mulc(CORE, 0.55), skip=('-z',))
    xs = [-4.0, -2.45, -0.7, 0.85, 2.5, 4.0]
    ys = [-4.0, -2.3, -0.9, 0.8, 2.35, 4.0]
    g = 0.035
    for j in range(5):
        for i in range(5):
            if (i, j) == (4, 0):
                continue                                   # missing corner slab
            x0, x1 = xs[i] + (0 if i == 0 else g), xs[i + 1] - (0 if i == 4 else g)
            y0, y1 = ys[j] + (0 if j == 0 else g), ys[j + 1] - (0 if j == 4 else g)
            sh = k.r(-0.25, 0.25) if 0 < i < 4 else 0.0
            c = k.jit(mulc(ST, 0.97), 0.09, 0.015)
            sunk = -0.035 if (i, j) in ((1, 3), (3, 1)) else 0.0
            zz = [0.3 + sunk + (k.r(-0.012, 0.012) if 0 < i < 4 and 0 < j < 4 else 0.0) for _ in range(4)]
            pts = [(x0, y0, zz[0]), (x1, y0, zz[1]), (x1 + (sh if j < 4 and i < 4 else 0) * 0, y1, zz[2]),
                   (x0, y1, zz[3])]
            if (i, j) in ((2, 2), (0, 3), (3, 4)):       # cracked in two
                m0 = (lerp(x0, x1, 0.35), y0, zz[0])
                m1 = (lerp(x0, x1, 0.62), y1, zz[3])
                k.quad([pts[0], (m0[0] - g / 2, m0[1], m0[2]), (m1[0] - g / 2, m1[1], m1[2]), pts[3]], CB, c)
                k.quad([(m0[0] + g / 2, m0[1], m0[2] - 0.02), pts[1], pts[2], (m1[0] + g / 2, m1[1], m1[2] - 0.015)],
                       CB, mulc(c, 0.94))
            else:
                k.quad(pts, CB, c)
    # the broken corner: a tilted fragment + rubble bed
    k.quad([(2.55, -3.9, 0.277), (3.95, -3.95, 0.277), (3.95, -2.35, 0.277), (2.55, -2.35, 0.277)], SW,
           mulc(CORE, 0.8))
    k.quad([(2.7, -3.6, 0.3), (3.5, -3.75, 0.33), (3.6, -2.9, 0.39), (2.85, -2.7, 0.31)], CB, k.jit(ST, 0.08))
    # edge kerb faces
    for (a, b, nh) in (((-4, -4), (4, -4), (0, -1, 0)), ((4, -4), (4, 4), (1, 0, 0)), ((4, 4), (-4, 4), (0, 1, 0)),
                       ((-4, 4), (-4, -4), (-1, 0, 0))):
        k.quad([(a[0], a[1], 0.0), (b[0], b[1], 0.0), (b[0], b[1], 0.3), (a[0], a[1], 0.3)], SB, ST_D, nh=nh)
    k.walk('top', (-4, -4, -0.3), (4, 4, 0.3))
    k.person = (1.0, -1.0, 0.3)


def column(k, c=(0, 0, 0), h=6.0, r=0.3, n=8, cap=True, shaft_to=None, colonnettes=True):
    """Gothic pier: square plinth, moulded base, shaft with four attached colonnettes, bell capital + abacus."""
    x, y, z = c
    k.box((x - 0.5, y - 0.5, z - 0.3), (x + 0.5, y + 0.5, z + 0.3), SB, ST, skip=('-z',), taper=(0.96, 0.96))
    top = h - 1.05 if shaft_to is None else shaft_to
    prof = [(r * 1.55, 0.3), (r * 1.55, 0.38), (r * 1.3, 0.47), (r * 1.18, 0.52), (r * 1.1, 0.64), (r, 0.7),
            (r * 0.95, top)]
    k.lathe(c, prof, n=n, mat=SB, col=ST, split=(1, 3, 5), phase=PI / n)
    if colonnettes:
        for i in range(4):
            a = i * PI / 2
            k.cyl((x + math.cos(a) * r * 1.02, y + math.sin(a) * r * 1.02, z + 0.52),
                  (x + math.cos(a) * r * 0.98, y + math.sin(a) * r * 0.98, z + top), 0.085, n=4, mat=SB, col=ST_L,
                  caps=(False, False), phase=a)
    if cap:
        z0 = top
        prof = [(r * 0.95, z0), (r * 1.2, z0 + 0.05), (r * 1.2, z0 + 0.12), (r * 1.0, z0 + 0.17),
                (r * 1.12, z0 + 0.42), (r * 1.62, z0 + 0.68), (r * 1.62, z0 + 0.75)]
        k.lathe(c, prof, n=n, mat=SB, col=ST_L, split=(1, 2, 3, 5), phase=PI / n)
        k.box((x - 0.56, y - 0.56, z + z0 + 0.75), (x + 0.56, y + 0.56, z + z0 + 0.93), SB, ST, taper=(1.0, 1.0))
        k.box((x - 0.42, y - 0.42, z + z0 + 0.93), (x + 0.42, y + 0.42, z + h), SB, ST_D, skip=('-z',))


@asset('pillar', 'Gothic pier, 6 m: plinth, moulded base, octagonal shaft with four colonnettes, bell capital and '
       'abacus', 300, footprint=[1.2, 1.2], bake=PBW)
def pillar(k):
    column(k)
    k.col('pillar', (-0.45, -0.45, 0), (0.45, 0.45, 6.0))
    k.person = (1.0, -0.4)


@asset('pillar_broken', 'Broken pier: 2.5 m stump with a jagged top, fallen drums and a capital fragment', 350,
       footprint=[3.6, 3.0], bake=PBW)
def pillar_broken(k):
    column(k, cap=False, shaft_to=1.5, colonnettes=False)
    r = 0.285
    zt = [2.45, 2.3, 1.95, 1.75, 2.0, 2.2, 2.52, 2.4]
    ring_wall(k, (0, 0, 0), 8, [(r, 1.5), (r, 1.7), (r, 2.55)], th=r, zt=zt, zin=1.5, phase=PI / 8, mat=SB)
    # fallen drums
    for (p, rz, ln, rr) in (((1.25, -0.55, 0.27), 0.5, 0.95, 0.28), ((0.95, 0.75, 0.26), 2.2, 0.7, 0.27),
                            ((-1.2, 0.5, 0.25), 1.2, 0.55, 0.27)):
        d = V((math.cos(rz), math.sin(rz), 0.04))
        k.cyl(V(p) - d * ln / 2, V(p) + d * ln / 2, rr, rr * 0.98, n=8, mat=SB, col=k.jit(ST, 0.06, 0.01), cap_mat=SW,
              cap_col=CORE, phase=0.4)
    # capital fragment
    with k.at((-0.9, -0.95, 0.2), rx=1.25, rz=0.7):
        k.lathe((0, 0, -0.3), [(0.3, 0.0), (0.34, 0.25), (0.5, 0.5), (0.5, 0.58)], n=8, mat=SB, col=ST_L, split=(2,),
                cap0=True, cap1=False)
        k.box((-0.56, -0.56, 0.28), (0.56, 0.56, 0.45), SB, ST)
    rubble(k, (0.2, 0.9, 0), (0.7, 0.5), 0.25, blocks=3, seed=4, heap=False, bs=(0.18, 0.4))
    k.col('pillar', (-0.45, -0.45, 0), (0.45, 0.45, 2.5))
    k.person = (2.0, 0.6)


@asset('arch_ruin', 'Free-standing pointed arch from a vanished hall, 5 m high, 4 m wide passable opening (3.9 m '
       'headroom at the axis), broken wall stubs, buttresses', 500, footprint=[6.6, 2.4], bake=WB)
def arch_ruin(k):
    op = Op(3.2, 4.0, -0.7, 2.45, 4.2, n=4)
    zt = [(0, 3.1), (0.55, 3.45), (0.55, 4.5), (1.5, 4.95), (2.9, 5.0), (3.7, 4.75), (4.5, 4.8), (4.5, 4.3),
          (5.0, 4.1), (5.0, 3.5), (5.7, 3.3), (5.7, 2.5), (6.4, 2.8)]
    w = masonry(k, (-3.2, -0.45), (3.2, -0.45), -0.7, zt, 0.9, ops=[op], zc=[0.0, 1.2], ds=9, end_core=(True, True))
    archivolt(k, w, op, band=0.24, proud=0.07, jambs=False)
    archivolt(k, w, op, band=0.24, proud=0.07, jambs=False, side=-1, th=0.9)
    for sx, zb in ((-1, 3.0), (1, 2.3)):
        for sy in (-1, 1):
            x = sx * 2.72
            y0, y1 = (-0.95, -0.45) if sy < 0 else (0.45, 0.95)
            k.box((x - 0.36, y0, -0.7), (x + 0.36, y1, zb - 0.6), SB, ST, skip=('-z', '+y' if sy < 0 else '-y', '+z'))
            yo, yi = (y0, y1) if sy < 0 else (y1, y0)
            k.loft([(x - 0.36, y0, zb - 0.6), (x + 0.36, y0, zb - 0.6), (x + 0.36, y1, zb - 0.6), (x - 0.36, y1, zb - 0.6)],
                   [(x - 0.36, yi - 0.02 * sy, zb), (x + 0.36, yi - 0.02 * sy, zb), (x + 0.36, yi, zb),
                    (x - 0.36, yi, zb)] if sy < 0 else
                   [(x - 0.36, yi, zb), (x + 0.36, yi, zb), (x + 0.36, yi + 0.02, zb), (x - 0.36, yi + 0.02, zb)],
                   SB, ST_L, caps=(False, False))
    # impost blocks at the springing
    for sx in (-1, 1):
        k.box((sx * 2.0 - 0.14, -0.53, 2.3), (sx * 2.0 + 0.14, 0.53, 2.47), SB, ST_L)
    rubble(k, (2.9, -1.5, 0), (1.0, 0.7), 0.4, blocks=5, seed=6)
    block(k, (-2.2, 1.6, 0.15), (0.7, 0.45, 0.35), rz=0.6, rx=0.2)
    k.col('left', (-3.2, -0.95, -0.7), (-2.0, 0.95, 4.6))
    k.col('right', (2.0, -0.95, -0.7), (3.2, 0.95, 4.2))
    k.person = (0.6, -0.9)


@asset('brazier_stone', 'Ceremonial stone brazier, 1.6 m: octagonal stepped foot, stem, wide carved bowl with '
       'glowing coals', 400, footprint=[1.6, 1.6], bake=PBW)
def brazier_stone(k):
    prof = [(0.6, 0.0), (0.6, 0.16), (0.47, 0.16), (0.47, 0.3), (0.3, 0.42), (0.21, 0.55), (0.19, 0.95), (0.3, 1.08),
            (0.62, 1.2), (0.74, 1.42), (0.74, 1.58), (0.64, 1.58), (0.58, 1.5), (0.0, 1.47)]
    k.lathe((0, 0, 0), prof, n=8, mat=SB, col=ST, split=(1, 2, 3, 7, 8, 9, 10, 11, 12), phase=PI / 8,
            colfn=lambda i, r, z: PAL['soot'] if i >= 11 else (mulc(ST, 0.8) if i >= 10 else ST))
    k.soot.append((V((0, 0, 1.6)), 0.75, 0.6))
    # carved rune band on the bowl (ember tint)
    for i in range(8):
        a0, a1 = PI / 8 + i * PI / 4, PI / 8 + (i + 1) * PI / 4
        p = [V((math.cos(a) * 0.74, math.sin(a) * 0.74, 0)) for a in (a0, a1)]
        pan = Panel(p[0] + V((0, 0, 1.42)), p[1] + V((0, 0, 1.42)), p[1] + V((0, 0, 1.58)), p[0] + V((0, 0, 1.58)))
        if i % 2 == 0:
            glyph(k, pan, GLYPH_SEQ[(i * 3) % 12], 0.5, 0.5, size=0.11, col=RUNE_E, w=0.018, off=0.012)
    # coals
    k.quad([(0.56 * math.cos(a), 0.56 * math.sin(a), 1.49) for a in [2 * PI * j / 8 + PI / 8 for j in range(8)]],
           'M_ember', mulc(EMB, 0.85), flag=NOAO)
    for i in range(7):
        a = i * 0.9
        rr = 0.12 + 0.3 * ((i * 37) % 10) / 10
        em = i % 3 != 2
        k.blob((rr * math.cos(a), rr * math.sin(a), 1.5), (0.12, 0.1, 0.085), nu=5, nv=2,
               mat='M_ember' if em else RK, col=(EMB_H if i % 2 else EMB) if em else PAL['dark'], zmin=0.0,
               flag=NOAO if em else 0)
    k.empty('FIRE_main', (0, 0, 1.62))
    k.col('brazier', (-0.55, -0.55, 0), (0.55, 0.55, 1.6))
    k.person = (1.1, -0.5)
