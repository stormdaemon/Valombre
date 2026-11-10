// Static architecture & props: placed instances are merged per material into spatial chunks (few draw
// calls for a whole village), colliders / walkable boxes / anchors are extracted from the special nodes.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { loadGLB, loadJSON } from '../core/assets.js';
import { getMaterial } from '../render/materials.js';

const CHUNK = 96;
const _m = new THREE.Matrix4(), _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _e = new THREE.Euler();

export class Structures {
  constructor(engine, collision) {
    this.engine = engine; this.collision = collision;
    this.group = new THREE.Group();
    this.templates = new Map();     // name -> { meshes:[{geometry, material, matrix}], nodes:[{name, type, matrix, ...}], rot:[...] }
    this.manifest = {};
    this.batches = new Map();       // chunkKey|materialKey -> { material, geos: [] }
    this.dynamic = [];              // ROT_ objects
    this.count = 0;
  }

  async loadManifests() {
    const [a, b, idx] = await Promise.all([loadJSON('assets/models/arch/manifest_village.json'), loadJSON('assets/models/arch/manifest_world.json'), loadJSON('assets/models/index.json')]);
    for (const m of [a, b]) if (m && m.assets) Object.assign(this.manifest, m.assets);
    this.files = new Set(idx && idx.arch ? idx.arch : []);
    return this;
  }

  /** a model can be placed if it is described in a manifest or simply present on disk (index.json) */
  has(name) { return !!this.manifest[name] || this.files.has(name); }
  info(name) { return this.manifest[name]; }

  /** load (once) and analyse a model */
  async template(name) {
    if (this.templates.has(name)) return this.templates.get(name);
    const p = (async () => {
      const def = this.manifest[name];
      const gltf = await loadGLB('assets/models/arch/' + (def ? def.file : name + '.glb'));
      if (!gltf) return null;
      const T = { meshes: [], nodes: [], rot: [] };
      gltf.scene.updateMatrixWorld(true);
      const visit = (o, inRot) => {
        const n = o.name || '';
        const tag = /^(COL|WALK|FIRE|SMOKE|GLOW|ANCHOR|ROT)_/.exec(n);
        if (tag && tag[1] !== 'ROT') {
          const kind = tag[1];
          o.matrixWorld.decompose(_p, _q, _s);
          _e.setFromQuaternion(_q, 'YXZ');
          T.nodes.push({ name: n, kind, pos: _p.clone(), yaw: _e.y, half: new THREE.Vector3(Math.abs(_s.x) * 0.5, Math.abs(_s.y) * 0.5, Math.abs(_s.z) * 0.5) });
          return;     // colliders / anchors are not rendered
        }
        if (tag && tag[1] === 'ROT' && !inRot) {
          const meshes = [];
          o.traverse((c) => { if (c.isMesh) meshes.push(c); });
          const pivot = new THREE.Matrix4().copy(o.matrixWorld);
          const inv = new THREE.Matrix4().copy(pivot).invert();
          T.rot.push({ name: n, pivot, parts: meshes.map(c => ({ geometry: c.geometry, material: this._mat(c), matrix: new THREE.Matrix4().multiplyMatrices(inv, c.matrixWorld) })) });
          return;
        }
        if (o.isMesh) T.meshes.push({ geometry: o.geometry, material: this._mat(o), matrix: o.matrixWorld.clone() });
        for (const c of o.children) visit(c, inRot);
      };
      visit(gltf.scene, false);
      return T;
    })();
    this.templates.set(name, p);
    return p;
  }

  _mat(mesh) {
    const name = (mesh.material && mesh.material.name ? mesh.material.name : 'M_proxy').replace(/\.\d+$/, '');
    return getMaterial(name, { vertexColors: !!mesh.geometry.attributes.color, doubleSide: name === 'M_cloth' ? false : false });
  }

