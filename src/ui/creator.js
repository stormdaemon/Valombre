// VALOMBRE UI — character creator. Left: tabs and controls, centre: free for the 3D preview, right: origin card.
import { add, h, clear, num, slider, chips, swatches } from './dom.js';
import { icon, itemIcon, skillIcon } from './icons.js';
import { Screen, panel, rule, hint } from './screen.js';
import {
  SKIN_TONES, HAIR_COLORS, EYE_COLORS, PAINT_COLORS, HAIR_STYLES, BEARD_STYLES, PAINT_STYLES, SCAR_STYLES, VOICES,
  MORPH_FALLBACK, PRESETS, defaultAppearance, randomAppearance,
} from '../game/data/creator.js';
import { ORIGINS, ATTRS, SKILLS, derive } from '../game/data/rules.js';
import { ITEMS } from '../game/data/items.js';

const TABS = [
  ['origin', 'Origine', 'body', 'quest'], ['body', 'Corps', 'body', 'person'], ['head', 'Tête', 'face', 'helm'], ['eyes', 'Yeux', 'face', 'eye'],
  ['nose', 'Nez', 'face', 'drop'], ['mouth', 'Bouche', 'face', 'speech'], ['jaw', 'Mâchoire', 'face', 'shield'], ['ears', 'Oreilles', 'face', 'sound'],
  ['skin', 'Peau & pilosité', 'face', 'feather'], ['marks', 'Marques', 'face', 'attributes'], ['voice', 'Voix & nom', 'face', 'book'],
];
const SLOT_LABEL = { weapon: 'Arme', offhand: 'Bouclier', head: 'Tête', chest: 'Torse', legs: 'Jambes' };

const clone = (a) => ({ ...defaultAppearance(), ...(a || {}), morphs: { ...((a && a.morphs) || {}) } });

export class CreatorScreen extends Screen {
  constructor(ui) {
    super(ui, 'creator', 'v-creator', { root: true });
    this.tab = 'origin';
    this.origin = ORIGINS[0].id;
    this.charName = 'Veilleur';
    this.view = 'body';
    this._local = defaultAppearance();
    this.tabBtns = {};

    // ---- left column
    this.tabsEl = h('nav.v-creator-tabs');
    for (const [id, label, , glyph] of TABS) {
      const b = h('button.v-ctab', { nav: true, type: 'button', onclick: () => this.setTab(id), onfocus: () => this.setTab(id) }, h('span.v-ctab-ico', { html: icon(glyph) }), h('span', { text: label }));
      this.tabBtns[id] = b; this.tabsEl.appendChild(b);
    }
    this.contentTitle = h('h3.v-creator-section');
    this.content = h('div.v-creator-content.v-scroll');
    const left = panel('v-creator-left',
      h('div.v-creator-head', null, h('span.v-kicker', { text: 'Nouvelle partie' }), h('h2', { text: 'Création du personnage' })),
      rule(),
      h('div.v-creator-cols', null, this.tabsEl, h('div.v-creator-pane', null, this.contentTitle, this.content)),
      h('div.v-creator-tip', { text: 'Double-clic sur une réglette pour la réinitialiser.' }));

    // ---- centre stage (kept free for the 3D preview)
    this.viewChips = chips({ cls: 'seg', choices: [['body', 'Corps'], ['face', 'Visage']], value: 'body', onChange: (v) => this.setView(v) });
    const presetRow = h('div.v-creator-presets', null, h('span.v-kicker', { text: 'Modèles' }),
      PRESETS.map((p) => h('button.v-chip', { nav: true, type: 'button', text: p.label, onclick: () => this._preset(p) })));
    this.stage = h('div.v-creator-stage', null,
      h('div.v-creator-drag', { title: '' }),
      h('div.v-creator-viewbar', null, this.viewChips.el, h('span.v-creator-draghint', null, h('span', { html: icon('rotate') }), 'Glisser pour tourner · Molette pour changer de vue')),
      h('div.v-creator-tools', null, presetRow,
        h('div.v-creator-toolbtns', null,
          h('button.v-btn', { nav: true, type: 'button', onclick: () => this._random() }, h('span.v-btn-ico', { html: icon('dice') }), 'Aléatoire'),
          h('button.v-btn.ghost', { nav: true, type: 'button', onclick: () => this._reset() }, h('span.v-btn-ico', { html: icon('undo') }), 'Réinitialiser'))));
    this._bindStage(this.stage.firstChild);

    // ---- right column
    this.nameEl = h('button.v-creator-name', { type: 'button', title: 'Modifier le nom', onclick: () => { this.setTab('voice'); const i = this.content.querySelector('input'); if (i) i.focus(); } });
    this.originEl = h('div.v-origin-card.v-scroll');
    this.startBtn = h('button.v-btn.primary.big', { nav: true, type: 'button', onclick: () => this._start() }, 'Commencer l\'aventure');
    this.startHint = h('div.v-creator-starthint');
    const right = panel('v-creator-right',
      h('div.v-creator-head', null, h('span.v-kicker', { text: 'Votre Veilleur' }), this.nameEl),
      rule(), this.originEl,
      h('div.v-creator-foot', null, this.startHint, this.startBtn,
        h('button.v-btn.ghost', { nav: true, type: 'button', text: 'Retour au menu', onclick: () => this._leave() })));

    add(this.el, left, this.stage, right);
  }

