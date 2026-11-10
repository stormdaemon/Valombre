// VALOMBRE UI — in-game HUD. Everything here is refreshed from update(): values are cached and the DOM is only
// touched when something changed; moving widgets use transforms; no node is created in the frame loop.
import { bus } from '../core/events.js';
import { add, h, clear, clamp, num, hourStr } from './dom.js';
import { icon, itemIcon, skillIcon, SKILL_TINT, STATUS_GLYPH, BUFFS } from './icons.js';
import { ITEMS, itemName } from '../game/data/items.js';
import { SKILLS, STATUS, xpForLevel } from '../game/data/rules.js';

const EBARS = 14, DMG = 24, CMARKS = 12, MAX_TOASTS = 6;
const COMPASS_W = 30;          // rem
const COMPASS_SPAN = 120;      // degrees visible
const RAD = 180 / Math.PI;
const MARK_GLYPH = { shrine: 'flame', quest: 'diamond', poi: 'pin', boss: 'skull' };

const mkBar = (cls) => {
  const ghost = h('i.v-bar-ghost'), fill = h('i.v-bar-fill'), numEl = h('span.v-bar-num');
  return { el: h('div.v-bar.' + cls, null, ghost, fill, h('i.v-bar-gloss'), numEl), ghost, fill, num: numEl, r: -1, gr: -1, gv: 1, last: 1, hold: 0, w: -1, n: '' };
};

function setFill(b, r) {
  if (Math.abs(r - b.r) > 0.0012 || (r === 0 && b.r !== 0) || (r === 1 && b.r !== 1)) { b.r = r; b.fill.style.transform = `scaleX(${r.toFixed(4)})`; }
}

/** delayed "ghost" bar behind a fill */
function setGhost(b, r, dt) {
  if (r >= b.gv) { b.gv = r; b.hold = 0; }
  else {
    if (r < b.last - 0.0005) b.hold = 0.55;
    b.hold -= dt;
    if (b.hold <= 0) b.gv = Math.max(r, b.gv - dt * 0.5);
  }
  b.last = r;
  if (Math.abs(b.gv - b.gr) > 0.0012) { b.gr = b.gv; b.ghost.style.transform = `scaleX(${b.gv.toFixed(4)})`; }
}

export class Hud {
  constructor(ui) {
    this.ui = ui; this.app = ui.app;
    this.el = h('div.v-hud', { hidden: true });
    ui.hudLayer.appendChild(this.el);
    this.visible = false;
    this._scr = { x: 0, y: 0, visible: false };
    this._wp = { x: 0, y: 0, z: 0 };
    this._build();
    this._readSettings();
    const on = (t, fn) => bus.on(t, (a) => { try { fn(a); } catch (e) { console.error('[hud] ' + t, e); } });
    on('toast', (o) => this._toast(o));
    on('damage', (o) => this._damage(o));
    on('discover', (o) => this._queue(this.areaQ, o));
    on('banner', (o) => this._queue(this.bannerQ, o));
    on('boss:start', () => { this.boss.force = 1; });
    on('boss:end', () => { this.boss.force = 0; });
    on('boss:phase', (o) => { if (o && o.text) this._subtitle(o.text, 5, true); });
    on('player:hurt', (dmg) => this._hurt(dmg));
    on('subtitle', (o) => { if (o && o.text) this._subtitle(o.text, o.time || 4, false); });
    on('lock', () => { this.reticle.x = -1e9; });
  }

