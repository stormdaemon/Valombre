"""Monster set (undead, trolls, golems): same rig, heavier, hunched, menacing. Unarmed (claws / fists)."""
from anim_poses import *
from anim_clips_loco import Gait, _c, _s

TAU = 2 * math.pi
ML, MR = MONSTER['footL'], MONSTER['footR']
MHL, MHR = MONSTER['handL'], MONSTER['handR']


def _dangle(p, swing_l=0.0, swing_r=0.0, lift_l=0.0, lift_r=0.0, out=0.0):
    """Hanging arms: hands swing fore / aft under the shoulders (chest space)."""
    p['hspL'] = p['hspR'] = 'chest'
    p['handL'] = (MHL[0] + out, MHL[1] - swing_l, MHL[2] + lift_l)
    p['handR'] = (MHR[0] - out, MHR[1] - swing_r, MHR[2] + lift_r)
    p['poleL'], p['poleR'] = MONSTER['poleL'], MONSTER['poleR']
    p['twistL'] = p['twistR'] = -20.0
    p['wristL'] = p['wristR'] = (15.0, 0.0)
    p['curlL'] = p['curlR'] = 0.45
    p['clavL'] = p['clavR'] = (0.0, 0.0)


def m_idle_fn(ph, t):
    w = TAU * ph
    sw = math.sin(w)
    br = math.sin(w - 0.6)
    p = P(MONSTER)
    h = MONSTER['hips']
    p['hips'] = (0.026 * sw, h[1] + 0.008 * math.sin(2 * w), h[2] - 0.012 * (0.5 + 0.5 * math.cos(2 * w)))
    p['pelvis'] = (14.0 + 1.0 * br, 2.0 * math.sin(w - 0.4), -2.4 * sw)
    p['spine'] = (34.0 + 3.0 * br, -4.0 * math.sin(w - 0.4), 3.0 * sw)
    p['head'] = (10.0 + 3.0 * math.sin(2 * w), 9.0 * math.sin(w + 1.5), 3.0 * math.sin(w + 0.8))
    _dangle(p, swing_l=0.035 * math.sin(w - 1.0), swing_r=0.035 * math.sin(w - 1.6),
            lift_l=0.012 * br, lift_r=0.012 * br, out=0.01 * math.sin(2 * w))
    p['clavL'] = p['clavR'] = (2.5 * br, 0.0)
    return p


G_MWALK = Gait(T=1.3, v=1.2, d=0.66, land=0.39, base={'L': (0.16, 0.02), 'R': (-0.16, 0.02)}, lift=0.07, peak=0.5,
               strike=-8.0, toeoff=40.0, swingp=6.0, vel_k=0.7, flat0=0.12, flat1=0.6, yaw={'L': 15.0, 'R': -17.0},
               swing_out=0.03)


def m_walk_fn(ph, t):
    g = G_MWALK
    c = _c(ph)
    roll = -5.0 * _s(ph, -0.04)
    p = {'fspL': 'world', 'fspR': 'world'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.05 * _c(ph, 0.33), 0.05 + 0.012 * _c(ph, 0.15, 2), 0.848 + 0.022 * _c(ph, 0.32, 2))
    p['pelvis'] = (13.0 + 2.0 * _c(ph, 0.10, 2), -8.0 * c, roll)
    p['spine'] = (34.0 + 4.0 * _c(ph, 0.14, 2), 10.0 * _c(ph, 0.05), 3.0 * _s(ph, 0.02) - roll * 0.5)
    p['head'] = (12.0 + 3.0 * _c(ph, 0.2, 2), 5.0 * _c(ph, 0.2), 0.0)
    p['hstab'] = 0.6
    _dangle(p, swing_l=-0.11 * _c(ph, 0.12), swing_r=0.11 * _c(ph, 0.12),
            lift_l=0.02 * _c(ph, 0.2, 2), lift_r=0.02 * _c(ph, 0.2, 2))
    return p


