"""Utility clips: drink, interact, pickup, casting, roar, kneeling at a shrine, NPC talk / idle / hammering."""
from anim_poses import *

TAU = 2 * math.pi
SL, SR = STAND['footL'], STAND['footR']
# natural hanging hand expressed as fingers + palm normal (so clips that use palm mode start / end like STAND)
PALM_L = (0.03, -0.10, -1.0, -1.0, 0.0, 0.0)
PALM_R = (-0.03, -0.10, -1.0, 1.0, 0.0, 0.0)


# ============================================================================ drink / interact / pickup
def drink():
    """Left hand raises a flask to the mouth, head tilts back, lower. (twist 0 = thumb side toward the face,
    which is where the neck of a flask held in the fist points.)"""
    k = [
        (0.00, P(STAND)),
        (0.32, P(STAND, handL=(0.21, -0.30, 1.26), poleL=(0.6, 0.3, -0.75), curlL=1.0, head=(2, 6, 0),
                 spine=(1, 3, 0))),
        (0.54, P(STAND, handL=(0.085, -0.22, 1.56), poleL=(0.85, 0.0, -0.5), curlL=1.0, head=(-10, 2, 0),
                 spine=(-1, 2, 0), wristL=(5.0, 0.0))),
        (0.74, P(STAND, handL=(0.07, -0.185, 1.635), poleL=(0.9, 0.0, -0.3), curlL=1.0, head=(-25, 0, 0),
                 spine=(-5, 0, 0), wristL=(24.0, 0.0), hips=(0.0, 0.012, 0.968))),
        (0.98, P(STAND, handL=(0.07, -0.18, 1.645), poleL=(0.9, 0.0, -0.25), curlL=1.0, head=(-28, 0, 0),
                 spine=(-6, 0, 0), wristL=(30.0, 0.0), hips=(0.0, 0.014, 0.968))),
        (1.16, P(STAND, handL=(0.17, -0.30, 1.36), poleL=(0.7, 0.2, -0.7), curlL=1.0, head=(-4, 3, 0),
                 spine=(0, 2, 0))),
        (1.40, P(STAND)),
    ]
    return Clip('drink', 1.40, keys=k, props='drink', lag={'head': 0.03}, nstrip=8, bounds=1.25,
                events={'release': 0.85, 'cancel': 1.15})


def interact():
    """Reach forward with the left hand at chest height (push a door, pull a lever, loot) and back."""
    k = [
        (0.00, P(STAND, palmL=PALM_L)),
        (0.30, P(STAND, hips=(0.0, -0.03, 0.96), pelvis=(3, -6, 0), spine=(8, -12, 0), head=(4, 12, 0),
                 handL=(0.13, -0.50, 1.31), poleL=(0.7, 0.2, -0.7), curlL=0.15,
                 palmL=(0.0, -0.94, 0.34, 0.0, -0.34, -0.94))),
        (0.48, P(STAND, hips=(0.0, -0.035, 0.958), pelvis=(3, -7, 0), spine=(9, -14, 0), head=(4, 13, 0),
                 handL=(0.12, -0.525, 1.30), poleL=(0.7, 0.2, -0.7), curlL=0.35,
                 palmL=(0.0, -0.96, 0.28, 0.0, -0.28, -0.96))),
        (0.90, P(STAND, palmL=PALM_L)),
    ]
    return Clip('interact', 0.90, keys=k, lag={'head': 0.02}, nstrip=8, bounds=1.25,
                events={'release': 0.40, 'cancel': 0.60})


