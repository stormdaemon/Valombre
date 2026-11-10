"""VALOMBRE settlements pack - hero buildings 1: tavern, forge (uses arch_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *
from arch_houses import rect_walls, door_reveal, purlin_ends

GOLD = lin('#d9a441')


# ----------------------------------------------------------------------------- shared bits
def dormer(k, xc, y_wall, z_eave, slope, tv_main, setback=0.8, w=1.35, h=1.15, pcol=None):
    """Gabled dormer on a front (-Y facing) roof slope whose underside starts at (y_wall, z_eave)."""
    yd = y_wall + setback
    zb = z_eave + setback * slope + tv_main
    zt = zb + h
    rise_d = (w / 2) * math.tan(math.radians(47))
    zlow = zb - 0.3
    base = pcol or PAL['plaster']
    wd = Wall((xc - w / 2, yd), (xc + w / 2, yd), zlow, zt)
    k.quad([wd.P(0, zlow), wd.P(w, zlow), wd.P(w, zt), wd.P(0, zt)], 'M_plaster', base)
    window(k, wd, w / 2, zb + 0.24, 0.62, 0.66, shutters=0, fw=0.07, sill=False)
    bw = 0.12
    wbeam(k, wd, bw / 2, zlow, bw / 2, zt, bw, 0.035)
    wbeam(k, wd, w - bw / 2, zlow, w - bw / 2, zt, bw, 0.035)
    wbeam(k, wd, 0, zb + 0.08, w, zb + 0.08, bw, 0.03)
    frame_gable(k, Wall((xc - w / 2, yd), (xc + w / 2, yd), zt, zt), rise_d, bw=0.12, pattern=None, pcol=base)
    yb = yd + (h + 0.3) / slope + 0.05
    for sg in (-1, 1):
        x = xc + sg * w / 2
        k.quad([(x, yd, zlow), (x, yd, zt), (x, yb, zt)], 'M_wood_planks', PAL['plank_d'], nh=(sg, 0, 0))
    yback = y_wall + (zt + rise_d + 0.35 - z_eave) / slope
    roof_gable(k, xc - w / 2, xc + w / 2, yd, yback, zt, rise_d, oe=0.16, og=0.24, og2=0.0, tv=0.1, sag=0.0,
               nu=1, nv=1, mat='M_roof_tiles', axis='y', ridge=False, barge=(True, False), moss=0.6)


def lantern(k, p, s=0.11, hang=0.0):
    """Small iron lantern with glowing panes; p = top hook point."""
    x, y, z = p
    if hang:
        k.tube([(x, y, z), (x, y, z - hang)], 0.008, n=3, mat='M_metal_iron', col=PAL['iron'])
    z -= hang
    k.cyl((x, y, z - 0.07), (x, y, z), s * 1.25, 0.012, n=4, mat='M_metal_iron', col=PAL['iron'], phase=PI / 4,
          smooth=False, uv='box')
    k.box((x - s * 0.72, y - s * 0.72, z - 0.07 - s * 2.1), (x + s * 0.72, y + s * 0.72, z - 0.07),
          'M_window_glow', PAL['glow'], skip=('+z',), flag=NOAO)
    k.box((x - s * 0.9, y - s * 0.9, z - 0.1 - s * 2.1), (x + s * 0.9, y + s * 0.9, z - 0.07 - s * 2.1),
          'M_metal_iron', PAL['iron'])
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.beam((x + sx * s * 0.78, y + sy * s * 0.78, z - 0.07 - s * 2.1), (x + sx * s * 0.78, y + sy * s * 0.78,
                   z - 0.07), 0.016, 0.016, 'M_metal_iron', PAL['iron'], skip=('c0', 'c1'), uv='box')


def hanging_sign(k, x, y_wall, z, reach=1.45, bw=0.95, bh=0.68):
    """Wrought-iron bracket projecting towards -Y with a hanging board (faces +/-X) and a gold star."""
    I, ic = 'M_metal_iron', PAL['iron']
    k.beam((x, y_wall, z), (x, y_wall - reach, z), 0.045, 0.055, I, ic, uv='box')
    k.beam((x, y_wall, z - 0.8), (x, y_wall - reach * 0.78, z - 0.03), 0.035, 0.04, I, ic, uv='box')
    k.tube([(x, y_wall - reach + 0.11 * math.sin(a), z + 0.11 - 0.11 * math.cos(a)) for a in
            [PI * 1.6 * i / 6 for i in range(7)]], 0.017, n=3, mat=I, col=ic)
    yc = y_wall - reach * 0.56
    zt = z - 0.24
    k.box((x - 0.022, yc - bw / 2, zt - bh), (x + 0.022, yc + bw / 2, zt), 'M_wood_planks', mulc(PAL['green'], 1.6),
          uv='swap')
    for (a, b, c, d) in ((yc - bw / 2 - 0.03, zt - 0.05, yc + bw / 2 + 0.03, zt + 0.01),
                         (yc - bw / 2 - 0.03, zt - bh - 0.01, yc + bw / 2 + 0.03, zt - bh + 0.05),
                         (yc - bw / 2 - 0.03, zt - bh, yc - bw / 2 + 0.03, zt),
                         (yc + bw / 2 - 0.03, zt - bh, yc + bw / 2 + 0.03, zt)):
        k.box((x - 0.035, a, b), (x + 0.035, c, d), 'M_wood_planks', k.jit(PAL['beam']))
    for sy in (-1, 1):
        k.tube([(x, yc + sy * bw * 0.36, z - 0.02), (x, yc + sy * bw * 0.36, zt + 0.01)], 0.011, n=3, mat=I, col=ic)
    zc = zt - bh / 2
    for sg in (-1, 1):
        pts = []
        for i in range(10):
            a = 2 * PI * i / 10
            r = 0.23 if i % 2 == 0 else 0.095
            pts.append((x + sg * 0.03, yc + r * math.sin(a), zc + r * math.cos(a)))
        k.quad(pts, 'M_metal_gold', GOLD, nh=(sg, 0, 0))


def trough_box(k, c, s=(1.4, 0.45, 0.4), rz=0.0, legs=True, fill=None):
    """Open plank trough. c = centre on the ground."""
    with k.at(c, rz=rz):
        sx, sy, sz = s
        t = 0.04
        z0 = 0.12 if legs else 0.0
        col = PAL['plank']
        k.box((-sx / 2, -sy / 2, z0), (sx / 2, sy / 2, z0 + sz), 'M_wood_planks', k.jit(col), skip=('+z',),
              taper=(1.0, 1.25), uv='swap')
        # inner faces + rim
        hy = sy / 2 * 1.25
        zi = z0 + sz * 0.45
        k.quad([(-sx / 2 + t, -hy + t, z0 + sz), (sx / 2 - t, -hy + t, z0 + sz), (sx / 2 - t, -hy * 0.6, zi),
                (-sx / 2 + t, -hy * 0.6, zi)], 'M_wood_planks', mulc(col, 0.7), nh=(0, 1, 0.3))
        k.quad([(-sx / 2 + t, hy - t, z0 + sz), (sx / 2 - t, hy - t, z0 + sz), (sx / 2 - t, hy * 0.6, zi),
                (-sx / 2 + t, hy * 0.6, zi)], 'M_wood_planks', mulc(col, 0.7), nh=(0, -1, 0.3))
        k.quad([(-sx / 2 + t, -hy * 0.6, zi), (sx / 2 - t, -hy * 0.6, zi), (sx / 2 - t, hy * 0.6, zi),
                (-sx / 2 + t, hy * 0.6, zi)], 'M_wood_planks', fill or mulc(col, 0.35), nh=(0, 0, 1))
        for sg in (-1, 1):
            k.quad([(sg * (sx / 2 - t), -hy + t, z0 + sz), (sg * (sx / 2 - t), hy - t, z0 + sz),
                    (sg * (sx / 2 - t), hy * 0.6, zi), (sg * (sx / 2 - t), -hy * 0.6, zi)], 'M_wood_planks',
                   mulc(col, 0.7), nh=(-sg, 0, 0.2))
        if legs:
            for sg in (-1, 1):
                k.box((sg * sx * 0.36 - 0.05, -sy * 0.55, 0), (sg * sx * 0.36 + 0.05, sy * 0.55, z0 + 0.02),
                      'M_wood_planks', k.jit(PAL['plank_d']), skip=('-z',))


def bench(k, c, L=1.6, rz=0.0, h=0.45, w=0.3):
    with k.at(c, rz=rz):
        k.box((-L / 2, -w / 2, h - 0.05), (L / 2, w / 2, h), 'M_wood_planks', k.jit(PAL['plank']), uv='swap')
        for sx in (-1, 1):
            k.box((sx * (L / 2 - 0.2) - 0.03, -w / 2 + 0.03, 0), (sx * (L / 2 - 0.2) + 0.03, w / 2 - 0.03, h - 0.05),
                  'M_wood_planks', k.jit(PAL['plank_d']), skip=('-z', '+z'), taper=(1.0, 0.8))
        k.beam((-L / 2 + 0.2, 0, h * 0.4), (L / 2 - 0.2, 0, h * 0.4), 0.05, 0.035, 'M_wood_planks',
               k.jit(PAL['plank_d']), skip=('c0', 'c1'))


def rail_bay(k, a, b, z0, top=0.9, n=3, w=0.07):
    """Balustrade between two points (a, b = (x, y)) starting at floor height z0."""
    a, b = V((a[0], a[1], 0)), V((b[0], b[1], 0))
    for zz, ww in ((z0 + top, w + 0.02), (z0 + 0.16, w)):
        k.beam(a + V((0, 0, zz)), b + V((0, 0, zz)), ww, w, 'M_wood_planks', k.jit(PAL['beam']), skip=('c0', 'c1'))
    for i in range(n):
        p = a.lerp(b, (i + 1) / (n + 1))
        k.beam(p + V((0, 0, z0 + 0.19)), p + V((0, 0, z0 + top - 0.03)), 0.05, 0.05, 'M_wood_planks',
               k.jit(PAL['beam_l']), up=(b - a).normalized(), skip=('c0', 'c1'))


# ----------------------------------------------------------------------------- tavern
@asset('tavern', 'Large two-storey inn: rubble-stone ground floor, half-timbered upper floor, tiled roof with '
       'dormers, front porch on posts, hanging star sign, side stable lean-to with stalls',
       6000, footprint=[14.0, 10.6], bake=dict(ao_dist=1.8, warp=0.03))
def tavern(k):
    x0, x1, y0, y1 = -6.0, 3.5, -2.5, 4.5
    zg, zu1 = 3.0, 5.75
    half, ym = 3.5, 1.0
    slope = math.tan(math.radians(47))
    rise = half * slope
    zr = zu1 + rise
    dsx = -1.5
    ds = dsx - x0
    dk = 0.25                                           # porch deck height
    wf, wr, wb, wl = rect_walls(x0, y0, x1, y1, 0.0, zg)
    plinth(k, x0, y0, x1, y1, h=0.55, out=0.06, batter=0.06, gaps=[(0, ds - 0.82, ds + 0.82), (2, 1.4, 2.6)],
           stones=10)
    tc = [0.0, 0.55, 2.45, zg]
    # ---- ground floor (stone)
    door(k, wf, ds, t0=dk, ww=1.25, hh=2.1, planks=6, fw=0.17, step=False)
    window(k, wf, 1.75, 1.32, 1.0, 1.0, bars=(2, 1))
    window(k, wf, 7.3, 1.32, 1.0, 1.0, bars=(2, 1))
    stone_wall(k, wf, quoins=5, scuts=[0, 2.4, 4.75, 7.1, 9.5], tcuts=tc)
    stone_wall(k, wr, quoins=2, tcuts=tc)
    door(k, wb, 2.0, t0=0.3, ww=0.9, hh=1.95, step=False)
    k.box((x1 - 2.0 - 0.7, y1, 0), (x1 - 2.0 + 0.7, y1 + 0.8, 0.15), 'M_stone_wall', PAL['stone_d'], skip=('-z',))
    k.box((x1 - 2.0 - 0.62, y1, 0.15), (x1 - 2.0 + 0.62, y1 + 0.42, 0.3), 'M_stone_wall', PAL['stone_d'],
          skip=('-z',))
    window(k, wb, 5.0, 1.35, 0.8, 0.9, shutters='l')
    window(k, wb, 7.7, 1.35, 0.8, 0.9)
    stone_wall(k, wb, quoins=6, tcuts=tc)
    window(k, wl, 1.3, 1.35, 0.7, 0.85, shutters='l')
    window(k, wl, 5.7, 1.35, 0.7, 0.85, shutters='r')
    stone_wall(k, wl, quoins=4, tcuts=tc)
    # ---- upper floor (timber frame)
    uf, ur, ub, ul = rect_walls(x0, y0, x1, y1, zg, zu1)
    tw = zg + 1.02
    B = 0.17
    ops = [window(k, uf, s, tw, 0.75, 0.95) for s in (1.3, 3.7, 5.8, 8.2)]
    frame_wall(k, uf, posts=[0.7, 1.9, 2.5, 3.1, 4.3, 4.75, 5.2, 6.4, 7.0, 7.6, 8.8], rails=[tw - 0.12],
               openings=ops, bw=B, braces=[(2, '/'), (3, '\\'), (8, '/'), (9, '\\'), (0, '/'), (11, '\\')])
    ops = [window(k, ur, 2.0, tw, 0.7, 0.9), window(k, ur, 5.0, tw, 0.7, 0.9, shutters='r')]
    frame_wall(k, ur, posts=[1.4, 2.6, 3.5, 4.4, 5.6], rails=[tw - 0.12], openings=ops, bw=B,
               braces=[(2, '/'), (3, '\\'), (0, '/'), (5, '\\')])
    ops = [window(k, ub, 1.5, tw, 0.7, 0.9), window(k, ub, 4.0, tw, 0.7, 0.9, shutters='l'),
           window(k, ub, 6.5, tw, 0.7, 0.9, shutters='r')]
    frame_wall(k, ub, posts=[0.9, 2.1, 3.4, 4.6, 5.9, 7.1, 8.3], rails=[tw - 0.12], openings=ops, bw=B,
               braces=[(2, 'X'), (4, 'X'), (6, 'k'), (0, '/'), (7, '\\')])
    ops = [window(k, ul, 1.4, tw, 0.7, 0.9, shutters='l'), window(k, ul, 5.6, tw, 0.7, 0.9, shutters='r')]
    frame_wall(k, ul, posts=[0.8, 2.0, 2.7, 4.3, 5.0, 6.2], rails=[tw - 0.12], openings=ops, bw=B,
               braces=[(0, '/'), (6, '\\')])
    corner_posts(k, x0, y0, x1, y1, zg, zu1, bw=0.2)
    # ---- gables + main roof
    gr = Wall((x1, y0), (x1, y1), zu1, zu1)
    window(k, gr, 3.5, zu1 + 0.8, 0.6, 0.75, shutters=0)
    frame_gable(k, gr, rise, pattern='window', bw=B)
    frame_gable(k, Wall((x0, y1), (x0, y0), zu1, zu1), rise, pattern='grid', bw=B)
    og, tvm = 0.4, 0.16
    roof_gable(k, x0, x1, y0, y1, zu1, rise, oe=0.5, og=og, tv=tvm, sag=0.16, nu=8, nv=4, mat='M_roof_tiles',
               moss=0.9)
    purlin_ends(k, x1, 1, ym, half, zu1, rise, og)
    purlin_ends(k, x0, -1, ym, half, zu1, rise, og)
    for xc in (-4.3, -1.25, 1.8):
        dormer(k, xc, y0, zu1, slope, tvm)
    with k.xf(Matrix.Translation((0, ym, 0)) @ Matrix.Rotation(PI, 4, 'Z') @ Matrix.Translation((0, -ym, 0))):
        for xc in (3.0, -0.4):
            dormer(k, xc, y0, zu1, slope, tvm)
    # ---- chimneys
    k.box((x0 - 0.7, ym - 0.85, 0.0), (x0 + 0.05, ym + 0.85, 3.7), 'M_stone_wall', PAL['stone'], skip=('-z', '+x'),
          taper=(1.0, 0.92))
    k.box((x0 - 0.7, ym - 0.78, 3.7), (x0 + 0.05, ym + 0.78, 4.9), 'M_stone_wall', PAL['stone'], skip=('-z', '+x'),
          taper=(1.0, 0.6))
    chimney(k, x0 - 0.325, ym, 4.9, zr + 1.2, wx=0.75, wy=0.94, taper=0.9)
    chimney(k, 2.0, ym + 1.7, zu1 + 1.3, zr + 0.95, wx=0.85, wy=0.7, taper=0.93, smoke='SMOKE_kitchen')
    # ---- porch
    px0, px1, pyf = -5.2, 2.7, -4.5
    yp = pyf + 0.12
    k.box((px0, pyf, 0), (px1, y0, dk), 'M_wood_planks', PAL['plank'], skip=('-z', '+y'))
    k.box((px0 - 0.03, pyf - 0.04, 0), (px1 + 0.03, pyf + 0.1, dk - 0.03), 'M_stone_wall', PAL['stone_d'],
          skip=('-z', '+y'))
    k.box((dsx - 1.15, pyf - 0.5, 0), (dsx + 1.15, pyf - 0.04, 0.13), 'M_stone_wall', PAL['stone_d'],
          skip=('-z', '+y'), taper=(0.97, 0.95))
    pxs = [px0 + 0.12, -2.75, -0.25, 1.2, px1 - 0.12]
    zpl = 2.47
    for x in pxs:
        post(k, x, yp, dk, zpl - 0.09, w=0.17, base=False)
    k.beam((px0 - 0.12, yp, zpl), (px1 + 0.12, yp, zpl), 0.17, 0.18, 'M_wood_planks', k.jit(PAL['beam']))
    for i, x in enumerate(pxs):
        for sg in (-1, 1):
            if (i == 0 and sg < 0) or (i == len(pxs) - 1 and sg > 0):
                continue
            knee(k, (x, yp, zpl - 0.09), (sg, 0, 0), size=0.42, w=0.09)
        k.beam((x, y0, 3.42), (x, yp, zpl + 0.1), 0.1, 0.12, 'M_wood_planks', k.jit(PAL['beam_d']),
               skip=('c0', 'c1'))
    for (a, b, n) in ((0, 1, 4), (2, 3, 3), (3, 4, 3)):
        rail_bay(k, (pxs[a] + 0.09, yp), (pxs[b] - 0.09, yp), dk, n=n)
    rail_bay(k, (pxs[0], yp + 0.09), (pxs[0], y0), dk, n=4)
    roof_plane(k, (px0 - 0.3, pyf - 0.4, 2.36), (px1 + 0.3, pyf - 0.4, 2.36), (px1 + 0.3, y0 + 0.03, 3.5),
               (px0 - 0.3, y0 + 0.03, 3.5), tv=0.13, nu=5, nv=2, mat='M_roof_tiles', sag=0.07, moss=0.9)
    bench(k, (1.3, y0 - 0.3, dk), L=1.7)
    barrel(k, (px0 + 0.55, y0 - 0.5, dk), r=0.3, h=0.85, n=8)
    barrel(k, (px0 + 1.2, y0 - 0.42, dk), r=0.27, h=0.75, n=8)
    k.beam((dsx + 0.95, y0, 2.25), (dsx + 0.95, y0 - 0.32, 2.25), 0.03, 0.035, 'M_metal_iron', PAL['iron'], uv='box')
    lantern(k, (dsx + 0.95, y0 - 0.28, 2.24), hang=0.06)
    hanging_sign(k, 3.12, y0, 4.85)
    # ---- stable lean-to (+X)
    sx0, sx1, sy0, sy1 = x1, 6.0, -1.5, y1
    roof_plane(k, (sx1 + 0.35, sy0 - 0.3, 2.1), (sx1 + 0.35, sy1 + 0.25, 2.1), (sx0 + 0.02, sy1 + 0.25, 3.35),
               (sx0 + 0.02, sy0 - 0.3, 3.35), tv=0.13, nu=4, nv=2, mat='M_roof_tiles', sag=0.07, moss=0.9)
    sys_ = [sy0 + 0.1, 0.55, 2.5, sy1 - 0.1]
    for yy in sys_:
        post(k, sx1 - 0.1, yy, 0, 2.14, w=0.16)
        k.beam((sx0, yy, 3.2), (sx1 - 0.1, yy, 2.27), 0.1, 0.13, 'M_wood_planks', k.jit(PAL['beam_d']),
               skip=('c0', 'c1'))
    k.beam((sx1 - 0.1, sy0 - 0.2, 2.22), (sx1 - 0.1, sy1 + 0.15, 2.22), 0.15, 0.16, 'M_wood_planks',
           k.jit(PAL['beam']))
    knee(k, (sx1 - 0.1, sys_[0], 2.14), (0, 1, 0), size=0.4, w=0.09)
    knee(k, (sx1 - 0.1, sys_[1], 2.14), (0, -1, 0), size=0.4, w=0.09)
    bwl = Wall((sx1, sy1), (sx0, sy1), 0.0, 2.2)
    k.quad([bwl.P(0, 0), bwl.P(bwl.L, 0), bwl.P(bwl.L, 3.3), bwl.P(0, 2.2)], 'M_wood_planks', PAL['plank'])
    k.quad([bwl.P(bwl.L, 0, -0.04), bwl.P(0, 0, -0.04), bwl.P(0, 2.2, -0.04), bwl.P(bwl.L, 3.3, -0.04)],
           'M_wood_planks', PAL['plank_d'])
    for s in (0.5, 1.0, 1.5, 2.0):
        wbeam(k, bwl, s, 0, s, 2.2 + 1.1 * s / bwl.L, 0.055, 0.018, depth=0.03, col=k.jit(PAL['plank_d']))
    k.box((sx1 - 0.15, 0.6, 0.08), (sx1 - 0.09, sy1 - 0.15, 1.25), 'M_wood_planks', PAL['plank'], uv='swap')
    for yy in (0.55, 2.5):
        k.box((sx0 + 0.02, yy - 0.03, 0.05), (sx1 - 0.25, yy + 0.03, 1.35), 'M_wood_planks', k.jit(PAL['plank_d']),
              uv='swap', skip=('-z',))
    k.box((sx0 + 0.02, 0.75, 0.75), (sx0 + 0.42, 4.3, 1.0), 'M_wood_planks', k.jit(PAL['plank']), uv='swap',
          taper=(1.15, 1.0))
    k.blob((sx0 + 0.24, 1.6, 1.0), (0.2, 0.7, 0.16), nu=6, nv=2, mat='M_thatch', col=PAL['hay'], zmin=0.0)
    k.blob((sx0 + 0.24, 3.5, 1.0), (0.2, 0.6, 0.13), nu=6, nv=2, mat='M_thatch', col=PAL['hay'], zmin=0.0)
    k.blob((sx0 + 0.95, 3.85, 0.0), (0.75, 0.5, 0.5), nu=7, nv=3, mat='M_thatch', col=mulc(PAL['hay'], 0.92), zmin=0.0)
    trough_box(k, (sx0 + 1.3, sy0 - 0.75, 0), s=(1.3, 0.4, 0.34))
    for xx in (sx0 + 0.45, sx1 - 0.2):
        k.cyl((xx, sy0 - 1.6, 0), (xx, sy0 - 1.6, 1.08), 0.065, 0.055, n=6, mat='M_wood_planks', col=PAL['beam_l'])
    k.cyl((sx0 + 0.25, sy0 - 1.6, 1.0), (sx1, sy0 - 1.6, 1.0), 0.05, n=6, mat='M_wood_planks', col=PAL['beam_l'])
    # ---- nodes
    k.empty('ANCHOR_door', (dsx, pyf - 0.8, 0.0))
    k.empty('ANCHOR_npc', (0.2, -3.55, dk))
    k.walk('porch', (px0, pyf, 0), (px1, y0, dk))
    k.walk('step', (dsx - 1.15, pyf - 0.5, 0), (dsx + 1.15, pyf, 0.13))
    k.col('body', (x0 - 0.1, y0 - 0.05, 0), (x1 + 0.1, y1 + 0.1, zr))
    k.col('chimney', (x0 - 0.75, ym - 0.9, 0), (x0, ym + 0.9, zr + 1.2))
    k.col('stable', (sx0, 0.45, 0), (sx1 + 0.05, sy1 + 0.05, 2.4))
    k.person = (dsx + 0.3, pyf - 1.0)


# ----------------------------------------------------------------------------- forge
def hammer(k, p, rz=0.0, ry=0.0, L=0.4, head=(0.12, 0.05, 0.05)):
    with k.at(p, rz=rz, ry=ry):
        k.beam((0, 0, 0), (L, 0, 0), 0.028, 0.028, 'M_wood_planks', PAL['plank'], skip=('c0',))
        k.cbox((L, 0, 0), (head[1], head[0], head[2]), 'M_metal_iron', PAL['iron_l'])


def tongs(k, p, rz=0.0, ry=0.0, L=0.6):
    with k.at(p, rz=rz, ry=ry):
        for sg in (-1, 1):
            k.beam((0, sg * 0.035, 0), (L * 0.72, -sg * 0.012, 0), 0.016, 0.016, 'M_metal_iron', PAL['iron'],
                   uv='box', skip=('c1',))
            k.beam((L * 0.72, -sg * 0.012, 0), (L, sg * 0.03, 0), 0.02, 0.016, 'M_metal_iron', PAL['iron'], uv='box')


def horseshoe(k, p, r=0.065, rx=PI / 2, rz=0.0):
    with k.at(p, rx=rx, rz=rz):
        pts = [(r * math.cos(a), r * 1.15 * math.sin(a), 0) for a in
               [-0.25 * PI + 1.5 * PI * i / 5 for i in range(6)]]
        k.tube(pts, 0.012, n=3, mat='M_metal_iron', col=PAL['iron_l'])


def anvil(k, c, rz=0.0):
    with k.at(c, rz=rz):
        I, col = 'M_metal_iron', PAL['iron_l']
        k.box((-0.17, -0.11, 0), (0.17, 0.11, 0.07), I, col, taper=(0.85, 0.85))
        k.box((-0.10, -0.07, 0.07), (0.10, 0.07, 0.2), I, col, taper=(1.25, 1.0), skip=('-z', '+z'))
        k.box((-0.2, -0.075, 0.2), (0.24, 0.075, 0.31), I, mulc(col, 1.15))
        k.cyl((-0.2, 0, 0.265), (-0.46, 0, 0.3), 0.05, 0.008, n=6, mat=I, col=col, caps=(False, True), uv='box')


def stump(k, c, r=0.3, h=0.55):
    k.cyl((c[0], c[1], c[2]), (c[0], c[1], c[2] + h), r, r * 0.9, n=9, mat='M_bark_oak', col=PAL['bark'],
          caps=(False, True), cap_mat='M_wood_planks', cap_col=PAL['plank_l'])


def tub(k, c, r=0.38, h=0.5, n=10, water=True):
    col = PAL['plank']
    k.lathe(c, [(r * 0.86, 0), (r, h * 0.5), (r * 0.95, h), (r * 0.86, h), (r * 0.88, h * 0.72), (0.0, h * 0.72)],
            n=n, mat='M_wood_planks', col=k.jit(col), split=(2, 3, 4),
            colfn=lambda i, rr, zz: (0.02, 0.028, 0.035) if (water and i >= 4) else col)
    for fz in (0.2, 0.8):
        rr = r * (0.9 + 0.1 * math.sin(fz * PI)) + 0.006
        k.lathe(c, [(rr, h * fz - 0.025), (rr, h * fz + 0.025)], n=n, mat='M_metal_iron', col=PAL['iron'])


@asset('forge', 'Blacksmith workshop: open-front timber shed on stone walls, stone hearth with hood and chimney, '
       'bellows, anvil on a stump, quench tub, tool rack, workbench, grindstone',
       4000, footprint=[8.4, 7.6], bake=dict(ao_dist=1.5, warp=0.02))
def forge(k):
    x0, x1, y0, y1 = -3.5, 3.5, -3.0, 3.0
    ze = 2.75
    half = 3.0
    slope = math.tan(math.radians(40))
    rise = half * slope
    zr = ze + rise
    S, W = 'M_stone_wall', 'M_wood_planks'
    yi = y1 - 0.38                                     # inner face of the back wall
    # floor slab
    k.quad([(x0 - 0.1, y0 - 0.7, 0.025), (x1 + 0.1, y0 - 0.7, 0.025), (x1 + 0.1, yi, 0.025), (x0 - 0.1, yi, 0.025)],
           'M_cobble', PAL['stone_d'])
    # back wall (stone, full height) + low side walls
    k.box((x0, yi, 0), (x1, y1, ze), S, PAL['stone'], skip=('-z',), taper=(1.0, 0.94))
    for sg, xa, xb in ((-1, x0, x0 + 0.38), (1, x1 - 0.38, x1)):
        k.box((xa, y0 + 1.3, 0), (xb, yi, 1.15), S, PAL['stone'], skip=('-z', '+y'), taper=(0.92, 1.0))
    plinth_stones = [(x0, -0.5, 0.5), (x1, 1.0, 0.4), (-1.5, y1, 0.9), (1.9, y1, 1.6)]
    for (px, py, pz) in plinth_stones:
        k.cbox((px, py, pz), (0.42 if abs(py) == y1 else 0.1, 0.1 if abs(py) == y1 else 0.42, 0.24), S,
               k.jit(mulc(PAL['stone'], 0.95), 0.05, 0))
    # timber: posts, plates, ties
    pf = y0 + 0.11
    for x in (x0 + 0.12, 0.0, x1 - 0.12):
        post(k, x, pf, 0, ze - 0.18, w=0.2)
    for x in (x0 + 0.12, x1 - 0.12):
        post(k, x, y0 + 1.3 - 0.1, 0, ze - 0.18, w=0.18)
        k.box((x - 0.08, 0.6 - 0.08, 1.15), (x + 0.08, 0.6 + 0.08, ze - 0.18), W, k.jit(PAL['beam']),
              skip=('-z', '+z'), uv='along')
        k.beam((x, y0 - 0.05, ze - 0.09), (x, yi + 0.1, ze - 0.09), 0.17, 0.18, W, k.jit(PAL['beam']))
    k.beam((x0 - 0.05, pf, ze - 0.09), (x1 + 0.05, pf, ze - 0.09), 0.19, 0.18, W, k.jit(PAL['beam']))
    for x, sgs in ((x0 + 0.12, (1,)), (0.0, (-1, 1)), (x1 - 0.12, (-1,))):
        for sg in sgs:
            knee(k, (x, pf, ze - 0.18), (sg, 0, 0), size=0.6, w=0.11)
    for x in (0.0,):
        k.beam((x, y0, ze - 0.09), (x, yi + 0.1, ze - 0.09), 0.16, 0.17, W, k.jit(PAL['beam']), skip=('c0',))
    for x in (x0 + 0.12, 0.0, x1 - 0.12):
        k.beam((x, 0, ze), (x, 0, zr - 0.05), 0.13, 0.13, W, k.jit(PAL['beam']), skip=('c0', 'c1'))
        for sg in (-1, 1):
            k.beam((x, sg * (half - 0.25), ze + 0.05), (x, sg * 0.05, zr - 0.1), 0.1, 0.13, W, k.jit(PAL['beam_d']),
                   skip=('c0', 'c1'))
    k.beam((x0, 0, zr - 0.07), (x1, 0, zr - 0.07), 0.12, 0.15, W, k.jit(PAL['beam_d']), skip=('c0', 'c1'))
    # plank infill above the low walls (right: full, left: rear half only)
    for xa, ya in ((x1 - 0.2, y0 + 1.3), (x0 + 0.14, 0.6)):
        k.box((xa, ya, 1.15), (xa + 0.06, yi, ze), W, PAL['plank'], skip=('-z', '+z'))
    # gables
    for (w_, nrm) in ((Wall((x1, y0), (x1, y1), ze, ze), 1), (Wall((x0, y1), (x0, y0), ze, ze), -1)):
        frame_gable(k, w_, rise, pattern='king', infill=W, pcol=PAL['plank'], bw=0.15)
        xx = x1 - 0.03 if nrm > 0 else x0 + 0.03
        k.quad([(xx, y0, ze), (xx, y1, ze), (xx, 0, zr)], W, PAL['plank_d'], nh=(-nrm, 0, 0))
    if not os.environ.get('ARCH_NOROOF'):
        roof_gable(k, x0, x1, y0, y1, ze, rise, oe=0.5, og=0.36, tv=0.14, sag=0.1, nu=5, nv=3, mat='M_roof_tiles',
                   moss=0.8)
    # ---- hearth, hood, chimney
    hx0, hx1, hy0, hy1, hz = 1.1, x1 - 0.38, 1.4, yi, 0.85
    k.box((hx0, hy0, 0), (hx1, hy1, hz), S, PAL['stone'], skip=('-z', '+y', '+x'), taper=(1.0, 1.0))
    k.box((hx0, hy0, hz), (hx1, hy0 + 0.15, hz + 0.12), S, k.jit(PAL['stone'], 0.05, 0), skip=('-z',))
    k.box((hx0, hy0 + 0.15, hz), (hx0 + 0.15, hy1, hz + 0.12), S, k.jit(PAL['stone'], 0.05, 0), skip=('-z', '-y'))
    k.quad([(hx0 + 0.15, hy0 + 0.15, hz + 0.05), (hx1, hy0 + 0.15, hz + 0.05), (hx1, hy1, hz + 0.05),
            (hx0 + 0.15, hy1, hz + 0.05)], S, PAL['soot'])
    fx, fy = (hx0 + hx1) / 2 + 0.1, (hy0 + hy1) / 2 + 0.05
    k.quad([(fx + (0.42 + 0.08 * math.sin(i * 2.3)) * math.cos(a), fy + (0.33 + 0.06 * math.cos(i * 1.7)) * math.sin(a),
             hz + 0.075) for i, a in enumerate([2 * PI * j / 9 for j in range(9)])], 'M_ember', PAL['ember'],
           flag=NOAO)
    for i in range(6):
        a = i * 1.1
        em = (i % 2 == 0)
        k.blob((fx + 0.27 * math.cos(a), fy + 0.2 * math.sin(a), hz + 0.08), (0.09, 0.075, 0.07), nu=5, nv=2,
               mat='M_ember' if em else S, col=PAL['ember'] if em else PAL['dark'], zmin=0.0,
               flag=NOAO if em else 0)
    k.beam((fx - 0.75, fy - 0.2, hz + 0.19), (fx - 0.05, fy - 0.05, hz + 0.12), 0.03, 0.03, 'M_metal_iron',
           PAL['iron_l'], uv='box')
    k.box((hx0, hy0, hz + 0.12), (hx0 + 0.26, hy0 + 0.26, 1.95), S, PAL['stone'], skip=('-z', '+z'))
    hood0 = [(hx0 - 0.06, hy0 - 0.06, 1.95), (hx1, hy0 - 0.06, 1.95), (hx1, hy1, 1.95), (hx0 - 0.06, hy1, 1.95)]
    cxh, cyh = 2.35, 2.12
    hood1 = [(cxh - 0.42, cyh - 0.42, 3.05), (cxh + 0.42, cyh - 0.42, 3.05), (cxh + 0.42, cyh + 0.42, 3.05),
             (cxh - 0.42, cyh + 0.42, 3.05)]
    k.loft(hood0, hood1, S, PAL['stone'], caps=(True, False), cap_col=PAL['soot'])
    k.box((hx0 - 0.1, hy0 - 0.1, 1.83), (hx1, hy0 + 0.08, 1.97), W, k.jit(PAL['beam_d']), uv='swap')
    k.box((hx0 - 0.1, hy0 + 0.08, 1.83), (hx0 + 0.08, hy1, 1.97), W, k.jit(PAL['beam_d']))
    chimney(k, cxh, cyh, 3.05, zr + 0.95, wx=0.84, wy=0.84, taper=0.9)
    k.soot.append((V((fx, fy, 1.5)), 1.7, 0.8))
    k.empty('FIRE_forge', (fx, fy, hz + 0.18))
    # ---- bellows (left of the hearth, nozzle towards the fire)
    bx, by, bz = 0.25, fy, 0.98
    k.loft([(bx - 0.75, by - 0.36, bz - 0.02), (bx - 0.75, by + 0.36, bz - 0.02), (bx - 0.75, by + 0.36, bz + 0.34),
            (bx - 0.75, by - 0.36, bz + 0.34)],
           [(bx + 0.55, by - 0.07, bz + 0.0), (bx + 0.55, by + 0.07, bz + 0.0), (bx + 0.55, by + 0.07, bz + 0.07),
            (bx + 0.55, by - 0.07, bz + 0.07)], 'M_leather', PAL['leather'])
    for zz, tilt in ((bz - 0.035, 0.0), (bz + 0.355, 0.27)):
        k.loft([(bx - 0.8, by - 0.4, zz - 0.02), (bx - 0.8, by + 0.4, zz - 0.02), (bx - 0.8, by + 0.4, zz + 0.02),
                (bx - 0.8, by - 0.4, zz + 0.02)],
               [(bx + 0.57, by - 0.09, zz - 0.02 - tilt * 1.0), (bx + 0.57, by + 0.09, zz - 0.02 - tilt * 1.0),
                (bx + 0.57, by + 0.09, zz + 0.02 - tilt * 1.0), (bx + 0.57, by - 0.09, zz + 0.02 - tilt * 1.0)],
               W, k.jit(PAL['plank_d']))
    k.cyl((bx + 0.55, by, bz + 0.035), (hx0 + 0.3, by, hz + 0.16), 0.045, 0.02, n=6, mat='M_metal_iron',
          col=PAL['iron'], uv='box')
    for sy in (-1, 1):
        k.beam((bx - 0.55, by + sy * 0.5, 0), (bx - 0.55, by + sy * 0.5, 1.75), 0.09, 0.09, W, k.jit(PAL['beam']),
               skip=('c0',))
    k.beam((bx - 0.55, by - 0.58, 1.68), (bx - 0.55, by + 0.58, 1.68), 0.08, 0.08, W, k.jit(PAL['beam']))
    k.beam((bx - 1.25, by - 0.2, 1.55), (bx + 0.2, by - 0.2, 1.95), 0.05, 0.05, W, k.jit(PAL['beam_l']))
    k.tube([(bx - 1.2, by - 0.2, 1.56), (bx - 1.2, by - 0.2, 1.2)], 0.012, n=3)
    k.tube([(bx + 0.15, by - 0.2, 1.93), (bx - 0.6, by - 0.15, bz + 0.42)], 0.01, n=3, mat='M_metal_iron',
           col=PAL['iron'])
    # ---- anvil, tub, tools
    ax, ay = -0.55, -0.95
    stump(k, (ax, ay, 0), r=0.3, h=0.55)
    anvil(k, (ax, ay, 0.55), rz=0.35)
    hammer(k, (ax + 0.02, ay - 0.02, 0.55 + 0.335), rz=1.9, L=0.36)
    tub(k, (0.85, -0.25, 0))
    k.beam((0.72, -0.3, 0.3), (1.02, -0.05, 0.95), 0.02, 0.02, 'M_metal_iron', PAL['iron_l'], uv='box')
    # tool rack on the back wall
    k.box((-3.0, yi - 0.05, 1.78), (-0.2, yi, 1.9), W, k.jit(PAL['plank']), uv='swap', skip=('+y',))
    for i, xx in enumerate((-2.75, -2.4, -2.05)):
        hammer(k, (xx, yi - 0.07, 1.86), ry=PI / 2, rz=0, L=0.36 + 0.06 * i, head=(0.12 + 0.03 * i, 0.05, 0.05))
    for xx in (-1.65, -1.3):
        tongs(k, (xx, yi - 0.07, 1.84), ry=PI / 2, rz=PI / 2, L=0.6)
    for i, xx in enumerate((-0.95, -0.7, -0.45)):
        horseshoe(k, (xx, yi - 0.065, 1.72), rx=PI / 2)
    k.box((-0.1, yi - 0.03, 0.02), (-0.04, yi, 1.9), 'M_metal_iron', PAL['iron_l'], uv='box')
    k.box((0.02, yi - 0.03, 0.02), (0.07, yi, 1.6), 'M_metal_iron', PAL['iron'], uv='box')
    # workbench (left)
    wx0, wx1, wy0, wy1 = x0 + 0.42, x0 + 1.2, 0.75, 2.45
    k.box((wx0, wy0, 0.8), (wx1, wy1, 0.88), W, k.jit(PAL['plank']))
    for (xx, yy) in ((wx0 + 0.06, wy0 + 0.08), (wx1 - 0.06, wy0 + 0.08), (wx0 + 0.06, wy1 - 0.08),
                     (wx1 - 0.06, wy1 - 0.08)):
        k.box((xx - 0.04, yy - 0.04, 0), (xx + 0.04, yy + 0.04, 0.8), W, k.jit(PAL['beam']), skip=('-z', '+z'),
              uv='along')
    k.box((wx0 + 0.04, wy0 + 0.06, 0.22), (wx1 - 0.04, wy1 - 0.06, 0.26), W, k.jit(PAL['plank_d']))
    hammer(k, (wx0 + 0.2, wy0 + 0.3, 0.905), rz=0.6, L=0.34)
    tongs(k, (wx0 + 0.15, wy0 + 0.9, 0.89), rz=0.2, L=0.55)
    crate(k, ((wx0 + wx1) / 2, wy1 - 0.3, 0.88), (0.42, 0.32, 0.2), rz=0.1, slats=False)
    k.box((wx0 + 0.25, wy0 + 1.0, 0.885), (wx0 + 0.33, wy0 + 1.7, 0.9), 'M_metal_steel', PAL['steel'], uv='box')
    k.blob(((wx0 + wx1) / 2, wy0 + 0.5, 0.26), (0.2, 0.2, 0.2), nu=6, nv=3, mat='M_metal_iron', col=PAL['iron_l'],
           zmin=0.0)
    # grindstone (front left)
    gx, gy = -2.1, -1.55
    k.cyl((gx - 0.06, gy, 0.74), (gx + 0.06, gy, 0.74), 0.36, n=10, mat=S, col=PAL['stone_w'], uv='box')
    for sx in (-0.16, 0.16):
        for sy in (-1, 1):
            k.beam((gx + sx, gy + sy * 0.38, 0), (gx + sx, gy + sy * 0.03, 0.8), 0.06, 0.06, W, k.jit(PAL['beam']),
                   skip=('c0',))
    k.cyl((gx - 0.22, gy, 0.74), (gx + 0.3, gy, 0.74), 0.02, n=4, mat='M_metal_iron', col=PAL['iron'], uv='box')
    k.beam((gx + 0.3, gy, 0.74), (gx + 0.3, gy + 0.16, 0.66), 0.025, 0.025, 'M_metal_iron', PAL['iron'], uv='box')
    # coal heap, barrel, sacks, bar stock
    k.blob((0.55, yi - 0.55, 0.0), (0.5, 0.42, 0.32), nu=7, nv=3, mat='M_rock', col=(0.045, 0.043, 0.042), zmin=0.0)
    barrel(k, (x1 - 0.85, y0 + 1.75, 0), r=0.3, h=0.85, n=8)
    sack(k, (x1 - 0.8, y0 + 2.5, 0), r=0.26, h=0.5)
    sack(k, (x1 - 1.25, y0 + 2.2, 0.0), r=0.24, h=0.5, rz=0.7)
    for i in range(4):
        k.beam((x0 + 0.5 + i * 0.06, 0.3, 0.02), (x0 + 0.42, 0.3 - 0.05 * i, 1.75 - 0.05 * i), 0.03, 0.03,
               'M_metal_iron', k.jit(PAL['iron_l']), uv='box')
    lantern(k, (0.0, pf + 0.02, ze - 0.19), hang=0.25)
    # outside: rain barrel + log stack against the back wall, horseshoe sign on the front corner post
    barrel(k, (x0 + 0.5, y1 + 0.42, 0), r=0.32, h=0.9, n=8, lid=False)
    rr = 0.09
    for row in range(3):
        for i in range(8 - row):
            xx = -1.6 + (i + 0.5 * row) * rr * 2.1
            zz = rr + row * rr * 1.78
            k.cyl((xx, y1 + 0.06, zz), (xx, y1 + 0.7 + k.r(0, 0.08), zz), rr * k.r(0.85, 1.05), n=5,
                  mat='M_bark_oak', col=PAL['bark'], caps=(False, True), cap_mat='M_wood_planks',
                  cap_col=k.jit(PAL['plank_l'], 0.15))
    k.beam((x0 + 0.12, pf - 0.1, 2.35), (x0 + 0.12, pf - 0.75, 2.35), 0.03, 0.035, 'M_metal_iron', PAL['iron'],
           uv='box')
    k.tube([(x0 + 0.12, pf - 0.62, 2.34), (x0 + 0.12, pf - 0.62, 2.18)], 0.008, n=3, mat='M_metal_iron',
           col=PAL['iron'])
    with k.at((x0 + 0.12, pf - 0.62, 2.0), rz=PI / 2, rx=PI / 2):
        pts = [(0.17 * math.cos(a), 0.2 * math.sin(a), 0) for a in [-0.3 * PI + 1.6 * PI * i / 7 for i in range(8)]]
        k.tube(pts, 0.03, n=4, mat='M_metal_iron', col=PAL['iron_l'])
    k.empty('ANCHOR_npc', (ax - 0.15, ay - 0.85, 0.0))
    k.empty('ANCHOR_door', (0.9, y0 - 0.8, 0.0))
    k.col('back', (x0, yi, 0), (x1, y1, ze))
    k.col('left', (x0, y0 + 1.2, 0), (x0 + 0.4, yi, ze))
    k.col('right', (x1 - 0.4, y0 + 1.2, 0), (x1, yi, ze))
    k.col('hearth', (bx - 0.85, hy0 - 0.1, 0), (hx1, yi, 2.0))
    k.col('anvil', (ax - 0.4, ay - 0.35, 0), (ax + 0.4, ay + 0.35, 0.9))
    k.person = (ax - 0.15, ay - 0.9)
