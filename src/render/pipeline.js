// Renderer + HDR post-processing chain tuned for integrated GPUs:
// scene (RGBA16F + depth) -> [SSAO half-res] -> [god rays quarter-res] -> [bloom dual-filter] ->
// composite (exposure, ACES, grading, vignette, grain) -> FXAA + sharpen + upscale to the canvas.
import * as THREE from 'three';

const VERT = 'in vec3 position; out vec2 vUv; void main(){ vUv = position.xy * 0.5 + 0.5; gl_Position = vec4( position.xy, 0.0, 1.0 ); }';
const HEAD = 'precision highp float;\nprecision highp sampler2D;\nin vec2 vUv;\nout vec4 fragColor;\n';

function mat(frag, uniforms, defines = {}) {
  return new THREE.RawShaderMaterial({
    glslVersion: THREE.GLSL3, vertexShader: VERT, fragmentShader: HEAD + frag, uniforms, defines,
    depthTest: false, depthWrite: false,
  });
}

const F_SSAO = /* glsl */`
uniform sampler2D tDepth;
uniform vec2 uNearFar;
uniform vec2 uTan;        // tan(fov/2) * aspect, tan(fov/2)
uniform vec2 uTexel;      // texel size of the depth buffer
uniform float uRadius;
uniform float uIntensity;
float linZ( float d ) { return uNearFar.x * uNearFar.y / ( uNearFar.y - d * ( uNearFar.y - uNearFar.x ) ); }
vec3 vpos( vec2 uv ) { float z = linZ( texture( tDepth, uv ).x ); return vec3( ( uv * 2.0 - 1.0 ) * uTan * z, z ); }
float ign( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }
void main() {
  float d = texture( tDepth, vUv ).x;
  if ( d >= 0.99995 ) { fragColor = vec4( 1.0, 1.0, 0.0, 1.0 ); return; }
  vec3 P = vpos( vUv );
  vec3 dx1 = vpos( vUv + vec2( uTexel.x, 0.0 ) ) - P, dx2 = P - vpos( vUv - vec2( uTexel.x, 0.0 ) );
  vec3 dy1 = vpos( vUv + vec2( 0.0, uTexel.y ) ) - P, dy2 = P - vpos( vUv - vec2( 0.0, uTexel.y ) );
  vec3 dx = abs( dx1.z ) < abs( dx2.z ) ? dx1 : dx2;
  vec3 dy = abs( dy1.z ) < abs( dy2.z ) ? dy1 : dy2;
  vec3 N = normalize( cross( dx, dy ) );
  if ( N.z > 0.0 ) N = -N;
  float fade = 1.0 - smoothstep( 90.0, 190.0, P.z );
  float ao = 1.0;
  if ( fade > 0.0 ) {
    float rad = uRadius * ( 0.35 + 0.65 * clamp( P.z / 12.0, 0.0, 1.0 ) );
    vec2 ruv = clamp( rad / ( P.z * uTan * 2.0 ), uTexel * 2.0, vec2( 0.09 ) );
    float ang = ign( gl_FragCoord.xy ) * 6.2831853;
    float occ = 0.0;
    for ( int i = 0; i < 8; i ++ ) {
      float fi = float( i );
      float a = ang + fi * 2.39996;
      float rr = sqrt( ( fi + 0.5 ) / 8.0 );
      vec3 Sp = vpos( vUv + vec2( cos( a ), sin( a ) ) * rr * ruv );
      vec3 v = Sp - P;
      float dd = dot( v, v );
      float nv = dot( N, v ) - 0.012 * P.z - 0.01;
      occ += max( nv, 0.0 ) / ( dd + 0.0025 ) * smoothstep( rad * rad * 2.2, rad * rad * 0.6, dd );
    }
    ao = clamp( 1.0 - occ * ( 2.0 * rad / 8.0 ) * uIntensity, 0.0, 1.0 );
    ao = mix( 1.0, ao, fade );
  }
  fragColor = vec4( ao, clamp( P.z / 256.0, 0.0, 1.0 ), 0.0, 1.0 );
}`;

