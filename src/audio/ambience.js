/**
 * VALOMBRE audio - layered ambience.
 *
 * Continuous layers (wind, howl, leaves, crickets, insects, surf, brook, rain, ash drones,
 * citadel hollow wind, village murmur, danger drone) are cross-faded from the smoothed
 * ambience state; sparse one-shot events (birds, owl, frogs, bells, whispers, hammering,
 * chickens, thunder...) are scheduled at random positions around the listener.
 */
import { clamp, smooth01, mtof, TAU } from './core.js';
import { WOOD, bell, click, thump, roar, define } from './recipes.js';

export const BIOMES = ['meadow', 'forest', 'swamp', 'mountain', 'ash', 'coast', 'citadel', 'village'];
const SCALARS = ['rain', 'wind', 'water', 'danger'];

// ---------------------------------------------------------------------------------------
// Event recipes (same signature as SFX recipes)
// ---------------------------------------------------------------------------------------

/** @type {Record<string, object>} */
export const AMB = Object.create(null);
const def = (name, rev, send, gain, fn) => define(AMB, name, 'amb', 1, rev, send, gain, fn);

def('bird_meadow', 'hall', 0.12, 2.0, (k, o, t, r) => {
  const v = r.int(0, 3);
  let tt = t;
  if (v === 0) {                                   // lark: fast warble
    const n = r.int(6, 12), f = r.range(3200, 4500);
    for (let i = 0; i < n; i++) {
      const d = r.range(0.04, 0.07), a = f * r.range(0.85, 1.2);
      k.tone(o, { f: a, f1: a * (r.chance(0.5) ? 1.25 : 0.8), t: tt, dur: d, vol: 0.25, a: 0.008, shape: 'flat', r: 0.015 });
      tt += d + r.range(0.01, 0.04);
    }
    return tt - t + 0.1;
  }
  if (v === 1) {                                   // sparrow: a few dry chirps
    const n = r.int(2, 4), f = r.range(3800, 5200);
    for (let i = 0; i < n; i++) {
      k.tone(o, { f: f * 1.3, f1: f * 0.75, t: tt, dur: 0.05, vol: 0.3, a: 0.004 });
      tt += r.range(0.11, 0.18);
    }
    return tt - t + 0.1;
  }
  if (v === 2) {                                   // finch: descending whistles
    const n = r.int(4, 7);
    let f = r.range(4200, 5200);
    for (let i = 0; i < n; i++) {
      k.tone(o, { f, f1: f * 0.88, t: tt, dur: 0.09, vol: 0.25, a: 0.012, shape: 'flat', r: 0.03 });
      f *= r.range(0.86, 0.95); tt += r.range(0.1, 0.14);
    }
    return tt - t + 0.1;
  }
  const f = r.range(640, 700);                     // cuckoo
  k.tone(o, { f, t, dur: 0.22, vol: 0.2, a: 0.03, shape: 'flat', r: 0.08 });
  k.tone(o, { f: f * 2, t, dur: 0.2, vol: 0.03, a: 0.03, shape: 'flat', r: 0.08 });
  k.tone(o, { f: f * 0.8, t: t + 0.33, dur: 0.3, vol: 0.2, a: 0.03, shape: 'flat', r: 0.12 });
  k.tone(o, { f: f * 1.6, t: t + 0.33, dur: 0.28, vol: 0.03, a: 0.03, shape: 'flat', r: 0.1 });
  return 0.8;
});

