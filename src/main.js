// VALOMBRE — entry point.
import { App } from './app.js';

const bootMsg = document.getElementById('bootmsg');
window.addEventListener('error', (e) => { window.__lastError = e.message + ' @ ' + (e.filename || '') + ':' + e.lineno; });
window.addEventListener('unhandledrejection', (e) => { window.__lastError = String(e.reason && e.reason.stack ? e.reason.stack : e.reason); });

const app = new App(document.getElementById('game'));
window.__app = app;
app.boot().then(() => {
  // test hooks (used by automated checks; harmless in normal play)
  window.__step = (n = 60, dt = 1 / 60) => { for (let i = 0; i < n; i++) { app.input.gameEnabled = true; app.input.update(); app.game.update(dt); app.engine.update(dt); app.input.endFrame(); } };
  const p = app.params;
  if (p.has('play')) {
    app.startNewGame({ name: 'Test', origin: p.get('play') || 'veilleur' });
    if (app.ui && app.ui._block) app.ui._block(false);
    const g = app.game;
    if (p.has('pos')) { const [x, z] = p.get('pos').split(',').map(Number); g.player.pos.set(x, g.collision.ground(x, z), z); g.cam.snap(g.player.yaw); }
    if (p.has('t')) app.engine.atmo.hour = Number(p.get('t'));
    if (p.has('freeze')) app.engine.atmo.timeScale = 0;
  }
}).catch((e) => {
  console.error(e);
  window.__bootError = String(e && e.stack ? e.stack : e);
  if (bootMsg) { bootMsg.textContent = 'Erreur de chargement : ' + (e && e.message ? e.message : e); bootMsg.style.color = '#e07060'; }
});
