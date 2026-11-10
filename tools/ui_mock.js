// VALOMBRE — UI test bench: a fake `app` that implements the whole UI contract (src/ui/CONTRACT.md) with
// plausible data, so that src/ui/ui.js can be exercised without the engine. See tools/ui_test.html.
//
// URL parameters: ?state=boot|title|creator|playing  &open=inventory|character|map|journal|pause|options|saves|credits|
//   shrine|shop|smith|dialogue|death|ending  &boss=1  &demo=0 (no fake fight)  &saves=0 (no save -> no "Continuer")
//   &hp=0.2  &scale=120  &cb=deuter|protan|tritan  &bar=1 (debug toolbar; also toggled with the ² / ` key)
// Console / automation: window.__mock (go, open, hurt, hit, boss, kill, toast, discover, banner, rest, shop, smith,
//   talk, ending, status, buff, levelUp, tick(seconds), log).
import { bus } from '../src/core/events.js';
import { Settings, applySettings } from '../src/core/settings.js';
import { Input } from '../src/core/input.js';
import { ITEMS, UPGRADE_COST } from '../src/game/data/items.js';
import { ORIGINS, SKILLS, REGIONS, STATUS, derive, xpForLevel, MAX_LEVEL } from '../src/game/data/rules.js';
import { MORPH_FALLBACK, defaultAppearance } from '../src/game/data/creator.js';
import { CODEX, QUESTS, ENDINGS } from '../src/game/data/story.js';
import { UI } from '../src/ui/ui.js';

const params = new URLSearchParams(location.search);
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const log = [];
const note = (...a) => { log.push(a.join(' ')); if (log.length > 60) log.shift(); const el = document.getElementById('mocklog'); if (el) el.textContent = log.slice(-4).join('\n'); };

class V3 {
  constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; }
  clone() { return new V3(this.x, this.y, this.z); }
}

// settings are kept under their own storage key so that the bench never alters the real game's options
const KEY = 'valombre.uitest.settings';
class MockSettings extends Settings {
  load() { try { const d = JSON.parse(localStorage.getItem(KEY) || 'null'); if (!d) return; for (const k in d.values || {}) if (k in this.values) this.values[k] = d.values[k]; for (const k in d.binds || {}) if (k in this.binds && Array.isArray(d.binds[k])) this.binds[k] = d.binds[k]; this.autoPreset = d.autoPreset || null; } catch (e) { /* ignore */ } }
  save() { try { localStorage.setItem(KEY, JSON.stringify({ values: this.values, binds: this.binds, autoPreset: this.autoPreset })); } catch (e) { /* ignore */ } }
}

// ------------------------------------------------------------------------------------------ world data
const WORLD = { shrines: [['s_hautefeuille', 'Autel de Hautefeuille', -118, 1418], ['s_croisee', 'Autel de la Croisée', -40, 905], ['s_laniere', 'Autel du Louvetier', -760, 760], ['s_refuge', 'Autel du Refuge', -1165, 318], ['s_port', 'Autel de Port-Brisants', 1450, 1908]].map(([id, name, x, z]) => ({ id, name, x, z })),
  pois: [['hautefeuille', 'village', 'Hautefeuille', -150, 1450], ['port_brisants', 'hamlet', 'Port-Brisants', 1480, 1930], ['camp_ecorcheurs', 'bandit_camp', 'Camp des Écorcheurs', 560, 1180], ['boss_wolf', 'arena', 'Tanière de Croc-Blême', -860, 860]].map(([id, type, name, x, z]) => ({ id, type, name, x, z })) };
const mapImage = new Image();
mapImage.src = new URL('../assets/world/map.png', import.meta.url).href;
try {
  const w = await (await fetch(new URL('../assets/world/world.json', import.meta.url))).json();
  if (Array.isArray(w.shrines) && w.shrines.length) WORLD.shrines = w.shrines.map((s) => ({ id: s.id, name: s.name, x: s.x, z: s.z }));
  if (Array.isArray(w.pois) && w.pois.length) WORLD.pois = w.pois.map((s) => ({ id: s.id, type: s.type, name: s.name, x: s.x, z: s.z }));
} catch (e) { note('world.json indisponible : données de secours'); }

let morphs = MORPH_FALLBACK;
try { const m = await (await fetch(new URL('../assets/models/char/human_manifest.json', import.meta.url))).json(); if (Array.isArray(m.morphs) && m.morphs.length) morphs = m.morphs.filter((x) => x.category !== 'expression'); } catch (e) { /* fallback list */ }

// the real newPlayerData when src/game/player.js imports cleanly in the browser (needs the "three" import map)
let newPlayerData = null;
try { ({ newPlayerData } = await import('../src/game/player.js')); } catch (e) { note('player.js non importable : équivalent local'); }
if (typeof newPlayerData !== 'function') {
  newPlayerData = (name, originId, appearance) => {
    const o = ORIGINS.find((x) => x.id === originId) || ORIGINS[0];
    const d = { name: name || 'Veilleur', origin: o.id, appearance: appearance || {}, level: 1, xp: 0, attrPoints: 0, attrs: { ...o.attrs }, hp: 1, stamina: 1, mana: 1, gold: o.gold, flasks: 3, flaskMax: 3, flaskLevel: 0,
      equipment: { weapon: null, offhand: null, head: null, chest: null, legs: null }, inventory: [], skills: [], skillSlots: [null, null, null], shards: [], pos: null, yaw: 0, lastShrine: 's_hautefeuille',
      discovered: { shrines: ['s_hautefeuille'], pois: [], lore: [], regions: [] }, quests: {}, flags: {}, killed: {}, opened: {}, stats: { kills: 0, deaths: 0, bosses: 0, time: 0 }, hour: 8.5, day: 1 };
    for (const slot in o.gear) d.equipment[slot] = { id: o.gear[slot], up: 0 };
    for (const [id, qty] of o.items) d.inventory.push({ id, qty, up: 0 });
    if (o.skill) { d.skills.push(o.skill); d.skillSlots[0] = o.skill; }
    const st = derive(d); d.hp = st.maxHp; d.stamina = st.maxSt; d.mana = st.maxMana;
    return d;
  };
}

