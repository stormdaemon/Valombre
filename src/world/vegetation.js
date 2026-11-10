// Trees, bushes, rocks: deterministic procedural placement per 64 m cell, GPU instancing with
// LOD0 / LOD1 meshes near the camera and relit billboard impostors far away. Wind in the vertex shader.
import * as THREE from 'three';
import { U, patchMaterial, inject, FOG_FUNC, SUNVIS_FUNC, WORLD_HALF } from '../core/globals.js';
import { getMaterial } from '../render/materials.js';
import { loadGLB, loadJSON, loadTexture } from '../core/assets.js';
import { hash2, mulberry32 } from '../core/rng.js';
import { BIOME } from './worlddata.js';

const CELL = 64;
const WIND_GLSL = /* glsl */`
uniform float uTime;
uniform vec4 uWind;
uniform sampler2D uNoiseTex;
vec3 valWind( vec3 wp, vec3 origin, float flutter, float phase ) {
  float t = uTime;
  vec2 wd = uWind.xy;
  float gust = texture2D( uNoiseTex, origin.xz * 0.004 - wd * t * 0.04 ).r;
  float sway = ( 0.35 + gust ) * uWind.z;
  float ph = origin.x * 0.37 + origin.z * 0.53;
  float hl = max( wp.y - origin.y, 0.0 );
  float k = hl * hl * 0.0011 * sway;
  vec3 off = vec3( wd.x, 0.0, wd.y ) * k * ( 0.7 + 0.5 * sin( t * 1.1 + ph ) );
  off += flutter * sway * 0.075 * vec3( sin( t * 3.3 + phase * 40.0 + wp.x ), 0.6 * sin( t * 4.1 + phase * 31.0 ), cos( t * 2.9 + phase * 27.0 + wp.z ) );
  return off;
}`;
const PROJECT_WIND = /* glsl */`
  vec4 mvPosition = vec4( transformed, 1.0 );
  #ifdef USE_INSTANCING
    mvPosition = instanceMatrix * mvPosition;
    vec3 natOrigin = instanceMatrix[ 3 ].xyz;
  #else
    vec3 natOrigin = vec3( 0.0 );
  #endif
  mvPosition = modelMatrix * mvPosition;
  mvPosition.xyz += valWind( mvPosition.xyz, natOrigin, color.g, color.b );
  mvPosition = viewMatrix * mvPosition;
  gl_Position = projectionMatrix * mvPosition;
`;

function natureStd(name) {
  const m = getMaterial(name, { vertexColors: false, variant: 'nature' });
  if (m.userData.nature) return m;
  m.userData.nature = true;
  patchMaterial(m, (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', `#include <common>\nattribute vec3 color;\nvarying float vNatAO;\n${WIND_GLSL}`);
    sh.vertexShader = inject(sh.vertexShader, 'begin_vertex', '#include <begin_vertex>\nvNatAO = color.r;');
    sh.vertexShader = inject(sh.vertexShader, 'project_vertex', PROJECT_WIND);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vNatAO;');
    sh.fragmentShader = inject(sh.fragmentShader, 'color_fragment', '#include <color_fragment>\ndiffuseColor.rgb *= vNatAO;');
  }, 'nat');
  return m;
}

function leafMaterial(tex, flowers = false) {
  const m = new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.42, side: THREE.DoubleSide, vertexColors: flowers });
  m.name = flowers ? 'M_flowers' : 'M_leaves';
  patchMaterial(m, (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', `#include <common>\n${flowers ? '' : 'attribute vec3 color;'}\nvarying float vNatAO;\n${WIND_GLSL}`);
    sh.vertexShader = inject(sh.vertexShader, 'begin_vertex', `#include <begin_vertex>\nvNatAO = ${flowers ? '1.0' : 'color.r'};`);
    sh.vertexShader = inject(sh.vertexShader, 'project_vertex', flowers ? PROJECT_WIND.replace('color.g, color.b', 'clamp( position.y * 1.6, 0.0, 1.0 ), 0.3') : PROJECT_WIND);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vNatAO;');
    sh.fragmentShader = inject(sh.fragmentShader, 'color_fragment', '#include <color_fragment>\ndiffuseColor.rgb *= mix( 0.5, 1.12, vNatAO );');
    sh.fragmentShader = inject(sh.fragmentShader, 'normal_fragment_begin', 'float faceDirection = 1.0;\nvec3 normal = normalize( vNormal );\nvec3 nonPerturbedNormal = normal;');
    sh.fragmentShader = inject(sh.fragmentShader, 'lights_fragment_end', /* glsl */`
      #include <lights_fragment_end>
      #if NUM_SUN_LIGHTS > 0
        vec3 lV = normalize( cameraPosition - vFogWorld );
        float lback = pow( max( dot( lV, -uSunDir ), 0.0 ), 2.5 );
        reflectedLight.directDiffuse += sunLights[ 0 ].color * diffuseColor.rgb * lback * 0.35 * vNatAO * valSunVis( vFogWorld, uSunDir );
      #endif
    `);
  }, 'leaf' + (flowers ? 'F' : ''));
  return m;
}

