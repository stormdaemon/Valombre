/**
 * VALOMBRE audio - one-shot sound effect recipes.
 *
 * Each recipe is `fn(k, o, t, r)`: build the sound with Kit `k` into node `o` starting at time
 * `t`, using `r` (Rng) for per-trigger variation, and return its dry duration in seconds.
 * Table entry: { cat, prio (0..10, voice stealing), rev (reverb bus), send, gain (trim), fn }.
 */
import { mtof } from './core.js';
import { BAR, WOOD, V, whoosh, thump, click, ping, metal, bell, scatter, crackle, bones, roar, define } from './recipes.js';

/** @type {Record<string, {name:string,cat:string,prio:number,rev:string|null,send:number,gain:number,fn:Function}>} */
export const SFX = Object.create(null);
const def = (name, cat, prio, rev, send, gain, fn) => define(SFX, name, cat, prio, rev, send, gain, fn);

// ---------------------------------------------------------------------------------------
// UI
// ---------------------------------------------------------------------------------------

def('ui_hover', 'ui', 3, null, 0, 1.6, (k, o, t, r) => {
  const f = r.range(1500, 1750);
  k.tone(o, { f, f1: f * 0.82, t, dur: 0.045, vol: 0.1 });
  click(k, o, t, 4200, 0.08, 0.012, 1.5);
  return 0.08;
});

def('ui_click', 'ui', 8, null, 0, 1.4, (k, o, t, r) => {
  const f = r.range(470, 560);
  click(k, o, t, r.range(2100, 2700), 0.3, 0.018);
  k.tone(o, { type: 'triangle', f, f1: f * 0.6, t, dur: 0.07, vol: 0.3 });
  return 0.1;
});

def('ui_back', 'ui', 8, null, 0, 1.4, (k, o, t, r) => {
  const f = r.range(330, 380);
  click(k, o, t, r.range(1500, 1900), 0.25, 0.02);
  k.tone(o, { type: 'triangle', f, f1: f * 0.55, t, dur: 0.11, vol: 0.3 });
  return 0.14;
});

def('ui_open', 'ui', 8, 'room', 0.25, 1.9, (k, o, t, r) => {
  const up = r.pick([0, 0, 2]);
  whoosh(k, o, t, 0.22, 500, 1800, 2600, 1.5, 0.35);
  ping(k, o, t + 0.03, mtof(74 + up), 0.1, 0.5);
  ping(k, o, t + 0.11, mtof(81 + up), 0.1, 0.6);
  return 0.8;
});

def('ui_close', 'ui', 8, 'room', 0.25, 1.75, (k, o, t, r) => {
  const up = r.pick([0, 0, 2]);
  whoosh(k, o, t, 0.2, 2600, 1500, 450, 1.5, 0.35);
  ping(k, o, t + 0.02, mtof(81 + up), 0.09, 0.4);
  ping(k, o, t + 0.1, mtof(74 + up), 0.09, 0.5);
  return 0.7;
});

def('ui_error', 'ui', 8, null, 0, 1.5, (k, o, t, r) => {
  const f = r.range(150, 165), lp = k.bq('lowpass', 900, 0.7);
  lp.connect(o);
  for (let i = 0; i < 2; i++) {
    const tt = t + i * 0.12;
    k.tone(lp, { type: 'square', f, f1: f * 0.94, t: tt, dur: 0.1, vol: 0.16 });
    k.tone(lp, { type: 'triangle', f: f * 1.06, t: tt, dur: 0.1, vol: 0.25 });
    click(k, o, tt, 900, 0.12, 0.02);
  }
  return 0.3;
});

def('ui_equip', 'ui', 8, 'room', 0.15, 1.6, (k, o, t, r) => {
  k.nz(o, { kind: 'pink', t, dur: 0.11, f: r.range(900, 1400), q: 0.8, vol: 0.6, a: 0.01 });
  metal(k, o, t + 0.06, r.range(1900, 2400), 0.1, 0.09);
  thump(k, o, t + 0.05, 160, 90, 0.07, 0.25);
  return 0.25;
});

def('ui_slider', 'ui', 3, null, 0, 1.5, (k, o, t, r) => {
  k.tone(o, { f: r.range(1150, 1250), t, dur: 0.022, vol: 0.12 });
  return 0.04;
});

def('ui_save', 'ui', 8, 'room', 0.3, 1.6, (k, o, t, r) => {
  k.nz(o, { t, dur: 0.22, f: r.range(2900, 3500), q: 2, vol: 0.3, shape: 'flat', a: 0.01, r: 0.05, am: { rate: 38, depth: 0.9, noise: true } });
  ping(k, o, t + 0.2, mtof(81), 0.12, 0.7);
  ping(k, o, t + 0.2, mtof(88), 0.06, 0.5);
  return 1.0;
});

def('ui_quest', 'ui', 9, 'hall', 0.3, 1.2, (k, o, t, r) => {
  k.nz(o, { kind: 'pink', t, dur: 0.25, f: 1800, f1: 3000, q: 0.9, vol: 0.35, shape: 'bell', am: { rate: 60, depth: 0.7, noise: true } });
  const n = [62, 69, 74];
  for (let i = 0; i < 3; i++) k.pluck(o, { t: t + 0.12 + i * r.range(0.12, 0.14), midi: n[i], vol: 0.35, type: 'harp', dur: 1.2 });
  return 1.9;
});

def('ui_quest_done', 'ui', 9, 'hall', 0.35, 1.2, (k, o, t, r) => {
  const n = [62, 66, 69, 74];
  for (let i = 0; i < 4; i++) k.pluck(o, { t: t + i * r.range(0.085, 0.095), midi: n[i], vol: 0.33, type: 'harp', dur: 1.4 });
  ping(k, o, t + 0.36, mtof(86), 0.1, 1.0);
  ping(k, o, t + 0.36, mtof(81), 0.07, 0.9);
  return 2.0;
});

def('ui_discover', 'ui', 9, 'hall', 0.45, 1.5, (k, o, t, r) => {
  for (const [m, v] of [[50, 0.12], [57, 0.1], [62, 0.08]]) k.tone(o, { type: 'triangle', f: mtof(m), t, dur: 1.8, vol: v, shape: 'swell', peakAt: 0.35 });
  const notes = [74, 81, 86, 93];
  for (let i = 0; i < 4; i++) ping(k, o, t + 0.25 + i * r.range(0.12, 0.16), mtof(notes[i]), 0.06, 0.8);
  k.nz(o, { kind: 'pink', t, dur: 1.2, f: 2500, fmid: 5000, f1: 3000, q: 2, vol: 0.08, shape: 'bell', peakAt: 0.4 });
  return 2.2;
});

def('ui_levelup', 'ui', 9, 'hall', 0.4, 0.88, (k, o, t, r) => {
  thump(k, o, t, 120, 50, 0.35, 0.45);
  const n = [62, 69, 74, 78, 81];
  for (let i = 0; i < 5; i++) {
    k.pluck(o, { t: t + i * 0.08, midi: n[i], vol: 0.3, type: 'harp', dur: 1.6 });
    ping(k, o, t + i * 0.08, mtof(n[i] + 12), 0.035, 0.6);
  }
  for (const [m, v] of [[62, 0.08], [66, 0.06], [69, 0.06], [74, 0.05]]) k.tone(o, { type: 'triangle', f: mtof(m), t: t + 0.1, dur: 1.7, vol: v, shape: 'swell', peakAt: 0.3 });
  ping(k, o, t + 0.45, mtof(93), 0.08, 1.2);
  return 2.4;
});

def('ui_buy', 'ui', 8, 'room', 0.15, 1.6, (k, o, t, r) => {
  const n = r.int(3, 4);
  let tt = t + 0.02;
  for (let i = 0; i < n; i++) {
    k.modal(o, { t: tt, f: r.range(4200, 6200), ratios: [1, 1.48, 2.13], gains: [1, 0.6, 0.35], decays: [0.12, 0.09, 0.05], vol: 0.12 });
    tt += r.range(0.035, 0.06);
  }
  thump(k, o, t, 180, 110, 0.06, 0.25);
  k.nz(o, { kind: 'pink', t, dur: 0.08, f: 900, q: 0.8, vol: 0.4 });
  return 0.5;
});

// ---------------------------------------------------------------------------------------
// Player / combat
// ---------------------------------------------------------------------------------------

def('swing_light', 'combat', 5, 'room', 0.12, 2.0, (k, o, t, r) => {
  const d = r.range(0.15, 0.19), s = r.range(0.9, 1.15);
  whoosh(k, o, t, d, 600 * s, 2600 * s, 900 * s, 2.2, 0.9);
  whoosh(k, o, t + 0.01, d * 0.9, 1800 * s, 5200 * s, 2500, 3, 0.3, 'white');
  return d + 0.05;
});

