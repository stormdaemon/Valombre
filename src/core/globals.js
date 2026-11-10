// Shared uniforms + global shader-chunk patches (atmospheric fog, terrain/cloud sun occlusion).
// Every lit material of the game goes through patchMaterial() so that it uses them.
import * as THREE from 'three';

export const WORLD_SIZE = 5120;
export const WORLD_HALF = 2560;

/** Shared uniform objects (same object referenced by every material => one update per frame). */
export const U = {
  uTime: { value: 0 },
  uSunDir: { value: new THREE.Vector3(0.45, 0.75, 0.35).normalize() },   // direction TOWARD the main light (sun or moon)
  uFogColor: { value: new THREE.Color(0.6, 0.7, 0.8) },
  uFogParams: { value: new THREE.Vector4(0.0006, 0.012, 0.0, 0.96) },    // density, height falloff, base height, max opacity
  uFogSun: { value: new THREE.Vector4(1.0, 0.8, 0.5, 8.0) },              // inscatter color (rgb), power
  uWorld: { value: new THREE.Vector4(WORLD_HALF, 1 / WORLD_SIZE, 0, 0) },
  uTerrainShadow: { value: null },                                        // RG16F: r = lit altitude, g = shadow depth above ground
  uShadowSoft: { value: new THREE.Vector2(6.0, 1.0) },                    // softness (m), enabled
  uNoiseTex: { value: null },                                             // fx_noise.png (tileable RGBA)
  uCloud: { value: new THREE.Vector4(0.00012, 0.0, 0.0, 0.5) },           // scale, offset x, offset z, coverage
  uCloudShadow: { value: 0.55 },
  uWind: { value: new THREE.Vector4(0.8, 0.6, 1.0, 0.0) },                // dir x, dir z, strength, unused
  uPlayerPos: { value: new THREE.Vector3() },
  uWet: { value: 0 },                                                     // rain wetness 0..1
};

const C = THREE.ShaderChunk;

// ---------------------------------------------------------------- fog (analytic height fog + sun inscatter)
C.fog_pars_vertex = /* glsl */`
#ifdef USE_FOG
  varying float vFogDepth;
  #ifdef VAL_GLOBALS
    varying vec3 vFogWorld;
  #endif
#endif`;

C.fog_vertex = /* glsl */`
#ifdef USE_FOG
  vFogDepth = - mvPosition.z;
  #ifdef VAL_GLOBALS
    #ifdef VAL_WORLD_SPACE
      vFogWorld = transformed;
    #else
      vec4 valW = vec4( transformed, 1.0 );
      #ifdef USE_BATCHING
        valW = batchingMatrix * valW;
      #endif
      #ifdef USE_INSTANCING
        valW = instanceMatrix * valW;
      #endif
      vFogWorld = ( modelMatrix * valW ).xyz;
    #endif
  #endif
#endif`;

export const FOG_FUNC = /* glsl */`
uniform vec3 uFogColor;
uniform vec4 uFogParams;
uniform vec4 uFogSun;
uniform vec3 uSunDir;
vec3 valFog( vec3 col, vec3 wpos ) {
  vec3 v = wpos - cameraPosition;
  float dist = length( v );
  vec3 rd = v / max( dist, 1e-4 );
  float b = uFogParams.y;
  float ry = rd.y;
  ry = abs( ry ) < 1e-3 ? ( ry < 0.0 ? -1e-3 : 1e-3 ) : ry;
  float e0 = exp( clamp( -b * ( cameraPosition.y - uFogParams.z ), -20.0, 6.0 ) );
  float t = b * ry * dist;
  float integ = ( 1.0 - exp( -clamp( t, -20.0, 20.0 ) ) ) / ( b * ry );
  float f = 1.0 - exp( -max( uFogParams.x * e0 * integ, 0.0 ) );
  f = min( f, uFogParams.w );
  float s = pow( max( dot( rd, uSunDir ), 0.0 ), uFogSun.w );
  vec3 fc = uFogColor + uFogSun.rgb * s * ( 0.35 + 0.65 * f );
  return mix( col, fc, f );
}`;

