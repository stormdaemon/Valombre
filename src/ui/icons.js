// VALOMBRE UI — inline SVG icon set (24x24, stroke based, closed shapes get a faint fill through `.s`).
import { ITEMS } from '../game/data/items.js';

const R = (inner, deg = 38, scale = 0.94) => `<g transform="rotate(${deg} 12 12) translate(12 12) scale(${scale}) translate(-12 -12)">${inner}</g>`;

export const ICONS = {
  // ---- weapons
  sword: '<path class="s" d="M20.5 3.5v3L10.2 16.8l-3-3L17.5 3.5z"/><path d="M5.2 11.8l7 7M8.2 15.800l-3.200 3.200"/><circle class="s" cx="4" cy="20" r="1.300"/>',
  dagger: '<path class="s" d="M17.800 6.200v2.700l-6.700 6.700-2.700-2.700 6.700-6.700z"/><path d="M6.500 11.500l6 6M9.200 14.800l-3 3"/><circle class="s" cx="5.200" cy="18.800" r="1.200"/>',
  greatsword: '<path class="s" d="M21.500 2.500v3.400L10.400 17l-3.400-3.400L18.100 2.500z"/><path d="M19.300 4.700L9.800 14.200M4.400 10.400l9.200 9.200M8.400 15.600l-3.700 3.700"/><circle class="s" cx="3.700" cy="20.300" r="1.300"/>',
  axe: R('<path d="M11 3v18.500"/><path class="s" d="M11 6h3c2-.2 4-1.200 5.500-2.500.8 3.500.6 7-.8 10.500-1.300-1.200-3-1.900-4.700-2H11z"/>'),
  greataxe: R('<path d="M12 2v20"/><path class="s" d="M12 6.500h2c2-.200 3.600-1 5-2.300.900 3.400.800 6.600-.500 10-1.200-1.100-2.700-1.600-4.500-1.700h-2z"/><path class="s" d="M12 6.500h-2c-2-.200-3.600-1-5-2.300-.900 3.400-.800 6.600.500 10 1.200-1.100 2.700-1.600 4.500-1.700h2z"/>'),
  mace: R('<path d="M12 11v11"/><circle class="s" cx="12" cy="7" r="3.500"/><path d="M12 1.800v1.700M12 10.500v1.300M6.800 7h1.700M15.500 7h1.700M8.300 3.300l1.200 1.200M14.500 9.500l1.200 1.200M15.700 3.300l-1.200 1.200M9.500 9.500l-1.200 1.200"/>'),
  hammer: R('<path d="M12 9.500V22"/><path class="s" d="M5.500 3.500h13v6h-13z"/><path d="M8.800 3.500v6M15.200 3.500v6"/>'),
  club: R('<path d="M12 22v-8.500"/><path class="s" d="M9.800 13.500c-1.100-3-1.300-6.700.1-9.500 1.300-1.300 2.900-1.300 4.200 0 1.400 2.800 1.200 6.500.1 9.500z"/><path d="M11 6.500h.01M13 9h.01M11.200 11h.01"/>'),
  // ---- armour
  shield: '<path class="s" d="M12 2.800l7.500 2.400v6.300c0 4.800-3 8.300-7.500 10-4.500-1.700-7.500-5.200-7.500-10V5.200z"/><path d="M12 6.500V18M8 10.500h8"/>',
  helm: '<path class="s" d="M5 19.500v-7.200C5 7.500 8 3.800 12 3.800s7 3.700 7 8.500v7.200h-4.600v-5.200H9.600v5.200z"/><path d="M12 3.800V11M8.200 11h7.600"/>',
  chest: '<path class="s" d="M8 3.500c1.200 1.400 2.500 2 4 2s2.800-.6 4-2l4.500 3.200-2 3.800-1.500-.8v10.800H7V9.700l-1.500.8-2-3.800z"/><path d="M12 9.500v7.500"/>',
  legs: '<path class="s" d="M6.500 3.500h11l-.6 17h-3.600L12 9.500l-1.300 11H7.100z"/><path d="M6.700 7.500h10.600"/>',
  // ---- consumables / materials / keys
  flask: '<path class="s" d="M9.500 3h5v1.600h-.9v3.200c2.900 1 4.900 3.600 4.900 6.700 0 3.600-2.900 6.500-6.500 6.500s-6.500-2.900-6.500-6.500c0-3.100 2-5.700 4.900-6.700V4.600h-.9z"/><path d="M6.300 13.300c2-1 3.700.8 5.700 0s3.700-1 5.700 0"/>',
  bread: '<path class="s" d="M3.500 14.500C3.500 10 7.300 7 12 7s8.500 3 8.500 7.500V17h-17z"/><path d="M8 9.500l1.300 3M12 8.500l1.300 3M16 9.500l1.300 3"/>',
  meat: '<path class="s" d="M13.500 4.500c3.500 0 6.500 2.800 6.500 6.300 0 3.700-3.300 6.200-7 6.200-1.500 0-2.800-.3-4-1l-2.300 2.300-1.200-1.200L7.800 14.800c-.6-1.100-.8-2.400-.8-3.800 0-3.600 3-6.500 6.500-6.500z"/><circle cx="13.800" cy="10.500" r="1.800"/><circle class="s" cx="4.600" cy="19.400" r="1.300"/>',
  leaf: '<path class="s" d="M5 19C5 10.500 10.500 5 19 5c0 8.500-5.500 14-14 14z"/><path d="M5 19l9.500-9.500M9.500 14.500V11M9.500 14.500H13"/>',
  salve: '<path class="s" d="M6.500 9h11v9.500c0 1.100-.9 2-2 2h-7c-1.100 0-2-.9-2-2z"/><path d="M5.500 5.500h13V9h-13zM9.500 14h5"/>',
  stone: '<path class="s" d="M3.500 14.500L14.500 6l6 3.500-11 8.500z"/><path d="M3.500 14.500v2.300l6 3.200 11-8.500v-2M9.500 18v2"/>',
  bomb: '<circle class="s" cx="11" cy="14" r="6.500"/><path d="M14.700 8.300l1.800-2.300M16.500 6c1-1.500 2.500-2 4-1.500M19.200 2.300v1.200M21.700 6.800h-1.200"/>',
  feather: '<path class="s" d="M20 4c-6.500 0-12 3.800-13.500 10.500L5 20l5.500-1.500C17 17 20 11 20 4z"/><path d="M5 20L15 9.500M9.300 12.500h3.200M9.800 16h3.700"/>',
  pelt: '<path class="s" d="M8 3.500l4 2 4-2 1 4.500 3.500 2-2.500 3 1.500 5-4.500-1-3 3.500-3-3.500-4.500 1 1.500-5-2.500-3L7 8z"/>',
  bone: '<path d="M8.200 8.200l7.600 7.600" stroke-width="2.6"/><circle class="s" cx="5.700" cy="7.600" r="1.900"/><circle class="s" cx="7.600" cy="5.700" r="1.900"/><circle class="s" cx="16.400" cy="18.300" r="1.900"/><circle class="s" cx="18.300" cy="16.400" r="1.900"/>',
  web: '<path d="M12 3v18M3 12h18M5.600 5.600l12.800 12.800M18.400 5.600L5.600 18.400M12 7.500l3.200 1.300 1.300 3.200-1.300 3.200-3.200 1.300-3.200-1.300L7.500 12l1.300-3.200z"/>',
  shard: '<path class="s" d="M5.500 20L9 4.500l8.500 6.500-3 9.500z"/><path d="M9 4.500L14.500 20.500M7.200 12.500l8-1"/>',
  crystal: '<path class="s" d="M12 2l5 6.500L12 22 7 8.500z"/><path d="M7 8.500h10M12 2l-1.800 6.500L12 22M12 2l1.800 6.500"/>',
  drop: '<path class="s" d="M12 3c3 4 6 7.300 6 11a6 6 0 01-12 0c0-3.700 3-7 6-11z"/><path d="M9 14.500c0 1.700 1.300 3 3 3"/>',
  seed: '<path class="s" d="M12 3.500c4 3 5.500 6.500 5.500 9.500 0 4-2.500 7.500-5.500 7.500S6.500 17 6.500 13c0-3 1.500-6.500 5.500-9.500z"/><path d="M12 20.500V11M12 15l2.500-2.500"/>',
  fang: '<path class="s" d="M8 3.500h8c0 6-1.500 12.500-4 17-2.500-4.500-4-11-4-17z"/><path d="M10.200 3.500c.3 3 .9 6 1.800 9"/>',
  ring: '<circle cx="12" cy="14.500" r="5.800"/><path class="s" d="M9.500 6.300L12 3.300l2.500 3L12 9z"/>',
  key: '<circle class="s" cx="7.500" cy="12" r="3.500"/><path d="M11 12h9.500M17 12v3M20.500 12v2.500"/>',
  letter: '<path class="s" d="M3.500 6h17v12h-17z"/><path d="M3.800 6.500L12 13l8.200-6.500"/>',
  unknown: '<path d="M9 9.300a3 3 0 115 2.200c-1 .8-2 1.400-2 2.800M12 17.700v.3"/>',
  // ---- interface
  coin: '<circle class="s" cx="12" cy="12" r="8.500"/><circle cx="12" cy="12" r="5.300"/><path d="M12 9.500v5M9.800 12h4.400"/>',
  skull: '<path class="s" d="M12 3C7.600 3 4.500 6.100 4.500 10.200c0 2.600 1.200 4.600 3 5.800V19h9v-3c1.800-1.200 3-3.200 3-5.800C19.500 6.100 16.400 3 12 3z"/><circle cx="9" cy="10.500" r="1.600"/><circle cx="15" cy="10.500" r="1.600"/><path d="M12 13.500V15M10 19v-2M14 19v-2"/>',
  flame: '<path class="s" d="M12.300 2.500c.4 3.300 4.200 5.300 4.200 10.300 0 4.300-2 8.200-4.500 8.200s-4.500-3.300-4.500-7c0-2.300 1.300-3.600 1.900-5.600.9 1 1.500 2 1.700 3.200 1.200-2.400.8-6.200 1.200-9.100z"/><path d="M12 21c-1.200-.8-1.800-2.200-1.800-3.600 0-1.400.9-2.300 1.800-3.400.9 1.100 1.800 2 1.800 3.400S13.200 20.200 12 21z"/>',
  pyre: '<path class="s" d="M12.300 1.800c.4 3 3.700 4.900 3.700 9.500 0 3.900-1.800 6.700-4 6.700s-4-2.600-4-6c0-2.100 1.200-3.300 1.700-5.100.8.9 1.300 1.800 1.500 2.900 1-2.200.7-5.400 1.100-8z"/><path d="M5 21.500h14M7.500 19.500h9"/>',
  pin: '<path class="s" d="M12 21.500S5.500 14.700 5.500 9.700C5.500 6 8.400 3 12 3s6.500 3 6.500 6.700c0 5-6.500 11.800-6.500 11.800z"/><circle cx="12" cy="9.700" r="2.300"/>',
  quest: '<path class="s" d="M7.500 3.500H19v13.200c0 1.800-1.300 3.300-3 3.300H5.800c1-.7 1.700-1.700 1.700-3z"/><path d="M5.800 20c-1.300 0-2.300-1-2.300-2.300V16h4M10.500 8H16M10.500 11.500H16M10.500 15H14"/>',
  lock: '<path class="s" d="M6 10.500h12V20H6z"/><path d="M8.500 10.500V7.700a3.500 3.500 0 017 0v2.800M12 14v2.500"/>',
  attributes: '<path class="s" d="M12 2.500l2 7.500 7.500 2-7.500 2-2 7.500-2-7.500-7.500-2 7.500-2z"/>',
  bag: '<path class="s" d="M8 8.500C5 11 4 14.200 4.500 17c.5 2.500 2.500 3.500 7.500 3.500s7-1 7.500-3.500c.5-2.800-.5-6-3.500-8.500z"/><path d="M8.500 8.500l-1-4h9l-1 4M8 8.500h8"/>',
  book: '<path class="s" d="M4 5.200c3-1 6-.7 8 .8 2-1.500 5-1.800 8-.8V19c-3-1-6-.7-8 .8-2-1.500-5-1.800-8-.8z"/><path d="M12 6v13.800"/>',
  map: '<path class="s" d="M3.500 6L9 4l6 2 5.500-2v14L15 20l-6-2-5.500 2z"/><path d="M9 4v14M15 6v14"/>',
  gear: '<circle class="s" cx="12" cy="12" r="6.200"/><circle cx="12" cy="12" r="2.400"/><circle cx="12" cy="12" r="8.300" stroke-width="2.600" stroke-dasharray="3.050 3.470"/>',
  person: '<circle class="s" cx="12" cy="7.800" r="3.800"/><path class="s" d="M4.500 20.500c0-4.500 3-7 7.500-7s7.500 2.500 7.500 7z"/>',
  weight: '<path class="s" d="M7 9.500h10l2.500 11h-15z"/><path d="M9.500 9.500a2.800 2.800 0 115 0"/>',
  check: '<path d="M5 12.500l4.700 4.700L19.500 6.800"/>',
  cross: '<path d="M6 6l12 12M18 6L6 18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  right: '<path d="M9 5l7 7-7 7"/>',
  left: '<path d="M15 5l-7 7 7 7"/>',
  anvil: '<path class="s" d="M5 7h12.500c0 2.300-1.700 3.800-4 4.300v2.500l2.500 4V20H7v-2.200l2.500-4v-2.500C7 10.800 5.500 9.300 5 7z"/><path d="M17.500 7H21c-.5 1.500-1.800 2.300-3.600 2.300M5 7H3"/>',
  sun: '<circle class="s" cx="12" cy="12" r="4"/><path d="M12 2.500V5M12 19v2.500M2.500 12H5M19 12h2.500M5.300 5.300L7 7M17 17l1.700 1.700M18.700 5.300L17 7M7 17l-1.700 1.700"/>',
  moon: '<path class="s" d="M19 14.500A8 8 0 019.500 5a8 8 0 109.500 9.500z"/>',
  exit: '<path d="M13.500 4H6v16h7.500M10 12h10.500M17 8.500l3.500 3.500-3.500 3.500"/>',
  eye: '<path class="s" d="M2.500 12C5 7.500 8.300 5.500 12 5.500s7 2 9.500 6.500c-2.500 4.500-5.800 6.500-9.500 6.500S5 16.500 2.500 12z"/><circle cx="12" cy="12" r="2.800"/>',
  speech: '<path class="s" d="M4 5h16v11h-8l-4.500 4v-4H4z"/>',
  house: '<path class="s" d="M4 11.500L12 4l8 7.500V20H4z"/><path d="M10 20v-5h4v5"/>',
  tent: '<path class="s" d="M12 4L3.500 20h17z"/><path d="M12 12.500L9.700 20M12 12.500l2.300 7.500"/>',
  ruin: '<path class="s" d="M5 20V8.500l2.500-2 2.500 2V13h4V6.500l2.500-2.500L19 6.500V20z"/>',
  tower: '<path class="s" d="M6.500 20.500V10L5 9V4h3v2h2.500V4h3v2H16V4h3v5l-1.500 1v10.500z"/><path d="M10.500 20.500v-4a1.500 1.500 0 013 0v4"/>',
  target: '<circle cx="12" cy="12" r="7.500"/><circle cx="12" cy="12" r="2"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
  heart: '<path class="s" d="M12 20.500C6 16 3.500 12.800 3.500 9.300 3.500 6.500 5.600 4.500 8 4.500c1.600 0 3 .8 4 2.200 1-1.400 2.400-2.200 4-2.200 2.400 0 4.500 2 4.500 4.800 0 3.500-2.500 6.700-8.500 11.200z"/>',
  bolt: '<path class="s" d="M13.500 2.500L5 13.500h6l-1 8 8.500-11h-6z"/>',
  snow: '<path d="M12 2.500v19M3.800 7.200l16.400 9.600M20.200 7.200L3.800 16.800M12 6l-2-2M12 6l2-2M12 18l-2 2M12 18l2 2"/>',
  wave: '<path d="M2.500 9c2.500-3 5-3 7 0s4.500 3 7 0c1.500-1.800 3-2.300 5-1.500M2.500 15.500c2.500-3 5-3 7 0s4.500 3 7 0c1.500-1.800 3-2.300 5-1.500"/>',
  wolf: '<path class="s" d="M4.500 3.500l4 3h7l4-3-1 7.500L15 19l-3 2-3-2-3.500-8z"/><path d="M9.300 11.300l1.700 1M14.700 11.300l-1.700 1M11 17h2"/>',
  trash: '<path d="M5 7h14M9.500 7V4.500h5V7M7 7l.8 13h8.400L17 7M10 10.500v6M14 10.500v6"/>',
  clock: '<circle cx="12" cy="12" r="8.500"/><path d="M12 7v5l3.500 2"/>',
  compass: '<circle cx="12" cy="12" r="8.500"/><path class="s" d="M15.500 8.500l-2 5-5 2 2-5z"/>',
  up: '<path class="f" d="M12 6.500l6.500 11h-13z"/>',
  down: '<path class="f" d="M12 17.500l6.500-11h-13z"/>',
  diamond: '<path class="s" d="M12 3l7 9-7 9-7-9z"/>',
  mouse: '<path class="s" d="M7 8.500a5 5 0 0110 0v7a5 5 0 01-10 0z"/><path d="M12 7v3.500"/>',
  rotate: '<path d="M4.500 12a7.500 7.500 0 0113.300-4.800M19.500 12a7.500 7.500 0 01-13.300 4.800M18 3.500v4h-4M6 20.500v-4h4"/>',
  sound: '<path class="s" d="M4 9.500h3.500l4.500-4v13l-4.500-4H4z"/><path d="M15.500 9a4 4 0 010 6M18 6.500a7.500 7.500 0 010 11"/>',
  dice: '<path class="s" d="M4.500 4.500h15v15h-15z"/><path d="M8.500 8.500h.01M15.500 8.500h.01M12 12h.01M8.500 15.500h.01M15.500 15.500h.01" stroke-width="2.200"/>',
  undo: '<path d="M8 5L4 9l4 4M4 9h10a5.500 5.500 0 010 11H9"/>',
  keyboard: '<path class="s" d="M2.500 6.500h19v11h-19z"/><path d="M6 10h.01M9 10h.01M12 10h.01M15 10h.01M18 10h.01M6 14h.01M18 14h.01M9 14h6"/>',
  screen: '<path class="s" d="M3 4.500h18v11.500H3z"/><path d="M8.500 20h7M12 16v4"/>',
  access: '<circle cx="12" cy="12" r="9"/><circle class="s" cx="12" cy="7.300" r="1.300"/><path d="M7.500 10l4.500 1 4.500-1M12 11v3.500M12 14.500L9.500 19M12 14.500l2.500 4.500"/>',
  gamepad: '<path class="s" d="M7 7h10c2.500 0 4.500 3 4.500 7.500 0 2-1 3-2.200 3-1.500 0-2.300-1.500-3.300-3H8c-1 1.500-1.800 3-3.300 3-1.200 0-2.200-1-2.200-3C2.500 10 4.500 7 7 7z"/><path d="M7.500 10v3M6 11.500h3M15.500 10.500h.01M17.500 12.500h.01"/>',
};

