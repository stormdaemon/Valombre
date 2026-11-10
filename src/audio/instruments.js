/**
 * VALOMBRE audio - synthesized instruments for the generative music.
 *
 * Every instrument plays into a channel strip of a music player (`strip(player, name)`), which
 * owns the level, pan, tone shaping and reverb send. Notes are fully scheduled when created and
 * free themselves when they end.
 */
import { mtof } from './core.js';
import { BELL, BELL_G, BELL_D, BAR } from './recipes.js';

/** level, reverb send, pan, optional EQ chain [type, freq, Q, gainDb]. */
const STRIPS = {
  harp: { level: 0.5, send: 0.35, pan: -0.2 },
  lute: { level: 0.55, send: 0.22, pan: 0.2, eq: [['peaking', 220, 1.2, 4], ['peaking', 900, 1.5, 3], ['lowpass', 5200, 0.6, 0]] },
  strings: { level: 0.16, send: 0.45, pan: -0.1, eq: [['lowpass', 2800, 0.6, 0], ['peaking', 320, 1, 3], ['highpass', 70, 0.6, 0]], ens: [5.3, 0.00018] },
  stacc: { level: 0.32, send: 0.25, pan: -0.15, eq: [['lowpass', 4200, 0.7, 0], ['peaking', 1700, 1.2, 4], ['highpass', 80, 0.6, 0]] },
  flute: { level: 0.3, send: 0.45, pan: 0.25 },
  choir: { level: 0.22, send: 0.7, pan: 0, ens: [5.0, 0.00022] },
  drum: { level: 0.7, send: 0.22, pan: 0 },
  bell: { level: 0.3, send: 0.6, pan: 0.1 },
  drone: { level: 0.12, send: 0.25, pan: 0, eq: [['lowpass', 2400, 0.6, 0], ['peaking', 900, 2, 5], ['highpass', 60, 0.6, 0]] },
  brass: { level: 0.15, send: 0.5, pan: 0.15, eq: [['highpass', 60, 0.6, 0]] },
};

const CHOIR_F = {
  aah: [[700, 5, 1], [1150, 7, 0.6], [2700, 9, 0.3], [3400, 9, 0.15]],
  ooh: [[380, 5, 1], [800, 7, 0.4], [2600, 9, 0.08]],
};

export class Instruments {
  /** @param {import('./core.js').Kit} kit a Kit whose `track` stays null */
  constructor(kit) { this.k = kit; this.ctx = kit.ctx; }

  /**
   * Returns (creating on first use) the named channel strip of player `p`.
   * `p` must expose { dry:GainNode, rev:GainNode, strips:{} }.
   */
  strip(p, name) {
    let s = p.strips[name];
    if (s) return s;
    const k = this.k, c = STRIPS[name], t = this.ctx.currentTime;
    const input = k.gain(1), level = k.gain(c.level), pan = k.pan(c.pan), send = k.gain(c.send);
    s = p.strips[name] = { in: input, level, lfos: [], nodes: [level, pan, send] };
    let node = input;
    if (name === 'choir') {
      const sum = k.gain(1);
      for (const vowel of ['aah', 'ooh']) {
        const vin = s[vowel] = k.gain(1);
        for (const [f, q, g] of CHOIR_F[vowel]) {
          const bp = k.bq('bandpass', f, q), gg = k.gain(g * 2.5);
          vin.connect(bp); bp.connect(gg); gg.connect(sum);
        }
        const lp = k.bq('lowpass', 480, 0.5), dg = k.gain(0.22);
        vin.connect(lp); lp.connect(dg); dg.connect(sum);
      }
      node = sum;
    }
    if (c.eq) for (const [type, f, q, g] of c.eq) { const b = k.bq(type, f, q, g); node.connect(b); node = b; }
    if (c.ens) {
      // Ensemble: a slowly modulated short delay mixed with the dry signal (vibrato + chorus).
      const d = k.delay(0.014, 0.05), l = k.osc('sine', c.ens[0], t), lg = k.gain(c.ens[1]);
      const n = k.lfoNoise(1.3, t), ng = k.gain(c.ens[1] * 2), dry = k.gain(0.6), wet = k.gain(0.7);
      l.connect(lg); lg.connect(d.delayTime); n.connect(ng); ng.connect(d.delayTime);
      node.connect(dry); node.connect(d); d.connect(wet); dry.connect(level); wet.connect(level);
      s.lfos.push(l, n);
    } else node.connect(level);
    level.connect(pan); pan.connect(p.dry); pan.connect(send); send.connect(p.rev);
    return s;
  }

  /** Runs `build(dest)` into a private gain that is released when its first source ends. */
  _hit(s, build) {
    const k = this.k, h = k.gain(1), arr = k.track = [];
    build(h);
    k.track = null;
    h.connect(s.in);
    if (arr.length) k.autoFree(arr[0], h);
  }

  /** Plucked string (Karplus-Strong). o: { type:'harp'|'lute', dur, cents } */
  pluck(s, t, midi, vel, o = {}) {
    const k = this.k;
    const e = k.pluck(s.in, { t, midi, vol: vel, type: o.type || 'harp', dur: o.dur, cents: o.cents, lp: 1100 + vel * 6500 });
    k.autoFree(e.src, e.out);
  }