  // ------------------------------------------------------------------------------------- creator API
  get creator() { return this.app.creator || null; }
  get A() { const c = this.creator; return (c && c.appearance) || this._local; }
  get morphList() { const c = this.creator; return c && Array.isArray(c.morphs) && c.morphs.length ? c.morphs : MORPH_FALLBACK; }
  _call(fn, ...args) { const c = this.creator; try { if (c && typeof c[fn] === 'function') c[fn](...args); } catch (e) { console.error('[ui] creator.' + fn, e); } }
  _set(key, v) { this._local[key] = v; this._call('set', key, v); }
  _setMorph(name, v) { this._local.morphs[name] = v; this._call('setMorph', name, v); }
  _setAll(a) { this._local = clone(a); this._call('setAll', clone(a)); this._buildTab(); }

  onOpen() {
    const c = this.creator;
    this._local = clone(c && c.appearance);
    this.charName = 'Veilleur';
    this.origin = ORIGINS[0].id;
    this.tab = 'origin';
    this._call('setOrigin', this.origin);
    this.setTab('origin', true);
    this._paintOrigin();
    this._paintName();
  }
  defaultFocus() { return this.tabBtns[this.tab]; }

  setView(v, fromTab) {
    if (v !== 'face' && v !== 'body') return;
    if (v === this.view && !fromTab) return;
    this.view = v;
    this.viewChips.set(v);
    this._call('setView', v);
  }

  setTab(id, force) {
    if (id === this.tab && !force) return;
    this.tab = id;
    const def = TABS.find((t) => t[0] === id) || TABS[0];
    for (const k in this.tabBtns) this.tabBtns[k].classList.toggle('on', k === id);
    this.contentTitle.textContent = def[1];
    this.setView(def[2], true);
    this._buildTab();
  }

  // ------------------------------------------------------------------------------------------ tabs
  _row(label, ctl, cls) { return h('div.v-crow' + (cls ? '.' + cls : ''), null, h('span.v-crow-label', { text: label }), ctl); }
  _sec(text) { return h('h5.v-csec', { text }); }

  _morphRows(cat) {
    const A = this.A, out = [];
    for (const m of this.morphList) {
      if (!m || m.category !== cat) continue;
      const def = m.default ?? 0;
      const s = slider({ min: m.min ?? -1, max: m.max ?? 1, step: 0.02, def, value: (A.morphs && A.morphs[m.name]) ?? def, format: (v) => String(Math.round(v * 100)), onInput: (v) => this._setMorph(m.name, v) });
      out.push(this._row(m.label || m.name, s.el));
    }
    return out;
  }