def('bird_forest', 'hall', 0.2, 1.5, (k, o, t, r) => {
  const v = r.int(0, 3);
  let tt = t;
  if (v === 0) {                                   // blackbird: fluty phrase
    const n = r.int(4, 6);
    for (let i = 0; i < n; i++) {
      const d = r.range(0.12, 0.25), f = r.range(1700, 3000);
      k.fm(o, { t: tt, dur: d, f, f1: f * r.range(0.8, 1.3), ratio: 0.012, idx: 0.03, vol: 0.3, shape: 'flat', a: 0.02, r: 0.04 });
      tt += d + r.range(0.02, 0.1);
    }
    for (let i = 0; i < 3; i++) { k.tone(o, { f: r.range(4500, 6000), t: tt, dur: 0.04, vol: 0.12, a: 0.005 }); tt += 0.06; }
    return tt - t + 0.1;
  }
  if (v === 1) {                                   // tit: two-note "tee-cher"
    const n = r.int(3, 4), hi = r.range(4000, 4500);
    for (let i = 0; i < n; i++) {
      k.tone(o, { f: hi, t: tt, dur: 0.1, vol: 0.28, a: 0.01, shape: 'flat', r: 0.03 });
      k.tone(o, { f: hi * 0.78, t: tt + 0.13, dur: 0.11, vol: 0.28, a: 0.01, shape: 'flat', r: 0.03 });
      tt += r.range(0.3, 0.34);
    }
    return tt - t + 0.1;
  }
  if (v === 2) {                                   // woodpecker drumming
    const n = r.int(10, 16), f = r.range(800, 1100);
    let gap = r.range(0.042, 0.05);
    for (let i = 0; i < n; i++) {
      const vol = 0.5 * (1 - (i / n) * 0.6);
      k.modal(o, { t: tt, f, ratios: WOOD, gains: [0.5, 0.35, 0.2, 0.1], decays: [0.025, 0.02, 0.015, 0.01], vol });
      click(k, o, tt, 2400, vol * 0.6, 0.006, 1.5);
      tt += gap; gap *= 1.02;
    }
    return tt - t + 0.1;
  }
  const f = r.range(420, 470), durs = [0.25, 0.42, 0.3, 0.2, 0.2];   // wood pigeon
  for (let i = 0; i < 5; i++) {
    const ff = f * (i === 1 ? 1.12 : 1);
    k.tone(o, { f: ff * 0.94, f1: ff, glide: 0.08, t: tt, dur: durs[i], vol: 0.4, a: 0.05, shape: 'flat', r: 0.1 });
    tt += durs[i] + 0.08;
  }
  return tt - t + 0.1;
});

def('crow', 'hall', 0.2, 0.25, (k, o, t, r) => {
  const n = r.int(2, 3), f = r.range(360, 430);
  let tt = t;
  for (let i = 0; i < n; i++) {
    const d = r.range(0.24, 0.32);
    roar(k, o, tt, {
      dur: d, f: [[0, f], [0.3, f * 1.2], [1, f * 0.88]], formants: [[1300, 4, 1], [1900, 5, 0.8], [2800, 6, 0.4]],
      growl: { rate: r.range(62, 80), depth: 0.8 }, breath: 0.3, drive: 3, direct: 0, amp: [[0, 0], [0.15, 1], [0.7, 0.8], [1, 0]],
    });
    tt += d + r.range(0.12, 0.2);
  }
  return tt - t + 0.1;
});

def('owl', 'hall', 0.3, 1.0, (k, o, t, r) => {
  const f = r.range(330, 400), pat = [[0, 0.26], [0.62, 0.12], [0.8, 0.12], [1.02, 0.5]];
  for (const [dt, d] of pat) {
    k.tone(o, { f, f1: f * (d > 0.3 ? 0.9 : 0.97), t: t + dt, dur: d, vol: 0.5, a: 0.04, shape: 'flat', r: d * 0.45 });
    k.tone(o, { f: f * 2, t: t + dt, dur: d, vol: 0.05, a: 0.04, shape: 'flat', r: d * 0.45 });
    k.nz(o, { kind: 'pink', t: t + dt, dur: d, f, q: 3, vol: 0.2, shape: 'bell', peakAt: 0.3 });
  }
  return 1.7;
});

def('frog', 'room', 0.1, 0.45, (k, o, t, r) => {
  if (r.chance(0.35)) {                            // spring peeper
    const n = r.int(1, 3), f = r.range(2500, 2900);
    for (let i = 0; i < n; i++) k.tone(o, { f, f1: f * 1.14, t: t + i * 0.19, dur: 0.09, vol: 0.3, a: 0.01, shape: 'flat', r: 0.03 });
    return n * 0.19 + 0.1;
  }
  const f = r.range(62, 92), n = r.chance(0.6) ? 2 : 1;
  for (let i = 0; i < n; i++) {
    const d = i ? r.range(0.2, 0.3) : r.range(0.1, 0.16), s = i ? 1.25 : 1;
    k.vox(o, {
      t: t + i * 0.17, dur: d, type: 'sawtooth', f: [[0, f], [1, f * 1.15]],
      formants: [[700 * s, 5, 1], [1400 * s, 6, 0.8], [2200 * s, 6, 0.3]], amp: [[0, 0], [0.2, 1], [0.7, 0.8], [1, 0]],
    });
  }
  return 0.6;
});

