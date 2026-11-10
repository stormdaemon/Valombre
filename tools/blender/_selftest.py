"""Pipeline self test: rig + proxy mesh + 2 clips + shape key -> glb, plus an EEVEE contact sheet."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
from humanoid_rig import *

reset_scene()
arm = build_humanoid_armature('Armature')

# proxy: one box per deform bone, rigidly weighted
bm = bmesh.new()
groups = []
for b in bone_table():
    if not b['deform']:
        continue
    h, t = b['head'], b['tail']
    L = (t - h).length
    r = min(0.06, max(0.012, L * 0.22))
    mat = (t - h).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    mat.translation = (h + t) * 0.5
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=mat @ Matrix.Diagonal((r * 2, r * 2, L * 0.92, 1)))
    groups.append((b['name'], [v.index for v in res['verts']]))
bm.verts.ensure_lookup_table()
proxy = bmesh_to_object(bm, 'proxy', smooth=False)
for nm, idx in groups:
    proxy.vertex_groups.new(name=nm).add(idx, 1.0, 'REPLACE')
mod = proxy.modifiers.new('Armature', 'ARMATURE')
mod.object = arm
proxy.parent = arm
assign_mat(proxy, make_mat('M_proxy', (0.7, 0.5, 0.3)))

# shape key test
proxy.shape_key_add(name='Basis')
k = proxy.shape_key_add(name='fat')
for v in k.data:
    v.co.y *= 1.5

acts = []
a = new_action(arm, 'wave')
pb = arm.pose.bones['upper_arm_R']
for f, ang in ((1, 0), (10, 60), (20, 0)):
    pb.rotation_quaternion = Euler((math.radians(ang), 0, 0)).to_quaternion()
    pb.keyframe_insert('rotation_quaternion', frame=f)
acts.append(a)
a = new_action(arm, 'kick')
pb = arm.pose.bones['thigh_L']
for f, ang in ((1, 0), (8, -70), (16, 0)):
    pb.rotation_quaternion = Euler((math.radians(ang), 0, 0)).to_quaternion()
    pb.keyframe_insert('rotation_quaternion', frame=f)
pb = arm.pose.bones['forearm_L']
for f, ang in ((1, 0), (8, -90), (16, 0)):
    pb.rotation_quaternion = Euler((0, 0, math.radians(ang))).to_quaternion()
    pb.keyframe_insert('rotation_quaternion', frame=f)
acts.append(a)

# preview while the last action is still active
render_sheet(os.path.join(PREVIEWS, '_selftest.png'), [proxy], views=('front',), frames=[1, 4, 8, 12], res=256)
render_sheet(os.path.join(PREVIEWS, '_selftest_views.png'), [proxy], views=('front', 'left', 'top', 'persp'), res=256)

actions_to_nla(arm, acts)
info = export_glb(os.path.join(ROOT, 'tools', 'previews', '_selftest.glb'), [arm, proxy], anims=True, morphs=True)
print('ANIMS', info['animations'])
print('MESH', info['meshes'])
print('NODES', len(info['nodes']), info['nodes'][:12])
