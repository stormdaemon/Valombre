# VALOMBRE — UI contract (between `src/ui/**` and the game code)

The UI is plain DOM + CSS layered over the WebGL canvas. ES modules, no dependency, no build step,
French text everywhere. It lives in `<div id="ui">` (already in `index.html`, `position:fixed; inset:0;
pointer-events:none`); interactive panels set `pointer-events:auto` on themselves.

```js
// src/ui/ui.js
export class UI {
  constructor(app)        // builds the DOM once, subscribes to the bus. Loads src/ui/ui.css itself (<link>).
  update(dt)              // called every frame by the app (HUD refresh, world-anchored widgets). Must be cheap:
                          // only touch the DOM when a value changed, no layout reads in the frame loop.
  setLoading(p, text)     // boot progress 0..1 (the UI owns the loading screen; hide it when app.state leaves 'boot')
  get blocking()          // true while a screen that needs the mouse is open
}
```
The UI drives navigation itself: it reads `app.state` and `app.input` and calls the `app.*` methods below.
Whenever `blocking` changes it calls `app.setUiBlocking(bool)` (the app then releases/requests pointer
lock, disables gameplay input and pauses the world). Menus must be fully usable with the mouse AND with
the keyboard (arrows / Entrée / Échap) and a gamepad through the same `app.input` actions.

## App
```js
app.state            // 'boot' | 'title' | 'creator' | 'playing'   (bus event 'state' (new, old) on change)
app.settings         // Settings instance (src/core/settings.js): get(k), set(k, v), resetCategory(id), resetBinds(),
                     // setBind(action, slot, code), .binds[action] -> [codes]. Schema: SETTINGS_SCHEMA, ACTIONS, PRESETS exports.
                     // The options screen is generated from SETTINGS_SCHEMA (select / slider / toggle + desc) and the
                     // key-binding page from ACTIONS; changes apply immediately (settings.set does it).
app.input            // Input (src/core/input.js): pressed(action), down(action), label(code), actionLabel(action),
                     // capture = (code|null) => {}  (next key/mouse button goes to the callback; null = cancelled by Échap)
app.audio            // AudioEngine or null. UI sounds: app.sfx('ui_hover'|'ui_click'|'ui_back'|'ui_open'|'ui_close'|'ui_error'|
                     //   'ui_equip'|'ui_slider'|'ui_save'|'ui_buy') — app.sfx is always safe to call.
app.gpu              // renderer string, app.perf() -> { fps, ms, calls, tris, scale, res:[w,h] }   (for "Afficher les performances")
app.saves            // list() -> [{ slot:0..3, empty, name, level, region, playtime (s), date (ms), origin }]  (slot 0 = autosave)
                     // latest() -> slot | -1 ; delete(slot)
app.continueGame()   // loads the most recent save
app.loadSlot(slot)
app.saveSlot(slot)   // only while playing and not in combat; returns bool
app.openCreator()    // state -> 'creator' (3D preview of the character on screen)
app.startNewGame({ name, origin, appearance })     // state -> 'playing'
app.quitToTitle()
app.setUiBlocking(bool)
app.benchmark()      // async -> { preset:'low'|'medium'|'high'|'ultra', fps } ; also stores it as the 'auto' preset
```

## Character creator (`app.creator`, valid in state 'creator')
```js
creator.morphs        // [{ name, category, label, min, max, default }]  categories: body, head, eyes, nose, mouth, jaw, ears
creator.appearance    // { morphs:{name:value}, skin, hair, hairColor, beard, eyeColor, brows, paint, paintColor, scar, voice, height }
creator.set(key, value)          // any appearance key (live preview)
creator.setMorph(name, value)
creator.setAll(appearance)       // presets / randomise
creator.setOrigin(originId)      // preview the starting equipment
creator.setView('face' | 'body') // camera framing
creator.rotate(deltaRadians)     // drag to rotate the character
creator.playVoice()              // audition the chosen voice pitch
```
Palettes, styles, presets, `randomAppearance()`, `defaultAppearance()`, `MORPH_CATEGORIES`: `src/game/data/creator.js`.
Origins (name, desc, attrs, gear): `ORIGINS` in `src/game/data/rules.js`. The creator must expose every morph as a
slider grouped by category, colour swatches, style pickers, presets, "Aléatoire", "Réinitialiser", name field, origin choice
with its stats, view toggle, and "Commencer l'aventure".

