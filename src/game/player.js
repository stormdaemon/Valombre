// The player character: input -> movement / combat state machine, stats, inventory.
import * as THREE from 'three';
import { Actor } from './actor.js';
import { ITEMS } from './data/items.js';
import { ORIGINS, SKILLS, derive, mitigate, xpForLevel, MAX_LEVEL, DIFFICULTY } from './data/rules.js';
import { bus } from '../core/events.js';
import { angleDelta, clamp, damp } from '../core/rng.js';

const WALK = 1.7, RUN = 4.7, SPRINT = 7.1, SWIM = 2.3;
const COST = { roll: 22, backstep: 14, jump: 10, sprint: 9.5 };

/** a fresh, serializable player state */
export function newPlayerData(name, originId, appearance) {
  const o = ORIGINS.find(x => x.id === originId) || ORIGINS[0];
  const d = {
    name: name || 'Veilleur', origin: o.id, appearance: appearance || {},
    level: 1, xp: 0, attrPoints: 0, attrs: { ...o.attrs },
    hp: 1, stamina: 1, mana: 1, gold: o.gold,
    flasks: 3, flaskMax: 3, flaskLevel: 0,
    equipment: { weapon: null, offhand: null, head: null, chest: null, legs: null },
    inventory: [],            // [{ id, qty, up }]
    skills: [], skillSlots: [null, null, null], shards: [],
    pos: null, yaw: 0, lastShrine: 's_hautefeuille',
    discovered: { shrines: ['s_hautefeuille'], pois: [], lore: [], regions: [] },
    quests: {}, flags: {}, killed: {}, opened: {},
    stats: { kills: 0, deaths: 0, bosses: 0, time: 0 }, hour: 8.5, day: 1,
  };
  for (const slot in o.gear) d.equipment[slot] = { id: o.gear[slot], up: 0 };
  for (const [id, qty] of o.items) d.inventory.push({ id, qty, up: 0 });
  d.inventory.push({ id: 'torch', qty: 1, up: 0 });
  if (o.skill) { d.skills.push(o.skill); d.skillSlots[0] = o.skill; }
  const st = derive(d);
  d.hp = st.maxHp; d.stamina = st.maxSt; d.mana = st.maxMana;
  return d;
}

export class Player extends Actor {
  constructor(game, data) {
    super(game);
    this.team = 'player';
    this.avoidWater = false;
    this.data = data;
    this.st = derive(data);
    this.radius = 0.38;
    this.state = 'free';
    this.stateT = 0;
    this.speed = 0;
    this.vel = new THREE.Vector2();
    this.moveYaw = 0;
    this.combo = 0; this.comboT = 0;
    this.atk = null;
    this.buffer = null; this.bufferT = 0;
    this.blocking = false; this.blockT = 0;
    this.staminaDelay = 0;
    this.target = null;                 // lock-on target
    this.combatT = 0;                   // > 0 while "in combat"
    this.buffs = {};                    // name -> { t, mult }
    this.regen = { rate: 0, t: 0 };
    this.sheathed = false;
    this.hyper = false;
    this.rollDir = 0; this.rollDist = 0;
    this.skillCd = {};
    this.stepT = 0;
    this.riposteT = 0;
    this.interactLock = 0;
    this.hp = data.hp; this.maxHp = this.st.maxHp;
    this.statusThreshold = 30;
    this.poiseMax = this.st.poise;
  }

  // ------------------------------------------------------------------ stats / inventory
  refresh() {
    this.st = derive(this.data);
    this.maxHp = this.st.maxHp;
    this.poiseMax = this.st.poise;
    this.hp = Math.min(this.hp, this.maxHp);
    this.data.stamina = Math.min(this.data.stamina, this.st.maxSt);
    this.data.mana = Math.min(this.data.mana, this.st.maxMana);
    bus.emit('player:stats');
  }

  get twoHanded() { return !!(this.st.weapon && this.st.weapon.moveset === '2h'); }

  count(id) { let n = 0; for (const it of this.data.inventory) if (it.id === id) n += it.qty; return n; }