function veteranData() {
  const d = newPlayerData('Aldéric', 'veilleur', defaultAppearance());
  Object.assign(d, { level: 9, xp: 1320, attrPoints: 2, gold: 437, flasks: 3, flaskMax: 4, flaskLevel: 1, day: 3, hour: 17.4 });
  d.attrs = { vigueur: 15, endurance: 13, force: 14, dexterite: 12, arcane: 10 };
  d.equipment.weapon = { id: 'iron_sword', up: 2 };
  const inv = [['steel_sword', 1, 1], ['dagger', 1, 0], ['war_axe', 1, 0], ['claymore', 1, 0], ['fang_blade', 1, 0], ['iron_shield', 1, 0], ['leather_head', 1, 0], ['leather_chest', 1, 0], ['plate_chest', 1, 0], ['robe_legs', 1, 0],
    ['bread', 4, 0], ['dried_meat', 2, 0], ['herb_poultice', 3, 0], ['whetstone', 2, 0], ['vigor_elixir', 1, 0], ['ember_bomb', 3, 0], ['return_charm', 1, 0],
    ['wolf_pelt', 6, 0], ['spider_silk', 3, 0], ['steel_shard', 4, 0], ['astral_fragment', 1, 0], ['amber_sap', 1, 0], ['ember_seed', 1, 0], ['bone_dust', 5, 0],
    ['shard_spider', 1, 0], ['wolf_fang', 1, 0], ['old_letter', 1, 0]];
  for (const [id, qty, up] of inv) d.inventory.push({ id, qty, up });
  d.skills = ['ember_bolt', 'wolf_howl', 'shadow_web']; d.skillSlots = ['ember_bolt', 'wolf_howl', null];
  d.discovered = { shrines: ['s_hautefeuille', 's_croisee', 's_laniere', 's_refuge', 's_port'], pois: ['hautefeuille', 'port_brisants', 'camp_ecorcheurs', 'boss_wolf', 'refuge'], regions: ['meadow', 'forest'],
    lore: ['nuit', 'astre', 'ordre', 'eclats', 'hautefeuille', 'port', 'sombreronce', 'refuge', 'c_wolf', 'c_bandit', 'c_spider', 'p_maelle', 'p_crocbleme'] };
  d.quests = { main: { state: 'active', n: 0, tracked: true }, wolf: { state: 'done', n: 0 }, bandits: { state: 'active', n: 0 }, silk: { state: 'active', n: 0 }, troll: { state: 'active', n: 1 } };
  d.flags = { boss_wolf: true };
  d.stats = { kills: 84, deaths: 6, bosses: 1, time: 3 * 3600 + 1560 };
  const st = derive(d); d.hp = st.maxHp; d.stamina = st.maxSt; d.mana = st.maxMana;
  return d;
}

// ------------------------------------------------------------------------------------------------ app
const settings = new MockSettings();
const input = new Input(canvas, settings);
if (params.has('scale')) settings.values.uiScale = Number(params.get('scale')) || 100;
if (params.has('cb')) settings.values.colorblind = params.get('cb');

const saves = (() => {
  const now = Date.now();
  let slots = params.get('saves') === '0' ? [null, null, null, null] : [
    { name: 'Aldéric', level: 9, region: 'Prés de Hautefeuille', playtime: 3 * 3600 + 1560, date: now - 3600e3 * 2, origin: 'veilleur' },
    { name: 'Aldéric', level: 7, region: 'Forêt de Sombreronce', playtime: 2 * 3600 + 300, date: now - 86400e3, origin: 'veilleur' },
    null,
    { name: 'Ysoria', level: 21, region: 'Pics de Givrelame', playtime: 14 * 3600 + 2040, date: now - 86400e3 * 9, origin: 'disciple' },
  ];
  return {
    list: () => slots.map((s, i) => (s ? { slot: i, empty: false, ...s } : { slot: i, empty: true })),
    latest: () => { let b = -1, t = -1; slots.forEach((s, i) => { if (s && s.date > t) { t = s.date; b = i; } }); return b; },
    delete: (i) => { slots[i] = null; note('saves.delete', i); },
    write: (i, s) => { slots[i] = s; },
  };
})();

const app = {
  state: 'boot', settings, input, audio: null, game: null, creator: null, saves, version: '0.9.2',
  gpu: 'ANGLE (AMD, AMD Radeon(TM) Vega 8 Graphics Direct3D11 vs_5_0 ps_5_0)',
  blocking: null, sfxLog: [],
  sfx(name) { this.sfxLog.push(name); if (this.sfxLog.length > 40) this.sfxLog.shift(); },
  perf: () => ({ fps: 57 + Math.round(Math.random() * 6), ms: 16.2 + Math.random(), calls: 412, tris: 684000, scale: settings.get('renderScale') / 100, res: [Math.round(innerWidth * settings.get('renderScale') / 100), Math.round(innerHeight * settings.get('renderScale') / 100)] }),
  setUiBlocking(b) { this.blocking = b; input.gameEnabled = !b; note('setUiBlocking', b); },
  async benchmark() { note('benchmark…'); await new Promise((r) => setTimeout(r, 1600)); settings.autoPreset = 'high'; settings.save(); if (settings.get('preset') === 'auto') { settings.applyPreset(); bus.emit('settings', '*'); } return { preset: 'high', fps: 52 }; },
  continueGame() { note('continueGame'); startGame(veteranData()); },
  loadSlot(slot) { note('loadSlot', slot); startGame(veteranData()); },
  saveSlot(slot) { if (!this.game || this.game.player.dead || fight.danger) { note('saveSlot refusé'); return false; } const d = this.game.player.data; saves.write(slot, { name: d.name, level: d.level, region: this.game.region.name, playtime: d.stats.time, date: Date.now(), origin: d.origin }); note('saveSlot', slot); return true; },
  openCreator() { note('openCreator'); this.creator = makeCreator(); setState('creator'); },
  startNewGame({ name, origin, appearance }) { note('startNewGame', name, origin, Object.keys((appearance && appearance.morphs) || {}).length + ' morphs'); this.lastNewGame = { name, origin, appearance }; startGame(newPlayerData(name, origin, appearance), true); },
  quitToTitle() { note('quitToTitle'); this.game = null; this.creator = null; setState('title'); },
};

function setState(s) { const old = app.state; if (s === old) return; app.state = s; bus.emit('state', s, old); }

// -------------------------------------------------------------------------------------------- creator
const look = { yaw: 0, view: 'body', zoom: 0 };
function makeCreator() {
  const c = {
    morphs, appearance: defaultAppearance(), origin: 'veilleur', calls: [],
    set(key, value) { this.appearance[key] = value; this.calls.push(['set', key, value]); note('creator.set', key, typeof value === 'number' ? value.toFixed(2) : value); },
    setMorph(name, value) { this.appearance.morphs[name] = value; this.calls.push(['setMorph', name, value]); note('creator.setMorph', name, value.toFixed(2)); },
    setAll(a) { this.appearance = { ...defaultAppearance(), ...a, morphs: { ...(a.morphs || {}) } }; this.calls.push(['setAll']); note('creator.setAll'); },
    setOrigin(id) { this.origin = id; this.calls.push(['setOrigin', id]); note('creator.setOrigin', id); },
    setView(v) { look.view = v; this.calls.push(['setView', v]); note('creator.setView', v); },
    rotate(d) { look.yaw += d; this.calls.push(['rotate', d]); },
    playVoice() { this.calls.push(['playVoice']); note('creator.playVoice', this.appearance.voice); },
  };
  look.yaw = 0; look.view = 'body';
  return c;
}

// ----------------------------------------------------------------------------------------------- game
const fight = { on: params.get('demo') !== '0', t: 0, danger: false };
const cam = { yaw: 0.6 };

function startGame(data, fresh) {
  app.game = makeGame(data, fresh);
  setState('playing');
  bus.emit('inventory'); bus.emit('quest'); bus.emit('player:stats');
  if (fresh) setTimeout(() => bus.emit('discover', { name: REGIONS.meadow.name, sub: REGIONS.meadow.desc }), 600);
}

