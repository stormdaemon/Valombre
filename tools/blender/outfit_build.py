"""Builds the outfits / hair of VALOMBRE, renders preview sheets, exports outfits.glb, hair.glb and the manifest.

  blender -b --factory-startup -P tools/blender/outfit_build.py -- only=chain sheets=set:chain
  blender -b --factory-startup -P tools/blender/outfit_build.py -- only=all sheets=final export=1

only   : comma list of piece names, set names, hair names, or outfits / hair / beards / all
sheets : comma list of  set:<set>  head:<set>  hair:<style>[+beard]  sets mix morphs poses hairs beards final
export : 1 -> writes assets/models/char/{outfits.glb, hair.glb, outfits_manifest.json} (needs only=all)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outfit_lib import *
import outfit_sets as OS
import outfit_hair as OH

ARGS = {}
if '--' in sys.argv:
    for a in sys.argv[sys.argv.index('--') + 1:]:
        k, _, v = a.partition('=')
        ARGS[k] = v
ONLY = [x for x in ARGS.get('only', 'all').split(',') if x]
SHEETS = [x for x in ARGS.get('sheets', '').split(',') if x]

HAIRS = [n for n in OH.HAIR if n.startswith('hair_')]
BEARDS = [n for n in OH.HAIR if not n.startswith('hair_')]


def expand(names):
    out = []
    for n in names:
        if n == 'all':
            out += list(OS.PIECES) + list(OH.HAIR)
        elif n == 'outfits':
            out += list(OS.PIECES)
        elif n == 'hair':
            out += HAIRS
        elif n == 'beards':
            out += BEARDS
        elif n in OS.SETS:
            out += [n + '_head', n + '_chest', n + '_legs']
        else:
            out.append(n)
    seen = []
    for n in out:
        if n not in seen:
            seen.append(n)
    return seen


open_human()
K = Kit()
BUILT = {}
for name in expand(ONLY):
    t0 = time.time()
    if name in OS.PIECES:
        pc = OS.PIECES[name][0](K)
        m, extra = OS.piece_morphs(name)
        pc.build(m, extra_morphs=extra)
        slot = name.rsplit('_', 1)[1]
        if pc.tris > OS.BUDGET[slot]:
            print('OVER BUDGET', name, pc.tris, '>', OS.BUDGET[slot])
        if len(pc.materials) > 3:
            print('TOO MANY MATERIALS', name, pc.materials)
    else:
        pc = OH.HAIR[name](K)
        pc.build(OH.hair_morphs(name), ao_strength=0.55)
    BUILT[name] = pc


def hides_of(names):
    h = set()
    for n in names:
        if n in OS.PIECES:
            h |= set(OS.PIECES[n][1])
    return h


def tile(show, **kw):
    show = [s for s in show if s in BUILT]
    h = hides_of(show)
    if 'hair' in h:
        show = [s for s in show if not s.startswith('hair_')]
    if 'beard' in h:
        show = [s for s in show if not (s.startswith('beard') or s == 'mustache')]
    d = dict(show=show, hides=[r for r in h if r.startswith('body_')], center=(0, 0, 0.93), half=1.0)
    d.update(kw)
    return d


def full(setname):
    return [setname + '_head', setname + '_chest', setname + '_legs']


HEADC = (0, -0.01, 1.66)
PV = lambda n: os.path.join(PREVIEWS, 'outfit_%s.png' % n)

for sh in SHEETS:
    kind, _, arg = sh.partition(':')
    tiles = []
    if kind == 'set':
        S = full(arg)
        for v in ('front', 'left', 'back', 'persp'):
            tiles.append(tile(S, view=v, pose='apose'))
        tiles += [tile(S, view='front', pose='arms_down'), tile(S, view='persp_back', pose='arms_down'),
                  tile(S, view='persp', pose='run'), tile(S, view='left', pose='run'),
                  tile(S, view='persp', pose='crouch', center=(0, -0.1, 0.6), half=0.8), tile(S, view='front', pose='sword_up', center=(0, 0, 1.1), half=1.1),
                  tile(S, view='persp', pose='twist'), tile(S, view='back', pose='tpose'),
                  tile(S, view='persp', pose='apose', center=(0, 0, 1.35), half=0.5), tile(S, view='persp_back', pose='apose', center=(0, 0, 1.35), half=0.5),
                  tile(S, view='persp', pose='apose', center=(0, 0, 0.45), half=0.55), tile(S, view='front', pose='head_turn', center=(0, 0, 1.55), half=0.33)]
        render_tiles(PV('set_' + arg), tiles, res=448, cols=4)
    elif kind == 'head':
        S = full(arg)
        for v in ('front', 'left', 'back', 'persp'):
            tiles.append(tile(S, view=v, pose='apose', center=(0, 0, 1.62), half=0.27))
        tiles += [tile(S, view='persp', pose='head_turn', center=(0, 0, 1.62), half=0.27),
                  tile([arg + '_head'], view='persp', pose='apose', center=(0, 0, 1.62), half=0.27),
                  tile([arg + '_head', 'beard_full'], view='front', pose='apose', center=(0, 0, 1.62), half=0.27, morphs={'heavy': 1.0, 'jaw_width': 1.0}),
                  tile(S, view='persp', pose='apose', center=(0, 0, 1.62), half=0.27, morphs={'head_size': 1.0, 'head_width': 1.0, 'neck_size': 1.0})]
        render_tiles(PV('head_' + arg), tiles, res=448, cols=4)
    elif kind == 'hair':
        names = arg.split('+')
        for v in ('front', 'left', 'back', 'persp', 'persp_back', 'top'):
            tiles.append(tile(names, view=v, pose='apose', center=HEADC if not any('long' in n or 'braid' in n or 'pony' in n for n in names) else (0, 0, 1.58), half=0.24 if not any('long' in n or 'braid' in n or 'pony' in n for n in names) else 0.36))
        tiles.append(tile(names, view='persp_back', pose='head_turn', center=(0, 0, 1.58), half=0.36))
        tiles.append(tile(names, view='front', pose='apose', center=HEADC, half=0.24, morphs={'head_size': 1.0, 'head_width': 1.0, 'jaw_width': 1.0, 'forehead_height': 1.0}))
        render_tiles(PV('hair_' + names[0]), tiles, res=448, cols=4)
    elif kind == 'sets' or kind == 'final':
        for v in ('front', 'left', 'back', 'persp'):
            for s in OS.SETS:
                tiles.append(tile(full(s), view=v, pose='apose'))
        render_tiles(PV('sets'), tiles, res=384, cols=7)
    if kind == 'mix' or kind == 'final':
        combos = [('plate_chest', 'peasant_legs', 'leather_head'), ('peasant_chest', 'plate_legs', 'chain_head'),
                  ('robe_chest', 'chain_legs', 'bandit_head'), ('chain_chest', 'leather_legs', 'robe_head'),
                  ('leather_chest', 'bandit_legs', 'peasant_head'), ('bandit_chest', 'royal_legs', 'plate_head'),
                  ('royal_chest', 'robe_legs', 'hair_long'), ('peasant_chest', 'hair_short', 'beard_full'),
                  ('leather_legs', 'hair_medium', 'beard_short'), ('robe_chest', 'hair_braid'), ('chain_legs', 'royal_head'),
                  ('plate_chest', 'hair_ponytail', 'bandit_legs')]
        tiles = []
        for c in combos:
            tiles.append(tile(list(c), view='persp', pose='arms_down'))
            tiles.append(tile(list(c), view='back', pose='arms_down'))
        render_tiles(PV('mix'), tiles, res=384, cols=8)
    if kind == 'morphs' or kind == 'final':
        tiles = []
        for m in ({'muscular': 1.0}, {'heavy': 1.0, 'belly': 1.0}, {'feminine': 1.0}, {'thin': 1.0}):
            for s in OS.SETS:
                tiles.append(tile(full(s), view='persp', pose='apose', morphs=m))
        render_tiles(PV('morphs'), tiles, res=384, cols=7)
    if kind == 'poses' or kind == 'final':
        tiles = []
        for ps, v, c, h in (('arms_down', 'front', (0, 0, 0.93), 1.0), ('run', 'left', (0, 0, 0.93), 1.0),
                            ('crouch', 'persp', (0, -0.1, 0.6), 0.8), ('sword_up', 'front', (0, 0, 1.1), 1.1),
                            ('twist', 'persp', (0, 0, 0.93), 1.0), ('head_turn', 'persp_back', (0, 0, 1.4), 0.5)):
            for s in OS.SETS:
                tiles.append(tile(full(s), view=v, pose=ps, center=c, half=h))
        render_tiles(PV('poses'), tiles, res=384, cols=7)
    if kind == 'hairs' or kind == 'final':
        tiles = []
        for v in ('front', 'left', 'back'):
            for n in HAIRS:
                lng = n in ('hair_long', 'hair_braid', 'hair_ponytail')
                tiles.append(tile([n], view=v, pose='apose', center=(0, 0, 1.58) if lng else HEADC, half=0.36 if lng else 0.24))
        render_tiles(PV('hair'), tiles, res=384, cols=8)
    if kind == 'beards' or kind == 'final':
        tiles = []
        for v in ('front', 'left', 'persp'):
            for n in BEARDS:
                lng = n == 'beard_long'
                tiles.append(tile([n], view=v, pose='apose', center=(0, -0.02, 1.56) if lng else (0, -0.02, 1.64), half=0.30 if lng else 0.19))
        render_tiles(PV('beards'), tiles, res=384, cols=6)

if ARGS.get('export') == '1':
    arm = K.rig
    set_pose(arm, {})
    set_morphs({})
    for o in bpy.data.objects:
        o.hide_render = False
    missing = [n for n in list(OS.PIECES) + list(OH.HAIR) if n not in BUILT]
    assert not missing, missing
    man = {'pieces': {}, 'hair': {}}
    for fname, names in (('outfits.glb', list(OS.PIECES)), ('hair.glb', list(OH.HAIR))):
        objs = [arm] + [BUILT[n].ob for n in names]
        info = export_glb(os.path.join(CHAR_DIR, fname), objs, morphs=True)
        by = {m['name']: m for m in info['meshes']}
        assert info['skins'] and all(s['joints'] == 40 for s in info['skins']), info['skins']
        for n in names:
            m = by[n]
            tris = sum(pr['tris'] for pr in m['prims'])
            attrs = set(a for pr in m['prims'] for a in pr['attrs'])
            assert {'COLOR_0', 'JOINTS_0', 'WEIGHTS_0', 'TEXCOORD_0', 'NORMAL'} <= attrs, (n, attrs)
            mats = [pr['material'] for pr in m['prims']]
            tn = m['targetNames'] or []
            print('GLB %-16s tris=%5d verts=%5d mats=%s targets=%d' % (n, tris, sum(pr['verts'] for pr in m['prims']), mats, len(tn)))
            if n in OS.PIECES:
                slot = n.rsplit('_', 1)[1]
                assert tris <= OS.BUDGET[slot], (n, tris)
                man['pieces'][n] = {'hides': OS.PIECES[n][1], 'triangles': tris, 'materials': mats, 'morphs': tn,
                                    'note': OS.PIECES[n][2]}
            else:
                man['hair'][n] = {'triangles': tris, 'morphs': tn}
    man['notes'] = OS.MANIFEST_NOTES if hasattr(OS, 'MANIFEST_NOTES') else {}
    with open(os.path.join(CHAR_DIR, 'outfits_manifest.json'), 'w', encoding='utf8') as f:
        json.dump(man, f, indent=1)
    print('MANIFEST written')
    save_blend('outfit_all.blend')
