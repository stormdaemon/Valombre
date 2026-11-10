// Settings: schema (drives the options menu), defaults, graphics presets, persistence.
import { bus } from './events.js';

const sel = (key, label, choices, def, desc) => ({ key, label, type: 'select', choices, def, desc });
const sld = (key, label, min, max, step, def, unit = '', desc) => ({ key, label, type: 'slider', min, max, step, def, unit, desc });
const tog = (key, label, def, desc) => ({ key, label, type: 'toggle', def, desc });
const Q4 = [['low', 'Bas'], ['medium', 'Moyen'], ['high', 'Élevé'], ['ultra', 'Ultra']];
const Q5 = [['off', 'Désactivé'], ...Q4];

export const SETTINGS_SCHEMA = [
  { id: 'graphics', label: 'Graphismes', options: [
    sel('preset', 'Préréglage', [['auto', 'Automatique'], ...Q4, ['custom', 'Personnalisé']], 'auto', 'Automatique mesure les performances de votre carte graphique au premier lancement.'),
    sld('renderScale', 'Échelle de rendu', 50, 100, 5, 100, '%', 'Résolution interne. Plus bas = plus rapide.'),
    tog('dynamicRes', 'Résolution dynamique', true, 'Ajuste automatiquement l\'échelle de rendu pour tenir la cadence cible.'),
    sel('targetFps', 'Cadence cible', [[30, '30 images/s'], [45, '45 images/s'], [60, '60 images/s']], 45),
    sel('antialias', 'Anticrénelage', [['off', 'Désactivé'], ['fxaa', 'FXAA'], ['msaa2', 'MSAA ×2 + FXAA'], ['msaa4', 'MSAA ×4 + FXAA']], 'fxaa'),
    sel('shadows', 'Ombres', Q5, 'high'),
    tog('terrainShadows', 'Ombres du relief', true, 'Ombres portées des montagnes et collines à grande distance.'),
    tog('cloudShadows', 'Ombres des nuages', true),
    sel('viewDistance', 'Distance d\'affichage', Q4, 'high'),
    sel('vegetation', 'Végétation', Q4, 'high', 'Distance et densité des arbres, buissons et rochers.'),
    sel('grass', 'Herbe', Q5, 'high'),
    sel('textures', 'Textures', [['low', 'Basse (512)'], ['high', 'Haute (1024)']], 'high', 'Appliqué au prochain lancement.'),
    sel('anisotropy', 'Filtrage anisotrope', [[1, '×1'], [2, '×2'], [4, '×4'], [8, '×8'], [16, '×16']], 4),
    sel('ao', 'Occlusion ambiante', [['off', 'Désactivée'], ['low', 'Normale'], ['high', 'Renforcée']], 'low'),
    sld('bloom', 'Halo lumineux (bloom)', 0, 100, 5, 55, '%'),
    tog('godrays', 'Rayons crépusculaires', true),
    sel('lights', 'Lumières dynamiques', [[0, 'Aucune'], [2, '2'], [4, '4']], 4, 'Torches, feux et sorts qui éclairent le décor.'),
    sel('particles', 'Particules', [['low', 'Peu'], ['medium', 'Normal'], ['high', 'Beaucoup']], 'high'),
    sld('sharpen', 'Netteté', 0, 100, 5, 30, '%'),
    sld('vignette', 'Vignettage', 0, 100, 5, 35, '%'),
    sld('grain', 'Grain de film', 0, 100, 5, 30, '%'),
    sld('chroma', 'Aberration chromatique', 0, 100, 5, 0, '%'),
    sld('fov', 'Champ de vision', 50, 90, 1, 62, '°'),
    sld('brightness', 'Luminosité', 70, 140, 2, 100, '%'),
    sld('contrast', 'Contraste', 80, 125, 1, 100, '%'),
    sld('saturation', 'Saturation', 60, 140, 2, 100, '%'),
    tog('showFps', 'Afficher les performances', false),
  ] },
  { id: 'audio', label: 'Son', options: [
    sld('volMaster', 'Volume général', 0, 100, 1, 80, '%'),
    sld('volMusic', 'Musique', 0, 100, 1, 65, '%'),
    sld('volSfx', 'Effets', 0, 100, 1, 85, '%'),
    sld('volAmbience', 'Ambiance', 0, 100, 1, 75, '%'),
    sld('volVoice', 'Voix', 0, 100, 1, 85, '%'),
    sld('volUi', 'Interface', 0, 100, 1, 70, '%'),
    tog('muteOnBlur', 'Couper le son hors de la fenêtre', true),
  ] },
  { id: 'controls', label: 'Commandes', options: [
    sld('mouseSens', 'Sensibilité de la souris', 10, 300, 5, 100, '%'),
    tog('invertY', 'Inverser l\'axe vertical', false),
    sld('camDistance', 'Distance de la caméra', 25, 60, 1, 38, '', 'En dixièmes de mètre.'),
    tog('camShoulder', 'Caméra décalée sur l\'épaule', true),
    tog('autoLock', 'Verrouiller la cible suivante automatiquement', true),
    tog('lockSwitchMouse', 'Changer de cible avec la souris', true),
    sld('padSens', 'Sensibilité de la manette', 10, 300, 5, 100, '%'),
    tog('vibration', 'Vibrations de la manette', true),
  ] },
  { id: 'gameplay', label: 'Jeu', options: [
    sel('difficulty', 'Difficulté', [['story', 'Conteur'], ['normal', 'Veilleur'], ['hard', 'Vétéran'], ['nightmare', 'Sans-Aube']], 'normal', 'Conteur : ennemis affaiblis. Sans-Aube : chaque coup peut être le dernier.'),
    sld('dayLength', 'Durée d\'une journée', 10, 90, 5, 30, ' min'),
    sld('cameraShake', 'Tremblement de caméra', 0, 100, 5, 70, '%'),
    tog('damageNumbers', 'Afficher les dégâts', true),
    tog('compass', 'Boussole', true),
    tog('questTracker', 'Suivi de quête', true),
    tog('enemyBars', 'Barres de vie des ennemis', true),
    tog('tutorials', 'Conseils', true),
    tog('autosave', 'Sauvegarde automatique', true),
    tog('showHelm', 'Afficher le casque', true, 'Masque le casque du personnage sans retirer sa protection.'),
  ] },
  { id: 'access', label: 'Accessibilité', options: [
    sld('uiScale', 'Taille de l\'interface', 80, 140, 5, 100, '%'),
    tog('subtitles', 'Sous-titres', true),
    sel('colorblind', 'Couleurs de l\'interface', [['off', 'Standard'], ['deuter', 'Deutéranopie'], ['protan', 'Protanopie'], ['tritan', 'Tritanopie']], 'off'),
    tog('reduceFlashes', 'Réduire les flashs lumineux', false),
    tog('holdToSprint', 'Maintenir pour courir', true, 'Sinon, appuyer une fois pour basculer.'),
    tog('lockToggle', 'Garde par bascule', false, 'Appuyer une fois pour lever/baisser la garde.'),
  ] },
];

