// Atmosphere: time of day, sun/moon light (cascaded shadows), hemisphere ambient, procedural sky
// with clouds/stars, fog parameters and the large-scale terrain shadow texture.
import * as THREE from 'three';
import { SunLight } from 'three/addons/lights/SunLight.js';
import { U, WORLD_HALF } from '../core/globals.js';

const sstep = (a, b, x) => { const t = Math.min(Math.max((x - a) / (b - a), 0), 1); return t * t * (3 - 2 * t); };
const col = (r, g, b) => new THREE.Color(r, g, b);
const KEY = {
  day: { zen: col(0.085, 0.24, 0.60), hor: col(0.46, 0.63, 0.84), sun: col(1.0, 0.95, 0.86), sunI: 3.7, sky: col(0.50, 0.66, 0.95), skyI: 2.1, gnd: col(0.44, 0.41, 0.33), expo: 1.0 },
  gold: { zen: col(0.10, 0.20, 0.46), hor: col(0.86, 0.56, 0.33), sun: col(1.0, 0.63, 0.33), sunI: 3.1, sky: col(0.55, 0.52, 0.62), skyI: 1.75, gnd: col(0.42, 0.33, 0.25), expo: 1.08 },
  twi: { zen: col(0.035, 0.06, 0.17), hor: col(0.72, 0.34, 0.17), sun: col(1.0, 0.42, 0.18), sunI: 0.7, sky: col(0.32, 0.31, 0.50), skyI: 1.25, gnd: col(0.24, 0.2, 0.2), expo: 1.35 },
  night: { zen: col(0.0035, 0.006, 0.017), hor: col(0.012, 0.021, 0.048), sun: col(0.46, 0.62, 1.0), sunI: 0.85, sky: col(0.13, 0.19, 0.40), skyI: 1.0, gnd: col(0.075, 0.09, 0.14), expo: 1.6 },
};

const SKY_VERT = /* glsl */`
uniform mat4 uProjInv;
uniform mat4 uCamWorld;
varying vec3 vRay;
void main() {
  vec4 v = uProjInv * vec4( position.xy, 1.0, 1.0 );
  vRay = mat3( uCamWorld ) * ( v.xyz / v.w );
  gl_Position = vec4( position.xy, 1.0, 1.0 );
}`;

