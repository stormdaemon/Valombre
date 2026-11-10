"""Post-process of assets/models/char/human.glb (pure python + numpy).

The glTF exporter recomputes the normals of every mesh that has shape keys, per mesh object. The body is
exported as 6 region meshes that share their border vertices, so the exporter's normals (base AND morph
normals) differ on the two sides of a border and a shading seam appears. fix_body_normals() welds the
regions by position, recomputes angle weighted normals of the base and of every morph target on the welded
surface and writes them back: duplicated border vertices then carry identical normals / morph normals.

read_glb / write_glb re-serialise the whole file (dense accessors, sparse accessors for morph targets).
"""
import json, struct
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}


def read_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    clen, ctype = struct.unpack_from('<II', data, 12)
    js = json.loads(data[20:20 + clen].decode('utf8'))
    off = 20 + clen
    blen, btype = struct.unpack_from('<II', data, off)
    binc = data[off + 8: off + 8 + blen]
    arrays = [_acc_array(js, binc, i) for i in range(len(js.get('accessors', [])))]
    return js, arrays


def _view(js, binc, bvi, offset, count, dtype, ncomp):
    bv = js['bufferViews'][bvi]
    start = bv.get('byteOffset', 0) + offset
    isz = np.dtype(dtype).itemsize * ncomp
    stride = bv.get('byteStride')
    if stride and stride != isz:
        raw = np.frombuffer(binc, np.uint8, count=stride * (count - 1) + isz, offset=start)
        idx = np.arange(count)[:, None] * stride + np.arange(isz)[None, :]
        return np.ascontiguousarray(raw[idx]).view(dtype).reshape(count, ncomp).copy()
    return np.frombuffer(binc, dtype, count=count * ncomp, offset=start).reshape(count, ncomp).copy()


def _acc_array(js, binc, i):
    a = js['accessors'][i]
    dt = CT[a['componentType']]
    nc = NC[a['type']]
    n = a['count']
    if 'bufferView' in a:
        arr = _view(js, binc, a['bufferView'], a.get('byteOffset', 0), n, dt, nc)
    else:
        arr = np.zeros((n, nc), dt)
    if 'sparse' in a:
        sp = a['sparse']
        cnt = sp['count']
        idx = _view(js, binc, sp['indices']['bufferView'], sp['indices'].get('byteOffset', 0), cnt,
                    CT[sp['indices']['componentType']], 1)[:, 0]
        val = _view(js, binc, sp['values']['bufferView'], sp['values'].get('byteOffset', 0), cnt, dt, nc)
        arr[idx] = val
    return arr


def write_glb(path, js, arrays):
    assert not js.get('images'), 'images are not supported by this writer'
    idx_acc, attr_acc, morph_acc = set(), set(), set()
    for m in js.get('meshes', []):
        for p in m['primitives']:
            if 'indices' in p:
                idx_acc.add(p['indices'])
            attr_acc.update(p['attributes'].values())
            for t in p.get('targets', []):
                morph_acc.update(t.values())
    buf = bytearray()
    views = []

    def add_view(raw, target=None):
        while len(buf) % 4:
            buf.append(0)
        v = {'buffer': 0, 'byteOffset': len(buf), 'byteLength': len(raw)}
        if target:
            v['target'] = target
        buf.extend(raw)
        views.append(v)
        return len(views) - 1

    for i, a in enumerate(js.get('accessors', [])):
        arr = np.ascontiguousarray(arrays[i], dtype=CT[a['componentType']])
        a.pop('bufferView', None)
        a.pop('byteOffset', None)
        a.pop('sparse', None)
        a['count'] = int(arr.shape[0])
        if 'min' in a or i in morph_acc and a['type'] == 'VEC3' and a['componentType'] == 5126:
            if 'min' in a:
                a['min'] = [float(x) for x in arr.min(0)] if a['componentType'] == 5126 else [int(x) for x in arr.min(0)]
                a['max'] = [float(x) for x in arr.max(0)] if a['componentType'] == 5126 else [int(x) for x in arr.max(0)]
        if i in morph_acc:
            nz = np.where(np.any(arr != 0, axis=1))[0]
            if len(nz) == 0:
                nz = np.array([0])
            it = np.uint16 if nz[-1] < 65536 else np.uint32
            dense = arr.nbytes
            sparse = len(nz) * (np.dtype(it).itemsize + arr.itemsize * arr.shape[1]) + 234
            if sparse < dense:
                bi = add_view(nz.astype(it).tobytes())
                bvv = add_view(arr[nz].tobytes())
                a['sparse'] = {'count': int(len(nz)),
                               'indices': {'bufferView': bi, 'componentType': 5123 if it == np.uint16 else 5125},
                               'values': {'bufferView': bvv}}
                continue
        target = 34963 if i in idx_acc else (34962 if (i in attr_acc or i in morph_acc) else None)
        a['bufferView'] = add_view(arr.tobytes(), target)
    while len(buf) % 4:
        buf.append(0)
    js['bufferViews'] = views
    js['buffers'] = [{'byteLength': len(buf)}]
    jb = json.dumps(js, separators=(',', ':'), ensure_ascii=False).encode('utf8')
    while len(jb) % 4:
        jb += b' '
    total = 12 + 8 + len(jb) + 8 + len(buf)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<I4s', len(jb), b'JSON'))
        f.write(jb)
        f.write(struct.pack('<I4s', len(buf), b'BIN\x00'))
        f.write(bytes(buf))
    return total