const IMP_VERT = /* glsl */`
attribute vec3 aPos;
attribute vec4 aSize;     // width, height, tint, phase
attribute vec4 aUV;
uniform vec4 uImpRange;   // near start, near end, far start, far end
uniform float uTime;
uniform vec4 uWind;
varying vec2 vUv;
varying vec2 vQuad;
varying vec3 vWorld;
varying vec3 vRight;
varying float vTint;
void main() {
  vec3 toCam = cameraPosition - aPos;
  float dist = length( toCam.xz );
  vec3 right = normalize( vec3( toCam.z, 0.0, -toCam.x ) );
  float show = smoothstep( uImpRange.x, uImpRange.y, dist ) * ( 1.0 - smoothstep( uImpRange.z, uImpRange.w, dist ) );
  vec3 p = aPos + right * position.x * aSize.x + vec3( 0.0, position.y * aSize.y * show, 0.0 );
  p.xz += uWind.xy * position.y * position.y * aSize.y * 0.012 * uWind.z * sin( uTime * 1.1 + aSize.w * 6.28 );
  if ( show < 0.01 ) p = vec3( 0.0, -9999.0, 0.0 );
  vUv = mix( aUV.xy, aUV.zw, vec2( position.x + 0.5, position.y ) );
  vQuad = vec2( position.x * 2.0, position.y );
  vWorld = p;
  vRight = right;
  vTint = aSize.z;
  gl_Position = projectionMatrix * viewMatrix * vec4( p, 1.0 );
}`;
const IMP_FRAG = /* glsl */`
uniform sampler2D uImpTex;
uniform vec3 uSunCol;
uniform vec3 uSkyCol;
uniform vec3 uGndCol;
varying vec2 vUv;
varying vec2 vQuad;
varying vec3 vWorld;
varying vec3 vRight;
varying float vTint;
${FOG_FUNC}
${SUNVIS_FUNC}
void main() {
  vec4 t = texture2D( uImpTex, vUv );
  if ( t.a < 0.45 ) discard;
  vec3 toCam = normalize( cameraPosition - vWorld );
  vec3 N = normalize( vRight * vQuad.x * 0.9 + vec3( 0.0, 1.0, 0.0 ) * ( vQuad.y - 0.35 ) * 1.1 + toCam * 0.55 );
  float nl = max( dot( N, uSunDir ), 0.0 ) * 0.75 + 0.1;
  float vis = valSunVis( vWorld, uSunDir );
  vec3 amb = mix( uGndCol, uSkyCol, N.y * 0.5 + 0.5 );
  vec3 alb = t.rgb * vTint;
  vec3 col = alb * ( uSunCol * nl * vis + amb ) * 0.3183;
  col += alb * uSunCol * pow( max( dot( toCam, -uSunDir ), 0.0 ), 2.5 ) * 0.1 * vis;
  gl_FragColor = vec4( valFog( col, vWorld ), 1.0 );
}`;

// species selection tables: [asset, weight]
const BROADLEAF = { [BIOME.FOREST]: [['oak_a', 4], ['oak_b', 3], ['birch_a', 2]], [BIOME.SWAMP]: [['willow_a', 5], ['oak_b', 1]], default: [['oak_a', 3], ['oak_b', 2], ['birch_a', 3]] };
const pick = (table, r) => { let tot = 0; for (const t of table) tot += t[1]; let v = r * tot; for (const t of table) { v -= t[1]; if (v <= 0) return t[0]; } return table[0][0]; };

