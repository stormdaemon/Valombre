// The player's torch: a resin torch carried from the start (item 'torch'), lit / put out with [T].
// Held in the left hand when it is free, hung at the belt when a shield or a two-handed weapon needs it.
// It owns a dedicated point light that always stays in the scene (intensity 0 when out), so toggling it
// never changes the light count (which would recompile every material).
import * as THREE from 'three';
import { U, patchMaterial } from '../core/globals.js';
import { bus } from '../core/events.js';

const _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _e = new THREE.Euler();
const LIGHT_I = 9, LIGHT_R = 24, DECAY = 1.15;   // soft falloff: the face is not burnt out, the path ahead stays lit

export class Torch {
  constructor(game) {
    this.game = game;
    this.light = new THREE.PointLight(0xffa24e, 0, LIGHT_R, DECAY);
    this.light.castShadow = false;
    game.scene.add(this.light);
    this.mesh = buildTorchMesh();
    this.flame = this.mesh.userData.flame;
    this.socket = null;
    this.power = LIGHT_I;
    this.glow = 0;            // 0..1, fades in when lit
    this.acc = 0;
    this._p = new THREE.Vector3();
  }

  get lit() { const p = this.game.player; return !!(p && p.data.torchLit); }

  /** light it or put it out; returns the new state, or null when impossible */
  toggle(force) {
    const g = this.game, p = g.player;
    if (!p || p.dead) return null;
    if (!p.count('torch')) { bus.emit('toast', { kind: 'text', text: 'Vous n\'avez pas de torche.' }); g.sfx('ui_error'); return null; }
    const on = force ?? !p.data.torchLit;
    if (on && p.swimming) { bus.emit('toast', { kind: 'text', text: 'Impossible d\'allumer une torche dans l\'eau.' }); g.sfx('ui_error'); return null; }
    if (on === !!p.data.torchLit) return on;
    p.data.torchLit = on;
    g.sfx(on ? 'ui_equip' : 'ui_close', p.pos);
    bus.emit('player:torch', on);
    return on;
  }

  /** where the torch goes: the free left hand, else strapped on the back (flame above the right shoulder) */
  _socketFor(p) {
    const m = p.model, s = m && m.sockets;
    if (!m) return null;
    const eq = p.data.equipment;
    const handBusy = p.twoHanded || !!eq.offhand;
    return (!handBusy && s && (s.weaponL || s.shieldL)) || m.root;
  }

  reset() { this.glow = 0; this._attach(null); this.light.intensity = 0; }

  _attach(sock) {
    if (sock === this.socket) return;
    if (this.mesh.parent) this.mesh.parent.remove(this.mesh);
    this.socket = sock;
    if (!sock) return;
    sock.add(this.mesh);
    const p = this.game.player;
    if (sock === p.model.root) {
      // model space: +Z forward, +X = the character's left. Behind the right shoulder, leaning back and out.
      this.mesh.position.set(-0.17, 1.12 * (p.model.scale || 1), -0.17);
      this.mesh.rotation.set(-0.32, 0, 0.3);
      this.mesh.scale.setScalar(1.1);
    } else {
      // in the hand: along the grip (+Y = weapon convention), held a little below the head
      this.mesh.position.set(0, -0.12, 0);
      this.mesh.rotation.set(0, 0, 0);
      this.mesh.scale.setScalar(1);
    }
  }

  update(dt) {
    const g = this.game, p = g.player;
    if (!p) { this.light.intensity = 0; return; }
    if (p.data.torchLit && p.swimming) { p.data.torchLit = false; bus.emit('toast', { kind: 'text', text: 'Votre torche s\'est éteinte dans l\'eau.' }); bus.emit('player:torch', false); g.sfx('splash', p.pos); }
    const on = !!p.data.torchLit && !p.dead;
    this.glow = Math.max(0, Math.min(1, this.glow + (on ? dt * 3 : -dt * 5)));
    if (!on && this.glow <= 0) { this._attach(null); this.light.intensity = 0; return; }
    this._attach(this._socketFor(p));
    this.mesh.visible = !!this.socket;
    if (this.socket && this.socket !== p.model.root) {
      // held upright (leaning forward a little) whatever the wrist does; the grip stays in the hand
      this.socket.updateWorldMatrix(true, false);
      this.socket.getWorldQuaternion(_q1).invert();
      _q2.setFromEuler(_e.set(0.3, p.yaw, 0, 'YXZ'));
      this.mesh.quaternion.copy(_q1).multiply(_q2);
      this.mesh.position.set(0, -0.14, 0).applyQuaternion(this.mesh.quaternion);
    }
    // flame position in the world
    const fp = this._p;
    if (this.socket) { this.flame.updateWorldMatrix(true, false); fp.setFromMatrixPosition(this.flame.matrixWorld); }
    else fp.set(p.pos.x, p.pos.y + 1.4, p.pos.z);
    const t = U.uTime.value;
    const fl = 0.86 + 0.09 * Math.sin(t * 13.1 + 0.7) + 0.06 * Math.sin(t * 27.3) + 0.04 * Math.sin(t * 5.3);
    // the light sits a little above and in front of the flame so the face and the path ahead are lit
    this.light.position.set(fp.x + p.fx * 0.5, fp.y + 0.5, fp.z + p.fz * 0.5);
    this.light.intensity = this.power * this.glow * fl;
    this.light.distance = LIGHT_R;
    this.flame.material.emissiveIntensity = (3.5 + 2 * fl) * this.glow;
    // fire particles
    if (on && g.vfx) {
      this.acc += dt * 30 * g.vfx.density;
      while (this.acc >= 1) {
        this.acc -= 1;
        g.vfx.puff('fire', fp.x, fp.y + 0.04, fp.z, 0.32);
        if (Math.random() < 0.07) g.vfx.puff('ember', fp.x, fp.y + 0.1, fp.z);
      }
    }
  }
}

/** handle along +Y, wrapped resin head at the top; userData.flame = emissive head */
function buildTorchMesh() {
  const root = new THREE.Group();
  root.name = 'player_torch';
  const wood = new THREE.MeshStandardMaterial({ color: 0x4a3322, roughness: 0.85 });
  patchMaterial(wood);
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.024, 0.52, 8).translate(0, 0.2, 0), wood);
  handle.castShadow = true;
  const cloth = new THREE.MeshStandardMaterial({ color: 0x2a1c12, roughness: 0.95 });
  patchMaterial(cloth);
  const wrap = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.032, 0.12, 8).translate(0, 0.48, 0), cloth);
  const ember = new THREE.MeshStandardMaterial({ color: 0x1a0a04, emissive: 0xff7a26, emissiveIntensity: 4, roughness: 1 });
  patchMaterial(ember);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.036, 8, 6).translate(0, 0.56, 0), ember);
  const flame = new THREE.Object3D();
  flame.position.set(0, 0.6, 0);
  flame.material = ember;
  root.add(handle, wrap, head, flame);
  root.userData.flame = flame;
  return root;
}
