// Fallback animation metadata (durations in seconds + gameplay events). The real values come from the
// .json files exported next to the animation .glb; these are used when a clip or file is missing.
const L = (duration, speed) => ({ duration, loop: true, speed, events: {} });
const O = (duration, events = {}) => ({ duration, loop: false, events });

export const HUMANOID_ANIMS = {
  idle: L(3.0), idle_combat: L(2.0), walk: L(1.0, 1.5), run: L(0.7, 4.6), sprint: L(0.5, 7.5),
  walk_back: L(1.0, 1.2), strafe_L: L(0.9, 2.0), strafe_R: L(0.9, 2.0),
  jump_start: O(0.25), jump_air: L(0.8), jump_land: O(0.35, { impact: 0.05 }),
  roll: O(0.75, { iframes: [0.05, 0.48], cancel: 0.62 }), backstep: O(0.45, { iframes: [0.03, 0.28], cancel: 0.4 }),
  atk1h_1: O(0.60, { hit: [0.20, 0.34], cancel: 0.40, whoosh: 0.18 }),
  atk1h_2: O(0.60, { hit: [0.20, 0.34], cancel: 0.40, whoosh: 0.18 }),
  atk1h_3: O(0.80, { hit: [0.30, 0.46], cancel: 0.62, whoosh: 0.28 }),
  atk1h_heavy: O(1.10, { hit: [0.56, 0.74], cancel: 0.92, whoosh: 0.54 }),
  atk1h_thrust: O(0.65, { hit: [0.24, 0.40], cancel: 0.50, whoosh: 0.22 }),
  block_idle: L(1.5), block_hit: O(0.35), parry: O(0.45, { hit: [0.06, 0.26] }), shield_bash: O(0.60, { hit: [0.22, 0.36], cancel: 0.48 }),
  idle_2h: L(2.4),
  atk2h_1: O(0.85, { hit: [0.34, 0.52], cancel: 0.62, whoosh: 0.32 }),
  atk2h_2: O(0.90, { hit: [0.36, 0.55], cancel: 0.66, whoosh: 0.34 }),
  atk2h_3: O(1.10, { hit: [0.50, 0.66], cancel: 0.86, whoosh: 0.48, impact: 0.6 }),
  atk2h_heavy: O(1.40, { hit: [0.50, 1.02], cancel: 1.2, whoosh: 0.48 }),
  hit_light: O(0.35), hit_heavy: O(0.70), knockdown: O(1.10, { impact: 0.5 }), getup: O(1.20),
  death: O(1.80, { impact: 1.1 }), death_back: O(1.60, { impact: 0.9 }),
  drink: O(1.40, { release: 0.75 }), interact: O(0.90, { release: 0.45 }), pickup: O(0.90, { release: 0.45 }),
  cast: O(0.80, { release: 0.40 }), cast_big: O(1.60, { release: 1.0 }), roar: O(1.60, { release: 0.6 }),
  kneel_down: O(0.80), kneel: L(2.5), kneel_up: O(0.80), talk: L(3.0), idle_npc: L(4.0), work_hammer: L(1.2),
  m_idle: L(2.5), m_walk: L(1.3, 1.2), m_run: L(0.75, 4.0),
  m_swipe_R: O(0.80, { hit: [0.30, 0.46], whoosh: 0.28 }), m_swipe_L: O(0.80, { hit: [0.30, 0.46], whoosh: 0.28 }),
  m_smash: O(1.30, { hit: [0.66, 0.80], impact: 0.70, whoosh: 0.6 }), m_stomp: O(1.00, { hit: [0.5, 0.6], impact: 0.52 }),
  m_roar: O(1.80, { release: 0.7 }), m_charge: L(0.6, 8.0),
};

export const WOLF_ANIMS = {
  idle: L(3.0), walk: L(1.0, 1.8), run: L(0.5, 6.5),
  bite: O(0.7, { hit: [0.24, 0.40] }), lunge: O(1.1, { hit: [0.40, 0.68] }), swipe: O(0.9, { hit: [0.34, 0.52] }),
  howl: O(2.4, { release: 0.9 }), hit: O(0.4), death: O(1.6, { impact: 0.8 }),
};

export const SPIDER_ANIMS = {
  idle: L(2.5), walk: L(0.8, 2.0), run: L(0.45, 5.0),
  bite: O(0.7, { hit: [0.28, 0.44] }), leap: O(1.2, { hit: [0.5, 0.78], impact: 0.8 }), spit: O(0.9, { release: 0.45 }),
  slam: O(1.3, { hit: [0.66, 0.82], impact: 0.7 }), rear_up: O(2.0, { release: 1.0 }), hit: O(0.4), death: O(1.6, { impact: 0.9 }),
};

/** map generic actor states to clip names per rig */
export const RIG_CLIPS = {
  humanoid: { idle: 'idle', walk: 'walk', run: 'run', hit: 'hit_light', stagger: 'hit_heavy', death: 'death' },
  humanoid_monster: { idle: 'm_idle', walk: 'm_walk', run: 'm_run', hit: 'hit_light', stagger: 'hit_heavy', death: 'death' },
  wolf: { idle: 'idle', walk: 'walk', run: 'run', hit: 'hit', stagger: 'hit', death: 'death' },
  spider: { idle: 'idle', walk: 'walk', run: 'run', hit: 'hit', stagger: 'hit', death: 'death' },
};

/** merge exported metadata (if any) over the fallback table */
export function mergeMeta(fallback, json) {
  const out = {};
  for (const k in fallback) out[k] = { ...fallback[k], events: { ...fallback[k].events } };
  if (json && json.clips) {
    for (const k in json.clips) {
      const c = json.clips[k];
      out[k] = { duration: c.duration ?? out[k]?.duration ?? 1, loop: c.loop ?? out[k]?.loop ?? false, speed: c.speed ?? out[k]?.speed, events: { ...(out[k]?.events || {}), ...(c.events || {}) } };
    }
  }
  return out;
}