def('swing_heavy', 'combat', 5, 'room', 0.15, 1.4, (k, o, t, r) => {
  const d = r.range(0.28, 0.34), s = r.range(0.9, 1.12);
  whoosh(k, o, t, d, 300 * s, 1500 * s, 450 * s, 1.8, 1);
  whoosh(k, o, t + 0.02, d * 0.9, 900 * s, 3200 * s, 1200, 2.5, 0.3, 'white');
  thump(k, o, t + d * 0.3, 95, 55, 0.2, 0.25);
  return d + 0.08;
});

def('swing_2h', 'combat', 5, 'room', 0.18, 1.27, (k, o, t, r) => {
  const d = r.range(0.4, 0.48), s = r.range(0.9, 1.1);
  whoosh(k, o, t, d, 220 * s, 1100 * s, 300 * s, 1.6, 1.1);
  whoosh(k, o, t + 0.03, d * 0.9, 700 * s, 2600 * s, 900, 2.2, 0.35, 'white');
  thump(k, o, t + d * 0.35, 80, 45, 0.25, 0.35);
  k.tone(o, { type: 'triangle', f: 320 * s, f1: 180 * s, t, dur: d, vol: 0.04, shape: 'swell', peakAt: 0.45 });
  return d + 0.1;
});

def('hit_flesh', 'combat', 6, 'room', 0.15, 0.85, (k, o, t, r) => {
  const s = r.range(0.9, 1.12);
  thump(k, o, t, 150 * s, 55, 0.11, 0.9);
  k.nz(o, { kind: 'pink', t, dur: 0.07, type: 'lowpass', f: 1100, q: 0.7, vol: 0.9 });
  k.nz(o, { t: t + 0.008, dur: 0.11, f: 1900 * s, f1: 480, q: 3.5, vol: 0.6, a: 0.006 });
  k.nz(o, { t: t + 0.03, dur: 0.09, f: 3200, f1: 1200, q: 4, vol: 0.25, a: 0.01 });
  return 0.2;
});

def('hit_armor', 'combat', 6, 'room', 0.22, 0.61, (k, o, t, r) => {
  const f = r.range(430, 620);
  click(k, o, t, 5200, 0.7, 0.012, 0.8);
  metal(k, o, t, f, 0.3, r.range(0.22, 0.34), 0.05);
  k.modal(o, { t, f: f * 6.3, ratios: [1, 1.34, 1.71], gains: [0.12, 0.1, 0.07], decays: [0.09, 0.07, 0.05] });
  thump(k, o, t, 130, 70, 0.09, 0.6);
  k.nz(o, { t, dur: 0.05, f: 2400, q: 0.7, vol: 0.4 });
  return 0.45;
});

def('hit_bone', 'combat', 6, 'room', 0.15, 0.56, (k, o, t, r) => {
  const f = r.range(700, 950);
  click(k, o, t, r.range(2200, 3000), 0.8, 0.02, 1.5);
  k.modal(o, { t, f, ratios: WOOD, gains: [0.5, 0.4, 0.25, 0.15], decays: [0.05, 0.04, 0.03, 0.02], jit: 0.06 });
  click(k, o, t + r.range(0.025, 0.045), r.range(1500, 2400), 0.45, 0.018, 2);
  k.modal(o, { t: t + 0.035, f: f * 1.37, ratios: [1, 1.9], gains: [0.25, 0.15], decays: [0.04, 0.03] });
  thump(k, o, t, 170, 90, 0.05, 0.35);
  return 0.16;
});

def('hit_wood', 'combat', 6, 'room', 0.15, 0.6, (k, o, t, r) => {
  const f = r.range(190, 250);
  k.modal(o, { t, f, ratios: WOOD, gains: [0.8, 0.5, 0.3, 0.15], decays: [0.13, 0.09, 0.05, 0.03], jit: 0.05, bend: 1.15 });
  k.nz(o, { t, dur: 0.035, type: 'lowpass', f: 2600, vol: 0.7 });
  click(k, o, t, 1300, 0.4, 0.02, 1);
  click(k, o, t + r.range(0.02, 0.05), r.range(2500, 3500), 0.15, 0.01, 2);
  return 0.22;
});

def('hit_stone', 'combat', 6, 'room', 0.18, 0.47, (k, o, t, r) => {
  const f = r.range(950, 1300);
  click(k, o, t, 3800, 0.9, 0.012, 0.7);
  k.modal(o, { t, f, ratios: [1, 1.58, 2.37, 3.55], gains: [0.4, 0.35, 0.25, 0.15], decays: [0.035, 0.03, 0.022, 0.015], jit: 0.08 });
  thump(k, o, t, 120, 60, 0.08, 0.6);
  k.nz(o, { kind: 'pink', t, dur: 0.06, type: 'lowpass', f: 700, vol: 0.5 });
  scatter(k, o, t + 0.03, r.int(4, 6), 0.16, 1800, 5000, 0.2, 0.008);
  return 0.26;
});

def('hit_chitin', 'combat', 6, 'room', 0.15, 1.25, (k, o, t, r) => {
  const s = r.range(0.9, 1.15);
  k.nz(o, { t, dur: 0.09, f: 2600 * s, q: 1.5, vol: 0.7, am: { rate: 90, depth: 1, noise: true } });
  k.nz(o, { kind: 'pink', t, dur: 0.1, f: 620 * s, f1: 430 * s, q: 9, vol: 1.6 });
  click(k, o, t, 4200, 0.6, 0.01, 1);
  k.nz(o, { t: t + 0.02, dur: 0.1, f: 1500, f1: 500, q: 4, vol: 0.35, a: 0.01 });
  thump(k, o, t, 180, 80, 0.07, 0.5);
  return 0.2;
});

def('crit', 'combat', 8, 'hall', 0.3, 0.6, (k, o, t, r) => {
  k.nz(o, { kind: 'pink', t, dur: 0.07, f: 1500, f1: 6000, q: 1, vol: 0.3, shape: 'bell', peakAt: 0.95 });
  const t1 = t + 0.07;
  click(k, o, t1, 5000, 1, 0.015, 0.6);
  k.tone(o, { f: 190, f1: 42, glide: 0.22, t: t1, dur: 0.35, vol: 1 });
  k.nz(o, { kind: 'pink', t: t1, dur: 0.18, type: 'lowpass', f: 3500, f1: 400, vol: 0.8 });
  metal(k, o, t1, r.range(2300, 2900), 0.1, 0.6, 0.04);
  return 0.75;
});

def('block_shield', 'combat', 6, 'room', 0.18, 0.55, (k, o, t, r) => {
  const f = r.range(140, 175);
  k.modal(o, { t, f, ratios: WOOD, gains: [1, 0.6, 0.35, 0.2], decays: [0.16, 0.1, 0.06, 0.04], jit: 0.05, bend: 1.2 });
  metal(k, o, t, r.range(800, 1000), 0.14, 0.12);
  k.nz(o, { kind: 'pink', t, dur: 0.06, type: 'lowpass', f: 1800, vol: 0.9 });
  click(k, o, t, 2800, 0.5, 0.012, 0.8);
  return 0.3;
});

def('parry', 'combat', 8, 'room', 0.25, 0.65, (k, o, t, r) => {
  const f = r.range(1750, 2150);
  click(k, o, t, 7000, 0.8, 0.008, 0.7);
  k.modal(o, { t, f, ratios: [1, 1.47, 2.09, 2.83, 3.71, 4.9], gains: [0.3, 0.28, 0.22, 0.18, 0.12, 0.08], decays: [0.55, 0.5, 0.4, 0.3, 0.22, 0.15], jit: 0.03 });
  k.nz(o, { t: t + 0.005, dur: 0.16, f: 5000, f1: 9500, q: 4, vol: 0.3, a: 0.01 });
  thump(k, o, t, 220, 120, 0.04, 0.3);
  return 0.7;
});

def('roll', 'combat', 4, 'room', 0.1, 1.2, (k, o, t, r) => {
  for (let i = 0; i < 3; i++) {
    const tt = t + i * r.range(0.1, 0.13);
    k.nz(o, { kind: 'pink', t: tt, dur: 0.09, type: 'lowpass', f: r.range(500, 800), vol: 0.7 * (1 - i * 0.2), a: 0.008 });
    thump(k, o, tt, 110, 60, 0.07, 0.25);
  }
  k.nz(o, { kind: 'pink', t, dur: 0.38, f: 2200, q: 0.8, vol: 0.3, shape: 'bell', peakAt: 0.4, am: { rate: 28, depth: 0.8, noise: true } });
  return 0.45;
});