const F_AOBLUR = /* glsl */`
uniform sampler2D tAO;
uniform vec2 uDir;
void main() {
  vec2 c = texture( tAO, vUv ).rg;
  float sum = c.r * 0.30, wsum = 0.30;
  for ( int i = -2; i <= 2; i ++ ) {
    if ( i == 0 ) continue;
    vec2 s = texture( tAO, vUv + uDir * float( i ) * 1.25 ).rg;
    float w = ( abs( float( i ) ) < 1.5 ? 0.22 : 0.13 ) * max( 0.0, 1.0 - abs( s.g - c.g ) * 256.0 / max( c.g * 256.0 * 0.06, 0.2 ) );
    sum += s.r * w; wsum += w;
  }
  fragColor = vec4( sum / wsum, c.g, 0.0, 1.0 );
}`;

const F_GOD = /* glsl */`
uniform sampler2D tDepth;
uniform vec2 uSun;
uniform float uAspect;
float ign( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }
void main() {
  const int N = 22;
  vec2 delta = ( uSun - vUv ) * ( 0.92 / float( N ) );
  vec2 uv = vUv + delta * ign( gl_FragCoord.xy );
  float acc = 0.0, decay = 1.0;
  for ( int i = 0; i < N; i ++ ) {
    uv += delta;
    vec2 q = clamp( uv, vec2( 0.001 ), vec2( 0.999 ) );
    float sky = step( 0.99995, texture( tDepth, q ).x );
    vec2 ds = ( q - uSun ) * vec2( uAspect, 1.0 );
    acc += sky * decay * smoothstep( 0.55, 0.0, length( ds ) );
    decay *= 0.965;
  }
  vec2 dv = ( vUv - uSun ) * vec2( uAspect, 1.0 );
  fragColor = vec4( acc / float( N ) * smoothstep( 1.25, 0.1, length( dv ) ), 0.0, 0.0, 1.0 );
}`;

const F_PREFILTER = /* glsl */`
uniform sampler2D tSrc;
uniform vec2 uTexel;
uniform float uThreshold;
void main() {
  vec3 c = 0.25 * ( texture( tSrc, vUv + uTexel * vec2( -1.0, -1.0 ) ).rgb + texture( tSrc, vUv + uTexel * vec2( 1.0, -1.0 ) ).rgb
                  + texture( tSrc, vUv + uTexel * vec2( -1.0, 1.0 ) ).rgb + texture( tSrc, vUv + uTexel * vec2( 1.0, 1.0 ) ).rgb );
  c = min( c, vec3( 48.0 ) );
  float br = max( c.r, max( c.g, c.b ) );
  float knee = uThreshold * 0.5;
  float soft = clamp( br - uThreshold + knee, 0.0, 2.0 * knee );
  soft = soft * soft / ( 4.0 * knee + 1e-4 );
  c *= max( soft, br - uThreshold ) / max( br, 1e-4 );
  fragColor = vec4( c, 1.0 );
}`;

const F_DOWN = /* glsl */`
uniform sampler2D tSrc;
uniform vec2 uTexel;
void main() {
  vec2 h = uTexel * 0.5;
  vec3 s = texture( tSrc, vUv ).rgb * 4.0;
  s += texture( tSrc, vUv - h ).rgb + texture( tSrc, vUv + h ).rgb;
  s += texture( tSrc, vUv + vec2( h.x, -h.y ) ).rgb + texture( tSrc, vUv - vec2( h.x, -h.y ) ).rgb;
  fragColor = vec4( s / 8.0, 1.0 );
}`;

const F_UP = /* glsl */`
uniform sampler2D tSrc;
uniform sampler2D tAdd;
uniform vec2 uTexel;
uniform float uSpread;
void main() {
  vec2 h = uTexel * 0.5 * uSpread;
  vec3 s = texture( tSrc, vUv + vec2( -h.x * 2.0, 0.0 ) ).rgb + texture( tSrc, vUv + vec2( h.x * 2.0, 0.0 ) ).rgb
         + texture( tSrc, vUv + vec2( 0.0, -h.y * 2.0 ) ).rgb + texture( tSrc, vUv + vec2( 0.0, h.y * 2.0 ) ).rgb;
  s += ( texture( tSrc, vUv + vec2( -h.x, h.y ) ).rgb + texture( tSrc, vUv + h ).rgb
       + texture( tSrc, vUv + vec2( h.x, -h.y ) ).rgb + texture( tSrc, vUv - h ).rgb ) * 2.0;
  fragColor = vec4( s / 12.0 + texture( tAdd, vUv ).rgb, 1.0 );
}`;

