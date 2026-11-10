"""VALOMBRE nature pack - trees (oak_a/b, pine_a/b, birch_a, willow_a, dead_a/b), LOD0 + LOD1 each.

  blender -b --factory-startup -P tools/blender/nat_trees.py            (all trees)
  blender -b --factory-startup -P tools/blender/nat_trees.py -- oak_a   (some trees)

Skeleton = recursive branching with tropism; trunk/limbs = tapered tubes; foliage = atlas cards
(leaves_a.png) with puffy custom normals; COLOR_0 = (AO, wind weight, phase).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nat_common import *

RECTS = None


# ----------------------------------------------------------------------------- skeleton
class Branch:
    def __init__(self, pts, rad, g, phase, level, parent=None, tag=''):
        self.pts = np.asarray(pts, np.float64)
        self.rad = np.asarray(rad, np.float64)
        self.g = np.asarray(g, np.float64)
        self.phase = float(phase)
        self.level = level
        self.parent = parent
        self.tag = tag
        self.seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.cum = np.concatenate([[0.0], np.cumsum(self.seg)])
        self.length = float(self.cum[-1])
        self.tip = 'cone'
        self.sides = None
        self.rad_fn = None
        self.keep_lod1 = True

    def at(self, t):
        s = min(max(t, 0.0), 1.0) * self.length
        i = int(min(max(np.searchsorted(self.cum, s) - 1, 0), len(self.seg) - 1))
        f = (s - self.cum[i]) / max(self.seg[i], 1e-9)
        pos = self.pts[i] + (self.pts[i + 1] - self.pts[i]) * f
        tan = unit(self.pts[i + 1] - self.pts[i])
        return pos, tan, self.rad[i] + (self.rad[i + 1] - self.rad[i]) * f, self.g[i] + (self.g[i + 1] - self.g[i]) * f

    def t_of_z(self, z):
        zs = self.pts[:, 2]
        return float(np.interp(z, zs, self.cum)) / max(self.length, 1e-9)

    def resampled(self, n):
        """Copy with n segments (uniform in arclength, end points kept)."""
        ts = np.linspace(0, 1, n + 1)
        pts, rad, g = [], [], []
        for t in ts:
            p, _, r, gg = self.at(t)
            pts.append(p)
            rad.append(r)
            g.append(gg)
        pts[-1] = self.pts[-1]
        rad[-1] = self.rad[-1]
        b = Branch(pts, rad, g, self.phase, self.level, self.parent, self.tag)
        b.tip, b.rad_fn = self.tip, None
        return b


def grow(rng, start, d0, length, nseg, r0, r1, gnarl=0.15, trop=None, taper=1.0, g0=0.0, g1=0.1, phase=0.0,
         level=0, seg_pow=1.0, parent=None, tag=''):
    pts = [np.array(start, np.float64)]
    d = unit(d0)
    ts = np.power(np.arange(nseg + 1) / nseg, seg_pow)
    for i in range(nseg):
        t = ts[i + 1]
        seg = length * (ts[i + 1] - ts[i])
        if i > 0:
            rv = rng.normal(size=3)
            rv -= d * np.dot(rv, d)
            d = d + rv * gnarl
            if trop is not None:
                d = d + np.asarray(trop(t, d, pts[-1]), np.float64)
            d = unit(d)
        pts.append(pts[-1] + d * seg)
    rad = r0 + (r1 - r0) * np.power(ts, taper)
    g = g0 + (g1 - g0) * ts
    return Branch(pts, rad, g, phase, level, parent, tag)


def child_dir(tan, angle, az):
    """Direction at `angle` degrees from the parent tangent. az (degrees) turns around the parent:
    0 = horizontal side, 90 = upper side, 180 = other side, 270 = lower side."""
    tan = unit(tan)
    side = np.cross(UP, tan)
    if np.linalg.norm(side) < 1e-3:
        side = np.array([1.0, 0, 0])
    side = unit(side)
    upv = np.cross(tan, side)
    a, z = math.radians(angle), math.radians(az)
    return unit(math.cos(a) * tan + math.sin(a) * (math.cos(z) * side + math.sin(z) * upv))


def sides_for(r, lod=0):
    if lod == 0:
        return 10 if r >= 0.34 else 8 if r >= 0.26 else 6 if r >= 0.12 else 5 if r >= 0.06 else 4 if r >= 0.032 else 3
    return 6 if r >= 0.34 else 5 if r >= 0.2 else 4 if r >= 0.09 else 3


def ray_ellipsoid(p, d, c, rad):
    """Distance from p along d to the surface of the ellipsoid (centre c, radii rad). 0 when p is outside."""
    q = (np.asarray(p, float) - c) / rad
    e = np.asarray(d, float) / rad
    A, B, C = float(e @ e), float(2 * q @ e), float(q @ q - 1.0)
    disc = B * B - 4 * A * C
    if C > 0 or disc < 0:
        return 0.0
    return (-B + math.sqrt(disc)) / (2 * A)


def skin(mb, branches, rng, mat=0, lod=0, ao_mul=1.0):
    for br in branches:
        s = br.sides or sides_for(br.rad[0], lod)
        tube(mb, br.pts, br.rad, s, mat, g=br.g, phase=br.phase, v0=rng.uniform(0, 3.0), tip=br.tip,
             rad_fn=br.rad_fn, uoff=rng.uniform(0, 1.0), ao=ao_mul)


def flare_fn(zs, amp=0.55, h=0.45, lobes=5, lobe_amp=0.22, phase=0.0):
    """Root flare for trunk rings: zs = z of every ring."""
    def f(ang, i):
        z = max(zs[i], -0.5)
        k = math.exp(-max(z + 0.1, 0.0) / h)
        return 1.0 + amp * k * (1.0 + lobe_amp * np.cos(lobes * ang + phase) + 0.1 * np.cos(2 * ang + phase * 2))
    return f


def add_roots(branches, rng, trunk_r, n=5, spread=2.6, level=1, z0=0.55, rscale=1.0, sides=4):
    az0 = rng.uniform(0, 2 * math.pi)
    for k in range(n):
        az = az0 + 2 * math.pi * (k + rng.uniform(-0.22, 0.22)) / n
        o = np.array([math.cos(az), math.sin(az), 0.0])
        side = np.array([-o[1], o[0], 0.0])
        sp = spread * rng.uniform(0.75, 1.2)
        R = trunk_r
        wob = rng.uniform(-0.25, 0.25)
        pts = [o * R * 0.25 + UP * z0 * rng.uniform(0.8, 1.2),
               o * R * 1.15 + UP * 0.20 + side * wob * R * 0.3,
               o * R * (1.15 + (sp - 1.15) * 0.5) + UP * 0.02 + side * wob * R,
               o * R * sp + UP * -0.32 + side * wob * R * 1.6]
        rad = np.array([0.50, 0.40, 0.25, 0.10]) * R * rscale * rng.uniform(0.85, 1.15)
        b = Branch(pts, rad, [0, 0, 0, 0], 0.5, level, tag='root')
        b.sides = sides
        b.keep_lod1 = False
        branches.append(b)


# ----------------------------------------------------------------------------- foliage sites
class Site:
    __slots__ = ('pos', 'dir', 'g', 'phase', 'clump', 'size', 'tag')

    def __init__(self, pos, dir, g, phase, clump, size=1.0, tag=''):
        self.pos, self.dir, self.g, self.phase, self.clump, self.size, self.tag = pos, unit(dir), g, phase, clump, size, tag


def rot_about(v, axis, ang):
    axis = unit(axis)
    c, s = math.cos(ang), math.sin(ang)
    return v * c + np.cross(axis, v) * s + axis * np.dot(axis, v) * (1 - c)


def place_cards(mb, sites, rng, cells, S_range, crown_c, nseg_big=2, droop=0.12, roll_jit=60.0, big=1.9, mat=1,
                out_bias=0.0, width=1.0):
    for s in sites:
        rect = RECTS[cells[rng.randint(len(cells))]]
        S = rng.uniform(*S_range) * s.size
        d = s.dir
        if out_bias:
            o = unit(s.pos - crown_c)
            d = unit(d + o * out_bias)
        o = s.pos + d * 0.5 * S - crown_c
        r = np.cross(d, o)
        if np.linalg.norm(r) < 1e-4:
            r = np.cross(d, (1, 0, 0))
        r = rot_about(unit(r), d, math.radians(rng.uniform(-roll_jit, roll_jit)))
        nseg = nseg_big if S >= big else 1
        card(mb, rect, s.pos - d * 0.03 * S, d, r, S, nseg=nseg, droop=droop if nseg > 1 else 0.0,
             flip=rng.rand() < 0.5, g0=s.g, phase=(s.phase + rng.uniform(-0.12, 0.12)) % 1.0, mat=mat, clump=s.clump,
             width=width)


def kmeans(P, k, rng, iters=14):
    P = np.asarray(P, np.float64)
    k = min(k, len(P))
    cen = [P[rng.randint(len(P))]]
    d2 = np.full(len(P), 1e18)
    for i in range(1, k):                                   # farthest point init
        d2 = np.minimum(d2, ((P - cen[-1]) ** 2).sum(axis=1))
        cen.append(P[int(np.argmax(d2))])
    cen = np.array(cen)
    for it in range(iters):
        lab = np.argmin(((P[:, None, :] - cen[None, :, :]) ** 2).sum(axis=2), axis=1)
        for j in range(k):
            m = lab == j
            if m.any():
                cen[j] = P[m].mean(axis=0)
    lab = np.argmin(((P[:, None, :] - cen[None, :, :]) ** 2).sum(axis=2), axis=1)
    return cen, lab


def lod1_shell_cards(mb, mb0, rng, cell, k, crown_c, S_min=2.4, S_max=4.4, S_mul=1.0, mat=1, nseg=1, droop=0.1,
                     g0=0.35, up=0.75, out=0.65):
    """Big cards replacing clusters of LOD0 cards: upright planes with random azimuth, growing up and outward,
    centred on the cluster (keeps the LOD0 silhouette and volume)."""
    C0 = np.array([c for c, r in mb0.cards])
    R0 = np.array([r for c, r in mb0.cards])
    cen, lab = kmeans(C0, k, rng)
    rect = RECTS[cell]
    cyc = (rect['cy0'] + rect['cy1']) / 2
    cw = (rect['cx1'] - rect['cx0'])
    for j in range(len(cen)):
        m = lab == j
        if not m.any():
            continue
        c = C0[m].mean(axis=0)
        ext = float(np.sqrt((((C0[m] - c) ** 2).sum(axis=1)).mean())) + float(R0[m].mean()) / 0.62 * 0.8
        S = min(max(2.0 * ext / cw * S_mul, S_min), S_max)
        o = unit(c - crown_c)
        d = unit(UP * up + o * out + rng.normal(size=3) * 0.18)
        az = rng.uniform(0, 2 * math.pi)
        nh = np.array([math.cos(az), math.sin(az), 0.0])
        r = np.cross(d, nh)
        if np.linalg.norm(r) < 0.2:
            r = np.cross(d, (nh[1], -nh[0], 0.0))
        anchor = c - d * (cyc - rect['cy0']) * S
        card(mb, rect, anchor, d, unit(r), S, nseg=nseg, droop=droop, flip=rng.rand() < 0.5, g0=g0,
             phase=rng.rand(), mat=mat, clump=c - o * 0.6 * ext)


def crown_center(sites):
    P = np.array([s.pos for s in sites])
    mn, mx = P.min(axis=0), P.max(axis=0)
    c = (mn + mx) / 2
    c[2] = mn[2] + (mx[2] - mn[2]) * 0.4
    return c


def lod1_wood(T, rng, trunk_segs=4, limb_segs=4, twig_min=0.045, trunk_sides=6, flare=0.5, limb_min=0.0,
              twig_segs=2):
    out = []
    for b in T['branches']:
        if not b.keep_lod1:
            continue
        if b.level == 0:
            nb = b.resampled(trunk_segs)
            zs = nb.pts[:, 2]
            nb.rad = nb.rad * np.array([1.0 + flare * math.exp(-max(z + 0.1, 0) / 0.5) for z in zs])
            nb.sides = trunk_sides
        elif b.level == 1:
            if b.rad[0] < limb_min:
                continue
            nb = b.resampled(limb_segs)
            nb.sides = 4 if b.rad[0] > 0.12 else 3
        else:
            if b.rad[0] < twig_min:
                continue
            nb = b.resampled(twig_segs)
            nb.sides = 3
        nb.tip = b.tip
        out.append(nb)
    return out


def assemble_broadleaf(T, droop=0.12, roll_jit=60.0, lod1_S=(2.6, 4.4), out_bias=0.0, lod1_droop=0.1,
                       lod1_twigs=0.045, ao_lo=0.33, big=2.08, lod1_up=0.75, lod1_out=0.65, kappa=0.42,
                       lod1_limb_segs=4):
    """LOD0 + LOD1 meshes for a broadleaf tree described by T (branches + foliage sites)."""
    rng = T['rng']
    mats = [nat_mat(T['bark']), nat_mat('M_leaves')]
    cc = crown_center(T['sites'])
    mb0 = MB()
    skin(mb0, T['branches'], rng, lod=0)
    place_cards(mb0, T['sites'], rng, T['cells'], T['S'], cc, droop=droop, roll_jit=roll_jit, out_bias=out_bias,
                big=big)
    crown = finish_tree(mb0, lo=ao_lo, kappa=kappa)
    ob0 = mb0.build(T['name'] + '_LOD0', mats)
    mb1 = MB()
    skin(mb1, lod1_wood(T, rng, twig_min=lod1_twigs, limb_segs=lod1_limb_segs), rng, lod=1)
    lod1_shell_cards(mb1, mb0, rng, T['dense'], T['P']['lod1_cards'], cc, S_min=lod1_S[0], S_max=lod1_S[1],
                     droop=lod1_droop, up=lod1_up, out=lod1_out)
    finish_tree(mb1, crown=crown, lo=ao_lo, kappa=kappa * 1.9)
    ob1 = mb1.build(T['name'] + '_LOD1', mats)
    return ob0, ob1, mb0, mb1


# ----------------------------------------------------------------------------- OAK
def build_oak(name, seed, P):
    rng = np.random.RandomState(seed)
    br = []
    env_c, env_r = np.array(P['env'][0], float), np.array(P['env'][1], float)
    lean = unit((rng.normal() * P['lean'], rng.normal() * P['lean'], 1.0))
    trunk = grow(rng, (0, 0, -0.35), lean, P['trunk_len'] + 0.35, 7, P['r0'], P['r_top'], gnarl=0.07, taper=0.8,
                 g0=0.0, g1=0.03, phase=0.5, level=0, seg_pow=1.35, tag='trunk')
    trunk.rad_fn = flare_fn(trunk.pts[:, 2], amp=0.45, h=0.5, phase=rng.uniform(0, 6))
    br.append(trunk)
    add_roots(br, rng, P['r0'], n=P.get('roots', 5), spread=2.7)
    limbs = []
    az0 = rng.uniform(0, 360)
    ntop = P['top_limbs']
    for k in range(ntop + 1):                                    # crown-forming limbs from the trunk head
        if k == 0:
            ang, az = rng.uniform(6, 16), rng.uniform(0, 360)     # leader
        else:
            az = az0 + 360.0 * k / ntop + rng.uniform(-18, 18)
            ang = rng.uniform(*P['top_angle'])
        p, tan, r, g = trunk.at(0.88 + 0.1 * rng.rand())
        d = child_dir(tan, ang, az)
        L = max(2.8, ray_ellipsoid(p, d, env_c, env_r) * rng.uniform(0.86, 1.0))
        b = grow(rng, p, d, L, 6, r * rng.uniform(0.60, 0.74), 0.035, gnarl=P['gnarl'],
                 trop=lambda t, d_, q: (0, 0, 0.06), taper=0.85, g0=g, g1=g + 0.24, phase=rng.rand(), level=1,
                 parent=trunk, tag='top')
        limbs.append(b)
    nlat = P['side_limbs']
    for k in range(nlat):                                        # big spreading lateral limbs
        az = az0 + 360.0 * (k + 0.5) / nlat + rng.uniform(-22, 22) + 30
        ang = rng.uniform(*P['side_angle'])
        p, tan, r, g = trunk.at(rng.uniform(*P['side_t']))
        d = child_dir(tan, ang, az)
        L = max(2.8, ray_ellipsoid(p, d, env_c, env_r) * rng.uniform(0.9, 1.02))
        b = grow(rng, p, d, L, 6, r * rng.uniform(0.48, 0.58), 0.035, gnarl=P['gnarl'] * 1.1,
                 trop=lambda t, d_, q: (0, 0, -0.05 + 0.24 * t + max(0.0, 3.6 - q[2]) * 0.55), taper=0.8, g0=g,
                 g1=g + 0.26, phase=rng.rand(),
                 level=1, parent=trunk, tag='side')
        limbs.append(b)
    br += limbs
    sites = []
    for lb in limbs:
        n2 = max(3, int(round(P['n2'] * lb.length / 5.5 + rng.uniform(-0.4, 0.4))))
        side = rng.choice([0, 180])
        for k in range(n2):
            t = 0.34 + 0.60 * (k + rng.uniform(0.15, 0.85)) / n2
            p, tan, r, g = lb.at(t)
            side = 180 - side
            az = side + rng.uniform(-40, 40)
            if rng.rand() < 0.22:
                az = 90 + rng.uniform(-30, 30)                    # an upright shoot now and then
            d = child_dir(tan, rng.uniform(40, 68), az)
            d = unit(d + UP * 0.2 + unit(p - env_c) * 0.25)
            L2 = min(max(ray_ellipsoid(p, d, env_c, env_r) * rng.uniform(0.8, 1.02), 1.0), P.get('l2_max', 3.4))
            b2 = grow(rng, p, d, L2, 4 if L2 > 2.3 else 3, min(0.058, max(0.035, r * 0.5)), 0.016,
                      gnarl=P['gnarl'] * 1.15, trop=lambda t_, d_, q: (0, 0, 0.08), taper=0.9, g0=g,
                      g1=min(0.8, g + 0.26), phase=(lb.phase + rng.uniform(-0.08, 0.08)) % 1.0, level=2, parent=lb)
            br.append(b2)
            clump = b2.at(0.8)[0]
            n3 = 2 + (rng.rand() < 0.5) + (L2 > 2.2)
            sd3 = rng.choice([0, 180])
            for j in range(n3):
                t3 = 0.34 + 0.56 * (j + rng.uniform(0.2, 0.8)) / n3
                p3, tan3, r3, g3 = b2.at(t3)
                sd3 = 180 - sd3
                d3 = child_dir(tan3, rng.uniform(35, 62), sd3 + rng.uniform(-50, 50))
                L3 = rng.uniform(0.7, 1.25)
                b3 = grow(rng, p3, d3, L3, 2, min(0.026, max(0.016, r3 * 0.6)), 0.008, gnarl=0.25,
                          trop=lambda t_, d_, q: (0, 0, 0.05), g0=g3, g1=min(0.85, g3 + 0.2), phase=b2.phase,
                          level=3, parent=b2)
                b3.keep_lod1 = False
                br.append(b3)
                sites.append(Site(b3.pts[-1], b3.at(1.0)[1], b3.g[-1], b2.phase, clump))
                pm, tm, rm, gm = b3.at(0.4)
                sites.append(Site(pm, child_dir(tm, rng.uniform(35, 60), rng.uniform(0, 360)), gm, b2.phase, clump, 0.92))
            pe, te, re_, ge = b2.at(1.0)                           # branch end: a tuft of cards
            for j in range(3):
                dd = child_dir(te, rng.uniform(5, 42), 120.0 * j + rng.uniform(-40, 40))
                sites.append(Site(pe, dd, ge, b2.phase, clump, 1.05))
            p7, t7, r7, g7 = b2.at(0.6)
            sites.append(Site(p7, child_dir(t7, rng.uniform(35, 60), rng.uniform(20, 160)), g7, b2.phase, clump, 0.95))
        pe, te, re_, ge = lb.at(1.0)
        clump = lb.at(0.9)[0]
        for j in range(3):
            sites.append(Site(pe, child_dir(te, rng.uniform(5, 42), 120.0 * j + rng.uniform(-40, 40)), ge, lb.phase,
                              clump, 1.1))
        for t in (0.74, 0.88):
            pm, tm, rm, gm = lb.at(t)
            sites.append(Site(pm, child_dir(tm, rng.uniform(40, 65), rng.uniform(20, 160)), gm, lb.phase, clump))
    return dict(name=name, rng=rng, branches=br, sites=sites, trunk=trunk, bark='M_bark_oak',
                cells=['oak_twig_a', 'oak_twig_b'], dense='oak_dense', S=P['S'], P=P)


OAK_A = dict(lean=0.05, trunk_len=3.5, r0=0.52, r_top=0.37, top_limbs=4, top_angle=(34, 56), side_limbs=3,
             side_angle=(58, 78), side_t=(0.74, 0.93), gnarl=0.24, n2=4.4, S=(1.75, 2.25), lod1_cards=62,
             env=((0.0, 0.0, 6.0), (3.3, 3.3, 3.7)))
OAK_B = dict(lean=0.09, trunk_len=2.9, r0=0.62, r_top=0.45, top_limbs=3, top_angle=(40, 62), side_limbs=4,
             side_angle=(58, 78), side_t=(0.76, 0.94), gnarl=0.30, n2=4.0, S=(1.75, 2.3), lod1_cards=64, roots=6,
             env=((0.3, -0.2, 5.5), (3.7, 3.7, 3.4)))


# ----------------------------------------------------------------------------- BIRCH
def build_birch(name, seed, P):
    rng = np.random.RandomState(seed)
    br = []
    env_c, env_r = np.array(P['env'][0], float), np.array(P['env'][1], float)
    lean = unit((rng.normal() * 0.05 + 0.05, rng.normal() * 0.05, 1.0))
    H = P['height']
    trunk = grow(rng, (0, 0, -0.3), lean, H + 0.3, 11, P['r0'], 0.022, gnarl=0.05, taper=0.9,
                 trop=lambda t, d, q: (-q[0] * 0.012, -q[1] * 0.012, 0.03), g0=0.0, g1=0.3, phase=0.5, level=0,
                 seg_pow=1.15, tag='trunk')
    trunk.rad_fn = flare_fn(trunk.pts[:, 2], amp=0.5, h=0.3, lobes=4, phase=rng.uniform(0, 6))
    br.append(trunk)
    add_roots(br, rng, P['r0'], n=4, spread=2.6, z0=0.35, rscale=0.9, sides=4)
    leaders = [trunk]
    p, tan, r, g = trunk.at(0.42)                                 # a second leader
    d = child_dir(tan, 20, rng.uniform(0, 360))
    b = grow(rng, p, d, H * 0.50, 7, r * 0.6, 0.02, gnarl=0.06, trop=lambda t, d_, q: (0, 0, 0.06), g0=g, g1=0.32,
             phase=rng.rand(), level=1, parent=trunk, tag='leader')
    br.append(b)
    leaders.append(b)
    sites = []
    az = rng.uniform(0, 360)
    for ld in leaders:
        t0 = 0.36 if ld is trunk else 0.25
        n1 = P['n1'] if ld is trunk else P['n1'] // 2
        for k in range(n1):
            t = t0 + (0.95 - t0) * (k + rng.uniform(0.2, 0.8)) / n1
            p, tan, r, g = ld.at(t)
            az += 137.5 + rng.uniform(-25, 25)
            d = child_dir(tan, rng.uniform(38, 58), az)
            L = min(max(ray_ellipsoid(p, d, env_c, env_r) * rng.uniform(0.85, 1.05), 0.9), 3.6)
            b1 = grow(rng, p, d, L, 4, min(0.05, max(0.02, r * 0.42)), 0.01, gnarl=0.13,
                      trop=lambda t_, d_, q: (0, 0, 0.10 - 0.42 * t_ * t_), g0=g, g1=min(0.85, g + 0.4),
                      phase=rng.rand(), level=2, parent=ld)
            b1.sides = 4 if b1.rad[0] > 0.03 else 3
            br.append(b1)
            clump = b1.at(0.8)[0]
            n2 = 2 + (L > 2.0) + (rng.rand() < 0.4)
            sd = rng.choice([0, 180])
            for j in range(n2):
                t2 = 0.35 + 0.6 * (j + rng.uniform(0.2, 0.8)) / n2
                p2, tan2, r2, g2 = b1.at(t2)
                sd = 180 - sd
                d2 = child_dir(tan2, rng.uniform(35, 60), sd + rng.uniform(-40, 40))
                b2 = grow(rng, p2, d2, rng.uniform(0.6, 1.1), 2, 0.012, 0.006, gnarl=0.2,
                          trop=lambda t_, d_, q: (0, 0, -0.35), g0=g2, g1=min(0.9, g2 + 0.25), phase=b1.phase,
                          level=3, parent=b1)
                b2.keep_lod1 = False
                br.append(b2)
                pe, te, _, ge = b2.at(1.0)
                sites.append(Site(pe, unit(te * 0.5 + np.array([0, 0, -0.75])), ge, b1.phase, clump))
                pm, tm, _, gm = b2.at(0.35)
                sites.append(Site(pm, unit(tm * 0.6 + child_dir(tm, 60, rng.uniform(0, 360)) * 0.6), gm, b1.phase,
                                  clump, 0.9))
            pe, te, _, ge = b1.at(1.0)
            sites.append(Site(pe, unit(te + np.array([0, 0, -0.5])), ge, b1.phase, clump, 1.05))
            sites.append(Site(pe, unit(te * 0.3 + np.array([0, 0, -1.0])), ge, b1.phase, clump, 1.0))
            pm, tm, _, gm = b1.at(0.6)
            sites.append(Site(pm, child_dir(tm, rng.uniform(40, 70), rng.uniform(30, 150)), gm, b1.phase, clump, 0.95))
        pe, te, _, ge = ld.at(1.0)
        for j in range(3):
            sites.append(Site(ld.at(0.93)[0], child_dir(te, rng.uniform(10, 40), 120 * j + rng.uniform(-30, 30)), ge,
                              ld.phase, ld.at(0.85)[0], 1.0))
    return dict(name=name, rng=rng, branches=br, sites=sites, trunk=trunk, bark='M_bark_birch',
                cells=['birch_twig'], dense='birch_dense', S=P['S'], P=P)


BIRCH_A = dict(height=10.4, r0=0.17, n1=17, S=(1.15, 1.6), lod1_cards=46,
               env=((0.2, 0.0, 6.9), (2.1, 2.1, 4.3)))


# ----------------------------------------------------------------------------- WILLOW
def build_willow(name, seed, P):
    rng = np.random.RandomState(seed)
    br = []
    lean = unit((0.30, 0.08, 1.0))
    trunk = grow(rng, (-0.25, 0, -0.35), lean, 3.9, 6, P['r0'], P['r0'] * 0.74, gnarl=0.09, taper=0.8,
                 trop=lambda t, d, q: (0.03, 0, 0.0), g0=0.0, g1=0.03, phase=0.5, level=0, seg_pow=1.3, tag='trunk')
    trunk.rad_fn = flare_fn(trunk.pts[:, 2], amp=0.5, h=0.45, phase=rng.uniform(0, 6))
    br.append(trunk)
    add_roots(br, rng, P['r0'], n=5, spread=2.6)
    limbs = []
    az0 = rng.uniform(0, 360)
    nl = P['limbs']
    for k in range(nl):
        az = az0 + 360.0 * k / nl + rng.uniform(-20, 20)
        ang = rng.uniform(28, 62) if k else 12.0
        p, tan, r, g = trunk.at(0.8 + 0.18 * rng.rand())
        d = unit(child_dir(tan, ang, az) + UP * 0.25)
        L = rng.uniform(*P['limb_len'])
        b = grow(rng, p, d, L, 7, r * rng.uniform(0.5, 0.62), 0.03, gnarl=0.17,
                 trop=lambda t, d_, q: (0, 0, 0.20 - 0.50 * t), taper=0.85, g0=g, g1=g + 0.3, phase=rng.rand(),
                 level=1, parent=trunk)
        limbs.append(b)
    br += limbs
    hang = []          # (pos, tangent, g, phase, clump)
    tops = []
    for lb in limbs:
        n2 = P['n2']
        side = rng.choice([0, 180])
        for k in range(n2):
            t = 0.3 + 0.62 * (k + rng.uniform(0.2, 0.8)) / n2
            p, tan, r, g = lb.at(t)
            side = 180 - side
            d = child_dir(tan, rng.uniform(40, 65), side + rng.uniform(-30, 45))
            d = unit(d + UP * 0.15)
            L2 = rng.uniform(1.6, 2.9)
            b2 = grow(rng, p, d, L2, 4, min(0.07, max(0.03, r * 0.5)), 0.012, gnarl=0.16,
                      trop=lambda t_, d_, q: (0, 0, 0.04 - 0.36 * t_), g0=g, g1=min(0.8, g + 0.3),
                      phase=(lb.phase + rng.uniform(-0.08, 0.08)) % 1.0, level=2, parent=lb)
            br.append(b2)
            clump = b2.at(0.5)[0] - UP * 1.0
            for tt in (0.45, 0.72, 0.98):
                q, tq, _, gq = b2.at(tt)
                hang.append((q, tq, gq, b2.phase, clump))
            for tt in (0.35, 0.7):
                q, tq, _, gq = b2.at(tt)
                tops.append((q, tq, gq, b2.phase, clump))
        clump = lb.at(0.7)[0] - UP * 1.0
        for tt in (0.55, 0.75, 0.9, 1.0):
            q, tq, _, gq = lb.at(tt)
            hang.append((q, tq, gq, lb.phase, clump))
        for tt in (0.5, 0.8):
            q, tq, _, gq = lb.at(tt)
            tops.append((q, tq, gq, lb.phase, clump))
    return dict(name=name, rng=rng, branches=br, hang=hang, tops=tops, trunk=trunk, bark='M_bark_oak', P=P)


def assemble_willow(T):
    rng = T['rng']
    P = T['P']
    mats = [nat_mat(T['bark']), nat_mat('M_leaves')]
    rect = RECTS['willow_strands']
    ch = rect['cy1'] - rect['cy0']
    mb0 = MB()
    skin(mb0, T['branches'], rng, lod=0)
    allp = np.array([h[0] for h in T['hang']])
    cxy = allp.mean(axis=0)
    for i, (q, tq, g, ph, clump) in enumerate(T['hang']):
        th = unit((tq[0], tq[1], 0.0)) if abs(tq[2]) < 0.98 else np.array([1.0, 0, 0])
        radial = unit((q[0] - cxy[0], q[1] - cxy[1], 0.0))
        for j in range(2):
            # one sheet across the outward direction (seen from outside), one along the branch
            base = np.cross(UP, radial) if j == 0 else th
            r = rot_about(base, UP, math.radians(rng.uniform(-35, 35)))
            r = unit(r + UP * (rng.uniform(-0.3, 0.3) if j == 0 else float(tq[2]) * 0.9))
            S = rng.uniform(1.35, 1.8)
            length = min(rng.uniform(*P['hang_len']), q[2] - rng.uniform(0.35, 0.9))
            if length < 0.8:
                continue
            d = unit(np.array([0, 0, -1.0]) + radial * rng.uniform(-0.02, 0.10))
            off = r * rng.uniform(-0.25, 0.25) * S + radial * rng.uniform(-0.2, 0.3)
            card(mb0, rect, q + off + UP * 0.05, d, r, S, nseg=3, droop=0.0, flip=rng.rand() < 0.5, g0=g,
                 phase=(ph + rng.uniform(-0.12, 0.12)) % 1.0, clump=clump, lscale=length / (ch * S),
                 curl=rng.uniform(-0.05, 0.05), ortho=False)
    for (q, tq, g, ph, clump) in T['tops']:
        r = unit(np.cross(tq, UP)) if abs(tq[2]) < 0.95 else np.array([1.0, 0, 0])
        r = rot_about(r, UP, math.radians(rng.uniform(-40, 40)))
        d = unit(tq * 0.9 + UP * rng.uniform(0.25, 0.7))
        S = rng.uniform(1.2, 1.6)
        card(mb0, rect, q - d * 0.1, d, r, S, nseg=2, droop=0.35, flip=rng.rand() < 0.5, g0=g,
             phase=(ph + rng.uniform(-0.12, 0.12)) % 1.0, clump=clump, lscale=rng.uniform(0.75, 1.1))
    crown = finish_tree(mb0, lo=0.36, kappa=0.3)
    ob0 = mb0.build(T['name'] + '_LOD0', mats)
    # ---- LOD1: fewer, wider, denser curtains at the cluster positions of the LOD0 anchors
    mb1 = MB()
    skin(mb1, lod1_wood(T, rng, twig_min=0.05), rng, lod=1)
    rect1 = RECTS['willow_dense']
    ch1 = rect1['cy1'] - rect1['cy0']
    H = np.array([h[0] for h in T['hang']])
    cen, lab = kmeans(H, P['lod1_cards'], rng)
    for j in range(len(cen)):
        m = lab == j
        if not m.any():
            continue
        q = H[m].mean(axis=0)
        q[2] = H[m][:, 2].max() + 0.1
        radial = unit((q[0] - cxy[0], q[1] - cxy[1], 0.0))
        base = np.cross(UP, radial)
        r = rot_about(base, UP, math.radians(rng.uniform(-50, 50)))
        S = rng.uniform(2.3, 2.9)
        length = min(P['hang_len'][1] * rng.uniform(0.85, 1.05) + 0.3, q[2] - 0.4)
        d = unit(np.array([0, 0, -1.0]) + radial * 0.06)
        card(mb1, rect1, q, d, r, S, nseg=2, flip=rng.rand() < 0.5, g0=0.4, phase=rng.rand(),
             clump=q - radial * 1.5 - UP * 1.0, lscale=length / (ch1 * S))
    T2 = np.array([t[0] for t in T['tops']])
    cen2, lab2 = kmeans(T2, max(6, P['lod1_cards'] // 4), rng)
    for j in range(len(cen2)):
        q = cen2[j]
        radial = unit((q[0] - cxy[0], q[1] - cxy[1], 0.0))
        r = rot_about(np.cross(UP, radial), UP, math.radians(rng.uniform(-50, 50)))
        d = unit(radial * 0.7 + UP * 0.6)
        S = rng.uniform(2.2, 2.7)
        card(mb1, rect1, q - d * 0.5, d, r, S, nseg=2, droop=0.4, flip=rng.rand() < 0.5, g0=0.4, phase=rng.rand(),
             clump=q - UP * 1.0, lscale=0.75)
    finish_tree(mb1, crown=crown, lo=0.36, kappa=0.5)
    ob1 = mb1.build(T['name'] + '_LOD1', mats)
    return ob0, ob1, mb0, mb1


WILLOW_A = dict(r0=0.46, limbs=5, limb_len=(4.6, 5.8), n2=4, hang_len=(2.0, 4.6), lod1_cards=40)


# ----------------------------------------------------------------------------- PINES
def build_pine(name, seed, P):
    rng = np.random.RandomState(seed)
    br = []
    H = P['height']
    lean = unit((rng.normal() * 0.02, rng.normal() * 0.02, 1.0))
    trunk = grow(rng, (0, 0, -0.3), lean, H + 0.3, 12, P['r0'], 0.025, gnarl=P.get('trunk_gnarl', 0.018), taper=0.95,
                 trop=lambda t, d, q: (-q[0] * 0.01, -q[1] * 0.01, 0.02), g0=0.0, g1=0.28, phase=0.5, level=0,
                 seg_pow=1.1, tag='trunk')
    trunk.rad_fn = flare_fn(trunk.pts[:, 2], amp=0.4, h=0.3, lobes=4, phase=rng.uniform(0, 6))
    br.append(trunk)
    add_roots(br, rng, P['r0'], n=4, spread=2.4, z0=0.4, rscale=0.85, sides=4)
    z0 = P['crown_base'] * H
    boughs = []
    z = H * 0.955
    tier = 0
    az = rng.uniform(0, 360)
    while z > z0:
        frac = (H - z) / (H - z0)                                 # 0 at the top, 1 at the crown base
        nb = P['per_tier'] if frac > 0.12 else max(3, P['per_tier'] - 1)
        az += 360.0 / nb / 2 + rng.uniform(-15, 15)
        for k in range(nb):
            if rng.rand() < P.get('skip', 0.0):
                continue
            zz = z + rng.uniform(-0.18, 0.18)
            t = trunk.t_of_z(zz)
            p, tan, r, g = trunk.at(t)
            a = az + 360.0 * k / nb + rng.uniform(-14, 14)
            prof = P['profile'](frac)
            L = max(0.5, P['spread'] * prof * rng.uniform(0.8, 1.12))
            a0, a1 = P.get('ang', (52, 98))
            ang = (a0 + (a1 - a0) * min(1.0, frac * 1.25)) + rng.uniform(-6, 6)
            d = child_dir(tan, ang, a)
            dr = P['droop'] * (0.4 + 0.9 * frac)
            b = grow(rng, p, d, L, 4, min(0.075, max(0.016, r * 0.34)), 0.008, gnarl=P.get('gnarl', 0.06),
                     trop=lambda t_, d_, q, dr=dr: (0, 0, -dr + (dr + 0.12) * t_ * t_ * 1.2), g0=g,
                     g1=min(0.85, g + 0.45), phase=rng.rand(), level=1, parent=trunk)
            b.sides = 4 if b.rad[0] > 0.05 else 3
            b.tier = tier
            br.append(b)
            boughs.append(b)
        z -= P['spacing'][0] + (P['spacing'][1] - P['spacing'][0]) * frac
        tier += 1
    stubs = []
    for k in range(P.get('stubs', 0)):                            # dead stubs under the crown
        zz = rng.uniform(P.get('stub_z', 0.22) * H, z0)
        p, tan, r, g = trunk.at(trunk.t_of_z(zz))
        d = child_dir(tan, rng.uniform(70, 100), rng.uniform(0, 360))
        b = grow(rng, p, d, rng.uniform(0.8, 2.4), 3, max(0.03, r * 0.3), 0.012, gnarl=0.15,
                 trop=lambda t_, d_, q: (0, 0, -0.08), g0=g, g1=g + 0.1, phase=rng.rand(), level=1, parent=trunk)
        b.sides = 3
        b.tier = -1
        br.append(b)
        stubs.append(b)
    return dict(name=name, rng=rng, branches=br, boughs=boughs, stubs=stubs, trunk=trunk, bark='M_bark_pine', P=P,
                H=H)


def pine_cards(mb, T, boughs, rng, flat_cell, hang_cell, wmul=1.0, side_sprays=True, nseg=2, hang=True, lmul=1.0,
               hang_mul=1.0):
    P = T['P']
    rf, rh = RECTS[flat_cell], RECTS[hang_cell]
    trunk = T['trunk']
    for b in boughs:
        p0 = b.at(0.10)[0]
        p1 = b.pts[-1]
        chord = p1 - p0
        cl = float(np.linalg.norm(chord))
        d = unit(chord)
        r = np.cross(d, UP)
        if np.linalg.norm(r) < 1e-3:
            r = np.array([1.0, 0, 0])
        r = unit(r)
        axis_p = trunk.at(trunk.t_of_z(p0[2] - 0.6))[0]
        g0 = b.g[0] + 0.05
        ph = b.phase
        # flat "tent" bough along the branch
        Lc = (cl + 0.35) * lmul
        S = Lc / (rf['cy1'] - rf['cy0'])
        w_world = min(P['bough_w'][1], max(P['bough_w'][0], cl * P['bough_ratio'])) * wmul
        width = w_world / ((rf['cx1'] - rf['cx0']) * S)
        card(mb, rf, p0, unit(d + UP * 0.04), rot_about(r, d, math.radians(rng.uniform(-10, 10))), S, nseg=nseg,
             droop=0.10, tent=P['tent'], cols=3, flip=rng.rand() < 0.5, g0=g0, phase=ph, clump=axis_p, width=width)
        # hanging curtain under the branch (branch along the bottom edge of the cell, base at u=0)
        if hang and cl > 1.0:
            Sh = cl * 1.02 / (rh['cx1'] - rh['cx0'])
            mid = p0 + chord * 0.5
            hl = min(1.6, max(0.5, cl * P['hang_ratio'])) * rng.uniform(0.8, 1.15) * hang_mul
            card(mb, rh, mid + UP * 0.03, unit(np.array([0, 0, -1.0]) + d * 0.08), d, Sh, nseg=1, g0=g0, phase=ph,
                 clump=axis_p, lscale=hl / ((rh['cy1'] - rh['cy0']) * Sh))
        # side sprays
        if side_sprays and cl > P.get('side_min', 1.7):
            for tt, sgn in ((0.42, 1), (0.66, -1)) if cl < 2.8 else ((0.36, 1), (0.55, -1), (0.74, 1)):
                q = b.at(tt)[0]
                dd = unit(rot_about(d, UP, math.radians(sgn * rng.uniform(40, 58))) + UP * -0.12)
                Ss = cl * rng.uniform(0.42, 0.56) / (rf['cy1'] - rf['cy0'])
                rr = unit(np.cross(dd, UP))
                card(mb, rf, q, dd, rot_about(rr, dd, math.radians(rng.uniform(-18, 18))), Ss, nseg=1, tent=P['tent'],
                     cols=3, flip=rng.rand() < 0.5, g0=min(0.9, g0 + 0.2), phase=ph, clump=axis_p,
                     width=min(1.0, 1.1 * wmul))


def assemble_pine(T):
    rng = T['rng']
    P = T['P']
    mats = [nat_mat(T['bark']), nat_mat('M_leaves')]
    trunk = T['trunk']
    rf = RECTS['pine_spray_a']
    mb0 = MB()
    skin(mb0, T['branches'], rng, lod=0)
    pine_cards(mb0, T, T['boughs'], rng, 'pine_spray_a', 'pine_spray_b')
    top = trunk.at(0.90)[0]
    for j in range(3):                                            # the leader
        a = math.radians(60 * j + rng.uniform(-10, 10))
        card(mb0, rf, top, UP, np.array([math.cos(a), math.sin(a), 0.0]), P['top_S'], nseg=1, g0=0.3, phase=0.5,
             clump=top - UP * 0.5, width=0.5)
    crown = finish_tree(mb0, lo=0.36, kappa=0.22, w_global=0.22, w_local=0.08, w_up=0.7)
    ob0 = mb0.build(T['name'] + '_LOD0', mats)
    # ---- LOD1: trunk + a subset of boughs with wider, denser cards
    mb1 = MB()
    wood = [b for b in lod1_wood(T, rng, trunk_segs=6, trunk_sides=5, flare=0.4, limb_min=9.9)]
    for b in T['stubs'][:P.get('lod1_stubs', 0)]:
        nb = b.resampled(2)
        nb.sides = 3
        wood.append(nb)
    skin(mb1, wood, rng, lod=1)
    by_tier = {}
    for b in T['boughs']:
        by_tier.setdefault(b.tier, []).append(b)
    keep = []
    for tier, bs in sorted(by_tier.items()):
        bs = sorted(bs, key=lambda b: -b.length)
        nk = max(2, int(math.ceil(len(bs) * P['lod1_keep'])))
        if tier % 2 == 1:
            nk = max(2, nk - 1)
        keep += bs[:nk]
    pine_cards(mb1, T, keep, rng, 'pine_dense', 'pine_spray_b', wmul=P['lod1_wmul'], side_sprays=False, nseg=1,
               lmul=1.05, hang_mul=1.25)
    rd = RECTS['pine_dense']
    for j in range(2):
        a = math.radians(90 * j + 20)
        card(mb1, rd, top, UP, np.array([math.cos(a), math.sin(a), 0.0]), P['top_S'], nseg=1, g0=0.3, phase=0.5,
             clump=top - UP * 0.5, width=0.55)
    finish_tree(mb1, crown=crown, lo=0.36, kappa=0.3, w_global=0.22, w_local=0.08, w_up=0.7)
    ob1 = mb1.build(T['name'] + '_LOD1', mats)
    return ob0, ob1, mb0, mb1


PINE_A = dict(height=17.5, r0=0.34, crown_base=0.24, per_tier=5, spread=3.5, droop=0.24, spacing=(0.62, 1.2),
              profile=lambda f: 0.10 + 0.90 * f ** 0.8, bough_w=(0.7, 2.0), bough_ratio=0.62, tent=0.52,
              hang_ratio=0.5, top_S=2.1, lod1_keep=0.62, lod1_wmul=1.45, stubs=3, stub_z=0.12)
PINE_B = dict(height=15.5, r0=0.40, crown_base=0.43, per_tier=4, spread=3.7, droop=0.30, spacing=(0.6, 1.25),
              profile=lambda f: (0.26 + 0.74 * min(1.0, f / 0.32) ** 0.8) * (1.0 - 0.45 * max(0.0, f - 0.6) / 0.4),
              bough_w=(0.6, 1.7), bough_ratio=0.5, tent=0.6, hang_ratio=0.6, top_S=1.8, lod1_keep=0.75,
              lod1_wmul=1.4, stubs=11, stub_z=0.2, skip=0.16, gnarl=0.13, trunk_gnarl=0.04, lod1_stubs=6,
              ang=(68, 102), side_min=1.4)


# ----------------------------------------------------------------------------- DEAD TREES
def build_dead(name, seed, P):
    rng = np.random.RandomState(seed)
    br = []
    lean = unit((P['lean'][0], P['lean'][1], 1.0))
    H = P['height']
    trunk = grow(rng, (0, 0, -0.3), lean, H + 0.3, 8, P['r0'], P['r_top'], gnarl=P['trunk_gnarl'], taper=0.9,
                 trop=lambda t, d, q: (0, 0, 0.05), g0=0.0, g1=0.06, phase=0.5, level=0, seg_pow=1.25, tag='trunk')
    trunk.rad_fn = flare_fn(trunk.pts[:, 2], amp=0.5, h=0.4, phase=rng.uniform(0, 6))
    br.append(trunk)
    if P.get('broken_top'):
        # jagged snapped top: two splinters
        p, tan, r, g = trunk.at(1.0)
        trunk.tip = 'flat'
        for k in range(2):
            d = child_dir(tan, rng.uniform(8, 22), rng.uniform(0, 360))
            b = grow(rng, trunk.at(0.93)[0] + child_dir(tan, 90, 180 * k + 40) * r * 0.45, d, rng.uniform(0.5, 1.1), 2,
                     r * 0.55, 0.01, gnarl=0.1, g0=g, g1=g, phase=0.5, level=1, parent=trunk)
            b.sides = 4
            br.append(b)
    add_roots(br, rng, P['r0'], n=P.get('roots', 5), spread=2.8, z0=0.45)
    az = rng.uniform(0, 360)
    n1 = P['n1']
    for k in range(n1):
        t = P['t1'][0] + (P['t1'][1] - P['t1'][0]) * (k + rng.uniform(0.2, 0.8)) / n1
        p, tan, r, g = trunk.at(t)
        az += 137.5 + rng.uniform(-35, 35)
        d = child_dir(tan, rng.uniform(*P['angle1']), az)
        L = rng.uniform(*P['len1']) * (1.0 - 0.35 * max(0.0, t - 0.6))
        broken = rng.rand() < P.get('broken', 0.2)
        if broken:
            L *= 0.45
        b1 = grow(rng, p, d, L, 6 if not broken else 3, max(0.035, r * rng.uniform(0.42, 0.58)),
                  0.014 if not broken else max(0.03, r * 0.3), gnarl=P['gnarl'],
                  trop=lambda t_, d_, q: (0, 0, P['trop']), taper=0.85, g0=g, g1=g + 0.14, phase=rng.rand(), level=1,
                  parent=trunk)
        if broken:
            b1.tip = 'flat'
        br.append(b1)
        if broken:
            continue
        n2 = P['n2'] + (rng.rand() < 0.5)
        sd = rng.choice([0, 180])
        for j in range(n2):
            t2 = 0.3 + 0.62 * (j + rng.uniform(0.2, 0.8)) / n2
            p2, tan2, r2, g2 = b1.at(t2)
            sd = 180 - sd
            d2 = child_dir(tan2, rng.uniform(35, 70), sd + rng.uniform(-60, 60))
            L2 = L * rng.uniform(0.28, 0.5) * (1.1 - 0.4 * t2)
            b2 = grow(rng, p2, d2, L2, 4, max(0.018, r2 * 0.6), 0.008, gnarl=P['gnarl'] * 1.3,
                      trop=lambda t_, d_, q: (0, 0, P['trop'] * 0.5), g0=g2, g1=g2 + 0.12, phase=b1.phase, level=2,
                      parent=b1)
            b2.sides = 4 if b2.rad[0] > 0.03 else 3
            br.append(b2)
            n3 = P['n3'] + (rng.rand() < 0.4)
            for m in range(n3):
                t3 = 0.35 + 0.6 * (m + rng.uniform(0.2, 0.8)) / max(n3, 1)
                p3, tan3, r3, g3 = b2.at(t3)
                d3 = child_dir(tan3, rng.uniform(35, 70), rng.uniform(0, 360))
                b3 = grow(rng, p3, d3, rng.uniform(0.3, 0.75), 2, max(0.01, r3 * 0.6), 0.004, gnarl=0.35,
                          g0=g3, g1=g3 + 0.1, phase=b1.phase, level=3, parent=b2)
                b3.sides = 3
                b3.keep_lod1 = P.get('lod1_l3', False) and (m == 0)
                br.append(b3)
    return dict(name=name, rng=rng, branches=br, trunk=trunk, bark=P['bark'], P=P)


def assemble_dead(T):
    rng = T['rng']
    P = T['P']
    mats = [nat_mat(T['bark'])]
    obs, mbs = [], []
    for lod in (0, 1):
        mb = MB()
        if lod == 0:
            skin(mb, T['branches'], rng, lod=0)
        else:
            wood = lod1_wood(T, rng, trunk_segs=5, limb_segs=3, twig_min=0.0, trunk_sides=5, twig_segs=2)
            skin(mb, wood, rng, lod=1)
        finish_tree(mb)
        # charring / weathering: darken R with a blotchy pattern, stronger toward the ends
        Pp = mb.pos
        burn = np.array([mnoise.noise(Vector((p[0] * 0.9, p[1] * 0.9, p[2] * 0.55))) for p in Pp]) * 0.5 + 0.5
        dark = P['dark'][0] + (P['dark'][1] - P['dark'][0]) * np.clip(burn * 1.3 - 0.15, 0, 1)
        mb.col[:, 0] = np.clip(mb.col[:, 0] * dark, 0, 1)
        ob = mb.build(T['name'] + '_LOD%d' % lod, mats)
        obs.append(ob)
        mbs.append(mb)
    return obs[0], obs[1], mbs[0], mbs[1]


DEAD_A = dict(height=6.6, r0=0.34, r_top=0.035, lean=(0.16, -0.06), trunk_gnarl=0.17, n1=10, t1=(0.30, 0.95),
              angle1=(38, 78), len1=(2.0, 3.4), gnarl=0.34, trop=0.05, n2=3, n3=2, broken=0.15, dark=(0.42, 0.78),
              bark='M_bark_oak', lod1_l3=False)
DEAD_B = dict(height=6.4, r0=0.40, r_top=0.20, lean=(-0.05, 0.08), trunk_gnarl=0.08, n1=8, t1=(0.36, 0.96),
              angle1=(48, 85), len1=(1.8, 2.8), gnarl=0.26, trop=-0.03, n2=2, n3=2, broken=0.45, dark=(0.22, 0.52),
              bark='M_bark_pine', broken_top=True, roots=4)


# ----------------------------------------------------------------------------- export
def trunk_radius_at(trunk, z=1.3):
    return float(np.interp(z, trunk.pts[:, 2], trunk.rad))


def export_tree(T, ob0, ob1, mb0, mb1, desc, extra=None):
    name = T['name']
    r_chest = trunk_radius_at(T['trunk']) * 1.05
    meta = dict(description=desc, collider={'type': 'cylinder', 'radius': round(r_chest, 3)},
                cards_lod0=len(mb0.cards), cards_lod1=len(mb1.cards))
    if extra:
        meta.update(extra)
    ob0['valombre'] = json.dumps(meta)
    path = os.path.join(NATURE, name + '.glb')
    export_glb(path, [ob0, ob1])
    st = glb_mesh_stats(path)
    for k, v in st.items():
        print('STATS', k, 'tris', v['tris'], v['tris_by_material'], 'size', v['size'], 'min', v['min'], 'max', v['max'])
    check_leaf_normals(path, name)
    return path


BUILDERS = {}


def tree(name):
    def deco(fn):
        BUILDERS[name] = fn
        return fn
    return deco


@tree('oak_a')
def _oak_a():
    T = build_oak('oak_a', 101, OAK_A)
    return T, assemble_broadleaf(T), 'broad old oak, thick gnarled trunk, big spreading limbs'


@tree('oak_b')
def _oak_b():
    T = build_oak('oak_b', 207, OAK_B)
    return T, assemble_broadleaf(T), 'very old squat oak, wide crown, heavy low limbs'


@tree('pine_a')
def _pine_a():
    T = build_pine('pine_a', 311, PINE_A)
    return T, assemble_pine(T), 'tall full conifer, layered drooping branch tiers'


@tree('pine_b')
def _pine_b():
    T = build_pine('pine_b', 419, PINE_B)
    return T, assemble_pine(T), 'old sparse conifer, long bare trunk with dead stubs, irregular crown'


@tree('birch_a')
def _birch_a():
    T = build_birch('birch_a', 523, BIRCH_A)
    return T, assemble_broadleaf(T, droop=0.3, roll_jit=70.0, lod1_S=(2.0, 3.2), lod1_twigs=0.03, ao_lo=0.45,
                                 big=1.35, lod1_up=0.3, lod1_out=0.5, kappa=0.3, lod1_limb_segs=5), \
        'slender birch, white bark, light airy crown with hanging twigs'


@tree('willow_a')
def _willow_a():
    T = build_willow('willow_a', 631, WILLOW_A)
    return T, assemble_willow(T), 'swamp willow, leaning trunk, long drooping curtains'


@tree('dead_a')
def _dead_a():
    T = build_dead('dead_a', 733, DEAD_A)
    return T, assemble_dead(T), 'dead twisted tree, bare claw-like branches (swamp)'


@tree('dead_b')
def _dead_b():
    T = build_dead('dead_b', 839, DEAD_B)
    return T, assemble_dead(T), 'burnt snag, snapped top and broken limbs (ash lands)'


def main():
    global RECTS
    only = cli_only()
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        reset_scene()
        RECTS = atlas_rects()
        T, (ob0, ob1, mb0, mb1), desc = fn()
        print('TREE', name, 'LOD0 tris', mb0.tri_count(), 'cards', len(mb0.cards), '| LOD1 tris', mb1.tri_count(),
              'cards', len(mb1.cards))
        export_tree(T, ob0, ob1, mb0, mb1, desc)
        preview_materials()
        nat_sheet(os.path.join(PREVIEWS, 'nat_%s.png' % name), [[ob0], [ob1]],
                  views=('front', 'left', 'persp', 'low'), res=448, same_bounds=True)


main()
