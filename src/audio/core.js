/**
 * VALOMBRE audio - core synthesis toolkit.
 *
 * Everything here works on any BaseAudioContext (realtime or offline): seeded RNG, baked
 * buffers (noise, reverb impulses, Karplus-Strong plucks, crackle, crickets, brook, crowd
 * murmur, rain drops), distortion curves, and `Kit`, a small node-building helper used by
 * every sound recipe.
 */

export const TAU = Math.PI * 2;
export function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
export function lerp(a, b, t) { return a + (b - a) * t; }
export function mtof(m) { return 440 * Math.pow(2, (m - 69) / 12); }
export function smooth01(x) { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); }

/** Small seeded PRNG (mulberry32) with a few convenience distributions. */
export class Rng {
  constructor(seed) { this.s = (seed >>> 0) || 0x9e3779b9; }
  next() {
    this.s = (this.s + 0x6D2B79F5) | 0;
    let t = this.s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  range(a, b) { return a + (b - a) * this.next(); }
  int(a, b) { return a + Math.floor(this.next() * (b - a + 1)); }
  pick(arr) { return arr[Math.floor(this.next() * arr.length)]; }
  chance(p) { return this.next() < p; }
  /** v multiplied by a random factor in [1-amt, 1+amt]. */
  jit(v, amt) { return v * (1 + (this.next() * 2 - 1) * amt); }
  /** Exponentially distributed value with the given mean. */
  exp(mean) { return -Math.log(1 - this.next() * 0.9999) * mean; }
}

// ---------------------------------------------------------------------------------------
// Baked buffers
// ---------------------------------------------------------------------------------------

function normalize(arrs, peak) {
  let m = 0;
  for (const d of arrs) for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > m) m = a; }
  if (m > 0) { const k = peak / m; for (const d of arrs) for (let i = 0; i < d.length; i++) d[i] *= k; }
}

/** Loopable mono noise buffer: 'white' | 'pink' | 'brown'. */
export function makeNoise(ctx, kind, seconds, rng) {
  const sr = ctx.sampleRate, n = Math.floor(seconds * sr), fade = Math.floor(0.06 * sr);
  const tmp = new Float32Array(n + fade);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, last = 0;
  for (let i = 0; i < tmp.length; i++) {
    const w = rng.next() * 2 - 1;
    if (kind === 'white') tmp[i] = w;
    else if (kind === 'pink') {
      b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759;
      b2 = 0.96900 * b2 + w * 0.1538520; b3 = 0.86650 * b3 + w * 0.3104856;
      b4 = 0.55000 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.0168980;
      tmp[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
      b6 = w * 0.115926;
    } else { last = (last + 0.02 * w) / 1.02; tmp[i] = last * 3.5; }
  }
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    if (i < fade && kind !== 'white') {
      const x = i / fade;
      out[i] = tmp[i] * Math.sqrt(x) + tmp[n + i] * Math.sqrt(1 - x);
    } else out[i] = tmp[i];
  }
  if (kind !== 'white') normalize([out], 0.95);
  const buf = ctx.createBuffer(1, n, sr);
  buf.copyToChannel(out, 0);
  return buf;
}

/**
 * Synthetic stereo reverb impulse: filtered noise with exponential decay, high-frequency
 * damping over time, diffuse build-up and a few early reflections.
 */
export function makeImpulse(ctx, rng, o) {
  const sr = ctx.sampleRate, n = Math.floor(o.seconds * sr), buf = ctx.createBuffer(2, n, sr);
  const pre = Math.floor((o.predelay || 0) * sr);
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    let lp = 0;
    for (let i = pre; i < n; i++) {
      const tt = (i - pre) / sr;
      const env = Math.exp(-6.908 * tt / o.t60) * (1 - Math.exp(-tt / (o.build || 0.01)));
      const fc = o.dark + (o.bright - o.dark) * Math.exp(-tt * o.damp);
      const a = 1 - Math.exp(-TAU * fc / sr);
      lp += a * ((rng.next() * 2 - 1) - lp);
      d[i] = lp * env;
    }
    for (let e = 0; e < (o.early || 0); e++) {
      const ti = pre + Math.floor((0.003 + rng.next() * (o.earlySpan || 0.06)) * sr);
      if (ti < n) d[ti] += (rng.next() < 0.5 ? -1 : 1) * (0.5 - e * 0.03) * (o.earlyGain || 0.5);
    }
    const fo = Math.floor(0.05 * sr);
    for (let i = 0; i < fo; i++) d[n - 1 - i] *= i / fo;
  }
  return buf;
}

