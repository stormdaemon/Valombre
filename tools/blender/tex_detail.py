"""VALOMBRE detail textures (512 px, one tile = 0.5 m, ~1 mm per pixel). The albedo is NEAR WHITE and neutral
(sRGB 200..235): the engine multiplies it by the vertex colour; the information is in normal / roughness / AO.
metal, leather, cloth, rope, fur, hide, chitin, bone, skin, hair.
Run:  blender -b --factory-startup -P tools/blender/tex_detail.py -- [names...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex_lib import *

N = 512
TILE = 0.5
LO, HI = 200.0 / 255.0, 235.0 / 255.0


def grain_noise(n, seed, lo=40, beta=0.6):
    return spectral(n, seed, beta=beta, lo=lo)


def speckle(n, seed, density, sigma=0.8):
    w = (white(n, seed) > (1.0 - density)).astype(F)
    s = blur(w, sigma)
    return sat(s * (2.0 * math.pi * sigma * sigma) * 1.3)


def white_alb(var, ao=None, base=0.862, ao_amount=0.06):
    """Neutral near-white albedo: base + small signed variation, slight cavity darkening, clamped 200..235."""
    v = base + var
    if ao is not None:
        v = v - (1.0 - ao) * ao_amount
    v = np.clip(v, LO, HI).astype(F)
    return np.repeat(v[..., None], 3, -1)


def out(name, var, H, rough, nscale=1.0, ao_radii=(1.5, 4.0, 10.0), ao_strength=1.0, nblur=0.0, ao_amount=0.06,
        height=None):
    ao = ao_from_height(H * nscale, ao_radii, ao_strength)
    alb = white_alb(var, ao, ao_amount=ao_amount)
    save_tex(name, alb, H, rough, ao=ao, nscale=nscale, tile_m=TILE, nblur=nblur, alb_range=(200, 235),
             height=norm01(H, 0.5, 99.7) if height is None else height)


# ============================================================================= metal
def metal():
    n, S = N, 3001
    r = rng(S)
    gr = grain_noise(n, S)
    xw, yw = warped_grid(n, 6, 5, S + 1, 2)
    w1 = worley(n, 12, seed=S + 2, jitter=0.95, x=xw, y=yw)
    d1 = np.exp(-(w1.f1 / 0.50) ** 2) * id_rand(w1.id, S + 3, 0.35, 1.0)
    w2 = worley(n, 21, seed=S + 4, jitter=0.95)
    d2 = np.exp(-(w2.f1 / 0.50) ** 2) * id_rand(w2.id, S + 5, 0.0, 1.0)
    H = -(d1 * 4.6 + d2 * 1.8) + fbm(n, 3, 3, S + 6) * 1.2
    H = blur(H, 1.0)
    # light scratches: mostly one direction, a few strays
    M = 340
    dom = r.uniform(0, math.pi)
    ang = np.where(r.random(M) < 0.6, dom + r.normal(0, 0.18, M), r.uniform(0, math.pi, M))
    zb = ZBuf(n, 2)
    strokes(zb, r.uniform(0, n, M), r.uniform(0, n, M), ang, np.minimum(15 + r.exponential(60, M), 300),
            r.uniform(0.55, 0.85, M), curve=r.normal(0, 0.01, M), h0=r.uniform(0.3, 1.0, M), h1=r.uniform(0.3, 1.0, M),
            taper=0.5, relief=0.3)
    sc = blur(zb.height(0.0), 0.45)
    pits = speckle(n, S + 7, 0.0011, 0.85)
    H = H - sc * 0.55 - pits * 1.1 + gr * 0.035
    mott = fbm(n, 5, 4, S + 8)
    patina = smoothstep(0.1, 0.7, fbm(n, 9, 3, S + 9) + 0.3 * mott)
    rough = 0.40 + 0.09 * mott + 0.12 * patina + 0.20 * sat(sc * 1.5) + 0.35 * pits - 0.07 * d1 + 0.02 * gr
    var = 0.012 * mott - 0.02 * patina + 0.03 * sat(sc * 1.5) - 0.08 * pits
    out('metal', var, H, rough)


# ============================================================================= leather
def leather():
    n, S = N, 3101
    gr = grain_noise(n, S)
    xw, yw = warped_grid(n, 6, 6, S + 1, 2)
    w1 = worley(n, 32, seed=S + 2, jitter=0.95, x=xw, y=yw)
    g1 = smoothstep(0.0, 0.30, w1.edge)
    w2 = worley(n, 62, seed=S + 3, jitter=0.95, x=xw, y=yw)
    g2 = smoothstep(0.0, 0.30, w2.edge)
    grain = g1 * (1.0 + id_randn(w1.id, S + 4, 0.22)) + g2 * 0.40
    xc = xw + fbm(n, 3, 2, S + 5) * 30 / n
    yc = yw + fbm(n, 3, 2, S + 6) * 30 / n
    wr = fbm(n, 4, 3, S + 7, mode='ridged', x=xc, y=yc, fy=6)
    crease = smoothstep(0.80, 0.97, wr)
    wr2 = fbm(n, 9, 2, S + 8, mode='ridged', x=xc, y=yc, fy=13)
    crease2 = smoothstep(0.84, 0.98, wr2) * 0.5
    pores = speckle(n, S + 9, 0.012, 0.8)
    und = fbm(n, 3, 3, S + 10)
    H = grain * 1.15 - crease * 2.6 - crease2 * 1.4 - pores * 0.7 + und * 1.2 + gr * 0.05
    mott = fbm(n, 5, 4, S + 11)
    cr = sat(crease + crease2)
    rough = 0.60 - 0.12 * g1 + 0.20 * cr + 0.18 * pores + 0.07 * mott
    var = 0.018 * (g1 - 0.7) - 0.05 * cr - 0.05 * pores + 0.012 * mott
    out('leather', var, H, rough)


# ============================================================================= cloth
def cloth():
    n, S = N, 3201
    x, y = grid(n)
    gr = grain_noise(n, S)
    T = 64
    xw = x + fbm(n, 4, 3, S + 1) * 1.8 / n
    yw = y + fbm(n, 4, 3, S + 2) * 1.8 / n
    u = xw * T
    v = yw * T
    i = np.floor(u)
    j = np.floor(v)
    fu = (u - i).astype(F)
    fv = (v - j).astype(F)
    ii = np.mod(i, T).astype(np.int32)
    jj = np.mod(j, T).astype(np.int32)
    # slubs: thread thickness varies from thread to thread and along each thread
    wi = id_rand(ii, S + 3, 0.80, 1.0) * (1.0 + 0.10 * perlin(n, 64, 5, S + 4))
    wj = id_rand(jj, S + 5, 0.80, 1.0) * (1.0 + 0.10 * perlin(n, 5, 64, S + 6))
    pw = np.sqrt(np.maximum(1 - ((2 * fu - 1) / wi) ** 2, 0))
    pf = np.sqrt(np.maximum(1 - ((2 * fv - 1) / wj) ** 2, 0))
    ow = 0.5 + 0.5 * np.sin(math.pi * (v + i))          # warp thread over (1) / under (0)
    of = 0.5 - 0.5 * np.sin(math.pi * (u + j))
    Hw = pw * (0.30 + 0.70 * ow)
    Hf = pf * (0.30 + 0.70 * of)
    isw = Hw > Hf
    Hm = np.maximum(Hw, Hf)
    fib_w = spectral(n, S + 7, beta=0.4, lo=30, sx=1.0, sy=5.0)
    fib_f = spectral(n, S + 8, beta=0.4, lo=30, sx=5.0, sy=1.0)
    fib = np.where(isw, fib_w, fib_f)
    H = Hm * 2.6 + fib * 0.22 * Hm + gr * 0.06
    tv = np.where(isw, id_randn(ii, S + 9, 1.0), id_randn(jj, S + 10, 1.0))
    rough = 0.93 - 0.07 * Hm + 0.02 * tv + 0.02 * fib
    var = 0.035 * (Hm - 0.62) + 0.008 * tv + 0.006 * fib
    out('cloth', var, H, rough, ao_radii=(1.5, 3.0, 6.0))


# ============================================================================= rope
def rope():
    n, S = N, 3301
    x, y = grid(n)
    gr = grain_noise(n, S)
    xw = x + fbm(n, 5, 2, S + 1) * 1.6 / n
    yw = y + fbm(n, 5, 2, S + 2) * 1.6 / n
    NS = 16
    p = (xw + yw) * NS
    sid = np.mod(np.floor(p), NS).astype(np.int32)
    f = (p - np.floor(p)).astype(F)
    wd = id_rand(sid, S + 3, 0.88, 1.0)
    prof = np.sqrt(np.maximum(1 - ((2 * f - 1) / wd) ** 2, 0))
    # fibres inside each strand run nearly along V, twisted the other way
    q = xw * 96 - yw * 16 + id_rand(sid, S + 4, 0, 1) + fbm(n, 10, 2, S + 5) * 0.7
    fibre = np.sin(TAU * q)
    fine = spectral(n, S + 6, beta=0.4, lo=40, sx=1.0, sy=4.0)
    yarn = np.sin(TAU * (xw * 48 - yw * 16 + id_rand(sid, S + 7, 0, 1)))        # 3 yarns per strand
    H = prof * (4.6 + 0.9 * yarn * prof) + prof * (fibre * 0.42 + fine * 0.22) + gr * 0.05
    # stray fibres
    r = rng(S + 8)
    M = 260
    zb = ZBuf(n, 2)
    strokes(zb, r.uniform(0, n, M), r.uniform(0, n, M), math.pi / 2 + r.normal(0, 0.5, M), r.uniform(8, 30, M),
            0.75, curve=r.normal(0, 0.2, M), h0=1.0, h1=1.0, taper=0.3, relief=0.4)
    stray = blur(zb.mask().astype(F), 0.5)
    H = H + stray * 0.6
    rough = 0.93 - 0.06 * prof + 0.02 * fibre * prof
    var = 0.035 * (prof - 0.65) + 0.008 * fibre * prof + 0.008 * id_randn(sid, S + 9, 1.0) + 0.01 * stray
    out('rope', var, H, rough, ao_radii=(1.5, 4.0, 9.0))


# ============================================================================= fur
def fur():
    n, S = N, 3401
    r = rng(S)
    flow = fbm(n, 2, 2, S + 1, exact=True) * 0.50
    lockh = norm01(fbm(n, 9, 2, S + 2))
    M = 12000
    x0 = r.uniform(0, n, M)
    y0 = r.uniform(0, n, M)
    ix = x0.astype(int) % n
    iy = y0.astype(int) % n
    ang = math.pi / 2 + flow[iy, ix] + r.normal(0, 0.15, M)
    L = r.uniform(22, 54, M)
    h1 = r.uniform(0.40, 1.0, M) * (0.65 + 0.35 * lockh[iy, ix])
    zb = ZBuf(n, 2)
    strokes(zb, x0, y0, ang, L, r.uniform(0.72, 1.08, M), curve=r.normal(0, 0.09, M), h0=r.uniform(0.0, 0.15, M),
            h1=h1, taper=0.72, relief=0.14)
    ids = np.maximum(zb.ids(), 0)
    t = zb.payload(0)
    Hn = zb.height(0.0)
    H = blur(Hn, 0.4) * 4.6
    sv = id_randn(ids, S + 3, 1.0)
    rough = 0.74 - 0.14 * t + 0.03 * sv
    rough = np.where(zb.mask(), rough, 0.95)
    var = 0.016 * sv + 0.03 * (t - 0.5)
    out('fur', var, H, rough, ao_amount=0.09, height=norm01(blur(Hn, 1.0), 0.5, 99.5))


# ============================================================================= hide
def hide():
    n, S = N, 3501
    r = rng(S)
    gr = grain_noise(n, S)
    xw, yw = warped_grid(n, 12, 4, S + 1, 2)
    K = 18
    w = worley(n, K, K, S + 2, jitter=0.80, x=xw, y=yw, hexa=True)
    e = w.edge * (n / K)
    t = sat((e - 1.2) / 7.0)
    prof = np.sqrt(1 - (1 - t) ** 2)
    dome = 1 - sat(w.f1 / 0.75) ** 2
    bump = prof * (1.8 + 2.4 * dome) * id_rand(w.id, S + 3, 0.40, 1.0)
    w2 = worley(n, 46, seed=S + 4, jitter=0.9, x=xw, y=yw)
    b2 = smoothstep(0.0, 0.3, w2.edge) * 0.6
    M = 30
    wr_ = r.uniform(7, 13, M)
    zb = blobs(n, r.uniform(0, n, M), r.uniform(0, n, M), wr_, wr_ * r.uniform(0.75, 1.0, M), r.uniform(0, TAU, M),
               S + 5, irr=0.15, hscale=r.uniform(3.0, 5.0, M), profile=0.6)
    warts = blur(zb.height(0.0), 1.0)
    xc = xw + fbm(n, 3, 2, S + 6) * 34 / n
    yc = yw + fbm(n, 3, 2, S + 7) * 34 / n
    wr = fbm(n, 3, 3, S + 8, mode='ridged', x=xc, y=yc, fy=6)
    crease = smoothstep(0.78, 0.96, wr)
    pores = speckle(n, S + 9, 0.008, 0.9)
    und = fbm(n, 3, 3, S + 10)
    H = bump + b2 + warts - crease * 4.2 - pores * 0.8 + und * 2.2 + gr * 0.06
    H = blur(H, 0.5)
    mott = fbm(n, 5, 4, S + 11)
    rough = 0.74 - 0.14 * dome * prof + 0.14 * crease + 0.12 * pores + 0.06 * mott - 0.08 * sat(warts / 4.0)
    var = 0.022 * (prof * dome - 0.4) - 0.05 * crease - 0.04 * pores + 0.012 * mott
    out('hide', var, H, rough, ao_radii=(2.0, 5.0, 12.0))


# ============================================================================= chitin
def chitin():
    n, S = N, 3601
    x, y = grid(n)
    gr = grain_noise(n, S)
    und = fbm(n, 2, 3, S + 1) * 1.3 + fbm(n, 7, 2, S + 2) * 0.35
    ph = y * 36 + fbm(n, 3, 3, S + 3) * 1.8
    ridg = (0.5 + 0.5 * np.sin(TAU * ph)) ** 3 * (0.16 + 0.26 * smoothstep(-0.3, 0.4, fbm(n, 4, 2, S + 4)))
    car = (0.5 + 0.5 * np.sin(TAU * (x * 6 + fbm(n, 3, 2, S + 5) * 0.35))) ** 10 * 0.30
    pits = speckle(n, S + 6, 0.0018, 0.9)
    big = speckle(n, S + 7, 0.00035, 1.6)
    H = und + ridg + car - pits * 0.85 - big * 1.4 + gr * 0.015
    mott = fbm(n, 5, 4, S + 8)
    msc = sat(spectral(n, S + 9, beta=0.3, lo=40, sx=1.0, sy=10.0) - 1.6)
    rough = 0.22 + 0.07 * mott + 0.45 * pits + 0.5 * big + 0.25 * ridg + 0.10 * msc
    var = 0.012 * mott - 0.07 * pits - 0.08 * big + 0.02 * ridg
    out('chitin', var, H, rough, ao_radii=(1.2, 3.0, 8.0))


# ============================================================================= bone
def bone():
    n, S = N, 3701
    r = rng(S)
    gr = grain_noise(n, S)
    und = fbm(n, 3, 3, S + 1) * 1.5
    fib = spectral(n, S + 2, beta=0.8, lo=10, hi=220, sx=1.0, sy=14.0)
    pz = smoothstep(-0.15, 0.45, fbm(n, 4, 3, S + 3))
    M = 5200
    px = r.uniform(0, n, M)
    py = r.uniform(0, n, M)
    keep = r.random(M) < (0.12 + 0.88 * pz[py.astype(int) % n, px.astype(int) % n])
    px, py = px[keep], py[keep]
    M = len(px)
    prx = r.uniform(0.75, 1.7, M)
    zb = blobs(n, px, py, prx, prx * r.uniform(1.4, 3.6, M), r.normal(0, 0.15, M), S + 4, irr=0.2, hscale=1.0,
               profile=0.6)
    pore = blur(zb.height(0.0), 0.4)
    ck = spectral(n, S + 5, beta=0.8, lo=6, hi=250, sx=1.0, sy=30.0)
    crack = smoothstep(2.0, 2.35, ck)
    xw, yw = warped_grid(n, 14, 5, S + 6, 2)
    w = worley(n, 5, seed=S + 7, jitter=1.0, x=xw, y=yw)
    hair_ = (1 - smoothstep(0.3, 1.0, w.edge * (n / 5))) * smoothstep(0.0, 0.4, fbm(n, 3, 2, S + 8)) * 0.6
    H = und + fib * 0.38 - pore * 1.6 - crack * 1.7 - hair_ * 1.1 + gr * 0.05
    mott = fbm(n, 5, 4, S + 9)
    ck_all = sat(crack + hair_)
    rough = 0.62 + 0.08 * pz + 0.28 * sat(pore) + 0.28 * ck_all + 0.05 * mott - 0.04 * fib
    var = 0.012 * mott + 0.01 * fib - 0.07 * sat(pore) - 0.06 * ck_all - 0.012 * pz
    out('bone', var, H, rough, ao_radii=(1.2, 3.0, 8.0))


# ============================================================================= skin
def skin():
    n, S = N, 3801
    gr = grain_noise(n, S)
    xw, yw = warped_grid(n, 5, 6, S + 1, 2)
    w1 = worley(n, 40, seed=S + 2, jitter=0.95, x=xw, y=yw)
    l1 = 1 - smoothstep(0.0, 0.16, w1.edge)
    w2 = worley(n, 21, seed=S + 3, jitter=0.95, x=xw, y=yw)
    l2 = 1 - smoothstep(0.0, 0.08, w2.edge)
    p1, e1 = ripples(n, S + 4, 58.0, 9.0, 12.0, angle=0.60)
    p2, e2 = ripples(n, S + 5, 58.0, 9.0, 12.0, angle=2.50)
    cross = np.cos(p1) * sat(e1) + np.cos(p2) * sat(e2)
    pores = speckle(n, S + 6, 0.012, 0.8)
    und = fbm(n, 4, 3, S + 7)
    H = -(l1 * 0.20 + l2 * 0.28) + cross * 0.10 - pores * 0.38 + und * 0.5 + gr * 0.025
    mott = fbm(n, 5, 4, S + 8)
    ln = sat(l1 * 0.6 + l2)
    rough = 0.50 + 0.07 * mott + 0.08 * ln - 0.07 * pores + 0.02 * cross
    var = 0.008 * mott - 0.02 * ln - 0.025 * pores
    out('skin', var, H, rough, ao_radii=(1.0, 2.5, 6.0), ao_amount=0.04)


# ============================================================================= hair
def hair():
    n, S = N, 3901
    r = rng(S)
    flow = fbm(n, 2, 2, S + 1, exact=True) * 0.10
    lock = norm01(perlin(n, 22, 2, S + 2) + 0.5 * perlin(n, 47, 3, S + 3))
    M = 5600
    x0 = r.uniform(0, n, M)
    y0 = r.uniform(0, n, M)
    ix = x0.astype(int) % n
    iy = y0.astype(int) % n
    hz = np.clip(0.25 + 0.55 * lock[iy, ix] + r.normal(0, 0.14, M), 0.05, 1.0)
    zb = ZBuf(n, 2)
    strokes(zb, x0, y0, math.pi / 2 + flow[iy, ix] + r.normal(0, 0.025, M), r.uniform(130, 420, M),
            r.uniform(0.72, 1.12, M), curve=r.normal(0, 0.012, M), h0=hz, h1=hz, taper=0.25, step=0.9, relief=0.16,
            wave_amp=r.uniform(0.0, 2.2, M), wave_freq=r.uniform(0.6, 2.4, M), wave_phase=r.random(M))
    ids = np.maximum(zb.ids(), 0)
    t = zb.payload(0)
    s = zb.payload(1)
    Hn = zb.height(0.0)
    H = blur(Hn, 0.35) * 4.2
    sv = id_randn(ids, S + 4, 1.0)
    cut = spectral(n, S + 5, beta=0.5, lo=20, sx=4.0, sy=1.0)                 # cuticle variation along the strands
    rough = 0.44 + 0.05 * sv + 0.05 * cut + 0.08 * (1 - Hn)
    rough = np.where(zb.mask(), rough, 0.85)
    var = 0.018 * sv + 0.02 * (Hn - 0.5) + 0.012 * (1 - s * s) - 0.006
    out('hair', var, H, rough, ao_amount=0.09, height=norm01(blur(Hn, 1.0), 0.5, 99.5))


TABLE = {
    'metal': metal,
    'leather': leather,
    'cloth': cloth,
    'rope': rope,
    'fur': fur,
    'hide': hide,
    'chitin': chitin,
    'bone': bone,
    'skin': skin,
    'hair': hair,
}

if __name__ == '__main__':
    run(TABLE)
