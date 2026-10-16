// "How a hole in your yard becomes a toilet" - realistic 3D cut-away, three.js.
// Every event time comes from data/events.json (generated from the voiceover timing).
import { THREE, Stage, cutGround, box, grassTufts, tree, palm, clouds, cameraPath, captions,
         smooth, lin, pop, lerp, clamp, rng } from '../lib/engine.js';

const EV = await (await fetch('data/events.json')).json();
const E = EV.events;
export const duration = EV.duration;

// ------------------------------------------------------------------ shared materials
let S, M;
function materials() {
  M = {
    soil: S.pbr('soil', { tile: 3.5, normalScale: 2.4 }),
    lawn: S.pbr('grass', { tile: 2.5, normalScale: 1.2 }),
    plaster: S.pbr('plaster', { tile: 3, normalScale: 0.6 }),
    trim: S.pbr('plaster', { tile: 2, color: 0xc8a676 }),
    stone: S.pbr('stone', { tile: 2.4, normalScale: 1.2 }),
    wood: S.pbr('wood', { tile: 1.6, normalScale: 1.0 }),
    conc: S.pbr('concrete', { tile: 2, normalScale: 0.9 }),
    asphalt: S.pbr('asphalt', { tile: 2, normalScale: 0.8 }),
    tiles: S.pbr('tiles', { tile: 1.0, normalScale: 0.8, color: 0xdde3e8 }),
    floor: S.pbr('floortile', { tile: 1.6, normalScale: 0.7 }),
    brick: S.pbr('brick', { tile: 1.2, normalScale: 1.2 }),
    paint: new THREE.MeshStandardMaterial({ color: 0xc9d5dc, roughness: 0.9 }),
    band: new THREE.MeshStandardMaterial({ color: 0x2f6fa8, roughness: 0.35 }),
    porcelain: new THREE.MeshPhysicalMaterial({ color: 0xf7f9fb, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08 }),
    porcelainCut: new THREE.MeshStandardMaterial({ color: 0xb9c4cf, roughness: 0.6 }),
    pvc: new THREE.MeshPhysicalMaterial({ color: 0xf2f6fa, roughness: 0.15, transmission: 0.55, thickness: 0.05, transparent: true, opacity: 0.85 }),
    pvcSolid: new THREE.MeshStandardMaterial({ color: 0xeef2f5, roughness: 0.35 }),
    water: new THREE.MeshPhysicalMaterial({ color: 0x3fb2ea, roughness: 0.05, transmission: 0.25, transparent: true, opacity: 0.85, ior: 1.33, thickness: 0.3 }),
    waterFlow: new THREE.MeshStandardMaterial({ color: 0x2fa8e6, roughness: 0.1, emissive: 0x0d5f96, emissiveIntensity: 0.45, transparent: true, opacity: 0.95 }),
    waste: new THREE.MeshStandardMaterial({ color: 0x5a3818, roughness: 0.55 }),
    gas: new THREE.MeshStandardMaterial({ color: 0x9be05a, emissive: 0x5fb52a, emissiveIntensity: 0.9, transparent: true, opacity: 0.55, depthWrite: false }),
    glow: new THREE.MeshBasicMaterial({ color: 0xffd34a, transparent: true, opacity: 0.95 }),
    white: new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.6, roughness: 0.4 }),
    red: new THREE.MeshStandardMaterial({ color: 0xe23b2e, emissive: 0x8a1208, emissiveIntensity: 0.6, roughness: 0.4 }),
    rubber: new THREE.MeshStandardMaterial({ color: 0xc8352b, roughness: 0.6 }),
    brass: new THREE.MeshStandardMaterial({ color: 0xd9a440, metalness: 1, roughness: 0.28 }),
    chrome: new THREE.MeshStandardMaterial({ color: 0xe9edf1, metalness: 1, roughness: 0.15 }),
    metal: new THREE.MeshStandardMaterial({ color: 0xa6adb4, metalness: 0.9, roughness: 0.35 }),
    glass: new THREE.MeshPhysicalMaterial({ color: 0x1f3448, roughness: 0.05, metalness: 0.2, clearcoat: 1 }),
    frame: new THREE.MeshStandardMaterial({ color: 0xf2ece0, roughness: 0.5 }),
    gravel: new THREE.MeshStandardMaterial({ color: 0x9a948a, roughness: 0.9 }),
    dark: new THREE.MeshStandardMaterial({ color: 0x1b1f24, roughness: 0.6 }),
  };
}

const add = (o, parent) => { (parent || S.scene).add(o); return o; };
const mesh = (g, m, x = 0, y = 0, z = 0, parent) => { const o = new THREE.Mesh(g, m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; return add(o, parent); };
const V = (x, y, z) => new THREE.Vector3(x, y, z);

function arrowMesh(mat, len = 0.5, rad = 0.05) {
  const g = new THREE.Group();
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(rad, rad, len * 0.6, 12), mat); shaft.position.y = len * 0.3;
  const head = new THREE.Mesh(new THREE.ConeGeometry(rad * 2.4, len * 0.4, 16), mat); head.position.y = len * 0.8;
  g.add(shaft, head);
  return g;
}

function redX(size = 0.6) {
  const g = new THREE.Group();
  for (const a of [Math.PI / 4, -Math.PI / 4]) { const b = new THREE.Mesh(new THREE.BoxGeometry(size, size * 0.16, size * 0.16), M.red); b.rotation.z = a; g.add(b); }
  return g;
}

function ring(r = 0.3, tube = 0.02) { return new THREE.Mesh(new THREE.TorusGeometry(r, tube, 12, 64), M.glow); }

// tube along points, rebuilt on demand (for animated water / contents)
function dynTube(mat, radius, parent) {
  const m = new THREE.Mesh(new THREE.BufferGeometry(), mat); m.castShadow = false; m.receiveShadow = false;
  add(m, parent);
  m.setPoints = (pts) => {
    m.geometry.dispose();
    if (!pts || pts.length < 2) { m.geometry = new THREE.BufferGeometry(); return; }
    const c = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.1);
    m.geometry = new THREE.TubeGeometry(c, Math.max(8, pts.length * 3), radius, 14, false);
  };
  return m;
}

function samplePolyline(pts, n = 120) {
  // resample a polyline (Vector3[]) uniformly by length
  const seg = []; let tot = 0;
  for (let i = 1; i < pts.length; i++) { const d = pts[i].distanceTo(pts[i - 1]); seg.push(d); tot += d; }
  const out = [];
  for (let k = 0; k <= n; k++) {
    let d = (k / n) * tot, i = 0;
    while (i < seg.length - 1 && d > seg[i]) { d -= seg[i]; i++; }
    out.push(pts[i].clone().lerp(pts[i + 1], seg[i] ? Math.min(1, d / seg[i]) : 0));
  }
  return out;
}
const roundCorners = (pts, r = 0.25) => new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.0).getPoints(pts.length * 16);

