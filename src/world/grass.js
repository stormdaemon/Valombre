// GPU grass: one instanced tuft mesh, instances laid on a toroidal grid that follows the camera.
// Everything (placement, density, height, wind, fade) is computed in the vertex shader: zero CPU per frame.
import * as THREE from 'three';
import { U, patchMaterial, inject, WORLD_SIZE } from '../core/globals.js';
import { HEIGHT_GLSL } from './terrain.js';

function tuftGeometry() {
  // one tuft = 3 curved "hero" blades (3 triangles each) + 7 simple single-triangle blades
  const pos = [], tip = [], idx = [], nrm = [];
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  for (let k = 0; k < 10; k++) {
    const hero = k < 3;
    const yaw = rnd() * Math.PI * 2, rad = Math.sqrt(rnd()) * 0.21, pa = rnd() * Math.PI * 2;
    const ox = Math.cos(pa) * rad, oz = Math.sin(pa) * rad;
    const h = hero ? 0.8 + rnd() * 0.2 : 0.42 + rnd() * 0.42;
    const w = hero ? 0.034 + rnd() * 0.012 : 0.03 + rnd() * 0.014;
    const lean = 0.12 + rnd() * 0.42;
    const c = Math.cos(yaw), sn = Math.sin(yaw), base = pos.length / 3;
    const pts = hero ? [[-0.5, 0], [0.5, 0], [-0.34, 0.5], [0.34, 0.5], [0, 1]] : [[-0.5, 0], [0.5, 0], [0, 1]];
    for (const [x, y] of pts) {
      const lx = x * w, lz = y * y * lean * h, ly = y * h;
      pos.push(ox + lx * c + lz * sn, ly, oz - lx * sn + lz * c);
      tip.push(y); nrm.push(0, 1, 0);
    }
    if (hero) idx.push(base, base + 1, base + 2, base + 1, base + 3, base + 2, base + 2, base + 3, base + 4);
    else idx.push(base, base + 1, base + 2);
  }
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('aTip', new THREE.Float32BufferAttribute(tip, 1));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));   // dummy: keeps vNormal declared
  g.setIndex(idx);
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);
  return g;
}