  // ------------------------------------------------------------------------------------------ build
  _build() {
    const el = this.el;
    // screen-space overlays
    this.lowEl = h('div.v-lowhp');
    this.hurtEl = h('div.v-hurt');
    // world anchored
    this.world = h('div.v-world');
    this.ebars = [];
    for (let i = 0; i < EBARS; i++) {
      const b = mkBar('enemy');
      const name = h('span.v-ebar-name');
      const node = h('div.v-ebar', null, name, b.el);
      this.world.appendChild(node);
      this.ebars.push({ el: node, bar: b, name, e: null, on: false, x: -1e9, y: -1e9, fade: false, vuln: false, lock: false });
    }
    this._ebarN = 0;
    this.reticle = { el: h('div.v-reticle', { html: '<svg viewBox="0 0 48 48"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="square"><path d="M24 4l5 5M24 4l-5 5M24 44l5-5M24 44l-5-5M4 24l5 5M4 24l5-5M44 24l-5 5M44 24l-5-5"/><circle cx="24" cy="24" r="2.2" fill="currentColor" stroke="none"/></g></svg>' }), on: false, x: -1e9, y: -1e9 };
    this.world.appendChild(this.reticle.el);
    this.dmg = [];
    for (let i = 0; i < DMG; i++) {
      const txt = h('span');
      const node = h('div.v-dmg', null, txt);
      this.world.appendChild(node);
      this.dmg.push({ el: node, txt, on: false, t: 0, x: 0, y: 0, z: 0, sx: -1e9, sy: -1e9, jx: 0, anim: null });
    }
    this._dmgI = 0; this._dmgOn = 0;

    // compass
    const strip = h('div.v-compass-strip');
    const per = COMPASS_W / COMPASS_SPAN;
    for (let deg = -90; deg <= 450; deg += 15) {
      const a = ((deg % 360) + 360) % 360;
      const left = ((deg + 90) * per).toFixed(3) + 'rem';
      if (a % 90 === 0) strip.appendChild(h('span.v-compass-card', { style: { left }, text: ['S', 'O', 'N', 'E'][a / 90] }));
      else if (a % 45 === 0) strip.appendChild(h('span.v-compass-inter', { style: { left }, text: { 45: 'SO', 135: 'NO', 225: 'NE', 315: 'SE' }[a] }));
      else strip.appendChild(h('i.v-compass-tick', { style: { left } }));
    }
    this.cmarks = [];
    const marks = h('div.v-compass-marks');
    for (let i = 0; i < CMARKS; i++) {
      const ico = h('span.v-cmark-ico'), dist = h('span.v-cmark-dist');
      const node = h('div.v-cmark', null, ico, dist);
      marks.appendChild(node);
      this.cmarks.push({ el: node, ico, dist, on: false, kind: '', x: -1e9, edge: false, d: '' });
    }
    this._cmarkN = 0;
    this.compassSub = h('div.v-compass-sub');
    this.compass = { el: h('div.v-compass', null, h('div.v-compass-clip', null, strip, marks), h('i.v-compass-needle'), this.compassSub), strip, x: -1e9, sub: '', shown: null };

    // vitals
    this.hp = mkBar('hp'); this.st = mkBar('st'); this.mp = mkBar('mp');
    this.flask = { count: h('span.v-flask-count', { text: '0' }), key: h('kbd.v-key.sm'), n: -1, max: -1, el: null };
    this.flask.el = h('div.v-flask', null, h('span.v-flask-ico', { html: icon('flask') }), this.flask.count, this.flask.key);
    this.xp = { fill: h('i'), level: h('span.v-xp-level'), r: -1, lv: -1, pts: -1, ptsEl: h('span.v-xp-points') };
    this.vitals = h('div.v-vitals', null, this.flask.el,
      h('div.v-vital-bars', null, this.hp.el, this.st.el, this.mp.el,
        h('div.v-xp', null, this.xp.level, h('div.v-xp-bar', null, this.xp.fill), this.xp.ptsEl)));

    // status build-ups and buffs
    this.statuses = {};
    const fx = h('div.v-effects');
    for (const k in STATUS) {
      const fill = h('i');
      const node = h('div.v-status', { 'data-status': k, style: { '--c': STATUS[k].color } }, h('span.v-status-ico', { html: icon(STATUS_GLYPH[k] || 'drop') }), h('div.v-status-body', null, h('span.v-status-name', { text: STATUS[k].name }), h('div.v-status-bar', null, fill)));
      node.style.setProperty('--c', STATUS[k].color);
      fx.appendChild(node);
      this.statuses[k] = { el: node, fill, on: false, r: -1, active: null };
    }
    this.buffs = {};
    const bf = h('div.v-buffs');
    for (const k in BUFFS) {
      const t = h('span.v-buff-t');
      const node = h('div.v-buff', { title: BUFFS[k].name, style: { color: BUFFS[k].color } }, h('span.v-buff-ico', { html: icon(BUFFS[k].glyph) }), t);
      bf.appendChild(node);
      this.buffs[k] = { el: node, t, on: false, n: -1 };
    }
    // lit torch / auto-travel: same chips as the buffs, with their key below
    this.tools = {};
    for (const [k, glyph, color, name, action] of [['torch', 'flame', '#f2a04e', 'Torche allumée', 'torch'], ['auto', 'compass', '#e3c47c', 'Déplacement automatique vers l\'objectif', 'autoTravel']]) {
      const t = h('span.v-buff-t');
      const node = h('div.v-buff', { title: name, style: { color } }, h('span.v-buff-ico', { html: icon(glyph) }), t);
      bf.appendChild(node);
      this.tools[k] = { el: node, t, on: false, action };
    }
    fx.appendChild(bf);
    this.effects = fx;

    // quick bar: weapon, shield, skills
    this.gear = { weapon: h('div.v-quick-item'), offhand: h('div.v-quick-item'), sig: null };
    this.skills = [];
    const skillsEl = h('div.v-skills');
    for (let i = 0; i < 3; i++) {
      const ico = h('span.v-skill-ico'), cd = h('i.v-skill-cd'), cdt = h('span.v-skill-cdt'), key = h('kbd.v-key.sm'), cost = h('span.v-skill-cost');
      const node = h('div.v-skill.empty', null, ico, cd, cdt, cost, key);
      skillsEl.appendChild(node);
      this.skills.push({ el: node, ico, cd, cdt, key, cost, id: undefined, r: -1, n: '', low: null, ready: null });
    }
    this.quick = h('div.v-quick', null, h('div.v-quick-gear', null, this.gear.weapon, this.gear.offhand), skillsEl);

    // boss
    this.boss = { bar: mkBar('boss'), name: h('span.v-boss-name'), title: h('span.v-boss-title'), el: null, on: false, ref: null, force: 0, phase: -1 };
    this.boss.el = h('div.v-boss', null, h('div.v-boss-head', null, this.boss.name, this.boss.title), this.boss.bar.el);

    // prompt, subtitle
    this.prompt = { key: h('kbd.v-key'), label: h('span'), el: null, on: false, k: '', l: '' };
    this.prompt.el = h('div.v-prompt', null, this.prompt.key, this.prompt.label);
    this.sub = { el: null, txt: h('span'), t: 0, on: false };
    this.sub.el = h('div.v-subtitle', null, this.sub.txt);

    // toasts, tracker, banners, perf
    this.toastEl = h('div.v-toasts');
    this.toasts = [];
    this.tracker = { title: h('div.v-tracker-title'), step: h('div.v-tracker-step'), el: null, dirty: true };
    this.tracker.el = h('div.v-tracker', { hidden: true }, h('div.v-tracker-kicker', null, h('span', { html: icon('diamond') }), 'Quête suivie'), this.tracker.title, this.tracker.step);
    this.area = { name: h('div.v-area-name'), sub: h('div.v-area-sub'), el: null, t: 0, on: false };
    this.area.el = h('div.v-area', null, this.area.name, h('div.v-rule'), this.area.sub);
    this.areaQ = [];
    this.banner = { title: h('div.v-banner-title'), sub: h('div.v-banner-sub'), el: null, t: 0, on: false };
    this.banner.el = h('div.v-banner', null, h('div.v-banner-band', null, this.banner.title, this.banner.sub));
    this.bannerQ = [];
    this.perf = { el: h('div.v-perf', { hidden: true }), t: 0, s: '' };

    add(el, this.lowEl, this.hurtEl, this.world, this.compass.el, this.tracker.el, this.vitals, this.effects, this.quick, this.boss.el,
      this.prompt.el, this.sub.el, this.toastEl, this.area.el, this.banner.el, this.perf.el);
  }