export class Vegetation {
  constructor(world, atmo) {
    this.world = world; this.atmo = atmo;
    this.group = new THREE.Group();
    this.cells = new Map();
    this.assets = {};
    this.ready = false;
    this.q = { lod0: 42, lod1: 135, imp: 560, spacing: 7.5, under: 1 };
    this._frustum = new THREE.Frustum();
    this._pm = new THREE.Matrix4();
    this._sphere = new THREE.Sphere();
    this._m = new THREE.Matrix4();
    this._q = new THREE.Quaternion();
    this._s = new THREE.Vector3();
    this._p = new THREE.Vector3();
    this._up = new THREE.Vector3(0, 1, 0);
    this._impCenter = new THREE.Vector2(1e9, 1e9);
    this.stats = { lod0: 0, lod1: 0, imp: 0, cells: 0 };
    this.frame = 0;
  }

  setQuality(level) {
    this.q = [
      { lod0: 30, lod1: 90, imp: 380, spacing: 9.5, under: 0.45 },
      { lod0: 36, lod1: 115, imp: 480, spacing: 8.5, under: 0.7 },
      { lod0: 42, lod1: 135, imp: 600, spacing: 7.5, under: 1.0 },
      { lod0: 52, lod1: 165, imp: 800, spacing: 7.0, under: 1.3 },
    ][level] || this.q;
    this.cells.clear();
    this._impCenter.set(1e9, 1e9);
  }

