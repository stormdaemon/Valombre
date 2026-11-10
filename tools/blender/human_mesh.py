"""Topology of the VALOMBRE base human: hand designed quad lofts projected on the implicit sculpt.

Only the character's LEFT half (x >= 0) is built, then mirrored (MB.mirrored). Pure numpy (no bpy).
"""
import math
import numpy as np
import human_sdf as hs
import human_morphs as hm

LM = hm.LM
SDFS = hs.build_human_sdf()
SID = {'head': 1, 'body': 2}
SDF_BY_ID = {1: SDFS['head'], 2: SDFS['body']}


def sstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def V3(*a):
    return np.array(a if len(a) == 3 else a[0], dtype=np.float64)


def nrm(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


# ============================================================================= mesh builder
class MB:
    """Half mesh builder (x >= 0, centre line on x = 0), mirrored at the end."""

    def __init__(self):
        self.P = []
        self.vt = []
        self.rw = []
        self.sid = []
        self.pend = []
        self.F = []
        self.ft = []
        self.sets = {}
        self.col = {}       # vertex -> (r, g, b) overrides (None = keep the analytic value)

    def _new(self, p, tag, rw, sid):
        self.P.append(None if p is None else np.array(p, dtype=np.float64))
        self.vt.append(tag)
        self.rw.append(rw)
        self.sid.append(sid)
        return len(self.P) - 1

    def fix(self, p, tag, rw=0.0, sid=0):
        return self._new(p, tag, rw, sid)

    def ray(self, o, d, tag, sid, tmax=0.2, rw=0.0):
        i = self._new(None, tag, rw, sid)
        self.pend.append((i, 0, np.array(o, float), np.array(d, float), tmax))
        return i

    def cp(self, p, tag, sid, rw=0.0):
        i = self._new(None, tag, rw, sid)
        self.pend.append((i, 1, np.array(p, float), None, 0.0))
        return i

    def flush(self):
        if not self.pend:
            return
        for sid in (1, 2):
            rays = [q for q in self.pend if q[1] == 0 and self.sid[q[0]] == sid]
            if rays:
                o = np.array([q[2] for q in rays])
                d = np.array([q[3] for q in rays])
                tm = np.array([q[4] for q in rays])
                pts, ok = SDF_BY_ID[sid].ray(o, d, tm)
                nbad = int((~ok).sum())
                if nbad:
                    print('WARN %d/%d rays failed (sid %d) e.g.' % (nbad, len(rays), sid),
                          [self.vt[rays[k][0]] for k in np.where(~ok)[0][:6]],
                          np.round(o[~ok][:3], 3).tolist(), np.round(d[~ok][:3], 2).tolist())
                for q, p in zip(rays, pts):
                    self.P[q[0]] = p
            cps = [q for q in self.pend if q[1] == 1 and self.sid[q[0]] == sid]
            if cps:
                pts = SDF_BY_ID[sid].project(np.array([q[2] for q in cps]), iters=8)
                for q, p in zip(cps, pts):
                    self.P[q[0]] = p
        self.pend = []

    def pos(self, i):
        if self.P[i] is None:
            self.flush()
        return self.P[i]

    def quad(self, a, b, c, d, tag):
        self.F.append((a, b, c, d))
        self.ft.append(tag)

    def tri(self, a, b, c, tag):
        self.F.append((a, b, c))
        self.ft.append(tag)

    def grid(self, I, tag, skip=None):
        I = np.asarray(I)
        for i in range(I.shape[0] - 1):
            for j in range(I.shape[1] - 1):
                if skip and skip(i, j):
                    continue
                q = (I[i, j], I[i + 1, j], I[i + 1, j + 1], I[i, j + 1])
                if min(q) < 0:
                    continue
                self.quad(*q, tag)

    def strip(self, A, B, tag, closed=False):
        """Quads between two index lists of equal length."""
        n = len(A)
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            self.quad(A[k], A[k2], B[k2], B[k], tag)

    # ------------------------------------------------------------------ relaxation
    def relax(self, iters=4, lam=0.5, only=None):
        self.flush()
        P = np.array(self.P)
        n = len(P)
        rw = np.array(self.rw)
        if only is not None:
            m = np.zeros(n)
            m[list(only)] = 1
            rw = rw * m
        sid = np.array(self.sid)
        e = set()
        for f in self.F:
            for k in range(len(f)):
                a, b = f[k], f[(k + 1) % len(f)]
                e.add((a, b))
                e.add((b, a))
        e = np.array(sorted(e))
        isc = np.abs(P[:, 0]) < 1e-7
        wgt = np.where(isc[e[:, 0]] & ~isc[e[:, 1]], 2.0, 1.0)
        mirr = isc[e[:, 0]] & ~isc[e[:, 1]]
        act = rw > 0
        for _ in range(iters):
            S = np.zeros((n, 3))
            W = np.zeros(n)
            contrib = P[e[:, 1]] * wgt[:, None]
            contrib[mirr, 0] = 0.0
            np.add.at(S, e[:, 0], contrib)
            np.add.at(W, e[:, 0], wgt)
            avg = S / np.maximum(W, 1e-9)[:, None]
            Pn = P + (rw * lam)[:, None] * (avg - P)
            for s in (1, 2):
                sel = act & (sid == s)
                if sel.any():
                    Pn[sel] = SDF_BY_ID[s].project(Pn[sel], iters=3)
            Pn[isc, 0] = 0.0
            P = Pn
        self.P = [p for p in P]

    # ------------------------------------------------------------------ remove unused vertices
    def compact(self):
        self.flush()
        n = len(self.P)
        used = np.zeros(n, bool)
        for f in self.F:
            used[list(f)] = True
        if used.all():
            return
        mp = -np.ones(n, int)
        mp[used] = np.arange(int(used.sum()))

        def rm(o):
            if isinstance(o, (int, np.integer)):
                return int(mp[o]) if o >= 0 else int(o)
            if isinstance(o, np.ndarray):
                return np.where(o >= 0, mp[np.maximum(o, 0)], o)
            if isinstance(o, (list, tuple)):
                return type(o)(rm(x) for x in o)
            if isinstance(o, dict):
                return {rm(k): v for k, v in o.items() if mp[k] >= 0}
            return o

        keep = np.where(used)[0]
        self.P = [self.P[i] for i in keep]
        self.vt = [self.vt[i] for i in keep]
        self.rw = [self.rw[i] for i in keep]
        self.sid = [self.sid[i] for i in keep]
        self.F = [tuple(int(mp[v]) for v in f) for f in self.F]
        self.col = {int(mp[k]): v for k, v in self.col.items() if mp[k] >= 0}
        self.sets = {k: rm(v) for k, v in self.sets.items()}
        print('compact: removed %d unused vertices' % int((~used).sum()))

    # ------------------------------------------------------------------ mirror
    def mirrored(self):
        self.flush()
        self.compact()
        P = np.array(self.P)
        n = len(P)
        isc = np.abs(P[:, 0]) < 1e-7
        P[isc, 0] = 0.0
        if (P[:, 0] < -1e-7).any():
            print('WARN: %d verts with x<0 in the half mesh' % int((P[:, 0] < -1e-7).sum()))
        mi = np.arange(n)
        k = n
        for i in range(n):
            if not isc[i]:
                mi[i] = k
                k += 1
        P2 = np.zeros((k, 3))
        P2[:n] = P
        P2[mi] = P * np.array([-1.0, 1.0, 1.0])
        P2[:n] = P
        side = np.zeros(k, int)
        side[:n] = np.where(isc, 0, 1)
        side[mi[~isc]] = -1
        vt = list(self.vt) + [None] * (k - n)
        for i in range(n):
            vt[mi[i]] = self.vt[i]
        F = list(self.F)
        ft = list(self.ft)
        fside = [1] * len(F)
        for f, t in zip(self.F, self.ft):
            g = tuple(int(mi[v]) for v in reversed(f))
            if set(g) == set(f):
                continue
            F.append(g)
            ft.append(t)
            fside.append(-1)
        col = {}
        for i, c in self.col.items():
            col[i] = c
            col[int(mi[i])] = c
        return dict(P=P2, F=F, ft=ft, fside=fside, vt=vt, side=side, mirror=mi, nhalf=n, col=col)


# ============================================================================= HEAD
HAX = 0.005                 # y of the vertical ray axis of the head
OD = V3(0, 0.010, 1.715)    # dome centre
AZ = [0, 2.6, 5.2, 7.6, 9.8, 12.0, 15.5, 19.0, 22.5, 25.8, 29.0, 32.0, 37, 43.5, 52, 62, 74, 87, 97, 108,
      122, 136, 150, 165, 180]
NI = len(AZ)
# rows: (origin y, origin z, elevation deg) at the front; the height at the back is HROW_ZB
HROWS = [
    (0.008, 1.5400, 0),      # 0 neck
    (0.008, 1.5570, 0),      # 1 jaw / neck junction
    (-0.022, 1.6220, -74),   # 2 under the chin
    (-0.022, 1.6220, -58),   # 3
    (-0.030, 1.6150, -40),   # 4 menton
    (HAX, 1.5795, 0),        # 5
    (HAX, 1.5860, 0),        # 6 pogonion
    (HAX, 1.5935, 0),        # 7
    (HAX, 1.6010, 0),        # 8 labiomental groove
    (HAX, 1.6065, 0),        # 9
    (HAX, 1.6095, 0),        # 10 lower lip border
    (HAX, 1.6148, 0),        # 11 lower lip
    (HAX, 1.6195, 0),        # 12 lip line (slit)
    (HAX, 1.6236, 0),        # 13 upper lip
    (HAX, 1.6276, 0),        # 14 upper lip border
    (HAX, 1.6300, 0),        # 15
    (HAX, 1.6350, 0),        # 16 philtrum
    (HAX, 1.6410, 0),        # 17 subnasale
    (-0.060, 1.6720, -30),   # 18 underside of the nose
    (HAX, 1.6475, 0),        # 19
    (HAX, 1.6540, 0),        # 20
    (HAX, 1.6610, 0),        # 21
    (HAX, 1.6690, 0),        # 22
    (HAX, 1.6765, 0),        # 23
    (HAX, 1.6812, 0),        # 24 lower lid
    (HAX, 1.6870, 0),        # 25 canthi
    (HAX, 1.6913, 0),        # 26 upper lid
    (HAX, 1.6955, 0),        # 27 crease
    (HAX, 1.7005, 0),        # 28 fold
    (HAX, 1.7065, 0),        # 29 brow
    ('dome', 0.0), ('dome', 7.0), ('dome', 14.5), ('dome', 22.5), ('dome', 31.0), ('dome', 40.0), ('dome', 51.0),
]
NR = len(HROWS)
J_SUB = 17                                    # from this row up, rows are horizontal all around the head
HROW_ZB = [1.560 + (HROWS[J_SUB][1] - 1.560) * j / J_SUB for j in range(J_SUB + 1)] + \
          [1.6445] + [r[1] for r in HROWS[J_SUB + 2:30]]
J_SLIT, J_NOSTRIL, J_DOME = 12, 18, 30
EYE_I0, EYE_I1, EYE_J0, EYE_J1 = 5, 11, 24, 26
EAR_I0, EAR_I1, EAR_J0, EAR_J1 = 17, 19, 20, 28
MOUTH_I = 6

E_C = V3(LM['eye_L'])
E_R = LM['eye_radius']
EYE_XI, EYE_XO, EYE_ZI, EYE_ZO = hm.LID_XI, hm.LID_XO, hm.LID_ZI, hm.LID_ZO
S_LID = [0.085, 0.24, 0.40, 0.56, 0.71, 0.85, 0.94]


def lid_pt(s, up, off=0.0010):
    x = EYE_XI + s * (EYE_XO - EYE_XI)
    z = float(hm.lid_zu(s) if up else hm.lid_zl(s))
    q = (E_R + off) ** 2 - (x - E_C[0]) ** 2 - (z - E_C[2]) ** 2
    dmin = lerp(0.0065, 0.0035, s)
    d = (max(q, 0.0) ** 2 + dmin ** 4) ** 0.25
    return V3(x, E_C[1] - d, z)


MOUTH_HW = hm.MOUTH_HW
MOUTH_X = [MOUTH_HW * t for t in (0, 0.175, 0.35, 0.522, 0.69, 0.853, 1.0)]


def slit_pt(x):
    t = x / MOUTH_HW
    y = LM['mouth'][1] + (LM['mouth_corner'][1] - LM['mouth'][1]) * t ** 2.2
    return V3(x, y, float(hm.slit_z(x)))


# ear frame (left ear)
EAR_C = V3(0.0748, 0.0130, 1.6775)
EAR_U = nrm((0.10, 1.0, 0.0))
EAR_V = nrm((0.0, 0.16, 1.0))
EAR_N = nrm(np.cross(EAR_U, EAR_V))
EAR_ANG = [252 - 18 * q for q in range(9)] + [90] + [72 - 18 * q for q in range(9)] + [270]
EAR_C0 = (0.003, 0.002)


def ear_outline_r(a):
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    ru = 0.0175 if ca >= 0 else 0.0110
    rv = 0.0295 if sa >= 0 else 0.0300
    e = 2.5 if sa >= 0 else 2.1
    return (abs(ca / ru) ** e + abs(sa / rv) ** e) ** (-1.0 / e)


def ear_pt(a, rho_rim, rho_front, h):
    """Point of the auricle at outline angle a (deg)."""
    da = abs((a - 180 + 180) % 360 - 180)
    wr = float(sstep(35, 75, da))                     # 1 = free rim, 0 = front attachment
    dl = abs((a - 270 + 180) % 360 - 180)
    wl = 1.0 - 0.6 * math.exp(-(dl / 40.0) ** 2)       # lobe: flatter
    rho = lerp(rho_front, rho_rim, wr)
    R = ear_outline_r(a)
    u = EAR_C0[0] + rho * R * math.cos(math.radians(a))
    v = EAR_C0[1] + rho * R * math.sin(math.radians(a))
    lobe = 0.70 + 0.30 * float(sstep(-0.022, 0.006, v))
    n = max(0.0, u + 0.009) * 0.40 * lobe
    hh = h[0] * wr * (wl if h[2] else 1.0) + h[1] * (1 - wr)
    return EAR_C + EAR_U * u + EAR_V * v + EAR_N * (n + hh)


def ear_root_pt(a):
    u = -0.002 + 0.0065 * math.cos(math.radians(a))
    v = 0.001 + 0.0215 * math.sin(math.radians(a))
    return EAR_C + EAR_U * u + EAR_V * v


def head_ray(i, j):
    r = HROWS[j]
    tt = float(sstep(J_DOME - 1, NR - 1, j))
    tb = 1.0 - float(sstep(0, 5, j))
    az = lerp(AZ[i], 7.5 * i, max(tt, tb))
    a = math.radians(az)
    if r[0] == 'dome':
        o = OD
        el = math.radians(r[1])
    elif j == J_NOSTRIL:
        wn = float(sstep(7, 13, az))
        o = V3(0, lerp(r[0], HAX, wn), lerp(r[1], HROW_ZB[j], wn))
        el = math.radians(lerp(r[2], 0.0, wn))
    else:
        wb = float(sstep(18, 85, az))
        o = V3(0, lerp(r[0], 0.008, wb), lerp(r[1], HROW_ZB[j], wb))
        el = math.radians(lerp(r[2], 0.0, wb))
    d = V3(math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))
    return o, d


