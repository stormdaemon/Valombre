// Enemies and bosses: perception, movement behaviours, attack timelines, phases.
import * as THREE from 'three';
import { Actor } from './actor.js';
import { RIG_CLIPS } from './data/anims.js';
import { mitigate, DIFFICULTY } from './data/rules.js';
import { bus } from '../core/events.js';
import { angleDelta, clamp } from '../core/rng.js';

const _v = new THREE.Vector3();
const rnd = (a, b) => a + Math.random() * (b - a);

export class Enemy extends Actor {
  constructor(game, defId, def, opts = {}) {
    super(game);
    this.defId = defId; this.def = def;
    this.isBoss = !!opts.boss;
    this.key = opts.key || null;                 // persistent id (kills are remembered until the next rest)
    this.home = new THREE.Vector3().copy(opts.home || this.pos);
    this.arenaR = opts.arenaR || 0;
    const diff = DIFFICULTY[game.settings.get('difficulty')] || DIFFICULTY.normal;
    this.maxHp = this.hp = Math.round(def.hp * diff.enemyHp);
    this.dmg = def.dmg;
    this.radius = def.radius; this.height = def.height; this.weight = def.weight || 1;
    this.poiseMax = def.poise;
    this.floats = !!def.floats;
    this.statusThreshold = this.isBoss ? 80 : 24;
    this.state = 'idle'; this.stateT = 0;
    this.aggro = false; this.alertT = 0;
    this.cds = {}; this.globalCd = rnd(0.2, 1.0);
    this.atk = null; this.lastAtk = null; this.lastAtkT = 9;
    this.strafe = Math.random() < 0.5 ? 1 : -1; this.strafeT = rnd(1, 3);
    this.thinkT = Math.random() * 0.3;
    this.wanderT = rnd(2, 8); this.wanderTo = null;
    this.retreatT = 0;
    this.phase = 1; this.enrage = 1;
    this.vulnerableT = 0;       // riposte window after being parried / poise broken
    this.hasToken = false;
    this.fadeT = -1;
    this.hitBy = 0;             // swing id of the last player swing that touched us
    this.speedNow = 0;
    this.moveDir = new THREE.Vector2();
    const rig = def.rig === 'humanoid' ? (def.monster ? 'humanoid_monster' : 'humanoid') : def.rig;
    this.clips = { ...RIG_CLIPS[rig] };
    if (rig === 'humanoid' && def.moveset === '2h') this.clips.idleCombat = 'idle_2h'; else if (rig === 'humanoid') this.clips.idleCombat = 'idle_combat';
    this.humanoid = def.rig === 'humanoid';
    this.barT = 0;              // show the health bar while > 0
    this.stepT = 0;
  }

  setState(s) { this.state = s; this.stateT = 0; }
  get player() { return this.game.player; }

  spawnAt(x, z, yaw = Math.random() * 6.283) {
    this.pos.set(x, this.game.collision.ground(x, z), z);
    this.home.copy(this.pos);
    this.yaw = yaw;
    this.syncModel();
    this.anim.play(this.clips.idle, 0.01);
  }

  // ------------------------------------------------------------------ perception
  _perceive() {
    const p = this.player;
    if (!p || p.dead) { if (this.aggro) this._calm(); return; }
    const d = this.distTo(p);
    if (!this.aggro) {
      const range = this.def.aggro || (this.isBoss ? this.arenaR : 20);
      if (this.isBoss) { if (d < this.arenaR - 2 && Math.hypot(p.pos.x - this.home.x, p.pos.z - this.home.z) < this.arenaR - 1) this.setAggro(true); return; }
      if (d < range) {
        const front = this.facingOff(p) < 1.9;
        const near = d < 6.5;
        if ((near || front) && (near || this.game.collision.los(this.pos.x, this.pos.y + this.height * 0.8, this.pos.z, p.pos.x, p.pos.y + 1.4, p.pos.z))) this.setAggro(true);
      }
    } else if (!this.isBoss) {
      const hd = Math.hypot(this.pos.x - this.home.x, this.pos.z - this.home.z);
      if (hd > (this.def.leash || 60) && d > 10) this._calm();
      else if (d > 55) this._calm();
    }
  }

