"""VALOMBRE building textures (1024 px, one tile = 2 m): stone_wall, stone_brick, cobble, plaster,
wood_planks, roof_tiles, thatch.
Run:  blender -b --factory-startup -P tools/blender/tex_building.py -- [names...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex_lib import *

N = 1024
TILE = 2.0


def grain_noise(n, seed, lo=40, beta=0.6):
    """Fine isotropic grain (unit std)."""
    return spectral(n, seed, beta=beta, lo=lo)


def speckle(n, seed, density, sigma=0.8):
    """Sparse soft dots 0..1 (pits, grit)."""
    w = (white(n, seed) > (1.0 - density)).astype(F)
    s = blur(w, sigma)
    return sat(s * (2.0 * math.pi * sigma * sigma) * 1.3)


# ============================================================================= stone_wall
def stone_wall():
    n, S = N, 71
    x, y = grid(n)
    wx = fbm(n, 4, 3, S + 1) * 13 + fbm(n, 14, 2, S + 2) * 5
    wy = fbm(n, 4, 3, S + 3) * 13 + fbm(n, 14, 2, S + 4) * 5
    xw = x + wx / n
    yw = y + wy / n
    rows = random_rows(10, S, hvar=0.42, wmin=0.075, wmax=0.27, skew=0.16)
    c = courses(xw, yw, rows)
    c = split_cells(c, S + 5, prob_h=0.20, prob_v=0.08, min_h=0.10, min_w=0.16)
    a = c.a * n
    b = c.b * n
    rad = np.minimum(id_rand(c.id, S + 6, 8, 30), np.minimum(c.w, c.h) * n * 0.46)
    gap = id_rand(c.id, S + 7, 2.2, 5.5)
    d = rrect(a, b, rad) - gap + fbm(n, 16, 3, S + 8) * 5.5 + fbm(n, 55, 2, S + 81) * 1.3
    bev = id_rand(c.id, S + 9, 5, 13)
    t = sat(d / bev)
    prof = 1 - (1 - t) ** 2

    # stone face: per stone level + tilt, rough-hewn facets, lumps, grain, pits
    top = 10.5 + id_randn(c.id, S + 10, 1.9)
    top += (c.u - 0.5) * id_randn(c.id, S + 11, 3.6) + (c.v - 0.5) * id_randn(c.id, S + 12, 2.8)
    fw = worley(n, 13, seed=S + 13, jitter=0.95, x=xw, y=yw)
    fm = smoothstep(0.0, 0.22, fw.edge)
    facets = (fw.dx * id_randn(fw.id, S + 14, 1.0) + fw.dy * id_randn(fw.id, S + 15, 1.0)) * 3.0 * fm
    facets += id_randn(fw.id, S + 16, 0.7) * fm
    lumps = fbm(n, 9, 4, S + 17) * 2.6
    gr = grain_noise(n, S + 18)
    pits = speckle(n, S + 19, 0.0012, 1.3)
    face = top + facets + lumps + gr * 0.30 - pits * 1.6
    Hs = prof * face
    Hm = 1.6 + fbm(n, 36, 3, S + 20) * 1.0 + gr * 0.35
    H = np.maximum(Hs, Hm)
    sm = smoothstep(0.0, 1.6, Hs - Hm)                      # 1 on stone, 0 on mortar

    # ---- albedo
    pal = ['#8f8a7d', '#969080', '#999181', '#8a857b', '#938875', '#85827a', '#979285', '#8c8375', '#807e78',
           '#948a79', '#8b857a', '#99917f']
    col = palette_pick(c.id, pal, S + 21)
    col = col * (1.0 + np.clip(id_randn(c.id, S + 22, 0.04), -0.07, 0.06))[..., None]
    mott = fbm(n, 7, 4, S + 23)
    col = col * (1.0 + 0.13 * mott + 0.06 * fbm(n, 40, 3, S + 24) + 0.035 * gr)[..., None]
    col = col + (hexc('#b09a78') - hexc('#8a9096'))[None, None, :] * (fbm(n, 3, 3, S + 25) * 0.16)[..., None]
    col = col * (1.0 + 0.05 * np.clip(facets / 3.0, -1, 1))[..., None]
    mortar = ramp(norm01(fbm(n, 14, 4, S + 26) + gr * 0.25), [(0, '#958b78'), (0.5, '#b0a690'), (1, '#c4baa2')])
    alb = mix(mortar, col, sm)
    # dirt in the joints and under stones (cavity only, no light direction)
    ao = ao_from_height(H, (3.0, 9.0, 24.0), 0.9)
    alb = alb * (0.78 + 0.22 * ao)[..., None]
    alb = mix(alb, alb * hexc('#96866c') / 0.55, sat((1 - ao) * 1.2) * 0.45)
    # moss: grows in joints / on ledges in damp patches
    mfield = fbm(n, 4, 4, S + 27) + 0.35 * fbm(n, 22, 3, S + 28)
    joint = 1.0 - smoothstep(0.0, 9.0, d)
    moss = smoothstep(0.15, 0.55, mfield + joint * 0.45 - 0.33) * (0.30 + 0.70 * joint)
    moss *= smoothstep(-0.2, 0.3, fbm(n, 48, 2, S + 29) + 0.2)
    mcol = ramp(norm01(fbm(n, 30, 3, S + 30)), [(0, '#4b5630'), (0.5, '#606b38'), (1, '#7c8048')])
    alb = mix(alb, mcol, moss * 0.85)
    H = H + moss * (1.2 + 0.8 * fbm(n, 60, 2, S + 31))
    # lichen specks (pale)
    lich = smoothstep(0.62, 0.8, fbm(n, 34, 3, S + 32, mode='billow') * 1.6) * sm * 0.35
    alb = mix(alb, '#b4b39a', lich)
    alb = balance(alb, 0.25, 0.7)

    rough = 0.80 + id_randn(c.id, S + 33, 0.045) + 0.05 * mott - 0.05 * sat(cavity(H, 4) / 2.0)
    rough = lerp(0.93, rough, sm)
    rough = lerp(rough, 0.96, moss)
    save_tex('stone_wall', alb, H, rough, ao=ao_from_height(H, (3.0, 9.0, 24.0), 1.0), nscale=1.0, tile_m=TILE,
             height=norm01(H, 0.5, 99.8))


# ============================================================================= stone_brick
def stone_brick():
    n, S = N, 123
    x, y = grid(n)
    xw = x + fbm(n, 5, 2, S + 1) * 2.4 / n
    yw = y + fbm(n, 5, 2, S + 2) * 2.4 / n
    r = rng(S)
    hs = 1.0 + (r.random(8) - 0.5) * 0.10
    hs /= hs.sum()
    rows = []
    for i in range(8):
        ws = 0.25 * (1 + (r.random(4) - 0.5) * 0.30)
        ws /= ws.sum()
        off = ((0.125 if i % 2 else 0.0) + r.normal(0, 0.014)) % 1.0
        rows.append((hs[i], ws, off, np.zeros(4)))
    c = courses(xw, yw, rows)
    a = c.a * n
    b = c.b * n
    gr = grain_noise(n, S + 3)
    gap = id_rand(c.id, S + 4, 1.4, 3.0)
    near_edge = 1 - smoothstep(0, 26, np.minimum(a, b))
    chipn = fbm(n, 11, 4, S + 5) + 0.25 * fbm(n, 40, 2, S + 6)
    chip = sat((chipn - 0.20) * 2.6) ** 1.4 * 20 * near_edge
    d = rrect(a, b, 4.0) - gap - chip + fbm(n, 60, 2, S + 7) * 0.7
    bev = id_rand(c.id, S + 8, 2.5, 5.5)
    t = sat(d / bev)
    prof = 1 - (1 - t) ** 2
    top = 9.0 + id_randn(c.id, S + 9, 0.9)
    top += (c.u - 0.5) * id_randn(c.id, S + 10, 1.3) + (c.v - 0.5) * id_randn(c.id, S + 11, 0.9)
    erosion = fbm(n, 5, 5, S + 12) * 1.7
    pitz = smoothstep(0.0, 0.5, fbm(n, 5, 3, S + 13))
    pits = speckle(n, S + 14, 0.006, 1.0) * pitz ** 2 * 1.5 + speckle(n, S + 15, 0.0007, 2.2) * 2.2
    ang = id_rand(c.id, S + 16, 0.2, 2.9)
    lu = c.u * c.w * n
    lv = c.v * c.h * n
    tool = np.sin((lu * np.cos(ang) + lv * np.sin(ang)) * TAU / 6.0 + fbm(n, 9, 2, S + 17) * 7.0)
    tool = tool * 0.30 * id_rand(c.id, S + 18, 0.15, 1.0)
    # soft chip slopes: broken arrises expose a sloping fracture
    chipdent = sat(chip / 10.0) * 2.5
    face = top + erosion + tool - pits + gr * 0.26 - chipdent
    Hs = prof * face
    Hm = 3.2 + fbm(n, 40, 3, S + 19) * 0.8 + gr * 0.4
    H = np.maximum(Hs, Hm)
    sm = smoothstep(0.0, 1.2, Hs - Hm)

    pal = ['#989282', '#9e9786', '#918b7e', '#a09885', '#8d887d', '#9b9382', '#958d7d', '#9c9588']
    col = palette_pick(c.id, pal, S + 20)
    col = col * (1.0 + np.clip(id_randn(c.id, S + 21, 0.035), -0.06, 0.05))[..., None]
    mott = fbm(n, 6, 5, S + 22)
    col = col * (1.0 + 0.10 * mott + 0.05 * fbm(n, 48, 2, S + 23) + 0.03 * gr)[..., None]
    col = col + (hexc('#b39f7e') - hexc('#868c92'))[None, None, :] * (fbm(n, 3, 3, S + 24) * 0.14)[..., None]
    # fossil / sediment bedding lines inside the limestone (very faint horizontal laminations)
    bed = spectral(n, S + 25, beta=1.0, lo=6, hi=200, sx=7.0, sy=1.0)
    col = col * (1.0 + 0.035 * bed)[..., None]
    col = mix(col, col * 1.12, sat(chip / 8.0) * 0.6)                 # fresh stone where chipped
    mortar = ramp(norm01(fbm(n, 16, 4, S + 26) + gr * 0.3), [(0, '#7d7566'), (0.5, '#958d7b'), (1, '#aaa18d')])
    alb = mix(mortar, col, sm)
    # weathering streaks running down from the joints
    st = spectral(n, S + 27, beta=1.1, lo=10, hi=200, sx=1.0, sy=16.0)
    below = (1.0 - c.v) ** 1.3
    dark = sat(st * 0.55 - 0.15) * (0.35 + 0.65 * below) * sm
    alb = mix(alb, alb * hexc('#6e6658') / 0.42 * 0.62, dark * 0.55)
    pale = sat(-st * 0.5 - 0.35) * below * sm
    alb = mix(alb, '#b9b4a4', pale * 0.30)
    ao = ao_from_height(H, (2.5, 8.0, 22.0), 1.0)
    alb = alb * (0.80 + 0.20 * ao)[..., None]
    # soot / damp darkening in large soft patches + faint moss in joints
    alb = alb * (1.0 - 0.10 * smoothstep(0.0, 0.6, fbm(n, 3, 3, S + 28)))[..., None]
    joint = 1.0 - smoothstep(0.0, 6.0, d)
    moss = joint * smoothstep(0.25, 0.6, fbm(n, 5, 4, S + 29) + 0.15 * fbm(n, 40, 2, S + 30))
    alb = mix(alb, '#5d6638', moss * 0.6)
    alb = balance(alb, 0.25, 0.7)

    rough = 0.76 + id_randn(c.id, S + 31, 0.03) + 0.06 * mott + 0.10 * dark - 0.03 * tool
    rough = lerp(0.93, rough, sm)
    rough = lerp(rough, 0.95, moss)
    save_tex('stone_brick', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.8))


# ============================================================================= cobble
def cobble():
    n, S = N, 211
    K = 18
    xw, yw = warped_grid(n, 12, 5, S, 2)
    w = worley(n, K, K, S + 1, jitter=0.66, x=xw, y=yw, hexa=True)
    cell = n / K
    e = w.edge * cell
    gap = id_rand(w.id, S + 2, 2.5, 7.0)
    inside = sat((e - gap) / 2.0 + 0.5)
    soft = blur(inside, 7.0)                                   # rounds the polygon corners
    t = smoothstep(0.45, 0.97, soft)
    prof = np.sqrt(1 - (1 - t) ** 2)
    dome = 1 - sat(w.f1 / 0.80) ** 2
    gr = grain_noise(n, S + 3)
    top = 12.0 + id_randn(w.id, S + 4, 1.8)
    tilt = (w.dx * id_randn(w.id, S + 5, 3.2) + w.dy * id_randn(w.id, S + 6, 3.2))
    lumps = fbm(n, 12, 4, S + 7) * 1.8
    pits = speckle(n, S + 8, 0.006, 1.2)
    face = top * (0.70 + 0.30 * dome) + tilt + lumps + gr * 0.22 - pits * 1.4
    Hs = prof * face
    # packed dirt between stones, with grit
    dirt_n = fbm(n, 20, 4, S + 9)
    grit = speckle(n, S + 10, 0.02, 1.3)
    Hd = 4.2 + dirt_n * 2.0 + grit * 1.6 + gr * 0.5
    H = np.maximum(Hs, Hd)
    sm = smoothstep(0.0, 1.5, Hs - Hd)

    pal = ['#7f7b74', '#8c857a', '#7a7977', '#938a79', '#716f6b', '#85807a', '#8a7f72', '#7d7e7d', '#958e80',
           '#80786c']
    col = palette_pick(w.id, pal, S + 11)
    col = col * (1.0 + id_randn(w.id, S + 12, 0.06))[..., None]
    mott = fbm(n, 9, 4, S + 13)
    col = col * (1.0 + 0.10 * mott + 0.05 * fbm(n, 50, 2, S + 14) + 0.03 * gr)[..., None]
    # mineral veins on some stones
    vein = (1 - smoothstep(0.0, 0.035, np.abs(fbm(n, 7, 3, S + 15)))) * (id_rand(w.id, S + 16) > 0.72)
    col = mix(col, '#aba599', vein * 0.45)
    # worn tops are slightly lighter and smoother
    wear = smoothstep(0.55, 1.0, prof * dome)
    col = col * (1.0 + 0.07 * wear)[..., None]
    dcol = ramp(norm01(dirt_n + 0.4 * gr), [(0, '#4a3d2e'), (0.5, '#63523d'), (1, '#7d6a50')])
    dcol = mix(dcol, '#8d8272', grit * 0.7)
    alb = mix(dcol, col, sm)
    ao = ao_from_height(H, (3.0, 9.0, 22.0), 1.0)
    alb = alb * (0.76 + 0.24 * ao)[..., None]
    # dirt film creeping up the stone flanks
    flank = sm * (1 - smoothstep(0.25, 0.75, prof))
    alb = mix(alb, dcol * 1.1, flank * 0.55)
    # tufts of moss in a few gaps
    moss = (1 - sm) * smoothstep(0.30, 0.55, fbm(n, 6, 3, S + 17) + 0.2 * fbm(n, 40, 2, S + 18))
    alb = mix(alb, ramp(norm01(fbm(n, 36, 2, S + 19)), [(0, '#3f4a29'), (1, '#667038')]), moss * 0.8)
    H = H + moss * 1.5
    alb = balance(alb, 0.25, 0.7)

    rough = 0.74 + id_randn(w.id, S + 20, 0.04) - 0.16 * wear + 0.05 * mott
    rough = lerp(0.95, rough, sm)
    rough = lerp(rough, 0.95, moss)
    save_tex('cobble', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.8))


# ============================================================================= plaster
def plaster():
    n, S = N, 611
    gr = grain_noise(n, S + 1)
    und = fbm(n, 3, 3, S + 2) * 3.0 + fbm(n, 9, 3, S + 3) * 1.4
    tro = spectral(n, S + 4, beta=1.2, lo=5, hi=70, sx=3.5, sy=1.0) * 0.60         # trowel drag, along x
    tro2 = spectral(n, S + 41, beta=1.0, lo=8, hi=70, sx=1.0, sy=3.0) * 0.30
    H = 8.0 + und + tro + tro2 + gr * 0.17 - speckle(n, S + 5, 0.0015, 1.2) * 1.2
    # cracks: sparse network (big) + hairlines
    xw, yw = warped_grid(n, 30, 5, S + 6, 3)
    w1 = worley(n, 4, seed=S + 7, jitter=0.95, x=xw, y=yw)
    e1 = w1.edge * (n / 4)
    crack1 = (1 - smoothstep(0.5, 1.7, e1)) * smoothstep(0.0, 0.25, fbm(n, 3, 2, S + 8) + 0.12)
    xw2, yw2 = warped_grid(n, 16, 9, S + 9, 2)
    w2 = worley(n, 10, seed=S + 10, jitter=0.95, x=xw2, y=yw2)
    e2 = w2.edge * (n / 10)
    crack2 = (1 - smoothstep(0.3, 1.1, e2)) * smoothstep(0.05, 0.4, fbm(n, 4, 2, S + 11)) * 0.6
    crack = np.maximum(crack1, crack2)
    H = H - crack * 2.6
    # flaked patches revealing the daub
    pf = fbm(n, 4, 2, S + 12) + 0.30 * fbm(n, 13, 3, S + 13) + 0.10 * fbm(n, 45, 2, S + 14) + 0.10 * crack1
    thr = np.percentile(pf, 96.3)
    flake = smoothstep(thr, thr + 0.015, pf)
    rim = smoothstep(thr - 0.09, thr, pf) * (1 - flake)
    zb = ZBuf(n, 2)
    r = rng(S + 15)
    M = 2600
    strokes(zb, r.uniform(0, n, M), r.uniform(0, n, M), r.uniform(0, TAU, M), r.uniform(12, 40, M),
            r.uniform(0.8, 1.3, M), curve=r.normal(0, 0.12, M), h0=0.6, h1=1.0, taper=0.2, relief=0.4)
    straw = zb.height(0.0)
    daub_n = fbm(n, 14, 4, S + 16)
    Hd = 3.0 + daub_n * 2.2 + gr * 0.55 + straw * 1.5 - speckle(n, S + 17, 0.01, 1.4) * 1.5
    H = lerp(H + rim * 0.9, Hd, flake)

    # ---- albedo
    base_t = norm01(fbm(n, 4, 4, S + 18) * 0.7 + und / 6.0 + 0.10 * gr)
    alb = ramp(base_t, [(0, '#cbc4b2'), (0.5, '#d9d3c3'), (1, '#e4dfd1')])
    yel = smoothstep(0.0, 0.7, fbm(n, 2, 3, S + 19) + 0.3 * fbm(n, 9, 3, S + 20))
    alb = mix(alb, '#c2b594', yel * 0.30)
    damp = smoothstep(0.15, 0.75, fbm(n, 3, 4, S + 21))
    alb = mix(alb, '#a9a595', damp * 0.28)
    st = spectral(n, S + 22, beta=1.0, lo=7, hi=180, sx=1.0, sy=13.0) * smoothstep(-0.3, 0.4, fbm(n, 3, 2, S + 23))
    alb = mix(alb, '#8f8777', sat(st * 0.5 - 0.15) * 0.30)
    alb = mix(alb, '#ebe7dc', sat(-st * 0.5 - 0.5) * 0.25)
    # brush marks of the limewash
    alb = alb * (1.0 + 0.022 * tro + 0.015 * gr)[..., None]
    alb = mix(alb, '#6d6455', sat(crack * 1.2) * 0.80)
    alb = mix(alb, alb * 0.90, rim * 0.6)
    dcol = ramp(norm01(daub_n + 0.3 * gr), [(0, '#8a7861'), (0.5, '#a08d74'), (1, '#b3a188')])
    dcol = mix(dcol, '#c2b18b', sat(straw * 1.3) * 0.65)
    alb = mix(alb, dcol, flake)
    ao = ao_from_height(H, (2.0, 6.0, 16.0), 1.0)
    alb = alb * (0.84 + 0.16 * ao)[..., None]
    alb = balance(alb, 0.25, 0.75)

    rough = 0.84 + 0.04 * base_t + 0.05 * damp - 0.03 * tro
    rough = lerp(rough, 0.96, np.maximum(flake, sat(crack)))
    save_tex('plaster', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.8))


# ============================================================================= wood_planks
def wood_planks():
    n, S = N, 333
    x, y = grid(n)
    r = rng(S)
    nb = 8
    ws = 1.0 + (r.random(nb) - 0.5) * 0.18
    ws /= ws.sum()
    ce = np.concatenate([[0.0], np.cumsum(ws)])
    ce[-1] = 1.0 + 1e-6
    xx = np.mod(x + perlin(n, 2, 3, S + 1) * 1.6 / n, 1.0)
    bid = np.clip(np.searchsorted(ce, xx, side='right') - 1, 0, nb - 1)
    wb = ws[bid].astype(F)
    ub = ((xx - ce[bid]) / wb).astype(F)
    xl = ub * wb * n                                             # px across the board
    a = np.minimum(ub, 1 - ub) * wb * n                          # px to the board edge

    # butt joints: boards are made of 1 or 2 lengths
    has = np.zeros(nb, bool)
    has[r.choice(nb, 3, replace=False)] = True
    y1 = r.random(nb)
    ln = r.uniform(0.36, 0.64, nb)
    rel = np.mod(y - y1[bid], 1.0)
    seg = (has[bid] & (rel < ln[bid])).astype(np.int32)
    sid = bid * 2 + seg
    dj = np.minimum(np.abs(wrapd(y - y1[bid])), np.abs(wrapd(y - y1[bid] - ln[bid]))) * n
    dj = np.where(has[bid], dj, 1e3).astype(F)

    # ---- grain: ring field with per-length offsets, bent around knots
    ox = id_rand(sid, S + 2, 0, 1)
    oy = id_rand(sid, S + 3, 0, 1)
    fr = id_rand(sid, S + 4, 1 / 11.0, 1 / 6.0)
    mea = perlin(n, 5, 2, S + 5, x=x * 1.0 + ox, y=y + oy) + 0.4 * perlin(n, 11, 4, S + 6, x=x + ox, y=y + oy)
    g = xl * fr + mea * id_rand(sid, S + 7, 5.0, 12.0)
    knot = np.zeros((n, n), F)
    knot_ring = np.zeros((n, n), F)
    nk = 11
    kb = r.integers(0, nb, nk)
    kx = r.uniform(0.22, 0.78, nk)
    ky = r.random(nk)
    kr = r.uniform(5.5, 12.0, nk)
    for i in range(nk):
        m = bid == kb[i]
        dxk = (ub - kx[i]) * wb * n
        dyk = wrapd(y - ky[i]) * n
        # keep knots away from the butt joints
        rr2 = dxk * dxk + (dyk / 2.4) ** 2
        g = g + np.where(m, 5.5 * np.exp(-rr2 / (2 * (kr[i] * 1.9) ** 2)), 0.0)
        rk = np.sqrt(dxk * dxk + (dyk / 1.25) ** 2) / kr[i]
        core = np.where(m, 1 - smoothstep(0.75, 1.05, rk), 0.0)
        knot = np.maximum(knot, core)
        knot_ring = np.where(core > 0, rk, knot_ring)
    f = g - np.floor(g)
    late = smoothstep(0.45, 0.90, f) * (1 - smoothstep(0.90, 1.0, f))
    fib = spectral(n, S + 8, beta=0.5, lo=30, sx=1.0, sy=26.0)
    fib = warp(fib, ox * n, oy * n)
    ckn = spectral(n, S + 9, beta=0.7, lo=10, hi=300, sx=1.0, sy=44.0)
    ckn = warp(ckn, ox * n * 3, oy * n)
    check = smoothstep(2.05, 2.35, ckn) * (1 - knot)
    kring = np.sin(knot_ring * 16.0) * knot

    # ---- height
    board_z = id_randn(bid * 2 + seg, S + 10, 1.0)
    cup = id_randn(sid, S + 11, 1.0) * (ub - 0.5) ** 2 * 4.0 + id_randn(sid, S + 12, 0.8) * (ub - 0.5)
    edge_w = 2.2 + fbm(n, 30, 2, S + 13, fy=6) * 1.0
    d = a - edge_w
    dz = np.minimum(d, dj - 1.4)
    t = sat(dz / 4.5)
    prof = 1 - (1 - t) ** 2
    surf = 12.0 + board_z + cup + late * 0.9 + fib * 0.42 - check * 3.2 + knot * (0.8 + 0.5 * kring) \
        + fbm(n, 6, 3, S + 14, fy=2) * 0.8
    H = prof * surf
    gapm = 1 - smoothstep(-0.5, 1.5, dz)

    # ---- nails near the butt joints
    nxs, nys = [], []
    for bi in range(nb):
        if not has[bi]:
            continue
        for yj in (y1[bi], y1[bi] + ln[bi]):
            for sgn in (-1, 1):
                for uf in (0.27, 0.73):
                    nxs.append((ce[bi] + (uf + r.normal(0, 0.05)) * ws[bi]) * n)
                    nys.append((yj * n + sgn * (13 + r.uniform(-2, 4))) % n)
    nxs = np.array(nxs)
    nys = np.array(nys)
    nd, nid = dots(n, nxs, nys, 4.6)
    nail = 1 - smoothstep(0.75, 1.0, nd)
    naild = np.sqrt(np.maximum(1 - nd * nd, 0))
    H = np.where(nail > 0, lerp(H, 12.0 + board_z + 0.3 + naild * 1.5, nail), H)
    hd, _ = dots(n, nxs, nys + 5.0, 13.0)
    halo = (1 - hd) ** 1.5 * (1 - nail)

    # ---- albedo
    pal = ['#75624d', '#7d6a55', '#6f5d4a', '#82705c', '#746354', '#86745f', '#7a6a58', '#6d5e4e']
    col = palette_pick(sid, pal, S + 15)
    col = col * (1.0 + id_randn(sid, S + 16, 0.05))[..., None]
    col = col * (1.0 - 0.26 * late + 0.045 * fib)[..., None]
    wth = smoothstep(-0.1, 0.6, fbm(n, 3, 4, S + 17, fy=1) + 0.3 * spectral(n, S + 18, 1.2, 4, 80, 1.0, 9.0) * 0.36)
    col = mix(col, luma(col)[..., None] * hexc('#a49f96') / 0.5, wth * 0.42)       # silver-grey weathering
    stain = sat(spectral(n, S + 19, beta=1.4, lo=3, hi=90, sx=1.0, sy=12.0) * 0.5 - 0.25)
    col = mix(col, '#4c4034', stain * 0.45)
    col = mix(col, '#46362a', knot * (0.72 + 0.12 * kring))
    col = mix(col, '#3a2f26', check * 0.8)
    col = mix(col, '#6b4a33', halo * 0.42)                                          # rust bleed
    ncol = ramp(norm01(fbm(n, 60, 2, S + 20)), [(0, '#3b3632'), (1, '#57483c')])
    col = mix(col, ncol, nail)
    gapc = hexc('#2a231d')
    alb = mix(col, gapc, gapm)
    ao = ao_from_height(H, (2.0, 5.0, 12.0), 1.0)
    alb = alb * (0.80 + 0.20 * ao)[..., None]
    alb = balance(alb, 0.25, 0.6)

    rough = 0.82 + 0.06 * wth - 0.10 * knot + 0.05 * fib * 0.3 - 0.05 * late
    rough = lerp(rough, 0.55, nail)
    rough = lerp(rough, 0.95, gapm)
    save_tex('wood_planks', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.8))


# ============================================================================= roof_tiles
def roof_tiles():
    n, S = N, 555
    x, y = grid(n)
    nr, nc = 16, 12
    r = rng(S)
    rows = []
    for i in range(nr):
        ws = 1.0 + (r.random(nc) - 0.5) * 0.20
        ws /= ws.sum()
        off = ((0.5 / nc if i % 2 else 0.0) + r.normal(0, 0.008)) % 1.0
        rows.append((1.0 / nr, ws, off, np.zeros(nc)))
    yy = y + fbm(n, 5, 2, S + 1) * 2.2 / n
    cA = courses(x, yy, rows)
    cB = courses(x, yy - 1.0 / nr, rows)                      # the tile one row up, at the same x
    rh = n / nr
    yv = cA.v * rh
    hang = id_rand(cB.id, S + 2, 0.0, 13.0)
    aB = np.minimum(cB.u, 1 - cB.u) * cB.w * n
    cr = id_rand(cB.id, S + 3, 2.0, 9.0)
    corner = np.where(aB < cr, cr - np.sqrt(np.maximum(cr * cr - (cr - aB) ** 2, 0.0)), 0.0)
    chipn = fbm(n, 22, 3, S + 4)
    chip = sat((chipn - 0.28) * 3.0) * 14.0 * (id_rand(cB.id, S + 5) > 0.45)
    wavy = perlin(n, 40, 1, S + 6) * 1.2
    bound = hang - corner - chip + wavy
    gapB = id_rand(cB.id, S + 7, 1.0, 2.4)
    own = (yv >= bound) | (aB < gapB)
    tid = np.where(own, cA.id, cB.id + cA.count)
    u = np.where(own, cA.u, cB.u)
    w = np.where(own, cA.w, cB.w)
    wv = np.where(own, cA.v, 1.0 + cA.v)                      # 0 = top of the exposed part
    a = np.minimum(u, 1 - u) * w * n
    rid = np.where(own, cA.id, cB.id)                          # real tile id (same tile in both roles)

    gr = grain_noise(n, S + 8)
    thick = 8.5
    z = 0.5 + thick * wv
    z += (u - 0.5) * id_randn(rid, S + 9, 1.8)                # sideways tilt
    z += wv * id_randn(rid, S + 10, 1.3)                      # lifted / sunk tail
    z -= (u - 0.5) ** 2 * 4.0 * id_rand(rid, S + 11, -0.6, 1.6)   # camber
    z += fbm(n, 10, 4, S + 12) * 1.1 + gr * 0.26
    z += spectral(n, S + 13, beta=0.8, lo=20, hi=200, sx=1.0, sy=9.0) * 0.22     # moulding striations
    # side grooves between neighbours of the same row
    gapw = id_rand(rid, S + 14, 1.0, 2.4)
    side = smoothstep(gapw, gapw + 2.5, a)
    z = z - (1 - side) * 7.0
    # rounded lower arris of the overhanging tile
    dbot = np.where(own, 1e3, bound - yv)
    z = z - 2.6 * (1 - smoothstep(0.0, 3.0, dbot)) * (~own)
    # cracks on a few tiles
    cw = worley(n, 9, 14, S + 15, jitter=1.0, x=x + fbm(n, 12, 2, S + 16) * 8 / n, y=y)
    crack = (1 - smoothstep(0.012, 0.035, cw.edge)) * (id_rand(rid, S + 17) > 0.90) * side
    z = z - crack * 2.0
    H = np.maximum(z, -1.0)

    pal = ['#855a48', '#8c614c', '#7d5543', '#936a54', '#755648', '#836352', '#70574d', '#96694f', '#69564f',
           '#885f4c', '#7c6052']
    col = palette_pick(rid, pal, S + 18)
    col = col * (1.0 + id_randn(rid, S + 19, 0.06))[..., None]
    mott = fbm(n, 8, 4, S + 20)
    col = col * (1.0 + 0.10 * mott + 0.04 * gr)[..., None]
    # weathering: soot / algae darkening towards the lower exposed edge, paler dusty top
    wvv = np.where(own, cA.v, 1.0)
    weather = id_rand(rid, S + 21, 0.2, 1.0) * smoothstep(0.25, 1.0, wvv)
    col = mix(col, col * hexc('#6b5a50') / 0.40 * 0.80, weather * 0.40)
    col = mix(col, '#a58d7c', (1 - smoothstep(0.0, 0.5, wvv)) * 0.18)
    col = mix(col, '#3b2e28', (1 - side) * 0.85)
    col = mix(col, '#4a3a32', crack * 0.7)
    # lichen: pale yellow-grey crusts + a little moss along the grooves and under the laps
    lf = fbm(n, 5, 3, S + 22)
    lich = smoothstep(0.66, 0.80, fbm(n, 34, 3, S + 23, mode='billow') * 1.5 + 0.40 * lf) * smoothstep(0.0, 0.4, lf + 0.1)
    lcol = ramp(norm01(fbm(n, 40, 2, S + 24)), [(0, '#8f9070'), (0.5, '#a9a57c'), (1, '#b7b08a')])
    col = mix(col, lcol, lich * 0.65 * side)
    ao = ao_from_height(H, (2.0, 6.0, 14.0), 1.1)
    moss = sat((1 - ao) * 2.2) * smoothstep(0.1, 0.5, fbm(n, 6, 3, S + 25) + 0.2 * fbm(n, 40, 2, S + 26))
    col = mix(col, '#55602f', moss * 0.7)
    alb = col * (0.78 + 0.22 * ao)[..., None]
    alb = balance(alb, 0.25, 0.7)
    H = H + lich * 0.7 * side + moss * 0.8

    rough = 0.80 + id_randn(rid, S + 27, 0.04) + 0.05 * mott + 0.08 * lich
    rough = lerp(rough, 0.95, np.maximum(moss, 1 - side))
    save_tex('roof_tiles', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.8))


# ============================================================================= thatch
def thatch():
    n, S = N, 444
    r = rng(S)
    nl = 4
    LH = n / nl
    Zb = 22.0
    slope = Zb / LH
    rag = fbm(n, 5, 3, S + 1, exact=True)[0] * 26.0 + fbm(n, 24, 2, S + 2, exact=True)[0] * 16.0   # 1D, periodic in x
    loff = r.uniform(-10, 10, nl)
    zb = ZBuf(n, 2)

    def edge_y(xpx, k):
        return (k + 0.5) * LH + rag[np.mod(xpx.astype(int), n)] + loff[np.mod(k, nl)]

    # straws whose butt ends form the ragged lower edge of each layer
    M1 = 9500
    xt = r.uniform(0, n, M1)
    k = r.integers(0, nl, M1)
    up = np.minimum(r.exponential(26.0, M1), 120.0)
    yt = edge_y(xt, k) - up
    L = r.uniform(150, 300, M1)
    ang = math.pi / 2 + r.normal(0, 0.055, M1)
    h1 = Zb - up * slope + r.normal(0, 1.3, M1)
    wd = r.uniform(1.15, 1.95, M1)
    strokes(zb, xt - np.cos(ang) * L, yt - np.sin(ang) * L, ang, L, wd, curve=r.normal(0, 0.015, M1),
            h0=h1 - L * slope, h1=h1, taper=0.12, step=1.15, relief=1.7)
    # straws lying on the surface of the layers
    M2 = 5200
    xt2 = r.uniform(0, n, M2)
    yt2 = r.uniform(0, n, M2)
    ee = np.full(M2, 1e9)
    for kk in range(-1, nl + 1):
        dd = edge_y(xt2, kk) - yt2
        ee = np.where((dd >= 0) & (dd < ee), dd, ee)
    L2 = r.uniform(45, 150, M2)
    ang2 = math.pi / 2 + r.normal(0, 0.10, M2)
    h12 = Zb - ee * slope + r.normal(0.3, 1.1, M2)
    strokes(zb, xt2 - np.cos(ang2) * L2, yt2 - np.sin(ang2) * L2, ang2, L2, r.uniform(1.1, 1.8, M2),
            curve=r.normal(0, 0.03, M2), h0=h12 - L2 * slope, h1=h12, taper=0.15, step=1.15, relief=1.7,
            ids=np.arange(M1, M1 + M2, dtype=np.int32))
    x, y = grid(n)
    ypx = y * n
    e = np.full((n, n), 1e9, F)
    for kk in range(-1, nl + 1):
        dd = (kk + 0.5) * LH + rag[None, :] + loff[kk % nl] - ypx
        e = np.where((dd >= 0) & (dd < e), dd, e)
    zs = Zb - e * slope
    H = zb.height(-1e9)
    H = np.where(zb.mask(), np.maximum(H, zs - 5.0), zs - 4.0)
    ids = zb.ids()
    tt = zb.payload(0)
    ss = zb.payload(1)

    pal = ['#a08c5c', '#ad9865', '#8c7a50', '#b5a26f', '#7f6f4b', '#978658', '#a39468', '#8a7c58', '#b09a62']
    col = palette_pick(np.maximum(ids, 0), pal, S + 3)
    col = col * (1.0 + id_randn(np.maximum(ids, 0), S + 4, 0.07))[..., None]
    col = col * (0.92 + 0.08 * (1 - ss * ss))[..., None]
    # weathering: exposed lower part of each layer greys and darkens, cut ends are dark
    expo = smoothstep(120.0, 0.0, e)
    wth = smoothstep(-0.2, 0.5, fbm(n, 4, 3, S + 5))
    col = mix(col, luma(col)[..., None] * hexc('#8f887a') / 0.52, expo * wth * 0.45)
    col = mix(col, '#5a4d38', smoothstep(0.965, 1.0, tt) * 0.6)
    col = mix(col, '#4a3f2e', (~zb.mask()).astype(F) * 0.85)
    ao = ao_from_height(H, (2.0, 6.0, 20.0), 1.0)
    alb = col * (0.70 + 0.30 * ao)[..., None]
    moss = smoothstep(0.35, 0.65, fbm(n, 4, 3, S + 6) + 0.25 * fbm(n, 30, 2, S + 7)) * sat((1 - ao) * 2.0 + 0.15)
    alb = mix(alb, '#5c6236', moss * 0.55)
    alb = balance(alb, 0.25, 0.7)
    rough = 0.80 + 0.08 * expo * wth + id_randn(np.maximum(ids, 0), S + 8, 0.05) - 0.05 * (1 - ss * ss)
    rough = lerp(rough, 0.95, moss)
    save_tex('thatch', alb, H, rough, ao=ao, nscale=0.8, nblur=0.5, tile_m=TILE, height=norm01(H, 0.5, 99.8))


TABLE = {
    'stone_wall': stone_wall,
    'stone_brick': stone_brick,
    'cobble': cobble,
    'plaster': plaster,
    'wood_planks': wood_planks,
    'roof_tiles': roof_tiles,
    'thatch': thatch,
}

if __name__ == '__main__':
    run(TABLE)