  /** Bowed strings / viol pad. o: { a, r, solo, cents } */
  strings(s, t, midi, dur, vel, o = {}) {
    const k = this.k, f = mtof(midi), a = o.a ?? 0.35, r = o.r ?? 0.6, hold = Math.max(a, dur), end = t + hold + r + 0.05;
    const g = k.gain(0);
    k.ar(g.gain, t, vel, a, hold - a, r);
    let last = null;
    if (o.solo) {
      const vib = k.osc('sine', 5.2, t, end), vg = k.gain(0);
      vg.gain.setValueAtTime(0, t + 0.15); vg.gain.linearRampToValueAtTime(11, t + 0.5);
      vib.connect(vg);
      for (const dt of [-3, 3]) { last = k.osc('sawtooth', f, t, end, dt + (o.cents || 0)); vg.connect(last.detune); last.connect(g); }
    } else {
      for (const dt of [-8, 7]) { last = k.osc('sawtooth', f, t, end, dt + (o.cents || 0)); last.connect(g); }
    }
    g.connect(s.in);
    k.autoFree(last, g);
  }

  /** Short bowed note (spiccato) for ostinatos. o: { dur } */
  stacc(s, t, midi, vel, o = {}) {
    const k = this.k, f = mtof(midi), d = o.dur ?? 0.16, g = k.gain(0);
    k.perc(g.gain, t, vel, 0.012, d);
    let last = null;
    for (const dt of [-8, 7]) { last = k.osc('sawtooth', f, t, t + d + 0.06, dt); last.connect(g); }
    g.connect(s.in);
    k.autoFree(last, g);
  }

