"""PEASANT set: linen coif, belted wool tunic with rolled sleeves, patched trousers with leg wraps and turn shoes."""
from outfit_parts import *


def peasant_chest(K):
    p = Piece('peasant_chest', K)
    wool = cfn('#8a7350', 0.12, 0.06, 1, dirt=(0.76, 0.95, 0.30))
    off = [0.016, 0.011, 0.020, 0.021, 0.019, 0.017, 0.015, 0.014, 0.013]
    hem = 0.012 * (vnoise(np.stack([A24 * 3, A24 * 0, A24 * 0], 1), 1.0, 3) - 0.5)
    G = torso_shell(p, 'M_cloth', wool, off=off, hull=0.8,
                    skirt=dict(zs=[0.775, 0.83, 0.89, 0.95], flare=0.035, folds=(6, 0.010, 0.4), hem_jitter=hem))
    p.lining(G[0:2], 'M_cloth', col('#4a3d2a'), src='body', w=skirt_weights())
    # short sleeves ending in a thick roll above the elbow (the forearms stay bare: body_arms is NOT hidden)
    sleeves(p, 'M_cloth', wool, off=lambda x, B: 0.012 + 0.006 * sstep(0.2, 0.4, x), x_end=0.415, end_off=0.016)
    for s in (1, -1):
        P, rad, ax = arm_ring(K, 0.425, 10, 0.012, s)
        roll(p, P, rad, ax, 0.013, 'M_cloth', col('#93805c'), flip=(s < 0), src='arm_' + SIDE[s])
    belt(p, 1.045, 0.013, 'M_leather', col('#4a3526'), buckle=('M_metal_iron', '#5a5650'), tail=4)
    return p


def peasant_legs(K):
    p = Piece('peasant_legs', K)
    c = cfn('#5f5546', 0.12, 0.06, 2, dirt=(0.25, 0.6, 0.25))
    trousers(p, 'M_cloth', c, off=0.009, z_bot=0.27, leg_off=lambda z: 0.010 + 0.006 * sstep(0.30, 0.42, z))
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


PIECES = {
    'peasant_head': (peasant_head, ['hair'], 'linen coif with loose ties; covers the scalp and ears'),
    'peasant_chest': (peasant_chest, ['body_torso'], 'belted wool tunic, sleeves rolled above the elbow: body_arms and body_hands stay visible'),
    'peasant_legs': (peasant_legs, ['body_legs', 'body_feet'], 'patched trousers, leg wraps, turn shoes'),
}
