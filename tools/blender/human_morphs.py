"""Morph targets of the VALOMBRE base human, defined as ANALYTIC DEFORMATION FIELDS.

    from human_morphs import MORPHS, MORPH_ORDER, MORPH_META, LM, apply_morphs
    delta = MORPHS['jaw_width'](points)        # points: (N, 3) numpy array, REST pose, Blender coordinates
    new_points = points + weight * delta       # weight in the range given by MORPH_META

Every field is a pure function of the rest position (T-pose, 1.80 m, facing -Y, left = +X, Z up), so the
very same deformation can be applied to anything that sits on the body: eyes, brows, teeth, hair, beards,
clothes, armour. Fields are symmetric in X and compose additively (three.js morph targets).

Pure numpy, no bpy: importable from any Blender script.
"""
import numpy as np
import math

# ----------------------------------------------------------------------------- landmarks (rest pose, meters)
LM = {
    'head_pivot': (0.0, 0.0, 1.59),            # head bone
    'head_center': (0.0, 0.010, 1.690),
    'head_top': (0.0, 0.012, 1.800),
    'eye_L': (0.0320, -0.0700, 1.6870),        # eyeball centre (character's left = +X)
    'eye_R': (-0.0320, -0.0700, 1.6870),
    'eye_radius': 0.0130,
    'eye_in': (0.0168, -0.0765, 1.6856),       # inner canthus (left eye)
    'eye_out': (0.0472, -0.0735, 1.6882),      # outer canthus
    'brow': (0.034, -0.0895, 1.7065),          # middle of the left eyebrow
    'glabella': (0.0, -0.0950, 1.7035),
    'nasion': (0.0, -0.0905, 1.6920),
    'nose_tip': (0.0, -0.1179, 1.6548),
    'subnasale': (0.0, -0.1000, 1.6410),
    'ala': (0.0170, -0.1000, 1.6475),          # outer edge of the left nostril wing
    'mouth': (0.0, -0.0945, 1.6195),           # stomion (middle of the lip line)
    'mouth_corner': (0.0245, -0.0840, 1.6192),
    'lip_top': (0.0, -0.0987, 1.6276),
    'lip_bottom': (0.0, -0.0955, 1.6095),
    'chin': (0.0, -0.0925, 1.5860),            # pogonion
    'menton': (0.0, -0.0800, 1.5725),          # underside of the chin
    'cheekbone': (0.050, -0.062, 1.665),
    'cheek': (0.045, -0.060, 1.632),
    'jaw_angle': (0.054, -0.006, 1.607),       # gonion
    'jaw_hinge': (0.060, 0.000, 1.667),        # temporo-mandibular joint (mouth_open rotates about X here)
    'ear_L': (0.0760, 0.0130, 1.6775),
    'ear_R': (-0.0760, 0.0130, 1.6775),
    'ear_top': (0.0880, 0.0240, 1.7060),
    'neck_base': (0.0, 0.012, 1.49),
}

# eyelid margins (left eye): x from LID_XI (inner corner) to LID_XO, s = 0..1
LID_XI, LID_XO, LID_ZI, LID_ZO = 0.0168, 0.0472, 1.6856, 1.6882
LID_HUP, LID_HLO = 0.0045, 0.0055
MOUTH_HW = LM['mouth_corner'][0]


def lid_zc(s):
    return LID_ZI + s * (LID_ZO - LID_ZI)


def lid_zu(s):
    s = np.clip(s, 0.0, 1.0)
    sp = s ** 0.80
    return lid_zc(s) + LID_HUP * np.maximum(4 * sp * (1 - sp), 0.0) ** 0.85


def lid_zl(s):
    s = np.clip(s, 0.0, 1.0)
    sp = s ** 1.20
    return lid_zc(s) - LID_HLO * np.maximum(4 * sp * (1 - sp), 0.0) ** 0.90


def slit_z(ax):
    """Height of the lip line at |x| = ax."""
    t = np.clip(np.asarray(ax, float) / MOUTH_HW, 0, 1)
    return LM['mouth'][2] - 0.0005 * np.exp(-(np.asarray(ax, float) / 0.0045) ** 2) + 0.0006 * np.sin(np.pi * t) ** 2 \
        + (LM['mouth_corner'][2] - LM['mouth'][2]) * t ** 3


