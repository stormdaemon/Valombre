"""Hair styles and facial hair of VALOMBRE (hair.glb): one skinned mesh per style, material M_hair,
white vertex colours with root / depth darkening, UV u across / v along the strands (0 at the root)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outfit_lib import *
from outfit_lib import _offs
from outfit_sets import wrap, _hood_rows

# hairline: (elevation deg, half angle of the bare zone in deg) from the crown down to the nape
HAIRLINE = [(90, 0), (72, 30), (56, 40), (43, 44), (33, 45), (24, 52), (14, 60), (4, 100), (-10, 104), (-24, 110),
            (-36, 121), (-46, 138)]
HL_E = np.array([h[0] for h in HAIRLINE[4:]][::-1], float)
HL_A = np.array([h[1] for h in HAIRLINE[4:]][::-1], float)


def in_hair(az_deg, e_deg, margin=0.0):
    """inside the hairline? az, e in degrees (az wrapped to -180..180)."""
    a = abs((az_deg + 180.0) % 360.0 - 180.0)
    if e_deg >= 33:
        return True
    if e_deg < -46:
        return False
    return a >= float(np.interp(e_deg, HL_E, HL_A)) + margin


def shade(t, edge=1.0, lo=0.50, hi=1.0):
    t = np.asarray(t, float)
    v = (lo + (hi - lo) * np.clip(t, 0, 1) ** 0.7) * edge
    return np.stack([v, v, v], -1)


def cap(p, off=0.003, ns=24, jf=4, rows=HAIRLINE, lo=0.42, hi=0.62, first_face=4, **kw):
    """scalp shell inside the hairline (under layer of every style)."""
    K = p.kit
    spec = [('e', e, off, af) for e, af in rows]
    G, AZ = _hood_rows(K, spec, ns, jf, 1.0, None)
    t = np.linspace(0, 1, len(rows))[:, None] * np.ones((1, ns))
    C = shade(t, 1.0, lo, hi)
    p.grid(G, 'M_hair', C, flip=True, weld=True, skip=face_skip(ns, jf, first_face, len(rows)), uv_fit=True,
           uv_swap=False, w={'head': 1.0}, src='skull', **kw)
    return G, AZ


def lock(p, path, nrm, width, thick, lo=0.55, hi=1.0, under=False, w=None, src='skull', edge=0.80, tip=0.25, **kw):
    """one tapered strand clump: 3 points arch per station (left edge, raised centre, right edge)."""
    path = np.asarray(path, float)
    n = len(path)
    T = unit(np.gradient(path, axis=0))
    nrm = unit(np.broadcast_to(np.asarray(nrm, float), path.shape))
    S = unit(np.cross(T, nrm))
    Nn = unit(np.cross(S, T))
    t = np.linspace(0, 1, n)
    wd = np.broadcast_to(np.asarray(width, float), (n,)) * (1.0 - (1.0 - tip) * t ** 2.2)
    th = np.broadcast_to(np.asarray(thick, float), (n,)) * (1.0 - 0.6 * t ** 2)
    G = np.stack([path - S * wd[:, None] * 0.5, path + Nn * th[:, None], path + S * wd[:, None] * 0.5], 1)
    C = np.stack([shade(t, edge, lo, hi), shade(t, 1.0, lo, hi), shade(t, edge, lo, hi)], 1)
    kw.setdefault('ao', 0.6)
    p.grid(G, 'M_hair', C, closed=False, uv_fit=True, w=w if w is not None else {'head': 1.0}, src=src, **kw)
    if under:
        G2 = np.stack([G[:, 2], G[:, 0]], 1)
        C2 = np.stack([shade(t, edge * 0.8, lo, hi)] * 2, 1)
        p.grid(G2, 'M_hair', C2, closed=False, uv_fit=True, w=w if w is not None else {'head': 1.0}, src=src, **kw)
    return G


def scalp_path(K, az0, e0, az1, e1, n=4, lift0=0.004, lift1=0.012, bow=0.0, lift_mid=0.0):
    t = np.linspace(0, 1, n)
    az = lerp(az0, az1, t) + bow * np.sin(math.pi * t)
    e = np.maximum(lerp(e0, e1, t), -60.0)
    over = e > 90.0                       # lanes may pass over the crown
    az = np.where(over, az + 180.0, az)
    e = np.where(over, 180.0 - e, e)
    lift = lerp(lift0, lift1, t) + lift_mid * np.sin(math.pi * t)
    P = K.dome.pts(np.radians(e), np.radians(az), off=lift)
    return P, unit(P - HEAD_C)


def hang_weights(P, Wa):
    """hair / beard hanging below the head: head -> neck -> spine_03 with the height."""
    z = P[:, 2]
    t1 = sstep(1.63, 1.52, z)
    t2 = sstep(1.53, 1.42, z)
    W = np.zeros_like(Wa)
    W[:, BI['head']] = 1 - t1
    W[:, BI['neck']] = t1 * (1 - t2)
    W[:, BI['spine_03']] = t1 * t2
    return W


def hang_path(K, start, d0, length, n, clear=0.022, grav=0.75, out=None, src='upper'):
    """polyline hanging from `start`: starts along d0, bends down, stays `clear` off the body."""
    pts = [np.asarray(start, float)]
    d = unit(np.asarray(d0, float))
    step = length / (n - 1)
    down = np.array([0.0, 0.0, -1.0])
    for k in range(n - 1):
        d = unit(d * (1 - grav) + down * grav + (np.asarray(out, float) * 0.15 if out is not None else 0.0))
        pts.append(pts[-1] + d * step)
    P = np.array(pts)
    cl = np.broadcast_to(np.asarray(clear, float), (n,))
    P[1:] = K.body.push_out(P[1:], cl[1:], src)
    dd, Q, Nq = K.body.sdist(P, src)
    return P, Nq


def swept(p, K, lanes, e_from, e_to, n_chain=2, n=5, width=0.036, thick=0.010, lift=(0.004, 0.012), seed=1, az_to=None,
          lo=0.5, overlap=0.35, jit=4.0, **kw):
    """chains of overlapping locks flowing from elevation e_from to e_to along azimuth lanes (deg)."""
    rs = np.random.RandomState(seed)
    for li, az in enumerate(lanes):
        azt = az if az_to is None else az_to[li]
        for c in range(n_chain):
            f0 = c / n_chain
            f1 = min(1.0, (c + 1 + overlap) / n_chain)
            a0, a1 = lerp(az, azt, f0) + rs.uniform(-jit, jit), lerp(az, azt, f1) + rs.uniform(-jit, jit)
            ea, eb = lerp(e_from, e_to, f0), lerp(e_from, e_to, f1)
            P, Nn = scalp_path(K, a0, ea, a1, eb, n, lift[0], lift[1] * rs.uniform(0.8, 1.3), lift_mid=0.004)
            lock(p, P, Nn, width * rs.uniform(0.85, 1.15), thick, lo=lo + 0.12 * c, **kw)


# ============================================================================= hair styles
def hair_crop(K):
    p = Piece('hair_crop', K)
    rows = [(90, 0), (78, 20), (66, 30), (55, 38), (44, 43), (33, 45), (24, 52), (14, 60), (4, 100), (-10, 104),
            (-22, 109), (-32, 117), (-40, 128), (-46, 138)]
    cap(p, off=0.0035, ns=28, jf=5, rows=rows, lo=0.55, hi=0.80, first_face=5)
    # short fringe tufts along the front hairline and the nape
    rs = np.random.RandomState(3)
    for az in np.linspace(-44, 44, 9):
        P, Nn = scalp_path(K, az + rs.uniform(-3, 3), 37, az + rs.uniform(-4, 4), 29.5, 3, 0.004, 0.0035)
        lock(p, P, Nn, 0.022, 0.003, lo=0.6, hi=0.85)
    for az in np.linspace(140, 220, 7):
        P, Nn = scalp_path(K, az, -40, az + rs.uniform(-3, 3), -50, 3, 0.004, 0.0035)
        lock(p, P, Nn, 0.022, 0.003, lo=0.6, hi=0.85)
    for s in (1, -1):   # sideburns
        P, Nn = scalp_path(K, 66 * s, 13, 70 * s, -9, 4, 0.0035, 0.003)
        lock(p, P, Nn, 0.016, 0.002, lo=0.6, hi=0.8)
    return p


def hair_short(K):
    p = Piece('hair_short', K)
    cap(p, off=0.004)
    rs = np.random.RandomState(11)
    rings = [(80, 5, 26, 0.020), (62, 9, 26, 0.022), (46, 13, 24, 0.020), (30, 15, 22, 0.018), (14, 14, 22, 0.016),
             (-2, 12, 20, 0.014), (-18, 11, 18, 0.012), (-32, 9, 16, 0.010)]
    for e0, n, drop, lift in rings:
        for k in range(n):
            az0 = 360.0 * (k + rs.uniform(0.15, 0.85)) / n - 180.0
            front = abs(az0) < 70 and e0 > 25
            if not in_hair(az0, e0 - (0 if front else 4), 2.0):
                continue
            if front:       # fringe swept to the side and up
                az1, e1 = az0 + rs.uniform(22, 38), e0 - rs.uniform(4, 12)
            else:
                az1, e1 = az0 + rs.uniform(-16, 16), e0 - drop * rs.uniform(0.8, 1.2)
            P, Nn = scalp_path(K, az0, e0, az1, e1, 4, 0.004, lift * rs.uniform(0.7, 1.4), lift_mid=0.006)
            lock(p, P, Nn, rs.uniform(0.030, 0.044), 0.008, lo=0.5 + 0.2 * rs.rand(), under=True)
    for s in (1, -1):
        P, Nn = scalp_path(K, 66 * s, 14, 70 * s, -8, 4, 0.004, 0.003)
        lock(p, P, Nn, 0.018, 0.003, lo=0.55, hi=0.8)
    return p


def hair_medium(K):
    p = Piece('hair_medium', K)
    cap(p, off=0.004)
    # top: from the front hairline back over the crown
    swept(p, K, [-36, -18, 0, 18, 36], 36, 150, n_chain=3, n=5, width=0.050, thick=0.012, lift=(0.006, 0.016), seed=2,
          az_to=[-14, -7, 0, 7, 14])
    # the top lanes pass over the pole: continue on the back of the head
    swept(p, K, [150, 165, 180, 195, 210], 40, -42, n_chain=3, n=5, width=0.050, thick=0.012, lift=(0.010, 0.020), seed=3)
    for s in (1, -1):
        swept(p, K, [56 * s, 70 * s], 30, -30, n_chain=2, n=5, width=0.046, thick=0.011, lift=(0.008, 0.018), seed=4 + s,
              az_to=[112 * s, 124 * s])
        swept(p, K, [100 * s, 124 * s], 34, -44, n_chain=3, n=5, width=0.050, thick=0.012, lift=(0.010, 0.020), seed=6 + s,
              az_to=[118 * s, 136 * s])
    return p


def long_locks(p, K, roots, length, seed=5, clear=0.024, width=0.050, n=7, lo=0.5):
    rs = np.random.RandomState(seed)
    for az, e in roots:
        P0, N0 = scalp_path(K, az, e, az, e - 14, 3, 0.012, 0.018)
        d0 = P0[-1] - P0[-2]
        out = np.array([math.sin(math.radians(az)), -math.cos(math.radians(az)), 0.0])
        P1, N1 = hang_path(K, P0[-1], d0, length * rs.uniform(0.9, 1.08), n, clear=clear, out=out)
        P = np.concatenate([P0[:-1], P1], 0)
        Nn = np.concatenate([N0[:-1], N1], 0)
        lock(p, P, Nn, width * rs.uniform(0.9, 1.15), 0.011, lo=lo + 0.1 * rs.rand(), under=True, w=hang_weights,
             src='upper', tip=0.35)


def hair_long(K):
    p = Piece('hair_long', K)
    cap(p, off=0.004)
    # centre part: lanes going down both sides from the part line
    for s in (1, -1):
        for q in (40, 62, 84, 100, 120, 142):
            if q <= 90:
                az0, e0 = s * (6 + (90 - q) * 0.1), q
            else:
                az0, e0 = s * 174, 180 - q
            az1 = s * float(np.interp(q, [40, 90, 142], [62, 96, 142]))
            e1 = float(np.interp(q, [40, 90, 142], [2, -8, -24]))
            for c in range(2):
                f0, f1 = (0.0, 0.62) if c == 0 else (0.42, 1.0)
                P, Nn = scalp_path(K, lerp(az0, az1, f0), lerp(e0, e1, f0), lerp(az0, az1, f1), lerp(e0, e1, f1), 5,
                                   0.006, 0.016, lift_mid=0.004)
                lock(p, P, Nn, 0.054, 0.012, lo=0.5 + 0.1 * c)
    roots = [(a, -14) for a in (78, 100, 122, 144, 166, 188, 210, 232, 254, 276)]
    long_locks(p, K, roots, 0.27, seed=5)
    roots = [(a, -6) for a in (90, 112, 134, 156, 180, 204, 226, 248, 270)]
    long_locks(p, K, roots, 0.22, seed=6, clear=0.036, lo=0.6)
    return p


def back_sweep(p, K, e_tie, seed=3, lanes_top=(-40, -20, 0, 20, 40)):
    """locks pulled back toward a tie point on the back of the head (az 180, elevation e_tie)."""
    swept(p, K, list(lanes_top), 36, 150, n_chain=3, n=5, width=0.050, thick=0.009, lift=(0.005, 0.009), seed=seed,
          az_to=[a * 0.3 for a in lanes_top], jit=2.0)
    for s in (1, -1):
        swept(p, K, [56 * s, 64 * s, 104 * s], 28, e_tie, n_chain=3, n=5, width=0.048, thick=0.008, lift=(0.005, 0.009),
              seed=seed + 2 + s, az_to=[168 * s, 172 * s, 174 * s], jit=2.0)
        swept(p, K, [112 * s, 128 * s], -30, e_tie, n_chain=2, n=4, width=0.046, thick=0.008, lift=(0.005, 0.009),
              seed=seed + 5 + s, az_to=[172 * s, 176 * s], jit=2.0)
    swept(p, K, [160, 180, 200], 62, e_tie, n_chain=2, n=5, width=0.050, thick=0.009, lift=(0.006, 0.010), seed=seed + 9, jit=2.0)
    swept(p, K, [160, 180, 200], -44, e_tie, n_chain=1, n=4, width=0.050, thick=0.008, lift=(0.005, 0.009), seed=seed + 10, jit=2.0)


def hair_ponytail(K):
    p = Piece('hair_ponytail', K)
    cap(p, off=0.004)
    back_sweep(p, K, 8)
    tie = K.dome.pts(math.radians(8), math.radians(180), off=0.012)
    ring = tube_path(np.array([tie + (0, -0.006, 0.004), tie + (0, 0.012, 0.0), tie + (0, 0.026, -0.008)]), [0.016, 0.019, 0.017], 8)
    p.grid(ring, 'M_hair', shade(np.array([0.2, 0.35, 0.3])[:, None] * np.ones((1, 8))), uv_fit=True, w={'head': 1.0}, src='skull')
    rs = np.random.RandomState(8)
    for k in range(7):
        a = TAU * k / 7
        st = tie + np.array([0.012 * math.cos(a), 0.022, -0.006 + 0.010 * math.sin(a)])
        P, Nn = hang_path(K, st, (0.25 * math.cos(a), 1.0, -0.2), 0.24 * rs.uniform(0.85, 1.1), 7, clear=0.030 + 0.012 * (math.sin(a) > 0),
                          grav=0.55, out=(0.3 * math.cos(a), 1, 0))
        lock(p, P, Nn, 0.034, 0.010, lo=0.55 + 0.15 * rs.rand(), under=True, w=hang_weights, src='upper', tip=0.2)
    return p


def hair_braid(K):
    p = Piece('hair_braid', K)
    cap(p, off=0.004)
    back_sweep(p, K, -30, seed=13)
    start = K.dome.pts(math.radians(-32), math.radians(180), off=0.014)
    n = 15
    path, Nn = hang_path(K, start, (0, 0.6, -1.0), 0.42, n, clear=0.034, grav=0.8, out=(0, 1, 0))
    path = smooth_ring(path[None], 2, 0.5, closed=False)[0]
    k = np.arange(n)
    rad = 0.021 * (1.0 - 0.45 * (k / (n - 1)) ** 1.5) * (1.0 + 0.22 * np.cos(math.pi * k))
    rad[-1] *= 0.45
    R = tube_path(path, rad, 6, up_hint=(1, 0, 0), twist=0.5)
    t = (k / (n - 1))[:, None] * np.ones((1, 6))
    C = shade(0.35 + 0.65 * t) * (0.80 + 0.2 * (np.cos(math.pi * k) > 0))[:, None, None]
    p.grid(R, 'M_hair', C, uv_fit=True, cap1=True, w=hang_weights_low, src='upper')
    return p


def hang_weights_low(P, Wa):
    """long braid: head -> neck -> spine_03 -> spine_02."""
    z = P[:, 2]
    W = hang_weights(P, Wa)
    t3 = sstep(1.40, 1.26, z)
    W[:, BI['spine_02']] = W[:, BI['spine_03']] * t3
    W[:, BI['spine_03']] *= (1 - t3)
    return W


def hair_topknot(K):
    p = Piece('hair_topknot', K)
    cap(p, off=0.004)
    # everything pulled up to the crown
    for az in np.linspace(-180, 150, 12):
        e0 = 34 if abs(az) < 50 else (10 if abs(az) < 64 else (4 if abs(az) < 100 else -40))
        if abs(az) >= 64 and abs(az) < 100:
            e0 = 12
        P, Nn = scalp_path(K, az, e0, az * 0.9, 80, 6, 0.005, 0.008, lift_mid=0.004)
        lock(p, P, Nn, 0.056, 0.008, lo=0.5)
        P, Nn = scalp_path(K, az + 15, max(e0, 20) + 22, az * 0.9 + 12, 84, 4, 0.007, 0.010)
        lock(p, P, Nn, 0.05, 0.008, lo=0.62)
    top = K.dome.pts(math.radians(86), math.radians(180), off=0.006)
    zs = np.array([0.0, 0.012, 0.022, 0.038, 0.054, 0.064, 0.068])
    rr = np.array([0.020, 0.017, 0.016, 0.027, 0.027, 0.017, 0.001])
    A = angles(8)
    G = np.stack([top + np.array([0, 0.006 * z / 0.068, z]) + dirxy(A) * r for z, r in zip(zs, rr)])
    t = np.array([0.2, 0.3, 0.25, 0.7, 0.9, 1.0, 1.0])[:, None] * np.ones((1, 8))
    p.grid(G, 'M_hair', shade(t), uv_fit=True, weld=True, w={'head': 1.0}, src='skull')
    return p


def hair_mohawk(K):
    p = Piece('hair_mohawk', K)
    # narrow base strip along the midline
    es = np.array([34, 50, 68, 86, 104, 122, 140, 158, 176, 194, 212, 226])    # arc angle from the front horizon
    def mid(e_arc, lift, side=0.0):
        e = e_arc if e_arc <= 90 else 180 - e_arc
        az = 0.0 if e_arc <= 90 else 180.0
        P = K.dome.pts(math.radians(e), math.radians(az), off=lift)
        return P + np.array([side, 0, 0])
    base = np.array([[mid(e, 0.003, -0.016), mid(e, 0.006, 0.0), mid(e, 0.003, 0.016)] for e in es])
    t = np.zeros((len(es), 3)) + 0.2
    p.grid(base, 'M_hair', shade(t, 1.0, 0.45, 0.7), closed=False, flip=True, uv_fit=True, uv_swap=True, w={'head': 1.0}, src='skull')
    rs = np.random.RandomState(4)
    for k, e in enumerate(np.linspace(36, 224, 17)):
        root = mid(e, 0.002)
        nrm = unit(root - HEAD_C)
        tang = unit(mid(e + 2, 0.002) - mid(e - 2, 0.002))
        h = 0.085 * (0.55 + 0.45 * math.sin(math.radians((e - 30) * 0.93))) * rs.uniform(0.9, 1.1)
        tipd = unit(nrm + tang * 0.35)
        path = np.array([root, root + tipd * h * 0.4, root + tipd * h * 0.75, root + tipd * h])
        for s in (1, -1):
            sn = np.array([float(s), 0, 0])
            lock(p, path + sn * 0.004, sn, 0.050, 0.006, lo=0.45, tip=0.12)
    return p


# ============================================================================= beards
def jaw_z(az):
    """height of the lower border of the jaw at azimuth az (rad)."""
    a = np.abs(wrap(az))
    return 1.5745 + (1.607 - 1.5745) * sstep(math.radians(18), math.radians(84), a)


def cheek_z(az, mouth=True):
    """upper border of a beard: under the lower lip in the middle, up the cheek toward the sideburn."""
    a = np.degrees(np.abs(wrap(az)))
    z = np.interp(a, [0, 13, 22, 32, 50, 66, 76], [1.604, 1.604, 1.618, 1.630, 1.648, 1.668, 1.690])
    return z


def beard_anchor(K):
    def fn(P, Q):
        Pc = P.copy()
        az = np.arctan2(P[:, 0], -(P[:, 1] - YC))
        zj = jaw_z(az) + 0.004
        low = Pc[:, 2] < zj
        Pc[low, 2] = zj[low]
        # hanging hair follows the chin above it
        Pc[low, 1] = np.maximum(Pc[low, 1], -0.10)
        Qc, TI = K.body.nearest(Pc, 'skull')
        return Qc
    return fn


def beard_shell(p, K, az_max=76, n_az=13, thick=0.010, drop=0.015, rows=6, top_feather=0.0015, taper=None,
                chin_extra=0.0, lo=0.55, hi=0.95, az_min=None, w=None, zcap=None):
    """beard as a shell over the cheeks / jaw / chin: rows from the cheek line down, around the jaw
    border, closing on the neck. thick: max thickness, drop: how far it hangs under the jaw border
    (scalar or callable(az_deg)), chin_extra: extra length under the chin."""
    az = np.radians(np.linspace(-az_max, az_max, n_az))
    zt = cheek_z(az)
    zj = jaw_z(az)
    a_deg = np.degrees(np.abs(az))
    dr = drop(a_deg) if callable(drop) else np.full(n_az, drop)
    dr = dr + chin_extra * np.exp(-(a_deg / 26.0) ** 2)
    th = thick(a_deg) if callable(thick) else np.full(n_az, thick)
    th = th * (1.0 - 0.75 * sstep(az_max - 22, az_max, a_deg))        # thin toward the sideburns
    G = np.zeros((rows + 2, n_az, 3))
    T = np.zeros((rows + 2, n_az))
    for i in range(rows + 1):
        f = i / rows
        z = zt + (zj - dr - zt) * f
        zr = np.maximum(z, zj + 0.004)                 # radius is taken on the face, never on the neck
        prof_t = np.sin(math.pi * min(f * 0.62 + 0.04, 0.5)) if f < 0.75 else 1.0
        r = K.head.rad(zr, az) + top_feather + th * prof_t
        below = np.clip((zj - z) / np.maximum(dr, 1e-4), 0, 1)
        r = r - below * th * 0.25
        G[i] = head_axis(z) + dirxy(az) * r[:, None]
        T[i] = f * 0.85
    # closing row on the neck / under the chin
    zc = zj - dr * 0.55
    rn = K.head.rad(np.maximum(zc, 1.545), az) + 0.003
    rn = np.minimum(rn, K.head.rad(zj + 0.004, az) - 0.008)
    G[rows + 1] = head_axis(zc) + dirxy(az) * rn[:, None]
    T[rows + 1] = 0.6
    if taper is not None:
        G = taper(G)
    C = shade(T, 1.0, lo, hi)
    p.grid(G, 'M_hair', C, closed=False, flip=True, uv_fit=True, w=w if w is not None else {'head': 1.0}, src='skull',
           anchor=beard_anchor(K))
    return G, az


def mustache(p, K, half=28, thick=0.006, droop=0.012, n=9, lo=0.6, w_mid=0.011):
    az = np.radians(np.linspace(-half, half, n))
    a = np.abs(np.degrees(az)) / half
    zc = 1.6335 - droop * a ** 1.7
    hw = w_mid * (1.0 - 0.55 * a ** 1.5)
    rows = []
    for k, (dz, o) in enumerate(((hw, 0.0012), (hw * 0.15, thick), (-hw, 0.0025 + thick * 0.4))):
        z = zc + dz
        r = K.head.rad(z, az) + o * (1.0 - 0.4 * a)
        rows.append(head_axis(z) + dirxy(az) * r[:, None])
    G = np.stack(rows)
    t = np.array([0.1, 0.6, 1.0])[:, None] * np.ones((1, n))
    p.grid(G, 'M_hair', shade(t, 1.0, lo, 1.0), closed=False, flip=True, uv_fit=True, w={'head': 1.0}, src='skull')
    return G


def beard_stubble(K):
    p = Piece('beard_stubble', K)
    beard_shell(p, K, thick=0.0016, drop=0.014, rows=6, n_az=15, lo=0.75, hi=0.95, top_feather=0.0012)
    mustache(p, K, half=26, thick=0.0018, droop=0.014, lo=0.8, w_mid=0.008)
    return p


def beard_short(K):
    p = Piece('beard_short', K)
    beard_shell(p, K, thick=0.009, drop=0.018, rows=6, n_az=15, chin_extra=0.006)
    mustache(p, K, half=28, thick=0.006, droop=0.016)
    return p


def beard_goatee(K):
    p = Piece('beard_goatee', K)
    beard_shell(p, K, az_max=30, n_az=9, thick=0.011, drop=0.012, rows=5, chin_extra=0.030)
    mustache(p, K, half=27, thick=0.006, droop=0.022)
    return p


def beard_full(K):
    p = Piece('beard_full', K)
    beard_shell(p, K, thick=lambda a: 0.016 + 0.010 * np.exp(-(a / 35.0) ** 2), drop=lambda a: 0.030 + 0.0 * a, rows=7,
                n_az=17, chin_extra=0.035)
    mustache(p, K, half=30, thick=0.009, droop=0.020, w_mid=0.013)
    return p


def beard_long(K):
    p = Piece('beard_long', K)
    G, az = beard_shell(p, K, thick=lambda a: 0.018 + 0.010 * np.exp(-(a / 35.0) ** 2), drop=lambda a: 0.030 + 0.0 * a,
                        rows=7, n_az=17, chin_extra=0.020, w=hang_weights)
    # long tapered mass down to the chest
    n = 8
    zs = np.linspace(1.565, 1.375, n)
    A = angles(8)
    rings = []
    for k, z in enumerate(zs):
        f = k / (n - 1)
        rx = 0.050 * (1 - f) ** 0.8 + 0.006
        ry = 0.030 * (1 - f) ** 0.7 + 0.005
        c = np.array([0.0, -0.066 - 0.022 * math.sin(math.pi * min(f * 1.2, 1.0)), z])
        rings.append(c + np.stack([np.sin(A) * rx, -np.cos(A) * ry, 0 * A], 1))
    R = np.array(rings)
    R = K.body.push_out(R.reshape(-1, 3), 0.012, 'upper').reshape(R.shape)
    t = (np.linspace(0.35, 1, n))[:, None] * np.ones((1, 8))
    p.grid(R[::-1], 'M_hair', shade(t[::-1], 1.0, 0.55, 1.0), uv_fit=True, cap0=True, w=hang_weights, src='upper',
           anchor=beard_anchor(K))
    mustache(p, K, half=31, thick=0.010, droop=0.030, w_mid=0.013)
    return p


def mustache_only(K):
    p = Piece('mustache', K)
    mustache(p, K, half=31, thick=0.008, droop=0.024, n=11, w_mid=0.012)
    return p


HAIR = {
    'hair_crop': hair_crop, 'hair_short': hair_short, 'hair_medium': hair_medium, 'hair_long': hair_long,
    'hair_ponytail': hair_ponytail, 'hair_braid': hair_braid, 'hair_topknot': hair_topknot, 'hair_mohawk': hair_mohawk,
    'beard_stubble': beard_stubble, 'beard_short': beard_short, 'beard_goatee': beard_goatee, 'beard_full': beard_full,
    'beard_long': beard_long, 'mustache': mustache_only,
}
HAIR_MORPHS = HEAD_MORPHS + ['thin', 'muscular', 'shoulder_width', 'ear_point']
BEARD_MORPHS = HEAD_MORPHS + ['thin', 'muscular', 'mouth_open', 'smile', 'mouth_width', 'mouth_height', 'lip_upper',
                              'lip_lower', 'chest_size', 'breast_size']


def hair_morphs(name):
    return BEARD_MORPHS if (name.startswith('beard') or name == 'mustache') else HAIR_MORPHS
