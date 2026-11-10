"""One-handed + shield combat, two-handed combat and hit reactions.
Attacks start from and return to their stance (COMBAT / TWOH). Blade directions of the slashes are given
in CHEST space (bd(azimuth, elevation)): the torso rotation carries the arc, the arm adds to it."""
from anim_poses import *

TAU = 2 * math.pi
CL, CR = COMBAT['footL'], COMBAT['footR']


# ============================================================================ one-handed attacks
def atk1h_1():
    """Horizontal slash from right to left (forehand, palm up), driven by the torso.
    The forearm stays ~55 deg ahead of the blade (toward the cut) so the wrist never breaks."""
    k = [
        (0.00, P(COMBAT)),
        # anticipation: coil to the right, weight on the rear leg, sword drawn back behind the shoulder
        (0.13, P(COMBAT, hips=(-0.02, 0.05, 0.855), pelvis=(4, -34, 0), spine=(6, -16, -3),
                 handL=(0.08, -0.37, 1.25), footR=tw(CR, yaw=-55),
                 **arm_fore('R', (-0.35, 0.18, 1.30), bd(-90, 12), bd(-148, 26)))),
        (0.21, P(COMBAT, hips=(0.0, 0.0, 0.85), pelvis=(5, -14, 0), spine=(8, -2, 0),
                 handL=(0.14, -0.34, 1.22),
                 **arm_fore('R', (-0.40, 0.02, 1.30), bd(-55, 6), bd(-112, 12)))),
        (0.26, P(COMBAT, hips=(0.01, -0.04, 0.845), pelvis=(6, 2, 0), spine=(10, 14, 2),
                 handL=(0.22, -0.28, 1.18), footR=tw(CR, pitch=18, yaw=-38),
                 **arm_fore('R', (-0.36, -0.10, 1.28), bd(-10, 5), bd(-66, 4)))),
        (0.31, P(COMBAT, hips=(0.02, -0.06, 0.84), pelvis=(6, 12, 0), spine=(10, 28, 3),
                 handL=(0.28, -0.20, 1.14), footR=tw(CR, pitch=28, yaw=-30),
                 **arm_fore('R', (-0.30, -0.16, 1.26), bd(40, 3), bd(-16, 0)))),
        # follow-through: arm wraps across the chest
        (0.39, P(COMBAT, hips=(0.02, -0.05, 0.845), pelvis=(5, 16, 0), spine=(9, 34, 3),
                 handL=(0.30, -0.16, 1.12), footR=tw(CR, pitch=30, yaw=-28),
                 **arm_fore('R', (-0.22, -0.20, 1.22), bd(86, 0), bd(32, -8)))),
        (0.60, P(COMBAT)),
    ]
    auto_edges(k, 1, 5)
    return Clip('atk1h_1', 0.60, keys=k, lag={'head': 0.02, 'handL': 0.03}, nstrip=12, bounds=1.55,
                events={'whoosh': 0.22, 'hit': [0.24, 0.34], 'cancel': 0.42})


