// Look-development demo: Saudi villa yard, cut-away ground with a pit and an outhouse,
// cinematic crane-down camera move.  Used to approve the new realistic 3D style.
import { THREE, Stage, cutGround, box, grassTufts, tree, palm, clouds, cameraPath, captions, smooth, pop, rng } from '../lib/engine.js';

export const duration = 6.0;

export async function build({ scale = 1, quality = 'full' }) {
  const S = new Stage({ scale, quality });
  S.setupSky({ elevation: 38, azimuth: 305, fogDensity: 0.0045 });
  S.setupPost({ ao: true, dof: true, aperture: 0.00008, maxblur: 0.005 });
  const sc = S.scene;

  const soil = S.pbr('soil', { tile: 3.5, normalScale: 2.4 });
  const lawn = S.pbr('grass', { tile: 2.5, normalScale: 1.2 });
  const plaster = S.pbr('plaster', { tile: 3, normalScale: 0.6 });
  const stone = S.pbr('stone', { tile: 2.4, normalScale: 1.2 });
  const wood = S.pbr('wood', { tile: 1.6, normalScale: 1.0 });
  const conc = S.pbr('concrete', { tile: 2, normalScale: 0.8 });

  // ground with the pit cut into it
  const PX = 0.7, PD = 2.3, PB = 1.5;
  cutGround(S, { x0: -40, x1: 40, depth: 16, back: 80, soil, lawn, holeDepth: PB,
    holes: [[[-PX, 0], [-PX, -PD], [PX, -PD], [PX, 0]]], lawnHoles: [[[-PX, 0], [PX, 0], [PX, PB], [-PX, PB]]] });
  // dark wet waste at the bottom of the pit
  const waste = new THREE.Mesh(new THREE.BoxGeometry(PX * 2 - 0.01, 0.5, PB - 0.01),
    new THREE.MeshStandardMaterial({ color: 0x3a2410, roughness: 0.85, envMapIntensity: 0.15, normalMap: S.tex('concrete_normal.jpg', 1), normalScale: new THREE.Vector2(2, 2) }));
  waste.position.set(0, -PD + 0.25, -PB / 2); waste.receiveShadow = true; sc.add(waste);
  S.onUpdate(t => { waste.scale.y = 1 + 1.2 * smooth(t, 2.5, 5); waste.position.y = -PD + 0.25 * waste.scale.y; });

  // dirt pile + shovel
  const pile = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), S.pbr('soil', { tile: 1.2, normalScale: 2 }));
  pile.scale.set(1.6, 0.75, 1.2); pile.position.set(-3.4, -0.25, -2.6); pile.castShadow = pile.receiveShadow = true; sc.add(pile);
  const shovel = new THREE.Group();
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 1.4, 8), new THREE.MeshStandardMaterial({ color: 0x8a6a44, roughness: 0.6 }));
  handle.position.y = 0.7; shovel.add(handle);
  const blade = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.32, 0.02), new THREE.MeshStandardMaterial({ color: 0x9aa3ab, metalness: 0.8, roughness: 0.35 }));
  shovel.add(blade); shovel.position.set(-2.4, 0.2, -2.2); shovel.rotation.set(0.15, 0.4, -0.35);
  shovel.traverse(o => { o.castShadow = true; }); sc.add(shovel);

  // outhouse: plank walls, slanted roof, door with a crescent window
  const oh = new THREE.Group(); oh.position.set(0, 0, -PB / 2); sc.add(oh);
  const W = 1.5, D = 1.4, Hh = 2.3;
  const wall = (w, h, d, x, y, z) => { const m = box(S, wood, w, h, d, x, y, z); sc.remove(m); oh.add(m); return m; };
  wall(W + 0.2, 0.12, D + 0.2, 0, 0.06, 0);
  wall(0.06, Hh, D, -W / 2, Hh / 2 + 0.12, 0); wall(0.06, Hh, D, W / 2, Hh / 2 + 0.12, 0);
  wall(W, Hh, 0.06, 0, Hh / 2 + 0.12, -D / 2);
  const door = wall(W - 0.06, Hh - 0.05, 0.06, 0, Hh / 2 + 0.12, D / 2);
  const moon = new THREE.Mesh(new THREE.CircleGeometry(0.14, 32), new THREE.MeshBasicMaterial({ color: 0x120a04 }));
  moon.position.set(0, Hh - 0.35, D / 2 + 0.035); oh.add(moon);
  const moonCut = new THREE.Mesh(new THREE.CircleGeometry(0.12, 32), wood); moonCut.position.set(0.07, Hh - 0.32, D / 2 + 0.037); oh.add(moonCut);
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), new THREE.MeshStandardMaterial({ color: 0xc9a14a, metalness: 1, roughness: 0.3 }));
  knob.position.set(W / 2 - 0.18, 1.2, D / 2 + 0.06); oh.add(knob);
  const roof = wall(W + 0.5, 0.08, D + 0.6, 0, Hh + 0.32, 0); roof.rotation.x = 0.16;
  // build-up animation: walls rise in, roof drops
  S.onUpdate(t => { const k = pop(t, 1.2, 0.6); oh.scale.set(1, Math.max(0.001, k), 1); });

  // villa (Saudi style): plastered volumes, parapet crenellations, arched-ish windows
  const vz = -17;
  const villa = (w, h, d, x, y, z) => box(S, plaster, w, h, d, x, y, z);
  villa(16, 7, 8, 0, 3.5, vz - 4);
  villa(8, 3.4, 6, -2.5, 8.7, vz - 4.5);
  const trimMat = S.pbr('plaster', { tile: 2, color: 0xc8a676 });
  box(S, trimMat, 16.3, 0.4, 8.3, 0, 7.2, vz - 4);
  const r = rng(3);
  for (let i = 0; i < 26; i++) box(S, trimMat, 0.32, 0.32, 0.3, -7.9 + i * 0.632, 7.55, vz + 0.05);
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x1f3448, roughness: 0.05, metalness: 0.2, clearcoat: 1, envMapIntensity: 1.4 });
  const frameM = new THREE.MeshStandardMaterial({ color: 0xf2ece0, roughness: 0.5 });
  for (const wx of [-5.5, -2.5, 2.5, 5.5]) for (const wy of [1.8, 4.9]) {
    box(S, frameM, 1.5, 2.0, 0.12, wx, wy, vz + 0.04);
    box(S, glass, 1.25, 1.75, 0.12, wx, wy, vz + 0.08);
    box(S, frameM, 1.7, 0.1, 0.3, wx, wy - 1.05, vz + 0.1);
  }
  box(S, S.pbr('wood', { tile: 1, color: 0x9a6a40 }), 1.8, 2.8, 0.15, 0, 1.4, vz + 0.06);
  box(S, conc, 18, 0.12, 3, 0, 0.06, vz + 1.5);
  // AC units
  for (const ax of [-7, 6.8]) box(S, new THREE.MeshStandardMaterial({ color: 0xeeeeea, roughness: 0.4 }), 1, 0.7, 0.5, ax, 5.2, vz + 0.3);
  // boundary walls (sandstone) with caps
  for (const [x, w] of [[-12.5, 9], [12.5, 9]]) {
    box(S, stone, w, 2.6, 0.35, x, 1.3, vz + 2.5);
    box(S, trimMat, w + 0.2, 0.15, 0.5, x, 2.66, vz + 2.5);
  }
  box(S, stone, 0.35, 2.6, 18, -17, 1.3, vz + 11);
  box(S, stone, 0.35, 2.6, 18, 17, 1.3, vz + 11);

  // vegetation
  palm(S, -8, -12, { height: 7.5, seed: 4, lean: 0.12 });
  palm(S, 8.5, -11, { height: 6.6, seed: 5, lean: -0.1 });
  palm(S, -13, -6, { height: 5.8, seed: 6, lean: 0.2 });
  tree(S, 12, -6, { height: 5.5, spread: 3, seed: 7 });
  tree(S, -20, -25, { height: 7, spread: 4, seed: 8 });
  tree(S, 22, -28, { height: 7.5, spread: 4.5, seed: 9 });
  for (const [x, z] of [[-4.5, -15.5], [4.5, -15.5], [-10, -9], [10.5, -14]]) {
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.3, 0.6, 20), new THREE.MeshStandardMaterial({ color: 0xa65a35, roughness: 0.7 }));
    pot.position.set(x, 0.3, z); pot.castShadow = pot.receiveShadow = true; sc.add(pot);
    tree(S, x, z, { height: 1.4, spread: 0.9, seed: Math.round(x * 7 + z) });
  }
  grassTufts(S, { count: 4000, x0: -14, x1: 14, z0: -0.02, z1: -10, height: 0.13, edgeBias: 0.55 });
  clouds(S, { count: 16 });
  S.setShadowBox(new THREE.Vector3(0, 0, -8), 22);

  // cinematic crane-down: wide establishing shot -> push in to the cut-away pit
  cameraPath(S, [
    { t: 0.0, pos: [7.5, 7.5, 15], look: [0, 1.0, -6], fov: 42 },
    { t: 2.5, pos: [3.5, 3.4, 9.5], look: [0, 0.2, -2.5], fov: 40 },
    { t: 6.0, pos: [1.6, 1.6, 7.6], look: [0, -0.3, -1.0], fov: 40 },
  ]);
  captions(S, [{ text: 'دورة', start: 2.2, end: 2.9 }, { text: 'مياه!', start: 2.9, end: 4.2 }]);
  await S.ready();
  return S;
}
