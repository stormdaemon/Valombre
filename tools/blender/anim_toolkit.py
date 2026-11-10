"""VALOMBRE animation toolkit (Blender 5.1, headless). Used by anim_build.py and the anim_clips_*.py files.

Everything is authored in CHARACTER space (X = character's left, -Y = front, Z = up, meters), never in raw
bone-local eulers:

  * a POSE is a flat dict of channels (see CHANNELS below): hips position, pelvis / spine / head eulers,
    foot targets (world or pelvis space, with heel/ball pivots), hand targets (chest / pelvis / world space),
    elbow & knee pole directions, weapon blade + cutting-edge directions, palm orientation, finger curl...
  * Rig.solve(pose) turns a pose into bone-local quaternions: FK for the trunk, analytic two-bone IK for the
    legs (foot target + knee direction) and the arms (hand / weapon-grip target + elbow direction), aim
    constraints for the hands (blade direction + cutting edge, or fingers + palm normal), automatic forearm
    twist and clavicle follow, optional two-handed grip (left hand IK'd onto the greatsword handle).
  * a CLIP is a list of key poses (time, pose) interpolated per channel with monotone cubic splines
    (no overshoot, flows through in-betweens, stops on extremes), hand targets travelling on ARCS around the
    shoulder, per-channel lag (overlap / follow-through), and an optional additive `post` hook
    (breathing, bounce...). Locomotion clips are procedural (`fn(phase)`), built on planted-foot gait cycles.
  * bake(): solves every frame and keys rotation_quaternion on all animated bones + location on hips only.

World delta convention: every bone has a world-space delta rotation D (pose_world = D * rest_world); the
local delta L = D_parent^-1 * D is expressed in character axes, and the pose-bone quaternion is
q = R_rest^-1 * L * R_rest. So no bone-local axis guessing anywhere.
"""
import sys, os, math, json, struct, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blcommon import *
from humanoid_rig import *

FPS = 30
XA = Vector((1, 0, 0))
YA = Vector((0, 1, 0))
ZA = Vector((0, 0, 1))
FWD = Vector((0, -1, 0))
DOWN = Vector((0, 0, -1))


# ----------------------------------------------------------------------------- math
def V(v):
    return v.copy() if isinstance(v, Vector) else Vector((float(v[0]), float(v[1]), float(v[2])))


def qaxis(axis, deg):
    return Quaternion(V(axis), math.radians(deg))


def E(pyr):
    """(pitch, yaw, roll) degrees in character axes -> quaternion.
    pitch + = bend forward, yaw + = turn to the character's left, roll + = lean to the left."""
    q = qaxis(ZA, pyr[1]) @ qaxis(XA, pyr[0]) @ qaxis(YA, pyr[2])
    if len(pyr) > 3 and abs(pyr[3]) > 1e-9:
        q = q @ qaxis(ZA, pyr[3])      # twist about the body's own long axis (rolling over when lying down)
    return q


def perp_to(v, n):
    return v - n * v.dot(n)


def any_perp(n):
    a = XA if abs(n.x) < 0.8 else YA
    p = perp_to(a, n)
    p.normalize()
    return p


def nrm(v, fallback=None):
    v = V(v)
    if v.length < 1e-8:
        return V(fallback) if fallback is not None else Vector((0, 0, 1))
    v.normalize()
    return v


def frame(a, h):
    a = nrm(a)
    c = perp_to(V(h), a)
    if c.length < 1e-6:
        c = any_perp(a)
    c.normalize()
    b = c.cross(a)
    M = Matrix((a, b, c))
    M.transpose()
    return M


def frame_map(a0, h0, a1, h1):
    """Rotation R with R*a0 = a1 and R*(h0 perpendicular to a0) = (h1 perpendicular to a1)."""
    return (frame(a1, h1) @ frame(a0, h0).transposed()).to_quaternion()


def twist_angle(q, axis):
    """Signed twist (degrees) of quaternion q about the unit axis (swing-twist decomposition)."""
    v = Vector((q.x, q.y, q.z))
    p = v.dot(axis)
    ang = 2.0 * math.degrees(math.atan2(p, q.w))
    while ang > 180:
        ang -= 360
    while ang < -180:
        ang += 360
    return ang


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def bump(u, peak=0.5, power=1.0):
    """0 -> 1 -> 0 over u in [0,1] with the maximum at `peak`."""
    u = clamp(u, 0.0, 1.0)
    k = math.log(0.5) / math.log(clamp(peak, 0.05, 0.95))
    return math.sin(math.pi * (u ** k)) ** power


def two_bone(H, A, l1, l2, pole, max_ext=0.998):
    """Analytic two-bone IK. Returns (joint position, reached end position, unit pole perp, shortfall)."""
    v = A - H
    d = v.length
    dmax = (l1 + l2) * max_ext
    dmin = abs(l1 - l2) + 1e-3
    short = max(0.0, d - dmax)
    dc = clamp(d, dmin, dmax)
    n = v / d if d > 1e-9 else Vector((0, 0, -1))
    cosa = clamp((l1 * l1 + dc * dc - l2 * l2) / (2 * l1 * dc), -1.0, 1.0)
    sina = math.sqrt(max(0.0, 1.0 - cosa * cosa))
    p = perp_to(pole, n)
    if p.length < 1e-5:
        p = any_perp(n)
    p.normalize()
    K = H + n * (l1 * cosa) + p * (l1 * sina)
    return K, H + n * dc, p, short


# ----------------------------------------------------------------------------- channels
SIDES = (('L', 1.0), ('R', -1.0))
# kind: vec (plain), eul (pitch,yaw,roll), sc (scalar), foot (x,y,z,pitch,yaw,roll), pos (hand target), dir,
#       dir2 (two directions), str (space name)
KIND = {'hips': 'vec', 'pelvis': 'eul', 'spine': 'eul', 'chest': 'eul', 'head': 'eul', 'hstab': 'sc',
        'foot': 'foot', 'knee': 'dir', 'toe': 'sc', 'fsp': 'str',
        'hand': 'pos', 'pole': 'dir', 'blade': 'dir', 'edge': 'dir', 'palm': 'dir2', 'twist': 'sc',
        'wrist': 'vec', 'curl': 'sc', 'clav': 'vec', 'hsp': 'str', 'bsp': 'str', 'gripsep': 'sc'}
CHANNELS = """
hips   (x, y, z)            world position of the hips bone head (rest = 0, 0, 0.98)
pelvis (pitch, yaw, roll)   pelvis orientation, degrees (see E())
spine  (pitch, yaw, roll)   total bend spread over spine_01..03 (30/35/35 %)
chest  (pitch, yaw, roll)   extra rotation of spine_03 only
head   (pitch, yaw, roll)   neck (40 %) + head (60 %) relative to the chest; hstab 0..1 blends toward
                            interpreting it in world space (head stays level while the torso twists)
footL/R (x, y, z, pitch, yaw, roll)  sole point under the ankle; pitch + = toes down (pivot on the ball),
                            pitch - = toes up (pivot on the heel); yaw + = toes to the character's left.
                            fspL/R = 'world' (default) or 'hips' (rest-like coordinates carried by the pelvis)
kneeL/R direction            optional knee pole (same space as the foot); automatic otherwise
toeL/R  degrees              extra toe bend (auto bend when the heel is raised on the ground)
handL/R (x, y, z)           wrist target (weapon mode: GRIP centre). hspL/R = 'chest' (default: rest-like
                            coordinates carried by spine_03), 'hips' or 'world'
poleL/R direction            elbow direction (same space as the hand)
bladeR/L direction           weapon mode: blade direction; edgeR/L = cutting edge hint (direction of the cut);
                            bspR/L = space of blade/edge (defaults to the hand space)
palmL/R (fx,fy,fz, nx,ny,nz) fingers direction + palm normal (same space as the hand)
twistL/R degrees             forearm supination (+) / pronation (-) when neither blade nor palm is given
wristL/R (flex, dev)        wrist flexion / ulnar deviation, default hand mode
curlL/R 0..1                 finger curl (1 = fist)
clavL/R (up, fwd)           extra clavicle shrug / protraction in degrees (auto follow is always on)
"""


def chan_kind(ch):
    if ch in KIND:
        return KIND[ch]
    return KIND[ch[:-1]]


def P(base=None, **kw):
    d = dict(base) if base else {}
    d.update(kw)
    return d


