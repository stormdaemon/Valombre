"""Tiny implicit-surface sculpting kit (numpy only) for the organic monsters of VALOMBRE.

Field: a regular grid of signed distances. Primitives (ellipsoids, round cones, spheres) are smoothly united /
subtracted block by block (each primitive only touches the grid cells around it), value noise can be added,
and the zero level set is polygonised with naive surface nets (clean, manifold quad mesh).
"""
import math
import numpy as np


def smin(a, b, k):
    if k <= 1e-6:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def rot_xyz(rx=0.0, ry=0.0, rz=0.0):
    """Rotation matrix (degrees); columns = local axes expressed in world."""
    rx, ry, rz = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


class Ell:
    def __init__(self, c, r, rot=None):
        self.c = np.asarray(c, np.float32)
        self.r = np.asarray(r, np.float32) if np.ndim(r) else np.full(3, r, np.float32)
        self.rot = None if rot is None else np.asarray(rot, np.float32)

    def bounds(self):
        m = float(self.r.max()) if self.rot is not None else self.r
        return self.c - m, self.c + m

    def dist(self, X, Y, Z):
        q = np.stack([X - self.c[0], Y - self.c[1], Z - self.c[2]], -1)
        if self.rot is not None:
            q = q @ self.rot
        a = q / self.r
        b = q / (self.r * self.r)
        k0 = np.sqrt((a * a).sum(-1))
        k1 = np.sqrt((b * b).sum(-1))
        return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -float(self.r.min()))


def Sph(c, r):
    return Ell(c, (r, r, r))


class Cone:
    """Round cone: segment a -> b, radius ra -> rb."""

    def __init__(self, a, b, ra, rb=None):
        self.a, self.b = np.asarray(a, np.float32), np.asarray(b, np.float32)
        self.ra, self.rb = float(ra), float(ra if rb is None else rb)

    def bounds(self):
        m = max(self.ra, self.rb)
        return np.minimum(self.a, self.b) - m, np.maximum(self.a, self.b) + m

    def dist(self, X, Y, Z):
        pa = np.stack([X - self.a[0], Y - self.a[1], Z - self.a[2]], -1)
        ba = self.b - self.a
        t = np.clip((pa * ba).sum(-1) / max(float((ba * ba).sum()), 1e-12), 0.0, 1.0)
        d = pa - ba * t[..., None]
        return np.sqrt((d * d).sum(-1)) - (self.ra + (self.rb - self.ra) * t)


