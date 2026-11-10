"""VALOMBRE weapons -> assets/models/gear/<id>.glb + previews + manifest entries.

Weapon space (hard contract, see humanoid_rig.py): grip centre (right fist) at the origin, tip toward +Z,
main cutting edge toward +X, flat in the XZ plane. Two-handed: left hand ~0.25 m below the origin.

Run:  blender -b --factory-startup -P tools/blender/gear_weapons.py [-- id id ...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gear_parts import *

OUT = os.path.join(MODELS, 'gear')
WEAPONS = {}


def weapon(wid, length, two=False, off=None, desc='', hand='1h'):
    def deco(fn):
        WEAPONS[wid] = dict(fn=fn, length=length, twoHanded=two, offhandGrip=off, desc=desc)
        return fn
    return deco


def flat_spike(mb, base, tip, hw, hy, mat, col, tipcol=None, mid=None, sharp=18.0):
    """Blade-like spike lying in the XZ plane: diamond base (hw in plane, hy along Y) -> tip."""
    base, tip = Vector(base), Vector(tip)
    ax = (tip - base).normalized()
    side = ax.cross(YA).normalized()
    rings = [[base + side * hw, base + YA * hy, base - side * hw, base - YA * hy]]
    if mid:
        f, k, off = mid
        c = base.lerp(tip, f) + Vector(off)
        rings.append([c + side * hw * k, c + YA * hy * k, c - side * hw * k, c - YA * hy * k])
    mb.loft(rings, col, mat, True, None, tip, sharp, capcol1=tipcol or mul(col, 1.4))


def butt_cap(mb, z, r, mat='M_metal_iron', col=IRON, spike=0.0, sx=1.0, sy=1.0):
    """Iron ferrule at the bottom of a haft (z = bottom of the wood)."""
    prof = [(r * 1.12, z + 0.035, col), (r * 1.2, z + 0.028, mul(col, 1.35)), (r * 1.16, z + 0.004, col)]
    if spike > 0:
        prof = [(0, z - spike, mul(col, 1.5)), (r * 0.55, z - 0.004, col)] + prof[::-1]
    else:
        prof = [(0, z - 0.006, col), (r * 0.8, z - 0.004, mul(col, 1.2))] + prof[::-1]
    mb.lathe(prof, 6, mat, None, sx=sx, sy=sy, sharp=40.0, cap1=None)


# =============================================================================== one-handed swords
@weapon('sword_iron', 0.95, desc='plain militia arming sword, straight guard, wheel pommel')
def sword_iron(mb):
    b = blade(mb, 'M_metal_steel', 0.064, 0.845, 0.0255, 0.0165, 0.0044, 0.0027, kind='lens', nr=5, tip=0.085,
              pal=STEEL_PLAIN, col_fn=lambda p, r, c: grime(p, c, 0.22, 3, 40.0))
    quillons(mb, 'M_metal_iron', 0.057, 0.094, 0.0072, 0.0082, IRON, square=True, end=(0.88, 0.82), n=5)
    grip(mb, -0.052, 0.05, 0.0145, 0.0118, ca=LEATHER, cb=LEATHER_DARK, n=9)
    wheel_pommel(mb, -0.0785, 0.0265, 0.0105, 'M_metal_iron', IRON, segs=8)
    return b


@weapon('sword_rusty', 0.92, desc='notched, pitted arming sword eaten by rust')
def sword_rusty(mb):
    notches = [(0.21, 1, 0.70), (0.385, -1, 0.74), (0.50, 1, 0.82), (0.635, 1, 0.62), (0.70, -1, 0.78)]
    z0, z1, tip = 0.062, 0.82, 0.045
    zb = z1 - tip
    zs = [z0, z0 + (zb - z0) * 0.3, zb]
    for zn, s, k in notches:
        zs += [zn - 0.015, zn, zn + 0.015]
    zs = sorted(zs)
    zs2 = [zs[0]]
    for z in zs[1:]:
        if z - zs2[-1] > 0.006:
            zs2.append(z)
    zs = zs2 + [zb + tip * 0.6]

    def em(z, side):
        for zn, s, k in notches:
            if s == side and abs(z - zn) < 1e-4:
                return k
        return 1.0 - 0.06 * vnoise((z * 40, side, 0), 1.0, 4)

    def cf(p, role, c):
        c = rust(p, c, 0.58, 11, 13.0)
        if role == 'e':
            c = mix(c, IRON_OLD['edge'], 0.4)
        return grime(p, c, 0.3, 2, 60.0)

    b = blade(mb, 'M_metal_iron', z0, z1, 0.0245, 0.0175, 0.0042, 0.003, kind='lens', tip=tip, zs=zs, pal=IRON_OLD,
              edge_mod=em, col_fn=cf, tip_pow=2.6, tip_dx=0.007, xoff=lambda z: 0.006 * ((z - 0.06) / 0.76) ** 2)
    m = mb.mark()
    quillons(mb, 'M_metal_iron', 0.055, 0.086, 0.0072, 0.0082, IRON_DARK, square=True, end=(0.85, 0.8), n=5, asym=-0.008)
    wheel_pommel(mb, -0.076, 0.0235, 0.0095, 'M_metal_iron', IRON_DARK, segs=7)
    mb.recolor(m, lambda p, c: rust(p, c, 0.6, 5, 30.0))
    # bare wooden core, half of the leather wrap is gone
    mb.lathe([(1.0, -0.053), (1.04, -0.02), (1.06, 0.01), (1.0, 0.05)], 6, 'M_wood_planks', None,
             cols=[mul(WOOD_DARK, 0.8), WOOD_DARK, mul(WOOD_DARK, 1.1), mul(WOOD_DARK, 0.8)], sx=0.0125, sy=0.0102,
             uv=WOOD_UV, sharp=60.0)
    wrap(mb, -0.05, 0.004, 0.0142, 0.0118, LEATHER_DARK, mul(LEATHER_DARK, 0.7), n=4, segs=6)
    return b


@weapon('sword_steel', 1.0, desc='fine arming sword, fullered blade, curved guard')
def sword_steel(mb):
    b = blade(mb, 'M_metal_steel', 0.066, 0.892, 0.0268, 0.0152, 0.0046, 0.0025, kind='fuller', nr=6, tip=0.10,
              fuller=(0.066, 0.60, 0.0074, 0.62), pal=STEEL)
    st = mul(STEEL['body'], 0.72)
    quillons(mb, 'M_metal_steel', 0.055, 0.108, 0.0082, 0.0092, st, hi=STEEL['body'], curve=0.032,
             power=2.0, end=(0.78, 0.7), n=7, segs=6)
    mb.cbox((0.036, 0.022, 0.024), 'M_metal_steel', st, tr(0, 0, 0.058), ch=0.005)
    grip(mb, -0.056, 0.047, 0.0142, 0.0116, ca=C('#4a2f25'), cb=C('#2b1c17'), n=9)
    wheel_pommel(mb, -0.082, 0.0265, 0.0095, 'M_metal_steel', st, hi=STEEL['body'], segs=8, boss=0.35)
    return b


@weapon('sword_watcher', 1.02, desc='knightly sword of the Order of the Ember: engraved blade, flared guard, ember stone in the pommel')
def sword_watcher(mb):
    b = blade(mb, 'M_metal_steel', 0.068, 0.905, 0.0278, 0.016, 0.0046, 0.0025, kind='fuller', nr=6, tip=0.105,
              fuller=(0.068, 0.63, 0.0082, 0.62), pal=STEEL_FINE)
    # engraving: a beaded gold inlay running in the fuller (thin prism through the blade, both faces)
    rings, cols = [], []
    for z, k in ((0.10, 1.0), (0.165, 0.42), (0.23, 1.0), (0.295, 0.42), (0.36, 1.0), (0.425, 0.42)):
        w = 0.0056 * k
        rings.append([Vector((w, 0, z)), Vector((0, 0.0031, z)), Vector((-w, 0, z)), Vector((0, -0.0031, z))])
        cols.append(mix(GOLD_DARK, GOLD_HI, k))
    mb.loft(rings, cols, 'M_metal_gold', True, Vector((0, 0, 0.086)), Vector((0, 0, 0.47)), 8.0)
    st = mul(STEEL_FINE['body'], 0.7)
    quillons(mb, 'M_metal_steel', 0.058, 0.112, 0.0072, 0.0078, st, hi=STEEL_FINE['body'], end=(0.9, 0.9),
             flare=(0.5, 2.3), n=7, square=True)
    mb.cbox((0.036, 0.023, 0.024), 'M_metal_gold', GOLD, tr(0, 0, 0.058), ch=0.005)
    grip(mb, -0.056, 0.047, 0.0143, 0.0117, ca=LEATHER_BLACK, cb=C('#6e2a16'), n=9)
    wheel_pommel(mb, -0.086, 0.029, 0.0098, 'M_metal_steel', st, hi=STEEL_FINE['body'], segs=8)
    for s in (1, -1):
        gem(mb, (0, s * 0.0092, -0.086), (0, s, 0), 0.0165, 0.0072, 'M_ember', EMBER, EMBER_HOT, segs=6)
    return b


@weapon('sword_dawn', 1.1, desc='royal sword "Aubeclat": long elegant blade, gold sun-ray guard, crystal shard pommel, crystal vein in the fuller')
def sword_dawn(mb):
    b = blade(mb, 'M_metal_steel', 0.074, 0.975, 0.0245, 0.0125, 0.0043, 0.0023, kind='fuller', nr=6, tip=0.13,
              fuller=(0.074, 0.72, 0.0066, 0.62), pal=STEEL_FINE, tip_pow=1.35)
    # crystal vein: a thin diamond prism through the blade, emerging in the fuller on both faces
    rings, cols = [], []
    for z, k in ((0.125, 1.0), (0.38, 0.9), (0.60, 0.7), (0.685, 0.3)):
        w = 0.0042 * k
        rings.append([Vector((w, 0, z)), Vector((0, 0.0033, z)), Vector((-w, 0, z)), Vector((0, -0.0033, z))])
        cols.append(mix(CRYSTAL, CRYSTAL_HI, k * 0.6))
    mb.loft(rings, cols, 'M_crystal', True, Vector((0, 0, 0.10)), Vector((0, 0, 0.705)), 8.0)
    # sun-ray guard: slender gold quillons, a sun disc on the cross and rays fanning over blade and grip
    quillons(mb, 'M_metal_gold', 0.060, 0.12, 0.0062, 0.007, GOLD, hi=GOLD_HI, curve=0.018, power=2.0,
             end=(0.7, 0.5), n=5, segs=6)
    wheel_pommel(mb, 0.060, 0.026, 0.0102, 'M_metal_gold', GOLD, hi=GOLD_HI, dark=GOLD_DARK, segs=8, boss=0.3)
    for ang, ln, hw in ((90, 0.075, 0.008), (52, 0.048, 0.0065), (128, 0.048, 0.0065), (-48, 0.036, 0.006),
                        (-132, 0.036, 0.006), (24, 0.04, 0.005), (156, 0.04, 0.005), (-90, 0.03, 0.006)):
        d = Vector((math.cos(math.radians(ang)), 0, math.sin(math.radians(ang))))
        c = Vector((0, 0, 0.060))
        flat_spike(mb, c + d * 0.019, c + d * (0.019 + ln), hw, 0.0058, 'M_metal_gold', GOLD, GOLD_HI)
    grip(mb, -0.062, 0.046, 0.0138, 0.0115, ca=LEATHER_PALE, cb=mul(LEATHER_PALE, 0.6), n=9)
    collar(mb, -0.013, -0.003, 0.0152, 'M_metal_gold', GOLD_DARK, GOLD_HI, segs=6, sy=0.85)
    # pommel: gold cup holding a glowing shard
    mb.lathe([(0.0125, -0.060, GOLD_DARK), (0.02, -0.068, GOLD_HI), (0.021, -0.082, GOLD), (0.012, -0.093, GOLD_DARK)],
             6, 'M_metal_gold', None, sy=0.9, sharp=30.0)
    crystal(mb, (0, 0, -0.093), (0, 0, -1), 0.05, 0.0145, 'M_crystal', CRYSTAL, CRYSTAL_HI, segs=5, seed=3, back=0.36)
    return b


@weapon('dagger', 0.38, desc='rondel dagger: disc guard and pommel, stiff diamond blade')
def dagger(mb):
    b = blade(mb, 'M_metal_steel', 0.056, 0.322, 0.0128, 0.0085, 0.0054, 0.0034, kind='diamond', nr=3, tip=0.085,
              pal=STEEL_PLAIN, tip_pow=1.0, sharp=10.0, zs=[0.056, 0.15, 0.237, 0.28])
    disc(mb, 0.0525, 0.0245, 0.0045, 'M_metal_iron', IRON, segs=10)
    mb.lathe([(0.0108, -0.048, mul(WOOD_DARK, 0.8)), (0.0128, -0.024, WOOD_DARK), (0.0122, 0.0, mul(WOOD_DARK, 1.15)),
              (0.0128, 0.024, WOOD_DARK), (0.0108, 0.048, mul(WOOD_DARK, 0.8))], 8, 'M_wood_planks', None,
             sy=0.92, uv=WOOD_UV, sharp=60.0)
    disc(mb, -0.0525, 0.0225, 0.0048, 'M_metal_iron', IRON, segs=10)
    mb.lathe([(0, -0.058, IRON_EDGE), (0.006, -0.0565, IRON), (0.006, -0.054, IRON)], 6, 'M_metal_iron', None)
    return b


@weapon('sword_fang', 0.9, desc='curved blade carved from a giant wolf fang, leather-wrapped grip')
def sword_fang(mb):
    L, z0 = 0.765, 0.052
    ph0, ph1 = math.radians(-15), math.radians(31)
    N = 40

    def cen(s):
        x = z = 0.0
        for i in range(int(N * s + 0.5)):
            ph = ph0 + (ph1 - ph0) * (i + 0.5) / N
            x += -math.sin(ph) * L / N
            z += math.cos(ph) * L / N
        return x, z0 + z, ph0 + (ph1 - ph0) * s

    ss = (0.0, 0.07, 0.18, 0.32, 0.47, 0.62, 0.76, 0.88, 0.96)
    rings, cols = [], []
    for s in ss:
        x, z, ph = cen(s)
        n = Vector((math.cos(ph), 0, math.sin(ph)))
        w = 0.0315 * (1 - s ** 1.7) ** 0.85 * (0.74 + 0.26 * sstep(0.0, 0.12, s))
        t = (0.0145 * (1 - s ** 1.3) + 0.0018) * (0.82 + 0.18 * sstep(0.0, 0.12, s))
        sec = [(1.0, 0.0, 'e'), (0.42, 0.74, 's'), (-0.3, 1.0, 'g'), (-0.95, 0.5, 'b'), (-0.95, -0.5, 'b'),
               (-0.3, -1.0, 'g'), (0.42, -0.74, 's')]
        ring, rc = [], []
        for a, b_, role in sec:
            p = Vector((x, 0, z)) + n * (a * w) + YA * (b_ * t)
            c = {'e': BONE_HI, 's': BONE, 'g': mul(BONE, 0.9), 'b': mix(BONE, BONE_DARK, 0.45)}[role]
            c = mix(c, C('#7d6a48'), 0.75 * sstep(0.2, 0.0, s))             # stained root
            c = mix(c, BONE_HI, 0.5 * sstep(0.7, 1.0, s))                   # bleached tip
            c = mul(c, 0.86 + 0.2 * vnoise(p, 55.0, 7))
            ring.append(p)
            rc.append(c)
        rings.append(ring)
        cols.append(rc)
    xt, zt, _ = cen(1.0)
    mb.loft(rings, cols, 'M_bone', True, 'ngon', Vector((xt, 0, zt)), 24.0, capcol1=BONE_HI)
    # rawhide binding round the root + small bone guard plate
    wrap(mb, 0.046, 0.082, 0.0275, 0.0165, C('#6a5136'), C('#3d2c1e'), n=4, segs=8)
    x1, z1, _ = cen(0.04)
    mb.cbox((0.068, 0.026, 0.012), 'M_bone', mix(BONE, BONE_DARK, 0.5), tr(0.002, 0, 0.047), ch=0.004)
    grip(mb, -0.056, 0.043, 0.0148, 0.0122, ca=C('#4b3526'), cb=C('#291c15'), n=9, swell=1.14)
    # pommel: carved bone knob + two teeth on a thong
    mb.lathe([(0, -0.098, BONE_DARK), (0.012, -0.095, BONE), (0.0185, -0.080, BONE_HI), (0.0165, -0.064, BONE),
              (0.012, -0.056, BONE_DARK)], 7, 'M_bone', None, sy=0.9, sharp=50.0)
    for sx_, ln in ((1, 0.05), (-1, 0.038)):
        a = Vector((sx_ * 0.012, 0.004 * sx_, -0.060))
        b_ = a + Vector((sx_ * 0.016, 0, -0.012))
        c_ = b_ + Vector((sx_ * 0.004, 0, -ln * 0.5))
        mb.tube([a, b_, c_], 0.0022, 3, 'M_leather', LEATHER_DARK, sharp=80.0)
        mb.spike(c_, c_ + Vector((sx_ * 0.004, 0, -0.03)), 0.0055, 'M_bone', BONE, segs=4, tipcol=BONE_HI)
    return (0.085, round(zt, 3))


# =============================================================================== clubs, axes, maces
@weapon('club', 0.75, desc='fire-hardened knotted oak branch')
def club(mb):
    zs = [-0.13, -0.118, -0.095, -0.04, 0.03, 0.12, 0.22, 0.32, 0.42, 0.50, 0.565, 0.605, 0.62]
    rr = [0.012, 0.0215, 0.0175, 0.0165, 0.017, 0.019, 0.0225, 0.028, 0.036, 0.042, 0.043, 0.032, 0.014]

    def px(z):
        return 0.012 * math.sin(z * 7.5 + 0.6) + 0.006 * math.sin(z * 19.0), 0.004 * math.sin(z * 11.0 + 2.0)

    pts = [Vector((px(z)[0], px(z)[1], z)) for z in zs]
    radii = [(r * (1.0 + 0.08 * math.sin(z * 31.0)), r * (1.0 + 0.1 * math.sin(z * 23.0 + 1.0))) for z, r in zip(zs, rr)]
    haft(mb, pts, radii, base=mul(WOOD, 0.92), segs=8, seed=3, char=(0.26, 0.52))
    # knots (burls) and a lopped branch stub
    for z, ang, r in ((0.455, 20, 0.019), (0.36, 200, 0.016), (0.535, 150, 0.018), (0.245, 100, 0.012), (0.56, 290, 0.016)):
        x, y = px(z)
        rad = rr[min(range(len(zs)), key=lambda i: abs(zs[i] - z))]
        d = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
        c = Vector((x, y, z)) + d * (rad * 0.86)
        k = sstep(0.26, 0.52, z)
        col = mix(mul(WOOD_DARK, 0.9), WOOD_CHAR, k * 0.8)
        Mk = tr(c) @ ZA.rotation_difference(d).to_matrix().to_4x4()
        mb.sphere((0, 0, 0), (r * 1.25, r * 1.6, r * 0.75), 'M_wood_planks',
                  lambda p, i, j, c_=c, col=col, d=d: mix(col, mul(col, 0.5), sstep(0.35, 1.0, (p - c_).normalized().dot(d))),
                  segs=7, rings=3, uv=WOOD_UV, M=Mk)
    x, y = px(0.30)
    a = Vector((x + 0.02, y, 0.30))
    b_ = a + Vector((0.034, 0.004, 0.03))
    mb.tube([a, b_], [0.0135, 0.011], 6, 'M_wood_planks', [mul(WOOD_DARK, 0.9), mul(WOOD_PALE, 0.9)], uv=WOOD_UV, cap0=None)
    wrap(mb, -0.062, 0.058, 0.0195, 0.0195, LEATHER, LEATHER_DARK, n=7, segs=8, xc=px(0.0)[0])
    return (0.2, 0.62)


@weapon('hatchet', 0.6, desc='small bearded hand axe')
def hatchet(mb):
    zs = [-0.14, -0.132, -0.11, -0.04, 0.08, 0.22, 0.36, 0.455]
    xs = [-0.012 * sstep(-0.02, -0.14, z) for z in zs]
    rr = [(0.0105, 0.016), (0.0145, 0.0215), (0.013, 0.018), (0.0122, 0.0158), (0.0122, 0.0155), (0.012, 0.0152),
          (0.0118, 0.015), (0.0115, 0.0148)]
    haft(mb, [Vector((x, 0, z)) for x, z in zip(xs, zs)], rr, base=WOOD, segs=8, seed=1, grips=[(-0.06, 0.06)])
    hd = lambda s, v: rust(Vector((s * 0.1, v * 0.1, 0.3)), mix(mul(IRON, 0.8), IRON_EDGE, sstep(0.80, 1.0, s)), 0.25 * (1 - s), 2, 40.0)
    eye_socket(mb, 0.372, 0.442, 0.0215, 0.0172, 'M_metal_iron', mul(IRON, 0.8))
    axe_blade(mb, 'M_metal_iron', 0.016, 0.112, lambda s: 0.441 + 0.012 * s, lambda s: 0.374 - 0.082 * sstep(0.18, 0.92, s),
              0.0125, bulge=0.012, nv=5, col=hd)
    mb.cbox((0.016, 0.03, 0.058), 'M_metal_iron', mul(IRON, 0.85), tr(-0.026, 0, 0.407), ch=0.004)
    return (0.29, 0.455)


@weapon('axe_war', 0.8, desc='one-handed broad war axe with a back spike')
def axe_war(mb):
    zs = [-0.12, -0.05, 0.10, 0.30, 0.50, 0.638]
    rr = [(0.013, 0.0165), (0.0125, 0.0158), (0.0122, 0.0152), (0.012, 0.015), (0.012, 0.015), (0.0118, 0.0148)]
    haft(mb, [Vector((0, 0, z)) for z in zs], rr, base=WOOD_DARK, segs=6, seed=5)
    wrap(mb, -0.075, 0.072, 0.0178, 0.0148, LEATHER, LEATHER_DARK, n=6, segs=6)
    butt_cap(mb, -0.12, 0.0155, spike=0.022)
    st = lambda s, v: mix(mul(IRON, 0.95), STEEL['edge'], sstep(0.80, 0.98, s))
    eye_socket(mb, 0.512, 0.612, 0.0205, 0.0172, 'M_metal_steel', mul(IRON, 0.95), segs=6)
    axe_blade(mb, 'M_metal_steel', 0.016, 0.138, lambda s: 0.598 + 0.057 * s ** 1.4, lambda s: 0.526 - 0.102 * s ** 1.15,
              0.0112, bulge=0.03, nv=6, col=st)
    flat_spike(mb, (-0.017, 0, 0.562), (-0.098, 0, 0.55), 0.019, 0.0095, 'M_metal_steel', mul(IRON, 0.95), STEEL['edge'],
               mid=(0.35, 0.6, (0, 0, 0.002)))
    langets(mb, 0.41, 0.512, 0.012, 'M_metal_steel', mul(IRON, 0.9), rivets=2)
    mb.lathe([(0.0125, 0.612, IRON), (0.009, 0.632, IRON_EDGE), (0, 0.655, STEEL['edge'])], 4, 'M_metal_steel', None, sharp=30.0)
    return (0.42, 0.655)


@weapon('mace', 0.7, desc='flanged mace, iron shaft, leather grip')
def mace(mb):
    disc(mb, -0.106, 0.021, 0.0075, 'M_metal_iron', IRON, segs=8)
    mb.lathe([(0, -0.118, IRON_EDGE), (0.008, -0.114, IRON)], 6, 'M_metal_iron', None, cap1=None)
    grip(mb, -0.099, 0.074, 0.0142, 0.0142, ca=LEATHER, cb=LEATHER_DARK, n=11, swell=1.08, segs=7)
    disc(mb, 0.082, 0.0235, 0.006, 'M_metal_iron', IRON, segs=8)
    mb.lathe([(0.0105, 0.086, mul(IRON, 0.8)), (0.0105, 0.25, IRON), (0.0115, 0.43, mul(IRON, 0.85))], 6, 'M_metal_iron',
             None, sharp=30.0)
    mb.lathe([(0.0135, 0.25, IRON), (0.016, 0.257, IRON_EDGE), (0.0135, 0.264, IRON)], 6, 'M_metal_iron', None, sharp=30.0)
    # head: core + 7 flanges
    mb.lathe([(0.015, 0.425, IRON), (0.021, 0.438, IRON_EDGE), (0.0185, 0.452, IRON), (0.0185, 0.555, IRON),
              (0.021, 0.568, IRON_EDGE), (0.012, 0.578, IRON), (0, 0.585, IRON_EDGE)], 7, 'M_metal_steel', None, sharp=40.0)
    fc = lambda s, v: mix(mul(IRON, 1.05), STEEL['edge'], sstep(0.5, 1.0, s))
    for k in range(7):
        m = mb.mark()
        axe_blade(mb, 'M_metal_steel', 0.014, 0.056, lambda s: 0.566 - 0.062 * s ** 0.85, lambda s: 0.44 + 0.058 * s ** 1.25,
                  0.0052, bulge=0.0, ss=(0.0, 0.55, 1.0), nv=2, col=fc, edge_at=0.55, horn_thin=0.0, cap=False)
        mb.xform(m, rot('Z', 360.0 * k / 7 + 12))
    return (0.43, 0.585)


@weapon('morningstar', 0.78, desc='spiked iron ball on an iron-bound haft')
def morningstar(mb):
    zs = [-0.118, -0.05, 0.12, 0.32, 0.505]
    rr = [0.0155, 0.015, 0.015, 0.016, 0.0175]
    haft(mb, [Vector((0, 0, z)) for z in zs], rr, base=WOOD_DARK, segs=6, seed=8)
    wrap(mb, -0.072, 0.07, 0.0172, 0.0172, LEATHER_DARK, mul(LEATHER_DARK, 0.65), n=6, segs=6)
    butt_cap(mb, -0.118, 0.0155, spike=0.022)
    for z in (0.17, 0.31):
        collar(mb, z, z + 0.022, 0.0172, 'M_metal_iron', IRON, IRON_EDGE, segs=6, lip=1.1)
    langets(mb, 0.335, 0.5, 0.0165, 'M_metal_iron', IRON, rivets=3)
    mb.lathe([(0.0185, 0.492, IRON), (0.022, 0.502, IRON_EDGE), (0.02, 0.515, IRON)], 6, 'M_metal_iron', None, sharp=40.0)
    cen, R = Vector((0, 0, 0.558)), 0.05
    mb.sphere(cen, R, 'M_metal_iron', lambda p, i, j: rust(p, mul(IRON, 0.9 + 0.3 * (p.z - 0.508) / 0.1), 0.25, 3, 30.0),
              segs=8, rings=5)
    dirs = [(0, 90)] + [(a * 60 + 30, 0) for a in range(6)] + [(a * 90, 42) for a in range(4)] + [(a * 90 + 45, -40) for a in range(4)]
    for az, el in dirs:
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        ln = 0.032 if el == 90 else 0.036
        mb.spike(cen + d * (R * 0.9), cen + d * (R + ln), 0.0115, 'M_metal_iron', IRON, segs=4, tipcol=STEEL['edge'],
                 up=(0, 0, 1) if abs(el) < 80 else (1, 0, 0), sharp=30.0)
    return (0.47, 0.64)


# =============================================================================== two-handed
@weapon('axe_woodcutter', 1.25, two=True, off=-0.25, desc='long two-handed felling axe')
def axe_woodcutter(mb):
    zs = [-0.38, -0.372, -0.34, -0.25, -0.05, 0.2, 0.45, 0.68, 0.865]

    def hx(z):
        u = (z + 0.38) / 1.245
        return 0.013 * math.sin(math.pi * u) - 0.004 + 0.016 * sstep(-0.28, -0.38, z)

    rr = [(0.012, 0.02), (0.0165, 0.027), (0.0158, 0.0235), (0.0138, 0.019), (0.0132, 0.018), (0.0132, 0.0182),
          (0.0135, 0.019), (0.0138, 0.02), (0.0138, 0.0205)]
    haft(mb, [Vector((hx(z), 0, z)) for z in zs], rr, base=WOOD_PALE, segs=8, seed=4, grips=[(-0.07, 0.07), (-0.33, -0.18)])
    hd = lambda s, v: rust(Vector((s * 0.2, v * 0.1, 0.8)), mix(mul(IRON, 0.75), IRON_EDGE, sstep(0.78, 1.0, s)), 0.3 * (1 - s), 6, 30.0)
    x0 = hx(0.81)
    m = mb.mark()
    eye_socket(mb, 0.762, 0.857, 0.0275, 0.0205, 'M_metal_iron', mul(IRON, 0.75))
    axe_blade(mb, 'M_metal_iron', 0.02, 0.165, lambda s: 0.856 + 0.014 * s, lambda s: 0.763 - 0.05 * s ** 1.2, 0.0195,
              bulge=0.016, nv=5, col=hd, edge_at=0.8)
    mb.cbox((0.024, 0.036, 0.09), 'M_metal_iron', mul(IRON, 0.8), tr(-0.036, 0, 0.8095), ch=0.005)
    mb.xform(m, tr(x0, 0, 0))
    return (0.71, 0.87)


@weapon('claymore', 1.5, two=True, off=-0.22, desc='two-handed greatsword, long ricasso, down-swept guard')
def claymore(mb):
    z1, tip = 1.165, 0.13
    zb = z1 - tip

    def wfn(z):
        if z < 0.285:
            return 0.0205
        if z < 0.318:
            return 0.0205 + 0.0085 * sstep(0.285, 0.318, z)
        if z <= zb:
            return 0.029 + (0.0175 - 0.029) * (z - 0.318) / (zb - 0.318)
        return 0.0175 * (1 - ((z - zb) / tip) ** 1.5)

    def tfn(z):
        if z < 0.3:
            return 0.0058
        if z <= zb:
            return 0.005 + (0.0027 - 0.005) * (z - 0.3) / (zb - 0.3)
        return 0.0027 * (1 - 0.45 * (z - zb) / tip)

    zs = [0.116, 0.283, 0.32, 0.56, 0.82, zb, zb + tip * 0.45, zb + tip * 0.8]
    b = blade(mb, 'M_metal_steel', 0.116, z1, 0, 0, 0, 0, kind='fuller', tip=tip, zs=zs, wfn=wfn, tfn=tfn,
              fuller=(0.33, 0.84, 0.0078, 0.6), pal=STEEL,
              col_fn=lambda p, r, c: mul(c, 0.74) if p.z < 0.29 else c)
    st = mul(STEEL['body'], 0.7)
    # down-swept quillons with trefoil terminals
    quillons(mb, 'M_metal_steel', 0.104, 0.165, 0.0092, 0.0105, st, hi=STEEL['body'], curve=0.075, power=1.15,
             end=(0.72, 0.66), n=5, segs=6)
    mb.cbox((0.044, 0.025, 0.03), 'M_metal_steel', st, tr(0, 0, 0.106), ch=0.006)
    for sx_ in (1, -1):
        c = Vector((sx_ * 0.172, 0, 0.183))
        for d in ((sx_ * 0.013, 0.014), (sx_ * 0.014, -0.011), (-sx_ * 0.004, 0.02)):
            mb.sphere(c + Vector((d[0], 0, d[1])), (0.0115, 0.0075, 0.0115), 'M_metal_steel', STEEL['body'], segs=4, rings=2)
    for sy_ in (1, -1):                                               # langets down the ricasso
        mb.cbox((0.016, 0.004, 0.06), 'M_metal_steel', st, tr(0, sy_ * 0.0068, 0.148), taper=0.5)
    grip(mb, -0.276, 0.093, 0.0152, 0.0128, ca=C('#4d3324'), cb=C('#2a1c15'), n=8, swell=1.1, segs=6, waist=0.08)
    wheel_pommel(mb, -0.305, 0.030, 0.0115, 'M_metal_steel', st, hi=STEEL['body'], segs=8)
    return (0.30, z1)


@weapon('axe_great', 1.45, two=True, off=-0.25, desc='great double-bladed bearded battle axe')
def axe_great(mb):
    zs = [-0.365, -0.2, 0.0, 0.3, 0.6, 0.82, 1.0]
    rr = [(0.0165, 0.02), (0.0158, 0.019), (0.0155, 0.0185), (0.0155, 0.0185), (0.0155, 0.0188), (0.016, 0.019), (0.016, 0.019)]
    haft(mb, [Vector((0, 0, z)) for z in zs], rr, base=mul(WOOD_DARK, 0.9), segs=6, seed=9)
    wrap(mb, -0.075, 0.08, 0.021, 0.0182, LEATHER, LEATHER_DARK, n=4, segs=6)
    wrap(mb, -0.33, -0.19, 0.0215, 0.0188, LEATHER, LEATHER_DARK, n=4, segs=6)
    butt_cap(mb, -0.365, 0.019, spike=0.035)
    st = lambda s, v: mix(mul(IRON, 0.85), STEEL['edge'], sstep(0.80, 0.98, s))
    eye_socket(mb, 0.80, 0.98, 0.0255, 0.0215, 'M_metal_steel', mul(IRON, 0.85), segs=6)
    for side in (1, -1):
        axe_blade(mb, 'M_metal_steel', 0.02, 0.198, lambda s: 0.962 + 0.086 * s ** 1.35, lambda s: 0.818 - 0.155 * s ** 1.1,
                  0.0125, bulge=0.036, nv=6, side=side, col=st)
    mb.lathe([(0.016, 0.98, IRON), (0.011, 1.0, IRON_EDGE), (0, 1.05, STEEL['edge'])], 4, 'M_metal_steel', None, sharp=30.0)
    langets(mb, 0.62, 0.80, 0.0158, 'M_metal_steel', mul(IRON, 0.85), rivets=2)
    return (0.66, 1.05)


@weapon('hammer_war', 1.35, two=True, off=-0.25, desc='two-handed war hammer, square head and back spike')
def hammer_war(mb):
    zs = [-0.345, -0.2, 0.0, 0.3, 0.6, 0.885]
    rr = [(0.0158, 0.0185), (0.015, 0.0178), (0.0148, 0.0175), (0.0148, 0.0175), (0.015, 0.0178), (0.015, 0.0178)]
    haft(mb, [Vector((0, 0, z)) for z in zs], rr, base=WOOD_DARK, segs=6, seed=12)
    wrap(mb, -0.075, 0.08, 0.0198, 0.0172, LEATHER, LEATHER_DARK, n=4, segs=6)
    wrap(mb, -0.33, -0.19, 0.0205, 0.0178, LEATHER, LEATHER_DARK, n=4, segs=6)
    butt_cap(mb, -0.345, 0.018, spike=0.035)
    ir, hi = mul(IRON, 0.95), STEEL['body']
    zc = 0.855
    m = mb.mark()
    mb.cbox((0.054, 0.046, 0.066), 'M_metal_steel', ir, tr(0, 0, zc), ch=0.006)
    # hammer side (+X): neck then square face with four blunt teeth
    mb.cbox((0.036, 0.036, 0.04), 'M_metal_steel', ir, tr(0.043, 0, zc) @ rot('Y', 90), ch=0.004)
    mb.cbox((0.054, 0.054, 0.032), 'M_metal_steel', mix(ir, hi, 0.4), tr(0.076, 0, zc) @ rot('Y', 90), ch=0.005)
    for dy in (-0.0135, 0.0135):
        for dz in (-0.0135, 0.0135):
            mb.spike((0.091, dy, zc + dz), (0.103, dy, zc + dz), 0.013, 'M_metal_steel', mix(ir, hi, 0.5), segs=4,
                     tipcol=STEEL['edge'], phase=math.pi / 4)
    # back spike (-X): curved beak
    rings = []
    for x, dz, hh, hy in ((-0.024, 0.0, 0.022, 0.013), (-0.06, -0.002, 0.0155, 0.0095), (-0.10, -0.01, 0.009, 0.006)):
        rings.append([Vector((x, hy, zc + dz + hh * 0.2)), Vector((x, 0, zc + dz + hh)), Vector((x, -hy, zc + dz + hh * 0.2)),
                      Vector((x, 0, zc + dz - hh))])
    mb.loft(rings, [ir, mix(ir, hi, 0.4), hi], 'M_metal_steel', True, None, Vector((-0.142, 0, zc - 0.026)), 20.0,
            capcol1=STEEL['edge'])
    mb.lathe([(0.0165, zc + 0.033, ir), (0.012, zc + 0.045, hi), (0, zc + 0.085, STEEL['edge'])], 4, 'M_metal_steel', None, sharp=30.0)
    mb.xform(m, tr(0, 0, zc) @ sc(1.3) @ tr(0, 0, -zc))
    langets(mb, 0.58, 0.81, 0.015, 'M_metal_steel', ir, rivets=3)
    return (0.80, 0.965)


@weapon('greatsword_drowned', 1.75, two=True, off=-0.24, desc='huge corroded greatsword from the drowned crypts: barnacles, verdigris, teal crystal shard in the guard')
def greatsword_drowned(mb):
    pal = dict(edge=C('#77827e'), body=C('#3f4745'), rim=C('#383e3c'), fuller=C('#2a2f2d'), ridge=C('#525b58'))
    notches = [(0.42, 1, 0.76), (0.68, -1, 0.70), (0.88, 1, 0.46), (1.10, -1, 0.78)]
    z0, z1, tip = 0.135, 1.35, 0.075
    zb = z1 - tip
    zs = [z0]
    for zn, s, k in notches:
        d = 0.035 if k < 0.6 else 0.02
        zs += [zn - d, zn, zn + d]
    zs = sorted(zs + [zb]) + [zb + tip * 0.55]

    def em(z, side):
        for zn, s, k in notches:
            if s == side and abs(z - zn) < 1e-4:
                return k
        return 1.0 - 0.08 * vnoise((z * 25, side, 0), 1.0, 9)

    def cf(p, role, c):
        c = rust(p, c, 0.34, 21, 8.0)
        g = fbm(p, 6.0, 33, 2)
        c = mix(c, mix(C('#24493e'), C('#4f8573'), vnoise(p, 30.0, 4)), 0.75 * sstep(0.46, 0.62, g))   # sea slime / verdigris
        if role == 'e':
            c = mix(c, pal['edge'], 0.35)
        return c

    b = blade(mb, 'M_metal_iron', z0, z1, 0.047, 0.038, 0.0068, 0.0045, kind='lens', tip=tip, zs=zs, pal=pal,
              edge_mod=em, col_fn=cf, tip_pow=2.2, tip_dx=-0.018)

    def verdi(p, c):
        g = fbm(p, 26.0, 5, 3)
        return mix(c, mix(VERDIGRIS, VERDIGRIS_PALE, vnoise(p, 60.0, 8)), sstep(0.40, 0.58, g) * 0.9)

    m = mb.mark()
    quillons(mb, 'M_metal_bronze', 0.118, 0.165, 0.0105, 0.0125, BRONZE_DARK, hi=BRONZE, end=(0.82, 0.8), n=5,
             square=True, curve=-0.012, power=2.0)
    mb.cbox((0.06, 0.03, 0.038), 'M_metal_bronze', BRONZE_DARK, tr(0, 0, 0.118), ch=0.007)
    pear_pommel(mb, -0.338, -0.40, 0.029, 'M_metal_bronze', BRONZE_DARK, BRONZE, segs=6, sy=0.85)
    mb.recolor(m, verdi)
    grip(mb, -0.34, 0.10, 0.0158, 0.0135, ca=C('#3a3128'), cb=C('#1f1d1a'), n=7, swell=1.06, segs=6, waist=0.06,
         col_fn=lambda p, c: mix(c, C('#2f4a3e'), 0.4 * vnoise(p, 20.0, 2)))
    # teal Astre shard grown through the guard, a splinter creeping up the blade
    crystal(mb, (0.0, 0, 0.12), (0, 1, 0), 0.092, 0.021, 'M_crystal', CRYSTAL_TEAL, CRYSTAL_HI, segs=5, seed=5, back=0.5)
    crystal(mb, (0.014, 0.004, 0.16), (0.3, 0.3, 1), 0.14, 0.013, 'M_crystal', CRYSTAL_TEAL, CRYSTAL_HI, segs=4, seed=7, back=0.3)
    crystal(mb, (-0.016, -0.004, 0.15), (-0.4, -0.3, 1), 0.085, 0.011, 'M_crystal', CRYSTAL_TEAL, CRYSTAL_HI, segs=4, seed=9, back=0.3)
    # barnacles
    rnd = random.Random(4)
    bc, bd = C('#bdb9a6'), C('#262a26')
    spots = [(0.014, 1, 0.285), (-0.014, 1, 0.31), (0.02, 1, 0.345), (-0.022, -1, 0.53), (0.006, -1, 0.56),
             (0.02, -1, 0.60), (-0.01, 1, 0.97), (-0.105, 1, 0.118)]
    for x, sy_, z in spots:
        r = rnd.uniform(0.011, 0.016)
        h = r * rnd.uniform(0.6, 0.9)
        y0 = sy_ * (0.004 if abs(x) < 0.03 else 0.01)
        M = tr(x, y0, z) @ rot('X', -90 * sy_) @ rot('Z', rnd.uniform(0, 60))
        mb.lathe([(r, 0.0, mul(bc, 0.7)), (r * 0.5, h, bc)], 4, 'M_bone', M, sharp=30.0, cap1='fan')
        mb.C[-1] = bd
    return b


@weapon('hammer_colossus', 1.5, two=True, off=-0.26, desc='great hammer of the Colossus: a jagged block of ice bound in iron')
def hammer_colossus(mb):
    zs = [-0.365, -0.2, 0.0, 0.3, 0.6, 0.80]
    rr = [(0.019, 0.021), (0.0182, 0.02), (0.018, 0.0198), (0.018, 0.02), (0.0185, 0.0205), (0.019, 0.021)]
    haft(mb, [Vector((0, 0, z)) for z in zs], rr, base=mul(WOOD_DARK, 0.8), segs=6, seed=14)
    wrap(mb, -0.33, -0.185, 0.0235, 0.0215, LEATHER_DARK, mul(LEATHER_DARK, 0.6), n=3, segs=6)
    wrap(mb, -0.075, 0.08, 0.0232, 0.0212, LEATHER_DARK, mul(LEATHER_DARK, 0.6), n=3, segs=6)
    butt_cap(mb, -0.365, 0.0215, spike=0.035)
    # ice block: rough-hewn glacier chunk lying along X (both ends strike), faceted
    rnd = random.Random(23)
    cen = Vector((0.0, 0.0, 0.93))
    pts = []
    for x, ry, rz, n in ((-0.19, 0.045, 0.06, 4), (-0.15, 0.10, 0.125, 5), (-0.05, 0.118, 0.148, 6), (0.06, 0.112, 0.14, 5),
                         (0.15, 0.098, 0.12, 5), (0.195, 0.05, 0.055, 4)):
        ph = rnd.uniform(0, 1.0)
        for k in range(n):
            a = ph + 2 * math.pi * k / n + rnd.uniform(-0.25, 0.25)
            j = rnd.uniform(0.78, 1.08)
            pts.append(cen + Vector((x + rnd.uniform(-0.03, 0.03), ry * j * math.cos(a), rz * j * math.sin(a) + 0.01 * math.sin(x * 20))))

    def icecol(p, i, j):
        k = (p.z - (cen.z - 0.15)) / 0.30
        c = mix(ICE_DEEP, ICE, clamp01(0.15 + k * 0.9 + 0.5 * (vnoise(p, 16.0, 5) - 0.5)))
        c = mix(c, ICE_HI, 0.75 * sstep(0.45, 0.8, vnoise(p, 23.0, 3)))
        return c

    f0 = mb.hull(pts, icecol, 'M_ice', sharp=4.0)
    f1 = len(mb.F)

    def section(xp):
        """Convex cross-section of the hull by the plane x = xp, sorted around the centre."""
        out = {}
        for f in mb.F[f0:f1]:
            for a, b_ in zip(f, f[1:] + f[:1]):
                pa, pb = mb.P[a], mb.P[b_]
                da, db = pa.x - xp, pb.x - xp
                if (da > 0) != (db > 0) and abs(da - db) > 1e-9:
                    p = pa.lerp(pb, da / (da - db))
                    out[(round(p.y, 4), round(p.z, 4))] = p
        ps = list(out.values())
        c = sum(ps, Vector()) / len(ps)
        ps.sort(key=lambda p: math.atan2(p.z - c.z, p.y - c.y))
        return [c + (p - c) * (1.0 + 0.006 / max((p - c).length, 1e-4)) for p in ps]

    # jagged shards
    for base, ax, ln, r, seed in (((0.07, 0.03, 1.02), (0.3, 0.15, 1), 0.115, 0.05, 1), ((-0.10, -0.04, 1.01), (-0.45, -0.2, 1), 0.10, 0.045, 2),
                                  ((0.175, -0.03, 0.87), (1, -0.15, -0.5), 0.12, 0.045, 3), ((-0.17, 0.04, 0.97), (-1, 0.25, 0.3), 0.11, 0.05, 4)):
        crystal(mb, base, ax, ln, r, 'M_ice', mix(ICE, ICE_DEEP, 0.3), ICE_HI, segs=5, seed=seed, back=0.3)
    # iron bands shrink-wrapped round the girth + straps from the socket
    ic = lambda p, i, j: rust(p, IRON, 0.3, 4, 30.0)
    for xp in (-0.085, 0.085):
        path = section(xp)
        mb.tube(path, [(0.02, 0.0062)] * len(path), 4, 'M_metal_iron', ic, up=(1, 0, 0), phase=math.pi / 4,
                closed_path=True, sharp=25.0)
    mb.lathe([(0.0215, 0.745, IRON), (0.031, 0.76, IRON_EDGE), (0.036, 0.80, IRON), (0.03, 0.815, IRON)], 6, 'M_metal_iron',
             None, sharp=40.0)
    for xp in (-0.085, 0.085):                                         # bars under the block joining socket and bands
        mb.cbox((0.11, 0.016, 0.01), 'M_metal_iron', IRON, tr(xp * 0.55, 0, 0.792) @ rot('Y', -18 if xp > 0 else 18))
    return (0.77, 1.10)


# =============================================================================== build / export / preview
ORDER = ['club', 'sword_rusty', 'sword_iron', 'sword_steel', 'sword_watcher', 'dagger', 'hatchet', 'axe_war', 'mace',
         'morningstar', 'axe_woodcutter', 'claymore', 'axe_great', 'hammer_war', 'sword_fang', 'greatsword_drowned',
         'hammer_colossus', 'sword_dawn']


def build_weapon(wid):
    spec = WEAPONS[wid]
    mb = MB()
    br = spec['fn'](mb)
    ob = mb.build(wid, all_preview_mats())
    return ob, br


def _solo(ob):
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = o is not ob


def sheet(path, objs, front=(208, 512), side=(96, 512)):
    """Front (blade flat) + side (edge on) tiles per weapon."""
    tiles = []
    for ob in objs:
        _solo(ob)
        mn, mx = mesh_bounds([ob])
        pair = []
        for view, res in (('front', front), ('left', side)):
            cam = setup_preview(res)
            frame_camera(cam, mn, mx, view, 1.04)
            pair.append(render_to_array()[:, :, :3])
        tiles.append(np.concatenate(pair, axis=1))
    cols = len(tiles) if len(tiles) <= 9 else int(math.ceil(len(tiles) / 2))
    save_png(path, montage(tiles, cols=cols))
    print('PREVIEW', path)


def detail(path, objs, res=352):
    """Per weapon: full front, hilt zoom (front + 3/4), business-end zoom (front + 3/4)."""
    tiles = []
    for ob in objs:
        _solo(ob)
        mn, mx = mesh_bounds([ob])
        L = mx.z - mn.z
        cam = setup_preview(res)
        hz = min(0.34, max(0.2, L * 0.3))
        hilt = (Vector((-0.13, mn.y, mn.z)), Vector((0.13, mx.y, max(mn.z + hz, 0.26 if mn.z < -0.2 else -9))))
        tz = min(0.42, max(0.2, L * 0.34))
        top = (Vector((mn.x, mn.y, mx.z - tz)), Vector((mx.x, mx.y, mx.z)))
        for (a, b), view in (((mn, mx), 'front'), (hilt, 'front'), (hilt, (-0.6, 0.7, -0.25)), (hilt, (-1, 0.05, 0.0)),
                             (top, 'front'), (top, (-0.6, 0.7, -0.3))):
            frame_camera(cam, a, b, view, 1.02)
            tiles.append(render_to_array()[:, :, :3])
    save_png(path, montage(tiles, cols=6))
    print('PREVIEW', path)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    flags = [a for a in argv if a.startswith('-')]
    ids = [a for a in argv if not a.startswith('-')] or ORDER
    reset_scene()
    os.makedirs(OUT, exist_ok=True)
    objs, entries = [], {}
    for wid in ids:
        spec = WEAPONS[wid]
        ob, br = build_weapon(wid)
        objs.append(ob)
        info = export_glb(os.path.join(OUT, wid + '.glb'), [ob])
        mn, mx = bounds_of(ob)
        length = round(mx[2] - mn[2], 3)
        prim = info['meshes'][0]['prims']
        ok = all('COLOR_0' in p['attrs'] for p in prim)
        entries[wid] = dict(file=wid + '.glb', description=spec['desc'], length=length,
                            triangles=info['summary']['tris'], materials=info['summary']['materials'],
                            blade=[br[0], br[1]], twoHanded=spec['twoHanded'], offhandGrip=spec['offhandGrip'],
                            size=[round(mx[i] - mn[i], 3) for i in range(3)], bboxMin=mn, bboxMax=mx)
        print('WEAPON %-20s len %.3f (target %.2f) tris %d %s color0=%s x[%.3f %.3f] y[%.3f %.3f] z[%.3f %.3f]' % (
            wid, length, spec['length'], info['summary']['tris'], 'OVER' if info['summary']['tris'] > 600 else 'ok', ok,
            mn[0], mx[0], mn[1], mx[1], mn[2], mx[2]))
    if len(ids) == len(ORDER):
        with open(os.path.join(OUT, '_weapons.json'), 'w') as f:
            json.dump(entries, f, indent=1)
    if '--nopreview' in flags:
        return
    if '--detail' in flags or len(ids) != len(ORDER):
        for k in range(0, len(objs), 3):
            detail(os.path.join(PREVIEWS, 'gear_wip%d.png' % (k // 3 + 1)), objs[k:k + 3])
    else:
        for k in range(3):
            sheet(os.path.join(PREVIEWS, 'gear_weapons_%d.png' % (k + 1)), objs[k * 6:(k + 1) * 6])
        sheet(os.path.join(PREVIEWS, 'gear_weapons.png'), objs, front=(160, 400), side=(72, 400))


if __name__ == '__main__':
    main()
