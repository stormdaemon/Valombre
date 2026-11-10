"""Two-handed (greatsword) combat and hit reactions / knockdown / deaths."""
from anim_poses import *

TAU = 2 * math.pi
CL, CR = COMBAT['footL'], COMBAT['footR']


# ============================================================================ two-handed
def idle_2h_fn(ph, t):
    w = TAU * ph
    b = 0.5 - 0.5 * math.cos(2 * w)
    p = P(TWOH)
    h = TWOH['hips']
    p['hips'] = (h[0] + 0.006 * math.sin(w), h[1] + 0.005 * math.sin(w + 1.0), h[2] - 0.012 * b)
    p['pelvis'] = (5.0 + 1.0 * b, -20.0 + 1.5 * math.sin(w + 0.4), 0.0)
    p['spine'] = (8.0 + 1.5 * math.sin(2 * w - 0.9), 8.0 - 1.5 * math.sin(w + 0.4), 0.0)
    hr = TWOH['handR']
    p['handR'] = (hr[0] + 0.006 * math.sin(w - 0.8), hr[1], hr[2] + 0.012 * math.sin(2 * w - 2.0))
    p['bladeR'] = (0.22 + 0.03 * math.sin(w - 1.2), -0.52 + 0.03 * math.sin(2 * w - 2.6), 0.82)
    return p


def atk2h_1():
    """Wide horizontal sweep from right to left. Like a two-handed bat swing: in chest space the blade stays
    out to the right with the hands in front of the body, and the rotation of the whole torso sweeps it."""
    k = [
        (0.00, P(TWOH)),
        (0.22, P(TWOH, hips=(-0.03, 0.06, 0.855), pelvis=(4, -44, 0), spine=(6, -28, -3),
                 handR=(-0.24, -0.26, 1.32), bladeR=bd(-125, 25), footR=tw(CR, yaw=-58))),
        (0.34, P(TWOH, hips=(-0.01, 0.0, 0.85), pelvis=(5, -20, 0), spine=(8, -6, 0),
                 handR=(-0.20, -0.38, 1.28), bladeR=bd(-105, 10))),
        (0.40, P(TWOH, hips=(0.01, -0.04, 0.845), pelvis=(6, 0, 0), spine=(10, 14, 2),
                 handR=(-0.12, -0.44, 1.25), bladeR=bd(-80, 2), footR=tw(CR, pitch=18, yaw=-38))),
        (0.46, P(TWOH, hips=(0.02, -0.06, 0.84), pelvis=(6, 20, 0), spine=(10, 32, 3),
                 handR=(-0.04, -0.46, 1.23), bladeR=bd(-62, -3), footR=tw(CR, pitch=30, yaw=-24))),
        (0.52, P(TWOH, hips=(0.02, -0.06, 0.84), pelvis=(6, 28, 0), spine=(10, 42, 3),
                 handR=(0.10, -0.40, 1.22), bladeR=bd(-50, -3), poleL=(0.5, 0.8, -0.3), footR=tw(CR, pitch=38, yaw=-16))),
        (0.62, P(TWOH, hips=(0.02, -0.05, 0.845), pelvis=(5, 30, 0), spine=(9, 46, 3),
                 handR=(0.16, -0.34, 1.22), bladeR=bd(-42, 4), poleL=(0.5, 0.8, -0.3), footR=tw(CR, pitch=38, yaw=-14))),
        (0.85, P(TWOH)),
    ]
    auto_edges(k, 1, 6)
    return Clip('atk2h_1', 0.85, keys=k, twoh=True, props='2h', lag={'head': 0.02}, nstrip=12, bounds=1.85,
                events={'whoosh': 0.38, 'hit': [0.40, 0.54], 'cancel': 0.66})


