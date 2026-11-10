"""Pose library of VALOMBRE (see anim_toolkit.CHANNELS for the meaning of every channel).
All positions in meters, character space: X = left, -Y = front, Z = up. Hand targets default to CHEST space
(rest-like coordinates carried by spine_03: shoulders at (+-0.185, 0, 1.47), mouth ~ (0, -0.10, 1.66))."""
from anim_toolkit import *


def blade_for(fdir, pref, keep=0.45):
    """Blade direction close to `pref` but kept roughly perpendicular to the forearm (comfortable wrist)."""
    pref = nrm(pref)
    fdir = nrm(fdir)
    b = perp_to(pref, fdir) + fdir * pref.dot(fdir) * keep
    return tuple(nrm(b, pref))


def bd(az, el=0.0):
    """Direction from azimuth / elevation in degrees: az 0 = forward, +90 = to the left, -90 = right,
    180 = back; el + = up."""
    a, e = math.radians(az), math.radians(el)
    return (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))


def auto_edges(keys, i0, i1, S='R'):
    """Cutting-edge hints for keys[i0..i1]: the edge leads along the path of the blade (direction of the
    cut), computed from the neighbouring blade directions. Edits the key dicts in place."""
    bl = [V(k[1]['blade' + S]) for k in keys]
    last = None
    for i in range(i0, i1 + 1):
        a, b = max(i0, i - 1), min(i1, i + 1)
        e = perp_to(bl[b] - bl[a], bl[i].normalized())
        if e.length > 1e-4:
            last = tuple(e.normalized())
        keys[i][1]['edge' + S] = last
    return keys


def arm_fore(S, elbow, fdir, blade=None, reach=0.31):
    """Arm pose from an (approximate) elbow position and the forearm direction, CHEST space.
    Returns dict(hand<S>, pole<S>[, blade<S>]). Rule of thumb for this rig (blade perpendicular to the palm):
    keep the forearm 45-90 degrees away from the blade, rotated toward the direction of the cut."""
    sx = 1.0 if S == 'L' else -1.0
    sh = Vector((sx * 0.185, 0.0, 1.47))
    e = V(elbow)
    h = e + nrm(fdir) * reach
    pole = nrm(e - (sh + h) * 0.5, (sx * 0.3, 0.6, -0.7))
    d = {'hand' + S: tuple(h), 'pole' + S: tuple(pole)}
    if blade is not None:
        d['blade' + S] = tuple(nrm(blade))
    return d


def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def tw(v, **kw):
    """Copy of a tuple with components replaced: tw(foot, z=0.1, pitch=20)."""
    names = {'x': 0, 'y': 1, 'z': 2, 'pitch': 3, 'yaw': 4, 'roll': 5}
    v = list(v)
    for k, x in kw.items():
        v[names[k]] = x
    return tuple(v)


# ---------------------------------------------------------------- relaxed standing (sword + shield)
STAND = P(
    hips=(0.0, 0.005, 0.968), pelvis=(1, 0, 0), spine=(1, 0, 0), head=(0, 0, 0), hstab=0.0,
    footL=(0.105, 0.015, 0, 0, 9, 0), footR=(-0.105, 0.025, 0, 0, -11, 0), fspL='world', fspR='world',
    handR=(-0.275, -0.03, 0.905), hspR='chest', poleR=(-0.35, 0.9, -0.2), bladeR=(0.05, -0.86, -0.50), curlR=1.0,
    handL=(0.285, -0.035, 0.945), hspL='chest', poleL=(0.35, 0.9, -0.2), twistL=0.0, curlL=0.55,
    wristL=(0.0, 0.0), clavL=(0.0, 0.0), clavR=(0.0, 0.0))