export const PRESETS = {
  low: { renderScale: 75, antialias: 'fxaa', shadows: 'low', terrainShadows: true, cloudShadows: true, viewDistance: 'low', vegetation: 'low', grass: 'low', anisotropy: 2, ao: 'off', bloom: 40, godrays: false, lights: 2, particles: 'low' },
  medium: { renderScale: 85, antialias: 'fxaa', shadows: 'medium', terrainShadows: true, cloudShadows: true, viewDistance: 'medium', vegetation: 'medium', grass: 'medium', anisotropy: 4, ao: 'low', bloom: 55, godrays: true, lights: 2, particles: 'medium' },
  high: { renderScale: 100, antialias: 'fxaa', shadows: 'high', terrainShadows: true, cloudShadows: true, viewDistance: 'high', vegetation: 'high', grass: 'high', anisotropy: 4, ao: 'low', bloom: 55, godrays: true, lights: 4, particles: 'high' },
  ultra: { renderScale: 100, antialias: 'fxaa', shadows: 'ultra', terrainShadows: true, cloudShadows: true, viewDistance: 'ultra', vegetation: 'ultra', grass: 'ultra', anisotropy: 8, ao: 'high', bloom: 60, godrays: true, lights: 4, particles: 'high' },
};
export const PRESET_KEYS = Object.keys(PRESETS.high);

/** Actions and default bindings (event.code values; Mouse0/1/2 = left/right/middle). */
export const ACTIONS = [
  ['forward', 'Avancer', ['KeyW', 'ArrowUp']], ['back', 'Reculer', ['KeyS', 'ArrowDown']],
  ['left', 'Gauche', ['KeyA', 'ArrowLeft']], ['right', 'Droite', ['KeyD', 'ArrowRight']],
  ['sprint', 'Courir', ['ShiftLeft']], ['dodge', 'Esquive / roulade', ['Space']], ['jump', 'Sauter', ['KeyC']],
  ['attack', 'Attaque légère', ['Mouse0']], ['heavy', 'Attaque lourde', ['KeyF']], ['block', 'Garde / parade', ['Mouse1']],
  ['lock', 'Verrouiller une cible', ['Mouse2', 'KeyQ']],
  ['skill1', 'Pouvoir d\'Éclat 1', ['Digit1']], ['skill2', 'Pouvoir d\'Éclat 2', ['Digit2']], ['skill3', 'Pouvoir d\'Éclat 3', ['Digit3']],
  ['flask', 'Boire une fiole', ['KeyR']], ['interact', 'Interagir', ['KeyE']], ['sheathe', 'Rengainer / dégainer', ['KeyX']],
  ['torch', 'Allumer / éteindre la torche', ['KeyT']], ['autoTravel', 'Aller vers l\'objectif suivi', ['KeyG']],
  ['inventory', 'Inventaire', ['KeyI', 'Tab']], ['map', 'Carte', ['KeyM']], ['journal', 'Journal', ['KeyJ']],
  ['character', 'Personnage', ['KeyP']], ['pause', 'Menu', ['Escape']], ['hideHud', 'Masquer l\'interface', ['F10']],
];

