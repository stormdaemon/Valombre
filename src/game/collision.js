// Lightweight collision world: terrain heightfield + static boxes / cylinders in a spatial hash + walkable platforms.
const CELL = 16;
const key = (i, j) => (i + 4096) * 8192 + (j + 4096);

export class CollisionWorld {
  constructor(world) {
    this.world = world;
    this.grid = new Map();
    this.walk = new Map();
    this.count = 0;
  }

  _insert(grid, o, minx, minz, maxx, maxz) {
    const i0 = Math.floor(minx / CELL), i1 = Math.floor(maxx / CELL), j0 = Math.floor(minz / CELL), j1 = Math.floor(maxz / CELL);
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
      const k = key(i, j);
      let l = grid.get(k);
      if (!l) grid.set(k, l = []);
      l.push(o);
    }
    this.count++;
  }

  /** oriented box: center (x,z), half sizes (hx,hz), rotation around Y (rad), vertical span [y0,y1] */
  addBox(x, z, hx, hz, rot, y0, y1, tag = null) {
    const c = Math.cos(rot), s = Math.sin(rot);
    const ex = Math.abs(c) * hx + Math.abs(s) * hz, ez = Math.abs(s) * hx + Math.abs(c) * hz;
    const o = { t: 0, x, z, hx, hz, c, s, y0, y1, tag };
    this._insert(this.grid, o, x - ex, z - ez, x + ex, z + ez);
    return o;
  }

  addCylinder(x, z, r, y0, y1, tag = null) {
    const o = { t: 1, x, z, r, y0, y1, tag };
    this._insert(this.grid, o, x - r, z - r, x + r, z + r);
    return o;
  }

  /** walkable platform: box whose top (y1) can be stood on */
  addWalk(x, z, hx, hz, rot, y1) {
    const c = Math.cos(rot), s = Math.sin(rot);
    const ex = Math.abs(c) * hx + Math.abs(s) * hz, ez = Math.abs(s) * hx + Math.abs(c) * hz;
    const o = { x, z, hx, hz, c, s, y1 };
    this._insert(this.walk, o, x - ex, z - ez, x + ex, z + ez);
    return o;
  }

  /** Ground height for something standing near altitude y (platforms within reach count). */
  ground(x, z, y = 1e9) {
    let h = this.world.height(x, z);
    const l = this.walk.get(key(Math.floor(x / CELL), Math.floor(z / CELL)));
    if (l) {
      for (let n = 0; n < l.length; n++) {
        const o = l[n], dx = x - o.x, dz = z - o.z;
        const lx = dx * o.c + dz * o.s, lz = -dx * o.s + dz * o.c;
        if (Math.abs(lx) <= o.hx && Math.abs(lz) <= o.hz && o.y1 > h && o.y1 <= y + 0.55) h = o.y1;
      }
    }
    return h;
  }

  /**
   * Push a vertical cylinder (pos = feet, radius r, height hh) out of the static colliders. Mutates pos (x,z).
   * Returns true if something was hit.
   */
  resolve(pos, r, hh = 1.8) {
    let hit = false;
    const i0 = Math.floor((pos.x - r) / CELL), i1 = Math.floor((pos.x + r) / CELL), j0 = Math.floor((pos.z - r) / CELL), j1 = Math.floor((pos.z + r) / CELL);
    for (let pass = 0; pass < 2; pass++) {
      for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
        const l = this.grid.get(key(i, j));
        if (!l) continue;
        for (let n = 0; n < l.length; n++) {
          const o = l[n];
          if (pos.y + hh < o.y0 || pos.y + 0.35 > o.y1) continue;
          if (o.t === 1) {
            const dx = pos.x - o.x, dz = pos.z - o.z, d2 = dx * dx + dz * dz, rr = r + o.r;
            if (d2 < rr * rr) {
              const d = Math.sqrt(d2) || 1e-4, p = (rr - d) / d;
              pos.x += dx * p; pos.z += dz * p; hit = true;
            }
          } else {
            const dx = pos.x - o.x, dz = pos.z - o.z;
            const lx = dx * o.c + dz * o.s, lz = -dx * o.s + dz * o.c;
            const cx = Math.max(-o.hx, Math.min(o.hx, lx)), cz = Math.max(-o.hz, Math.min(o.hz, lz));
            let ox = lx - cx, oz = lz - cz;
            const d2 = ox * ox + oz * oz;
            if (d2 >= r * r) continue;
            if (d2 > 1e-8) {
              const d = Math.sqrt(d2), p = (r - d) / d;
              ox *= p; oz *= p;
            } else {
              // center inside the box: leave through the nearest face
              const px = o.hx - Math.abs(lx) + r, pz = o.hz - Math.abs(lz) + r;
              if (px < pz) { ox = lx < 0 ? -px : px; oz = 0; } else { oz = lz < 0 ? -pz : pz; ox = 0; }
            }
            pos.x += ox * o.c - oz * o.s; pos.z += ox * o.s + oz * o.c; hit = true;
          }
        }
      }
      if (!hit) break;
    }
    return hit;
  }

  /** true if the segment a->b (3D points) is blocked by terrain or a collider (sampled). Returns blocked fraction 0..1 (1 = clear). */
  sweep(ax, ay, az, bx, by, bz, radius = 0.25, steps = 10) {
    for (let s = 1; s <= steps; s++) {
      const t = s / steps;
      const x = ax + (bx - ax) * t, y = ay + (by - ay) * t, z = az + (bz - az) * t;
      if (y < this.world.height(x, z) + radius) return (s - 1) / steps;
      const l = this.grid.get(key(Math.floor(x / CELL), Math.floor(z / CELL)));
      if (!l) continue;
      for (let n = 0; n < l.length; n++) {
        const o = l[n];
        if (y < o.y0 - radius || y > o.y1 + radius) continue;
        if (o.t === 1) {
          const dx = x - o.x, dz = z - o.z;
          if (dx * dx + dz * dz < (o.r + radius) * (o.r + radius)) return (s - 1) / steps;
        } else {
          const dx = x - o.x, dz = z - o.z;
          const lx = dx * o.c + dz * o.s, lz = -dx * o.s + dz * o.c;
          if (Math.abs(lx) < o.hx + radius && Math.abs(lz) < o.hz + radius) return (s - 1) / steps;
        }
      }
    }
    return 1;
  }

  /** line of sight between two points at eye height */
  los(ax, ay, az, bx, by, bz) { return this.sweep(ax, ay, az, bx, by, bz, 0.1, 12) >= 1; }
}