/** `<svg>` markup for an icon name. */
export function icon(name, cls = '') {
  return `<svg class="v-i${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ICONS.unknown}</svg>`;
}

// ------------------------------------------------------------------------------------------- items
const WEAPON_GLYPH = { sword: 'sword', dagger: 'dagger', axe: 'axe', mace: 'mace', greataxe: 'greataxe', greatsword: 'greatsword', hammer: 'hammer' };
const ID_GLYPH = {
  club: 'club', flask: 'flask', bread: 'bread', dried_meat: 'meat', herb_poultice: 'leaf', frost_salve: 'salve', whetstone: 'stone', vigor_elixir: 'flask',
  ember_bomb: 'bomb', return_charm: 'feather', wolf_pelt: 'pelt', spider_silk: 'web', bone_dust: 'bone', troll_hide: 'pelt', cinder_core: 'flame',
  steel_shard: 'shard', astral_fragment: 'crystal', amber_sap: 'drop', ember_seed: 'seed', wolf_fang: 'fang', garrick_ring: 'ring', chapel_key: 'key', old_letter: 'letter', torch: 'flame',
};
const TINTS = [
  [/rusty/, '#b87548'], [/fang/, '#e9e1cd'], [/drowned/, '#74b9ab'], [/colossus|frost/, '#a9dcf0'], [/dawn/, '#ffd98a'], [/watcher/, '#e3c47c'], [/royal/, '#e6c56c'],
  [/steel|plate/, '#cfd9df'], [/chain/, '#b7bcc0'], [/iron|mace|morningstar|war_|great_|claymore|hatchet|dagger/, '#c2bcae'],
  [/leather|bandit/, '#b98858'], [/robe/, '#9aa9d0'], [/peasant|club|wood/, '#a98e63'],
  [/torch|ember|cinder|whetstone/, '#e99a55'], [/amber|bread|meat/, '#e0b060'], [/herb|poultice/, '#9cc76a'], [/vigor/, '#8fd0a0'], [/astral|shard_/, '#8fe0f0'],
  [/silk|bone/, '#d8d2c2'], [/pelt|hide/, '#a8906c'],
];

