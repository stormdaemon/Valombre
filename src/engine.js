// Engine: owns the renderer pipeline, the scene and the world rendering systems.
import * as THREE from 'three';
import { U } from './core/globals.js';
import { Pipeline } from './render/pipeline.js';
import { WorldData } from './world/worlddata.js';
import { Terrain, loadTerrainLayers } from './world/terrain.js';
import { Atmosphere, TerrainShadow } from './world/sky.js';
import { Water } from './world/water.js';
import { Grass } from './world/grass.js';
import { Vegetation } from './world/vegetation.js';
import { MU, setEnvMap } from './render/materials.js';
import { loadTexture, makeNoiseTexture, makeWaterNormalTexture } from './core/assets.js';

export class Engine {
  constructor(canvas) {
    this.canvas = canvas;
    this.pipeline = new Pipeline(canvas);
    this.renderer = this.pipeline.renderer;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(60, 16 / 9, 0.3, 9000);
    this.camera.position.set(-150, 40, 1500);
    this.time = 0;
    this.systems = [];          // objects with update(dt, engine)
    this._sunScreen = new THREE.Vector3();
    this.env = { exposure: 1, sunScreen: this._sunScreen, sunColor: new THREE.Color(), sunStrength: 1 };
    this.quality = {};
  }

  async load(progress = () => {}) {
    const maxAniso = this.renderer.capabilities.getMaxAnisotropy();
    this.world = await new WorldData().load((p) => progress(p * 0.4, 'Lecture du monde'));
    const [layers, noise, waterN] = await Promise.all([
      loadTerrainLayers(1024, Math.min(4, maxAniso)),
      loadTexture('assets/textures/fx_noise.png', { mips: true }),
      loadTexture('assets/textures/water_n.png', { mips: true }),
    ]);
    progress(0.7, 'Textures du terrain');
    U.uNoiseTex.value = noise || makeNoiseTexture(256);
    this.terrain = new Terrain(this.world, layers);
    this.scene.add(this.terrain.group);
    this.atmo = new Atmosphere(this.scene, this.camera, this.renderer, this.world);
    this.terrainShadow = new TerrainShadow(this.renderer, this.world, 1024);
    this.water = new Water(this.world, this.atmo, waterN || makeWaterNormalTexture(256));
    this.scene.add(this.water.group);
    this.grass = new Grass(this.world, { quality: 2 });
    this.scene.add(this.grass.mesh);
    progress(0.8, 'Forêts et rochers');
    this.vegetation = new Vegetation(this.world, this.atmo);
    await this.vegetation.load();
    this.scene.add(this.vegetation.group);
    this._buildEnv();
    progress(1, 'Prêt');
    return this;
  }

  /** q: { shadows, terrainShadows, cloudShadows, view 0-3, vegetation 0-3, grass 0-4, lights, particles, fov } */
  setQuality(q) {
    Object.assign(this.quality, q);
    const Q = this.quality;
    if (this.atmo) {
      const sh = { off: [0, 60], low: [1024, 60], medium: [1536, 85], high: [2048, 115], ultra: [3072, 160] }[Q.shadows] || [2048, 115];
      this.atmo.setShadowQuality(sh[0], sh[1]);
      this.atmo.cloudShadows = Q.cloudShadows !== false;
    }
    if (this.terrain && Q.view != null) {
      this.terrain.setRange([100, 130, 170, 220][Q.view]);
      this.terrain.uniforms.uTerrOpt.value.z = Q.view >= 1 ? 1 : 0;
      this.camera.far = [5500, 7000, 9000, 12000][Q.view];
    }
    if (this.grass && Q.grass != null && Q.grass !== this._grassQ) { this._grassQ = Q.grass; this.grass.setQuality(Q.grass); }
    if (this.vegetation && Q.vegetation != null && Q.vegetation !== this._vegQ) { this._vegQ = Q.vegetation; this.vegetation.setQuality(Q.vegetation); }
    if (Q.fov) this.camera.fov = Q.fov;
    this.camera.updateProjectionMatrix();
  }

