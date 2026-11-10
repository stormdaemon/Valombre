"""Topology of the body below the collar: torso, arms, hands, legs, feet (left half, see human_mesh.py)."""
import math
import numpy as np
from human_mesh import *

X = V3(1, 0, 0)
Y = V3(0, 1, 0)
Z = V3(0, 0, 1)

# ----------------------------------------------------------------------------- torso
TH = [0, 8, 16, 24, 32, 40, 48, 55, 61, 75.5, 90, 104.5, 119, 125, 132, 140, 148, 156, 164, 172, 180]
TZ = [0.895, 0.930, 0.965, 1.000, 1.040, 1.080, 1.120, 1.160, 1.200, 1.240, 1.280, 1.320, 1.355, 1.385]
J_HIP = 3                # torso ring index of the hip line (torso / legs split)
J_ARMPIT = len(TZ) - 1
TAX = 0.010
XJ = 0.172               # plane of the arm / torso junction ring
ARM_Z = 1.469


def coons(P, i, r, i0, i1, r0, r1):
    u = (i - i0) / float(i1 - i0)
    v = (r - r0) / float(r1 - r0)
    return ((1 - v) * P(i, r0) + v * P(i, r1) + (1 - u) * P(i0, r) + u * P(i1, r)
            - ((1 - u) * (1 - v) * P(i0, r0) + u * (1 - v) * P(i1, r0) + (1 - u) * v * P(i0, r1) + u * v * P(i1, r1)))


