"""VALOMBRE golem -> assets/models/creatures/golem.glb : ~3.1 m brute of cracked volcanic rock.
Angular basalt plates (convex hulls, rigidly skinned to ONE bone each) float on glowing ember cores; the cores,
joints, eyes and chest heart are the separate material slot `M_ember` (the engine swaps it for `M_ice`).

Run:  blender -b --factory-startup -P tools/blender/mon_golem.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mon_lib import *

S = 3.1 / 3.0
BASALT, BASALT_DK, BASALT_LT, SCORCH = C('#383433'), C('#1d1b1b'), C('#6a645e'), C('#5a2414')
EMB, EMB_HOT, EMB_DEEP = C('#ff7a1e'), C('#ffd27a'), C('#d0300a')


def fib_dirs(n):
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        out.append(Vector((r * math.cos(ga * i), r * math.sin(ga * i), z)))
    return out


DIRS = fib_dirs(320)


def spread(n, rnd):
    """n well-spread directions (farthest point sampling with a little randomness)."""
    seeds = [DIRS[rnd.randrange(len(DIRS))]]
    while len(seeds) < n:
        best, bd = None, -1
        for d in DIRS:
            m = min(d.angle(s) for s in seeds) * rnd.uniform(0.78, 1.0)
            if m > bd:
                best, bd = d, m
        seeds.append(best)
    return seeds


def sup(d, p):
    """Superellipsoid direction shaping: p < 1 -> blockier."""
    return Vector((math.copysign(abs(d.x) ** p, d.x), math.copysign(abs(d.y) ** p, d.y), math.copysign(abs(d.z) ** p, d.z)))


def rock_col(c, r3, inner=0.74, seed=0):
    r3 = Vector(r3)

    def f(p, i, j):
        q = p - c
        t = math.sqrt((q.x / r3.x) ** 2 + (q.y / r3.y) ** 2 + (q.z / r3.z) ** 2)
        depth = clamp01((t - inner) / max(1e-6, 1.0 - inner))            # 0 = by the core, 1 = outer skin
        col = mix(BASALT_DK, BASALT, 0.3 + 0.7 * vnoise(p, 6.0, seed))
        up = clamp01(q.normalized().z * 0.5 + 0.5) if q.length > 1e-6 else 0.5
        col = mix(col, BASALT_LT, 0.6 * up * up * (0.45 + 0.55 * vnoise(p, 11.0, seed + 3)))   # ash / dust on top
        col = mix(SCORCH, col, 0.2 + 0.8 * sstep(0.0, 0.8, depth))                               # heat-stained near the seams
        return mul(col, 0.82 + 0.36 * vnoise(p, 25.0, seed + 7))
    return f


def ember_col(seed=0, hot=0.0):
    def f(p, i, j):
        n = fbm(p, 7.0, seed, 2)
        c = mix(EMB_DEEP, EMB, sstep(0.3, 0.6, n))
        return mix(c, EMB_HOT, clamp01(hot + 0.8 * sstep(0.55, 0.8, vnoise(p, 13.0, seed + 5))))
    return f


def plates(mb, c, r3, K, seed, shrink=0.915, inner=0.72, jag=0.10, p=0.72, skip=None, n_rim=7, core=0.82, core_hot=0.0, core_segs=(8, 5)):
    """Cover an ellipsoid (centre c, radii r3) with K angular rock plates separated by narrow seams, over an ember core."""
    c, r3 = Vector(c), Vector(r3)
    rnd = random.Random(seed)

    def E(d, k=1.0):
        s = sup(d.normalized(), p)
        return c + Vector((s.x * r3.x, s.y * r3.y, s.z * r3.z)) * k

    seeds = spread(K, rnd)
    cells = [[] for _ in seeds]
    for d in DIRS:
        k = min(range(K), key=lambda i: d.angle(seeds[i]))
        cells[k].append(d)
    col = rock_col(c, r3, inner, seed)
    for k, sd in enumerate(seeds):
        if skip and skip(sd):
            continue
        u = sd.orthogonal().normalized()
        v = sd.cross(u)
        best = {}
        for d in cells[k]:
            ang = math.atan2(d.dot(v), d.dot(u))
            sec = int((ang + math.pi) / (2 * math.pi) * n_rim) % n_rim
            dist = d.angle(sd)
            if sec not in best or dist > best[sec][0]:
                best[sec] = (dist, d)
        rim = [b[1] for b in best.values()]
        if len(rim) < 3:
            continue
        lift = 1 + rnd.uniform(-0.03, jag)                    # each plate sits at its own height: stepped, cracked crust
        pd = [(sd * (1 - shrink) + d * shrink).normalized() for d in rim]
        pts = [E(d, lift + rnd.uniform(-jag * 0.5, jag * 0.3)) for d in pd]
        pts.append(E(sd, lift + rnd.uniform(0.02, jag * 1.2)))
        d2 = (sd * 0.5 + rim[rnd.randrange(len(rim))] * 0.5).normalized()
        pts.append(E(d2, lift + rnd.uniform(0.0, jag)))
        pts += [E(d, inner) for d in pd]
        mb.hull(pts, col, 'M_rock', sharp=22.0, uvs=0.25)
    if core:
        mb.sphere((0, 0, 0), tuple(r3 * core), 'M_ember', ember_col(seed, core_hot), segs=core_segs[0], rings=core_segs[1], M=tr(c), sharp=80.0)


def boulder(mb, c, r3, n, seed, p=0.7, jag=0.12, flat_bottom=None):
    c, r3 = Vector(c), Vector(r3)
    rnd = random.Random(seed)
    pts = []
    for d in spread(n, rnd):
        s = sup(d, p)
        q = c + Vector((s.x * r3.x, s.y * r3.y, s.z * r3.z)) * (1 + rnd.uniform(-jag, jag * 0.5))
        if flat_bottom is not None:
            q.z = max(q.z, flat_bottom)
        pts.append(q)
    mb.hull(pts, rock_col(c, r3, 0.0, seed), 'M_rock', sharp=22.0, uvs=0.25)


def ember(mb, c, r, seed=0, hot=0.2, segs=6, rings=4):
    r3 = tuple(r) if isinstance(r, (tuple, list, Vector)) else (r, r, r)
    mb.sphere((0, 0, 0), r3, 'M_ember', ember_col(seed, hot), segs=segs, rings=rings, M=tr(Vector(c)), sharp=80.0)


def build(mb):
    def sc3(*v):
        return Vector(v) * S

    # ------------------------------------------------------------------ trunk
    mb.bone = 'hips'
    plates(mb, sc3(0, 0.03, 1.14), sc3(0.46, 0.36, 0.25), 11, 11)
    mb.bone = 'spine_01'
    plates(mb, sc3(0, -0.03, 1.47), sc3(0.43, 0.37, 0.22), 10, 12)
    mb.bone = 'spine_02'
    plates(mb, sc3(0, -0.01, 1.77), sc3(0.52, 0.41, 0.24), 11, 13)
    mb.bone = 'spine_03'
    heart = sc3(0, -0.36, 2.12)
    plates(mb, sc3(0, 0.06, 2.20), sc3(0.68, 0.50, 0.40), 24, 14, skip=lambda d: d.y < -0.86 and abs(d.x) < 0.3 and abs(d.z + 0.12) < 0.3,
           core_segs=(10, 6))
    ember(mb, heart, 0.15 * S, 3, 0.8, segs=8, rings=5)                                               # chest heart
    for k, (dx, dz, rx, rz) in enumerate(((0.17, 0.06, 0.075, 0.16), (-0.17, -0.02, 0.07, 0.17), (0.02, -0.17, 0.15, 0.06), (-0.03, 0.18, 0.16, 0.065))):
        boulder(mb, heart + Vector((dx, -0.05, dz)) * S, sc3(rx, 0.085, rz), 10, 40 + k)                 # slabs caging the heart
    # hump of boulders on the back and shoulders
    for k, (cx, cy, cz, rx, ry, rz) in enumerate(((0.0, 0.30, 2.70, 0.34, 0.30, 0.30), (0.33, 0.24, 2.62, 0.26, 0.26, 0.24), (-0.34, 0.22, 2.64, 0.27, 0.25, 0.25),
                                                  (0.12, 0.44, 2.38, 0.24, 0.2, 0.26), (-0.16, 0.45, 2.32, 0.22, 0.2, 0.24))):
        boulder(mb, sc3(cx, cy, cz), sc3(rx, ry, rz), 16, 60 + k, p=0.75, jag=0.16)
    mb.bone = 'neck'
    ember(mb, sc3(0, -0.2, 2.31), sc3(0.16, 0.16, 0.12), 8, 0.1, segs=7)
    boulder(mb, sc3(0.13, -0.17, 2.31), sc3(0.1, 0.14, 0.1), 10, 71)
    boulder(mb, sc3(-0.13, -0.17, 2.31), sc3(0.1, 0.14, 0.1), 10, 72)
    # ------------------------------------------------------------------ head: one craggy block, slit eyes, glowing jaw seam
    mb.bone = 'head'
    boulder(mb, sc3(0, -0.27, 2.635), sc3(0.215, 0.235, 0.15), 22, 80, p=0.72, jag=0.1)                # cranium + face block
    boulder(mb, sc3(0, -0.475, 2.675), sc3(0.21, 0.08, 0.05), 12, 81, p=0.8)                             # brow ledge
    boulder(mb, sc3(0, -0.49, 2.57), sc3(0.05, 0.05, 0.085), 9, 83)                                    # nose wedge
    ember(mb, sc3(0, -0.30, 2.487), sc3(0.18, 0.195, 0.026), 9, 0.4, segs=8, rings=3)                   # seam between skull and jaw
    boulder(mb, sc3(0, -0.315, 2.41), sc3(0.19, 0.215, 0.075), 16, 82, p=0.75, jag=0.1)                # heavy lower jaw
    for sx in (1, -1):
        ember(mb, sc3(sx * 0.108, -0.488, 2.622), sc3(0.046, 0.024, 0.02), 5, 0.9, segs=6, rings=3)     # eyes under the brow
    # ------------------------------------------------------------------ arms
    for sd, sx in (('L', 1.0), ('R', -1.0)):
        o = 0 if sx > 0 else 100

        def P(x, y, z):
            return Vector((sx * x, y, z)) * S

        mb.bone = 'clavicle_' + sd
        plates(mb, P(0.60, 0.04, 2.40), sc3(0.36, 0.34, 0.31), 10, 20 + o, core=0.8)
        mb.bone = 'upper_arm_' + sd
        ember(mb, P(0.66, 0, 2.28), 0.2 * S, 21 + o, 0.2, segs=7)                                      # shoulder joint
        plates(mb, P(0.98, 0, 2.28), sc3(0.33, 0.215, 0.215), 9, 22 + o, p=0.8, core_segs=(7, 4))
        mb.bone = 'forearm_' + sd
        ember(mb, P(1.30, 0, 2.28), 0.16 * S, 23 + o, 0.3, segs=7)                                     # elbow
        plates(mb, P(1.60, 0, 2.28), sc3(0.32, 0.225, 0.225), 10, 24 + o, p=0.8, core_segs=(7, 4))
        # hand: fist block + three rock fingers and a thumb on ember knuckles
        mb.bone = 'hand_' + sd
        ember(mb, P(1.935, 0.0, 2.275), 0.12 * S, 25 + o, 0.3)                                         # wrist
        boulder(mb, P(2.035, 0.035, 2.285), sc3(0.14, 0.225, 0.13), 16, 26 + o, p=0.8)
        ember(mb, P(2.155, 0.035, 2.28), sc3(0.04, 0.2, 0.07), 27 + o, 0.3, segs=6, rings=3)
        for k, (bone, y, x0, x1, r) in enumerate((('index_01_', -0.095, 2.15, 2.29, 0.082), ('index_02_', -0.10, 2.27, 2.43, 0.07),
                                                  ('fingers_01_', 0.04, 2.15, 2.30, 0.085), ('fingers_02_', 0.042, 2.28, 2.45, 0.072),
                                                  ('fingers_01_', 0.175, 2.145, 2.28, 0.08), ('fingers_02_', 0.18, 2.26, 2.41, 0.068))):
            mb.bone = bone + sd
            boulder(mb, P((x0 + x1) / 2, y, 2.28), sc3((x1 - x0) / 2, r, r * 1.0), 10, 300 + k * 7 + o, p=0.82, jag=0.08)
        mb.bone = 'thumb_01_' + sd
        boulder(mb, P(2.03, -0.135, 2.243), sc3(0.1, 0.085, 0.075), 10, 31 + o, p=0.8, jag=0.08)
        mb.bone = 'thumb_02_' + sd
        boulder(mb, P(2.14, -0.19, 2.222), sc3(0.09, 0.07, 0.062), 10, 32 + o, p=0.8, jag=0.08)
        # ------------------------------------------------------------------ legs
        mb.bone = 'thigh_' + sd
        ember(mb, P(0.27, 0, 1.09), 0.2 * S, 33 + o, 0.1, segs=7)                                      # hip joint
        plates(mb, P(0.285, 0.0, 0.86), sc3(0.245, 0.25, 0.27), 9, 34 + o, p=0.8, core_segs=(7, 4))
        mb.bone = 'shin_' + sd
        ember(mb, P(0.27, -0.01, 0.60), 0.16 * S, 35 + o, 0.3, segs=7)                                 # knee
        plates(mb, P(0.28, 0.01, 0.38), sc3(0.215, 0.225, 0.235), 8, 36 + o, p=0.8, core_segs=(7, 4))
        mb.bone = 'foot_' + sd
        ember(mb, P(0.27, 0.01, 0.15), 0.125 * S, 37 + o, 0.2)                                         # ankle
        boulder(mb, P(0.27, -0.07, 0.09), sc3(0.19, 0.2, 0.09), 16, 38 + o, p=0.8, flat_bottom=0.0)
        boulder(mb, P(0.27, 0.11, 0.09), sc3(0.15, 0.12, 0.09), 12, 39 + o, p=0.8, flat_bottom=0.0)
        ember(mb, P(0.27, -0.235, 0.06), sc3(0.17, 0.03, 0.045), 44 + o, 0.2, segs=6, rings=3)         # seam before the toes
        mb.bone = 'toe_' + sd
        for k, (tx, tr_) in enumerate(((0.14, 0.095), (0.275, 0.105), (0.41, 0.09))):
            boulder(mb, P(tx, -0.35, 0.085), sc3(tr_, 0.135, 0.085), 10, 41 + o + k, p=0.82, jag=0.08, flat_bottom=0.0)
    mb.bone = None


def main():
    reset_scene()
    warp = brute_warp(S)
    arm = build_humanoid_armature('Armature', warp=warp)
    mb = MB()
    build(mb)
    ob = mb.build('golem', all_preview_mats())
    skin_to(ob, arm)
    clips = None
    try:
        clips = Clips()
    except Exception as e:
        print('NO CLIPS', e)
    export_monster('golem', arm, ob, clips, max_tris=7000,
                   extra=dict(description='golem of cracked volcanic rock: rigid basalt plates on glowing ember cores',
                              warp='brute_warp(S=%.4f) in tools/blender/mon_lib.py' % S, handScale=round(2.7 * S, 3),
                              glowMaterial='M_ember (cores, joints, eyes, chest heart): swap for M_ice for the frost variant'))
    if '--nopreview' in sys.argv:
        return
    render_rest('golem', [ob])
    render_closeups('golem', [ob], [(Vector((-0.5, -0.7, 2.1)) * S, Vector((0.5, 0.3, 3.0)) * S, (-0.25, 0.95, -0.05)),
                                     (Vector((-0.5, -0.7, 2.1)) * S, Vector((0.5, 0.3, 3.0)) * S, (-0.9, 0.4, -0.1)),
                                     (Vector((-0.8, -0.6, 1.5)) * S, Vector((0.8, 0.6, 2.6)) * S, (0.0, 1, 0.0)),
                                     (Vector((1.6, -0.4, 1.9)) * S, Vector((2.5, 0.4, 2.6)) * S, (0.3, 0.6, -0.7)),
                                     (Vector((-0.6, -0.6, 0.0)) * S, Vector((0.6, 0.5, 1.2)) * S, (-0.5, 0.8, -0.2))])
    if clips:
        ratio = arm.data.bones['hips'].head_local.z / HUMAN_HIPS
        shots = [('m_idle', 0.5), ('m_walk', 0.25), ('m_swipe_R', None), ('m_smash', None), ('m_stomp', None), ('m_roar', 0.8),
                 ('hit_heavy', 0.2), ('death', -0.02)]
        render_poses('golem', arm, [ob], clips, shots, ratio, res=336)


if __name__ == '__main__':
    main()
