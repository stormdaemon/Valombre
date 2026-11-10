"""VALOMBRE world pack - manifest_world.json + overview sheet.
Run through world_build.py:  blender -b --factory-startup -P tools/blender/world_build.py -- @manifest
The manifest is derived from the exported .glb files (so it always matches what the engine loads); assets whose
.glb is missing are listed under 'missing'."""
import sys, os, json, struct, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *

ORDER = ['castle_wall', 'castle_wall_ruin_a', 'castle_wall_ruin_b', 'castle_tower', 'castle_tower_ruin', 'castle_gate',
         'castle_keep', 'castle_stairs', 'floor_slab', 'pillar', 'pillar_broken', 'arch_ruin', 'throne',
         'statue_knight', 'statue_broken', 'brazier_stone',
         'shrine', 'standing_stone_a', 'standing_stone_b', 'standing_stone_c', 'dolmen', 'lore_stele', 'gravestone_a',
         'gravestone_b', 'gravestone_c', 'grave_cross', 'sarcophagus', 'chest', 'chest_ornate', 'crystal_small',
         'crystal_cluster', 'crystal_giant',
         'barricade', 'cage_hanging', 'skull_pike', 'bone_pile', 'ruin_house', 'ruin_wall_a', 'ruin_wall_b',
         'ruin_tower', 'spider_cocoon', 'egg_sacs', 'bramble_arch', 'cave_mouth', 'swamp_hut', 'sunken_boat',
         'drowned_chapel', 'ice_spikes_a', 'ice_spikes_b', 'frost_cairn', 'obsidian_spire_a', 'obsidian_spire_b',
         'cult_altar', 'cult_banner', 'lighthouse', 'shipwreck']

GROUPS = {
    'citadel': ORDER[0:16], 'sacred': ORDER[16:32], 'bandits': ORDER[32:40], 'forest': ORDER[40:44],
    'swamp': ORDER[44:47], 'mountain': ORDER[47:50], 'ash': ORDER[50:54], 'coast': ORDER[54:56],
}