function makeGame(d, fresh) {
  const shrineById = {}; for (const s of WORLD.shrines) shrineById[s.id] = s;
  const home = shrineById[d.lastShrine] || WORLD.shrines[0];
  const p = {
    data: d, st: derive(d), hp: d.hp, maxHp: 1, status: {}, statusThreshold: 30, buffs: {}, target: null, dead: false, state: 'free', skillCd: {},
    pos: new V3(home.x + 14, 20, home.z + 22), yaw: 0.6, height: 1.8,
    refresh() { this.st = derive(d); this.maxHp = this.st.maxHp; this.hp = Math.min(this.hp, this.maxHp); d.stamina = Math.min(d.stamina, this.st.maxSt); d.mana = Math.min(d.mana, this.st.maxMana); bus.emit('player:stats'); },
    count(id) { let n = 0; for (const it of d.inventory) if (it.id === id) n += it.qty; return n; },
    addItem(id, qty = 1, up = 0, silent = false) {
      const def = ITEMS[id]; if (!def) return;
      const stackable = def.type === 'consumable' || def.type === 'material' || def.type === 'key';
      const ex = stackable ? d.inventory.find((i) => i.id === id) : null;
      if (ex) ex.qty += qty; else if (stackable) d.inventory.push({ id, qty, up: 0 }); else for (let i = 0; i < qty; i++) d.inventory.push({ id, qty: 1, up });
      if (!silent) bus.emit('toast', { kind: 'item', id, qty });
      bus.emit('inventory');
    },
    removeItem(id, qty = 1) { for (let i = d.inventory.length - 1; i >= 0 && qty > 0; i--) { if (d.inventory[i].id !== id) continue; const take = Math.min(d.inventory[i].qty, qty); d.inventory[i].qty -= take; qty -= take; if (d.inventory[i].qty <= 0) d.inventory.splice(i, 1); } bus.emit('inventory'); return qty === 0; },
    equip(index) {
      const it = d.inventory[index], def = it && ITEMS[it.id]; if (!def || !def.slot) return;
      const eq = d.equipment; d.inventory.splice(index, 1);
      if (eq[def.slot]) d.inventory.push({ id: eq[def.slot].id, qty: 1, up: eq[def.slot].up || 0 });
      eq[def.slot] = { id: it.id, up: it.up || 0 };
      if (def.slot === 'weapon' && def.moveset === '2h' && eq.offhand) { d.inventory.push({ id: eq.offhand.id, qty: 1, up: eq.offhand.up || 0 }); eq.offhand = null; }
      this.refresh(); app.sfx('ui_equip'); bus.emit('inventory'); note('player.equip', it.id);
    },
    unequip(slot) { const eq = d.equipment; if (!eq[slot]) return; d.inventory.push({ id: eq[slot].id, qty: 1, up: eq[slot].up || 0 }); eq[slot] = null; this.refresh(); bus.emit('inventory'); note('player.unequip', slot); },
    spendPoint(attr) { if (d.attrPoints <= 0 || d.attrs[attr] >= 50) return false; d.attrPoints--; d.attrs[attr]++; const r = this.hp / this.maxHp; this.refresh(); this.hp = Math.round(this.maxHp * r); note('player.spendPoint', attr); return true; },
    addXp(n) { if (d.level >= MAX_LEVEL) return; d.xp += Math.round(n); let up = false; while (d.xp >= xpForLevel(d.level)) { d.xp -= xpForLevel(d.level); d.level++; d.attrPoints++; up = true; } if (up) { this.refresh(); this.hp = this.maxHp; bus.emit('toast', { kind: 'level', level: d.level }); } bus.emit('player:xp'); },
    heal(a) { this.hp = Math.min(this.maxHp, this.hp + a); },
    buff(name, mult, t) { this.buffs[name] = { t, mult }; bus.emit('player:buffs'); },
  };
  p.maxHp = p.st.maxHp; p.hp = Math.min(d.hp, p.maxHp);

  const mkEnemy = (name, dx, dz, hp, height = 1.8, w = 0.5) => ({ pos: new V3(p.pos.x + dx, 20, p.pos.z + dz), height, hp, maxHp: hp, barT: 0, dead: false, isBoss: false, vulnerableT: 0, def: { name }, w, ph: Math.random() * 6, hx: dx, hz: dz, fade: 0 });
  const enemies = [mkEnemy('Loup', 2.5, 7.5, 80, 1.0, 0.7), mkEnemy('Écorcheur', -3.2, 9, 130), mkEnemy('Écorcheur colosse', 5.5, 11, 260, 2.15, 0.7), mkEnemy('Loup sinistre', -6, 13, 150, 1.15, 0.8), mkEnemy('Écorcheur au bouclier', 0.5, 14, 160)];

  const questList = () => Object.keys(d.quests).filter((id) => QUESTS[id]).map((id) => {
    const q = d.quests[id], def = QUESTS[id];
    const fake = { main: 1, bandits: 0, silk: 0, troll: 0, wolf: 9 }[id] ?? 0;
    return { id, title: def.title, desc: def.desc, state: q.state, main: !!def.main, tracked: !!q.tracked && q.state === 'active', steps: def.steps.map((s, i) => ({ text: s.text, done: q.state === 'done' || i < fake })) };
  }).sort((a, b) => (b.main - a.main) || (a.state === 'done') - (b.state === 'done'));
  const QM = { main: [-1800, -150], bandits: [560, 1180], silk: [-150, 1450], troll: [-620, -1230] };

  const g = {
    player: p, enemies, boss: null, focus: null, region: { id: 'meadow', name: REGIONS.meadow.name }, day: d.day || 1, hour: d.hour ?? 8.5,
    shrine: null, shop: null, smith: null, dialogue: null, canFastTravel: false, _shrines: shrineById,
    toScreen(v, out = {}) {
      const fx = Math.sin(cam.yaw), fz = Math.cos(cam.yaw);
      const cx = p.pos.x - fx * 5.6, cy = p.pos.y + 2.5, cz = p.pos.z - fz * 5.6;
      const rx = v.x - cx, ry = v.y - cy, rz = v.z - cz;
      const depth = rx * fx + rz * fz, side = rx * -fz + rz * fx;
      const f = (innerHeight * 0.5) / Math.tan(31 * Math.PI / 180);
      out.depth = depth;
      if (depth < 0.4) { out.visible = false; out.x = -9999; out.y = -9999; return out; }
      out.x = innerWidth * 0.5 + side / depth * f; out.y = innerHeight * 0.44 - (ry + depth * 0.1) / depth * f;
      out.visible = out.x > -40 && out.x < innerWidth + 40 && out.y > -40 && out.y < innerHeight + 40;
      return out;
    },
    compass() {
      const markers = [];
      for (const id of d.discovered.shrines) { const s = shrineById[id]; if (s && Math.hypot(s.x - p.pos.x, s.z - p.pos.z) < 700) markers.push({ kind: 'shrine', x: s.x, z: s.z, name: s.name }); }
      for (const m of this.quests.markers()) if (m.tracked) markers.push({ kind: 'quest', x: m.x, z: m.z, name: m.name });
      if (this.boss) markers.push({ kind: 'boss', x: this.boss.pos.x, z: this.boss.pos.z, name: this.boss.def.name });
      return { yaw: cam.yaw, markers };
    },
    map() {
      return { image: mapImage, player: { x: p.pos.x, z: p.pos.z, yaw: p.yaw },
        shrines: WORLD.shrines.map((s) => ({ id: s.id, name: s.name, x: s.x, z: s.z, found: d.discovered.shrines.includes(s.id) })),
        pois: WORLD.pois.map((o) => ({ id: o.id, name: o.name, type: o.type, x: o.x, z: o.z, found: d.discovered.pois.includes(o.id) })),
        quests: this.quests.markers() };
    },
    quests: {
      list: questList,
      track(id) { for (const k in d.quests) d.quests[k].tracked = k === id; note('quests.track', id); bus.emit('quest'); },
      markers() { const out = []; for (const id in d.quests) { const q = d.quests[id]; if (q.state !== 'active' || !QM[id] || !QUESTS[id]) continue; out.push({ x: QM[id][0], z: QM[id][1], name: QUESTS[id].title, tracked: !!q.tracked }); } return out; },
    },
    codex() { return Object.keys(CODEX).map((id) => ({ id, title: CODEX[id].title, text: CODEX[id].text, category: CODEX[id].category, found: d.discovered.lore.includes(id) })); },
    useItem(index) {
      const it = d.inventory[index], def = it && ITEMS[it.id]; if (!def) return false;
      if (def.slot) { p.equip(index); return true; }
      if (def.type !== 'consumable') return false;
      const e = def.effect;
      if (e.heal) p.heal(p.maxHp * e.heal);
      if (e.regen) p.heal(p.maxHp * 0.2);
      if (e.cure) delete p.status[e.cure];
      if (e.buff) p.buff(e.buff, e.mult, e.time);
      p.removeItem(it.id, 1); note('game.useItem', it.id); return true;
    },
    dropItem(index) { const it = d.inventory[index]; if (!it || ITEMS[it.id].type === 'key') return; note('game.dropItem', it.id); p.removeItem(it.id, it.qty); },
    setSkillSlot(slot, id) { if (id && !d.skills.includes(id)) return; for (let i = 0; i < 3; i++) if (d.skillSlots[i] === id) d.skillSlots[i] = null; d.skillSlots[slot] = id; note('game.setSkillSlot', slot, id); bus.emit('player:stats'); },
    fastTravel(id) { const s = shrineById[id]; if (!s || !this.canFastTravel) return; note('game.fastTravel', id); p.pos.set(s.x + 6, 20, s.z + 8); d.lastShrine = id; this.shrine.id = id; this.shrine.name = s.name; rest(); },
    shrineAction(a) {
      if (!this.shrine) return; note('game.shrineAction', a);
      if (a === 'flaskCount' && p.count('amber_sap') > 0 && d.flaskMax < 9) { p.removeItem('amber_sap', 1); d.flaskMax++; d.flasks = d.flaskMax; bus.emit('player:flask'); }
      else if (a === 'flaskPower' && p.count('ember_seed') > 0 && d.flaskLevel < 5) { p.removeItem('ember_seed', 1); d.flaskLevel++; bus.emit('player:flask'); }
      else if (a === 'morning' || a === 'night') { const t = a === 'morning' ? 7.5 : 21.5; if (this.hour > t) { d.day++; this.day = d.day; } this.hour = t; rest(); }
      else if (a === 'leave') this.closePanel();
    },
    closePanel() { note('game.closePanel'); if (this.shrine) { this.shrine = null; this.canFastTravel = false; p.state = 'free'; } this.shop = null; this.smith = null; if (this.dialogue) { this.dialogue = null; bus.emit('dialogue'); } },
  };
  const rest = () => { p.refresh(); p.hp = p.maxHp; d.stamina = p.st.maxSt; d.mana = p.st.maxMana; d.flasks = d.flaskMax; p.status = {}; for (const e of enemies) { e.hp = e.maxHp; e.dead = false; e.barT = 0; } bus.emit('player:flask'); };
  g._rest = rest;
  if (fresh) { d.quests.main = { state: 'active', n: 0, tracked: true }; }
  return g;
}

