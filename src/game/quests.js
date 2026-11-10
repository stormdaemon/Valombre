// Quest runtime: state lives in player.data.quests = { [id]: { state: 'active'|'done', n (kill counter), tracked } }.
import { QUESTS } from './data/story.js';
import { bus } from '../core/events.js';

export class Quests {
  constructor(game) { this.game = game; this._stepCache = {}; }
  get data() { return this.game.player.data.quests; }

  state(id) { const q = this.data[id]; return q ? q.state : 'none'; }
  counter(id) { const q = this.data[id]; return q ? q.n || 0 : 0; }

  start(id) {
    if (this.data[id] || !QUESTS[id]) return;
    this.data[id] = { state: 'active', n: 0 };
    if (!this.tracked() || QUESTS[id].main) this.track(id);
    this.game.sfx('ui_quest');
    bus.emit('toast', { kind: 'quest', title: QUESTS[id].title, done: false });
    bus.emit('quest');
  }

  complete(id) {
    const q = this.data[id], def = QUESTS[id];
    if (!q || q.state === 'done' || !def) return;
    q.state = 'done';
    const r = def.reward || {}, p = this.game.player;
    if (r.gold) { p.data.gold += r.gold; bus.emit('toast', { kind: 'gold', n: r.gold }); }
    for (const [item, n] of r.items || []) p.addItem(item, n);
    if (r.xp) { p.addXp(r.xp); bus.emit('toast', { kind: 'xp', n: r.xp }); }
    this.game.sfx('ui_quest_done');
    bus.emit('toast', { kind: 'quest', title: def.title, done: true });
    if (q.tracked) { q.tracked = false; const next = Object.keys(this.data).find(k => this.data[k].state === 'active'); if (next) this.track(next); }
    bus.emit('quest');
  }

  tracked() { return Object.keys(this.data).find(k => this.data[k].tracked && this.data[k].state === 'active') || null; }
  track(id) { for (const k in this.data) this.data[k].tracked = k === id; bus.emit('quest'); }

  /** game events: ('kill', enemyDefId) | ('item', id) | ('flag', name) | ('shrine', id) */
  onEvent(type, arg) {
    for (const id in this.data) {
      const q = this.data[id], def = QUESTS[id];
      if (!def || q.state !== 'active') continue;
      if (type === 'kill' && def.countKill === arg) { q.n = (q.n || 0) + 1; bus.emit('quest'); }
    }
    this._check();
  }

  _check() {
    // notify when the current step of a quest advances
    for (const id in this.data) {
      const q = this.data[id], def = QUESTS[id];
      if (!def || q.state !== 'active') continue;
      const idx = this._firstOpen(id);
      if (this._stepCache[id] !== undefined && idx !== this._stepCache[id]) { bus.emit('quest'); if (idx >= 0) bus.emit('toast', { kind: 'text', text: 'Quête mise à jour : ' + def.title }); }
      this._stepCache[id] = idx;
      if (def.main && idx < 0 && this.game.flag('boss_king')) q.state = 'done';
    }
  }

  _firstOpen(id) {
    const q = this.data[id], def = QUESTS[id];
    for (let i = 0; i < def.steps.length; i++) if (!def.steps[i].done(this.game, q.state, q)) return i;
    return -1;
  }

  list() {
    const out = [];
    for (const id in this.data) {
      const q = this.data[id], def = QUESTS[id];
      if (!def) continue;
      out.push({ id, title: def.title, desc: def.desc, state: q.state, main: !!def.main, tracked: !!q.tracked && q.state === 'active',
        steps: def.steps.map(s => ({ text: s.text, done: q.state === 'done' || !!s.done(this.game, q.state, q) })) });
    }
    out.sort((a, b) => (b.main - a.main) || (a.state === 'done') - (b.state === 'done'));
    return out;
  }

  /** world positions the compass / map should point at */
  markers() {
    const out = [], g = this.game;
    for (const id in this.data) {
      const q = this.data[id], def = QUESTS[id];
      if (!def || q.state !== 'active') continue;
      let m = null;
      if (def.marker) m = def.marker(g);
      else {
        const idx = this._firstOpen(id);
        const last = idx === def.steps.length - 1 && def.steps.length > 1;
        if (last && def.npc) m = g.npcPos(def.npc);
        else if (def.poi) m = g.poiPos(def.poi);
        else if (def.npc) m = g.npcPos(def.npc);
      }
      if (m) out.push({ x: m.x, z: m.z, name: def.title, tracked: !!q.tracked });
    }
    return out;
  }
}
