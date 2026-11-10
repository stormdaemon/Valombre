// Third-person follow camera: orbit, shoulder offset, terrain/prop collision, lock-on framing, shake.
import * as THREE from 'three';
import { damp, dampAngle, clamp } from '../core/rng.js';

export class FollowCamera {
  constructor(camera, game) {
    this.camera = camera; this.game = game;
    this.yaw = Math.PI; this.pitch = -0.18;
    this.dist = 3.8; this.curDist = 3.8;
    this.pivot = new THREE.Vector3();
    this.trauma = 0;
    this.fovKick = 0;
    this.mode = 'follow';          // 'follow' | 'fixed'
    this.fixedPos = new THREE.Vector3(); this.fixedLook = new THREE.Vector3();
    this._dir = new THREE.Vector3(); this._look = new THREE.Vector3(); this._t = 0;
    this.baseFov = 62;
    this.first = true;
  }

  shake(amount) { this.trauma = Math.min(1, this.trauma + amount * (this.game.settings.get('cameraShake') / 100)); }

  /** place the camera behind the player immediately */
  snap(yaw) { if (yaw != null) this.yaw = yaw; this.first = true; }

  setFixed(pos, look) { this.mode = 'fixed'; this.fixedPos.copy(pos); this.fixedLook.copy(look); }
  setFollow() { this.mode = 'follow'; }

  update(dt) {
    const g = this.game, cam = this.camera, s = g.settings, inp = g.input;
    this._t += dt;
    this.trauma = Math.max(0, this.trauma - dt * 1.6);
    const sh = this.trauma * this.trauma;
    if (this.mode === 'fixed') {
      cam.position.lerp(this.fixedPos, 1 - Math.exp(-4 * dt));
      this._look.lerp(this.fixedLook, 1 - Math.exp(-4 * dt));
      cam.lookAt(this._look);
      return;
    }
    const p = g.player;
    if (!p) return;
    const sens = 0.0022 * s.get('mouseSens') / 100;
    if (inp.gameEnabled) {
      this.yaw -= inp.lookDX * sens;
      this.pitch = clamp(this.pitch - inp.lookDY * sens * (s.get('invertY') ? -1 : 1), -1.25, 1.1);
      if (inp.wheel) s.set('camDistance', clamp(s.get('camDistance') + inp.wheel * 3, 25, 60), true);
    }
    this.dist = s.get('camDistance') / 10;
    const t = p.target && !p.target.dead ? p.target : null;
    if (t) {
      // frame the player and the target: look from behind the player toward the target
      const ty = Math.atan2(t.pos.x - p.pos.x, t.pos.z - p.pos.z);
      this.yaw = dampAngle(this.yaw, ty, 5.5, dt);
      const d = Math.max(p.distTo(t), 1);
      const want = clamp(-0.2 + Math.atan2((t.pos.y + t.height * 0.5) - (p.pos.y + 1.5), d) * 0.6 - Math.min(t.height, 6) * 0.02, -0.7, 0.35);
      this.pitch = damp(this.pitch, want, 3.5, dt);
    }
    const scale = p.model ? p.model.scale || 1 : 1;
    const px = p.pos.x, py = p.pos.y + 1.52 * scale, pz = p.pos.z;
    if (this.first) { this.pivot.set(px, py, pz); this.curDist = this.dist; this.first = false; }
    else { this.pivot.x = damp(this.pivot.x, px, 22, dt); this.pivot.z = damp(this.pivot.z, pz, 22, dt); this.pivot.y = damp(this.pivot.y, py, 12, dt); }
    const cp = Math.cos(this.pitch), dir = this._dir.set(Math.sin(this.yaw) * cp, Math.sin(this.pitch), Math.cos(this.yaw) * cp);
    // shoulder offset (to the camera's right)
    const so = s.get('camShoulder') ? 0.42 : 0;
    const rx = -Math.cos(this.yaw) * so, rz = Math.sin(this.yaw) * so;
    const ox = this.pivot.x + rx, oy = this.pivot.y + 0.12, oz = this.pivot.z + rz;
    let want = this.dist;
    const frac = g.collision.sweep(ox, oy, oz, ox - dir.x * want, oy - dir.y * want, oz - dir.z * want, 0.28, 14);
    want = Math.max(want * frac - 0.15, 0.55);
    this.curDist = want < this.curDist ? damp(this.curDist, want, 30, dt) : damp(this.curDist, want, 4, dt);
    cam.position.set(ox - dir.x * this.curDist, oy - dir.y * this.curDist, oz - dir.z * this.curDist);
    const gh = g.world.height(cam.position.x, cam.position.z) + 0.3;
    if (cam.position.y < gh) cam.position.y = gh;
    const wl = g.waterLevel(cam.position.x, cam.position.z) + 0.25;
    if (cam.position.y < wl) cam.position.y = wl;
    this._look.set(cam.position.x + dir.x, cam.position.y + dir.y, cam.position.z + dir.z);
    cam.lookAt(this._look);
    if (sh > 0.0005) {
      const tt = this._t * 38;
      cam.rotateX((Math.sin(tt * 1.13) + Math.sin(tt * 2.7)) * 0.012 * sh);
      cam.rotateY((Math.sin(tt * 1.57 + 2) + Math.sin(tt * 2.31)) * 0.012 * sh);
      cam.rotateZ(Math.sin(tt * 1.9 + 1) * 0.015 * sh);
    }
    const kick = p.speed > 6 ? 5 : 0;
    this.fovKick = damp(this.fovKick, kick, 4, dt);
    const fov = s.get('fov') + this.fovKick;
    if (Math.abs(cam.fov - fov) > 0.05) { cam.fov = fov; cam.updateProjectionMatrix(); }
  }
}
