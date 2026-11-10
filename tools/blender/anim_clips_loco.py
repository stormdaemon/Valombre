"""Idles, locomotion loops, jump and dodge clips."""
from anim_poses import *

TAU = 2 * math.pi


def _c(ph, off=0.0, n=1):
    return math.cos(TAU * n * (ph - off))


def _s(ph, off=0.0, n=1):
    return math.sin(TAU * n * (ph - off))


class Gait:
    """Planted-foot gait cycle, in place. During stance the sole moves at exactly -v along the travel
    direction (no skating when the engine moves the character at v); swing is a Hermite arc whose end
    velocities match the ground speed (foot retraction), with a lift bump and a pitch profile
    (heel strike -> flat -> heel off / toe off -> swing)."""

    def __init__(self, T, v, d, land, base, dirv=(0.0, -1.0), off=None, lift=0.10, peak=0.45, strike=-18.0,
                 toeoff=45.0, swingp=12.0, vel_k=0.8, yaw=None, flat0=0.15, flat1=0.5, swing_out=0.0):
        self.T, self.v, self.d = T, v, d
        self.travel = v * d * T
        self.land = land if isinstance(land, dict) else {'L': land, 'R': land}
        self.base, self.dirv = base, dirv
        self.off = off or {'L': 0.0, 'R': 0.5}
        self.lift, self.peak, self.vel_k, self.swing_out = lift, peak, vel_k, swing_out
        self.yaw = yaw or {'L': 6.0, 'R': -6.0}
        self.pitch = spline([(0.0, strike), (flat0 * d, 0.0), (flat1 * d, 0.0), (d, toeoff),
                             (d + 0.42 * (1 - d), swingp)], 1.0, True)

    def foot(self, S, ph):
        p = (ph - self.off[S]) % 1.0
        d, tr, land = self.d, self.travel, self.land[S]
        out = 0.0
        if p < d:
            along = land - tr * p / d
            z = 0.0
        else:
            u = (p - d) / (1 - d)
            y0, y1 = land - tr, land
            m = -tr / d * (1 - d) * self.vel_k
            u2, u3 = u * u, u * u * u
            along = (2 * u3 - 3 * u2 + 1) * y0 + (u3 - 2 * u2 + u) * m + (-2 * u3 + 3 * u2) * y1 + (u3 - u2) * m
            z = self.lift * bump(u, self.peak)
            out = self.swing_out * math.sin(math.pi * u) * (1 if S == 'L' else -1)
        bx, by = self.base[S]
        return (bx + self.dirv[0] * along + out, by + self.dirv[1] * along, z, self.pitch(p), self.yaw[S], 0.0)

    def steps(self):
        return sorted([[round((self.off[S] % 1.0) * self.T, 3), S] for S in 'LR'])


# ============================================================================ idles
def idle_fn(ph, t):
    w = TAU * ph
    sw = math.sin(w + 0.6)                      # weight shift: hips drift toward the left then the right foot
    br = math.sin(w)                            # one breath per loop
    p = P(STAND)
    p['hips'] = (0.013 * sw, 0.005 + 0.003 * math.sin(w + 2.0), 0.968 - 0.004 * (0.5 + 0.5 * sw))
    p['pelvis'] = (1.0, 1.2 * math.sin(w + 0.2), -1.3 * sw)
    p['spine'] = (1.0 - 1.4 * br, -1.6 * math.sin(w + 0.2), 1.1 * sw)
    p['head'] = (1.0 + 1.0 * math.sin(w - 0.9), 3.5 * math.sin(w + 2.4), -0.5 * sw)
    p['clavL'] = (1.6 * br, 0.0)
    p['clavR'] = (1.6 * br, 0.0)
    p['handR'] = (-0.275 + 0.004 * math.sin(w - 0.5), -0.03 + 0.012 * math.sin(w - 1.2), 0.905 + 0.004 * br)
    p['bladeR'] = (0.05 + 0.02 * math.sin(w - 1.0), -0.86, -0.50 + 0.04 * math.sin(w - 1.6))
    p['handL'] = (0.285 + 0.003 * math.sin(w - 0.3), -0.035 + 0.010 * math.sin(w - 2.0), 0.945 + 0.004 * br)
    return p