// ================================================================== SET 1: YARD + OUTHOUSE
const YX = -80;
function buildYard() {
  const PX = 0.7, PD = 2.3, PB = 1.5;
  // waste filling the pit
  const waste = mesh(new THREE.BoxGeometry(PX * 2 - 0.02, 1, PB - 0.02), new THREE.MeshStandardMaterial({ color: 0x3a2410, roughness: 0.7, envMapIntensity: 0.2 }), YX, -PD, -PB / 2);
  S.onUpdate(t => {
    const h = lerp(0.25, PD - 0.15, smooth(t, E.fill - 0.2, E.fill + 1.6)) * (t > E.build ? 1 : 0.4);
    waste.scale.y = h; waste.position.y = -PD + h / 2;
  });
  // dirt pile + shovel
  const pile = mesh(new THREE.SphereGeometry(1, 32, 16), S.pbr('soil', { tile: 1.2, normalScale: 2 }), YX - 3.2, -0.25, -2.4);
  pile.scale.set(1.6, 0.8, 1.2);
  S.onUpdate(t => { const k = Math.max(0.01, smooth(t, E.dig, E.build)); pile.scale.set(1.6 * k, 0.8 * k, 1.2 * k); });
  const shovel = new THREE.Group(); add(shovel);
  mesh(new THREE.CylinderGeometry(0.025, 0.025, 1.4, 8), M.wood, 0, 0.7, 0, shovel);
  mesh(new THREE.BoxGeometry(0.26, 0.32, 0.02), M.metal, 0, 0, 0, shovel);
  S.onUpdate(t => {
    if (t < E.build) { // digging strokes
      const ph = ((t - E.dig) / 0.45) % 1;
      shovel.position.set(YX + 0.2, 0.3 - Math.sin(ph * Math.PI) * 0.6, -0.6); shovel.rotation.set(0.3 - Math.sin(ph * Math.PI) * 0.5, 0.4, -0.3);
    } else { shovel.position.set(YX - 2.2, 0.2, -2.1); shovel.rotation.set(0.15, 0.4, -0.35); }
  });
  // outhouse
  const oh = new THREE.Group(); oh.position.set(YX, 0, -PB / 2); add(oh);
  const W = 1.5, D = 1.4, H = 2.3;
  const part = (w, h, d, x, y, z) => mesh(new THREE.BoxGeometry(w, h, d), M.wood, x, y, z, oh);
  const parts = [part(W + 0.2, 0.12, D + 0.2, 0, 0.06, 0),
    part(0.06, H, D, -W / 2, H / 2 + 0.12, 0), part(0.06, H, D, W / 2, H / 2 + 0.12, 0), part(W, H, 0.06, 0, H / 2 + 0.12, -D / 2),
    part(W - 0.06, H - 0.05, 0.06, 0, H / 2 + 0.12, D / 2)];
  const roof = part(W + 0.5, 0.08, D + 0.6, 0, H + 0.32, 0); roof.rotation.x = 0.16;
  const moon = mesh(new THREE.CircleGeometry(0.14, 32), new THREE.MeshBasicMaterial({ color: 0x120a04 }), 0, H - 0.35, D / 2 + 0.035, oh);
  const moonCut = mesh(new THREE.CircleGeometry(0.12, 32), M.wood, 0.07, H - 0.32, D / 2 + 0.037, oh);
  mesh(new THREE.SphereGeometry(0.035, 12, 8), M.brass, W / 2 - 0.18, 1.2, D / 2 + 0.06, oh);
  const pieces = [...parts, roof];
  S.onUpdate(t => {
    pieces.forEach((p, i) => { const k = smooth(t, E.build + i * 0.15, E.build + i * 0.15 + 0.4); p.visible = k > 0.01; p.position.y = p.userData.y0 + (1 - k) * 3; });
    moon.visible = moonCut.visible = t > E.build + 0.8;
  });
  pieces.forEach(p => (p.userData.y0 = p.position.y));
  // stink lines + flies
  const stinkMat = new THREE.MeshStandardMaterial({ color: 0xb6d83a, emissive: 0x6a8a10, emissiveIntensity: 0.8, transparent: true, opacity: 0, depthWrite: false });
  const stinks = [];
  for (let i = 0; i < 4; i++) {
    const pts = []; for (let k = 0; k <= 30; k++) pts.push(V(Math.sin(k * 0.6) * 0.12, k * 0.06, 0));
    const s = mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 80, 0.025, 8), stinkMat, YX - 0.6 + i * 0.4, 2.5, -0.2);
    s.castShadow = false; stinks.push(s);
  }
  S.onUpdate(t => {
    stinkMat.opacity = 0.9 * smooth(t, E.smell - 0.2, E.smell + 0.4) * (1 - smooth(t, E.house - 0.4, E.house));
    stinks.forEach((s, i) => { s.position.y = 2.5 + ((t * 0.5 + i * 0.25) % 0.6); s.rotation.y = Math.sin(t * 2 + i) * 0.5; });
  });
  const flyG = new THREE.SphereGeometry(0.035, 8, 6), wingG = new THREE.PlaneGeometry(0.06, 0.035);
  const wingM = new THREE.MeshStandardMaterial({ color: 0xdfeaf5, transparent: true, opacity: 0.6, side: THREE.DoubleSide });
  const flies = [];
  const r = rng(9);
  for (let i = 0; i < 10; i++) {
    const f = new THREE.Group(); f.add(new THREE.Mesh(flyG, M.dark));
    const w1 = new THREE.Mesh(wingG, wingM); w1.position.set(-0.04, 0.03, 0); const w2 = w1.clone(); w2.position.x = 0.04; f.add(w1, w2);
    f.userData = { ph: r() * 6.28, rx: 0.5 + r() * 0.8, ry: 0.3 + r() * 0.5, sp: 2 + r() * 2, w1, w2 }; add(f); flies.push(f);
  }
  S.onUpdate(t => {
    const on = t > E.flies - 0.2 && t < E.house;
    flies.forEach((f, i) => {
      f.visible = on; const u = f.userData;
      f.position.set(YX + Math.cos(t * u.sp + u.ph) * u.rx, 1.4 + Math.sin(t * u.sp * 1.3 + u.ph) * u.ry, 0.4 + Math.sin(t * u.sp * 0.7 + u.ph) * 0.4);
      u.w1.rotation.x = u.w2.rotation.x = Math.sin(t * 80 + i) * 0.8;
    });
  });
  // villa backdrop for the yard
  villa(YX, -17);
  palm(S, YX - 8, -12, { height: 7.5, seed: 4, lean: 0.12 });
  palm(S, YX + 8.5, -11, { height: 6.6, seed: 5, lean: -0.1 });
  palm(S, YX - 13, -6, { height: 5.8, seed: 6, lean: 0.2 });
  tree(S, YX + 12, -6, { height: 5.5, spread: 3, seed: 7 });
  grassTufts(S, { count: 3500, x0: YX - 12, x1: YX + 12, z0: -0.02, z1: -9, height: 0.13, edgeBias: 0.55, seed: 4 });
  return { PX, PB };
}

function villa(x, z, { floors = 2 } = {}) {
  box(S, M.plaster, 16, 7, 8, x, 3.5, z - 4);
  if (floors > 1) box(S, M.plaster, 8, 3.4, 6, x - 2.5, 8.7, z - 4.5);
  box(S, M.trim, 16.3, 0.4, 8.3, x, 7.2, z - 4);
  for (let i = 0; i < 26; i++) box(S, M.trim, 0.32, 0.32, 0.3, x - 7.9 + i * 0.632, 7.55, z + 0.05);
  for (const wx of [-5.5, -2.5, 2.5, 5.5]) for (const wy of [1.8, 4.9]) {
    box(S, M.frame, 1.5, 2.0, 0.12, x + wx, wy, z + 0.04); box(S, M.glass, 1.25, 1.75, 0.12, x + wx, wy, z + 0.08);
    box(S, M.frame, 1.7, 0.1, 0.3, x + wx, wy - 1.05, z + 0.1);
  }
  box(S, S.pbr('wood', { tile: 1, color: 0x9a6a40 }), 1.8, 2.8, 0.15, x, 1.4, z + 0.06);
  box(S, M.conc, 18, 0.12, 3, x, 0.06, z + 1.5);
  for (const ax of [-7, 6.8]) box(S, new THREE.MeshStandardMaterial({ color: 0xeeeeea, roughness: 0.4 }), 1, 0.7, 0.5, x + ax, 5.2, z + 0.3);
  for (const [dx, w] of [[-12.5, 9], [12.5, 9]]) { box(S, M.stone, w, 2.6, 0.35, x + dx, 1.3, z + 2.5); box(S, M.trim, w + 0.2, 0.15, 0.5, x + dx, 2.66, z + 2.5); }
}

