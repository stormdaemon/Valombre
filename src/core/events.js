// Tiny synchronous event bus.
export class Bus {
  constructor() { this.map = new Map(); }
  on(type, fn) { let l = this.map.get(type); if (!l) this.map.set(type, l = []); l.push(fn); return () => this.off(type, fn); }
  off(type, fn) { const l = this.map.get(type); if (l) { const i = l.indexOf(fn); if (i >= 0) l.splice(i, 1); } }
  emit(type, a, b, c) { const l = this.map.get(type); if (l) for (let i = 0; i < l.length; i++) l[i](a, b, c); }
}
export const bus = new Bus();
