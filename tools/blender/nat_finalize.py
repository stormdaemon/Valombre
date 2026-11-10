"""VALOMBRE nature pack - final step: impostor atlas, family contact sheets (rendered from the EXPORTED .glb
files) and manifest.json.

  blender -b --factory-startup -P tools/blender/nat_finalize.py [-- keep]     ("keep" = keep per-asset previews)

Run after nat_atlas.py, nat_trees.py, nat_plants.py, nat_rocks.py.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nat_common import *
from blcommon import _bounds

TREES = ['oak_a', 'oak_b', 'pine_a', 'pine_b', 'birch_a', 'willow_a', 'dead_a', 'dead_b']
PLANTS = ['bush_a', 'bush_b', 'fern', 'reeds', 'flowers_a', 'mushrooms', 'stump', 'log']
ROCKS = ['rock_a', 'rock_b', 'rock_c', 'rock_d', 'rock_e', 'cliff_a', 'cliff_b', 'pebbles']
IMP_W, IMP_H, IMP_CELL, IMP_PAD = 2048, 1024, 512, 6
IMP_INNER = IMP_CELL - 2 * IMP_PAD


def bleed(P, A):
    """Pull-push dilation (P premultiplied colour, A weight; square power-of-two size)."""
    Ps, As = [P.astype(np.float32)], [A.astype(np.float32)]
    while Ps[-1].shape[0] > 1:
        p, a = Ps[-1], As[-1]
        h = p.shape[0] // 2
        Ps.append(p.reshape(h, 2, h, 2, p.shape[2]).sum(axis=(1, 3)))
        As.append(a.reshape(h, 2, h, 2).sum(axis=(1, 3)))
    col = Ps[-1] / np.maximum(As[-1], 1e-6)[..., None]
    for lvl in range(len(Ps) - 2, -1, -1):
        up = np.repeat(np.repeat(col, 2, axis=0), 2, axis=1)
        up = (up + np.roll(up, 1, 0) + np.roll(up, -1, 0) + np.roll(up, 1, 1) + np.roll(up, -1, 1)) / 5.0
        a = As[lvl]
        k = np.clip(a * (8.0 if lvl == 0 else 3.0), 0, 1)
        own = Ps[lvl] / np.maximum(a, 1e-6)[..., None]
        col = up * (1 - k)[..., None] + own * k[..., None]
    return col


def area_weights(n_in, n_out):
    W = np.zeros((n_out, n_in), np.float32)
    s = n_in / n_out
    for i in range(n_out):
        a, b = i * s, (i + 1) * s
        for j in range(int(math.floor(a)), min(int(math.ceil(b)), n_in)):
            W[i, j] = max(0.0, min(b, j + 1) - max(a, j))
        W[i] /= max(W[i].sum(), 1e-9)
    return W


def resample(img, h, w):
    Wy, Wx = area_weights(img.shape[0], h), area_weights(img.shape[1], w)
    tmp = np.einsum('kl,jlc->jkc', Wx, img)
    return np.einsum('ij,jkc->ikc', Wy, tmp)


def load_lods(name):
    objs = import_glb(os.path.join(NATURE, name + '.glb'))
    lod0 = [o for o in objs if o.name.endswith('_LOD0')]
    lod1 = [o for o in objs if o.name.endswith('_LOD1')]
    return (lod0[0] if lod0 else None), (lod1[0] if lod1 else None)


# ----------------------------------------------------------------------------- impostors
def render_impostor(name):
    reset_scene()
    lod0, lod1 = load_lods(name)
    if lod1 is not None:
        bpy.data.objects.remove(lod1)
    preview_materials(unlit=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.render.image_settings.media_type = 'IMAGE'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.resolution_percentage = 100
    sc.render.filter_size = 0.01
    sc.eevee.taa_render_samples = 1
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0, 0, 0, 1)
    sc.world = world
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    link(cam)
    cam.data.type = 'ORTHO'
    cam.data.clip_start, cam.data.clip_end = 1.0, 1000.0
    cam.rotation_euler = (math.pi / 2, 0, 0)          # looks along +Y (front view)
    sc.camera = cam
    mn, mx = _bounds([lod0])

    def shoot(hw, H, scale_px):
        rx, ry = max(8, int(round(2 * hw * scale_px))), max(8, int(round(H * scale_px)))
        sc.render.resolution_x, sc.render.resolution_y = rx, ry
        cam.data.ortho_scale = 2 * hw if rx >= ry else H
        cam.location = (0.0, mn.y - 50.0, H / 2)
        return render_to_array()

    hw0, H0 = max(abs(mn.x), abs(mx.x)) * 1.03, mx.z * 1.03
    im = shoot(hw0, H0, 640.0 / max(2 * hw0, H0))
    a = im[:, :, 3] > 0.5
    ys, xs = np.where(a.any(axis=1))[0], np.where(a.any(axis=0))[0]
    px = (2 * hw0) / im.shape[1]
    cx = im.shape[1] / 2.0
    hw = max(cx - xs[0], xs[-1] + 1 - cx) * px * 1.012
    H = (im.shape[0] - ys[0]) * (H0 / im.shape[0]) * 1.008
    im = shoot(hw, H, min(1000.0 / min(2 * hw, H), 2600.0 / max(2 * hw, H)))
    A = (im[:, :, 3] > 0.5).astype(np.float32)
    P = im[:, :, :3] * A[..., None]
    small = resample(np.dstack([P, A]), IMP_INNER, IMP_INNER)
    print('IMPOSTOR', name, 'render', im.shape[1], 'x', im.shape[0], 'world %.2f x %.2f m' % (2 * hw, H),
          'coverage %.2f' % float((small[:, :, 3] > 0.5).mean()))
    return small, round(float(2 * hw), 3), round(float(H), 3)


def build_impostors():
    atlasP = np.zeros((IMP_H, IMP_W, 3), np.float32)
    atlasA = np.zeros((IMP_H, IMP_W), np.float32)
    info = {}
    for i, name in enumerate(TREES):
        c, r = i % 4, i // 4
        small, w, h = render_impostor(name)
        y0, x0 = r * IMP_CELL + IMP_PAD, c * IMP_CELL + IMP_PAD
        atlasP[y0:y0 + IMP_INNER, x0:x0 + IMP_INNER] = small[:, :, :3]
        atlasA[y0:y0 + IMP_INNER, x0:x0 + IMP_INNER] = small[:, :, 3]
        info[name] = dict(cell=[c, r], px=[x0, y0, x0 + IMP_INNER, y0 + IMP_INNER],
                          uv=[round(x0 / IMP_W, 6), round(1.0 - (y0 + IMP_INNER) / IMP_H, 6),
                              round((x0 + IMP_INNER) / IMP_W, 6), round(1.0 - y0 / IMP_H, 6)],
                          width=w, height=h)
    out = np.zeros((IMP_H, IMP_W, 4), np.float32)
    for r in range(2):
        for c in range(4):
            ys, xs = slice(r * IMP_CELL, (r + 1) * IMP_CELL), slice(c * IMP_CELL, (c + 1) * IMP_CELL)
            out[ys, xs, :3] = np.clip(bleed(atlasP[ys, xs], atlasA[ys, xs]), 0, 1)
            out[ys, xs, 3] = np.clip((atlasA[ys, xs] - 0.5) * 1.6 + 0.5, 0, 1)      # crisp alpha
    save_png(IMPOSTORS_A, out)
    print('WROTE', IMPOSTORS_A)
    bg = np.array([0.42, 0.45, 0.5], np.float32)
    comp = out[..., :3] * out[..., 3:4] + bg * (1 - out[..., 3:4])
    for k in range(1, 4):
        comp[:, k * IMP_CELL - 1:k * IMP_CELL + 1] = 0.2
    comp[IMP_CELL - 1:IMP_CELL + 1, :] = 0.2
    sheet = np.concatenate([comp, out[..., :3], np.repeat(out[..., 3:4], 3, axis=2)], axis=0)
    sheet = sheet.reshape(sheet.shape[0] // 2, 2, sheet.shape[1] // 2, 2, 3).mean(axis=(1, 3))
    save_png(os.path.join(PREVIEWS, 'nat_impostors.png'), sheet)
    print('PREVIEW', os.path.join(PREVIEWS, 'nat_impostors.png'))
    return info


# ----------------------------------------------------------------------------- contact sheets from the glb files
def family_sheet(names, out, res=256, views=('front', 'persp'), cols=2):
    tmp = []
    for name in names:
        reset_scene()
        lod0, lod1 = load_lods(name)
        preview_materials()
        p = os.path.join(PREVIEWS, 'nat__tmp_%s.png' % name)
        groups = [[lod0]] + ([[lod1]] if lod1 is not None else [])
        nat_sheet(p, groups, views=views, res=res, same_bounds=True, cols=len(views) * len(groups))
        tmp.append(p)
    stack_images(tmp, out, cols=cols)
    for p in tmp:
        os.remove(p)


# ----------------------------------------------------------------------------- manifest
def to_three(v):
    return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]


def build_manifest(imp):
    rects = atlas_rects()
    cs = ATLAS_PX // ATLAS_GRID
    cells = {}
    for name, (c, r, kind, desc) in ATLAS_CELLS.items():
        R = rects[name]
        x0, x1 = int(round(c * cs + R['cx0'] * cs)), int(round(c * cs + R['cx1'] * cs))
        y0, y1 = int(round(r * cs + (1 - R['cy1']) * cs)), int(round(r * cs + (1 - R['cy0']) * cs))
        cells[name] = dict(cell=[c, r], px=[c * cs, r * cs, (c + 1) * cs, (r + 1) * cs], content_px=[x0, y0, x1, y1],
                           anchor='bottom_edge' if kind == 'curtain' else 'bottom_center', description=desc,
                           opaque_fraction=round(R['coverage'], 3))
    assets = {}
    cats = [(n, 'tree') for n in TREES] + [(n, 'plant') for n in PLANTS] + [(n, 'rock') for n in ROCKS]
    total = 0
    for name, cat in cats:
        path = os.path.join(NATURE, name + '.glb')
        st = glb_mesh_stats(path)
        l0 = st[name + '_LOD0']
        meta = json.loads(l0['extras'].get('valombre', '{}'))
        mn, mx = l0['min'], l0['max']
        a = dict(file=name + '.glb', category=cat, description=meta.get('description', ''),
                 bytes=os.path.getsize(path),
                 lods={}, materials=sorted(set(l0['materials'])),
                 size=[round(mx[0] - mn[0], 3), round(mx[2] - mn[2], 3), round(mx[1] - mn[1], 3)],
                 bounds_min=[round(mn[0], 3), round(mn[2], 3), round(-mx[1], 3)],
                 bounds_max=[round(mx[0], 3), round(mx[2], 3), round(-mn[1], 3)],
                 height_above_ground=round(mx[2], 3),
                 collider=meta.get('collider'),
                 vertex_color=meta.get('vertex_color', 'R=AO, G=wind weight, B=phase'))
        for lod in ('LOD0', 'LOD1'):
            k = name + '_' + lod
            if k in st:
                a['lods'][lod] = dict(mesh=k, tris=st[k]['tris'], verts=st[k]['verts'],
                                      tris_by_material=st[k]['tris_by_material'])
                total += st[k]['tris'] if lod == 'LOD0' else 0
        if cat == 'tree':
            a['impostor'] = imp.get(name)
            a['lod1_distance'] = 70
            a['cards'] = dict(LOD0=meta.get('cards_lod0'), LOD1=meta.get('cards_lod1'))
        if 'sink' in meta:
            a['buried_fraction'] = meta['sink']
        a['scale_range'] = [0.8, 1.25]
        assets[name] = a
    man = dict(
        pack='nature', generator='tools/blender/nat_atlas.py, nat_trees.py, nat_plants.py, nat_rocks.py, nat_finalize.py',
        conventions=dict(
            axes='all vectors below are in glTF / three.js axes: [x, y (up), z]; meters; origin = base on the ground',
            lod='every .glb holds mesh nodes <asset>_LOD0 and (trees, boulders) <asset>_LOD1; LOD1 replaces LOD0 at ~70 m; '
                'trees switch to the impostor billboard further away',
            vertex_color='COLOR_0 (linear): R = ambient occlusion (multiply albedo), G = wind flutter weight '
                         '(0 rigid .. 1 leaf tips), B = random phase per branch / leaf cluster. Rocks, stump, log: G = B = 0. '
                         'EXCEPTIONS: flowers_a (M_flowers) and mushrooms (M_mushroom): RGB = actual linear colour.',
            foliage_normals='foliage vertices carry custom normals = normalize(0.3 * puffy outward (crown ellipsoid + '
                            'local clump) + 0.7 * up). Render M_leaves double sided and do NOT flip the normal on back '
                            'faces. (Weights are the w_global / w_local / w_up arguments of finish_tree in nat_common.py.)',
            uv='foliage UVs address leaves_a.png in glTF convention (v = 0 at the TOP of the image): load the atlas with '
               'texture.flipY = false. Bark UV: u = around the trunk (texture repeats), v = metres along the branch '
               '(1 m per tile). Rock UV: box projection, 4 m per tile.',
            collider='cylinder: vertical, radius = trunk at chest height, centred on the origin, use the tree height; '
                     'box: size [x, y, z] + center; sphere: radius + center. None = walk-through.',
            ground='trunks/roots/rocks continue 0.1-1.0 m below y = 0 so that they stay planted on slopes'),
        materials={
            'M_leaves': 'alpha-tested (cutoff 0.5), double sided foliage: assets/textures/leaves_a.png (+ leaves_n.png: '
                        'RG = normal, B = roughness). Albedo x COLOR_0.R; wind from COLOR_0.G/B.',
            'M_flowers': 'NEW. Same atlas and alpha test as M_leaves, but COLOR_0.rgb is a tint multiplied with the '
                         'texture (white flower heads become coloured); no wind attributes (sway by height).',
            'M_mushroom': 'NEW. Opaque, no texture needed (or a faint detail map): COLOR_0.rgb is the albedo, '
                          'roughness ~0.6.',
            'M_bark_oak': 'oak, willow, dead_a, stump, log, bush_b stems', 'M_bark_pine': 'pine_a, pine_b, dead_b',
            'M_bark_birch': 'birch_a', 'M_rock': 'rocks, cliffs, pebbles'},
        textures=dict(
            leaves_a=dict(file='assets/textures/leaves_a.png', size=[ATLAS_PX, ATLAS_PX], grid=[4, 4], cell_px=cs,
                          alpha='straight, colour bled into transparent texels', cells=cells,
                          note='px rects are [x0, y0, x1, y1] from the TOP-LEFT of the image; cell [col, row], row 0 = top'),
            leaves_n=dict(file='assets/textures/leaves_n.png', size=[ATLAS_PX, ATLAS_PX],
                          channels='R,G = tangent-space normal (OpenGL, +Y up), B = roughness, A = 255; same layout'),
            impostors_a=dict(file='assets/textures/impostors_a.png', size=[IMP_W, IMP_H], grid=[4, 2], cell_px=IMP_CELL,
                             alpha='straight, colour bled, alpha test at 0.5',
                             content='unlit albedo x AO, orthographic front view (camera looking along Blender +Y = '
                                     'three.js -Z); the engine relights it',
                             note='each tree fills the inner 500x500 px of its cell (6 px guard band); the tree base is at '
                                  'the bottom centre. impostor.px = [x0, y0, x1, y1] from the top-left; impostor.uv = '
                                  '[u0, v0, u1, v1] with v measured from the BOTTOM (three.js flipY = true default); '
                                  'the quad is width x height metres, bottom centre on the tree origin.')),
        totals=dict(assets=len(assets), lod0_tris_sum=total),
        assets=assets)
    with open(os.path.join(NATURE, 'manifest.json'), 'w', encoding='utf8') as f:
        json.dump(man, f, indent=1)
    print('WROTE manifest.json with', len(assets), 'assets')
    for name, a in assets.items():
        print('ASSET %-10s' % name, ' '.join('%s=%d' % (k, v['tris']) for k, v in a['lods'].items()), 'size', a['size'],
              'collider', a['collider'])


def uv_check():
    for name, lod, cols, rows in (('oak_a', 'LOD0', (0, 2), (0, 1)), ('oak_a', 'LOD1', (0, 1), (3, 4)),
                                  ('pine_a', 'LOD0', (0, 2), (1, 2)), ('fern', 'LOD0', (0, 1), (2, 3))):
        js, meshes = glb_arrays(os.path.join(NATURE, name + '.glb'))
        for m in meshes:
            if not m['name'].endswith(lod):
                continue
            for p in m['prims']:
                if p['material'] == 'M_leaves':
                    uv = p['TEXCOORD_0']
                    ok = (uv[:, 0].min() >= cols[0] / 4 - 1e-4 and uv[:, 0].max() <= cols[1] / 4 + 1e-4 and
                          uv[:, 1].min() >= rows[0] / 4 - 1e-4 and uv[:, 1].max() <= rows[1] / 4 + 1e-4)
                    print('UVCHECK', m['name'], 'u %.3f..%.3f v %.3f..%.3f' % (uv[:, 0].min(), uv[:, 0].max(),
                                                                              uv[:, 1].min(), uv[:, 1].max()),
                          'OK' if ok else 'UNEXPECTED')


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    imp = build_impostors()
    family_sheet(TREES, os.path.join(PREVIEWS, 'nat_trees.png'), res=256, views=('front', 'persp'), cols=2)
    if 'nosheets' not in args:
        family_sheet(PLANTS, os.path.join(PREVIEWS, 'nat_plants.png'), res=256, views=('front', 'persp', 'top'), cols=2)
        family_sheet(ROCKS, os.path.join(PREVIEWS, 'nat_rocks.png'), res=256, views=('front', 'persp'), cols=2)
    build_manifest(imp)
    uv_check()
    for n in TREES:
        check_leaf_normals(os.path.join(NATURE, n + '.glb'), n)
    if 'keep' not in args:
        for n in TREES + PLANTS + ROCKS:
            p = os.path.join(PREVIEWS, 'nat_%s.png' % n)
            if os.path.exists(p):
                os.remove(p)


main()