// ================================================================== SET 2: HOUSE CUT-AWAY
const RX0 = -2.2, RX1 = 2.0, WALL = 0.25, RD = 3.0, RZ = 2.8, SLAB = 0.35, ROOF = 0.35;
const TS = 1.3, TX = RX0 + 0.04;
const SEW = { x: 5.6, y: -2.2, r: 0.55 };
const ROAD_X = 3.6;
const BODY = [[0.30, 0.0], [0.68, 0.0], [0.66, 0.10], [0.74, 0.18], [0.86, 0.30], [0.90, 0.40], [0.90, 0.45], [0.84, 0.45],
  [0.80, 0.32], [0.70, 0.22], [0.56, 0.15], [0.46, 0.12], [0.40, 0.13], [0.36, 0.20], [0.31, 0.32], [0.27, 0.45], [0.18, 0.45], [0.18, 0.40], [0.22, 0.30], [0.27, 0.16], [0.29, 0.06]];
const BASIN = [[0.84, 0.45], [0.80, 0.32], [0.70, 0.22], [0.56, 0.15], [0.46, 0.12], [0.40, 0.13], [0.36, 0.20], [0.31, 0.32], [0.27, 0.45]];
const TRAP_S = [[0.44, 0.13], [0.37, 0.16], [0.31, 0.22], [0.27, 0.29], [0.22, 0.31], [0.19, 0.26], [0.21, 0.15], [0.30, 0.04], [0.40, 0.0]];
const TRAP_0 = [[0.44, 0.13], [0.435, 0.12], [0.43, 0.11], [0.425, 0.09], [0.42, 0.075], [0.415, 0.06], [0.41, 0.04], [0.405, 0.02], [0.40, 0.0]];
const CREST = 4, SEAL = 0.235;
const T = (u, v, z = 0) => V(TX + u * TS, v * TS, z);

function trapPts(t) {
  const k = smooth(t, E.bend, E.S + 0.4);
  return TRAP_0.map((a, i) => T(lerp(a[0], TRAP_S[i][0], k), lerp(a[1], TRAP_S[i][1], k), 0.0));
}
function drainPts() {
  const o = T(0.40, 0);
  return roundCorners([o, V(o.x, -0.8, 0), V(o.x + 0.35, -1.0, 0), V(SEW.x - 0.9, SEW.y + 0.25, 0), V(SEW.x - SEW.r + 0.05, SEW.y + 0.05, 0)]);
}
const VENT_X = RX0 - WALL / 2;
function ventPts() { const o = T(0.40, 0); return roundCorners([V(o.x, -0.75, 0), V(VENT_X, -0.75, 0), V(VENT_X, RZ + ROOF + 0.95, 0)]); }

function bowlLevel(t) {
  if (t < E.bend) return null;
  const keys = [[E.seal - 0.3, 0.06], [E.seal + 0.6, SEAL], [E.bigflush, SEAL], [E.bigflush + 0.5, 0.36], [E.rush, 0.36],
    [E.empty, 0.08], [E.gurgle + 0.2, 0.06], [E.air + 0.8, SEAL], [E.lift, SEAL], [E.lift + 0.6, 0.34], [E.float, 0.10], [E.full, SEAL],
    [E.rush2, SEAL], [E.suckair + 0.2, SEAL], [E.dry, 0.02], [E.vent, 0.02], [E.air_in, SEAL]];
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) if (t <= keys[i + 1][0]) return lerp(keys[i][1], keys[i + 1][1], smooth(t, keys[i][0], keys[i + 1][0]));
  return keys[keys.length - 1][1];
}
const siphonOn = t => (E.rush - 0.1 < t && t < E.gurgle + 0.1) || (E.lift + 0.3 < t && t < E.float + 0.2) || (E.suckair - 0.2 < t && t < E.dry + 0.1);

function polyBelow(poly, level) {
  // part of a closed (u,v) polygon below v = level (Sutherland-Hodgman against a half-plane)
  const out = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    const ain = a[1] <= level, bin = b[1] <= level;
    if (ain) out.push(a);
    if (ain !== bin) { const k = (level - a[1]) / (b[1] - a[1]); out.push([a[0] + (b[0] - a[0]) * k, level]); }
  }
  return out;
}

