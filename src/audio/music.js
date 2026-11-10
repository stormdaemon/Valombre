/**
 * VALOMBRE audio - generative music.
 *
 * A look-ahead sequencer drives "players" (one per music state) that schedule a bar at a time
 * on synthesized instruments. States cross-fade; 'death' and 'victory' are stingers that fall
 * back to the last calm state. All writing is modal (Dorian, Aeolian, Phrygian, Mixolydian...)
 * and expressed in scale degrees so the main theme can be quoted in any mode.
 */
import { clamp, smooth01 } from './core.js';
import { Instruments } from './instruments.js';

export const MUSIC_STATES = ['none', 'menu', 'creator', 'explore', 'village', 'combat', 'boss', 'death', 'victory'];
export const BOSSES = ['wolf', 'spider', 'knight', 'colossus', 'priestess', 'king'];

const MODES = {
  dorian: [0, 2, 3, 5, 7, 9, 10], aeolian: [0, 2, 3, 5, 7, 8, 10], phrygian: [0, 1, 3, 5, 7, 8, 10],
  mixolydian: [0, 2, 4, 5, 7, 9, 10], locrian: [0, 1, 3, 5, 6, 8, 10], phrygDom: [0, 1, 4, 5, 7, 8, 10],
};

/** MIDI note of scale degree `d` (0 = tonic, 7 = octave, negatives allowed). */
function deg(root, mode, d) {
  const n = mode.length, o = Math.floor(d / n);
  return root + mode[d - o * n] + 12 * o;
}

/** Chord on scale degree `ch` ([d] = open fifth): [bass, fifth, octave, third (or fifth), fifth above]. */
function chord(root, mode, ch) {
  const open = Array.isArray(ch);
  let d = (((open ? ch[0] : ch) % 7) + 7) % 7;
  if (d > 4) d -= 7;
  const b = deg(root - 12, mode, d);
  return [b, deg(root - 12, mode, d + 4), b + 12, open ? deg(root, mode, d + 4) : deg(root, mode, d + 2), deg(root, mode, d + 4)];
}

const _ = null;

/**
 * MAIN THEME ("Valombre"), 16 bars of 4 beats, as [scale degree, beats]. In D Dorian:
 * D A . G A | C . B A . | G F E G | E . . - | D A . G A | C . D E D | C B G B | A . . . |
 * F . E D C | D . C A . | B . A G B | A . . - | D A . G A | C . B A G | F E D C E | D . . .
 */
const THEME = [
  [[0, 1], [4, 2], [3, 0.5], [4, 0.5]], [[6, 1.5], [5, 0.5], [4, 2]], [[3, 1], [2, 1], [1, 1], [3, 1]], [[1, 3], [_, 1]],
  [[0, 1], [4, 2], [3, 0.5], [4, 0.5]], [[6, 1.5], [7, 0.5], [8, 1], [7, 1]], [[6, 1], [5, 1], [3, 1], [5, 1]], [[4, 4]],
  [[9, 1.5], [8, 0.5], [7, 1], [6, 1]], [[7, 1.5], [6, 0.5], [4, 2]], [[5, 1.5], [4, 0.5], [3, 1], [5, 1]], [[4, 3], [_, 1]],
  [[0, 1], [4, 2], [3, 0.5], [4, 0.5]], [[6, 1.5], [5, 0.5], [4, 1], [3, 1]], [[2, 1], [1, 1], [0, 1], [-1, 0.5], [1, 0.5]], [[0, 4]],
];
/** One chord per bar: Dm Am C Am | Dm C G A5 | F Dm G A5 | Dm Am C Dm. */
const THEME_CH = [0, 4, 6, 4, 0, 6, 3, [4], 2, 0, 3, [4], 0, 4, 6, 0];
const ARPS = [[0, 1, 2, 3, 4, 3, 2, 1], [0, 2, 3, 2, 4, 2, 3, 2], [0, 1, 3, 1, 2, 1, 3, 1]];

/** Village dance, 6/8, G Mixolydian: [degree, eighths] per bar, A and B strains of 8 bars. */
const DANCE = {
  A: [
    [[4, 2], [2, 1], [0, 2], [2, 1]], [[4, 2], [5, 1], [4, 3]], [[3, 2], [1, 1], [-1, 2], [1, 1]], [[3, 2], [4, 1], [3, 3]],
    [[4, 2], [2, 1], [0, 2], [2, 1]], [[5, 2], [4, 1], [3, 2], [2, 1]], [[1, 2], [2, 1], [3, 2], [1, 1]], [[0, 5], [_, 1]],
  ],
  B: [
    [[5, 2], [7, 1], [5, 2], [3, 1]], [[4, 2], [5, 1], [4, 2], [2, 1]], [[3, 2], [4, 1], [3, 2], [1, 1]], [[2, 3], [4, 3]],
    [[5, 2], [7, 1], [5, 2], [3, 1]], [[4, 2], [2, 1], [0, 2], [2, 1]], [[1, 1], [2, 1], [3, 1], [2, 2], [1, 1]], [[0, 6]],
  ],
  chA: [0, 0, 6, 6, 0, 3, 6, 0], chB: [3, 0, 6, 0, 3, 0, 6, 0],
};

/** Phrase pool for exploration (degrees, beats). */
const PHRASES = [
  [[0, 1], [1, 1], [2, 2], [1, 1], [0, 3]],
  [[4, 1.5], [3, 0.5], [2, 1], [1, 1], [0, 4]],
  [[0, 1], [4, 2], [3, 1], [4, 4]],
  [[7, 2], [6, 1], [4, 1], [5, 2], [4, 4]],
  [[2, 1], [3, 1], [4, 2], [6, 1], [4, 3]],
  [[4, 1], [5, 0.5], [4, 0.5], [2, 2], [1, 1], [2, 3]],
  [[0, 2], [-1, 1], [0, 1], [2, 4]],
  [[4, 3], [2, 1], [3, 3], [1, 1], [0, 4]],
  [[7, 1], [4, 1], [5, 1], [3, 1], [4, 2], [2, 2], [0, 4]],
  [[0, 0.5], [2, 0.5], [4, 1], [2, 2], [0, 4]],
  [[1, 1], [0, 1], [-3, 2], [0, 4]],
  [[4, 2], [7, 2], [6, 1], [5, 1], [4, 4]],
];
const RHYTHMS = [[1, 1, 2], [0.5, 0.5, 1, 2], [1.5, 0.5, 2], [1, 0.5, 0.5, 1, 3], [2, 1, 1, 4], [1, 1, 1, 1, 4], [0.5, 0.5, 0.5, 0.5, 2, 4], [3, 1, 4], [1, 2, 1, 4]];
const STABLE = [-3, 0, 2, 4, 7];

