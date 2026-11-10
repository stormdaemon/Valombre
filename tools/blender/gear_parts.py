"""Weapon / shield part generators (blades, guards, grips, pommels, hafts, axe heads...) built on gear_lib.MB.
Weapon space: grip centre at the origin, tip toward +Z, main cutting edge toward +X, flat in the XZ plane."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gear_lib import *

# ----------------------------------------------------------------------------- palettes (linear)
STEEL = dict(edge=C('#e6e9ec'), body=C('#aab0b7'), rim=C('#8a9098'), fuller=C('#565b63'), ridge=C('#ccd1d6'))
STEEL_PLAIN = dict(edge=C('#cfd2d5'), body=C('#92979d'), rim=C('#7b8086'), fuller=C('#54585e'), ridge=C('#b1b5ba'))
STEEL_FINE = dict(edge=C('#f2f4f6'), body=C('#bcc3ca'), rim=C('#98a0a9'), fuller=C('#5d646e'), ridge=C('#dde1e5'))
IRON_OLD = dict(edge=C('#8d8a84'), body=C('#5f5a54'), rim=C('#4d4843'), fuller=C('#3a3531'), ridge=C('#77726b'))
IRON = C('#55575b')
IRON_DARK = C('#313236')
IRON_EDGE = C('#9da1a6')
RUST_A, RUST_B, RUST_C = C('#5e3722'), C('#7d4a28'), C('#38231a')
LEATHER, LEATHER_DARK, LEATHER_LIGHT = C('#553726'), C('#32221a'), C('#7a5539')
LEATHER_BLACK, LEATHER_RED, LEATHER_PALE = C('#27201d'), C('#5c211b'), C('#c7bca8')
WOOD, WOOD_DARK, WOOD_PALE, WOOD_CHAR = C('#8a6a4b'), C('#5f4836'), C('#a98c68'), C('#2a211c')
GOLD, GOLD_DARK, GOLD_HI = C('#d6a63c'), C('#8a6520'), C('#f3d477')
BRONZE, BRONZE_DARK, VERDIGRIS, VERDIGRIS_PALE = C('#a37440'), C('#5f4326'), C('#3c8a78'), C('#79b8a4')
BONE, BONE_DARK, BONE_HI = C('#d9cdb0'), C('#8c7c5e'), C('#f0e8d4')
EMBER, EMBER_HOT = C('#ff7a1e'), C('#ffc15a')
CRYSTAL, CRYSTAL_TEAL, CRYSTAL_HI = C('#9fe8ff'), C('#35d2c2'), C('#e6fbff')
ICE, ICE_DEEP, ICE_HI = C('#a6d6f4'), C('#5b9fd4'), C('#eef9ff')
ROPE = C('#a08a62')

WOOD_UV = (0.5, 0.03, 0.0)       # true 2 m tile, kept inside one board of the plank texture


def rust(p, col, amount=0.5, seed=0, scale=22.0):
    """Blend rust blotches into a metal color. amount ~ covered fraction (0..1)."""
    n = fbm(p, scale, seed, 3)
    thr = 0.5 + 0.5 * (0.5 - amount)
    k = sstep(thr - 0.07, thr + 0.07, n)
    r = mix(RUST_A, RUST_B, vnoise(p, scale * 2.7, seed + 5))
    r = mix(r, RUST_C, vnoise(p, scale * 1.3, seed + 9) * 0.7)
    return mix(col, r, k * 0.92)


def grime(p, col, amount=0.3, seed=0, scale=30.0):
    n = fbm(p, scale, seed, 2)
    return mul(col, 1.0 - amount * n)


# ----------------------------------------------------------------------------- blade
def blade(mb, mat, z0, z1, w0, w1, t0, t1, kind='fuller', nr=6, tip=0.10, fuller=None, pal=None, zs=None,
          wfn=None, edge_mod=None, xoff=None, col_fn=None, tip_pow=1.6, sharp=13.0, tip_dx=0.0, tfn=None,
          base_dark=0.72):
    """Double-edged blade lofted along +Z with a real cross-section.
    kind: 'fuller' (12 pts: bevels + hollow), 'lens' (8), 'hex' (6), 'diamond' (4).
    fuller = (z_start, z_end, half_width, depth 0..1). edge_mod(z, side) -> width factor (notches).
    xoff(z) -> x offset (curved blades). col_fn(p, role, col) -> col."""
    pal = pal or STEEL
    zb = z1 - tip
    if zs is None:
        zs = [z0 + (zb - z0) * i / (nr - 1) for i in range(nr)] + [zb + tip * 0.45, zb + tip * 0.8]

    def width(z):
        if wfn:
            return wfn(z)
        if z <= zb:
            return w0 + (w1 - w0) * (z - z0) / (zb - z0)
        return w1 * (1 - ((z - zb) / tip) ** tip_pow)

    def thick(z):
        if tfn:
            return tfn(z)
        if z <= zb:
            return t0 + (t1 - t0) * (z - z0) / (zb - z0)
        return t1 * (1 - 0.45 * (z - zb) / tip)

    rings, cols = [], []
    for z in zs:
        w, t = width(z), thick(z)
        wp = w * (edge_mod(z, 1) if edge_mod else 1.0)
        wm = w * (edge_mod(z, -1) if edge_mod else 1.0)
        x0 = xoff(z) if xoff else 0.0
        d, fw = 0.0, w * 0.25
        if fuller and kind == 'fuller':
            zf0, zf1, fwa, fd = fuller
            d = fd * sstep(zf1, zf1 - 0.07, z) * sstep(zf0 - 0.002, zf0 + 0.015, z)
            fw = min(fwa, w * 0.42)
        if kind == 'fuller':
            sp, sm = max(wp * 0.55, fw * 1.2), max(wm * 0.55, fw * 1.2)
            pts = [(wp, 0, 'e'), (sp, t, 's'), (fw, t, 'r'), (0, t * (1 - d), 'f'), (-fw, t, 'r'), (-sm, t, 's'),
                   (-wm, 0, 'e'), (-sm, -t, 's'), (-fw, -t, 'r'), (0, -t * (1 - d), 'f'), (fw, -t, 'r'), (sp, -t, 's')]
        elif kind == 'lens':
            pts = [(wp, 0, 'e'), (wp * 0.5, t * 0.74, 's'), (0, t, 'g'), (-wm * 0.5, t * 0.74, 's'),
                   (-wm, 0, 'e'), (-wm * 0.5, -t * 0.74, 's'), (0, -t, 'g'), (wp * 0.5, -t * 0.74, 's')]
        elif kind == 'hex':
            pts = [(wp, 0, 'e'), (wp * 0.55, t, 's'), (-wm * 0.55, t, 's'), (-wm, 0, 'e'), (-wm * 0.55, -t, 's'),
                   (wp * 0.55, -t, 's')]
        else:
            pts = [(wp, 0, 'e'), (0, t, 'g'), (-wm, 0, 'e'), (0, -t, 'g')]
        ring, rc = [], []
        kz = base_dark + (1 - base_dark) * sstep(z0, z0 + 0.06, z)
        for x, y, role in pts:
            p = Vector((x0 + x, y, z))
            if role == 'e':
                c = pal['edge']
            elif role == 'g':
                c = pal['ridge']
            elif role == 'f':
                c = mix(pal['body'], pal['fuller'], (d / fuller[3]) if (fuller and fuller[3] > 0) else 0.0)
            elif role == 'r':
                c = mix(pal['body'], pal['rim'], (d / fuller[3]) if (fuller and fuller[3] > 0) else 0.0)
            else:
                c = pal['body']
            c = mul(c, kz)
            if col_fn:
                c = col_fn(p, role, c)
            ring.append(p)
            rc.append(c)
        rings.append(ring)
        cols.append(rc)
    apex = Vector(((xoff(z1) if xoff else 0.0) + tip_dx, 0, z1))
    ac = pal['edge']
    if col_fn:
        ac = col_fn(apex, 'e', ac)
    mb.loft(rings, cols, mat, True, 'ngon', apex, sharp, capcol1=ac)
    return (round(z0, 3), round(z1, 3))


# ----------------------------------------------------------------------------- hilt parts
def grip(mb, z0, z1, rx, ry, mat='M_leather', ca=LEATHER, cb=LEATHER_DARK, n=9, swell=1.1, segs=6, bands=True,
         col_fn=None, waist=None):
    """Wrapped grip: lathe along Z, alternating band colors read as a cord / leather wrap."""
    prof = []
    for i in range(n):
        u = i / (n - 1)
        k = 1.0 + (swell - 1.0) * math.sin(math.pi * u)
        if waist:
            k *= 1.0 - waist * math.sin(math.pi * u) ** 2
        c = (ca if i % 2 == 0 else cb) if bands else mix(ca, cb, 0.5 + 0.5 * math.sin(u * 9.0))
        z = z0 + (z1 - z0) * u
        if col_fn:
            c = col_fn(Vector((0, 0, z)), c)
        prof.append((1.0 * k, z, c))
    return mb.lathe(prof, segs, mat, None, sx=rx, sy=ry, sharp=60.0)


def wheel_pommel(mb, zc, r, h, mat, col, hi=None, segs=8, boss=0.0, dark=None, ry=1.0):
    """Disc pommel whose axis is Y (faces visible from the flat of the blade)."""
    hi = hi or mul(col, 1.25)
    dark = dark or mul(col, 0.7)
    M = tr(0, 0, zc) @ sc(1, 1, ry) @ rot('X', 90)
    prof = [(0, -h * (1 + boss), hi), (r * 0.56, -h, dark if boss else col), (r * 0.96, -h * 0.55, hi),
            (r * 0.96, h * 0.55, hi), (r * 0.56, h, dark if boss else col), (0, h * (1 + boss), hi)]
    return mb.lathe(prof, segs, mat, M, sharp=30.0)


def pear_pommel(mb, zt, zb, r, mat, col, hi=None, segs=8, sy=0.85, facets=False):
    """Scent-stopper / pear pommel along Z (zt = top next to the grip, zb = bottom end)."""
    hi = hi or mul(col, 1.25)
    h = zt - zb
    prof = [(0, zb, hi), (r * 0.5, zb + h * 0.03, hi), (r * 0.96, zb + h * 0.28, col), (r, zb + h * 0.45, hi),
            (r * 0.74, zb + h * 0.78, col), (r * 0.52, zt, mul(col, 0.7))]
    return mb.lathe(prof, segs, mat, None, sx=1.0, sy=sy, sharp=(20.0 if facets else 50.0), cap1='fan')


def disc(mb, zc, r, h, mat, col, hi=None, segs=10, sy=1.0, bevel=0.6):
    """Flat disc whose axis is Z (rondel guard, collars, haft bands)."""
    hi = hi or mul(col, 1.3)
    prof = [(0, zc - h, col), (r * bevel, zc - h, col), (r, zc - h * 0.3, hi), (r, zc + h * 0.3, hi),
            (r * bevel, zc + h, col), (0, zc + h, col)]
    return mb.lathe(prof, segs, mat, None, sx=1.0, sy=sy, sharp=30.0)


def collar(mb, z0, z1, r, mat, col, hi=None, segs=8, sx=1.0, sy=1.0, lip=1.08):
    """Open band around a haft / grip end (ferrule, langet band)."""
    hi = hi or mul(col, 1.35)
    prof = [(r * 0.86, z0, col), (r * lip, z0 + (z1 - z0) * 0.28, hi), (r * lip, z0 + (z1 - z0) * 0.72, hi),
            (r * 0.86, z1, col)]
    return mb.lathe(prof, segs, mat, None, sx=sx, sy=sy, sharp=40.0)


def bar(mb, mat, stations, col, segs=6, square=False, sharp=35.0, cap=True, up=(0, 1, 0)):
    """Guard bar / quillons: stations = [(point, ry, rz[, color])...] swept as a tube
    (ry = half thickness along Y, rz = half height)."""
    path = [s[0] for s in stations]
    k = 1.4142 if square else 1.0
    radii = [(s[1] * k, s[2] * k) for s in stations]
    cols = [(s[3] if len(s) > 3 else col) for s in stations]
    return mb.tube(path, radii, 4 if square else segs, mat, cols, up=up, sharp=(25.0 if square else sharp),
                   phase=(math.pi / 4 if square else 0.0), cap0='fan' if cap else None, cap1='fan' if cap else None)


def quillons(mb, mat, z, L, ry, rz, col, hi=None, curve=0.0, power=2.0, end=(0.8, 0.8), flare=None, n=9, segs=6,
             square=False, asym=0.0, tipcol=None):
    """Symmetric cross-guard along X. curve > 0: ends sweep toward the blade (+Z). end = (ky, kz) scale at the
    tips. flare = (start 0..1, kz factor): spatulate ends."""
    hi = hi or mul(col, 1.3)
    st = []
    for i in range(n):
        u = -1 + 2 * i / (n - 1)
        a = abs(u)
        zz = z + curve * a ** power + (asym * u if asym else 0.0)
        ky = 1 + (end[0] - 1) * a
        kz = 1 + (end[1] - 1) * a
        if flare and a > flare[0]:
            kz *= 1 + (flare[1] - 1) * ((a - flare[0]) / (1 - flare[0])) ** 1.5
        c = mix(col, hi, a ** 2)
        if tipcol is not None and i in (0, n - 1):
            c = tipcol
        st.append((Vector((u * L, 0, zz)), ry * ky, rz * kz, c))
    return bar(mb, mat, st, col, segs, square)


def haft(mb, pts, radii, base=WOOD, segs=8, seed=0, grips=(), cap0='fan', cap1='fan', char=None, mat='M_wood_planks'):
    """Wooden haft swept along pts. radii: [(ry, rx)...] or r. grips = [(z0, z1)] darkened by hands.
    char = (z_start, z_full): fire-blackened above."""
    def col(p, i, j):
        n = fbm(p, 14.0, seed, 2)
        c = mix(mul(base, 0.74), mul(base, 1.12), n)
        for g0, g1 in grips:
            c = mul(c, 1.0 - 0.3 * sstep(g0 - 0.04, g0, p.z) * sstep(g1 + 0.04, g1, p.z))
        if char:
            c = mix(c, WOOD_CHAR, sstep(char[0], char[1], p.z) * (0.75 + 0.25 * n))
        return c
    return mb.tube(pts, radii, segs, mat, col, up=(0, 1, 0), uv=WOOD_UV, sharp=50.0, cap0=cap0, cap1=cap1)


def wrap(mb, z0, z1, rx, ry, ca=LEATHER, cb=LEATHER_DARK, n=7, segs=8, mat='M_leather', xc=0.0):
    """Leather strip wound round a haft (slightly proud of it)."""
    prof = []
    for i in range(n):
        u = i / (n - 1)
        k = 1.0 + (0.05 if i % 2 == 0 else 0.0)
        prof.append((k, z0 + (z1 - z0) * u, ca if i % 2 == 0 else cb))
    prof = [(0.82, z0 - 0.002, cb)] + prof + [(0.82, z1 + 0.002, cb)]
    return mb.lathe(prof, segs, mat, tr(xc, 0, 0), sx=rx, sy=ry, sharp=60.0)


def axe_blade(mb, mat, x0, x1, zt, zb, t0, bulge=0.02, ss=(0.0, 0.3, 0.6, 0.86, 1.0), nv=5, side=1, col=None,
              sharp=16.0, edge_at=0.86, horn_thin=0.55, cap=True):
    """Axe blade plate lofted from the eye (s = 0, x0) to the cutting edge (s = 1, x1).
    zt(s), zb(s) = top / bottom outline (absolute z). Thickness t0 at the eye, bevel from `edge_at`."""
    rings, cols = [], []
    col = col or (lambda s, v: mix(IRON, IRON_EDGE, sstep(edge_at - 0.08, 1.0, s)))
    for s in ss:
        x = x0 + (x1 - x0) * s
        if s >= 1.0 - 1e-9:
            t = 0.0
        elif s <= edge_at:
            t = t0 * (1 - 0.62 * s / edge_at)
        else:
            t = t0 * 0.38 * (1 - (s - edge_at) / (1 - edge_at))
        top, bot = zt(s), zb(s)
        fr, bk, cf, cb = [], [], [], []
        for k in range(nv):
            v = k / (nv - 1)
            z = bot + (top - bot) * v
            xx = x + bulge * 4 * v * (1 - v) * s * s
            tv = t * (1 - horn_thin * abs(2 * v - 1) ** 2.5)
            fr.append(Vector((side * xx, tv, z)))
            bk.append(Vector((side * xx, -tv, z)))
            c = col(s, v)
            cf.append(c)
            cb.append(c)
        rings.append(fr + bk[::-1])
        cols.append(cf + cb[::-1])
    mb.loft(rings, cols, mat, True, 'ngon' if cap else None, None, sharp)


def eye_socket(mb, z0, z1, rx, ry, mat, col, hi=None, segs=8):
    """Axe / hammer eye: oval iron sleeve round the haft."""
    hi = hi or mul(col, 1.3)
    prof = [(0.0, z0, col), (0.9, z0, col), (1.0, z0 + 0.006, hi), (1.0, z1 - 0.006, hi), (0.9, z1, col), (0.0, z1, col)]
    return mb.lathe(prof, segs, mat, None, sx=rx, sy=ry, sharp=40.0)


def langets(mb, z0, z1, r, mat, col, w=0.007, th=0.0035, rivets=2, hi=None):
    """Two iron tongues nailed along the haft on its flat (+Y / -Y) sides."""
    hi = hi or mul(col, 1.4)
    for sy_ in (1, -1):
        M = tr(0, sy_ * (r + th * 0.5), (z0 + z1) * 0.5)
        mb.cbox((w * 2, th, abs(z1 - z0)), mat, col, M)
        for i in range(rivets):
            z = z0 + (z1 - z0) * (i + 0.5) / rivets
            mb.spike((0, sy_ * (r + th), z), (0, sy_ * (r + th + 0.003), z), 0.0035, mat, hi, segs=4, up=(0, 0, 1))


def rivet(mb, p, n, r, mat, col, h=None):
    p, n = Vector(p), Vector(n).normalized()
    mb.spike(p, p + n * (h or r * 0.8), r, mat, col, segs=5, sharp=60.0, up=n.orthogonal())


def gem(mb, c, n, r, h, mat, col, hi, segs=6):
    """Low cabochon dome centered at c, bulging along n."""
    c, n = Vector(c), Vector(n).normalized()
    q = ZA.rotation_difference(n).to_matrix().to_4x4()
    M = tr(c) @ q
    mb.lathe([(r, 0.0, col), (r * 0.72, h * 0.62, col), (0, h, hi)], segs, mat, M, sharp=25.0)


def crystal(mb, c, axis, length, r, mat, col, hi, segs=5, seed=0, back=0.35):
    """Elongated faceted shard (double pyramid)."""
    c, axis = Vector(c), Vector(axis).normalized()
    rnd = random.Random(seed)
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    ring = []
    for j in range(segs):
        a = 2 * math.pi * j / segs + rnd.uniform(-0.2, 0.2)
        rr = r * rnd.uniform(0.8, 1.15)
        ring.append(c + u * (rr * math.cos(a)) + v * (rr * math.sin(a)) + axis * rnd.uniform(-0.1, 0.1) * length)
    mb.loft([ring], col, mat, True, c - axis * length * back, c + axis * length * (1 - back), 8.0,
            capcol0=mul(col, 0.8), capcol1=hi)
