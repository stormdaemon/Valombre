"""BANDIT set: ragged hood with a face scarf, fur trimmed hide vest over a dirty shirt with one pauldron and
wrist wraps, mismatched hose and fur wrapped boots."""
from outfit_parts import *


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
    arm_tube(p, 1, [0.135, 0.19, 0.25, 0.305], [0.022, 0.034, 0.032, 0.028], 'M_leather', cfn('#2f2620', 0.2, 0.03, 16), B=B,
             closed=False, w=lambda P, Wa: 0.5 * w_bones(P, {'clavicle_L': 1.0}) + 0.5 * Wa)
    for s in (1, -1):
        arm_tube(p, s, [0.62, 0.655, 0.69, 0.72], [0.012, 0.013, 0.012, 0.010], 'M_cloth', cfn('#8a7d68', 0.15, 0.02, 17))
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
            ('z', 1.595, o + 0.004, 60), ('z', 1.565, o + 0.012, 30), ('n', 0.050, 0.024, 0), ('n', 0.026, 0.030, 0),
            ('n', 0.004, 0.036, 0)]
    c = cfn('#3d4336', 0.16, 0.05, 22)
    G, AZ = hood(p, 'M_cloth', c, spec, ns=20, jf=3, face=(3, 9), src='upper')
    # face scarf over the nose and mouth
    az = np.radians(np.linspace(-66, 66, 11))
    zs = np.array([1.668, 1.645, 1.62, 1.595, 1.572])
    S = K.head.pts(zs[:, None], az[None, :], off=np.array([0.006, 0.007, 0.008, 0.009, 0.012])[:, None], hull=0.6)
    p.grid(S, 'M_cloth', cfn('#5c2f27', 0.15, 0.03, 23), closed=False, flip=True, src='head', w={'head': 1.0})
    return p


PIECES = {
    'bandit_head': (bandit_head, ['hair', 'beard'], 'ragged hood with a face scarf over nose and mouth'),
    'bandit_chest': (bandit_chest, ['body_torso', 'body_arms'], 'fur trimmed hide vest over a dirty shirt, one boiled leather pauldron (left), wrist wraps, belt; bare hands'),
    'bandit_legs': (bandit_legs, ['body_legs', 'body_feet'], 'mismatched patched hose, fur wrapped boots'),
}