/** Per-biome exploration music. root = tonic of the melodic octave. */
const EXPLORE = {
  meadow: { tempo: 66, root: 62, mode: 'dorian', beds: [{ type: 'strings', p: 0.6, vel: 0.5 }], voices: ['lute', 'lute', 'lute', 'flute', 'flute'], gap: [2, 5], prog: [[0, 6, 0, 3], [0, 3, 6, 0], [0, 4, 6, 0]], quote: 'flute' },
  forest: { tempo: 54, root: 57, mode: 'aeolian', beds: [{ type: 'drone', p: 0.8, vel: 0.6 }, { type: 'choir', vowel: 'ooh', p: 0.55, vel: 0.4 }], voices: ['harp', 'harp', 'harp', 'flute', 'choir'], gap: [2, 5], prog: [[0, 5, 6, 0], [0, 3, 0, 6], [0, 0, 5, 4]], quote: 'harp' },
  swamp: { tempo: 48, root: 52, mode: 'locrian', beds: [{ type: 'drone', p: 0.9, vel: 0.6, detune: 14, fifth: false }], voices: ['lute', 'lute', 'lute', 'bell'], gap: [3, 6], prog: [[0, 1, 0, 4], [0, 4, 1, 0]], detune: 28, bellKind: 'dull', quote: 'lute' },
  mountain: { tempo: 50, root: 62, mode: 'mixolydian', beds: [{ type: 'fifths', p: 0.75, vel: 0.4 }], voices: ['bell', 'flute'], gap: [3, 6], prog: [[0, 3, 0, 4], [0, 4, 3, 0]], avoid: 2, bellKind: 'chime', hiFlute: true, quote: 'flute' },
  ash: { tempo: 56, root: 52, mode: 'phrygian', beds: [{ type: 'brass', p: 0.7, vel: 0.6 }, { type: 'drone', p: 0.5, vel: 0.45 }], voices: ['choir', 'strings'], gap: [3, 6], prog: [[0, 1, 0, 6], [0, 0, 1, 0], [0, 5, 1, 0]], drum: 0.45, quote: 'brass' },
  coast: { tempo: 60, root: 55, mode: 'mixolydian', beds: [{ type: 'harpwave', p: 0.7, vel: 0.3 }, { type: 'strings', p: 0.45, vel: 0.4 }], voices: ['flute', 'flute', 'flute', 'harp', 'harp'], gap: [2, 5], prog: [[0, 6, 3, 0], [0, 3, 6, 0], [0, 4, 3, 0]], quote: 'harp' },
  citadel: { tempo: 46, root: 50, mode: 'aeolian', beds: [{ type: 'choir', vowel: 'aah', p: 0.9, vel: 0.5 }], voices: ['strings', 'strings', 'strings', 'bell'], gap: [3, 6], prog: [[0, 5, 3, 4], [0, 3, 5, 4], [0, 6, 5, 4]], bellKind: 'church', bellLow: true, quote: 'choir' },
};
EXPLORE.village = EXPLORE.meadow;

/**
 * Battle music specs. stepDur = seconds per grid step, steps per bar, beat = steps per beat,
 * root = low tonic, prog = chord degree per bar, ost = string ostinato patterns (degree above
 * the chord root or null), drum patterns = velocities, motif = bars of [degree, steps].
 */
