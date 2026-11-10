"""Shared helpers for every Blender asset script of VALOMBRE (Blender 5.1, headless).

Run scripts with:
  "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" -b --factory-startup -P tools/blender/<script>.py

In a script:
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
  from blcommon import *

Conventions (ALL assets):
  * Units = meters. Blender Z up. Characters/creatures/buildings FRONT faces -Y (Blender front view).
  * Origin of every asset = center of its footprint ON THE GROUND (z = 0).
  * Exported as .glb with +Y up (glTF). Blender (x, y, z) -> glTF/three.js (x, z, -y).
  * Materials are matched BY NAME by the game engine (the engine replaces them with its own PBR
    materials), so material names are a contract. Colors set here are only used for previews and as a
    fallback tint.
  * No image textures inside .glb unless a brief says so.
"""
import bpy, bmesh, os, sys, math, zlib, struct, json, tempfile, random
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ASSETS = os.path.join(ROOT, 'assets')
MODELS = os.path.join(ASSETS, 'models')
TEXTURES = os.path.join(ASSETS, 'textures')
PREVIEWS = os.path.join(ROOT, 'tools', 'previews')
for _d in (ASSETS, MODELS, TEXTURES, PREVIEWS):
    os.makedirs(_d, exist_ok=True)


# ----------------------------------------------------------------------------- scene
def reset_scene():
    """Empty scene, metric units, 30 fps."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.render.fps = 30
    return sc


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_mesh_object(name, verts, faces, edges=(), smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [tuple(e) for e in edges], [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


def bmesh_to_object(bm, name, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


def select_only(objs, active=None):
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def apply_modifiers(obj):
    select_only(obj)
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as e:  # e.g. disabled modifier
            print('modifier_apply failed', obj.name, m.name, e)
            obj.modifiers.remove(m)


def apply_transforms(obj, location=True, rotation=True, scale=True):
    select_only(obj)
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)


def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        if name:
            objs[0].name = name
        return objs[0]
    select_only(objs, objs[0])
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if name:
        ob.name = name
        ob.data.name = name
    return ob


def tri_count(objs):
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        n += len(me.loop_triangles)
        o.evaluated_get(dg).to_mesh_clear()
    return n


# ----------------------------------------------------------------------------- materials
def make_mat(name, color=(0.8, 0.8, 0.8), rough=0.7, metal=0.0, emissive=None, emissive_strength=1.0,
             use_vertex_color=False, alpha=1.0):
    """Create (or fetch) a Principled material. The NAME is what the game engine keys on."""
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = None
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
    if bsdf is None:
        nt.nodes.clear()
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Alpha'].default_value = alpha
    if emissive is not None:
        bsdf.inputs['Emission Color'].default_value = (emissive[0], emissive[1], emissive[2], 1.0)
        bsdf.inputs['Emission Strength'].default_value = emissive_strength
    if use_vertex_color:
        vc = nt.nodes.new('ShaderNodeVertexColor')
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        mix.inputs[6].default_value = (color[0], color[1], color[2], 1.0)
        nt.links.new(vc.outputs['Color'], mix.inputs[7])
        nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


def assign_mat(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def set_vertex_colors(obj, fn, name='Col'):
    """fn(world_position: Vector, normal: Vector, vertex_index) -> (r, g, b[, a]) in LINEAR 0..1.
    Stored as a per-corner FLOAT_COLOR attribute that the glTF exporter writes as COLOR_0."""
    me = obj.data
    attr = me.color_attributes.get(name) or me.color_attributes.new(name, 'FLOAT_COLOR', 'CORNER')
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = list(me.color_attributes).index(attr)
    mw = obj.matrix_world
    cache = {}
    for li, loop in enumerate(me.loops):
        vi = loop.vertex_index
        c = cache.get(vi)
        if c is None:
            v = me.vertices[vi]
            c = fn(mw @ v.co, v.normal, vi)
            if len(c) == 3:
                c = (c[0], c[1], c[2], 1.0)
            cache[vi] = c
        attr.data[li].color = c
    return attr


# ----------------------------------------------------------------------------- color / uv / skinning helpers
def lin(c):
    """sRGB -> linear. Accepts '#rrggbb' or an (r, g, b) tuple in 0..1 sRGB. Vertex colors and make_mat
    colors are LINEAR, so wrap every color you pick by eye:  lin('#8a6a4b')."""
    if isinstance(c, str):
        c = c.lstrip('#')
        c = tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c[:3])


def box_uv(obj, tile=2.0, rotate_faces=None):
    """World-scale box-projected UVs: 1 UV unit = `tile` meters. Faces are projected along their dominant
    normal axis. Vertical faces get u = horizontal distance, v = height (z).
    rotate_faces: optional function(face_normal: Vector, face_center: Vector) -> bool; True = swap u/v
    (rotate the texture 90 degrees on that face, e.g. horizontal beams / planks)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.verify()
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    for f in bm.faces:
        n = (nm @ f.normal).normalized()
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        rot = bool(rotate_faces(n, mw @ f.calc_center_median())) if rotate_faces else False
        for l in f.loops:
            p = mw @ l.vert.co
            if az >= ax and az >= ay:
                u, v = p.x, p.y
            elif ax >= ay:
                u, v = (p.y if n.x > 0 else -p.y), p.z
            else:
                u, v = (-p.x if n.y > 0 else p.x), p.z
            if rot:
                u, v = v, u
            l[uvl].uv = (u / tile, v / tile)
    bm.to_mesh(me)
    bm.free()


