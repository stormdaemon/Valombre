"""VALOMBRE nature pack - undergrowth: bush_a, bush_b, fern, reeds, flowers_a, mushrooms, stump, log (LOD0 only).

  blender -b --factory-startup -P tools/blender/nat_plants.py [-- name ...]

Foliage plants use the shared atlas (M_leaves) with COLOR_0 = (AO, wind, phase).
flowers_a (M_flowers) and mushrooms (M_mushroom): COLOR_0.rgb = actual linear colour.
stump / log: M_bark_oak, COLOR_0 = (AO, 0, 0).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nat_common import *

RECTS = None
TAU = 2 * math.pi


def stem_path(rng, start, d, L, n, gnarl=0.12, up=0.05):
    pts = [np.array(start, np.float64)]
    d = unit(d)
    for i in range(n):
        if i > 0:
            rv = rng.normal(size=3)
            rv -= d * np.dot(rv, d)
            d = unit(d + rv * gnarl + UP * up)
        pts.append(pts[-1] + d * L / n)
    return np.array(pts)


def sph_dir(z, az):
    s = math.sqrt(max(0.0, 1 - z * z))
    return np.array([s * math.cos(az), s * math.sin(az), z])


# ----------------------------------------------------------------------------- bushes
def build_bush(name, seed, cell, radii, n_tan, n_rad, S, stems=0):
    rng = np.random.RandomState(seed)
    rect = RECTS[cell]
    ch = rect['cy1'] - rect['cy0']
    mb = MB()
    LEAF = 1 if stems else 0
    mats = ([nat_mat('M_bark_oak')] if stems else []) + [nat_mat('M_leaves')]
    rad = np.array(radii, float)
    cen = np.array([0, 0, rad[2] * 0.2])
    for k in range(stems):
        az = TAU * (k + rng.uniform(-0.3, 0.3)) / stems
        a = math.radians(rng.uniform(10, 42))
        d = np.array([math.sin(a) * math.cos(az), math.sin(a) * math.sin(az), math.cos(a)])
        L = rad[2] * rng.uniform(0.7, 0.95)
        pts = stem_path(rng, (math.cos(az) * 0.07, math.sin(az) * 0.07, -0.08), d, L, 3, 0.16, 0.08)
        ph = rng.rand()
        tube(mb, pts, np.linspace(0.026, 0.007, 4), 3, 0, g=np.linspace(0, 0.4, 4), phase=ph, v0=rng.uniform(0, 2))
        for t, sz in ((0.5, 0.85), (0.78, 0.95), (1.0, 1.0), (1.0, 0.9)):
            i = min(int(t * 3), 2)
            f = t * 3 - i
            q = pts[i] + (pts[i + 1] - pts[i]) * f
            tan = unit(pts[i + 1] - pts[i])
            dd = unit(tan + rng.normal(size=3) * 0.45 + UP * 0.1)
            r = unit(np.cross(dd, rng.normal(size=3)))
            card(mb, rect, q, dd, r, rng.uniform(*S) * sz, nseg=1, flip=rng.rand() < 0.5, g0=0.2 + 0.2 * t, phase=ph,
                 mat=LEAF, clump=cen)
    for i in range(n_tan):                                   # shell cards facing outward, growing upward
        z = 0.06 + 0.9 * (i + 0.5) / n_tan
        dv = sph_dir(z, i * 2.39996 + rng.uniform(-0.3, 0.3))
        ps = cen + dv * rad * rng.uniform(0.70, 0.93)
        up_t = UP - dv * float(UP @ dv)
        if np.linalg.norm(up_t) < 0.35:
            a = rng.uniform(0, TAU)
            up_t = np.array([math.cos(a), math.sin(a), 0.0])
            up_t = up_t - dv * float(up_t @ dv)
        d = unit(unit(up_t) + dv * rng.uniform(0.25, 0.65))
        r = rot_about(unit(np.cross(d, dv)), d, math.radians(rng.uniform(-30, 30)))
        Sx = rng.uniform(*S)
        anchor = ps - d * ch * Sx * 0.5
        anchor[2] = max(anchor[2], 0.02)
        card(mb, rect, anchor, d, r, Sx, nseg=1, flip=rng.rand() < 0.5, g0=0.3, phase=rng.rand(), mat=LEAF, clump=cen)
    for i in range(n_rad):                                   # radial sprigs (silhouette)
        z = 0.04 + 0.94 * (i + 0.5) / n_rad
        dv = sph_dir(z, i * 2.39996 * 1.7 + 1.0)
        d = unit(dv * rad / rad.max() + UP * 0.15)
        Sx = rng.uniform(*S)
        ps = cen + dv * rad * rng.uniform(0.98, 1.08)
        anchor = ps - d * ch * Sx
        anchor[2] = max(anchor[2], 0.0)
        r = unit(np.cross(d, rng.normal(size=3)))
        card(mb, rect, anchor, d, r, Sx, nseg=1, flip=rng.rand() < 0.5, g0=0.3, phase=rng.rand(), mat=LEAF, clump=cen)
    finish_tree(mb, lo=0.42, kappa=0.4, ground_h=0.7, ground_lo=0.6, w_global=0.3, w_local=0.0, w_up=0.7)
    return mb.build(name + '_LOD0', mats), mb


# ----------------------------------------------------------------------------- fern / reeds
def build_fern(name, seed):
    rng = np.random.RandomState(seed)
    rect = RECTS['fern_frond']
    ch = rect['cy1'] - rect['cy0']
    mb = MB()
    n = 9
    for k in range(n):
        az = TAU * (k + rng.uniform(-0.25, 0.25)) / n
        el = math.radians(rng.uniform(46, 64))
        d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        r = np.array([-math.sin(az), math.cos(az), 0.0])
        Lf = rng.uniform(0.62, 0.82)
        card(mb, rect, (math.cos(az) * 0.03, math.sin(az) * 0.03, 0.0), d, r, Lf / ch, nseg=3, droop=0.42,
             flip=rng.rand() < 0.5, g0=0.05, phase=rng.rand(), mat=0, clump=(0, 0, -0.1))
    for k in range(3):
        az = TAU * (k + rng.uniform(-0.2, 0.2)) / 3 + 0.5
        el = math.radians(rng.uniform(72, 84))
        d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        r = np.array([-math.sin(az), math.cos(az), 0.0])
        card(mb, rect, (0, 0, 0.0), d, r, rng.uniform(0.42, 0.52) / ch, nseg=2, droop=0.22, flip=rng.rand() < 0.5,
             g0=0.05, phase=rng.rand(), mat=0, clump=(0, 0, -0.1))
    finish_tree(mb, lo=0.5, kappa=0.3, ground_h=0.3, ground_lo=0.55, w_global=0.3, w_local=0.0, w_up=0.7)
    return mb.build(name + '_LOD0', [nat_mat('M_leaves')]), mb


def build_reeds(name, seed):
    rng = np.random.RandomState(seed)
    rect = RECTS['reed_blades']
    ch = rect['cy1'] - rect['cy0']
    mb = MB()
    n = 16
    for k in range(n):
        a = k * 2.39996 + rng.uniform(-0.4, 0.4)
        rr = 0.46 * math.sqrt((k + 0.5) / n)
        out = np.array([math.cos(a), math.sin(a), 0.0])
        pos = out * rr
        yaw = rng.uniform(0, TAU)
        d = unit(UP + out * rng.uniform(0.02, 0.16) * (0.4 + rr * 2) + rng.normal(size=3) * 0.03)
        S = rng.uniform(0.7, 0.92)
        H = rng.uniform(1.15, 1.55)
        card(mb, rect, pos - UP * 0.03, d, np.array([math.cos(yaw), math.sin(yaw), 0.0]), S, nseg=2, droop=0.03,
             flip=rng.rand() < 0.5, lscale=H / (ch * S), g0=0.0, phase=rng.rand(), mat=0, clump=(0, 0, 0.2))
    finish_tree(mb, lo=0.5, kappa=0.25, ground_h=0.5, ground_lo=0.55, w_global=0.35, w_local=0.0, w_up=0.65)
    return mb.build(name + '_LOD0', [nat_mat('M_leaves')]), mb


# ----------------------------------------------------------------------------- flowers (COLOR_0 = tint)
FLOWER_TINTS = ['#f2ecd8', '#e8c33a', '#7d62c9', '#f2ecd8', '#c9442f', '#5f83cf', '#e8c33a', '#d98aae', '#f2ecd8']


def build_flowers(name, seed):
    rng = np.random.RandomState(seed)
    rect = RECTS['flower_heads']
    mb = MB()
    split = 0.5
    lo = dict(rect)
    lo['cy1'] = split
    hi = dict(rect)
    hi['cy0'] = split
    n = len(FLOWER_TINTS)
    for k in range(n):
        a = TAU * (k + rng.uniform(-0.3, 0.3)) / n
        out = np.array([math.cos(a), math.sin(a), 0.0])
        rr = rng.uniform(0.02, 0.2)
        lean = rng.uniform(0.2, 0.75)
        d = unit(UP + out * lean)
        yaw = a + math.pi / 2 + rng.uniform(-0.6, 0.6)
        r = np.array([math.cos(yaw), math.sin(yaw), 0.0])
        S = rng.uniform(0.46, 0.6)
        tint = np.array(lin(FLOWER_TINTS[k]))
        base = out * rr - UP * 0.01
        flip = rng.rand() < 0.5
        green = np.array([0.9, 0.95, 0.85])
        card(mb, lo, base, d, r, S, nseg=1, flip=flip, mat=0, clump=(0, 0, 0),
             col_fn=lambda t, x, g=green: tuple(g * (0.6 + 0.4 * t)))
        dd = d
        base2 = base + dd * (split - lo['cy0']) * S
        card(mb, hi, base2, d, r, S, nseg=1, flip=flip, mat=0, clump=(0, 0, 0),
             col_fn=lambda t, x, c=tint: tuple(c))
    mb.arrays()
    # ground-plant normals: mostly up, a little outward
    o = mb.pos.copy()
    o[:, 2] = 0
    o /= np.maximum(np.linalg.norm(o, axis=1), 1e-6)[:, None]
    nn = o * 0.35 + UP[None, :] * 0.75
    mb.nrm = nn / np.linalg.norm(nn, axis=1)[:, None]
    return mb.build(name + '_LOD0', [nat_mat('M_flowers')]), mb


# ----------------------------------------------------------------------------- lathe helpers (solid props)
def ring(mb, pos, uv, col):
    return mb.add(pos, np.zeros_like(pos), uv, col, kind=0)


def band(mb, a, b, n, mat=0):
    for j in range(n):
        mb.face((a + j, a + j + 1, b + j + 1, b + j), mat)


def fan(mb, a, c, n, mat=0, flip=False):
    for j in range(n):
        mb.face((a + j + 1, a + j, c) if flip else (a + j, a + j + 1, c), mat)


def build_mushrooms(name, seed):
    rng = np.random.RandomState(seed)
    mb = MB()
    specs = [(0.00, 0.00, 0.19, 0.095, 0.06), (0.16, 0.07, 0.14, 0.07, 0.05), (-0.13, 0.11, 0.105, 0.055, 0.042),
             (-0.06, -0.15, 0.155, 0.08, 0.05), (0.12, -0.12, 0.085, 0.045, 0.035)]
    stem_top, stem_base = np.array(lin('#cfc3a2')), np.array(lin('#9a8c6e')) * 0.6
    gill = np.array(lin('#8f7d5e')) * 0.55
    for (x, y, h, cr, chh) in specs:
        rs = cr * 0.3
        az, tilt = rng.uniform(0, TAU), rng.uniform(0.0, 0.3)
        ax = np.array([math.cos(az), math.sin(az), 0.0])
        hue = rng.uniform(0.0, 1.0)
        cap_top = np.array(lin('#4f2a1c')) * (0.8 + 0.3 * hue) + np.array([0.02, 0.0, 0.0]) * hue
        cap_rim = np.array(lin('#86583a')) * (0.85 + 0.3 * hue)
        base = np.array([x, y, 0.0])

        def tr(p):
            p = np.asarray(p, float)
            return np.array([rot_about(q, ax, tilt) for q in p]) + base

        s4 = np.linspace(0, TAU, 5)
        s5 = np.linspace(0, TAU, 6)
        c4, n4 = np.cos(s4), np.sin(s4)
        c5, n5 = np.cos(s5), np.sin(s5)
        uv4 = np.stack([s4 / TAU * 0.5, np.zeros(5)], axis=1)
        a = ring(mb, tr(np.stack([c4 * rs * 1.3, n4 * rs * 1.3, np.full(5, -0.02)], axis=1)), uv4,
                 np.tile(stem_base, (5, 1)))
        b = ring(mb, tr(np.stack([c4 * rs * 0.85, n4 * rs * 0.85, np.full(5, h - 0.01)], axis=1)),
                 uv4 + np.array([0, h * 2]), np.tile(stem_top * 0.7, (5, 1)))
        band(mb, a, b, 4)
        wob = 1.0 + 0.08 * np.cos(s5 * 2 + rng.uniform(0, 6))
        rim_p = np.stack([c5 * cr * wob, n5 * cr * wob, np.full(6, h - 0.12 * chh)], axis=1)
        uv5 = np.stack([0.5 + c5 * 0.4, 0.5 + n5 * 0.4], axis=1)
        rim = ring(mb, tr(rim_p), uv5, np.tile(cap_rim, (6, 1)))
        mid = ring(mb, tr(np.stack([c5 * cr * 0.62, n5 * cr * 0.62, np.full(6, h + 0.62 * chh)], axis=1)),
                   np.stack([0.5 + c5 * 0.25, 0.5 + n5 * 0.25], axis=1), np.tile((cap_rim + cap_top) / 2, (6, 1)))
        band(mb, rim, mid, 5)
        apex = mb.add(tr([[0, 0, h + chh]]), [[0, 0, 1]], [[0.5, 0.5]], [cap_top], kind=0)
        fan(mb, mid, apex, 5)
        rim2 = ring(mb, tr(rim_p), uv5, np.tile(gill, (6, 1)))
        cen = mb.add(tr([[0, 0, h - 0.03]]), [[0, 0, -1]], [[0.5, 0.5]], [gill * 0.8], kind=0)
        fan(mb, rim2, cen, 5, flip=True)
    mb.auto_normals(angle=70.0)
    return mb.build(name + '_LOD0', [nat_mat('M_mushroom')]), mb


def build_stump(name, seed):
    rng = np.random.RandomState(seed)
    mb = MB()
    sides = 10
    R, H = 0.36, 0.60
    ang = np.linspace(0, TAU, sides + 1)
    ca, sa = np.cos(ang), np.sin(ang)
    ph = rng.uniform(0, 6, 6)
    wob = 1 + 0.07 * np.cos(2 * ang + ph[0]) + 0.05 * np.cos(3 * ang + ph[1])
    lob = 0.24 * np.cos(4 * ang + ph[2]) + 0.12 * np.cos(7 * ang + ph[3])
    zs = [-0.25, 0.05, 0.27, H]
    fl = [1.75, 1.42, 1.1, 1.0]
    rings = []
    top_pos = None
    for z, f in zip(zs, fl):
        r = R * f * wob * (1 + (f - 1) * 1.1 * lob)
        zz = np.full(sides + 1, z)
        if z == H:
            zz = H + 0.07 * np.cos(ang + ph[4]) + 0.05 * np.cos(3 * ang + ph[5]) + 0.03 * np.cos(5 * ang)
            zz[-1] = zz[0]
        pos = np.stack([r * ca + 0.05 * z, r * sa, zz], axis=1)
        if z == H:
            top_pos = pos
        uv = np.stack([ang / TAU * 3.0, zz], axis=1)
        rings.append(ring(mb, pos, uv, np.tile([1.0, 0, 0], (sides + 1, 1))))
    for i in range(3):
        band(mb, rings[i], rings[i + 1], sides)
    # top: broken, slightly hollow
    cen_top = top_pos[:sides].mean(axis=0)
    rim = ring(mb, top_pos, np.stack([0.5 + ca * 0.36, 0.5 + sa * 0.36], axis=1), np.tile([1.0, 0, 0], (sides + 1, 1)))
    inner_p = cen_top + (top_pos - cen_top) * 0.6
    inner_p[:, 2] = top_pos[:, 2] - 0.045 + rng.uniform(-0.02, 0.02, sides + 1)
    inner_p[-1] = inner_p[0]
    inner = ring(mb, inner_p, np.stack([0.5 + ca * 0.22, 0.5 + sa * 0.22], axis=1),
                 np.tile([1.0, 0, 0], (sides + 1, 1)))
    band(mb, rim, inner, sides)
    c = mb.add([cen_top + np.array([0, 0, -0.10])], [[0, 0, 1]], [[0.5, 0.5]], [[1.0, 0, 0]], kind=0)
    fan(mb, inner, c, sides)
    # roots
    for k in range(5):
        az = TAU * (k + rng.uniform(-0.25, 0.25)) / 5 + ph[2] * 0.25
        o = np.array([math.cos(az), math.sin(az), 0.0])
        side = np.array([-o[1], o[0], 0.0])
        w = rng.uniform(-0.2, 0.2)
        sp = rng.uniform(1.9, 2.5)
        pts = [o * R * 0.3 + UP * 0.34, o * R * 1.15 + UP * 0.15 + side * w * 0.1,
               o * R * (1.15 + (sp - 1.15) * 0.6) + UP * 0.03 + side * w * 0.3, o * R * sp + UP * -0.28 + side * w * 0.5]
        tube(mb, pts, np.array([0.19, 0.16, 0.11, 0.06]) * rng.uniform(0.85, 1.15), 4, 0, g=0.0, phase=0.0,
             v0=rng.uniform(0, 2))
    mb.auto_normals(angle=62.0)
    ob = mb.build(name + '_LOD0', [nat_mat('M_bark_oak')])
    ao = bake_ao_raycast(ob, dist=0.9, rays=64, lo=0.32, ground_grad=0.25)
    set_colors_per_vertex(ob, np.stack([ao, np.zeros_like(ao), np.zeros_like(ao)], axis=1))
    return ob, mb


def build_log(name, seed):
    rng = np.random.RandomState(seed)
    mb = MB()
    sides, nseg, L = 8, 6, 3.0
    ang = np.linspace(0, TAU, sides + 1)
    ca, sa = np.cos(ang), np.sin(ang)
    ph = rng.uniform(0, 6, 6)
    wob = 1 + 0.06 * np.cos(2 * ang + ph[0]) + 0.04 * np.cos(3 * ang + ph[1])
    xs = np.linspace(-L / 2, L / 2, nseg + 1)
    rr = np.linspace(0.27, 0.215, nseg + 1) + rng.uniform(-0.012, 0.012, nseg + 1)
    yy = 0.05 * np.sin(xs * 1.3 + ph[2])
    zc = rr * 0.80
    rings = []
    ends = []
    for i in range(nseg + 1):
        pos = np.stack([np.full(sides + 1, xs[i]), yy[i] + rr[i] * wob * ca, zc[i] + rr[i] * wob * sa], axis=1)
        if i == nseg:                         # broken end: jagged
            jag = 0.07 * np.cos(3 * ang + ph[3]) + 0.05 * np.cos(5 * ang + ph[4])
            jag[-1] = jag[0]
            pos[:, 0] += jag
        uv = np.stack([ang / TAU * 2.0, np.full(sides + 1, xs[i] + L / 2)], axis=1)
        rings.append(ring(mb, pos, uv, np.tile([1.0, 0, 0], (sides + 1, 1))))
        if i in (0, nseg):
            ends.append(pos)
    for i in range(nseg):
        band(mb, rings[i], rings[i + 1], sides)
    for e, pos in enumerate(ends):                # end caps, slightly hollow
        sgn = -1.0 if e == 0 else 1.0
        cen = pos[:sides].mean(axis=0)
        uvr = np.stack([0.5 + ca * 0.3, 0.5 + sa * 0.3], axis=1)
        rim = ring(mb, pos, uvr, np.tile([1.0, 0, 0], (sides + 1, 1)))
        ip = cen + (pos - cen) * 0.58
        ip[:, 0] = pos[:, 0] - sgn * 0.07
        inner = ring(mb, ip, np.stack([0.5 + ca * 0.17, 0.5 + sa * 0.17], axis=1), np.tile([1.0, 0, 0], (sides + 1, 1)))
        c = mb.add([cen - np.array([sgn * 0.16, 0, 0])], [[sgn, 0, 0]], [[0.5, 0.5]], [[1.0, 0, 0]], kind=0)
        if e == 0:
            band(mb, inner, rim, sides)
            fan(mb, inner, c, sides, flip=True)
        else:
            band(mb, rim, inner, sides)
            fan(mb, inner, c, sides)
    for (x, az, ln, r0) in ((-0.55, 1.15, 0.5, 0.075), (0.45, 2.3, 0.34, 0.06)):      # branch stubs
        p0 = np.array([x, float(np.interp(x, xs, yy)), float(np.interp(x, xs, zc))])
        d = unit(np.array([0.25, math.cos(az), math.sin(az)]))
        pts = [p0, p0 + d * (0.24 + ln * 0.4), p0 + d * (0.24 + ln) + UP * 0.03]
        tube(mb, pts, [r0, r0 * 0.85, r0 * 0.62], 5, 0, g=0.0, phase=0.0, tip='flat', v0=0.0)
    mb.auto_normals(angle=62.0)
    ob = mb.build(name + '_LOD0', [nat_mat('M_bark_oak')])
    ao = bake_ao_raycast(ob, dist=0.8, rays=64, lo=0.32, ground_grad=0.2)
    set_colors_per_vertex(ob, np.stack([ao, np.zeros_like(ao), np.zeros_like(ao)], axis=1))
    return ob, mb


# ----------------------------------------------------------------------------- registry
ASSETS_P = {
    'bush_a': (lambda: build_bush('bush_a', 11, 'bush_sprig_a', (0.78, 0.78, 0.98), 34, 26, (0.66, 0.9)),
               dict(description='round dense broad-leaf bush', collider=None, budget=350,
                    vertex_color='R=AO, G=wind weight, B=phase')),
    'bush_b': (lambda: build_bush('bush_b', 23, 'bush_sprig_b', (0.55, 0.55, 1.15), 24, 20, (0.56, 0.78), stems=6),
               dict(description='taller thorny bush with red berries, visible woody stems', collider=None, budget=350,
                    vertex_color='R=AO, G=wind weight, B=phase')),
    'fern': (lambda: build_fern('fern', 31),
             dict(description='rosette of arching fern fronds', collider=None, budget=80,
                  vertex_color='R=AO, G=wind weight, B=phase')),
    'reeds': (lambda: build_reeds('reeds', 41),
              dict(description='swamp reed cluster with cattail heads', collider=None, budget=120,
                   vertex_color='R=AO, G=wind weight, B=phase')),
    'flowers_a': (lambda: build_flowers('flowers_a', 53),
                  dict(description='wild flower clump (white, yellow, violet, blue, red, pink heads)', collider=None,
                       budget=60, vertex_color='RGB = actual linear tint (multiply the atlas); no wind data: '
                                                'sway by height (uv/position y)')),
    'mushrooms': (lambda: build_mushrooms('mushrooms', 61),
                  dict(description='cluster of 5 brown-capped mushrooms, solid geometry', collider=None, budget=150,
                       vertex_color='RGB = actual linear colour (AO baked in)')),
    'stump': (lambda: build_stump('stump', 71),
              dict(description='old broken tree stump with flaring roots',
                   collider={'type': 'box', 'size': [0.8, 0.6, 0.8], 'center': [0.0, 0.3, 0.0]}, budget=200,
                   vertex_color='R=AO, G=0, B=0')),
    'log': (lambda: build_log('log', 83),
            dict(description='fallen 3 m log lying along X, one end broken, two branch stubs',
                 collider={'type': 'box', 'size': [3.0, 0.5, 0.56], 'center': [0.0, 0.22, 0.0]}, budget=250,
                 vertex_color='R=AO, G=0, B=0')),
}


def main():
    global RECTS
    only = cli_only()
    done = []
    for name, (fn, meta) in ASSETS_P.items():
        if only and name not in only:
            continue
        reset_scene()
        RECTS = atlas_rects()
        ob, mb = fn()
        ob['valombre'] = json.dumps(meta)
        path = os.path.join(NATURE, name + '.glb')
        export_glb(path, [ob])
        for k, v in glb_mesh_stats(path).items():
            flag = '' if v['tris'] <= meta['budget'] else '  !!! OVER BUDGET'
            print('STATS', k, 'tris', v['tris'], v['tris_by_material'], 'size', v['size'], 'min', v['min'], 'max',
                  v['max'], flag)
        preview_materials()
        nat_sheet(os.path.join(PREVIEWS, 'nat_%s.png' % name), [[ob]], views=('front', 'persp', 'top'), res=320)
        done.append(name)
    stack_images([os.path.join(PREVIEWS, 'nat_%s.png' % n) for n in ASSETS_P], os.path.join(PREVIEWS, 'nat_plants.png'),
                 cols=2)


main()
