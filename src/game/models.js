// Model factory: builds the visual (scene graph + animator) of every actor from the Blender-made assets.
// Every asset is optional: a missing file falls back to a simple stand-in so the game stays playable.
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';
import { loadGLB, loadJSON } from '../core/assets.js';
import { applyLibrary, getMaterial } from '../render/materials.js';
import { patchMaterial, inject } from '../core/globals.js';
import { Animator, prepareClips } from './animator.js';
import { HUMANOID_ANIMS, WOLF_ANIMS, SPIDER_ANIMS, mergeMeta } from './data/anims.js';
import { ITEMS } from './data/items.js';

const HUMAN_HIPS = 0.98;

function capsuleStandIn(height, radius, color) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(radius, Math.max(height - radius * 2, 0.1), 6, 12), new THREE.MeshStandardMaterial({ color, roughness: 0.8 }));
  patchMaterial(body.material);
  body.position.y = height / 2;
  body.castShadow = true; body.receiveShadow = true;
  const nose = new THREE.Mesh(new THREE.BoxGeometry(radius * 0.5, radius * 0.4, radius * 0.9), body.material);
  nose.position.set(0, height * 0.86, radius * 0.9);
  g.add(body, nose);
  return g;
}

export class ModelFactory {
  constructor() {
    this.ready = false;
    this.gearCache = new Map();
    this.human = null; this.humanManifest = null; this.hair = null; this.outfits = null;
    this.animSets = {};       // key -> { clips, meta }
    this.creatures = {};      // name -> gltf
    this.monsterInfo = {};
  }

  async load(progress = () => {}) {
    const base = 'assets/models/';
    const [anims, animMeta, human, humanMan, hair, outfits, outfitMan, wolf, wolfMeta, spider, spiderMeta, skeleton, troll, golem, monInfo, gearMan] = await Promise.all([
      loadGLB(base + 'char/humanoid_anims.glb'), loadJSON(base + 'char/humanoid_anims.json'),
      loadGLB(base + 'char/human.glb'), loadJSON(base + 'char/human_manifest.json'),
      loadGLB(base + 'char/hair.glb'), loadGLB(base + 'char/outfits.glb'), loadJSON(base + 'char/outfits_manifest.json'),
      loadGLB(base + 'creatures/wolf.glb'), loadJSON(base + 'creatures/wolf.json'),
      loadGLB(base + 'creatures/spider.glb'), loadJSON(base + 'creatures/spider.json'),
      loadGLB(base + 'creatures/skeleton.glb'), loadGLB(base + 'creatures/troll.glb'), loadGLB(base + 'creatures/golem.glb'),
      loadJSON(base + 'creatures/humanoid_monsters.json'), loadJSON(base + 'gear/manifest.json'),
    ]);
    progress(1);
    this.animGltf = anims;
    this.humanoidMeta = mergeMeta(HUMANOID_ANIMS, animMeta);
    this.humanoidClipsRaw = anims ? anims.animations : [];
    this.animSets.humanoid = { clips: prepareClips(this.humanoidClipsRaw), meta: this.humanoidMeta };
    this.human = human; this.humanManifest = humanMan; this.hair = hair; this.outfits = outfits; this.outfitManifest = outfitMan;
    this.creatures = { wolf, spider, skeleton, troll, golem };
    this.creatureMeta = { wolf: mergeMeta(WOLF_ANIMS, wolfMeta), spider: mergeMeta(SPIDER_ANIMS, spiderMeta) };
    this.creatureInfo = { wolf: wolfMeta, spider: spiderMeta };
    this.monsterInfo = monInfo || {};
    this.gearManifest = gearMan || {};
    for (const k of ['wolf', 'spider']) {
      const g = this.creatures[k];
      this.animSets[k] = { clips: g ? prepareClips(g.animations, { keepPositions: true }) : {}, meta: this.creatureMeta[k] };
    }
    this.ready = true;
  }