def idle_combat_fn(ph, t):
    w = TAU * ph
    b = 0.5 - 0.5 * math.cos(2 * w)             # two soft bounces per loop
    p = P(COMBAT)
    h = COMBAT['hips']
    p['hips'] = (h[0] + 0.006 * math.sin(w), h[1] + 0.006 * math.sin(w + 1.0), h[2] - 0.014 * b)
    p['pelvis'] = (5.0 + 1.0 * b, -24.0 + 1.5 * math.sin(w + 0.4), 0.0)
    p['spine'] = (9.0 + 1.6 * math.sin(2 * w - 0.9), 8.0 - 1.5 * math.sin(w + 0.4), 0.0)
    p['head'] = (5.0 - 1.0 * math.sin(2 * w - 1.4), 1.5 * math.sin(w + 1.0), 0.0)
    hl = COMBAT['handL']
    p['handL'] = (hl[0] + 0.008 * math.sin(w - 0.7), hl[1] + 0.006 * math.sin(2 * w - 1.6), hl[2] + 0.012 * math.sin(2 * w - 1.9))
    hr = COMBAT['handR']
    p['handR'] = (hr[0], hr[1] + 0.008 * math.sin(w - 1.0), hr[2] + 0.010 * math.sin(2 * w - 2.2))
    p['bladeR'] = (-0.10 + 0.03 * math.sin(w - 1.2), -0.52 + 0.04 * math.sin(2 * w - 2.6), 0.85)
    return p


# ============================================================================ walk / run / sprint
G_WALK = Gait(T=1.0, v=1.5, d=0.60, land=0.385, base={'L': (0.085, 0.0), 'R': (-0.085, 0.0)}, lift=0.085,
              peak=0.38, strike=-20.0, toeoff=48.0, swingp=10.0, vel_k=0.75, flat0=0.16, flat1=0.52)


def walk_fn(ph, t):
    g = G_WALK
    c = _c(ph)
    ca = _c(ph, 0.05)
    roll = -2.8 * _s(ph, -0.05)
    p = {'fspL': 'world', 'fspR': 'world', 'hspL': 'chest', 'hspR': 'chest'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.020 * _c(ph, 0.30), 0.010 + 0.008 * _c(ph, 0.12, 2), 0.922 + 0.020 * _c(ph, 0.29, 2))
    p['pelvis'] = (2.5, -6.0 * c, roll)
    p['spine'] = (4.0 + 0.8 * _c(ph, 0.10, 2), 11.0 * _c(ph, 0.02), -roll * 0.85)
    p['head'] = (0.5 + 0.8 * _c(ph, 0.16, 2), 0.0, 0.0)
    p['hstab'] = 0.85
    wR, poleR, fR = arm_angles('R', fwd=2 + 15 * ca, out=9, bend=20 + 8 * ca, inw=4)
    p['handR'], p['poleR'] = wR, poleR
    p['bladeR'] = blade_for(fR, (0.05, -0.80, -0.60 + 0.12 * ca))
    p['curlR'] = 1.0
    wL, poleL, fL = arm_angles('L', fwd=10 - 9 * ca, out=10, bend=58 - 6 * ca, inw=26)
    p['handL'], p['poleL'], p['twistL'], p['curlL'] = wL, poleL, 0.0, 0.7
    return p


G_RUN = Gait(T=0.7, v=4.6, d=0.28, land=0.335, base={'L': (0.075, 0.0), 'R': (-0.075, 0.0)}, lift=0.24,
             peak=0.36, strike=-6.0, toeoff=66.0, swingp=38.0, vel_k=0.55, flat0=0.12, flat1=0.42)


