// Smoke test of the real UI against the real game (not the mock bench).
// Usage, in a page of the game while playing:  (await import('/tools/game_smoke.js')).run()
// Returns { ok, steps, errors }. It changes the current game (gold, items, death...): use a throwaway game.

export async function run() {
  const a = window.__app, ui = a.ui, S = ui.screens;
  const errors = [], steps = [];
  const orig = console.error;
  console.error = (...x) => { errors.push(x.map((v) => (v && v.stack) || String(v)).join(' ').slice(0, 500)); orig.apply(console, x); };
  const onErr = (e) => errors.push('window: ' + e.message);
  addEventListener('error', onErr);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const step = async (name, fn) => {
    try { await fn(); await wait(120); if (window.__lastError) { errors.push(name + ' (frame): ' + window.__lastError.slice(0, 400)); window.__lastError = null; a._errShown = false; } steps.push(name); }
    catch (e) { errors.push(name + ': ' + String((e && e.stack) || e).slice(0, 500)); }
  };
  const expectTop = (scr, what) => { if (ui.top !== scr) throw new Error(what + ' not on top (top = ' + (ui.top && ui.top.constructor.name) + ')'); };
  if (a.state !== 'playing') return { ok: false, steps: 0, errors: ['not playing: ' + a.state] };
  let g = a.game, p = g.player, d = p.data;

  await step('pause', () => { ui.closeAll(); ui.back(); expectTop(S.pause, 'pause'); if (!a.blocking) throw new Error('pause does not block'); });
  await step('pause > options', () => { ui.open('options'); for (const id of ['graphics', 'audio', 'controls', 'gameplay', 'access', 'keys']) S.options.setTab(id); ui.back(); expectTop(S.pause, 'pause after options'); });
  await step('pause > save', () => { ui.open('saves', { mode: 'save' }); ui.closeAll(); if (a.blocking) throw new Error('still blocking after closeAll'); });
  await step('save slot 2', () => { if (!a.saveSlot(2)) throw new Error('saveSlot(2) refused'); const l = a.saves.list(); if (l[2].empty) throw new Error('slot 2 empty after save'); });
  d.attrPoints = (d.attrPoints || 0) + 2;
  d.gold += 3000;
  p.addItem('steel_shard', 6); p.addItem('herb_poultice', 2); p.addItem('steel_sword', 1); p.addItem('plate_chest', 1);
  for (const tab of ['inventory', 'character', 'map', 'journal']) await step('hub ' + tab, () => { ui.open('hub', { tab }); });
  await step('inventory actions', () => {
    S.hub.setTab('inventory'); const inv = S.hub.pages.inventory;
    for (const f of ['weapon', 'shield', 'armor', 'consumable', 'material', 'key', 'all']) { inv.filter = f; inv.refresh(); }
    const iSword = d.inventory.findIndex((it) => it && it.id === 'steel_sword');
    inv._select({ kind: 'inv', index: iSword }); inv._primary();
    if (!d.equipment.weapon || d.equipment.weapon.id !== 'steel_sword') throw new Error('steel_sword not equipped by the primary action');
    const iPlate = d.inventory.findIndex((it) => it && it.id === 'plate_chest');
    inv._select({ kind: 'inv', index: iPlate }); inv._primary();
    if (!d.equipment.chest || d.equipment.chest.id !== 'plate_chest') throw new Error('plate_chest not equipped');
    const h = p.model.inner.userData.human; if (h && (!h.state.outfit || h.state.outfit.chest !== 'plate_chest')) throw new Error('3D outfit not updated: ' + JSON.stringify(h.state.outfit));
    inv._select({ kind: 'eq', slot: 'offhand' }); inv._unequip('offhand'); inv.refresh();
    const iShield = d.inventory.findIndex((it) => it && it.id === 'wood_shield'); inv._select({ kind: 'inv', index: iShield }); inv._primary();
  });
  await step('character actions', () => { S.hub.setTab('character'); const c = S.hub.pages.character; const before = d.attrs.vigueur; c._add('vigueur', 1); c._confirm(); if (d.attrs.vigueur !== before + 1) throw new Error('attribute point not spent'); });
  await step('map actions', () => { S.hub.setTab('map'); const m = S.hub.pages.map; m._zoomBy(1.3); m._zoomBy(0.5); m._centerOnPlayer(true); });
  await step('journal actions', () => { S.hub.setTab('journal'); const j = S.hub.pages.journal; j.mode = 'quests'; j.refresh(); j.mode = 'codex'; j.refresh(); ui.closeAll(); });
  await step('use item', () => { const i = d.inventory.findIndex((it) => it && it.id === 'herb_poultice'); if (i < 0) throw new Error('no poultice'); if (!g.useItem(i)) throw new Error('useItem refused'); });

  // shrine
  const sid = d.lastShrine, shrine = g.content.shrines[sid];
  await step('shrine open', async () => { g._useShrine(shrine); await wait(1900); expectTop(S.shrine, 'shrine'); });
  await step('shrine actions', () => { S.shrine._act('night', ''); S.shrine._act('morning', ''); ui.open('hub', { tab: 'map' }); ui.close(); expectTop(S.shrine, 'shrine after map'); S.shrine._leave(); if (g.shrine) throw new Error('shrine still open'); });
  await wait(1200);

  // shop
  const shopId = 'ysabeau';
  await step('shop', () => { g.openShop(shopId); expectTop(S.shop, 'shop'); const gold = d.gold; S.shop._select({ side: 'buy', i: 0 }); S.shop._trade(); if (d.gold >= gold) throw new Error('buying did not cost gold'); S.shop._select({ side: 'sell', i: 0 }); S.shop._trade(); ui.back(); if (g.shop) throw new Error('shop still open'); });
  // smith
  await step('smith', () => { g.openSmith(); expectTop(S.smith, 'smith'); const up = d.equipment.weapon.up || 0; S.smith._upgrade(); if ((d.equipment.weapon.up || 0) !== up + 1) throw new Error('weapon not upgraded (' + up + ' -> ' + d.equipment.weapon.up + ')'); ui.back(); if (g.smith) throw new Error('smith still open'); });
  // dialogue
  await step('dialogue', async () => {
    const npc = g.npcs.find((n) => n.id === 'maelle') || g.npcs[0];
    g.talk(npc); await wait(200); expectTop(S.dialogue, 'dialogue');
    for (let k = 0; k < 12 && g.dialogue; k++) { const n = g.dialogue.options.length; S.dialogue._choose(n - 1); await wait(150); }
    if (g.dialogue) throw new Error('dialogue never ends');
  });
  await step('dialogue to shop', async () => {
    const npc = g.npcs.find((n) => n.id === 'ysabeau');
    g.talk(npc); await wait(200);
    const i = g.dialogue.options.findIndex((o) => /march|achet|voir|comm/i.test(o.label));
    if (i < 0) throw new Error('no trade option in: ' + g.dialogue.options.map((o) => o.label).join(' | '));
    S.dialogue._skip(); S.dialogue._choose(i); await wait(200); expectTop(S.shop, 'shop from dialogue'); ui.back();
  });
  // death and respawn
  await step('death', async () => { ui.closeAll(); p.hp = 0; p.die(null); await wait(400); if (!ui.death.on) throw new Error('death overlay missing'); });
  await wait(7000);
  await step('respawn', () => { if (ui.death.on) throw new Error('death overlay still shown'); if (p.dead) throw new Error('player still dead'); });
  // load the slot saved above
  await step('load slot 2', async () => { ui.closeAll(); if (!a.loadSlot(2)) throw new Error('loadSlot failed'); await wait(600); g = a.game; p = g.player; d = p.data; if (a.state !== 'playing') throw new Error('not playing after load'); });
  // ending
  await step('ending', async () => { g._ending(); await wait(300); expectTop(S.dialogue, 'ending choice'); S.dialogue._skip(); S.dialogue._choose(0); await wait(900); expectTop(S.ending, 'ending'); S.ending._finish(); S.ending._quit(); await wait(300); if (a.state !== 'title') throw new Error('ending did not return to the title: ' + a.state); });

  removeEventListener('error', onErr);
  console.error = orig;
  return { ok: errors.length === 0, steps: steps.length, done: steps, errors };
}