  /** small sky-only scene captured into a PMREM cube: reflections for metal, ice, glass */
  _buildEnv() {
    const su = this.atmo.skyUniforms;
    this.pmrem = new THREE.PMREMGenerator(this.renderer);
    this.envScene = new THREE.Scene();
    const mat = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { uZenith: su.uZenith, uHorizon: su.uHorizon, uSunPos: su.uSunPos, uGlow: su.uGlow, uGnd: { value: new THREE.Color() } },
      vertexShader: 'varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }',
      fragmentShader: `uniform vec3 uZenith; uniform vec3 uHorizon; uniform vec3 uSunPos; uniform vec3 uGlow; uniform vec3 uGnd; varying vec3 vDir;
        void main(){ vec3 rd = normalize( vDir ); float t = pow( 1.0 - clamp( rd.y, 0.0, 1.0 ), 3.2 ); vec3 c = mix( uZenith, uHorizon, t );
        c = mix( c, uGnd, smoothstep( 0.02, -0.2, rd.y ) ); float sd = max( dot( rd, uSunPos ), 0.0 );
        c += uGlow * ( pow( sd, 5.0 ) * 0.25 + pow( sd, 60.0 ) * 1.5 ); gl_FragColor = vec4( c, 1.0 ); }`,
    });
    this.envMat = mat;
    this.envScene.add(new THREE.Mesh(new THREE.SphereGeometry(10, 24, 12), mat));
    this._envHour = -99; this._envT = 0;
    this._updateEnv(0, true);
  }

  _updateEnv(dt, force) {
    this._envT += dt;
    const h = this.atmo.hour;
    if (!force && (this._envT < 4 || Math.abs(h - this._envHour) < 0.12)) return;
    this._envT = 0; this._envHour = h;
    this.envMat.uniforms.uGnd.value.copy(this.atmo.hemi.groundColor).multiplyScalar(this.atmo.hemi.intensity * 0.22);
    const prevRT = this.renderer.getRenderTarget();
    const rt = this.pmrem.fromScene(this.envScene, 0, 0.1, 100, { size: 64 });
    this.renderer.setRenderTarget(prevRT);
    setEnvMap(rt.texture);
    if (this._envRT) this._envRT.dispose();
    this._envRT = rt;
  }

  resize(w, h) {
    this.pipeline.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  update(dt) {
    this.time += dt;
    U.uTime.value = this.time;
    this.atmo.update(dt);
    if (this.pmrem) this._updateEnv(dt, false);
    for (const s of this.systems) s.update(dt, this);
  }

  render() {
    const cam = this.camera;
    cam.updateMatrixWorld();
    this.terrain.update(cam);
    this.water.update(cam);
    this.grass.update(cam);
    this.vegetation.update(cam);
    MU.uNight.value = this.atmo.night;
    this.terrainShadow.update(this.atmo.lightDir, this.quality.terrainShadows !== false);
    // cheaper presets refresh the cascaded shadow map every 2nd / 3rd frame
    const every = { low: 3, medium: 2 }[this.quality.shadows] || 1;
    const sh = this.atmo.sun.shadow;
    this._frame = (this._frame || 0) + 1;
    sh.autoUpdate = every === 1;
    if (every > 1 && this._frame % every === 0) sh.needsUpdate = true;
    this.atmo.sunScreen(this._sunScreen);
    this.env.exposure = this.atmo.exposure;
    this.env.sunColor.copy(this.atmo.sun.color).multiplyScalar(Math.min(this.atmo.sun.intensity / 3.5, 1));
    this.env.sunStrength = Math.max(0, Math.min(1, (this.atmo.sunPos.y + 0.08) * 6)) * (1 - this.atmo.overcast);
    this.pipeline.render(this.scene, cam, this.env);
  }
}
