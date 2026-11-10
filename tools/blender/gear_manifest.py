"""Merge the partial manifests written by gear_weapons.py / gear_shields.py into assets/models/gear/manifest.json.
Plain python (no Blender needed):  python tools/blender/gear_manifest.py
"""
import os, json, struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GEAR = os.path.join(ROOT, 'assets', 'models', 'gear')


def glb_summary(path):
    data = open(path, 'rb').read()
    clen, = struct.unpack_from('<I', data, 12)
    js = json.loads(data[20:20 + clen].decode('utf8'))
    acc = js['accessors']
    tris, col = 0, True
    for m in js['meshes']:
        for p in m['primitives']:
            tris += acc[p['indices']]['count'] // 3
            col = col and ('COLOR_0' in p['attributes'])
    return tris, [m['name'] for m in js['materials']], col, len(js['meshes']), len(data)


def main():
    weapons = json.load(open(os.path.join(GEAR, '_weapons.json')))
    shields = json.load(open(os.path.join(GEAR, '_shields.json')))
    out = {
        'units': 'meters',
        'conventions': {
            'axes': 'Coordinates below are BLENDER authoring axes (x, y, z up). In the .glb (+Y up) a point (x, y, z) is (x, z, -y).',
            'weapon': 'grip centre (right fist) at the origin, tip toward Blender +Z (glTF +Y), main cutting edge toward +X, '
                      'flat in the XZ plane. Attach the glTF scene to the bone `weapon_R` with an identity local transform.',
            'twoHanded': 'right hand at the origin, left hand at z = offhandGrip (handle is long enough for 0.17 .. 0.30 m below).',
            'blade': '[z_base, z_tip] of the damaging part along the weapon axis (glTF +Y), for weapon trails / hit sweeps.',
            'shield': 'upright, facing Blender -Y (glTF +Z), straps side at the origin: attach to the bone `shield_L` with an identity '
                      'local transform. The forearm lies along X behind the board (elbow toward +X); the fist closes on the '
                      'rolled grip at gripLocal. Bent shields have their centre slightly in FRONT of the origin plane so that '
                      'the straight forearm bridges the hollow.',
            'materials': 'engine materials by NAME; vertex color COLOR_0 (linear) carries the albedo tint + wear on every primitive.',
        },
        'weapons': {}, 'shields': {},
    }
    problems = []
    for wid, e in weapons.items():
        tris, mats, col, nmesh, nbytes = glb_summary(os.path.join(GEAR, e['file']))
        e['triangles'], e['materials'], e['bytes'] = tris, mats, nbytes
        if tris > 600 or not col or nmesh != 1:
            problems.append((wid, tris, col, nmesh))
        out['weapons'][wid] = e
    for sid, e in shields.items():
        tris, mats, col, nmesh, nbytes = glb_summary(os.path.join(GEAR, e['file']))
        e['triangles'], e['materials'], e['bytes'] = tris, mats, nbytes
        if tris > 700 or not col or nmesh != 1:
            problems.append((sid, tris, col, nmesh))
        out['shields'][sid] = e
    with open(os.path.join(GEAR, 'manifest.json'), 'w') as f:
        json.dump(out, f, indent=1)
    for k in ('_weapons.json', '_shields.json'):
        os.remove(os.path.join(GEAR, k))
    print('MANIFEST %d weapons, %d shields, problems: %s' % (len(out['weapons']), len(out['shields']), problems))
    for wid, e in list(out['weapons'].items()) + list(out['shields'].items()):
        print('  %-20s tris %4d  size %s  %s' % (wid, e['triangles'], e['size'], ','.join(m[2:] for m in e['materials'])))


if __name__ == '__main__':
    main()
