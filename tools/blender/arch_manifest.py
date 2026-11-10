"""VALOMBRE settlements pack - manifest_village.json + overview sheet.
Run through arch_build.py:  blender -b --factory-startup -P tools/blender/arch_build.py -- @manifest
The manifest is derived from the exported .glb files (so it always matches what the engine loads)."""
import sys, os, json, struct, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *

ORDER = ['house_a', 'house_b', 'house_c', 'house_d', 'tavern', 'forge', 'chapel', 'barn', 'windmill', 'watchtower',
         'well', 'market_stall_a', 'market_stall_b', 'notice_board', 'signpost', 'fence_wood', 'fence_wattle',
         'stone_wall_low', 'palisade', 'palisade_gate', 'cart', 'barrel', 'crate', 'sacks', 'haystack', 'woodpile',
         'bench', 'table', 'trough', 'ladder', 'lamp_post', 'brazier', 'campfire', 'tent_a', 'tent_b', 'bedroll',
         'banner', 'scarecrow', 'dock', 'rowboat', 'bridge_wood', 'bridge_stone']

NOTES = {
    'house_a': 'Rain barrel, firewood stack and bench are part of the mesh (inside the footprint, not in COL_body).',
    'house_c': 'Lean-to shed on +X is open towards -Y; COL_shed / COL_shed_side only cover its back and outer side.',
    'house_d': 'ANCHOR_npc = in front of the shop counter (shopkeeper or customer spot). Awning cloth is double '
               'sided geometry.',
    'tavern': 'Porch deck is 0.25 m high: WALK_porch + WALK_step. ANCHOR_npc is ON the porch (z = 0.25). Stable '
              'lean-to (+X): front bay is passable, COL_stable covers the stalls. SMOKE_chimney = hall chimney '
              '(-X gable), SMOKE_kitchen = rear stack. Lantern by the door uses M_window_glow (no FIRE_ node).',
    'forge': 'Open front (-Y). FIRE_forge sits on the coal bed of the hearth, SMOKE_chimney on the stack. '
             'ANCHOR_npc = smith standing at the anvil. The water in the quench tub is a dark M_wood_planks disc '
             '(no water material in the contract).',
    'chapel': 'Slate roofs use M_roof_tiles with a blue-grey vertex colour that greys the clay texture. '
              'GLOW_window is 0.6 m in front of the rose window of the tower. The tower walls are 9.6 m, the spire '
              'tip 13 m, iron cross to 13.75 m.',
    'barn': 'Doors are closed (not enterable). Hay-loft opening is a dark recessed panel with hay and a hoist beam.',
    'windmill': 'ROT_blades is a separate mesh (origin at the hub). Its node has NO rotation: spin it around its '
                'local Blender Y axis = local Z axis in three.js (node.rotation.z += w * dt); Y points to the back, '
                'the sign only sets the direction. Sail sweep radius is 5.05 m around the hub (0, -2.72, 9.55), so '
                'keep 5.2 m clear left/right of the tower above 4.4 m. COL_tower_a + COL_tower_b (rotated 45 deg) '
                'approximate the round base.',
    'watchtower': 'ANCHOR_npc = lookout on the platform (z = 6.06). FIRE_brazier on the platform. The ladder is '
                  'decorative (no WALK boxes).',
    'well': 'ANCHOR_interact in front (-Y).',
    'market_stall_a': 'ANCHOR_npc = seller behind the counter (faces -Y). Cloth is double sided geometry.',
    'market_stall_b': 'ANCHOR_npc = seller behind the table (faces -Y). Cloth is double sided geometry.',
    'notice_board': 'ANCHOR_interact 0.8 m in front of the board (-Y).',
    'fence_wood': 'Runs along X, exactly 3.0 m, tiles end to end.',
    'fence_wattle': 'Runs along X, exactly 3.0 m, tiles end to end. Weave uses M_rope (wicker).',
    'stone_wall_low': 'Runs along X, 4.0 m between end faces (cope stones overhang by a few cm), tiles end to end.',
    'palisade': 'Runs along X, exactly 4.0 m, tiles end to end. Logs use M_bark_pine, sharpened tips M_wood_planks.',
    'palisade_gate': 'Runs along X, 6.0 m wide, same line as `palisade` (outside = -Y). 3.0 m clear opening between '
                     'x = -1.5 and 1.5, 3.3 m headroom. Flank logs are 4.7 m high. WALK_walkway (top z = 3.64) and '
                     'ANCHOR_npc are on the fighting platform; the ladder is decorative.',
    'cart': 'Shafts point to -Y and rest on the ground.',
    'ladder': 'Leans 14 degrees towards +Y (place it in front of a wall that is at y = +0.9).',
    'lamp_post': 'FIRE_lamp is at the lantern (use a small flame / warm light). Lantern panes use M_window_glow.',
    'banner': 'Cloth vertex colour is pure white (no baked AO) so the engine can tint M_cloth per instance; '
              'cloth is double sided geometry.',
    'tent_a': 'Entrance faces -Y. Canvas is double sided geometry.',
    'tent_b': 'Entrance faces -Y. Canvas is double sided geometry; guy ropes reach 3.5 m from the centre.',
    'dock': 'Runs along X, 6.0 m, tiles end to end. Deck top z = 0.9 (WALK_deck). Piles go down to z = -1.8.',
    'rowboat': 'Bow points to -Y. Keel bottom at z = 0, waterline about z = 0.22.',
    'bridge_wood': 'Walk direction = X. Flat deck x = -5..5 (top z = 1.0), ramps to z = 0 at x = +-7.5 (total '
                   '15 m). WALK_deck + 4 WALK_ramp_* steps per side (0.25 m each). Piles go down to z = -2.2. '
                   'COL_rail_* keep the player on the bridge.',
    'bridge_stone': 'Walk direction = X. Deck z = 2.2 * cos^2(pi * x / 14) between the parapets (|y| < 1.65). '
                    '19 WALK_deck_* boxes in 0.22 m steps. Arch (6.4 m span, crown z = 1.6) springs at z = -0.6: '
                    'put the water / river bed below. COL_parapet_* cover the parapets.',
}


