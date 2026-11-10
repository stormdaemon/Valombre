"""tex_lib.py - numpy procedural texture toolkit for VALOMBRE (runs inside Blender's bundled Python).

Everything here is PERIODIC: every function produces data that tiles seamlessly on both axes.
Conventions:
  * arrays are float32, shape (n, n) (row 0 = TOP of the image), colors are (n, n, 3) sRGB 0..1
  * tile coordinates x, y in [0, 1): x -> right, y -> DOWN (row index). `grid(n)` gives pixel centers.
  * height fields `H` are expressed in PIXELS of displacement (physical: mm / (mm per pixel)), so the normal
    map derived from them is physically meaningful; `nscale` exaggerates / tones it down.
  * normal maps are OpenGL style: +X right, +Y UP in the image, encoded n * 0.5 + 0.5.

Texture scripts:  from tex_lib import *
"""
import os, sys, math, json, time, zlib, struct
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import save_png, montage, TEXTURES, PREVIEWS, ROOT

F = np.float32
TAU = 2.0 * math.pi


# ----------------------------------------------------------------------------- basics
def rng(seed):
    return np.random.default_rng(int(seed) & 0x7fffffff)


def grid(n):
    """Pixel-center tile coordinates (x, y), each (n, n) float32 in [0, 1)."""
    c = ((np.arange(n, dtype=F) + 0.5) / n)
    return np.broadcast_to(c[None, :], (n, n)).copy(), np.broadcast_to(c[:, None], (n, n)).copy()


def sat(x):
    return np.clip(x, 0.0, 1.0)


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    t = sat((x - a) / (b - a + 1e-12))
    return t * t * (3.0 - 2.0 * t)


def norm01(a, lo=None, hi=None):
    """Rescale to 0..1. lo/hi are PERCENTILES (0..100) when given (robust to outliers)."""
    a = np.asarray(a, F)
    mn = a.min() if lo is None else np.percentile(a, lo)
    mx = a.max() if hi is None else np.percentile(a, hi)
    return sat((a - mn) / (mx - mn + 1e-12)).astype(F)


def nstd(a):
    """zero mean, unit std."""
    a = a - a.mean()
    return (a / (a.std() + 1e-12)).astype(F)


def bias(x, b):
    return x / ((1.0 / b - 2.0) * (1.0 - x) + 1.0)


def soft_clip_hi(x, knee, ceil):
    """Compress values above `knee` smoothly towards `ceil`."""
    over = np.maximum(x - knee, 0.0)
    return np.minimum(x, knee) + (ceil - knee) * (1.0 - np.exp(-over / (ceil - knee + 1e-9)))


