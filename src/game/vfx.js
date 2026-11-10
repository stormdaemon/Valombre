// Visual effects: CPU-simulated instanced particles (additive + alpha), fire emitters, weapon trails,
// ground telegraphs and a small pool of dynamic point lights.
import * as THREE from 'three';
import { U, FOG_FUNC } from '../core/globals.js';

const P_VERT = /* glsl */`
attribute vec3 aPos;
attribute vec4 aData;   // size, alpha, kind, stretch
attribute vec3 aCol;
attribute vec3 aVel;
varying vec2 vUv;
varying vec4 vCol;
varying vec3 vWorld;
varying float vKind;
void main() {
  vec4 mv = viewMatrix * vec4( aPos, 1.0 );
  vec2 off = position.xy * aData.x;
  if ( aData.w > 0.0 ) {
    // stretch along the screen-space velocity (sparks, rain)
    vec3 vv = ( viewMatrix * vec4( aVel, 0.0 ) ).xyz;
    vec2 d = normalize( vv.xy + vec2( 1e-5 ) );
    float len = 1.0 + length( vv.xy ) * aData.w;
    off = d * position.y * aData.x * len + vec2( -d.y, d.x ) * position.x * aData.x;
  }
  mv.xy += off;
  vUv = position.xy * 2.0;
  vCol = vec4( aCol, aData.y );
  vKind = aData.z;
  vWorld = aPos;
  gl_Position = projectionMatrix * mv;
}`;
const P_FRAG = /* glsl */`
varying vec2 vUv;
varying vec4 vCol;
varying vec3 vWorld;
varying float vKind;
${FOG_FUNC}
void main() {
  float d = length( vUv );
  if ( d > 1.0 ) discard;
  float soft = 1.0 - d;
  float a = vKind < 0.5 ? soft * soft : smoothstep( 0.0, 0.55, soft );
  vec3 c = vCol.rgb;
  #ifdef ALPHA_MODE
    c = valFog( c, vWorld );
    gl_FragColor = vec4( c, a * vCol.a );
  #else
    float f = exp( -length( vWorld - cameraPosition ) * uFogParams.x * 1.5 );
    gl_FragColor = vec4( c * a * vCol.a * f, 1.0 );
  #endif
}`;

