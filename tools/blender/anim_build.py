"""Builds assets/models/char/humanoid_anims.glb (+ .json) and the preview strips of every clip.

  blender -b --factory-startup -P tools/blender/anim_build.py -- [clip names | prefix*] [--strips] [--export]
                                                                  [--overview] [--view=<name>] [--n=<frames>]
  no clip name  = every clip.
  --strips      = render tools/previews/anim_<clip>.png for the selected clips
  --export      = bake ALL clips, export the .glb, patch non-integer durations, write the .json
  --overview    = one labelled tile per clip -> tools/previews/anim_overview.png
  --view / --n  = override the strip view / frame count (debug; with --tag=x writes anim_<clip>_x.png)
"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim_toolkit import *

MODULES = ('anim_clips_loco', 'anim_clips_combat', 'anim_clips_combat2', 'anim_clips_misc', 'anim_clips_monster')
OUT_GLB = os.path.join(MODELS, 'char', 'humanoid_anims.glb')
OUT_JSON = os.path.join(MODELS, 'char', 'humanoid_anims.json')


def all_clips():
    out = []
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError as e:
            if e.name != m:
                raise
            print('SKIP module', m)
            continue
        out += mod.clips()
    names = [c.name for c in out]
    assert len(set(names)) == len(names), 'duplicate clip names'
    return out


def write_json(clips):
    meta = {'fps': FPS, 'clips': {}}
    for c in clips:
        d = {'duration': round(c.dur, 4), 'loop': bool(c.loop)}
        if c.speed is not None:
            d['speed'] = c.speed
        d['events'] = c.events or {}
        meta['clips'][c.name] = d
    with open(OUT_JSON, 'w', encoding='utf8') as f:
        f.write('{\n  "fps": %d,\n  "clips": {\n' % FPS)
        items = list(meta['clips'].items())
        for i, (k, v) in enumerate(items):
            f.write('    %s: %s%s\n' % (json.dumps(k), json.dumps(v), ',' if i < len(items) - 1 else ''))
        f.write('  }\n}\n')
    print('WROTE', os.path.relpath(OUT_JSON, ROOT), len(meta['clips']), 'clips')


def overview(st, clips, path):
    """One tile per clip (a representative frame) with the clip name as a 3D label."""
    cam_dir = VIEWS['persp']
    font = bpy.data.curves.new('pv_label', 'FONT')
    font.size = 0.21
    font.align_x = 'CENTER'
    lab = bpy.data.objects.new('pv_label', font)
    link(lab)
    assign_mat(lab, make_mat('PV_label', (1, 1, 1), emissive=(1, 1, 1), emissive_strength=2.0))
    flat = Vector((cam_dir.x, cam_dir.y, 0)).normalized()
    lab.rotation_euler = (math.radians(90), 0, math.atan2(-flat.x, flat.y))
    lab.location = Vector((0, 0, 2.02)) - flat * 0.2
    k = 1.42 / math.sqrt(3.0)
    fb = (Vector((-k, -k, 1.0 - k)), Vector((k, k, 1.0 + k)))
    cam = setup_preview(224)
    sc = bpy.context.scene
    imgs = []
    for c in clips:
        st.activate(c)
        font.body = c.name
        fr = int(round(getattr(c, 'thumb', 0.45) * c.nframes))
        sc.frame_set(fr)
        bpy.context.view_layer.update()
        frame_camera(cam, fb[0], fb[1], cam_dir)
        imgs.append(render_to_array())
    lab.hide_render = True
    save_png(path, montage(imgs, cols=7))
    print('PREVIEW', path)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    flags = {a.split('=')[0]: (a.split('=')[1] if '=' in a else True) for a in argv if a.startswith('--')}
    names = [a for a in argv if not a.startswith('--')]
    t0 = time.time()
    st = Stage()
    st.keyinfo = '--keys' in flags
    clips = all_clips()
    if names and '--export' not in flags:
        sel = [c for c in clips if c.name in names or any(n.endswith('*') and c.name.startswith(n[:-1]) for n in names)]
    else:
        sel = clips
    for c in sel:
        st.bake(c)
    print('BAKE_DONE %d clips in %.1fs' % (len(sel), time.time() - t0))
    if '--strips' in flags:
        show = [c for c in sel if (not names) or c.name in names or any(n.endswith('*') and c.name.startswith(n[:-1]) for n in names)]
        for c in show:
            tag = flags.get('--tag')
            path = os.path.join(PREVIEWS, 'anim_%s%s.png' % (c.name, ('_' + tag) if tag else ''))
            st.strip(c, path, n=int(flags['--n']) if '--n' in flags else None, view=flags.get('--view'),
                     bounds=float(flags['--bounds']) if '--bounds' in flags else None)
    if '--overview' in flags:
        overview(st, sel, os.path.join(PREVIEWS, 'anim_overview.png'))
    if '--export' in flags:
        for c in clips:
            show_props(st.props, 'none')
        actions_to_nla(st.arm, [st.actions[c.name] for c in clips])
        export_glb(OUT_GLB, [st.arm, st.man], anims=True)
        kept, removed = glb_clean_animations(OUT_GLB)
        print('CLEANED channels kept %d removed %d' % (kept, removed))
        scales = {c.name: (c.dur * FPS) / c.nframes for c in clips if abs(c.dur * FPS - c.nframes) > 1e-6}
        if scales:
            glb_rescale_times(OUT_GLB, scales)
            print('RESCALED', json.dumps({k: round(v, 5) for k, v in scales.items()}))
        info = glb_info(OUT_GLB)
        got = dict(info['summary']['animations'])
        bad = [(c.name, c.dur, got.get(c.name)) for c in clips if c.name not in got or abs(got[c.name] - c.dur) > 0.002]
        print('FINAL', json.dumps(info['summary']))
        print('NODES', len(info['nodes']), 'MESHES', [(m['name'], [(p['tris'], p['material'], p['attrs']) for p in m['prims']]) for m in info['meshes']])
        print('DURATION_CHECK', 'OK %d clips' % len(clips) if not bad else 'MISMATCH %s' % bad)
        write_json(clips)
    print('TOTAL %.1fs' % (time.time() - t0))


main()
