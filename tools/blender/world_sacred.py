"""VALOMBRE world pack - sacred / lore props: Autel de Braise (shrine), standing stones, dolmen, lore stele,
graves, sarcophagus, treasure chests, Astre crystals (uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *

PBW = dict(ao_dist=0.9, ao_min=0.34, dirt_h=0.4, dirt=0.3)
PBS = dict(ao_dist=0.45, ao_min=0.38, dirt_h=0.2, dirt=0.25)
WAX = L('#e6dcc2')
STEEL_OLD = L('#7d7a74')


def candle(k, p, h=0.16, r=0.022, lit=True):
    x, y, z = p
    k.cyl((x, y, z), (x, y, z + h), r * 1.15, r, n=5, mat='M_bone', col=k.jit(WAX, 0.06), caps=(False, True))
    if lit:
        k.cyl((x, y, z + h), (x, y, z + h + 0.07), 0.016, 0.0, n=3, mat='M_ember', col=EMB_H, caps=(False, False),
              smooth=False, flag=NOAO)


def sword_planted(k, p, rx=0.05, ry=-0.04, rz=0.0, s=1.0, depth=0.12, cloth=None):
    """Old sword stuck in the ground: blade towards -Z, flat of the blade facing -Y."""
    with k.at(p, rx=rx, ry=ry, rz=rz, scale=s):
        k.box((-0.032, -0.007, -depth), (0.032, 0.007, 0.8), 'M_metal_steel', STEEL_OLD, skip=('-z',))
        k.box((-0.17, -0.02, 0.8), (0.17, 0.02, 0.838), IR, PAL['iron_l'])
        k.cyl((0, 0, 0.838), (0, 0, 0.99), 0.018, 0.016, n=5, mat='M_leather', col=PAL['leather'], caps=(False, False))
        k.blob((0, 0, 1.015), (0.036, 0.022, 0.034), nu=6, nv=3, mat=IR, col=PAL['iron_l'])
        if cloth:
            rag(k, (-0.05, -0.024, 0.83), (1, 0, 0), (0.25, -0.2, -1), 0.09, 0.42, nu=1, nv=3, col=cloth, wave=0.03,
                seed=3)


def stone_runes(k, rings, facet, names, col, size=0.4, i0=1, v=0.5):
    for i, nm in enumerate(names):
        if nm is None:
            continue
        pan = ring_panel(rings, i0 + i, i0 + i + 1, facet)
        sz = min(size, pan.wv * 0.72, pan.wu * 0.82 / 0.7)
        glyph(k, pan, nm, 0.5, v, size=sz, col=col)


# ----------------------------------------------------------------------------- shrine
@asset('shrine', "Autel de Braise (checkpoint): round two-tier stone dais 3.2 m across with an ember rune ring, carved "
       "altar holding an iron bowl of embers, three tall leaning rune stones (ember glyphs inside and outside), an old "
       "sword planted in front of the altar, candles and offerings", 2500, footprint=[6.4, 6.2],
       bake=dict(ao_dist=1.3, ao_min=0.36, dirt_h=0.5, dirt=0.3), res=512, seed=11,
       weather=dict(top=0.22, base=0.5))
def shrine(k):
    # ---- dais
    k.lathe((0, 0, 0), [(1.68, -0.4), (1.62, 0.15), (1.45, 0.15), (1.4, 0.3)], n=20, mat=SB, col=ST, split=(1, 2))
    ns = 10
    ri = 0.78
    for i in range(ns):
        a0, a1 = 2 * PI * (i + 0.07) / ns, 2 * PI * (i + 0.93) / ns
        dz = k.r(-0.006, 0.006)
        k.quad([(ri * math.cos(a0), ri * math.sin(a0), 0.3 + dz), (1.4 * math.cos(a0), 1.4 * math.sin(a0), 0.3 + dz),
                (1.4 * math.cos(a1), 1.4 * math.sin(a1), 0.3 - dz), (ri * math.cos(a1), ri * math.sin(a1), 0.3 - dz)],
               SB, k.jit(mulc(ST, 0.97), 0.07, 0.01), nh=(0, 0, 1))
    k.quad([(1.4 * math.cos(2 * PI * i / 20), 1.4 * math.sin(2 * PI * i / 20), 0.272) for i in range(20)], SB,
           mulc(ST, 0.5))
    k.quad([((ri - 0.03) * math.cos(2 * PI * i / ns + 0.3), (ri - 0.03) * math.sin(2 * PI * i / ns + 0.3), 0.3)
            for i in range(ns)], SB, mulc(ST, 0.92))
    # glowing rune ring inlaid in the dais (broken into arcs)
    for i in range(16):
        if i in (3, 4, 5, 11):          # behind the altar / worn away
            continue
        a0, a1 = 2 * PI * (i + 0.1) / 16, 2 * PI * (i + 0.9) / 16
        r0, r1 = 1.07, 1.15
        k.quad([(r0 * math.cos(a0), r0 * math.sin(a0), 0.318), (r1 * math.cos(a0), r1 * math.sin(a0), 0.318),
                (r1 * math.cos(a1), r1 * math.sin(a1), 0.318), (r0 * math.cos(a1), r0 * math.sin(a1), 0.318)],
               'M_rune_glow', RUNE_E, flag=NOAO, nh=(0, 0, 1))
    # ---- altar (centre y = 0.45)
    ay = 0.45
    k.box((-0.6, ay - 0.4, 0.3), (0.6, ay + 0.4, 0.43), SB, ST, skip=('-z',), taper=(0.95, 0.93))
    k.box((-0.43, ay - 0.27, 0.43), (0.43, ay + 0.27, 0.98), SB, ST_D, skip=('-z', '+z'), taper=(0.93, 0.93))
    k.box((-0.46, ay - 0.3, 0.98), (0.46, ay + 0.3, 1.05), SB, ST, skip=('-z', '+z'), taper=(1.24, 1.26))
    k.box((-0.57, ay - 0.38, 1.05), (0.57, ay + 0.38, 1.16), SB, ST_L, skip=('-z',))
    for sx in (-1, 1):
        k.cyl((sx * 0.47, ay - 0.31, 0.43), (sx * 0.45, ay - 0.3, 0.98), 0.055, 0.05, n=5, mat=SB, col=ST_L,
              caps=(False, False))
    front = Panel((-0.43, ay - 0.27, 0.43), (0.43, ay - 0.27, 0.43), (0.40, ay - 0.251, 0.98), (-0.40, ay - 0.251, 0.98))
    glyph(k, front, 'ember', 0.5, 0.52, size=0.4, col=RUNE_E, w=0.05)
    glyph(k, front, 'ash', 0.17, 0.5, size=0.2, col=RUNE_E)
    glyph(k, front, 'tyr', 0.83, 0.5, size=0.2, col=RUNE_E)
    for sx in (-1, 1):
        side = Panel((sx * 0.43, ay - sx * 0.27, 0.43), (sx * 0.43, ay + sx * 0.27, 0.43),
                     (sx * 0.40, ay + sx * 0.251, 0.98), (sx * 0.40, ay - sx * 0.251, 0.98))
        glyph(k, side, 'sun' if sx > 0 else 'gate', 0.5, 0.5, size=0.3, col=RUNE_E)
    # iron bowl with embers
    zb = 1.16
    k.lathe((0, ay, zb), [(0.1, 0.0), (0.15, 0.035), (0.21, 0.05), (0.37, 0.2), (0.41, 0.29), (0.36, 0.29),
                          (0.31, 0.21), (0.0, 0.2)], n=10, mat=IR, col=PAL['iron'], split=(1, 4, 5, 6),
            colfn=lambda i, r, z: PAL['soot'] if i >= 6 else PAL['iron'])
    k.quad([(0.3 * math.cos(2 * PI * i / 9), ay + 0.3 * math.sin(2 * PI * i / 9), zb + 0.225) for i in range(9)],
           'M_ember', mulc(EMB, 0.9), flag=NOAO)
    for i in range(6):
        a = i * 1.07
        rr = 0.07 + 0.14 * ((i * 53) % 10) / 10
        em = i != 4
        k.blob((rr * math.cos(a), ay + rr * math.sin(a), zb + 0.235), (0.085, 0.07, 0.07), nu=5, nv=2,
               mat='M_ember' if em else RK, col=(EMB_H if i % 2 else EMB) if em else PAL['dark'], zmin=0.0,
               flag=NOAO if em else 0)
    k.soot.append((V((0, ay, zb + 0.3)), 0.6, 0.55))
    k.empty('FIRE_main', (0, ay, zb + 0.32))
    # ---- three leaning rune stones
    R = 2.32
    specs = [(90, 4.35, 1.05, 0.62, 2, ('ember', 'sun', 'tyr', 'ash'), ('sun', 'fork')),
             (212, 3.7, 0.98, 0.56, 5, ('gate', 'ember', 'zig', 'eye'), ('ember', 'bar')),
             (331, 3.95, 0.92, 0.6, 8, ('fork', 'sun', 'hook', 'ember'), ('tyr', 'star'))]
    for si, (deg, h, w, d, seed, inner, outer) in enumerate(specs):
        a = math.radians(deg)
        c = (R * math.cos(a), R * math.sin(a), 0.0)
        rz = a - PI / 2
        fr, bk = menhir(k, c, h, w, d, lean=(0.03 * (seed % 3 - 1), -0.115), seed=seed, rz=rz, sink=0.8, n=5,
                        taper=0.5, rough=0.1)
        stone_runes(k, fr.rings, 0, inner, RUNE_E, size=0.46, i0=1)
        stone_runes(k, fr.rings, 4, (None, None) + outer, RUNE_E, size=0.5, i0=1)
        k.col('stone_%d' % (si + 1),
              (c[0] - w / 2, c[1] - d / 2 - 0.15, 0), (c[0] + w / 2, c[1] + d / 2 + 0.05, h), rz=rz)
        rock(k, (c[0] + 0.55 * math.cos(a + 1.3), c[1] + 0.55 * math.sin(a + 1.3), 0.02), (0.3, 0.24, 0.2), seed=seed,
             nu=6, nv=3)
    # ---- sword, candles, offerings
    sword_planted(k, (0.0, -0.38, 0.3), rx=0.07, ry=-0.05, s=1.12, cloth=L('#b8491f'))
    for (x, y, z, h) in ((-0.5, ay - 0.36, 0.43, 0.2), (-0.41, ay - 0.37, 0.43, 0.11), (0.5, ay - 0.35, 0.43, 0.15),
                         (-0.45, ay - 0.25, 1.16, 0.13), (0.47, ay - 0.27, 1.16, 0.19), (0.38, ay - 0.31, 1.16, 0.09),
                         (0.78, -0.2, 0.3, 0.17), (0.9, -0.12, 0.3, 0.1), (-0.85, -0.25, 0.3, 0.14)):
        candle(k, (x, y, z), h)
    skull(k, (-0.62, -0.05, 0.385), s=1.0, rz=0.5, rx=0.1)
    k.lathe((0.68, 0.05, 0.3), [(0.07, 0.0), (0.15, 0.06), (0.16, 0.09), (0.13, 0.085), (0.0, 0.05)], n=7, mat=WD,
            col=PAL['plank_d'], split=(2, 3))
    for (x, y, z) in ((0.68, 0.05, 0.352), (0.71, 0.02, 0.36), (0.5, -0.12, 0.3), (0.56, -0.2, 0.3)):
        k.cyl((x, y, z), (x, y, z + 0.012), 0.032, n=6, mat='M_metal_gold', col=GOLD, caps=(False, True))
    k.blob((-0.82, 0.2, 0.3), (0.16, 0.12, 0.1), nu=6, nv=2, mat=CL, col=L('#8a3a22'), zmin=0.0)
    k.empty('ANCHOR_rest', (0.0, ay - 0.38 - 1.3, 0.3))
    k.walk('dais', (-1.15, -1.15, -0.4), (1.15, 1.15, 0.3))
    k.walk('dais_b', (-1.15, -1.15, -0.4), (1.15, 1.15, 0.3), rz=PI / 4)
    k.col('altar', (-0.57, ay - 0.38, 0), (0.57, ay + 0.38, 1.45))
    k.person = (-1.0, -0.75, 0.3)


# ----------------------------------------------------------------------------- standing stones, dolmen, stele
def foot_stones(k, pts, seed=1):
    for i, (x, y, r) in enumerate(pts):
        rock(k, (x, y, r * 0.15), (r, r * 0.8, r * 0.6), seed=seed + i, nu=6, nv=3)


@asset('standing_stone_a', 'Menhir, 3.2 m, slender and leaning, column of three glowing runes on the front, one on '
       'the back', 300, footprint=[1.8, 1.5], bake=PBW)
def standing_stone_a(k):
    fr, bk = menhir(k, (0, 0, 0), 3.2, 1.0, 0.55, lean=(0.07, -0.05), seed=3, sink=0.8, n=4)
    stone_runes(k, fr.rings, 0, ('tyr', 'eye', 'ash'), RUNE_C, size=0.42, i0=2)
    stone_runes(k, fr.rings, 4, (None, 'sun'), RUNE_C, size=0.42, i0=2)
    foot_stones(k, ((0.62, -0.25, 0.22), (-0.55, 0.3, 0.17)), 3)
    k.col('stone', (-0.5, -0.35, 0), (0.6, 0.3, 3.2))
    k.person = (1.2, -0.6)


@asset('standing_stone_b', 'Menhir, 2.5 m, broad and squat, big eye rune flanked by two small ones', 300,
       footprint=[2.2, 1.5], bake=PBW)
def standing_stone_b(k):
    fr, bk = menhir(k, (0, 0, 0), 2.5, 1.55, 0.62, lean=(-0.03, 0.04), seed=7, sink=0.8, n=4, taper=0.68,
                    top_slant=0.5)
    pan = ring_panel(fr.rings, 2, 4, 0)
    glyph(k, pan, 'eye', 0.5, 0.52, size=0.62, col=RUNE_C, w=0.06, aspect=1.0)
    glyph(k, pan, 'zig', 0.17, 0.5, size=0.3, col=RUNE_C)
    glyph(k, pan, 'fork', 0.83, 0.5, size=0.3, col=RUNE_C)
    stone_runes(k, fr.rings, 4, ('gate',), RUNE_C, size=0.45, i0=3)
    foot_stones(k, ((0.95, 0.2, 0.25), (-0.9, -0.3, 0.2), (0.3, 0.5, 0.15)), 5)
    k.col('stone', (-0.8, -0.35, 0), (0.8, 0.35, 2.5))
    k.person = (1.5, -0.6)


@asset('standing_stone_c', 'Menhir, 4 m, tall, split by a glowing crack, column of four runes', 300,
       footprint=[1.8, 1.6], bake=PBW)
def standing_stone_c(k):
    fr, bk = menhir(k, (0, 0, 0), 4.0, 0.95, 0.62, lean=(-0.05, 0.06), seed=11, sink=0.9, n=5, taper=0.5)
    stone_runes(k, fr.rings, 0, ('sun', 'hook', 'bar', 'ember'), RUNE_C, size=0.4, i0=2)
    # glowing crack zig-zagging up the +X side facet and the back
    for (j, i0) in ((2, 1), (4, 2)):
        for i in range(i0, i0 + 3):
            pan = ring_panel(fr.rings, i, i + 1, j)
            u0, u1 = (0.35, 0.62) if i % 2 else (0.62, 0.35)
            stroke(k, pan, (u0, 0.0), ((u0 + u1) / 2 + 0.12, 0.5), w=0.035, col=RUNE_C)
            stroke(k, pan, ((u0 + u1) / 2 + 0.12, 0.5), (u1, 1.0), w=0.03, col=RUNE_C)
    foot_stones(k, ((-0.65, -0.3, 0.24), (0.6, 0.35, 0.2)), 9)
    k.col('stone', (-0.55, -0.3, 0), (0.45, 0.45, 4.0))
    k.person = (1.2, -0.6)


@asset('dolmen', 'Dolmen: three leaning uprights carrying a 3.6 m capstone, chamber open towards -Y (1.75 m clear), '
       'rune on the back upright', 400, footprint=[4.0, 3.4], bake=dict(ao_dist=1.4, ao_min=0.3, dirt_h=0.5, dirt=0.3))
def dolmen(k):
    f1, _ = menhir(k, (-1.25, 0.1, 0), 1.85, 1.5, 0.5, lean=(0.05, 0.0), seed=2, rz=PI / 2 + 0.12, sink=0.7, n=3,
                   taper=0.8, top_slant=0.1)
    f2, _ = menhir(k, (1.25, 0.0, 0), 1.8, 1.6, 0.48, lean=(-0.04, 0.0), seed=4, rz=-PI / 2 - 0.08, sink=0.7, n=3,
                   taper=0.8, top_slant=0.1)
    f3, _ = menhir(k, (0.05, 1.15, 0), 1.9, 1.7, 0.45, lean=(0.0, -0.05), seed=6, rz=0.05, sink=0.7, n=3, taper=0.85,
                   top_slant=0.1)
    glyph(k, ring_panel(f3.rings, 2, 3, 0), 'sun', 0.5, 0.5, size=0.42, col=RUNE_C)
    rock(k, (0.0, 0.15, 2.12), (1.95, 1.5, 0.36), seed=5, nu=10, nv=4, rough=0.16, zmin=-0.75, rz=0.15,
         lean=(0.0, 0.06))
    foot_stones(k, ((-1.7, -0.7, 0.25), (1.75, 0.8, 0.2)), 3)
    k.col('left', (-1.25 - 0.3, 0.1 - 0.8, 0), (-1.25 + 0.3, 0.1 + 0.8, 1.9))
    k.col('right', (1.25 - 0.3, -0.8, 0), (1.25 + 0.3, 0.8, 1.9))
    k.col('back', (-0.8, 1.15 - 0.3, 0), (0.9, 1.15 + 0.3, 1.9))
    k.person = (2.3, -1.2)


def slab_outline(w, h, kind='round', n=3, shoulder=0.0):
    """2D outline (x, z) of a head stone, counter-clockwise seen from the front (-Y)."""
    hw = w / 2
    if kind == 'round':
        zs = h - hw
        pts = [(-hw, 0), (hw, 0), (hw, zs)]
        pts += [(hw * math.cos(PI * i / (2 * n)), zs + hw * math.sin(PI * i / (2 * n))) for i in range(1, 2 * n)]
        pts.append((-hw, zs))
    else:   # pointed
        zs = h - hw * 1.25
        pts = [(-hw, 0), (hw, 0), (hw, zs)]
        if shoulder:
            pts += [(hw - shoulder, zs), (hw - shoulder, zs + shoulder * 0.8)]
        pts += [(hw * 0.45, zs + (h - zs) * 0.62), (0, h), (-hw * 0.45, zs + (h - zs) * 0.62)]
        if shoulder:
            pts += [(-hw + shoulder, zs + shoulder * 0.8), (-hw + shoulder, zs)]
        pts.append((-hw, zs))
    return pts


def slab(k, outline, th, mat=RK, col=None, z0=0.0, y=0.0):
    col = col or ROCK
    k.prism([(x, y - th / 2, z0 + z) for x, z in outline], (0, th, 0), mat, col)
    return Panel((min(x for x, z in outline), y - th / 2, z0), (max(x for x, z in outline), y - th / 2, z0),
                 (max(x for x, z in outline), y - th / 2, z0 + max(z for x, z in outline)),
                 (min(x for x, z in outline), y - th / 2, z0 + max(z for x, z in outline)))


@asset('lore_stele', 'Carved lore tablet, 1.7 m: arched slab on a plinth with a sun emblem and five lines of glowing '
       'inscription', 300, footprint=[1.5, 2.2], bake=PBW)
def lore_stele(k):
    k.box((-0.68, -0.3, -0.3), (0.68, 0.3, 0.22), SB, ST_D, skip=('-z',), taper=(0.93, 0.9))
    with k.at((0, 0.02, 0.2), rx=-0.07):
        out = slab_outline(1.02, 1.5, 'round', n=3)
        pan = slab(k, out, 0.2, mat=SB, col=ST)
        # raised border: darker recessed field
        inner = [(x * 0.84, 0.1 + z * 0.9) for x, z in slab_outline(1.02, 1.5, 'round', n=3)]
        k.quad([(x, -0.1 - 0.006, z) for x, z in inner], SB, mulc(ST, 0.7), nh=(0, -1, 0))
        glyph(k, pan, 'sun', 0.5, 0.83, size=0.26, col=RUNE_C, w=0.03, off=0.016, aspect=1.0)
        gi = 0
        for row in range(5):
            v = 0.63 - row * 0.115
            ng = 5 if row < 4 else 3
            for i in range(ng):
                u = 0.5 + (i - (ng - 1) / 2) * 0.15
                glyph(k, pan, ['ash', 'tyr', 'zig', 'hook', 'x', 'fork'][(gi * 5 + row) % 6], u, v, size=0.105,
                      col=RUNE_C, w=0.02, off=0.016, aspect=0.75)
                gi += 1
    foot_stones(k, ((0.75, 0.25, 0.14),), 2)
    k.empty('ANCHOR_interact', (0, -1.0, 0))
    k.col('stele', (-0.6, -0.25, 0), (0.6, 0.25, 1.7))
    k.person = (1.15, 0.2)


# ----------------------------------------------------------------------------- graves
def carve(k, pan, segs, w=0.03, col=None, mat=RK):
    col = col or mulc(ROCK, 0.4)
    for (a, b) in segs:
        stroke(k, pan, a, b, w=w, off=0.012, col=col, mat=mat)


@asset('gravestone_a', 'Round-headed gravestone, 1 m, leaning back, carved sun', 80, footprint=[0.9, 0.6], bake=PBS)
def gravestone_a(k):
    with k.at((0, 0, -0.25), rx=0.1, ry=0.03):
        pan = slab(k, slab_outline(0.62, 1.25, 'round', n=2), 0.14)
        carve(k, pan, [((0.5, 0.52), (0.5, 0.8)), ((0.28, 0.66), (0.72, 0.66)), ((0.25, 0.4), (0.75, 0.4))])
    rock(k, (0.34, -0.05, 0.03), (0.16, 0.13, 0.1), seed=1, nu=5, nv=2)
    k.col('stone', (-0.32, -0.12, 0), (0.32, 0.12, 1.0))
    k.person = (0.8, -0.3)


@asset('gravestone_b', 'Pointed gothic gravestone with shoulders, 1.25 m, leaning sideways', 80, footprint=[0.9, 0.6],
       bake=PBS)
def gravestone_b(k):
    with k.at((0, 0, -0.25), rx=-0.05, ry=0.13):
        pan = slab(k, slab_outline(0.6, 1.5, 'pointed', shoulder=0.07), 0.13)
        carve(k, pan, [((0.5, 0.45), (0.5, 0.78)), ((0.3, 0.66), (0.7, 0.66))])
    k.box((-0.4, -0.16, -0.1), (0.42, 0.16, 0.1), RK, mulc(ROCK, 0.92), skip=('-z',), taper=(0.9, 0.85))
    k.col('stone', (-0.3, -0.12, 0), (0.42, 0.12, 1.2))
    k.person = (0.8, -0.3)


@asset('gravestone_c', 'Broken gravestone: jagged stump, the fallen head lying in front', 80, footprint=[1.0, 1.5],
       bake=PBS)
def gravestone_c(k):
    with k.at((0, 0, -0.25), rx=0.04, ry=-0.05):
        k.prism([(x, -0.07, z) for x, z in ((-0.3, 0), (0.3, 0), (0.3, 0.72), (0.12, 0.6), (-0.05, 0.86),
                                              (-0.3, 0.95))], (0, 0.14, 0), RK, ROCK)
    with k.at((0.12, -0.62, 0.05), rx=-PI / 2 + 0.12, rz=0.35):
        pan = slab(k, [(-0.3, 0.28), (-0.05, 0.2), (0.12, 0.0), (0.3, 0.1), (0.3, 0.38), (0.0, 0.62), (-0.3, 0.38)],
                   0.14)
    rock(k, (-0.3, -0.3, 0.02), (0.14, 0.11, 0.09), seed=4, nu=5, nv=2)
    k.col('stone', (-0.3, -0.1, 0), (0.3, 0.1, 0.7))
    k.person = (0.85, -0.3)


@asset('grave_cross', 'Weathered stone wheel cross, 1.6 m, on a stepped base, leaning', 120, footprint=[1.0, 0.8],
       bake=PBS)
def grave_cross(k):
    k.box((-0.38, -0.3, -0.2), (0.38, 0.3, 0.16), RK, mulc(ROCK, 0.92), skip=('-z',), taper=(0.9, 0.88))
    with k.at((0, 0, 0.12), ry=0.07, rx=0.04):
        k.box((-0.11, -0.075, 0), (0.11, 0.075, 1.5), RK, ROCK, skip=('-z',), taper=(0.72, 0.85))
        k.box((-0.36, -0.065, 1.0), (0.36, 0.065, 1.19), RK, ROCK)
        zc_, r0, r1 = 1.095, 0.24, 0.32
        for q in range(4):
            a0 = q * PI / 2 + 0.33
            for s_ in range(2):
                b0, b1 = a0 + s_ * 0.455, a0 + (s_ + 1) * 0.455
                pts = [(r0 * math.cos(b0), zc_ + r0 * math.sin(b0)), (r1 * math.cos(b0), zc_ + r1 * math.sin(b0)),
                       (r1 * math.cos(b1), zc_ + r1 * math.sin(b1)), (r0 * math.cos(b1), zc_ + r0 * math.sin(b1))]
                k.quad([(x, -0.045, z) for x, z in pts], RK, ROCK, nh=(0, -1, 0))
                k.quad([(x, 0.045, z) for x, z in pts], RK, ROCK, nh=(0, 1, 0))
                k.quad([(pts[1][0], -0.045, pts[1][1]), (pts[2][0], -0.045, pts[2][1]), (pts[2][0], 0.045, pts[2][1]),
                        (pts[1][0], 0.045, pts[1][1])], RK, mulc(ROCK, 0.95),
                       nh=(math.cos((b0 + b1) / 2), 0, math.sin((b0 + b1) / 2)))
                k.quad([(pts[0][0], -0.045, pts[0][1]), (pts[3][0], -0.045, pts[3][1]), (pts[3][0], 0.045, pts[3][1]),
                        (pts[0][0], 0.045, pts[0][1])], RK, mulc(ROCK, 0.85),
                       nh=(-math.cos((b0 + b1) / 2), 0, -math.sin((b0 + b1) / 2)))
    k.col('cross', (-0.3, -0.2, 0), (0.3, 0.2, 1.6))
    k.person = (0.85, -0.3)


@asset('sarcophagus', "Stone sarcophagus, 2.4 m: plinth, chest with blind arcades, skewed lid carved with the effigy "
       "of a knight (head on a cushion, hands joined, sword on the body)", 600, footprint=[2.8, 1.5], bake=PBW)
def sarcophagus(k):
    k.box((-1.3, -0.62, -0.25), (1.3, 0.62, 0.16), SB, ST_D, skip=('-z',), taper=(0.97, 0.94))
    k.box((-1.12, -0.46, 0.16), (1.12, 0.46, 0.8), SB, ST, skip=('-z', '+z'))
    for sy in (-1, 1):
        w = Wall((-1.12, -0.46), (1.12, -0.46), 0, 0) if sy < 0 else Wall((1.12, 0.46), (-1.12, 0.46), 0, 0)
        for i in range(4):
            arch_decal(k, w, 0.37 + i * 0.5, 0.26, 0.34, 0.5, 0.7, off=0.012, col=mulc(ST, 0.5), n=2, flag=0)
    for sx in (-1, 1):
        w = Wall((1.12, -0.46), (1.12, 0.46), 0, 0) if sx > 0 else Wall((-1.12, 0.46), (-1.12, -0.46), 0, 0)
        arch_decal(k, w, 0.46, 0.26, 0.46, 0.48, 0.7, off=0.012, col=mulc(ST, 0.5), n=2, flag=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box((sx * 1.12 - 0.06, sy * 0.46 - 0.06, 0.16), (sx * 1.12 + 0.06, sy * 0.46 + 0.06, 0.8), SB, ST_L,
                  skip=('-z', '+z'))
    with k.at((0.05, 0.03, 0.8), rz=0.07):
        k.box((-1.22, -0.55, 0.0), (1.22, 0.55, 0.08), SB, ST_L, skip=())
        k.box((-1.22, -0.55, 0.08), (1.22, 0.55, 0.17), SB, ST, skip=('-z',), taper=(0.95, 0.88))
        E = dict(mat=SB, col=mulc(ST, 1.02))
        k.box((-1.05, -0.24, 0.17), (-0.6, 0.24, 0.26), SB, ST_D, skip=('-z',), taper=(0.9, 0.9))       # cushion
        k.blob((-0.83, 0, 0.36), (0.13, 0.115, 0.12), nu=7, nv=3, zmin=-0.75, **E)                         # helm
        k.blob((-0.2, 0, 0.17), (0.5, 0.25, 0.2), nu=8, nv=3, zmin=0.0, **E)                               # torso
        k.blob((-0.57, 0.0, 0.17), (0.14, 0.31, 0.15), nu=6, nv=2, zmin=0.0, **E)                          # shoulders
        for sy in (-1, 1):
            k.cyl((0.2, sy * 0.105, 0.24), (0.95, sy * 0.1, 0.22), 0.1, 0.07, n=5, caps=(False, False), **E)
            k.box((0.93, sy * 0.1 - 0.055, 0.17), (1.05, sy * 0.1 + 0.055, 0.42), SB, ST, skip=('-z',),
                  taper=(0.7, 0.9))
        k.loft([(-0.42, -0.06, 0.34), (-0.42, 0.06, 0.34), (-0.42, 0.0, 0.46)],
               [(-0.26, -0.06, 0.34), (-0.26, 0.06, 0.34), (-0.26, 0.0, 0.44)], SB, ST_L)                 # joined hands
        k.box((-0.3, -0.035, 0.36), (0.85, 0.035, 0.4), SB, ST_L, skip=('-z',), taper=(1.0, 0.6))          # sword
        k.box((-0.26, -0.17, 0.36), (-0.2, 0.17, 0.41), SB, ST_L, skip=('-z',))
    rubble(k, (0.9, -0.85, 0), (0.4, 0.3), 0.1, blocks=3, seed=3, heap=False, bs=(0.14, 0.3))
    k.col('tomb', (-1.3, -0.62, 0), (1.3, 0.62, 1.25))
    k.person = (1.7, -0.7)


# ----------------------------------------------------------------------------- chests
def chest_build(k, ornate=False):
    W, D, H = (1.0, 0.6, 0.4) if ornate else (0.9, 0.55, 0.36)
    hx, hy = W / 2, D / 2
    wood = L('#c9a58a') if ornate else PAL['plank']
    wood_d = mulc(wood, 0.45)
    MT, mc = ('M_metal_gold', GOLD) if ornate else (IR, PAL['iron'])
    mc_l = mulc(mc, 1.25)
    t = 0.035
    z0 = 0.05 if ornate else 0.0
    z1 = z0 + H
    lidh = 0.26 if ornate else 0.21
    sx_straps = (-0.3, 0.3) if ornate else (-0.26, 0.26)
    # ---- body
    k.box((-hx, -hy, z0), (hx, hy, z1), WD, wood, skip=('+z',), uv='swap')
    xi, yi, zb = hx - t, hy - t, z0 + t
    k.quad([(-xi, -yi, zb), (xi, -yi, zb), (xi, yi, zb), (-xi, yi, zb)], WD, wood_d, nh=(0, 0, 1))
    for (a, b, nh) in (((-xi, -yi), (xi, -yi), (0, 1, 0)), ((xi, -yi), (xi, yi), (-1, 0, 0)),
                       ((xi, yi), (-xi, yi), (0, -1, 0)), ((-xi, yi), (-xi, -yi), (1, 0, 0))):
        k.quad([(a[0], a[1], zb), (b[0], b[1], zb), (b[0], b[1], z1), (a[0], a[1], z1)], WD, wood_d, nh=nh, uv='swap')
    for (o, i_) in ((((-hx, -hy), (hx, -hy)), ((-xi, -yi), (xi, -yi))), (((hx, -hy), (hx, hy)), ((xi, -yi), (xi, yi))),
                    (((hx, hy), (-hx, hy)), ((xi, yi), (-xi, yi))), (((-hx, hy), (-hx, -hy)), ((-xi, yi), (-xi, -yi)))):
        k.quad([(o[0][0], o[0][1], z1), (o[1][0], o[1][1], z1), (i_[1][0], i_[1][1], z1), (i_[0][0], i_[0][1], z1)],
               WD, mulc(wood, 0.8), nh=(0, 0, 1))
    e = 0.009
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (hx + e - 0.03), sy * (hy + e - 0.03)
            k.box((cx - 0.03, cy - 0.03, z0 - (0.0 if not ornate else 0.0)), (cx + 0.03, cy + 0.03, z1 - 0.004), MT, mc,
                  skip=('-z',))
            if ornate:
                k.blob((sx * (hx - 0.05), sy * (hy - 0.05), 0.0), (0.06, 0.06, 0.055), nu=6, nv=2, mat=MT, col=GOLD_D,
                       zmin=0.0)
    for x in sx_straps:
        k.box((x - 0.035, -hy - e, z0), (x + 0.035, -hy, z1 - 0.004), MT, mc, skip=('+y', '-z'))
        k.box((x - 0.035, hy, z0), (x + 0.035, hy + e, z1 - 0.004), MT, mc, skip=('-y', '-z'))
    if ornate:
        for z in (z0 + 0.02, z1 - 0.05):
            k.box((-hx - e * 0.6, -hy - e * 0.6, z), (hx + e * 0.6, hy + e * 0.6, z + 0.03), MT, GOLD_D,
                  skip=('-z', '+z'))
    # lock plate + keyhole, side handles
    k.box((-0.065, -hy - 0.014, z1 - 0.15), (0.065, -hy, z1 - 0.02), MT, mc_l, skip=('+y',))
    k.quad([(-0.012, -hy - 0.019, z1 - 0.115), (0.012, -hy - 0.019, z1 - 0.115), (0.012, -hy - 0.019, z1 - 0.07),
            (-0.012, -hy - 0.019, z1 - 0.07)], MT, DARK, flag=NOAO, nh=(0, -1, 0))
    for sx in (-1, 1):
        k.tube([(sx * (hx + 0.006), -0.09, z0 + H * 0.62), (sx * (hx + 0.05), -0.07, z0 + H * 0.52),
                (sx * (hx + 0.05), 0.07, z0 + H * 0.52), (sx * (hx + 0.006), 0.09, z0 + H * 0.62)], 0.011, n=3, mat=MT,
               col=mc_l)
    # ---- lid (separate object, origin on the back hinge line; opens with a NEGATIVE rotation about X)
    lid = k.sub('ROT_lid', origin=(0, hy, z1), seed=5)
    lid.bake_args = dict(k.bake_args)
    n = 6
    arc = [(hy * math.cos(PI * i / n), z1 + 0.004 + lidh * math.sin(PI * i / n) ** 0.85) for i in range(n + 1)]
    for i in range(n):
        (ya, za), (yb, zb_) = arc[i], arc[i + 1]
        nh = (0, (ya + yb) / 2, (za + zb_) / 2 - z1 + 0.08)
        lid.quad([(-hx, ya, za), (hx, ya, za), (hx, yb, zb_), (-hx, yb, zb_)], WD, lid.jit(wood, 0.06), nh=nh,
                 uv='swap')
        for x in sx_straps:
            sc = 1.0 + e / hy
            lid.quad([(x - 0.035, ya * sc, z1 + (za - z1) * sc + 0.002), (x + 0.035, ya * sc, z1 + (za - z1) * sc + 0.002),
                      (x + 0.035, yb * sc, z1 + (zb_ - z1) * sc + 0.002),
                      (x - 0.035, yb * sc, z1 + (zb_ - z1) * sc + 0.002)], MT, mc, nh=nh)
        if ornate and i in (2, 3):
            sc = 1.0 + e / hy
            lid.quad([(-0.1, ya * sc, z1 + (za - z1) * sc + 0.002), (0.1, ya * sc, z1 + (za - z1) * sc + 0.002),
                      (0.1, yb * sc, z1 + (zb_ - z1) * sc + 0.002), (-0.1, yb * sc, z1 + (zb_ - z1) * sc + 0.002)],
                     MT, GOLD_D, nh=nh)
    for sx in (-1, 1):
        lid.quad([(sx * hx, y, z) for y, z in arc], WD, mulc(wood, 0.9), nh=(sx, 0, 0), uv='swap')
        lid.quad([(sx * (hx + e * 0.5), y * 1.0, z) for y, z in
                  (arc[0], arc[1], (arc[1][0] * 0.82, z1 + (arc[1][1] - z1) * 0.7), (arc[0][0] * 0.82, z1 + 0.004))],
                 MT, mc, nh=(sx, 0, 0))
        lid.quad([(sx * (hx + e * 0.5), y * 1.0, z) for y, z in
                  (arc[n], arc[n - 1], (arc[n - 1][0] * 0.82, z1 + (arc[n - 1][1] - z1) * 0.7),
                   (arc[n][0] * 0.82, z1 + 0.004))], MT, mc, nh=(sx, 0, 0))
    lid.quad([(-hx, -hy, z1 + 0.004), (hx, -hy, z1 + 0.004), (hx, hy, z1 + 0.004), (-hx, hy, z1 + 0.004)], WD, wood_d,
             nh=(0, 0, -1))
    lid.box((-0.045, -hy - 0.02, z1 - 0.06), (0.045, -hy - 0.004, z1 + 0.07), MT, mc_l, skip=())          # hasp
    if ornate:
        shard(lid, (0, -hy - 0.02, z1 - 0.01), (0, -1, 0), 0.05, 0.03, n=4, tipf=0.99, col0=CRY0, col1=CRY1)
        for x in (-hx + 0.02, hx - 0.02):
            lid.blob((x, 0, z1 + lidh + 0.01), (0.035, 0.035, 0.035), nu=5, nv=2, mat=MT, col=GOLD)
        lid.box((-hx, -0.012, z1 + lidh - 0.004), (hx, 0.012, z1 + lidh + 0.018), MT, GOLD_D, skip=('-z',))
    k.empty('ANCHOR_loot', (0, 0, z1 + 0.1))
    k.col('chest', (-hx, -hy, 0), (hx, hy, z1 + lidh))
    k.person = (0.95, -0.35)


@asset('chest', 'Iron-bound wooden treasure chest, 0.9 m wide, barrel lid = separate object ROT_lid hinged at the '
       'back', 500, footprint=[1.1, 0.7], bake=PBS, weather=False)
def chest(k):
    chest_build(k, False)


@asset('chest_ornate', 'Gilded treasure chest, 1.0 m wide, on ball feet, gold bands and a crystal set in the hasp, '
       'barrel lid = separate object ROT_lid hinged at the back', 600, footprint=[1.2, 0.8], bake=PBS, weather=False)
def chest_ornate(k):
    chest_build(k, True)


# ----------------------------------------------------------------------------- Astre crystals
def crystal_group(k, specs, col0=CRY0, col1=CRY1, mat='M_crystal', seed=0):
    """specs: (x, y, z, azimuth deg, tilt deg from vertical, length, radius[, seg])"""
    for i, sp in enumerate(specs):
        x, y, z, az, tilt, ln, r = sp[:7]
        seg = sp[7] if len(sp) > 7 else 1
        a, t = math.radians(az), math.radians(tilt)
        axis = (math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))
        shard(k, (x, y, z), axis, ln, r, n=6, col0=col0, col1=col1, mat=mat, phase=i * 0.7 + seed, seg=seg,
              tipf=0.24 + 0.1 * ((i * 7 + seed) % 3) / 2, slant=0.07, seed=i + seed, jit=0.08)


@asset('crystal_small', 'Small Astre shard cluster, 0.6 m: four cyan-white crystals on a stone', 150,
       footprint=[0.8, 0.8], bake=PBS)
def crystal_small(k):
    rock(k, (0, 0, 0.0), (0.3, 0.26, 0.16), seed=2, nu=6, nv=3, zmin=-0.5)
    crystal_group(k, [(0.0, 0.0, 0.02, 40, 8, 0.6, 0.085), (0.1, -0.06, 0.03, -30, 38, 0.36, 0.055),
                      (-0.1, 0.03, 0.03, 160, 42, 0.4, 0.06), (0.02, 0.11, 0.03, 85, 50, 0.27, 0.045),
                      (-0.04, -0.12, 0.03, 250, 55, 0.22, 0.04)])
    k.empty('GLOW_core', (0, 0, 0.3))
    k.person = (0.7, -0.3)


@asset('crystal_cluster', 'Astre crystal cluster, 2.2 m: a dozen jagged hexagonal shards bursting from cracked rock',
       500, footprint=[2.6, 2.4], bake=PBW)
def crystal_cluster(k):
    rock(k, (0, 0, 0.0), (1.0, 0.9, 0.5), seed=4, nu=9, nv=4, zmin=-0.6)
    rock(k, (0.85, -0.45, 0.0), (0.5, 0.42, 0.32), seed=6, nu=6, nv=3, zmin=-0.5)
    rock(k, (-0.8, 0.5, 0.0), (0.45, 0.5, 0.3), seed=8, nu=6, nv=3, zmin=-0.5)
    crystal_group(k, [(0.05, 0.0, 0.1, 30, 7, 2.15, 0.27, 2), (0.3, -0.15, 0.15, -25, 30, 1.45, 0.19, 2),
                      (-0.3, 0.1, 0.15, 165, 34, 1.6, 0.2, 2), (0.05, 0.38, 0.15, 95, 40, 1.15, 0.15),
                      (-0.15, -0.38, 0.15, 255, 44, 1.0, 0.14), (0.55, 0.25, 0.1, 30, 55, 0.85, 0.12),
                      (-0.55, -0.3, 0.1, 205, 58, 0.8, 0.11), (0.7, -0.5, 0.2, -40, 35, 0.6, 0.09),
                      (-0.75, 0.5, 0.2, 140, 30, 0.7, 0.1), (0.2, -0.7, 0.05, 280, 62, 0.6, 0.085),
                      (-0.1, 0.75, 0.05, 80, 65, 0.55, 0.08), (0.95, 0.05, 0.05, 5, 70, 0.45, 0.07)], seed=2)
    k.empty('GLOW_core', (0, 0, 0.9))
    k.col('cluster', (-0.8, -0.7, 0), (0.8, 0.7, 1.9))
    k.person = (1.6, -0.9)