def('bubble', 'room', 0.1, 1.0, (k, o, t, r) => {
  const n = r.int(1, 3);
  for (let i = 0; i < n; i++) {
    const f = r.range(200, 480), tt = t + i * r.range(0.07, 0.16);
    k.tone(o, { f, f1: f * r.range(1.8, 2.4), glide: 0.05, t: tt, dur: 0.07, vol: 0.5, a: 0.008 });
    k.nz(o, { kind: 'pink', t: tt, dur: 0.04, type: 'lowpass', f: 600, vol: 0.2, a: 0.005 });
  }
  return 0.5;
});

def('bell_far', 'hall', 0.7, 0.7, (k, o, t, r) => {
  const lp = k.bq('lowpass', 1700, 0.5), f = mtof(r.pick([50, 53, 45, 48])), n = r.int(1, 2);
  lp.connect(o);
  for (let i = 0; i < n; i++) bell(k, lp, t + i * r.range(1.8, 2.2), f, 0.5, 2.4);
  return n * 2.0 + 2.2;
});

def('whisper', 'hall', 0.6, 0.8, (k, o, t, r) => {
  const d = r.range(0.6, 1.2);
  let tt = t;
  while (tt < t + d) {
    const sd = r.range(0.09, 0.2);
    k.vox(o, {
      t: tt, dur: sd, voiced: 0, breath: 1, breathKind: 'pink',
      formants: [[r.range(350, 800), 6, 1], [r.range(1100, 2400), 8, 0.9]], amp: [[0, 0], [0.3, 1], [1, 0]], vol: 1.5,
    });
    tt += sd * r.range(0.8, 1.3);
  }
  return d + 0.3;
});

def('hammer_far', 'hall', 0.25, 0.6, (k, o, t, r) => {
  const lp = k.bq('lowpass', 2600, 0.5), n = r.int(3, 5), f = r.range(1080, 1250), gap = r.range(0.42, 0.52);
  lp.connect(o);
  for (let i = 0; i < n; i++) {
    const tt = t + i * gap + r.range(-0.015, 0.015);
    k.modal(lp, { t: tt, f, ratios: [1, 1.47, 2.09, 2.56, 3.39], gains: [0.35, 0.3, 0.3, 0.2, 0.15], decays: [0.3, 0.25, 0.2, 0.15, 0.1], jit: 0.01, vol: r.range(0.7, 1) });
    thump(k, lp, tt, 190, 110, 0.05, 0.3);
    if (i === n - 1 && r.chance(0.5)) k.modal(lp, { t: tt + 0.11, f, ratios: [1, 1.47, 2.09], gains: [0.15, 0.12, 0.1], decays: [0.2, 0.15, 0.1] });
  }
  return n * gap + 0.5;
});

def('chicken', 'room', 0.1, 0.45, (k, o, t, r) => {
  const n = r.int(3, 6), f = r.range(400, 470);
  let tt = t;
  for (let i = 0; i < n; i++) {
    const d = r.range(0.055, 0.085);
    k.vox(o, { t: tt, dur: d, type: 'sawtooth', tilt: 3500, f: [[0, f], [0.3, f * 1.35], [1, f * 0.9]], formants: [[1200, 5, 1], [2600, 6, 0.7]], a: 0.008, r: 0.03 });
    tt += d + r.range(0.1, 0.24);
  }
  if (r.chance(0.3)) {
    k.vox(o, {
      t: tt, dur: 0.32, type: 'sawtooth', tilt: 3500, f: [[0, f * 1.1], [0.4, f * 1.9], [1, f * 1.2]], jitter: { rate: 30, depth: 0.04 },
      formants: [[1300, 4, 1], [2700, 5, 0.8]], growl: { rate: 50, depth: 0.5 }, amp: [[0, 0], [0.15, 0.7], [0.5, 1], [1, 0]],
    });
    tt += 0.35;
  }
  return tt - t + 0.1;
});

def('dog_far', 'hall', 0.3, 0.3, (k, o, t, r) => {
  const lp = k.bq('lowpass', 2200, 0.5), n = r.int(2, 4), f = r.range(250, 330);
  lp.connect(o);
  let tt = t;
  for (let i = 0; i < n; i++) {
    const d = r.range(0.11, 0.15);
    roar(k, lp, tt, {
      dur: d, f: [[0, f * 1.2], [0.25, f * 1.4], [1, f * 0.8]], formants: [[700, 4, 1], [1500, 5, 0.8], [2600, 6, 0.3]],
      growl: { rate: 60, depth: 0.5 }, breath: 0.3, drive: 3, amp: [[0, 0], [0.12, 1], [0.5, 0.6], [1, 0]],
    });
    tt += d + r.range(0.18, 0.45);
  }
  return tt - t + 0.1;
});

