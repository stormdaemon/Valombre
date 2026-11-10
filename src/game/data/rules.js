// Game rules: attributes, origins (starting classes), shard powers, difficulty, regions, formulas.
import { ITEMS, upgradeMult } from './items.js';

export const ATTRS = [
  ['vigueur', 'Vigueur', 'Augmente la vie maximale.'],
  ['endurance', 'Endurance', 'Augmente le souffle et la charge portée.'],
  ['force', 'Force', 'Dégâts des armes lourdes, garde plus solide.'],
  ['dexterite', 'Dextérité', 'Dégâts des armes légères, coups critiques.'],
  ['arcane', 'Arcane', 'Puissance et réserve des pouvoirs d\'Éclat, efficacité des fioles.'],
];

export const ORIGINS = [
  { id: 'veilleur', name: 'Veilleur déchu', desc: 'Dernier d\'un ordre de chevaliers qui gardaient les Autels de Braise. Équilibré, solide derrière son bouclier.',
    attrs: { vigueur: 12, endurance: 11, force: 12, dexterite: 10, arcane: 8 }, gear: { weapon: 'iron_sword', offhand: 'wood_shield', head: 'chain_head', chest: 'chain_chest', legs: 'chain_legs' }, items: [['bread', 2]], gold: 30 },
  { id: 'lame', name: 'Lame errante', desc: 'Mercenaire sans bannière, payé à la tête. Rapide, précis, peu protégé.',
    attrs: { vigueur: 10, endurance: 12, force: 9, dexterite: 14, arcane: 8 }, gear: { weapon: 'iron_sword', chest: 'leather_chest', legs: 'leather_legs', head: 'leather_head' }, items: [['dagger', 1], ['whetstone', 2]], gold: 60 },
  { id: 'bucheron', name: 'Bûcheron de Sombreronce', desc: 'Il abattait des chênes ; la forêt s\'est mise à rendre les coups. Lent et dévastateur.',
    attrs: { vigueur: 13, endurance: 10, force: 15, dexterite: 8, arcane: 7 }, gear: { weapon: 'woodcutter_axe', chest: 'peasant_chest', legs: 'peasant_legs' }, items: [['dried_meat', 3]], gold: 15 },
  { id: 'disciple', name: 'Disciple de l\'Astre', desc: 'Elle écoutait l\'Astre-Cœur chanter. Elle l\'entend encore, brisé. Fragile, mais l\'Éclat lui obéit.',
    attrs: { vigueur: 9, endurance: 10, force: 8, dexterite: 10, arcane: 16 }, gear: { weapon: 'mace', head: 'robe_head', chest: 'robe_chest', legs: 'robe_legs' }, items: [['herb_poultice', 2]], gold: 25, skill: 'ember_bolt' },
  { id: 'gueux', name: 'Gueux', desc: 'Ni nom, ni terre, ni maître. Un gourdin et la rage de vivre. Pour qui veut souffrir.',
    attrs: { vigueur: 10, endurance: 10, force: 10, dexterite: 10, arcane: 10 }, gear: { weapon: 'club', chest: 'peasant_chest', legs: 'peasant_legs' }, items: [['bread', 1]], gold: 0 },
];

// Shard powers. cost = Éclat (mana). type drives the effect in game/skills.js
export const SKILLS = {
  ember_bolt: { name: 'Trait de Braise', cost: 14, cd: 1.2, clip: 'cast', type: 'projectile', proj: 'fire', dmg: 34, sc: 2.2, status: ['burn', 8], desc: 'Projette une braise de l\'Autel. Enflamme la cible.' },
  wolf_howl: { name: 'Hurlement de l\'Alpha', cost: 22, cd: 18, clip: 'roar', type: 'buff', radius: 7, stagger: 60, buff: 'fury', mult: 1.25, time: 14, desc: 'Un hurlement qui fait vaciller les ennemis proches et attise vos coups.' },
  shadow_web: { name: 'Toile d\'Ombre', cost: 20, cd: 12, clip: 'cast', type: 'cone', range: 9, arc: 70, dmg: 18, sc: 1.2, status: ['slow', 6], desc: 'Des fils d\'ombre entravent tout ce qui vous fait face.' },
  drowned_tide: { name: 'Marée Noyée', cost: 30, cd: 16, clip: 'cast_big', type: 'wave', range: 16, width: 3.2, dmg: 70, sc: 3.0, knock: true, desc: 'Une lame d\'eau noire balaie le sol devant vous et renverse vos ennemis.' },
  frost_nova: { name: 'Givre du Colosse', cost: 34, cd: 20, clip: 'cast_big', type: 'nova', radius: 7, dmg: 60, sc: 2.6, status: ['frost', 40], desc: 'Le froid du col éclate autour de vous et fige les ennemis.' },
  ysolde_flame: { name: 'Flamme d\'Ysolde', cost: 38, cd: 14, clip: 'cast_big', type: 'pillar', range: 18, radius: 3.4, dmg: 120, sc: 4.0, status: ['burn', 14], desc: 'Une colonne de feu jaillit sous la cible.' },
};

