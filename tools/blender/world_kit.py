"""VALOMBRE - world pack (citadel, ruins, sacred sites, biome set dressing): toolkit built on arch_kit.

Adds what the village kit does not have:
  * masonry(): thick stone wall with a (broken) top profile, pointed / flat / open-topped openings, jambs,
    soffits, exposed rubble core on the breaks, optional battered base
  * ring_wall() / cone_roof(): round towers with a jagged top, (broken) conical roofs with rafters
  * rock(), rubble(), shard() (crystal / ice / obsidian), menhir(), Panel + rune glyph strokes, vine()
  * weather(): noise tint + moss weights on every stone surface (run automatically before the AO bake)
  * wbuild(): export + contact sheet tools/previews/world_<asset>.png

Coordinates: Blender Z up, front = -Y, origin = centre of the footprint on the ground.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *
import arch_kit as AK
from blcommon import _bounds

AK.PREV.update({
    'M_ice': ('#a9d8f2', 0.12, 0.0, 0), 'M_obsidian': ('#211f27', 0.16, 0.0, 0),
    'M_bark_birch': ('#c9c2b4', 0.9, 0, 0), 'M_hide': ('#ffffff', 0.8, 0, 0),
})

SB, SW, RK, CB = 'M_stone_brick', 'M_stone_wall', 'M_rock', 'M_cobble'
WD, IR, CL = 'M_wood_planks', 'M_metal_iron', 'M_cloth'
STONE_MATS = (SB, SW, RK, CB)
ST = PAL['stone']
ST_D = mulc(ST, 0.84)
ST_L = mulc(ST, 1.05)
CORE = mulc(L('#d9d1c2'), 0.78)          # exposed rubble core of a broken wall
ROCK = L('#e8e5df')
DARK = (0.012, 0.012, 0.014)
CRY0, CRY1 = L('#4fc3e6'), L('#f2ffff')    # crystal: base -> tip
ICE0, ICE1 = L('#b9def5'), L('#ffffff')
OBS = L('#e9e6f0')
RUNE_E = L('#ffb057')                    # ember order runes
RUNE_C = L('#9fe9ff')                    # old Aubeclair / Astre runes
RUNE_V = L('#b76bff')                    # corruption
EMB = PAL['ember']
EMB_H = L('#ffc25a')
CHAR = L('#3b332d')                      # charred timber (multiplies M_wood_planks)
RUST = L('#6a4630')
BONE = L('#d9cfb6')
GOLD = L('#d9a441')
GOLD_D = L('#9c7a34')
BRASS = L('#b8923f')
SLATE = (0.30, 0.56, 0.84)
ZC = [0.0, 0.9, 2.4, 4.4, 6.6, 9.0, 11.5, 14.0, 16.5]


def prep_mats():
    """Preview materials whose emission follows the vertex colour (rune / crystal / ember tints)."""
    for name, strength, rough in (('M_rune_glow', 3.0, 0.5), ('M_crystal', 1.6, 0.15), ('M_ember', 4.0, 0.6),
                                  ('M_window_glow', 1.6, 0.4)):
        m = make_mat(name, (1, 1, 1), rough, 0.0, emissive=(1, 1, 1), emissive_strength=strength,
                     use_vertex_color=True)
        nt = m.node_tree
        vc = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeVertexColor'][0]
        bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Emission Color'])
        m.use_backface_culling = True


# ----------------------------------------------------------------------------- weathering pass
def weather(k, top=0.45, base=0.6, base_h=1.5, tint=0.12, streak=0.1, mats=STONE_MATS, freq=0.55, wood=0.06,
            damp=0.16, moss_col=(0.55, 0.76, 0.36)):
    """Noise tint + rain streaks + damp base + moss (tops and near the ground) on stone. Called before bake()."""
    bm = k.bm
    bm.normal_update()
    idx = set(k.mats.index(m) for m in mats if m in k.mats)
    widx = set(k.mats.index(m) for m in (WD, 'M_bark_oak', 'M_bark_pine', 'M_thatch') if m in k.mats)
    cl, fl = k.cl, k.fl
    o = V((5.3, 1.1, 2.7))
    o2 = V((11.9, 4.2, 7.7))
    for f in bm.faces:
        if f[fl] & NOAO:
            continue
        mi = f.material_index
        if mi in idx:
            n = f.normal
            up = clamp(n.z) ** 1.5
            side = 1.0 - abs(n.z)
            for l in f.loops:
                p = l.vert.co
                a = mnoise.noise(p * freq + o)
                b = mnoise.noise(V((p.x * 2.1, p.y * 2.1, p.z * 0.38)) + o)
                g = 1.0 - sstep(0.0, base_h, p.z)
                m = (1.0 + tint * a - streak * max(0.0, b) * side) * (1.0 - damp * g)
                c = l[cl]
                r, gg, bb = c[0] * m, c[1] * m * (1.0 + 0.012 * a), c[2] * m * (1.0 - 0.02 * a)
                nz = mnoise.noise(p * 0.8 + o2) * 0.5 + 0.5
                mw = clamp(base * g * (0.2 + 1.4 * nz) + top * up * (0.3 + 1.1 * nz))
                l[cl] = (r * lerp(1.0, moss_col[0], mw), gg * lerp(1.0, moss_col[1], mw),
                         bb * lerp(1.0, moss_col[2], mw), 1.0)
        elif mi in widx and wood:
            for l in f.loops:
                p = l.vert.co
                m = 1.0 + wood * mnoise.noise(p * 0.9 + o)
                c = l[cl]
                l[cl] = (c[0] * m, c[1] * m, c[2] * m, 1.0)


# ----------------------------------------------------------------------------- small geometry helpers
def dedupe(pts, eps=1e-5):
    out = []
    for p in pts:
        p = V(p)
        if not out or (p - out[-1]).length > eps:
            out.append(p)
    if len(out) > 1 and (out[0] - out[-1]).length <= eps:
        out.pop()
    return out


def block(k, c, s, rz=0.0, rx=0.0, ry=0.0, mat=SB, col=None, skip=(), taper=(1.0, 1.0), **kw):
    """Loose stone block / plank: box centred on c with its own rotation."""
    with k.at(c, rz=rz, rx=rx, ry=ry):
        k.cbox((0, 0, 0), s, mat, col or k.jit(ST, 0.07, 0.01), skip=skip, taper=taper, **kw)


def rock(k, c, rad, seed=0.0, nu=8, nv=4, mat=RK, col=None, rough=0.26, zmin=-0.45, smooth=True, freq=None,
         rz=0.0, flag=0, lean=(0.0, 0.0)):
    """Noise-deformed boulder (ellipsoid radii rad). zmin cuts the bottom (-1..1)."""
    col = col or ROCK
    c = V(c)
    o = V((seed * 5.13 + 1.7, seed * 2.71 + 4.1, seed * 9.37 + 0.3))
    fr = freq or 1.25 / max(rad)
    cz, sz = math.cos(rz), math.sin(rz)

    def deform(p):
        d = p - c
        n1 = mnoise.noise(d * fr + o)
        n2 = mnoise.noise(d * fr * 2.4 + o * 1.7)
        s = 1.0 + rough * (n1 + 0.45 * n2)
        x, y, z = d.x * s, d.y * s, d.z * (1.0 + rough * 0.7 * n2)
        x += lean[0] * z
        y += lean[1] * z
        return c + V((x * cz - y * sz, x * sz + y * cz, z))
    k.blob(c, rad, nu=nu, nv=nv, mat=mat, col=col, deform=deform, zmin=zmin, smooth=smooth, flag=flag)


def rubble(k, c, rad, h, blocks=7, seed=1, heap=True, mat=SW, bmat=SB, col=None, bs=(0.32, 0.7), nu=8, nv=3,
           spread=1.0):
    """Heap of rubble (deformed mound) with loose ashlar blocks half buried in it."""
    rng = random.Random(seed * 7919 + 13)
    c = V(c)
    col = col or mulc(CORE, 1.08)
    if heap:
        rock(k, (c.x, c.y, c.z - 0.12), (rad[0], rad[1], h + 0.12), seed=seed, nu=nu, nv=nv, mat=mat, col=col,
             rough=0.3, zmin=0.0, freq=1.6 / max(rad))
    for i in range(blocks):
        a = rng.uniform(0, 2 * PI)
        d = math.sqrt(rng.uniform(0.02, 1.0)) * spread
        x, y = c.x + math.cos(a) * rad[0] * d, c.y + math.sin(a) * rad[1] * d
        z = c.z + (h * max(0.0, 1.0 - d * d) * 0.85 if heap else 0.0)
        s = (rng.uniform(*bs), rng.uniform(bs[0] * 0.7, bs[1] * 0.7), rng.uniform(bs[0] * 0.55, bs[1] * 0.5))
        block(k, (x, y, z + s[2] * 0.28), s, rz=rng.uniform(0, PI), rx=rng.uniform(-0.45, 0.45),
              ry=rng.uniform(-0.45, 0.45), mat=bmat, col=k.jit(mulc(ST, 0.93), 0.08, 0.01))


def shard(k, p0, axis, length, r, n=6, tipf=0.3, col0=None, col1=None, mat='M_crystal', phase=0.0, slant=0.12,
          tip_off=0.25, seg=1, rtop=0.8, flag=0, jit=0.0, seed=0, smooth=False, base_cap=False, bend=(0.0, 0.0)):
    """Faceted prism with an off-centre pointed tip (crystal, ice, obsidian). p0 = base centre, axis = direction."""
    col0 = col0 or CRY0
    col1 = col1 or CRY1
    p0, d = V(p0), V(axis).normalized()
    ref = V((0, 0, 1)) if abs(d.z) < 0.9 else V((1, 0, 0))
    s = ref.cross(d).normalized()
    u = d.cross(s)
    rng = random.Random(seed * 131 + 7)
    body = length * (1.0 - tipf)
    rings = []
    for j in range(seg + 1):
        t = j / seg
        rr = lerp(r, r * rtop, t)
        ring = []
        for i in range(n):
            a = phase + 2 * PI * i / n
            rj = rr * (1.0 + (rng.uniform(-jit, jit) if jit else 0.0))
            h = body * t + (slant * length * math.cos(a - phase - 0.6) if j == seg else 0.0)
            off = s * bend[0] * (t * t) * length + u * bend[1] * (t * t) * length
            ring.append(p0 + off + (s * math.cos(a) + u * math.sin(a)) * rj + d * h)
        rings.append(ring)
    apex = p0 + d * length + (s * math.cos(phase + 0.6) + u * math.sin(phase + 0.6)) * (r * rtop * tip_off) \
        + s * bend[0] * length + u * bend[1] * length
    vr = [[k.v(p) for p in ring] for ring in rings]
    va = k.v(apex)
    cols = [mixc(col0, col1, (j / seg) * 0.55) for j in range(seg + 1)]
    for j in range(seg):
        for i in range(n):
            i2 = (i + 1) % n
            q = [vr[j][i], vr[j][i2], vr[j + 1][i2], vr[j + 1][i]]
            cm = {q[0]: cols[j], q[1]: cols[j], q[2]: cols[j + 1], q[3]: cols[j + 1]}
            k.f(q, mat, cm, smooth=smooth, flag=flag)
    for i in range(n):
        i2 = (i + 1) % n
        q = [vr[seg][i], vr[seg][i2], va]
        k.f(q, mat, {q[0]: cols[seg], q[1]: cols[seg], q[2]: col1}, smooth=smooth, flag=flag)
    if base_cap:
        k.f(list(reversed(vr[0])), mat, col0, flag=flag)
    return rings, apex


# ----------------------------------------------------------------------------- arches
def arch_z(x, hw, hs, ha):
    """height of a pointed (two-centred) arch at offset x from its axis. ha = apex, hs = springing."""
    r = ha - hs
    if r < 1e-4:
        return hs
    c = (r * r - hw * hw) / (2 * hw)
    R = c + hw
    return hs + math.sqrt(max(0.0, R * R - (abs(x) + c) ** 2))


def arch_xs(hw, hs, ha, n):
    """x offsets (negative, from the springing towards the axis, ends excluded) uniform along the arc."""
    r = ha - hs
    if r < 1e-4 or n < 2:
        return []
    c = (r * r - hw * hw) / (2 * hw)
    R = c + hw
    tha = math.atan2(r, -c)
    return [c + R * math.cos(PI + (tha - PI) * i / n) for i in range(1, n)]


class Op:
    """Opening in a masonry wall. s = centre along the wall, w = width, z0 = bottom, hs = springing height,
    ha = apex height (hs == ha: flat lintel, None: open to the sky = crenel / collapsed head)."""

    def __init__(self, s, w, z0, hs, ha=None, n=3):
        self.s, self.w, self.z0, self.hs, self.ha, self.n = s, w, z0, hs, ha, n
        self.s0, self.s1 = s - w / 2, s + w / 2

    def arch(self, s):
        if self.ha is None:
            return 1e9
        return arch_z(s - self.s, self.w / 2, self.hs, self.ha)

    def stations(self):
        out = [self.s0, self.s1]
        if self.ha is not None and self.ha - self.hs > 1e-3:
            xs = arch_xs(self.w / 2, self.hs, self.ha, self.n)
            out += [self.s + x for x in xs] + [self.s] + [self.s - x for x in xs]
        return out

    def outline(self, zb=None):
        """(s, z) polyline: left jamb bottom -> over the head -> right jamb bottom."""
        zb = self.z0 if zb is None else zb
        path = [(self.s0, zb), (self.s0, self.hs)]
        if self.ha is not None and self.ha - self.hs > 1e-3:
            xs = arch_xs(self.w / 2, self.hs, self.ha, self.n)
            path += [(self.s + x, self.arch(self.s + x)) for x in xs]
            path.append((self.s, self.ha))
            path += [(self.s - x, self.arch(self.s - x)) for x in reversed(xs)]
        path += [(self.s1, self.hs), (self.s1, zb)]
        return path


def _tops(zt, Lw):
    if isinstance(zt, (int, float)):
        kn = [(0.0, float(zt)), (Lw, float(zt))]
    else:
        kn = [(float(s), float(z)) for s, z in zt]
        if kn[0][0] > 1e-6:
            kn.insert(0, (0.0, kn[0][1]))
        if kn[-1][0] < Lw - 1e-6:
            kn.append((Lw, kn[-1][1]))
    n = len(kn)

    def ev(s, right):
        eps = 1e-6
        if right:
            i = max([j for j in range(n) if kn[j][0] <= s + eps] or [0])
            if i == n - 1:
                return kn[i][1]
            a, b = kn[i], kn[i + 1]
        else:
            i = min([j for j in range(n) if kn[j][0] >= s - eps] or [n - 1])
            if i == 0:
                return kn[0][1]
            a, b = kn[i - 1], kn[i]
        if b[0] - a[0] < eps:
            return b[1] if right else a[1]
        return a[1] + (b[1] - a[1]) * clamp((s - a[0]) / (b[0] - a[0]))
    return (lambda s: ev(s, False)), (lambda s: ev(s, True)), kn


def _isub(A, B):
    out = []
    for (a0, a1) in A:
        segs = [(a0, a1)]
        for (b0, b1) in B:
            ns = []
            for (x0, x1) in segs:
                if b1 <= x0 + 1e-4 or b0 >= x1 - 1e-4:
                    ns.append((x0, x1))
                else:
                    if b0 > x0 + 1e-4:
                        ns.append((x0, b0))
                    if b1 < x1 - 1e-4:
                        ns.append((b1, x1))
            segs = ns
        out += segs
    return [(x0, x1) for (x0, x1) in out if x1 - x0 > 0.03]


def masonry(k, a, b, z0, zt, th, ops=(), mat=SB, col=None, core=SW, core_col=None, ds=2.0, zc=None,
            ends=(True, True), end_core=(False, False), inner=True, outer=True, top_core=None, batter=None, tsub=1,
            inner_mat=None, inner_col=None, cuts=(), top=True):
    """Thick wall from 2D point a to b (exterior on the RIGHT when walking a -> b), from z0 up to the top
    profile zt (number, or [(s, z), ...] knots; repeat an s for a vertical step). th = thickness (towards the
    interior). ops = [Op, ...]. Broken tops / steps show the rubble core. batter = (amount, height).
    Returns the Wall (outer face)."""
    w = Wall(a, b, z0, z0)
    Lw = w.L
    zL, zR, kn = _tops(zt, Lw)
    col = col or ST
    core_col = core_col or CORE
    imat = inner_mat or mat
    icol = inner_col or (mulc(col, 0.93) if not callable(col) else col)
    zc = list(ZC if zc is None else zc)
    if batter:
        zc = sorted(set(zc + [batter[1]]))
    if top_core is None:
        top_core = not isinstance(zt, (int, float))
    S = [0.0, Lw] + [s for s, z in kn] + list(cuts)
    for o in ops:
        S += o.stations()
    n = max(1, int(math.ceil(Lw / ds - 1e-6)))
    reg = [Lw * i / n for i in range(1, n)]
    S = sorted(clamp(s, 0.0, Lw) for s in S)
    out = []
    for s in S:
        if not out or s - out[-1] > 1e-4:
            out.append(s)
    for s in reg:
        if all(abs(s - x) > 0.3 for x in out):
            out.append(s)
    S = sorted(out)

    def fo(z):
        if not batter:
            return 0.0
        return batter[0] * clamp((batter[1] - z) / (batter[1] - z0)) if z < batter[1] else 0.0

    def pt(s, z, t):
        return w.P(s, z, lerp(fo(z), -th, t))

    def tq(sa, za, sb, zb, nh, m, c):
        for i in range(tsub):
            t0, t1 = i / tsub, (i + 1) / tsub
            pts = dedupe([pt(sa, za, t0), pt(sb, zb, t0), pt(sb, zb, t1), pt(sa, za, t1)])
            if len(pts) >= 3:
                k.quad(pts, m, c, nh=nh)

    cols = []
    for i in range(len(S) - 1):
        sa, sb = S[i], S[i + 1]
        sm = (sa + sb) / 2
        op = None
        for o in ops:
            if o.s0 - 1e-6 <= sm <= o.s1 + 1e-6:
                op = o
        ta, tb = zR(sa), zL(sb)
        slabs = []
        if op is None:
            if max(ta, tb) > z0 + 0.02:
                slabs.append(((z0, z0), (max(ta, z0), max(tb, z0)), 'base', 'top'))
        else:
            if op.z0 > z0 + 1e-3:
                ha_, hb_ = min(op.z0, ta), min(op.z0, tb)
                kind = 'sill' if (ta >= op.z0 - 1e-4 and tb >= op.z0 - 1e-4) else 'top'
                if max(ha_, hb_) > z0 + 0.02:
                    slabs.append(((z0, z0), (max(ha_, z0), max(hb_, z0)), 'base', kind))
            if op.ha is not None:
                aa, ab = op.arch(sa), op.arch(sb)
                if ta > aa + 0.03 or tb > ab + 0.03:
                    slabs.append(((aa, ab), (max(ta, aa), max(tb, ab)), 'arch', 'top'))
        cols.append((sa, sb, slabs, op))
        for (lo, hi, klo, khi) in slabs:
            cz = [z for z in zc if max(lo) + 0.3 < z < min(hi) - 0.3]
            rows = [lo] + [(z, z) for z in cz] + [hi]
            for r0, r1 in zip(rows[:-1], rows[1:]):
                if outer:
                    pts = dedupe([pt(sa, r0[0], 0), pt(sb, r0[1], 0), pt(sb, r1[1], 0), pt(sa, r1[0], 0)])
                    if len(pts) >= 3:
                        k.quad(pts, mat, col, nh=w.n)
                if inner:
                    pts = dedupe([pt(sa, r0[0], 1), pt(sb, r0[1], 1), pt(sb, r1[1], 1), pt(sa, r1[0], 1)])
                    if len(pts) >= 3:
                        k.quad(pts, imat, icol, nh=-w.n)
            if top and khi in ('top', 'sill'):
                tc = (khi == 'top') and (top_core(sm) if callable(top_core) else top_core)
                tq(sa, hi[0], sb, hi[1], (0, 0, 1), core if tc else mat, core_col if tc else col)
            if klo == 'arch':
                hint = w.P(op.s, (op.z0 + op.hs) / 2, -th / 2) - w.P(sm, (lo[0] + lo[1]) / 2, -th / 2)
                tq(sa, lo[0], sb, lo[1], hint, mat, mulc(col, 0.95) if not callable(col) else col)
    for j, s in enumerate(S):
        if (j == 0 and not ends[0]) or (j == len(S) - 1 and not ends[1]):
            continue
        Lf = [(sl[0][1], sl[1][1]) for sl in cols[j - 1][2]] if j > 0 else []
        Rt = [(sl[0][0], sl[1][0]) for sl in cols[j][2]] if j < len(cols) else []
        Lf = [(x0, x1) for x0, x1 in Lf if x1 - x0 > 0.02]
        Rt = [(x0, x1) for x0, x1 in Rt if x1 - x0 > 0.02]
        edge = any(abs(s - o.s0) < 1e-4 or abs(s - o.s1) < 1e-4 for o in ops)
        if j == 0:
            usecore = end_core[0]
        elif j == len(S) - 1:
            usecore = end_core[1]
        else:
            usecore = not edge
        for sg, segs in ((1, _isub(Lf, Rt)), (-1, _isub(Rt, Lf))):
            for (x0, x1) in segs:
                zs = [x0] + [z for z in zc if x0 + 0.3 < z < x1 - 0.3] + [x1]
                for za, zb in zip(zs[:-1], zs[1:]):
                    for i in range(tsub):
                        t0, t1 = i / tsub, (i + 1) / tsub
                        k.quad([pt(s, za, t0), pt(s, zb, t0), pt(s, zb, t1), pt(s, za, t1)],
                               core if usecore else mat, core_col if usecore else col, nh=w.d * sg)
    return w


def archivolt(k, w, op, band=0.22, proud=0.06, mat=SB, col=None, side=1, th=0.0, zb=None, jambs=True, sill=0.0):
    """Moulding band around an opening on the outer face (side=1) or on the inner face (side=-1, th = wall
    thickness). sill > 0 adds a projecting sill of that height under the opening."""
    col = col or ST_L
    path = op.outline(zb)
    if not jambs:
        path = path[1:-1]
    base = 0.0 if side > 0 else -th
    n = len(path)
    segn = []
    for i in range(n - 1):
        dx, dz = path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]
        l = math.hypot(dx, dz) or 1.0
        segn.append((-dz / l, dx / l))
    nrm = []
    for i in range(n):
        a = segn[max(i - 1, 0)]
        b = segn[min(i, n - 2)]
        mx, mz = a[0] + b[0], a[1] + b[1]
        l = math.hypot(mx, mz) or 1.0
        mx, mz = mx / l, mz / l
        cosh = max(0.6, mx * a[0] + mz * a[1])
        nrm.append((mx / cosh, mz / cosh))

    def P(i, o, pr):
        s, z = path[i]
        return w.P(s + nrm[i][0] * o, z + nrm[i][1] * o, base + side * pr)
    for i in range(n - 1):
        k.quad([P(i, 0, proud), P(i + 1, 0, proud), P(i + 1, band, proud), P(i, band, proud)], mat, col,
               nh=w.n * side)
        n3 = w.d * segn[i][0] + V((0, 0, segn[i][1]))
        k.quad([P(i, band, proud), P(i + 1, band, proud), P(i + 1, band, 0), P(i, band, 0)], mat, col, nh=n3)
        k.quad([P(i, 0, proud), P(i + 1, 0, proud), P(i + 1, 0, 0), P(i, 0, 0)], mat, mulc(col, 0.9), nh=-n3)
    if sill:
        s0, s1 = op.s0 - band, op.s1 + band
        r0 = [w.P(s0, op.z0 - sill, base), w.P(s1, op.z0 - sill, base), w.P(s1, op.z0, base), w.P(s0, op.z0, base)]
        o = w.n * side * (proud + 0.05)
        k.prism(r0, o, mat, col, caps=(False, True))


def arch_decal(k, w, s, z0, ww, hs, ha, off=0.02, col=DARK, mat=SB, n=3, flag=NOAO):
    """Flat filled pointed-arch shape on a wall face (dark doorway / blind window / glowing pane)."""
    o = Op(s, ww, z0, hs, ha, n)
    pts = [w.P(a, b, off) for a, b in o.outline()]
    return k.quad(pts, mat, col, nh=w.n, flag=flag)


def pier(k, x0, y0, x1, y1, z0, z1, mat=SB, col=None, zc=None, tops=None, top_mat=None, top_col=None,
         batter=None, skip=(), ds=None, top=True):
    """Rectangular masonry pier / turret with horizontal cuts (for AO) and optional jagged top
    (tops = heights of the 4 corners SW, SE, NE, NW)."""
    col = col or ST
    zc = list(ZC if zc is None else zc)
    if batter:
        zc = sorted(set(zc + [batter[1]]))
    tops = tops or (z1, z1, z1, z1)
    cs = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    sg = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    names = ['-y', '+x', '+y', '-x']

    def fo(z):
        if not batter:
            return 0.0
        return batter[0] * clamp((batter[1] - z) / (batter[1] - z0)) if z < batter[1] else 0.0

    def C(i, z):
        o = fo(z)
        return V((cs[i][0] + sg[i][0] * o, cs[i][1] + sg[i][1] * o, z))
    for i in range(4):
        if names[i] in skip:
            continue
        j = (i + 1) % 4
        ln = math.hypot(cs[j][0] - cs[i][0], cs[j][1] - cs[i][1])
        ns = max(1, int(round(ln / ds))) if ds else 1
        lo, hi = (z0, z0), (tops[i], tops[j])
        cz = [z for z in zc if z0 + 0.3 < z < min(hi) - 0.3]
        rows = [lo] + [(z, z) for z in cz] + [hi]
        for r0, r1 in zip(rows[:-1], rows[1:]):
            for q in range(ns):
                f0, f1 = q / ns, (q + 1) / ns
                pa0 = C(i, lerp(r0[0], r0[1], f0)).lerp(C(j, lerp(r0[0], r0[1], f0)), f0)
                pb0 = C(i, lerp(r0[0], r0[1], f1)).lerp(C(j, lerp(r0[0], r0[1], f1)), f1)
                pa1 = C(i, lerp(r1[0], r1[1], f0)).lerp(C(j, lerp(r1[0], r1[1], f0)), f0)
                pb1 = C(i, lerp(r1[0], r1[1], f1)).lerp(C(j, lerp(r1[0], r1[1], f1)), f1)
                k.quad([pa0, pb0, pb1, pa1], mat, col)
    if top and '+z' not in skip:
        k.quad([C(i, tops[i]) for i in range(4)], top_mat or mat, top_col or col, nh=(0, 0, 1))


def crenels(k, a, b, z, h=0.9, th=0.5, mw=1.2, gap=0.8, lead=None, mat=SB, col=None, missing=(), broken=None,
            cap=0.0):
    """Row of merlons standing on the line a -> b (exterior on the right), base at z."""
    w = Wall(a, b, z, z)
    lead = gap / 2 if lead is None else lead
    col = col or ST
    broken = broken or {}
    s = lead
    i = 0
    while s + mw <= w.L + 1e-6:
        if i not in missing:
            hh = h * broken.get(i, 1.0)
            r0 = [w.P(s, z, 0), w.P(s + mw, z, 0), w.P(s + mw, z, -th), w.P(s, z, -th)]
            if i in broken:
                r1 = [p + V((0, 0, hh * k.r(0.7, 1.15))) for p in r0]
                k.loft(r0, r1, mat, col, caps=(False, True), cap_mat=SW, cap_col=CORE)
            else:
                r1 = [p + V((0, 0, hh)) for p in r0]
                k.loft(r0, r1, mat, col, caps=(False, True))
                if cap:
                    c0 = [w.P(s - cap, z + hh, cap), w.P(s + mw + cap, z + hh, cap), w.P(s + mw + cap, z + hh, -th - cap),
                          w.P(s - cap, z + hh, -th - cap)]
                    k.loft(c0, [p + V((0, 0, 0.1)) for p in c0], mat, mulc(col, 1.03))
        s += mw + gap
        i += 1
    return i


def slit(k, w, s, z, h=1.3, ww=0.13, frame=0.15, proud=0.05, cross=False, off=0.0, col=None, mat=SB):
    """Arrow slit: dark slot with a proud stone surround (wall is NOT pierced)."""
    col = col or ST_L
    s0, s1 = s - ww / 2, s + ww / 2
    k.quad([w.P(s0, z, off + 0.015), w.P(s1, z, off + 0.015), w.P(s1, z + h, off + 0.015), w.P(s0, z + h, off + 0.015)],
           mat, DARK, flag=NOAO)
    if cross:
        zm = z + h * 0.62
        k.quad([w.P(s - ww * 2.2, zm - ww / 2, off + 0.016), w.P(s + ww * 2.2, zm - ww / 2, off + 0.016),
                w.P(s + ww * 2.2, zm + ww / 2, off + 0.016), w.P(s - ww * 2.2, zm + ww / 2, off + 0.016)],
               mat, DARK, flag=NOAO)
    if frame:
        for sa in (s0 - frame / 2, s1 + frame / 2):
            wbeam(k, w, sa, z - frame * 0.5, sa, z + h + frame * 0.5, frame, off + proud, depth=proud + 0.02,
                  col=col, mat=mat, caps=(True, True))
        wbeam(k, w, s0, z + h + frame * 0.3, s1, z + h + frame * 0.3, frame * 0.6, off + proud,
              depth=proud + 0.02, col=col, mat=mat, sides=False)
        wbeam(k, w, s0, z - frame * 0.3, s1, z - frame * 0.3, frame * 0.6, off + proud, depth=proud + 0.02,
              col=col, mat=mat, sides=False)


def proud_stones(k, w, n, z0, z1, s0=0.2, s1=None, off=0.0, mat=SB, depth=0.05, seed=1, dark=0.3):
    """A few ashlar blocks standing slightly proud of a wall face + some dark holes of missing stones."""
    rng = random.Random(seed * 101 + 9)
    s1 = w.L - 0.2 if s1 is None else s1
    for i in range(n):
        sl, sh = rng.uniform(0.45, 0.8), rng.uniform(0.26, 0.36)
        s = rng.uniform(s0, max(s0 + 0.01, s1 - sl))
        t = rng.uniform(z0, z1 - sh)
        if rng.random() < dark:
            k.quad([w.P(s, t, off + 0.012), w.P(s + sl * 0.7, t, off + 0.012), w.P(s + sl * 0.7, t + sh, off + 0.012),
                    w.P(s, t + sh, off + 0.012)], mat, mulc(ST, 0.22), flag=NOAO, nh=w.n)
        else:
            p = w.P(s + sl / 2, t + sh / 2, off)
            k.beam(p - w.d * sl / 2, p + w.d * sl / 2, sh, depth * 2, mat, k.jit(mulc(ST, 0.97), 0.07, 0.01), up=w.n,
                   skip=('-u',), uv='box')


def tangent_wall(r, half=1.0):
    """Wall plane tangent to a cylinder of radius r at local -Y (use inside k.at(c, rz=angle + pi/2))."""
    return Wall((-half, -r), (half, -r), 0.0, 0.0)


# ----------------------------------------------------------------------------- round towers
def ring_wall(k, c, n, prof, th=None, zt=None, zin=None, mat=SB, col=None, core=SW, core_col=None, phase=0.0,
              split=(), inner_col=None, door=None, top_core=True, smooth=True, inner_mat=None):
    """Round wall. prof = [(r, z), ...] outer profile, bottom -> top. zt = per-vertex top heights (len n) for
    a broken top. th = thickness (None: only the outer skin). zin = level where the inner face starts.
    door = (sector index, height): sector left open from the bottom up to that height (must be a prof z)."""
    c = V(c)
    col = col or ST
    core_col = core_col or CORE
    K = len(prof)
    rmax = max(r for r, z in prof)
    ztop = prof[-1][1]

    def r_at(z):
        if z <= prof[0][1]:
            return prof[0][0]
        for (r0, za), (r1, zb) in zip(prof[:-1], prof[1:]):
            if z <= zb + 1e-9:
                if zb - za < 1e-9:
                    return r1
                return lerp(r0, r1, (z - za) / (zb - za))
        return prof[-1][0]
    tops = [min(ztop, zt[j]) if zt is not None else ztop for j in range(n)]
    ang = [phase + 2 * PI * j / n for j in range(n + 1)]

    def P(j, r, z):
        return c + V((math.cos(ang[j]) * r, math.sin(ang[j]) * r, z))

    def columns(pr, dr):
        out = []
        for j in range(n):
            colv = []
            tv = None
            for kk, (r, z) in enumerate(pr):
                if z >= tops[j] - 0.02:
                    if tv is None:
                        tv = k.v(P(j, r_at(tops[j]) + dr, tops[j]))
                    colv.append((tv, tv))
                else:
                    a = k.v(P(j, r + dr, z))
                    b = k.v(P(j, r + dr, z)) if kk in split else a
                    colv.append((a, b))
            out.append(colv)
        return out
    vo = columns(prof, 0.0)
    dj, dz = door if door else (None, None)
    for j in range(n):
        j2 = (j + 1) % n
        u0, u1 = rmax * ang[j], rmax * ang[j + 1]
        for b in range(K - 1):
            if j == dj and prof[b + 1][1] <= dz + 1e-6:
                continue
            q = [vo[j][b][1], vo[j2][b][1], vo[j2][b + 1][0], vo[j][b + 1][0]]
            d = {q[0]: (u0, q[0].co.z), q[3]: (u0, q[3].co.z)}
            d[q[1]] = (u1, q[1].co.z)
            d[q[2]] = (u1, q[2].co.z)
            k.f(q, mat, col, uv=d, smooth=smooth)
    if th is None:
        return r_at, tops
    zin = prof[0][1] if zin is None else zin
    ipr = [(r_at(zin), zin)] + [(r, z) for (r, z) in prof if z > zin + 0.05]
    icol = inner_col or (mulc(col, 0.85) if not callable(col) else col)
    vi = columns(ipr, -th)
    for j in range(n):
        j2 = (j + 1) % n
        u0, u1 = rmax * ang[j], rmax * ang[j + 1]
        for b in range(len(ipr) - 1):
            if j == dj and ipr[b + 1][1] <= dz + 1e-6:
                continue
            q = [vi[j2][b][1], vi[j][b][1], vi[j][b + 1][0], vi[j2][b + 1][0]]
            d = {q[0]: (-u1, q[0].co.z), q[3]: (-u1, q[3].co.z)}
            d[q[1]] = (-u0, q[1].co.z)
            d[q[2]] = (-u0, q[2].co.z)
            k.f(q, inner_mat or mat, icol, uv=d, smooth=smooth)
        if tops[j] > zin + 0.02 or tops[j2] > zin + 0.02:
            ro, r2 = r_at(tops[j]), r_at(tops[j2])
            k.quad(dedupe([P(j, ro, tops[j]), P(j + 1, r2, tops[j2]), P(j + 1, r2 - th, tops[j2]),
                           P(j, ro - th, tops[j])]), core if top_core else mat, core_col if top_core else col,
                   nh=(0, 0, 1))
    if door:
        zb = prof[0][1]
        for jj, sgn in ((dj, 1), (dj + 1, -1)):
            t = V((-math.sin(ang[jj]), math.cos(ang[jj]), 0)) * sgn
            k.quad([P(jj, r_at(zb), zb), P(jj, r_at(dz), dz), P(jj, r_at(dz) - th, dz), P(jj, r_at(zb) - th, zb)],
                   mat, mulc(col, 0.95) if not callable(col) else col, nh=t)
        k.quad([P(dj, r_at(dz), dz), P(dj + 1, r_at(dz), dz), P(dj + 1, r_at(dz) - th, dz), P(dj, r_at(dz) - th, dz)],
               mat, mulc(col, 0.9) if not callable(col) else col, nh=(0, 0, -1))
    return r_at, tops


def cone_roof(k, c, r, h, n=12, present=None, tv=0.13, mat='M_roof_tiles', col=None, phase=0.0, rafters=True,
              rcol=None, mid=0.5, under_col=None, moss=0.7, plate=True):
    """Conical roof, eave ring of radius r at c, apex h above. present[i]: 0 = sector gone, 1 = whole,
    2 = only the lower half left. Missing parts show the rafters."""
    c = V(c)
    col = col or SLATE
    rcol = rcol or PAL['beam_d']
    under_col = under_col or mulc(PAL['beam_d'], 0.8)
    present = present or [1] * n
    ang = [phase + 2 * PI * j / n for j in range(n + 1)]
    sl = math.hypot(r, h)

    def P(j, f, dz=0.0):
        rr = r * (1.0 - f)
        return c + V((math.cos(ang[j]) * rr, math.sin(ang[j]) * rr, h * f + dz))
    ve = [k.v(P(j, 0.0)) for j in range(n)]
    vm = [k.v(P(j, mid)) for j in range(n)]
    apex = P(0, 1.0)
    va = k.v(apex)
    for i in range(n):
        if not present[i]:
            continue
        i2 = (i + 1) % n
        u0, u1 = r * ang[i], r * ang[i + 1]
        q = [ve[i], ve[i2], vm[i2], vm[i]]
        k.f(q, mat, col, uv={q[0]: (u0, 0), q[1]: (u1, 0), q[2]: (u1, sl * mid), q[3]: (u0, sl * mid)}, smooth=True,
            moss=moss)
        k.quad([P(i, 0, -tv), P(i, mid, -tv), P(i + 1, mid, -tv), P(i + 1, 0, -tv)], WD, under_col, nh=(0, 0, -1))
        k.quad([P(i, 0, -tv), P(i + 1, 0, -tv), P(i + 1, 0), P(i, 0)], mat, mulc(col, 0.75))
        if present[i] == 1:
            q = [vm[i], vm[i2], va]
            k.f(q, mat, col, uv={q[0]: (u0, sl * mid), q[1]: (u1, sl * mid), q[2]: ((u0 + u1) / 2, sl)}, smooth=True,
                moss=moss * 0.5)
            k.quad([P(i, mid, -tv), apex + V((0, 0, -tv)), P(i + 1, mid, -tv)], WD, under_col, nh=(0, 0, -1))
        else:
            k.quad([P(i, mid, -tv), P(i + 1, mid, -tv), P(i + 1, mid), P(i, mid)], mat, mulc(col, 0.7),
                   nh=P(i, 1.0) - P(i, 0.0))
    for j in range(n):
        pa, pb = present[(j - 1) % n], present[j]
        t = V((-math.sin(ang[j]), math.cos(ang[j]), 0))
        if (pa > 0) != (pb > 0):
            k.quad([P(j, 0), P(j, mid), P(j, mid, -tv), P(j, 0, -tv)], mat, mulc(col, 0.7), nh=t if pa else -t)
        if (pa == 1) != (pb == 1):
            k.quad([P(j, mid), apex, apex + V((0, 0, -tv)), P(j, mid, -tv)], mat, mulc(col, 0.7),
                   nh=t if pa == 1 else -t)
        if rafters and (pa != 1 or pb != 1):
            k.beam(P(j, 0.02, -tv - 0.07), P(j, 0.97, -tv - 0.07), 0.09, 0.12, WD, k.jit(rcol), skip=('c0', 'c1'))
    if rafters and plate and any(p != 1 for p in present):
        k.beam(c + V((0, 0, -tv - 0.3)), apex + V((0, 0, -tv - 0.05)), 0.14, 0.14, WD, k.jit(rcol), skip=('c0',))


# ----------------------------------------------------------------------------- panels, runes
class Panel:
    """Bilinear quad patch: P(u, v, off) with u along p00 -> p10, v along p00 -> p01."""

    def __init__(self, p00, p10, p11, p01):
        self.p = [V(p00), V(p10), V(p11), V(p01)]
        self.n = (self.p[1] - self.p[0]).cross(self.p[3] - self.p[0]).normalized()
        self.wu = ((self.p[1] - self.p[0]).length + (self.p[2] - self.p[3]).length) / 2
        self.wv = ((self.p[3] - self.p[0]).length + (self.p[2] - self.p[1]).length) / 2

    def P(self, u, v, off=0.0):
        a = self.p[0].lerp(self.p[1], u)
        b = self.p[3].lerp(self.p[2], u)
        return a.lerp(b, v) + self.n * off


GLYPHS = {
    'sun': [(0.5, 0.0, 0.5, 1.0), (0.5, 0.78, 0.15, 0.5), (0.15, 0.5, 0.5, 0.22), (0.5, 0.22, 0.85, 0.5),
            (0.85, 0.5, 0.5, 0.78)],
    'ash': [(0.3, 0.0, 0.3, 1.0), (0.3, 1.0, 0.8, 0.7), (0.3, 0.62, 0.8, 0.32)],
    'tyr': [(0.5, 0.0, 0.5, 1.0), (0.5, 1.0, 0.12, 0.62), (0.5, 1.0, 0.88, 0.62)],
    'gate': [(0.2, 0.0, 0.2, 1.0), (0.8, 0.0, 0.8, 1.0), (0.2, 1.0, 0.8, 0.55), (0.2, 0.55, 0.8, 0.1)],
    'ember': [(0.5, 0.0, 0.15, 0.45), (0.15, 0.45, 0.5, 1.0), (0.5, 1.0, 0.85, 0.45), (0.85, 0.45, 0.5, 0.0),
              (0.5, 0.25, 0.5, 0.7)],
    'zig': [(0.2, 1.0, 0.8, 0.68), (0.8, 0.68, 0.2, 0.34), (0.2, 0.34, 0.8, 0.0)],
    'fork': [(0.5, 0.0, 0.5, 0.55), (0.5, 0.55, 0.12, 1.0), (0.5, 0.55, 0.88, 1.0), (0.5, 0.55, 0.5, 1.0)],
    'eye': [(0.1, 0.5, 0.5, 0.85), (0.5, 0.85, 0.9, 0.5), (0.9, 0.5, 0.5, 0.15), (0.5, 0.15, 0.1, 0.5)],
    'bar': [(0.5, 0.0, 0.5, 1.0), (0.15, 0.7, 0.85, 0.7), (0.15, 0.3, 0.85, 0.3)],
    'x': [(0.15, 0.0, 0.85, 1.0), (0.85, 0.0, 0.15, 1.0)],
    'star': [(0.5, 0.0, 0.5, 1.0), (0.1, 0.25, 0.9, 0.75), (0.9, 0.25, 0.1, 0.75)],
    'hook': [(0.3, 0.0, 0.3, 1.0), (0.3, 1.0, 0.8, 0.75), (0.8, 0.75, 0.3, 0.5)],
}
GLYPH_SEQ = ['sun', 'ash', 'tyr', 'gate', 'ember', 'zig', 'fork', 'eye', 'bar', 'star', 'hook', 'x']


def stroke(k, pan, a, b, w=0.035, off=0.022, col=RUNE_C, mat='M_rune_glow'):
    A, B = pan.P(a[0], a[1], off), pan.P(b[0], b[1], off)
    d = B - A
    if d.length < 1e-5:
        return
    d.normalize()
    s = pan.n.cross(d) * (w / 2)
    e = d * (w * 0.35)
    k.quad([A - s - e, B - s + e, B + s + e, A + s - e], mat, col, flag=NOAO, nh=pan.n)


def glyph(k, pan, name, u, v, size=0.3, w=None, col=RUNE_C, off=0.022, aspect=0.7, mat='M_rune_glow'):
    """Rune centred at (u, v) of the panel; size = height in metres."""
    gh = size / pan.wv
    gw = size * aspect / pan.wu
    w = w or size * 0.13
    for (x0, y0, x1, y1) in GLYPHS[name]:
        stroke(k, pan, (u + (x0 - 0.5) * gw, v + (y0 - 0.5) * gh), (u + (x1 - 0.5) * gw, v + (y1 - 0.5) * gh), w, off,
               col, mat)


def rune_column(k, pan, names, v0=0.2, v1=0.85, u=0.5, size=0.3, col=RUNE_C, **kw):
    n = len(names)
    for i, nm in enumerate(names):
        v = lerp(v1, v0, i / max(n - 1, 1)) if n > 1 else (v0 + v1) / 2
        glyph(k, pan, nm, u, v, size, col=col, **kw)


def menhir(k, c, h, w, d, lean=(0.0, 0.0), seed=0, rz=0.0, sink=0.7, mat=RK, col=None, taper=0.55, n=4,
           top_slant=0.25, rough=0.1):
    """Standing stone: lofted rounded-rectangle sections. Returns (front Panel, back Panel) in the CURRENT
    local frame (already including c / rz), usable for rune strokes."""
    col = col or ROCK
    rng = random.Random(seed * 977 + 5)
    zs = [-sink] + [h * (i / n) ** 0.9 for i in range(n + 1)]
    zs[1] = 0.0
    rings = []
    fronts, backs = [], []
    cz, sz = math.cos(rz), math.sin(rz)

    def X(p):
        return V((c[0] + p[0] * cz - p[1] * sz, c[1] + p[0] * sz + p[1] * cz, c[2] + p[2]))
    for i, z in enumerate(zs):
        t = clamp(z / h)
        sc = 1.0 - (1.0 - taper) * t ** 1.6
        if i == 0:
            sc = 1.08
        hw = w / 2 * sc * (1 + rng.uniform(-rough, rough))
        hd = d / 2 * (1.0 - (1.0 - taper) * 0.6 * t ** 1.6) * (1 + rng.uniform(-rough, rough))
        ox, oy = lean[0] * max(z, 0.0) + rng.uniform(-rough, rough) * w * 0.25, lean[1] * max(z, 0.0)
        ch = min(hw, hd) * 0.42
        zz = [z] * 8
        if i == len(zs) - 1:
            zz = [z - top_slant * h * 0.12 * (1 + math.cos(a)) for a in [0.6 + j * PI / 4 for j in range(8)]]
        ring = [(-hw + ch, -hd), (hw - ch, -hd), (hw, -hd + ch), (hw, hd - ch), (hw - ch, hd), (-hw + ch, hd),
                (-hw, hd - ch), (-hw, -hd + ch)]
        ring = [X((x + ox, y + oy, zz[j])) for j, (x, y) in enumerate(ring)]
        rings.append(ring)
    vr = [[k.v(p) for p in ring] for ring in rings]
    for i in range(len(rings) - 1):
        for j in range(8):
            j2 = (j + 1) % 8
            k.f([vr[i][j], vr[i][j2], vr[i + 1][j2], vr[i + 1][j]], mat, col, smooth=True)
    # top cap (fan around a raised centre)
    top = rings[-1]
    cen = sum(top, V((0, 0, 0))) / 8 + V((0, 0, h * 0.035))
    vc = k.v(cen)
    for j in range(8):
        k.f([vr[-1][j], vr[-1][(j + 1) % 8], vc], mat, col, smooth=True)
    front = Panel(rings[1][0], rings[1][1], rings[-1][1], rings[-1][0])
    back = Panel(rings[1][4], rings[1][5], rings[-1][5], rings[-1][4])
    front.rings = rings
    return front, back


def ring_panel(rings, i0, i1, j):
    """Panel on the facet j (0 = front, 2 = +X side, 4 = back, 6 = -X side) of a menhir between ring i0, i1."""
    return Panel(rings[i0][j], rings[i0][(j + 1) % 8], rings[i1][(j + 1) % 8], rings[i1][j])


# ----------------------------------------------------------------------------- vines, tubes with frames
def vine(k, pts, rads, n=5, mat='M_bark_oak', col=None, caps=(True, True), twist=0.0, flag=0, smooth=True):
    """Tube with per-point radius. Returns frames [(p, s, u, r), ...] for thorns / veins."""
    col = col or ROCK
    pts = [V(p) for p in pts]
    if not isinstance(rads, (list, tuple)):
        rads = [rads] * len(pts)
    frames = []
    ref = None
    cum = 0.0
    rings = []
    cums = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if i:
            cum += (pts[i] - pts[i - 1]).length
        cums.append(cum)
        if ref is None:
            ref = V((0, 0, 1)) if abs(d.z) < 0.9 else V((1, 0, 0))
        s = ref.cross(d)
        if s.length < 1e-6:
            s = V((1, 0, 0)).cross(d)
        s.normalize()
        u = d.cross(s)
        ref = u
        frames.append((p, s, u, rads[i]))
        tw = twist * i
        rings.append([k.v(p + (s * math.cos(tw + 2 * PI * j / n) + u * math.sin(tw + 2 * PI * j / n)) * rads[i])
                      for j in range(n)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        per = 2 * PI * max(rads[i], 0.02)
        for j in range(n):
            j2 = (j + 1) % n
            d = {a[j]: (per * j / n, cums[i]), a[j2]: (per * (j + 1) / n, cums[i]),
                 b[j2]: (per * (j + 1) / n, cums[i + 1]), b[j]: (per * j / n, cums[i + 1])}
            k.f([a[j], a[j2], b[j2], b[j]], mat, col, uv=d, smooth=smooth, flag=flag)
    if caps[0]:
        k.f(list(reversed(rings[0])), mat, col, flag=flag)
    if caps[1]:
        k.f(rings[-1], mat, col, flag=flag)
    return frames


def surf(fr, ang, off=0.0):
    p, s, u, r = fr
    return p + (s * math.cos(ang) + u * math.sin(ang)) * (r + off)


def vein(k, frames, ang0, w=0.05, off=0.02, col=RUNE_V, mat='M_rune_glow', spin=0.0, i0=0, i1=None):
    """Glowing ribbon running along a vine (angle ang0 around it, drifting by `spin` per frame)."""
    i1 = len(frames) - 1 if i1 is None else i1
    for i in range(i0, i1):
        a0, a1 = ang0 + spin * i, ang0 + spin * (i + 1)
        f0, f1 = frames[i], frames[i + 1]
        h0, h1 = w / 2 / max(f0[3], 0.03), w / 2 / max(f1[3], 0.03)
        pts = [surf(f0, a0 - h0, off), surf(f1, a1 - h1, off), surf(f1, a1 + h1, off), surf(f0, a0 + h0, off)]
        nrm = (surf(f0, a0, 1.0) - f0[0])
        k.quad(pts, mat, col, flag=NOAO, nh=nrm)


def thorn(k, p, d, length=0.3, r=0.05, mat='M_bark_oak', col=None, n=3):
    col = col or mulc(ROCK, 0.7)
    k.cyl(p, V(p) + V(d).normalized() * length, r, 0.0, n=n, mat=mat, col=col, caps=(False, False), smooth=False)


# ----------------------------------------------------------------------------- bones
def skull(k, c, s=1.0, rz=0.0, rx=0.0, ry=0.0, jaw=True, col=None, nu=7, nv=3):
    """Human skull, ~0.2 m (scale s), face towards local -Y."""
    col = col or BONE
    with k.at(c, rz=rz, rx=rx, ry=ry, scale=s):
        k.blob((0, 0.015, 0.045), (0.078, 0.095, 0.075), nu=nu, nv=nv, mat='M_bone', col=col, zmin=-0.55)
        k.box((-0.05, -0.085, -0.055), (0.05, -0.02, 0.03), 'M_bone', mulc(col, 0.95), taper=(1.15, 1.0),
              skip=('+y', '+z'))
        if jaw:
            k.box((-0.04, -0.08, -0.105), (0.04, 0.0, -0.062), 'M_bone', mulc(col, 0.88), taper=(1.2, 1.0),
                  skip=('+z',))
        for sx in (-1, 1):
            k.quad([(sx * 0.012, -0.088, -0.012), (sx * 0.043, -0.088, -0.012), (sx * 0.043, -0.088, 0.022),
                    (sx * 0.012, -0.088, 0.022)], 'M_bone', DARK, flag=NOAO, nh=(0, -1, 0))
        k.quad([(-0.011, -0.088, -0.042), (0.011, -0.088, -0.042), (0, -0.088, -0.018)], 'M_bone', DARK, flag=NOAO,
               nh=(0, -1, 0))


def bone(k, a, b, r=0.022, col=None, n=4, knobs=True):
    col = col or k.jit(BONE, 0.08)
    a, b = V(a), V(b)
    d = (b - a)
    if not knobs:
        k.cyl(a, b, r, r * 0.85, n=3, mat='M_bone', col=col, caps=(True, True))
        return
    k.cyl(a + d * 0.08, b - d * 0.08, r, r, n=n, mat='M_bone', col=col, caps=(False, False))
    for p in (a + d * 0.06, b - d * 0.06):
        k.blob(p, (r * 1.7, r * 1.7, r * 1.5), nu=4, nv=2, mat='M_bone', col=col)


# ----------------------------------------------------------------------------- cloth
def rag(k, p0, ua, va, w, h, nu=3, nv=5, col=None, wave=0.08, ragged=0.35, seed=0, mat=CL, flag=NOAO, sag=0.0,
        taper=0.0):
    """Tattered hanging cloth: top edge from p0 along ua (width w), hanging along va (length h). Double sided,
    ragged bottom edge. No baked AO by default (the two skins would occlude each other at the frayed corners)."""
    col = col or PAL['red']
    rng = random.Random(seed * 31 + 3)
    p0, ua, va = V(p0), V(ua).normalized(), V(va).normalized()
    nrm = ua.cross(va).normalized()
    rows = []
    for j in range(nv + 1):
        fv = j / nv
        row = []
        for i in range(nu + 1):
            fu = i / nu
            hh = h * fv
            if j == nv:
                hh = h * (1.0 - ragged * rng.random())
            elif j == nv - 1:
                hh = min(hh, h * (1.0 - ragged) * 0.98)
            x = (fu - 0.5) * w * (1.0 - taper * fv) + 0.5 * w
            wv = wave * fv * math.sin(fu * 5.1 + fv * 4.0 + seed)
            row.append(p0 + ua * x + va * hh + nrm * wv - V((0, 0, sag * 4 * fu * (1 - fu) * (1 - fv))))
        rows.append(row)

    def cf(p):
        return mulc(col, 0.86 + 0.2 * (mnoise.noise(p * 1.7 + V((seed, 0, 0))) * 0.5 + 0.5))
    k.grid(rows, mat, col, double=True, smooth=True, colfn=cf, flag=flag)


# ----------------------------------------------------------------------------- build / preview
def wconstruct(name):
    reg = REG[name]
    reset_scene()
    prep_mats()
    k = Kit(name, seed=reg['opts'].get('seed', 7))
    k.bake_args = dict(reg['opts'].get('bake', {}))
    reg['fn'](k)
    wz = reg['opts'].get('weather', {})
    if wz is not False:
        weather(k, **wz)
        for s in k.subs:
            weather(s, **wz)
    main, objs = k.finish()
    return k, main, objs


def wbuild(name, preview=True, zoom=False, showcol=False):
    reg = REG[name]
    k, main, objs = wconstruct(name)
    path = os.path.join(OUT, name + '.glb')
    info = export_glb(path, objs)
    tris = sum(p['tris'] for m in info['meshes'] if not (m['name'] or '').startswith(('COL_', 'WALK_'))
               for p in m['prims'])
    mn, mx = _bounds([o for o in objs if o.type == 'MESH' and not o.name.startswith(('COL_', 'WALK_'))])
    flag = 'OK' if tris <= reg['budget'] else 'OVER BUDGET'
    nodes = [o.name for o in objs if o.type != 'MESH' or o.name.startswith(('COL_', 'WALK_', 'ROT_'))]
    print('ASSET %s tris=%d/%d %s size=(%.2f, %.2f, %.2f) min=(%.2f, %.2f, %.2f) max=(%.2f, %.2f, %.2f) nodes=%s'
          % (name, tris, reg['budget'], flag, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, mn.x, mn.y, mn.z,
             mx.x, mx.y, mx.z, nodes))
    if preview:
        if showcol:
            os.environ['ARCH_SHOWCOL'] = '1'
        show = stage(k, objs)
        back_light()
        if showcol:
            show += [o for o in objs if o.name.startswith(('COL_', 'WALK_'))]
            render_sheet(os.path.join(PREVIEWS, 'world_%s_col.png' % name), show, views=('top', 'persp', 'front'),
                         res=384, cols=3)
        else:
            res = reg['opts'].get('res', 384)
            render_sheet(os.path.join(PREVIEWS, 'world_%s.png' % name), show,
                         views=reg['opts'].get('views', ('front', 'left', 'back', 'persp')), res=res, cols=4)
            if zoom:
                render_sheet(os.path.join(PREVIEWS, 'world_%s_zoom.png' % name), show,
                             views=zoom if isinstance(zoom, (list, tuple)) else ('persp_back', 'top', (0.3, 0.9, -0.3)),
                             res=512, cols=3)
    return info, tris


def back_light():
    """extra preview sun from behind so that the back views are readable"""
    if bpy.data.objects.get('pv_back') is None:
        ld = bpy.data.lights.new('pv_back', 'SUN')
        ld.energy = 1.3
        lo = bpy.data.objects.new('pv_back', ld)
        lo.rotation_euler = (math.radians(-50), 0, math.radians(25))
        link(lo)


def wfamily(names, path, views=('persp',), res=224, per_row=9):
    imgs = []
    for name in names:
        k, main, objs = wconstruct(name)
        show = stage(k, objs)
        cam = setup_preview(res)
        bpy.context.view_layer.update()
        mn, mx = _bounds(show)
        for v in views:
            frame_camera(cam, mn, mx, v)
            imgs.append(render_to_array())
    save_png(path, montage(imgs, cols=per_row * len(views)))
    print('PREVIEW', path)