  addItem(id, qty = 1, up = 0, silent = false) {
    const def = ITEMS[id];
    if (!def) return;
    if (id === 'flask') return;
    const inv = this.data.inventory;
    const stackable = def.type === 'consumable' || def.type === 'material' || def.type === 'key';
    const ex = stackable ? inv.find(i => i.id === id) : null;
    if (ex) ex.qty += qty; else if (stackable) inv.push({ id, qty, up: 0 }); else for (let i = 0; i < qty; i++) inv.push({ id, qty: 1, up });
    if (!silent) bus.emit('toast', { kind: 'item', id, qty });
    bus.emit('inventory');
    this.game.quests && this.game.quests.onEvent('item', id);
  }

  removeItem(id, qty = 1) {
    const inv = this.data.inventory;
    for (let i = inv.length - 1; i >= 0 && qty > 0; i--) {
      if (inv[i].id !== id) continue;
      const take = Math.min(inv[i].qty, qty);
      inv[i].qty -= take; qty -= take;
      if (inv[i].qty <= 0) inv.splice(i, 1);
    }
    bus.emit('inventory');
    return qty === 0;
  }

  /** equip the inventory entry at `index` (weapon / shield / armor) */
  equip(index) {
    const it = this.data.inventory[index];
    if (!it) return;
    const def = ITEMS[it.id];
    if (!def || !def.slot) return;
    const eq = this.data.equipment;
    this.data.inventory.splice(index, 1);
    if (eq[def.slot]) this.data.inventory.push({ id: eq[def.slot].id, qty: 1, up: eq[def.slot].up || 0 });
    eq[def.slot] = { id: it.id, up: it.up || 0 };
    if (def.slot === 'weapon' && def.moveset === '2h' && eq.offhand) { this.data.inventory.push({ id: eq.offhand.id, qty: 1, up: eq.offhand.up || 0 }); eq.offhand = null; }
    if (def.slot === 'offhand' && this.twoHanded) { /* shield stays on the back while two-handing */ }
    this.refresh(); this.updateGear();
    this.game.sfx('ui_equip');
    bus.emit('inventory');
  }

  unequip(slot) {
    const eq = this.data.equipment;
    if (!eq[slot]) return;
    this.data.inventory.push({ id: eq[slot].id, qty: 1, up: eq[slot].up || 0 });
    eq[slot] = null;
    this.refresh(); this.updateGear();
    bus.emit('inventory');
  }

  updateGear() {
    if (!this.model) return;
    const eq = this.data.equipment;
    this.model.setWeapon(eq.weapon ? eq.weapon.id : null);
    this.model.setShield(eq.offhand && !this.twoHanded ? eq.offhand.id : null);
    const helm = this.game.settings.get('showHelm') !== false;
    if (this.model.setOutfit) this.model.setOutfit({ head: helm && eq.head ? eq.head.id : null, chest: eq.chest && eq.chest.id, legs: eq.legs && eq.legs.id });
  }

  addXp(n) {
    const d = this.data;
    if (d.level >= MAX_LEVEL) return;
    d.xp += Math.round(n);
    let up = false;
    while (d.level < MAX_LEVEL && d.xp >= xpForLevel(d.level)) { d.xp -= xpForLevel(d.level); d.level++; d.attrPoints++; up = true; }
    if (up) {
      this.refresh(); this.hp = this.maxHp; d.stamina = this.st.maxSt;
      this.game.sfx('ui_levelup');
      bus.emit('toast', { kind: 'level', level: d.level });
      this.game.vfx && this.game.vfx.burst('levelup', this.pos);
    }
    bus.emit('player:xp');
  }

  spendPoint(attr) {
    const d = this.data;
    if (d.attrPoints <= 0 || d.attrs[attr] >= 50) return false;
    d.attrPoints--; d.attrs[attr]++;
    const hpRatio = this.hp / this.maxHp;
    this.refresh();
    this.hp = Math.round(this.maxHp * hpRatio);
    return true;
  }

  heal(amount) { this.hp = Math.min(this.maxHp, this.hp + amount); }

  // ------------------------------------------------------------------ helpers
  setState(s) { this.state = s; this.stateT = 0; }

  useStamina(n) { this.data.stamina = Math.max(this.data.stamina - n, -20); this.staminaDelay = this.data.stamina <= 0 ? 1.6 : 0.85; if (this.data.stamina <= 0) this.game.sfx('stamina_empty'); }