def pickup():
    """Crouch, grab something on the ground with the left hand, stand."""
    low = dict(hips=(0.0, 0.08, 0.40), pelvis=(34, 0, 0), spine=(48, -10, 0), head=(-20, 6, 0),
               footL=tw(SL, pitch=24), footR=(-0.115, 0.13, 0.0, 46, -11, 0),
               handR=(-0.40, -0.14, 1.06), poleR=(-0.6, 0.7, -0.3), bladeR=(-0.45, -0.88, 0.12), bspR='world',
               hspL='world', poleL=(0.7, 0.5, 0.4))
    k = [
        (0.00, P(STAND, palmL=PALM_L)),
        (0.18, P(STAND, hips=(0.0, 0.04, 0.80), pelvis=(14, 0, 0), spine=(22, -5, 0), head=(4, 3, 0),
                 footR=(-0.11, 0.08, 0.03, 14, -11, 0), handL=(0.22, -0.26, 0.97), palmL=(0.0, -0.5, -0.87, -0.9, 0.2, -0.3),
                 handR=(-0.34, -0.08, 0.96), bladeR=(-0.15, -0.88, -0.2))),
        (0.36, P(STAND, handL=(0.13, -0.36, 0.11), curlL=0.1, palmL=(0.0, -0.75, -0.66, 0.0, -0.66, -0.75), **low)),
        (0.48, P(STAND, handL=(0.13, -0.36, 0.10), curlL=1.0, palmL=(0.0, -0.75, -0.66, 0.0, -0.66, -0.75), **low)),
        (0.68, P(STAND, hips=(0.0, 0.035, 0.82), pelvis=(12, 0, 0), spine=(20, -4, 0), head=(2, 2, 0),
                 footR=(-0.11, 0.07, 0.03, 12, -11, 0), handL=(0.24, -0.22, 0.98), curlL=1.0,
                 palmL=(0.0, -0.5, -0.87, -0.9, 0.2, -0.3), handR=(-0.34, -0.08, 0.96), bladeR=(-0.15, -0.88, -0.2))),
        (0.90, P(STAND, palmL=PALM_L)),
    ]
    return Clip('pickup', 0.90, keys=k, lag={'head': 0.02}, nstrip=8, bounds=1.25, view='persp_l',
                events={'release': 0.44, 'cancel': 0.70})


# ============================================================================ casting / roar
def cast():
    """Thrust the left palm forward: projectile leaves at ~0.40 s."""
    k = [
        (0.00, P(STAND, palmL=PALM_L)),
        (0.20, P(STAND, hips=(0.0, 0.03, 0.95), pelvis=(2, 8, 0), spine=(2, 16, 0), head=(2, -20, 0),
                 handL=(0.25, -0.04, 1.30), poleL=(0.6, 0.7, -0.4), curlL=0.25,
                 palmL=(0.0, -0.75, 0.66, 0.0, -0.66, -0.75), handR=(-0.30, -0.06, 0.93))),
        (0.36, P(STAND, hips=(0.0, -0.05, 0.945), pelvis=(4, -8, 0), spine=(8, -18, 0), head=(2, 24, 0),
                 handL=(0.09, -0.53, 1.38), poleL=(0.7, 0.2, -0.7), curlL=0.0,
                 palmL=(0.0, -0.55, 0.83, 0.0, -0.83, -0.55), handR=(-0.33, 0.06, 0.95), footR=tw(SR, pitch=16))),
        (0.46, P(STAND, hips=(0.0, -0.04, 0.95), pelvis=(4, -7, 0), spine=(6, -15, 0), head=(2, 20, 0),
                 handL=(0.10, -0.49, 1.40), poleL=(0.7, 0.2, -0.7), curlL=0.05,
                 palmL=(0.0, -0.45, 0.89, 0.0, -0.89, -0.45), handR=(-0.33, 0.05, 0.95), footR=tw(SR, pitch=12))),
        (0.80, P(STAND, palmL=PALM_L)),
    ]
    return Clip('cast', 0.80, keys=k, lag={'head': 0.02, 'handR': 0.04}, nstrip=8, bounds=1.25,
                events={'release': 0.40, 'cancel': 0.55})