def run_fn(ph, t):
    g = G_RUN
    c = _c(ph)
    ca = _c(ph, 0.04)
    roll = -3.0 * _s(ph, -0.02)
    p = {'fspL': 'world', 'fspR': 'world', 'hspL': 'chest', 'hspR': 'chest'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.014 * _c(ph, 0.18), 0.03 + 0.012 * _c(ph, 0.30, 2), 0.887 + 0.028 * _c(ph, 0.40, 2))
    p['pelvis'] = (9.0 + 1.5 * _c(ph, 0.18, 2), -10.0 * _c(ph, -0.08), roll)
    p['spine'] = (15.0 + 2.0 * _c(ph, 0.22, 2), 19.0 * _c(ph, 0.02), -roll * 0.8)
    p['head'] = (-4.0 + 1.2 * _c(ph, 0.25, 2), 0.0, 0.0)
    p['hstab'] = 0.8
    wR, poleR, fR = arm_angles('R', fwd=-4 + 30 * ca, out=13, bend=48 + 20 * ca, inw=10)
    p['handR'], p['poleR'] = wR, poleR
    p['bladeR'] = blade_for(fR, (-0.12, -0.88, 0.35 + 0.25 * ca), 0.35)
    p['curlR'] = 1.0
    wL, poleL, fL = arm_angles('L', fwd=-2 - 34 * ca, out=14, bend=88 - 12 * ca, inw=24)
    p['handL'], p['poleL'], p['twistL'], p['curlL'] = wL, poleL, 0.0, 0.9
    return p


G_SPRINT = Gait(T=0.5, v=7.5, d=0.25, land=0.355, base={'L': (0.065, 0.0), 'R': (-0.065, 0.0)}, lift=0.34,
                peak=0.34, strike=4.0, toeoff=68.0, swingp=48.0, vel_k=0.45, flat0=0.10, flat1=0.35)


def sprint_fn(ph, t):
    g = G_SPRINT
    c = _c(ph)
    ca = _c(ph, 0.04)
    roll = -3.5 * _s(ph, -0.02)
    p = {'fspL': 'world', 'fspR': 'world', 'hspL': 'chest', 'hspR': 'chest'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.012 * _c(ph, 0.16), 0.06 + 0.012 * _c(ph, 0.30, 2), 0.872 + 0.028 * _c(ph, 0.38, 2))
    p['pelvis'] = (15.0 + 2.0 * _c(ph, 0.16, 2), -13.0 * _c(ph, -0.08), roll)
    p['spine'] = (24.0 + 2.5 * _c(ph, 0.20, 2), 25.0 * _c(ph, 0.02), -roll * 0.8)
    p['head'] = (-12.0 + 1.5 * _c(ph, 0.25, 2), 0.0, 0.0)
    p['hstab'] = 0.75
    wR, poleR, fR = arm_angles('R', fwd=-6 + 46 * ca, out=14, bend=70 + 22 * ca, inw=12)
    p['handR'], p['poleR'] = wR, poleR
    p['bladeR'] = blade_for(fR, (-0.25, -0.75, 0.55 + 0.3 * ca), 0.3)
    p['curlR'] = 1.0
    wL, poleL, fL = arm_angles('L', fwd=-6 - 46 * ca, out=14, bend=92 - 14 * ca, inw=22)
    p['handL'], p['poleL'], p['twistL'], p['curlL'] = wL, poleL, 0.0, 0.9
    return p


# ============================================================================ guarded walks (combat stance)
G_BACK = Gait(T=1.0, v=1.2, d=0.62, land=0.34, base={'L': (0.115, -0.06), 'R': (-0.125, 0.06)}, dirv=(0.0, 1.0),
              lift=0.06, peak=0.5, strike=24.0, toeoff=-12.0, swingp=8.0, vel_k=0.7, flat0=0.22, flat1=0.72,
              yaw={'L': 8.0, 'R': -20.0})