const BATTLE = {
  combat: {
    stepDur: 60 / 132 / 4, steps: 16, beat: 4, root: 38, mode: 'aeolian', prog: [0, 0, 5, 6, 0, 0, 3, 4],
    ost: [[0, _, 0, 0, 2, _, 0, _, 0, _, 0, 0, 4, _, 2, _], [0, 0, _, 0, 0, _, 2, _, 0, 0, _, 0, 4, _, 3, 2], [0, _, 4, _, 0, _, 4, _, 2, _, 4, _, 0, _, 4, 2]],
    war: [1, _, _, _, _, _, 0.6, _, 0.9, _, _, 0.5, _, _, 0.7, _],
    taiko: [_, _, 0.5, _, 0.7, _, 0.4, 0.4, _, _, 0.5, _, 0.8, _, 0.5, 0.5],
    motif: [[[0, 4], [4, 6], [3, 2], [4, 4]], [[6, 6], [5, 2], [4, 8]]], motifInst: 'brass', choir: 'aah', cluster: 0,
  },
  wolf: {
    stepDur: 0.19, steps: 6, beat: 3, root: 40, mode: 'aeolian', prog: [0, 0, 6, 0, 5, 5, 6, 4],
    ost: [[0, _, 0, 2, _, 0], [0, 0, 0, 4, _, 2], [0, _, 4, 2, _, 0]],
    war: [1, _, _, 0.7, _, _], taiko: [_, 0.4, 0.5, _, 0.4, 0.6],
    motif: [[[0, 2], [4, 4]], [[4, 6]], [[6, 2], [5, 1], [4, 3]], [[2, 6]]], motifInst: 'brass', choir: 'ooh', cluster: 0.2,
  },
  spider: {
    stepDur: 0.185, steps: 7, beat: 2, root: 37, mode: 'locrian', prog: [0, 0, 1, 0, 4, 4, 1, 0],
    ost: [[0, _, 1, _, 0, 6, _], [0, 0, _, 1, _, 4, 3], [0, _, 4, _, 1, _, 0]],
    war: [1, _, _, _, 0.8, _, _], frame: [_, 0.5, 0.6, _, _, 0.5, 0.7],
    motif: [[[7, 3], [8, 4]], [[7, 2], [4, 2], [5, 3]]], motifInst: 'trem', choir: 'ooh', cluster: 0.8, skitter: true, pizz: true,
  },
  knight: {
    stepDur: 60 / 108 / 4, steps: 16, beat: 4, root: 38, mode: 'dorian', prog: [0, 0, 6, 6, 0, 3, 4, 4],
    ost: [[0, _, _, 0, 0, _, 0, _, 0, _, _, 0, 4, _, 4, _], [0, _, 0, _, 0, 0, 0, _, 2, _, 2, _, 4, 4, 4, _]],
    war: [1, _, _, _, _, _, _, _, 0.9, _, _, _, _, _, _, _], taiko: [_, _, _, _, 0.6, _, _, _, _, _, _, _, 0.6, _, 0.4, 0.4],
    frame: [_, _, 0.3, 0.3, _, 0.3, 0.4, _, _, _, 0.3, 0.3, _, 0.3, 0.4, 0.4],
    motif: [[[0, 3], [0, 1], [0, 4], [2, 3], [1, 1], [0, 4]], [[4, 6], [3, 2], [4, 8]]], motifInst: 'brass', choir: 'aah', cluster: 0.1,
  },
  colossus: {
    stepDur: 60 / 80 / 2, steps: 8, beat: 2, root: 36, mode: 'phrygian', prog: [0, 0, 1, 0, 0, 5, 1, 0],
    ost: [[0, _, _, _, 0, _, 1, _], [0, _, _, 0, _, _, 1, 0]],
    war: [1, _, _, _, _, 0.9, _, _], taiko: [_, _, _, _, 0.6, _, _, 0.5],
    motif: [[[7, 4], [8, 4]], [[7, 8]], [[5, 4], [6, 4]], [[4, 8]]], motifInst: 'brass', choir: 'ooh', cluster: 0.6, heavy: true,
  },
  priestess: {
    stepDur: 60 / 132 / 2, steps: 6, beat: 2, root: 42, mode: 'phrygDom', prog: [0, 0, 1, 0, 3, 3, 1, 0],
    ost: [[0, _, 4, _, 2, _], [0, 2, 4, 2, 4, 2], [0, _, 4, 2, 4, _]],
    war: [0.9, _, _, _, _, _], frame: [_, _, 0.5, _, 0.5, _],
    motif: [[[4, 6]], [[5, 4], [4, 2]], [[2, 6]], [[1, 4], [0, 2]]], motifInst: 'choir', motifAlways: true, choir: 'aah', cluster: 0.4, bells: true, harpOst: true,
  },
  king: {
    stepDur: 60 / 120 / 4, steps: 16, beat: 4, root: 38, mode: 'aeolian', prog: [0, 4, 6, 4, 0, 6, 3, 4],
    ost: [[0, 0, 2, 0, 4, 0, 2, 0, 0, 0, 2, 0, 6, 4, 2, 0], [0, _, 0, 0, 4, _, 0, 0, 2, _, 0, 0, 4, 2, 0, _]],
    war: [1, _, _, 0.5, _, _, 0.7, _, 1, _, _, _, 0.7, _, 0.6, _], taiko: [_, _, 0.5, _, 0.7, _, _, 0.5, _, _, 0.5, 0.5, 0.8, _, 0.6, 0.6],
    motif: [[[0, 4], [4, 8], [3, 2], [4, 2]], [[6, 6], [5, 2], [4, 8]], [[3, 4], [2, 4], [1, 4], [3, 4]], [[1, 12], [_, 4]]],
    motifInst: 'brass', motifAlways: true, motifChoir: true, choir: 'aah', cluster: 0.3, bells: true,
  },
};

/** [fade-in of the new state, fade-out of the previous one] in seconds. */
const FADES = {
  none: [0, 2], menu: [2, 2.5], creator: [2, 2.5], explore: [3, 3], village: [2.5, 2.5],
  combat: [0.4, 1.5], boss: [0.5, 1.5], death: [0.05, 0.8], victory: [0.05, 0.6],
};
const CALM = { none: 1, menu: 1, creator: 1, explore: 1, village: 1 };
const NO_OPTS = Object.freeze({});

// ---------------------------------------------------------------------------------------

class Player {
  constructor(sys, key) {
    const k = sys.k;
    this.sys = sys; this.key = key; this.k = k; this.I = sys.inst; this.rng = sys.rng;
    this.dry = k.gain(1); this.rev = k.gain(1);
    this.fadeD = k.gain(0); this.fadeR = k.gain(0);
    this.dry.connect(this.fadeD); this.rev.connect(this.fadeR);
    this.fadeD.connect(sys.outDry); this.fadeR.connect(sys.outHall);
    this.strips = {};
    this.bar = 0; this.next = 0;
    this.dying = false; this.dieAt = 0;
    this.stinger = false; this.endAt = Infinity;
    this.intensity = 0.5; this.intensityT = 0.5;
  }
  s(name) { return this.I.strip(this, name); }
  fade(to, now, dur) {
    for (const p of [this.fadeD.gain, this.fadeR.gain]) {
      p.cancelScheduledValues(now);
      p.setValueAtTime(p.value, now);
      p.linearRampToValueAtTime(to, now + Math.max(0.02, dur));
    }
  }
  start(now, fadeIn) { this.next = now + 0.06; this.fade(1, now, fadeIn); }
  stop(now, fadeOut) { this.dying = true; this.dieAt = now + fadeOut + 0.4; this.fade(0, now, fadeOut); }
  dispose() {
    this.I.release(this);
    for (const n of [this.dry, this.rev, this.fadeD, this.fadeR]) { try { n.disconnect(); } catch (e) { /* gone */ } }
  }
  /** Schedules the next bar at `this.next` and advances it. */
  step() { this.next += 1; }
}

/** Main theme: 'menu' (harp, strings, distant choir) and the calmer 'creator' variation. */
class ThemePlayer extends Player {
  constructor(sys, key, creator) {
    super(sys, key);
    this.creator = creator;
    this.tempo = creator ? 54 : 60;
    this.root = creator ? 57 : 62;
    this.mode = MODES.dorian;
    this.arp = 0;
  }

