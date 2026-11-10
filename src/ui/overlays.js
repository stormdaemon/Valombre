// VALOMBRE UI — loading screen, pause menu, confirmation dialog, death screen, ending / credits roll.
import { add, h, clear, hourStr, playtime } from './dom.js';
import { icon, EMBLEM } from './icons.js';
import { Screen, panel, rule, hint } from './screen.js';
import { ENDINGS } from '../game/data/story.js';

const TIPS = [
  'Reposez-vous aux Autels de Braise : vos fioles s\'y remplissent, mais ce que vous avez abattu se relève.',
  'Une garde levée au dernier instant devient une parade. L\'ennemi chancelle : frappez.',
  'Votre charge décide de votre roulade. Sous 40 %, elle est vive ; au-delà de 75 %, elle vous coûtera cher.',
  'Le souffle se régénère plus lentement tant que vous gardez votre bouclier levé.',
  'Chaque coup porté rend un peu d\'Éclat. Les pouvoirs se méritent l\'arme à la main.',
  'Un cataplasme d\'herbes chasse le venin des araignées de Sombreronce.',
  'Verrouillez une cible pour tourner autour d\'elle sans la quitter des yeux.',
  'Les stèles gravées racontent Valombre. Les lire rapporte de l\'expérience.',
  'La forgeronne de Hautefeuille améliore les armes contre des éclats d\'acier.',
  'Quand un cercle rouge paraît au sol, n\'y soyez plus.',
];

// ---------------------------------------------------------------------------------------- loading
export class LoadingOverlay {
  constructor(ui) {
    this.ui = ui;
    this.fill = h('div.v-load-fill');
    this.text = h('div.v-load-text', { text: 'Chargement…' });
    this.tip = h('p.v-load-tip', { text: TIPS[Math.floor(Math.random() * TIPS.length)] });
    this.pct = h('span.v-load-pct', { text: '0 %' });
    this.el = h('div.v-loading', { hidden: true },
      h('div.v-load-center', null,
        h('div.v-load-emblem', { html: EMBLEM }),
        h('h1.v-load-title', { text: 'VALOMBRE' }),
        h('p.v-load-sub', { text: 'Les Éclats de l\'Aube' }),
        h('div.v-load-bar', null, this.fill),
        h('div.v-load-row', null, this.text, this.pct)),
      h('div.v-load-foot', null, rule(), this.tip));
    ui.topLayer.appendChild(this.el);
    this.p = -1; this.shown = false;
  }
  set(p, text) {
    p = Math.max(0, Math.min(1, Number(p) || 0));
    if (p !== this.p) { this.p = p; this.fill.style.transform = `scaleX(${p.toFixed(3)})`; this.pct.textContent = Math.round(p * 100) + ' %'; }
    if (text !== undefined && text !== null && text !== this._t) { this._t = text; this.text.textContent = text; }
  }
  show() { if (this.shown) return; this.shown = true; this.el.hidden = false; this.el.classList.remove('out'); }
  hide() {
    if (!this.shown) return;
    this.shown = false; this.el.classList.add('out');
    setTimeout(() => { if (!this.shown) this.el.hidden = true; }, 450);
  }
}

