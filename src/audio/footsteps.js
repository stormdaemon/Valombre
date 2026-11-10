/**
 * VALOMBRE audio - footsteps per ground surface.
 * Recipe signature: fn(k, o, t, r, x) with x = { run:boolean, heavy:boolean }.
 */
import { WOOD, thump, click, metal, define } from './recipes.js';

/** @type {Record<string, object>} */
export const FOOT = Object.create(null);

function step(name, gain, body) {
  define(FOOT, name, 'foot', 2, 'room', 0.08, gain, (k, o, t, r, x) => {
    const run = !!(x && x.run), heavy = !!(x && x.heavy);
    const m = k.gain((run ? 1.25 : 1) * (heavy ? 1.25 : 1) * r.range(0.85, 1.1));
    m.connect(o);
    const ls = (heavy ? 0.78 : 1) * r.range(0.93, 1.07);     // low-end pitch scale
    const sh = run ? 0.8 : 1;                                // shorter contact when running
    body(k, m, t, r, ls, sh);
    if (heavy) {
      thump(k, m, t, 70, 40, 0.1, 0.2);
      if (r.chance(0.7)) metal(k, m, t + r.range(0.01, 0.04), r.range(2200, 3400), 0.035, 0.06);
    }
    return 0.28;
  });
}

step('grass', 0.55, (k, m, t, r, ls, sh) => {
  thump(k, m, t, 95 * ls, 55, 0.07, 0.25);
  k.nz(m, { t, dur: 0.09 * sh, f: r.range(2400, 3800), q: 0.7, vol: 0.5, a: 0.01, am: { rate: 60, depth: 0.7, noise: true } });
  k.nz(m, { kind: 'pink', t, dur: 0.06, type: 'lowpass', f: 500, vol: 0.5, a: 0.006 });
});

step('dirt', 0.4, (k, m, t, r, ls, sh) => {
  thump(k, m, t, 110 * ls, 55, 0.08, 0.45);
  k.nz(m, { kind: 'pink', t, dur: 0.06 * sh, f: r.range(800, 1200), q: 0.8, vol: 0.9, a: 0.004 });
  k.nz(m, { t: t + 0.01, dur: 0.05, f: r.range(2500, 3500), q: 1, vol: 0.15, am: { rate: 80, depth: 1, noise: true } });
});

step('stone', 0.3, (k, m, t, r, ls, sh) => {
  click(k, m, t, r.range(1700, 2300), 0.7, 0.02 * sh, 1.2);
  k.modal(m, { t, f: r.range(850, 1100), ratios: [1, 1.6, 2.4], gains: [0.2, 0.15, 0.08], decays: [0.03, 0.025, 0.015] });
  thump(k, m, t, 150 * ls, 80, 0.05, 0.4);
  k.nz(m, { t: t + 0.015, dur: 0.04, f: 4000, q: 1, vol: 0.1 });
});

step('sand', 0.6, (k, m, t, r, ls, sh) => {
  k.nz(m, { t, dur: 0.13 * sh, f: r.range(1500, 2600), q: 0.6, vol: 0.5, shape: 'bell', peakAt: 0.3 });
  k.nz(m, { kind: 'pink', t, dur: 0.07, type: 'lowpass', f: 400 * ls, vol: 0.4, a: 0.01 });
});

step('snow', 0.55, (k, m, t, r, ls, sh) => {
  k.nz(m, { t, dur: 0.14 * sh, f: r.range(1000, 1500), q: 1.2, vol: 0.8, a: 0.012, am: { rate: 55, depth: 1, noise: true } });
  k.nz(m, { t: t + 0.02, dur: 0.1 * sh, f: 3200, q: 1.5, vol: 0.2, am: { rate: 90, depth: 1, noise: true } });
  thump(k, m, t, 85 * ls, 50, 0.09, 0.35);
});

step('mud', 0.55, (k, m, t, r, ls, sh) => {
  k.nz(m, { kind: 'pink', t, dur: 0.15 * sh, f: 450, fmid: r.range(1100, 1500), f1: 320, q: 4, vol: 1.6, a: 0.015, peakAt: 0.3 });
  thump(k, m, t, 90 * ls, 50, 0.09, 0.4);
  k.tone(m, { f: 220, f1: r.range(450, 600), glide: 0.05, t: t + 0.09 * sh, dur: 0.07, vol: 0.12, a: 0.01 });
});

step('wood', 0.3, (k, m, t, r, ls, sh) => {
  k.modal(m, { t, f: r.range(125, 160) * ls, ratios: WOOD, gains: [0.6, 0.35, 0.2, 0.08], decays: [0.11, 0.07, 0.04, 0.025], bend: 1.1, jit: 0.05, decay: sh });
  click(k, m, t, 1300, 0.4, 0.018, 1);
  k.nz(m, { kind: 'pink', t, dur: 0.04, type: 'lowpass', f: 900, vol: 0.4 });
  if (r.chance(0.12)) {
    k.vox(m, { t: t + 0.03, dur: 0.14, f: [[0, 95], [1, 130]], jitter: { rate: 40, depth: 0.1 }, formants: [[900, 12, 1], [1700, 12, 0.6]], vol: 0.15 });
  }
});

step('water', 0.5, (k, m, t, r, ls, sh) => {
  k.nz(m, { t, dur: 0.16 * sh, f: 2600, f1: 700, q: 1, vol: 0.7, a: 0.01 });
  k.nz(m, { kind: 'pink', t, dur: 0.1, type: 'lowpass', f: 450 * ls, vol: 0.5 });
  for (let i = 0; i < 2; i++) {
    const f = r.range(300, 700), tt = t + 0.03 + r.range(0, 0.1);
    k.tone(m, { f, f1: f * 2, glide: 0.04, t: tt, dur: 0.06, vol: 0.15, a: 0.005 });
  }
});

step('ash', 0.7, (k, m, t, r, ls, sh) => {
  k.nz(m, { kind: 'pink', t, dur: 0.11 * sh, type: 'lowpass', f: r.range(1000, 1500), vol: 0.6, a: 0.018 });
  k.nz(m, { t: t + 0.01, dur: 0.07, f: 3500, q: 1, vol: 0.1, am: { rate: 100, depth: 1, noise: true } });
  thump(k, m, t, 80 * ls, 50, 0.06, 0.2);
});

export const FOOT_NAMES = Object.keys(FOOT);
