// Auto-travel toward the tracked objective ([G]): A* on a 4 m grid over the whole island, run a few
// milliseconds per frame. Cells are evaluated lazily (terrain + bridges height, river depth, static
// colliders); roads are cheaper so the route follows them like a traveller would. The player then
// steers along the path; any manual movement, a fight or a menu interrupts it.
import { bus } from '../core/events.js';

const HALF = 2520, C = 4, N = Math.ceil(HALF * 2 / C);      // 1260 x 1260 cells
const UP = 1.0, DOWN = 1.4;                                  // max climb / descent per metre (moveStep blocks above ~1.07 uphill)
const BUDGET_MS = 5, MAX_EXPAND = 700000;
const ARRIVE = 5, REPLAN_MOVE = 18;
const SQ2 = Math.SQRT2;
const DI = [1, -1, 0, 0, 1, 1, -1, -1], DJ = [0, 0, 1, -1, 1, -1, 1, -1];
const OFF = [0, 0, 1.3, 0, -1.3, 0, 0, 1.3, 0, -1.3, 1.3, 1.3, -1.3, 1.3, 1.3, -1.3, -1.3, -1.3];

export class AutoTravel {
  constructor(game) {
    this.game = game;
    this.cell = new Uint8Array(N * N);       // 0 unknown, 1 land, 2 water, 3 blocked
    this.h = new Float32Array(N * N);
    this.px = new Float32Array(N * N); this.pz = new Float32Array(N * N);   // walkable point of each cell
    this.road = new Uint8Array(N * N);
    this.g = new Float32Array(N * N);
    this.from = new Int32Array(N * N);
    this.stamp = new Uint32Array(N * N);
    this.closed = new Uint32Array(N * N);
    this.gen = 0;
    this.heap = new MinHeap();
    this.roadsReady = false;
    this.active = false;
    this.search = null;
    this.path = null; this.k = 0;
    this.goal = null;            // { x, z, name }
    this.moving = false;
    this.stuckT = 0; this.stuckRef = { x: 0, z: 0 }; this.stuckN = 0;
    this._probe = { x: 0, y: 0, z: 0 };
  }

  // ------------------------------------------------------------------ public
  toggle() { if (this.active) this.stop('manual'); else this.start(); }

  start() {
    const g = this.game, p = g.player;
    if (!p || p.dead) return false;
    if (g.boss) { this._say('Impossible pendant un combat de boss.'); g.sfx('ui_error'); return false; }
    const goal = this._target();
    if (!goal) { this._say('Aucun objectif suivi : choisissez une quête dans le journal.'); g.sfx('ui_error'); return false; }
    if (this._danger()) { this._say('Des ennemis sont trop proches.'); g.sfx('ui_error'); return false; }
    if (Math.hypot(goal.x - p.pos.x, goal.z - p.pos.z) < ARRIVE + 1) { this._say('Vous êtes déjà sur place.'); return false; }
    this.active = true; this.stuckN = 0;
    this.cell.fill(0);            // colliders and streamed trees may have changed since the last trip
    this._plan(goal);
    this._say('Déplacement automatique vers : ' + goal.name);
    g.sfx('ui_click');
    bus.emit('player:auto', true);
    return true;
  }

  stop(reason) {
    if (!this.active) return;
    this.active = false; this.search = null; this.path = null; this.moving = false;
    const msg = { arrived: 'Objectif atteint.', danger: 'Déplacement automatique interrompu : ennemi en vue.', blocked: 'Déplacement automatique interrompu : chemin bloqué.', nopath: 'Aucun chemin trouvé vers l\'objectif.', manual: 'Déplacement automatique arrêté.' }[reason];
    if (msg && reason !== 'silent') this._say(msg);
    bus.emit('player:auto', false);
  }

  /** world-space steering direction (Vector2: x, y = z) for this frame; zero while planning */
  dir(out) {
    out.set(0, 0);
    if (!this.active || !this.path) return out;
    const p = this.game.player, P = this.path;
    // advance along the path; skip ahead if a later point is already closer
    let best = this.k, bd = dist2(P[this.k], p.pos);
    for (let i = this.k + 1; i < Math.min(P.length, this.k + 8); i++) { const d = dist2(P[i], p.pos); if (d < bd) { bd = d; best = i; } }
    this.k = best;
    while (this.k < P.length - 1 && dist2(P[this.k], p.pos) < 1.6 * 1.6) this.k++;
    const q = P[this.k];
    const dx = q[0] - p.pos.x, dz = q[1] - p.pos.z, l = Math.hypot(dx, dz);
    if (l > 1e-3) out.set(dx / l, dz / l);
    this.moving = true;
    return out;
  }