// ------------------------------------------------------------------------------------------ pause
export class PauseScreen extends Screen {
  constructor(ui) {
    super(ui, 'pause', 'v-pause');
    this.info = h('div.v-pause-info');
    this.menu = h('nav.v-menu.v-pause-menu');
    this.msg = h('div.v-pause-msg');
    add(this.el, h('div.v-dim'), h('div.v-pause-col', null,
      h('div.v-pause-emblem', { html: EMBLEM }),
      h('h2.v-pause-title', { text: 'Pause' }), rule(), this.info, this.menu, this.msg),
    h('div.v-foot-hints', null, hint('↑ ↓', 'Naviguer'), hint('Entrée', 'Valider'), hint('Échap', 'Reprendre')));
    const item = (label, glyph, fn) => h('button.v-menu-item', { nav: true, type: 'button', onclick: fn }, h('span.v-menu-ico', { html: icon(glyph) }), h('span.v-menu-label', { text: label }));
    add(this.menu, 
      item('Reprendre', 'right', () => ui.close(this)),
      item('Inventaire', 'bag', () => ui.open('hub', { tab: 'inventory' })),
      item('Carte', 'map', () => ui.open('hub', { tab: 'map' })),
      item('Journal', 'book', () => ui.open('hub', { tab: 'journal' })),
      item('Options', 'gear', () => ui.open('options')),
      item('Sauvegarder', 'feather', () => ui.open('saves', { mode: 'save' })),
      item('Menu principal', 'exit', async () => {
        const ok = await ui.confirm({ title: 'Retourner au menu principal ?', text: 'La progression non sauvegardée depuis le dernier Autel sera perdue.', yes: 'Quitter la partie', no: 'Rester', danger: true });
        if (ok) { ui.closeAll(); try { this.app.quitToTitle(); } catch (e) { console.error(e); } }
      }));
  }
  onOpen() { this._info(); this.msg.textContent = ''; }
  onResume() { this._info(); }
  _info() {
    const g = this.game, d = g && g.player && g.player.data;
    clear(this.info);
    if (!d) return;
    const region = g.region && g.region.name ? g.region.name : '';
    add(this.info, 
      h('div.v-pause-name', { text: `${d.name || 'Veilleur'} · Niveau ${d.level || 1}` }),
      h('div.v-pause-where', { text: [region, typeof g.day === 'number' ? 'Jour ' + g.day : '', hourStr(g.hour)].filter(Boolean).join(' · ') }),
      d.stats && d.stats.time ? h('div.v-pause-time', { text: 'Temps de jeu : ' + playtime(d.stats.time) }) : null);
  }
}

// ---------------------------------------------------------------------------------------- confirm
export class ConfirmScreen extends Screen {
  constructor(ui) {
    super(ui, 'confirm', 'v-confirm', { overlay: true });
    this.title = h('h3.v-confirm-title');
    this.text = h('p.v-confirm-text');
    this.yes = h('button.v-btn.primary', { nav: true, type: 'button', onclick: () => this._done(true) });
    this.no = h('button.v-btn', { nav: true, type: 'button', onclick: () => this._done(false) });
    add(this.el, h('div.v-dim.strong'), panel('v-confirm-box', this.title, rule(), this.text, h('div.v-confirm-btns', null, this.no, this.yes)));
    this._resolve = null;
  }
  onOpen(o = {}) {
    this.title.textContent = o.title || 'Confirmer ?';
    this.text.textContent = o.text || '';
    this.text.hidden = !o.text;
    this.yes.textContent = o.yes || 'Oui';
    this.no.textContent = o.no || 'Non';
    this.yes.classList.toggle('danger', !!o.danger);
    this._resolve = o.resolve || null;
  }
  defaultFocus() { return this.no; }
  _done(v) { const r = this._resolve; this._resolve = null; this.ui.close(this); if (r) r(v); }
  onBack() { this._done(false); return true; }
  onClose() { if (this._resolve) { const r = this._resolve; this._resolve = null; r(false); } }
}

// ------------------------------------------------------------------------------------------ death
export class DeathOverlay {
  constructor(ui) {
    this.el = h('div.v-death', { hidden: true }, h('div.v-death-band', null,
      h('div.v-death-text', { text: 'VOUS AVEZ PÉRI' }),
      h('div.v-death-sub', { text: 'La Braise vous rappelle…' })));
    ui.topLayer.appendChild(this.el);
    this.on = false;
  }
  show() { if (this.on) return; this.on = true; this.el.hidden = false; this.el.classList.remove('out'); }
  hide() { if (!this.on) return; this.on = false; this.el.classList.add('out'); setTimeout(() => { if (!this.on) this.el.hidden = true; }, 900); }
}

// ---------------------------------------------------------------------------------------- credits
export function creditsData(app) {
  if (app && Array.isArray(app.credits) && app.credits.length) return app.credits;
  return [
    ['Un jeu de', ['L\'Atelier de Valombre']],
    ['Conception et programmation', ['Moteur de rendu, monde ouvert, combat, intelligence des créatures', 'Interface et outils']],
    ['Direction artistique', ['Personnages, créatures, architectures et paysages modelés par le code', 'Aucune ressource externe : tout est généré']],
    ['Monde et récit', ['L\'île de Valombre, ses six contrées et la Citadelle d\'Aubeclair', 'Dialogues, quêtes et codex']],
    ['Musique et sons', ['Partitions et ambiances synthétisées en temps réel', 'Bruitages, voix et pas générés procéduralement']],
    ['Technologies', ['three.js · WebGL 2 · Web Audio', 'JavaScript, sans moteur tiers']],
    ['Remerciements', ['À celles et ceux qui rallument les Autels.', 'À vous, Veilleur.']],
  ];
}

