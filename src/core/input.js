// Input: keyboard + mouse (pointer lock) + gamepad -> named actions (rebindable, see settings.js ACTIONS).
import { bus } from './events.js';

const PAD_MAP = { 5: 'attack', 7: 'heavy', 4: 'block', 6: 'skill1', 3: 'skill2', 12: 'skill3', 1: 'dodge', 0: 'interact', 2: 'flask', 11: 'lock', 9: 'pause', 8: 'map', 13: 'sheathe', 14: 'journal', 15: 'inventory', 10: 'sprint' };
const NICE = {
  Space: 'Espace', ShiftLeft: 'Maj', ShiftRight: 'Maj droite', ControlLeft: 'Ctrl', ControlRight: 'Ctrl droite', AltLeft: 'Alt', AltRight: 'Alt Gr',
  Escape: 'Échap', Tab: 'Tab', Enter: 'Entrée', Backspace: 'Retour', CapsLock: 'Verr. maj',
  ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Mouse0: 'Clic gauche', Mouse1: 'Clic droit', Mouse2: 'Clic molette', Mouse3: 'Souris 4', Mouse4: 'Souris 5',
};

export class Input {
  constructor(canvas, settings) {
    this.canvas = canvas; this.settings = settings;
    this.codes = new Set();           // physical keys / buttons currently down
    this.act = {};                    // action -> held
    this.prev = {};
    this.virtual = {};                // actions forced down by tests / UI
    this.pulse = {};                  // actions pressed for one frame (tests)
    this.padDown = {};
    this.lookDX = 0; this.lookDY = 0; this.wheel = 0;
    this.moveX = 0; this.moveY = 0;   // -1..1 (x: right, y: forward)
    this.locked = false;
    this.gameEnabled = false;         // false while a menu is open
    this.usingPad = false;
    this.capture = null;              // rebinding: next key goes here
    this.layout = null;
    if (navigator.keyboard && navigator.keyboard.getLayoutMap) navigator.keyboard.getLayoutMap().then((m) => { this.layout = m; bus.emit('binds'); }).catch(() => {});
    this._rebuild();
    bus.on('binds', () => this._rebuild());

    window.addEventListener('keydown', (e) => this._key(e, true), true);
    window.addEventListener('keyup', (e) => this._key(e, false), true);
    canvas.addEventListener('mousedown', (e) => this._mouse(e, true));
    window.addEventListener('mouseup', (e) => this._mouse(e, false));
    window.addEventListener('mousemove', (e) => { if (this.locked) { this.lookDX += e.movementX; this.lookDY += e.movementY; } });
    canvas.addEventListener('wheel', (e) => { this.wheel += Math.sign(e.deltaY); e.preventDefault(); }, { passive: false });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === canvas;
      bus.emit('pointerlock', this.locked);
    });
    window.addEventListener('blur', () => { this.codes.clear(); });
  }

  _rebuild() {
    this.byCode = new Map();
    const b = this.settings.binds;
    for (const a in b) for (const c of b[a]) { if (!this.byCode.has(c)) this.byCode.set(c, []); this.byCode.get(c).push(a); }
  }

  _key(e, down) {
    if (this.capture && down) {
      e.preventDefault(); e.stopPropagation();
      const cb = this.capture; this.capture = null;
      cb(e.code === 'Escape' ? null : e.code);
      return;
    }
    const tag = e.target && e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (down) { if (!e.repeat) this.codes.add(e.code); } else this.codes.delete(e.code);
    if (this.byCode.has(e.code) && (this.gameEnabled || e.code === 'Tab' || e.code === 'Space' || e.code.startsWith('Arrow'))) e.preventDefault();
    if (down && !e.repeat) bus.emit('keydown', e.code, e);
    this.usingPad = false;
  }

  _mouse(e, down) {
    const code = 'Mouse' + e.button;
    if (this.capture && down) { const cb = this.capture; this.capture = null; cb(code); e.preventDefault(); return; }
    if (down) this.codes.add(code); else this.codes.delete(code);
    this.usingPad = false;
  }

  requestLock() {
    if (this.locked || !this.canvas.requestPointerLock) return;
    try { const p = this.canvas.requestPointerLock({ unadjustedMovement: true }); if (p && p.catch) p.catch(() => { try { this.canvas.requestPointerLock(); } catch (e) { /* needs a user gesture */ } }); } catch (e) { /* ignore */ }
  }

  exitLock() { if (document.pointerLockElement) document.exitPointerLock(); }

  /** call once per frame BEFORE game logic */
  update() {
    const b = this.settings.binds;
    // gamepad
    let px = 0, py = 0;
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const pad = pads && (pads[0] || pads[1] || pads[2] || pads[3]);
    for (const k in this.padDown) this.padDown[k] = false;
    if (pad && pad.connected) {
      const dz = (v) => (Math.abs(v) < 0.18 ? 0 : (v - Math.sign(v) * 0.18) / 0.82);
      px = dz(pad.axes[0] || 0); py = -dz(pad.axes[1] || 0);
      const rx = dz(pad.axes[2] || 0), ry = dz(pad.axes[3] || 0);
      const ps = this.settings.values.padSens / 100;
      if (rx || ry) { this.lookDX += rx * 14 * ps; this.lookDY += ry * 10 * ps; this.usingPad = true; }
      if (px || py) this.usingPad = true;
      for (const i in PAD_MAP) { const bt = pad.buttons[i]; if (bt && (bt.pressed || bt.value > 0.45)) { this.padDown[PAD_MAP[i]] = true; this.usingPad = true; } }
      this.pad = pad;
    }
    for (const a in b) {
      this.prev[a] = this.act[a] || false;
      let d = false;
      for (const c of b[a]) if (this.codes.has(c)) { d = true; break; }
      this.act[a] = d || !!this.padDown[a] || !!this.virtual[a] || !!this.pulse[a];
    }
    for (const k in this.pulse) this.pulse[k] = false;
    let mx = (this.act.right ? 1 : 0) - (this.act.left ? 1 : 0), my = (this.act.forward ? 1 : 0) - (this.act.back ? 1 : 0);
    if (px || py) { mx = px; my = py; }
    const l = Math.hypot(mx, my);
    if (l > 1) { mx /= l; my /= l; }
    this.moveX = mx; this.moveY = my;
  }

  /** call once per frame AFTER game logic */
  endFrame() { this.lookDX = 0; this.lookDY = 0; this.wheel = 0; }

  down(a) { return !!this.act[a]; }
  pressed(a) { return !!this.act[a] && !this.prev[a]; }
  released(a) { return !this.act[a] && !!this.prev[a]; }

  /** tests / UI: press an action for one frame */
  tap(a) { this.pulse[a] = true; }

  rumble(strong = 0.5, weak = 0.5, ms = 120) {
    if (!this.usingPad || !this.settings.values.vibration || !this.pad || !this.pad.vibrationActuator) return;
    try { this.pad.vibrationActuator.playEffect('dual-rumble', { duration: ms, strongMagnitude: strong, weakMagnitude: weak }); } catch (e) { /* unsupported */ }
  }

  /** human label of a key code, following the real keyboard layout (AZERTY shows Z Q S D) */
  label(code) {
    if (!code) return '—';
    if (NICE[code]) return NICE[code];
    if (this.layout && this.layout.has(code)) return this.layout.get(code).toUpperCase();
    if (code.startsWith('Key')) return code.slice(3);
    if (code.startsWith('Digit')) return code.slice(5);
    if (code.startsWith('Numpad')) return 'Pavé ' + code.slice(6);
    return code;
  }

  /** label of the first binding of an action */
  actionLabel(a) { const l = this.settings.binds[a]; return l && l.length ? this.label(l[0]) : '—'; }
}