// ---- services
function openShrine(isNew) {
  const g = app.game; if (!g) return;
  const p = g.player, d = p.data;
  const s = g._shrines[d.lastShrine] || WORLD.shrines[0];
  if (isNew) bus.emit('banner', { title: 'AUTEL EMBRASÉ', sub: s.name, kind: 'shrine' });
  p.target = null; bus.emit('lock', null); p.state = 'rest'; g._rest();
  g.shrine = { id: s.id, name: s.name, get flaskCountCost() { return p.count('amber_sap') > 0 && d.flaskMax < 9; }, get flaskPowerCost() { return p.count('ember_seed') > 0 && d.flaskLevel < 5; } };
  g.canFastTravel = true;
  setTimeout(() => { if (g.shrine) bus.emit('open', 'shrine'); }, isNew ? 1200 : 150);
}
function openShop() {
  const g = app.game; if (!g) return;
  const p = g.player, d = p.data;
  const stock = [['bread', 10], ['dried_meat', 8], ['herb_poultice', 6], ['frost_salve', 4], ['whetstone', 4], ['vigor_elixir', 3], ['ember_bomb', 4], ['return_charm', 2], ['iron_shield', 1], ['mace', 1], ['chain_chest', 1], ['watcher_blade', 1], ['steel_shard', 3]].map(([id, qty]) => ({ id, price: Math.max(1, ITEMS[id].value), qty }));
  g.dialogue = null; bus.emit('dialogue');
  g.shop = { name: 'Ysabeau', stock,
    buy(i) { const s = stock[i]; if (!s || s.qty <= 0 || d.gold < s.price) return false; d.gold -= s.price; s.qty--; p.addItem(s.id, 1, 0, true); note('shop.buy', s.id); return true; },
    sellPrice(idx) { const it = d.inventory[idx], def = it && ITEMS[it.id]; return def && def.type !== 'key' ? Math.max(1, Math.floor((def.value || 0) * 0.4 * (1 + (it.up || 0) * 0.3))) : 0; },
    sell(idx) { const it = d.inventory[idx], pr = this.sellPrice(idx); if (!it || pr <= 0) return false; d.gold += pr; note('shop.sell', it.id); p.removeItem(it.id, 1); return true; },
    close() { g.closePanel(); } };
  bus.emit('open', 'shop');
}
function openSmith() {
  const g = app.game; if (!g) return;
  const p = g.player, d = p.data;
  g.dialogue = null; bus.emit('dialogue');
  const entry = (where, inst) => { const def = ITEMS[inst.id]; if (!def || !def.maxUp || (inst.up || 0) >= def.maxUp) return null; const cost = UPGRADE_COST[inst.up || 0]; let can = d.gold >= cost.gold; for (const k in cost) if (k !== 'gold' && p.count(k) < cost[k]) can = false; return { where, id: inst.id, up: inst.up || 0, cost, can }; };
  g.smith = {
    list() { const out = []; for (const slot of ['weapon', 'offhand']) if (d.equipment[slot]) { const e = entry(slot, d.equipment[slot]); if (e) out.push(e); } d.inventory.forEach((it, i) => { const e = entry(i, it); if (e) out.push(e); }); return out; },
    upgrade(where) { const inst = typeof where === 'string' ? d.equipment[where] : d.inventory[where]; const e = inst && entry(where, inst); if (!e || !e.can) return false; d.gold -= e.cost.gold; for (const k in e.cost) if (k !== 'gold') p.removeItem(k, e.cost[k]); inst.up = (inst.up || 0) + 1; p.refresh(); bus.emit('inventory'); note('smith.upgrade', inst.id, '+' + inst.up); return true; },
    close() { g.closePanel(); } };
  bus.emit('open', 'smith');
}
function talk() {
  const g = app.game; if (!g) return;
  const def = { name: 'Hildegarde', role: 'Forgeronne' };
  const end = (text) => ({ text, options: [{ label: 'Au revoir.', go: () => null }] });
  const root = () => ({ text: "Du fer, j'en ai. De l'acier, plus depuis que le col est fermé. Les Écorcheurs m'ont pris mes réserves, et personne n'ose aller les leur reprendre. Qu'est-ce qu'il vous faut, Veilleur ?", options: [
    { label: 'Voir vos marchandises.', go: () => { openShop(); return null; } },
    { label: 'Améliorer mon équipement.', go: () => { openSmith(); return null; } },
    { label: "Vous manquez d'acier ?", go: () => ({ text: "Rapportez-moi trois éclats d'acier — les Écorcheurs en ont plein les poches, c'est le mien qu'ils ont volé. Je vous forgerai une vraie épée.", options: [{ label: "Je m'en charge.", go: () => { bus.emit('toast', { kind: 'quest', title: "L'acier de Roc-au-Vent", done: false }); return end('Alors bonne chasse. Et ramenez votre peau avec.'); } }, { label: 'Parlons d\'autre chose.', go: root }] }) },
    { label: 'Au revoir.', go: () => null }] });
  const setNode = (node) => {
    if (!node) { g.dialogue = null; bus.emit('dialogue'); return; }
    const opts = node.options && node.options.length ? node.options : [{ label: 'Au revoir.', go: () => null }];
    g.dialogue = { speaker: def.name, role: def.role, text: node.text, options: opts.map((o) => ({ label: o.label })), choose: (i) => { const o = opts[i]; if (!o) return; note('dialogue.choose', i); setNode(o.go ? o.go() : null); } };
    bus.emit('dialogue');
  };
  setNode(root());
}

