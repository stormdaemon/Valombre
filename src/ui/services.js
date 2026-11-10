// VALOMBRE UI — shrine menu, shop, forge, dialogue.
import { add, h, clear, num, hourStr } from './dom.js';
import { icon, itemIcon } from './icons.js';
import { Screen, panel, rule, hint } from './screen.js';
import { defOf, nameOf, itemCard } from './iteminfo.js';
import { ITEMS, upgradeMult } from '../game/data/items.js';

const count = (d, id) => { let n = 0; for (const it of (d && d.inventory) || []) if (it && it.id === id) n += it.qty || 0; return n; };

// ------------------------------------------------------------------------------------------ shrine
export class ShrineScreen extends Screen {
  constructor(ui) {
    super(ui, 'shrine', 'v-shrine');
    this.nameEl = h('h2.v-shrine-name');
    this.menu = h('nav.v-menu.v-shrine-menu');
    this.info = h('div.v-shrine-info');
    this.msg = h('div.v-shrine-msg');
    add(this.el, h('div.v-shrine-shade'),
      panel('v-shrine-panel',
        h('div.v-shrine-head', null, h('span.v-shrine-flame', { html: icon('flame') }), h('div', null, h('span.v-kicker', { text: 'Autel de Braise' }), this.nameEl)),
        rule(), this.menu, this.msg, rule(), this.info),
      h('div.v-foot-hints', null, hint('↑ ↓', 'Naviguer'), hint('Entrée', 'Valider'), hint('Échap', 'Quitter l\'Autel')));
  }
  onOpen() { this.msg.textContent = ''; this._build(); }
  onResume() { this._build(true); }
  onEvent(type) { if (type === 'player:flask' || type === 'inventory' || type === 'player:stats' || type === 'player:xp') this._build(true); }

  _build(keep) {
    const g = this.game, s = g && g.shrine, d = g && g.player && g.player.data;
    const focusKey = keep && document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.k : null;
    clear(this.menu); clear(this.info);
    if (!s || !d) return;
    this.nameEl.textContent = s.name || 'Autel';
    const item = (key, label, glyph, sub, fn, disabled) => {
      const b = h('button.v-menu-item', { nav: true, type: 'button', 'data-k': key, onclick: fn }, h('span.v-menu-ico', { html: icon(glyph) }), h('span.v-menu-label', { text: label }), sub ? h('span.v-menu-sub', { text: sub }) : null);
      if (disabled) b.disabled = true;
      this.menu.appendChild(b);
      return b;
    };
    const pts = d.attrPoints || 0;
    const lv = item('level', 'Monter de niveau', 'attributes', pts > 0 ? `${pts} point${pts > 1 ? 's' : ''} à répartir` : 'Attributs et pouvoirs d\'Éclat', () => this.ui.open('hub', { tab: 'character' }));
    if (pts > 0) lv.classList.add('notice');
    item('travel', 'Voyage rapide', 'pin', 'Rejoindre un autre Autel embrasé', () => this.ui.open('hub', { tab: 'map' }));
    const sap = count(d, 'amber_sap'), seed = count(d, 'ember_seed');
    item('flaskCount', 'Ajouter une gorgée', 'flask', s.flaskCountCost ? `Offrir 1 Sève d'Ambre (${sap} en besace)` : (d.flaskMax >= 9 ? 'La fiole ne peut contenir davantage' : 'Sève d\'Ambre requise'), () => this._act('flaskCount', 'La fiole contient une gorgée de plus.'), !s.flaskCountCost);
    item('flaskPower', 'Renforcer la fiole', 'flame', s.flaskPowerCost ? `Offrir 1 Graine de Braise (${seed} en besace)` : ((d.flaskLevel || 0) >= 5 ? 'La fiole est à sa pleine puissance' : 'Graine de Braise requise'), () => this._act('flaskPower', 'La sève brûle plus fort.'), !s.flaskPowerCost);
    item('morning', 'Attendre le matin', 'sun', 'Le monde se relève avec vous', () => this._act('morning', 'L\'aube se lève sur Valombre.'));
    item('night', 'Attendre la nuit', 'moon', 'Certaines choses ne sortent que dans le noir', () => this._act('night', 'La nuit tombe.'));
    item('leave', 'Quitter l\'Autel', 'exit', '', () => this._leave());
    add(this.info, 
      h('span', null, h('span', { html: icon('flask') }), `Fiole : ${d.flasks ?? 0} / ${d.flaskMax ?? 0}` + ((d.flaskLevel || 0) > 0 ? ` · puissance +${d.flaskLevel}` : '')),
      h('span', null, h('span', { html: icon('clock') }), [typeof g.day === 'number' ? 'Jour ' + g.day : '', hourStr(g.hour)].filter(Boolean).join(' · ')),
      h('span', null, h('span', { html: icon('attributes') }), `Niveau ${d.level || 1}`));
    if (focusKey) { const again = this.menu.querySelector(`[data-k="${focusKey}"]`); if (again && !again.disabled) again.focus({ preventScroll: true }); else { const f = this.defaultFocus(); if (f) f.focus({ preventScroll: true }); } }
  }
  _act(a, msg) {
    const g = this.game;
    if (!g) return;
    try { g.shrineAction(a); } catch (e) { console.error('[ui] shrineAction', e); }
    this.msg.textContent = msg;
    this.ui.sfx('ui_save');
    this._build(true);
  }
  _leave() {
    const g = this.game;
    try { if (g && g.shrine) g.shrineAction('leave'); } catch (e) { console.error(e); }
    if (this.isOpen) this.ui.close(this, true);
  }
  onBack() { this.ui.sfx('ui_back'); this._leave(); return true; }
}

