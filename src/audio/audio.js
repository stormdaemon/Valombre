/**
 * VALOMBRE audio engine - public entry point.
 *
 * Everything is synthesized at runtime with the Web Audio API (no audio files):
 *   buses (sfx, ui, voice, ambience, music) -> master -> compressor -> soft clipper -> output
 *   two generated convolution reverbs (hall, room) fed by per-bus sends
 *   one-shot voices with a cap, priorities and stealing; virtualised positional loops
 *   layered ambience and a generative music sequencer
 *
 * The synthesis graph can be built on any BaseAudioContext: pass `{ context, destination }`
 * to the constructor to render through an OfflineAudioContext (see tools/audio_test.js).
 */
import { Rng, Resources, Kit, clamp } from './core.js';
import { SFX, SFX_NAMES } from './sfx.js';
import { FOOT, FOOT_NAMES } from './footsteps.js';
import { VOICE, VOICE_NAMES } from './voice.js';
import { LOOPS, LOOP_NAMES } from './loops.js';
import { Ambience, AMB, AMB_NAMES, THUNDER, BIOMES } from './ambience.js';
import { Music, MUSIC_STATES, BOSSES } from './music.js';

const MAX_VOICES = 28;
const MAX_LOOPS = 12;
const LOOP_IN = 48, LOOP_OUT = 56;          // metres: loops are instantiated / released around the listener
const CULL_DIST = 100;                      // positional one-shots farther than this are skipped
const BUS_NAMES = ['sfx', 'ui', 'voice', 'ambience', 'music'];
const DEFAULT_VOL = { master: 1, music: 0.7, sfx: 1, ambience: 0.8, ui: 0.8, voice: 1 };
/**
 * Cancels the automatic make-up gain Chromium applies in DynamicsCompressorNode for the settings
 * below (threshold -8, knee 6, ratio 6): measured x1.381 by tools/audio_test (calib.quietSineGain).
 * Re-measure if the compressor settings change.
 */
const COMP_MAKEUP = 0.724;

const EMPTY = Object.freeze({});
const NOOP_LOOP = Object.freeze({ setVolume() {}, setPitch() {}, setPos() {}, stop() {} });

function rampTo(param, value, now, seconds) {
  if (seconds > 0.001) param.setTargetAtTime(value, now, seconds / 3);
  else param.setValueAtTime(value, now);
}

/** Handle returned by AudioEngine.startLoop(). */
class LoopHandle {
  constructor(engine, name, def, o) {
    this._e = engine; this.name = name; this._def = def;
    this._pos = o.pos ? [o.pos[0], o.pos[1], o.pos[2]] : null;
    this._vol = o.volume === undefined ? 1 : o.volume;
    this._pitch = o.pitch === undefined ? 1 : o.pitch;
    this._inst = null; this._stopped = false;
  }

  /** @param {number} v linear volume @param {number} [ramp] seconds */
  setVolume(v, ramp = 0.1) {
    this._vol = v;
    if (this._inst) rampTo(this._inst.in.gain, v * this._def.gain, this._e._ctx.currentTime, ramp);
  }

  /** @param {number} p playback pitch factor (1 = original) */
  setPitch(p) {
    this._pitch = p > 0 ? p : 1;
    const i = this._inst;
    if (!i) return;
    const cents = 1200 * Math.log2(this._pitch), now = this._e._ctx.currentTime;
    for (let n = 0; n < i.sources.length; n++) { const s = i.sources[n]; if (s.detune) s.detune.setTargetAtTime(i.base[n] + cents, now, 0.03); }
  }

  /** @param {number[]} pos world position [x, y, z] */
  setPos(pos) {
    if (!pos) return;
    if (!this._pos) {
      // Was non-positional: drop the current nodes, the next update re-creates them with a panner.
      this._pos = [pos[0], pos[1], pos[2]];
      if (this._inst) { this._e._release(this, this._e._ctx.currentTime, 0.1); this._e._loopTick = 0; }
      return;
    }
    this._pos[0] = pos[0]; this._pos[1] = pos[1]; this._pos[2] = pos[2];
    const p = this._inst && this._inst.panner;
    if (p) { p.positionX.value = pos[0]; p.positionY.value = pos[1]; p.positionZ.value = pos[2]; }
  }

