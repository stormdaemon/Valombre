"""VALOMBRE wolf: skeleton + procedural model (module used by crea_wolf.py).

The organic body is a voxel union of lofted tubes / blobs / fur tufts, smoothed and decimated; skin
weights and the coat pattern are authored analytically on the source parts and transferred to the
final surface. Ears, lower jaw, tongue, teeth, claws and eyes are separate clean pieces."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crea_common import *

NAME = 'wolf'
XF, XH = 0.095, 0.092                       # sagittal planes of the front / hind legs
TAU = rad(12.0)                             # rest head tilt (nose down)
HS = 1.10                                   # head scale (head-local numbers below are for a 1.0 head)
HEAD0 = V((0, -0.62, 0.92))                 # atlas joint
HA = V((0, -math.cos(TAU), -math.sin(TAU)))  # head axis (toward the nose)
HV = V((0, -math.sin(TAU), math.cos(TAU)))   # head "up"


def hp(a, v, x=0.0):
    """head-local (along the muzzle, up, lateral) -> world."""
    return HEAD0 + (HA * a + HV * v + XA * x) * HS


def hloc(p):
    d = (V(p) - HEAD0) / HS
    return d.dot(HA), d.dot(HV), d.x


JT = dict(
    hips=V((0, 0.385, 0.70)), sp1=V((0, 0.22, 0.715)), sp2=V((0, 0.06, 0.715)), chest=V((0, -0.10, 0.71)),
    neck1=V((0, -0.30, 0.70)), neck2=V((0, -0.465, 0.805)), head=HEAD0,
    tail=[V((0, 0.495, 0.70)), V((0, 0.565, 0.60)), V((0, 0.615, 0.50)), V((0, 0.65, 0.40)), V((0, 0.665, 0.30))],
    scap=V((0.07, -0.28, 0.77)), shoulder=V((XF, -0.40, 0.585)), elbow=V((XF, -0.25, 0.44)),
    carpus=V((XF, -0.27, 0.167)), mcp=V((XF, -0.285, 0.055)), ftoe=V((XF, -0.385, 0.0)),
    hip=V((XH, 0.335, 0.635)), stifle=V((XH, 0.235, 0.41)), hock=V((XH, 0.425, 0.25)),
    mtp=V((XH, 0.41, 0.055)), htoe=V((XH, 0.315, 0.0)),
    jaw=hp(0.048, -0.032), chin=hp(0.250, -0.030),
    ear=hp(0.022, 0.068, 0.056), ear_tip=hp(0.030, 0.166, 0.086),
)
WITHERS = V((0, -0.28, 0.78))               # reference point carried by the chest bone


# ----------------------------------------------------------------------------- rig
def build_rig():
    r = Rig()
    r.bone('root', (0, 0, 0), (0, 0, 0.2), None, zref=(0, -1, 0), deform=False)
    r.bone('hips', JT['hips'], JT['sp1'], 'root')
    r.bone('spine1', JT['sp1'], JT['sp2'], 'hips')
    r.bone('spine2', JT['sp2'], JT['chest'], 'spine1')
    r.bone('chest', JT['chest'], JT['neck1'], 'spine2')
    r.bone('neck1', JT['neck1'], JT['neck2'], 'chest')
    r.bone('neck2', JT['neck2'], JT['head'], 'neck1')
    r.bone('head', JT['head'], hp(0.15, 0.0), 'neck2')
    r.bone('jaw', JT['jaw'], JT['chin'], 'head')
    r.mirror('ear', JT['ear'], JT['ear_tip'], 'head', zref=(0, -1, 0))
    tl = JT['tail']
    for i in range(4):
        r.bone('tail%d' % (i + 1), tl[i], tl[i + 1], 'hips' if i == 0 else 'tail%d' % i)
    r.mirror('scap', JT['scap'], JT['shoulder'], 'chest', zref=(0, -1, 0))
    r.mirror('uarm', JT['shoulder'], JT['elbow'], 'scap_S')
    r.mirror('farm', JT['elbow'], JT['carpus'], 'uarm_S')
    r.mirror('fmeta', JT['carpus'], JT['mcp'], 'farm_S')
    r.mirror('fpaw', JT['mcp'], JT['ftoe'], 'fmeta_S')
    r.mirror('thigh', JT['hip'], JT['stifle'], 'hips')
    r.mirror('shin', JT['stifle'], JT['hock'], 'thigh_S')
    r.mirror('hmeta', JT['hock'], JT['mtp'], 'shin_S')
    r.mirror('hpaw', JT['mtp'], JT['htoe'], 'hmeta_S')
    return r


# ----------------------------------------------------------------------------- colours (LINEAR multipliers)
DARK, MID, LIGHT = 0.55, 0.78, 1.0


def coat(v, warm=0.0):
    """neutral grey value with an optional slight warm cast (tan legs / muzzle of a grey wolf)."""
    return (v, v * (1 - 0.04 * warm), v * (1 - 0.10 * warm))


def c_torso(p, u, th):
    h = math.sin(th)                                  # +1 spine, -1 belly
    v = lerp(lerp(LIGHT, MID, ramp(h, -0.65, -0.05)), DARK, ramp(h, 0.0, 0.62))
    v *= 1.0 + 0.05 * vnoise(p, 9.0, 1.0)
    return coat(clamp(v, 0.52, 1.0), 0.7 * (1 - ramp(h, -0.2, 0.5)))


def c_neck(p, u, th):
    h = math.sin(th)
    v = lerp(lerp(LIGHT, 0.82, ramp(h, -0.7, -0.1)), 0.58, ramp(h, 0.0, 0.7))
    v *= 1.0 + 0.05 * vnoise(p, 9.0, 2.0)
    return coat(clamp(v, 0.52, 1.0), 0.5)


def c_head(p, u, th):
    a, v, x = hloc(p)
    if a > 0.254 and v > 0.000:                       # nose leather
        return (0.05, 0.045, 0.045)
    top = ramp(v, 0.000, 0.050)
    val = lerp(LIGHT, 0.64, top)
    val = lerp(val, 0.58, 0.9 * ramp(v, 0.015, 0.035) * ramp(a, 0.11, 0.19) * ramp(-abs(x), -0.030, -0.012))   # dark bridge
    val = lerp(val, 0.95, bump(a, 0.085, 0.150) * ramp(abs(x), 0.028, 0.045) * ramp(v, 0.025, 0.05) * 0.7)      # pale brows
    return coat(val, 0.7 * (1 - top))


def c_leg(xc):
    def fn(p, u, th):
        inner = ramp(-(abs(p.x) - xc), -0.01, 0.02)
        v = lerp(0.64, 0.96, ramp(-p.z, -0.62, -0.36))
        v = lerp(v, LIGHT, 0.6 * inner)
        v *= 1.0 + 0.04 * vnoise(p, 11.0, 3.0)
        return coat(clamp(v, 0.52, 1.0), 0.9)
    return fn


def c_paw(p, u, th):
    if p.z < 0.006:
        return (0.09, 0.08, 0.08)                     # pads
    return coat(0.95, 1.0)


def c_tail(p, u, th):
    h = math.sin(th)
    v = lerp(0.90, 0.58, ramp(h, -0.5, 0.5))
    v = lerp(v, 0.52, ramp(p.z, 0.42, 0.31))          # dark tail tip
    v *= 1.0 + 0.06 * vnoise(p, 12.0, 4.0)
    return coat(clamp(v, 0.5, 1.0), 0.3)


# ----------------------------------------------------------------------------- weights
def w_torso(p, u=0, th=0):
    return chainw(-p.y, ['hips', 'spine1', 'spine2', 'chest'], [-JT['sp1'].y, -JT['sp2'].y, -JT['chest'].y], 0.065)


_NB1 = bisector(JT['chest'], JT['neck1'], JT['neck2'])
_NB2 = bisector(JT['neck1'], JT['neck2'], JT['head'])


def w_neck(p, u=0, th=0):
    return planew(p, 'chest', [('neck1', JT['neck1'], _NB1, 0.09, 0.07), ('neck2', JT['neck2'], _NB2, 0.06, 0.06),
                               ('head', JT['head'] + HA * 0.01, HA, 0.035, 0.03)])


def w_head(p, u=0, th=0):
    a, v, x = hloc(p)
    t = ramp(a, -0.035, 0.02)
    return {'head': t, 'neck2': 1 - t}


def w_tail(p, u=0, th=0):
    tl = JT['tail']
    js = [('tail1', tl[0] + V((0, 0.02, -0.02)), (tl[1] - tl[0]), 0.05, 0.04)]
    for i in (1, 2, 3):
        js.append(('tail%d' % (i + 1), tl[i], bisector(tl[i - 1], tl[i], tl[i + 1]), 0.04, 0.04))
    return planew(p, 'hips', js)


def w_fleg(sx):
    sfx = '_L' if sx > 0 else '_R'

    def fn(p, u=0, th=0):
        q = V((abs(p.x), p.y, p.z))
        sc, sh, el, ca, mc = JT['scap'], JT['shoulder'], JT['elbow'], JT['carpus'], JT['mcp']
        return planew(q, 'chest', [
            ('scap' + sfx, sc + (sh - sc) * 0.25, (sh - sc), 0.07, 0.07),
            ('uarm' + sfx, sh, V((0, 0.35, -1)), 0.05, 0.05),
            ('farm' + sfx, el, V((0, -0.15, -1)), 0.04, 0.035),
            ('fmeta' + sfx, ca, V((0, 0, -1)), 0.025, 0.025),
            ('fpaw' + sfx, mc + V((0, 0, 0.005)), V((0, -0.35, -1)), 0.02, 0.02)])
    return fn


def w_hleg(sx):
    sfx = '_L' if sx > 0 else '_R'

    def fn(p, u=0, th=0):
        q = V((abs(p.x), p.y, p.z))
        hi, st, ho, mt = JT['hip'], JT['stifle'], JT['hock'], JT['mtp']
        return planew(q, 'hips', [
            ('thigh' + sfx, hi, (st - hi), 0.075, 0.06),
            ('shin' + sfx, st, bisector(hi, st, ho), 0.045, 0.04),
            ('hmeta' + sfx, ho, bisector(st, ho, mt), 0.03, 0.03),
            ('hpaw' + sfx, mt + V((0, 0, 0.005)), V((0, -0.35, -1)), 0.02, 0.02)])
    return fn


# ----------------------------------------------------------------------------- model tables
HEAD_SECS = [  # a, v_top, v_bot, rx, tap, ex   (head-local, unscaled)
    (-0.040, 0.036, -0.030, 0.045, 0.0, 2.0),
    (0.000, 0.072, -0.052, 0.076, 0.0, 2.2),
    (0.045, 0.088, -0.062, 0.090, 0.1, 2.3),
    (0.090, 0.087, -0.058, 0.086, 0.1, 2.4),
    (0.122, 0.076, -0.046, 0.068, 0.0, 2.4),
    (0.148, 0.055, -0.024, 0.048, -0.15, 2.5),
    (0.190, 0.049, -0.022, 0.043, -0.2, 2.6),
    (0.230, 0.045, -0.020, 0.040, -0.2, 2.6),
    (0.258, 0.041, -0.018, 0.037, -0.15, 2.5),
    (0.272, 0.030, -0.010, 0.028, 0.0, 2.2),
]


def muzzle_rx(a):
    """half width of the upper head at head-local a (unscaled)."""
    return float(np.interp(a, [s[0] for s in HEAD_SECS], [s[3] for s in HEAD_SECS]))


def leg_secs(table, sx, dy=0.0):
    """table rows: (z, y_front, y_back, rx, xc) from top to bottom -> loft sections (path goes down)."""
    return [S((xc * sx, 0.5 * (yf + yb) + dy, z), rx, 0.5 * (yb - yf)) for z, yf, yb, rx, xc in table]


FLEG = [
    (0.725, -0.340, -0.215, 0.040, 0.078),
    (0.650, -0.405, -0.235, 0.052, 0.092),
    (0.575, -0.442, -0.270, 0.057, 0.100),
    (0.505, -0.394, -0.236, 0.051, 0.100),
    (0.440, -0.316, -0.198, 0.042, 0.097),
    (0.385, -0.304, -0.222, 0.036, 0.095),
    (0.300, -0.301, -0.233, 0.031, 0.095),
    (0.210, -0.300, -0.242, 0.027, 0.095),
    (0.165, -0.304, -0.237, 0.029, 0.095),
    (0.105, -0.307, -0.254, 0.025, 0.095),
    (0.060, -0.314, -0.256, 0.028, 0.095),
    (0.034, -0.316, -0.254, 0.029, 0.095),
]
HDY = -0.135
HLEG = [
    (0.705, 0.405, 0.590, 0.045, 0.070),
    (0.635, 0.362, 0.628, 0.062, 0.088),
    (0.555, 0.330, 0.614, 0.067, 0.094),
    (0.480, 0.314, 0.562, 0.059, 0.094),
    (0.415, 0.316, 0.494, 0.047, 0.092),
    (0.360, 0.364, 0.518, 0.038, 0.092),
    (0.310, 0.438, 0.563, 0.032, 0.092),
    (0.270, 0.498, 0.605, 0.028, 0.092),
    (0.240, 0.520, 0.603, 0.027, 0.092),
    (0.180, 0.528, 0.582, 0.0245, 0.092),
    (0.110, 0.523, 0.574, 0.024, 0.092),
    (0.060, 0.513, 0.575, 0.028, 0.092),
    (0.034, 0.510, 0.577, 0.029, 0.092),
]
# paws: (y, z_top, z_bot, rx) from heel to toe tips
FPAW = [(-0.246, 0.040, 0.012, 0.020), (-0.268, 0.062, 0.003, 0.036), (-0.298, 0.063, 0.0, 0.043),
        (-0.326, 0.053, 0.0, 0.044), (-0.348, 0.039, 0.0, 0.039), (-0.361, 0.023, 0.002, 0.025)]
HPAW = [(0.452, 0.040, 0.012, 0.018), (0.430, 0.060, 0.003, 0.033), (0.402, 0.061, 0.0, 0.040),
        (0.375, 0.051, 0.0, 0.041), (0.354, 0.037, 0.0, 0.036), (0.342, 0.022, 0.002, 0.023)]
TOE_DX = (-0.029, -0.010, 0.010, 0.029)


def toe_y(tab, k):
    return tab[-1][0] + (0.018 if k in (0, 3) else 0.005)


# ----------------------------------------------------------------------------- model
def build_model(rig, arm):
    B = Builder(rig.names)

    # ---- torso (rump -> chest front), section = (y, z_top, z_bot, half width, taper)
    torso = [
        (0.540, 0.690, 0.610, 0.040, 0.0), (0.500, 0.718, 0.560, 0.076, 0.1), (0.430, 0.744, 0.528, 0.098, 0.15),
        (0.340, 0.760, 0.532, 0.104, 0.2), (0.240, 0.765, 0.548, 0.099, 0.3), (0.140, 0.768, 0.532, 0.102, 0.35),
        (0.040, 0.772, 0.492, 0.113, 0.4), (-0.060, 0.780, 0.456, 0.123, 0.45), (-0.170, 0.795, 0.432, 0.129, 0.5),
        (-0.275, 0.803, 0.428, 0.126, 0.5), (-0.365, 0.790, 0.445, 0.112, 0.45), (-0.435, 0.760, 0.490, 0.090, 0.3),
        (-0.478, 0.720, 0.545, 0.058, 0.2)]
    secs = []
    for y, zt, zb, rx, tap in torso:
        zc = zb + 0.57 * (zt - zb)
        secs.append(S((0, y, zc), rx, (zt - zc, zc - zb), 2.15, tap))
    B.add(loft(secs, n=24, sub=4, caps=(0.7, 0.7)), w_torso, c_torso, name='torso')

    # ---- neck (inside the chest -> skull), thick with the ruff
    nk = [((0, -0.260, 0.640), 0.108, (0.140, 0.140)), ((0, -0.370, 0.705), 0.112, (0.125, 0.135)),
          ((0, -0.460, 0.775), 0.108, (0.105, 0.125)), ((0, -0.540, 0.850), 0.098, (0.090, 0.105)),
          ((0, -0.605, 0.905), 0.086, (0.078, 0.085)), ((0, -0.655, 0.935), 0.064, (0.058, 0.058))]
    B.add(loft([S(c, rx, ry, 2.1) for c, rx, ry in nk], n=20, sub=4), w_neck, c_neck, name='neck')

    # ---- head (skull + upper jaw)
    secs = []
    for a, vt, vb, rx, tap, ex in HEAD_SECS:
        vc = vb + 0.45 * (vt - vb)
        secs.append(S(hp(a, vc), rx * HS, ((vt - vc) * HS, (vc - vb) * HS), ex, tap))
    B.add(loft(secs, n=20, sub=4, caps=(0.6, 0.9)), w_head, c_head, name='head')
    B.add(blob(hp(0.270, 0.024, 0.0), (0.019, 0.014, 0.014), rot=(-12, 0, 0)), 'head', (0.05, 0.045, 0.045), name='nose')
    for sx in (1, -1):
        # brow ridge + cheek bone
        B.add(blob(hp(0.105, 0.060, 0.042 * sx), (0.022, 0.032, 0.015), rot=(-12, 0, 20 * sx)), 'head', c_head, name='brow')
        B.add(blob(hp(0.075, 0.000, 0.072 * sx), (0.020, 0.044, 0.028), rot=(-12, 0, 0)), 'head', c_head, name='cheek')

    # ---- legs
    for sx in (1, -1):
        sfx = '_L' if sx > 0 else '_R'
        B.add(loft(leg_secs(FLEG, sx), n=16, sub=3, caps=(0.6, 0.3)), w_fleg(sx), c_leg(XF), name='fleg')
        B.add(loft(leg_secs(HLEG, sx, HDY), n=16, sub=3, caps=(0.6, 0.3)), w_hleg(sx), c_leg(XH), name='hleg')
        for tab, xc, bone, front in ((FPAW, XF, 'fpaw', True), (HPAW, XH, 'hpaw', False)):
            secs = [S((xc * sx, y, 0.5 * (zt + zb)), rx, 0.5 * (zt - zb), 2.3) for y, zt, zb, rx in reversed(tab)]
            wf = w_fleg(sx) if front else w_hleg(sx)
            B.add(loft(secs, n=14, sub=3, caps=(0.6, 0.6)), wf, c_paw, name=bone)
            for k, dx in enumerate(TOE_DX):
                B.add(blob((xc * sx + dx, toe_y(tab, k), 0.021), (0.0125, 0.022, 0.020), n=8, m=4), bone + sfx, c_paw, name='toe')

    # ---- tail
    tl = [((0, 0.465, 0.705), 0.038), ((0, 0.525, 0.668), 0.044), ((0, 0.577, 0.592), 0.053), ((0, 0.617, 0.500), 0.058),
          ((0, 0.649, 0.402), 0.052), ((0, 0.667, 0.312), 0.036), ((0, 0.673, 0.262), 0.010)]
    B.add(loft([S(c, r * 0.92, r) for c, r in tl], n=14, sub=3, caps=(0.6, 0.5)), w_tail, c_tail, name='tail')

    # ---- fur tufts: ruff, mane, cheeks, elbows, breeches, tail
    def tf(base, d, L, r, wfn, cfn, bend=(0, 0, -0.25), flat=1.0, mirror=True, side_w=False):
        for sx in ((1, -1) if mirror else (1,)):
            b = (base[0] * sx, base[1], base[2])
            dd = (d[0] * sx, d[1], d[2])
            bb = (bend[0] * sx, bend[1], bend[2])
            wf = wfn(sx) if side_w else wfn              # side_w: wfn is a per-side factory (legs)
            w = wf(V(b)) if callable(wf) else wf
            B.add(tuft(b, dd, L, r, bend=bb, flat=flat), w, cfn, name='tuft')

    # cheek ruff (frames the face)
    tf(hp(0.045, -0.010, 0.080), (0.55, 0.75, -0.30), 0.110, 0.040, 'head', c_head, bend=(0, 0.2, -0.2), flat=0.7)
    tf(hp(0.040, -0.046, 0.064), (0.35, 0.60, -0.70), 0.100, 0.038, 'head', c_head, bend=(0, 0.2, -0.2), flat=0.7)
    tf(hp(0.012, 0.030, 0.082), (0.60, 0.80, 0.00), 0.080, 0.030, 'head', c_head, bend=(0, 0.2, -0.1), flat=0.7)
    # neck ruff: a few big flat locks lying back over the shoulders + throat bib
    nU = V((0, 0.66, 0.75)).normalized()
    nBack = V((0, 0.75, -0.66)).normalized()
    for (c, rr, L, r, angs) in ((V((0, -0.500, 0.812)), 0.082, 0.120, 0.050, (-90, -35)),
                                (V((0, -0.400, 0.722)), 0.098, 0.140, 0.058, (-90, -50, -5))):
        for ang in angs:
            radial = XA * math.cos(rad(ang)) + nU * math.sin(rad(ang))
            base = c + radial * rr
            d = nBack * 0.92 + radial * 0.22
            tf(tuple(base), tuple(d), L, r, w_neck, c_neck, mirror=(ang != -90), flat=0.6, bend=(0, 0.1, -0.15))
    tf((0.0, -0.455, 0.580), (0, -0.10, -1), 0.090, 0.046, w_torso, c_torso, mirror=False)
    # mane / hackles along the top line
    for (y, z, L, r) in ((-0.470, 0.868, 0.090, 0.042), (-0.370, 0.830, 0.100, 0.046), (-0.265, 0.808, 0.090, 0.042)):
        wf = w_neck if y < -0.32 else w_torso
        tf((0.0, y, z - 0.026), (0, 0.96, 0.22), L, r, wf, (DARK, DARK, DARK), mirror=False, bend=(0, 0.3, -0.15), flat=0.7)
    # elbow feathering, brisket, breeches behind the thighs
    tf((XF, -0.212, 0.468), (0.1, 0.80, -0.55), 0.065, 0.026, w_fleg, c_leg(XF), side_w=True)
    tf((0.0, -0.200, 0.440), (0, 0.60, -0.75), 0.070, 0.042, w_torso, c_torso, mirror=False)
    tf((XH + 0.008, 0.470, 0.575), (0.12, 0.75, -0.60), 0.085, 0.036, w_hleg, c_leg(XH), side_w=True)
    tf((XH + 0.008, 0.448, 0.490), (0.12, 0.65, -0.72), 0.075, 0.030, w_hleg, c_leg(XH), side_w=True)
    # bushy tail
    for (y, z, L, r, d) in ((0.612, 0.540, 0.070, 0.036, (0, 0.80, -0.6)), (0.648, 0.440, 0.075, 0.036, (0, 0.72, -0.7)),
                            (0.668, 0.345, 0.070, 0.030, (0, 0.50, -0.85))):
        tf((0.0, y, z), d, L, r, w_tail, c_tail, mirror=False, bend=(0, 0, -0.3), flat=0.8)

    body, W, C = B.union('wolf_body', voxel=0.0075, smooth=(1, 4), tris=4950, keep_fn=None)
    W = smooth_weights(body, W, iters=3)

    # mouth faces of the union mesh (palate + back of the mouth)
    me = body.data
    mats = [make_mat('M_fur', (0.46, 0.44, 0.42), 0.9, use_vertex_color=True),
            make_mat('M_mouth', (0.9, 0.9, 0.9), 0.4, use_vertex_color=True),
            make_mat('M_bone', (0.95, 0.95, 0.95), 0.45, use_vertex_color=True),
            make_mat('M_eye_glow', (1, 1, 1), 0.2, emissive=(1.0, 0.55, 0.1), emissive_strength=1.5, use_vertex_color=True)]
    me.materials.append(mats[0])
    me.materials.append(mats[1])
    mouth_v = set()
    for pl in me.polygons:
        a, v, x = hloc(pl.center)
        if 0.086 < a < 0.266 and v < -0.008 and abs(x) < muzzle_rx(a) - 0.009 and pl.normal.dot(HV) < -0.45:
            pl.material_index = 1
            mouth_v.update(pl.vertices)
    fur_v = set()
    for pl in me.polygons:
        if pl.material_index == 0:
            fur_v.update(pl.vertices)
    for vi in mouth_v:
        if vi not in fur_v:
            C[vi] = (0.20, 0.05, 0.05)
    # black lips: thin rim under the upper lip
    for vtx in me.vertices:
        a, v, x = hloc(vtx.co)
        if vtx.index in fur_v and 0.135 < a < 0.272 and v < -0.006 and abs(x) > muzzle_rx(a) * 0.5:
            C[vtx.index] = np.minimum(C[vtx.index], lerp(0.14, 1.0, ramp(v, -0.014, -0.004)))
    pieces = [(body, W, C)]

    # ---- ears (clean lofts, cupped)
    D = Builder(rig.names)
    for sx in (1, -1):
        sfx = '_L' if sx > 0 else '_R'
        b0, b1 = V((JT['ear'].x * sx, JT['ear'].y, JT['ear'].z)), V((JT['ear_tip'].x * sx, JT['ear_tip'].y, JT['ear_tip'].z))
        ax = (b1 - b0).normalized()
        b0 = b0 - ax * 0.024
        Lr = (b1 - b0).length
        fwd = V((0.55 * sx, -1.0, -0.1)).normalized()            # opening faces forward-outward
        sd = ax.cross(fwd).normalized()                          # width direction
        secs = []
        for t, w, thk in ((0.0, 0.046, 0.024), (0.28, 0.050, 0.018), (0.58, 0.041, 0.014), (0.84, 0.024, 0.009), (1.0, 0.006, 0.005)):
            secs.append(S(b0 + ax * (Lr * t) - fwd * (0.012 * math.sin(math.pi * t)), w, thk, 2.0))

        def c_ear(p, u, th, b0=b0, ax=ax):
            s = math.sin(th)
            if s > 0.15:
                return (0.78, 0.66, 0.60)                         # inner ear
            return coat(lerp(0.62, 0.52, ramp((p - b0).dot(ax), 0.05, 0.12)), 0.2)
        D.add(loft(secs, n=8, sub=1, caps=(None, 0.0), side=sd, cup=0.75), 'ear' + sfx, c_ear, group='ear', name='ear')
    ears, We, Ce = D.object('ear', 'wolf_ears')
    ears.data.materials.append(mats[0])
    pieces.append((ears, We, Ce))

    # ---- lower jaw + tongue (head-local a, v_top, v_bot, rx)
    D = Builder(rig.names)
    jw = [(0.045, -0.026, -0.062, 0.032), (0.095, -0.024, -0.078, 0.044), (0.145, -0.020, -0.068, 0.041),
          (0.190, -0.017, -0.058, 0.036), (0.230, -0.015, -0.052, 0.032), (0.252, -0.016, -0.046, 0.026)]

    def c_jaw(p, u, th):
        a, v, x = hloc(p)
        if math.sin(th) > 0.30:
            edge = ramp(abs(x), muzzle_rx(a) * 0.5, muzzle_rx(a) * 0.72)
            return lerp(np.array((0.24, 0.06, 0.06)), np.array((0.07, 0.05, 0.05)), edge)
        return coat(lerp(LIGHT, 0.88, ramp(a, 0.2, 0.05)), 0.8)
    secs = [S(hp(a, vt - 0.004), rx * HS, (0.004 * HS, (vt - 0.004 - vb) * HS), 2.5, 0.25) for a, vt, vb, rx in jw]
    D.add(loft(secs, n=10, sub=1, caps=(0.0, 0.7)), 'jaw', c_jaw, group='jaw', name='jaw')
    jaw, Wj, Cj = D.object('jaw', 'wolf_jaw')
    jaw.data.materials.append(mats[0])
    jaw.data.materials.append(mats[1])
    for pl in jaw.data.polygons:
        if pl.normal.dot(HV) > 0.55:
            pl.material_index = 1
    pieces.append((jaw, Wj, Cj))

    D = Builder(rig.names)
    tg = [(0.090, 0.015), (0.145, 0.021), (0.195, 0.020), (0.228, 0.016), (0.244, 0.009)]
    secs = [S(hp(a, -0.015 - 0.004 * (a < 0.1)), rx * HS, (0.007 * HS, 0.006 * HS), 2.0) for a, rx in tg]
    D.add(loft(secs, n=6, sub=1, caps=(0.0, 0.5)), 'jaw', (0.42, 0.10, 0.12), group='tongue', name='tongue')
    tongue, Wt, Ct = D.object('tongue', 'wolf_tongue')
    tongue.data.materials.append(mats[1])
    pieces.append((tongue, Wt, Ct))

    # ---- teeth + claws
    D = Builder(rig.names)
    ivory = (0.93, 0.88, 0.74)
    for sx in (1, -1):
        # canines
        D.add(cone(hp(0.226, -0.012, 0.033 * sx), hp(0.234, -0.048, 0.035 * sx), 0.0085, n=4, segs=2, curve=HA * -0.25),
              'head', ivory, group='hard', name='canU')
        D.add(cone(hp(0.240, -0.026, 0.022 * sx), hp(0.246, 0.006, 0.023 * sx), 0.0075, n=4, segs=2, curve=HA * -0.2),
              'jaw', ivory, group='hard', name='canL')
        # cheek teeth
        for k in range(5):
            a = 0.150 + k * 0.0150
            h = 0.012 if k in (1, 2) else 0.009
            xx = (muzzle_rx(a) - 0.011) * sx
            D.add(cone(hp(a, -0.017, xx), hp(a, -0.017 - h, xx), 0.0070, n=3), 'head', ivory, group='hard', name='tU')
            a2 = a + 0.008
            xx = (muzzle_rx(a2) - 0.015) * sx
            D.add(cone(hp(a2, -0.022, xx), hp(a2, -0.022 + h, xx), 0.0070, n=3), 'jaw', ivory, group='hard', name='tL')
        # incisors
        for k in range(2):
            xx = (0.006 + 0.011 * k) * sx
            D.add(cone(hp(0.258 - 0.004 * k, -0.012, xx), hp(0.260 - 0.004 * k, -0.024, xx), 0.0048, n=3), 'head', ivory, group='hard', name='iU')
            D.add(cone(hp(0.251 - 0.004 * k, -0.021, xx * 0.85), hp(0.253 - 0.004 * k, -0.010, xx * 0.85), 0.0042, n=3), 'jaw', ivory, group='hard', name='iL')
        # claws
        sfx = '_L' if sx > 0 else '_R'
        for tab, xc, bone in ((FPAW, XF, 'fpaw'), (HPAW, XH, 'hpaw')):
            for k, dx in enumerate(TOE_DX):
                yy = toe_y(tab, k) - 0.016
                D.add(cone((xc * sx + dx, yy, 0.024), (xc * sx + dx * 1.05, yy - 0.024, 0.004), 0.0065, n=3),
                      bone + sfx, (0.16, 0.14, 0.13), group='hard', name='claw')
    hard, Wh, Ch = D.object('hard', 'wolf_hard')
    hard.data.materials.append(mats[2])
    pieces.append((hard, Wh, Ch))

    # ---- eyes: found on the surface of the union mesh
    D = Builder(rig.names)
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    for sx in (1, -1):
        tgt = hp(0.136, 0.026, 0.0)
        out = (V((1.0 * sx, 0, 0)) + HA * 0.45 + HV * 0.05).normalized()
        org = tgt + out * 0.3
        hit = bvh.ray_cast(org, (tgt - org).normalized())
        pos, nrm = hit[0], hit[1]
        look = (nrm * 0.5 + (V((0.9 * sx, 0, 0)) + HA * 0.6).normalized() * 0.5).normalized()

        def c_eye(p, u, th):
            return (0.03, 0.02, 0.01) if u >= 3 else (1.0, 0.72, 0.22)
        D.add(dome(pos - look * 0.0075, look, 0.0130, n=8, rings=2, flat=0.7), 'head', c_eye, group='eye', name='eye')
        # dark eye rim on the fur around
        for vtx in me.vertices:
            dd = (vtx.co - pos).length
            if dd < 0.032:
                C[vtx.index] *= lerp(0.28, 1.0, ramp(dd, 0.013, 0.032))
    eyes, Wy, Cy = D.object('eye', 'wolf_eyes')
    eyes.data.materials.append(mats[3])
    pieces.append((eyes, Wy, Cy))

    # ---- ambient occlusion into the vertex colours, weights, join
    objs = [p[0] for p in pieces]
    aos = bake_ao(objs, rays=24, dist=0.30)
    for (ob, Wp, Cp), ao in zip(pieces, aos):
        if ob.name not in ('wolf_eyes', 'wolf_hard'):
            Cp = Cp * lerp(0.70, 1.0, ao)[:, None]
        write_colors(ob, Cp)
        write_weights(ob, Wp, rig.names, arm)
    mesh = join(objs, NAME)
    activate_colors(mesh)
    box_uv(mesh, 0.5)
    for pl in mesh.data.polygons:
        pl.use_smooth = True
    return mesh
