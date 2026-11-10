// VALOMBRE UI — in-game panels: inventory + equipment, character sheet + level-up + powers, world map, journal.
import { add, h, clear, clamp, num, hourStr } from './dom.js';
import { icon, itemIcon, skillIcon, SKILL_TINT } from './icons.js';
import { Screen, rule, hint } from './screen.js';
import { defOf, nameOf, itemCard, previewEquip, loadLabel, SLOT_LABEL, SLOT_GLYPH } from './iteminfo.js';
import { ITEMS } from '../game/data/items.js';
import { ATTRS, ORIGINS, SKILLS, derive, xpForLevel } from '../game/data/rules.js';

const TABS = [['inventory', 'Inventaire', 'bag'], ['character', 'Personnage', 'person'], ['map', 'Carte', 'map'], ['journal', 'Journal', 'book']];
const FILTERS = [['all', 'Tout', 'bag'], ['weapon', 'Armes', 'sword'], ['shield', 'Boucliers', 'shield'], ['armor', 'Armures', 'chest'], ['consumable', 'Consommables', 'flask'], ['material', 'Matériaux', 'shard'], ['key', 'Objets clés', 'key']];
const TYPE_ORDER = { weapon: 0, shield: 1, armor: 2, consumable: 3, material: 4, key: 5 };
const POI_GLYPH = { village: 'house', hamlet: 'house', camp: 'tent', ruin_village: 'ruin', bandit_camp: 'tent', arena: 'skull', citadel: 'tower' };
const POI_KIND = { village: 'Village', hamlet: 'Hameau', camp: 'Campement', ruin_village: 'Ruines', bandit_camp: 'Repaire', arena: 'Antre', citadel: 'Citadelle' };

export class HubScreen extends Screen {
  constructor(ui) {
    super(ui, 'hub', 'v-hub');
    this.tab = 'inventory';
    this.tabBtns = {}; this.tabKeys = {};
    const nav = h('nav.v-hub-tabs');
    for (const [id, label, glyph] of TABS) {
      const key = h('kbd.v-key.sm');
      const b = h('button.v-hub-tab', { nav: true, type: 'button', onclick: () => this.setTab(id) }, h('span.v-hub-tab-ico', { html: icon(glyph) }), h('span', { text: label }), key);
      this.tabBtns[id] = b; this.tabKeys[id] = key; nav.appendChild(b);
    }
    this.gold = h('span.v-hub-gold-n', { text: '0' });
    this.who = h('span.v-hub-who');
    this.body = h('div.v-hub-body');
    this.hints = h('div.v-hub-hints');
    this.pages = { inventory: new InventoryTab(this), character: new CharacterTab(this), map: new MapTab(this), journal: new JournalTab(this) };
    for (const k in this.pages) { this.pages[k].el.hidden = true; this.body.appendChild(this.pages[k].el); }
    add(this.el, h('div.v-dim.strong'),
      h('div.v-hub-frame', null,
        h('header.v-hub-head', null, nav,
          h('div.v-hub-right', null, this.who, h('span.v-hub-gold', { title: 'Pièces d\'or' }, h('span', { html: icon('coin') }), this.gold),
            h('button.v-close', { type: 'button', 'aria-label': 'Fermer', html: icon('cross'), onclick: () => ui.back() }))),
        this.body,
        h('footer.v-hub-foot', null, this.hints)));
  }
  get page() { return this.pages[this.tab]; }
  onOpen(o = {}) { this._keys(); this.setTab(o.tab && this.pages[o.tab] ? o.tab : this.tab, true); }
  onResume() { this._head(); try { if (this.page.refresh) this.page.refresh(); else this.page.show(); } catch (e) { console.error(e); } }
  onResize() { if (this.page.onResize) this.page.onResize(); }
  defaultFocus() { return (this.page.defaultFocus && this.page.defaultFocus()) || this.tabBtns[this.tab]; }
  _keys() { for (const [id] of TABS) this.tabKeys[id].textContent = this.ui.keyLabel(id); }
  _head() {
    const g = this.game, d = g && g.player && g.player.data;
    this.gold.textContent = d ? num(d.gold || 0) : '0';
    this.who.textContent = d ? `${d.name || 'Veilleur'} · Niv. ${d.level || 1}` : '';
  }
  setTab(id, force) {
    if (!this.pages[id]) return;
    if (id === this.tab && !force) return;
    this.tab = id;
    for (const k in this.pages) { this.pages[k].el.hidden = k !== id; this.tabBtns[k].classList.toggle('on', k === id); }
    this._head();
    clear(this.hints);
    add(this.hints, (this.page.hints ? this.page.hints() : []).map(([k, l]) => hint(k, l)), hint('Échap', 'Fermer'));
    try { this.page.show(); } catch (e) { console.error('[ui] hub ' + id, e); }
    if (this.isOpen && this.ui.top === this) { const f = this.defaultFocus(); if (f) this.ui._focus(f, true); }
  }
  onEvent(type) {
    if (type === 'binds') { this._keys(); return; }
    if (type === 'settings') return;
    this._head();
    try { this.page.onEvent(type); } catch (e) { console.error(e); }
  }
  onKey(e) { return this.page.onKey ? this.page.onKey(e) === true : false; }
  onBack() { return this.page.onBack ? this.page.onBack() === true : false; }
  update(dt) { if (this.page.update) this.page.update(dt); }
}

