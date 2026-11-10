// CDLOD terrain: one instanced grid drawn for every selected quadtree node, heights fetched from an
// integer texture in the vertex shader, 8 splatted PBR layers with height blending in the fragment shader.
import * as THREE from 'three';
import { U, patchMaterial, inject, WORLD_HALF, WORLD_SIZE } from '../core/globals.js';

export const TERRAIN_LAYERS = ['grass', 'dirt', 'rock', 'sand', 'snow', 'forest', 'mud', 'ash'];
const FALLBACK = {
  grass: [86, 108, 52], dirt: [120, 96, 70], rock: [118, 114, 108], sand: [196, 178, 132],
  snow: [232, 236, 240], forest: [70, 62, 44], mud: [66, 58, 44], ash: [58, 54, 54],
};
// average linear albedo each layer is calibrated to (art direction lives here)
const LAYER_TARGET = { grass: [0.135, 0.178, 0.052], forest: [0.105, 0.085, 0.052], dirt: [0.26, 0.2, 0.135], mud: [0.085, 0.07, 0.048] };
const LEAF = 40, LEVELS = 8;   // 40 m leaves (16x16 quads of 2.5 m), root = 5120 m

function loadImg(url) {
  return new Promise((res) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => res(null);
    im.src = url;
  });
}

/** Build the two terrain texture arrays (albedo+height, normal+rough+ao). */
export async function loadTerrainLayers(size = 1024, anisotropy = 4) {
  const n = TERRAIN_LAYERS.length;
  const dataA = new Uint8Array(size * size * 4 * n), dataN = new Uint8Array(size * size * 4 * n);
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  await Promise.all(TERRAIN_LAYERS.map(async (name, i) => {
    const [a, nn] = await Promise.all([loadImg(`assets/textures/terrain_${name}_a.png`), loadImg(`assets/textures/terrain_${name}_n.png`)]);
    return { i, name, a, nn };
  })).then((list) => {
    for (const { i, name, a, nn } of list) {
      const off = i * size * size * 4;
      if (a) {
        ctx.clearRect(0, 0, size, size); ctx.globalCompositeOperation = 'copy'; ctx.drawImage(a, 0, 0, size, size);
        const px = flattenTile(ctx.getImageData(0, 0, size, size).data, size);
        const tgt = LAYER_TARGET[name];
        if (tgt) {
          // calibrate the layer so that its average LINEAR colour equals the target (keeps grass blades and ground in tune)
          const toLin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
          const toS = (v) => 255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
          const mean = [0, 0, 0];
          for (let p = 0; p < px.length; p += 16) { mean[0] += toLin(px[p]); mean[1] += toLin(px[p + 1]); mean[2] += toLin(px[p + 2]); }
          const cnt = px.length / 16;
          for (let c = 0; c < 3; c++) {
            const f = tgt[c] / (mean[c] / cnt), lut = new Uint8Array(256);
            for (let v = 0; v < 256; v++) lut[v] = Math.max(0, Math.min(255, toS(toLin(v) * f)));
            for (let p = c; p < px.length; p += 4) px[p] = lut[px[p]];
          }
        }
        dataA.set(px, off);
      } else {
        const c = FALLBACK[name];
        for (let p = 0; p < size * size; p++) {
          const v = 0.85 + 0.3 * Math.random();
          dataA[off + p * 4] = c[0] * v; dataA[off + p * 4 + 1] = c[1] * v; dataA[off + p * 4 + 2] = c[2] * v; dataA[off + p * 4 + 3] = 128 * v;
        }
      }
      if (nn) {
        ctx.clearRect(0, 0, size, size); ctx.globalCompositeOperation = 'copy'; ctx.drawImage(nn, 0, 0, size, size);
        dataN.set(ctx.getImageData(0, 0, size, size).data, off);
      } else {
        for (let p = 0; p < size * size; p++) { dataN[off + p * 4] = 128; dataN[off + p * 4 + 1] = 128; dataN[off + p * 4 + 2] = 220; dataN[off + p * 4 + 3] = 255; }
      }
    }
  });
  const mk = (data, srgb) => {
    const t = new THREE.DataArrayTexture(data, size, size, n);
    t.format = THREE.RGBAFormat; t.type = THREE.UnsignedByteType;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
    t.generateMipmaps = true; t.anisotropy = anisotropy;
    t.needsUpdate = true;
    return t;
  };
  return { layA: mk(dataA, true), layN: mk(dataN, false) };
}