## Game (`app.game`, valid in state 'playing')
```js
const g = app.game, p = g.player, d = p.data, st = p.st;
// vitals
p.hp, p.maxHp, d.stamina, st.maxSt, d.mana, st.maxMana, d.flasks, d.flaskMax, d.gold, d.level, d.xp, d.attrPoints, d.attrs
p.status          // { poison|burn|frost|slow: { t (s left), build (0..threshold) } } ; p.statusThreshold ; STATUS (rules.js) gives name/color
p.buffs           // { sharp|vigor|fury: { t, mult } }
p.target          // locked enemy or null ; p.dead ; p.state ('rest' while sitting at a shrine)
d.equipment       // { weapon, offhand, head, chest, legs } -> { id, up } | null
d.inventory       // [{ id, qty, up }]   (ITEMS[id] in src/game/data/items.js: name, type, desc, slot, stats, value; itemName(inst))
d.skills, d.skillSlots [3], p.skillCd[id] (s left) ; SKILLS[id] = { name, cost, cd, desc }
st                // derive(d): maxHp, maxSt, maxMana, def, poise, weight, capacity, load, attack, crit, skillPower, block, stability, weapon, shield
xpForLevel(level), ATTRS, derive   // rules.js  (preview a stat change with derive on a copy of d)

p.equip(invIndex)   p.unequip(slot)   p.spendPoint(attr) -> bool
g.useItem(invIndex) -> bool            g.dropItem(invIndex)
g.setSkillSlot(slot, skillId | null)

g.focus           // { label, key } | null : interaction prompt ("[E] label")
g.boss            // null | { def:{ name, title }, hp, maxHp, phase }
g.enemies         // [{ pos:Vector3, height, hp, maxHp, barT (>0 = show bar), dead, isBoss, vulnerableT, def:{ name } }]
g.toScreen(vec3, out)        // -> out = { x, y, visible } in CSS pixels
g.compass()       // { yaw (camera heading, rad; 0 = looking south(+Z), increases turning left), markers:[{ kind:'shrine'|'quest'|'poi'|'boss', x, z, name }] }
                  //   world axes: +X = east, +Z = south. bearing of a marker = atan2(dx, dz).
g.region          // { id, name } current region ; g.hour (0..24) ; g.day
g.map()           // { image:HTMLImageElement (1024x1024 parchment, world x,z in [-2560,2560] -> px (x+2560)/5, (z+2560)/5),
                  //   player:{ x, z, yaw }, shrines:[{ id, name, x, z, found }], pois:[{ id, name, type, x, z, found }], quests:[{ x, z, name }] }
g.canFastTravel   // true only while resting at a shrine ; g.fastTravel(shrineId)
g.shrine          // while resting: { id, name, flaskCountCost: bool (has amber_sap), flaskPowerCost: bool (has ember_seed) }
g.shrineAction('flaskCount' | 'flaskPower' | 'morning' | 'night' | 'leave')
g.shop            // while trading: { name, stock:[{ id, price, qty }], buy(i) -> bool, sellPrice(invIndex), sell(invIndex) -> bool, close() }
g.smith           // while at the forge: { list() -> [{ where:'weapon'|'offhand'|invIndex, id, up, cost:{ gold, <itemId>:n }, can }], upgrade(where) -> bool, close() }
g.dialogue        // while talking: { speaker, text, options:[{ label }], choose(i) }  (bus 'dialogue' on every change; null when over)
g.quests.list()   // [{ id, title, desc, state:'active'|'done', main:bool, steps:[{ text, done }], tracked }] ; g.quests.track(id)
g.codex()         // [{ id, title, text, category:'Histoire'|'Lieux'|'Créatures'|'Personnages', found }]
g.closePanel()    // leave shrine / shop / smith / dialogue
```

## Bus events (`import { bus } from '../core/events.js'`; `bus.on(type, fn)`)
| event | payload | meaning |
|---|---|---|
| `state` | new, old | app state changed |
| `settings` | key, value | a setting changed (`'*'` = many) |
| `binds` | – | key bindings changed |
| `toast` | `{ kind:'item', id, qty }` / `{ kind:'gold', n }` / `{ kind:'xp', n }` / `{ kind:'level', level }` / `{ kind:'text', text }` / `{ kind:'quest', title, done }` / `{ kind:'skill', id }` | small notification |
| `damage` | `{ x, y, z, dmg, crit, blocked }` | floating damage number (if setting `damageNumbers`) |
| `discover` | `{ name, sub }` | big area banner ("Forêt de Sombreronce") |
| `banner` | `{ title, sub, kind:'boss'|'shard'|'shrine' }` | centre banner ("ÉCLAT RETROUVÉ", "AUTEL EMBRASÉ"…) |
| `boss:start` / `boss:end` | boss / `{ boss, won }` | show / hide the boss bar |
| `boss:phase` | `{ boss, text }` | subtitle line |
| `player:hurt` | dmg | (HUD flash; the 3D vignette is handled by the engine) |
| `death` | – | "VOUS AVEZ PÉRI" screen until `respawn` |
| `respawn` | – | |
| `open` | `'shrine'|'shop'|'smith'|'inventory'|'map'|'journal'|'character'` | the game asks for a panel |
| `dialogue` | – | `g.dialogue` changed |
| `lock` | enemy or null | lock-on target changed (reticle follows `g.toScreen`) |
| `subtitle` | `{ text, time }` | a spoken/ambient line |
| `ending` | `{ id }` | end of the game: credits roll |
| `inventory`, `player:stats`, `player:xp`, `player:flask`, `player:buffs`, `quest` | – | refresh hints |

## Screens to build
Title (Continuer / Nouvelle partie / Charger / Options / Crédits / Quitter le jeu), save slots, options (5 categories +
key bindings + "Tester ma machine" benchmark + reset), character creator, loading, HUD (health / stamina / Éclat bars,
flask count, 3 skill slots with cooldowns and key labels, equipped weapon, status build-ups and buffs, compass strip with
markers, lock-on reticle, enemy health bars above heads, boss bar, interaction prompt, toasts, damage numbers, area
banners, quest tracker, subtitles, low-health pulse, optional perf counter), pause menu (Reprendre / Inventaire / Carte /
Journal / Options / Sauvegarder / Menu principal), inventory + equipment with comparison and item details, character
sheet + level-up, world map with pan/zoom, markers and fast travel, journal (quests + codex), shrine menu (rest:
level up, fast travel, improve flask, wait until morning/night, leave), shop (buy / sell), smith (upgrade), dialogue box
with choices, death screen, ending credits.
