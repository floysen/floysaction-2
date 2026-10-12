// On-screen text, driven purely by t. Kept in the top safe area (platform UI sits at the bottom).
import { win, pulse, smooth, range } from './util.js';

const ITEMS = [
  { id: 'title', t0: 0, t1: 9.8, html: 'EVERY ANT.<br>HUMAN-SIZED.', cls: 'big', y: 250, fadeIn: 0 },
  { id: 'count', t0: 0.5, t1: 4.9, html: '≈20,000,000,000,000,000 ants<div class="sub">estimated alive on Earth today</div>', cls: 'mid', y: 520 },
  { id: 'nests', t0: 13.2, t1: 15.9, html: 'NESTS BUILT<br>FOR TINY BODIES', cls: 'mid', y: 300 },
  { id: 'density', t0: 22.6, t1: 26.3, html: '≈130+ PER m² OF LAND<div class="sub">rough average: ~20 quadrillion ÷ ~149 million km²</div>', cls: 'mid', y: 260 },
  { id: 'spir', t0: 32.8, t1: 40.0, html: 'SPIRACLES → TRACHEAE', cls: 'label', y: 300 },
  { id: 'lungs', t0: 34.6, t1: 40.0, html: 'NO LUNGS', cls: 'label', y: 390 },
  { id: 'o2', t0: 37.0, t1: 40.0, html: "O₂ CAN'T KEEP UP", cls: 'label warn', y: 480 },
  { id: 'cube', t0: 41.0, t1: 48.6, html: 'SIZE ×300 → WEIGHT ×27,000,000<div class="sub">square-cube law (approx.)</div>', cls: 'mid', y: 280 },
  { id: 'later', t0: 50.2, t1: 52.8, html: 'LATER…', cls: 'mid', y: 280 },
  { id: 'soil', t0: 52.6, t1: 57.0, html: 'SOIL', cls: 'word', y: 300, x: 270 },
  { id: 'seeds', t0: 53.9, t1: 57.0, html: 'SEEDS', cls: 'word', y: 300, x: 540 },
  { id: 'pests', t0: 55.1, t1: 57.0, html: 'PESTS', cls: 'word', y: 300, x: 810 },
  { id: 'final', t0: 57.3, t1: 60.5, html: "THE SCARIEST GIANT ANT<br>IS THE ONE THAT'S GONE.", cls: 'big', y: 300 },
];

export function buildOverlay(root) {
  const els = ITEMS.map((it) => {
    const d = document.createElement('div');
    d.className = 'ov ' + it.cls; d.innerHTML = it.html; d.style.top = it.y + 'px';
    if (it.x) { d.style.left = it.x + 'px'; d.style.width = 'auto'; d.style.transform = 'translateX(-50%)'; }
    root.appendChild(d); return d;
  });
  // 1 m² inset: about 130 dots in a square (illustrative of the average density).
  const inset = document.createElement('div'); inset.className = 'inset';
  inset.innerHTML = '<div class="sq"></div><div class="cap">1 m × 1 m</div>';
  const sq = inset.querySelector('.sq');
  for (let i = 0; i < 130; i++) {
    const dot = document.createElement('i');
    const gx = i % 12, gy = Math.floor(i / 12);
    dot.style.left = (8 + gx * 19 + (gy % 2) * 6) + 'px'; dot.style.top = (8 + gy * 21) + 'px';
    sq.appendChild(dot);
  }
  root.appendChild(inset);
  const fade = document.createElement('div'); fade.className = 'fade'; root.appendChild(fade);

  return function update(t) {
    ITEMS.forEach((it, i) => {
      const o = it.fadeIn === 0 && t < 0.3 ? 1 - smooth(range(t, it.t1 - 0.35, it.t1)) : win(t, it.t0, it.t1);
      els[i].style.opacity = o.toFixed(3);
      els[i].style.visibility = o > 0.002 ? 'visible' : 'hidden';
    });
    const io = win(t, 23.4, 26.3);
    inset.style.opacity = io.toFixed(3); inset.style.visibility = io > 0.002 ? 'visible' : 'hidden';
    const f = Math.max(pulse(t, 21.55, 22.25), pulse(t, 26.25, 26.95));
    fade.style.opacity = Math.min(1, f * 1.4).toFixed(3);
  };
}