NOTES = {
    'castle_wall': 'Runs along X, exactly 8.0 m, tiles end to end; outside (battered face, corbelled parapet) = -Y. '
                   'Wall-walk top z = 5.3 (WALK_walk, 1.15 m wide between the parapets), merlon tops z = 7.0. Goes '
                   '0.8 m below ground. COL_wall stops at the wall-walk; COL_parapet_front / _back keep the player '
                   'on it. Same wall line as castle_gate (its side faces are 5.7 m deep, centre the wall on y = 0 of '
                   'the gate) and castle_tower (overlap the tower by ~1 m).',
    'castle_wall_ruin_a': 'Same line / length as castle_wall. Full section at x = -4 (tiles with castle_wall), 2.0 m '
                          'stump at x = +4 (tiles with the -X end of castle_wall_ruin_b; mirror it by rotating 180 '
                          'deg if you need the other handedness, the outside then faces +Y). Not climbable.',
    'castle_wall_ruin_b': 'Same line / length as castle_wall. 2.0 m stump at x = -4, full section at x = +4. '
                          'The breach x = -1.75 .. 0.65 is passable: WALK_breach_a (top 0.2) + WALK_breach_b '
                          '(top 0.45) over the rubble ramp, COL_left / COL_right on both sides.',
    'castle_tower': 'Outside = -Y (banner, main arrow slit), door case on +Y (courtyard). Shaft radius 3.0 m (3.34 at '
                    'ground, battered), parapet radius 3.54, hoarding beam stubs reach 4.3 m. Roof apex 14.3 m, iron '
                    'spike 14.9 m. Goes 0.9 m below ground. 4 COL_tower_* boxes (6.4 x 2.66, rotated 0/45/90/135 deg) '
                    'form an octagon. Not enterable. Roof = M_roof_tiles with a blue-grey vertex colour (slate).',
    'castle_tower_ruin': 'Same footprint / base as castle_tower. Hollow shell (inner faces + debris floor at ~3.4 m, '
                         'not enterable). Rubble spill towards -X/-Y (COL_spill).',
    'castle_gate': 'Front = -Y. Passage along Y through x = -1.8 .. 1.8, clear height 2.7 m at the jambs, 4.5 m at the '
                   'apex; the raised portcullis hangs above z = 2.98 at y = -1.75 (M_metal_iron). ANCHOR_gate = '
                   'centre of the passage on the ground. COL_left / COL_right only (nothing over the passage). Roof '
                   'terrace z = 7.3 is not walkable (no WALK). Goes 0.8 m below ground. Banners: M_cloth, double sided.',
    'castle_keep': 'Backdrop building, not enterable: COL_body (14 x 12) + 3 COL_turret_* + COL_collapse (rubble mound '
                   'over the missing front-right corner) + COL_steps. Front (sealed doorway) = -Y. Interior is '
                   'modelled as a hollow shell (inner faces, debris, charred beams) because it is visible through '
                   'the windows and the breach. Goes 0.9 m below ground. Highest point 18 m (back-left turret).',
    'castle_stairs': 'Rise along +X: bottom edge x = -3 (z = 0), top edge x = +3 (z = 3.0). 12 WALK_step_NN boxes '
                     '(0.5 m run, 0.25 m rise, 3.3 m wide between the side walls). 6 COL_side_* boxes (stepped) cover '
                     'the string walls. The high end is a blank wall: butt it against floor_slab stacks / a terrace.',
    'floor_slab': 'Top z = 0.3 (WALK_top). Rubble skirt down to z = -0.6 so it can sit on uneven ground or be stacked '
                  'as a terrace. One corner slab (+X, -Y) is missing on purpose. Top uses M_cobble, kerb M_stone_brick.',
    'pillar': 'COL_pillar 0.9 x 0.9. Abacus top z = 6.0: a vault / arch_ruin springing can sit on it.',
    'arch_ruin': 'Passage along Y between x = -2.0 and 2.0 (springing 2.45 m, apex 4.2 m). COL_left / COL_right.',
    'throne': 'Front = -Y. Dais steps 0.2 / 0.4 / 0.6 m: WALK_dais_1, WALK_dais_2, WALK_dais (top). ANCHOR_boss = on '
              'the floor 1.3 m in front of the first step (boss spawn / arena centre side); ANCHOR_seat = on the '
              'seat (z = 1.22) for a seated pose. GLOW_crystal at the big shard. Sun emblem + crown = M_metal_gold. '
              'COL_throne covers seat + back + the big crystals.',
    'statue_knight': 'Figure 2.76 m on a 0.85 m plinth (total 3.6 m), faces -Y. Statue = M_rock (plain stone), plinth = '
                     'M_stone_brick.',
    'statue_broken': 'Same plinth. COL_statue (plinth + legs) and COL_torso (fallen torso in front).',
    'brazier_stone': 'FIRE_main above the coal bed (z = 1.62). Rune band uses M_rune_glow with an ember-orange vertex '
                     'colour.',
    'shrine': 'Autel de Braise. Front (approach) = -Y. FIRE_main = ember bowl on the altar (z = 1.48). ANCHOR_rest = '
              'kneeling spot ON the dais (z = 0.3), 1.3 m in front of the altar face, facing +Y. WALK_dais + '
              'WALK_dais_b (same box rotated 45 deg) approximate the round dais top (z = 0.3). Rune stones are 3.7 - '
              '4.35 m high, lean towards the fire and carry M_rune_glow glyphs on both the inner and the outer face '
              '(vertex colour = ember orange #ffb057: multiply your rune emissive by COLOR_0). A rune ring is inlaid '
              'in the dais. COL_altar + 3 COL_stone_* (rotated boxes).',
    'standing_stone_a': 'M_rune_glow vertex colour = pale cyan #9fe9ff (old Aubeclair / Astre runes). Goes 0.8 m below '
                        'ground.',
    'standing_stone_b': 'See standing_stone_a.',
    'standing_stone_c': 'See standing_stone_a; the crack on the +X side and the back is M_rune_glow too.',
    'dolmen': 'Chamber open towards -Y, 1.75 m clear under the capstone: characters can stand inside (3 COL boxes on the '
              'uprights only).',
    'lore_stele': 'ANCHOR_interact 1.0 m in front (-Y). Inscription = M_rune_glow (pale cyan vertex colour).',
    'gravestone_c': 'The fallen head lies in front (-Y) and has no collider.',
    'sarcophagus': 'Long axis = X (head of the effigy at -X).',
    'chest': 'ROT_lid = separate mesh, origin on the back hinge line (y = +0.275, z = 0.36), closed at rotation 0. '
             'To open rotate it around its local X by a NEGATIVE angle (three.js: lid.rotation.x = -1.9 for fully '
             'open; X is the same axis in Blender and three.js). ANCHOR_loot = above the opening. The inside of the '
             'box is modelled (dark wood).',
    'chest_ornate': 'Same rig as chest (ROT_lid origin y = +0.3, z = 0.45, open = negative rotation.x). M_metal_gold '
                    'fittings, a small M_crystal gem in the hasp.',
    'crystal_small': 'GLOW_core. Scale 0.7 - 1.4 and rotate freely.',
    'crystal_cluster': 'GLOW_core at z = 0.9. Rock base goes 0.3 m below ground.',
    'crystal_giant': 'GLOW_core half way up the monolith + GLOW_base. Leans towards +X/-Y. COL_base + COL_shard.',
    'barricade': 'Runs along X (4 m); the extra stakes point to -Y (enemy side).',
    'cage_hanging': 'Post at x = +0.8, cage hangs at x = -0.5 between z = 2.35 and 4.2 (no collider: walk under it).',
    'ruin_house': 'Roofless shell, enterable through the doorway in the front wall (-Y, x = -1.9 .. -0.7) - '
                  'ANCHOR_door 0.8 m in front of it. Floor = terrain. COL boxes cover the wall stretches and the '
                  'chimney.',
    'ruin_wall_a': 'L-shaped corner fragment. Goes 0.7 m below ground.',
    'ruin_wall_b': 'Straight fragment along X with a broken doorway (passable, x = -0.1 .. 1.1).',
    'ruin_tower': 'Hollow round base, radius 3.0 m, walls 1.0 m: enterable through the doorway on -Y (1.15 m wide, '
                  '2.2 m high) only; 8 thin COL_wall_* boxes follow the ring and leave that doorway open (the low '
                  'collapsed side on -X is NOT passable). Floor = terrain.',
    'bramble_arch': 'Passage along Y under the arch (4.4 m wide, 3.3 m clear at the axis). M_rune_glow veins have a '
                    'violet vertex colour (#b76bff). COL_base_l / COL_base_r only.',
    'cave_mouth': 'Not enterable: the opening is recessed 2.7 m and closed by a black M_obsidian wall; COL_rock covers '
                  'everything behind y = -0.6. Put it against a cliff / hillside (the back slopes down to the ground '
                  'at y = +5.4).',
    'swamp_hut': 'Hut on stilts, platform top z = 2.0. Not enterable (COL_body from the ground up so nobody walks '
                 'under it); the ladder is decorative. ANCHOR_npc = on the porch (z = 2.0), ANCHOR_interact = at the '
                 'foot of the ladder. Window / lantern = M_window_glow. SMOKE_roof = smoke hole.',
    'sunken_boat': 'Tilted and meant to be half buried: keep the origin on the mud / water line.',
    'drowned_chapel': 'Boss-arena backdrop. Long axis = X (apse at +X, west door at -X), the south wall (-Y) is mostly '
                      'gone so the nave is open towards -Y. WALK_floor top z = 0.25 (flagged nave + apse floor). '
                      'COL boxes: north wall, west gable left / right of the door, apse, south stubs. The toppled '
                      'bell lies in the nave (COL_bell). Walls go 1 m below ground: sink it in the water / mud.',
    'ice_spikes_a': 'M_ice spikes on M_rock. Scale 0.7 - 1.3.',
    'frost_cairn': 'Banner = M_cloth (double sided), icicles = M_ice.',
    'obsidian_spire_a': 'M_obsidian with M_ember cracks; GLOW_ember for a warm point light. Goes 0.6 m below ground.',
    'obsidian_spire_b': 'See obsidian_spire_a. Leans towards -X.',
    'cult_altar': 'Front = -Y. FIRE_candle_1..3 = small candle flames (use a tiny flame / weak light), '
                  'FIRE_brazier_l / _r = the two iron tripod braziers. ANCHOR_boss = 1.2 m in front of the first step. '
                  'WALK_step_1 (0.2) and WALK_step_2 (0.4). The split sun = M_metal_bronze (brass vertex colour), '
                  'double sided; posts = M_obsidian. Blood = dark red vertex colour on M_rock.',
    'cult_banner': 'Cloth = M_cloth with a red vertex colour (baked), double sided. Finial = M_metal_bronze.',
    'lighthouse': 'Door faces -Y. FIRE_top = centre of the lantern room (z = 14.2): use a strong warm light / beam. '
                  'Lantern panes = M_window_glow. Gallery z = 12.6 (not walkable). 4 COL_tower_* boxes form an '
                  'octagon + COL_annex + COL_door (door case). Goes 0.9 m below ground. Cap = M_metal_bronze with a '
                  'verdigris vertex colour, annex roof = M_roof_tiles tinted slate.',
    'shipwreck': 'Long axis = X (bow at +X), heeled over towards -Y (you look into the hull from the front). '
                 'COL_hull covers the hull, COL_mast a low box on the fallen mast (which runs from the hull to '
                 'x = 5.6, y = -8.6). Sail rag = M_cloth, double sided. Sunk 1 m: put the origin on the sand.',
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
                                  'axis': 'local X (same axis in Blender and three.js); closed = 0, open = negative '
                                          'angle (about -1.9 rad)'})
        else:
            kind = nm.split('_')[0].lower()
            out_nodes.append({'name': nm, 'type': kind, 'pos': g2b(t), 'pos_gltf': [round(x, 3) for x in t]})
    ex = max(abs(fmn[0]), abs(fmx[0]))
    ey = max(abs(fmn[1]), abs(fmx[1]))
    for nd in out_nodes:
        if nd['type'] == 'anchor' and abs(nd['pos'][2]) < 0.5:
            ex = max(ex, abs(nd['pos'][0]))
            ey = max(ey, abs(nd['pos'][1]))
    group = [g for g, names in GROUPS.items() if name in names]
    d = {'file': name + '.glb', 'group': group[0] if group else 'misc', 'description': reg['desc'],
         'size': [round(mx[j] - mn[j], 2) for j in range(3)],
         'bounds_min': [round(v, 2) for v in mn], 'bounds_max': [round(v, 2) for v in mx],
         'tris': tris, 'tri_budget': reg['budget'], 'materials': mats,
         'footprint': [round(2 * ex + 0.6, 1), round(2 * ey + 0.6, 1)],
         'footprint_rect': [round(fmn[0], 2), round(fmn[1], 2), round(fmx[0], 2), round(fmx[1], 2)],
         'below_ground': round(-min(0.0, mn[2]), 2),
         'nodes': out_nodes}
    if name in NOTES:
        d['notes'] = NOTES[name]
    return d