def mirror_pose(p):
    """Swap left / right."""
    out = {}
    for k, v in p.items():
        k2 = k
        base = k
        if k not in KIND:
            base = k[:-1]
            k2 = base + ('R' if k[-1] == 'L' else 'L')
        kind = KIND[base]
        if v is None or kind in ('sc', 'str'):
            out[k2] = v
        elif kind == 'eul':
            out[k2] = (v[0], -v[1], -v[2]) + ((-v[3],) if len(v) > 3 else ())
        elif kind == 'foot':
            out[k2] = (-v[0], v[1], v[2], v[3], -v[4], -v[5] if len(v) > 5 else 0.0)
        elif kind == 'dir2':
            out[k2] = (-v[0], v[1], v[2], -v[3], v[4], v[5])
        elif base in ('hips', 'hand', 'pole', 'blade', 'edge', 'knee'):
            out[k2] = (-v[0], v[1], v[2])
        else:
            out[k2] = v
    return out


# ----------------------------------------------------------------------------- curves
def _pchip_tangents(ts, vs, loop, T, flow0=False, flow1=False):
    n = len(ts)
    m = np.zeros_like(vs)
    if n < 2:
        return m
    for i in range(n):
        if loop:
            ip, inx = (i - 1) % n, (i + 1) % n
            h0 = ts[i] - ts[ip]
            h1 = ts[inx] - ts[i]
            if h0 <= 0:
                h0 += T
            if h1 <= 0:
                h1 += T
        else:
            if i == 0:
                if flow0:
                    m[i] = (vs[1] - vs[0]) / (ts[1] - ts[0])
                continue
            if i == n - 1:
                if flow1:
                    m[i] = (vs[-1] - vs[-2]) / (ts[-1] - ts[-2])
                continue
            ip, inx = i - 1, i + 1
            h0 = ts[i] - ts[ip]
            h1 = ts[inx] - ts[i]
        d0 = (vs[i] - vs[ip]) / h0
        d1 = (vs[inx] - vs[i]) / h1
        w1 = 2 * h1 + h0
        w2 = h1 + 2 * h0
        ok = (d0 * d1) > 1e-12
        d0s = np.where(ok, d0, 1.0)
        d1s = np.where(ok, d1, 1.0)
        m[i] = np.where(ok, (w1 + w2) / (w1 / d0s + w2 / d1s), 0.0)
    return m


class Curve:
    """Monotone cubic (PCHIP / 'auto clamped') interpolation of vector keys.
    kind 'dir': re-normalised; 'dir2': two directions; 'arc': position interpolated as direction + radius
    around `center` (hands swing on arcs around the shoulder instead of straight lines)."""

    def __init__(self, ts, vals, T, loop=False, kind='vec', center=None, flow0=False, flow1=False):
        ts = [float(t) for t in ts]
        vals = [np.atleast_1d(np.array(v, dtype=np.float64)) for v in vals]
        if loop and len(ts) > 1 and abs(ts[-1] - T) < 1e-6:
            ts, vals = ts[:-1], vals[:-1]
        self.kind = kind
        self.center = np.array(center, dtype=np.float64) if center is not None else None
        if kind == 'arc':
            vv = []
            for v in vals:
                d = v - self.center
                r = float(np.linalg.norm(d))
                vv.append(np.concatenate([d / max(r, 1e-9), [r]]))
            vals = vv
        self.ts = np.array(ts)
        self.vs = np.array(vals)
        self.T = float(T)
        self.loop = loop
        self.m = _pchip_tangents(self.ts, self.vs, loop, self.T, flow0, flow1)

    def raw(self, t):
        ts, vs, m = self.ts, self.vs, self.m
        n = len(ts)
        if n == 1:
            return vs[0].copy()
        if self.loop:
            t = (t - ts[0]) % self.T + ts[0]
            i = int(np.searchsorted(ts, t, side='right')) - 1
            i = max(0, min(n - 1, i))
            j = (i + 1) % n
            h = ts[j] - ts[i]
            if h <= 0:
                h += self.T
        else:
            if t <= ts[0]:
                return vs[0].copy()
            if t >= ts[-1]:
                return vs[-1].copy()
            i = int(np.searchsorted(ts, t, side='right')) - 1
            i = max(0, min(n - 2, i))
            j = i + 1
            h = ts[j] - ts[i]
        u = (t - ts[i]) / h
        u2, u3 = u * u, u * u * u
        return ((2 * u3 - 3 * u2 + 1) * vs[i] + (u3 - 2 * u2 + u) * h * m[i]
                + (-2 * u3 + 3 * u2) * vs[j] + (u3 - u2) * h * m[j])

    def __call__(self, t):
        v = self.raw(t)
        k = self.kind
        if k == 'dir':
            n = np.linalg.norm(v)
            return v / n if n > 1e-6 else v
        if k == 'dir2':
            a, b = v[:3], v[3:]
            return np.concatenate([a / max(np.linalg.norm(a), 1e-6), b / max(np.linalg.norm(b), 1e-6)])
        if k == 'arc':
            d = v[:3]
            d = d / max(np.linalg.norm(d), 1e-6)
            return self.center + d * v[3]
        if k == 'quat':      # 3 position comps + quaternion + extra
            q = v[3:7]
            v[3:7] = q / max(np.linalg.norm(q), 1e-9)
            return v
        return v


def spline(knots, T=1.0, loop=True):
    """Scalar periodic curve from (x, y) knots."""
    c = Curve([k[0] for k in knots], [[k[1]] for k in knots], T, loop)
    return lambda x: float(c(x)[0])


# ----------------------------------------------------------------------------- rig + solver
class Body:
    pass


