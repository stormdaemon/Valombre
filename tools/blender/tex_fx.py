"""VALOMBRE FX textures:
  water_n.png      512 RGBA: R,G = tiling ripple normal (two blended wave scales), B = foam / caustic noise, A = 255
  fx_noise.png     512 RGBA: R = low-frequency perlin fbm, G = worley F1, B = high-frequency fbm, A = billowy cloud
  fx_bluenoise.png 64  grey: void-and-cluster blue noise (tileable, flat histogram)
Run:  blender -b --factory-startup -P tools/blender/tex_fx.py -- [water_n fx_noise fx_bluenoise]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex_lib import *


def _report(name, arr):
    chans = arr.shape[2] if arr.ndim == 3 else 1
    a = arr if arr.ndim == 3 else arr[..., None]
    seams = ' '.join('%.2f/%.2f' % seam_score(a[..., k]) for k in range(chans))
    means = ' '.join('%.3f' % a[..., k].mean() for k in range(chans))
    print('WROTE %s %s  mean=[%s]  seam=[%s]' % (name, 'x'.join(map(str, arr.shape)), means, seams))


# ============================================================================= water
def water_n():
    n, S = 512, 5001
    # two wave scales: broad swell-like ripples + fine wind chop
    h1 = spectral(n, S + 1, beta=1.6, lo=4.0, hi=11.0)
    h2 = spectral(n, S + 2, beta=1.2, lo=13.0, hi=42.0)
    h1 = h1 + 0.14 * (h1 * h1 - 1.0)                       # sharper crests, flatter troughs
    H = h1 * 3.2 + h2 * 0.85
    nrm = normal_from_height(H, 1.0)
    # foam / caustic web: bright filaments where two warped cellular layers meet, plus soft fbm
    xw, yw = warped_grid(n, 16, 4, S + 3, 2)
    w1 = worley(n, 7, seed=S + 4, jitter=1.0, x=xw, y=yw)
    w2 = worley(n, 12, seed=S + 5, jitter=1.0, x=xw + 0.031, y=yw + 0.017)
    c1 = (1 - smoothstep(0.0, 0.28, w1.edge)) ** 1.5
    c2 = (1 - smoothstep(0.0, 0.30, w2.edge)) ** 1.5
    foam = c1 * 0.65 + c2 * 0.45 + 0.20 * (fbm(n, 6, 4, S + 6) + 0.3)
    foam = norm01(blur(foam, 0.8), 0.5, 99.8)
    img = np.stack([nrm[..., 0] * 0.5 + 0.5, nrm[..., 1] * 0.5 + 0.5, foam, np.ones((n, n), F)], -1)
    save_png(os.path.join(TEXTURES, 'water_n.png'), img)
    _report('water_n', img)
    print('  water normal: nz avg=%.3f p05=%.3f' % (nrm[..., 2].mean(), np.percentile(nrm[..., 2], 5)))
    # preview: relief of the normal map lit on a neutral surface (3x3), foam channel (3x3), relief at 1:1
    alb = np.broadcast_to(hexc('#6f8f9c'), (n, n, 3)).astype(F)
    lit = lit_render(alb, nrm, np.full((n, n), 0.35, F), np.ones((n, n), F))
    p1 = down(tile(lit, 3), 3)
    p2 = down(tile(np.repeat(foam[..., None], 3, -1), 3), 3)
    p3 = lit
    save_png(os.path.join(PREVIEWS, 'tex_water_n.png'), montage([p1, p2, p3], cols=3))
    print('PREVIEW', os.path.join(PREVIEWS, 'tex_water_n.png'))


# ============================================================================= noise
def fx_noise():
    n, S = 512, 5101
    r_ = norm01(fbm(n, 4, 5, S + 1, exact=True), 0.05, 99.95)
    w = worley(n, 12, seed=S + 2, jitter=1.0)
    g_ = sat(w.f1 / float(w.f1.max()))
    b_ = norm01(fbm(n, 24, 4, S + 3, exact=True), 0.05, 99.95)
    # billowy cloud: perlin fbm eroded by inverted worley fbm (perlin-worley)
    wf = 0.0
    for k, a in ((5, 0.625), (10, 0.25), (20, 0.125)):
        wk = worley(n, k, seed=S + 4 + k, jitter=1.0)
        wf = wf + a * (1.0 - sat(wk.f1 / 1.0))
    pf = norm01(fbm(n, 4, 5, S + 9, exact=True), 0.05, 99.95)
    a_ = norm01((pf - (1.0 - wf) * 0.75) / (1.0 - (1.0 - wf) * 0.75 + 1e-3) * 0.5 + wf * 0.5, 0.05, 99.95)
    a_ = np.clip(a_, 2.0 / 255.0, 1.0)
    img = np.stack([r_, g_, b_, a_], -1)
    save_png(os.path.join(TEXTURES, 'fx_noise.png'), img)
    _report('fx_noise', img)
    panels = [np.repeat(down(tile(img[..., k], 2), 2)[..., None], 3, -1) for k in range(4)]
    save_png(os.path.join(PREVIEWS, 'tex_fx_noise.png'), montage(panels, cols=4))
    print('PREVIEW', os.path.join(PREVIEWS, 'tex_fx_noise.png'))


# ============================================================================= blue noise
def void_and_cluster(n=64, sigma=1.9, seed=0):
    """Ulichney's void-and-cluster dither array on a torus. Returns ranks 0..n*n-1 as (n, n) ints."""
    N = n * n
    d = np.minimum(np.arange(n), n - np.arange(n)).astype(np.float64)
    g = np.exp(-d * d / (2 * sigma * sigma))
    K = np.outer(g, g)
    Kf = np.fft.rfft2(K)

    def energy(bp):
        return np.fft.irfft2(np.fft.rfft2(bp.astype(np.float64)) * Kf, s=(n, n))

    def kern(idx):
        return np.roll(np.roll(K, idx // n, 0), idx % n, 1)

    r = rng(seed)
    bp = np.zeros(N, bool)
    bp[r.choice(N, N // 10, replace=False)] = True
    bp = bp.reshape(n, n)
    E = energy(bp)
    # relax the initial pattern: move the tightest cluster into the largest void until stable
    for _ in range(10 * N):
        c = int(np.argmax(np.where(bp, E, -np.inf)))
        bp.flat[c] = False
        E -= kern(c)
        v = int(np.argmin(np.where(bp, np.inf, E)))
        bp.flat[v] = True
        E += kern(v)
        if v == c:
            break
    rank = np.zeros(N, np.int64)
    n1 = int(bp.sum())
    # phase 1: remove points from the tightest clusters
    b = bp.copy()
    e = E.copy()
    for k in range(n1 - 1, -1, -1):
        c = int(np.argmax(np.where(b, e, -np.inf)))
        b.flat[c] = False
        e -= kern(c)
        rank[c] = k
    # phase 2: fill the largest voids up to half coverage
    b = bp.copy()
    e = E.copy()
    for k in range(n1, N // 2):
        v = int(np.argmin(np.where(b, np.inf, e)))
        b.flat[v] = True
        e += kern(v)
        rank[v] = k
    # phase 3: the zeros are now the minority: remove the tightest clusters of zeros
    b0 = ~b
    e = energy(b0)
    for k in range(N // 2, N):
        c = int(np.argmax(np.where(b0, e, -np.inf)))
        b0.flat[c] = False
        e -= kern(c)
        rank[c] = k
    return rank.reshape(n, n)


def fx_bluenoise():
    n = 64
    rank = void_and_cluster(n, 1.9, 5201)
    img8 = (rank * 256 // (n * n)).astype(np.uint8)
    save_png(os.path.join(TEXTURES, 'fx_bluenoise.png'), img8)
    v = img8.astype(np.float64) / 255.0
    sp = np.abs(np.fft.fftshift(np.fft.fft2(v - v.mean()))) ** 2
    yy, xx = np.mgrid[-n // 2:n // 2, -n // 2:n // 2]
    rad = np.sqrt(xx * xx + yy * yy)
    low = sp[(rad > 0) & (rad < 6)].mean()
    high = sp[(rad > 20) & (rad < 32)].mean()
    hist = np.bincount(img8.ravel(), minlength=256)
    print('WROTE fx_bluenoise %dx%d grey  mean=%.3f  hist min/max=%d/%d  spectrum low/high energy ratio=%.4f' % (
        n, n, v.mean(), hist.min(), hist.max(), low / high))
    # preview: 3x3 tiled x2 nearest, spectrum, thresholded at 25 %
    up = np.kron(tile(v, 3), np.ones((2, 2)))                      # 384
    pad = np.zeros((512, 512), F)
    pad[64:448, 64:448] = up
    spn = np.log1p(sp)
    spn = np.kron(spn / spn.max(), np.ones((8, 8)))
    th = np.kron((tile(v, 3) < 0.25).astype(F), np.ones((2, 2)))
    pad2 = np.zeros((512, 512), F)
    pad2[64:448, 64:448] = th
    panels = [np.repeat(p[..., None], 3, -1).astype(F) for p in (pad, spn, pad2)]
    save_png(os.path.join(PREVIEWS, 'tex_fx_bluenoise.png'), montage(panels, cols=3))
    print('PREVIEW', os.path.join(PREVIEWS, 'tex_fx_bluenoise.png'))


TABLE = {
    'water_n': water_n,
    'fx_noise': fx_noise,
    'fx_bluenoise': fx_bluenoise,
}

if __name__ == '__main__':
    run(TABLE)