  reset() { this.stop('silent'); }

  update(dt) {
    if (!this.active) return;
    const g = this.game, p = g.player;
    if (!p || p.dead || g.boss) { this.stop('silent'); return; }
    if (g.dialogue || g.shrine || g.shop || g.smith || p.state === 'rest') { this.stop('silent'); return; }
    if (this._danger()) { this.stop('danger'); return; }
    const goal = this._target();
    if (!goal) { this.stop('manual'); return; }
    if (Math.hypot(goal.x - p.pos.x, goal.z - p.pos.z) < ARRIVE) { this.stop('arrived'); return; }
    // objective moved (an NPC walking, next quest step) or the player was teleported
    if (this.goal && (Math.hypot(goal.x - this.goal.x, goal.z - this.goal.z) > REPLAN_MOVE || (this.path && dist2(this.path[Math.min(this.k, this.path.length - 1)], p.pos) > 40 * 40))) this._plan(goal);
    if (this.search) { this._step(); return; }
    if (!this.path) return;
    // end of a partial path (objective inside a building, path limit): stop near it
    if (this.k >= this.path.length - 1 && dist2(this.path[this.path.length - 1], p.pos) < 2.5 * 2.5) { this.stop(Math.hypot(goal.x - p.pos.x, goal.z - p.pos.z) < 30 ? 'arrived' : 'blocked'); return; }
    // stuck detection: replan, then give up
    this.stuckT += dt;
    if (this.stuckT > 1.6) {
      const moved = Math.hypot(p.pos.x - this.stuckRef.x, p.pos.z - this.stuckRef.z);
      this.stuckT = 0; this.stuckRef.x = p.pos.x; this.stuckRef.z = p.pos.z;
      if (moved < 1.2 && p.state === 'free' && g.input.gameEnabled) {
        if (++this.stuckN > 3) { this.stop('blocked'); return; }
        this._plan(goal, true);
      } else if (moved > 4) this.stuckN = 0;
    }
  }

  // ------------------------------------------------------------------ internals
  _say(text) { bus.emit('toast', { kind: 'text', text }); }

  _target() {
    const g = this.game;
    const ms = g.quests.markers();
    const m = ms.find(x => x.tracked) || null;
    return m ? { x: m.x, z: m.z, name: m.name } : null;
  }

  _danger() {
    const p = this.game.player;
    for (const e of this.game.enemies) if (!e.dead && e.aggro && e.distTo(p) < 30) return true;
    return false;
  }

  _plan(goal, avoidHere = false) {
    const p = this.game.player;
    if (!this.roadsReady) this._rasterRoads();
    this.goal = { ...goal };
    this.path = null; this.k = 0; this.moving = false;
    this.stuckT = 0; this.stuckRef.x = p.pos.x; this.stuckRef.z = p.pos.z;
    const s = idx(p.pos.x, p.pos.z), t = idx(goal.x, goal.z);
    if (++this.gen >= 0xffffffff) { this.gen = 1; this.stamp.fill(0); this.closed.fill(0); }
    const gen = this.gen;
    this.heap.clear();
    this.stamp[s] = gen; this.g[s] = 0; this.from[s] = -1;
    this.heap.push(s, this._hcost(s, t));
    const near = this._eval(t) === 3 ? 3 : 1;      // objective inside a building / rock: stop at its door
    this.search = { s, t, gx: goal.x, gz: goal.z, near, expanded: 0, best: s, bestH: this._hdist(s, t), avoid: avoidHere ? s : -1 };
    this._step();
  }

  _hdist(a, t) { const ai = a % N, aj = (a / N) | 0, ti = t % N, tj = (t / N) | 0; const dx = Math.abs(ai - ti), dz = Math.abs(aj - tj); return (Math.max(dx, dz) + (SQ2 - 1) * Math.min(dx, dz)) * C; }
  _hcost(a, t) { return this._hdist(a, t) * 0.95; }      // a bit greedy: near-optimal routes, far fewer cells explored