  // -------------------------------------------------------------------------------------- plumbing
  _readSettings() {
    const s = (k, d) => this.ui.setting(k, d);
    this.sCompass = s('compass', true) !== false;
    this.sTracker = s('questTracker', true) !== false;
    this.sBars = s('enemyBars', true) !== false;
    this.sDmg = s('damageNumbers', true) !== false;
    this.sSubs = s('subtitles', true) !== false;
    this.sPerf = !!s('showFps', false);
    this.sCalm = !!s('reduceFlashes', false);
    this.compass.el.hidden = !this.sCompass;
    this.perf.el.hidden = !this.sPerf;
    this.el.classList.toggle('calm', this.sCalm);
    this.tracker.dirty = true;
  }

  onSettings() { this._readSettings(); }
  onBinds() { this._keys = true; }
  onResize() { this.compass.x = -1e9; for (const m of this.cmarks) m.x = -1e9; }
  onHint(type) {
    if (type === 'quest') this.tracker.dirty = true;
    else if (type === 'inventory' || type === 'player:stats') this.gear.sig = null;
  }

  reset() {
    for (const t of this.toasts) t.el.remove();
    this.toasts.length = 0;
    this.areaQ.length = 0; this.bannerQ.length = 0;
    this.area.t = 0; this.banner.t = 0; this.sub.t = 0;
    this._off(this.area); this._off(this.banner); this._off(this.sub);
    this.boss.force = 0; this.boss.ref = null;
    this.gear.sig = null; this.tracker.dirty = true; this._keys = true;
    this.hp.gv = 1; this.hp.last = 1;
    this.el.classList.remove('low', 'dead');
  }

  setVisible(v) {
    v = !!v;
    if (v === this.visible) return;
    this.visible = v;
    this.el.hidden = !v;
    if (v) { this.gear.sig = null; this.tracker.dirty = true; this._keys = true; }
  }