  step() {
    const spb = 60 / this.tempo, t0 = this.next, bar = this.bar % 38, r = this.rng, I = this.I;
    let section = 'inter', b = -1, ch;
    if (bar < 2) { section = 'intro'; ch = bar === 0 ? 0 : [4]; }
    else if (bar < 18) { section = 't1'; b = bar - 2; ch = THEME_CH[b]; }
    else if (bar < 34) { section = 't2'; b = bar - 18; ch = THEME_CH[b]; }
    else ch = [0, 6, 3, [4]][bar - 34];
    if (bar === 0 || (b >= 0 && b % 8 === 0)) this.arp = r.int(0, ARPS.length - 1);
    const c = chord(this.root, this.mode, ch), pat = ARPS[this.arp], harp = this.s('harp'), str = this.s('strings');
    const soft = this.creator ? 0.8 : 1, bd = 4 * spb;

    // Harp accompaniment: eighth-note broken chords (quarter notes in the creator variation).
    const n = this.creator ? 4 : 8;
    for (let i = 0; i < n; i++) {
      const idx = pat[this.creator ? i * 2 : i], vel = (i === 0 ? 0.55 : idx >= 3 ? 0.24 : 0.32) * soft * r.range(0.85, 1.1);
      I.pluck(harp, t0 + i * (4 / n) * spb + r.range(0, 0.012), c[idx], vel, { type: 'harp' });
    }
    // Viol pad.
    const sv = (section === 'intro' && bar === 0 ? 0.45 : 0.8) * soft;
    I.strings(str, t0, c[0], bd, sv, { a: 0.9, r: 1.3 });
    I.strings(str, t0, c[1], bd, sv * 0.7, { a: 0.9, r: 1.3 });
    I.strings(str, t0, c[3], bd, sv * 0.6, { a: 0.9, r: 1.3 });
    // Distant choir (menu only): second statement and interlude.
    if (!this.creator && (section === 't2' || (section === 'inter' && bar >= 36))) {
      const ch2 = this.s('choir'), vowel = section === 't2' && b >= 8 ? 'aah' : 'ooh';
      I.choir(ch2, t0, c[2], bd, 0.5, { vowel, a: 0.9, r: 1.4 });
      I.choir(ch2, t0, c[4], bd, 0.4, { vowel, a: 0.9, r: 1.4 });
      if (b === 0 || b === 8) I.bell(this.s('bell'), t0, this.root + 12, 0.5, { kind: 'chime', decay: 2.5 });
    }
    if (b >= 0) this._melody(t0, spb, b, section);
    this.bar++; this.next += bd;
  }

  _melody(t0, spb, b, section) {
    const r = this.rng, I = this.I;
    let inst;
    if (this.creator) { if (section === 't1') { if (b < 8) return; inst = 'flute'; } else inst = 'harp'; }
    else inst = section === 't1' ? 'harp' : 'flute';
    let beat = 0;
    for (const [d, len] of THEME[b]) {
      if (d !== null) {
        const midi = deg(this.root, this.mode, d), t = t0 + beat * spb;
        const vel = 0.7 + 0.3 * Math.sin(Math.PI * ((b % 4) + beat / 4) / 4);
        if (inst === 'harp') {
          I.pluck(this.s('harp'), t + r.range(0, 0.01), midi, vel * 0.9, { type: 'harp' });
          if (len >= 2 && !this.creator) I.pluck(this.s('harp'), t + 0.02, midi - 12, vel * 0.35, { type: 'harp' });
        } else {
          I.flute(this.s('flute'), t, midi + (this.creator ? 0 : 12), len * spb * 0.96, vel * 0.75);
          if (!this.creator) I.pluck(this.s('harp'), t + r.range(0, 0.01), midi, vel * 0.45, { type: 'harp' });
        }
      }
      beat += len;
    }
  }
}

/** Village: gentle 6/8 dance for lute, recorder and frame drum. */
class DancePlayer extends Player {
  constructor(sys, key) {
    super(sys, key);
    this.eighth = 0.205; this.root = 67; this.mode = MODES.mixolydian;
    this.plan = []; this.pi = 0;
  }

  _plan() {
    const r = this.rng, p = [];
    const add = (sec, pass, rep) => { for (let b = 0; b < 8; b++) p.push({ sec, b, pass, rep }); };
    p.push({ sec: 'intro', b: 0 }, { sec: 'intro', b: 1 });
    add('A', 0, 0); add('A', 0, 1); add('B', 0, 0); add('B', 0, 1);
    add('A', 1, 0); add('A', 1, 1); add('B', 1, 0); add('B', 1, 1);
    p.push({ sec: 'outro', b: 0 }, { sec: 'outro', b: 1 });
    for (let i = r.int(4, 7); i > 0; i--) p.push({ sec: 'rest', b: 0 });
    this.plan = p; this.pi = 0;
    this.swap = r.chance(0.5);
  }

  step() {
    if (this.pi >= this.plan.length) this._plan();
    const e = this.eighth, t0 = this.next, r = this.rng, I = this.I, it = this.plan[this.pi++];
    this.next += 6 * e;
    this.bar++;
    if (it.sec === 'rest') return;
    const tune = it.sec === 'A' || it.sec === 'B';
    const chd = tune ? DANCE[it.sec === 'A' ? 'chA' : 'chB'][it.b] : 0;
    const c = chord(this.root, this.mode, chd), lute = this.s('lute'), drum = this.s('drum');
    const out = it.sec === 'outro' ? (it.b ? 0.5 : 0.75) : 1;

    // Lute: bass - strum - bass - strum.
    I.pluck(lute, t0, c[0], 0.6 * out, { type: 'lute' });
    I.pluck(lute, t0 + 3 * e, c[1], 0.45 * out, { type: 'lute' });
    for (const st of [2, 5]) {
      for (let i = 2; i < 5; i++) I.pluck(lute, t0 + st * e + (i - 2) * 0.016 + r.range(0, 0.006), c[i], 0.3 * out * r.range(0.85, 1.1), { type: 'lute' });
    }
    // Frame drum: dum . tak dum . tak
    I.drum(drum, t0, 'dum', 0.55 * out);
    I.drum(drum, t0 + 2 * e, 'tak', 0.22 * out);
    I.drum(drum, t0 + 3 * e, 'dum', 0.36 * out);
    I.drum(drum, t0 + 5 * e, 'tak', 0.27 * out);
    if (tune && it.b === 7 && r.chance(0.6)) I.drum(drum, t0 + 4.5 * e, 'tak', 0.18);
    if (!tune) return;

    // Melody: recorder first time through, lute (recorder joins on B) the second time.
    const first = (it.pass === 0) !== this.swap;
    let pos = 0;
    for (const [d0, len] of DANCE[it.sec][it.b]) {
      if (d0 !== null) {
        const t = t0 + pos * e, midi = deg(this.root, this.mode, d0), orn = it.rep === 1 && len === 2 && r.chance(0.3);
        const rec = first || it.sec === 'B';
        if (rec) {
          if (orn) {
            I.flute(this.s('flute'), t, deg(this.root, this.mode, d0 + 1), e * 0.45, 0.5, { vib: 0 });
            I.flute(this.s('flute'), t + e * 0.5, midi, e * 1.4, 0.6);
          } else I.flute(this.s('flute'), t, midi, len * e * 0.9, 0.6 + (pos === 0 ? 0.1 : 0));
        }
        if (!first) I.pluck(lute, t + r.range(0, 0.008), midi - (it.sec === 'B' ? 12 : 0), 0.6, { type: 'lute' });
      }
      pos += len;
    }
  }
}