def atk1h_2():
    """Backhand slash from left to right (palm down; chains after atk1h_1)."""
    k = [
        (0.00, P(COMBAT)),
        # coil to the left: forearm folded across the chest, blade over the left shoulder
        (0.13, P(COMBAT, hips=(0.02, -0.03, 0.855), pelvis=(5, -6, 0), spine=(9, 30, 3),
                 handL=(0.26, -0.22, 1.12), footR=tw(CR, pitch=16, yaw=-36),
                 **arm_fore('R', (-0.16, -0.24, 1.24), bd(95, 20), bd(150, 30)))),
        (0.21, P(COMBAT, hips=(0.01, -0.03, 0.85), pelvis=(5, -12, 0), spine=(9, 14, 2),
                 handL=(0.24, -0.24, 1.14), footR=tw(CR, pitch=10, yaw=-40),
                 **arm_fore('R', (-0.22, -0.26, 1.26), bd(60, 10), bd(115, 14)))),
        (0.26, P(COMBAT, hips=(0.0, -0.02, 0.845), pelvis=(6, -22, 0), spine=(10, -4, 0),
                 handL=(0.20, -0.28, 1.16),
                 **arm_fore('R', (-0.30, -0.22, 1.28), bd(10, 4), bd(65, 4)))),
        (0.31, P(COMBAT, hips=(-0.01, 0.0, 0.845), pelvis=(6, -30, 0), spine=(10, -18, -2),
                 handL=(0.14, -0.32, 1.20),
                 **arm_fore('R', (-0.38, -0.12, 1.30), bd(-40, 2), bd(15, 0)))),
        (0.39, P(COMBAT, hips=(-0.02, 0.02, 0.85), pelvis=(5, -34, 0), spine=(9, -26, -3),
                 handL=(0.08, -0.36, 1.24),
                 **arm_fore('R', (-0.455, -0.03, 1.385), bd(-76, -4), bd(-24, -6)))),
        (0.60, P(COMBAT)),
    ]
    auto_edges(k, 1, 5)
    return Clip('atk1h_2', 0.60, keys=k, lag={'head': 0.02, 'handL': 0.03}, nstrip=12, bounds=1.55,
                events={'whoosh': 0.22, 'hit': [0.24, 0.34], 'cancel': 0.42})


def atk1h_3():
    """Overhead downward chop with a step in (combo finisher). Blade given in world space."""
    k = [
        (0.00, P(COMBAT)),
        # raise: sword up and back over the right shoulder, body rises, front foot unloads
        (0.20, P(COMBAT, hips=(0.0, 0.05, 0.895), pelvis=(0, -22, 0), spine=(-7, 4, 0),
                 handR=(-0.30, -0.02, 1.84), poleR=(-0.9, -0.2, 0.3), bladeR=(0.05, 0.86, 0.50), bspR='world',
                 handL=(0.02, -0.40, 1.30), footL=tw(CL, y=-0.27, z=0.07, pitch=8))),
        (0.30, P(COMBAT, hips=(0.0, -0.01, 0.885), pelvis=(2, -20, 0), spine=(-2, 6, 0),
                 handR=(-0.28, -0.16, 1.90), poleR=(-0.9, -0.3, 0.2), bladeR=(0.0, 0.30, 0.95), bspR='world',
                 handL=(0.04, -0.38, 1.26), footL=tw(CL, y=-0.42, z=0.05, pitch=-10))),
        # step lands, arm whips down
        (0.36, P(COMBAT, hips=(0.0, -0.09, 0.84), pelvis=(8, -16, 0), spine=(12, 10, 0),
                 handR=(-0.24, -0.46, 1.66), poleR=(-0.8, 0.1, -0.5), bladeR=(0.0, -0.62, 0.78), bspR='world',
                 handL=(0.10, -0.32, 1.20), footL=tw(CL, y=-0.47), footR=tw(CR, pitch=16))),
        (0.42, P(COMBAT, hips=(0.0, -0.13, 0.79), pelvis=(13, -12, 0), spine=(26, 12, 0),
                 handR=(-0.20, -0.54, 1.26), poleR=(-0.7, 0.3, -0.6), bladeR=(0.0, -0.96, -0.28), bspR='world',
                 handL=(0.18, -0.24, 1.12), footL=tw(CL, y=-0.47), footR=tw(CR, pitch=32))),
        (0.50, P(COMBAT, hips=(0.0, -0.13, 0.775), pelvis=(14, -12, 0), spine=(32, 12, 0),
                 handR=(-0.20, -0.40, 1.08), poleR=(-0.7, 0.4, -0.5), bladeR=(0.0, -0.84, -0.54), bspR='world',
                 handL=(0.20, -0.20, 1.10), footL=tw(CL, y=-0.47), footR=tw(CR, pitch=34))),
        (0.66, P(COMBAT, hips=(0.0, -0.06, 0.83), pelvis=(9, -20, 0), spine=(18, 9, 0),
                 handR=(-0.30, -0.22, 1.04), bladeR=(-0.05, -0.80, 0.35), bspR='world',
                 handL=(0.04, -0.34, 1.22), footL=tw(CL, y=-0.36, z=0.04))),
        (0.80, P(COMBAT)),
    ]
    auto_edges(k, 1, 5)
    k[6][1]['edgeR'] = (0.0, -0.4, -0.9)
    k[6][1]['bspR'] = 'world'
    return Clip('atk1h_3', 0.80, keys=k, lag={'head': 0.02, 'handL': 0.03}, nstrip=12, bounds=1.6, view='side_r',
                events={'whoosh': 0.33, 'hit': [0.35, 0.46], 'cancel': 0.56, 'steps': [[0.36, 'L'], [0.74, 'L']]})


