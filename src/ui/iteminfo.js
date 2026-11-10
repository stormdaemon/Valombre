// VALOMBRE UI — item texts, stat rows and comparisons shared by the inventory, the shop and the forge.
import { add, h, num, signed } from './dom.js';
import { icon, itemIcon, itemRarity } from './icons.js';
import { ITEMS, itemName, upgradeMult } from '../game/data/items.js';
import { derive, STATUS } from '../game/data/rules.js';

export const TYPE_LABEL = { weapon: 'Arme', shield: 'Bouclier', armor: 'Armure', consumable: 'Consommable', material: 'Matériau', key: 'Objet clé' };
export const CLASS_LABEL = { sword: 'Épée', dagger: 'Dague', axe: 'Hache', mace: 'Masse', greataxe: 'Grande hache', greatsword: 'Espadon', hammer: 'Marteau de guerre' };
export const SLOT_LABEL = { weapon: 'Arme', offhand: 'Bouclier', head: 'Tête', chest: 'Torse', legs: 'Jambes' };
export const SLOT_GLYPH = { weapon: 'sword', offhand: 'shield', head: 'helm', chest: 'chest', legs: 'legs' };
const RARITY_LABEL = { legend: 'Relique', rare: 'Ouvrage de maître', fine: 'Belle facture' };

export const defOf = (inst) => (inst && ITEMS[inst.id]) || null;
export const nameOf = (inst) => { try { return inst ? itemName(inst) : ''; } catch (e) { return inst ? String(inst.id) : ''; } };

export function scaleLetter(v) {
  return v >= 1 ? 'S' : v >= 0.75 ? 'A' : v >= 0.5 ? 'B' : v >= 0.3 ? 'C' : v >= 0.1 ? 'D' : v > 0 ? 'E' : '—';
}

export function typeLine(def) {
  if (!def) return 'Objet inconnu';
  if (def.type === 'weapon') return `${CLASS_LABEL[def.cls] || 'Arme'} · ${def.moveset === '2h' ? 'Deux mains' : 'Une main'}${def.unique ? ' · Relique' : ''}`;
  if (def.type === 'armor') return `Armure · ${SLOT_LABEL[def.slot] || ''}`;
  return TYPE_LABEL[def.type] || 'Objet';
}

export function loadLabel(load) {
  return load > 1 ? 'Surcharge' : load >= 0.75 ? 'Lourde' : load >= 0.4 ? 'Moyenne' : 'Légère';
}

/** what a consumable does, in plain French */
export function effectLines(def) {
  const e = def && def.effect;
  const out = [];
  if (!e) return out;
  if (e.heal) out.push(`Rend ${Math.round(e.heal * 100)} % de la vie`);
  if (e.regen) out.push(`Régénère la vie pendant ${e.time} s`);
  if (e.cure) out.push(`Dissipe : ${(STATUS[e.cure] && STATUS[e.cure].name) || e.cure}`);
  if (e.buff === 'sharp') out.push(`Dégâts d'arme +${Math.round((e.mult - 1) * 100)} % pendant ${e.time} s`);
  else if (e.buff === 'vigor') out.push(`Récupération du souffle +${Math.round((e.mult - 1) * 100)} % pendant ${e.time} s`);
  else if (e.buff) out.push(`Effet « ${e.buff} » pendant ${e.time} s`);
  if (e.throw) out.push(`Projectile : ${e.dmg} dégâts de feu dans un rayon de ${num(e.radius, 1)} m`);
  if (e.recall) out.push('Ramène au dernier Autel de Braise');
  return out;
}

/** derived stats of player data `d` with `inst` equipped in its slot (2H weapons free the off hand) */
export function previewEquip(d, inst) {
  const def = defOf(inst);
  if (!d || !def || !def.slot) return null;
  try {
    const eq = { ...(d.equipment || {}) };
    eq[def.slot] = { id: inst.id, up: inst.up || 0 };
    if (def.slot === 'weapon' && def.moveset === '2h') eq.offhand = null;
    return derive({ attrs: d.attrs, equipment: eq });
  } catch (e) { return null; }
}

/**
 * stat rows of an item instance: [{ key, label, value (number | null), text, better: 1 | -1 | 0 }]
 * `d` (player data) is optional: with it, weapons also get their effective attack.
 */