/** Exploration: sparse beds and phrases from pools, with long silences and theme quotes. */
class ExplorePlayer extends Player {
  constructor(sys, key, biome) {
    super(sys, key);
    this.sp = EXPLORE[biome] || EXPLORE.meadow;
    this.mode = MODES[this.sp.mode];
    this.prog = null; this.chIdx = 0; this.ch = 0;
    this.rest = 0;
    this.untilQuote = this.rng.int(3, 5);
    this.bedOn = this.sp.beds.map(() => false);
  }

  step() {
    const sp = this.sp, spb = 60 / sp.tempo, t0 = this.next, r = this.rng, I = this.I, bd = 4 * spb;
    if (this.bar % 2 === 0) {
      if (!this.prog || this.chIdx >= this.prog.length) {
        this.prog = r.pick(sp.prog); this.chIdx = 0;
        for (let i = 0; i < sp.beds.length; i++) this.bedOn[i] = r.chance(sp.beds[i].p) || this.bar === 0;
      }
      this.ch = this.prog[this.chIdx++];
      this._beds(t0, 2 * bd, spb);
    }
    if (this.rest > 0) this.rest--;
    else {
      const beats = this._speak(t0 + (this.bar === 0 ? 0.4 : r.range(0, 1) * spb), spb);
      this.rest = Math.ceil(beats / 4) + r.int(sp.gap[0], sp.gap[1]);
    }
    if (sp.drum && this.bar % 2 === 1 && r.chance(sp.drum)) {
      const d = this.s('drum');
      I.drum(d, t0, 'war', 0.5);
      I.drum(d, t0 + 1.5 * spb, 'war', 0.28);
      if (r.chance(0.5)) I.drum(d, t0 + 2 * spb, 'war', 0.38);
    }
    this.bar++; this.next += bd;
  }

  _beds(t, dur, spb) {
    const sp = this.sp, I = this.I, r = this.rng, c = chord(sp.root, this.mode, this.ch);
    for (let i = 0; i < sp.beds.length; i++) {
      if (!this.bedOn[i]) continue;
      const b = sp.beds[i], v = b.vel * r.range(0.85, 1.05);
      if (b.type === 'strings') {
        const s = this.s('strings');
        I.strings(s, t, c[0], dur, v, { a: 1.6, r: 2.2 });
        I.strings(s, t, c[1], dur, v * 0.7, { a: 1.6, r: 2.2 });
        I.strings(s, t, c[3], dur, v * 0.6, { a: 1.6, r: 2.2 });
      } else if (b.type === 'drone') {
        I.drone(this.s('drone'), t, sp.root - 12, dur, v, { fifth: b.fifth, detune: b.detune, a: 2, r: 3 });
      } else if (b.type === 'choir') {
        const s = this.s('choir');
        I.choir(s, t, c[2], dur, v, { vowel: b.vowel, a: 1.6, r: 2.2 });
        I.choir(s, t, c[4], dur, v * 0.8, { vowel: b.vowel, a: 1.6, r: 2.2 });
        if (b.vowel === 'aah') I.choir(s, t, c[3], dur, v * 0.7, { vowel: 'aah', a: 1.6, r: 2.2 });
      } else if (b.type === 'fifths') {
        const s = this.s('strings');
        I.strings(s, t, c[2] + 12, dur, v, { a: 2, r: 2.5 });
        I.strings(s, t, c[4] + 12, dur, v * 0.8, { a: 2, r: 2.5 });
      } else if (b.type === 'brass') {
        const s = this.s('brass');
        I.brass(s, t, c[0], dur * 0.6, v, { a: 1.4, r: 1.8, bright: 0.5 });
        I.brass(s, t, c[1], dur * 0.6, v * 0.6, { a: 1.4, r: 1.8, bright: 0.5 });
      } else if (b.type === 'harpwave') {
        const s = this.s('harp'), order = [0, 1, 2, 3, 4, 3, 2, 1];
        for (let n = 0; n < 8; n++) I.pluck(s, t + n * spb + r.range(0, 0.02), c[order[n]], v * (n === 0 ? 1.2 : 0.8), { type: 'harp' });
      }
    }
  }

  _gen() {
    const r = this.rng, rh = r.pick(RHYTHMS), out = [];
    let d = r.pick([0, 2, 4, 4, 7]);
    for (let i = 0; i < rh.length; i++) {
      if (i === rh.length - 1) { let best = STABLE[0]; for (const s of STABLE) if (Math.abs(s - d) < Math.abs(best - d)) best = s; d = best; }
      out.push([d, rh[i]]);
      const u = r.next();
      d = clamp(d + (u < 0.4 ? -1 : u < 0.75 ? 1 : u < 0.85 ? 2 : u < 0.93 ? -2 : r.pick([3, -3, 4])), -3, 9);
    }
    return out;
  }

  _speak(t, spb) {
    const sp = this.sp, r = this.rng;
    let notes, inst, shift = 0;
    if (--this.untilQuote <= 0) {
      this.untilQuote = r.int(5, 8);
      inst = sp.quote;
      notes = r.chance(0.5) ? THEME[0].concat(THEME[1]) : THEME[0].concat(THEME[1], THEME[2], THEME[3]);
    } else {
      inst = r.pick(sp.voices);
      if (r.chance(0.55)) { notes = r.pick(PHRASES); shift = r.pick([0, 0, 0, 2, 4, -3]); } else notes = this._gen();
    }
    return this._play(inst, notes, shift, t, spb);
  }

