// Save slots in localStorage. Slot 0 = autosave, 1..3 = manual.
const KEY = (n) => 'valombre.save.' + n;
export const SLOTS = 4;

export class Saves {
  constructor(app) { this.app = app; }

  _read(slot) {
    try { const raw = localStorage.getItem(KEY(slot)); return raw ? JSON.parse(raw) : null; } catch (e) { return null; }
  }

  list() {
    const out = [];
    for (let s = 0; s < SLOTS; s++) {
      const d = this._read(s);
      if (!d || !d.player) out.push({ slot: s, empty: true });
      else out.push({ slot: s, empty: false, name: d.player.name, level: d.player.level, region: d.region || '', playtime: d.player.stats.time || 0, date: d.date || 0, origin: d.player.origin });
    }
    return out;
  }

  latest() {
    let best = -1, t = -1;
    for (const s of this.list()) if (!s.empty && s.date > t) { t = s.date; best = s.slot; }
    return best;
  }

  load(slot) { const d = this._read(slot); return d && d.player ? d : null; }

  write(slot, payload) {
    try { localStorage.setItem(KEY(slot), JSON.stringify({ ...payload, date: Date.now(), version: 1 })); return true; } catch (e) { console.warn('save failed', e); return false; }
  }

  delete(slot) { try { localStorage.removeItem(KEY(slot)); } catch (e) { /* ignore */ } }
}