/** Wave-shaper transfer curves. */
export function makeCurve(kind, k) {
  const n = 2049, c = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const x = (i / (n - 1)) * 2 - 1, ax = Math.abs(x), s = x < 0 ? -1 : 1;
    if (kind === 'soft') c[i] = Math.tanh(k * x) / Math.tanh(k);
    else if (kind === 'fold') c[i] = Math.sin(x * k * Math.PI * 0.5);
    else if (kind === 'limit') {
      // Transparent below the knee, then a smooth saturation that never exceeds 0.93.
      const knee = 0.62, top = 0.93;
      c[i] = ax <= knee ? x : s * (knee + (top - knee) * Math.tanh((ax - knee) / (top - knee)));
    } else c[i] = x;
  }
  return c;
}

/**
 * Karplus-Strong plucked string rendered into a buffer.
 * Returns { buffer, rate } where `rate` corrects the integer loop length to the exact pitch.
 */
export function bakePluck(ctx, rng, freq, o) {
  const sr = ctx.sampleRate;
  const b = o.blend;                                   // 0..0.5, loop filter blend (damping of highs)
  const N = Math.max(2, Math.round(sr / freq - b));
  const period = (N + b) / sr;
  const t60 = clamp(o.t60 * Math.pow(220 / freq, 0.35), 0.35, o.t60 * 1.7);
  const g = Math.exp(-6.908 * period / t60);
  const len = Math.floor(Math.min(o.maxSeconds, t60 * 1.15 + 0.2) * sr);
  const out = new Float32Array(len);
  // Excitation: one period of low-passed noise, comb-filtered by the pick position.
  const exc = new Float32Array(N);
  let lp = 0, mean = 0;
  const a = clamp(o.bright, 0.05, 1);
  for (let i = 0; i < N; i++) { lp += a * ((rng.next() * 2 - 1) - lp); exc[i] = lp; }
  for (let i = 0; i < N; i++) { lp += a * (exc[i] - lp); exc[i] = lp; }   // second pass smooths the loop seam
  const pk = Math.max(1, Math.round(N * o.pick));
  for (let i = 0; i < N; i++) { out[i] = exc[i] - exc[(i + N - pk) % N]; mean += out[i]; }
  mean /= N;
  let m = 0;
  for (let i = 0; i < N; i++) { out[i] -= mean; const v = Math.abs(out[i]); if (v > m) m = v; }
  const k = m > 0 ? 0.9 / m : 1;
  for (let i = 0; i < N; i++) out[i] *= k;
  for (let i = N; i < len; i++) out[i] = g * ((1 - b) * out[i - N] + b * (i - N - 1 >= 0 ? out[i - N - 1] : 0));
  const fo = Math.floor(0.04 * sr);
  for (let i = 0; i < fo && i < len; i++) out[len - 1 - i] *= i / fo;
  const at = Math.min(len, Math.floor(0.0015 * sr));
  for (let i = 0; i < at; i++) out[i] *= i / at;
  const buf = ctx.createBuffer(1, len, sr);
  buf.copyToChannel(out, 0);
  return { buffer: buf, rate: freq * period };
}

/** Loopable crackle (fire / embers): random filtered pops with heavy-tailed amplitudes. */
export function bakeCrackle(ctx, rng, seconds, perSec) {
  const sr = ctx.sampleRate, n = Math.floor(seconds * sr), d = new Float32Array(n);
  const count = Math.floor(seconds * perSec);
  for (let c = 0; c < count; c++) {
    const pos = Math.floor(rng.next() * n);
    const amp = Math.pow(rng.next(), 3.2) * 0.95 + 0.04;
    const len = Math.floor(sr * (0.0008 + rng.next() * 0.009 * (0.3 + amp)));
    const col = 0.12 + rng.next() * 0.85;
    let y = 0;
    for (let i = 0; i < len; i++) {
      y += col * ((rng.next() * 2 - 1) - y);
      d[(pos + i) % n] += y * Math.exp(-5 * i / len) * amp;
    }
  }
  normalize([d], 0.9);
  const buf = ctx.createBuffer(1, n, sr);
  buf.copyToChannel(d, 0);
  return buf;
}