export function statRows(inst, d) {
  const def = defOf(inst);
  const rows = [];
  if (!def) return rows;
  const row = (key, label, value, text, better = 1) => rows.push({ key, label, value, text, better });
  if (def.type === 'weapon') {
    const base = def.dmg * upgradeMult(inst.up || 0);
    row('dmg', 'Dégâts', base, num(base));
    if (d) { const st = previewEquip(d, inst); if (st) row('atk', 'Attaque effective', st.attack, num(st.attack)); }
    const sc = def.sc || [0, 0];
    row('sc', 'Affinité', null, `Force ${scaleLetter(sc[0])} · Dextérité ${scaleLetter(sc[1])}${def.arcane ? ' · Arcane ' + scaleLetter(def.arcane) : ''}`, 0);
    row('st', 'Coût en souffle', def.st, num(def.st), -1);
    row('spd', 'Vitesse', def.spd, '×' + num(def.spd, 2));
    row('reach', 'Allonge', def.reach, num(def.reach, 2) + ' m');
    row('poise', 'Impact', def.poise, num(def.poise));
    row('crit', 'Coup critique', def.crit || 1.5, '×' + num(def.crit || 1.5, 1));
    if (def.bleed) row('fx', 'Effet', null, `Hémorragie (${def.bleed})`, 0);
    if (def.frost) row('fx', 'Effet', null, `Gel (${def.frost})`, 0);
  } else if (def.type === 'shield') {
    row('block', 'Absorption', def.block * 100, Math.round(def.block * 100) + ' %');
    row('stability', 'Stabilité', def.stability, num(def.stability));
  } else if (def.type === 'armor') {
    row('def', 'Défense', def.def, num(def.def));
    row('poisea', 'Équilibre', def.poise, num(def.poise));
    if (def.arcane) row('arc', 'Puissance d\'Éclat', def.arcane * 100, '+' + Math.round(def.arcane * 100) + ' %');
  }
  if (typeof def.weight === 'number') row('weight', 'Poids', def.weight, num(def.weight, 1), -1);
  return rows;
}

/** DOM: detail card body for an item instance. opts: { d, compare (instance), price, priceLabel, qty } */
export function itemCard(inst, opts = {}) {
  const def = defOf(inst);
  const box = h('div.v-card');
  if (!inst) { add(box, h('div.v-card-empty', null, h('span', { html: icon('bag') }), h('p', { text: opts.emptyText || 'Sélectionnez un objet.' }))); return box; }
  const cmp = opts.compare && opts.compare.id ? opts.compare : null;
  const cmpRows = cmp ? statRows(cmp, opts.d) : null;
  const rows = statRows(inst, opts.d);
  const rar = def ? RARITY_LABEL[itemRarity(def)] : '';
  add(box, 
    h('div.v-card-head', null,
      h('span.v-card-ico', { html: itemIcon(inst.id, 'lg') }),
      h('div.v-card-titles', null,
        h('h3.v-card-name', { text: nameOf(inst) || 'Objet inconnu' }),
        h('div.v-card-type', { text: typeLine(def) + (rar && !(def && def.unique) ? ' · ' + rar : '') }),
        opts.tag ? h('div.v-card-tag', { text: opts.tag }) : null)),
    def && def.desc ? h('p.v-card-desc', { text: def.desc }) : null);
  const fx = effectLines(def);
  if (fx.length) add(box, h('ul.v-card-fx', null, fx.map((t) => h('li', null, h('span', { html: icon('attributes') }), t))));
  if (rows.length) {
    const table = h('div.v-stats');
    if (cmp) add(table, h('div.v-stats-cmp', { text: 'Comparé à : ' + nameOf(cmp) }));
    for (const r of rows) {
      let delta = null;
      if (cmpRows && r.value !== null && r.better) {
        const o = cmpRows.find((x) => x.key === r.key);
        if (o && o.value !== null) {
          const dv = r.value - o.value;
          const digits = Math.abs(dv) < 10 && Math.abs(dv % 1) > 0.001 ? (Math.abs(dv) < 1 ? 2 : 1) : 0;
          if (Math.abs(dv) > 0.004) delta = h('span.v-delta.' + (dv * r.better > 0 ? 'up' : 'down'), null, h('span', { html: icon(dv > 0 ? 'up' : 'down') }), signed(dv, digits).replace(/^[+−±]/, ''));
          else delta = h('span.v-delta.same', { text: '=' });
        }
      }
      add(table, h('div.v-stat', null, h('span.v-stat-label', { text: r.label }), h('span.v-stat-val', { text: r.text }), delta || h('span.v-delta')));
    }
    add(box, table);
  }
  const meta = h('div.v-card-meta');
  if (def && def.value > 0 && opts.price === undefined) add(meta, h('span', null, h('span', { html: icon('coin') }), `Valeur ${num(def.value)}`));
  if (opts.price !== undefined) add(meta, h('span.v-card-price', null, h('span', { html: icon('coin') }), `${opts.priceLabel || 'Prix'} ${num(opts.price)}`));
  if (opts.qty > 1) add(meta, h('span', { text: `Possédé : ${opts.qty}` }));
  if (meta.childNodes.length) add(box, meta);
  return box;
}
