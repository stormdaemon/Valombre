"""VALOMBRE bark textures (512 px, one tile = 1 m, u wraps around the trunk, v = height):
bark_oak, bark_pine, bark_birch.
Run:  blender -b --factory-startup -P tools/blender/tex_bark.py -- [names...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex_lib import *

N = 512
TILE = 1.0


def grain_noise(n, seed, lo=40, beta=0.6):
    return spectral(n, seed, beta=beta, lo=lo)


def speckle(n, seed, density, sigma=0.8):
    w = (white(n, seed) > (1.0 - density)).astype(F)
    s = blur(w, sigma)
    return sat(s * (2.0 * math.pi * sigma * sigma) * 1.3)


def hash2(a, b):
    """Cheap deterministic 0..1 hash of two integer arrays."""
    v = np.sin(a.astype(np.float64) * 12.9898 + b.astype(np.float64) * 78.233) * 43758.5453
    return (v - np.floor(v)).astype(F)


# ============================================================================= oak
def bark_oak():
    n, S = N, 2001
    x, y = grid(n)
    wx = perlin(n, 3, 3, S + 1) * 20 + perlin(n, 7, 6, S + 2) * 9
    wy = perlin(n, 4, 3, S + 3) * 10
    xw = x + wx / n
    yw = y + wy / n
    kx, ky = 13, 2
    w = worley(n, kx, ky, S + 4, jitter=0.90, x=xw, y=yw, hexa=True)
    e = w.edge * (n / kx)
    gr = grain_noise(n, S + 5)
    gap = id_rand(w.id, S + 6, 0.8, 3.2) + fbm(n, 14, 2, S + 7) * 1.6
    t = sat((e - gap) / id_rand(w.id, S + 8, 7.0, 13.0))
    prof = 1 - (1 - t) ** 1.6
    top = 13.0 + id_randn(w.id, S + 9, 2.2)
    # ridges are broken into blocks by cross cracks
    K = np.round(id_rand(w.id, S + 10, 5, 11)).astype(np.int32)
    cph = yw * K + id_rand(w.id, S + 11, 0, 1) + fbm(n, 6, 2, S + 12) * 0.7
    cl = np.floor(cph)
    cf = cph - cl
    cross = (1 - smoothstep(0.0, 0.11, np.minimum(cf, 1 - cf))) * (id_rand(w.id, S + 13) > 0.15)
    blk = hash2(w.id, np.mod(cl, K).astype(np.int32))
    fib = spectral(n, S + 14, beta=0.9, lo=12, hi=200, sx=1.0, sy=10.0)
    fib2 = spectral(n, S + 15, beta=0.6, lo=40, hi=250, sx=1.0, sy=6.0)
    face = top + (blk - 0.5) * 3.4 + fib * 1.5 + fib2 * 0.5 - cross * 3.4 + fbm(n, 18, 3, S + 16) * 1.3 + gr * 0.35
    Hr = prof * face
    Hf = 1.0 + fbm(n, 16, 3, S + 17) * 1.2 + fib * 0.6
    H = np.maximum(Hr, Hf)
    sm = smoothstep(0.0, 1.5, Hr - Hf)

    tc = norm01(prof * 0.55 + (blk - 0.5) * 0.35 + fib * 0.10 + fbm(n, 8, 3, S + 18) * 0.5 + gr * 0.04, 1, 99)
    col = ramp(tc, [(0, '#3a3029'), (0.3, '#51463c'), (0.6, '#696057'), (0.85, '#7d766c'), (1, '#8c867c')])
    col = col * (1.0 + 0.07 * fib + 0.03 * gr)[..., None]
    col = mix(col, '#3a2e24', sat(cross * 1.2) * 0.6)
    fcol = ramp(norm01(fbm(n, 12, 3, S + 19) + fib * 0.2), [(0, '#241f1b'), (0.6, '#332b25'), (1, '#43372d')])
    alb = mix(fcol, col, sm)
    ao = ao_from_height(H, (2.0, 5.0, 12.0), 1.0)
    alb = alb * (0.74 + 0.26 * ao)[..., None]
    # grey-green algae film and pale lichen on some ridges
    alg = smoothstep(0.1, 0.6, fbm(n, 3, 3, S + 20) + 0.2 * fbm(n, 20, 2, S + 21)) * sm
    alb = mix(alb, alb * hexc('#8c9474') / 0.55, alg * 0.28)
    lich = smoothstep(0.66, 0.80, fbm(n, 22, 3, S + 22, mode='billow') * 1.6 + 0.3 * fbm(n, 4, 2, S + 23)) * sm * prof
    alb = mix(alb, '#a3a48d', lich * 0.6)
    alb = balance(alb, 0.2, 0.7)
    rough = 0.90 - 0.06 * prof * sm + 0.03 * gr * 0.5 + 0.04 * lich
    save_tex('bark_oak', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7))


# ============================================================================= pine
def bark_pine():
    n, S = N, 2101
    x, y = grid(n)
    wx = perlin(n, 3, 2, S + 1) * 13 + fbm(n, 9, 2, S + 2) * 5
    wy = perlin(n, 3, 3, S + 3) * 12
    xw = x + wx / n
    yw = y + wy / n
    kx, ky = 8, 4
    w = worley(n, kx, ky, S + 4, jitter=0.85, x=xw, y=yw, hexa=True)
    e = w.edge * (n / kx)
    gr = grain_noise(n, S + 5)
    en = e + fbm(n, 9, 3, S + 6) * 5.5 + fbm(n, 28, 2, S + 7) * 2.2
    gap = id_rand(w.id, S + 8, 1.8, 4.2)
    d = en - gap
    lay = d / id_rand(w.id, S + 9, 6.5, 10.5)
    cap = np.floor(id_rand(w.id, S + 10, 2.0, 4.99))
    lev = np.clip(np.floor(lay), 0, cap)
    fr = np.where(np.floor(lay) > cap, 1.0, lay - np.floor(lay))
    step = smoothstep(0.0, 0.16, fr)
    inside = smoothstep(-1.0, 0.6, d)
    lh = hash2(w.id, lev.astype(np.int32))
    fib = spectral(n, S + 11, beta=0.8, lo=14, hi=220, sx=1.0, sy=7.0)
    flake = fbm(n, 24, 3, S + 12)
    plate = 5.0 + (lev + step) * 2.0 + (lh - 0.5) * 1.0
    plate += w.dx * id_randn(w.id, S + 13, 1.6) + w.dy * id_randn(w.id, S + 14, 1.2)
    plate += fib * 0.55 + flake * 0.8 + gr * 0.3 - speckle(n, S + 15, 0.004, 1.2) * 1.2
    Hf = 0.8 + fbm(n, 14, 3, S + 16) * 1.0 + fib * 0.4
    H = lerp(Hf, np.maximum(plate, Hf), inside)

    # colour per flake layer: outer flakes weathered grey-violet, inner ones fresh cinnamon / orange-brown
    lt = sat(lev / 4.0 + (lh - 0.5) * 0.45 + id_randn(w.id, S + 17, 0.10) + flake * 0.10)
    col = ramp(lt, [(0, '#64564f'), (0.25, '#735c50'), (0.5, '#815c46'), (0.75, '#8e6244'), (1, '#996b49')])
    col = col * (1.0 + 0.06 * fib + 0.05 * flake + 0.03 * gr)[..., None]
    rim = (1 - smoothstep(0.0, 0.30, fr)) * (lev > 0)
    col = mix(col, col * 1.16, rim * 0.5)                               # curled pale rim of each flake
    col = mix(col, '#55463f', smoothstep(0.80, 1.0, fr) * (np.floor(lay) < cap) * 0.45)   # shadowed foot of the next step
    grey = smoothstep(0.2, 0.7, fbm(n, 4, 3, S + 18) + 0.25 * fbm(n, 18, 2, S + 19))
    col = mix(col, luma(col)[..., None] * hexc('#93898a') / 0.50, grey * 0.35)
    fcol = ramp(norm01(fbm(n, 12, 3, S + 20)), [(0, '#231914'), (0.6, '#33231b'), (1, '#472d20')])
    alb = mix(fcol, col, inside)
    ao = ao_from_height(H, (2.0, 5.0, 12.0), 1.0)
    alb = alb * (0.74 + 0.26 * ao)[..., None]
    lich = smoothstep(0.70, 0.82, fbm(n, 24, 3, S + 21, mode='billow') * 1.6 + 0.3 * fbm(n, 4, 2, S + 22)) * inside
    alb = mix(alb, '#8d927c', lich * 0.3)
    alb = balance(alb, 0.2, 0.7)
    rough = 0.86 + 0.05 * flake - 0.06 * sat(lev / 4.0) + 0.04 * grey
    rough = lerp(0.95, rough, inside)
    save_tex('bark_pine', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7))


# ============================================================================= birch
def bark_birch():
    n, S = N, 2201
    r = rng(S)
    x, y = grid(n)
    gr = grain_noise(n, S + 1)
    und = fbm(n, 3, 3, S + 2) * 1.6
    band = spectral(n, S + 3, beta=1.0, lo=5, hi=200, sx=9.0, sy=1.0)          # horizontal paper streaks
    band2 = spectral(n, S + 4, beta=0.6, lo=30, hi=250, sx=14.0, sy=1.0)
    H = 6.0 + und + band * 0.35 + band2 * 0.18 + gr * 0.10
    # peeling paper: thin layers ending in horizontal curled edges
    pl = spectral(n, S + 5, beta=1.6, lo=3, hi=60, sx=4.0, sy=1.0)
    peel1 = smoothstep(0.55, 0.62, pl)
    peel2 = smoothstep(-0.75, -0.68, pl)
    lip = np.exp(-((pl - 0.64) / 0.05) ** 2) + np.exp(-((pl + 0.66) / 0.05) ** 2)
    H = H + peel1 * 0.9 - peel2 * 0.8 + lip * 0.9
    # lenticels: dark horizontal dashes
    zb = ZBuf(n, 2)
    ML = 420
    ll = np.minimum(5.0 + r.exponential(11.0, ML), 46.0)
    strokes(zb, r.uniform(0, n, ML), r.uniform(0, n, ML), r.normal(0, 0.05, ML), ll, r.uniform(0.8, 1.9, ML),
            curve=r.normal(0, 0.03, ML), h0=1.0, h1=1.0, taper=0.0, relief=0.7)
    lm = blur(zb.mask().astype(F), 0.7)
    lent = sat(lm * 1.4)
    lt = zb.payload(0)
    lent = lent * sat(np.sin(lt * math.pi) * 2.5 + 0.3)                          # pointed ends
    H = H + lent * (0.9 + 0.5 * gr)
    # black scars: rough dark lenses with "eyebrow" whiskers running down on both sides
    MS = 6
    gx = (np.arange(MS) + r.uniform(0.2, 0.8, MS)) / MS
    sx_ = (gx * n + r.uniform(-20, 20, MS)) % n
    sy_ = r.permutation(MS) / MS * n + r.uniform(0, n / MS, MS)
    srx = r.uniform(8, 16, MS)
    sry = srx * r.uniform(0.38, 0.6, MS)
    zs = blobs(n, sx_, sy_, srx, sry, r.normal(0, 0.08, MS), S + 6, irr=0.25, hscale=1.0, profile=0.5)
    zw = ZBuf(n, 2)
    wx0, wy0, wa, wl = [], [], [], []
    for i in range(MS):
        for sgn in (-1, 1):
            wx0.append(sx_[i] + sgn * srx[i] * 0.75)
            wy0.append(sy_[i])
            wa.append(math.pi / 2 - sgn * r.uniform(0.75, 1.05))
            wl.append(srx[i] * r.uniform(0.9, 1.6))
    strokes(zw, np.array(wx0), np.array(wy0), np.array(wa), np.array(wl), 1.7, curve=0.0, h0=0.8, h1=0.2,
            taper=0.85, relief=0.5)
    # a few vertical splits with dark, corky lips
    MC = 5
    cxs = r.uniform(0, n, MC)
    cys = r.uniform(0, n, MC)
    crx = r.uniform(1.6, 3.0, MC)
    zc = blobs(n, cxs, cys, crx, crx * r.uniform(3.0, 6.0, MC), r.normal(0, 0.06, MC), S + 7, irr=0.25, hscale=1.0,
               profile=0.6)
    scar = np.maximum(np.maximum(sat(zs.height(0.0) * 1.6), sat(zw.height(0.0)) * 0.9), sat(zc.height(0.0) * 1.8))
    scar = sat(blur(scar, 0.8) * 1.15)
    srough = fbm(n, 30, 3, S + 8) * 1.6 + gr * 0.5
    H = H + scar * (1.6 + srough) - sat(zc.height(0.0) * 2.0 - 0.9) * 3.0

    tb = norm01(und * 0.35 + band * 0.45 + band2 * 0.2 + fbm(n, 6, 3, S + 9) * 0.8, 1, 99)
    alb = ramp(tb, [(0, '#c3beb2'), (0.4, '#d3cfc5'), (0.75, '#dedad1'), (1, '#e6e3db')])
    pink = smoothstep(0.0, 0.7, fbm(n, 3, 3, S + 10))
    alb = mix(alb, '#d8c9b8', pink * 0.30)
    alb = mix(alb, '#cdbfa9', peel2 * 0.45)                                       # fresher tan layer under a peel
    alb = mix(alb, '#a79f93', lip * 0.35)
    grey = smoothstep(0.25, 0.8, fbm(n, 4, 4, S + 11) + 0.2 * band)
    alb = mix(alb, '#b1ada4', grey * 0.35)
    alb = mix(alb, '#4f453c', lent * 0.85)
    scol = ramp(norm01(srough), [(0, '#211d1a'), (0.5, '#35302b'), (1, '#514a43')])
    alb = mix(alb, scol, scar)
    halo = sat(blur(scar, 5.0) * 1.6) * (1 - scar)
    alb = mix(alb, '#8f877c', halo * 0.45)
    ao = ao_from_height(H, (1.5, 4.0, 10.0), 1.0)
    alb = alb * (0.86 + 0.14 * ao)[..., None]
    alb = balance(alb, 0.2, 0.7)
    rough = 0.58 + 0.06 * tb - 0.05 * band * 0.4 + 0.05 * grey
    rough = lerp(rough, 0.90, np.maximum(lent, scar))
    save_tex('bark_birch', alb, H, rough, ao=ao, nscale=1.0, tile_m=TILE, height=norm01(H, 0.5, 99.7))


TABLE = {
    'bark_oak': bark_oak,
    'bark_pine': bark_pine,
    'bark_birch': bark_birch,
}

if __name__ == '__main__':
    run(TABLE)