  /** @param {number} [fadeSeconds] */
  stop(fadeSeconds = 0.3) {
    if (this._stopped) return;
    this._stopped = true;
    this._e._dropLoop(this, fadeSeconds);
  }
}

export class AudioEngine {
  /**
   * @param {{context?:BaseAudioContext, destination?:AudioNode, seed?:number}} [opts]
   *   Optional: build the engine on an existing (e.g. offline) context / output node, with a fixed random seed.
   */
  constructor(opts) {
    this._opts = opts || EMPTY;
    this._ctx = null;
    this._ready = false;
    this._initP = null;
    this._vol = Object.assign({}, DEFAULT_VOL);
    this._lpos = [0, 0, 0];
    this._lfwd = [0, 0, -1];
    this._voices = [];
    this._dying = [];
    /** @type {LoopHandle[]} */ this._loops = [];
    this._loopTick = 0;
    this._warned = new Set();
    this._pendingAmb = null;
    this._pendingMusic = null;
    this._scratch = { pos: null, volume: 1 };
    this._offline = false;
    this._paused = false;
    this._unlock = null;
  }

  /**
   * Creates the AudioContext, buses, reverbs and pre-rendered buffers. Call from a user
   * gesture. Idempotent: later calls return the same promise.
   * @returns {Promise<void>}
   */
  init() {
    if (!this._initP) {
      this._initP = this._init().catch((e) => { console.warn('[audio] init failed', e); this._initP = null; });
    }
    return this._initP;
  }

  async _init() {
    const AC = globalThis.AudioContext || globalThis.webkitAudioContext;
    const ctx = this._opts.context || new AC({ latencyHint: 'interactive' });
    this._ctx = ctx;
    this._offline = typeof OfflineAudioContext !== 'undefined' && ctx instanceof OfflineAudioContext;
    const seed = this._opts.seed !== undefined ? this._opts.seed >>> 0 : ((Date.now() ^ Math.floor(Math.random() * 0x7fffffff)) >>> 0);
    this._rng = new Rng(seed);
    const res = this._res = new Resources(ctx, new Rng(seed ^ 0x5bd1e995));
    this._kit = new Kit(ctx, res, this._rng);

    // Master chain.
    const master = this._master = ctx.createGain();
    master.gain.value = this._vol.master;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -8; comp.knee.value = 6; comp.ratio.value = 6; comp.attack.value = 0.003; comp.release.value = 0.15;
    const makeup = ctx.createGain();
    makeup.gain.value = COMP_MAKEUP;
    const clip = this._out = ctx.createWaveShaper();
    clip.curve = res.curves.limit; clip.oversample = '2x';
    master.connect(comp); comp.connect(makeup); makeup.connect(clip);
    clip.connect(this._opts.destination || ctx.destination);

    // Reverbs.
    const mkVerb = (ir, ret) => {
      const input = ctx.createGain(), conv = ctx.createConvolver(), out = ctx.createGain();
      conv.buffer = ir; out.gain.value = ret;
      input.connect(conv); conv.connect(out); out.connect(master);
      return input;
    };
    const hallIn = mkVerb(res.irHall, 0.9), roomIn = mkVerb(res.irRoom, 0.8);

    // Buses: a dry gain and two reverb-send gains that all follow the bus volume.
    this._bus = {};
    for (const n of BUS_NAMES) {
      const dry = ctx.createGain(), hall = ctx.createGain(), room = ctx.createGain();
      dry.gain.value = hall.gain.value = room.gain.value = this._vol[n];
      dry.connect(master); hall.connect(hallIn); room.connect(roomIn);
      this._bus[n] = { dry, hall, room };
    }

    const warn = (key) => this._warn(key, 'unknown name "' + key + '"');
    this._music = new Music({
      kit: new Kit(ctx, res, new Rng(seed ^ 0x1234567)), rng: new Rng(seed ^ 0x2468ace),
      outDry: this._bus.music.dry, outHall: this._bus.music.hall, warn,
    });
    this._amb = new Ambience({
      kit: new Kit(ctx, res, new Rng(seed ^ 0x7654321)), rng: new Rng(seed ^ 0x13579bd),
      out: this._bus.ambience.dry, lpos: this._lpos, warn,
      spawn: (def, o) => this._spawn(def, o, 'ambience'),
      spawnSfx: (name, o) => { if (SFX[name]) this._spawn(SFX[name], o, 'ambience'); },
      thunder: (d) => this.thunder(d),
    });

    // Never wait for resume(): without a user gesture the promise stays pending. Arm a one-shot unlock instead.
    if (!this._offline && ctx.state === 'suspended') { ctx.resume().catch(() => {}); this._armUnlock(); }
    this._ready = true;
    this._applyListener();
    if (this._pendingAmb) { this._amb.set(this._pendingAmb); this._pendingAmb = null; }
    if (this._pendingMusic) { this._music.set(this._pendingMusic[0], this._pendingMusic[1]); this._pendingMusic = null; }
  }

