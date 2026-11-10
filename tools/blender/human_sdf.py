"""Implicit (signed distance) sculpt of the VALOMBRE base human (male base, T-pose, 1.80 m).

The body SHAPE lives here as a smooth union of anatomical primitives (ellipsoids, round cones). The
TOPOLOGY is designed by hand in human_build.py and projected onto this surface. Pure numpy.

Everything is evaluated on (|x|, y, z): the character is perfectly symmetric, primitives are listed for
the character's LEFT side (+X) or on the centre line.
"""
import numpy as np
import math


# ----------------------------------------------------------------------------- primitives
def smin(a, b, k):
    if k <= 0.0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def rot_xyz(rx=0.0, ry=0.0, rz=0.0):
    """Rotation matrix (degrees), columns = local axes expressed in world."""
    rx, ry, rz = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


class Ell:
    def __init__(self, c, r, rot=None):
        self.c = np.asarray(c, float)
        self.r = np.asarray(r, float)
        self.rot = rot
        self.rad = float(self.r.max())

    def __call__(self, p):
        q = p - self.c
        if self.rot is not None:
            q = q @ self.rot
        a = q / self.r
        b = q / (self.r * self.r)
        k0 = np.sqrt((a * a).sum(1))
        k1 = np.sqrt((b * b).sum(1))
        return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -float(self.r.min()))

    def center(self):
        return self.c


class Cone:
    """Segment a->b with radius ra->rb (linear)."""

    def __init__(self, a, b, ra, rb=None):
        self.a = np.asarray(a, float)
        self.b = np.asarray(b, float)
        self.ra = float(ra)
        self.rb = float(ra if rb is None else rb)
        self.ba = self.b - self.a
        self.bb = float(self.ba @ self.ba)
        self.rad = max(self.ra, self.rb) + math.sqrt(self.bb) * 0.5

    def __call__(self, p):
        pa = p - self.a
        h = np.clip((pa @ self.ba) / self.bb, 0.0, 1.0)
        d = pa - h[:, None] * self.ba
        return np.sqrt((d * d).sum(1)) - (self.ra + (self.rb - self.ra) * h)

    def center(self):
        return (self.a + self.b) * 0.5


class Sph(Ell):
    def __init__(self, c, r):
        Ell.__init__(self, c, (r, r, r))


class Sdf:
    """Ordered list of smooth unions / subtractions."""

    def __init__(self):
        self.ops = []

    def add(self, prim, k=0.01):
        self.ops.append((0, prim, k))
        return self

    def sub(self, prim, k=0.004):
        self.ops.append((1, prim, k))
        return self

    def cut_below(self, z0, k=0.006):
        self.ops.append((2, z0, k))
        return self

    def __call__(self, p):
        p = np.array(p, dtype=np.float64).reshape(-1, 3)
        p[:, 0] = np.abs(p[:, 0])
        d = None
        for kind, prim, k in self.ops:
            if kind == 2:
                d = smax(d, prim - p[:, 2], k)
                continue
            v = prim(p)
            if d is None:
                d = v
            elif kind == 0:
                d = smin(d, v, k)
            else:
                d = smax(d, -v, k)
        return d

    def grad(self, p, e=4e-4):
        p = np.asarray(p, dtype=np.float64).reshape(-1, 3)
        g = np.empty_like(p)
        for a in range(3):
            dp = np.zeros(3)
            dp[a] = e
            g[:, a] = (self(p + dp) - self(p - dp)) / (2 * e)
        return g

    def project(self, p, iters=6):
        """Closest-point style projection (gradient steps)."""
        p = np.array(p, dtype=np.float64).reshape(-1, 3)
        for _ in range(iters):
            d = self(p)
            g = self.grad(p)
            n2 = np.maximum((g * g).sum(1), 1e-12)
            p = p - (d / n2)[:, None] * g
        return p

    def ray(self, o, d, tmax, step=0.0015, t0=0.0):
        """First exit point along rays that start INSIDE. o, d: Nx3; tmax scalar or N. Returns (points, ok)."""
        o = np.asarray(o, float).reshape(-1, 3)
        d = np.asarray(d, float).reshape(-1, 3)
        d = d / np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
        n = len(o)
        tmax = np.broadcast_to(np.asarray(tmax, float), (n,)).copy()
        ns = int(math.ceil(float(tmax.max()) / step)) + 1
        t_in = np.full(n, t0)
        t_out = np.full(n, -1.0)
        done = np.zeros(n, bool)
        start = self(o + d * t0)
        bad = start > 0
        # coarse march
        for s in range(1, ns + 1):
            act = ~done
            if not act.any():
                break
            t = np.minimum(t0 + s * step, tmax[act])
            v = self(o[act] + d[act] * t[:, None])
            idx = np.where(act)[0]
            out = v > 0
            t_out[idx[out]] = t[out]
            done[idx[out]] = True
            t_in[idx[~out]] = t[~out]
            fin = (~out) & (t >= tmax[act] - 1e-12)
            done[idx[fin]] = True
        ok = (t_out > 0) & ~bad
        lo = t_in.copy()
        hi = np.where(t_out > 0, t_out, t_in)
        for _ in range(14):
            mid = (lo + hi) * 0.5
            v = self(o + d * mid[:, None])
            ins = v <= 0
            lo = np.where(ins, mid, lo)
            hi = np.where(ins, hi, mid)
        t = (lo + hi) * 0.5
        return o + d * t[:, None], ok