def atk2h_2():
    """Return sweep from left to right (chains after atk2h_1): mirror logic, blade out to the left."""
    k = [
        (0.00, P(TWOH)),
        (0.24, P(TWOH, hips=(0.02, -0.03, 0.855), pelvis=(5, -2, 0), spine=(8, 42, 3),
                 handR=(0.12, -0.30, 1.32), bladeR=bd(125, 25), footR=tw(CR, pitch=24, yaw=-30))),
        (0.37, P(TWOH, hips=(0.01, -0.03, 0.85), pelvis=(5, -14, 0), spine=(9, 16, 2),
                 handR=(0.06, -0.40, 1.28), bladeR=bd(105, 10), footR=tw(CR, pitch=10, yaw=-40))),
        (0.43, P(TWOH, hips=(0.0, -0.02, 0.845), pelvis=(6, -26, 0), spine=(10, -6, 0),
                 handR=(-0.02, -0.45, 1.25), bladeR=bd(80, 2))),
        (0.49, P(TWOH, hips=(-0.01, 0.0, 0.845), pelvis=(6, -36, 0), spine=(10, -22, -2),
                 handR=(-0.10, -0.46, 1.23), bladeR=bd(52, -3))),
        (0.55, P(TWOH, hips=(-0.02, 0.02, 0.845), pelvis=(6, -44, 0), spine=(10, -34, -3),
                 handR=(-0.06, -0.45, 1.25), bladeR=bd(58, -3), poleR=(-0.5, 0.8, -0.3), footR=tw(CR, yaw=-58))),
        (0.65, P(TWOH, hips=(-0.02, 0.02, 0.85), pelvis=(5, -46, 0), spine=(9, -38, -3),
                 handR=(-0.06, -0.45, 1.26), bladeR=bd(52, 4), poleR=(-0.5, 0.8, -0.3), footR=tw(CR, yaw=-60))),
        (0.90, P(TWOH)),
    ]
    auto_edges(k, 1, 6)
    return Clip('atk2h_2', 0.90, keys=k, twoh=True, props='2h', lag={'head': 0.02}, nstrip=12, bounds=1.85,
                events={'whoosh': 0.43, 'hit': [0.44, 0.57], 'cancel': 0.69})


def atk2h_3():
    """Overhead smash to the ground with a step in."""
    up = dict(poleR=(-0.5, 0.6, 0.6), poleL=(0.5, 0.6, 0.6))
    k = [
        (0.00, P(TWOH)),
        (0.30, P(TWOH, hips=(0.0, 0.04, 0.90), pelvis=(-2, -14, 0), spine=(-9, 4, 0),
                 handR=(-0.07, -0.20, 1.87), bladeR=(0.0, 0.72, 0.69), bspR='world',
                 footL=tw(CL, y=-0.26, z=0.06, pitch=6), **up)),
        (0.42, P(TWOH, hips=(0.0, 0.0, 0.905), pelvis=(0, -12, 0), spine=(-5, 4, 0),
                 handR=(-0.06, -0.26, 1.90), bladeR=(0.0, 0.30, 0.95), bspR='world',
                 footL=tw(CL, y=-0.38, z=0.05, pitch=-8), **up)),
        (0.50, P(TWOH, hips=(0.0, -0.07, 0.84), pelvis=(10, -10, 0), spine=(16, 6, 0),
                 handR=(-0.04, -0.47, 1.44), poleR=(-0.8, 0.1, 0.5), poleL=(0.8, 0.1, 0.5),
                 bladeR=(0.0, -0.62, 0.78), bspR='world', footL=tw(CL, y=-0.42), footR=tw(CR, pitch=18))),
        (0.56, P(TWOH, hips=(0.0, -0.10, 0.74), pelvis=(22, -8, 0), spine=(40, 4, 0),
                 handR=(-0.02, -0.44, 1.12), poleR=(-0.8, 0.4, -0.3), poleL=(0.8, 0.4, -0.3),
                 bladeR=(0.0, -0.925, -0.38), bspR='world', footL=tw(CL, y=-0.42), footR=tw(CR, pitch=34))),
        (0.68, P(TWOH, hips=(0.0, -0.10, 0.735), pelvis=(23, -8, 0), spine=(41, 4, 0),
                 handR=(-0.02, -0.43, 1.11), poleR=(-0.8, 0.4, -0.3), poleL=(0.8, 0.4, -0.3),
                 bladeR=(0.0, -0.93, -0.37), bspR='world', footL=tw(CL, y=-0.42), footR=tw(CR, pitch=34))),
        (0.88, P(TWOH, hips=(0.0, -0.05, 0.82), pelvis=(11, -16, 0), spine=(20, 7, 0),
                 handR=(-0.05, -0.40, 1.16), bladeR=(0.08, -0.90, 0.25), bspR='world',
                 footL=tw(CL, y=-0.34, z=0.04))),
        (1.10, P(TWOH)),
    ]
    auto_edges(k, 1, 4)
    k[5][1]['edgeR'] = k[4][1]['edgeR']
    k[6][1]['edgeR'] = (0.0, -0.3, -0.95)
    return Clip('atk2h_3', 1.10, keys=k, twoh=True, props='2h', lag={'head': 0.02}, nstrip=12, bounds=1.9,
                view='side_r', events={'whoosh': 0.47, 'hit': [0.48, 0.60], 'impact': 0.56, 'cancel': 0.82,
                                       'steps': [[0.49, 'L'], [0.96, 'L']]})