def atk1h_heavy():
    """Long wind-up with the sword laid over the right shoulder, then a big diagonal cleave
    (high right -> low left) with the whole body behind it."""
    k = [
        (0.00, P(COMBAT)),
        (0.30, P(COMBAT, hips=(-0.03, 0.07, 0.84), pelvis=(3, -40, 0), spine=(3, -22, -4),
                 handL=(0.10, -0.38, 1.28), footR=tw(CR, yaw=-58),
                 **arm_fore('R', (-0.36, -0.14, 1.52), (0.1, 0.55, 0.83), (0.25, 0.85, -0.45)))),
        # held anticipation, still sinking / twisting a little
        (0.50, P(COMBAT, hips=(-0.035, 0.08, 0.83), pelvis=(3, -44, 0), spine=(2, -26, -5),
                 handL=(0.12, -0.38, 1.28), footR=tw(CR, yaw=-58),
                 **arm_fore('R', (-0.36, -0.13, 1.53), (0.12, 0.60, 0.80), (0.30, 0.80, -0.52)))),
        (0.59, P(COMBAT, hips=(-0.01, 0.0, 0.835), pelvis=(6, -20, 0), spine=(6, -6, 0),
                 handL=(0.18, -0.32, 1.20), footR=tw(CR, pitch=14, yaw=-45),
                 **arm_fore('R', (-0.40, -0.10, 1.50), (-0.1, -0.3, 0.95), (-0.3, 0.6, 0.75)))),
        (0.65, P(COMBAT, hips=(0.01, -0.06, 0.82), pelvis=(9, 2, 0), spine=(14, 14, 2),
                 handL=(0.26, -0.24, 1.14), footR=tw(CR, pitch=28, yaw=-34),
                 **arm_fore('R', (-0.38, -0.20, 1.42), (0.2, -0.85, 0.5), (-0.45, -0.35, 0.82)))),
        (0.70, P(COMBAT, hips=(0.02, -0.10, 0.80), pelvis=(11, 14, 0), spine=(20, 26, 4),
                 handL=(0.30, -0.16, 1.10), footR=tw(CR, pitch=36, yaw=-26),
                 **arm_fore('R', (-0.32, -0.22, 1.28), (0.6, -0.75, -0.25), (-0.1, -0.97, 0.2)))),
        (0.78, P(COMBAT, hips=(0.02, -0.10, 0.785), pelvis=(11, 20, 0), spine=(25, 34, 6),
                 handL=(0.32, -0.12, 1.08), footR=tw(CR, pitch=38, yaw=-24),
                 **arm_fore('R', (-0.25, -0.22, 1.19), (0.8, -0.3, -0.42), (0.35, -0.80, -0.50), 0.28))),
        (0.88, P(COMBAT, hips=(0.02, -0.08, 0.80), pelvis=(10, 16, 0), spine=(22, 30, 5),
                 handL=(0.30, -0.14, 1.10), footR=tw(CR, pitch=30, yaw=-28),
                 **arm_fore('R', (-0.25, -0.21, 1.20), (0.8, -0.25, -0.40), (0.42, -0.78, -0.46), 0.28))),
        (1.10, P(COMBAT)),
    ]
    auto_edges(k, 1, 7)
    k[1][1]['edgeR'] = k[2][1]['edgeR'] = (-0.2, 0.35, 0.92)     # sword rests on its back over the shoulder
    k[7][1]['edgeR'] = k[6][1]['edgeR']
    return Clip('atk1h_heavy', 1.10, keys=k, lag={'head': 0.02, 'handL': 0.04}, nstrip=12, bounds=1.6,
                events={'whoosh': 0.60, 'hit': [0.62, 0.76], 'cancel': 0.88})