def run(overview=True):
    names = [n for n in ORDER if n in REG] + [n for n in REG if n not in ORDER]
    assets = {}
    missing = [n for n in ORDER if n not in REG]
    for n in names:
        if not os.path.exists(os.path.join(OUT, n + '.glb')):
            print('MANIFEST missing glb for', n)
            missing.append(n)
            continue
        assets[n] = describe(n)
        a = assets[n]
        print('MANIFEST %-19s tris=%5d/%5d %s size=%s nodes=%d' % (n, a['tris'], a['tri_budget'],
              'OK' if a['tris'] <= a['tri_budget'] else 'OVER', a['size'], len(a['nodes'])))
    man = {
        'pack': 'world (citadel of Aubeclair, ruins, sacred sites, biome set dressing)',
        'generator': 'tools/blender/world_build.py (+ world_kit / world_castle / world_castle2 / world_castle3 / '
                     'world_sacred / world_wild / world_wild2, built on arch_kit); rebuild one asset: blender -b '
                     '--factory-startup -P tools/blender/world_build.py -- <name>',
        'units': 'meters',
        'coords': "All 'pos', 'size', 'bounds_*' and 'footprint*' values are in authoring space: X = right, "
                  "Y = back, Z = up, fronts / doors face -Y, origin = centre of the footprint on the ground. "
                  "three.js position = [x, z, -y] and is also given as 'pos_gltf'. Collider / walkable 'size' is "
                  "the full box size [x, y, z] before 'rot_z' (radians around the vertical axis).",
        'footprint': "'footprint' = [x, y] rectangle centred on the origin to keep clear / flatten (static mesh "
                     "extent + ground anchors + 0.3 m margin). 'footprint_rect' = exact [min x, min y, max x, max y] "
                     "of the static mesh. 'below_ground' = how far the mesh goes below z = 0 (pieces made to sink "
                     "into uneven terrain).",
        'node_types': {
            'collider': 'COL_* invisible box, blocks characters', 'walkable': 'WALK_* invisible box, stand on its top',
            'anchor': 'ANCHOR_* gameplay anchor (rest, boss, gate, loot, interact, door, npc, seat)',
            'fire': 'FIRE_* flame + flickering light', 'smoke': 'SMOKE_* smoke', 'glow': 'GLOW_* soft point light '
            '(cold cyan for crystals, warm for GLOW_ember, violet for GLOW_veins)',
            'rotating_mesh': 'ROT_* separate mesh, origin = pivot'},
        'materials': 'Only contract material names are used (no new material). Every mesh has COLOR_0 (tint x baked '
                     'AO, ground dirt, damp base, moss on tops and near the ground, soot) and world-scale TEXCOORD_0 '
                     '(2 m tiles for M_stone_brick / M_stone_wall / M_cobble / M_wood_planks / M_roof_tiles / '
                     'M_thatch, 4 m for M_rock, 1 m for bark, 0.5 m for detail materials). Cloth (banners, rags, '
                     'webs, sails) is modelled double sided, so FrontSide materials are fine. Emissive materials: '
                     'COLOR_0 is the intended tint and is NOT darkened by AO - M_rune_glow: ember orange (#ffb057) '
                     'on the shrine / brazier_stone / cult_altar, pale cyan (#9fe9ff) on standing stones / dolmen / '
                     'lore_stele, violet (#b76bff) on bramble_arch; M_crystal: cyan at the base to white at the '
                     'tips; M_ember: orange / yellow; M_ice and M_obsidian: near white (the material gives the '
                     'colour). Rune glyphs, arrow slits, cracks and blood are thin quads 1 - 2.5 cm proud of the '
                     'surface (no z-fighting at gameplay distances).',
        'groups': GROUPS,
        'missing': sorted(set(missing), key=ORDER.index) if missing else [],
        'tri_total': sum(a['tris'] for a in assets.values()),
        'assets': assets,
    }
    path = os.path.join(OUT, 'manifest_world.json')
    with open(path, 'w', encoding='utf8') as f:
        json.dump(man, f, indent=1)
    print('MANIFEST written', path, 'assets=%d' % len(assets), 'tris=%d' % man['tri_total'], 'missing=%d' % len(man['missing']))
    if overview:
        wfamily(list(assets), os.path.join(PREVIEWS, 'world_overview.png'), views=('persp',), res=224, per_row=8)