// ================================================================================================ inventory
class InventoryTab {
  constructor(hub) {
    this.hub = hub; this.ui = hub.ui;
    this.filter = 'all';
    this.sel = null;                       // { kind:'inv', index } | { kind:'eq', slot }
    this.slotBtns = {};
    const doll = h('div.v-doll', null, h('div.v-doll-fig', { html: '<svg viewBox="0 0 100 200" aria-hidden="true"><path d="M50 8c8 0 13 6 13 14s-4 14-9 16v5c10 2 20 6 24 14l6 44-9 3-6-32-3 30 4 86H54l-4-62-4 62H30l4-86-3-30-6 32-9-3 6-44c4-8 14-12 24-14v-5c-5-2-9-8-9-16S42 8 50 8z"/></svg>' }));
    for (const slot of ['head', 'weapon', 'chest', 'offhand', 'legs']) {
      const b = h('button.v-slot', { nav: true, type: 'button', 'data-slot': slot, onclick: () => this._select({ kind: 'eq', slot }), ondblclick: () => this._unequip(slot), onfocus: () => this._select({ kind: 'eq', slot }, true) });
      this.slotBtns[slot] = b; doll.appendChild(b);
    }
    this.summary = h('div.v-inv-summary');
    this.filtersEl = h('div.v-inv-filters');
    this.filterBtns = {};
    for (const [id, label, glyph] of FILTERS) {
      const b = h('button.v-filter', { nav: true, type: 'button', title: label, 'aria-label': label, html: icon(glyph), onclick: () => { this.filter = id; this._grid(); this._detail(); } });
      this.filterBtns[id] = b; this.filtersEl.appendChild(b);
    }
    this.filterLabel = h('span.v-inv-filter-label');
    this.grid = h('div.v-grid.v-scroll');
    this.detail = h('div.v-inv-detail');
    this.el = h('div.v-page.v-inv', null,
      h('section.v-inv-left.v-box', null, h('h4.v-box-title', { text: 'Équipement' }), doll, this.summary),
      h('section.v-inv-mid.v-box', null, h('div.v-inv-bar', null, this.filtersEl, this.filterLabel), this.grid),
      h('section.v-inv-right.v-box', null, this.detail));
  }
  get g() { return this.hub.game; }
  get d() { const g = this.g; return g && g.player ? g.player.data : null; }
  hints() { return [['Entrée', 'Équiper / utiliser'], ['Suppr', 'Jeter']]; }
  defaultFocus() { return this.grid.querySelector('.v-cell:not(.filler)') || this.slotBtns.weapon; }
  show() { this.sel = null; this.refresh(); const first = this.grid.querySelector('.v-cell:not(.filler)'); if (first) this._select({ kind: 'inv', index: Number(first.dataset.i) }, true); }
  onEvent() { this.refresh(); }
  refresh() { this._doll(); this._grid(); this._detail(); }

  _inst(sel = this.sel) {
    const d = this.d;
    if (!d || !sel) return null;
    return sel.kind === 'eq' ? (d.equipment || {})[sel.slot] || null : (d.inventory || [])[sel.index] || null;
  }

  _doll() {
    const d = this.d, eq = (d && d.equipment) || {};
    for (const slot in this.slotBtns) {
      const b = this.slotBtns[slot], inst = eq[slot];
      b.innerHTML = (inst ? itemIcon(inst.id) + (inst.up ? `<span class="v-up">+${inst.up}</span>` : '') : `<span class="v-item-ico ghost">${icon(SLOT_GLYPH[slot])}</span>`) + `<span class="v-slot-label">${SLOT_LABEL[slot]}</span>`;
      b.title = inst ? nameOf(inst) : SLOT_LABEL[slot] + ' — vide';
      b.classList.toggle('empty', !inst);
      b.classList.toggle('sel', !!this.sel && this.sel.kind === 'eq' && this.sel.slot === slot);
    }
    this._summary();
  }

  _summary() {
    const g = this.g, d = this.d, p = g && g.player;
    clear(this.summary);
    if (!d || !p) return;
    let st = p.st;
    if (!st) { try { st = derive(d); } catch (e) { return; } }
    const cand = this.sel && this.sel.kind === 'inv' ? this._inst() : null;
    const pv = cand && defOf(cand) && defOf(cand).slot ? previewEquip(d, cand) : null;
    const line = (label, cur, next, fmt, better = 1) => {
      const row = h('div.v-sum-row', null, h('span.v-sum-label', { text: label }), h('span.v-sum-val', { text: fmt(cur) }));
      if (pv && Math.abs(next - cur) > 0.004) add(row, h('span.v-sum-next.' + ((next - cur) * better > 0 ? 'up' : 'down'), null, '→ ', fmt(next)));
      return row;
    };
    const pct = (v) => Math.round(v * 100) + ' %';
    add(this.summary, 
      line('Attaque', st.attack, pv ? pv.attack : 0, (v) => num(v)),
      line('Défense', st.def, pv ? pv.def : 0, (v) => num(v)),
      line('Équilibre', st.poise, pv ? pv.poise : 0, (v) => num(v)),
      line('Garde', st.block, pv ? pv.block : 0, pct),
      line('Stabilité', st.stability, pv ? pv.stability : 0, (v) => num(v)));
    const load = st.load || 0, nl = pv ? pv.load : load;
    const bar = h('div.v-load-bar2', null, h('i', { style: { width: clamp(load * 100, 0, 100).toFixed(1) + '%' } }), h('b.t40'), h('b.t75'));
    bar.classList.toggle('heavy', load >= 0.75); bar.classList.toggle('over', load > 1);
    add(this.summary, h('div.v-load', null,
      h('div.v-load-head', null, h('span', { html: icon('weight') }), h('span.v-sum-label', { text: 'Charge' }),
        h('span.v-load-num', { text: `${num(st.weight, 1)} / ${num(st.capacity, 1)}` }),
        h('span.v-load-kind', { text: loadLabel(load) })),
      bar,
      pv && Math.abs(nl - load) > 0.004 ? h('div.v-load-next.' + (nl < load ? 'up' : 'down'), { text: `→ ${num(pv.weight, 1)} (${Math.round(nl * 100)} %) · ${loadLabel(nl)}` }) : h('div.v-load-note', { text: load < 0.4 ? 'Roulade vive' : load < 0.75 ? 'Roulade normale' : load <= 1 ? 'Roulade lente' : 'Déplacements entravés' })));
  }

  _grid() {
    const d = this.d, inv = (d && d.inventory) || [];
    for (const k in this.filterBtns) this.filterBtns[k].classList.toggle('on', k === this.filter);
    const list = [];
    for (let i = 0; i < inv.length; i++) {
      const it = inv[i], def = it && ITEMS[it.id];
      if (!it) continue;
      const type = def ? def.type : 'material';
      if (this.filter !== 'all' && type !== this.filter) continue;
      list.push({ i, it, def, type });
    }
    list.sort((a, b) => (TYPE_ORDER[a.type] ?? 9) - (TYPE_ORDER[b.type] ?? 9) || String(a.def ? a.def.name : a.it.id).localeCompare(String(b.def ? b.def.name : b.it.id), 'fr') || a.i - b.i);
    const f = FILTERS.find((x) => x[0] === this.filter);
    this.filterLabel.textContent = `${f ? f[1] : ''} · ${list.length}`;
    clear(this.grid);
    for (const { i, it } of list) {
      const b = h('button.v-cell', { nav: true, type: 'button', 'data-i': i, title: nameOf(it), html: itemIcon(it.id) + (it.qty > 1 ? `<span class="v-qty">${it.qty}</span>` : '') + (it.up ? `<span class="v-up">+${it.up}</span>` : '') });
      b.addEventListener('click', () => this._select({ kind: 'inv', index: i }));
      b.addEventListener('focus', () => this._select({ kind: 'inv', index: i }, true));
      b.addEventListener('dblclick', () => this._primary());
      if (this.sel && this.sel.kind === 'inv' && this.sel.index === i) b.classList.add('sel');
      this.grid.appendChild(b);
    }
    const min = Math.max(35, Math.ceil(list.length / 7) * 7);
    for (let k = list.length; k < min; k++) this.grid.appendChild(h('div.v-cell.filler'));
    if (!list.length && this.sel && this.sel.kind === 'inv') this.sel = null;
  }

