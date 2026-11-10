"""ROYAL set: bascinet fused with a tarnished crown, gilded cuirass with a high gorget, large pauldrons and a
torn cape, gilded leg harness."""
from outfit_parts import *
from outfit_set_plate import plate_arms, plate_torso, plate_leg_parts, eye_slits


def cape_weights(P, Wa):
    z = P[:, 2]
    W = np.zeros_like(Wa)
    t = sstep(1.50, 1.30, z)
    W[:, BI['spine_03']] = 1 - t
    t2 = sstep(1.30, 1.05, z)
    W[:, BI['spine_02']] = t * (1 - t2)
    t3 = sstep(1.05, 0.80, z)
    W[:, BI['hips']] = t * t2 * (1 - 0.45 * t3)
    sl = sstep(-0.08, 0.08, P[:, 0])
    W[:, BI['thigh_L']] = t * t2 * 0.45 * t3 * sl
    W[:, BI['thigh_R']] = t * t2 * 0.45 * t3 * (1 - sl)
    return W


def royal_chest(K):
    p = Piece('royal_chest', K)
    gold = ('M_metal_gold', cfn('#b08d3e', 0.14, 0.04, 41))
    dark = cfn('#5d6068', 0.12, 0.015, 42)
    plate_torso(p, K, gold, dark, gorget=((0.010, 0.045), (0.018, 0.015)))
    plate_arms(p, K, gold, dark, big=1.25)
    # torn cape
    cape = cfn('#5b1f2a', 0.14, 0.09, 43, dirt=(0.30, 0.7, 0.4))
    az = np.radians(np.linspace(100, 260, 11))
    zs = np.array([1.50, 1.44, 1.34, 1.22, 1.10, 0.98, 0.85, 0.72, 0.58, 0.45, 0.33])
    G = np.zeros((len(zs), len(az), 3))
    for i, z in enumerate(zs):
        r = K.torso.rad(min(z, 1.45), az, 1.0) + 0.045 + 0.05 * sstep(1.3, 0.4, z) + 0.012 * np.cos(5 * az + 2.0 * i) * sstep(1.45, 1.0, z)
        if z > 1.45:
            r = K.torso.rad(1.45, az, 1.0) + 0.040
        G[i] = torso_center(z) + dirxy(az) * r[:, None]
    G[0, :, 2] = 1.535
    G[-1, :, 2] += 0.09 * vnoise(np.stack([az * 3, az * 0, az * 0], 1), 1.0, 9)
    p.grid(G, 'M_cloth', cape, closed=False, flip=True, src='body', w=cape_weights)
    p.lining(G, 'M_cloth', lambda P: cape(P) * 0.6, closed=False, flip=True, src='body', w=cape_weights, inset=0.006)
    return p


def royal_legs(K):
    p = Piece('royal_legs', K)
    plate_leg_parts(p, K, ('M_metal_steel', cfn('#7d8087', 0.1, 0.04, 44)), cfn('#5d6068', 0.12, 0.015, 45),
                    trim=cfn('#b08d3e', 0.14, 0.04, 46))
    return p


def royal_head(K):
    p = Piece('royal_head', K)
    steel = cfn('#7d8087', 0.1, 0.04, 47)
    zs = [1.555, 1.60, 1.66, 1.72, 1.775, 1.82, 1.855, 1.875]
    rx = [0.106, 0.106, 0.105, 0.103, 0.095, 0.070, 0.035, 0.0005]
    ry = [0.128, 0.130, 0.130, 0.126, 0.116, 0.088, 0.045, 0.0005]
    G = helm_rows(K, zs, rx, ry)
    G[..., 1] -= 0.03 * np.maximum(np.cos(wrap(angles(24))), 0)[None, :] ** 3 * np.array([0.5, 1, 1, 0.6, 0.2, 0, 0, 0])[:, None]
    G[5:, :, 1] += np.array([0.012, 0.03, 0.04])[:, None]
    p.grid(G, 'M_metal_steel', steel, weld=True, w={'head': 1.0}, src='head')
    eye_slits(p, K, G, zs, 1.683, 1.694, 8, 55)
    gold = cfn('#b08d3e', 0.16, 0.03, 48)
    A = angles(24)
    base = np.stack([helm_point(K, G, zs, a, 1.745, 0.004) for a in A])
    top = np.stack([helm_point(K, G, zs, a, 1.775, 0.010) for a in A])
    spike = top + (dirxy(A) * 0.012 + UP * 0.035) * (np.arange(24) % 2)[:, None]
    p.grid(np.stack([base, top, spike]), 'M_metal_gold', gold, w={'head': 1.0}, src='head')
    aventail(p, 'M_metal_iron', cfn('#5d6068', 0.12, 0.015, 49), top_z=1.57, top_off=0.018)
    return p


PIECES = {
    'royal_head': (royal_head, ['hair', 'beard'], 'bascinet fused with a tarnished gold crown, mail aventail'),
    'royal_chest': (royal_chest, ['body_torso', 'body_arms', 'body_hands'], 'gilded cuirass with a high gorget, large pauldrons, torn cape to the calves'),
    'royal_legs': (royal_legs, ['body_legs', 'body_feet'], 'dark steel leg harness with gilded poleyns'),
}
