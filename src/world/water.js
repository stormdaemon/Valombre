// Sea / lakes (one plane at sea level following the camera) + river ribbon. Depth comes from the heightmap,
// so no depth-texture read is needed: shoreline fade, foam, absorption colour, fresnel sky reflection, sun glitter.
import * as THREE from 'three';
import { U, FOG_FUNC, SUNVIS_FUNC, WORLD_SIZE } from '../core/globals.js';
import { HEIGHT_GLSL } from './terrain.js';

const WATER_VERT = /* glsl */`
varying vec3 vWorld;
varying float vSurf;
#ifdef RIVER
attribute vec2 aFlow;
varying vec2 vFlow;
varying float vEdge;
#endif
void main() {
  vec4 w = modelMatrix * vec4( position, 1.0 );
  vWorld = w.xyz;
  vSurf = w.y;
  #ifdef RIVER
    vFlow = aFlow;
    vEdge = uv.x;
  #endif
  gl_Position = projectionMatrix * viewMatrix * w;
}`;

const WATER_FRAG = /* glsl */`
uniform sampler2D uWaterN;
uniform sampler2D uSplat1;
uniform float uTime;
uniform vec3 uZenith;
uniform vec3 uHorizon;
uniform vec3 uSunCol;
uniform vec3 uAmbient;
uniform vec3 uShallow;
uniform vec3 uDeep;
uniform vec3 uSwamp;
uniform float uQuality;
varying vec3 vWorld;
varying float vSurf;
#ifdef RIVER
varying vec2 vFlow;
varying float vEdge;
#endif
${HEIGHT_GLSL}
${FOG_FUNC}
${SUNVIS_FUNC}
void main() {
  vec3 wp = vWorld;
  float depth = vSurf - valHeight( wp.xz );
  #ifdef RIVER
    float edge = smoothstep( 0.0, 0.16, vEdge ) * smoothstep( 1.0, 0.84, vEdge );
    depth = max( depth, 0.0 ) * edge * 1.6 + 0.02;
  #else
    if ( depth < -0.02 ) discard;
  #endif
  vec3 V = cameraPosition - wp;
  float dist = length( V );
  V /= dist;
  // normals: two scrolling layers (+ one large swell layer), flattened in the distance
  #ifdef RIVER
    vec2 flow = vFlow * uTime;
    vec2 n1 = texture2D( uWaterN, wp.xz * 0.11 - flow * 0.22 ).rg;
    vec2 n2 = texture2D( uWaterN, wp.xz * 0.27 - flow * 0.37 + 0.37 ).rg;
    float nStr = 0.55;
  #else
    vec2 n1 = texture2D( uWaterN, wp.xz * 0.055 + uTime * vec2( 0.018, 0.011 ) ).rg;
    vec2 n2 = texture2D( uWaterN, wp.xz * 0.151 + uTime * vec2( -0.022, 0.027 ) ).rg;
    float nStr = 0.42;
  #endif
  vec2 nn = ( n1 + n2 - 1.0 );
  vec2 n3 = texture2D( uWaterN, wp.xz * 0.012 + uTime * vec2( 0.006, -0.004 ) ).rg - 0.5;
  nn = nn * nStr + n3 * 0.5;
  nn *= 1.0 / ( 1.0 + dist * 0.006 );
  vec3 N = normalize( vec3( nn.x, 1.0, nn.y ) );
  float ndv = max( dot( N, V ), 0.0 );
  float fres = 0.02 + 0.98 * pow( 1.0 - ndv, 5.0 );
  // reflection of the analytic sky
  vec3 R = reflect( -V, N );
  R.y = abs( R.y );
  vec3 refl = mix( uZenith, uHorizon, pow( 1.0 - R.y, 3.2 ) );
  float vis = valSunVis( wp, uSunDir );
  float sd = max( dot( R, uSunDir ), 0.0 );
  refl += uSunCol * ( pow( sd, 12.0 ) * 0.04 + pow( sd, 900.0 ) * 9.0 * vis );
  // body colour by depth, murky in the swamp
  float mud = texture2D( uSplat1, wp.xz * ${(1 / WORLD_SIZE).toFixed(10)} + 0.5 ).b;
  float k = 1.0 - exp( -depth * mix( 0.42, 1.6, mud ) );
  vec3 body = mix( uShallow, uDeep, k );
  body = mix( body, uSwamp, mud * 0.85 );
  float nl = max( dot( N, uSunDir ), 0.0 );
  body *= uAmbient + uSunCol * ( 0.16 * vis * ( 0.4 + 0.6 * nl ) );
  // foam near the shore
  float foam = 0.0;
  #ifndef RIVER
    float fn = texture2D( uWaterN, wp.xz * 0.21 + uTime * 0.01 ).b;
    float band = sin( depth * 7.0 - uTime * 1.4 + fn * 5.0 ) * 0.5 + 0.5;
    foam = smoothstep( 0.9, 0.05, depth ) * smoothstep( 0.35, 0.8, fn * 0.7 + band * 0.5 ) * ( 1.0 - mud );
    foam += smoothstep( 0.22, 0.0, depth ) * 0.6 * ( 1.0 - mud );
  #else
    float fn = texture2D( uWaterN, wp.xz * 0.3 - flow * 0.4 ).b;
    foam = smoothstep( 0.62, 0.9, fn ) * 0.35 * edge;
  #endif
  foam = clamp( foam, 0.0, 1.0 );
  vec3 colr = mix( body, refl, fres );
  colr = mix( colr, ( uAmbient + uSunCol * 0.25 * vis ) * 0.92, foam * 0.85 );
  float alpha = smoothstep( 0.0, mix( 0.55, 0.12, mud ), depth ) * mix( 0.72, 1.0, k );
  alpha = max( alpha, fres * smoothstep( 0.0, 0.1, depth ) );
  alpha = max( alpha, foam * 0.8 );
  #ifdef RIVER
    alpha *= edge;
  #endif
  colr = valFog( colr, wp );
  gl_FragColor = vec4( colr, alpha );
}`;

