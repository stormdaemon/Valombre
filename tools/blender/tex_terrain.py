"""VALOMBRE terrain textures (1024 px, one tile = 4 m, ~3.9 mm per pixel):
terrain_grass, terrain_dirt, terrain_rock, terrain_sand, terrain_snow, terrain_forest, terrain_mud, terrain_ash.
Run:  blender -b --factory-startup -P tools/blender/tex_terrain.py -- [names...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex_lib import *

N = 1024
TILE = 4.0


def grain_noise(n, seed, lo=40, beta=0.6):
    return spectral(n, seed, beta=beta, lo=lo)


def speckle(n, seed, density, sigma=0.8):
    w = (white(n, seed) > (1.0 - density)).astype(F)
    s = blur(w, sigma)
    return sat(s * (2.0 * math.pi * sigma * sigma) * 1.3)


def cols_of(hexes):
    return np.stack([hexc(h) for h in hexes])


def interp_cols(t, pos, hexes):
    """Per-instance colors: t (M,) -> (M, 3) along a ramp."""
    c = cols_of(hexes)
    return np.stack([np.interp(t, pos, c[:, k]) for k in range(3)], -1).astype(F)


# ============================================================================= grass
def terrain_grass():
    n, S = N, 1001
    r = rng(S)
    dry_f = smoothstep(0.05, 0.60, fbm(n, 3, 3, S + 2) + 0.30 * fbm(n, 11, 2, S + 3))
    lush_f = smoothstep(-0.30, 0.50, fbm(n, 4, 3, S + 4))
    flow_f = fbm(n, 2, 2, S + 1, exact=True) * 2.4
    clov_f = fbm(n, 4, 3, S + 5) + 0.3 * fbm(n, 14, 2, S + 6)

    G = 54
    gi, gj = np.meshgrid(np.arange(G), np.arange(G))
    tx = ((gi + r.uniform(0.0, 1.0, (G, G))) * n / G).ravel()
    ty = ((gj + r.uniform(0.0, 1.0, (G, G))) * n / G).ravel()
    NT = G * G
    ts = r.uniform(0.70, 1.40, NT)
    ix = tx.astype(int) % n
    iy = ty.astype(int) % n
    t_dry, t_lush, t_flow = dry_f[iy, ix], lush_f[iy, ix], flow_f[iy, ix]
    lean = t_flow + r.normal(0, 0.5, NT)
    t_tone = r.normal(0, 0.13, NT)
    nb = r.integers(19, 30, NT)
    tid = np.repeat(np.arange(NT), nb)
    NB = len(tid)
    ra = r.uniform(0, TAU, NB)
    rr = np.abs(r.normal(0, 3.4, NB)) * ts[tid]
    bx = tx[tid] + np.cos(ra) * rr
    by = ty[tid] + np.sin(ra) * rr
    dxv = np.cos(ra) * 0.9 + np.cos(lean[tid]) * 0.75 + r.normal(0, 0.35, NB)
    dyv = np.sin(ra) * 0.9 + np.sin(lean[tid]) * 0.75 + r.normal(0, 0.35, NB)
    ang = np.arctan2(dyv, dxv)
    length = r.uniform(12, 31, NB) * ts[tid] * (0.85 + 0.30 * t_lush[tid])
    width = r.uniform(0.95, 1.42, NB)
    h1 = r.uniform(0.45, 1.0, NB) * (0.70 + 0.30 * ts[tid] / 1.4)
    h0 = r.uniform(0.02, 0.15, NB)
    zb = ZBuf(n, 2)
    strokes(zb, bx, by, ang, length, width, curve=r.normal(0, 0.22, NB), h0=h0, h1=h1, taper=0.78, step=0.7,
            relief=0.14)

    # per blade colors (root -> mid -> tip)
    g = np.clip(r.normal(0.5, 0.20, NB) + 0.24 * (t_lush[tid] - 0.5) + t_tone[tid], 0, 1)
    mid = interp_cols(g, [0, 0.5, 1], ['#6f8438', '#52702c', '#3c5c25'])
    tip = mid * 0.62 + hexc('#98a455')[None, :] * 0.38 + 0.03
    root = mid * 0.50
    isdry = r.random(NB) < (0.06 + 0.20 * t_dry[tid] ** 1.5)
    dmid = interp_cols(r.random(NB), [0, 1], ['#8f8352', '#a3965f'])
    mid = np.where(isdry[:, None], dmid, mid)
    tip = np.where(isdry[:, None], dmid * 1.13, tip)
    root = np.where(isdry[:, None], dmid * 0.62, root)

    # clover leaves in a few soft patches (three leaflets each)
    thr = np.percentile(clov_f, 86)
    MC = 2600
    cx = r.uniform(0, n, MC)
    cy = r.uniform(0, n, MC)
    keep = clov_f[cy.astype(int) % n, cx.astype(int) % n] > thr
    cx, cy = cx[keep], cy[keep]
    MC = len(cx)
    a0 = r.uniform(0, TAU, MC)
    lx, ly, la, lh = [], [], [], []
    csz = r.uniform(0.85, 1.25, MC)
    for k in range(3):
        aa = a0 + k * TAU / 3 + r.normal(0, 0.12, MC)
        lx.append(cx + np.cos(aa) * 3.7 * csz)
        ly.append(cy + np.sin(aa) * 3.7 * csz)
        la.append(aa)
        lh.append(r.uniform(0.72, 0.98, MC))
    lx, ly, la, lh = map(np.concatenate, (lx, ly, la, lh))
    csz3 = np.tile(csz, 3)
    blobs(n, lx, ly, 3.9 * csz3, 3.3 * csz3, la, S + 7, irr=0.06, hscale=lh, zb=zb, id0=NB, profile=0.35)

    Hn = zb.height(0.0)
    ids = zb.ids()
    p0 = zb.payload(0)
    p1 = zb.payload(1)
    isblade = (ids >= 0) & (ids < NB)
    isclov = ids >= NB
    bid = np.clip(ids, 0, NB - 1)
    t = p0
    c_lo = root[bid] + (mid[bid] - root[bid]) * sat(t * 2.0)[..., None]
    col = c_lo + (tip[bid] - mid[bid]) * sat(t * 2.0 - 1.0)[..., None]
    col = col * (0.90 + 0.10 * (1 - p1 * p1))[..., None]                  # midrib a bit lighter than the rims
    # clover: blue-green leaflets with the pale chevron
    cl = np.clip(ids - NB, 0, None)
    ccol = palette_pick(cl % max(MC, 1), ['#44682f', '#4c7334', '#3e5f2c', '#527a38'], S + 8)
    chev = np.exp(-((p0 - 0.05) / 0.22) ** 2) * (1 - sat(np.abs(p1) * 1.1) ** 2)
    ccol = ccol + chev[..., None] * 0.13
    col = np.where(isclov[..., None], ccol, col)
    soil = ramp(norm01(fbm(n, 30, 3, S + 9)), [(0, '#33321d'), (1, '#4a4529')])
    col = np.where((ids < 0)[..., None], soil, col)

    H = blur(Hn, 0.5) * 6.0
    ao = ao_from_height(H, (2.0, 5.0, 14.0), 1.0)
    alb = col * (0.70 + 0.30 * ao)[..., None]
    alb = balance(alb, 0.14, 0.8)
    rough = np.where(isblade, 0.70 - 0.10 * sat(t) + np.where(isdry[bid], 0.18, 0.0), 0.95)
    rough = np.where(isclov, 0.62, rough) + 0.04 * grain_noise(n, S + 10)
    save_tex('terrain_grass', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(blur(Hn, 1.0), 0.5, 99.5))


# ============================================================================= dirt
def terrain_dirt():
    n, S = N, 1101
    r = rng(S)
    gr = grain_noise(n, S)
    base = fbm(n, 3, 4, S + 1) * 5.0 + fbm(n, 11, 4, S + 2) * 2.4
    lumps = fbm(n, 26, 3, S + 3)
    clod = np.minimum(lumps, 0.12) * 4.0                              # packed: clods are flattened on top
    grit = speckle(n, S + 4, 0.035, 1.1)
    H = base + clod + gr * 0.40 + grit * 1.1
    # fine drying cracks (patchy)
    xw, yw = warped_grid(n, 18, 6, S + 5, 3)
    w1 = worley(n, 9, seed=S + 6, jitter=0.95, x=xw, y=yw)
    e1 = w1.edge * (n / 9)
    cm = smoothstep(-0.05, 0.35, fbm(n, 3, 3, S + 7))
    crack = (1 - smoothstep(0.25, 1.15, e1)) * cm
    xw2, yw2 = warped_grid(n, 8, 14, S + 8, 2)
    w2 = worley(n, 24, seed=S + 9, jitter=0.95, x=xw2, y=yw2)
    e2 = w2.edge * (n / 24)
    crack2 = (1 - smoothstep(0.3, 1.0, e2)) * smoothstep(0.1, 0.5, fbm(n, 4, 3, S + 10)) * 0.55
    crack = np.maximum(crack, crack2)
    H = H - crack * 2.4
    # embedded pebbles
    M = 2200
    rx = np.minimum(1.6 + r.exponential(2.2, M), 11.0)
    ry = rx * r.uniform(0.55, 1.0, M)
    zb = blobs(n, r.uniform(0, n, M), r.uniform(0, n, M), rx, ry, r.uniform(0, TAU, M), S + 11, irr=0.22,
               hscale=rx * 0.62, profile=0.5)
    ph = zb.height(0.0)
    pid = np.maximum(zb.ids(), 0)
    sink = id_rand(pid, S + 12, 0.25, 0.75) * rx.astype(F)[pid] * 0.62
    emerg = ph - sink
    pm = smoothstep(0.0, 0.9, emerg) * zb.mask()
    H = np.where(pm > 0, H + np.maximum(emerg, 0) * pm, H)

    t = norm01(base * 0.10 + lumps * 0.5 + gr * 0.10 + fbm(n, 9, 3, S + 13) * 0.45, 1, 99)
    alb = ramp(t, [(0, '#574433'), (0.35, '#6f5a45'), (0.7, '#866f55'), (1, '#9b856a')])
    alb = alb * (1.0 + 0.05 * gr)[..., None]
    alb = mix(alb, '#a39178', grit * 0.5)
    damp = smoothstep(0.2, 0.8, fbm(n, 3, 3, S + 14))
    alb = mix(alb, alb * 0.90, damp * 0.4)
    alb = mix(alb, '#45362a', sat(crack * 1.3) * 0.60)
    pcol = palette_pick(pid, ['#8d877c', '#9a9282', '#827c72', '#a39a86', '#8a7d6c', '#7b7770', '#aaa392', '#93876f'],
                        S + 15)
    pcol = pcol * (1.0 + id_randn(pid, S + 16, 0.07) + 0.05 * gr + 0.10 * (zb.payload(0) * 0.5))[..., None]
    alb = mix(alb, pcol, pm)
    ao = ao_from_height(H, (2.0, 6.0, 18.0), 1.0)
    alb = alb * (0.80 + 0.20 * ao)[..., None]
    alb = balance(alb, 0.13, 0.8)
    rough = 0.90 + 0.04 * lumps - 0.05 * damp
    rough = lerp(rough, 0.62 + id_randn(pid, S + 17, 0.06), pm)
    save_tex('terrain_dirt', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7))


# ============================================================================= rock
def terrain_rock():
    n, S = N, 1201
    x, y = grid(n)
    wx = fbm(n, 3, 3, S + 1) * 44 + fbm(n, 9, 3, S + 2) * 15
    wy = fbm(n, 2, 3, S + 3) * 38 + fbm(n, 10, 3, S + 4) * 10
    xw = x + wx / n
    yw = y + wy / n
    rows = random_rows(6, S, hvar=0.7, wmin=0.2, wmax=0.75, skew=0.7)
    c = courses(xw, yw, rows)
    c = split_cells(c, S + 5, prob_h=0.32, prob_v=0.15, min_h=0.10, min_w=0.25)
    a = c.a * n
    b = c.b * n
    d = np.minimum(a, b) + fbm(n, 18, 3, S + 6) * 3.5
    gr = grain_noise(n, S + 7)
    # blocks: strong level differences = ledges, tilted faces
    top = id_randn(c.id, S + 8, 6.5)
    top += (c.u - 0.5) * id_randn(c.id, S + 9, 9.0) + (c.v - 0.5) * id_randn(c.id, S + 10, 6.0)
    fis = id_rand(c.id, S + 11, 0.0, 1.0) ** 2.0
    fissure = (1 - smoothstep(0.0, 4.5, d)) * fis
    xw3, yw3 = warped_grid(n, 60, 3, S + 40, 3)
    w3 = worley(n, 3, seed=S + 41, jitter=1.0, x=xw3, y=yw3)
    long_crack = (1 - smoothstep(0.6, 2.4, w3.edge * (n / 3))) * smoothstep(-0.1, 0.3, fbm(n, 3, 2, S + 42))
    fissure = np.maximum(fissure, long_crack * 0.8)
    # secondary fracture facets inside the blocks
    fw = worley(n, 9, 13, seed=S + 12, jitter=0.95, x=xw, y=yw)
    fm = smoothstep(0.0, 0.18, fw.edge)
    facets = (fw.dx * id_randn(fw.id, S + 13, 1.0) + fw.dy * id_randn(fw.id, S + 14, 1.0)) * 4.5 * fm
    facets += id_randn(fw.id, S + 15, 1.6) * fm
    # laminations: thin strata ledges following the bedding
    lam_ph = yw * 34.0 + fbm(n, 4, 3, S + 16) * 2.5 + id_rand(c.id, S + 17, 0, 1)
    saw = lam_ph - np.floor(lam_ph)
    lam_amp = 0.5 + 1.6 * smoothstep(-0.2, 0.5, fbm(n, 5, 3, S + 18))
    lam = (smoothstep(0.0, 0.85, saw) - smoothstep(0.85, 1.0, saw)) * lam_amp
    streak = sample(spectral(n, S + 19, beta=0.9, lo=8, hi=220, sx=9.0, sy=1.0), xw * n, yw * n)
    erosion = fbm(n, 5, 5, S + 20) * 3.4
    pits = speckle(n, S + 21, 0.0012, 1.6)
    H = top + facets + lam + streak * 0.55 + erosion + gr * 0.32 - pits * 1.5 - fissure * 7.0
    H = blur(H, 0.8)

    # ---- albedo: grey with warm / cool beds
    bedt = norm01(perlin(n, 1, 6, S + 22, x=xw, y=yw) + 0.5 * perlin(n, 2, 15, S + 23, x=xw, y=yw))
    alb = ramp(bedt, [(0, '#77777a'), (0.3, '#8b8780'), (0.55, '#7f7c78'), (0.8, '#968c7c'), (1, '#84868a')])
    alb = alb * (1.0 + id_randn(c.id, S + 24, 0.06))[..., None]
    mott = fbm(n, 6, 5, S + 25)
    alb = alb * (1.0 + 0.12 * mott + 0.05 * streak + 0.035 * gr + 0.04 * (saw - 0.5) * lam_amp / 2.1)[..., None]
    alb = alb + (hexc('#a8906c') - hexc('#7f8890'))[None, None, :] * (fbm(n, 2, 3, S + 26) * 0.14)[..., None]
    # iron staining seeping from fissures
    rust = smoothstep(0.35, 0.8, fbm(n, 4, 4, S + 27) + 0.4 * fissure) * 0.30
    alb = mix(alb, '#8d6a4b', rust)
    ao = ao_from_height(H, (3.0, 9.0, 26.0), 1.0)
    alb = alb * (0.74 + 0.26 * ao)[..., None]
    alb = mix(alb, '#4a4540', sat(fissure * 1.2) * 0.50)
    # lichen: pale grey-green crusts and a few ochre ones, on exposed faces only
    lf = fbm(n, 4, 3, S + 28)
    lb = fbm(n, 30, 3, S + 29, mode='billow') * 1.6
    lich = smoothstep(0.64, 0.78, lb + 0.30 * lf) * smoothstep(0.0, 0.3, ao - 0.6)
    alb = mix(alb, ramp(norm01(fbm(n, 44, 2, S + 30)), [(0, '#8f947f'), (1, '#afb09b')]), lich * 0.75)
    lich2 = smoothstep(0.76, 0.86, fbm(n, 36, 3, S + 31, mode='billow') * 1.6 + 0.30 * fbm(n, 5, 2, S + 32))
    alb = mix(alb, '#9a8d5c', lich2 * 0.35)
    # moss in the damp fissures
    moss = sat(fissure * 1.5) * smoothstep(0.2, 0.55, fbm(n, 5, 3, S + 33))
    alb = mix(alb, '#56602f', moss * 0.6)
    # dust on the convex ledge edges
    alb = alb * (1.0 + 0.06 * np.clip(cavity(H, 5.0) / 2.5, -1, 1))[..., None]
    alb = balance(alb, 0.15, 0.8)
    rough = 0.82 + 0.06 * mott + 0.06 * lich - 0.04 * np.clip(cavity(H, 5.0) / 2.5, -1, 1)
    rough = lerp(rough, 0.95, moss)
    save_tex('terrain_rock', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7))


# ============================================================================= sand
def terrain_sand():
    n, S = N, 1301
    r = rng(S)
    gr = grain_noise(n, S, lo=60, beta=0.3)
    ph, env = ripples(n, S + 1, f0=27.0, bw_par=2.6, bw_perp=4.0, angle=math.pi / 2 + 0.10)
    rip = np.cos(ph + 0.55 * np.cos(ph)) * sat(env * 1.6)             # skewed: gentle windward, steep lee
    big = fbm(n, 2, 3, S + 2) * 3.0 + fbm(n, 6, 3, S + 3) * 1.6
    amp = 0.78 + 0.22 * smoothstep(-0.3, 0.4, fbm(n, 3, 2, S + 4))
    H = big + rip * 2.3 * amp + gr * 0.22
    # coarse grains gather in the troughs
    trough = sat(-rip * 0.6) * amp
    coarse = speckle(n, S + 5, 0.05, 0.9) * (0.25 + 0.75 * trough)
    H = H + coarse * 0.7
    # pebbles and shell fragments
    M = 230
    rx = np.minimum(1.8 + r.exponential(1.8, M), 8.0)
    zb = blobs(n, r.uniform(0, n, M), r.uniform(0, n, M), rx, rx * r.uniform(0.5, 1.0, M), r.uniform(0, TAU, M),
               S + 6, irr=0.2, hscale=rx * 0.55, profile=0.5)
    MS = 170
    sx_ = r.uniform(2.0, 4.6, MS)
    blobs(n, r.uniform(0, n, MS), r.uniform(0, n, MS), sx_, sx_ * r.uniform(0.35, 0.7, MS), r.uniform(0, TAU, MS),
          S + 7, irr=0.3, hscale=sx_ * 0.30, zb=zb, id0=M, profile=0.6)
    ph = zb.height(0.0)
    pid = np.maximum(zb.ids(), 0)
    pm = smoothstep(0.0, 0.7, ph - 0.5) * zb.mask()
    H = H + np.maximum(ph - 0.5, 0) * pm
    # scour hollow around pebbles
    H = H - blur(pm, 5.0) * 1.2 * (1 - pm)

    t = norm01(rip * 0.30 * amp + fbm(n, 5, 4, S + 8) * 0.9 + big * 0.03, 1, 99)
    alb = ramp(t, [(0, '#ab946e'), (0.4, '#bea780'), (0.75, '#cdb891'), (1, '#d8c7a2')])
    alb = alb * (1.0 + 0.045 * gr)[..., None]
    alb = mix(alb, '#8c7a5e', coarse * 0.45)
    dark_grain = speckle(n, S + 9, 0.012, 0.7)
    alb = mix(alb, '#5d5246', dark_grain * 0.5)
    damp = smoothstep(0.25, 0.8, fbm(n, 2, 3, S + 10))
    alb = mix(alb, alb * 0.93, damp * 0.5)
    pcol = palette_pick(pid, ['#8b857b', '#9c9484', '#787570', '#a69c88', '#6d6a68', '#93897a'], S + 11)
    scol = palette_pick(pid, ['#ddd5c4', '#d2c8b4', '#e2dccd', '#c9bba4', '#d9cdbb'], S + 12)
    pcol = np.where((pid >= M)[..., None], scol, pcol) * (1.0 + 0.05 * gr)[..., None]
    alb = mix(alb, pcol, pm)
    ao = ao_from_height(H, (2.0, 6.0, 16.0), 0.9)
    alb = alb * (0.86 + 0.14 * ao)[..., None]
    alb = balance(alb, 0.14, 0.85)
    sparkle = speckle(n, S + 13, 0.010, 0.6)
    rough = 0.90 + 0.04 * gr * 0.3 - 0.06 * damp - 0.45 * sparkle
    rough = lerp(rough, np.where(pid >= M, 0.45, 0.62), pm)
    save_tex('terrain_sand', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7))


# ============================================================================= snow
def terrain_snow():
    n, S = N, 1401
    gr = grain_noise(n, S, lo=60, beta=0.3)
    big = spectral(n, S + 1, beta=2.4, lo=1.5, hi=20, sx=1.5, sy=1.0) * 8.0          # soft drifts
    # sastrugi: wind-carved crust layers, elongated along the wind (x), with crisp little scarps
    s0 = spectral(n, S + 2, beta=1.7, lo=3, hi=110, sx=3.0, sy=1.0)
    s0 = warp(s0, s0 * 7.0, s0 * 0.0)                                              # steeper on the lee side
    terr = (smoothstep(-0.70, -0.46, s0) * 0.9 + smoothstep(0.04, 0.26, s0) * 1.2 + smoothstep(0.74, 0.98, s0) * 1.0
            + np.clip(s0, -1.5, 1.5) * 1.3)
    ph, env = ripples(n, S + 3, f0=50.0, bw_par=5.0, bw_perp=9.0, angle=0.06)      # fine ripples across the wind
    rmask = smoothstep(-0.1, 0.5, fbm(n, 3, 3, S + 4))
    rip = np.cos(ph + 0.5 * np.cos(ph)) * sat(env * 1.5) * 0.40 * rmask
    powder = fbm(n, 22, 3, S + 5) * 0.8 * (1 - rmask)
    H = big + terr + rip + powder + gr * 0.10
    hol = sat(-(H - blur(H, 26.0)) / 5.0)                                           # broad hollows
    hol2 = sat(-(H - blur(H, 5.0)) / 1.0)                                           # foot of the scarps
    t = sat(1.0 - hol * 0.75 - hol2 * 0.12 + fbm(n, 6, 3, S + 6) * 0.08)
    alb = ramp(t, [(0, '#bccadd'), (0.45, '#d0d9e4'), (0.8, '#dfe4e9'), (1, '#e6e8ea')])
    alb = alb * (1.0 + 0.010 * gr)[..., None]
    ao = ao_from_height(H, (3.0, 10.0, 28.0), 0.8)
    alb = alb * (0.93 + 0.07 * ao)[..., None]
    alb = balance(alb, 0.16, 0.8)
    crust = smoothstep(-0.2, 0.6, s0)
    sparkle = speckle(n, S + 8, 0.022, 0.6)
    rough = 0.62 - 0.17 * crust + 0.05 * gr * 0.4 + 0.10 * hol - 0.42 * sparkle
    save_tex('terrain_snow', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7),
             alb_range=(26, 236))


# ============================================================================= forest floor
def terrain_forest():
    n, S = N, 1501
    r = rng(S)
    gr = grain_noise(n, S)
    base = fbm(n, 3, 4, S + 1) * 4.5 + fbm(n, 14, 4, S + 2) * 2.0 + gr * 0.5
    zb = ZBuf(n, 2, base=-1e9)
    # needles (lowest litter layer)
    MN = 15000
    strokes(zb, r.uniform(0, n, MN), r.uniform(0, n, MN), r.uniform(0, TAU, MN), r.uniform(8, 19, MN),
            r.uniform(0.62, 0.9, MN), curve=r.normal(0, 0.06, MN), h0=r.uniform(0.6, 2.4, MN),
            h1=r.uniform(0.6, 2.4, MN), taper=0.3, relief=0.5)
    # dead leaves
    ML = 2500
    lcx, lcy = r.uniform(0, n, ML), r.uniform(0, n, ML)
    ln = r.uniform(7.5, 13.5, ML).astype(F)
    asp = r.uniform(0.42, 0.66, ML).astype(F)
    lang = r.uniform(0, TAU, ML).astype(F)
    lhs = r.uniform(1.8, 5.2, ML).astype(F)
    cu = r.normal(0, 0.9, ML).astype(F)
    cv = r.normal(0.4, 0.9, ML).astype(F)
    lobe = r.uniform(0.0, 0.22, ML).astype(F)
    lph = r.uniform(0, TAU, ML).astype(F)

    def leaf_fn(sel, dx, dy):
        e = lambda v: v[sel][:, None, None]
        ca, sa = np.cos(e(lang)), np.sin(e(lang))
        u = (dx * ca + dy * sa) / e(ln)
        v = (-dx * sa + dy * ca) / (e(ln) * e(asp))
        wdt = np.maximum(1 - u * u, 0) ** 0.7 * (1 - e(lobe) * (0.5 + 0.5 * np.cos(u * 9 + e(lph)))) * (1 - 0.22 * u)
        inside = np.abs(v) < wdt
        vv = v / np.maximum(wdt, 1e-3)
        h = e(lhs) + e(cu) * u * u * 1.2 + e(cv) * vv * vv + 0.35 * np.exp(-(vv / 0.14) ** 2) - 0.4 * vv ** 4
        return np.where(inside, h, -1e9).astype(F), [u, vv]

    stamp(zb, lcx, lcy, ln * 1.05, leaf_fn, ids=np.arange(MN, MN + ML, dtype=np.int32))
    # twigs
    MT = 240
    tl = r.uniform(30, 150, MT)
    strokes(zb, r.uniform(0, n, MT), r.uniform(0, n, MT), r.uniform(0, TAU, MT), tl, r.uniform(1.2, 2.7, MT),
            curve=r.normal(0, 0.07, MT), h0=r.uniform(3.5, 7.0, MT), h1=r.uniform(3.5, 7.0, MT), taper=0.45,
            relief=2.0, wave_amp=r.uniform(0, 2.0, MT), wave_freq=r.uniform(0.5, 2.0, MT),
            wave_phase=r.random(MT), ids=np.arange(MN + ML, MN + ML + MT, dtype=np.int32))
    ids = zb.ids()
    p0, p1 = zb.payload(0), zb.payload(1)
    lit_h = zb.height(0.0)
    has = ids >= 0
    isn = has & (ids < MN)
    isl = (ids >= MN) & (ids < MN + ML)
    ist = ids >= MN + ML
    H = base + np.where(has, lit_h, 0.0)

    soil = ramp(norm01(base + fbm(n, 30, 2, S + 3) * 1.5), [(0, '#261d15'), (0.5, '#35281d'), (1, '#493929')])
    nid = np.clip(ids, 0, MN - 1)
    ncol = palette_pick(nid, ['#6b4a30', '#7a5637', '#5a3f2b', '#86633f', '#4d3827', '#73573c'], S + 4)
    ncol = ncol * (1.0 + id_randn(nid, S + 5, 0.08))[..., None]
    lid = np.clip(ids - MN, 0, ML - 1)
    lcol = palette_pick(lid, ['#6e4b2c', '#7c5630', '#5b3f28', '#866234', '#684a33', '#8a6636', '#55402d',
                              '#7a5a3a', '#83512d', '#4a3a2b'], S + 6)
    lcol = lcol * (1.0 + id_randn(lid, S + 7, 0.09))[..., None]
    vein = np.exp(-(p1 / 0.10) ** 2) * 0.22 + 0.07 * (np.sin((p0 * 7.0 - np.abs(p1) * 2.2) * math.pi) > 0.82)
    lcol = lcol * (1.0 - vein - 0.16 * p1 * p1 + 0.08 * fbm(n, 24, 2, S + 8))[..., None]
    lcol = mix(lcol, '#2f251c', smoothstep(0.55, 0.75, fbm(n, 40, 2, S + 9, mode='billow') * 1.5) * 0.5)   # rot spots
    tid = np.clip(ids - MN - ML, 0, MT - 1)
    tcol = palette_pick(tid, ['#4a3a2d', '#57463a', '#3d3027', '#625244', '#6a5d51'], S + 10)
    tcol = tcol * (0.85 + 0.25 * (1 - p1 * p1) + 0.10 * fbm(n, 50, 2, S + 11))[..., None]
    col = soil
    col = np.where(isn[..., None], ncol, col)
    col = np.where(isl[..., None], lcol, col)
    col = np.where(ist[..., None], tcol, col)

    # moss cushions
    mf = fbm(n, 6, 3, S + 12) + 0.35 * fbm(n, 16, 3, S + 13) + 0.10 * fbm(n, 50, 2, S + 14)
    thr = np.percentile(mf, 87)
    moss = smoothstep(thr, thr + 0.16, mf) * (1 - ist * 0.8)
    mb = fbm(n, 28, 3, S + 15, mode='billow')
    mh = 2.5 + smoothstep(thr, thr + 0.5, mf) * 5.0 + mb * 3.2 + gr * 0.6
    H = lerp(H, base + mh, moss)
    mcol = ramp(norm01(mb + 0.25 * gr + fbm(n, 9, 2, S + 16) * 0.4), [(0, '#2b3619'), (0.45, '#3d4823'), (0.8, '#525c2c'),
                                                                 (1, '#666c36')])
    col = mix(col, mcol, moss)
    ao = ao_from_height(H, (2.0, 5.0, 14.0), 1.0)
    alb = col * (0.68 + 0.32 * ao)[..., None]
    alb = balance(alb, 0.14, 0.8)
    rough = np.where(isl, 0.78, np.where(ist, 0.86, np.where(isn, 0.82, 0.93))) + 0.04 * gr * 0.5
    rough = lerp(rough, 0.95, moss)
    save_tex('terrain_forest', alb, blur(H, 0.4), rough, ao=ao, nscale=1.0, tile_m=TILE,
             height=norm01(blur(H, 1.0), 0.5, 99.7))


# ============================================================================= mud
def terrain_mud():
    n, S = N, 1601
    r = rng(S)
    gr = grain_noise(n, S)
    big = spectral(n, S + 1, beta=2.1, lo=2.6, hi=40) * 5.0
    rid = fbm(n, 7, 4, S + 2, mode='ridged', exact=True)
    churn = fbm(n, 14, 3, S + 3, mode='billow', exact=True)
    H0 = big + rid * 5.0 + churn * 2.5 + fbm(n, 30, 3, S + 4) * 0.9
    wl = np.percentile(H0, 17)
    depth = wl - H0
    pud = smoothstep(-0.15, 0.35, depth)                              # 1 = standing water
    wet = smoothstep(5.5, 0.3, H0 - wl)                               # glistening wet band above the water line
    pores = speckle(n, S + 5, 0.006, 1.0)
    Hm = H0 + gr * 0.30 - pores * 1.0
    H = np.maximum(Hm, wl) * 1.0
    H = lerp(Hm, np.maximum(Hm, wl), 1.0)
    H = lerp(H, wl + 0.0 * H, pud)                                    # dead flat water
    # organic debris: bits of stalks / twigs and rotten leaf scraps, some floating
    zb = ZBuf(n, 2)
    MT = 230
    strokes(zb, r.uniform(0, n, MT), r.uniform(0, n, MT), r.uniform(0, TAU, MT), r.uniform(10, 55, MT),
            r.uniform(0.9, 2.0, MT), curve=r.normal(0, 0.08, MT), h0=1.6, h1=1.6, taper=0.3, relief=1.2)
    ML = 380
    lr = r.uniform(3.0, 7.5, ML)
    blobs(n, r.uniform(0, n, ML), r.uniform(0, n, ML), lr, lr * r.uniform(0.45, 0.8, ML), r.uniform(0, TAU, ML),
          S + 6, irr=0.35, hscale=0.9, zb=zb, id0=MT, profile=0.25)
    dh = zb.height(0.0)
    did = np.maximum(zb.ids(), 0)
    dm = zb.mask().astype(F)
    H = H + dh * dm

    t = norm01(H0 * 0.10 + fbm(n, 6, 4, S + 7) * 0.8 + gr * 0.08, 1, 99)
    alb = ramp(t, [(0, '#30271e'), (0.4, '#42362a'), (0.75, '#544434'), (1, '#65533f')])
    alb = alb * (1.0 + 0.04 * gr)[..., None]
    alb = mix(alb, alb * 0.72, wet * 0.8)                              # wet mud is darker
    water = ramp(sat(depth / 5.0), [(0, '#3d3427'), (0.4, '#302b20'), (1, '#27261c')])
    scum = smoothstep(0.55, 0.8, fbm(n, 9, 4, S + 8) + 0.3 * fbm(n, 40, 2, S + 9)) * 0.5
    water = mix(water, '#44452c', scum * 0.8)                               # algae film
    alb = mix(alb, water, pud)
    dcol = palette_pick(did, ['#4f4130', '#43372a', '#5d4d38', '#3a3025', '#544732', '#62533a'], S + 10)
    dcol = dcol * (0.9 + 0.2 * (1 - zb.payload(1) ** 2))[..., None]
    alb = mix(alb, dcol, dm * 0.92)
    ao = ao_from_height(H, (2.0, 6.0, 18.0), 0.9)
    ao = lerp(ao, np.maximum(ao, 0.95), pud * (1 - dm))
    alb = alb * (0.80 + 0.20 * ao)[..., None]
    alb = balance(alb, 0.16, 0.8)
    rough = 0.74 + 0.08 * gr * 0.4 + 0.06 * churn
    rough = lerp(rough, 0.30, wet * 0.85)
    rough = lerp(rough, 0.07 + 0.10 * scum, pud)
    rough = lerp(rough, 0.70, dm)
    hb = norm01(lerp(Hm, np.minimum(Hm, wl - 1.0), pud), 0.5, 99.7)
    save_tex('terrain_mud', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=hb, alb_range=(26, 235))


# ============================================================================= ash
def terrain_ash():
    n, S = N, 1701
    r = rng(S)
    gr = grain_noise(n, S)
    xw, yw = warped_grid(n, 24, 4, S + 1, 3)
    w = worley(n, 10, 10, S + 2, jitter=0.92, x=xw, y=yw)
    e = w.edge * (n / 10)
    gap = id_rand(w.id, S + 3, 0.6, 2.6) + fbm(n, 20, 2, S + 4) * 1.4
    xwb, ywb = warped_grid(n, 50, 3, S + 30, 3)
    wb = worley(n, 4, 4, S + 31, jitter=0.95, x=xwb, y=ywb)
    eb = wb.edge * (n / 4)
    gapb = 3.0 + 5.0 * smoothstep(-0.3, 0.4, fbm(n, 3, 2, S + 32)) + fbm(n, 16, 2, S + 33) * 2.5
    t = np.minimum(sat((e - gap) / 5.0), sat((eb - gapb) / 7.0))
    prof = 1 - (1 - t) ** 2
    top = 9.0 + id_randn(w.id, S + 5, 1.6) + w.dx * id_randn(w.id, S + 6, 3.0) + w.dy * id_randn(w.id, S + 7, 3.0)
    curl = (1 - smoothstep(0.0, 0.30, w.edge)) * id_rand(w.id, S + 8, 0.0, 3.0)      # plates curl up at the rims
    xw2, yw2 = warped_grid(n, 10, 9, S + 9, 2)
    w2 = worley(n, 24, 24, S + 10, jitter=0.95, x=xw2, y=yw2)
    e2 = w2.edge * (n / 24)
    sub = (1 - smoothstep(0.4, 1.8, e2)) * smoothstep(-0.1, 0.4, fbm(n, 4, 3, S + 11))
    crust = fbm(n, 14, 4, S + 12) * 2.2
    ves = speckle(n, S + 13, 0.012, 1.2)
    face = top + curl + crust + gr * 0.45 - ves * 1.6 - sub * 1.8
    Hs = prof * face
    Hc = 1.5 + fbm(n, 18, 3, S + 14) * 1.2 + gr * 0.2
    H = np.maximum(Hs, Hc)
    sm = smoothstep(0.0, 1.5, Hs - Hc)
    # cinders
    M = 1100
    rx = np.minimum(2.0 + r.exponential(2.2, M), 10.0)
    zb = blobs(n, r.uniform(0, n, M), r.uniform(0, n, M), rx, rx * r.uniform(0.6, 1.0, M), r.uniform(0, TAU, M),
               S + 15, irr=0.3, hscale=rx * 0.7, profile=0.45)
    ph = zb.height(0.0)
    pid = np.maximum(zb.ids(), 0)
    pm = zb.mask().astype(F) * smoothstep(0.0, 0.8, ph)
    ph = ph * (1.0 + 0.25 * fbm(n, 60, 2, S + 16)) - speckle(n, S + 17, 0.05, 0.9) * 0.9
    H = H + np.maximum(ph, 0) * pm
    # pale ash dust settles in the hollows and cracks, smoothing them
    low = sat(-(H - blur(H, 22.0)) / 4.5)
    dfield = fbm(n, 5, 3, S + 18) * 1.3 + fbm(n, 14, 2, S + 34) * 0.40
    dust = sat(low * 1.1 + (1 - sm) * 0.45 + dfield - 0.22) * (1 - pm)
    dust = smoothstep(0.25, 0.85, dust)
    H = lerp(H, blur(H, 3.0) + 0.8, dust * 0.75)

    ct = norm01(crust * 0.3 + fbm(n, 6, 4, S + 19) * 0.9 + gr * 0.12 + id_randn(w.id, S + 20, 0.25), 1, 99)
    alb = ramp(ct, [(0, '#292726'), (0.4, '#383635'), (0.75, '#4a4746'), (1, '#5c5856')])
    rust = smoothstep(0.30, 0.75, fbm(n, 5, 4, S + 21) + 0.3 * fbm(n, 22, 2, S + 22))
    alb = mix(alb, ramp(norm01(fbm(n, 30, 3, S + 23)), [(0, '#55332a'), (1, '#724633')]), rust * 0.45 * sm)
    ccol = palette_pick(pid, ['#2c2928', '#3a3534', '#262424', '#4b3229', '#342f2e', '#5f3a2b', '#444040'], S + 24)
    ccol = ccol * (1.0 + id_randn(pid, S + 25, 0.08) + 0.06 * gr)[..., None]
    alb = mix(alb, '#211f1e', (1 - sm) * 0.8)
    alb = mix(alb, ccol, pm)
    dcol = ramp(norm01(fbm(n, 12, 4, S + 26) + 0.2 * gr), [(0, '#6c6863'), (0.5, '#807c76'), (1, '#96928b')])
    alb = mix(alb, dcol, dust * 0.85)
    ao = ao_from_height(H, (2.0, 6.0, 18.0), 1.0)
    alb = alb * (0.78 + 0.22 * ao)[..., None]
    alb = balance(alb, 0.15, 0.8)
    rough = 0.88 + 0.05 * gr * 0.4 - 0.10 * rust * sm
    rough = lerp(rough, 0.58 + id_randn(pid, S + 27, 0.10), pm)
    rough = lerp(rough, 0.97, dust)
    save_tex('terrain_ash', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7),
             alb_range=(26, 235))


TABLE = {
    'terrain_grass': terrain_grass,
    'terrain_dirt': terrain_dirt,
    'terrain_rock': terrain_rock,
    'terrain_sand': terrain_sand,
    'terrain_snow': terrain_snow,
    'terrain_forest': terrain_forest,
    'terrain_mud': terrain_mud,
    'terrain_ash': terrain_ash,
}

if __name__ == '__main__':
    run(TABLE)