export class Grass {
  constructor(world, opts = {}) {
    this.world = world;
    this.uniforms = {
      uGrid: { value: new THREE.Vector4(192, 0.45, 50, 0) },     // G, cell size, fade radius, -
      uCenter: { value: new THREE.Vector2() },
      uHeightTex: { value: world.heightTex }, uHInfo: { value: world.heightInfo },
      uVeg: { value: world.vegTex }, uSplat1G: { value: world.splat1Tex },
      uTerrNrmG: { value: world.nrmTex },
      uGrassCol: { value: new THREE.Color(0.165, 0.215, 0.062) },
      uNoiseG: U.uNoiseTex,
    };
    const mat = new THREE.MeshLambertMaterial({ color: 0xffffff, side: THREE.DoubleSide });
    mat.defines = { VAL_WORLD_SPACE: 1 };
    patchMaterial(mat, (sh) => {
      Object.assign(sh.uniforms, this.uniforms);
      sh.vertexShader = sh.vertexShader.replace('#include <common>', /* glsl */`
        #include <common>
        attribute float aTip;
        uniform vec4 uGrid;
        uniform vec2 uCenter;
        uniform sampler2D uVeg;
        uniform sampler2D uSplat1G;
        uniform sampler2D uTerrNrmG;
        uniform sampler2D uNoiseG;
        uniform vec3 uGrassCol;
        uniform float uTime;
        uniform vec4 uWind;
        uniform vec3 uPlayerPos;
        varying vec3 vGrassCol;
        varying float vTip;
        ${HEIGHT_GLSL}
        float gh( vec2 p ) { return fract( sin( dot( p, vec2( 127.1, 311.7 ) ) ) * 43758.5453 ); }
      `);
      sh.vertexShader = inject(sh.vertexShader, 'beginnormal_vertex', /* glsl */`
        float G = uGrid.x, cs = uGrid.y;
        vec2 cell = vec2( float( gl_InstanceID % int( G ) ), float( gl_InstanceID / int( G ) ) );
        vec2 gbase = floor( uCenter / cs );
        vec2 gid = gbase + mod( cell - gbase, G ) - G * 0.5;
        float r1 = gh( gid ), r2 = gh( gid + 37.3 ), r3 = gh( gid + 71.9 ), r4 = gh( gid * 1.37 + 5.1 );
        vec2 gxz = ( gid + 0.1 + 0.8 * vec2( r1, r2 ) ) * cs;
        vec2 guv = gxz * ${(1 / WORLD_SIZE).toFixed(10)} + 0.5;
        vec4 gveg = texture2D( uVeg, guv );
        vec4 gs1 = texture2D( uSplat1G, guv );
        vec4 gtn = texture2D( uTerrNrmG, guv );
        float gdist = distance( gxz, cameraPosition.xz );
        float glod = gdist / uGrid.z;
        float gkeep = ( 1.0 - 0.78 * smoothstep( 0.3, 0.85, glod ) ) * min( gveg.b * 1.25, 1.0 );
        float galive = smoothstep( 0.0, 0.14, gkeep - r3 ) * ( 1.0 - smoothstep( 0.8, 1.0, glod ) );
        vec3 objectNormal = vec3( gtn.r * 2.0 - 1.0, 0.0, gtn.g * 2.0 - 1.0 );
        objectNormal.y = sqrt( max( 1.0 - objectNormal.x * objectNormal.x - objectNormal.z * objectNormal.z, 0.05 ) );
        galive *= smoothstep( 0.55, 0.75, objectNormal.y );
      `);
      sh.vertexShader = inject(sh.vertexShader, 'begin_vertex', /* glsl */`
        vec4 gn = texture2D( uNoiseG, gxz * 0.0137 );
        float gmacro = gn.r * 0.55 + texture2D( uNoiseG, gxz * 0.0023 + 0.37 ).b * 0.45;
        float gpatch = gn.g;
        float gheight = ( 0.30 + 0.34 * r4 ) * ( 0.6 + 0.8 * gpatch ) * ( 1.0 + 1.1 * gs1.b + 0.2 * gs1.g ) * galive;
        float gwidth = 1.0 + 2.6 * smoothstep( 0.15, 0.85, glod );
        float ang = r1 * 6.2831853;
        float ca = cos( ang ), sa = sin( ang );
        vec3 lp = position;
        lp.xz = vec2( lp.x * ca + lp.z * sa, -lp.x * sa + lp.z * ca ) * gwidth;
        lp.y *= gheight;
        // wind: large gusts travelling with the wind + small flutter
        vec2 wdir = uWind.xy;
        float gust = texture2D( uNoiseG, gxz * 0.0045 - wdir * uTime * 0.04 ).r;
        float flut = sin( uTime * 3.1 + r2 * 6.28 + gxz.x * 0.7 ) * 0.5 + 0.5;
        float bend = ( 0.05 + 0.6 * gust * gust + 0.05 * flut ) * uWind.z * aTip * aTip * gheight * 1.5;
        lp.xz += wdir * bend;
        // the player pushes blades aside
        vec2 pd = gxz - uPlayerPos.xz;
        float pl = length( pd );
        float push = ( 1.0 - smoothstep( 0.25, 1.0, pl ) ) * aTip * 0.35 * step( abs( uPlayerPos.y - 0.0 ), 1e5 );
        lp.xz += pd / max( pl, 0.05 ) * push;
        lp.y -= ( bend * bend + push * push ) * 0.9;
        float gy = valHeight( gxz );
        vec3 transformed = vec3( gxz.x + lp.x, gy + lp.y - 0.03, gxz.y + lp.z );
        vec3 gc = uGrassCol * ( 0.74 + 0.52 * gmacro );
        gc = mix( gc, gc * vec3( 1.25, 1.08, 0.7 ), smoothstep( 0.45, 0.8, gpatch ) * 0.6 );   // dry patches
        gc = mix( gc, gc * vec3( 0.62, 0.74, 0.6 ), gs1.g );                 // forest: darker
        gc = mix( gc, gc * vec3( 1.05, 0.9, 0.55 ), gs1.b );                 // swamp: olive
        gc *= mix( 0.86, 1.18, r4 );
        vGrassCol = gc * mix( 0.42, 1.5, aTip ) + vec3( 0.06, 0.055, 0.0 ) * aTip * aTip * ( 0.3 + r2 );
        vTip = aTip;
      `);
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vGrassCol;\nvarying float vTip;');
      sh.fragmentShader = inject(sh.fragmentShader, 'map_fragment', 'diffuseColor.rgb = vGrassCol;');
      sh.fragmentShader = inject(sh.fragmentShader, 'normal_fragment_begin', 'float faceDirection = 1.0;\nvec3 normal = normalize( vNormal );\nvec3 nonPerturbedNormal = normal;');
      // translucency: grass glows when looking toward the sun
      sh.fragmentShader = inject(sh.fragmentShader, 'lights_fragment_end', /* glsl */`
        #include <lights_fragment_end>
        #if NUM_SUN_LIGHTS > 0
          vec3 gV = normalize( cameraPosition - vFogWorld );
          float gback = pow( max( dot( gV, -uSunDir ), 0.0 ), 3.0 ) * vTip;
          reflectedLight.directDiffuse += sunLights[ 0 ].color * vGrassCol * gback * 0.22 * valSunVis( vFogWorld, uSunDir );
        #endif
      `);
    }, 'grass');
    this.material = mat;
    this.geometry = tuftGeometry();
    this.mesh = new THREE.Mesh(this.geometry, mat);
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = false;
    this.mesh.receiveShadow = true;
    this.mesh.matrixAutoUpdate = false;
    this.mesh.renderOrder = 5;
    this._fwd = new THREE.Vector3();
    this.setQuality(opts.quality ?? 2);
  }

  /** 0 = off, 1 = low, 2 = medium, 3 = high, 4 = ultra */
  setQuality(q) {
    const P = [null, [96, 0.52, 31], [128, 0.46, 37], [176, 0.40, 44], [240, 0.35, 52]][q];
    this.mesh.visible = !!P;
    if (!P) return;
    this.G = P[0]; this.cell = P[1]; this.radius = P[2];
    this.uniforms.uGrid.value.set(P[0], P[1], P[2], 0);
    this.geometry.instanceCount = P[0] * P[0];
  }

  setBaseColor(r, g, b) { this.uniforms.uGrassCol.value.setRGB(r, g, b); }

  update(camera) {
    if (!this.mesh.visible) return;
    camera.getWorldDirection(this._fwd);
    const half = this.G * this.cell * 0.5;
    const off = Math.max(half - this.radius * 0.42, 0) * 0.9;
    const l = Math.hypot(this._fwd.x, this._fwd.z) || 1;
    this.uniforms.uCenter.value.set(camera.position.x + this._fwd.x / l * off, camera.position.z + this._fwd.z / l * off);
  }
}