const KEY = 'valombre.settings.v1';

export class Settings {
  constructor() {
    this.values = {};
    for (const cat of SETTINGS_SCHEMA) for (const o of cat.options) this.values[o.key] = o.def;
    this.binds = {};
    for (const [id, , keys] of ACTIONS) this.binds[id] = keys.slice();
    this.autoPreset = null;      // result of the first-launch benchmark
    this.firstRun = true;
    this.load();
  }

  load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return;
      const d = JSON.parse(raw);
      for (const k in d.values || {}) if (k in this.values) this.values[k] = d.values[k];
      for (const k in d.binds || {}) if (k in this.binds && Array.isArray(d.binds[k])) this.binds[k] = d.binds[k];
      this.autoPreset = d.autoPreset || null;
      this.firstRun = false;
    } catch (e) { console.warn('settings load', e); }
  }

  save() {
    try { localStorage.setItem(KEY, JSON.stringify({ values: this.values, binds: this.binds, autoPreset: this.autoPreset })); } catch (e) { /* storage full / blocked */ }
  }

  get(k) { return this.values[k]; }

  set(k, v, silent = false) {
    if (this.values[k] === v) return;
    this.values[k] = v;
    if (k === 'preset') this.applyPreset();
    else if (PRESET_KEYS.includes(k) && this.values.preset !== 'custom') this.values.preset = 'custom';
    this.save();
    if (!silent) bus.emit('settings', k, v);
  }

  applyPreset() {
    let p = this.values.preset;
    if (p === 'custom') return;
    if (p === 'auto') p = this.autoPreset || 'medium';
    Object.assign(this.values, PRESETS[p]);
  }

  /** effective preset name used for systems that only know low/medium/high/ultra */
  resetCategory(id) {
    const cat = SETTINGS_SCHEMA.find(c => c.id === id);
    if (!cat) return;
    for (const o of cat.options) this.values[o.key] = o.def;
    if (id === 'graphics') this.applyPreset();
    this.save();
    bus.emit('settings', '*');
  }

  resetBinds() {
    for (const [id, , keys] of ACTIONS) this.binds[id] = keys.slice();
    this.save();
    bus.emit('binds');
  }

  setBind(action, slot, code) {
    // remove the code from any other action so that a key does one thing
    for (const a in this.binds) this.binds[a] = this.binds[a].filter(c => c !== code || a === action);
    const list = this.binds[action];
    list[slot] = code;
    this.binds[action] = list.filter(Boolean);
    this.save();
    bus.emit('binds');
  }
}

const LEVEL = { low: 0, medium: 1, high: 2, ultra: 3 };

/** Push the settings into the engine / audio. Safe to call at any time. */
export function applySettings(s, app) {
  const v = s.values, e = app.engine;
  if (e && e.pipeline) {
    const aa = v.antialias;
    e.pipeline.setOptions({
      renderScale: v.renderScale / 100,
      fxaa: aa !== 'off', msaa: aa === 'msaa2' ? 2 : aa === 'msaa4' ? 4 : 0,
      ao: v.ao === 'off' ? 0 : v.ao === 'low' ? 1 : 2,
      bloom: v.bloom / 100, god: !!v.godrays,
      sharpen: v.sharpen / 100 * 0.8, vignette: v.vignette / 100 * 0.9, grain: v.grain / 100 * 0.11, chroma: v.chroma / 100 * 0.06,
      gamma: v.brightness / 100, contrast: 1.05 * v.contrast / 100, saturation: v.saturation / 100,
    });
    e.pipeline.autoScale = !!v.dynamicRes;
    e.pipeline.targetFps = Number(v.targetFps);
    if (!v.dynamicRes) e.pipeline.setOptions({ renderScale: v.renderScale / 100 });
    e.pipeline.maxScale = v.renderScale / 100;
    e.setQuality({
      shadows: v.shadows, terrainShadows: !!v.terrainShadows, cloudShadows: !!v.cloudShadows,
      view: LEVEL[v.viewDistance] ?? 2, vegetation: LEVEL[v.vegetation] ?? 2,
      grass: v.grass === 'off' ? 0 : (LEVEL[v.grass] ?? 2) + 1,
      lights: Number(v.lights), particles: LEVEL[v.particles] ?? 2, fov: v.fov,
    });
    if (e.atmo) e.atmo.dayLength = v.dayLength * 60;
  }
  if (app.audio) {
    const m = v.volMaster / 100;
    app.audio.setVolumes({ master: m, music: v.volMusic / 100, sfx: v.volSfx / 100, ambience: v.volAmbience / 100, voice: v.volVoice / 100, ui: v.volUi / 100 });
  }
  document.documentElement.style.setProperty('--ui-scale', String(v.uiScale / 100));
  document.documentElement.dataset.colorblind = v.colorblind;
}