def('jump', 'combat', 4, 'room', 0.08, 1.4, (k, o, t, r) => {
  const s = r.range(0.9, 1.1);
  whoosh(k, o, t, 0.14, 350 * s, 1100 * s, 1400, 1.5, 0.5);
  k.nz(o, { kind: 'pink', t, dur: 0.1, f: 2400, q: 0.8, vol: 0.2, am: { rate: 30, depth: 0.8, noise: true } });
  thump(k, o, t, 120, 80, 0.05, 0.25);
  return 0.18;
});

def('land', 'combat', 5, 'room', 0.12, 0.9, (k, o, t, r) => {
  thump(k, o, t, r.range(105, 125), 50, 0.14, 0.8);
  k.nz(o, { kind: 'pink', t, dur: 0.08, type: 'lowpass', f: 650, vol: 0.9 });
  k.nz(o, { kind: 'pink', t: t + 0.01, dur: 0.12, f: 2000, q: 0.8, vol: 0.15 });
  metal(k, o, t + 0.02, r.range(2500, 3300), 0.03, 0.07);
  return 0.22;
});

def('body_fall', 'combat', 6, 'room', 0.15, 0.6, (k, o, t, r) => {
  thump(k, o, t, 95, 48, 0.14, 0.6);
  k.nz(o, { kind: 'pink', t, dur: 0.09, type: 'lowpass', f: 600, vol: 0.7 });
  const t2 = t + r.range(0.16, 0.22);
  thump(k, o, t2, 75, 36, 0.22, 1);
  k.nz(o, { kind: 'pink', t: t2, dur: 0.14, type: 'lowpass', f: 800, vol: 1 });
  k.nz(o, { kind: 'pink', t: t2, dur: 0.25, f: 1800, q: 0.7, vol: 0.2, am: { rate: 25, depth: 0.8, noise: true } });
  metal(k, o, t2 + 0.02, r.range(1500, 2200), 0.06, 0.12);
  metal(k, o, t2 + 0.09, r.range(2200, 3000), 0.04, 0.08);
  return 0.6;
});

def('potion', 'combat', 6, 'room', 0.12, 1.1, (k, o, t, r) => {
  k.tone(o, { f: r.range(850, 1000), f1: 280, glide: 0.03, t, dur: 0.06, vol: 0.5 });
  click(k, o, t, 2500, 0.3, 0.008);
  for (let i = 0; i < 3; i++) {
    const tt = t + 0.12 + i * r.range(0.11, 0.14), f = r.range(260, 340) * (1 + i * 0.12);
    k.tone(o, { f, f1: f * 2.1, glide: 0.07, t: tt, dur: 0.09, vol: 0.4, a: 0.01 });
    k.nz(o, { kind: 'pink', t: tt, dur: 0.07, f: 700, q: 2, vol: 0.3, a: 0.01 });
  }
  ping(k, o, t + 0.5, r.range(2800, 3400), 0.05, 0.25);
  return 0.8;
});

def('heal', 'combat', 7, 'hall', 0.45, 1.3, (k, o, t, r) => {
  const base = r.pick([60, 62]), arp = [0, 4, 7, 12, 16, 19];
  for (const [m, v] of [[0, 0.12], [4, 0.09], [7, 0.09], [12, 0.07]]) k.tone(o, { type: 'triangle', f: mtof(base + 12 + m), t, dur: 1.5, vol: v, shape: 'swell', peakAt: 0.3 });
  k.tone(o, { f: 400, f1: 1600, t, dur: 0.7, vol: 0.06, shape: 'swell', peakAt: 0.8 });
  for (let i = 0; i < 6; i++) ping(k, o, t + 0.1 + i * 0.11 + r.range(0, 0.03), mtof(base + 24 + arp[i]), 0.05, 0.5);
  k.nz(o, { kind: 'pink', t, dur: 1.2, f: 3000, fmid: 6000, f1: 4000, q: 2, vol: 0.1, shape: 'bell', peakAt: 0.4 });
  return 1.7;
});

def('stamina_empty', 'combat', 5, null, 0, 1.2, (k, o, t, r) => {
  const s = r.range(0.93, 1.07);
  k.nz(o, { kind: 'pink', t, dur: 0.22, f: 750 * s, q: 1.2, vol: 0.8, shape: 'bell', peakAt: 0.25 });
  k.tone(o, { type: 'triangle', f: 130 * s, f1: 85, t, dur: 0.16, vol: 0.4 });
  k.tone(o, { type: 'triangle', f: 110 * s, f1: 70, t: t + 0.13, dur: 0.16, vol: 0.3 });
  return 0.35;
});

def('spell_cast', 'combat', 7, 'hall', 0.35, 1.1, (k, o, t, r) => {
  const s = r.range(0.92, 1.1);
  k.fm(o, { t, dur: 0.45, f: 220 * s, f1: 880 * s, ratio: 1.5, idx: 0.5, idx1: 4, vol: 0.3, shape: 'swell', peakAt: 0.85 });
  whoosh(k, o, t, 0.45, 500, 2500, 5000, 2, 0.7, 'pink', 0.85);
  for (let i = 0; i < 4; i++) ping(k, o, t + 0.4 + i * 0.03, r.range(2500, 5000), 0.06, 0.3);
  thump(k, o, t + 0.42, 160, 70, 0.12, 0.4);
  return 0.85;
});

def('spell_fire', 'combat', 7, 'room', 0.25, 1.0, (k, o, t, r) => {
  const s = r.range(0.9, 1.1);
  k.nz(o, { kind: 'pink', t, dur: 0.7, type: 'lowpass', f: 300, fmid: 3200 * s, f1: 500, peakAt: 0.25, q: 1.2, vol: 1, shape: 'bell', am: { rate: 45, depth: 0.5, noise: true } });
  k.nz(o, { kind: 'brown', t, dur: 0.6, type: 'lowpass', f: 250, vol: 0.9, shape: 'bell', peakAt: 0.2 });
  thump(k, o, t + 0.02, 95 * s, 45, 0.25, 0.7);
  crackle(k, o, t + 0.05, 0.6, 0.4, 1500);
  return 0.8;
});

def('spell_ice', 'combat', 7, 'hall', 0.35, 1.2, (k, o, t, r) => {
  k.nz(o, { t, dur: 0.5, type: 'highpass', f: 9000, f1: 3000, q: 1, vol: 0.25, shape: 'bell', peakAt: 0.15 });
  k.tone(o, { f: 2400, f1: 700, t, dur: 0.4, vol: 0.12, shape: 'swell', peakAt: 0.1 });
  for (let i = 0; i < 9; i++) {
    k.modal(o, { t: t + r.range(0, 0.3), f: r.range(2800, 8000), ratios: [1, 1.41, 2.3], gains: [0.1, 0.07, 0.04], decays: [0.18, 0.12, 0.07], decay: r.range(0.5, 1.5) });
  }
  crackle(k, o, t, 0.35, 0.3, 4000);
  thump(k, o, t, 200, 90, 0.08, 0.3);
  return 0.7;
});

def('spell_dark', 'combat', 7, 'hall', 0.4, 0.61, (k, o, t, r) => {
  const s = r.range(0.92, 1.08), lp = k.bq('lowpass', 120, 3);
  lp.frequency.setValueAtTime(120, t);
  lp.frequency.exponentialRampToValueAtTime(1400, t + 0.6);
  lp.frequency.exponentialRampToValueAtTime(200, t + 0.95);
  lp.connect(o);
  k.tone(lp, { type: 'sawtooth', f: 55 * s, f1: 49 * s, t, dur: 0.95, vol: 0.5, shape: 'swell', peakAt: 0.65 });
  k.tone(lp, { type: 'sawtooth', f: 77.8 * s, f1: 69 * s, t, dur: 0.95, vol: 0.35, shape: 'swell', peakAt: 0.65 });
  k.fm(o, { t, dur: 0.9, f: 110 * s, f1: 82 * s, ratio: 2.71, idx: 3, idx1: 0.5, vol: 0.15, shape: 'swell', peakAt: 0.6 });
  k.nz(o, { kind: 'pink', t, dur: 0.9, f: 3000, f1: 500, q: 4, vol: 0.5, shape: 'bell', peakAt: 0.6, am: { rate: 14, depth: 0.7, noise: true } });
  thump(k, o, t + 0.6, 90, 35, 0.3, 0.6);
  return 1.05;
});

def('spell_impact', 'combat', 7, 'hall', 0.35, 0.57, (k, o, t, r) => {
  const s = r.range(0.9, 1.1);
  k.tone(o, { f: 130 * s, f1: 34, glide: 0.3, t, dur: 0.5, vol: 1 });
  k.nz(o, { kind: 'pink', t, dur: 0.5, type: 'lowpass', f: 7000, f1: 300, vol: 1 });
  click(k, o, t, 4500, 0.8, 0.012, 0.6);
  for (let i = 0; i < 5; i++) ping(k, o, t + 0.03 + r.range(0, 0.25), r.range(1800, 5200), 0.06, 0.35);
  k.fm(o, { t, dur: 0.35, f: 600 * s, f1: 150, ratio: 1.41, idx: 3, idx1: 0, vol: 0.2 });
  return 0.7;
});