export function itemGlyph(def) {
  if (!def) return 'unknown';
  if (ID_GLYPH[def.id]) return ID_GLYPH[def.id];
  switch (def.type) {
    case 'weapon': return WEAPON_GLYPH[def.cls] || 'sword';
    case 'shield': return 'shield';
    case 'armor': return def.slot === 'head' ? 'helm' : def.slot === 'legs' ? 'legs' : 'chest';
    case 'consumable': { const e = def.effect || {}; return e.throw ? 'bomb' : e.recall ? 'feather' : e.cure ? 'leaf' : e.regen ? 'bread' : 'flask'; }
    case 'material': return 'shard';
    case 'key': return /^shard_/.test(def.id) ? 'crystal' : 'key';
    default: return 'unknown';
  }
}

export function itemRarity(def) {
  if (!def) return 'common';
  if (def.type === 'key') return /^shard_/.test(def.id) ? 'eclat' : 'key';
  if (def.unique || def.set === 'royal' || def.id === 'astral_fragment') return def.id === 'astral_fragment' ? 'eclat' : 'legend';
  const v = def.value || 0;
  if (def.type === 'weapon' || def.type === 'shield' || def.type === 'armor') return v >= 500 ? 'rare' : v >= 200 ? 'fine' : 'common';
  return v >= 60 ? 'fine' : 'common';
}

