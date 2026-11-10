// VALOMBRE — user interface entry point. Plain DOM + CSS layered over the WebGL canvas (see CONTRACT.md).
import { bus } from '../core/events.js';
import { add, h } from './dom.js';
import { Hud } from './hud.js';
import { TitleScreen, SavesScreen, CreditsScreen } from './title.js';
import { OptionsScreen } from './options.js';
import { CreatorScreen } from './creator.js';
import { HubScreen } from './hub.js';
import { ShrineScreen, ShopScreen, SmithScreen, DialogueScreen } from './services.js';
import { LoadingOverlay, PauseScreen, ConfirmScreen, DeathOverlay, EndingScreen } from './overlays.js';

const HUB_ACTIONS = ['inventory', 'character', 'map', 'journal'];
const UI_ACTIONS = ['pause', 'inventory', 'character', 'map', 'journal', 'hideHud'];
const SERVICES = { shrine: 'shrine', shop: 'shop', smith: 'smith', dialogue: 'dialogue' };

export class UI {
  constructor(app) {
    this.app = app;
    let root = document.getElementById('ui');
    if (!root) {
      root = document.createElement('div'); root.id = 'ui';
      root.style.cssText = 'position:fixed;inset:0;pointer-events:none';
      document.body.appendChild(root);
    }
    this.root = root;
    root.classList.add('v-ui');
    this._loadCss();

    this.hudLayer = h('div.v-layer.v-layer-hud');
    this.screenLayer = h('div.v-layer.v-layer-screens');
    this.topLayer = h('div.v-layer.v-layer-top');
    add(root, this.hudLayer, this.screenLayer, this.topLayer);

    this.rem = 16;
    this.stack = [];
    this.screens = {};
    this.hudHidden = false;
    this.capturing = false;
    this._blocking = null;
    this._state = null;
    this._backT = 0; this._navT = 0; this._padT = 0; this._padDir = 0;
    this._rawKeys = new Set();          // key codes currently down, as seen by our own listener
    this._rawActs = {};                 // interface actions already handled from a raw keydown
    this._errLogged = false;
    this._hoverEl = null;

    this.hud = new Hud(this);
    this.loading = new LoadingOverlay(this);
    this.death = new DeathOverlay(this);
    for (const S of [TitleScreen, SavesScreen, CreditsScreen, OptionsScreen, CreatorScreen, PauseScreen, HubScreen, ShrineScreen, ShopScreen, SmithScreen, DialogueScreen, EndingScreen, ConfirmScreen]) {
      try { const s = new S(this); this.screens[s.name] = s; } catch (e) { console.error('[ui] screen init failed', S && S.name, e); }
    }

    this._bind();
    this._measure();
    this._applyState(app.state || 'boot', null);
  }

  // ------------------------------------------------------------------------------------ public API
  update(dt) {
    try { this._update(Math.min(Math.max(Number(dt) || 0, 0), 0.25)); }
    catch (e) { if (!this._errLogged) { this._errLogged = true; console.error('[ui] update failed', e); } }
  }

  setLoading(p, text) {
    try { this.loading.set(p, text); if (this.app.state === 'boot') this.loading.show(); } catch (e) { /* never break the boot */ }
  }

  get blocking() {
    return this.app.state !== 'playing' || this.stack.length > 0;
  }

  // ------------------------------------------------------------------------------------- helpers
  get game() { return this.app.game || null; }
  get top() { return this.stack.length ? this.stack[this.stack.length - 1] : null; }
  isOpen(name) { const s = this.screens[name]; return !!s && s.isOpen; }

  sfx(name) { try { if (typeof this.app.sfx === 'function') this.app.sfx(name); } catch (e) { /* audio is optional */ } }

  setting(key, fallback) {
    try { const v = this.app.settings.get(key); return v === undefined ? fallback : v; } catch (e) { return fallback; }
  }

  keyLabel(action) {
    try { return this.app.input.actionLabel(action); } catch (e) { return '—'; }
  }

  confirm(opts = {}) {
    return new Promise((resolve) => { this.open('confirm', { ...opts, resolve }); });
  }

