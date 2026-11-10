// Item definitions. All texts in French. `model` = id of a weapon/shield model (assets/models/gear) or outfit piece.
// Weapons: dmg = base damage, sc = scaling [force, dextérité] (fraction of the attribute bonus), st = stamina per light swing,
// spd = animation speed multiplier, reach (m), poise = stagger power, moveset '1h' | '2h'.

const W = (id, name, cls, moveset, dmg, sc, st, spd, reach, poise, weight, value, model, desc, extra = {}) =>
  ({ id, name, type: 'weapon', slot: 'weapon', cls, moveset, dmg, sc, st, spd, reach, poise, weight, value, model, desc, maxUp: 5, ...extra });
const S = (id, name, block, stability, weight, value, model, desc) =>
  ({ id, name, type: 'shield', slot: 'offhand', block, stability, weight, value, model, desc, maxUp: 3 });
const A = (id, name, slot, set, def, poise, weight, value, desc) =>
  ({ id, name, type: 'armor', slot, set, def, poise, weight, value, model: set + '_' + slot, desc });
const C = (id, name, effect, value, desc, extra = {}) => ({ id, name, type: 'consumable', effect, value, desc, stack: 20, ...extra });
const M = (id, name, value, desc) => ({ id, name, type: 'material', value, desc, stack: 99 });
const K = (id, name, desc) => ({ id, name, type: 'key', value: 0, desc, stack: 1 });

export const ITEMS = {};
const add = (...list) => { for (const it of list) ITEMS[it.id] = it; };

add(
  // ---- one-handed
  W('club', 'Gourdin', 'mace', '1h', 14, [0.55, 0.05], 13, 1.0, 1.25, 16, 2.5, 5, 'club', 'Une branche de chêne durcie au feu. Les gueux de Valombre n\'ont jamais eu mieux.'),
  W('rusty_sword', 'Épée rouillée', 'sword', '1h', 16, [0.30, 0.35], 11, 1.05, 1.4, 10, 2.5, 12, 'sword_rusty', 'Sa lame a connu la Nuit sans Aube. Elle tranche encore, par habitude.'),
  W('iron_sword', 'Épée de fer', 'sword', '1h', 24, [0.35, 0.40], 12, 1.05, 1.45, 12, 3.0, 120, 'sword_iron', 'L\'arme réglementaire des milices d\'Hautefeuille. Fiable, sans génie.'),
  W('steel_sword', 'Épée d\'acier', 'sword', '1h', 34, [0.35, 0.50], 12, 1.08, 1.5, 13, 3.0, 420, 'sword_steel', 'Forgée à Roc-au-Vent, trempée dans l\'eau des glaciers.'),
  W('watcher_blade', 'Lame du Veilleur', 'sword', '1h', 44, [0.40, 0.55], 12, 1.1, 1.55, 14, 3.0, 900, 'sword_watcher', 'Les Veilleurs gravaient sur leur lame le nom de ceux qu\'ils avaient juré de protéger. Celui-ci est illisible.'),
  W('dagger', 'Dague', 'dagger', '1h', 13, [0.10, 0.70], 7, 1.3, 1.0, 5, 0.8, 60, 'dagger', 'Rapide, discrète. On ne la voit qu\'une fois.', { crit: 1.6 }),
  W('hatchet', 'Hachette', 'axe', '1h', 22, [0.55, 0.20], 14, 0.98, 1.3, 18, 2.8, 70, 'hatchet', 'Elle fend le bois et, à l\'occasion, les Écorcheurs.'),
  W('war_axe', 'Hache de guerre', 'axe', '1h', 36, [0.65, 0.20], 15, 0.95, 1.4, 22, 3.6, 380, 'axe_war', 'Le fer large des hommes du Nord. Chaque coup compte double.'),
  W('mace', 'Masse d\'armes', 'mace', '1h', 30, [0.70, 0.05], 15, 0.94, 1.3, 26, 4.0, 300, 'mace', 'Les os et les armures ne font pas la différence.'),
  W('morningstar', 'Étoile du matin', 'mace', '1h', 40, [0.75, 0.10], 16, 0.92, 1.35, 30, 4.5, 700, 'morningstar', 'Bénie autrefois à la chapelle d\'Aubeclair. La bénédiction n\'a pas tenu.'),
  // ---- two-handed
  W('woodcutter_axe', 'Cognée de bûcheron', 'greataxe', '2h', 34, [0.80, 0.05], 20, 0.95, 1.8, 34, 6.0, 40, 'axe_woodcutter', 'Faite pour les chênes de Sombreronce. Les araignées sont moins dures.'),
  W('claymore', 'Claymore', 'greatsword', '2h', 46, [0.60, 0.35], 20, 1.0, 2.0, 32, 6.5, 520, 'claymore', 'Une lame à deux mains, longue comme un homme.'),
  W('great_axe', 'Grande hache', 'greataxe', '2h', 56, [0.90, 0.05], 23, 0.93, 1.9, 40, 8.0, 780, 'axe_great', 'On dit qu\'elle a décapité un troll d\'un seul revers.'),
  W('war_hammer', 'Marteau de guerre', 'hammer', '2h', 60, [1.00, 0.00], 25, 0.88, 1.8, 50, 9.5, 850, 'hammer_war', 'Lent comme un glas. Aussi définitif.'),
  // ---- boss weapons
  W('fang_blade', 'Croc-Blême', 'sword', '1h', 40, [0.25, 0.75], 10, 1.18, 1.45, 12, 2.2, 0, 'sword_fang', 'Taillée dans la canine du Grand Alpha. Elle a faim.', { bleed: 12, unique: true }),
  W('drowned_greatsword', 'Lame Noyée de Malgrin', 'greatsword', '2h', 66, [0.70, 0.40], 22, 0.98, 2.2, 38, 8.0, 0, 'greatsword_drowned', 'L\'eau noire du marais suinte encore de son fil. Sire Malgrin ne l\'a jamais lâchée.', { frost: 10, unique: true }),
  W('colossus_hammer', 'Poing du Colosse', 'hammer', '2h', 78, [1.10, 0.00], 28, 0.85, 1.9, 60, 12.0, 0, 'hammer_colossus', 'Un bloc de glace vive sur un manche de fer. Il ne fond pas.', { frost: 18, unique: true }),
  W('dawn_sword', 'Aubéclat', 'sword', '1h', 58, [0.45, 0.60], 12, 1.12, 1.6, 16, 3.0, 0, 'sword_dawn', 'L\'épée des rois d\'Aubeclair. Un éclat de l\'Astre bat dans son pommeau.', { arcane: 0.5, unique: true }),
  // ---- shields
  S('wood_shield', 'Targe de bois', 0.60, 40, 2.0, 30, 'shield_wood', 'Des planches, du cuir, une prière.'),
  S('iron_shield', 'Écu de fer', 0.80, 58, 4.0, 260, 'shield_iron', 'L\'écu des milices. Les armoiries ont été grattées.'),
  S('watcher_shield', 'Pavois du Veilleur', 0.92, 74, 5.5, 800, 'shield_watcher', 'Derrière lui, une flamme ne s\'éteint pas.'),
  S('kite_shield', 'Écu royal', 0.86, 66, 4.5, 560, 'shield_kite', 'Frappé du soleil d\'Aubeclair, à demi effacé.'),
);