export const DIFFICULTY = {
  story: { label: 'Conteur', dmgTaken: 0.55, dmgDealt: 1.35, enemyHp: 0.8, xp: 1.2 },
  normal: { label: 'Veilleur', dmgTaken: 1.0, dmgDealt: 1.0, enemyHp: 1.0, xp: 1.0 },
  hard: { label: 'Vétéran', dmgTaken: 1.45, dmgDealt: 0.9, enemyHp: 1.25, xp: 1.1 },
  nightmare: { label: 'Sans-Aube', dmgTaken: 2.2, dmgDealt: 0.8, enemyHp: 1.5, xp: 1.25 },
};

export const REGIONS = {
  ocean: { name: 'Mer des Brisants', level: [1, 1] },
  beach: { name: 'Côte de Valombre', level: [1, 6] },
  meadow: { name: 'Prés de Hautefeuille', level: [1, 6], desc: 'Des prairies grasses que plus personne ne fauche.' },
  forest: { name: 'Forêt de Sombreronce', level: [6, 12], desc: 'Les arbres y sont plus vieux que le royaume. Les toiles aussi.' },
  swamp: { name: 'Marais de Fangemort', level: [11, 18], desc: 'Le Vieux-Gué s\'est enfoncé là avec ses habitants. Ils ne sont pas tous restés au fond.' },
  mountain: { name: 'Pics de Givrelame', level: [15, 24], desc: 'Le vent du col porte la voix du Colosse.' },
  ash: { name: 'Landes Calcinées', level: [20, 30], desc: 'Là où le plus gros éclat de l\'Astre est tombé, la terre brûle encore.' },
  citadel: { name: 'Citadelle d\'Aubeclair', level: [28, 35], desc: 'Le trône des rois, sous un ciel sans aube.' },
};

export const STATUS = {
  poison: { name: 'Poison', color: '#8fd14f', dps: 0.012, time: 10 },      // dps = fraction of max hp per second
  burn: { name: 'Brûlure', color: '#ff7a2a', dps: 0.022, time: 5 },
  frost: { name: 'Gel', color: '#8fd8ff', slow: 0.55, stamina: 0.5, time: 8 },
  slow: { name: 'Entrave', color: '#a070ff', slow: 0.45, time: 6 },
  bleed: { name: 'Hémorragie', color: '#d03030', burst: 0.12, time: 0 },
};

// ---------------------------------------------------------------- formulas
export const MAX_LEVEL = 60;
export const xpForLevel = (lvl) => Math.round(70 * Math.pow(lvl, 1.62));      // xp needed to go from lvl to lvl+1
export const attrBonus = (v) => (v <= 10 ? (v - 10) * 0.03 : v <= 30 ? (v - 10) * 0.045 : 0.9 + (v - 30) * 0.02);   // soft cap at 30

/** Derived stats of a player state (see game/player.js for the state layout). */
export function derive(p) {
  const a = p.attrs, eq = p.equipment || {};
  const it = (slot) => (eq[slot] ? ITEMS[eq[slot].id] : null);
  const w = it('weapon'), sh = it('offhand');
  let def = 0, poise = 0, weight = 0, arcane = 0;
  for (const slot of ['head', 'chest', 'legs']) { const d = it(slot); if (d) { def += d.def; poise += d.poise; weight += d.weight; arcane += d.arcane || 0; } }
  if (w) weight += w.weight;
  if (sh) weight += sh.weight;
  const maxHp = Math.round(90 + a.vigueur * 13 + Math.max(0, a.vigueur - 20) * -3);
  const maxSt = Math.round(70 + a.endurance * 5.5);
  const maxMana = Math.round(30 + a.arcane * 6);
  const capacity = 18 + a.endurance * 1.6;
  const load = weight / capacity;
  let atk = 8;
  if (w) {
    const up = upgradeMult(eq.weapon.up || 0);
    atk = w.dmg * up * (1 + w.sc[0] * attrBonus(a.force) + w.sc[1] * attrBonus(a.dexterite) + (w.arcane || 0) * attrBonus(a.arcane));
  }
  return {
    maxHp, maxSt, maxMana, def, poise: 20 + poise, weight, capacity, load,
    rollSpeed: load < 0.4 ? 1.12 : load < 0.75 ? 1.0 : 0.82, staminaRegen: (load < 0.75 ? 34 : 24) * (1 + a.endurance * 0.004),
    attack: atk, crit: 0.05 + Math.max(0, a.dexterite - 10) * 0.006, critMult: (w && w.crit) || 1.5,
    skillPower: 1 + attrBonus(a.arcane) * 1.4 + arcane, flaskHeal: 0.42 + a.arcane * 0.004,
    block: sh ? sh.block : (w ? 0.35 : 0), stability: (sh ? sh.stability : 22) + a.force * 0.5,
    weapon: w, shield: sh,
  };
}

/** damage after armor: diminishing returns */
export const mitigate = (dmg, def) => dmg * (100 / (100 + def * 4));

/** enemy stats scaled by level and difficulty */
export function enemyScale(def, diff) {
  const d = DIFFICULTY[diff] || DIFFICULTY.normal;
  return { hp: Math.round(def.hp * d.enemyHp), dmg: def.dmg * d.dmgTaken, xp: Math.round(def.xp * d.xp) };
}
