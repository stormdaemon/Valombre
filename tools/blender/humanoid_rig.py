"""THE humanoid skeleton of VALOMBRE. Shared by the player, NPCs and every humanoid monster.
Bone NAMES, hierarchy and rest orientations are a hard contract: animation clips are authored once on
this rig and replayed on every mesh skinned to it. Never rename / re-roll / add parents.

Rest pose = T-pose, 1.80 m tall, facing -Y, character's LEFT side = +X, feet on z = 0.

Local axes (Blender bone space: +Y runs along the bone, head -> tail):
  spine chain (hips, spine_01..03, neck, head): bone +Y = world up, local X = world +X, local Z = world -Y
      -> rotation about local X, positive = bend FORWARD; about local Y = twist (positive = turn to
         the character's left); about local Z = side bend.
  legs (thigh, shin): bone +Y = down, local X = world +X, local Z = world +Y (back)
      -> thigh: NEGATIVE X rot = leg swings forward (hip flexion). shin: POSITIVE X rot = knee flexion.
  foot / toe: bone points forward(-Y); local X = world +X -> positive X rot = toes down (plantar flexion)... verify with a render.
  arms (clavicle, upper_arm, forearm, hand, fingers), T-pose along the X axis, local Z = world up (+Z)
      left arm : bone +Y = +X world, local X = world -Y(front).  +X rot = raise arm, -Z rot = swing forward
      right arm: bone +Y = -X world, local X = world +Y(back).   +X rot = raise arm, +Z rot = swing forward
      elbow flexion (forearm): left = NEGATIVE Z rot, right = POSITIVE Z rot (forearm folds to the front).
      finger curl (fingers_*, index_*): rotation about local X: NEGATIVE X rot = curl toward palm (palms face down).
  ALWAYS double check a pose with a preview render, the comments above are a guide.

Sockets (non deforming, the engine parents props to them; prop local axes are glTF axes):
  weapon_R / weapon_L : at the grip inside the fist. bone +Y = blade direction (tip), bone +X = cutting
                        edge direction. A weapon .glb is authored in Blender standing upright: grip
                        center at the origin, tip toward +Z, main cutting edge toward +X, flat in the XZ plane.
  shield_L            : on top of the left forearm. bone +Y = shield "up", bone +Z = shield face normal
                        (pointing away from the arm). A shield .glb is authored upright facing -Y,
                        its back (arm straps) at the origin.
  sheath_back         : weapon carried on the back (grip above right shoulder), bone +Y = toward the tip.
  sheath_hip          : weapon carried on the left hip, bone +Y = toward the tip.
"""
import bpy, math
from mathutils import Vector

HEIGHT = 1.80