  buff(name, mult, time) { this.buffs[name] = { t: time, mult }; bus.emit('player:buffs'); }
  buffMult(name) { const b = this.buffs[name]; return b && b.t > 0 ? b.mult : 1; }

  queue(action) { this.buffer = action; this.bufferT = 0.28; }

  wishDir(out) {
    const inp = this.game.input, cy = this.game.cam.yaw;
    const fx = Math.sin(cy), fz = Math.cos(cy);
    out.set(fx * inp.moveY - fz * inp.moveX, fz * inp.moveY + fx * inp.moveX);
    return out;
  }

  // ------------------------------------------------------------------ actions
  tryAttack(kind) {
    if (this.data.stamina <= 0) return false;
    if (this.swimming) return false;
    const w = this.st.weapon, two = this.twoHanded;
    const a = { kind, hit: new Set(), done: false, whooshed: false, lunged: 0 };
    if (kind === 'light') {
      const step = this.combo % 3;
      a.clip = (two ? 'atk2h_' : 'atk1h_') + (step + 1);
      a.mult = [1.0, 1.06, 1.42][step]; a.lunge = [0.75, 0.75, 1.15][step]; a.arc = two ? 85 : 70; a.cost = w ? w.st : 9;
      this.combo++;
    } else if (kind === 'heavy') {
      a.clip = two ? 'atk2h_heavy' : 'atk1h_heavy';
      a.mult = two ? 2.15 : 1.9; a.lunge = two ? 0.6 : 1.3; a.arc = two ? 180 : 75; a.cost = (w ? w.st : 9) * 1.8; a.hyper = true; a.heavy = true;
      this.combo = 0;
    } else {
      a.clip = two ? 'atk2h_3' : 'atk1h_thrust';
      a.mult = 1.4; a.lunge = 2.4; a.arc = 50; a.cost = (w ? w.st : 9) * 1.25;
      this.combo = 0;
    }
    a.speed = (w ? w.spd : 1.1) * (this.hasStatus('frost') ? 0.82 : 1);
    a.ev = this.anim.events(a.clip);
    a.dur = this.anim.duration(a.clip);
    a.reach = (w ? w.reach : 1.0) + 0.45;
    this.useStamina(a.cost);
    // aim: lock target, else the stick direction, else current facing
    if (this.target && !this.target.dead) this.yaw = this.angleTo(this.target);
    else { const v = this.wishDir(_v2); if (v.lengthSq() > 0.04) this.yaw = Math.atan2(v.x, v.y); else { const near = this.game.nearestEnemy(this.pos, 4.5, this.yaw, 1.2); if (near) this.yaw = this.angleTo(near); } }
    this.atk = a; this.hyper = !!a.hyper;
    this.setState('attack');
    this.sheathed = false;
    this.anim.setUpper(null);
    this.anim.playOnce(a.clip, { speed: a.speed, fade: 0.07 });
    this.combatT = 8;
    return true;
  }

  tryDodge() {
    if (this.data.stamina <= 0 || this.swimming || !this.onGround) return false;
    const v = this.wishDir(_v2);
    const moving = v.lengthSq() > 0.04;
    const clip = moving ? 'roll' : 'backstep';
    this.useStamina(moving ? COST.roll : COST.backstep);
    this.rollDir = moving ? Math.atan2(v.x, v.y) : this.yaw + Math.PI;
    if (moving) this.yaw = this.rollDir;
    this.rollDist = (moving ? 4.6 : 2.7) * this.st.rollSpeed;
    this.rollEv = this.anim.events(clip);
    this.rollDur = this.anim.duration(clip);
    this.setState('roll');
    this.anim.setUpper(null);
    this.anim.playOnce(clip, { speed: this.st.rollSpeed, fade: 0.06 });
    this.game.sfx('roll', this.pos);
    this.game.voice('roll');
    this.atk = null; this.hyper = false;
    return true;
  }

  tryFlask() {
    const d = this.data;
    if (d.flasks <= 0) { this.game.sfx('ui_error'); bus.emit('toast', { kind: 'text', text: 'La fiole est vide.' }); return false; }
    if (this.hp >= this.maxHp) return false;
    this.setState('drink');
    this.anim.setUpper(null);
    this.anim.playOnce('drink', { fade: 0.12 });
    this.drinkDone = false;
    return true;
  }