  _play(inst, notes, shift, t, spb) {
    const sp = this.sp, r = this.rng, I = this.I;
    const slow = inst === 'choir' || inst === 'bell' || inst === 'brass' ? 2 : 1;
    let beat = 0;
    for (const [d0, len0] of notes) {
      const len = len0 * slow;
      if (d0 !== null) {
        let d = d0 + shift;
        if (sp.avoid !== undefined && ((d % 7) + 7) % 7 === sp.avoid) d -= 1;
        const midi = deg(sp.root, this.mode, d), tt = t + beat * spb, vel = r.range(0.6, 0.85);
        const cents = sp.detune ? r.range(-sp.detune, sp.detune) : 0;
        if (inst === 'lute') {
          I.pluck(this.s('lute'), tt + r.range(0, 0.015), midi, vel, { type: 'lute', cents });
          if (len >= 2 && r.chance(0.3)) I.pluck(this.s('lute'), tt + 0.5 * spb, midi - 12, vel * 0.5, { type: 'lute', cents });
        } else if (inst === 'harp') {
          I.pluck(this.s('harp'), tt + r.range(0, 0.015), midi + 12, vel, { type: 'harp', cents });
          if (len >= 2 && r.chance(0.35)) I.pluck(this.s('harp'), tt + 0.03, midi, vel * 0.5, { type: 'harp', cents });
        } else if (inst === 'flute') I.flute(this.s('flute'), tt, midi + (sp.hiFlute ? 24 : 12), len * spb * 0.95, vel * 0.7);
        else if (inst === 'choir') I.choir(this.s('choir'), tt, midi, len * spb, vel * 0.7, { vowel: sp.mode === 'phrygian' ? 'ooh' : 'aah', a: 0.3, r: 0.6 });
        else if (inst === 'strings') I.strings(this.s('strings'), tt, midi, len * spb, vel * 1.6, { solo: true, a: 0.14, r: 0.35 });
        else if (inst === 'bell') I.bell(this.s('bell'), tt, midi + (sp.bellLow ? -12 : 12), vel, { kind: sp.bellKind });
        else if (inst === 'brass') I.brass(this.s('brass'), tt, midi - 12, len * spb, vel * 0.9, { a: 0.25, r: 0.5, bright: 0.6 });
      }
      beat += len;
    }
    return beat;
  }
}

/** Combat and boss music: ostinato strings, war drums, layers driven by intensity. */
class BattlePlayer extends Player {
  constructor(sys, key, id) {
    super(sys, key);
    this.sp = BATTLE[id] || BATTLE.combat;
    this.mode = MODES[this.sp.mode];
    this.pat = 0;
  }

  step() {
    const sp = this.sp, I = this.I, r = this.rng, t0 = this.next, sd = sp.stepDur, n = sp.steps, bar = this.bar, mode = this.mode;
    this.intensity += (this.intensityT - this.intensity) * (bar === 0 ? 1 : 0.6);
    const it = this.intensity, L1 = smooth01((it - 0.2) / 0.2), L2 = smooth01((it - 0.55) / 0.2);
    let cd = ((sp.prog[bar % sp.prog.length] % 7) + 7) % 7;
    if (cd > 4) cd -= 7;
    if (bar % 4 === 0 && bar > 0) this.pat = r.int(0, sp.ost.length - 1);
    const pat = sp.ost[this.pat], fill = bar % 4 === 3, fillFrom = n - Math.max(2, n >> 2);
    const st = this.s('stacc'), drum = this.s('drum'), str = this.s('strings'), barDur = n * sd;

    for (let s = 0; s < n; s++) {
      const t = t0 + s * sd, acc = s === 0 ? 1 : s % sp.beat === 0 ? 0.85 : 0.62, d = pat[s];
      if (d !== null) {
        const m = deg(sp.root + 12, mode, cd + d);
        I.stacc(st, t, m, acc * (0.7 + 0.3 * it), { dur: Math.max(0.12, sd * 1.3) });
        I.stacc(st, t, m + 12, acc * (0.3 + 0.3 * L1), { dur: Math.max(0.1, sd * 1.1) });
        if (sp.pizz) I.pluck(this.s('lute'), t, m + 12, acc * 0.6, { type: 'lute' });
        if (sp.harpOst) I.pluck(this.s('harp'), t, m + 24, acc * 0.5, { type: 'harp' });
      }
      const w = sp.war[s], tk = sp.taiko ? sp.taiko[s] : null, fr = sp.frame ? sp.frame[s] : null;
      if (w) {
        I.drum(drum, t, 'war', w * (0.7 + 0.2 * it));
        if (sp.heavy) I.drum(drum, t + 0.012, 'taiko', w * 0.7);
      }
      if (fill && s >= fillFrom && L1 > 0.05) I.drum(drum, t, 'taiko', (0.45 + 0.5 * (s - fillFrom) / (n - fillFrom)) * L1);
      else if (tk && L1 > 0.05) I.drum(drum, t, 'taiko', tk * L1 * (1 + 0.25 * L2));
      if (fr) I.drum(drum, t, s % sp.beat === 0 ? 'dum' : 'tak', fr * (0.5 + 0.5 * L1));
    }

    // Pedal bass.
    I.strings(str, t0, deg(sp.root, mode, cd), barDur, 0.5, { a: 0.05, r: 0.2 });
    I.strings(str, t0, deg(sp.root, mode, cd + 4), barDur, 0.3, { a: 0.05, r: 0.2 });

    // Brass stabs on every other bar.
    if (L1 > 0.05 && bar % 2 === 0) {
      const b = this.s('brass'), len = sd * sp.beat * 1.5;
      I.brass(b, t0, deg(sp.root + 12, mode, cd), len, 0.8 * L1, { a: 0.03, r: 0.18 });
      I.brass(b, t0, deg(sp.root + 12, mode, cd + 4), len, 0.6 * L1, { a: 0.03, r: 0.18 });
    }

    // Motif.
    const M = sp.motif.length, mv = sp.motifAlways ? Math.max(0.55, L2) : L2;
    if (mv > 0.05) {
      const mb = bar % (M * 2);
      if (mb < M) this._motif(sp.motif[mb], t0, sd, mv, L2);
    }

    // Choir pad.
    if (L2 > 0.05) {
      const c = this.s('choir'), o = { vowel: sp.choir, a: 0.18, r: 0.45 };
      I.choir(c, t0, deg(sp.root + 24, mode, cd), barDur, 0.36 * L2, o);
      I.choir(c, t0, deg(sp.root + 24, mode, cd + 4), barDur, 0.28 * L2, o);
      I.choir(c, t0, deg(sp.root + 24, mode, cd + 2), barDur, 0.24 * L2, o);
    }

    // Dissonant cluster stabs.
    if (sp.cluster && bar % 4 === 2 && r.chance(sp.cluster * (0.5 + 0.5 * it))) {
      const t = t0 + (n >> 1) * sd, m = deg(sp.root + 24, mode, cd + 4);
      for (const off of [0, 1, 6]) I.stacc(st, t, m + off, 0.7, { dur: 0.5 });
      I.brass(this.s('brass'), t, sp.root + 13, 0.5, 0.6, { a: 0.04, r: 0.3 });
      I.brass(this.s('brass'), t, sp.root + 12, 0.5, 0.6, { a: 0.04, r: 0.3 });
    }
    if (sp.heavy && L2 > 0.05 && bar % 2 === 1) {
      I.brass(this.s('brass'), t0, sp.root + 12, barDur * 0.9, 0.6 * L2, { a: 0.5, r: 0.5, bright: 0.5 });
      I.brass(this.s('brass'), t0, sp.root + 13, barDur * 0.9, 0.45 * L2, { a: 0.5, r: 0.5, bright: 0.5 });
    }
    if (sp.bells && bar % 2 === 0) I.bell(this.s('bell'), t0, deg(sp.root + 24, mode, cd), 0.5 + 0.3 * L2, { kind: 'church', decay: 2 });
    if (sp.skitter && L1 > 0.05) {
      for (let s = 0; s < n * 2; s++) {
        if (r.chance(0.45)) I.pluck(this.s('harp'), t0 + s * sd * 0.5, deg(sp.root + 36, mode, r.int(0, 8)), 0.35 * L1, { type: 'harp', dur: 0.15 });
      }
    }
    this.bar++; this.next += barDur;
  }

