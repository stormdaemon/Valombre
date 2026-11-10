"""Generic garment parts shared by the outfit sets of VALOMBRE (torso shells, sleeves, trousers, boots,
belts, hoods, knee cops...). Built on outfit_lib."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outfit_lib import *
from outfit_lib import _offs

A24 = angles(24)
TORSO_Z = [1.00, 1.04, 1.08, 1.13, 1.19, 1.25, 1.31, 1.36, 1.40]
ARM_X = [0.165, 0.205, 0.25, 0.31, 0.37, 0.43, 0.47, 0.51, 0.58, 0.65, 0.705]
LEG_Z = [0.10, 0.16, 0.24, 0.32, 0.40, 0.46, 0.50, 0.54, 0.62, 0.71, 0.79, 0.85, 0.90, 0.94]
UP = np.array([0.0, 0.0, 1.0])
# azimuths of a torso garment slit at the front and back centre (cells 23 and 11 are the slits)
SLIT_A = np.radians([3, 20, 35, 50, 65, 80, 95, 110, 125, 140, 160, 177, 183, 200, 220, 235, 250, 265, 280, 295, 310, 325,
                     340, 357])


def wrap(a):
    return (np.asarray(a, float) + math.pi) % TAU - math.pi


def cfn(base, amt=0.10, scale=0.07, seed=0, dirt=None):
    """colour function: mottled base, optional dirt gradient (z0 dark .. z1 clean, strength)."""
    base = col(base)

    def f(P):
        P = np.asarray(P, float)
        c = mottle(P, base, amt, scale, seed)
        if dirt:
            z0, z1, k = dirt
            c = c * (1.0 - k * (1.0 - sstep(z0, z1, P[..., 2])))[..., None]
        return c
    return f


def ring_r(G_row):
    """horizontal radius of a torso ring about the torso axis."""
    return np.hypot(G_row[:, 0], G_row[:, 1] - YC)


# ----------------------------------------------------------------------------- torso / arms
def torso_shell(p, mat, color, off=0.012, hull=0.7, zs=TORSO_Z, A=A24, yoke_ks=(0.3, 0.6, 0.85, 1.0), yoke_off=None,
                neck_dz=(0.012, 0.027), neck_off=(0.007, 0.004), skirt=None, w=None, src='body', split=(), skip=None,
                **kw):
    """torso tube (zs, bottom -> top, last = 1.40) + yoke + collar. skirt = dict(zs=[hem .. up], flare,
    min_off, folds, power, hem_jitter, weights) adds draped rows below zs[0]. Returns the grid."""
    K = p.kit
    zs = list(zs)
    offs = _offs(off, zs, A)
    rows = []
    T = K.torso_rows(zs, A, offs, hull)
    if skirt:
        sz = np.asarray(skirt['zs'], float)
        S = K.drape(A, zs[0], sz, 0.0, min_off=skirt.get('min_off', 0.016), flare=skirt.get('flare', 0.03),
                    power=skirt.get('power', 1.3), folds=skirt.get('folds', (0, 0, 0)), r_top=ring_r(T[0]))
        hj = skirt.get('hem_jitter')
        if hj is not None:
            S[0, :, 2] += hj
        rows.append(S)
    rows.append(T)
    if yoke_ks:
        yo = float(offs[-1].mean()) if yoke_off is None else yoke_off
        rows.append(K.yoke(A, yoke_ks, yo))
        if neck_dz:
            rows.append(K.neck(A, neck_dz, neck_off))
    G = np.concatenate(rows, 0)
    if skirt and w is None:
        w = skirt_weights(**skirt.get('weights', {}))
    p.grid(G, mat, color, src=src, w=w, split=split, skip=skip, **kw)
    return G


def sleeves(p, mat, color, off=0.010, x_end=0.74, end_off=None, xs=ARM_X, nb=10, sides=(1, -1), hull=0.0, x_start=None,
            **kw):
    """set-in sleeves. off: scalar or callable(x, B). The last row sits at x_end with end_off."""
    K = p.kit
    B = angles(nb)
    xs = [x for x in xs if x < x_end - 0.02 and (x_start is None or x >= x_start)] + [x_end]
    o = _offs(off, xs, B)
    if end_off is not None:
        o[-1] = end_off
    out = {}
    for s in sides:
        G = K.sleeve_rows(xs, B, o, side=s, hull=hull, cap=x_start is None)
        p.grid(G, mat, color, flip=(s < 0), src='arm_' + SIDE[s], **kw)
        out[s] = G
    return out


def arm_tube(p, s, xs, offs, mat, color, nb=10, hull=0.0, B=None, closed=True, **kw):
    """tube (or open plate when B is an angle range) around the arm, stations xs with offsets offs."""
    K = p.kit
    B = angles(nb) if B is None else B
    G = K.arm.pts(np.asarray(xs, float)[:, None], B[None, :], off=_offs(offs, xs, B), side=s, hull=hull)
    kw.setdefault('src', 'arm_' + SIDE[s])
    p.grid(G, mat, color, closed=closed, flip=(s < 0), **kw)
    return G


def leg_tube(p, s, zs, offs, mat, color, nl=12, hull=0.0, A=None, closed=True, **kw):
    K = p.kit
    A = angles(nl) if A is None else A
    G = K.leg.pts(np.asarray(zs, float)[:, None], A[None, :], off=_offs(offs, zs, A), side=s, hull=hull)
    kw.setdefault('src', 'leg_' + SIDE[s])
    p.grid(G, mat, color, closed=closed, flip=(s < 0), **kw)
    return G


def arm_ring(K, x, nb, off, side=1, hull=0.0):
    """ring around the arm at x: points, radial directions, axis direction (toward the hand)."""
    B = angles(nb)
    P = K.arm.pts(x, B, off=off, hull=hull, side=side)
    return P, diryz(B), np.array([float(side), 0.0, 0.0])


def leg_ring(K, z, nl, off, side=1, hull=0.0):
    L = angles(nl)
    P = K.leg.pts(z, L, off=off, hull=hull, side=side)
    return P, dirxy(L) * np.array([float(side), 1.0, 1.0])


def torso_ring(K, z, A, off, hull=0.7):
    return K.torso.pts(z, A, off=off, hull=hull), dirxy(A)


def hips_only(P_, Wa):
    return w_move(Wa, ('thigh_L', 'thigh_R'), 'hips')


def belt(p, z, off, mat, color, h=0.035, t=0.006, A=A24, hull=0.8, buckle=None, tail=None, src='body', **kw):
    """belt around the waist + optional buckle (material, colour) and hanging strap end."""
    K = p.kit
    P, rad = torso_ring(K, z, A, off, hull)
    band(p, P, rad, UP, h, t, mat, color, src=src, **kw)
    if buckle:
        c = K.torso.pts(z, 0.0, off=off + t + 0.002, hull=hull)
        p.box(c, (0.019, 0, 0), (0, 0.004, 0), (0, 0, 0.024), buckle[0], col(buckle[1]), src=src)
    if tail:
        a0 = 0.30
        pts = np.array([K.torso.pts(z - 0.004 - 0.03 * k, a0 + 0.02 * k, off=off + t + 0.003 - 0.002 * min(k, 2), hull=hull)
                        for k in range(tail + 1)])
        side = np.array([math.cos(a0), math.sin(a0), 0.0]) * 0.012
        G = np.stack([pts - side, pts + side], 1)
        p.grid(G, mat, np.asarray(color) * 0.9, closed=False, flip=True, src=src, w=hips_only)


def pouch(p, z, az, off, mat, color, size=(0.017, 0.032, 0.036), hull=0.9):
    K = p.kit
    c = K.torso.pts(z, az, off=off + size[0], hull=hull)
    rd = dirxy(az)
    tg = np.array([rd[1], -rd[0], 0.0])
    p.box(c, rd * size[0], tg * size[1], UP * size[2], mat, color, src='body', w=hips_only)


# ----------------------------------------------------------------------------- legs / feet
def trousers(p, mat, color, off=0.008, z_bot=0.10, z_top=1.075, nl=12, leg_off=None, color_r=None, hip_hull=None,
             zs=LEG_Z, **kw):
    """hip tube (closed under the crotch) + two leg tubes. leg_off: callable(z) -> offset."""
    K = p.kit
    A = A24
    hz = [0.855, 0.89, 0.93, 0.97, 1.01, 1.045, z_top]
    ho = [off + 0.004, off + 0.003, off + 0.002, off + 0.002, off + 0.001, off, 0.004]
    G = K.torso_rows(hz, A, ho, hull=hip_hull or [1.0, 0.9, 0.6, 0.4, 0.3, 0.3, 0.0])
    p.grid(G, mat, color, src='body', cap0=True, **kw)
    L = angles(nl)
    zs = [z_bot] + [z for z in zs if z > z_bot + 0.03]

    def lo(z, A_):
        return (leg_off(z) if leg_off else off) - 0.004 * float(sstep(0.84, 0.90, z))
    out = {}
    for s in (1, -1):
        Gl = K.leg_rows(zs, L, lo, side=s)
        p.grid(Gl, mat, (color_r if (s < 0 and color_r is not None) else color), flip=(s < 0), src='leg_' + SIDE[s], **kw)
        out[s] = Gl
    return out


def boots(p, mat, color, top=0.30, off=0.007, sole=None, nl=12, toe=0.0, top_off=None, zs=None, sides=(1, -1), **kw):
    """shoe + shaft up to `top`."""
    K = p.kit
    L = angles(nl)
    if zs is None:
        zs = [0.07, 0.105] + [z for z in (0.15, 0.21, 0.28, 0.36, 0.43) if z < top - 0.03] + [top]
    o = np.full(len(zs), off + 0.002)
    if top_off is not None:
        o[-1] = top_off
    out = {}
    for s in sides:
        shoe(p, s, off, mat, color, sole=sole, toe=toe, **kw)
        G = K.leg_rows(zs, L, o, side=s)
        p.grid(G, mat, color, flip=(s < 0), src='leg_' + SIDE[s], **kw)
        out[s] = G
    return out


def knee_cop(p, s, mat, color, r=0.014, bulge=0.016, wing=True, wing_color=None, z0=0.435, z1=0.57, half=86, **kw):
    """domed knee plate with an optional fan plate on the outer side."""
    K = p.kit
    az = np.radians(np.linspace(-half, half, 7))
    zs = np.linspace(z0, z1, 5)
    dome = r + bulge * np.sin(np.linspace(0.12, math.pi - 0.12, 5))[:, None] * np.cos(np.linspace(-1.25, 1.25, 7))[None, :]
    G = K.leg.pts(zs[:, None], az[None, :], off=dome, side=s, hull=1.0)
    src = 'leg_' + SIDE[s]
    p.grid(G, mat, color, closed=False, flip=(s < 0), src=src, **kw)
    if wing:
        c = K.leg.pts(0.50, math.radians(92), off=r + 0.006, side=s, hull=1.0)
        n = np.array([float(s), 0.0, 0.0])
        ring = [c + n * 0.004 + np.array([0, math.cos(t) * 0.036, math.sin(t) * 0.042]) for t in np.linspace(0, TAU, 9)[:-1]]
        V = np.array([c + n * 0.014] + ring)
        F = [[0, 1 + k, 1 + (k + 1) % 8] for k in range(8)]
        if s > 0:
            F = [f[::-1] for f in F]
        p.add(V, F, mat, wing_color(V) if callable(wing_color) else (color(V) if callable(color) else color), src=src)
    return G


# ----------------------------------------------------------------------------- head
def hood_hull(az):
    """use the raw face surface near the face, the ear covering envelope on the sides and back."""
    return sstep(math.radians(38), math.radians(62), np.abs(wrap(az)))


def hood_rows(K, spec, ns, jf, hull=hood_hull, prof=None):
    """rows of a head covering, listed top -> bottom. spec items: (kind, value, off, af_deg)
        'e': spherical row at elevation value (deg) around the head centre (skull, ears flattened)
        'z': cylindrical row at height z (head envelope: `hull` blends the raw skin and the hull with ears)
        'n': neck ring, value = height above the collar line (offset along the skin normal)
       off: scalar or callable(az wrapped) ; af_deg: half angle of the face opening for that row."""
    prof = prof or K.head
    G = np.zeros((len(spec), ns, 3))
    AZ = np.zeros((len(spec), ns))
    for i, (kind, val, off, af) in enumerate(spec):
        az = face_az(ns, math.radians(af), jf)
        o = off(wrap(az)) if callable(off) else off
        if kind == 'e':
            G[i] = K.dome.pts(math.radians(val), az, off=o)
        elif kind == 'n':
            G[i] = K.neck(az, (val,), o if np.isscalar(o) else float(np.mean(o)))[0]
        else:
            h = hull(az) if callable(hull) else hull
            G[i] = prof.pts(val, az, off=o, hull=h)
        AZ[i] = az
    return G, AZ


def hood(p, mat, color, spec, ns=20, jf=3, face=(3, 99), w=None, hull=hood_hull, src='head', prof=None, **kw):
    """head covering from a row spec; the cells of the face opening (rows face[0] .. face[1]-1) are removed."""
    G, AZ = hood_rows(p.kit, spec, ns, jf, hull, prof)
    p.grid(G, mat, color, flip=True, weld=True, skip=face_skip(ns, jf, face[0], face[1]), src=src, w=w, **kw)
    return G, AZ


def edge_path(G, ns, jf, r0, r1):
    """closed polyline of the face opening of a hood grid (rows r0..r1, columns +-jf)."""
    left = [G[i, jf] for i in range(r0, r1 + 1)]
    right = [G[i, ns - jf] for i in range(r1, r0 - 1, -1)]
    top = [G[r0, j % ns] for j in range(ns - jf + 1, ns + jf)]
    return np.array(left + right + top)


def face_rim(p, G, ns, jf, r0, r1, mat, color, r=0.005, w=None, src='head', bottom=True, nseg=4):
    """rolled edge around the face opening of a hood grid."""
    path = edge_path(G, ns, jf, r0, r1)
    if bottom:
        path = np.concatenate([path, path[:1]], 0)
    else:                                   # open under the chin: right side up, across the top, left side down
        k = r1 - r0 + 1
        path = np.concatenate([path[k:2 * k], path[2 * k:], path[:k]], 0)
    T = tube_path(path, r, nseg)
    p.grid(T, mat, color, w=w, src=src)
    return path


def helm_rows(K, zs, rx, ry, yc=0.0, ns=24, clear=0.012):
    """shape of revolution-ish helm: ellipse (rx, ry) per row, never closer than `clear` to the head."""
    A = angles(ns)
    G = np.zeros((len(zs), ns, 3))
    for i, z in enumerate(zs):
        d = dirxy(A)
        r = 1.0 / np.sqrt((d[:, 0] / rx[i]) ** 2 + (d[:, 1] / ry[i]) ** 2)
        if z < 1.795:
            r = np.maximum(r, K.head.rad(min(z, 1.795), A, 1.0) + clear)
        G[i] = np.array([0.0, YC + yc, z]) + d * r[:, None]
    return G


def helm_point(K, G, zs, az, z, lift=0.0025):
    """point on a helm grid (rows zs, ns columns) at azimuth az / height z, lifted off the surface."""
    ns = G.shape[1]
    f = (az % TAU) / TAU * ns
    j0 = int(math.floor(f)) % ns
    j1 = (j0 + 1) % ns
    t = f - math.floor(f)
    i = int(np.searchsorted(zs, z) - 1)
    i = max(0, min(i, len(zs) - 2))
    u = (z - zs[i]) / (zs[i + 1] - zs[i])
    pt = (G[i, j0] * (1 - t) + G[i, j1] * t) * (1 - u) + (G[i + 1, j0] * (1 - t) + G[i + 1, j1] * t) * u
    return pt + dirxy(az) * lift


def aventail(p, mat, color, top_z=1.565, top_off=0.018, ns=20, **kw):
    """mail / padded collar hanging from a helm down to just above the collar line (covers any chest collar)."""
    spec = [('z', top_z, top_off, 0), ('n', 0.050, 0.022, 0), ('n', 0.026, 0.029, 0), ('n', 0.004, 0.035, 0)]
    Gm, AZ = hood_rows(p.kit, spec, ns, 0, 1.0)
    p.grid(Gm, mat, color, flip=True, src='upper', **kw)
    return Gm
