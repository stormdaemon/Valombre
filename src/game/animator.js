// Animation controller on top of THREE.AnimationMixer: looping base state, one-shot actions,
// optional upper-body layer, and metadata-driven events. Works without clips (timers only), so game
// logic never depends on the art being present.
import * as THREE from 'three';

const UPPER = /^(spine_02|spine_03|neck|head|clavicle|upper_arm|forearm|hand|thumb|index|fingers)/;

/**
 * Prepare humanoid clips for sharing across skeletons: keep rotations of real bones, the hips position
 * (optionally rescaled for differently-proportioned rigs), drop everything else.
 */
export function prepareClips(clips, { hipsScale = 1, hipsName = 'hips', keepPositions = false } = {}) {
  const out = {};
  for (const clip of clips) {
    const tracks = [];
    for (const t of clip.tracks) {
      const dot = t.name.lastIndexOf('.');
      const node = t.name.slice(0, dot), prop = t.name.slice(dot + 1);
      if (prop === 'scale') continue;
      if (/^(weapon_|shield_|sheath_|root$)/.test(node)) continue;
      if (prop === 'position') {
        if (!keepPositions && node !== hipsName) continue;
        if (hipsScale !== 1 && node === hipsName) {
          const c = t.clone();
          for (let i = 0; i < c.values.length; i++) c.values[i] *= hipsScale;
          tracks.push(c);
          continue;
        }
      }
      tracks.push(t);
    }
    out[clip.name] = new THREE.AnimationClip(clip.name, clip.duration, tracks);
  }
  return out;
}

/** upper-body-only variant of a clip (for layering over locomotion) */
export function upperBodyClip(clip) {
  const tracks = clip.tracks.filter(t => UPPER.test(t.name) && !t.name.endsWith('.position'));
  return new THREE.AnimationClip(clip.name + '@upper', clip.duration, tracks);
}

export class Animator {
  /** root: object containing the bones; clips: {name: AnimationClip}; meta: {name: {duration, loop, speed, events}} */
  constructor(root, clips, meta) {
    this.root = root; this.clips = clips || {}; this.meta = meta || {};
    this.mixer = root ? new THREE.AnimationMixer(root) : null;
    this.actions = {};
    this.base = null; this.baseName = '';
    this.one = null; this.oneName = ''; this.oneT = 0; this.oneDur = 0; this.oneSpeed = 1; this.oneHold = false; this.oneDone = null;
    this.upper = null; this.upperName = '';
    this.timeScale = 1;
  }

  has(name) { return !!this.clips[name]; }
  duration(name) { const m = this.meta[name]; return m ? m.duration : (this.clips[name] ? this.clips[name].duration : 0.6); }
  events(name) { const m = this.meta[name]; return (m && m.events) || {}; }
  clipSpeed(name) { const m = this.meta[name]; return (m && m.speed) || 0; }

  _action(name, upper = false) {
    const key = upper ? name + '@upper' : name;
    if (this.actions[key]) return this.actions[key];
    let clip = this.clips[name];
    if (!clip || !this.mixer) return null;
    if (upper) clip = this.clips[key] || (this.clips[key] = upperBodyClip(clip));
    return (this.actions[key] = this.mixer.clipAction(clip));
  }

  /** looping base animation (locomotion, idle...) */
  play(name, fade = 0.2, speed = 1) {
    if (this.baseName === name) { if (this.base) this.base.timeScale = speed; return; }
    const a = this._action(name);
    const prev = this.base;
    this.baseName = name; this.base = a;
    if (a) {
      a.reset(); a.setLoop(THREE.LoopRepeat, Infinity); a.clampWhenFinished = false; a.timeScale = speed;
      a.setEffectiveWeight(this.one ? 0 : 1);
      a.play();
      if (prev && prev !== a && !this.one) a.crossFadeFrom(prev, fade, false);
      else if (prev && prev !== a) prev.stop();
      if (!prev && !this.one) a.fadeIn(Math.min(fade, 0.05));
    } else if (prev && !this.one) prev.fadeOut(fade);
  }

  /** one-shot full-body action. opts: fade, speed, hold (keep last pose), onDone */
  playOnce(name, opts = {}) {
    const fade = opts.fade ?? 0.1, speed = opts.speed ?? 1;
    const a = this._action(name);
    const prev = this.one || this.base;
    this.oneName = name; this.oneT = 0; this.oneSpeed = speed; this.oneDur = this.duration(name); this.oneHold = !!opts.hold; this.oneDone = opts.onDone || null;
    if (a) {
      a.reset(); a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; a.timeScale = speed; a.setEffectiveWeight(1);
      a.play();
      if (prev && prev !== a) a.crossFadeFrom(prev, fade, false);
    }
    if (this.one && this.one !== a) { const o = this.one; setTimeout(() => { if (this.one !== o) o.stop(); }, fade * 1000 + 30); }
    this.one = a || { stub: true };
    return this.oneDur / speed;
  }

  /** stop the one-shot and return to the base loop */
  stopOnce(fade = 0.15) {
    const a = this.one;
    this.one = null; this.oneName = ''; this.oneDone = null;
    if (this.base) {
      this.base.reset(); this.base.setEffectiveWeight(1); this.base.play();
      if (a && !a.stub) this.base.crossFadeFrom(a, fade, false);
    } else if (a && !a.stub) a.fadeOut(fade);
  }

  /** upper-body overlay (looping), e.g. block while walking. name = null to remove. */
  setUpper(name, fade = 0.12) {
    if (this.upperName === (name || '')) return;
    if (this.upper) this.upper.fadeOut(fade);
    this.upperName = name || ''; this.upper = null;
    if (!name) return;
    const a = this._action(name, true);
    // a heavy weight makes the overlay win the per-bone weighted blend against the locomotion layer
    if (a) { a.reset(); a.setLoop(THREE.LoopRepeat, Infinity); a.setEffectiveWeight(9); a.fadeIn(fade); a.play(); this.upper = a; }
  }

  /** seconds elapsed in the current one-shot, in clip time */
  get time() { return this.oneT; }
  get busy() { return !!this.one; }

  update(dt) {
    const d = dt * this.timeScale;
    if (this.mixer) this.mixer.update(d);
    if (this.one) {
      this.oneT += d * this.oneSpeed;
      if (this.oneT >= this.oneDur) {
        const cb = this.oneDone;
        if (this.oneHold) { this.oneDone = null; this.oneT = this.oneDur; if (cb) cb(); }
        else { this.stopOnce(); if (cb) cb(); }
      }
    }
  }

  dispose() { if (this.mixer) { this.mixer.stopAllAction(); this.mixer.uncacheRoot(this.root); } }
}