  setAggro(shout) {
    if (this.aggro || this.dead) return;
    this.aggro = true; this.barT = 6;
    this.setState('chase');
    const g = this.game;
    if (shout) {
      g.alertNear(this, 15);
      const v = this.def.voice;
      if (v === 'wolf') g.sfx(Math.random() < 0.5 ? 'wolf_growl' : 'wolf_bark', this.pos);
      else if (v === 'spider') g.sfx('spider_hiss', this.pos);
      else if (v === 'undead') g.sfx('undead_moan', this.pos);
      else if (v === 'troll') g.sfx('troll_roar', this.pos);
      else if (v === 'golem') g.sfx('golem_rumble', this.pos);
      else if (v === 'wraith') g.sfx('wraith_wail', this.pos);
      else if (v === 'bones') g.sfx('bones_rattle', this.pos);
      else if (v === 'human') g.sfx('human_grunt', this.pos);
    }
    if (this.isBoss) g.startBoss(this);
  }

  _calm() {
    this.aggro = false; this.atk = null; this._releaseToken();
    this.setState('return');
  }

  _releaseToken() { if (this.hasToken) { this.hasToken = false; this.game.tokens = Math.max(0, this.game.tokens - 1); } }

  // ------------------------------------------------------------------ attacks
  _chooseAttack(d) {
    const list = this.def.attacks, t = this.lastAtkT;
    // combo continuation first
    if (this.lastAtk && t < 0.35) {
      for (const a of list) if (a.chain === this.lastAtk.id && d <= a.range[1] + 0.8 && Math.random() < 0.75) return a;
    }
    if (this.globalCd > 0) return null;
    let best = null, bw = 0;
    for (const a of list) {
      if (a.chain) continue;
      if ((a.phase || 1) > this.phase) continue;
      if ((this.cds[a.id] || 0) > 0) continue;
      if (d < a.range[0] || d > a.range[1]) continue;
      const w = (a.type ? 1.4 : 1) * (0.5 + Math.random());
      if (w > bw) { bw = w; best = a; }
    }
    return best;
  }

  _startAttack(a) {
    const g = this.game, p = this.player, anim = this.anim;
    const melee = !a.type || a.type === 'slam' || a.type === 'charge';
    if (melee && !this.isBoss && !a.chain) {
      if (!this.hasToken) { if (g.tokens >= g.maxTokens) return false; g.tokens++; this.hasToken = true; }
    }
    const speed = (a.speed || 1) * this.enrage * (this.hasStatus('frost') ? 0.75 : 1);
    const dur = anim.duration(a.clip);
    const ev = anim.events(a.clip);
    let hs, he;
    if (anim.has(a.clip) && ev.hit && !a.type) { hs = ev.hit[0]; he = ev.hit[1]; }
    else if (anim.has(a.clip) && (ev.impact != null || ev.release != null) && a.type) { hs = ev.impact ?? ev.release; he = hs + 0.12; }
    else { hs = a.hit[0] * dur; he = Math.max(a.hit[1] * dur, hs + 0.1); }
    this.atk = { a, t: 0, hs, he, dur, speed, done: false, lunged: 0, fired: 0, hitDone: false, dirYaw: this.angleTo(p) };
    this.cds[a.id] = a.cd * rnd(0.85, 1.25) / this.enrage;
    this.yaw = this.atk.dirYaw;
    this.setState('attack');
    anim.playOnce(a.clip, { speed, fade: 0.1 });
    // telegraphs
    const y = this.pos.y;
    if (a.type === 'slam') { const off = Math.min((a.range[1] || 3) * 0.45, a.radius * 0.6); g.vfx.telegraph(this.pos.x + this.fx * off, y, this.pos.z + this.fz * off, a.radius, hs / speed); this.atk.cx = this.pos.x + this.fx * off; this.atk.cz = this.pos.z + this.fz * off; }
    else if (a.type === 'nova') g.vfx.telegraph(this.pos.x, y, this.pos.z, a.radius, hs / speed, 0xff7a2a);
    else if (a.type === 'charge') { this.atk.chargeLeft = a.dist; this.atk.he = 99; }
    if (a.type === 'summon' || a.clip === 'howl' || a.clip === 'm_roar' || a.clip === 'roar' || a.clip === 'rear_up') {
      const v = this.def.voice;
      g.sfx(this.isBoss ? 'boss_roar' : v === 'wolf' ? 'wolf_howl' : v === 'spider' ? 'spider_screech' : 'troll_roar', this.pos);
    } else if (this.def.voice === 'wolf' && Math.random() < 0.4) g.sfx('wolf_growl', this.pos);
    else if (this.def.voice === 'troll' || this.def.voice === 'golem') g.sfx('troll_grunt', this.pos);
    return true;
  }