  /** If the context could not start (init() called outside a user gesture), start it on the next gesture. */
  _armUnlock() {
    if (typeof window === 'undefined' || this._unlock) return;
    const events = ['pointerdown', 'keydown', 'touchstart'];
    this._unlock = () => {
      for (const ev of events) window.removeEventListener(ev, this._unlock, true);
      this._unlock = null;
      if (this._ctx.state === 'suspended' && !this._paused) this._ctx.resume().catch(() => {});
    };
    for (const ev of events) window.addEventListener(ev, this._unlock, true);
  }

  /** True once init() has completed. */
  get ready() { return this._ready; }

  /** The underlying BaseAudioContext (null before init). */
  get context() { return this._ctx; }

  /** Resumes the audio clock (tab focus, leaving the pause menu). */
  resume() {
    this._paused = false;
    if (this._ready && !this._offline && this._ctx.state === 'suspended') this._ctx.resume().catch(() => {});
  }

  /** Suspends the audio clock (tab hidden, pause menu). */
  suspend() {
    this._paused = true;
    if (this._ready && !this._offline && this._ctx.state === 'running') this._ctx.suspend().catch(() => {});
  }

  /**
   * Sets any subset of the bus volumes (each 0..1) with a short ramp.
   * @param {{master?:number, music?:number, sfx?:number, ambience?:number, ui?:number, voice?:number}} v
   */
  setVolumes(v) {
    if (!v) return;
    const now = this._ready ? this._ctx.currentTime : 0;
    for (const key in DEFAULT_VOL) {
      if (typeof v[key] !== 'number' || !(v[key] === v[key])) continue;
      const val = clamp(v[key], 0, 1);
      if (val === this._vol[key]) continue;
      this._vol[key] = val;
      if (!this._ready) continue;
      if (key === 'master') this._master.gain.setTargetAtTime(val, now, 0.04);
      else { const b = this._bus[key]; b.dry.gain.setTargetAtTime(val, now, 0.04); b.hall.gain.setTargetAtTime(val, now, 0.04); b.room.gain.setTargetAtTime(val, now, 0.04); }
    }
  }

  /**
   * Listener (camera) transform; call every frame.
   * @param {number[]} pos [x, y, z]
   * @param {number[]} forward [x, y, z], need not be normalised
   */
  setListener(pos, forward) {
    const p = this._lpos, f = this._lfwd;
    if (pos) { p[0] = pos[0]; p[1] = pos[1]; p[2] = pos[2]; }
    if (forward) {
      const l = Math.hypot(forward[0], forward[1], forward[2]);
      if (l > 1e-5) { f[0] = forward[0] / l; f[1] = forward[1] / l; f[2] = forward[2] / l; }
    }
    if (this._ready) this._applyListener();
  }

  _applyListener() {
    const L = this._ctx.listener, p = this._lpos, f = this._lfwd;
    // Keep "up" valid even when looking straight up or down.
    const vertical = Math.abs(f[1]) > 0.999;
    if (L.positionX) {
      L.positionX.value = p[0]; L.positionY.value = p[1]; L.positionZ.value = p[2];
      L.forwardX.value = f[0]; L.forwardY.value = f[1]; L.forwardZ.value = f[2];
      L.upX.value = 0; L.upY.value = vertical ? 0 : 1; L.upZ.value = vertical ? 1 : 0;
    } else {
      L.setPosition(p[0], p[1], p[2]);
      L.setOrientation(f[0], f[1], f[2], 0, vertical ? 0 : 1, vertical ? 1 : 0);
    }
  }

