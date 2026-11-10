// Human characters: body from human.glb with morph targets (live in the creator, baked in game),
// skin / eye / hair shaders, hair + beard + outfit pieces bound to the same skeleton, region hiding.
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { patchMaterial, inject } from '../core/globals.js';
import { getMaterial, applyLibrary } from '../render/materials.js';
import { loadTexture } from '../core/assets.js';
import { ITEMS } from './data/items.js';

const PAINT_ID = { none: 0, stripe: 1, claws: 2, tears: 3, half: 4, runes: 5, dots: 6, skull: 7 };
const SCAR_ID = { none: 0, brow: 1, cheek: 2, lip: 3, cross: 4, burn: 5 };
const bakeCache = new Map();
let skinPack = null;
function skinNormal() {
  if (!skinPack) { skinPack = { tex: null }; loadTexture('assets/textures/skin_n.png', { aniso: 2 }).then((t) => { skinPack.tex = t; for (const m of skinPack.users || []) { m.normalMap = t; m.needsUpdate = true; } }); skinPack.users = []; }
  return skinPack;
}

function skinMaterial(look, head) {
  const m = new THREE.MeshStandardMaterial({ color: new THREE.Color(look.skin || '#c9a184'), roughness: 0.62, metalness: 0 });
  m.name = 'M_skin';
  const sp = skinNormal();
  if (sp.tex) m.normalMap = sp.tex; else sp.users.push(m);
  m.normalScale.set(0.35, -0.35);
  const u = m.userData.u = {
    uPaint: { value: new THREE.Vector4(PAINT_ID[look.paint] || 0, SCAR_ID[look.scar] || 0, look.undead ? 1 : 0, 0) },
    uPaintCol: { value: new THREE.Color(look.paintColor || '#1a1a1a') },
    uGlow: { value: new THREE.Color(look.ghost || '#000000') },
  };
  if (head) m.defines = { VAL_HEAD: 1 };
  if (look.ghost) { m.transparent = true; m.opacity = 0.55; m.depthWrite = false; m.emissive.set(look.ghost); m.emissiveIntensity = 0.6; }
  patchMaterial(m, (sh) => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', `#include <common>
      attribute vec3 color;
      varying vec3 vMask;
      #ifdef VAL_HEAD
        attribute vec2 uv1;
        varying vec3 vFace;
      #endif`);
    sh.vertexShader = inject(sh.vertexShader, 'begin_vertex', `#include <begin_vertex>
      vMask = color;
      #ifdef VAL_HEAD
        vFace = vec3( uv1, normal.z );
      #endif`);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>
      varying vec3 vMask;
      uniform vec4 uPaint;
      uniform vec3 uPaintCol;
      #ifdef VAL_HEAD
        varying vec3 vFace;
        float pHash( vec2 p ) { return fract( sin( dot( p, vec2( 41.3, 289.1 ) ) ) * 43758.5453 ); }
        float paintMask( vec2 uv, float id ) {
          vec2 c = uv - vec2( 0.5, 0.0 );
          float ax = abs( c.x );
          if ( id < 1.5 ) return smoothstep( 0.075, 0.055, abs( uv.y - 0.615 ) ) * smoothstep( 0.44, 0.4, ax );
          if ( id < 2.5 ) { float d = fract( ( uv.x * 0.9 + uv.y * 0.55 ) * 9.0 ); return step( 0.5, uv.x ) * smoothstep( 0.3, 0.2, abs( d - 0.5 ) ) * smoothstep( 0.2, 0.26, uv.y ) * smoothstep( 0.62, 0.56, uv.y ) * smoothstep( 0.6, 0.64, uv.x ) * smoothstep( 0.92, 0.86, uv.x ); }
          if ( id < 3.5 ) return smoothstep( 0.022, 0.012, abs( ax - 0.17 ) ) * smoothstep( 0.56, 0.52, uv.y ) * smoothstep( 0.2, 0.3, uv.y );
          if ( id < 4.5 ) return smoothstep( 0.5, 0.52, uv.x );
          if ( id < 5.5 ) { vec2 g = floor( uv * vec2( 22.0, 26.0 ) ); float h = pHash( g ); vec2 f = fract( uv * vec2( 22.0, 26.0 ) ) - 0.5; float bar = h > 0.5 ? abs( f.x ) : abs( f.y ); return step( 0.62, pHash( g + 7.0 ) ) * smoothstep( 0.22, 0.12, bar ) * smoothstep( 0.52, 0.6, uv.y ) * smoothstep( 0.42, 0.36, ax ); }
          if ( id < 6.5 ) { vec2 f = fract( vec2( uv.x * 9.0, 0.0 ) ) - vec2( 0.5, 0.0 ); return smoothstep( 0.3, 0.2, length( vec2( f.x, ( uv.y - 0.74 ) * 9.0 ) ) ) * smoothstep( 0.36, 0.3, ax ); }
          float eye = smoothstep( 0.15, 0.1, length( ( vec2( ax, uv.y ) - vec2( 0.17, 0.615 ) ) * vec2( 1.0, 1.25 ) ) );
          float nose = smoothstep( 0.06, 0.03, length( ( c - vec2( 0.0, 0.42 ) ) * vec2( 1.3, 0.8 ) ) );
          float teeth = smoothstep( 0.02, 0.01, abs( fract( uv.x * 14.0 ) - 0.5 ) - 0.3 ) * smoothstep( 0.05, 0.03, abs( uv.y - 0.26 ) ) * smoothstep( 0.2, 0.16, ax );
          return max( max( eye, nose ), teeth * 0.0 + smoothstep( 0.012, 0.004, abs( uv.y - 0.25 ) ) * smoothstep( 0.2, 0.16, ax ) );
        }
        float scarMask( vec2 uv, float id ) {
          if ( id < 0.5 ) return 0.0;
          vec2 a, b; float w = 0.011;
          if ( id < 1.5 ) { a = vec2( 0.62, 0.78 ); b = vec2( 0.70, 0.52 ); }
          else if ( id < 2.5 ) { a = vec2( 0.26, 0.5 ); b = vec2( 0.4, 0.3 ); }
          else if ( id < 3.5 ) { a = vec2( 0.56, 0.36 ); b = vec2( 0.6, 0.2 ); }
          else if ( id < 4.5 ) { a = vec2( 0.2, 0.62 ); b = vec2( 0.44, 0.34 ); }
          else { float n = pHash( floor( uv * 46.0 ) ); return smoothstep( 0.5, 0.8, uv.x ) * smoothstep( 0.2, 0.45, uv.y ) * smoothstep( 0.8, 0.6, uv.y ) * ( 0.5 + 0.5 * n ); }
          vec2 pa = uv - a, ba = b - a;
          float h = clamp( dot( pa, ba ) / dot( ba, ba ), 0.0, 1.0 );
          float d = length( pa - ba * h );
          float s = smoothstep( w, w * 0.4, d );
          if ( id > 3.5 && id < 4.5 ) { vec2 a2 = vec2( 0.44, 0.62 ), b2 = vec2( 0.2, 0.34 ); vec2 pa2 = uv - a2, ba2 = b2 - a2; float h2 = clamp( dot( pa2, ba2 ) / dot( ba2, ba2 ), 0.0, 1.0 ); s = max( s, smoothstep( w, w * 0.4, length( pa2 - ba2 * h2 ) ) ); }
          return s;
        }
      #endif`);
    sh.fragmentShader = inject(sh.fragmentShader, 'color_fragment', `#include <color_fragment>
      vec3 sk = diffuseColor.rgb;
      if ( uPaint.z > 0.5 ) sk = mix( sk, sk * vec3( 0.7, 0.85, 0.78 ), 0.5 );
      sk = mix( sk, sk * vec3( 1.22, 0.72, 0.66 ), vMask.r * 0.6 );
      sk = mix( sk, sk * vec3( 1.05, 0.5, 0.48 ), vMask.b * 0.75 );
      #ifdef VAL_HEAD
        float front = smoothstep( 0.05, 0.4, vFace.z );
        float pm = uPaint.x > 0.5 ? paintMask( vFace.xy, uPaint.x ) * front : 0.0;
        sk = mix( sk, uPaintCol, pm * 0.85 );
        float sm = scarMask( vFace.xy, uPaint.y ) * front;
        sk = mix( sk, sk * vec3( 1.3, 0.78, 0.74 ) + 0.03, sm * 0.8 );
      #endif
      sk *= mix( 0.42, 1.0, vMask.g );
      diffuseColor.rgb = sk;`);
    sh.fragmentShader = inject(sh.fragmentShader, 'roughnessmap_fragment', `
      #ifdef USE_NORMALMAP
        vec4 valPack = texture2D( normalMap, vNormalMapUv );
      #else
        vec4 valPack = vec4( 0.5, 0.5, 1.0, 1.0 );
      #endif
      float roughnessFactor = roughness * ( 0.75 + 0.25 * valPack.b ) * ( 1.0 - 0.45 * vMask.b );`);
    sh.fragmentShader = inject(sh.fragmentShader, 'normal_fragment_maps', `
      #ifdef USE_NORMALMAP_TANGENTSPACE
        vec3 mapN = vec3( valPack.xy * 2.0 - 1.0, 0.0 );
        mapN.xy *= normalScale;
        mapN.z = sqrt( max( 1.0 - dot( mapN.xy, mapN.xy ), 0.05 ) );
        normal = normalize( tbn * mapN );
      #endif`);
    // cheap subsurface: light wraps around the terminator with a warm tint
    sh.fragmentShader = inject(sh.fragmentShader, 'lights_fragment_end', `#include <lights_fragment_end>
      #if NUM_SUN_LIGHTS > 0
        float sWrap = clamp( ( dot( geometryNormal, sunLights[ 0 ].direction ) + 0.45 ) / 1.45, 0.0, 1.0 ) - clamp( dot( geometryNormal, sunLights[ 0 ].direction ), 0.0, 1.0 );
        reflectedLight.directDiffuse += sunLights[ 0 ].color * diffuseColor.rgb * vec3( 1.0, 0.32, 0.2 ) * max( sWrap, 0.0 ) * 0.22 * valSunVis( vFogWorld, uSunDir );
      #endif`);
  }, 'skin' + (head ? 'H' : ''));
  return m;
}

