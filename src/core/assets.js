// Asset loading helpers (textures with procedural fallbacks, glb models, json).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export function loadImage(url) {
  return new Promise((res) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => res(null);
    im.src = url;
  });
}

/** Tiling texture from a PNG. opts: srgb, flipY (default false: glTF convention), aniso, mips, repeat */
export async function loadTexture(url, opts = {}) {
  const im = await loadImage(url);
  if (!im) return null;
  const t = new THREE.Texture(im);
  t.flipY = opts.flipY ?? false;
  t.colorSpace = opts.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  const rep = opts.repeat ?? true;
  t.wrapS = t.wrapT = rep ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
  const mips = opts.mips ?? true;
  t.minFilter = mips ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = mips;
  t.anisotropy = opts.aniso ?? 4;
  t.needsUpdate = true;
  return t;
}

function lattice(size, cells, rnd) {
  const g = new Float32Array(cells * cells);
  for (let i = 0; i < g.length; i++) g[i] = rnd();
  const out = new Float32Array(size * size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const fx = x / size * cells, fy = y / size * cells;
    const ix = Math.floor(fx), iy = Math.floor(fy);
    let u = fx - ix, v = fy - iy;
    u = u * u * (3 - 2 * u); v = v * v * (3 - 2 * v);
    const x1 = (ix + 1) % cells, y1 = (iy + 1) % cells;
    const a = g[iy * cells + ix], b = g[iy * cells + x1], c = g[y1 * cells + ix], d = g[y1 * cells + x1];
    out[y * size + x] = a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  return out;
}

function fbmTile(size, base, oct, rnd, billow = false) {
  const out = new Float32Array(size * size);
  let amp = 1, norm = 0, cells = base;
  for (let o = 0; o < oct && cells <= size / 2; o++) {
    const l = lattice(size, cells, rnd);
    for (let i = 0; i < out.length; i++) out[i] += (billow ? 1 - Math.abs(l[i] * 2 - 1) : l[i]) * amp;
    norm += amp; amp *= 0.5; cells *= 2;
  }
  let mn = 1e9, mx = -1e9;
  for (let i = 0; i < out.length; i++) { out[i] /= norm; if (out[i] < mn) mn = out[i]; if (out[i] > mx) mx = out[i]; }
  for (let i = 0; i < out.length; i++) out[i] = (out[i] - mn) / (mx - mn);
  return out;
}

function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

/** Fallback for fx_noise.png: tileable RGBA noise. */
export function makeNoiseTexture(size = 256) {
  const r = rng(12345);
  const R = fbmTile(size, 4, 5, r), G = fbmTile(size, 8, 4, r, true), B = fbmTile(size, 16, 4, r), A = fbmTile(size, 4, 5, r, true);
  const d = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i++) { d[i * 4] = R[i] * 255; d[i * 4 + 1] = G[i] * 255; d[i * 4 + 2] = B[i] * 255; d[i * 4 + 3] = A[i] * 255; }
  const t = new THREE.DataTexture(d, size, size, THREE.RGBAFormat);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}

/** Fallback for water_n.png: RG = normal, B = foam noise. */
export function makeWaterNormalTexture(size = 256) {
  const r = rng(777);
  const h = fbmTile(size, 8, 5, r, true), f = fbmTile(size, 8, 4, r);
  const d = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const i = y * size + x;
    const dx = h[y * size + (x + 1) % size] - h[y * size + (x + size - 1) % size];
    const dy = h[((y + 1) % size) * size + x] - h[((y + size - 1) % size) * size + x];
    d[i * 4] = Math.max(0, Math.min(255, 128 - dx * 900)); d[i * 4 + 1] = Math.max(0, Math.min(255, 128 - dy * 900));
    d[i * 4 + 2] = f[i] * 255; d[i * 4 + 3] = 255;
  }
  const t = new THREE.DataTexture(d, size, size, THREE.RGBAFormat);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}

const gltfLoader = new GLTFLoader();
const gltfCache = new Map();
/** Load a .glb once (cached). Resolves to the gltf object, or null when the file is missing. */
export function loadGLB(url) {
  if (!gltfCache.has(url)) {
    gltfCache.set(url, new Promise((res) => {
      gltfLoader.load(url, (g) => res(g), undefined, () => { console.warn('[assets] missing model', url); res(null); });
    }));
  }
  return gltfCache.get(url);
}

export async function loadJSON(url) {
  try { const r = await fetch(url); if (!r.ok) return null; return await r.json(); } catch (e) { return null; }
}
