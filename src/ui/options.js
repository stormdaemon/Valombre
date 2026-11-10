// VALOMBRE UI — options (generated from SETTINGS_SCHEMA) + key bindings + benchmark.
import { add, h, clear, num, slider, stepper, toggle } from './dom.js';
import { icon } from './icons.js';
import { Screen, panel, rule, hint } from './screen.js';
import { SETTINGS_SCHEMA, ACTIONS } from '../core/settings.js';

const TAB_ICON = { graphics: 'screen', audio: 'sound', controls: 'gamepad', gameplay: 'sword', access: 'access', keys: 'keyboard' };
const PRESET_LABEL = { low: 'Bas', medium: 'Moyen', high: 'Élevé', ultra: 'Ultra' };
const ACTION_GROUPS = [
  ['Déplacement', ['forward', 'back', 'left', 'right', 'sprint', 'dodge', 'jump']],
  ['Combat', ['attack', 'heavy', 'block', 'lock', 'skill1', 'skill2', 'skill3', 'flask', 'sheathe']],
  ['Monde et interface', ['interact', 'inventory', 'map', 'journal', 'character', 'pause', 'hideHud']],
];

export class OptionsScreen extends Screen {
  constructor(ui) {
    super(ui, 'options', 'v-options');
    this.tab = 'graphics';
    this.rows = [];
    this.tabsEl = h('nav.v-tabs-v');
    this.listEl = h('div.v-options-list.v-scroll');
    this.actionsEl = h('div.v-options-actions');
    this.descTitle = h('h4.v-desc-title');
    this.descText = h('p.v-desc-text');
    this.descDef = h('p.v-desc-def');
    this.descExtra = h('div.v-desc-extra');
    this.tabs = {};
    const tabs = [...SETTINGS_SCHEMA.map((c) => [c.id, c.label]), ['keys', 'Clavier / souris']];
    for (const [id, label] of tabs) {
      const b = h('button.v-tab-v', { nav: true, type: 'button', onclick: () => this.setTab(id), onfocus: () => this.setTab(id) }, h('span.v-tab-ico', { html: icon(TAB_ICON[id] || 'gear') }), h('span', { text: label }));
      this.tabs[id] = b;
      this.tabsEl.appendChild(b);
    }
    add(this.el, h('div.v-dim'),
      panel('v-options-panel',
        h('div.v-panel-head', null, h('h2.v-panel-title', { text: 'Options' }), h('button.v-close', { type: 'button', 'aria-label': 'Fermer', html: icon('cross'), onclick: () => ui.back() })),
        rule(),
        h('div.v-options-body', null,
          this.tabsEl,
          h('div.v-options-main', null, this.listEl, this.actionsEl),
          h('aside.v-options-desc', null, h('i.v-desc-orn', { html: icon('attributes') }), this.descTitle, this.descText, this.descDef, this.descExtra)),
        h('div.v-panel-foot', null, hint('↑ ↓', 'Naviguer'), hint('← →', 'Modifier'), hint('Échap', 'Retour'))));
    this._benchState = '';
  }

  get settings() { return this.app.settings; }

  onOpen() { this._built = null; this.setTab(this.tab, true); }
  defaultFocus() { return this.tabs[this.tab]; }
  onEvent(type) {
    if (type === 'settings') this._refresh();
    else if (type === 'binds' && this.tab === 'keys' && !this.ui.capturing) this._buildKeys(true);
  }
  onBack() {
    if (this.ui.capturing) return true;
    return false;
  }

  setTab(id, force) {
    if (!force && id === this.tab && this._built === id) return;
    this.tab = id; this._built = id;
    for (const k in this.tabs) this.tabs[k].classList.toggle('on', k === id);
    this.listEl.scrollTop = 0;
    if (id === 'keys') this._buildKeys(); else this._buildCategory(id);
  }

