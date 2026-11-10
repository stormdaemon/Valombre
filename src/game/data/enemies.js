// Enemy and boss definitions.
// rig: 'humanoid' | 'wolf' | 'spider'. look: how the model is built (see game/character.js / creatures.js).
// attacks: { id, clip, dmg (multiplier of base damage), range [min,max], arc (deg), cd, lunge (m), poise, speed, type?, ... }
// times (windup / hit windows) come from the animation metadata when available, else from `hit: [t0, t1]` (fraction of clip).

const atk = (id, clip, dmg, range, o = {}) => ({ id, clip, dmg, range, arc: 110, cd: 2.2, lunge: 0.6, poise: 20, speed: 1, hit: [0.38, 0.55], ...o });

export const ENEMIES = {
  // ------------------------------------------------------------------ meadow
  wolf: {
    name: 'Loup', rig: 'wolf', look: { model: 'wolf', scale: 1.0, tint: '#8d8478' }, level: 2,
    hp: 60, dmg: 13, def: 0, poise: 12, speed: 6.2, walk: 1.8, radius: 0.5, height: 1.0, xp: 22, weight: 0.8,
    aggro: 26, leash: 70, pack: [2, 3], behavior: 'pack', hitSfx: 'hit_flesh', voice: 'wolf',
    attacks: [atk('bite', 'bite', 1.0, [0, 1.9], { cd: 1.6, lunge: 0.9 }), atk('lunge', 'lunge', 1.5, [3.0, 6.5], { cd: 4.5, lunge: 4.6, hit: [0.4, 0.62] })],
    loot: [['wolf_pelt', 0.5], ['dried_meat', 0.2]], gold: [0, 4],
  },
  bandit: {
    name: 'Écorcheur', rig: 'humanoid', look: { human: true, outfit: 'bandit', weapon: 'rusty_sword', skin: '#b08a6a', hair: 'hair_short' }, level: 3,
    hp: 90, dmg: 16, def: 3, poise: 22, speed: 4.4, walk: 1.5, radius: 0.42, height: 1.8, xp: 34, weight: 1,
    aggro: 22, leash: 60, pack: [1, 3], behavior: 'duelist', blocks: 0.0, hitSfx: 'hit_flesh', voice: 'human', moveset: '1h',
    attacks: [atk('slash1', 'atk1h_1', 1.0, [0, 2.2]), atk('slash2', 'atk1h_2', 1.0, [0, 2.2], { chain: 'slash1' }), atk('chop', 'atk1h_3', 1.4, [0, 2.4], { cd: 3.5, lunge: 1.0 })],
    loot: [['bread', 0.3], ['rusty_sword', 0.06], ['steel_shard', 0.08]], gold: [4, 16],
  },
  bandit_shield: {
    name: 'Écorcheur au bouclier', rig: 'humanoid', look: { human: true, outfit: 'bandit', weapon: 'hatchet', shield: 'wood_shield', skin: '#a8805e', hair: 'hair_crop', beard: 'beard_short' }, level: 5,
    hp: 120, dmg: 19, def: 5, poise: 30, speed: 4.2, walk: 1.5, radius: 0.42, height: 1.8, xp: 48, weight: 1,
    aggro: 22, leash: 60, behavior: 'duelist', blocks: 0.55, hitSfx: 'hit_flesh', voice: 'human', moveset: '1h',
    attacks: [atk('slash1', 'atk1h_1', 1.0, [0, 2.1]), atk('bash', 'shield_bash', 0.7, [0, 1.8], { cd: 4, poise: 45 }), atk('chop', 'atk1h_3', 1.4, [0, 2.3], { cd: 3.5, lunge: 1.0 })],
    loot: [['wood_shield', 0.08], ['bread', 0.3], ['steel_shard', 0.1]], gold: [6, 20],
  },
  bandit_brute: {
    name: 'Écorcheur colosse', rig: 'humanoid', look: { human: true, outfit: 'bandit', weapon: 'woodcutter_axe', skin: '#a07656', hair: 'hair_bald', beard: 'beard_full', scale: 1.12, morphs: { muscular: 0.9, heavy: 0.5 } }, level: 6,
    hp: 190, dmg: 26, def: 5, poise: 55, speed: 3.6, walk: 1.3, radius: 0.5, height: 2.0, xp: 80, weight: 1.4,
    aggro: 22, leash: 60, behavior: 'brute', hitSfx: 'hit_flesh', voice: 'human', moveset: '2h',
    attacks: [atk('sweep', 'atk2h_1', 1.0, [0, 2.8], { cd: 2.8, arc: 150 }), atk('smash', 'atk2h_3', 1.5, [0, 3.0], { cd: 4.2, lunge: 1.2, poise: 50 })],
    loot: [['woodcutter_axe', 0.1], ['dried_meat', 0.4], ['steel_shard', 0.2]], gold: [10, 30],
  },
  // ------------------------------------------------------------------ forest
  dire_wolf: {
    name: 'Loup sinistre', rig: 'wolf', look: { model: 'wolf', scale: 1.28, tint: '#3d3a3c', eyes: '#ff5a2a' }, level: 8,
    hp: 150, dmg: 24, def: 3, poise: 26, speed: 6.8, walk: 2.0, radius: 0.62, height: 1.25, xp: 75, weight: 1.2,
    aggro: 30, leash: 80, pack: [2, 3], behavior: 'pack', hitSfx: 'hit_flesh', voice: 'wolf',
    attacks: [atk('bite', 'bite', 1.0, [0, 2.1], { cd: 1.5, lunge: 1.0 }), atk('lunge', 'lunge', 1.6, [3.0, 7.5], { cd: 4.0, lunge: 5.2, hit: [0.4, 0.62] })],
    loot: [['wolf_pelt', 0.8], ['dried_meat', 0.3]], gold: [0, 8],
  },
  spider: {
    name: 'Araignée de Sombreronce', rig: 'spider', look: { model: 'spider', scale: 1.0, tint: '#2c2420' }, level: 7,
    hp: 95, dmg: 18, def: 4, poise: 18, speed: 5.2, walk: 2.0, radius: 0.7, height: 0.9, xp: 55, weight: 0.9,
    aggro: 20, leash: 55, pack: [2, 4], behavior: 'skirmisher', hitSfx: 'hit_chitin', voice: 'spider',
    attacks: [atk('bite', 'bite', 1.0, [0, 2.0], { cd: 1.7, status: ['poison', 8] }), atk('leap', 'leap', 1.4, [3.5, 7.0], { cd: 5, lunge: 5.0, hit: [0.45, 0.65], status: ['poison', 8] })],
    loot: [['spider_silk', 0.6], ['herb_poultice', 0.12]], gold: [0, 3],
  },
  spider_spitter: {
    name: 'Cracheuse', rig: 'spider', look: { model: 'spider', scale: 0.85, tint: '#4a5a22', eyes: '#b8ff3a' }, level: 9,
    hp: 80, dmg: 20, def: 2, poise: 14, speed: 4.6, walk: 2.0, radius: 0.6, height: 0.8, xp: 65, weight: 0.8,
    aggro: 26, leash: 55, behavior: 'ranged', keep: [7, 13], hitSfx: 'hit_chitin', voice: 'spider',
    attacks: [atk('spit', 'spit', 1.0, [4, 16], { cd: 2.8, type: 'projectile', proj: 'venom', hit: [0.5, 0.5], status: ['poison', 12] }), atk('bite', 'bite', 0.8, [0, 1.9], { cd: 2.0 })],
    loot: [['spider_silk', 0.7], ['herb_poultice', 0.2]], gold: [0, 3],
  },
  // ------------------------------------------------------------------ swamp
  drowned: {
    name: 'Mort-noyé', rig: 'humanoid', look: { human: true, outfit: 'peasant', skin: '#6f8573', undead: true, hair: 'hair_long', morphs: { thin: 0.8, age: 0.8 } }, level: 12, monster: true,
    hp: 170, dmg: 27, def: 4, poise: 40, speed: 3.9, walk: 1.2, radius: 0.42, height: 1.8, xp: 105, weight: 1,
    aggro: 16, leash: 45, pack: [2, 4], behavior: 'shambler', hitSfx: 'hit_flesh', voice: 'undead',
    attacks: [atk('swipeR', 'm_swipe_R', 1.0, [0, 2.0], { cd: 1.9 }), atk('swipeL', 'm_swipe_L', 1.0, [0, 2.0], { cd: 1.9 }), atk('smash', 'm_smash', 1.6, [0, 2.4], { cd: 5, poise: 45, hit: [0.5, 0.62] })],
    loot: [['bone_dust', 0.5], ['herb_poultice', 0.1]], gold: [0, 12],
  },
  skeleton: {
    name: 'Squelette du Vieux-Gué', rig: 'humanoid', look: { model: 'skeleton', weapon: 'rusty_sword', shield: 'wood_shield' }, level: 13,
    hp: 130, dmg: 30, def: 8, poise: 24, speed: 4.6, walk: 1.5, radius: 0.4, height: 1.8, xp: 115, weight: 0.7,
    aggro: 20, leash: 55, behavior: 'duelist', blocks: 0.35, hitSfx: 'hit_bone', voice: 'bones', moveset: '1h',
    attacks: [atk('slash1', 'atk1h_1', 1.0, [0, 2.2]), atk('slash2', 'atk1h_2', 1.0, [0, 2.2], { chain: 'slash1' }), atk('thrust', 'atk1h_thrust', 1.3, [1.5, 3.6], { cd: 3.2, lunge: 1.8 })],
    loot: [['bone_dust', 0.7], ['steel_shard', 0.15], ['iron_sword', 0.04]], gold: [2, 14],
  },
  wraith: {
    name: 'Spectre des brumes', rig: 'humanoid', look: { human: true, outfit: 'robe', ghost: '#7fd6c8' }, level: 15, monster: true, floats: true,
    hp: 120, dmg: 32, def: 0, poise: 999, speed: 4.2, walk: 2.2, radius: 0.45, height: 1.9, xp: 150, weight: 0.3,
    aggro: 22, leash: 55, behavior: 'ranged', keep: [5, 10], hitSfx: 'spell_impact', voice: 'wraith',
    attacks: [atk('bolt', 'cast', 1.0, [3, 16], { cd: 2.6, type: 'projectile', proj: 'frost', hit: [0.5, 0.5], status: ['frost', 14] }), atk('wail', 'cast_big', 1.4, [0, 4.5], { cd: 7, type: 'nova', radius: 4.5, hit: [0.62, 0.7], status: ['frost', 20] })],
    loot: [['frost_salve', 0.25], ['astral_fragment', 0.04]], gold: [0, 20],
  },
  // ------------------------------------------------------------------ mountains
  snow_wolf: {
    name: 'Loup des neiges', rig: 'wolf', look: { model: 'wolf', scale: 1.15, tint: '#d9dde0' }, level: 16,
    hp: 190, dmg: 34, def: 4, poise: 26, speed: 6.9, walk: 2.0, radius: 0.58, height: 1.15, xp: 140, weight: 1.1,
    aggro: 30, leash: 80, pack: [2, 4], behavior: 'pack', hitSfx: 'hit_flesh', voice: 'wolf',
    attacks: [atk('bite', 'bite', 1.0, [0, 2.0], { cd: 1.5, lunge: 1.0 }), atk('lunge', 'lunge', 1.6, [3.0, 7.5], { cd: 4.0, lunge: 5.2, hit: [0.4, 0.62], status: ['frost', 8] })],
    loot: [['wolf_pelt', 0.9]], gold: [0, 10],
  },
  troll: {
    name: 'Troll des pics', rig: 'humanoid', look: { model: 'troll', scale: 1.0 }, level: 19, monster: true,
    hp: 620, dmg: 48, def: 10, poise: 120, speed: 3.8, walk: 1.4, radius: 0.95, height: 3.0, xp: 420, weight: 4,
    aggro: 24, leash: 70, behavior: 'brute', hitSfx: 'hit_flesh', voice: 'troll', stepSfx: 'troll_step',
    attacks: [atk('swipeR', 'm_swipe_R', 1.0, [0, 3.6], { cd: 2.4, arc: 150, poise: 60 }), atk('smash', 'm_smash', 1.6, [0, 4.2], { cd: 5, poise: 90, hit: [0.5, 0.62], type: 'slam', radius: 3.6 }), atk('stomp', 'm_stomp', 1.2, [0, 3.0], { cd: 6, type: 'slam', radius: 3.2, hit: [0.5, 0.6] }), atk('charge', 'm_charge', 1.5, [7, 16], { cd: 9, type: 'charge', dist: 14, speed: 9 })],
    loot: [['troll_hide', 0.8], ['steel_shard', 0.5], ['amber_sap', 0.08]], gold: [20, 60],
  },
  // ------------------------------------------------------------------ ash lands
  cultist: {
    name: 'Cultiste de l\'Aube Morte', rig: 'humanoid', look: { human: true, outfit: 'robe', tintOutfit: '#5a1f1a', weapon: 'dagger', skin: '#9c8a80', hair: 'hair_bald' }, level: 22,
    hp: 210, dmg: 40, def: 4, poise: 26, speed: 4.4, walk: 1.5, radius: 0.42, height: 1.8, xp: 230, weight: 1,
    aggro: 26, leash: 60, pack: [1, 3], behavior: 'ranged', keep: [7, 13], hitSfx: 'hit_flesh', voice: 'human', moveset: '1h',
    attacks: [atk('firebolt', 'cast', 1.0, [4, 20], { cd: 2.4, type: 'projectile', proj: 'fire', hit: [0.5, 0.5], status: ['burn', 10] }), atk('stab', 'atk1h_thrust', 0.8, [0, 2.4], { cd: 2.2 })],
    loot: [['ember_bomb', 0.2], ['frost_salve', 0.1], ['astral_fragment', 0.05]], gold: [8, 30],
  },
  cultist_blade: {
    name: 'Zélote incandescent', rig: 'humanoid', look: { human: true, outfit: 'robe', tintOutfit: '#3a1512', weapon: 'war_axe', skin: '#9c8a80', hair: 'hair_bald', morphs: { muscular: 0.6 } }, level: 23,
    hp: 290, dmg: 44, def: 6, poise: 40, speed: 4.8, walk: 1.5, radius: 0.42, height: 1.8, xp: 260, weight: 1,
    aggro: 24, leash: 60, behavior: 'duelist', blocks: 0, hitSfx: 'hit_flesh', voice: 'human', moveset: '1h',
    attacks: [atk('slash1', 'atk1h_1', 1.0, [0, 2.3], { status: ['burn', 6] }), atk('slash2', 'atk1h_2', 1.0, [0, 2.3], { chain: 'slash1' }), atk('heavy', 'atk1h_heavy', 1.7, [0, 2.8], { cd: 4.5, lunge: 1.4, poise: 45 })],
    loot: [['ember_bomb', 0.25], ['steel_shard', 0.3], ['war_axe', 0.05]], gold: [10, 34],
  },
  ash_golem: {
    name: 'Golem de cendre', rig: 'humanoid', look: { model: 'golem', scale: 1.0 }, level: 25, monster: true,
    hp: 900, dmg: 58, def: 22, poise: 200, speed: 3.2, walk: 1.2, radius: 1.0, height: 3.1, xp: 620, weight: 6,
    aggro: 22, leash: 60, behavior: 'brute', hitSfx: 'hit_stone', voice: 'golem', stepSfx: 'troll_step',
    attacks: [atk('swipeL', 'm_swipe_L', 1.0, [0, 3.6], { cd: 2.6, arc: 150, poise: 70, status: ['burn', 8] }), atk('smash', 'm_smash', 1.7, [0, 4.4], { cd: 5, poise: 100, hit: [0.5, 0.62], type: 'slam', radius: 4.2, status: ['burn', 12] }), atk('stomp', 'm_stomp', 1.2, [0, 3.2], { cd: 6, type: 'slam', radius: 3.6, hit: [0.5, 0.6] })],
    loot: [['cinder_core', 0.8], ['astral_fragment', 0.15], ['ember_seed', 0.06]], gold: [30, 80],
  },
  // ------------------------------------------------------------------ citadel
  hollow_knight: {
    name: 'Chevalier creux', rig: 'humanoid', look: { human: true, outfit: 'plate', tintOutfit: '#4a4d55', weapon: 'steel_sword', shield: 'kite_shield', hollow: '#7fe0ff' }, level: 28,
    hp: 420, dmg: 54, def: 18, poise: 70, speed: 4.6, walk: 1.5, radius: 0.45, height: 1.9, xp: 480, weight: 1.4,
    aggro: 24, leash: 60, behavior: 'duelist', blocks: 0.6, hitSfx: 'hit_armor', voice: 'undead', moveset: '1h',
    attacks: [atk('slash1', 'atk1h_1', 1.0, [0, 2.4]), atk('slash2', 'atk1h_2', 1.0, [0, 2.4], { chain: 'slash1' }), atk('chop', 'atk1h_3', 1.4, [0, 2.6], { chain: 'slash2', lunge: 1.0 }), atk('thrust', 'atk1h_thrust', 1.3, [1.8, 4.0], { cd: 3.4, lunge: 2.2 }), atk('bash', 'shield_bash', 0.7, [0, 1.9], { cd: 5, poise: 60 })],
    loot: [['steel_shard', 0.6], ['astral_fragment', 0.12], ['kite_shield', 0.04]], gold: [20, 60],
  },
  hollow_greatsword: {
    name: 'Garde royal creux', rig: 'humanoid', look: { human: true, outfit: 'plate', tintOutfit: '#5a4a30', weapon: 'claymore', hollow: '#7fe0ff', scale: 1.08 }, level: 30,
    hp: 560, dmg: 66, def: 20, poise: 100, speed: 4.2, walk: 1.4, radius: 0.48, height: 2.0, xp: 620, weight: 1.6,
    aggro: 24, leash: 60, behavior: 'brute', hitSfx: 'hit_armor', voice: 'undead', moveset: '2h',
    attacks: [atk('sweep', 'atk2h_1', 1.0, [0, 3.0], { cd: 2.6, arc: 150 }), atk('sweep2', 'atk2h_2', 1.0, [0, 3.0], { chain: 'sweep', arc: 150 }), atk('smash', 'atk2h_3', 1.5, [0, 3.2], { cd: 4, lunge: 1.2, poise: 60 }), atk('spin', 'atk2h_heavy', 1.8, [0, 3.2], { cd: 8, arc: 360, poise: 70, hit: [0.4, 0.75] })],
    loot: [['astral_fragment', 0.25], ['claymore', 0.05], ['amber_sap', 0.05]], gold: [30, 90],
  },
};

