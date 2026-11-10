"""VALOMBRE settlements pack - street furniture and props (uses arch_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *
from arch_hero import trough_box, lantern, stump, hammer
from arch_hero2 import mini_brazier

S, W, I, C = 'M_stone_wall', 'M_wood_planks', 'M_metal_iron', 'M_cloth'
PB = dict(ao_dist=0.5, dirt_h=0.3, dirt=0.25)
PV = dict(views=('persp', 'front', 'left', 'back'), cols=4, res=384)


def rock(k, c, r=(0.2, 0.16, 0.12), rz=0.0, col=None, mat='M_rock', nu=5, nv=2):
    with k.at(c, rz=rz):
        k.blob((0, 0, 0), r, nu=nu, nv=nv, mat=mat, col=col or k.jit(PAL['stone'], 0.1, 0.0), zmin=-0.25)


def log(k, a, b, r=0.09, n=5, bark='M_bark_oak', caps=(True, True)):
    k.cyl(a, b, r, r * 0.92, n=n, mat=bark, col=PAL['bark'], caps=caps, cap_mat=W,
          cap_col=k.jit(PAL['plank_l'], 0.15))


def loaf(k, c, r=0.13, rz=0.0):
    with k.at(c, rz=rz):
        k.blob((0, 0, 0), (r, r * 0.72, r * 0.5), nu=6, nv=2, mat=C, col=k.jit(PAL['bread'], 0.12), zmin=-0.3)


def fish(k, c, L=0.34, rz=0.0):
    with k.at(c, rz=rz):
        col = k.jit(PAL['fish'], 0.12)
        k.blob((0, 0, 0.025), (L / 2, L * 0.16, 0.03), nu=5, nv=2, mat=C, col=col)
        k.quad([(L * 0.42, 0, 0.025), (L * 0.62, 0.07, 0.03), (L * 0.62, -0.07, 0.03)], C, mulc(col, 0.8), double=True)


def produce_crate(k, c, s=(0.5, 0.38, 0.2), kind='cabbage', rz=0.0, rx=0.0):
    with k.at(c, rz=rz, rx=rx):
        sx, sy, sz = s
        col = k.jit(PAL['plank'])
        k.box((-sx / 2, -sy / 2, 0), (sx / 2, sy / 2, sz), W, col, skip=('+z',), uv='swap')
        k.quad([(-sx / 2 + 0.02, -sy / 2 + 0.02, sz * 0.55), (sx / 2 - 0.02, -sy / 2 + 0.02, sz * 0.55),
                (sx / 2 - 0.02, sy / 2 - 0.02, sz * 0.55), (-sx / 2 + 0.02, sy / 2 - 0.02, sz * 0.55)], W,
               mulc(col, 0.35))
        if kind == 'cabbage':
            for i in range(3):
                for j in range(2):
                    k.blob((-sx / 2 + sx * (i + 0.5) / 3, -sy / 2 + sy * (j + 0.5) / 2, sz * 0.75),
                           (sx / 6.4, sy / 4.3, sz * 0.55), nu=5, nv=2, mat=C, col=k.jit(PAL['cabbage'], 0.15))
        elif kind == 'apple':
            for i in range(4):
                for j in range(2):
                    k.blob((-sx / 2 + sx * (i + 0.5) / 4 + k.r(-0.01, 0.01), -sy / 2 + sy * (j + 0.5) / 2, sz * 0.8),
                           (sx / 9, sx / 9, sx / 10), nu=5, nv=2, mat=C,
                           col=k.jit(PAL['apple'] if (i + j) % 3 else PAL['yellow'], 0.15))
        elif kind == 'carrot':
            for i in range(6):
                x = -sx / 2 + sx * (i + 0.5) / 6
                k.cyl((x, -sy * 0.4, sz * 0.72 + (i % 2) * 0.02), (x + k.r(-0.03, 0.03), sy * 0.38, sz * 0.7), 0.03,
                      0.006, n=4, mat=C, col=k.jit(PAL['carrot'], 0.12), caps=(True, False))
        elif kind == 'fish':
            for i in range(4):
                fish(k, (-sx * 0.05 + k.r(-0.03, 0.03), -sy / 2 + sy * (i + 0.5) / 4, sz * 0.62 + i * 0.012), L=sx * 0.8,
                     rz=k.r(-0.2, 0.2) + (PI if i % 2 else 0))


def basket(k, c, r=0.24, h=0.26, fill=None, n=8):
    col = PAL['rope']
    k.lathe(c, [(r * 0.7, 0), (r, h * 0.7), (r * 0.96, h), (r * 0.86, h), (r * 0.8, h * 0.72), (0.0, h * 0.72)], n=n,
            mat='M_rope', col=col, split=(2, 3), colfn=lambda i, rr, zz: mulc(col, 0.45) if i >= 4 else col)
    if fill:
        for i in range(5):
            a = i * 1.3
            k.blob((c[0] + r * 0.42 * math.cos(a), c[1] + r * 0.42 * math.sin(a), c[2] + h * 0.8), (r * 0.26,) * 3,
                   nu=5, nv=2, mat=C, col=k.jit(fill, 0.15))


def awning(k, x0, x1, ya, za, yb, zb, n=6, cols=None, sag=0.07, val=0.18, rows=2):
    """Striped cloth from the back edge (ya, za) to the front edge (yb, zb) with a pointed valance."""
    cols = cols or (PAL['red'], PAL['white'])
    for i in range(n):
        xa, xb = lerp(x0, x1, i / n), lerp(x0, x1, (i + 1) / n)
        cc = cols[i % len(cols)]
        rws = []
        for j in range(rows + 1):
            f = j / rows
            sg = -sag * math.sin(PI * f)
            rws.append([(xa, lerp(ya, yb, f), lerp(za, zb, f) + sg), (xb, lerp(ya, yb, f), lerp(za, zb, f) + sg)])
        k.grid(rws, C, cc, double=True, smooth=False, flip=(yb < ya), back_col=mulc(cc, 0.72))
        if val:
            k.quad([(xa, yb, zb), (xb, yb, zb), ((xa + xb) / 2, yb + 0.01 * (1 if yb > ya else -1), zb - val)], C,
                   mulc(cc, 0.92), double=True, back_col=mulc(cc, 0.7))


# ----------------------------------------------------------------------------- well
@asset('well', 'Roofed stone well with windlass, crank, rope and bucket', 700, footprint=[2.8, 2.6],
       bake=dict(ao_dist=0.8, dirt_h=0.4, dirt=0.3, warp=0.012))
def well(k):
    R, ri, h = 1.0, 0.72, 0.85
    st = PAL['stone']
    k.lathe((0, 0, 0), [(R + 0.05, 0), (R, 0.3), (R - 0.03, h), (ri, h), (ri, 0.2), (0.0, 0.2)], n=10, mat=S, col=st,
            split=(2, 3, 4), colfn=lambda i, r, z: (0.02, 0.03, 0.04) if i >= 4 else st)
    for i in range(7):
        a = 0.4 + i * 0.93
        zz = 0.12 + (i * 0.37) % 0.5
        with k.at(((R - 0.01) * math.cos(a), (R - 0.01) * math.sin(a), zz), rz=a):
            k.cbox((0, 0, 0.1), (0.1, 0.34, 0.2), S, k.jit(mulc(st, 0.95), 0.06, 0), skip=('-x',))
    px = R + 0.1
    for sx in (-1, 1):
        k.box((sx * px - 0.07, -0.07, 0), (sx * px + 0.07, 0.07, 2.2), W, k.jit(PAL['beam']), skip=('-z',), uv='along')
        k.beam((sx * px, -0.72, 2.2), (sx * px, 0.72, 2.2), 0.1, 0.1, W, k.jit(PAL['beam']))
        for sy in (-1, 1):
            k.beam((sx * px, sy * 0.07, 1.75), (sx * px, sy * 0.5, 2.16), 0.07, 0.07, W, k.jit(PAL['beam_l']),
                   skip=('c0', 'c1'))
        k.quad([(sx * (px + 0.02), -0.7, 2.25), (sx * (px + 0.02), 0.7, 2.25), (sx * (px + 0.02), 0, 2.86)], W,
               PAL['plank_d'], double=True)
    roof_gable(k, -px - 0.05, px + 0.05, -0.72, 0.72, 2.25, 0.62, oe=0.24, og=0.2, tv=0.07, sag=0.03, nu=2, nv=1,
               mat=W, col=PAL['plank_d'], ridge=False, barge=False, moss=0.9)
    k.beam((-px - 0.3, 0, 2.95), (px + 0.3, 0, 2.95), 0.1, 0.08, W, k.jit(PAL['beam_d']))
    # windlass + crank + rope + bucket
    k.cyl((-px, 0, 1.55), (px, 0, 1.55), 0.085, n=6, mat=W, col=PAL['beam_l'])
    k.cyl((-0.22, 0, 1.55), (0.22, 0, 1.55), 0.11, n=6, mat='M_rope', col=PAL['rope'])
    for (a, b) in (((px, 0, 1.55), (px + 0.2, 0, 1.55)), ((px + 0.2, 0, 1.55), (px + 0.2, 0.2, 1.38)),
                   ((px + 0.2, 0.2, 1.38), (px + 0.42, 0.2, 1.38))):
        k.beam(a, b, 0.03, 0.03, I, PAL['iron'], uv='box')
    bx, by = 0.48, -0.72
    k.tube([(0.1, -0.1, 1.5), (0.3, -0.5, 1.15), (bx, by, h + 0.42)], 0.014, n=3)
    k.lathe((bx, by, h), [(0.13, 0), (0.17, 0.3), (0.145, 0.3), (0.12, 0.06), (0.0, 0.06)], n=7, mat=W,
            col=PAL['plank'], split=(1, 2))
    k.lathe((bx, by, h), [(0.165, 0.2), (0.175, 0.25)], n=7, mat=I, col=PAL['iron'])
    k.tube([(bx + 0.16 * math.cos(a), by, h + 0.3 + 0.14 * math.sin(a)) for a in [PI * i / 4 for i in range(5)]],
           0.01, n=3, mat=I, col=PAL['iron'])
    k.col('ring', (-R, -R, 0), (R, R, h + 0.05))
    k.empty('ANCHOR_interact', (0.0, -R - 0.7, 0.0))
    k.person = (1.7, -1.2)


# ----------------------------------------------------------------------------- market stalls
@asset('market_stall_a', 'Market stall: timber frame, plank counter, red/white striped awning; cabbages, carrots, '
       'apples, bread, sacks and a barrel', 1200, footprint=[3.6, 2.8], bake=dict(ao_dist=0.6, dirt_h=0.3, dirt=0.25))
def market_stall_a(k):
    hw, hd = 1.38, 0.72
    hf, hb = 2.05, 2.45
    for sx in (-1, 1):
        for sy, hh in ((-1, hf), (1, hb)):
            k.box((sx * hw - 0.045, sy * hd - 0.045, 0), (sx * hw + 0.045, sy * hd + 0.045, hh), W,
                  k.jit(PAL['beam_l']), skip=('-z',), uv='along')
        k.beam((sx * hw, -hd - 0.35, hf - 0.02 - 0.35 * (hb - hf) / (2 * hd)), (sx * hw, hd + 0.05, hb + 0.01), 0.06,
               0.07, W, k.jit(PAL['beam_l']))
        k.beam((sx * hw, -hd, 0.5), (sx * hw, hd, 0.5), 0.05, 0.07, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    k.beam((-hw - 0.08, -hd, hf - 0.03), (hw + 0.08, -hd, hf - 0.03), 0.06, 0.08, W, k.jit(PAL['beam_l']))
    k.beam((-hw - 0.08, hd, hb - 0.03), (hw + 0.08, hd, hb - 0.03), 0.06, 0.08, W, k.jit(PAL['beam_l']))
    # counter
    cz = 0.9
    k.boards((-hw - 0.06, -hd - 0.1, cz - 0.04), (1, 0, 0), (0, 1, 0), 2 * hw + 0.12, 0.7, 3, thick=0.04, skip=(),
             col=PAL['plank'])
    k.box((-hw + 0.02, -hd - 0.03, 0.22), (hw - 0.02, -hd + 0.0, cz - 0.05), W, PAL['plank_d'], uv='swap',
          skip=('+y',))
    k.beam((-hw, -hd + 0.55, cz - 0.08), (hw, -hd + 0.55, cz - 0.08), 0.05, 0.07, W, k.jit(PAL['beam_l']),
           skip=('c0', 'c1'))
    # back drape
    k.grid([[(-hw, hd + 0.02, 0.95), (hw, hd + 0.02, 0.95)], [(-hw, hd + 0.05, 1.7), (hw, hd + 0.05, 1.7)],
            [(-hw, hd + 0.02, hb - 0.08), (hw, hd + 0.02, hb - 0.08)]], C, PAL['white'], double=True, flip=True,
           back_col=mulc(PAL['white'], 0.8))
    awning(k, -hw - 0.12, hw + 0.12, hd + 0.06, hb + 0.05, -hd - 0.42, hf - 0.14, n=6)
    # goods
    produce_crate(k, (-0.98, -hd + 0.2, cz), kind='cabbage', rx=0.12)
    produce_crate(k, (-0.38, -hd + 0.2, cz), kind='carrot', rx=0.12)
    produce_crate(k, (0.22, -hd + 0.2, cz), kind='apple', rx=0.12)
    k.quad([(0.58, -hd - 0.05, cz + 0.004), (1.36, -hd - 0.05, cz + 0.004), (1.36, -hd + 0.5, cz + 0.004),
            (0.58, -hd + 0.5, cz + 0.004)], C, PAL['canvas'])
    for (x, y, rz) in ((0.78, -hd + 0.1, 0.3), (1.12, -hd + 0.12, -0.4), (0.95, -hd + 0.36, 1.2)):
        loaf(k, (x, y, cz + 0.035), rz=rz)
    loaf(k, (0.96, -hd + 0.2, cz + 0.11), rz=0.1, r=0.11)
    sack(k, (hw + 0.38, -hd + 0.1, 0), r=0.26, h=0.55, n=6)
    sack(k, (hw + 0.42, -hd + 0.65, 0), r=0.24, h=0.5, rz=0.9, n=6)
    barrel(k, (-hw - 0.42, hd - 0.4, 0), r=0.28, h=0.8, n=8)
    basket(k, (-hw - 0.4, -hd + 0.2, 0), fill=PAL['apple'])
    k.empty('ANCHOR_npc', (0.0, 0.25, 0.0))
    k.col('counter', (-hw - 0.06, -hd - 0.1, 0), (hw + 0.06, -hd + 0.6, cz))
    k.person = (-0.3, -1.6)


@asset('market_stall_b', "Fishmonger's stall: trestle table under a blue/yellow ridge awning, fish on a slanted "
       'board, baskets, tub and crates', 1200, footprint=[3.4, 2.8], bake=dict(ao_dist=0.6, dirt_h=0.3, dirt=0.25))
def market_stall_b(k):
    hw = 1.3
    zr = 2.5
    # two end A-frames + ridge pole
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.cyl((sx * hw, sy * 0.85, 0), (sx * hw, -sy * 0.06, zr + 0.12), 0.04, 0.032, n=5, mat=W, col=PAL['beam_l'])
        k.tube([(sx * hw + 0.045, -0.12, zr - 0.08), (sx * hw + 0.045, 0.12, zr - 0.02), (sx * hw - 0.045, 0.1, zr - 0.1),
                (sx * hw - 0.045, -0.1, zr - 0.02)], 0.014, n=3)
    k.cyl((-hw - 0.2, 0, zr), (hw + 0.2, 0, zr), 0.035, n=5, mat=W, col=PAL['beam_l'])
    cols = (PAL['blue'], PAL['yellow'])
    awning(k, -hw - 0.1, hw + 0.1, 0.0, zr + 0.04, -1.25, 1.85, n=6, cols=cols, sag=0.06)
    awning(k, -hw - 0.1, hw + 0.1, 0.0, zr + 0.04, 0.95, 1.55, n=6, cols=cols, sag=0.05, val=0.0)
    for sx in (-1, 1):
        k.cyl((sx * (hw + 0.1), -1.25, 1.86), (sx * (hw + 0.1), -1.25, 0), 0.028, n=4, mat=W, col=PAL['beam_l'],
              caps=(False, False))
    # trestle table
    cz = 0.86
    k.boards((-hw + 0.1, -0.85, cz - 0.04), (1, 0, 0), (0, 1, 0), 2 * hw - 0.2, 0.75, 3, thick=0.04, skip=(),
             col=PAL['plank'], lj=0.04)
    for sx in (-0.85, 0.85):
        for sy in (-1, 1):
            k.beam((sx, -0.47 + sy * 0.36, 0), (sx, -0.47 + sy * 0.1, cz - 0.04), 0.06, 0.05, W, k.jit(PAL['beam_l']),
                   skip=('c1',))
        k.beam((sx, -0.75, 0.35), (sx, -0.2, 0.35), 0.04, 0.05, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    # slanted display board with fish
    with k.at((-0.45, -0.52, cz), rx=0.3):
        k.box((-0.6, -0.26, 0.0), (0.6, 0.26, 0.03), W, PAL['plank_l'], uv='swap')
        for i in range(5):
            fish(k, (-0.46 + i * 0.23, k.r(-0.03, 0.03), 0.032), L=0.4, rz=PI / 2 + k.r(-0.15, 0.15))
    produce_crate(k, (0.72, -0.5, cz), s=(0.5, 0.4, 0.16), kind='fish', rz=0.15)
    basket(k, (0.2, -0.22, cz), r=0.17, h=0.16, fill=PAL['fish'], n=7)
    # tub with fish, crates, sack behind
    k.lathe((hw + 0.5, -0.5, 0), [(0.3, 0), (0.36, 0.42), (0.33, 0.42), (0.31, 0.3), (0.0, 0.3)], n=8, mat=W,
            col=PAL['plank'], split=(1, 2), colfn=lambda i, r, z: (0.03, 0.045, 0.055) if i >= 3 else PAL['plank'])
    k.lathe((hw + 0.5, -0.5, 0), [(0.345, 0.28), (0.36, 0.34)], n=8, mat=I, col=PAL['iron'])
    fish(k, (hw + 0.5, -0.5, 0.31), L=0.36, rz=0.6)
    crate(k, (-hw - 0.45, -0.45, 0), (0.6, 0.5, 0.42), rz=0.2)
    crate(k, (-hw - 0.42, -0.42, 0.42), (0.48, 0.4, 0.3), rz=-0.25)
    sack(k, (-hw - 0.35, 0.45, 0), r=0.25, h=0.52, n=6)
    k.tube([(-hw + 0.15, -1.2, 1.82), (0, -1.22, 1.68), (hw - 0.15, -1.2, 1.82)], 0.008, n=3)
    for i, x in enumerate((-0.6, -0.2, 0.25, 0.7)):
        zz = 1.72 - 0.04 * math.cos(x * 1.2) * 1.0
        with k.at((x, -1.21, zz - 0.2), ry=PI / 2):
            fish(k, (0, 0, 0), L=0.3)
    k.empty('ANCHOR_npc', (0.0, 0.3, 0.0))
    k.col('table', (-hw + 0.1, -0.85, 0), (hw - 0.1, -0.1, cz))
    k.person = (0.3, -1.75)


# ----------------------------------------------------------------------------- boards and posts
@asset('notice_board', 'Quest notice board: two posts, plank panel under a small shingle hood, pinned papers',
       250, footprint=[2.0, 1.0], bake=PB)
def notice_board(k):
    for sx in (-1, 1):
        k.box((sx * 0.8 - 0.06, -0.06, 0), (sx * 0.8 + 0.06, 0.06, 2.25), W, k.jit(PAL['beam']), skip=('-z',),
              uv='along', taper=(0.9, 0.9))
        rock(k, (sx * 0.8 + 0.05 * sx, -0.1, 0.0), (0.16, 0.13, 0.1), rz=sx)
    k.boards((-0.74, -0.03, 1.0), (0, 0, 1), (1, 0, 0), 1.05, 1.48, 5, thick=0.035, skip=(), col=PAL['plank'],
             lj=0.03)
    for zz in (1.08, 1.97):
        k.beam((-0.76, -0.041, zz), (0.76, -0.041, zz), 0.07, 0.02, W, k.jit(PAL['beam']), up=(0, -1, 0),
               skip=('-u',))
    # hood
    for sy, y0_, y1_ in ((-1, -0.3, 0.0), (1, 0.0, 0.22)):
        k.beam((-0.95, (y0_ + y1_) / 2, 2.32 - abs((y0_ + y1_) / 2) * 0.55), (0.95, (y0_ + y1_) / 2,
               2.32 - abs((y0_ + y1_) / 2) * 0.55), abs(y1_ - y0_) + 0.04, 0.03, W, k.jit(PAL['plank_d']),
               up=(0, sy * 0.5, 1.0), uv='around')
    # papers
    papers = [(-0.42, 1.62, 0.3, 0.38, 0.08, PAL['paper']), (0.02, 1.7, 0.26, 0.3, -0.12, mulc(PAL['paper'], 0.9)),
              (0.42, 1.58, 0.3, 0.42, 0.05, PAL['paper']), (-0.2, 1.25, 0.34, 0.24, -0.06, mulc(PAL['paper'], 0.82)),
              (0.3, 1.2, 0.22, 0.26, 0.15, PAL['paper'])]
    for i, (x, z, w_, h_, rot, col) in enumerate(papers):
        with k.at((x, -0.034 - 0.003 * i, z), ry=rot):
            k.quad([(-w_ / 2, 0, -h_ / 2), (w_ / 2, 0, -h_ / 2), (w_ / 2, -0.012, h_ / 2), (-w_ / 2, 0, h_ / 2)], C,
                   col)
            k.quad([(-0.02, -0.006, h_ / 2 - 0.05), (0.02, -0.006, h_ / 2 - 0.05), (0.0, -0.016, h_ / 2 - 0.02)], I,
                   PAL['iron'] if i != 2 else PAL['red'])
    k.col('board', (-0.86, -0.1, 0), (0.86, 0.1, 2.3))
    k.empty('ANCHOR_interact', (0.0, -0.8, 0.0))


@asset('signpost', 'Wooden signpost with two arrow boards on a stone-packed base', 200, footprint=[1.9, 0.8],
       bake=PB)
def signpost(k):
    k.cyl((0, 0, 0), (0.03, 0.02, 2.75), 0.075, 0.055, n=6, mat=W, col=PAL['beam_l'], caps=(False, True))
    for i in range(4):
        a = i * 1.7 + 0.3
        rock(k, (0.17 * math.cos(a), 0.17 * math.sin(a), 0.0), (0.15, 0.12, 0.11), rz=a)
    for (z, sg, rot, L) in ((2.38, 1, 0.12, 0.95), (2.05, -1, -0.2, 0.85)):
        with k.at((0.02, -0.065, z), rz=rot):
            pts = [(-sg * 0.22, 0, -0.1), (sg * (L - 0.16), 0, -0.1), (sg * L, 0, 0.0), (sg * (L - 0.16), 0, 0.1),
                   (-sg * 0.22, 0, 0.1)]
            k.prism(pts, (0, -0.03, 0), W, k.jit(PAL['plank']), uv='swap')
            k.quad([(-0.012, -0.034, -0.012), (0.012, -0.034, -0.012), (0.012, -0.034, 0.012), (-0.012, -0.034, 0.012)],
                   I, PAL['iron'], nh=(0, -1, 0))
    k.col('post', (-0.12, -0.12, 0), (0.12, 0.12, 2.7))


# ----------------------------------------------------------------------------- containers & small props
@asset('barrel', 'Oak barrel with iron hoops', 200, footprint=[0.75, 0.75], bake=PB)
def barrel_asset(k):
    barrel(k, (0, 0, 0), r=0.34, h=0.95, n=10)
    k.col('barrel', (-0.3, -0.3, 0), (0.3, 0.3, 0.95))
    k.person = False


@asset('crate', 'Wooden crate with corner battens', 60, footprint=[0.8, 0.8], bake=PB)
def crate_asset(k):
    s = 0.7
    k.box((-s / 2, -s / 2, 0), (s / 2, s / 2, s * 0.86), W, PAL['plank'], skip=('-z',), uv='swap')
    t = 0.018
    for (nx, ny) in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        for sgn in (-1, 1):
            tx, ty = -ny, nx
            cx = nx * (s / 2 + t / 2) + tx * sgn * (s / 2 - 0.045)
            cy = ny * (s / 2 + t / 2) + ty * sgn * (s / 2 - 0.045)
            k.beam((cx, cy, 0), (cx, cy, s * 0.86), 0.09, t, W, k.jit(PAL['plank_d']), up=(nx, ny, 0),
                   skip=('-u', 'c0', 'c1'))
    k.col('crate', (-s / 2, -s / 2, 0), (s / 2, s / 2, s * 0.86))
    k.person = False


@asset('sacks', 'Pile of four grain sacks', 250, footprint=[1.5, 1.3], bake=PB)
def sacks(k):
    sack(k, (-0.3, 0.1, 0), r=0.3, h=0.62, n=5)
    sack(k, (0.32, 0.15, 0), r=0.28, h=0.58, rz=0.8, n=5)
    sack(k, (0.05, -0.38, 0.0), r=0.27, h=0.55, rz=2.0, n=5)
    with k.at((0.02, 0.05, 0.6), rz=0.4, rx=PI / 2 * 0.95):
        k.lathe((0, 0, -0.3), [(0.2, 0.0), (0.27, 0.15), (0.26, 0.42), (0.15, 0.56), (0.07, 0.6), (0.1, 0.66)], n=5,
                mat=C, col=k.jit(PAL['sack'], 0.1), cap0=True, cap1=True, sy=0.8)
    k.col('sacks', (-0.6, -0.6, 0), (0.6, 0.45, 0.75))
    k.person = False


@asset('haystack', 'Conical haystack around a pole', 250, footprint=[3.6, 3.6],
       bake=dict(ao_dist=0.9, dirt_h=0.4, dirt=0.3))
def haystack(k):
    def df(p):
        a = math.atan2(p.y, p.x)
        f = 1.0 + 0.07 * math.sin(a * 3 + p.z * 1.3) + 0.04 * math.sin(a * 5 + 1.0)
        return V((p.x * f, p.y * f, p.z + 0.05 * math.sin(a * 2 + 0.5) * (p.z / 2.6)))
    hay = PAL['hay']
    k.lathe((0, 0, 0), [(1.55, 0), (1.7, 0.35), (1.6, 1.0), (1.25, 1.7), (0.7, 2.3), (0.2, 2.65), (0.0, 2.72)], n=10,
            mat='M_thatch', col=hay, deform=df,
            colfn=lambda i, r, z: mulc(hay, 0.8 + 0.07 * i))
    k.cyl((0, 0, 2.5), (0.04, 0.02, 3.25), 0.045, 0.03, n=5, mat=W, col=PAL['beam_l'], caps=(False, True))
    for i in range(3):
        a = 0.6 + i * 2.2
        k.blob((1.75 * math.cos(a), 1.75 * math.sin(a), 0.0), (0.4, 0.3, 0.16), nu=5, nv=2, mat='M_thatch',
               col=mulc(hay, 0.9), zmin=0.0)
    k.col('hay', (-1.3, -1.3, 0), (1.3, 1.3, 2.2))
    k.person = (2.2, -1.2)


@asset('woodpile', 'Stacked split firewood between four stakes, chopping block with axe', 300, footprint=[2.6, 1.0],
       bake=PB)
def woodpile(k):
    rr = 0.105
    rows = [7, 6, 5]
    for j, n in enumerate(rows):
        for i in range(n):
            x = -0.72 + (i + 0.5 * j) * rr * 2.05
            z = rr * 0.9 + j * rr * 1.7
            r = rr * k.r(0.85, 1.08)
            y0 = -0.3 + k.r(-0.04, 0.04)
            k.cyl((x, y0, z), (x, y0 + 0.6 + k.r(-0.05, 0.05), z), r, r * 0.93, n=4, mat='M_bark_oak',
                  col=PAL['bark'], cap_mat=W, cap_col=k.jit(PAL['plank_l'], 0.15), phase=k.r(0, 1.5))
    for sx in (-0.88, 0.78):
        for sy in (-0.2, 0.2):
            k.cyl((sx, sy, 0), (sx + (0.03 if sx > 0 else -0.03), sy, 0.85), 0.035, 0.028, n=3, mat=W,
                  col=PAL['beam_l'], caps=(False, True))
    k.cyl((1.35, -0.1, 0), (1.35, -0.1, 0.4), 0.2, 0.18, n=7, mat='M_bark_oak', col=PAL['bark'], caps=(False, True),
          cap_mat=W, cap_col=PAL['plank_l'])
    with k.at((1.35, -0.1, 0.4), rz=0.5, ry=-0.9):
        k.beam((0, 0, 0), (0.62, 0, 0), 0.03, 0.035, W, PAL['plank'], skip=('c0',))
        k.prism([(0.0, 0, 0.0), (0.12, 0, 0.0), (0.12, 0, -0.16), (0.03, 0, -0.14)], (0, 0.03, 0), I, PAL['iron_l'])
    k.col('pile', (-0.95, -0.35, 0), (0.9, 0.35, 0.65))
    k.person = False


@asset('bench', 'Rough plank bench on four splayed legs', 120, footprint=[1.9, 0.6], bake=PB)
def bench_asset(k):
    L, w, h = 1.7, 0.32, 0.46
    k.boards((-L / 2, -w / 2, h - 0.05), (1, 0, 0), (0, 1, 0), L, w, 2, thick=0.05, skip=(), col=PAL['plank'],
             lj=0.02)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.beam((sx * (L / 2 - 0.12), sy * (w / 2 + 0.05), 0), (sx * (L / 2 - 0.24), sy * (w / 2 - 0.07), h - 0.05),
                   0.06, 0.06, W, k.jit(PAL['beam_l']), skip=('c1',))
        k.beam((sx * (L / 2 - 0.2), -w / 2, h * 0.45), (sx * (L / 2 - 0.2), w / 2, h * 0.45), 0.04, 0.04, W,
               k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    k.col('bench', (-L / 2, -w / 2, 0), (L / 2, w / 2, h))
    k.person = False


def tankard(k, c, r=0.055, h=0.15, rz=0.0):
    with k.at(c, rz=rz):
        k.cyl((0, 0, 0), (0, 0, h), r * 1.05, r, n=6, mat=W, col=k.jit(PAL['plank_d']), caps=(False, False))
        k.quad([(r * 0.9 * math.cos(2 * PI * i / 6), r * 0.9 * math.sin(2 * PI * i / 6), h * 0.86) for i in range(6)],
               W, PAL['dark'])
        k.tube([(r, 0, h * 0.8), (r + 0.05, 0, h * 0.7), (r + 0.05, 0, h * 0.3), (r, 0, h * 0.2)], 0.012, n=3, mat=W,
               col=PAL['plank_d'], caps=False)


@asset('table', 'Trestle table with three tankards, a loaf on a board and a candle', 250, footprint=[2.1, 1.0],
       bake=PB)
def table(k):
    L, w, h = 1.9, 0.8, 0.78
    k.boards((-L / 2, -w / 2, h - 0.045), (1, 0, 0), (0, 1, 0), L, w, 3, thick=0.045, skip=(), col=PAL['plank'],
             lj=0.03)
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.3)
        for sy in (-1, 1):
            k.beam((x, sy * (w / 2 - 0.02), 0), (x, sy * 0.1, h - 0.045), 0.07, 0.06, W, k.jit(PAL['beam_l']),
                   skip=('c1',))
        k.beam((x, -w / 2 + 0.1, h - 0.09), (x, w / 2 - 0.1, h - 0.09), 0.06, 0.06, W, k.jit(PAL['beam_l']),
               skip=('-u',))
    k.beam((-L / 2 + 0.3, 0, 0.32), (L / 2 - 0.3, 0, 0.32), 0.05, 0.07, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    tankard(k, (-0.55, -0.15, h), rz=0.5)
    tankard(k, (0.1, 0.2, h), rz=2.4)
    tankard(k, (0.62, -0.2, h), rz=-1.0)
    k.box((-0.28, -0.3, h), (0.12, -0.05, h + 0.02), W, PAL['plank_l'])
    loaf(k, (-0.08, -0.18, h + 0.045), r=0.12, rz=0.3)
    k.cyl((0.45, 0.18, h), (0.45, 0.18, h + 0.13), 0.02, n=4, mat=C, col=PAL['white'], caps=(False, True))
    k.col('table', (-L / 2, -w / 2, 0), (L / 2, w / 2, h))
    k.person = False


@asset('trough', 'Plank water trough on two sleepers', 120, footprint=[1.9, 0.8], bake=PB)
def trough(k):
    trough_box(k, (0, 0, 0), s=(1.7, 0.46, 0.4), fill=(0.03, 0.045, 0.055))
    for sx in (-0.55, 0.55):
        k.beam((sx, -0.36, 0.3), (sx, 0.36, 0.3), 0.05, 0.02, I, PAL['iron'], up=(0, 0, 1), skip=('-u',), uv='box')
    k.col('trough', (-0.85, -0.3, 0), (0.85, 0.3, 0.52))
    k.person = False


@asset('ladder', 'Wooden ladder, 3.6 m, leaning 14 degrees towards +Y (rotate it for other uses)', 100,
       footprint=[0.7, 1.1], bake=PB)
def ladder(k):
    L, lean = 3.6, math.radians(14)
    with k.at((0, 0, 0), rx=-lean):
        for sx in (-1, 1):
            k.beam((sx * 0.24, 0, 0), (sx * 0.2, 0, L), 0.05, 0.075, W, k.jit(PAL['plank']), up=(0, 1, 0))
        for i in range(9):
            z = 0.32 + i * 0.37
            hw = lerp(0.24, 0.2, z / L)
            k.beam((-hw, 0, z), (hw, 0, z), 0.045, 0.04, W, k.jit(PAL['plank_d']), skip=('c0', 'c1'))
    k.col('ladder', (-0.3, 0.0, 0), (0.3, 0.9, 3.5))
    k.person = (0.9, -0.2)


# ----------------------------------------------------------------------------- lights & fires
@asset('lamp_post', 'Timber lamp post with a bracket and a hanging iron lantern', 300, footprint=[0.8, 1.2],
       bake=PB)
def lamp_post(k):
    k.box((-0.075, -0.075, 0), (0.075, 0.075, 3.1), W, k.jit(PAL['beam']), skip=('-z',), uv='along',
          taper=(0.78, 0.78))
    for i in range(3):
        a = i * 2.1 + 0.4
        rock(k, (0.16 * math.cos(a), 0.16 * math.sin(a), 0.0), (0.16, 0.13, 0.12), rz=a)
    k.beam((0, 0.12, 2.85), (0, -0.72, 2.95), 0.07, 0.08, W, k.jit(PAL['beam']))
    k.beam((0, -0.03, 2.3), (0, -0.52, 2.88), 0.05, 0.055, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    k.lathe((0, 0, 0), [(0.085, 2.72), (0.085, 2.78)], n=4, mat=I, col=PAL['iron'], phase=PI / 4, smooth=False)
    lantern(k, (0, -0.6, 2.9), s=0.12, hang=0.16)
    k.empty('FIRE_lamp', (0.0, -0.6, 2.52))
    k.col('post', (-0.1, -0.1, 0), (0.1, 0.1, 3.0))
    k.person = (0.8, -0.3)


@asset('brazier', 'Wrought-iron tripod brazier with a bowl of glowing coals', 300, footprint=[0.9, 0.9], bake=PB)
def brazier(k):
    r, h = 0.34, 1.05
    k.lathe((0, 0, 0), [(r * 0.3, h * 0.66), (r * 0.8, h * 0.8), (r, h), (r * 0.9, h), (r * 0.82, h * 0.9),
                        (0.0, h * 0.85)], n=8, mat=I, col=PAL['iron'], split=(2, 3),
            colfn=lambda i, rr, zz: PAL['soot'] if i >= 4 else PAL['iron'])
    k.quad([(r * 0.74 * math.cos(2 * PI * i / 8), r * 0.74 * math.sin(2 * PI * i / 8), h * 0.93) for i in range(8)],
           'M_ember', PAL['ember'], flag=NOAO)
    for i in range(6):
        a = i * 1.05 + 0.3
        em = i % 2 == 0
        k.blob((r * 0.45 * math.cos(a), r * 0.45 * math.sin(a), h * 0.94), (0.075, 0.065, 0.06), nu=5, nv=2,
               mat='M_ember' if em else 'M_rock', col=PAL['ember'] if em else (0.04, 0.04, 0.04), zmin=-0.2,
               flag=NOAO if em else 0)
    for i in range(3):
        a = 2 * PI * i / 3 + 0.5
        ca, sa = math.cos(a), math.sin(a)
        k.beam((ca * r * 1.25, sa * r * 1.25, 0), (ca * r * 0.45, sa * r * 0.45, h * 0.72), 0.03, 0.03, I, PAL['iron'],
               uv='box')
        a2 = a + 2 * PI / 3
        k.beam((ca * r * 0.95, sa * r * 0.95, h * 0.27), (math.cos(a2) * r * 0.95, math.sin(a2) * r * 0.95, h * 0.27),
               0.02, 0.02, I, PAL['iron_l'], uv='box', skip=('c0', 'c1'))
    k.lathe((0, 0, 0), [(r * 1.0, h * 0.97), (r * 1.03, h * 1.0)], n=8, mat=I, col=PAL['iron_l'])
    k.empty('FIRE_brazier', (0.0, 0.0, h + 0.05))
    k.col('brazier', (-0.3, -0.3, 0), (0.3, 0.3, h))
    k.person = False


@asset('campfire', 'Camp fire: ring of stones, charred logs, glowing embers', 250, footprint=[1.6, 1.6], bake=PB)
def campfire(k):
    n = 8
    for i in range(n):
        a = 2 * PI * i / n + k.r(-0.1, 0.1)
        rr = 0.58 + k.r(-0.04, 0.04)
        rock(k, (rr * math.cos(a), rr * math.sin(a), 0.02), (k.r(0.14, 0.2), k.r(0.1, 0.14), k.r(0.09, 0.13)),
             rz=a + PI / 2 + k.r(-0.4, 0.4), nu=4)
    k.quad([(0.5 * math.cos(2 * PI * i / 8), 0.5 * math.sin(2 * PI * i / 8), 0.015) for i in range(8)], 'M_rock',
           (0.035, 0.033, 0.032))
    k.quad([((0.26 + 0.05 * math.sin(i * 2.1)) * math.cos(2 * PI * i / 8), (0.26 + 0.05 * math.cos(i * 1.3)) *
             math.sin(2 * PI * i / 8), 0.035) for i in range(8)], 'M_ember', PAL['ember'], flag=NOAO)
    for i in range(4):
        a = i * PI / 2 + 0.35
        ca, sa = math.cos(a), math.sin(a)
        k.cyl((ca * 0.46, sa * 0.46, 0.06), (-ca * 0.08, -sa * 0.08, 0.36), 0.06, 0.05, n=4, mat='M_bark_oak',
              col=mulc(PAL['bark'], 0.3), cap_mat=W, cap_col=mulc(PAL['plank'], 0.5), phase=0.4)
    for i in range(3):
        a = i * 2.1 + 1.0
        k.blob((0.17 * math.cos(a), 0.17 * math.sin(a), 0.04), (0.07, 0.06, 0.05), nu=4, nv=2, mat='M_ember',
               col=PAL['ember'], zmin=-0.2, flag=NOAO)
    k.empty('FIRE_main', (0.0, 0.0, 0.25))
    k.col('fire', (-0.55, -0.55, 0), (0.55, 0.55, 0.35))
    k.person = False


# ----------------------------------------------------------------------------- camp
@asset('tent_a', 'Small A-frame canvas tent with ridge pole, open front flaps, guy ropes and pegs', 400,
       footprint=[3.4, 4.2], bake=dict(ao_dist=0.8, dirt_h=0.4, dirt=0.35))
def tent_a(k):
    hw, hl, zr = 1.25, 1.5, 1.85
    cv = PAL['canvas']
    k.cyl((0, -hl - 0.12, zr), (0, hl + 0.12, zr), 0.035, n=5, mat=W, col=PAL['beam_l'])
    for sy in (-1, 1):
        k.cyl((0, sy * hl, 0), (0, sy * hl, zr + 0.14), 0.04, 0.03, n=5, mat=W, col=PAL['beam_l'],
              caps=(False, True))
    for sx in (-1, 1):
        rows = []
        for j in range(4):
            f = j / 3
            sag = -0.07 * math.sin(PI * f)
            rows.append([(sx * (hw * (1 - f)) + sx * sag * 0.6, lerp(-hl, hl, i / 3),
                          zr * f + 0.02 + sag * 0.5 - 0.03 * math.sin(PI * i / 3) * math.sin(PI * f)) for i in range(4)])
        k.grid(rows, C, cv, double=True, smooth=True, flip=(sx < 0), back_col=mulc(cv, 0.6))
    # back wall
    k.quad([(-hw, hl, 0.02), (hw, hl, 0.02), (0, hl, zr + 0.02)], C, mulc(cv, 0.92), double=True,
           back_col=mulc(cv, 0.55), nh=(0, 1, 0))
    # front flaps, tied open
    for sx in (-1, 1):
        k.quad([(sx * hw, -hl, 0.02), (sx * 0.62, -hl - 0.12, 0.02), (sx * 0.2, -hl - 0.05, zr * 0.72),
                (0, -hl, zr + 0.02)], C, mulc(cv, 0.95), double=True, back_col=mulc(cv, 0.6), nh=(0, -1, 0))
    # ground sheet + bedding hint
    k.quad([(-hw + 0.1, -hl + 0.1, 0.012), (hw - 0.1, -hl + 0.1, 0.012), (hw - 0.1, hl - 0.1, 0.012),
            (-hw + 0.1, hl - 0.1, 0.012)], C, mulc(PAL['sack'], 0.6))
    # guy ropes + pegs
    for sx in (-1, 1):
        for yy in (-hl, 0.0, hl):
            px, py = sx * (hw + 0.5), yy * 1.08
            k.tube([(sx * hw * 0.55, yy, zr * 0.45 + 0.02), (px, py, 0.08)], 0.01, n=3, caps=False)
            k.cyl((px - sx * 0.04, py, 0.2), (px + sx * 0.03, py, -0.02), 0.022, 0.012, n=4, mat=W,
                  col=PAL['beam_l'], caps=(True, False))
    for sy in (-1, 1):
        k.tube([(0, sy * hl, zr + 0.1), (0, sy * (hl + 0.9), 0.08)], 0.01, n=3, caps=False)
        k.cyl((0, sy * (hl + 0.86), 0.2), (0, sy * (hl + 0.93), -0.02), 0.022, 0.012, n=4, mat=W, col=PAL['beam_l'],
              caps=(True, False))
    k.col('tent', (-hw * 0.8, -hl, 0), (hw * 0.8, hl, 1.2))
    k.person = (1.8, -1.9)


@asset('tent_b', 'Round striped pavilion: central pole with pennant, conical roof with valance, cloth walls, '
       'open front, guy ropes', 900, footprint=[7.4, 7.4], bake=dict(ao_dist=1.0, dirt_h=0.4, dirt=0.35))
def tent_b(k):
    n = 12
    R, ze, za = 2.5, 2.1, 3.7
    ca_, cb_ = PAL['red'], PAL['white']

    def pt(i, r, z):
        a = 2 * PI * i / n - PI / 2 - PI / n          # panel 0 centred on the front (-Y)
        return (r * math.cos(a), r * math.sin(a), z)
    k.cyl((0, 0, 0), (0, 0, za + 0.75), 0.06, 0.04, n=6, mat=W, col=PAL['beam_l'], caps=(False, True))
    k.blob((0, 0, za + 0.8), (0.08, 0.08, 0.08), nu=5, nv=2, mat='M_metal_gold', col=lin('#d9a441'))
    k.quad([(0, 0, za + 0.68), (0.75, 0.02, za + 0.55), (0, 0, za + 0.38)], C, ca_, double=True)
    for i in range(n):
        cc = ca_ if i % 2 == 0 else cb_
        # roof panel (3 rows, catenary sag)
        rows = []
        for j in range(4):
            f = j / 3
            r = R * (1 - f) + 0.05 * f
            z = lerp(ze, za, f) - 0.16 * math.sin(PI * f)
            rows.append([pt(i, r, z), pt(i + 1, r, z)])
        k.grid(rows, C, cc, double=True, smooth=False, back_col=mulc(cc, 0.6))
        # valance
        a, b = V(pt(i, R + 0.02, ze)), V(pt(i + 1, R + 0.02, ze))
        m = (a + b) * 0.5
        k.quad([a, b, b + V((0, 0, -0.14)), m + V((0, 0, -0.26)), a + V((0, 0, -0.14))], C, cb_ if i % 2 == 0 else ca_,
               double=True, back_col=mulc(cc, 0.6))
        # wall panel (front two panels left open)
        if i not in (0,):
            rows = [[pt(i, R - 0.04, 0.02), pt(i + 1, R - 0.04, 0.02)], [pt(i, R - 0.1, 1.0), pt(i + 1, R - 0.1, 1.0)],
                    [pt(i, R - 0.04, ze - 0.02), pt(i + 1, R - 0.04, ze - 0.02)]]
            k.grid(rows, C, mulc(cc, 0.97), double=True, smooth=False, back_col=mulc(cc, 0.6))
        else:
            # tied-back door flaps
            for (p0, p1, sg) in ((pt(i, R - 0.04, 0), pt(i + 1, R - 0.04, 0), 1), (pt(i + 1, R - 0.04, 0),
                                                                                  pt(i, R - 0.04, 0), -1)):
                p0, p1 = V(p0), V(p1)
                k.quad([(p0.x, p0.y, 0.02), (p0.x + (p1.x - p0.x) * 0.18, p0.y - 0.1, 0.02),
                        (p0.x + (p1.x - p0.x) * 0.12, p0.y - 0.06, 1.1), (p0.x + (p1.x - p0.x) * 0.5, p0.y, ze - 0.02),
                        (p0.x, p0.y, ze - 0.02)], C, mulc(cc, 0.9), double=True, back_col=mulc(cc, 0.6))
        # perimeter pole, guy rope, peg
        e = V(pt(i, R, ze))
        k.cyl((e.x * 0.985, e.y * 0.985, 0), (e.x * 0.985, e.y * 0.985, ze + 0.04), 0.03, n=4, mat=W,
              col=PAL['beam_l'], caps=(False, False))
        g = V(pt(i, R + 1.05, 0.06))
        k.tube([e, g], 0.01, n=3, caps=False)
        k.cyl((g.x * 0.99, g.y * 0.99, 0.2), (g.x * 1.01, g.y * 1.01, -0.02), 0.022, 0.012, n=4, mat=W,
              col=PAL['beam_l'], caps=(True, False))
    # floor rug
    k.quad([pt(i, R - 0.5, 0.012) for i in range(n)], C, mulc(PAL['blue'], 0.8))
    k.col('tent', (-1.75, -1.75, 0), (1.75, 1.75, 2.1))
    k.person = (1.6, -3.3)


@asset('bedroll', 'Bedroll: straw mat, blanket and rolled pillow', 80, footprint=[2.1, 0.9], bake=PB)
def bedroll(k):
    k.box((-0.38, -0.95, 0), (0.38, 0.95, 0.045), 'M_thatch', PAL['hay'], skip=('-z',))
    k.box((-0.4, -0.97, 0.045), (0.4, 0.25, 0.085), C, mulc(PAL['green'], 1.1), skip=('-z',), taper=(0.97, 0.98))
    k.cyl((-0.34, 0.72, 0.13), (0.34, 0.72, 0.13), 0.12, n=6, mat=C, col=PAL['sack'], sx=1.0)
    k.person = False


@asset('banner', 'Banner pole (4 m) with cross-bar and hanging swallow-tailed cloth; cloth vertex colour is white '
       'so the engine can tint it', 200, footprint=[1.2, 0.8], bake=PB)
def banner(k):
    k.cyl((0, 0, 0), (0, 0, 4.0), 0.055, 0.04, n=6, mat=W, col=PAL['beam_l'], caps=(False, False))
    k.cyl((0, 0, 4.0), (0, 0, 4.28), 0.045, 0.004, n=5, mat='M_metal_iron', col=PAL['iron_l'], caps=(True, True),
          uv='box')
    for i in range(3):
        a = i * 2.1 + 0.2
        rock(k, (0.15 * math.cos(a), 0.15 * math.sin(a), 0.0), (0.15, 0.12, 0.1), rz=a)
    zc = 3.72
    k.cyl((-0.5, -0.07, zc), (0.5, -0.07, zc), 0.028, n=5, mat=W, col=PAL['beam_l'])
    for sx in (-1, 1):
        k.tube([(sx * 0.42, -0.07, zc), (0, -0.02, zc + 0.24)], 0.008, n=3, caps=False)
    # cloth: 3 x 5 grid, swallow tail
    hw, Lc = 0.42, 2.0
    rows = []
    for j in range(6):
        f = j / 5
        row = []
        for i in range(4):
            u = i / 3
            x = lerp(-hw, hw, u)
            tail = 0.0
            if j == 5:
                tail = 0.3 * (1 - abs(u - 0.5) * 2) if False else (-0.32 if i in (1, 2) else 0.0)
            z = zc - 0.03 - Lc * f - tail
            y = -0.075 - 0.05 * math.sin(f * 5.0 + u * 2.0) * f
            row.append((x, y, z))
        rows.append(row)
    k.grid(rows[::-1], C, WHITE, double=True, smooth=True, flag=NOAO, flip=True)
    k.col('pole', (-0.1, -0.1, 0), (0.1, 0.1, 4.0))
    k.person = (0.9, -0.3)


@asset('scarecrow', 'Scarecrow: pole cross, patched tunic, sack head with straw hat, straw hands, a crow', 500,
       footprint=[1.9, 0.8], bake=PB)
def scarecrow(k):
    k.cyl((0, 0, 0), (0.02, 0, 2.05), 0.045, 0.035, n=5, mat=W, col=PAL['beam_l'], caps=(False, False))
    k.cyl((-0.85, 0, 1.52), (0.85, 0.02, 1.58), 0.035, 0.03, n=5, mat=W, col=PAL['beam_l'])
    tun = mulc(PAL['blue'], 0.9)

    def df(p):
        return V((p.x, p.y, p.z + 0.03 * math.sin(p.x * 9.0)))
    k.lathe((0, 0, 0), [(0.3, 0.72), (0.27, 0.95), (0.22, 1.3), (0.2, 1.55), (0.08, 1.68)], n=7, mat=C, col=tun,
            sy=0.55, deform=df, colfn=lambda i, r, z: mulc(tun, 0.75 + 0.07 * i))
    for sx in (-1, 1):
        k.cyl((sx * 0.18, 0, 1.56), (sx * 0.72, 0.01, 1.52 + (0.04 if sx > 0 else 0)), 0.1, 0.075, n=5, mat=C,
              col=mulc(tun, 0.95), caps=(False, False), sx=1.0)
        for j in range(3):
            k.cyl((sx * 0.72, 0, 1.53), (sx * (0.93 + 0.03 * j), -0.06 + 0.06 * j, 1.42 + 0.07 * j), 0.035, 0.004,
                  n=4, mat='M_thatch', col=PAL['hay'], caps=(False, False))
    k.quad([(-0.1, -0.168, 1.0), (0.06, -0.165, 1.02), (0.05, -0.172, 1.18), (-0.09, -0.17, 1.16)], C,
           mulc(PAL['red'], 0.9))
    k.lathe((0, 0, 0), [(0.262, 1.0), (0.268, 1.05)], n=7, mat='M_rope', col=PAL['rope'], sy=0.57)
    for j in range(5):
        a = j * 1.3
        k.cyl((0.22 * math.cos(a), 0.12 * math.sin(a), 0.76), (0.3 * math.cos(a), 0.17 * math.sin(a), 0.5), 0.05,
              0.004, n=4, mat='M_thatch', col=PAL['hay'], caps=(False, False))
    # head + hat
    k.blob((0.01, 0, 1.86), (0.17, 0.16, 0.19), nu=7, nv=4, mat=C, col=PAL['sack'])
    for sx in (-1, 1):
        k.quad([(sx * 0.07 - 0.025, -0.153, 1.88), (sx * 0.07 + 0.025, -0.153, 1.88), (sx * 0.07, -0.158, 1.92)], C,
               PAL['dark'], nh=(0, -1, 0))
    k.quad([(-0.07, -0.16, 1.8), (0.07, -0.16, 1.8), (0.07, -0.158, 1.815), (-0.07, -0.158, 1.815)], C, PAL['dark'])
    hat = mulc(PAL['hay'], 0.85)
    k.lathe((0.01, 0, 0), [(0.36, 1.96), (0.17, 2.0), (0.13, 2.14), (0.0, 2.2)], n=8, mat='M_thatch', col=hat,
            colfn=lambda i, r, z: mulc(hat, 0.8 + 0.08 * i))
    k.lathe((0.01, 0, 0), [(0.17, 1.995), (0.36, 1.955)], n=8, mat='M_thatch', col=mulc(hat, 0.6))
    # crow on the left arm
    cx, cz = -0.55, 1.63
    crow = (0.03, 0.03, 0.035)
    k.blob((cx, 0, cz + 0.06), (0.06, 0.11, 0.06), nu=5, nv=2, mat=C, col=crow)
    k.blob((cx, -0.1, cz + 0.13), (0.04, 0.045, 0.04), nu=5, nv=2, mat=C, col=crow)
    k.cyl((cx, -0.13, cz + 0.13), (cx, -0.2, cz + 0.115), 0.014, 0.002, n=3, mat='M_bone', col=PAL['iron'],
          caps=(False, False))
    k.quad([(cx - 0.03, 0.08, cz + 0.07), (cx + 0.03, 0.08, cz + 0.07), (cx, 0.22, cz + 0.02)], C, crow, double=True)
    k.col('pole', (-0.2, -0.15, 0), (0.2, 0.15, 2.0))
    k.person = (1.3, -0.3)