/** Loopable stereo night crickets. */
export function bakeCrickets(ctx, rng, seconds) {
  const sr = ctx.sampleRate, n = Math.floor(seconds * sr), L = new Float32Array(n), R = new Float32Array(n);
  for (let c = 0; c < 6; c++) {
    const f = 3700 + rng.next() * 1500, pan = rng.next(), amp = 0.25 + rng.next() * 0.75;
    const trill = c === 5;
    const pulseRate = trill ? 38 + rng.next() * 8 : 48 + rng.next() * 16;
    const pulses = trill ? 0 : 2 + Math.floor(rng.next() * 3);
    const period = trill ? seconds : 0.42 + rng.next() * 0.55;
    const pl = Math.floor(sr * (trill ? 0.012 : 0.011));
    let ts = rng.next() * 0.4;
    while (ts < seconds - 0.2) {
      const np = trill ? Math.floor((seconds - 0.3) * pulseRate) : pulses;
      for (let p = 0; p < np; p++) {
        const st = Math.floor((ts + p / pulseRate) * sr);
        const pa = amp * (trill ? 0.35 : 1) * (0.8 + 0.2 * rng.next());
        for (let i = 0; i < pl; i++) {
          const idx = st + i;
          if (idx >= n) break;
          const e = Math.sin(Math.PI * i / pl);
          const s = Math.sin(TAU * f * i / sr) * e * e * pa;
          L[idx] += s * (1 - pan); R[idx] += s * pan;
        }
      }
      if (trill) break;
      ts += period * (0.92 + rng.next() * 0.16);
    }
  }
  normalize([L, R], 0.8);
  const buf = ctx.createBuffer(2, n, sr);
  buf.copyToChannel(L, 0); buf.copyToChannel(R, 1);
  return buf;
}

/** Loopable stereo babbling brook: a dense cloud of tiny rising/falling sine droplets. */
export function bakeBrook(ctx, rng, seconds) {
  const sr = ctx.sampleRate, n = Math.floor(seconds * sr), L = new Float32Array(n), R = new Float32Array(n);
  const count = Math.floor(seconds * 240);
  for (let c = 0; c < count; c++) {
    const pos = Math.floor(rng.next() * n);
    const f0 = 450 * Math.pow(2, rng.next() * 2.7), rise = 1 + (rng.next() - 0.25) * 0.8;
    const len = Math.floor(sr * (0.005 + rng.next() * 0.028));
    const amp = (0.15 + Math.pow(rng.next(), 2)) * Math.pow(600 / f0, 0.35), pan = rng.next();
    let ph = 0;
    for (let i = 0; i < len; i++) {
      const x = i / len;
      ph += TAU * f0 * (1 + (rise - 1) * x) / sr;
      const e = x < 0.12 ? x / 0.12 : Math.exp(-4.5 * (x - 0.12));
      const s = Math.sin(ph) * e * amp, idx = (pos + i) % n;
      L[idx] += s * (1 - pan); R[idx] += s * pan;
    }
  }
  let yl = 0, yr = 0;
  for (let i = 0; i < n; i++) {
    yl += 0.18 * ((rng.next() * 2 - 1) - yl); yr += 0.18 * ((rng.next() * 2 - 1) - yr);
    L[i] += yl * 0.35; R[i] += yr * 0.35;
  }
  normalize([L, R], 0.85);
  const buf = ctx.createBuffer(2, n, sr);
  buf.copyToChannel(L, 0); buf.copyToChannel(R, 1);
  return buf;
}