def('shard_burst', 'combat', 7, 'hall', 0.4, 0.72, (k, o, t, r) => {
  click(k, o, t, 6000, 0.9, 0.01, 0.6);
  k.nz(o, { t, dur: 0.25, type: 'highpass', f: 4500, vol: 0.4 });
  k.modal(o, { t, f: r.range(650, 820), ratios: BAR, gains: [0.2, 0.14, 0.1, 0.05], decays: [0.9, 0.6, 0.35, 0.2] });
  for (let i = 0; i < 12; i++) {
    k.modal(o, { t: t + Math.pow(r.next(), 1.6) * 0.35, f: r.range(2200, 9000), ratios: [1, 1.52], gains: [0.09, 0.05], decays: [r.range(0.05, 0.3), 0.05] });
  }
  thump(k, o, t, 160, 60, 0.12, 0.5);
  return 1.1;
});

def('arrow_shoot', 'combat', 5, 'room', 0.1, 1.2, (k, o, t, r) => {
  const f = r.range(160, 200);
  k.tone(o, { type: 'triangle', f: f * 1.25, f1: f, glide: 0.04, t, dur: 0.18, vol: 0.5 });
  k.tone(o, { type: 'sawtooth', f: f * 2.02, f1: f * 2, t, dur: 0.07, vol: 0.08 });
  click(k, o, t, 3000, 0.4, 0.008, 1);
  whoosh(k, o, t + 0.015, 0.14, 1800, 4800, 3000, 3, 0.6, 'white', 0.3);
  return 0.25;
});

def('arrow_hit', 'combat', 5, 'room', 0.12, 0.65, (k, o, t, r) => {
  const f = r.range(260, 340);
  k.modal(o, { t, f, ratios: WOOD, gains: [0.7, 0.4, 0.25, 0.1], decays: [0.08, 0.05, 0.035, 0.02], bend: 1.2 });
  click(k, o, t, 2200, 0.7, 0.012, 1);
  k.nz(o, { kind: 'pink', t, dur: 0.04, type: 'lowpass', f: 1500, vol: 0.6 });
  k.fm(o, { t: t + 0.01, dur: 0.28, f: r.range(380, 460), ratio: 0.13, idx: 0.3, vol: 0.15 });
  return 0.35;
});

// ---------------------------------------------------------------------------------------
// Creatures
// ---------------------------------------------------------------------------------------

def('wolf_growl', 'creature', 5, 'room', 0.12, 0.185, (k, o, t, r) => {
  const d = r.range(0.9, 1.4), f = r.range(82, 105);
  roar(k, o, t, {
    dur: d, f: [[0, f], [0.4, f * 1.12], [1, f * 0.92]], formants: [[380, 3, 1], [950, 4, 0.7], [2300, 5, 0.3]],
    growl: { rate: r.range(27, 36), depth: 0.85 }, breath: 0.25, drive: 2.5, amp: [[0, 0], [0.25, 0.8], [0.6, 1], [1, 0]],
  });
  return d + 0.1;
});

def('wolf_bark', 'creature', 6, 'room', 0.18, 0.34, (k, o, t, r) => {
  const n = r.chance(0.4) ? 2 : 1, f = r.range(190, 240);
  for (let i = 0; i < n; i++) {
    const tt = t + i * r.range(0.2, 0.26), d = r.range(0.13, 0.17);
    roar(k, o, tt, {
      dur: d, f: [[0, f * 1.25], [0.25, f * 1.4], [1, f * 0.75]],
      formants: [[650, 4, 1], [1450, 5, 0.8], [2700, 6, 0.35]], formants1: [[450, 4, 1], [1000, 5, 0.8], [2300, 6, 0.35]],
      growl: { rate: 55, depth: 0.5 }, breath: 0.35, drive: 4, curve: 'hard', amp: [[0, 0], [0.12, 1], [0.5, 0.6], [1, 0]],
    });
    k.nz(o, { kind: 'pink', t: tt, dur: 0.05, f: 1200, q: 1, vol: 0.5 });
  }
  return n * 0.25 + 0.05;
});

def('wolf_howl', 'creature', 6, 'hall', 0.5, 0.125, (k, o, t, r) => {
  const d = r.range(2.4, 3.2), f = r.range(390, 470);
  const path = [[0, f * 0.62], [0.18, f * 0.98], [0.3, f], [0.75, f * 1.02], [1, f * 0.72]];
  k.vox(o, {
    t, dur: d, type: 'triangle', unison: 2, spread: 10, f: path, vib: { rate: 5, depth: 0.012, delay: 0.7 }, jitter: { rate: 8, depth: 0.01 },
    formants: [[520, 4, 1], [1050, 5, 0.6], [2300, 6, 0.15]], direct: 0.4, directF: 1200, breath: 0.03,
    amp: [[0, 0], [0.12, 0.5], [0.3, 1], [0.75, 0.85], [1, 0]],
  });
  k.vox(o, {
    t, dur: d, type: 'sawtooth', f: path, tilt: 1500, jitter: { rate: 20, depth: 0.02 },
    formants: [[520, 5, 1], [1100, 6, 0.5]], vol: 0.5, amp: [[0, 0], [0.3, 0.6], [0.8, 0.4], [1, 0]],
  });
  return d + 0.1;
});

def('wolf_hurt', 'creature', 6, 'room', 0.15, 0.185, (k, o, t, r) => {
  const f = r.range(480, 560), d = r.range(0.22, 0.3), n = r.chance(0.45) ? 2 : 1;
  for (let i = 0; i < n; i++) {
    const tt = t + i * (d + 0.04), dd = i ? d * 0.6 : d, ff = i ? f * 1.15 : f;
    k.vox(o, {
      t: tt, dur: dd, type: 'sawtooth', tilt: 3000, f: [[0, ff], [0.2, ff * 1.7], [1, ff * 0.8]], jitter: { rate: 30, depth: 0.03 },
      formants: [[850, 4, 1], [1900, 5, 0.8], [3100, 6, 0.4]], breath: 0.15, drive: 2, vol: i ? 0.6 : 1, amp: [[0, 0], [0.1, 1], [0.5, 0.7], [1, 0]],
    });
  }
  return n * (d + 0.04) + 0.05;
});

def('wolf_death', 'creature', 7, 'room', 0.2, 0.32, (k, o, t, r) => {
  const d = r.range(1.0, 1.3), f = r.range(380, 440);
  k.vox(o, {
    t, dur: d, type: 'sawtooth', tilt: 2500, f: [[0, f], [0.15, f * 1.3], [0.6, f * 0.7], [1, f * 0.4]], jitter: { rate: 25, depth: 0.04 },
    formants: [[800, 4, 1], [1700, 5, 0.7], [2900, 6, 0.3]], formants1: [[450, 4, 1], [1000, 5, 0.7], [2300, 6, 0.3]],
    breath: 0.3, growl: { rate: 30, rate1: 16, depth: 0.5 }, drive: 2, amp: [[0, 0], [0.08, 1], [0.5, 0.6], [1, 0]],
  });
  k.nz(o, { kind: 'pink', t: t + d * 0.6, dur: d * 0.6, f: 900, q: 1, vol: 0.3, shape: 'bell', peakAt: 0.3 });
  return d + 0.35;
});

def('spider_hiss', 'creature', 5, 'room', 0.12, 1.2, (k, o, t, r) => {
  const d = r.range(0.5, 0.75);
  k.nz(o, { t, dur: d, f: r.range(5000, 6500), q: 1.2, vol: 0.6, shape: 'bell', peakAt: 0.3, am: { rate: r.range(38, 55), depth: 0.7, type: 'sawtooth' } });
  k.nz(o, { t, dur: d, type: 'highpass', f: 7500, vol: 0.2, shape: 'bell', peakAt: 0.3 });
  k.nz(o, { kind: 'pink', t, dur: d * 0.8, f: 1800, q: 3, vol: 0.4, shape: 'bell', peakAt: 0.2, am: { rate: 60, depth: 0.9, noise: true } });
  return d + 0.05;
});

def('spider_skitter', 'creature', 4, 'room', 0.1, 1.4, (k, o, t, r) => {
  const n = r.int(8, 13);
  let tt = t;
  for (let i = 0; i < n; i++) {
    click(k, o, tt, r.range(2800, 5200), r.range(0.4, 0.8), 0.006, 2.5);
    if (i % 2 === 0) k.tone(o, { type: 'triangle', f: r.range(1500, 2300), t: tt, dur: 0.012, vol: 0.15 });
    tt += r.range(0.018, 0.045);
  }
  return tt - t + 0.05;
});