def cast_big():
    """Raise both arms gathering power, then slam them forward / down (release at ~1.0 s)."""
    up = dict(poleL=(0.8, 0.3, -0.4), poleR=(-0.8, 0.3, -0.4))
    k = [
        (0.00, P(STAND, palmL=PALM_L)),
        (0.24, P(STAND, hips=(0.0, 0.02, 0.94), pelvis=(4, 0, 0), spine=(10, 0, 0), head=(6, 0, 0),
                 handL=(0.34, -0.26, 1.10), handR=(-0.34, -0.26, 1.08), bladeR=(-0.3, -0.75, 0.6),
                 palmL=(0.1, -0.95, 0.3, 0.0, 0.3, 0.95), curlL=0.3)),
        (0.60, P(STAND, hips=(0.0, 0.03, 0.985), pelvis=(-3, 0, 0), spine=(-12, 0, 0), head=(-16, 0, 0),
                 footL=tw(SL, pitch=14), footR=tw(SR, pitch=14),
                 handL=(0.34, -0.12, 1.86), handR=(-0.34, -0.12, 1.86), bladeR=(-0.25, 0.88, 0.40),
                 palmL=(-0.3, 0.1, 0.95, -0.9, -0.3, -0.3), curlL=0.0, **up)),
        (0.88, P(STAND, hips=(0.0, 0.04, 0.99), pelvis=(-4, 0, 0), spine=(-16, 0, 0), head=(-20, 0, 0),
                 footL=tw(SL, pitch=18), footR=tw(SR, pitch=18),
                 handL=(0.30, -0.06, 1.90), handR=(-0.30, -0.06, 1.90), bladeR=(-0.2, 0.95, 0.22),
                 palmL=(-0.3, 0.2, 0.93, -0.9, -0.3, -0.2), curlL=0.0, **up)),
        (1.00, P(STAND, hips=(0.0, -0.02, 0.87), pelvis=(12, 0, 0), spine=(30, 0, 0), head=(-10, 0, 0),
                 handL=(0.20, -0.48, 1.24), handR=(-0.24, -0.48, 1.24), bladeR=(-0.80, -0.35, -0.48),
                 poleL=(0.8, 0.3, -0.5), poleR=(-0.8, 0.3, -0.5),
                 palmL=(0.0, -0.8, 0.6, 0.0, -0.6, -0.8), curlL=0.0)),
        (1.12, P(STAND, hips=(0.0, -0.02, 0.85), pelvis=(14, 0, 0), spine=(35, 0, 0), head=(-12, 0, 0),
                 handL=(0.20, -0.45, 1.14), handR=(-0.24, -0.45, 1.14), bladeR=(-0.78, -0.30, -0.55),
                 poleL=(0.8, 0.3, -0.5), poleR=(-0.8, 0.3, -0.5),
                 palmL=(0.0, -0.9, 0.44, 0.0, -0.44, -0.9), curlL=0.0)),
        (1.60, P(STAND, palmL=PALM_L)),
    ]
    return Clip('cast_big', 1.60, keys=k, lag={'head': 0.03}, nstrip=12, bounds=1.45, view='persp',
                events={'release': 1.0, 'cancel': 1.25})


def _roar_shake(t0, t1, amp):
    def post(t, pz):
        e = smooth((t - t0) / 0.12) * (1.0 - smooth((t - t1) / 0.2))
        if e > 1e-3:
            s1, s2 = math.sin(TAU * 11.0 * t), math.sin(TAU * 13.7 * t + 1.0)
            hd = pz['head']
            pz['head'] = (hd[0] + amp * e * s1, hd[1] + 0.7 * amp * e * s2, hd[2])
            sp = pz['spine']
            pz['spine'] = (sp[0] + 0.4 * amp * e * s2, sp[1], sp[2])
    return post


def roar():
    """Battle roar: arms out and back, chest forward, head back."""
    out = dict(handL=(0.50, 0.14, 1.06), poleL=(0.6, 0.7, 0.1), handR=(-0.52, 0.12, 1.06), poleR=(-0.6, 0.7, 0.1),
               bladeR=(-0.45, -0.86, -0.22), twistL=40.0, curlL=0.9)
    k = [
        (0.00, P(STAND)),
        (0.28, P(STAND, hips=(0.0, 0.03, 0.92), pelvis=(8, 0, 0), spine=(14, 0, 0), head=(8, 0, 0),
                 handL=(0.26, -0.20, 1.02), handR=(-0.30, -0.06, 0.95), curlL=0.9, clavL=(6, 4), clavR=(6, 4))),
        (0.52, P(STAND, hips=(0.0, -0.03, 0.935), pelvis=(6, 0, 0), spine=(-16, 0, 0), head=(-28, 0, 0),
                 footL=tw(SL, x=0.15, yaw=14), footR=tw(SR, x=-0.15, yaw=-16), clavL=(0, -8), clavR=(0, -8), **out)),
        (1.15, P(STAND, hips=(0.0, -0.035, 0.93), pelvis=(7, 0, 0), spine=(-18, 0, 0), head=(-30, 0, 0),
                 footL=tw(SL, x=0.15, yaw=14), footR=tw(SR, x=-0.15, yaw=-16), clavL=(0, -8), clavR=(0, -8), **out)),
        (1.60, P(STAND)),
    ]
    k[2][1]['footL'] = tw(SL, x=0.15, yaw=14)
    return Clip('roar', 1.60, keys=k, post=_roar_shake(0.5, 1.15, 1.6), nstrip=8, bounds=1.3,
                events={'release': 0.50, 'cancel': 1.30})