  _describe(title, text, def, extra) {
    this.descTitle.textContent = title || '';
    this.descText.textContent = text || '';
    this.descDef.textContent = def ? 'Par défaut : ' + def : '';
    if (extra !== undefined) { clear(this.descExtra); if (extra) add(this.descExtra, extra); }
  }

  // ----------------------------------------------------------------------------------- categories
  _fmtDefault(o) {
    if (o.type === 'toggle') return o.def ? 'Activé' : 'Désactivé';
    if (o.type === 'slider') return num(o.def) + (o.unit || '');
    const c = (o.choices || []).find((x) => x[0] === o.def);
    return c ? c[1] : String(o.def);
  }

  _buildCategory(id) {
    const cat = SETTINGS_SCHEMA.find((c) => c.id === id);
    const s = this.settings;
    clear(this.listEl); clear(this.actionsEl);
    this.rows = [];
    if (!cat || !s) return;
    this.listEl.classList.remove('keys');
    const generic = { slider: 'Faites glisser ou utilisez ← → pour ajuster la valeur.', select: 'Utilisez ← → pour changer de valeur.', toggle: 'Entrée ou clic pour basculer.' };
    for (const o of cat.options) {
      let ctl;
      const set = (v) => { try { s.set(o.key, v); } catch (e) { console.error(e); } this._refresh(o.key); };
      if (o.type === 'slider') ctl = slider({ min: o.min, max: o.max, step: o.step, value: s.get(o.key), def: o.def, unit: o.unit, onInput: (v) => { set(v); this.ui.sfx('ui_slider'); } });
      else if (o.type === 'toggle') ctl = toggle({ value: s.get(o.key), onChange: set });
      else ctl = stepper({ choices: o.choices, value: s.get(o.key), onChange: set });
      const describe = () => {
        this._describe(o.label, o.desc || generic[o.type], this._fmtDefault(o), this._extraFor(id));
        for (const r of this.rows) r.el.classList.toggle('hot', r.o === o);
      };
      const row = h('div.v-opt', { onmouseenter: describe }, h('span.v-opt-label', { text: o.label }), h('span.v-opt-ctl', null, ctl.el));
      ctl.el.addEventListener('focus', describe);
      this.listEl.appendChild(row);
      this.rows.push({ o, ctl, el: row });
    }
    if (id === 'graphics') {
      this.benchBtn = h('button.v-btn', { nav: true, type: 'button', onclick: () => this._benchmark() }, h('span.v-btn-ico', { html: icon('clock') }), 'Tester ma machine');
      this.actionsEl.appendChild(this.benchBtn);
    }
    this.actionsEl.appendChild(h('button.v-btn.ghost', { nav: true, type: 'button', onclick: () => this._reset(cat) }, h('span.v-btn-ico', { html: icon('undo') }), 'Réinitialiser'));
    this._describe(cat.label, { graphics: 'Qualité de l\'image et performances. Les changements s\'appliquent immédiatement.', audio: 'Volumes de la musique, des effets et des voix.', controls: 'Souris, caméra et manette.', gameplay: 'Difficulté et aides de jeu.', access: 'Lisibilité et confort.' }[id] || '', '', this._extraFor(id));
  }

  _extraFor(id) {
    if (id !== 'graphics') return null;
    const box = h('div.v-desc-gpu');
    if (this.app.gpu) add(box, h('span.v-desc-k', { text: 'Carte graphique' }), h('span.v-desc-v', { text: String(this.app.gpu) }));
    if (this._benchState) add(box, h('span.v-desc-k', { text: 'Test de performances' }), h('span.v-desc-v.bench', { text: this._benchState }));
    return box.childNodes.length ? box : null;
  }

  _refresh() {
    const s = this.settings;
    if (!s || this.tab === 'keys') return;
    for (const r of this.rows) { try { r.ctl.set(s.get(r.o.key)); } catch (e) { /* unknown key */ } }
  }

