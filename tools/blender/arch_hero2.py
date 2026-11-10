"""VALOMBRE settlements pack - hero buildings 2: chapel, windmill, watchtower (uses arch_kit)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arch_kit import *
from arch_houses import rect_walls

S, W, I = 'M_stone_wall', 'M_wood_planks', 'M_metal_iron'


# ----------------------------------------------------------------------------- gothic bits
def arch_outline(ww, hs, q=1.0, n=4):
    """Pointed-arch outline (counter-clockwise seen from outside) in wall coords relative to the sill centre.
    hs = springing height, q = arc radius / width (1 = equilateral, >1 = lancet)."""
    R = ww * q
    cx = -ww / 2 + R
    a1 = math.acos(-cx / R)
    left = [(cx + R * math.cos(PI - (PI - a1) * i / n), hs + R * math.sin(PI - (PI - a1) * i / n))
            for i in range(n + 1)]
    right = [(-x, z) for (x, z) in left]
    return [(-ww / 2, 0.0), (ww / 2, 0.0)] + right + left[-2::-1]


def arch_surround(k, w, s, t, out, frame=0.14, proud=0.07, offset=0.0, col=None, mat=S, depth=0.12):
    """Stone moulding following an outline (all edges except the bottom one)."""
    col = col or PAL['stone_w']
    n = len(out)
    for i in range(1, n):
        a, b = V((out[i][0], out[i][1])), V((out[(i + 1) % n][0], out[(i + 1) % n][1]))
        d = (b - a).normalized()
        nr = V((d.y, -d.x)) * (frame / 2 + offset)
        a2, b2 = a + nr - d * 0.035, b + nr + d * 0.035
        o = proud - depth / 2
        k.beam(w.P(s + a2.x, t + a2.y, o), w.P(s + b2.x, t + b2.y, o), frame, depth, mat, k.jit(col, 0.05, 0.0),
               up=w.n, skip=('-u',), uv='box')


def lancet(k, w, s, t, ww=0.6, hs=1.6, q=1.25, n=4, frame=0.13, proud=0.06, glow=None, sill=True):
    out = arch_outline(ww, hs, q, n)
    k.quad([w.P(s + a, t + b, 0.012) for (a, b) in out], 'M_window_glow', glow or PAL['glow'], flag=NOAO)
    arch_surround(k, w, s, t, out, frame, proud)
    if sill:
        o = proud + 0.03 - 0.07
        k.beam(w.P(s - ww / 2 - frame - 0.04, t - frame / 2, o), w.P(s + ww / 2 + frame + 0.04, t - frame / 2, o),
               frame, 0.14, S, PAL['stone_w'], up=w.n, skip=('-u',), uv='box')
    # one vertical iron bar + two horizontal saddle bars
    k.beam(w.P(s, t, 0.02), w.P(s, t + hs + ww * 0.6, 0.02), 0.025, 0.02, I, PAL['iron'], up=w.n,
           skip=('-u', 'c0', 'c1'), uv='box')
    for f in (0.4, 0.85):
        k.beam(w.P(s - ww / 2, t + hs * f, 0.02), w.P(s + ww / 2, t + hs * f, 0.02), 0.025, 0.02, I, PAL['iron'],
               up=w.n, skip=('-u', 'c0', 'c1'), uv='box')


def rose(k, w, s, tc, r=0.72, n=12):
    """Round window: glowing disc, stone ring, hub and spokes."""
    M = Matrix((w.d, V((0, 0, 1)), w.n)).transposed().to_4x4()
    M.translation = w.P(s, tc, 0.0)
    with k.xf(M):
        k.quad([(r * math.cos(2 * PI * i / n), r * math.sin(2 * PI * i / n), 0.012) for i in range(n)],
               'M_window_glow', PAL['glow'], flag=NOAO)
        k.lathe((0, 0, 0), [(r + 0.2, -0.02), (r + 0.2, 0.1), (r + 0.03, 0.12), (r - 0.02, 0.0)], n=n, mat=S,
                col=PAL['stone_w'], smooth=False)
        k.lathe((0, 0, 0), [(0.2, 0.02), (0.2, 0.06), (0.12, 0.06), (0.12, 0.02)], n=6, mat=S, col=PAL['stone_w'],
                smooth=False)
        for i in range(6):
            a = 2 * PI * i / 6 + PI / 6
            k.beam((0.19 * math.cos(a), 0.19 * math.sin(a), 0.035), (r * math.cos(a), r * math.sin(a), 0.035), 0.06,
                   0.05, S, PAL['stone_w'], up=(0, 0, 1), skip=('-u', 'c0', 'c1'), uv='box')


def buttress(k, w, s, z0, z1, width=0.6, depth=0.6, cap=0.7, step=None, col=None):
    """Stepped buttress against a wall: body up to z1 - cap, then a sloping weathering back to the wall."""
    col = col or PAL['stone']
    a, b = s - width / 2, s + width / 2

    def ring(t, d):
        return [w.P(a, t, 0), w.P(a, t, d), w.P(b, t, d), w.P(b, t, 0)]
    zs = z1 - cap
    if step:
        zm = z0 + (zs - z0) * step
        k.loft(ring(z0, depth + 0.06), ring(zm, depth), S, col, caps=(False, False), skip=(3,))
        d2 = depth * 0.62
        k.loft(ring(zm, depth), [w.P(a, zm + 0.3, 0), w.P(a, zm + 0.3, d2), w.P(b, zm + 0.3, d2), w.P(b, zm + 0.3, 0)],
               S, mulc(col, 0.95), caps=(False, False), skip=(3,))
        k.loft(ring(zm + 0.3, d2), ring(zs, d2), S, col, caps=(False, False), skip=(3,))
        depth = d2
    else:
        k.loft(ring(z0, depth + 0.06), ring(zs, depth), S, col, caps=(False, False), skip=(3,))
    k.loft(ring(zs, depth), [w.P(a, z1, 0), w.P(a, z1, 0.02), w.P(b, z1, 0.02), w.P(b, z1, 0)], S, mulc(col, 0.95),
           caps=(False, False), skip=(3,))


def stone_cross(k, c, h=0.9, col=None, mat=S, axis='x', t=0.12):
    col = col or PAL['stone_w']
    x, y, z = c
    k.box((x - t / 2, y - t / 2, z), (x + t / 2, y + t / 2, z + h), mat, col, skip=('-z',))
    a = h * 0.3
    if axis == 'x':
        k.box((x - a, y - t / 2, z + h * 0.58), (x + a, y + t / 2, z + h * 0.58 + t), mat, col)
    else:
        k.box((x - t / 2, y - a, z + h * 0.58), (x + t / 2, y + a, z + h * 0.58 + t), mat, col)


# ----------------------------------------------------------------------------- chapel
@asset('chapel', 'Stone chapel: buttressed nave with lancet windows and slate roof, west bell tower with '
       'pointed-arch door, rose window, louvred belfry and slate spire',
       5000, footprint=[8.6, 13.4], bake=dict(ao_dist=2.0, warp=0.02, north_moss=0.5))
def chapel(k):
    x0, x1 = -3.5, 3.5
    yn0, y1 = -2.4, 6.0                      # nave
    tx0, tx1, ty0, ty1 = -1.9, 1.9, -6.0, -2.2   # tower
    zn, zt = 5.0, 9.6
    slate = PAL['slate']
    half = 3.5
    slope = math.tan(math.radians(52))
    rise = half * slope
    tcn = [0.0, 0.6, zn - 0.6, zn]
    # ---------------- nave
    plinth(k, x0, yn0, x1, y1, h=0.6, out=0.1, batter=0.05, stones=0, gaps=[(0, 1.6 - 0.1, 5.4 + 0.1)])
    wr = Wall((x1, yn0), (x1, y1), 0.0, zn)
    we = Wall((x1, y1), (x0, y1), 0.0, zn)
    wl = Wall((x0, y1), (x0, yn0), 0.0, zn)
    for w in (wr, wl):
        stone_wall(k, w, quoins=5, scuts=[0, 1.6, 4.2, 6.8, 8.4], tcuts=tcn)
        for s in (0.35, 2.9, 5.5, 8.05):
            buttress(k, w, s, 0.0, 4.3, width=0.62, depth=0.72, cap=0.8, step=0.52)
        for s in (1.62, 4.2, 6.78):
            lancet(k, w, s, 1.7, ww=0.55, hs=1.55, q=1.3)
        k.beam(w.P(-0.1, zn - 0.09, -0.02), w.P(w.L + 0.1, zn - 0.09, -0.02), 0.18, 0.24, S, PAL['stone_w'],
               up=w.n, skip=('-u',), uv='box')
    stone_wall(k, we, quoins=4, scuts=[0, 1.75, 3.5, 5.25, 7.0], tcuts=tcn)
    for s in (0.35, 6.65):
        buttress(k, we, s, 0.0, 4.3, width=0.62, depth=0.72, cap=0.8, step=0.52)
    lancet(k, we, 3.5, 1.7, ww=0.85, hs=2.3, q=1.25, frame=0.15)
    lancet(k, we, 2.15, 1.9, ww=0.5, hs=1.5, q=1.3)
    lancet(k, we, 4.85, 1.9, ww=0.5, hs=1.5, q=1.3)
    # west wall stubs either side of the tower + gables
    for (a, b) in (((x0, yn0), (tx0, yn0)), ((tx1, yn0), (x1, yn0))):
        stone_wall(k, Wall(a, b, 0.0, zn), quoins=1, scuts=[0, 1.6], tcuts=tcn)
    gable_tri(k, Wall((x0, yn0), (x1, yn0), zn, zn), rise)
    ge = Wall((x1, y1), (x0, y1), zn, zn)
    gable_tri(k, ge, rise)
    # small trefoil-ish oculus in the east gable
    k.quad([ge.P(3.5 + 0.28 * math.cos(2 * PI * i / 8), zn + 1.9 + 0.28 * math.sin(2 * PI * i / 8), 0.012)
            for i in range(8)], 'M_window_glow', PAL['glow'], flag=NOAO)
    M = Matrix((ge.d, V((0, 0, 1)), ge.n)).transposed().to_4x4()
    M.translation = ge.P(3.5, zn + 1.9, 0.0)
    with k.xf(M):
        k.lathe((0, 0, 0), [(0.42, -0.02), (0.42, 0.08), (0.3, 0.09), (0.27, 0.0)], n=8, mat=S, col=PAL['stone_w'],
                smooth=False)
    roof_gable(k, x0, x1, yn0, y1, zn, rise, oe=0.32, og=0.02, og2=0.12, tv=0.14, sag=0.1, nu=5, nv=3,
               mat='M_roof_tiles', col=slate, axis='y', barge=False, moss=1.0)
    zr = zn + rise
    # east gable coping + cross
    for sg in (-1, 1):
        k.beam((sg * (half + 0.3), y1 + 0.05, zn - 0.3 * slope + 0.12), (0, y1 + 0.05, zr + 0.2), 0.34, 0.16, S,
               PAL['stone_w'], up=(sg * slope, 0, 1.0), uv='box')
    stone_cross(k, (0, y1 + 0.05, zr + 0.2), h=1.0)
    # ---------------- tower
    plinth(k, tx0, ty0, tx1, ty1, h=0.6, out=0.1, batter=0.05, stones=0, sides=(0, 1, 3),
           gaps=[(0, 1.9 - 1.05, 1.9 + 1.05)])
    tf = Wall((tx0, ty0), (tx1, ty0), 0.0, zt)
    tr = Wall((tx1, ty0), (tx1, ty1), 0.0, zt)
    tb = Wall((tx1, ty1), (tx0, ty1), 0.0, zt)
    tl = Wall((tx0, ty1), (tx0, ty0), 0.0, zt)
    tct = [0.0, 0.6, 4.2, 7.4, zt]
    for w in (tf, tr, tb, tl):
        stone_wall(k, w, quoins=5 if w is not tb else 0, scuts=[0, 1.9, 3.8], tcuts=tct)
    for z in (4.2, 7.4):
        k.box((tx0 - 0.08, ty0 - 0.08, z), (tx1 + 0.08, ty1 + 0.08, z + 0.15), S, PAL['stone_w'])
    k.box((tx0 - 0.12, ty0 - 0.12, zt - 0.2), (tx1 + 0.12, ty1 + 0.12, zt), S, PAL['stone_w'])
    for w, ss in ((tf, (0.32, 3.48)), (tr, (0.32,)), (tl, (3.48,))):
        for s in ss:
            buttress(k, w, s, 0.0, 4.2, width=0.64, depth=0.55, cap=0.9, step=0.5)
    # door: pointed arch, two orders
    ds, dt = 1.9, 0.12
    out = arch_outline(1.5, 1.6, 1.0, 5)
    k.quad([tf.P(ds + a, dt + b, 0.03) for (a, b) in out], W, PAL['door'])
    k.quad([tf.P(ds - 0.012, dt, 0.034), tf.P(ds + 0.012, dt, 0.034), tf.P(ds + 0.012, dt + 2.85, 0.034),
            tf.P(ds - 0.012, dt + 2.85, 0.034)], W, PAL['dark'])
    arch_surround(k, tf, ds, dt, out, frame=0.2, proud=0.12, depth=0.16)
    arch_surround(k, tf, ds, dt, out, frame=0.1, proud=0.19, offset=0.2, depth=0.1, col=PAL['stone'])
    for sgn in (-1, 1):
        for tt in (0.45, 1.45):
            wbeam(k, tf, ds + sgn * 0.72, dt + tt, ds + sgn * 0.12, dt + tt, 0.07, 0.05, depth=0.02, col=PAL['iron'],
                  mat=I, sides=False)
        c = tf.P(ds + sgn * 0.14, dt + 1.0, 0.035)
        k.cyl(c, c + tf.n * 0.05, 0.045, 0.035, n=6, mat=I, col=PAL['iron_l'], caps=(False, True), uv='box')
    k.box((-1.25, ty0 - 1.0, 0), (1.25, ty0 - 0.1, 0.06), S, PAL['stone_d'], skip=('-z',), taper=(0.97, 0.97))
    k.box((-1.05, ty0 - 0.6, 0.06), (1.05, ty0, 0.12), S, PAL['stone_d'], skip=('-z', '+y'))
    rose(k, tf, 1.9, 5.8, r=0.72)
    for w in (tr, tl):
        k.quad([w.P(1.9 - 0.09, 5.2, 0.01), w.P(1.9 + 0.09, 5.2, 0.01), w.P(1.9 + 0.09, 6.2, 0.01),
                w.P(1.9 - 0.09, 6.2, 0.01)], S, PAL['dark'], flag=NOAO)
        wbeam(k, w, 1.9 - 0.25, 5.14, 1.9 + 0.25, 5.14, 0.1, 0.05, depth=0.1, col=PAL['stone_w'], mat=S,
              caps=(True, True))
    # belfry openings with louvres
    bo = arch_outline(0.85, 0.95, 1.0, 4)
    for w in (tf, tr, tb, tl):
        k.quad([w.P(1.9 + a, 7.8 + b, 0.012) for (a, b) in bo], W, PAL['dark'], flag=NOAO)
        arch_surround(k, w, 1.9, 7.8, bo, frame=0.13, proud=0.07)
        k.beam(w.P(1.9 - 0.6, 7.74, 0.02), w.P(1.9 + 0.6, 7.74, 0.02), 0.12, 0.14, S, PAL['stone_w'], up=w.n,
               skip=('-u',), uv='box')
        for i in range(4):
            tt = 7.95 + i * 0.3
            hwid = 0.42 if i < 3 else 0.33
            k.beam(w.P(1.9 - hwid, tt, 0.03), w.P(1.9 + hwid, tt, 0.03), 0.2, 0.025, W, k.jit(PAL['plank_d']),
                   up=(w.n + V((0, 0, 0.9))).normalized(), skip=('c0', 'c1'))
    cyt = (ty0 + ty1) / 2
    roof_hip(k, tx0, tx1, ty0, ty1, zt, 3.3, ridge_len=0.0, oh=0.3, tv=0.13, mat='M_roof_tiles', col=slate, nu=2,
             nv=3, moss=0.8)
    stone_cross(k, (0, cyt, zt + 3.3), h=0.85, col=PAL['iron_l'], mat=I, axis='x', t=0.06)
    # ---------------- nodes
    k.empty('GLOW_window', (0.0, ty0 - 0.6, 5.8))
    k.empty('ANCHOR_door', (0.0, ty0 - 0.9, 0.0))
    k.col('nave', (x0 - 0.15, yn0, 0), (x1 + 0.15, y1 + 0.15, zr))
    k.col('tower', (tx0 - 0.15, ty0 - 0.15, 0), (tx1 + 0.15, ty1 + 0.1, zt + 3.0))
    k.person = (1.6, ty0 - 1.0)


# ----------------------------------------------------------------------------- windmill
def sail(rb, spread=1.0):
    """One lattice sail pointing along local +Z from the hub (local Y = rotation axis)."""
    z0, z1 = 1.05, 4.9
    xl, xt = -0.28, 1.15

    def tw(z):       # weather (twist) of the sail
        return math.tan(math.radians(lerp(20, 6, (z - z0) / (z1 - z0))))
    rb.beam((0, 0, 0.1), (0, 0, z1 + 0.15), 0.14, 0.12, W, rb.jit(PAL['beam']), up=(0, 1, 0), taper=0.7)
    for x in (xl, (xl + xt) / 2 + 0.2, xt):
        rb.beam((x, x * tw(z0), z0), (x, x * tw(z1), z1), 0.045, 0.035, W, rb.jit(PAL['beam_l']), up=(0, 1, 0))
    nb = 9
    for i in range(nb):
        z = lerp(z0, z1, i / (nb - 1))
        rb.beam((xl, xl * tw(z), z), (xt, xt * tw(z), z), 0.04, 0.03, W, rb.jit(PAL['beam_l']), up=(0, 1, 0),
                skip=('c0', 'c1'))
    # canvas (spread fraction of the width, from the stock outwards)
    xc = lerp(0.08, xt - 0.03, spread)
    rows = []
    for j in range(5):
        z = lerp(z0 + 0.05, z1 - 0.05, j / 4)
        row = []
        for i in range(3):
            x = lerp(0.08, xc, i / 2)
            bil = 0.05 * math.sin(PI * i / 2) * math.sin(PI * j / 4) * spread
            row.append((x, x * tw(z) + 0.035 + bil, z))
        rows.append(row)
    rb.grid(rows, 'M_cloth', PAL['canvas'], double=True, smooth=True, back_col=mulc(PAL['canvas'], 0.8))


@asset('windmill', 'Smock windmill: round rubble-stone base, eight-sided boarded timber tower with gallery, '
       'boarded cap with tail pole; four lattice sails with canvas as separate ROT_blades',
       4000, footprint=[8.4, 9.0], bake=dict(ao_dist=1.8, warp=0.02))
def windmill(k):
    zb, zs, zc = 3.2, 8.6, 10.9
    rb0, rb1 = 3.0, 2.78              # stone base radii
    r0, r1 = 2.7, 1.72                # smock radii (to the corners)
    n8 = 8
    ph = PI / 8
    # stone base
    k.lathe((0, 0, 0), [(rb0 + 0.08, 0.0), (rb0, 0.45), ((rb0 + rb1) / 2, 1.8), (rb1, zb)], n=16, mat=S,
            col=PAL['stone'])
    for i in range(9):
        a = 0.5 + i * 0.71
        zz = 0.5 + (i * 0.83) % 2.2
        rr = lerp(rb0, rb1, zz / zb) - 0.02
        with k.at((rr * math.cos(a), rr * math.sin(a), zz), rz=a):
            k.cbox((0, 0, 0), (0.14, 0.5, 0.26), S, k.jit(mulc(PAL['stone'], 0.95), 0.05, 0), skip=('-x',))
    # smock tower (flat-shaded octagon) + cant posts + girts
    zl = [zb, 5.0, 6.8, zs]
    rl = [lerp(r0, r1, (z - zb) / (zs - zb)) for z in zl]
    k.lathe((0, 0, 0), list(zip(rl, zl)), n=n8, mat=W, col=PAL['plank'], smooth=False, phase=ph,
            colfn=lambda i, r, z: mulc(PAL['plank'], 1.0 - 0.06 * i))

    def corner(i, z, extra=0.0):
        r = lerp(r0, r1, (z - zb) / (zs - zb)) + extra
        a = ph + 2 * PI * i / n8
        return V((r * math.cos(a), r * math.sin(a), z))
    for i in range(n8):
        k.beam(corner(i, zb, 0.03), corner(i, zs, 0.03), 0.17, 0.17, W, k.jit(PAL['beam']),
               up=corner(i, zb).normalized(), skip=('c0', 'c1'))
        for z in (zb + 0.1, 5.0, 6.8, zs - 0.1):
            a, b = corner(i, z, 0.0), corner(i + 1, z, 0.0)
            nrm = ((a + b) * 0.5)
            nrm.z = 0
            nrm.normalize()
            k.beam(a + nrm * 0.02, b + nrm * 0.02, 0.14, 0.06, W, k.jit(PAL['beam']), up=nrm,
                   skip=('-u', 'c0', 'c1'))
    # windows on three faces (built in a face-aligned frame)
    for fi, zz in ((5, 5.6), (7, 7.3), (1, 6.0), (3, 4.2)):
        a, b = corner(fi, zz), corner(fi + 1, zz)
        mid = (a + b) * 0.5
        tang = (b - a).normalized()
        upv = (corner(fi, zz + 1) + corner(fi + 1, zz + 1)) * 0.5 - mid
        upv.normalize()
        outw = tang.cross(upv)
        Mx = Matrix((tang, outw * -1.0, upv)).transposed().to_4x4()
        Mx.translation = mid
        with k.xf(Mx):
            window(k, Wall((-1, 0), (1, 0), 0, 1), 1.0, 0.0, 0.45, 0.6, shutters=0, fw=0.07, bars=(1, 1))
    # gallery (stage) at the top of the stone base
    rg = 3.95
    k.lathe((0, 0, 0), [(rb1 - 0.1, zb - 0.12), (rg, zb - 0.12), (rg, zb), (rb1 - 0.1, zb)], n=16, mat=W,
            col=PAL['plank'], smooth=False)
    for i in range(16):
        a = 2 * PI * i / 16
        ca, sa = math.cos(a), math.sin(a)
        k.beam((ca * (rg - 0.08), sa * (rg - 0.08), zb), (ca * (rg - 0.08), sa * (rg - 0.08), zb + 1.0), 0.07, 0.07, W,
               k.jit(PAL['beam']), up=(ca, sa, 0), skip=('c0',))
        a2 = 2 * PI * (i + 1) / 16
        for zz, ww in ((zb + 0.98, 0.08), (zb + 0.5, 0.05)):
            k.beam((ca * (rg - 0.08), sa * (rg - 0.08), zz),
                   (math.cos(a2) * (rg - 0.08), math.sin(a2) * (rg - 0.08), zz), ww, 0.06, W, k.jit(PAL['beam_l']),
                   skip=('c0', 'c1'))
        if i % 2 == 0:
            rr = lerp(rb0, rb1, 1.9 / zb) - 0.03
            k.beam((ca * rr, sa * rr, 1.9), (ca * (rg - 0.25), sa * (rg - 0.25), zb - 0.12), 0.1, 0.1, W,
                   k.jit(PAL['beam']), up=(-sa, ca, 0))
    # ladder from the ground to the gallery (east side)
    lx = rg - 0.1
    for sy in (-0.24, 0.24):
        k.beam((lx + 1.15, sy, 0), (lx, sy, zb + 0.05), 0.05, 0.08, W, k.jit(PAL['plank']), up=(1, 0, 0.35))
    for i in range(10):
        f = (i + 0.7) / 10.5
        k.beam((lerp(lx + 1.15, lx, f), -0.24, zb * f), (lerp(lx + 1.15, lx, f), 0.24, zb * f), 0.04, 0.04, W,
               k.jit(PAL['plank_d']), skip=('c0', 'c1'))
    # cap (boarded, boat-like) + breast for the windshaft
    capc = mulc(PAL['plank_d'], 0.9)
    k.lathe((0, 0, 0), [(r1 + 0.28, zs - 0.05), (r1 + 0.34, zs + 0.2), (r1 + 0.2, zs + 0.95), (r1 * 0.72, zs + 1.75),
                        (r1 * 0.3, zc - 0.12), (0.0, zc)], n=10, mat=W, col=capc, sy=1.12, split=(1,))
    hub = V((0, -2.72, 9.55))
    k.box((-0.55, -2.25, hub.z - 0.5), (0.55, -1.2, hub.z + 0.55), W, capc, skip=('+y',), taper=(0.9, 1.0))
    k.cyl((0, -1.6, hub.z), (0, -2.42, hub.z), 0.21, 0.2, n=8, mat=W, col=PAL['beam'], caps=(False, False))
    k.cyl((0, 0, zc - 0.05), (0, 0, zc + 0.55), 0.05, 0.02, n=5, mat=W, col=PAL['beam_d'])
    # tail pole + braces
    tp0, tp1 = V((0, 1.7, zs + 0.9)), V((0, 5.3, zb + 1.1))
    k.beam(tp0, tp1, 0.15, 0.15, W, k.jit(PAL['beam']), up=(1, 0, 0))
    for sx in (-1, 1):
        k.beam((sx * 1.5, 0.9, zs + 0.5), tp0.lerp(tp1, 0.55), 0.09, 0.09, W, k.jit(PAL['beam']))
    k.beam(tp1 + V((-0.5, 0, 0.05)), tp1 + V((0.5, 0, 0.05)), 0.08, 0.08, W, k.jit(PAL['beam_l']))
    # door (stone porch block at the front)
    k.box((-0.95, -rb0 - 0.2, 0), (0.95, -2.5, 2.55), S, PAL['stone'], skip=('-z', '+y'), taper=(0.95, 1.0))
    dw = Wall((-0.95, -rb0 - 0.2), (0.95, -rb0 - 0.2), 0, 2.5)
    door(k, dw, 0.95, t0=0.08, ww=0.95, hh=1.95, fw=0.13)
    k.box((-1.05, -rb0 - 0.26, 2.55), (1.05, -2.5, 2.68), S, PAL['stone_w'], taper=(0.96, 1.0))
    # ---- rotating sails
    rb = k.sub('ROT_blades', hub)
    rb.bake_args = dict(ao_dist=0.5, dirt=0.0, ground=False)
    rb.cyl(hub + V((0, 0.35, 0)), hub + V((0, -0.42, 0)), 0.2, 0.17, n=8, mat=W, col=PAL['beam'])
    rb.cyl(hub + V((0, -0.42, 0)), hub + V((0, -0.56, 0)), 0.25, 0.22, n=8, mat=I, col=PAL['iron'], uv='box')
    for i in range(4):
        Mx = Matrix.Translation(hub + V((0, -0.2 - 0.06 * (i % 2), 0))) @ Matrix.Rotation(math.radians(17) + i * PI / 2,
                                                                                        4, 'Y')
        with rb.xf(Mx):
            sail(rb, spread=(1.0 if i % 2 == 0 else 0.45))
    k.empty('ANCHOR_door', (0.0, -rb0 - 1.0, 0.0))
    k.col('tower_a', (-2.75, -2.75, 0), (2.75, 2.75, zc))
    k.col('tower_b', (-2.75, -2.75, 0), (2.75, 2.75, zc), rz=PI / 4)
    k.person = (1.6, -rb0 - 1.0)


# ----------------------------------------------------------------------------- watchtower
def mini_brazier(k, c, r=0.24, h=0.8):
    x, y, z = c
    k.lathe((x, y, z), [(r * 0.35, h * 0.62), (r * 0.9, h * 0.8), (r, h), (r * 0.86, h), (r * 0.8, h * 0.9),
                        (0.0, h * 0.86)], n=7, mat=I, col=PAL['iron'], split=(2, 3),
            colfn=lambda i, rr, zz: PAL['soot'] if i >= 4 else PAL['iron'])
    k.quad([(x + r * 0.7 * math.cos(2 * PI * i / 6), y + r * 0.7 * math.sin(2 * PI * i / 6), z + h * 0.93)
            for i in range(6)], 'M_ember', PAL['ember'], flag=NOAO)
    for i in range(3):
        a = 2 * PI * i / 3 + 0.4
        k.beam((x + r * 1.05 * math.cos(a), y + r * 1.05 * math.sin(a), z),
               (x + r * 0.3 * math.cos(a), y + r * 0.3 * math.sin(a), z + h * 0.72), 0.025, 0.025, I, PAL['iron'],
               uv='box')


@asset('watchtower', 'Wooden lookout tower on four splayed log legs with cross-bracing, ladder, boarded platform '
       'under a thatched pyramid roof, signal brazier', 2000, footprint=[4.6, 5.4],
       bake=dict(ao_dist=1.2, warp=0.02))
def watchtower(k):
    b, t = 1.5, 1.2
    zp = 6.0

    def hs(z):
        return lerp(b, t, z / zp)
    legs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for (sx, sy) in legs:
        k.cyl((sx * b, sy * b, 0), (sx * t, sy * t, zp + 0.02), 0.15, 0.115, n=7, mat='M_bark_pine', col=PAL['bark'],
              caps=(False, False))
    tiers = [0.4, 2.25, 4.1, 5.8]
    for i in range(4):
        (ax, ay), (bx, by) = legs[i], legs[(i + 1) % 4]
        for z in tiers:
            h = hs(z)
            k.beam((ax * h, ay * h, z), (bx * h, by * h, z), 0.1, 0.12, W, k.jit(PAL['beam']), skip=('c0', 'c1'))
        for j in range(3):
            za, zb_ = tiers[j] + 0.08, tiers[j + 1] - 0.08
            ha, hb = hs(za), hs(zb_)
            k.beam((ax * ha, ay * ha, za), (bx * hb, by * hb, zb_), 0.08, 0.09, W, k.jit(PAL['beam_l']),
                   skip=('c0', 'c1'))
            if j < 2:
                k.beam((bx * ha, by * ha, za), (ax * hb, ay * hb, zb_), 0.08, 0.09, W, k.jit(PAL['beam_l']),
                       skip=('c0', 'c1'))
    # platform
    pd = 1.75
    for yy in (-t, t):
        k.beam((-pd, yy, zp - 0.07), (pd, yy, zp - 0.07), 0.12, 0.14, W, k.jit(PAL['beam']))
    k.boards((pd, -pd, zp), (0, 1, 0), (-1, 0, 0), 2 * pd, 2 * pd, 9, thick=0.06, skip=(), col=PAL['plank'],
             lj=0.05)
    zd = zp + 0.06
    # parapet (boards) - gap on the back (+Y) for the ladder
    ph_ = 0.95
    walls = [((-pd, -pd), (pd, -pd)), ((pd, -pd), (pd, pd)), ((-pd, pd), (-pd, -pd)),
             ((pd, pd), (0.55, pd)), ((-0.35, pd), (-pd, pd))]
    for (a, c) in walls:
        w = Wall(a, c, zd, zd + ph_)
        k.beam(w.P(0, zd + ph_ / 2 + 0.03, -0.05), w.P(w.L, zd + ph_ / 2 + 0.03, -0.05), ph_ - 0.1, 0.035, W,
               k.jit(PAL['plank']), up=w.n, uv='around')
        k.beam(w.P(-0.02, zd + ph_, -0.05), w.P(w.L + 0.02, zd + ph_, -0.05), 0.09, 0.07, W, k.jit(PAL['beam']),
               up=w.n)
    # roof on four posts
    zr0 = zd + 1.95
    pr = pd - 0.1
    for (sx, sy) in legs:
        k.box((sx * pr - 0.06, sy * pr - 0.06, zd), (sx * pr + 0.06, sy * pr + 0.06, zr0 + 0.05), W,
              k.jit(PAL['beam']), skip=('-z', '+z'), uv='along')
    for i in range(4):
        (ax, ay), (bx, by) = legs[i], legs[(i + 1) % 4]
        k.beam((ax * pr, ay * pr, zr0), (bx * pr, by * pr, zr0), 0.1, 0.12, W, k.jit(PAL['beam']), skip=('c0', 'c1'))
        k.beam((ax * pr, ay * pr, zr0 - 0.5), (lerp(ax, bx, 0.25) * pr, lerp(ay, by, 0.25) * pr, zr0 - 0.02), 0.07,
               0.07, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
        k.beam((bx * pr, by * pr, zr0 - 0.5), (lerp(bx, ax, 0.25) * pr, lerp(by, ay, 0.25) * pr, zr0 - 0.02), 0.07,
               0.07, W, k.jit(PAL['beam_l']), skip=('c0', 'c1'))
    roof_hip(k, -pr, pr, -pr, pr, zr0 + 0.05, 1.15, ridge_len=0.0, oh=0.55, tv=0.28, mat='M_thatch',
             under_mat='M_thatch', nu=2, nv=2, undercut=0.1, wob=0.03, round_eave=0.06, finial=True)
    # ladder (back side)
    lx0, lx1 = -0.3, 0.5
    yb, yt = pd + 1.0, pd + 0.02
    for xx in (lx0, lx1):
        k.beam((xx, yb, 0), (xx, yt, zd + 0.9), 0.06, 0.09, W, k.jit(PAL['plank']), up=(0, 1, 0.3))
    nr = 19
    for i in range(nr):
        f = (i + 0.8) / (nr + 2.6)
        k.beam((lx0, lerp(yb, yt, f), (zd + 0.9) * f), (lx1, lerp(yb, yt, f), (zd + 0.9) * f), 0.045, 0.045, W,
               k.jit(PAL['plank_d']), skip=('c0', 'c1'))
    # brazier, crate, hanging horn-lantern
    mini_brazier(k, (0.95, -0.95, zd))
    k.empty('FIRE_brazier', (0.95, -0.95, zd + 0.9))
    crate(k, (-1.1, 1.05, zd), (0.5, 0.45, 0.4), rz=0.2)
    k.empty('ANCHOR_npc', (-0.3, -0.6, zd))
    k.col('legs', (-b - 0.1, -b - 0.1, 0), (b + 0.1, b + 0.1, zr0 + 1.4))
    k.col('ladder', (lx0 - 0.1, pd, 0), (lx1 + 0.1, pd + 1.05, 3.0))
    k.person = (2.4, -1.0)