  _motif(notes, t0, sd, vel, L2) {
    const sp = this.sp, I = this.I, mode = this.mode;
    let pos = 0;
    for (const [d, len] of notes) {
      if (d !== null) {
        const t = t0 + pos * sd, m = deg(sp.root + 24, mode, d), dur = len * sd;
        if (sp.motifInst === 'brass') {
          I.brass(this.s('brass'), t, m, dur * 0.92, 0.9 * vel, { a: 0.04, r: 0.12 });
          I.brass(this.s('brass'), t, m - 12, dur * 0.92, 0.65 * vel, { a: 0.04, r: 0.12 });
          if (sp.motifChoir && L2 > 0.05) I.choir(this.s('choir'), t, m, dur, 0.6 * L2, { vowel: 'aah', a: 0.08, r: 0.3 });
        } else if (sp.motifInst === 'choir') {
          I.choir(this.s('choir'), t, m, dur, 0.8 * vel, { vowel: 'aah', a: 0.1, r: 0.35 });
          I.choir(this.s('choir'), t, m - 12, dur, 0.55 * vel, { vowel: 'aah', a: 0.1, r: 0.35 });
        } else {
          // Tremolo strings with a minor-second shadow.
          for (let i = 0; i < len * 2; i++) {
            I.stacc(this.s('stacc'), t + i * sd * 0.5, m + 12, 0.5 * vel, { dur: sd * 0.6 });
            I.stacc(this.s('stacc'), t + i * sd * 0.5, m + 13, 0.3 * vel, { dur: sd * 0.6 });
          }
        }
      }
      pos += len;
    }
  }
}

/** One-shot stingers: 'death' lament and 'victory' fanfare. */
class StingerPlayer extends Player {
  constructor(sys, key, kind) {
    super(sys, key);
    this.kind = kind; this.stinger = true; this.done = false;
    if (kind === 'victory') { this.dry.gain.value = 0.7; this.rev.gain.value = 0.7; }
  }

  step() {
    const t = this.next;
    this.next += 1;
    if (this.done) return;
    this.done = true;
    this.endAt = t + (this.kind === 'death' ? this._death(t) : this._victory(t));
  }

  /** Descending lament A G F Eb D over a tolling bell (about 3.7 s plus reverb tail). */
  _death(t) {
    const I = this.I, str = this.s('strings'), ch = this.s('choir'), bell = this.s('bell');
    const line = [69, 67, 65, 63, 62], durs = [0.5, 0.45, 0.5, 0.6, 1.1];
    let tt = t + 0.08;
    for (let i = 0; i < 5; i++) {
      I.strings(str, tt, line[i], durs[i] * 0.96, 1.6, { solo: true, a: 0.08, r: 0.28 });
      I.strings(str, tt, line[i] - 12, durs[i], 0.9, { a: 0.1, r: 0.3 });
      tt += durs[i];
    }
    I.drum(this.s('drum'), t + 0.08, 'war', 0.7);
    I.bell(bell, t + 0.08, 50, 0.9, { kind: 'church', decay: 2.2 });
    I.bell(bell, t + 2.13, 50, 0.6, { kind: 'church', decay: 1.3 });
    I.choir(ch, t + 0.08, 50, 2.6, 0.8, { vowel: 'ooh', a: 0.5, r: 0.7 });
    I.choir(ch, t + 0.08, 45, 2.6, 0.7, { vowel: 'ooh', a: 0.5, r: 0.7 });
    return 3.7;
  }