function buildHouse() {
  const sc = S.scene;
  // slab, footings, walls, roof (section faces sit at z = +0.01, in front of the soil cut)
  box(S, M.conc, (RX1 - RX0) + 2 * WALL + 0.8, SLAB, 12, (RX0 + RX1) / 2, -SLAB / 2, -6 + 0.01);
  for (const x of [RX0 - WALL / 2, RX1 + WALL / 2]) box(S, M.conc, 0.7, 0.6, 12, x, -SLAB - 0.3, -6 + 0.012);
  box(S, M.floor, RX1 - RX0, 0.02, RD, (RX0 + RX1) / 2, 0.01, -RD / 2);
  // walls
  box(S, M.plaster, WALL, RZ, 12, RX0 - WALL / 2, RZ / 2, -6 + 0.01);
  box(S, M.plaster, WALL, RZ, 12, RX1 + WALL / 2, RZ / 2, -6 + 0.01);
  box(S, M.paint, RX1 - RX0, RZ, WALL, (RX0 + RX1) / 2, RZ / 2, -RD - WALL / 2);
  // interior finishes: tiles + blue band + paint
  const tileH = 1.3;
  box(S, M.tiles, RX1 - RX0, tileH, 0.02, (RX0 + RX1) / 2, tileH / 2, -RD + 0.01, { cast: false });
  box(S, M.band, RX1 - RX0, 0.12, 0.03, (RX0 + RX1) / 2, tileH + 0.06, -RD + 0.015, { cast: false });
  box(S, M.tiles, 0.02, tileH, RD, RX0 + 0.01, tileH / 2, -RD / 2, { cast: false });
  box(S, M.band, 0.03, 0.12, RD, RX0 + 0.015, tileH + 0.06, -RD / 2, { cast: false });
  box(S, M.tiles, 0.02, tileH, RD, RX1 - 0.01, tileH / 2, -RD / 2, { cast: false });
  box(S, M.band, 0.03, 0.12, RD, RX1 - 0.015, tileH + 0.06, -RD / 2, { cast: false });
  // window on the back wall (daylight panes) + sink + mirror + lamp + mat
  box(S, M.frame, 1.2, 1.0, 0.08, 0.1, 2.0, -RD + 0.03);
  box(S, new THREE.MeshStandardMaterial({ color: 0xcfe6fb, emissive: 0x9cc8ea, emissiveIntensity: 0.9 }), 1.05, 0.85, 0.04, 0.1, 2.0, -RD + 0.07);
  box(S, M.frame, 0.04, 0.85, 0.06, 0.1, 2.0, -RD + 0.09); box(S, M.frame, 1.05, 0.04, 0.06, 0.1, 2.0, -RD + 0.09);
  const sink = mesh(new THREE.SphereGeometry(0.3, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), M.porcelain, 1.3, 0.85, -RD + 0.3); sink.rotation.x = Math.PI; sink.scale.set(1, 0.45, 0.8);
  mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.75, 16), M.porcelain, 1.3, 0.42, -RD + 0.25);
  box(S, new THREE.MeshPhysicalMaterial({ color: 0xbfd6e4, metalness: 1, roughness: 0.04 }), 0.6, 0.75, 0.03, 1.3, 1.85, -RD + 0.03);
  const lamp = mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.05, 24), new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff3d6, emissiveIntensity: 2.5 }), 0, RZ - 0.03, -RD / 2);
  const pl = new THREE.PointLight(0xfff1d8, 2.2, 6, 1.8); pl.position.set(0, RZ - 0.2, -RD / 2); sc.add(pl);
  box(S, new THREE.MeshStandardMaterial({ color: 0x7fcfc4, roughness: 0.9 }), 0.9, 0.015, 0.6, 0.8, 0.03, -1.2, { cast: false });
  // ceiling + roof slab + parapet + rest of the villa mass behind
  box(S, M.paint, RX1 - RX0, 0.02, RD, (RX0 + RX1) / 2, RZ - 0.01, -RD / 2, { cast: false });
  box(S, M.conc, (RX1 - RX0) + 2 * WALL + 0.4, ROOF, 12, (RX0 + RX1) / 2, RZ + ROOF / 2, -6 + 0.01);
  box(S, M.trim, 0.2, 0.55, 12, RX0 - WALL - 0.1, RZ + ROOF + 0.27, -6);
  box(S, M.trim, 0.2, 0.55, 12, RX1 + WALL + 0.1, RZ + ROOF + 0.27, -6);
  box(S, M.trim, (RX1 - RX0) + 2 * WALL + 0.4, 0.55, 0.2, (RX0 + RX1) / 2, RZ + ROOF + 0.27, -0.1);
  box(S, M.plaster, 7, 3.2, 6, -0.5, RZ + ROOF + 1.6, -9);
  for (let i = 0; i < 12; i++) box(S, M.trim, 0.3, 0.3, 0.3, -3.8 + i * 0.6, RZ + ROOF + 3.35, -5.95);
  // exterior strip on the outside of the right wall + small window
  box(S, M.glass, 0.04, 0.9, 1.0, RX1 + WALL + 0.02, 1.8, -2.0);
  // street side: lawn strip, sidewalk, curb, road with layers in section, sewer main
  box(S, M.conc, ROAD_X - 2.9, 0.12, 40, (2.9 + ROAD_X) / 2, 0.06, -20 + 0.01);
  box(S, M.asphalt, 12, 0.18, 40, ROAD_X + 6, -0.09, -20 + 0.012);
  box(S, M.gravel, 12, 0.45, 40, ROAD_X + 6, -0.4, -20 + 0.012);
  for (let k = 0; k < 9; k++) box(S, new THREE.MeshStandardMaterial({ color: 0xf2f2f2, roughness: 0.6 }), 0.15, 0.01, 1.8, ROAD_X + 6, 0.005, -2 - k * 4.2, { cast: false });
  const sewer = new THREE.Group(); add(sewer);
  const outer = mesh(new THREE.CylinderGeometry(SEW.r, SEW.r, 30, 48, 1, true), new THREE.MeshStandardMaterial({ color: 0x8f8a80, roughness: 0.8, side: THREE.DoubleSide }), 0, 0, 0, sewer);
  outer.rotation.x = Math.PI / 2; outer.position.set(SEW.x, SEW.y, -15 + 0.02);
  const rim = mesh(new THREE.RingGeometry(SEW.r * 0.86, SEW.r, 48), new THREE.MeshStandardMaterial({ color: 0xbdb8ad, roughness: 0.8 }), SEW.x, SEW.y, 0.03, sewer);
  const inner = mesh(new THREE.CircleGeometry(SEW.r * 0.86, 48), new THREE.MeshStandardMaterial({ color: 0x15181c, roughness: 1 }), SEW.x, SEW.y, -6, sewer);
  const sewWater = mesh(new THREE.BoxGeometry(SEW.r * 1.6, SEW.r * 0.7, 30), new THREE.MeshStandardMaterial({ color: 0x5f6e3e, roughness: 0.3 }), SEW.x, SEW.y - SEW.r * 0.5, -15, sewer);
  // soil cut-out behind the sewer so the pipe reads as a tunnel
  // background: palms + neighbours behind the house and across the road
  palm(S, -5.5, -8, { height: 7.5, seed: 11, lean: 0.1 });
  palm(S, 3.2, -6, { height: 6.2, seed: 12, lean: -0.12 });
  palm(S, 8.5, -18, { height: 7.0, seed: 13 });
  tree(S, -9, -14, { height: 6, spread: 3.4, seed: 14 });
  tree(S, 12, -22, { height: 7, spread: 4, seed: 15 });
  villa(14, -26, { floors: 1 });
  grassTufts(S, { count: 2500, x0: -12, x1: RX0 - WALL, z0: -0.02, z1: -8, height: 0.12, edgeBias: 0.6, seed: 21 });
  grassTufts(S, { count: 800, x0: RX1 + WALL, x1: 2.9, z0: -0.02, z1: -8, height: 0.12, edgeBias: 0.6, seed: 22 });
}