// ---- armor sets: [id, label, def(head, chest, legs), poise, weight, value]
const SETS = [
  ['peasant', 'de gueux', [1, 3, 2], 0, 0.6, 8, 'Chanvre rêche et rapiéçages.'],
  ['leather', 'de cuir bouilli', [3, 8, 5], 2, 1.6, 90, 'Cuir durci à la cire, souple et silencieux.'],
  ['bandit', 'd\'Écorcheur', [3, 7, 5], 2, 1.5, 70, 'Peaux mal tannées. L\'odeur précède le porteur.'],
  ['chain', 'de mailles', [5, 13, 8], 5, 3.2, 320, 'Vingt mille anneaux rivetés un à un.'],
  ['robe', 'du Disciple', [2, 5, 4], 0, 0.9, 150, 'La bure de ceux qui écoutent l\'Astre. Elle renforce les pouvoirs d\'Éclat.'],
  ['plate', 'de plates du Veilleur', [8, 20, 12], 9, 5.0, 900, 'L\'acier de l\'Ordre de la Braise. Lourd comme un serment.'],
  ['royal', 'des Rois sans Aube', [9, 22, 13], 10, 5.2, 0, 'L\'armure d\'apparat d\'Aldric. L\'or s\'est terni la nuit où l\'Astre s\'est brisé.'],
];
const PIECE = { head: ['Coiffe', 'Capuche', 'Cagoule', 'Camail', 'Capuchon', 'Heaume', 'Couronne-heaume'], chest: ['Tunique', 'Brigandine', 'Pourpoint', 'Haubert', 'Bure', 'Plastron', 'Cuirasse'], legs: ['Braies', 'Jambières', 'Chausses', 'Chausses', 'Braies', 'Grèves', 'Grèves'] };
SETS.forEach(([set, label, def, poise, weight, value, desc], i) => {
  ['head', 'chest', 'legs'].forEach((slot, k) => {
    const it = A(`${set}_${slot}`, `${PIECE[slot][i]} ${label}`, slot, set, def[k], Math.round(poise * [0.2, 0.5, 0.3][k]), +(weight * [0.6, 1.6, 1.0][k]).toFixed(1), Math.round(value * [0.6, 1.4, 1.0][k]), desc);
    if (set === 'robe') it.arcane = [0.04, 0.10, 0.06][k];
    add(it);
  });
});