def _guard_arms(p, bob=0.0, sway=0.0, k=1.0):
    hl, hr = COMBAT['handL'], COMBAT['handR']
    p['hspL'], p['hspR'] = 'chest', 'chest'
    p['edgeR'] = COMBAT['edgeR']
    p['handL'] = (hl[0] + 0.02 * sway * k, hl[1] + 0.02, hl[2] - 0.03 + 0.012 * bob * k)
    p['poleL'], p['twistL'], p['curlL'] = COMBAT['poleL'], 0.0, 0.9
    p['handR'] = (hr[0] - 0.01 * sway * k, hr[1] + 0.02 * sway * k, hr[2] + 0.012 * bob * k)
    p['poleR'], p['curlR'] = COMBAT['poleR'], 1.0
    p['bladeR'] = (-0.10 + 0.04 * sway * k, -0.52 + 0.05 * bob * k, 0.85)


def walk_back_fn(ph, t):
    g = G_BACK
    c = _c(ph)
    roll = -2.0 * _s(ph, -0.05)
    p = {'fspL': 'world', 'fspR': 'world'}
    p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
    p['hips'] = (0.022 * _c(ph, 0.30), -0.01 + 0.006 * _c(ph, 0.1, 2), 0.885 + 0.014 * _c(ph, 0.30, 2))
    p['pelvis'] = (7.0, -12.0 + 5.0 * c, roll)
    p['spine'] = (11.0 + 1.0 * _c(ph, 0.1, 2), 5.0 - 7.0 * _c(ph, 0.03), -roll * 0.8)
    p['head'] = (5.0, 0.0, 0.0)
    p['hstab'] = 1.0
    _guard_arms(p, bob=_c(ph, 0.36, 2), sway=_c(ph, 0.08))
    return p


def _strafe(sign):
    """sign = +1: toward the character's left (+X). Lead foot reaches out, trail foot closes (no crossing
    of the fore-aft stance: left foot stays forward, right foot stays back)."""
    lead, trail = ('L', 'R') if sign > 0 else ('R', 'L')
    land = {lead: 0.33, trail: 0.23}
    g = Gait(T=0.9, v=2.0, d=0.33, land=land, base={'L': (0.14, -0.20), 'R': (-0.16, 0.24)},
             dirv=(float(sign), 0.0), off={lead: 0.0, trail: 0.5}, lift=0.09, peak=0.5, strike=6.0, toeoff=22.0,
             swingp=10.0, vel_k=0.5, flat0=0.2, flat1=0.6, yaw={'L': 6.0, 'R': -44.0})

    def fn(ph, t):
        p = {'fspL': 'world', 'fspR': 'world'}
        p['footL'], p['footR'] = g.foot('L', ph), g.foot('R', ph)
        # body: lowest when a foot lands, leans a little into the direction of travel
        p['hips'] = (sign * (0.02 + 0.045 * _c(ph, 0.02)), 0.02, 0.800 + 0.012 * _c(ph, 0.415, 2))
        p['pelvis'] = (7.0, -22.0 + sign * 3.0 * _c(ph, 0.1), sign * (2.0 + 2.5 * _c(ph, 0.55)))
        p['spine'] = (11.0 + 1.5 * _c(ph, 0.4, 2), 7.0, -sign * (1.0 + 2.0 * _c(ph, 0.55)))
        p['head'] = (6.0, 0.0, 0.0)
        p['hstab'] = 1.0
        _guard_arms(p, bob=_c(ph, 0.42, 2), sway=sign * _c(ph, 0.6), k=1.3)
        return p

    return g, fn


G_STRAFE_L, strafe_L_fn = _strafe(+1)
G_STRAFE_R, strafe_R_fn = _strafe(-1)


# ============================================================================ jump
AIR = P(
    STAND,
    hips=(0.0, 0.0, 1.03), pelvis=(6, 0, 0), spine=(8, 0, 0), head=(-6, 0, 0),
    footL=(0.11, -0.17, 0.22, 22, 6, 0), footR=(-0.12, 0.16, 0.25, 42, -8, 0), fspL='hips', fspR='hips',
    handR=(-0.50, -0.08, 1.20), poleR=(-0.5, 0.6, -0.6), bladeR=(-0.45, -0.62, 0.64),
    handL=(0.50, -0.14, 1.24), poleL=(0.5, 0.6, -0.6), twistL=-10.0, curlL=0.5)