def _spin_feet(t, pz):
    """atk2h_heavy: the feet step around the 360 degree turn. Each foot is planted on its ball (fixed in the
    world, heel raised, pivoting with the pelvis) while the other one swings around."""
    yaw = float(pz['pelvis'][1])
    act = smooth((t - 0.40) / 0.10) * (1.0 - smooth((t - 1.0) / 0.12))
    d = (yaw + 20.0) if t < 0.9 else (yaw - 340.0)

    def foot(az, r, base_heading, z=0.0, pitch=None):
        heading = base_heading + d * act
        a, h = math.radians(az), math.radians(heading)
        bx, by = r * math.sin(a), -r * math.cos(a)
        return (bx - 0.13 * math.sin(h), by + 0.13 * math.cos(h), z, 26.0 * act if pitch is None else pitch, heading, 0.0)

    def seg(t0, t1, az0, r0, az1, r1, base_heading):
        u = clamp((t - t0) / (t1 - t0), 0.0, 1.0)
        s = smooth(u)
        return foot(lerp(az0, az1, s), lerp(r0, r1, s) - 0.05 * math.sin(math.pi * u), base_heading,
                    0.11 * bump(u, 0.45), lerp(26.0, 34.0, math.sin(math.pi * u)))

    L0, R0, R1 = (24.5, 0.395), (-122.5, 0.34), (65.0, 0.30)
    if t < 0.60:
        pz['footL'] = foot(L0[0], L0[1], 6.0)
    elif t < 0.83:
        pz['footL'] = seg(0.60, 0.83, L0[0], L0[1], L0[0] + 360.0, L0[1], 6.0)
    else:
        pz['footL'] = foot(L0[0] + 360.0, L0[1], 6.0)
    if t < 0.44:
        pz['footR'] = foot(R0[0], R0[1], -48.0)
    elif t < 0.59:
        pz['footR'] = seg(0.44, 0.59, R0[0], R0[1], R1[0], R1[1], -48.0)
    elif t < 0.80:
        pz['footR'] = foot(R1[0], R1[1], -48.0)
    elif t < 0.98:
        pz['footR'] = seg(0.80, 0.98, R1[0], R1[1], R0[0] + 360.0, R0[1], -48.0)
    else:
        pz['footR'] = foot(R0[0] + 360.0, R0[1], -48.0)
    pz['fspL'] = pz['fspR'] = 'world'