# ----------------------------------------------------------------------------- color
def hexc(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return np.array([int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], F)
    c = np.asarray(c, F)
    return c / 255.0 if c.max() > 1.0 else c


def srgb2lin(c):
    c = np.asarray(c, F)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(F)


def lin2srgb(c):
    c = np.clip(np.asarray(c, F), 0.0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055).astype(F)


def ramp(t, stops):
    """Color ramp: t (n, n) in 0..1, stops = [(pos, color), ...] -> (n, n, 3)."""
    pos = np.array([s[0] for s in stops], F)
    cols = np.stack([hexc(s[1]) for s in stops])
    out = np.empty(t.shape + (3,), F)
    for k in range(3):
        out[..., k] = np.interp(t, pos, cols[:, k])
    return out


def mix(a, b, m):
    """Blend colors (n, n, 3) / constants with a mask (n, n)."""
    a = hexc(a) if isinstance(a, str) else a
    b = hexc(b) if isinstance(b, str) else b
    m = np.asarray(m, F)[..., None]
    return (a * (1.0 - m) + b * m).astype(F)


def luma(c):
    return (c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114).astype(F)


def palette_pick(ids, colors, seed, weights=None):
    """Per-instance color: ids (int array, any shape) -> color table lookup with random choice per id."""
    cols = np.stack([hexc(c) for c in colors])
    n = int(ids.max()) + 2
    r = rng(seed)
    pick = r.choice(len(cols), size=n, p=None if weights is None else np.asarray(weights, float) / np.sum(weights))
    return cols[pick][ids]


def id_rand(ids, seed, lo=0.0, hi=1.0):
    """Per-instance random scalar looked up by integer id array (ids >= -1)."""
    n = int(ids.max()) + 2
    t = rng(seed).random(n).astype(F) * (hi - lo) + lo
    return t[ids]


def id_randn(ids, seed, sigma=1.0):
    n = int(ids.max()) + 2
    t = (rng(seed).standard_normal(n) * sigma).astype(F)
    return t[ids]


# ----------------------------------------------------------------------------- periodic noise
def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin(n, fx, fy=None, seed=0, x=None, y=None):
    """Periodic gradient noise, fx / fy cells per tile (integers). Output roughly in [-1, 1].
    Optional x, y: custom (e.g. domain warped) tile coordinates."""
    fx = int(max(1, round(fx)))
    fy = fx if fy is None else int(max(1, round(fy)))
    r = rng(seed * 7919 + fx * 31 + fy)
    ang = r.uniform(0, TAU, (fy, fx)).astype(F)
    gx, gy = np.cos(ang), np.sin(ang)
    if x is None:
        x, y = grid(n)
    px = x * fx
    py = y * fy
    x0 = np.floor(px)
    y0 = np.floor(py)
    tx = (px - x0).astype(F)
    ty = (py - y0).astype(F)
    x0 = x0.astype(np.int32) % fx
    y0 = y0.astype(np.int32) % fy
    x1 = (x0 + 1) % fx
    y1 = (y0 + 1) % fy
    n00 = gx[y0, x0] * tx + gy[y0, x0] * ty
    n10 = gx[y0, x1] * (tx - 1) + gy[y0, x1] * ty
    n01 = gx[y1, x0] * tx + gy[y1, x0] * (ty - 1)
    n11 = gx[y1, x1] * (tx - 1) + gy[y1, x1] * (ty - 1)
    u = _fade(tx)
    v = _fade(ty)
    return ((n00 + (n10 - n00) * u) * (1 - v) + (n01 + (n11 - n01) * u) * v).astype(F) * 1.5


def fbm(n, f, octaves=5, seed=0, gain=0.5, fy=None, mode='fbm', x=None, y=None, exact=False):
    """Fractal sum of periodic perlin. mode: 'fbm' (-1..1), 'ridged' (0..1 sharp crests), 'billow' (0..1)."""
    if x is None and mode == 'fbm' and fy is None and not exact:
        # fast path: FFT-shaped noise with the same band and spectral slope as the perlin sum
        beta = 1.0 - math.log2(gain)
        return (spectral(n, seed * 13 + int(f) * 7 + octaves, beta=beta, lo=f * 0.75,
                         hi=min(f * (2 ** octaves) * 0.75, n * 0.5)) * 0.36).astype(F)
    out = np.zeros((n, n) if x is None else x.shape, F)
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        ffx = f * (2 ** o)
        ffy = (fy if fy is not None else f) * (2 ** o)
        if max(ffx, ffy) > n // 2:
            break
        p = perlin(n, ffx, ffy, seed + o * 101, x, y)
        if mode == 'ridged':
            p = 1.0 - np.abs(p)
            p = p * p
        elif mode == 'billow':
            p = np.abs(p)
        out += p * amp
        tot += amp
        amp *= gain
    return (out / tot).astype(F)


def _kgrid(n):
    ky = (np.fft.fftfreq(n) * n).astype(F)[:, None]
    kx = (np.fft.rfftfreq(n) * n).astype(F)[None, :]
    return kx, ky


def spectral(n, seed, beta=1.5, lo=1.0, hi=None, sx=1.0, sy=1.0):
    """Periodic 1/f^beta noise by FFT filtering (unit std). lo/hi: band limits in cycles per tile.
    sx, sy > 1 damp frequencies along that axis => features elongated ALONG that axis."""
    w = rng(seed).standard_normal((n, n)).astype(F)
    Fw = np.fft.rfft2(w)
    kx, ky = _kgrid(n)
    k = np.sqrt((kx * sx) ** 2 + (ky * sy) ** 2)
    k[0, 0] = 1.0
    amp = k ** (-beta)
    amp *= 1.0 - np.exp(-(k / max(lo, 1e-3)) ** 4)
    if hi is not None:
        amp *= np.exp(-(k / hi) ** 4)
    amp[0, 0] = 0.0
    return nstd(np.fft.irfft2(Fw * amp, s=(n, n)).astype(F))


def bandnoise(n, seed, f0, bw_par, bw_perp, angle=math.pi / 2):
    """Band-pass oriented noise (ripples with natural dislocations). f0 = cycles per tile along the wave
    vector, whose direction is `angle` (pi/2 => wave vector along y => crests run horizontally)."""
    w = rng(seed).standard_normal((n, n)).astype(F)
    Fw = np.fft.rfft2(w)
    kx, ky = _kgrid(n)
    ca, sa = math.cos(angle), math.sin(angle)
    kpar = kx * ca + ky * sa
    kper = -kx * sa + ky * ca
    amp = np.exp(-((np.abs(kpar) - f0) ** 2) / (2 * bw_par ** 2) - (kper ** 2) / (2 * bw_perp ** 2))
    amp[0, 0] = 0.0
    return nstd(np.fft.irfft2(Fw * amp, s=(n, n)).astype(F))


def ripples(n, seed, f0, bw_par, bw_perp, angle=math.pi / 2):
    """Uniform-amplitude oriented ripples with natural dislocations (analytic signal of a band-pass noise).
    Returns (phase, env): phase in radians (use cos(phase)), env >= 0 with mean 1 (-> 0 at the defects)."""
    w = rng(seed).standard_normal((n, n)).astype(F)
    Fw = np.fft.fft2(w)
    ky = (np.fft.fftfreq(n) * n).astype(F)[:, None]
    kx = (np.fft.fftfreq(n) * n).astype(F)[None, :]
    ca, sa = math.cos(angle), math.sin(angle)
    kpar = kx * ca + ky * sa
    kper = -kx * sa + ky * ca
    amp = np.exp(-((kpar - f0) ** 2) / (2 * bw_par ** 2) - (kper ** 2) / (2 * bw_perp ** 2))
    z = np.fft.ifft2(Fw * amp)
    env = np.abs(z)
    return np.angle(z).astype(F), (env / env.mean()).astype(F)


def white(n, seed):
    return rng(seed).random((n, n)).astype(F)


def blur(a, sigma, sigma_y=None):
    """Periodic gaussian blur (FFT). sigma in pixels (x), sigma_y defaults to sigma."""
    a = np.asarray(a, F)
    n0, n1 = a.shape[:2]
    sy = sigma if sigma_y is None else sigma_y
    fy = np.fft.fftfreq(n0).astype(F)[:, None]
    fx = np.fft.rfftfreq(n1).astype(F)[None, :]
    g = np.exp(-2.0 * (math.pi ** 2) * ((sigma * fx) ** 2 + (sy * fy) ** 2)).astype(F)
    if a.ndim == 3:
        return np.stack([np.fft.irfft2(np.fft.rfft2(a[..., k]) * g, s=(n0, n1)) for k in range(a.shape[2])],
                        -1).astype(F)
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(n0, n1)).astype(F)