/** Loopable crowd murmur: several formant "talkers" speaking nonsense syllables. */
export function bakeMurmur(ctx, rng, seconds) {
  const sr = ctx.sampleRate, n = Math.floor(seconds * sr), d = new Float32Array(n);
  for (let v = 0; v < 7; v++) {
    const base = 95 + rng.next() * 120, amp = 0.4 + rng.next() * 0.6;
    let pos = Math.floor(rng.next() * n), written = 0, ph = 0;
    let x1 = 0, x2 = 0, y1a = 0, y2a = 0, y1b = 0, y2b = 0;
    while (written < n) {
      const syl = Math.floor(sr * (0.11 + rng.next() * 0.2));
      const gap = Math.floor(sr * (rng.next() < 0.22 ? 0.3 + rng.next() * 0.8 : 0.02 + rng.next() * 0.07));
      const f0 = base * (0.88 + rng.next() * 0.38), f1 = f0 * (0.92 + rng.next() * 0.16);
      const F1 = 300 + rng.next() * 520, F2 = 900 + rng.next() * 1300;
      const wa = TAU * F1 / sr, aa = Math.sin(wa) / 12, a0a = 1 + aa, ca = -2 * Math.cos(wa) / a0a, da = (1 - aa) / a0a, ga = aa / a0a;
      const wb = TAU * F2 / sr, ab = Math.sin(wb) / 16, a0b = 1 + ab, cb = -2 * Math.cos(wb) / a0b, db = (1 - ab) / a0b, gb = ab / a0b;
      for (let i = 0; i < syl; i++) {
        const x = i / syl;
        ph += (f0 + (f1 - f0) * x) / sr; if (ph >= 1) ph -= 1;
        const src = (ph * 2 - 1) * Math.pow(Math.sin(Math.PI * x), 0.6);
        const ya = ga * (src - x2) - ca * y1a - da * y2a;
        const yb = gb * (src - x2) - cb * y1b - db * y2b;
        x2 = x1; x1 = src; y2a = y1a; y1a = ya; y2b = y1b; y1b = yb;
        d[(pos + i) % n] += (ya + yb * 0.5) * amp;
      }
      pos = (pos + syl + gap) % n; written += syl + gap;
    }
  }
  normalize([d], 0.85);
  const buf = ctx.createBuffer(1, n, sr);
  buf.copyToChannel(d, 0);
  return buf;
}

/** Loopable stereo rain drop patter (individual ticks; the hiss is a separate noise layer). */
export function bakeRainDrops(ctx, rng, seconds) {
  const sr = ctx.sampleRate, n = Math.floor(seconds * sr), L = new Float32Array(n), R = new Float32Array(n);
  const count = Math.floor(seconds * 420);
  for (let c = 0; c < count; c++) {
    const pos = Math.floor(rng.next() * n), amp = Math.pow(rng.next(), 4) * 0.95 + 0.05, pan = rng.next();
    const len = Math.floor(sr * (0.0005 + rng.next() * 0.003 + amp * 0.004)), col = 0.25 + rng.next() * 0.75;
    let y = 0;
    for (let i = 0; i < len; i++) {
      y += col * ((rng.next() * 2 - 1) - y);
      const s = y * Math.exp(-6 * i / len) * amp, idx = (pos + i) % n;
      L[idx] += s * (1 - pan); R[idx] += s * pan;
    }
  }
  normalize([L, R], 0.85);
  const buf = ctx.createBuffer(2, n, sr);
  buf.copyToChannel(L, 0); buf.copyToChannel(R, 1);
  return buf;
}

function makeWave(ctx, n, ampFn) {
  const re = new Float32Array(n + 1), im = new Float32Array(n + 1);
  for (let h = 1; h <= n; h++) im[h] = ampFn(h);
  return ctx.createPeriodicWave(re, im);
}

const PLUCK = {
  harp: { t60: 4.2, blend: 0.24, bright: 0.7, pick: 0.21, maxSeconds: 4.0 },
  lute: { t60: 1.8, blend: 0.4, bright: 0.55, pick: 0.13, maxSeconds: 2.2 },
};

/** Shared, lazily baked resources of one audio context. */
export class Resources {
  constructor(ctx, rng) {
    this.ctx = ctx;
    this.rng = rng;
    this.noise = {
      white: makeNoise(ctx, 'white', 2.5, rng),
      pink: makeNoise(ctx, 'pink', 5, rng),
      brown: makeNoise(ctx, 'brown', 5, rng),
    };
    this.curves = {
      soft: makeCurve('soft', 2.2), hard: makeCurve('soft', 7), fold: makeCurve('fold', 2.5),
      limit: makeCurve('limit', 0),
    };
    this.waves = {
      glottal: makeWave(ctx, 40, (h) => 1 / Math.pow(h, 1.35)),
      reed: makeWave(ctx, 36, (h) => (h % 2 ? 1 : 0.45) / Math.pow(h, 0.95)),
      brass: makeWave(ctx, 30, (h) => Math.exp(-0.5 * Math.pow((h - 2.2) / 3.2, 2)) / Math.sqrt(h)),
    };
    this.irHall = makeImpulse(ctx, rng, { seconds: 3.2, t60: 2.7, predelay: 0.018, bright: 9000, dark: 900, damp: 1.6, build: 0.02, early: 8, earlySpan: 0.08, earlyGain: 0.35 });
    this.irRoom = makeImpulse(ctx, rng, { seconds: 0.7, t60: 0.5, predelay: 0.004, bright: 11000, dark: 2500, damp: 4, build: 0.004, early: 10, earlySpan: 0.035, earlyGain: 0.6 });
    this._baked = new Map();
    this._plucks = new Map();
  }