def('gull', 'hall', 0.2, 0.35, (k, o, t, r) => {
  const n = r.int(3, 5);
  let tt = t, f = r.range(950, 1150), d = r.range(0.3, 0.4);
  for (let i = 0; i < n; i++) {
    k.vox(o, {
      t: tt, dur: d, type: 'sawtooth', tilt: 3500, f: [[0, f * 0.8], [0.25, f * 1.25], [1, f * 0.85]], jitter: { rate: 30, depth: 0.03 },
      formants: [[1500, 4, 1], [2600, 5, 0.8], [3600, 6, 0.4]], amp: [[0, 0], [0.2, 1], [0.6, 0.8], [1, 0]],
    });
    tt += d + r.range(0.05, 0.12); d *= 0.85; f *= 0.97;
  }
  return tt - t + 0.1;
});

def('hawk', 'hall', 0.3, 0.25, (k, o, t, r) => {
  const d = r.range(0.8, 1.1), f = r.range(2100, 2500);
  k.vox(o, {
    t, dur: d, type: 'sawtooth', tilt: 5000, f: [[0, f], [0.15, f * 1.12], [1, f * 0.65]], jitter: { rate: 40, depth: 0.03 },
    formants: [[2400, 3, 1], [3600, 4, 0.6]], breath: 0.1, amp: [[0, 0], [0.1, 1], [0.6, 0.7], [1, 0]],
  });
  return d + 0.1;
});

/** Thunder: fn(k, o, t, r, distance01). 0 = overhead crack, 1 = far rumble. */
export const THUNDER = {
  name: 'thunder', cat: 'weather', prio: 7, rev: 'hall', send: 0.5, gain: 1.0,
  fn(k, o, t, r, dist) {
    dist = clamp(dist === undefined ? 0.5 : dist, 0, 1);
    const near = 1 - dist, m = k.gain(1.15 - 0.5 * dist), pan = k.pan(r.range(-0.5, 0.5));
    m.connect(pan); pan.connect(o);
    if (near > 0.25) {
      const n = r.int(2, 4);
      for (let i = 0; i < n; i++) {
        k.nz(m, { t: t + i * r.range(0.04, 0.12), dur: r.range(0.08, 0.2), type: 'highpass', f: 800 + 2000 * dist, vol: near * r.range(0.4, 0.8), a: 0.002 });
      }
      k.nz(m, { kind: 'pink', t, dur: 0.5, type: 'lowpass', f: 6000, f1: 500, vol: near * 0.9 });
    }
    const dur = r.range(3.5, 5.5), lpF = 520 - 380 * dist, rolls = r.int(3, 5);
    for (let i = 0; i < rolls; i++) {
      const tt = t + 0.1 + (i * dur / rolls) * r.range(0.6, 1);
      k.nz(m, {
        kind: 'brown', t: tt, dur: dur * r.range(0.35, 0.6), type: 'lowpass', f: lpF * r.range(0.7, 1.3),
        vol: (0.8 + 0.5 * near) * r.range(0.5, 1) * (1 - i / (rolls + 1)), shape: 'bell', peakAt: r.range(0.1, 0.3),
      });
    }
    k.tone(m, { f: 48, f1: 32, t, dur: 1.5, vol: 0.4 + 0.4 * near, a: 0.03 });
    return dur + 0.8;
  },
};

// ---------------------------------------------------------------------------------------
// Continuous layers
// ---------------------------------------------------------------------------------------

function wob(k, param, t, rate, depth) {
  const l = k.lfoNoise(rate, t), g = k.gain(depth);
  l.connect(g); g.connect(param);
}

function chain(o, ...nodes) {
  for (let i = 0; i < nodes.length - 1; i++) nodes[i].connect(nodes[i + 1]);
  nodes[nodes.length - 1].connect(o);
}