def highpass(a, sigma):
    return (a - blur(a, sigma)).astype(F)


def sample(a, px, py):
    """Bilinear periodic sampling of array a at pixel coordinates (px = column, py = row)."""
    n0, n1 = a.shape[:2]
    px = px - 0.5
    py = py - 0.5
    x0 = np.floor(px)
    y0 = np.floor(py)
    tx = (px - x0).astype(F)
    ty = (py - y0).astype(F)
    x0 = x0.astype(np.int64) % n1
    y0 = y0.astype(np.int64) % n0
    x1 = (x0 + 1) % n1
    y1 = (y0 + 1) % n0
    if a.ndim == 3:
        tx = tx[..., None]
        ty = ty[..., None]
    return ((a[y0, x0] * (1 - tx) + a[y0, x1] * tx) * (1 - ty) + (a[y1, x0] * (1 - tx) + a[y1, x1] * tx) * ty).astype(F)


def warp(a, dx, dy):
    """Domain warp an existing array: out(x, y) = a(x + dx, y + dy), offsets in pixels."""
    n = a.shape[0]
    xs = np.arange(a.shape[1], dtype=F)[None, :] + 0.5
    ys = np.arange(n, dtype=F)[:, None] + 0.5
    return sample(a, xs + dx, ys + dy)


def warped_grid(n, amp_px, f, seed, octaves=2, gain=0.5):
    """Tile coords displaced by periodic fbm (amp in pixels). Feed to perlin / worley / courses."""
    x, y = grid(n)
    wx = fbm(n, f, octaves, seed, gain) * (amp_px / n)
    wy = fbm(n, f, octaves, seed + 57, gain) * (amp_px / n)
    return (x + wx).astype(F), (y + wy).astype(F)


# ----------------------------------------------------------------------------- worley / voronoi
class Cells:
    pass


