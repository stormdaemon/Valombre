"""VALOMBRE settlements pack - build entry point.
  blender -b --factory-startup -P tools/blender/arch_build.py -- [asset names...]   (no names = everything)
  blender -b --factory-startup -P tools/blender/arch_build.py -- @manifest          (manifest + overview sheet)
"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if '@noroof' in argv:
    os.environ['ARCH_NOROOF'] = '1'
for mod in ('arch_houses', 'arch_hero', 'arch_hero2', 'arch_props', 'arch_infra'):
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), mod + '.py')):
        importlib.import_module(mod)

if '@showcol' in argv:
    os.environ['ARCH_SHOWCOL'] = '1'
if '@manifest' in argv:
    import arch_manifest
    arch_manifest.run()
elif any(a.startswith('@family=') for a in argv):
    # @family=<sheet name>  asset asset ...   -> tools/previews/arch_<sheet name>.png (also exports the .glb files)
    sheet = [a for a in argv if a.startswith('@family=')][0].split('=', 1)[1]
    names = [a for a in argv if not a.startswith('@')]
    for n in names:
        if n not in REG:
            print('Error: unknown asset', n)
    names = [n for n in names if n in REG]
    for n in names:
        build(n, preview=False)
    family(names, os.path.join(PREVIEWS, 'arch_%s.png' % sheet), export=False)
else:
    names = [a for a in argv if not a.startswith('@')] or list(REG)
    for n in names:
        if n not in REG:
            print('Error: unknown asset', n)
            continue
        build(n, preview=('@nopreview' not in argv), zoom=('@zoom' in argv))