def auto_weights(mesh_objs, arm_obj):
    """Parent meshes to the armature with automatic (bone heat) weights. Returns True on success.
    Falls back to envelope weights when bone heat fails (non manifold meshes)."""
    if not isinstance(mesh_objs, (list, tuple)):
        mesh_objs = [mesh_objs]
    select_only(list(mesh_objs) + [arm_obj], arm_obj)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    ok = True
    for o in mesh_objs:
        if not any(len(v.groups) for v in o.data.vertices):
            ok = False
    if not ok:
        select_only(list(mesh_objs) + [arm_obj], arm_obj)
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
    return ok


def rigid_weights(mesh_obj, arm_obj, bone_name):
    """Skin a whole mesh 100% to one bone (hair on head, a plate on a forearm...)."""
    vg = mesh_obj.vertex_groups.get(bone_name) or mesh_obj.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(mesh_obj.data.vertices))), 1.0, 'REPLACE')
    if not any(m.type == 'ARMATURE' for m in mesh_obj.modifiers):
        mod = mesh_obj.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm_obj
    mesh_obj.parent = arm_obj


def limit_weights(mesh_obj, n=4):
    """glTF wants <= 4 influences per vertex, normalized."""
    select_only(mesh_obj)
    try:
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=n)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    except Exception as e:
        print('limit_weights failed', e)


def add_empty(name, location, parent=None, rotation=(0, 0, 0), size=0.2):
    """Marker exported as an empty glTF node (anchors such as FIRE_*, ANCHOR_*, ...)."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.location = location
    e.rotation_euler = rotation
    link(e)
    if parent:
        e.parent = parent
    return e


def add_collider_box(name, center, size, rot_z=0.0, parent=None):
    """Invisible collision proxy: a box mesh named COL_<name>. The engine reads its transform + bounds,
    builds an oriented box collider from it and does not render it."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    ob = bmesh_to_object(bm, 'COL_' + name, smooth=False)
    ob.location = center
    ob.scale = size
    ob.rotation_euler = (0, 0, rot_z)
    ob.display_type = 'WIRE'
    ob.hide_render = True
    if parent:
        ob.parent = parent
    return ob


# ----------------------------------------------------------------------------- PNG io (no color management)
def save_png(path, arr):
    """arr: HxW, HxWx3 or HxWx4. float (0..1) or uint8. Row 0 = TOP of the image. Bytes are written as is."""
    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    if arr.ndim == 2:
        arr = arr[:, :, None]
    h, w, c = arr.shape
    ctype = {1: 0, 2: 4, 3: 2, 4: 6}[c]
    raw = np.empty((h, w * c + 1), np.uint8)
    raw[:, 0] = 0
    raw[:, 1:] = arr.reshape(h, w * c)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw.tobytes(), 6)) + chunk(b'IEND', b''))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(png)


def load_image(path):
    """Load any image as float32 HxWx4 array, row 0 = top (values as stored, sRGB for 8-bit files)."""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1].copy()


def montage(images, cols=4, pad=4, bg=0.1):
    """Tile HxWxC float arrays (same size) into one sheet."""
    h, w = images[0].shape[:2]
    rows = int(math.ceil(len(images) / cols))
    sheet = np.full((rows * (h + pad) + pad, cols * (w + pad) + pad, 3), bg, np.float32)
    for i, im in enumerate(images):
        r, c = divmod(i, cols)
        y, x = pad + r * (h + pad), pad + c * (w + pad)
        sheet[y:y + h, x:x + w] = im[:, :, :3]
    return sheet