function buildToilet() {
  const g = new THREE.Group(); add(g);
  // porcelain body = side profile extruded backwards (we see the cut face at z = 0)
  const sh = new THREE.Shape(BODY.map(([u, v]) => new THREE.Vector2(TX + u * TS, v * TS)));
  const body = mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.36, bevelEnabled: false }), [M.porcelainCut, M.porcelain], 0, 0, -0.36, g);
  // trapway channel (white tube) + water inside it
  const chan = dynTube(new THREE.MeshStandardMaterial({ color: 0xe8f3fb, roughness: 0.25, emissive: 0x2a4a60, emissiveIntensity: 0.15 }), 0.05 * TS, g);
  const chanWater = dynTube(M.waterFlow, 0.038 * TS, g);
  const basinWater = mesh(new THREE.BufferGeometry(), M.water, 0, 0, 0, g); basinWater.castShadow = false;
  let lastK = -1, lastL = -1, lastFull = null;
  S.onUpdate(t => {
    const k = smooth(t, E.bend, E.S + 0.4);
    const trap = trapPts(t);
    if (Math.abs(k - lastK) > 1e-3) { chan.setPoints(trap); lastK = k; }
    const lv = bowlLevel(t), full = siphonOn(t);
    if (lv !== lastL || full !== lastFull) {
      lastL = lv; lastFull = full;
      if (full) chanWater.setPoints(trap);
      else if (lv !== null) {
        const rising = samplePolyline(trap.slice(0, CREST + 1), 40).filter(p => p.y <= lv * TS + 0.002);
        chanWater.setPoints(rising.length > 1 ? rising : null);
      } else chanWater.setPoints(null);
      basinWater.geometry.dispose();
      if (lv !== null && lv > 0.125) {
        const poly = polyBelow(BASIN, Math.min(lv, 0.44));
        if (poly.length > 2) {
          const ws = new THREE.Shape(poly.map(([u, v]) => new THREE.Vector2(TX + u * TS, v * TS)));
          basinWater.geometry = new THREE.ExtrudeGeometry(ws, { depth: 0.34, bevelEnabled: false }); basinWater.position.z = -0.35;
        } else basinWater.geometry = new THREE.BufferGeometry();
      } else basinWater.geometry = new THREE.BufferGeometry();
    }
    const kk = pop(t, E.seat_in, 0.45);
    g.visible = kk > 0.01;
    g.scale.setScalar(Math.max(0.01, kk));
    g.position.set((1 - kk) * TX * 0, 0, 0);
  });
  // tank (cut open) behind the bowl, against the wall
  const tank = new THREE.Group(); add(tank);
  const tu0 = 0.0, tu1 = 0.46, tv0 = 0.66, tv1 = 1.32;
  const tw = (tu1 - tu0) * TS, th = (tv1 - tv0) * TS, tcx = TX + (tu0 + tu1) / 2 * TS, tcy = (tv0 + tv1) / 2 * TS;
  mesh(new THREE.BoxGeometry(tw, th, 0.04), M.porcelain, tcx, tcy, -0.36, tank);
  mesh(new THREE.BoxGeometry(0.035, th, 0.36), M.porcelain, tcx - tw / 2, tcy, -0.18, tank);
  mesh(new THREE.BoxGeometry(0.035, th, 0.36), M.porcelain, tcx + tw / 2, tcy, -0.18, tank);
  mesh(new THREE.BoxGeometry(tw, 0.035, 0.36), M.porcelain, tcx, tcy - th / 2, -0.18, tank);
  mesh(new THREE.BoxGeometry(tw + 0.05, 0.05, 0.4), M.porcelain, tcx, tcy + th / 2 + 0.02, -0.18, tank);
  const tankWater = mesh(new THREE.BoxGeometry(tw - 0.04, 1, 0.33), M.water, tcx, 0, -0.18, tank); tankWater.castShadow = false;
  const flapPivot = new THREE.Group(); flapPivot.position.set(TX + 0.24 * TS, tv0 * TS + 0.03, -0.12); tank.add(flapPivot);
  const flap = mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.03, 24), M.rubber, 0.075, 0, 0, flapPivot);
  const flushValve = mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.06, 24), M.pvcSolid, TX + 0.30 * TS, tv0 * TS + 0.0, -0.12, tank);
  mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.5, 12), M.pvcSolid, TX + 0.38 * TS, tv0 * TS + 0.27, -0.12, tank);
  mesh(new THREE.CylinderGeometry(0.03, 0.03, th - 0.18, 12), new THREE.MeshStandardMaterial({ color: 0xd6dce2, roughness: 0.4 }), TX + 0.07 * TS, tcy - 0.05, -0.12, tank);
  const floatArm = mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.22, 8), M.metal, 0, 0, -0.12, tank);
  const floatBall = mesh(new THREE.SphereGeometry(0.055, 24, 16), M.brass, 0, 0, -0.12, tank);
  const handlePivot = new THREE.Group(); handlePivot.position.set(TX + tu1 * TS + 0.02, tv1 * TS - 0.1, -0.05); tank.add(handlePivot);
  mesh(new THREE.BoxGeometry(0.16, 0.03, 0.03), M.chrome, -0.06, 0, 0, handlePivot);
  const chain = dynTube(M.metal, 0.004, tank);
  const fillChannel = mesh(new THREE.CylinderGeometry(0.03, 0.03, (tv0 - 0.43) * TS, 12), M.porcelain, TX + 0.28 * TS, (tv0 + 0.43) / 2 * TS, -0.14, tank);
  const hiFlap = ring(0.11, 0.01); hiFlap.rotation.x = Math.PI / 2; tank.add(hiFlap);
  const hiFloat = ring(0.09, 0.01); tank.add(hiFloat);
  const hiHandle = ring(0.08, 0.01); tank.add(hiHandle);
  S.onUpdate(t => {
    const k = smooth(t, E.tank, E.tank + 0.45);
    tank.visible = k > 0.01; tank.position.y = (1 - k) * 1.2;
    const tl = (() => { const ks = [[E.tank, 0.9], [E.lift + 0.1, 0.9], [E.lift + 0.8, 0.12], [E.float, 0.15], [E.full, 0.9]];
      if (t <= ks[0][0]) return 0.9; for (let i = 0; i < ks.length - 1; i++) if (t <= ks[i + 1][0]) return lerp(ks[i][1], ks[i + 1][1], smooth(t, ks[i][0], ks[i + 1][0])); return 0.9; })();
    const wh = Math.max(0.01, (th - 0.06) * tl);
    tankWater.scale.y = wh; tankWater.position.y = tv0 * TS + 0.035 + wh / 2;
    const lift = smooth(t, E.lift, E.lift + 0.25) * (1 - smooth(t, E.lift + 1.2, E.lift + 1.6));
    flapPivot.rotation.z = lift * 0.9;
    handlePivot.rotation.z = -0.5 * lift;
    const fy = lerp(tv0 * TS + 0.18, tv1 * TS - 0.15, tl);
    floatBall.position.set(TX + 0.24 * TS, fy, -0.12);
    const fvTop = V(TX + 0.07 * TS, tv1 * TS - 0.12, -0.12);
    floatArm.position.copy(fvTop.clone().lerp(floatBall.position, 0.5));
    floatArm.lookAt(floatBall.position); floatArm.rotateX(Math.PI / 2); floatArm.scale.y = fvTop.distanceTo(floatBall.position) / 0.22;
    const tip = V(handlePivot.position.x - 0.13 * Math.cos(-0.5 * lift), handlePivot.position.y - 0.13 * Math.sin(-0.5 * lift), -0.05);
    chain.setPoints([tip, V(TX + 0.3 * TS, tv0 * TS + 0.08 + 0.1 * lift, -0.12)]);
    hiFlap.visible = t > E.flapper - 0.1 && t < E.handle + 0.6; hiFlap.position.set(TX + 0.30 * TS, tv0 * TS + 0.06, -0.12); hiFlap.scale.setScalar(1 + 0.15 * Math.sin(t * 9));
    hiHandle.visible = t > E.handle - 0.1 && t < E.float; hiHandle.position.set(handlePivot.position.x - 0.06, handlePivot.position.y, 0.0); hiHandle.scale.setScalar(1 + 0.15 * Math.sin(t * 9));
    hiFloat.visible = t > E.float - 0.1 && t < E.rush2; hiFloat.position.set(floatBall.position.x, floatBall.position.y, 0.0); hiFloat.scale.setScalar(1 + 0.15 * Math.sin(t * 9));
  });
  // seat and lid
  const seat = mesh(new THREE.TorusGeometry(0.2 * TS, 0.03 * TS, 12, 48, Math.PI), M.porcelain, TX + 0.54 * TS, 0.47 * TS, -0.0);
  seat.rotation.x = Math.PI / 2; seat.scale.set(1.2, 1, 1);
  const lidPivot = new THREE.Group(); lidPivot.position.set(TX + 0.2 * TS, 0.49 * TS, 0); add(lidPivot);
  const lid = mesh(new THREE.CylinderGeometry(0.34 * TS, 0.34 * TS, 0.025, 48, 1, false, Math.PI, Math.PI), M.porcelain, 0.34 * TS, 0, 0, lidPivot);
  lid.scale.set(1.05, 1, 0.7);
  S.onUpdate(t => {
    const k1 = smooth(t, E.seat, E.seat + 0.4), k2 = smooth(t, E.lid, E.lid + 0.5);
    seat.visible = k1 > 0.01; seat.position.y = 0.47 * TS + (1 - k1) * 0.8;
    lidPivot.visible = k2 > 0.01; lidPivot.rotation.z = lerp(1.35, 1.25, k2); lidPivot.position.y = 0.49 * TS + (1 - k2) * 0.8;
  });
  return { chan };
}

