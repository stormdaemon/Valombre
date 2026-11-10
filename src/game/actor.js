// Base class of everything that walks and fights: transform, grounded movement with collisions,
// health / poise / status effects.
import * as THREE from 'three';
import { STATUS } from './data/rules.js';
import { dampAngle, angleDelta } from '../core/rng.js';

const SLOPE_LIMIT = Math.tan(47 * Math.PI / 180);
const BOUND = 2520;

export class Actor {
  constructor(game) {
    this.game = game;
    this.pos = new THREE.Vector3();
    this.yaw = 0;
    this.vy = 0;
    this.knock = new THREE.Vector3();
    this.radius = 0.4; this.height = 1.8; this.weight = 1;
    this.team = 'enemy';
    this.hp = 100; this.maxHp = 100;
    this.poiseMax = 30; this.poiseAcc = 0; this.poiseT = 0;
    this.dead = false; this.onGround = true; this.swimming = false;
    this.invuln = 0;
    this.status = {};           // name -> { t, build }
    this.speedMul = 1;
    this.model = null;
    this.floats = false;
    this.flash = 0;             // hit flash timer
    this.avoidWater = true;
  }

  setModel(model) {
    if (this.model) { this.game.scene.remove(this.model.root); this.model.dispose(); }
    this.model = model;
    this.game.scene.add(model.root);
    this.syncModel();
  }

  get anim() { return this.model.animator; }
  get fx() { return Math.sin(this.yaw); }
  get fz() { return Math.cos(this.yaw); }

  distTo(o) { return Math.hypot(o.pos.x - this.pos.x, o.pos.z - this.pos.z); }
  angleTo(o) { return Math.atan2(o.pos.x - this.pos.x, o.pos.z - this.pos.z); }
  /** absolute angle (rad) between facing and the direction to o */
  facingOff(o) { return Math.abs(angleDelta(this.yaw, this.angleTo(o))); }

  turnToward(yaw, rate, dt) { this.yaw = dampAngle(this.yaw, yaw, rate, dt); }

  /** move by a horizontal velocity (m/s) with collisions, slopes, water and gravity */
  moveStep(dt, vx, vz) {
    const g = this.game, p = this.pos;
    const k = this.knock;
    vx += k.x; vz += k.z;
    const kd = Math.exp(-6 * dt);
    k.x *= kd; k.z *= kd;
    if (vx !== 0 || vz !== 0) {
      const ox = p.x, oz = p.z;
      let nx = p.x + vx * dt, nz = p.z + vz * dt;
      if (!this.floats) {
        const step = Math.hypot(nx - ox, nz - oz);
        if (step > 1e-5) {
          const h0 = g.collision.ground(ox, oz, p.y), h1 = g.collision.ground(nx, nz, p.y);
          let blocked = (h1 - h0) / step > SLOPE_LIMIT;
          if (!blocked && this.avoidWater && g.waterDepth(nx, nz) > 0.95 && g.waterDepth(ox, oz) <= 0.95) blocked = true;
          if (blocked) {
            // try sliding along one axis
            const hx = g.collision.ground(nx, oz, p.y), hz = g.collision.ground(ox, nz, p.y);
            const okx = (hx - h0) / Math.max(Math.abs(nx - ox), 1e-4) <= SLOPE_LIMIT && !(this.avoidWater && g.waterDepth(nx, oz) > 0.95);
            const okz = (hz - h0) / Math.max(Math.abs(nz - oz), 1e-4) <= SLOPE_LIMIT && !(this.avoidWater && g.waterDepth(ox, nz) > 0.95);
            if (okx && Math.abs(vx) >= Math.abs(vz)) nz = oz; else if (okz) nx = ox; else if (okx) nz = oz; else { nx = ox; nz = oz; }
          }
        }
      }
      p.x = nx; p.z = nz;
      g.collision.resolve(p, this.radius, this.height);
      if (g.vegetation) g.vegetation.resolve(p, this.radius);
      if (p.x > BOUND) p.x = BOUND; else if (p.x < -BOUND) p.x = -BOUND;
      if (p.z > BOUND) p.z = BOUND; else if (p.z < -BOUND) p.z = -BOUND;
    }
    // vertical
    const ground = g.collision.ground(p.x, p.z, p.y);
    const depth = g.waterLevel(p.x, p.z) - ground;
    if (this.floats) {
      const target = Math.max(ground, g.waterLevel(p.x, p.z)) + 0.35;
      p.y += (target - p.y) * Math.min(dt * 6, 1);
      this.onGround = true; this.swimming = false;
      return;
    }
    if (depth > 1.35 && this.vy <= 0) {
      // swimming: keep the head above water
      const target = g.waterLevel(p.x, p.z) - 1.3;
      p.y += (target - p.y) * Math.min(dt * 5, 1);
      this.vy = 0; this.onGround = true; this.swimming = true;
      return;
    }
    this.swimming = false;
    if (this.vy > 0 || p.y > ground + 0.45) {
      this.vy -= 24 * dt;
      p.y += this.vy * dt;
      if (p.y <= ground) { p.y = ground; const v = this.vy; this.vy = 0; if (!this.onGround) { this.onGround = true; this.onLand(v); } }
      else this.onGround = false;
    } else {
      p.y = ground; this.vy = 0;
      if (!this.onGround) { this.onGround = true; this.onLand(0); }
    }
  }

  onLand() {}

  syncModel() {
    if (!this.model) return;
    const r = this.model.root;
    r.position.copy(this.pos);
    r.rotation.y = this.yaw;
  }

  // ------------------------------------------------------------------ status effects
  applyStatus(name, amount) {
    const def = STATUS[name];
    if (!def || this.dead) return;
    const s = this.status[name] || (this.status[name] = { t: 0, build: 0 });
    s.build += amount;
    const threshold = this.statusThreshold || 20;
    if (s.build >= threshold) {
      s.build = 0;
      if (def.burst) { this.hp = Math.max(1, this.hp - this.maxHp * def.burst); this.game.onStatusProc(this, name); }
      else { s.t = def.time; this.game.onStatusProc(this, name); }
    }
  }

  hasStatus(name) { const s = this.status[name]; return !!s && s.t > 0; }
  cureStatus(name) { delete this.status[name]; }

  updateStatus(dt) {
    let slow = 1;
    for (const name in this.status) {
      const s = this.status[name], def = STATUS[name];
      if (s.t > 0) {
        s.t -= dt;
        if (def.dps && !this.dead) { this.hp -= this.maxHp * def.dps * dt * (this.team === 'player' ? 1 : 0.5); if (this.hp <= 0) { this.hp = 0; this.die(null); } }
        if (def.slow) slow = Math.min(slow, def.slow);
      } else if (s.build > 0) s.build = Math.max(0, s.build - dt * 2.5);
    }
    this.speedMul = slow;
    if (this.invuln > 0) this.invuln -= dt;
    if (this.flash > 0) this.flash -= dt;
    if (this.poiseT > 0) { this.poiseT -= dt; if (this.poiseT <= 0) this.poiseAcc = 0; }
  }

  /** accumulate poise damage; returns true when the actor's poise breaks */
  addPoise(amount) {
    this.poiseAcc += amount; this.poiseT = 4;
    if (this.poiseAcc >= this.poiseMax) { this.poiseAcc = 0; return true; }
    return false;
  }

  die() { this.dead = true; }

  dispose() {
    if (this.model) { this.game.scene.remove(this.model.root); this.model.dispose(); this.model = null; }
  }
}