def atk1h_thrust():
    """Lunging thrust: coil back, step in with the front foot and stab along the line of attack."""
    fw = (0.02, -0.995, 0.06)
    k = [
        (0.00, P(COMBAT)),
        (0.16, P(COMBAT, hips=(-0.02, 0.07, 0.85), pelvis=(5, -38, 0), spine=(9, -12, 0),
                 handR=(-0.36, 0.16, 1.16), poleR=(-0.4, 0.6, -0.7), bladeR=fw, bspR='world', edgeR=(0, 0, -1),
                 handL=(0.06, -0.38, 1.28), footL=tw(CL, y=-0.25, z=0.03))),
        (0.27, P(COMBAT, hips=(0.02, -0.17, 0.78), pelvis=(11, 16, 0), spine=(15, 22, 0),
                 handR=(-0.24, -0.50, 1.20), poleR=(-0.6, 0.2, -0.75), bladeR=(0.0, -0.99, 0.10), bspR='world', edgeR=(0, 0, -1),
                 handL=(0.28, -0.18, 1.14), footL=tw(CL, y=-0.50), footR=tw(CR, pitch=34, yaw=-30))),
        (0.36, P(COMBAT, hips=(0.02, -0.18, 0.775), pelvis=(12, 18, 0), spine=(16, 24, 0),
                 handR=(-0.23, -0.51, 1.21), poleR=(-0.6, 0.2, -0.75), bladeR=(0.0, -0.99, 0.08), bspR='world', edgeR=(0, 0, -1),
                 handL=(0.30, -0.16, 1.12), footL=tw(CL, y=-0.50), footR=tw(CR, pitch=36, yaw=-30))),
        (0.52, P(COMBAT, hips=(0.0, -0.07, 0.83), pelvis=(8, -10, 0), spine=(12, 12, 0),
                 handR=(-0.32, -0.20, 1.10), bladeR=(-0.03, -0.90, 0.42), bspR='world', edgeR=(0, -0.3, -1),
                 handL=(0.06, -0.34, 1.24), footL=tw(CL, y=-0.38, z=0.04))),
        (0.65, P(COMBAT)),
    ]
    return Clip('atk1h_thrust', 0.65, keys=k, lag={'head': 0.02, 'handL': 0.03}, nstrip=8, bounds=1.6, view='side_r',
                events={'whoosh': 0.22, 'hit': [0.24, 0.36], 'cancel': 0.46, 'steps': [[0.26, 'L'], [0.60, 'L']]})


# ============================================================================ shield
def block_idle_fn(ph, t):
    w = TAU * ph
    p = P(BLOCK)
    h = BLOCK['hips']
    p['hips'] = (h[0], h[1] + 0.004 * math.sin(w), h[2] - 0.008 * (0.5 - 0.5 * math.cos(w)))
    p['spine'] = (13.0 + 1.2 * math.sin(w - 0.6), 6.0, 0.0)
    hl = BLOCK['handL']
    p['handL'] = (hl[0] + 0.004 * math.sin(w - 1.0), hl[1], hl[2] + 0.008 * math.sin(w - 1.3))
    hr = BLOCK['handR']
    p['handR'] = (hr[0], hr[1], hr[2] + 0.006 * math.sin(w - 1.8))
    return p


def block_hit():
    k = [
        (0.00, P(BLOCK)),
        # the blow drives the shield into the body, the torso rocks back over the rear leg
        (0.06, P(BLOCK, hips=(-0.01, 0.085, 0.82), pelvis=(2, -20, -2), spine=(4, 10, 2), head=(12, 0, 0),
                 handL=(-0.06, -0.24, 1.36), poleL=(0.85, 0.2, -0.5), clavL=(8, -4),
                 handR=(-0.40, 0.10, 1.00), bladeR=(-0.30, -0.30, 0.90), footL=tw(BLOCK['footL'], pitch=-8))),
        (0.15, P(BLOCK, hips=(0.0, 0.05, 0.81), pelvis=(8, -22, 0), spine=(15, 6, 0), head=(8, 0, 0),
                 handL=(-0.10, -0.33, 1.36))),
        (0.35, P(BLOCK)),
    ]
    return Clip('block_hit', 0.35, keys=k, lag={'head': 0.03, 'handR': 0.04}, nstrip=8, bounds=1.3, view='side_r',
                events={'impact': 0.03, 'cancel': 0.25})