  _select(sel, quiet) {
    if (this.sel && sel && this.sel.kind === sel.kind && this.sel.index === sel.index && this.sel.slot === sel.slot) return;
    this.sel = sel;
    for (const c of this.grid.children) c.classList.toggle('sel', !!sel && sel.kind === 'inv' && Number(c.dataset.i) === sel.index);
    for (const s in this.slotBtns) this.slotBtns[s].classList.toggle('sel', !!sel && sel.kind === 'eq' && sel.slot === s);
    this._summary();
    this._detail();
  }

  _detail() {
    const d = this.d, sel = this.sel, inst = this._inst(), def = defOf(inst);
    clear(this.detail);
    if (!inst) {
      add(this.detail, itemCard(null, { emptyText: sel && sel.kind === 'eq' ? `${SLOT_LABEL[sel.slot]} : rien d'équipé.` : 'Votre besace est vide.' }));
      return;
    }
    const equipped = sel.kind === 'eq';
    const cmp = !equipped && def && def.slot ? (d.equipment || {})[def.slot] : null;
    add(this.detail, itemCard(inst, { d, compare: cmp, qty: inst.qty, tag: equipped ? 'Équipé' : '' }));
    const btns = h('div.v-card-actions');
    if (equipped) add(btns, h('button.v-btn.primary', { nav: true, type: 'button', text: 'Retirer', onclick: () => this._unequip(sel.slot) }));
    else if (def && def.slot) add(btns, h('button.v-btn.primary', { nav: true, type: 'button', text: 'Équiper', onclick: () => this._primary() }));
    else if (def && def.tool === 'torch') { const lit = !!(d && d.torchLit); add(btns, h('button.v-btn.primary', { nav: true, type: 'button', text: lit ? 'Éteindre' : 'Allumer', onclick: () => this._primary() })); }
    else if (def && def.type === 'consumable') add(btns, h('button.v-btn.primary', { nav: true, type: 'button', text: 'Utiliser', onclick: () => this._primary() }));
    if (!equipped && !(def && def.type === 'key')) add(btns, h('button.v-btn.ghost', { nav: true, type: 'button', onclick: () => this._drop() }, h('span.v-btn-ico', { html: icon('trash') }), 'Jeter'));
    if (def && def.type === 'key') add(btns, h('span.v-card-note', { text: def.tool ? `Toujours sur vous · touche ${this.ui.keyLabel('torch')}` : 'Objet de quête : ne peut être jeté.' }));
    if (def && def.type === 'material' && !btns.querySelector('.primary')) btns.prepend(h('span.v-card-note', { text: 'Matériau d\'artisanat.' }));
    add(this.detail, btns);
  }

  _refocus(index) {
    this.refresh();
    const cells = [...this.grid.querySelectorAll('.v-cell:not(.filler)')];
    if (!cells.length) { this.sel = null; this._detail(); this.ui._focus(this.slotBtns.weapon, true); return; }
    let best = cells.find((c) => Number(c.dataset.i) === index) || cells[Math.min(cells.length - 1, Math.max(0, cells.findIndex((c) => Number(c.dataset.i) > index)))] || cells[0];
    this.sel = null;
    this.ui._focus(best, true);
    this._select({ kind: 'inv', index: Number(best.dataset.i) }, true);
  }

  _primary() {
    const g = this.g, sel = this.sel, inst = this._inst(), def = defOf(inst);
    if (!g || !g.player || !sel || sel.kind !== 'inv' || !def) return;
    try {
      if (def.slot) { g.player.equip(sel.index); this.ui.sfx('ui_equip'); }
      else if (def.type === 'consumable' || def.tool) { if (g.useItem(sel.index) === false) { this.ui.sfx('ui_error'); return; } }
      else return;
    } catch (e) { console.error('[ui] item action', e); }
    this._refocus(sel.index);
  }

  _unequip(slot) {
    const g = this.g;
    if (!g || !g.player || !(this.d.equipment || {})[slot]) return;
    try { g.player.unequip(slot); this.ui.sfx('ui_equip'); } catch (e) { console.error(e); }
    this.refresh();
    this.sel = null; this._select({ kind: 'eq', slot }, true);
  }

  async _drop() {
    const g = this.g, sel = this.sel, inst = this._inst(), def = defOf(inst);
    if (!g || !sel || sel.kind !== 'inv' || !inst || (def && def.type === 'key')) return;
    const ok = await this.ui.confirm({ title: 'Jeter cet objet ?', text: nameOf(inst) + (inst.qty > 1 ? ` ×${inst.qty}` : '') + ' sera perdu définitivement.', yes: 'Jeter', no: 'Garder', danger: true });
    if (!ok) return;
    try { g.dropItem(sel.index); } catch (e) { console.error(e); }
    this._refocus(sel.index);
  }

  onKey(e) {
    const a = document.activeElement;
    if (!a || !this.el.contains(a)) return false;
    if (e.code === 'Enter' || e.code === 'NumpadEnter') {
      if (a.classList.contains('v-cell')) { this._primary(); return true; }
      if (a.classList.contains('v-slot')) { this._unequip(a.dataset.slot); return true; }
    }
    if ((e.code === 'Delete' || e.code === 'Backspace') && a.classList.contains('v-cell')) { this._drop(); return true; }
    return false;
  }
}