def atk2h_heavy():
    """Full 360 degree spinning cleave (turning to the left). The blade is held out to the right of the
    chest and the spin carries it: it crosses the front twice (two hit windows)."""
    hs = dict(hstab=0.0)
    k = [
        (0.00, P(TWOH)),
        (0.30, P(TWOH, hips=(-0.02, 0.04, 0.85), pelvis=(4, -50, 0), spine=(6, -26, -3),
                 handR=(-0.24, -0.26, 1.32), bladeR=bd(-125, 24))),
        (0.42, P(TWOH, hips=(-0.02, 0.04, 0.84), pelvis=(4, -54, 0), spine=(6, -30, -3),
                 handR=(-0.25, -0.25, 1.32), bladeR=bd(-128, 22))),
        (0.55, P(TWOH, hips=(0.0, 0.0, 0.875), pelvis=(5, 10, 0), spine=(8, -10, 0), head=(0, 35, 0),
                 handR=(-0.18, -0.40, 1.28), bladeR=bd(-100, 6), **hs)),
        (0.66, P(TWOH, hips=(0.0, 0.0, 0.895), pelvis=(5, 100, 0), spine=(8, 6, 0), head=(0, 32, 0),
                 handR=(-0.14, -0.44, 1.26), bladeR=bd(-90, 0), **hs)),
        (0.78, P(TWOH, hips=(0.0, 0.0, 0.90), pelvis=(5, 200, 0), spine=(8, 8, 0), head=(0, 30, 0),
                 handR=(-0.14, -0.44, 1.26), bladeR=bd(-88, 0), **hs)),
        (0.90, P(TWOH, hips=(0.0, 0.0, 0.885), pelvis=(6, 290, 0), spine=(9, 10, 0), head=(2, 30, 0),
                 handR=(-0.13, -0.45, 1.25), bladeR=bd(-85, -2), **hs)),
        (1.00, P(TWOH, hips=(0.01, -0.03, 0.855), pelvis=(7, 335, 0), spine=(11, 30, 2), head=(5, -10, 0),
                 handR=(-0.08, -0.46, 1.24), bladeR=bd(-62, -4), **hs)),
        (1.10, P(TWOH, hips=(0.02, -0.05, 0.845), pelvis=(6, 345, 0), spine=(10, 44, 3), head=(5, 0, 0), hstab=1.0,
                 handR=(0.08, -0.41, 1.22), bladeR=bd(-48, -2), poleL=(0.5, 0.8, -0.3))),
        (1.19, P(TWOH, hips=(0.02, -0.05, 0.85), pelvis=(6, 352, 0), spine=(10, 54, 3),
                 handR=(0.15, -0.35, 1.22), bladeR=bd(-36, 5), poleL=(0.5, 0.8, -0.3))),
        (1.40, P(TWOH, pelvis=(5, 340, 0))),
    ]
    auto_edges(k, 1, 9)
    k[1][1]['edgeR'] = k[2][1]['edgeR'] = k[3][1]['edgeR']
    return Clip('atk2h_heavy', 1.40, keys=k, twoh=True, props='2h', post=_spin_feet, nstrip=16, bounds=1.85,
                grounded=False,
                events={'whoosh': 0.54, 'hit': [[0.58, 0.70], [1.04, 1.19]], 'cancel': 1.26,
                        'steps': [[0.59, 'R'], [0.83, 'L'], [0.98, 'R']]})


# ============================================================================ reactions
def hit_light():
    """Flinch from a blow coming from the front."""
    k = [
        (0.00, P(COMBAT)),
        (0.06, P(COMBAT, hips=(0.0, 0.075, 0.85), pelvis=(-3, -20, -2), spine=(-11, 13, 4), head=(14, -6, 5), hstab=0.3,
                 clavL=(9, 0), clavR=(9, 0), handL=(-0.02, -0.28, 1.24), handR=(-0.40, 0.0, 1.10),
                 bladeR=(-0.3, -0.45, 0.84), footL=tw(CL, pitch=-10))),
        (0.15, P(COMBAT, hips=(0.0, 0.05, 0.84), pelvis=(6, -24, 0), spine=(13, 7, -1), head=(8, 0, 0), hstab=0.8,
                 clavL=(4, 0), clavR=(4, 0), handL=(-0.04, -0.34, 1.25))),
        (0.35, P(COMBAT)),
    ]
    return Clip('hit_light', 0.35, keys=k, lag={'head': 0.035, 'handR': 0.04, 'handL': 0.02}, nstrip=8, bounds=1.3,
                view='side_r', events={'impact': 0.0, 'cancel': 0.25})


