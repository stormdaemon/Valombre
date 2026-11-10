"""VALOMBRE world pack - biome set dressing 1: giant Astre shard, bandit / battlefield props, spider lair,
mountain ice, ash-land obsidian and the cult of the Dead Dawn (uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *
from world_sacred import candle, crystal_group

PBW = dict(ao_dist=0.9, ao_min=0.34, dirt_h=0.4, dirt=0.3)
PBS = dict(ao_dist=0.45, ao_min=0.38, dirt_h=0.2, dirt=0.25)
BIG = dict(ao_dist=1.8, ao_min=0.3, dirt_h=0.8, dirt=0.3)
PINE = 'M_bark_pine'
BARK_D = mulc(PAL['bark'], 0.42)
SILK = L('#d8d6c8')
BASALT = mulc(ROCK, 0.36)
BLOOD = L('#4a0f0c')
CULT_RED = L('#8a1f1a')


# ----------------------------------------------------------------------------- giant crystal
@asset('crystal_giant', "Giant Astre shard, 7 m: a leaning hexagonal monolith of cold cyan-white crystal that burst "
       "through the ground, ring of up-tilted cracked rock slabs, secondary shards, glowing seams", 900,
       footprint=[6.6, 6.2], bake=BIG, res=512)
def crystal_giant(k):
    rock(k, (0.1, 0.0, -0.1), (1.9, 1.7, 0.95), seed=3, nu=10, nv=4, zmin=-0.5, rough=0.2)
    # up-tilted slabs around the eruption
    for i in range(8):
        a = 2 * PI * i / 8 + 0.25
        rr = 2.0 + 0.35 * math.sin(i * 2.1)
        tilt = 0.55 + 0.25 * math.sin(i * 1.3 + 1.0)
        ln = 1.5 + 0.5 * math.cos(i * 1.7)
        with k.at((rr * math.cos(a), rr * math.sin(a), 0.1), rz=a, ry=-tilt):
            k.box((-ln * 0.75, -0.75 - 0.1 * (i % 3), -0.3), (ln * 0.55, 0.75 + 0.12 * (i % 2), 0.2), RK,
                  k.jit(ROCK, 0.06, 0.01), taper=(0.8, 0.72), shift=(0.1, 0.05 * (i % 3 - 1)))
    # main shard + secondary shards
    shard(k, (0.0, 0.05, -0.4), (0.25, -0.1, 1.0), 7.55, 0.86, n=6, seg=3, tipf=0.2, slant=0.035, tip_off=0.5, jit=0.05,
          seed=2, phase=0.3, rtop=0.74)
    crystal_group(k, [(0.75, -0.55, 0.2, -30, 26, 3.3, 0.36, 2), (-0.75, 0.25, 0.2, 170, 30, 2.6, 0.3, 2),
                      (0.25, 0.85, 0.2, 80, 36, 2.1, 0.26, 2), (-0.45, -0.85, 0.2, 245, 44, 1.6, 0.2),
                      (1.25, 0.45, 0.3, 20, 52, 1.5, 0.19), (-1.3, -0.5, 0.3, 200, 58, 1.2, 0.16),
                      (0.9, -1.4, 0.2, -65, 60, 1.0, 0.13), (-0.2, 1.5, 0.25, 100, 62, 0.9, 0.12),
                      (1.9, -0.3, 0.3, -5, 68, 0.75, 0.1), (-1.75, 0.9, 0.3, 150, 66, 0.7, 0.1)], seed=3)
    # glowing seams between the slabs
    for i in range(6):
        a = 2 * PI * (i + 0.5) / 6 + 0.1
        d = V((math.cos(a), math.sin(a), 0))
        s = V((-math.sin(a), math.cos(a), 0))
        p0, p1, p2 = d * 1.3 + V((0, 0, 0.62)), d * 2.1 + s * 0.2 + V((0, 0, 0.3)), d * 2.9 - s * 0.1 + V((0, 0, 0.06))
        for (a_, b_, w) in ((p0, p1, 0.12), (p1, p2, 0.07)):
            k.quad([a_ - s * w, b_ - s * w * 0.6, b_ + s * w * 0.6, a_ + s * w], 'M_crystal', mixc(CRY0, CRY1, 0.3),
                   nh=(0, 0, 1))
    k.empty('GLOW_core', (0.75, -0.3, 3.2))
    k.empty('GLOW_base', (0.0, 0.0, 0.9))
    k.col('base', (-1.9, -1.8, 0), (2.0, 1.8, 1.4))
    k.col('shard', (-0.7, -1.1, 1.4), (1.9, 0.8, 6.9))
    k.person = (2.9, -2.2)


# ----------------------------------------------------------------------------- bandits / battlefield
def stake(k, p0, p1, r=0.055, n=5, tip=0.3, mat=PINE, col=None):
    col = col or PAL['bark']
    p0, p1 = V(p0), V(p1)
    d = (p1 - p0).normalized()
    k.cyl(p0, p1 - d * tip, r * 1.1, r, n=n, mat=mat, col=col, caps=(False, False))
    k.cyl(p1 - d * tip, p1, r, 0.0, n=n, mat=WD, col=PAL['plank_l'], caps=(False, False))


@asset('barricade', 'Spiked log barricade (cheval de frise), 4 m: pine log on crossed sharpened stakes, lashed with '
       'rope, extra stakes pointing outwards (-Y)', 400, footprint=[4.2, 2.6], bake=PBW)
def barricade(k):
    k.cyl((-2.0, 0.0, 0.93), (2.0, 0.03, 1.0), 0.13, 0.12, n=7, mat=PINE, col=PAL['bark'], cap_mat=WD,
          cap_col=PAL['plank_l'])
    for i in range(7):
        x = -1.74 + i * 0.58
        for sg in (-1, 1):
            a = 0.62 + k.r(-0.06, 0.06)
            d = V((k.r(-0.05, 0.05), sg * math.sin(a), math.cos(a)))
            c = V((x + sg * 0.085, 0.0, 0.96))
            stake(k, c - d * 1.22, c + d * (1.0 + k.r(-0.1, 0.12)))
    for i, x in enumerate((-1.45, -0.3, 0.9, 1.75)):
        d = V((k.r(-0.1, 0.1), -math.cos(0.4), math.sin(0.4)))
        stake(k, V((x, 0.35, -0.15)), V((x, 0.35, -0.15)) + d * (1.9 + 0.2 * (i % 2)), r=0.05)
    for x in (-1.16, 1.16):
        k.tube([(x, 0.17 * math.cos(a), 0.965 + 0.17 * math.sin(a)) for a in
                [2 * PI * j / 6 for j in range(7)]], 0.022, n=3, caps=False)
    k.col('barricade', (-2.0, -0.75, 0), (2.0, 0.75, 1.5))
    k.person = (2.6, -0.5)


@asset('cage_hanging', 'Iron gibbet cage hanging from a timber gallows post (5 m), a skeleton inside', 500,
       footprint=[2.4, 1.2], bake=PBW)
def cage_hanging(k):
    px = 0.8
    k.box((px - 0.11, -0.11, -0.6), (px + 0.11, 0.11, 4.9), WD, k.jit(PAL['beam']), skip=('-z',), uv='along',
          taper=(0.9, 0.9))
    k.beam((px + 0.25, 0, 4.62), (-0.85, 0, 4.72), 0.16, 0.17, WD, k.jit(PAL['beam_d']))
    k.beam((px, 0, 3.6), (-0.1, 0, 4.6), 0.11, 0.11, WD, k.jit(PAL['beam']), skip=('c0', 'c1'))
    for (x, y, r) in ((px + 0.25, 0.1, 0.2), (px - 0.2, -0.2, 0.17), (px - 0.05, 0.25, 0.15)):
        rock(k, (x, y, 0.03), (r, r * 0.85, r * 0.6), seed=x, nu=5, nv=2)
    cx = -0.5
    k.tube([(cx, 0, 4.64), (cx + 0.02, 0, 4.4), (cx, 0, 4.18)], 0.02, n=3, mat=IR, col=PAL['iron'], caps=False)
    prof = [(0.05, 4.18), (0.2, 4.02), (0.33, 3.7), (0.36, 3.05), (0.3, 2.35)]
    nb = 6
    ic = k.jit(RUST, 0.1)
    for i in range(nb):
        a = 2 * PI * i / nb
        k.tube([(cx + r * math.cos(a), r * math.sin(a), z) for r, z in prof], 0.014, n=3, mat=IR,
               col=mixc(PAL['iron'], RUST, 0.4), caps=False)
    for (r, z) in prof[2:]:
        k.tube([(cx + (r + 0.008) * math.cos(a), (r + 0.008) * math.sin(a), z) for a in
                [2 * PI * j / nb for j in range(nb + 1)]], 0.017, n=3, mat=IR, col=PAL['iron'], caps=False)
    k.quad([(cx + 0.3 * math.cos(2 * PI * j / nb), 0.3 * math.sin(2 * PI * j / nb), 2.35) for j in range(nb)], IR,
           mixc(PAL['iron'], RUST, 0.5), double=True)
    # the occupant
    skull(k, (cx + 0.03, -0.05, 3.62), s=1.0, rz=0.3, rx=0.35, nu=6)
    k.blob((cx, 0.02, 3.2), (0.15, 0.11, 0.26), nu=6, nv=3, mat='M_bone', col=mulc(BONE, 0.85))
    k.blob((cx, 0.02, 2.82), (0.13, 0.1, 0.12), nu=5, nv=2, mat='M_bone', col=mulc(BONE, 0.8))
    for sx in (-1, 1):
        bone(k, (cx + sx * 0.09, -0.02, 2.8), (cx + sx * 0.14, -0.2, 2.42), r=0.022, knobs=False)
        bone(k, (cx + sx * 0.17, 0.0, 3.4), (cx + sx * 0.24, -0.05, 2.95), r=0.016, knobs=False)
    k.col('post', (px - 0.2, -0.2, 0), (px + 0.2, 0.2, 4.9))
    k.person = (-0.5, -0.9)


@asset('skull_pike', 'Warning pike: leaning stake with a skull on top and a rag', 150, footprint=[0.7, 0.7], bake=PBS)
def skull_pike(k):
    top = V((0.1, 0.04, 2.25))
    stake(k, (0, 0, -0.3), top, r=0.035, tip=0.2, mat='M_bark_oak')
    skull(k, (0.085, 0.03, 2.02), s=1.15, rz=0.25, rx=0.2, ry=0.05)
    k.beam((-0.22, 0.02, 1.62), (0.3, 0.02, 1.68), 0.035, 0.035, WD, PAL['beam_l'])
    rag(k, (-0.2, 0.0, 1.63), (1, 0, 0.1), (0, -0.05, -1), 0.3, 0.55, nu=1, nv=3, col=L('#7a2c22'), wave=0.04, seed=2)
    k.col('pike', (-0.1, -0.1, 0), (0.2, 0.15, 2.2))
    k.person = (0.8, -0.3)


@asset('bone_pile', 'Heap of bones: two skulls, long bones and rib arcs', 300, footprint=[1.6, 1.4], bake=PBS)
def bone_pile(k):
    skull(k, (0.12, -0.22, 0.2), s=1.1, rz=0.4, rx=0.3, nu=6)
    skull(k, (-0.38, 0.18, 0.1), s=1.05, rz=2.3, rx=-0.9, ry=0.4, nu=6, jaw=False)
    for (a, b) in (((-0.6, -0.3, 0.04), (0.1, -0.5, 0.07)), ((0.2, 0.35, 0.05), (0.62, -0.15, 0.2)),
                   ((-0.15, 0.1, 0.12), (0.45, 0.3, 0.06))):
        bone(k, a, b, r=0.024)
    for (a, b) in (((-0.5, 0.45, 0.03), (0.0, 0.55, 0.05)), ((0.3, -0.45, 0.03), (0.7, -0.35, 0.04)),
                   ((-0.3, -0.1, 0.06), (-0.05, -0.38, 0.22)), ((0.0, 0.0, 0.03), (0.3, 0.1, 0.25))):
        bone(k, a, b, r=0.018, knobs=False)
    for i in range(4):
        x = -0.25 + i * 0.11
        k.tube([(x, 0.25, 0.02), (x + 0.02, 0.45, 0.2), (x + 0.03, 0.62, 0.22), (x + 0.02, 0.75, 0.05)], 0.012, n=3,
               mat='M_bone', col=k.jit(BONE, 0.08), caps=False)
    k.person = (0.95, -0.4)


# ----------------------------------------------------------------------------- spider lair
@asset('spider_cocoon', 'Silk-wrapped victim, 1.8 m, standing and leaning, anchored by web strands, a boot sticking '
       'out', 250, footprint=[1.6, 1.4], bake=PBW)
def spider_cocoon(k):
    prof = [(0.09, 0.0), (0.2, 0.1), (0.24, 0.42), (0.21, 0.78), (0.27, 1.12), (0.3, 1.36), (0.2, 1.5), (0.19, 1.64),
            (0.12, 1.76), (0.0, 1.8)]

    def deform(p):
        n = mnoise.noise(V((p.x * 3.0, p.y * 3.0, p.z * 2.2)) + V((3, 1, 7)))
        s = 1.0 + 0.12 * n
        return V((p.x * s + 0.14 * p.z, p.y * s - 0.07 * p.z, p.z))
    k.lathe((0, 0, 0), prof, n=8, mat=CL, col=SILK, sy=0.78, deform=deform,
            colfn=lambda i, r, z: mulc(SILK, 1.0 if i % 2 else 0.78))
    k.box((-0.02, -0.34, 0.0), (0.09, -0.1, 0.1), 'M_leather', PAL['leather'], skip=('-z', '+y'), taper=(0.85, 0.8))
    for (p, q) in (((0.2, 0.0, 1.45), (1.05, 0.3, 0.0)), ((0.12, -0.1, 1.2), (-0.75, -0.55, 0.0)),
                   ((0.05, 0.12, 0.9), (-0.5, 0.75, 0.0)), ((0.25, -0.12, 1.55), (0.7, -0.7, 0.0)),
                   ((0.22, 0.1, 1.7), (0.15, 0.9, 0.0)), ((0.1, -0.02, 0.6), (0.9, -0.2, 0.0))):
        p, q = V(p), V(q)
        s = (q - p).cross(V((0, 0, 1))).normalized()
        k.quad([p - s * 0.035, q - s * 0.008, q + s * 0.008, p + s * 0.035], CL, mulc(SILK, 0.92), double=True)
    k.col('cocoon', (-0.25, -0.25, 0), (0.45, 0.25, 1.75))
    k.person = (1.2, -0.5)


@asset('egg_sacs', 'Cluster of seven pale spider egg sacs on a web mat, 0.9 m high', 250, footprint=[1.8, 1.6],
       bake=PBS)
def egg_sacs(k):
    k.blob((0, 0, 0.0), (0.7, 0.6, 0.12), nu=6, nv=2, mat=CL, col=mulc(SILK, 0.55), zmin=0.0)
    sacs = [(0.0, 0.05, 0.36, 0.38), (0.42, -0.2, 0.26, 0.27), (-0.42, -0.1, 0.24, 0.26), (-0.15, 0.42, 0.22, 0.24),
            (0.3, 0.38, 0.19, 0.2), (0.05, -0.42, 0.17, 0.18), (-0.02, 0.1, 0.78, 0.2)]
    for i, (x, y, z, r) in enumerate(sacs):
        c = mixc(L('#cfd2ba'), L('#a9b08c'), (i * 37 % 10) / 10)
        k.lathe((x, y, z), [(0.0, -r * 0.95), (r * 0.75, -r * 0.6), (r, 0.0), (r * 0.72, r * 0.62), (0.0, r * 0.95)],
                n=5 if i else 6, mat=CL, phase=i * 0.5, sx=1.0, sy=0.92,
                colfn=lambda j, rr, zz, c=c: mulc(c, 0.55 + 0.45 * (j / 4.0)))
    for (p, q) in (((0.3, 0.0, 0.5), (0.95, 0.5, 0.0)), ((-0.3, 0.1, 0.45), (-1.0, -0.4, 0.0)),
                   ((0.0, 0.3, 0.6), (-0.3, 0.95, 0.0))):
        p, q = V(p), V(q)
        s = (q - p).cross(V((0, 0, 1))).normalized()
        k.quad([p - s * 0.03, q - s * 0.008, q + s * 0.008, p + s * 0.03], CL, mulc(SILK, 0.9), double=True)
    k.col('eggs', (-0.6, -0.55, 0), (0.6, 0.55, 0.8))
    k.person = (1.2, -0.5)


@asset('bramble_arch', 'Giant thorny bramble arch, 6.4 m wide, 4.6 m high (opening 4.4 m wide, 3.3 m clear at the '
       'axis): three twisted dark vines with thorns, tendrils and glowing violet corruption veins', 900,
       footprint=[7.4, 2.6], bake=dict(ao_dist=1.0, ao_min=0.4, dirt_h=0.5, dirt=0.2), res=448)
def bramble_arch(k):
    N = 14

    def path(t, ph, ro):
        a = PI * t
        x = -2.95 * math.cos(a)
        z = 4.05 * math.sin(a) ** 0.82 - 0.55
        w = 0.5 + 0.5 * math.sin(a)
        ox = ro * math.cos(ph + 5.2 * t) * (0.6 + 0.4 * w)
        oy = ro * math.sin(ph + 5.2 * t) * 1.5
        return V((x + ox * math.sin(a), oy, z + ox * math.cos(a) * 0.4 + 0.25 * math.sin(ph * 2 + 9 * t) * w))
    vines = []
    for vi, (ph, ro, r0) in enumerate(((0.0, 0.36, 0.3), (2.1, 0.4, 0.26), (4.2, 0.33, 0.23))):
        pts = [path(i / N, ph, ro) for i in range(N + 1)]
        rads = [r0 * (0.58 + 0.42 * abs(1 - 2 * i / N) ** 1.3) for i in range(N + 1)]
        fr = vine(k, pts, rads, n=5, mat='M_bark_oak', col=k.jit(BARK_D, 0.1), caps=(False, False), twist=0.3)
        vines.append(fr)
        vein(k, fr, 0.6 + vi * 2.0, w=0.075, off=0.022, col=RUNE_V, spin=0.42, i0=1, i1=N - 1)
        for i in range(1, N):
            if (i + vi) % 2:
                continue
            ang = i * 2.4 + vi
            p = surf(fr[i], ang, -0.02)
            d = surf(fr[i], ang, 1.0) - fr[i][0]
            d = d.normalized() + V((0, 0, 0.25))
            thorn(k, p, d, length=0.34 + 0.16 * math.sin(i * 1.7) ** 2, r=0.06, col=mulc(BARK_D, 0.8))
    # tendrils
    for (i, vi, dirv, ln, sd) in ((2, 0, (-0.8, -0.5, 0.5), 1.5, 1), (12, 1, (0.9, 0.5, 0.5), 1.4, 2),
                                  (7, 2, (0.1, -0.7, 0.9), 1.3, 3), (6, 0, (-0.3, 0.8, 0.7), 1.1, 4),
                                  (10, 2, (0.6, -0.6, -0.3), 1.2, 5), (4, 1, (-0.6, 0.6, -0.2), 1.0, 6)):
        p0 = vines[vi][i][0]
        d = V(dirv).normalized()
        s = d.cross(V((0, 0, 1))).normalized()
        pts = [p0 + d * (ln * f) + s * (0.35 * ln * math.sin(f * 3.4 + sd)) + V((0, 0, 0.25 * ln * math.sin(f * 2.6)))
               for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
        fr = vine(k, pts, [0.1, 0.085, 0.065, 0.045, 0.02], n=4, mat='M_bark_oak', col=mulc(BARK_D, 0.9),
                  caps=(False, False))
        thorn(k, surf(fr[2], sd, -0.01), surf(fr[2], sd, 1.0) - fr[2][0], length=0.22, r=0.035, col=mulc(BARK_D, 0.8))
    for sx in (-1, 1):
        rock(k, (sx * 3.05, 0.1 * sx, -0.05), (0.75, 0.65, 0.4), seed=sx + 3, nu=7, nv=3, col=mulc(ROCK, 0.8))
        k.col('base_l' if sx < 0 else 'base_r', (sx * 3.05 - 0.65, -0.75, 0), (sx * 3.05 + 0.65, 0.75, 2.4))
    k.empty('GLOW_veins', (0, 0, 3.4))
    k.person = (0.5, -0.9)


@asset('cave_mouth', 'Rock archway of a cave / lair entrance, 9 m wide, 5.6 m high, opening 4.2 m wide x 3.3 m high '
       'recessed 2.7 m to a black back wall (not enterable), boulders, stalactites, cobwebs, bones', 1200,
       footprint=[10.0, 7.2], bake=dict(ao_dist=2.4, ao_min=0.22, dirt_h=0.8, dirt=0.3), res=512)
def cave_mouth(k):
    NU = 18

    def inner(u, sc=1.0):
        a = PI * u
        return (-2.1 * sc * math.cos(a), 3.3 * sc * math.sin(a) ** 0.72 if 0 < u < 1 else -0.7)

    def outer(u, sx=1.0, sz=1.0):
        a = PI * u
        bump = 1.0 + 0.1 * math.sin(a * 3.0 + 0.6) + 0.06 * math.sin(a * 7.0)
        return (-4.5 * sx * math.cos(a) * (1.0 + 0.05 * math.sin(a * 2.0)), 5.5 * sz * bump * math.sin(a) ** 0.6
                if 0 < u < 1 else -0.7)
    spec = [(lambda u: inner(u, 0.78), 2.4), (lambda u: inner(u, 0.9), 1.1), (lambda u: inner(u, 1.0), -0.25),
            (None, -0.8), (lambda u: outer(u, 0.93, 0.93), -0.35), (lambda u: outer(u, 1.0, 1.0), 1.3),
            (lambda u: outer(u, 0.9, 0.8), 3.2), (lambda u: outer(u, 0.72, 0.45), 4.6), (lambda u: outer(u, 0.6, 0.0), 5.4)]
    rows = []
    for ri, (fn, y) in enumerate(spec):
        row = []
        for i in range(NU + 1):
            u = i / NU
            if fn is None:
                a, b = inner(u, 1.0), outer(u, 0.93, 0.93)
                x, z = lerp(a[0], b[0], 0.45), lerp(a[1], b[1], 0.45)
            else:
                x, z = fn(u)
            if ri == 8:
                z = -0.6
            p = V((x, y, z))
            if ri >= 2:
                n3 = mnoise.noise_vector(p * 0.42 + V((2.2, 5.1, 0.7)))
                amp = 0.42 if ri != 2 else 0.2
                p = p + V((n3.x * amp, n3.y * amp, n3.z * amp * (0.2 if z < 0.3 else 1.0)))
            row.append(p)
        rows.append(row)

    def cf(p):
        dark = sstep(-0.6, 1.6, p.y) if (abs(p.x) < 2.4 and p.z < 3.6) else 0.0
        return mulc(ROCK, (1.0 - 0.72 * dark) * (0.93 + 0.1 * mnoise.noise(p * 0.5)))
    k.grid(rows, RK, ROCK, smooth=True, colfn=cf)
    k.quad([rows[0][i] + V((0, -0.02, 0)) for i in range(NU + 1)], 'M_obsidian', mulc(OBS, 0.5), nh=(0, -1, 0),
           flag=NOAO)
    # boulders, stalactites, webs, bones
    for (c, r, sd) in (((-4.6, -1.0, 0.1), (1.2, 1.0, 0.9), 2), ((4.4, -0.9, 0.1), (1.0, 1.1, 0.75), 5),
                       ((-3.2, -1.9, 0.0), (0.7, 0.6, 0.45), 7), ((3.0, -1.8, 0.0), (0.55, 0.6, 0.4), 9),
                       ((5.3, 0.9, 0.2), (1.1, 1.3, 1.0), 11), ((-5.2, 1.4, 0.2), (1.0, 1.2, 0.9), 13)):
        rock(k, c, r, seed=sd, nu=8, nv=4, zmin=-0.4)
    for (x, ln) in ((-1.25, 0.75), (-0.5, 0.5), (0.15, 0.95), (0.85, 0.55), (1.45, 0.7)):
        z = 3.3 * max(0.0, 1 - (x / 2.1) ** 2) ** 0.36
        k.cyl((x, -0.15, z + 0.12), (x + 0.05, -0.2, z - ln), 0.16, 0.0, n=4, mat=RK, col=mulc(ROCK, 0.8),
              caps=(False, False), smooth=False)
    for sx in (-1, 1):
        c = V((sx * 1.9, -0.3, 2.35))
        tips = [V((sx * 1.05, -0.33, 3.0)), V((sx * 1.2, -0.36, 2.45)), V((sx * 1.35, -0.33, 1.75)),
                V((sx * 1.95, -0.3, 1.3))]
        for i, (a, b) in enumerate(zip(tips[:-1], tips[1:])):
            m = (a + b) / 2
            m = c.lerp(m, 0.62)
            k.quad([c, a, m], CL, mulc(SILK, 0.5), double=True)
            k.quad([c, m, b], CL, mulc(SILK, 0.42), double=True)
    skull(k, (-1.4, -1.5, 0.1), s=1.1, rz=-0.6, rx=0.2, nu=6)
    bone(k, (-0.9, -1.7, 0.04), (-0.3, -1.4, 0.05), r=0.025)
    bone(k, (0.6, -1.3, 0.04), (1.2, -1.75, 0.05), r=0.022, knobs=False)
    k.col('rock', (-4.4, -0.6, 0), (4.4, 4.6, 5.3))
    k.col('left', (-5.6, -1.9, 0), (-3.4, 0.3, 1.6))
    k.col('right', (3.4, -1.9, 0), (5.4, 0.3, 1.5))
    k.person = (0.9, -1.5)


# ----------------------------------------------------------------------------- mountain
def ice_group(k, specs, seed=0):
    for i, sp in enumerate(specs):
        x, y, z, az, tilt, ln, r = sp[:7]
        seg = sp[7] if len(sp) > 7 else 1
        a, t = math.radians(az), math.radians(tilt)
        axis = (math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))
        shard(k, (x, y, z), axis, ln, r, n=5, col0=ICE0, col1=ICE1, mat='M_ice', phase=i * 0.8 + seed, seg=seg,
              tipf=0.55, slant=0.03, seed=i + seed, jit=0.12, tip_off=0.15, rtop=0.72)


@asset('ice_spikes_a', 'Cluster of ice spikes on frozen rock, tallest 5 m, upright', 500, footprint=[4.0, 3.6],
       bake=BIG, weather=dict(top=0.0, base=0.0, tint=0.1))
def ice_spikes_a(k):
    rock(k, (0, 0, -0.1), (1.6, 1.4, 0.75), seed=6, nu=9, nv=4, zmin=-0.5, col=mulc(ROCK, 1.0))
    rock(k, (1.3, -0.7, -0.1), (0.8, 0.7, 0.5), seed=8, nu=7, nv=3, zmin=-0.5)
    rock(k, (-1.2, 0.8, -0.1), (0.75, 0.8, 0.45), seed=10, nu=7, nv=3, zmin=-0.5)
    ice_group(k, [(0.0, 0.0, 0.2, 20, 5, 4.9, 0.42, 2), (0.55, -0.3, 0.2, -30, 14, 3.4, 0.32, 2),
                  (-0.55, 0.25, 0.2, 160, 17, 3.0, 0.3, 2), (0.15, 0.6, 0.2, 80, 22, 2.3, 0.25),
                  (-0.3, -0.6, 0.2, 250, 24, 2.0, 0.22), (1.2, -0.7, 0.2, -30, 30, 1.6, 0.2),
                  (-1.15, 0.8, 0.2, 140, 28, 1.7, 0.2), (0.9, 0.5, 0.15, 30, 40, 1.2, 0.16),
                  (-0.95, -0.4, 0.15, 200, 44, 1.1, 0.15), (0.3, -1.1, 0.1, -80, 50, 0.9, 0.13)], seed=1)
    k.col('ice', (-1.3, -1.2, 0), (1.4, 1.2, 3.6))
    k.person = (2.3, -1.2)


@asset('ice_spikes_b', 'Leaning fan of ice spikes on frozen rock, 3.8 m, swept towards +X like a frozen wave', 500,
       footprint=[5.2, 3.4], bake=BIG, weather=dict(top=0.0, base=0.0, tint=0.1))
def ice_spikes_b(k):
    rock(k, (-0.3, 0, -0.1), (1.9, 1.2, 0.6), seed=16, nu=9, nv=4, zmin=-0.5)
    rock(k, (1.4, 0.5, -0.1), (0.9, 0.7, 0.4), seed=18, nu=7, nv=3, zmin=-0.5)
    sp = []
    for i in range(11):
        x = -1.5 + i * 0.3
        tilt = 16 + i * 4.6
        ln = 4.1 - abs(i - 4.5) * 0.36 - (i % 2) * 0.55
        sp.append((x, 0.34 * math.sin(i * 1.9), 0.15, 8 * math.sin(i * 2.3), tilt, ln, 0.3 - 0.012 * i) +
                  ((2,) if ln > 2.9 else ()))
    ice_group(k, sp, seed=4)
    k.col('ice', (-1.9, -0.9, 0), (2.4, 0.9, 2.8))
    k.person = (0.5, -1.7)


@asset('frost_cairn', 'Stone cairn, 1.5 m, with two skulls, icicles and a tattered banner on a crooked pole (3.4 m)',
       400, footprint=[2.2, 2.0], bake=PBW, weather=dict(top=0.1, base=0.2))
def frost_cairn(k):
    stones = [(0.5, 0.05, 0.2, 0.46), (-0.42, 0.25, 0.2, 0.44), (-0.12, -0.5, 0.18, 0.42), (0.1, 0.5, 0.18, 0.38),
              (0.22, -0.12, 0.58, 0.4), (-0.25, 0.12, 0.6, 0.36), (0.0, 0.08, 0.95, 0.34), (0.05, -0.02, 1.25, 0.25)]
    for i, (x, y, z, r) in enumerate(stones):
        rock(k, (x, y, z), (r, r * 0.85, r * 0.6), seed=i * 3 + 1, nu=5, nv=3, zmin=-0.7, rz=i * 1.1,
             col=k.jit(ROCK, 0.06, 0.01))
    skull(k, (0.42, -0.4, 0.42), s=1.15, rz=0.5, rx=0.25, nu=6)
    skull(k, (-0.02, -0.14, 1.47), s=1.1, rz=-0.2, rx=0.1, nu=6, jaw=False)
    top = V((-0.42, 0.42, 3.4))
    k.cyl((-0.22, 0.3, 0.3), top, 0.04, 0.03, n=4, mat='M_bark_pine', col=PAL['bark'], caps=(False, True))
    k.beam(top + V((-0.05, 0, -0.25)), top + V((0.85, -0.1, -0.2)), 0.04, 0.04, WD, PAL['beam_l'])
    rag(k, top + V((0.0, -0.02, -0.26)), (1, -0.1, 0.05), (0.08, 0, -1), 0.8, 1.35, nu=2, nv=4, col=L('#4d6278'),
        wave=0.04, ragged=0.35, seed=7)
    for (x, y, z, ln) in ((0.62, -0.1, 0.42, 0.26), (-0.55, 0.05, 0.4, 0.22), (0.3, 0.45, 0.72, 0.3),
                          (-0.3, -0.25, 0.8, 0.25)):
        k.cyl((x, y, z), (x, y, z - ln), 0.035, 0.0, n=3, mat='M_ice', col=ICE1, caps=(False, False), smooth=False)
    k.col('cairn', (-0.7, -0.7, 0), (0.75, 0.7, 1.5))
    k.person = (1.3, -0.5)


# ----------------------------------------------------------------------------- ash lands
def ember_crack(k, rings, ri, fi, pts, w=0.07, col=None):
    """zig-zag molten crack on facet fi between rings ri and ri + 1 of a shard()"""
    n = len(rings[ri])
    pan = Panel(rings[ri][fi % n], rings[ri][(fi + 1) % n], rings[ri + 1][(fi + 1) % n], rings[ri + 1][fi % n])
    for a, b in zip(pts[:-1], pts[1:]):
        stroke(k, pan, a, b, w=w, off=0.02, col=col or EMB, mat='M_ember')


def spire(k, p0, axis, ln, r, seg=3, seed=0, cracks=(), n=5, tipf=0.3):
    rings, apex = shard(k, p0, axis, ln, r, n=n, seg=seg, tipf=tipf, col0=mulc(OBS, 0.85), col1=OBS, mat='M_obsidian',
                        slant=0.05, jit=0.16, seed=seed, phase=seed * 0.7, tip_off=0.6, rtop=0.55)
    for (ri, fi, sg) in cracks:
        z = [(0.5 + 0.18 * sg, 0.0), (0.5 - 0.2 * sg, 0.3), (0.5 + 0.14 * sg, 0.62), (0.5 - 0.1 * sg, 1.0)]
        ember_crack(k, rings, ri, fi, z, w=0.05 + r * 0.08, col=EMB if (ri + fi) % 2 else EMB_H)
    return rings


@asset('obsidian_spire_a', 'Jagged black obsidian spire, 5 m, with two side shards on scorched rock, glowing ember '
       'cracks', 500, footprint=[3.2, 3.0], bake=BIG, weather=dict(top=0.0, base=0.0, tint=0.1))
def obsidian_spire_a(k):
    rock(k, (0, 0, -0.2), (1.4, 1.25, 0.7), seed=21, nu=8, nv=3, zmin=-0.6, col=BASALT)
    spire(k, (0.0, 0.0, -0.6), (0.1, -0.06, 1.0), 5.65, 0.72, seg=3, seed=3,
          cracks=((0, 0, 1), (1, 0, -1), (1, 3, 1), (2, 1, 1), (0, 2, -1), (2, 4, -1)))
    spire(k, (0.8, 0.35, -0.4), (0.5, 0.2, 1.0), 2.9, 0.4, seg=2, seed=5, cracks=((0, 1, 1), (1, 3, -1)))
    spire(k, (-0.75, -0.35, -0.4), (-0.55, -0.15, 1.0), 2.2, 0.34, seg=2, seed=8, cracks=((0, 4, 1),))
    spire(k, (-0.2, 0.9, -0.3), (-0.2, 0.7, 1.0), 1.5, 0.26, seg=1, seed=9)
    k.empty('GLOW_ember', (0.1, -0.2, 1.4))
    k.col('spire', (-0.9, -0.8, 0), (1.0, 0.8, 4.2))
    k.person = (1.9, -1.0)


@asset('obsidian_spire_b', 'Great obsidian spire, 9 m, leaning, with three side shards on scorched rock, glowing '
       'ember cracks', 500, footprint=[5.0, 4.6], bake=BIG, weather=dict(top=0.0, base=0.0, tint=0.1))
def obsidian_spire_b(k):
    rock(k, (0, 0, -0.2), (2.2, 1.9, 0.95), seed=31, nu=9, nv=3, zmin=-0.6, col=BASALT)
    spire(k, (0.0, 0.0, -0.8), (-0.14, 0.08, 1.0), 9.9, 1.15, seg=4, seed=4, n=6,
          cracks=((0, 0, 1), (1, 0, -1), (2, 1, 1), (1, 3, 1), (2, 4, -1), (3, 2, 1), (0, 4, -1), (3, 5, -1)))
    spire(k, (1.3, -0.5, -0.5), (0.45, -0.2, 1.0), 5.0, 0.6, seg=2, seed=6, cracks=((0, 0, 1), (1, 2, -1)))
    spire(k, (-1.2, 0.8, -0.5), (-0.5, 0.3, 1.0), 3.6, 0.5, seg=2, seed=7, cracks=((0, 3, 1), (1, 1, -1)))
    spire(k, (0.5, 1.4, -0.4), (0.25, 0.75, 1.0), 2.3, 0.36, seg=1, seed=11, cracks=((0, 2, 1),))
    spire(k, (-0.9, -1.2, -0.3), (-0.4, -0.7, 1.0), 1.7, 0.3, seg=1, seed=12)
    k.empty('GLOW_ember', (0.0, -0.3, 2.2))
    k.col('spire', (-1.5, -1.3, 0), (1.5, 1.3, 7.0))
    k.person = (2.8, -1.6)


def half_sun(k, c, r, side=1, rz=0.0, ry=0.0, mat='M_metal_bronze', col=None, rays=5):
    """Half of a split brass sun (flat, double sided): side = +1 right half, -1 left half. In the XZ plane."""
    col = col or BRASS
    with k.at(c, rz=rz, ry=ry):
        m = 6
        pts = [(side * r * 0.55 * math.sin(PI * i / m), 0, r * 0.55 * math.cos(PI * i / m)) for i in range(m + 1)]
        k.quad(pts, mat, col, double=True, back_col=mulc(col, 0.8))
        for i in range(rays):
            a = PI * (i + 0.5) / rays
            da = PI / rays * 0.33
            ln = r if i % 2 == 0 else r * 0.8
            k.quad([(side * r * 0.6 * math.sin(a - da), 0, r * 0.6 * math.cos(a - da)),
                    (side * r * 0.6 * math.sin(a + da), 0, r * 0.6 * math.cos(a + da)),
                    (side * ln * math.sin(a), 0, ln * math.cos(a))], mat, mulc(col, 1.1), double=True,
                   back_col=mulc(col, 0.8))


def iron_brazier(k, c, h=1.25, r=0.34, fire=None):
    x, y, z = c
    for i in range(3):
        a = 2 * PI * i / 3 + 0.5
        k.beam((x + 0.36 * math.cos(a), y + 0.36 * math.sin(a), z), (x + 0.08 * math.cos(a), y + 0.08 * math.sin(a), z + h),
               0.035, 0.035, IR, PAL['iron'], skip=('c0', 'c1'), uv='box')
    k.lathe((x, y, z + h - 0.12), [(0.08, 0.0), (r * 0.8, 0.1), (r, 0.26), (r * 0.9, 0.26), (r * 0.72, 0.14), (0.0, 0.12)],
            n=8, mat=IR, col=PAL['iron'], split=(2, 3))
    k.quad([(x + r * 0.78 * math.cos(2 * PI * j / 7), y + r * 0.78 * math.sin(2 * PI * j / 7), z + h + 0.05)
            for j in range(7)], 'M_ember', mulc(EMB, 0.9), flag=NOAO)
    for i in range(3):
        a = i * 2.2
        k.blob((x + 0.12 * math.cos(a), y + 0.12 * math.sin(a), z + h + 0.05), (0.09, 0.08, 0.075), nu=5, nv=2,
               mat='M_ember', col=EMB_H if i % 2 else EMB, zmin=0.0, flag=NOAO)
    if fire:
        k.empty(fire, (x, y, z + h + 0.18))


@asset('cult_altar', "Altar of the Dead Dawn: blood-stained basalt block on two steps, ember runes, candles, two iron "
       "tripod braziers, an iron gallows frame from which the two halves of a split brass sun hang on chains", 1200,
       footprint=[5.6, 5.4], bake=dict(ao_dist=1.2, ao_min=0.3, dirt_h=0.4, dirt=0.25), res=512,
       weather=dict(top=0.0, base=0.0, tint=0.12))
def cult_altar(k):
    for i, (hx, hy, z) in enumerate(((2.0, 1.4, 0.2), (1.6, 1.05, 0.4))):
        k.box((-hx, -hy, -0.3 if i == 0 else z - 0.2), (hx, hy, z), RK, k.jit(BASALT, 0.05), skip=('-z',),
              taper=(0.985, 0.98))
    k.box((-1.0, -0.5, 0.4), (1.0, 0.5, 0.56), RK, mulc(BASALT, 1.15), skip=('-z',), taper=(0.94, 0.9))
    k.box((-0.9, -0.42, 0.56), (0.9, 0.42, 1.2), RK, BASALT, skip=('-z', '+z'), taper=(1.0, 1.0))
    k.box((-0.93, -0.45, 1.2), (0.93, 0.45, 1.26), RK, BASALT, skip=('-z', '+z'), taper=(1.16, 1.22))
    k.box((-1.1, -0.57, 1.26), (1.1, 0.57, 1.4), RK, mulc(BASALT, 1.2), skip=('-z',))
    # blood: pool on the slab + runs down the front
    k.quad([(0.75 * math.cos(a) * (1 + 0.25 * math.sin(3 * a)) - 0.1, 0.36 * math.sin(a) * (1 + 0.2 * math.cos(2 * a)),
             1.415) for a in [2 * PI * i / 9 for i in range(9)]], RK, BLOOD, flag=NOAO, nh=(0, 0, 1))
    for (x, w, ln) in ((-0.55, 0.07, 0.5), (-0.2, 0.05, 0.75), (0.25, 0.08, 0.38), (0.6, 0.05, 0.6)):
        k.quad([(x - w, -0.585, 1.4), (x + w, -0.585, 1.4), (x + w * 0.5, -0.585, 1.4 - 0.13), (x - w * 0.5, -0.585, 1.4 - 0.13)],
               RK, BLOOD, flag=NOAO, nh=(0, -1, 0))
        k.quad([(x - w * 0.5, -0.436, 1.2), (x + w * 0.5, -0.436, 1.2), (x + w * 0.3, -0.436, 1.2 - ln),
                (x - w * 0.3, -0.436, 1.2 - ln)], RK, BLOOD, flag=NOAO, nh=(0, -1, 0))
    front = Panel((-0.9, -0.42, 0.56), (0.9, -0.42, 0.56), (0.9, -0.42, 1.2), (-0.9, -0.42, 1.2))
    for i, g in enumerate(('zig', 'eye', 'x')):
        glyph(k, front, g, 0.25 + i * 0.25, 0.48, size=0.32, col=L('#ff5a2a'), w=0.04)
    # candles (with FIRE nodes), bowl, dagger, skulls
    for i, (x, y, z, h) in enumerate(((-0.92, -0.38, 1.4, 0.24), (0.9, 0.3, 1.4, 0.3), (-1.35, -0.8, 0.4, 0.2))):
        candle(k, (x, y, z), h, r=0.03)
        k.empty('FIRE_candle_%d' % (i + 1), (x, y, z + h + 0.05))
    for (x, y, z, h) in ((0.82, -0.4, 1.4, 0.12), (1.3, -0.85, 0.4, 0.13), (-0.8, 0.35, 1.4, 0.16)):
        candle(k, (x, y, z), h, r=0.028, lit=False)
    k.lathe((0.45, 0.0, 1.4), [(0.06, 0.0), (0.16, 0.07), (0.17, 0.1), (0.14, 0.09), (0.0, 0.05)], n=7,
            mat='M_metal_bronze', col=BRASS, split=(2, 3), colfn=lambda i, r, z: BLOOD if i >= 3 else BRASS)
    with k.at((-0.25, -0.15, 1.43), rz=0.5):
        k.loft([(-0.022, 0, -0.004), (0.022, 0, -0.004), (0.022, 0, 0.004), (-0.022, 0, 0.004)],
               [(-0.004, 0.3, -0.002), (0.004, 0.3, -0.002), (0.004, 0.3, 0.002), (-0.004, 0.3, 0.002)],
               'M_metal_steel', L('#8d8a86'))
        k.box((-0.06, -0.015, -0.008), (0.06, 0.0, 0.008), IR, PAL['iron_l'])
        k.box((-0.014, -0.13, -0.008), (0.014, -0.015, 0.008), 'M_leather', PAL['leather'])
    skull(k, (-1.55, -1.05, 0.3), s=1.1, rz=-0.5, rx=0.15, nu=6)
    skull(k, (1.0, -0.7, 0.51), s=1.05, rz=0.6, rx=0.2, nu=6)
    # braziers
    iron_brazier(k, (-2.35, -0.9, 0.0), fire='FIRE_brazier_l')
    iron_brazier(k, (2.35, -0.9, 0.0), fire='FIRE_brazier_r')
    # gallows frame + split sun
    for sx in (-1, 1):
        shard(k, (sx * 1.75, 0.95, -0.5), (-sx * 0.045, 0.0, 1.0), 5.2, 0.2, n=4, tipf=0.16, col0=mulc(OBS, 0.8),
              col1=OBS, mat='M_obsidian', seed=sx + 2, slant=0.0, tip_off=0.2, rtop=0.6, phase=PI / 4)
    k.beam((-1.85, 0.95, 3.98), (1.85, 0.95, 4.06), 0.1, 0.12, IR, PAL['iron'], uv='box')
    for sx, zc_, tilt, sw in ((-1, 2.95, 0.22, 0.5), (1, 2.7, -0.3, -0.35)):
        x = sx * 0.42
        k.tube([(x * 1.2, 0.95, 4.0), (x * 1.1, 0.95, (4.0 + zc_ + 0.5) / 2), (x, 0.95, zc_ + 0.52)], 0.018, n=3, mat=IR,
               col=PAL['iron'], caps=False)
        half_sun(k, (x - sx * 0.1, 0.95, zc_), 0.62, side=sx, rz=sw, ry=tilt)
    k.empty('ANCHOR_boss', (0, -2.6, 0))
    k.walk('step_1', (-2.0, -1.4, -0.3), (2.0, 1.4, 0.2))
    k.walk('step_2', (-1.6, -1.05, 0.0), (1.6, 1.05, 0.4))
    k.col('altar', (-1.1, -0.57, 0), (1.1, 0.57, 1.45))
    k.col('post_l', (-1.95, 0.75, 0), (-1.55, 1.15, 4.6))
    k.col('post_r', (1.55, 0.75, 0), (1.95, 1.15, 4.6))
    k.col('brazier_l', (-2.65, -1.2, 0), (-2.05, -0.6, 1.5))
    k.col('brazier_r', (2.05, -1.2, 0), (2.65, -0.6, 1.5))
    k.person = (1.2, -2.2)


@asset('cult_banner', 'Banner of the Dead Dawn: 5.2 m pole, ragged red cloth with a black split sun, brass broken-sun '
       'finial, stones at the foot', 250, footprint=[1.6, 1.2], bake=PBW, weather=dict(top=0.1, base=0.2))
def cult_banner(k):
    k.cyl((0, 0, -0.4), (0.06, 0.0, 4.75), 0.055, 0.04, n=5, mat='M_bark_pine', col=mulc(PAL['bark'], 0.6),
          caps=(False, True))
    k.beam((-0.62, 0, 4.42), (0.74, 0, 4.42), 0.05, 0.05, WD, PAL['beam_d'])
    rag(k, (-0.5, -0.035, 4.4), (1, 0, 0), (0, -0.04, -1), 1.1, 2.7, nu=3, nv=6, col=CULT_RED, wave=0.03, ragged=0.42,
        seed=9)
    pan = Panel((-0.5, -0.155, 2.6), (0.6, -0.155, 2.6), (0.6, -0.085, 4.3), (-0.5, -0.085, 4.3))
    for (a, b) in (((0.5, 0.82), (0.44, 0.6)), ((0.44, 0.6), (0.54, 0.42)), ((0.54, 0.42), (0.47, 0.2)),
                   ((0.25, 0.72), (0.38, 0.62)), ((0.2, 0.5), (0.36, 0.5)), ((0.75, 0.72), (0.62, 0.62)),
                   ((0.8, 0.5), (0.64, 0.5)), ((0.27, 0.3), (0.38, 0.4)), ((0.73, 0.3), (0.62, 0.4))):
        stroke(k, pan, a, b, w=0.07, off=0.0, col=mulc(PAL['dark'], 0.8), mat=CL)
    half_sun(k, (0.02, 0.0, 4.98), 0.34, side=-1, ry=0.1)
    half_sun(k, (0.14, 0.0, 4.9), 0.34, side=1, ry=-0.45, rays=3)
    for (x, y, r) in ((0.22, 0.1, 0.2), (-0.2, 0.12, 0.17), (0.02, -0.22, 0.16)):
        rock(k, (x, y, 0.04), (r, r * 0.85, r * 0.65), seed=x * 9, nu=5, nv=2)
    k.col('pole', (-0.2, -0.2, 0), (0.25, 0.2, 5.0))
    k.person = (1.1, -0.4)
