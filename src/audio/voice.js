/**
 * VALOMBRE audio - player vocal efforts (formant synthesis).
 * Recipe signature: fn(k, o, t, r, pitch) with pitch 0.7 (deep) .. 1.5 (high).
 */
import { clamp } from './core.js';
import { V, fset, define } from './recipes.js';

/** @type {Record<string, object>} */
export const VOICE = Object.create(null);
const def = (name, prio, gain, fn) => define(VOICE, name, 'voice', prio, 'room', 0.12, gain, (k, o, t, r, p) => fn(k, o, t, r, clamp(p || 1, 0.5, 2)));

const f0 = (p) => 128 * p;                                             // 90 Hz .. 192 Hz
const fs = (p) => 0.86 + 0.26 * clamp((p - 0.7) / 0.8, 0, 1);          // vocal tract scale

def('attack', 7, 0.42, (k, o, t, r, p) => {
  const f = f0(p) * r.range(0.95, 1.08), s = fs(p), d = r.range(0.17, 0.22);
  k.nz(o, { kind: 'pink', t, dur: 0.05, f: 1800 * s, q: 1, vol: 0.3, a: 0.008 });
  k.vox(o, {
    t: t + 0.015, dur: d, type: 'glottal', f: [[0, f * 1.25], [0.25, f * 1.5], [1, f * 1.05]], jitter: { rate: 30, depth: 0.025 },
    formants: fset(r.pick([V.a, V.a, V.e]), s), breath: 0.15, breathF: 2000, growl: { rate: 60, depth: 0.2 }, drive: 1.5,
    direct: 0.2, directF: 600, amp: [[0, 0], [0.1, 1], [0.5, 0.7], [1, 0]],
  });
  return d + 0.1;
});

def('attack_heavy', 7, 0.5, (k, o, t, r, p) => {
  const f = f0(p) * r.range(0.95, 1.06), s = fs(p), d = r.range(0.38, 0.5);
  k.nz(o, { kind: 'pink', t, dur: 0.07, f: 1600 * s, q: 1, vol: 0.3, a: 0.01 });
  k.vox(o, {
    t: t + 0.02, dur: d, type: 'glottal', f: [[0, f * 1.15], [0.3, f * 1.6], [1, f * 0.95]], jitter: { rate: 30, depth: 0.03 },
    formants: fset(V.a, s), formants1: fset(V.uh, s), breath: 0.2, breathF: 2000, growl: { rate: r.range(40, 50), depth: 0.45 }, drive: 2.5,
    direct: 0.2, directF: 600, amp: [[0, 0], [0.08, 0.8], [0.35, 1], [1, 0]],
  });
  return d + 0.12;
});

def('hurt', 8, 0.42, (k, o, t, r, p) => {
  const f = f0(p) * r.range(0.95, 1.1), s = fs(p), d = r.range(0.22, 0.3);
  k.vox(o, {
    t, dur: d, type: 'glottal', f: [[0, f * 1.55], [0.3, f * 1.4], [1, f * 1.05]], jitter: { rate: 30, depth: 0.03 },
    formants: fset(r.pick([V.uh, V.a, V.o]), s), breath: 0.2, breathF: 1800, growl: { rate: 50, depth: 0.3 }, drive: 1.8,
    direct: 0.2, directF: 600, amp: [[0, 0], [0.08, 1], [0.5, 0.7], [1, 0]],
  });
  return d + 0.06;
});

def('death', 9, 0.48, (k, o, t, r, p) => {
  const f = f0(p) * r.range(0.96, 1.06), s = fs(p), d = r.range(1.0, 1.3);
  k.vox(o, {
    t, dur: d, type: 'glottal', f: [[0, f * 1.5], [0.15, f * 1.6], [1, f * 0.7]], jitter: { rate: 25, depth: 0.04 },
    formants: fset(V.a, s), formants1: fset(V.o, s), breath: 0.3, breathF: 1600, growl: { rate: 40, rate1: 14, depth: 0.45 }, drive: 1.8,
    direct: 0.2, directF: 600, amp: [[0, 0], [0.06, 1], [0.5, 0.6], [1, 0]],
  });
  k.nz(o, { kind: 'pink', t: t + d * 0.6, dur: d * 0.6, f: 1200 * s, q: 1, vol: 0.25, shape: 'bell', peakAt: 0.3 });
  return d + 0.3;
});

def('roll', 5, 1.0, (k, o, t, r, p) => {
  const f = f0(p), s = fs(p);
  k.nz(o, { kind: 'pink', t, dur: 0.17, f: r.range(1300, 1700) * s, q: 1.2, vol: 0.7, shape: 'bell', peakAt: 0.3 });
  k.vox(o, { t: t + 0.01, dur: 0.1, type: 'glottal', f: [[0, f * 1.1], [1, f * 0.95]], formants: fset(V.uh, s), breath: 0.4, breathF: 1500, vol: 0.3, a: 0.02, r: 0.05 });
  return 0.22;
});

def('jump', 5, 0.55, (k, o, t, r, p) => {
  const f = f0(p) * r.range(0.96, 1.08), s = fs(p), d = r.range(0.11, 0.14);
  k.nz(o, { kind: 'pink', t, dur: 0.04, f: 1700 * s, q: 1, vol: 0.25, a: 0.006 });
  k.vox(o, {
    t: t + 0.01, dur: d, type: 'glottal', f: [[0, f * 1.3], [1, f * 1.6]], formants: fset(V.uh, s), breath: 0.2, breathF: 1800,
    direct: 0.2, directF: 600, vol: 0.8, amp: [[0, 0], [0.2, 1], [0.7, 0.8], [1, 0]],
  });
  return d + 0.06;
});

def('drink', 6, 0.22, (k, o, t, r, p) => {
  const f = f0(p), s = fs(p), n = r.int(2, 3);
  let tt = t;
  for (let i = 0; i < n; i++) {
    k.vox(o, {
      t: tt, dur: 0.075, type: 'glottal', f: [[0, f * 0.8], [1, f * 1.05]], formants: [[300 * s, 6, 1], [700 * s, 6, 0.5]],
      formants1: [[450 * s, 6, 1], [900 * s, 6, 0.5]], direct: 0.5, directF: 400, vol: 0.7, a: 0.012, r: 0.03,
    });
    k.tone(o, { f: 180, f1: 110, t: tt, dur: 0.05, vol: 0.2 });
    tt += r.range(0.19, 0.23);
  }
  k.vox(o, {
    t: tt + 0.05, dur: 0.42, type: 'glottal', voiced: 0.35, f: [[0, f], [1, f * 0.85]], formants: fset(V.a, s), breath: 0.5, breathF: 1500,
    amp: [[0, 0], [0.2, 0.6], [1, 0]],
  });
  return tt - t + 0.55;
});

export const VOICE_NAMES = Object.keys(VOICE);