// ================================================================================================ character
const DERIVED = [
  ['Vie maximale', (s) => s.maxHp, (v) => num(v), 'heart'],
  ['Souffle maximal', (s) => s.maxSt, (v) => num(v), 'bolt'],
  ['Éclat maximal', (s) => s.maxMana, (v) => num(v), 'crystal'],
  ['Attaque', (s) => s.attack, (v) => num(v), 'sword'],
  ['Coup critique', (s) => s.crit * 100, (v) => num(v, 1) + ' %', 'target'],
  ['Puissance d\'Éclat', (s) => s.skillPower * 100, (v) => num(v) + ' %', 'flame'],
  ['Défense', (s) => s.def, (v) => num(v), 'chest'],
  ['Équilibre', (s) => s.poise, (v) => num(v), 'weight'],
  ['Garde', (s) => s.block * 100, (v) => num(v) + ' %', 'shield'],
  ['Stabilité', (s) => s.stability, (v) => num(v, 1), 'shield'],
  ['Charge portée', (s) => s.capacity, (v) => num(v, 1), 'bag'],
  ['Regain de souffle', (s) => s.staminaRegen, (v) => num(v, 1) + ' /s', 'bolt'],
  ['Soin de la fiole', (s) => s.flaskHeal * 100, (v) => num(v) + ' %', 'flask'],
];

class CharacterTab {
  constructor(hub) {
    this.hub = hub; this.ui = hub.ui;
    this.pending = {};
    this.slotSel = 0;
    this.identity = h('div.v-char-id');
    this.attrsEl = h('div.v-char-attrs');
    this.attrDesc = h('p.v-char-attrdesc');
    this.confirmEl = h('div.v-char-confirm');
    this.derivedEl = h('div.v-char-derived');
    this.slotsEl = h('div.v-char-slots');
    this.skillsEl = h('div.v-char-skills.v-scroll');
    this.el = h('div.v-page.v-char', null,
      h('section.v-box.v-char-left', null, this.identity, h('h4.v-box-title', { text: 'Attributs' }), this.attrsEl, this.attrDesc, this.confirmEl),
      h('section.v-box.v-char-mid', null, h('h4.v-box-title', { text: 'Caractéristiques' }), this.derivedEl),
      h('section.v-box.v-char-right', null, h('h4.v-box-title', { text: 'Pouvoirs d\'Éclat' }), this.slotsEl, h('div.v-rule'), this.skillsEl));
  }
  get g() { return this.hub.game; }
  get d() { const g = this.g; return g && g.player ? g.player.data : null; }
  hints() { return [['Entrée', 'Valider'], ['← →', 'Répartir']]; }
  defaultFocus() { return this.attrsEl.querySelector('button:not([disabled])') || this.slotsEl.querySelector('button'); }
  show() { this.pending = {}; this.refresh(); }
  onEvent() { this.refresh(); }
  _spent() { let n = 0; for (const k in this.pending) n += this.pending[k]; return n; }

  refresh() {
    const d = this.d;
    if (!d) return;
    const focusKey = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.k : null;
    const pts = Math.max(0, (d.attrPoints || 0) - this._spent());
    const o = ORIGINS.find((x) => x.id === d.origin);
    const need = xpForLevel(d.level || 1) || 1;
    clear(this.identity);
    add(this.identity, 
      h('div.v-char-name', { text: d.name || 'Veilleur' }),
      h('div.v-char-origin', { text: o ? o.name : '' }),
      h('div.v-char-level', null, h('span.v-char-lv', null, 'Niveau ', h('b', { text: String(d.level || 1) })),
        h('span.v-char-xp', { text: `${num(d.xp || 0)} / ${num(need)} exp.` })),
      h('div.v-char-xpbar', null, h('i', { style: { width: clamp((d.xp || 0) / need * 100, 0, 100).toFixed(1) + '%' } })),
      h('div.v-char-points' + (d.attrPoints > 0 ? '.has' : ''), null, h('span', { html: icon('attributes') }), d.attrPoints > 0 ? (pts > 0 ? `${pts} point${pts > 1 ? 's' : ''} à répartir` : 'Points répartis : confirmez') : 'Aucun point à répartir'));

    clear(this.attrsEl);
    for (const [key, label, desc] of ATTRS) {
      const base = (d.attrs && d.attrs[key]) || 0, add = this.pending[key] || 0;
      const describe = () => { this.attrDesc.textContent = `${label} — ${desc}`; };
      const minus = h('button.v-attr-btn', { nav: true, type: 'button', 'data-k': key + '-', 'aria-label': 'Retirer un point', html: icon('minus'), onclick: () => this._add(key, -1), onfocus: describe });
      const plus = h('button.v-attr-btn.plus', { nav: true, type: 'button', 'data-k': key + '+', 'aria-label': 'Ajouter un point', html: icon('plus'), onclick: () => this._add(key, 1), onfocus: describe });
      minus.disabled = add <= 0;
      plus.disabled = pts <= 0 || base + add >= 50;
      const row = h('div.v-attr' + (add ? '.changed' : ''), { onmouseenter: describe },
        h('span.v-attr-name', { text: label }),
        h('span.v-attr-val', null, String(base + add), add ? h('small', { text: ' +' + add }) : null),
        d.attrPoints > 0 ? h('span.v-attr-btns', null, minus, plus) : null);
      this.attrsEl.appendChild(row);
    }
    if (!this.attrDesc.textContent) this.attrDesc.textContent = d.attrPoints > 0 ? 'Chaque niveau accorde un point. Répartissez-les, puis confirmez.' : 'Gagnez de l\'expérience pour monter de niveau et renforcer vos attributs.';
    clear(this.confirmEl);
    if (this._spent() > 0) {
      add(this.confirmEl, 
        h('button.v-btn.primary', { nav: true, type: 'button', 'data-k': 'ok', text: 'Confirmer', onclick: () => this._confirm() }),
        h('button.v-btn.ghost', { nav: true, type: 'button', 'data-k': 'no', text: 'Annuler', onclick: () => { this.pending = {}; this.refresh(); } }));
    }
    this._derived();
    this._skills();
    if (focusKey) { const again = this.el.querySelector(`[data-k="${focusKey}"]`); if (again && !again.disabled) again.focus({ preventScroll: true }); else { const f = this.defaultFocus(); if (f && this.ui.top === this.hub) f.focus({ preventScroll: true }); } }
  }

  _add(key, n) {
    const d = this.d;
    if (!d) return;
    const cur = this.pending[key] || 0;
    if (n > 0 && (this._spent() >= (d.attrPoints || 0) || (d.attrs[key] || 0) + cur >= 50)) { this.ui.sfx('ui_error'); return; }
    if (n < 0 && cur <= 0) return;
    this.pending[key] = cur + n;
    if (!this.pending[key]) delete this.pending[key];
    this.refresh();
  }

  _confirm() {
    const g = this.g, p = g && g.player;
    if (!p) return;
    let okAll = true;
    for (const key in this.pending) for (let i = 0; i < this.pending[key]; i++) { try { if (p.spendPoint(key) === false) okAll = false; } catch (e) { okAll = false; console.error(e); } }
    this.pending = {};
    this.ui.sfx(okAll ? 'ui_save' : 'ui_error');
    this.refresh();
  }

