"""VALOMBRE world pack (citadel, ruins, sacred sites, biome set dressing) - build entry point.
  blender -b --factory-startup -P tools/blender/world_build.py -- [asset names...]   (no names = everything)
  blender -b --factory-startup -P tools/blender/world_build.py -- @manifest          (manifest + overview sheet)
Options: @nopreview, @zoom (extra close-up sheet world_<asset>_zoom.png), @showcol (world_<asset>_col.png with the
COL_/WALK_ boxes visible), @list
"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
for mod in ('world_castle', 'world_castle2', 'world_castle3', 'world_sacred', 'world_sacred2', 'world_wild',
            'world_wild2', 'world_wild3'):
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), mod + '.py')):
        importlib.import_module(mod)

if '@list' in argv:
    print('ASSETS', ' '.join(REG))
elif '@manifest' in argv:
    import world_manifest
    world_manifest.run(overview='@nooverview' not in argv)
else:
    names = [a for a in argv if not a.startswith('@')] or list(REG)
    for n in names:
        if n not in REG:
            print('Error: unknown asset', n)
            continue
        wbuild(n, preview=('@nopreview' not in argv), zoom=('@zoom' in argv), showcol=('@showcol' in argv))