/** name -> builder(k, o, t, r) returning an optional control object. */
const LAYERS = {
  wind(k, o, t) {
    const bps = [];
    for (const [pan, rate] of [[-0.5, 1], [0.5, 0.87]]) {
      const n = k.noise('pink', t, undefined, rate), bp = k.bq('bandpass', 420, 0.7), g = k.gain(0.8);
      chain(o, n, bp, g, k.pan(pan));
      wob(k, g.gain, t, 0.4, 0.5); wob(k, bp.frequency, t, 0.3, 160);
      bps.push(bp);
    }
    const lg = k.gain(0.9);
    chain(o, k.noise('brown', t), k.bq('lowpass', 260, 0.7), lg);
    wob(k, lg.gain, t, 0.3, 0.4);
    return { bps };
  },
  howl(k, o, t) {
    for (const [f, pan] of [[480, -0.35], [730, 0.4], [1080, 0]]) {
      const bp = k.bq('bandpass', f, 18), g = k.gain(2.2);
      chain(o, k.noise('pink', t), bp, g, k.pan(pan));
      wob(k, bp.frequency, t, 0.5, f * 0.3); wob(k, g.gain, t, 0.35, 2.0);
    }
  },
  hollow(k, o, t) {
    for (const [f, q, pan] of [[118, 6, 0], [172, 7, -0.4], [291, 9, 0.4]]) {
      const bp = k.bq('bandpass', f, q), g = k.gain(2.0);
      chain(o, k.noise('brown', t), bp, g, k.pan(pan));
      wob(k, bp.frequency, t, 0.18, f * 0.12); wob(k, g.gain, t, 0.22, 1.6);
    }
  },
  leaves(k, o, t) {
    for (const pan of [-0.6, 0.6]) {
      const g = k.gain(0.3);
      chain(o, k.noise('white', t), k.bq('highpass', 3200, 0.7), k.bq('bandpass', 6000, 0.5), g, k.pan(pan));
      wob(k, g.gain, t, 1.3, 0.25);
    }
  },
  crickets(k, o, t) {
    chain(o, k.buf(k.res.baked('crickets'), t, { loop: true }), k.gain(0.5));
  },
  insects(k, o, t) {
    for (const [f, am, pan] of [[5800, 140, -0.4], [7300, 173, 0.4]]) {
      const amg = k.gain(0.5), l = k.osc('sawtooth', am, t), lg = k.gain(0.5), g = k.gain(0.55);
      l.connect(lg); lg.connect(amg.gain);
      chain(o, k.noise('white', t), k.bq('bandpass', f, 7), amg, g, k.pan(pan));
      wob(k, g.gain, t, 0.5, 0.4);
    }
  },
  surf(k, o, t) {
    const lp = k.bq('lowpass', 400, 0.6), g = k.gain(0.15), hg = k.gain(0.02);
    chain(o, k.noise('pink', t), lp, g);
    chain(o, k.noise('white', t), k.bq('highpass', 2500, 0.6), k.bq('lowpass', 9000, 0.6), hg);
    return { lp, g, hg, next: t };
  },
  brook(k, o, t) {
    chain(o, k.buf(k.res.baked('brook'), t, { loop: true }), k.gain(0.6));
  },
  rain(k, o, t) {
    const hiss = k.gain(0), body = k.gain(0), drops = k.gain(0);
    chain(o, k.noise('white', t), k.bq('highpass', 2200, 0.6), k.bq('lowpass', 9500, 0.6), hiss);
    chain(o, k.noise('pink', t), k.bq('bandpass', 1100, 0.5), body);
    chain(o, k.buf(k.res.baked('raindrops'), t, { loop: true }), k.bq('highpass', 900, 0.6), drops);
    return { hiss, body, drops };
  },
  ash(k, o, t) {
    const dg = k.gain(0.09);
    for (const f of [55, 55.6]) k.osc('sine', f, t).connect(dg);
    dg.connect(o);
    wob(k, dg.gain, t, 0.2, 0.04);
    const sg = k.gain(0.1);
    chain(o, k.osc('sawtooth', 82.4, t), k.bq('lowpass', 260, 2), sg);
    wob(k, sg.gain, t, 0.15, 0.06);
    for (const [f, a] of [[138.6, 0.035], [277.2, 0.025], [293.7, 0.012]]) {
      const hg = k.gain(a);
      chain(o, k.osc('sine', f, t), hg);
      wob(k, hg.gain, t, 0.3, a);
    }
    const rg = k.gain(0.3);
    chain(o, k.noise('brown', t), k.bq('lowpass', 180, 0.7), rg);
    wob(k, rg.gain, t, 0.25, 0.15);
    chain(o, k.buf(k.res.baked('embers'), t, { loop: true }), k.bq('bandpass', 2500, 0.5), k.gain(0.7));
  },
  murmur(k, o, t) {
    chain(o, k.buf(k.res.baked('murmur'), t, { loop: true }), k.bq('lowpass', 1500, 0.5), k.bq('highpass', 220, 0.5), k.gain(0.6));
  },
  danger(k, o, t) {
    const dg = k.gain(0.1), trem = k.osc('sine', 0.4, t), tg = k.gain(0.05);
    trem.connect(tg); tg.connect(dg.gain);
    for (const f of [55, 58.3, 110.4]) k.osc('sine', f, t).connect(dg);
    dg.connect(o);
    const ng = k.gain(0.4);
    chain(o, k.noise('brown', t), k.bq('bandpass', 110, 2), ng);
    wob(k, ng.gain, t, 0.3, 0.2);
    const hg = k.gain(0.018);
    for (const f of [1318.5, 1396.9]) k.osc('sine', f, t).connect(hg);
    hg.connect(o);
    wob(k, hg.gain, t, 0.4, 0.018);
  },
};
const LAYER_NAMES = Object.keys(LAYERS);

