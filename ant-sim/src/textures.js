// Procedural PBR textures drawn on canvases from seeded noise (deterministic, no image files).
import * as THREE from 'three';
import { rng } from './util.js';

// Tileable value noise + fBm on a periodic lattice.
function makeNoise(seed, period) {
  const R = rng(seed), g = new Float32Array(period * period);
  for (let i = 0; i < g.length; i++) g[i] = R();
  const at = (x, y) => g[((y % period + period) % period) * period + ((x % period + period) % period)];
  return (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    const a = at(xi, yi), b = at(xi + 1, yi), c = at(xi, yi + 1), d = at(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  };
}
function fbm(n, x, y, oct = 5) {
  let s = 0, a = 0.5, f = 1;
  for (let i = 0; i < oct; i++) { s += a * n(x * f, y * f); a *= 0.5; f *= 2; }
  return s;
}

function canvasTex(size, paint, { srgb = true, repeat = [1, 1] } = {}) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const ctx = c.getContext('2d');
  const img = ctx.createImageData(size, size);
  paint(img.data, size, ctx);
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repeat);
  t.anisotropy = 4;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Paint a colour field and a matching height field in one pass.
function pair(size, seed, fn) {
  const h = new Float32Array(size * size);
  const color = canvasTex(size, (d, S) => {
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const [r, g, b, height] = fn(x, y, S);
      const i = (y * S + x) * 4; d[i] = r; d[i + 1] = g; d[i + 2] = b; d[i + 3] = 255; h[y * S + x] = height;
    }
  });
  const bump = canvasTex(size, (d, S) => {
    for (let i = 0; i < S * S; i++) { const v = Math.max(0, Math.min(255, h[i] * 255)); d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = v; d[i * 4 + 3] = 255; }
  }, { srgb: false });
  return { color, bump };
}

const mix = (a, b, t) => a + (b - a) * t;