class ParticleSet {
  constructor(cap, additive) {
    this.cap = cap; this.n = 0;
    this.p = new Float32Array(cap * 3); this.v = new Float32Array(cap * 3);
    this.life = new Float32Array(cap); this.max = new Float32Array(cap);
    this.s0 = new Float32Array(cap); this.s1 = new Float32Array(cap);
    this.col = new Float32Array(cap * 3); this.alpha = new Float32Array(cap);
    this.drag = new Float32Array(cap); this.grav = new Float32Array(cap);
    this.kind = new Float32Array(cap); this.stretch = new Float32Array(cap);
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0], 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    this.aPos = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3);
    this.aData = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4);
    this.aCol = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3);
    this.aVel = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3);
    for (const a of [this.aPos, this.aData, this.aCol, this.aVel]) a.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('aPos', this.aPos); g.setAttribute('aData', this.aData); g.setAttribute('aCol', this.aCol); g.setAttribute('aVel', this.aVel);
    g.instanceCount = 0;
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);
    const m = new THREE.ShaderMaterial({
      vertexShader: P_VERT, fragmentShader: P_FRAG, uniforms: { ...U }, defines: additive ? {} : { ALPHA_MODE: 1 },
      transparent: true, depthWrite: false, fog: false,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    this.mesh = new THREE.Mesh(g, m);
    this.mesh.frustumCulled = false; this.mesh.matrixAutoUpdate = false; this.mesh.renderOrder = additive ? 41 : 40;
  }

  add(x, y, z, vx, vy, vz, life, s0, s1, r, g, b, alpha, drag, grav, kind = 0, stretch = 0) {
    if (this.n >= this.cap) return;
    const i = this.n++;
    this.p[i * 3] = x; this.p[i * 3 + 1] = y; this.p[i * 3 + 2] = z;
    this.v[i * 3] = vx; this.v[i * 3 + 1] = vy; this.v[i * 3 + 2] = vz;
    this.life[i] = life; this.max[i] = life; this.s0[i] = s0; this.s1[i] = s1;
    this.col[i * 3] = r; this.col[i * 3 + 1] = g; this.col[i * 3 + 2] = b; this.alpha[i] = alpha;
    this.drag[i] = drag; this.grav[i] = grav; this.kind[i] = kind; this.stretch[i] = stretch;
  }

  update(dt) {
    const P = this.aPos.array, D = this.aData.array, C = this.aCol.array, V = this.aVel.array;
    let n = this.n;
    for (let i = 0; i < n; i++) {
      this.life[i] -= dt;
      if (this.life[i] <= 0) {
        // swap-remove
        const j = --n;
        if (i !== j) {
          for (let k = 0; k < 3; k++) { this.p[i * 3 + k] = this.p[j * 3 + k]; this.v[i * 3 + k] = this.v[j * 3 + k]; this.col[i * 3 + k] = this.col[j * 3 + k]; }
          this.life[i] = this.life[j]; this.max[i] = this.max[j]; this.s0[i] = this.s0[j]; this.s1[i] = this.s1[j]; this.alpha[i] = this.alpha[j];
          this.drag[i] = this.drag[j]; this.grav[i] = this.grav[j]; this.kind[i] = this.kind[j]; this.stretch[i] = this.stretch[j];
        }
        i--; continue;
      }
      const dr = Math.exp(-this.drag[i] * dt);
      this.v[i * 3] *= dr; this.v[i * 3 + 1] = this.v[i * 3 + 1] * dr - this.grav[i] * dt; this.v[i * 3 + 2] *= dr;
      this.p[i * 3] += this.v[i * 3] * dt; this.p[i * 3 + 1] += this.v[i * 3 + 1] * dt; this.p[i * 3 + 2] += this.v[i * 3 + 2] * dt;
      const t = 1 - this.life[i] / this.max[i];
      P[i * 3] = this.p[i * 3]; P[i * 3 + 1] = this.p[i * 3 + 1]; P[i * 3 + 2] = this.p[i * 3 + 2];
      V[i * 3] = this.v[i * 3]; V[i * 3 + 1] = this.v[i * 3 + 1]; V[i * 3 + 2] = this.v[i * 3 + 2];
      D[i * 4] = this.s0[i] + (this.s1[i] - this.s0[i]) * t;
      D[i * 4 + 1] = this.alpha[i] * (t < 0.12 ? t / 0.12 : 1 - (t - 0.12) / 0.88);
      D[i * 4 + 2] = this.kind[i]; D[i * 4 + 3] = this.stretch[i];
      C[i * 3] = this.col[i * 3]; C[i * 3 + 1] = this.col[i * 3 + 1]; C[i * 3 + 2] = this.col[i * 3 + 2];
    }
    this.n = n;
    this.mesh.geometry.instanceCount = n;
    for (const a of [this.aPos, this.aData, this.aCol, this.aVel]) { a.clearUpdateRanges(); a.addUpdateRange(0, n * a.itemSize); a.needsUpdate = true; }
  }
}

const rnd = (a = 1, b) => (b === undefined ? Math.random() * a : a + Math.random() * (b - a));
const sph = (out, sp, up = 0) => { const t = Math.random() * 6.283, z = Math.random() * 2 - 1, r = Math.sqrt(1 - z * z); out[0] = Math.cos(t) * r * sp; out[1] = Math.abs(z) * sp + up; out[2] = Math.sin(t) * r * sp; return out; };
const _d = [0, 0, 0];

const TRAIL_N = 20;

export class VFX {
  constructor(game) {
    this.game = game;
    this.group = new THREE.Group();
    this.add = new ParticleSet(3000, true);
    this.alp = new ParticleSet(2000, false);
    this.group.add(this.alp.mesh, this.add.mesh);
    this.emitters = [];
    this.trails = [];
    this.rings = [];
    this.lightReq = [];
    this.lights = [];
    this.density = 1;
    this._ringGeo = new THREE.RingGeometry(0.86, 1.0, 48).rotateX(-Math.PI / 2);
    this._discGeo = new THREE.CircleGeometry(1.0, 40).rotateX(-Math.PI / 2);
    this.setLightCount(4);
  }