def hit_heavy():
    """Stagger backward, off balance: thrown back on the heels, stumbling step, arms out, recover."""
    k = [
        (0.00, P(COMBAT)),
        (0.08, P(COMBAT, hips=(0.0, 0.12, 0.855), pelvis=(-8, -18, -3), spine=(-20, 12, 5), head=(18, -8, 6), hstab=0.2,
                 clavL=(10, 0), clavR=(10, 0),
                 handL=(0.20, -0.36, 1.36), poleL=(0.8, 0.3, -0.4), handR=(-0.52, -0.10, 1.26), poleR=(-0.7, 0.6, -0.3),
                 bladeR=(-0.5, -0.3, 0.8), footL=tw(CL, z=0.05, pitch=-22))),
        # front foot leaves the ground and reaches back, torso still thrown back
        (0.22, P(COMBAT, hips=(0.0, 0.15, 0.87), pelvis=(-10, -14, -2), spine=(-16, 8, 3), head=(4, -4, 2), hstab=0.3,
                 handL=(0.34, -0.26, 1.34), poleL=(0.8, 0.4, -0.3), handR=(-0.56, -0.04, 1.30), poleR=(-0.7, 0.6, -0.2),
                 bladeR=(-0.6, -0.2, 0.77), footL=tw(CL, y=-0.06, z=0.10, pitch=10), footR=tw(CR, pitch=-8))),
        # it lands close under the body, the body over-corrects forward, rear foot shuffles
        (0.36, P(COMBAT, hips=(0.0, 0.07, 0.80), pelvis=(8, -22, 0), spine=(16, 6, -2), head=(10, 0, 0), hstab=0.7,
                 handL=(0.20, -0.34, 1.12), handR=(-0.46, -0.16, 1.02), bladeR=(-0.3, -0.75, 0.55),
                 footL=tw(CL, y=-0.05), footR=tw(CR, y=0.33, z=0.05, pitch=14))),
        (0.50, P(COMBAT, hips=(0.0, 0.04, 0.82), pelvis=(8, -24, 0), spine=(15, 8, 0), head=(8, 0, 0),
                 handL=(0.02, -0.36, 1.20), handR=(-0.38, -0.08, 1.04),
                 footL=tw(CL, y=-0.12, z=0.05, pitch=6), footR=tw(CR, y=0.29))),
        (0.70, P(COMBAT)),
    ]
    return Clip('hit_heavy', 0.70, keys=k, lag={'head': 0.04, 'handR': 0.05, 'handL': 0.04}, nstrip=8, bounds=1.3,
                view='side_r', grounded=False,
                events={'impact': 0.0, 'cancel': 0.52, 'steps': [[0.34, 'L'], [0.41, 'R'], [0.58, 'L']]})


LIE_BACK = P(
    hips=(0.0, 0.10, 0.115), pelvis=(-90, 0, 0), spine=(-4, 0, 0), head=(-6, 14, 0), hstab=0.0,
    footL=(0.17, 0.08, -0.045, 28, 22, 0), footR=(-0.19, 0.08, -0.045, 24, -30, 0), fspL='hips', fspR='hips',
    handR=(-0.52, 0.03, 1.20), hspR='chest', poleR=(-0.7, -0.35, 0.6), bladeR=(-0.97, 0.0, -0.24),
    edgeR=(0.1, 0.0, -1.0), curlR=1.0,
    handL=(0.50, 0.03, 1.28), hspL='chest', poleL=(0.7, -0.35, 0.6), twistL=40.0, curlL=0.4, wristL=(0.0, 0.0))


def knockdown():
    """Thrown onto the back; ends lying (getup starts from this pose)."""
    k = [
        (0.00, P(COMBAT)),
        (0.08, P(COMBAT, hips=(0.0, 0.08, 0.86), pelvis=(-14, -14, 0), spine=(-16, 8, 0), head=(22, 0, 0), hstab=0.0,
                 handR=(-0.50, -0.20, 1.36), poleR=(-0.7, 0.5, -0.4), bladeR=(-0.4, -0.3, 0.86),
                 handL=(0.30, -0.40, 1.40), poleL=(0.7, 0.4, -0.5), footL=tw(CL, z=0.04, pitch=-20), footR=tw(CR, pitch=-10))),
        # off the ground, body going horizontal, legs kick up
        (0.24, P(COMBAT, hips=(0.0, 0.10, 0.64), pelvis=(-52, -6, 0), spine=(-8, 4, 0), head=(18, 0, 0), hstab=0.0,
                 footL=(0.13, -0.26, 0.14, 20, 10, 0), footR=(-0.14, -0.18, 0.22, 25, -10, 0), fspL='hips', fspR='hips',
                 handR=(-0.58, -0.12, 1.50), poleR=(-0.6, 0.6, -0.4), bladeR=(-0.5, -0.2, 0.84),
                 handL=(0.50, -0.25, 1.52), poleL=(0.6, 0.6, -0.4))),
        # the back hits, chin tucked, legs still in the air
        (0.40, P(LIE_BACK, hips=(0.0, 0.10, 0.15), pelvis=(-94, 0, 0), spine=(14, 0, 0), head=(24, 0, 0),
                 footL=(0.14, -0.40, 0.30, 10, 12, 0), footR=(-0.15, -0.34, 0.38, 14, -12, 0),
                 handR=(-0.56, 0.02, 1.38), bladeR=(-0.6, -0.1, -0.79), handL=(0.54, 0.0, 1.40))),
        (0.52, P(LIE_BACK, hips=(0.0, 0.10, 0.18), pelvis=(-88, 0, 0), spine=(6, 0, 0), head=(10, 6, 0),
                 footL=(0.16, -0.16, 0.10, 20, 18, 0), footR=(-0.17, -0.20, 0.16, 20, -20, 0),
                 handR=(-0.54, 0.04, 1.28), handL=(0.52, 0.01, 1.34))),
        (0.68, P(LIE_BACK, hips=(0.0, 0.10, 0.118), footR=(-0.19, 0.02, 0.0, 24, -28, 0))),
        (0.84, P(LIE_BACK)),
        (1.10, P(LIE_BACK)),
    ]
    return Clip('knockdown', 1.10, keys=k, lag={'handR': 0.03, 'handL': 0.03}, nstrip=12, bounds=1.5, view='side_r',
                grounded=False, events={'impact': 0.40, 'iframes': [0.10, 1.10]})