  _derived() {
    const g = this.g, d = this.d, p = g && g.player;
    clear(this.derivedEl);
    if (!d) return;
    let cur = null, next = null;
    try { cur = derive(d); } catch (e) { cur = p && p.st; }
    if (!cur) return;
    if (this._spent() > 0) { const attrs = { ...d.attrs }; for (const k in this.pending) attrs[k] = (attrs[k] || 0) + this.pending[k]; try { next = derive({ ...d, attrs }); } catch (e) { next = null; } }
    for (const [label, get, fmt, glyph] of DERIVED) {
      let a, b = null;
      try { a = get(cur); if (next) b = get(next); } catch (e) { continue; }
      if (label === 'Soin de la fiole') { a += (d.flaskLevel || 0) * 8; if (b !== null) b += (d.flaskLevel || 0) * 8; }
      const changed = b !== null && Math.abs(b - a) > 0.004;
      add(this.derivedEl, h('div.v-der' + (changed ? '.changed' : ''), null, h('span.v-der-ico', { html: icon(glyph) }), h('span.v-der-label', { text: label }),
        h('span.v-der-val', { text: fmt(a) }), changed ? h('span.v-der-next.' + (b > a ? 'up' : 'down'), null, '→ ', fmt(b)) : null));
    }
    const load = cur.load || 0;
    add(this.derivedEl, h('div.v-der', null, h('span.v-der-ico', { html: icon('weight') }), h('span.v-der-label', { text: 'Charge actuelle' }), h('span.v-der-val', { text: `${num(cur.weight, 1)} · ${Math.round(load * 100)} % (${loadLabel(load)})` })));
  }

  _skills() {
    const g = this.g, d = this.d;
    clear(this.slotsEl); clear(this.skillsEl);
    if (!d) return;
    const slots = d.skillSlots || [null, null, null];
    for (let i = 0; i < 3; i++) {
      const id = slots[i], sk = id && SKILLS[id];
      const b = h('button.v-pslot' + (i === this.slotSel ? '.sel' : '') + (id ? '' : '.empty'), { nav: true, type: 'button', 'data-k': 'slot' + i, title: sk ? sk.name : 'Emplacement vide', onclick: () => { if (this.slotSel === i && id) { this._assign(i, null); } else { this.slotSel = i; this._skills(); const again = this.slotsEl.querySelector(`[data-k="slot${i}"]`); if (again) again.focus({ preventScroll: true }); } } },
        h('span.v-pslot-ico', { html: id ? skillIcon(id) : '', style: { color: SKILL_TINT[id] || '' } }),
        h('kbd.v-key.sm', { text: this.ui.keyLabel('skill' + (i + 1)) }),
        h('span.v-pslot-name', { text: sk ? sk.name : 'Vide' }));
      this.slotsEl.appendChild(b);
    }
    this.slotsEl.appendChild(h('p.v-pslot-note', { text: 'Choisissez un emplacement, puis un pouvoir. Cliquez de nouveau sur un emplacement pour le vider.' }));
    const known = d.skills || [];
    if (!known.length) { add(this.skillsEl, h('div.v-empty', null, h('span', { html: icon('crystal') }), h('p', { text: 'Aucun pouvoir pour l\'instant. Les Éclats arrachés à leurs gardiens vous en confieront.' }))); return; }
    for (const id of known) {
      const sk = SKILLS[id];
      const at = slots.indexOf(id);
      const b = h('button.v-skillrow' + (at >= 0 ? '.assigned' : ''), { nav: true, type: 'button', 'data-k': 'sk' + id, onclick: () => this._assign(this.slotSel, id) },
        h('span.v-skillrow-ico', { html: skillIcon(id), style: { color: SKILL_TINT[id] || '' } }),
        h('span.v-skillrow-body', null,
          h('span.v-skillrow-name', null, sk ? sk.name : id, at >= 0 ? h('span.v-skillrow-slot', { text: 'Emplacement ' + (at + 1) }) : null),
          h('span.v-skillrow-desc', { text: sk ? sk.desc : '' }),
          sk ? h('span.v-skillrow-meta', null, h('span.eclat', { text: `${sk.cost} Éclat` }), h('span', { text: `Recharge ${num(sk.cd, sk.cd % 1 ? 1 : 0)} s` })) : null));
      this.skillsEl.appendChild(b);
    }
    void g;
  }

  _assign(slot, id) {
    const g = this.g;
    if (!g || typeof g.setSkillSlot !== 'function') return;
    try { g.setSkillSlot(slot, id); this.ui.sfx('ui_equip'); } catch (e) { console.error(e); }
    if (id) this.slotSel = Math.min(2, slot);
    this._skills();
    const again = this.el.querySelector(`[data-k="${id ? 'sk' + id : 'slot' + slot}"]`);
    if (again) again.focus({ preventScroll: true });
  }

  onBack() {
    if (this._spent() > 0) { this.pending = {}; this.refresh(); return true; }
    return false;
  }
}

// ================================================================================================ map
class MapTab {
  constructor(hub) {
    this.hub = hub; this.ui = hub.ui;
    this.s = 1; this.tx = 0; this.ty = 0; this.vw = 0; this.vh = 0; this.size = 1024; this.k = 0.2;
    this.target = null;                       // selected shrine id (fast travel)
    this.img = h('img.v-map-img', { alt: '', draggable: 'false' });
    this.marks = h('div.v-map-marks');
    this.layer = h('div.v-map-layer', null, this.img, this.marks);
    this.view = h('div.v-map-view', { nav: true, tabindex: 0 }, this.layer);
    this.where = h('div.v-map-where');
    this.zoomEl = h('div.v-map-zoom', null,
      h('button.v-btn.icon', { type: 'button', 'aria-label': 'Zoom avant', html: icon('plus'), onclick: () => this._zoomBy(1.3) }),
      h('button.v-btn.icon', { type: 'button', 'aria-label': 'Zoom arrière', html: icon('minus'), onclick: () => this._zoomBy(1 / 1.3) }),
      h('button.v-btn.icon', { type: 'button', 'aria-label': 'Centrer sur le personnage', title: 'Centrer sur le personnage', html: icon('target'), onclick: () => this._centerOnPlayer(true) }));
    this.legend = h('div.v-map-legend', null,
      [['player', 'Vous', 'up'], ['shrine', 'Autel de Braise', 'flame'], ['arena', 'Antre d\'un gardien', 'skull'], ['quest', 'Objectif de quête', 'diamond']].map(([c, t, g]) => h('span.v-legend', null, h('span.v-legend-ico.' + c, { html: icon(g) }), t)));
    this.sideTitle = h('h4.v-box-title');
    this.sideNote = h('p.v-map-note');
    this.sideList = h('div.v-map-list.v-scroll');
    this.travelBtn = h('button.v-btn.primary', { nav: true, type: 'button', text: 'Voyager', onclick: () => this._travel() });
    this.el = h('div.v-page.v-map', null,
      h('section.v-box.v-map-main', null, this.view, this.where, this.zoomEl, this.legend),
      h('section.v-box.v-map-side', null, this.sideTitle, this.sideNote, this.sideList, this.travelBtn));
    this._bind();
  }
  get g() { return this.hub.game; }
  hints() { return [['Glisser', 'Déplacer'], ['Molette', 'Zoom']]; }
  defaultFocus() { return this.sideList.querySelector('button:not([disabled])') || this.view; }

