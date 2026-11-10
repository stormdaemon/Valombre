// Lists the model files so the game knows what exists without probing (static server = no directory listing).
// Run: node tools/make_index.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'assets', 'models');
const out = {};
for (const dir of fs.readdirSync(root)) {
  const p = path.join(root, dir);
  if (!fs.statSync(p).isDirectory()) continue;
  out[dir] = fs.readdirSync(p).filter(f => f.endsWith('.glb')).map(f => f.slice(0, -4)).sort();
}
fs.writeFileSync(path.join(root, 'index.json'), JSON.stringify(out));
console.log(Object.entries(out).map(([k, v]) => `${k}: ${v.length}`).join(', '));