  /** Fanfare quoting the head of the main theme, resolving on a D major chord (about 6.5 s). */
  _victory(t) {
    const I = this.I, spb = 0.34, brass = this.s('brass'), str = this.s('strings'), ch = this.s('choir');
    const drum = this.s('drum'), bell = this.s('bell'), harp = this.s('harp'), st = this.s('stacc');
    const mot = [[62, 1], [69, 2], [67, 0.5], [69, 0.5], [72, 1.5], [71, 0.5], [69, 2]];
    let beat = 0;
    for (const [m, len] of mot) {
      const tt = t + beat * spb, d = len * spb * 0.92;
      I.brass(brass, tt, m, d, 0.95, { a: 0.04, r: 0.12 });
      I.brass(brass, tt, m - 12, d, 0.7, { a: 0.04, r: 0.12 });
      I.stacc(st, tt, m + 12, 0.7, { dur: Math.min(0.35, d) });
      beat += len;
    }
    const o = { a: 0.08, r: 0.3 };
    I.strings(str, t, 50, 4 * spb, 0.9, o); I.strings(str, t, 57, 4 * spb, 0.7, o);
    I.strings(str, t + 4 * spb, 48, 2 * spb, 0.9, o); I.strings(str, t + 4 * spb, 55, 2 * spb, 0.7, o);
    I.strings(str, t + 6 * spb, 45, 2 * spb, 0.9, o); I.strings(str, t + 6 * spb, 52, 2 * spb, 0.7, o);
    for (const [b, v] of [[0, 0.9], [1, 0.7], [4, 0.9], [6, 0.8]]) I.drum(drum, t + b * spb, 'war', v);
    for (let i = 0; i < 6; i++) I.drum(drum, t + (6.5 + i * 0.25) * spb, 'taiko', 0.35 + i * 0.1);
    const tf = t + 8 * spb, hold = 2.3, scale = [62, 64, 66, 67, 69, 71, 73, 74, 78, 81, 86];
    for (let i = 0; i < scale.length; i++) I.pluck(harp, tf - 0.36 + i * 0.033, scale[i], 0.5, { type: 'harp' });
    for (const [m, v] of [[50, 0.9], [57, 0.8], [62, 0.9], [66, 0.7], [74, 0.9]]) I.brass(brass, tf, m, hold, v, { a: 0.05, r: 0.9 });
    for (const [m, v] of [[38, 1], [50, 0.8], [69, 0.6], [78, 0.5]]) I.strings(str, tf, m, hold, v, { a: 0.06, r: 1.0 });
    for (const [m, v] of [[62, 0.7], [66, 0.6], [69, 0.6], [74, 0.5]]) I.choir(ch, tf, m, hold, v, { vowel: 'aah', a: 0.12, r: 1.0 });
    I.drum(drum, tf, 'war', 1); I.drum(drum, tf + 0.01, 'taiko', 0.8);
    I.bell(bell, tf, 62, 0.8, { kind: 'church', decay: 2.6 });
    I.bell(bell, tf + 0.02, 86, 0.6, { kind: 'chime', decay: 2 });
    I.bell(bell, tf + 0.3, 93, 0.4, { kind: 'chime', decay: 1.8 });
    return 8 * spb + hold + 1.2;
  }
}

/** Music state machine. `host` = { kit, rng, outDry, outHall, warn }. */
export class Music {
  constructor(host) {
    this.host = host;
    this.k = host.kit; this.ctx = host.kit.ctx; this.rng = host.rng;
    this.inst = new Instruments(host.kit);
    this.outDry = host.outDry; this.outHall = host.outHall;
    /** @type {Player[]} */ this.players = [];
    /** @type {Player|null} */ this.cur = null;
    this.curKey = 'none';
    this.stKey = ''; this.stTime = -10;
    this._keys = {};
    this.calm = { state: 'none', biome: 'meadow' };
    this.biome = 'meadow'; this.boss = 'wolf';
    this.intensity = 0.5;
  }

  /** Current resolved state key, e.g. 'explore:forest', 'boss:king', 'none'. */
  get key() { return this.curKey; }

  /**
   * @param {string} state one of MUSIC_STATES
   * @param {{biome?:string, boss?:string, intensity?:number}} [opts]
   */
  set(state, opts) {
    if (!MUSIC_STATES.includes(state)) { this.host.warn('music:' + state); return; }
    const o = opts || NO_OPTS, now = this.ctx.currentTime;
    if (o.biome) this.biome = o.biome;
    if (o.boss) { if (BATTLE[o.boss]) this.boss = o.boss; else this.host.warn('boss:' + o.boss); }
    const key = this._key(state, this.biome, this.boss);
    if (typeof o.intensity === 'number') this.intensity = clamp(o.intensity, 0, 1);
    else if ((state === 'combat' || state === 'boss') && key !== this.curKey) this.intensity = 0.5;
    if (this.cur) this.cur.intensityT = this.intensity;
    if (state === 'death' || state === 'victory') {
      // Stingers are edge-triggered: a caller repeating the request every frame gets one stinger.
      const held = key === this.stKey && now - this.stTime < 1.0;
      this.stKey = key; this.stTime = now;
      if (!held && key !== this.curKey) this._switch(state, key);
      return;
    }
    if (CALM[state]) {
      this.calm.state = state; this.calm.biome = this.biome;
      // A calm request during a stinger is deferred until the stinger has finished.
      if (this.cur && this.cur.stinger && !this.cur.dying) return;
    }
    this._switch(state, key);
  }

  _key(state, biome, boss) {
    if (state !== 'explore' && state !== 'boss') return state;
    const sub = state === 'explore' ? (EXPLORE[biome] ? biome : 'meadow') : boss;
    const m = this._keys[state] || (this._keys[state] = {});
    return m[sub] || (m[sub] = state + ':' + sub);       // memoised: no string building per frame
  }

  _switch(state, key, fadeIn) {
    if (key === this.curKey) return;
    const now = this.ctx.currentTime, f = FADES[state];
    if (this.cur) { this.cur.stop(now, f[1]); this.cur = null; }
    this.curKey = key;
    let p = null;
    if (state === 'menu' || state === 'creator') p = new ThemePlayer(this, key, state === 'creator');
    else if (state === 'village') p = new DancePlayer(this, key);
    else if (state === 'explore') p = new ExplorePlayer(this, key, key.split(':')[1]);
    else if (state === 'combat') p = new BattlePlayer(this, key, 'combat');
    else if (state === 'boss') p = new BattlePlayer(this, key, key.split(':')[1]);
    else if (state === 'death' || state === 'victory') p = new StingerPlayer(this, key, state);
    if (p) {
      p.intensity = p.intensityT = this.intensity;
      p.start(now, fadeIn !== undefined ? fadeIn : f[0]);
      this.players.push(p);
      this.cur = p;
    }
  }

  /** Called every frame: look-ahead scheduling, stinger fallback, disposal of faded players. */
  update(now) {
    const ps = this.players;
    for (let i = ps.length - 1; i >= 0; i--) {
      const p = ps[i];
      if (p.dying) {
        if (now > p.dieAt) { p.dispose(); ps[i] = ps[ps.length - 1]; ps.pop(); }
        continue;
      }
      if (p.next < now - 0.2) p.next = now + 0.05;        // tab was asleep: resynchronise
      let guard = 0;
      while (p.next < now + 0.3 && guard++ < 8) p.step();
      if (p.stinger && now > p.endAt) {
        const c = this.calm;
        this._switch(c.state, this._key(c.state, c.biome, this.boss), 3);
      }
    }
  }

  dispose() {
    for (const p of this.players) p.dispose();
    this.players.length = 0; this.cur = null; this.curKey = 'none';
  }
}