const SKY_FRAG = /* glsl */`
uniform vec3 uZenith;
uniform vec3 uHorizon;
uniform vec3 uGround;
uniform vec3 uSunPos;
uniform vec3 uMoonPos;
uniform vec3 uSunDisc;
uniform vec3 uGlow;
uniform vec3 uMoonCol;
uniform float uStars;
uniform vec3 uCloudLit;
uniform vec3 uCloudDark;
uniform sampler2D uNoiseTex;
uniform vec4 uCloud;
uniform float uTime;
varying vec3 vRay;

float hash13( vec3 p ) { p = fract( p * 0.1031 ); p += dot( p, p.zyx + 31.32 ); return fract( ( p.x + p.y ) * p.z ); }
float cloudCover( vec2 xz ) {
  vec2 uv = xz * uCloud.x + uCloud.yz;
  float c = texture2D( uNoiseTex, uv ).a * 0.65 + texture2D( uNoiseTex, uv * 2.7 + 0.31 ).r * 0.35;
  return c;
}
void main() {
  vec3 rd = normalize( vRay );
  float y = rd.y;
  float t = pow( 1.0 - clamp( y, 0.0, 1.0 ), 3.2 );
  vec3 col = mix( uZenith, uHorizon, t );
  col = mix( col, uGround, smoothstep( 0.0, -0.12, y ) );
  float sd = max( dot( rd, uSunPos ), 0.0 );
  float hz = 1.0 - clamp( y, 0.0, 1.0 );
  col += uGlow * ( pow( sd, 5.0 ) * 0.22 * hz + pow( sd, 40.0 ) * 0.55 + pow( sd, 600.0 ) * 2.0 );
  float above = smoothstep( -0.02, 0.01, y );
  // stars
  if ( uStars > 0.01 && y > 0.0 ) {
    vec3 sp = rd * 220.0;
    vec3 ip = floor( sp );
    float h = hash13( ip );
    vec3 fp = fract( sp ) - 0.5;
    float tw = 0.75 + 0.25 * sin( uTime * 2.0 + h * 80.0 );
    float star = step( 0.9965, h ) * smoothstep( 0.42, 0.05, length( fp ) ) * tw;
    col += vec3( 0.9, 0.95, 1.0 ) * star * uStars * 2.2 * smoothstep( 0.0, 0.25, y ) * ( 0.4 + 2.0 * fract( h * 91.7 ) );
  }
  // moon
  float md = dot( rd, uMoonPos );
  float moon = smoothstep( 0.99962, 0.99974, md );
  if ( moon > 0.0 ) {
    vec3 ax = normalize( cross( uMoonPos, vec3( 0.0, 1.0, 0.0 ) ) );
    vec3 ay = cross( ax, uMoonPos );
    vec2 mp = vec2( dot( rd, ax ), dot( rd, ay ) ) / 0.0276;
    float crat = texture2D( uNoiseTex, mp * 0.35 + 0.4 ).g;
    float lim = sqrt( max( 1.0 - dot( mp, mp ), 0.0 ) );
    col = mix( col, uMoonCol * ( 0.55 + 0.45 * crat ) * ( 0.45 + 0.55 * lim ), moon * above );
  }
  col += uMoonCol * 0.06 * pow( max( md, 0.0 ), 180.0 );
  // sun disc
  col += uSunDisc * smoothstep( 0.99982, 0.99994, sd ) * above;
  // clouds
  if ( y > 0.004 ) {
    float tpl = ( 900.0 - min( cameraPosition.y, 700.0 ) ) / max( y, 0.03 );
    vec2 xz = cameraPosition.xz + rd.xz * tpl;
    float lo = 1.0 - uCloud.w;
    float c = cloudCover( xz );
    float det = texture2D( uNoiseTex, xz * uCloud.x * 9.0 + uCloud.yz * 3.0 ).b;
    float cov = smoothstep( lo - 0.12, lo + 0.22, c + ( det - 0.5 ) * 0.16 );
    if ( cov > 0.003 ) {
      float c2 = cloudCover( xz + uSunPos.xz * 320.0 + uMoonPos.xz * 0.0 );
      float sh = smoothstep( lo - 0.1, lo + 0.4, c2 );
      float thick = smoothstep( lo, lo + 0.45, c );
      vec3 cc = mix( uCloudLit, uCloudDark, clamp( sh * 0.75 + thick * 0.45, 0.0, 1.0 ) );
      cc += uGlow * pow( sd, 10.0 ) * ( 1.0 - thick ) * 0.8;
      float fade = smoothstep( 0.004, 0.11, y );
      col = mix( col, mix( uHorizon, cc, fade ), cov * mix( 0.55, 1.0, fade ) );
    }
  }
  gl_FragColor = vec4( col, 1.0 );
}`;