def worley(n, kx, ky=None, seed=0, jitter=0.85, x=None, y=None, hexa=False):
    """Periodic Voronoi on a jittered kx * ky grid (metric is isotropic in CELL units, so kx != ky gives
    stretched cells). Returns Cells with: f1, f2 (cell units), edge (exact distance to the nearest cell
    border, cell units), id (int, 0..kx*ky-1), dx, dy (offset from the cell's seed point, cell units).
    hexa: shift odd rows by half a cell (rounder, honeycomb-like cells; ky must be even)."""
    kx = int(kx)
    ky = kx if ky is None else int(ky)
    r = rng(seed * 104729 + kx * 131 + ky)
    px = (0.5 + (r.random((ky, kx)) - 0.5) * jitter).astype(F)
    py = (0.5 + (r.random((ky, kx)) - 0.5) * jitter).astype(F)
    if x is None:
        x, y = grid(n)
    gx = x * kx
    gy = y * ky
    ix = np.floor(gx)
    iy = np.floor(gy)
    fx = (gx - ix).astype(F)
    fy = (gy - iy).astype(F)
    ix = ix.astype(np.int32)
    iy = iy.astype(np.int32)
    shp = fx.shape
    f1 = np.full(shp, 1e9, F)
    f2 = np.full(shp, 1e9, F)
    v1x = np.zeros(shp, F)
    v1y = np.zeros(shp, F)
    v2x = np.zeros(shp, F)
    v2y = np.zeros(shp, F)
    cid = np.zeros(shp, np.int32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cx = (ix + ox) % kx
            cy = (iy + oy) % ky
            dx = ox + px[cy, cx] - fx
            if hexa:
                dx = dx + 0.5 * (cy & 1)
            dy = oy + py[cy, cx] - fy
            d = dx * dx + dy * dy
            m1 = d < f1
            m2 = (~m1) & (d < f2)
            f2 = np.where(m1, f1, np.where(m2, d, f2))
            v2x = np.where(m1, v1x, np.where(m2, dx, v2x))
            v2y = np.where(m1, v1y, np.where(m2, dy, v2y))
            f1 = np.where(m1, d, f1)
            v1x = np.where(m1, dx, v1x)
            v1y = np.where(m1, dy, v1y)
            cid = np.where(m1, cy * kx + cx, cid)
    c = Cells()
    c.f1 = np.sqrt(f1)
    c.f2 = np.sqrt(f2)
    sep = np.sqrt((v2x - v1x) ** 2 + (v2y - v1y) ** 2) + 1e-6
    c.edge = ((f2 - f1) / (2.0 * sep)).astype(F)
    c.id = cid
    c.dx = -v1x
    c.dy = -v1y
    c.count = kx * ky
    return c


# ----------------------------------------------------------------------------- masonry layouts
def random_rows(nrows, seed, hvar=0.3, wmin=0.08, wmax=0.25, widths=None, skew=0.0):
    """Rows of a coursed wall: list of (height, widths array (sums to 1), x offset, joint skews).
    Heights sum to 1. skew: std of the slant of the vertical joints (dx / dy)."""
    r = rng(seed)
    hs = 1.0 + (r.random(nrows) - 0.5) * 2 * hvar
    hs /= hs.sum()
    rows = []
    for i in range(nrows):
        if widths is not None:
            ws = np.asarray(widths(i, r), float)
        else:
            ws = []
            while sum(ws) < 1.0:
                ws.append(r.uniform(wmin, wmax))
            ws = np.array(ws)
            if ws[-1] - (ws.sum() - 1.0) < wmin * 0.7 and len(ws) > 2:   # avoid a sliver
                ws = ws[:-1]
        ws = ws / ws.sum()
        sk = np.clip(r.normal(0, 1, len(ws)), -2, 2) * skew * hs[i]
        rows.append((hs[i], ws, r.random(), sk))
    return rows


def courses(x, y, rows):
    """Evaluate a coursed layout at tile coords (x, y) (may be domain warped).
    Returns Cells: id, u, v (0..1 inside the stone), w, h (stone size in tile units),
    a (distance to the nearest vertical joint), b (distance to nearest horizontal joint), row, count."""
    shp = x.shape
    yy = np.mod(y, 1.0)
    xx = np.mod(x, 1.0)
    hs = np.array([r[0] for r in rows], float)
    edges = np.concatenate([[0.0], np.cumsum(hs)])
    edges[-1] = 1.0 + 1e-6
    row = np.clip(np.searchsorted(edges, yy, side='right') - 1, 0, len(rows) - 1)
    c = Cells()
    c.id = np.zeros(shp, np.int32)
    c.u = np.zeros(shp, F)
    c.w = np.zeros(shp, F)
    c.row = row.astype(np.int32)
    c.h = hs[row].astype(F)
    c.v = ((yy - edges[row]) / hs[row]).astype(F)
    base = 0
    for i, rw in enumerate(rows):
        h, ws, off = rw[0], rw[1], rw[2]
        k = len(ws)
        sk = rw[3] if len(rw) > 3 else np.zeros(k)
        m = row == i
        if not m.any():
            base += k
            continue
        xs = np.mod(xx[m] - off, 1.0)
        vv = c.v[m] - 0.5
        ce = np.concatenate([[0.0], np.cumsum(ws)])
        ce[-1] = 1.0
        col = np.clip(np.searchsorted(ce, xs, side='right') - 1, 0, k - 1)
        L = ce[col] + sk[col] * vv
        R = ce[col + 1] + sk[(col + 1) % k] * vv
        col = col - (xs < L) + (xs >= R)
        lo = col < 0
        hi = col >= k
        xs = xs + lo - hi
        col = np.where(lo, k - 1, np.where(hi, 0, col))
        L = ce[col] + sk[col] * vv
        R = ce[col + 1] + sk[(col + 1) % k] * vv
        c.id[m] = base + col
        c.u[m] = np.clip((xs - L) / (R - L), 0.0, 1.0)
        c.w[m] = R - L
        base += k
    c.count = base
    c.a = (np.minimum(c.u, 1 - c.u) * c.w).astype(F)
    c.b = (np.minimum(c.v, 1 - c.v) * c.h).astype(F)
    return c


def split_cells(c, seed, prob_h=0.15, prob_v=0.0, min_h=0.0, min_w=0.0):
    """Randomly split some stones in two (stacked: prob_h, side by side: prob_v) for size variety."""
    r = rng(seed)
    n = c.count
    kind = r.random(n)
    frac = r.uniform(0.38, 0.62, n).astype(F)
    do_h = (kind < prob_h)[c.id] & (c.h >= min_h)
    do_v = ((kind >= prob_h) & (kind < prob_h + prob_v))[c.id] & (c.w >= min_w)
    fr = frac[c.id]
    # stacked split
    top = c.v < fr
    v2 = np.where(top, c.v / fr, (c.v - fr) / (1 - fr))
    h2 = np.where(top, c.h * fr, c.h * (1 - fr))
    left = c.u < fr
    u2 = np.where(left, c.u / fr, (c.u - fr) / (1 - fr))
    w2 = np.where(left, c.w * fr, c.w * (1 - fr))
    nid = c.id.copy()
    nid = np.where(do_h & ~top, c.id + n, nid)
    nid = np.where(do_v & ~left, c.id + n, nid)
    c.v = np.where(do_h, v2, c.v).astype(F)
    c.h = np.where(do_h, h2, c.h).astype(F)
    c.u = np.where(do_v, u2, c.u).astype(F)
    c.w = np.where(do_v, w2, c.w).astype(F)
    c.id = nid.astype(np.int32)
    c.count = 2 * n
    c.a = (np.minimum(c.u, 1 - c.u) * c.w).astype(F)
    c.b = (np.minimum(c.v, 1 - c.v) * c.h).astype(F)
    return c


def rrect(a, b, r):
    """Inner distance to the border of a rounded rectangle given distances a, b to its straight sides."""
    corner = (a < r) & (b < r)
    return np.where(corner, r - np.sqrt((r - a) ** 2 + (r - b) ** 2), np.minimum(a, b)).astype(F)


# ----------------------------------------------------------------------------- z-buffered stamping
class ZBuf:
    """Max-height compositing buffer with per-pixel instance id + float payloads (wraps around)."""

    def __init__(self, n, npay=0, base=-1e9):
        self.n = n
        self.h = np.full(n * n, base, F)
        self.id = np.full(n * n, -1, np.int32)
        self.pay = [np.zeros(n * n, F) for _ in range(npay)]

    def add(self, ix, iy, h, ids, pays=()):
        n = self.n
        idx = (np.mod(iy, n) * n + np.mod(ix, n)).astype(np.int64)
        h = h.astype(F)
        np.maximum.at(self.h, idx, h)
        win = h >= self.h[idx]
        idx = idx[win]
        self.id[idx] = ids[win]
        for b, p in zip(self.pay, pays):
            b[idx] = p[win]

    def height(self, empty=0.0):
        n = self.n
        return np.where(self.id >= 0, self.h, empty).reshape(n, n).astype(F)

    def ids(self):
        return self.id.reshape(self.n, self.n)

    def mask(self):
        return (self.id >= 0).reshape(self.n, self.n)

    def payload(self, i):
        return self.pay[i].reshape(self.n, self.n)


_BUCKETS = np.array([2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256])


def stamp(zb, cx, cy, rad, fn, ids=None, max_elems=3_000_000):
    """Stamp N instances. cx, cy: pixel coords (float, pixel i has its center at i + 0.5); rad: bounding
    radius in px (array). fn(sel, dx, dy) -> (h, [payload, ...]) where dx (k,1,w) / dy (k,w,1) are pixel
    offsets from each instance center and the results have shape (k, w, w); pixels with h <= -1e8 are skipped."""
    cx = np.asarray(cx, float)
    cy = np.asarray(cy, float)
    N = len(cx)
    rad = np.broadcast_to(np.asarray(rad, float), (N,))
    if ids is None:
        ids = np.arange(N, dtype=np.int32)
    half = np.ceil(rad).astype(int) + 1
    b = np.minimum(np.searchsorted(_BUCKETS, half), len(_BUCKETS) - 1)
    for bi in np.unique(b):
        sel_all = np.nonzero(b == bi)[0]
        hw = int(_BUCKETS[bi])
        w = 2 * hw + 1
        per = max(1, max_elems // (w * w))
        o = np.arange(-hw, hw + 1)
        for s in range(0, len(sel_all), per):
            sel = sel_all[s:s + per]
            bx = np.floor(cx[sel]).astype(np.int64)
            by = np.floor(cy[sel]).astype(np.int64)
            ix = bx[:, None, None] + o[None, None, :]
            iy = by[:, None, None] + o[None, :, None]
            dx = (ix + 0.5 - cx[sel][:, None, None]).astype(F)
            dy = (iy + 0.5 - cy[sel][:, None, None]).astype(F)
            h, pays = fn(sel, dx, dy)
            m = h > -1e8
            if not m.any():
                continue
            k = len(sel)
            ixb = np.broadcast_to(ix, (k, w, w))[m]
            iyb = np.broadcast_to(iy, (k, w, w))[m]
            idb = np.broadcast_to(ids[sel][:, None, None], (k, w, w))[m]
            zb.add(ixb, iyb, h[m], idb, [np.broadcast_to(p, (k, w, w))[m] for p in pays])


def strokes(zb, x0, y0, ang, length, width, curve=0.0, h0=0.2, h1=1.0, taper=0.6, step=0.7, ids=None,
            wave_amp=0.0, wave_freq=1.0, wave_phase=0.0, max_elems=4_000_000, relief=0.3):
    """Rasterize N curved strokes (blades, straws, twigs, hairs) into a ZBuf with payloads (t, s):
    t = 0..1 from root to tip, s = signed cross position -1..1.
    x0, y0 root in px; ang heading (0 = +x, pi/2 = +y = DOWN the image); length, width (HALF width) in px;
    curve = sideways bend as a fraction of length; h0 -> h1 = height from root to tip (arrays or scalars);
    taper = fraction of width lost at the tip; wave_* = sinusoidal wobble (px, cycles over the length);
    relief = how much lower the rim of the rounded cross-section is than its crest (same unit as h)."""
    N = len(x0)
    bc = lambda v: np.broadcast_to(np.asarray(v, F), (N,)).astype(F)
    x0, y0, ang, length, width, curve, h0, h1, wave_amp, wave_freq, wave_phase = map(
        bc, (x0, y0, ang, length, width, curve, h0, h1, wave_amp, wave_freq, wave_phase))
    if ids is None:
        ids = np.arange(N, dtype=np.int32)
    order = np.argsort(length)
    R = max(1, int(math.floor(float(width.max()) + 0.5)))
    oy, ox = np.mgrid[-R:R + 1, -R:R + 1]
    ox = ox.ravel()
    oy = oy.ravel()
    K = len(ox)
    pos = 0
    while pos < N:
        # chunk of strokes with similar length
        L0 = length[order[pos]]
        T = int(math.ceil(max(L0 * 1.6, 2.0) / step)) + 1
        per = max(1, int(max_elems // (T * K)))
        end = min(N, pos + per)
        # limit chunk so the longest stroke is not undersampled
        Lmax_ok = (T - 1) * step * 1.05
        while end > pos + 1 and length[order[end - 1]] > Lmax_ok:
            end = pos + max(1, (end - pos) // 2)
        sel = order[pos:end]
        pos = end
        T = int(math.ceil(float(length[sel].max()) / step)) + 1
        t = np.linspace(0.0, 1.0, T, dtype=F)[None, :]
        L = length[sel][:, None]
        ca = np.cos(ang[sel])[:, None]
        sa = np.sin(ang[sel])[:, None]
        cv = curve[sel][:, None]
        wob = wave_amp[sel][:, None] * np.sin(TAU * (wave_freq[sel][:, None] * t + wave_phase[sel][:, None]))
        side = cv * L * t * t + wob
        px = x0[sel][:, None] + ca * L * t - sa * side
        py = y0[sel][:, None] + sa * L * t + ca * side
        # tangent (for the signed cross coordinate)
        dside = 2 * cv * t + wave_amp[sel][:, None] * TAU * wave_freq[sel][:, None] / np.maximum(L, 1e-3) * np.cos(
            TAU * (wave_freq[sel][:, None] * t + wave_phase[sel][:, None]))
        tx = ca - sa * dside
        ty = sa + ca * dside
        tl = np.sqrt(tx * tx + ty * ty)
        nx = -ty / tl
        ny = tx / tl
        wt = width[sel][:, None] * (1.0 - taper * t * t)
        ht = h0[sel][:, None] + (h1[sel][:, None] - h0[sel][:, None]) * t
        bx = np.floor(px).astype(np.int64)
        by = np.floor(py).astype(np.int64)
        ix = bx[:, :, None] + ox[None, None, :]
        iy = by[:, :, None] + oy[None, None, :]
        ddx = (ix + 0.5 - px[:, :, None]).astype(F)
        ddy = (iy + 0.5 - py[:, :, None]).astype(F)
        s = (ddx * nx[:, :, None] + ddy * ny[:, :, None]) / np.maximum(wt[:, :, None], 1e-3)
        d2 = (ddx * ddx + ddy * ddy) / np.maximum(wt[:, :, None], 1e-3) ** 2
        m = d2 < 1.0
        if not m.any():
            continue
        prof = np.sqrt(np.maximum(1.0 - s * s, 0.0))
        h = ht[:, :, None] - relief * (1.0 - prof)
        k = len(sel)
        shape = (k, T, K)
        zb.add(ix[m], iy[m], h[m], np.broadcast_to(ids[sel][:, None, None], shape)[m],
               [np.broadcast_to(t[:, :, None], shape)[m], np.clip(s, -1, 1)[m]])


def blobs(n, cx, cy, rx, ry, ang=0.0, seed=0, irr=0.15, hscale=1.0, zb=None, id0=0, profile=0.5):
    """Stamp rotated, slightly irregular ellipsoids (pebbles, cinders, warts...).
    cx, cy px; rx, ry radii px; hscale = per-instance crest height. Height = hscale * (1 - r^2)^profile.
    Returns the ZBuf (payloads: u, v local coords -1..1). Read .height(), .ids(), .mask()."""
    N = len(cx)
    bc = lambda v: np.broadcast_to(np.asarray(v, F), (N,)).astype(F)
    rx, ry, ang, hscale = map(bc, (rx, ry, ang, hscale))
    r = rng(seed)
    p1 = r.uniform(0, TAU, N).astype(F)
    p2 = r.uniform(0, TAU, N).astype(F)
    if zb is None:
        zb = ZBuf(n, 2)

    def fn(sel, dx, dy):
        ca = np.cos(ang[sel])[:, None, None]
        sa = np.sin(ang[sel])[:, None, None]
        u = (dx * ca + dy * sa) / rx[sel][:, None, None]
        v = (-dx * sa + dy * ca) / ry[sel][:, None, None]
        th = np.arctan2(v, u)
        rr = np.sqrt(u * u + v * v) / (1.0 + irr * (0.6 * np.sin(2 * th + p1[sel][:, None, None])
                                                     + 0.4 * np.sin(3 * th + p2[sel][:, None, None])))
        h = np.where(rr < 1.0, hscale[sel][:, None, None] * np.maximum(1.0 - rr * rr, 0.0) ** profile, -1e9)
        return h.astype(F), [u, v]

    stamp(zb, cx, cy, np.maximum(rx, ry) * (1.0 + irr), fn, ids=np.arange(id0, id0 + N, dtype=np.int32))
    return zb


def dots(n, cx, cy, rad):
    """Nearest-dot fields: returns (d, id) with d = 0 at a dot center -> 1 at its radius (1 outside)."""
    N = len(cx)
    rad = np.broadcast_to(np.asarray(rad, F), (N,)).astype(F)
    zb = ZBuf(n, 0)

    def fn(sel, dx, dy):
        r = np.sqrt(dx * dx + dy * dy) / rad[sel][:, None, None]
        return np.where(r < 1.0, 1.0 - r, -1e9).astype(F), []

    stamp(zb, cx, cy, rad, fn)
    return (1.0 - zb.height(0.0)).astype(F), zb.ids()


def wrapd(a):
    """Wrapped difference of tile coordinates -> [-0.5, 0.5)."""
    return np.mod(a + 0.5, 1.0) - 0.5


# ----------------------------------------------------------------------------- height -> normal / ao
def normal_from_height(H, strength=1.0):
    """Wrapped Sobel. H in pixels of displacement. Returns unit normals (n, n, 3), +Y = up in the image."""
    H = np.asarray(H, F)
    l = np.roll(H, 1, 1)
    r = np.roll(H, -1, 1)
    gx = (2.0 * (r - l) + (np.roll(r, 1, 0) - np.roll(l, 1, 0)) + (np.roll(r, -1, 0) - np.roll(l, -1, 0))) / 8.0
    u = np.roll(H, 1, 0)      # row above
    d = np.roll(H, -1, 0)     # row below
    gy = (2.0 * (d - u) + (np.roll(d, 1, 1) - np.roll(u, 1, 1)) + (np.roll(d, -1, 1) - np.roll(u, -1, 1))) / 8.0
    nx = -gx * strength
    ny = gy * strength          # image rows grow downwards, +Y points up
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
    return np.stack([nx * inv, ny * inv, nz * inv], -1).astype(F)


def ao_from_height(H, radii=(2.0, 6.0, 18.0), strength=1.0, weights=None):
    """Cheap cavity AO: how far the surface sits below its blurred neighbourhood, at several radii.
    H in pixels. Returns 0..1 (1 = open)."""
    occ = np.zeros_like(H, F)
    weights = weights or [1.0] * len(radii)
    for r, w in zip(radii, weights):
        occ += w * np.clip((blur(H, r) - H) / r, 0.0, None)
    occ = 1.0 - np.exp(-occ * strength * 1.6)
    return (1.0 - occ).astype(F)


def cavity(H, r=3.0):
    """Signed convexity (positive on convex edges / tops, negative in creases), in pixels."""
    return (H - blur(H, r)).astype(F)


def balance(img, sigma_frac=0.22, amount=0.8):
    """Remove the very low frequencies of an image (so a 4x4 tiling shows no big repeating blotch)."""
    n = img.shape[0]
    low = blur(img, sigma_frac * n)
    mean = low.mean(axis=(0, 1), keepdims=True)
    return (img - (low - mean) * amount).astype(F)


# ----------------------------------------------------------------------------- output
MM_PER_PX = {}


def down(a, f):
    """Box downsample by an integer factor."""
    if f == 1:
        return a
    h, w = a.shape[:2]
    h2, w2 = h // f, w // f
    a = a[:h2 * f, :w2 * f]
    if a.ndim == 2:
        return a.reshape(h2, f, w2, f).mean((1, 3)).astype(F)
    return a.reshape(h2, f, w2, f, a.shape[2]).mean((1, 3)).astype(F)


def tile(a, k):
    return np.tile(a, (k, k) + ((1,) if a.ndim == 3 else ()))


def lit_render(alb, nrm, rough, ao, light=(-0.52, 0.55, 0.65)):
    """Top-down lit preview: Lambert + GGX-ish specular + faint sky reflection. Light from the upper left.
    alb sRGB (n, n, 3), nrm unit normals, rough / ao (n, n). Returns sRGB."""
    L = np.array(light, F)
    L /= np.linalg.norm(L)
    V = np.array([0, 0, 1], F)
    Hh = L + V
    Hh /= np.linalg.norm(Hh)
    a = srgb2lin(alb)
    ndl = np.clip(nrm @ L, 0.0, 1.0)
    ndh = np.clip(nrm @ Hh, 0.0, 1.0)
    diff = a * ((0.30 * ao + 1.0 * ndl)[..., None]) / (0.30 + L[2])
    al = np.clip(rough, 0.06, 1.0) ** 2
    D = al * al / (math.pi * (ndh * ndh * (al * al - 1.0) + 1.0) ** 2)
    spec = np.minimum(0.04 * D * ndl * 0.6, 1.2)
    env = 0.10 * (1.0 - rough) ** 2 * ao * np.clip(nrm[..., 2], 0, 1) ** 6
    out = diff + spec[..., None] + env[..., None] * np.array([0.8, 0.9, 1.0], F)
    return lin2srgb(np.clip(out, 0.0, 1.0))


def read_png(path):
    """Decode an 8-bit PNG written by blcommon.save_png (filter 0 only). Returns uint8 (h, w, c)."""
    with open(path, 'rb') as f:
        data = f.read()
    pos = 8
    idat = b''
    w = h = c = 0
    while pos < len(data):
        ln, tag = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if tag == b'IHDR':
            w, h, bd, ct = struct.unpack('>IIBB', body[:10])
            c = {0: 1, 4: 2, 2: 3, 6: 4}[ct]
        elif tag == b'IDAT':
            idat += body
        pos += 12 + ln
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, w * c + 1)
    assert (raw[:, 0] == 0).all(), 'unsupported PNG filter'
    return raw[:, 1:].reshape(h, w, c).copy()


def seam_score(a):
    """Ratio of the wrap-around discontinuity to the typical neighbour difference (~1 = seamless)."""
    a = np.asarray(a, F)
    dx_in = np.abs(a[:, 1:] - a[:, :-1]).mean()
    dx_w = np.abs(a[:, 0] - a[:, -1]).mean()
    dy_in = np.abs(a[1:] - a[:-1]).mean()
    dy_w = np.abs(a[0] - a[-1]).mean()
    return float(dx_w / (dx_in + 1e-9)), float(dy_w / (dy_in + 1e-9))


def decode_tex(name):
    """Load <name>_a/_n PNGs back -> (albedo sRGB, height, normal unit vectors, rough, ao)."""
    a = read_png(os.path.join(TEXTURES, name + '_a.png')).astype(F) / 255.0
    nn = read_png(os.path.join(TEXTURES, name + '_n.png')).astype(F) / 255.0
    nx = nn[..., 0] * 2 - 1
    ny = nn[..., 1] * 2 - 1
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0.0, 1.0))
    return a[..., :3], a[..., 3], np.stack([nx, ny, nz], -1), nn[..., 2], nn[..., 3]


def preview_panels(name):
    """(albedo 512, lit 3x3 tiled 512, lit 1:1 crop 512) from the files on disk."""
    alb, hgt, nrm, rough, ao = decode_tex(name)
    n = alb.shape[0]
    lit = lit_render(alb, nrm, rough, ao)
    p_alb = down(alb, n // 512)
    f = (3 * n) // 512
    p_lit = down(tile(lit, 3), f)[:512, :512]
    if n > 512:
        o = n // 4
        p_crop = lit[o:o + 512, o:o + 512]
    else:
        p_crop = lit
    return p_alb, p_lit, p_crop


def save_tex(name, alb, H, rough, ao=None, nscale=1.0, height=None, tile_m=1.0, nblur=0.0, ao_strength=1.0,
             ao_radii=(2.0, 6.0, 18.0), alb_range=(26, 235), preview=True):
    """Write <name>_a.png (sRGB albedo + height in alpha) and <name>_n.png (normal xy, roughness, ao).
    alb: sRGB (n, n, 3). H: height in pixels (source of the normal map). height: optional 0..1 blend
    height for the alpha channel (default: H normalised with robust percentiles)."""
    t0 = time.time()
    n = alb.shape[0]
    H = np.asarray(H, F)
    Hn = blur(H, nblur) if nblur > 0 else H
    nrm = normal_from_height(Hn, nscale)
    if ao is None:
        ao = ao_from_height(H * nscale, ao_radii, ao_strength)
    if height is None:
        height = norm01(H, 0.3, 99.7)
    height = np.clip(height, 8.0 / 255.0, 1.0)
    lo, hi = alb_range[0] / 255.0, alb_range[1] / 255.0
    alb = np.clip(alb, lo, hi)
    A = np.concatenate([alb, height[..., None]], -1)
    N = np.stack([nrm[..., 0] * 0.5 + 0.5, nrm[..., 1] * 0.5 + 0.5, sat(rough), sat(ao)], -1)
    save_png(os.path.join(TEXTURES, name + '_a.png'), A)
    save_png(os.path.join(TEXTURES, name + '_n.png'), N)
    sa = seam_score(luma(alb))
    sn = seam_score(nrm[..., 0])
    sh = seam_score(height)
    m = alb.reshape(-1, 3).mean(0) * 255
    print('WROTE %s %dpx tile=%.1fm  albedo avg=(%d,%d,%d) min=%d max=%d  rough avg=%.2f [%.2f..%.2f]  ao avg=%.2f '
          'nz avg=%.3f p05=%.3f  seam(alb)=%.2f/%.2f seam(nrm)=%.2f/%.2f seam(h)=%.2f/%.2f  (%.1fs)' % (
              name, n, tile_m, m[0], m[1], m[2], alb.min() * 255, alb.max() * 255, rough.mean(),
              np.percentile(rough, 1), np.percentile(rough, 99), ao.mean(), nrm[..., 2].mean(),
              np.percentile(nrm[..., 2], 5), sa[0], sa[1], sn[0], sn[1], sh[0], sh[1], time.time() - t0))
    if preview:
        write_preview(name)


def write_preview(name):
    p = preview_panels(name)
    path = os.path.join(PREVIEWS, 'tex_%s.png' % name)
    save_png(path, montage(list(p), cols=3, pad=4))
    print('PREVIEW', path)


def run(table):
    """table: {name: function}. Command line: blender ... -P script.py -- [name ...] (default: all)."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    names = [a for a in args if a in table] or list(table.keys())
    for nm in names:
        t0 = time.time()
        table[nm]()
        print('TIME %s %.1fs' % (nm, time.time() - t0))