// -------------------------------------------------------------------------------------------- shop
export class ShopScreen extends Screen {
  constructor(ui) {
    super(ui, 'shop', 'v-shop');
    this.sel = null;                          // { side:'buy'|'sell', i }
    this.title = h('h2.v-panel-title');
    this.gold = h('span.v-hub-gold-n');
    this.buyList = h('div.v-trade-list.v-scroll');
    this.sellList = h('div.v-trade-list.v-scroll');
    this.detail = h('div.v-trade-detail');
    add(this.el, h('div.v-dim.strong'),
      h('div.v-trade-frame', null,
        h('header.v-trade-head', null, h('div', null, h('span.v-kicker', { text: 'Commerce' }), this.title),
          h('div.v-hub-right', null, h('span.v-hub-gold', { title: 'Vos pièces d\'or' }, h('span', { html: icon('coin') }), this.gold),
            h('button.v-close', { type: 'button', 'aria-label': 'Fermer', html: icon('cross'), onclick: () => ui.back() }))),
        h('div.v-trade-body', null,
          h('section.v-box.v-trade-col', null, h('h4.v-box-title', { text: 'Marchandises' }), this.buyList),
          h('section.v-box.v-trade-mid', null, this.detail),
          h('section.v-box.v-trade-col', null, h('h4.v-box-title', { text: 'Vos biens' }), this.sellList)),
        h('footer.v-hub-foot', null, h('div.v-hub-hints', null, hint('Entrée', 'Acheter / vendre'), hint('← →', 'Changer de colonne'), hint('Échap', 'Fermer')))));
  }
  get shop() { const g = this.game; return g ? g.shop : null; }
  get d() { const g = this.game; return g && g.player ? g.player.data : null; }
  onOpen() { this.sel = null; this._build(); const f = this.defaultFocus(); if (f && f._sel) this._select(f._sel); }
  onEvent(type) { if (type === 'inventory') this._build(true); }
  defaultFocus() { return this.buyList.querySelector('button') || this.sellList.querySelector('button'); }