# ============================================================================ kneeling at a shrine
def kneel_fn(ph, t):
    w = TAU * ph
    p = P(KNEEL)
    h = KNEEL['hips']
    p['hips'] = (h[0], h[1], h[2] + 0.004 * math.sin(w))
    p['spine'] = (14.0 - 1.6 * math.sin(w), 4.0, 0.0)
    p['head'] = (26.0 + 1.2 * math.sin(w - 0.8), 2.0, 0.0)
    p['clavL'] = (1.5 * math.sin(w), 0.0)
    p['clavR'] = (1.5 * math.sin(w), 0.0)
    return p


def kneel_down():
    k = [
        (0.00, P(STAND, palmL=PALM_L)),
        (0.24, P(STAND, hips=(0.0, 0.03, 0.88), pelvis=(6, -3, 0), spine=(8, 2, 0), head=(6, 0, 0),
                 footL=tw(SL, x=0.12, y=-0.10, z=0.05, pitch=-6), footR=tw(SR, x=-0.11, y=0.06, pitch=20),
                 handR=(-0.28, -0.18, 0.97), bladeR=(-0.55, -0.50, -0.67), palmL=PALM_L)),
        (0.52, P(KNEEL, hips=(0.0, 0.04, 0.66), pelvis=(8, -6, 0), spine=(14, 4, 0), head=(12, 2, 0),
                 handL=(0.22, -0.30, 0.74), handR=(-0.19, -0.41, 0.88))),
        (0.80, P(KNEEL)),
    ]
    return Clip('kneel_down', 0.80, keys=k, props='1h', lag={'head': 0.03}, nstrip=8, bounds=1.25,
                events={'steps': [[0.36, 'L']], 'impact': 0.62})


def kneel_up():
    k = [
        (0.00, P(KNEEL)),
        (0.28, P(KNEEL, hips=(0.0, 0.03, 0.66), pelvis=(10, -6, 0), spine=(18, 4, 0), head=(8, 2, 0),
                 handL=(0.22, -0.30, 0.74), handR=(-0.19, -0.41, 0.88))),
        (0.56, P(STAND, hips=(0.0, 0.02, 0.89), pelvis=(6, -3, 0), spine=(8, 2, 0), head=(2, 0, 0),
                 footL=tw(SL, x=0.12, y=-0.10, z=0.04, pitch=6), footR=tw(SR, x=-0.11, y=0.08, pitch=22),
                 handR=(-0.28, -0.18, 0.97), bladeR=(-0.55, -0.50, -0.67), palmL=PALM_L)),
        (0.80, P(STAND, palmL=PALM_L)),
    ]
    return Clip('kneel_up', 0.80, keys=k, props='1h', lag={'head': 0.03}, nstrip=8, bounds=1.25,
                events={'steps': [[0.66, 'L'], [0.70, 'R']]})


