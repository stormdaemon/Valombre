// VALOMBRE UI — small DOM toolkit (no dependency) + reusable form widgets.

/** h('button.v-btn.primary', { text, onclick, data:{}, title }, ...children) */
export function h(sel, props, ...kids) {
  const parts = sel.split('.');
  const el = document.createElement(parts[0] || 'div');
  if (parts.length > 1) el.className = parts.slice(1).join(' ');
  if (props) {
    for (const k in props) {
      const v = props[k];
      if (v === null || v === undefined || v === false) continue;
      if (k === 'text') el.textContent = v;
      else if (k === 'html') el.innerHTML = v;
      else if (k === 'class') { if (v) el.className += ' ' + v; }
      else if (k === 'style') { if (typeof v === 'string') el.style.cssText = v; else Object.assign(el.style, v); }
      else if (k === 'data') { for (const d in v) if (v[d] !== undefined && v[d] !== null) el.dataset[d] = v[d]; }
      else if (k === 'nav') el.setAttribute('data-nav', '');
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
  }
  append(el, kids);
  return el;
}

export function append(el, kids) {
  for (const k of kids) {
    if (k === null || k === undefined || k === false) continue;
    if (Array.isArray(k)) append(el, k);
    else el.appendChild(typeof k === 'object' ? k : document.createTextNode(String(k)));
  }
  return el;
}

export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }

export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

/** French number formatting: 1,5  /  12 400 */
export function num(v, digits = 0) {
  if (typeof v !== 'number' || !isFinite(v)) return '—';
  const s = v.toFixed(digits);
  const [i, f] = s.split('.');
  const neg = i.startsWith('-');
  const ii = (neg ? i.slice(1) : i).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return (neg ? '−' : '') + ii + (f ? ',' + f : '');
}

export function signed(v, digits = 0) {
  const r = Number(v.toFixed(digits));
  return (r > 0 ? '+' : r < 0 ? '−' : '±') + num(Math.abs(r), digits);
}

export function playtime(sec) {
  sec = Math.max(0, Math.floor(sec || 0));
  const hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60);
  return hh > 0 ? `${hh} h ${String(mm).padStart(2, '0')}` : `${mm} min`;
}

export function dateStr(ms) {
  if (!ms) return '';
  try {
    const d = new Date(ms);
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) + ' · ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  } catch (e) { return ''; }
}

export function hourStr(hour) {
  if (typeof hour !== 'number' || !isFinite(hour)) return '';
  const hh = Math.floor(((hour % 24) + 24) % 24), mm = Math.floor((hour - Math.floor(hour)) * 60);
  return `${hh} h ${String(mm).padStart(2, '0')}`;
}

export const escapeHtml = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// ---------------------------------------------------------------------------------------------- widgets
// Every widget root carries [data-nav] (keyboard / gamepad focus) and an `_adjust(dir)` hook used by the
// navigation code for ← / →.

/** Slider. opts: { min, max, step, value, def, unit, format(v) -> string, onInput(v), wide } */
export function slider(opts) {
  const { min, max } = opts;
  const step = opts.step || (max - min) / 100;
  const bipolar = min < 0 && max > 0;
  let value = clamp(opts.value ?? min, min, max);
  const fill = h('div.v-slider-fill');
  const thumb = h('div.v-slider-thumb');
  const track = h('div.v-slider-track', null, bipolar ? h('div.v-slider-zero') : null, fill, thumb);
  const val = h('span.v-slider-val');
  const el = h('div.v-slider', { nav: true, tabindex: 0, role: 'slider', 'aria-valuemin': min, 'aria-valuemax': max }, track, val);
  const fmt = opts.format || ((v) => num(v, step < 1 ? (step < 0.1 ? 2 : 1) : 0) + (opts.unit || ''));
  const paint = () => {
    const t = (value - min) / (max - min || 1);
    thumb.style.left = (t * 100).toFixed(2) + '%';
    if (bipolar) {
      const z = (0 - min) / (max - min);
      fill.style.left = (Math.min(z, t) * 100).toFixed(2) + '%';
      fill.style.width = (Math.abs(t - z) * 100).toFixed(2) + '%';
    } else fill.style.width = (t * 100).toFixed(2) + '%';
    val.textContent = fmt(value);
    el.setAttribute('aria-valuenow', value);
    el.classList.toggle('is-default', opts.def !== undefined && Math.abs(value - opts.def) < step * 0.5);
  };
  const snap = (v) => {
    v = Math.round((v - min) / step) * step + min;
    return clamp(Number(v.toFixed(5)), min, max);
  };
  const commit = (v, fire = true) => {
    v = snap(v);
    if (v === value) return;
    value = v; paint();
    if (fire && opts.onInput) opts.onInput(value);
  };
  let rect = null;
  const fromPointer = (e) => { if (rect && rect.width > 0) commit(min + clamp((e.clientX - rect.left) / rect.width, 0, 1) * (max - min)); };
  track.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    rect = track.getBoundingClientRect();
    try { track.setPointerCapture(e.pointerId); } catch (err) { /* synthetic event */ }
    el.classList.add('dragging');
    el.focus({ preventScroll: true });
    fromPointer(e);
    e.preventDefault();
  });
  track.addEventListener('pointermove', (e) => { if (el.classList.contains('dragging')) fromPointer(e); });
  const end = () => { el.classList.remove('dragging'); rect = null; };
  track.addEventListener('pointerup', end);
  track.addEventListener('pointercancel', end);
  el.addEventListener('dblclick', () => { if (opts.def !== undefined) commit(opts.def); });
  el._adjust = (dir, big) => commit(value + dir * step * (big ? 5 : 1));
  paint();
  return { el, get: () => value, set: (v) => { value = clamp(Number(v) || 0, min, max); paint(); } };
}

