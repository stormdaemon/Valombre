// VALOMBRE UI — base class of every blocking screen (title, options, panels…).
import { h } from './dom.js';

export class Screen {
  /**
   * @param ui    the UI instance
   * @param name  registry key (ui.open(name))
   * @param cls   extra class of the root element
   * opts: root (cannot be closed with Échap), overlay (the screen below stays visible)
   */
  constructor(ui, name, cls = '', opts = {}) {
    this.ui = ui; this.app = ui.app; this.name = name;
    this.root = !!opts.root; this.overlay = !!opts.overlay;
    this.el = h('div.v-screen' + (cls ? '.' + cls : ''), { hidden: true, 'data-screen': name });
    ui.screenLayer.appendChild(this.el);
    this.isOpen = false;
  }
  get game() { return this.app.game || null; }
  onOpen() {}
  onClose() {}
  onResume() {}
  /** return true when the "back" request was consumed */
  onBack() { return false; }
  /** raw keydown; return true when handled */
  onKey() { return false; }
  /** bus refresh hints ('inventory', 'player:stats', 'quest', 'settings', 'binds'…) */
  onEvent() {}
  update() {}
  defaultFocus() { return this.el.querySelector('[data-nav]:not([disabled])'); }
}

/** panel frame with ornamental corners */
export function panel(cls, ...kids) {
  return h('div.v-panel' + (cls ? '.' + cls : ''), null, h('i.v-corners'), ...kids);
}

export function rule(cls) { return h('div.v-rule' + (cls ? '.' + cls : '')); }

/** key cap + label hint ("[Échap] Retour") */
export function hint(key, label) {
  return h('span.v-hint', null, h('kbd.v-key', { text: key }), h('span', { text: label }));
}