  /** Lazily baked texture buffers. */
  baked(name) {
    let b = this._baked.get(name);
    if (!b) {
      const c = this.ctx, r = this.rng;
      if (name === 'crackle') b = bakeCrackle(c, r, 4, 60);
      else if (name === 'embers') b = bakeCrackle(c, r, 6, 7);
      else if (name === 'crickets') b = bakeCrickets(c, r, 6);
      else if (name === 'brook') b = bakeBrook(c, r, 5);
      else if (name === 'murmur') b = bakeMurmur(c, r, 7);
      else if (name === 'raindrops') b = bakeRainDrops(c, r, 4);
      else throw new Error('unknown baked buffer ' + name);
      this._baked.set(name, b);
    }
    return b;
  }

  /** Karplus-Strong pluck for an integer MIDI note (LRU cache). */
  pluck(type, midi) {
    const key = type + midi;
    let e = this._plucks.get(key);
    if (e) { this._plucks.delete(key); this._plucks.set(key, e); return e; }
    e = bakePluck(this.ctx, this.rng, mtof(midi), PLUCK[type] || PLUCK.harp);
    this._plucks.set(key, e);
    if (this._plucks.size > 44) this._plucks.delete(this._plucks.keys().next().value);
    return e;
  }
}

// ---------------------------------------------------------------------------------------
// Kit: node-building helper
// ---------------------------------------------------------------------------------------

/**
 * Builds small synthesis graphs. Sources created through a Kit are scheduled immediately and,
 * when `track` is an array, registered in it so the owner can stop/detune them later.
 */
export class Kit {
  constructor(ctx, res, rng) {
    this.ctx = ctx; this.res = res; this.rng = rng;
    /** @type {Array|null} */ this.track = null;
    this.cents = 0;
  }

  _reg(src) { if (this.track) this.track.push(src); return src; }

  /** Oscillator; `type` is a waveform name or a key of Resources.waves. */
  osc(type, f, t0, t1, detune = 0) {
    const o = this.ctx.createOscillator(), w = this.res.waves[type];
    if (w) o.setPeriodicWave(w); else o.type = type;
    o.frequency.value = f;
    o.detune.value = detune + this.cents;
    o.start(t0);
    if (t1 !== undefined) o.stop(t1);
    return this._reg(o);
  }

  /** Looping noise source starting at a random offset. */
  noise(kind, t0, t1, rate = 1) {
    const s = this.ctx.createBufferSource(), b = this.res.noise[kind];
    s.buffer = b; s.loop = true; s.playbackRate.value = rate;
    s.start(t0, this.rng.next() * (b.duration - 0.2));
    if (t1 !== undefined) s.stop(t1);
    return this._reg(s);
  }

  /** Slow random control signal in [-1, 1] changing about `rateHz` times per second. */
  lfoNoise(rateHz, t0, t1) {
    const s = this.ctx.createBufferSource(), b = this.res.noise.white;
    s.buffer = b; s.loop = true; s.playbackRate.value = rateHz / this.ctx.sampleRate;
    s.start(t0, this.rng.next() * (b.duration - 0.2));
    if (t1 !== undefined) s.stop(t1);
    return this._reg(s);
  }

  /** Plays an arbitrary buffer. */
  buf(buffer, t0, o = {}) {
    const s = this.ctx.createBufferSource();
    s.buffer = buffer; s.loop = !!o.loop; s.playbackRate.value = o.rate || 1;
    s.start(t0, o.loop ? this.rng.next() * buffer.duration * 0.9 : 0);
    if (o.stop !== undefined) s.stop(o.stop);
    return this._reg(s);
  }

  gain(v = 1) { const g = this.ctx.createGain(); g.gain.value = v; return g; }

  bq(type, f, q = 0.707, gainDb = 0) {
    const b = this.ctx.createBiquadFilter();
    b.type = type; b.frequency.value = f; b.Q.value = q; b.gain.value = gainDb;
    if (this.cents) b.detune.value = this.cents;
    return b;
  }

  shaper(name) { const w = this.ctx.createWaveShaper(); w.curve = this.res.curves[name]; return w; }
  pan(p) { const n = this.ctx.createStereoPanner(); n.pan.value = p; return n; }
  delay(time, max = 1) { const d = this.ctx.createDelay(max); d.delayTime.value = time; return d; }