# name, parent, head, tail, roll-align vector (desired local Z), deform, connected
_C = [
    ('root',      None,       (0, 0, 0),          (0, 0, 0.10),        (0, -1, 0), False),
    ('hips',      'root',     (0, 0, 0.98),       (0, 0, 1.08),        (0, -1, 0), True),
    ('spine_01',  'hips',     (0, 0, 1.08),       (0, 0, 1.20),        (0, -1, 0), True),
    ('spine_02',  'spine_01', (0, 0, 1.20),       (0, 0, 1.34),        (0, -1, 0), True),
    ('spine_03',  'spine_02', (0, 0, 1.34),       (0, 0, 1.50),        (0, -1, 0), True),
    ('neck',      'spine_03', (0, 0.01, 1.50),    (0, 0.0, 1.59),      (0, -1, 0), True),
    ('head',      'neck',     (0, 0.0, 1.59),     (0, 0.0, 1.80),      (0, -1, 0), True),
    ('sheath_back', 'spine_03', (-0.16, 0.14, 1.50), (-0.11, 0.14, 1.415), (0, 1, 0), False),
    ('sheath_hip',  'hips',     (0.19, -0.04, 1.00), (0.19, 0.005, 0.91),  (1, 0, 0), False),
]
# left side (mirrored automatically for the right side)
_L = [
    ('clavicle',    'spine_03',    (0.03, 0, 1.46),          (0.17, 0, 1.47),          (0, 0, 1), True),
    ('upper_arm',   'clavicle_S',  (0.185, 0, 1.47),         (0.47, 0, 1.47),          (0, 0, 1), True),
    ('forearm',     'upper_arm_S', (0.47, 0, 1.47),          (0.73, 0, 1.47),          (0, 0, 1), True),
    ('hand',        'forearm_S',   (0.73, 0, 1.47),          (0.81, 0, 1.47),          (0, 0, 1), True),
    ('thumb_01',    'hand_S',      (0.755, -0.030, 1.462),   (0.790, -0.056, 1.452),   (0, 0, 1), True),
    ('thumb_02',    'thumb_01_S',  (0.790, -0.056, 1.452),   (0.826, -0.072, 1.446),   (0, 0, 1), True),
    ('index_01',    'hand_S',      (0.81, -0.030, 1.47),     (0.856, -0.032, 1.47),    (0, 0, 1), True),
    ('index_02',    'index_01_S',  (0.856, -0.032, 1.47),    (0.906, -0.034, 1.47),    (0, 0, 1), True),
    ('fingers_01',  'hand_S',      (0.81, 0.012, 1.47),      (0.860, 0.014, 1.47),     (0, 0, 1), True),
    ('fingers_02',  'fingers_01_S', (0.860, 0.014, 1.47),    (0.915, 0.016, 1.47),     (0, 0, 1), True),
    ('thigh',       'hips',        (0.095, 0, 0.93),         (0.10, -0.005, 0.50),     (0, 1, 0), True),
    ('shin',        'thigh_S',     (0.10, -0.005, 0.50),     (0.10, 0.015, 0.09),      (0, 1, 0), True),
    ('foot',        'shin_S',      (0.10, 0.015, 0.09),      (0.10, -0.115, 0.02),     (0, 0, -1), True),
    ('toe',         'foot_S',      (0.10, -0.115, 0.02),     (0.10, -0.20, 0.02),      (0, 0, -1), True),
]
# sockets that are not mirrored: (name, parent, head, tail, roll vec)
_S = [
    ('weapon_R', 'hand_R',    (-0.775, 0.0, 1.44),  (-0.775, -0.10, 1.44), (0, 0, 1)),
    ('weapon_L', 'hand_L',    (0.775, 0.0, 1.44),   (0.775, -0.10, 1.44),  (0, 0, -1)),
    ('shield_L', 'forearm_L', (0.60, 0.0, 1.515),   (0.60, -0.10, 1.515),  (0, 0, 1)),
]


def bone_table():
    """Full list of dict(name, parent, head, tail, roll_vec, deform) in creation order."""
    out = []
    for n, p, h, t, r, d in _C:
        out.append(dict(name=n, parent=p, head=Vector(h), tail=Vector(t), roll=Vector(r), deform=d))
    for side, sx in (('L', 1.0), ('R', -1.0)):
        for n, p, h, t, r, d in _L:
            out.append(dict(name='%s_%s' % (n, side), parent=p.replace('_S', '_' + side) if p.endswith('_S') else p,
                            head=Vector((h[0] * sx, h[1], h[2])), tail=Vector((t[0] * sx, t[1], t[2])),
                            roll=Vector(r), deform=d))
    for n, p, h, t, r in _S:
        out.append(dict(name=n, parent=p, head=Vector(h), tail=Vector(t), roll=Vector(r), deform=False))
    return out


BONE_NAMES = [b['name'] for b in bone_table()]
DEFORM_BONES = [b['name'] for b in bone_table() if b['deform']]


def build_humanoid_armature(name='Armature', warp=None):
    """Create the armature object in the current scene and return it.
    warp: optional function(bone_name, Vector point) -> Vector, to build NON-human proportions (troll,
    golem, giant...). It must keep every bone direction roughly the same as the human rest pose (only
    lengths / offsets change), otherwise the shared animation clips will look wrong."""
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    for b in bone_table():
        eb = arm.edit_bones.new(b['name'])
        h, t = b['head'], b['tail']
        if warp:
            h, t = Vector(warp(b['name'], h.copy())), Vector(warp(b['name'], t.copy()))
        eb.head, eb.tail = h, t
        eb.align_roll(b['roll'])
        eb.use_deform = b['deform']
        if b['parent']:
            eb.parent = arm.edit_bones[b['parent']]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    arm.display_type = 'STICK'
    return ob