export class Water {
  constructor(world, atmosphere, waterNormalTex) {
    this.world = world; this.atmo = atmosphere;
    waterNormalTex.wrapS = waterNormalTex.wrapT = THREE.RepeatWrapping;
    this.uniforms = {
      ...U,
      uWaterN: { value: waterNormalTex },
      uSplat1: { value: world.splat1Tex },
      uHeightTex: { value: world.heightTex }, uHInfo: { value: world.heightInfo },
      uZenith: atmosphere.skyUniforms.uZenith, uHorizon: atmosphere.skyUniforms.uHorizon,
      uSunCol: { value: new THREE.Color() }, uAmbient: { value: new THREE.Color() },
      uShallow: { value: new THREE.Color(0.055, 0.16, 0.14) }, uDeep: { value: new THREE.Color(0.008, 0.04, 0.065) },
      uSwamp: { value: new THREE.Color(0.075, 0.085, 0.035) }, uQuality: { value: 1 },
    };
    const mk = (river) => new THREE.ShaderMaterial({
      vertexShader: WATER_VERT, fragmentShader: WATER_FRAG, uniforms: this.uniforms,
      defines: river ? { RIVER: 1 } : {}, transparent: true, depthWrite: false, fog: false,
    });
    const geo = new THREE.PlaneGeometry(1, 1, 1, 1).rotateX(-Math.PI / 2);
    this.sea = new THREE.Mesh(geo, mk(false));
    this.sea.scale.set(40000, 1, 40000);
    this.sea.frustumCulled = false;
    this.sea.renderOrder = 30;
    this.group = new THREE.Group();
    this.group.add(this.sea);
    if (world.river && world.river.points.length > 2) {
      this.river = new THREE.Mesh(this._riverGeo(world.river), mk(true));
      this.river.renderOrder = 29;
      this.river.frustumCulled = false;
      this.group.add(this.river);
    }
  }

  _riverGeo(river) {
    const pts = river.points, n = pts.length, hw = river.width * 0.5 + 4.0;
    const pos = new Float32Array(n * 2 * 3), uv = new Float32Array(n * 2 * 2), flow = new Float32Array(n * 2 * 2);
    const idx = [];
    for (let i = 0; i < n; i++) {
      const a = pts[Math.max(i - 1, 0)], b = pts[Math.min(i + 1, n - 1)];
      let tx = b[0] - a[0], tz = b[1] - a[1];
      const l = Math.hypot(tx, tz) || 1; tx /= l; tz /= l;
      const nx = -tz, nz = tx, p = pts[i];
      const drop = Math.max((a[2] - b[2]) / l, 0);
      const speed = 0.6 + Math.min(drop * 14, 1.6);
      for (let s = 0; s < 2; s++) {
        const k = i * 2 + s, sg = s ? 1 : -1;
        pos[k * 3] = p[0] + nx * hw * sg; pos[k * 3 + 1] = p[2]; pos[k * 3 + 2] = p[1] + nz * hw * sg;
        uv[k * 2] = s; uv[k * 2 + 1] = i;
        flow[k * 2] = tx * speed; flow[k * 2 + 1] = tz * speed;
      }
      if (i < n - 1) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('aFlow', new THREE.BufferAttribute(flow, 2));
    g.setIndex(idx);
    return g;
  }

  /** river surface height near (x,z), or -Infinity when not on the river */
  riverLevel(x, z) {
    const r = this.world.river;
    if (!r) return -Infinity;
    const pts = r.points, hw = r.width * 0.5 + 1.5;
    let best = -Infinity, bd = hw * hw;
    for (let i = 0; i < pts.length; i++) {
      const dx = pts[i][0] - x, dz = pts[i][1] - z, d = dx * dx + dz * dz;
      if (d < bd + 150) { if (d < bd + 36) { bd = Math.min(bd, d); best = pts[i][2]; } }
    }
    return best;
  }

  update(camera) {
    this.sea.position.set(camera.position.x, 0, camera.position.z);
    const a = this.atmo;
    this.uniforms.uSunCol.value.copy(a.sun.color).multiplyScalar(a.sun.intensity);
    this.uniforms.uAmbient.value.copy(a.hemi.color).multiplyScalar(a.hemi.intensity * 0.32);
  }
}