const eyeCache = new Map();
function eyeMaterial(color, glow) {
  const key = color + '|' + (glow || '');
  if (eyeCache.has(key)) return eyeCache.get(key);
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.12, metalness: 0 });
  m.name = 'M_eye';
  m.defines = { USE_UV: '' };
  const u = { uIris: { value: new THREE.Color(color || '#3f6f8f') }, uEyeGlow: { value: new THREE.Color(glow || '#000000') } };
  patchMaterial(m, (sh) => {
    Object.assign(sh.uniforms, u);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform vec3 uIris;\nuniform vec3 uEyeGlow;');
    sh.fragmentShader = inject(sh.fragmentShader, 'color_fragment', `#include <color_fragment>
      vec2 ec = vUv - 0.5;
      float er = length( ec );
      float ea = atan( ec.y, ec.x );
      vec3 sclera = vec3( 0.86, 0.84, 0.8 ) - vec3( 0.0, 0.1, 0.1 ) * smoothstep( 0.3, 0.5, er );
      float streak = 0.75 + 0.25 * sin( ea * 23.0 ) * sin( ea * 7.0 + 1.3 );
      vec3 iris = uIris * streak * mix( 1.25, 0.55, smoothstep( 0.06, 0.2, er ) );
      iris *= 1.0 - 0.6 * smoothstep( 0.165, 0.2, er );
      vec3 ecol = mix( iris, sclera, smoothstep( 0.19, 0.21, er ) );
      ecol = mix( vec3( 0.01 ), ecol, smoothstep( 0.07, 0.085, er ) );
      diffuseColor.rgb = ecol;`);
    sh.fragmentShader = inject(sh.fragmentShader, 'emissivemap_fragment', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += uEyeGlow * 4.0 * ( 1.0 - smoothstep( 0.1, 0.24, length( vUv - 0.5 ) ) );');
  }, 'eye');
  eyeCache.set(key, m);
  return m;
}

