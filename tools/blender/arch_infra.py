"""VALOMBRE settlements pack - fences, walls, palisade, cart, dock, boat and bridges (uses arch_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *
from arch_props import rock, PB

S, W, I, C = 'M_stone_wall', 'M_wood_planks', 'M_metal_iron', 'M_cloth'
PINE = 'M_bark_pine'


# ----------------------------------------------------------------------------- fences & walls (run along X)
@asset('fence_wood', '3 m post-and-rail fence segment (centred, runs along X, tiles end to end)', 120,
       footprint=[3.0, 0.4], bake=PB)
def fence_wood(k):
    for x in (-0.75, 0.75):
        k.box((x - 0.06, -0.055, 0), (x + 0.06, 0.055, 1.12 + k.r(0, 0.08)), W, k.jit(PAL['beam_l']), skip=('-z',),
              taper=(0.72, 0.72), uv='along', shift=(k.r(-0.02, 0.02), 0))
    for z in (0.3, 0.62, 0.95):
        for (xa, xb, sy) in ((-1.5, 0.12, -1), (-0.12, 1.5, 1)):
            dz = k.r(-0.03, 0.03)
            k.beam((xa, sy * 0.075, z + (0 if abs(xa) > 1 else dz)), (xb, sy * 0.075, z + (0 if abs(xb) > 1 else dz)),
                   0.035, 0.1, W, k.jit(PAL['plank'], 0.12), up=(0, 0, 1))
    k.col('fence', (-1.5, -0.1, 0), (1.5, 0.1, 1.1))
    k.person = (0.2, -0.6)


@asset('fence_wattle', '3 m woven wattle fence segment (centred, runs along X, tiles end to end)', 300,
       footprint=[3.0, 0.4], bake=PB)
def fence_wattle(k):
    xs = [-1.5 + 0.1875 + i * 0.375 for i in range(8)]
    for i, x in enumerate(xs):
        k.cyl((x, 0, 0), (x + k.r(-0.02, 0.02), 0, 1.12 + k.r(0, 0.1)), 0.03, 0.022, n=4, mat=W, col=PAL['beam_l'],
              caps=(False, True), phase=k.r(0, 1))
    cols_x = [-1.5] + xs + [1.5]
    wc = lin('#8a7052')
    nb = 5
    for b in range(nb):
        z0 = 0.08 + b * 0.19
        rows = [[], []]
        for c, x in enumerate(cols_x):
            end = c in (0, len(cols_x) - 1)
            y = 0.0 if end else 0.042 * (1 if (c + b) % 2 else -1)
            dz = 0.0 if end else k.r(-0.012, 0.012)
            rows[0].append((x, y, z0 + dz))
            rows[1].append((x, y, z0 + 0.18 + dz))
        cc = k.jit(wc, 0.12)
        k.grid(rows, 'M_rope', cc, double=True, smooth=True, flip=True, back_col=cc)
    k.col('fence', (-1.5, -0.08, 0), (1.5, 0.08, 1.05))
    k.person = (0.2, -0.6)


@asset('stone_wall_low', '4 m dry-stone field wall, 1 m high (centred, runs along X, tiles end to end)', 250,
       footprint=[4.0, 0.8], bake=dict(ao_dist=0.5, dirt_h=0.3, dirt=0.3))
def stone_wall_low(k):
    xs = [-2.0, -1.0, 0.0, 1.0, 2.0]

    def ring(x, j):
        w0, w1, w2, h = 0.31, 0.25, 0.17, 0.9
        if j:
            w0 += k.r(-0.03, 0.03)
            w1 += k.r(-0.03, 0.03)
            h += k.r(-0.05, 0.05)
        return [(x, -w0, 0), (x, w0, 0), (x, w1, h * 0.6), (x, w2, h), (x, 0, h + 0.04), (x, -w2, h), (x, -w1, h * 0.6)]
    rings = [ring(x, 0 < i < len(xs) - 1) for i, x in enumerate(xs)]
    for i in range(len(xs) - 1):
        k.loft(rings[i], rings[i + 1], S, k.jit(PAL['stone'], 0.04, 0), caps=(i == 0, i == len(xs) - 2), skip=(0,))
    for i in range(9):
        x = -1.78 + i * 0.445 + k.r(-0.04, 0.04)
        with k.at((x, k.r(-0.03, 0.03), 0.9 + k.r(-0.02, 0.02)), rz=k.r(-0.25, 0.25), ry=k.r(-0.08, 0.08)):
            k.box((-0.2, -0.19, 0), (0.2, 0.19, k.r(0.08, 0.13)), S, k.jit(mulc(PAL['stone'], 0.95), 0.08, 0),
                  skip=('-z',), taper=(0.85, 0.85))
    for i in range(8):
        sy = 1 if i % 2 else -1
        x = -1.7 + i * 0.47 + k.r(-0.1, 0.1)
        z = k.r(0.12, 0.6)
        yy = lerp(0.31, 0.25, z / 0.54) if z < 0.54 else 0.25
        with k.at((x, sy * (yy - 0.02), z), rz=k.r(-0.1, 0.1)):
            k.cbox((0, 0, 0), (k.r(0.28, 0.45), 0.1, k.r(0.14, 0.22)), S, k.jit(mulc(PAL['stone'], 0.93), 0.07, 0),
                   skip=('+y',) if sy < 0 else ('-y',))
    k.col('wall', (-2.0, -0.3, 0), (2.0, 0.3, 0.98))
    k.person = (0.3, -0.9)


def pale(k, x, y, h, r, n=7, lean=(0.0, 0.0), tip=0.4):
    """One sharpened log."""
    top = (x + lean[0], y + lean[1], h - tip)
    k.cyl((x, y, 0), top, r, r * 0.9, n=n, mat=PINE, col=k.jit(PAL['bark'], 0.1), caps=(False, False),
          phase=k.r(0, 1))
    k.cyl(top, (top[0] + k.r(-0.02, 0.02), top[1], h), r * 0.9, 0.0, n=n, mat=W, col=k.jit(PAL['plank_l'], 0.1),
          caps=(False, False), phase=0)


@asset('palisade', '4 m palisade segment of sharpened logs, 3.2 m high (centred, runs along X, tiles end to end)',
       500, footprint=[4.0, 0.7], bake=dict(ao_dist=0.8, dirt_h=0.5, dirt=0.35))
def palisade(k):
    n = 14
    for i in range(n):
        x = -2.0 + (i + 0.5) * 4.0 / n
        pale(k, x, k.r(-0.025, 0.025), 3.2 + k.r(-0.14, 0.14), 0.147 * k.r(0.92, 1.03),
             lean=(k.r(-0.02, 0.02), k.r(-0.03, 0.03)))
    for z in (0.95, 2.45):
        k.beam((-2.0, 0.19, z), (2.0, 0.19, z), 0.16, 0.1, W, k.jit(PAL['beam']), up=(0, 1, 0))
    k.col('wall', (-2.0, -0.17, 0), (2.0, 0.25, 3.2))
    k.person = (0.4, -0.8)


@asset('palisade_gate', '6 m palisade gate: log flanks, big posts and lintel, plank doors swung open inwards '
       '(3 m clear opening), fighting platform above with ladder', 1200, footprint=[6.0, 3.2],
       bake=dict(ao_dist=1.0, dirt_h=0.5, dirt=0.35))
def palisade_gate(k):
    zl, zw = 3.45, 3.64                # lintel centre, walkway top
    # flanking logs
    for sg in (-1, 1):
        for i in range(4):
            x = sg * (1.88 + 0.16 + i * 0.31)
            pale(k, x, k.r(-0.02, 0.02), 4.7 + k.r(-0.12, 0.12), 0.158 * k.r(0.94, 1.02),
                 lean=(k.r(-0.015, 0.015), k.r(-0.02, 0.02)))
        k.box((sg * 1.5, -0.2, 0), (sg * 1.86, 0.2, 4.35), W, k.jit(PAL['beam']), skip=('-z',), uv='along')
        k.beam((sg * 1.5, 0.0, zl - 0.85), (sg * 0.72, 0.0, zl - 0.14), 0.16, 0.16, W, k.jit(PAL['beam']),
               up=(0, 1, 0))
    k.beam((-2.0, 0, zl), (2.0, 0, zl), 0.36, 0.34, W, k.jit(PAL['beam']), up=(0, 0, 1))
    # parapet over the opening
    for i in range(10):
        x = -1.5 + (i + 0.5) * 0.3
        top = 4.75 + k.r(-0.1, 0.1)
        k.cyl((x, -0.06, zl + 0.17), (x, -0.06, top - 0.35), 0.148, 0.135, n=6, mat=PINE, col=k.jit(PAL['bark'], 0.1),
              caps=(False, False), phase=k.r(0, 1))
        k.cyl((x, -0.06, top - 0.35), (x, -0.06, top), 0.135, 0.0, n=6, mat=W, col=k.jit(PAL['plank_l'], 0.1),
              caps=(False, False))
    # walkway behind
    k.boards((3.0, 0.12, zw - 0.06), (0, 1, 0), (-1, 0, 0), 1.35, 6.0, 10, thick=0.06, skip=(), col=PAL['plank'],
             lj=0.04)
    k.beam((-3.0, 1.35, zw - 0.15), (3.0, 1.35, zw - 0.15), 0.14, 0.18, W, k.jit(PAL['beam']))
    for sg in (-1, 1):
        k.box((sg * 2.7 - 0.09, 1.26, 0), (sg * 2.7 + 0.09, 1.44, zw - 0.24), W, k.jit(PAL['beam']), skip=('-z',),
              uv='along')
        k.beam((sg * 2.7, 1.35, zw - 1.0), (sg * 1.95, 1.35, zw - 0.24), 0.1, 0.1, W, k.jit(PAL['beam_l']),
               up=(0, 1, 0), skip=('c0', 'c1'))
        k.beam((sg * 2.7, 0.2, zw - 0.2), (sg * 2.7, 1.35, zw - 0.2), 0.1, 0.12, W, k.jit(PAL['beam']),
               skip=('c0', 'c1'))
    for x in (-2.9, -1.0, 1.0):
        k.box((x - 0.04, 1.36, zw), (x + 0.04, 1.44, zw + 1.0), W, k.jit(PAL['beam_l']), skip=('-z',), uv='along')
    k.beam((-3.0, 1.4, zw + 0.98), (1.05, 1.4, zw + 0.98), 0.07, 0.07, W, k.jit(PAL['beam_l']))
    # ladder (back right)
    for xx in (1.45, 1.95):
        k.beam((xx, 2.75, 0), (xx, 1.47, zw + 0.75), 0.05, 0.08, W, k.jit(PAL['plank']), up=(0, 1, 0.3))
    for i in range(9):
        f = (i + 0.8) / 11.0
        k.beam((1.45, lerp(2.75, 1.47, f), (zw + 0.75) * f), (1.95, lerp(2.75, 1.47, f), (zw + 0.75) * f), 0.045,
               0.045, W, k.jit(PAL['plank_d']), skip=('c0', 'c1'))
    # door leaves, swung open inwards
    for sg, ang in ((1, math.radians(78)), (-1, math.radians(102))):
        with k.at((sg * 1.5, 0.24, 0), rz=ang):
            k.boards((0.0, -0.035, 0.08), (0, 0, 1), (1, 0, 0), 3.22, 1.48, 6, thick=0.07, skip=(), col=PAL['plank'],
                     lj=0.03)
            side = -0.045 if sg > 0 else 0.045
            for zz in (0.5, 1.7, 2.9):
                k.beam((0.03, side, zz), (1.45, side, zz), 0.16, 0.05, W, k.jit(PAL['beam']), up=(0, sg * -1, 0),
                       skip=('-u',))
            k.beam((0.08, side, 0.62), (1.4, side, 1.58), 0.13, 0.045, W, k.jit(PAL['beam']), up=(0, sg * -1, 0),
                   skip=('-u',))
            for zz in (0.9, 2.5):
                k.beam((-0.02, -side * 0.9, zz), (0.8, -side * 0.9, zz), 0.07, 0.02, I, PAL['iron'],
                       up=(0, sg * 1, 0), skip=('-u',), uv='box')
    k.empty('ANCHOR_npc', (0.0, 0.75, zw))
    k.walk('walkway', (-3.0, 0.12, zw - 0.2), (3.0, 1.47, zw))
    k.col('left', (-3.0, -0.25, 0), (-1.5, 1.8, 4.7))
    k.col('right', (1.5, -0.25, 0), (3.0, 1.8, 4.7))
    k.person = (0.6, -0.9)


# ----------------------------------------------------------------------------- cart
def wheel(k, c, r=0.55, n=10):
    """Spoked cart wheel, axle along X."""
    with k.at(c, ry=PI / 2):
        t = 0.04
        k.lathe((0, 0, 0), [(r, -t), (r, t), (r - 0.09, t), (r - 0.09, -t), (r, -t)], n=n, mat=W, col=PAL['plank'],
                smooth=False, colfn=lambda i, rr, zz: PAL['iron'] if i in (0, 1, 4) else PAL['plank'])
        k.cyl((0, 0, -0.11), (0, 0, 0.11), 0.095, 0.08, n=6, mat=W, col=PAL['beam'])
        for i in range(6):
            a = 2 * PI * i / 6 + 0.3
            k.beam((0.08 * math.cos(a), 0.08 * math.sin(a), 0), ((r - 0.08) * math.cos(a), (r - 0.08) * math.sin(a), 0),
                   0.05, 0.04, W, k.jit(PAL['plank']), up=(0, 0, 1), skip=('c0', 'c1'))


@asset('cart', 'Two-wheeled farm cart resting on its shafts, loaded with sacks, a crate and hay', 900,
       footprint=[1.9, 4.2], bake=dict(ao_dist=0.6, dirt_h=0.4, dirt=0.3))
def cart(k):
    az, ay = 0.55, 0.15
    wheel(k, (-0.74, ay, az))
    wheel(k, (0.74, ay, az))
    k.cyl((-0.86, ay, az), (0.86, ay, az), 0.045, n=5, mat=W, col=PAL['beam'])
    th = math.radians(12.5)
    with k.at((0, ay, az), rx=th):
        zb = 0.16                                   # bed floor (local)
        k.box((-0.55, -1.1, zb), (0.55, 1.0, zb + 0.05), W, PAL['plank'], uv='box')
        for sx in (-1, 1):
            k.beam((sx * 0.5, -1.1, zb - 0.06), (sx * 0.5, 1.0, zb - 0.06), 0.08, 0.1, W, k.jit(PAL['beam']))
            k.beam((sx * 0.57, -1.12, zb + 0.5), (sx * 0.57, 1.02, zb + 0.5), 0.05, 0.06, W, k.jit(PAL['beam_l']))
            k.box((sx * 0.57 - 0.012, -1.08, zb + 0.05), (sx * 0.57 + 0.012, 0.98, zb + 0.33), W,
                  k.jit(PAL['plank'], 0.1), uv='swap', skip=('-z',))
            for yy in (-1.05, -0.35, 0.35, 0.95):
                k.beam((sx * 0.6, yy, zb - 0.1), (sx * 0.6, yy, zb + 0.5), 0.045, 0.045, W, k.jit(PAL['beam_l']),
                       skip=('c1',))
            # shafts
            k.beam((sx * 0.42, -1.1, zb - 0.04), (sx * 0.36, -2.95, zb + 0.02), 0.07, 0.08, W, k.jit(PAL['beam_l']),
                   taper=0.8)
        k.box((-0.55, 0.97, zb + 0.05), (0.55, 1.0, zb + 0.42), W, k.jit(PAL['plank']), uv='swap', skip=('-z',))
        k.box((-0.55, -1.1, zb + 0.05), (0.55, -1.07, zb + 0.3), W, k.jit(PAL['plank']), uv='swap', skip=('-z',))
        k.beam((-0.4, -2.8, zb + 0.01), (0.4, -2.8, zb + 0.01), 0.05, 0.05, W, k.jit(PAL['beam_l']))
        # load
        sack(k, (-0.22, 0.55, zb + 0.05), r=0.25, h=0.52, n=5)
        sack(k, (0.22, 0.2, zb + 0.05), r=0.24, h=0.5, rz=1.0, n=5)
        crate(k, (-0.2, -0.45, zb + 0.05), (0.5, 0.45, 0.36), rz=0.15, slats=False)
        k.blob((0.2, -0.6, zb + 0.05), (0.32, 0.4, 0.26), nu=6, nv=2, mat='M_thatch', col=PAL['hay'], zmin=0.0)
    k.col('cart', (-0.8, -1.1, 0), (0.8, 1.3, 1.25))
    k.person = (1.5, -0.6)


# ----------------------------------------------------------------------------- dock & boat
@asset('dock', '6 x 2.4 m pier segment on four piles (runs along X, tiles end to end), deck top at z = 0.9, '
       'piles reach 1.8 m below the origin', 500, footprint=[6.0, 2.6],
       bake=dict(ao_dist=0.7, dirt_h=0.3, dirt=0.0, ground=False), ground_low=True)
def dock(k):
    zt = 0.9
    k.boards((3.0, -1.2, zt - 0.06), (0, 1, 0), (-1, 0, 0), 2.4, 6.0, 12, thick=0.06, skip=(), col=PAL['plank'],
             lj=0.06)
    for sy in (-1, 1):
        k.beam((-3.0, sy * 0.88, zt - 0.17), (3.0, sy * 0.88, zt - 0.17), 0.14, 0.2, W, k.jit(PAL['beam']))
    for x in (-1.5, 1.5):
        for sy in (-1, 1):
            tall = (x > 0) == (sy < 0)
            k.cyl((x, sy * 1.08, -1.8), (x + k.r(-0.03, 0.03), sy * 1.08, zt + (0.5 if tall else 0.12)), 0.12, 0.1,
                  n=6, mat=PINE, col=PAL['bark'], caps=(False, True), cap_mat=W, cap_col=PAL['plank_l'])
        k.beam((x, -1.25, zt - 0.35), (x, 1.25, zt - 0.35), 0.16, 0.16, W, k.jit(PAL['beam']))
        k.beam((x, -1.05, -0.5), (x, 1.05, zt - 0.5), 0.06, 0.1, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
        k.beam((x, 1.05, -0.5), (x, -1.05, zt - 0.5), 0.06, 0.1, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    # mooring rope + coil
    k.lathe((1.5, -1.08, 0), [(0.125, zt + 0.2), (0.135, zt + 0.25), (0.125, zt + 0.3)], n=6, mat='M_rope',
            col=PAL['rope'])
    k.lathe((-2.2, 0.6, zt), [(0.2, 0.0), (0.27, 0.045), (0.2, 0.09), (0.13, 0.045), (0.2, 0.0)], n=8, mat='M_rope',
            col=PAL['rope'])
    k.walk('deck', (-3.0, -1.2, 0.5), (3.0, 1.2, zt))
    k.person = (0.5, 0.2, 0.9)


@asset('rowboat', 'Clinker-style rowing boat with three thwarts and a pair of oars (keel at z = 0, waterline '
       '~0.22)', 500, footprint=[1.6, 4.0], bake=dict(ao_dist=0.5, dirt_h=0.2, dirt=0.15))
def rowboat(k):
    ys = [-1.95, -1.5, -0.8, 0.0, 0.8, 1.45, 1.75]
    hb = [0.0, 0.33, 0.6, 0.68, 0.62, 0.5, 0.42]
    gz = [0.74, 0.62, 0.52, 0.48, 0.5, 0.55, 0.58]
    kz = [0.4, 0.08, 0.0, 0.0, 0.02, 0.1, 0.18]
    col = PAL['plank']

    def sect(i, inner):
        b, g, kk, y = hb[i], gz[i], kz[i], ys[i]
        if inner:
            b = max(0.0, b - 0.035)
            kk += 0.035
            y = y + (0.04 if i == 0 else (-0.03 if i == len(ys) - 1 else 0))
        pts = [(-b, y, g), (-b * 0.93, y, kk + (g - kk) * 0.5), (-b * 0.6, y, kk + (g - kk) * 0.13), (0, y, kk),
               (b * 0.6, y, kk + (g - kk) * 0.13), (b * 0.93, y, kk + (g - kk) * 0.5), (b, y, g)]
        return pts
    outer = [sect(i, False) for i in range(len(ys))]
    inner = [sect(i, True) for i in range(len(ys))]
    k.grid(outer, W, col, smooth=True, flip=True, uv='swap', colfn=lambda p: mulc(col, 0.75 + 0.5 * clamp(p.z)))
    k.grid(inner, W, mulc(col, 0.8), smooth=True, uv='swap')
    for i in range(len(ys) - 1):
        for sd in (0, 6):
            a, b = outer[i][sd], outer[i + 1][sd]
            c, d = inner[i + 1][sd], inner[i][sd]
            k.quad([a, b, c, d], W, k.jit(PAL['beam_l']), nh=(0, 0, 1))
    # transom
    k.quad(outer[-1], W, mulc(col, 0.9), nh=(0, 1, 0))
    k.quad(inner[-1], W, mulc(col, 0.75), nh=(0, -1, 0))
    k.quad([outer[-1][0], outer[-1][6], inner[-1][6], inner[-1][0]], W, PAL['beam_l'], nh=(0, 0, 1))
    # stem + keel
    k.beam((0, -1.97, 0.36), (0, -2.02, 0.86), 0.05, 0.07, W, k.jit(PAL['beam']), up=(0, 1, 0))
    k.beam((0, -1.5, 0.06), (0, 1.75, 0.16), 0.04, 0.05, W, k.jit(PAL['beam']), skip=('+u',))
    # thwarts
    for (y, hbw, z) in ((-0.95, 0.5, 0.36), (0.1, 0.63, 0.33), (1.15, 0.5, 0.38)):
        k.box((-hbw, y - 0.11, z), (hbw, y + 0.11, z + 0.03), W, k.jit(PAL['plank_l']), uv='swap')
    # oars
    for sx in (-1, 1):
        a, b = V((sx * 0.3, -1.1, 0.42)), V((sx * 0.42, 1.25, 0.47))
        k.cyl(a, b, 0.022, n=4, mat=W, col=PAL['beam_l'])
        d = (b - a).normalized()
        k.beam(b, b + d * 0.5, 0.13, 0.02, W, k.jit(PAL['plank_l']), up=(0, 0, 1), taper=1.15)
        k.box((sx * 0.6 - 0.03, 0.28, 0.48), (sx * 0.6 + 0.03, 0.36, 0.56), W, k.jit(PAL['beam']), skip=('-z',))
    k.col('boat', (-0.68, -1.95, 0), (0.68, 1.75, 0.6))
    k.person = (1.3, -0.5)


# ----------------------------------------------------------------------------- bridges (span along X)
@asset('bridge_wood', 'Plank bridge: 10 m deck (3 m wide, top at z = 1.0) on three pile bents with railings, plus '
       '2.5 m ramps down to z = 0 at both ends (total length 15 m); walk direction = X', 900, footprint=[15.0, 3.4],
       bake=dict(ao_dist=0.8, dirt_h=0.3, dirt=0.0, ground=False), ground_low=True)
def bridge_wood(k):
    zt, hw = 1.0, 1.5
    k.boards((5.0, -hw - 0.05, zt - 0.06), (0, 1, 0), (-1, 0, 0), 2 * hw + 0.1, 10.0, 20, thick=0.06, col=PAL['plank'],
             lj=0.06)
    k.quad([(-5, -hw, zt - 0.06), (-5, hw, zt - 0.06), (5, hw, zt - 0.06), (5, -hw, zt - 0.06)], W, PAL['plank_d'],
           nh=(0, 0, -1))
    for y in (-1.2, 0.0, 1.2):
        k.beam((-5.0, y, zt - 0.17), (5.0, y, zt - 0.17), 0.16, 0.22, W, k.jit(PAL['beam']))
    for x in (-4.85, 0.0, 4.85):
        for sy in (-1, 1):
            k.cyl((x, sy * 1.25, -2.2), (x, sy * 1.25, zt - 0.3), 0.13, 0.115, n=6, mat=PINE, col=PAL['bark'],
                  caps=(False, False))
        k.beam((x, -1.6, zt - 0.36), (x, 1.6, zt - 0.36), 0.18, 0.16, W, k.jit(PAL['beam']))
        k.beam((x, -1.2, -0.7), (x, 1.2, zt - 0.5), 0.07, 0.1, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
        k.beam((x, 1.2, -0.7), (x, -1.2, zt - 0.5), 0.07, 0.1, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    # ramps
    run, th = 2.5, math.atan2(1.0, 2.5)
    Ls = math.hypot(run, zt)
    for sg in (-1, 1):
        M = Matrix.Translation((sg * 5.0, 0, zt))
        if sg < 0:
            M = M @ Matrix.Rotation(PI, 4, 'Z')
        M = M @ Matrix.Rotation(th, 4, 'Y')
        with k.xf(M):
            k.boards((Ls + 0.05, -hw - 0.05, -0.06), (0, 1, 0), (-1, 0, 0), 2 * hw + 0.1, Ls + 0.05, 5, thick=0.06,
                     col=PAL['plank'], lj=0.06)
            for y in (-1.2, 1.2):
                k.beam((0, y, -0.16), (Ls, y, -0.16), 0.14, 0.2, W, k.jit(PAL['beam']))
        # ramp railing
        for sy in (-1, 1):
            k.box((sg * 7.3 - 0.05, sy * 1.42 - 0.05, 0), (sg * 7.3 + 0.05, sy * 1.42 + 0.05, 1.12), W,
                  k.jit(PAL['beam_l']), skip=('-z',), uv='along')
            k.beam((sg * 5.0, sy * 1.42, zt + 0.95), (sg * 7.38, sy * 1.42, 1.05), 0.07, 0.08, W,
                   k.jit(PAL['beam_l']))
    for sy in (-1, 1):
        for x in (-5.0, -1.67, 1.67, 5.0):
            k.box((x - 0.055, sy * 1.42 - 0.055, zt - 0.3), (x + 0.055, sy * 1.42 + 0.055, zt + 1.02), W,
                  k.jit(PAL['beam_l']), skip=('-z',), uv='along')
        k.beam((-5.08, sy * 1.42, zt + 0.95), (5.08, sy * 1.42, zt + 0.95), 0.07, 0.08, W, k.jit(PAL['beam_l']))
        k.beam((-5.0, sy * 1.42, zt + 0.5), (5.0, sy * 1.42, zt + 0.5), 0.05, 0.07, W, k.jit(PAL['beam_l']),
               skip=('c0', 'c1'))
    k.walk('deck', (-5.0, -hw, 0.5), (5.0, hw, zt))
    for sg, nm in ((-1, 'w'), (1, 'e')):
        for i in range(4):
            xa, xb = 5.0 + i * run / 4, 5.0 + (i + 1) * run / 4
            top = zt - 0.125 - 0.25 * i
            k.walk('ramp_%s%d' % (nm, i), (min(sg * xa, sg * xb), -hw, -0.3), (max(sg * xa, sg * xb), hw, top))
    for sy, nm in ((-1, 's'), (1, 'n')):
        k.col('rail_' + nm, (-7.4, sy * 1.42 - 0.07, 0), (7.4, sy * 1.42 + 0.07, 2.0))
    k.person = (0.5, 0.0, 1.0)


@asset('bridge_stone', 'Single-arch humpback stone bridge, 14 m long, 4 m wide, deck peak 2.2 m, cobbled deck '
       'between 0.85 m parapets; arch springs 0.6 m below the origin; walk direction = X', 1500,
       footprint=[14.0, 4.4], bake=dict(ao_dist=1.2, dirt_h=0.4, dirt=0.25, ground=False), ground_low=True)
def bridge_stone(k):
    HW, HI, PH, ZB = 2.0, 1.65, 0.85, -0.6
    AW = 3.2

    def zd(x):
        return 2.2 * math.cos(PI * x / 14.0) ** 2

    def za(x):
        return ZB + 2.2 * math.sqrt(max(0.0, 1.0 - (x / AW) ** 2))
    xs = [-7, -6, -5, -4, -AW, -2.6, -1.8, -0.9, 0, 0.9, 1.8, 2.6, AW, 4, 5, 6, 7]
    st = PAL['stone']
    n = len(xs)
    for sy in (-1, 1):
        yo, yi = sy * HW, sy * HI
        bot = [(x, yo, za(x) if abs(x) < AW else ZB) for x in xs]
        mid = [(x, yo, zd(x)) for x in xs]
        top = [(x, yo, zd(x) + PH) for x in xs]
        k.grid([bot, mid, top], S, st, smooth=False, flip=(sy > 0),
               colfn=lambda p: mulc(st, 0.92 + 0.08 * mnoise.noise(p * 0.6)))
        tin = [(x, yi, zd(x) + PH) for x in xs]
        k.grid([top, tin], S, mulc(PAL['stone_w'], 0.98), smooth=True, flip=(sy > 0))
        din = [(x, yi, zd(x) - 0.02) for x in xs]
        k.grid([tin, din], S, st, smooth=False, flip=(sy > 0))
        # parapet end caps + corner pillars
        for sx in (-1, 1):
            x = sx * 7.0
            k.quad([(x, yo, ZB), (x, yi, ZB), (x, yi, PH), (x, yo, PH)], S, st, nh=(sx, 0, 0))
            k.box((x - 0.3, sy * 1.83 - 0.3, ZB), (x + 0.3, sy * 1.83 + 0.3, 1.2), S, k.jit(st, 0.04, 0), skip=('-z',),
                  taper=(0.92, 0.92))
            k.box((x - 0.33, sy * 1.83 - 0.33, 1.2), (x + 0.33, sy * 1.83 + 0.33, 1.32), S, PAL['stone_w'],
                  taper=(0.6, 0.6))
        # string course under the parapet
        for i in range(n - 1):
            a, b = V(mid[i]), V(mid[i + 1])
            k.beam(a + V((0, sy * 0.02, 0)), b + V((0, sy * 0.02, 0)), 0.14, 0.1, S, PAL['stone_w'], up=(0, sy, 0),
                   skip=('-u', 'c0', 'c1'), uv='box')
        # voussoirs
        ax = [x for x in xs if abs(x) <= AW]
        j = 0
        for i in range(len(ax) - 1):
            for h in range(2):
                xa, xb = lerp(ax[i], ax[i + 1], h / 2), lerp(ax[i], ax[i + 1], (h + 1) / 2)
                p0, p1 = V((xa, yo, za(xa))), V((xb, yo, za(xb)))
                d = (p1 - p0).normalized()
                nr = V((-d.z, 0, d.x))
                if nr.z < 0:
                    nr = -nr
                o = nr * 0.2 + V((0, sy * 0.0, 0))
                k.beam(p0 + o, p1 + o, 0.42, 0.14, S, k.jit(PAL['stone_w'] if j % 2 else PAL['stone'], 0.05, 0),
                       up=(0, sy, 0), skip=('-u',), uv='box')
                j += 1
        for i in range(5):
            x = (-5.6, -4.3, 4.6, 5.8, -6.4)[i] + k.r(-0.2, 0.2)
            z = k.r(0.0, max(0.05, zd(x) - 0.35))
            k.cbox((x, yo, z), (k.r(0.35, 0.6), 0.1, k.r(0.18, 0.28)), S, k.jit(mulc(st, 0.94), 0.06, 0),
                   skip=('+y',) if sy < 0 else ('-y',))
    # deck (cobbles) + soffit
    k.grid([[(x, -HI, zd(x)) for x in xs], [(x, HI, zd(x)) for x in xs]], 'M_cobble', PAL['stone_w'], smooth=True,
           colfn=lambda p: mulc(PAL['stone_w'], 0.9 + 0.1 * mnoise.noise(p * 0.8)))
    ax = [x for x in xs if abs(x) <= AW]
    k.grid([[(x, -HW, za(x)) for x in ax], [(x, HW, za(x)) for x in ax]], S, mulc(st, 0.8), smooth=True, flip=True)
    # walkable steps (bands of 0.22 m) + parapet colliders

    def xz(z):
        return 14.0 / PI * math.acos(math.sqrt(clamp(z / 2.2)))
    nb = 10
    step = 2.2 / nb
    k.walk('deck_0', (-xz(2.2 - step), -HI, ZB), (xz(2.2 - step), HI, 2.2 - step / 2))
    for b in range(1, nb):
        z_hi, z_lo = 2.2 - step * b, 2.2 - step * (b + 1)
        xa, xb = xz(z_hi), xz(max(z_lo, 0.0))
        for sg, nm in ((-1, 'w'), (1, 'e')):
            k.walk('deck_%s%d' % (nm, b), (min(sg * xa, sg * xb), -HI, ZB), (max(sg * xa, sg * xb), HI,
                                                                             (z_hi + z_lo) / 2))
    for sy, nm in ((-1, 's'), (1, 'n')):
        k.col('parapet_' + nm, (-7.0, sy * HI, ZB) if sy > 0 else (-7.0, -HW, ZB),
              (7.0, HW, 3.1) if sy > 0 else (7.0, -HI, 3.1))
    k.person = (0.0, 0.0, 2.2)
