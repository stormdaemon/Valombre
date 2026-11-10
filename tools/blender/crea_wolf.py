"""VALOMBRE creature: WOLF (wolves, dire wolves, snow wolves, giant boss wolf).
Builds the model + rig (crea_wolf_model.py), bakes the 9 animation clips, exports
assets/models/creatures/wolf.glb + wolf.json and renders the preview sheets tools/previews/crea_wolf_*.png.

  blender -b --factory-startup -P tools/blender/crea_wolf.py                 (everything + export)
  blender ... -P tools/blender/crea_wolf.py -- model                         (model sheets only)
  blender ... -P tools/blender/crea_wolf.py -- nomodel clips=walk,run        (only these strips, no export)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crea_common import *
from crea_wolf_model import *

ARGS = args_after_dashes()
BOUNDS = (V((-0.3, -1.05, -0.02)), V((0.3, 0.80, 1.15)))
HEAD_BOUNDS = (V((-0.2, -1.0, 0.62)), V((0.2, -0.45, 1.12)))
V34 = (-0.6, 0.7, -0.35)            # 3/4 front-left view
PI2 = 2 * math.pi

# ----------------------------------------------------------------------------- pose solver
RIG = None
LEGS = {}
LEGKEYS = ('FL', 'FR', 'HL', 'HR')
K_META = {'F': 1.0, 'H': 0.85}      # how much the metacarpus / metatarsus follows the leg line
K_COMP = {'F': 0.0, 'H': 1.3}       # extra forward tilt of the metatarsus when the leg is compressed
K_SCAP = 0.22                       # scapula swing as a fraction of the fore leg swing


def setup_solver(rig):
    global RIG
    RIG = rig
    for s in ('L', 'R'):
        LEGS['F' + s] = PlanarLeg(rig, ['uarm_' + s, 'farm_' + s, 'fmeta_' + s, 'fpaw_' + s], 'x')
        LEGS['H' + s] = PlanarLeg(rig, ['thigh_' + s, 'shin_' + s, 'hmeta_' + s, 'hpaw_' + s], 'x')


def leg(d=(0, 0, 0), p=0.0, m=0.0, b=(0, 0, 0), mix=0.0, scap=None, floor=None):
    """d: world offset of the toe tip from rest. p: paw pitch (deg, + = heel up / toes down).
    m: extra metacarpus / metatarsus angle (deg, + = swings forward). b / mix: target given in BODY
    space (offset carried by chest / hips), mix 0 = world target, 1 = body target."""
    return dict(d=d, p=p, m=m, b=b, mix=mix, scap=scap, floor=floor)


def P0():
    return dict(hip=(0.0, 0.0, 0.0), pitch=0.0, yaw=0.0, roll=0.0, chest_dz=None,
                sp=(0.0, 0.0, 0.0), spy=(0.0, 0.0, 0.0), spr=(0.0, 0.0, 0.0),
                neck=(0.0, 0.0), necky=(0.0, 0.0), head=(0.0, 0.0, 0.0), headw=None, jaw=0.0,
                ear=(0.0, 0.0), earo=(0.0, 0.0), tail=(0.0, 0.0, 0.0, 0.0), taily=(0.0, 0.0, 0.0, 0.0), tailw=0.0,
                FL=leg(), FR=leg(), HL=leg(), HR=leg())


def leg_target(pose, k, lp):
    L = LEGS[k]
    par = 'chest' if k[0] == 'F' else 'hips'
    tip = L.tip0 + V(lp['d'])
    zref = ZA
    if lp['mix'] > 0:
        tb = pose.carry(par, L.tip0 + V(lp['b']))
        tip = tip.lerp(tb, lp['mix'])
        zref = ZA.lerp(pose.carry_dir(par, ZA), lp['mix']).normalized()
    if lp['floor'] is not None:
        tip.z = max(tip.z, lp['floor'])
    return tip, zref


def solve(P):
    """params -> Pose (local bone rotations + hips location)."""
    pose = Pose(RIG)
    pose.move('hips', P['hip'])

    def set_body(pt):
        pose.delta('hips', RZ(P['yaw']) @ RX(-pt) @ RY(P['roll']))
        pose.delta('tail1', RZ(P['taily'][0]) @ RX(P['tail'][0] + pt * P['tailw']))
    pitch = P['pitch']
    for i, b in enumerate(('spine1', 'spine2', 'chest')):
        pose.delta(b, RZ(P['spy'][i]) @ RX(P['sp'][i]) @ RY(P['spr'][i]))
    pose.delta('neck1', RZ(P['necky'][0]) @ RX(-P['neck'][0]))
    pose.delta('neck2', RZ(P['necky'][1]) @ RX(-P['neck'][1]))
    hpi, hya, hro = P['head']
    pose.delta('head', RZ(hya) @ RX(-hpi) @ RY(hro))
    pose.delta('jaw', RX(P['jaw']))
    pose.delta('ear_L', RX(-P['ear'][0]) @ RY(P['earo'][0]))
    pose.delta('ear_R', RX(-P['ear'][1]) @ RY(-P['earo'][1]))
    for i in range(1, 4):
        pose.delta('tail%d' % (i + 1), RZ(P['taily'][i]) @ RX(P['tail'][i]))
    set_body(pitch)
    pose.fk()
    if P['chest_dz'] is not None:                       # find the hips pitch that puts the withers at a height
        for _ in range(3):
            w = pose.carry('chest', WITHERS)
            err = (WITHERS.z + P['chest_dz']) - w.z
            pitch += math.degrees(math.asin(clamp(err / 0.66, -0.5, 0.5)))
            set_body(pitch)
            pose.fk()
    if P['headw'] is not None:                          # head orientation given in world space (heading kept)
        hpi, hya, hro = P['headw']
        Q = RZ(P['yaw'] + hya) @ RX(-hpi) @ RY(hro)
        pose.set_world_rot('head', (Q.to_matrix() @ RIG.rest_rot['head']))
    for k in ('FL', 'FR'):                              # the scapula follows the fore leg
        L, lp = LEGS[k], P[k]
        sc = lp['scap']
        if sc is None:
            tip, zref = leg_target(pose, k, lp)
            beta, _ = L.beta(pose, tip, pose.carry_dir('chest', XA), zref)
            sc = math.degrees(beta - L.beta0) * K_SCAP
        pose.delta('scap_' + k[1], RX(-sc))
    pose.fk()
    for k in LEGKEYS:
        L, lp = LEGS[k], P[k]
        par = 'chest' if k[0] == 'F' else 'hips'
        tip, zref = leg_target(pose, k, lp)
        xref = pose.carry_dir(par, XA)
        beta, dist = L.beta(pose, tip, xref, zref)
        th3 = L.th0[2] + K_META[k[0]] * (beta - L.beta0) + rad(lp['m']) + K_COMP[k[0]] * max(0.0, (L.len0 - dist) / L.len0)
        th4 = L.th0[3] - rad(lp['p'])
        L.solve(pose, tip, [th3, th4], xref, zref)
    pose.fk()
    return pose


# ----------------------------------------------------------------------------- gait helpers
def gait_leg(f, duty, S, lift, y0=0.0, toe_off=38.0, swing_pitch=50.0, meta_flex=-30.0, x=0.0, heel=0.5, zskew=0.85, vmatch=1.0):
    """One leg of an in-place gait. f = phase in [0,1), 0 = touch-down. The toe tip slides back by S during
    the stance (ground speed), then swings forward on an arc. Returns a leg() dict."""
    if f < duty:
        s = f / duty
        y = y0 - S / 2 + S * s
        z = 0.0
        pitch = toe_off * clamp((s - heel) / (1 - heel)) ** 1.6
        m = 0.0
    else:
        r = (f - duty) / (1 - duty)
        vel = vmatch * S * (1 - duty) / duty             # ground speed expressed per unit of r
        y = hermite(r, y0 + S / 2, y0 - S / 2, vel, vel)
        z = lift * math.sin(math.pi * r ** zskew) ** 1.2
        pitch = tr(r, [(0, toe_off), (0.28, swing_pitch), (0.78, 6.0), (1.0, 0.0)], 'c')
        m = meta_flex * math.sin(math.pi * r ** 0.6) ** 2       # flexion peaks early, leg re-extends before landing
    return leg(d=(x, y, z), p=pitch, m=m)


def steps_of(phases, T, dur):
    out = []
    for c in range(int(round(dur / T))):
        for k, ph in phases.items():
            out.append(round(((c + ph) * T) % dur, 3))
    return sorted(out)


# ----------------------------------------------------------------------------- clips
CLIPS = {}


def clip(name, dur, loop=False, speed=None, events=None, **kw):
    def deco(fn):
        CLIPS[name] = dict(name=name, dur=dur, loop=loop, fn=fn, speed=speed, events=events or {}, **kw)
        return fn
    return deco


@clip('idle', 3.0, loop=True, events={'sound': 1.0}, views=('left', V34), count=6)
def idle(t):
    P = P0()
    a = PI2 * t / 3.0
    br = math.sin(2 * a)                                # breathing, 2 breaths per loop
    s1, s2 = math.sin(a), math.sin(2 * a)
    P['chest_dz'] = 0.004 * br
    P['hip'] = (0.008 * s1, 0.004 * s2, 0.002 * br)
    P['sp'] = (0.5 * br, 0.5 * br, -0.6 * br)
    P['roll'] = 0.8 * s1
    scan = 15 * s1 + 5 * math.sin(3 * a)                # head scanning left / right
    P['necky'] = (0.22 * scan, 0.28 * scan)
    P['neck'] = (1.5 * s2, 2.0 * s2)
    P['head'] = (3.0 * s2 - 1.0 * (1 - math.cos(a)), 0.5 * scan, 4.0 * s1)
    P['jaw'] = 2.5 * bump(t, 1.9, 2.6)
    P['ear'] = (16 * bump(t, 0.85, 1.10) + 3 * s2, 14 * bump(t, 2.05, 2.30) + 3 * s2)
    P['earo'] = (8 * bump(t, 0.85, 1.10), 8 * bump(t, 2.05, 2.30))
    lag = (0.0, 0.5, 1.0, 1.5)
    P['taily'] = tuple(am * (math.sin(a - lg) + math.sin(lg)) for am, lg in zip((3, 4, 5, 6), lag))
    P['tail'] = (2 * s2, 2 * s2, 1.5 * (math.sin(2 * a - 0.5) + math.sin(0.5)), 1.5 * (math.sin(2 * a - 1.0) + math.sin(1.0)))
    return P


WALK_T, WALK_V, WALK_DUTY = 0.5, 1.8, 0.62
WALK_PH = dict(HL=0.0, FL=0.25, HR=0.5, FR=0.75)       # lateral sequence 4-beat walk: LH, LF, RH, RF


@clip('walk', 1.0, loop=True, speed=WALK_V, events={'steps': steps_of(WALK_PH, WALK_T, 1.0)}, span=0.5, views=('left', V34))
def walk(t):
    ph = t / WALK_T
    P = P0()
    Sd = WALK_V * WALK_DUTY * WALK_T
    for k in LEGKEYS:
        f = frac(ph - WALK_PH[k])
        if k[0] == 'F':
            P[k] = gait_leg(f, WALK_DUTY, Sd, 0.070, y0=-0.035, toe_off=42, swing_pitch=56, meta_flex=-32, heel=0.45)
        else:
            P[k] = gait_leg(f, WALK_DUTY, Sd, 0.045, y0=-0.02, toe_off=32, swing_pitch=30, meta_flex=4, heel=0.55)

    def c2(p0):
        return math.cos(2 * PI2 * (ph - p0))
    s1 = math.sin(PI2 * (ph - 0.12))
    P['chest_dz'] = -0.022 + 0.009 * c2(0.06)           # shoulders highest at fore mid-stance
    P['hip'] = (0.012 * s1, 0.0, -0.020 + 0.009 * c2(0.31))
    P['roll'] = 1.6 * math.sin(PI2 * (ph - 0.30))
    P['yaw'] = 1.2 * math.sin(PI2 * (ph - 0.05))
    bend = 3.5 * math.sin(PI2 * ph)
    P['spy'] = (bend, bend * 0.6, -bend * 0.8)
    P['sp'] = (1.0 * c2(0.2), 0.0, -1.0 * c2(0.2))
    P['neck'] = (-13.0 + 1.5 * c2(0.16), -7.0)
    P['necky'] = (-bend * 0.3, 0.0)
    P['headw'] = (-5.0 + 1.5 * c2(0.22), -P['yaw'], 0.0)
    P['ear'] = (6.0, 6.0)
    P['taily'] = tuple(7.0 * math.sin(PI2 * (ph - 0.15 - 0.09 * i)) for i in range(4))
    P['tail'] = (3.0 + 2.0 * c2(0.4), 2.0, 2.0 * c2(0.55), 2.0 * c2(0.65))
    return P


RUN_T, RUN_V, RUN_DUTY = 0.5, 6.5, 0.20
RUN_PH = dict(HL=0.00, HR=0.09, FR=0.50, FL=0.59)       # rotary gallop: LH, RH, (flight), RF, LF, (flight)


@clip('run', 0.5, loop=True, speed=RUN_V, events={'steps': steps_of(RUN_PH, RUN_T, 0.5)}, views=('left', V34),
      bounds=(V((-0.3, -1.15, -0.02)), V((0.3, 1.0, 1.1))))
def run(t):
    ph = t / RUN_T
    P = P0()
    Sd = RUN_V * RUN_DUTY * RUN_T
    for k in LEGKEYS:
        f = frac(ph - RUN_PH[k])
        if k[0] == 'F':
            P[k] = gait_leg(f, RUN_DUTY, Sd, 0.20, y0=-0.07, toe_off=50, swing_pitch=75, meta_flex=-75, heel=0.35, zskew=0.7, vmatch=0.3)
        else:
            P[k] = gait_leg(f, RUN_DUTY, Sd, 0.15, y0=-0.10, toe_off=48, swing_pitch=55, meta_flex=20, heel=0.4, zskew=0.75, vmatch=0.3)
    fl = math.cos(PI2 * (ph - 0.90))                    # +1 gathered (spine flexed), -1 extended
    P['sp'] = (9.0 * fl, 9.0 * fl, 6.0 * fl)
    P['hip'] = (0.0, -0.035 * fl - 0.02, -0.035 + 0.045 * math.cos(PI2 * (ph - 0.55)))
    P['chest_dz'] = -0.040 + 0.040 * math.cos(PI2 * (ph - 0.12))
    P['neck'] = (-22.0 + 6.0 * math.cos(PI2 * (ph - 0.65)), -10.0)
    P['headw'] = (-4.0 + 3.0 * math.cos(PI2 * (ph - 0.2)), 0.0, 0.0)
    P['ear'] = (30.0, 30.0)
    P['jaw'] = 7.0 + 3.0 * math.cos(PI2 * (ph - 0.3))
    w = [math.cos(PI2 * (ph - 0.25 - 0.1 * i)) for i in range(4)]
    P['tail'] = (40.0 + 5 * w[0], 16.0 + 7 * w[1], 8.0 + 8 * w[2], 4.0 + 8 * w[3])
    P['tailw'] = 1.0
    return P


@clip('bite', 0.7, events={'hit': [0.24, 0.36], 'sound': 0.18}, views=('left', V34))
def bite(t):
    P = P0()
    P['hip'] = (0.0, tr(t, [(0, 0), (0.15, 0.06), (0.27, -0.15, 'i'), (0.38, -0.13), (0.7, 0)]),
                tr(t, [(0, 0), (0.15, -0.03), (0.27, -0.05), (0.40, -0.04), (0.7, 0)]))
    P['chest_dz'] = tr(t, [(0, 0), (0.15, -0.05), (0.27, -0.10), (0.40, -0.07), (0.7, 0)])
    P['sp'] = tuple(tr(t, [(0, (0, 0, 0)), (0.15, (4, 4, 3)), (0.27, (-3, -3, -2), 'i'), (0.42, (-1, -1, -1)), (0.7, (0, 0, 0))]))
    P['neck'] = tuple(tr(t, [(0, (0, 0)), (0.15, (9, 7)), (0.27, (-32, -16), 'i'), (0.40, (-26, -12)), (0.7, (0, 0))]))
    shake = tr(t, [(0.30, 0), (0.35, 10), (0.41, -9), (0.47, 5), (0.55, 0)], 'c')
    P['headw'] = (tr(t, [(0, 0), (0.15, 5), (0.24, 14), (0.30, -6, 'i'), (0.44, -4), (0.7, 0)]), shake, shake * 0.6)
    P['jaw'] = tr(t, [(0, 0), (0.10, 10), (0.21, 42), (0.27, 38), (0.31, 2, 'I'), (0.46, 3), (0.7, 0)])
    e = tr(t, [(0, 0), (0.12, 30), (0.45, 30), (0.7, 0)])
    P['ear'] = (e, e)
    k = bump(t, 0.12, 0.62)
    P['tail'] = (18 * k, 8 * k, 4 * k, 0.0)
    for kk in ('HL', 'HR'):
        P[kk] = leg(p=16 * bump(t, 0.16, 0.6))
    return P


@clip('lunge', 1.1, events={'hit': [0.50, 0.72], 'impact': 0.70, 'sound': 0.36},
      views=('left', V34), bounds=(V((-0.3, -1.25, -0.02)), V((0.3, 0.85, 1.5))))
def lunge(t):
    P = P0()
    P['hip'] = (0.0, tr(t, [(0, 0), (0.30, 0.09), (0.46, -0.10), (0.70, -0.05), (0.82, -0.02), (1.1, 0)]),
                tr(t, [(0, 0), (0.30, -0.13), (0.40, -0.03, 'i'), (0.46, 0.10, 'l'), (0.56, 0.24, 'o'), (0.70, 0.12, 'i'),
                       (0.79, -0.07, 'l'), (0.92, -0.03), (1.1, 0)]))
    P['chest_dz'] = tr(t, [(0, 0), (0.30, -0.17), (0.40, 0.12, 'i'), (0.46, 0.27, 'l'), (0.54, 0.36, 'o'), (0.65, 0.12, 'i'),
                           (0.72, -0.13, 'l'), (0.86, -0.05), (1.1, 0)])
    P['sp'] = tuple(tr(t, [(0, (0, 0, 0)), (0.30, (8, 8, 6)), (0.46, (-6, -6, -5)), (0.58, (-5, -5, -4)), (0.76, (7, 7, 5)), (1.1, (0, 0, 0))]))
    P['neck'] = tuple(tr(t, [(0, (0, 0)), (0.30, (-22, -10)), (0.46, (-28, -14)), (0.66, (-26, -12)), (0.80, (-12, -6)), (1.1, (0, 0))]))
    P['headw'] = (tr(t, [(0, 0), (0.30, -6), (0.46, 12), (0.62, 10), (0.68, -8, 'i'), (0.84, -4), (1.1, 0)]), 0.0, 0.0)
    P['jaw'] = tr(t, [(0, 0), (0.30, 6), (0.44, 40), (0.63, 44), (0.68, 3, 'I'), (0.85, 3), (1.1, 0)])
    e = tr(t, [(0, 0), (0.25, 32), (0.80, 32), (1.1, 0)])
    P['ear'] = (e, e)
    P['tail'] = tuple(tr(t, [(0, (0, 0, 0, 0)), (0.30, (-10, -6, 0, 0)), (0.50, (48, 20, 8, 0)), (0.72, (40, 20, 10, 5)), (1.1, (0, 0, 0, 0))]))
    fm = tr(t, [(0, 0), (0.36, 0), (0.43, 1), (0.63, 1), (0.70, 0), (1.1, 0)], 'l')
    fb = tuple(tr(t, [(0.36, (0, -0.05, 0.05)), (0.46, (0, -0.30, 0.22)), (0.56, (0, -0.50, 0.26)), (0.66, (0, -0.42, 0.10)), (0.72, (0, -0.2, 0.0))], 'c'))
    fp = tr(t, [(0, 0), (0.36, 0), (0.46, -30), (0.62, -42), (0.70, 0), (1.1, 0)])
    hm = tr(t, [(0, 0), (0.44, 0), (0.50, 1), (0.72, 1), (0.79, 0), (1.1, 0)], 'l')
    hb = tuple(tr(t, [(0.44, (0, 0.10, 0.0)), (0.54, (0, 0.34, 0.06)), (0.64, (0, 0.20, 0.14)), (0.74, (0, -0.06, 0.12)), (0.80, (0, 0, 0))], 'c'))
    hpch = tr(t, [(0, 0), (0.30, 0), (0.44, 50, 'i'), (0.56, 62), (0.72, 20), (0.79, 0), (1.1, 0)])
    for kk in ('FL', 'FR'):
        P[kk] = leg(p=fp, b=fb, mix=fm, m=-10 * fm)
    for kk in ('HL', 'HR'):
        P[kk] = leg(p=hpch, b=hb, mix=hm)
    return P


@clip('swipe', 0.9, events={'hit': [0.30, 0.46], 'sound': 0.27}, views=('left', (0.55, 0.75, -0.38)))
def swipe(t):
    P = P0()
    yaw = tr(t, [(0, 0), (0.26, -8), (0.44, 13, 'i'), (0.56, 11), (0.9, 0)])
    P['yaw'] = yaw
    P['chest_dz'] = tr(t, [(0, 0), (0.26, 0.01), (0.42, -0.08), (0.56, -0.09), (0.9, 0)])
    P['hip'] = (tr(t, [(0, 0), (0.26, 0.03), (0.44, -0.03), (0.9, 0)]), tr(t, [(0, 0), (0.26, 0.05), (0.44, -0.05), (0.9, 0)]),
                tr(t, [(0, 0), (0.26, -0.07), (0.5, -0.05), (0.9, 0)]))
    b = tr(t, [(0, 0), (0.26, -4), (0.44, 6, 'i'), (0.58, 5), (0.9, 0)])
    P['spy'] = (b, b, b)
    tw = tr(t, [(0, 0), (0.26, 6), (0.44, -9, 'i'), (0.58, -6), (0.9, 0)])
    P['spr'] = (0.0, tw * 0.5, tw)
    P['neck'] = tuple(tr(t, [(0, (0, 0)), (0.26, (4, 2)), (0.44, (-16, -8)), (0.9, (0, 0))]))
    P['headw'] = (tr(t, [(0, 0), (0.26, 2), (0.44, -8), (0.9, 0)]), -0.5 * yaw, 0.0)
    P['jaw'] = tr(t, [(0, 0), (0.2, 16), (0.5, 20), (0.9, 0)])
    e = tr(t, [(0, 0), (0.15, 30), (0.6, 30), (0.9, 0)])
    P['ear'] = (e, e)
    P['taily'] = (-yaw * 0.8, -yaw * 0.6, -yaw * 0.4, -yaw * 0.3)
    P['tail'] = (12 * bump(t, 0.1, 0.8),) * 2 + (0.0, 0.0)
    d = tr(t, [(0, (0, 0, 0)), (0.10, (-0.03, 0.02, 0.10)), (0.26, (-0.26, 0.04, 0.44)), (0.34, (-0.14, -0.34, 0.42), 'l'),
               (0.44, (0.28, -0.28, 0.22), 'l'), (0.54, (0.24, -0.10, 0.04)), (0.68, (0.12, -0.04, 0.10)), (0.80, (0, 0, 0)), (0.9, (0, 0, 0))], 'c')
    P['FR'] = leg(d=(d[0], d[1], max(d[2], 0.0)),
                  p=tr(t, [(0, 0), (0.12, 35), (0.26, 20), (0.36, -35), (0.46, -25), (0.56, 10), (0.68, 25), (0.80, 0)]),
                  m=tr(t, [(0, 0), (0.26, -40), (0.36, 10), (0.46, 0), (0.68, -20), (0.80, 0)]))
    return P


@clip('howl', 2.4, events={'sound': 0.45}, views=('left', V34), count=6, bounds=(V((-0.3, -1.05, -0.02)), V((0.3, 0.85, 1.35))))
def howl(t):
    P = P0()
    k = tr(t, [(0, 0), (0.55, 1), (1.85, 1), (2.4, 0)])
    vib = math.sin(PI2 * 2.5 * t) * k
    P['hip'] = (0.0, 0.06 * k, -0.12 * k)
    P['chest_dz'] = -0.02 * k + 0.004 * vib
    P['sp'] = (-3 * k, -3 * k, -4 * k)
    P['neck'] = (20 * k, 18 * k)
    P['headw'] = (64 * k + 1.5 * vib, 5 * math.sin(PI2 * t / 2.4) * k, 0.0)
    P['jaw'] = tr(t, [(0, 0), (0.35, 3), (0.65, 24), (1.7, 20), (1.95, 5), (2.4, 0)]) + 1.5 * vib
    P['ear'] = (34 * k, 34 * k)
    P['tail'] = (12 * k, 8 * k, 4 * k, 2 * k)
    return P


@clip('hit', 0.4, events={'sound': 0.03}, views=('left', V34), count=6)
def hit(t):
    P = P0()
    k = tr(t, [(0, 0), (0.09, 1, 'o'), (0.22, 0.45), (0.4, 0)])
    P['hip'] = (0.02 * k, 0.07 * k, -0.06 * k)
    P['chest_dz'] = -0.10 * k
    P['yaw'] = -6 * k
    P['roll'] = 4 * k
    P['sp'] = (4 * k, 4 * k, 3 * k)
    P['neck'] = (-14 * k, -8 * k)
    P['necky'] = (-10 * k, -8 * k)
    P['head'] = (-10 * k, -14 * k, 8 * k)
    P['jaw'] = tr(t, [(0, 0), (0.06, 24), (0.18, 9), (0.4, 0)])
    P['ear'] = (38 * k, 38 * k)
    P['tail'] = (-10 * k, -12 * k, -8 * k, -4 * k)
    w = bump(t, 0.02, 0.32)
    P['FL'] = leg(d=(0.0, 0.05 * k, 0.08 * w), p=30 * w, m=-20 * w)
    return P


@clip('death', 1.6, events={'impact': 0.85, 'sound': 0.08}, views=('left', (-0.5, 0.6, -0.6)),
      bounds=(V((-0.7, -1.05, -0.02)), V((0.7, 0.80, 1.15))))
def death(t):
    P = P0()
    k = tr(t, [(0, 0), (0.25, 0.12), (0.5, 0.45, 'i'), (0.85, 1.0, 'i'), (1.6, 1.0)])
    P['hip'] = (tr(t, [(0, 0), (0.5, -0.03), (0.85, -0.10), (1.6, -0.10)]), 0.0,
                tr(t, [(0, 0), (0.22, -0.10), (0.5, -0.30, 'i'), (0.85, -0.545, 'i'), (0.95, -0.528), (1.08, -0.545), (1.6, -0.545)]))
    P['chest_dz'] = tr(t, [(0, 0), (0.22, -0.17), (0.5, -0.38), (0.85, -0.625, 'i'), (0.95, -0.595), (1.08, -0.622), (1.6, -0.622)])
    P['roll'] = tr(t, [(0, 0), (0.22, -8), (0.5, -40, 'i'), (0.85, -91, 'i'), (0.95, -85), (1.08, -89), (1.6, -89)])
    P['sp'] = (2 * k, 3 * k, 2 * k)
    P['spy'] = (-2 * k, -2 * k, -3 * k)
    P['neck'] = (-24 * k, -18 * k)
    P['necky'] = (-1 * k, 0.0)
    P['head'] = (tr(t, [(0, 0), (0.2, -12), (0.85, 6), (0.95, 10), (1.1, 6), (1.6, 6)]), 0.0, 0.0)
    P['jaw'] = tr(t, [(0, 0), (0.10, 26), (0.5, 12), (0.9, 16), (1.1, 9), (1.6, 9)])
    P['ear'] = (20 * k, 20 * k)
    P['tail'] = (-6 * k, 4 * k, 6 * k, 6 * k)
    P['taily'] = (-5 * k, -5 * k, -3 * k, -2 * k)
    m = tr(t, [(0, 0), (0.18, 0), (0.5, 1), (1.6, 1)])
    tw = bump(t, 0.9, 1.15)
    P['FR'] = leg(b=(-0.012, -0.06, 0.13), mix=m, p=28 * m, floor=0.035 * m)
    P['FL'] = leg(b=(-0.15, 0.05, 0.16 + 0.03 * tw), mix=m, p=38 * m, m=-14 * m, floor=0.0)
    P['HR'] = leg(b=(-0.012, 0.06, 0.12), mix=m, p=30 * m, floor=0.035 * m)
    P['HL'] = leg(b=(-0.15, -0.08, 0.15 + 0.03 * tw), mix=m, p=40 * m, m=8 * m, floor=0.0)
    return P


# ----------------------------------------------------------------------------- main
def write_meta(mesh, info, mn, mxx):
    clips = {}
    for name, c in CLIPS.items():
        d = {'duration': round(int(round(c['dur'] * FPS)) / FPS, 4), 'loop': bool(c['loop'])}
        if c['speed'] is not None:
            d['speed'] = c['speed']
        d['events'] = c['events']
        clips[name] = d
    meta = {
        'file': 'wolf.glb', 'fps': FPS,
        'description': 'Grey wolf, rigged + skinned, 9 in-place clips. Scale 1-1.3 for wolves, 2.3 for the giant boss.',
        'size': {'length': round(float(mxx[1] - mn[1]), 3), 'height': round(float(mxx[2]), 3), 'radius': 0.45,
                 'width': round(float(mxx[0] - mn[0]), 3), 'shoulder_height': 0.80, 'nose_to_rump': 1.47},
        'triangles': info['summary']['tris'],
        'materials': {'M_fur': 'coat (COLOR_0 = neutral light-grey pattern 0.5-1.0 x baked AO, to be multiplied by the variant tint)',
                      'M_bone': 'teeth (ivory vertex colour) and claws (dark vertex colour)',
                      'M_mouth': 'NEW: dark wet gums / palate / tongue, vertex colour = dark red tint',
                      'M_eye_glow': 'eyeballs (vertex colour amber iris, dark pupil); make emissive for corrupted variants'},
        'bones': {'root': 'root', 'hips': 'hips', 'head': 'head', 'jaw': 'jaw', 'chest': 'chest',
                  'spine': ['hips', 'spine1', 'spine2', 'chest', 'neck1', 'neck2', 'head'],
                  'tail': ['tail1', 'tail2', 'tail3', 'tail4'], 'ears': ['ear_L', 'ear_R'],
                  'paws': ['fpaw_L', 'fpaw_R', 'hpaw_L', 'hpaw_R']},
        'notes': 'Only bone rotations are animated, plus the location of "hips" (root stays at the origin). '
                 'All clips are in place. One-shots start from and return to the idle pose (= rest pose).',
        'clips': clips,
    }
    with open(os.path.join(CREA_DIR, 'wolf.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print('META', json.dumps(meta['size']))


def main():
    reset_scene()
    rig = build_rig()
    arm = rig.build('wolf_rig')
    setup_solver(rig)
    mesh = build_model(rig, arm)
    print('TRIS', tri_count(mesh), 'VERTS', len(mesh.data.vertices))
    co = eval_verts(mesh)
    size_mn, size_mx = co.min(0), co.max(0)
    if 'nomodel' not in ARGS:
        jaw = arm.pose.bones['jaw']

        def openjaw():
            jaw.rotation_quaternion = Quaternion((1, 0, 0), rad(34))

        def closejaw():
            jaw.rotation_quaternion = Quaternion()
        render_tiles(os.path.join(PREVIEWS, 'crea_wolf_model.png'), [mesh],
                     [('left', None, None), ('front', None, None), ('top', None, None), ('persp', None, None),
                      ('back', None, None), ('persp_back', None, None), ('left', HEAD_BOUNDS, openjaw), ((-0.5, 0.75, -0.25), HEAD_BOUNDS, None),
                      ('front', HEAD_BOUNDS, closejaw)], res=(500, 420), cols=3)
    if 'model' in ARGS:
        return
    p = solve(P0())                                     # sanity: the solver must reproduce the rest pose
    print('REST CHECK (should be ~0): %.2e' % max(abs(1 - abs(q.w)) for q in p.q.values()))
    only = None
    for a in ARGS:
        if a.startswith('clips='):
            only = a[6:].split(',')
    ensure_ground()
    acts = []
    for name, c in CLIPS.items():
        if only and name not in only:
            continue
        act, nfr = bake_clip(arm, rig, name, c['dur'], lambda t, c=c: solve(c['fn'](t)), loop=c['loop'])
        acts.append(act)
        clip_report(name, mesh, nfr)
        if 'nostrip' not in ARGS:
            render_strip(os.path.join(PREVIEWS, 'crea_wolf_%s.png' % name), [mesh], int(nfr * c.get('span', 1.0)),
                         count=c.get('count', 8), loop=c['loop'], views=c.get('views', ('left',)),
                         res=c.get('res', (420, 330)), bounds=c.get('bounds', BOUNDS))
    if only:
        return
    bpy.data.objects.remove(bpy.data.objects['pv_ground'])
    bpy.context.scene.frame_set(0)
    actions_to_nla(arm, acts)
    info = export_glb(os.path.join(CREA_DIR, 'wolf.glb'), [arm, mesh], anims=True)
    print('MESHES', json.dumps(info['meshes']))
    write_meta(mesh, info, size_mn, size_mx)


main()
