/**
 * VALOMBRE audio test bench.
 *  - interactive buttons for every SFX / loop / music state / ambience preset;
 *  - `?auto=1`: offline measurements of everything (duration, peak, RMS, spectral centroid,
 *    onset count), JSON report in <pre id="report">, then document.title = 'AUDIO_TEST_DONE'.
 */
import { AudioEngine } from '../src/audio/audio.js';

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const SR = 44100;

const PRESETS = {
  meadow_day: { biome: 'meadow', hour: 12, rain: 0, wind: 0.3, water: 0, danger: 0 },
  meadow_dawn: { biome: 'meadow', hour: 6, rain: 0, wind: 0.15, water: 0, danger: 0 },
  meadow_night: { biome: 'meadow', hour: 23, rain: 0, wind: 0.15, water: 0, danger: 0 },
  forest_day: { biome: 'forest', hour: 14, rain: 0, wind: 0.35, water: 0, danger: 0 },
  forest_night: { biome: 'forest', hour: 1, rain: 0, wind: 0.2, water: 0, danger: 0 },
  swamp_day: { biome: 'swamp', hour: 15, rain: 0, wind: 0.1, water: 0, danger: 0 },
  swamp_night: { biome: 'swamp', hour: 22, rain: 0, wind: 0.1, water: 0, danger: 0 },
  mountain_wind: { biome: 'mountain', hour: 11, rain: 0, wind: 0.85, water: 0, danger: 0 },
  ash: { biome: 'ash', hour: 16, rain: 0, wind: 0.3, water: 0, danger: 0 },
  coast: { biome: 'coast', hour: 10, rain: 0, wind: 0.4, water: 0.9, danger: 0 },
  citadel: { biome: 'citadel', hour: 18, rain: 0, wind: 0.3, water: 0, danger: 0 },
  village_day: { biome: 'village', hour: 13, rain: 0, wind: 0.15, water: 0, danger: 0 },
  village_night: { biome: 'village', hour: 23.5, rain: 0, wind: 0.1, water: 0, danger: 0 },
  storm: { biome: 'forest', hour: 15, rain: 1, wind: 0.9, water: 0, danger: 0 },
  light_rain: { biome: 'meadow', hour: 12, rain: 0.3, wind: 0.2, water: 0, danger: 0 },
  river: { biome: 'forest', hour: 12, rain: 0, wind: 0.15, water: 1, danger: 0 },
  danger: { biome: 'forest', hour: 22, rain: 0, wind: 0.2, water: 0, danger: 1 },
};

// =========================================================================================
// Interactive bench
// =========================================================================================

const engine = new AudioEngine();
window.audio = engine;
const cat = engine.catalog();
const loopHandles = {};
let musicState = 'none';

function btn(parent, label, fn) {
  const b = document.createElement('button');
  b.textContent = label;
  b.addEventListener('click', () => fn(b));
  parent.appendChild(b);
  return b;
}

function randomPos() {
  const a = Math.random() * Math.PI * 2, d = 2 + Math.random() * 10;
  return [Math.cos(a) * d, 1, Math.sin(a) * d];
}