function screechBus(k, o, t, d, rate0, rate1) {
  const am = k.gain(0.5), lfo = k.osc('sawtooth', rate0, t, t + d + 0.1), lg = k.gain(0.5);
  if (rate1) { lfo.frequency.setValueAtTime(rate0, t); lfo.frequency.linearRampToValueAtTime(rate1, t + d); }
  lfo.connect(lg); lg.connect(am.gain); am.connect(o);
  return am;
}

def('spider_screech', 'creature', 6, 'room', 0.2, 1.3, (k, o, t, r) => {
  const d = r.range(0.6, 0.85), f = r.range(1700, 2100), am = screechBus(k, o, t, d, r.range(55, 80));
  k.fm(am, { t, dur: d, f, f1: f * 0.8, ratio: 1.37, idx: 2.5, idx1: 4, vol: 0.3, shape: 'swell', peakAt: 0.25, type: 'sawtooth' });
  k.fm(am, { t, dur: d, f: f * 1.51, f1: f * 1.1, ratio: 2.3, idx: 2, vol: 0.15, shape: 'swell', peakAt: 0.25 });
  k.nz(am, { t, dur: d, f: 4500, f1: 3000, q: 2, vol: 0.6, shape: 'bell', peakAt: 0.25 });
  return d + 0.05;
});

def('spider_spit', 'creature', 5, 'room', 0.12, 1.3, (k, o, t, r) => {
  const s = r.range(0.9, 1.15);
  k.nz(o, { t, dur: 0.13, f: 3200 * s, f1: 900, q: 2.5, vol: 0.9 });
  k.nz(o, { kind: 'pink', t, dur: 0.06, type: 'lowpass', f: 900, vol: 0.5 });
  k.tone(o, { f: 500 * s, f1: 1100, glide: 0.05, t: t + 0.02, dur: 0.07, vol: 0.25 });
  whoosh(k, o, t + 0.05, 0.25, 1500, 2600, 1200, 4, 0.5, 'pink', 0.2);
  return 0.35;
});

def('spider_death', 'creature', 7, 'room', 0.2, 1.3, (k, o, t, r) => {
  const d = r.range(0.8, 1.0), f = r.range(2000, 2400), am = screechBus(k, o, t, d, 70, 18);
  k.fm(am, { t, dur: d, f, f1: f * 0.25, ratio: 1.37, idx: 3, idx1: 1, vol: 0.3, type: 'sawtooth', shape: 'swell', peakAt: 0.1 });
  k.nz(am, { t, dur: d, f: 4500, f1: 1200, q: 2, vol: 0.6, shape: 'bell', peakAt: 0.1 });
  k.nz(o, { t: t + d * 0.6, dur: 0.12, f: 2400, q: 1.5, vol: 0.5, am: { rate: 90, depth: 1, noise: true } });
  thump(k, o, t + d * 0.65, 140, 60, 0.12, 0.5);
  let tt = t + d * 0.7;
  for (let i = 0; i < 6; i++) { click(k, o, tt, r.range(2800, 4800), 0.5 * (1 - i / 7), 0.006, 2.5); tt += 0.04 + i * 0.018; }
  return d + 0.5;
});

def('undead_moan', 'creature', 5, 'hall', 0.3, 0.24, (k, o, t, r) => {
  const d = r.range(1.4, 2.0), f = r.range(78, 100);
  roar(k, o, t, {
    dur: d, spread: 20, f: [[0, f], [0.3, f * 1.1], [1, f * 0.82]], tilt: 1800,
    formants: [[480, 5, 1], [820, 6, 0.7], [2400, 8, 0.2]], formants1: [[330, 5, 1], [700, 6, 0.6], [2300, 8, 0.15]],
    growl: { rate: r.range(16, 22), depth: 0.6 }, breath: 0.4, breathF: 1200, drive: 1.2, amp: [[0, 0], [0.3, 1], [0.7, 0.8], [1, 0]],
  });
  return d + 0.1;
});

def('undead_hurt', 'creature', 6, 'room', 0.18, 0.37, (k, o, t, r) => {
  const d = r.range(0.28, 0.36), f = r.range(105, 130);
  roar(k, o, t, {
    dur: d, f: [[0, f * 1.2], [1, f * 0.8]], formants: [[620, 4, 1], [1150, 5, 0.7], [2500, 7, 0.3]],
    growl: { rate: 24, depth: 0.7 }, breath: 0.6, breathF: 1500, drive: 2.5, amp: [[0, 0], [0.1, 1], [1, 0]],
  });
  bones(k, o, t + 0.03, 2, 0.08, 0.3);
  return d + 0.12;
});

def('undead_death', 'creature', 7, 'hall', 0.25, 0.32, (k, o, t, r) => {
  const d = r.range(1.2, 1.5), f = r.range(95, 115);
  roar(k, o, t, {
    dur: d, f: [[0, f * 1.2], [0.2, f * 1.3], [1, f * 0.55]],
    formants: [[600, 4, 1], [1000, 5, 0.7], [2400, 7, 0.25]], formants1: [[300, 4, 1], [650, 5, 0.6], [2200, 7, 0.2]],
    growl: { rate: 22, rate1: 9, depth: 0.8 }, breath: 0.5, breathF: 1200, drive: 2, amp: [[0, 0], [0.1, 1], [0.6, 0.6], [1, 0]],
  });
  bones(k, o, t + d * 0.55, 8, 0.5, 0.35);
  thump(k, o, t + d * 0.7, 90, 45, 0.15, 0.4);
  return d + 0.4;
});

def('bones_rattle', 'creature', 4, 'room', 0.15, 1.1, (k, o, t, r) => {
  const span = r.range(0.35, 0.5);
  bones(k, o, t, r.int(6, 10), span, 0.5);
  return span + 0.12;
});

def('troll_roar', 'creature', 8, 'hall', 0.35, 0.225, (k, o, t, r) => {
  const d = r.range(1.6, 2.1), f = r.range(52, 62);
  roar(k, o, t, {
    dur: d, unison: 3, spread: 35, f: [[0, f], [0.25, f * 1.4], [0.7, f * 1.2], [1, f * 0.8]], tilt: 2200,
    formants: [[320, 2.5, 1], [720, 3, 0.9], [1500, 4, 0.5], [2600, 5, 0.2]], growl: { rate: r.range(20, 26), depth: 0.9 },
    breath: 0.4, drive: 4, curve: 'hard', direct: 0.6, directF: 300, amp: [[0, 0], [0.15, 0.9], [0.4, 1], [0.8, 0.7], [1, 0]],
  });
  k.nz(o, { kind: 'brown', t, dur: d, type: 'lowpass', f: 180, vol: 0.5, shape: 'bell', peakAt: 0.3 });
  return d + 0.1;
});

def('troll_grunt', 'creature', 5, 'room', 0.2, 0.24, (k, o, t, r) => {
  const d = r.range(0.3, 0.42), f = r.range(62, 74);
  roar(k, o, t, {
    dur: d, unison: 3, spread: 30, f: [[0, f * 1.2], [1, f * 0.8]], formants: [[350, 3, 1], [800, 3, 0.8], [1600, 4, 0.4]],
    growl: { rate: r.range(22, 27), depth: 0.8 }, breath: 0.3, drive: 3, direct: 0.6, directF: 300, amp: [[0, 0], [0.15, 1], [1, 0]],
  });
  return d + 0.08;
});

def('troll_hurt', 'creature', 6, 'room', 0.22, 0.29, (k, o, t, r) => {
  const d = r.range(0.5, 0.65), f = r.range(85, 100);
  roar(k, o, t, {
    dur: d, unison: 3, spread: 30, f: [[0, f], [0.2, f * 1.35], [1, f * 0.7]], formants: [[520, 3, 1], [1050, 3.5, 0.9], [1900, 4, 0.4]],
    growl: { rate: 28, depth: 0.8 }, breath: 0.35, drive: 4, curve: 'hard', direct: 0.5, directF: 350, amp: [[0, 0], [0.1, 1], [0.5, 0.7], [1, 0]],
  });
  return d + 0.08;
});

def('troll_death', 'creature', 8, 'hall', 0.3, 0.25, (k, o, t, r) => {
  const d = r.range(2.0, 2.5), f = r.range(70, 80);
  roar(k, o, t, {
    dur: d, unison: 3, spread: 35, f: [[0, f * 1.1], [0.15, f * 1.3], [1, f * 0.42]],
    formants: [[500, 3, 1], [1000, 3, 0.9], [1800, 4, 0.4]], formants1: [[260, 3, 1], [600, 3, 0.9], [1400, 4, 0.4]],
    growl: { rate: 24, rate1: 8, depth: 0.9 }, breath: 0.5, drive: 4, curve: 'hard', direct: 0.6, directF: 300, amp: [[0, 0], [0.1, 1], [0.5, 0.7], [1, 0]],
  });
  k.nz(o, { kind: 'pink', t: t + d * 0.7, dur: 0.7, f: 500, q: 1, vol: 0.5, shape: 'bell', peakAt: 0.3 });
  return d + 0.5;
});

