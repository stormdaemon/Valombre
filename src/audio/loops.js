/**
 * VALOMBRE audio - looping emitters (fire, brazier, torch, crystal hum, waterfall, boss aura, forge).
 * Recipe signature: fn(k, o, t, r). Sources are started without a stop time; the engine keeps
 * the list of tracked sources (k.track) to detune and stop them.
 */
import { define } from './recipes.js';

/** @type {Record<string, object>} */
export const LOOPS = Object.create(null);
const def = (name, rev, send, gain, fn) => define(LOOPS, name, 'loop', 5, rev, send, gain, fn);

/** Random slow modulation of an AudioParam around its current value. */
function wobble(k, param, t, rate, depth) {
  const l = k.lfoNoise(rate, t), g = k.gain(depth);
  l.connect(g); g.connect(param);
}

/** size: 0 torch, 1 camp fire, 2 brazier. */
function fire(k, o, t, r, size) {
  const cr = k.buf(k.res.baked('crackle'), t, { loop: true, rate: r.range(0.9, 1.1) * (size === 0 ? 1.3 : size === 2 ? 0.85 : 1) });
  const crHp = k.bq('highpass', [1400, 900, 500][size], 0.7), crG = k.gain([0.2, 0.55, 0.7][size]);
  cr.connect(crHp); crHp.connect(crG); crG.connect(o);
  const roarN = k.noise('brown', t), lp = k.bq('lowpass', [650, 420, 300][size], 0.8), rg = k.gain([0.35, 0.45, 0.8][size]);
  roarN.connect(lp); lp.connect(rg); rg.connect(o);
  wobble(k, rg.gain, t, size === 0 ? 11 : 5, [0.25, 0.2, 0.3][size]);
  wobble(k, lp.frequency, t, 3, [250, 120, 90][size]);
  const hiss = k.noise('pink', t), bp = k.bq('bandpass', [2600, 2000, 1500][size], 0.7), hg = k.gain([0.12, 0.1, 0.14][size]);
  hiss.connect(bp); bp.connect(hg); hg.connect(o);
  wobble(k, hg.gain, t, size === 0 ? 14 : 7, [0.1, 0.06, 0.08][size]);
}

def('fire', 'room', 0.05, 0.9, (k, o, t, r) => fire(k, o, t, r, 1));
def('brazier', 'room', 0.08, 0.65, (k, o, t, r) => fire(k, o, t, r, 2));
def('torch', 'room', 0.04, 0.9, (k, o, t, r) => fire(k, o, t, r, 0));

def('crystal_hum', 'hall', 0.35, 0.45, (k, o, t, r) => {
  const base = r.pick([196, 220, 246.9]), lp = k.bq('lowpass', 5000, 0.5);
  lp.connect(o);
  const parts = [[1, 0.2], [2.005, 0.12], [3.01, 0.07], [4.02, 0.04], [5.4, 0.03], [8.03, 0.015]];
  for (const [ratio, amp] of parts) {
    const osc = k.osc('sine', base * ratio, t, undefined, r.range(-6, 6)), g = k.gain(amp);
    const trem = k.osc('sine', r.range(0.08, 0.45), t), tg = k.gain(amp * 0.6);
    trem.connect(tg); tg.connect(g.gain);
    osc.connect(g); g.connect(lp);
  }
  const sh = k.noise('white', t), bp = k.bq('bandpass', base * 16, 30), sg = k.gain(0.12);
  sh.connect(bp); bp.connect(sg); sg.connect(lp);
  wobble(k, sg.gain, t, 2, 0.1);
});

def('waterfall', 'room', 0.05, 0.8, (k, o, t, r) => {
  const hi = k.noise('white', t), hl = k.bq('lowpass', 6500, 0.5), hh = k.bq('highpass', 900, 0.5), hg = k.gain(0.3);
  hi.connect(hl); hl.connect(hh); hh.connect(hg); hg.connect(o);
  const mid = k.noise('pink', t), mb = k.bq('bandpass', 700, 0.4), mg = k.gain(0.6);
  mid.connect(mb); mb.connect(mg); mg.connect(o);
  wobble(k, mg.gain, t, 1.5, 0.1);
  const low = k.noise('brown', t), ll = k.bq('lowpass', 180, 0.7), lg = k.gain(0.7);
  low.connect(ll); ll.connect(lg); lg.connect(o);
  wobble(k, lg.gain, t, 0.8, 0.15);
});

def('boss_aura', 'hall', 0.4, 0.45, (k, o, t, r) => {
  const base = r.pick([41.2, 43.65, 38.9]), lp = k.bq('lowpass', 170, 4), pulse = k.gain(0.75);
  pulse.connect(o);
  const lfo = k.osc('sine', r.range(0.55, 0.8), t), lfg = k.gain(0.25);
  lfo.connect(lfg); lfg.connect(pulse.gain);
  const cut = k.osc('sine', 0.31, t), cg = k.gain(70);
  cut.connect(cg); cg.connect(lp.frequency);
  for (const dt of [-9, 9]) { const s = k.osc('sawtooth', base, t, undefined, dt), g = k.gain(0.5); s.connect(g); g.connect(lp); }
  const tri = k.osc('sine', base * 2.828, t), tg = k.gain(0.12);
  tri.connect(tg); tg.connect(pulse);
  const hi = k.osc('sine', base * 12.1, t), hgn = k.gain(0.012);
  hi.connect(hgn); hgn.connect(pulse);
  wobble(k, hgn.gain, t, 1.2, 0.01);
  lp.connect(pulse);
  const wn = k.noise('pink', t), wb = k.bq('bandpass', 1800, 3), wg = k.gain(0.1);
  wn.connect(wb); wb.connect(wg); wg.connect(pulse);
  wobble(k, wb.frequency, t, 2, 800);
  wobble(k, wg.gain, t, 1.5, 0.08);
});

def('forge', 'room', 0.08, 0.6, (k, o, t, r) => {
  fire(k, o, t, r, 2);
  // Bellows: slow breathing roar.
  const bn = k.noise('pink', t), bb = k.bq('bandpass', 520, 0.8), bg = k.gain(0.25);
  const br = k.osc('sine', r.range(0.22, 0.3), t), brg = k.gain(0.25);
  br.connect(brg); brg.connect(bg.gain);
  const bf = k.gain(260);
  br.connect(bf); bf.connect(bb.frequency);
  bn.connect(bb); bb.connect(bg); bg.connect(o);
  const em = k.buf(k.res.baked('embers'), t, { loop: true, rate: 1.4 }), eh = k.bq('highpass', 1800, 0.7), eg = k.gain(0.5);
  em.connect(eh); eh.connect(eg); eg.connect(o);
});

export const LOOP_NAMES = Object.keys(LOOPS);