  _off(o) { if (o.on) { o.on = false; o.el.classList.remove('on'); } }
  _on(o) { if (!o.on) { o.on = true; o.el.classList.add('on'); } }

  // --------------------------------------------------------------------------------------- events
  _queue(q, o) { if (o && q.length < 4) q.push(o); }

  _hurt(dmg) {
    if (!this.visible) return;
    const el = this.hurtEl;
    try {
      if (this._hurtAnim) this._hurtAnim.cancel();
      const a = this.sCalm ? 0.22 : clamp(0.35 + (Number(dmg) || 0) / 120, 0.35, 0.8);
      this._hurtAnim = el.animate([{ opacity: a }, { opacity: 0 }], { duration: 520, easing: 'ease-out' });
    } catch (e) { /* Web Animations unavailable */ }
  }

  _subtitle(text, time, strong) {
    if (!this.sSubs && !strong) return;
    this.sub.txt.textContent = text;
    this.sub.el.classList.toggle('strong', !!strong);
    this.sub.t = clamp(time, 1.5, 14);
    this._on(this.sub);
  }

  _damage(o) {
    if (!o || !this.sDmg || !this.visible) return;
    const s = this.dmg[this._dmgI];
    this._dmgI = (this._dmgI + 1) % DMG;
    s.x = o.x || 0; s.y = o.y || 0; s.z = o.z || 0; s.t = 0; s.sx = -1e9;
    s.jx = (Math.random() - 0.5) * 2.6 * this.ui.rem;
    s.txt.textContent = String(Math.max(1, Math.round(o.dmg || 0)));
    s.el.className = 'v-dmg on' + (o.crit ? ' crit' : '') + (o.blocked ? ' blocked' : '');
    s.on = true;
    try {
      if (s.anim) s.anim.cancel();
      const up = (o.crit ? 3.4 : 2.6) * this.ui.rem;
      s.anim = s.txt.animate([
        { transform: 'translate3d(0,0,0) scale(.6)', opacity: 0 },
        { transform: `translate3d(0,${(-up * 0.35).toFixed(1)}px,0) scale(${o.crit ? 1.25 : 1.05})`, opacity: 1, offset: 0.14 },
        { transform: `translate3d(0,${(-up * 0.8).toFixed(1)}px,0) scale(1)`, opacity: 1, offset: 0.7 },
        { transform: `translate3d(0,${(-up).toFixed(1)}px,0) scale(.94)`, opacity: 0 },
      ], { duration: o.crit ? 1100 : 900, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'forwards' });
    } catch (e) { /* Web Animations unavailable */ }
    s.life = o.crit ? 1.1 : 0.9;
  }

  _toast(o) {
    if (!o || !o.kind) return;
    let ico = '', label = '', text = '', cls = o.kind, life = 3.6;
    const merge = (o.kind === 'gold' || o.kind === 'xp') ? this.toasts.find((t) => t.kind === o.kind && t.t < t.life - 0.4) : null;
    if (merge) {
      merge.n += Number(o.n) || 0; merge.t = Math.min(merge.t, 0.4);
      merge.text.textContent = o.kind === 'gold' ? `+${num(merge.n)} pièces d'or` : `+${num(merge.n)} expérience`;
      try { merge.el.animate([{ filter: 'brightness(1.7)' }, { filter: 'brightness(1)' }], { duration: 300, easing: 'ease-out' }); } catch (e) { /* no WAAPI */ }
      return;
    }
    switch (o.kind) {
      case 'item': { const def = ITEMS[o.id]; ico = itemIcon(o.id); label = 'Objet obtenu'; text = (def ? def.name : String(o.id)) + ((o.qty || 1) > 1 ? ' ×' + o.qty : ''); break; }
      case 'gold': ico = icon('coin'); text = `+${num(Number(o.n) || 0)} pièces d'or`; life = 2.8; break;
      case 'xp': ico = icon('attributes'); text = `+${num(Number(o.n) || 0)} expérience`; life = 2.8; break;
      case 'level': ico = icon('attributes'); label = 'Niveau supérieur'; text = `Niveau ${o.level} atteint`; life = 5; break;
      case 'quest': ico = icon(o.done ? 'check' : 'quest'); label = o.done ? 'Quête accomplie' : 'Nouvelle quête'; text = o.title || ''; life = 5; cls += o.done ? ' done' : ''; break;
      case 'skill': { const sk = SKILLS[o.id]; ico = skillIcon(o.id); label = 'Pouvoir d\'Éclat acquis'; text = sk ? sk.name : String(o.id); life = 5.5; break; }
      default: text = o.text || ''; cls = 'text';
    }
    if (!text) return;
    const textEl = h('span.v-toast-text', { text });
    const node = h('div.v-toast.' + cls.split(' ').join('.'), null,
      ico ? h('span.v-toast-ico', { html: ico }) : null,
      h('span.v-toast-body', null, label ? h('span.v-toast-label', { text: label }) : null, textEl));
    this.toastEl.appendChild(node);
    this.toasts.push({ el: node, text: textEl, kind: o.kind, n: Number(o.n) || 0, t: 0, life, out: false });
    while (this.toasts.length > MAX_TOASTS) { const old = this.toasts.shift(); old.el.remove(); }
  }