def('troll_step', 'creature', 5, 'room', 0.2, 0.75, (k, o, t, r) => {
  k.tone(o, { f: r.range(58, 68), f1: 30, glide: 0.2, t, dur: 0.38, vol: 1 });
  k.nz(o, { kind: 'brown', t, dur: 0.25, type: 'lowpass', f: 350, vol: 1 });
  k.nz(o, { kind: 'pink', t, dur: 0.1, type: 'lowpass', f: 1200, vol: 0.5 });
  scatter(k, o, t + 0.04, 4, 0.2, 1200, 3500, 0.12, 0.01);
  return 0.5;
});

def('golem_rumble', 'creature', 5, 'room', 0.2, 0.85, (k, o, t, r) => {
  const d = r.range(1.4, 1.9);
  k.nz(o, { kind: 'brown', t, dur: d, type: 'lowpass', f: 220, vol: 1, shape: 'bell', peakAt: 0.4, am: { rate: 7, depth: 0.5, noise: true } });
  k.nz(o, { kind: 'pink', t, dur: d, f: r.range(450, 700), f1: r.range(300, 500), q: 2.5, vol: 1, shape: 'bell', peakAt: 0.45, am: { rate: r.range(16, 26), depth: 1, noise: true } });
  k.nz(o, { t, dur: d, f: 2600, q: 2, vol: 0.2, shape: 'bell', peakAt: 0.5, am: { rate: 40, depth: 1, noise: true } });
  k.tone(o, { f: 42, f1: 36, t, dur: d, vol: 0.5, shape: 'swell', peakAt: 0.4 });
  return d + 0.1;
});

def('golem_slam', 'creature', 8, 'hall', 0.35, 0.46, (k, o, t, r) => {
  k.tone(o, { f: r.range(88, 100), f1: 27, glide: 0.35, t, dur: 0.7, vol: 1.2 });
  click(k, o, t, 2500, 1, 0.02, 0.5);
  k.nz(o, { kind: 'pink', t, dur: 0.3, type: 'lowpass', f: 4000, f1: 300, vol: 1.2 });
  k.nz(o, { kind: 'brown', t, dur: 1.2, type: 'lowpass', f: 160, vol: 0.9 });
  k.modal(o, { t, f: r.range(700, 900), ratios: [1, 1.58, 2.37], gains: [0.2, 0.15, 0.1], decays: [0.05, 0.04, 0.03] });
  scatter(k, o, t + 0.06, 8, 0.6, 900, 4000, 0.18, 0.012);
  return 1.4;
});

def('wraith_wail', 'creature', 6, 'hall', 0.55, 0.08, (k, o, t, r) => {
  const d = r.range(2.0, 2.6), f = r.range(560, 700);
  const path = [[0, f * 0.8], [0.3, f * 1.3], [0.6, f * 1.15], [1, f * 0.7]];
  k.vox(o, {
    t, dur: d, type: 'triangle', unison: 3, spread: 30, f: path, vib: { rate: 6, depth: 0.02, delay: 0.3 }, jitter: { rate: 6, depth: 0.015 },
    formants: [[700, 5, 1], [1500, 6, 0.6], [3000, 8, 0.3]], formants1: [[400, 5, 1], [2000, 6, 0.6], [3200, 8, 0.3]],
    breath: 0.25, breathF: 2500, direct: 0.3, directF: 2000, amp: [[0, 0], [0.3, 1], [0.7, 0.8], [1, 0]],
  });
  k.vox(o, {
    t: t + 0.08, dur: d, type: 'sine', f: path.map(([x, v]) => [x, v * 1.498]), vib: { rate: 5.3, depth: 0.02 },
    formants: [[1500, 2, 1]], direct: 0.5, directF: 3000, vol: 0.35, amp: [[0, 0], [0.4, 1], [1, 0]],
  });
  return d + 0.2;
});

def('wraith_whisper', 'creature', 4, 'hall', 0.45, 0.48, (k, o, t, r) => {
  const d = r.range(1.2, 1.8);
  let tt = t;
  while (tt < t + d) {
    const sd = r.range(0.09, 0.2);
    k.vox(o, {
      t: tt, dur: sd, voiced: 0, breath: 1, breathKind: 'pink',
      formants: [[r.range(350, 800), 6, 1], [r.range(1100, 2400), 8, 0.9], [r.range(2800, 3600), 9, 0.5]],
      amp: [[0, 0], [0.3, 1], [1, 0]], vol: 1.5,
    });
    tt += sd * r.range(0.8, 1.3);
  }
  k.nz(o, { t, dur: d, type: 'highpass', f: 5000, vol: 0.05, shape: 'bell' });
  return d + 0.3;
});

def('wraith_death', 'creature', 7, 'hall', 0.55, 0.075, (k, o, t, r) => {
  const d = r.range(1.6, 2.0), f = r.range(800, 950);
  k.vox(o, {
    t, dur: d, type: 'triangle', unison: 3, spread: 40, f: [[0, f], [0.15, f * 1.2], [1, f * 0.2]], vib: { rate: 7, depth: 0.03, delay: 0.1 },
    formants: [[800, 4, 1], [1700, 5, 0.7], [3000, 6, 0.3]], formants1: [[300, 4, 1], [800, 5, 0.7], [2000, 6, 0.3]],
    breath: 0.4, breathF: 2500, direct: 0.3, directF: 2000, amp: [[0, 0], [0.08, 1], [0.6, 0.6], [1, 0]],
  });
  k.nz(o, { kind: 'pink', t: t + 0.2, dur: d, f: 6000, f1: 800, q: 2, vol: 0.5, shape: 'bell', peakAt: 0.3 });
  for (let i = 0; i < 6; i++) ping(k, o, t + d * 0.4 + i * 0.12, r.range(3000, 7000), 0.03, 0.4);
  return d + 0.4;
});

def('cultist_chant', 'creature', 5, 'hall', 0.45, 0.155, (k, o, t, r) => {
  const base = r.pick([43, 45, 41]), notes = r.pick([[0, 0, 1, 0], [0, 3, 1, 0], [0, 0, -2, 0], [0, 1, 3, 1]]);
  const vow = ['o', 'a', 'u', 'o'];
  let tt = t;
  for (let i = 0; i < 4; i++) {
    const sd = i === 3 ? r.range(0.7, 0.9) : r.range(0.38, 0.5), f = mtof(base + notes[i]);
    k.vox(o, {
      t: tt, dur: sd, type: 'glottal', unison: 3, spread: 22, f: [[0, f * 0.97], [0.15, f], [1, f]], vib: { rate: 5, depth: 0.008, delay: 0.2 },
      formants: V[vow[i]], direct: 0.25, directF: 400, breath: 0.03, a: 0.06, r: 0.12,
    });
    tt += sd * 0.95;
  }
  return tt - t + 0.2;
});

def('human_grunt', 'creature', 5, 'room', 0.12, 0.4, (k, o, t, r) => {
  const d = r.range(0.2, 0.27), f = r.range(115, 140);
  k.vox(o, {
    t, dur: d, type: 'glottal', f: [[0, f * 1.15], [0.3, f * 1.25], [1, f * 0.85]], jitter: { rate: 25, depth: 0.03 }, formants: V.uh,
    breath: 0.2, breathF: 1500, growl: { rate: 40, depth: 0.3 }, drive: 1.5, direct: 0.2, amp: [[0, 0], [0.12, 1], [0.5, 0.7], [1, 0]],
  });
  return d + 0.05;
});

def('human_hurt', 'creature', 6, 'room', 0.14, 0.34, (k, o, t, r) => {
  const d = r.range(0.26, 0.34), f = r.range(170, 200);
  k.vox(o, {
    t, dur: d, type: 'glottal', f: [[0, f * 1.2], [0.2, f * 1.3], [1, f * 0.8]], jitter: { rate: 25, depth: 0.03 }, formants: V.a, formants1: V.uh,
    breath: 0.25, breathF: 1800, growl: { rate: 45, depth: 0.35 }, drive: 2, direct: 0.2, amp: [[0, 0], [0.1, 1], [0.5, 0.7], [1, 0]],
  });
  return d + 0.05;
});

def('human_death', 'creature', 7, 'room', 0.2, 0.4, (k, o, t, r) => {
  const d = r.range(0.9, 1.2), f = r.range(160, 190);
  k.vox(o, {
    t, dur: d, type: 'glottal', f: [[0, f * 1.15], [0.15, f * 1.25], [1, f * 0.5]], jitter: { rate: 25, depth: 0.04 }, formants: V.a, formants1: V.o,
    breath: 0.35, breathF: 1500, growl: { rate: 30, rate1: 12, depth: 0.5 }, drive: 1.8, direct: 0.2, amp: [[0, 0], [0.08, 1], [0.5, 0.65], [1, 0]],
  });
  k.nz(o, { kind: 'pink', t: t + d * 0.6, dur: d * 0.6, f: 1100, q: 1, vol: 0.25, shape: 'bell', peakAt: 0.3 });
  return d + 0.3;
});

