"""VALOMBRE textures: verification, manifest and contact sheet.
Reads every texture back from disk (so the checks cover what the engine will really load), then writes
  assets/textures/manifest.json
  tools/previews/tex_overview.png   (labelled contact sheet: 3x3 tiled, normal-mapped lit render of each texture)
Run:  blender -b --factory-startup -P tools/blender/tex_finish.py [-- sheet name1 name2 ...]
      ("sheet" + names: only writes tools/previews/tex_sheet.png with the 1:1 lit crops of those textures)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex_lib import *

# name: (pixel size, tile size in meters, engine material, description)
PBR = [
    ('terrain_grass', 1024, 4.0, 'terrain layer', 'short meadow grass seen from above: tufts of blades, a few dry blades, clover'),
    ('terrain_dirt', 1024, 4.0, 'terrain layer', 'packed earth path, embedded pebbles, fine drying cracks'),
    ('terrain_rock', 1024, 4.0, 'terrain layer / M_rock', 'stratified cliff rock, beds run along U (horizontal in the image), fissures, lichen'),
    ('terrain_sand', 1024, 4.0, 'terrain layer', 'beach sand with wind ripples (crests along U), pebbles and shell bits'),
    ('terrain_snow', 1024, 4.0, 'terrain layer', 'wind-packed snow: soft drifts, crust scarps, blue hollows, sparkle in roughness'),
    ('terrain_forest', 1024, 4.0, 'terrain layer', 'forest floor: dark humus, dead leaves, twigs, needles, moss cushions'),
    ('terrain_mud', 1024, 4.0, 'terrain layer', 'wet swamp mud with glossy puddles (roughness ~0.07) and organic debris'),
    ('terrain_ash', 1024, 4.0, 'terrain layer', 'volcanic ash: cracked charcoal crust, cinders, rust, pale ash dust drifts'),
    ('stone_wall', 1024, 2.0, 'M_stone_wall', 'rough rubble masonry in horizontal courses, recessed lime mortar, moss in joints'),
    ('stone_brick', 1024, 2.0, 'M_stone_brick', 'cut ashlar blocks 0.5 x 0.25 m in running bond, chipped arrises, weathering streaks'),
    ('cobble', 1024, 2.0, 'M_cobble', 'rounded cobblestones (~11 cm), packed dirt and a little moss in the gaps'),
    ('plaster', 1024, 2.0, 'M_plaster', 'whitewashed daub: hairline cracks, stains, small flaked patches showing the daub'),
    ('wood_planks', 1024, 2.0, 'M_wood_planks', 'weathered boards running along V, 8 boards across U, grain, knots, nails, gaps'),
    ('roof_tiles', 1024, 2.0, 'M_roof_tiles', 'flat clay shingles, 16 rows x 12 per tile, top of image = ridge side, lichen'),
    ('thatch', 1024, 2.0, 'M_thatch', 'straw thatch, straws along V, 4 overlapping layers per tile (top = ridge side)'),
    ('bark_oak', 512, 1.0, 'M_bark_oak', 'deep vertical furrows, grey-brown blocky ridges'),
    ('bark_pine', 512, 1.0, 'M_bark_pine', 'reddish-brown scaly plates made of stacked flakes, dark furrows'),
    ('bark_birch', 512, 1.0, 'M_bark_birch', 'white papery bark, dark horizontal lenticels, a few black scars'),
    ('metal', 512, 0.5, 'M_metal_iron / steel / gold / bronze', 'hammered plate, light scratches, tiny pits (near-white albedo)'),
    ('leather', 512, 0.5, 'M_leather', 'pebbled grain, creases, pores (near-white albedo)'),
    ('cloth', 512, 0.5, 'M_cloth', 'plain weave, 64 x 64 threads per tile (near-white albedo)'),
    ('rope', 512, 0.5, 'M_rope', 'twisted strands at 45 degrees, rope axis along V (near-white albedo)'),
    ('fur', 512, 0.5, 'M_fur', 'short strands, roots up / tips down the image = flowing towards -V (near-white albedo)'),
    ('hide', 512, 0.5, 'M_hide', 'thick monster hide: tubercles, warts, deep wrinkles (near-white albedo)'),
    ('chitin', 512, 0.5, 'M_chitin', 'smooth glossy shell, faint growth ridges across V, micro pits (near-white albedo)'),
    ('bone', 512, 0.5, 'M_bone', 'porous bone, pores and fine cracks elongated along V (near-white albedo)'),
    ('skin', 512, 0.5, 'M_skin', 'very subtle pores and crosshatch micro wrinkles (near-white albedo)'),
    ('hair', 512, 0.5, 'M_hair', 'fine strands running along V (near-white albedo)'),
]
FX = [
    ('water_n', 512, 4, 'R,G = tiling water ripple normal (OpenGL, two blended wave scales), B = foam / caustic web noise, A = 255'),
    ('fx_noise', 512, 4, 'R = low-frequency perlin fbm, G = worley F1 (0 at the cell seeds), B = high-frequency fbm, A = billowy perlin-worley cloud; every channel tiles'),
    ('fx_bluenoise', 64, 1, '8-bit greyscale void-and-cluster blue noise, flat histogram, tiles'),
]

FONT = {
    'a': '010101111101101', 'b': '110101110101110', 'c': '011100100100011', 'd': '110101101101110',
    'e': '111100110100111', 'f': '111100110100100', 'g': '011100101101011', 'h': '101101111101101',
    'i': '111010010010111', 'j': '001001001101010', 'k': '101101110101101', 'l': '100100100100111',
    'm': '101111111101101', 'n': '110101101101101', 'o': '010101101101010', 'p': '110101110100100',
    'q': '010101101111011', 'r': '110101110101101', 's': '011100010001110', 't': '111010010010010',
    'u': '101101101101111', 'v': '101101101101010', 'w': '101101111111101', 'x': '101101010101101',
    'y': '101101010010010', 'z': '111001010100111', '_': '000000000000111', ' ': '000000000000000',
}


def draw_label(img, text, scale=2):
    """Stamp a tiny 3x5 pixel-font label on a dark strip at the top-left of an image (in place)."""
    w = len(text) * 4 * scale + 2 * scale
    h = 7 * scale
    img[:h, :w] = img[:h, :w] * 0.25
    for k, ch in enumerate(text):
        g = FONT.get(ch, FONT[' '])
        for b, bit in enumerate(g):
            if bit == '1':
                gy, gx = divmod(b, 3)
                y0 = scale + gy * scale
                x0 = scale + (k * 4 + gx) * scale
                img[y0:y0 + scale, x0:x0 + scale] = 1.0
    return img


def seam_rank(a):
    """Fraction of interior column / row boundaries that are at least as discontinuous as the wrap-around
    boundary. Near 0 would mean the wrap is the worst line of the whole image = a visible seam."""
    a = np.asarray(a, F)
    dx = np.abs(a[:, 1:] - a[:, :-1]).mean(0)
    wx = np.abs(a[:, 0] - a[:, -1]).mean()
    dy = np.abs(a[1:] - a[:-1]).mean(1)
    wy = np.abs(a[0] - a[-1]).mean()
    return float((dx >= wx).mean()), float((dy >= wy).mean())


def sheet(names):
    panels = []
    for nm in names:
        alb, hgt, nrm, rough, ao = decode_tex(nm)
        lit = lit_render(alb, nrm, rough, ao)
        n = lit.shape[0]
        o = (n - 512) // 2
        panels.append(draw_label(lit[o:o + 512, o:o + 512].copy(), nm))
    path = os.path.join(PREVIEWS, 'tex_sheet.png')
    save_png(path, montage(panels, cols=min(len(panels), 4)))
    print('PREVIEW', path)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if args and args[0] == 'sheet':
        sheet(args[1:])
        return
    man = {
        'format': {
            '<name>_a.png': 'RGB = albedo (sRGB), A = height 0..1 (linear; stones / blades high, mortar / gaps low)',
            '<name>_n.png': 'R,G = tangent-space normal x,y as n*0.5+0.5 (OpenGL: +Y = up in the image), '
                            'B = roughness, A = ambient occlusion (1 = open); all linear. z = sqrt(1 - x^2 - y^2)',
            'loading': 'load with premultiplyAlpha = false; _a is sRGB (alpha stays linear), _n and the fx files are '
                       'linear data (NoColorSpace). All textures wrap (RepeatWrapping) and are power-of-two '
                       '(mipmaps OK). Height alpha is clamped to >= 8/255.',
        },
        'textures': {},
        'fx': {},
    }
    panels = []
    ok = True
    for name, size, tile_m, material, desc in PBR:
        pa = os.path.join(TEXTURES, name + '_a.png')
        pn = os.path.join(TEXTURES, name + '_n.png')
        if not (os.path.exists(pa) and os.path.exists(pn)):
            print('MISSING', name)
            ok = False
            continue
        ra = read_png(pa)
        rn = read_png(pn)
        good = ra.shape == (size, size, 4) and rn.shape == (size, size, 4)
        alb, hgt, nrm, rough, ao = decode_tex(name)
        sr_a = seam_rank(luma(alb))
        sr_n = min(seam_rank(nrm[..., 0]) + seam_rank(nrm[..., 1]))
        sr_h = seam_rank(hgt)
        worst = min(min(sr_a), sr_n, min(sr_h))
        ratio = max(seam_score(luma(alb)) + seam_score(nrm[..., 0]) + seam_score(nrm[..., 1]))
        amin, amax = int(ra[..., :3].min()), int(ra[..., :3].max())
        avg = [int(round(v)) for v in ra[..., :3].reshape(-1, 3).mean(0)]
        # large-scale balance: brightness spread of the tile cut in 4x4 blocks
        blocks = down(luma(alb), size // 4)
        entry = {
            'files': {'albedo_height': name + '_a.png', 'normal_rough_ao': name + '_n.png'},
            'size_px': [size, size],
            'tile_m': tile_m,
            'used_by': material,
            'description': desc,
            'avg_albedo_srgb': avg,
            'albedo_min_max': [amin, amax],
            'avg_roughness': round(float(rough.mean()), 3),
            'roughness_p01_p99': [round(float(np.percentile(rough, 1)), 3), round(float(np.percentile(rough, 99)), 3)],
            'avg_ao': round(float(ao.mean()), 3),
            'avg_height': round(float(hgt.mean()), 3),
            'avg_normal_z': round(float(nrm[..., 2].mean()), 3),
        }
        man['textures'][name] = entry
        print('CHECK %-15s %s %dpx alb=%s [%d..%d] rough=%.2f nz=%.3f wrap/interior=%.2f blocks(luma)=%.3f..%.3f' % (
            name, 'OK ' if good else 'BAD', size, avg, amin, amax, rough.mean(), nrm[..., 2].mean(), ratio,
            blocks.min(), blocks.max()))
        ok = ok and good
        lit = lit_render(alb, nrm, rough, ao)
        panels.append(draw_label(down(tile(lit, 3), (3 * size) // 256)[:256, :256].copy(), name, 2))

    # fx
    for name, size, ch, desc in FX:
        p = os.path.join(TEXTURES, name + '.png')
        if not os.path.exists(p):
            print('MISSING', name)
            ok = False
            continue
        a = read_png(p)
        good = a.shape == (size, size, ch)
        man['fx'][name] = {'file': name + '.png', 'size_px': [size, size], 'channels': ch, 'description': desc,
                           'channel_means': [round(float(a[..., k].mean()) / 255.0, 3) for k in range(ch)]}
        af = a.astype(F) / 255.0
        sr = min(min(seam_rank(af[..., k])) for k in range(ch) if af[..., k].std() > 0)
        print('CHECK %-15s %s %s seam_rank=%.2f' % (name, 'OK ' if good else 'BAD', a.shape, sr))
        ok = ok and good
        if name == 'water_n':
            nx, ny = af[..., 0] * 2 - 1, af[..., 1] * 2 - 1
            nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
            nr = np.stack([nx, ny, nz], -1)
            alb = np.broadcast_to(hexc('#2f4a55'), (size, size, 3)).astype(F) + af[..., 2:3] * 0.35
            lit = lit_render(alb, nr, np.full((size, size), 0.12, F), np.ones((size, size), F))
            panels.append(draw_label(down(tile(lit, 3), 6).copy(), name, 2))
        elif name == 'fx_noise':
            q = [down(af[..., k], 4) for k in range(4)]
            im = np.concatenate([np.concatenate([q[0], q[1]], 1), np.concatenate([q[2], q[3]], 1)], 0)
            panels.append(draw_label(np.repeat(im[..., None], 3, -1).copy(), name, 2))
        else:
            im = np.kron(tile(af[..., 0], 2), np.ones((2, 2), F))
            panels.append(draw_label(np.repeat(im[..., None], 3, -1).copy(), name, 2))

    man['overview_order'] = [p[0] for p in PBR] + [f[0] for f in FX]
    man['generator'] = 'tools/blender/tex_terrain.py, tex_building.py, tex_bark.py, tex_detail.py, tex_fx.py ' \
                       '(library tex_lib.py), checked by tex_finish.py'
    with open(os.path.join(TEXTURES, 'manifest.json'), 'w', encoding='utf8') as f:
        json.dump(man, f, indent=1)
    print('WROTE', os.path.join(TEXTURES, 'manifest.json'))
    path = os.path.join(PREVIEWS, 'tex_overview.png')
    save_png(path, montage(panels, cols=8, pad=4))
    print('PREVIEW', path, 'ALL OK' if ok else 'PROBLEMS')


if __name__ == '__main__':
    main()