  _step() {
    const S = this.search, H = this.heap, gen = this.gen, t0 = performance.now();
    const G = this.g, F = this.from, ST = this.stamp, CL = this.closed;
    const ti = S.t % N, tj = (S.t / N) | 0;
    let n = 0;
    while (H.size) {
      if ((++n & 255) === 0 && performance.now() - t0 > BUDGET_MS) return;
      const a = H.pop();
      if (CL[a] === gen) continue;
      CL[a] = gen;
      const ai = a % N, aj = (a / N) | 0;
      const hd = this._hdist(a, S.t);
      if (hd < S.bestH) { S.bestH = hd; S.best = a; }
      if (Math.abs(ai - ti) <= S.near && Math.abs(aj - tj) <= S.near) { this._finish(a); return; }
      if (++S.expanded > MAX_EXPAND) break;
      const ga = G[a];
      const ha = this._height(a);
      for (let k = 0; k < 8; k++) {
        const bi = ai + DI[k], bj = aj + DJ[k];
        if (bi < 0 || bj < 0 || bi >= N || bj >= N) continue;
        const b = bj * N + bi;
        if (CL[b] === gen) continue;
        const cb = this._eval(b);
        if (k >= 4 && (this._eval(aj * N + bi) === 3 || this._eval(bj * N + ai) === 3)) continue;   // no corner cutting
        if (cb === 3) continue;
        // step between the two cells' walkable points: slope on both halves, colliders along the segment
        const ax = this.px[a], az = this.pz[a], bx = this.px[b], bz = this.pz[b];
        const d = Math.hypot(bx - ax, bz - az) || 0.5;
        const hb = this.h[b];
        const mx = (ax + bx) * 0.5, mz = (az + bz) * 0.5;
        const hm = this.game.collision.ground(mx, mz);
        const s1 = (hm - ha) / (d * 0.5), s2 = (hb - hm) / (d * 0.5);
        if (s1 > UP || s2 > UP || s1 < -DOWN || s2 < -DOWN) continue;
        if (this.game.collision.sweep(ax, ha + 0.9, az, bx, hb + 0.9, bz, 0.42, 6) < 1) continue;
        if (this._vegBlocked(mx, mz)) continue;
        let cost = d * (this.road[b] ? 0.6 : 1) * (1 + Math.abs(hb - ha) / d * 1.5);
        if (cb === 2) cost *= 12;
        if (b === S.avoid) cost += 40;
        const ng = ga + cost;
        if (ST[b] === gen && ng >= G[b]) continue;
        ST[b] = gen; G[b] = ng; F[b] = a;
        H.push(b, ng + this._hcost(b, S.t));
      }
    }
    // exhausted or over budget: go as close as we could if that is meaningful
    const p = this.game.player;
    const start = Math.hypot(S.gx - p.pos.x, S.gz - p.pos.z);
    if (S.best !== S.s && S.bestH < start - 20) this._finish(S.best);
    else { this.search = null; this.stop('nopath'); }
  }

  _finish(end) {
    const S = this.search, F = this.from, pts = [];
    for (let c = end; c !== -1; c = F[c]) pts.push(c);
    pts.reverse();
    // world points, dropping the ones on a straight line
    const out = [];
    for (let i = 0; i < pts.length; i++) {
      if (i > 0 && i < pts.length - 1) {
        const a = pts[i - 1], b = pts[i], c = pts[i + 1];
        if (b - a === c - b && this.px[b] === center(b)[0] && this.pz[b] === center(b)[1]) continue;
      }
      out.push([this.px[pts[i]], this.pz[pts[i]]]);
    }
    if (S.near === 1 && Math.hypot(out[out.length - 1][0] - S.gx, out[out.length - 1][1] - S.gz) < 8) out.push([S.gx, S.gz]);
    if (out.length > 1) out.shift();     // the start cell centre is behind / under the player
    this.path = out; this.k = 0; this.search = null;
  }

  _height(i) { this._eval(i); return this.h[i]; }