class Field:
    def __init__(self, lo, hi, h):
        self.lo = np.asarray(lo, np.float32)
        self.h = float(h)
        self.n = (np.ceil((np.asarray(hi, np.float32) - self.lo) / h).astype(int) + 1)
        self.F = np.full(tuple(self.n), 1.0, np.float32)

    def _block(self, lo, hi, pad):
        i0 = np.clip(np.floor((np.asarray(lo) - pad - self.lo) / self.h).astype(int), 0, self.n - 1)
        i1 = np.clip(np.ceil((np.asarray(hi) + pad - self.lo) / self.h).astype(int) + 1, 1, self.n)
        ax = [self.lo[a] + np.arange(i0[a], i1[a], dtype=np.float32) * self.h for a in range(3)]
        X, Y, Z = np.meshgrid(ax[0], ax[1], ax[2], indexing='ij')
        return (slice(i0[0], i1[0]), slice(i0[1], i1[1]), slice(i0[2], i1[2])), X, Y, Z

    def add(self, prim, k=0.05, mirror=False):
        """Smooth union. mirror=True also adds the primitive mirrored through x = 0."""
        for sx in ((1.0, -1.0) if mirror else (1.0,)):
            lo, hi = prim.bounds()
            lo, hi = np.array(lo, np.float32), np.array(hi, np.float32)
            if sx < 0:
                lo[0], hi[0] = -hi[0], -lo[0]
            sl, X, Y, Z = self._block(lo, hi, k * 1.5 + 3 * self.h + 0.03)
            d = prim.dist(X * sx, Y, Z).astype(np.float32)
            self.F[sl] = smin(self.F[sl], d, k)

    def cut(self, prim, k=0.03, mirror=False):
        """Smooth subtraction."""
        for sx in ((1.0, -1.0) if mirror else (1.0,)):
            lo, hi = prim.bounds()
            lo, hi = np.array(lo, np.float32), np.array(hi, np.float32)
            if sx < 0:
                lo[0], hi[0] = -hi[0], -lo[0]
            sl, X, Y, Z = self._block(lo, hi, k * 1.5 + 3 * self.h)
            d = prim.dist(X * sx, Y, Z).astype(np.float32)
            self.F[sl] = -smin(-self.F[sl], d, k)

    def floor(self, z=0.0):
        zs = self.lo[2] + np.arange(self.n[2], dtype=np.float32) * self.h
        self.F = np.maximum(self.F, (z - zs)[None, None, :])

    def noise(self, cell, amp, seed=0, band=0.12):
        """Add smooth value noise (lattice spacing `cell` meters) near the surface."""
        rs = np.random.RandomState(seed)
        m = [int(math.ceil(self.n[a] * self.h / cell)) + 2 for a in range(3)]
        A = rs.rand(*m).astype(np.float32) - 0.5
        for a in range(3):
            t = np.arange(self.n[a], dtype=np.float32) * self.h / cell
            i0 = np.floor(t).astype(int)
            f = t - i0
            f = f * f * (3 - 2 * f)
            A0 = np.take(A, i0, axis=a)
            A1 = np.take(A, i0 + 1, axis=a)
            sh = [1, 1, 1]
            sh[a] = -1
            f = f.reshape(sh)
            A = A0 * (1 - f) + A1 * f
        w = np.clip(1.0 - np.abs(self.F) / band, 0.0, 1.0)
        self.F += (A * (2.0 * amp)) * w

    def sample(self, P):
        """Trilinear lookup of the field at points P (N, 3)."""
        P = np.asarray(P, np.float32)
        t = (P - self.lo) / self.h
        i0 = np.floor(t).astype(int)
        for a in range(3):
            i0[:, a] = np.clip(i0[:, a], 0, self.n[a] - 2)
        f = np.clip(t - i0, 0.0, 1.0)
        x, y, z = i0[:, 0], i0[:, 1], i0[:, 2]
        F = self.F
        c00 = F[x, y, z] * (1 - f[:, 0]) + F[x + 1, y, z] * f[:, 0]
        c10 = F[x, y + 1, z] * (1 - f[:, 0]) + F[x + 1, y + 1, z] * f[:, 0]
        c01 = F[x, y, z + 1] * (1 - f[:, 0]) + F[x + 1, y, z + 1] * f[:, 0]
        c11 = F[x, y + 1, z + 1] * (1 - f[:, 0]) + F[x + 1, y + 1, z + 1] * f[:, 0]
        c0 = c00 * (1 - f[:, 1]) + c10 * f[:, 1]
        c1 = c01 * (1 - f[:, 1]) + c11 * f[:, 1]
        return c0 * (1 - f[:, 2]) + c1 * f[:, 2]

    def surface_from(self, origin, direction, far=1.5):
        """First surface point met when walking from `origin` (inside) along `direction` (outward)."""
        o = np.asarray(origin, np.float32)
        d = np.asarray(direction, np.float32)
        d = d / np.linalg.norm(d)
        ts = np.arange(0.0, far, self.h * 0.5, dtype=np.float32)
        v = self.sample(o[None, :] + ts[:, None] * d[None, :])
        out = np.nonzero(v > 0)[0]
        if len(out) == 0 or out[0] == 0:
            return None
        i = out[0]
        t = ts[i - 1] + (ts[i] - ts[i - 1]) * (-v[i - 1]) / max(v[i] - v[i - 1], 1e-9)
        return o + d * t

    def radius(self, origin, direction, far=1.6):
        """Distance from `origin` to the OUTERMOST surface along `direction` (walks inward from far away)."""
        o = np.asarray(origin, np.float32)
        d = np.asarray(direction, np.float32)
        d = d / np.linalg.norm(d)
        ts = np.arange(far, 0.0, -self.h * 0.5, dtype=np.float32)
        v = self.sample(o[None, :] + ts[:, None] * d[None, :])
        ins = np.nonzero(v < 0)[0]
        if len(ins) == 0:
            return 0.0
        i = ins[0]
        if i == 0:
            return float(ts[0])
        return float(ts[i] + (ts[i - 1] - ts[i]) * (-v[i]) / max(v[i - 1] - v[i], 1e-9))

    def mesh(self):
        """Naive surface nets -> (vertices (N, 3) float32, quads (M, 4) int32), outward winding."""
        F = self.F
        ins = F < 0
        cnt = (ins[:-1, :-1, :-1].astype(np.int8) + ins[1:, :-1, :-1] + ins[:-1, 1:, :-1] + ins[1:, 1:, :-1]
               + ins[:-1, :-1, 1:] + ins[1:, :-1, 1:] + ins[:-1, 1:, 1:] + ins[1:, 1:, 1:])
        act = (cnt > 0) & (cnt < 8)
        ci, cj, ck = np.nonzero(act)
        nv = len(ci)
        vid = np.full(act.shape, -1, np.int32)
        vid[ci, cj, ck] = np.arange(nv, dtype=np.int32)
        corners = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
        fv = np.stack([F[ci + a, cj + b, ck + c] for a, b, c in corners], 1)
        acc = np.zeros((nv, 3), np.float32)
        num = np.zeros(nv, np.float32)
        for a, b in ((0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)):
            fa, fb = fv[:, a], fv[:, b]
            m = (fa < 0) != (fb < 0)
            t = np.where(m, fa / np.where(m, fa - fb, 1.0), 0.0)
            pa, pb = np.array(corners[a], np.float32), np.array(corners[b], np.float32)
            acc += (pa[None, :] + t[:, None] * (pb - pa)[None, :]) * m[:, None]
            num += m
        V = (np.stack([ci, cj, ck], 1).astype(np.float32) + acc / num[:, None]) * self.h + self.lo
        quads = []
        # x edges
        e = ins[:-1, 1:-1, 1:-1] != ins[1:, 1:-1, 1:-1]
        i, j, k = np.nonzero(e)
        j, k = j + 1, k + 1
        q = np.stack([vid[i, j - 1, k - 1], vid[i, j, k - 1], vid[i, j, k], vid[i, j - 1, k]], 1)
        fl = ~ins[i, j, k]
        q[fl] = q[fl][:, ::-1]
        quads.append(q)
        # y edges
        e = ins[1:-1, :-1, 1:-1] != ins[1:-1, 1:, 1:-1]
        i, j, k = np.nonzero(e)
        i, k = i + 1, k + 1
        q = np.stack([vid[i - 1, j, k - 1], vid[i, j, k - 1], vid[i, j, k], vid[i - 1, j, k]], 1)
        fl = ins[i, j, k]
        q[fl] = q[fl][:, ::-1]
        quads.append(q)
        # z edges
        e = ins[1:-1, 1:-1, :-1] != ins[1:-1, 1:-1, 1:]
        i, j, k = np.nonzero(e)
        i, j = i + 1, j + 1
        q = np.stack([vid[i - 1, j - 1, k], vid[i, j - 1, k], vid[i, j, k], vid[i - 1, j, k]], 1)
        fl = ~ins[i, j, k]
        q[fl] = q[fl][:, ::-1]
        quads.append(q)
        Q = np.concatenate(quads, 0)
        Q = Q[(Q >= 0).all(1)]
        return V, Q
