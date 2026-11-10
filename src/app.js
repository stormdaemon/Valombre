// Application: boot, state machine (title / creator / playing), frame loop, settings, saves, creator preview.
import * as THREE from 'three';
import { Engine } from './engine.js';
import { Settings, applySettings } from './core/settings.js';
import { Input } from './core/input.js';
import { Saves } from './core/saves.js';
import { bus } from './core/events.js';
import { Game, newPlayerData } from './game/game.js';
import { installHumanBuilder } from './game/character.js';
import { defaultAppearance, MORPH_FALLBACK } from './game/data/creator.js';
import { ORIGINS } from './game/data/rules.js';
import { ITEMS } from './game/data/items.js';
import { INTRO } from './game/data/story.js';
import { FallbackUI } from './ui_fallback.js';

export class App {
  constructor(canvas) {
    this.canvas = canvas;
    this.params = new URLSearchParams(location.search);
    this.state = 'boot';
    this.settings = new Settings();
    this.input = new Input(canvas, this.settings);
    this.saves = new Saves(this);
    this.engine = new Engine(canvas);
    this.audio = null;
    this.game = null;
    this.ui = null;
    this.creator = null;
    this.blocking = false;
    this.noLock = this.params.has('nolock');
    this._last = performance.now();
    this._titleA = 0;
    this._tmp = new THREE.Vector3();
  }

  get gpu() { return this.engine.pipeline.gpu; }
  sfx(name) { if (this.audio) this.audio.play(name); }
  perf() { const p = this.engine.pipeline; return { fps: Math.round(1000 / p.frameMs), ms: +p.frameMs.toFixed(1), calls: p.sceneCalls || 0, tris: p.sceneTris || 0, scale: p.opts.renderScale, res: [p.rw, p.rh] }; }

  setState(s) { const old = this.state; if (old === s) return; this.state = s; bus.emit('state', s, old); }

  async boot() {
    const loading = (p, t) => { if (this.ui) this.ui.setLoading(p, t); const f = document.getElementById('bootfill'), m = document.getElementById('bootmsg'); if (f) f.style.width = Math.round(p * 100) + '%'; if (m && t) m.textContent = t; };
    // UI first (it owns the loading screen); fall back to a minimal one if the full UI is not available
    try { const mod = await import('./ui/ui.js'); this.ui = new mod.UI(this); }
    catch (e) { console.warn('[app] full UI unavailable, using the fallback UI:', e && e.message); this.ui = new FallbackUI(this); }
    try { const mod = await import('./audio/audio.js'); this.audio = new mod.AudioEngine(); this.audio.init(); }
    catch (e) { console.warn('[app] audio unavailable', e); }
    loading(0.02, 'Lecture du monde');
    await this.engine.load((p, t) => loading(0.02 + p * 0.5, t));
    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.settings.applyPreset();
    this.game = new Game(this);
    await this.game.load((p, t) => loading(0.52 + p * 0.46, t));
    if (this.game.models.human) installHumanBuilder(this.game.models);
    this.applySettings();
    bus.on('settings', () => this.applySettings());
    bus.on('pointerlock', (locked) => { if (!locked && this.state === 'playing' && !this.blocking && !this.noLock && !this.input.usingPad) bus.emit('open', 'pause'); });
    this.canvas.addEventListener('mousedown', () => { if (this.state === 'playing' && !this.blocking && !this.noLock) this.input.requestLock(); });
    document.addEventListener('visibilitychange', () => { if (!this.audio) return; if (document.hidden && this.settings.get('muteOnBlur')) this.audio.suspend(); else this.audio.resume(); });
    window.addEventListener('beforeunload', () => { if (this.state === 'playing' && this.game.player && !this.game.player.dead && !this.game.boss) this.game.save(0); });
    // first launch: measure the machine once
    if (this.settings.firstRun || !this.settings.autoPreset) { loading(0.99, 'Mesure des performances'); await this.benchmark(); }
    loading(1, 'Prêt');
    const boot = document.getElementById('boot');
    if (boot) boot.style.display = 'none';
    this._enterTitle();
    requestAnimationFrame((t) => this.frame(t));
    return this;
  }

  resize() { this.engine.resize(window.innerWidth, window.innerHeight); }