# ---------------------------------------------------------------- fighting stance
# left foot forward, knees bent, shield arm forward at chest height, sword hand cocked by the right hip
COMBAT = P(
    STAND,
    hips=(0.0, 0.02, 0.865), pelvis=(5, -24, 0), spine=(9, 8, 0), head=(5, 0, 0), hstab=1.0,
    footL=(0.15, -0.23, 0, 0, 6, 0), footR=(-0.19, 0.27, 0, 0, -48, 0),
    handL=(-0.04, -0.37, 1.27), poleL=(0.75, 0.15, -0.65), twistL=0.0, curlL=0.9,
    handR=(-0.34, -0.05, 1.05), hspR='chest', poleR=(-0.45, 0.8, -0.35), bladeR=(-0.10, -0.52, 0.85),
    edgeR=(0.0, -0.85, -0.52))

# shield raised in front of the torso, crouched, sword back
BLOCK = P(
    COMBAT,
    hips=(0.0, 0.03, 0.835), pelvis=(7, -22, 0), spine=(13, 6, 0), head=(8, 0, 0),
    handL=(-0.10, -0.35, 1.37), poleL=(0.8, 0.05, -0.6), twistL=8.0,
    handR=(-0.36, -0.02, 1.07), poleR=(-0.45, 0.85, -0.3), bladeR=(-0.20, -0.36, 0.91))

# ---------------------------------------------------------------- two-handed stance (greatsword)
# the left hand is IK'd on the handle below the right hand (Clip(twoh=True)); handL is ignored
TWOH = P(
    STAND,
    hips=(0.0, 0.02, 0.87), pelvis=(5, -20, 0), spine=(8, 8, 0), head=(5, 0, 0), hstab=1.0,
    footL=(0.15, -0.23, 0, 0, 6, 0), footR=(-0.19, 0.27, 0, 0, -48, 0),
    handR=(-0.06, -0.36, 1.21), hspR='chest', poleR=(-0.7, 0.5, -0.5), bladeR=(0.22, -0.52, 0.82),
    edgeR=(0.0, -0.85, -0.5), poleL=(0.7, 0.4, -0.6), curlL=1.0, gripsep=0.17)

# ---------------------------------------------------------------- unarmed civilian
NPC = P(
    STAND, bladeR=None, curlR=0.35, curlL=0.35,
    handR=(-0.275, -0.02, 0.935), handL=(0.275, -0.02, 0.935), twistR=0.0, wristR=(0.0, 0.0))

# ---------------------------------------------------------------- monster (hunched, arms dangling)
# the chest leans ~48 deg forward: hands hanging under the shoulders are FORWARD in chest space
MONSTER = P(
    hips=(0.0, 0.05, 0.86), pelvis=(14, 0, 0), spine=(34, 0, 0), head=(10, 0, 0), hstab=0.85,
    footL=(0.19, 0.0, 0, 0, 16, 0), footR=(-0.19, 0.03, 0, 0, -18, 0), fspL='world', fspR='world',
    handL=(0.27, -0.40, 1.16), hspL='chest', poleL=(0.6, 0.6, -0.5), twistL=-20.0, curlL=0.45, wristL=(15.0, 0.0),
    handR=(-0.27, -0.40, 1.16), hspR='chest', poleR=(-0.6, 0.6, -0.5), twistR=-20.0, curlR=0.45, wristR=(15.0, 0.0),
    clavL=(0.0, 0.0), clavR=(0.0, 0.0))

# ---------------------------------------------------------------- kneeling at a shrine
# right knee on the ground, left foot forward, sword planted tip down in front, left hand on the knee,
# head bowed
KNEEL = P(
    STAND,
    hips=(0.0, 0.06, 0.50), pelvis=(6, -6, 0), spine=(14, 4, 0), head=(26, 2, 0),
    footL=(0.12, -0.20, 0, 0, 6, 0), footR=(-0.13, 0.48, 0.0, 62, -4, 0), kneeR=(-0.12, -1.0, -0.25),
    kneeL=(0.10, -1.0, 0.15),
    handR=(-0.20, -0.36, 0.86), hspR='world', poleR=(-0.8, 0.3, -0.5), bladeR=(0.0, -0.05, -1.0), bspR='world',
    handL=(0.15, -0.31, 0.575), hspL='world', poleL=(0.8, 0.3, -0.3), palmL=(0.0, -0.95, -0.3, 0.0, 0.3, -0.95),
    curlL=0.4)