C.fog_pars_fragment = /* glsl */`
#ifdef USE_FOG
  varying float vFogDepth;
  #ifdef VAL_GLOBALS
    varying vec3 vFogWorld;
    ${FOG_FUNC}
  #else
    uniform vec3 fogColor;
    #ifdef FOG_EXP2
      uniform float fogDensity;
    #else
      uniform float fogNear;
      uniform float fogFar;
    #endif
  #endif
#endif`;

C.fog_fragment = /* glsl */`
#ifdef USE_FOG
  #ifdef VAL_GLOBALS
    gl_FragColor.rgb = valFog( gl_FragColor.rgb, vFogWorld );
  #else
    #ifdef FOG_EXP2
      float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
    #else
      float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
    #endif
    gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
  #endif
#endif`;

// ---------------------------------------------------------------- sun visibility (terrain heightfield shadow + cloud shadows)
export const SUNVIS_FUNC = /* glsl */`
uniform sampler2D uTerrainShadow;
uniform vec2 uShadowSoft;
uniform sampler2D uNoiseTex;
uniform vec4 uCloud;
uniform float uCloudShadow;
uniform vec4 uWorld;
float valCloudCover( vec2 xz ) {
  vec2 uv = xz * uCloud.x + uCloud.yz;
  float c = texture2D( uNoiseTex, uv ).a * 0.65 + texture2D( uNoiseTex, uv * 2.7 + 0.31 ).r * 0.35;
  return smoothstep( 1.0 - uCloud.w - 0.12, 1.0 - uCloud.w + 0.22, c );
}
float valSunVis( vec3 wpos, vec3 sunDir ) {
  float vis = 1.0;
  if ( uShadowSoft.y > 0.5 ) {
    vec2 uv = wpos.xz * uWorld.y + 0.5;
    vec2 ts = texture2D( uTerrainShadow, uv ).rg;
    float ground = 1.0 - smoothstep( 0.0, uShadowSoft.x, ts.g );
    float above = smoothstep( ts.r - uShadowSoft.x, ts.r, wpos.y - 1.5 );
    vis = max( ground, above );
  }
  vec2 cxz = wpos.xz + sunDir.xz * ( ( 900.0 - wpos.y ) / max( sunDir.y, 0.25 ) );
  vis *= 1.0 - uCloudShadow * valCloudCover( cxz );
  return vis;
}`;

C.lights_pars_begin = /* glsl */`
#if defined( VAL_GLOBALS ) && defined( USE_FOG )
  ${SUNVIS_FUNC}
#endif
` + C.lights_pars_begin;

{
  const needle = 'getSunLightInfo( sunLight, directLight );';
  if (!C.lights_fragment_begin.includes(needle)) console.error('[globals] three.js chunk changed: sun light patch not applied');
  C.lights_fragment_begin = C.lights_fragment_begin.replace(needle, needle + /* glsl */`
    #if defined( VAL_GLOBALS ) && defined( USE_FOG )
      directLight.color *= valSunVis( vFogWorld, uSunDir );
    #endif
  `);
}

/**
 * Make a material use the shared atmosphere/shadow uniforms. `extra(shader)` lets the caller do further
 * shader edits; `key` must identify those edits (program cache key).
 */
export function patchMaterial(mat, extra = null, key = '') {
  mat.defines = mat.defines || {};
  mat.defines.VAL_GLOBALS = 1;
  mat.fog = true;
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (shader, renderer) => {
    if (prev) prev.call(mat, shader, renderer);
    for (const k in U) if (!(k in shader.uniforms)) shader.uniforms[k] = U[k];
    if (extra) extra(shader, renderer);
    mat.userData.shader = shader;
  };
  const prevKey = mat.customProgramCacheKey ? mat.customProgramCacheKey.bind(mat) : null;
  mat.customProgramCacheKey = () => 'val|' + key + (prevKey ? prevKey() : '');
  return mat;
}

/** Insert `code` before/after/in place of an #include in a shader stage. */
export function inject(src, include, code, mode = 'replace') {
  const tag = `#include <${include}>`;
  if (!src.includes(tag)) { console.warn('[inject] missing', include); return src; }
  if (mode === 'before') return src.replace(tag, code + '\n' + tag);
  if (mode === 'after') return src.replace(tag, tag + '\n' + code);
  return src.replace(tag, code);
}
