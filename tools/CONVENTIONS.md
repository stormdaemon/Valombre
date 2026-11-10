# VALOMBRE — asset production conventions (read fully before producing anything)

VALOMBRE is a third-person medieval dark-fantasy action RPG that runs in the browser (three.js r187,
WebGL2) on an integrated GPU (AMD Radeon Vega 8). Every 3D asset is generated **procedurally with
Blender 5.1 Python scripts run headless**. The scripts are part of the deliverable (reproducible).

## Hard rules
- Never ask the user anything. Never download anything from the internet (no asset packs, no pip, no
  add-ons). Everything is authored by your own code. Zero cost.
- Only write inside the folders your brief gives you. Never edit `tools/blender/blcommon.py`,
  `tools/blender/humanoid_rig.py` or this file (if you find a real bug in them, work around it in your
  own script and report it in your final message).
- Blender: `"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup -P <script.py>`
  (Bash tool: `"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup -P tools/blender/x.py 2>&1 | grep -E "PREVIEW|EXPORTED|Error|Traceback|line [0-9]+"`).
  Blender bundles numpy. System python has no numpy: run numpy code through Blender.
- Other agents run Blender at the same time on this 8-core / 10 GB machine: keep scenes light, no
  Cycles renders, previews <= 512 px per tile, never leave a process running.
- Blender 5.x API reminders: EEVEE id is `BLENDER_EEVEE`; `action.fcurves` no longer exists (use
  `pose_bone.keyframe_insert(...)`); set `image_settings.media_type` before `file_format`;
  shape keys forbid applying modifiers (apply modifiers BEFORE adding shape keys).
- Use `tools/blender/blcommon.py` (read it first): `reset_scene, make_mat, lin, set_vertex_colors, box_uv,
  auto_weights, rigid_weights, limit_weights, add_empty, add_collider_box, export_glb, glb_info,
  render_sheet, save_png, load_image, montage, new_action, actions_to_nla, tri_count`.
- **You must LOOK at what you make.** Render contact sheets with `render_sheet(...)` into
  `tools/previews/<your prefix>_*.png` and open them with the Read tool. Iterate until the asset is
  genuinely good: correct proportions, readable silhouette, no holes, no inverted normals, no exploded
  geometry. A model you have not looked at is not done. Delete obsolete previews at the end, keep one
  final sheet per asset family.
- Verify every exported file with the summary printed by `export_glb` (triangle counts, materials,
  skins, animations, attributes).

## Art direction
Grounded, weathered medieval Europe (12th-14th century) turned dark fantasy: a kingdom ruined by the
shattering of a fallen star ("l'Astre-Coeur"). Realistic proportions (NOT cartoon / chibi / low-poly
faceted look: smooth shading with sensible hard edges). Muted earthy palette (stone grey-beige, aged
wood, moss, rust, wool) with a few strong accents: ember orange (shrine fires), cold cyan-white
(Astre shards, `M_crystal`), sickly green (swamp), violet (corruption). Things are worn, asymmetric,
repaired, leaning: avoid perfect boxes — bevel edges, taper, sag roofs slightly, jitter planks/stones.

## Coordinates, scale, export
- Meters. Blender Z up. Everything FRONT faces **-Y**. Character's left = +X.
- Origin = center of the footprint on the ground (z = 0), unless the brief says otherwise.
- `.glb`, +Y up, exported with `export_glb` only. Transforms applied (scale 1, rotation 0) on meshes.
- One mesh object per logical part; few materials per mesh (each material = one draw call).
- Smooth shading + sharp edges where needed (split edges or `mark sharp` + custom normals are exported).
- Triangle budgets are in each brief and are hard limits (integrated GPU!).

## Materials = names (contract with the engine)
The engine REPLACES every material by its own PBR material, looked up by **material name**. Blender-side
colors are only for previews. Albedo color variation is carried by **vertex colors**: every mesh has a
`COLOR_0` attribute (use `set_vertex_colors`, LINEAR values, use `lin('#rrggbb')`), which **multiplies**
the material's texture. Bake simple ambient occlusion / dirt gradients into it (darker in crevices,
under eaves, near the ground): it adds a lot of depth for free. Create preview materials with
`make_mat(name, color, rough, metal, use_vertex_color=True)`.

Tiling materials (UV = world meters / tile size; use `box_uv(obj, tile)` or equivalent):