def parry():
    k = [
        (0.00, P(COMBAT)),
        # tiny inward load, then the shield swipes outward across the front
        (0.06, P(COMBAT, pelvis=(5, -26, 0), spine=(10, 2, 0), handL=(-0.16, -0.32, 1.30), poleL=(0.7, 0.2, -0.7))),
        (0.15, P(COMBAT, hips=(0.01, 0.0, 0.86), pelvis=(5, -18, 0), spine=(9, 26, 2),
                 handL=(0.30, -0.36, 1.50), poleL=(0.2, 0.3, -0.95), twistL=0.0,
                 handR=(-0.36, 0.08, 1.04))),
        (0.23, P(COMBAT, hips=(0.01, 0.0, 0.86), pelvis=(5, -16, 0), spine=(9, 32, 3),
                 handL=(0.44, -0.22, 1.50), poleL=(0.2, 0.4, -0.9), twistL=0.0,
                 handR=(-0.36, 0.08, 1.04))),
        (0.45, P(COMBAT)),
    ]
    return Clip('parry', 0.45, keys=k, lag={'head': 0.02, 'handR': 0.03}, nstrip=8, bounds=1.3,
                events={'whoosh': 0.10, 'parry': [0.07, 0.22], 'cancel': 0.30})


def shield_bash():
    k = [
        (0.00, P(COMBAT)),
        # load: shield pulled to the chest, left shoulder back, weight on the rear leg
        (0.15, P(COMBAT, hips=(0.0, 0.07, 0.85), pelvis=(5, -10, 0), spine=(9, 14, 0),
                 handL=(0.02, -0.25, 1.30), poleL=(0.8, 0.4, -0.5), footL=tw(CL, y=-0.25, z=0.04),
                 handR=(-0.36, 0.06, 1.02))),
        # step and punch: left shoulder driven forward behind the shield
        (0.27, P(COMBAT, hips=(0.0, -0.15, 0.80), pelvis=(10, -42, 0), spine=(14, -10, 0),
                 handL=(0.04, -0.50, 1.36), poleL=(0.8, 0.3, -0.5), clavL=(4, 10),
                 footL=tw(CL, y=-0.48), footR=tw(CR, pitch=30),
                 handR=(-0.38, 0.02, 1.03), bladeR=(-0.2, -0.38, 0.90))),
        (0.35, P(COMBAT, hips=(0.0, -0.15, 0.80), pelvis=(10, -42, 0), spine=(15, -10, 0),
                 handL=(0.04, -0.49, 1.35), poleL=(0.8, 0.3, -0.5), clavL=(4, 8),
                 footL=tw(CL, y=-0.48), footR=tw(CR, pitch=32),
                 handR=(-0.38, 0.02, 1.03), bladeR=(-0.2, -0.38, 0.90))),
        (0.48, P(COMBAT, hips=(0.0, -0.05, 0.84), footL=tw(CL, y=-0.36, z=0.04))),
        (0.60, P(COMBAT)),
    ]
    return Clip('shield_bash', 0.60, keys=k, lag={'head': 0.02, 'handR': 0.04}, nstrip=8, bounds=1.3, view='side_r',
                events={'whoosh': 0.20, 'hit': [0.22, 0.33], 'cancel': 0.44, 'steps': [[0.26, 'L'], [0.56, 'L']]})


def clips():
    out = [atk1h_1(), atk1h_2(), atk1h_3(), atk1h_heavy(), atk1h_thrust(),
           Clip('block_idle', 1.5, loop=True, fn=block_idle_fn, nstrip=4, bounds=1.3),
           block_hit(), parry(), shield_bash()]
    return out
