"""VALOMBRE skeleton warrior -> assets/models/creatures/skeleton.glb (human proportions, shared rig, no warp).
Every bone piece is rigidly skinned to its rig bone; the cloth remains are blended down the spine.

Run:  blender -b --factory-startup -P tools/blender/mon_skeleton.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mon_lib import *

IV, IV_DK, IV_DEEP, IV_HI, IV_STAIN = C('#cdbf9f'), C('#8a7858'), C('#3d3327'), C('#e9dfc6'), C('#a08c62')
HOLLOW = C('#14100c')
CLOTH, CLOTH_DK = C('#5a2a26'), C('#2e1715')
STRAP, STRAP_DK = C('#3b2a1f'), C('#221812')
EYE = C('#9dffd2')


def bcol(p, k=0.0):
    """Aged ivory; k = 0 shaft .. 1 joint end (darker, dirtier)."""
    c = mix(IV, IV_DK, clamp01(k))
    c = mix(c, IV_STAIN, 0.55 * sstep(0.48, 0.7, fbm(p, 17.0, 3, 2)))
    return mul(c, 0.86 + 0.24 * vnoise(p, 70.0, 5))


def btube(mb, st, segs=6, up=(0, 0, 1), cap=True, sharp=55.0, closed=False):
    """st = [(point, r | (ra, rb), darkness)...]"""
    ks = [s[2] if len(s) > 2 else 0.0 for s in st]
    mb.tube([Vector(s[0]) for s in st], [s[1] for s in st], segs, 'M_bone', lambda p, i, j: bcol(p, ks[min(i, len(ks) - 1)]),
            up=up, cap0='fan' if cap else None, cap1='fan' if cap else None, sharp=sharp, closed_path=closed)


def phal(mb, a, b, ra, rb, up=(0, 0, 1), k0=0.5, k1=0.3):
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    u = (Vector(up) - ax * Vector(up).dot(ax)).normalized()
    v = ax.cross(u)
    rings = [[p + u * r + v * r * 0.0, p + v * r, p - u * r, p - v * r] for p, r in ((a, ra), (b, rb))]
    rings = [[p + u * r, p + v * r * 1.15, p - u * r, p - v * r * 1.15] for p, r in ((a, ra), (a.lerp(b, 0.5), (ra + rb) * 0.42), (b, rb))]
    mb.loft(rings, [bcol(a, k0), bcol(a, 0.0), bcol(b, k1)], 'M_bone', True, 'ngon', 'ngon', 50.0)


def y_spine(z):
    if z >= 1.50:
        return 0.03 + (0.014 - 0.03) * clamp01((z - 1.50) / 0.10)
    if z >= 1.20:
        return 0.03 + 0.03 * math.sin(math.pi * (z - 1.20) / 0.30)
    return 0.03 - 0.016 * math.sin(math.pi * clamp01((1.20 - z) / 0.24))


def spine_bone(z):
    return 'hips' if z < 1.08 else 'spine_01' if z < 1.20 else 'spine_02' if z < 1.34 else 'spine_03' if z < 1.50 else 'neck'


def w_torso(p):
    """Smooth weights down the trunk for cloth / straps."""
    z = p.z
    ch = [('hips', 1.03), ('spine_01', 1.14), ('spine_02', 1.27), ('spine_03', 1.40)]
    if z >= ch[-1][1]:
        return {'spine_03': 1.0}
    if z <= ch[0][1]:
        k = 0.55 * sstep(0.98, 0.78, z)
        if k <= 0.01:
            return {'hips': 1.0}
        if p.x > 0.035:
            return {'hips': 1 - k, 'thigh_L': k}
        if p.x < -0.035:
            return {'hips': 1 - k, 'thigh_R': k}
        return {'hips': 1 - k * 0.6, 'thigh_L': k * 0.3, 'thigh_R': k * 0.3}
    for (n0, z0), (n1, z1) in zip(ch[:-1], ch[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return {n0: 1 - t, n1: t}


def cloth(mb, grid, col_fn, mat='M_cloth'):
    """Double-sided cloth patch from a point grid [col][row] (None = hole)."""
    mb.keep = True
    old = mb.fn_w
    mb.fn_w = w_torso
    for sidek in (0, 1):
        ids = [[(mb.add(p, col_fn(p, sidek)) if p is not None else None) for p in colm] for colm in grid]
        for i in range(len(grid) - 1):
            for j in range(len(grid[i]) - 1):
                if j + 1 >= len(grid[i + 1]):
                    continue
                q = [ids[i][j], ids[i + 1][j], ids[i + 1][j + 1], ids[i][j + 1]]
                q = [k for k in q if k is not None]
                if len(q) < 3:
                    continue
                mb.face(q if sidek == 0 else q[::-1], mat, None, 40.0)
    mb.fn_w = old
    mb.keep = False


def build(mb):
    # ------------------------------------------------------------------ skull
    mb.bone = 'head'
    cc = Vector((0, 0.014, 1.718))
    m = mb.mark()

    def skull_col(p, i, j):
        k = sstep(-0.02, -0.045, p.y) * sstep(1.728, 1.705, p.z)          # face cavity wall = shadow
        c = bcol(p, 0.25 * sstep(1.70, 1.64, p.z))
        return mix(c, HOLLOW, k)

    mb.sphere(cc, (0.074, 0.093, 0.080), 'M_bone', (1, 1, 1), segs=10, rings=7, sharp=70.0)

    def skull_shape(p):
        p = p.copy()
        k = sstep(1.735, 1.70, p.z)
        if p.y < -0.03:
            p.y = -0.03 + (p.y + 0.03) * (1.0 - 0.72 * k)                  # recess behind the face bones
        p.z = max(p.z, 1.644)
        p.x *= 1.0 - 0.1 * sstep(1.70, 1.65, p.z)
        if p.y > 0.03 and p.z < 1.70:
            p.y *= 1.0 - 0.12 * sstep(1.70, 1.65, p.z)
        return p

    mb.displace(m, skull_shape)
    mb.recolor(m, lambda p, c: skull_col(p, 0, 0))
    # brow ridge, nasal bone, orbit rims, cheekbones
    btube(mb, [((-0.068, -0.040, 1.706), (0.008, 0.007), 0.3), ((-0.052, -0.072, 1.716), (0.0105, 0.0085)), ((-0.022, -0.087, 1.713), (0.0105, 0.0085)),
               ((0, -0.089, 1.708), (0.0095, 0.008), 0.2), ((0.022, -0.087, 1.713), (0.0105, 0.0085)), ((0.052, -0.072, 1.716), (0.0105, 0.0085)),
               ((0.068, -0.040, 1.706), (0.008, 0.007), 0.3)], segs=5)
    mb.cbox((0.021, 0.015, 0.042), 'M_bone', lambda p, i, j: bcol(p, 0.2), tr(0, -0.083, 1.688) @ rot('X', -12), taper=0.7)
    for sx in (1, -1):
        btube(mb, [((sx * 0.016, -0.080, 1.663), (0.007, 0.0065), 0.3), ((sx * 0.044, -0.078, 1.661), (0.008, 0.0065)),
                   ((sx * 0.066, -0.058, 1.667), (0.0085, 0.006)), ((sx * 0.0745, -0.02, 1.672), (0.007, 0.0045), 0.2),
                   ((sx * 0.073, 0.018, 1.677), (0.006, 0.004), 0.4)], segs=5)
        btube(mb, [((sx * 0.064, -0.052, 1.708), 0.0062, 0.2), ((sx * 0.067, -0.056, 1.668), 0.0062, 0.2)], segs=4, up=(1, 0, 0), cap=False)
    # maxilla + teeth
    mb.cbox((0.068, 0.04, 0.036), 'M_bone', lambda p, i, j: bcol(p, 0.25 + 0.5 * sstep(1.645, 1.655, p.z) * (abs(p.x) < 0.014)),
            tr(0, -0.072, 1.6365), ch=0.007)

    def teeth(z, rx, ry, y0, n, a_max, h):
        st = []
        for i in range(n):
            a = math.radians(-a_max + 2 * a_max * i / (n - 1))
            st.append(Vector((rx * math.sin(a), y0 - ry * math.cos(a), z)))
        mb.tube(st, [(h * 1.4142, 0.0042 * 1.4142)] * n, 4, 'M_bone', lambda p, i, j: (IV_HI if i % 2 == 0 else IV_DEEP), up=(0, 0, 1),
                phase=math.pi / 4, sharp=40.0)

    teeth(1.6135, 0.033, 0.056, -0.038, 13, 78, 0.0065)
    # mandible (hanging a little open)
    jaw = [((0.058, 0.012, 1.654), 0.0075, 0.6), ((0.057, 0.010, 1.606), 0.0085, 0.2), ((0.046, -0.044, 1.585), (0.0085, 0.011)),
           ((0.024, -0.082, 1.577), (0.0085, 0.0125)), ((0, -0.093, 1.575), (0.009, 0.0135), 0.1), ((-0.024, -0.082, 1.577), (0.0085, 0.0125)),
           ((-0.046, -0.044, 1.585), (0.0085, 0.011)), ((-0.057, 0.010, 1.606), 0.0085, 0.2), ((-0.058, 0.012, 1.654), 0.0075, 0.6)]
    btube(mb, jaw, segs=5, up=(0, 1, 0))
    teeth(1.5965, 0.030, 0.052, -0.036, 11, 74, 0.006)
    # glowing eyes deep in the sockets
    for sx in (1, -1):
        mb.sphere((sx * 0.036, -0.057, 1.689), 0.0125, 'M_eye_glow', EYE, segs=6, rings=4)
    # battered iron cap with a nasal bar
    m = mb.mark()
    ic = lambda p, i=0, j=0: rust(p, mul(IRON, 0.7 + 0.3 * vnoise(p, 30.0, 7)), 0.4, 4, 16.0)
    mb.lathe([(0.0915, 1.727), (0.094, 1.735), (0.089, 1.762), (0.074, 1.79), (0.045, 1.808), (0, 1.815)], 8, 'M_metal_iron',
             tr(0, 0.012, 0), cols=ic, sx=0.9, sy=1.1, sharp=50.0, cap0='ngon', phase=math.pi / 8)
    mb.cbox((0.019, 0.006, 0.075), 'M_metal_iron', ic, tr(0, -0.0985, 1.696) @ rot('X', -5), taper=0.8)
    mb.displace(m, lambda p: p + Vector((0, 0, -0.012)) * sstep(0.03, 0.085, p.x) * sstep(1.77, 1.80, p.z))     # dent
    # ------------------------------------------------------------------ spine
    zs = [0.992, 1.032, 1.072, 1.112, 1.152] + [1.20 + 0.0335 * i for i in range(9)] + [1.508, 1.531, 1.553, 1.574]
    for i, z in enumerate(zs):
        lumbar, cerv = i < 5, i >= 14
        r = 0.0225 if lumbar else (0.0135 if cerv else 0.0185 - 0.0003 * (i - 5))
        h = (0.031 if lumbar else (0.017 if cerv else 0.026))
        mb.bone = spine_bone(z + h * 0.5)
        y = y_spine(z + h * 0.5)
        mb.lathe([(0, z, bcol((0, y, z), 0.7)), (r, z + h * 0.18, bcol((r, y, z), 0.3)), (r * 0.9, z + h * 0.82, bcol((r, y, z + h), 0.3)),
                  (0, z + h, bcol((0, y, z + h), 0.7))], 6, 'M_bone', tr(0, y, 0), sy=0.85, sharp=50.0)
        mb.spike((0, y + r * 0.7, z + h * 0.6), (0, y + r * 0.7 + (0.03 if not cerv else 0.018), z + h * 0.1 - 0.008), r * 0.45, 'M_bone',
                 bcol((0, y, z), 0.4), segs=4, tipcol=bcol((0, y, z), 0.1))
    # ------------------------------------------------------------------ rib cage
    aw = [0.062, 0.086, 0.104, 0.117, 0.127, 0.133, 0.136, 0.134, 0.127, 0.112]
    yf = [-0.058, -0.078, -0.093, -0.103, -0.109, -0.111, -0.109, -0.104, -0.097, -0.088]
    for i in range(10):
        z0 = 1.458 - i * 0.0268
        mb.bone = 'spine_03' if z0 >= 1.34 else 'spine_02'
        yb = y_spine(z0) + 0.036
        yc, b = (yb + yf[i]) * 0.5, (yb - yf[i]) * 0.5
        end = 0.93 if i < 7 else (0.78 if i < 9 else 0.6)
        drop = 0.03 + 0.004 * i
        for sx in (1, -1):
            st = []
            n = 7
            for k in range(n):
                ph = math.pi * (0.07 + (end - 0.07) * k / (n - 1))
                p = Vector((sx * aw[i] * math.sin(ph) ** 0.85, yc + b * math.cos(ph), z0 - drop * (1 - math.cos(ph)) * 0.5))
                rr = 0.0078 if 0 < k < n - 1 else 0.006
                st.append((p, (rr * 1.4142, 0.0044 * 1.4142), 0.55 if k in (0, n - 1) else 0.05))
            ks = [s[2] for s in st]
            mb.tube([s[0] for s in st], [s[1] for s in st], 4, 'M_bone',
                    lambda p, i_, j, ks=ks: mul(bcol(p, ks[i_]), 0.78 if j in (1, 2) and False else 1.0), up=(0, 0, 1),
                    phase=math.pi / 4, sharp=50.0)
    mb.bone = 'spine_03'
    mb.cbox((0.044, 0.012, 0.165), 'M_bone', lambda p, i, j: bcol(p, 0.25), tr(0, -0.1005, 1.365) @ rot('X', 171), taper=0.5)
    # ------------------------------------------------------------------ limbs
    for S, sx in (('L', 1.0), ('R', -1.0)):
        def P(x, y, z):
            return Vector((sx * x, y, z))
        # shoulder girdle
        mb.bone = 'clavicle_' + S
        btube(mb, [(P(0.018, -0.090, 1.447), 0.0075, 0.5), (P(0.062, -0.086, 1.455), 0.0062), (P(0.115, -0.046, 1.468), 0.0062),
                   (P(0.168, -0.008, 1.48), 0.008, 0.5)], segs=5)
        nrm_ = Vector((sx * 0.35, 0.93, 0.1)).normalized()
        pl = [P(0.168, 0.034, 1.48), P(0.074, 0.08, 1.462), P(0.104, 0.086, 1.305), P(0.15, 0.062, 1.40)]
        mb.hull([p + nrm_ * d for p in pl for d in (0.0035, -0.0035)], lambda p, i, j: bcol(p, 0.3), 'M_bone', sharp=40.0)
        btube(mb, [(P(0.082, 0.089, 1.438), 0.005, 0.3), (P(0.17, 0.042, 1.482), 0.0065, 0.4)], segs=4, up=(0, 0, 1))
        # humerus
        mb.bone = 'upper_arm_' + S
        mb.sphere(P(0.196, 0.0, 1.471), 0.0235, 'M_bone', lambda p, i, j: bcol(p, 0.45), segs=6, rings=4)
        btube(mb, [(P(0.20, 0, 1.47), 0.016, 0.5), (P(0.235, 0, 1.47), 0.0125, 0.1), (P(0.33, 0, 1.47), 0.0108), (P(0.42, 0, 1.47), 0.011),
                   (P(0.452, 0, 1.47), (0.0125, 0.02), 0.4), (P(0.468, 0, 1.47), (0.0135, 0.0235), 0.7)], segs=6)
        # radius (thumb side, -Y) and ulna
        mb.bone = 'forearm_' + S
        btube(mb, [(P(0.476, -0.013, 1.471), 0.0095, 0.6), (P(0.50, -0.015, 1.471), 0.007, 0.1), (P(0.64, -0.016, 1.47), 0.0072),
                   (P(0.705, -0.016, 1.47), 0.0095, 0.3), (P(0.727, -0.015, 1.47), 0.0115, 0.7)], segs=5)
        btube(mb, [(P(0.456, 0.013, 1.466), 0.012, 0.7), (P(0.485, 0.013, 1.468), 0.011, 0.3), (P(0.56, 0.014, 1.47), 0.0075),
                   (P(0.70, 0.015, 1.47), 0.0062, 0.2), (P(0.726, 0.015, 1.47), 0.0078, 0.7)], segs=5)
        # hand
        mb.bone = 'hand_' + S
        mb.cbox((0.028, 0.05, 0.017), 'M_bone', lambda p, i, j: bcol(p, 0.6), tr(sx * 0.744, 0.0, 1.468))
        for y0, y1 in ((-0.02, -0.031), (-0.007, -0.009), (0.007, 0.013), (0.02, 0.033)):
            phal(mb, P(0.757, y0, 1.468), P(0.809, y1, 1.47), 0.0052, 0.006, k0=0.6, k1=0.5)
        mb.bone = 'index_01_' + S
        phal(mb, P(0.811, -0.031, 1.47), P(0.856, -0.032, 1.47), 0.0054, 0.0046)
        mb.bone = 'index_02_' + S
        phal(mb, P(0.858, -0.032, 1.47), P(0.906, -0.034, 1.47), 0.0046, 0.003, k1=0.1)
        for y0, y1, l1, l2 in ((-0.009, -0.0085, 0.862, 0.918), (0.013, 0.0145, 0.860, 0.910), (0.033, 0.036, 0.852, 0.892)):
            mb.bone = 'fingers_01_' + S
            phal(mb, P(0.811, y0, 1.47), P(l1 - 0.002, y1, 1.47), 0.0054, 0.0046)
            mb.bone = 'fingers_02_' + S
            phal(mb, P(l1, y1, 1.47), P(l2, y1 + (y1 - y0) * 0.6, 1.47), 0.0046, 0.003, k1=0.1)
        mb.bone = 'thumb_01_' + S
        phal(mb, P(0.752, -0.028, 1.463), P(0.789, -0.055, 1.452), 0.0062, 0.0055)
        mb.bone = 'thumb_02_' + S
        phal(mb, P(0.792, -0.057, 1.452), P(0.826, -0.072, 1.446), 0.0052, 0.0032, k1=0.1)
        # hip bone
        mb.bone = 'hips'
        wing = [P(0.044, 0.064, 1.034), P(0.086, 0.074, 1.083), P(0.133, 0.022, 1.094), P(0.139, -0.044, 1.064), P(0.119, -0.064, 1.02),
                P(0.102, -0.02, 0.953), P(0.072, 0.046, 0.963)]
        inw = [p + Vector((-sx * 0.012, -0.004 if p.y > 0 else 0.006, -0.004)) for p in wing]
        mb.hull(wing + inw, lambda p, i, j: bcol(p, 0.25 + 0.4 * sstep(1.0, 0.95, p.z)), 'M_bone', sharp=32.0)
        btube(mb, [(P(0.097, -0.004, 0.947), 0.0135, 0.4), (P(0.064, 0.04, 0.869), 0.0125, 0.2), (P(0.022, -0.032, 0.878), 0.0095),
                   (P(0.013, -0.064, 0.914), 0.011, 0.3), (P(0.084, -0.047, 0.95), 0.0105, 0.2)], segs=4, cap=False, closed=True)
        # femur
        mb.bone = 'thigh_' + S
        mb.sphere(P(0.086, -0.003, 0.941), 0.0215, 'M_bone', lambda p, i, j: bcol(p, 0.5), segs=6, rings=4)
        btube(mb, [(P(0.089, -0.003, 0.938), 0.0125, 0.4), (P(0.111, 0.0, 0.921), 0.014, 0.3)], segs=5, up=(0, 1, 0), cap=False)
        btube(mb, [(P(0.115, 0.002, 0.934), (0.017, 0.016), 0.6), (P(0.111, 0.0, 0.905), (0.0165, 0.0175), 0.3), (P(0.105, -0.003, 0.83), 0.014),
                   (P(0.10, -0.006, 0.66), 0.013), (P(0.10, -0.005, 0.555), (0.0165, 0.02), 0.25), (P(0.10, -0.004, 0.522), (0.0235, 0.031), 0.6),
                   (P(0.10, -0.002, 0.506), (0.0215, 0.029), 0.8)], segs=6, up=(0, 1, 0))
        # patella, tibia, fibula
        mb.bone = 'shin_' + S
        mb.sphere(P(0.10, -0.034, 0.503), (0.0175, 0.0095, 0.02), 'M_bone', lambda p, i, j: bcol(p, 0.35), segs=5, rings=3)
        btube(mb, [(P(0.10, -0.005, 0.497), (0.021, 0.0295), 0.8), (P(0.10, -0.007, 0.468), (0.0185, 0.022), 0.4), (P(0.10, -0.004, 0.40), 0.014),
                   (P(0.10, 0.006, 0.22), 0.0118), (P(0.10, 0.013, 0.115), (0.014, 0.0155), 0.3), (P(0.10, 0.015, 0.084), (0.017, 0.021), 0.75)],
              segs=6, up=(0, 1, 0))
        btube(mb, [(P(0.129, 0.012, 0.472), 0.0078, 0.6), (P(0.131, 0.016, 0.42), 0.0055, 0.1), (P(0.128, 0.022, 0.16), 0.0055),
                   (P(0.124, 0.021, 0.082), 0.0082, 0.6)], segs=4, up=(0, 1, 0))
        # foot
        mb.bone = 'foot_' + S
        mb.cbox((0.05, 0.068, 0.042), 'M_bone', lambda p, i, j: bcol(p, 0.55), tr(sx * 0.10, -0.006, 0.058) @ rot('X', 18), ch=0.008)
        mb.cbox((0.036, 0.062, 0.046), 'M_bone', lambda p, i, j: bcol(p, 0.5), tr(sx * 0.103, 0.05, 0.03) @ rot('X', -12), ch=0.008)
        for i in range(5):
            x0, x1 = 0.079 + i * 0.011, 0.066 + i * 0.0175
            r = 0.0085 if i == 0 else 0.006
            z1 = 0.017 if i == 0 else 0.014
            mb.bone = 'foot_' + S
            phal(mb, P(x0, -0.036, 0.05 - i * 0.003), P(x1, -0.113, z1), r, r * 1.05, up=(0, 0, 1), k0=0.6, k1=0.5)
            mb.bone = 'toe_' + S
            ln = (0.056, 0.047, 0.042, 0.036, 0.03)[i]
            phal(mb, P(x1, -0.117, z1 - 0.001), P(x1 + (i - 1.5) * 0.002, -0.117 - ln, 0.0085 if i else 0.011), r * 0.95, r * 0.6, k1=0.1)
    mb.bone = 'hips'
    mb.cbox((0.088, 0.036, 0.10), 'M_bone', lambda p, i, j: bcol(p, 0.4), tr(0, 0.054, 1.004) @ rot('X', 188), taper=0.45)
    mb.spike((0, 0.066, 0.957), (0, 0.05, 0.912), 0.012, 'M_bone', bcol((0, 0, 0.95), 0.5), segs=4)

    # ------------------------------------------------------------------ remains of gear
    # rusted pauldron on the left shoulder + one lame on the arm
    mb.bone = 'clavicle_L'
    icp = lambda p, i=0, j=0: rust(p, mul(IRON, 0.7 + 0.3 * vnoise(p, 26.0, 2)), 0.42, 9, 14.0)
    Mp = tr(0.198, 0.004, 1.474) @ rot('Y', 14)
    mb.lathe([(0.095, -0.012), (0.1, 0.002), (0.094, 0.022), (0.072, 0.045), (0.038, 0.058), (0, 0.062)], 8, 'M_metal_iron', Mp, cols=icp,
             sx=1.0, sy=0.98, sharp=45.0, cap0='ngon', phase=math.pi / 8)
    mb.C[-1] = icp(Vector((0.2, 0, 1.53)))
    for a in (40, 140, 220, 320):
        rivet(mb, Mp @ Vector((0.088 * math.cos(math.radians(a)), 0.088 * math.sin(math.radians(a)), 0.03)),
              Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.5)), 0.006, 'M_metal_iron', IRON_EDGE)
    mb.bone = 'upper_arm_L'
    mb.lathe([(0.066, -0.022), (0.07, -0.006), (0.064, 0.012), (0.04, 0.026), (0, 0.03)], 7, 'M_metal_iron', tr(0.30, 0.004, 1.482) @ rot('Y', 8),
             cols=icp, sx=1.05, sy=0.95, sharp=45.0, cap0='ngon')
    # torn tabard: front panel, back panel, shoulder bands
    def ccol(p, sidek):
        n = fbm(p, 9.0, 12, 3)
        c = mix(CLOTH, CLOTH_DK, 0.6 * sstep(0.4, 0.7, n))
        c = mul(c, 0.72 + 0.4 * vnoise(p, 30.0, 6))
        c = mul(c, 1.0 - 0.45 * sstep(1.0, 0.72, p.z))                    # mud at the hem
        return mul(c, 0.62) if sidek else c

    def yfront(z, x):
        pts = [(1.50, -0.01), (1.458, -0.074), (1.40, -0.114), (1.33, -0.128), (1.22, -0.122), (1.12, -0.108), (1.035, -0.106), (0.93, -0.098), (0.70, -0.09)]
        for (z0, y0), (z1, y1) in zip(pts[:-1], pts[1:]):
            if z1 <= z <= z0:
                t = (z0 - z) / (z0 - z1)
                return y0 + (y1 - y0) * t + 1.5 * x * x
        return pts[-1][1] + 1.5 * x * x

    def yback(z, x):
        pts = [(1.50, 0.0), (1.458, 0.086), (1.40, 0.118), (1.30, 0.118), (1.18, 0.092), (1.035, 0.104), (0.93, 0.10), (0.70, 0.095)]
        for (z0, y0), (z1, y1) in zip(pts[:-1], pts[1:]):
            if z1 <= z <= z0:
                t = (z0 - z) / (z0 - z1)
                return y0 + (y1 - y0) * t - 1.3 * x * x
        return pts[-1][1] - 1.3 * x * x

    rnd = random.Random(5)
    xs = [-0.108, -0.056, 0.0, 0.056, 0.108]
    zrow = [1.458, 1.40, 1.33, 1.22, 1.12, 1.035]
    grid = [[Vector((x, yfront(z, x), z)) for z in zrow] for x in xs]
    cloth(mb, grid, ccol)
    # tatters below the belt: three strips of unequal length
    for xa, xb, zend, jit in ((-0.108, -0.05, 0.80, 0.012), (-0.038, 0.034, 0.69, 0.01), (0.056, 0.108, 0.90, 0.014)):
        zr = [1.035, 1.035 - (1.035 - zend) * 0.4, 1.035 - (1.035 - zend) * 0.75, zend]
        g = []
        for x in (xa, (xa + xb) * 0.5, xb):
            colm = []
            for k, z in enumerate(zr):
                zz = z - (rnd.uniform(0.0, 0.05) if k == len(zr) - 1 else 0.0)
                xx = x + rnd.uniform(-jit, jit) * k
                colm.append(Vector((xx, yfront(zz, xx) + 0.004 * k, zz)))
            g.append(colm)
        g[1][-1] = g[1][-1] + Vector((0, 0, -0.045))
        cloth(mb, g, ccol)
    zrow_b = [1.458, 1.40, 1.30, 1.18, 1.07]
    xsb = [-0.10, -0.035, 0.04, 0.10]
    gridb = [[Vector((x, yback(z, x), z - (0.03 * abs(math.sin(x * 40)) if z < 1.1 else 0))) for z in zrow_b] for x in xsb]
    cloth(mb, gridb, ccol)
    g = [[Vector((x + 0.006 * k, yback(z, x) + 0.004 * k, z)) for k, z in enumerate((1.07, 0.97, 0.86, 0.78))] for x in (-0.035, 0.0, 0.04)]
    g[1][-1] = g[1][-1] + Vector((0.01, 0, -0.05))
    cloth(mb, g, ccol)
    for sx in (1, -1):
        g = [[Vector((sx * x, y, z)) for (y, z) in ((-0.074, 1.458), (-0.045, 1.492), (0.0, 1.507), (0.05, 1.494), (0.086, 1.458))]
             for x in (0.052, 0.108)]
        cloth(mb, g, ccol)
    # belt + diagonal strap (dark leather-like bands)
    def scol(p, i, j):
        return mul(mix(STRAP, STRAP_DK, vnoise(p, 25.0, 3)), 0.85 + 0.3 * vnoise(p, 60.0, 9))

    mb.fn_w = w_torso
    path = []
    for k in range(12):
        a = 2 * math.pi * k / 12
        x, yy = 0.152 * math.cos(a), 0.004 + 0.112 * math.sin(a)
        path.append(Vector((x, yy, 1.036 + 0.008 * math.cos(a * 2))))
    mb.tube(path, [(0.0165 * 1.4142, 0.0045 * 1.4142)] * 12, 4, 'M_cloth', scol, up=(0, 0, 1), phase=math.pi / 4, closed_path=True, sharp=35.0)
    strap = [(-0.112, 0.0, 1.512), (-0.088, -0.088, 1.45), (-0.035, -0.138, 1.34), (0.04, -0.14, 1.215), (0.112, -0.112, 1.09), (0.158, -0.01, 1.03),
             (0.115, 0.098, 1.10), (0.03, 0.125, 1.25), (-0.055, 0.128, 1.385), (-0.105, 0.085, 1.475)]
    mb.tube([Vector(p) for p in strap], [(0.0048 * 1.4142, 0.017 * 1.4142)] * len(strap), 4, 'M_cloth', scol, up=(0, 1, 0), phase=math.pi / 4,
            closed_path=True, sharp=35.0)
    mb.fn_w = None
    mb.bone = 'hips'
    mb.cbox((0.04, 0.008, 0.042), 'M_metal_iron', lambda p, i, j: rust(p, IRON, 0.45, 3, 30.0), tr(0.0, -0.112, 1.044), ch=0.004)
    mb.bone = 'spine_03'
    mb.cbox((0.03, 0.008, 0.032), 'M_metal_iron', lambda p, i, j: rust(p, IRON, 0.45, 5, 30.0), tr(-0.04, -0.142, 1.348) @ rot('Y', 35), ch=0.003)
    mb.bone = None


def main():
    reset_scene()
    arm = build_humanoid_armature('Armature')
    mb = MB()
    build(mb)
    for i, w in enumerate(mb.W):
        if w is None:
            mb.W[i] = 'spine_03'
    ob = mb.build('skeleton', all_preview_mats())
    skin_to(ob, arm)
    clips = None
    try:
        clips = Clips()
    except Exception as e:
        print('NO CLIPS', e)
    entry = export_monster('skeleton', arm, ob, clips, max_tris=6000,
                           extra=dict(description='skeleton warrior: rigid bones, rusted cap and pauldron, torn tabard',
                                      warp='none (human proportions)'))
    if '--nopreview' in sys.argv:
        return
    render_rest('skeleton', [ob])
    render_closeups('skeleton', [ob], [((-0.13, -0.14, 1.52), (0.13, 0.12, 1.83), (0, 1, 0)), ((-0.13, -0.14, 1.52), (0.13, 0.12, 1.83), (-0.75, 0.62, -0.1)),
                                         ((-0.3, -0.2, 1.12), (0.3, 0.2, 1.55), (-0.3, 0.9, -0.1)), ((-0.25, -0.15, 0.82), (0.25, 0.15, 1.15), (-0.2, 0.95, 0.1)),
                                         ((0.68, -0.1, 1.40), (0.95, 0.1, 1.54), (0.05, 0.3, -1.0))])
    if clips:
        shots = [('idle', 0.5), ('idle_combat', 0.4), ('run', 0.12), ('atk1h_heavy', None), ('block_idle', 0.3), ('roll', 0.3),
                 ('kneel', 0.5), ('death', -0.02)]
        render_poses('skeleton', arm, [ob], clips, shots, 1.0, res=336)


if __name__ == '__main__':
    main()