# ============================================================================ NPC
def talk():
    """Standing conversation: the right hand does most of the talking, the left answers, nods."""
    rest = dict(handR=NPC['handR'], palmR=PALM_R, poleR=NPC['poleR'], handL=NPC['handL'], palmL=PALM_L,
                poleL=NPC['poleL'], curlR=0.35, curlL=0.35)
    gp = (-0.75, 0.1, -0.65)
    k = [
        (0.00, P(NPC, hips=(0.012, 0.005, 0.966), pelvis=(1, 2, -1), spine=(2, -2, 0), head=(2, 4, 0), **rest)),
        (0.45, P(NPC, hips=(0.014, 0.005, 0.966), pelvis=(1, 3, -1), spine=(3, -4, 0), head=(4, 6, 2),
                 handR=(-0.27, -0.34, 1.20), poleR=gp, palmR=(0.25, -0.93, 0.25, 0.0, 0.26, 0.96), curlR=0.2,
                 handL=NPC['handL'], palmL=PALM_L, poleL=NPC['poleL'], curlL=0.35)),
        (0.85, P(NPC, hips=(0.010, 0.005, 0.966), pelvis=(1, 1, -1), spine=(2, -7, 0), head=(-2, 8, -2),
                 handR=(-0.40, -0.36, 1.16), poleR=gp, palmR=(-0.25, -0.93, 0.25, 0.2, 0.2, 0.96), curlR=0.1,
                 handL=NPC['handL'], palmL=PALM_L, poleL=NPC['poleL'], curlL=0.35)),
        (1.25, P(NPC, hips=(0.004, 0.005, 0.967), pelvis=(1, 0, 0), spine=(4, -3, 0), head=(8, 3, 0),
                 handR=(-0.25, -0.33, 1.25), poleR=gp, palmR=(0.3, -0.85, 0.42, -0.3, 0.3, 0.9), curlR=0.3,
                 handL=(0.27, -0.12, 0.98), palmL=(0.1, -0.7, -0.7, -0.9, 0.0, -0.3), poleL=(0.6, 0.7, -0.3), curlL=0.3)),
        (1.75, P(NPC, hips=(-0.008, 0.005, 0.966), pelvis=(1, -2, 1), spine=(3, 3, 0), head=(0, -4, 0),
                 handR=(-0.29, -0.24, 1.08), poleR=gp, palmR=(0.2, -0.9, -0.4, 0.4, 0.3, 0.86), curlR=0.3,
                 handL=(0.25, -0.33, 1.16), palmL=(-0.25, -0.93, 0.25, 0.0, 0.26, 0.96), poleL=(0.75, 0.1, -0.65), curlL=0.2)),
        (2.15, P(NPC, hips=(-0.012, 0.005, 0.966), pelvis=(1, -3, 1), spine=(2, 5, 0), head=(-3, -7, 2),
                 handR=(-0.28, -0.10, 0.98), poleR=NPC['poleR'], palmR=(-0.1, -0.5, -0.86, 0.9, 0.0, -0.3), curlR=0.35,
                 handL=(0.36, -0.34, 1.12), palmL=(0.25, -0.93, 0.25, -0.2, 0.2, 0.96), poleL=(0.75, 0.1, -0.65), curlL=0.1)),
        (2.60, P(NPC, hips=(0.0, 0.005, 0.967), pelvis=(1, 0, 0), spine=(3, 1, 0), head=(6, -2, 0),
                 handR=NPC['handR'], palmR=PALM_R, poleR=NPC['poleR'], curlR=0.35,
                 handL=(0.27, -0.14, 1.00), palmL=(0.1, -0.7, -0.7, -0.9, 0.0, -0.3), poleL=(0.6, 0.7, -0.3), curlL=0.3)),
        (3.00, P(NPC, hips=(0.012, 0.005, 0.966), pelvis=(1, 2, -1), spine=(2, -2, 0), head=(2, 4, 0), **rest)),
    ]
    return Clip('talk', 3.0, loop=True, keys=k, props='none', lag={'head': 0.05}, nstrip=8, bounds=1.25)


def idle_npc_fn(ph, t):
    """Unarmed civilian: hands on hips, weight shifting from one leg to the other, looking around."""
    w = TAU * ph
    sw = math.sin(w)                         # + = weight on the left leg
    br = math.sin(2 * w + 0.5)
    p = P(NPC)
    p['hips'] = (0.035 * sw, 0.008 + 0.004 * math.sin(2 * w), 0.966 - 0.006 * abs(sw))
    p['pelvis'] = (1.0, 2.0 * math.sin(w - 0.5), -3.2 * sw)
    p['spine'] = (2.0 - 1.2 * br, -3.0 * math.sin(w - 0.5), 2.6 * sw)
    p['head'] = (2.0 + 3.0 * math.sin(2 * w + 1.0), 24.0 * math.sin(w + 1.9) + 6.0 * math.sin(2 * w), -1.0 * sw)
    p['footL'] = tw(NPC['footL'], x=0.125, yaw=14)
    p['footR'] = tw(NPC['footR'], x=-0.125, yaw=-16)
    p['clavL'] = (2.0 + 1.2 * br, 0.0)
    p['clavR'] = (2.0 + 1.2 * br, 0.0)
    p['hspL'] = p['hspR'] = 'hips'
    p['handL'] = (0.215, 0.015, 1.045)
    p['handR'] = (-0.215, 0.015, 1.045)
    p['poleL'] = (0.85, 0.5, 0.1)
    p['poleR'] = (-0.85, 0.5, 0.1)
    p['palmL'] = (-0.25, -0.75, -0.6, -0.9, 0.3, 0.0)
    p['palmR'] = (0.25, -0.75, -0.6, 0.9, 0.3, 0.0)
    p['curlL'] = p['curlR'] = 0.3
    return p


