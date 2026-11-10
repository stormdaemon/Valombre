// Material library: every .glb material is replaced, by NAME, with one of these shared PBR materials.
// Texture convention: <name>_a.png = albedo (sRGB) + height (A) ; <name>_n.png = normal XY (RG) + roughness (B) + AO (A).
import * as THREE from 'three';
import { U, patchMaterial, inject } from '../core/globals.js';
import { loadTexture } from '../core/assets.js';

export const MU = {
  uNight: { value: 0 },                              // 0 day .. 1 night (window glow, eyes)
  uEnvInt: { value: 1 },
};

// name -> definition. tex: texture base name; tile: UVs are in meters / tile (informative); st: standard params.
const DEFS = {
  M_stone_wall: { tex: 'stone_wall' }, M_stone_brick: { tex: 'stone_brick' }, M_cobble: { tex: 'cobble' },
  M_plaster: { tex: 'plaster' }, M_wood_planks: { tex: 'wood_planks' }, M_roof_tiles: { tex: 'roof_tiles' }, M_thatch: { tex: 'thatch' },
  M_rock: { tex: 'terrain_rock' },
  M_bark_oak: { tex: 'bark_oak' }, M_bark_pine: { tex: 'bark_pine' }, M_bark_birch: { tex: 'bark_birch' },
  M_metal_iron: { tex: 'metal', metal: 0.85, rough: 1.25, env: 1 },
  M_metal_steel: { tex: 'metal', metal: 1.0, rough: 0.6, env: 1 },
  M_metal_gold: { tex: 'metal', metal: 1.0, rough: 0.5, env: 1 },
  M_metal_bronze: { tex: 'metal', metal: 1.0, rough: 0.7, env: 1 },
  M_leather: { tex: 'leather' }, M_cloth: { tex: 'cloth', rough: 1.1 }, M_rope: { tex: 'rope' },
  M_fur: { tex: 'fur' }, M_hide: { tex: 'hide' }, M_chitin: { tex: 'chitin', rough: 0.9, env: 1 }, M_bone: { tex: 'bone' },
  M_skin: { tex: 'skin', skin: true }, M_hair: { tex: 'hair', hair: true }, M_eye: { eye: true }, M_mouth: { color: 0x2a0f0f, roughness: 0.5 },
  M_eye_glow: { color: 0x101010, glow: [1.0, 0.9, 0.7], glowI: 0.0, roughness: 0.2 },
  M_crystal: { color: 0x9fdcf0, glow: [0.45, 0.85, 1.0], glowI: 3.2, roughness: 0.15, env: 1 },
  M_rune_glow: { color: 0x1a1a22, glow: [0.5, 0.8, 1.0], glowI: 2.4, roughness: 0.6 },
  M_ember: { color: 0x200a04, glow: [1.0, 0.36, 0.08], glowI: 4.5, roughness: 0.8 },
  M_window_glow: { color: 0x2a2a30, glow: [1.0, 0.62, 0.25], glowI: 2.2, roughness: 0.25, night: true, env: 1 },
  M_ice: { color: 0xa9d2ee, glow: [0.25, 0.5, 0.8], glowI: 0.35, roughness: 0.12, env: 1 },
  M_obsidian: { color: 0x0b0b0e, roughness: 0.12, env: 1 },
  M_mushroom: { roughness: 0.7 },
  M_proxy: { roughness: 0.8 },
};

const texCache = new Map();
let texOpts = { aniso: 4, low: false };
export function setTextureOptions(o) { Object.assign(texOpts, o); }

function getTex(name, srgb) {
  const k = name + (srgb ? '_a' : '_n');
  if (!texCache.has(k)) {
    // placeholder 1x1 until the file arrives
    const data = srgb ? new Uint8Array([180, 180, 180, 255]) : new Uint8Array([128, 128, 200, 255]);
    const t = new THREE.DataTexture(data, 1, 1, THREE.RGBAFormat);
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.needsUpdate = true;
    const holder = { tex: t, users: [] };
    texCache.set(k, holder);
    holder.promise = loadTexture(`assets/textures/${k}.png`, { srgb, aniso: texOpts.aniso }).then((real) => {
      if (!real) return;
      holder.tex = real;
      for (const fn of holder.users) fn(real);
      holder.users.length = 0;
    });
  }
  return texCache.get(k);
}

/** wait until every texture requested so far is loaded */
export function texturesReady() { return Promise.all([...texCache.values()].map(h => h.promise)); }

const matCache = new Map();
export let envMap = null;
const envUsers = new Set();
export function setEnvMap(tex) { envMap = tex; for (const m of envUsers) { m.envMap = tex; } }

