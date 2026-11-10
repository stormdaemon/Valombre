"""VALOMBRE settlements pack - village houses + barn (uses arch_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *


def rect_walls(x0, y0, x1, y1, z0, z1):
    """front (-Y), right (+X), back (+Y), left (-X) walls of a rectangle, counter-clockwise."""
    return (Wall((x0, y0), (x1, y0), z0, z1), Wall((x1, y0), (x1, y1), z0, z1),
            Wall((x1, y1), (x0, y1), z0, z1), Wall((x0, y1), (x0, y0), z0, z1))


def door_reveal(k, w, s, hw, zp, col=None):
    """Dark strip behind a door where the plinth is interrupted."""
    k.quad([w.P(s - hw, 0.0), w.P(s + hw, 0.0), w.P(s + hw, zp), w.P(s - hw, zp)], 'M_plaster',
           mulc(col or PAL['plaster'], 0.5))


def purlin_ends(k, x, sg, ym, half, z_eave, rise, og, n=3):
    """Purlin / ridge-beam stubs poking out under a gable verge (gable plane at x, outward sign sg)."""
    for i in range(n):
        f = i / (n - 1) if n > 1 else 0.5
        for sy in ((-1, 1) if f < 0.999 else (1,)):
            yy = ym + sy * half * (1 - f) * 0.92
            zz = z_eave + rise * (1 - (1 - f) * 0.92) - 0.13
            k.beam((x, yy, zz), (x + sg * (og - 0.03), yy, zz), 0.13, 0.15, 'M_wood_planks', k.jit(PAL['beam_d']),
                   skip=('c0',))


def jetty(k, x0, x1, y0, yf, zj, zu0, nj, knees=()):
    """Joist ends + soffit + knee braces of a front (-Y) jetty."""
    for i in range(nj):
        x = lerp(x0 + 0.065, x1 - 0.065, i / (nj - 1))
        k.beam((x, y0, zj + 0.09), (x, yf - 0.035, zj + 0.09), 0.13, 0.18, 'M_wood_planks', k.jit(PAL['beam_d']),
               skip=('c0', '+u'))
    k.quad([(x0, yf, zu0 - 0.01), (x0, y0, zu0 - 0.01), (x1, y0, zu0 - 0.01), (x1, yf, zu0 - 0.01)],
           'M_wood_planks', PAL['plank_d'], uv='swap')
    for s in knees:
        x = x0 + s
        k.beam((x, y0 - 0.03, zj - 0.62), (x, yf + 0.05, zj - 0.03), 0.12, 0.13, 'M_wood_planks',
               k.jit(PAL['beam']), up=(1, 0, 0))


# ----------------------------------------------------------------------------- house_a
@asset('house_a', 'Small single-storey thatched cottage, half-timbered on a rubble plinth, gable chimney',
       2500, footprint=[7.6, 6.2], bake=dict(ao_dist=1.6, warp=0.025))
def house_a(k):
    x0, x1, y0, y1 = -3.0, 3.0, -2.5, 2.5
    zp, ze = 0.42, 2.6
    rise = 2.5 * math.tan(math.radians(50))
    wf, wr, wb, wl = rect_walls(x0, y0, x1, y1, zp, ze)
    ds = 2.05                                       # door centre along the front wall
    plinth(k, x0, y0, x1, y1, h=zp, gaps=[(0, ds - 0.62, ds + 0.62)], stones=7)
    # front
    ops = [door(k, wf, ds, t0=0.1, ww=0.96, hh=1.98),
           window(k, wf, 4.45, 1.2, 0.72, 0.78)]
    door_reveal(k, wf, ds, 0.62, zp)
    frame_wall(k, wf, posts=[1.25, 2.85, 3.65, 5.25], rails=[1.08], braces=[(0, '\\'), (4, '/')], openings=ops)
    # right gable wall (chimney side)
    ops = [window(k, wr, 1.2, 1.25, 0.6, 0.7, shutters='l')]
    frame_wall(k, wr, posts=[1.9, 3.1], rails=[1.08], braces=[(2, '/')], openings=ops)
    frame_gable(k, Wall((x1, y0), (x1, y1), ze, ze), rise, pattern='king')
    # back
    ops = [window(k, wb, 1.5, 1.25, 0.6, 0.7), window(k, wb, 4.4, 1.25, 0.6, 0.7, shutters='r')]
    frame_wall(k, wb, posts=[0.75, 2.25, 3.0, 3.65, 5.15], rails=[1.08], braces=[(2, 'X')], openings=ops)
    # left gable wall
    ops = [window(k, wl, 2.5, 1.2, 0.8, 0.8)]
    frame_wall(k, wl, posts=[1.25, 1.85, 3.15, 3.75], rails=[1.08], braces=[(0, '\\'), (4, '/')], openings=ops)
    gw = Wall((x0, y1), (x0, y0), ze, ze)
    frame_gable(k, gw, rise, pattern='fan')
    corner_posts(k, x0, y0, x1, y1, zp, ze)
    # thatched roof
    roof_gable(k, x0, x1, y0, y1, ze, rise, oe=0.42, og=0.32, tv=0.5, sag=0.16, nu=6, nv=3, mat='M_thatch',
               under_mat='M_thatch', undercut=0.16, wob=0.04, moss=1.0, bulge=0.07, round_eave=0.1)
    # external gable chimney (+X)
    cy = 0.35
    k.box((x1 - 0.05, cy - 0.65, 0.0), (x1 + 0.62, cy + 0.65, 3.3), 'M_stone_wall', PAL['stone'], skip=('-z', '-x'),
          taper=(1.0, 0.9))
    k.box((x1 - 0.05, cy - 0.585, 3.3), (x1 + 0.62, cy + 0.585, 4.3), 'M_stone_wall', PAL['stone'],
          skip=('-z', '-x'), taper=(1.0, 0.62))
    chimney(k, x1 + 0.285, cy, 4.3, 6.75, wx=0.67, wy=0.72, taper=0.9)
    # lived-in clutter: rain barrel at the corner, firewood against the back wall, bench by the door
    barrel(k, (x0 + 0.25, y0 - 0.42, 0), r=0.3, h=0.85, n=8, lid=False)
    k.quad([(x0 + 0.25 + 0.26 * math.cos(a), y0 - 0.42 + 0.26 * math.sin(a), 0.74)
            for a in [2 * PI * i / 8 for i in range(8)]], 'M_wood_planks', PAL['dark'], flag=NOAO)
    rr = 0.08
    for row in range(3):
        for i in range(7 - row):
            xx = x1 - 2.3 + (i + 0.5 * row) * rr * 2.1
            zz = rr + row * rr * 1.78
            k.cyl((xx, y1 + 0.08, zz), (xx, y1 + 0.62 + k.r(0, 0.06), zz), rr * k.r(0.85, 1.05), n=5,
                  mat='M_bark_oak', col=PAL['bark'], caps=(False, True), cap_mat='M_wood_planks',
                  cap_col=k.jit(PAL['plank_l'], 0.15))
    bx = x0 + 4.45
    k.box((bx - 0.65, y0 - 0.5, 0.42), (bx + 0.65, y0 - 0.14, 0.47), 'M_wood_planks', PAL['plank'], uv='swap')
    for sx in (-0.5, 0.5):
        k.box((bx + sx - 0.04, y0 - 0.46, 0.0), (bx + sx + 0.04, y0 - 0.18, 0.42), 'M_wood_planks',
              k.jit(PAL['plank_d']), skip=('-z', '+z'))
    k.empty('ANCHOR_door', (x0 + ds, y0 - 0.8, 0.0))
    k.col('body', (x0 - 0.12, y0 - 0.12, 0), (x1 + 0.12, y1 + 0.12, 5.8))
    k.col('chimney', (x1, cy - 0.7, 0), (x1 + 0.68, cy + 0.7, 6.9))
    k.person = (x0 + ds + 1.0, y0 - 0.9)


# ----------------------------------------------------------------------------- house_b
@asset('house_b', 'Two-storey half-timbered house with jettied upper floor, clay tile roof and stone chimney',
       3500, footprint=[8.2, 7.8], bake=dict(ao_dist=1.6, warp=0.025))
def house_b(k):
    x0, x1, y0, y1 = -3.5, 3.5, -3.0, 3.0
    zp, zj = 0.45, 2.95
    zu0 = zj + 0.18
    zu1 = zu0 + 2.45
    jet = 0.45
    yf = y0 - jet
    half = (y1 - yf) / 2
    ym = (y1 + yf) / 2
    rise = half * math.tan(math.radians(48))
    ds = 2.3
    plinth(k, x0, y0, x1, y1, h=zp, gaps=[(0, ds - 0.66, ds + 0.66)], stones=8)
    wf = Wall((x0, y0), (x1, y0), zp, zj)
    wr = Wall((x1, y0), (x1, y1), zp, zu0)
    wb = Wall((x1, y1), (x0, y1), zp, zu0)
    wl = Wall((x0, y1), (x0, y0), zp, zu0)
    # ---- ground floor
    ops = [door(k, wf, ds, t0=0.12, ww=1.04, hh=2.0),
           window(k, wf, 0.78, 1.3, 0.55, 0.8, shutters=0),
           window(k, wf, 4.9, 1.22, 1.1, 0.95, bars=(2, 1))]
    door_reveal(k, wf, ds, 0.66, zp)
    frame_wall(k, wf, posts=[1.45, 3.15, 4.12, 5.68], rails=[1.12], braces=[(4, '/')], openings=ops, bw=0.16)
    ops = [window(k, wr, 1.5, 1.3, 0.65, 0.8, shutters='r'), window(k, wr, 4.4, 1.3, 0.65, 0.8, shutters=0)]
    frame_wall(k, wr, posts=[0.9, 2.1, 3.0, 3.8, 5.0], rails=[1.12], braces=[(2, 'X', zp + 0.16, 1.05)],
               openings=ops, bw=0.16)
    ops = [window(k, wb, 1.6, 1.3, 0.65, 0.8), window(k, wb, 5.3, 1.3, 0.65, 0.8, shutters='l')]
    frame_wall(k, wb, posts=[0.85, 2.35, 3.1, 3.9, 4.65, 5.95], rails=[1.12], braces=[(3, 'X'), (0, '\\'), (6, '/')],
               openings=ops, bw=0.16)
    ops = [window(k, wl, 3.0, 1.3, 0.7, 0.8, shutters=0)]
    frame_wall(k, wl, posts=[1.2, 2.4, 3.6, 4.8], rails=[1.12], braces=[(0, '\\'), (4, '/')], openings=ops, bw=0.16)
    corner_posts(k, x0, y0, x1, y1, zp, zu0, bw=0.19)
    jetty(k, x0, x1, y0, yf, zj, zu0, 13, knees=(0.1, 1.45, 3.15, 5.68, 6.9))
    # ---- upper floor
    uf = Wall((x0, yf), (x1, yf), zu0, zu1)
    ur = Wall((x1, yf), (x1, y1), zu0, zu1)
    ub = Wall((x1, y1), (x0, y1), zu0, zu1)
    ul = Wall((x0, y1), (x0, yf), zu0, zu1)
    tw = zu0 + 0.98
    ops = [window(k, uf, s, tw, 0.75, 0.95) for s in (1.4, 3.5, 5.6)]
    frame_wall(k, uf, posts=[0.8, 2.0, 2.9, 4.1, 5.0, 6.2], rails=[tw - 0.12], openings=ops, bw=0.16, sill=False,
               braces=[(2, 'X', zu0 + 0.2, tw - 0.2), (4, 'X', zu0 + 0.2, tw - 0.2), (0, '/'), (6, '\\')])
    wbeam(k, uf, -0.05, zu0 + 0.1, uf.L + 0.05, zu0 + 0.1, 0.24, 0.055, depth=0.1, col=k.jit(PAL['beam_d']),
          caps=(True, True))
    ops = [window(k, ur, 2.0, tw, 0.7, 0.9), window(k, ur, 4.7, tw, 0.7, 0.9, shutters='l')]
    frame_wall(k, ur, posts=[1.1, 2.9, 3.8, 5.6], rails=[tw - 0.12], openings=ops, bw=0.16,
               braces=[(2, 'X'), (0, '/'), (4, '\\')])
    ops = [window(k, ub, 1.7, tw, 0.7, 0.9, shutters='r'), window(k, ub, 5.2, tw, 0.7, 0.9)]
    frame_wall(k, ub, posts=[0.9, 2.5, 3.5, 4.3, 6.1], rails=[tw - 0.12], openings=ops, bw=0.16,
               braces=[(2, 'k'), (0, '/'), (5, '\\')])
    ops = [window(k, ul, 3.3, tw, 0.75, 0.9)]
    frame_wall(k, ul, posts=[1.3, 2.5, 4.1, 5.3], rails=[tw - 0.12], openings=ops, bw=0.16,
               braces=[(0, '/'), (4, '\\'), (1, 'k'), (3, 'k')])
    corner_posts(k, x0, yf, x1, y1, zu0, zu1, bw=0.19)
    # ---- gables
    gr = Wall((x1, yf), (x1, y1), zu1, zu1)
    window(k, gr, gr.L / 2, zu1 + 0.75, 0.6, 0.75, shutters=0)
    frame_gable(k, gr, rise, pattern='window', bw=0.16)
    gl = Wall((x0, y1), (x0, yf), zu1, zu1)
    frame_gable(k, gl, rise, pattern='king', bw=0.16)
    og = 0.34
    roof_gable(k, x0, x1, yf, y1, zu1, rise, oe=0.42, og=og, tv=0.15, sag=0.12, nu=6, nv=3, mat='M_roof_tiles',
               moss=0.9)
    purlin_ends(k, x1, 1, ym, half, zu1, rise, og)
    purlin_ends(k, x0, -1, ym, half, zu1, rise, og)
    # ---- chimney through the back slope
    chimney(k, 1.55, ym + 1.05, zu1 + 1.6, zu1 + rise + 1.15, wx=1.0, wy=0.72, taper=0.93)
    k.empty('ANCHOR_door', (x0 + ds, y0 - 0.8, 0.0))
    k.col('body', (x0 - 0.12, yf, 0), (x1 + 0.12, y1 + 0.12, zu1 + rise))
    k.person = (x0 + ds + 1.1, yf - 0.7)


# ----------------------------------------------------------------------------- house_c
@asset('house_c', 'Long thatched farmhouse (hipped west end) with an open plank lean-to shed on the east gable',
       3500, footprint=[11.6, 6.8], bake=dict(ao_dist=1.6, warp=0.03))
def house_c(k):
    x0, x1, y0, y1 = -5.0, 3.0, -2.75, 2.75
    zp, ze = 0.4, 2.55
    half = 2.75
    slope = math.tan(math.radians(48))
    rise = half * slope
    d1, d2 = 4.7, 1.55                               # main door / byre door (s along the front wall)
    plinth(k, x0, y0, x1, y1, h=zp, gaps=[(0, d1 - 0.62, d1 + 0.62), (0, d2 - 0.79, d2 + 0.79)], stones=8)
    wf, wr, wb, wl = rect_walls(x0, y0, x1, y1, zp, ze)
    pc = PAL['plaster_o']
    ops = [door(k, wf, d1, t0=0.1, ww=0.96, hh=1.95),
           door(k, wf, d2, t0=0.06, ww=1.3, hh=1.8, planks=6, col=PAL['plank_d'], handle=False),
           window(k, wf, 3.1, 1.35, 0.5, 0.55, shutters=0, bars=(1, 0)),
           window(k, wf, 6.6, 1.2, 0.7, 0.75)]
    door_reveal(k, wf, d1, 0.62, zp, pc)
    door_reveal(k, wf, d2, 0.79, zp, pc)
    frame_wall(k, wf, posts=[0.7, 2.4, 3.85, 5.5, 7.2], rails=[1.15], braces=[(0, '\\'), (5, '/')], openings=ops,
               pcol=pc)
    ops = [window(k, wr, 1.0, 1.25, 0.55, 0.65, shutters=0)]
    frame_wall(k, wr, posts=[1.8, 3.2, 4.4], rails=[1.15], openings=ops, pcol=pc)
    frame_gable(k, Wall((x1, y0), (x1, y1), ze, ze), rise, pattern='grid', pcol=pc)
    ops = [window(k, wb, 1.4, 1.3, 0.55, 0.6, shutters='r'), window(k, wb, 4.2, 1.3, 0.55, 0.6, shutters=0),
           window(k, wb, 6.7, 1.3, 0.55, 0.6, shutters='l')]
    frame_wall(k, wb, posts=[0.7, 2.1, 2.8, 3.5, 4.9, 6.0, 7.4], rails=[1.15], braces=[(2, '/'), (5, '\\')],
               openings=ops, pcol=pc)
    ops = [window(k, wl, 2.75, 1.25, 0.6, 0.65)]
    frame_wall(k, wl, posts=[1.2, 2.0, 3.5, 4.3], rails=[1.15], braces=[(0, '\\'), (4, '/')], openings=ops, pcol=pc)
    corner_posts(k, x0, y0, x1, y1, zp, ze)
    # ---- thatch: gable at +X, hip at -X
    oe, og, tv, sag = 0.45, 0.32, 0.5, 0.2
    ze_, zr = ze - oe * slope, ze + rise
    xh = x0 + half
    kw = dict(tv=tv, nv=3, mat='M_thatch', under_mat='M_thatch', undercut=0.16, wob=0.045, bulge=0.07,
              round_eave=0.1)
    roof_plane(k, (x0 - oe, y0 - oe, ze_), (x1 + og, y0 - oe, ze_), (x1 + og, 0, zr), (xh, 0, zr), nu=7, sag=sag,
               edges=('eave', 'v1'), **kw)
    roof_plane(k, (x1 + og, y1 + oe, ze_), (x0 - oe, y1 + oe, ze_), (xh, 0, zr), (x1 + og, 0, zr), nu=7, sag=sag,
               edges=('eave', 'v0'), **kw)
    roof_plane(k, (x0 - oe, y1 + oe, ze_), (x0 - oe, y0 - oe, ze_), (xh, 0, zr), (xh, 0, zr), nu=4, sag=0.0,
               edges=('eave',), **kw)
    Lr = x1 + og - xh

    def zs(x):
        fu = clamp((x - xh) / Lr)
        return zr + tv - sag * 4 * fu * (1 - fu)
    ridge_roll(k, xh - 0.15, x1 + og, 0.0, zs, slope, thatch=True, nu=6)
    chimney(k, 0.9, 0.0, zr - 1.0, zr + 1.45, wx=0.95, wy=0.8, taper=0.92)
    # ---- lean-to shed on the east gable
    sx0, sx1, sy0, sy1 = x1, x1 + 2.0, y0 + 0.55, y1
    zt, zl = 3.05, 2.05
    roof_plane(k, (sx1 + 0.3, sy0 - 0.25, zl - 0.15), (sx1 + 0.3, sy1 + 0.2, zl - 0.15), (sx0 + 0.02, sy1 + 0.2, zt),
               (sx0 + 0.02, sy0 - 0.25, zt), tv=0.07, nu=3, nv=2, mat='M_wood_planks', col=PAL['plank_d'],
               under_col=PAL['beam_d'], sag=0.05, moss=0.8)
    for yy in (sy0, (sy0 + sy1) / 2, sy1 - 0.09):
        post(k, sx1 - 0.09, yy, 0, zl + 0.02, w=0.16)
    k.beam((sx1 - 0.09, sy0 - 0.2, zl + 0.03), (sx1 - 0.09, sy1 + 0.15, zl + 0.03), 0.14, 0.16, 'M_wood_planks')
    for yy in (sy0, sy1 - 0.09):
        k.beam((sx0, yy, zt - 0.12), (sx1, yy, zl), 0.12, 0.14, 'M_wood_planks')
    # back wall of the shed (sloping top) + half-height outer boards
    bw_ = Wall((sx1, sy1), (sx0, sy1), 0.0, zl)
    k.quad([bw_.P(0, 0), bw_.P(bw_.L, 0), bw_.P(bw_.L, zt - 0.1), bw_.P(0, zl)], 'M_wood_planks', PAL['plank'])
    k.quad([bw_.P(bw_.L, 0, -0.03), bw_.P(0, 0, -0.03), bw_.P(0, zl, -0.03), bw_.P(bw_.L, zt - 0.1, -0.03)],
           'M_wood_planks', PAL['plank_d'])
    for s in (0.5, 1.0, 1.5):
        wbeam(k, bw_, s, 0, s, zl + (zt - 0.1 - zl) * s / bw_.L, 0.055, 0.018, depth=0.03, col=k.jit(PAL['plank_d']))
    ow = Wall((sx1, sy0 + 0.1), (sx1, sy1 - 0.1), 0.0, 1.05)
    k.boards(ow.P(0, 0.12, -0.02), ow.d, V((0, 0, 1)), ow.L, 0.9, 4, thick=0.03, skip=(), col=PAL['plank'])
    # firewood stack + chopping block + barrel inside the shed
    rr = 0.085
    for row in range(4):
        for i in range(5 - (row % 2)):
            xx = sx0 + 0.25 + (i + 0.5 * (row % 2)) * rr * 2.1
            zz = rr + row * rr * 1.78
            cc = k.jit(PAL['plank_l'], 0.15)
            k.cyl((xx, sy1 - 0.12, zz), (xx, sy1 - 0.12 - 0.62 - k.r(0, 0.08), zz), rr * k.r(0.85, 1.05), n=5,
                  mat='M_bark_oak', col=PAL['bark'], caps=(False, True), cap_mat='M_wood_planks', cap_col=cc)
    k.cyl((sx0 + 0.75, sy0 + 0.9, 0), (sx0 + 0.75, sy0 + 0.9, 0.42), 0.24, 0.22, n=7, mat='M_bark_oak',
          col=PAL['bark'], caps=(False, True), cap_mat='M_wood_planks', cap_col=PAL['plank_l'])
    barrel(k, (sx0 + 1.45, sy0 + 2.3, 0), r=0.3, h=0.85, n=8)
    k.empty('ANCHOR_door', (x0 + d1, y0 - 0.8, 0.0))
    k.col('body', (x0 - 0.12, y0 - 0.12, 0), (x1 + 0.12, y1 + 0.12, zr))
    k.col('shed', (sx0, sy1 - 0.3, 0), (sx1 + 0.05, sy1 + 0.05, 2.3))
    k.col('shed_side', (sx1 - 0.2, sy0 - 0.1, 0), (sx1 + 0.05, sy1, 1.2))
    k.person = (x0 + d1 + 1.0, y0 - 0.9)


# ----------------------------------------------------------------------------- house_d
@asset('house_d', 'Narrow gable-fronted townhouse: jettied upper floor, shop window with counter and cloth awning',
       3000, footprint=[6.0, 9.2], bake=dict(ao_dist=1.6, warp=0.025))
def house_d(k):
    x0, x1, y0, y1 = -2.5, 2.5, -3.5, 3.5
    zp, zj = 0.4, 3.0
    zu0 = zj + 0.18
    zu1 = zu0 + 2.4
    jet = 0.4
    yf = y0 - jet
    half = 2.5
    rise = half * math.tan(math.radians(55))
    ds = 0.92
    pc = PAL['plaster_r']
    plinth(k, x0, y0, x1, y1, h=zp, gaps=[(0, ds - 0.6, ds + 0.6)], stones=6)
    wf = Wall((x0, y0), (x1, y0), zp, zj)
    wr = Wall((x1, y0), (x1, y1), zp, zu0)
    wb = Wall((x1, y1), (x0, y1), zp, zu0)
    wl = Wall((x0, y1), (x0, y0), zp, zu0)
    # ---- shop front
    sw, sh_, st = 3.35, 1.2, 1.12                     # shop window centre s, height, sill height
    ops = [door(k, wf, ds, t0=0.1, ww=0.92, hh=2.0),
           window(k, wf, sw, st, 1.9, sh_, shutters=0, bars=(3, 0), fw=0.11)]
    door_reveal(k, wf, ds, 0.6, zp, pc)
    frame_wall(k, wf, posts=[1.72, 4.6], rails=[st - 0.2, 2.55], openings=ops, pcol=pc, bw=0.16)
    # counter on brackets + goods
    cz = st - 0.12
    c0, c1 = wf.P(sw - 1.1, cz, 0.0), wf.P(sw + 1.1, cz, 0.0)
    k.box((c0.x, c0.y - 0.5, cz - 0.05), (c1.x, c0.y - 0.02, cz), 'M_wood_planks', PAL['plank'], uv='swap')
    for s in (sw - 0.85, sw + 0.85):
        p = wf.P(s, cz - 0.05, 0.0)
        k.beam((p.x, p.y - 0.02, cz - 0.5), (p.x, p.y - 0.42, cz - 0.05), 0.07, 0.08, 'M_wood_planks',
               k.jit(PAL['beam']), up=(1, 0, 0))
    for i, (dx, r) in enumerate(((-0.75, 0.13), (-0.42, 0.12), (-0.55, 0.11))):
        k.blob((c0.x + 1.1 + dx, c0.y - 0.27 + (0.1 if i == 2 else 0), cz + 0.05 + (0.1 if i == 2 else 0)),
               (r, r * 0.8, 0.08), nu=6, nv=3, mat='M_cloth', col=k.jit(PAL['bread'], 0.1), zmin=-0.6)
    for dx in (0.2, 0.5):
        k.lathe((c0.x + 1.1 + dx, c0.y - 0.27, cz), [(0.07, 0), (0.1, 0.1), (0.085, 0.2), (0.05, 0.24), (0.06, 0.28)],
                n=6, mat='M_roof_tiles', col=k.jit(PAL['tile_d'], 0.1), cap1=True)
    crate(k, (c0.x + 1.1 + 0.85, c0.y - 0.27, cz), (0.3, 0.28, 0.16), rz=0.2, slats=False)
    # awning (striped cloth) on two poles
    ax0, ax1 = c0.x - 0.1, c1.x + 0.1
    za, zb, reach = 2.72, 2.22, 1.25
    ns = 6
    for i in range(ns):
        xa, xb = lerp(ax0, ax1, i / ns), lerp(ax0, ax1, (i + 1) / ns)
        cc = PAL['red'] if i % 2 == 0 else PAL['white']
        rows = []
        for j in range(3):
            f = j / 2
            sg = -0.06 * math.sin(PI * f)
            rows.append([(xa, y0 - 0.04 - reach * f, lerp(za, zb, f) + sg),
                         (xb, y0 - 0.04 - reach * f, lerp(za, zb, f) + sg)])
        rows.append([(xa, y0 - 0.04 - reach, zb - 0.16), (xb, y0 - 0.04 - reach, zb - 0.16)])
        k.grid(rows, 'M_cloth', cc, double=True, smooth=False, flip=True, back_col=mulc(cc, 0.75))
    for xx in (ax0 + 0.03, ax1 - 0.03):
        k.cyl((xx, y0 - 0.03, zb - 0.55), (xx, y0 - 0.02 - reach, zb - 0.03), 0.028, n=5, col=PAL['beam_l'])
    k.cyl((ax0 - 0.05, y0 - 0.03 - reach, zb - 0.02), (ax1 + 0.05, y0 - 0.03 - reach, zb - 0.02), 0.025, n=5,
          col=PAL['beam_l'])
    # ---- other ground-floor walls
    ops = [window(k, wr, 2.0, 1.4, 0.6, 0.75, shutters=0), window(k, wr, 5.2, 1.4, 0.6, 0.75, shutters='r')]
    frame_wall(k, wr, posts=[1.2, 2.8, 3.6, 4.4, 6.0], rails=[1.2], braces=[(2, 'X', zp + 0.16, 1.13)],
               openings=ops, pcol=pc, bw=0.16)
    ops = [door(k, wb, 3.6, t0=0.42, ww=0.85, hh=1.9, step=False), window(k, wb, 1.5, 1.4, 0.6, 0.75)]
    frame_wall(k, wb, posts=[0.75, 2.3, 2.95, 4.25], rails=[1.2], openings=ops, pcol=pc, bw=0.16)
    k.box((x1 - 3.6 - 0.6, y1, 0), (x1 - 3.6 + 0.6, y1 + 0.75, 0.2), 'M_stone_wall', PAL['stone_d'], skip=('-z',))
    k.box((x1 - 3.6 - 0.55, y1, 0.2), (x1 - 3.6 + 0.55, y1 + 0.42, 0.42), 'M_stone_wall', PAL['stone_d'],
          skip=('-z',))
    ops = [window(k, wl, 3.5, 1.4, 0.6, 0.75, shutters=0)]
    frame_wall(k, wl, posts=[1.0, 2.2, 4.8, 6.0], rails=[1.2], braces=[(0, '\\'), (4, '/')], openings=ops,
               pcol=pc, bw=0.16)
    corner_posts(k, x0, y0, x1, y1, zp, zu0, bw=0.19)
    jetty(k, x0, x1, y0, yf, zj, zu0, 9, knees=(0.1, 1.72, 4.9))
    # ---- upper floor
    uf = Wall((x0, yf), (x1, yf), zu0, zu1)
    ur = Wall((x1, yf), (x1, y1), zu0, zu1)
    ub = Wall((x1, y1), (x0, y1), zu0, zu1)
    ul = Wall((x0, y1), (x0, yf), zu0, zu1)
    tw = zu0 + 0.95
    ops = [window(k, uf, 1.45, tw, 0.75, 0.95, shutters='l'), window(k, uf, 3.55, tw, 0.75, 0.95, shutters='r')]
    frame_wall(k, uf, posts=[0.85, 2.05, 2.5, 2.95, 4.15], rails=[tw - 0.12], openings=ops, pcol=pc, bw=0.16,
               sill=False, braces=[(2, '/', zu0 + 0.2, tw - 0.2), (3, '\\', zu0 + 0.2, tw - 0.2)])
    wbeam(k, uf, -0.05, zu0 + 0.1, uf.L + 0.05, zu0 + 0.1, 0.24, 0.055, depth=0.1, col=k.jit(PAL['beam_d']),
          caps=(True, True))
    ops = [window(k, ur, 2.4, tw, 0.65, 0.85, shutters=0), window(k, ur, 5.6, tw, 0.65, 0.85)]
    frame_wall(k, ur, posts=[1.3, 3.5, 4.5, 6.7], rails=[tw - 0.12], openings=ops, pcol=pc, bw=0.16,
               braces=[(2, 'X'), (0, '/')])
    ops = [window(k, ub, 2.5, tw, 0.8, 0.9)]
    frame_wall(k, ub, posts=[1.2, 1.8, 3.2, 3.8], rails=[tw - 0.12], openings=ops, pcol=pc, bw=0.16,
               braces=[(0, '/'), (4, '\\')])
    ops = [window(k, ul, 4.6, tw, 0.65, 0.85, shutters='l')]
    frame_wall(k, ul, posts=[1.2, 2.4, 3.6, 5.6, 6.4], rails=[tw - 0.12], openings=ops, pcol=pc, bw=0.16,
               braces=[(1, 'X'), (5, '\\')])
    corner_posts(k, x0, yf, x1, y1, zu0, zu1, bw=0.19)
    # ---- gables (front + back), roof ridge along Y
    gf = Wall((x0, yf), (x1, yf), zu1, zu1)
    window(k, gf, gf.L / 2, zu1 + 0.7, 0.6, 0.8, shutters=0)
    frame_gable(k, gf, rise, pattern='window', pcol=pc, bw=0.16)
    gb = Wall((x1, y1), (x0, y1), zu1, zu1)
    frame_gable(k, gb, rise, pattern='king', pcol=pc, bw=0.16)
    roof_gable(k, x0, x1, yf, y1, zu1, rise, oe=0.38, og=0.42, og2=0.28, tv=0.15, sag=0.1, nu=6, nv=3,
               mat='M_roof_tiles', axis='y', moss=0.9)
    # hoist beam at the front gable apex
    k.beam((0, yf + 0.05, zu1 + rise - 0.55), (0, yf - 0.7, zu1 + rise - 0.55), 0.13, 0.15, 'M_wood_planks',
           k.jit(PAL['beam_d']), skip=('c0',))
    k.tube([(0, yf - 0.6, zu1 + rise - 0.62), (0.01, yf - 0.6, zu1 + rise - 1.2), (0.0, yf - 0.6, zu1 + rise - 1.5)],
           0.015, n=3)
    k.cyl((0, yf - 0.6, zu1 + rise - 1.5), (0, yf - 0.6, zu1 + rise - 1.62), 0.03, 0.01, n=4, mat='M_metal_iron',
          col=PAL['iron'])
    chimney(k, x1 - 1.1, y1 - 1.6, zu1 + 0.9, zu1 + rise + 0.4, wx=0.7, wy=0.85, taper=0.93)
    k.empty('ANCHOR_door', (x0 + ds, y0 - 0.8, 0.0))
    k.empty('ANCHOR_npc', (x0 + sw, y0 - 1.0, 0.0))
    k.col('body', (x0 - 0.12, yf + 0.3, 0), (x1 + 0.12, y1 + 0.12, zu1 + rise))
    k.person = (x0 + ds + 0.2, yf - 1.3)


# ----------------------------------------------------------------------------- barn
@asset('barn', 'Timber barn on a stone plinth: board-and-batten walls, big double doors, hay-loft opening with '
       'hoist beam, thatched roof', 2500, footprint=[10.4, 8.4], bake=dict(ao_dist=1.8, warp=0.03))
def barn(k):
    x0, x1, y0, y1 = -4.5, 4.5, -3.5, 3.5
    zp, ze = 0.5, 3.4
    half = 4.5
    slope = math.tan(math.radians(46))
    rise = half * slope
    dw, dh = 3.0, 3.05
    plinth(k, x0, y0, x1, y1, h=zp, gaps=[(0, 4.5 - dw / 2 - 0.2, 4.5 + dw / 2 + 0.2)], stones=8)
    wf, wr, wb, wl = rect_walls(x0, y0, x1, y1, zp, ze)
    # front: double doors
    op = door(k, wf, 4.5, t0=0.04, ww=dw, hh=dh, planks=12, double=True, fw=0.2, handle=False, step=False,
              col=PAL['plank_d'])
    for (a, b) in ((4.5 - dw / 2, 4.5), (4.5, 4.5 + dw / 2)):      # Z braces on each leaf
        for tt in (0.45, dh - 0.35):
            wbeam(k, wf, a + 0.06, tt, b - 0.06, tt, 0.16, 0.06, depth=0.04, col=k.jit(PAL['plank']),
                  caps=(True, True))
        wbeam(k, wf, a + 0.1, 0.5, b - 0.1, dh - 0.4, 0.15, 0.052, depth=0.04, col=k.jit(PAL['plank']))
    k.quad([wf.P(4.5 - dw / 2 - 0.2, 0.0), wf.P(4.5 + dw / 2 + 0.2, 0.0), wf.P(4.5 + dw / 2 + 0.2, zp),
            wf.P(4.5 - dw / 2 - 0.2, zp)], 'M_wood_planks', PAL['dark'])
    k.box((-dw / 2 - 0.3, y0 - 0.9, 0), (dw / 2 + 0.3, y0, 0.05), 'M_stone_wall', PAL['stone_d'], skip=('-z', '+y'),
          taper=(0.97, 1.0))
    plank_wall(k, wf, posts=[1.4, 2.75, 6.25, 7.6], openings=[op], rails=())
    wbeam(k, wf, 0.2, zp + 0.3, 1.35, ze - 0.3, 0.13, 0.03, col=k.jit(PAL['beam']))
    wbeam(k, wf, 8.8, zp + 0.3, 7.65, ze - 0.3, 0.13, 0.03, col=k.jit(PAL['beam']))
    # sides + back
    for w in (wr, wl):
        plank_wall(k, w, posts=[1.75, 3.5, 5.25], rails=[zp + 1.5])
        for s in (0.875, 6.125):
            wbeam(k, w, s - 0.7, zp + 0.25, s + 0.7, zp + 1.4, 0.12, 0.028, col=k.jit(PAL['beam']))
        for s in (2.6, 4.4):
            k.quad([w.P(s - 0.09, 2.3, 0.006), w.P(s + 0.09, 2.3, 0.006), w.P(s + 0.09, 2.95, 0.006),
                    w.P(s - 0.09, 2.95, 0.006)], 'M_wood_planks', PAL['dark'], flag=NOAO)
    op = door(k, wb, 6.6, t0=0.5, ww=0.95, hh=1.9, step=False, col=PAL['plank_d'])
    k.box((x1 - 6.6 - 0.7, y1, 0), (x1 - 6.6 + 0.7, y1 + 0.8, 0.25), 'M_stone_wall', PAL['stone_d'], skip=('-z',))
    k.box((x1 - 6.6 - 0.65, y1, 0.25), (x1 - 6.6 + 0.65, y1 + 0.45, 0.5), 'M_stone_wall', PAL['stone_d'],
          skip=('-z',))
    plank_wall(k, wb, posts=[1.5, 3.0, 4.5, 7.6], openings=[op], rails=())
    corner_posts(k, x0, y0, x1, y1, zp, ze, bw=0.2)
    # gables (plank) - front with loft opening
    gf = Wall((x0, y0), (x1, y0), ze, ze)
    frame_gable(k, gf, rise, pattern='grid', infill='M_wood_planks', pcol=PAL['plank'], bw=0.17)
    lz = ze + 0.55
    k.quad([gf.P(3.85, lz, 0.008), gf.P(5.15, lz, 0.008), gf.P(5.15, lz + 1.35, 0.008), gf.P(3.85, lz + 1.35, 0.008)],
           'M_wood_planks', PAL['dark'], flag=NOAO)
    for (a, b, c, d) in ((3.78, lz, 3.78, lz + 1.42), (5.22, lz, 5.22, lz + 1.42)):
        wbeam(k, gf, a, b, c, d, 0.14, 0.06, depth=0.09, col=k.jit(PAL['beam_d']))
    wbeam(k, gf, 3.65, lz + 1.42, 5.35, lz + 1.42, 0.14, 0.07, depth=0.1, col=k.jit(PAL['beam_d']), caps=(True, True))
    wbeam(k, gf, 3.65, lz - 0.05, 5.35, lz - 0.05, 0.12, 0.09, depth=0.14, col=k.jit(PAL['beam_d']), caps=(True, True))
    # hay spilling out of the loft
    k.blob((0.1, y0 - 0.05, lz + 0.3), (0.6, 0.3, 0.42), nu=7, nv=3, mat='M_thatch', col=PAL['hay'], zmin=-0.5)
    k.blob((-0.35, y0 - 0.12, lz + 0.12), (0.3, 0.22, 0.2), nu=6, nv=3, mat='M_thatch', col=mulc(PAL['hay'], 0.9),
           zmin=-0.5)
    # hoist beam + rope + hook
    hz = ze + rise - 1.25
    k.beam((0, y0 + 0.1, hz), (0, y0 - 1.0, hz), 0.15, 0.17, 'M_wood_planks', k.jit(PAL['beam_d']), skip=('c0',))
    k.tube([(0, y0 - 0.85, hz - 0.08), (0.02, y0 - 0.85, hz - 0.9), (0.0, y0 - 0.85, hz - 1.5)], 0.016, n=3)
    k.cyl((0, y0 - 0.85, hz - 1.5), (0, y0 - 0.85, hz - 1.66), 0.035, 0.01, n=4, mat='M_metal_iron', col=PAL['iron'])
    gb = Wall((x1, y1), (x0, y1), ze, ze)
    frame_gable(k, gb, rise, pattern='king', infill='M_wood_planks', pcol=PAL['plank'], bw=0.17)
    roof_gable(k, x0, x1, y0, y1, ze, rise, oe=0.5, og=0.55, og2=0.35, tv=0.5, sag=0.22, nu=6, nv=3, mat='M_thatch',
               under_mat='M_thatch', undercut=0.16, wob=0.05, bulge=0.08, round_eave=0.1, axis='y')
    k.empty('ANCHOR_door', (0.0, y0 - 0.8, 0.0))
    k.col('body', (x0 - 0.12, y0 - 0.12, 0), (x1 + 0.12, y1 + 0.12, ze + rise))
    k.person = (2.3, y0 - 0.9)