  // --------------------------------------------------------------------------------------- update
  update(dt, g) {
    if (!this.visible || !g) return;
    const p = g.player;
    if (!p || !p.data) return;
    const d = p.data, st = p.st || {}, rem = this.ui.rem;

    // ---- vitals
    const maxHp = p.maxHp || st.maxHp || 1, hp = clamp(p.hp || 0, 0, maxHp);
    const maxSt = st.maxSt || 1, maxMp = st.maxMana || 1;
    this._width(this.hp, clamp(6 + maxHp * 0.036, 8, 27));
    this._width(this.st, clamp(5 + maxSt * 0.05, 7, 22));
    this._width(this.mp, clamp(4.5 + maxMp * 0.06, 6, 20));
    const hr = hp / maxHp;
    setFill(this.hp, hr); setGhost(this.hp, hr, dt);
    const hn = Math.ceil(hp) + ' / ' + Math.round(maxHp);
    if (hn !== this.hp.n) { this.hp.n = hn; this.hp.num.textContent = hn; }
    const sr = clamp((d.stamina || 0) / maxSt, 0, 1);
    setFill(this.st, sr);
    const tired = (d.stamina || 0) <= 0;
    if (tired !== this.st.tired) { this.st.tired = tired; this.st.el.classList.toggle('empty', tired); }
    setFill(this.mp, clamp((d.mana || 0) / maxMp, 0, 1));
    const low = hr < 0.25 && !p.dead;
    if (low !== this._low) { this._low = low; this.el.classList.toggle('low', low); }
    const dead = !!p.dead;
    if (dead !== this._dead) { this._dead = dead; this.el.classList.toggle('dead', dead); }

    // flask, level, xp
    const f = this.flask;
    if (d.flasks !== f.n || d.flaskMax !== f.max) { f.n = d.flasks; f.max = d.flaskMax; f.count.textContent = String(d.flasks ?? 0); f.el.classList.toggle('empty', !(d.flasks > 0)); }
    const x = this.xp;
    if (d.level !== x.lv) { x.lv = d.level; x.level.textContent = 'Niv. ' + (d.level || 1); x.need = xpForLevel(d.level || 1) || 1; }
    const xr = clamp((d.xp || 0) / (x.need || 1), 0, 1);
    if (Math.abs(xr - x.r) > 0.002) { x.r = xr; x.fill.style.transform = `scaleX(${xr.toFixed(3)})`; }
    if (d.attrPoints !== x.pts) { x.pts = d.attrPoints; x.ptsEl.textContent = d.attrPoints > 0 ? `+${d.attrPoints} point${d.attrPoints > 1 ? 's' : ''}` : ''; }

    if (this._keys) { this._keys = false; this._paintKeys(); }

    // ---- status build-ups and buffs
    const ps = p.status || null, thr = p.statusThreshold || 30;
    for (const k in this.statuses) {
      const s = this.statuses[k], v = ps ? ps[k] : null;
      let show = false, r = 0, active = false;
      if (v) {
        if (v.t > 0) { show = true; active = true; const tt = STATUS[k].time || 0; r = tt > 0 ? clamp(v.t / tt, 0, 1) : 1; }
        else if (v.build > 0) { show = true; r = clamp(v.build / thr, 0, 1); }
      }
      if (show !== s.on) { s.on = show; s.el.classList.toggle('on', show); }
      if (!show) continue;
      if (active !== s.active) { s.active = active; s.el.classList.toggle('active', active); }
      if (Math.abs(r - s.r) > 0.004) { s.r = r; s.fill.style.transform = `scaleX(${r.toFixed(3)})`; }
    }
    const pb = p.buffs || null;
    for (const k in this.buffs) {
      const s = this.buffs[k], v = pb ? pb[k] : null;
      const show = !!v && v.t > 0;
      if (show !== s.on) { s.on = show; s.el.classList.toggle('on', show); }
      if (!show) continue;
      const n = Math.ceil(v.t);
      if (n !== s.n) { s.n = n; s.t.textContent = n + ' s'; s.el.classList.toggle('ending', n <= 5); }
    }

    for (const k in this.tools) {
      const s = this.tools[k], show = k === 'torch' ? !!d.torchLit : !!(g.auto && g.auto.active);
      if (show !== s.on) { s.on = show; s.el.classList.toggle('on', show); }
    }

    // ---- quick bar
    const eq = d.equipment || {};
    const sig = (eq.weapon ? eq.weapon.id + ':' + (eq.weapon.up || 0) : '-') + '|' + (eq.offhand ? eq.offhand.id + ':' + (eq.offhand.up || 0) : '-');
    if (sig !== this.gear.sig) { this.gear.sig = sig; this._paintGear(eq); }
    const slots = d.skillSlots || [], cds = p.skillCd || null;
    for (let i = 0; i < 3; i++) {
      const s = this.skills[i], id = slots[i] || null;
      if (id !== s.id) this._paintSkill(s, id);
      if (!id) continue;
      const sk = SKILLS[id];
      const cd = cds && cds[id] > 0 ? cds[id] : 0;
      const r = sk && sk.cd > 0 ? clamp(cd / sk.cd, 0, 1) : 0;
      if (Math.abs(r - s.r) > 0.004 || (r === 0 && s.r !== 0)) { s.r = r; s.cd.style.transform = `scaleY(${r.toFixed(3)})`; }
      const n = cd > 0 ? (cd < 9.5 ? cd.toFixed(cd < 3 ? 1 : 0) : String(Math.ceil(cd))) : '';
      if (n !== s.n) { s.n = n; s.cdt.textContent = n; }
      const lowM = !!sk && (d.mana || 0) < sk.cost;
      if (lowM !== s.low) { s.low = lowM; s.el.classList.toggle('nomana', lowM); }
      const ready = cd <= 0 && !lowM;
      if (ready !== s.ready) {
        if (ready && s.ready === false) { try { s.el.animate([{ filter: 'brightness(2.2)' }, { filter: 'brightness(1)' }], { duration: 420, easing: 'ease-out' }); } catch (e) { /* no WAAPI */ } }
        s.ready = ready;
      }
    }

    // ---- compass
    if (this.sCompass) this._compass(g, p, rem);

    // ---- world anchored widgets
    this._world(dt, g, p);

    // ---- boss bar
    const b = g.boss || null, B = this.boss;
    if (b) {
      if (b !== B.ref) {
        B.ref = b;
        B.name.textContent = (b.def && b.def.name) || '';
        B.title.textContent = (b.def && b.def.title) || '';
        B.bar.gv = 1; B.bar.last = 1; B.phase = -1;
      }
      const r = clamp((b.hp || 0) / (b.maxHp || 1), 0, 1);
      setFill(B.bar, r); setGhost(B.bar, r, dt);
      if (b.phase !== B.phase) { B.phase = b.phase; B.el.classList.toggle('enraged', (b.phase || 1) > 1); }
      this._on(B);
    } else { B.ref = null; this._off(B); }

    // ---- interaction prompt
    const fo = g.focus || null, P = this.prompt;
    if (fo && fo.label && !dead) {
      const key = fo.key || this.ui.keyLabel('interact');
      if (key !== P.k) { P.k = key; P.key.textContent = key; }
      if (fo.label !== P.l) { P.l = fo.label; P.label.textContent = fo.label; }
      this._on(P);
    } else this._off(P);

    // ---- timed widgets
    if (this.sub.on) { this.sub.t -= dt; if (this.sub.t <= 0) this._off(this.sub); }
    this._timed(this.area, this.areaQ, dt, 4.6, (o) => { this.area.name.textContent = o.name || ''; this.area.sub.textContent = o.sub || ''; this.area.sub.hidden = !o.sub; });
    this._timed(this.banner, this.bannerQ, dt, 4.4, (o) => { this.banner.title.textContent = o.title || ''; this.banner.sub.textContent = o.sub || ''; this.banner.el.dataset.kind = o.kind || 'shrine'; });
    for (let i = this.toasts.length - 1; i >= 0; i--) {
      const t = this.toasts[i];
      t.t += dt;
      if (!t.out && t.t > t.life - 0.35) { t.out = true; t.el.classList.add('out'); }
      if (t.t > t.life) { t.el.remove(); this.toasts.splice(i, 1); }
    }

    // ---- quest tracker, perf
    if (this.tracker.dirty) { this.tracker.dirty = false; this._paintTracker(g); }
    if (this.sPerf) {
      this.perf.t -= dt;
      if (this.perf.t <= 0) { this.perf.t = 0.5; this._paintPerf(); }
    }
  }