G_MRUN = Gait(T=0.75, v=4.0, d=0.30, land=0.34, base={'L': (0.12, 0.0), 'R': (-0.12, 0.0)}, lift=0.20, peak=0.38,
              strike=-4.0, toeoff=62.0, swingp=34.0, vel_k=0.55, flat0=0.12, flat1=0.42, yaw={'L': 10.0, 'R': -10.0})


def m_run_fn(ph, t):
    """Loping run: big torso heave, arms clawing forward alternately."""
    g = G_MRUN
    ca = _c(ph, 0.05)
    roll = -4.0 * _s(ph, -0.02)
    p = {'fspL': 'world', 'fspR': 'world'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.02 * _c(ph, 0.18), 0.08 + 0.015 * _c(ph, 0.3, 2), 0.835 + 0.034 * _c(ph, 0.40, 2) + 0.012 * _c(ph, 0.4))
    p['pelvis'] = (20.0 + 3.0 * _c(ph, 0.18, 2), -10.0 * _c(ph, -0.08), roll)
    p['spine'] = (36.0 + 5.0 * _c(ph, 0.22, 2) + 3.0 * _c(ph, 0.3), 20.0 * _c(ph, 0.02), -roll * 0.6)
    p['head'] = (8.0, 0.0, 0.0)
    p['hstab'] = 0.75
    p['hspL'] = p['hspR'] = 'chest'
    wR, poleR, fR = arm_angles('R', fwd=44 + 38 * ca, out=20, bend=58 - 22 * ca, inw=6)
    wL, poleL, fL = arm_angles('L', fwd=44 - 38 * ca, out=20, bend=58 + 22 * ca, inw=6)
    p['handR'], p['poleR'], p['handL'], p['poleL'] = wR, poleR, wL, poleL
    p['twistL'] = p['twistR'] = -30.0
    p['wristL'] = (-20.0 + 15.0 * ca, 0.0)
    p['wristR'] = (-20.0 - 15.0 * ca, 0.0)
    p['curlL'] = p['curlR'] = 0.4
    p['clavL'] = p['clavR'] = (0.0, 0.0)
    return p


G_MCHARGE = Gait(T=0.6, v=5.5, d=0.28, land=0.34, base={'L': (0.11, 0.0), 'R': (-0.11, 0.0)}, lift=0.24, peak=0.36,
                 strike=0.0, toeoff=64.0, swingp=40.0, vel_k=0.5, flat0=0.1, flat1=0.4, yaw={'L': 4.0, 'R': -14.0})


def m_charge_fn(ph, t):
    """Bull rush: body low, left shoulder leading, head tucked behind it, right arm pumping."""
    g = G_MCHARGE
    ca = _c(ph, 0.05)
    roll = -3.0 * _s(ph, -0.02)
    p = {'fspL': 'world', 'fspR': 'world'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.012 * _c(ph, 0.18), 0.12 + 0.012 * _c(ph, 0.3, 2), 0.80 + 0.028 * _c(ph, 0.40, 2))
    p['pelvis'] = (24.0 + 2.0 * _c(ph, 0.18, 2), -22.0 - 7.0 * _c(ph, -0.08), roll)
    p['spine'] = (36.0 + 3.0 * _c(ph, 0.22, 2), -14.0 + 8.0 * _c(ph, 0.02), -4.0 - roll * 0.6)
    p['head'] = (22.0, 14.0, 4.0)
    p['hstab'] = 0.7
    p['hspL'] = p['hspR'] = 'chest'
    # left arm folded across the chest, shoulder forward
    p['handL'] = (0.02 + 0.01 * ca, -0.30, 1.30 + 0.015 * _c(ph, 0.3, 2))
    p['poleL'] = (0.6, -0.5, -0.6)
    p['clavL'] = (8.0, 14.0)
    p['twistL'], p['wristL'], p['curlL'] = 0.0, (10.0, 0.0), 1.0
    wR, poleR, fR = arm_angles('R', fwd=-10 + 30 * ca, out=18, bend=80 + 12 * ca, inw=8)
    p['handR'], p['poleR'] = wR, poleR
    p['clavR'] = (0.0, 0.0)
    p['twistR'], p['wristR'], p['curlR'] = 0.0, (0.0, 0.0), 1.0
    return p


