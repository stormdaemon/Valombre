/**
 * VALOMBRE audio - shared building blocks for sound recipes (used by sfx, footsteps, voice,
 * ambience events). Every helper takes the Kit `k`, a destination node `o` and a start time.
 */

/** Inharmonic partial sets. */
export const METAL = [1, 1.52, 2.31, 3.17, 4.23, 5.43];
export const BELL = [0.5, 1, 1.19, 1.5, 2, 2.51, 3.01, 4.17];
export const BELL_G = [0.45, 1, 0.6, 0.3, 0.5, 0.22, 0.14, 0.1];
export const BELL_D = [1.25, 1, 0.8, 0.6, 0.5, 0.35, 0.25, 0.18];
export const BAR = [1, 2.76, 5.4, 8.93];
export const WOOD = [1, 1.87, 3.3, 5.1];

/** Vowel formants [frequency, Q, gain] for an adult male voice. */
export const V = {
  a: [[730, 7, 1], [1090, 9, 0.7], [2440, 10, 0.3]],
  e: [[530, 8, 1], [1840, 10, 0.5], [2480, 10, 0.3]],
  i: [[270, 8, 1], [2290, 12, 0.4], [3010, 12, 0.25]],
  o: [[570, 8, 1], [840, 9, 0.6], [2410, 10, 0.2]],
  u: [[300, 8, 1], [870, 9, 0.45], [2240, 10, 0.15]],
  uh: [[640, 7, 1], [1190, 9, 0.6], [2390, 10, 0.25]],
};

/** Scales a formant set (smaller / larger vocal tract). */
export function fset(v, s) { return v.map(([f, q, g]) => [f * s, q, g]); }

/** Air movement: band-passed noise whose centre rises then falls. */
export function whoosh(k, o, t, dur, f0, fm, f1, q, vol, kind = 'pink', peakAt = 0.45) {
  return k.nz(o, { kind, t, dur, shape: 'bell', peakAt, f: f0, fmid: fm, f1, q, vol });
}

/** Low body thump: sine with a fast downward glide. */
export function thump(k, o, t, f0, f1, dur, vol) {
  return k.tone(o, { f: f0, f1, glide: dur * 0.6, t, dur, vol, a: 0.002 });
}

/** Very short band-passed noise transient. */
export function click(k, o, t, f, vol, dur = 0.015, q = 1.2) {
  return k.nz(o, { t, dur, f, q, vol, a: 0.0008 });
}

/** Glassy / chime ping. */
export function ping(k, o, t, f, vol, decay) {
  k.modal(o, { t, f, ratios: BAR, gains: [1, 0.35, 0.12, 0.04], decays: [1, 0.45, 0.2, 0.1], decay, vol });
}

/** Struck metal ring. */
export function metal(k, o, t, f, vol, decay, jit = 0.03) {
  k.modal(o, { t, f, ratios: METAL, gains: [1, 0.7, 0.55, 0.4, 0.3, 0.2], decays: [1, 0.8, 0.6, 0.45, 0.3, 0.2], decay, vol, jit });
}

/** Church bell (hum, prime, tierce, quint, nominal...). `f` is the prime. */
export function bell(k, o, t, f, vol, decay) {
  k.modal(o, { t, f, ratios: BELL, gains: BELL_G, decays: BELL_D, decay, vol, a: 0.002 });
}

/** A handful of random clicks spread over `span` seconds (debris, grit). */
export function scatter(k, o, t, n, span, fLo, fHi, vol, dur = 0.01) {
  const r = k.rng;
  for (let i = 0; i < n; i++) click(k, o, t + r.next() * span, r.range(fLo, fHi), vol * r.range(0.4, 1), dur * r.range(0.6, 1.5), 2);
}

/** Burst of fire crackle fading out over `dur`. */
export function crackle(k, o, t, dur, vol, hp = 1200) {
  const s = k.buf(k.res.baked('crackle'), t, { loop: true, stop: t + dur + 0.05, rate: k.rng.range(0.8, 1.3) });
  const h = k.bq('highpass', hp, 0.7), g = k.gain(0);
  g.gain.setValueAtTime(vol, t); g.gain.linearRampToValueAtTime(0, t + dur);
  s.connect(h); h.connect(g); g.connect(o);
}

/** Dry bone clacks. */
export function bones(k, o, t, n, span, vol) {
  const r = k.rng;
  for (let i = 0; i < n; i++) {
    const tt = t + r.next() * span, f = r.range(900, 2400);
    k.modal(o, { t: tt, f, ratios: [1, 1.87, 3.3], gains: [0.5, 0.35, 0.2], decays: [0.045, 0.03, 0.02], vol: vol * r.range(0.5, 1), jit: 0.08 });
    click(k, o, tt, f * 2, vol * 0.6, 0.008, 2);
  }
}

/** Creature vocalisation: a rough, detuned, driven formant voice. */
export function roar(k, o, t, p) {
  return k.vox(o, Object.assign({ t, type: 'sawtooth', unison: 2, spread: 28, tilt: 2600, jitter: { rate: 28, depth: 0.05 }, direct: 0.35, directF: 500 }, p));
}

/** Registers a recipe: { name, cat, prio, rev ('room'|'hall'|null), send, gain, fn }. */
export function define(table, name, cat, prio, rev, send, gain, fn) {
  table[name] = { name, cat, prio, rev, send, gain, fn };
}
