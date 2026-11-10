"""Merge the per-monster entries written by mon_skeleton / mon_troll / mon_golem into
assets/models/creatures/humanoid_monsters.json and re-verify the exported files.
Plain python (no Blender needed):  python tools/blender/mon_manifest.py
"""
import os, json, struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CRE = os.path.join(ROOT, 'assets', 'models', 'creatures')
BUDGET = {'skeleton': 6000, 'troll': 9000, 'golem': 7000}


def glb_summary(path):
    data = open(path, 'rb').read()
    clen, = struct.unpack_from('<I', data, 12)
    js = json.loads(data[20:20 + clen].decode('utf8'))
    acc = js['accessors']
    tris, col, skin = 0, True, True
    per = {}
    for m in js['meshes']:
        for p in m['primitives']:
            t = acc[p['indices']]['count'] // 3
            tris += t
            per[js['materials'][p['material']]['name']] = per.get(js['materials'][p['material']]['name'], 0) + t
            col = col and ('COLOR_0' in p['attributes'])
            skin = skin and ('JOINTS_0' in p['attributes']) and ('JOINTS_1' not in p['attributes'])
    joints = [js['nodes'][j]['name'] for j in js['skins'][0]['joints']] if js.get('skins') else []
    return tris, per, col, skin, joints, len(data), len(js['meshes'])


def main():
    out = {
        'rig': 'shared humanoid rig (tools/blender/humanoid_rig.py): 40 joints, same bone names and rest ORIENTATIONS as the player; '
               'only bone lengths / offsets differ on troll and golem (brute_warp in tools/blender/mon_lib.py).',
        'retargeting': 'replay the shared clips (assets/models/char/humanoid_anims.glb) by bone name: quaternion tracks as they are, '
                       'hips position track multiplied by hipsRatio (= hipsHeight / 0.98). Verified offline with the real clips.',
        'units': 'meters; rest pose = the rig T-pose; armature root at the origin on the ground, facing +Z in glTF (Blender -Y)',
        'monsters': {},
    }
    ok_all = True
    for name in ('skeleton', 'troll', 'golem'):
        e = json.load(open(os.path.join(CRE, '_%s.json' % name)))
        tris, per, col, skin, joints, nbytes, nmesh = glb_summary(os.path.join(CRE, e['file']))
        e['triangles'], e['trianglesByMaterial'], e['bytes'], e['joints'] = tris, per, nbytes, len(joints)
        e['materials'] = list(per.keys())
        ok = tris <= BUDGET[name] and col and skin and len(joints) == 40 and nmesh == 1
        ok_all = ok_all and ok
        out['monsters'][name] = e
        print('%-9s tris %5d / %d  joints %d  COLOR_0 %s  <=4 influences %s  %s  -> %s' % (
            name, tris, BUDGET[name], len(joints), col, skin, per, 'OK' if ok else 'PROBLEM'))
    out['materialNotes'] = {
        'M_eye_glow': 'small emissive eye spheres (not in the convention table): unlit emissive, vertex color = tint '
                      '(skeleton pale green, troll amber). Golem eyes are part of M_ember.',
        'M_ember': 'golem cores / joints / eyes / chest heart: own primitive, swap for M_ice (frost variant) and tint M_rock.',
        'M_cloth': 'skeleton tabard, belt and diagonal strap (dark vertex colors read as old leather). The tabard is modelled '
                   'double-sided (two faces per quad), single-sided rendering is fine.',
        'M_fur': 'troll loincloth, modelled double-sided.',
    }
    with open(os.path.join(CRE, 'humanoid_monsters.json'), 'w') as f:
        json.dump(out, f, indent=1)
    for name in ('skeleton', 'troll', 'golem'):
        os.remove(os.path.join(CRE, '_%s.json' % name))
    print('humanoid_monsters.json written, all OK:', ok_all)


if __name__ == '__main__':
    main()