function buildPipes() {
  const sc = S.scene;
  const dp = drainPts();
  const drain = dynTube(M.pvc, 0.13);
  const vent = dynTube(M.pvc, 0.1);
  const vpts = ventPts();
  const ventCap = mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.08, 24), M.pvcSolid, VENT_X, RZ + ROOF + 0.98, 0);
  // contents: water slugs + waste + flow dots
  const water = dynTube(M.waterFlow, 0.085);
  const wasteBlobs = [0, 1, 2].map(() => { const m = mesh(new THREE.SphereGeometry(0.06, 16, 12), M.waste); m.scale.set(1.4, 0.8, 1); return m; });
  const bubbles = Array.from({ length: 10 }, () => mesh(new THREE.SphereGeometry(0.025, 10, 8), M.white));
  let lastG = -1, lastV = -1;
  const sub = (pts, a, b) => { const s = samplePolyline(pts, 120); const i0 = Math.floor(clamp(a) * 120), i1 = Math.floor(clamp(b) * 120); return s.slice(i0, i1 + 1); };
  const at = (pts, u) => samplePolyline(pts, 200)[Math.round(clamp(u) * 200)];
  S.onUpdate(t => {
    const g = smooth(t, E.pipe, E.sewer + 0.4);
    if (Math.abs(g - lastG) > 1e-3) { drain.setPoints(g > 0.01 ? sub(dp, 0, g) : null); lastG = g; }
    const gv = smooth(t, E.vent, E.roof + 0.3);
    if (Math.abs(gv - lastV) > 1e-3) { vent.setPoints(gv > 0.01 ? sub(vpts, 0, gv) : null); lastV = gv; }
    ventCap.visible = gv > 0.98;
    // water pushed by the bucket and the flushes
    let seg = null;
    if (t > E.bucket + 0.3 && t < E.problem2 + 0.4) { const u = lin(t, E.bucket + 0.3, E.push + 1.2); seg = [Math.max(0, u - 0.35), u]; }
    for (const [a0, a1] of [[E.rush, E.gurgle + 0.4], [E.lift + 0.3, E.float + 0.6], [E.rush2, E.dry + 0.3]]) if (t > a0 && t < a1 + 0.8) { const u = lin(t, a0, a1); seg = [Math.max(0, u - 0.6), u]; }
    water.setPoints(seg ? sub(dp, seg[0], seg[1]) : null);
    bubbles.forEach((b, i) => { const on = !!seg; b.visible = on; if (on) { const uu = seg[0] + ((t * 0.5 + i / 10) % 1) * (seg[1] - seg[0]); b.position.copy(at(dp, uu)).add(V(0, 0, 0.09)); } });
    const push = smooth(t, E.push - 0.2, E.push + 1.4);
    wasteBlobs.forEach((w, i) => {
      const on = t > E.still - 1.0 && t < E.problem2;
      const u = lerp(0.22 + i * 0.08, 1.02, push);
      w.visible = on && u < 1;
      if (w.visible) w.position.copy(at(dp, u)).add(V(0, -0.04, 0.02));
    });
  });
  return { dp, vpts };
}

function buildEffects() {
  // sewer gas puffs travelling up the drain; blocked by the water seal; through the dry trap later
  const puffs = Array.from({ length: 14 }, () => { const m = mesh(new THREE.SphereGeometry(0.07, 16, 12), M.gas); m.castShadow = false; return m; });
  const stinkMat = new THREE.MeshStandardMaterial({ color: 0xb6d83a, emissive: 0x6a8a10, emissiveIntensity: 0.8, transparent: true, opacity: 0, depthWrite: false });
  const stinks = [0, 1, 2].map(i => {
    const pts = []; for (let k = 0; k <= 30; k++) pts.push(V(Math.sin(k * 0.6) * 0.07, k * 0.04, 0));
    const s = mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 80, 0.015, 8), stinkMat, TX + (0.4 + i * 0.2) * TS, 0.6, 0.0); s.castShadow = false; return s;
  });
  const xBlock = redX(0.22); add(xBlock);
  const dp = drainPts();
  const sp = samplePolyline(dp, 200);
  S.onUpdate(t => {
    const trap = samplePolyline(trapPts(t), 60);
    const wins = [[E.gas - 0.2, E.bend - 0.2, false], [E.seal + 0.3, E.trap_name + 1.0, true], [E.gas_back - 0.5, E.air_in, false]];
    let any = false, blockedOn = false, a = 0, w0 = null;
    for (const [t0, t1, bl] of wins) if (t > t0 && t < t1 + 0.5) { any = true; blockedOn = bl; a = smooth(t, t0, t0 + 0.5) * (1 - smooth(t, t1, t1 + 0.5)); w0 = t0; }
    puffs.forEach((p, i) => {
      p.visible = any;
      if (!any) return;
      const u = ((t - w0) * 0.28 + i / 14) % 1;
      let pos;
      if (u < 0.75) pos = sp[Math.round((1 - u / 0.75) * 200)];
      else {
        const k = (u - 0.75) / 0.25;
        if (blockedOn && k > 0.45) { p.visible = false; return; }
        pos = trap[Math.round((1 - Math.min(k, 1)) * 60)];
      }
      p.position.copy(pos).add(V(0, 0, 0.12));
      p.scale.setScalar(0.8 + 0.3 * Math.sin(i + t * 3));
    });
    M.gas.opacity = 0.6 * a;
    const stinkOn = any && !blockedOn && ((w0 < E.bend && t > E.enter - 0.4) || (w0 > E.trap_name && t > E.dry));
    stinkMat.opacity = stinkOn ? 0.85 * a : 0;
    stinks.forEach((s, i) => { s.position.y = 0.6 + ((t * 0.4 + i * 0.2) % 0.5); });
    xBlock.visible = blockedOn && t > E.block - 0.1;
    const kx = pop(t, E.block, 0.3);
    xBlock.scale.setScalar(Math.max(0.01, kx)); xBlock.position.copy(trap[30]).add(V(0.25, 0.2, 0.15));
  });
  // siphon arrows through the trap and down the drain
  const arrows = Array.from({ length: 6 }, () => { const a = arrowMesh(M.white, 0.14, 0.012); add(a); return a; });
  const airArrows = Array.from({ length: 5 }, () => { const a = arrowMesh(new THREE.MeshStandardMaterial({ color: 0xcfefff, emissive: 0x7fbfe0, emissiveIntensity: 0.6 }), 0.22, 0.018); add(a); return a; });
  const siphonRing = ring(0.28, 0.012); add(siphonRing);
  const trapRing = ring(0.2, 0.012); add(trapRing);
  const vp = samplePolyline(ventPts(), 100);
  S.onUpdate(t => {
    const on = t > E.fills - 0.2 && t < E.siphon_name + 1.0;
    const path = samplePolyline([...trapPts(t), ...drainPts().slice(1, 60)], 120);
    arrows.forEach((a, i) => {
      a.visible = on; if (!on) return;
      const u = ((t - E.fills) * 0.45 + i / 6) % 1;
      const p = path[Math.round(u * 119)], q = path[Math.round(u * 119) + 1];
      a.position.copy(p).add(V(0, 0, 0.1)); a.quaternion.setFromUnitVectors(V(0, 1, 0), q.clone().sub(p).normalize());
    });
    siphonRing.visible = t > E.siphon_name - 0.1 && t < E.siphon_name + 1.0; siphonRing.position.copy(T(0.32, 0.18, 0.05)); siphonRing.scale.setScalar(1 + 0.1 * Math.sin(t * 8));
    trapRing.visible = t > E.trap_name - 0.1 && t < E.trap_name + 1.4; trapRing.position.copy(T(0.24, 0.27, 0.05)); trapRing.scale.setScalar(1 + 0.1 * Math.sin(t * 8));
    // air coming down the vent stack (balancing the pressure)
    const air = t > E.air_in - 0.1 && t < E.see;
    airArrows.forEach((a, i) => {
      a.visible = air; if (!air) return;
      const u = ((t - E.air_in) * 0.5 + i / 5) % 1;
      const p = vp[Math.round((1 - u) * 99)];
      a.position.copy(p).add(V(0.18, 0, 0.1)); a.rotation.set(0, 0, Math.PI);
    });
  });
  // gurgle bubbles in the trap
  const gb = Array.from({ length: 10 }, () => mesh(new THREE.TorusGeometry(0.02, 0.005, 6, 16), M.white));
  S.onUpdate(t => {
    const on = t > E.gurgle - 0.1 && t < E.air + 1.4;
    const r = rng(Math.floor(t * 12) + 1);
    const tp = samplePolyline(trapPts(t), 40);
    gb.forEach(b => { b.visible = on; if (on) { b.position.copy(tp[Math.floor(r() * 40)]).add(V((r() - 0.5) * 0.04, (r() - 0.5) * 0.04, 0.08)); b.scale.setScalar(0.6 + r()); } });
  });
  // buckets: small one (paragraph 3) and big flush (paragraph 6)
  const bucketG = new THREE.LatheGeometry([new THREE.Vector2(0.11, 0), new THREE.Vector2(0.14, 0.26), new THREE.Vector2(0.145, 0.27)], 32);
  const bucket = mesh(bucketG, new THREE.MeshStandardMaterial({ color: 0xb9c0c7, metalness: 0.85, roughness: 0.3, side: THREE.DoubleSide }));
  const bucketWater = mesh(new THREE.CircleGeometry(0.13, 32), M.water, 0, 0, 0, bucket); bucketWater.rotation.x = -Math.PI / 2; bucketWater.position.y = 0.22;
  const stream = dynTube(M.waterFlow, 0.035);
  S.onUpdate(t => {
    let on = null;
    for (const [t0, t1, big] of [[E.bucket - 0.5, E.push + 0.9, false], [E.bigflush - 0.5, E.rush + 0.4, true]]) if (t > t0 && t < t1) on = [t0, t1, big];
    bucket.visible = !!on; if (!on) { stream.setPoints(null); return; }
    const [t0, t1, big] = on;
    const k = smooth(t, t0, t0 + 0.4) * (1 - smooth(t, t1 - 0.3, t1));
    const tilt = smooth(t, t0 + 0.3, t0 + 0.9) * (big ? 2.0 : 1.7);
    bucket.scale.setScalar(big ? 1.5 : 1.1);
    bucket.position.copy(T(0.95, 1.25)).add(V(0, (1 - k) * 1.2, 0.12)); bucket.rotation.set(0, 0, tilt);
    const pour = smooth(t, t0 + 0.7, t0 + 1.0) * (1 - smooth(t, t1 - 0.6, t1 - 0.2));
    if (pour > 0.05) {
      const lip = bucket.localToWorld(V(-0.145, 0.27, 0));
      const tgt = T(0.58, 0.32, 0.12);
      stream.setPoints([lip, lip.clone().lerp(tgt, 0.4).add(V(-0.05, 0.05, 0)), tgt]);
    } else stream.setPoints(null);
  });
  // "nobody wants to carry buckets": a pile of buckets with a red X
  const pileG = new THREE.Group(); add(pileG);
  for (const [dx, dy] of [[0, 0], [0.32, 0], [0.16, 0.27]]) { const b = mesh(bucketG, bucket.material, dx, dy, 0, pileG); }
  const pileX = redX(0.7); pileX.position.set(0.16, 0.25, 0.25); pileG.add(pileX);
  S.onUpdate(t => {
    const k = pop(t, E.lazy, 0.4) * (1 - smooth(t, E.tank - 0.4, E.tank));
    pileG.visible = k > 0.02; pileG.scale.setScalar(Math.max(0.02, k)); pileG.position.copy(T(1.15, 0.0, 0.25));
  });
  // waste in the bowl, caught by the bend, then siphoned away
  const bowlWaste = [0, 1, 2].map(() => { const m = mesh(new THREE.SphereGeometry(0.04, 14, 10), M.waste); m.scale.set(1.5, 0.8, 1); return m; });
  S.onUpdate(t => {
    const show = t > E.catch - 0.4 && t < E.empty + 0.2;
    const u = smooth(t, E.rush + 0.3, E.empty);
    const tp = samplePolyline([...trapPts(t), ...drainPts().slice(1, 40)], 100);
    bowlWaste.forEach((w, i) => {
      w.visible = show; if (!show) return;
      if (u > 0) { const uu = clamp(u * 1.4 - i * 0.12); w.position.copy(tp[Math.round(uu * 99)]).add(V(0, 0, 0.06)); w.visible = uu < 0.99; }
      else { const drop = smooth(t, E.catch - 0.4 + i * 0.12, E.catch + i * 0.12); w.position.copy(T([0.52, 0.58, 0.47][i], lerp(0.7, [0.2, 0.24, 0.17][i], drop), 0.05)); }
    });
  });
}