  _hitPlayer(a, extra = {}) {
    const p = this.player;
    const res = p.takeHit({ dmg: this.dmg * a.dmg * (this.phase > 1 ? 1.08 : 1), poise: a.poise || 20, from: this, status: a.status, knock: 3 + (a.poise || 20) * 0.05, knockdown: (a.poise || 0) >= 80, ...extra });
    return res;
  }

  _updateAttack(dt) {
    const g = this.game, k = this.atk, a = k.a, p = this.player, anim = this.anim;
    k.t += dt * k.speed;
    const t = k.t;
    let vx = 0, vz = 0;
    if (a.type === 'charge') {
      // run in a (nearly) straight line; knock the player down on contact
      if (t > 0.25) {
        const sp = a.speed || 9;
        this.yaw += clamp(angleDelta(this.yaw, this.angleTo(p)), -0.6 * dt, 0.6 * dt);
        vx = this.fx * sp; vz = this.fz * sp;
        k.chargeLeft -= sp * dt;
        if (!anim.busy || anim.oneName !== a.clip) anim.playOnce(a.clip, { fade: 0.1 });
        if (!k.hitDone && this.distTo(p) < this.radius + p.radius + 0.5) { k.hitDone = true; this._hitPlayer(a, { knockdown: true, poise: 100 }); g.cam.shake(0.5); }
        const ox = this.pos.x, oz = this.pos.z;
        this.moveStep(dt, vx, vz);
        const moved = Math.hypot(this.pos.x - ox, this.pos.z - oz);
        if (k.chargeLeft <= 0 || moved < sp * dt * 0.3 || k.hitDone) { anim.stopOnce(0.2); this._endAttack(1.2); }
        if (this.isBoss) this._keepInArena();
        return;
      }
      this.turnToward(this.angleTo(p), 6, dt);
      this.moveStep(dt, 0, 0);
      return;
    }
    // tracking before the strike, lunge
    if (t < k.hs) {
      this.turnToward(this.angleTo(p), a.type ? 8 : 5, dt);
      if (a.lunge && t > k.hs * 0.3 && k.lunged < a.lunge && !a.type) {
        const d = this.distTo(p) - this.radius - p.radius;
        let sp = a.lunge / Math.max((k.hs * 0.7) / k.speed, 0.08);
        if (d < 0.5) sp = 0;
        k.lunged += sp * dt; vx = this.fx * sp; vz = this.fz * sp;
      }
    } else if (a.lunge > 3 && t < k.he && k.lunged < a.lunge) {
      const sp = a.lunge / Math.max((k.he * 0.8) / k.speed, 0.1);
      k.lunged += sp * dt; vx = this.fx * sp; vz = this.fz * sp;
    }
    this.moveStep(dt, vx, vz);
    if (this.isBoss) this._keepInArena();
    // effect
    if (!a.type) {
      if (t >= k.hs && t <= k.he && !k.hitDone) {
        const reach = a.range[1] + 0.55 + this.radius * 0.3 + p.radius;
        if (this.distTo(p) <= reach && this.facingOff(p) <= (a.arc || 110) * Math.PI / 360 + 0.15) { k.hitDone = true; this._hitPlayer(a); }
      }
    } else if (!k.done && t >= k.hs) {
      const y = this.pos.y;
      if (a.type === 'slam' || a.type === 'nova') {
        k.done = true;
        const cx = a.type === 'slam' ? k.cx : this.pos.x, cz = a.type === 'slam' ? k.cz : this.pos.z;
        const d = Math.hypot(p.pos.x - cx, p.pos.z - cz);
        g.vfx.burst(a.type === 'nova' ? (a.status && a.status[0] === 'frost' ? 'ice' : 'fire') : 'slam', _v.set(cx, y, cz), a.radius);
        g.sfx(a.type === 'nova' ? 'spell_impact' : 'golem_slam', this.pos);
        g.cam.shake(clamp(1.2 - d / 18, 0.1, 0.8));
        if (d < a.radius + p.radius * 0.5 && p.pos.y < y + 2.2) this._hitPlayer(a, { pos: _v.set(cx, y, cz), unblockable: a.type === 'nova' });
      } else if (a.type === 'projectile') {
        const n = a.burst || 1;
        const idx = Math.floor((t - k.hs) / 0.2);
        while (k.fired <= idx && k.fired < n) { g.spawnProjectile(this, a, k.fired, n); k.fired++; }
        if (k.fired >= n) k.done = true;
      } else if (a.type === 'summon') {
        k.done = true;
        g.summon(this, a.summon, a.count);
      } else if (a.type === 'blink') {
        k.done = true;
        g.vfx.burst('magic', this.pos, 1.5, [2.2, 0.8, 0.3]);
        const ang = Math.random() * 6.283, r = Math.min(this.arenaR * 0.6, 14);
        let nx = this.home.x + Math.cos(ang) * r, nz = this.home.z + Math.sin(ang) * r;
        if (Math.hypot(nx - p.pos.x, nz - p.pos.z) < 6) { nx = this.home.x - Math.cos(ang) * r; nz = this.home.z - Math.sin(ang) * r; }
        this.pos.set(nx, g.collision.ground(nx, nz), nz);
        this.yaw = this.angleTo(p);
        g.vfx.burst('magic', this.pos, 1.5, [2.2, 0.8, 0.3]);
        g.sfx('spell_dark', this.pos);
      } else if (a.type === 'rain' || a.type === 'pillars') {
        k.done = true;
        g.hazardRain(this, a);
      } else if (a.type === 'wave') {
        k.done = true;
        g.hazardWave(this, a);
      }
    }
    if (t >= k.dur - 0.03 || (!anim.busy && t > k.he)) this._endAttack();
  }