def _vertex_normals(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    fn = np.cross(b - a, c - a)
    ln = np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(ln, 1e-20)[:, None]
    N = np.zeros_like(P)
    for i0, i1, i2 in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        u = P[T[:, i1]] - P[T[:, i0]]
        v = P[T[:, i2]] - P[T[:, i0]]
        cs = (u * v).sum(1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-20)
        ang = np.arccos(np.clip(cs, -1.0, 1.0))
        np.add.at(N, T[:, i0], fn * ang[:, None])
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-20)[:, None]
    return N


def fix_body_normals(js, arrays, mesh_names):
    """Recompute NORMAL and morph NORMAL deltas of the given meshes on their welded union."""
    prims = []
    for m in js['meshes']:
        if m['name'] in mesh_names:
            for p in m['primitives']:
                prims.append(p)
    pos = [arrays[p['attributes']['POSITION']].astype(np.float32) for p in prims]
    counts = [len(x) for x in pos]
    allp = np.ascontiguousarray(np.concatenate(pos, 0))
    key = allp.view(np.dtype((np.void, 12))).ravel()
    uniq, first, inv = np.unique(key, return_index=True, return_inverse=True)
    inv = inv.ravel()
    PW = allp[first].astype(np.float64)
    tris = []
    off = 0
    for p, n in zip(prims, counts):
        t = arrays[p['indices']].astype(np.int64).reshape(-1, 3) + off
        tris.append(inv[t])
        off += n
    T = np.concatenate(tris, 0)
    T = T[(T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])]
    N0 = _vertex_normals(PW, T)
    old = np.concatenate([arrays[p['attributes']['NORMAL']] for p in prims], 0)
    agree = float((old * N0[inv]).sum(1).mean())
    ntarget = len(prims[0].get('targets', []))
    off = 0
    for p, n in zip(prims, counts):
        arrays[p['attributes']['NORMAL']] = N0[inv[off:off + n]].astype(np.float32)
        off += n
    maxdup = 0.0
    for ti in range(ntarget):
        dall = np.concatenate([arrays[p['targets'][ti]['POSITION']] for p in prims], 0).astype(np.float64)
        DW = dall[first]
        maxdup = max(maxdup, float(np.abs(dall - DW[inv]).max()))
        moved = np.any(DW != 0, axis=1)
        if moved.any():
            Nt = _vertex_normals(PW + DW, T)
            dn = Nt - N0
            dn[np.abs(dn).max(1) < 2e-4] = 0.0
        else:
            dn = np.zeros_like(N0)
        off = 0
        for p, n in zip(prims, counts):
            if 'NORMAL' in p['targets'][ti]:
                arrays[p['targets'][ti]['NORMAL']] = dn[inv[off:off + n]].astype(np.float32)
            off += n
    return {'welded_vertices': int(len(PW)), 'gltf_vertices': int(len(allp)), 'normal_agreement': round(agree, 4),
            'max_morph_delta_mismatch_on_duplicates': maxdup, 'targets': ntarget}


def describe(js, arrays):
    out = []
    for m in js['meshes']:
        for p in m['primitives']:
            at = p['attributes']
            n = len(arrays[at['POSITION']])
            d = {'mesh': m['name'], 'material': js['materials'][p['material']]['name'] if 'material' in p else None,
                 'verts': n, 'tris': len(arrays[p['indices']]) // 3, 'attrs': sorted(at.keys()),
                 'targets': len(p.get('targets', [])),
                 'targetNames': len((m.get('extras') or {}).get('targetNames', []))}
            if 'WEIGHTS_0' in at:
                w = arrays[at['WEIGHTS_0']].astype(np.float64)
                d['weight_sum_min'] = round(float(w.sum(1).min()), 4)
                d['weight_sum_max'] = round(float(w.sum(1).max()), 4)
                d['max_influences'] = int((w > 0).sum(1).max())
            out.append(d)
    return out
