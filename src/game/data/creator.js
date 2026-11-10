// Character creator data: palettes, presets, default appearance. Morph names come from the human kit
// (assets/models/char/human_manifest.json); the list below is the contract used when the manifest is missing.
export const SKIN_TONES = ['#f1d3bd', '#e8c2a5', '#dcae8c', '#c9a184', '#b98d6c', '#a67855', '#8d6242', '#734c31', '#573823', '#3f2818', '#c7b6a8', '#9fb0a0'];
export const HAIR_COLORS = ['#17120f', '#2b1d14', '#47301f', '#6b4728', '#8c5a2b', '#a9713a', '#c79a56', '#dcc18a', '#b8452a', '#8c2f1d', '#8f8f8f', '#d9d6cf', '#f1ede4', '#3a4a5a'];
export const EYE_COLORS = ['#3b2a1c', '#5a3d22', '#7a5a2e', '#4d6b3a', '#6f8f4f', '#3f6f8f', '#5f9fc7', '#8fb7c9', '#7f7f86', '#b08a3a', '#8f3a3a', '#a070d0'];
export const PAINT_COLORS = ['#1a1a1a', '#7a1c14', '#1f3a6b', '#e8e2d4', '#2f5a34', '#c9a13a'];

export const HAIR_STYLES = [
  ['none', 'Crâne rasé'], ['hair_crop', 'Ras'], ['hair_short', 'Court'], ['hair_medium', 'Mi-long'], ['hair_long', 'Long'],
  ['hair_ponytail', 'Queue de cheval'], ['hair_braid', 'Tresse'], ['hair_topknot', 'Chignon'], ['hair_mohawk', 'Crête'],
];
export const BEARD_STYLES = [['none', 'Imberbe'], ['beard_stubble', 'Barbe naissante'], ['beard_short', 'Courte'], ['beard_goatee', 'Bouc'], ['beard_full', 'Fournie'], ['beard_long', 'Longue'], ['mustache', 'Moustache']];
export const PAINT_STYLES = [['none', 'Aucune'], ['stripe', 'Bandeau'], ['claws', 'Griffes'], ['tears', 'Larmes'], ['half', 'Demi-visage'], ['runes', 'Runes'], ['dots', 'Points'], ['skull', 'Crâne']];
export const SCAR_STYLES = [['none', 'Aucune'], ['brow', 'Arcade'], ['cheek', 'Joue'], ['lip', 'Lèvre'], ['cross', 'Croix'], ['burn', 'Brûlure']];
export const VOICES = [[0.72, 'Très grave'], [0.85, 'Grave'], [1.0, 'Médium'], [1.18, 'Claire'], [1.35, 'Aiguë']];

export const MORPH_FALLBACK = [
  ['feminine', 'body', 'Silhouette féminine', 0, 1], ['muscular', 'body', 'Musculature', 0, 1], ['heavy', 'body', 'Corpulence', 0, 1], ['thin', 'body', 'Maigreur', 0, 1],
  ['shoulder_width', 'body', 'Largeur d\'épaules', -1, 1], ['chest_size', 'body', 'Poitrine', -1, 1], ['breast_size', 'body', 'Buste', -1, 1], ['waist_size', 'body', 'Taille', -1, 1],
  ['hip_size', 'body', 'Hanches', -1, 1], ['belly', 'body', 'Ventre', 0, 1], ['glutes', 'body', 'Fessiers', -1, 1], ['arm_size', 'body', 'Bras', -1, 1], ['leg_size', 'body', 'Jambes', -1, 1], ['neck_size', 'body', 'Cou', -1, 1],
  ['head_size', 'head', 'Taille de la tête', -1, 1], ['head_width', 'head', 'Largeur du crâne', -1, 1], ['head_depth', 'head', 'Profondeur du crâne', -1, 1],
  ['forehead_height', 'head', 'Hauteur du front', -1, 1], ['forehead_slope', 'head', 'Inclinaison du front', -1, 1], ['brow_ridge', 'head', 'Arcade sourcilière', -1, 1], ['brow_height', 'head', 'Hauteur des sourcils', -1, 1],
  ['cheekbone_height', 'head', 'Hauteur des pommettes', -1, 1], ['cheekbone_width', 'head', 'Largeur des pommettes', -1, 1], ['cheek_fullness', 'head', 'Joues', -1, 1], ['age', 'head', 'Âge', 0, 1],
  ['eye_size', 'eyes', 'Taille des yeux', -1, 1], ['eye_spacing', 'eyes', 'Écartement', -1, 1], ['eye_height', 'eyes', 'Hauteur', -1, 1], ['eye_depth', 'eyes', 'Profondeur', -1, 1], ['eye_tilt', 'eyes', 'Inclinaison', -1, 1],
  ['nose_length', 'nose', 'Longueur', -1, 1], ['nose_width', 'nose', 'Largeur', -1, 1], ['nose_bridge', 'nose', 'Arête', -1, 1], ['nose_tip', 'nose', 'Pointe', -1, 1], ['nostril_width', 'nose', 'Narines', -1, 1],
  ['mouth_width', 'mouth', 'Largeur de la bouche', -1, 1], ['mouth_height', 'mouth', 'Hauteur de la bouche', -1, 1], ['lip_upper', 'mouth', 'Lèvre supérieure', -1, 1], ['lip_lower', 'mouth', 'Lèvre inférieure', -1, 1],
  ['jaw_width', 'jaw', 'Largeur de la mâchoire', -1, 1], ['jaw_height', 'jaw', 'Hauteur de la mâchoire', -1, 1], ['chin_length', 'jaw', 'Longueur du menton', -1, 1], ['chin_width', 'jaw', 'Largeur du menton', -1, 1], ['chin_forward', 'jaw', 'Avancée du menton', -1, 1],
  ['ear_size', 'ears', 'Taille des oreilles', -1, 1], ['ear_point', 'ears', 'Oreilles pointues', 0, 1],
].map(([name, category, label, min, max]) => ({ name, category, label, min, max, default: 0 }));