def read_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    clen, ctype = struct.unpack_from('<II', data, 12)
    return json.loads(data[20:20 + clen].decode('utf8'))


def g2b(v):
    """glTF (x, y up, z) -> authoring (x, y, z up)"""
    return [round(v[0], 3), round(-v[2], 3), round(v[1], 3)]


def describe(name):
    reg = REG[name]
    path = os.path.join(OUT, name + '.glb')
    js = read_glb(path)
    acc = js.get('accessors', [])
    nodes = js.get('nodes', [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            parent[c] = i

    def wpos(i):
        t = list(nodes[i].get('translation', [0, 0, 0]))
        p = parent.get(i)
        while p is not None:
            pt = nodes[p].get('translation', [0, 0, 0])
            t = [t[0] + pt[0], t[1] + pt[1], t[2] + pt[2]]
            p = parent.get(p)
        return t
    mn = [1e9] * 3
    mx = [-1e9] * 3
    fmn = [1e9] * 3
    fmx = [-1e9] * 3
    tris = 0
    mats = []
    out_nodes = []
    for i, n in enumerate(nodes):
        nm = n.get('name', '')
        t = wpos(i)
        if 'mesh' in n:
            mesh = js['meshes'][n['mesh']]
            if nm.startswith(('COL_', 'WALK_')):
                s = n.get('scale', [1, 1, 1])
                q = n.get('rotation', [0, 0, 0, 1])
                ang = 2 * math.atan2(q[1], q[3])
                out_nodes.append({'name': nm, 'type': 'collider' if nm.startswith('COL_') else 'walkable',
                                  'pos': g2b(t), 'size': [round(abs(s[0]), 3), round(abs(s[2]), 3), round(abs(s[1]), 3)],
                                  'rot_z': round(ang, 4), 'pos_gltf': [round(x, 3) for x in t]})
                continue
            for p in mesh['primitives']:
                a = acc[p['attributes']['POSITION']]
                tris += acc[p['indices']]['count'] // 3
                m = js['materials'][p['material']]['name']
                if m not in mats:
                    mats.append(m)
                lo = g2b([a['min'][0] + t[0], a['min'][1] + t[1], a['max'][2] + t[2]])
                hi = g2b([a['max'][0] + t[0], a['max'][1] + t[1], a['min'][2] + t[2]])
                for j in range(3):
                    mn[j] = min(mn[j], lo[j])
                    mx[j] = max(mx[j], hi[j])
                    if not nm.startswith('ROT_'):
                        fmn[j] = min(fmn[j], lo[j])
                        fmx[j] = max(fmx[j], hi[j])
            if nm.startswith('ROT_'):
                out_nodes.append({'name': nm, 'type': 'rotating_mesh', 'pos': g2b(t),
                                  'pos_gltf': [round(x, 3) for x in t],
                                  'axis': 'local Y in Blender = local Z in three.js'})
        else:
            kind = nm.split('_')[0].lower()
            out_nodes.append({'name': nm, 'type': kind, 'pos': g2b(t), 'pos_gltf': [round(x, 3) for x in t]})
    # footprint: symmetric about the origin, covers the static mesh and the ground-level anchors (+0.3 m)
    ex = max(abs(fmn[0]), abs(fmx[0]))
    ey = max(abs(fmn[1]), abs(fmx[1]))
    for nd in out_nodes:
        if nd['type'] == 'anchor' and abs(nd['pos'][2]) < 0.5:
            ex = max(ex, abs(nd['pos'][0]))
            ey = max(ey, abs(nd['pos'][1]))
    d = {'file': name + '.glb', 'description': reg['desc'],
         'size': [round(mx[j] - mn[j], 2) for j in range(3)],
         'bounds_min': [round(v, 2) for v in mn], 'bounds_max': [round(v, 2) for v in mx],
         'tris': tris, 'tri_budget': reg['budget'], 'materials': mats,
         'footprint': [round(2 * ex + 0.6, 1), round(2 * ey + 0.6, 1)],
         'footprint_rect': [round(fmn[0], 2), round(fmn[1], 2), round(fmx[0], 2), round(fmx[1], 2)],
         'nodes': out_nodes}
    if name in NOTES:
        d['notes'] = NOTES[name]
    return d


def run():
    names = [n for n in ORDER if n in REG] + [n for n in REG if n not in ORDER]
    assets = {}
    for n in names:
        if not os.path.exists(os.path.join(OUT, n + '.glb')):
            print('Error: missing glb for', n)
            continue
        assets[n] = describe(n)
        a = assets[n]
        print('MANIFEST %-15s tris=%5d/%5d %s size=%s nodes=%d' % (n, a['tris'], a['tri_budget'],
              'OK' if a['tris'] <= a['tri_budget'] else 'OVER', a['size'], len(a['nodes'])))
    man = {
        'pack': 'village (settlements kit)',
        'generator': 'tools/blender/arch_build.py (+ arch_kit / arch_houses / arch_hero / arch_hero2 / arch_props / '
                     'arch_infra); rebuild one asset: blender -b --factory-startup -P tools/blender/arch_build.py '
                     '-- <name>',
        'units': 'meters',
        'coords': "All 'pos', 'size', 'bounds_*' and 'footprint*' values are in authoring space: X = right, "
                  "Y = back, Z = up, fronts / doors face -Y, origin = centre of the footprint on the ground. "
                  "three.js position = [x, z, -y] and is also given as 'pos_gltf'. Collider / walkable 'size' is "
                  "the full box size [x, y, z] before 'rot_z' (radians around the vertical axis).",
        'footprint': "'footprint' = [x, y] rectangle centred on the origin to keep clear / flatten (static mesh "
                     "extent + ground anchors + 0.3 m margin). 'footprint_rect' = exact [min x, min y, max x, max y] "
                     "of the static mesh.",
        'node_types': {
            'collider': 'COL_* invisible box, blocks characters', 'walkable': 'WALK_* invisible box, stand on its top',
            'anchor': 'ANCHOR_* gameplay anchor (door = 0.8 m in front of the door on the ground, npc, interact)',
            'fire': 'FIRE_* flame + flickering light', 'smoke': 'SMOKE_* chimney smoke', 'glow': 'GLOW_* soft light',
            'rotating_mesh': 'ROT_* separate mesh, origin = pivot'},
        'materials': 'Only contract material names are used. Every mesh has COLOR_0 (tint x baked AO, ground dirt, '
                     'moss on roofs, soot at chimneys) and world-scale TEXCOORD_0 (2 m tiles for the tiling '
                     'materials, 1 m for bark, 0.5 m for detail materials). Thin cloth (awnings, tents, sails, '
                     'banner) is modelled double sided, so FrontSide materials are fine.',
        'tri_total': sum(a['tris'] for a in assets.values()),
        'assets': assets,
    }
    path = os.path.join(OUT, 'manifest_village.json')
    with open(path, 'w', encoding='utf8') as f:
        json.dump(man, f, indent=1)
    print('MANIFEST written', path, 'assets=%d' % len(assets), 'tris=%d' % man['tri_total'])
    if '@nooverview' not in sys.argv:
        family(names, os.path.join(PREVIEWS, 'arch_village_overview.png'), views=('persp',), res=256, per_row=9)