  trySkill(slot) {
    const id = this.data.skillSlots[slot], sk = id && SKILLS[id];
    if (!sk) return false;
    if ((this.skillCd[id] || 0) > 0) { this.game.sfx('ui_error'); return false; }
    if (this.data.mana < sk.cost) { this.game.sfx('ui_error'); bus.emit('toast', { kind: 'text', text: 'Pas assez d\'Éclat.' }); return false; }
    this.data.mana -= sk.cost;
    this.skillCd[id] = sk.cd;
    if (this.target && !this.target.dead) this.yaw = this.angleTo(this.target);
    this.cast = { id, sk, done: false, ev: this.anim.events(sk.clip) };
    this.setState('cast');
    this.anim.setUpper(null);
    this.anim.playOnce(sk.clip, { fade: 0.1 });
    this.game.sfx('spell_cast', this.pos);
    this.combatT = 8;
    return true;
  }

  tryJump() {
    if (!this.onGround || this.swimming || this.data.stamina <= 0) return false;
    this.useStamina(COST.jump);
    this.vy = 7.2; this.onGround = false;
    this.setState('air');
    this.anim.playOnce('jump_start', { fade: 0.05, onDone: () => { if (this.state === 'air') this.anim.play('jump_air', 0.1); } });
    this.game.sfx('jump', this.pos);
    this.game.voice('jump');
    return true;
  }

  onLand(v) {
    if (this.state === 'air') {
      this.setState('free');
      this.anim.playOnce('jump_land', { fade: 0.05 });
      this.game.sfx('land', this.pos);
      this.game.footstep(this, true);
    }
  }

  toggleLock() {
    if (this.target) { this.target = null; bus.emit('lock', null); return; }
    const t = this.game.findLockTarget();
    this.target = t;
    bus.emit('lock', t);
    if (t) this.sheathed = false;
  }

  // ------------------------------------------------------------------ being hit
  /** hit: { dmg, poise, from, status:[name,amt], knock, unblockable, pos } -> 'dodged' | 'parried' | 'blocked' | 'hit' | 'dead' */
  takeHit(hit) {
    if (this.dead) return 'dodged';
    if (this.invuln > 0 || this.state === 'rest') return 'dodged';
    const g = this.game, from = hit.from;
    this.combatT = 10;
    const diff = DIFFICULTY[g.settings.get('difficulty')] || DIFFICULTY.normal;
    let dmg = hit.dmg * diff.dmgTaken;
    const srcYaw = from ? this.angleTo(from) : (hit.pos ? Math.atan2(hit.pos.x - this.pos.x, hit.pos.z - this.pos.z) : this.yaw);
    const facing = Math.abs(angleDelta(this.yaw, srcYaw)) < 1.35;
    if (this.blocking && facing && !hit.unblockable) {
      if (this.blockT < 0.22 && from && !hit.ranged) {
        g.sfx('parry', this.pos); g.vfx && g.vfx.burst('parry', this.pos, 1.3);
        if (from.onParried) from.onParried(this);
        this.riposteT = 2.2;
        g.hitStop(0.09); g.cam.shake(0.25);
        return 'parried';
      }
      const raw = dmg;
      dmg *= 1 - this.st.block;
      this.useStamina(raw * (1 - this.st.stability / 100) * 0.85 + 4);
      g.sfx('block_shield', this.pos); g.vfx && g.vfx.burst('spark', this.pos, 1.2);
      g.cam.shake(0.2);
      this.knock.set(-Math.sin(srcYaw) * 2.2, 0, -Math.cos(srcYaw) * 2.2);
      if (this.data.stamina <= 0) {
        // guard broken
        this.blocking = false; this.anim.setUpper(null);
        this.setState('stagger'); this.staggerDur = this.anim.playOnce('hit_heavy', { fade: 0.06 });
        g.sfx('crit', this.pos);
      } else if (this.state === 'free') this.anim.playOnce('block_hit', { fade: 0.04 });
      this.hp -= mitigate(dmg, this.st.def);
      if (this.hp <= 0) { this.die(from); return 'dead'; }
      return 'blocked';
    }
    dmg = mitigate(dmg, this.st.def);
    this.hp -= dmg;
    this.flash = 0.18;
    if (hit.status) this.applyStatus(hit.status[0], hit.status[1]);
    g.sfx(this.st.def > 14 ? 'hit_armor' : 'hit_flesh', this.pos);
    g.vfx && g.vfx.burst('blood', this.pos, 1.2);
    g.cam.shake(Math.min(0.25 + dmg / this.maxHp * 2.2, 0.9));
    g.hurtFlash(Math.min(0.25 + dmg / this.maxHp * 1.5, 0.75));
    g.input.rumble(0.7, 0.4, 160);
    bus.emit('player:hurt', dmg);
    if (this.hp <= 0) { this.hp = 0; this.die(from); return 'dead'; }
    const kb = (hit.knock ?? 3.5);
    this.knock.set(-Math.sin(srcYaw) * kb, 0, -Math.cos(srcYaw) * kb);
    const broke = this.addPoise(hit.poise || 15);
    if (hit.knockdown) {
      this.atk = null; this.hyper = false; this.blocking = false; this.anim.setUpper(null);
      this.setState('down'); this.yaw = srcYaw;
      this.anim.playOnce('knockdown', { fade: 0.05, onDone: () => { this.anim.playOnce('getup', { fade: 0.1, onDone: () => { if (this.state === 'down') this.setState('free'); } }); } });
      this.invulnAfter = true;
      g.voice('hurt');
    } else if (!(this.hyper && !broke)) {
      if (this.state !== 'roll' && this.state !== 'down') {
        this.atk = null; this.hyper = false; this.anim.setUpper(null);
        this.setState('stagger');
        this.staggerDur = this.anim.playOnce(broke ? 'hit_heavy' : 'hit_light', { fade: 0.05 });
        g.voice('hurt');
      }
    }
    return 'hit';
  }