export class Atmosphere {
  constructor(scene, camera, renderer, world, opts = {}) {
    this.scene = scene; this.camera = camera; this.renderer = renderer; this.world = world;
    this.hour = opts.hour ?? 9.0;
    this.dayLength = opts.dayLength ?? 1800;     // real seconds per 24 game hours
    this.timeScale = 1;
    this.cloudCoverage = 0.45;                   // weather-driven
    this.overcast = 0;                           // 0..1 dims the sun
    this.fogMul = 1; this.fogTint = new THREE.Color(1, 1, 1);
    this._fogMulCur = 1; this._fogTintCur = new THREE.Color(1, 1, 1);
    this.sunPos = new THREE.Vector3(0, 1, 0);
    this.moonPos = new THREE.Vector3(0, -1, 0);
    this.lightDir = U.uSunDir.value;
    this.exposure = 1;
    this.night = 0;

    this.sun = new SunLight(0xffffff, 3);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.camera.near = 0.5;
    this.sun.shadow.camera.far = 150;
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.06;
    this.sun.shadow.radius = 2.2;
    scene.add(this.sun);
    this.hemi = new THREE.HemisphereLight(0xffffff, 0x888888, 1);
    scene.add(this.hemi);
    scene.fog = new THREE.Fog(0x000000, 1, 2);   // only switches USE_FOG on; real fog = globals.js

    this.skyUniforms = {
      uProjInv: { value: camera.projectionMatrixInverse }, uCamWorld: { value: camera.matrixWorld },
      uZenith: { value: col(0, 0, 0) }, uHorizon: { value: col(0, 0, 0) }, uGround: { value: col(0, 0, 0) },
      uSunPos: { value: this.sunPos }, uMoonPos: { value: this.moonPos },
      uSunDisc: { value: col(0, 0, 0) }, uGlow: { value: col(0, 0, 0) }, uMoonCol: { value: col(0.8, 0.86, 1.0) },
      uStars: { value: 0 }, uCloudLit: { value: col(1, 1, 1) }, uCloudDark: { value: col(0.5, 0.5, 0.5) },
      uNoiseTex: U.uNoiseTex, uCloud: U.uCloud, uTime: U.uTime,
    };
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);
    this.sky = new THREE.Mesh(geo, new THREE.ShaderMaterial({
      vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, uniforms: this.skyUniforms,
      depthWrite: false, depthTest: true, depthFunc: THREE.LessEqualDepth, fog: false,
    }));
    this.sky.frustumCulled = false;
    this.sky.renderOrder = 20;
    this.sky.matrixAutoUpdate = false;
    scene.add(this.sky);
    this._c = { zen: col(0, 0, 0), hor: col(0, 0, 0), sun: col(0, 0, 0), sky: col(0, 0, 0), gnd: col(0, 0, 0) };
    this._tmp = new THREE.Color();
    this.windOffset = new THREE.Vector2();
    this.update(0);
  }

  setShadowQuality(mapSize, distance, radius = 2.2) {
    const sh = this.sun.shadow;
    this.sun.castShadow = mapSize > 0;
    if (mapSize > 0 && sh.mapSize.x !== mapSize) {
      sh.mapSize.set(mapSize, mapSize);
      if (sh.map) { sh.map.dispose(); sh.map = null; }
    }
    sh.camera.far = distance;
    sh.radius = radius;
  }

  _blend(e) {
    const wDay = sstep(0.10, 0.38, e);
    const g = sstep(-0.02, 0.10, e);
    const wGold = g * (1 - wDay);
    const tw = sstep(-0.16, -0.02, e);
    const wTwi = tw * (1 - g);
    const wNight = 1 - tw;
    const W = [[KEY.day, wDay], [KEY.gold, wGold], [KEY.twi, wTwi], [KEY.night, wNight]];
    const c = this._c;
    for (const k of ['zen', 'hor', 'sun', 'sky', 'gnd']) c[k].setRGB(0, 0, 0);
    let sunI = 0, skyI = 0, expo = 0;
    for (const [K, w] of W) {
      if (w <= 0) continue;
      for (const k of ['zen', 'hor', 'sun', 'sky', 'gnd']) { c[k].r += K[k].r * w; c[k].g += K[k].g * w; c[k].b += K[k].b * w; }
      sunI += K.sunI * w; skyI += K.skyI * w; expo += K.expo * w;
    }
    return { sunI, skyI, expo, wNight, wDay, wTwi, wGold };
  }

  update(dt) {
    this.hour = (this.hour + dt * this.timeScale * 24 / this.dayLength) % 24;
    if (this.hour < 0) this.hour += 24;
    const a = (this.hour - 6) / 12 * Math.PI;
    const tilt = 0.62;
    // east = +X, south = +Z ; sun culminates toward the south
    this.sunPos.set(Math.cos(a), Math.sin(a) * Math.cos(tilt), Math.sin(a) * Math.sin(tilt)).normalize();
    const am = a + Math.PI;
    this.moonPos.set(Math.cos(am) * 0.9, Math.sin(am) * Math.cos(0.45) + 0.12, -Math.sin(am) * Math.sin(0.45) + 0.2).normalize();
    const e = this.sunPos.y;
    const b = this._blend(e);
    const c = this._c;
    this.night = b.wNight;
    // which body lights the world
    const useSun = e > -0.07;
    const dir = useSun ? this.sunPos : this.moonPos;
    this.lightDir.copy(dir);
    const minY = useSun ? 0.06 : 0.16;
    if (this.lightDir.y < minY) { this.lightDir.y = minY; this.lightDir.normalize(); }
    // intensity dips to zero across the sun/moon hand-over
    let lightI = b.sunI;
    if (useSun) lightI *= sstep(-0.07, 0.03, e) * (0.25 + 0.75 * sstep(0.0, 0.2, e)) + 0.0001;
    else lightI *= sstep(-0.07, -0.16, e) * (0.35 + 0.65 * sstep(-0.05, 0.15, this.moonPos.y));
    const oc = this.overcast;
    lightI *= 1 - 0.78 * oc;
    this.sun.position.copy(this.lightDir);
    this.sun.color.copy(c.sun);
    this.sun.intensity = lightI;
    this.sun.updateMatrixWorld();
    // overcast greys the sky
    const grey = this._tmp.setRGB(0.42, 0.45, 0.5).multiplyScalar(0.25 + 0.75 * (1 - b.wNight) * (0.3 + 0.7 * sstep(-0.1, 0.3, e)) + 0.02);
    c.zen.lerp(grey, oc * 0.85); c.hor.lerp(grey, oc * 0.8);
    this.hemi.color.copy(c.sky).lerp(grey, oc * 0.5);
    this.hemi.groundColor.copy(c.gnd);
    this.hemi.intensity = b.skyI * (1 - 0.25 * oc);
    // analytic auto-exposure: estimate the luminance of sunlit flat ground and adapt (partially) to it
    const Lg = 0.15 * (lightI * Math.max(this.lightDir.y, 0.05) + this.hemi.intensity * 0.9) / Math.PI;
    this.exposure = Math.pow(0.2 / Math.max(Lg, 0.004), 0.72) * (1 - 0.42 * b.wNight);

    const su = this.skyUniforms;
    su.uZenith.value.copy(c.zen); su.uHorizon.value.copy(c.hor);
    su.uGround.value.copy(c.hor).multiplyScalar(0.55);
    su.uSunDisc.value.copy(c.sun).multiplyScalar(60 * sstep(-0.03, 0.05, e) * (1 - oc));
    su.uGlow.value.copy(c.sun).multiplyScalar((0.35 + 0.9 * b.wGold + 1.2 * b.wTwi) * sstep(-0.2, 0.0, e) * (1 - 0.8 * oc));
    su.uStars.value = b.wNight * (1 - oc);
    su.uMoonCol.value.setRGB(0.75, 0.82, 1.0).multiplyScalar(0.35 + 0.9 * b.wNight);
    const amb = this._tmp.copy(c.sky).multiplyScalar(b.skyI * 0.42);
    su.uCloudLit.value.copy(c.sun).multiplyScalar(lightI * 0.27).add(amb);
    su.uCloudDark.value.copy(amb).multiplyScalar(0.55).lerp(grey, oc * 0.3);

    // fog
    this._fogMulCur += (this.fogMul - this._fogMulCur) * Math.min(dt * 0.5, 1);
    this._fogTintCur.lerp(this.fogTint, Math.min(dt * 0.5, 1));
    const morning = (this.hour > 4.5 && this.hour < 9.5) ? Math.sin((this.hour - 4.5) / 5 * Math.PI) : 0;
    const dens = 0.00042 * (1 + 1.6 * morning + 2.4 * oc + 0.5 * b.wNight) * this._fogMulCur;
    U.uFogParams.value.set(dens, 0.011, 0.0, 0.985);
    U.uFogColor.value.copy(c.hor).lerp(c.zen, 0.22).multiply(this._fogTintCur);
    const fs = U.uFogSun.value;
    const g = (0.25 + 0.6 * b.wGold + 0.5 * b.wTwi) * sstep(-0.12, 0.05, e) * (1 - oc);
    fs.set(c.sun.r * g, c.sun.g * g, c.sun.b * g, 7.0);
    // clouds drift with the wind
    const w = U.uWind.value;
    this.windOffset.x += w.x * dt * 0.00035 * (0.6 + w.z);
    this.windOffset.y += w.y * dt * 0.00035 * (0.6 + w.z);
    U.uCloud.value.set(0.00012, this.windOffset.x, this.windOffset.y, this.cloudCoverage);
    U.uCloudShadow.value = this.cloudShadows === false ? 0 : 0.6 * (1 - oc);
  }

  /** screen-space position of the visible sun (for god rays). Returns z < 0 when behind the camera. */
  sunScreen(out) {
    out.copy(this.sunPos).multiplyScalar(1000).add(this.camera.position).project(this.camera);
    const fwd = this._fwd || (this._fwd = new THREE.Vector3());
    this.camera.getWorldDirection(fwd);
    out.z = fwd.dot(this.sunPos);
    return out;
  }
}