const hairCache = new Map();
function hairMaterial(color) {
  if (hairCache.has(color)) return hairCache.get(color);
  const m = getMaterial('M_hair', { vertexColors: false, variant: 'c' + color, tint: new THREE.Color(color), doubleSide: true });
  m.side = THREE.DoubleSide;
  m.roughness = 0.6;
  hairCache.set(color, m);
  return m;
}

/** geometry with the given morph influences applied once (no runtime morph cost) */
function bake(geometry, dict, morphs, cacheKey) {
  const mp = geometry.morphAttributes.position;
  if (!mp || !dict) return geometry;
  const key = geometry.uuid + '|' + cacheKey;
  if (bakeCache.has(key)) return bakeCache.get(key);
  const g = new THREE.BufferGeometry();
  for (const n in geometry.attributes) if (n !== 'position' && n !== 'normal') g.setAttribute(n, geometry.attributes[n]);
  g.setIndex(geometry.index);
  const pos = new Float32Array(geometry.attributes.position.array), nrm = new Float32Array(geometry.attributes.normal.array);
  const mn = geometry.morphAttributes.normal;
  for (const name in morphs) {
    const w = morphs[name], idx = dict[name];
    if (!w || idx === undefined) continue;
    const dp = mp[idx].array, dn = mn && mn[idx] ? mn[idx].array : null;
    for (let i = 0; i < pos.length; i++) pos[i] += dp[i] * w;
    if (dn) for (let i = 0; i < nrm.length; i++) nrm[i] += dn[i] * w;
  }
  for (let i = 0; i < nrm.length; i += 3) { const l = Math.hypot(nrm[i], nrm[i + 1], nrm[i + 2]) || 1; nrm[i] /= l; nrm[i + 1] /= l; nrm[i + 2] /= l; }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
  g.boundingSphere = geometry.boundingSphere; g.boundingBox = geometry.boundingBox;
  bakeCache.set(key, g);
  if (bakeCache.size > 400) bakeCache.delete(bakeCache.keys().next().value);
  return g;
}