  _width(b, w) {
    if (Math.abs(w - b.w) < 0.02) return;
    b.w = w; b.el.style.width = w.toFixed(2) + 'rem';
  }

  _timed(o, q, dt, life, paint) {
    if (o.on) { o.t -= dt; if (o.t <= 0) this._off(o); return; }
    if (o.t > -0.5) { o.t -= dt; return; }          // short gap between two banners
    if (q.length) { paint(q.shift()); o.t = life; this._on(o); }
  }

  _paintKeys() {
    this.flask.key.textContent = this.ui.keyLabel('flask');
    for (let i = 0; i < 3; i++) this.skills[i].key.textContent = this.ui.keyLabel('skill' + (i + 1));
    for (const k in this.tools) this.tools[k].t.textContent = this.ui.keyLabel(this.tools[k].action);
    this.prompt.k = '';
  }

  _paintGear(eq) {
    const paint = (el, inst, empty) => {
      if (inst) { el.innerHTML = itemIcon(inst.id) + (inst.up ? `<span class="v-up">+${inst.up}</span>` : ''); el.title = itemName(inst); el.classList.remove('empty'); }
      else { el.innerHTML = `<span class="v-item-ico ghost">${icon(empty)}</span>`; el.title = ''; el.classList.add('empty'); }
    };
    paint(this.gear.weapon, eq.weapon, 'sword');
    paint(this.gear.offhand, eq.offhand, 'shield');
  }