  /**
   * Per-frame update: music look-ahead scheduling, ambience cross-fades and events, loop
   * virtualisation, release of finished voices.
   * @param {number} dt seconds since the previous frame
   */
  update(dt) {
    if (!this._ready) return;
    const now = this._ctx.currentTime;
    if (!(dt > 0)) dt = 1 / 60;
    this._sweep(this._voices, now);
    this._sweep(this._dying, now);
    this._music.update(now);
    this._amb.update(now, dt);
    this._loopTick -= dt;
    if (this._loopTick <= 0) { this._loopTick = 0.2; this._updateLoops(now); }
  }

  _sweep(list, now) {
    for (let i = list.length - 1; i >= 0; i--) {
      const v = list[i];
      if (now > v.end) { this._free(v); list[i] = list[list.length - 1]; list.pop(); }
    }
  }

  _free(v) {
    try { v.in.disconnect(); } catch (e) { /* gone */ }
    if (v.panner) { try { v.panner.disconnect(); } catch (e) { /* gone */ } }
    if (v.send) { try { v.send.disconnect(); } catch (e) { /* gone */ } }
  }

  _warn(key, msg) {
    if (this._warned.has(key)) return;
    this._warned.add(key);
    console.warn('[audio] ' + msg);
  }

  _panner(pos, ref) {
    const p = this._ctx.createPanner();
    p.panningModel = 'equalpower'; p.distanceModel = 'inverse';
    p.refDistance = ref || 4; p.maxDistance = 80; p.rolloffFactor = 1;
    p.positionX.value = pos[0]; p.positionY.value = pos[1]; p.positionZ.value = pos[2];
    return p;
  }

  /** Makes room for a new one-shot of priority `prio`; false if it must be dropped. */
  _steal(prio, now) {
    const vs = this._voices;
    let vi = -1;
    for (let i = 0; i < vs.length; i++) {
      if (vi < 0 || vs[i].prio < vs[vi].prio || (vs[i].prio === vs[vi].prio && vs[i].end < vs[vi].end)) vi = i;
    }
    if (vi < 0 || vs[vi].prio > prio) return false;
    const v = vs[vi];
    v.in.gain.cancelScheduledValues(now);
    v.in.gain.setTargetAtTime(0, now, 0.008);
    for (const s of v.sources) { try { s.stop(now + 0.05); } catch (e) { /* ended */ } }
    v.end = now + 0.08;
    vs[vi] = vs[vs.length - 1]; vs.pop();
    this._dying.push(v);
    return true;
  }

  /**
   * Builds one voice: recipe -> gain -> [panner] -> bus (+ reverb send).
   * @returns {object|null} the voice, or null when culled / dropped
   */
  _spawn(def, o, busName, extra) {
    o = o || EMPTY;
    const ctx = this._ctx, now = ctx.currentTime, pos = busName === 'ui' ? null : o.pos;
    if (pos) {
      const lp = this._lpos, dx = pos[0] - lp[0], dy = pos[1] - lp[1], dz = pos[2] - lp[2];
      if (dx * dx + dy * dy + dz * dz > CULL_DIST * CULL_DIST) return null;
    }
    if (this._voices.length >= MAX_VOICES && !this._steal(def.prio, now)) return null;
    const t = now + 0.006 + (o.delay > 0 ? o.delay : 0);
    const bus = this._bus[busName], vin = ctx.createGain();
    vin.gain.value = def.gain * (o.volume === undefined ? 1 : o.volume);
    const v = { in: vin, panner: null, send: null, sources: [], prio: def.prio, end: 0 };
    let tail = vin;
    if (pos) { v.panner = this._panner(pos, o.ref); vin.connect(v.panner); tail = v.panner; }
    tail.connect(bus.dry);
    if (def.rev && def.send > 0) {
      v.send = ctx.createGain(); v.send.gain.value = def.send;
      tail.connect(v.send); v.send.connect(def.rev === 'hall' ? bus.hall : bus.room);
    }
    const k = this._kit;
    k.track = v.sources;
    k.cents = o.pitch > 0 && o.pitch !== 1 ? 1200 * Math.log2(o.pitch) : 0;
    let dur = 1;
    try { dur = def.fn(k, vin, t, k.rng, extra) || 1; } catch (e) { this._warn('err:' + def.name, 'recipe "' + def.name + '" failed: ' + e); dur = 0; }
    k.track = null; k.cents = 0;
    v.end = t + dur + 0.15;
    this._voices.push(v);
    return v;
  }

