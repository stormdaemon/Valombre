"""VALOMBRE world pack - biome set dressing 3: wrecks (sunken rowboat, beached ship) and the swamp stilt hut
(uses world_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_kit import *

OAK = 'M_bark_oak'
WET = mulc(PAL['plank_d'], 0.72)       # rotten, waterlogged planking


# ----------------------------------------------------------------------------- hull generator
def hull(k, Lh, B, D, ns=10, nk=4, present=None, th=0.04, col=None, sheer=0.3, rocker=0.25, ribs=(), rib_r=0.045,
         rib_sides=(-1, 1), keel=0.07, posts=(0.35, 0.5), rib_col=None, full=(3.4, 2.3)):
    """Planked hull along X (stern at -X, bow at +X), keel on z = 0 amidships. present(i, j, side) -> False to
    leave a plank quad out (holes, missing strakes). Shared vertices (smooth), inner + outer skin, closed edges.
    Returns P(i, j, side, inner) for placing thwarts / beams."""
    col = col or WET
    rib_col = rib_col or mulc(col, 0.8)
    present = present or (lambda i, j, side: True)
    R3 = k.M.to_3x3()

    def hb(t):
        e = max(0.0, 1.0 - abs(2 * t - 1) ** (full[1] if t > 0.5 else full[0]))
        return B / 2 * e ** 0.55

    def zk(t):
        return D * rocker * abs(2 * t - 1) ** 3

    def zs(t):
        return D * (1.0 + sheer * (2 * t - 1) ** 2)

    def P(i, j, side, inner=False):
        t, s = i / ns, j / nk
        a = s * PI / 2
        y = side * hb(t) * math.sin(a) ** 0.8
        z = zk(t) + (zs(t) - zk(t)) * (1.0 - math.cos(a)) ** 0.85
        p = V((-Lh / 2 + Lh * t, y, z))
        if inner:
            p += V((0, -side * th * math.sin(a), th * math.cos(a)))
        return p
    cache = {}

    def vert(i, j, side, inner):
        key = (i, j, side if (j > 0 or inner) else 0, inner)
        v = cache.get(key)
        if v is None:
            v = k.v(P(i, j, side, inner))
            cache[key] = v
        return v

    def face(vs, hint, c, **kw):
        co = [v.co for v in vs]
        nrm = V((0, 0, 0))
        for q in range(len(co)):
            a, b = co[q], co[(q + 1) % len(co)]
            nrm += V(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        if nrm.dot(R3 @ V(hint)) < 0:
            vs = list(reversed(vs))
        k.f(vs, WD, c, uv='swap', **kw)
    strake = [k.jit(col, 0.1) for _ in range(nk)]

    def has(i, j, side):
        return 0 <= i < ns and 0 <= j < nk and present(i, j, side)
    for side in (-1, 1):
        for i in range(ns):
            for j in range(nk):
                if not has(i, j, side):
                    continue
                cen = (P(i, j, side) + P(i + 1, j + 1, side)) / 2
                out = V((0, side * (0.3 + j), -(nk - j) * 0.8))
                idx = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                face([vert(a, b, side, False) for a, b in idx], out, strake[j], smooth=True)
                face([vert(a, b, side, True) for a, b in idx], -out, mulc(strake[j], 0.8), smooth=True)
                for (e0, e1, ni, nj) in ((idx[0], idx[1], i, j - 1), (idx[1], idx[2], i + 1, j), (idx[2], idx[3], i, j + 1),
                                         (idx[3], idx[0], i - 1, j)):
                    if nj < 0 or has(ni, nj, side):
                        continue
                    if (ni < 0 or ni >= ns) and nj == j:
                        continue                       # stem / stern: the strakes meet on the centre line
                    mid = (P(e0[0], e0[1], side) + P(e1[0], e1[1], side)) / 2
                    vs = [k.v(P(e0[0], e0[1], side)), k.v(P(e1[0], e1[1], side)), k.v(P(e1[0], e1[1], side, True)),
                          k.v(P(e0[0], e0[1], side, True))]
                    face(vs, mid - cen, mulc(strake[j], 0.7))
    for i in ribs:
        for side in rib_sides:
            pts = [P(i, j, side, True) + V((0, -side * rib_r * 0.6 * math.sin(j / nk * PI / 2), rib_r * 0.5)) for j in
                   range(nk + 1)]
            pts[-1] = pts[-1] + V((0, 0, rib_r * 2.5))
            k.tube(pts, rib_r, n=3, mat=WD, col=k.jit(rib_col, 0.1), caps=True)
    if keel:
        kp = [V((-Lh / 2 + Lh * t, 0, zk(t) - keel * 0.6)) for t in [0.03 + 0.94 * q / 6 for q in range(7)]]
        k.tube(kp, keel, n=4, mat=WD, col=rib_col, caps=True)
        for (t, rake, hh) in ((0.0, -1, posts[0]), (1.0, 1, posts[1])):
            x = -Lh / 2 + Lh * t
            k.beam((x - rake * keel * 0.3, 0, zk(t) - keel), (x + rake * (0.12 * D + hh * 0.25), 0, zs(t) + hh), keel * 1.7,
                   keel * 2.2, WD, k.jit(rib_col, 0.08), up=(1, 0, 0))
    return P, zs


# ----------------------------------------------------------------------------- sunken rowboat
@asset('sunken_boat', 'Half-buried wreck of a rowing boat, 4.4 m, heeled over, planking stove in on one side showing '
       'the ribs, broken oar', 400, footprint=[5.0, 2.6], bake=dict(ao_dist=0.7, ao_min=0.32, dirt_h=0.35, dirt=0.4),
       weather=False)
def sunken_boat(k):
    def pres(i, j, side):
        if side > 0 and j >= 2 and 2 <= i <= 4:
            return False
        if side > 0 and j == 3 and i == 5:
            return False
        if side < 0 and j == 3 and i in (0, 1):
            return False
        return True
    with k.at((0, 0.1, -0.3), rx=0.36, ry=0.1, rz=0.25):
        P, zs = hull(k, 4.4, 1.6, 0.62, ns=7, nk=4, present=pres, ribs=(2, 4), rib_sides=(1,), rib_r=0.032, th=0.03,
                     keel=0.05, posts=(0.22, 0.3))
        a, b = P(3, 2, -1, True), P(3, 2, 1, True)
        k.beam(a, b, 0.2, 0.035, WD, k.jit(WET, 0.1), up=(0, 0, 1))
    k.cyl((0.4, -1.25, 0.05), (2.1, -0.95, 0.12), 0.028, n=4, mat=WD, col=PAL['plank_d'])
    block(k, (2.3, -0.92, 0.12), (0.5, 0.14, 0.025), rz=0.18, ry=-0.05, mat=WD, col=PAL['plank_d'])
    k.col('boat', (-2.1, -0.7, 0), (2.1, 0.8, 0.7))
    k.person = (2.0, -1.6)


# ----------------------------------------------------------------------------- beached ship
@asset('shipwreck', 'Beached cog broken open, 14 m: keel, stem and stern posts, bare ribs, the surviving planking of the '
       'far side and the stern, deck beams, mast stump and the fallen mast with a yard and sail rags, spilled cargo',
       1500, footprint=[15.4, 11.6], bake=dict(ao_dist=1.8, ao_min=0.28, dirt_h=0.9, dirt=0.4), res=512,
       weather=False)
def shipwreck(k):
    ns, nk = 14, 5

    def pres(i, j, side):
        if side < 0:                                   # near (low) side: mostly gone
            if i <= 3:
                return j <= 3
            if i >= 11:
                return j <= 1
            return j == 0 or (j == 1 and i % 4 != 2)
        if i >= 12:                                    # far side: broken bow
            return j <= 2
        if j == nk - 1 and i in (5, 6, 9):
            return False
        if j >= 3 and i == 8:
            return False
        return True
    M = Matrix.Translation((0, 0.3, -0.75)) @ Euler((0.4, 0.03, 0.06), 'XYZ').to_matrix().to_4x4()
    with k.xf(M):
        P, zs = hull(k, 14.0, 4.4, 2.5, ns=ns, nk=nk, present=pres, ribs=(2, 4, 6, 8, 10, 12), rib_r=0.085,
                     th=0.06, keel=0.14, posts=(0.9, 1.5), sheer=0.34, col=WET)
        for i in (3, 5, 7, 9, 11):
            a, b = P(i, nk - 1, -1, True), P(i, nk - 1, 1, True)
            if i in (7, 9):
                b = a.lerp(b, 0.55) + V((0, 0, -0.5))
            k.beam(a, b, 0.2, 0.2, WD, k.jit(mulc(WET, 0.85), 0.1), up=(0, 0, 1))
        # stern deck remnant + rudder
        a0, a1 = P(1, nk - 1, -1, True), P(1, nk - 1, 1, True)
        b0, b1 = P(3, nk - 1, -1, True), P(3, nk - 1, 1, True)
        k.quad([a0, a1, b1, b0], WD, WET, double=True, uv='swap')
        k.box((-7.55, -0.06, 0.2), (-6.95, 0.06, 2.3), WD, mulc(WET, 0.85), taper=(0.6, 1.0), shift=(0.1, 0))
        # mast stump
        k.cyl((-0.6, 0, 0.25), (-0.7, 0.1, 3.3), 0.24, 0.21, n=6, mat=WD, col=PAL['beam_l'], cap_col=PAL['plank_l'])
    # fallen mast, yard, sail rags, rope
    m0, m1 = V((-0.2, -1.6, 1.5)), V((5.6, -8.6, 0.22))
    k.cyl(m0, m1, 0.2, 0.13, n=6, mat=WD, col=PAL['beam_l'])
    yd = (m1 - m0).normalized()
    ys = yd.cross(V((0, 0, 1))).normalized()
    yc = m0.lerp(m1, 0.78) + V((0, 0, 0.24))
    k.cyl(yc - ys * 2.6 + V((0, 0, 0.5)), yc + ys * 2.4 - V((0, 0, 0.05)), 0.09, 0.07, n=5, mat=WD, col=PAL['beam'])
    rag(k, yc - ys * 2.3 + V((0, 0, 0.42)), ys + V((0, 0, -0.1)), -yd * 0.9 + V((0, 0, -0.35)), 3.6, 2.4, nu=4, nv=4,
        col=L('#b9ad92'), wave=0.22, ragged=0.5, seed=3, sag=0.25)
    k.tube([m0.lerp(m1, 0.3) + V((0, 0, 0.2)), V((1.2, -1.3, 1.9)), V((2.8, -0.6, 2.2))], 0.03, n=3)
    # spilled cargo, rocks
    barrel(k, (3.2, -3.4, 0.0), r=0.34, h=0.9, n=6)
    with k.at((1.6, -4.3, 0.3), rx=PI / 2 - 0.1, rz=0.8):
        barrel(k, (0, 0, -0.4), r=0.32, h=0.85, n=6, lid=False)
    crate(k, (-2.6, -3.9, -0.08), (0.8, 0.7, 0.6), rz=0.4, col=WET)
    for (c, r, sd) in (((6.6, 2.0, 0.0), (1.1, 0.9, 0.6), 3), ((-6.9, -2.4, 0.0), (0.9, 0.8, 0.5), 5),
                       ((7.4, -1.6, 0.0), (0.7, 0.6, 0.4), 8)):
        rock(k, c, r, seed=sd, nu=7, nv=3, zmin=-0.4)
    k.col('hull', (-7.2, -2.3, 0), (7.2, 2.6, 2.6))
    k.col('mast', (1.6, -5.4, 0), (3.2, -3.8, 1.2), rz=0.0)
    k.person = (-3.9, -3.2)


# ----------------------------------------------------------------------------- swamp hut
def log(k, a, b, r=0.11, n=6, mat=OAK, col=None, caps=(True, True), taper=0.85):
    k.cyl(a, b, r, r * taper, n=n, mat=mat, col=col or k.jit(mulc(PAL['bark'], 0.6), 0.1), caps=caps, cap_mat=WD,
          cap_col=PAL['plank_d'])


@asset('swamp_hut', "Crooked hermit's hut on stilts: plank platform 2 m above the mud on six leaning logs, leaning "
       "board walls, sagging mossy thatch roof, porch with ladder, lantern, hanging bones", 2000, footprint=[5.4, 7.6],
       bake=dict(ao_dist=1.4, ao_min=0.3, dirt_h=0.7, dirt=0.35, moss=1.3), res=512, weather=False)
def swamp_hut(k):
    ZP = 2.0
    x0, x1, yf, yb, yp = -2.0, 2.0, -1.4, 1.8, -2.7
    # ---- stilts + bracing
    feet = [(-1.9, -2.45, 0.1, 0.12), (1.95, -2.4, -0.12, 0.1), (-1.95, -0.3, 0.14, -0.05), (1.9, -0.2, -0.1, -0.08),
            (-1.85, 1.65, 0.1, -0.14), (1.9, 1.7, -0.13, -0.1)]
    tops = []
    for (x, y, lx, ly) in feet:
        a, b = V((x - lx * 1.6, y - ly * 1.6, -1.0)), V((x + lx * 0.4, y + ly * 0.4, ZP - 0.05))
        log(k, a, b, r=0.15, n=6, caps=(False, True))
        tops.append((a, b))
    for (i, j, za, zb_) in ((0, 2, 0.4, 1.7), (2, 4, 1.6, 0.4), (1, 3, 1.7, 0.5), (3, 5, 0.4, 1.6), (0, 1, 0.5, 1.6),
                            (4, 5, 1.5, 0.5)):
        pa = tops[i][0].lerp(tops[i][1], (za + 1.0) / 3.0)
        pb = tops[j][0].lerp(tops[j][1], (zb_ + 1.0) / 3.0)
        log(k, pa, pb, r=0.06, n=4, caps=(False, False), taper=0.9)
    # ---- platform: bearers + deck boards
    for x in (x0 + 0.05, 0.0, x1 - 0.05):
        k.beam((x, yp - 0.1, ZP - 0.17), (x, yb + 0.1, ZP - 0.17), 0.16, 0.18, WD, k.jit(PAL['beam_d']))
    k.boards((x0 - 0.25, yp, ZP - 0.08), (1, 0, 0), (0, 1, 0), 4.5, yb - yp + 0.1, 13, thick=0.06, col=WET, gap=0.03,
             lj=0.18, cj=0.14, skip=())
    # ---- crooked hut body (sheared)
    Sh = Matrix.Identity(4)
    Sh[0][2], Sh[1][2] = 0.085, -0.04
    Mh = Matrix.Translation((0, 0, ZP)) @ Sh @ Matrix.Translation((0, 0, -ZP))
    ze = ZP + 1.85
    rise = 2.0
    with k.xf(Mh):
        wf = Wall((x0, yf), (x1, yf), ZP, ze)
        wr = Wall((x1, yf), (x1, yb), ZP, ze)
        wb = Wall((x1, yb), (x0, yb), ZP, ze)
        wl = Wall((x0, yb), (x0, yf), ZP, ze)
        # doorway (dark) with a hide curtain, small lit window
        ds, dw, dh = 1.55, 0.95, 1.6
        k.quad([wf.P(ds - dw / 2, ZP, 0.012), wf.P(ds + dw / 2, ZP, 0.012), wf.P(ds + dw / 2, ZP + dh, 0.012),
                wf.P(ds - dw / 2, ZP + dh, 0.012)], WD, DARK, flag=NOAO)
        for s in (ds - dw / 2 - 0.06, ds + dw / 2 + 0.06):
            wbeam(k, wf, s, ZP, s, ZP + dh + 0.1, 0.12, 0.06, col=k.jit(PAL['beam_d']))
        wbeam(k, wf, ds - dw / 2 - 0.2, ZP + dh + 0.1, ds + dw / 2 + 0.2, ZP + dh + 0.06, 0.14, 0.07,
              col=k.jit(PAL['beam_d']), caps=(True, True))
        rag(k, wf.P(ds - dw / 2 + 0.02, ZP + dh, 0.05), wf.d, (0.1, -0.06, -1), 0.55, 1.5, nu=2, nv=4,
            col=L('#6b5a45'), wave=0.05, ragged=0.2, seed=2, mat='M_leather')
        opf = [(ds - dw / 2 - 0.12, ds + dw / 2 + 0.12, ZP, ZP + dh + 0.18),
               window(k, wf, 3.15, ZP + 0.85, 0.5, 0.5, shutters='r', bars=(1, 1), fw=0.07)]
        plank_wall(k, wf, col=WET, battens=0.42, openings=opf, bw=0.13)
        opr = [window(k, wr, 1.7, ZP + 0.8, 0.55, 0.55, shutters='l', bars=(1, 1), fw=0.07)]
        plank_wall(k, wr, col=WET, battens=0.45, openings=opr, bw=0.13)
        plank_wall(k, wb, col=mulc(WET, 0.95), battens=0.45, bw=0.13)
        plank_wall(k, wl, col=WET, battens=0.45, bw=0.13)
        corner_posts(k, x0, yf, x1, yb, ZP, ze, bw=0.15, col=PAL['beam_d'])
        gable_tri(k, Wall((x0, yf), (x1, yf), ze, ze), rise, mat=WD, col=mulc(WET, 0.9))
        gable_tri(k, Wall((x1, yb), (x0, yb), ze, ze), rise, mat=WD, col=mulc(WET, 0.9))
        roof_gable(k, x0, x1, yf, yb, ze, rise, oe=0.55, og=1.05, og2=0.45, tv=0.3, sag=0.3, nu=5, nv=4,
                   mat='M_thatch', col=PAL['thatch_old'], axis='y', moss=1.2, wob=0.07)
        # stove pipe through the roof
        k.cyl((1.05, 0.9, ze + 0.9), (1.2, 0.95, ze + 2.2), 0.1, 0.09, n=6, mat=IR, col=mixc(PAL['iron'], RUST, 0.5),
              caps=(False, True), cap_col=DARK)
        k.empty('SMOKE_roof', tuple(Mh @ V((1.22, 0.95, ze + 2.3))))
        # lantern under the porch eave
        lx, ly, lz = -0.9, yf - 0.85, ze + 0.25
        k.tube([(lx, ly, lz + 0.35), (lx, ly, lz)], 0.01, n=3, mat=IR, col=PAL['iron'], caps=False)
        k.box((lx - 0.08, ly - 0.08, lz - 0.24), (lx + 0.08, ly + 0.08, lz - 0.02), 'M_window_glow', PAL['glow'],
              flag=NOAO)
        k.cyl((lx, ly, lz - 0.02), (lx, ly, lz + 0.06), 0.12, 0.02, n=4, mat=IR, col=PAL['iron'], phase=PI / 4,
              smooth=False, caps=(True, False))
        k.box((lx - 0.1, ly - 0.1, lz - 0.28), (lx + 0.1, ly + 0.1, lz - 0.24), IR, PAL['iron'])
    # ---- porch: railing, ladder, clutter
    for (xa, ya, xb, yb_) in ((x0 - 0.15, yp + 0.08, x0 - 0.15, yf - 0.1), (x0 - 0.15, yp + 0.08, -0.9, yp + 0.08),
                              (x1 + 0.15, yp + 0.08, x1 + 0.15, yf - 0.1), (0.75, yp + 0.08, x1 + 0.15, yp + 0.08)):
        k.beam((xa, ya, ZP + 0.95 + k.r(-0.05, 0.05)), (xb, yb_, ZP + 0.92 + k.r(-0.06, 0.06)), 0.07, 0.07, WD,
               k.jit(PAL['beam_l']))
    for (x, y) in ((x0 - 0.15, yp + 0.08), (x1 + 0.15, yp + 0.08), (-0.9, yp + 0.08), (0.75, yp + 0.08),
                   (x0 - 0.15, yf - 0.1), (x1 + 0.15, yf - 0.1)):
        k.beam((x, y, ZP - 0.1), (x + k.r(-0.05, 0.05), y, ZP + 1.02), 0.08, 0.08, WD, k.jit(PAL['beam']),
               skip=('c0',))
    lxa, lxb = -0.72, 0.58
    for x in (lxa, lxb):
        k.beam((x, yp - 1.05, -0.2), (x, yp + 0.02, ZP + 0.55), 0.08, 0.07, WD, k.jit(PAL['beam']), up=(1, 0, 0))
    for i in range(7):
        f = (i + 0.7) / 8.2
        y = lerp(yp - 1.05, yp + 0.02, f)
        z = lerp(-0.2, ZP + 0.55, f)
        k.beam((lxa - 0.06, y, z), (lxb + 0.06, y, z + k.r(-0.03, 0.03)), 0.05, 0.05, WD, k.jit(PAL['plank']))
    barrel(k, (1.45, yf - 0.5, ZP), r=0.27, h=0.75, n=7)
    k.box((-1.75, yf - 0.75, ZP), (-1.2, yf - 0.3, ZP + 0.4), WD, k.jit(WET), skip=('-z',))
    # bone charms hanging under the porch edge
    for (x, ln, sd) in ((-1.5, 0.75, 1), (1.3, 0.55, 2), (1.75, 0.9, 3)):
        k.tube([(x, yp + 0.02, ZP - 0.12), (x + 0.03, yp, ZP - 0.12 - ln)], 0.008, n=3, caps=False)
        bone(k, (x - 0.1, yp, ZP - 0.14 - ln), (x + 0.14, yp, ZP - 0.2 - ln), r=0.018, knobs=False)
        if sd == 1:
            skull(k, (x + 0.02, yp - 0.02, ZP - 0.34 - ln), s=0.9, rz=0.3, nu=6)
    k.empty('ANCHOR_npc', (0.9, -2.05, ZP))
    k.empty('ANCHOR_interact', (0.0, yp - 1.6, 0.0))
    k.col('body', (x0 - 0.3, yp, 0), (x1 + 0.3, yb + 0.1, ze + rise))
    k.col('ladder', (lxa - 0.1, yp - 1.1, 0), (lxb + 0.1, yp, 1.2))
    k.person = (1.4, yp - 1.4)