  _build(keep) {
    const shop = this.shop, d = this.d;
    if (!shop || !d) return;
    this.title.textContent = shop.name || 'Marchand';
    this.gold.textContent = num(d.gold || 0);
    const focus = keep && document.activeElement && document.activeElement._sel ? document.activeElement._sel : null;
    clear(this.buyList); clear(this.sellList);
    const row = (sel, inst, qty, price, off) => {
      const b = h('button.v-trade-row' + (off ? '.off' : '') + (this.sel && this.sel.side === sel.side && this.sel.i === sel.i ? '.sel' : ''), { nav: true, type: 'button' },
        h('span', { html: itemIcon(inst.id, 'sm') }),
        h('span.v-trade-name', { text: nameOf(inst) }),
        qty > 1 ? h('span.v-trade-qty', { text: '×' + qty }) : h('span.v-trade-qty'),
        h('span.v-trade-price', null, price > 0 ? num(price) : '—', h('span', { html: icon('coin') })));
      b._sel = sel;
      b.addEventListener('click', () => this._select(sel));
      b.addEventListener('focus', () => this._select(sel));
      b.addEventListener('dblclick', () => this._trade());
      return b;
    };
    const stock = shop.stock || [];
    stock.forEach((s, i) => { if (s && s.qty > 0) this.buyList.appendChild(row({ side: 'buy', i }, { id: s.id, up: 0 }, s.qty, s.price, (d.gold || 0) < s.price)); });
    if (!this.buyList.children.length) add(this.buyList, h('div.v-empty', null, h('span', { html: icon('bag') }), h('p', { text: 'Plus rien à vendre.' })));
    (d.inventory || []).forEach((it, i) => {
      if (!it) return;
      let pr = 0; try { pr = shop.sellPrice(i) || 0; } catch (e) { pr = 0; }
      this.sellList.appendChild(row({ side: 'sell', i }, it, it.qty, pr, pr <= 0));
    });
    if (!this.sellList.children.length) add(this.sellList, h('div.v-empty', null, h('span', { html: icon('bag') }), h('p', { text: 'Votre besace est vide.' })));
    // keep a valid selection
    const valid = (s) => s && (s.side === 'buy' ? stock[s.i] && stock[s.i].qty > 0 : (d.inventory || [])[s.i]);
    if (!valid(this.sel)) { const f = this.defaultFocus(); this.sel = f ? f._sel : null; }
    this._detail();
    if (focus) {
      const all = [...this.el.querySelectorAll('.v-trade-row')];
      const again = all.find((b) => b._sel.side === focus.side && b._sel.i === focus.i) || all.filter((b) => b._sel.side === focus.side).pop() || all[0];
      if (again) { again.focus({ preventScroll: true }); this._select(again._sel); }
    }
  }

  _select(sel) {
    if (this.sel && sel && this.sel.side === sel.side && this.sel.i === sel.i) return;
    this.sel = sel;
    for (const b of this.el.querySelectorAll('.v-trade-row')) b.classList.toggle('sel', !!sel && b._sel.side === sel.side && b._sel.i === sel.i);
    this._detail();
  }

  _detail() {
    const shop = this.shop, d = this.d, sel = this.sel;
    clear(this.detail);
    if (!shop || !d || !sel) { add(this.detail, itemCard(null, { emptyText: 'Choisissez un article.' })); return; }
    let inst, price, label, can;
    if (sel.side === 'buy') { const s = (shop.stock || [])[sel.i]; if (!s) return; inst = { id: s.id, up: 0, qty: count(d, s.id) }; price = s.price; label = 'Prix'; can = (d.gold || 0) >= s.price && s.qty > 0; }
    else { inst = (d.inventory || [])[sel.i]; if (!inst) return; try { price = shop.sellPrice(sel.i) || 0; } catch (e) { price = 0; } label = 'Rachat'; can = price > 0; }
    const def = defOf(inst);
    const cmp = def && def.slot ? (d.equipment || {})[def.slot] : null;
    add(this.detail, itemCard(inst, { d, compare: cmp, price, priceLabel: label, qty: inst.qty }));
    const btn = h('button.v-btn.primary', { nav: true, type: 'button', onclick: () => this._trade() }, sel.side === 'buy' ? `Acheter · ${num(price)}` : price > 0 ? `Vendre · ${num(price)}` : 'Invendable');
    btn.disabled = !can;
    add(this.detail, h('div.v-card-actions', null, btn, sel.side === 'buy' && !can ? h('span.v-card-note.bad', { text: 'Pas assez d\'or.' }) : null));
  }