  /** Percussive envelope: 0 -> peak (linear attack) -> exponential decay to silence. */
  perc(p, t, peak, a, d) {
    p.setValueAtTime(0, t);
    if (!(peak > 0)) return;
    d = Math.max(0.004, d);
    p.linearRampToValueAtTime(peak, t + a);
    p.exponentialRampToValueAtTime(peak * 0.001, t + a + d);
    p.linearRampToValueAtTime(0, t + a + d + 0.008);
  }

  /** Attack / hold / release envelope with linear segments. */
  ar(p, t, peak, a, hold, r) {
    p.setValueAtTime(0, t);
    p.linearRampToValueAtTime(peak, t + a);
    p.setValueAtTime(peak, t + a + Math.max(0, hold));
    p.linearRampToValueAtTime(0, t + a + Math.max(0, hold) + r);
  }

  /** Linear breakpoint envelope: pts = [[fraction of dur, value], ...]. */
  pts(p, t, dur, pts, scale = 1) {
    p.setValueAtTime(pts[0][1] * scale, t + pts[0][0] * dur);
    for (let i = 1; i < pts.length; i++) p.linearRampToValueAtTime(pts[i][1] * scale, t + pts[i][0] * dur);
  }

  /** Exponential breakpoint curve (frequencies): pts = [[fraction of dur, value > 0], ...]. */
  xpts(p, t, dur, pts, scale = 1) {
    p.setValueAtTime(pts[0][1] * scale, t + pts[0][0] * dur);
    for (let i = 1; i < pts.length; i++) p.exponentialRampToValueAtTime(pts[i][1] * scale, t + pts[i][0] * dur);
  }

  /** Disconnects `node` when `src` has finished playing. */
  autoFree(src, node) { src.onended = () => { try { node.disconnect(); } catch (e) { /* already gone */ } }; }