  _paintSkill(s, id) {
    s.id = id; s.r = -1; s.n = null; s.low = null; s.ready = null;
    const sk = id ? SKILLS[id] : null;
    s.el.classList.toggle('empty', !id);
    s.el.classList.remove('nomana', 'flash');
    if (!id) { s.ico.innerHTML = ''; s.cdt.textContent = ''; s.cost.textContent = ''; s.cd.style.transform = 'scaleY(0)'; s.el.title = ''; return; }
    s.ico.innerHTML = skillIcon(id);
    s.ico.style.color = SKILL_TINT[id] || '';
    s.cost.textContent = sk ? String(sk.cost) : '';
    s.el.title = sk ? sk.name : id;
  }

  _paintTracker(g) {
    const T = this.tracker;
    let q = null;
    if (this.sTracker && g.quests && typeof g.quests.list === 'function') {
      try { const list = g.quests.list() || []; q = list.find((x) => x.tracked && x.state === 'active') || null; } catch (e) { q = null; }
    }
    if (!q) { T.el.hidden = true; return; }
    const step = (q.steps || []).find((s) => !s.done);
    T.title.textContent = q.title || '';
    T.step.textContent = step ? step.text : 'Objectif accompli';
    T.el.classList.toggle('main', !!q.main);
    T.el.hidden = false;
  }

  _paintPerf() {
    let s = '';
    try {
      const p = typeof this.app.perf === 'function' ? this.app.perf() : null;
      if (p) s = `${Math.round(p.fps || 0)} ips · ${num(p.ms || 0, 1)} ms\n${p.res ? p.res[0] + '×' + p.res[1] : ''} (${Math.round((p.scale || 1) * 100)} %)\n${num(p.calls || 0)} appels · ${num((p.tris || 0) / 1000)} k tri.`;
    } catch (e) { s = ''; }
    if (s !== this.perf.s) { this.perf.s = s; this.perf.el.textContent = s; }
  }

  _compass(g, p, rem) {
    let c = null;
    try { c = typeof g.compass === 'function' ? g.compass() : null; } catch (e) { c = null; }
    if (!c) return;
    const C = this.compass, W = COMPASS_W * rem, ppd = W / COMPASS_SPAN;
    const yawDeg = (c.yaw || 0) * RAD;
    const phi = (((-yawDeg) % 360) + 360) % 360;
    const x = Math.round((W * 0.5 - (phi + 90) * ppd) * 2) / 2;
    if (x !== C.x) { C.x = x; C.strip.style.transform = `translate3d(${x}px,0,0)`; }
    const list = c.markers || [], px = p.pos ? p.pos.x : 0, pz = p.pos ? p.pos.z : 0;
    let n = 0;
    const half = COMPASS_SPAN * 0.5 - 3;
    for (let i = 0; i < list.length && n < CMARKS; i++) {
      const m = list[i];
      if (!m) continue;
      const dx = m.x - px, dz = m.z - pz;
      let delta = (Math.atan2(dx, dz) - (c.yaw || 0)) * RAD;
      delta = ((delta + 180) % 360 + 360) % 360 - 180;
      const edge = Math.abs(delta) > half;
      const cl = clamp(delta, -half, half);
      const mx = Math.round((W * 0.5 - cl * ppd) * 2) / 2;
      const s = this.cmarks[n++];
      if (!s.on) { s.on = true; s.el.classList.add('on'); }
      if (m.kind !== s.kind) { s.kind = m.kind; s.ico.innerHTML = icon(MARK_GLYPH[m.kind] || 'pin'); s.el.dataset.kind = m.kind || 'poi'; }
      if (mx !== s.x) { s.x = mx; s.el.style.transform = `translate3d(${mx}px,0,0)`; }
      if (edge !== s.edge) { s.edge = edge; s.el.classList.toggle('edge', edge); }
      let dtxt = '';
      if (m.kind === 'quest') { const dist = Math.hypot(dx, dz); dtxt = dist >= 1000 ? num(dist / 1000, 1) + ' km' : Math.round(dist / 5) * 5 + ' m'; }
      if (dtxt !== s.d) { s.d = dtxt; s.dist.textContent = dtxt; }
    }
    for (let i = n; i < this._cmarkN; i++) { const s = this.cmarks[i]; if (s.on) { s.on = false; s.el.classList.remove('on'); } }
    this._cmarkN = n;
    // region and time of day under the strip
    const hour = typeof g.hour === 'number' ? g.hour : null;
    const bucket = hour === null ? -1 : Math.floor(hour * 6);
    const rn = g.region && g.region.name ? g.region.name : '';
    if (bucket !== C.bucket || rn !== C.rn) {
      C.bucket = bucket; C.rn = rn;
      const txt = [rn, hour === null ? '' : hourStr(Math.floor(hour * 6) / 6)].filter(Boolean).join('  ·  ');
      if (txt !== C.sub) { C.sub = txt; this.compassSub.textContent = txt; }
    }
  }