  /** clips rescaled for a humanoid whose hips are at another height */
  _humanoidSet(hipsHeight) {
    const ratio = Math.round(hipsHeight / HUMAN_HIPS * 100) / 100;
    if (Math.abs(ratio - 1) < 0.03) return this.animSets.humanoid;
    const key = 'humanoid@' + ratio;
    if (!this.animSets[key]) this.animSets[key] = { clips: prepareClips(this.humanoidClipsRaw, { hipsScale: ratio }), meta: this.humanoidMeta };
    return this.animSets[key];
  }

  _bones(root) {
    const bones = {};
    root.traverse((o) => { if (o.isBone) bones[o.name] = o; });
    return bones;
  }

  // ------------------------------------------------------------------ gear
  async gear(id) {
    if (!this.gearCache.has(id)) this.gearCache.set(id, loadGLB(`assets/models/gear/${id}.glb`).then((g) => { if (g) applyLibrary(g.scene); return g; }));
    return this.gearCache.get(id);
  }

  /** attach a weapon / shield model to a socket bone (async, replaces what was there) */
  attach(socket, modelId, fallbackColor = 0x9aa3ad) {
    if (!socket) return;
    for (let i = socket.children.length - 1; i >= 0; i--) if (socket.children[i].userData.gear) socket.remove(socket.children[i]);
    if (!modelId) return;
    const holder = new THREE.Group();
    holder.userData.gear = modelId;
    socket.add(holder);
    this.gear(modelId).then((g) => {
      if (!holder.parent) return;
      if (g) holder.add(g.scene.clone());
      else {
        // stand-in: blade along +Y (weapon convention) / disc facing +Z (shield convention)
        const isShield = modelId.startsWith('shield');
        const m = new THREE.MeshStandardMaterial({ color: fallbackColor, roughness: 0.5, metalness: isShield ? 0.2 : 0.8 });
        patchMaterial(m);
        const geo = isShield ? new THREE.CylinderGeometry(0.32, 0.32, 0.04, 16).rotateX(Math.PI / 2) : new THREE.BoxGeometry(0.05, 1.0, 0.012).translate(0, 0.42, 0);
        const mesh = new THREE.Mesh(geo, m);
        mesh.castShadow = true;
        holder.add(mesh);
      }
    });
    return holder;
  }

  gearInfo(modelId) { const m = this.gearManifest; return (m.weapons && m.weapons[modelId]) || (m.shields && m.shields[modelId]) || (m.items && m.items[modelId]) || null; }

  // ------------------------------------------------------------------ humanoids
  /**
   * look: { human, outfit, weapon, shield, skin, hair, hairColor, beard, morphs, scale, model, variant, ... }
   * returns { root, animator, bones, sockets, height, radius, setWeapon(itemId), setShield(itemId), tint(color) }
   */
  humanoid(look = {}) {
    const root = new THREE.Group();
    let inner = null, hips = HUMAN_HIPS, height = 1.8;
    const custom = look.model && this.creatures[look.model];
    if (look.model && custom) {
      inner = cloneSkinned(custom.scene);
      applyLibrary(inner, look.variant === 'ice' ? { variant: 'ice', custom: { M_ember: (o) => getMaterial('M_ice', { vertexColors: !!o.geometry.attributes.color }), M_rock: (o) => getMaterial('M_rock', { vertexColors: !!o.geometry.attributes.color, variant: 'ice', tint: new THREE.Color(0.62, 0.8, 1.0) }) } } : {});
      const info = this.monsterInfo[look.model] || (this.monsterInfo.monsters && this.monsterInfo.monsters[look.model]);
      if (info) { hips = info.hips_height || info.hipsHeight || (info.hips && info.hips[2]) || hips; height = info.height || height; }
    } else if (this.human && look.human) {
      inner = this._buildHuman(look);
    } else if (this.animGltf) {
      inner = cloneSkinned(this.animGltf.scene);       // animated mannequin stand-in
      const col = new THREE.Color(look.skin || (look.model ? '#7d8a6a' : '#b9a58c'));
      inner.traverse((o) => { if (o.isMesh) { o.material = new THREE.MeshStandardMaterial({ color: col, roughness: 0.75 }); patchMaterial(o.material); o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false; } });
      if (look.model === 'troll' || look.model === 'golem') height = 3.0;
    } else {
      inner = capsuleStandIn(1.8, 0.32, look.skin || 0xb9a58c);
    }
    const scale = (look.scale || 1) * (look.model && !custom && (look.model === 'troll' || look.model === 'golem') ? 1.65 : 1);
    inner.scale.setScalar(scale);
    root.add(inner);
    inner.traverse((o) => { if (o.isSkinnedMesh) o.frustumCulled = false; });
    const bones = this._bones(inner);
    const set = bones.hips ? this._humanoidSet(hips) : { clips: {}, meta: this.humanoidMeta };
    const animator = new Animator(bones.hips ? inner : null, set.clips, set.meta);
    const sockets = { weaponR: bones.weapon_R, weaponL: bones.weapon_L, shieldL: bones.shield_L, sheathBack: bones.sheath_back, sheathHip: bones.sheath_hip, head: bones.head, chest: bones.spine_03 };
    const self = this;
    const model = {
      root, inner, animator, bones, sockets, height: height * scale, scale,
      setWeapon(itemId) { const d = itemId && ITEMS[itemId]; self.attach(sockets.weaponR, d ? d.model : null); model.weaponId = itemId || null; },
      setShield(itemId) { const d = itemId && ITEMS[itemId]; self.attach(sockets.shieldL, d ? d.model : null, 0x7a6248); model.shieldId = itemId || null; },
      /** armor pieces: { head, chest, legs } -> item ids (humans only) */
      setOutfit(pieces, tint) { const h = inner.userData.human; if (h) h.setOutfit(pieces, tint); },
      human: inner.userData.human || null,
      dispose() { animator.dispose(); },
    };
    if (look.weapon) model.setWeapon(look.weapon);
    if (look.shield) model.setShield(look.shield);
    return model;
  }