  /**
   * Plays a one-shot sound effect.
   * @param {string} name one of list()
   * @param {{pos?:number[], volume?:number, pitch?:number, delay?:number}} [opts]
   *   pos omitted = non-positional; volume 1 = nominal; pitch 1 = original; delay in seconds.
   */
  play(name, opts) {
    if (!this._ready) return;
    const def = SFX[name];
    if (!def) { this._warn('sfx:' + name, 'unknown SFX "' + name + '"'); return; }
    this._spawn(def, opts, def.cat === 'ui' ? 'ui' : 'sfx');
  }

  /**
   * Starts a looping emitter. Positional loops are virtualised: nodes only exist while the
   * emitter is near the listener, so it is safe to register every torch of a village.
   * @param {string} name 'fire'|'brazier'|'torch'|'crystal_hum'|'waterfall'|'boss_aura'|'forge'
   * @param {{pos?:number[], volume?:number, pitch?:number}} [opts]
   * @returns {{setVolume(v:number, ramp?:number):void, setPitch(p:number):void, setPos(pos:number[]):void, stop(fadeSeconds?:number):void}}
   */
  startLoop(name, opts) {
    const def = LOOPS[name];
    if (!def) { this._warn('loop:' + name, 'unknown loop "' + name + '"'); return NOOP_LOOP; }
    const h = new LoopHandle(this, name, def, opts || EMPTY);
    this._loops.push(h);
    this._loopTick = 0;
    return h;
  }

  _realize(h, now) {
    const ctx = this._ctx, def = h._def, bus = this._bus.sfx, vin = ctx.createGain();
    vin.gain.value = 0;
    vin.gain.setTargetAtTime(h._vol * def.gain, now, 0.1);
    const inst = { in: vin, panner: null, send: null, sources: [], base: null, end: Infinity, prio: 99 };
    let tail = vin;
    if (h._pos) { inst.panner = this._panner(h._pos); vin.connect(inst.panner); tail = inst.panner; }
    tail.connect(bus.dry);
    if (def.rev && def.send > 0) {
      inst.send = ctx.createGain(); inst.send.gain.value = def.send;
      tail.connect(inst.send); inst.send.connect(def.rev === 'hall' ? bus.hall : bus.room);
    }
    const k = this._kit;
    k.track = inst.sources; k.cents = 0;
    try { def.fn(k, vin, now + 0.01, k.rng); } catch (e) { this._warn('err:' + def.name, 'loop "' + def.name + '" failed: ' + e); }
    k.track = null;
    inst.base = inst.sources.map((s) => (s.detune ? s.detune.value : 0));
    h._inst = inst;
    if (h._pitch !== 1) h.setPitch(h._pitch);
  }

  _release(h, now, fade) {
    const inst = h._inst;
    if (!inst) return;
    h._inst = null;
    inst.in.gain.cancelScheduledValues(now);
    inst.in.gain.setTargetAtTime(0, now, Math.max(0.01, fade / 4));
    for (const s of inst.sources) { try { s.stop(now + fade + 0.1); } catch (e) { /* ended */ } }
    inst.end = now + fade + 0.15;
    this._dying.push(inst);
  }

  _dropLoop(h, fade) {
    const i = this._loops.indexOf(h);
    if (i >= 0) this._loops.splice(i, 1);
    if (this._ready) this._release(h, this._ctx.currentTime, Math.max(0, fade));
  }

  _dist2(h) {
    if (!h._pos) return 0;
    const p = h._pos, l = this._lpos, dx = p[0] - l[0], dy = p[1] - l[1], dz = p[2] - l[2];
    return dx * dx + dy * dy + dz * dz;
  }

  _updateLoops(now) {
    const ls = this._loops;
    let active = 0;
    for (let i = 0; i < ls.length; i++) if (ls[i]._inst) active++;
    for (let i = 0; i < ls.length; i++) {
      const h = ls[i], d2 = this._dist2(h);
      if (h._inst) {
        if (d2 > LOOP_OUT * LOOP_OUT) { this._release(h, now, 0.3); active--; }
      } else if (d2 < LOOP_IN * LOOP_IN) {
        if (active < MAX_LOOPS) { this._realize(h, now); active++; }
        else {
          // Replace the farthest active loop if this one is clearly closer.
          let far = null, fd = d2 * 1.4;
          for (let j = 0; j < ls.length; j++) { if (ls[j]._inst) { const dj = this._dist2(ls[j]); if (dj > fd) { fd = dj; far = ls[j]; } } }
          if (far) { this._release(far, now, 0.3); this._realize(h, now); }
        }
      }
    }
  }