export function buildTextures() {
  const S = 256;
  const n1 = makeNoise(11, 16), n2 = makeNoise(12, 64), n3 = makeNoise(13, 8);

  // Lawn: mottled greens with dry flecks and clover-dark patches.
  const grass = pair(S, 1, (x, y) => {
    const big = fbm(n3, x / 32, y / 32, 3), mid = fbm(n1, x / 16, y / 16, 4), fine = n2(x / 4, y / 4);
    const t = big * 0.6 + mid * 0.4;
    let r = mix(52, 104, t), g = mix(92, 140, t), b = mix(30, 52, t);
    if (fine > 0.78) { r += 40; g += 30; b += 8; }
    if (fine < 0.18) { r *= 0.7; g *= 0.75; b *= 0.7; }
    return [r, g, b, fine * 0.6 + mid * 0.4];
  });

  // Gravel: packed fines with scattered stones (Voronoi-ish cells).
  const RS = rng(5), stones = Array.from({ length: 260 }, () => [RS() * S, RS() * S, 2 + RS() * 5, RS()]);
  const gravel = pair(S, 2, (x, y) => {
    let h = fbm(n2, x / 6, y / 6, 3) * 0.35, tone = 0;
    for (const [sx, sy, r, c] of stones) {
      let dx = Math.abs(x - sx), dy = Math.abs(y - sy); dx = Math.min(dx, S - dx); dy = Math.min(dy, S - dy);
      const d = Math.hypot(dx, dy) / r; if (d < 1) { const k = Math.sqrt(1 - d * d); if (k * 0.8 > h) { h = 0.35 + k * 0.6; tone = c; } }
    }
    const base = mix(160, 205, fbm(n1, x / 10, y / 10, 3));
    const st = tone ? mix(0.75, 1.15, tone) : 1;
    return [base * st, base * 0.93 * st, base * 0.78 * st, h];
  });

  // Brick with mortar joints, per-brick colour variation and surface grain.
  const RB = rng(7);
  const brickCols = Array.from({ length: 64 }, () => [150 + RB() * 50, 62 + RB() * 30, 45 + RB() * 20]);
  const brick = pair(S, 3, (x, y) => {
    const bh = S / 8, bw = S / 4, row = Math.floor(y / bh), off = row % 2 ? bw / 2 : 0;
    const col = Math.floor((x + off) / bw) % 4, lx = (x + off) % bw, ly = y % bh;
    const mortar = lx < 3 || ly < 3;
    const grain = n2(x / 2, y / 2);
    if (mortar) { const m = 175 + grain * 30; return [m, m * 0.96, m * 0.9, 0.1]; }
    const [r, g, b] = brickCols[(row * 4 + col) % 64];
    const k = 0.85 + grain * 0.3;
    return [r * k, g * k, b * k, 0.6 + grain * 0.4];
  });

  const asphalt = pair(S, 4, (x, y) => {
    const v = 50 + fbm(n2, x / 3, y / 3, 3) * 30 + (n1(x * 1.7, y * 1.7) > 0.85 ? 35 : 0);
    return [v, v * 1.02, v * 1.06, v / 120];
  });
  const concrete = pair(S, 5, (x, y) => {
    const v = 165 + fbm(n1, x / 8, y / 8, 4) * 40 - (n2(x, y) > 0.9 ? 30 : 0);
    return [v, v * 0.98, v * 0.94, fbm(n2, x / 3, y / 3, 2)];
  });
  const soil = pair(S, 6, (x, y) => {
    const t = fbm(n1, x / 12, y / 12, 5), f = n2(x / 2, y / 2);
    return [mix(55, 110, t) + f * 15, mix(36, 75, t) + f * 10, mix(22, 45, t), t * 0.7 + f * 0.3];
  });
  const stone = pair(S, 8, (x, y) => {
    const v = 205 + fbm(n1, x / 6, y / 6, 5) * 40;
    return [v, v * 0.97, v * 0.92, fbm(n2, x / 2, y / 2, 3)];
  });
  const bark = pair(S, 9, (x, y) => {
    const ridge = Math.abs(Math.sin(x / 6 + fbm(n1, x / 20, y / 40, 3) * 6));
    const v = 40 + ridge * 45 + n2(x / 2, y / 2) * 15;
    return [v * 1.1, v * 0.85, v * 0.6, ridge];
  });
  const leaf = pair(S, 10, (x, y) => {
    const t = fbm(n1, x / 5, y / 5, 4), f = n2(x / 1.5, y / 1.5);
    return [mix(30, 95, t) + f * 20, mix(60, 135, t) + f * 20, mix(22, 50, t), t];
  });
  // Chitin: fine pitting and micro-sculpture (height only).
  const chitin = canvasTex(S, (d, s) => {
    for (let i = 0; i < s * s; i++) { const x = i % s, y = (i / s) | 0; const v = (fbm(n2, x / 2.5, y / 2.5, 3) * 0.7 + (n1(x * 1.3, y * 1.3) > 0.8 ? 0.3 : 0)) * 255; d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = v; d[i * 4 + 3] = 255; }
  }, { srgb: false, repeat: [3, 3] });

  return { grass, gravel, brick, asphalt, concrete, soil, stone, bark, leaf, chitin };
}

// World-space planar UVs (metres / scale) for geometries without useful UVs.
export function planarUV(geo, scale = 1) {
  const p = geo.attributes.position, uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) { uv[i * 2] = p.getX(i) / scale; uv[i * 2 + 1] = p.getZ(i) / scale; }
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return geo;
}

// Clone a texture pair with its own repeat (shares the canvas image).
export function rep(pair, rx, ry) {
  const c = pair.color.clone(), b = pair.bump.clone();
  c.repeat.set(rx, ry); b.repeat.set(rx, ry); c.needsUpdate = b.needsUpdate = true;
  return { color: c, bump: b };
}

let TEX = null;
export const tex = () => TEX || (TEX = buildTextures());