// ---------------------------------------------------------------------------------------------
// Large-scale terrain shadows: for every 5 m texel, the altitude above which the sun is visible,
// ray-marched through the heightmap on the GPU, amortized over several frames.
const TS_FRAG = /* glsl */`
precision highp float;
precision highp usampler2D;
uniform highp usampler2D uHeightTex;
uniform vec4 uHInfo;
uniform vec3 uL;
in vec2 vUv;
out vec4 fragColor;
float H( vec2 p ) {
  ivec2 i = ivec2( clamp( ( p + ${WORLD_HALF.toFixed(1)} ) / uHInfo.z, vec2( 0.0 ), vec2( uHInfo.w - 1.0 ) ) );
  return float( texelFetch( uHeightTex, i, 0 ).r ) * uHInfo.y + uHInfo.x;
}
void main() {
  vec2 p = ( vUv - 0.5 ) * ${(WORLD_HALF * 2).toFixed(1)};
  float h0 = max( H( p ), 0.0 );
  float lxz = length( uL.xz );
  float alt = h0;
  if ( lxz > 0.02 ) {
    vec2 dir = uL.xz / lxz;
    float tanE = uL.y / lxz;
    float s = 5.0;
    for ( int k = 0; k < 44; k ++ ) {
      alt = max( alt, H( p + dir * s ) - s * tanE );
      s = s * 1.1 + 2.5;
    }
  }
  fragColor = vec4( alt, alt - h0, 0.0, 1.0 );
}`;

