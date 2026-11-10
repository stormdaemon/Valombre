"""VALOMBRE shields -> assets/models/gear/shield_*.glb + previews + manifest entries.

Shield space (hard contract, see humanoid_rig.py `shield_L`): upright, facing -Y, the BACK of the shield at
the origin (the forearm lies across the back along X: elbow toward +X, fist at x = -0.175, y = +0.075).

Run:  blender -b --factory-startup -P tools/blender/gear_shields.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gear_parts import *

OUT = os.path.join(MODELS, 'gear')
HAND_X, HAND_Y = -0.175, 0.075          # weapon_L socket seen from shield_L (rig T-pose)
ARM_Y = 0.045                           # forearm axis below the socket


class Shape:
    """Shield outline + curvature. zt(x) / zb(x): top and bottom outline; the board is bent round the
    vertical axis (concave toward the bearer): y_back(x) = curv * (x / W)^2 + keel * |x| / W - y_off.
    y_off puts the back surface on the origin plane at |x| = xref (where elbow and wrist touch it): the
    straight forearm bridges the hollow, so the centre of a bent shield sits a little in FRONT of the origin."""

    def __init__(self, W, zt, zb, curv=0.0, thick=0.014, keel=0.0, clip=1.0, xref=0.15):
        self.W, self.zt, self.zb, self.curv, self.thick, self.keel, self.clip = W, zt, zb, curv, thick, keel, clip
        self.y_off = curv * (xref / W) ** 2 + keel * xref / W

    def yb(self, x):
        return self.curv * (x / self.W) ** 2 + self.keel * abs(x) / self.W - self.y_off

    def yf(self, x):
        return self.yb(x) - self.thick

    def front(self, x, z, lift=0.0):
        return Vector((x, self.yf(x) - lift, z))

    def back(self, x, z, lift=0.0):
        return Vector((x, self.yb(x) + lift, z))


def heater(W, z_top, z_s, z_point, corner=0.012):
    R = ((z_s - z_point) ** 2 + W * W) / (2 * W)

    def zb(x):
        return z_s - math.sqrt(max(0.0, R * R - (abs(x) - (W - R)) ** 2))

    def zt(x):
        return z_top - corner * (abs(x) / W) ** 8

    def outline(nt=5, nb=5):
        pts = [(-W + 2 * W * i / (nt - 1), None) for i in range(nt)]
        pts = [(x, zt(x)) for x, _ in pts]
        for i in range(nb):
            x = W * (1 - i / nb)
            pts.append((x, zb(x)))
        pts.append((0.0, z_point))
        for i in range(1, nb + 1):
            x = -W * i / nb
            pts.append((x, zb(x)))
        return pts

    return zt, zb, outline


def kite(W, z_s, rise, z_point):
    R = ((z_s - z_point) ** 2 + W * W) / (2 * W)

    def zb(x):
        return z_s - math.sqrt(max(0.0, R * R - (abs(x) - (W - R)) ** 2))

    def zt(x):
        return z_s + rise * math.sqrt(max(0.0, 1 - (x / W) ** 2))

    def outline(nt=9, nb=6):
        pts = []
        for i in range(nt):
            a = math.pi * i / (nt - 1)
            x = -W * math.cos(a)
            pts.append((x, zt(x)))
        for i in range(1, nb):
            x = W * (1 - i / nb)
            pts.append((x, zb(x)))
        pts.append((0.0, z_point))
        for i in range(1, nb):
            x = -W * i / nb
            pts.append((x, zb(x)))
        return pts

    return zt, zb, outline


def planks(mb, sh, pw, rows, base, seed, paint=None, x_off=0.0, e=0.007, dirt=None, back=False, mat='M_wood_planks'):
    """Vertical boards. Each board is its own little grid (own tone, dark seams along its edges).
    paint(x, z) -> (color, amount) | None. rows: list of v in 0..1 (bottom -> top)."""
    rnd = random.Random(seed)
    Wc = sh.W * sh.clip
    tile = 8.0 * pw
    k0 = math.floor((-Wc - x_off) / pw)
    x = x_off + k0 * pw
    bounds = []
    while x < Wc - 1e-6:
        a, b_ = max(x, -Wc), min(x + pw, Wc)
        if b_ - a > 0.012:
            bounds.append((a, b_))
        x += pw
    mb.keep = True
    for (a, b_) in bounds:
        tone = rnd.uniform(0.8, 1.12)
        hue = rnd.uniform(-0.04, 0.04)
        if back:
            cx, dk = [a, b_], [0.62, 0.62]
        else:
            cx, dk = [a, a + e, b_ - e, b_], [0.42, 1.0, 1.0, 0.42]
        G = []
        for i, xx in enumerate(cx):
            col = []
            for v in rows:
                z = sh.zb(xx) + (sh.zt(xx) - sh.zb(xx)) * v
                p = sh.back(xx, z) if back else sh.front(xx, z)
                c = mul((base[0] * (1 + hue), base[1], base[2] * (1 - hue)), tone * (0.85 + 0.3 * vnoise(p, 9.0, seed)))
                if paint and not back:
                    pc = paint(xx, z)
                    if pc is not None:
                        c = mix(c, pc[0], pc[1])
                if dirt:
                    c = dirt(p, c)
                c = mul(c, dk[i] if not back else 0.6)
                col.append(mb.add(p, c))
            G.append(col)
        for i in range(len(cx) - 1):
            for j in range(len(rows) - 1):
                q = (G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1])
                uv = tuple(((mb.P[k].x - x_off) / tile, mb.P[k].z / tile) for k in q)
                if back:
                    q, uv = q[::-1], uv[::-1]
                mb.face(q, mat, uv, 30.0)
    mb.keep = False


def sheet_face(mb, sh, xs, rows, col_fn, mat, back=False, sharp=30.0):
    """One smooth curved plate (metal facing or plain back)."""
    mb.keep = True
    G = []
    for xx in xs:
        colm = []
        for v in rows:
            z = sh.zb(xx) + (sh.zt(xx) - sh.zb(xx)) * v
            p = sh.back(xx, z) if back else sh.front(xx, z)
            colm.append(mb.add(p, col_fn(p)))
        G.append(colm)
    for i in range(len(xs) - 1):
        for j in range(len(rows) - 1):
            q = (G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1])
            uv = tuple((mb.P[k].x * 2.0, mb.P[k].z * 2.0) for k in q)
            if back:
                q, uv = q[::-1], uv[::-1]
            mb.face(q, mat, uv, sharp)
    mb.keep = False


def rim(mb, sh, outline, mat, col_fn, half_w=0.011, extra=0.004, segs=4):
    """Edge binding: a band wrapped round the outline (covers the board's edge, front and back)."""
    path = [Vector((x, (sh.yf(x) + sh.yb(x)) * 0.5, z)) for x, z in outline]
    ra, rb = sh.thick * 0.5 + extra, half_w
    k = 1.4142 if segs == 4 else 1.0
    mb.tube(path, [(ra * k, rb * k)] * len(path), segs, mat, col_fn, up=(0, 1, 0), phase=(math.pi / 4 if segs == 4 else 0.0),
            closed_path=True, sharp=30.0)


def boss(mb, sh, x, z, r, h, mat, col, hi, segs=8):
    M = tr(x, sh.yf(x), z) @ rot('X', 90)
    prof = [(r * 1.5, 0.0, mul(col, 0.8)), (r * 1.42, 0.005, hi), (r * 1.08, 0.007, col), (r, h * 0.42, col),
            (r * 0.62, h * 0.86, hi), (0, h, hi)]
    mb.lathe(prof, segs, mat, M, sharp=38.0)


def stud(mb, sh, x, z, r, mat, col, back=False):
    if back:
        p = sh.back(x, z)
        rivet(mb, p, (0, 1, 0), r, mat, col)
    else:
        p = sh.front(x, z)
        rivet(mb, p, (0, -1, 0), r, mat, col)


def straps(mb, sh, arm_x=0.05, two=False):
    """Enarmes: a broad forearm strap near the elbow side, a rolled hand grip at the fist, a leather pad."""
    lc, ld = LEATHER, LEATHER_DARK
    for ax in ([arm_x] if not two else [arm_x, arm_x + 0.085]):
        y0 = sh.yb(ax)
        path = [Vector((ax, y0 - 0.002, -0.062)), Vector((ax, y0 + 0.05, -0.058)), Vector((ax, ARM_Y + 0.05, -0.026)),
                Vector((ax, ARM_Y + 0.05, 0.026)), Vector((ax, y0 + 0.05, 0.058)), Vector((ax, y0 - 0.002, 0.062))]
        mb.tube(path, [(0.019 * 1.4142, 0.003 * 1.4142)] * len(path), 4, 'M_leather', [ld, lc, mul(lc, 1.15), mul(lc, 1.15), lc, ld],
                up=(1, 0, 0), phase=math.pi / 4, sharp=30.0)
        for zz in (-0.062, 0.062):
            rivet(mb, Vector((ax, y0 + 0.003, zz * 1.02)), (0, 1, 0), 0.0055, 'M_metal_iron', IRON_EDGE)
    yh = sh.yb(HAND_X)
    path = [Vector((HAND_X, yh - 0.002, -0.068)), Vector((HAND_X, HAND_Y - 0.012, -0.05)), Vector((HAND_X, HAND_Y, -0.02)),
            Vector((HAND_X, HAND_Y, 0.02)), Vector((HAND_X, HAND_Y - 0.012, 0.05)), Vector((HAND_X, yh - 0.002, 0.068))]
    mb.tube(path, [0.008, 0.0095, 0.0115, 0.0115, 0.0095, 0.008], 5, 'M_leather', [ld, lc, mul(lc, 0.8), mul(lc, 0.8), lc, ld],
            up=(1, 0, 0), sharp=60.0)
    for zz in (-0.068, 0.068):
        rivet(mb, Vector((HAND_X, yh + 0.003, zz * 1.04)), (0, 1, 0), 0.0055, 'M_metal_iron', IRON_EDGE)
    # forearm pad
    xa, xb = HAND_X + 0.05, arm_x + 0.05
    pts = [sh.back(xa, -0.05, 0.004), sh.back((xa + xb) / 2, -0.055, 0.005), sh.back(xb, -0.05, 0.004),
           sh.back(xb, 0.05, 0.004), sh.back((xa + xb) / 2, 0.055, 0.005), sh.back(xa, 0.05, 0.004)]
    mb.keep = True
    idx = [mb.add(p, mul(LEATHER_LIGHT, 0.75 + 0.2 * vnoise(p, 40.0, 3))) for p in pts]
    mb.face(idx[::-1], 'M_leather', None, 30.0)
    mb.keep = False


def dirt_fn(zlow, zhigh, amount=0.35, seed=1):
    def f(p, c):
        k = 1.0 - amount * sstep(zhigh, zlow, p.z) * (0.6 + 0.4 * vnoise(p, 12.0, seed))
        return mul(c, k * (0.9 + 0.15 * vnoise(p, 30.0, seed + 3)))
    return f


SHIELDS = {}


def shield(sid, desc):
    def deco(fn):
        SHIELDS[sid] = dict(fn=fn, desc=desc)
        return fn
    return deco


# ----------------------------------------------------------------------------- the four shields
@shield('shield_wood', 'round planked targe, iron boss, rawhide rim (0.62 m)')
def shield_wood(mb):
    R = 0.31
    zt = lambda x: 0.0 + math.sqrt(max(0.0, R * R - x * x))
    zb = lambda x: 0.0 - math.sqrt(max(0.0, R * R - x * x))
    sh = Shape(R, zt, zb, curv=0.0, thick=0.016, clip=0.975)
    dirt = dirt_fn(-0.31, 0.1, 0.3, 4)
    planks(mb, sh, 0.105, [0.0, 0.25, 0.5, 0.75, 1.0], mul(WOOD, 0.95), 7, x_off=-0.0525, dirt=dirt)
    planks(mb, sh, 0.105, [0.0, 0.5, 1.0], mul(WOOD_DARK, 0.95), 7, x_off=-0.0525, back=True)
    outline = [(R * math.cos(2 * math.pi * k / 20), R * math.sin(2 * math.pi * k / 20)) for k in range(20)]
    rim(mb, sh, outline, 'M_leather', lambda p, i, j: mul(mix(LEATHER, LEATHER_LIGHT, vnoise(p, 14.0, 2)), 0.8 + 0.3 * vnoise(p, 40.0, 5)),
        half_w=0.013, extra=0.0035)
    boss(mb, sh, 0, 0, 0.062, 0.05, 'M_metal_iron', IRON, IRON_EDGE, segs=9)
    m = mb.mark()
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        stud(mb, sh, 0.079 * math.cos(a), 0.079 * math.sin(a), 0.0065, 'M_metal_iron', IRON_EDGE)
    for k in range(10):
        a = 2 * math.pi * (k + 0.25) / 10
        stud(mb, sh, 0.283 * math.cos(a), 0.283 * math.sin(a), 0.007, 'M_metal_iron', IRON)
    # two wooden battens on the back
    for zz in (0.15, -0.15):
        hw = math.sqrt(R * R - zz * zz) - 0.035
        mb.cbox((hw * 2, 0.012, 0.045), 'M_wood_planks', mul(WOOD_DARK, 0.85), tr(0, sh.yb(0) + 0.006, zz), uv=(0.5, 0.03, 0.0))
    straps(mb, sh)
    return sh, dict(shape='round', diameter=0.62)


@shield('shield_iron', 'heater shield, iron rim and bars, scraped-off heraldry (0.55 x 0.75 m)')
def shield_iron(mb):
    W = 0.275
    zt, zb, outline = heater(W, 0.40, 0.11, -0.35)
    sh = Shape(W, zt, zb, curv=0.055, thick=0.015)
    red, white = C('#6b2a22'), C('#b9ae96')

    def paint(x, z):
        # party per pale, gules and argent: mostly scraped / flaked away
        flake = fbm((x * 1.0, z * 1.0, 0.3), 7.0, 21, 3)
        keep = sstep(0.36, 0.5, flake) * (0.6 + 0.4 * sstep(-0.3, 0.3, z))
        if abs(x) < 0.004:
            return None
        return (red if x < 0 else white, 0.93 * keep)

    dirt = dirt_fn(-0.35, 0.1, 0.35, 6)
    planks(mb, sh, 0.11, [0.0, 0.16, 0.33, 0.5, 0.67, 0.84, 1.0], mul(WOOD, 0.9), 3, paint=paint, x_off=0.0, dirt=dirt)
    planks(mb, sh, 0.11, [0.0, 0.5, 1.0], mul(WOOD_DARK, 0.95), 3, x_off=0.0, back=True)
    irc = lambda p, i, j: rust(p, mul(IRON, 0.9 + 0.4 * vnoise(p, 50.0, 9)), 0.3, 12, 18.0)
    rim(mb, sh, outline(9, 5), 'M_metal_iron', irc, half_w=0.015, extra=0.0045)
    # two iron bars across the face, nailed
    for zz in (0.24, -0.02):
        hw = W - 0.006 if zz > 0.11 else None
        xs = [(-1 + 2 * i / 6) for i in range(7)]
        xr = W - 0.008
        if zz < 0.11:
            # stay inside the outline
            lo, hi_ = 0.0, W
            for _ in range(30):
                mid = (lo + hi_) / 2
                if zb(mid) < zz:
                    lo = mid
                else:
                    hi_ = mid
            xr = lo - 0.006
        path = [sh.front(u * xr, zz, 0.003) for u in xs]
        mb.tube(path, [(0.0032 * 1.4142, 0.0135 * 1.4142)] * len(path), 4, 'M_metal_iron', irc, up=(0, 1, 0), phase=math.pi / 4,
                sharp=30.0)
        for u in (-0.82, -0.42, 0.0, 0.42, 0.82):
            rivet(mb, sh.front(u * xr, zz, 0.0055), (0, -1, 0), 0.0065, 'M_metal_iron', IRON_EDGE)
    straps(mb, sh)
    return sh, dict(shape='heater', width=0.55, height=0.75)


@shield('shield_watcher', 'large steel-faced heater of the Order of the Ember, embossed flame emblem (0.6 x 0.9 m)')
def shield_watcher(mb):
    W = 0.30
    zt, zb, outline = heater(W, 0.42, 0.10, -0.48)
    sh = Shape(W, zt, zb, curv=0.05, thick=0.014, keel=0.018)
    dark, lite = C('#3b4048'), C('#7c838c')

    def face(p):
        # blackened steel plate, burnished toward the keel and the worn rim
        k = sstep(0.75, 0.0, abs(p.x) / W) * 0.45 + 0.25 * vnoise(p, 14.0, 4)
        c = mix(dark, lite, k)
        return mul(c, 1.0 - 0.3 * sstep(0.0, -0.48, p.z) * vnoise(p, 9.0, 2))

    xs = [W * u for u in (-1, -0.72, -0.4, -0.12, 0.0, 0.12, 0.4, 0.72, 1)]
    sheet_face(mb, sh, xs, [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], face, 'M_metal_steel')
    planks(mb, sh, 0.12, [0.0, 0.5, 1.0], mul(WOOD_DARK, 0.9), 5, x_off=0.0, back=True)
    rc = lambda p, i, j: mul(STEEL['body'], 0.8 + 0.35 * vnoise(p, 35.0, 6))
    rim(mb, sh, outline(9, 5), 'M_metal_steel', rc, half_w=0.017, extra=0.005)
    # embossed flame: raised bronze/gold relief following the plate
    fl = [(0.0, -1.0), (0.40, -0.88), (0.68, -0.48), (0.66, 0.0), (0.46, 0.36), (0.60, 0.95), (0.26, 0.52), (0.10, 1.55),
          (-0.14, 0.62), (-0.40, 1.12), (-0.46, 0.38), (-0.70, -0.02), (-0.64, -0.5), (-0.38, -0.88)]
    S, cz = 0.175, 0.0
    mb.keep = True
    for scale, lift, ca, cb, m in ((1.0, 0.0015, GOLD_DARK, GOLD, 'M_metal_gold'), (0.6, 0.0105, GOLD, GOLD_HI, 'M_metal_gold')):
        outer = [sh.front(u * S * scale, cz - 0.03 * (1 - scale) * 2 + v * S * scale, lift) for u, v in fl]
        inner = [sh.front(u * S * scale * 0.7, cz - 0.03 * (1 - scale) * 2 + (v * 0.74 - 0.05) * S * scale, lift + 0.008) for u, v in fl]
        io = [mb.add(p, ca) for p in outer]
        ii = [mb.add(p, cb) for p in inner]
        n = len(fl)
        for k in range(n):
            k2 = (k + 1) % n
            mb.face((io[k2], io[k], ii[k], ii[k2]), m, None, 25.0)
        it = [mb.add(p, cb) for p in inner]
        mb.face(it[::-1], m, None, 25.0)
    mb.keep = False
    for x, z in ((-0.245, 0.37), (0.245, 0.37), (-0.25, 0.12), (0.25, 0.12), (-0.19, -0.16), (0.19, -0.16), (0, -0.40),
                 (0, 0.375), (-0.1, -0.30), (0.1, -0.30)):
        stud(mb, sh, x, z, 0.008, 'M_metal_gold', GOLD)
    straps(mb, sh, two=True)
    return sh, dict(shape='heater', width=0.60, height=0.90)


@shield('shield_kite', 'kite shield, leather-bound planks, faded sun emblem (0.55 x 1.05 m)')
def shield_kite(mb):
    W = 0.275
    zt, zb, outline = kite(W, 0.20, 0.18, -0.67)
    sh = Shape(W, zt, zb, curv=0.075, thick=0.015, clip=0.97)
    blue, ochre = C('#2f4258'), C('#c2a04e')
    sun_c = (0.0, 0.10)

    def paint(x, z):
        flake = fbm((x, z, 0.7), 5.5, 8, 3)
        keep = sstep(0.36, 0.52, flake)
        return (mix(blue, mul(blue, 1.35), vnoise((x, z, 0), 9.0, 3)), 0.88 * keep)

    dirt = dirt_fn(-0.67, 0.0, 0.4, 9)
    planks(mb, sh, 0.11, [0.0, 0.14, 0.3, 0.47, 0.64, 0.82, 1.0], mul(WOOD, 0.9), 12, paint=paint, x_off=0.0, dirt=dirt)
    planks(mb, sh, 0.11, [0.0, 0.5, 1.0], mul(WOOD_DARK, 0.95), 12, x_off=0.0, back=True)
    rim(mb, sh, outline(9, 5), 'M_leather', lambda p, i, j: mul(mix(LEATHER_DARK, LEATHER, vnoise(p, 12.0, 2)), 0.85 + 0.3 * vnoise(p, 40.0, 5)),
        half_w=0.014, extra=0.004)
    # faded sun: painted disc + rays (thin painted relief hugging the boards) round a small iron boss
    mb.keep = True

    def sc_(p, a=1.0):
        f = fbm(p, 16.0, 31, 2)
        return mix(mul(WOOD, 0.8), mix(ochre, mul(ochre, 0.7), vnoise(p, 30.0, 2)), a * (0.45 + 0.55 * sstep(0.3, 0.55, f)))

    nseg, r1, r2 = 12, 0.062, 0.105
    ring1 = [sh.front(sun_c[0] + r1 * math.cos(2 * math.pi * k / nseg), sun_c[1] + r1 * math.sin(2 * math.pi * k / nseg), 0.0032) for k in range(nseg)]
    ring2 = [sh.front(sun_c[0] + r2 * math.cos(2 * math.pi * k / nseg), sun_c[1] + r2 * math.sin(2 * math.pi * k / nseg), 0.0028) for k in range(nseg)]
    i1 = [mb.add(p, sc_(p)) for p in ring1]
    i2 = [mb.add(p, sc_(p)) for p in ring2]
    for k in range(nseg):
        k2 = (k + 1) % nseg
        mb.face((i1[k2], i1[k], i2[k], i2[k2]), 'M_wood_planks', None, 30.0, 1.0 / 0.88)
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        ln = 0.115 if k % 2 == 0 else 0.07
        da = 0.14
        pa = sh.front(sun_c[0] + (r2 + 0.012) * math.cos(a - da), sun_c[1] + (r2 + 0.012) * math.sin(a - da), 0.0028)
        pb = sh.front(sun_c[0] + (r2 + 0.012) * math.cos(a + da), sun_c[1] + (r2 + 0.012) * math.sin(a + da), 0.0028)
        pm = sh.front(sun_c[0] + (r2 + 0.012 + ln * 0.5) * math.cos(a), sun_c[1] + (r2 + 0.012 + ln * 0.5) * math.sin(a), 0.003)
        pt = sh.front(sun_c[0] + (r2 + 0.012 + ln) * math.cos(a), sun_c[1] + (r2 + 0.012 + ln) * math.sin(a), 0.0028)
        ids = [mb.add(p, sc_(p, 0.9)) for p in (pa, pb, pt)]
        mb.face((ids[1], ids[0], ids[2]), 'M_wood_planks', None, 30.0, 1.0 / 0.88)
    mb.keep = False
    boss(mb, sh, sun_c[0], sun_c[1], 0.045, 0.04, 'M_metal_iron', IRON, IRON_EDGE, segs=8)
    for x, z in ((-0.2, 0.26), (0.2, 0.26), (-0.235, 0.05), (0.235, 0.05), (-0.17, -0.2), (0.17, -0.2), (-0.085, -0.44),
                 (0.085, -0.44), (0, 0.345)):
        stud(mb, sh, x, z, 0.0065, 'M_metal_iron', IRON_EDGE)
    straps(mb, sh)
    return sh, dict(shape='kite', width=0.55, height=1.05)


ORDER = ['shield_wood', 'shield_iron', 'shield_watcher', 'shield_kite']


def build_shield(sid):
    mb = MB()
    sh, extra = SHIELDS[sid]['fn'](mb)
    ob = mb.build(sid, all_preview_mats())
    return ob, extra


def main():
    reset_scene()
    os.makedirs(OUT, exist_ok=True)
    objs, entries = [], {}
    for sid in ORDER:
        ob, extra = build_shield(sid)
        objs.append(ob)
        info = export_glb(os.path.join(OUT, sid + '.glb'), [ob])
        mn, mx = bounds_of(ob)
        ok = all('COLOR_0' in p['attrs'] for p in info['meshes'][0]['prims'])
        e = dict(file=sid + '.glb', description=SHIELDS[sid]['desc'], triangles=info['summary']['tris'],
                 materials=info['summary']['materials'], size=[round(mx[i] - mn[i], 3) for i in range(3)],
                 bboxMin=mn, bboxMax=mx, center=[round((mx[i] + mn[i]) * 0.5, 3) for i in range(3)],
                 gripLocal=[HAND_X, HAND_Y, 0.0])
        e.update(extra)
        entries[sid] = e
        print('SHIELD %-16s tris %d %s color0=%s size %s center %s' % (sid, info['summary']['tris'],
              'OVER' if info['summary']['tris'] > 700 else 'ok', ok, e['size'], e['center']))
    with open(os.path.join(OUT, '_shields.json'), 'w') as f:
        json.dump(entries, f, indent=1)
    render_items(os.path.join(PREVIEWS, 'gear_shields.png'), objs,
                 views=('front', 'back', 'left', (-0.55, 0.75, -0.3), (0.5, -0.8, -0.25)), res=400, cols=5, margin=1.05)


if __name__ == '__main__':
    main()