  show() {
    this.target = null;
    this.refresh();
    // the page is visible when show() runs, so the view can be measured now (once per opening, never per frame);
    // if it is not laid out yet, update() retries on the following frames
    this._fit = this._doFit(true) ? 0 : 2;
  }
  /** re-read the map data without moving the view */
  refresh() {
    const g = this.g;
    let m = null;
    try { m = g && typeof g.map === 'function' ? g.map() : null; } catch (e) { m = null; }
    this.data = m;
    if (m && m.image && m.image.src && this.img.getAttribute('src') !== m.image.src) this.img.src = m.image.src;
    const nat = m && m.image && m.image.naturalWidth ? m.image.naturalWidth : 1024;
    this.size = 1024; this.k = this.size / 5120;
    this.layer.style.width = this.layer.style.height = this.size + 'px';
    void nat;
    this._marks();
    this._side();
    const reg = g && g.region && g.region.name ? g.region.name : '';
    this.where.textContent = [reg, g && typeof g.day === 'number' ? 'Jour ' + g.day : '', g ? hourStr(g.hour) : ''].filter(Boolean).join(' · ');
    if (this.vw) this._apply();
  }
  onResize() { this._fit = 1; }
  onEvent(type) { if (type === 'quest') this.refresh(); }
  update() {
    if (this._fit > 0 && --this._fit === 0 && !this._doFit(!this._keep)) this._fit = 1;
  }
  /** measure the view and place the map; `recenter` puts the player in the middle at the default zoom */
  _doFit(recenter) {
    this.vw = this.view.clientWidth; this.vh = this.view.clientHeight;
    if (!this.vw || !this.vh) return false;
    this.min = Math.max(this.vw, this.vh) / this.size * 0.62;
    this.max = Math.max(3.2, this.min * 5);
    if (recenter) { this.s = clamp(this.min * 2.1, this.min, this.max); this._centerOnPlayer(false); }
    else this.s = clamp(this.s, this.min, this.max);
    this._apply();
    this._keep = true;
    return true;
  }
  toPx(x, z) { return [(x + 2560) * this.k, (z + 2560) * this.k]; }

  _marks() {
    const m = this.data;
    clear(this.marks);
    if (!m) return;
    const g = this.g;
    const mark = (cls, x, z, glyph, label, extra) => {
      const [px, py] = this.toPx(x, z);
      const el = h('div.v-mark.' + cls, { style: { left: px.toFixed(1) + 'px', top: py.toFixed(1) + 'px' } }, glyph ? h('span.v-mark-ico', { html: icon(glyph) }) : h('span.v-mark-dot'), label ? h('span.v-mark-label', { text: label }) : null);
      if (extra) Object.assign(el.dataset, extra);
      this.marks.appendChild(el);
      return el;
    };
    // places are written on the map like on a chart (a dot and a name); only the lairs get an icon
    for (const p of m.pois || []) if (p && p.found) { if (p.type === 'arena') mark('poi.arena', p.x, p.z, 'skull', p.name); else mark('poi.place', p.x, p.z, null, p.name); }
    const here = g && g.shrine ? g.shrine.id : null;
    for (const s of m.shrines || []) if (s && s.found) mark('shrine' + (s.id === here ? '.here' : ''), s.x, s.z, 'flame', s.name, { id: s.id });
    for (const q of m.quests || []) if (q) mark('quest' + (q.tracked ? '.tracked' : ''), q.x, q.z, 'diamond', q.name);
    if (m.player) {
      const [px, py] = this.toPx(m.player.x, m.player.z);
      const el = h('div.v-mark.player', { style: { left: px.toFixed(1) + 'px', top: py.toFixed(1) + 'px' } }, h('span.v-mark-arrow', { style: { transform: `rotate(${(180 - (m.player.yaw || 0) * 180 / Math.PI).toFixed(1)}deg)` }, html: '<svg viewBox="0 0 24 24"><path d="M12 2l7 18-7-4.500L5 20z"/></svg>' }));
      this.marks.appendChild(el);
    }
  }

  _side() {
    const g = this.g, m = this.data;
    const can = !!(g && g.canFastTravel);
    const here = g && g.shrine ? g.shrine.id : null;
    this.sideTitle.textContent = can ? 'Voyage rapide' : 'Autels découverts';
    this.sideNote.textContent = can ? 'Choisissez un Autel embrasé. Le voyage vous y dépose, reposé.' : 'Reposez-vous à un Autel de Braise pour voyager entre les Autels embrasés.';
    clear(this.sideList);
    const found = ((m && m.shrines) || []).filter((s) => s && s.found);
    const px = m && m.player ? m.player.x : 0, pz = m && m.player ? m.player.z : 0;
    found.sort((a, b) => Math.hypot(a.x - px, a.z - pz) - Math.hypot(b.x - px, b.z - pz));
    for (const s of found) {
      const dist = Math.hypot(s.x - px, s.z - pz);
      const b = h('button.v-map-item' + (s.id === here ? '.here' : '') + (s.id === this.target ? '.sel' : ''), { nav: true, type: 'button', 'data-id': s.id, onclick: () => this._pick(s), onfocus: () => this._focusOn(s.x, s.z) },
        h('span.v-map-item-ico', { html: icon('flame') }),
        h('span.v-map-item-body', null, h('span.v-map-item-name', { text: s.name }), h('span.v-map-item-dist', { text: s.id === here ? 'Vous êtes ici' : dist >= 1000 ? num(dist / 1000, 1) + ' km' : Math.round(dist / 10) * 10 + ' m' })));
      this.sideList.appendChild(b);
    }
    if (!found.length) add(this.sideList, h('div.v-empty', null, h('span', { html: icon('flame') }), h('p', { text: 'Aucun Autel embrasé.' })));
    const pois = ((m && m.pois) || []).filter((p) => p && p.found && p.type !== 'arena');
    if (!can && pois.length) {
      add(this.sideList, h('h5.v-csec', { text: 'Lieux' }));
      for (const p of pois) add(this.sideList, h('button.v-map-item.place', { nav: true, type: 'button', onclick: () => this._focusOn(p.x, p.z, true), onfocus: () => this._focusOn(p.x, p.z) },
        h('span.v-map-item-ico', { html: icon(POI_GLYPH[p.type] || 'pin') }), h('span.v-map-item-body', null, h('span.v-map-item-name', { text: p.name }), h('span.v-map-item-dist', { text: POI_KIND[p.type] || 'Lieu' }))));
    }
    this.travelBtn.hidden = !can;
    this._travelState();
  }