export class TerrainShadow {
  constructor(renderer, world, size = 1024) {
    this.renderer = renderer; this.size = size;
    const mk = () => {
      const rt = new THREE.WebGLRenderTarget(size, size, { format: THREE.RGFormat, type: THREE.HalfFloatType, depthBuffer: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false });
      rt.texture.wrapS = rt.texture.wrapT = THREE.ClampToEdgeWrapping;
      return rt;
    };
    this.front = mk(); this.back = mk();
    this.dir = new THREE.Vector3(0, -1, 0);
    this.jobDir = new THREE.Vector3();
    this.row = -1;
    this.strips = 8;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
    this.mat = new THREE.RawShaderMaterial({
      glslVersion: THREE.GLSL3, depthTest: false, depthWrite: false,
      vertexShader: 'in vec3 position; out vec2 vUv; void main(){ vUv = position.xy * 0.5 + 0.5; gl_Position = vec4( position.xy, 0.0, 1.0 ); }',
      fragmentShader: TS_FRAG,
      uniforms: { uHeightTex: { value: world.heightTex }, uHInfo: { value: world.heightInfo }, uL: { value: this.jobDir } },
    });
    this.mesh = new THREE.Mesh(geo, this.mat);
    this.mesh.frustumCulled = false;
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.first = true;
    U.uTerrainShadow.value = this.front.texture;
  }

  /** call once per frame with the current light direction */
  update(lightDir, enabled = true) {
    U.uShadowSoft.value.y = enabled ? 1 : 0;
    if (!enabled) return;
    if (this.row < 0) {
      if (!this.first && this.dir.dot(lightDir) > 0.99997) return;   // < ~0.45 degree
      this.jobDir.copy(lightDir);
      this.row = 0;
    }
    const r = this.renderer, rt = this.back;
    const prev = r.getRenderTarget();
    const n = this.first ? 1 : this.strips;
    const h = Math.ceil(this.size / n);
    rt.scissorTest = true;
    rt.scissor.set(0, this.row * h, this.size, h);
    r.setRenderTarget(rt);
    r.render(this.mesh, this.cam);
    r.setRenderTarget(prev);
    this.row++;
    if (this.row >= n) {
      this.row = -1; this.first = false;
      this.dir.copy(this.jobDir);
      const t = this.front; this.front = this.back; this.back = t;
      U.uTerrainShadow.value = this.front.texture;
      U.uShadowSoft.value.x = THREE.MathUtils.clamp(2.5 / Math.max(this.jobDir.y, 0.08), 3, 22);
    }
  }
}
