"""VALOMBRE world generator: 5120 m x 5120 m island (~20 km2 of land).
Outputs (assets/world): height.bin (uint16), splat0.png, splat1.png, terrain_nrm.png, biome.png,
veg.png, tint.png, map.png, world.json.   Run through Blender's python (numpy):
  blender -b --factory-startup -P tools/blender/world_gen.py
Axes: +X = east, +Z = south (north is -Z), Y up. Grid vertex (i, j) -> x = -2560 + i*2.5, z = -2560 + j*2.5.
"""
import sys, os, json, math, heapq, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from blcommon import save_png, ASSETS, PREVIEWS

T0 = time.time()
OUT = os.path.join(ASSETS, 'world')
os.makedirs(OUT, exist_ok=True)
N = 2048
SIZE = 5120.0
CELL = SIZE / N
HALF = SIZE / 2
M = 1024            # macro / erosion resolution
MC = SIZE / M
SEED = 7131
rng = np.random.default_rng(SEED)


def log(*a):
    print('[world %.1fs]' % (time.time() - T0), *a)
    sys.stdout.flush()


def S(a, b, v):
    t = np.clip((v - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Noise:
    def __init__(self, seed, size=256):
        r = np.random.default_rng(seed)
        ang = r.random((size, size)) * 2 * np.pi
        self.gx = np.cos(ang).astype(np.float32)
        self.gy = np.sin(ang).astype(np.float32)
        self.n = size

    def at(self, x, y):
        n = self.n
        x0 = np.floor(x)
        y0 = np.floor(y)
        fx = (x - x0).astype(np.float32)
        fy = (y - y0).astype(np.float32)
        ix = x0.astype(np.int64) % n
        iy = y0.astype(np.int64) % n
        ix1 = (ix + 1) % n
        iy1 = (iy + 1) % n
        gx, gy = self.gx, self.gy
        n00 = gx[iy, ix] * fx + gy[iy, ix] * fy
        n10 = gx[iy, ix1] * (fx - 1) + gy[iy, ix1] * fy
        n01 = gx[iy1, ix] * fx + gy[iy1, ix] * (fy - 1)
        n11 = gx[iy1, ix1] * (fx - 1) + gy[iy1, ix1] * (fy - 1)
        u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
        v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
        a = n00 + (n10 - n00) * u
        b = n01 + (n11 - n01) * u
        return (a + (b - a) * v) * 1.5


def fbm(noise, x, y, wavelength, octaves=5, gain=0.5, lac=2.0, ridged=False, offset=0.0):
    f = 1.0 / wavelength
    amp = 1.0
    tot = 0.0
    norm = 0.0
    for o in range(octaves):
        v = noise.at(x * f + o * 17.3 + offset, y * f + o * 31.7 + offset * 1.7)
        if ridged:
            v = 1.0 - np.abs(v)
            v = v * v
        tot = tot + v * amp
        norm += amp
        amp *= gain
        f *= lac
    return tot / norm


def blur(a, it=1):
    for _ in range(it):
        a = (np.roll(a, 1, 0) + np.roll(a, -1, 0) + 2 * a) * 0.25
        a = (np.roll(a, 1, 1) + np.roll(a, -1, 1) + 2 * a) * 0.25
    return a


def resize(a, n):
    """bilinear resize of a square array to n x n (vertex aligned)."""
    m = a.shape[0]
    t = np.arange(n, dtype=np.float32) * ((m - 1) / (n - 1))
    i0 = np.clip(np.floor(t).astype(np.int64), 0, m - 2)
    f = (t - i0).astype(np.float32)
    a = a[i0] * (1 - f)[:, None] + a[i0 + 1] * f[:, None]
    a = a[:, i0] * (1 - f)[None, :] + a[:, i0 + 1] * f[None, :]
    return a.astype(np.float32)


def sample(a, x, z):
    """bilinear sample of a grid covering the world at world coords (arrays or scalars)."""
    n = a.shape[0]
    c = SIZE / n
    fx = np.clip((np.asarray(x, np.float64) + HALF) / c, 0, n - 1.001)
    fz = np.clip((np.asarray(z, np.float64) + HALF) / c, 0, n - 1.001)
    i = np.floor(fx).astype(np.int64)
    j = np.floor(fz).astype(np.int64)
    u = fx - i
    v = fz - j
    return (a[j, i] * (1 - u) * (1 - v) + a[j, i + 1] * u * (1 - v) + a[j + 1, i] * (1 - u) * v + a[j + 1, i + 1] * u * v)


# ============================================================================= design data
POIS = [
    # id, type, name, x, z, radius, flatten strength
    dict(id='hautefeuille', type='village', name='Hautefeuille', x=-150, z=1450, r=115, flat=0.92),
    dict(id='port_brisants', type='hamlet', name='Port-Brisants', x=1420, z=1790, r=70, flat=0.85),
    dict(id='refuge', type='camp', name='Refuge des Veilleurs', x=-1180, z=300, r=45, flat=0.85),
    dict(id='roc_au_vent', type='hamlet', name='Roc-au-Vent', x=-620, z=-1230, r=62, flat=0.9),
    dict(id='vieux_gue', type='ruin_village', name='Vieux-Gué', x=1250, z=350, r=75, flat=0.8, minh=1.1),
    dict(id='camp_ecorcheurs', type='bandit_camp', name='Camp des Écorcheurs', x=560, z=1180, r=42, flat=0.85),
    dict(id='boss_wolf', type='arena', name='Tanière de Croc-Blême', x=-860, z=860, r=34, flat=0.95, boss='wolf'),
    dict(id='boss_spider', type='arena', name="Nid d'Arakha", x=-1800, z=-150, r=42, flat=0.95, boss='spider'),
    dict(id='boss_knight', type='arena', name='Chapelle Engloutie', x=1800, z=-120, r=38, flat=0.95, boss='knight', minh=0.9),
    dict(id='boss_colossus', type='arena', name='Lac de Givre', x=-150, z=-1930, r=50, flat=1.0, boss='colossus'),
    dict(id='boss_priestess', type='arena', name='Autel de la Caldeira', x=1520, z=-1480, r=44, flat=0.97, boss='priestess'),
    dict(id='boss_king', type='arena', name="Salle du Trône d'Aubeclair", x=0, z=-250, r=44, flat=1.0, boss='king'),
    dict(id='citadel_court', type='citadel', name="Citadelle d'Aubeclair", x=0, z=-110, r=60, flat=1.0),
]
SHRINES = [
    ('s_hautefeuille', 'Autel de Hautefeuille', -118, 1418),
    ('s_port', 'Autel de Port-Brisants', 1385, 1765),
    ('s_refuge', 'Autel du Refuge', -1165, 318),
    ('s_roc', 'Autel de Roc-au-Vent', -600, -1210),
    ('s_croisee', 'Autel de la Croisée', -40, 905),
    ('s_gue', 'Autel du Vieux-Gué', 1130, 470),
    ('s_ronces', 'Autel des Ronces', -1600, -40),
    ('s_fange', 'Autel de Fangemort', 1660, 40),
    ('s_givre', 'Autel du Col de Givre', -390, -1680),
    ('s_cendres', 'Autel des Cendres', 1120, -560),
    ('s_caldeira', 'Autel de la Caldeira', 1400, -1300),
    ('s_porte', 'Autel de la Porte Royale', 22, 95),
    ('s_laniere', 'Autel du Louvetier', -760, 760),
    ('s_cote_ouest', 'Autel des Falaises', -2050, 900),
]
# roads: waypoints refined by A*
ROADS = [
    dict(id='r_citadelle', w=4.5, pts=[(-150, 1450), (-40, 900), (0, 380)]),
    dict(id='r_rampe', w=5.0, pts=[(0, 380), (0, 40), (0, -60)], straight=True),
    dict(id='r_foret', w=3.6, pts=[(-40, 900), (-590, 520), (-1180, 300), (-1560, -20), (-1800, -150)]),
    dict(id='r_port', w=4.0, pts=[(-150, 1450), (600, 1640), (1420, 1790)]),
    dict(id='r_marais', w=3.6, pts=[(-40, 900), (560, 860), (1250, 350), (1620, 40), (1800, -120)]),
    dict(id='r_camp', w=2.6, pts=[(560, 860), (560, 1180)]),
    dict(id='r_nord', w=3.6, pts=[(0, 380), (-320, 60), (-290, -640), (-330, -1000), (-620, -1230), (-400, -1680), (-150, -1930)]),
    dict(id='r_ouest', w=3.0, pts=[(-150, 1450), (-600, 1400), (-1300, 1330), (-2030, 900)]),
    dict(id='r_cendres', w=3.4, pts=[(1250, 350), (1120, -540), (1400, -1280), (1520, -1480)]),
    dict(id='r_loup', w=2.4, pts=[(-690, 540), (-860, 860)]),
]
RIVER = [(-380, -900), (-470, -650), (-560, -380), (-640, -80), (-610, 300), (-590, 520), (-530, 900),
         (-600, 1400), (-760, 1900), (-880, 2300), (-900, 2540)]
CITADEL = (0.0, -180.0)

# ============================================================================= macro heights (1024)
log('macro heights')
ax = (-HALF + np.arange(M, dtype=np.float32) * (SIZE / (M - 1)))
X, Z = np.meshgrid(ax, ax)
nA, nB, nC, nD, nE, nF = [Noise(SEED + k) for k in range(6)]
wx = X + 230 * fbm(nA, X, Z, 950, 3)
wz = Z + 230 * fbm(nB, X, Z, 950, 3, offset=50)

p = 4.0
R_ISLAND = 2420.0
d = (np.abs(wx / R_ISLAND) ** p + np.abs(wz / R_ISLAND) ** p) ** (1 / p)
d = d + 0.045 * fbm(nC, X, Z, 520, 4)
# two bays (south-east harbour, west cove)
d = d + 0.16 * np.exp(-(((X - 1650) / 260) ** 2 + ((Z - 2150) / 300) ** 2))
d = d + 0.13 * np.exp(-(((X + 2350) / 280) ** 2 + ((Z - 500) / 230) ** 2))
land = S(1.03, 0.90, d)

wxb = wx + 160 * fbm(nC, X, Z, 300, 3, offset=13)
wzb = wz + 160 * fbm(nD, X, Z, 300, 3, offset=14)
ash = S(1.06, 0.74, np.hypot((wxb - 1520) / 1180, (wzb + 1560) / 1060))
mount = S(-740, -1360, wzb) * (1 - ash)
swamp = S(1.06, 0.70, np.hypot((wxb - 1520) / 720, (wzb - 330) / 860))
forest = S(1.06, 0.78, np.hypot((wxb + 1520) / 1080, (wzb - 150) / 1330)) * (1 - mount)
cd = np.hypot(X - CITADEL[0], Z - CITADEL[1])
citadel_zone = S(420, 260, cd)
forest = forest * (1 - citadel_zone)
swamp = swamp * (1 - ash)

base = 21 + 13 * fbm(nA, X, Z, 640, 4, offset=9) + 3.5 * fbm(nB, X, Z, 130, 3, offset=3)
moor = np.exp(-(((X - 880) / 620) ** 2 + ((Z - 1480) / 400) ** 2))
base = base + moor * (14 + 22 * (0.5 + 0.5 * fbm(nC, X, Z, 260, 4, offset=61)))
knoll = S(0.28, 0.6, fbm(nE, X, Z, 340, 3, offset=71))
base = base + 16 * knoll * (1 - moor)
hills = forest * (12 + 30 * (0.5 + 0.5 * fbm(nC, wx, wz, 430, 5, offset=7)))
ridge = fbm(nD, wx, wz, 760, 6, gain=0.5, ridged=True)
peak = np.exp(-(((X + 100) / 1500) ** 2 + ((Z + 2050) / 820) ** 2))
mh = mount * (38 + 430 * (ridge ** 1.45) * (0.32 + 0.68 * peak))
ah = 42 + 46 * fbm(nE, wx, wz, 420, 5, ridged=True)
cal = np.hypot(X - 1520, Z + 1480)
ah = ah + 78 * np.exp(-((cal - 255) / 85) ** 2) - 16 * S(235, 110, cal)
elev = base + hills + mh + ash * ah
sw_h = 0.75 + 2.1 * fbm(nD, X, Z, 95, 4, offset=21) + 0.7 * fbm(nE, X, Z, 26, 2, offset=4)
elev = elev * (1 - swamp) + sw_h * swamp

# citadel plateau with a causeway ramp on the south side
cn = cd + 26 * fbm(nB, X, Z, 140, 3, offset=77)
plateau = 58 * S(275, 208, cn)
ramp_t = S(380, 45, Z)
corridor = S(36, 13, np.abs(X)) * S(-40, 30, Z)
plateau = np.maximum(plateau, 58 * ramp_t * corridor * S(420, 380, Z))
elev = elev + plateau

t = land
h_sea = -30 + 29 * S(0.0, 0.42, t)
h_beach = -1 + 3.6 * S(0.42, 0.63, t)
k = S(0.63, 1.0, t)
H = np.where(t < 0.42, h_sea, np.where(t < 0.63, h_beach, 2.6 + (elev - 2.6) * k)).astype(np.float32)
H = np.where(t >= 0.63, np.maximum(H, np.minimum(elev, 2.6 * (1 - swamp) + elev * swamp)), H).astype(np.float32)

# ============================================================================= hydraulic erosion (batched droplets)
def erode(H, drops=900000, batch=100000, steps=34, inertia=0.06, capacity=4.0, min_slope=0.01, deposit=0.3,
          erosion=0.3, evap=0.012, gravity=4.0, scale=100.0):
    n = H.shape[0]
    Hn = (H / scale).astype(np.float64)
    r = np.random.default_rng(SEED + 99)
    for b in range(drops // batch):
        px = r.random(batch) * (n - 4) + 2
        py = r.random(batch) * (n - 4) + 2
        dx = np.zeros(batch)
        dy = np.zeros(batch)
        speed = np.ones(batch)
        water = np.ones(batch)
        sed = np.zeros(batch)
        alive = Hn[py.astype(np.int64), px.astype(np.int64)] > 0.01
        for s in range(steps):
            ix = px.astype(np.int64)
            iy = py.astype(np.int64)
            fx = px - ix
            fy = py - iy
            h00 = Hn[iy, ix]
            h10 = Hn[iy, ix + 1]
            h01 = Hn[iy + 1, ix]
            h11 = Hn[iy + 1, ix + 1]
            gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
            gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
            hold = h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy) + h01 * (1 - fx) * fy + h11 * fx * fy
            dx = dx * inertia - gx * (1 - inertia)
            dy = dy * inertia - gy * (1 - inertia)
            l = np.sqrt(dx * dx + dy * dy) + 1e-12
            dx /= l
            dy /= l
            npx = px + dx
            npy = py + dy
            alive &= (npx >= 2) & (npx < n - 3) & (npy >= 2) & (npy < n - 3) & (hold > -0.01)
            npx = np.where(alive, npx, px)
            npy = np.where(alive, npy, py)
            jx = npx.astype(np.int64)
            jy = npy.astype(np.int64)
            ux = npx - jx
            uy = npy - jy
            hnew = (Hn[jy, jx] * (1 - ux) * (1 - uy) + Hn[jy, jx + 1] * ux * (1 - uy)
                    + Hn[jy + 1, jx] * (1 - ux) * uy + Hn[jy + 1, jx + 1] * ux * uy)
            dh = hnew - hold
            cap = np.maximum(-dh, min_slope) * speed * water * capacity
            dep = np.where(dh > 0, np.minimum(dh, sed), np.where(sed > cap, (sed - cap) * deposit, 0.0))
            ero = np.where((dh <= 0) & (sed <= cap), np.minimum((cap - sed) * erosion, -dh), 0.0)
            delta = (dep - ero) * alive
            sed = sed + (ero - dep) * alive
            D = np.zeros_like(Hn)
            np.add.at(D, (iy, ix), delta * (1 - fx) * (1 - fy))
            np.add.at(D, (iy, ix + 1), delta * fx * (1 - fy))
            np.add.at(D, (iy + 1, ix), delta * (1 - fx) * fy)
            np.add.at(D, (iy + 1, ix + 1), delta * fx * fy)
            Hn += np.clip(blur(D, 1), -0.0012, 0.0012)
            speed = np.sqrt(np.maximum(speed * speed - dh * gravity, 0.01))
            water *= (1 - evap)
            px, py = npx, npy
    return (Hn * scale).astype(np.float32)


log('erosion')
H0 = H.copy()
He = erode(H)
# keep erosion mostly on slopes/uplands, protect beaches & swamp flats from noise
ero_mask = S(3.0, 12.0, H0) * (1 - swamp)
He = np.clip(He, H0 - 16.0, H0 + 10.0)
H = (H0 + (He - H0) * ero_mask).astype(np.float32)
H = (H * 0.75 + blur(H, 1) * 0.25).astype(np.float32)

# ============================================================================= upsample to 2048 + detail
log('upsample')
H = resize(H, N)
ax2 = (-HALF + np.arange(N, dtype=np.float32) * CELL)
X2, Z2 = np.meshgrid(ax2, ax2)
mount2, ash2, swamp2, forest2, land2 = [resize(a.astype(np.float32), N) for a in (mount, ash, swamp, forest, land)]
gy_, gx_ = np.gradient(H, CELL)
slope0 = np.sqrt(gx_ ** 2 + gy_ ** 2)
detail = fbm(nF, X2, Z2, 34, 4, gain=0.55) * (0.5 + 2.2 * S(0.15, 0.7, slope0) + 1.2 * mount2 + 0.9 * ash2)
detail += 0.35 * fbm(nA, X2, Z2, 9, 2, offset=5) * (0.3 + S(0.2, 0.8, slope0))
H = (H + detail * S(1.5, 6.0, H) * (1 - 0.8 * swamp2)).astype(np.float32)


def stamp_flat(H, x, z, r, strength, target=None, minh=None):
    i0 = max(int((x - r * 2 + HALF) / CELL), 0)
    i1 = min(int((x + r * 2 + HALF) / CELL) + 2, N)
    j0 = max(int((z - r * 2 + HALF) / CELL), 0)
    j1 = min(int((z + r * 2 + HALF) / CELL) + 2, N)
    sub = H[j0:j1, i0:i1]
    dd = np.hypot(X2[j0:j1, i0:i1] - x, Z2[j0:j1, i0:i1] - z)
    w = S(r * 1.75, r * 0.95, dd) * strength
    if target is None:
        core = dd < r
        target = float(sub[core].mean())
    if minh is not None:
        target = max(target, minh)
    H[j0:j1, i0:i1] = sub * (1 - w) + target * w
    return target


log('snap coastal POIs')
Hs = blur(H, 3)
for P in POIS:
    if P['id'] != 'port_brisants':
        continue
    best = None
    for dx in range(-700, 701, 20):
        for dz in range(-700, 701, 20):
            x, z = P['x'] + dx, P['z'] + dz
            if abs(x) > 2450 or abs(z) > 2450:
                continue
            hh = float(sample(Hs, x, z))
            if 3.0 < hh < 5.5:
                # must have sea within 90 m
                near = min(float(sample(Hs, x + ox, z + oz)) for ox, oz in ((90, 0), (-90, 0), (0, 90), (0, -90), (64, 64), (-64, 64), (64, -64), (-64, -64)))
                if near < 0.0:
                    sc = math.hypot(dx, dz)
                    if best is None or sc < best[0]:
                        best = (sc, x, z)
    if best:
        old = (P['x'], P['z'])
        P['x'], P['z'] = best[1], best[2]
        log('  port snapped to', best[1], best[2])
        for R in ROADS:
            R['pts'] = [((P['x'], P['z']) if tuple(q) == old else q) for q in R['pts']]
        SHRINES = [((s[0], s[1], P['x'] - 30, P['z'] - 22) if s[0] == 's_port' else s) for s in SHRINES]
log('flatten POIs')
for P in POIS:
    P['y'] = round(stamp_flat(H, P['x'], P['z'], P['r'], P['flat'], minh=P.get('minh')), 2)
# citadel: whole top is one level
ctop = stamp_flat(H, CITADEL[0], CITADEL[1], 150, 1.0)
for P in POIS:
    if P['id'] in ('boss_king', 'citadel_court'):
        P['y'] = round(ctop, 2)

# ============================================================================= river
def polyline_resample(pts, step):
    pts = np.asarray(pts, np.float64)
    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    L = np.concatenate([[0], np.cumsum(seg)])
    n = max(int(L[-1] / step), 2)
    s = np.linspace(0, L[-1], n)
    return np.stack([np.interp(s, L, pts[:, 0]), np.interp(s, L, pts[:, 1])], 1)


def chaikin(pts, it=2):
    pts = np.asarray(pts, np.float64)
    for _ in range(it):
        q = pts[:-1] * 0.75 + pts[1:] * 0.25
        r = pts[:-1] * 0.25 + pts[1:] * 0.75
        mid = np.empty((len(q) * 2, 2))
        mid[0::2] = q
        mid[1::2] = r
        pts = np.concatenate([pts[:1], mid, pts[-1:]])
    return pts


def meander(pts, amp, wl, seed):
    pts = polyline_resample(pts, 12.0)
    tng = np.gradient(pts, axis=0)
    tng /= (np.linalg.norm(tng, axis=1, keepdims=True) + 1e-9)
    nrm = np.stack([-tng[:, 1], tng[:, 0]], 1)
    s = np.arange(len(pts)) * 12.0
    r = np.random.default_rng(seed)
    off = np.zeros(len(pts))
    for kk in range(3):
        off += amp / (kk + 1) * np.sin(s / (wl / (kk + 1)) * 2 * np.pi + r.random() * 6.28)
    fade = np.minimum(1, np.minimum(s, s[::-1]) / 120.0)
    return pts + nrm * (off * fade)[:, None]


def carve_path(H, pts, heights, core, outer, paint=None, paint_val=1.0, only_lower=False):
    """Blend the terrain toward `heights` along a polyline. core = full-strength half width, outer = falloff end."""
    rc = int(outer / CELL) + 2
    for (x, z), hh in zip(pts, heights):
        ci = int(round((x + HALF) / CELL))
        cj = int(round((z + HALF) / CELL))
        i0, i1, j0, j1 = max(ci - rc, 0), min(ci + rc + 1, N), max(cj - rc, 0), min(cj + rc + 1, N)
        if i0 >= i1 or j0 >= j1:
            continue
        dd = np.hypot(X2[j0:j1, i0:i1] - x, Z2[j0:j1, i0:i1] - z)
        w = S(outer, core, dd)
        sub = H[j0:j1, i0:i1]
        tgt = np.minimum(sub, hh) if only_lower else hh
        H[j0:j1, i0:i1] = sub * (1 - w) + tgt * w
        if paint is not None:
            pw = S(core * 1.25, core * 0.7, dd) * paint_val
            paint[j0:j1, i0:i1] = np.maximum(paint[j0:j1, i0:i1], pw)


log('river')
riv = chaikin(meander(RIVER, 34.0, 420.0, 5), 1)
riv = polyline_resample(riv, 2.0)
rh_raw = sample(H, riv[:, 0], riv[:, 1])
cut = len(riv)
for kk in range(len(riv) // 3, len(riv)):
    if rh_raw[kk] < -1.0:
        cut = min(kk + 12, len(riv))
        break
riv = riv[:cut]
rh = sample(blur(H, 6), riv[:, 0], riv[:, 1])
# water surface: non-increasing downstream, smoothed, reaching the sea
surf = np.minimum.accumulate(rh - 1.2)
kern = np.ones(81) / 81
surf = np.convolve(np.pad(surf, 40, mode='edge'), kern, mode='valid')
surf = np.minimum.accumulate(surf)
surf = np.maximum(surf, 0.0)
river_mask = np.zeros((N, N), np.float32)
RIVER_W = 9.0
# 1) a broad, gentle valley so that the banks are natural slopes instead of a trench
valley = np.full((N, N), 1e9, np.float32)
for (x, z), hh in zip(riv[::6], (surf + 1.6)[::6]):
    ci = int(round((x + HALF) / CELL)); cj = int(round((z + HALF) / CELL)); rc = int(230 / CELL)
    i0, i1, j0, j1 = max(ci - rc, 0), min(ci + rc + 1, N), max(cj - rc, 0), min(cj + rc + 1, N)
    dd = np.hypot(X2[j0:j1, i0:i1] - x, Z2[j0:j1, i0:i1] - z)
    # allowed height grows with the distance to the river: flat floor 16 m, then ~8 degree slopes easing out
    allowed = hh + np.maximum(dd - 16.0, 0.0) ** 1.25 * 0.085
    valley[j0:j1, i0:i1] = np.minimum(valley[j0:j1, i0:i1], allowed)
H = np.minimum(H, valley).astype(np.float32)
# 2) the channel itself
carve_path(H, riv[::2], (surf - 1.5)[::2], RIVER_W * 0.5, RIVER_W * 0.5 + 9.0, paint=river_mask, only_lower=True)
river_json = [[round(float(x), 1), round(float(z), 1), round(float(y), 2)] for (x, z), y in zip(riv[::6], surf[::6])]

# ============================================================================= roads (A* on a 10 m grid)
log('roads')
G = 512
GC = SIZE / G
Hc = resize(blur(H, 2), G)
gyc, gxc = np.gradient(Hc, GC)
slc = np.sqrt(gxc ** 2 + gyc ** 2)
rivc = resize(blur(river_mask, 2), G)
cost_map = 1.0 + 55.0 * slc ** 2 + 30.0 * slc + np.where(Hc < 0.6, 40.0, 0.0) + 9.0 * rivc


def astar(a, b):
    def cell(p):
        return (int(np.clip((p[0] + HALF) / GC, 1, G - 2)), int(np.clip((p[1] + HALF) / GC, 1, G - 2)))
    s, e = cell(a), cell(b)
    openq = [(0.0, s)]
    g = {s: 0.0}
    came = {}
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while openq:
        f, c = heapq.heappop(openq)
        if c == e:
            break
        gc = g[c]
        if f > gc + math.hypot(c[0] - e[0], c[1] - e[1]) + 1e-6:
            continue
        for dx, dy, dl in nb:
            n2 = (c[0] + dx, c[1] + dy)
            if not (1 <= n2[0] < G - 1 and 1 <= n2[1] < G - 1):
                continue
            dz = abs(Hc[n2[1], n2[0]] - Hc[c[1], c[0]]) / (GC * dl)
            ng = gc + dl * (cost_map[n2[1], n2[0]] + 70.0 * dz * dz)
            if ng < g.get(n2, 1e18):
                g[n2] = ng
                came[n2] = c
                heapq.heappush(openq, (ng + math.hypot(n2[0] - e[0], n2[1] - e[1]), n2))
    path = [e]
    while path[-1] != s:
        path.append(came[path[-1]])
    path.reverse()
    return [(-HALF + (i + 0.5) * GC, -HALF + (j + 0.5) * GC) for i, j in path]


road_mask = np.zeros((N, N), np.float32)
roads_json = []
bridges = []
for R in ROADS:
    pts = []
    wp = R['pts']
    for a, b in zip(wp[:-1], wp[1:]):
        seg = [a, b] if R.get('straight') else [a] + astar(a, b)[1:-1] + [b]
        pts += seg if not pts else seg[1:]
    pts = polyline_resample(chaikin(polyline_resample(pts, 30.0), 3), 1.5)
    R['poly'] = pts
# bridges where roads cross the river
def seg_inter(p, p2, q, q2):
    r = p2 - p
    s = q2 - q
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return None
    t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
    u = ((q[0] - p[0]) * r[1] - (q[1] - p[1]) * r[0]) / den
    if 0 <= t <= 1 and 0 <= u <= 1:
        return p + r * t, u
    return None

rivc_pts = riv[::8]
for R in ROADS:
    pts = R['poly']
    skip = np.zeros(len(pts), bool)
    step = 6
    for a in range(0, len(pts) - step, step):
        for b in range(len(rivc_pts) - 1):
            if abs(pts[a][0] - rivc_pts[b][0]) > 60 or abs(pts[a][1] - rivc_pts[b][1]) > 60:
                continue
            res = seg_inter(pts[a], pts[a + step], rivc_pts[b], rivc_pts[b + 1])
            if res is None:
                continue
            pt, u = res
            k0 = b * 8 + int(u * 8)
            ysurf = float(surf[min(k0, len(surf) - 1)])
            dirv = pts[min(a + step, len(pts) - 1)] - pts[a]
            ang = math.atan2(dirv[1], dirv[0])
            big = R['w'] >= 3.5
            bridges.append(dict(x=round(float(pt[0]), 1), z=round(float(pt[1]), 1), y=round(ysurf + 1.3, 2),
                                angle=round(ang, 4), model='bridge_stone' if big else 'bridge_wood',
                                length=14.0 if big else 10.0, road=R['id']))
            dd = np.hypot(pts[:, 0] - pt[0], pts[:, 1] - pt[1])
            skip |= dd < (8.0 if big else 6.0)
    R['skip'] = skip
# de-duplicate bridges
ub = []
for b in bridges:
    if all(math.hypot(b['x'] - o['x'], b['z'] - o['z']) > 25 for o in ub):
        ub.append(b)
bridges = ub
for R in ROADS:
    pts = R['poly']
    hh = sample(H, pts[:, 0], pts[:, 1])
    win = 31
    hs = np.convolve(np.pad(hh, win // 2, mode='edge'), np.ones(win) / win, mode='valid')
    hs = np.maximum(hs, 0.75)
    # approach ramps to bridge decks
    for b in bridges:
        dd = np.hypot(pts[:, 0] - b['x'], pts[:, 1] - b['z'])
        w = S(34.0, 9.0, dd)
        hs = hs * (1 - w) + b['y'] * w
    keep = ~R['skip']
    carve_path(H, pts[keep][::2], hs[keep][::2], R['w'] * 0.55, R['w'] * 0.55 + 7.0, paint=road_mask)
    R['heights'] = hs
    roads_json.append(dict(id=R['id'], width=R['w'], points=[[round(float(x), 1), round(float(z), 1)] for x, z in pts[::8]]))
# make sure the banks under bridge ends are at deck height
for b in bridges:
    ca, sa = math.cos(b['angle']), math.sin(b['angle'])
    for sgn in (-1, 1):
        ex = b['x'] + ca * sgn * (b['length'] * 0.5 + 2.0)
        ez = b['z'] + sa * sgn * (b['length'] * 0.5 + 2.0)
        stamp_flat(H, ex, ez, 4.0, 0.9, target=b['y'])

H = H.astype(np.float32)
# ============================================================================= derived maps
log('derived maps')
gz, gx = np.gradient(H, CELL)
slope = np.sqrt(gx ** 2 + gz ** 2)
slope_deg = np.degrees(np.arctan(slope))
nx = -gx
nz = -gz
nl = np.sqrt(nx * nx + nz * nz + 1.0)
nx /= nl
nz /= nl
# large scale AO from height difference to blurred height
Hb = H.copy()
for _ in range(3):
    Hb = blur(Hb, 6)
aoc = np.clip(1.0 + (H - Hb) * 0.035, 0.45, 1.0)
aoc = np.where(H < 0, 1.0, aoc)
nrm_img = np.stack([nx * 0.5 + 0.5, nz * 0.5 + 0.5, aoc, np.ones_like(aoc)], -1)
save_png(os.path.join(OUT, 'terrain_nrm.png'), nrm_img)

n1 = fbm(nA, X2, Z2, 60, 4, offset=3.3)
n2 = fbm(nB, X2, Z2, 260, 3, offset=8.1)
n3 = fbm(nC, X2, Z2, 14, 3, offset=1.9)
cd2 = np.hypot(X2 - CITADEL[0], Z2 - CITADEL[1])
poi_clear = np.zeros((N, N), np.float32)
village_dirt = np.zeros((N, N), np.float32)
for P in POIS:
    dd = np.hypot(X2 - P['x'], Z2 - P['z'])
    poi_clear = np.maximum(poi_clear, S(P['r'] * 1.25, P['r'] * 0.9, dd))
    if P['type'] in ('village', 'hamlet', 'camp', 'bandit_camp', 'ruin_village'):
        village_dirt = np.maximum(village_dirt, S(P['r'] * 0.8, P['r'] * 0.25, dd) * (0.45 + 0.5 * n1))
for sid, sname, sx, sz in SHRINES:
    poi_clear = np.maximum(poi_clear, S(16, 9, np.hypot(X2 - sx, Z2 - sz)))
citadel_paved = S(165, 140, cd2)

w_rock = S(31, 43, slope_deg + 6 * n3) + 0.55 * mount2 * S(20, 34, slope_deg) + 0.5 * ash2 * S(18, 30, slope_deg)
w_rock = np.clip(w_rock, 0, 1)
w_snow = S(205, 262, H + 30 * n1) * S(52, 36, slope_deg) * (1 - ash2)
under = S(0.3, -1.5, H)
w_sand = np.clip(S(3.4, 1.7, H + 0.6 * n3) * (1 - swamp2) + under * (1 - swamp2), 0, 1) * (1 - 0.8 * mount2 * S(10, 25, slope_deg))
w_mud = swamp2 * np.clip(S(2.0, 0.5, H + 0.5 * n3) + 0.25 + under, 0, 1)
w_ash = ash2 * (0.85 + 0.15 * n1)
w_forest = np.clip(forest2 * (0.75 + 0.5 * n1) + 0.3 * mount2 * S(190, 90, H) * (0.5 + n2), 0, 1) * (1 - poi_clear)
w_dirt = np.clip(road_mask * 1.2 + village_dirt + 0.5 * S(21, 30, slope_deg) * (1 - w_rock)
                 + 0.35 * S(0.25, 0.5, n1 * n2 + 0.2) * (1 - forest2) + citadel_paved * 0.55, 0, 1)
w_river = S(0.35, 0.9, river_mask)
w_dirt = np.clip(w_dirt + w_river * 0.6, 0, 1)

w_grass = np.ones_like(H)
layers = {}
remain = np.ones_like(H)
for name, w in (('snow', w_snow), ('rock', w_rock * (1 - 0.65 * w_snow)), ('dirt_road', np.clip(road_mask * 1.3, 0, 1)),
                ('sand', w_sand), ('ash', w_ash), ('mud', w_mud), ('dirt', w_dirt), ('forest', w_forest)):
    ww = np.clip(w, 0, 1) * remain
    layers[name] = ww
    remain = remain - ww
layers['dirt'] = layers['dirt'] + layers.pop('dirt_road')
layers['grass'] = np.clip(remain, 0, 1)
splat0 = np.stack([layers['grass'], layers['dirt'], layers['rock'], layers['sand']], -1)
splat1 = np.stack([layers['snow'], layers['forest'], layers['mud'], layers['ash']], -1)
save_png(os.path.join(OUT, 'splat0.png'), splat0)
save_png(os.path.join(OUT, 'splat1.png'), splat1)

# vegetation densities (1024): R trees, G conifer fraction, B grass, A dead-tree fraction
log('vegetation / biome maps')
clear = np.clip(poi_clear + S(0.05, 0.4, blur(road_mask, 2)) + S(0.05, 0.3, blur(river_mask, 1)) + citadel_paved, 0, 1)
groves = S(0.12, 0.3, n2 * 0.6 + fbm(nD, X2, Z2, 180, 3, offset=12) * 0.5)
t_forest = forest2 * (0.55 + 0.45 * S(-0.25, 0.2, n2))
t_meadow = (1 - forest2) * (1 - swamp2) * (1 - ash2) * (1 - mount2) * (0.035 + 0.5 * groves)
t_mount = mount2 * S(235, 120, H) * (0.25 + 0.45 * S(-0.1, 0.25, n2))
t_swamp = swamp2 * S(0.2, 1.0, H) * 0.22
t_ash = ash2 * 0.05 * S(0.0, 0.3, n2)
trees = np.clip(t_forest + t_meadow + t_mount + t_swamp + t_ash, 0, 1)
trees *= S(36, 26, slope_deg) * S(2.2, 3.5, H) * (1 - clear) * (1 - layers['snow'] * 0.6)
conifer = np.clip(mount2 * 1.2 + forest2 * S(0.0, 0.35, fbm(nE, X2, Z2, 500, 3, offset=31)) * 0.8 + S(120, 200, H), 0, 1)
grass_d = np.clip(layers['grass'] * (0.75 + 0.5 * n1) + layers['forest'] * 0.35 + layers['mud'] * 0.3, 0, 1) * (1 - np.clip(road_mask * 2, 0, 1))
grass_d *= S(-0.2, 0.6, H) * S(40, 28, slope_deg)
dead = np.clip(swamp2 * 0.55 + ash2 * 1.0 + S(0.75, 1.0, citadel_zone if citadel_zone.shape == H.shape else resize(citadel_zone.astype(np.float32), N)) * 0.5, 0, 1)
veg = np.stack([trees, conifer, grass_d, dead], -1)
veg = veg.reshape(M, 2, M, 2, 4).mean(axis=(1, 3))
save_png(os.path.join(OUT, 'veg.png'), veg)

# biome ids: 0 ocean 1 meadow 2 forest 3 swamp 4 mountain 5 ash 6 citadel 7 beach
biome = np.ones((N, N), np.uint8)
biome[forest2 > 0.5] = 2
biome[swamp2 > 0.5] = 3
biome[mount2 > 0.5] = 4
biome[ash2 > 0.5] = 5
biome[cd2 < 285] = 6
biome[(layers['sand'] > 0.5) & (H > -0.5)] = 7
biome[(H < -0.6) & (swamp2 < 0.5)] = 0
biome_s = biome[::2, ::2]
save_png(os.path.join(OUT, 'biome.png'), (biome_s * 30).astype(np.uint8))

# CPU-side maps in one raw file (canvas readback would premultiply alpha and destroy the data):
#   veg 1024x1024x4 | biome 1024x1024 | surface layer 512x512 | dirt weight 512x512 | rock weight 512x512
lay_stack = np.stack([layers[k] for k in ('grass', 'dirt', 'rock', 'sand', 'snow', 'forest', 'mud', 'ash')], -1)
lay4 = lay_stack.reshape(512, 4, 512, 4, 8).mean(axis=(1, 3))
with open(os.path.join(OUT, 'cpu_maps.bin'), 'wb') as f:
    f.write((np.clip(veg, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    f.write(biome_s.astype(np.uint8).tobytes())
    f.write(np.argmax(lay4, -1).astype(np.uint8).tobytes())
    f.write((np.clip(lay4[:, :, 1], 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    f.write((np.clip(lay4[:, :, 2], 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())

# macro tint (512): multiplicative color variation around 0.5
tn = fbm(nB, X2[::4, ::4], Z2[::4, ::4], 700, 3, offset=40)
tm = fbm(nC, X2[::4, ::4], Z2[::4, ::4], 150, 3, offset=41)
f4, s4, m4, a4 = forest2[::4, ::4], swamp2[::4, ::4], mount2[::4, ::4], ash2[::4, ::4]
tr = 0.5 + 0.10 * tn + 0.05 * tm - 0.06 * f4 - 0.03 * s4 + 0.02 * m4
tg = 0.5 + 0.04 * tn + 0.06 * tm - 0.03 * f4 + 0.00 * s4 - 0.02 * m4
tb = 0.5 - 0.08 * tn + 0.03 * tm - 0.05 * f4 + 0.03 * s4 + 0.04 * m4
save_png(os.path.join(OUT, 'tint.png'), np.stack([tr, tg, tb], -1))

# ============================================================================= height file
hmin = float(H.min())
hmax = float(H.max())
q = np.round((H - hmin) / (hmax - hmin) * 65535.0).astype('<u2')
q.tofile(os.path.join(OUT, 'height.bin'))
land_area = float((H > 0.0).sum()) * CELL * CELL / 1e6
log('height range', hmin, hmax, 'land km2', land_area)

# ============================================================================= map image (in-game parchment map + preview)
log('map image')
lx, lz, ly = -0.55, -0.55, 0.62
shade = np.clip((nx * lx + nz * lz + ly / nl) / 1.0, 0, 1)
shade = 0.45 + 0.75 * shade
cols = {'grass': (0.56, 0.60, 0.36), 'dirt': (0.62, 0.52, 0.38), 'rock': (0.55, 0.52, 0.48), 'sand': (0.80, 0.74, 0.56),
        'snow': (0.93, 0.94, 0.95), 'forest': (0.33, 0.42, 0.27), 'mud': (0.40, 0.40, 0.30), 'ash': (0.32, 0.29, 0.29)}
rgb = np.zeros((N, N, 3), np.float32)
for kname, c in cols.items():
    rgb += layers[kname][:, :, None] * np.array(c, np.float32)
rgb *= shade[:, :, None]
sea = H < 0.0
depth = np.clip(-H / 30.0, 0, 1)
seacol = np.stack([0.50 - 0.22 * depth, 0.62 - 0.22 * depth, 0.66 - 0.16 * depth], -1)
rgb = np.where(sea[:, :, None], seacol, rgb)
rm = np.clip(road_mask * 1.5, 0, 1)[:, :, None]
rgb = rgb * (1 - rm * 0.75) + np.array([0.42, 0.30, 0.20]) * rm * 0.75
rv = np.clip(river_mask * 1.5, 0, 1)[:, :, None]
rgb = rgb * (1 - rv) + np.array([0.42, 0.56, 0.62]) * rv
mp = rgb.reshape(M, 2, M, 2, 3).mean(axis=(1, 3))
# parchment tone
gray = mp.mean(-1, keepdims=True)
mp = mp * 0.7 + gray * 0.3 * np.array([1.05, 0.98, 0.84])
mp = np.clip(mp * np.array([1.04, 0.99, 0.90]), 0, 1)
save_png(os.path.join(OUT, 'map.png'), mp)
# debug preview with POIs
pv = mp.copy()
def dot(x, z, col, r=5):
    i = int((x + HALF) / SIZE * M)
    j = int((z + HALF) / SIZE * M)
    pv[max(j - r, 0):j + r, max(i - r, 0):i + r] = col
for P in POIS:
    dot(P['x'], P['z'], (1, 0, 0) if P['type'] == 'arena' else (1, 1, 0), 6)
for s in SHRINES:
    dot(s[2], s[3], (1, 0.5, 0), 3)
for b in bridges:
    dot(b['x'], b['z'], (0, 1, 1), 4)
save_png(os.path.join(PREVIEWS, 'world_map.png'), pv)
hp = np.clip((H[::2, ::2] - hmin) / (hmax - hmin), 0, 1)
save_png(os.path.join(PREVIEWS, 'world_height.png'), hp)
save_png(os.path.join(PREVIEWS, 'world_veg.png'), veg[:, :, :3])

# ============================================================================= world.json
shr = [dict(id=s[0], name=s[1], x=s[2], z=s[3], y=round(float(sample(H, s[2], s[3])), 2)) for s in SHRINES]
world = dict(
    seed=SEED, size=SIZE, n=N, cell=CELL, seaLevel=0.0, heightMin=hmin, heightMax=hmax,
    landAreaKm2=round(land_area, 2), citadel=dict(x=CITADEL[0], z=CITADEL[1], y=round(float(ctop), 2), radius=150),
    biomes=['ocean', 'meadow', 'forest', 'swamp', 'mountain', 'ash', 'citadel', 'beach'],
    pois=[{k: v for k, v in P.items() if k not in ('flat',)} for P in POIS],
    shrines=shr, roads=roads_json, river=dict(width=RIVER_W, points=river_json), bridges=bridges,
)
with open(os.path.join(OUT, 'world.json'), 'w', encoding='utf8') as f:
    json.dump(world, f, ensure_ascii=False, indent=1)
log('river surface from', float(surf[0]), 'to', float(surf[-1]), 'points', len(riv))
log('done. bridges:', [(b['model'], b['x'], b['z']) for b in bridges])
for P in POIS:
    log('  poi', P['id'], P['y'])