_HAMMER_STANCE = dict(
    hips=(0.0, 0.03, 0.90), pelvis=(8, -8, 0), head=(14, 4, 0), hstab=0.0,
    footL=(0.15, -0.13, 0, 0, 8, 0), footR=(-0.17, 0.12, 0, 0, -28, 0),
    handL=(0.10, -0.44, 0.87), hspL='world', poleL=(0.7, 0.5, -0.2), palmL=(-0.5, -0.8, -0.3, 0.0, -0.3, -0.95), curlL=0.9,
    curlR=1.0, bspR='world', hspR='chest')


def work_hammer():
    """Blacksmith: hammer blows on an anvil at hip height (top at z = 0.80, 0.5 m in front)."""
    k = [
        (0.00, P(NPC, spine=(22, -4, 0), handR=(-0.24, -0.36, 1.16), poleR=(-0.8, 0.4, -0.4),
                 bladeR=(0.15, -0.96, 0.22), edgeR=(0, 0, -1), **_HAMMER_STANCE)),
        (0.30, P(NPC, spine=(16, -9, 0), handR=(-0.34, -0.20, 1.50), poleR=(-0.9, 0.2, -0.3),
                 bladeR=(0.05, -0.30, 0.95), edgeR=(0, -1, -0.3), **_HAMMER_STANCE)),
        (0.48, P(NPC, spine=(13, -12, 0), handR=(-0.36, -0.12, 1.64), poleR=(-0.9, 0.1, -0.2),
                 bladeR=(0.0, 0.45, 0.89), edgeR=(0, -0.9, 0.45), **_HAMMER_STANCE)),
        (0.62, P(NPC, spine=(19, -7, 0), handR=(-0.30, -0.36, 1.44), poleR=(-0.9, 0.3, -0.3),
                 bladeR=(0.08, -0.72, 0.69), edgeR=(0, -0.69, -0.72), **_HAMMER_STANCE)),
        (0.70, P(NPC, spine=(26, -2, 0), handR=(-0.23, -0.40, 1.10), poleR=(-0.8, 0.4, -0.4),
                 bladeR=(0.16, -0.985, -0.06), edgeR=(0, 0, -1), **_HAMMER_STANCE)),
        (0.80, P(NPC, spine=(24, -3, 0), handR=(-0.23, -0.39, 1.15), poleR=(-0.8, 0.4, -0.4),
                 bladeR=(0.15, -0.975, 0.16), edgeR=(0, 0, -1), **_HAMMER_STANCE)),
        (1.20, P(NPC, spine=(22, -4, 0), handR=(-0.24, -0.36, 1.16), poleR=(-0.8, 0.4, -0.4),
                 bladeR=(0.15, -0.96, 0.22), edgeR=(0, 0, -1), **_HAMMER_STANCE)),
    ]
    for t, pz in k:
        s = pz['spine'][0]
        pz['hips'] = (0.0, 0.03, 0.90 - 0.0025 * (s - 13))
    return Clip('work_hammer', 1.2, loop=True, keys=k, props='hammer', lag={'head': 0.03}, nstrip=8, bounds=1.3,
                events={'impact': 0.70, 'whoosh': 0.60})


def clips():
    return [drink(), interact(), pickup(), cast(), cast_big(), roar(),
            kneel_down(), Clip('kneel', 2.5, loop=True, fn=kneel_fn, props='1h', nstrip=4, bounds=1.25), kneel_up(),
            talk(), Clip('idle_npc', 4.0, loop=True, fn=idle_npc_fn, props='none', nstrip=8, bounds=1.25),
            work_hammer()]