export function itemTint(def) {
  if (!def) return '#8a8372';
  for (const [re, c] of TINTS) if (re.test(def.id)) return c;
  return '#c9bfa8';
}

/** framed item icon (id may be unknown -> "?" glyph). */
export function itemIcon(id, cls = '') {
  const def = ITEMS[id];
  return `<span class="v-item-ico r-${itemRarity(def)}${cls ? ' ' + cls : ''}" style="color:${itemTint(def)}">${icon(itemGlyph(def))}</span>`;
}

export const SKILL_GLYPH = { ember_bolt: 'flame', wolf_howl: 'wolf', shadow_web: 'web', drowned_tide: 'wave', frost_nova: 'snow', ysolde_flame: 'pyre' };
export const SKILL_TINT = { ember_bolt: '#f29a4e', wolf_howl: '#e6dcc4', shadow_web: '#b08cf0', drowned_tide: '#6fc0b4', frost_nova: '#a9e2ff', ysolde_flame: '#ffb45e' };
export const skillIcon = (id) => icon(SKILL_GLYPH[id] || 'crystal');

export const STATUS_GLYPH = { poison: 'drop', burn: 'flame', frost: 'snow', slow: 'web', bleed: 'drop' };
export const BUFFS = {
  sharp: { name: 'Fil aiguisé', glyph: 'sword', color: '#e6dcc4' },
  vigor: { name: 'Vigueur', glyph: 'bolt', color: '#8fd0a0' },
  fury: { name: 'Fureur de l\'Alpha', glyph: 'wolf', color: '#f29a4e' },
};