def jump_air_fn(ph, t):
    w = TAU * ph
    s1, s2 = math.sin(w), math.sin(w - 1.1)
    p = P(AIR)
    p['hips'] = (0.0, 0.0, 1.03 + 0.006 * s1)
    p['pelvis'] = (6.0 + 1.5 * s1, 0.0, 0.0)
    p['spine'] = (8.0 - 2.0 * s2, 0.0, 0.0)
    p['footL'] = (0.11, -0.17 - 0.03 * s1, 0.22 + 0.025 * s2, 22 + 5 * s1, 6, 0)
    p['footR'] = (-0.12, 0.16 + 0.03 * s1, 0.25 - 0.025 * s2, 42 - 5 * s1, -8, 0)
    p['handR'] = (-0.50, -0.08 + 0.02 * s2, 1.20 + 0.035 * s2)
    p['handL'] = (0.50, -0.14 - 0.02 * s2, 1.24 + 0.035 * math.sin(w - 1.6))
    return p


JUMP_CROUCH = P(
    STAND,
    hips=(0.0, 0.035, 0.79), pelvis=(16, 0, 0), spine=(24, 0, 0), head=(-18, 0, 0),
    handR=(-0.30, 0.20, 0.98), bladeR=(-0.1, -0.55, -0.82), poleR=(-0.4, 0.85, 0.1),
    handL=(0.31, 0.18, 1.00), poleL=(0.4, 0.85, 0.1))
JUMP_LAUNCH = P(
    STAND,
    hips=(0.0, -0.01, 1.025), pelvis=(2, 0, 0), spine=(-3, 0, 0), head=(-4, 0, 0),
    footL=(0.105, 0.015, 0, 56, 9, 0), footR=(-0.105, 0.025, 0, 56, -11, 0),
    handR=(-0.36, -0.30, 1.22), bladeR=(-0.35, -0.70, 0.62), poleR=(-0.5, 0.6, -0.6),
    handL=(0.36, -0.32, 1.28), poleL=(0.5, 0.6, -0.6), twistL=-10.0)
LAND_TOUCH = P(
    STAND,
    hips=(0.0, 0.0, 0.955), pelvis=(6, 0, 0), spine=(8, 0, 0), head=(-4, 0, 0),
    footL=(0.105, 0.015, 0, 14, 9, 0), footR=(-0.105, 0.025, 0, 14, -11, 0),
    handR=(-0.48, -0.10, 1.16), poleR=(-0.5, 0.6, -0.6), bladeR=(-0.45, -0.62, 0.64),
    handL=(0.48, -0.14, 1.18), poleL=(0.5, 0.6, -0.6), twistL=-10.0)
LAND_LOW = P(
    STAND,
    hips=(0.0, 0.04, 0.72), pelvis=(20, 0, 0), spine=(30, 0, 0), head=(-26, 0, 0),
    handR=(-0.40, -0.26, 1.02), poleR=(-0.6, 0.7, -0.3), bladeR=(-0.2, -0.85, 0.3),
    handL=(0.40, -0.28, 1.04), poleL=(0.6, 0.7, -0.3), twistL=-10.0)