/** Random events: rate(s) is the expected count per minute for the smoothed state `s`. */
const EVENTS = [
  { amb: 'bird_meadow', dist: [10, 32], h: [2, 10], rate: (s) => 16 * s.day * (s.w.meadow + 0.45 * s.w.village + 0.3 * s.w.coast) * (1 + 2.2 * s.dawn) * (1 - 0.9 * s.rain) * (1 - 0.7 * s.danger) },
  { amb: 'bird_forest', dist: [10, 34], h: [3, 14], rate: (s) => 13 * s.day * (s.w.forest + 0.25 * s.w.swamp + 0.2 * s.w.mountain) * (1 + 2.2 * s.dawn) * (1 - 0.9 * s.rain) * (1 - 0.7 * s.danger) },
  { amb: 'crow', dist: [18, 45], h: [6, 20], rate: (s) => s.day * (1.5 * s.w.forest + 1.1 * s.w.ash + 1.3 * s.w.citadel + 1.0 * s.w.swamp + 0.5 * s.w.mountain) * (1 - 0.6 * s.rain) },
  { amb: 'owl', dist: [16, 40], h: [4, 12], rate: (s) => s.night * (1.7 * s.w.forest + 0.7 * s.w.meadow + 0.5 * s.w.mountain + 0.4 * s.w.village + 0.6 * s.w.swamp) * (1 - s.rain) },
  { sfx: 'wolf_howl', dist: [45, 70], h: [0, 6], vol: 1.6, rate: (s) => s.night * (0.35 * s.w.forest + 0.4 * s.w.mountain) },
  { amb: 'frog', dist: [5, 22], h: [0, 0.5], rate: (s) => 22 * s.w.swamp * (0.5 + 0.5 * s.night) + 7 * s.night * s.water * (s.w.meadow + s.w.forest) },
  { amb: 'bubble', dist: [3, 14], h: [0, 0.2], rate: (s) => 14 * s.w.swamp },
  { amb: 'bell_far', dist: [30, 55], h: [10, 30], rate: (s) => 1.3 * s.w.citadel },
  { amb: 'whisper', dist: [4, 12], h: [1, 3], rate: (s) => 2.5 * s.w.citadel + 1.5 * s.danger },
  { amb: 'hammer_far', dist: [22, 40], h: [1, 2], rate: (s) => 2.2 * s.w.village * s.day * (1 - s.rain) },
  { amb: 'chicken', dist: [8, 22], h: [0.2, 0.6], rate: (s) => 4 * s.w.village * s.day * (1 - 0.7 * s.rain) },
  { amb: 'dog_far', dist: [30, 55], h: [0.5, 1], rate: (s) => 0.7 * s.w.village },
  { amb: 'gull', dist: [15, 45], h: [8, 25], rate: (s) => 5 * s.w.coast * s.day * (1 - 0.6 * s.rain) },
  { amb: 'hawk', dist: [30, 60], h: [20, 45], rate: (s) => 0.9 * s.w.mountain * s.day * (1 - s.rain) },
  { thunder: true, rate: (s) => Math.max(0, s.rain - 0.5) * 5 },
];

/** Ambience state machine. `host` is provided by the engine (see audio.js). */
export class Ambience {
  constructor(host) {
    this.host = host;
    this.k = host.kit;
    this.rng = host.rng;
    this.tgt = null;
    this.cur = { w: {}, day: 1, dawn: 0, night: 0, rain: 0, wind: 0.2, water: 0, danger: 0 };
    for (const b of BIOMES) this.cur.w[b] = 0;
    this.layers = {};
    for (const n of LAYER_NAMES) this.layers[n] = { name: n, node: null, ctl: null, sources: null, last: 0, zeroAt: -1 };
    this.next = new Float64Array(EVENTS.length).fill(-1);
    this.acc = 0;
    this._pos = [0, 0, 0];
    this._evOpts = { pos: this._pos, volume: 1, ref: 12 };
  }

