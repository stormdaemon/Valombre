// Minimal emergency UI, used only if src/ui/ui.js fails to load. Keeps the game playable.
import { bus } from './core/events.js';
import { ITEMS } from './game/data/items.js';
import { ATTRS, ORIGINS } from './game/data/rules.js';
import { randomAppearance } from './game/data/creator.js';

const el = (tag, css, html) => { const e = document.createElement(tag); if (css) e.style.cssText = css; if (html !== undefined) e.innerHTML = html; return e; };
const BTN = 'display:block;margin:8px auto;padding:10px 28px;background:#1b1712;color:#d9cdb4;border:1px solid #6b5a3a;font:18px Georgia,serif;cursor:pointer;min-width:260px';

export class FallbackUI {
  constructor(app) {
    this.app = app;
    const root = this.root = document.getElementById('ui');
    this.panel = el('div', 'position:absolute;inset:0;display:none;align-items:center;justify-content:center;flex-direction:column;background:rgba(5,5,8,.45);pointer-events:auto;color:#d9cdb4;font-family:Georgia,serif;text-align:center');
    this.hud = el('div', 'position:absolute;left:18px;bottom:18px;color:#e8e0cc;font:14px Georgia,serif;text-shadow:0 1px 3px #000;display:none;white-space:pre');
    this.prompt = el('div', 'position:absolute;left:50%;bottom:24%;transform:translateX(-50%);color:#fff;font:17px Georgia,serif;text-shadow:0 1px 4px #000');
    this.toasts = el('div', 'position:absolute;right:18px;top:18px;color:#e8e0cc;font:14px Georgia,serif;text-align:right;text-shadow:0 1px 3px #000');
    this.center = el('div', 'position:absolute;left:0;right:0;top:22%;text-align:center;color:#f0e6cc;font:34px Georgia,serif;letter-spacing:.2em;text-shadow:0 2px 8px #000');
    this.sub = el('div', 'position:absolute;left:10%;right:10%;bottom:8%;text-align:center;color:#eee;font:16px Georgia,serif;text-shadow:0 1px 4px #000');
    this.bossBar = el('div', 'position:absolute;left:25%;right:25%;top:40px;color:#f0e6cc;font:16px Georgia,serif;text-align:center;display:none');
    root.append(this.hud, this.prompt, this.toasts, this.center, this.sub, this.bossBar, this.panel);
    this.blockingNow = false; this.kind = '';
    bus.on('state', (s) => this._state(s));
    bus.on('toast', (t) => this._toast(t.kind === 'item' ? `+ ${(ITEMS[t.id] || {}).name || t.id}${t.qty > 1 ? ' ×' + t.qty : ''}` : t.kind === 'gold' ? `+ ${t.n} écus` : t.kind === 'xp' ? `+ ${t.n} XP` : t.kind === 'level' ? `Niveau ${t.level} !` : t.kind === 'quest' ? (t.done ? 'Quête accomplie : ' : 'Nouvelle quête : ') + t.title : t.kind === 'skill' ? 'Nouveau pouvoir' : t.text));
    bus.on('discover', (d) => this._banner(d.name));
    bus.on('banner', (d) => this._banner(d.title));
    bus.on('death', () => this._banner('VOUS AVEZ PÉRI', 4));
    bus.on('subtitle', (s) => { this.sub.textContent = s.text; clearTimeout(this._st); this._st = setTimeout(() => { this.sub.textContent = ''; }, (s.time || 5) * 1000); });
    bus.on('dialogue', () => this._dialogue());
    bus.on('open', (what) => { if (what === 'shrine') this._shrine(); else if (what === 'pause') this._pause(); else if (what === 'shop' || what === 'smith') this._simple(what); });
    bus.on('ending', (e) => this._banner(e.id === 'reforge' ? "L'AUBE ÉTERNELLE" : 'LE PREMIER MATIN', 12));
    window.addEventListener('keydown', (e) => { if (this.kind === 'dialogue' && e.code.startsWith('Digit')) { const g = this.app.game; if (g.dialogue) g.dialogue.choose(Number(e.code.slice(5)) - 1); } });
  }
  get blocking() { return this.blockingNow; }
  setLoading() {}
  _block(b, kind = '') { this.kind = b ? kind : ''; this.panel.style.display = b ? 'flex' : 'none'; if (b !== this.blockingNow) { this.blockingNow = b; this.app.setUiBlocking(b); } }
  _btn(label, fn) { const b = el('button', BTN, label); b.onclick = () => { this.app.sfx('ui_click'); fn(); }; this.panel.append(b); return b; }
  _toast(text) { const t = el('div', 'margin:3px 0;transition:opacity .6s', text); this.toasts.append(t); setTimeout(() => { t.style.opacity = 0; setTimeout(() => t.remove(), 700); }, 3200); }
  _banner(text, time = 3.5) { this.center.textContent = text; clearTimeout(this._bt); this._bt = setTimeout(() => { this.center.textContent = ''; }, time * 1000); }
  _state(s) {
    this.hud.style.display = s === 'playing' ? 'block' : 'none';
    if (s === 'title') {
      this.panel.innerHTML = '';
      this.panel.append(el('div', 'font-size:64px;letter-spacing:.3em;margin-bottom:6px', 'VALOMBRE'), el('div', 'opacity:.75;margin-bottom:34px', "Les Éclats de l'Aube"));
      if (this.app.saves.latest() >= 0) this._btn('Continuer', () => { this._block(false); this.app.continueGame(); });
      this._btn('Nouvelle partie', () => this.app.openCreator());
      this._block(true, 'title');
    } else if (s === 'creator') {
      this.panel.innerHTML = '';
      this.panel.style.background = 'none'; this.panel.style.justifyContent = 'flex-end';
      const name = el('input', 'font:18px Georgia,serif;padding:8px;background:#14110d;color:#d9cdb4;border:1px solid #6b5a3a;text-align:center;margin:6px'); name.value = 'Veilleur';
      const sel = el('select', 'font:16px Georgia,serif;padding:8px;background:#14110d;color:#d9cdb4;border:1px solid #6b5a3a;margin:6px');
      for (const o of ORIGINS) { const op = el('option', '', o.name); op.value = o.id; sel.append(op); }
      sel.onchange = () => this.app.creator.setOrigin(sel.value);
      this.panel.append(name, sel);
      this._btn('Apparence aléatoire', () => this.app.creator.setAll(randomAppearance(this.app.creator.morphs)));
      this._btn('Visage / Corps', () => this.app.creator.setView(this.app.creator.view === 'face' ? 'body' : 'face'));
      this._btn("Commencer l'aventure", () => { this.panel.style.background = 'rgba(5,5,8,.45)'; this.panel.style.justifyContent = 'center'; this._block(false); this.app.startNewGame({ name: name.value || 'Veilleur', origin: sel.value }); });
      this.panel.append(el('div', 'height:30px'));
      this._block(true, 'creator');
    } else if (s === 'playing') this._block(false);
  }
  _dialogue() {
    const d = this.app.game && this.app.game.dialogue;
    if (!d) { if (this.kind === 'dialogue') this._block(false); return; }
    this.panel.innerHTML = '';
    this.panel.append(el('div', 'font-size:22px;color:#e0803a;margin-bottom:8px', d.speaker), el('div', 'max-width:640px;font-size:17px;line-height:1.5;margin-bottom:18px', d.text));
    d.options.forEach((o, i) => this._btn(`${i + 1}. ${o.label}`, () => d.choose(i)));
    this._block(true, 'dialogue');
  }
  _shrine() {
    const g = this.app.game, p = g.player, d = p.data;
    const draw = () => {
      if (!g.shrine) { this._block(false); return; }
      this.panel.innerHTML = '';
      this.panel.append(el('div', 'font-size:26px;color:#e0803a;margin-bottom:10px', g.shrine.name), el('div', 'margin-bottom:12px', `Niveau ${d.level} — points à répartir : ${d.attrPoints}`));
      if (d.attrPoints > 0) for (const [id, label] of ATTRS) this._btn(`${label} ${d.attrs[id]} +`, () => { p.spendPoint(id); draw(); });
      if (g.shrine.flaskCountCost) this._btn('Ajouter une gorgée à la fiole', () => { g.shrineAction('flaskCount'); draw(); });
      if (g.shrine.flaskPowerCost) this._btn('Renforcer la fiole', () => { g.shrineAction('flaskPower'); draw(); });
      for (const s of g.map().shrines) if (s.found && s.id !== g.shrine.id) this._btn('Voyager : ' + s.name, () => { g.fastTravel(s.id); draw(); });
      this._btn("Quitter l'Autel", () => { g.shrineAction('leave'); this._block(false); });
    };
    draw(); this._block(true, 'shrine');
  }
  _simple(what) {
    const g = this.app.game;
    this.panel.innerHTML = '';
    if (what === 'shop' && g.shop) g.shop.stock.forEach((s, i) => this._btn(`${(ITEMS[s.id] || {}).name} — ${s.price} écus`, () => { g.shop.buy(i); }));
    if (what === 'smith' && g.smith) g.smith.list().forEach((e) => this._btn(`${(ITEMS[e.id] || {}).name} +${e.up} → +${e.up + 1} (${e.cost.gold} écus)`, () => { g.smith.upgrade(e.where); this._simple('smith'); }));
    this._btn('Fermer', () => { g.closePanel(); this._block(false); });
    this._block(true, what);
  }
  _pause() {
    this.panel.innerHTML = '';
    this.panel.append(el('div', 'font-size:30px;margin-bottom:16px', 'PAUSE'));
    this._btn('Reprendre', () => this._block(false));
    this._btn('Menu principal', () => { this._block(false); this.app.quitToTitle(); });
    this._block(true, 'pause');
  }
  update() {
    const app = this.app, g = app.game;
    if (app.state !== 'playing' || !g || !g.player) return;
    const p = g.player, d = p.data;
    this.hud.textContent = `Vie ${Math.ceil(p.hp)}/${p.maxHp}   Souffle ${Math.ceil(d.stamina)}/${p.st.maxSt}   Éclat ${Math.floor(d.mana)}/${p.st.maxMana}\nFioles ${d.flasks}/${d.flaskMax}   Écus ${d.gold}   Niv. ${d.level}   ${g.region.name}`;
    this.prompt.textContent = g.focus && !this.blockingNow ? `[${g.focus.key}] ${g.focus.label}` : '';
    if (g.boss) { this.bossBar.style.display = 'block'; this.bossBar.textContent = `${g.boss.def.name} — ${Math.ceil(g.boss.hp)} / ${g.boss.maxHp}`; } else this.bossBar.style.display = 'none';
    if (app.input.pressed('pause') && !this.blockingNow) this._pause();
  }
}
