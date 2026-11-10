"""Shared helpers for the humanoid monsters of VALOMBRE (skeleton, troll, golem).

  * brute_warp(): proportions of the troll / golem on the shared humanoid rig (bone directions untouched).
  * Clips: reads assets/models/char/humanoid_anims.glb (the real shared clips) and replays any clip at any
    time on ANY armature built from the shared rig, by bone name, the way the engine does it: the track's
    absolute local rotation is applied to the bone, the hips translation is multiplied by the hips-height
    ratio. Used to test deformation with real game poses.
  * export / verification / preview helpers.
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gear_parts import *
from humanoid_rig import *

CREATURES = os.path.join(MODELS, 'creatures')
ANIMS = os.path.join(MODELS, 'char', 'humanoid_anims.glb')
HUMAN_HIPS = 0.98


# ----------------------------------------------------------------------------- rig proportions
def rest_points(warp=None):
    """{bone: (head, tail)} of the rest pose, exactly as build_humanoid_armature(warp=...) builds it."""
    out = {}
    for b in bone_table():
        h, t = b['head'].copy(), b['tail'].copy()
        if warp:
            h, t = Vector(warp(b['name'], h.copy())), Vector(warp(b['name'], t.copy()))
        out[b['name']] = (h, t)
    return out


def brute_warp(S=1.0):
    """Mountain-troll proportions (3.0 m at S = 1): long heavy arms, short legs, wide hips and shoulders, the
    head set low and forward. Every bone keeps EXACTLY its human direction (new_tail = new_head + human
    direction * new length), so the rest orientations stay those of the shared rig."""
    HUM = {b['name']: (b['head'], b['tail']) for b in bone_table()}
    K_HAND = 2.7
    wrist_h = Vector((0.73, 0, 1.47))
    wrist_t = Vector((1.92, 0, 2.28))
    # name: (new head (left side / centre), new length)
    T = {
        'root': ((0, 0, 0), 0.16),
        'hips': ((0, 0, 1.16), 0.18),
        'spine_01': ((0, 0, 1.34), 0.26),
        'spine_02': ((0, 0, 1.60), 0.30),
        'spine_03': ((0, 0, 1.90), 0.36),
        'neck': ((0, -0.22, 2.20), 0.16),
        'head': ((0, -0.238, 2.36), 0.40),
        'sheath_back': ((-0.45, 0.50, 2.50), 0.16),
        'sheath_hip': ((0.52, -0.10, 1.20), 0.16),
        'clavicle': ((0.10, 0.0, 2.24), 0.50),
        'upper_arm': ((0.64, 0.0, 2.28), 0.66),
        'forearm': ((1.30, 0.0, 2.28), 0.62),
        'hand': ((1.92, 0.0, 2.28), 0.216),
        'thigh': ((0.26, 0.0, 1.10), 0.50),
        'shin': (None, 0.44),
        'foot': (None, 0.2636),
        'toe': (None, 0.22),
        'shield': ((1.61, 0.0, 2.41), 0.27),
    }
    cache = {}

    def solve(name):
        if name in cache:
            return cache[name]
        base, side = name, None
        if name[-2:] in ('_L', '_R'):
            base, side = name[:-2], name[-1]
        sx = -1.0 if side == 'R' else 1.0
        hh, ht = HUM[name]
        d = (ht - hh).normalized()
        if base in ('thumb_01', 'thumb_02', 'index_01', 'index_02', 'fingers_01', 'fingers_02', 'weapon'):
            # similarity about the wrist: big hands, same finger layout
            def m(p):
                q = Vector((abs(p.x), p.y, p.z)) - wrist_h
                r = wrist_t + q * K_HAND
                return Vector((r.x * (1 if p.x >= 0 else -1), r.y, r.z))
            res = (m(hh) * S, m(ht) * S)
        else:
            key = base if base in T else name
            head, ln = T[key]
            if head is None:
                parent = {'shin': 'thigh', 'foot': 'shin', 'toe': 'foot'}[base] + '_' + side
                h = solve(parent)[1] / S
            else:
                h = Vector(head)
                if side is not None or key == 'shield':
                    if name in ('shield_L',):
                        sx = 1.0
                    h = Vector((h.x * sx, h.y, h.z))
            res = (h * S, (h + d * ln) * S)
        cache[name] = res
        return res

    def warp(name, p):
        hh, ht = HUM[name]
        h, t = solve(name)
        return h.copy() if (Vector(p) - hh).length <= (Vector(p) - ht).length else t.copy()

    return warp


# ----------------------------------------------------------------------------- real clips
class Clips:
    def __init__(self, path=ANIMS):
        data = open(path, 'rb').read()
        jlen, = struct.unpack_from('<I', data, 12)
        js = json.loads(data[20:20 + jlen].decode('utf8'))
        bin0 = 20 + jlen + 8
        nodes = js['nodes']

        def acc(i):
            a = js['accessors'][i]
            bv = js['bufferViews'][a['bufferView']]
            off = bin0 + bv.get('byteOffset', 0) + a.get('byteOffset', 0)
            nc = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
            arr = np.frombuffer(data, dtype='<f4', count=a['count'] * nc, offset=off).astype(np.float64)
            return arr.reshape(a['count'], nc) if nc > 1 else arr

        self.rest = {n['name']: (n.get('rotation', [0, 0, 0, 1]), n.get('translation', [0, 0, 0])) for n in nodes if 'name' in n}
        self.clips, self.dur = {}, {}
        for an in js.get('animations', []):
            ch, tmax = {}, 0.0
            for c in an['channels']:
                s = an['samplers'][c['sampler']]
                tt, vv = acc(s['input']), acc(s['output'])
                ch[(nodes[c['target']['node']]['name'], c['target']['path'])] = (tt, vv)
                tmax = max(tmax, float(tt[-1]))
            self.clips[an['name']] = ch
            self.dur[an['name']] = tmax
        meta = os.path.splitext(path)[0] + '.json'
        self.meta = json.load(open(meta)).get('clips', {}) if os.path.exists(meta) else {}

    @staticmethod
    def _interp(tt, vv, t, quat):
        if t <= tt[0]:
            return vv[0]
        if t >= tt[-1]:
            return vv[-1]
        i = int(np.searchsorted(tt, t)) - 1
        u = (t - tt[i]) / max(tt[i + 1] - tt[i], 1e-9)
        a, b = vv[i], vv[i + 1]
        if quat and float(np.dot(a, b)) < 0:
            b = -b
        v = a + (b - a) * u
        if quat:
            v = v / np.linalg.norm(v)
        return v

    def hit_time(self, clip):
        ev = self.meta.get(clip, {}).get('events', {})
        h = ev.get('hit')
        if isinstance(h, list):
            return float(h[0]) + 0.02
        if isinstance(h, (int, float)):
            return float(h)
        return self.dur[clip] * 0.5

    def apply(self, arm, clip, t, ratio=1.0):
        """Pose `arm` like the engine would: absolute local rotations from the track, hips translation * ratio."""
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
        for (bone, path), (tt, vv) in self.clips[clip].items():
            if bone not in arm.pose.bones:
                continue
            b = arm.data.bones[bone]
            pb = arm.pose.bones[bone]
            RL = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy()
            rq = RL.to_quaternion()
            if path == 'rotation':
                v = self._interp(tt, vv, t, True)
                pb.rotation_quaternion = rq.inverted() @ Quaternion((v[3], v[0], v[1], v[2]))
            elif path == 'translation':
                v = self._interp(tt, vv, t, False)
                pb.location = rq.inverted() @ (Vector(v) * ratio - RL.translation)
        bpy.context.view_layer.update()

    def rest_mismatch(self, arm):
        """Largest angle (degrees) between a bone's rest local rotation and the one of the shared clips file."""
        worst, wname = 0.0, None
        for b in arm.data.bones:
            if b.parent is None or b.name not in self.rest:
                continue
            rq = (b.parent.matrix_local.inverted() @ b.matrix_local).to_quaternion()
            r = self.rest[b.name][0]
            q = Quaternion((r[3], r[0], r[1], r[2]))
            ang = math.degrees(rq.rotation_difference(q).angle)
            if ang > 180:
                ang = 360 - ang
            if ang > worst:
                worst, wname = ang, b.name
        return worst, wname


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