function packPatch(sh) {
  // packed normal/roughness/AO texture bound as normalMap
  sh.fragmentShader = inject(sh.fragmentShader, 'roughnessmap_fragment', /* glsl */`
    #ifdef USE_NORMALMAP
      vec4 valPack = texture2D( normalMap, vNormalMapUv );
    #else
      vec4 valPack = vec4( 0.5, 0.5, 1.0, 1.0 );
    #endif
    float roughnessFactor = clamp( roughness * valPack.b, 0.04, 1.0 );
  `);
  sh.fragmentShader = inject(sh.fragmentShader, 'normal_fragment_maps', /* glsl */`
    #ifdef USE_NORMALMAP_TANGENTSPACE
      vec3 mapN = vec3( valPack.xy * 2.0 - 1.0, 0.0 );
      mapN.xy *= normalScale;
      mapN.z = sqrt( max( 1.0 - dot( mapN.xy, mapN.xy ), 0.05 ) );
      normal = normalize( tbn * mapN );
    #endif
  `);
  sh.fragmentShader = inject(sh.fragmentShader, 'aomap_fragment', 'reflectedLight.indirectDiffuse *= valPack.a;');
}

/**
 * Get the shared material for a glb material name.
 * opts: vertexColors (bool), skinned handled by three automatically, variant (string key for tinted variants), tint (THREE.Color multiplier)
 */
export function getMaterial(name, opts = {}) {
  const def = DEFS[name] || (console.warn('[materials] unknown material', name), DEFS.M_proxy);
  const vc = opts.vertexColors !== false;
  const key = name + '|' + (vc ? 1 : 0) + '|' + (opts.variant || '') + '|' + (opts.doubleSide ? 'd' : '');
  if (matCache.has(key)) return matCache.get(key);
  const m = new THREE.MeshStandardMaterial({
    color: def.color ?? 0xffffff, roughness: def.roughness ?? def.rough ?? 1, metalness: def.metal ?? 0,
    vertexColors: vc, side: opts.doubleSide ? THREE.DoubleSide : THREE.FrontSide,
  });
  m.name = name;
  if (opts.tint) m.color.multiply(opts.tint);
  if (def.tex) {
    const a = getTex(def.tex, true), n = getTex(def.tex, false);
    m.map = a.tex; m.normalMap = n.tex;
    m.normalScale.set(1, -1);
    if (a.tex.image.width === 1) a.users.push((t) => { m.map = t; m.needsUpdate = true; });
    if (n.tex.image.width === 1) n.users.push((t) => { m.normalMap = t; m.needsUpdate = true; });
  }
  if (def.glow) { m.emissive.setRGB(def.glow[0], def.glow[1], def.glow[2]); m.emissiveIntensity = def.glowI; }
  if (def.env) { m.envMap = envMap; m.envMapIntensity = 1.0; envUsers.add(m); }
  const uniforms = { uNight: MU.uNight };
  patchMaterial(m, (sh) => {
    Object.assign(sh.uniforms, uniforms);
    if (def.tex) packPatch(sh);
    // vertex colours were authored rather dark: calibrate (x^0.78) while keeping the stock chunk for later patches
    sh.fragmentShader = inject(sh.fragmentShader, 'color_fragment', `
      #if defined( USE_COLOR_ALPHA ) || defined( USE_COLOR )
        diffuseColor.rgb *= pow( max( vColor.rgb, vec3( 1e-3 ) ), vec3( -0.22 ) );
      #endif`, 'after');
    if (def.glow) {
      // the vertex colour of a glowing part is its intended tint: take its hue (when it has one) at the material's brightness
      sh.fragmentShader = inject(sh.fragmentShader, 'emissivemap_fragment', `
      #if defined( USE_COLOR_ALPHA ) || defined( USE_COLOR )
      {
        vec3 vcT = max( vColor.rgb, vec3( 1e-3 ) );
        float mxT = max( vcT.r, max( vcT.g, vcT.b ) ), mnT = min( vcT.r, min( vcT.g, vcT.b ) );
        vec3 hueT = vcT / mxT;
        float lumE = dot( totalEmissiveRadiance, vec3( 0.2126, 0.7152, 0.0722 ) );
        vec3 tintT = hueT * lumE / max( dot( hueT, vec3( 0.2126, 0.7152, 0.0722 ) ), 0.12 );
        totalEmissiveRadiance = mix( totalEmissiveRadiance, tintT, smoothstep( 0.18, 0.5, ( mxT - mnT ) / mxT ) );
      }
      #endif`, 'before');
    }
    if (def.night) {
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uNight;');
      sh.fragmentShader = inject(sh.fragmentShader, 'emissivemap_fragment', 'totalEmissiveRadiance *= 0.04 + 0.96 * uNight;');
    }
  }, 'lib:' + name + (def.night ? 'n' : ''));
  matCache.set(key, m);
  return m;
}

/** Replace all materials of a loaded glb scene by library materials. Returns list of {mesh, name}. */
export function applyLibrary(root, opts = {}) {
  const out = [];
  root.traverse((o) => {
    if (!o.isMesh) return;
    const hasColor = !!o.geometry.attributes.color;
    const conv = (mat) => {
      const name = mat && mat.name ? mat.name.replace(/\.\d+$/, '') : 'M_proxy';
      out.push({ mesh: o, name });
      if (opts.custom && opts.custom[name]) return opts.custom[name](o, mat);
      return getMaterial(name, { vertexColors: hasColor, variant: opts.variant, tint: opts.tint });
    };
    o.material = Array.isArray(o.material) ? o.material.map(conv) : conv(o.material);
    o.castShadow = opts.castShadow ?? true;
    o.receiveShadow = opts.receiveShadow ?? true;
  });
  return out;
}

export function materialDef(name) { return DEFS[name]; }