  die(from) {
    if (this.dead) return;
    this.dead = true; this.hp = 0;
    this.atk = null; this.blocking = false; this.target = null;
    this.anim.setUpper(null);
    this.setState('dead');
    this.anim.playOnce('death', { fade: 0.08, hold: true });
    this.game.voice('death');
    this.data.stats.deaths++;
    bus.emit('lock', null);
    this.game.onPlayerDeath(from);
  }

  revive() {
    this.dead = false; this.hp = this.maxHp;
    this.data.stamina = this.st.maxSt; this.data.mana = this.st.maxMana;
    this.status = {}; this.knock.set(0, 0, 0); this.vy = 0;
    this.setState('free');
    this.anim.stopOnce(0.01);
    this.anim.play('idle', 0.01);
  }

  // ------------------------------------------------------------------ update
  update(dt) {
    const g = this.game, inp = g.input, d = this.data, anim = this.anim;
    this.stateT += dt;
    this.updateStatus(dt);
    if (this.combatT > 0) this.combatT -= dt;
    if (this.riposteT > 0) this.riposteT -= dt;
    if (this.interactLock > 0) this.interactLock -= dt;
    for (const k in this.skillCd) if (this.skillCd[k] > 0) this.skillCd[k] -= dt;
    for (const k in this.buffs) { const b = this.buffs[k]; if (b.t > 0) { b.t -= dt; if (b.t <= 0) bus.emit('player:buffs'); } }
    if (this.regen.t > 0) { this.regen.t -= dt; this.heal(this.regen.rate * dt); }
    if (this.bufferT > 0) { this.bufferT -= dt; if (this.bufferT <= 0) this.buffer = null; }
    if (this.comboT > 0) { this.comboT -= dt; if (this.comboT <= 0) this.combo = 0; }
    // stamina / mana regeneration
    if (this.staminaDelay > 0) this.staminaDelay -= dt;
    else if (d.stamina < this.st.maxSt) d.stamina = Math.min(this.st.maxSt, d.stamina + this.st.staminaRegen * (this.blocking ? 0.35 : 1) * this.buffMult('vigor') * (this.hasStatus('frost') ? 0.5 : 1) * dt);
    if (d.mana < this.st.maxMana) d.mana = Math.min(this.st.maxMana, d.mana + 0.7 * dt);
    if (this.target && (this.target.dead || this.distTo(this.target) > 42)) {
      this.target = g.settings.get('autoLock') && this.combatT > 0 ? g.findLockTarget(true) : null;
      bus.emit('lock', this.target);
    }
    if (this.dead) { this.moveStep(dt, 0, 0); this.syncModel(); anim.update(dt); return; }

    const en = inp.gameEnabled && g.playerControl;
    // ---- input -> buffered actions
    if (en) {
      if (inp.pressed('attack')) this.queue(inp.down('sprint') && this.speed > 5.5 ? 'sprintAttack' : 'attack');
      if (inp.pressed('heavy')) this.queue('heavy');
      if (inp.pressed('dodge')) this.queue('dodge');
      if (inp.pressed('flask')) this.queue('flask');
      if (inp.pressed('jump')) this.queue('jump');
      for (let i = 0; i < 3; i++) if (inp.pressed('skill' + (i + 1))) this.queue('skill' + i);
      if (inp.pressed('lock')) this.toggleLock();
      if (inp.pressed('sheathe')) { this.sheathed = !this.sheathed; }
      if (inp.pressed('torch')) g.torch.toggle();
      if (inp.pressed('autoTravel')) g.auto.toggle();
      if (inp.pressed('interact') && this.interactLock <= 0 && (this.state === 'free')) { if (g.interact()) this.interactLock = 0.4; }
    }
    const wantBlock = en && inp.down('block') && !this.swimming;

    switch (this.state) {
      case 'free': this._free(dt, en, wantBlock); break;
      case 'attack': this._attack(dt); break;
      case 'roll': this._roll(dt); break;
      case 'air': { const v = this.wishDir(_v2); const sp = RUN * 0.85; this.vel.x = damp(this.vel.x, v.x * sp, 3, dt); this.vel.y = damp(this.vel.y, v.y * sp, 3, dt); this.moveStep(dt, this.vel.x, this.vel.y); if (this.onGround && this.state === 'air' && this.stateT > 0.15) this.onLand(0); break; }
      case 'stagger': this.moveStep(dt, 0, 0); if (this.stateT >= (this.staggerDur || 0.4) * 0.92) this.setState('free'); break;
      case 'down': this.invuln = Math.max(this.invuln, 0.1); this.moveStep(dt, 0, 0); break;
      case 'drink': {
        const v = this.wishDir(_v2); this.moveStep(dt, v.x * WALK * 0.7, v.y * WALK * 0.7);
        const ev = anim.events('drink');
        if (!this.drinkDone && anim.time >= (ev.release ?? 0.75)) {
          this.drinkDone = true; d.flasks--;
          this.heal(this.maxHp * (this.st.flaskHeal + d.flaskLevel * 0.08));
          g.sfx('potion', this.pos); g.sfx('heal', this.pos); g.vfx && g.vfx.burst('heal', this.pos);
          bus.emit('player:flask');
        }
        if (!anim.busy || anim.oneName !== 'drink') this.setState('free');
        if (this.buffer === 'dodge' && this.drinkDone) { this.buffer = null; this.tryDodge(); }
        break;
      }
      case 'cast': {
        this.moveStep(dt, 0, 0);
        const c = this.cast;
        if (!c.done && anim.time >= (c.ev.release ?? 0.4)) { c.done = true; g.castSkill(this, c.id, c.sk); }
        if (!anim.busy) this.setState('free');
        break;
      }
      case 'interact': this.moveStep(dt, 0, 0); if (!anim.busy) this.setState('free'); break;
      case 'rest': this.moveStep(dt, 0, 0); break;
      default: this.moveStep(dt, 0, 0);
    }
    this.blocking = this.state === 'free' && wantBlock && this.data.stamina > 0;
    if (this.blocking) this.blockT += dt; else this.blockT = 0;
    anim.setUpper(this.blocking && anim.has('block_idle') ? 'block_idle' : null);
    this.syncModel();
    anim.update(dt);
    d.hp = this.hp;
  }