def('boss_roar', 'creature', 9, 'hall', 0.5, 0.155, (k, o, t, r) => {
  const d = r.range(2.3, 2.8), f = r.range(44, 52);
  roar(k, o, t, {
    dur: d, unison: 3, spread: 40, f: [[0, f], [0.2, f * 1.55], [0.7, f * 1.3], [1, f * 0.75]],
    formants: [[280, 2.5, 1], [650, 3, 0.9], [1400, 4, 0.5], [2500, 5, 0.25]], growl: { rate: r.range(18, 23), depth: 0.9 },
    breath: 0.45, drive: 5, curve: 'hard', direct: 0.7, directF: 260, amp: [[0, 0], [0.12, 0.9], [0.35, 1], [0.8, 0.7], [1, 0]],
  });
  roar(k, o, t + 0.05, {
    dur: d * 0.9, spread: 50, f: [[0, f * 4.2], [0.2, f * 6.4], [0.6, f * 5.6], [1, f * 3.4]],
    formants: [[900, 3, 1], [2000, 4, 0.8], [3400, 5, 0.4]], growl: { rate: 46, depth: 0.8 }, breath: 0.3, drive: 5, curve: 'hard',
    direct: 0, vol: 0.45, amp: [[0, 0], [0.15, 1], [0.6, 0.7], [1, 0]],
  });
  k.nz(o, { kind: 'brown', t, dur: d, type: 'lowpass', f: 150, vol: 0.8, shape: 'bell', peakAt: 0.3 });
  k.tone(o, { f: 38, f1: 30, t, dur: d, vol: 0.5, shape: 'swell', peakAt: 0.3 });
  return d + 0.1;
});

def('boss_phase', 'creature', 9, 'hall', 0.5, 0.46, (k, o, t, r) => {
  k.nz(o, { kind: 'pink', t, dur: 0.8, f: 400, f1: 5000, q: 1.5, vol: 0.7, shape: 'bell', peakAt: 0.97 });
  k.fm(o, { t, dur: 0.8, f: 80, f1: 320, ratio: 1.41, idx: 1, idx1: 5, vol: 0.25, shape: 'swell', peakAt: 0.97 });
  const t1 = t + 0.8, lp = k.bq('lowpass', 1300, 0.7);
  lp.connect(o);
  k.tone(o, { f: 110, f1: 30, glide: 0.4, t: t1, dur: 0.9, vol: 1.1 });
  k.nz(o, { kind: 'pink', t: t1, dur: 0.6, type: 'lowpass', f: 6000, f1: 250, vol: 1 });
  click(k, o, t1, 4000, 0.8, 0.015, 0.5);
  k.modal(o, {
    t: t1, f: r.range(82, 98), ratios: [1, 1.48, 2.02, 2.77, 3.41, 4.6, 5.87], gains: [0.5, 0.4, 0.35, 0.3, 0.2, 0.14, 0.08],
    decays: [2.4, 2.0, 1.7, 1.3, 1.0, 0.7, 0.5], a: 0.004, jit: 0.02,
  });
  for (const m of [50, 51, 56, 57]) k.tone(lp, { type: 'sawtooth', f: mtof(m), t: t1, dur: 1.6, vol: 0.07, shape: 'swell', peakAt: 0.1 });
  return 3.4;
});

def('boss_death', 'creature', 9, 'hall', 0.5, 0.26, (k, o, t, r) => {
  const d = 2.2, f = r.range(55, 65);
  roar(k, o, t, {
    dur: d, unison: 3, spread: 40, f: [[0, f * 1.4], [0.12, f * 1.8], [1, f * 0.45]],
    formants: [[420, 2.5, 1], [900, 3, 0.9], [1700, 4, 0.5], [2700, 5, 0.25]], formants1: [[240, 2.5, 1], [520, 3, 0.9], [1200, 4, 0.5], [2200, 5, 0.25]],
    growl: { rate: 24, rate1: 7, depth: 0.9 }, breath: 0.5, drive: 5, curve: 'hard', direct: 0.6, directF: 260, amp: [[0, 0], [0.06, 1], [0.5, 0.75], [1, 0]],
  });
  k.fm(o, { t: t + 1.2, dur: 1.4, f: 200, f1: 1600, ratio: 2.01, idx: 2, idx1: 0.3, vol: 0.12, shape: 'swell', peakAt: 0.95 });
  k.nz(o, { kind: 'pink', t: t + 1.2, dur: 1.4, f: 600, f1: 7000, q: 2, vol: 0.5, shape: 'bell', peakAt: 0.97 });
  const t1 = t + 2.6;
  k.tone(o, { f: 100, f1: 28, glide: 0.4, t: t1, dur: 0.9, vol: 1 });
  k.nz(o, { kind: 'pink', t: t1, dur: 0.7, type: 'lowpass', f: 8000, f1: 300, vol: 0.9 });
  for (let i = 0; i < 10; i++) ping(k, o, t1 + Math.pow(r.next(), 1.5) * 0.9, r.range(1800, 7000), 0.05, r.range(0.3, 0.9));
  bell(k, o, t1, r.range(98, 110), 0.25, 1.4);
  return 4.6;
});

// ---------------------------------------------------------------------------------------
// World
// ---------------------------------------------------------------------------------------

def('chest_open', 'world', 6, 'room', 0.2, 0.75, (k, o, t, r) => {
  click(k, o, t, 3200, 0.5, 0.01, 1.5);
  metal(k, o, t, r.range(1800, 2300), 0.08, 0.08);
  const d = r.range(0.4, 0.55), t1 = t + 0.08, f = r.range(70, 95);
  k.vox(o, {
    t: t1, dur: d, type: 'sawtooth', f: [[0, f], [0.5, f * 1.5], [1, f * 1.9]], jitter: { rate: 45, depth: 0.12 },
    formants: [[r.range(750, 950), 12, 1], [r.range(1500, 1900), 14, 0.7], [2900, 12, 0.3]], growl: { rate: f * 0.5, depth: 0.6 },
    amp: [[0, 0], [0.2, 0.6], [0.7, 1], [1, 0]], vol: 0.6,
  });
  const t2 = t1 + d;
  k.modal(o, { t: t2, f: r.range(150, 190), ratios: WOOD, gains: [0.7, 0.4, 0.25, 0.1], decays: [0.14, 0.09, 0.05, 0.03], bend: 1.15 });
  k.nz(o, { kind: 'pink', t: t2, dur: 0.05, type: 'lowpass', f: 1500, vol: 0.5 });
  ping(k, o, t2 + 0.05, r.range(3000, 3600), 0.04, 0.5);
  return d + 0.6;
});

def('pickup_item', 'world', 6, null, 0, 1.4, (k, o, t, r) => {
  const f = r.range(640, 760);
  k.nz(o, { kind: 'pink', t, dur: 0.08, f: r.range(1300, 1800), q: 0.9, vol: 0.5, a: 0.008 });
  k.tone(o, { type: 'triangle', f, f1: f * 1.5, glide: 0.06, t: t + 0.03, dur: 0.12, vol: 0.25 });
  ping(k, o, t + 0.08, f * 3, 0.05, 0.25);
  return 0.35;
});

def('pickup_gold', 'world', 6, 'room', 0.12, 1.5, (k, o, t, r) => {
  const n = r.int(4, 6);
  let tt = t;
  for (let i = 0; i < n; i++) {
    k.modal(o, { t: tt, f: r.range(4000, 6500), ratios: [1, 1.48, 2.13, 2.9], gains: [1, 0.6, 0.4, 0.2], decays: [0.14, 0.1, 0.06, 0.04], vol: r.range(0.08, 0.14) });
    click(k, o, tt, 8000, 0.1, 0.004);
    tt += r.range(0.025, 0.06);
  }
  return tt - t + 0.2;
});

def('shrine_ignite', 'world', 8, 'hall', 0.3, 0.7, (k, o, t, r) => {
  k.nz(o, { kind: 'pink', t, dur: 0.9, type: 'lowpass', f: 200, fmid: 2800, f1: 700, peakAt: 0.35, vol: 1, shape: 'bell', am: { rate: 30, depth: 0.4, noise: true } });
  thump(k, o, t + 0.25, 85, 40, 0.3, 0.8);
  crackle(k, o, t + 0.2, 1.3, 0.5, 1500);
  k.tone(o, { type: 'triangle', f: mtof(50), t: t + 0.25, dur: 1.4, vol: 0.12, shape: 'swell', peakAt: 0.2 });
  k.tone(o, { type: 'triangle', f: mtof(57), t: t + 0.4, dur: 1.3, vol: 0.1, shape: 'swell', peakAt: 0.2 });
  ping(k, o, t + 0.3, mtof(r.pick([86, 88, 81])), 0.05, 0.9);
  return 1.8;
});