// ================================================================== rooftop extras + finale
function buildRoofExtras() {
  const chim = new THREE.Group(); chim.position.set(-0.5, RZ + ROOF, -2.2); add(chim);
  mesh(new THREE.BoxGeometry(0.7, 1.4, 0.7), M.brick, 0, 0.7, 0, chim);
  const smoke = Array.from({ length: 4 }, (_, i) => { const m = mesh(new THREE.SphereGeometry(0.18 + i * 0.05, 16, 12), new THREE.MeshStandardMaterial({ color: 0x9a9a9e, transparent: true, opacity: 0.5, depthWrite: false }), 0, 0, 0, chim); m.castShadow = false; return m; });
  const x = redX(1.4); x.position.set(0, 0.9, 0.5); chim.add(x);
  const breath = Array.from({ length: 6 }, () => { const m = mesh(new THREE.SphereGeometry(0.12, 16, 12), new THREE.MeshStandardMaterial({ color: 0xeaf6ff, transparent: true, opacity: 0, depthWrite: false })); m.castShadow = false; return m; });
  const pointer = arrowMesh(new THREE.MeshStandardMaterial({ color: 0xffd34a, emissive: 0xb08a10, emissiveIntensity: 0.6 }), 0.8, 0.06); add(pointer);
  S.onUpdate(t => {
    const k = pop(t, E.chimney - 0.2, 0.35);
    chim.visible = t > E.see && t < E.seat - 0.1 && k > 0.01; chim.scale.setScalar(Math.max(0.01, k));
    smoke.forEach((s, i) => { s.position.set(0.1 * Math.sin(i + t), 1.6 + ((t * 0.4 + i * 0.25) % 1) * 1.2, 0); });
    const kx = pop(t, E.chimney + 0.3, 0.3); x.visible = kx > 0.01; x.scale.setScalar(Math.max(0.01, kx));
    const ba = smooth(t, E.breathe - 0.3, E.breathe + 0.2);
    breath.forEach((b, i) => {
      const ph = ((t - E.breathe) * 0.8 + i / 6) % 1;
      b.visible = t > E.breathe - 0.3 && t < E.seat; b.position.set(VENT_X + 0.15 * Math.sin(i * 2 + t), RZ + ROOF + 1.1 + ph * 1.6, 0.1);
      b.scale.setScalar(1 + 2.5 * ph); b.material.opacity = 0.5 * (1 - ph) * ba;
    });
    const kp = pop(t, E.see + 0.3, 0.35);
    pointer.visible = t > E.see + 0.3 && t < E.chimney; pointer.scale.setScalar(Math.max(0.01, kp));
    pointer.position.set(VENT_X + 0.9, RZ + ROOF + 1.9, 0.2); pointer.rotation.set(0, 0, Math.PI * 0.75);
  });
  // confetti for the finale
  const N = 160;
  const conf = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.06, 0.035), new THREE.MeshStandardMaterial({ side: THREE.DoubleSide, roughness: 0.5 }), N);
  const r = rng(77), cols = [0xffcc22, 0x22b5ff, 0xff4f7a, 0x7bdc4a, 0xffffff], seeds = [];
  const c = new THREE.Color();
  for (let i = 0; i < N; i++) { conf.setColorAt(i, c.set(cols[i % 5])); seeds.push([r() - 0.5, r(), r() - 0.5, r() * 6, r() * 6]); }
  add(conf);
  const mtx = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(1, 1, 1), p = new THREE.Vector3();
  S.onUpdate(t => {
    const age = t - (E.final + 0.1);
    conf.visible = age > 0 && age < 3;
    if (!conf.visible) return;
    seeds.forEach(([vx, vy, vz, a, b], i) => {
      p.set(-0.5 + vx * 3 * age, 1.0 + (2.5 + vy * 2) * age - 2.2 * age * age, 0.8 + vz * 2 * age);
      e.set(a + age * 6, b + age * 5, 0); q.setFromEuler(e); mtx.compose(p, q, sc); conf.setMatrixAt(i, mtx);
    });
    conf.instanceMatrix.needsUpdate = true;
  });
}