  _consumeBuffer() {
    const b = this.buffer;
    if (!b) return false;
    let ok = false;
    if (b === 'attack') ok = this.tryAttack('light');
    else if (b === 'sprintAttack') ok = this.tryAttack('sprint');
    else if (b === 'heavy') ok = this.tryAttack('heavy');
    else if (b === 'dodge') ok = this.tryDodge();
    else if (b === 'flask') ok = this.tryFlask();
    else if (b === 'jump') ok = this.tryJump();
    else if (b.startsWith('skill')) ok = this.trySkill(Number(b[5]));
    this.buffer = null;
    return ok;
  }

  _free(dt, en, wantBlock) {
    const g = this.game, inp = g.input, anim = this.anim, d = this.data;
    if (en && this.buffer && this._consumeBuffer()) return;
    const v = en ? this.wishDir(_v2) : _v2.set(0, 0);
    // auto-travel steers when the player does not; any manual movement takes back control
    if (g.auto.active) { if (v.lengthSq() > 0.01 || wantBlock) g.auto.stop('manual'); else if (en) g.auto.dir(v); }
    const mag = Math.min(v.length(), 1);
    let top = RUN, sprinting = false;
    if (this.swimming) top = SWIM;
    else if (wantBlock || anim.oneName === 'block_hit') top = WALK;
    else if (en && inp.down('sprint') && mag > 0.5 && d.stamina > 0) { top = SPRINT; sprinting = true; }
    top *= this.speedMul * (this.st.load > 1 ? 0.6 : 1);
    if (sprinting) { d.stamina -= COST.sprint * dt; this.staminaDelay = 0.6; }
    if (this.swimming) { d.stamina -= 4 * dt; this.staminaDelay = 0.5; if (d.stamina <= -15) { this.hp -= this.maxHp * 0.08 * dt; if (this.hp <= 0) this.die(null); } }
    const tx = mag > 0.01 ? v.x / v.length() * top * mag : 0, tz = mag > 0.01 ? v.y / v.length() * top * mag : 0;
    const acc = mag > 0.01 ? 11 : 14;
    this.vel.x = damp(this.vel.x, tx, acc, dt); this.vel.y = damp(this.vel.y, tz, acc, dt);
    this.speed = this.vel.length();
    const locked = this.target && !this.target.dead && !sprinting;
    if (locked) this.turnToward(this.angleTo(this.target), 14, dt);
    else if (this.speed > 0.3) this.turnToward(Math.atan2(this.vel.x, this.vel.y), 13, dt);
    this.moveStep(dt, this.vel.x, this.vel.y);
    // animation
    if (anim.busy && (anim.oneName === 'jump_land' || anim.oneName === 'block_hit') && this.speed > 1.5) anim.stopOnce(0.12);
    if (!anim.busy) {
      const sp = this.speed;
      const combat = this.combatT > 0 || locked;
      if (sp < 0.25) anim.play(this.twoHanded && anim.has('idle_2h') && !this.sheathed ? 'idle_2h' : (combat && anim.has('idle_combat') ? 'idle_combat' : 'idle'), 0.25);
      else if (locked && sp < 5.6) {
        // strafing relative to the facing direction
        const mv = Math.atan2(this.vel.x, this.vel.y), rel = angleDelta(this.yaw, mv);
        const a = Math.abs(rel);
        if (a < 0.9) anim.play(sp > 2.6 ? 'run' : 'walk', 0.18, sp > 2.6 ? clamp(sp / (anim.clipSpeed('run') || RUN), 0.6, 1.3) : clamp(sp / (anim.clipSpeed('walk') || 1.5), 0.6, 1.5));
        else if (a > 2.2) anim.play('walk_back', 0.18, clamp(sp / (anim.clipSpeed('walk_back') || 1.2), 0.7, 2.2));
        else anim.play(rel > 0 ? 'strafe_L' : 'strafe_R', 0.18, clamp(sp / (anim.clipSpeed('strafe_L') || 2), 0.7, 2));
      } else if (sp < 2.7) anim.play('walk', 0.2, clamp(sp / (anim.clipSpeed('walk') || 1.5), 0.6, 1.6));
      else if (sp < 5.9) anim.play('run', 0.2, clamp(sp / (anim.clipSpeed('run') || RUN), 0.7, 1.3));
      else anim.play('sprint', 0.2, clamp(sp / (anim.clipSpeed('sprint') || 7.5), 0.8, 1.2));
    }
    // footsteps
    if (this.speed > 0.6 && this.onGround) {
      this.stepT -= dt * this.speed;
      if (this.stepT <= 0) { this.stepT = this.speed > 5.6 ? 2.3 : this.speed > 2.7 ? 1.75 : 0.85; g.footstep(this, this.speed > 2.7); }
    }
  }