function buildUI() {
  // Volumes
  for (const key of ['master', 'music', 'sfx', 'ambience', 'ui', 'voice']) {
    const l = document.createElement('label'), r = document.createElement('input');
    r.type = 'range'; r.min = 0; r.max = 1; r.step = 0.01; r.value = { master: 1, music: 0.7, sfx: 1, ambience: 0.8, ui: 0.8, voice: 1 }[key];
    r.addEventListener('input', () => engine.setVolumes({ [key]: +r.value }));
    l.append(key + ' ', r);
    $('volumes').appendChild(l);
  }
  // SFX grouped by category
  const groups = {};
  for (const n of engine.list()) (groups[cat.categories[n]] ||= []).push(n);
  for (const g in groups) {
    const h = document.createElement('h3'); h.textContent = g; $('sfx').appendChild(h);
    const d = document.createElement('div'); $('sfx').appendChild(d);
    for (const n of groups[g]) btn(d, n, () => engine.play(n, $('positional').checked ? { pos: randomPos() } : undefined));
  }
  for (const s of cat.footsteps) btn($('foot'), s, () => engine.footstep(s, { run: $('run').checked, heavy: $('heavy').checked }));
  for (const v of cat.voices) btn($('voice'), v, () => engine.voice(v, { pitch: +$('vpitch').value }));
  $('vpitch').addEventListener('input', () => { $('vpitchv').textContent = (+$('vpitch').value).toFixed(2); });
  for (const n of cat.loops) {
    btn($('loops'), n, (b) => {
      if (loopHandles[n]) { loopHandles[n].stop(0.5); loopHandles[n] = null; b.classList.remove('on'); }
      else { loopHandles[n] = engine.startLoop(n, { pos: [3, 1, -2] }); b.classList.add('on'); }
    });
  }
  // Music
  for (const b of cat.biomes) { $('mbiome').add(new Option(b, b)); $('abiome').add(new Option(b, b)); }
  for (const b of cat.bosses) $('mboss').add(new Option(b, b));
  const sendMusic = () => engine.setMusic(musicState, { biome: $('mbiome').value, boss: $('mboss').value, intensity: +$('mint').value });
  for (const s of cat.music) btn($('music'), s, () => { musicState = s; sendMusic(); });
  $('mbiome').addEventListener('change', sendMusic);
  $('mboss').addEventListener('change', sendMusic);
  $('mint').addEventListener('input', () => { $('mintv').textContent = (+$('mint').value).toFixed(2); sendMusic(); });
  // Ambience
  const sendAmb = () => {
    $('ahourv').textContent = $('ahour').value;
    engine.setAmbience({ biome: $('abiome').value, hour: +$('ahour').value, rain: +$('arain').value, wind: +$('awind').value, water: +$('awater').value, danger: +$('adanger').value });
  };
  for (const id of ['abiome', 'ahour', 'arain', 'awind', 'awater', 'adanger']) $(id).addEventListener('input', sendAmb);
  for (const p in PRESETS) {
    btn($('presets'), p, () => {
      const s = PRESETS[p];
      $('abiome').value = s.biome; $('ahour').value = s.hour; $('arain').value = s.rain; $('awind').value = s.wind; $('awater').value = s.water; $('adanger').value = s.danger;
      sendAmb();
    });
  }
  for (const [label, d] of [['overhead', 0], ['near', 0.3], ['mid', 0.6], ['far', 1]]) btn($('thunder'), label, () => engine.thunder(d));
  for (const e of cat.ambienceEvents) btn($('events'), e, () => engine.debugAmbienceEvent(e, { pos: randomPos(), ref: 12 }));

  $('init').addEventListener('click', async () => { await engine.init(); $('init').classList.remove('big'); });
  $('suspend').addEventListener('click', () => engine.suspend());
  $('resume').addEventListener('click', () => engine.resume());
  $('runauto').addEventListener('click', () => runAuto());

  let last = performance.now(), walkT = 0, tick = 0;
  const frame = (now) => {
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    engine.setListener([0, 1.7, 0], [0, 0, -1]);
    engine.update(dt);
    if ($('walk').checked && engine.ready) {
      walkT -= dt;
      if (walkT <= 0) {
        walkT = $('run').checked ? 0.3 : 0.48;
        engine.footstep(cat.footsteps[Math.floor(now / 6000) % cat.footsteps.length], { run: $('run').checked, heavy: $('heavy').checked });
      }
    }
    if (++tick % 15 === 0) {
      const s = engine.stats;
      $('status').textContent = engine.ready ? `ready | voices ${s.voices} | loops ${s.loops}/${s.loopHandles} | music ${s.music} | ctx ${engine.context.state}` : 'not initialised';
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

// =========================================================================================
// Offline rendering + analysis
// =========================================================================================

/**
 * Renders `seconds` of the engine through an OfflineAudioContext.
 * Channels 0-1: final output. Channels 2-3: mix before the limiter.
 * `step` > 0 runs engine.update() at that period during the render (via suspend/resume).
 */
async function render(seconds, setup, o = {}) {
  const ctx = new OfflineAudioContext(4, Math.ceil(seconds * SR), SR);
  const out = ctx.createGain(), tap = ctx.createGain(), merger = ctx.createChannelMerger(4);
  for (const g of [out, tap]) { g.channelCount = 2; g.channelCountMode = 'explicit'; }
  const s1 = ctx.createChannelSplitter(2), s2 = ctx.createChannelSplitter(2);
  out.connect(s1); s1.connect(merger, 0, 0); s1.connect(merger, 1, 1);
  tap.connect(s2); s2.connect(merger, 0, 2); s2.connect(merger, 1, 3);
  merger.connect(ctx.destination);
  const e = new AudioEngine({ context: ctx, destination: out, seed: o.seed === undefined ? 20261109 : o.seed });
  await e.init();
  if (!e.ready) throw new Error('engine init failed');
  e.debugNodes.pre.connect(tap);
  e.setListener([0, 1.7, 0], [0, 0, -1]);
  await setup(e, ctx);
  const step = o.step || 0;
  let fired = !o.fire;
  if (o.fire && step <= 0) ctx.suspend(o.at).then(() => { try { o.fire(e, ctx); } catch (err) { console.error(err); } ctx.resume(); });
  if (step > 0) {
    for (let t = step; t < seconds - 0.01; t += step) {
      const tt = t;
      ctx.suspend(tt).then(() => {
        try {
          if (!fired && tt >= o.at - 1e-6) { fired = true; o.fire(e, ctx); }
          e.update(step);
          if (o.onStep) o.onStep(e, tt);
        } catch (err) { console.error(err); }
        ctx.resume();
      });
    }
  }
  e.update(0.016);
  const buf = await ctx.startRendering();
  return { buf, engine: e };
}

function levels(buf, t0, t1, full) {
  const sr = buf.sampleRate, L = buf.getChannelData(0), R = buf.getChannelData(1), pL = buf.getChannelData(2), pR = buf.getChannelData(3);
  const i0 = Math.floor(t0 * sr), i1 = Math.min(buf.length, Math.floor(t1 * sr)), TH = 0.0015;
  let peak = 0, pre = 0, first = -1, last = -1;
  for (let i = i0; i < i1; i++) {
    const a = Math.max(Math.abs(L[i]), Math.abs(R[i])), b = Math.max(Math.abs(pL[i]), Math.abs(pR[i]));
    if (a > peak) peak = a;
    if (b > pre) pre = b;
    if (a > TH) { if (first < 0) first = i; last = i; }
  }
  const a0 = full || first < 0 ? i0 : first, a1 = full || first < 0 ? i1 : last + 1;
  let sum = 0, sumPre = 0;
  for (let i = a0; i < a1; i++) { sum += 0.5 * (L[i] * L[i] + R[i] * R[i]); sumPre += 0.5 * (pL[i] * pL[i] + pR[i] * pR[i]); }
  const n = Math.max(1, a1 - a0);
  return {
    peak, pre, rms: Math.sqrt(sum / n), rmsPre: Math.sqrt(sumPre / n),
    start: first < 0 ? 0 : first / sr, dur: first < 0 ? 0 : (last + 1) / sr - t0, tail: last >= i1 - 256,
  };
}

const NF = 1024, HOP = 512;
const fRe = new Float32Array(NF), fIm = new Float32Array(NF), hann = new Float32Array(NF);
const cosT = new Float32Array(NF / 2), sinT = new Float32Array(NF / 2), rev = new Uint16Array(NF);
for (let i = 0; i < NF; i++) hann[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / NF);
for (let i = 0; i < NF / 2; i++) { cosT[i] = Math.cos(2 * Math.PI * i / NF); sinT[i] = Math.sin(2 * Math.PI * i / NF); }
for (let i = 0, bits = Math.log2(NF); i < NF; i++) { let r = 0; for (let b = 0; b < bits; b++) if (i & (1 << b)) r |= 1 << (bits - 1 - b); rev[i] = r; }

function fft() {
  for (let i = 0; i < NF; i++) { const j = rev[i]; if (j > i) { const a = fRe[i]; fRe[i] = fRe[j]; fRe[j] = a; const b = fIm[i]; fIm[i] = fIm[j]; fIm[j] = b; } }
  for (let size = 2; size <= NF; size <<= 1) {
    const half = size >> 1, stepT = NF / size;
    for (let i = 0; i < NF; i += size) {
      for (let j = 0, k = 0; j < half; j++, k += stepT) {
        const wr = cosT[k], wi = -sinT[k], a = i + j, b = a + half;
        const xr = fRe[b] * wr - fIm[b] * wi, xi = fRe[b] * wi + fIm[b] * wr;
        fRe[b] = fRe[a] - xr; fIm[b] = fIm[a] - xi; fRe[a] += xr; fIm[a] += xi;
      }
    }
  }
}

/** Spectral centroid (Hz), band energy shares [<250, 250-2k, >2k] in %, onset count (spectral flux). */
function spectral(buf, t0, t1) {
  const sr = buf.sampleRate, L = buf.getChannelData(0), R = buf.getChannelData(1);
  const i0 = Math.floor(t0 * sr), i1 = Math.min(buf.length, Math.floor(t1 * sr)), half = NF / 2;
  const avg = new Float64Array(half), prev = new Float32Array(half), flux = [];
  let frames = 0;
  for (let p = i0; p + NF <= i1; p += HOP) {
    for (let i = 0; i < NF; i++) { fRe[i] = 0.5 * (L[p + i] + R[p + i]) * hann[i]; fIm[i] = 0; }
    fft();
    let fl = 0;
    for (let k = 1; k < half; k++) {
      const m = Math.hypot(fRe[k], fIm[k]) / (NF / 4);
      avg[k] += m * m;
      const lm = Math.log1p(m * 200), d = lm - prev[k];
      if (d > 0) fl += d;
      prev[k] = lm;
    }
    flux.push(frames === 0 ? 0 : fl);
    frames++;
  }
  let num = 0, den = 0, lo = 0, mid = 0, hi = 0;
  for (let k = 1; k < half; k++) {
    const f = k * sr / NF, pw = avg[k], m = Math.sqrt(pw);
    num += f * m; den += m;
    if (f < 250) lo += pw; else if (f < 2000) mid += pw; else hi += pw;
  }
  const tot = lo + mid + hi || 1;
  // Onsets: local maxima of the flux above an adaptive threshold.
  let mean = 0;
  for (const v of flux) mean += v;
  mean /= Math.max(1, flux.length);
  let onsets = 0, lastOn = -100;
  const W = 8;
  for (let i = 2; i < flux.length - 1; i++) {
    let lm = 0, c = 0;
    for (let j = Math.max(0, i - W); j <= Math.min(flux.length - 1, i + W); j++) { lm += flux[j]; c++; }
    lm /= c;
    if (flux[i] > flux[i - 1] && flux[i] >= flux[i + 1] && flux[i] > lm * 1.5 + mean * 0.3 + 1.5 && i - lastOn >= 4) { onsets++; lastOn = i; }
  }
  return { cen: den > 0 ? num / den : 0, bands: [100 * lo / tot, 100 * mid / tot, 100 * hi / tot], onsets, seconds: (i1 - i0) / sr };
}

const r3 = (x) => Math.round(x * 1000) / 1000;
const WARM = 0.5;
const LIMITS = { ui: 4.5, combat: 4.5, creature: 7, world: 8, foot: 1.5, voice: 3.5, amb: 8, weather: 9.6 };

/** Measures a one-shot rendered by `trigger(engine)`. */
async function measureShot(trigger, kind, seconds, seed) {
  // Chromium's compressor dips its gain for ~0.3 s after a context starts: trigger after WARM seconds.
  const { buf } = await render(seconds + WARM, () => {}, { seed, at: WARM, fire: (e) => trigger(e) });
  const lv = levels(buf, WARM, seconds + WARM, false), sp = spectral(buf, lv.start, Math.max(lv.start + 0.1, WARM + lv.dur));
  const flags = [];
  if (lv.rms < 0.003) flags.push('silent');
  if (lv.peak > 0.99) flags.push('clipping');
  if (lv.dur > (LIMITS[kind] || 8) || lv.tail) flags.push('too_long');
  if (lv.pre > 1.0) flags.push('hot');
  if (lv.peak < 0.03 && lv.rms >= 0.003) flags.push('quiet');
  return { dur: r3(lv.dur), peak: r3(lv.peak), rms: r3(lv.rms), pre: r3(lv.pre), cen: Math.round(sp.cen), flags };
}

/** Measures a continuous bed (music, ambience, loop). */
async function measureBed(seconds, from, setup, o = {}) {
  const { buf, engine: e } = await render(seconds, setup, Object.assign({ step: 0.05 }, o));
  const lv = levels(buf, from, seconds, true), sp = spectral(buf, from, seconds);
  const flags = [];
  if (lv.rms < 0.003) flags.push('silent');
  if (lv.peak > 0.99) flags.push('clipping');
  if (lv.pre > 1.0) flags.push('hot');
  return {
    peak: r3(lv.peak), rms: r3(lv.rms), pre: r3(lv.pre), cen: Math.round(sp.cen), bands: sp.bands.map((b) => Math.round(b)),
    onsets10: Math.round(sp.onsets * 100 / sp.seconds) / 10, flags, _music: e.stats.music, _buf: o.keep ? buf : null,
  };
}

function compactJSON(rep) {
  const lines = ['{'];
  const keys = Object.keys(rep);
  keys.forEach((k, i) => {
    const v = rep[k], comma = i < keys.length - 1 ? ',' : '';
    if (v && typeof v === 'object' && !Array.isArray(v) && Object.values(v).every((x) => x && typeof x === 'object')) {
      lines.push(`  ${JSON.stringify(k)}: {`);
      const ek = Object.keys(v);
      ek.forEach((n, j) => lines.push(`    ${JSON.stringify(n)}: ${JSON.stringify(v[n])}${j < ek.length - 1 ? ',' : ''}`));
      lines.push('  }' + comma);
    } else lines.push(`  ${JSON.stringify(k)}: ${JSON.stringify(v)}${comma}`);
  });
  lines.push('}');
  return lines.join('\n');
}

async function runAuto() {
  const t0 = performance.now();
  const only = params.get('only') ? params.get('only').split(',') : null;
  const filter = params.get('filter') || '';
  const fast = params.get('fast') === '1';
  const want = (sec) => !only || only.includes(sec);
  const pass = (n) => !filter || n.includes(filter);
  const prog = (s) => { $('progress').textContent = s; };
  const rep = { summary: null, checks: {}, calib: null };
  const flagged = [];
  let count = 0;
  const note = (section, name, m) => { count++; if (m.flags && m.flags.length) flagged.push(`${section}/${name}: ${m.flags.join('+')}`); };
  const tick = () => new Promise((res) => setTimeout(res, 0));

  try {
    // Limiter calibration: a quiet sine straight into the master; post/pre ratio should be 1.
    {
      const { buf } = await render(2, (e, ctx) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = 440; g.gain.value = 0.05; o.connect(g); g.connect(e.debugNodes.pre); o.start(0);
      });
      const lv = levels(buf, 1.2, 2, true);
      rep.calib = { quietSineGain: r3(lv.rms / lv.rmsPre) };
      const { buf: b2 } = await render(2, (e, ctx) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = 440; g.gain.value = 3; o.connect(g); g.connect(e.debugNodes.pre); o.start(0);
      });
      rep.calib.overloadPeak = r3(levels(b2, 1, 2, true).peak);
    }

    if (want('engine')) {
      prog('engine checks');
      // 1. Every public method is safe before init().
      let pre = true;
      try {
        const e0 = new AudioEngine();
        e0.setVolumes({ master: 0.5 }); e0.setListener([0, 0, 0], [0, 0, -1]); e0.update(0.016); e0.play('ui_click'); e0.play('nope');
        const h = e0.startLoop('fire', { pos: [1, 0, 0] });
        h.setVolume(0.5); h.setPitch(1.1); h.setPos([2, 0, 0]); h.stop(0.1);
        e0.startLoop('nope').stop(); e0.footstep('grass'); e0.voice('attack', { pitch: 1 });
        e0.setAmbience({ biome: 'forest' }); e0.setMusic('explore', { biome: 'forest' }); e0.thunder(0.5);
        e0.resume(); e0.suspend(); void e0.ready; void e0.list();
      } catch (err) { pre = String(err); }
      rep.checks.preinit_safe = { ok: pre === true, error: pre === true ? null : pre };
      if (pre !== true) flagged.push('check/preinit_safe');

      // 2. Positional audio: a source on the right is louder on the right; level falls with distance.
      const side = async (pos) => {
        const { buf } = await render(1.6, () => {}, { at: WARM, fire: (e) => e.play('hit_wood', { pos }), seed: 5 });
        const L = buf.getChannelData(0), R = buf.getChannelData(1);
        let l = 0, r = 0;
        for (let i = Math.floor(WARM * SR); i < buf.length; i++) { l += L[i] * L[i]; r += R[i] * R[i]; }
        return { l: Math.sqrt(l / buf.length), r: Math.sqrt(r / buf.length) };
      };
      const right = await side([6, 1.7, 0]), near = await side([0, 1.7, -4]), far = await side([0, 1.7, -16]);
      const ratio = (far.l + far.r) / (near.l + near.r);
      rep.checks.positional = {
        rightSourceLR: [r3(right.l), r3(right.r)], dist4mVs16m: r3(ratio),
        ok: right.r > right.l * 1.5 && ratio > 0.15 && ratio < 0.4,
      };
      if (!rep.checks.positional.ok) flagged.push('check/positional');

      // 3. Voice cap, unknown names, loop virtualisation.
      let maxVoices = 0, loopsNear = 0, loopsFar = 0, burstErr = null;
      await render(3.2, () => {}, {
        step: 0.05, at: WARM,
        fire: (e) => {
          try {
            for (let i = 0; i < 70; i++) e.play(cat.sfx[i % cat.sfx.length], { pos: [Math.sin(i) * 5, 1, Math.cos(i) * 5] });
            maxVoices = e.stats.voices;
            for (let i = 0; i < 40; i++) e.startLoop('torch', { pos: [i * 5, 2, 0] });
            e.play('does_not_exist'); e.footstep('lava'); e.voice('sing'); e.setMusic('polka'); e.setAmbience({ biome: 'moon' });
            e.startLoop('nope').setVolume(1);
          } catch (err) { burstErr = String(err); }
        },
        onStep: (e, t) => {
          if (Math.abs(t - 1.5) < 0.02) { loopsNear = e.stats.loops; e.setListener([150, 1.7, 0], [0, 0, -1]); }
          if (t > 2.9) loopsFar = e.stats.loops;
        },
      });
      rep.checks.voice_cap = { burstOf: 70, voices: maxVoices, error: burstErr, ok: maxVoices > 0 && maxVoices <= 28 && !burstErr };
      rep.checks.loop_virtualisation = { handles: 40, activeAtOrigin: loopsNear, activeAt150m: loopsFar, ok: loopsNear > 0 && loopsNear <= 12 && loopsFar > 0 && loopsFar <= 12 };
      if (!rep.checks.voice_cap.ok) flagged.push('check/voice_cap');

      // 4. Soak: schedule many bars of every music state (no rendering) to exercise all generator paths.
      const soak = { bars: 0, errors: [] };
      const states = [['menu'], ['creator'], ['village'], ['combat', { intensity: 1 }]];
      for (const b of cat.bosses) states.push(['boss', { boss: b, intensity: 1 }]);
      for (const b of cat.biomes) states.push(['explore', { biome: b }]);
      for (const [st, o] of states) {
        const ctx = new OfflineAudioContext(2, SR, SR), e = new AudioEngine({ context: ctx, seed: 99 });
        await e.init();
        e.setMusic(st, o);
        const p = e._music.cur;
        try { for (let i = 0; i < 70; i++) { p.intensityT = (i % 20) / 19; p.step(); soak.bars++; } } catch (err) { soak.errors.push(st + (o ? ':' + (o.boss || o.biome || '') : '') + ' ' + String(err)); }
        await tick();
      }
      rep.checks.music_soak = Object.assign(soak, { ok: soak.errors.length === 0 });
      if (!soak.ok) flagged.push('check/music_soak');
      if (!rep.checks.loop_virtualisation.ok) flagged.push('check/loop_virtualisation');
    }

    if (want('sfx')) {
      rep.sfx = {};
      for (const n of cat.sfx.filter(pass)) {
        prog('sfx ' + n);
        const kind = cat.categories[n], m = await measureShot((e) => e.play(n), kind, 9.6, 1001);
        if (!fast) {
          const m2 = await measureShot((e) => e.play(n), kind, 9.6, 77);
          m.var = [r3(m2.dur - m.dur), r3(m2.peak - m.peak), m2.cen - m.cen];
          for (const f of m2.flags) if (!m.flags.includes(f)) m.flags.push(f);
          if (m.var[0] === 0 && m.var[1] === 0 && m.var[2] === 0) m.flags.push('no_variation');
        }
        m.cat = kind;
        rep.sfx[n] = m; note('sfx', n, m);
        await tick();
      }
    }
    if (want('foot')) {
      rep.foot = {};
      for (const s of cat.footsteps) {
        for (const [tag, o] of [['walk', {}], ['run', { run: true }], ['heavy', { heavy: true }]]) {
          const n = s + '_' + tag;
          if (!pass(n)) continue;
          prog('foot ' + n);
          const m = await measureShot((e) => e.footstep(s, o), 'foot', 3, 31);
          rep.foot[n] = m; note('foot', n, m);
        }
        await tick();
      }
    }
    if (want('voice')) {
      rep.voice = {};
      for (const v of cat.voices) {
        for (const p of [0.7, 1, 1.5]) {
          const n = v + '_p' + p;
          if (!pass(n)) continue;
          prog('voice ' + n);
          const m = await measureShot((e) => e.voice(v, { pitch: p }), 'voice', 5, 5);
          rep.voice[n] = m; note('voice', n, m);
        }
        await tick();
      }
    }
    if (want('thunder')) {
      rep.thunder = {};
      for (const d of [0, 0.5, 1]) {
        prog('thunder ' + d);
        const m = await measureShot((e) => e.thunder(d), 'weather', 9.9, 9);
        rep.thunder['d' + d] = m; note('thunder', 'd' + d, m);
      }
    }
    if (want('events')) {
      rep.events = {};
      for (const n of cat.ambienceEvents.filter(pass)) {
        prog('event ' + n);
        const m = await measureShot((e) => e.debugAmbienceEvent(n), 'amb', 9.6, 3);
        rep.events[n] = m; note('events', n, m);
        await tick();
      }
    }
    if (want('loops')) {
      rep.loops = {};
      for (const n of cat.loops.filter(pass)) {
        prog('loop ' + n);
        const m = await measureBed(6, 1, (e) => { e.startLoop(n); });
        delete m._music; delete m._buf;
        rep.loops[n] = m; note('loops', n, m);
        await tick();
      }
    }
    if (want('music')) {
      rep.music = {};
      const jobs = [
        ['menu', 26, 2, (e) => e.setMusic('menu')],
        ['creator', 26, 2, (e) => e.setMusic('creator')],
        ['village', 16, 2, (e) => e.setMusic('village')],
        ['combat_i0', 13, 3, (e) => e.setMusic('combat', { intensity: 0 })],
        ['combat_i50', 13, 3, (e) => e.setMusic('combat', { intensity: 0.5 })],
        ['combat_i100', 13, 3, (e) => e.setMusic('combat', { intensity: 1 })],
      ];
      for (const b of cat.bosses) {
        jobs.push(['boss_' + b + '_i30', 13, 3, (e) => e.setMusic('boss', { boss: b, intensity: 0.3 })]);
        jobs.push(['boss_' + b + '_i100', 13, 3, (e) => e.setMusic('boss', { boss: b, intensity: 1 })]);
      }
      for (const b of cat.biomes) if (b !== 'village') jobs.push(['explore_' + b, 32, 2, (e) => e.setMusic('explore', { biome: b })]);
      for (const [name, secs, from, setup] of jobs) {
        if (!pass(name)) continue;
        prog('music ' + name);
        const m = await measureBed(secs, from, setup);
        delete m._music; delete m._buf;
        rep.music[name] = m; note('music', name, m);
        await tick();
      }
      // Stingers: measured as one-shots on top of an exploration state, then the fallback is checked.
      for (const st of ['death', 'victory']) {
        if (!pass(st)) continue;
        prog('music ' + st);
        let fallback = null;
        const { buf } = await render(14.5, (en) => { en.setMusic('none'); }, {
          step: 0.05, at: WARM, fire: (en) => en.setMusic(st), onStep: (en, t) => { if (t > 14.3) fallback = en.stats.music; },
        });
        const lv = levels(buf, WARM, 14.5, false), sp = spectral(buf, WARM, WARM + Math.max(1, lv.dur));
        const m = { dur: r3(lv.dur), peak: r3(lv.peak), rms: r3(lv.rms), pre: r3(lv.pre), cen: Math.round(sp.cen), onsets: sp.onsets, fallbackTo: fallback, flags: [] };
        if (lv.rms < 0.003) m.flags.push('silent');
        if (lv.peak > 0.99) m.flags.push('clipping');
        if (lv.pre > 1) m.flags.push('hot');
        if (fallback !== 'none') m.flags.push('no_fallback');
        if (st === 'death' && (lv.dur < 3 || lv.dur > 8)) m.flags.push('length');
        if (st === 'victory' && (lv.dur < 5 || lv.dur > 10.5)) m.flags.push('length');
        rep.music[st] = m; note('music', st, m);
      }
      // Stinger falling back to the previous exploration state.
      if (!filter) {
        let key = null;
        await render(12, (en) => { en.setMusic('explore', { biome: 'forest' }); }, {
          step: 0.05, onStep: (en, t) => { if (Math.abs(t - 1) < 0.02) en.setMusic('combat'); if (Math.abs(t - 3) < 0.02) en.setMusic('victory'); if (t > 3) en.setMusic('victory'); if (t > 11.8) key = en.stats.music; },
        });
        rep.checks.stinger_fallback = { expected: 'explore:forest', got: key, ok: key === 'explore:forest' };
        if (key !== 'explore:forest') flagged.push('check/stinger_fallback');
      }
    }
    if (want('ambience')) {
      rep.ambience = {};
      for (const p in PRESETS) {
        if (!pass(p)) continue;
        prog('ambience ' + p);
        const m = await measureBed(14, 2, (e) => e.setAmbience(PRESETS[p]), { seed: 4242 });
        delete m._music; delete m._buf;
        rep.ambience[p] = m; note('ambience', p, m);
        await tick();
      }
    }

    // ---- Musical sanity checks -------------------------------------------------------
    const M = rep.music;
    if (M && !filter) {
      const ex = Object.keys(M).filter((k) => k.startsWith('explore_')).map((k) => M[k]);
      const avg = (arr, f) => arr.reduce((a, x) => a + x[f], 0) / Math.max(1, arr.length);
      const exOn = avg(ex, 'onsets10'), exRms = avg(ex, 'rms');
      const c = M.combat_i50;
      rep.checks.combat_vs_explore = {
        combatOnsets10: c.onsets10, exploreOnsets10: r3(exOn), combatRms: c.rms, exploreRms: r3(exRms),
        ok: c.onsets10 > exOn * 1.5 && c.rms > exRms * 1.3,
      };
      if (!rep.checks.combat_vs_explore.ok) flagged.push('check/combat_vs_explore');
      const inten = {};
      // More energy at full intensity, and the rhythm must not be buried under the added sustained layers.
      let intenOk = M.combat_i100.rms > M.combat_i0.rms * 1.2 && M.combat_i100.onsets10 >= M.combat_i0.onsets10 * 0.8;
      inten.combat = [M.combat_i0.rms, M.combat_i50.rms, M.combat_i100.rms];
      inten.combatOnsets10 = [M.combat_i0.onsets10, M.combat_i50.onsets10, M.combat_i100.onsets10];
      for (const b of cat.bosses) {
        const a = M['boss_' + b + '_i30'], z = M['boss_' + b + '_i100'];
        inten[b] = [a.rms, z.rms];
        if (!(z.rms > a.rms)) intenOk = false;
      }
      rep.checks.intensity_raises_energy = Object.assign(inten, { ok: intenOk });
      if (!intenOk) flagged.push('check/intensity');
      // Boss themes must differ: compare (onset rate, centroid, band profile).
      const feat = (m) => [m.onsets10 / 40, m.cen / 2000, m.bands[0] / 100, m.bands[2] / 100];
      const dist = (a, b) => Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) * (v - b[i]), 0));
      let minD = Infinity, minPair = '';
      for (let i = 0; i < cat.bosses.length; i++) {
        for (let j = i + 1; j < cat.bosses.length; j++) {
          const d = dist(feat(M['boss_' + cat.bosses[i] + '_i100']), feat(M['boss_' + cat.bosses[j] + '_i100']));
          if (d < minD) { minD = d; minPair = cat.bosses[i] + '/' + cat.bosses[j]; }
        }
      }
      rep.checks.boss_distinct = { minDistance: r3(minD), closestPair: minPair, ok: minD > 0.03 };
      if (!rep.checks.boss_distinct.ok) flagged.push('check/boss_distinct');
    }
    const A = rep.ambience;
    if (A && !filter) {
      const names = Object.keys(A), feat = (m) => [m.cen / 3000, m.bands[0] / 100, m.bands[1] / 100, m.bands[2] / 100, Math.min(1, m.rms * 10)];
      let minD = Infinity, minPair = '';
      for (let i = 0; i < names.length; i++) {
        for (let j = i + 1; j < names.length; j++) {
          const a = feat(A[names[i]]), b = feat(A[names[j]]);
          const d = Math.sqrt(a.reduce((s, v, k) => s + (v - b[k]) * (v - b[k]), 0));
          if (d < minD) { minD = d; minPair = names[i] + '/' + names[j]; }
        }
      }
      rep.checks.ambience_distinct = { minDistance: r3(minD), closestPair: minPair, ok: minD > 0.02 };
      if (!rep.checks.ambience_distinct.ok) flagged.push('check/ambience_distinct');
    }
    rep.summary = { measured: count, flagged: flagged.length, flaggedList: flagged, seconds: Math.round((performance.now() - t0) / 100) / 10, sampleRate: SR };
  } catch (err) {
    rep.summary = { error: String(err && err.stack || err), measured: count, flagged: flagged.length, flaggedList: flagged };
  }
  window.__report = rep;
  $('report').textContent = compactJSON(rep);
  prog('done in ' + Math.round((performance.now() - t0) / 1000) + ' s');
  document.title = 'AUDIO_TEST_DONE';
}

buildUI();
if (params.get('auto') === '1') runAuto();