class Rig:
    SPINE_W = (0.30, 0.35, 0.35)

    def __init__(self, arm):
        self.arm = arm
        B = arm.data.bones
        self.names = [b.name for b in B]
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in B}
        self.rq = {b.name: b.matrix_local.to_quaternion() for b in B}
        self.head = {b.name: b.head_local.copy() for b in B}
        self.tail = {b.name: b.tail_local.copy() for b in B}
        self.anim_bones = [n for n in self.names
                           if n != 'root' and not n.startswith(('weapon_', 'shield_', 'sheath_'))]
        h = self.head
        self.leg = {}
        self.armd = {}
        for S, sx in SIDES:
            th, sh, ft, toe = 'thigh_' + S, 'shin_' + S, 'foot_' + S, 'toe_' + S
            self.leg[S] = dict(l1=(h[sh] - h[th]).length, l2=(h[ft] - h[sh]).length,
                               d1=(h[sh] - h[th]).normalized(), d2=(h[ft] - h[sh]).normalized(),
                               ankle=h[ft].copy(), ball=Vector((h[toe].x, h[toe].y, 0.0)),
                               heel=Vector((h[ft].x, 0.070, 0.0)), sole=Vector((h[ft].x, h[ft].y, 0.0)),
                               tip=Vector((self.tail[toe].x, self.tail[toe].y - 0.005, 0.0)))
            ua, fa, ha = 'upper_arm_' + S, 'forearm_' + S, 'hand_' + S
            self.armd[S] = dict(l1=(h[fa] - h[ua]).length, l2=(h[ha] - h[fa]).length,
                                a=Vector((sx, 0, 0)), hinge=Vector((0, 0, -sx)),
                                off=h['weapon_' + S] - h[ha], sh=h[ua].copy())
            # fist pose of the thumb (wraps under the grip), computed from target directions in the T-pose
            t1, t2 = 'thumb_01_' + S, 'thumb_02_' + S
            d1 = (self.tail[t1] - h[t1]).normalized()
            d2 = (self.tail[t2] - h[t2]).normalized()
            D1 = d1.rotation_difference(Vector((-0.15 * sx, -0.45, -0.88)).normalized())
            D2 = (D1 @ d2).rotation_difference(Vector((0.75 * sx, -0.10, -0.65)).normalized()) @ D1
            self.armd[S]['thumb'] = (self.rq[t1].conjugated() @ D1 @ self.rq[t1],
                                     self.rq[t2].conjugated() @ (D1.conjugated() @ D2) @ self.rq[t2])
        self.leg_len = self.leg['L']['l1'] + self.leg['L']['l2']
        self.arm_len = self.armd['L']['l1'] + self.armd['L']['l2']

    # -- trunk FK
    def solve_body(self, p):
        r = self
        b = Body()
        D, pos = {}, {}
        b.D, b.pos = D, pos
        D['root'] = Quaternion()
        pos['root'] = Vector((0, 0, 0))
        D['hips'] = E(p['pelvis'])
        pos['hips'] = V(p['hips'])
        sp = p['spine']
        prev = 'hips'
        for i, n in enumerate(('spine_01', 'spine_02', 'spine_03')):
            w = r.SPINE_W[i]
            D[n] = D[prev] @ E((sp[0] * w, sp[1] * w, sp[2] * w))
            pos[n] = pos[prev] + D[prev] @ (r.head[n] - r.head[prev])
            prev = n
        ch = p.get('chest')
        if ch is not None:
            D['spine_03'] = D['spine_03'] @ E(ch)
        hd = p['head']
        Dn = D['spine_03'] @ E((hd[0] * 0.4, hd[1] * 0.4, hd[2] * 0.4))
        Dh = Dn @ E((hd[0] * 0.6, hd[1] * 0.6, hd[2] * 0.6))
        st = float(p.get('hstab', 0.0) or 0.0)
        if st > 1e-4:
            Dh = Dh.slerp(E(hd), clamp(st, 0, 1))
            Dn = D['spine_03'].slerp(Dh, 0.45)
        D['neck'] = Dn
        pos['neck'] = pos['spine_03'] + D['spine_03'] @ (r.head['neck'] - r.head['spine_03'])
        D['head'] = Dh
        pos['head'] = pos['neck'] + Dn @ (r.head['head'] - r.head['neck'])
        b.pelvis_yaw = p['pelvis'][1]
        return b

    def xf(self, body, space):
        if space == 'world':
            return Vector((0, 0, 0)), Vector((0, 0, 0)), Quaternion()
        if space == 'hips':
            return self.head['hips'], body.pos['hips'], body.D['hips']
        if space == 'chest':
            return self.head['spine_03'], body.pos['spine_03'], body.D['spine_03']
        raise ValueError(space)

    def to_world(self, body, pt, space):
        o0, o1, q = self.xf(body, space)
        return o1 + q @ (V(pt) - o0)

    def dir_world(self, body, d, space):
        return nrm(self.xf(body, space)[2] @ V(d))

    # -- foot target -> (ankle world, foot world delta, toe bend)
    def foot_target(self, body, S, f, space, toe_extra=0.0):
        if space == 'raw':
            return Vector(f[0:3]), Quaternion(f[3:7]).normalized(), float(f[7])
        L = self.leg[S]
        o0, o1, qs = self.xf(body, space)
        pitch, yaw = float(f[3]), float(f[4])
        roll = float(f[5]) if len(f) > 5 else 0.0
        Qy = qaxis(ZA, yaw)
        Dloc = Qy @ qaxis(XA, pitch) @ qaxis(YA, roll)
        piv_r = L['ball'] if pitch >= 0 else L['heel']
        pt = Vector((float(f[0]), float(f[1]), float(f[2])))
        piv = pt + Qy @ (piv_r - L['sole'])
        ankle_s = piv + Dloc @ (L['ankle'] - piv_r)
        A = o1 + qs @ (ankle_s - o0)
        ground = clamp(1.0 - float(f[2]) / 0.10, 0.0, 1.0) if space == 'world' else 0.0
        toe = float(toe_extra) - clamp(pitch, 0.0, 70.0) * ground
        return A, qs @ Dloc, toe

    def solve(self, p, twoh=False):
        """pose dict -> (local quaternions {bone: Quaternion}, hips location (bone space), info dict)."""
        r = self
        body = r.solve_body(p)
        D, pos = body.D, body.pos
        info = {'short': {}, 'wrist': {}}
        local = {}
        Dh_ = D['hips']
        # ---------------- legs
        for S, sx in SIDES:
            L = r.leg[S]
            th, sh, ft, toe = 'thigh_' + S, 'shin_' + S, 'foot_' + S, 'toe_' + S
            H = pos['hips'] + Dh_ @ (r.head[th] - r.head['hips'])
            pos[th] = H
            space = p.get('fsp' + S) or 'world'
            A, Dfoot, toe_ang = r.foot_target(body, S, p['foot' + S], space, p.get('toe' + S, 0.0) or 0.0)
            n = nrm(A - H, DOWN)
            kn = p.get('knee' + S)
            if kn is not None:
                pole = nrm(kn) if space in ('world', 'raw') else r.dir_world(body, kn, space)
            else:
                ff = perp_to(Dfoot @ FWD, Dh_ @ ZA)
                pf = Dh_ @ FWD
                if ff.length > 0.3:
                    pf = nrm(pf * 0.5 + ff.normalized() * 0.5, pf)
                pole = (Dh_ @ DOWN).rotation_difference(n) @ pf
            K, A2, pp, short = two_bone(H, A, L['l1'], L['l2'], pole, 0.9985)
            a1 = nrm(K - H)
            a2 = nrm(A2 - K)
            g = perp_to(a2, a1)
            g = -pp if g.length < 1e-4 else g.normalized()
            hg = a1.cross(g)
            D[th] = frame_map(L['d1'], XA, a1, hg)
            D[sh] = frame_map(L['d2'], XA, a2, hg)
            pos[sh], pos[ft] = K, A2
            D[ft] = Dfoot
            D[toe] = Dfoot @ qaxis(XA, toe_ang)
            pos[toe] = A2 + Dfoot @ (r.head[toe] - r.head[ft])
            info['short']['leg' + S] = short
            info['ext' + S] = (A2 - H).length / (L['l1'] + L['l2'])
        # ---------------- arms (right first: the left hand may follow the weapon)
        grip = None
        for S, sx in (('R', -1.0), ('L', 1.0)):
            AD = r.armd[S]
            cl, ua, fa, ha = 'clavicle_' + S, 'upper_arm_' + S, 'forearm_' + S, 'hand_' + S
            D3 = D['spine_03']
            pos[cl] = pos['spine_03'] + D3 @ (r.head[cl] - r.head['spine_03'])
            space = p.get('hsp' + S) or 'chest'
            follow = twoh and S == 'L' and grip is not None
            blade = p.get('blade' + S)
            palm = p.get('palm' + S)
            if follow:
                Gr, b_, k_ = grip
                sep = float(p.get('gripsep', 0.17) or 0.17)
                tgt = Gr - b_ * sep
            else:
                tgt = r.to_world(body, p['hand' + S], space)
            # clavicle: explicit + automatic follow of the hand
            sh0 = pos[cl] + D3 @ (r.head[ua] - r.head[cl])
            dch = D3.conjugated() @ (tgt - sh0)
            dch = nrm(dch, DOWN)
            cv = p.get('clav' + S)
            cv = (0.0, 0.0) if cv is None else cv
            up = float(cv[0]) + 16.0 * max(0.0, dch.z)
            fw = float(cv[1]) + 12.0 * max(0.0, -dch.y) + 8.0 * max(0.0, -sx * dch.x)
            D[cl] = D3 @ (qaxis(YA, -sx * up) @ qaxis(ZA, -sx * fw))
            Sp = pos[cl] + D[cl] @ (r.head[ua] - r.head[cl])
            pos[ua] = Sp
            pole = r.dir_world(body, p['pole' + S], space)

            def ik(Wt):
                K, W2, pp, short = two_bone(Sp, Wt, AD['l1'], AD['l2'], pole, 0.999)
                a1 = nrm(K - Sp)
                a2 = nrm(W2 - K)
                g = perp_to(a2, a1)
                g = -pp if g.length < 1e-4 else g.normalized()
                hg = a1.cross(g)
                return K, W2, a2, frame_map(AD['a'], AD['hinge'], a1, hg), frame_map(AD['a'], AD['hinge'], a2, hg), short

            Dhand = None
            if follow or blade is not None:
                if follow:
                    b = b_
                    e = k_
                else:
                    bspace = p.get('bsp' + S) or space
                    b = r.dir_world(body, blade, bspace)
                    eh = p.get('edge' + S)
                    e = r.dir_world(body, eh, bspace) if eh is not None else None
                W = tgt
                for _ in range(3):
                    K, W2, a2, Du, Df0, short = ik(W)
                    ee = e if (e is not None and not follow) else a2
                    k = perp_to(ee, b)
                    if k.length < 0.05:
                        k = perp_to(e if e is not None else -pole, b)
                    k.normalize()
                    # soft wrist limit: the hand may turn around the handle toward the forearm
                    kf = perp_to(a2, b)
                    if kf.length > 0.25:
                        kf.normalize()
                        ang = math.degrees(k.angle(kf))
                        lim = 28.0 if twoh else 42.0
                        if ang > lim:
                            ax = kf.cross(k)
                            ax = b if ax.length < 1e-6 else ax.normalized()
                            k = Quaternion(ax, math.radians(lim + (0.15 if twoh else 0.3) * (ang - lim))) @ kf
                    Dhand = frame_map(FWD, AD['a'], b, k)
                    W = tgt - Dhand @ AD['off']
                K, W2, a2, Du, Df0, short = ik(W)
                if S == 'R':
                    grip = (W2 + Dhand @ AD['off'], b, k)
                info['blade' + S] = (W2 + Dhand @ AD['off'], b)
            elif palm is not None:
                fd = r.dir_world(body, palm[0:3], space)
                pn = r.dir_world(body, palm[3:6], space)
                Dhand = frame_map(AD['a'], DOWN, fd, pn)
                K, W2, a2, Du, Df0, short = ik(tgt)
            else:
                K, W2, a2, Du, Df0, short = ik(tgt)
            if Dhand is not None:
                rel = Df0.conjugated() @ Dhand
                tw = clamp(twist_angle(rel, AD['a']), -120.0, 120.0) * 0.85
                Df = Df0 @ Quaternion(AD['a'], math.radians(tw))
            else:
                tw = float(p.get('twist' + S, 0.0) or 0.0)
                Df = Df0 @ Quaternion(AD['a'], math.radians(-sx * tw))
                wr = p.get('wrist' + S)
                wr = (0.0, 0.0) if wr is None else wr
                Dhand = Df @ (qaxis(YA, sx * float(wr[0])) @ qaxis(ZA, sx * float(wr[1])))
            D[ua], D[fa], D[ha] = Du, Df, Dhand
            pos[fa], pos[ha] = K, W2
            info['short']['arm' + S] = short
            info['wrist'][S] = math.degrees((Dhand @ AD['a']).angle(a2))
            # fingers (bone-local curls; same sign on both sides, see humanoid_rig.py)
            c = float(p.get('curl' + S, 0.3) or 0.0)
            for nm, a in (('fingers_01_', 80.0), ('fingers_02_', 95.0), ('index_01_', 78.0), ('index_02_', 92.0)):
                local[nm + S] = Quaternion((1, 0, 0), math.radians(-a * c))
            local['thumb_01_' + S] = Quaternion().slerp(AD['thumb'][0], clamp(c, 0, 1))
            local['thumb_02_' + S] = Quaternion().slerp(AD['thumb'][1], clamp(c, 0, 1))
        # ---------------- world deltas -> bone-local quaternions
        for n in r.anim_bones:
            if n in local:
                continue
            L_ = D[r.parent[n]].conjugated() @ D[n]
            rq = r.rq[n]
            local[n] = rq.conjugated() @ L_ @ rq
        loc = r.rq['hips'].conjugated() @ (pos['hips'] - r.head['hips'])
        info['pos'] = pos
        info['D'] = D
        return local, loc, info

    def point(self, info, bone, rest_pt):
        return info['pos'][bone] + info['D'][bone] @ (V(rest_pt) - self.head[bone])