def build_torso(mb):
    S = SID['body']
    col = mb.sets['collar']
    T = -np.ones((21, 20), int)
    for j, z in enumerate(TZ):
        for i, th in enumerate(TH):
            a = math.radians(th)
            T[i, j] = mb.ray((0, TAX, z), (math.sin(a), -math.cos(a), 0), 'torso', S, tmax=0.3, rw=0.15)
    ja = J_ARMPIT
    # junction ring (arm ring 0): bottom = top row of the side panel
    J = [None] * 20
    for i in range(8, 13):
        J[25 - i] = T[i, ja]
    oj = V3(XJ, 0.004, 1.452)
    for k in (18, 19, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        a = math.radians(18 * k)
        J[k] = mb.ray(oj, (0, -math.cos(a), math.sin(a)), 'torso', S, tmax=0.2, rw=0.3)
    mb.flush()
    P = lambda i, r: mb.pos(T[i, r])
    # ---- front panel
    for r in range(ja + 1, ja + 6):
        T[8, r] = J[(17 + (r - ja)) % 20]
    T[8, ja + 6] = J[3]
    for i in range(5):
        T[i, ja + 6] = col[i]
    zn = mb.pos(col[0])[2]
    for r in range(ja + 1, ja + 6):
        t = (r - ja) / 6.0
        T[0, r] = mb.ray((0, TAX, lerp(TZ[ja], zn, t)), (0, -1, 0), 'torso', S, tmax=0.3, rw=0.2)
    for i in (5, 6, 7):
        t = (i - 4) / 4.0
        p = lerp(mb.pos(col[4]), mb.pos(J[3]), t) + V3(0, -0.004, 0.004) * math.sin(math.pi * t)
        T[i, ja + 6] = mb.cp(p, 'torso', S, rw=0.3)
    # ---- back panel
    for r in range(ja + 1, ja + 6):
        T[12, r] = J[13 - (r - ja)]
    T[12, ja + 6] = J[7]
    for i in range(16, 21):
        T[i, ja + 6] = col[i - 8]
    zb = mb.pos(col[12])[2]
    for r in range(ja + 1, ja + 6):
        t = (r - ja) / 6.0
        T[20, r] = mb.ray((0, TAX, lerp(TZ[ja], zb, t)), (0, 1, 0), 'torso', S, tmax=0.3, rw=0.2)
    for i in (13, 14, 15):
        t = (i - 12) / 4.0
        p = lerp(mb.pos(J[7]), mb.pos(col[8]), t) + V3(0, 0.004, 0.004) * math.sin(math.pi * t)
        T[i, ja + 6] = mb.cp(p, 'torso', S, rw=0.3)
    mb.flush()
    for (i0, i1) in ((0, 8), (12, 20)):
        for i in range(i0 + 1, i1):
            for r in range(ja + 1, ja + 6):
                p = coons(P, i, r, i0, i1, ja, ja + 6)
                o = V3(0, TAX, min(p[2], 1.43))
                T[i, r] = mb.ray(o, p - o, 'torso', S, tmax=0.3, rw=0.3)
    # ---- shoulder cap
    C = -np.ones((5, 5), int)
    for c in range(5):
        C[c, 0] = T[4 + c, ja + 6]
        C[c, 4] = T[16 - c, ja + 6]
    for r in range(5):
        C[0, r] = col[4 + r]
        C[4, r] = J[3 + r]
    mb.flush()
    PC = lambda c, r: mb.pos(C[c, r])
    for c in range(1, 4):
        for r in range(1, 4):
            p = coons(PC, c, r, 0, 4, 0, 4)
            o = V3(p[0] * 0.7, p[1] * 0.5 + 0.005, 1.40)
            C[c, r] = mb.ray(o, p - o, 'torso', S, tmax=0.3, rw=0.4)
    # ---- faces
    for i in range(20):
        for j in range(ja):
            mb.quad(T[i, j], T[i + 1, j], T[i + 1, j + 1], T[i, j + 1], 'legs' if j < J_HIP else 'torso')
    mb.grid(T[0:9, ja:ja + 7], 'torso')
    mb.grid(T[12:21, ja:ja + 7], 'torso')
    mb.grid(C, 'torso')
    mb.flush()
    # navel: one pushed-in vertex
    nv = T[0, 5]
    mb.P[nv] = mb.P[nv] + V3(0, 0.007, 0)
    mb.rw[nv] = 0.0
    mb.col[nv] = (None, 0.35, None)
    mb.sets['torso'] = T
    mb.sets['junction'] = J
    return T, J


# ----------------------------------------------------------------------------- arm
AX = [0.205, 0.235, 0.270, 0.305, 0.340, 0.375, 0.410, 0.440, 0.458, 0.472, 0.486, 0.505, 0.535, 0.570, 0.610,
      0.650, 0.685, 0.710, 0.727]


def build_arm(mb, J):
    S = SID['body']
    rings = [list(J)]
    for x in AX:
        ring = []
        for k in range(20):
            a = math.radians(18 * k)
            ring.append(mb.ray((x, 0.0, ARM_Z), (0, -math.cos(a), math.sin(a)), 'arm', S, tmax=0.12,
                               rw=0.0 if x == AX[-1] else 0.15))
        rings.append(ring)
    for n in range(len(rings) - 1):
        mb.strip(rings[n], rings[n + 1], 'torso' if n == 0 else 'arms', closed=True)
    mb.sets['arm_rings'] = rings
    mb.flush()
    return rings


# ----------------------------------------------------------------------------- hand (explicit)
HZ = 1.470
PX = [0.727, 0.745, 0.762, 0.779, 0.795, 0.810]
F_Y = [-0.0312, -0.0096, 0.0122, 0.0322]
F_B = [-0.0420, -0.0206, 0.0013, 0.0231, 0.0420]
F_XK = [0.810, 0.813, 0.808, 0.798]
F_L = [0.096, 0.103, 0.097, 0.078]
F_R = [0.0092, 0.0095, 0.0090, 0.0080]
F_D = [(1, -0.04, 0), (1, -0.01, 0), (1, 0.03, 0), (1, 0.08, 0)]
F_XPIP = [0.856, 0.860, 0.860, 0.860]       # x of the second finger bone (index_02 / fingers_02)
YF_KN = [-0.93, -0.71, -0.49, -0.245, 0.03, 0.29, 0.55, 0.77, 0.93]
TH_B = V3(0.757, -0.031, 1.4625)
TH_J = V3(0.790, -0.056, 1.4520)
TH_T = V3(0.828, -0.073, 1.4455)


def knuckle_x(y):
    return float(np.interp(y, F_Y, F_XK))


def build_hand(mb, wrist):
    """wrist: the 20 vertices of the last arm ring (k = 0 front, 5 top, 10 back, 15 bottom)."""
    H = {}       # vertex -> (part, fraction) for the skin weights
    rings = [list(wrist)]
    yc = 0.0
    for r in range(1, 6):
        u = r / 5.0
        w = 0.0270 + 0.0150 * float(sstep(0.0, 0.85, u))
        t = lerp(0.0185, 0.0125, u)
        n = lerp(2.0, 3.4, u)
        ring = [None] * 20
        for k in (0, 10):
            y = yc + (-w if k == 0 else w)
            x = PX[r] + (knuckle_x(y) - 0.810) * u * u
            ring[k] = mb.fix((x, y, HZ), 'hand')
        for j in range(9):
            yf = lerp(-math.cos(math.radians(18 * (j + 1))), YF_KN[j], u)
            zf = (1 - abs(yf) ** n) ** (1.0 / n)
            y = yc + w * yf
            x = PX[r] + (knuckle_x(y) - 0.810) * u * u
            # back of the hand (top): flatter; knuckles slightly raised on the last ring
            zt = t * zf * (1.0 - 0.10 * u)
            if r == 5 and j % 2 == 1:
                zt += 0.0014
            # palm (bottom): thenar pad on the thumb side, hypothenar on the other
            pad = 1.0 + 0.45 * math.exp(-((u - 0.40) / 0.30) ** 2) * math.exp(-((yf + 0.75) / 0.45) ** 2) \
                + 0.25 * math.exp(-((u - 0.45) / 0.35) ** 2) * math.exp(-((yf - 0.80) / 0.40) ** 2) \
                + 0.12 * math.exp(-((u - 0.95) / 0.15) ** 2)
            zb = t * zf * pad
            ring[1 + j] = mb.fix((x, y, HZ + zt), 'hand')
            ring[19 - j] = mb.fix((x, y, HZ - zb), 'hand')
            if r == 5 and j % 2 == 1:
                mb.col[ring[1 + j]] = (0.25, None, None)       # knuckles: blush
        for v in ring:
            H[v] = ('palm', u)
        rings.append(ring)
    for v in wrist:
        H[v] = ('palm', 0.0)
    # thenar: push the thumb side edge of the palm outwards (rings 1..3)
    for r, dy in ((1, 0.0030), (2, 0.0055), (3, 0.0035)):
        for k, f in ((19, 0.8), (0, 1.0), (1, 0.8)):
            v = rings[r][k]
            mb.P[v] = mb.P[v] + V3(0, -dy * f, -0.0015 if k == 19 else 0.0)
    # palm faces (skip the 4 quads of the thumb hole)
    for r in range(5):
        for k in range(20):
            k2 = (k + 1) % 20
            if r in (1, 2) and k in (19, 0):
                continue
            mb.quad(rings[r][k], rings[r][k2], rings[r + 1][k2], rings[r + 1][k], 'hands')
    kn = rings[5]
    tj = lambda j: kn[1 + j]
    bj = lambda j: kn[19 - j]
    # webs
    mL = {0: kn[0]}
    mR = {3: kn[10]}
    for i in range(3):
        yb = F_B[i + 1]
        xb = knuckle_x(yb) + 0.0075
        mR[i] = mb.fix((xb, yb - 0.0011, HZ), 'hand')
        mL[i + 1] = mb.fix((xb, yb + 0.0011, HZ), 'hand')
        mb.col[mR[i]] = (None, 0.50, None)
        mb.col[mL[i + 1]] = (None, 0.50, None)
        H[mR[i]] = ('f%d' % i, 0.05)
        H[mL[i + 1]] = ('f%d' % (i + 1), 0.05)
        mb.quad(tj(2 * i + 2), mL[i + 1], bj(2 * i + 2), mR[i], 'hands')
    ANG = [135, 90, 45, 0, -45, -90, -135, 180]
    tips = {}
    for i in range(4):
        base = [tj(2 * i), tj(2 * i + 1), tj(2 * i + 2), mR[i], bj(2 * i + 2), bj(2 * i + 1), bj(2 * i), mL[i]]
        K = V3(F_XK[i], F_Y[i], HZ)
        d = nrm(F_D[i])
        ey = nrm((-d[1], d[0], 0))
        prev = base
        fp = (F_XPIP[i] - F_XK[i]) / (F_L[i] * d[0])
        ff = [fp * 0.37, fp * 0.72, fp - 0.03, fp + 0.03] + [fp + 0.03 + (0.955 - fp - 0.03) * q for q in (1 / 3.0, 2 / 3.0, 1.0)]
        ff.insert(4, fp + 0.03 + (0.955 - fp - 0.03) * 0.12) if False else None
        ff = ff[:4] + [lerp(fp + 0.03, 0.955, 0.25), lerp(fp + 0.03, 0.955, 0.5), lerp(fp + 0.03, 0.955, 0.75), 0.955]
        for f in ff:
            r = F_R[i] * (1 - 0.20 * f) * (1 + 0.06 * math.exp(-((f - 0.47) / 0.05) ** 2)
                                           + 0.05 * math.exp(-((f - 0.74) / 0.04) ** 2))
            if f >= 0.92:
                r *= 0.70
            c = K + d * (f * F_L[i])
            ring = []
            for a in ANG:
                ar = math.radians(a)
                v = mb.fix(c + ey * (r * math.cos(ar)) + Z * (0.90 * r * math.sin(ar)), 'hand')
                H[v] = ('f%d' % i, f)
                ring.append(v)
            if abs(f - fp) < 0.035:
                mb.col[ring[1]] = (0.20, None, None)
            mb.strip(prev, ring, 'hands', closed=True)
            prev = ring
        tip = mb.fix(K + d * F_L[i] - Z * 0.0008, 'hand')
        H[tip] = ('f%d' % i, 1.0)
        tips[i] = tip
        mb.quad(tip, prev[1], prev[0], prev[7], 'hands')
        mb.quad(tip, prev[3], prev[2], prev[1], 'hands')
        mb.quad(tip, prev[5], prev[4], prev[3], 'hands')
        mb.quad(tip, prev[7], prev[6], prev[5], 'hands')
    # thumb
    hole = [rings[1][19], rings[1][0], rings[1][1], rings[2][1], rings[3][1], rings[3][0], rings[3][19], rings[2][19]]
    TANG = [225, 180, 135, 90, 45, 0, 315, 270]
    L1 = float(np.linalg.norm(TH_J - TH_B))
    L2 = float(np.linalg.norm(TH_T - TH_J))
    d1, d2 = nrm(TH_J - TH_B), nrm(TH_T - TH_J)
    prev = hole
    for v in hole:
        H[v] = ('palm', 0.4)
    spec = [(TH_B, d1, 0.35 * L1, 0.0125, 0.35 * 0.5), (TH_B, d1, 0.65 * L1, 0.0115, 0.65 * 0.5),
            (TH_B, d1, 0.92 * L1, 0.0109, 0.92 * 0.5), (TH_J, d2, 0.10 * L2, 0.0107, 0.5 + 0.10 * 0.5),
            (TH_J, d2, 0.38 * L2, 0.0101, 0.5 + 0.38 * 0.5), (TH_J, d2, 0.70 * L2, 0.0094, 0.5 + 0.70 * 0.5),
            (TH_J, d2, 0.93 * L2, 0.0068, 0.5 + 0.93 * 0.5)]
    for (o, d, s, r, f) in spec:
        eu = nrm(Z - d * float(Z @ d))
        ed = nrm(np.cross(eu, d))
        c = o + d * s
        ring = []
        for a in TANG:
            ar = math.radians(a)
            v = mb.fix(c + ed * (r * math.cos(ar)) + eu * (0.88 * r * math.sin(ar)), 'hand')
            H[v] = ('thumb', f)
            ring.append(v)
        mb.strip(prev, ring, 'hands', closed=True)
        prev = ring
    tip = mb.fix(TH_T + d2 * 0.002, 'hand')
    H[tip] = ('thumb', 1.0)
    # TANG order: index 3 = 90 (top), 5 = 0, 7 = 270, 1 = 180 are the edge mids; 2, 4, 6, 0 the corners
    mb.quad(tip, prev[3], prev[2], prev[1], 'hands')
    mb.quad(tip, prev[5], prev[4], prev[3], 'hands')
    mb.quad(tip, prev[7], prev[6], prev[5], 'hands')
    mb.quad(tip, prev[1], prev[0], prev[7], 'hands')
    mb.sets['hand_info'] = H
    mb.sets['palm_rings'] = rings
    return H


# ----------------------------------------------------------------------------- leg + foot
LZ = [0.800, 0.745, 0.690, 0.635, 0.585, 0.545, 0.515, 0.490, 0.465, 0.435, 0.400, 0.360, 0.315, 0.270, 0.225,
      0.180, 0.140, 0.105]
BETA = [150 - 15 * m for m in range(24)]


def leg_axis(z):
    if z >= 0.50:
        t = (0.915 - z) / (0.915 - 0.50)
        return V3(lerp(0.098, 0.100, t), lerp(0.004, -0.005, t), z)
    t = (0.50 - z) / (0.50 - 0.105)
    return V3(0.100, lerp(-0.005, 0.018, t), z)


def ring24(mb, c, e2, tag, tmax=0.15, rw=0.15):
    S = SID['body']
    out = []
    for b in BETA:
        br = math.radians(b)
        out.append(mb.ray(c, X * math.cos(br) + V3(e2) * math.sin(br), tag, S, tmax=tmax, rw=rw))
    return out


def cap_grid(mb, ring, corners, n, origin, tag, ftag, sid):
    """Close a ring of 4*n vertices with an n x n quad grid. corners: ring index of the first corner."""
    N = len(ring)
    G = -np.ones((n + 1, n + 1), int)
    for u in range(n + 1):
        G[u, 0] = ring[(corners + u) % N]
        G[n, u] = ring[(corners + n + u) % N]
        G[n - u, n] = ring[(corners + 2 * n + u) % N]
        G[0, n - u] = ring[(corners + 3 * n + u) % N]
    mb.flush()
    PG = lambda a, b: mb.pos(G[a, b])
    o = V3(origin)
    for a in range(1, n):
        for b in range(1, n):
            p = coons(PG, a, b, 0, n, 0, n)
            G[a, b] = mb.ray(o, p - o, tag, sid, tmax=0.2, rw=0.4)
    mb.grid(G, ftag)
    return G


def build_leg(mb, T):
    S = SID['body']
    oc = V3(0, 0.012, 0.945)
    strip = []
    for phi in (40, 0, -40):                 # back -> front, under the crotch
        a = math.radians(phi)
        strip.append(mb.ray(oc, (0, math.sin(a), -math.cos(a)), 'leg', S, tmax=0.25, rw=0.3))
    L0 = [T[i, 0] for i in range(21)] + strip
    rings = []
    for z in LZ:
        rings.append(ring24(mb, leg_axis(z), (0, -1, 0), 'leg', rw=0.0 if z == LZ[-1] else 0.15))
    mb.flush()
    L1 = [mb.cp(lerp(mb.pos(a), mb.pos(b), 0.5), 'leg', S, rw=0.4) for a, b in zip(L0, rings[0])]
    allr = [L0, L1] + rings
    # foot: fan around the heel, then the forefoot
    for phi in (15, 30, 45, 60, 75, 90):
        f = math.radians(phi)
        c = V3(0.100, 0.020 - 0.065 * (phi / 90.0) ** 1.3, 0.105 - 0.064 * math.sin(f))
        allr.append(ring24(mb, c, (0, -math.cos(f), math.sin(f)), 'foot', rw=0.3))
    for (y, zc) in ((-0.072, 0.035), (-0.100, 0.030), (-0.128, 0.025), (-0.156, 0.021), (-0.182, 0.018)):
        allr.append(ring24(mb, V3(0.100, y, zc), (0, 0, 1), 'foot', rw=0.2))
    n_leg = 2 + len(LZ)
    for n in range(len(allr) - 1):
        mb.strip(allr[n], allr[n + 1], 'legs' if n < n_leg - 1 else 'feet', closed=True)
    cap_grid(mb, allr[-1], 1, 6, (0.100, -0.150, 0.018), 'foot', 'feet', S)
    mb.sets['leg_rings'] = allr
    mb.flush()
    return allr


def build_body(mb):
    T, J = build_torso(mb)
    arm = build_arm(mb, J)
    build_hand(mb, arm[-1])
    build_leg(mb, T)