// ================================================================== camera
function cameraKeys() {
  const P = (x, y, z) => [x, y, z];
  const yard = [
    { t: 0.0, pos: P(YX + 6.5, 6.5, 14), look: P(YX, 1.0, -5), fov: 44 },
    { t: E.build, pos: P(YX + 3.5, 3.2, 9.5), look: P(YX, 0.6, -1.5), fov: 40 },
    { t: E.problem, pos: P(YX + 2.2, 2.4, 7.4), look: P(YX, 1.2, -0.8), fov: 38 },
    { t: E.fill - 0.2, pos: P(YX + 1.6, 1.6, 6.8), look: P(YX, 0.6, -0.8), fov: 38 },
    { t: E.house - 0.01, pos: P(YX + 1.0, -0.2, 5.6), look: P(YX, -1.3, -0.7), fov: 38 },
  ];
  const tx = TX + 0.55 * TS;
  const house = [
    { t: E.house, pos: P(3.6, 2.6, 10.5), look: P(-0.2, 1.0, -1.5), fov: 46 },
    { t: E.seat_in - 0.1, pos: P(2.2, 2.0, 8.0), look: P(-0.6, 0.9, -1.2), fov: 44 },
    { t: E.seat_in + 0.8, pos: P(tx + 0.5, 1.2, 3.4), look: P(tx, 0.55, -0.3), fov: 40 },
    { t: E.pipe + 0.4, pos: P(1.6, 0.4, 7.4), look: P(0.6, -0.9, -0.4), fov: 44 },
    { t: E.street, pos: P(4.6, 0.6, 7.0), look: P(4.4, -1.4, -0.6), fov: 44 },
    { t: E.stuck + 0.6, pos: P(4.2, 0.2, 6.2), look: P(3.4, -1.5, -0.4), fov: 42 },
    { t: E.still + 0.6, pos: P(0.0, 0.4, 5.6), look: P(-0.9, -0.7, -0.3), fov: 42 },
    { t: E.bucket + 0.3, pos: P(tx + 0.6, 1.3, 3.6), look: P(tx + 0.1, 0.7, -0.3), fov: 40 },
    { t: E.push + 1.3, pos: P(4.6, 0.2, 6.6), look: P(4.4, -1.6, -0.3), fov: 44 },
    { t: E.gas + 1.0, pos: P(3.2, 0.0, 6.8), look: P(2.0, -1.2, -0.3), fov: 44 },
    { t: E.enter, pos: P(tx + 0.6, 1.4, 3.8), look: P(tx, 0.8, -0.4), fov: 40 },
    { t: E.bend + 0.5, pos: P(tx + 0.1, 0.55, 2.5), look: P(TX + 0.48 * TS, 0.33, -0.1), fov: 34 },
    { t: E.siphon_name, pos: P(tx - 0.05, 0.5, 2.3), look: P(TX + 0.45 * TS, 0.3, -0.1), fov: 34 },
    { t: E.air + 0.8, pos: P(tx + 0.15, 0.55, 2.5), look: P(TX + 0.48 * TS, 0.33, -0.1), fov: 34 },
    { t: E.lazy + 0.4, pos: P(tx + 0.9, 1.3, 3.6), look: P(tx + 0.3, 0.7, -0.3), fov: 40 },
    { t: E.tank + 0.6, pos: P(TX + 0.55, 1.3, 2.1), look: P(TX + 0.3 * TS, 1.2, -0.2), fov: 38 },
    { t: E.full + 0.3, pos: P(TX + 0.45, 1.25, 2.0), look: P(TX + 0.3 * TS, 1.15, -0.2), fov: 38 },
    { t: E.rush2 + 0.4, pos: P(tx + 0.1, 0.55, 2.5), look: P(TX + 0.48 * TS, 0.33, -0.1), fov: 34 },
    { t: E.gas_back + 0.5, pos: P(tx + 0.15, 0.7, 2.7), look: P(TX + 0.48 * TS, 0.42, -0.1), fov: 36 },
    { t: E.vent + 0.6, pos: P(2.2, 2.6, 11.5), look: P(-1.2, 1.6, -1.0), fov: 50 },
    { t: E.see - 0.01, pos: P(1.8, 3.0, 11.0), look: P(-1.2, 2.0, -1.0), fov: 50 },
    { t: E.see, pos: P(3.0, 6.6, 7.6), look: P(-1.4, RZ + ROOF + 0.9, -1.8), fov: 42 },
    { t: E.seat - 0.12, pos: P(2.2, 5.6, 6.2), look: P(-1.6, RZ + ROOF + 1.0, -1.6), fov: 40 },
    { t: E.seat - 0.1, pos: P(tx + 0.7, 1.1, 2.8), look: P(tx, 0.5, -0.3), fov: 40 },
    { t: E.final + 0.2, pos: P(tx + 0.9, 1.3, 3.2), look: P(tx, 0.6, -0.3), fov: 40 },
    { t: duration, pos: P(2.6, 2.4, 9.0), look: P(-0.4, 1.0, -1.2), fov: 46 },
  ];
  return { yard, house };
}

// ================================================================== build
export async function build({ scale = 1, quality = 'full' }) {
  S = new Stage({ scale, quality });
  S.setupSky({ elevation: 40, azimuth: 300, fogDensity: 0.004, envIntensity: 0.22 });
  S.setupPost({ ao: true, dof: true, aperture: 0.00006, maxblur: 0.004 });
  materials();
  const yard = buildYard();
  cutGround(S, { x0: -140, x1: 60, depth: 16, back: 80, soil: M.soil, lawn: M.lawn, holeDepth: yard.PB,
    holes: [[[YX - yard.PX, 0], [YX - yard.PX, -2.3], [YX + yard.PX, -2.3], [YX + yard.PX, 0]]],
    lawnHoles: [[[YX - yard.PX, 0], [YX + yard.PX, 0], [YX + yard.PX, yard.PB], [YX - yard.PX, yard.PB]]] });
  buildHouse();
  buildToilet();
  buildPipes();
  buildEffects();
  buildRoofExtras();
  clouds(S, { count: 18 });
  // shots: yard | house (until the rooftop) | rooftop | house finale - hard cuts with a quick white dip
  const keys = cameraKeys();
  const h = keys.house;
  const iSee = h.findIndex(k => k.t === E.see), iSeat = h.findIndex(k => k.t === E.seat - 0.1);
  cameraPath(S, [keys.yard, h.slice(0, iSee), h.slice(iSee, iSeat), h.slice(iSeat)]);
  const fade = document.getElementById('fade');
  S.onUpdate(t => {
    // shadow region follows the action
    const inYard = t < E.house;
    S.setShadowBox(new THREE.Vector3(inYard ? YX : 0.5, 0, -3), inYard ? 14 : 10);
    let a = 0;
    for (const tc of [E.house, E.see, E.seat - 0.1]) a = Math.max(a, 1 - Math.abs(t - tc) / 0.22);
    fade.style.opacity = Math.max(0, a) * 0.95;
  });
  if (EV.captions) captions(S, EV.words, { y: 0.27, size: 104 });
  await S.ready();
  return S;
}