/** mean of the (engine calibrated) vertex colours of a geometry, cached */
function avgVertexColor(geometry) {
  if (geometry.userData.avgVc) return geometry.userData.avgVc;
  const c = geometry.attributes.color, out = [1, 1, 1];
  if (c && c.count) {
    let r = 0, g = 0, b = 0;
    for (let i = 0; i < c.count; i++) { r += Math.pow(Math.max(c.getX(i), 1e-3), 0.78); g += Math.pow(Math.max(c.getY(i), 1e-3), 0.78); b += Math.pow(Math.max(c.getZ(i), 1e-3), 0.78); }
    out[0] = Math.max(r / c.count, 0.02); out[1] = Math.max(g / c.count, 0.02); out[2] = Math.max(b / c.count, 0.02);
  }
  return (geometry.userData.avgVc = out);
}

const morphKey = (m) => m ? Object.keys(m).sort().map(k => k + ':' + (Math.round(m[k] * 50) / 50)).join(',') : '';

/** Install the human builder on a ModelFactory. */
export function installHumanBuilder(factory) {
  // a piece is one mesh, or (several materials) a group of meshes carrying the piece name
  const srcByName = (gltf) => { const map = {}; if (gltf) gltf.scene.traverse((o) => { if (o.isSkinnedMesh || o.isMesh || (!o.isBone && o.children.some(c => c.isMesh))) map[o.name] = o; }); return map; };
  const hairSrc = srcByName(factory.hair), outfitSrc = srcByName(factory.outfits);
  const outfitInfo = (factory.outfitManifest && (factory.outfitManifest.pieces || factory.outfitManifest.assets)) || {};

  factory.buildHumanHook = (look) => {
    const inner = cloneSkinned(factory.human.scene);
    const live = !!look.live;                           // creator: keep morph targets live
    const bones = {};
    let parent = inner, bodyMeshes = {};
    inner.traverse((o) => { if (o.isBone) bones[o.name] = o; });
    const morphs = { ...(look.morphs || {}) };
    if (look.feminine) morphs.feminine = look.feminine;
    const mkey = morphKey(morphs);
    const state = { look: { ...look, morphs }, extras: {}, hidden: {} };
    const skinB = skinMaterial(look, false), skinH = skinMaterial(look, true);
    const apply = (o) => {
      const mn = (o.material.name || '').replace(/\.\d+$/, '');
      if (mn === 'M_skin') o.material = o.name === 'body_head' ? skinH : skinB;
      else if (mn === 'M_eye') o.material = eyeMaterial(look.eyeColor || '#3f6f8f', look.hollow || look.eyes);
      else if (mn === 'M_hair') o.material = hairMaterial(look.hairColor || '#47301f');
      else o.material = getMaterial(mn, { vertexColors: !!o.geometry.attributes.color });
      o.castShadow = !/^(eye_|brows|mouth)/.test(o.name); o.receiveShadow = true; o.frustumCulled = false;
      if (live) { if (o.morphTargetDictionary) for (const n in o.morphTargetDictionary) o.morphTargetInfluences[o.morphTargetDictionary[n]] = morphs[n] || 0; }
      else if (o.morphTargetDictionary) { o.geometry = bake(o.geometry, o.morphTargetDictionary, morphs, mkey); o.morphTargetInfluences = undefined; o.morphTargetDictionary = undefined; }
      bodyMeshes[o.name] = o;
      parent = o.parent;
    };
    const list = [];
    inner.traverse((o) => { if (o.isSkinnedMesh) list.push(o); });
    list.forEach(apply);

    /** add a skinned piece coming from another glb (hair, beard, outfit) */
    const addPiece = (slot, src, material) => {
      const old = state.extras[slot];
      if (old) { for (const m of old) { m.parent && m.parent.remove(m); } state.extras[slot] = null; }
      if (!src) return;
      const sources = [];
      if (src.isSkinnedMesh || src.isMesh) sources.push(src);
      src.children && src.children.forEach((c) => { if (c.isSkinnedMesh || c.isMesh) sources.push(c); });
      const out = [];
      for (const s of sources) {
        const dict = s.morphTargetDictionary;
        const geo = live || !dict ? s.geometry : bake(s.geometry, dict, morphs, mkey);
        const mat = material || (Array.isArray(s.material) ? s.material[0] : s.material);
        let mesh;
        if (s.isSkinnedMesh) {
          mesh = new THREE.SkinnedMesh(geo, mat);
          const sk = new THREE.Skeleton(s.skeleton.bones.map(b => bones[b.name] || bones.hips), s.skeleton.boneInverses);
          mesh.bind(sk, s.bindMatrix);
          parent.add(mesh);
        } else { mesh = new THREE.Mesh(geo, mat); (bones.head || parent).add(mesh); }
        if (live && dict) { mesh.morphTargetDictionary = dict; mesh.morphTargetInfluences = new Array(Object.keys(dict).length).fill(0); for (const n in dict) mesh.morphTargetInfluences[dict[n]] = morphs[n] || 0; }
        mesh.castShadow = true; mesh.receiveShadow = true; mesh.frustumCulled = false;
        out.push(mesh);
      }
      state.extras[slot] = out;
    };
    const pieceMaterial = (src, tint) => {
      const mn = ((Array.isArray(src.material) ? src.material[0] : src.material).name || 'M_cloth').replace(/\.\d+$/, '');
      const vc = !!src.geometry.attributes.color;
      if (!tint || !/^M_(cloth|metal_)/.test(mn)) return getMaterial(mn, { vertexColors: vc });
      // The pieces carry their authored colours as vertex colours. A tint recolours the cloth (its average
      // becomes the tint, the baked shading is kept) and only shades the metal; leather, fur, rope stay as made.
      const c = new THREE.Color(tint);
      if (mn === 'M_cloth') {
        const avg = avgVertexColor(src.geometry);
        c.setRGB(Math.min(c.r / (avg[0] * 0.71), 8), Math.min(c.g / (avg[1] * 0.71), 8), Math.min(c.b / (avg[2] * 0.71), 8));
      } else c.setRGB(Math.pow(c.r, 0.4), Math.pow(c.g, 0.4), Math.pow(c.b, 0.4));
      return getMaterial(mn, { vertexColors: vc, variant: 't' + tint + (mn === 'M_cloth' ? '|' + src.geometry.uuid : ''), tint: c });
    };
    const refreshHidden = () => {
      const hide = {};
      for (const slot in state.outfit || {}) { const info = outfitInfo[state.outfit[slot]]; if (info && info.hides) for (const r of info.hides) hide[r] = true; }
      const regions = ['body_torso', 'body_arms', 'body_hands', 'body_legs', 'body_feet'];
      if (live) { for (const r of regions) if (bodyMeshes[r]) bodyMeshes[r].visible = !hide[r]; }
      else {
        // one skinned mesh for everything visible below the neck
        if (state.merged) { state.merged.parent && state.merged.parent.remove(state.merged); state.merged.geometry.dispose(); state.merged = null; }
        const vis = regions.filter(r => bodyMeshes[r] && !hide[r]);
        for (const r of regions) if (bodyMeshes[r]) bodyMeshes[r].visible = false;
        if (vis.length) {
          const first = bodyMeshes[vis[0]];
          let geo = null;
          try { geo = mergeGeometries(vis.map(r => bodyMeshes[r].geometry), false); } catch (e) { geo = null; }
          if (geo) {
            const mesh = new THREE.SkinnedMesh(geo, skinB);
            mesh.bind(first.skeleton, first.bindMatrix);
            mesh.castShadow = true; mesh.receiveShadow = true; mesh.frustumCulled = false;
            first.parent.add(mesh);
            state.merged = mesh;
          } else for (const r of vis) bodyMeshes[r].visible = true;
        }
      }
      if (state.extras.hair) for (const m of state.extras.hair) m.visible = !hide.hair;
      if (state.extras.beard) for (const m of state.extras.beard) m.visible = !hide.beard;
    };
    const api = {
      setHair(id, color) { state.look.hair = id; if (color) state.look.hairColor = color; const c = state.look.hairColor || '#47301f'; addPiece('hair', id && id !== 'none' ? hairSrc[id] : null, hairMaterial(c)); if (bodyMeshes.brows) bodyMeshes.brows.material = hairMaterial(c); refreshHidden(); },
      setBeard(id) { state.look.beard = id; addPiece('beard', id && id !== 'none' ? hairSrc[id] : null, hairMaterial(state.look.hairColor || '#47301f')); },
      /** pieces: { head, chest, legs } -> model ids like 'chain_chest' (or item ids) */
      setOutfit(pieces, tint) {
        state.outfit = {};
        for (const slot of ['head', 'chest', 'legs']) {
          let id = pieces && pieces[slot];
          if (id && ITEMS[id]) id = ITEMS[id].model;
          const src = id ? outfitSrc[id] : null;
          if (src) { state.outfit[slot] = id; addPiece('outfit_' + slot, src, null); for (const m of state.extras['outfit_' + slot] || []) m.material = pieceMaterial(m, tint); }
          else addPiece('outfit_' + slot, null);
        }
        refreshHidden();
      },
      setMorph(name, v) { morphs[name] = v; if (!live) return; inner.traverse((o) => { if (o.morphTargetDictionary && o.morphTargetDictionary[name] !== undefined) o.morphTargetInfluences[o.morphTargetDictionary[name]] = v; }); },
      setSkin(color) { skinB.color.set(color); skinH.color.set(color); },
      setEyes(color) { const m = eyeMaterial(color); for (const n of ['eye_L', 'eye_R']) if (bodyMeshes[n]) bodyMeshes[n].material = m; },
      setPaint(style, color, scar) { for (const m of [skinH]) { if (style !== undefined) m.userData.u.uPaint.value.x = PAINT_ID[style] || 0; if (scar !== undefined) m.userData.u.uPaint.value.y = SCAR_ID[scar] || 0; if (color) m.userData.u.uPaintCol.value.set(color); } },
      state,
    };
    inner.userData.human = api;
    refreshHidden();
    api.setHair(look.hair, look.hairColor);
    if (look.beard) api.setBeard(look.beard);
    if (look.outfit) api.setOutfit({ head: look.noHelm ? null : look.outfit + '_head', chest: look.outfit + '_chest', legs: look.outfit + '_legs' }, look.tintOutfit);
    return inner;
  };
}