# designed targets around the base of the nose (closest-point projected on the sculpt)
NOSE_PTS = {
    (0, 17): (0.0000, -0.1000, 1.6410), (1, 17): (0.0045, -0.0990, 1.6412), (2, 17): (0.0088, -0.0975, 1.6416),
    (3, 17): (0.0130, -0.0955, 1.6420), (4, 17): (0.0172, -0.0925, 1.6428),
    (0, 18): (0.0000, -0.1070, 1.6455), (1, 18): (0.0036, -0.1060, 1.6460),
    (3, 18): (0.0125, -0.1030, 1.6425), (4, 18): (0.0178, -0.0945, 1.6450),
    (0, 19): (0.0000, -0.1170, 1.6492), (1, 19): (0.0050, -0.1150, 1.6490), (2, 19): (0.0092, -0.1100, 1.6486),
    (3, 19): (0.0140, -0.1060, 1.6480), (4, 19): (0.0180, -0.0985, 1.6488),
}


def head_rw(i, j):
    if 22 <= j <= 29 and 2 <= i <= 14:
        return 0.6
    if EAR_J0 - 2 <= j <= EAR_J1 + 2 and EAR_I0 - 2 <= i <= EAR_I1 + 2:
        return 0.6
    if 17 <= j <= 20 and i <= 6:
        return 0.3 if (j == 20 or i >= 5) else 0.0
    if j <= 4:
        return 0.5
    if 9 <= j <= 15 and 6 <= i <= 9:
        return 0.5
    if 9 <= j <= 15 and i < 6:
        return 0.0
    return 0.2