/** Stepper (◄ value ►). opts: { choices:[[value,label]], value, onChange(v) } */
export function stepper(opts) {
  const choices = opts.choices || [];
  let idx = Math.max(0, choices.findIndex((c) => c[0] === opts.value));
  const label = h('span.v-stepper-label');
  const pips = h('span.v-stepper-pips', null, choices.map(() => h('i')));
  const go = (dir) => {
    if (!choices.length) return;
    idx = (idx + dir + choices.length) % choices.length;
    paint();
    if (opts.onChange) opts.onChange(choices[idx][0]);
  };
  const prev = h('button.v-stepper-arrow', { tabindex: -1, type: 'button', 'aria-label': 'Précédent', html: '<svg viewBox="0 0 12 12"><path d="M8 1.5 3.5 6 8 10.5"/></svg>', onclick: (e) => { e.stopPropagation(); go(-1); } });
  const next = h('button.v-stepper-arrow', { tabindex: -1, type: 'button', 'aria-label': 'Suivant', html: '<svg viewBox="0 0 12 12"><path d="M4 1.5 8.5 6 4 10.5"/></svg>', onclick: (e) => { e.stopPropagation(); go(1); } });
  const el = h('div.v-stepper', { nav: true, tabindex: 0, role: 'listbox' }, prev, h('span.v-stepper-mid', null, label, pips), next);
  const paint = () => {
    label.textContent = choices[idx] ? choices[idx][1] : '—';
    for (let i = 0; i < pips.children.length; i++) pips.children[i].className = i === idx ? 'on' : '';
  };
  el.addEventListener('click', () => go(1));
  el._adjust = (dir) => go(dir);
  paint();
  return { el, get: () => (choices[idx] ? choices[idx][0] : undefined), set: (v) => { const i = choices.findIndex((c) => c[0] === v); if (i >= 0) { idx = i; paint(); } } };
}

/** Toggle switch. opts: { value, onChange(bool) } */
export function toggle(opts) {
  let value = !!opts.value;
  const label = h('span.v-toggle-label');
  const el = h('div.v-toggle', { nav: true, tabindex: 0, role: 'switch' }, h('span.v-toggle-box', null, h('i')), label);
  const paint = () => { el.classList.toggle('on', value); el.setAttribute('aria-checked', value); label.textContent = value ? 'Activé' : 'Désactivé'; };
  const set = (v, fire = true) => { v = !!v; if (v === value) return; value = v; paint(); if (fire && opts.onChange) opts.onChange(value); };
  el.addEventListener('click', () => set(!value));
  el._adjust = (dir) => set(dir > 0);
  el._activate = () => set(!value);
  paint();
  return { el, get: () => value, set: (v) => { value = !!v; paint(); } };
}

/** A row of exclusive choice chips. opts: { choices:[[value,label]], value, onChange(v), cls } */
export function chips(opts) {
  let value = opts.value;
  const el = h('div.v-chips' + (opts.cls ? '.' + opts.cls : ''));
  const btns = (opts.choices || []).map(([v, label]) => {
    const b = h('button.v-chip', { nav: true, type: 'button', text: label, onclick: () => { value = v; paint(); if (opts.onChange) opts.onChange(v); } });
    b._v = v; el.appendChild(b); return b;
  });
  const paint = () => { for (const b of btns) b.classList.toggle('on', b._v === value); };
  paint();
  return { el, get: () => value, set: (v) => { value = v; paint(); } };
}

/** Colour swatches. opts: { colors:[hex], value, onChange(hex) } */
export function swatches(opts) {
  let value = opts.value;
  const el = h('div.v-swatches');
  const btns = (opts.colors || []).map((c) => {
    const b = h('button.v-swatch', { nav: true, type: 'button', title: c, 'aria-label': 'Couleur ' + c, style: { '--c': c }, onclick: () => { value = c; paint(); if (opts.onChange) opts.onChange(c); } });
    b.style.setProperty('--c', c);
    b._v = c; el.appendChild(b); return b;
  });
  const paint = () => { const lv = String(value || '').toLowerCase(); for (const b of btns) b.classList.toggle('on', b._v.toLowerCase() === lv); };
  paint();
  return { el, get: () => value, set: (v) => { value = v; paint(); } };
}

/** like Element.append, but flattens arrays and skips null / false children */
export function add(el, ...kids) { return append(el, kids); }