# ----------------------------------------------------------------------------- previews
def render_rest(name, objs, res=448):
    return render_sheet(os.path.join(PREVIEWS, 'mon_%s.png' % name), objs,
                        views=('front', 'left', 'back', (-0.6, 0.72, -0.25), (0.55, -0.75, -0.3)), res=res, cols=5)


def render_closeups(name, objs, boxes, res=448):
    """boxes: [(min, max, view)...] -> tools/previews/mon_<name>_zoom.png"""
    cam = setup_preview(res)
    imgs = []
    for mn, mx, view in boxes:
        frame_camera(cam, Vector(mn), Vector(mx), view, 1.0)
        imgs.append(render_to_array()[:, :, :3])
    path = os.path.join(PREVIEWS, 'mon_%s_zoom.png' % name)
    save_png(path, montage(imgs, cols=min(5, len(imgs))))
    print('PREVIEW', path)


def render_poses(name, arm, objs, clips, shots, ratio, res=400, views=((-0.55, 0.78, -0.22), 'left'), extra=None, suffix='poses'):
    """shots: [(clip, time or None (= hit time))...]. One column per shot, one row per view."""
    cam = setup_preview(res)
    rows = [[] for _ in views]
    for clip, t in shots:
        if clip not in clips.clips:
            print('MISSING CLIP', clip)
            continue
        tt = clips.hit_time(clip) if t is None else (t if t >= 0 else clips.dur[clip] + t)
        clips.apply(arm, clip, tt, ratio)
        if extra:
            extra(clip, tt)
        mn, mx = mesh_bounds(objs)
        for r, v in enumerate(views):
            frame_camera(cam, mn, mx, v, 1.02)
            rows[r].append(render_to_array()[:, :, :3])
    imgs = [im for row in rows for im in row]
    path = os.path.join(PREVIEWS, 'mon_%s_%s.png' % (name, suffix))
    save_png(path, montage(imgs, cols=len(rows[0])))
    print('PREVIEW', path)
    reset_pose(arm)