// ---- fake fight
function hitEnemy(e, dmg, crit) {
  const g = app.game; if (!g || !e || e.dead) return;
  e.hp = Math.max(0, e.hp - dmg); e.barT = 8;
  bus.emit('damage', { x: e.pos.x, y: e.pos.y + e.height * 0.9, z: e.pos.z, dmg, crit: !!crit, blocked: false });
  if (e.hp <= 0) {
    e.dead = true;
    if (e.isBoss) { g.boss = null; bus.emit('boss:end', { boss: e, won: true }); bus.emit('banner', { title: 'ÉCLAT RETROUVÉ', sub: e.def.name + ' — ' + e.def.title, kind: 'shard' }); bus.emit('toast', { kind: 'skill', id: 'shadow_web' }); g.player.addItem('shard_knight', 1); const i = g.enemies.indexOf(e); if (i >= 0) g.enemies.splice(i, 1); }
    else { bus.emit('toast', { kind: 'xp', n: 45 }); g.player.addXp(45); if (Math.random() < 0.5) bus.emit('toast', { kind: 'gold', n: 8 + Math.floor(Math.random() * 20) }); if (Math.random() < 0.35) g.player.addItem('wolf_pelt', 1); setTimeout(() => { e.hp = e.maxHp; e.dead = false; e.barT = 0; }, 9000); }
    if (g.player.target === e) { g.player.target = null; bus.emit('lock', null); }
  }
}
function hurt(dmg, status) {
  const g = app.game; if (!g) return; const p = g.player; if (p.dead) return;
  p.hp = Math.max(0, p.hp - dmg); bus.emit('player:hurt', dmg);
  if (status) { const s = p.status[status] || (p.status[status] = { t: 0, build: 0 }); if (s.t <= 0) { s.build += 12; if (s.build >= p.statusThreshold) { s.build = 0; s.t = STATUS[status].time || 6; bus.emit('toast', { kind: 'text', text: { poison: 'Empoisonné !', burn: 'Vous brûlez !', frost: 'Gelé !', slow: 'Entravé !', bleed: 'Hémorragie !' }[status] }); } } }
  if (p.hp <= 0) die();
}
function die() {
  const g = app.game; if (!g) return; const p = g.player; if (p.dead) return;
  p.dead = true; p.hp = 0; p.target = null; bus.emit('lock', null); bus.emit('death'); note('death');
  setTimeout(() => { if (app.game !== g) return; p.dead = false; g._rest(); if (g.boss) { const b = g.boss; g.boss = null; bus.emit('boss:end', { boss: b, won: false }); const i = g.enemies.indexOf(b); if (i >= 0) g.enemies.splice(i, 1); } bus.emit('respawn'); note('respawn'); }, 4600);
}
function startBoss() {
  const g = app.game; if (!g || g.boss) return; const p = g.player;
  const e = { pos: new V3(p.pos.x + Math.sin(cam.yaw) * 13, 20, p.pos.z + Math.cos(cam.yaw) * 13), height: 3.4, hp: 2400, maxHp: 2400, barT: 0, dead: false, isBoss: true, vulnerableT: 0, def: { name: 'Arakha', title: 'La Reine Tisseuse' }, phase: 1, w: 2.2, ph: 0, hx: 0, hz: 13, boss: true };
  g.enemies.push(e); g.boss = e;
  bus.emit('boss:start', e); bus.emit('banner', { title: 'ARAKHA', sub: 'La Reine Tisseuse', kind: 'boss' });
}