  /**
   * Place a model. opts: y (absolute base height; default = terrain), sink (m), scale, collide (default true).
   * Returns { anchors: {NAME: Vector3 world}, fires: [Vector3], smokes: [...], glows: [...], rot: {NAME: Object3D}, pos, yaw } or null.
   */
  async place(name, x, z, yaw = 0, opts = {}) {
    const T = await this.template(name);
    if (!T) return null;
    const world = this.engine.world;
    const scale = opts.scale || 1;
    const y = (opts.y ?? world.height(x, z)) - (opts.sink || 0);
    _q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, yaw);
    const M = new THREE.Matrix4().compose(_p.set(x, y, z), _q, _s.set(scale, scale, scale));
    const ck = Math.floor(x / CHUNK) + ',' + Math.floor(z / CHUNK);
    for (const part of T.meshes) {
      const key = ck + '|' + part.material.uuid;
      let b = this.batches.get(key);
      if (!b) this.batches.set(key, b = { material: part.material, geos: [] });
      const g = part.geometry.clone();
      g.applyMatrix4(_m.multiplyMatrices(M, part.matrix));
      // keep only what the shaders use, with uniform types, so that merging works
      for (const an of Object.keys(g.attributes)) if (!['position', 'normal', 'uv', 'color'].includes(an)) g.deleteAttribute(an);
      const col = g.attributes.color;
      if (col && (col.itemSize !== 3 || !(col.array instanceof Float32Array))) {
        const f = new Float32Array(col.count * 3);
        for (let i = 0; i < col.count; i++) { f[i * 3] = col.getX(i); f[i * 3 + 1] = col.getY(i); f[i * 3 + 2] = col.getZ(i); }
        g.setAttribute('color', new THREE.BufferAttribute(f, 3));
      }
      if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
      if (g.index && !(g.index.array instanceof Uint32Array)) g.setIndex(new THREE.BufferAttribute(new Uint32Array(g.index.array), 1));
      b.geos.push(g);
    }
    const out = { anchors: {}, fires: [], smokes: [], glows: [], rot: {}, pos: new THREE.Vector3(x, y, z), yaw, name };
    const c = Math.cos(yaw), s = Math.sin(yaw);
    for (const n of T.nodes) {
      // rotation about Y by yaw: x' = x cos + z sin ; z' = -x sin + z cos
      const wx = x + (n.pos.x * c + n.pos.z * s) * scale, wz = z + (-n.pos.x * s + n.pos.z * c) * scale, wy = y + n.pos.y * scale;
      if (n.kind === 'COL') { if (opts.collide !== false) this.collision.addBox(wx, wz, n.half.x * scale, n.half.z * scale, -(yaw + n.yaw), wy - n.half.y * scale - 0.3, wy + n.half.y * scale, name); }
      else if (n.kind === 'WALK') this.collision.addWalk(wx, wz, n.half.x * scale, n.half.z * scale, -(yaw + n.yaw), wy + n.half.y * scale);
      else {
        const v = new THREE.Vector3(wx, wy, wz);
        if (n.kind === 'FIRE') out.fires.push(v); else if (n.kind === 'SMOKE') out.smokes.push(v); else if (n.kind === 'GLOW') out.glows.push(v);
        out.anchors[n.name] = v;
      }
    }
    for (const r of T.rot) {
      const holder = new THREE.Group();
      holder.applyMatrix4(_m.multiplyMatrices(M, r.pivot));
      for (const part of r.parts) { const mesh = new THREE.Mesh(part.geometry, part.material); mesh.applyMatrix4(part.matrix); mesh.castShadow = true; mesh.receiveShadow = true; holder.add(mesh); }
      this.group.add(holder);
      out.rot[r.name] = holder;
      this.dynamic.push(holder);
    }
    this.count++;
    return out;
  }

  /** merge everything placed so far into chunk meshes (call after a batch of place() calls) */
  build() {
    let meshes = 0, tris = 0;
    const perChunk = new Map();
    for (const [key, b] of this.batches) {
      if (!b.geos.length) continue;
      let merged;
      try { merged = mergeGeometries(b.geos, false); } catch (e) { merged = null; }
      if (!merged) {
        // attribute mismatch between sources: normalise then retry
        const names = ['position', 'normal', 'uv', 'color'];
        for (const g of b.geos) for (const an of names) if (!g.attributes[an]) { const n = g.attributes.position.count, sz = an === 'uv' ? 2 : 3; const arr = new Float32Array(n * sz); if (an === 'color') arr.fill(1); g.setAttribute(an, new THREE.BufferAttribute(arr, sz)); }
        merged = mergeGeometries(b.geos, false);
      }
      for (const g of b.geos) g.dispose();
      b.geos.length = 0;
      if (!merged) continue;
      merged.computeBoundingSphere();
      const mesh = new THREE.Mesh(merged, b.material);
      // shadows are cast by one position-only proxy per chunk (below): 1 draw call instead of 1 per material
      mesh.castShadow = false; mesh.receiveShadow = true; mesh.matrixAutoUpdate = false;
      this.group.add(mesh);
      meshes++; tris += merged.index ? merged.index.count / 3 : merged.attributes.position.count / 3;
      const ck = key.split('|')[0];
      if (!perChunk.has(ck)) perChunk.set(ck, []);
      perChunk.get(ck).push(merged);
    }
    this.batches.clear();
    for (const list of perChunk.values()) {
      const parts = list.map((g) => { const p = new THREE.BufferGeometry(); p.setAttribute('position', g.attributes.position); p.setIndex(g.index); return p; });
      let geo = null;
      try { geo = parts.length === 1 ? parts[0].clone() : mergeGeometries(parts, false); } catch (e) { geo = null; }
      if (!geo) { for (const g of list) for (const m of this.group.children) if (m.geometry === g) m.castShadow = true; continue; }
      geo.computeBoundingSphere();
      const proxy = new THREE.Mesh(geo, this._proxyMat || (this._proxyMat = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false, depthTest: false, fog: false })));
      proxy.castShadow = true; proxy.receiveShadow = false; proxy.matrixAutoUpdate = false; proxy.renderOrder = -5;
      // draw nothing in the colour pass, everything in the shadow pass
      proxy.onBeforeRender = () => { geo.setDrawRange(0, 0); };
      proxy.onBeforeShadow = () => { geo.setDrawRange(0, Infinity); };
      this.group.add(proxy);
    }
    this.stats = { meshes: (this.stats ? this.stats.meshes : 0) + meshes, tris: (this.stats ? this.stats.tris : 0) + tris, placed: this.count };
    return this.stats;
  }
}