# ----------------------------------------------------------------------------- preview rendering
VIEW_DIRS = {
    # direction the camera LOOKS along
    'front': Vector((0, 1, 0)),          # camera in front of the character (which faces -Y)
    'back': Vector((0, -1, 0)),
    'left': Vector((-1, 0, 0)),          # camera on the character's left (+X) side
    'right': Vector((1, 0, 0)),
    'top': Vector((0.0001, 0.0001, -1)),
    'persp': Vector((-0.55, 0.75, -0.38)),
    'persp_back': Vector((0.55, -0.75, -0.38)),
    'low': Vector((-0.35, 0.9, 0.18)),
}


def _bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != 'MESH':
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        n = len(me.vertices)
        if n:
            co = np.empty(n * 3, np.float32)
            me.vertices.foreach_get('co', co)
            co = co.reshape(n, 3)
            M = np.array(oe.matrix_world, dtype=np.float32)
            wco = co @ M[:3, :3].T + M[:3, 3]
            a, b = wco.min(0), wco.max(0)
            mn = Vector((min(mn.x, a[0]), min(mn.y, a[1]), min(mn.z, a[2])))
            mx = Vector((max(mx.x, b[0]), max(mx.y, b[1]), max(mx.z, b[2])))
        oe.to_mesh_clear()
    return mn, mx


def setup_preview(res=384, bg=(0.16, 0.18, 0.22), ground=False):
    """Camera + 3-point lighting for EEVEE previews. Returns the camera object."""
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    if isinstance(res, int):
        res = (res, res)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.media_type = 'IMAGE'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    try:
        sc.eevee.taa_render_samples = 8
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    world = bpy.data.worlds.get('pv_world') or bpy.data.worlds.new('pv_world')
    sc.world = world
    world.use_nodes = True
    bgn = world.node_tree.nodes.get('Background')
    if bgn:
        bgn.inputs[0].default_value = (bg[0], bg[1], bg[2], 1)
        bgn.inputs[1].default_value = 1.0
    cam = bpy.data.objects.get('pv_cam')
    if cam is None:
        cam = bpy.data.objects.new('pv_cam', bpy.data.cameras.new('pv_cam'))
        link(cam)
        for nm, energy, rot in (('pv_key', 2.4, (math.radians(50), 0, math.radians(-35))),
                                ('pv_fill', 0.7, (math.radians(65), 0, math.radians(120))),
                                ('pv_rim', 1.2, (math.radians(-60), 0, math.radians(200)))):
            ld = bpy.data.lights.new(nm, 'SUN')
            ld.energy = energy
            lo = bpy.data.objects.new(nm, ld)
            lo.rotation_euler = rot
            link(lo)
    cam.data.lens = 60
    cam.data.clip_start = 0.02
    cam.data.clip_end = 5000
    sc.camera = cam
    return cam


def frame_camera(cam, mn, mx, view='persp', margin=1.12):
    d = VIEW_DIRS[view].normalized() if isinstance(view, str) else Vector(view).normalized()
    center = (mn + mx) * 0.5
    radius = max((mx - mn).length * 0.5, 0.01)
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    fov = 2 * math.atan(18.0 / cam.data.lens)       # horizontal fov, 36mm sensor
    if aspect > 1:
        fov = 2 * math.atan(math.tan(fov / 2) / aspect)
    dist = radius * margin / math.sin(fov / 2)
    cam.location = center - d * dist
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render_to_array(path=None):
    sc = bpy.context.scene
    tmp = path or os.path.join(tempfile.gettempdir(), 'valombre_pv_%d.png' % os.getpid())
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    return load_image(tmp)


def render_sheet(path, objs, views=('front', 'left', 'back', 'persp'), res=384, cols=4, frames=None,
                 fixed_bounds=None):
    """Render a contact sheet PNG of `objs` (list of objects; armatures are skipped for bounds).
    views: names from VIEW_DIRS or direction vectors.
    frames: optional list of frame numbers -> every (frame, view) pair is rendered (use ONE view for
    animation strips). fixed_bounds=(min Vector, max Vector) keeps the framing constant over frames."""
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    cam = setup_preview(res)
    sc = bpy.context.scene
    imgs = []
    for fr in (frames or [sc.frame_current]):
        sc.frame_set(int(fr))
        bpy.context.view_layer.update()
        mn, mx = fixed_bounds if fixed_bounds else _bounds(objs)
        for v in views:
            frame_camera(cam, mn, mx, v)
            imgs.append(render_to_array())
    save_png(path, montage(imgs, cols=cols))
    print('PREVIEW', path)
    return path