# ============================================================================ dodge
_TUCK_L = (0.12, -0.10, 0.82, 30, 8, 0)
_TUCK_R = (-0.12, -0.07, 0.84, 35, -8, 0)
_CL, _CR = COMBAT['footL'], COMBAT['footR']
ROLL_KEYS = [
    (0.00, P(COMBAT)),
    # dive: hands reach for the ground, the sword is laid out to the right
    (0.09, P(COMBAT, hips=(0.0, 0.09, 0.72), pelvis=(55, -12, 0), spine=(48, 10, 6), head=(40, 22, 8), hstab=0.0,
             footL=tw(_CL, pitch=26), footR=tw(_CR, pitch=40, yaw=-30),
             handR=(-0.14, -0.46, 0.32), hspR='world', poleR=(-0.9, 0.3, 0.3), bladeR=(-0.85, -0.45, 0.25), bspR='world',
             handL=(0.20, -0.52, 0.27), hspL='world', poleL=(0.8, 0.5, 0.3))),
    # hands down, head tucked, hips over the top, toes leave the ground
    (0.21, P(COMBAT, hips=(0.0, 0.13, 0.68), pelvis=(102, -8, -10), spine=(70, 14, 8), head=(66, 30, 12), hstab=0.0,
             footL=(0.14, 0.02, 0.05, 62, 6, 0), footR=(-0.16, 0.30, 0.12, 70, -20, 0),
             handR=(-0.15, -0.34, 0.09), hspR='world', poleR=(-0.9, 0.3, 0.3), bladeR=(-0.9, -0.3, 0.12), bspR='world',
             handL=(0.20, -0.42, 0.05), hspL='world', poleL=(0.9, 0.3, 0.3))),
    # rolling over the (right) shoulder and upper back, tightly tucked
    (0.33, P(COMBAT, hips=(0.0, 0.03, 0.44), pelvis=(190, 0, -12), spine=(76, 10, 6), head=(55, 24, 10), hstab=0.0,
             footL=_TUCK_L, footR=_TUCK_R, fspL='hips', fspR='hips',
             handR=(-0.22, -0.30, 1.20), hspR='chest', poleR=(-0.9, 0.3, -0.2), bladeR=(-0.8, 0.5, 0.3), bspR='chest',
             handL=(0.16, -0.30, 1.22), hspL='chest', poleL=(0.9, 0.3, -0.2))),
    # on the lower back, legs start to open toward the ground
    (0.45, P(COMBAT, hips=(0.0, -0.10, 0.23), pelvis=(265, 0, -6), spine=(68, 2, 0), head=(45, 8, 0), hstab=0.0,
             footL=(0.12, -0.14, 0.74, 20, 8, 0), footR=(-0.12, -0.10, 0.78, 25, -8, 0), fspL='hips', fspR='hips',
             handR=(-0.26, -0.34, 1.14), hspR='chest', poleR=(-0.8, 0.5, -0.2), bladeR=(-0.6, -0.3, 0.75), bspR='chest',
             handL=(0.12, -0.36, 1.18), hspL='chest', poleL=(0.9, 0.3, -0.2))),
    # feet catch the ground, deep squat
    (0.56, P(COMBAT, hips=(0.0, -0.10, 0.40), pelvis=(325, -8, 0), spine=(55, 5, 0), head=(8, 10, 0), hstab=0.0,
             footL=(0.15, -0.41, 0, 0, 6, 0), footR=(-0.18, -0.26, 0, 10, -30, 0),
             handR=(-0.30, -0.30, 1.10), hspR='chest', poleR=(-0.7, 0.6, -0.3), bladeR=(-0.3, -0.5, 0.8), bspR='chest',
             handL=(0.02, -0.38, 1.22), hspL='chest', poleL=(0.8, 0.3, -0.4))),
    (0.65, P(COMBAT, hips=(0.0, -0.03, 0.66), pelvis=(352, -16, 0), spine=(30, 7, 0), head=(4, 0, 0), hstab=0.6,
             footL=tw(_CL, y=-0.28), footR=tw(_CR, y=0.04, z=0.07, pitch=20, yaw=-40),
             handR=(-0.33, -0.12, 1.08), hspR='chest', poleR=(-0.5, 0.8, -0.3), bladeR=(-0.1, -0.55, 0.83), bspR='chest',
             handL=(-0.02, -0.38, 1.26), hspL='chest')),
    (0.75, P(COMBAT, pelvis=(365, -24, 0))),
]