def('shrine_rest', 'world', 8, 'hall', 0.5, 0.31, (k, o, t, r) => {
  const notes = [81, 86, 90, 93];
  bell(k, o, t, mtof(62), 0.18, 2.0);
  for (const [m, v, dl] of [[50, 0.1, 0], [57, 0.09, 0.1], [62, 0.07, 0.2], [66, 0.05, 0.4]]) {
    k.tone(o, { type: 'triangle', f: mtof(m), t: t + dl, dur: 2.8, vol: v, shape: 'swell', peakAt: 0.3 });
  }
  k.vox(o, { t: t + 0.2, dur: 2.6, type: 'glottal', unison: 3, spread: 18, f: mtof(57), vib: { rate: 5, depth: 0.006, delay: 0.5 }, formants: V.u, direct: 0.1, a: 0.8, r: 1.2, vol: 0.5 });
  for (let i = 0; i < 4; i++) ping(k, o, t + 0.5 + i * r.range(0.25, 0.35), mtof(notes[i]), 0.03, 0.9);
  return 3.2;
});

def('fast_travel', 'world', 8, 'hall', 0.4, 0.74, (k, o, t, r) => {
  const dl = k.delay(0.012, 0.05), mix = k.gain(1);
  dl.delayTime.setValueAtTime(0.012, t);
  dl.delayTime.exponentialRampToValueAtTime(0.0006, t + 1.1);
  mix.connect(o); mix.connect(dl); dl.connect(o);
  k.nz(mix, { kind: 'pink', t, dur: 1.15, f: 300, f1: 6000, q: 1.2, vol: 0.6, shape: 'bell', peakAt: 0.92 });
  k.fm(o, { t, dur: 1.15, f: 110, f1: 1320, ratio: 2, idx: 1, idx1: 3, vol: 0.12, shape: 'swell', peakAt: 0.92 });
  const t1 = t + 1.12;
  thump(k, o, t1, 120, 40, 0.4, 0.8);
  k.nz(o, { kind: 'pink', t: t1, dur: 0.7, type: 'lowpass', f: 9000, f1: 500, vol: 0.5 });
  for (let i = 0; i < 6; i++) ping(k, o, t1 + r.range(0, 0.4), r.range(2000, 6000), 0.05, 0.6);
  return 2.0;
});

def('anvil', 'world', 5, 'room', 0.2, 0.43, (k, o, t, r) => {
  const f = r.range(1050, 1300);
  click(k, o, t, 6000, 0.9, 0.006, 0.6);
  k.modal(o, {
    t, f, ratios: [1, 1.47, 2.09, 2.56, 3.39, 4.08, 5.2], gains: [0.35, 0.3, 0.3, 0.22, 0.18, 0.12, 0.08],
    decays: [0.9, 0.8, 0.6, 0.5, 0.35, 0.25, 0.15], decay: r.range(0.7, 1.1), jit: 0.02,
  });
  thump(k, o, t, 200, 110, 0.06, 0.5);
  k.nz(o, { t, dur: 0.03, f: 3000, q: 0.7, vol: 0.5 });
  return 1.1;
});

def('crystal_chime', 'world', 5, 'hall', 0.5, 0.78, (k, o, t, r) => {
  const scale = [0, 2, 5, 7, 9, 12, 14], base = r.pick([74, 76, 79]), n = r.int(2, 3);
  for (let i = 0; i < n; i++) {
    const f = mtof(base + r.pick(scale)), tt = t + i * r.range(0.09, 0.16);
    k.modal(o, { t: tt, f, ratios: BAR, gains: [0.25, 0.1, 0.05, 0.02], decays: [1.5, 0.8, 0.4, 0.2] });
    k.modal(o, { t: tt, f: f * 1.004, ratios: [1, 2.76], gains: [0.12, 0.05], decays: [1.4, 0.7] });
    click(k, o, tt, 7000, 0.08, 0.004);
  }
  return 1.9;
});

def('rune_activate', 'world', 7, 'hall', 0.4, 1.1, (k, o, t, r) => {
  const base = r.pick([110, 123.5, 98]);
  k.nz(o, { kind: 'pink', t, dur: 0.3, f: 500, q: 2, vol: 0.7, am: { rate: 22, depth: 1, noise: true } });
  k.fm(o, { t, dur: 1.2, f: base, ratio: 1.5, idx: 0.3, idx1: 2.5, vol: 0.3, shape: 'swell', peakAt: 0.4 });
  for (let i = 0; i < 5; i++) ping(k, o, t + 0.15 + i * 0.07, base * 2 * (i + 2), 0.07, 0.7);
  k.nz(o, { t: t + 0.1, dur: 0.9, f: 5000, q: 3, vol: 0.1, shape: 'bell', peakAt: 0.3 });
  thump(k, o, t + 0.1, 100, 50, 0.2, 0.5);
  return 1.4;
});

def('death_toll', 'world', 9, 'hall', 0.55, 0.48, (k, o, t, r) => {
  const f = mtof(r.pick([45, 46, 47]));
  bell(k, o, t, f, 0.5, 3.4);
  k.modal(o, { t, f: f * 1.003, ratios: [1, 2, 3.01], gains: [0.2, 0.15, 0.06], decays: [3.2, 2.0, 1.2], a: 0.003 });
  click(k, o, t, 1800, 0.5, 0.02, 0.6);
  thump(k, o, t, 90, 50, 0.15, 0.5);
  return 4.4;
});

def('respawn', 'world', 9, 'hall', 0.5, 1.0, (k, o, t, r) => {
  const arp = [0, 7, 12, 7, 19];
  k.nz(o, { kind: 'pink', t, dur: 0.9, f: 300, f1: 4000, q: 1.5, vol: 0.6, shape: 'bell', peakAt: 0.95 });
  k.tone(o, { f: 110, f1: 440, t, dur: 0.9, vol: 0.15, shape: 'swell', peakAt: 0.95 });
  const t1 = t + 0.9;
  for (const [m, v] of [[50, 0.14], [57, 0.12], [62, 0.1], [69, 0.07], [74, 0.05]]) k.tone(o, { type: 'triangle', f: mtof(m), t: t1, dur: 1.6, vol: v, shape: 'swell', peakAt: 0.06 });
  bell(k, o, t1, mtof(62), 0.1, 1.2);
  for (let i = 0; i < 5; i++) ping(k, o, t1 + i * r.range(0.07, 0.09), mtof(74 + arp[i]), 0.04, 0.6);
  thump(k, o, t1, 100, 45, 0.3, 0.5);
  return 2.7;
});

def('splash', 'world', 5, 'room', 0.15, 0.8, (k, o, t, r) => {
  const s = r.range(0.85, 1.15);
  k.nz(o, { t, dur: 0.4, type: 'lowpass', f: 6000 * s, f1: 700, vol: 0.9, a: 0.008 });
  k.nz(o, { kind: 'pink', t, dur: 0.18, type: 'lowpass', f: 500, vol: 0.9 });
  for (let i = 0; i < 6; i++) {
    const f = r.range(280, 900), tt = t + 0.05 + r.range(0, 0.35);
    k.tone(o, { f, f1: f * r.range(1.6, 2.4), glide: 0.05, t: tt, dur: 0.07, vol: 0.2, a: 0.006 });
  }
  for (let i = 0; i < 4; i++) {
    const f = r.range(1500, 3500), tt = t + 0.25 + r.range(0, 0.4);
    k.tone(o, { f, f1: f * 1.3, t: tt, dur: 0.03, vol: 0.08 });
  }
  return 0.8;
});

def('bush_rustle', 'world', 3, 'room', 0.08, 1.2, (k, o, t, r) => {
  const n = r.int(3, 5);
  let tt = t;
  for (let i = 0; i < n; i++) {
    const d = r.range(0.07, 0.14);
    k.nz(o, { t: tt, dur: d, f: r.range(3500, 6500), q: 0.7, hp: 2000, vol: r.range(0.4, 0.8), shape: 'bell', peakAt: 0.3, am: { rate: 70, depth: 0.8, noise: true } });
    tt += d * r.range(0.5, 0.9);
  }
  k.nz(o, { kind: 'pink', t, dur: tt - t + 0.05, f: 900, q: 1, vol: 0.2, shape: 'bell' });
  click(k, o, t + r.range(0.02, 0.1), r.range(1500, 2500), 0.15, 0.008, 2);
  return tt - t + 0.15;
});

/** Ordered list of public SFX names. */
export const SFX_NAMES = Object.keys(SFX);