const F_COMPOSITE = /* glsl */`
uniform sampler2D tScene;
uniform sampler2D tBloom;
uniform sampler2D tAO;
uniform sampler2D tGod;
uniform float uBloom;
uniform float uAO;
uniform vec3 uGodCol;
uniform float uExposure;
uniform vec4 uGrade;      // contrast, saturation, vignette, grain
uniform vec3 uTint;       // white-balance style multiplier
uniform vec3 uShadowTint;
uniform float uChroma;
uniform float uTime;
uniform float uFade;      // 0 = normal, 1 = black
uniform vec4 uHurt;       // rgb + amount (damage / low-health edge glow)
uniform float uDesat;     // death desaturation
uniform float uFlash;     // lightning
vec3 RRTAndODTFit( vec3 v ) { vec3 a = v * ( v + 0.0245786 ) - 0.000090537; vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081; return a / b; }
vec3 aces( vec3 c ) {
  const mat3 mi = mat3( 0.59719, 0.07600, 0.02840, 0.35458, 0.90834, 0.13383, 0.04823, 0.01566, 0.83777 );
  const mat3 mo = mat3( 1.60475, -0.10208, -0.00327, -0.53108, 1.10813, -0.07276, -0.07367, -0.00605, 1.07602 );
  return clamp( mo * RRTAndODTFit( mi * c ), 0.0, 1.0 );
}
float hash12( vec2 p ) { vec3 p3 = fract( vec3( p.xyx ) * 0.1031 ); p3 += dot( p3, p3.yzx + 33.33 ); return fract( ( p3.x + p3.y ) * p3.z ); }
void main() {
  vec2 dir = vUv - 0.5;
  float r2 = dot( dir, dir );
  vec3 col;
  #ifdef CHROMA
    vec2 off = dir * r2 * uChroma;
    col = vec3( texture( tScene, vUv + off ).r, texture( tScene, vUv ).g, texture( tScene, vUv - off ).b );
  #else
    col = texture( tScene, vUv ).rgb;
  #endif
  #ifdef USE_AO
    col *= mix( 1.0, texture( tAO, vUv ).r, uAO );
  #endif
  #ifdef USE_BLOOM
    col += texture( tBloom, vUv ).rgb * uBloom;
  #endif
  #ifdef USE_GOD
    col += uGodCol * texture( tGod, vUv ).r;
  #endif
  col += vec3( 0.7, 0.78, 1.0 ) * uFlash;
  col *= uExposure * uTint;
  col = aces( col * 1.45 );
  col = pow( col, vec3( 0.86 ) );          // lift the toe: dark materials stay readable in shade
  // grading in display-referred space
  float l = dot( col, vec3( 0.2126, 0.7152, 0.0722 ) );
  col = mix( vec3( l ), col, uGrade.y * ( 1.0 - uDesat ) );
  col = mix( col, col * uShadowTint * 2.0, ( 1.0 - smoothstep( 0.0, 0.45, l ) ) * 0.5 );
  col = clamp( ( col - 0.5 ) * uGrade.x + 0.5, 0.0, 1.0 );
  col = pow( col, vec3( 1.0 / 2.2 ) );
  float vig = 1.0 - uGrade.z * smoothstep( 0.18, 0.95, r2 * 1.9 );
  col *= vig;
  col = mix( col, uHurt.rgb, uHurt.a * smoothstep( 0.08, 0.6, r2 * 1.6 ) );
  float n = hash12( gl_FragCoord.xy + fract( uTime ) * 91.7 ) - 0.5;
  col += n * ( uGrade.w * ( 1.0 - 0.6 * l ) + 1.0 / 255.0 );
  col *= 1.0 - uFade;
  fragColor = vec4( clamp( col, 0.0, 1.0 ), dot( col, vec3( 0.299, 0.587, 0.114 ) ) );
}`;