  /** @param {{biome?:string,hour?:number,rain?:number,wind?:number,water?:number,danger?:number}} state */
  set(state) {
    const first = !this.tgt;
    const t = this.tgt || (this.tgt = { biome: 'meadow', hour: 12, rain: 0, wind: 0.2, water: 0, danger: 0 });
    if (state.biome !== undefined) { if (BIOMES.includes(state.biome)) t.biome = state.biome; else this.host.warn('biome:' + state.biome); }
    if (typeof state.hour === 'number') t.hour = ((state.hour % 24) + 24) % 24;
    for (let i = 0; i < SCALARS.length; i++) { const key = SCALARS[i]; if (typeof state[key] === 'number') t[key] = clamp(state[key], 0, 1); }
    if (first) this._approach(1);
  }

  _approach(a) {
    const t = this.tgt, c = this.cur, h = t.hour;
    const day = smooth01((h - 5) / 2) * (1 - smooth01((h - 19.5) / 2));
    const dawn = Math.max(0, 1 - Math.abs(h - 6.2) / 1.6);
    for (const b of BIOMES) c.w[b] += ((b === t.biome ? 1 : 0) - c.w[b]) * a;
    c.day += (day - c.day) * a; c.dawn += (dawn - c.dawn) * a; c.night = 1 - c.day;
    c.rain += (t.rain - c.rain) * a; c.wind += (t.wind - c.wind) * a;
    c.water += (t.water - c.water) * a; c.danger += (t.danger - c.danger) * a;
  }

  _level(name) {
    const s = this.cur, w = s.w;
    switch (name) {
      case 'wind': return 0.09 + 0.36 * s.wind + 0.08 * w.mountain + 0.04 * w.coast + 0.04 * w.ash;
      case 'howl': return w.mountain * (0.1 + 0.4 * s.wind) + Math.max(0, s.wind - 0.6) * 0.5;
      case 'hollow': return w.citadel * 0.5;
      case 'leaves': return (0.6 * w.forest + 0.2 * w.meadow + 0.15 * w.village + 0.2 * w.swamp) * (0.25 + 0.75 * s.wind);
      case 'crickets': return s.night * (0.8 * w.meadow + 0.5 * w.forest + 0.6 * w.village + 0.6 * w.swamp + 0.3 * w.coast) * (1 - 0.8 * s.rain);
      case 'insects': return w.swamp * (0.3 + 0.3 * s.day) * (1 - 0.6 * s.rain);
      case 'surf': return w.coast * (0.32 + 0.4 * s.water);
      case 'brook': return (1 - w.coast) * s.water * 0.8;
      case 'rain': return s.rain > 0.01 ? 1 : 0;
      case 'ash': return w.ash * 0.45;
      case 'murmur': return w.village * s.day * 0.5 * (1 - 0.5 * s.rain);
      case 'danger': return s.danger * 0.55;
      default: return 0;
    }
  }

  _build(L, now) {
    const k = this.k, ctx = k.ctx;
    L.node = ctx.createGain();
    L.node.gain.value = 0;
    L.node.connect(this.host.out);
    L.sources = k.track = [];
    k.cents = 0;
    L.ctl = LAYERS[L.name](k, L.node, now + 0.02, this.rng) || null;
    k.track = null;
    L.last = 0; L.zeroAt = -1;
  }

  _destroy(L) {
    for (const s of L.sources) { try { s.stop(); } catch (e) { /* not started */ } }
    try { L.node.disconnect(); } catch (e) { /* gone */ }
    L.node = null; L.ctl = null; L.sources = null; L.last = 0;
  }

