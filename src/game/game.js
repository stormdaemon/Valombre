// Game: owns the simulation (player, enemies, NPCs, projectiles, interactions, quests, bosses, saving).
import * as THREE from 'three';
import { bus } from '../core/events.js';
import { U } from '../core/globals.js';
import { hash2, mulberry32, clamp } from '../core/rng.js';
import { CollisionWorld } from './collision.js';
import { Structures } from '../world/structures.js';
import { ModelFactory } from './models.js';
import { VFX } from './vfx.js';
import { FollowCamera } from './camera.js';
import { Player, newPlayerData } from './player.js';
import { Enemy } from './enemy.js';
import { Actor } from './actor.js';
import { Quests } from './quests.js';
import { buildContent } from './content.js';
import { ENEMIES, BOSSES, SPAWN_TABLE } from './data/enemies.js';
import { ITEMS, UPGRADE_COST } from './data/items.js';
import { SKILLS, REGIONS, DIFFICULTY } from './data/rules.js';
import { NPCS, CODEX, QUESTS } from './data/story.js';
import { BIOME_KEYS } from '../world/worlddata.js';

const _v = new THREE.Vector3(), _v2 = new THREE.Vector3();
const SPAWN_CELL = 120;
const CREATURE_CODEX = { wolf: 'c_wolf', dire_wolf: 'c_wolf', snow_wolf: 'c_wolf', bandit: 'c_bandit', bandit_shield: 'c_bandit', bandit_brute: 'c_bandit', spider: 'c_spider', spider_spitter: 'c_spider', drowned: 'c_drowned', skeleton: 'c_skeleton', wraith: 'c_wraith', troll: 'c_troll', cultist: 'c_cultist', cultist_blade: 'c_cultist', ash_golem: 'c_golem', hollow_knight: 'c_hollow', hollow_greatsword: 'c_hollow' };
const BOSS_CODEX = { wolf: 'p_crocbleme', spider: 'p_arakha', knight: 'p_malgrin', colossus: 'p_colosse', priestess: 'p_ysolde', king: 'aldric' };
const SHARD_OF = { spider: 'shard_spider', knight: 'shard_knight', colossus: 'shard_colossus', priestess: 'shard_priestess' };

class Npc extends Actor {
  constructor(game, id, def) { super(game); this.id = id; this.def = def; this.team = 'npc'; this.radius = 0.4; this.baseYaw = 0; }
  update(dt, near) {
    const p = this.game.player;
    if (near && p && this.distTo(p) < 5) this.turnToward(this.angleTo(p), 4, dt); else this.turnToward(this.baseYaw, 2, dt);
    this.syncModel();
    if (near) this.anim.update(dt);
  }
}

export class Game {
  constructor(app) {
    this.app = app; this.engine = app.engine; this.scene = app.engine.scene; this.world = app.engine.world;
    this.input = app.input; this.settings = app.settings; this.audio = app.audio;
    this.vegetation = app.engine.vegetation;
    this.collision = new CollisionWorld(this.world);
    this.structures = new Structures(app.engine, this.collision);
    this.models = new ModelFactory();
    this.vfx = new VFX(this);
    this.cam = new FollowCamera(app.engine.camera, this);
    this.scene.add(this.structures.group, this.vfx.group);
    this.player = null;
    this.quests = new Quests(this);
    this.enemies = []; this.npcs = []; this.projectiles = []; this.hazards = []; this.loot = [];
    this.interactables = []; this.focus = null;
    this.tokens = 0; this.maxTokens = 2;
    this.playerControl = true; this.hitStopT = 0; this.nightFactor = 0;
    this.boss = null; this.bossRing = null;
    this.swing = 0;
    this.activeGroups = new Map();     // key -> [enemies]
    this.riverCells = new Map();
    this.region = { id: 'meadow', name: REGIONS.meadow.name };
    this.shrine = null; this.shop = null; this.smith = null; this.dialogue = null;
    this.canFastTravel = false;
    this.time = 0; this.saveT = 0; this.musicT = 0; this.spawnT = 0; this.deathT = -1;
    this.loops = [];
    this._scr = new THREE.Vector3();
    this.weather = { kind: 'clear', t: 120, rain: 0, target: { cover: 0.42, overcast: 0, rain: 0, wind: 1 } };
  }

  // ------------------------------------------------------------------ loading
  async load(progress = () => {}) {
    progress(0.05, 'Personnages et créatures');
    await this.models.load();
    progress(0.4, 'Villages et ruines');
    this.content = await buildContent(this);
    progress(0.9, 'Mise en place');
    this._buildRiver();
    for (const e of this.content.emitters) {
      const em = this.vfx.addEmitter(e.kind, e.pos, e.scale);
      if (this.audio && (e.kind === 'fire' || e.kind === 'forge' || e.kind === 'torch')) this.loops.push(this.audio.startLoop(e.kind === 'forge' ? 'forge' : e.kind === 'torch' ? 'torch' : 'fire', { pos: [e.pos.x, e.pos.y, e.pos.z], volume: 0.8 }));
      else if (this.audio && e.kind === 'crystal') this.loops.push(this.audio.startLoop('crystal_hum', { pos: [e.pos.x, e.pos.y, e.pos.z], volume: 0.6 }));
      e.handle = em;
    }
    // shrine fires exist only once the shrine has been lit
    for (const id in this.content.shrines) { const s = this.content.shrines[id]; s.emitter = this.vfx.addEmitter('fire', s.fire, 1.1); s.emitter.on = false; }
    if (this.content.iceLake) this._buildIce(this.content.iceLake);
    if (this.content.gate) this._buildGateBarrier(this.content.gate);
    progress(1, 'Prêt');
  }