def arm_angles(S, fwd=0.0, out=8.0, bend=20.0, inw=0.0):
    """FK-style helper: wrist position + elbow pole in CHEST space from shoulder / elbow angles (degrees).
    fwd = shoulder flexion (arm swings forward), out = abduction, bend = elbow flexion, inw = internal
    rotation (the forearm crosses in front of the body)."""
    sx = 1.0 if S == 'L' else -1.0
    sh = Vector((sx * 0.185, 0.0, 1.47))
    q = qaxis(XA, -fwd) @ qaxis(YA, -sx * out)
    u = q @ DOWN
    hx = q @ Vector((-1, 0, 0))
    f = qaxis(hx, bend) @ u
    f = qaxis(u, sx * inw) @ f
    w = sh + u * 0.285 + f * 0.26
    pl = perp_to(f, u)
    pole = (-pl).normalized() if pl.length > 0.05 else (q @ Vector((0, 1, 0)))
    pole = nrm(pole * 0.8 + (q @ Vector((sx * 0.3, 0.6, 0))) * 0.2)
    return (w.x, w.y, w.z), (pole.x, pole.y, pole.z), f.normalized()


# ----------------------------------------------------------------------------- clips
BODY_CH = ('hips', 'pelvis', 'spine', 'chest', 'head', 'hstab')


class Clip:
    def __init__(self, name, dur, loop=False, keys=None, fn=None, lag=None, post=None, props='1h',
                 events=None, speed=None, twoh=False, view='persp', nstrip=8, bounds=1.15,
                 flow_start=False, flow_end=False, grounded=True, note=''):
        self.name, self.dur, self.loop = name, float(dur), loop
        self.keys, self.fn, self.lag, self.post = keys, fn, lag or {}, post
        self.props, self.events, self.speed, self.twoh = props, events or {}, speed, twoh
        self.view, self.nstrip, self.bounds = view, nstrip, bounds
        self.flow_start, self.flow_end, self.grounded, self.note = flow_start, flow_end, grounded, note
        self.nframes = int(math.ceil(self.dur * FPS - 1e-6))
        self.curves = None
        self.const = {}

    # -- curve construction from keys
    def build(self, rig):
        if self.fn is not None or self.curves is not None:
            return
        keys = sorted(self.keys, key=lambda k: k[0])
        T, loop = self.dur, self.loop
        chans = []
        for t, pz in keys:
            for c in pz:
                if c not in chans:
                    chans.append(c)
        curves, const = {}, {}

        def mk(ch, ks, kind=None, center=None):
            kind = kind or {'dir': 'dir', 'dir2': 'dir2'}.get(chan_kind(ch), 'vec')
            return Curve([k[0] for k in ks], [k[1] for k in ks], T, loop, kind, center,
                         self.flow_start, self.flow_end)

        def kv(ch):
            return [(t, pz[ch]) for t, pz in keys if pz.get(ch) is not None]

        for ch in chans:
            if chan_kind(ch) == 'str' or chan_kind(ch) in ('foot', 'pos') or ch[:-1] in ('knee', 'pole', 'blade', 'edge', 'palm'):
                continue
            ks = kv(ch)
            if ks and chan_kind(ch) == 'eul':
                ks = [(t, tuple(v) + (0.0,) * (4 - len(v))) for t, v in ks]
            if ks:
                curves[ch] = mk(ch, ks)
        defaults = {'hips': (0, 0, 0.98), 'pelvis': (0, 0, 0), 'spine': (0, 0, 0), 'head': (0, 0, 0)}

        def body_at(t):
            pz = {c: (curves[c](t) if c in curves else defaults.get(c)) for c in BODY_CH}
            pz = {c: v for c, v in pz.items() if v is not None}
            if 'hstab' in pz:
                pz['hstab'] = float(pz['hstab'][0])
            return rig.solve_body(pz)

        for S, sx in SIDES:
            # ---- feet
            fch, sch, kch = 'foot' + S, 'fsp' + S, 'knee' + S
            ks = kv(fch)
            if ks:
                sps = [(pz.get(sch) or 'world') for t, pz in keys if pz.get(fch) is not None]
                if len(set(sps)) == 1:
                    const[sch] = sps[0]
                    curves[fch] = mk(fch, [(t, tuple(v) + (0.0,) * (6 - len(v))) for t, v in ks])
                    kk = kv(kch)
                    if kk:
                        curves[kch] = mk(kch, kk)
                else:
                    raw, kraw = [], []
                    prevq = None
                    for (t, v), sp in zip(ks, sps):
                        bd = body_at(t)
                        pz = dict([k for k in keys if k[0] == t][0][1])
                        A, Dq, toe = rig.foot_target(bd, S, v, sp, pz.get('toe' + S, 0.0) or 0.0)
                        if prevq is not None and prevq.dot(Dq) < 0:
                            Dq = -Dq
                        prevq = Dq
                        raw.append((t, (A.x, A.y, A.z, Dq.w, Dq.x, Dq.y, Dq.z, toe)))
                        kn = pz.get(kch)
                        if kn is not None:
                            kraw.append((t, tuple(nrm(kn) if sp == 'world' else rig.dir_world(bd, kn, sp))))
                    const[sch] = 'raw'
                    curves[fch] = mk(fch, raw, kind='quat')
                    if kraw and len(kraw) == len(raw):
                        curves[kch] = mk(kch, kraw)
            # ---- hands
            hch, sch = 'hand' + S, 'hsp' + S
            ks = kv(hch)
            if ks:
                sps = [(pz.get(sch) or 'chest') for t, pz in keys if pz.get(hch) is not None]
                bsps = [(pz.get('bsp' + S) or (pz.get(sch) or 'chest')) for t, pz in keys if pz.get('blade' + S) is not None]
                mixed = len(set(sps)) > 1
                if not mixed:
                    const[sch] = sps[0]
                    center = rig.armd[S]['sh'] if sps[0] in ('chest', 'hips') else None
                    curves[hch] = mk(hch, ks, kind='arc' if center is not None else 'vec', center=center)
                else:
                    const[sch] = 'world'
                    curves[hch] = mk(hch, [(t, tuple(rig.to_world(body_at(t), v, sp))) for (t, v), sp in zip(ks, sps)])
                for dch in ('pole' + S, 'palm' + S):
                    kk = kv(dch)
                    if not kk:
                        continue
                    if mixed:
                        out = []
                        for t, v in kk:
                            sp = [pz.get(sch) or 'chest' for tt, pz in keys if tt == t][0]
                            bd = body_at(t)
                            if len(v) == 3:
                                out.append((t, tuple(rig.dir_world(bd, v, sp))))
                            else:
                                out.append((t, tuple(rig.dir_world(bd, v[0:3], sp)) + tuple(rig.dir_world(bd, v[3:6], sp))))
                        kk = out
                    curves[dch] = mk(dch, kk)
                bmixed = mixed or len(set(bsps)) > 1
                for dch in ('blade' + S, 'edge' + S):
                    kk = kv(dch)
                    if not kk:
                        continue
                    if bmixed:
                        out = []
                        for t, v in kk:
                            pz = [pz for tt, pz in keys if tt == t][0]
                            sp = pz.get('bsp' + S) or (pz.get(sch) or 'chest')
                            out.append((t, tuple(rig.dir_world(body_at(t), v, sp))))
                        kk = out
                    curves[dch] = mk(dch, kk)
                if bsps:
                    const['bsp' + S] = 'world' if bmixed else bsps[0]
        self.curves, self.const = curves, const

    def _lag_t(self, ch, t):
        lg = self.lag.get(ch)
        if lg is None and ch not in KIND:
            lg = self.lag.get(ch[:-1])
        if not lg:
            return t
        if self.loop:
            return (t - lg) % self.dur
        return t - lg * math.sin(math.pi * clamp(t / self.dur, 0, 1))

    def eval(self, t):
        if self.fn is not None:
            pz = self.fn(t / self.dur, t)
        else:
            pz = dict(self.const)
            for ch, cv in self.curves.items():
                v = cv(self._lag_t(ch, t))
                pz[ch] = float(v[0]) if len(v) == 1 else v
        if self.post:
            self.post(t, pz)
        return pz

    def frame_time(self, f):
        if self.loop and f >= self.nframes:
            return 0.0
        return self.dur * f / self.nframes


