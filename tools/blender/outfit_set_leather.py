"""LEATHER set: leather arming cap, boiled leather jerkin over a padded gambeson with bracers, leather
trousers and tall boots."""
from outfit_parts import *


def quilt(base, n_cols, amount=0.10):
    """colour function for a quilted grid: darker seams on every other column (needs grid shaped input)."""
    def f(P):
        c = base(P)
        return c
    return f


def leather_chest(K):
    p = Piece('leather_chest', K)
    gamb = cfn('#9a8b6c', 0.08, 0.05, 6, dirt=(0.80, 0.95, 0.25))
    lea = cfn('#523a26', 0.14, 0.05, 7)
    dark = cfn('#3a281b', 0.14, 0.05, 8)
    A = A24
    ridge = 0.0035 * (np.arange(24) % 2)                    # quilting: every other column is a ridge
    seam = (1.0 - 0.16 * (1 - np.arange(24) % 2))[None, :, None]
    # gambeson: quilted skirt + standing collar + quilted sleeves (its torso is hidden under the jerkin)
    T0 = K.torso_rows([1.00, 1.04], A, np.array([0.017, 0.013])[:, None] + ridge[None, :] * 0.5, 0.8)
    S = K.drape(A, 1.00, [0.83, 0.885, 0.945], 0.0, min_off=0.017, flare=0.024, r_top=ring_r(T0[0]))
    S += dirxy(A)[None] * (ridge[None, :, None] * np.array([1.6, 1.3, 1.0])[:, None, None])
    G = np.concatenate([S, T0], 0)
    wG = skirt_weights(z_full=0.80)
    p.grid(G, 'M_cloth', gamb(G) * seam, src='body', w=wG)
    p.lining(G[0:2], 'M_cloth', col('#4a4232'), src='body', w=wG)
    Y = np.concatenate([K.yoke(A, (0.72, 1.0), 0.012), K.neck(A, (0.016, 0.036), (0.010, 0.007))], 0)
    p.grid(Y, 'M_cloth', gamb, src='trunk')
    B = angles(10)
    rb = 0.003 * (np.arange(10) % 2)
    sb = (1.0 - 0.16 * (1 - np.arange(10) % 2))[None, :, None]
    for s in (1, -1):
        xs = [0.165, 0.205, 0.25, 0.31, 0.37, 0.43, 0.47, 0.51, 0.54]
        Gs = K.sleeve_rows(xs, B, np.full((len(xs), 1), 0.012) + rb[None, :], side=s)
        p.grid(Gs, 'M_cloth', gamb(Gs) * sb, flip=(s < 0), src='arm_' + SIDE[s])
        # forearm: tight sleeve end under the bracer, hugging the wrist
        arm_tube(p, s, [0.66, 0.70, 0.74], [0.008, 0.007, 0.005], 'M_cloth', gamb)
        # bracer with two straps
        fa = 'forearm_' + SIDE[s]
        arm_tube(p, s, [0.515, 0.535, 0.60, 0.665, 0.69], [0.014, 0.020, 0.018, 0.015, 0.012], 'M_leather', dark,
                 w=('rigid', fa, 0.75))
        for x in (0.56, 0.645):
            P, rad, ax = arm_ring(K, x, 10, 0.019 - 0.02 * (x - 0.56) * 1.8, s)
            band(p, P, rad, ax, 0.014, 0.004, 'M_leather', col('#2a1c13'), flip=(s < 0), src='arm_' + SIDE[s],
                 w=('rigid', fa, 0.75), bevel=False)
        # shoulder cap: two overlapping leather lames
        Bp = np.radians(np.linspace(-118, 118, 8))
        cl, ua = 'clavicle_' + SIDE[s], 'upper_arm_' + SIDE[s]
        wP = (lambda P, Wa, cl=cl, ua=ua: w_bones(P, {cl: 1.0}) * (1 - 0.6 * sstep(0.17, 0.29, np.abs(P[:, 0])))[:, None]
              + w_bones(P, {ua: 1.0}) * (0.6 * sstep(0.17, 0.29, np.abs(P[:, 0])))[:, None])
        arm_tube(p, s, [0.150, 0.195, 0.238, 0.240, 0.285, 0.305], [0.016, 0.030, 0.030, 0.025, 0.025, 0.021], 'M_leather',
                 dark, B=Bp, closed=False, split=(2,), w=wP)
    # boiled leather jerkin (sleeveless), short split skirt
    As = SLIT_A
    off = [0.030, 0.026, 0.021, 0.023, 0.024, 0.024, 0.024, 0.023, 0.022, 0.021]
    zs = [0.955, 1.00, 1.04, 1.08, 1.13, 1.19, 1.25, 1.31, 1.36, 1.40]
    T = K.torso_rows(zs, As, off, 0.9)
    S = K.drape(As, zs[0], [0.875, 0.915], 0.0, min_off=0.028, flare=0.012, r_top=ring_r(T[0]))
    Yk = K.yoke(As, (0.3, 0.6, 0.80, 0.87), (0.021, 0.021, 0.020, 0.022))
    G = np.concatenate([S, T, Yk], 0)
    wJ = skirt_weights(z_free=0.99, z_full=0.84, xw=0.03)
    slit = lambda i, j: i < 2 and j in (23, 11, 5, 17)
    p.grid(G[0:15], 'M_leather', lea, src='body', w=wJ, skip=slit)
    p.grid(G[14:16], 'M_leather', dark, src='trunk', w=w_trunk)              # rolled neck edge
    p.lining(G[0:2], 'M_leather', col('#2a1c13'), src='body', w=wJ, skip=slit)
    # front closure: darker placket and three straps
    zc = np.array([1.00, 1.06, 1.13, 1.20, 1.27, 1.34, 1.385])
    aa = np.array([-0.16, 0.16])
    Gp = K.torso.pts(zc[:, None], aa[None, :], off=np.interp(zc, zs, off)[:, None] + 0.0035, hull=0.9)
    p.grid(Gp, 'M_leather', dark, closed=False, src='trunk', w=w_trunk)
    for z in (1.15, 1.235, 1.32):
        c = K.torso.pts(z, 0.0, off=float(np.interp(z, zs, off)) + 0.006, hull=0.9)
        p.box(c, (0.040, 0, 0), (0, 0.0025, 0), (0, 0, 0.009), 'M_leather', col('#241810'), src='trunk', w=w_trunk)
        p.box(c + np.array([0.026, -0.003, 0]), (0.008, 0, 0), (0, 0.002, 0), (0, 0, 0.011), 'M_metal_iron', col('#8a857b'),
              src='trunk', w=w_trunk)
    belt(p, 1.045, 0.024, 'M_leather', col('#2e2118'), h=0.042, buckle=('M_metal_iron', '#8a857b'), tail=4, hull=0.9)
    pouch(p, 1.005, 1.2, 0.026, 'M_leather', col('#4a3423'))
    return p