  _travelState() {
    const g = this.g, here = g && g.shrine ? g.shrine.id : null;
    const s = this.target && this.data ? (this.data.shrines || []).find((x) => x.id === this.target) : null;
    this.travelBtn.disabled = !s || s.id === here;
    this.travelBtn.textContent = s && s.id !== here ? 'Voyager vers ' + s.name.replace(/^Autel\s+/, 'l\'Autel ') : 'Choisissez une destination';
    for (const b of this.sideList.querySelectorAll('.v-map-item')) b.classList.toggle('sel', !!this.target && b.dataset.id === this.target);
    for (const el of this.marks.querySelectorAll('.v-mark.shrine')) el.classList.toggle('sel', !!this.target && el.dataset.id === this.target);
  }

  _pick(s) {
    const g = this.g;
    this._focusOn(s.x, s.z, true);
    if (!g || !g.canFastTravel) return;
    if (this.target === s.id) { this._travel(); return; }
    this.target = s.id;
    this._travelState();
  }

  async _travel() {
    const g = this.g, id = this.target;
    const s = id && this.data ? (this.data.shrines || []).find((x) => x.id === id) : null;
    if (!g || !g.canFastTravel || !s) return;
    const ok = await this.ui.confirm({ title: 'Voyager ?', text: `Rejoindre ${s.name.replace(/^Autel\s+/, "l'Autel ")}. Les ennemis abattus se relèveront.`, yes: 'Voyager', no: 'Annuler' });
    if (!ok) return;
    try { g.fastTravel(id); } catch (e) { console.error('[ui] fastTravel', e); }
    this.ui.close(this.hub);
  }

  // ---- view transform
  _apply() {
    const w = this.size * this.s;
    this.tx = w <= this.vw ? (this.vw - w) / 2 : clamp(this.tx, this.vw - w, 0);
    this.ty = w <= this.vh ? (this.vh - w) / 2 : clamp(this.ty, this.vh - w, 0);
    this.layer.style.transform = `translate3d(${this.tx.toFixed(1)}px,${this.ty.toFixed(1)}px,0) scale(${this.s.toFixed(4)})`;
    this.layer.style.setProperty('--inv', (1 / this.s).toFixed(4));
    this.layer.classList.toggle('far', this.s < this.min * 1.45);
  }
  _centerOn(x, z) { const [px, py] = this.toPx(x, z); this.tx = this.vw / 2 - px * this.s; this.ty = this.vh / 2 - py * this.s; }
  _centerOnPlayer(apply) { const m = this.data; if (m && m.player) this._centerOn(m.player.x, m.player.z); if (apply) this._glide(); }
  _focusOn(x, z, zoom) { if (!this.vw) return; if (zoom && this.s < this.min * 2) this.s = clamp(this.min * 2.4, this.min, this.max); this._centerOn(x, z); this._glide(); }
  _glide() { this.layer.classList.add('glide'); this._apply(); clearTimeout(this._gt); this._gt = setTimeout(() => this.layer.classList.remove('glide'), 260); }
  _zoomBy(f, cx = this.vw / 2, cy = this.vh / 2, glide = true) {
    const ns = clamp(this.s * f, this.min || 0.3, this.max || 3);
    if (ns === this.s) return;
    this.tx = cx - (cx - this.tx) * ns / this.s; this.ty = cy - (cy - this.ty) * ns / this.s;
    this.s = ns;
    if (glide) this._glide(); else this._apply();
  }
  _bind() {
    const v = this.view;
    let drag = false, lx = 0, ly = 0, rect = null;
    v.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      drag = true; lx = e.clientX; ly = e.clientY;
      try { v.setPointerCapture(e.pointerId); } catch (err) { /* synthetic */ }
      v.classList.add('dragging'); this.layer.classList.remove('glide');
    });
    v.addEventListener('pointermove', (e) => {
      if (!drag) return;
      this.tx += e.clientX - lx; this.ty += e.clientY - ly; lx = e.clientX; ly = e.clientY;
      this._apply();
    });
    const end = () => { drag = false; v.classList.remove('dragging'); };
    v.addEventListener('pointerup', end); v.addEventListener('pointercancel', end);
    v.addEventListener('wheel', (e) => {
      e.preventDefault();
      rect = v.getBoundingClientRect();
      this._zoomBy(e.deltaY < 0 ? 1.18 : 1 / 1.18, e.clientX - rect.left, e.clientY - rect.top, false);
    }, { passive: false });
    v._adjust = (dir) => { this.tx -= dir * 60; this._glide(); };
  }
  onKey(e) {
    if (document.activeElement !== this.view) return false;
    if (e.code === 'ArrowUp') { this.ty += 60; this._glide(); return true; }
    if (e.code === 'ArrowDown') { this.ty -= 60; this._glide(); return true; }
    if (e.code === 'NumpadAdd' || e.code === 'Equal') { this._zoomBy(1.3); return true; }
    if (e.code === 'NumpadSubtract' || e.code === 'Minus') { this._zoomBy(1 / 1.3); return true; }
    return false;
  }
}