  _buildTab() {
    const c = this.content, A = this.A, id = this.tab;
    clear(c);
    c.scrollTop = 0;
    if (id === 'origin') {
      for (const o of ORIGINS) {
        const parts = o.desc.split(/(?<=[.!?…])\s+/);
        const b = h('button.v-origin-pick' + (o.id === this.origin ? '.on' : ''), { nav: true, type: 'button', onclick: () => this._pickOrigin(o.id) },
          h('span.v-origin-pick-ico', { html: itemIcon(o.gear.weapon) }),
          h('span.v-origin-pick-body', null, h('span.v-origin-pick-name', { text: o.name }), h('span.v-origin-pick-tag', { text: parts[parts.length - 1] })));
        b._origin = o.id;
        c.appendChild(b);
      }
      return;
    }
    if (id === 'body') {
      const s = slider({ min: 0.9, max: 1.1, step: 0.005, def: 1, value: A.height ?? 1, format: (v) => Math.round(v * 176) + ' cm', onInput: (v) => this._set('height', v) });
      add(c, this._row('Stature', s.el), this._morphRows('body'));
      return;
    }
    if (id === 'skin') {
      add(c, 
        this._sec('Teint'), swatches({ colors: SKIN_TONES, value: A.skin, onChange: (v) => this._set('skin', v) }).el,
        this._sec('Coiffure'), chips({ choices: HAIR_STYLES, value: A.hair, onChange: (v) => this._set('hair', v) }).el,
        this._sec('Couleur des cheveux'), swatches({ colors: HAIR_COLORS, value: A.hairColor, onChange: (v) => this._set('hairColor', v) }).el,
        this._sec('Barbe'), chips({ choices: BEARD_STYLES, value: A.beard, onChange: (v) => this._set('beard', v) }).el,
        this._sec('Sourcils'), this._row('Épaisseur', slider({ min: 0, max: 1, step: 0.02, def: 0.5, value: A.brows ?? 0.5, format: (v) => String(Math.round(v * 100)), onInput: (v) => this._set('brows', v) }).el));
      return;
    }
    if (id === 'marks') {
      add(c, 
        this._sec('Peinture de guerre'), chips({ choices: PAINT_STYLES, value: A.paint, onChange: (v) => this._set('paint', v) }).el,
        this._sec('Couleur de la peinture'), swatches({ colors: PAINT_COLORS, value: A.paintColor, onChange: (v) => this._set('paintColor', v) }).el,
        this._sec('Cicatrice'), chips({ choices: SCAR_STYLES, value: A.scar, onChange: (v) => this._set('scar', v) }).el);
      return;
    }
    if (id === 'voice') {
      const input = h('input.v-input', { type: 'text', maxlength: 18, spellcheck: 'false', autocomplete: 'off', placeholder: 'Veilleur', value: this.charName, 'data-nav': '' });
      input.value = this.charName;
      input.addEventListener('input', () => { this.charName = input.value; this._paintName(); });
      const nearest = (v) => { let b = VOICES[0]; for (const x of VOICES) if (Math.abs(x[0] - v) < Math.abs(b[0] - v)) b = x; return b; };
      let fine = null;
      const vc = chips({ choices: VOICES, value: nearest(A.voice ?? 1)[0], onChange: (v) => { this._set('voice', v); if (fine) fine.set(v); this._call('playVoice'); } });
      fine = slider({ min: 0.7, max: 1.4, step: 0.01, def: 1, value: A.voice ?? 1, format: (v) => nearest(v)[1], onInput: (v) => { this._set('voice', v); vc.set(nearest(v)[0]); } });
      add(c, 
        this._sec('Nom'), input, h('p.v-cnote', { text: 'Le nom que les survivants de Valombre vous donneront.' }),
        this._sec('Voix'), vc.el, this._row('Hauteur', fine.el),
        h('button.v-btn', { nav: true, type: 'button', onclick: () => this._call('playVoice') }, h('span.v-btn-ico', { html: icon('sound') }), 'Écouter'));
      return;
    }
    // morph categories: head, eyes, nose, mouth, jaw, ears
    if (id === 'eyes') add(c, this._sec('Couleur des yeux'), swatches({ colors: EYE_COLORS, value: A.eyeColor, onChange: (v) => this._set('eyeColor', v) }).el, this._sec('Forme'));
    const rows = this._morphRows(id);
    if (rows.length) add(c, rows); else add(c, h('p.v-cnote', { text: 'Aucun réglage disponible pour cette partie.' }));
  }

  // ---------------------------------------------------------------------------------------- origin
  _pickOrigin(id) {
    this.origin = id;
    this._call('setOrigin', id);
    for (const b of this.content.querySelectorAll('.v-origin-pick')) b.classList.toggle('on', b._origin === id);
    this._paintOrigin();
  }

