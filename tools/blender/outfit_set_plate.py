"""PLATE set (knights of the Order of the Ember) and the shared plate harness builders used by ROYAL."""
from outfit_parts import *


def plate_arms(p, K, steel, mail, trim=None, big=1.0, gaunt=True):
    for s in (1, -1):
        src = 'arm_' + SIDE[s]
        B = angles(10)
        cl, ua, fa = 'clavicle_' + SIDE[s], 'upper_arm_' + SIDE[s], 'forearm_' + SIDE[s]
        Gm = K.sleeve_rows([0.165, 0.21, 0.30, 0.40, 0.47, 0.54, 0.62, 0.70], B, 0.010, side=s)     # mail sleeve
        p.grid(Gm, 'M_metal_iron', mail, flip=(s < 0), src=src)
        # pauldron: 3 lames
        Bp = np.radians(np.linspace(-125, 125, 9))
        xs = np.array([0.120, 0.165, 0.215, 0.218, 0.262, 0.265, 0.305 + 0.02 * (big - 1)])
        of = np.array([0.020, 0.040, 0.040, 0.034, 0.034, 0.028, 0.028]) * big
        arm_tube(p, s, xs, of, steel[0], steel[1], B=Bp, closed=False, hull=1.0, split=(2, 4),
                 w=lambda P, Wa, cl=cl, ua=ua: w_bones(P, {cl: 1.0}) * (1 - 0.55 * sstep(0.16, 0.30, np.abs(P[:, 0])))[:, None]
                 + w_bones(P, {ua: 1.0}) * (0.55 * sstep(0.16, 0.30, np.abs(P[:, 0])))[:, None])
        # rerebrace, couter, vambrace
        arm_tube(p, s, [0.30, 0.33, 0.40, 0.425], [0.016, 0.019, 0.019, 0.016], steel[0], steel[1], hull=1.0, w=('rigid', ua, 0.9))
        arm_tube(p, s, [0.425, 0.447, 0.47, 0.493, 0.515], [0.017, 0.028, 0.033, 0.028, 0.017], steel[0], trim or steel[1], hull=1.0)
        arm_tube(p, s, [0.515, 0.55, 0.63, 0.70], [0.016, 0.020, 0.018, 0.016], steel[0], steel[1], hull=1.0, w=('rigid', fa, 0.9))
        if gaunt:
            glove(p, s, 0.007, steel[0], steel[1], x0=0.70)
            arm_tube(p, s, [0.655, 0.70, 0.722], [0.030, 0.022, 0.016], steel[0], steel[1], hull=1.0)


def plate_torso(p, K, steel, mail, gorget=((0.010, 0.030), (0.018, 0.016)), fauld_c=None):
    A = A24
    prof = K.torso.blur(0.03)
    zs = [1.075, 1.11, 1.16, 1.22, 1.28, 1.34, 1.40]
    off = np.array([0.020, 0.018, 0.022, 0.026, 0.028, 0.026, 0.024])
    ridge = 0.010 * np.maximum(np.cos(wrap(A)), 0) ** 6
    T = prof.pts(np.array(zs)[:, None], A[None, :], off=off[:, None] + ridge[None, :] * np.array([0.3, 0.6, 1, 1, 1, 0.6, 0.3])[:, None], hull=1.0)
    Y = K.yoke(A, (0.3, 0.6, 0.85, 1.0), (0.024, 0.024, 0.022, 0.020))
    N = K.neck(A, gorget[0], gorget[1])
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


def plate_leg_parts(p, K, steel, mail, trim=None):
    trousers(p, 'M_metal_iron', mail, off=0.008, z_bot=0.20)
    for s in (1, -1):
        th, sh = 'thigh_' + SIDE[s], 'shin_' + SIDE[s]
        az = np.radians(np.linspace(-95, 150, 9))                       # cuisse: front and outside of the thigh
        leg_tube(p, s, [0.555, 0.60, 0.68, 0.76, 0.82], [0.018, 0.022, 0.024, 0.024, 0.020], steel[0], steel[1], A=az,
                 closed=False, hull=1.0, w=('rigid', th, 0.85))
        knee_cop(p, s, steel[0], trim or steel[1], r=0.020, bulge=0.018, z0=0.43, z1=0.565, half=110)
        leg_tube(p, s, [0.115, 0.16, 0.25, 0.35, 0.425, 0.445], [0.016, 0.018, 0.020, 0.020, 0.018, 0.014], steel[0], steel[1],
                 hull=1.0, w=('rigid', sh, 0.9))                        # greave
        shoe(p, s, 0.009, steel[0], steel[1], toe=0.012)               # sabaton
        leg_tube(p, s, [0.07, 0.10, 0.125], [0.012, 0.014, 0.018], steel[0], steel[1], hull=1.0)


def eye_slits(p, K, G, zs, z0=1.682, z1=1.694, a0=8, a1=62):
    for s in (1, -1):
        az = np.radians(np.linspace(a0, a1, 5)) * s
        top = np.stack([helm_point(K, G, zs, a, z1) for a in az])
        bot = np.stack([helm_point(K, G, zs, a, z0) for a in az])
        Q = np.stack([bot, top]) if s > 0 else np.stack([top, bot])
        p.grid(Q, 'M_metal_iron', col('#0c0c0d'), closed=False, w={'head': 1.0}, src='head', ao=0.0)


def plate_chest(K):
    p = Piece('plate_chest', K)
    steel = ('M_metal_steel', cfn('#b4b9c0', 0.08, 0.04, 35))
    mail = cfn('#6f7378', 0.12, 0.015, 36)
    plate_torso(p, K, steel, mail)
    plate_arms(p, K, steel, mail)
    belt(p, 1.075, 0.024, 'M_cloth', col('#b4521c'), h=0.035, t=0.005, hull=1.0)
    return p


def plate_legs(K):
    p = Piece('plate_legs', K)
    plate_leg_parts(p, K, ('M_metal_steel', cfn('#b4b9c0', 0.08, 0.04, 37)), cfn('#6f7378', 0.12, 0.015, 38))
    return p


def plate_head(K):
    p = Piece('plate_head', K)
    steel = cfn('#aeb3ba', 0.08, 0.04, 39)
    zs = [1.545, 1.60, 1.66, 1.72, 1.775, 1.815, 1.838, 1.846]
    rx = [0.112, 0.110, 0.108, 0.106, 0.100, 0.078, 0.045, 0.0005]
    ry = [0.132, 0.132, 0.131, 0.128, 0.120, 0.094, 0.055, 0.0005]
    G = helm_rows(K, zs, rx, ry)
    G[..., 1] -= 0.012 * np.maximum(np.cos(wrap(angles(24))), 0)[None, :] ** 4 * np.array([0.6, 1, 1, 1, 0.8, 0.5, 0.2, 0])[:, None]
    p.grid(G, 'M_metal_steel', steel, weld=True, w={'head': 1.0}, src='head')
    eye_slits(p, K, G, zs)
    aventail(p, 'M_metal_iron', cfn('#6f7378', 0.12, 0.015, 40), top_z=1.56, top_off=0.020)
    return p


PIECES = {
    'plate_head': (plate_head, ['hair', 'beard'], 'closed great helm with eye slits and a mail collar'),
    'plate_chest': (plate_chest, ['body_torso', 'body_arms', 'body_hands'], 'cuirass, laminated pauldrons, couters, vambraces, mitten gauntlets, fauld over a mail skirt, ember sash'),
    'plate_legs': (plate_legs, ['body_legs', 'body_feet'], 'cuisses, poleyns, greaves, sabatons over mail'),
}