add(
  // ---- consumables
  C('flask', 'Fiole d\'Ambre', { heal: 0.45 }, 0, 'Une sève dorée recueillie aux Autels de Braise. Elle se remplit quand on s\'y repose.', { special: true }),
  C('bread', 'Pain noir', { regen: 2.2, time: 20 }, 6, 'Rassis, mais nourrissant. Rend lentement de la vie.'),
  C('dried_meat', 'Viande séchée', { regen: 3.5, time: 25 }, 14, 'Salée à en pleurer. Rend lentement de la vie.'),
  C('herb_poultice', 'Cataplasme d\'herbes', { cure: 'poison', heal: 0.08 }, 20, 'Plantain et achillée. Chasse le poison.'),
  C('frost_salve', 'Baume de braise', { cure: 'frost', heal: 0.05 }, 24, 'Réchauffe les membres gelés.'),
  C('whetstone', 'Pierre à aiguiser', { buff: 'sharp', mult: 1.2, time: 60 }, 35, 'Un fil neuf pour une minute : dégâts d\'arme augmentés.'),
  C('vigor_elixir', 'Élixir de vigueur', { buff: 'vigor', mult: 1.6, time: 60 }, 60, 'Le souffle revient plus vite pendant une minute.'),
  C('ember_bomb', 'Braise vive', { throw: 'fire', dmg: 60, radius: 3.5 }, 45, 'Un charbon de l\'Autel dans une fiole d\'huile. À lancer, et vite.'),
  C('return_charm', 'Charme de retour', { recall: true }, 80, 'Une plume nouée de rouge. Ramène au dernier Autel de Braise.'),
  // ---- materials
  M('wolf_pelt', 'Peau de loup', 18, 'Épaisse et grise. Les tanneurs de Hautefeuille en donnent un bon prix.'),
  M('spider_silk', 'Soie d\'araignée', 26, 'Plus solide que le chanvre, plus légère que la laine.'),
  M('bone_dust', 'Poussière d\'os', 15, 'Ce qui reste des morts qui ne veulent pas le rester.'),
  M('troll_hide', 'Cuir de troll', 70, 'Dur comme l\'écorce. Sent bien pire.'),
  M('cinder_core', 'Cœur de cendre', 90, 'Une braise qui ne refroidit jamais, arrachée à un golem.'),
  M('steel_shard', 'Éclat d\'acier', 40, 'Le forgeron s\'en sert pour améliorer les armes (+1 à +3).'),
  M('astral_fragment', 'Fragment d\'Astre', 220, 'Une parcelle de l\'Astre-Cœur. Améliore les armes au-delà de +3.'),
  M('amber_sap', 'Sève d\'Ambre', 0, 'Offerte à un Autel, elle ajoute une gorgée à votre fiole.'),
  M('ember_seed', 'Graine de Braise', 0, 'Offerte à un Autel, elle rend la fiole plus puissante.'),
  // ---- keys / quest items
  K('shard_spider', 'Éclat de l\'Ombre', 'L\'éclat que la Reine Tisseuse couvait au cœur de Sombreronce.'),
  K('shard_knight', 'Éclat des Eaux', 'L\'éclat serti dans la cuirasse du Chevalier Noyé.'),
  K('shard_colossus', 'Éclat du Givre', 'L\'éclat qui battait dans la poitrine du Colosse.'),
  K('shard_priestess', 'Éclat de Cendre', 'L\'éclat qu\'Ysolde l\'Incandescente adorait comme un dieu.'),
  K('wolf_fang', 'Croc du Grand Alpha', 'La preuve que Croc-Blême ne hantera plus les lisières.'),
  K('garrick_ring', 'Chevalière de Garrick', 'La bague du chef des Écorcheurs. Volée, comme le reste.'),
  K('chapel_key', 'Clef de la chapelle', 'Ouvre la crypte de la chapelle de Hautefeuille.'),
  K('old_letter', 'Lettre scellée', 'Une lettre à l\'encre passée, adressée au dernier Veilleur.'),
);

export const UPGRADE_COST = [
  { steel_shard: 1, gold: 60 }, { steel_shard: 2, gold: 140 }, { steel_shard: 3, gold: 260 },
  { astral_fragment: 1, gold: 500 }, { astral_fragment: 2, gold: 900 },
];
export const upgradeMult = (level) => 1 + 0.11 * level;

export function itemName(inst) {
  const d = ITEMS[inst.id];
  return d ? d.name + (inst.up ? ` +${inst.up}` : '') : inst.id;
}