def getup():
    """From lying on the back: roll onto the right side, prop on the sword hand, get a knee under, stand."""
    k = [
        (0.00, P(LIE_BACK)),
        (0.24, P(LIE_BACK, hips=(-0.02, 0.08, 0.14), pelvis=(-78, 0, 0, -50), spine=(22, -6, 0), head=(16, -10, 0),
                 handR=(-0.42, 0.10, 0.06), hspR='world', poleR=(-0.9, 0.3, 0.2), bladeR=(-0.35, -0.93, 0.08), bspR='world',
                 edgeR=(0.0, 0.0, -1.0),
                 handL=(0.10, -0.35, 1.26), hspL='chest', poleL=(0.8, 0.3, -0.5), twistL=0.0,
                 footL=(0.12, -0.44, 0.0, 0, -4, 0), fspL='world',
                 footR=(-0.22, -0.34, 0.04, 30, -40, 0), fspR='world')),
        (0.46, P(LIE_BACK, hips=(-0.03, 0.05, 0.29), pelvis=(-38, -10, -8, -24), spine=(30, 8, 0), head=(4, 6, 0),
                 handR=(-0.36, 0.14, 0.06), hspR='world', poleR=(-0.9, 0.4, 0.2), bladeR=(-0.35, -0.93, 0.08), bspR='world',
                 edgeR=(0.0, 0.0, -1.0),
                 handL=(0.04, -0.36, 1.24), hspL='chest', poleL=(0.8, 0.3, -0.5), twistL=0.0,
                 footL=(0.14, -0.30, 0.0, 0, 6, 0), fspL='world',
                 footR=(-0.17, 0.40, 0.0, 62, -10, 0), fspR='world')),
        (0.58, P(LIE_BACK, hips=(-0.01, 0.03, 0.455), pelvis=(-8, -14, -3, -8), spine=(27, 7, 0), head=(5, 3, 0),
                 handR=(-0.37, -0.02, 0.99), hspR='chest', poleR=(-0.6, 0.7, -0.3), bladeR=(-0.3, -0.9, 0.3), bspR='world',
                 edgeR=(0.0, -0.3, -1.0),
                 handL=(0.0, -0.36, 1.24), hspL='chest', poleL=(0.8, 0.3, -0.5), twistL=0.0,
                 footL=(0.15, -0.29, 0.0, 0, 6, 0), fspL='world',
                 footR=(-0.17, 0.40, 0.0, 62, -10, 0), fspR='world')),
        (0.70, P(COMBAT, hips=(0.0, 0.02, 0.50), pelvis=(8, -16, 0, 0), spine=(22, 6, 0), head=(6, 0, 0), hstab=0.8,
                 handL=(-0.02, -0.36, 1.24),
                 footL=(0.15, -0.28, 0.0, 0, 6, 0), footR=(-0.17, 0.40, 0.0, 62, -10, 0))),
        (0.96, P(COMBAT, hips=(0.0, 0.02, 0.76), pelvis=(9, -22, 0), spine=(15, 8, 0),
                 footL=tw(CL, y=-0.25), footR=(-0.19, 0.31, 0.0, 26, -40, 0))),
        (1.20, P(COMBAT)),
    ]
    return Clip('getup', 1.20, keys=k, lag={'head': 0.03, 'handL': 0.03}, nstrip=12, bounds=1.5, view='persp',
                grounded=False, events={'iframes': [0.0, 0.70], 'cancel': 1.0})