// ---------------------------------------------------------------------- bosses
export const BOSSES = {
  wolf: {
    name: 'Croc-Blême', title: 'Le Grand Alpha', rig: 'wolf', look: { model: 'wolf', scale: 2.3, tint: '#cfd3d6', eyes: '#ff3a1a', scars: true }, level: 6, poi: 'boss_wolf', music: 'wolf',
    hp: 900, dmg: 30, def: 4, poise: 140, speed: 7.4, walk: 2.4, radius: 1.25, height: 2.3, xp: 900, weight: 5,
    behavior: 'boss_wolf', hitSfx: 'hit_flesh', voice: 'wolf',
    attacks: [atk('bite', 'bite', 1.0, [0, 3.6], { cd: 1.6, lunge: 1.6, arc: 120 }), atk('lunge', 'lunge', 1.7, [5, 13], { cd: 4.2, lunge: 9, hit: [0.4, 0.62] }), atk('swipe', 'swipe', 1.2, [0, 4.0], { cd: 3, arc: 200, poise: 50 }), atk('howl', 'howl', 0, [0, 40], { cd: 26, type: 'summon', summon: 'wolf', count: 2, phase: 2 })],
    phases: [{ at: 0.5, enrage: 1.15, say: 'Le Grand Alpha hurle à la lune.' }],
    reward: { items: [['wolf_fang', 1], ['fang_blade', 1], ['amber_sap', 1]], gold: 300, skill: 'wolf_howl' },
  },
  spider: {
    name: 'Arakha', title: 'La Reine Tisseuse', rig: 'spider', look: { model: 'spider', scale: 3.4, tint: '#1c1418', eyes: '#c04aff', queen: true }, level: 12, poi: 'boss_spider', music: 'spider',
    hp: 1700, dmg: 40, def: 8, poise: 220, speed: 5.4, walk: 2.4, radius: 2.2, height: 2.6, xp: 2200, weight: 9,
    behavior: 'boss_spider', hitSfx: 'hit_chitin', voice: 'spider',
    attacks: [atk('bite', 'bite', 1.0, [0, 4.6], { cd: 1.9, arc: 120, status: ['poison', 14] }), atk('slam', 'slam', 1.5, [0, 5.5], { cd: 5, type: 'slam', radius: 5.5, poise: 80, hit: [0.5, 0.62] }), atk('leap', 'leap', 1.6, [7, 18], { cd: 7, lunge: 14, type: 'slam', radius: 4.5, hit: [0.5, 0.68] }), atk('spit', 'spit', 0.9, [6, 26], { cd: 3.2, type: 'projectile', proj: 'venom', burst: 3, hit: [0.5, 0.5], status: ['poison', 14] }), atk('brood', 'rear_up', 0, [0, 40], { cd: 30, type: 'summon', summon: 'spider', count: 3, phase: 2 })],
    phases: [{ at: 0.55, enrage: 1.15, say: 'Les cocons se déchirent autour de vous.' }],
    reward: { items: [['shard_spider', 1], ['astral_fragment', 2], ['ember_seed', 1]], gold: 600, skill: 'shadow_web' },
  },
  knight: {
    name: 'Sire Malgrin', title: 'Le Chevalier Noyé', rig: 'humanoid', look: { human: true, outfit: 'plate', tintOutfit: '#2e4a48', weapon: 'drowned_greatsword', hollow: '#58ffd0', scale: 1.55, drowned: true }, level: 18, poi: 'boss_knight', music: 'knight',
    hp: 2600, dmg: 58, def: 16, poise: 260, speed: 4.4, walk: 1.5, radius: 0.85, height: 2.9, xp: 4200, weight: 8, moveset: '2h',
    behavior: 'boss_knight', hitSfx: 'hit_armor', voice: 'undead',
    attacks: [atk('sweep', 'atk2h_1', 1.0, [0, 4.6], { cd: 2.2, arc: 160 }), atk('sweep2', 'atk2h_2', 1.0, [0, 4.6], { chain: 'sweep', arc: 160 }), atk('smash', 'atk2h_3', 1.5, [0, 5.0], { chain: 'sweep2', type: 'slam', radius: 3.6, poise: 80 }), atk('spin', 'atk2h_heavy', 1.6, [0, 5.0], { cd: 9, arc: 360, hit: [0.4, 0.75], poise: 70 }), atk('wave', 'cast_big', 1.3, [5, 22], { cd: 8, type: 'wave', hit: [0.62, 0.62], status: ['frost', 16], phase: 2 }), atk('charge', 'atk1h_thrust', 1.5, [6, 16], { cd: 7, lunge: 10, hit: [0.3, 0.7] })],
    phases: [{ at: 0.5, enrage: 1.12, say: 'L\'eau noire monte autour de Sire Malgrin.' }],
    reward: { items: [['shard_knight', 1], ['drowned_greatsword', 1], ['amber_sap', 1]], gold: 1100, skill: 'drowned_tide' },
  },
  colossus: {
    name: 'Le Colosse de Givre', title: 'Gardien du Col', rig: 'humanoid', look: { model: 'golem', variant: 'ice', scale: 1.75 }, level: 24, poi: 'boss_colossus', music: 'colossus', monster: true,
    hp: 3800, dmg: 70, def: 26, poise: 500, speed: 3.6, walk: 1.5, radius: 1.8, height: 5.4, xp: 7000, weight: 20,
    behavior: 'boss_colossus', hitSfx: 'hit_stone', voice: 'golem', stepSfx: 'golem_slam',
    attacks: [atk('swipeR', 'm_swipe_R', 1.0, [0, 6.2], { cd: 2.6, arc: 160, poise: 90, status: ['frost', 10] }), atk('swipeL', 'm_swipe_L', 1.0, [0, 6.2], { cd: 2.6, arc: 160, poise: 90, status: ['frost', 10] }), atk('smash', 'm_smash', 1.6, [0, 7.5], { cd: 4.5, type: 'slam', radius: 6.5, poise: 140, hit: [0.5, 0.62], status: ['frost', 18] }), atk('stomp', 'm_stomp', 1.2, [0, 6], { cd: 6, type: 'slam', radius: 7.5, hit: [0.5, 0.6], status: ['frost', 12] }), atk('shards', 'm_roar', 1.0, [0, 40], { cd: 14, type: 'rain', proj: 'ice', count: 9, hit: [0.5, 0.5], phase: 2 }), atk('charge', 'm_charge', 1.5, [9, 26], { cd: 10, type: 'charge', dist: 20, speed: 11 })],
    phases: [{ at: 0.5, enrage: 1.1, say: 'La glace du lac se fend sous vos pieds.' }],
    reward: { items: [['shard_colossus', 1], ['colossus_hammer', 1], ['ember_seed', 1]], gold: 1800, skill: 'frost_nova' },
  },
  priestess: {
    name: 'Ysolde', title: 'L\'Incandescente', rig: 'humanoid', look: { human: true, outfit: 'robe', tintOutfit: '#7a1c10', skin: '#d9b8a0', hair: 'hair_long', hairColor: '#e8e2d8', feminine: 1, glow: '#ff7a2a', scale: 1.12 }, level: 28, poi: 'boss_priestess', music: 'priestess', floats: true,
    hp: 3200, dmg: 74, def: 10, poise: 160, speed: 5.0, walk: 2.4, radius: 0.55, height: 2.0, xp: 9500, weight: 2,
    behavior: 'boss_priestess', hitSfx: 'hit_flesh', voice: 'human',
    attacks: [atk('firebolt', 'cast', 1.0, [4, 30], { cd: 1.7, type: 'projectile', proj: 'fire', burst: 3, hit: [0.5, 0.5], status: ['burn', 12] }), atk('pillars', 'cast_big', 1.5, [0, 30], { cd: 6, type: 'pillars', count: 4, radius: 2.6, hit: [0.62, 0.62], status: ['burn', 16] }), atk('nova', 'roar', 1.4, [0, 6], { cd: 8, type: 'nova', radius: 6.5, hit: [0.5, 0.56], status: ['burn', 16], poise: 100 }), atk('blink', 'cast', 0, [0, 5], { cd: 5, type: 'blink' }), atk('meteor', 'cast_big', 2.0, [0, 40], { cd: 16, type: 'rain', proj: 'meteor', count: 8, hit: [0.6, 0.6], phase: 2, status: ['burn', 20] })],
    phases: [{ at: 0.5, enrage: 1.15, say: 'La caldeira s\'embrase. Ysolde rit.' }],
    reward: { items: [['shard_priestess', 1], ['astral_fragment', 3], ['amber_sap', 1]], gold: 2600, skill: 'ysolde_flame' },
  },
  king: {
    name: 'Aldric IV', title: 'Le Roi sans Aube', rig: 'humanoid', look: { human: true, outfit: 'royal', weapon: 'dawn_sword', hollow: '#fff2b0', scale: 1.3, crown: true, morphs: { age: 1, thin: 0.5 }, beard: 'beard_long', hair: 'hair_long', hairColor: '#cfcfcf', skin: '#a9a096' }, level: 34, poi: 'boss_king', music: 'king',
    hp: 5200, dmg: 86, def: 22, poise: 300, speed: 5.2, walk: 1.6, radius: 0.7, height: 2.4, xp: 20000, weight: 5, moveset: '1h',
    behavior: 'boss_king', hitSfx: 'hit_armor', voice: 'human',
    attacks: [atk('slash1', 'atk1h_1', 1.0, [0, 3.6]), atk('slash2', 'atk1h_2', 1.0, [0, 3.6], { chain: 'slash1' }), atk('chop', 'atk1h_3', 1.4, [0, 3.8], { chain: 'slash2', lunge: 1.6, type: 'slam', radius: 3 }), atk('thrust', 'atk1h_thrust', 1.4, [2.5, 9], { cd: 3.6, lunge: 6 }), atk('heavy', 'atk1h_heavy', 1.8, [0, 4.2], { cd: 6, lunge: 2, poise: 110 }), atk('beam', 'cast', 1.2, [6, 34], { cd: 5, type: 'projectile', proj: 'dawn', burst: 2, hit: [0.5, 0.5] }), atk('nova', 'roar', 1.6, [0, 8], { cd: 10, type: 'nova', radius: 8, hit: [0.5, 0.56], poise: 140, phase: 2 }), atk('rain', 'cast_big', 1.8, [0, 40], { cd: 14, type: 'rain', proj: 'dawn', count: 12, hit: [0.6, 0.6], phase: 2 }), atk('blink', 'cast', 0, [8, 40], { cd: 7, type: 'blink', phase: 2 })],
    phases: [{ at: 0.55, enrage: 1.2, say: 'L\'Astre brisé répond à son roi.' }],
    reward: { items: [['dawn_sword', 1]], gold: 5000, ending: true },
  },
};

/** which enemies spawn in which biome: [id, weight, minDist from start village in meters] */
export const SPAWN_TABLE = {
  meadow: [['wolf', 5], ['bandit', 4], ['bandit_shield', 2], ['bandit_brute', 1]],
  beach: [['bandit', 3], ['wolf', 2]],
  forest: [['spider', 5], ['dire_wolf', 4], ['spider_spitter', 3], ['bandit_brute', 1]],
  swamp: [['drowned', 6], ['skeleton', 4], ['wraith', 2], ['spider_spitter', 1]],
  mountain: [['snow_wolf', 5], ['troll', 2], ['skeleton', 2], ['wraith', 1]],
  ash: [['cultist', 5], ['cultist_blade', 4], ['ash_golem', 2]],
  citadel: [['hollow_knight', 5], ['hollow_greatsword', 3], ['wraith', 1]],
};