  _paintOrigin() {
    const o = ORIGINS.find((x) => x.id === this.origin) || ORIGINS[0];
    const el = this.originEl;
    clear(el);
    let st = null;
    try { const eq = { weapon: null, offhand: null, head: null, chest: null, legs: null }; for (const s in o.gear) eq[s] = { id: o.gear[s], up: 0 }; st = derive({ attrs: o.attrs, equipment: eq }); } catch (e) { st = null; }
    const attrs = h('div.v-origin-attrs', null, ATTRS.map(([key, label, desc]) => {
      const v = o.attrs[key] || 0;
      return h('div.v-origin-attr', { title: desc }, h('span.v-origin-attr-name', { text: label }), h('span.v-origin-attr-bar', null, h('i', { style: { width: Math.min(100, (v / 18) * 100).toFixed(1) + '%' } })), h('span.v-origin-attr-val', { text: String(v) }));
    }));
    const gear = h('div.v-origin-gear', null, Object.keys(SLOT_LABEL).filter((s) => o.gear[s]).map((s) => {
      const def = ITEMS[o.gear[s]];
      return h('div.v-origin-item', null, h('span', { html: itemIcon(o.gear[s], 'sm') }), h('span.v-origin-item-name', { text: def ? def.name : o.gear[s] }), h('span.v-origin-item-slot', { text: SLOT_LABEL[s] }));
    }));
    const extras = [];
    for (const [id, qty] of o.items || []) { const def = ITEMS[id]; extras.push(h('div.v-origin-item', null, h('span', { html: itemIcon(id, 'sm') }), h('span.v-origin-item-name', { text: (def ? def.name : id) + (qty > 1 ? ' ×' + qty : '') }))); }
    if (o.skill && SKILLS[o.skill]) extras.push(h('div.v-origin-item.eclat', null, h('span.v-item-ico.sm.r-eclat', { html: skillIcon(o.skill) }), h('span.v-origin-item-name', { text: SKILLS[o.skill].name }), h('span.v-origin-item-slot', { text: 'Pouvoir d\'Éclat' })));
    extras.push(h('div.v-origin-item', null, h('span.v-item-ico.sm.r-gold', { html: icon('coin') }), h('span.v-origin-item-name', { text: o.gold > 0 ? `${o.gold} pièces d'or` : 'Sans le sou' })));
    add(el, 
      h('h3.v-origin-name', { text: o.name }),
      h('p.v-origin-desc', { text: o.desc }),
      h('h5.v-csec', { text: 'Attributs de départ' }), attrs,
      st ? h('div.v-origin-derived', null,
        h('span', null, h('b', { text: String(st.maxHp) }), ' Vie'), h('span', null, h('b', { text: String(st.maxSt) }), ' Souffle'), h('span', null, h('b', { text: String(st.maxMana) }), ' Éclat')) : null,
      h('h5.v-csec', { text: 'Équipement de départ' }), gear, extras);
    el.scrollTop = 0;
  }

  _paintName() {
    const n = this.charName.trim();
    this.nameEl.textContent = n || 'Sans nom';
    this.nameEl.classList.toggle('missing', !n);
    this.startBtn.disabled = !n;
    this.startHint.textContent = n ? '' : 'Donnez un nom à votre personnage (onglet « Voix & nom »).';
  }

  // --------------------------------------------------------------------------------------- actions
  _preset(p) { this._setAll({ ...defaultAppearance(), ...p.a, morphs: { ...(p.a.morphs || {}) } }); this.ui.sfx('ui_equip'); }
  _random() { let a; try { a = randomAppearance(this.morphList); } catch (e) { a = defaultAppearance(); } this._setAll(a); this.ui.sfx('ui_equip'); }
  async _reset() {
    const ok = await this.ui.confirm({ title: 'Réinitialiser l\'apparence ?', text: 'Tous les réglages reprendront leur valeur par défaut.', yes: 'Réinitialiser', no: 'Annuler' });
    if (ok) this._setAll(defaultAppearance());
  }
  async _leave() {
    const ok = await this.ui.confirm({ title: 'Abandonner la création ?', text: 'Votre personnage ne sera pas conservé.', yes: 'Retour au menu', no: 'Continuer' });
    if (ok) { try { this.app.quitToTitle(); } catch (e) { console.error(e); } }
  }
  onBack() { this._leave(); return true; }

  _start() {
    const name = this.charName.trim();
    if (!name) { this.ui.sfx('ui_error'); this._paintName(); return; }
    const a = clone(this.A);
    try { this.app.startNewGame({ name, origin: this.origin, appearance: a }); } catch (e) { console.error('[ui] startNewGame', e); }
  }

  // ----------------------------------------------------------------------------------------- stage
  _bindStage(zone) {
    let drag = false, lastX = 0, wheelT = 0;
    zone.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      drag = true; lastX = e.clientX;
      try { zone.setPointerCapture(e.pointerId); } catch (err) { /* synthetic */ }
      zone.classList.add('dragging');
      if (document.activeElement && document.activeElement.tagName === 'INPUT') document.activeElement.blur();
    });
    zone.addEventListener('pointermove', (e) => {
      if (!drag) return;
      const dx = e.clientX - lastX; lastX = e.clientX;
      if (dx) this._call('rotate', dx * 0.011);
    });
    const end = () => { drag = false; zone.classList.remove('dragging'); };
    zone.addEventListener('pointerup', end);
    zone.addEventListener('pointercancel', end);
    zone.addEventListener('wheel', (e) => {
      e.preventDefault();
      const now = performance.now();
      if (now - wheelT < 220) return;
      wheelT = now;
      this.setView(e.deltaY < 0 ? 'face' : 'body');
    }, { passive: false });
  }

  onKey(e) {
    // Q / E style rotation with the keyboard while no slider is focused
    if (e.code === 'PageUp') { this._call('rotate', -0.35); return true; }
    if (e.code === 'PageDown') { this._call('rotate', 0.35); return true; }
    return false;
  }
}
