// World content: settlements, citadel, boss arenas, shrines, bridges, steles, chests, fixed spawns.
// Everything is placed deterministically from world.json + the model manifests; missing models are skipped.
import * as THREE from 'three';
import { mulberry32 } from '../core/rng.js';
import { STELES } from './data/story.js';

const face = (x, z, tx, tz) => Math.atan2(tx - x, tz - z);          // yaw so that the model front (+Z) looks at (tx, tz)
const alongX = (dx, dz) => Math.atan2(-dz, dx);                      // yaw so that the model's local X runs along (dx, dz)

export async function buildContent(game) {
  const S = game.structures, w = game.world, rnd = mulberry32(4242);
  await S.loadManifests();
  const C = { named: {}, interact: [], spawns: [], shrines: {}, emitters: [], safe: [], gate: null, rot: {}, chests: [] };
  const jobs = [];
  const P = {};
  for (const p of w.pois) P[p.id] = p;
  const blocked = [];       // footprint circles [x, z, r]
  const free = (x, z, r) => blocked.every(b => Math.hypot(b[0] - x, b[1] - z) > b[2] + r);
  const R = (a, b) => a + rnd() * (b - a);
  const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
  const first = (...names) => names.find(n => S.has(n)) || null;
  const FOOT = { castle_wall: 4.5, castle_wall_ruin_a: 4.5, castle_wall_ruin_b: 4.5, castle_tower: 3.6, castle_tower_ruin: 3.6, castle_gate: 6, castle_keep: 11, castle_stairs: 4, floor_slab: 5, throne: 3.2, statue_knight: 1.4, statue_broken: 1.6, shrine: 3, lighthouse: 4, drowned_chapel: 9, ruin_house: 5, ruin_tower: 4, swamp_hut: 3.5, shipwreck: 7, crystal_giant: 3.5, crystal_cluster: 1.4, cave_mouth: 5, bramble_arch: 4, cult_altar: 2.5 };
  const foot = (name) => { const i = S.info(name); return i && i.footprint ? Math.max(i.footprint[0], i.footprint[1]) * 0.5 : (FOOT[name] || 1.5); };

  /** place a model (async); registers fire/smoke/glow emitters; returns a promise of the placement */
  const put = (name, x, z, yaw = 0, opts = {}) => {
    if (!name || !S.has(name)) return Promise.resolve(null);
    if (opts.block !== false) blocked.push([x, z, opts.blockR ?? foot(name)]);
    const job = S.place(name, x, z, yaw, opts).then((pl) => {
      if (!pl) return null;
      if (!opts.noFire) for (const f of pl.fires) C.emitters.push({ kind: name === 'forge' ? 'forge' : name.includes('lamp') || /candle/.test(Object.keys(pl.anchors).join()) ? 'torch' : 'fire', pos: f, scale: opts.fireScale || (name.includes('lamp') ? 0.45 : name === 'brazier_stone' || name === 'lighthouse' ? 1.5 : 0.9) });
      for (const s of pl.smokes) C.emitters.push({ kind: 'smoke', pos: s, scale: 1 });
      for (const gl of pl.glows) C.emitters.push({ kind: name.startsWith('crystal') ? 'crystal' : 'glow', pos: gl, scale: opts.glowScale || 1 });
      if (opts.as) C.named[opts.as] = pl;
      return pl;
    });
    jobs.push(job);
    return job;
  };

  // ------------------------------------------------------------------ roads helper
  const roadDirs = (poi, maxDist = 400) => {
    // unit directions of the roads leaving a POI
    const out = [];
    for (const r of w.roads) {
      const pts = r.points;
      for (const end of [0, pts.length - 1]) {
        if (Math.hypot(pts[end][0] - poi.x, pts[end][1] - poi.z) > 30) continue;
        const step = end === 0 ? 1 : -1;
        let k = end;
        while (pts[k + step] && Math.hypot(pts[k][0] - poi.x, pts[k][1] - poi.z) < Math.min(poi.r * 0.9, maxDist)) k += step;
        const dx = pts[k][0] - poi.x, dz = pts[k][1] - poi.z, l = Math.hypot(dx, dz) || 1;
        out.push({ x: dx / l, z: dz / l, id: r.id });
      }
    }
    return out;
  };

  const props = ['barrel', 'crate', 'sacks', 'woodpile', 'barrel', 'crate', 'bench', 'trough', 'haystack'];
  const dress = (x, z, yaw, radius, n = 3) => {
    for (let i = 0; i < n; i++) {
      const a = yaw + Math.PI + R(-1.3, 1.3), d = radius + R(0.4, 1.6);
      const px = x + Math.sin(a) * d, pz = z + Math.cos(a) * d;
      const name = pick(props);
      if (free(px, pz, 0.8)) put(name, px, pz, R(0, 6.28), { blockR: 0.9 });
    }
  };

  const palisadeRing = (cx, cz, radius, gates, arc = [0, Math.PI * 2]) => {
    // gates: [{ x, z (unit dir) }] ; segments of 4 m with gaps for 6 m gates
    if (!S.has('palisade')) return;
    const n = Math.round((arc[1] - arc[0]) * radius / 4);
    const gateAngles = gates.map(g => Math.atan2(g.x, g.z));
    for (const g of gates) {
      const gx = cx + g.x * radius, gz = cz + g.z * radius;
      put('palisade_gate', gx, gz, Math.atan2(g.x, g.z), { blockR: 4, sink: 0.1 });
      put('brazier', gx + g.z * 4.2 + g.x * 2.5, gz - g.x * 4.2 + g.z * 2.5, 0, { blockR: 0.6 });
      put('banner', gx - g.z * 4.2 + g.x * 2.5, gz + g.x * 4.2 + g.z * 2.5, Math.atan2(g.x, g.z), { blockR: 0.5 });
    }
    for (let i = 0; i < n; i++) {
      const a = arc[0] + (i + 0.5) / n * (arc[1] - arc[0]);
      if (gateAngles.some(ga => Math.abs(Math.atan2(Math.sin(a - ga), Math.cos(a - ga))) * radius < 5.2)) continue;
      const x = cx + Math.sin(a) * radius, z = cz + Math.cos(a) * radius;
      // segment runs along its local X = tangent of the circle
      put('palisade', x, z, alongX(Math.cos(a), -Math.sin(a)), { block: false, sink: 0.25 });
    }
  };

  const housesAlong = (poi, dirs, from, to, models, sideOff = 10.5, step = 15) => {
    for (const d of dirs) {
      for (let s = from; s <= to; s += step) {
        for (const side of [-1, 1]) {
          const name = pick(models);
          if (!S.has(name)) continue;
          const off = sideOff + R(0, 2.5) + foot(name) * 0.25;
          const x = poi.x + d.x * (s + R(-2, 2)) + d.z * off * side, z = poi.z + d.z * (s + R(-2, 2)) - d.x * off * side;
          const r = foot(name) + 1.2;
          if (!free(x, z, r) || w.slope(x, z) > 14) continue;
          const yaw = face(x, z, x - d.z * side, z + d.x * side) + R(-0.12, 0.12);
          put(name, x, z, yaw);
          dress(x, z, yaw, r * 0.75, 2 + Math.floor(rnd() * 3));
          if (rnd() < 0.3) put('lamp_post', x - d.z * side * (r + 0.5) + d.x * 4, z + d.x * side * (r + 0.5) + d.z * 4, 0, { blockR: 0.5 });
        }
      }
    }
  };

  // ------------------------------------------------------------------ shrines
  for (const s of w.shrines) {
    blocked.push([s.x, s.z, 5]);
    const model = first('shrine', 'campfire');
    const yaw = R(0, 6.28);
    const job = model ? S.place(model, s.x, s.z, yaw, { sink: 0.05 }) : Promise.resolve(null);
    jobs.push(job.then((pl) => {
      const fire = pl && pl.fires[0] ? pl.fires[0] : new THREE.Vector3(s.x, w.height(s.x, s.z) + 0.8, s.z);
      const rest = pl && pl.anchors.ANCHOR_rest ? pl.anchors.ANCHOR_rest : new THREE.Vector3(s.x + Math.sin(yaw) * 1.8, w.height(s.x, s.z), s.z + Math.cos(yaw) * 1.8);
      C.shrines[s.id] = { id: s.id, name: s.name, x: s.x, z: s.z, fire, rest, yaw };
    }));
  }

  // ------------------------------------------------------------------ Hautefeuille
  {
    const p = P.hautefeuille, c = p;
    C.safe.push([p.x, p.z, p.r + 40]);
    const dirs = roadDirs(p);
    blocked.push([c.x, c.z, 7]);
    for (const d of dirs) for (let s = 0; s < 100; s += 5) blocked.push([c.x + d.x * s, c.z + d.z * s, 3.6]);
    const fixed = [['tavern', -24, 26, 'tavern'], ['chapel', -40, -18, 'chapel'], ['forge', 28, 24, 'forge'], ['barn', 52, -40, 'barn'], ['windmill', -72, -50, 'windmill'], ['watchtower', 14, -70, 'tower']];
    for (const [name, dx, dz, as] of fixed) {
      const x = c.x + dx, z = c.z + dz;
      put(name, x, z, face(x, z, c.x, c.z), { as: 'hautefeuille.' + as });
      dress(x, z, face(x, z, c.x, c.z), foot(name) * 0.8, 3);
    }
    put('well', c.x + 5, c.z - 6, 0.4);
    put('notice_board', c.x - 8, c.z - 7, face(c.x - 8, c.z - 7, c.x, c.z));
    put('market_stall_a', c.x + 10, c.z + 8, face(c.x + 10, c.z + 8, c.x, c.z), { as: 'hautefeuille.stall' });
    put('market_stall_b', c.x - 7, c.z + 11, face(c.x - 7, c.z + 11, c.x, c.z));
    put('cart', c.x + 16, c.z + 1, 1.1);
    for (const [dx, dz] of [[7, -9], [-9, 6], [12, 4], [-4, -11]]) put('lamp_post', c.x + dx, c.z + dz, face(c.x + dx, c.z + dz, c.x, c.z), { blockR: 0.5 });
    housesAlong(p, dirs, 30, 78, ['house_a', 'house_b', 'house_c', 'house_d', 'house_a', 'house_b']);
    palisadeRing(c.x, c.z, 96, dirs);
    C.named['hautefeuille.gate'] = { anchors: { ANCHOR_npc: new THREE.Vector3(c.x + (dirs[0] ? dirs[0].x * 88 + dirs[0].z * 5 : 0), 0, c.z + (dirs[0] ? dirs[0].z * 88 - dirs[0].x * 5 : -88)) } };
    // fields outside the walls
    for (let i = 0; i < 9; i++) {
      const a = R(0, 6.28), d = R(112, 150), x = c.x + Math.sin(a) * d, z = c.z + Math.cos(a) * d;
      if (w.slope(x, z) > 10 || w.height(x, z) < 3 || !free(x, z, 3)) continue;
      put(pick(['haystack', 'haystack', 'scarecrow', 'cart']), x, z, R(0, 6.28));
      for (let k = 0; k < 4; k++) { const fa = a + 1.57, fx = x + Math.sin(fa) * (k * 3 - 4.5) + Math.sin(a) * 5, fz = z + Math.cos(fa) * (k * 3 - 4.5) + Math.cos(a) * 5; put(pick(['fence_wood', 'fence_wattle']), fx, fz, alongX(Math.sin(fa), Math.cos(fa)), { block: false }); }
    }
  }

  // ------------------------------------------------------------------ Port-Brisants
  {
    const p = P.port_brisants;
    C.safe.push([p.x, p.z, p.r + 40]);
    const dirs = roadDirs(p);
    // direction of the open sea = lowest ground around
    let sea = { x: 0, z: 1 }, low = 1e9;
    for (let a = 0; a < 6.28; a += 0.2) { const h = w.height(p.x + Math.sin(a) * 85, p.z + Math.cos(a) * 85) + w.height(p.x + Math.sin(a) * 50, p.z + Math.cos(a) * 50); if (h < low) { low = h; sea = { x: Math.sin(a), z: Math.cos(a) }; } }
    blocked.push([p.x, p.z, 6]);
    housesAlong(p, dirs.length ? dirs : [{ x: -sea.x, z: -sea.z }], 14, 58, ['house_a', 'house_c', 'house_a', 'house_d'], 9.5, 14);
    put('market_stall_b', p.x + sea.z * 9, p.z - sea.x * 9, face(p.x + sea.z * 9, p.z - sea.x * 9, p.x, p.z), { as: 'port_brisants.stall' });
    put('well', p.x - sea.z * 8, p.z + sea.x * 8, 0);
    // walk toward the sea until the shore, then build the pier
    let t = 10;
    while (t < 140 && w.height(p.x + sea.x * t, p.z + sea.z * t) > 0.75) t += 1.5;
    const sx = p.x + sea.x * t, sz = p.z + sea.z * t;
    for (let k = 0; k < 4; k++) put('dock', sx + sea.x * (3 + k * 6), sz + sea.z * (3 + k * 6), alongX(sea.x, sea.z), { y: 0.0, block: false });
    put('rowboat', sx + sea.x * 14 + sea.z * 3.4, sz + sea.z * 14 - sea.x * 3.4, alongX(sea.x, sea.z) + 0.3, { y: -0.12, block: false, collide: false });
    put('rowboat', sx + sea.x * 6 - sea.z * 5, sz + sea.z * 6 + sea.x * 5, 1.9, { block: false });
    put('shipwreck', sx - sea.z * 60 + sea.x * 6, sz + sea.x * 60 + sea.z * 6, R(0, 6.28), { sink: 0.5 });
    // lighthouse on the shore, off to one side
    const lx = sx + sea.z * 34 - sea.x * 6, lz = sz - sea.x * 34 - sea.z * 6;
    const lh = first('lighthouse', 'watchtower');
    put(lh, lx, lz, face(lx, lz, p.x, p.z), { as: 'port_brisants.lighthouse', noFire: true, sink: 0.4 }).then((pl) => {
      if (!pl) return;
      const top = pl.fires[0] || new THREE.Vector3(lx, w.height(lx, lz) + 9, lz);
      C.named.lighthouseTop = top;
      C.interact.push({ type: 'lighthouse', x: lx + Math.sin(pl.yaw) * 4.5, z: lz + Math.cos(pl.yaw) * 4.5, r: 3.2, label: 'Rallumer le phare', key: 'lighthouse', once: 'lighthouse_lit' });
    });
    for (let i = 0; i < 6; i++) { const a = R(0, 6.28), d = R(8, 40); const x = p.x + Math.sin(a) * d, z = p.z + Math.cos(a) * d; if (free(x, z, 1) && w.height(x, z) > 1.5) put(pick(['barrel', 'crate', 'sacks', 'cart', 'lamp_post']), x, z, R(0, 6.28), { blockR: 1 }); }
  }

  // ------------------------------------------------------------------ Roc-au-Vent
  {
    const p = P.roc_au_vent;
    C.safe.push([p.x, p.z, p.r + 35]);
    const dirs = roadDirs(p);
    blocked.push([p.x, p.z, 5]);
    for (const d of dirs) for (let s = 0; s < 70; s += 5) blocked.push([p.x + d.x * s, p.z + d.z * s, 3.2]);
    put('well', p.x + 4, p.z + 4, 0);
    put('market_stall_a', p.x - 9, p.z + 5, face(p.x - 9, p.z + 5, p.x, p.z), { as: 'roc_au_vent.stall' });
    put('watchtower', p.x + 22, p.z - 26, 0);
    put('forge', p.x + 20, p.z + 16, face(p.x + 20, p.z + 16, p.x, p.z));
    housesAlong(p, dirs, 16, 50, ['house_a', 'house_c', 'house_a'], 9.5, 14);
    palisadeRing(p.x, p.z, 56, dirs);
  }

  // ------------------------------------------------------------------ Refuge des Veilleurs
  {
    const p = P.refuge;
    C.safe.push([p.x, p.z, p.r + 30]);
    const dirs = roadDirs(p);
    blocked.push([p.x, p.z, 4]);
    put('campfire', p.x, p.z, 0);
    put('tent_b', p.x + 10, p.z - 8, face(p.x + 10, p.z - 8, p.x, p.z));
    for (const [dx, dz] of [[-9, -9], [-12, 3], [8, 11], [-3, 13]]) { put('tent_a', p.x + dx, p.z + dz, face(p.x + dx, p.z + dz, p.x, p.z)); put('bedroll', p.x + dx * 0.55, p.z + dz * 0.55, R(0, 6.28), { blockR: 0.6 }); }
    put('watchtower', p.x - 18, p.z - 16, 0);
    for (const [dx, dz] of [[3, -4], [-4, 4]]) put('bench', p.x + dx, p.z + dz, face(p.x + dx, p.z + dz, p.x, p.z), { blockR: 0.8 });
    for (let i = 0; i < 8; i++) { const a = R(0, 6.28), d = R(7, 22); const x = p.x + Math.sin(a) * d, z = p.z + Math.cos(a) * d; if (free(x, z, 1)) put(pick(['barrel', 'crate', 'sacks', 'woodpile', 'banner']), x, z, R(0, 6.28), { blockR: 1 }); }
    palisadeRing(p.x, p.z, 30, dirs.length ? [dirs[0]] : [{ x: 1, z: 0 }]);
  }

  // ------------------------------------------------------------------ Camp des Écorcheurs
  {
    const p = P.camp_ecorcheurs;
    const dirs = roadDirs(p);
    const g0 = dirs[0] || { x: 0, z: -1 };
    blocked.push([p.x, p.z, 3]);
    put('campfire', p.x, p.z, 0);
    put('tent_b', p.x - g0.x * 15, p.z - g0.z * 15, face(p.x - g0.x * 15, p.z - g0.z * 15, p.x, p.z));
    for (let i = 0; i < 5; i++) { const a = Math.atan2(g0.x, g0.z) + 1.0 + i * 0.95, x = p.x + Math.sin(a) * 15, z = p.z + Math.cos(a) * 15; if (free(x, z, 2.5)) put('tent_a', x, z, face(x, z, p.x, p.z)); }
    put('watchtower', p.x + g0.x * 18 + g0.z * 8, p.z + g0.z * 18 - g0.x * 8, 0);
    put('cage_hanging', p.x + g0.z * 8, p.z - g0.x * 8, R(0, 6.28));
    for (let i = 0; i < 10; i++) { const a = R(0, 6.28), d = R(4, 20); const x = p.x + Math.sin(a) * d, z = p.z + Math.cos(a) * d; if (free(x, z, 1)) put(pick(['barrel', 'crate', 'sacks', 'crate', 'skull_pike', 'bone_pile']), x, z, R(0, 6.28), { blockR: 1 }); }
    for (const s of [-1, 1]) put('barricade', p.x + g0.x * 34 + g0.z * 5 * s, p.z + g0.z * 34 - g0.x * 5 * s, alongX(g0.z, -g0.x), { blockR: 2 });
    palisadeRing(p.x, p.z, 26, [g0]);
    C.chests.push({ key: 'camp', x: p.x - g0.x * 11, z: p.z - g0.z * 11, yaw: face(p.x - g0.x * 11, p.z - g0.z * 11, p.x, p.z), tier: 1, ornate: false, loot: [['iron_sword', 1], ['steel_shard', 2], ['whetstone', 2]], gold: 140 });
    C.spawns.push({ key: 'camp_a', def: 'bandit', x: p.x + 6, z: p.z + 5, n: 3, r: 5 }, { key: 'camp_b', def: 'bandit_shield', x: p.x - 7, z: p.z + 4, n: 2, r: 4 },
      { key: 'camp_gate', def: 'bandit', x: p.x + g0.x * 30, z: p.z + g0.z * 30, n: 2, r: 3 },
      { key: 'garrick', def: 'bandit_brute', x: p.x - g0.x * 9, z: p.z - g0.z * 9, n: 1, r: 1, elite: { name: 'Garrick le Borgne', hp: 2.6, dmg: 1.25, xp: 5, flag: 'garrick_dead', loot: [['garrick_ring', 1], ['war_axe', 1]], gold: 220, scale: 1.2 } });
  }

  // ------------------------------------------------------------------ Vieux-Gué (drowned village)
  {
    const p = P.vieux_gue;
    for (let i = 0; i < 9; i++) {
      const a = i / 9 * 6.28 + R(-0.2, 0.2), d = R(16, 52), x = p.x + Math.sin(a) * d, z = p.z + Math.cos(a) * d;
      if (!free(x, z, 5)) continue;
      put(first(pick(['ruin_house', 'ruin_house', 'ruin_wall_a', 'ruin_wall_b', 'swamp_hut'])), x, z, R(0, 6.28), { sink: 0.35 });
    }
    put('ruin_tower', p.x + 4, p.z - 6, 0.3, { sink: 0.4 });
    put('sunken_boat', p.x + 30, p.z + 24, 1.2, { sink: 0.2 }); put('sunken_boat', p.x - 38, p.z - 10, 2.6, { sink: 0.3 });
    for (let i = 0; i < 12; i++) { const a = R(0, 6.28), d = R(8, 60), x = p.x + Math.sin(a) * d, z = p.z + Math.cos(a) * d; if (free(x, z, 1)) put(first(pick(['gravestone_a', 'gravestone_b', 'gravestone_c', 'grave_cross', 'bone_pile'])), x, z, R(0, 6.28), { blockR: 0.8, sink: 0.1 }); }
    C.chests.push({ key: 'gue', x: p.x + 2, z: p.z + 3, yaw: 0.5, tier: 2, loot: [['astral_fragment', 1], ['frost_salve', 3], ['amber_sap', 1]], gold: 260 });
    C.spawns.push({ key: 'gue_a', def: 'drowned', x: p.x + 14, z: p.z + 8, n: 4, r: 9 }, { key: 'gue_b', def: 'drowned', x: p.x - 16, z: p.z - 10, n: 4, r: 9 }, { key: 'gue_c', def: 'skeleton', x: p.x, z: p.z - 4, n: 3, r: 5 }, { key: 'gue_d', def: 'wraith', x: p.x - 4, z: p.z + 22, n: 1, r: 2 });
  }

  // ------------------------------------------------------------------ boss arenas
  const ring = (p, radius, n, names, opts = {}) => { for (let i = 0; i < n; i++) { const a = i / n * 6.28 + R(-0.15, 0.15), x = p.x + Math.sin(a) * radius * R(0.95, 1.08), z = p.z + Math.cos(a) * radius * R(0.95, 1.08); const nm = first(pick(names)); if (nm && (!opts.gap || Math.abs(Math.atan2(Math.sin(a - opts.gap), Math.cos(a - opts.gap))) > 0.45)) put(nm, x, z, opts.faceIn ? face(x, z, p.x, p.z) : R(0, 6.28), { sink: opts.sink ?? 0.4, block: false, ...(opts.o || {}) }); } };
  const entry = (p) => { const d = roadDirs(p)[0]; return d ? Math.atan2(d.x, d.z) : 0; };
  {
    const p = P.boss_wolf, e = entry(p);
    ring(p, p.r + 2, 9, ['standing_stone_a', 'standing_stone_b', 'standing_stone_c', 'rock'], { gap: e });
    put('cave_mouth', p.x - Math.sin(e) * (p.r + 6), p.z - Math.cos(e) * (p.r + 6), e, { sink: 0.6 });
    for (let i = 0; i < 7; i++) { const a = R(0, 6.28), d = R(8, p.r - 3); put(first('bone_pile', 'skull_pike'), p.x + Math.sin(a) * d, p.z + Math.cos(a) * d, R(0, 6.28), { block: false, collide: false }); }
  }
  {
    const p = P.boss_spider, e = entry(p);
    ring(p, p.r + 1, 14, ['spider_cocoon', 'egg_sacs', 'spider_cocoon'], { gap: e, sink: 0.1 });
    put('bramble_arch', p.x + Math.sin(e) * (p.r + 3), p.z + Math.cos(e) * (p.r + 3), e, { sink: 0.3 });
    put('cave_mouth', p.x - Math.sin(e) * (p.r + 7), p.z - Math.cos(e) * (p.r + 7), e, { sink: 0.6 });
    for (let i = 0; i < 8; i++) { const a = R(0, 6.28), d = R(10, p.r - 4); put(first('egg_sacs', 'bone_pile'), p.x + Math.sin(a) * d, p.z + Math.cos(a) * d, R(0, 6.28), { block: false, collide: false, sink: 0.05 }); }
    put('crystal_cluster', p.x - Math.sin(e) * (p.r - 4), p.z - Math.cos(e) * (p.r - 4), R(0, 6.28), { sink: 0.3 });
  }
  {
    const p = P.boss_knight, e = entry(p);
    put('drowned_chapel', p.x - Math.sin(e) * (p.r + 2), p.z - Math.cos(e) * (p.r + 2), e, { sink: 0.2 });
    ring(p, p.r + 1, 10, ['gravestone_a', 'grave_cross', 'pillar_broken', 'gravestone_c'], { gap: e, sink: 0.15 });
    for (const s of [-1, 1]) put(first('brazier_stone', 'brazier'), p.x + Math.sin(e) * (p.r - 2) + Math.cos(e) * 6 * s, p.z + Math.cos(e) * (p.r - 2) - Math.sin(e) * 6 * s, 0);
    put('crystal_cluster', p.x - Math.sin(e) * (p.r - 6), p.z - Math.cos(e) * (p.r - 6), R(0, 6.28), { sink: 0.3 });
  }
  {
    const p = P.boss_colossus, e = entry(p);
    ring(p, p.r + 2, 14, ['ice_spikes_a', 'ice_spikes_b', 'ice_spikes_a', 'frost_cairn'], { gap: e, sink: 0.4 });
    put('crystal_cluster', p.x - Math.sin(e) * (p.r - 6), p.z - Math.cos(e) * (p.r - 6), R(0, 6.28), { sink: 0.3 });
    C.iceLake = { x: p.x, z: p.z, y: p.y, r: p.r - 3 };
  }
  {
    const p = P.boss_priestess, e = entry(p);
    put('cult_altar', p.x - Math.sin(e) * (p.r - 6), p.z - Math.cos(e) * (p.r - 6), e);
    ring(p, p.r + 2, 12, ['obsidian_spire_a', 'obsidian_spire_b', 'obsidian_spire_a', 'cult_banner'], { gap: e, sink: 0.5 });
    for (let i = 0; i < 4; i++) { const a = e + 0.8 + i * 1.57, x = p.x + Math.sin(a) * (p.r - 5), z = p.z + Math.cos(a) * (p.r - 5); put(first('brazier_stone', 'brazier'), x, z, 0); }
    put('crystal_giant', p.x - Math.sin(e) * (p.r + 16), p.z - Math.cos(e) * (p.r + 16), R(0, 6.28), { sink: 0.8, glowScale: 2.5 });
  }

  // ------------------------------------------------------------------ citadel
  {
    const cx = 0, cz = -170, RR = 140, n = Math.round(2 * Math.PI * RR / 8);
    const gateA = 0;         // south (+Z)
    for (let i = 0; i < n; i++) {
      const a = (i + 0.5) / n * 6.283;
      const da = Math.abs(Math.atan2(Math.sin(a - gateA), Math.cos(a - gateA)));
      if (da * RR < 7.5) continue;
      const x = cx + Math.sin(a) * RR, z = cz + Math.cos(a) * RR;
      if (i % 11 === 5) { put(first(rnd() < 0.3 ? 'castle_tower_ruin' : 'castle_tower', 'castle_tower'), x, z, face(x, z, cx, cz), { sink: 0.6, block: false }); continue; }
      const nm = rnd() < 0.16 ? 'castle_wall_ruin_a' : 'castle_wall';
      put(first(nm, 'castle_wall'), x, z, alongX(Math.cos(a), -Math.sin(a)), { sink: 0.5, block: false });
    }
    const gx = cx, gz = cz + RR;
    put('castle_gate', gx, gz, Math.PI, { sink: 0.3, block: false });
    for (const s of [-1, 1]) put('castle_tower', gx + s * 9.5, gz + 0.5, 0, { sink: 0.6, block: false });
    C.gate = { x: gx, z: gz, yaw: 0, width: 4.2 };
    // avenue of statues from the gate to the throne court
    for (let k = 0; k < 6; k++) for (const s of [-1, 1]) {
      const x = s * 9, z = gz - 22 - k * 22;
      put(first((k + (s > 0 ? 1 : 0)) % 3 === 0 ? 'statue_broken' : 'statue_knight', 'pillar'), x, z, s > 0 ? -Math.PI / 2 : Math.PI / 2, { sink: 0.1 });
      put(first('brazier_stone', 'brazier'), s * 5.2, z + 11, 0);
    }
    const t = P.boss_king;
    // throne court: paved floor, colonnade, throne against the keep
    if (S.has('floor_slab')) for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) put('floor_slab', t.x + i * 8, t.z + j * 8, 0, { y: t.y - 0.22, block: false });
    for (let k = -2; k <= 2; k++) for (const s of [-1, 1]) put(first(rnd() < 0.3 ? 'pillar_broken' : 'pillar'), t.x + s * 22, t.z + k * 9, 0, { sink: 0.1 });
    put('throne', t.x, t.z - 24, 0, { as: 'throne' });
    put('castle_keep', t.x, t.z - 52, 0, { sink: 0.5 });
    for (const [dx, dz] of [[-16, -20], [16, -20], [-26, 6], [26, 6]]) put('crystal_cluster', t.x + dx, t.z + dz, R(0, 6.28), { sink: 0.3 });
    put('crystal_giant', t.x + 30, t.z - 36, 0.6, { sink: 1, glowScale: 2.5 });
    // ruined inner ward: quarters of collapsed houses, a graveyard, a broken inner wall round the throne court, shards
    const cc = P.citadel_court;
    for (const [x, z, r] of [[-18, cc.z + 10, 7], [20, cc.z - 20, 7], [0, t.z + t.r + 14, 7], [-60, cz, 9], [62, cz - 20, 9], [-70, cz + 30, 4]]) blocked.push([x, z, r]);   // fixed spawns and the chest stay clear
    const inWard = (x, z, r) => Math.hypot(x - cx, z - cz) < RR - 10 - r && Math.abs(x) > 15 + r && Math.hypot(x - t.x, z - t.z) > t.r + 16 + r;
    let quarters = 0;
    for (let i = 0; i < 80 && quarters < 14; i++) {
      const a = R(0, 6.28), d = R(30, RR - 20), qx = cx + Math.sin(a) * d, qz = cz + Math.cos(a) * d;
      if (!inWard(qx, qz, 8) || !free(qx, qz, 8)) continue;
      quarters++;
      const rot = R(0, 6.28);
      put(first(rnd() < 0.75 ? 'ruin_house' : 'ruin_tower', 'ruin_house'), qx, qz, rot, { sink: 0.3 });
      const wx = qx + Math.cos(rot) * 9, wz = qz - Math.sin(rot) * 9;
      if (free(wx, wz, 3)) put(first(pick(['ruin_wall_a', 'ruin_wall_b', 'arch_ruin'])), wx, wz, rot + R(-0.3, 0.3), { sink: 0.3 });
      for (let k = 0; k < 4; k++) {
        const b = R(0, 6.28), e = R(5.5, 10), px = qx + Math.sin(b) * e, pz = qz + Math.cos(b) * e;
        if (free(px, pz, 1)) put(pick(['bone_pile', 'crate', 'barrel', 'pillar_broken', 'crystal_small', 'sacks', 'statue_broken']), px, pz, R(0, 6.28), { blockR: 1.1, sink: 0.05 });
      }
    }
    // the graveyard of the knights of Aubeclair
    {
      const gx0 = -84, gz0 = cz - 50;
      put('sarcophagus', gx0, gz0, 0.2, { sink: 0.1 });
      for (let i = -3; i <= 3; i++) for (let j = -2; j <= 2; j++) {
        if (!i && !j) continue;
        const x = gx0 + i * 3.2 + R(-0.4, 0.4), z = gz0 + j * 3.6 + R(-0.4, 0.4);
        if (rnd() < 0.15 || !free(x, z, 0.6)) continue;
        put(pick(['gravestone_a', 'gravestone_b', 'gravestone_c', 'gravestone_a', 'grave_cross']), x, z, Math.PI + R(-0.25, 0.25), { blockR: 0.7, sink: 0.05 });
      }
    }
    // broken inner wall round the throne court, open toward the avenue (south)
    {
      const r2 = t.r + 12, m = Math.round(2 * Math.PI * r2 / 8);
      for (let i = 0; i < m; i++) {
        const a = (i + 0.5) / m * 6.283;
        if (Math.abs(Math.atan2(Math.sin(a), Math.cos(a))) < 0.42 || rnd() < 0.35) continue;    // the gap, and collapsed sections
        const x = t.x + Math.sin(a) * r2, z = t.z + Math.cos(a) * r2;
        if (Math.hypot(x - cx, z - cz) > RR - 9) continue;
        put(first(rnd() < 0.5 ? 'castle_wall_ruin_a' : 'castle_wall_ruin_b', 'ruin_wall_a'), x, z, alongX(Math.cos(a), -Math.sin(a)), { sink: 0.5, block: false });
      }
    }
    for (let i = 0; i < 18; i++) { const a = R(0, 6.28), d = R(20, RR - 15), x = cx + Math.sin(a) * d, z = cz + Math.cos(a) * d; if (Math.abs(x) > 6 && free(x, z, 1.2)) put(rnd() < 0.3 ? 'crystal_cluster' : 'crystal_small', x, z, R(0, 6.28), { sink: 0.2, blockR: 1.2 }); }
    C.spawns.push({ key: 'cit_a', def: 'hollow_knight', x: -18, z: cc.z + 10, n: 2, r: 5 }, { key: 'cit_b', def: 'hollow_knight', x: 20, z: cc.z - 20, n: 2, r: 5 }, { key: 'cit_c', def: 'hollow_greatsword', x: 0, z: t.z + t.r + 14, n: 2, r: 4 }, { key: 'cit_d', def: 'hollow_knight', x: -60, z: cz, n: 3, r: 8 }, { key: 'cit_e', def: 'hollow_greatsword', x: 62, z: cz - 20, n: 2, r: 8 });
    C.chests.push({ key: 'cit', x: -70, z: cz + 30, yaw: 1, tier: 4, ornate: true, loot: [['astral_fragment', 3], ['ember_seed', 1], ['plate_chest', 1]], gold: 900 });
  }

  // ------------------------------------------------------------------ bridges, steles, signposts, wild places
  for (const b of w.bridges) put(b.model, b.x, b.z, -b.angle, { y: b.y - 0.05, block: false });
  for (const [id, x, z] of STELES) {
    if (!free(x, z, 1.5)) continue;
    const yaw = R(0, 6.28);
    put(first('lore_stele', 'signpost'), x, z, yaw, { sink: 0.15, blockR: 1.2 });
    C.interact.push({ type: 'stele', x, z, r: 2.6, label: 'Lire la stèle', key: 'stele_' + id, codex: id });
  }
  for (const s of w.shrines) { const a = R(0, 6.28); put('signpost', s.x + Math.sin(a) * 7, s.z + Math.cos(a) * 7, R(0, 6.28), { blockR: 0.6 }); }
  // standing-stone circles and lone ruins in the wild, each with a chest
  const wild = [[-420, 1890, 1], [330, 1420, 1], [820, 2050, 1], [-1420, 1150, 2], [-2020, 320, 2], [-1380, -620, 2], [900, 980, 2], [1900, 900, 3], [1560, -420, 3], [-1100, -1500, 3], [300, -1150, 3], [-1700, -1900, 4], [650, -1900, 4], [2050, -1250, 4], [900, -800, 4], [-250, 2250, 1], [2150, 1500, 2]];
  wild.forEach(([x, z, tier], i) => {
    if (w.height(x, z) < 2 || w.slope(x, z) > 20) return;
    const kind = i % 3;
    if (kind === 0) ring({ x, z }, 7.5, 7, ['standing_stone_a', 'standing_stone_b', 'standing_stone_c'], { sink: 0.4 });
    else if (kind === 1) { put(first('ruin_tower', 'watchtower'), x + 5, z - 4, R(0, 6.28), { sink: 0.5 }); put(first('ruin_wall_a', 'stone_wall_low'), x - 5, z + 3, R(0, 6.28), { sink: 0.3 }); }
    else { put(first('dolmen', 'tent_a'), x + 4, z + 3, R(0, 6.28), { sink: 0.2 }); put('campfire', x - 1, z - 2, 0, { noFire: true }); put('bedroll', x - 3, z, 1); }
    C.chests.push({ key: 'wild' + i, x, z, yaw: R(0, 6.28), tier, ornate: tier >= 3 });
    if (rnd() < 0.5) put('crystal_small', x + R(-6, 6), z + R(-6, 6), R(0, 6.28), { sink: 0.1, blockR: 0.6 });
  });
  // crystals near the caldera and scattered over the ash lands
  for (let i = 0; i < 14; i++) { const a = R(0, 6.28), d = R(120, 420), x = 1520 + Math.sin(a) * d, z = -1480 + Math.cos(a) * d; if (w.height(x, z) > 3 && w.slope(x, z) < 30) put(pick(['crystal_small', 'crystal_cluster', 'obsidian_spire_a']), x, z, R(0, 6.28), { sink: 0.4, block: false }); }

  await Promise.all(jobs);
  // chests need their model placed after the await so that the lid object is available
  const chestJobs = C.chests.map((c) => {
    const model = first(c.ornate ? 'chest_ornate' : 'chest', 'chest', 'crate');
    if (!model) return null;
    return S.place(model, c.x, c.z, c.yaw, { sink: 0.02 }).then((pl) => { if (pl) { c.lid = pl.rot.ROT_lid || null; c.y = pl.pos.y; } });
  });
  await Promise.all(chestJobs);
  for (const c of C.chests) C.interact.push({ type: 'chest', x: c.x, z: c.z, r: 2.2, label: 'Ouvrir le coffre', key: 'chest_' + c.key, chest: c });
  C.stats = S.build();
  C.P = P;
  return C;
}