  applySettings() {
    applySettings(this.settings, this);
    const helm = this.settings.get('showHelm');
    if (this._helm !== helm) { this._helm = helm; if (this.game && this.game.player && this.game.player.model) this.game.player.updateGear(); }
    const v = this.settings.values;
    if (this.game) {
      if (this.game.vfx.lights.length !== Number(v.lights)) this.game.vfx.setLightCount(Number(v.lights));
      this.game.vfx.density = { low: 0.45, medium: 0.75, high: 1 }[v.particles] ?? 1;
    }
  }

  // ------------------------------------------------------------------ benchmark
  async benchmark() {
    const e = this.engine, gl = e.renderer.getContext(), px = new Uint8Array(4);
    const cam = e.camera;
    const savePos = cam.position.clone(), saveQ = cam.quaternion.clone();
    const prev = { ...e.pipeline.opts }, prevAuto = e.pipeline.autoScale;
    e.pipeline.autoScale = false;
    e.setQuality({ shadows: 'high', view: 2, vegetation: 2, grass: 3 });
    e.pipeline.setOptions({ renderScale: 1, ao: 1, god: true, bloom: 0.55, fxaa: true, msaa: 0 });
    // a demanding but typical view: forest edge near the starting village
    cam.position.set(-640, e.world.height(-640, 700) + 2.2, 700);
    cam.lookAt(-760, e.world.height(-760, 640) + 4, 640);
    cam.updateMatrixWorld();
    const sync = () => { e.renderer.setRenderTarget(null); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); };
    for (let i = 0; i < 12; i++) { e.update(0.016); e.render(); await new Promise(r => setTimeout(r, 30)); }   // warm up: shaders, textures, vegetation cells
    const run = (k, n) => { e.render(); sync(); const t0 = performance.now(); for (let i = 0; i < n; i++) { for (let j = 0; j < k; j++) e.render(); sync(); } return (performance.now() - t0) / n; };
    const t1 = run(1, 5), t4 = run(4, 5);
    const ms = Math.max((t4 - t1) / 3, 0.5);
    // scale to the real resolution budget: the measure already ran at the current canvas size
    const fps = 1000 / ms;
    // measured with the 'high' settings at full resolution; 'ultra' costs ~10-15 % more (real frame loop: ultra
    // holds 60 fps at 1600x900 on a Vega 8 when this test gives ~74 fps), gameplay adds a few ms on top
    const preset = fps >= 62 ? 'ultra' : fps >= 45 ? 'high' : fps >= 30 ? 'medium' : 'low';
    this.settings.autoPreset = preset;
    this.settings.firstRun = false;
    if (this.settings.values.preset === 'auto') this.settings.applyPreset();
    this.settings.save();
    cam.position.copy(savePos); cam.quaternion.copy(saveQ);
    e.pipeline.setOptions(prev); e.pipeline.autoScale = prevAuto;
    this.applySettings();
    this.benchResult = { preset, fps: Math.round(fps), ms: +ms.toFixed(1) };
    return this.benchResult;
  }

  // ------------------------------------------------------------------ title
  _enterTitle() {
    const e = this.engine;
    this.setUiBlocking(true);
    e.atmo.hour = 17.35; e.atmo.timeScale = 0;
    e.atmo.cloudCoverage = 0.42; e.atmo.overcast = 0;
    this.game.cam.mode = 'none';
    this.setState('title');
    if (this.audio) { this.audio.setMusic('menu'); this.audio.setAmbience({ biome: 'meadow', hour: 17.3, rain: 0, wind: 0.3, water: 0, danger: 0 }); }
  }

  _titleCam(dt) {
    const cam = this.engine.camera, w = this.engine.world;
    this._titleA += dt * 0.012;
    const a = this._titleA + 2.4, cx = -150, cz = 1450, r = 210;
    const x = cx + Math.sin(a) * r, z = cz + Math.cos(a) * r;
    cam.position.set(x, Math.max(w.height(x, z) + 14, 52), z);
    cam.lookAt(cx, w.height(cx, cz) + 14, cz);
    if (cam.fov !== 50) { cam.fov = 50; cam.updateProjectionMatrix(); }
    if (this.audio) { cam.getWorldDirection(this._tmp); this.audio.setListener([cam.position.x, cam.position.y, cam.position.z], [this._tmp.x, this._tmp.y, this._tmp.z]); }
  }

  quitToTitle() {
    if (this.state === 'playing' && this.game.player && !this.game.player.dead && !this.game.boss) this.game.save(0);
    this._closeCreator();
    this.game.reset();
    this.engine.pipeline.fade = 0; this.engine.pipeline.desat = 0;
    this._enterTitle();
  }

  // ------------------------------------------------------------------ creator
  openCreator() {
    const g = this.game, e = this.engine, self = this;
    this._closeCreator();
    const man = g.models.humanManifest;
    const morphs = (man && man.morphs ? man.morphs : MORPH_FALLBACK).filter(m => m.category !== 'expression' && !['blink', 'mouth_open', 'smile', 'angry'].includes(m.name));
    const spot = g.content.shrines.s_hautefeuille || Object.values(g.content.shrines)[0];
    const base = new THREE.Vector3(spot.rest.x + 3.5, 0, spot.rest.z + 2.5);
    base.y = g.collision.ground(base.x, base.z);
    e.atmo.hour = 9.3; e.atmo.timeScale = 0;
    // the character faces the camera (which stays on the sun side, see _creatorCam); yaw = the player's extra rotation
    const faceYaw = 0;
    const C = this.creator = {
      morphs, appearance: defaultAppearance(), origin: ORIGINS[0].id, view: 'body', yaw: faceYaw, model: null, base,
      set(key, value) { C.appearance[key] = value; self._creatorApply(key); },
      setMorph(name, value) { C.appearance.morphs[name] = value; const h = C.model && C.model.inner.userData.human; if (h) h.setMorph(name, value); },
      setAll(a) { C.appearance = { ...defaultAppearance(), ...a, morphs: { ...(a.morphs || {}) } }; self._creatorBuild(); },
      setOrigin(id) { C.origin = id; self._creatorGear(); },
      setView(v) { C.view = v; },
      rotate(d) { C.yaw += d; },
      playVoice() { if (self.audio) self.audio.voice('attack', { pitch: C.appearance.voice || 1 }); },
    };
    this._creatorBuild();
    this.game.cam.mode = 'none';
    this.setState('creator');
    if (this.audio) this.audio.setMusic('creator');
  }

  _creatorBuild() {
    const C = this.creator, g = this.game;
    if (C.model) { g.scene.remove(C.model.root); C.model.dispose(); }
    const a = C.appearance;
    C.model = g.models.humanoid({ human: true, live: true, skin: a.skin, hair: a.hair, hairColor: a.hairColor, beard: a.beard, eyeColor: a.eyeColor, morphs: a.morphs, paint: a.paint, paintColor: a.paintColor, scar: a.scar, scale: a.height || 1 });
    C.model.root.position.copy(C.base);
    g.scene.add(C.model.root);
    C.model.animator.play('idle', 0.01);
    this._creatorGear();
  }

  _creatorApply(key) {
    const C = this.creator, a = C.appearance, h = C.model && C.model.inner.userData.human;
    if (!h) { this._creatorBuild(); return; }
    if (key === 'skin') h.setSkin(a.skin);
    else if (key === 'hair' || key === 'hairColor') { h.setHair(a.hair, a.hairColor); h.setBeard(a.beard); }
    else if (key === 'beard') h.setBeard(a.beard);
    else if (key === 'eyeColor') h.setEyes(a.eyeColor);
    else if (key === 'paint' || key === 'paintColor' || key === 'scar') h.setPaint(a.paint, a.paintColor, a.scar);
    else if (key === 'height') C.model.inner.scale.setScalar(a.height || 1);
  }

  _creatorGear() {
    const C = this.creator, o = ORIGINS.find(x => x.id === C.origin) || ORIGINS[0];
    if (!C.model) return;
    C.model.setWeapon(o.gear.weapon || null);
    const w = o.gear.weapon && ITEMS[o.gear.weapon];
    C.model.setShield(w && w.moveset === '2h' ? null : o.gear.offhand || null);
    const h = C.model.inner.userData.human;
    if (h) h.setOutfit({ head: null, chest: o.gear.chest, legs: o.gear.legs });
  }

  _creatorCam(dt) {
    const C = this.creator, cam = this.engine.camera, m = C.model;
    if (!m) return;
    m.animator.update(dt);
    const s = C.appearance.height || 1;
    const face = C.view === 'face';
    const dist = face ? 0.78 : 3.5, h = face ? 1.66 * s : 1.0 * s, look = face ? 1.655 * s : 0.98 * s;
    // camera stays on the sun side of the character; the character rotates
    const sun = this.engine.atmo.sunPos, cy = Math.atan2(sun.x, sun.z) + 0.45;
    m.root.rotation.y = cy + C.yaw;                 // facing the camera, plus the rotation chosen by the player
    // keep the character left of centre so that the UI columns do not hide it
    const tx = C.base.x + Math.sin(cy) * dist, tz = C.base.z + Math.cos(cy) * dist;
    this._tmp.set(tx, C.base.y + h, tz);
    const k = C._camInit ? 1 - Math.exp(-6 * dt) : 1;
    C._camInit = true;
    cam.position.lerp(this._tmp, k);
    this._look = this._look || new THREE.Vector3();
    this._look.lerp(this._tmp.set(C.base.x, C.base.y + look, C.base.z), k);
    cam.lookAt(this._look);
    const fov = face ? 26 : 34;
    if (Math.abs(cam.fov - fov) > 0.1) { cam.fov += (fov - cam.fov) * (k === 1 ? 1 : Math.min(dt * 6, 1)); cam.updateProjectionMatrix(); }
  }

  _closeCreator() {
    const C = this.creator;
    if (C && C.model) { this.game.scene.remove(C.model.root); C.model.dispose(); }
    this.creator = null;
  }

  // ------------------------------------------------------------------ start / load
  startNewGame({ name, origin, appearance }) {
    const a = appearance || (this.creator ? this.creator.appearance : defaultAppearance());
    const data = newPlayerData(name, origin, JSON.parse(JSON.stringify(a)));
    this._closeCreator();
    this._play(data, true);
    INTRO.forEach((text, i) => setTimeout(() => { if (this.state === 'playing') bus.emit('subtitle', { text, time: 8.5 }); }, 1200 + i * 9000));
    this.game.save(0);
  }

  continueGame() { const s = this.saves.latest(); if (s >= 0) this.loadSlot(s); }

  loadSlot(slot) {
    const d = this.saves.load(slot);
    if (!d) return false;
    this._closeCreator();
    this._play(d.player, false);
    return true;
  }

  saveSlot(slot) { const p = this.game && this.game.player; if (this.state !== 'playing' || !p || p.dead || this.game.boss || p.combatT > 0) return false; return this.game.save(slot); }

  _play(data, fresh) {
    const e = this.engine;
    e.atmo.timeScale = 1;
    e.pipeline.fade = 1; this.game._fadeIn = 1.4;
    this.game.start(data, fresh);
    this.setState('playing');
    this.setUiBlocking(false);
    this.applySettings();
  }

  setUiBlocking(b) {
    this.blocking = !!b;
    if (b) this.input.exitLock(); else if (this.state === 'playing' && !this.noLock) this.input.requestLock();
  }

  // ------------------------------------------------------------------ frame
  frame(now) {
    requestAnimationFrame((t) => this.frame(t));
    const cap = this.settings.get('targetFps');
    const dt = Math.min((now - this._last) / 1000, 0.1);
    this._last = now;
    const inp = this.input, e = this.engine;
    inp.gameEnabled = this.state === 'playing' && !this.blocking && (inp.locked || inp.usingPad || this.noLock);
    inp.update();
    try {
      if (this.state === 'playing') {
        if (!this.blocking || this.game.shrine || this.game.dialogue || this.game.shop || this.game.smith) this.game.update(this.blocking && !(this.game.shrine || this.game.dialogue) ? 0 : dt);
        else { this.game.cam.update(0); }
        e.update(this.blocking ? 0 : dt);
      } else if (this.state === 'title') { this._titleCam(dt); e.update(dt); if (this.audio) this.audio.update(dt); }
      else if (this.state === 'creator') { this._creatorCam(dt); e.update(dt); if (this.audio) this.audio.update(dt); }
      if (this.state === 'playing' && this.audio) this.audio.update(dt);
      e.render();
      if (this.ui) this.ui.update(dt);
    } catch (err) {
      if (!this._errShown) { this._errShown = true; console.error(err); window.__lastError = String(err && err.stack ? err.stack : err); }
    }
    inp.endFrame();
  }
}