# ----------------------------------------------------------------------------- animation helpers
def new_action(arm_obj, name):
    """Create a fresh action, make it the armature's active action and reset the pose."""
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm_obj.animation_data.action = act
    for pb in arm_obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    return act


def actions_to_nla(arm_obj, actions):
    """Put every action on its own NLA track (track name = clip name). Call once before export_glb(anims=True)."""
    ad = arm_obj.animation_data
    ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    for act in actions:
        tr = ad.nla_tracks.new()
        tr.name = act.name
        st = tr.strips.new(act.name, int(act.frame_range[0]), act)
        st.name = act.name
        tr.mute = True
    for pb in arm_obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)


# ----------------------------------------------------------------------------- export
def export_glb(path, objs, anims=False, skins=None, morphs=False, vcol=True, apply_mods=True):
    """Export the given objects (and nothing else) to a .glb.
    anims=True  -> exports every NLA track as one animation (use actions_to_nla first).
    morphs=True -> exports shape keys as morph targets (modifiers are then NOT applied by the exporter)."""
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    if skins is None:
        skins = any(o.type == 'ARMATURE' for o in objs)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True,
        export_apply=bool(apply_mods and not morphs),
        export_cameras=False, export_lights=False, export_extras=True,
        export_texcoords=True, export_normals=True, export_tangents=False,
        export_materials='EXPORT', export_image_format='AUTO',
        export_vertex_color='ACTIVE' if vcol else 'NONE', export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=True,
        export_skins=bool(skins), export_all_influences=False, export_influence_nb=4,
        export_def_bones=False, export_rest_position_armature=True,
        export_morph=bool(morphs), export_morph_normal=bool(morphs), export_morph_tangent=False,
        export_animations=bool(anims), export_animation_mode='NLA_TRACKS',
        export_force_sampling=True, export_frame_step=1, export_bake_animation=False,
        export_optimize_animation_size=True, export_optimize_animation_keep_anim_armature=True,
        export_anim_slide_to_zero=True, export_reset_pose_bones=True, export_negative_frame='SLIDE',
        export_morph_animation=False,
    )
    info = glb_info(path)
    print('EXPORTED', os.path.relpath(path, ROOT), json.dumps(info['summary']))
    return info


def glb_info(path):
    """Parse a .glb and return a dict describing meshes / skins / animations (no dependencies)."""
    with open(path, 'rb') as f:
        data = f.read()
    magic, ver, length = struct.unpack_from('<4sII', data, 0)
    clen, ctype = struct.unpack_from('<II', data, 12)
    js = json.loads(data[20:20 + clen].decode('utf8'))
    acc = js.get('accessors', [])
    meshes = []
    tris = 0
    for m in js.get('meshes', []):
        prims = []
        for p in m['primitives']:
            nv = acc[p['attributes']['POSITION']]['count']
            ni = acc[p['indices']]['count'] if 'indices' in p else nv
            tris += ni // 3
            mat = js['materials'][p['material']]['name'] if 'material' in p else None
            prims.append({'verts': nv, 'tris': ni // 3, 'material': mat, 'attrs': sorted(p['attributes'].keys()),
                          'targets': len(p.get('targets', []))})
        meshes.append({'name': m.get('name'), 'prims': prims,
                       'targetNames': (m.get('extras') or {}).get('targetNames')})
    anims = []
    for a in js.get('animations', []):
        tmax = 0.0
        for s in a['samplers']:
            tmax = max(tmax, acc[s['input']].get('max', [0])[0])
        anims.append({'name': a.get('name'), 'duration': round(tmax, 3), 'channels': len(a['channels'])})
    skins = [{'name': s.get('name'), 'joints': len(s['joints'])} for s in js.get('skins', [])]
    nodes = [n.get('name') for n in js.get('nodes', [])]
    return {'meshes': meshes, 'animations': anims, 'skins': skins, 'nodes': nodes,
            'materials': [m.get('name') for m in js.get('materials', [])],
            'summary': {'bytes': len(data), 'tris': tris, 'meshes': len(meshes),
                        'materials': [m.get('name') for m in js.get('materials', [])],
                        'skins': skins, 'animations': [(a['name'], a['duration']) for a in anims]}}