  _attack(dt) {
    const g = this.game, a = this.atk, anim = this.anim;
    if (!a) { this.setState('free'); return; }
    const t = anim.time;
    const hs = a.ev.hit ? a.ev.hit[0] : a.dur * 0.35, he = a.ev.hit ? a.ev.hit[1] : a.dur * 0.55;
    // lunge forward before / during the strike
    const l0 = hs * 0.35, l1 = he;
    let vx = 0, vz = 0;
    if (t > l0 && t < l1 && a.lunged < a.lunge) {
      let sp = a.lunge / ((l1 - l0) / a.speed);
      const tgt = this.target && !this.target.dead ? this.target : null;
      if (tgt && this.distTo(tgt) < a.reach * 0.75 + tgt.radius) sp = 0;       // do not walk through the target
      a.lunged += sp * dt; vx = this.fx * sp; vz = this.fz * sp;
    }
    if (this.target && !this.target.dead && t < hs) this.turnToward(this.angleTo(this.target), 10, dt);
    this.moveStep(dt, vx, vz);
    if (!a.whooshed && t >= (a.ev.whoosh ?? hs * 0.9)) {
      a.whooshed = true;
      g.sfx(a.heavy ? 'swing_heavy' : this.twoHanded ? 'swing_2h' : 'swing_light', this.pos);
      if (a.heavy || a.kind === 'sprint' || this.combo % 3 === 0) g.voice(a.heavy ? 'attack_heavy' : 'attack');
      g.vfx && g.vfx.trail(this, (he - hs) / a.speed + 0.08);
    }
    if (t >= hs && t <= he) g.playerSwing(this, a);
    const cancel = a.ev.cancel ?? a.dur * 0.7;
    if (t >= cancel && this.buffer) {
      const b = this.buffer;
      if (b === 'attack' || b === 'heavy' || b === 'dodge' || b === 'sprintAttack') {
        this.atk = null; this.hyper = false; this.comboT = 0.6;
        anim.stopOnce(0.08);
        this.setState('free');
        if (this._consumeBuffer()) return;
      }
    }
    if (!anim.busy || t >= a.dur - 0.02) { this.atk = null; this.hyper = false; this.comboT = 0.55; if (anim.busy) anim.stopOnce(0.15); this.setState('free'); }
  }