  async load() {
    const man = await loadJSON('assets/models/nature/manifest.json');
    if (!man) { console.warn('[vegetation] no nature manifest'); return; }
    const [leaves, imp] = await Promise.all([
      loadTexture('assets/textures/leaves_a.png', { srgb: true, aniso: 2 }),
      loadTexture('assets/textures/impostors_a.png', { srgb: true, flipY: true, repeat: false, aniso: 1 }),
    ]);
    const leafMat = leaves ? leafMaterial(leaves) : new THREE.MeshLambertMaterial({ color: 0x3a5a22 });
    const flowerMat = leaves ? leafMaterial(leaves, true) : leafMat;
    const depthLeaf = new THREE.MeshDepthMaterial({ map: leaves, alphaTest: 0.42, side: THREE.DoubleSide });
    const names = Object.keys(man.assets);
    const glbs = await Promise.all(names.map(n => loadGLB('assets/models/nature/' + man.assets[n].file)));
    names.forEach((name, i) => {
      const def = man.assets[name], gltf = glbs[i];
      if (!gltf) return;
      const A = { name, def, lods: [], tree: def.category === 'tree', collider: def.collider, impostor: def.impostor || null };
      const isSmall = def.category === 'plant' && !def.collider;
      for (const lodName of ['LOD0', 'LOD1']) {
        const L = def.lods[lodName];
        if (!L) continue;
        const node = gltf.scene.getObjectByName(L.mesh);
        if (!node) continue;
        const meshes = [];
        node.traverse((o) => { if (o.isMesh) meshes.push(o); });
        const cap = A.tree ? (lodName === 'LOD0' ? 96 : 420) : (isSmall ? 900 : 420);
        const inst = [];
        let shared = null;
        for (const src of meshes) {
          const mn = (src.material.name || '').replace(/\.\d+$/, '');
          let mat;
          if (mn === 'M_leaves') mat = leafMat; else if (mn === 'M_flowers') mat = flowerMat;
          else if (mn === 'M_mushroom') mat = getMaterial('M_mushroom', { vertexColors: true });
          else mat = natureStd(mn);
          const im = new THREE.InstancedMesh(src.geometry, mat, cap);
          if (shared) im.instanceMatrix = shared; else shared = im.instanceMatrix;
          im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
          im.count = 0;
          im.frustumCulled = false;
          im.castShadow = !isSmall;
          im.receiveShadow = true;
          im.matrixAutoUpdate = false;
          if (mn === 'M_leaves') im.customDepthMaterial = depthLeaf;
          if (isSmall) im.renderOrder = 4;
          this.group.add(im);
          inst.push(im);
        }
        A.lods.push({ inst, cap, n: 0, attr: shared });
      }
      const b0 = def.bounds_min, b1 = def.bounds_max;
      A.radius = Math.hypot(b1[0] - b0[0], b1[1] - b0[1], b1[2] - b0[2]) * 0.5;
      A.cy = (b0[1] + b1[1]) * 0.5;
      A.small = isSmall;
      this.assets[name] = A;
    });
    // impostors
    if (imp) {
      const cap = this.impCap = 16000;
      const g = new THREE.InstancedBufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute([-0.5, 0, 0, 0.5, 0, 0, 0.5, 1, 0, -0.5, 1, 0], 3));
      g.setIndex([0, 1, 2, 0, 2, 3]);
      this.impPos = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3);
      this.impSize = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4);
      this.impUV = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4);
      for (const a of [this.impPos, this.impSize, this.impUV]) a.setUsage(THREE.DynamicDrawUsage);
      g.setAttribute('aPos', this.impPos); g.setAttribute('aSize', this.impSize); g.setAttribute('aUV', this.impUV);
      g.instanceCount = 0;
      g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);
      this.impUniforms = {
        ...U, uImpTex: { value: imp }, uImpRange: { value: new THREE.Vector4(120, 135, 520, 560) },
        uSunCol: { value: new THREE.Color() }, uSkyCol: { value: new THREE.Color() }, uGndCol: { value: new THREE.Color() },
      };
      this.impMesh = new THREE.Mesh(g, new THREE.ShaderMaterial({ vertexShader: IMP_VERT, fragmentShader: IMP_FRAG, uniforms: this.impUniforms, side: THREE.DoubleSide, fog: false }));
      this.impMesh.frustumCulled = false; this.impMesh.matrixAutoUpdate = false; this.impMesh.renderOrder = 6;
      this.group.add(this.impMesh);
    }
    this.ready = true;
  }

  // ------------------------------------------------------------------ placement
  _cell(ci, cj) {
    const k = ci * 4096 + cj;
    let c = this.cells.get(k);
    if (c) return c;
    c = { trees: [], props: [], small: [] };     // each entry: [asset, x, y, z, rot, scale, tint]
    this.cells.set(k, c);
    const w = this.world, x0 = ci * CELL, z0 = cj * CELL;
    if (Math.abs(x0 + CELL / 2) > WORLD_HALF || Math.abs(z0 + CELL / 2) > WORLD_HALF) return c;
    const rnd = mulberry32(hash2(ci, cj, 9173));
    const sp = this.q.spacing, n = Math.floor(CELL / sp);
    for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) {
      const x = x0 + (a + 0.15 + 0.7 * rnd()) * sp, z = z0 + (b + 0.15 + 0.7 * rnd()) * sp;
      const r1 = rnd(), r2 = rnd(), r3 = rnd(), r4 = rnd(), r5 = rnd();
      const dens = w.veg(x, z, 0);
      if (r1 > dens * 1.05) continue;
      const h = w.height(x, z);
      const biome = w.biome(x, z);
      if (h < (biome === BIOME.SWAMP ? 0.35 : 2.6)) continue;
      if (w.slope(x, z) > 34) continue;
      const conifer = w.veg(x, z, 1), dead = w.veg(x, z, 3);
      let asset;
      if (r2 < dead) asset = biome === BIOME.ASH ? (r3 < 0.6 ? 'dead_b' : 'dead_a') : (r3 < 0.7 ? 'dead_a' : 'dead_b');
      else if (r3 < conifer) asset = r4 < 0.6 ? 'pine_a' : 'pine_b';
      else asset = pick(BROADLEAF[biome] || BROADLEAF.default, r4);
      if (!this.assets[asset]) continue;
      const scale = 0.8 + 0.5 * r5 * r5 + (asset.startsWith('pine') ? 0.1 : 0);
      const snow = h > 190 ? Math.min((h - 190) / 60, 1) : 0;
      c.trees.push([asset, x, h - 0.15, z, rnd() * 6.283, scale, 0.82 + 0.3 * rnd() + snow * 0.35]);
    }
    // undergrowth, rocks
    const us = 4.6 / Math.sqrt(this.q.under), un = Math.floor(CELL / us);
    for (let a = 0; a < un; a++) for (let b = 0; b < un; b++) {
      const x = x0 + (a + rnd()) * us, z = z0 + (b + rnd()) * us;
      const r1 = rnd(), r2 = rnd(), r3 = rnd();
      const h = w.height(x, z);
      if (h < 0.25) continue;
      const biome = w.biome(x, z), slope = w.slope(x, z);
      const tdens = w.veg(x, z, 0), gdens = w.veg(x, z, 2);
      const road = w.splatWeight(x, z, 1);
      if (road > 0.55) { if (r1 < 0.03) c.small.push(['pebbles', x, h, z, r2 * 6.283, 0.8 + r3, 1]); continue; }
      let asset = null, sc = 1, list = c.small;
      const rockiness = w.splatWeight(x, z, 2) + (biome === BIOME.MOUNTAIN ? 0.25 : 0) + (biome === BIOME.ASH ? 0.2 : 0);
      if (r1 < 0.035 + rockiness * 0.16) {
        if (slope > 28 && r2 < 0.12 && biome === BIOME.MOUNTAIN && this.q.under >= 0.7) { asset = r3 < 0.5 ? 'cliff_a' : 'cliff_b'; sc = 0.7 + r3; list = c.props; }
        else { asset = ['rock_a', 'rock_b', 'rock_c', 'rock_d', 'rock_e', 'rock_e'][Math.floor(r2 * 6)]; sc = 0.6 + 1.6 * r3 * r3; list = c.props; }
      } else if (slope < 30) {
        if (biome === BIOME.FOREST || tdens > 0.35) {
          if (r1 < 0.30) asset = 'fern'; else if (r1 < 0.37) asset = 'bush_a'; else if (r1 < 0.42) asset = 'bush_b';
          else if (r1 < 0.45) asset = 'mushrooms'; else if (r1 < 0.465) { asset = 'stump'; list = c.props; } else if (r1 < 0.478) { asset = 'log'; list = c.props; }
          sc = 0.8 + 0.6 * r3;
        } else if (biome === BIOME.SWAMP) {
          if (r1 < 0.26 && h < 1.4) asset = 'reeds'; else if (r1 < 0.34) asset = 'fern'; else if (r1 < 0.36) asset = 'bush_b';
          sc = 0.8 + 0.7 * r3;
        } else if (biome === BIOME.MEADOW || biome === BIOME.BEACH) {
          const patch = (hash2(Math.floor(x / 22), Math.floor(z / 22), 5) % 100) / 100;
          if (gdens > 0.4 && patch < 0.3 && r1 < 0.5) asset = 'flowers_a';
          else if (r1 < 0.075) asset = r2 < 0.6 ? 'bush_a' : 'bush_b';
          sc = 0.8 + 0.6 * r3;
        } else if (biome === BIOME.MOUNTAIN && h < 200) {
          if (r1 < 0.1) asset = 'bush_b'; else if (r1 < 0.16) asset = 'fern';
          sc = 0.7 + 0.5 * r3;
        }
      }
      if (!asset || !this.assets[asset]) continue;
      const A = this.assets[asset];
      const sink = A.collider ? 0.12 * sc : 0;
      list.push([asset, x, h - sink - (asset.startsWith('cliff') ? 1.2 * sc : 0), z, r2 * 6.283, sc, 0.85 + 0.3 * rnd()]);
    }
    return c;
  }

  // ------------------------------------------------------------------ per-frame update
  _push(A, lod, e) {
    const L = A.lods[Math.min(lod, A.lods.length - 1)];
    if (!L || L.n >= L.cap) return;
    this._q.setFromAxisAngle(this._up, e[4]);
    this._s.setScalar(e[5]);
    this._p.set(e[1], e[2], e[3]);
    this._m.compose(this._p, this._q, this._s);
    this._m.toArray(L.attr.array, L.n * 16);
    L.n++;
  }

  update(camera) {
    if (!this.ready) return;
    this.frame++;
    const q = this.q, cx = camera.position.x, cz = camera.position.z;
    this._pm.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this._frustum.setFromProjectionMatrix(this._pm);
    for (const k in this.assets) for (const L of this.assets[k].lods) L.n = 0;
    const R = q.lod1, c0 = Math.floor((cx - R) / CELL), c1 = Math.floor((cx + R) / CELL), d0 = Math.floor((cz - R) / CELL), d1 = Math.floor((cz + R) / CELL);
    const sph = this._sphere;
    let budget = 3;
    for (let ci = c0; ci <= c1; ci++) for (let cj = d0; cj <= d1; cj++) {
      const kx = Math.max(ci * CELL - cx, 0, cx - (ci + 1) * CELL), kz = Math.max(cj * CELL - cz, 0, cz - (cj + 1) * CELL);
      const cd2 = kx * kx + kz * kz;
      if (cd2 > R * R) continue;
      if (!this.cells.has(ci * 4096 + cj)) { if (budget-- <= 0 && cd2 > 70 * 70) continue; }
      const cell = this._cell(ci, cj);
      for (const e of cell.trees) {
        const dx = e[1] - cx, dz = e[3] - cz, d2 = dx * dx + dz * dz;
        if (d2 > R * R) continue;
        const A = this.assets[e[0]];
        if (d2 > 45 * 45) { sph.center.set(e[1], e[2] + A.cy * e[5], e[3]); sph.radius = A.radius * e[5]; if (!this._frustum.intersectsSphere(sph)) continue; }
        this._push(A, d2 < q.lod0 * q.lod0 ? 0 : 1, e);
      }
      for (const e of cell.props) {
        const dx = e[1] - cx, dz = e[3] - cz, d2 = dx * dx + dz * dz;
        const A = this.assets[e[0]];
        const far = A.radius * e[5] > 3 ? R : R * 0.7;
        if (d2 > far * far) continue;
        if (d2 > 30 * 30) { sph.center.set(e[1], e[2] + A.cy * e[5], e[3]); sph.radius = A.radius * e[5]; if (!this._frustum.intersectsSphere(sph)) continue; }
        this._push(A, d2 < 38 * 38 ? 0 : 1, e);
      }
      if (cd2 < 62 * 62) for (const e of cell.small) {
        const dx = e[1] - cx, dz = e[3] - cz, d2 = dx * dx + dz * dz;
        if (d2 > 58 * 58) continue;
        const A = this.assets[e[0]];
        sph.center.set(e[1], e[2] + 0.4, e[3]); sph.radius = 1.4 * e[5];
        if (!this._frustum.intersectsSphere(sph)) continue;
        // shrink toward the edge of the range instead of popping
        const f = d2 > 46 * 46 ? 1 - (Math.sqrt(d2) - 46) / 12 : 1;
        const s = e[5]; e[5] = s * f; this._push(A, 0, e); e[5] = s;
      }
    }
    let n0 = 0, n1 = 0;
    for (const k in this.assets) {
      const A = this.assets[k];
      A.lods.forEach((L, li) => {
        for (const im of L.inst) { im.count = L.n; im.visible = L.n > 0; }
        if (L.n) { L.attr.clearUpdateRanges(); L.attr.addUpdateRange(0, L.n * 16); L.attr.needsUpdate = true; }
        if (A.tree) { if (li === 0) n0 += L.n; else n1 += L.n; }
      });
    }
    this.stats.lod0 = n0; this.stats.lod1 = n1; this.stats.cells = this.cells.size;
    // impostors: rebuilt only when the camera moved far enough
    if (this.impMesh) {
      const u = this.impUniforms;
      u.uImpRange.value.set(q.lod1 - 14, q.lod1 - 2, q.imp * 0.9, q.imp);
      const a = this.atmo;
      u.uSunCol.value.copy(a.sun.color).multiplyScalar(a.sun.intensity);
      u.uSkyCol.value.copy(a.hemi.color).multiplyScalar(a.hemi.intensity);
      u.uGndCol.value.copy(a.hemi.groundColor).multiplyScalar(a.hemi.intensity);
      if (Math.hypot(cx - this._impCenter.x, cz - this._impCenter.y) > 24) this._rebuildImpostors(cx, cz);
    }
    if (this.cells.size > 1400) this._evict(cx, cz);
  }

  _rebuildImpostors(cx, cz) {
    const q = this.q, R = q.imp + 24, near = q.lod1 - 40;
    const c0 = Math.floor((cx - R) / CELL), c1 = Math.floor((cx + R) / CELL), d0 = Math.floor((cz - R) / CELL), d1 = Math.floor((cz + R) / CELL);
    const P = this.impPos.array, S = this.impSize.array, V = this.impUV.array;
    let n = 0, pending = 0;
    for (let ci = c0; ci <= c1 && n < this.impCap; ci++) for (let cj = d0; cj <= d1; cj++) {
      const kx = Math.max(ci * CELL - cx, 0, cx - (ci + 1) * CELL), kz = Math.max(cj * CELL - cz, 0, cz - (cj + 1) * CELL);
      if (kx * kx + kz * kz > R * R) continue;
      if (!this.cells.has(ci * 4096 + cj) && ++pending > 60) continue;    // spread generation over a few rebuilds
      const cell = this._cell(ci, cj);
      for (const e of cell.trees) {
        const dx = e[1] - cx, dz = e[3] - cz, d2 = dx * dx + dz * dz;
        if (d2 < near * near || d2 > R * R || n >= this.impCap) continue;
        const A = this.assets[e[0]];
        if (!A.impostor) continue;
        const im = A.impostor;
        P[n * 3] = e[1]; P[n * 3 + 1] = e[2]; P[n * 3 + 2] = e[3];
        S[n * 4] = im.width * e[5]; S[n * 4 + 1] = im.height * e[5]; S[n * 4 + 2] = e[6]; S[n * 4 + 3] = (e[4] * 0.159) % 1;
        V[n * 4] = im.uv[0]; V[n * 4 + 1] = im.uv[1]; V[n * 4 + 2] = im.uv[2]; V[n * 4 + 3] = im.uv[3];
        n++;
      }
    }
    this.impMesh.geometry.instanceCount = n;
    for (const a of [this.impPos, this.impSize, this.impUV]) { a.clearUpdateRanges(); a.addUpdateRange(0, n * a.itemSize); a.needsUpdate = true; }
    this.stats.imp = n;
    // if some cells were skipped, come back soon
    if (pending > 60) this._impCenter.set(cx + 20, cz); else this._impCenter.set(cx, cz);
  }

  _evict(cx, cz) {
    const lim = (this.q.imp + 200) ** 2;
    for (const [k, c] of this.cells) {
      const ci = Math.floor(k / 4096 + 0.5), cj = k - ci * 4096;
      const dx = (ci + 0.5) * CELL - cx, dz = (cj + 0.5) * CELL - cz;
      if (dx * dx + dz * dz > lim) this.cells.delete(k);
    }
  }

  // ------------------------------------------------------------------ collisions
  /** push a circle out of tree trunks and big rocks. Mutates pos.x/z. */
  resolve(pos, r) {
    const c0 = Math.floor((pos.x - r - 6) / CELL), c1 = Math.floor((pos.x + r + 6) / CELL), d0 = Math.floor((pos.z - r - 6) / CELL), d1 = Math.floor((pos.z + r + 6) / CELL);
    let hit = false;
    for (let ci = c0; ci <= c1; ci++) for (let cj = d0; cj <= d1; cj++) {
      const cell = this.cells.get(ci * 4096 + cj);
      if (!cell) continue;
      for (let pass = 0; pass < 2; pass++) {
        const list = pass ? cell.props : cell.trees;
        for (const e of list) {
          const col = this.assets[e[0]].collider;
          if (!col) continue;
          const dx = pos.x - e[1], dz = pos.z - e[3];
          if (col.type === 'cylinder' || col.type === 'sphere') {
            const rr = col.radius * e[5] + r, d2 = dx * dx + dz * dz;
            if (d2 < rr * rr) { const d = Math.sqrt(d2) || 1e-4, p = (rr - d) / d; pos.x += dx * p; pos.z += dz * p; hit = true; }
          } else {
            if (pos.y > e[2] + (col.center[1] + col.size[1] * 0.5) * e[5] - 0.3) continue;    // standing on top
            const c = Math.cos(-e[4]), s = Math.sin(-e[4]);
            const lx = dx * c + dz * s, lz = -dx * s + dz * c;      // into the prop's frame (rotation about Y)
            const hx = col.size[0] * 0.5 * e[5], hz = col.size[2] * 0.5 * e[5];
            const qx = Math.max(-hx, Math.min(hx, lx)), qz = Math.max(-hz, Math.min(hz, lz));
            let ox = lx - qx, oz = lz - qz;
            const d2 = ox * ox + oz * oz;
            if (d2 >= r * r) continue;
            if (d2 > 1e-8) { const d = Math.sqrt(d2), p = (r - d) / d; ox *= p; oz *= p; }
            else { const px = hx - Math.abs(lx) + r, pz = hz - Math.abs(lz) + r; if (px < pz) { ox = lx < 0 ? -px : px; oz = 0; } else { oz = lz < 0 ? -pz : pz; ox = 0; } }
            pos.x += ox * c - oz * s; pos.z += ox * s + oz * c; hit = true;
          }
        }
      }
    }
    return hit;
  }
}