  open(name, args) {
    const s = this.screens[name];
    if (!s) return null;
    if (s.isOpen) {
      // already somewhere in the stack: bring it back to the top
      while (this.top && this.top !== s) this.close(this.top, true);
      try { s.onOpen(args || {}); } catch (e) { console.error('[ui] open', name, e); }
      this._sync();
      return s;
    }
    const prev = this.top;
    if (prev) {
      prev._focus = prev.el.contains(document.activeElement) ? document.activeElement : null;
      if (!s.overlay) prev.el.classList.add('under');
    }
    this.stack.push(s);
    s.isOpen = true;
    s.el.hidden = false;
    s.el.classList.remove('under');
    try { s.onOpen(args || {}); } catch (e) { console.error('[ui] open', name, e); }
    if (!s.root) this.sfx('ui_open');
    this._sync();
    this._focusDefault(s);
    return s;
  }

  close(screen, silent) {
    const s = screen || this.top;
    if (!s || !s.isOpen) return;
    const i = this.stack.indexOf(s);
    if (i < 0) return;
    this.stack.splice(i, 1);
    s.isOpen = false;
    s.el.hidden = true;
    try { s.onClose(); } catch (e) { console.error('[ui] close', s.name, e); }
    const top = this.top;
    if (top) {
      top.el.classList.remove('under');
      try { top.onResume(); } catch (e) { console.error('[ui] resume', top.name, e); }
      const f = top._focus;
      if (f && f.isConnected && top.el.contains(f) && !f.disabled) this._focus(f); else this._focusDefault(top);
    } else if (document.activeElement && this.root.contains(document.activeElement)) document.activeElement.blur();
    if (!silent) this.sfx('ui_close');
    this._sync();
  }

  closeAll() {
    while (this.stack.length) this.close(this.top, true);
  }

  /** "back" request (Échap, pad B, pause action) */
  back() {
    const now = performance.now();
    if (now - this._backT < 40) return;          // same press reported by two sources
    this._backT = now;
    const top = this.top;
    if (!top) {
      const g = this.game;
      if (this.app.state === 'playing' && !(g && g.player && g.player.dead)) this.open('pause');
      return;
    }
    let handled = false;
    try { handled = top.onBack(); } catch (e) { console.error(e); }
    if (handled) return;
    if (top.root) return;
    this.sfx('ui_back');
    this.close(top, true);
  }