# ----------------------------------------------------------------------------- mannequin + props
C_TORSO = (0.50, 0.50, 0.52)
C_HEAD = (0.72, 0.56, 0.44)
C_L = (0.16, 0.32, 0.72)
C_R = (0.72, 0.18, 0.14)
C_DARK = (0.06, 0.06, 0.07)


def build_mannequin(arm):
    """Light proxy body skinned to the rig: lofted torso (smooth weights), capsule limbs (rigid weights),
    head with nose + eyes, mitten hands with separate index / thumb, feet with toes pointing forward.
    Left limbs are blue, right limbs are red (reading aid), vertex colors on material M_cloth."""
    bm = bmesh.new()
    Wt, Cl = [], []

    def add(pts, w, col):
        out = []
        for pt in pts:
            pt = V(pt)
            out.append(bm.verts.new(pt))
            Wt.append(w(pt) if callable(w) else w)
            Cl.append(col(pt) if callable(col) else col)
        return out

    def loft(rings, w, col, segs=10, caps=True):
        rv = []
        for c, u, v in rings:
            rv.append(add([c + u * math.cos(2 * math.pi * i / segs) + v * math.sin(2 * math.pi * i / segs)
                           for i in range(segs)], w, col))
        for a, b in zip(rv[:-1], rv[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((a[i], a[j], b[j], b[i]))
        if caps:
            bm.faces.new(rv[0][::-1])
            bm.faces.new(rv[-1])
        return rv

    def capsule(p0, p1, r0, r1, w, col, segs=10, mid=None):
        p0, p1 = V(p0), V(p1)
        ax = (p1 - p0).normalized()
        u = any_perp(ax)
        v = ax.cross(u)
        rings = [(p0 + ax * r0 * o, u * r0 * s, v * r0 * s) for o, s in ((-0.9, 0.42), (-0.55, 0.84), (0.0, 1.0))]
        if mid:
            rings.append((p0.lerp(p1, mid[0]), u * mid[1], v * mid[1]))
        rings += [(p1 + ax * r1 * o, u * r1 * s, v * r1 * s) for o, s in ((0.0, 1.0), (0.55, 0.84), (0.9, 0.42))]
        loft(rings, w, col, segs)

    def box(lo, hi, w, col):
        lo, hi = V(lo), V(hi)
        vs = add([(x, y, z) for z in (lo.z, hi.z) for y in (lo.y, hi.y) for x in (lo.x, hi.x)], w, col)
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            bm.faces.new([vs[i] for i in f])

    # torso: one loft, weights blended along z
    cz = (('hips', 1.00), ('spine_01', 1.14), ('spine_02', 1.27), ('spine_03', 1.41))

    def torso_w(pt):
        z = pt.z
        if z <= cz[0][1]:
            return {cz[0][0]: 1.0}
        if z >= cz[-1][1]:
            return {cz[-1][0]: 1.0}
        for (n0, z0), (n1, z1) in zip(cz[:-1], cz[1:]):
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0)
                return {n0: 1 - t, n1: t}

    sec = [(0.87, 0.10, 0.075), (0.92, 0.155, 0.10), (0.98, 0.170, 0.11), (1.04, 0.165, 0.105),
           (1.10, 0.150, 0.095), (1.16, 0.140, 0.09), (1.22, 0.147, 0.095), (1.28, 0.160, 0.105),
           (1.34, 0.172, 0.113), (1.40, 0.180, 0.118), (1.45, 0.172, 0.11), (1.49, 0.13, 0.09), (1.515, 0.07, 0.06)]
    loft([(Vector((0, 0.005, z)), XA * rx, YA * ry) for z, rx, ry in sec], torso_w, C_TORSO, segs=14)
    box((-0.05, -0.135, 1.33), (0.05, -0.105, 1.43), {'spine_03': 1.0}, C_DARK)         # chest emblem (front)
    box((-0.035, -0.125, 0.96), (0.035, -0.10, 1.02), {'hips': 1.0}, C_DARK)            # belt buckle (front)
    capsule((0, 0.008, 1.49), (0, 0.0, 1.60), 0.05, 0.047, {'neck': 1.0}, C_HEAD, segs=8)
    # head
    hc, hr = Vector((0, -0.012, 1.705)), Vector((0.078, 0.095, 0.118))
    rings = []
    for i in range(1, 8):
        a = math.pi * i / 8
        rings.append((hc + ZA * (-math.cos(a) * hr.z), XA * hr.x * math.sin(a), YA * hr.y * math.sin(a)))
    loft(rings, {'head': 1.0}, C_HEAD, segs=12)
    nose = add([(-0.016, -0.098, 1.70), (0.016, -0.098, 1.70), (0, -0.10, 1.725), (0, -0.142, 1.685), (0, -0.095, 1.665)],
               {'head': 1.0}, C_HEAD)
    for f in ((0, 3, 2), (1, 2, 3), (0, 4, 3), (1, 3, 4), (0, 2, 1), (0, 1, 4)):
        bm.faces.new([nose[i] for i in f])
    for sx in (1, -1):
        box((sx * 0.034 - 0.013, -0.104, 1.722), (sx * 0.034 + 0.013, -0.084, 1.742), {'head': 1.0}, C_DARK)
    # limbs
    T = bone_table()
    bt = {b['name']: b for b in T}
    for S, sx in SIDES:
        col = C_L if S == 'L' else C_R
        col2 = tuple(min(1.0, c * 1.35 + 0.08) for c in col)

        def m(x, y, z):
            return Vector((x * sx, y, z))

        def bn(n):
            return {n + '_' + S: 1.0}

        capsule(m(0.06, 0, 1.468), m(0.165, 0, 1.475), 0.042, 0.046, bn('clavicle'), C_TORSO, segs=8)
        capsule(m(0.185, 0, 1.47), m(0.47, 0, 1.47), 0.055, 0.042, bn('upper_arm'), col)
        capsule(m(0.47, 0, 1.47), m(0.73, 0, 1.47), 0.042, 0.030, bn('forearm'), col, mid=(0.3, 0.044))
        box(m(0.725, -0.043, 1.452), m(0.812, 0.043, 1.486), bn('hand'), col2)
        box(m(0.81, -0.013, 1.458), m(0.862, 0.043, 1.482), bn('fingers_01'), col2)
        box(m(0.858, -0.012, 1.459), m(0.915, 0.041, 1.481), bn('fingers_02'), col2)
        box(m(0.81, -0.044, 1.459), m(0.858, -0.018, 1.481), bn('index_01'), col2)
        box(m(0.854, -0.043, 1.46), m(0.906, -0.019, 1.48), bn('index_02'), col2)
        capsule(m(0.755, -0.030, 1.462), m(0.790, -0.056, 1.452), 0.014, 0.012, bn('thumb_01'), col2, segs=6)
        capsule(m(0.790, -0.056, 1.452), m(0.826, -0.072, 1.446), 0.012, 0.010, bn('thumb_02'), col2, segs=6)
        capsule(m(0.095, 0, 0.93), m(0.10, -0.005, 0.50), 0.086, 0.058, bn('thigh'), col)
        capsule(m(0.10, -0.005, 0.50), m(0.10, 0.015, 0.09), 0.056, 0.040, bn('shin'), col, mid=(0.28, 0.060))
        loft([(m(0.10, y, cz_), XA * hw, ZA * hh) for y, cz_, hw, hh in
              ((0.078, 0.040, 0.020, 0.030), (0.065, 0.046, 0.036, 0.046), (0.015, 0.056, 0.043, 0.056),
               (-0.05, 0.040, 0.047, 0.040), (-0.115, 0.027, 0.050, 0.027))], bn('foot'), col2, segs=8)
        loft([(m(0.10, y, cz_), XA * hw, ZA * hh) for y, cz_, hw, hh in
              ((-0.112, 0.027, 0.050, 0.027), (-0.165, 0.024, 0.048, 0.024), (-0.198, 0.019, 0.038, 0.019),
               (-0.208, 0.016, 0.022, 0.012))], bn('toe'), col2, segs=8)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bmesh_to_object(bm, 'mannequin', smooth=True)
    for n in DEFORM_BONES:
        ob.vertex_groups.new(name=n)
    for i, w in enumerate(Wt):
        for n, x in w.items():
            if x > 1e-4:
                ob.vertex_groups[n].add([i], x, 'REPLACE')
    mod = ob.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    ob.parent = arm
    assign_mat(ob, make_mat('M_cloth', (1.0, 1.0, 1.0), rough=0.75, use_vertex_color=True))
    set_vertex_colors(ob, lambda pt, n, i: Cl[i])
    # crease hard box edges a bit: flat shade the boxes by splitting is not needed for a proxy
    return ob


def _prop_object(name, parts, color, arm, bone, rough=0.4, metal=0.8):
    """parts: list of ('box', lo, hi) or ('taper', y0, y1, hw0, hw1, ht) or ('disc', radius, z0, z1, segs)
    in socket space (x = cutting edge, y = blade / shield up, z = flat normal / shield face)."""
    bm = bmesh.new()
    for part in parts:
        if part[0] == 'box':
            lo, hi = V(part[1]), V(part[2])
            vs = [bm.verts.new((x, y, z)) for z in (lo.z, hi.z) for y in (lo.y, hi.y) for x in (lo.x, hi.x)]
            for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
                bm.faces.new([vs[i] for i in f])
        elif part[0] == 'taper':
            _, y0, y1, hw0, hw1, ht = part
            ym = y0 + (y1 - y0) * 0.86
            rings = []
            for y, hw in ((y0, hw0), (ym, lerp(hw0, hw1, 0.4)), (y1, 0.003)):
                rings.append([bm.verts.new(c) for c in ((-hw, y, 0), (0, y, ht), (hw, y, 0), (0, y, -ht))])
            for a, b in zip(rings[:-1], rings[1:]):
                for i in range(4):
                    j = (i + 1) % 4
                    bm.faces.new((a[i], a[j], b[j], b[i]))
            bm.faces.new(rings[0][::-1])
            bm.faces.new(rings[-1])
        elif part[0] == 'disc':
            _, rad, z0, z1, segs = part
            r0 = [bm.verts.new((rad * math.cos(2 * math.pi * i / segs), rad * math.sin(2 * math.pi * i / segs), z0)) for i in range(segs)]
            r1 = [bm.verts.new((rad * 0.96 * math.cos(2 * math.pi * i / segs), rad * 0.96 * math.sin(2 * math.pi * i / segs), z1)) for i in range(segs)]
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            bm.faces.new(r0[::-1])
            c = bm.verts.new((0, 0, z1 + rad * 0.12))
            for i in range(segs):
                bm.faces.new((r1[i], r1[(i + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bmesh_to_object(bm, name, smooth=False)
    assign_mat(ob, make_mat('PV_' + name, color, rough=rough, metal=metal))
    if bone:
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = bone
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = (0, -arm.data.bones[bone].length, 0)
    return ob


def build_props(arm):
    """Preview-only props parented to the sockets (never exported)."""
    pr = {}
    steel, dark, wood = (0.75, 0.77, 0.8), (0.12, 0.09, 0.07), (0.35, 0.22, 0.12)
    pr['sword'] = [
        _prop_object('sword_blade', [('taper', 0.085, 0.82, 0.026, 0.016, 0.006),
                                     ('box', (-0.095, 0.065, -0.012), (0.095, 0.088, 0.012)),
                                     ('box', (-0.022, -0.13, -0.022), (0.022, -0.095, 0.022))], steel, arm, 'weapon_R'),
        _prop_object('sword_grip', [('box', (-0.014, -0.10, -0.014), (0.014, 0.068, 0.014))], dark, arm, 'weapon_R', 0.8, 0.0)]
    pr['shield'] = [
        _prop_object('shield', [('disc', 0.30, 0.0, 0.03, 20)], (0.42, 0.27, 0.13), arm, 'shield_L', 0.7, 0.0),
        _prop_object('shield_boss', [('disc', 0.07, 0.03, 0.06, 10), ('box', (-0.02, 0.2, 0.03), (0.02, 0.28, 0.045))],
                     steel, arm, 'shield_L')]
    pr['greatsword'] = [
        _prop_object('gs_blade', [('taper', 0.12, 1.18, 0.038, 0.024, 0.007),
                                  ('box', (-0.15, 0.095, -0.014), (0.15, 0.122, 0.014)),
                                  ('box', (-0.028, -0.32, -0.028), (0.028, -0.275, 0.028))], steel, arm, 'weapon_R'),
        _prop_object('gs_grip', [('box', (-0.015, -0.28, -0.015), (0.015, 0.10, 0.015))], dark, arm, 'weapon_R', 0.8, 0.0)]
    pr['hammer'] = [
        _prop_object('hammer_head', [('box', (-0.06, 0.20, -0.025), (0.05, 0.26, 0.025))], (0.25, 0.25, 0.27), arm, 'weapon_R'),
        _prop_object('hammer_handle', [('box', (-0.012, -0.08, -0.012), (0.012, 0.22, 0.012))], wood, arm, 'weapon_R', 0.8, 0.0)]
    pr['flask'] = [
        _prop_object('flask', [('box', (-0.03, -0.05, -0.03), (0.03, 0.05, 0.03)),
                               ('box', (-0.012, 0.05, -0.012), (0.012, 0.09, 0.012))], (0.55, 0.12, 0.1), arm, 'weapon_L', 0.3, 0.0)]
    pr['anvil'] = [
        _prop_object('anvil', [('box', (-0.33, -0.62, 0.0), (0.13, -0.38, 0.62)),
                               ('box', (-0.42, -0.66, 0.62), (0.22, -0.34, 0.80))], (0.2, 0.2, 0.22), arm, None, 0.6, 0.6)]
    return pr


BLADE_LEN = {'1h': 0.82, '2h': 1.18, 'sword': 0.82, 'drink': 0.82}
PROP_SETS = {'1h': ('sword', 'shield'), '2h': ('greatsword',), 'none': (), 'hammer': ('hammer', 'anvil'),
             'sword': ('sword',), 'drink': ('sword', 'shield', 'flask')}


def show_props(props, key):
    vis = PROP_SETS[key]
    for k, objs in props.items():
        for o in objs:
            o.hide_render = k not in vis
            o.hide_viewport = k not in vis


def build_ground():
    bm = bmesh.new()
    s = 6.0
    vs = [bm.verts.new(c) for c in ((-s, -s, -0.003), (s, -s, -0.003), (s, s, -0.003), (-s, s, -0.003))]
    bm.faces.new(vs)
    g = bmesh_to_object(bm, 'pv_ground', smooth=False)
    assign_mat(g, make_mat('PV_ground', (0.085, 0.095, 0.085), rough=0.95))
    bm = bmesh.new()
    for i in range(-10, 11):
        c = i * 0.5
        w = 0.006 if i else 0.012
        for a, b in (((c - w, -5, -0.002), (c + w, 5, -0.002)), ((-5, c - w, -0.002), (5, c + w, -0.002))):
            vs = [bm.verts.new(q) for q in ((a[0], a[1], -0.0015), (b[0], a[1], -0.0015), (b[0], b[1], -0.0015), (a[0], b[1], -0.0015))]
            bm.faces.new(vs)
    l = bmesh_to_object(bm, 'pv_grid', smooth=False)
    assign_mat(l, make_mat('PV_grid', (0.2, 0.22, 0.2), rough=0.95))
    return [g, l]


# ----------------------------------------------------------------------------- baking + diagnostics
class Stage:
    """Scene with the rig, the mannequin, the props and the ground."""

    def __init__(self):
        reset_scene()
        self.arm = build_humanoid_armature('Armature')
        self.rig = Rig(self.arm)
        self.man = build_mannequin(self.arm)
        self.props = build_props(self.arm)
        self.ground = build_ground()
        self.actions = {}
        self.diag = {}

    def bake(self, clip, verbose=True):
        rig, arm = self.rig, self.arm
        clip.build(rig)
        act = new_action(arm, clip.name)
        pbs = {n: arm.pose.bones[n] for n in rig.anim_bones}
        prev = {}
        first = None
        dg = dict(leg=0.0, arm=0.0, wrist=0.0, zmin=9.0, zfoot_max=0.0, ext_max=0.0, ext_min=9.0, loop_err=0.0,
                  body_zmin=9.0, hipxy=0.0)
        N = clip.nframes
        frames = []
        for f in range(N + 1):
            pz = clip.eval(clip.frame_time(f))
            local, loc, info = rig.solve(pz, clip.twoh)
            for n in rig.anim_bones:
                q = local[n]
                pq = prev.get(n)
                if pq is not None and pq.dot(q) < 0:
                    q = -q
                prev[n] = q
                pb = pbs[n]
                pb.rotation_quaternion = q
                pb.keyframe_insert('rotation_quaternion', frame=f)
            hp = pbs['hips']
            hp.location = loc
            hp.keyframe_insert('location', frame=f)
            # diagnostics
            sh = info['short']
            dg['leg'] = max(dg['leg'], sh['legL'], sh['legR'])
            dg['arm'] = max(dg['arm'], sh['armL'], sh['armR'])
            dg['wrist'] = max(dg['wrist'], info['wrist']['R'], info['wrist']['L'])
            dg['ext_max'] = max(dg['ext_max'], info['extL'], info['extR'])
            dg['ext_min'] = min(dg['ext_min'], info['extL'], info['extR'])
            zf = []
            for S, sx in SIDES:
                L = rig.leg[S]
                zf.append(min(rig.point(info, 'foot_' + S, L['heel']).z, rig.point(info, 'foot_' + S, L['ball']).z,
                              rig.point(info, 'toe_' + S, L['tip']).z))
            dg['zfoot_max'] = max(dg['zfoot_max'], min(zf))
            pos = info['pos']
            parts = {'head': rig.point(info, 'head', (0, -0.012, 1.705)).z - 0.09, 'chest': pos['spine_03'].z - 0.11,
                     'hips': pos['hips'].z - 0.10, 'handL': pos['hand_L'].z - 0.025, 'handR': pos['hand_R'].z - 0.025,
                     'elbowL': pos['forearm_L'].z - 0.04, 'elbowR': pos['forearm_R'].z - 0.04,
                     'kneeL': pos['shin_L'].z - 0.055, 'kneeR': pos['shin_R'].z - 0.055,
                     'ankleL': pos['foot_L'].z - 0.04, 'ankleR': pos['foot_R'].z - 0.04}
            wn = min(parts, key=parts.get)
            if parts[wn] < dg['body_zmin']:
                dg['body_zmin'], dg['body_worst'] = parts[wn], '%s@f%d' % (wn, f)
            zw = min(zf)
            if zw <= dg['zmin']:
                dg['zmin_f'] = f
            dg['zmin'] = min(dg['zmin'], zw)
            dg['hipxy'] = max(dg['hipxy'], math.hypot(pos['hips'].x, pos['hips'].y))
            if 'bladeR' in info and clip.props in BLADE_LEN:
                gp, bdir = info['bladeR']
                dg['tipz'] = min(dg.get('tipz', 9.0), (gp + bdir * BLADE_LEN[clip.props]).z)
            cur = [tuple(local[n]) for n in rig.anim_bones] + [tuple(loc)]
            if first is None:
                first = (dict(local), loc.copy())
            frames.append(info)
        # loop / end error vs first frame
        le = 0.0
        for n in rig.anim_bones:
            ang = math.degrees(first[0][n].rotation_difference(local[n]).angle)
            le = max(le, min(ang, 360.0 - ang))
        dg['loop_err'] = le
        dg['loop_loc'] = (first[1] - loc).length
        self.actions[clip.name] = act
        self.diag[clip.name] = dg
        if getattr(self, 'keyinfo', False) and clip.keys:
            for t, _ in sorted(clip.keys, key=lambda k: k[0]):
                f = min(N, int(round(t / clip.dur * N)))
                inf = frames[f]
                tip = ''
                if 'bladeR' in inf and clip.props in BLADE_LEN:
                    gp, bdir = inf['bladeR']
                    tp = gp + bdir * BLADE_LEN[clip.props]
                    tip = 'grip(%.2f %.2f %.2f) tip(%.2f %.2f %.2f)' % (gp.x, gp.y, gp.z, tp.x, tp.y, tp.z)
                ps = inf['pos']
                print('   key t=%.2f f=%2d wrist R%3.0f L%3.0f short aR %.2f aL %.2f lL %.2f lR %.2f | z knee %.2f %.2f elbow %.2f %.2f hand %.2f %.2f ankle %.2f %.2f chest %.2f head %.2f | %s'
                      % (t, f, inf['wrist']['R'], inf['wrist']['L'], inf['short']['armR'], inf['short']['armL'],
                         inf['short']['legL'], inf['short']['legR'], ps['shin_L'].z, ps['shin_R'].z,
                         ps['forearm_L'].z, ps['forearm_R'].z, ps['hand_L'].z, ps['hand_R'].z,
                         ps['foot_L'].z, ps['foot_R'].z, ps['spine_03'].z, ps['head'].z, tip))
        clip.frames_info = frames
        if verbose:
            warn = []
            if dg['leg'] > 0.004:
                warn.append('LEG_SHORT %.3f' % dg['leg'])
            if dg['arm'] > 0.004:
                warn.append('ARM_SHORT %.3f' % dg['arm'])
            if dg['wrist'] > 75:
                warn.append('WRIST %.0f' % dg['wrist'])
            if dg['zmin'] < -0.012:
                warn.append('FOOT_SINK %.3f@f%s' % (dg['zmin'], dg.get('zmin_f')))
            if clip.grounded and dg['zfoot_max'] > 0.02:
                warn.append('FLOAT %.3f' % dg['zfoot_max'])
            if dg.get('tipz', 1.0) < -0.03:
                warn.append('TIP_SINK %.3f' % dg['tipz'])
            if dg['hipxy'] > 0.2:
                warn.append('HIP_XY %.2f' % dg['hipxy'])
            if dg['body_zmin'] < -0.02:
                warn.append('BODY_SINK %.3f %s' % (dg['body_zmin'], dg.get('body_worst')))
            if clip.loop and (dg['loop_err'] > 0.05 or dg['loop_loc'] > 1e-4):
                warn.append('LOOP_ERR %.2f deg %.4f m' % (dg['loop_err'], dg['loop_loc']))
            print('BAKED %-14s %5.2fs %3d fr  ext[%.2f..%.3f] wrist %3.0f end-vs-start %5.1f deg  %s'
                  % (clip.name, clip.dur, N, dg['ext_min'], dg['ext_max'], dg['wrist'], dg['loop_err'], ' '.join(warn)))
        return act

    def activate(self, clip):
        self.arm.animation_data.action = self.actions[clip.name]
        show_props(self.props, clip.props)

    def strip(self, clip, path=None, n=None, view=None, res=None, cols=None, bounds=None):
        self.activate(clip)
        n = n or clip.nstrip
        N = clip.nframes
        if clip.loop:
            frames = [int(round(i * N / n)) for i in range(n)]
        else:
            frames = [int(round(i * N / (n - 1))) for i in range(n)]
        view = view or clip.view
        b = bounds or clip.bounds
        vd = VIEWS.get(view, view)
        k = b / math.sqrt(3.0)
        cz = getattr(clip, 'cam_z', 0.92)
        fb = (Vector((-k, -k, cz - k)), Vector((k, k, cz + k)))
        path = path or os.path.join(PREVIEWS, 'anim_%s.png' % clip.name)
        render_sheet(path, [self.man], views=(vd,), res=res or 384, cols=cols or 4, frames=frames, fixed_bounds=fb)
        return path


VIEWS = {'persp': Vector((0.62, 0.70, -0.34)),       # camera in front, on the character's RIGHT (sword side)
         'persp_l': Vector((-0.62, 0.70, -0.34)),
         'right': Vector((1, 0, 0)),                 # side view, character faces image right
         'left': Vector((-1, 0, 0)),
         'front': Vector((0, 1, 0)), 'back': Vector((0, -1, 0)),
         'top': Vector((0.0001, 0.35, -1)), 'back_r': Vector((0.6, -0.7, -0.35)),
         'side_r': Vector((0.95, 0.25, -0.18))}


# ----------------------------------------------------------------------------- glb time patch
def glb_rescale_times(path, scales):
    """scales: {animation name: factor}. Multiplies the keyframe times of the given animations (used for
    clips whose duration is not a whole number of frames at 30 fps: they are baked on ceil(d*30) frames and
    squeezed to the exact duration). Accessors shared with other animations are duplicated first."""
    with open(path, 'rb') as f:
        data = f.read()
    clen = struct.unpack_from('<I', data, 12)[0]
    js = json.loads(data[20:20 + clen].decode('utf8'))
    boff = 20 + clen
    blen = struct.unpack_from('<I', data, boff)[0]
    binb = bytearray(data[boff + 8: boff + 8 + blen])
    acc, bvs = js['accessors'], js['bufferViews']
    users = {}
    for a in js.get('animations', []):
        for s in a['samplers']:
            users.setdefault(s['input'], set()).add(a.get('name'))
    done = {}
    for a in js.get('animations', []):
        name = a.get('name')
        k = scales.get(name)
        if not k or abs(k - 1.0) < 1e-9:
            continue
        for s in a['samplers']:
            ai = s['input']
            key = (ai, name)
            if key in done:
                s['input'] = done[key]
                continue
            A = acc[ai]
            bv = bvs[A['bufferView']]
            o = bv.get('byteOffset', 0) + A.get('byteOffset', 0)
            n = A['count']
            vals = np.frombuffer(bytes(binb[o:o + 4 * n]), dtype='<f4').astype(np.float64) * k
            raw = vals.astype('<f4').tobytes()
            if users[ai] - {name}:
                while len(binb) % 4:
                    binb.append(0)
                bvs.append({'buffer': 0, 'byteOffset': len(binb), 'byteLength': len(raw)})
                binb.extend(raw)
                A2 = dict(A)
                A2['bufferView'] = len(bvs) - 1
                A2['byteOffset'] = 0
                A2['min'], A2['max'] = [float(vals.min())], [float(vals.max())]
                acc.append(A2)
                done[key] = len(acc) - 1
                s['input'] = done[key]
            else:
                binb[o:o + 4 * n] = raw
                A['min'], A['max'] = [float(np.float32(vals.min()))], [float(np.float32(vals.max()))]
                done[key] = ai
    while len(binb) % 4:
        binb.append(0)
    js['buffers'][0]['byteLength'] = len(binb)
    jb = json.dumps(js, separators=(',', ':')).encode('utf8')
    while len(jb) % 4:
        jb += b' '
    out = bytearray()
    out += struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(jb) + 8 + len(binb))
    out += struct.pack('<I4s', len(jb), b'JSON') + jb
    out += struct.pack('<I4s', len(binb), b'BIN\x00') + bytes(binb)
    with open(path, 'wb') as f:
        f.write(out)


def glb_clean_animations(path, keep_translation=('hips',), skip_prefixes=('weapon_', 'shield_', 'sheath_'), skip_names=('root',)):
    """The Blender exporter writes translation / rotation / scale channels for EVERY bone (constant ones as
    2-key STEP tracks). The clips must stay retargetable to other proportions, so keep only: rotation of the
    animated bones + translation of hips. Unused accessors / buffer views are dropped and the binary chunk is
    repacked. Returns (channels kept, channels removed)."""
    with open(path, 'rb') as f:
        data = f.read()
    clen = struct.unpack_from('<I', data, 12)[0]
    js = json.loads(data[20:20 + clen].decode('utf8'))
    boff = 20 + clen
    blen = struct.unpack_from('<I', data, boff)[0]
    binb = data[boff + 8: boff + 8 + blen]
    nodes = js['nodes']
    kept = removed = 0
    for an in js.get('animations', []):
        chans, samplers, smap = [], [], {}
        for ch in an['channels']:
            nm = nodes[ch['target']['node']].get('name', '')
            pth = ch['target']['path']
            ok = (pth == 'rotation' or (pth == 'translation' and nm in keep_translation))
            if nm in skip_names or nm.startswith(skip_prefixes):
                ok = False
            if not ok:
                removed += 1
                continue
            si = ch['sampler']
            if si not in smap:
                smap[si] = len(samplers)
                samplers.append(an['samplers'][si])
            ch = dict(ch)
            ch['sampler'] = smap[si]
            chans.append(ch)
            kept += 1
        an['channels'], an['samplers'] = chans, samplers
    # ---- garbage-collect accessors / bufferViews, repack the buffer
    used = []

    def use(i):
        if i is not None and i not in used:
            used.append(i)

    for m in js.get('meshes', []):
        for pr in m['primitives']:
            use(pr.get('indices'))
            for a in pr['attributes'].values():
                use(a)
            for tg in pr.get('targets', []):
                for a in tg.values():
                    use(a)
    for sk in js.get('skins', []):
        use(sk.get('inverseBindMatrices'))
    for an in js.get('animations', []):
        for sm in an['samplers']:
            use(sm['input'])
            use(sm['output'])
    amap = {old: new for new, old in enumerate(used)}
    acc = [dict(js['accessors'][i]) for i in used]
    bvmap, bvs, out = {}, [], bytearray()
    for a in acc:
        bi = a['bufferView']
        if bi not in bvmap:
            bv = dict(js['bufferViews'][bi])
            o = bv.get('byteOffset', 0)
            while len(out) % 4:
                out.append(0)
            chunk = binb[o:o + bv['byteLength']]
            bv['byteOffset'] = len(out)
            out.extend(chunk)
            bvmap[bi] = len(bvs)
            bvs.append(bv)
        a['bufferView'] = bvmap[bi]
    for m in js.get('meshes', []):
        for pr in m['primitives']:
            if 'indices' in pr:
                pr['indices'] = amap[pr['indices']]
            pr['attributes'] = {k: amap[v] for k, v in pr['attributes'].items()}
            if 'targets' in pr:
                pr['targets'] = [{k: amap[v] for k, v in tg.items()} for tg in pr['targets']]
    for sk in js.get('skins', []):
        if 'inverseBindMatrices' in sk:
            sk['inverseBindMatrices'] = amap[sk['inverseBindMatrices']]
    for an in js.get('animations', []):
        for sm in an['samplers']:
            sm['input'], sm['output'] = amap[sm['input']], amap[sm['output']]
    js['accessors'], js['bufferViews'] = acc, bvs
    while len(out) % 4:
        out.append(0)
    js['buffers'][0]['byteLength'] = len(out)
    jb = json.dumps(js, separators=(',', ':')).encode('utf8')
    while len(jb) % 4:
        jb += b' '
    res = bytearray()
    res += struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(jb) + 8 + len(out))
    res += struct.pack('<I4s', len(jb), b'JSON') + jb
    res += struct.pack('<I4s', len(out), b'BIN\x00') + bytes(out)
    with open(path, 'wb') as f:
        f.write(res)
    return kept, removed