  _world(dt, g, p) {
    const can = typeof g.toScreen === 'function';
    const out = this._scr, v = this._wp;
    let n = 0;
    const list = g.enemies;
    if (can && this.sBars && list) {
      for (let i = 0; i < list.length && n < EBARS; i++) {
        const e = list[i];
        if (!e || e.dead || e.isBoss || !(e.barT > 0) || !e.pos) continue;
        v.x = e.pos.x; v.y = e.pos.y + (e.height || 1.8) + 0.3; v.z = e.pos.z;
        g.toScreen(v, out);
        if (!out.visible) continue;
        const s = this.ebars[n++];
        const r = clamp((e.hp || 0) / (e.maxHp || 1), 0, 1);
        if (s.e !== e) { s.e = e; s.bar.gv = r; s.bar.last = r; s.name.textContent = (e.def && e.def.name) || ''; }
        if (!s.on) { s.on = true; s.el.classList.add('on'); }
        const sx = Math.round(out.x * 2) / 2, sy = Math.round(out.y * 2) / 2;
        if (sx !== s.x || sy !== s.y) { s.x = sx; s.y = sy; s.el.style.transform = `translate3d(${sx}px,${sy}px,0)`; }
        setFill(s.bar, r); setGhost(s.bar, r, dt);
        const fade = e.barT < 0.6;
        if (fade !== s.fade) { s.fade = fade; s.el.classList.toggle('fade', fade); }
        const vuln = e.vulnerableT > 0;
        if (vuln !== s.vuln) { s.vuln = vuln; s.el.classList.toggle('vuln', vuln); }
        const lock = p.target === e;
        if (lock !== s.lock) { s.lock = lock; s.el.classList.toggle('lock', lock); }
      }
    }
    for (let i = n; i < this._ebarN; i++) { const s = this.ebars[i]; if (s.on) { s.on = false; s.e = null; s.el.classList.remove('on'); } }
    this._ebarN = n;

    // lock-on reticle
    const R = this.reticle, t = p.target;
    let show = false;
    if (can && t && !t.dead && t.pos) {
      v.x = t.pos.x; v.y = t.pos.y + (t.height || 1.8) * 0.62; v.z = t.pos.z;
      g.toScreen(v, out);
      if (out.visible) {
        show = true;
        const sx = Math.round(out.x * 2) / 2, sy = Math.round(out.y * 2) / 2;
        if (sx !== R.x || sy !== R.y) { R.x = sx; R.y = sy; R.el.style.transform = `translate3d(${sx}px,${sy}px,0)`; }
      }
    }
    if (show !== R.on) { R.on = show; R.el.classList.toggle('on', show); }

    // damage numbers
    for (let i = 0; i < DMG; i++) {
      const s = this.dmg[i];
      if (!s.on) continue;
      s.t += dt;
      if (s.t >= s.life || !can) { s.on = false; s.el.className = 'v-dmg'; continue; }
      v.x = s.x; v.y = s.y; v.z = s.z;
      g.toScreen(v, out);
      const sx = Math.round(out.x + s.jx), sy = Math.round(out.y);
      if (sx !== s.sx || sy !== s.sy) { s.sx = sx; s.sy = sy; s.el.style.transform = `translate3d(${sx}px,${sy}px,0)`; }
    }
  }
}