  _trade() {
    const shop = this.shop, sel = this.sel;
    if (!shop || !sel) return;
    let ok = false;
    try { ok = sel.side === 'buy' ? shop.buy(sel.i) : shop.sell(sel.i); } catch (e) { console.error('[ui] trade', e); }
    this.ui.sfx(ok ? 'ui_buy' : 'ui_error');
    const prev = { ...sel };
    this._build(false);
    const all = [...this.el.querySelectorAll('.v-trade-row')];
    const side = all.filter((b) => b._sel.side === prev.side);
    const again = side.find((b) => b._sel.i === prev.i) || side.find((b) => b._sel.i > prev.i) || side[side.length - 1] || all[0];
    if (again) { this.sel = null; again.focus({ preventScroll: true }); this._select(again._sel); } else { this.sel = null; this._detail(); }
  }

  onKey(e) {
    const a = document.activeElement;
    if ((e.code === 'Enter' || e.code === 'NumpadEnter') && a && a.classList.contains('v-trade-row')) { this._trade(); return true; }
    return false;
  }
  onBack() {
    const g = this.game, shop = this.shop;
    try { if (shop && typeof shop.close === 'function') shop.close(); else if (g && typeof g.closePanel === 'function') g.closePanel(); } catch (e) { console.error(e); }
    this.ui.sfx('ui_back');
    if (this.isOpen) this.ui.close(this, true);
    return true;
  }
}

// ------------------------------------------------------------------------------------------- smith
export class SmithScreen extends Screen {
  constructor(ui) {
    super(ui, 'smith', 'v-smith');
    this.sel = 0;
    this.gold = h('span.v-hub-gold-n');
    this.list = h('div.v-trade-list.v-scroll');
    this.detail = h('div.v-smith-detail');
    add(this.el, h('div.v-dim.strong'),
      h('div.v-trade-frame.narrow', null,
        h('header.v-trade-head', null, h('div', null, h('span.v-kicker', { text: 'Forge' }), h('h2.v-panel-title', { text: 'Améliorer l\'équipement' })),
          h('div.v-hub-right', null, h('span.v-hub-gold', { title: 'Vos pièces d\'or' }, h('span', { html: icon('coin') }), this.gold),
            h('button.v-close', { type: 'button', 'aria-label': 'Fermer', html: icon('cross'), onclick: () => ui.back() }))),
        h('div.v-trade-body.two', null,
          h('section.v-box.v-trade-col', null, h('h4.v-box-title', { text: 'Pièces à forger' }), this.list),
          h('section.v-box.v-trade-mid', null, this.detail)),
        h('footer.v-hub-foot', null, h('div.v-hub-hints', null, hint('Entrée', 'Améliorer'), hint('Échap', 'Fermer')))));
  }
  get smith() { const g = this.game; return g ? g.smith : null; }
  get d() { const g = this.game; return g && g.player ? g.player.data : null; }
  onOpen() { this.sel = 0; this._build(); }
  onEvent(type) { if (type === 'inventory' || type === 'player:stats') this._build(true); }
  defaultFocus() { return this.list.querySelector('button.sel') || this.list.querySelector('button'); }
  _entries() { const s = this.smith; try { return (s && s.list()) || []; } catch (e) { return []; } }