// ================================================================================================ journal
class JournalTab {
  constructor(hub) {
    this.hub = hub; this.ui = hub.ui;
    this.mode = 'quests';
    this.selQuest = null; this.selCodex = null;
    this.modeBtns = {};
    const seg = h('div.v-chips.seg');
    for (const [id, label] of [['quests', 'Quêtes'], ['codex', 'Codex']]) { const b = h('button.v-chip', { nav: true, type: 'button', text: label, onclick: () => { this.mode = id; this.refresh(); } }); this.modeBtns[id] = b; seg.appendChild(b); }
    this.count = h('span.v-journal-count');
    this.list = h('div.v-journal-list.v-scroll');
    this.detail = h('div.v-journal-detail.v-scroll');
    this.el = h('div.v-page.v-journal', null,
      h('section.v-box.v-journal-left', null, h('div.v-journal-bar', null, seg, this.count), this.list),
      h('section.v-box.v-journal-right', null, this.detail));
  }
  get g() { return this.hub.game; }
  hints() { return [['Entrée', 'Sélectionner']]; }
  defaultFocus() { return this.list.querySelector('button.sel') || this.list.querySelector('button:not([disabled])') || this.modeBtns[this.mode]; }
  show() { this.refresh(); }
  onEvent(type) { if (type === 'quest') this.refresh(); }

  refresh() {
    for (const k in this.modeBtns) this.modeBtns[k].classList.toggle('on', k === this.mode);
    if (this.mode === 'quests') this._quests(); else this._codex();
  }

  _quests() {
    const g = this.g;
    let list = [];
    try { list = (g && g.quests && typeof g.quests.list === 'function' ? g.quests.list() : []) || []; } catch (e) { list = []; }
    clear(this.list);
    const active = list.filter((q) => q.state !== 'done'), done = list.filter((q) => q.state === 'done');
    this.count.textContent = `${active.length} en cours · ${done.length} accomplie${done.length > 1 ? 's' : ''}`;
    if (!list.some((q) => q.id === this.selQuest)) { const t = list.find((q) => q.tracked) || active[0] || list[0]; this.selQuest = t ? t.id : null; }
    const addQuest = (q) => {
      const b = h('button.v-quest' + (q.id === this.selQuest ? '.sel' : '') + (q.state === 'done' ? '.done' : '') + (q.main ? '.main' : ''), { nav: true, type: 'button', onclick: () => { this.selQuest = q.id; this._quests(); const s = this.list.querySelector('.sel'); if (s) s.focus({ preventScroll: true }); } },
        h('span.v-quest-ico', { html: icon(q.state === 'done' ? 'check' : q.main ? 'attributes' : 'quest') }),
        h('span.v-quest-body', null, h('span.v-quest-title', { text: q.title || '' }), h('span.v-quest-kind', { text: (q.main ? 'Quête principale' : 'Quête secondaire') + (q.state === 'done' ? ' · accomplie' : '') })),
        q.tracked ? h('span.v-quest-tracked', { title: 'Quête suivie', html: icon('diamond') }) : null);
      this.list.appendChild(b);
    };
    if (active.length) { add(this.list, h('h5.v-csec', { text: 'En cours' })); active.forEach(addQuest); }
    if (done.length) { add(this.list, h('h5.v-csec', { text: 'Accomplies' })); done.forEach(addQuest); }
    if (!list.length) add(this.list, h('div.v-empty', null, h('span', { html: icon('quest') }), h('p', { text: 'Aucune quête. Parlez aux survivants de Valombre.' })));
    const q = list.find((x) => x.id === this.selQuest);
    clear(this.detail);
    if (!q) { add(this.detail, h('div.v-empty', null, h('span', { html: icon('book') }), h('p', { text: 'Votre journal est vierge.' }))); return; }
    const steps = q.steps || [];
    const cur = steps.findIndex((s) => !s.done);
    add(this.detail, 
      h('div.v-kicker', { text: q.main ? 'Quête principale' : 'Quête secondaire' }),
      h('h3.v-journal-title', { text: q.title || '' }),
      rule(),
      h('p.v-journal-desc', { text: q.desc || '' }),
      h('h5.v-csec', { text: 'Étapes' }),
      h('ol.v-steps', null, steps.map((s, i) => h('li.v-step' + (s.done ? '.done' : i === cur ? '.cur' : ''), null, h('span.v-step-ico', { html: icon(s.done ? 'check' : i === cur ? 'right' : 'minus') }), h('span', { text: s.text })))),
      q.state === 'done' ? h('div.v-journal-state', null, h('span', { html: icon('check') }), 'Quête accomplie')
        : q.tracked ? h('div.v-journal-state.tracked', null, h('span', { html: icon('diamond') }), 'Quête suivie — indiquée sur la boussole')
          : h('button.v-btn.primary', { nav: true, type: 'button', text: 'Suivre cette quête', onclick: () => { try { g.quests.track(q.id); } catch (e) { console.error(e); } this._quests(); } }));
  }

  _codex() {
    const g = this.g;
    let list = [];
    try { list = (g && typeof g.codex === 'function' ? g.codex() : []) || []; } catch (e) { list = []; }
    clear(this.list);
    const found = list.filter((c) => c.found).length;
    this.count.textContent = `${found} / ${list.length} entrées`;
    if (!list.some((c) => c.id === this.selCodex && c.found)) { const f = list.find((c) => c.found); this.selCodex = f ? f.id : null; }
    const cats = [];
    for (const c of list) if (!cats.includes(c.category)) cats.push(c.category);
    for (const cat of cats) {
      const entries = list.filter((c) => c.category === cat);
      add(this.list, h('h5.v-csec', null, cat, h('small', { text: ` ${entries.filter((c) => c.found).length}/${entries.length}` })));
      for (const c of entries) {
        if (!c.found) { add(this.list, h('div.v-codex.unknown', null, h('span.v-quest-ico', { html: icon('lock') }), h('span.v-quest-title', { text: '???' }))); continue; }
        add(this.list, h('button.v-codex' + (c.id === this.selCodex ? '.sel' : ''), { nav: true, type: 'button', onclick: () => { this.selCodex = c.id; this._codex(); const s = this.list.querySelector('.sel'); if (s) s.focus({ preventScroll: true }); } },
          h('span.v-quest-ico', { html: icon('book') }), h('span.v-quest-title', { text: c.title || '' })));
      }
    }
    if (!list.length) add(this.list, h('div.v-empty', null, h('span', { html: icon('book') }), h('p', { text: 'Le codex est vide.' })));
    const c = list.find((x) => x.id === this.selCodex && x.found);
    clear(this.detail);
    if (!c) { add(this.detail, h('div.v-empty', null, h('span', { html: icon('lock') }), h('p', { text: 'Explorez Valombre pour remplir le codex.' }))); return; }
    add(this.detail, h('div.v-kicker', { text: c.category || 'Codex' }), h('h3.v-journal-title', { text: c.title || '' }), rule(), h('p.v-journal-desc.lore', { text: c.text || '' }));
  }
}