function simulate(dt) {
  const g = app.game; if (!g) return;
  const p = g.player, d = p.data;
  d.stats.time += dt;
  g.hour = (g.hour + dt / 75) % 24;
  if (app.blocking) return;                                  // the app pauses the world while a panel is open
  // camera / movement from the real input actions
  if (!p.dead && p.state !== 'rest') {
    cam.yaw += (-input.moveX) * dt * 1.4 * -1 + (input.locked ? -input.lookDX * 0.003 : 0);
    if (input.moveY) { p.pos.x += Math.sin(cam.yaw) * input.moveY * dt * 4.5; p.pos.z += Math.cos(cam.yaw) * input.moveY * dt * 4.5; }
    if (fight.on && !input.moveX) cam.yaw += dt * 0.05;
  }
  p.yaw = cam.yaw;
  for (const k in p.skillCd) if (p.skillCd[k] > 0) p.skillCd[k] -= dt;
  for (const k in p.buffs) if (p.buffs[k].t > 0) p.buffs[k].t -= dt;
  for (const k in p.status) { const s = p.status[k]; if (s.t > 0) { s.t -= dt; if (STATUS[k].dps) p.hp = Math.max(1, p.hp - p.maxHp * STATUS[k].dps * dt); } else if (s.build > 0) s.build = Math.max(0, s.build - dt * 2.5); }
  if (d.stamina < p.st.maxSt) d.stamina = Math.min(p.st.maxSt, d.stamina + 30 * dt);
  if (d.mana < p.st.maxMana) d.mana = Math.min(p.st.maxMana, d.mana + 1.2 * dt);
  for (const e of g.enemies) {
    if (!e || !e.pos) continue;          // the smoke test pushes broken entries on purpose
    e.ph += dt;
    if (e.barT > 0) e.barT -= dt;
    if (e.vulnerableT > 0) e.vulnerableT -= dt;
    if (!e.dead && !e.boss) { e.pos.x += Math.sin(e.ph * 0.7 + e.hx) * dt * 0.6; e.pos.z += Math.cos(e.ph * 0.5 + e.hz) * dt * 0.5; }
  }
  // actions
  if (!p.dead && input.gameEnabled) {
    if (input.pressed('attack')) { const t = p.target || g.enemies.find((e) => e && e.pos && !e.dead); if (t) { d.stamina -= 14; hitEnemy(t, 32 + Math.random() * 14, Math.random() < 0.15); } }
    if (input.pressed('lock')) { p.target = p.target ? null : g.enemies.find((e) => e && e.pos && !e.dead) || null; bus.emit('lock', p.target); }
    if (input.pressed('flask') && d.flasks > 0 && p.hp < p.maxHp) { d.flasks--; p.heal(p.maxHp * 0.45); bus.emit('player:flask'); }
    for (let i = 0; i < 3; i++) if (input.pressed('skill' + (i + 1))) { const id = d.skillSlots[i], sk = id && SKILLS[id]; if (sk && !(p.skillCd[id] > 0) && d.mana >= sk.cost) { d.mana -= sk.cost; p.skillCd[id] = sk.cd; if (sk.buff) p.buff(sk.buff, sk.mult, sk.time); const t = p.target || g.enemies.find((e) => e && e.pos && !e.dead); if (t && sk.dmg) hitEnemy(t, sk.dmg, false); } else if (sk && d.mana < sk.cost) bus.emit('toast', { kind: 'text', text: 'Pas assez d\'Éclat.' }); }
    if (input.pressed('interact') && g.focus) { if (g.focus.kind === 'shrine') openShrine(false); else talk(); }
  }
  // interaction prompts near the home shrine
  const s = g._shrines[d.lastShrine];
  const near = s && Math.hypot(s.x + 14 - p.pos.x, s.z + 22 - p.pos.z) < 3;
  const wantFocus = fight.on ? (Math.floor(fight.t / 9) % 3 === 2) : near;
  if (wantFocus && !g.focus) g.focus = { label: 'Se reposer à l\'Autel', key: input.actionLabel('interact'), kind: 'shrine' };
  else if (!wantFocus && g.focus && !g.focus.manual) g.focus = null;
  // scripted skirmish
  if (fight.on && !p.dead && p.state !== 'rest') {
    const before = Math.floor(fight.t / 1.1); fight.t += dt; const now = Math.floor(fight.t / 1.1);
    if (now !== before) {
      const alive = g.enemies.filter((e) => e && e.pos && !e.dead);
      if (alive.length) { const t = g.boss && !g.boss.dead ? g.boss : alive[now % alive.length]; hitEnemy(t, 26 + Math.random() * 30, now % 7 === 0); d.stamina = Math.max(-5, d.stamina - 26); d.mana = Math.min(p.st.maxMana, d.mana + 4); if (now % 5 === 0) t.vulnerableT = 2; }
      if (now % 4 === 1) hurt(18 + Math.random() * 22, now % 8 === 1 ? 'poison' : null);
      if (now % 9 === 0) { p.target = alive[0] || null; bus.emit('lock', p.target); }
      if (now % 13 === 6 && d.skillSlots[0]) { const id = d.skillSlots[0]; p.skillCd[id] = SKILLS[id].cd * 4; d.mana = Math.max(0, d.mana - SKILLS[id].cost); }
      if (now % 17 === 9 && d.skillSlots[1]) { const id = d.skillSlots[1]; p.skillCd[id] = SKILLS[id].cd; p.buff('fury', 1.25, 14); }
      if (p.hp < p.maxHp * 0.35 && d.flasks > 0) { d.flasks--; p.heal(p.maxHp * 0.5); bus.emit('player:flask'); }
      if (g.boss && g.boss.hp < g.boss.maxHp * 0.5 && g.boss.phase === 1) { g.boss.phase = 2; bus.emit('boss:phase', { boss: g.boss, text: 'Mes filles… festoyez.' }); }
    }
    fight.danger = true;
  } else fight.danger = false;
}

// ---------------------------------------------------------------------------------------- backdrop
function resize() { const r = Math.min(devicePixelRatio || 1, 1.5); canvas.width = Math.round(innerWidth * r); canvas.height = Math.round(innerHeight * r); ctx.setTransform(r, 0, 0, r, 0, 0); }
addEventListener('resize', resize); resize();
let clock = 0;
function ridge(yaw, k, base, amp, color, seed) {
  const W = innerWidth, H = innerHeight;
  ctx.beginPath(); ctx.moveTo(0, H);
  for (let x = 0; x <= W; x += 8) { const a = (x / W - 0.5) * 1.9 - yaw * k + seed; ctx.lineTo(x, base + Math.sin(a * 2.1) * amp + Math.sin(a * 5.3 + 1) * amp * 0.45 + Math.sin(a * 11.7 + 2) * amp * 0.18); }
  ctx.lineTo(W, H); ctx.closePath(); ctx.fillStyle = color; ctx.fill();
}
function figure(x, y, h, w, color, rim) {
  ctx.save(); ctx.translate(x, y);
  ctx.fillStyle = color; ctx.strokeStyle = rim; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.ellipse(0, -h * 0.9, h * 0.085 * (0.6 + w), h * 0.1, 0, 0, 7); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-h * 0.17 * w * 2, -h * 0.76); ctx.quadraticCurveTo(0, -h * 0.84, h * 0.17 * w * 2, -h * 0.76); ctx.lineTo(h * 0.13 * w * 2, -h * 0.02); ctx.lineTo(-h * 0.13 * w * 2, -h * 0.02); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.restore();
}
function draw(dt) {
  clock += dt;
  const W = innerWidth, H = innerHeight, g = app.game;
  const yaw = app.state === 'playing' ? cam.yaw : clock * 0.03;
  const sky = ctx.createLinearGradient(0, 0, 0, H * 0.62);
  sky.addColorStop(0, '#141a26'); sky.addColorStop(0.55, '#3b3642'); sky.addColorStop(0.85, '#8a5f45'); sky.addColorStop(1, '#c08a55');
  ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
  const sx = ((((0.9 - yaw) / 1.9 + 0.5) % 3.3) + 3.3) % 3.3 * W - W * 0.5;
  const glow = ctx.createRadialGradient(sx, H * 0.5, 0, sx, H * 0.5, H * 0.5); glow.addColorStop(0, 'rgba(255,214,150,.75)'); glow.addColorStop(0.12, 'rgba(255,170,90,.35)'); glow.addColorStop(1, 'rgba(255,150,80,0)');
  ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
  ridge(yaw, 0.55, H * 0.5, H * 0.07, '#3a3740', 0.3); ridge(yaw, 0.8, H * 0.55, H * 0.05, '#2a2a2e', 2.1); ridge(yaw, 1.15, H * 0.6, H * 0.035, '#1c1e1c', 4.4);
  const gr = ctx.createLinearGradient(0, H * 0.6, 0, H); gr.addColorStop(0, '#22251c'); gr.addColorStop(0.3, '#1a1d15'); gr.addColorStop(1, '#0c0d0a');
  ctx.fillStyle = gr; ctx.fillRect(0, H * 0.62, W, H * 0.38);
  const fog = ctx.createLinearGradient(0, H * 0.5, 0, H * 0.72); fog.addColorStop(0, 'rgba(150,120,95,0)'); fog.addColorStop(0.5, 'rgba(150,120,95,.22)'); fog.addColorStop(1, 'rgba(150,120,95,0)');
  ctx.fillStyle = fog; ctx.fillRect(0, H * 0.5, W, H * 0.22);
  if (app.state === 'playing' && g) {
    const out = {}, list = g.enemies.filter((e) => e && e.pos).sort((a, b) => g.toScreen(b.pos, out).depth - g.toScreen(a.pos, out).depth);
    for (const e of list) {
      if (e.dead) continue;
      g.toScreen(e.pos, out); if (!out.visible) continue;
      const top = { ...out }; g.toScreen({ x: e.pos.x, y: e.pos.y + e.height, z: e.pos.z }, top);
      figure(out.x, out.y, out.y - top.y, e.w, e.boss ? '#1a0f14' : '#15130f', e.vulnerableT > 0 ? '#d2b06a' : 'rgba(190,150,110,.35)');
    }
    const p = g.player; g.toScreen(p.pos, out); const top = {}; g.toScreen({ x: p.pos.x, y: p.pos.y + 1.8, z: p.pos.z }, top);
    if (!p.dead) figure(out.x, out.y, out.y - top.y, 0.5, '#0f0e0c', 'rgba(230,200,150,.4)');
  } else if (app.state === 'creator' && app.creator) {
    const a = app.creator.appearance, face = look.view === 'face';
    look.zoom += ((face ? 1 : 0) - look.zoom) * Math.min(1, dt * 6);
    const z = look.zoom, cx = (30.6 * 16 + W - 22 * 16) / 2 * (W / 1280) + (1 - W / 1280) * W * 0.5, h = H * (0.62 + z * 1.5), y = H * 0.86 + z * H * 1.22;
    const wide = 0.5 + ((a.morphs.shoulder_width || 0) + (a.morphs.muscular || 0) + (a.morphs.heavy || 0)) * 0.12, turn = 0.55 + 0.45 * Math.abs(Math.cos(look.yaw));
    figure(cx, y, h * (a.height || 1), wide * turn, a.skin || '#c9a184', 'rgba(0,0,0,.6)');
    ctx.fillStyle = a.hairColor || '#333'; if (a.hair !== 'none') { ctx.beginPath(); ctx.ellipse(cx, y - h * (a.height || 1) * 0.955, h * 0.09 * (0.6 + wide * turn), h * 0.06, 0, Math.PI, 0); ctx.fill(); }
    ctx.fillStyle = a.eyeColor || '#345'; ctx.fillRect(cx - h * 0.035 * turn + Math.sin(look.yaw) * h * 0.03, y - h * (a.height || 1) * 0.905, h * 0.014, h * 0.008); ctx.fillRect(cx + h * 0.02 * turn + Math.sin(look.yaw) * h * 0.03, y - h * (a.height || 1) * 0.905, h * 0.014, h * 0.008);
  }
  const vg = ctx.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 0.95); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.6)');
  ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
}