/** Remove the large-scale brightness/colour variation of a tiling image (keeps detail): without it a
 * repeated tile reads as a regular grid of blotches from a distance. Macro variation is re-added in the
 * shader with non-repeating noise. Operates in place on RGBA bytes, wraps around the tile borders. */
function flattenTile(px, size, B = 16, amount = 0.9) {
  const bs = size / B, n = B * B;
  const acc = new Float32Array(n * 4);
  for (let y = 0; y < size; y++) {
    const by = (y / bs) | 0;
    for (let x = 0; x < size; x++) {
      const k = (by * B + ((x / bs) | 0)) * 4, i = (y * size + x) * 4;
      acc[k] += px[i]; acc[k + 1] += px[i + 1]; acc[k + 2] += px[i + 2]; acc[k + 3] += px[i + 3];
    }
  }
  const inv = 1 / (bs * bs), mean = [0, 0, 0, 0];
  for (let k = 0; k < n * 4; k++) { acc[k] *= inv; mean[k & 3] += acc[k] / n; }
  for (let y = 0; y < size; y++) {
    const fy = (y + 0.5) / bs - 0.5, y0 = Math.floor(fy), ty = fy - y0;
    const ya = ((y0 % B) + B) % B, yb = (ya + 1) % B;
    for (let x = 0; x < size; x++) {
      const fx = (x + 0.5) / bs - 0.5, x0 = Math.floor(fx), tx = fx - x0;
      const xa = ((x0 % B) + B) % B, xb = (xa + 1) % B;
      const i = (y * size + x) * 4, a = (ya * B + xa) * 4, b = (ya * B + xb) * 4, c = (yb * B + xa) * 4, d = (yb * B + xb) * 4;
      for (let ch = 0; ch < 4; ch++) {
        const lo = (acc[a + ch] * (1 - tx) + acc[b + ch] * tx) * (1 - ty) + (acc[c + ch] * (1 - tx) + acc[d + ch] * tx) * ty;
        const m = mean[ch], ref = m + (lo - m) * amount;
        const v = px[i + ch] * (m / Math.max(ref, 1));
        px[i + ch] = v > 255 ? 255 : v;
      }
    }
  }
  return px;
}

function gridGeometry(G, maxInstances) {
  const nv = (G + 1) * (G + 1);
  const pos = new Float32Array(nv * 3), morph = new Float32Array(nv * 2);
  let k = 0;
  for (let j = 0; j <= G; j++) for (let i = 0; i <= G; i++, k++) {
    pos[k * 3] = i / G; pos[k * 3 + 1] = 0; pos[k * 3 + 2] = j / G;
    morph[k * 2] = (i & 1) ? -1 / G : 0;
    morph[k * 2 + 1] = (j & 1) ? -1 / G : 0;
  }
  const idx = new Uint16Array(G * G * 6);
  k = 0;
  for (let j = 0; j < G; j++) for (let i = 0; i < G; i++) {
    const a = j * (G + 1) + i, b = a + 1, c = a + G + 1, d = c + 1;
    // alternate diagonals so that morphed (collapsed) quads stay consistent
    if ((i + j) & 1) { idx[k++] = a; idx[k++] = c; idx[k++] = b; idx[k++] = b; idx[k++] = c; idx[k++] = d; }
    else { idx[k++] = a; idx[k++] = c; idx[k++] = d; idx[k++] = a; idx[k++] = d; idx[k++] = b; }
  }
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aMorph', new THREE.BufferAttribute(morph, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  const node = new THREE.InstancedBufferAttribute(new Float32Array(maxInstances * 4), 4);
  node.setUsage(THREE.DynamicDrawUsage);
  g.setAttribute('aNode', node);
  g.instanceCount = 0;
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);
  return g;
}

export const HEIGHT_GLSL = /* glsl */`
uniform highp usampler2D uHeightTex;
uniform vec4 uHInfo;   // hmin, hscale, cell, n
float valHeight( vec2 p ) {
  vec2 f = clamp( ( p + ${WORLD_HALF.toFixed(1)} ) / uHInfo.z, vec2( 0.0 ), vec2( uHInfo.w - 1.001 ) );
  ivec2 i = ivec2( floor( f ) );
  vec2 t = f - vec2( i );
  float h00 = float( texelFetch( uHeightTex, i, 0 ).r );
  float h10 = float( texelFetch( uHeightTex, i + ivec2( 1, 0 ), 0 ).r );
  float h01 = float( texelFetch( uHeightTex, i + ivec2( 0, 1 ), 0 ).r );
  float h11 = float( texelFetch( uHeightTex, i + ivec2( 1, 1 ), 0 ).r );
  return mix( mix( h00, h10, t.x ), mix( h01, h11, t.x ), t.y ) * uHInfo.y + uHInfo.x;
}`;