  _endAttack(extraCd = 0) {
    const a = this.atk ? this.atk.a : null;
    this.lastAtk = a; this.lastAtkT = 0;
    this.atk = null;
    const b = this.def.behavior;
    this.globalCd = (this.isBoss ? rnd(0.35, 0.9) : b === 'brute' ? rnd(0.9, 1.6) : b === 'shambler' ? rnd(0.5, 1.2) : rnd(0.7, 1.7)) / this.enrage + extraCd;
    if (b === 'skirmisher' || b === 'pack') this.retreatT = rnd(0.5, 1.2);
    if (!this.isBoss && Math.random() < 0.6) this._releaseToken();
    this.setState('combat');
  }

  _keepInArena() {
    if (!this.arenaR) return;
    const dx = this.pos.x - this.home.x, dz = this.pos.z - this.home.z, d = Math.hypot(dx, dz), m = this.arenaR - this.radius - 1;
    if (d > m) { this.pos.x = this.home.x + dx / d * m; this.pos.z = this.home.z + dz / d * m; }
  }

  // ------------------------------------------------------------------ damage
  /** hit: { dmg, poise, from, heavy, status, crit, type } -> { dmg, killed, blocked } */
  takeHit(hit) {
    if (this.dead) return { dmg: 0 };
    if (this.invuln > 0) return { dmg: 0, immune: true };
    const g = this.game;
    if (!this.aggro) { this.setAggro(true); hit.dmg *= 1.6; hit.sneak = true; }
    this.barT = 8;
    let dmg = hit.dmg, blocked = false;
    if (this.vulnerableT > 0 && !hit.dot) { dmg *= 1.8; hit.crit = true; }
    // guards
    if (this.def.blocks && this.state === 'combat' && !hit.heavy && !hit.skill && hit.from && this.facingOff(hit.from) < 1.1 && Math.random() < this.def.blocks) {
      blocked = true; dmg *= 0.2;
      this.anim.playOnce('block_hit', { fade: 0.04 });
      g.sfx('block_shield', this.pos); g.vfx.burst('spark', this.pos, 1.1);
    }
    dmg = Math.max(1, Math.round(mitigate(dmg, this.def.def || 0)));
    this.hp -= dmg;
    this.flash = 0.15;
    if (hit.status && !blocked) this.applyStatus(hit.status[0], hit.status[1]);
    bus.emit('damage', { x: this.pos.x, y: this.pos.y + this.height * 0.9, z: this.pos.z, dmg, crit: !!hit.crit, blocked });
    if (!blocked) {
      const fxk = this.def.hitSfx === 'hit_bone' ? 'bone' : this.def.hitSfx === 'hit_stone' ? 'stone' : this.def.hitSfx === 'hit_chitin' ? 'ichor' : this.def.hitSfx === 'hit_armor' ? 'spark' : this.floats ? 'magic' : 'blood';
      g.vfx.burst(fxk, this.pos, Math.min(this.height, 2.2) * 0.55);
      if (hit.crit) g.vfx.burst('crit', this.pos, Math.min(this.height, 2.2) * 0.6);
      g.sfx(hit.crit ? 'crit' : this.def.hitSfx || 'hit_flesh', this.pos);
    }
    if (this.hp <= 0) { this.hp = 0; this.die(hit.from); return { dmg, killed: true }; }
    if (hit.from) { const yaw = Math.atan2(this.pos.x - hit.from.pos.x, this.pos.z - hit.from.pos.z); const kb = (hit.heavy ? 4.5 : 2.2) / Math.max(this.weight, 0.5); this.knock.x += Math.sin(yaw) * kb; this.knock.z += Math.cos(yaw) * kb; }
    if (!blocked) {
      const broke = this.addPoise((hit.poise || 10));
      const hyper = this.state === 'attack' && (this.isBoss || this.def.behavior === 'brute' || this.def.poise >= 100);
      if (broke || (!hyper && !this.isBoss && this.def.poise < 60 && this.state !== 'stagger')) this._stagger(broke ? (this.isBoss ? 1.6 : 1.0) : 0.35, broke);
      const v = this.def.voice;
      if (Math.random() < 0.5) g.sfx(v === 'wolf' ? 'wolf_hurt' : v === 'undead' ? 'undead_hurt' : v === 'troll' || v === 'golem' ? 'troll_hurt' : v === 'human' ? 'human_hurt' : v === 'spider' ? 'spider_hiss' : 'bones_rattle', this.pos);
    }
    return { dmg, blocked };
  }