  setLightCount(n) {
    for (const l of this.lights) this.game.scene.remove(l);
    this.lights = [];
    for (let i = 0; i < n; i++) { const l = new THREE.PointLight(0xffaa55, 0, 14, 2); l.castShadow = false; this.game.scene.add(l); this.lights.push(l); }
  }

  // ------------------------------------------------------------------ bursts
  burst(kind, pos, scale = 1, color = null) {
    const x = pos.x, y = pos.y + (kind === 'slam' || kind === 'dust' ? 0.15 : 1.0 * scale), z = pos.z;
    const A = this.add, B = this.alp, n = (k) => Math.max(1, Math.round(k * this.density));
    switch (kind) {
      case 'blood': for (let i = 0; i < n(12); i++) { sph(_d, rnd(1.5, 4.5), 1); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.3, 0.6), 0.07, 0.03, 0.32, 0.02, 0.02, 0.95, 1.5, 11, 1); } break;
      case 'ichor': for (let i = 0; i < n(12); i++) { sph(_d, rnd(1.5, 4.5), 1); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.3, 0.6), 0.08, 0.03, 0.25, 0.4, 0.08, 0.95, 1.5, 11, 1); } break;
      case 'bone': for (let i = 0; i < n(10); i++) { sph(_d, rnd(1.5, 4), 1); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.4, 0.7), 0.06, 0.04, 0.75, 0.72, 0.6, 1, 1, 10, 1); } break;
      case 'stone': for (let i = 0; i < n(10); i++) { sph(_d, rnd(1.5, 4), 1); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.4, 0.7), 0.09, 0.05, 0.3, 0.29, 0.28, 1, 1, 10, 1); } // fallthrough
      case 'spark': for (let i = 0; i < n(14); i++) { sph(_d, rnd(2.5, 7), 0.5); A.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.18, 0.42), 0.035, 0.01, 2.2, 1.3, 0.5, 1, 2, 9, 1, 0.045); } break;
      case 'parry': for (let i = 0; i < n(26); i++) { sph(_d, rnd(3, 9), 0.5); A.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.2, 0.45), 0.04, 0.01, 1.6, 2.0, 2.6, 1, 2.5, 6, 1, 0.05); } A.add(x, y, z, 0, 0, 0, 0.16, 0.3, 1.5, 1.4, 1.7, 2.2, 0.9, 0, 0); break;
      case 'crit': for (let i = 0; i < n(18); i++) { sph(_d, rnd(3, 8), 0.5); A.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.2, 0.4), 0.04, 0.01, 2.6, 2.0, 0.6, 1, 2.5, 6, 1, 0.05); } A.add(x, y, z, 0, 0, 0, 0.14, 0.3, 1.2, 2.2, 1.7, 0.6, 0.8, 0, 0); break;
      case 'dust': for (let i = 0; i < n(7); i++) { sph(_d, rnd(0.4, 1.4), 0.2); B.add(x + rnd(-0.3, 0.3), y, z + rnd(-0.3, 0.3), _d[0], _d[1] * 0.5 + 0.3, _d[2], rnd(0.6, 1.1), 0.25 * scale, 0.9 * scale, 0.42, 0.37, 0.3, 0.32, 1.5, -0.2, 0); } break;
      case 'slam': {
        const k = n(22);
        for (let i = 0; i < k; i++) { const a = i / k * 6.283, sp = rnd(3, 5.5) * scale * 0.5; B.add(x + Math.cos(a) * scale * 0.5, y, z + Math.sin(a) * scale * 0.5, Math.cos(a) * sp, rnd(0.6, 1.8), Math.sin(a) * sp, rnd(0.7, 1.2), 0.5, 1.6 * Math.min(scale, 3) * 0.6, 0.4, 0.36, 0.3, 0.42, 2.2, -0.3, 0); }
        for (let i = 0; i < n(12); i++) { sph(_d, rnd(2, 6), 2); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.5, 0.9), 0.1, 0.05, 0.25, 0.23, 0.2, 1, 0.8, 12, 1); }
        break;
      }
      case 'heal': for (let i = 0; i < n(18); i++) { const a = rnd(6.283), r = rnd(0.2, 0.6); A.add(x + Math.cos(a) * r, y - 0.8 + rnd(0.6), z + Math.sin(a) * r, 0, rnd(0.8, 2), 0, rnd(0.6, 1.1), 0.09, 0.02, 0.5, 1.3, 0.45, 0.9, 0.5, 0); } break;
      case 'levelup': for (let i = 0; i < n(46); i++) { const a = rnd(6.283), r = rnd(0.2, 0.9); A.add(x + Math.cos(a) * r, y - 0.9, z + Math.sin(a) * r, Math.cos(a) * 0.5, rnd(1.5, 4.5), Math.sin(a) * 0.5, rnd(0.8, 1.6), 0.1, 0.02, 2.0, 1.5, 0.5, 1, 0.8, 0); } break;
      case 'fire': for (let i = 0; i < n(22); i++) { sph(_d, rnd(1, 4) * scale, 1); A.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.3, 0.7), 0.4 * scale, 0.05, 2.4, 0.9, 0.2, 0.9, 2, -2); } for (let i = 0; i < n(6); i++) { sph(_d, 1.2, 0.6); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.7, 1.3), 0.4 * scale, 1.3 * scale, 0.08, 0.07, 0.07, 0.4, 1, -0.8); } break;
      case 'ice': for (let i = 0; i < n(22); i++) { sph(_d, rnd(1.5, 5) * scale, 0.6); A.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.3, 0.7), 0.12 * scale, 0.02, 0.6, 1.3, 2.2, 0.9, 2.5, 3, 1, 0.03); } A.add(x, y, z, 0, 0, 0, 0.25, 0.4, 2.2 * scale, 0.5, 0.9, 1.6, 0.6, 0, 0); break;
      case 'poison': for (let i = 0; i < n(14); i++) { sph(_d, rnd(0.6, 2.2), 0.4); B.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.6, 1.1), 0.25 * scale, 0.9 * scale, 0.25, 0.5, 0.1, 0.5, 1.5, -0.3); } break;
      case 'magic': { const c = color || [0.6, 1.2, 2.2]; for (let i = 0; i < n(20); i++) { sph(_d, rnd(1.5, 5) * scale, 0.4); A.add(x, y, z, _d[0], _d[1], _d[2], rnd(0.3, 0.7), 0.1 * scale, 0.02, c[0], c[1], c[2], 1, 2.5, 0, 1, 0.03); } A.add(x, y, z, 0, 0, 0, 0.22, 0.3, 1.8 * scale, c[0], c[1], c[2], 0.7, 0, 0); break; }
      case 'death': for (let i = 0; i < n(26); i++) { sph(_d, rnd(0.4, 1.6), 0.3); B.add(x + rnd(-0.4, 0.4) * scale, y - 0.6 + rnd(1.2) * scale, z + rnd(-0.4, 0.4) * scale, _d[0], _d[1] + 0.4, _d[2], rnd(0.9, 1.8), 0.3 * scale, 1.0 * scale, 0.06, 0.06, 0.08, 0.5, 1, -0.6); } for (let i = 0; i < n(16); i++) { sph(_d, rnd(0.5, 1.5), 0.5); A.add(x + rnd(-0.4, 0.4) * scale, y - 0.5 + rnd(1.0) * scale, z + rnd(-0.4, 0.4) * scale, _d[0], _d[1] + 0.8, _d[2], rnd(0.8, 1.6), 0.05, 0.01, 0.9, 1.4, 2.0, 1, 0.6, -0.5); } break;
      case 'pickup': for (let i = 0; i < n(10); i++) { sph(_d, rnd(0.5, 1.6), 0.8); A.add(x, y - 0.6, z, _d[0], _d[1], _d[2], rnd(0.4, 0.8), 0.06, 0.01, 2.0, 1.6, 0.6, 1, 1.5, 1); } break;
      case 'shrine': for (let i = 0; i < n(60); i++) { const a = rnd(6.283), r = rnd(0.2, 2.2); A.add(x + Math.cos(a) * r, y - 0.8, z + Math.sin(a) * r, 0, rnd(1, 4), 0, rnd(1, 2.2), 0.09, 0.02, 2.4, 1.1, 0.3, 1, 0.6, -0.4); } break;
      case 'splash': for (let i = 0; i < n(12); i++) { sph(_d, rnd(1, 3), 1.5); B.add(x, y - 0.9, z, _d[0], _d[1], _d[2], rnd(0.4, 0.7), 0.08, 0.04, 0.8, 0.9, 1.0, 0.6, 0.5, 9, 1); } break;
    }
  }

  /** single puff used every frame by projectiles and continuous effects */
  puff(kind, x, y, z, scale = 1) {
    const A = this.add, B = this.alp;
    if (kind === 'fire') { A.add(x + rnd(-0.1, 0.1), y + rnd(-0.1, 0.1), z + rnd(-0.1, 0.1), rnd(-0.3, 0.3), rnd(0.2, 0.9), rnd(-0.3, 0.3), rnd(0.25, 0.5), 0.5 * scale, 0.06, 2.6, 0.95, 0.2, 0.85, 1, -1.5); }
    else if (kind === 'venom') { A.add(x, y, z, rnd(-0.3, 0.3), rnd(-0.2, 0.3), rnd(-0.3, 0.3), rnd(0.25, 0.5), 0.35 * scale, 0.05, 0.5, 1.6, 0.2, 0.85, 1, 1); }
    else if (kind === 'frost' || kind === 'ice') { A.add(x, y, z, rnd(-0.3, 0.3), rnd(-0.2, 0.3), rnd(-0.3, 0.3), rnd(0.25, 0.5), 0.4 * scale, 0.05, 0.5, 1.2, 2.2, 0.85, 1, 0.5); }
    else if (kind === 'dawn') { A.add(x, y, z, rnd(-0.3, 0.3), rnd(-0.2, 0.3), rnd(-0.3, 0.3), rnd(0.3, 0.55), 0.5 * scale, 0.05, 2.4, 2.0, 1.1, 0.9, 1, 0); }
    else if (kind === 'meteor') { A.add(x, y, z, rnd(-0.4, 0.4), rnd(0.2, 1.2), rnd(-0.4, 0.4), rnd(0.3, 0.6), 0.9 * scale, 0.1, 2.8, 0.8, 0.15, 0.9, 1, -1); B.add(x, y, z, rnd(-0.3, 0.3), rnd(0.5, 1.2), rnd(-0.3, 0.3), rnd(0.6, 1.1), 0.5, 1.4, 0.07, 0.06, 0.06, 0.35, 1, -0.5); }
    else if (kind === 'smoke') { B.add(x + rnd(-0.15, 0.15), y, z + rnd(-0.15, 0.15), rnd(-0.2, 0.2) + U.uWind.value.x * 0.5, rnd(0.6, 1.2), rnd(-0.2, 0.2) + U.uWind.value.y * 0.5, rnd(1.6, 3), 0.3 * scale, 1.6 * scale, 0.1, 0.1, 0.11, 0.3, 0.4, -0.25); }
    else if (kind === 'ember') { A.add(x + rnd(-0.2, 0.2), y, z + rnd(-0.2, 0.2), rnd(-0.5, 0.5) + U.uWind.value.x, rnd(0.8, 2.4), rnd(-0.5, 0.5) + U.uWind.value.y, rnd(0.8, 1.8), 0.035, 0.01, 2.6, 1.0, 0.25, 1, 0.5, -0.3); }
    else if (kind === 'glow') { A.add(x, y, z, 0, 0, 0, 0.12, scale, scale * 0.9, 0.8, 1.3, 1.9, 0.5, 0, 0); }
    else if (kind === 'crystal') { A.add(x + rnd(-0.6, 0.6) * scale, y + rnd(1.5) * scale, z + rnd(-0.6, 0.6) * scale, 0, rnd(0.1, 0.5), 0, rnd(1, 2.2), 0.05, 0.01, 0.6, 1.4, 2.0, 0.9, 0.2, 0); }
  }

  // ------------------------------------------------------------------ emitters (fires, braziers, smoke, crystals)
  addEmitter(kind, pos, scale = 1) { const e = { kind, pos: pos.clone(), scale, acc: Math.random(), on: true }; this.emitters.push(e); return e; }

  // ------------------------------------------------------------------ lights
  /** request a dynamic light for this frame */
  light(x, y, z, r, g, b, intensity, radius = 12) { this.lightReq.push(x, y, z, r, g, b, intensity, radius); }

  // ------------------------------------------------------------------ weapon trails
  trail(actor, duration) {
    const sock = actor.model && actor.model.sockets.weaponR;
    if (!sock) return;
    let t = this.trails.find(x => !x.active);
    if (!t) {
      if (this.trails.length >= 6) return;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(TRAIL_N * 2 * 3), 3));
      g.setAttribute('aAge', new THREE.BufferAttribute(new Float32Array(TRAIL_N * 2), 1));
      const idx = [];
      for (let i = 0; i < TRAIL_N - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
      g.setIndex(idx);
      g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);
      const m = new THREE.ShaderMaterial({
        vertexShader: 'attribute float aAge; varying float vAge; varying float vSide; void main(){ vAge = aAge; vSide = mod( float( gl_VertexID ), 2.0 ); gl_Position = projectionMatrix * viewMatrix * vec4( position, 1.0 ); }',
        fragmentShader: 'uniform vec3 uColor; varying float vAge; varying float vSide; void main(){ float a = ( 1.0 - vAge ) * ( 0.25 + 0.75 * vSide ); gl_FragColor = vec4( uColor * a * a * 1.6, 1.0 ); }',
        uniforms: { uColor: { value: new THREE.Color(0.9, 0.95, 1.0) } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
      });
      const mesh = new THREE.Mesh(g, m);
      mesh.frustumCulled = false; mesh.renderOrder = 42;
      this.group.add(mesh);
      t = { mesh, pts: [], active: false };
      this.trails.push(t);
    }
    t.active = true; t.actor = actor; t.sock = sock; t.time = duration; t.pts.length = 0; t.fade = 0.22;
    t.len = (actor.st && actor.st.weapon ? actor.st.weapon.reach : 1.3) - 0.35; t.base = 0.25;
    const gi = actor.st && actor.st.weapon ? this.game.models.gearInfo(actor.st.weapon.model) : null;
    if (gi && gi.blade) { t.base = gi.blade[0]; t.len = gi.blade[1]; }
    t.mesh.visible = true;
  }

  // ------------------------------------------------------------------ ground telegraphs
  telegraph(x, y, z, radius, time, color = 0xff3a1a) {
    const m = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false });
    const ring = new THREE.Mesh(this._ringGeo, m);
    const fill = new THREE.Mesh(this._discGeo, m.clone());
    ring.position.set(x, y + 0.12, z); fill.position.set(x, y + 0.1, z);
    ring.scale.setScalar(radius); fill.scale.setScalar(0.01);
    ring.renderOrder = fill.renderOrder = 39;
    this.group.add(ring, fill);
    this.rings.push({ ring, fill, t: 0, time, radius });
  }

  update(dt, camera) {
    const cx = camera.position.x, cy = camera.position.y, cz = camera.position.z;
    // emitters
    for (const e of this.emitters) {
      if (!e.on) continue;
      const dx = e.pos.x - cx, dz = e.pos.z - cz, d2 = dx * dx + dz * dz;
      if (d2 > 90 * 90) continue;
      const near = d2 < 45 * 45;
      const s = e.scale;
      if (e.kind === 'fire' || e.kind === 'brazier' || e.kind === 'torch' || e.kind === 'forge') {
        e.acc += dt * (near ? 26 : 9) * this.density;
        while (e.acc >= 1) { e.acc -= 1; this.puff('fire', e.pos.x + rnd(-0.12, 0.12) * s, e.pos.y + 0.05, e.pos.z + rnd(-0.12, 0.12) * s, s * 0.8); if (Math.random() < 0.1) this.puff('ember', e.pos.x, e.pos.y + 0.3, e.pos.z); if (near && Math.random() < 0.08) this.puff('smoke', e.pos.x, e.pos.y + 0.7 * s, e.pos.z, s); }
        const fl = 0.8 + 0.2 * Math.sin(U.uTime.value * 11 + e.pos.x) + 0.12 * Math.sin(U.uTime.value * 23.7 + e.pos.z);
        this.light(e.pos.x, e.pos.y + 0.6, e.pos.z, 1.0, 0.52, 0.2, 7.5 * s * fl, 11 + 5 * s);
      } else if (e.kind === 'smoke') {
        e.acc += dt * 5 * this.density;
        while (e.acc >= 1) { e.acc -= 1; this.puff('smoke', e.pos.x, e.pos.y, e.pos.z, s * 1.2); }
      } else if (e.kind === 'crystal') {
        e.acc += dt * 5 * this.density;
        while (e.acc >= 1) { e.acc -= 1; this.puff('crystal', e.pos.x, e.pos.y, e.pos.z, s); }
        this.light(e.pos.x, e.pos.y + 0.8 * s, e.pos.z, 0.35, 0.75, 1.0, 5 * s, 10 + 4 * s);
      } else if (e.kind === 'glow') {
        this.light(e.pos.x, e.pos.y, e.pos.z, 1.0, 0.62, 0.3, 3.5 * s * this.game.nightFactor, 9);
      }
    }
    this.add.update(dt); this.alp.update(dt);
    // trails
    for (const t of this.trails) {
      if (!t.active) continue;
      t.time -= dt;
      if (t.time > 0 && t.sock) {
        t.sock.updateWorldMatrix(true, false);
        const e = t.sock.matrixWorld.elements;
        const ax = e[4], ay = e[5], az = e[6], l = Math.hypot(ax, ay, az) || 1;
        const bx = e[12], by = e[13], bz = e[14];
        t.pts.unshift([bx + ax / l * t.base, by + ay / l * t.base, bz + az / l * t.base, bx + ax / l * t.len, by + ay / l * t.len, bz + az / l * t.len, 0]);
        if (t.pts.length > TRAIL_N) t.pts.length = TRAIL_N;
      }
      const P = t.mesh.geometry.attributes.position, A = t.mesh.geometry.attributes.aAge;
      let alive = false;
      for (let i = 0; i < TRAIL_N; i++) {
        const q = t.pts[Math.min(i, t.pts.length - 1)];
        if (!q) break;
        if (i < t.pts.length) q[6] += dt / t.fade;
        const age = i < t.pts.length ? Math.min(q[6], 1) : 1;
        if (age < 1) alive = true;
        P.setXYZ(i * 2, q[0], q[1], q[2]); P.setXYZ(i * 2 + 1, q[3], q[4], q[5]);
        A.setX(i * 2, age); A.setX(i * 2 + 1, age);
      }
      P.needsUpdate = true; A.needsUpdate = true;
      if (t.time <= 0 && !alive) { t.active = false; t.mesh.visible = false; }
    }
    // telegraphs
    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i];
      r.t += dt;
      const u = Math.min(r.t / r.time, 1);
      r.ring.material.opacity = 0.35 + 0.45 * u;
      r.fill.material.opacity = 0.12 + 0.2 * u;
      r.fill.scale.setScalar(Math.max(r.radius * u, 0.01));
      if (r.t > r.time + 0.12) { this.group.remove(r.ring, r.fill); r.ring.material.dispose(); r.fill.material.dispose(); this.rings.splice(i, 1); }
    }
    // assign the pooled lights to the best requests
    const R = this.lightReq, n = R.length / 8, L = this.lights;
    const best = [];
    for (let i = 0; i < n; i++) {
      const dx = R[i * 8] - cx, dy = R[i * 8 + 1] - cy, dz = R[i * 8 + 2] - cz;
      best.push([R[i * 8 + 6] / (dx * dx + dy * dy + dz * dz + 25), i]);
    }
    best.sort((a, b) => b[0] - a[0]);
    for (let k = 0; k < L.length; k++) {
      const l = L[k];
      if (k < best.length) {
        const i = best[k][1];
        l.position.set(R[i * 8], R[i * 8 + 1], R[i * 8 + 2]);
        l.color.setRGB(R[i * 8 + 3], R[i * 8 + 4], R[i * 8 + 5]);
        l.intensity = R[i * 8 + 6]; l.distance = R[i * 8 + 7];
      } else l.intensity = 0;
    }
    R.length = 0;
  }
}