  async _reset(cat) {
    const ok = await this.ui.confirm({ title: `Réinitialiser « ${cat.label} » ?`, text: 'Les réglages de cette catégorie reprendront leur valeur par défaut.', yes: 'Réinitialiser', no: 'Annuler' });
    if (!ok) return;
    try { this.settings.resetCategory(cat.id); } catch (e) { console.error(e); }
    this._refresh();
  }

  async _benchmark() {
    if (this._benching || typeof this.app.benchmark !== 'function') return;
    this._benching = true;
    this.benchBtn.disabled = true; this.benchBtn.classList.add('busy');
    this._benchState = 'Mesure en cours…';
    this._describe('Tester ma machine', 'Valombre mesure la cadence de votre carte graphique pendant quelques secondes, puis règle le préréglage « Automatique » en conséquence.', '', this._extraFor('graphics'));
    let res = null;
    try { res = await this.app.benchmark(); } catch (e) { console.error('[ui] benchmark', e); }
    this._benching = false;
    if (this.benchBtn) { this.benchBtn.disabled = false; this.benchBtn.classList.remove('busy'); }
    this._benchState = res && res.preset ? `Préréglage conseillé : ${PRESET_LABEL[res.preset] || res.preset} (${Math.round(res.fps || 0)} images/s)` : 'Le test n\'a pas pu aboutir.';
    this.ui.sfx(res ? 'ui_save' : 'ui_error');
    if (this.isOpen && this.tab === 'graphics') {
      this._refresh();
      this._describe('Tester ma machine', res ? 'Le préréglage « Automatique » utilise désormais ce résultat.' : '', '', this._extraFor('graphics'));
    }
  }

  // ---------------------------------------------------------------------------------- key bindings
  _buildKeys(keepScroll) {
    const s = this.settings, inp = this.app.input;
    const top = keepScroll ? this.listEl.scrollTop : 0;
    const focus = keepScroll && document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.bind : null;
    clear(this.listEl); clear(this.actionsEl);
    this.rows = [];
    this.listEl.classList.add('keys');
    if (!s || !s.binds) return;
    const labelOf = (code) => { try { return inp.label(code); } catch (e) { return code || '—'; } };
    const names = {}; for (const [id, label] of ACTIONS) names[id] = label;
    this.listEl.appendChild(h('div.v-bind-head', null, h('span', { text: 'Action' }), h('span', { text: 'Touche principale' }), h('span', { text: 'Touche secondaire' })));
    const seen = new Set();
    const addRow = (id) => {
      if (!names[id] || seen.has(id)) return;
      seen.add(id);
      const binds = s.binds[id] || [];
      const row = h('div.v-bind-row' + (binds.length ? '' : '.unbound'), null, h('span.v-opt-label', { text: names[id] }));
      for (let slot = 0; slot < 2; slot++) {
        const code = binds[slot];
        const b = h('button.v-bind' + (code ? '' : '.unset'), { nav: true, type: 'button', 'data-bind': id + ':' + slot, text: code ? labelOf(code) : (!binds.length && slot === 0 ? 'Non assignée' : '—') });
        b.addEventListener('click', () => this._capture(id, slot, b));
        b.addEventListener('focus', () => this._describe(names[id], 'Entrée ou clic, puis appuyez sur la touche ou le bouton de souris voulu. Échap annule. Suppr retire l\'assignation.', '', null));
        b._bind = { id, slot };
        row.appendChild(b);
      }
      this.listEl.appendChild(row);
    };
    for (const [title, ids] of ACTION_GROUPS) {
      this.listEl.appendChild(h('div.v-bind-group', { text: title }));
      ids.forEach(addRow);
    }
    const rest = ACTIONS.map((a) => a[0]).filter((id) => !seen.has(id));
    if (rest.length) { this.listEl.appendChild(h('div.v-bind-group', { text: 'Autres' })); rest.forEach(addRow); }
    this.actionsEl.appendChild(h('button.v-btn.ghost', { nav: true, type: 'button', onclick: async () => {
      const ok = await this.ui.confirm({ title: 'Rétablir les commandes par défaut ?', yes: 'Rétablir', no: 'Annuler' });
      if (!ok) return;
      try { s.resetBinds(); } catch (e) { console.error(e); }
      this._buildKeys();
      this._describe('Clavier / souris', 'Commandes par défaut rétablies.', '', null);
    } }, h('span.v-btn-ico', { html: icon('undo') }), 'Commandes par défaut'));
    if (!keepScroll) this._describe('Clavier / souris', 'Deux touches peuvent être assignées à chaque action. Une touche ne peut servir qu\'à une seule action : la réassigner la retire de l\'ancienne.', '', null);
    this.listEl.scrollTop = top;
    if (focus) { const b = this.listEl.querySelector(`[data-bind="${focus}"]`); if (b) b.focus({ preventScroll: true }); }
  }

