"""ROBE set: deep cowl, long monk robe with wide sleeves and a rope belt, under trousers and soft boots."""
from outfit_parts import *


def robe_chest(K):
    p = Piece('robe_chest', K)
    c = cfn('#4b3d30', 0.12, 0.08, 31, dirt=(0.26, 0.55, 0.35))
    off = [0.022, 0.014, 0.024, 0.026, 0.024, 0.021, 0.018, 0.016, 0.015]
    A = angles(28)
    torso_shell(p, 'M_cloth', c, off=off, hull=0.9, A=A,
                skirt=dict(zs=[0.28, 0.40, 0.52, 0.64, 0.76, 0.87, 0.95], flare=0.075, power=1.1, min_off=0.02,
                           folds=(7, 0.022, 0.5), weights=dict(z_full=0.70, follow=0.9, shin=0.35)))

    def so(x, B):          # wide sleeves, hanging lower under the wrist
        return 0.014 + 0.05 * sstep(0.30, 0.70, x) * (1.0 + 0.9 * np.maximum(0, -np.cos(B)))
    Gs = sleeves(p, 'M_cloth', c, off=so, x_end=0.70)
    for s in (1, -1):
        p.lining(Gs[s][-3:], 'M_cloth', col('#2a221b'), flip=(s < 0), src='arm_' + SIDE[s])
        arm_tube(p, s, [0.56, 0.66, 0.74], [0.006, 0.006, 0.004], 'M_cloth', col('#6e6250'), nb=8)   # under sleeve
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
            ('z', 1.575, fwd(0.034), 52), ('n', 0.050, 0.030, 0), ('n', 0.026, 0.034, 0), ('n', 0.004, 0.038, 0)]
    c = cfn('#4b3d30', 0.12, 0.08, 34)
    G, AZ = hood(p, 'M_cloth', c, spec, ns=20, jf=3, face=(2, 9), src='upper', hull=1.0)
    p.lining(G[1:10], 'M_cloth', col('#1c1611'), flip=True, closed=True, weld=True,
             skip=face_skip(20, 3, 1, 8), src='upper')
    return p


PIECES = {
    'robe_head': (robe_head, ['hair'], 'deep cowl with a short collar, dark lining'),
    'robe_chest': (robe_chest, ['body_torso', 'body_arms'], 'monk robe to mid shin with wide sleeves (tight under sleeves at the wrists) and a rope belt; bare hands'),
    'robe_legs': (robe_legs, ['body_legs', 'body_feet'], 'under trousers and soft ankle boots'),
}