export class Terrain {
  constructor(world, layers, opts = {}) {
    this.world = world;
    this.range0 = opts.range0 || 140;   // must stay >= 95 (see morph zone)
    this.uniforms = {
      uHeightTex: { value: world.heightTex },
      uHInfo: { value: world.heightInfo },
      uRange0: { value: this.range0 },
      uSplat0: { value: world.splat0Tex },
      uSplat1: { value: world.splat1Tex },
      uTerrNrm: { value: world.nrmTex },
      uTint: { value: world.tintTex },
      uLayA: { value: layers.layA },
      uLayN: { value: layers.layN },
      uTerrOpt: { value: new THREE.Vector4(0.25, 0.0437, 1.0, 0.0) },  // near scale, far scale, quality, -
      uNoiseTex2: U.uNoiseTex,
    };
    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, metalness: 0 });
    mat.defines = { VAL_WORLD_SPACE: 1 };
    patchMaterial(mat, (sh) => {
      Object.assign(sh.uniforms, this.uniforms);
      sh.vertexShader = sh.vertexShader.replace('#include <common>', /* glsl */`
        #include <common>
        attribute vec4 aNode;
        attribute vec2 aMorph;
        uniform float uRange0;
        ${HEIGHT_GLSL}
      `);
      sh.vertexShader = inject(sh.vertexShader, 'beginnormal_vertex', 'vec3 objectNormal = vec3( 0.0, 1.0, 0.0 );');
      sh.vertexShader = inject(sh.vertexShader, 'begin_vertex', /* glsl */`
        vec2 wxz = aNode.xy + position.xz * aNode.z;
        float rng = uRange0 * exp2( aNode.w );
        float dcam = distance( wxz, cameraPosition.xz );
        float mk = clamp( ( dcam - rng * 0.80 ) / ( rng * 0.17 ), 0.0, 1.0 );
        wxz += aMorph * aNode.z * mk;
        vec3 transformed = vec3( wxz.x, valHeight( wxz ), wxz.y );
      `);
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', /* glsl */`
        #include <common>
        uniform sampler2D uSplat0;
        uniform sampler2D uSplat1;
        uniform sampler2D uTerrNrm;
        uniform sampler2D uTint;
        uniform mediump sampler2DArray uLayA;
        uniform mediump sampler2DArray uLayN;
        uniform vec4 uTerrOpt;
        uniform float uWet;
        uniform sampler2D uNoiseTex2;
      `);
      sh.fragmentShader = inject(sh.fragmentShader, 'map_fragment', /* glsl */`
        vec3 tw = vFogWorld;
        vec2 wuv = tw.xz * ${(1 / WORLD_SIZE).toFixed(10)} + 0.5;
        vec4 s0 = texture2D( uSplat0, wuv );
        vec4 s1 = texture2D( uSplat1, wuv );
        vec4 tn = texture2D( uTerrNrm, wuv );
        vec3 nW = vec3( tn.r * 2.0 - 1.0, 0.0, tn.g * 2.0 - 1.0 );
        nW.y = sqrt( max( 1.0 - nW.x * nW.x - nW.z * nW.z, 0.02 ) );
        float cdist = length( tw - cameraPosition );
        float nearK = 1.0 - smoothstep( 60.0, 150.0, cdist );
        bool useN = cdist < 380.0;
        vec2 uvN = tw.xz * uTerrOpt.x;
        vec2 uvF = mat2( 0.8, -0.6, 0.6, 0.8 ) * tw.xz * uTerrOpt.y;
        vec2 dxN = dFdx( uvN ), dyN = dFdy( uvN ), dxF = dFdx( uvF ), dyF = dFdy( uvF );
        // triplanar (rock on steep slopes)
        float steep = ( 1.0 - smoothstep( 0.58, 0.82, nW.y ) ) * uTerrOpt.z;
        vec2 uvX = vec2( tw.z, -tw.y ) * uTerrOpt.x, uvZ = vec2( tw.x, -tw.y ) * uTerrOpt.x;
        vec2 dxX = dFdx( uvX ), dyX = dFdy( uvX ), dxZ = dFdx( uvZ ), dyZ = dFdy( uvZ );
        float wgt[8];
        wgt[0] = s0.r; wgt[1] = s0.g; wgt[2] = s0.b; wgt[3] = s0.a; wgt[4] = s1.r; wgt[5] = s1.g; wgt[6] = s1.b; wgt[7] = s1.a;
        vec4 la[8];
        vec4 lr[8];     // xyz = world-space normal perturbation, w = roughness
        float lao[8];
        float hb[8];
        float hmax = 0.0;
        for ( int i = 0; i < 8; i ++ ) {
          hb[i] = 0.0; la[i] = vec4( 0.0 ); lr[i] = vec4( 0.0, 0.0, 0.0, 0.9 ); lao[i] = 1.0;
          if ( wgt[i] > 0.012 ) {
            float fi = float( i );
            vec4 a; vec4 n = vec4( 0.5, 0.5, 0.9, 1.0 );
            if ( nearK < 0.999 ) {
              a = textureGrad( uLayA, vec3( uvF, fi ), dxF, dyF );
              if ( useN ) n = textureGrad( uLayN, vec3( uvF, fi ), dxF, dyF );
            }
            if ( nearK > 0.001 ) {
              vec4 a2 = textureGrad( uLayA, vec3( uvN, fi ), dxN, dyN );
              vec4 n2 = textureGrad( uLayN, vec3( uvN, fi ), dxN, dyN );
              if ( nearK < 0.999 ) { a = mix( a, a2, nearK ); n = mix( n, n2, nearK ); } else { a = a2; n = n2; }
            }
            vec3 pert = vec3( n.x * 2.0 - 1.0, 0.0, -( n.y * 2.0 - 1.0 ) );
            if ( i == 2 && steep > 0.01 && nearK > 0.001 ) {
              vec2 tb = abs( nW.xz ) + 0.001;
              tb /= ( tb.x + tb.y );
              vec4 ax = textureGrad( uLayA, vec3( uvX, fi ), dxX, dyX );
              vec4 az = textureGrad( uLayA, vec3( uvZ, fi ), dxZ, dyZ );
              vec4 nx = textureGrad( uLayN, vec3( uvX, fi ), dxX, dyX );
              vec4 nz = textureGrad( uLayN, vec3( uvZ, fi ), dxZ, dyZ );
              float k = steep * nearK;
              a = mix( a, ax * tb.x + az * tb.y, k );
              vec3 px = vec3( 0.0, nx.y * 2.0 - 1.0, nx.x * 2.0 - 1.0 );
              vec3 pz = vec3( nz.x * 2.0 - 1.0, nz.y * 2.0 - 1.0, 0.0 );
              pert = mix( pert, px * tb.x + pz * tb.y, k );
              n.zw = mix( n.zw, nx.zw * tb.x + nz.zw * tb.y, k );
            }
            la[i] = a; lr[i] = vec4( pert, n.z ); lao[i] = n.w;
            hb[i] = wgt[i] + a.a * 0.55;
            hmax = max( hmax, hb[i] );
          }
        }
        float thr = hmax - 0.16;
        vec4 accA = vec4( 0.0 ); vec4 accR = vec4( 0.0 ); float accO = 0.0; float tot = 0.0;
        for ( int i = 0; i < 8; i ++ ) {
          float b = max( hb[i] - thr, 0.0 );
          accA += la[i] * b; accR += lr[i] * b; accO += lao[i] * b; tot += b;
        }
        tot = max( tot, 1e-4 );
        accA /= tot; accR /= tot; accO /= tot;
        float macro = texture2D( uNoiseTex2, tw.xz * 0.0137 ).r * 0.55 + texture2D( uNoiseTex2, tw.xz * 0.0023 + 0.37 ).b * 0.45;
        vec3 valAlbedo = accA.rgb * ( texture2D( uTint, wuv ).rgb * 2.0 ) * ( 0.74 + 0.52 * macro );
        float valRough = accR.w;
        // wet shore + rain
        float wet = max( ( 1.0 - smoothstep( 0.1, 1.4, tw.y ) ) * 0.85, uWet * 0.6 * ( 1.0 - s1.r ) );
        valAlbedo *= 1.0 - 0.38 * wet;
        valRough = mix( valRough, 0.18, wet * 0.8 );
        float nStr = mix( 0.35, 1.0, nearK );
        vec3 valNormalW = normalize( nW + accR.xyz * nStr );
        float valAO = accO * tn.b;
        diffuseColor.rgb *= valAlbedo;
      `);
      sh.fragmentShader = inject(sh.fragmentShader, 'roughnessmap_fragment', 'float roughnessFactor = valRough;');
      sh.fragmentShader = inject(sh.fragmentShader, 'normal_fragment_begin', /* glsl */`
        float faceDirection = 1.0;
        vec3 normal = normalize( ( viewMatrix * vec4( valNormalW, 0.0 ) ).xyz );
        vec3 nonPerturbedNormal = normal;
      `);
      sh.fragmentShader = inject(sh.fragmentShader, 'aomap_fragment', 'reflectedLight.indirectDiffuse *= valAO;');
    }, 'terrain');
    this.material = mat;

    this.maxNodes = 1024;
    this.geoFull = gridGeometry(16, this.maxNodes);
    this.geoQuad = gridGeometry(8, this.maxNodes);
    this.meshFull = new THREE.Mesh(this.geoFull, mat);
    this.meshQuad = new THREE.Mesh(this.geoQuad, mat);
    for (const m of [this.meshFull, this.meshQuad]) {
      m.frustumCulled = false; m.receiveShadow = true; m.castShadow = false; m.matrixAutoUpdate = false; m.renderOrder = 10;
    }
    this.group = new THREE.Group();
    this.group.add(this.meshFull, this.meshQuad);
    this._frustum = new THREE.Frustum();
    this._pm = new THREE.Matrix4();
    this._box = new THREE.Box3();
    this._full = []; this._quad = [];
    this.stats = { nodes: 0, tris: 0 };
  }

  setRange(r0) { this.range0 = r0; this.uniforms.uRange0.value = r0; }

  _minmax(x, z, size) {
    const lvl = Math.round(Math.log2(size / LEAF));
    const mm = this.world.mm[lvl];
    const i = Math.round((x + WORLD_HALF) / size), j = Math.round((z + WORLD_HALF) / size);
    const k = j * mm.n + i;
    return [mm.min[k], mm.max[k]];
  }

  _circle(x, z, size, cx, cz, r) {
    const dx = Math.max(x - cx, 0, cx - (x + size)), dz = Math.max(z - cz, 0, cz - (z + size));
    return dx * dx + dz * dz < r * r;
  }

  _select(x, z, size, level, cx, cz) {
    const r = this.range0 * (1 << level);
    if (level < LEVELS - 1 && !this._circle(x, z, size, cx, cz, r)) return false;
    const [lo, hi] = this._minmax(x, z, size);
    this._box.min.set(x, lo - 1, z); this._box.max.set(x + size, hi + 1, z + size);
    if (!this._frustum.intersectsBox(this._box)) return true;
    if (level === 0 || !this._circle(x, z, size, cx, cz, r * 0.5)) {
      this._full.push(x, z, size, level);
      return true;
    }
    const h = size * 0.5;
    for (let q = 0; q < 4; q++) {
      const qx = x + (q & 1) * h, qz = z + (q >> 1) * h;
      if (!this._select(qx, qz, h, level - 1, cx, cz)) {
        const [l2, h2] = this._minmax(qx, qz, h);
        this._box.min.set(qx, l2 - 1, qz); this._box.max.set(qx + h, h2 + 1, qz + h);
        if (this._frustum.intersectsBox(this._box)) this._quad.push(qx, qz, h, level);
      }
    }
    return true;
  }

  update(camera) {
    this._pm.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this._frustum.setFromProjectionMatrix(this._pm);
    this._full.length = 0; this._quad.length = 0;
    const cx = camera.position.x, cz = camera.position.z;
    this._select(-WORLD_HALF, -WORLD_HALF, WORLD_SIZE, LEVELS - 1, cx, cz);
    this._fill(this.geoFull, this._full, cx, cz);
    this._fill(this.geoQuad, this._quad, cx, cz);
    this.stats.nodes = this.geoFull.instanceCount + this.geoQuad.instanceCount;
    this.stats.tris = this.geoFull.instanceCount * 512 + this.geoQuad.instanceCount * 128;
  }

  _fill(geo, list, cx, cz) {
    const attr = geo.attributes.aNode, arr = attr.array;
    let n = Math.min(list.length / 4, this.maxNodes);
    // front-to-back order helps early-z on the (expensive) terrain shader
    const order = [];
    for (let i = 0; i < n; i++) {
      const x = list[i * 4] + list[i * 4 + 2] * 0.5 - cx, z = list[i * 4 + 1] + list[i * 4 + 2] * 0.5 - cz;
      order.push([x * x + z * z, i]);
    }
    order.sort((a, b) => a[0] - b[0]);
    for (let k = 0; k < n; k++) {
      const i = order[k][1];
      arr[k * 4] = list[i * 4]; arr[k * 4 + 1] = list[i * 4 + 1]; arr[k * 4 + 2] = list[i * 4 + 2]; arr[k * 4 + 3] = list[i * 4 + 3];
    }
    geo.instanceCount = n;
    attr.clearUpdateRanges();
    attr.addUpdateRange(0, n * 4);
    attr.needsUpdate = true;
  }
}