const F_FXAA = /* glsl */`
uniform sampler2D tSrc;
uniform vec2 uTexel;
uniform float uSharpen;
void main() {
  vec3 m = texture( tSrc, vUv ).rgb;
  #ifdef FXAA
    vec3 nw = texture( tSrc, vUv + uTexel * vec2( -0.5, -0.5 ) ).rgb;
    vec3 ne = texture( tSrc, vUv + uTexel * vec2( 0.5, -0.5 ) ).rgb;
    vec3 sw = texture( tSrc, vUv + uTexel * vec2( -0.5, 0.5 ) ).rgb;
    vec3 se = texture( tSrc, vUv + uTexel * vec2( 0.5, 0.5 ) ).rgb;
    const vec3 L = vec3( 0.299, 0.587, 0.114 );
    float lnw = dot( nw, L ), lne = dot( ne, L ), lsw = dot( sw, L ), lse = dot( se, L ), lm = dot( m, L );
    float lmin = min( lm, min( min( lnw, lne ), min( lsw, lse ) ) );
    float lmax = max( lm, max( max( lnw, lne ), max( lsw, lse ) ) );
    vec2 d = vec2( -( ( lnw + lne ) - ( lsw + lse ) ), ( lnw + lsw ) - ( lne + lse ) );
    float red = max( ( lnw + lne + lsw + lse ) * 0.03125, 0.0078125 );
    float rcp = 1.0 / ( min( abs( d.x ), abs( d.y ) ) + red );
    d = clamp( d * rcp, vec2( -8.0 ), vec2( 8.0 ) ) * uTexel;
    vec3 a = 0.5 * ( texture( tSrc, vUv + d * ( 1.0 / 3.0 - 0.5 ) ).rgb + texture( tSrc, vUv + d * ( 2.0 / 3.0 - 0.5 ) ).rgb );
    vec3 b = a * 0.5 + 0.25 * ( texture( tSrc, vUv + d * -0.5 ).rgb + texture( tSrc, vUv + d * 0.5 ).rgb );
    float lb = dot( b, L );
    vec3 c = ( lb < lmin || lb > lmax ) ? a : b;
    vec3 blur = ( nw + ne + sw + se ) * 0.25;
    c += ( c - blur ) * uSharpen;
  #else
    vec3 blur = 0.25 * ( texture( tSrc, vUv + uTexel * vec2( -0.75, -0.75 ) ).rgb + texture( tSrc, vUv + uTexel * vec2( 0.75, -0.75 ) ).rgb
                       + texture( tSrc, vUv + uTexel * vec2( -0.75, 0.75 ) ).rgb + texture( tSrc, vUv + uTexel * vec2( 0.75, 0.75 ) ).rgb );
    vec3 c = m + ( m - blur ) * uSharpen;
  #endif
  fragColor = vec4( clamp( c, 0.0, 1.0 ), 1.0 );
}`;