def leather_legs(K):
    p = Piece('leather_legs', K)
    c = cfn('#4a3a2d', 0.13, 0.05, 10)
    trousers(p, 'M_leather', c, off=0.008, z_bot=0.36)
    bc = cfn('#33261c', 0.12, 0.04, 11, dirt=(0.0, 0.14, 0.35))
    cuff = cfn('#3f2f23', 0.12, 0.04, 12)
    boots(p, 'M_leather', bc, top=0.425, off=0.008, sole=col('#1d1612'), top_off=0.012)
    for s in (1, -1):
        src = 'leg_' + SIDE[s]
        # folded boot cuff
        Gc = leg_tube(p, s, [0.36, 0.375, 0.43, 0.445], [0.016, 0.021, 0.022, 0.015], 'M_leather', cuff, split=(1, 2))
        # knee patch (reinforced)
        az = np.radians(np.linspace(-70, 70, 6))
        leg_tube(p, s, [0.46, 0.50, 0.545, 0.58], [0.011, 0.014, 0.013, 0.011], 'M_leather', cfn('#5b4735', 0.12, 0.04, 13),
                 A=az, closed=False)
        for z in (0.125, 0.30):                                         # straps
            P, rad = leg_ring(K, z, 12, 0.0115, s)
            band(p, P, rad, UP, 0.016, 0.004, 'M_leather', col('#221812'), flip=(s < 0), src=src, bevel=False)
    return p


def leather_head(K):
    p = Piece('leather_head', K)
    o = 0.008
    spec = [('e', 90, o, 0), ('e', 64, o, 30), ('e', 44, o, 40), ('e', 31, o + 0.001, 47), ('z', 1.712, o, 54),
            ('z', 1.685, o, 58), ('z', 1.655, o, 62), ('z', 1.625, o, 68), ('z', 1.597, o + 0.003, 78),
            ('z', 1.574, o + 0.010, 92)]
    c = cfn('#5a4029', 0.14, 0.05, 12)
    G, AZ = hood(p, 'M_leather', c, spec, ns=20, jf=3, face=(3, 9), w={'head': 1.0})
    face_rim(p, G, 20, 3, 3, 9, 'M_leather', col('#3a2819'), r=0.005, w={'head': 1.0}, bottom=False)
    # raised seam from the brow over the crown to the nape
    es = np.array([33, 50, 70, 90, 110, 130, 150, 172])
    path = []
    for e in es:
        az, el = (0.0, e) if e <= 90 else (math.pi, 180 - e)
        path.append(K.dome.pts(math.radians(el), az, off=o + 0.0015))
    path.append(G[8, 10] + np.array([0, 0.002, 0]))
    T = tube_path(np.array(path), 0.0045, 4, up_hint=(1, 0, 0))
    p.grid(T, 'M_leather', col('#3a2819'), w={'head': 1.0}, src='head')
    # chin strap hanging from the left flap, buckle end on the right
    for s in (1, -1):
        a = G[8, 3 if s > 0 else 17]
        path = np.array([a + (0, 0, 0.006), a + (0.002 * s, -0.006, -0.022), a + (0.003 * s, -0.012, -0.05 if s > 0 else -0.03)])
        Tt = tube_path(path, [0.006, 0.0055, 0.005], 4, squash=0.45)
        p.grid(Tt, 'M_leather', col('#3a2819'), cap1=True, w={'head': 1.0}, src='head')
    return p


PIECES = {
    'leather_head': (leather_head, ['hair'], 'leather arming cap with ear / neck flaps, centre seam and loose chin straps'),
    'leather_chest': (leather_chest, ['body_torso', 'body_arms'], 'boiled leather jerkin with strapped front over a quilted gambeson, leather shoulder caps, strapped bracers, belt and pouch; bare hands'),
    'leather_legs': (leather_legs, ['body_legs', 'body_feet'], 'leather trousers with knee patches, tall boots with folded cuffs'),
}
