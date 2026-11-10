"""In-hand convention check for the VALOMBRE gear.

Loads the EXPORTED .glb files, attaches them to the `weapon_R` / `shield_L` sockets of the shared humanoid
rig exactly like the engine does (identity local transform of a +Y-up glTF node under the socket bone, i.e.
authored Blender (x, y, z) -> bone space (x, z, -y)), poses the rig with the real game poses of the animation
toolkit (STAND / COMBAT / BLOCK / TWOH) and renders the result.

Run:  blender -b --factory-startup -P tools/blender/gear_inhand.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gear_lib import *
from humanoid_rig import *

GEAR = os.path.join(MODELS, 'gear')
GLTF_TO_BONE = Matrix.Rotation(math.radians(-90), 4, 'X')        # Blender-authored axes -> glTF axes


def import_glb(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(GEAR, name + '.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    ob = [o for o in new if o.type == 'MESH'][0]
    for o in new:
        if o is not ob:
            bpy.data.objects.remove(o)
    for i, slot in enumerate(ob.material_slots):
        nm = slot.material.name.split('.')[0]
        slot.material = preview_mat(nm)
    return ob


def attach(ob, arm, bone):
    """Engine attach: socketBone.add(gltfScene) with identity local transform."""
    ob.parent = arm
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = Matrix.Translation((0, -arm.data.bones[bone].length, 0)) @ GLTF_TO_BONE


def apply_pose(arm, local, loc, scale=1.0):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for n, q in local.items():
        if n in arm.pose.bones:
            arm.pose.bones[n].rotation_quaternion = q
    arm.pose.bones['hips'].location = Vector(loc) * scale
    bpy.context.view_layer.update()


def manual_poses():
    """Fallback (no animation toolkit): bone-local eulers, see humanoid_rig.py docstring."""
    def q(x=0, y=0, z=0):
        return Euler((math.radians(x), math.radians(y), math.radians(z))).to_quaternion()
    down = {'upper_arm_R': q(-72, 0, 10), 'upper_arm_L': q(-72, 0, -10), 'forearm_R': q(0, 0, 15), 'forearm_L': q(0, 0, -15)}
    guard = {'upper_arm_R': q(-60, 0, 30), 'forearm_R': q(0, 0, 80), 'upper_arm_L': q(-55, 0, -40), 'forearm_L': q(0, 0, -95)}
    return {'arms_down': (down, (0, 0, 0)), 'guard': (guard, (0, 0, 0))}


def main():
    reset_scene()
    arm = build_humanoid_armature('Armature')
    poses, body, src = {}, None, 'manual'
    try:
        import anim_toolkit as AT
        import anim_poses as AP
        rig = AT.Rig(arm)
        body = AT.build_mannequin(arm)
        for nm, p, twoh in (('stand', AP.STAND, False), ('combat', AP.COMBAT, False), ('block', AP.BLOCK, False),
                            ('twoh', AP.TWOH, True)):
            local, loc, info = rig.solve(p, twoh=twoh)
            poses[nm] = (local, loc)
        src = 'anim_toolkit'
    except Exception as e:
        print('INHAND: animation toolkit unavailable (%s), manual poses' % e)
        poses = manual_poses()
    print('INHAND pose source:', src)
    if body is None:
        mb = MB()
        for b in bone_table():
            if not b['deform']:
                continue
            h, t = b['head'], b['tail']
            r = min(0.05, max(0.012, (t - h).length * 0.2))
            mb.bone = b['name']
            mb.tube([h, t], r, 6, 'M_cloth', (0.6, 0.5, 0.4))
        body = skin_to(mb.build('proxy'), arm)

    sword, shield_ = import_glb('sword_steel'), import_glb('shield_iron')
    clay, kite_, axe, wood = import_glb('claymore'), import_glb('shield_kite'), import_glb('axe_war'), import_glb('shield_wood')
    attach(sword, arm, 'weapon_R')
    attach(axe, arm, 'weapon_R')
    attach(clay, arm, 'weapon_R')
    attach(shield_, arm, 'shield_L')
    attach(kite_, arm, 'shield_L')
    attach(wood, arm, 'shield_L')
    gear = [sword, shield_, clay, kite_, axe, wood]

    def show(*objs):
        for o in gear:
            o.hide_render = o not in objs

    # numeric check of the convention in the T-pose (rest): where do the authored axes end up in the world?
    bpy.context.view_layer.update()
    R = sword.matrix_world.to_3x3()
    S = shield_.matrix_world.to_3x3()
    print('INHAND rest sword : tip(+Z) -> %s  edge(+X) -> %s  origin %s' % (
        tuple(round(v, 3) for v in R @ ZA), tuple(round(v, 3) for v in R @ XA),
        tuple(round(v, 3) for v in sword.matrix_world.translation)))
    print('INHAND rest shield: face(-Y) -> %s  up(+Z) -> %s  elbow side(+X) -> %s  origin %s' % (
        tuple(round(v, 3) for v in S @ -YA), tuple(round(v, 3) for v in S @ ZA), tuple(round(v, 3) for v in S @ XA),
        tuple(round(v, 3) for v in shield_.matrix_world.translation)))

    tiles_full, tiles_zoom = [], []
    cam = setup_preview(400)
    setups = [('rest', None, (sword, shield_))]
    for nm in poses:
        if nm == 'twoh':
            setups.append((nm, poses[nm], (clay,)))
        elif nm == 'block':
            setups.append((nm, poses[nm], (sword, kite_)))
        elif nm == 'combat':
            setups.append((nm, poses[nm], (axe, wood)))
        else:
            setups.append((nm, poses[nm], (sword, shield_)))
    for nm, pz, objs in setups:
        if pz is None:
            apply_pose(arm, {}, (0, 0, 0))
        else:
            apply_pose(arm, pz[0], pz[1])
        show(*objs)
        bpy.context.view_layer.update()
        mn, mx = mesh_bounds([body] + list(objs))
        for v in ('front', 'left', 'back', (-0.6, 0.7, -0.3)):
            frame_camera(cam, mn, mx, v, 1.0)
            tiles_full.append(render_to_array()[:, :, :3])
        # close-ups: right fist (thumb side), left forearm + shield from outside and from the bearer
        M = arm.matrix_world
        hr = M @ arm.pose.bones['weapon_R'].head
        box = (hr - Vector((0.22, 0.22, 0.22)), hr + Vector((0.22, 0.22, 0.22)))
        for v in ((0.55, 0.8, -0.2), (-0.7, 0.6, -0.35)):
            frame_camera(cam, box[0], box[1], v, 1.0)
            tiles_zoom.append(render_to_array()[:, :, :3])
        hl = M @ arm.pose.bones['shield_L'].head
        box = (hl - Vector((0.36, 0.36, 0.36)), hl + Vector((0.36, 0.36, 0.36)))
        for v in ((-0.75, 0.6, -0.25), (0.35, -0.9, -0.3)):
            frame_camera(cam, box[0], box[1], v, 1.0)
            tiles_zoom.append(render_to_array()[:, :, :3])
    save_png(os.path.join(PREVIEWS, 'gear_in_hand.png'), montage(tiles_full, cols=4))
    print('PREVIEW', os.path.join(PREVIEWS, 'gear_in_hand.png'))
    save_png(os.path.join(PREVIEWS, 'gear_in_hand_zoom.png'), montage(tiles_zoom, cols=4))
    print('PREVIEW', os.path.join(PREVIEWS, 'gear_in_hand_zoom.png'))


if __name__ == '__main__':
    main()
