// VALOMBRE UI — title screen, save slots, credits.
import { add, h, clear, playtime, dateStr } from './dom.js';
import { icon, EMBLEM } from './icons.js';
import { Screen, panel, rule, hint } from './screen.js';
import { creditsBlocks } from './overlays.js';
import { ORIGINS } from '../game/data/rules.js';

const originName = (id) => { const o = ORIGINS.find((x) => x.id === id); return o ? o.name : ''; };

function savesList(app) {
  try { const l = app.saves && app.saves.list ? app.saves.list() : []; return Array.isArray(l) ? l : []; } catch (e) { return []; }
}
function latestSlot(app) {
  try { const n = app.saves && app.saves.latest ? app.saves.latest() : -1; return typeof n === 'number' ? n : -1; } catch (e) { return -1; }
}

// ------------------------------------------------------------------------------------------ title
export class TitleScreen extends Screen {
  constructor(ui) {
    super(ui, 'title', 'v-title', { root: true });
    this.menu = h('nav.v-menu.v-title-menu');
    this.bye = h('div.v-title-bye', { hidden: true }, h('p', { text: 'Que la Braise veille sur vous.' }), h('span', { text: 'Vous pouvez fermer cet onglet.' }));
    add(this.el, 
      h('div.v-title-shade'),
      h('header.v-title-head', null,
        h('div.v-title-emblem', { html: EMBLEM }),
        h('h1.v-title-name', { text: 'VALOMBRE' }),
        h('div.v-title-rule', null, h('i')),
        h('p.v-title-sub', { text: 'Les Éclats de l\'Aube' })),
      this.menu,
      h('footer.v-title-foot', null,
        h('span.v-title-version', { text: 'Version ' + (this.app.version || '0.9') + ' — Aubeclair' }),
        h('span.v-title-hints', null, hint('↑ ↓', 'Naviguer'), hint('Entrée', 'Valider'))),
      this.bye);
  }
  onOpen() { this.bye.hidden = true; this._build(); }
  onResume() { this._build(); }
  _build() {
    const app = this.app, ui = this.ui;
    clear(this.menu);
    const item = (label, fn, sub) => {
      const b = h('button.v-menu-item', { nav: true, type: 'button', onclick: fn }, h('i.v-menu-mark'), h('span.v-menu-label', { text: label }), sub ? h('span.v-menu-sub', { text: sub }) : null);
      this.menu.appendChild(b);
      return b;
    };
    const latest = latestSlot(app);
    if (latest >= 0) {
      const s = savesList(app).find((x) => x.slot === latest);
      const sub = s && !s.empty ? [s.name, s.level ? 'Niv. ' + s.level : '', s.region].filter(Boolean).join(' · ') : '';
      item('Continuer', () => { try { app.continueGame(); } catch (e) { console.error(e); } }, sub);
    }
    item('Nouvelle partie', () => { try { app.openCreator(); } catch (e) { console.error(e); } });
    const anySave = savesList(app).some((s) => !s.empty);
    const load = item('Charger', () => ui.open('saves', { mode: 'load' }));
    if (!anySave) load.disabled = true;
    item('Options', () => ui.open('options'));
    item('Crédits', () => ui.open('credits'));
    item('Quitter le jeu', async () => {
      const ok = await ui.confirm({ title: 'Quitter Valombre ?', yes: 'Quitter', no: 'Rester' });
      if (!ok) return;
      try { window.close(); } catch (e) { /* not allowed */ }
      setTimeout(() => { this.bye.hidden = false; }, 150);
    });
  }
  onKey() { if (!this.bye.hidden) { this.bye.hidden = true; return true; } return false; }
}