  /**
   * Footstep on a ground surface.
   * @param {'grass'|'dirt'|'stone'|'sand'|'snow'|'mud'|'wood'|'water'|'ash'} surface
   * @param {{pos?:number[], run?:boolean, heavy?:boolean, volume?:number}} [opts]
   */
  footstep(surface, opts) {
    if (!this._ready) return;
    let def = FOOT[surface];
    if (!def) { this._warn('foot:' + surface, 'unknown surface "' + surface + '"'); def = FOOT.dirt; }
    this._spawn(def, opts, 'sfx', opts);
  }

  /**
   * Character vocal effort (formant synthesis).
   * @param {'attack'|'attack_heavy'|'hurt'|'death'|'roll'|'jump'|'drink'} kind
   * @param {{pitch?:number, pos?:number[], volume?:number}} [opts] pitch 0.7 (deep) .. 1.5 (high)
   */
  voice(kind, opts) {
    if (!this._ready) return;
    const def = VOICE[kind];
    if (!def) { this._warn('voice:' + kind, 'unknown voice "' + kind + '"'); return; }
    const s = this._scratch;
    s.pos = (opts && opts.pos) || null;
    s.volume = opts && opts.volume !== undefined ? opts.volume : 1;
    this._spawn(def, s, 'voice', opts && opts.pitch);
  }

  /**
   * Cross-fades the layered ambience towards a new state. Any subset of fields; cheap to call every frame.
   * @param {{biome?:'meadow'|'forest'|'swamp'|'mountain'|'ash'|'coast'|'citadel'|'village', hour?:number,
   *          rain?:number, wind?:number, water?:number, danger?:number}} state
   */
  setAmbience(state) {
    if (!state) return;
    if (!this._ready) { this._pendingAmb = Object.assign(this._pendingAmb || {}, state); return; }
    this._amb.set(state);
  }

  /**
   * Selects the music state (cross-fade 0.4 - 3 s). 'death' and 'victory' are stingers that
   * fall back to the last calm state (menu / creator / explore / village / none). Cheap to call every frame.
   * @param {'none'|'menu'|'creator'|'explore'|'village'|'combat'|'boss'|'death'|'victory'} state
   * @param {{biome?:string, boss?:'wolf'|'spider'|'knight'|'colossus'|'priestess'|'king', intensity?:number}} [opts]
   */
  setMusic(state, opts) {
    if (!this._ready) { this._pendingMusic = [state, opts ? Object.assign({}, opts) : undefined]; return; }
    this._music.set(state, opts);
  }

  /**
   * Thunder one-shot.
   * @param {number} distance01 0 = overhead crack, 1 = distant rumble
   */
  thunder(distance01) {
    if (!this._ready) return;
    this._spawn(THUNDER, EMPTY, 'ambience', distance01);
  }

  /** @returns {string[]} every SFX name accepted by play() */
  list() { return SFX_NAMES.slice(); }

  // --- Introspection helpers (test page / debugging; not part of the game contract) -----

  /** Names accepted by startLoop / footstep / voice / setMusic / setAmbience, plus ambience event names. */
  catalog() {
    return {
      sfx: SFX_NAMES.slice(), loops: LOOP_NAMES.slice(), footsteps: FOOT_NAMES.slice(), voices: VOICE_NAMES.slice(),
      music: MUSIC_STATES.slice(), bosses: BOSSES.slice(), biomes: BIOMES.slice(), ambienceEvents: AMB_NAMES.slice(),
      categories: Object.fromEntries(SFX_NAMES.map((n) => [n, SFX[n].cat])),
    };
  }

  /** Plays one ambience event recipe directly (bird, owl, frog, ...). */
  debugAmbienceEvent(name, opts) {
    if (this._ready && AMB[name]) this._spawn(AMB[name], opts, 'ambience');
  }

  /** Live counters. */
  get stats() {
    let loops = 0;
    for (const h of this._loops) if (h._inst) loops++;
    return { voices: this._voices.length, loops, loopHandles: this._loops.length, music: this._ready ? this._music.key : 'none' };
  }

  /** Internal nodes for measurement: `pre` = mix before the limiter, `out` = final output. */
  get debugNodes() { return this._ready ? { pre: this._master, out: this._out } : null; }
}

export default AudioEngine;