  _roll(dt) {
    const anim = this.anim, ev = this.rollEv || {};
    const t = anim.time, dur = this.rollDur || 0.7;
    const ifr = ev.iframes || [0.05, 0.45];
    if (t >= ifr[0] && t <= ifr[1]) this.invuln = Math.max(this.invuln, 0.03);
    // ease-out travel over the first 80 % of the clip
    const u = Math.min(t / (dur * 0.8), 1), sp = this.rollDist / (dur * 0.8) * (1.6 - 1.2 * u) * this.st.rollSpeed;
    this.moveStep(dt, Math.sin(this.rollDir) * sp * (u < 1 ? 1 : 0), Math.cos(this.rollDir) * sp * (u < 1 ? 1 : 0));
    const cancel = ev.cancel ?? dur * 0.82;
    if (t >= cancel && this.buffer && (this.buffer === 'attack' || this.buffer === 'dodge' || this.buffer === 'heavy')) { anim.stopOnce(0.08); this.setState('free'); this.vel.set(Math.sin(this.rollDir) * 2, Math.cos(this.rollDir) * 2); this._consumeBuffer(); return; }
    if (!anim.busy || t >= dur - 0.02) { if (anim.busy) anim.stopOnce(0.15); this.vel.set(Math.sin(this.rollDir) * 2.5, Math.cos(this.rollDir) * 2.5); this.setState('free'); }
  }
}
const _v2 = new THREE.Vector2();