| Material name | Looks like | Tile | Notes |
|---|---|---|---|
| `M_stone_wall` | rough rubble masonry, grey-beige, horizontal courses | 2 m | texture has its own color: use near-white vertex colors (plus AO/dirt) |
| `M_stone_brick` | large cut stone blocks (castle) | 2 m | idem |
| `M_cobble` | cobblestones (ground, paths) | 2 m | idem |
| `M_plaster` | whitewashed daub, stained | 2 m | idem; tint slightly for variety |
| `M_wood_planks` | weathered planks, boards run along **V** (texture vertical), ~8 boards across | 2 m | swap U/V for horizontal boards/beams. Vertex color darkens for beams (e.g. lin('#6b5647')) |
| `M_roof_tiles` | clay/slate shingles in horizontal rows, top of texture = ridge side | 2 m | v must run up the roof slope |
| `M_thatch` | straw thatch, straws run along V (downhill) | 2 m | also used for hay |
| `M_rock` | natural rock / cliff | 4 m | rocks, cliffs, standing stones |
| `M_bark_oak`, `M_bark_pine`, `M_bark_birch` | tree bark | 1 m | u = around the trunk (meters of circumference), v = height |

Detail materials: the texture is a near-white fine detail (normal/roughness) — **the vertex color IS the
color**. UV = any reasonable unwrap at roughly world meters / 0.5.

| Material name | Use |
|---|---|
| `M_metal_iron` | dark wrought iron: hinges, tools, chains, crude weapons |
| `M_metal_steel` | polished steel: blades, plate armor |
| `M_metal_gold`, `M_metal_bronze` | ornaments, crowns, fittings |
| `M_leather` | straps, belts, boots, leather armor |
| `M_cloth` | fabric: tunics, capes, banners, tents, sacks |
| `M_rope` | ropes, wicker |
| `M_fur` | animal fur |
| `M_hide` | thick bumpy monster hide (troll...) |
| `M_chitin` | glossy insect/spider shell |
| `M_bone` | bone, horn, teeth, claws |
| `M_skin` | human skin (engine skin shader) |
| `M_hair` | hair, beards, brows (engine hair shader; vertex color = white, engine tints) |
| `M_eye` | eyeballs (engine eye shader) |

Emissive / special (no UV needed, vertex color = tint):

| Material name | Use |
|---|---|
| `M_crystal` | Astre shards: glowing cold cyan-white crystal |
| `M_rune_glow` | glowing runes / corruption veins (engine sets the color) |
| `M_ember` | hot coals, lava cracks, molten glow (orange) |
| `M_window_glow` | window panes, lanterns (warm, lit at night) |
| `M_ice` | translucent blue ice |
| `M_obsidian` | black volcanic glass |
| `M_leaves` | alpha-tested foliage atlas (nature pack only) |

Need a material that is not listed? Prefer the closest one + vertex color. If truly necessary, create
`M_<new_name>` and list it in your manifest with a description so the engine can map it.

## Special nodes inside a .glb
- `COL_*` : box mesh = collision proxy (use `add_collider_box`). Any static asset a character should not
  walk through needs them (walls, trunks, big props). Leave doors/arches passable (a gate = 2 pillars).
  Keep the count low (1-6 boxes per asset). Colliders are axis-aligned boxes rotated around Z only.
- `WALK_*` : box mesh = walkable platform; the player stands on its TOP face (bridges, docks, daises,
  stairs = a few boxes rising by <= 0.3 m each). Create it like a collider box
  (`add_collider_box` then rename `COL_x` -> `WALK_x`). The ground is otherwise the terrain only.
- Empties (use `add_empty`), child of the main mesh:
  `FIRE_*` (a flame + flickering light spawns here), `SMOKE_*` (chimney smoke), `GLOW_*` (soft point
  light), `ANCHOR_*` (gameplay anchor: `ANCHOR_door`, `ANCHOR_npc`, `ANCHOR_loot`, ...).
- `ROT_*` : separate mesh object the engine rotates/animates (windmill blades, chest lid). Its origin must
  be the pivot.

## Manifest
Each pack writes a `manifest.json` next to its .glb files: for every asset its file, a one-line
description, real size (bounding box in meters), triangle count, materials used, special nodes, and
anything the engine must know (animation clip list with durations and event times, morph target list,
atlas rectangles, suggested scale range...). Brief-specific fields are described in each brief.

## Final report (your last message)
List what you produced (paths), anything you could not finish, deviations from the brief, and any
integration notes for the engine programmer. Be factual: if something looks mediocre, say so.