# ============================================================================ attacks
def _swipe_keys():
    """Right arm claw swipe (from the outside to the inside, across the front at chest height)."""
    claw = dict(curlR=0.55, twistR=-50.0)
    return [
        (0.00, P(MONSTER)),
        # wind-up: arm thrown back and out, torso coils to the right, weight on the right leg
        (0.24, P(MONSTER, hips=(-0.05, 0.08, 0.85), pelvis=(10, -22, 2), spine=(22, -30, -6), head=(10, 0, 0),
                 handR=(-0.56, 0.16, 1.44), poleR=(-0.6, 0.7, -0.4), wristR=(-25.0, 0.0),
                 handL=(0.22, -0.44, 1.18), footL=tw(ML, pitch=0), **claw)),
        (0.33, P(MONSTER, hips=(-0.01, 0.02, 0.83), pelvis=(14, -4, 0), spine=(32, -6, -2), head=(10, 0, 0),
                 handR=(-0.56, -0.26, 1.42), poleR=(-0.7, 0.5, -0.5), wristR=(-10.0, 0.0),
                 handL=(0.28, -0.36, 1.10), footR=tw(MR, pitch=16), **claw)),
        (0.39, P(MONSTER, hips=(0.03, -0.03, 0.81), pelvis=(16, 12, -2), spine=(38, 20, 2), head=(12, 0, 0),
                 handR=(-0.22, -0.52, 1.30), poleR=(-0.8, 0.3, -0.5), wristR=(15.0, 0.0),
                 handL=(0.34, -0.26, 1.08), footR=tw(MR, pitch=28, yaw=-8), **claw)),
        (0.47, P(MONSTER, hips=(0.05, -0.04, 0.80), pelvis=(17, 22, -3), spine=(42, 36, 4), head=(12, 0, 0),
                 handR=(0.06, -0.42, 1.22), poleR=(-0.8, 0.2, -0.5), wristR=(30.0, 0.0),
                 handL=(0.38, -0.18, 1.08), footR=tw(MR, pitch=32, yaw=-4), **claw)),
        (0.58, P(MONSTER, hips=(0.05, -0.03, 0.81), pelvis=(16, 20, -3), spine=(40, 32, 4), head=(12, 0, 0),
                 handR=(0.10, -0.36, 1.16), poleR=(-0.8, 0.2, -0.5), wristR=(30.0, 0.0),
                 handL=(0.38, -0.20, 1.08), footR=tw(MR, pitch=26, yaw=-6), **claw)),
        (0.80, P(MONSTER)),
    ]


def m_swipe(side):
    k = _swipe_keys()
    if side == 'L':
        k = [(t, mirror_pose(pz)) for t, pz in k]
    return Clip('m_swipe_' + side, 0.80, keys=k, props='none', lag={'head': 0.03, 'hand' + ('L' if side == 'R' else 'R'): 0.05},
                nstrip=8, bounds=1.4, view='persp' if side == 'R' else 'persp_l',
                events={'whoosh': 0.30, 'hit': [0.32, 0.48], 'cancel': 0.62})


