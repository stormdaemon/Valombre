"""VALOMBRE base human (male base, T-pose, 1.80 m) with morph targets.

Run:
  blender -b --factory-startup -P tools/blender/human_build.py -- [flags]
flags (any combination):
  final   export assets/models/char/human.glb + human_manifest.json, save tools/blender/build/human.blend and
          render the final preview sheets tools/previews/hum_{body,head,presets,expressions,poses}.png
  head    work-in-progress close-ups of the head            (hum_*_wip.png)
  shape   work-in-progress sheets of the body               (hum_*_wip.png)
  poses   work-in-progress skinning test poses              (hum_poses_wip.png)
  morphs  work-in-progress presets / expressions            (hum_*_wip.png)
  each    one tile per morph at -1 / +1                      (hum_each_*_wip.png)
  wire    add a wireframe overlay to the wip sheets

Modules:  human_sdf.py     implicit sculpt (the SHAPE)
          human_mesh.py    mesh builder + head topology        human_body.py   body topology
          human_morphs.py  morph targets as analytic fields (importable by the outfit / hair scripts)
          human_util.py    blender helpers, vertex colours, skin weights
          human_final.py   mouth, shape keys, UVs, region split, export      human_glb.py  glb post-process
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from human_final import *

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FLAGS = set(ARGV) or {'final'}
WIRE = 'wire' in FLAGS
T0 = time.time()
OUT_GLB = os.path.join(MODELS, 'char', 'human.glb')
OUT_MANIFEST = os.path.join(MODELS, 'char', 'human_manifest.json')
OUT_BLEND = os.path.join(ROOT, 'tools', 'blender', 'build', 'human.blend')

PRESETS = [
    ('male base', {}),
    ('female base', {'feminine': 1.0}),
    ('old heavy man', {'heavy': 0.9, 'age': 1.0, 'belly': 0.5, 'nose_width': 0.5, 'jaw_width': 0.4,
                       'brow_height': -0.3, 'neck_size': 0.3, 'ear_size': 0.4}),
    ('athletic woman', {'feminine': 1.0, 'muscular': 0.55, 'shoulder_width': 0.3, 'breast_size': -0.3,
                        'jaw_width': 0.25, 'cheekbone_width': 0.4, 'eye_tilt': 0.35, 'lip_lower': 0.2}),
    ('gaunt elf-eared', {'thin': 0.9, 'ear_point': 1.0, 'cheekbone_height': 0.6, 'cheekbone_width': 0.4,
                         'jaw_width': -0.6, 'chin_length': 0.4, 'chin_width': -0.5, 'eye_tilt': 0.8,
                         'eye_size': 0.3, 'nose_width': -0.5, 'nose_bridge': 0.3, 'head_width': -0.3,
                         'brow_height': 0.3}),
    ('brute', {'muscular': 1.0, 'heavy': 0.3, 'shoulder_width': 0.8, 'jaw_width': 1.0, 'brow_ridge': 1.0,
               'neck_size': 0.8, 'chin_width': 0.8, 'nose_width': 0.8, 'eye_depth': 0.7, 'forehead_slope': 0.8,
               'eye_size': -0.4, 'lip_upper': -0.5}),
    ('young woman', {'feminine': 1.0, 'thin': 0.3, 'eye_size': 0.5, 'lip_upper': 0.4, 'lip_lower': 0.4,
                     'nose_length': -0.4, 'nose_tip': 0.5, 'cheek_fullness': 0.4, 'chin_length': -0.3,
                     'breast_size': 0.2, 'hip_size': 0.3}),
    ('old woman', {'feminine': 1.0, 'age': 1.0, 'heavy': 0.45, 'belly': 0.3, 'breast_size': 0.3, 'nose_length': 0.3,
                   'chin_forward': 0.3, 'eye_size': -0.2}),
]
HEAD_C, HEAD_H = (0, -0.005, 1.675), 0.150
FACE_C, FACE_H = (0, -0.06, 1.655), 0.088

# ============================================================================= 1. topology + projection
reset_scene()
mb = MB()
build_head(mb)
hmesh_body.build_body(mb)
mb.relax(iters=6, lam=0.5)
M = mb.mirrored()
M['hand'] = {}
for i, v in mb.sets.get('hand_info', {}).items():
    M['hand'][int(i)] = v
    M['hand'][int(M['mirror'][i])] = v
# consistent outward winding, colours, rest positions (float32 exactly as stored in the meshes)
tmp = mesh_from('tmp_full', M['P'], M['F'])
recalc_normals(tmp)
M['F'] = [tuple(p.vertices) for p in tmp.data.polygons]
P32 = object_points(tmp)
_vol = 0.0
for f in M['F']:
    for k in range(1, len(f) - 1):
        _vol += float(np.dot(P32[f[0]], np.cross(P32[f[k]], P32[f[k + 1]]))) / 6.0
if _vol < 0:
    print('WARN: inverted mesh, flipping')
    M['F'] = [tuple(reversed(f)) for f in M['F']]
COL = skin_colors(tmp, M)
bpy.data.objects.remove(tmp, do_unlink=True)
TRIS = {}
for f, tg in zip(M['F'], M['ft']):
    TRIS[tg] = TRIS.get(tg, 0) + len(f) - 2
print('verts', len(P32), 'faces', len(M['F']), 'volume %.4f m3' % _vol, 'TRIS', TRIS, 'total', sum(TRIS.values()),
      'time %.1f' % (time.time() - T0))

# ============================================================================= 2. rig, weights, morphs, uvs
arm = build_humanoid_armature('Armature')
W = compute_weights(M, arm)
print('weights: max influences', int((W > 0).sum(1).max()), 'sum range', float(W.sum(1).min()), float(W.sum(1).max()))
if 'dbg' in FLAGS:
    for k in (0, 5, 10, 15):
        print('ARM k=%d ' % k + ' | '.join('%.3f: ua %.2f fa %.2f h %.2f' % (
            P32[r[k]][0], W[r[k], BI['upper_arm_L']], W[r[k], BI['forearm_L']], W[r[k], BI['hand_L']])
            for r in mb.sets['arm_rings'][5:15]))
DELTAS = {nm: hm.MORPHS[nm](P32) for nm in hm.MORPH_ORDER}
UV0, UV1 = compute_uvs(P32, M['F'], M['ft'], M['vt'])
D = dict(P=P32, F=M['F'], W=W, COL=COL, UV0=UV0, UV1=UV1, DELTAS=DELTAS)

# ============================================================================= 3. objects
body = build_body_object('body_full', D, None, arm, True)
eL = make_eye('eye_L', LM['eye_L'])
eR = make_eye('eye_R', LM['eye_R'])
brows = make_brows()
mouth = make_mouth()
for o in (eL, eR):
    rigid_skin(o, arm, 'head')
    add_shape_keys(o, names=hm.EYE_MORPHS)
for o in (brows, mouth):
    rigid_skin(o, arm, 'head')
    add_shape_keys(o)
extras = [eL, eR, brows, mouth]
objs = [body] + extras
print('objects built %.1f' % (time.time() - T0), 'extra tris', {o.name: tri_count(o) for o in extras})
preview_lights(False)
ws = [wire_overlay(body)] if WIRE else []


def P_(name):
    return os.path.join(PREVIEWS, name)


def preset_tiles(presets):
    tiles = []
    for nm, w in presets:
        tiles.append(dict(center=(0, 0, 0.92), half=0.98, view=(-0.25, 0.96, -0.08), morphs=w, pose=POSES['a_pose']))
        tiles.append(dict(center=HEAD_C, half=0.168, view='front', morphs=w))
        tiles.append(dict(center=HEAD_C, half=0.168, view=V34, morphs=w))
    return tiles


def pose_tiles():
    A = POSES
    return [
        dict(center=(0, 0, 1.15), half=0.70, view='front', pose=A['arms_down']),
        dict(center=(0, 0, 1.15), half=0.70, view='back', pose=A['arms_down']),
        dict(center=(0.18, 0, 1.38), half=0.30, view=(-0.5, 0.8, -0.25), pose=A['arms_down']),
        dict(center=(0, 0, 1.45), half=0.80, view='front', pose=A['arms_up']),
        dict(center=(0.17, 0, 1.45), half=0.26, view=(-0.3, 0.9, -0.2), pose=A['arms_up']),
        dict(center=(0, -0.1, 0.95), half=1.0, view=(-0.7, 0.7, -0.2), pose=A['elbows_knees_90']),
        dict(center=(0.1, -0.2, 0.75), half=0.5, view='left', pose=A['elbows_knees_90']),
        dict(center=(0.3, -0.2, 1.35), half=0.36, view=(-0.4, 0.8, -0.4), pose=A['elbows_knees_90']),
        dict(center=(0, -0.1, 0.62), half=0.75, view='front', pose=A['crouch']),
        dict(center=(0, -0.1, 0.62), half=0.75, view='left', pose=A['crouch']),
        dict(center=(0, -0.1, 0.62), half=0.75, view=(0.6, -0.7, -0.3), pose=A['crouch']),
        dict(center=(0, 0, 1.58), half=0.32, view='front', pose=A['head_turn']),
        dict(center=(0, 0, 1.58), half=0.32, view=(-0.7, 0.7, -0.1), pose=A['head_turn']),
        dict(center=(0, 0, 1.58), half=0.32, view='back', pose=A['head_turn']),
        dict(center=(0.36, -0.30, 1.30), half=0.20, view=(-0.2, 0.9, -0.3), pose=A['fist']),
        dict(center=(0.30, -0.22, 1.36), half=0.30, view=(0.7, 0.5, -0.5), pose=A['fist']),
    ]


def expression_tiles():
    tiles = []
    for base in ({}, {'feminine': 1.0}):
        for ex in ({}, {'blink': 1.0}, {'mouth_open': 1.0}, {'smile': 1.0}, {'angry': 1.0},
                   {'angry': 1.0, 'mouth_open': 0.8}, {'smile': 0.7, 'blink': 0.5}, {'mouth_open': 0.5, 'blink': 1.0}):
            w = dict(base)
            w.update(ex)
            tiles.append(dict(center=FACE_C, half=FACE_H, view=(-0.35, 0.93, -0.04), morphs=w))
    return tiles


# ============================================================================= 4. work-in-progress sheets
if 'head' in FLAGS:
    shots(P_('hum_head_wip.png'), objs + ws, HEAD_C, HEAD_H, ['front', V34, VPROF])
    shots(P_('hum_face_wip.png'), objs + ws, FACE_C, 0.085, ['front', V34, VPROF])
    shots(P_('hum_eye_wip.png'), objs + ws, (0.03, -0.075, 1.690), 0.034, ['front', V34, VPROF])
if 'shape' in FLAGS:
    render_tiles(P_('hum_apose_wip.png'), objs + ws, [
        dict(center=(0, 0, 0.92), half=0.98, view=v, pose=POSES['a_pose'], morphs={'muscular': 1.0}) for v in ('front', 'back')] + [
        dict(center=(0, 0, 0.92), half=0.98, view=v, pose=POSES['a_pose']) for v in ('front', 'left', 'back', 'persp')]
        + [dict(center=(0, 0, 0.92), half=0.98, view=v, pose=POSES['a_pose'], morphs={'feminine': 1.0})
           for v in ('front', 'left', 'back', 'persp')], res=(320, 448), cols=5, arm=arm)
    shots(P_('hum_body_wip.png'), objs + ws, (0, 0, 0.92), 1.0, ['front', 'left', 'back', 'persp'], cols=4)
    shots(P_('hum_torso_wip.png'), objs + ws, (0.1, 0, 1.25), 0.42,
          ['front', 'back', (-0.7, 0.7, -0.2), (0.7, -0.7, -0.2)], cols=4)
    shots(P_('hum_hand_wip.png'), objs + ws, (0.80, -0.01, 1.47), 0.12,
          [(0.0001, 0.0001, -1), (0.0001, 0.0001, 1), (-0.5, 0.7, -0.5), (0.3, 0.8, 0.5)], cols=4)
    shots(P_('hum_legs_wip.png'), objs + ws, (0.1, 0, 0.45), 0.52, ['front', 'left', 'back', (-0.7, 0.7, -0.2)], cols=4)
    shots(P_('hum_foot_wip.png'), objs + ws, (0.1, -0.06, 0.06), 0.17,
          ['left', 'right', (-0.6, 0.7, -0.4), (0.5, -0.6, -0.6)], cols=4)
if 'neck' in FLAGS:
    shots(P_('hum_neck_wip.png'), objs + ws, (0.07, 0.0, 1.47), 0.17, ['front', (-0.6, 0.75, -0.3), 'back', (0.0001, 0.0001, -1)], cols=4)
    shots(P_('hum_hand_wip.png'), objs + ws, (0.80, -0.01, 1.47), 0.12,
          [(0.0001, 0.0001, -1), (0.0001, 0.0001, 1), (-0.5, 0.7, -0.5), (0.3, 0.8, 0.5)], cols=4)
    shots(P_('hum_foot_wip.png'), objs + ws, (0.1, -0.06, 0.06), 0.17,
          ['left', 'right', (-0.6, 0.7, -0.4), (0.5, -0.6, -0.6)], cols=4)
if 'poses' in FLAGS:
    render_tiles(P_('hum_poses_wip.png'), objs + ws, pose_tiles(), res=384, cols=4, arm=arm)
if 'morphs' in FLAGS:
    render_tiles(P_('hum_presets_wip.png'), objs, preset_tiles(PRESETS), res=(320, 448), cols=6, arm=arm)
    render_tiles(P_('hum_expressions_wip.png'), objs, expression_tiles(), res=384, cols=4)
if 'each' in FLAGS:
    names = [n for n in hm.MORPH_ORDER if hm.MORPH_META[n]['category'] not in ('body', 'expression')]
    tiles = []
    for n in names:
        lo = hm.MORPH_META[n]['min']
        if lo < 0:
            tiles.append(dict(center=FACE_C, half=0.10, view=(-0.45, 0.89, -0.04), morphs={n: -1.0}))
        tiles.append(dict(center=FACE_C, half=0.10, view=(-0.45, 0.89, -0.04), morphs={n: 1.0}))
    render_tiles(P_('hum_each_head_wip.png'), objs, tiles, res=256, cols=10)
    names = [n for n in hm.MORPH_ORDER if hm.MORPH_META[n]['category'] == 'body']
    tiles = []
    for n in names:
        lo = hm.MORPH_META[n]['min']
        if lo < 0:
            tiles.append(dict(center=(0, 0, 1.05), half=0.85, view=(-0.5, 0.85, -0.1), morphs={n: -1.0}))
        tiles.append(dict(center=(0, 0, 1.05), half=0.85, view=(-0.5, 0.85, -0.1), morphs={n: 1.0}))
    render_tiles(P_('hum_each_body_wip.png'), objs, tiles, res=256, cols=8)

# ============================================================================= 5. final outputs
if 'final' in FLAGS:
    regions = []
    for rn in REGIONS:
        sel = [i for i, t in enumerate(M['ft']) if t == REGION_TAG[rn]]
        regions.append(build_body_object(rn, D, sel, arm, rn == 'body_head'))
    info, desc, js, arrays = export_human(OUT_GLB, arm, regions, extras)
    bc = border_check(js, arrays)
    print('BORDER_CHECK', json.dumps(bc))
    for r in regions:
        r.hide_render = True
    # ---- final preview sheets
    shots(P_('hum_body.png'), objs, (0, 0, 0.92), 1.0, ['front', 'left', 'back', 'persp'], cols=4)
    render_tiles(P_('hum_head.png'), objs, [
        dict(center=HEAD_C, half=HEAD_H, view='front'), dict(center=HEAD_C, half=HEAD_H, view=V34),
        dict(center=HEAD_C, half=HEAD_H, view=VPROF),
        dict(center=HEAD_C, half=HEAD_H, view='front', morphs={'feminine': 1.0}),
        dict(center=HEAD_C, half=HEAD_H, view=V34, morphs={'feminine': 1.0}),
        dict(center=HEAD_C, half=HEAD_H, view=VPROF, morphs={'feminine': 1.0})], res=512, cols=3)
    render_tiles(P_('hum_presets.png'), objs, preset_tiles(PRESETS), res=(320, 448), cols=6, arm=arm)
    render_tiles(P_('hum_expressions.png'), objs, expression_tiles(), res=384, cols=4)
    render_tiles(P_('hum_poses.png'), objs, pose_tiles(), res=384, cols=4, arm=arm)
    # ---- manifest
    H = SDFS['head']
    ring = []
    for k in range(24):
        a = math.radians(15.0 * k)
        zr = 1.725 + 0.020 * math.cos(a)
        pt, ok = H.ray([[0, 0.01, zr]], [[math.sin(a), -math.cos(a), 0]], 0.2)
        ring.append([round(float(v), 4) for v in pt[0]])
    rl = sum(float(np.linalg.norm(np.array(ring[k]) - np.array(ring[(k + 1) % 24]))) for k in range(24))
    bt = {b['name']: b for b in bone_table()}
    R3 = lambda v: [round(float(x), 4) for x in v]
    joints = {}
    for nm, bn in (('shoulder', 'upper_arm'), ('elbow', 'forearm'), ('wrist', 'hand'), ('hip', 'thigh'),
                   ('knee', 'shin'), ('ankle', 'foot')):
        for sfx in ('L', 'R'):
            joints['%s_%s' % (nm, sfx)] = R3(bt['%s_%s' % (bn, sfx)]['head'])
    er = LM['eye_radius']
    landmarks = {
        'coordinates': 'Blender rest pose (T-pose): X = character left, -Y = front, Z = up, meters. glTF/three.js = (x, z, -y)',
        'eye_center_L': R3(LM['eye_L']), 'eye_center_R': R3(LM['eye_R']), 'eye_radius': er,
        'pupil_L': R3((LM['eye_L'][0], LM['eye_L'][1] - er, LM['eye_L'][2])),
        'pupil_R': R3((LM['eye_R'][0], LM['eye_R'][1] - er, LM['eye_R'][2])),
        'mouth_center': R3(LM['mouth']), 'mouth_corner_L': R3(LM['mouth_corner']), 'chin': R3(LM['chin']),
        'chin_bottom': R3(LM['menton']), 'nose_tip': R3(LM['nose_tip']), 'brow_L': R3(LM['brow']),
        'top_of_head': R3(LM['head_top']),
        'crown_ring': ring, 'crown_ring_length': round(rl, 4),
        'crown_ring_note': '24 points every 15 degrees starting at the front (forehead above the brows) going to the character left; tilted hat line, use it to fit hair caps, crowns, helmets',
        'ear_L': R3(LM['ear_L']), 'ear_R': R3(LM['ear_R']), 'ear_top_L': R3(LM['ear_top']),
        'neck_base': R3(LM['neck_base']), 'head_pivot': R3(LM['head_pivot']),
        'jaw_hinge_L': R3(LM['jaw_hinge']),
        'hand_grip_L': R3(bt['weapon_L']['head']), 'hand_grip_R': R3(bt['weapon_R']['head']),
    }
    landmarks.update(joints)
    meshes = []
    for d in desc:
        meshes.append({'name': d['mesh'], 'triangles': d['tris'], 'vertices': d['verts'], 'materials': [d['material']],
                       'attributes': d['attrs'], 'morph_targets': d['targets']})
    body_tris = sum(d['tris'] for d in desc if d['mesh'] in REGIONS)
    manifest = {
        'asset': 'human',
        'file': 'human.glb',
        'description': 'Base human body (male base, T-pose, 1.80 m) skinned to the shared 40 bone humanoid rig, '
                       'split in 6 hideable regions, with eyes, brows, mouth interior and 50 morph targets.',
        'size_m': {'width': round(float(P32[:, 0].max() - P32[:, 0].min()), 3),
                   'depth': round(float(P32[:, 1].max() - P32[:, 1].min()), 3),
                   'height': round(float(P32[:, 2].max()), 3)},
        'triangles': {'total': sum(d['tris'] for d in desc), 'body': body_tris},
        'skin': {'joints': 40, 'max_influences': 4, 'armature': 'Armature (tools/blender/humanoid_rig.py)'},
        'regions': REGIONS,
        'region_notes': {
            'body_head': 'head, ears, neck down to the collar line',
            'body_torso': 'collar to hip line (z = 1.00 m), shoulders to mid deltoid (|x| = 0.205 m)',
            'body_arms': 'mid deltoid to wrist (|x| = 0.727 m)',
            'body_hands': 'wrist to finger tips',
            'body_legs': 'hip line to ankle (z = 0.105 m), includes hips and crotch',
            'body_feet': 'below the ankle',
            'borders': 'border vertices are duplicated in both regions with identical position, normal, weights, '
                       'colour and morph deltas (normals and morph normals are recomputed on the welded body).'},
        'meshes': meshes,
        'morphs': [hm.MORPH_META[n] for n in hm.MORPH_ORDER],
        'morph_notes': {
            'order': 'every mesh carries the same 50 targets in this order (zero deltas where unaffected)',
            'negative': 'weights down to min are valid: negative = linear opposite',
            'eyes': 'eye_L / eye_R follow every morph except the expressions (blink, mouth_open, smile, angry)',
            'feminine': 'female body type on the same skeleton; suggested extra root scale 0.94 for an average woman',
            'fields': 'tools/blender/human_morphs.py exposes MORPHS[name](points Nx3) -> deltas, the same analytic '
                      'fields can be evaluated on hair / outfits / props',
            'jaw_open_deg': hm.JAW_OPEN_DEG},
        'vertex_colors': {'attribute': 'COLOR_0 (linear)', 'R': 'blush mask (cheeks 0.35, nose tip, ears, knuckles, '
                          'elbows, knees 0.25)', 'G': 'ambient occlusion / cavity (1 = open); the upper eyelid margin '
                          'is darkened on purpose (lash line)', 'B': 'lips mask', 'A': '1',
                          'note': 'only meaningful on M_skin. eyes and brows are white; M_mouth uses COLOR_0 as albedo'},
        'uv': {'TEXCOORD_0': 'skin: cylindrical / planar projections, about 0.5 m per UV unit (tiling pore detail, '
                             'seams between body parts). eyes: planar from the front, pupil at (0.5, 0.5), the '
                             'eyeball silhouette fills 0..1',
               'TEXCOORD_1': 'body_head only: planar projection from the front for decals (war paint, scars). '
                             'u = 0.5 + x / %.4f (u=0 at the character RIGHT ear, u=1 at the LEFT ear, i.e. the '
                             'image is the face as seen from the front), v = (z - %.4f) / %.4f (0 = under the chin, '
                             '1 = top of the forehead). Blender convention (v up); the back of the head mirrors the '
                             'front, mask decals with the normal.' % (2 * X_EAR, UV1_Z0, UV1_Z1 - UV1_Z0)},
        'materials': {
            'M_skin': 'contract material (engine skin shader: skin tone uniform + COLOR_0 masks)',
            'M_eye': 'contract material (engine eye shader), mesh eye_L / eye_R',
            'M_hair': 'contract material, mesh brows = eyebrows + upper eyelashes (thin double sided strips that '
                      'follow blink; the feminine morph lengthens them), vertex colour white, UV u along / v across',
            'M_mouth': 'NEW: mouth interior and teeth. Opaque, single sided, albedo = COLOR_0 (dark red cavity, '
                       'pink tongue area, ivory teeth), roughness about 0.45, no texture. Only visible when '
                       'mouth_open > 0.'},
        'landmarks': landmarks,
        'previews': ['tools/previews/hum_body.png', 'tools/previews/hum_head.png', 'tools/previews/hum_presets.png',
                     'tools/previews/hum_expressions.png', 'tools/previews/hum_poses.png'],
        'presets_shown_in_previews': {nm: w for nm, w in PRESETS},
    }
    os.makedirs(os.path.dirname(OUT_MANIFEST), exist_ok=True)
    with open(OUT_MANIFEST, 'w', encoding='utf8') as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print('MANIFEST', OUT_MANIFEST)
    # ---- blend file for the outfit / hair artist
    for nm in ('pv_cam', 'pv_key', 'pv_fill', 'pv_rim'):
        o = bpy.data.objects.get(nm)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    set_morphs(objs + regions, {})
    set_pose(arm, {})
    for r in regions:
        r.hide_render = False
        r.hide_set(True)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    if os.path.exists(OUT_BLEND + '1'):
        os.remove(OUT_BLEND + '1')
    print('SAVED', OUT_BLEND)
print('DONE %.1f s' % (time.time() - T0))