export class Pipeline {
  constructor(canvas) {
    this.canvas = canvas;
    const r = this.renderer = new THREE.WebGLRenderer({
      canvas, antialias: false, alpha: false, depth: false, stencil: false,
      powerPreference: 'high-performance', preserveDrawingBuffer: false,
    });
    r.setPixelRatio(1);
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.NoToneMapping;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFShadowMap;
    r.info.autoReset = false;
    r.sortObjects = true;
    this.gpu = this._gpuName();
    this.opts = { renderScale: 1, bloom: 0.55, ao: 1, aoIntensity: 1.0, god: true, fxaa: true, sharpen: 0.25, chroma: 0.0, vignette: 0.32, grain: 0.035, contrast: 1.05, saturation: 1.0, msaa: 0, gamma: 1.0 };
    this.fade = 0; this.hurt = new THREE.Vector4(0.5, 0, 0, 0); this.desat = 0;
    this.tint = new THREE.Vector3(1, 1, 1); this.shadowTint = new THREE.Vector3(0.5, 0.5, 0.5);
    this.w = 2; this.h = 2; this.rw = 2; this.rh = 2;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
    this.quad = new THREE.Mesh(g, null);
    this.quad.frustumCulled = false;
    this.ocam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.m = {
      ssao: mat(F_SSAO, { tDepth: { value: null }, uNearFar: { value: new THREE.Vector2() }, uTan: { value: new THREE.Vector2() }, uTexel: { value: new THREE.Vector2() }, uRadius: { value: 0.9 }, uIntensity: { value: 1 } }),
      aoBlur: mat(F_AOBLUR, { tAO: { value: null }, uDir: { value: new THREE.Vector2() } }),
      god: mat(F_GOD, { tDepth: { value: null }, uSun: { value: new THREE.Vector2() }, uAspect: { value: 1 } }),
      pre: mat(F_PREFILTER, { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uThreshold: { value: 1.05 } }),
      down: mat(F_DOWN, { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() } }),
      up: mat(F_UP, { tSrc: { value: null }, tAdd: { value: null }, uTexel: { value: new THREE.Vector2() }, uSpread: { value: 1.0 } }),
      comp: mat(F_COMPOSITE, {
        tScene: { value: null }, tBloom: { value: null }, tAO: { value: null }, tGod: { value: null },
        uBloom: { value: 0.5 }, uAO: { value: 1 }, uGodCol: { value: new THREE.Vector3() }, uExposure: { value: 1 },
        uGrade: { value: new THREE.Vector4(1.06, 1.08, 0.3, 0.03) }, uTint: { value: this.tint }, uShadowTint: { value: this.shadowTint },
        uChroma: { value: 0 }, uTime: { value: 0 }, uFade: { value: 0 }, uHurt: { value: this.hurt }, uDesat: { value: 0 }, uFlash: { value: 0 },
      }),
      fxaa: mat(F_FXAA, { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uSharpen: { value: 0.25 } }),
    };
    this.rt = {};
    this._key = '';
    this._sun = new THREE.Vector3();
    this.frameMs = 16; this._last = performance.now();
    this.autoScale = false; this.targetFps = 60; this._scaleTimer = 0; this.minScale = 0.55;
  }

  _gpuName() {
    try {
      const gl = this.renderer.getContext();
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    } catch (e) { return 'unknown'; }
  }

  setSize(w, h) {
    this.w = Math.max(2, Math.floor(w)); this.h = Math.max(2, Math.floor(h));
    this.renderer.setSize(this.w, this.h, false);
    this._alloc();
  }

  setOptions(o) { Object.assign(this.opts, o); this._alloc(); }

  _alloc() {
    const o = this.opts;
    const rw = Math.max(2, Math.round(this.w * o.renderScale / 2) * 2), rh = Math.max(2, Math.round(this.h * o.renderScale / 2) * 2);
    const key = [rw, rh, o.msaa, o.ao > 0, o.god, o.bloom > 0].join('|');
    if (key === this._key) return;
    this._key = key;
    for (const k in this.rt) { const t = this.rt[k]; if (Array.isArray(t)) t.forEach(x => x.dispose()); else t.dispose(); }
    this.rw = rw; this.rh = rh;
    const hdr = (w, h, depth = false, samples = 0) => {
      const t = new THREE.WebGLRenderTarget(w, h, { type: THREE.HalfFloatType, format: THREE.RGBAFormat, depthBuffer: depth, samples, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false });
      if (depth) { t.depthTexture = new THREE.DepthTexture(w, h); t.depthTexture.type = THREE.UnsignedIntType; t.depthTexture.minFilter = t.depthTexture.magFilter = THREE.NearestFilter; }
      return t;
    };
    const ldr = (w, h, fmt = THREE.RGBAFormat) => new THREE.WebGLRenderTarget(w, h, { type: THREE.UnsignedByteType, format: fmt, depthBuffer: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false });
    const rt = this.rt = {};
    rt.scene = hdr(rw, rh, true, o.msaa);
    rt.ldr = ldr(rw, rh);
    if (o.ao > 0) { rt.ao0 = ldr(rw >> 1, rh >> 1); rt.ao1 = ldr(rw >> 1, rh >> 1); }
    if (o.god) rt.god = ldr(rw >> 2, rh >> 2);
    if (o.bloom > 0) {
      rt.down = []; rt.up = [];
      let w = rw >> 1, h = rh >> 1;
      for (let i = 0; i < 5 && w > 8 && h > 8; i++) { rt.down.push(hdr(w, h)); if (i > 0) rt.up.push(hdr(rt.down[i - 1].width, rt.down[i - 1].height)); w >>= 1; h >>= 1; }
    }
    const c = this.m.comp;
    c.defines = {};
    if (o.ao > 0) c.defines.USE_AO = 1;
    if (o.bloom > 0) c.defines.USE_BLOOM = 1;
    if (o.god) c.defines.USE_GOD = 1;
    if (o.chroma > 0) c.defines.CHROMA = 1;
    c.needsUpdate = true;
    this.m.fxaa.defines = o.fxaa ? { FXAA: 1 } : {};
    this.m.fxaa.needsUpdate = true;
  }

  _pass(material, target) {
    this.quad.material = material;
    this.renderer.setRenderTarget(target);
    this.renderer.render(this.quad, this.ocam);
  }

  /** env: { exposure, sunScreen:Vector3 (ndc xy, z = facing), sunColor:Color, sunStrength } */
  render(scene, camera, env) {
    const r = this.renderer, o = this.opts, rt = this.rt, m = this.m;
    const now = performance.now();
    const ms = now - this._last; this._last = now;
    this.frameMs += (Math.min(ms, 100) - this.frameMs) * 0.08;
    r.info.reset();

    this._t('scene', () => { r.setRenderTarget(rt.scene); r.render(scene, camera); });
    this.sceneCalls = r.info.render.calls; this.sceneTris = r.info.render.triangles;
    this._pollProfile();

    const depth = rt.scene.depthTexture;
    if (o.ao > 0) this._t('ssao', () => {
      const u = m.ssao.uniforms;
      u.tDepth.value = depth; u.uNearFar.value.set(camera.near, camera.far);
      const tf = Math.tan(camera.fov * Math.PI / 360);
      u.uTan.value.set(tf * camera.aspect, tf); u.uTexel.value.set(1 / this.rw, 1 / this.rh);
      u.uRadius.value = 0.85; u.uIntensity.value = o.aoIntensity * (o.ao > 1 ? 1.25 : 1.0);
      this._pass(m.ssao, rt.ao0);
      m.aoBlur.uniforms.tAO.value = rt.ao0.texture; m.aoBlur.uniforms.uDir.value.set(2 / this.rw, 0);
      this._pass(m.aoBlur, rt.ao1);
      m.aoBlur.uniforms.tAO.value = rt.ao1.texture; m.aoBlur.uniforms.uDir.value.set(0, 2 / this.rh);
      this._pass(m.aoBlur, rt.ao0);
    });
    let god = 0;
    if (o.god && env.sunScreen) {
      const s = env.sunScreen;
      god = s.z > 0.05 ? Math.min((s.z - 0.05) * 2.5, 1) * (env.sunStrength ?? 1) : 0;
      if (god > 0.002) {
        m.god.uniforms.tDepth.value = depth; m.god.uniforms.uSun.value.set(s.x * 0.5 + 0.5, s.y * 0.5 + 0.5); m.god.uniforms.uAspect.value = camera.aspect;
        this._pass(m.god, rt.god);
      }
    }
    if (o.bloom > 0 && rt.down.length) this._t('bloom', () => {
      m.pre.uniforms.tSrc.value = rt.scene.texture; m.pre.uniforms.uTexel.value.set(1 / this.rw, 1 / this.rh);
      this._pass(m.pre, rt.down[0]);
      for (let i = 1; i < rt.down.length; i++) {
        m.down.uniforms.tSrc.value = rt.down[i - 1].texture; m.down.uniforms.uTexel.value.set(1 / rt.down[i - 1].width, 1 / rt.down[i - 1].height);
        this._pass(m.down, rt.down[i]);
      }
      let src = rt.down[rt.down.length - 1];
      for (let i = rt.up.length - 1; i >= 0; i--) {
        m.up.uniforms.tSrc.value = src.texture; m.up.uniforms.tAdd.value = rt.down[i].texture; m.up.uniforms.uTexel.value.set(1 / src.width, 1 / src.height);
        this._pass(m.up, rt.up[i]);
        src = rt.up[i];
      }
      this._bloomTex = src.texture;
    });
    const cu = m.comp.uniforms;
    cu.tScene.value = rt.scene.texture;
    cu.tBloom.value = this._bloomTex || null; cu.uBloom.value = o.bloom * 0.11;
    cu.tAO.value = rt.ao0 ? rt.ao0.texture : null; cu.uAO.value = 1;
    cu.tGod.value = rt.god ? rt.god.texture : null;
    if (env.sunColor) cu.uGodCol.value.set(env.sunColor.r, env.sunColor.g, env.sunColor.b).multiplyScalar(god * 0.55);
    else cu.uGodCol.value.set(0, 0, 0);
    cu.uExposure.value = (env.exposure ?? 1) * o.gamma;
    cu.uGrade.value.set(o.contrast, o.saturation, o.vignette, o.grain);
    cu.uChroma.value = o.chroma; cu.uTime.value = now * 0.001; cu.uFade.value = this.fade; cu.uDesat.value = this.desat; cu.uFlash.value = this.flash || 0;
    this._t('composite', () => this._pass(m.comp, rt.ldr));
    m.fxaa.uniforms.tSrc.value = rt.ldr.texture; m.fxaa.uniforms.uTexel.value.set(1 / this.rw, 1 / this.rh);
    m.fxaa.uniforms.uSharpen.value = o.sharpen * (o.renderScale < 0.99 ? 1.6 : 1.0);
    this._t('fxaa', () => this._pass(m.fxaa, null));

    if (this.autoScale) this._auto(ms);
  }

  // ---- GPU profiling (EXT_disjoint_timer_query_webgl2): await pipeline.profile(frames) -> { pass: ms }
  _t(label, fn) {
    const P = this._prof;
    if (!P) { fn(); return; }
    const gl = P.gl, q = gl.createQuery();
    gl.beginQuery(P.ext.TIME_ELAPSED_EXT, q);
    fn();
    gl.endQuery(P.ext.TIME_ELAPSED_EXT);
    P.pending.push([label, q]);
  }

  _pollProfile() {
    const P = this._prof;
    if (!P) return;
    const gl = P.gl;
    for (let i = P.pending.length - 1; i >= 0; i--) {
      const [label, q] = P.pending[i];
      if (!gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) continue;
      const ns = gl.getQueryParameter(q, gl.QUERY_RESULT);
      (P.acc[label] || (P.acc[label] = [])).push(ns / 1e6);
      gl.deleteQuery(q);
      P.pending.splice(i, 1);
    }
    if (--P.frames <= 0 && !P.pending.length) {
      const out = {};
      let total = 0;
      for (const k in P.acc) { const a = P.acc[k].slice().sort((x, y) => x - y); out[k] = +a[Math.floor(a.length / 2)].toFixed(2); total += out[k]; }
      out.total = +total.toFixed(2);
      this._prof = null;
      P.resolve(out);
    }
  }

  /** median GPU time per pass over `frames` rendered frames (requires the frame loop to be running) */
  profile(frames = 30) {
    const gl = this.renderer.getContext(), ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    if (!ext) return Promise.resolve(null);
    return new Promise((resolve) => { this._prof = { gl, ext, frames, pending: [], acc: {}, resolve }; });
  }

  // Dynamic resolution. The frame interval can never be shorter than the display refresh, so "there is
  // headroom" cannot be read from it: when the frame rate holds, the scale is raised one step as a probe and
  // taken back (with a growing delay before the next try) if the frame rate then drops.
  _auto(ms) {
    if (ms > 200 || (typeof document !== 'undefined' && document.hidden)) { this._scaleTimer = 0; this._accMs = 0; this._accN = 0; return; }   // hitch / background tab: not a GPU measure
    this._scaleTimer += ms; this._accMs = (this._accMs || 0) + ms; this._accN = (this._accN || 0) + 1;
    if (this._scaleTimer < 1000) return;
    const avg = this._accMs / this._accN, span = this._scaleTimer;
    this._scaleTimer = 0; this._accMs = 0; this._accN = 0;
    const target = 1000 / this.targetFps, o = this.opts, max = this.maxScale ?? 1;
    let s = o.renderScale;
    if (avg > target * 1.12) {
      if (this._probing) { this._probeFails = Math.min((this._probeFails || 0) + 1, 4); this._probing = false; }
      s -= avg > target * 1.45 ? 0.1 : 0.05;
      this._stable = 0;
    } else {
      this._stable = (this._stable || 0) + span;
      const wait = 3000 * Math.pow(2, this._probeFails || 0);          // 3 s, 6 s ... 48 s
      if (this._probing && this._stable >= 2500) { this._probing = false; this._probeFails = Math.max((this._probeFails || 0) - 1, 0); }
      if (s < max - 1e-3 && this._stable >= wait && avg < target * 1.04) { s += 0.05; this._probing = true; this._stable = 0; }
    }
    s = Math.min(max, Math.max(this.minScale, Math.round(s * 20) / 20));
    if (s !== o.renderScale) { o.renderScale = s; this._alloc(); }
  }
}