BACKSTEP_KEYS = [
    (0.00, P(COMBAT)),
    # load the front leg
    (0.07, P(COMBAT, hips=(0.0, 0.03, 0.80), pelvis=(11, -24, 0), spine=(17, 8, 0), head=(6, 0, 0),
             footL=tw(_CL, pitch=10))),
    # airborne: body thrown back and low, rear foot reaching back, front foot trailing
    (0.19, P(COMBAT, hips=(0.0, 0.05, 0.85), pelvis=(10, -20, 0), spine=(24, 8, 0), head=(6, 0, 0),
             footL=tw(_CL, y=-0.19, z=0.10, pitch=30), footR=tw(_CR, y=0.36, z=0.08, pitch=14),
             handL=(0.0, -0.40, 1.20), handR=(-0.40, -0.06, 1.10), bladeR=(-0.2, -0.75, 0.60))),
    # rear foot lands first, then the front foot; absorb
    (0.29, P(COMBAT, hips=(0.0, 0.05, 0.775), pelvis=(12, -24, 0), spine=(22, 8, 0), head=(6, 0, 0),
             footL=tw(_CL, y=-0.25, z=0.02, pitch=16), handL=(-0.03, -0.38, 1.22),
             handR=(-0.36, -0.03, 1.02))),
    (0.34, P(COMBAT, hips=(0.0, 0.045, 0.77), pelvis=(12, -24, 0), spine=(21, 8, 0), head=(6, 0, 0))),
    (0.45, P(COMBAT)),
]


def clips():
    out = []
    out.append(Clip('idle', 3.0, loop=True, fn=idle_fn, view='persp', nstrip=8, bounds=1.25))
    out.append(Clip('idle_combat', 2.0, loop=True, fn=idle_combat_fn, view='persp', nstrip=8, bounds=1.25))
    out.append(Clip('walk', 1.0, loop=True, fn=walk_fn, speed=1.5, view='right', nstrip=12, bounds=1.3,
                    events={'steps': G_WALK.steps()}))
    out.append(Clip('run', 0.7, loop=True, fn=run_fn, speed=4.6, view='right', nstrip=12, bounds=1.3,
                    events={'steps': G_RUN.steps()}, grounded=False))
    out.append(Clip('sprint', 0.5, loop=True, fn=sprint_fn, speed=7.5, view='right', nstrip=12, bounds=1.3,
                    events={'steps': G_SPRINT.steps()}, grounded=False))
    out.append(Clip('walk_back', 1.0, loop=True, fn=walk_back_fn, speed=1.2, view='right', nstrip=8, bounds=1.3,
                    events={'steps': G_BACK.steps()}))
    out.append(Clip('strafe_L', 0.9, loop=True, fn=strafe_L_fn, speed=2.0, view='front', nstrip=8, bounds=1.3,
                    events={'steps': G_STRAFE_L.steps()}, grounded=False))
    out.append(Clip('strafe_R', 0.9, loop=True, fn=strafe_R_fn, speed=2.0, view='front', nstrip=8, bounds=1.3,
                    events={'steps': G_STRAFE_R.steps()}, grounded=False))
    out.append(Clip('jump_start', 0.25, keys=[(0.0, P(STAND)), (0.11, JUMP_CROUCH), (0.25, JUMP_LAUNCH)],
                    flow_end=True, view='right', nstrip=4, bounds=1.3, lag={'head': 0.02, 'hand': 0.02}))
    out.append(Clip('jump_air', 0.8, loop=True, fn=jump_air_fn, view='persp', nstrip=4, bounds=1.3, grounded=False))
    out.append(Clip('jump_land', 0.35, keys=[(0.0, LAND_TOUCH), (0.10, LAND_LOW), (0.35, P(STAND))],
                    flow_start=True, view='right', nstrip=4, bounds=1.3, events={'impact': 0.0},
                    lag={'head': 0.03, 'hand': 0.04, 'spine': 0.015}))
    out.append(Clip('roll', 0.75, keys=ROLL_KEYS, view='right', nstrip=12, bounds=1.3, grounded=False,
                    events={'iframes': [0.06, 0.52], 'cancel': 0.62}))
    out.append(Clip('backstep', 0.45, keys=BACKSTEP_KEYS, view='right', nstrip=8, bounds=1.3, grounded=False,
                    events={'iframes': [0.04, 0.26], 'cancel': 0.36, 'steps': [[0.24, 'R'], [0.26, 'L']]},
                    lag={'head': 0.02, 'handL': 0.03, 'handR': 0.04}))
    return out