  _stagger(time, heavy) {
    this.atk = null; this._releaseToken();
    this.setState('stagger');
    this.staggerT = time;
    if (heavy) this.vulnerableT = time + 0.4;
    this.anim.playOnce(heavy ? this.clips.stagger : this.clips.hit, { fade: 0.05 });
  }

  onParried() {
    this._stagger(1.5, true);
    this.vulnerableT = 2.0;
    this.cds = {};
  }

  die(from) {
    if (this.dead) return;
    this.dead = true; this.atk = null; this._releaseToken();
    this.setState('dead');
    this.anim.setUpper && this.anim.setUpper(null);
    this.anim.playOnce(this.clips.death, { fade: 0.08, hold: true });
    this.fadeT = this.isBoss ? 5 : 7;
    const v = this.def.voice;
    this.game.sfx(this.isBoss ? 'boss_death' : v === 'wolf' ? 'wolf_death' : v === 'spider' ? 'spider_death' : v === 'undead' ? 'undead_death' : v === 'troll' || v === 'golem' ? 'troll_death' : v === 'wraith' ? 'wraith_death' : v === 'bones' ? 'bones_rattle' : 'human_death', this.pos);
    this.game.onEnemyKilled(this, from);
  }

  // ------------------------------------------------------------------ update
  update(dt) {
    const g = this.game, p = this.player, anim = this.anim, def = this.def;
    this.stateT += dt;
    this.updateStatus(dt);
    if (this.barT > 0) this.barT -= dt;
    if (this.vulnerableT > 0) this.vulnerableT -= dt;
    if (this.dead) {
      this.moveStep(dt, 0, 0); this.syncModel(); anim.update(dt);
      if (this.fadeT > 0) {
        this.fadeT -= dt;
        if (this.fadeT < 1.2) { const s = Math.max(this.fadeT / 1.2, 0.01); this.model.root.scale.set(1, s, 1); this.model.root.position.y -= (1 - s) * 0.1; }
        if (this.fadeT <= 0) { g.vfx.burst('death', this.pos, Math.min(this.height, 2.5) * 0.5); this.remove = true; }
      }
      return;
    }
    for (const k in this.cds) if (this.cds[k] > 0) this.cds[k] -= dt;
    if (this.globalCd > 0) this.globalCd -= dt;
    this.lastAtkT += dt;
    if (this.retreatT > 0) this.retreatT -= dt;
    this.thinkT -= dt;
    if (this.thinkT <= 0) { this.thinkT = 0.2 + Math.random() * 0.1; this._perceive(); }
    // boss phases
    if (this.isBoss && this.aggro && def.phases && this.phase <= def.phases.length && this.state !== 'attack' && this.state !== 'phase') {
      const ph = def.phases[this.phase - 1];
      if (this.hp / this.maxHp <= ph.at) {
        this.phase++; this.enrage = ph.enrage || 1.1;
        this.setState('phase'); this.invuln = 2.2; this.atk = null;
        const clip = def.rig === 'wolf' ? 'howl' : def.rig === 'spider' ? 'rear_up' : def.monster ? 'm_roar' : 'roar';
        this.phaseDur = anim.playOnce(clip, { fade: 0.15 });
        g.sfx('boss_phase', this.pos); g.sfx('boss_roar', this.pos);
        g.cam.shake(0.7);
        g.vfx.burst('magic', this.pos, 2.5, [2.2, 0.5, 0.3]);
        bus.emit('boss:phase', { boss: this, text: ph.say });
        if (p.distTo(this) < 6) { const yaw = this.angleTo(p); p.knock.set(Math.sin(yaw) * 12, 0, Math.cos(yaw) * 12); }
      }
    }
    let vx = 0, vz = 0, wantAnim = this.clips.idle, animSpeed = 1, faceYaw = null, faceRate = 8;
    const speedMul = this.speedMul * this.enrage;
    switch (this.state) {
      case 'idle': {
        this.wanderT -= dt;
        if (this.wanderT <= 0 && !this.isBoss && def.behavior !== 'ranged') {
          this.wanderT = rnd(5, 14);
          const a = Math.random() * 6.283, r = rnd(2, 7);
          this.wanderTo = [this.home.x + Math.cos(a) * r, this.home.z + Math.sin(a) * r];
        }
        if (this.wanderTo) {
          const dx = this.wanderTo[0] - this.pos.x, dz = this.wanderTo[1] - this.pos.z, d = Math.hypot(dx, dz);
          if (d < 0.5 || this.stateT > 30) { this.wanderTo = null; this.stateT = 0; }
          else { const sp = def.walk; vx = dx / d * sp; vz = dz / d * sp; faceYaw = Math.atan2(dx, dz); wantAnim = this.clips.walk; animSpeed = sp / (anim.clipSpeed(this.clips.walk) || sp); }
        }
        break;
      }
      case 'return': {
        const dx = this.home.x - this.pos.x, dz = this.home.z - this.pos.z, d = Math.hypot(dx, dz);
        this.hp = Math.min(this.maxHp, this.hp + this.maxHp * 0.25 * dt);
        if (d < 1.2) { this.setState('idle'); break; }
        const sp = def.speed * 0.8 * speedMul;
        vx = dx / d * sp; vz = dz / d * sp; faceYaw = Math.atan2(dx, dz); wantAnim = this.clips.run; animSpeed = sp / (anim.clipSpeed(this.clips.run) || sp);
        break;
      }
      case 'chase': case 'combat': {
        if (!p || p.dead) { this._calm(); break; }
        const d = this.distTo(p) - this.radius - p.radius;
        const toP = this.angleTo(p);
        const a = this.retreatT > 0 ? null : this._chooseAttack(d);
        if (a && this.facingOff(p) < 0.9 && this._startAttack(a)) break;
        const b = def.behavior;
        const melee = def.attacks[0].range[1];
        let desire = 0;         // +1 approach, -1 back off, 0 hold
        let side = 0;
        if (b === 'ranged') {
          const k = def.keep || [6, 12];
          if (d < k[0]) desire = -1; else if (d > k[1]) desire = 1; else side = this.strafe;
        } else if (this.retreatT > 0) { desire = -1; side = this.strafe * 0.6; }
        else if (b === 'brute' || b === 'shambler' || this.isBoss) { desire = d > melee * 0.75 ? 1 : 0; if (this.isBoss && d < melee && this.globalCd > 0.2) side = this.strafe * 0.5; }
        else {
          const waiting = this.globalCd > 0.15 || (!this.hasToken && g.tokens >= g.maxTokens);
          const ring = waiting ? melee + (b === 'pack' ? 2.6 : 1.4) : melee * 0.7;
          if (d > ring + 0.6) desire = 1; else if (d < ring - 0.8 && waiting) desire = -0.7;
          if (waiting && d < ring + 3) side = this.strafe;
        }
        this.strafeT -= dt;
        if (this.strafeT <= 0) { this.strafeT = rnd(1.2, 3.5); if (Math.random() < 0.55) this.strafe = -this.strafe; }
        const run = desire > 0 && d > 5.5;
        const sp = (run ? def.speed : Math.max(def.walk * 1.25, def.speed * 0.45)) * speedMul;
        const fx = Math.sin(toP), fz = Math.cos(toP);
        let mx = fx * desire - fz * side * 0.9, mz = fz * desire + fx * side * 0.9;
        const ml = Math.hypot(mx, mz);
        if (ml > 0.05) { mx /= ml; mz /= ml; vx = mx * sp * Math.min(ml, 1); vz = mz * sp * Math.min(ml, 1); }
        // facing & animation
        if (this.humanoid || this.isBoss || d < 4 || ml < 0.05) faceYaw = toP; else faceYaw = desire >= 0 ? Math.atan2(vx + fx * 2, vz + fz * 2) : toP;
        if (run && !this.humanoid) faceYaw = Math.atan2(vx, vz);
        const moving = Math.hypot(vx, vz);
        if (moving < 0.2) wantAnim = this.clips.idleCombat || this.clips.idle;
        else if (run) { wantAnim = this.clips.run; animSpeed = moving / (anim.clipSpeed(this.clips.run) || moving); }
        else if (this.humanoid && !def.monster && Math.abs(side) > 0.3 && Math.abs(desire) < 0.6 && anim.has('strafe_L')) { wantAnim = side > 0 ? 'strafe_R' : 'strafe_L'; animSpeed = moving / (anim.clipSpeed('strafe_L') || 2); }
        else if (this.humanoid && !def.monster && desire < -0.3 && anim.has('walk_back')) { wantAnim = 'walk_back'; animSpeed = moving / (anim.clipSpeed('walk_back') || 1.2); }
        else { wantAnim = this.clips.walk; animSpeed = moving / (anim.clipSpeed(this.clips.walk) || moving); }
        if (this.state === 'chase' && d < 9) this.setState('combat');
        break;
      }
      case 'attack': this._updateAttack(dt); this.syncModel(); anim.update(dt); return;
      case 'stagger': if (this.stateT >= this.staggerT) this.setState(this.aggro ? 'combat' : 'idle'); wantAnim = null; break;
      case 'phase': if (this.stateT >= (this.phaseDur || 1.6)) { this.setState('combat'); this.globalCd = 0.3; } wantAnim = null; break;
    }
    if (faceYaw !== null) this.turnToward(faceYaw, faceRate, dt);
    this.moveStep(dt, vx, vz);
    if (this.isBoss && this.aggro) this._keepInArena();
    this.speedNow = Math.hypot(vx, vz);
    if (wantAnim && !anim.busy) anim.play(wantAnim, 0.22, clamp(animSpeed || 1, 0.55, 1.7));
    if (def.stepSfx && this.speedNow > 0.5) { this.stepT -= dt * this.speedNow; if (this.stepT <= 0) { this.stepT = 2.6; g.sfx(def.stepSfx, this.pos, { volume: 0.5 }); if (p && this.distTo(p) < 14) g.cam.shake(0.08); } }
    this.syncModel();
    anim.update(dt);
  }
}