  _build(keep) {
    const d = this.d;
    if (!d) return;
    const had = keep && document.activeElement && this.el.contains(document.activeElement);
    this.gold.textContent = num(d.gold || 0);
    const list = this.entries = this._entries();
    this.sel = Math.max(0, Math.min(this.sel, list.length - 1));
    clear(this.list);
    list.forEach((e, i) => {
      const b = h('button.v-trade-row' + (i === this.sel ? '.sel' : '') + (e.can ? '' : '.off'), { nav: true, type: 'button' },
        h('span', { html: itemIcon(e.id, 'sm') }),
        h('span.v-trade-name', null, nameOf({ id: e.id, up: e.up }), typeof e.where === 'string' ? h('small.v-tag', { text: 'Équipé' }) : null),
        h('span.v-trade-price', null, `+${e.up} → +${e.up + 1}`));
      b.addEventListener('click', () => this._select(i));
      b.addEventListener('focus', () => this._select(i));
      b.addEventListener('dblclick', () => this._upgrade());
      this.list.appendChild(b);
    });
    if (!list.length) add(this.list, h('div.v-empty', null, h('span', { html: icon('anvil') }), h('p', { text: 'Rien à améliorer : vos armes sont au sommet de leur art.' })));
    this._detail();
    if (had) { const f = this.defaultFocus(); if (f) f.focus({ preventScroll: true }); }
  }
  _select(i) {
    if (i === this.sel) return;
    this.sel = i;
    [...this.list.querySelectorAll('.v-trade-row')].forEach((b, k) => b.classList.toggle('sel', k === i));
    this._detail();
  }
  _detail() {
    const d = this.d, e = (this.entries || [])[this.sel];
    clear(this.detail);
    if (!e || !d) { add(this.detail, itemCard(null, { emptyText: 'Apportez des éclats d\'acier ou des fragments d\'Astre.' })); return; }
    const def = ITEMS[e.id];
    const head = h('div.v-card-head', null, h('span.v-card-ico', { html: itemIcon(e.id, 'lg') }),
      h('div.v-card-titles', null, h('h3.v-card-name', { text: nameOf({ id: e.id, up: e.up }) }), h('div.v-card-type', { text: `Amélioration vers +${e.up + 1}` + (def && def.maxUp ? ` (maximum +${def.maxUp})` : '') })));
    const stats = h('div.v-stats');
    if (def && def.type === 'weapon') {
      const a = def.dmg * upgradeMult(e.up), b = def.dmg * upgradeMult(e.up + 1);
      add(stats, h('div.v-stat', null, h('span.v-stat-label', { text: 'Dégâts' }), h('span.v-stat-val', { text: num(a) }), h('span.v-delta.up', null, '→ ', num(b))));
    } else add(stats, h('div.v-stat', null, h('span.v-stat-label', { text: 'Qualité' }), h('span.v-stat-val', { text: '+' + e.up }), h('span.v-delta.up', null, '→ +', String(e.up + 1))));
    const costs = h('div.v-costs');
    const cost = e.cost || {};
    for (const k in cost) {
      const need = cost[k], have = k === 'gold' ? (d.gold || 0) : count(d, k);
      const cdef = ITEMS[k];
      add(costs, h('div.v-cost' + (have >= need ? '' : '.missing'), null,
        h('span', { html: k === 'gold' ? `<span class="v-item-ico sm r-gold">${icon('coin')}</span>` : itemIcon(k, 'sm') }),
        h('span.v-cost-name', { text: k === 'gold' ? 'Pièces d\'or' : (cdef ? cdef.name : k) }),
        h('span.v-cost-n', { text: `${num(have)} / ${num(need)}` })));
    }
    const btn = h('button.v-btn.primary', { nav: true, type: 'button', onclick: () => this._upgrade() }, h('span.v-btn-ico', { html: icon('anvil') }), 'Améliorer');
    btn.disabled = !e.can;
    add(this.detail, h('div.v-card', null, head, def && def.desc ? h('p.v-card-desc', { text: def.desc }) : null, stats, h('h5.v-csec', { text: 'Coût' }), costs),
      h('div.v-card-actions', null, btn, e.can ? null : h('span.v-card-note.bad', { text: 'Il vous manque des ressources.' })));
  }
  _upgrade() {
    const s = this.smith, e = (this.entries || [])[this.sel];
    if (!s || !e) return;
    let ok = false;
    try { ok = s.upgrade(e.where); } catch (err) { console.error('[ui] upgrade', err); }
    this.ui.sfx(ok ? 'ui_equip' : 'ui_error');
    this._build(false);
    const f = this.defaultFocus(); if (f) f.focus({ preventScroll: true });
  }
  onKey(e) {
    const a = document.activeElement;
    if ((e.code === 'Enter' || e.code === 'NumpadEnter') && a && a.classList.contains('v-trade-row')) { this._upgrade(); return true; }
    return false;
  }
  onBack() {
    const g = this.game, s = this.smith;
    try { if (s && typeof s.close === 'function') s.close(); else if (g && typeof g.closePanel === 'function') g.closePanel(); } catch (e) { console.error(e); }
    this.ui.sfx('ui_back');
    if (this.isOpen) this.ui.close(this, true);
    return true;
  }
}

