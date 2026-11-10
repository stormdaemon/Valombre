"""CHAIN set: mail coif, mail hauberk under a belted surcoat with leather gloves, mail chausses with knee cops."""
from outfit_parts import *

MAIL = '#8d9095'


def chain_chest(K):
    p = Piece('chain_chest', K)
    mail = cfn(MAIL, 0.14, 0.012, 24)
    A = A24
    # mail hauberk: skirt, collar, sleeves (its torso is hidden under the surcoat)
    T0 = K.torso_rows([1.00, 1.04], A, [0.018, 0.015], 0.9)
    S = K.drape(A, 1.00, [0.655, 0.74, 0.82, 0.89, 0.95], 0.0, min_off=0.018, flare=0.016, folds=(6, 0.004, 0.3),
                r_top=ring_r(T0[0]))
    S[0, :, 2] += 0.008 * np.cos(12 * A)
    wM = skirt_weights(z_full=0.74)
    Gm = np.concatenate([S, T0], 0)
    p.grid(Gm, 'M_metal_iron', cfn(MAIL, 0.14, 0.012, 24, dirt=(0.62, 0.8, 0.25)), src='body', w=wM)
    p.lining(Gm[0:2], 'M_metal_iron', col('#3c3e42'), src='body', w=wM)
    Y = np.concatenate([K.yoke(A, (0.66, 1.0), 0.013), K.neck(A, (0.014, 0.034), (0.011, 0.008))], 0)
    p.grid(Y, 'M_metal_iron', mail, src='trunk')
    sleeves(p, 'M_metal_iron', mail, off=lambda x, B: 0.012 + 0.003 * sstep(0.3, 0.5, x), x_end=0.70, end_off=0.012)
    # surcoat: slit front and back, cream border, pale lozenge on the chest
    As = SLIT_A
    red = cfn('#6e2a22', 0.13, 0.07, 25, dirt=(0.53, 0.85, 0.35))
    trim = cfn('#b5a076', 0.10, 0.05, 26, dirt=(0.53, 0.75, 0.3))
    zs = [0.965, 1.00, 1.04, 1.08, 1.13, 1.19, 1.25, 1.31, 1.36, 1.40]
    off = [0.030, 0.028, 0.024, 0.027, 0.028, 0.028, 0.027, 0.026, 0.025, 0.024]
    T = K.torso_rows(zs, As, off, 0.95)
    sz = [0.545, 0.575, 0.66, 0.75, 0.84, 0.91]
    S = K.drape(As, zs[0], sz, 0.0, min_off=0.028, flare=0.05, folds=(5, 0.008, 0.6), r_top=ring_r(T[0]))
    Y = K.yoke(As, (0.3, 0.6, 0.76, 0.85), (0.024, 0.024, 0.023, 0.024))
    G = np.concatenate([S, T, Y], 0)
    wS = skirt_weights(z_free=0.97, z_full=0.76, xw=0.03)

    def slit(i, j):
        return i < 4 and j in (23, 11)
    p.grid(G[0:2], 'M_cloth', trim, src='body', w=wS, skip=slit)
    p.grid(G[1:19], 'M_cloth', red, src='body', w=wS, skip=lambda i, j: slit(i + 1, j))
    p.grid(G[18:20], 'M_cloth', trim, src='body', w=w_trunk)
    p.lining(G[0:3], 'M_cloth', lambda P: red(P) * 0.55, src='body', w=wS, skip=slit)
    lz = [K.torso.pts(z, a, off=0.031, hull=0.95) for z, a in ((1.375, 0.0), (1.30, 0.42), (1.225, 0.0), (1.30, -0.42), (1.30, 0.0))]
    lz[4] = lz[4] + np.array([0, -0.004, 0])
    p.add(lz, [[4, 0, 3], [4, 3, 2], [4, 2, 1], [4, 1, 0]], 'M_cloth', col('#c9bd9a'), src='trunk', w=w_trunk)
    belt(p, 1.05, 0.027, 'M_leather', col('#3d2b1e'), h=0.04, buckle=('M_metal_iron', '#9a958a'), tail=5, hull=0.95)
    pouch(p, 1.012, -1.15, 0.028, 'M_leather', col('#46301f'))
    gl = cfn('#4c3625', 0.12, 0.03, 26)
    for s in (1, -1):
        glove(p, s, 0.005, 'M_leather', gl, x0=0.70)
        Gc = arm_tube(p, s, [0.648, 0.668, 0.70, 0.722], [0.024, 0.023, 0.016, 0.011], 'M_leather', gl)
        p.lining(Gc[:2], 'M_leather', col('#2a1d14'), flip=(s < 0), src='arm_' + SIDE[s])
    return p


def chain_legs(K):
    p = Piece('chain_legs', K)
    mail = cfn('#84878c', 0.14, 0.012, 27, dirt=(0.25, 0.5, 0.2))
    trousers(p, 'M_metal_iron', mail, off=0.009, z_bot=0.26)
    bc = cfn('#3b2b1f', 0.12, 0.04, 28, dirt=(0.0, 0.14, 0.35))
    boots(p, 'M_leather', bc, top=0.31, off=0.008, sole=col('#1d1612'), top_off=0.016)
    steel = cfn('#a9adb3', 0.08, 0.03, 29)
    for s in (1, -1):
        src = 'leg_' + SIDE[s]
        knee_cop(p, s, 'M_metal_steel', steel)
        P, rad = leg_ring(K, 0.292, 12, 0.014, s)                      # turned boot cuff
        band(p, P, rad, UP, 0.05, 0.006, 'M_leather', col('#4a382a'), flip=(s < 0), src=src)
        P, rad = leg_ring(K, 0.125, 12, 0.011, s)                      # ankle strap
        band(p, P, rad, UP, 0.016, 0.004, 'M_leather', col('#2a1e16'), flip=(s < 0), src=src)
        for z in (0.452, 0.552):                                       # knee cop straps
            P, rad = leg_ring(K, z, 12, 0.010, s)
            band(p, P, rad, UP, 0.014, 0.003, 'M_leather', col('#2f2219'), flip=(s < 0), src=src, bevel=False)
    return p


def chain_head(K):
    p = Piece('chain_head', K)
    o = 0.010
    spec = [('e', 90, o, 0), ('e', 64, o, 30), ('e', 44, o, 38), ('e', 27, o, 42), ('z', 1.705, o, 46),
            ('z', 1.675, o, 48), ('z', 1.645, o, 46), ('z', 1.615, o, 38), ('z', 1.588, o + 0.002, 24),
            ('z', 1.563, o + 0.008, 0), ('n', 0.050, 0.021, 0), ('n', 0.026, 0.028, 0), ('n', 0.004, 0.034, 0)]
    mail = cfn(MAIL, 0.14, 0.012, 30)
    G, AZ = hood(p, 'M_metal_iron', mail, spec, ns=20, jf=3, face=(3, 8), src='upper')
    face_rim(p, G, 20, 3, 3, 8, 'M_leather', col('#4a3526'), r=0.0045, w={'head': 1.0})
    return p


PIECES = {
    'chain_head': (chain_head, ['hair', 'beard'], 'mail coif with an open face, leather edging, short mail collar that covers the collar of any chest piece'),
    'chain_chest': (chain_chest, ['body_torso', 'body_arms', 'body_hands'], 'mail hauberk (skirt to mid thigh) under a belted surcoat slit front and back, pouch, leather mitten gloves with flared cuffs'),
    'chain_legs': (chain_legs, ['body_legs', 'body_feet'], 'mail chausses, steel knee cops with fan plates, leather boots with turned cuffs'),
}