  // ------------------------------------------------------------------------------------ internals
  _loadCss() {
    if (document.querySelector('link[data-valombre-ui]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = new URL('./ui.css', import.meta.url).href;
    link.dataset.valombreUi = '';
    this.root.style.visibility = 'hidden';
    const show = () => {
      if (this.root.style.visibility !== 'hidden') return;
      this.root.style.visibility = '';
      this._measure();
      const top = this.top;                       // nothing can take the focus while the layer is hidden
      if (top && !this.root.contains(document.activeElement)) this._focusDefault(top);
    };
    link.addEventListener('load', show);
    link.addEventListener('error', show);
    setTimeout(show, 1500);
    document.head.appendChild(link);
  }

  _measure() {
    const fs = parseFloat(getComputedStyle(this.root).fontSize);
    this.rem = fs > 0 ? fs : 16;
    this.vw = window.innerWidth; this.vh = window.innerHeight;
    // fewer than 74 x 41.5 rem on screen (large interface scale or small window): tighter layouts
    this.root.classList.toggle('v-compact', this.vw / this.rem < 74 || this.vh / this.rem < 41.5);
    if (this.hud) this.hud.onResize();
    for (const s of this.stack) if (s.onResize) s.onResize();
  }

  _bind() {
    const on = (t, fn) => bus.on(t, (a, b) => { try { fn(a, b); } catch (e) { console.error('[ui] bus ' + t, e); } });
    on('state', (now, old) => this._applyState(now, old));
    on('open', (what) => this._onOpenRequest(what));
    on('dialogue', () => this._onDialogue());
    on('death', () => { this.closeAll(); this.death.show(); });
    on('respawn', () => this.death.hide());
    on('ending', (e) => { this.closeAll(); this.death.hide(); this.open('ending', e || {}); });
    on('settings', (k, v) => { this._measureSoon(); this.hud.onSettings(k, v); this._each('settings', k); });
    on('binds', () => { this.hud.onBinds(); this._each('binds'); });
    for (const t of ['inventory', 'player:stats', 'player:xp', 'player:flask', 'player:buffs', 'quest']) on(t, () => { this.hud.onHint(t); this._each(t); });

    window.addEventListener('keydown', (e) => this._onKeyDown(e));
    window.addEventListener('keyup', (e) => this._rawKeys.delete(e.code));
    window.addEventListener('blur', () => { this._rawKeys.clear(); this._rawActs = {}; });
    window.addEventListener('resize', () => this._measure());
    this.root.addEventListener('click', (e) => {
      const t = e.target.closest && e.target.closest('button,[data-nav]');
      if (t && !t.disabled && !t.hasAttribute('data-quiet')) this.sfx('ui_click');
    });
    this.root.addEventListener('mouseover', (e) => {
      const t = e.target.closest && e.target.closest('[data-nav]');
      if (t === this._hoverEl) return;
      this._hoverEl = t;
      if (t && !t.disabled) {
        this.sfx('ui_hover');
        if (t.classList.contains('v-menu-item')) this._focus(t, true);
      }
    });
    this.root.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  _each(type, arg) {
    for (const s of this.stack) { try { s.onEvent(type, arg); } catch (e) { console.error('[ui] event', s.name, type, e); } }
  }

  _measureSoon() {
    if (this._mt) return;
    this._mt = setTimeout(() => { this._mt = 0; this._measure(); }, 60);
  }

  _applyState(now, old) {
    if (now === this._state) return;
    this._state = now;
    this.closeAll();
    this.death.hide();
    if (now === 'boot') this.loading.show(); else this.loading.hide();
    if (now === 'title') this.open('title');
    else if (now === 'creator') this.open('creator');
    this.hudHidden = false;
    this.hud.reset();
    this._sync();
  }

  _sync() {
    const b = this.blocking;
    if (b !== this._blocking) {
      this._blocking = b;
      try { this.app.setUiBlocking(b); } catch (e) { console.error('[ui] setUiBlocking', e); }
    }
    this.hud.setVisible(this.app.state === 'playing' && this.stack.length === 0 && !this.hudHidden);
    this.root.classList.toggle('v-has-screen', this.stack.length > 0);
  }

  _onOpenRequest(what) {
    if (this.app.state !== 'playing' || !this.game) return;
    if (what === 'pause') { if (!this.stack.length) this.open('pause'); return; }
    if (HUB_ACTIONS.includes(what)) { this.open('hub', { tab: what }); return; }
    if (SERVICES[what]) {
      // a service replaces whatever was open (dialogue -> shop, etc.)
      if (what !== 'shrine') this.closeAll();
      this.open(SERVICES[what]);
    }
  }

  _onDialogue() {
    const g = this.game;
    const d = g && g.dialogue;
    const s = this.screens.dialogue;
    if (!s) return;
    if (d) { if (s.isOpen) s.refresh(); else if (this.app.state === 'playing') this.open('dialogue'); }
    else if (s.isOpen) this.close(s, true);
  }

  _focus(el, quiet) {
    if (!el || el === document.activeElement) return;
    try { el.focus({ preventScroll: true }); } catch (e) { return; }
    if (!quiet && el.scrollIntoView) { try { el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e) { /* old browsers */ } }
  }

  _focusDefault(s) {
    let el = null;
    try { el = s.defaultFocus(); } catch (e) { /* ignore */ }
    if (el) this._focus(el, true);
    else if (document.activeElement && this.root.contains(document.activeElement)) document.activeElement.blur();
  }

  _navigable(s) {
    const out = [];
    const list = s.el.querySelectorAll('[data-nav]');
    for (let i = 0; i < list.length; i++) {
      const el = list[i];
      if (el.disabled || el.getClientRects().length === 0) continue;
      out.push(el);
    }
    return out;
  }

  /** spatial navigation: dx, dy in {-1, 0, 1} */
  nav(dx, dy, big) {
    const top = this.top;
    if (!top) return;
    const cur = document.activeElement;
    const inTop = cur && top.el.contains(cur) && cur.hasAttribute('data-nav');
    if (dx && inTop && typeof cur._adjust === 'function') { cur._adjust(dx, big); this.sfx('ui_slider'); return; }
    const list = this._navigable(top);
    if (!list.length) return;
    if (!inTop) { this._focus(top.defaultFocus() || list[0]); return; }
    const r = cur.getBoundingClientRect();
    let best = null, bs = 1e12;
    for (const el of list) {
      if (el === cur) continue;
      const q = el.getBoundingClientRect();
      let primary, gap;
      if (dy) {
        primary = dy > 0 ? q.top - r.bottom : r.top - q.bottom;
        if ((dy > 0 ? q.top + q.height * 0.5 <= r.top + r.height * 0.5 : q.top + q.height * 0.5 >= r.top + r.height * 0.5) || primary < -r.height * 0.5) continue;
        gap = Math.max(0, q.left - r.right, r.left - q.right);
        if (gap === 0) gap = Math.abs((q.left + q.right) - (r.left + r.right)) * 0.02;
      } else {
        primary = dx > 0 ? q.left - r.right : r.left - q.right;
        if ((dx > 0 ? q.left + q.width * 0.5 <= r.left + r.width * 0.5 : q.left + q.width * 0.5 >= r.left + r.width * 0.5) || primary < -r.width * 0.5) continue;
        gap = Math.max(0, q.top - r.bottom, r.top - q.bottom);
        if (gap === 0) gap = Math.abs((q.top + q.bottom) - (r.top + r.bottom)) * 0.02;
      }
      const score = Math.max(primary, 0) + gap * 3;
      if (score < bs) { bs = score; best = el; }
    }
    if (best) { this._focus(best); this.sfx('ui_hover'); }
  }

  _activate(el) {
    if (!el || el.disabled) return;
    if (typeof el._activate === 'function') el._activate(); else el.click();
  }

  /** the rebindable interface action bound to a key code, if any */
  _actionOf(code) {
    const b = this.app.settings && this.app.settings.binds;
    if (!b) return null;
    for (const a of UI_ACTIONS) if (b[a] && b[a].includes(code)) return a;
    return null;
  }

  _rawDown(a) {
    const b = this.app.settings && this.app.settings.binds;
    const list = b && b[a];
    if (!list) return false;
    for (const c of list) if (this._rawKeys.has(c)) return true;
    return false;
  }

  /** pause / inventory / character / map / journal / hideHud. Returns true when something happened. */
  _uiAction(a) {
    if (a === 'pause') { this.back(); return true; }
    const g = this.game;
    if (this.app.state !== 'playing' || !g || !g.player || g.player.dead) return false;
    if (a === 'hideHud') {
      if (this.stack.length) return false;
      this.hudHidden = !this.hudHidden; this._sync();
      return true;
    }
    if (HUB_ACTIONS.includes(a)) {
      const hub = this.screens.hub;
      if (hub && hub.isOpen && this.top === hub) {
        if (hub.tab === a) { this.sfx('ui_close'); this.close(hub, true); } else hub.setTab(a);
        return true;
      }
      if (!this.top || this.top.name === 'pause') { this.open('hub', { tab: a }); return true; }
    }
    return false;
  }

  _onKeyDown(e) {
    // note: the Input already calls preventDefault() on bound keys (arrows, Tab…), so defaultPrevented means nothing here
    if (this.capturing) return;
    const top = this.top;
    const t = e.target;
    const inField = !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA');
    if (!e.repeat) this._rawKeys.add(e.code);
    if (top) {
      let handled = false;
      try { handled = !inField && top.onKey(e) === true; } catch (err) { console.error(err); }
      if (handled) { e.preventDefault(); return; }
    }
    // Interface actions are taken from the raw key event (a short tap can fall between two frames at low frame
    // rates and never show up in input.pressed); update() then ignores the same press coming through the Input.
    const menuKey = !!top && (e.code.startsWith('Arrow') || e.code === 'Enter' || e.code === 'NumpadEnter' || e.code === 'Space');
    if (!inField && !e.repeat && !menuKey) {
      const act = this._actionOf(e.code);
      if (act) {
        this._rawActs[act] = true;
        if (this._uiAction(act)) { e.preventDefault(); return; }
        if (e.code !== 'Escape') return;
      }
    }
    if (!top) {
      if (e.code === 'Escape' && this.app.state === 'playing' && !e.repeat) { this.back(); e.preventDefault(); }
      return;
    }
    switch (e.code) {
      case 'Escape':
        if (inField) t.blur(); else if (!e.repeat) this.back();
        e.preventDefault();
        break;
      case 'ArrowUp': this._navT = performance.now(); this.nav(0, -1); e.preventDefault(); break;
      case 'ArrowDown': this._navT = performance.now(); this.nav(0, 1); e.preventDefault(); break;
      case 'ArrowLeft': if (!inField) { this._navT = performance.now(); this.nav(-1, 0, e.shiftKey); e.preventDefault(); } break;
      case 'ArrowRight': if (!inField) { this._navT = performance.now(); this.nav(1, 0, e.shiftKey); e.preventDefault(); } break;
      case 'Enter': case 'NumpadEnter': case 'Space': {
        if (inField) { if (e.code !== 'Space') { t.blur(); e.preventDefault(); } break; }
        const a = document.activeElement;
        if (a && top.el.contains(a) && a.hasAttribute('data-nav') && a.tagName !== 'BUTTON') { this._activate(a); e.preventDefault(); }
        else if (e.code === 'Space') e.preventDefault();
        break;
      }
      case 'Tab': e.preventDefault(); break;
      default:
    }
  }

  _fieldFocused() {
    const a = document.activeElement;
    return !!a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA');
  }

  _update(dt) {
    const app = this.app, inp = app.input;
    if (app.state !== this._state) this._applyState(app.state, this._state);
    const playing = app.state === 'playing';
    const g = playing ? this.game : null;

    // ---- interface actions coming through the Input (gamepad, mouse buttons, or keys we did not see ourselves)
    if (typeof app.blocking === 'boolean' && app.blocking !== this.blocking) { this._blocking = null; this._sync(); }   // safety net
    if (inp && !this.capturing && !this._fieldFocused()) {
      for (let i = 0; i < UI_ACTIONS.length; i++) {
        const a = UI_ACTIONS[i];
        if (inp.pressed(a)) { if (this._rawActs[a]) this._rawActs[a] = false; else this._uiAction(a); }
        else if (this._rawActs[a] && !inp.down(a) && !this._rawDown(a)) this._rawActs[a] = false;
      }
      const top = this.top;
      // gamepad menu navigation
      if (top && inp.usingPad) {
        const mx = Math.abs(inp.moveX) > 0.55 ? Math.sign(inp.moveX) : 0, my = Math.abs(inp.moveY) > 0.55 ? Math.sign(inp.moveY) : 0;
        const dir = my ? (my > 0 ? 1 : 2) : mx ? (mx > 0 ? 3 : 4) : 0;
        if (dir !== this._padDir) { this._padDir = dir; this._padT = 0.38; if (dir) this._padNav(dir); }
        else if (dir) { this._padT -= dt; if (this._padT <= 0) { this._padT = 0.13; this._padNav(dir); } }
        if (inp.pressed('interact')) { const a = document.activeElement; if (a && top.el.contains(a)) this._activate(a); }
        if (inp.pressed('dodge')) this.back();
      } else this._padDir = 0;
    }

    // ---- service screens follow the game objects
    if (this.stack.length) {
      const sv = this.screens;
      if (sv.shrine && sv.shrine.isOpen && !(g && g.shrine)) this._drop(sv.shrine);
      if (sv.shop && sv.shop.isOpen && !(g && g.shop)) this._drop(sv.shop);
      if (sv.smith && sv.smith.isOpen && !(g && g.smith)) this._drop(sv.smith);
      if (sv.dialogue && sv.dialogue.isOpen && !(g && g.dialogue)) this._drop(sv.dialogue);
      const top = this.top;
      if (top) top.update(dt);
    }

    // ---- death overlay safety net (in case the events were missed)
    if (g && g.player) { if (g.player.dead && !this.death.on && !this.isOpen('ending')) { this.closeAll(); this.death.show(); } else if (!g.player.dead && this.death.on) this.death.hide(); }
    else if (this.death.on) this.death.hide();

    this.hud.update(dt, g);
  }

  _padNav(dir) {
    if (performance.now() - this._navT < 160) return;
    if (dir === 1) this.nav(0, -1); else if (dir === 2) this.nav(0, 1); else if (dir === 3) this.nav(1, 0); else this.nav(-1, 0);
  }

  /** a service ended on the game side: remove its screen and anything opened on top of it */
  _drop(s) {
    while (this.top && this.top !== s) this.close(this.top, true);
    this.close(s, true);
  }
}

export default UI;