# ----------------------------------------------------------------------------- export
def export_monster(name, arm, mesh, clips=None, max_tris=9000, extra=None):
    """Export armature + skinned mesh, verify the summary, return the humanoid_monsters.json entry."""
    reset_pose(arm)
    loose = [v.index for v in mesh.data.vertices if not v.groups]
    if loose:
        print('MONSTER %s: %d vertices without weights -> hips' % (name, len(loose)))
        (mesh.vertex_groups.get('hips') or mesh.vertex_groups.new(name='hips')).add(loose, 1.0, 'REPLACE')
    limit_weights(mesh, 4)
    path = os.path.join(CREATURES, name + '.glb')
    info = export_glb(path, [arm, mesh])
    s = info['summary']
    prims = [p for m in info['meshes'] for p in m['prims']]
    col = all('COLOR_0' in p['attrs'] for p in prims)
    skin = all('JOINTS_0' in p['attrs'] and 'WEIGHTS_0' in p['attrs'] for p in prims)
    joints = s['skins'][0]['joints'] if s['skins'] else 0
    mn, mx = mesh_bounds([mesh])
    B = arm.data.bones

    def gl(v):          # Blender (x, y, z) -> glTF / three.js (x, z, -y)
        return [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]

    rest = {k: gl(B[k].head_local) for k in ('hips', 'head', 'hand_R', 'hand_L', 'foot_L', 'foot_R', 'weapon_R', 'shield_L')}
    mism = clips.rest_mismatch(arm) if clips else (None, None)
    entry = dict(file=name + '.glb', height=round(mx.z, 3), hipsHeight=round(B['hips'].head_local.z, 4),
                 hipsRatio=round(B['hips'].head_local.z / HUMAN_HIPS, 4),
                 shoulderWidth=round(abs(B['upper_arm_L'].head_local.x - B['upper_arm_R'].head_local.x), 3),
                 triangles=s['tris'], materials=s['materials'], joints=joints,
                 bboxMin=gl(mn), bboxMax=gl(mx), restSpace='glTF / three.js axes (x = character left, y up, z = front), meters, armature at the origin',
                 rest=rest)
    if extra:
        entry.update(extra)
    ok = col and skin and joints == 40 and s['tris'] <= max_tris
    print('MONSTER %-9s tris %d/%d  joints %d  COLOR_0 %s  skin %s  mats %s  height %.3f  hips %.3f  restMismatch %s -> %s' % (
        name, s['tris'], max_tris, joints, col, skin, s['materials'], mx.z, B['hips'].head_local.z,
        ('%.4f deg (%s)' % mism) if mism[0] is not None else 'n/a', 'OK' if ok else 'PROBLEM'))
    pj = os.path.join(CREATURES, '_%s.json' % name)
    with open(pj, 'w') as f:
        json.dump(entry, f, indent=1)
    return entry