  /** Human body + hair + outfit. Completed by game/character.js when the human kit is available. */
  _buildHuman(look) {
    if (this.buildHumanHook) return this.buildHumanHook(look, this);
    const inner = cloneSkinned(this.human.scene);
    applyLibrary(inner);
    return inner;
  }

  // ------------------------------------------------------------------ creatures
  creature(kind, look = {}) {
    const root = new THREE.Group();
    const gltf = this.creatures[kind];
    const scale = look.scale || 1;
    let inner, animator;
    const set = this.animSets[kind] || { clips: {}, meta: this.creatureMeta[kind] || {} };
    if (gltf) {
      inner = cloneSkinned(gltf.scene);
      let tint = null;
      if (look.tint) { tint = new THREE.Color(look.tint); tint.setRGB(Math.sqrt(tint.r), Math.sqrt(tint.g), Math.sqrt(tint.b)); }
      applyLibrary(inner, {
        variant: (look.tint || '') + (look.eyes || ''), tint,
        custom: look.eyes ? { M_eye_glow: (o) => { const m = getMaterial('M_eye_glow', { vertexColors: false, variant: 'glow' + look.eyes }); m.emissive.set(look.eyes); m.emissiveIntensity = 5; return m; } } : null,
      });
      inner.traverse((o) => { if (o.isSkinnedMesh) o.frustumCulled = false; });
      animator = new Animator(inner, set.clips, set.meta);
    } else {
      const dims = kind === 'wolf' ? [0.9, 0.34] : [0.8, 0.5];
      inner = capsuleStandIn(dims[0], dims[1], look.tint || 0x777777);
      inner.children[0].rotation.x = Math.PI / 2; inner.children[0].scale.set(1, 1.5, 1); inner.children[0].position.y = dims[0] * 0.6;
      animator = new Animator(null, {}, set.meta);
    }
    inner.scale.setScalar(scale);
    root.add(inner);
    const bones = this._bones(inner);
    const info = this.creatureInfo[kind];
    const headName = info && info.bones && info.bones.head;
    return { root, inner, animator, bones, sockets: { head: headName ? bones[headName] : null }, height: (kind === 'wolf' ? 1.0 : 0.9) * scale, scale, setWeapon() {}, setShield() {}, dispose() { animator.dispose(); } };
  }

  /** build the model for an enemy / boss definition */
  forDef(def) {
    const look = def.look || {};
    if (def.rig === 'wolf' || def.rig === 'spider') return this.creature(def.rig, look);
    return this.humanoid(look);
  }
}