  _capture(action, slot, btn) {
    const inp = this.app.input, s = this.settings, ui = this.ui;
    if (!inp || ui.capturing) return;
    ui.capturing = true;
    btn.classList.add('listening');
    btn.textContent = 'Appuyez sur une touche…';
    const names = {}; for (const [id, label] of ACTIONS) names[id] = label;
    let done = false;
    const onMouse = (e) => {
      // the Input only sees mouse buttons on the canvas: handle them here while a panel covers it
      e.preventDefault(); e.stopPropagation();
      if (inp.capture) inp.capture = null;
      const swallow = (ev) => { ev.preventDefault(); ev.stopPropagation(); };
      window.addEventListener('click', swallow, { capture: true, once: true });
      window.addEventListener('auxclick', swallow, { capture: true, once: true });
      setTimeout(() => { window.removeEventListener('click', swallow, true); window.removeEventListener('auxclick', swallow, true); }, 350);
      finish('Mouse' + e.button);
    };
    const finish = (code) => {
      if (done) return;
      done = true;
      window.removeEventListener('mousedown', onMouse, true);
      setTimeout(() => { ui.capturing = false; }, 0);
      let msg = code ? '' : 'Assignation annulée.';
      if (code) {
        let stolen = '';
        for (const id in s.binds) if (id !== action && (s.binds[id] || []).includes(code)) stolen = names[id] || id;
        try { s.setBind(action, slot, code); } catch (e) { console.error(e); }
        let lab = code; try { lab = inp.label(code); } catch (e) { /* keep code */ }
        msg = stolen ? `« ${lab} » était assignée à « ${stolen} » : cette assignation a été retirée.` : `« ${lab} » assignée à « ${names[action] || action} ».`;
        ui.sfx('ui_equip');
      } else ui.sfx('ui_back');
      this._buildKeys(true);
      this._describe(names[action] || action, msg, '', null);
      const again = this.listEl.querySelector(`[data-bind="${action}:${Math.min(slot, Math.max(0, (s.binds[action] || []).length - 1))}"]`) || this.listEl.querySelector(`[data-bind="${action}:${slot}"]`);
      if (again) again.focus({ preventScroll: true });
    };
    inp.capture = (code) => finish(code);
    window.addEventListener('mousedown', onMouse, true);
  }

  onKey(e) {
    if (this.tab !== 'keys' || (e.code !== 'Delete' && e.code !== 'Backspace')) return false;
    const a = document.activeElement, b = a && a._bind, s = this.settings;
    if (!b || !s) return false;
    const list = s.binds[b.id] || [];
    if (!list[b.slot]) return true;
    if (list.length <= 1) { this._describe('Assignation requise', 'Chaque action doit garder au moins une touche.', '', null); this.ui.sfx('ui_error'); return true; }
    try { s.setBind(b.id, b.slot, null); } catch (err) { console.error(err); }
    this._buildKeys(true);
    return true;
  }
}