def m_smash():
    """Rear up with both arms overhead, then slam the ground (impact at 0.70 s)."""
    up = dict(poleL=(0.8, 0.2, -0.4), poleR=(-0.8, 0.2, -0.4), curlL=1.0, curlR=1.0, twistL=0.0, twistR=0.0,
              wristL=(0.0, 0.0), wristR=(0.0, 0.0))
    dn = dict(hspL='world', hspR='world', poleL=(0.8, 0.4, 0.3), poleR=(-0.8, 0.4, 0.3), curlL=1.0, curlR=1.0,
              twistL=0.0, twistR=0.0, wristL=(0.0, 0.0), wristR=(0.0, 0.0))
    k = [
        (0.00, P(MONSTER)),
        (0.22, P(MONSTER, hips=(0.0, 0.07, 0.82), pelvis=(18, 0, 0), spine=(40, 0, 0), head=(8, 0, 0),
                 handL=(0.26, -0.36, 1.06), handR=(-0.26, -0.36, 1.06), curlL=0.9, curlR=0.9)),
        (0.44, P(MONSTER, hips=(0.0, 0.06, 0.95), pelvis=(-2, 0, 0), spine=(-10, 0, 0), head=(-8, 0, 0),
                 footL=tw(ML, pitch=10), footR=tw(MR, pitch=10),
                 handL=(0.24, -0.06, 1.94), handR=(-0.24, -0.06, 1.94), **up)),
        (0.58, P(MONSTER, hips=(0.0, 0.07, 0.96), pelvis=(-4, 0, 0), spine=(-14, 0, 0), head=(-4, 0, 0),
                 footL=tw(ML, pitch=14), footR=tw(MR, pitch=14),
                 handL=(0.22, 0.0, 1.97), handR=(-0.22, 0.0, 1.97), **up)),
        (0.70, P(MONSTER, hips=(0.0, 0.05, 0.46), pelvis=(45, 0, 0), spine=(55, 0, 0), head=(-6, 0, 0),
                 handL=(0.24, -0.62, 0.10), handR=(-0.24, -0.62, 0.10), **dn)),
        (0.84, P(MONSTER, hips=(0.0, 0.05, 0.45), pelvis=(46, 0, 0), spine=(56, 0, 0), head=(-2, 0, 0),
                 handL=(0.24, -0.62, 0.095), handR=(-0.24, -0.62, 0.095), **dn)),
        (1.06, P(MONSTER, hips=(0.0, 0.05, 0.78), pelvis=(22, 0, 0), spine=(42, 0, 0), head=(8, 0, 0),
                 handL=(0.28, -0.40, 1.10), handR=(-0.28, -0.40, 1.10), curlL=0.6, curlR=0.6)),
        (1.30, P(MONSTER)),
    ]
    return Clip('m_smash', 1.30, keys=k, props='none', lag={'head': 0.03}, nstrip=12, bounds=1.5, view='side_r',
                events={'whoosh': 0.62, 'hit': [0.64, 0.76], 'impact': 0.70, 'cancel': 1.0})


def m_stomp():
    """Raise the right knee high, then stomp (impact at 0.50 s)."""
    k = [
        (0.00, P(MONSTER)),
        (0.34, P(MONSTER, hips=(0.08, 0.07, 0.93), pelvis=(2, 6, -8), spine=(22, -6, 10), head=(14, -6, 0),
                 footR=(-0.20, -0.24, 0.60, 24, -18, 0), kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0),
                 handL=(0.44, -0.30, 1.22), handR=(-0.40, -0.20, 1.30), curlL=0.9, curlR=0.9)),
        (0.44, P(MONSTER, hips=(0.05, 0.03, 0.88), pelvis=(10, 4, -4), spine=(30, -4, 6), head=(16, -6, 0),
                 footR=(-0.21, -0.27, 0.30, 0, -18, 0), kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0),
                 handL=(0.44, -0.30, 1.20), handR=(-0.40, -0.22, 1.28), curlL=0.9, curlR=0.9)),
        (0.50, P(MONSTER, hips=(-0.03, -0.03, 0.79), pelvis=(20, -4, 3), spine=(42, 4, -3), head=(14, 0, 0),
                 footR=(-0.21, -0.30, 0.0, 0, -18, 0), kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0),
                 handL=(0.32, -0.36, 1.14), handR=(-0.32, -0.38, 1.12), curlL=0.9, curlR=0.9)),
        (0.64, P(MONSTER, hips=(-0.03, -0.03, 0.775), pelvis=(21, -4, 3), spine=(44, 4, -3), head=(12, 0, 0),
                 footR=(-0.21, -0.30, 0.0, 0, -18, 0), kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0),
                 handL=(0.31, -0.37, 1.13), handR=(-0.31, -0.38, 1.11), curlL=0.7, curlR=0.7)),
        (0.84, P(MONSTER, hips=(-0.01, 0.02, 0.84), footR=tw(MR, y=-0.12, z=0.05, pitch=10),
                 kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0))),
        (1.00, P(MONSTER, kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0))),
    ]
    k[0] = (0.00, P(MONSTER, kneeR=(-0.25, -1.0, 0.5), kneeL=(0.2, -1.0, 0.0)))
    return Clip('m_stomp', 1.00, keys=k, props='none', lag={'head': 0.03, 'hand': 0.04}, nstrip=8, bounds=1.4,
                grounded=False, events={'hit': [0.47, 0.58], 'impact': 0.50, 'cancel': 0.78, 'steps': [[0.50, 'R'], [0.94, 'R']]})