// --------------------------------------------------------------------------------------------- boot
const ui = new UI(app);
applySettings(settings, app);
bus.on('settings', () => applySettings(settings, app));

function frame(dt) {
  input.update();
  simulate(dt);
  ui.update(dt);
  input.endFrame();
}
let last = performance.now();
function raf(now) {
  requestAnimationFrame(raf);
  const dt = Math.min((now - last) / 1000, 0.1); last = now;
  frame(dt); draw(dt);
}
requestAnimationFrame(raf);

const openers = {
  inventory: () => bus.emit('open', 'inventory'), character: () => bus.emit('open', 'character'), map: () => bus.emit('open', 'map'), journal: () => bus.emit('open', 'journal'),
  pause: () => ui.open('pause'), options: () => ui.open('options'), saves: () => ui.open('saves', { mode: app.state === 'playing' ? 'save' : 'load' }), credits: () => ui.open('credits'),
  shrine: () => openShrine(false), shop: openShop, smith: openSmith, dialogue: talk, death: () => { if (app.game) { app.game.player.hp = 0; die(); } },
  ending: () => bus.emit('ending', { id: params.get('ending') || Object.keys(ENDINGS)[0] }),
};
const mock = window.__mock = {
  app, ui, bus, log, fight, cam,
  go(state) { if (state === 'playing') { if (!app.game) startGame(veteranData()); else setState('playing'); } else if (state === 'creator') app.openCreator(); else if (state === 'title') app.quitToTitle(); else setState(state); },
  open(what) { if (app.state !== 'playing' && !['options', 'saves', 'credits'].includes(what)) this.go('playing'); (openers[what] || (() => {}))(); },
  hurt, hit(dmg = 40, crit = false) { const g = app.game; if (g) hitEnemy(g.enemies.find((e) => e && e.pos && !e.dead), dmg, crit); },
  boss: startBoss, kill() { const g = app.game; if (g && g.boss) hitEnemy(g.boss, 1e6, true); },
  toast: (o) => bus.emit('toast', o), discover: (name = REGIONS.forest.name, sub = REGIONS.forest.desc) => bus.emit('discover', { name, sub }), banner: (o) => bus.emit('banner', o || { title: 'AUTEL EMBRASÉ', sub: 'Autel de la Croisée', kind: 'shrine' }),
  rest: openShrine, shop: openShop, smith: openSmith, talk, die, ending: (id = 'reforge') => bus.emit('ending', { id }),
  status(name = 'poison', active = true) { const g = app.game; if (g) g.player.status[name] = active ? { t: STATUS[name].time || 6, build: 0 } : { t: 0, build: 18 }; },
  buff(name = 'sharp', t = 60) { const g = app.game; if (g) g.player.buff(name, 1.2, t); },
  levelUp() { const g = app.game; if (g) g.player.addXp(xpForLevel(g.player.data.level)); },
  subtitle: (text = 'Les cloches du Vieux-Gué sonnent encore sous la vase, certains soirs.', time = 6) => bus.emit('subtitle', { text, time }),
  /** advance the simulation without waiting for requestAnimationFrame (background tabs) */
  tick(seconds = 1, step = 1 / 60) { for (let t = 0; t < seconds; t += step) frame(step); draw(step); return app.state; },
  toasts() { for (const o of [{ kind: 'item', id: 'steel_sword', qty: 1 }, { kind: 'item', id: 'wolf_pelt', qty: 3 }, { kind: 'gold', n: 35 }, { kind: 'xp', n: 120 }, { kind: 'quest', title: 'La bête des lisières', done: true }, { kind: 'text', text: 'Codex : Forêt de Sombreronce' }]) bus.emit('toast', o); },
};

// ---- debug toolbar
const bar = document.getElementById('mockbar');
if (bar) {
  const btn = (label, fn) => { const b = document.createElement('button'); b.textContent = label; b.addEventListener('click', (e) => { e.stopPropagation(); fn(); b.blur(); }); bar.appendChild(b); };
  btn('Boot', () => { setState('boot'); let p = 0; const iv = setInterval(() => { p += 0.07; ui.setLoading(p, ['Relief et rivières', 'Personnages et créatures', 'Villages et ruines', 'Mise en place'][Math.min(3, Math.floor(p * 4))]); if (p >= 1) { clearInterval(iv); setState('title'); } }, 140); });
  btn('Titre', () => mock.go('title')); btn('Créateur', () => mock.go('creator')); btn('Jeu', () => mock.go('playing'));
  for (const k of ['inventory', 'character', 'map', 'journal', 'pause', 'options', 'shrine', 'shop', 'smith', 'dialogue', 'death', 'ending']) btn(k, () => mock.open(k));
  btn('boss', startBoss); btn('tuer boss', () => mock.kill()); btn('coup reçu', () => hurt(60)); btn('toasts', () => mock.toasts()); btn('zone', () => mock.discover()); btn('bannière', () => mock.banner());
  btn('poison', () => mock.status('poison')); btn('niveau', () => mock.levelUp()); btn('sous-titre', () => mock.subtitle()); btn('combat on/off', () => { fight.on = !fight.on; });
  const lg = document.createElement('pre'); lg.id = 'mocklog'; bar.appendChild(lg);
  const show = (v) => { bar.style.display = v ? 'flex' : 'none'; };
  show(params.get('bar') === '1');
  addEventListener('keydown', (e) => { if (e.code === 'Backquote' || e.code === 'IntlBackslash') show(bar.style.display === 'none'); });
}