  /** 1 land, 2 water (swim), 3 blocked. The cell keeps the first free point of a 3x3 pattern (gates are narrower than a cell). */
  _eval(i) {
    const c = this.cell[i];
    if (c) return c;
    const [cx, cz] = center(i);
    const g = this.game;
    let r = 3;
    for (let k = 0; k < OFF.length; k += 2) {
      const x = cx + OFF[k], z = cz + OFF[k + 1];
      const gh = g.collision.ground(x, z);
      if (gh < -0.6) continue;                               // the sea
      if (this._blockedAt(x, gh, z)) continue;
      const wh = g.world.height(x, z);
      r = g.waterLevel(x, z) - gh > 0.95 || (wh < -0.2 && gh <= wh + 0.01) ? 2 : 1;   // river / shallows (bridges stand above)
      this.px[i] = x; this.pz[i] = z; this.h[i] = gh;
      break;
    }
    if (r === 3) { this.px[i] = cx; this.pz[i] = cz; this.h[i] = g.collision.ground(cx, cz); }
    this.cell[i] = r;
    return r;
  }

  _blockedAt(x, y, z) {
    const q = this._probe;
    q.x = x; q.y = y; q.z = z;
    if (this.game.collision.resolve(q, 0.45, 1.8)) return true;
    return this._vegBlocked(x, z);
  }

  _vegBlocked(x, z) {
    const v = this.game.vegetation, q = this._probe;
    if (!v || !v.resolve) return false;
    q.x = x; q.z = z;
    return v.resolve(q, 0.4);
  }

  _rasterRoads() {
    this.roadsReady = true;
    const roads = this.game.world.roads || [];
    for (const r of roads) {
      const pts = r.points || [], rad = (r.width || 4) * 0.5 + 1;
      for (let k = 0; k < pts.length - 1; k++) {
        const [ax, az] = pts[k], [bx, bz] = pts[k + 1], l = Math.hypot(bx - ax, bz - az), steps = Math.max(1, Math.ceil(l / 2));
        for (let s = 0; s <= steps; s++) {
          const x = ax + (bx - ax) * s / steps, z = az + (bz - az) * s / steps;
          const i0 = Math.floor((x - rad + HALF) / C), i1 = Math.floor((x + rad + HALF) / C), j0 = Math.floor((z - rad + HALF) / C), j1 = Math.floor((z + rad + HALF) / C);
          for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) if (i >= 0 && j >= 0 && i < N && j < N) this.road[j * N + i] = 1;
        }
      }
    }
  }
}

function idx(x, z) {
  let i = Math.floor((x + HALF) / C), j = Math.floor((z + HALF) / C);
  if (i < 0) i = 0; else if (i >= N) i = N - 1;
  if (j < 0) j = 0; else if (j >= N) j = N - 1;
  return j * N + i;
}
function center(i) { return [((i % N) + 0.5) * C - HALF, (((i / N) | 0) + 0.5) * C - HALF]; }
function dist2(q, p) { const dx = q[0] - p.x, dz = q[1] - p.z; return dx * dx + dz * dz; }

/** binary min-heap of (index, priority) */
class MinHeap {
  constructor() { this.ids = new Int32Array(1 << 16); this.pr = new Float32Array(1 << 16); this.size = 0; }
  clear() { this.size = 0; }
  push(id, p) {
    if (this.size >= this.ids.length) { const a = new Int32Array(this.ids.length * 2), b = new Float32Array(this.ids.length * 2); a.set(this.ids); b.set(this.pr); this.ids = a; this.pr = b; }
    const I = this.ids, P = this.pr;
    let i = this.size++;
    while (i > 0) { const pa = (i - 1) >> 1; if (P[pa] <= p) break; I[i] = I[pa]; P[i] = P[pa]; i = pa; }
    I[i] = id; P[i] = p;
  }
  pop() {
    const I = this.ids, P = this.pr, top = I[0], n = --this.size;
    if (n > 0) {
      const id = I[n], p = P[n];
      let i = 0;
      for (;;) {
        let c = 2 * i + 1;
        if (c >= n) break;
        if (c + 1 < n && P[c + 1] < P[c]) c++;
        if (P[c] >= p) break;
        I[i] = I[c]; P[i] = P[c]; i = c;
      }
      I[i] = id; P[i] = p;
    }
    return top;
  }
}