  _surfWave(c) {
    const r = this.rng, t = c.next, P = r.range(6, 10.5), big = r.range(0.7, 1);
    c.g.gain.setValueAtTime(0.15, t);
    c.g.gain.linearRampToValueAtTime(0.85 * big, t + 0.36 * P);
    c.g.gain.linearRampToValueAtTime(big, t + 0.43 * P);
    c.g.gain.linearRampToValueAtTime(0.15, t + P);
    c.lp.frequency.setValueAtTime(380, t);
    c.lp.frequency.exponentialRampToValueAtTime(1700, t + 0.36 * P);
    c.lp.frequency.exponentialRampToValueAtTime(4200 * big, t + 0.45 * P);
    c.lp.frequency.exponentialRampToValueAtTime(380, t + P);
    c.hg.gain.setValueAtTime(0.02, t);
    c.hg.gain.linearRampToValueAtTime(0.03, t + 0.33 * P);
    c.hg.gain.linearRampToValueAtTime(0.45 * big, t + 0.46 * P);
    c.hg.gain.linearRampToValueAtTime(0.2 * big, t + 0.72 * P);
    c.hg.gain.linearRampToValueAtTime(0.02, t + P);
    c.next = t + P;
  }

  /** Called every frame by the engine. */
  update(now, dt) {
    if (!this.tgt) return;
    this.acc += dt;
    const surf = this.layers.surf;
    if (surf.node && now + 1.5 > surf.ctl.next) { if (surf.ctl.next < now) surf.ctl.next = now + 0.02; this._surfWave(surf.ctl); }
    if (this.acc < 0.1) return;
    const step = this.acc;
    this.acc = 0;
    this._approach(1 - Math.exp(-step / 1.4));
    const s = this.cur;

    for (let i = 0; i < LAYER_NAMES.length; i++) {
      const L = this.layers[LAYER_NAMES[i]], lv = this._level(L.name);
      if (lv > 0.004) {
        if (!L.node) this._build(L, now);
        L.zeroAt = -1;
        if (Math.abs(lv - L.last) > 0.008) { L.node.gain.setTargetAtTime(lv, now, 0.45); L.last = lv; }
      } else if (L.node) {
        if (L.last !== 0) { L.node.gain.setTargetAtTime(0, now, 0.45); L.last = 0; L.zeroAt = now; }
        else if (L.zeroAt >= 0 && now - L.zeroAt > 4) this._destroy(L);
      }
    }
    const wind = this.layers.wind;
    if (wind.node) {
      const f = 300 + 650 * s.wind + 150 * s.w.mountain;
      if (Math.abs(f - (wind.ctl.f || 0)) > 8) { wind.ctl.f = f; for (const bp of wind.ctl.bps) bp.frequency.setTargetAtTime(f, now, 0.8); }
    }
    const rain = this.layers.rain;
    if (rain.node && Math.abs(s.rain - (rain.ctl.r || 0)) > 0.008) {
      const r = rain.ctl.r = s.rain;
      rain.ctl.hiss.gain.setTargetAtTime(Math.pow(r, 1.5) * 0.2, now, 0.4);
      rain.ctl.body.gain.setTargetAtTime(r * r * 0.4, now, 0.4);
      rain.ctl.drops.gain.setTargetAtTime(Math.min(1, r * 3) * 0.5 * (1 - 0.4 * r), now, 0.4);
    }

    for (let i = 0; i < EVENTS.length; i++) {
      const ev = EVENTS[i], rate = ev.rate(s);
      if (rate < 0.02) { this.next[i] = -1; continue; }
      const mean = 60 / rate;
      if (this.next[i] < 0) this.next[i] = now + this.rng.exp(mean) * 0.5 + 0.3;
      else if (this.next[i] > now + mean * 3) this.next[i] = now + mean * 3;
      if (now >= this.next[i]) {
        this.next[i] = now + Math.max(0.35, this.rng.exp(mean));
        this._fire(ev);
      }
    }
  }

  _fire(ev) {
    const r = this.rng, host = this.host;
    if (ev.thunder) { host.thunder(r.range(0.45, 1)); return; }
    const az = r.next() * TAU, d = r.range(ev.dist[0], ev.dist[1]), lp = host.lpos, p = this._pos;
    p[0] = lp[0] + Math.cos(az) * d; p[1] = lp[1] + r.range(ev.h[0], ev.h[1]); p[2] = lp[2] + Math.sin(az) * d;
    this._evOpts.volume = (ev.vol || 1) * r.range(0.6, 1);
    if (ev.sfx) { this._evOpts.ref = 4; host.spawnSfx(ev.sfx, this._evOpts); }
    else { this._evOpts.ref = 12; host.spawn(AMB[ev.amb], this._evOpts); }
  }

  dispose() {
    for (const n of LAYER_NAMES) if (this.layers[n].node) this._destroy(this.layers[n]);
  }
}

export const AMB_NAMES = Object.keys(AMB);