// ---- initial state from the URL
const st0 = params.get('state') || 'title';
if (st0 === 'boot') { ui.setLoading(Number(params.get('p') || 0.42), 'Personnages et créatures'); }
else mock.go(st0);
if (params.has('open')) { const what = params.get('open'); setTimeout(() => mock.open(what), 60); }
if (params.get('boss') === '1') setTimeout(startBoss, 120);
if (params.has('hp') && app.game) app.game.player.hp = app.game.player.maxHp * Number(params.get('hp'));

/** screenshot helper: magnify the page around (x, y) — __zoom(0, 0, 1) resets */
window.__zoom = (x = 0, y = 0, s = 1) => {
  for (const id of ['ui', 'game']) { const el = document.getElementById(id); el.style.transformOrigin = x + 'px ' + y + 'px'; el.style.transform = s && s !== 1 ? 'scale(' + s + ')' : ''; }
  return 'zoom ' + s;
};

/** screenshot helper for background tabs: creates paint damage so that the next captured frame is fresh */
window.__poke = () => {
  let el = document.getElementById('poke');
  if (!el) { el = document.createElement('div'); el.id = 'poke'; el.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;z-index:999;pointer-events:none'; document.body.appendChild(el); }
  window.__pokeN = (window.__pokeN || 0) + 1;
  el.style.background = window.__pokeN % 2 ? '#0a0908' : '#0b0a09';
  return window.__pokeN;
};

/**
 * Automated smoke test: walks through every screen and the main flows, returns the errors logged meanwhile.
 * Usage (console): await __mock.smoke()
 */
mock.smoke = async () => {
  const errors = [];
  const orig = console.error;
  console.error = (...a) => { errors.push(a.map((x) => (x && x.stack) || String(x)).join(' ')); orig.apply(console, a); };
  const onErr = (e) => errors.push('window: ' + e.message);
  addEventListener('error', onErr);
  const steps = [];
  const step = (name, fn) => { try { fn(); mock.tick(0.25); steps.push(name); } catch (e) { errors.push(name + ': ' + (e.stack || e)); } };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const S = ui.screens;
  step('title', () => mock.go('title'));
  step('options', () => { ui.open('options'); for (const id of ['graphics', 'audio', 'controls', 'gameplay', 'access', 'keys']) S.options.setTab(id); });
  step('options widgets', () => { S.options.setTab('graphics'); for (const r of S.options.rows) { if (r.ctl.el._adjust) { r.ctl.el._adjust(1); r.ctl.el._adjust(-1); } } settings.resetCategory('graphics'); });
  step('saves load', () => { ui.close(); ui.open('saves', { mode: 'load' }); ui.close(); });
  step('credits', () => { ui.open('credits'); ui.close(); });
  step('creator', () => { mock.go('creator'); for (const b of Object.keys(S.creator.tabBtns)) S.creator.setTab(b); S.creator._random(); S.creator._preset({ a: { morphs: { age: 1 }, hair: 'none' } }); S.creator._pickOrigin('disciple'); S.creator._start(); });
  step('playing after creator', () => { if (app.state !== 'playing') throw new Error('creator did not start the game: ' + app.state); });
  step('veteran game', () => { app.quitToTitle(); app.continueGame(); mock.tick(3); });
  step('hud events', () => { mock.toasts(); mock.discover(); mock.banner(); mock.subtitle(); startBoss(); hurt(30, 'poison'); mock.status('burn', false); mock.buff('sharp', 20); mock.levelUp(); mock.tick(6); mock.kill(); mock.tick(6); });
  for (const tab of ['inventory', 'character', 'map', 'journal']) step('hub ' + tab, () => { ui.open('hub', { tab }); });
  step('inventory actions', () => { S.hub.setTab('inventory'); const inv = S.hub.pages.inventory; for (const f of ['weapon', 'shield', 'armor', 'consumable', 'material', 'key', 'all']) { inv.filter = f; inv.refresh(); } inv.sel = null; inv._select({ kind: 'inv', index: 0 }); inv._primary(); inv._select({ kind: 'eq', slot: 'weapon' }); inv._unequip('weapon'); inv._unequip('offhand'); inv.refresh(); });
  step('character actions', () => { S.hub.setTab('character'); const c = S.hub.pages.character; c._add('vigueur', 1); c._confirm(); c._assign(2, 'shadow_web'); c._assign(2, null); });
  step('map actions', () => { S.hub.setTab('map'); const m = S.hub.pages.map; m._zoomBy(1.3); m._zoomBy(0.5); m._centerOnPlayer(true); });
  step('journal actions', () => { S.hub.setTab('journal'); const j = S.hub.pages.journal; j.mode = 'quests'; j.refresh(); app.game.quests.track('bandits'); j.mode = 'codex'; j.refresh(); ui.closeAll(); });
  step('pause', () => { ui.back(); if (ui.top !== S.pause) throw new Error('pause did not open'); ui.open('options'); ui.back(); ui.open('saves', { mode: 'save' }); ui.closeAll(); });
  step('shrine', () => { openShrine(false); });
  await wait(260);
  step('shrine menu', () => { if (ui.top !== S.shrine) throw new Error('shrine did not open'); S.shrine._act('flaskCount', ''); S.shrine._act('flaskPower', ''); S.shrine._act('night', ''); ui.open('hub', { tab: 'map' }); ui.close(); S.shrine._leave(); });
  step('shop', () => { openShop(); S.shop._select({ side: 'buy', i: 0 }); S.shop._trade(); S.shop._select({ side: 'sell', i: 0 }); S.shop._trade(); ui.back(); if (app.game.shop) throw new Error('shop still open'); });
  step('smith', () => { openSmith(); S.smith._upgrade(); ui.back(); });
  step('dialogue', () => { talk(); mock.tick(6); S.dialogue._choose(2); mock.tick(6); S.dialogue._choose(1); mock.tick(6); S.dialogue._choose(3); if (app.game.dialogue) throw new Error('dialogue still open'); });
  step('dialogue to shop', () => { talk(); mock.tick(6); S.dialogue._choose(0); if (ui.top !== S.shop) throw new Error('shop did not replace the dialogue'); ui.back(); });
  step('death', () => { die(); mock.tick(1); if (!ui.death.on) throw new Error('death overlay missing'); if (ui.blocking) throw new Error('death must not block'); });
  await wait(4800);
  step('respawn', () => { if (ui.death.on) throw new Error('death overlay still shown'); });
  step('ending', () => { mock.ending('reforge'); mock.tick(2); S.ending._finish(); S.ending._quit(); if (app.state !== 'title') throw new Error('ending did not return to the title'); });
  step('null game', () => { app.game = null; ui.update(0.016); mock.go('playing'); app.game.enemies.push(null, { pos: null }, { hp: 1 }); app.game.player.data.inventory.push({ id: 'does_not_exist', qty: 1 }, null); app.game.player.data.equipment.head = { id: 'ghost_item' }; mock.tick(1); ui.open('hub', { tab: 'inventory' }); ui.closeAll(); app.game.player.data.inventory = app.game.player.data.inventory.filter(Boolean); });
  removeEventListener('error', onErr);
  console.error = orig;
  return { ok: errors.length === 0, steps: steps.length, errors };
};