export const MORPH_CATEGORIES = [['body', 'Corps'], ['head', 'Tête'], ['eyes', 'Yeux'], ['nose', 'Nez'], ['mouth', 'Bouche'], ['jaw', 'Mâchoire'], ['ears', 'Oreilles']];

export function defaultAppearance() {
  return {
    morphs: {}, skin: SKIN_TONES[3], hair: 'hair_short', hairColor: HAIR_COLORS[2], beard: 'none', eyeColor: EYE_COLORS[5],
    brows: 0.5, paint: 'none', paintColor: PAINT_COLORS[0], scar: 'none', voice: 1.0, height: 1.0,
  };
}

export const PRESETS = [
  { id: 'veteran', label: 'Vétéran', a: { morphs: { muscular: 0.55, jaw_width: 0.4, brow_ridge: 0.4, age: 0.45, nose_bridge: 0.3 }, skin: SKIN_TONES[4], hair: 'hair_crop', hairColor: HAIR_COLORS[10], beard: 'beard_short', eyeColor: EYE_COLORS[8], scar: 'brow', voice: 0.85 } },
  { id: 'errante', label: 'Errante', a: { morphs: { feminine: 1, thin: 0.2, cheekbone_height: 0.4, eye_size: 0.25, jaw_width: -0.3, lip_lower: 0.3 }, skin: SKIN_TONES[2], hair: 'hair_braid', hairColor: HAIR_COLORS[8], beard: 'none', eyeColor: EYE_COLORS[3], voice: 1.18 } },
  { id: 'colosse', label: 'Colosse', a: { morphs: { muscular: 0.9, heavy: 0.5, shoulder_width: 0.7, neck_size: 0.6, jaw_width: 0.6, brow_ridge: 0.6 }, skin: SKIN_TONES[6], hair: 'none', hairColor: HAIR_COLORS[0], beard: 'beard_full', eyeColor: EYE_COLORS[0], voice: 0.72, height: 1.06 } },
  { id: 'disciple', label: 'Disciple', a: { morphs: { feminine: 0.8, thin: 0.5, cheek_fullness: -0.4, eye_size: 0.3, ear_point: 0.6, chin_length: 0.2 }, skin: SKIN_TONES[0], hair: 'hair_long', hairColor: HAIR_COLORS[12], beard: 'none', eyeColor: EYE_COLORS[11], paint: 'runes', paintColor: PAINT_COLORS[2], voice: 1.18 } },
  { id: 'ancien', label: 'Ancien', a: { morphs: { age: 1, thin: 0.5, nose_length: 0.4, cheek_fullness: -0.5, brow_height: -0.2 }, skin: SKIN_TONES[1], hair: 'hair_medium', hairColor: HAIR_COLORS[11], beard: 'beard_long', eyeColor: EYE_COLORS[7], voice: 0.85, height: 0.97 } },
];

export function randomAppearance(morphList = MORPH_FALLBACK) {
  const r = Math.random, pick = (a) => a[Math.floor(r() * a.length)];
  const a = defaultAppearance();
  const fem = r() < 0.5;
  for (const m of morphList) {
    if (m.category === 'expression') continue;
    if (m.name === 'feminine') { a.morphs.feminine = fem ? 0.75 + r() * 0.25 : r() * 0.15; continue; }
    if (m.name === 'ear_point') { a.morphs.ear_point = r() < 0.12 ? r() : 0; continue; }
    if (m.name === 'age') { a.morphs.age = r() < 0.3 ? r() : r() * 0.25; continue; }
    const span = (m.max - m.min) * (m.category === 'body' ? 0.3 : 0.28);
    const g = (r() + r() + r()) / 3 - 0.5;
    a.morphs[m.name] = Math.max(m.min, Math.min(m.max, (m.min < 0 ? 0 : 0.15) + g * 2 * span));
  }
  a.skin = pick(SKIN_TONES); a.hairColor = pick(HAIR_COLORS); a.eyeColor = pick(EYE_COLORS);
  a.hair = pick(HAIR_STYLES)[0]; a.beard = fem ? 'none' : pick(BEARD_STYLES)[0];
  a.paint = r() < 0.2 ? pick(PAINT_STYLES)[0] : 'none'; a.paintColor = pick(PAINT_COLORS);
  a.scar = r() < 0.25 ? pick(SCAR_STYLES)[0] : 'none';
  a.voice = fem ? 1.0 + r() * 0.35 : 0.72 + r() * 0.35; a.height = 0.94 + r() * 0.12;
  return a;
}