// ------------------------------------------------------------------------------------------ saves
export class SavesScreen extends Screen {
  constructor(ui) {
    super(ui, 'saves', 'v-saves');
    this.mode = 'load';
    this.title = h('h2.v-panel-title');
    this.list = h('div.v-saves-list');
    this.msg = h('div.v-saves-msg');
    add(this.el, h('div.v-dim'),
      panel('v-saves-panel',
        h('div.v-panel-head', null, this.title, h('button.v-close', { type: 'button', 'aria-label': 'Fermer', html: icon('cross'), onclick: () => ui.back() })),
        rule(), this.list, this.msg,
        h('div.v-panel-foot', null, hint('Entrée', 'Choisir'), hint('Suppr', 'Effacer'), hint('Échap', 'Retour'))));
  }
  onOpen(o = {}) { this.mode = o.mode === 'save' ? 'save' : 'load'; this.msg.textContent = ''; this._build(); }
  _build() {
    const save = this.mode === 'save';
    this.title.textContent = save ? 'Sauvegarder la partie' : 'Charger une partie';
    clear(this.list);
    const slots = savesList(this.app);
    for (let n = 0; n < 4; n++) {
      const s = slots.find((x) => x.slot === n) || { slot: n, empty: true };
      const auto = n === 0;
      const disabled = save ? auto : s.empty;
      const row = h('button.v-save' + (s.empty ? '.empty' : '') + (auto ? '.auto' : ''), { nav: true, type: 'button', 'data-slot': n, onclick: () => this._pick(s) },
        h('span.v-save-slot', null, h('span.v-save-ico', { html: icon(auto ? 'flame' : 'feather') }), h('span', { text: auto ? 'Automatique' : 'Emplacement ' + n })),
        s.empty
          ? h('span.v-save-main', null, h('span.v-save-empty', { text: save && auto ? 'Réservé à la sauvegarde automatique' : 'Emplacement vide' }))
          : h('span.v-save-main', null,
            h('span.v-save-name', { text: s.name || 'Veilleur' }),
            h('span.v-save-info', { text: ['Niveau ' + (s.level || 1), originName(s.origin), s.region].filter(Boolean).join(' · ') })),
        s.empty ? null : h('span.v-save-meta', null, h('span', { text: playtime(s.playtime) }), h('span.v-save-date', { text: dateStr(s.date) })));
      if (disabled) row.disabled = true;
      row._slot = s;
      this.list.appendChild(row);
    }
  }
  defaultFocus() { return this.list.querySelector('button:not([disabled])'); }
  async _pick(s) {
    const app = this.app, ui = this.ui;
    if (this.mode === 'load') {
      if (s.empty) return;
      if (app.state === 'playing') { const ok = await ui.confirm({ title: 'Charger cette partie ?', text: 'La progression non sauvegardée sera perdue.', yes: 'Charger', no: 'Annuler' }); if (!ok) return; }
      ui.closeAll();
      try { app.loadSlot(s.slot); } catch (e) { console.error(e); }
      return;
    }
    if (!s.empty) { const ok = await ui.confirm({ title: 'Écraser cette sauvegarde ?', text: `${s.name || 'Veilleur'} · Niveau ${s.level || 1}`, yes: 'Écraser', no: 'Annuler', danger: true }); if (!ok) return; }
    let ok = false;
    try { ok = app.saveSlot(s.slot) !== false; } catch (e) { ok = false; }
    if (ok) { ui.sfx('ui_save'); this.msg.textContent = 'Partie sauvegardée.'; this.msg.className = 'v-saves-msg ok'; }
    else { ui.sfx('ui_error'); this.msg.textContent = 'Impossible de sauvegarder maintenant (combat en cours ?).'; this.msg.className = 'v-saves-msg err'; }
    this._build();
    const again = this.list.querySelector(`[data-slot="${s.slot}"]`);
    if (again && !again.disabled) again.focus({ preventScroll: true });
  }
  onKey(e) {
    if (e.code !== 'Delete' && e.code !== 'Backspace') return false;
    const a = document.activeElement, s = a && a._slot;
    if (!s || s.empty) return false;
    this.ui.confirm({ title: 'Effacer cette sauvegarde ?', text: `${s.name || 'Veilleur'} · Niveau ${s.level || 1} — cette action est définitive.`, yes: 'Effacer', no: 'Annuler', danger: true }).then((ok) => {
      if (!ok) return;
      try { this.app.saves.delete(s.slot); } catch (err) { console.error(err); }
      this.msg.textContent = 'Sauvegarde effacée.'; this.msg.className = 'v-saves-msg';
      this._build();
      const f = this.defaultFocus(); if (f) f.focus({ preventScroll: true });
    });
    return true;
  }
}

// ---------------------------------------------------------------------------------------- credits
export class CreditsScreen extends Screen {
  constructor(ui) {
    super(ui, 'credits', 'v-credits');
    this.body = h('div.v-credits-body.v-scroll');
    add(this.el, h('div.v-dim'),
      panel('v-credits-panel',
        h('div.v-panel-head', null, h('h2.v-panel-title', { text: 'Crédits' }), h('button.v-close', { type: 'button', 'aria-label': 'Fermer', html: icon('cross'), onclick: () => ui.back() })),
        rule(), this.body,
        h('div.v-panel-foot', null, h('button.v-btn', { nav: true, type: 'button', text: 'Retour', onclick: () => ui.back() }))));
  }
  onOpen() {
    clear(this.body);
    add(this.body, 
      h('div.v-credits-logo', null, h('div.v-credits-emblem', { html: EMBLEM }), h('h3', { text: 'VALOMBRE' }), h('p', { text: 'Les Éclats de l\'Aube' })),
      creditsBlocks(this.app));
    this.body.scrollTop = 0;
  }
}