DEAD_FRONT = P(
    hips=(0.0, -0.14, 0.135), pelvis=(87, 0, 0, 0), spine=(2, 0, 0), head=(-12, 50, 0), hstab=0.0,
    footL=(0.14, 0.13, -0.057, 62, 14, 0), footR=(-0.17, 0.13, -0.057, 62, -22, 0), fspL='hips', fspR='hips',
    handR=(-0.44, -0.045, 1.56), hspR='chest', poleR=(-0.9, -0.2, -0.3), bladeR=(-0.98, 0.0, 0.2),
    edgeR=(0.0, 0.0, 1.0), curlR=0.9,
    handL=(0.40, -0.035, 1.30), hspL='chest', poleL=(0.8, 0.35, 0.4), twistL=0.0, curlL=0.3, wristL=(0.0, 0.0))


def death():
    """Drop to the knees, sway, then collapse face down. The last pose is held."""
    kn = dict(kneeL=(0.10, -1.0, -0.35), kneeR=(-0.10, -1.0, -0.35))
    k = [
        (0.00, P(COMBAT, **kn)),
        (0.10, P(COMBAT, hips=(0.0, 0.06, 0.85), pelvis=(-2, -20, 0), spine=(-12, 10, 2), head=(-14, 0, 0), hstab=0.0,
                 handR=(-0.40, -0.04, 1.00), bladeR=(-0.25, -0.8, 0.35), handL=(0.06, -0.30, 1.16), **kn)),
        # knees hit the ground
        (0.45, P(COMBAT, hips=(0.0, 0.02, 0.50), pelvis=(2, -10, 0), spine=(8, 4, 0), head=(20, 0, 0), hstab=0.0,
                 footL=(0.14, 0.42, 0.0, 62, 4, 0), footR=(-0.17, 0.46, 0.0, 62, -12, 0),
                 handR=(-0.31, -0.04, 0.93), poleR=(-0.4, 0.9, -0.1), bladeR=(-0.2, -0.92, -0.33), edgeR=(0, -0.4, -0.9),
                 handL=(0.30, -0.08, 0.97), poleL=(0.4, 0.9, -0.1), curlL=0.4, **kn)),
        # sway on the knees, head drops
        (0.72, P(COMBAT, hips=(0.01, 0.04, 0.49), pelvis=(-2, -8, 2), spine=(4, 2, 2), head=(32, 4, 0), hstab=0.0,
                 footL=(0.14, 0.42, 0.0, 62, 4, 0), footR=(-0.17, 0.46, 0.0, 62, -12, 0),
                 handR=(-0.30, -0.02, 0.92), poleR=(-0.4, 0.9, -0.1), bladeR=(-0.25, -0.90, -0.35), edgeR=(0, -0.4, -0.9),
                 handL=(0.30, -0.06, 0.96), poleL=(0.4, 0.9, -0.1), curlL=0.3, **kn)),
        # toppling forward
        (1.04, P(COMBAT, hips=(0.0, -0.04, 0.47), pelvis=(42, -4, 0, 0), spine=(14, 0, 0), head=(14, 20, 0), hstab=0.0,
                 footL=(0.14, 0.63, 0.022, 120, 8, 0), footR=(-0.17, 0.67, 0.022, 120, -16, 0),
                 handR=(-0.36, -0.10, 1.10), poleR=(-0.8, 0.3, -0.4), bladeR=(-0.3, -0.2, 0.93), edgeR=(-0.9, 0, -0.3),
                 handL=(0.34, -0.10, 1.10), poleL=(0.8, 0.3, 0.2), curlL=0.3, **kn)),
        (1.16, P(COMBAT, hips=(0.0, -0.10, 0.30), pelvis=(66, -2, 0, 0), spine=(10, 0, 0), head=(4, 30, 0), hstab=0.0,
                 footL=(0.14, 0.91, 0.123, 165, 10, 0), footR=(-0.17, 0.94, 0.123, 165, -18, 0),
                 handR=(-0.42, -0.10, 1.34), poleR=(-0.9, 0.0, -0.4), bladeR=(-0.8, -0.1, 0.59), edgeR=(-0.5, 0, 0.86),
                 handL=(0.38, -0.10, 1.20), poleL=(0.8, 0.3, 0.3), curlL=0.3, **kn)),
        (1.26, P(DEAD_FRONT, hips=(0.0, -0.14, 0.145), spine=(6, 0, 0), head=(-4, 40, 0), **kn)),
        (1.36, P(DEAD_FRONT, hips=(0.0, -0.14, 0.15), spine=(0, 0, 0), head=(-14, 48, 0), **kn)),
        (1.50, P(DEAD_FRONT, **kn)),
        (1.80, P(DEAD_FRONT, **kn)),
    ]
    return Clip('death', 1.80, keys=k, lag={'handR': 0.04, 'handL': 0.04}, nstrip=12, bounds=1.5, view='side_r',
                grounded=False, events={'impact': 1.26, 'steps': [[0.45, 'L'], [0.46, 'R']]})


