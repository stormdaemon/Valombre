"""The 7 outfit sets of VALOMBRE (21 pieces: <set>_head / <set>_chest / <set>_legs).
Every function receives the Kit and returns an unbuilt Piece. PIECES maps the object name to
(builder, hides, note)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outfit_lib import *
from outfit_lib import _offs

A24 = angles(24)
TORSO_Z = [1.00, 1.04, 1.08, 1.13, 1.19, 1.25, 1.31, 1.36, 1.40]
ARM_X = [0.165, 0.205, 0.25, 0.31, 0.37, 0.43, 0.47, 0.51, 0.58, 0.65, 0.705]
LEG_Z = [0.10, 0.16, 0.24, 0.32, 0.40, 0.46, 0.50, 0.54, 0.62, 0.71, 0.79, 0.85, 0.90, 0.94]
UP = np.array([0.0, 0.0, 1.0])


def wrap(a):
    return (np.asarray(a, float) + math.pi) % TAU - math.pi


def cfn(base, amt=0.10, scale=0.07, seed=0, dirt=None, tint=None):
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


# ----------------------------------------------------------------------------- generic garment parts
def torso_shell(p, mat, color, off=0.012, hull=0.7, zs=TORSO_Z, A=A24, yoke_ks=(0.3, 0.6, 0.85, 1.0), yoke_off=None,
                neck_dz=(0.012, 0.027), neck_off=(0.007, 0.004), skirt=None, w=None, src='body', split=(), skip=None,
                top_only=False, **kw):
    """torso tube (zs, bottom -> top, last = 1.40) + yoke + collar. skirt = dict(zs=[hem .. up], flare,
    min_off, folds, power, hem_jitter) adds draped rows below zs[0]. Returns the grid."""
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


def arm_ring(K, x, nb, off, side=1, hull=0.0):
    """ring around the arm at x: points, radial directions, axis direction (toward the hand)."""
    B = angles(nb)
    P = K.arm.pts(x, B, off=off, hull=hull, side=side)
    rad = diryz(B)
    ax = np.array([float(side), 0.0, 0.0])
    return P, rad, ax


def leg_ring(K, z, nl, off, side=1, hull=0.0):
    L = angles(nl)
    P = K.leg.pts(z, L, off=off, hull=hull, side=side)
    rad = dirxy(L) * np.array([float(side), 1.0, 1.0])
    return P, rad


def torso_ring(K, z, A, off, hull=0.7):
    P = K.torso.pts(z, A, off=off, hull=hull)
    return P, dirxy(A)


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
        pts = [K.torso.pts(z - 0.004 - 0.03 * k, a0 + 0.02 * k, off=off + t + 0.003 - 0.002 * k, hull=hull) for k in range(tail + 1)]
        pts = np.array(pts)
        side = np.array([math.cos(a0), math.sin(a0), 0.0]) * 0.012
        G = np.stack([pts - side, pts + side], 1)
        p.grid(G, mat, np.asarray(color) * 0.9, closed=False, flip=True, src=src,
               w=lambda P_, Wa: w_move(Wa, ('thigh_L', 'thigh_R'), 'hips'))


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


def hood_hull(az):
    """use the raw face surface near the face, the ear covering envelope on the sides and back."""
    return sstep(math.radians(52), math.radians(78), np.abs(wrap(az)))


def hood(p, mat, color, spec, ns=20, jf=3, face=(3, 99), w=None, hull=hood_hull, src='head', prof=None, **kw):
    """head covering from a row spec (see outfit_lib.head_rows), rows listed top -> bottom."""
    G, AZ = _hood_rows(p.kit, spec, ns, jf, hull, prof)
    p.grid(G, mat, color, flip=True, weld=True, skip=face_skip(ns, jf, face[0], face[1]), src=src, w=w, **kw)
    return G, AZ


def _hood_rows(K, spec, ns, jf, hull, prof):
    prof = prof or K.head
    G = np.zeros((len(spec), ns, 3))
    AZ = np.zeros((len(spec), ns))
    for i, (kind, val, off, af) in enumerate(spec):
        az = face_az(ns, math.radians(af), jf)
        o = off(wrap(az)) if callable(off) else off
        if kind == 'e':
            G[i] = K.dome.pts(math.radians(val), az, off=o)
        else:
            h = hull(az) if callable(hull) else hull
            G[i] = prof.pts(val, az, off=o, hull=h)
        AZ[i] = az
    return G, AZ


def edge_path(G, ns, jf, r0, r1):
    """closed polyline of the face opening of a hood grid (rows r0..r1, columns +-jf)."""
    left = [G[i, jf] for i in range(r0, r1 + 1)]
    right = [G[i, ns - jf] for i in range(r1, r0 - 1, -1)]
    top = [G[r0, j % ns] for j in range(ns - jf + 1, ns + jf)]
    return np.array(left + right + top)


# ============================================================================= PEASANT
def peasant_chest(K):
    p = Piece('peasant_chest', K)
    wool = cfn('#8a7350', 0.12, 0.06, 1, dirt=(0.76, 0.95, 0.30))
    off = [0.016, 0.011, 0.020, 0.021, 0.019, 0.017, 0.015, 0.014, 0.013]
    hem = 0.012 * (vnoise(np.stack([A24 * 3, A24 * 0, A24 * 0], 1), 1.0, 3) - 0.5)
    torso_shell(p, 'M_cloth', wool, off=off, hull=0.8,
                skirt=dict(zs=[0.775, 0.83, 0.89, 0.95], flare=0.035, folds=(6, 0.010, 0.4), hem_jitter=hem))
    # short sleeves ending in a thick roll above the elbow (the forearms stay bare: body_arms is NOT hidden)
    G = sleeves(p, 'M_cloth', wool, off=lambda x, B: 0.012 + 0.006 * sstep(0.2, 0.4, x), x_end=0.415, end_off=0.016)
    for s in (1, -1):
        P, rad, ax = arm_ring(K, 0.425, 10, 0.012, s)
        roll(p, P, rad, ax, 0.013, 'M_cloth', col('#93805c'), flip=(s < 0), src='arm_' + SIDE[s])
    belt(p, 1.045, 0.013, 'M_leather', col('#4a3526'), buckle=('M_metal_iron', '#5a5650'), tail=4)
    return p


def peasant_legs(K):
    p = Piece('peasant_legs', K)
    c = cfn('#5f5546', 0.12, 0.06, 2, dirt=(0.25, 0.6, 0.25))
    legs = trousers(p, 'M_cloth', c, off=0.009, z_bot=0.27, leg_off=lambda z: 0.010 + 0.006 * sstep(0.30, 0.42, z))
    # leg wraps (winingas) from the ankle to under the knee, simple turn shoes
    wrapc = col('#8c8068')
    L = angles(12)
    for s in (1, -1):
        zs, offs, cc = [], [], []
        for k, z in enumerate(np.linspace(0.085, 0.31, 7)):
            zs += [z, z + 0.036]
            offs += [0.012, 0.008]
            cc += [wrapc * (0.78 + 0.1 * (k % 2)), wrapc * (1.0 - 0.08 * (k % 2))]
        G = K.leg_rows(zs, L, offs, side=s)
        C = np.repeat(np.array(cc)[:, None, :], 12, 1)
        p.grid(G, 'M_cloth', C, flip=(s < 0), src='leg_' + SIDE[s], split=tuple(range(1, len(zs) - 1, 2)))
        shoe(p, s, 0.006, 'M_leather', cfn('#4b3a2a', 0.1, 0.04, 5), sole=col('#2a2019'))
    # patches
    for s, z0, a0, cpatch in ((1, 0.52, -0.3, '#75654a'), (-1, 0.70, 0.5, '#4d4a40')):
        zz = np.array([z0, z0 + 0.045, z0 + 0.09])
        aa = np.array([a0, a0 + 0.35, a0 + 0.7])
        G = K.leg.pts(zz[:, None], aa[None, :], off=0.016 + 0.006 * float(sstep(0.30, 0.42, z0)), side=s)
        p.grid(G, 'M_cloth', col(cpatch), closed=False, flip=(s < 0), src='leg_' + SIDE[s])
    return p


def peasant_head(K):
    p = Piece('peasant_head', K)
    o = 0.006
    spec = [('e', 90, o, 0), ('e', 64, o, 30), ('e', 44, o, 40), ('e', 30, o, 46), ('z', 1.712, o, 52),
            ('z', 1.685, o, 55), ('z', 1.655, o, 60), ('z', 1.628, o, 66), ('z', 1.603, o + 0.002, 74)]
    c = cfn('#b9ad92', 0.07, 0.05, 4)
    G, AZ = hood(p, 'M_cloth', c, spec, ns=20, jf=3, face=(3, 8), w={'head': 1.0})
    # ties hanging from the ear flaps
    for s in (1, -1):
        a = G[8, 3 if s > 0 else 17]
        path = np.array([a + (0, 0, 0.004), a + (0.004 * s, -0.004, -0.03), a + (0.006 * s, -0.008, -0.065)])
        T = tube_path(path, [0.0035, 0.003, 0.0025], 4)
        p.grid(T, 'M_cloth', col('#a89c82'), cap1=True, w={'head': 1.0}, src='head')
    return p


# ============================================================================= LEATHER
def leather_chest(K):
    p = Piece('leather_chest', K)
    gamb = cfn('#9a8b6c', 0.08, 0.05, 6, dirt=(0.80, 0.95, 0.25))
    lea = cfn('#523a26', 0.14, 0.05, 7)
    # gambeson: skirt + collar + sleeves (its torso is hidden under the jerkin)
    A = A24
    T0 = K.torso_rows([1.00, 1.04], A, [0.017, 0.013], 0.8)
    S = K.drape(A, 1.00, [0.835, 0.89, 0.95], 0.0, min_off=0.017, flare=0.022, folds=(8, 0.004, 0.0), r_top=ring_r(T0[0]))
    G = np.concatenate([S, T0], 0)
    p.grid(G, 'M_cloth', gamb, src='body', w=skirt_weights(z_full=0.80))
    Y = np.concatenate([K.yoke(A, (0.72, 1.0), 0.012), K.neck(A, (0.014, 0.032), (0.009, 0.006))], 0)
    p.grid(Y, 'M_cloth', gamb, src='trunk')
    sleeves(p, 'M_cloth', gamb, off=0.012, end_off=0.006)
    # boiled leather jerkin
    off = [0.022, 0.019, 0.022, 0.023, 0.023, 0.023, 0.022, 0.021, 0.020]
    torso_shell(p, 'M_leather', lea, off=off, hull=0.9, zs=[0.965] + TORSO_Z[1:], yoke_ks=(0.3, 0.6, 0.86), yoke_off=0.020,
                neck_dz=None, w=w_trunk)
    # shoulder caps
    for s in (1, -1):
        B = np.radians(np.linspace(-115, 115, 8))
        xs = np.array([0.150, 0.20, 0.25, 0.292])
        Gs = K.arm.pts(xs[:, None], B[None, :], off=np.array([0.016, 0.026, 0.024, 0.022])[:, None], side=s)
        p.grid(Gs, 'M_leather', cfn('#46301f', 0.12, 0.05, 8), closed=False, flip=(s < 0), src='arm_' + SIDE[s])
        # bracers
        xb = [0.52, 0.56, 0.62, 0.68, 0.705]
        Gb = K.arm.pts(np.array(xb)[:, None], angles(10)[None, :], off=np.array([0.019, 0.018, 0.016, 0.014, 0.013])[:, None], side=s)
        p.grid(Gb, 'M_leather', cfn('#3f2c1e', 0.12, 0.04, 9), flip=(s < 0), src='arm_' + SIDE[s],
               w=('rigid', 'forearm_' + SIDE[s], 0.7))
    belt(p, 1.05, 0.021, 'M_leather', col('#2e2118'), h=0.04, buckle=('M_metal_iron', '#77726a'), tail=3)
    return p


def leather_legs(K):
    p = Piece('leather_legs', K)
    c = cfn('#4a3a2d', 0.12, 0.05, 10)
    trousers(p, 'M_leather', c, off=0.008, z_bot=0.36)
    bc = cfn('#33261c', 0.12, 0.04, 11, dirt=(0.0, 0.12, 0.3))
    Gb = boots(p, 'M_leather', bc, top=0.43, off=0.008, sole=col('#1d1612'), top_off=0.016)
    for s in (1, -1):
        P, rad = leg_ring(K, 0.415, 12, 0.014, s)
        band(p, P, rad, UP, 0.045, 0.006, 'M_leather', col('#3d2d21'), flip=(s < 0), src='leg_' + SIDE[s])
    return p


def leather_head(K):
    p = Piece('leather_head', K)
    o = 0.008
    spec = [('e', 90, o, 0), ('e', 64, o, 30), ('e', 44, o, 40), ('e', 31, o, 47), ('z', 1.712, o, 54),
            ('z', 1.685, o, 58), ('z', 1.655, o, 64), ('z', 1.625, o, 72), ('z', 1.595, o + 0.004, 84), ('z', 1.572, o + 0.008, 95)]
    G, AZ = hood(p, 'M_leather', cfn('#5a4029', 0.14, 0.05, 12), spec, ns=20, jf=3, face=(3, 9), w={'head': 1.0})
    return p


# ============================================================================= BANDIT
def bandit_chest(K):
    p = Piece('bandit_chest', K)
    shirt = cfn('#77705f', 0.16, 0.06, 13, dirt=(0.84, 1.05, 0.35))
    hem = 0.03 * (vnoise(np.stack([A24 * 4, A24 * 0, A24 * 0], 1), 1.0, 5) - 0.4)
    torso_shell(p, 'M_cloth', shirt, off=0.011, hull=0.75,
                skirt=dict(zs=[0.86, 0.91, 0.955], flare=0.02, folds=(7, 0.006, 1.0), hem_jitter=hem))
    sleeves(p, 'M_cloth', shirt, off=lambda x, B: 0.010 + 0.004 * sstep(0.25, 0.4, x), end_off=0.006)
    hide = cfn('#5d4830', 0.18, 0.05, 14)
    off = [0.021, 0.020, 0.022, 0.023, 0.024, 0.024, 0.023, 0.022, 0.021]
    # hide vest, open at the front
    torso_shell(p, 'M_leather', hide, off=off, hull=0.9, zs=[1.01, 1.04] + TORSO_Z[2:], yoke_ks=(0.3, 0.6, 0.82),
                yoke_off=0.021, neck_dz=None, w=w_trunk, skip=lambda i, j: j in (23, 0))
    # fur trim around the neck opening of the vest
    Y = K.yoke(A24, (0.80,), 0.030)[0]
    roll(p, Y, unit(Y - np.array([0, YC, 1.36])), UP, 0.016, 'M_fur', cfn('#6e5d48', 0.2, 0.02, 15), src='trunk')
    # one pauldron (left shoulder) and wrist wraps
    B = np.radians(np.linspace(-120, 120, 8))
    xs = np.array([0.135, 0.19, 0.25, 0.305])
    Gs = K.arm.pts(xs[:, None], B[None, :], off=np.array([0.022, 0.034, 0.032, 0.028])[:, None], side=1)
    p.grid(Gs, 'M_leather', cfn('#2f2620', 0.2, 0.03, 16), closed=False, src='arm_L',
           w=lambda P, Wa: 0.5 * w_bones(P, {'clavicle_L': 1.0}) + 0.5 * Wa)
    for s in (1, -1):
        Gw = K.arm.pts(np.array([0.62, 0.655, 0.69, 0.72])[:, None], angles(10)[None, :], off=np.array([0.012, 0.013, 0.012, 0.010])[:, None], side=s)
        p.grid(Gw, 'M_cloth', cfn('#8a7d68', 0.15, 0.02, 17), flip=(s < 0), src='arm_' + SIDE[s])
    belt(p, 1.035, 0.022, 'M_leather', col('#3a2a1e'), h=0.03, t=0.007)
    return p


def bandit_legs(K):
    p = Piece('bandit_legs', K)
    c1 = cfn('#4d4a3d', 0.15, 0.06, 18, dirt=(0.25, 0.7, 0.3))
    c2 = cfn('#5a4636', 0.15, 0.06, 19, dirt=(0.25, 0.7, 0.3))
    trousers(p, 'M_cloth', c1, off=0.008, z_bot=0.30, color_r=c2)
    bc = cfn('#3a2c20', 0.14, 0.04, 20, dirt=(0.0, 0.12, 0.3))
    boots(p, 'M_leather', bc, top=0.34, off=0.008, sole=col('#1d1612'))
    fur = cfn('#6a5a46', 0.22, 0.02, 21)
    for s in (1, -1):
        for z, r in ((0.335, 0.020), (0.26, 0.016)):
            P, rad = leg_ring(K, z, 12, 0.012, s)
            roll(p, P, rad, UP, r, 'M_fur', fur, flip=(s < 0), src='leg_' + SIDE[s])
    return p


def bandit_head(K):
    p = Piece('bandit_head', K)
    o = 0.012
    spec = [('e', 90, o + 0.004, 0), ('e', 64, o + 0.004, 30), ('e', 44, o + 0.003, 40), ('e', 29, o + 0.006, 47),
            ('z', 1.712, o + 0.004, 52), ('z', 1.685, o, 54), ('z', 1.655, o, 56), ('z', 1.625, o, 58),
            ('z', 1.595, o + 0.004, 60), ('z', 1.565, o + 0.012, 30), ('z', 1.535, 0.020, 0), ('z', 1.505, 0.022, 0)]
    c = cfn('#3d4336', 0.16, 0.05, 22)
    G, AZ = hood(p, 'M_cloth', c, spec, ns=20, jf=3, face=(3, 9), src='upper')
    # face scarf over the nose and mouth
    az = np.radians(np.linspace(-66, 66, 11))
    zs = np.array([1.668, 1.645, 1.62, 1.595, 1.572])
    S = K.head.pts(zs[:, None], az[None, :], off=np.array([0.006, 0.007, 0.008, 0.009, 0.012])[:, None], hull=0.6)
    p.grid(S, 'M_cloth', cfn('#5c2f27', 0.15, 0.03, 23), closed=False, flip=True, src='head', w={'head': 1.0})
    return p


# ============================================================================= CHAIN
def chain_chest(K):
    p = Piece('chain_chest', K)
    mail = cfn('#8a8d92', 0.12, 0.015, 24)
    A = A24
    # mail: skirt, collar, sleeves (the torso is under the surcoat)
    T0 = K.torso_rows([1.00, 1.04], A, [0.018, 0.015], 0.9)
    S = K.drape(A, 1.00, [0.66, 0.74, 0.82, 0.89, 0.95], 0.0, min_off=0.018, flare=0.018, folds=(6, 0.004, 0.3), r_top=ring_r(T0[0]))
    p.grid(np.concatenate([S, T0], 0), 'M_metal_iron', mail, src='body', w=skirt_weights(z_full=0.72))
    Y = np.concatenate([K.yoke(A, (0.70, 1.0), 0.014), K.neck(A, (0.014, 0.034), (0.011, 0.008))], 0)
    p.grid(Y, 'M_metal_iron', mail, src='trunk')
    sleeves(p, 'M_metal_iron', mail, off=0.013, x_end=0.70, end_off=0.012)
    # surcoat
    sur = cfn('#6a2b24', 0.12, 0.07, 25, dirt=(0.55, 0.8, 0.3))
    off = [0.027, 0.024, 0.026, 0.026, 0.026, 0.025, 0.024, 0.023, 0.022]
    torso_shell(p, 'M_cloth', sur, off=off, hull=0.95, yoke_ks=(0.3, 0.6, 0.84), yoke_off=0.022, neck_dz=None,
                skirt=dict(zs=[0.57, 0.66, 0.75, 0.84, 0.92, 0.965], flare=0.04, min_off=0.026, folds=(4, 0.008, 0.0),
                           weights=dict(z_full=0.70)),
                skip=lambda i, j: i < 5 and j in (5, 6, 17, 18))
    belt(p, 1.05, 0.026, 'M_leather', col('#3d2b1e'), h=0.04, buckle=('M_metal_iron', '#8f8a80'), tail=4)
    gl = cfn('#4c3625', 0.12, 0.03, 26)
    for s in (1, -1):
        glove(p, s, 0.005, 'M_leather', gl, x0=0.70)
        Gc = K.arm.pts(np.array([0.655, 0.685, 0.715])[:, None], angles(10)[None, :], off=np.array([0.022, 0.018, 0.012])[:, None], side=s)
        p.grid(Gc, 'M_leather', gl, flip=(s < 0), src='arm_' + SIDE[s])
    return p


def chain_legs(K):
    p = Piece('chain_legs', K)
    mail = cfn('#84878c', 0.12, 0.015, 27)
    trousers(p, 'M_metal_iron', mail, off=0.009, z_bot=0.26)
    bc = cfn('#3b2b1f', 0.12, 0.04, 28, dirt=(0.0, 0.12, 0.3))
    boots(p, 'M_leather', bc, top=0.30, off=0.008, sole=col('#1d1612'), top_off=0.014)
    steel = cfn('#a9adb3', 0.08, 0.03, 29)
    for s in (1, -1):
        az = np.radians(np.linspace(-80, 80, 7))
        zs = np.array([0.435, 0.47, 0.505, 0.54, 0.57])
        dome = 0.014 + 0.014 * np.sin(np.linspace(0, math.pi, 5))[:, None] * np.cos(np.linspace(-1.2, 1.2, 7))[None, :]
        G = K.leg.pts(zs[:, None], az[None, :], off=dome, side=s, hull=1.0)
        p.grid(G, 'M_metal_steel', steel, closed=False, flip=(s < 0), src='leg_' + SIDE[s])
    return p


def chain_head(K):
    p = Piece('chain_head', K)
    o = 0.009
    spec = [('e', 90, o, 0), ('e', 64, o, 30), ('e', 44, o, 38), ('e', 27, o, 42), ('z', 1.705, o, 46),
            ('z', 1.675, o, 48), ('z', 1.645, o, 46), ('z', 1.615, o, 38), ('z', 1.588, o, 24),
            ('z', 1.565, o + 0.006, 0), ('z', 1.535, 0.018, 0), ('z', 1.505, 0.020, 0), ('z', 1.478, 0.024, 0)]
    G, AZ = hood(p, 'M_metal_iron', cfn('#8a8d92', 0.12, 0.015, 30), spec, ns=20, jf=3, face=(3, 8), src='upper')
    return p


# ============================================================================= ROBE
def robe_chest(K):
    p = Piece('robe_chest', K)
    c = cfn('#4b3d30', 0.12, 0.08, 31, dirt=(0.26, 0.55, 0.35))
    off = [0.022, 0.014, 0.024, 0.026, 0.024, 0.021, 0.018, 0.016, 0.015]
    A = angles(28)
    torso_shell(p, 'M_cloth', c, off=off, hull=0.9, A=A,
                skirt=dict(zs=[0.28, 0.40, 0.52, 0.64, 0.76, 0.87, 0.95], flare=0.075, power=1.1, min_off=0.02,
                           folds=(7, 0.022, 0.5), weights=dict(z_full=0.70, follow=0.8, shin=0.35)))
    # wide sleeves
    def so(x, B):
        return 0.014 + 0.05 * sstep(0.30, 0.70, x) * (1.0 + 0.9 * np.maximum(0, -np.cos(B)))
    Gs = sleeves(p, 'M_cloth', c, off=so, x_end=0.70)
    for s in (1, -1):
        p.lining(Gs[s][-3:], 'M_cloth', col('#2a221b'), flip=(s < 0), src='arm_' + SIDE[s])
        # tight under sleeve at the wrist
        Gu = K.arm.pts(np.array([0.56, 0.66, 0.74])[:, None], angles(8)[None, :], off=np.array([0.006, 0.006, 0.004])[:, None], side=s)
        p.grid(Gu, 'M_cloth', col('#6e6250'), flip=(s < 0), src='arm_' + SIDE[s])
    P, rad = torso_ring(K, 1.045, A, 0.016, 0.9)
    roll(p, P, rad, UP, 0.009, 'M_rope', col('#a8946a'), src='body')
    return p


def robe_legs(K):
    p = Piece('robe_legs', K)
    c = cfn('#3a3229', 0.12, 0.06, 32)
    trousers(p, 'M_cloth', c, off=0.008, z_bot=0.13)
    boots(p, 'M_leather', cfn('#3a2c21', 0.12, 0.04, 33), top=0.17, off=0.007, sole=col('#1d1612'))
    return p


def robe_head(K):
    p = Piece('robe_head', K)
    def fwd(o):
        return lambda az: o + 0.03 * sstep(math.radians(75), math.radians(35), np.abs(az))
    spec = [('e', 90, 0.035, 0), ('e', 66, 0.036, 30), ('e', 46, fwd(0.03), 40), ('e', 28, fwd(0.03), 50),
            ('z', 1.712, fwd(0.028), 58), ('z', 1.68, fwd(0.026), 62), ('z', 1.645, fwd(0.026), 64), ('z', 1.61, fwd(0.028), 62),
            ('z', 1.575, fwd(0.034), 52), ('z', 1.545, 0.036, 0), ('z', 1.515, 0.030, 0), ('z', 1.485, 0.030, 0)]
    c = cfn('#4b3d30', 0.12, 0.08, 34)
    G, AZ = hood(p, 'M_cloth', c, spec, ns=20, jf=3, face=(2, 9), src='upper', hull=1.0)
    p.lining(G[1:10], 'M_cloth', col('#1c1611'), flip=True, closed=True, weld=True,
             skip=face_skip(20, 3, 1, 8), src='upper')
    return p


# ============================================================================= PLATE / ROYAL
def plate_arms(p, K, steel, mail, trim=None, big=1.0, gaunt=True):
    for s in (1, -1):
        src = 'arm_' + SIDE[s]
        # mail sleeve
        B = angles(10)
        Gm = K.sleeve_rows([0.165, 0.21, 0.30, 0.40, 0.47, 0.54, 0.62, 0.70], B, 0.010, side=s)
        p.grid(Gm, 'M_metal_iron', mail, flip=(s < 0), src=src)
        # pauldron: 3 lames
        Bp = np.radians(np.linspace(-125, 125, 9))
        xs = np.array([0.120, 0.165, 0.215, 0.218, 0.262, 0.265, 0.305 + 0.02 * (big - 1)])
        of = np.array([0.020, 0.040, 0.040, 0.034, 0.034, 0.028, 0.028]) * big
        Gp = K.arm.pts(xs[:, None], Bp[None, :], off=of[:, None], side=s, hull=1.0)
        cl, ua = 'clavicle_' + SIDE[s], 'upper_arm_' + SIDE[s]
        p.grid(Gp, steel[0], steel[1], closed=False, flip=(s < 0), src=src, split=(2, 4),
               w=lambda P, Wa, cl=cl, ua=ua: w_bones(P, {cl: 1.0}) * (1 - 0.55 * sstep(0.16, 0.30, np.abs(P[:, 0])))[:, None]
               + w_bones(P, {ua: 1.0}) * (0.55 * sstep(0.16, 0.30, np.abs(P[:, 0])))[:, None])
        # rerebrace, couter, vambrace
        Gr = K.arm.pts(np.array([0.30, 0.33, 0.40, 0.425])[:, None], B[None, :], off=np.array([0.016, 0.019, 0.019, 0.016])[:, None], side=s, hull=1.0)
        p.grid(Gr, steel[0], steel[1], flip=(s < 0), src=src, w=('rigid', ua, 0.9))
        Gc = K.arm.pts(np.array([0.425, 0.447, 0.47, 0.493, 0.515])[:, None], B[None, :],
                       off=np.array([0.017, 0.028, 0.033, 0.028, 0.017])[:, None], side=s, hull=1.0)
        p.grid(Gc, steel[0], steel[1], flip=(s < 0), src=src)
        Gv = K.arm.pts(np.array([0.515, 0.55, 0.63, 0.70])[:, None], B[None, :], off=np.array([0.016, 0.020, 0.018, 0.016])[:, None], side=s, hull=1.0)
        p.grid(Gv, steel[0], steel[1], flip=(s < 0), src=src, w=('rigid', 'forearm_' + SIDE[s], 0.9))
        if gaunt:
            glove(p, s, 0.007, steel[0], steel[1], x0=0.70)
            Gg = K.arm.pts(np.array([0.655, 0.70, 0.722])[:, None], B[None, :], off=np.array([0.030, 0.022, 0.016])[:, None], side=s, hull=1.0)
            p.grid(Gg, steel[0], steel[1], flip=(s < 0), src=src)


def plate_torso(p, K, steel, mail, gorget_h=0.03, fauld_c=None):
    A = A24
    prof = K.torso.blur(0.03)
    zs = [1.075, 1.11, 1.16, 1.22, 1.28, 1.34, 1.40]
    off = np.array([0.020, 0.018, 0.022, 0.026, 0.028, 0.026, 0.024])
    ridge = 0.010 * np.maximum(np.cos(wrap(A)), 0) ** 6
    T = prof.pts(np.array(zs)[:, None], A[None, :], off=off[:, None] + ridge[None, :] * np.array([0.3, 0.6, 1, 1, 1, 0.6, 0.3])[:, None], hull=1.0)
    Y = K.yoke(A, (0.3, 0.6, 0.85, 1.0), (0.024, 0.024, 0.022, 0.020))
    N = K.neck(A, (0.010, gorget_h), (0.018, 0.016))
    G = np.concatenate([T, Y, N], 0)
    p.grid(G, steel[0], steel[1], src='trunk', w=w_trunk, split=(10,))
    # fauld: 3 lames
    zf = [0.915, 0.975, 0.97, 1.025, 1.02, 1.08]
    of = [0.034, 0.030, 0.030, 0.026, 0.026, 0.022]
    F = K.torso_rows(zf, A, of, 1.0)
    p.grid(F, steel[0], fauld_c or steel[1], src='body', split=(1, 3), w=skirt_weights(z_free=1.02, z_full=0.86, follow=0.35))
    # mail skirt
    T0 = K.torso_rows([0.97], A, [0.022], 1.0)
    S = K.drape(A, 0.97, [0.80, 0.86, 0.92], 0.0, min_off=0.02, flare=0.012, r_top=ring_r(T0[0]))
    p.grid(np.concatenate([S, T0], 0), 'M_metal_iron', mail, src='body', w=skirt_weights(z_full=0.78))


def plate_chest(K):
    p = Piece('plate_chest', K)
    steel = ('M_metal_steel', cfn('#b4b9c0', 0.08, 0.04, 35))
    mail = cfn('#6f7378', 0.12, 0.015, 36)
    plate_torso(p, K, steel, mail)
    plate_arms(p, K, steel, mail)
    belt(p, 1.075, 0.024, 'M_cloth', col('#b4521c'), h=0.035, t=0.005, hull=1.0)
    return p


def plate_leg_parts(p, K, steel, mail, trim=None):
    trousers(p, 'M_metal_iron', mail, off=0.008, z_bot=0.20)
    L = angles(12)
    for s in (1, -1):
        src = 'leg_' + SIDE[s]
        th, sh = 'thigh_' + SIDE[s], 'shin_' + SIDE[s]
        # cuisse (front and outside of the thigh)
        az = np.radians(np.linspace(-95, 150, 9))
        zs = np.array([0.555, 0.60, 0.68, 0.76, 0.82])
        G = K.leg.pts(zs[:, None], az[None, :], off=np.array([0.018, 0.022, 0.024, 0.024, 0.020])[:, None], side=s, hull=1.0)
        p.grid(G, steel[0], steel[1], closed=False, flip=(s < 0), src=src, w=('rigid', th, 0.85))
        # poleyn
        az = np.radians(np.linspace(-110, 110, 9))
        zs = np.array([0.43, 0.465, 0.50, 0.535, 0.565])
        dome = np.array([0.018, 0.030, 0.036, 0.030, 0.018])[:, None] + 0.006 * np.cos(np.linspace(-1.4, 1.4, 9))[None, :]
        G = K.leg.pts(zs[:, None], az[None, :], off=dome, side=s, hull=1.0)
        p.grid(G, steel[0], trim or steel[1], closed=False, flip=(s < 0), src=src)
        # greave
        zs = np.array([0.115, 0.16, 0.25, 0.35, 0.425, 0.445])
        G = K.leg.pts(zs[:, None], L[None, :], off=np.array([0.016, 0.018, 0.020, 0.020, 0.018, 0.014])[:, None], side=s, hull=1.0)
        p.grid(G, steel[0], steel[1], flip=(s < 0), src=src, w=('rigid', sh, 0.9))
        # sabaton
        shoe(p, s, 0.009, steel[0], steel[1], toe=0.012)
        G = K.leg.pts(np.array([0.07, 0.10, 0.125])[:, None], L[None, :], off=np.array([0.012, 0.014, 0.018])[:, None], side=s, hull=1.0)
        p.grid(G, steel[0], steel[1], flip=(s < 0), src=src)


def plate_legs(K):
    p = Piece('plate_legs', K)
    plate_leg_parts(p, K, ('M_metal_steel', cfn('#b4b9c0', 0.08, 0.04, 37)), cfn('#6f7378', 0.12, 0.015, 38))
    return p


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


def plate_head(K):
    p = Piece('plate_head', K)
    steel = cfn('#aeb3ba', 0.08, 0.04, 39)
    zs = [1.545, 1.60, 1.66, 1.72, 1.775, 1.815, 1.838, 1.846]
    rx = [0.112, 0.110, 0.108, 0.106, 0.100, 0.078, 0.045, 0.0005]
    ry = [0.132, 0.132, 0.131, 0.128, 0.120, 0.094, 0.055, 0.0005]
    G = helm_rows(K, zs, rx, ry)
    G[..., 1] -= 0.012 * np.maximum(np.cos(wrap(angles(24))), 0)[None, :] ** 4 * np.array([0.6, 1, 1, 1, 0.8, 0.5, 0.2, 0])[:, None]
    p.grid(G, 'M_metal_steel', steel, weld=True, w={'head': 1.0}, src='head')
    # eye slit + mail collar
    for s in (1, -1):
        az = np.radians(np.linspace(8, 62, 5)) * s
        S = np.stack([helm_point(K, G, zs, a, 1.694) for a in az]), np.stack([helm_point(K, G, zs, a, 1.682) for a in az])
        Q = np.stack([S[1], S[0]]) if s > 0 else np.stack([S[0], S[1]])
        p.grid(Q, 'M_metal_iron', col('#0c0c0d'), closed=False, w={'head': 1.0}, src='head', ao=0.0)
    spec = [('z', 1.56, 0.020, 0), ('z', 1.53, 0.020, 0), ('z', 1.50, 0.022, 0), ('z', 1.476, 0.026, 0)]
    Gm, AZ = _hood_rows(K, spec, 20, 0, 1.0, None)
    p.grid(Gm, 'M_metal_iron', cfn('#6f7378', 0.12, 0.015, 40), flip=True, src='upper')
    return p


def helm_point(K, G, zs, az, z, lift=0.0025):
    """point on a helm grid (rows zs, 24 columns) at azimuth az / height z, lifted off the surface."""
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


def royal_chest(K):
    p = Piece('royal_chest', K)
    gold = ('M_metal_gold', cfn('#b08d3e', 0.14, 0.04, 41))
    dark = cfn('#5d6068', 0.12, 0.015, 42)
    plate_torso(p, K, gold, dark, gorget_h=0.06)
    plate_arms(p, K, gold, dark, big=1.25)
    # torn cape
    cape = cfn('#5b1f2a', 0.14, 0.09, 43, dirt=(0.30, 0.7, 0.4))
    az = np.radians(np.linspace(100, 260, 11))
    zs = np.array([1.50, 1.44, 1.34, 1.22, 1.10, 0.98, 0.85, 0.72, 0.58, 0.45, 0.33])
    G = np.zeros((len(zs), len(az), 3))
    for i, z in enumerate(zs):
        r = K.torso.rad(min(z, 1.45), az, 1.0) + 0.045 + 0.05 * sstep(1.3, 0.4, z) + 0.012 * np.cos(5 * az + 2.0 * i) * sstep(1.45, 1.0, z)
        if z > 1.45:
            r = K.torso.rad(1.45, az, 1.0) + 0.040
        G[i] = torso_center(z) + dirxy(az) * r[:, None]
    G[0, :, 2] = 1.535
    G[-1, :, 2] += 0.09 * vnoise(np.stack([az * 3, az * 0, az * 0], 1), 1.0, 9)

    def capew(P, Wa):
        z = P[:, 2]
        W = np.zeros_like(Wa)
        t = sstep(1.50, 1.30, z)
        W[:, BI['spine_03']] = 1 - t
        t2 = sstep(1.30, 1.05, z)
        W[:, BI['spine_02']] = t * (1 - t2)
        t3 = sstep(1.05, 0.80, z)
        W[:, BI['hips']] = t * t2 * (1 - 0.45 * t3)
        sl = sstep(-0.08, 0.08, P[:, 0])
        W[:, BI['thigh_L']] = t * t2 * 0.45 * t3 * sl
        W[:, BI['thigh_R']] = t * t2 * 0.45 * t3 * (1 - sl)
        return W
    p.grid(G, 'M_cloth', cape, closed=False, flip=True, src='body', w=capew)
    p.lining(G, 'M_cloth', lambda P: cape(P) * 0.6, closed=False, flip=True, src='body', w=capew, inset=0.006)
    return p


def royal_legs(K):
    p = Piece('royal_legs', K)
    plate_leg_parts(p, K, ('M_metal_steel', cfn('#7d8087', 0.1, 0.04, 44)), cfn('#5d6068', 0.12, 0.015, 45),
                    trim=cfn('#b08d3e', 0.14, 0.04, 46))
    return p


def royal_head(K):
    p = Piece('royal_head', K)
    steel = cfn('#7d8087', 0.1, 0.04, 47)
    zs = [1.555, 1.60, 1.66, 1.72, 1.775, 1.82, 1.855, 1.875]
    rx = [0.106, 0.106, 0.105, 0.103, 0.095, 0.070, 0.035, 0.0005]
    ry = [0.128, 0.130, 0.130, 0.126, 0.116, 0.088, 0.045, 0.0005]
    G = helm_rows(K, zs, rx, ry)
    G[..., 1] -= 0.03 * np.maximum(np.cos(wrap(angles(24))), 0)[None, :] ** 3 * np.array([0.5, 1, 1, 0.6, 0.2, 0, 0, 0])[:, None]
    G[5:, :, 1] += np.array([0.012, 0.03, 0.04])[:, None]
    p.grid(G, 'M_metal_steel', steel, weld=True, w={'head': 1.0}, src='head')
    for s in (1, -1):
        az = np.radians(np.linspace(8, 55, 5)) * s
        S = np.stack([helm_point(K, G, zs, a, 1.694) for a in az]), np.stack([helm_point(K, G, zs, a, 1.683) for a in az])
        Q = np.stack([S[1], S[0]]) if s > 0 else np.stack([S[0], S[1]])
        p.grid(Q, 'M_metal_iron', col('#0c0c0d'), closed=False, w={'head': 1.0}, src='head', ao=0.0)
    # crown fused around the skull
    gold = cfn('#b08d3e', 0.16, 0.03, 48)
    A = angles(24)
    base = np.stack([helm_point(K, G, zs, a, 1.745, 0.004) for a in A])
    top = np.stack([helm_point(K, G, zs, a, 1.775, 0.010) for a in A])
    spike = top + (dirxy(A) * 0.012 + UP * 0.035) * (np.arange(24) % 2)[:, None]
    p.grid(np.stack([base, top, spike]), 'M_metal_gold', gold, w={'head': 1.0}, src='head')
    spec = [('z', 1.57, 0.018, 0), ('z', 1.535, 0.020, 0), ('z', 1.50, 0.024, 0), ('z', 1.476, 0.028, 0)]
    Gm, AZ = _hood_rows(K, spec, 20, 0, 1.0, None)
    p.grid(Gm, 'M_metal_iron', cfn('#5d6068', 0.12, 0.015, 49), flip=True, src='upper')
    return p


# ----------------------------------------------------------------------------- registry
PIECES = {
    'peasant_head': (peasant_head, ['hair'], 'linen coif with loose ties; covers the scalp and ears'),
    'peasant_chest': (peasant_chest, ['body_torso'], 'belted wool tunic, sleeves rolled above the elbow: body_arms and body_hands stay visible'),
    'peasant_legs': (peasant_legs, ['body_legs', 'body_feet'], 'patched trousers, leg wraps, turn shoes'),
    'leather_head': (leather_head, ['hair'], 'leather arming cap with ear and neck flaps'),
    'leather_chest': (leather_chest, ['body_torso', 'body_arms'], 'boiled leather jerkin over a padded gambeson, shoulder caps, bracers, belt; bare hands'),
    'leather_legs': (leather_legs, ['body_legs', 'body_feet'], 'leather trousers, tall cuffed boots'),
    'bandit_head': (bandit_head, ['hair', 'beard'], 'ragged hood with a face scarf over nose and mouth'),
    'bandit_chest': (bandit_chest, ['body_torso', 'body_arms'], 'fur trimmed hide vest over a dirty shirt, one boiled leather pauldron (left), wrist wraps, belt; bare hands'),
    'bandit_legs': (bandit_legs, ['body_legs', 'body_feet'], 'mismatched patched hose, fur wrapped boots'),
    'chain_head': (chain_head, ['hair', 'beard'], 'mail coif with an open face and a mantle over the shoulders'),
    'chain_chest': (chain_chest, ['body_torso', 'body_arms', 'body_hands'], 'mail hauberk under a belted surcoat, leather mitten gloves'),
    'chain_legs': (chain_legs, ['body_legs', 'body_feet'], 'mail chausses, steel knee cops, leather boots'),
    'robe_head': (robe_head, ['hair'], 'deep cowl with a shoulder mantle, dark lining'),
    'robe_chest': (robe_chest, ['body_torso', 'body_arms'], 'monk robe to mid shin with wide sleeves (tight under sleeves at the wrists) and a rope belt; bare hands'),
    'robe_legs': (robe_legs, ['body_legs', 'body_feet'], 'under trousers and soft ankle boots'),
    'plate_head': (plate_head, ['hair', 'beard'], 'closed great helm with eye slits and a mail collar'),
    'plate_chest': (plate_chest, ['body_torso', 'body_arms', 'body_hands'], 'cuirass, laminated pauldrons, couters, vambraces, mitten gauntlets, fauld over a mail skirt, ember sash'),
    'plate_legs': (plate_legs, ['body_legs', 'body_feet'], 'cuisses, poleyns, greaves, sabatons over mail'),
    'royal_head': (royal_head, ['hair', 'beard'], 'bascinet fused with a tarnished gold crown, mail aventail'),
    'royal_chest': (royal_chest, ['body_torso', 'body_arms', 'body_hands'], 'gilded cuirass with a high gorget, large pauldrons, torn cape to the calves'),
    'royal_legs': (royal_legs, ['body_legs', 'body_feet'], 'dark steel leg harness with gilded poleyns'),
}
SETS = ['peasant', 'leather', 'bandit', 'chain', 'robe', 'plate', 'royal']
BUDGET = {'head': 1200, 'chest': 3000, 'legs': 2200}


def piece_morphs(name):
    if name.endswith('_head'):
        return HEAD_MORPHS, ['muscular', 'thin', 'shoulder_width', 'chest_size', 'nose_length',
                                             'nose_width', 'nose_tip', 'nose_bridge', 'mouth_open', 'ear_point']
    return BODY_MORPHS, []
