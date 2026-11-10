"""VALOMBRE creature: GIANT FOREST SPIDER (giant spiders at scale 0.85-1, boss queen at scale 3.4).
Builds the model + rig (crea_spider_model.py), bakes the 10 animation clips, exports
assets/models/creatures/spider.glb + spider.json and renders tools/previews/crea_spider_*.png.

  blender -b --factory-startup -P tools/blender/crea_spider.py                (everything + export)
  blender ... -P tools/blender/crea_spider.py -- model                        (model sheet only)
  blender ... -P tools/blender/crea_spider.py -- nomodel clips=walk,run       (only these strips, no export)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crea_common import *
from crea_spider_model import *

ARGS = args_after_dashes()
BOUNDS = (V((-1.25, -1.50, -0.02)), V((1.25, 1.05, 1.25)))
SIDE_B = (V((-0.2, -1.55, -0.02)), V((0.2, 1.05, 1.30)))
V34 = (-0.55, 0.70, -0.45)
PI2 = 2 * math.pi

# ----------------------------------------------------------------------------- pose solver
RIG = None
LEGS = {}
REST_R = {}
K_REACH = 0.8                       # tarsus leans outward (rad per metre) when the foot is far from the coxa


def setup_solver(rig):
    global RIG
    RIG = rig
    for k in LEGKEYS:
        nm = 'leg%s' % k[1]
        L = PlanarLeg(rig, [nm + 'a_' + k[0], nm + 'b_' + k[0], nm + 'c_' + k[0]], 'radial')
        LEGS[k] = L
        h = L.tip0 - L.S0
        REST_R[k] = V((h.x, h.y, 0)).length


def sleg(d=(0, 0, 0), b=(0, 0, 0), mix=0.0, t=0.0, floor=None):
    """d: world offset of the foot tip from rest. b / mix: BODY-space offset and its blend (1 = body space).
    t: extra tarsus angle (deg, + = leans outward)."""
    return dict(d=d, b=b, mix=mix, t=t, floor=floor)


def P0():
    P = dict(pos=(0.0, 0.0, 0.0), pitch=0.0, yaw=0.0, roll=0.0, abd=(0.0, 0.0), chel=(0.0, 0.0), fang=(0.0, 0.0),
             palp={'L': (0.0, 0.0, 0.0), 'R': (0.0, 0.0, 0.0)})
    for k in LEGKEYS:
        P[k] = sleg()
    return P


def solve(P):
    pose = Pose(RIG)
    pose.move('body', P['pos'])
    pose.delta('body', RZ(P['yaw']) @ RX(-P['pitch']) @ RY(P['roll']))
    pose.delta('abdomen', RZ(P['abd'][1]) @ RX(P['abd'][0]))
    for sfx, sx in (('_L', 1), ('_R', -1)):
        pose.delta('chel' + sfx, RX(-P['chel'][0]) @ RY(-sx * P['chel'][1]))
        pose.delta('fang' + sfx, RX(-P['fang'][0]) @ RY(-sx * P['fang'][1]))
        a, b, c = P['palp'][sfx[1]]
        pose.delta('palp1' + sfx, RZ(sx * b) @ RX(-a))
        pose.delta('palp2' + sfx, RX(-c))
    pose.fk()
    for k in LEGKEYS:
        L, lp = LEGS[k], P[k]
        tip = L.tip0 + V(lp['d'])
        zref = ZA
        if lp['mix'] > 0:
            tb = pose.carry('body', L.tip0 + V(lp['b']))
            tip = tip.lerp(tb, lp['mix'])
            zb = pose.carry_dir('body', ZA)
            zref = ZA.lerp(zb, lp['mix'])
            zref = zb if zref.length < 0.05 else zref.normalized()
        if lp['floor'] is not None:
            tip.z = max(tip.z, lp['floor'])
        h = tip - pose.head(L.bones[0])
        r = (h - zref * h.dot(zref)).length
        th = clamp(L.th0[2] + K_REACH * (r - REST_R[k]) + rad(lp['t']), rad(-135), rad(80))
        L.solve(pose, tip, [th], XA, zref)
    pose.fk()
    return pose


# ----------------------------------------------------------------------------- gait
GROUP = dict(L1=0.0, R2=0.0, L3=0.0, R4=0.0, R1=0.5, L2=0.5, R3=0.5, L4=0.5)      # alternating tetrapods
LAG = {'1': 0.10, '2': 0.06, '3': 0.03, '4': 0.0}                                   # small rear-to-front wave
Y0 = {'1': 0.10, '2': 0.03, '3': -0.03, '4': -0.12}                                 # stance centre offsets


def gait(P, ph, duty, Sd, lift, vmatch=0.6):
    for k in LEGKEYS:
        f = frac(ph - GROUP[k] - LAG[k[1]])
        y0 = Y0[k[1]]
        if f < duty:
            s = f / duty
            P[k] = sleg(d=(0.0, y0 - Sd / 2 + Sd * s, 0.0))
        else:
            r = (f - duty) / (1 - duty)
            vel = vmatch * Sd * (1 - duty) / duty
            y = hermite(r, y0 + Sd / 2, y0 - Sd / 2, vel, vel)
            z = lift * math.sin(math.pi * r ** 0.85) ** 1.1
            sx = 1.0 if k[0] == 'L' else -1.0
            P[k] = sleg(d=(0.05 * sx * math.sin(math.pi * r), y, z), t=16.0 * math.sin(math.pi * r))
    return P


def beats(T, dur, duty):
    """touch-down times of the two leg groups (centre of each little wave)."""
    out = []
    for c in range(int(round(dur / T))):
        for g in (0.0, 0.5):
            out.append(round(((c + g + 0.05) * T) % dur, 3))
    return sorted(out)


# ----------------------------------------------------------------------------- clips
CLIPS = {}


def clip(name, dur, loop=False, speed=None, events=None, **kw):
    def deco(fn):
        CLIPS[name] = dict(name=name, dur=dur, loop=loop, fn=fn, speed=speed, events=events or {}, **kw)
        return fn
    return deco


def front_legs(P, keys, dL, t=0.0, b=None, mix=0.0):
    """same motion on both sides (x mirrored)."""
    for k in keys:
        sx = 1.0 if k[0] == 'L' else -1.0
        bb = (0, 0, 0) if b is None else (b[0] * sx, b[1], b[2])
        P[k] = sleg(d=(dL[0] * sx, dL[1], max(dL[2], 0.0)), t=t, b=bb, mix=mix)


@clip('idle', 2.5, loop=True, events={'sound': 1.2}, views=('left', V34), count=6)
def idle(t):
    P = P0()
    a = PI2 * t / 2.5
    s1, s2 = math.sin(a), math.sin(2 * a)
    P['pos'] = (0.014 * s2, 0.012 * s1, 0.032 * s1)
    P['pitch'] = 1.5 * s1
    P['roll'] = 1.0 * s2
    P['abd'] = (3.0 * (math.sin(a - 0.7) + math.sin(0.7)), 2.0 * s2)
    wl = bump(t, 0.35, 0.65) + bump(t, 1.55, 1.80)
    wr = bump(t, 0.90, 1.20) + bump(t, 2.00, 2.25)
    P['palp'] = {'L': (16 * wl, 8 * wl, -22 * wl), 'R': (16 * wr, 8 * wr, -22 * wr)}
    c = bump(t, 1.0, 1.7)
    P['chel'] = (5 * c, 3 * c)
    P['fang'] = (10 * c, 0.0)
    w = bump(t, 1.15, 1.60) + 0.5 * bump(t, 1.62, 1.92)          # a front leg lifts and taps
    P['L1'] = sleg(d=(0.04 * w, -0.10 * w, 0.26 * w), t=14 * w)
    return P


WALK_T, WALK_V, WALK_DUTY = 0.4, 2.0, 0.55


@clip('walk', 0.8, loop=True, speed=WALK_V, events={'steps': beats(WALK_T, 0.8, WALK_DUTY)}, span=0.5, views=('top', 'left'), count=6)
def walk(t):
    ph = t / WALK_T
    P = gait(P0(), ph, WALK_DUTY, WALK_V * WALK_DUTY * WALK_T, 0.17)
    c2 = math.cos(2 * PI2 * (ph - 0.12))
    s1 = math.sin(PI2 * (ph - 0.1))
    P['pos'] = (0.010 * s1, 0.0, -0.015 + 0.012 * c2)
    P['roll'] = 1.6 * s1
    P['yaw'] = 1.4 * math.sin(PI2 * (ph + 0.05))
    P['pitch'] = 0.8 * c2
    P['abd'] = (2.5 * math.cos(2 * PI2 * (ph - 0.30)), -2.0 * math.sin(PI2 * (ph - 0.05)))
    wl, wr = math.sin(PI2 * ph), math.sin(PI2 * (ph + 0.5))
    P['palp'] = {'L': (6 + 6 * wl, 3, -8 * wl), 'R': (6 + 6 * wr, 3, -8 * wr)}
    return P


RUN_T, RUN_V, RUN_DUTY = 14 / 30 / 2, 5.0, 0.5


@clip('run', 14 / 30, loop=True, speed=RUN_V, events={'steps': beats(RUN_T, 14 / 30, RUN_DUTY)}, span=0.5, views=('top', 'left'), count=6)
def run(t):
    ph = t / RUN_T
    P = gait(P0(), ph, RUN_DUTY, RUN_V * RUN_DUTY * RUN_T, 0.22, vmatch=0.4)
    c2 = math.cos(2 * PI2 * (ph - 0.12))
    s1 = math.sin(PI2 * (ph - 0.1))
    P['pos'] = (0.012 * s1, 0.0, -0.05 + 0.014 * c2)
    P['roll'] = 2.2 * s1
    P['yaw'] = 2.0 * math.sin(PI2 * (ph + 0.05))
    P['pitch'] = -3.0 + 1.0 * c2
    P['abd'] = (6.0 + 4.0 * math.cos(2 * PI2 * (ph - 0.30)), -3.0 * math.sin(PI2 * (ph - 0.05)))
    P['chel'] = (10.0, 6.0)
    P['fang'] = (20.0, 0.0)
    P['palp'] = {'L': (14, 8, -6), 'R': (14, 8, -6)}
    return P


@clip('bite', 0.7, events={'hit': [0.29, 0.42], 'sound': 0.22}, views=('left', V34))
def bite(t):
    P = P0()
    P['pitch'] = tr(t, [(0, 0), (0.22, 20), (0.33, -10, 'i'), (0.43, -8), (0.7, 0)])
    P['pos'] = (0.0, tr(t, [(0, 0), (0.22, 0.10), (0.33, -0.26, 'i'), (0.43, -0.24), (0.7, 0)]),
                tr(t, [(0, 0), (0.22, 0.05), (0.33, -0.10), (0.43, -0.09), (0.7, 0)]))
    P['abd'] = (tr(t, [(0, 0), (0.22, 12), (0.33, -6), (0.5, 3), (0.7, 0)]), 0.0)
    P['chel'] = (tr(t, [(0, 0), (0.20, 38), (0.31, 4, 'i'), (0.45, 10), (0.7, 0)]), tr(t, [(0, 0), (0.20, 20), (0.33, 2), (0.7, 0)]))
    P['fang'] = (tr(t, [(0, 0), (0.18, 55), (0.29, 62), (0.34, -8, 'I'), (0.46, 8), (0.7, 0)]), tr(t, [(0, 0), (0.2, 14), (0.34, 0), (0.7, 0)]))
    pa = tr(t, [(0, (0, 0, 0)), (0.2, (28, 22, -10)), (0.34, (-6, 4, 20)), (0.7, (0, 0, 0))])
    P['palp'] = {'L': tuple(pa), 'R': tuple(pa)}
    d1 = tr(t, [(0, (0, 0, 0)), (0.10, (0.05, 0.0, 0.25)), (0.22, (0.16, -0.02, 0.66)), (0.33, (0.02, -0.24, 0.10), 'i'), (0.40, (0.0, -0.22, 0.0)),
                (0.46, (0.0, -0.22, 0.0)), (0.56, (0.0, -0.10, 0.12)), (0.66, (0, 0, 0)), (0.7, (0, 0, 0))], 'c')
    front_legs(P, ('L1', 'R1'), d1, t=tr(t, [(0, 0), (0.22, 30), (0.34, 0), (0.7, 0)]))
    return P


@clip('leap', 1.2, events={'hit': [0.72, 0.94], 'impact': 0.84, 'sound': 0.38}, views=('left', V34),
      bounds=(V((-1.3, -1.6, -0.02)), V((1.3, 1.1, 1.9))), sbounds=(V((-0.2, -1.6, -0.02)), V((0.2, 1.1, 1.9))))
def leap(t):
    P = P0()
    P['pos'] = (0.0, tr(t, [(0, 0), (0.32, 0.10), (0.46, -0.12), (0.82, -0.06), (1.2, 0)]),
                tr(t, [(0, 0), (0.32, -0.20), (0.40, -0.06, 'i'), (0.46, 0.16, 'l'), (0.62, 0.55, 'o'), (0.78, 0.18, 'i'), (0.87, -0.20, 'l'),
                       (1.00, -0.06), (1.2, 0)]))
    P['pitch'] = tr(t, [(0, 0), (0.32, -6), (0.46, 16), (0.62, 6), (0.80, -10), (0.92, -4), (1.2, 0)])
    P['abd'] = (tr(t, [(0, 0), (0.32, -6), (0.5, 14), (0.78, 10), (0.88, -10), (1.0, 2), (1.2, 0)]), 0.0)
    o = tr(t, [(0, 0), (0.36, 0), (0.5, 1), (0.8, 1), (0.88, 0), (1.2, 0)])
    P['chel'] = (34 * o, 20 * o)
    P['fang'] = (tr(t, [(0, 0), (0.36, 0), (0.5, 58), (0.80, 60), (0.86, -6, 'I'), (1.0, 6), (1.2, 0)]), 12 * o)
    P['palp'] = {'L': (26 * o, 20 * o, -8 * o), 'R': (26 * o, 20 * o, -8 * o)}
    m = tr(t, [(0, 0), (0.40, 0), (0.47, 1), (0.76, 1), (0.84, 0), (1.2, 0)], 'l')
    sp = tr(t, [(0.40, 0.3), (0.58, 1.0), (0.76, 0.75)])                   # legs spread wide at the apex
    for k in LEGKEYS:
        sx = 1.0 if k[0] == 'L' else -1.0
        bo = {'1': (0.22, -0.10, 0.85), '2': (0.30, -0.05, 0.62), '3': (0.25, 0.08, 0.45), '4': (0.10, 0.25, 0.32)}[k[1]]
        P[k] = sleg(b=(bo[0] * sx * sp, bo[1] * sp, bo[2] * sp), mix=m, t=18 * m, floor=0.0)
    return P


@clip('spit', 0.9, events={'release': 0.45, 'sound': 0.42}, views=('left', V34))
def spit(t):
    P = P0()
    P['pitch'] = tr(t, [(0, 0), (0.32, 28), (0.45, -4, 'i'), (0.56, 5), (0.9, 0)])
    P['pos'] = (0.0, tr(t, [(0, 0), (0.32, 0.14), (0.45, -0.16, 'i'), (0.60, -0.06), (0.9, 0)]),
                tr(t, [(0, 0), (0.32, 0.10), (0.45, -0.04, 'i'), (0.60, 0.0), (0.9, 0)]))
    P['abd'] = (tr(t, [(0, 0), (0.32, 30), (0.45, -8, 'i'), (0.6, 6), (0.9, 0)]), 0.0)
    P['chel'] = (tr(t, [(0, 0), (0.30, 44), (0.45, 54), (0.62, 14), (0.9, 0)]), tr(t, [(0, 0), (0.30, 24), (0.48, 30), (0.65, 5), (0.9, 0)]))
    P['fang'] = (tr(t, [(0, 0), (0.30, 55), (0.50, 60), (0.68, 8), (0.9, 0)]), tr(t, [(0, 0), (0.30, 16), (0.5, 20), (0.7, 0), (0.9, 0)]))
    pa = tr(t, [(0, (0, 0, 0)), (0.28, (26, 30, -6)), (0.46, (34, 36, -16)), (0.62, (4, 6, 6)), (0.9, (0, 0, 0))])
    P['palp'] = {'L': tuple(pa), 'R': tuple(pa)}
    d1 = tr(t, [(0, (0, 0, 0)), (0.14, (0.06, 0.04, 0.22)), (0.30, (0.18, 0.10, 0.46)), (0.45, (0.10, 0.02, 0.0), 'i'), (0.60, (0.10, 0.02, 0.0)),
                (0.72, (0.05, 0.0, 0.12)), (0.84, (0, 0, 0)), (0.9, (0, 0, 0))], 'c')
    front_legs(P, ('L1', 'R1'), d1, t=tr(t, [(0, 0), (0.3, 20), (0.46, 0), (0.9, 0)]))
    return P


def reared(P, t, t_up, t_down, wave=0.0, land=None):
    """front two leg pairs raised in body space between t_up and t_down."""
    m = tr(t, [(0, 0), (t_up[0], 0), (t_up[1], 1), (t_down[0], 1), (t_down[1], 0)], 's')
    for k in ('L1', 'R1', 'L2', 'R2'):
        sx = 1.0 if k[0] == 'L' else -1.0
        first = k[1] == '1'
        ph = (0.0 if k[0] == 'L' else 0.5) + (0.0 if first else 0.25)
        w = wave * math.sin(PI2 * (3.0 * t + ph))
        bo = (0.20, 0.16 + 0.05 * w, 0.64 + 0.16 * w) if first else (0.26, 0.06, 0.46 + 0.12 * w)
        d = (0, 0, 0) if land is None else land(k, sx)
        P[k] = sleg(b=(bo[0] * sx, bo[1], bo[2]), mix=m, d=d, t=18 * m + 10 * w)
    return m


@clip('slam', 1.3, events={'hit': [0.66, 0.82], 'impact': 0.70, 'sound': 0.50}, views=('left', V34),
      bounds=(V((-1.3, -1.7, -0.02)), V((1.3, 1.2, 1.9))), sbounds=(V((-0.2, -1.7, -0.02)), V((0.2, 1.2, 1.9))))
def slam(t):
    P = P0()
    P['pitch'] = tr(t, [(0, 0), (0.48, 44), (0.58, 41), (0.70, -12, 'I'), (0.78, -7), (0.90, -9), (1.3, 0)])
    P['pos'] = (0.0, tr(t, [(0, 0), (0.48, 0.20), (0.58, 0.20), (0.70, -0.20, 'I'), (0.86, -0.15), (1.3, 0)]),
                tr(t, [(0, 0), (0.48, 0.22), (0.58, 0.24), (0.70, -0.16, 'I'), (0.80, -0.10), (0.92, -0.12), (1.3, 0)]))
    P['abd'] = (tr(t, [(0, 0), (0.48, 26), (0.70, -8, 'i'), (0.82, 4), (1.3, 0)]), 0.0)
    o = tr(t, [(0, 0), (0.40, 1), (0.66, 1), (0.76, 0.2), (1.3, 0)])
    P['chel'] = (40 * o, 24 * o)
    P['fang'] = (58 * o, 14 * o)
    P['palp'] = {'L': (26 * o, 24 * o, -10 * o), 'R': (26 * o, 24 * o, -10 * o)}

    def land(k, sx):
        tgt = (0.02 * sx, -0.30, 0.0) if k[1] == '1' else (0.06 * sx, -0.14, 0.0)
        lift = 0.12 if k[1] == '1' else 0.10
        t0 = 0.92 if k[0] == 'L' else 1.02                                # the legs step back one side after the other
        s = tr(t, [(0, 0), (0.44, 0), (0.56, 1), (t0, 1), (t0 + 0.20, 0)])
        return (tgt[0] * s, tgt[1] * s, lift * bump(t, t0, t0 + 0.20))
    reared(P, t, (0.10, 0.42), (0.60, 0.70), wave=0.25 * bump(t, 0.3, 0.62), land=land)
    return P


@clip('rear_up', 2.0, events={'sound': 0.50}, views=('left', V34),
      bounds=(V((-1.3, -1.6, -0.02)), V((1.3, 1.2, 1.9))), sbounds=(V((-0.2, -1.6, -0.02)), V((0.2, 1.2, 1.9))))
def rear_up(t):
    P = P0()
    k = tr(t, [(0, 0), (0.45, 1), (1.50, 1), (2.0, 0)])
    sh = math.sin(PI2 * 9.0 * t) * bump(t, 0.45, 1.55, 0.3)                # screech tremble
    P['pitch'] = 40 * k + 1.2 * sh
    P['pos'] = (0.004 * sh, 0.16 * k, 0.20 * k)
    P['roll'] = 1.5 * math.sin(PI2 * 1.5 * t) * k
    P['abd'] = (24 * k + 2 * sh, 0.0)
    P['chel'] = (38 * k + 5 * sh, 24 * k)
    P['fang'] = (55 * k + 6 * sh, 14 * k)
    wl, wr = math.sin(PI2 * 3 * t), math.sin(PI2 * 3 * t + 2.0)
    P['palp'] = {'L': ((26 + 8 * wl) * k, 22 * k, -10 * k), 'R': ((26 + 8 * wr) * k, 22 * k, -10 * k)}
    reared(P, t, (0.08, 0.40), (1.55, 1.92), wave=1.0 * bump(t, 0.3, 1.7, 0.3))
    return P


@clip('hit', 0.4, events={'sound': 0.03}, views=('left', V34), count=6)
def hit(t):
    P = P0()
    k = tr(t, [(0, 0), (0.09, 1, 'o'), (0.22, 0.45), (0.4, 0)])
    P['pos'] = (0.02 * k, 0.13 * k, -0.07 * k)
    P['pitch'] = 9 * k
    P['roll'] = 5 * k
    P['yaw'] = -4 * k
    P['abd'] = (-8 * k, 4 * k)
    P['chel'] = (22 * k, 14 * k)
    P['fang'] = (30 * k, 8 * k)
    P['palp'] = {'L': (24 * k, 18 * k, 10 * k), 'R': (24 * k, 18 * k, 10 * k)}
    w = bump(t, 0.02, 0.34)
    front_legs(P, ('L1', 'R1'), (0.06 * w, 0.10 * k, 0.26 * w), t=14 * w)
    return P


@clip('death', 1.6, events={'impact': 0.85, 'sound': 0.05}, views=('left', V34),
      bounds=(V((-1.3, -1.5, -0.02)), V((1.3, 1.1, 1.5))), sbounds=(V((-0.2, -1.5, -0.02)), V((0.2, 1.1, 1.5))))
def death(t):
    """death throe: crouch, convulsive hop that flips the spider in the air, lands on its back, legs curl."""
    P = P0()
    P['roll'] = tr(t, [(0, 0), (0.28, 0), (0.45, 45, 'i'), (0.60, 105, 'l'), (0.85, 180, 'o'), (1.6, 180)])
    P['pos'] = (tr(t, [(0, 0), (0.28, 0), (0.85, 0.35), (1.6, 0.35)]), 0.0,
                tr(t, [(0, 0), (0.24, -0.16), (0.34, 0.18, 'i'), (0.56, 0.72, 'o'), (0.85, -0.13, 'i'), (0.95, -0.08), (1.08, -0.13), (1.6, -0.13)]))
    P['pitch'] = tr(t, [(0, 0), (0.24, -5), (0.5, 6), (0.85, 0), (1.6, 0)])
    P['abd'] = (tr(t, [(0, 0), (0.24, -8), (0.6, 8), (0.85, -4), (1.6, -4)]), 0.0)
    c = tr(t, [(0, 0), (0.15, 1), (1.6, 0.5)])
    P['chel'] = (20 * c, 14 * c)
    P['fang'] = (36 * c, 8 * c)
    pk = tr(t, [(0, 0), (0.3, 1), (1.6, 1)])
    P['palp'] = {'L': (-10 * pk, 4 * pk, 40 * pk), 'R': (-10 * pk, 4 * pk, 40 * pk)}
    m = tr(t, [(0, 0), (0.26, 0), (0.36, 1), (1.6, 1)])
    curl = tr(t, [(0, 0.0), (0.24, -0.10), (0.34, 0.10), (0.56, 0.92), (0.85, 0.97), (0.98, 0.88), (1.15, 1.0), (1.6, 1.0)])
    for k in LEGKEYS:
        L = LEGS[k]
        h = L.tip0 - L.S0
        hh = V((h.x, h.y, 0.0))
        tw = 0.03 * math.sin(PI2 * 5 * t + int(k[1])) * bump(t, 0.85, 1.3)
        cc = clamp(curl + tw, -0.2, 1.0)
        b = -hh * (0.92 * cc) - ZA * (0.06 * max(cc, 0.0))
        P[k] = sleg(b=tuple(b), mix=m, t=-86 * max(cc, 0.0), floor=0.0 if t < 0.5 else None)
    return P


# ----------------------------------------------------------------------------- main
def write_meta(info, mn, mxx):
    clips = {}
    for name, c in CLIPS.items():
        d = {'duration': round(int(round(c['dur'] * FPS)) / FPS, 4), 'loop': bool(c['loop'])}
        if c['speed'] is not None:
            d['speed'] = c['speed']
        d['events'] = c['events']
        clips[name] = d
    meta = {
        'file': 'spider.glb', 'fps': FPS,
        'description': 'Giant forest spider, rigged + skinned, 10 in-place clips. Scale 0.85-1 for giant spiders, 3.4 for the queen.',
        'size': {'length': round(float(mxx[1] - mn[1]), 3), 'height': round(float(mxx[2]), 3), 'radius': 1.0,
                 'width': round(float(mxx[0] - mn[0]), 3), 'body_length': 1.3, 'body_height': 0.56, 'leg_span': 2.5},
        'triangles': info['summary']['tris'],
        'materials': {'M_chitin': 'shell (COLOR_0 = neutral grey-brown pattern 0.45-1.0 x baked AO: darker joints, banded legs, pale abdomen mark)',
                      'M_bone': 'fangs (dark red-brown to black vertex colour) and foot claws',
                      'M_eye_glow': '8 eyes (vertex colour deep red)'},
        'bones': {'root': 'root', 'body': 'body', 'head': 'head', 'jaw': 'fang_L', 'fangs': ['fang_L', 'fang_R'],
                  'chelicerae': ['chel_L', 'chel_R'], 'mouth': 'mouth', 'abdomen': 'abdomen',
                  'feet': ['leg%dc_%s' % (i, s) for i in (1, 2, 3, 4) for s in ('L', 'R')]},
        'notes': 'Only bone rotations are animated, plus the location of "body" (root stays at the origin). '
                 '"head" is a static reference bone on the cephalothorax; "mouth" (child of head, +Y forward) is the spit origin. '
                 'All clips are in place. One-shots start from and return to the idle pose (= rest pose). '
                 'run lasts 14 frames (0.4667 s) instead of 0.45 s so that both half cycles are identical at 30 fps.',
        'clips': clips,
    }
    with open(os.path.join(CREA_DIR, 'spider.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print('META', json.dumps(meta['size']))


def main():
    reset_scene()
    rig = build_rig()
    arm = rig.build('spider_rig')
    setup_solver(rig)
    mesh = build_model(rig, arm)
    print('TRIS', tri_count(mesh), 'VERTS', len(mesh.data.vertices))
    co = eval_verts(mesh)
    size_mn, size_mx = co.min(0), co.max(0)
    if 'nomodel' not in ARGS:
        hb = (V((-0.42, -0.75, 0.15)), V((0.42, 0.0, 0.85)))

        def bare():
            for sfx, sx in (('_L', 1), ('_R', -1)):
                arm.pose.bones['chel' + sfx].rotation_quaternion = RIG.rest_rot['chel' + sfx].to_quaternion().inverted() @ (RX(-30) @ RY(-sx * 16)) @ RIG.rest_rot['chel' + sfx].to_quaternion()
                arm.pose.bones['fang' + sfx].rotation_quaternion = RIG.rest_rot['fang' + sfx].to_quaternion().inverted() @ RX(-50) @ RIG.rest_rot['fang' + sfx].to_quaternion()

        def relax():
            for n in ('chel_L', 'chel_R', 'fang_L', 'fang_R'):
                arm.pose.bones[n].rotation_quaternion = Quaternion()
        render_tiles(os.path.join(PREVIEWS, 'crea_spider_model.png'), [mesh],
                     [('left', None, None), ('front', None, None), ('top', None, None), ('persp', None, None),
                      ((0.5, 0.75, 0.42), None, None), ('persp_back', None, None), ('front', hb, None), ((-0.6, 0.7, -0.2), hb, bare),
                      ((0.0, 0.25, -1.0), (V((-0.45, 0.0, 0.3)), V((0.45, 0.9, 1.0))), relax)], res=(500, 420), cols=3)
    if 'model' in ARGS:
        return
    p = solve(P0())
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
        act, nfr = bake_clip(arm, rig, name, c['dur'], lambda t, c=c: solve(c['fn'](t)), loop=c['loop'], loc_bones=('body',))
        acts.append(act)
        clip_report(name, mesh, nfr)
        if 'nostrip' not in ARGS:
            imgs_path = os.path.join(PREVIEWS, 'crea_spider_%s.png' % name)
            views = c.get('views', ('left',))
            render_strip(imgs_path, [mesh], int(nfr * c.get('span', 1.0)), count=c.get('count', 8), loop=c['loop'], views=views,
                         res=c.get('res', (420, 330)), bounds=c.get('bounds', BOUNDS))
    if only:
        return
    bpy.data.objects.remove(bpy.data.objects['pv_ground'])
    bpy.context.scene.frame_set(0)
    actions_to_nla(arm, acts)
    info = export_glb(os.path.join(CREA_DIR, 'spider.glb'), [arm, mesh], anims=True)
    print('MESHES', json.dumps(info['meshes']))
    write_meta(info, size_mn, size_mx)


main()