  _buildRiver() {
    const r = this.world.river;
    if (!r) return;
    const hw = r.width * 0.5 + 3, pts = r.points;
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1], n = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 3);
      for (let k = 0; k <= n; k++) {
        const t = k / n, x = a[0] + (b[0] - a[0]) * t, z = a[1] + (b[1] - a[1]) * t, y = a[2] + (b[2] - a[2]) * t;
        for (let dx = -hw; dx <= hw; dx += 3) for (let dz = -hw; dz <= hw; dz += 3) {
          if (dx * dx + dz * dz > hw * hw) continue;
          const key = Math.floor((x + dx) / 4) * 8192 + Math.floor((z + dz) / 4);
          const prev = this.riverCells.get(key);
          if (prev === undefined || y > prev) this.riverCells.set(key, y);
        }
      }
    }
  }

  _buildIce(l) {
    const m = new THREE.MeshStandardMaterial({ color: 0x9fc8e6, roughness: 0.08, metalness: 0.0, transparent: true, opacity: 0.86 });
    const mesh = new THREE.Mesh(new THREE.CircleGeometry(l.r, 48).rotateX(-Math.PI / 2), m);
    mesh.position.set(l.x, l.y + 0.06, l.z); mesh.receiveShadow = true;
    this.scene.add(mesh);
  }

  _buildGateBarrier(gt) {
    const mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
      uniforms: { uTime: U.uTime, uAlpha: { value: 1 } },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }',
      fragmentShader: 'uniform float uTime; uniform float uAlpha; varying vec2 vUv; void main(){ float w = sin( vUv.y * 24.0 - uTime * 2.0 + sin( vUv.x * 9.0 + uTime ) * 2.0 ) * 0.5 + 0.5; float e = smoothstep( 0.0, 0.2, vUv.y ) * smoothstep( 1.0, 0.6, vUv.y ); gl_FragColor = vec4( vec3( 0.5, 0.85, 1.0 ) * ( 0.35 + 0.65 * w ) * e * uAlpha * 1.4, 1.0 ); }',
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(gt.width + 1, 5.5), mat);
    mesh.position.set(gt.x, this.world.height(gt.x, gt.z) + 2.6, gt.z);
    this.scene.add(mesh);
    this.gateBarrier = { mesh, mat, box: this.collision.addBox(gt.x, gt.z, gt.width * 0.5 + 0.6, 0.6, 0, -50, 500, 'barrier') };
  }

  // ------------------------------------------------------------------ world helpers
  waterLevel(x, z) {
    const r = this.riverCells.get(Math.floor(x / 4) * 8192 + Math.floor(z / 4));
    return r !== undefined && r > 0 ? r : 0;
  }
  waterDepth(x, z) { return this.waterLevel(x, z) - this.world.height(x, z); }

  sfx(name, pos, opts) {
    if (!this.audio) return;
    if (pos) this.audio.play(name, { pos: [pos.x, pos.y + 1, pos.z], ...(opts || {}) }); else this.audio.play(name, opts);
  }
  voice(kind) { if (this.audio && this.player) this.audio.voice(kind, { pitch: this.player.data.appearance.voice || 1 }); }
  footstep(actor, run) {
    if (!this.audio) return;
    const p = actor.pos;
    let surf = this.waterDepth(p.x, p.z) > 0.12 ? 'water' : this.world.surface(p.x, p.z);
    if (this.collision.ground(p.x, p.z, p.y) > this.world.height(p.x, p.z) + 0.2) surf = 'wood';
    this.audio.footstep(surf, { pos: [p.x, p.y, p.z], run, heavy: actor.st ? actor.st.weight > 16 : false });
    if (surf === 'water' && run) this.vfx.burst('splash', p, 1);
    else if (run && (surf === 'dirt' || surf === 'sand' || surf === 'ash') && Math.random() < 0.5) this.vfx.burst('dust', p, 0.6);
  }
  hitStop(t) { this.hitStopT = Math.max(this.hitStopT, t); }
  hurtFlash(a) { this.engine.pipeline.hurt.set(0.45, 0.02, 0.02, Math.max(this.engine.pipeline.hurt.w, a)); }
  flag(name) { return !!this.player.data.flags[name]; }
  setFlag(name) { if (this.player.data.flags[name]) return; this.player.data.flags[name] = true; this.quests.onEvent('flag', name); }
  shrineFound(id) { return this.player.data.discovered.shrines.includes(id); }
  poiPos(id) { const p = this.content.P[id]; return p ? { x: p.x, z: p.z } : null; }
  npcPos(id) { const n = this.npcs.find(x => x.id === id); return n ? { x: n.pos.x, z: n.pos.z } : null; }
  mainMarker() {
    const d = this.player.data;
    if (!this.shrineFound('s_croisee')) return this.content.shrines.s_croisee;
    for (const [b, poi] of [['spider', 'boss_spider'], ['knight', 'boss_knight'], ['colossus', 'boss_colossus'], ['priestess', 'boss_priestess']]) if (!d.flags['boss_' + b]) return this.poiPos(poi);
    return this.poiPos('boss_king');
  }
  discoverCodex(id) {
    const d = this.player.data.discovered;
    if (!CODEX[id] || d.lore.includes(id)) return false;
    d.lore.push(id);
    bus.emit('toast', { kind: 'text', text: 'Codex : ' + CODEX[id].title });
    return true;
  }
  codex() { const found = this.player.data.discovered.lore; return Object.keys(CODEX).map(id => ({ id, title: CODEX[id].title, text: CODEX[id].text, category: CODEX[id].category, found: found.includes(id) })); }
  toScreen(v, out = {}) {
    const s = this._scr.copy(v).project(this.engine.camera);
    out.visible = s.z > -1 && s.z < 1 && Math.abs(s.x) < 1.1 && Math.abs(s.y) < 1.1;
    out.x = (s.x * 0.5 + 0.5) * window.innerWidth; out.y = (-s.y * 0.5 + 0.5) * window.innerHeight;
    return out;
  }
  get hour() { return this.engine.atmo.hour; }
  get day() { return this.player ? this.player.data.day : 1; }

  // ------------------------------------------------------------------ start / save
  start(data, fresh) {
    this.reset();
    const p = this.player = new Player(this, data);
    p.setModel(this.models.humanoid({ human: true, ...this._playerLook(data) }));
    p.updateGear();
    if (data.pos) { p.pos.set(data.pos[0], data.pos[1], data.pos[2]); p.yaw = data.yaw || 0; }
    else { const s = this.content.shrines[data.lastShrine] || Object.values(this.content.shrines)[0]; p.pos.copy(s.rest); p.yaw = s.yaw + Math.PI; }
    p.pos.y = this.collision.ground(p.pos.x, p.pos.z);
    p.syncModel(); p.anim.play('idle', 0.01);
    this.engine.atmo.hour = data.hour ?? 8.5;
    this.cam.snap(p.yaw + Math.PI); this.cam.yaw = p.yaw; this.cam.setFollow();
    for (const id of data.discovered.shrines) { const s = this.content.shrines[id]; if (s) s.emitter.on = true; }
    if (this.gateBarrier && data.flags.gate_open) this._openGate(true);
    if (this.content.named.lighthouseTop && data.flags.lighthouse_lit) this.vfx.addEmitter('fire', this.content.named.lighthouseTop, 2.2);
    this._spawnNpcs();
    this._buildInteractables();
    this.playerControl = true; this.deathT = -1;
    if (fresh) { this.discoverCodex('hautefeuille'); }
    this._region(true);
    bus.emit('inventory'); bus.emit('quest'); bus.emit('player:stats');
  }

  _playerLook(d) { const a = d.appearance || {}; return { skin: a.skin, hair: a.hair, hairColor: a.hairColor, beard: a.beard, eyeColor: a.eyeColor, morphs: a.morphs, paint: a.paint, paintColor: a.paintColor, scar: a.scar, brows: a.brows, scale: a.height || 1, player: true }; }

  reset() {
    for (const e of this.enemies) e.dispose();
    for (const n of this.npcs) n.dispose();
    for (const l of this.loot) this.scene.remove(l.mesh);
    if (this.player) this.player.dispose();
    this.enemies = []; this.npcs = []; this.loot = []; this.projectiles = []; this.hazards = [];
    this.activeGroups.clear(); this.tokens = 0; this.boss = null;
    if (this.bossRing) { this.scene.remove(this.bossRing); this.bossRing = null; }
    this.shrine = this.shop = this.smith = this.dialogue = null; this.canFastTravel = false;
    this.player = null;
  }

  serialize() {
    const p = this.player, d = p.data;
    d.pos = [p.pos.x, p.pos.y, p.pos.z]; d.yaw = p.yaw; d.hp = p.hp; d.hour = this.engine.atmo.hour;
    return { player: d, region: this.region.name };
  }

  save(slot = 0) {
    if (!this.player || this.player.dead) return false;
    const ok = this.app.saves.write(slot, this.serialize());
    if (ok && slot !== 0) this.sfx('ui_save');
    return ok;
  }

  // ------------------------------------------------------------------ NPCs & interactables
  _spawnNpcs() {
    for (const id in NPCS) {
      const def = NPCS[id];
      let x, z, yaw = 0;
      const pl = def.place;
      if (pl[0] === '@') { x = pl[1]; z = pl[2]; }
      else {
        const poi = this.content.P[pl[0]];
        if (!poi) continue;
        if (typeof pl[1] === 'string') {
          const named = this.content.named[pl[0] + '.' + pl[1]];
          const a = named && named.anchors && (named.anchors.ANCHOR_npc || named.anchors.ANCHOR_door);
          if (a) { x = a.x; z = a.z; yaw = named.yaw ?? 0; } else { x = poi.x + 6; z = poi.z + 6; }
        } else { x = poi.x + pl[1]; z = poi.z + pl[2]; yaw = Math.atan2(poi.x - x, poi.z - z); }
      }
      const n = new Npc(this, id, def);
      n.setModel(this.models.humanoid({ human: true, ...def.look }));
      n.pos.set(x, this.collision.ground(x, z, 1e9), z);
      // do not stand inside a wall
      this.collision.resolve(n.pos, 0.45, 1.8);
      n.pos.y = this.collision.ground(n.pos.x, n.pos.z, n.pos.y + 0.6);
      n.yaw = n.baseYaw = yaw;
      n.syncModel();
      n.anim.play(n.anim.has(def.anim) ? def.anim : 'idle', 0.01);
      this.npcs.push(n);
    }
  }

  _buildInteractables() {
    const list = this.interactables = [];
    const d = this.player.data;
    for (const id in this.content.shrines) {
      const s = this.content.shrines[id];
      list.push({ type: 'shrine', x: s.x, z: s.z, r: 3.6, shrine: s, get label() { return d.discovered.shrines.includes(id) ? 'Se reposer à l\'Autel' : 'Embraser l\'Autel'; } });
    }
    for (const n of this.npcs) list.push({ type: 'npc', npc: n, get x() { return n.pos.x; }, get z() { return n.pos.z; }, r: 2.6, label: 'Parler à ' + n.def.name });
    for (const it of this.content.interact) {
      if (it.type === 'chest') { if (d.opened[it.key]) { if (it.chest.lid) it.chest.lid.rotation.x = -1.9; continue; } }
      if (it.once && d.flags[it.once]) continue;
      list.push(it);
    }
    const t = this.content.named.throne;
    if (t) list.push({ type: 'throne', x: t.pos.x, z: t.pos.z + 3, r: 4, label: 'Approcher de l\'Astre brisé', get hidden() { return !d.flags.boss_king || d.flags.ending; } });
  }

  _updateFocus() {
    const p = this.player;
    let best = null, bd = 1e9;
    if (p.state === 'free' && !p.dead && this.playerControl) {
      for (const it of this.interactables) {
        if (it.hidden || it.done) continue;
        const dx = it.x - p.pos.x, dz = it.z - p.pos.z, d = Math.hypot(dx, dz);
        if (d < it.r && d < bd) { bd = d; best = it; }
      }
      for (const l of this.loot) { const d = Math.hypot(l.x - p.pos.x, l.z - p.pos.z); if (d < 1.4) this._pickup(l); }
    }
    if (best !== this._focusIt) { this._focusIt = best; this.focus = best ? { label: best.label, key: this.input.actionLabel('interact') } : null; }
    else if (best) this.focus.label = best.label;
  }

  /** called by the player on the interact action */
  interact() {
    const it = this._focusIt, p = this.player, d = p.data;
    if (!it) return false;
    if (this.boss && it.type !== 'throne') return false;
    if (it.type === 'shrine') this._useShrine(it.shrine);
    else if (it.type === 'npc') this.talk(it.npc);
    else if (it.type === 'stele') {
      p.setState('interact'); p.anim.playOnce('interact', { fade: 0.1 });
      this.sfx('rune_activate', p.pos);
      const c = CODEX[it.codex];
      if (this.discoverCodex(it.codex)) p.addXp(60);
      if (c) bus.emit('subtitle', { text: c.title + ' — ' + c.text, time: 9 });
    } else if (it.type === 'chest') {
      p.setState('interact'); p.anim.playOnce('pickup', { fade: 0.1 });
      d.opened[it.key] = true; it.done = true;
      it.chest.opening = 0.001;
      this.sfx('chest_open', p.pos);
      this._chestLoot(it.chest);
    } else if (it.type === 'lighthouse') {
      p.setState('interact'); p.anim.playOnce('interact', { fade: 0.1 });
      this.setFlag('lighthouse_lit'); it.done = true;
      const top = this.content.named.lighthouseTop;
      if (top) { this.vfx.addEmitter('fire', top, 2.2); this.vfx.burst('shrine', top, 2); }
      this.sfx('shrine_ignite', p.pos);
      bus.emit('banner', { title: 'LE PHARE BRÛLE', sub: 'Port-Brisants', kind: 'shrine' });
    } else if (it.type === 'throne') this._ending();
    return true;
  }

  _chestLoot(c) {
    const p = this.player, rnd = mulberry32(hash2(Math.round(c.x), Math.round(c.z), 77));
    const tier = c.tier || 1;
    const gold = c.gold ?? Math.round((40 + rnd() * 60) * tier * tier * 0.7);
    p.data.gold += gold; bus.emit('toast', { kind: 'gold', n: gold });
    const items = c.loot ? c.loot.slice() : [];
    if (!c.loot) {
      const pools = [null, ['whetstone', 'herb_poultice', 'bread', 'steel_shard', 'hatchet', 'leather_head'], ['steel_shard', 'vigor_elixir', 'frost_salve', 'war_axe', 'chain_head', 'chain_legs', 'ember_bomb'], ['astral_fragment', 'amber_sap', 'steel_sword', 'morningstar', 'chain_chest', 'return_charm'], ['astral_fragment', 'ember_seed', 'great_axe', 'war_hammer', 'plate_legs', 'plate_head', 'amber_sap']];
      const pool = pools[tier];
      const n = 2 + Math.floor(rnd() * 2);
      for (let i = 0; i < n; i++) { const id = pool[Math.floor(rnd() * pool.length)]; items.push([id, ITEMS[id].stack ? 1 + Math.floor(rnd() * 2) : 1]); }
    }
    for (const [id, n] of items) p.addItem(id, n);
    this.sfx('pickup_gold', p.pos);
    this.vfx.burst('pickup', p.pos);
  }

  // ------------------------------------------------------------------ shrines
  _useShrine(s) {
    const p = this.player, d = p.data;
    const isNew = !d.discovered.shrines.includes(s.id);
    if (isNew) {
      d.discovered.shrines.push(s.id);
      s.emitter.on = true;
      this.vfx.burst('shrine', _v.set(s.x, s.fire.y - 1, s.z), 1.5);
      this.sfx('shrine_ignite', p.pos);
      bus.emit('banner', { title: 'AUTEL EMBRASÉ', sub: s.name, kind: 'shrine' });
      p.addXp(120 + d.discovered.shrines.length * 30);
      this.quests.onEvent('shrine', s.id);
    }
    d.lastShrine = s.id;
    p.pos.x = s.rest.x; p.pos.z = s.rest.z; p.yaw = Math.atan2(s.x - s.rest.x, s.z - s.rest.z);
    p.target = null; bus.emit('lock', null);
    p.setState('rest');
    p.anim.setUpper(null);
    p.anim.playOnce('kneel_down', { fade: 0.2, onDone: () => { if (p.state === 'rest') p.anim.play('kneel', 0.15); } });
    this._restEffects();
    this.shrine = { id: s.id, name: s.name, get flaskCountCost() { return p.count('amber_sap') > 0 && d.flaskMax < 9; }, get flaskPowerCost() { return p.count('ember_seed') > 0 && d.flaskLevel < 5; } };
    this.canFastTravel = true;
    if (!isNew) this.sfx('shrine_rest', p.pos);
    setTimeout(() => { if (this.shrine) bus.emit('open', 'shrine'); }, isNew ? 1600 : 700);
    this.save(0);
  }

  _restEffects() {
    const p = this.player, d = p.data;
    p.refresh();
    p.hp = p.maxHp; d.stamina = p.st.maxSt; d.mana = p.st.maxMana; d.flasks = d.flaskMax;
    p.status = {};
    d.killed = {};
    // everything that was slain rises again
    for (const e of this.enemies) e.dispose();
    this.enemies = []; this.activeGroups.clear(); this.tokens = 0;
    for (const l of this.loot) this.scene.remove(l.mesh);
    this.loot = [];
    bus.emit('player:flask');
  }

  shrineAction(a) {
    const p = this.player, d = p.data;
    if (!this.shrine) return;
    if (a === 'flaskCount' && p.count('amber_sap') > 0 && d.flaskMax < 9) { p.removeItem('amber_sap', 1); d.flaskMax++; d.flasks = d.flaskMax; this.sfx('heal'); bus.emit('player:flask'); }
    else if (a === 'flaskPower' && p.count('ember_seed') > 0 && d.flaskLevel < 5) { p.removeItem('ember_seed', 1); d.flaskLevel++; this.sfx('heal'); bus.emit('player:flask'); }
    else if (a === 'morning' || a === 'night') { const target = a === 'morning' ? 7.5 : 21.5; if (this.engine.atmo.hour > target || a === 'night' && this.engine.atmo.hour < 5) d.day++; this.engine.atmo.hour = target; this._restEffects(); }
    else if (a === 'leave') this.closePanel();
  }

  fastTravel(id) {
    const s = this.content.shrines[id], p = this.player;
    if (!s || !this.canFastTravel || !this.shrineFound(id)) return;
    this.sfx('fast_travel');
    this.engine.pipeline.fade = 1; this._fadeIn = 0.9;
    p.pos.set(s.rest.x, this.collision.ground(s.rest.x, s.rest.z), s.rest.z);
    p.yaw = Math.atan2(s.x - s.rest.x, s.z - s.rest.z);
    p.data.lastShrine = id;
    this.shrine.id = id; this.shrine.name = s.name;
    this.cam.snap(p.yaw);
    this._restEffects();
    this._region(true);
  }

  closePanel() {
    const p = this.player;
    if (this.shrine) {
      this.shrine = null; this.canFastTravel = false;
      if (p.state === 'rest') p.anim.playOnce('kneel_up', { fade: 0.15, onDone: () => { if (p.state === 'rest') p.setState('free'); } });
      this.save(0);
    }
    this.shop = null; this.smith = null;
    if (this.dialogue) { this.dialogue = null; bus.emit('dialogue'); }
  }

  // ------------------------------------------------------------------ dialogue / shop / smith
  talk(npc) {
    const def = npc.def;
    if (def.codex) this.discoverCodex(def.codex);
    this._setNode(def, def.talk(this));
  }
  _setNode(def, node) {
    if (!node) { this.dialogue = null; bus.emit('dialogue'); return; }
    const opts = node.options && node.options.length ? node.options : [{ label: 'Au revoir.', go: () => null }];
    this.dialogue = { speaker: def.name, role: def.role, text: node.text, options: opts.map(o => ({ label: o.label })), choose: (i) => { const o = opts[i]; if (!o) return; this.sfx('ui_click'); this._setNode(def, o.go ? o.go(this) : null); } };
    bus.emit('dialogue');
  }
  openShop(npcId) {
    const def = NPCS[npcId], p = this.player, d = p.data, g = this;
    const sold = d.flags;
    const stock = def.stock.map(([id, qty]) => ({ id, price: Math.max(1, Math.round(ITEMS[id].value * 1.0)) || 50, qty: Math.max(0, qty - (sold['sold_' + npcId + '_' + id] || 0)) })).filter(s => s.qty > 0);
    this.dialogue = null; bus.emit('dialogue');
    this.shop = {
      name: def.name, stock,
      buy(i) { const s = stock[i]; if (!s || s.qty <= 0 || d.gold < s.price) { g.sfx('ui_error'); return false; } d.gold -= s.price; s.qty--; const it = ITEMS[s.id]; if (!it.stack) sold['sold_' + npcId + '_' + s.id] = (sold['sold_' + npcId + '_' + s.id] || 0) + 1; p.addItem(s.id, 1, 0, true); g.sfx('ui_buy'); return true; },
      sellPrice(idx) { const it = d.inventory[idx]; const def2 = it && ITEMS[it.id]; return def2 && def2.type !== 'key' ? Math.max(1, Math.floor((def2.value || 0) * 0.4 * (1 + (it.up || 0) * 0.3))) : 0; },
      sell(idx) { const it = d.inventory[idx]; const pr = this.sellPrice(idx); if (!it || pr <= 0) { g.sfx('ui_error'); return false; } d.gold += pr; p.removeItem(it.id, 1); g.sfx('pickup_gold'); return true; },
      close() { g.closePanel(); },
    };
    bus.emit('open', 'shop');
  }
  openSmith() {
    const p = this.player, d = p.data, g = this;
    this.dialogue = null; bus.emit('dialogue');
    const entry = (where, inst) => {
      const def = ITEMS[inst.id];
      if (!def || !def.maxUp || (inst.up || 0) >= def.maxUp) return null;
      const cost = UPGRADE_COST[inst.up || 0];
      let can = d.gold >= cost.gold;
      for (const k in cost) if (k !== 'gold' && p.count(k) < cost[k]) can = false;
      return { where, id: inst.id, up: inst.up || 0, cost, can };
    };
    this.smith = {
      list() { const out = []; for (const slot of ['weapon', 'offhand']) if (d.equipment[slot]) { const e = entry(slot, d.equipment[slot]); if (e) out.push(e); } d.inventory.forEach((it, i) => { const e = entry(i, it); if (e) out.push(e); }); return out; },
      upgrade(where) {
        const inst = typeof where === 'string' ? d.equipment[where] : d.inventory[where];
        const e = inst && entry(where, inst);
        if (!e || !e.can) { g.sfx('ui_error'); return false; }
        d.gold -= e.cost.gold;
        for (const k in e.cost) if (k !== 'gold') p.removeItem(k, e.cost[k]);
        inst.up = (inst.up || 0) + 1;
        p.refresh(); g.sfx('anvil'); bus.emit('inventory');
        return true;
      },
      close() { g.closePanel(); },
    };
    bus.emit('open', 'smith');
  }

  // ------------------------------------------------------------------ items / skills
  useItem(index) {
    const p = this.player, it = p.data.inventory[index], def = it && ITEMS[it.id];
    if (!def) return false;
    if (def.slot) { p.equip(index); return true; }
    if (def.type !== 'consumable') return false;
    const e = def.effect;
    if (e.recall) { const s = this.content.shrines[p.data.lastShrine]; if (!s || this.boss) { this.sfx('ui_error'); return false; } this.sfx('fast_travel'); this.engine.pipeline.fade = 1; this._fadeIn = 0.9; p.pos.set(s.rest.x, this.collision.ground(s.rest.x, s.rest.z), s.rest.z); this.cam.snap(p.yaw); }
    if (e.heal) p.heal(p.maxHp * e.heal);
    if (e.regen) p.regen = { rate: e.regen * (1 + p.maxHp / 400), t: e.time };
    if (e.cure) p.cureStatus(e.cure);
    if (e.buff) p.buff(e.buff, e.mult, e.time);
    if (e.throw) {
      const dir = p.target ? _v.subVectors(p.target.pos, p.pos).setY(0).normalize() : _v.set(Math.sin(this.cam.yaw), 0, Math.cos(this.cam.yaw));
      this.projectiles.push({ x: p.pos.x + dir.x * 0.6, y: p.pos.y + 1.6, z: p.pos.z + dir.z * 0.6, vx: dir.x * 15, vy: 5, vz: dir.z * 15, kind: 'fire', dmg: e.dmg * p.st.skillPower, team: 'player', radius: e.radius, grav: 12, life: 3, status: ['burn', 12], from: p });
      this.sfx('swing_light', p.pos);
    }
    p.removeItem(it.id, 1);
    this.sfx(e.throw ? 'ui_click' : 'potion', p.pos);
    if (e.heal || e.regen) this.vfx.burst('heal', p.pos);
    return true;
  }
  dropItem(index) { const it = this.player.data.inventory[index]; if (!it || ITEMS[it.id].type === 'key') return; this.player.removeItem(it.id, it.qty); }
  setSkillSlot(slot, id) { const d = this.player.data; if (id && !d.skills.includes(id)) return; for (let i = 0; i < 3; i++) if (d.skillSlots[i] === id) d.skillSlots[i] = null; d.skillSlots[slot] = id; bus.emit('player:stats'); }

  castSkill(p, id, sk) {
    const power = p.st.skillPower, dmg = (sk.dmg || 0) * (1 + (power - 1) * (sk.sc || 1) * 0.5);
    const fx = p.fx, fz = p.fz;
    if (sk.type === 'projectile') {
      let dir = _v.set(fx, 0, fz);
      const t = p.target;
      if (t && !t.dead) dir.set(t.pos.x - p.pos.x, (t.pos.y + t.height * 0.5) - (p.pos.y + 1.4), t.pos.z - p.pos.z).normalize();
      this.projectiles.push({ x: p.pos.x + fx * 0.7, y: p.pos.y + 1.4, z: p.pos.z + fz * 0.7, vx: dir.x * 24, vy: dir.y * 24, vz: dir.z * 24, kind: sk.proj, dmg, team: 'player', radius: 1.6, grav: 0, life: 2.4, status: sk.status, from: p, skill: true });
      this.sfx('spell_fire', p.pos);
    } else if (sk.type === 'buff') {
      p.buff(sk.buff, sk.mult, sk.time);
      this.sfx('wolf_howl', p.pos); this.cam.shake(0.4);
      this.vfx.burst('magic', p.pos, 2.2, [2.2, 1.4, 0.6]);
      for (const e of this.enemies) if (!e.dead && e.distTo(p) < sk.radius + e.radius) { e.setAggro(false); if (e.addPoise(sk.stagger) || !e.isBoss) e._stagger(1.1, true); }
    } else if (sk.type === 'cone') {
      this.sfx('spell_dark', p.pos);
      for (let i = 1; i <= 4; i++) this.vfx.burst('magic', _v.set(p.pos.x + fx * i * 2, p.pos.y, p.pos.z + fz * i * 2), 0.8 + i * 0.3, [1.0, 0.5, 2.0]);
      for (const e of this.enemies) if (!e.dead && e.distTo(p) < sk.range + e.radius && p.facingOff(e) < sk.arc * Math.PI / 360 + 0.2) { e.takeHit({ dmg, poise: 20, from: p, status: sk.status, skill: true }); e.applyStatus('slow', 100); }
    } else if (sk.type === 'wave') {
      this.sfx('splash', p.pos); this.sfx('spell_impact', p.pos);
      this.hazards.push({ type: 'wave', team: 'player', x: p.pos.x, z: p.pos.z, y: p.pos.y, dx: fx, dz: fz, t: 0, speed: 18, range: sk.range, width: sk.width, dmg, hit: new Set(), from: p, knock: true });
    } else if (sk.type === 'nova') {
      this.sfx('spell_ice', p.pos); this.cam.shake(0.4);
      this.vfx.burst('ice', p.pos, sk.radius * 0.5);
      for (const e of this.enemies) if (!e.dead && e.distTo(p) < sk.radius + e.radius) { e.takeHit({ dmg, poise: 60, from: p, status: sk.status, skill: true }); e.applyStatus('frost', 100); }
    } else if (sk.type === 'pillar') {
      const t = p.target && !p.target.dead ? p.target.pos : _v.set(p.pos.x + fx * 9, 0, p.pos.z + fz * 9);
      const x = t.x, z = t.z, y = this.collision.ground(x, z);
      this.vfx.telegraph(x, y, z, sk.radius, 0.5, 0xffa040);
      this.hazards.push({ type: 'blast', team: 'player', x, y, z, t: 0, delay: 0.5, radius: sk.radius, dmg, status: sk.status, fx: 'fire', from: p });
    }
    bus.emit('player:stats');
  }

  // ------------------------------------------------------------------ combat resolution
  nearestEnemy(pos, range, yaw, maxAngle) {
    let best = null, bd = range;
    for (const e of this.enemies) {
      if (e.dead) continue;
      const d = Math.hypot(e.pos.x - pos.x, e.pos.z - pos.z) - e.radius;
      if (d > bd) continue;
      const a = Math.abs(Math.atan2(Math.sin(Math.atan2(e.pos.x - pos.x, e.pos.z - pos.z) - yaw), Math.cos(Math.atan2(e.pos.x - pos.x, e.pos.z - pos.z) - yaw)));
      if (a > maxAngle) continue;
      bd = d; best = e;
    }
    return best;
  }

  findLockTarget() {
    const p = this.player, cy = this.cam.yaw;
    let best = null, bs = 1e9;
    for (const e of this.enemies) {
      if (e.dead) continue;
      const d = p.distTo(e);
      if (d > 30) continue;
      const ang = Math.atan2(e.pos.x - p.pos.x, e.pos.z - p.pos.z);
      const off = Math.abs(Math.atan2(Math.sin(ang - cy), Math.cos(ang - cy)));
      if (off > 1.25) continue;
      if (!this.collision.los(p.pos.x, p.pos.y + 1.5, p.pos.z, e.pos.x, e.pos.y + e.height * 0.7, e.pos.z)) continue;
      const score = off * 14 + d * (e.aggro ? 0.6 : 1) - (e.isBoss ? 20 : 0);
      if (score < bs) { bs = score; best = e; }
    }
    return best;
  }

  /** called every frame of the active window of a player attack */
  playerSwing(p, a) {
    const diff = DIFFICULTY[this.settings.get('difficulty')] || DIFFICULTY.normal;
    let any = false;
    for (const e of this.enemies) {
      if (e.dead || a.hit.has(e)) continue;
      const d = p.distTo(e) - e.radius;
      if (d > a.reach) continue;
      if (Math.abs(e.pos.y - p.pos.y) > 2.2 + e.height) continue;
      const tol = Math.atan2(e.radius, Math.max(d + e.radius, 0.3));
      if (p.facingOff(e) > a.arc * Math.PI / 180 + tol) continue;
      a.hit.add(e);
      const st = p.st, w = st.weapon;
      let dmg = st.attack * a.mult * diff.dmgDealt * p.buffMult('sharp') * p.buffMult('fury');
      let crit = Math.random() < st.crit;
      if (p.riposteT > 0 && e.vulnerableT > 0) crit = true;
      if (crit) dmg *= st.critMult;
      const status = w && w.bleed ? ['bleed', w.bleed] : w && w.frost ? ['frost', w.frost] : null;
      const res = e.takeHit({ dmg, poise: (w ? w.poise : 10) * a.mult * (a.heavy ? 1.5 : 1), from: p, heavy: !!a.heavy, crit, status });
      p.data.mana = Math.min(p.st.maxMana, p.data.mana + (res.blocked ? 1 : 4));
      any = true;
    }
    if (any && !a.stopped) { a.stopped = true; this.hitStop(a.heavy ? 0.085 : 0.05); this.cam.shake(a.heavy ? 0.35 : 0.15); this.input.rumble(0.4, 0.6, 90); }
  }

  alertNear(src, range) { for (const e of this.enemies) if (e !== src && !e.dead && !e.aggro && !e.isBoss && e.distTo(src) < range) e.setAggro(false); }

  spawnProjectile(e, a, i, n) {
    const p = this.player;
    const sx = e.pos.x + e.fx * (e.radius + 0.3), sy = e.pos.y + e.height * 0.75, sz = e.pos.z + e.fz * (e.radius + 0.3);
    const speed = a.proj === 'meteor' ? 16 : a.proj === 'venom' ? 17 : 21;
    const dist = Math.hypot(p.pos.x - sx, p.pos.z - sz), tt = dist / speed;
    const lead = n > 1 ? (i - (n - 1) / 2) * 0.9 : 0.6;
    const tx = p.pos.x + p.vel.x * tt * (n > 1 ? 0.5 : lead) + (n > 1 ? -e.fz * lead * 1.6 : 0), tz = p.pos.z + p.vel.y * tt * (n > 1 ? 0.5 : lead) + (n > 1 ? e.fx * lead * 1.6 : 0);
    const grav = a.proj === 'venom' ? 6 : 0;
    const dx = tx - sx, dz = tz - sz, dy = (p.pos.y + 1.1) - sy, d = Math.hypot(dx, dz) || 1, t2 = d / speed;
    this.projectiles.push({ x: sx, y: sy, z: sz, vx: dx / d * speed, vy: dy / t2 + 0.5 * grav * t2, vz: dz / d * speed, kind: a.proj, dmg: e.dmg * a.dmg, team: 'enemy', radius: 0.9, grav, life: 4, status: a.status, from: e, poise: a.poise || 15 });
    this.sfx(a.proj === 'venom' ? 'spider_spit' : a.proj === 'frost' ? 'spell_ice' : 'spell_fire', e.pos);
  }

  hazardRain(e, a) {
    const p = this.player;
    for (let i = 0; i < a.count; i++) {
      const ang = Math.random() * 6.283, r = i < 3 ? Math.random() * 2 : 2 + Math.random() * 9;
      const x = p.pos.x + Math.cos(ang) * r + p.vel.x * (i < 3 ? 0.6 : 0), z = p.pos.z + Math.sin(ang) * r + p.vel.y * (i < 3 ? 0.6 : 0);
      const delay = 0.9 + i * (a.type === 'pillars' ? 0.28 : 0.2);
      const radius = a.radius || 2.4, y = this.collision.ground(x, z);
      this.hazards.push({ type: 'blast', team: 'enemy', x, y, z, t: 0, delay, radius, dmg: e.dmg * a.dmg, status: a.status, fx: a.proj === 'ice' ? 'ice' : 'fire', from: e, tele: false, falling: a.proj === 'meteor' || a.proj === 'ice' || a.proj === 'dawn' ? a.proj : null });
    }
  }

  hazardWave(e, a) {
    this.sfx('splash', e.pos);
    this.hazards.push({ type: 'wave', team: 'enemy', x: e.pos.x, z: e.pos.z, y: e.pos.y, dx: e.fx, dz: e.fz, t: 0, speed: 16, range: a.range[1], width: 3.4, dmg: e.dmg * a.dmg, status: a.status, hit: new Set(), from: e, knock: true });
  }

  summon(src, defId, count) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * 6.283, r = 5 + Math.random() * 4;
      const e = this._makeEnemy(defId, ENEMIES[defId], src.pos.x + Math.cos(a) * r, src.pos.z + Math.sin(a) * r, { home: src.home });
      e.arenaR = src.arenaR; e.summoned = true;
      this.vfx.burst('magic', e.pos, 1.2, [1.0, 0.4, 1.6]);
      e.setAggro(false);
    }
  }

  onStatusProc(actor, name) {
    const fx = name === 'poison' ? 'poison' : name === 'burn' ? 'fire' : name === 'frost' || name === 'slow' ? 'ice' : 'blood';
    this.vfx.burst(fx, actor.pos, 1);
    if (actor === this.player) bus.emit('toast', { kind: 'text', text: { poison: 'Empoisonné !', burn: 'Vous brûlez !', frost: 'Gelé !', slow: 'Entravé !', bleed: 'Hémorragie !' }[name] || name });
  }

  // ------------------------------------------------------------------ enemies: spawning
  _makeEnemy(defId, def, x, z, opts = {}) {
    const e = new Enemy(this, defId, def, opts);
    e.setModel(this.models.forDef(def));
    e.spawnAt(x, z);
    if (opts.home) e.home.copy(opts.home);
    this.enemies.push(e);
    return e;
  }

  _spawnGroup(key, defId, x, z, n, r, elite) {
    const def0 = ENEMIES[defId];
    if (!def0) return;
    const def = elite ? { ...def0, name: elite.name, hp: def0.hp * elite.hp, dmg: def0.dmg * elite.dmg, xp: def0.xp * elite.xp, poise: def0.poise * 1.6, look: { ...def0.look, scale: elite.scale || def0.look.scale }, loot: elite.loot || def0.loot, gold: [elite.gold || 0, elite.gold || 0], eliteFlag: elite.flag } : def0;
    const list = [];
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, d = Math.random() * r;
      let ex = x + Math.cos(a) * d, ez = z + Math.sin(a) * d;
      if (this.world.height(ex, ez) < 0.2 && !def.floats) { ex = x; ez = z; }
      const e = this._makeEnemy(defId, def, ex, ez, { key });
      this.collision.resolve(e.pos, e.radius, e.height);
      e.groupKey = key;
      list.push(e);
    }
    this.activeGroups.set(key, list);
  }

  _updateSpawns() {
    const p = this.player, d = p.data, w = this.world;
    const px = p.pos.x, pz = p.pos.z;
    // procedural groups on a coarse grid
    const c0 = Math.floor((px - 130) / SPAWN_CELL), c1 = Math.floor((px + 130) / SPAWN_CELL), d0 = Math.floor((pz - 130) / SPAWN_CELL), d1 = Math.floor((pz + 130) / SPAWN_CELL);
    for (let ci = c0; ci <= c1; ci++) for (let cj = d0; cj <= d1; cj++) {
      const key = 'g' + ci + '_' + cj;
      if (this.activeGroups.has(key) || d.killed[key]) continue;
      const rnd = mulberry32(hash2(ci, cj, 31337));
      const x = (ci + 0.15 + rnd() * 0.7) * SPAWN_CELL, z = (cj + 0.15 + rnd() * 0.7) * SPAWN_CELL;
      const roll = rnd(), pickR = rnd(), nR = rnd();
      const dist = Math.hypot(x - px, z - pz);
      if (dist > 125 || dist < 45) continue;
      if (Math.abs(x) > 2450 || Math.abs(z) > 2450) { this.activeGroups.set(key, []); continue; }
      const biome = BIOME_KEYS[w.biome(x, z)];
      const table = SPAWN_TABLE[biome];
      const chance = { meadow: 0.42, beach: 0.25, forest: 0.62, swamp: 0.66, mountain: 0.5, ash: 0.62, citadel: 0.75 }[biome] || 0;
      let ok = !!table && roll < chance && w.height(x, z) > 0.6 && w.slope(x, z) < 26;
      if (ok) for (const s of this.content.safe) if (Math.hypot(x - s[0], z - s[1]) < s[2] + 30) ok = false;
      if (ok) for (const poi of w.pois) if (Math.hypot(x - poi.x, z - poi.z) < poi.r + 25) ok = false;
      if (ok) for (const s of w.shrines) if (Math.hypot(x - s.x, z - s.z) < 28) ok = false;
      if (!ok) { this.activeGroups.set(key, []); continue; }
      let tot = 0; for (const t of table) tot += t[1];
      let v = pickR * tot, defId = table[0][0];
      for (const t of table) { v -= t[1]; if (v <= 0) { defId = t[0]; break; } }
      const def = ENEMIES[defId];
      const n = def.pack ? def.pack[0] + Math.floor(nR * (def.pack[1] - def.pack[0] + 1)) : 1;
      this._spawnGroup(key, defId, x, z, n, 5 + n * 1.2);
    }
    // fixed groups
    for (const s of this.content.spawns) {
      if (this.activeGroups.has(s.key) || d.killed[s.key]) continue;
      if (s.elite && s.elite.flag && d.flags[s.elite.flag]) continue;
      if (Math.hypot(s.x - px, s.z - pz) < 115) this._spawnGroup(s.key, s.def, s.x, s.z, s.n, s.r, s.elite);
    }
    // bosses wait in their arena
    for (const id in BOSSES) {
      const def = BOSSES[id], key = 'boss_' + id;
      if (this.activeGroups.has(key) || d.flags[key]) continue;
      const poi = this.content.P[def.poi];
      if (!poi || Math.hypot(poi.x - px, poi.z - pz) > 170) continue;
      const e = this._makeEnemy(id, def, poi.x, poi.z - 4, { boss: true, key, home: new THREE.Vector3(poi.x, poi.y, poi.z), arenaR: poi.r });
      e.bossId = id; e.yaw = Math.atan2(px - poi.x, pz - poi.z); e.syncModel();
      this.activeGroups.set(key, [e]);
    }
    // despawn far, idle groups
    for (const [key, list] of this.activeGroups) {
      if (!list.length) { if (key[0] === 'g') { const [ci, cj] = key.slice(1).split('_').map(Number); if (Math.hypot((ci + 0.5) * SPAWN_CELL - px, (cj + 0.5) * SPAWN_CELL - pz) > 260) this.activeGroups.delete(key); } continue; }
      let far = true, alive = false;
      for (const e of list) { if (!e.dead && !e.remove) alive = true; if (e.distTo(p) < 175 || e.aggro) far = false; }
      if (far || !alive && list.every(e => e.remove)) {
        for (const e of list) { const i = this.enemies.indexOf(e); if (i >= 0) this.enemies.splice(i, 1); e.dispose(); }
        this.activeGroups.delete(key);
        if (!alive && key[0] !== 'b') d.killed[key] = 1;
      }
    }
  }

  onEnemyKilled(e, from) {
    const p = this.player, d = p.data, def = e.def;
    const diff = DIFFICULTY[this.settings.get('difficulty')] || DIFFICULTY.normal;
    d.stats.kills++;
    if (!e.summoned) { const xp = Math.round(def.xp * diff.xp); p.addXp(xp); bus.emit('toast', { kind: 'xp', n: xp }); }
    this.quests.onEvent('kill', e.defId);
    const cx = e.isBoss ? BOSS_CODEX[e.bossId] : CREATURE_CODEX[e.defId];
    if (cx) this.discoverCodex(cx);
    if (def.eliteFlag) this.setFlag(def.eliteFlag);
    // loot
    const items = [];
    for (const [id, ch] of def.loot || []) if (Math.random() < ch) items.push([id, 1]);
    const gold = def.gold ? Math.round(def.gold[0] + Math.random() * (def.gold[1] - def.gold[0])) : 0;
    if (e.isBoss) this._bossDefeated(e);
    else if ((items.length || gold) && !e.summoned) this._dropLoot(e.pos, items, gold);
    if (e.groupKey) { const list = this.activeGroups.get(e.groupKey); if (list && list.every(x => x.dead)) d.killed[e.groupKey] = 1; }
    if (p.target === e) { p.target = this.settings.get('autoLock') ? this.findLockTarget() : null; bus.emit('lock', p.target); }
  }

  _dropLoot(pos, items, gold) {
    const mesh = new THREE.Mesh(new THREE.OctahedronGeometry(0.16), new THREE.MeshBasicMaterial({ color: 0xffd27a, fog: false }));
    mesh.position.set(pos.x, pos.y + 0.6, pos.z);
    this.scene.add(mesh);
    this.loot.push({ x: pos.x, z: pos.z, y: pos.y, items, gold, mesh, t: 0 });
  }

  _pickup(l) {
    const p = this.player;
    const i = this.loot.indexOf(l);
    if (i < 0) return;
    this.loot.splice(i, 1); this.scene.remove(l.mesh);
    if (l.gold) { p.data.gold += l.gold; bus.emit('toast', { kind: 'gold', n: l.gold }); this.sfx('pickup_gold', p.pos); }
    for (const [id, n] of l.items) p.addItem(id, n);
    if (l.items.length) this.sfx('pickup_item', p.pos);
    this.vfx.burst('pickup', p.pos);
  }

  // ------------------------------------------------------------------ bosses
  startBoss(e) {
    if (this.boss === e) return;
    this.boss = e;
    this.sfx('boss_roar', e.pos);
    this.cam.shake(0.5);
    bus.emit('boss:start', e);
    bus.emit('banner', { title: e.def.name.toUpperCase(), sub: e.def.title, kind: 'boss' });
    const geo = new THREE.CylinderGeometry(e.arenaR, e.arenaR, 7, 64, 1, true);
    const mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, uniforms: { uTime: U.uTime },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }',
      fragmentShader: 'uniform float uTime; varying vec2 vUv; void main(){ float w = sin( vUv.x * 180.0 + uTime * 1.5 ) * 0.5 + 0.5; float f = pow( 1.0 - vUv.y, 2.5 ); gl_FragColor = vec4( vec3( 1.0, 0.35, 0.15 ) * f * ( 0.25 + 0.5 * w ), 1.0 ); }',
    });
    this.bossRing = new THREE.Mesh(geo, mat);
    this.bossRing.position.set(e.home.x, e.home.y + 3.4, e.home.z);
    this.scene.add(this.bossRing);
  }

  _endBoss(won) {
    const e = this.boss;
    if (!e) return;
    this.boss = null;
    if (this.bossRing) { this.scene.remove(this.bossRing); this.bossRing.geometry.dispose(); this.bossRing = null; }
    bus.emit('boss:end', { boss: e, won });
  }

  _bossDefeated(e) {
    const p = this.player, d = p.data, def = e.def, id = e.bossId;
    this._endBoss(true);
    d.stats.bosses++;
    this.hitStop(0.25); this.cam.shake(0.9);
    this.vfx.burst('levelup', e.pos, 2);
    const r = def.reward || {};
    for (const [it, n] of r.items || []) p.addItem(it, n);
    if (r.gold) { d.gold += r.gold; bus.emit('toast', { kind: 'gold', n: r.gold }); }
    if (r.skill && !d.skills.includes(r.skill)) { d.skills.push(r.skill); const free = d.skillSlots.indexOf(null); if (free >= 0) d.skillSlots[free] = r.skill; bus.emit('toast', { kind: 'skill', id: r.skill }); }
    if (SHARD_OF[id] && !d.shards.includes(id)) d.shards.push(id);
    this.setFlag('boss_' + id);
    for (const o of this.enemies) if (o.summoned && !o.dead) o.die(null);
    this.audio && this.audio.setMusic('victory');
    bus.emit('banner', { title: SHARD_OF[id] ? 'ÉCLAT RETROUVÉ' : id === 'king' ? 'LE ROI EST TOMBÉ' : 'GRAND ALPHA TERRASSÉ', sub: def.name + ' — ' + def.title, kind: 'shard' });
    p.heal(p.maxHp); d.flasks = d.flaskMax; bus.emit('player:flask');
    this.save(0);
  }

  _openGate(instant) {
    const gb = this.gateBarrier;
    if (!gb || gb.open) return;
    gb.open = true;
    gb.box.y0 = 9999; gb.box.y1 = 9998;       // disable the collider
    if (instant) gb.mesh.visible = false; else { gb.fade = 1; this.sfx('rune_activate', this.player.pos); this.vfx.burst('magic', _v.set(gb.mesh.position.x, gb.mesh.position.y - 2, gb.mesh.position.z), 3); bus.emit('banner', { title: 'LA PORTE ROYALE S\'OUVRE', sub: 'Citadelle d\'Aubeclair', kind: 'shrine' }); }
    this.setFlag('gate_open');
  }

  _ending() {
    const g = this, d = this.player.data;
    this.dialogue = { speaker: "L'Astre brisé", role: '', text: "Les quatre Éclats vibrent contre le cinquième, encore tiède de la main du roi. Ils veulent se rejoindre. Votre lame, elle, n'attend qu'un geste.", options: [{ label: "Reforger l'Astre-Cœur." }, { label: 'Briser le dernier Éclat.' }, { label: 'Pas encore.' }],
      choose(i) { g.dialogue = null; bus.emit('dialogue'); if (i > 1) return; d.flags.ending = i === 0 ? 'reforge' : 'shatter'; g.save(0); g.vfx.burst('shrine', g.player.pos, 3); g.sfx(i === 0 ? 'shrine_ignite' : 'boss_death'); bus.emit('ending', { id: d.flags.ending }); } };
    bus.emit('dialogue');
  }

  onPlayerDeath() {
    this.deathT = 0;
    this.sfx('death_toll');
    this.audio && this.audio.setMusic('death');
    bus.emit('death');
  }

  _respawn() {
    const p = this.player, d = p.data;
    this.deathT = -1;
    if (this.boss) { const b = this.boss; this._endBoss(false); }
    d.gold = Math.floor(d.gold * 0.9);
    const s = this.content.shrines[d.lastShrine] || Object.values(this.content.shrines)[0];
    p.pos.set(s.rest.x, this.collision.ground(s.rest.x, s.rest.z), s.rest.z);
    p.yaw = Math.atan2(s.x - s.rest.x, s.z - s.rest.z);
    p.revive();
    this._restEffects();
    this.projectiles.length = 0; this.hazards.length = 0;
    this.cam.snap(p.yaw);
    this.engine.pipeline.fade = 1; this._fadeIn = 1.2;
    this.engine.pipeline.desat = 0;
    this.sfx('respawn');
    this._region(true);
    bus.emit('respawn');
    this.save(0);
  }

  // ------------------------------------------------------------------ UI data
  compass() {
    const p = this.player, d = p.data, markers = [];
    for (const id of d.discovered.shrines) { const s = this.content.shrines[id]; if (s && Math.hypot(s.x - p.pos.x, s.z - p.pos.z) < 700) markers.push({ kind: 'shrine', x: s.x, z: s.z, name: s.name }); }
    for (const m of this.quests.markers()) if (m.tracked) markers.push({ kind: 'quest', x: m.x, z: m.z, name: m.name });
    if (this.boss) markers.push({ kind: 'boss', x: this.boss.pos.x, z: this.boss.pos.z, name: this.boss.def.name });
    return { yaw: this.cam.yaw, markers };
  }

  map() {
    const p = this.player, d = p.data;
    return {
      image: this.world.mapImage, player: { x: p.pos.x, z: p.pos.z, yaw: p.yaw },
      shrines: Object.values(this.content.shrines).map(s => ({ id: s.id, name: s.name, x: s.x, z: s.z, found: d.discovered.shrines.includes(s.id) })),
      pois: this.world.pois.map(o => ({ id: o.id, name: o.name, type: o.type, x: o.x, z: o.z, found: d.discovered.pois.includes(o.id) })),
      quests: this.quests.markers(),
    };
  }

  _region(silent) {
    const p = this.player, d = p.data, w = this.world;
    const key = BIOME_KEYS[w.biome(p.pos.x, p.pos.z)] || 'meadow';
    if (key !== this.region.id && key !== 'ocean') {
      this.region = { id: key, name: REGIONS[key].name };
      if (!d.discovered.regions.includes(key)) {
        d.discovered.regions.push(key);
        if (!silent) { bus.emit('discover', { name: REGIONS[key].name, sub: REGIONS[key].desc || '' }); this.sfx('ui_discover'); p.addXp(80); }
        const cx = { forest: 'sombreronce', swamp: 'fangemort', mountain: 'givrelame', ash: 'calcinees', citadel: 'citadelle' }[key];
        if (cx) this.discoverCodex(cx);
      } else if (!silent) bus.emit('discover', { name: REGIONS[key].name, sub: '' });
    }
    for (const poi of w.pois) {
      if (d.discovered.pois.includes(poi.id)) continue;
      if (Math.hypot(poi.x - p.pos.x, poi.z - p.pos.z) < poi.r + 25) {
        d.discovered.pois.push(poi.id);
        if (!silent && poi.type !== 'arena' && poi.type !== 'citadel') { bus.emit('discover', { name: poi.name, sub: 'Lieu découvert' }); this.sfx('ui_discover'); p.addXp(60); }
        const cx = { port_brisants: 'port', roc_au_vent: 'rocauvent', refuge: 'refuge', vieux_gue: 'vieuxgue' }[poi.id];
        if (cx) this.discoverCodex(cx);
      }
    }
  }

  // ------------------------------------------------------------------ weather / ambience
  _weather(dt) {
    const W = this.weather, a = this.engine.atmo, biome = this.region.id;
    W.t -= dt;
    if (W.t <= 0) {
      const r = Math.random();
      const wet = biome === 'swamp' ? 0.25 : biome === 'mountain' ? 0.15 : biome === 'ash' ? -0.2 : 0;
      if (r < 0.42 - wet) { W.kind = 'clear'; W.target = { cover: 0.25 + Math.random() * 0.25, overcast: 0, rain: 0, wind: 0.7 + Math.random() * 0.5 }; }
      else if (r < 0.72 - wet * 0.5) { W.kind = 'cloudy'; W.target = { cover: 0.55 + Math.random() * 0.15, overcast: 0.25, rain: 0, wind: 1.0 + Math.random() * 0.5 }; }
      else if (r < 0.88) { W.kind = 'overcast'; W.target = { cover: 0.85, overcast: 0.7, rain: biome === 'ash' ? 0 : 0.25, wind: 1.3 }; }
      else { W.kind = 'storm'; W.target = { cover: 0.95, overcast: 0.95, rain: biome === 'ash' ? 0 : 1, wind: 1.9 }; }
      W.t = 150 + Math.random() * 260;
    }
    const k = Math.min(dt * 0.06, 1), T = W.target;
    a.cloudCoverage += (T.cover - a.cloudCoverage) * k;
    a.overcast += (T.overcast - a.overcast) * k;
    W.rain += (T.rain - W.rain) * k;
    U.uWind.value.z += (T.wind - U.uWind.value.z) * k;
    U.uWet.value += ((W.rain > 0.15 ? 1 : 0) - U.uWet.value) * Math.min(dt * 0.05, 1);
    const fog = { swamp: [2.6, 0.72, 0.9, 0.7], forest: [1.5, 0.85, 1.0, 0.85], ash: [2.0, 1.1, 0.8, 0.65], mountain: [0.8, 0.95, 1.0, 1.08], citadel: [1.6, 0.8, 0.85, 1.0] }[biome] || [1, 1, 1, 1];
    a.fogMul = fog[0] * (1 + W.rain * 1.5); a.fogTint.setRGB(fog[1], fog[2], fog[3]);
    if (W.kind === 'storm' && Math.random() < dt * 0.06 && this.audio) { this.audio.thunder(Math.random()); this.engine.pipeline.flash = 0.5; }
    // rain streaks around the camera
    if (W.rain > 0.08) {
      const c = this.engine.camera.position, n = Math.round(W.rain * 14 * this.vfx.density);
      const snow = biome === 'mountain' && c.y > 150;
      for (let i = 0; i < n; i++) {
        const x = c.x + (Math.random() - 0.5) * 34, z = c.z + (Math.random() - 0.5) * 34, y = c.y + 6 + Math.random() * 9;
        if (snow) this.vfx.alp.add(x, y, z, U.uWind.value.x * 2, -2.2, U.uWind.value.y * 2, 3.5, 0.06, 0.06, 0.9, 0.93, 1.0, 0.8, 0, 0, 1);
        else this.vfx.alp.add(x, y, z, U.uWind.value.x * 3, -26, U.uWind.value.y * 3, 0.65, 0.022, 0.022, 0.62, 0.68, 0.78, 0.38, 0, 0, 1, 0.09);
      }
    } else if (biome === 'ash' && Math.random() < dt * 14) {
      const c = this.engine.camera.position;
      this.vfx.alp.add(c.x + (Math.random() - 0.5) * 30, c.y + 4 + Math.random() * 8, c.z + (Math.random() - 0.5) * 30, U.uWind.value.x, -0.7, U.uWind.value.y, 6, 0.05, 0.05, 0.3, 0.28, 0.27, 0.7, 0, 0, 1);
      if (Math.random() < 0.3) this.vfx.puff('ember', c.x + (Math.random() - 0.5) * 30, c.y - 1 + Math.random() * 3, c.z + (Math.random() - 0.5) * 30);
    } else if (biome === 'forest' && this.nightFactor > 0.5 && Math.random() < dt * 5) {
      const c = this.engine.camera.position;
      this.vfx.add.add(c.x + (Math.random() - 0.5) * 26, this.world.height(c.x, c.z) + 0.5 + Math.random() * 2, c.z + (Math.random() - 0.5) * 26, (Math.random() - 0.5) * 0.4, (Math.random() - 0.5) * 0.2, (Math.random() - 0.5) * 0.4, 3 + Math.random() * 2, 0.05, 0.05, 1.6, 2.2, 0.5, 0.9, 0, 0);
    }
  }

  _audio(dt) {
    const au = this.audio;
    if (!au) return;
    const p = this.player, cam = this.engine.camera, a = this.engine.atmo;
    cam.getWorldDirection(_v);
    au.setListener([cam.position.x, cam.position.y, cam.position.z], [_v.x, _v.y, _v.z]);
    this.musicT -= dt;
    if (this.musicT > 0) return;
    this.musicT = 0.5;
    let inVillage = false;
    for (const s of this.content.safe) if (Math.hypot(p.pos.x - s[0], p.pos.z - s[1]) < s[2] - 20) inVillage = true;
    const biome = { meadow: 'meadow', beach: 'coast', forest: 'forest', swamp: 'swamp', mountain: 'mountain', ash: 'ash', citadel: 'citadel', ocean: 'coast' }[this.region.id] || 'meadow';
    let water = clamp(1 - Math.abs(this.world.height(p.pos.x, p.pos.z)) / 6, 0, 1) * (biome === 'swamp' ? 0.5 : 1);
    if (this.waterLevel(p.pos.x, p.pos.z) > 0.1) water = 1;
    let danger = 0, fighting = 0;
    for (const e of this.enemies) if (!e.dead && e.aggro) { fighting++; danger = Math.max(danger, 1 - e.distTo(p) / 30); }
    au.setAmbience({ biome: inVillage ? 'village' : biome, hour: a.hour, rain: this.weather.rain, wind: clamp((U.uWind.value.z - 0.5) / 1.5, 0, 1), water, danger });
    if (p.dead) return;
    if (this.boss) au.setMusic('boss', { boss: this.boss.bossId, intensity: this.boss.phase > 1 ? 1 : 0.45 });
    else if (fighting) au.setMusic('combat', { biome, intensity: clamp(0.25 + fighting * 0.2 + (1 - p.hp / p.maxHp) * 0.4, 0, 1) });
    else if (inVillage) au.setMusic('village', { biome });
    else au.setMusic('explore', { biome });
  }

  // ------------------------------------------------------------------ frame
  update(dt) {
    const p = this.player;
    if (!p) return;
    const real = dt;
    if (this.hitStopT > 0) { this.hitStopT -= dt; dt *= 0.06; }
    this.time += dt;
    p.data.stats.time += real;
    this.nightFactor = this.engine.atmo.night;
    const pipe = this.engine.pipeline;
    pipe.hurt.w = Math.max(0, pipe.hurt.w - real * 1.6);
    const low = p.hp / p.maxHp;
    if (!p.dead && low < 0.3) pipe.hurt.w = Math.max(pipe.hurt.w, (0.3 - low) * 1.3 * (0.75 + 0.25 * Math.sin(this.time * 5)));
    if (this._fadeIn > 0) { this._fadeIn -= real; pipe.fade = clamp(this._fadeIn / 0.8, 0, 1); }
    if (this.deathT >= 0) {
      this.deathT += real;
      pipe.desat = clamp(this.deathT / 1.5, 0, 1);
      if (this.deathT > 3.2) pipe.fade = clamp((this.deathT - 3.2) / 1.0, 0, 1);
      if (this.deathT > 4.6) this._respawn();
    }
    p.update(dt);
    U.uPlayerPos.value.copy(p.pos);
    // boss arena keeps the player in
    if (this.boss) {
      const b = this.boss, dx = p.pos.x - b.home.x, dz = p.pos.z - b.home.z, d = Math.hypot(dx, dz), m = b.arenaR - 0.6;
      if (d > m) { p.pos.x = b.home.x + dx / d * m; p.pos.z = b.home.z + dz / d * m; }
    }
    // enemies
    const en = this.enemies;
    for (let i = en.length - 1; i >= 0; i--) {
      const e = en[i];
      if (e.remove) { en.splice(i, 1); e.dispose(); continue; }
      const d = e.distTo(p);
      e.model.root.visible = d < 150;
      if (d < 90 || e.aggro) e.update(dt);
      else if (!e.dead) { e.syncModel(); }
    }
    // soft separation between bodies
    for (let i = 0; i < en.length; i++) {
      const a = en[i];
      if (a.dead) continue;
      for (let j = i + 1; j < en.length; j++) {
        const b = en[j];
        if (b.dead) continue;
        const dx = b.pos.x - a.pos.x, dz = b.pos.z - a.pos.z, rr = a.radius + b.radius, d2 = dx * dx + dz * dz;
        if (d2 < rr * rr && d2 > 1e-6) { const d = Math.sqrt(d2), push = (rr - d) * 0.5 / d, wa = b.weight / (a.weight + b.weight), wb = 1 - wa; a.pos.x -= dx * push * wa * 2; a.pos.z -= dz * push * wa * 2; b.pos.x += dx * push * wb * 2; b.pos.z += dz * push * wb * 2; }
      }
      if (!p.dead && p.invuln <= 0) {
        const dx = p.pos.x - a.pos.x, dz = p.pos.z - a.pos.z, rr = a.radius + p.radius, d2 = dx * dx + dz * dz;
        if (d2 < rr * rr && d2 > 1e-6) { const d = Math.sqrt(d2), push = (rr - d) / d, wp = clamp(a.weight / (a.weight + 1), 0.3, 0.95); p.pos.x += dx * push * wp; p.pos.z += dz * push * wp; a.pos.x -= dx * push * (1 - wp); a.pos.z -= dz * push * (1 - wp); }
      }
    }
    for (const n of this.npcs) { const nd = n.distTo(p); n.model.root.visible = nd < 130; n.update(dt, nd < 130); }   // animated whenever visible (never a frozen T-pose in the distance)
    this._projectiles(dt);
    this._hazards(dt);
    // loot orbs, chest lids, gate
    for (const l of this.loot) { l.t += dt; l.mesh.rotation.y += dt * 2; l.mesh.position.y = l.y + 0.6 + Math.sin(l.t * 3) * 0.08; if (Math.random() < dt * 3) this.vfx.puff('glow', l.x, l.y + 0.6, l.z, 0.5); }
    for (const c of this.content.chests) if (c.opening > 0 && c.opening < 1) { c.opening = Math.min(1, c.opening + dt * 1.6); if (c.lid) c.lid.rotation.x = -1.9 * (1 - Math.pow(1 - c.opening, 3)); }
    const wm = this.content.named['hautefeuille.windmill'];
    if (wm && wm.rot.ROT_blades) wm.rot.ROT_blades.rotateZ(dt * 0.3 * U.uWind.value.z);
    const gb = this.gateBarrier;
    if (gb && !gb.open && p.data.shards.length >= 4 && Math.hypot(p.pos.x - gb.mesh.position.x, p.pos.z - gb.mesh.position.z) < 14) this._openGate(false);
    if (gb && gb.fade > 0) { gb.fade -= dt * 0.6; gb.mat.uniforms.uAlpha.value = Math.max(gb.fade, 0); if (gb.fade <= 0) gb.mesh.visible = false; }
    // periodic systems
    this.spawnT -= real;
    if (this.spawnT <= 0) { this.spawnT = 0.5; this._updateSpawns(); this._region(false); this.quests._check(); }
    this._updateFocus();
    this._weather(real);
    this.cam.update(real);
    this.vfx.update(dt, this.engine.camera);
    this._audio(real);
    this.saveT += real;
    if (this.saveT > 180 && this.settings.get('autosave') && !this.boss && p.combatT <= 0 && !p.dead) { this.saveT = 0; this.save(0); }
    if (pipe.flash > 0) pipe.flash = Math.max(0, pipe.flash - real * 3);
  }

  _projectiles(dt) {
    const list = this.projectiles, p = this.player;
    for (let i = list.length - 1; i >= 0; i--) {
      const o = list[i];
      o.life -= dt;
      const ox = o.x, oy = o.y, oz = o.z;
      o.vy -= o.grav * dt;
      o.x += o.vx * dt; o.y += o.vy * dt; o.z += o.vz * dt;
      this.vfx.puff(o.kind === 'fire' && o.grav ? 'fire' : o.kind, o.x, o.y, o.z, 0.8);
      const lc = o.kind === 'fire' || o.kind === 'meteor' ? [1, 0.5, 0.15] : o.kind === 'venom' ? [0.4, 1, 0.2] : o.kind === 'dawn' ? [1, 0.9, 0.6] : [0.4, 0.7, 1];
      this.vfx.light(o.x, o.y, o.z, lc[0], lc[1], lc[2], 12, 9);
      let hit = o.life <= 0 || this.collision.sweep(ox, oy, oz, o.x, o.y, o.z, 0.15, 3) < 1;
      let direct = null;
      if (!hit) {
        if (o.team === 'enemy') { if (!p.dead && Math.hypot(p.pos.x - o.x, p.pos.z - o.z) < p.radius + 0.35 && o.y > p.pos.y - 0.2 && o.y < p.pos.y + 2) { hit = true; direct = p; } }
        else for (const e of this.enemies) if (!e.dead && Math.hypot(e.pos.x - o.x, e.pos.z - o.z) < e.radius + 0.4 && o.y > e.pos.y - 0.3 && o.y < e.pos.y + e.height + 0.3) { hit = true; direct = e; break; }
      }
      if (!hit) continue;
      list.splice(i, 1);
      _v.set(o.x, o.y - 1, o.z);
      this.vfx.burst(o.kind === 'venom' ? 'poison' : o.kind === 'frost' || o.kind === 'ice' ? 'ice' : o.kind === 'dawn' ? 'magic' : 'fire', _v, o.team === 'player' ? o.radius * 0.6 : 0.8, [2.4, 2.0, 1.0]);
      this.sfx('spell_impact', _v);
      if (o.team === 'enemy') { if (direct) p.takeHit({ dmg: o.dmg, poise: o.poise, from: o.from && !o.from.dead ? o.from : null, pos: _v2.set(ox, oy, oz), status: o.status, ranged: true, knock: 2 }); }
      else for (const e of this.enemies) if (!e.dead && Math.hypot(e.pos.x - o.x, e.pos.z - o.z) < o.radius + e.radius) e.takeHit({ dmg: o.dmg * (e === direct ? 1 : 0.6), poise: 25, from: o.from, status: o.status, skill: true });
    }
  }

  _hazards(dt) {
    const list = this.hazards, p = this.player;
    for (let i = list.length - 1; i >= 0; i--) {
      const h = list[i];
      h.t += dt;
      if (h.type === 'blast') {
        if (!h.tele && h.t >= h.delay - 0.9) { h.tele = true; this.vfx.telegraph(h.x, h.y, h.z, h.radius, Math.min(0.9, h.delay), h.fx === 'ice' ? 0x66ccff : 0xff5a1a); }
        if (h.falling && h.t > h.delay - 0.5 && h.t < h.delay) { const k = (h.delay - h.t) / 0.5; this.vfx.puff(h.falling, h.x + k * 3, h.y + k * 22, h.z + k * 2, 1.4); }
        if (h.t < h.delay) continue;
        list.splice(i, 1);
        _v.set(h.x, h.y, h.z);
        this.vfx.burst(h.fx, _v, h.radius * 0.6); this.vfx.burst('slam', _v, h.radius * 0.7);
        this.sfx(h.fx === 'ice' ? 'spell_ice' : 'spell_impact', _v);
        this.vfx.light(h.x, h.y + 1, h.z, 1, 0.5, 0.2, 40, 14);
        if (h.team === 'enemy') { if (!p.dead && Math.hypot(p.pos.x - h.x, p.pos.z - h.z) < h.radius + 0.2) p.takeHit({ dmg: h.dmg, poise: 40, pos: _v, status: h.status, unblockable: true, from: null }); if (Math.hypot(p.pos.x - h.x, p.pos.z - h.z) < 14) this.cam.shake(0.25); }
        else for (const e of this.enemies) if (!e.dead && Math.hypot(e.pos.x - h.x, e.pos.z - h.z) < h.radius + e.radius) e.takeHit({ dmg: h.dmg, poise: 50, from: h.from, status: h.status, skill: true });
      } else if (h.type === 'wave') {
        const d = h.t * h.speed;
        if (d > h.range) { list.splice(i, 1); continue; }
        const wx = h.x + h.dx * d, wz = h.z + h.dz * d, wy = this.collision.ground(wx, wz);
        for (let k = -1; k <= 1; k++) { this.vfx.alp.add(wx - h.dz * k * h.width * 0.4, wy + 0.4, wz + h.dx * k * h.width * 0.4, h.dx * 3, 2.5, h.dz * 3, 0.5, 0.5, 1.4, 0.2, 0.32, 0.36, 0.6, 1, 6, 0); this.vfx.puff('frost', wx - h.dz * k * h.width * 0.4, wy + 0.5, wz + h.dx * k * h.width * 0.4, 1.2); }
        const test = (a) => { const rx = a.pos.x - wx, rz = a.pos.z - wz; return Math.abs(rx * h.dx + rz * h.dz) < 1.4 && Math.abs(-rx * h.dz + rz * h.dx) < h.width * 0.5 + a.radius; };
        if (h.team === 'enemy') { if (!p.dead && !h.hit.has(p) && test(p)) { h.hit.add(p); p.takeHit({ dmg: h.dmg, poise: 90, pos: _v.set(h.x, wy, h.z), status: h.status, knockdown: true, from: h.from }); } }
        else for (const e of this.enemies) if (!e.dead && !h.hit.has(e) && test(e)) { h.hit.add(e); e.takeHit({ dmg: h.dmg, poise: 120, from: h.from, skill: true, heavy: true }); }
      }
    }
  }
}

export { newPlayerData };