/** the shattered star of the title screen */
export const EMBLEM = `<svg class="v-emblem" viewBox="0 0 120 120" aria-hidden="true">
  <defs><radialGradient id="v-emb-g" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#dff8ff" stop-opacity=".95"/><stop offset=".35" stop-color="#7fd6e8" stop-opacity=".55"/><stop offset="1" stop-color="#7fd6e8" stop-opacity="0"/></radialGradient></defs>
  <circle cx="60" cy="60" r="46" fill="url(#v-emb-g)" opacity=".5"/>
  <g fill="none" stroke="currentColor" stroke-width="1" stroke-linejoin="round">
    <path d="M60 6l7 40-7 8-7-8z" fill="currentColor" fill-opacity=".14"/>
    <path d="M114 60l-40 7-8-7 8-7z" fill="currentColor" fill-opacity=".08" transform="translate(3 -2) rotate(4 90 60)"/>
    <path d="M60 114l-7-40 7-8 7 8z" fill="currentColor" fill-opacity=".14" transform="translate(-2 3)"/>
    <path d="M6 60l40-7 8 7-8 7z" fill="currentColor" fill-opacity=".08"/>
    <path d="M24 24l25 20 1 9-9-1z" transform="translate(-2 -1)"/><path d="M96 24L76 49l-9 1 1-9z" transform="translate(2 -3) rotate(5 82 38)"/>
    <path d="M96 96L71 76l-1-9 9 1z" transform="translate(3 2)"/><path d="M24 96l20-25 9-1-1 9z"/>
    <circle cx="60" cy="60" r="4.500" fill="currentColor" fill-opacity=".5"/><circle cx="60" cy="60" r="30" stroke-dasharray="2 5" opacity=".5"/>
  </g></svg>`;