def _mroar_post(t, pz):
    e = smooth((t - 0.66) / 0.12) * (1.0 - smooth((t - 1.32) / 0.2))
    if e > 1e-3:
        s1, s2 = math.sin(TAU * 10.0 * t), math.sin(TAU * 12.3 * t + 1.0)
        hd = pz['head']
        pz['head'] = (hd[0] + 2.2 * e * s1, hd[1] + 1.5 * e * s2, hd[2])
        sp = pz['spine']
        pz['spine'] = (sp[0] + 0.8 * e * s2, sp[1], sp[2])


def m_roar():
    """Gathers low, then roars: chest thrown open, arms wide and back, head thrust up and forward."""
    wide = dict(handL=(0.60, 0.06, 1.14), poleL=(0.5, 0.8, 0.0), handR=(-0.60, 0.06, 1.14), poleR=(-0.5, 0.8, 0.0),
                curlL=0.3, curlR=0.3, twistL=50.0, twistR=50.0, wristL=(-25.0, 0.0), wristR=(-25.0, 0.0),
                clavL=(4, -10), clavR=(4, -10))
    k = [
        (0.00, P(MONSTER)),
        (0.36, P(MONSTER, hips=(0.0, 0.08, 0.78), pelvis=(22, 0, 0), spine=(48, 0, 0), head=(28, 0, 0), hstab=0.6,
                 handL=(0.20, -0.36, 1.12), handR=(-0.20, -0.36, 1.12), curlL=1.0, curlR=1.0)),
        (0.66, P(MONSTER, hips=(0.0, -0.02, 0.88), pelvis=(8, 0, 0), spine=(-6, 0, 0), head=(-26, 0, 0), hstab=0.8,
                 footL=tw(ML, x=0.22), footR=tw(MR, x=-0.22), **wide)),
        (1.32, P(MONSTER, hips=(0.0, -0.03, 0.87), pelvis=(9, 0, 0), spine=(-8, 0, 0), head=(-28, 0, 0), hstab=0.8,
                 footL=tw(ML, x=0.22), footR=tw(MR, x=-0.22), **wide)),
        (1.80, P(MONSTER)),
    ]
    return Clip('m_roar', 1.80, keys=k, props='none', post=_mroar_post, nstrip=8, bounds=1.4,
                events={'release': 0.62, 'cancel': 1.45})


def clips():
    return [Clip('m_idle', 2.5, loop=True, fn=m_idle_fn, props='none', nstrip=4, bounds=1.3),
            Clip('m_walk', 1.3, loop=True, fn=m_walk_fn, props='none', speed=1.2, view='right', nstrip=12, bounds=1.3,
                 events={'steps': G_MWALK.steps()}),
            Clip('m_run', 0.75, loop=True, fn=m_run_fn, props='none', speed=4.0, view='right', nstrip=12, bounds=1.3,
                 events={'steps': G_MRUN.steps()}, grounded=False),
            m_swipe('R'), m_swipe('L'), m_smash(), m_stomp(), m_roar(),
            Clip('m_charge', 0.6, loop=True, fn=m_charge_fn, props='none', speed=5.5, view='right', nstrip=12,
                 bounds=1.3, events={'steps': G_MCHARGE.steps()}, grounded=False)]
