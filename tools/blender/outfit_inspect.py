"""Inspection of the human body kit (read only): region boundary loops."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
import numpy as np

BLEND = os.path.join(ROOT, 'tools', 'blender', 'build', 'human.blend')
bpy.ops.wm.open_mainfile(filepath=BLEND)
for nm in ('body_head', 'body_torso', 'body_arms', 'body_hands', 'body_legs', 'body_feet'):
    o = bpy.data.objects[nm]
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bv = set()
    for e in bm.edges:
        if len(e.link_faces) == 1:
            bv.add(e.verts[0].index); bv.add(e.verts[1].index)
    bm.verts.ensure_lookup_table()
    pts = np.array([bm.verts[i].co[:] for i in sorted(bv)])
    print('BOUNDARY', nm, len(pts))
    if nm == 'body_head':
        ang = np.degrees(np.arctan2(pts[:, 0], -(pts[:, 1] - 0.01)))
        for i in np.argsort(ang):
            if pts[i, 0] >= -1e-4:
                print('   a=%6.1f  %.4f %.4f %.4f  r=%.4f' % (ang[i], pts[i, 0], pts[i, 1], pts[i, 2], np.hypot(pts[i, 0], pts[i, 1] - 0.01)))
    else:
        print('   min', np.round(pts.min(0), 4), 'max', np.round(pts.max(0), 4))
    bm.free()
# neck sections
bf = bpy.data.objects['body_full']
n = len(bf.data.vertices)
P = np.empty(n * 3, np.float32)
bf.data.shape_keys.key_blocks['Basis'].data.foreach_get('co', P)
P = P.reshape(n, 3)
for z in np.arange(1.44, 1.60, 0.01):
    m = (np.abs(P[:, 2] - z) < 0.006) & (np.abs(P[:, 0]) < 0.21)
    S = P[m]
    if len(S):
        c = S[np.abs(S[:, 0]) < 0.02]
        print('z=%.2f x[%.3f %.3f] y[%.3f %.3f] center-line y: %s n=%d' % (z, S[:, 0].min(), S[:, 0].max(), S[:, 1].min(), S[:, 1].max(), np.round(np.sort(c[:, 1]), 3)[:6], len(S)))
# ring z values of the torso
zs = np.unique(np.round(P[(np.abs(P[:, 0]) < 0.01) & (P[:, 1] < 0), 2], 3))
print('front centre line z:', zs)
zs = np.unique(np.round(P[(np.abs(P[:, 0]) < 0.01) & (P[:, 1] > 0), 2], 3))
print('back centre line z:', zs)
# hand
m = P[:, 0] > 0.72
H = P[m]
for x in np.arange(0.72, 0.93, 0.02):
    S = H[np.abs(H[:, 0] - x) < 0.008]
    if len(S):
        print('hand x=%.2f y[%.3f %.3f] z[%.3f %.3f]' % (x, S[:, 1].min(), S[:, 1].max(), S[:, 2].min(), S[:, 2].max()))
m = (P[:, 2] < 0.13) & (P[:, 0] > 0)
Fp = P[m]
for y in np.arange(-0.21, 0.08, 0.02):
    S = Fp[np.abs(Fp[:, 1] - y) < 0.008]
    if len(S):
        print('foot y=%.2f x[%.3f %.3f] z[%.3f %.3f]' % (y, S[:, 0].min(), S[:, 0].max(), S[:, 2].min(), S[:, 2].max()))