  /** Recorder / flute: triangle body, breath noise with chiff, delayed vibrato. o: { a, r, vib } */
  flute(s, t, midi, dur, vel, o = {}) {
    const k = this.k, f = mtof(midi), a = o.a ?? 0.05, r = o.r ?? 0.09, hold = Math.max(a + 0.1, dur), end = t + hold + r + 0.05;
    const g = k.gain(0), ng = k.gain(0);
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vel, t + a);
    g.gain.linearRampToValueAtTime(vel * 0.85, t + a + 0.1);
    g.gain.setValueAtTime(vel * 0.85, t + hold);
    g.gain.linearRampToValueAtTime(0, t + hold + r);
    const o1 = k.osc('triangle', f, t, end), o2 = k.osc('sine', f * 2, t, end), g2 = k.gain(0.2);
    const vib = k.osc('sine', 4.8, t, end), vg = k.gain(0);
    vg.gain.setValueAtTime(0, t + 0.18); vg.gain.linearRampToValueAtTime(o.vib ?? 9, t + 0.55);
    vib.connect(vg); vg.connect(o1.detune); vg.connect(o2.detune);
    const n = k.noise('pink', t, end), bp = k.bq('bandpass', Math.min(f * 2, 6000), 1.4);
    ng.gain.setValueAtTime(0, t);
    ng.gain.linearRampToValueAtTime(vel * 0.6, t + 0.015);
    ng.gain.linearRampToValueAtTime(vel * 0.13, t + 0.09);
    ng.gain.setValueAtTime(vel * 0.13, t + hold);
    ng.gain.linearRampToValueAtTime(0, t + hold + r);
    o1.connect(g); o2.connect(g2); g2.connect(g); n.connect(bp); bp.connect(ng);
    g.connect(s.in); ng.connect(s.in);
    o1.onended = () => { try { g.disconnect(); ng.disconnect(); } catch (e) { /* gone */ } };
  }

  /** Choir voice group into the strip's formant bank. o: { vowel:'aah'|'ooh', a, r } */
  choir(s, t, midi, dur, vel, o = {}) {
    const k = this.k, f = mtof(midi), a = o.a ?? 0.5, r = o.r ?? 0.9, hold = Math.max(a, dur), end = t + hold + r + 0.05;
    const g = k.gain(0);
    k.ar(g.gain, t, vel, a, hold - a, r);
    let last = null;
    for (const dt of [-11, 0, 9]) { last = k.osc('glottal', f, t, end, dt + k.rng.range(-3, 3)); last.connect(g); }
    g.connect(o.vowel === 'ooh' ? s.ooh : s.aah);
    k.autoFree(last, g);
  }

  /** Membrane drums: 'war' | 'taiko' | 'dum' (frame drum centre) | 'tak' (frame drum edge). */
  drum(s, t, kind, vel) {
    const k = this.k, r = k.rng;
    this._hit(s, (h) => {
      if (kind === 'war') {
        const f = 58 * r.range(0.98, 1.02);
        k.tone(h, { f: f * 2.3, f1: f, glide: 0.07, t, dur: 0.75, vol: vel });
        k.tone(h, { type: 'triangle', f: f * 3.2, f1: f * 1.5, glide: 0.05, t, dur: 0.22, vol: vel * 0.4 });
        k.nz(h, { kind: 'pink', t, dur: 0.07, type: 'lowpass', f: 900, vol: vel * 0.8 });
        k.nz(h, { t, dur: 0.012, f: 2400, q: 1, vol: vel * 0.3, a: 0.001 });
      } else if (kind === 'taiko') {
        const f = 92 * r.range(0.98, 1.02);
        k.tone(h, { f: f * 2.0, f1: f, glide: 0.04, t, dur: 0.42, vol: vel });
        k.tone(h, { type: 'triangle', f: f * 1.59, t, dur: 0.15, vol: vel * 0.3 });
        k.nz(h, { kind: 'pink', t, dur: 0.05, type: 'lowpass', f: 1500, vol: vel * 0.7 });
        k.nz(h, { t, dur: 0.015, f: 1900, q: 1.2, vol: vel * 0.5, a: 0.001 });
      } else if (kind === 'dum') {
        const f = 128 * r.range(0.97, 1.03);
        k.tone(h, { f: f * 1.6, f1: f, glide: 0.03, t, dur: 0.28, vol: vel });
        k.tone(h, { f: f * 1.59, t, dur: 0.1, vol: vel * 0.3 });
        k.tone(h, { f: f * 2.14, t, dur: 0.07, vol: vel * 0.2 });
        k.nz(h, { kind: 'pink', t, dur: 0.03, type: 'lowpass', f: 1800, vol: vel * 0.5 });
      } else {
        k.tone(h, { f: 410, f1: 380, t, dur: 0.06, vol: vel * 0.35 });
        k.nz(h, { t, dur: 0.04, f: r.range(1700, 2000), q: 2, vol: vel * 0.9, a: 0.001 });
        k.nz(h, { t, dur: 0.02, type: 'highpass', f: 4000, vol: vel * 0.2 });
      }
    });
  }

  /** Bells: kind 'church' | 'chime' | 'dull'. o: { kind, decay } */
  bell(s, t, midi, vel, o = {}) {
    const k = this.k, f = mtof(midi), kind = o.kind || 'church';
    this._hit(s, (h) => {
      if (kind === 'church') k.modal(h, { t, f, ratios: BELL, gains: BELL_G, decays: BELL_D, decay: o.decay ?? 3, vol: vel * 0.5, a: 0.003 });
      else if (kind === 'chime') k.modal(h, { t, f, ratios: BAR, gains: [1, 0.3, 0.12, 0.04], decays: [1, 0.5, 0.25, 0.12], decay: o.decay ?? 1.8, vol: vel * 0.6 });
      else k.modal(h, { t, f, ratios: [1, 1.34, 2.41, 3.07], gains: [1, 0.6, 0.3, 0.15], decays: [1, 0.7, 0.4, 0.2], decay: o.decay ?? 1.6, vol: vel * 0.5, jit: 0.02 });
    });
  }

  /** Hurdy-gurdy-like drone (root + fifth). o: { a, r, fifth, detune } */
  drone(s, t, midi, dur, vel, o = {}) {
    const k = this.k, a = o.a ?? 1.5, r = o.r ?? 2.5, hold = Math.max(a, dur), end = t + hold + r + 0.05, g = k.gain(0);
    const dt = o.detune ?? 5;
    k.ar(g.gain, t, vel, a, hold - a, r);
    let last = null;
    for (const n of (o.fifth === false ? [0] : [0, 7])) {
      const og = k.gain(n ? 0.5 : 1);
      for (const c of [-dt, dt]) { last = k.osc('reed', mtof(midi + n), t, end, c); last.connect(og); }
      og.connect(g);
    }
    const l = k.osc('sine', 1.3, t, end), lg = k.gain(vel * 0.08);
    l.connect(lg); lg.connect(g.gain);
    g.connect(s.in);
    k.autoFree(last, g);
  }

  /** Low brass: saws through a low-pass that opens with the swell. o: { a, r, bright } */
  brass(s, t, midi, dur, vel, o = {}) {
    const k = this.k, f = mtof(midi), a = o.a ?? 0.12, r = o.r ?? 0.25, hold = Math.max(a, dur), end = t + hold + r + 0.05;
    const lp = k.bq('lowpass', f * 1.2, 1.2), g = k.gain(0), top = Math.min(6000, f * (2.5 + 7 * vel * (o.bright ?? 1)));
    lp.frequency.setValueAtTime(f * 1.2, t);
    lp.frequency.linearRampToValueAtTime(top, t + a);
    lp.frequency.setValueAtTime(top, t + hold);
    lp.frequency.linearRampToValueAtTime(f * 1.5, t + hold + r);
    k.ar(g.gain, t, vel, a, hold - a, r);
    let last = null;
    for (const dt of [-6, 5]) { last = k.osc('sawtooth', f, t, end, dt); last.connect(lp); }
    lp.connect(g); g.connect(s.in);
    k.autoFree(last, g);
  }

  /** Stops the persistent modulators of a player's strips and disconnects them. */
  release(p) {
    for (const name in p.strips) {
      const s = p.strips[name];
      for (const l of s.lfos) { try { l.stop(); } catch (e) { /* stopped */ } }
      for (const n of s.nodes) { try { n.disconnect(); } catch (e) { /* gone */ } }
    }
    p.strips = {};
  }
}