# ----------------------------------------------------------------------------- helpers
def _s(a, b, x):
    """smoothstep from a (0) to b (1); a > b gives the falling version."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _xyz(p):
    p = np.asarray(p, dtype=np.float64).reshape(-1, 3)
    return p, p[:, 0], p[:, 1], p[:, 2], np.abs(p[:, 0])


def _sx(x, w=0.006):
    """smooth sign of x (0 on the centre line)."""
    return np.clip(x / w, -1.0, 1.0)


def _g(p, c, s):
    """Gaussian blob mirrored in X. c on the left side (x >= 0)."""
    q = np.abs(p[:, 0]) - c[0]
    s = np.broadcast_to(np.asarray(s, float), (3,))
    return np.exp(-((q / s[0]) ** 2 + ((p[:, 1] - c[1]) / s[1]) ** 2 + ((p[:, 2] - c[2]) / s[2]) ** 2))


def _vec(n, sx, dx, dy, dz, w):
    d = np.zeros((n, 3))
    d[:, 0] = sx * dx * w
    d[:, 1] = dy * w
    d[:, 2] = dz * w
    return d


def _eye_dist(p):
    e = np.array(LM['eye_L'])
    return np.sqrt((np.abs(p[:, 0]) - e[0]) ** 2 + (p[:, 1] - e[1]) ** 2 + (p[:, 2] - e[2]) ** 2)


def eye_protect(p):
    """1 around the eyeballs and eyelids, 0 elsewhere: facial fields are multiplied by (1 - eye_protect)
    so that the eyelids never leave the eyeballs."""
    return 1.0 - _s(0.0165, 0.0260, _eye_dist(p))


def eye_plateau(p):
    """1 on the eyeball + lids, soft falloff around: used by the eye_* morphs (the eyeball moves rigidly)."""
    return 1.0 - _s(0.0185, 0.0400, _eye_dist(p))


def head_mask(p):
    p, x, y, z, ax = _xyz(p)
    zh = 1.555 + (1.590 - 1.555) * _s(-0.05, 0.07, y)
    return _s(zh - 0.030, zh + 0.025, z) * _s(0.135, 0.110, ax)


def arm_mask(p):
    p, x, y, z, ax = _xyz(p)
    return _s(0.165, 0.225, ax) * _s(1.32, 1.37, z) * _s(1.62, 1.58, z)


def torso_mask(p):
    p, x, y, z, ax = _xyz(p)
    return (1.0 - arm_mask(p)) * _s(0.80, 0.90, z) * _s(1.56, 1.50, z)


ARM_Z = 1.469


def leg_axis_y(z):
    return np.where(z >= 0.50, 0.004 + (-0.005 - 0.004) * (0.915 - z) / 0.415, -0.005 + 0.023 * (0.50 - z) / 0.395)


# ----------------------------------------------------------------------------- body fields
def f_shoulder_width(p):
    p, x, y, z, ax = _xyz(p)
    w = _s(0.06, 0.19, ax) * (1.0 - _s(0.23, 0.44, ax)) * _s(1.33, 1.41, z) * _s(1.60, 1.54, z)
    d = _vec(len(p), _sx(x), 0.022, 0, 0, w)
    d[:, 2] += 0.004 * w * _s(1.44, 1.50, z)
    return d


def f_chest_size(p):
    p, x, y, z, ax = _xyz(p)
    w = np.exp(-((z - 1.32) / 0.13) ** 2) * (1.0 - arm_mask(p)) * _s(0.86, 1.0, z) * _s(1.56, 1.50, z)
    d = np.zeros_like(p)
    d[:, 0] = x * 0.075 * w
    d[:, 1] = (y - 0.012) * 0.105 * w
    d += _vec(len(p), _sx(x), 0.002, -0.006, 0, _g(p, (0.085, -0.085, 1.355), (0.075, 0.05, 0.06)))
    return d


def f_breast_size(p):
    p, x, y, z, ax = _xyz(p)
    sz = np.where(z < 1.320, 0.048, 0.075)
    q = ((ax - 0.078) / 0.052) ** 2 + ((y + 0.090) / 0.060) ** 2 + ((z - 1.320) / sz) ** 2
    g = np.exp(-q) * _s(0.02, -0.03, y)
    return _vec(len(p), _sx(x), 0.008, -0.046, -0.007, g)


def f_waist_size(p):
    p, x, y, z, ax = _xyz(p)
    w = np.exp(-((z - 1.110) / 0.085) ** 2) * (1.0 - arm_mask(p))
    d = np.zeros_like(p)
    d[:, 0] = x * 0.115 * w
    d[:, 1] = (y - 0.004) * 0.080 * w
    return d


def f_hip_size(p):
    p, x, y, z, ax = _xyz(p)
    sg = np.where(z < 0.94, 0.130, 0.080)
    w = np.exp(-((z - 0.940) / sg) ** 2)
    d = np.zeros_like(p)
    d[:, 0] = x * 0.105 * w * np.minimum(ax / 0.05, 1.0)
    d[:, 1] = (y - 0.012) * 0.060 * w
    return d


def f_belly(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((ax / 0.125) ** 2 + ((z - 1.085) / 0.115) ** 2)) * _s(0.035, -0.045, y) * (1.0 - arm_mask(p))
    d = np.zeros_like(p)
    d[:, 0] = x * 0.22 * g
    d[:, 1] = -0.062 * g
    d[:, 2] = -0.012 * g
    w = np.exp(-((z - 1.07) / 0.10) ** 2) * (1.0 - arm_mask(p))
    d[:, 0] += x * 0.05 * w
    return d


def f_glutes(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.085, 0.085, 0.930), (0.070, 0.065, 0.078))
    return _vec(len(p), _sx(x), 0.003, 0.028, -0.003, g)


def _arm_radial(p, k_upper, k_fore):
    p, x, y, z, ax = _xyz(p)
    prof = _s(0.170, 0.245, ax) * (k_upper + (k_fore - k_upper) * _s(0.43, 0.50, ax)) * (1.0 - _s(0.655, 0.725, ax))
    prof = prof * _s(1.33, 1.37, z) * _s(1.62, 1.58, z)
    d = np.zeros_like(p)
    d[:, 1] = y * prof
    d[:, 2] = (z - ARM_Z) * prof
    return d


def f_arm_size(p):
    return _arm_radial(p, 0.17, 0.14)


def _leg_radial(p, k_thigh, k_calf):
    p, x, y, z, ax = _xyz(p)
    prof = (1.0 - _s(0.86, 0.97, z)) * _s(0.085, 0.150, z) * (k_calf + (k_thigh - k_calf) * _s(0.44, 0.56, z))
    knee = 1.0 - 0.45 * np.exp(-((z - 0.50) / 0.05) ** 2)
    prof = prof * knee
    d = np.zeros_like(p)
    inner = np.minimum(ax / 0.045, 1.0)
    d[:, 0] = np.sign(x) * (ax - 0.100) * prof * np.where(ax < 0.100, inner, 1.0)
    d[:, 1] = (y - leg_axis_y(z)) * prof
    return d


def f_leg_size(p):
    return _leg_radial(p, 0.14, 0.13)


def f_neck_size(p):
    p, x, y, z, ax = _xyz(p)
    zlim = 1.560 + 0.065 * _s(-0.045, 0.045, y)
    w = _s(1.450, 1.505, z) * (1.0 - _s(zlim - 0.022, zlim + 0.012, z)) * _s(0.115, 0.075, ax)
    d = np.zeros_like(p)
    d[:, 0] = x * 0.14 * w
    d[:, 1] = (y - 0.011) * 0.14 * w
    return d


def brow_line_z(ax):
    """Height of the centre line of the eyebrow at |x| = ax."""
    return np.interp(ax, [0.0100, 0.0170, 0.0250, 0.0330, 0.0410, 0.0480, 0.0535, 0.0575],
                     [1.7012, 1.7040, 1.7060, 1.7070, 1.7068, 1.7052, 1.7028, 1.7002])


def f_muscular(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    d = _arm_radial(p, 0.16, 0.12)
    # deltoid, biceps, triceps
    g = _g(p, (0.215, 0.0, 1.475), (0.065, 0.075, 0.065))
    d += _vec(n, sx, 0.008, 0, 0, g)
    d[:, 1] += y * 0.10 * g
    d[:, 2] += (z - ARM_Z) * 0.14 * g
    d += _vec(n, sx, 0, -0.006, 0.004, _g(p, (0.320, -0.035, 1.480), (0.060, 0.030, 0.030)))
    d += _vec(n, sx, 0, 0.006, -0.002, _g(p, (0.330, 0.040, 1.460), (0.075, 0.030, 0.030)))
    # chest, lats, traps, back
    d += _vec(n, sx, 0.003, -0.014, 0.0, _g(p, (0.085, -0.090, 1.360), (0.070, 0.050, 0.055)) * (1 - arm_mask(p)))
    d += _vec(n, sx, 0.013, 0.003, 0.0, _g(p, (0.160, 0.030, 1.300), (0.045, 0.075, 0.100)) * (1 - arm_mask(p)))
    d += _vec(n, sx, 0.0, 0.002, 0.010, _g(p, (0.075, 0.020, 1.530), (0.055, 0.050, 0.030)))
    d += _vec(n, sx, 0.0, 0.008, 0.0, _g(p, (0.070, 0.100, 1.400), (0.085, 0.050, 0.100)))
    # legs, glutes, neck, waist
    d += _leg_radial(p, 0.09, 0.10)
    d += _vec(n, sx, 0, 0.007, 0, _g(p, (0.100, 0.060, 0.370), (0.05, 0.04, 0.09)))
    d += _vec(n, sx, 0.004, -0.006, 0, _g(p, (0.110, -0.060, 0.700), (0.05, 0.04, 0.14)))
    d += 0.25 * f_glutes(p) + 0.5 * f_neck_size(p) - 0.15 * f_waist_size(p)
    return d


def f_heavy(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    d = 0.90 * f_belly(p) + 1.25 * f_waist_size(p) + 0.75 * f_chest_size(p) + 0.80 * f_hip_size(p) \
        + 0.30 * f_breast_size(p) + 0.45 * f_glutes(p) + 1.15 * f_neck_size(p)
    d += _arm_radial(p, 0.17, 0.11) + _leg_radial(p, 0.14, 0.09)
    d += _vec(n, sx, 0.020, 0.004, -0.004, _g(p, (0.140, 0.020, 1.030), (0.060, 0.090, 0.070)) * (1 - arm_mask(p)))
    d += _vec(n, sx, 0.004, 0.014, 0.0, _g(p, (0.080, 0.090, 1.180), (0.10, 0.05, 0.14)))
    # face
    d += 0.9 * f_cheek_fullness(p) + 0.45 * f_jaw_width(p)
    d += _vec(n, sx, 0.0, -0.005, -0.011, _g(p, (0.0, -0.045, 1.570), (0.045, 0.040, 0.020)))      # double chin
    d += _vec(n, sx, 0.004, -0.002, -0.004, _g(p, (0.040, -0.045, 1.598), (0.022, 0.030, 0.018)))   # jowls
    return d


def f_thin(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    d = -0.70 * f_waist_size(p) - 0.60 * f_chest_size(p) - 0.50 * f_hip_size(p) - 0.25 * f_glutes(p) \
        - 0.70 * f_neck_size(p)
    d -= _arm_radial(p, 0.13, 0.11) + _leg_radial(p, 0.12, 0.10)
    g = np.exp(-((ax / 0.11) ** 2 + ((z - 1.10) / 0.11) ** 2)) * _s(0.03, -0.04, y) * (1.0 - arm_mask(p))
    d[:, 1] += 0.010 * g
    d += -0.85 * f_cheek_fullness(p) + 0.25 * f_cheekbone_width(p) - 0.20 * f_jaw_width(p)
    d += _vec(n, sx, -0.0022, 0, 0, _g(p, (0.066, -0.045, 1.705), (0.012, 0.022, 0.020)))          # temples
    return d


def f_feminine(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    d = -0.80 * f_shoulder_width(p) + 0.85 * f_breast_size(p) - 0.85 * f_waist_size(p) + 0.70 * f_hip_size(p) \
        + 0.30 * f_glutes(p) - 0.75 * f_neck_size(p)
    # narrower rib cage, softer / thinner limbs
    w = np.exp(-((z - 1.30) / 0.14) ** 2) * (1.0 - arm_mask(p)) * _s(1.56, 1.50, z)
    d[:, 0] -= x * 0.065 * w
    d[:, 1] -= (y - 0.012) * 0.050 * w * _s(-0.02, 0.03, y)
    d -= _arm_radial(p, 0.13, 0.11)
    d -= _leg_radial(p, -0.02, 0.07)
    # waist sits higher, lower back curve
    d[:, 1] += -0.006 * np.exp(-((z - 1.10) / 0.07) ** 2) * _s(0.02, 0.06, y) * (1.0 - arm_mask(p))
    # smaller hands and feet (about the wrist / ankle)
    wh = _s(0.725, 0.760, ax)
    d[:, 0] -= np.sign(x) * (ax - 0.727) * 0.07 * wh
    d[:, 1] -= y * 0.08 * wh
    d[:, 2] -= (z - 1.470) * 0.08 * wh
    wf = _s(0.11, 0.07, z)
    d[:, 0] -= np.sign(x) * (ax - 0.100) * 0.07 * wf
    d[:, 1] -= (y - 0.018) * 0.07 * wf
    # face: softer jaw and brow, smaller nose and chin, fuller lips, slightly larger eyes
    d += -0.95 * f_jaw_width(p) - 0.80 * f_chin_width(p) - 0.45 * f_chin_length(p) - 0.95 * f_brow_ridge(p) \
        + 0.55 * f_brow_height(p) + 0.75 * f_lip_upper(p) + 0.70 * f_lip_lower(p) - 0.70 * f_nose_width(p) \
        - 0.50 * f_nose_length(p) + 0.35 * f_nose_tip(p) - 0.40 * f_nose_bridge(p) + 0.50 * f_cheek_fullness(p) \
        + 0.45 * f_eye_size(p) - 0.60 * f_forehead_slope(p) - 0.50 * f_jaw_height(p) - 0.30 * f_mouth_width(p) \
        - 0.40 * f_nostril_width(p) + 0.25 * f_eye_tilt(p) - 0.30 * f_chin_forward(p)
    # longer eyelashes: only the lash tips are further than 2.5 mm from the eyelid surface
    e = np.array(LM['eye_L'])
    sl = (ax - LID_XI) / (LID_XO - LID_XI)
    ml = _s(LM['eye_radius'] + 0.0020, LM['eye_radius'] + 0.0034, _eye_dist(p)) * (z > lid_zl(sl) - 0.001) \
        * (z < lid_zu(sl) + 0.0030) * (sl > -0.05) * (sl < 1.05) * (y < e[1] - 0.010)
    d += (p - _eye_centers(p)) * (0.16 * ml)[:, None]
    # thinner, more arched eyebrows (squeeze toward the brow line; the skin only slides a little)
    zb = brow_line_z(ax)
    gb = np.exp(-(((z - zb) / 0.0060) ** 2 + ((y + 0.088) / 0.020) ** 2)) * _s(0.006, 0.012, ax) * _s(0.064, 0.056, ax)
    d[:, 2] += -(z - zb) * 0.38 * gb + 0.0012 * gb * np.sin(np.pi * np.clip((ax - 0.010) / 0.048, 0, 1))
    # masseter / jaw angle softening, slightly narrower head
    d += _vec(n, sx, -0.0025, 0, 0.002, _g(p, (0.050, -0.012, 1.618), (0.016, 0.03, 0.022)))
    d[:, 0] -= x * 0.02 * head_mask(p)
    return d


# ----------------------------------------------------------------------------- head fields
def f_head_size(p):
    p, x, y, z, ax = _xyz(p)
    c = np.array(LM['head_pivot'])
    return (p - c) * (0.07 * head_mask(p))[:, None]


def f_head_width(p):
    p, x, y, z, ax = _xyz(p)
    d = np.zeros_like(p)
    d[:, 0] = x * 0.075 * head_mask(p)
    return d


def f_head_depth(p):
    p, x, y, z, ax = _xyz(p)
    d = np.zeros_like(p)
    d[:, 1] = (y - 0.008) * 0.075 * head_mask(p)
    return d


def f_forehead_height(p):
    p, x, y, z, ax = _xyz(p)
    d = np.zeros_like(p)
    d[:, 2] = 0.016 * _s(1.712, 1.765, z) * head_mask(p)
    return d


def f_forehead_slope(p):
    p, x, y, z, ax = _xyz(p)
    d = np.zeros_like(p)
    d[:, 1] = 0.011 * _s(1.710, 1.770, z) * _s(1.800, 1.775, z) * _s(0.030, -0.040, y) * head_mask(p)
    return d


def f_brow_ridge(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((np.maximum(ax - 0.030, 0) / 0.024) ** 2 + ((y + 0.088) / 0.022) ** 2 + ((z - 1.7045) / 0.0085) ** 2))
    return _vec(len(p), _sx(x), 0.0005, -0.0045, 0.0, g * (1.0 - eye_protect(p)))


def f_brow_height(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((np.maximum(ax - 0.034, 0) / 0.026) ** 2 + ((y + 0.085) / 0.030) ** 2 + ((z - 1.7060) / 0.0105) ** 2))
    return _vec(len(p), _sx(x), 0, 0, 0.0050, g * (1.0 - eye_protect(p)))


def _eye_centers(p):
    e = np.array(LM['eye_L'])
    c = np.tile(e, (len(p), 1))
    c[:, 0] *= np.where(p[:, 0] >= 0, 1.0, -1.0)
    return c


def f_eye_size(p):
    p, x, y, z, ax = _xyz(p)
    return (p - _eye_centers(p)) * (0.12 * eye_plateau(p))[:, None]


def f_eye_spacing(p):
    p, x, y, z, ax = _xyz(p)
    return _vec(len(p), _sx(x), 0.0035, 0, 0, eye_plateau(p))


def f_eye_height(p):
    p, x, y, z, ax = _xyz(p)
    return _vec(len(p), 0, 0, 0, 0.0040, eye_plateau(p))


def f_eye_depth(p):
    p, x, y, z, ax = _xyz(p)
    return _vec(len(p), 0, 0, 0.0040, 0, eye_plateau(p))


def f_eye_tilt(p):
    p, x, y, z, ax = _xyz(p)
    th = math.radians(7.0)
    e = np.array(LM['eye_L'])
    w = eye_plateau(p)
    d = np.zeros_like(p)
    d[:, 2] = (ax - e[0]) * th * w
    d[:, 0] = -np.sign(x) * (z - e[2]) * th * w
    return d


def f_nose_length(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.0, -0.105, 1.650), (0.022, 0.024, 0.016))
    return _vec(len(p), 0, 0, -0.0015, -0.0060, g)


def f_nose_width(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((np.maximum(ax - 0.008, 0) / 0.012) ** 2 + ((y + 0.103) / 0.020) ** 2 + ((z - 1.655) / 0.020) ** 2))
    return _vec(len(p), _sx(x, 0.004), 0.0032, 0, 0, g)


def f_nose_bridge(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.0, -0.101, 1.6740), (0.009, 0.013, 0.012))
    return _vec(len(p), 0, 0, -0.0040, 0, g)


def f_nose_tip(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, LM['nose_tip'], (0.013, 0.013, 0.0095))
    return _vec(len(p), 0, 0, 0.0008, 0.0036, g)


def f_nostril_width(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.0135, -0.1000, 1.6478), (0.0075, 0.0100, 0.0075))
    return _vec(len(p), _sx(x, 0.004), 0.0030, 0, 0, g)


def f_cheekbone_height(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.048, -0.062, 1.664), (0.022, 0.028, 0.016))
    return _vec(len(p), 0, 0, 0, 0.0050, g * (1.0 - eye_protect(p)))


def f_cheekbone_width(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.052, -0.052, 1.666), (0.022, 0.035, 0.018))
    return _vec(len(p), _sx(x), 0.0050, -0.0015, 0, g * (1.0 - eye_protect(p)))


def f_cheek_fullness(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.043, -0.058, 1.632), (0.020, 0.028, 0.022))
    return _vec(len(p), _sx(x), 0.0045, -0.0040, 0, g)


def f_jaw_width(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.052, -0.010, 1.610), (0.020, 0.040, 0.024))
    g2 = _g(p, (0.034, -0.050, 1.592), (0.016, 0.025, 0.016))
    return _vec(len(p), _sx(x), 0.0070, 0, 0, g) + _vec(len(p), _sx(x), 0.0030, 0, 0, g2)


def _jaw_region(p):
    p, x, y, z, ax = _xyz(p)
    zn = 1.553 + 0.047 * _s(-0.050, 0.030, y)
    return _s(zn - 0.012, zn + 0.010, z) * _s(0.020, -0.010, y) * _s(0.085, 0.065, ax)


def f_jaw_height(p):
    p, x, y, z, ax = _xyz(p)
    w = _s(1.6150, 1.5850, z) * _jaw_region(p)
    return _vec(len(p), 0, 0, 0, -0.0070, w)


def f_chin_length(p):
    p, x, y, z, ax = _xyz(p)
    return _vec(len(p), 0, 0, 0, -0.0060, _g(p, (0.0, -0.082, 1.580), (0.024, 0.022, 0.014)))


def f_chin_width(p):
    p, x, y, z, ax = _xyz(p)
    return _vec(len(p), _sx(x), 0.0050, 0, 0, _g(p, (0.014, -0.080, 1.584), (0.014, 0.022, 0.014)))


def f_chin_forward(p):
    p, x, y, z, ax = _xyz(p)
    return _vec(len(p), 0, 0, -0.0060, 0, _g(p, (0.0, -0.085, 1.584), (0.026, 0.022, 0.016)))


def _mouth_front(y):
    return _s(-0.050, -0.072, y)


def f_mouth_width(p):
    p, x, y, z, ax = _xyz(p)
    prof = np.where(ax < MOUTH_HW, ax / MOUTH_HW, np.exp(-((ax - MOUTH_HW) / 0.014) ** 2))
    w = prof * np.exp(-((z - LM['mouth'][2]) / 0.012) ** 2) * _mouth_front(y)
    d = _vec(len(p), np.sign(x), 0.0040, 0, 0, w)
    d[:, 1] += 0.0012 * w * _s(0.012, MOUTH_HW, ax)
    return d


def f_mouth_height(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((ax / 0.034) ** 2 + ((z - LM['mouth'][2]) / 0.0145) ** 2)) * _mouth_front(y)
    return _vec(len(p), 0, 0, 0, 0.0040, g)


def f_lip_upper(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((ax / 0.022) ** 2 + ((z - 1.6262) / 0.0050) ** 2)) * _s(-0.070, -0.084, y)
    return _vec(len(p), 0, 0, -0.0022, 0.0016, g)


def f_lip_lower(p):
    p, x, y, z, ax = _xyz(p)
    g = np.exp(-((ax / 0.020) ** 2 + ((z - 1.6118) / 0.0055) ** 2)) * _s(-0.070, -0.084, y)
    return _vec(len(p), 0, 0, -0.0024, -0.0018, g)


def _ear_centers(p):
    e = np.array((0.0740, 0.0120, 1.6770))
    c = np.tile(e, (len(p), 1))
    c[:, 0] *= np.where(p[:, 0] >= 0, 1.0, -1.0)
    return c


def f_ear_size(p):
    p, x, y, z, ax = _xyz(p)
    c = _ear_centers(p)
    r = np.sqrt(((np.abs(p[:, 0]) - 0.082) ** 2) + (y - 0.016) ** 2 + (z - 1.677) ** 2)
    w = (1.0 - _s(0.033, 0.050, r)) * _s(0.066, 0.0745, ax)
    return (p - c) * (0.18 * w)[:, None]


def f_ear_point(p):
    p, x, y, z, ax = _xyz(p)
    g = _g(p, (0.0865, 0.0225, 1.7040), (0.012, 0.014, 0.0115)) * _s(0.068, 0.076, ax)
    return _vec(len(p), _sx(x), 0.0060, 0.0110, 0.0250, g)


def f_age(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    d = _vec(n, sx, 0.0012, -0.0010, -0.0042, _g(p, (0.040, -0.050, 1.603), (0.020, 0.030, 0.020)))      # jowls
    d += _vec(n, sx, -0.0006, 0.0026, 0.0, _g(p, (0.0235, -0.088, 1.6400), (0.0055, 0.012, 0.014)))      # nasolabial
    d += _vec(n, sx, 0.0, -0.0013, -0.0009, _g(p, (0.032, -0.080, 1.6745), (0.013, 0.010, 0.0040)))      # eye bags
    d += _vec(n, sx, -0.0026, 0.0, 0.0, _g(p, (0.066, -0.045, 1.705), (0.012, 0.022, 0.020)))            # temples
    d += _vec(n, sx, 0.0, -0.0020, -0.0060, _g(p, (0.0, -0.045, 1.568), (0.035, 0.035, 0.016)))          # loose chin
    d += _vec(n, sx, 0.0010, 0.0, -0.0022, _g(p, (LM['mouth_corner'][0] + 0.004, -0.082, 1.612), (0.007, 0.012, 0.009)))
    d += -0.60 * f_lip_upper(p) - 0.50 * f_lip_lower(p) - 0.50 * f_brow_height(p) - 0.40 * f_cheek_fullness(p) \
        + 0.40 * f_nose_length(p) - 0.35 * f_nose_tip(p) + 0.30 * f_ear_size(p) + 0.25 * f_nose_width(p)
    return d


# ----------------------------------------------------------------------------- expressions
def f_blink(p):
    p, x, y, z, ax = _xyz(p)
    e = np.array(LM['eye_L'])
    s = (ax - LID_XI) / (LID_XO - LID_XI)
    zu, zl = lid_zu(s), lid_zl(s)
    zm = 0.5 * (zu + zl)
    gap = np.maximum(zu - zl - 0.0002, 0.0)
    span = np.maximum(zu - zm, 1e-5)
    up = np.where(z >= zu, 1.0 - _s(0.0, 0.0130, z - zu), np.clip((z - zm) / span, 0.0, 1.0))
    wx = _s(LID_XI - 0.0005, LID_XI + 0.0030, ax) * (1.0 - _s(LID_XO - 0.0030, LID_XO + 0.0005, ax))
    wd = _s(-0.052, -0.064, y) * (z < zu + 0.016) * (z > zl - 0.010)
    w = wx * wd
    dz = -gap * up * w
    # lower lid comes up a little
    lo = np.where(z < zm, 1.0 - _s(0.0, 0.0070, zl - z), 0.0) * (z <= zl + 0.0012)
    dz = dz + 0.0007 * lo * w
    # slide on the eyeball: keep the distance to the eye axis (in the y-z plane)
    rho2 = (y - e[1]) ** 2 + (z - e[2]) ** 2
    zn = z + dz
    yn = e[1] - np.sqrt(np.maximum(rho2 - (zn - e[2]) ** 2, 0.0045 ** 2))
    dy = np.where(np.abs(dz) > 1e-7, (yn - y), 0.0) * np.clip(np.abs(dz) / np.maximum(gap, 1e-5), 0.0, 1.0) ** 0.5
    dy = np.minimum(dy, 0.0) * w
    d = np.zeros_like(p)
    d[:, 1] = dy
    d[:, 2] = dz
    return d


JAW_OPEN_DEG = 17.0


def jaw_weight(p):
    p, x, y, z, ax = _xyz(p)
    zs = slit_z(ax)
    t = _s(LM['mouth_corner'][1], 0.0, y)
    zsep = np.where(ax <= MOUTH_HW, zs, zs + (LM['jaw_hinge'][2] - 0.022 - zs) * t)
    sig = 0.0125 * _s(MOUTH_HW - 0.0005, MOUTH_HW + 0.016, ax) + 1e-6
    w = 1.0 - _s(zsep - sig, zsep + sig, z)
    return w * _jaw_region(p)


def f_mouth_open(p):
    p, x, y, z, ax = _xyz(p)
    h = LM['jaw_hinge']
    th = math.radians(JAW_OPEN_DEG)
    c, sn = math.cos(th), math.sin(-th)
    ry, rz = y - h[1], z - h[2]
    w = jaw_weight(p)
    d = np.zeros_like(p)
    d[:, 1] = (ry * c + rz * sn - ry - 0.006) * w
    d[:, 2] = (-ry * sn + rz * c - rz) * w
    # the upper lip lifts a little, the corners come in
    g = np.exp(-((ax / 0.022) ** 2 + ((z - 1.6255) / 0.0060) ** 2)) * _s(-0.070, -0.084, y) * (z > slit_z(ax))
    d[:, 2] += 0.0016 * g
    gc = _g(p, LM['mouth_corner'], (0.010, 0.014, 0.010))
    d[:, 0] -= _sx(x) * 0.0022 * gc
    return d


def f_smile(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    gc = _g(p, LM['mouth_corner'], (0.0150, 0.0200, 0.0130))
    d = _vec(n, sx, 0.0052, 0.0028, 0.0042, gc)
    d += 0.45 * f_mouth_width(p)
    d += _vec(n, sx, 0.0018, -0.0022, 0.0030, _g(p, (0.043, -0.066, 1.645), (0.020, 0.026, 0.016)) * (1.0 - eye_protect(p)))
    d += _vec(n, sx, 0.0010, 0.0, 0.0010, _g(p, (0.0150, -0.0990, 1.6480), (0.008, 0.010, 0.007)))
    return d


def f_angry(p):
    p, x, y, z, ax = _xyz(p)
    n = len(p)
    sx = _sx(x)
    prot = 1.0 - eye_protect(p)
    d = _vec(n, sx, -0.0032, -0.0008, -0.0048, _g(p, (0.016, -0.090, 1.7035), (0.013, 0.020, 0.0095)) * prot)
    d += _vec(n, sx, -0.0010, 0.0, -0.0022, _g(p, (0.036, -0.086, 1.7065), (0.016, 0.022, 0.0100)) * prot)
    d += _vec(n, sx, 0.0, 0.0012, 0.0, _g(p, (0.0, -0.095, 1.7030), (0.006, 0.010, 0.010)))
    d += _vec(n, sx, 0.0008, 0.0, 0.0024, _g(p, (0.0160, -0.0985, 1.6490), (0.009, 0.012, 0.009)))
    d += _vec(n, sx, 0.0, -0.0006, 0.0020, _g(p, (0.0120, -0.0940, 1.6265), (0.008, 0.010, 0.0055)) * _s(-0.070, -0.084, y))
    d += _vec(n, sx, -0.0008, 0.0, -0.0024, _g(p, LM['mouth_corner'], (0.009, 0.014, 0.009)))
    d += _vec(n, sx, 0.0, -0.0008, 0.0016, _g(p, (0.0, -0.090, 1.6040), (0.018, 0.014, 0.008)))
    return d


# ----------------------------------------------------------------------------- registry
#  name, function, category, french label, min, max
_DEFS = [
    ('feminine', f_feminine, 'body', 'Morphologie féminine', 0, 1),
    ('muscular', f_muscular, 'body', 'Musculature', 0, 1),
    ('heavy', f_heavy, 'body', 'Corpulence', 0, 1),
    ('thin', f_thin, 'body', 'Maigreur', 0, 1),
    ('shoulder_width', f_shoulder_width, 'body', 'Largeur des épaules', -1, 1),
    ('chest_size', f_chest_size, 'body', 'Tour de poitrine', -1, 1),
    ('breast_size', f_breast_size, 'body', 'Taille des seins', -1, 1),
    ('waist_size', f_waist_size, 'body', 'Tour de taille', -1, 1),
    ('hip_size', f_hip_size, 'body', 'Largeur des hanches', -1, 1),
    ('belly', f_belly, 'body', 'Ventre', 0, 1),
    ('glutes', f_glutes, 'body', 'Fessiers', -1, 1),
    ('arm_size', f_arm_size, 'body', 'Épaisseur des bras', -1, 1),
    ('leg_size', f_leg_size, 'body', 'Épaisseur des jambes', -1, 1),
    ('neck_size', f_neck_size, 'body', 'Épaisseur du cou', -1, 1),
    ('head_size', f_head_size, 'head', 'Taille de la tête', -1, 1),
    ('head_width', f_head_width, 'head', 'Largeur de la tête', -1, 1),
    ('head_depth', f_head_depth, 'head', 'Profondeur du crâne', -1, 1),
    ('forehead_height', f_forehead_height, 'head', 'Hauteur du front', -1, 1),
    ('forehead_slope', f_forehead_slope, 'head', 'Inclinaison du front', -1, 1),
    ('brow_ridge', f_brow_ridge, 'head', 'Arcade sourcilière', -1, 1),
    ('brow_height', f_brow_height, 'head', 'Hauteur des sourcils', -1, 1),
    ('eye_size', f_eye_size, 'eyes', 'Taille des yeux', -1, 1),
    ('eye_spacing', f_eye_spacing, 'eyes', 'Écartement des yeux', -1, 1),
    ('eye_height', f_eye_height, 'eyes', 'Hauteur des yeux', -1, 1),
    ('eye_depth', f_eye_depth, 'eyes', 'Enfoncement des yeux', -1, 1),
    ('eye_tilt', f_eye_tilt, 'eyes', 'Inclinaison des yeux', -1, 1),
    ('nose_length', f_nose_length, 'nose', 'Longueur du nez', -1, 1),
    ('nose_width', f_nose_width, 'nose', 'Largeur du nez', -1, 1),
    ('nose_bridge', f_nose_bridge, 'nose', 'Arête du nez', -1, 1),
    ('nose_tip', f_nose_tip, 'nose', 'Pointe du nez', -1, 1),
    ('nostril_width', f_nostril_width, 'nose', 'Largeur des narines', -1, 1),
    ('cheekbone_height', f_cheekbone_height, 'head', 'Hauteur des pommettes', -1, 1),
    ('cheekbone_width', f_cheekbone_width, 'head', 'Largeur des pommettes', -1, 1),
    ('cheek_fullness', f_cheek_fullness, 'head', 'Rondeur des joues', -1, 1),
    ('jaw_width', f_jaw_width, 'jaw', 'Largeur de la mâchoire', -1, 1),
    ('jaw_height', f_jaw_height, 'jaw', 'Hauteur de la mâchoire', -1, 1),
    ('chin_length', f_chin_length, 'jaw', 'Longueur du menton', -1, 1),
    ('chin_width', f_chin_width, 'jaw', 'Largeur du menton', -1, 1),
    ('chin_forward', f_chin_forward, 'jaw', 'Avancée du menton', -1, 1),
    ('mouth_width', f_mouth_width, 'mouth', 'Largeur de la bouche', -1, 1),
    ('mouth_height', f_mouth_height, 'mouth', 'Hauteur de la bouche', -1, 1),
    ('lip_upper', f_lip_upper, 'mouth', 'Lèvre supérieure', -1, 1),
    ('lip_lower', f_lip_lower, 'mouth', 'Lèvre inférieure', -1, 1),
    ('ear_size', f_ear_size, 'ears', 'Taille des oreilles', -1, 1),
    ('ear_point', f_ear_point, 'ears', 'Oreilles pointues', 0, 1),
    ('age', f_age, 'head', 'Âge', 0, 1),
    ('blink', f_blink, 'expression', 'Clignement des yeux', 0, 1),
    ('mouth_open', f_mouth_open, 'expression', 'Bouche ouverte', 0, 1),
    ('smile', f_smile, 'expression', 'Sourire', 0, 1),
    ('angry', f_angry, 'expression', 'Colère', 0, 1),
]

# amplitude of the registered morph at weight 1 (the composite fields above call the raw f_* functions)
AMP = {
    'muscular': 1.45, 'heavy': 1.2, 'shoulder_width': 1.35, 'chest_size': 1.3, 'breast_size': 1.1, 'waist_size': 1.2,
    'hip_size': 1.3, 'belly': 1.2, 'glutes': 1.3, 'arm_size': 1.4, 'leg_size': 1.4, 'neck_size': 1.2,
    'head_width': 1.2, 'head_depth': 1.2, 'brow_ridge': 1.4, 'brow_height': 1.3, 'eye_size': 1.35,
    'eye_spacing': 1.3, 'eye_height': 1.3, 'eye_depth': 1.3, 'eye_tilt': 1.45, 'nose_length': 1.35,
    'nose_width': 1.6, 'nose_bridge': 1.4, 'nose_tip': 1.4, 'nostril_width': 1.5, 'cheekbone_height': 1.4,
    'cheekbone_width': 1.4, 'cheek_fullness': 1.5, 'jaw_width': 1.45, 'jaw_height': 1.4, 'chin_length': 1.5,
    'chin_width': 1.5, 'chin_forward': 1.5, 'mouth_width': 1.5, 'mouth_height': 1.35, 'lip_upper': 1.45,
    'lip_lower': 1.45, 'ear_size': 1.4, 'age': 1.3,
}


def _scaled(f, a):
    if a == 1.0:
        return f
    return lambda p: a * f(p)


MORPHS = {}
MORPH_ORDER = []
MORPH_META = {}
for _n, _f, _c, _l, _a, _b in _DEFS:
    MORPHS[_n] = _scaled(_f, AMP.get(_n, 1.0))
    MORPH_ORDER.append(_n)
    MORPH_META[_n] = {'name': _n, 'category': _c, 'label': _l, 'min': _a, 'max': _b, 'default': 0}

EXPRESSIONS = ('blink', 'mouth_open', 'smile', 'angry')
# morphs the EYEBALLS follow (everything that is not an expression: facial fields leave the eye area alone,
# the eye_* fields move it rigidly)
EYE_MORPHS = tuple(n for n in MORPH_ORDER if n not in EXPRESSIONS)


def apply_morphs(points, weights):
    """points (N,3) rest positions, weights {name: value} -> morphed points."""
    p = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    out = p.copy()
    for k, w in weights.items():
        if w:
            out += w * MORPHS[k](p)
    return out