export function creditsBlocks(app) {
  return creditsData(app).map(([head, lines]) => h('div.v-cred-block', null, h('div.v-cred-head', { text: head }), (lines || []).map((l) => h('div.v-cred-line', { text: l }))));
}

// ----------------------------------------------------------------------------------------- ending
export class EndingScreen extends Screen {
  constructor(ui) {
    super(ui, 'ending', 'v-ending', { root: true });
    this.roll = h('div.v-ending-roll');
    this.done = h('div.v-ending-done', { hidden: true },
      h('div.v-ending-fin', { text: 'FIN' }),
      h('button.v-btn.primary', { nav: true, type: 'button', text: 'Retour au menu principal', onclick: () => this._quit() }));
    this.skip = h('div.v-ending-skip', null, hint('Espace', 'Accélérer'), hint('Échap', 'Passer'));
    add(this.el, h('div.v-ending-bg'), h('div.v-ending-view', null, this.roll), this.done, this.skip);
    this.y = 0; this.h = 0; this.vh = 0; this.finished = false; this.fast = false;
    window.addEventListener('keyup', (e) => { if (e.code === 'Space') this.fast = false; });
  }
  onOpen(o = {}) {
    const end = ENDINGS[o.id] || { title: 'Fin', text: [] };
    const g = this.game, d = g && g.player && g.player.data;
    clear(this.roll);
    add(this.roll, 
      h('div.v-ending-title', null, h('div.v-ending-kicker', { text: 'Épilogue' }), h('h2', { text: end.title }), rule()),
      (end.text || []).map((t) => h('p.v-ending-para', { text: t })),
      h('div.v-ending-gap'),
      h('div.v-ending-logo', null, h('div.v-ending-emblem', { html: EMBLEM }), h('h1', { text: 'VALOMBRE' }), h('p', { text: 'Les Éclats de l\'Aube' })),
      creditsBlocks(this.app),
      d ? h('div.v-cred-block', null, h('div.v-cred-head', { text: 'Votre périple' }),
        h('div.v-cred-line', { text: `${d.name || 'Veilleur'}, niveau ${d.level || 1}` }),
        d.stats ? h('div.v-cred-line', { text: `${playtime(d.stats.time)} de veille · ${d.stats.kills || 0} ennemis abattus · ${d.stats.deaths || 0} morts` }) : null) : null,
      h('div.v-ending-gap'));
    this.finished = false; this.fast = false; this.done.hidden = true; this.skip.hidden = false;
    this.vh = this.el.clientHeight || window.innerHeight;
    this.h = 0; this.y = this.vh * 0.72;
    this.roll.style.transform = `translate3d(0,${this.y}px,0)`;
    this._measure = 2;
  }
  defaultFocus() { return this.finished ? this.done.querySelector('button') : null; }
  onKey(e) {
    if (this.finished) return false;
    if (e.code === 'Space') { this.fast = true; return true; }
    if (e.code === 'Enter' || e.code === 'NumpadEnter') { this._finish(); return true; }
    return false;
  }
  onBack() { if (!this.finished) this._finish(); return true; }
  _finish() {
    if (this.finished) return;
    this.finished = true; this.done.hidden = false; this.skip.hidden = true;
    this.roll.classList.add('gone');
    const b = this.done.querySelector('button'); if (b) b.focus({ preventScroll: true });
  }
  _quit() { this.ui.closeAll(); try { this.app.quitToTitle(); } catch (e) { console.error(e); } }
  update(dt) {
    if (this.finished) return;
    if (this._measure > 0 && --this._measure === 0) { this.h = this.roll.offsetHeight; this.vh = this.el.clientHeight || window.innerHeight; }
    const speed = (this.ui.rem * 2.6) * (this.fast ? 7 : 1);
    this.y -= speed * dt;
    this.roll.style.transform = `translate3d(0,${this.y.toFixed(1)}px,0)`;
    if (this.h > 0 && this.y < -this.h + this.vh * 0.35) this._finish();
  }
  onClose() { this.roll.classList.remove('gone'); }
}