DEAD_BACK = P(
    LIE_BACK, pelvis=(-90, 0, 0, 0), spine=(-3, -4, 0), head=(-6, -32, 0),
    footL=(0.18, 0.08, -0.045, 30, 26, 0), footR=(-0.34, 0.03, 0.26, 20, -55, 0),
    handR=(-0.46, 0.0, 1.74), poleR=(-0.9, -0.3, 0.1), bladeR=(-0.95, -0.02, 0.3), edgeR=(0.0, 0.0, 1.0), curlR=0.8,
    handL=(0.16, -0.13, 1.12), poleL=(0.9, -0.1, -0.2), twistL=0.0, curlL=0.3)


def death_back():
    """Fall backward and stay down."""
    k = [
        (0.00, P(COMBAT)),
        (0.12, P(COMBAT, hips=(0.0, 0.08, 0.86), pelvis=(-9, -18, 0), spine=(-20, 8, 2), head=(-16, 0, 0), hstab=0.0,
                 handR=(-0.52, -0.14, 1.40), poleR=(-0.7, 0.5, -0.3), bladeR=(-0.4, -0.2, 0.89),
                 handL=(0.36, -0.30, 1.44), poleL=(0.7, 0.4, -0.4), curlL=0.4, footL=tw(CL, pitch=-16))),
        # knees give way, falling back
        (0.42, P(COMBAT, hips=(0.0, 0.14, 0.70), pelvis=(-34, -10, 0), spine=(-14, 4, 0), head=(-4, 0, 0), hstab=0.0,
                 handR=(-0.56, -0.02, 1.46), poleR=(-0.6, 0.6, -0.3), bladeR=(-0.5, 0.1, 0.86),
                 handL=(0.50, -0.14, 1.48), poleL=(0.6, 0.6, -0.3), curlL=0.4,
                 footL=tw(CL, pitch=-24), footR=tw(CR, pitch=-10))),
        (0.70, P(LIE_BACK, hips=(0.0, 0.12, 0.36), pelvis=(-72, -4, 0), spine=(4, 0, 0), head=(18, 0, 0),
                 footL=(0.14, -0.30, 0.10, 10, 12, 0), footR=(-0.16, -0.26, 0.16, 14, -14, 0),
                 handR=(-0.56, -0.04, 1.50), bladeR=(-0.6, -0.3, 0.74), edgeR=(-0.87, 0.0, -0.5),
                 handL=(0.52, -0.06, 1.46), twistL=20.0)),
        (0.88, P(DEAD_BACK, hips=(0.0, 0.10, 0.15), pelvis=(-93, 0, 0, 0), spine=(10, 0, 0), head=(20, -10, 0),
                 footL=(0.16, -0.24, 0.16, 16, 18, 0), footR=(-0.24, -0.26, 0.30, 16, -30, 0),
                 handR=(-0.54, -0.03, 1.62), bladeR=(-0.9, -0.2, 0.39), handL=(0.40, -0.06, 1.30))),
        (1.02, P(DEAD_BACK, hips=(0.0, 0.10, 0.17), spine=(3, -2, 0), head=(6, -24, 0),
                 footL=(0.18, -0.02, 0.05, 26, 24, 0))),
        (1.20, P(DEAD_BACK)),
        (1.60, P(DEAD_BACK)),
    ]
    return Clip('death_back', 1.60, keys=k, lag={'handR': 0.04, 'handL': 0.04}, nstrip=12, bounds=1.5, view='side_r',
                grounded=False, events={'impact': 0.88})


def clips():
    return [Clip('idle_2h', 2.4, loop=True, fn=idle_2h_fn, twoh=True, props='2h', nstrip=4, bounds=1.5),
            atk2h_1(), atk2h_2(), atk2h_3(), atk2h_heavy(),
            hit_light(), hit_heavy(), knockdown(), getup(), death(), death_back()]