def build_head(mb):
    S = SID['head']
    G = -np.ones((NI, NR), int)
    low = {}
    ear_root = {}
    for j in range(NR):
        for i in range(NI):
            # ---- eye opening
            if EYE_I0 <= i <= EYE_I1 and EYE_J0 <= j <= EYE_J1:
                if j == EYE_J0 + 1:
                    if i == EYE_I0:
                        G[i, j] = mb.fix(lid_pt(0.0, True), 'lid')
                    elif i == EYE_I1:
                        G[i, j] = mb.fix(lid_pt(1.0, True), 'lid')
                    continue
                G[i, j] = mb.fix(lid_pt(S_LID[i - EYE_I0], j == EYE_J1), 'lid')
                continue
            # ---- lip line
            if j == J_SLIT and i <= MOUTH_I:
                p = slit_pt(MOUTH_X[i])
                if i == MOUTH_I:
                    G[i, j] = mb.fix(p, 'lipline')
                else:
                    G[i, j] = mb.fix(p + V3(0, 0, 0.00015), 'lipline')
                    low[i] = mb.fix(p - V3(0, 0, 0.00015), 'lipline')
                continue
            if j == J_NOSTRIL and i == 2:
                G[i, j] = mb.fix((0.0068, -0.1035, 1.6468), 'nostril')
                mb.col[G[i, j]] = (None, 0.30, None)
                continue
            if (i, j) in NOSE_PTS:
                G[i, j] = mb.cp(NOSE_PTS[(i, j)], 'head', S, rw=0.0)
                continue
            # ---- ear root
            if EAR_I0 <= i <= EAR_I1 and EAR_J0 <= j <= EAR_J1:
                if i == EAR_I0 + 1 and EAR_J0 < j < EAR_J1:
                    continue
                if i == EAR_I0:
                    q = j - EAR_J0
                elif i == EAR_I1:
                    q = 10 + (EAR_J1 - j)
                else:
                    q = 9 if j == EAR_J1 else 19
                G[i, j] = mb.cp(ear_root_pt(EAR_ANG[q]), 'ear_root', S)
                ear_root[q] = G[i, j]
                continue
            o, d = head_ray(i, j)
            G[i, j] = mb.ray(o, d, 'head', S, tmax=0.17, rw=head_rw(i, j))
    mb.flush()

    def is_hole(i, j):
        if EYE_I0 <= i < EYE_I1 and EYE_J0 <= j < EYE_J1:
            return True
        if EAR_I0 <= i < EAR_I1 and EAR_J0 <= j < EAR_J1:
            return True
        return False

    for i in range(NI - 1):
        for j in range(NR - 1):
            if is_hole(i, j):
                continue
            a, b, c, d = G[i, j], G[i + 1, j], G[i + 1, j + 1], G[i, j + 1]
            if j + 1 == J_SLIT:      # quad below the lip line uses the lower copies
                c = low.get(i + 1, c)
                d = low.get(i, d)
            mb.quad(a, b, c, d, 'head')

    # ---- eyelid thickness ring (16 verts)
    loop = [G[i, EYE_J1] for i in range(EYE_I0, EYE_I1 + 1)] + [G[EYE_I1, EYE_J0 + 1]] + \
           [G[i, EYE_J0] for i in range(EYE_I1, EYE_I0 - 1, -1)] + [G[EYE_I0, EYE_J0 + 1]]
    inner = []
    for v in loop:
        p = mb.pos(v)
        dr = nrm(p - E_C)
        inner.append(mb.fix(E_C + dr * (E_R - 0.0007), 'lid_in'))
    mb.strip(loop, inner, 'head', closed=True)
    for k, v in enumerate(loop):
        mb.col[v] = (None, 0.26 if k <= 7 else 0.62, None)      # lash line (upper) / lower margin
    for k, v in enumerate(inner):
        car = math.exp(-((mb.pos(v)[0] - EYE_XI) / 0.0035) ** 2)
        mb.col[v] = (0.45 * car, 0.42, 0.0)
    mb.sets['lid_loop'] = loop
    mb.sets['lid_in'] = inner

    # ---- inner lips
    up = [G[i, J_SLIT] for i in range(MOUTH_I + 1)]
    lo = [low[i] for i in range(MOUTH_I)] + [G[MOUTH_I, J_SLIT]]
    upA, upB, loA, loB = [], [], [], []
    for i in range(MOUTH_I):
        p = slit_pt(MOUTH_X[i])
        upA.append(mb.fix(p + V3(0, 0.0040, 0.0001), 'lip_in'))
        loA.append(mb.fix(p + V3(0, 0.0040, -0.0001), 'lip_in'))
        upB.append(mb.fix(p * V3(0.96, 1, 1) + V3(0, 0.0085, 0.0045), 'lip_in'))
        loB.append(mb.fix(p * V3(0.96, 1, 1) + V3(0, 0.0085, -0.0045), 'lip_in'))
    pc = slit_pt(MOUTH_X[MOUTH_I])
    cA = mb.fix(pc + V3(-0.0015, 0.0040, 0), 'lip_in')
    cB = mb.fix(pc + V3(-0.0035, 0.0080, 0), 'lip_in')
    upA.append(cA), loA.append(cA), upB.append(cB), loB.append(cB)
    mb.strip(up, upA, 'head')
    mb.strip(upA, upB, 'head')
    mb.strip(loA, lo, 'head')
    mb.strip(loB, loA, 'head')
    for v in up + lo:
        mb.col[v] = (None, 0.62, 1.0)
    for v in upA + loA:
        mb.col[v] = (0.0, 0.30, 1.0)
    for v in upB + loB:
        mb.col[v] = (0.0, 0.10, 1.0)
    mb.sets['lip_up'] = up
    mb.sets['lip_lo'] = lo
    mb.sets['lip_in_end'] = upB + loB

    # ---- ear
    rings = [[ear_root[q] for q in range(20)]]
    spec = [  # rho on the free rim, rho on the front attachment, (h rim, h front, lobe flattening)
        (0.80, 0.93, (-0.0035, 0.0006, False)),
        (1.00, 0.86, (-0.0008, 0.0016, False)),
        (0.93, 0.76, (0.0026, 0.0030, True)),
        (0.76, 0.64, (-0.0002, 0.0012, False)),
        (0.56, 0.52, (0.0022, -0.0010, True)),
        (0.34, 0.36, (-0.0050, -0.0045, False)),
    ]
    for (rr, rf, h) in spec:
        rings.append([mb.fix(ear_pt(EAR_ANG[q], rr, rf, h), 'ear') for q in range(20)])
    for k in range(len(rings) - 1):
        mb.strip(rings[k], rings[k + 1], 'head', closed=True)
    cc = mb.fix(EAR_C + EAR_U * EAR_C0[0] + EAR_V * EAR_C0[1] + EAR_N * (0.012 * 0.40 - 0.0062), 'ear')
    for q in range(20):
        mb.tri(rings[-1][q], rings[-1][(q + 1) % 20], cc, 'head')
    for k, rg in enumerate(rings):
        g = (0.80, 0.85, 1.0, 1.0, 0.80, 0.95, 0.50)[k]
        for v in rg:
            mb.col[v] = (0.10 if k == 0 else 0.25, g, None)
    mb.col[cc] = (0.25, 0.35, None)
    mb.sets['ear_rings'] = rings

    # ---- cap (grid on the dome)
    top = [G[i, NR - 1] for i in range(NI)]
    C = -np.ones((7, 13), int)
    for a in range(7):
        C[a, 0] = top[a]
        C[a, 12] = top[24 - a]
    for b in range(13):
        C[6, b] = top[6 + b]
    el0 = math.radians(HROWS[-1][1])
    for a in range(6):
        for b in range(1, 12):
            u, v = a / 6.0, (b - 6) / 6.0
            dx, dy = u * math.sqrt(1 - v * v / 2), v * math.sqrt(1 - u * u / 2)
            rho = math.hypot(dx, dy)
            pol = rho * (math.pi / 2 - el0)
            az = math.atan2(dx, -dy)
            d = V3(math.sin(az) * math.sin(pol), -math.cos(az) * math.sin(pol), math.cos(pol))
            C[a, b] = mb.ray(OD, d, 'head', S, tmax=0.17, rw=0.5)
    mb.grid(C, 'head')

    # ---- neck: reduction strip then rings down to the collar
    NECK_N = 4
    rings = []
    for n in range(1, NECK_N + 1):
        t = n / NECK_N
        ring = []
        for m in range(13):
            az = math.radians(15.0 * m)
            o0, d0 = head_ray(2 * m, 0)
            tgt = V3(0.066 * math.sin(az), 0.012 - 0.058 * math.cos(az),
                     1.49525 - 0.0125 * math.cos(az) - 0.01475 * math.cos(2 * az))
            oc = V3(0, 0.012, 1.47)
            dc = nrm(tgt - oc)
            o = lerp(o0, oc, t)
            d = nrm(lerp(d0, dc, t))
            ring.append(mb.ray(o, d, 'collar' if n == NECK_N else 'neck', S, tmax=0.2, rw=0.0 if n == NECK_N else 0.3))
        rings.append(ring)
    r0 = [G[i, 0] for i in range(NI)]
    for m in range(12):
        mb.quad(rings[0][m], rings[0][m + 1], r0[2 * m + 2], r0[2 * m + 1], 'head')
        mb.tri(rings[0][m], r0[2 * m + 1], r0[2 * m], 'head')
    for n in range(NECK_N - 1):
        mb.strip(rings[n], rings[n + 1], 'head')
    # strip() orientation: fix later with recalc normals
    mb.sets['collar'] = rings[-1]
    mb.sets['head_grid'] = G
    mb.flush()
    return G


