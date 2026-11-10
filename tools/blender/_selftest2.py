import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
from humanoid_rig import *
reset_scene()
# 1) static prop with vertex colors, box uv, collider, anchor
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
box = bmesh_to_object(bm, 'crate', smooth=False)
box.location = (0, 0, 1); apply_transforms(box)
assign_mat(box, make_mat('M_wood_planks', lin('#8a6a4b'), use_vertex_color=True))
set_vertex_colors(box, lambda p, n, i: (0.2 + 0.4 * p.z,) * 3)
box_uv(box, 2.0)
col = add_collider_box('crate', (0, 0, 1), (2, 2, 2), parent=box)
anc = add_empty('FIRE_top', (0, 0, 2.1), parent=box)
info = export_glb(os.path.join(PREVIEWS, '_t2_prop.glb'), [box, col, anc])
print('PROP_MESHES', info['meshes']); print('PROP_NODES', info['nodes'])
# 2) auto weights on a capsule-ish body
arm = build_humanoid_armature()
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.5)
body = bmesh_to_object(bm, 'blob')
body.scale = (0.5, 0.35, 1.7); body.location = (0, 0, 0.9); apply_transforms(body)
ok = auto_weights(body, arm); limit_weights(body)
print('AUTOWEIGHTS', ok, [g.name for g in body.vertex_groups][:8], len(body.vertex_groups))
render_sheet(os.path.join(PREVIEWS, '_t2.png'), [box], views=('persp',), res=256, cols=1)