# ----------------------------------------------------------------------------- the human
def build_human_sdf():
    """Returns dict of Sdf objects: 'head' (head + neck + shoulders context), 'body' (everything below the
    jaw). They overlap around the neck so that both give the same surface there."""
    # ---------------------------------------------------------------- BODY
    B = Sdf()
    # torso
    B.add(Ell((0, 0.014, 1.295), (0.166, 0.115, 0.205)))                       # rib cage
    B.add(Ell((0, 0.000, 1.105), (0.150, 0.100, 0.170)), 0.035)                # abdomen
    B.add(Ell((0, 0.014, 0.965), (0.155, 0.104, 0.120)), 0.035)                # pelvis
    B.add(Ell((0.088, 0.058, 0.935), (0.080, 0.072, 0.095)), 0.030)            # glute
    B.add(Ell((0.128, 0.010, 0.930), (0.030, 0.055, 0.075)), 0.030)            # hip side (trochanter)
    B.add(Ell((0.085, -0.072, 1.362), (0.090, 0.036, 0.062), rot_xyz(6, 0, 8)), 0.022)    # pectoral
    B.add(Cone((0.02, -0.048, 1.452), (0.165, -0.012, 1.482), 0.026, 0.028), 0.022)       # clavicle / upper chest
    B.add(Ell((0.160, -0.035, 1.445), (0.040, 0.035, 0.048)), 0.022)           # front of the shoulder
    B.add(Ell((0.080, 0.068, 1.385), (0.090, 0.045, 0.115)), 0.030)            # scapula / upper back
    B.add(Ell((0.165, 0.042, 1.435), (0.045, 0.040, 0.055)), 0.025)            # back of the shoulder
    B.add(Ell((0.128, 0.040, 1.300), (0.043, 0.064, 0.125)), 0.030)            # latissimus
    B.add(Ell((0.0, 0.080, 1.20), (0.060, 0.030, 0.20)), 0.03)                 # spine erectors
    # neck + trapezius
    B.add(Cone((0, 0.016, 1.440), (0, 0.008, 1.630), 0.060, 0.054), 0.022)     # neck
    B.add(Cone((0.035, 0.022, 1.526), (0.160, 0.010, 1.490), 0.027, 0.025), 0.030)        # trapezius top
    B.add(Cone((0.0, 0.045, 1.555), (0.09, 0.055, 1.45), 0.026, 0.040), 0.030)            # trapezius back
    B.add(Cone((0.012, -0.042, 1.47), (0.048, -0.002, 1.60), 0.010, 0.010), 0.020)        # sternomastoid
    # shoulder + arm (T-pose, along +X)
    B.add(Ell((0.207, 0.002, 1.470), (0.070, 0.068, 0.064)), 0.028)            # deltoid
    B.add(Cone((0.185, 0.0, 1.470), (0.470, 0.0, 1.468), 0.049, 0.040), 0.020)  # upper arm
    B.add(Ell((0.320, -0.019, 1.471), (0.090, 0.036, 0.039)), 0.016)           # biceps
    B.add(Ell((0.335, 0.023, 1.466), (0.105, 0.035, 0.040)), 0.016)            # triceps
    B.add(Ell((0.470, 0.008, 1.468), (0.038, 0.038, 0.036)), 0.016)            # elbow
    B.add(Cone((0.470, 0.0, 1.468), (0.700, 0.0, 1.470), 0.042, 0.022), 0.016)  # forearm
    B.add(Ell((0.550, -0.002, 1.472), (0.085, 0.048, 0.043)), 0.020)           # forearm muscle mass
    B.add(Ell((0.712, 0.0, 1.470), (0.045, 0.0285, 0.0195)), 0.012)            # wrist (flat: wide in Y)
    B.add(Ell((0.770, 0.0, 1.470), (0.050, 0.036, 0.0150)), 0.010)             # palm stub (hand is explicit)
    # leg
    B.add(Cone((0.099, 0.004, 0.915), (0.100, -0.005, 0.500), 0.090, 0.055), 0.028)       # thigh
    B.add(Ell((0.106, -0.034, 0.720), (0.060, 0.052, 0.200)), 0.022)           # quadriceps
    B.add(Ell((0.097, 0.038, 0.700), (0.053, 0.045, 0.190)), 0.022)            # hamstrings
    B.add(Ell((0.100, -0.020, 0.498), (0.047, 0.045, 0.050)), 0.020)           # knee
    B.add(Cone((0.100, -0.005, 0.500), (0.100, 0.015, 0.105), 0.049, 0.034), 0.020)       # shin
    B.add(Ell((0.102, 0.036, 0.370), (0.050, 0.050, 0.115)), 0.020)            # calf
    B.add(Ell((0.112, 0.005, 0.380), (0.036, 0.034, 0.100)), 0.02)             # outer calf
    # foot
    B.add(Cone((0.100, 0.018, 0.120), (0.100, 0.020, 0.060), 0.034, 0.035), 0.014)        # ankle
    B.add(Sph((0.137, 0.022, 0.082), 0.015), 0.010)                            # outer malleolus
    B.add(Sph((0.064, 0.014, 0.093), 0.015), 0.010)                            # inner malleolus
    B.add(Ell((0.100, 0.030, 0.038), (0.033, 0.034, 0.040)), 0.016)            # heel
    B.add(Cone((0.100, 0.005, 0.052), (0.102, -0.120, 0.030), 0.040, 0.030), 0.016)       # mid foot
    B.add(Ell((0.102, -0.128, 0.022), (0.050, 0.050, 0.026)), 0.016)           # ball
    B.add(Ell((0.098, -0.176, 0.017), (0.047, 0.032, 0.018)), 0.014)           # toes
    B.sub(Ell((0.058, -0.040, -0.004), (0.020, 0.050, 0.022)), 0.012)          # arch
    B.cut_below(0.0, 0.007)

    # ---------------------------------------------------------------- HEAD
    H = Sdf()
    H.add(Ell((0, 0.0125, 1.7065), (0.0765, 0.0940, 0.0935)))                  # cranium
    H.add(Ell((0, -0.0300, 1.7270), (0.0630, 0.0605, 0.0580)), 0.028)          # forehead
    H.add(Ell((0, -0.0290, 1.6540), (0.0590, 0.0600, 0.0680)), 0.020)          # mid face
    H.add(Ell((0, -0.0290, 1.6130), (0.0460, 0.0540, 0.0410)), 0.015)          # lower face core
    H.add(Cone((0.013, -0.074, 1.588), (0.0435, -0.006, 1.611), 0.0160, 0.0110), 0.012)   # mandible body
    H.add(Cone((0.0445, -0.004, 1.613), (0.0570, 0.000, 1.660), 0.0110, 0.0090), 0.012)   # ramus
    H.add(Ell((0, -0.0745, 1.5905), (0.0185, 0.0180, 0.0185)), 0.010)          # chin
    H.add(Ell((0, -0.0380, 1.6020), (0.0340, 0.0400, 0.0225)), 0.014)          # floor of the mouth
    H.add(Ell((0.046, -0.060, 1.665), (0.019, 0.017, 0.014)), 0.016)           # cheek bone
    H.add(Cone((0.054, -0.045, 1.670), (0.0630, -0.004, 1.674), 0.008, 0.006), 0.014)     # zygomatic arch
    H.add(Ell((0.045, -0.032, 1.640), (0.018, 0.034, 0.030)), 0.016)           # cheek
    H.add(Ell((0.036, -0.060, 1.641), (0.020, 0.022, 0.021)), 0.016)           # front of the cheek
    H.add(Ell((0.048, -0.018, 1.628), (0.010, 0.020, 0.026)), 0.012)           # masseter
    H.add(Ell((0, -0.0640, 1.6265), (0.0290, 0.0315, 0.0240)), 0.012)          # muzzle (dental arch)
    # brow
    H.add(Ell((0, -0.0850, 1.7035), (0.012, 0.0085, 0.0075)), 0.010)           # glabella
    H.add(Cone((0.010, -0.0838, 1.7035), (0.034, -0.0790, 1.7070), 0.0078, 0.0073), 0.010)
    H.add(Cone((0.034, -0.0790, 1.7070), (0.053, -0.0650, 1.7045), 0.0073, 0.0068), 0.010)
    # eye socket, lid ball, upper lid fold
    H.sub(Ell((0.0335, -0.0850, 1.6875), (0.0190, 0.0150, 0.0125)), 0.007)
    H.add(Sph((0.0320, -0.0700, 1.6870), 0.0130 + 0.0012), 0.0035)
    H.add(Ell((0.0345, -0.0768, 1.7005), (0.0170, 0.0075, 0.0055), rot_xyz(0, 0, -12)), 0.0030)
    # nose
    H.add(Ell((0, -0.0905, 1.6570), (0.0115, 0.0110, 0.0160)), 0.012)          # pyramid base
    H.add(Cone((0, -0.0790, 1.6925), (0, -0.1020, 1.669), 0.0048, 0.0060), 0.005)
    H.add(Cone((0, -0.1020, 1.669), (0, -0.1085, 1.6580), 0.0060, 0.0072), 0.005)
    H.add(Sph((0, -0.1092, 1.6548), 0.0087), 0.004)                            # tip
    H.add(Ell((0.0122, -0.1000, 1.6478), (0.0060, 0.0085, 0.0062)), 0.004)     # ala
    H.add(Cone((0, -0.1085, 1.6476), (0, -0.0975, 1.6432), 0.0042, 0.0040), 0.003)        # columella
    H.sub(Ell((0.0068, -0.1035, 1.6440), (0.0034, 0.0056, 0.0042)), 0.002)     # nostril
    # lips
    H.add(Cone((0, -0.0935, 1.6240), (0.011, -0.0915, 1.6235), 0.0052, 0.0046), 0.004)
    H.add(Cone((0.011, -0.0915, 1.6235), (0.0215, -0.0850, 1.6212), 0.0046, 0.0028), 0.004)
    H.add(Cone((0, -0.0915, 1.6140), (0.010, -0.0895, 1.6148), 0.0062, 0.0054), 0.004)
    H.add(Cone((0.010, -0.0895, 1.6148), (0.0205, -0.0845, 1.6180), 0.0054, 0.0028), 0.004)
    H.sub(Cone((0, -0.0955, 1.6010), (0.012, -0.0930, 1.6015), 0.0055, 0.0045), 0.006)    # labiomental groove
    H.sub(Cone((0, -0.1030, 1.6395), (0, -0.1010, 1.6300), 0.0022, 0.0028), 0.004)        # philtrum
    # the whole body is unioned last: head and body then agree exactly around the collar
    H.add(B, 0.018)
    return {'head': H, 'body': B}