  /**
   * Pitched tone with optional glide.
   * o: { type, f, f1, glide, fpts, t, dur, a, vol, detune, shape:'perc'|'flat'|'swell', r, peakAt }
   */
  tone(dest, o) {
    const t = o.t, dur = o.dur, vol = o.vol ?? 1, a = o.a ?? 0.003;
    const osc = this.osc(o.type || 'sine', o.f, t, t + dur + 0.05, o.detune || 0);
    if (o.fpts) this.xpts(osc.frequency, t, dur, o.fpts);
    else if (o.f1) { osc.frequency.setValueAtTime(o.f, t); osc.frequency.exponentialRampToValueAtTime(o.f1, t + (o.glide || dur)); }
    const g = this.gain(0);
    if (o.shape === 'flat') this.ar(g.gain, t, vol, a, dur - a - (o.r ?? 0.05), o.r ?? 0.05);
    else if (o.shape === 'swell') { g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + dur * (o.peakAt ?? 0.7)); g.gain.linearRampToValueAtTime(0, t + dur); }
    else this.perc(g.gain, t, vol, a, dur - a);
    osc.connect(g); g.connect(dest);
    return g;
  }

  /**
   * Filtered noise burst.
   * o: { kind, t, dur, a, vol, type, f, fmid, f1, q, hp, lp, rate, shape:'perc'|'bell'|'flat', peakAt, r, am:{rate,depth,type,noise} }
   */
  nz(dest, o) {
    const t = o.t, dur = o.dur, vol = o.vol ?? 1, a = o.a ?? 0.002, end = t + dur + 0.05;
    let node = this.noise(o.kind || 'white', t, end, o.rate || 1);
    if (o.f) {
      const flt = this.bq(o.type || 'bandpass', o.f, o.q ?? 1);
      if (o.fmid || o.f1) {
        flt.frequency.setValueAtTime(o.f, t);
        if (o.fmid) flt.frequency.exponentialRampToValueAtTime(o.fmid, t + dur * (o.peakAt ?? 0.5));
        if (o.f1) flt.frequency.exponentialRampToValueAtTime(o.f1, t + dur);
      }
      node.connect(flt); node = flt;
    }
    if (o.hp) { const h = this.bq('highpass', o.hp, 0.7); node.connect(h); node = h; }
    if (o.lp) { const l = this.bq('lowpass', o.lp, 0.7); node.connect(l); node = l; }
    if (o.am) {
      const am = this.gain(1 - o.am.depth * 0.5), mg = this.gain(o.am.depth * 0.5);
      const m = o.am.noise ? this.lfoNoise(o.am.rate, t, end) : this.osc(o.am.type || 'square', o.am.rate, t, end);
      m.connect(mg); mg.connect(am.gain); node.connect(am); node = am;
    }
    const g = this.gain(0);
    if (o.shape === 'bell') {
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(vol, t + dur * (o.peakAt ?? 0.5));
      g.gain.linearRampToValueAtTime(0, t + dur);
    } else if (o.shape === 'flat') this.ar(g.gain, t, vol, a, dur - a - (o.r ?? 0.05), o.r ?? 0.05);
    else this.perc(g.gain, t, vol, a, dur - a);
    node.connect(g); g.connect(dest);
    return g;
  }

  /**
   * Bank of decaying partials (metal, wood, bells, glass).
   * o: { t, f, ratios[], decays[], gains[], decay, vol, a, type, jit, bend }
   */
  modal(dest, o) {
    const t = o.t, rs = o.ratios, vol = o.vol ?? 1, dk = o.decay ?? 1;
    for (let i = 0; i < rs.length; i++) {
      const d = (o.decays ? o.decays[i] : 1 / (i + 1)) * dk;
      const fr = o.f * rs[i] * (o.jit ? 1 + (this.rng.next() - 0.5) * o.jit : 1);
      if (fr > 15000 || fr < 20) continue;
      const osc = this.osc(o.type || 'sine', fr, t, t + d + 0.06);
      if (o.bend) { osc.frequency.setValueAtTime(fr * o.bend, t); osc.frequency.exponentialRampToValueAtTime(fr, t + 0.04); }
      const g = this.gain(0);
      this.perc(g.gain, t, (o.gains ? o.gains[i] : 1 / (i + 1)) * vol, o.a ?? 0.001, d);
      osc.connect(g); g.connect(dest);
    }
  }

  /**
   * Two-operator FM voice.
   * o: { t, dur, f, f1, ratio, idx, idx1, a, vol, type, mtype, shape:'perc'|'swell'|'flat', peakAt, r }
   */
  fm(dest, o) {
    const t = o.t, dur = o.dur, end = t + dur + 0.05, f = o.f, f1 = o.f1 || f, ratio = o.ratio ?? 2;
    const vol = o.vol ?? 1, a = o.a ?? 0.003, idx = o.idx ?? 1;
    const car = this.osc(o.type || 'sine', f, t, end), mod = this.osc(o.mtype || 'sine', f * ratio, t, end);
    const mg = this.gain(f * idx);
    if (f1 !== f) {
      car.frequency.setValueAtTime(f, t); car.frequency.exponentialRampToValueAtTime(f1, t + dur);
      mod.frequency.setValueAtTime(f * ratio, t); mod.frequency.exponentialRampToValueAtTime(f1 * ratio, t + dur);
    }
    if (o.idx1 != null) { mg.gain.setValueAtTime(f * idx, t); mg.gain.linearRampToValueAtTime(f1 * o.idx1, t + dur); }
    mod.connect(mg); mg.connect(car.frequency);
    const g = this.gain(0);
    if (o.shape === 'swell') {
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(vol, t + dur * (o.peakAt ?? 0.8));
      g.gain.linearRampToValueAtTime(0, t + dur);
    } else if (o.shape === 'flat') this.ar(g.gain, t, vol, a, dur - a - (o.r ?? 0.05), o.r ?? 0.05);
    else this.perc(g.gain, t, vol, a, dur - a);
    car.connect(g); g.connect(dest);
    return g;
  }

  /**
   * Karplus-Strong pluck. o: { t, midi, vol, type:'harp'|'lute', dur, lp, cents }
   */
  pluck(dest, o) {
    const m = Math.round(o.midi), e = this.res.pluck(o.type || 'harp', m), t = o.t, vol = o.vol ?? 1;
    const s = this.ctx.createBufferSource();
    s.buffer = e.buffer;
    s.playbackRate.value = e.rate * Math.pow(2, ((o.midi - m) * 100 + (o.cents || 0) + this.cents) / 1200);
    const g = this.gain(vol);
    let node = s;
    if (o.lp) { const l = this.bq('lowpass', o.lp, 0.6); s.connect(l); node = l; }
    node.connect(g); g.connect(dest);
    s.start(t);
    if (o.dur) { g.gain.setValueAtTime(vol, t + o.dur); g.gain.setTargetAtTime(0, t + o.dur, 0.06); s.stop(t + o.dur + 0.45); }
    this._reg(s);
    return { src: s, out: g };
  }

  /**
   * Formant voice for humans, creatures and birds: harmonic source + breath noise, optional
   * roughness / drive, through parallel band-pass formants.
   * o: { t, dur, f | [[frac,hz]..], type, unison, spread, voiced, tilt, jitter:{rate,depth}, vib:{rate,depth,delay},
   *      breath, breathF, breathQ, breathKind, growl:{rate,rate1,depth,type}, drive, curve,
   *      formants:[[f,q,g]..], formants1, fglide, direct, directF, amp:[[frac,level]..], a, r, vol }
   */
  vox(dest, o) {
    const t = o.t, dur = o.dur, end = t + dur + 0.06;
    const fp = o.f === undefined ? [[0, 120]] : typeof o.f === 'number' ? [[0, o.f]] : o.f, f0 = fp[0][1];
    const pre = this.gain(1), voiced = o.voiced ?? 1;
    if (voiced > 0) {
      const vg = this.gain(voiced), n = o.unison || 1, oscs = [];
      for (let i = 0; i < n; i++) {
        const osc = this.osc(o.type || 'sawtooth', f0, t, end, n > 1 ? (i - (n - 1) / 2) * (o.spread ?? 16) : 0);
        osc.frequency.setValueAtTime(f0, t);
        for (let j = 1; j < fp.length; j++) osc.frequency.exponentialRampToValueAtTime(fp[j][1], t + fp[j][0] * dur);
        osc.connect(vg); oscs.push(osc);
      }
      if (o.tilt) { const lp = this.bq('lowpass', o.tilt, 0.5); vg.connect(lp); lp.connect(pre); } else vg.connect(pre);
      if (o.jitter) {
        const j = this.lfoNoise(o.jitter.rate, t, end), jg = this.gain(o.jitter.depth * f0);
        j.connect(jg); for (const x of oscs) jg.connect(x.frequency);
      }
      if (o.vib) {
        const v = this.osc('sine', o.vib.rate, t, end), vgn = this.gain(0), vd = o.vib.delay ?? 0.1;
        vgn.gain.setValueAtTime(0, t + vd); vgn.gain.linearRampToValueAtTime(o.vib.depth * f0, t + vd + 0.15);
        v.connect(vgn); for (const x of oscs) vgn.connect(x.frequency);
      }
    }
    if (o.breath) {
      let nn = this.noise(o.breathKind || 'white', t, end);
      if (o.breathF) { const bp = this.bq('bandpass', o.breathF, o.breathQ ?? 0.8); nn.connect(bp); nn = bp; }
      const bg = this.gain(o.breath);
      nn.connect(bg); bg.connect(pre);
    }
    let node = pre;
    if (o.growl) {
      const am = this.gain(1 - o.growl.depth * 0.5), l = this.osc(o.growl.type || 'sawtooth', o.growl.rate, t, end);
      const lg = this.gain(o.growl.depth * 0.5);
      if (o.growl.rate1) { l.frequency.setValueAtTime(o.growl.rate, t); l.frequency.linearRampToValueAtTime(o.growl.rate1, t + dur); }
      l.connect(lg); lg.connect(am.gain); node.connect(am); node = am;
    }
    if (o.drive) { const dg = this.gain(o.drive), sh = this.shaper(o.curve || 'soft'); node.connect(dg); dg.connect(sh); node = sh; }
    const env = this.gain(0), mk = (o.vol ?? 1) * 3, F = o.formants, F1 = o.formants1;
    for (let i = 0; i < F.length; i++) {
      const bp = this.bq('bandpass', F[i][0], F[i][1]), g = this.gain(F[i][2]);
      if (F1) { bp.frequency.setValueAtTime(F[i][0], t); bp.frequency.linearRampToValueAtTime(F1[i][0], t + dur * (o.fglide ?? 1)); }
      node.connect(bp); bp.connect(g); g.connect(env);
    }
    if (o.direct) { const lp = this.bq('lowpass', o.directF || 900, 0.5), g = this.gain(o.direct); node.connect(lp); lp.connect(g); g.connect(env); }
    if (o.amp) {
      env.gain.setValueAtTime(0, t);
      for (let j = 0; j < o.amp.length; j++) env.gain.linearRampToValueAtTime(o.amp[j][1] * mk, t + Math.max(0.002, o.amp[j][0] * dur));
      env.gain.linearRampToValueAtTime(0, t + dur + 0.02);
    } else {
      const a = o.a ?? 0.02, r = o.r ?? 0.08;
      this.ar(env.gain, t, mk, a, dur - a - r, r);
    }
    env.connect(dest);
    return env;
  }
}