// ---------------------------------------------------------------------------------------- dialogue
export class DialogueScreen extends Screen {
  constructor(ui) {
    super(ui, 'dialogue', 'v-dialogue');
    this.speaker = h('span.v-dlg-speaker');
    this.role = h('span.v-dlg-role');
    this.shown = h('span');
    this.rest = h('span.v-dlg-rest');
    this.options = h('div.v-dlg-options');
    this.more = h('span.v-dlg-more', { html: icon('right') });
    this.box = panel('v-dlg-box',
      h('div.v-dlg-head', null, this.speaker, this.role),
      h('p.v-dlg-text', null, this.shown, this.rest, this.more),
      this.options);
    add(this.el, h('div.v-dlg-shade'), this.box);
    this.box.addEventListener('click', (e) => { if (!e.target.closest('button')) this._skip(); });
    this.text = ''; this.n = 0; this.typing = false; this.ref = null;
  }
  onOpen() { this.ref = null; this.refresh(); }
  refresh() {
    const g = this.game, d = g && g.dialogue;
    if (!d) return;
    this.ref = d;
    this.speaker.textContent = d.speaker || '';
    this.role.textContent = d.role || '';
    this.role.hidden = !d.role;
    this.text = String(d.text || '');
    this.n = 0; this.typing = this.text.length > 0;
    this.shown.textContent = ''; this.rest.textContent = this.text;
    this.box.classList.add('typing');
    clear(this.options);
    const opts = d.options && d.options.length ? d.options : [{ label: 'Continuer' }];
    opts.forEach((o, i) => {
      this.options.appendChild(h('button.v-dlg-option', { nav: true, type: 'button', onclick: () => this._choose(i) }, h('span.v-dlg-num', { text: String(i + 1) }), h('span', { text: o.label || '…' })));
    });
    if (!this.typing) this._done();
  }
  defaultFocus() { return this.typing ? null : this.options.querySelector('button'); }
  _done() {
    this.typing = false; this.n = this.text.length;
    this.shown.textContent = this.text; this.rest.textContent = '';
    this.box.classList.remove('typing');
    const f = this.options.querySelector('button');
    if (f && this.ui.top === this) f.focus({ preventScroll: true });
  }
  _skip() { if (this.typing) this._done(); }
  _choose(i) {
    const g = this.game, d = g && g.dialogue;
    if (!d) { if (this.isOpen) this.ui.close(this, true); return; }
    if (this.typing) { this._done(); return; }
    const before = d;
    try { d.choose(i); } catch (e) { console.error('[ui] dialogue.choose', e); }
    // the game normally emits 'dialogue'; cover the case where it does not
    const now = this.game && this.game.dialogue;
    if (!now) { if (this.isOpen) this.ui.close(this, true); }
    else if (now !== this.ref) this.refresh();
    else if (now === before && !(d.options && d.options.length)) { try { g.closePanel(); } catch (e) { /* ignore */ } }
  }
  update(dt) {
    const g = this.game, d = g && g.dialogue;
    if (d && d !== this.ref) this.refresh();
    if (!this.typing) return;
    this.n = Math.min(this.text.length, this.n + dt * 75);
    const k = Math.floor(this.n);
    if (k !== this._k) { this._k = k; this.shown.textContent = this.text.slice(0, k); this.rest.textContent = this.text.slice(k); }
    if (k >= this.text.length) this._done();
  }
  onKey(e) {
    if (this.typing) {
      if (e.code === 'Enter' || e.code === 'NumpadEnter' || e.code === 'Space') { this._done(); return true; }
      return false;
    }
    const m = /^(?:Digit|Numpad)([1-9])$/.exec(e.code);
    if (m) { const i = Number(m[1]) - 1; if (i < this.options.children.length) { this._choose(i); return true; } }
    return false;
  }
  onBack() {
    if (this.typing) { this._done(); return true; }
    const g = this.game;
    try { if (g && typeof g.closePanel === 'function') g.closePanel(); } catch (e) { console.error(e); }
    if (this.isOpen) this.ui.close(this, true);
    return true;
  }
}
