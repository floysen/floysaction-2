import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { M } from '../materials.js';
import { rng } from '../timeline.js';

// Night street. Layout (metres): building facade on z=0 (interior z<0), sidewalk z 0..4 (top y=0),
// road z 4..13 (y=-0.12). "Your" window: x -0.8..0.8, y 0.9..2.3. Doorstep: x 1.6..2.8.
export const LAYOUT = {
  window: { x0: -0.8, x1: 0.8, y0: 0.9, y1: 2.3 },
  door: { x0: 1.75, x1: 2.65, y0: 0.54, y1: 2.7 },
  car: { x: 1.2, z: 5.2 },
};

const solid = (m, cast = true) => {
  m.castShadow = cast;
  m.receiveShadow = true;
  m.userData.solid = true;
  return m;
};
const boxAt = (parent, mat, w, h, d, x, y, z, r = 0) => {
  const geo = r > 0 ? new RoundedBoxGeometry(w, h, d, 2, r) : new THREE.BoxGeometry(w, h, d);
  const m = solid(new THREE.Mesh(geo, mat));
  m.position.set(x, y, z);
  parent.add(m);
  return m;
};

function buildCar() {
  const car = new THREE.Group();
  car.name = 'car';
  const ext = (pts, depth, mat, bevel = 0.05) => {
    const shape = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
    const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 2 });
    g.translate(0, 0, -depth / 2);
    return solid(new THREE.Mesh(g, mat));
  };
  car.add(ext([[-2.2, 0.3], [2.15, 0.3], [2.22, 0.72], [1.95, 0.86], [-2.05, 0.88], [-2.22, 0.68]], 1.7, M.carPaint));
  const cabin = ext([[-1.45, 0.86], [0.85, 0.86], [0.3, 1.34], [-1.05, 1.34], [-1.55, 0.9]], 1.44, M.carGlass, 0.03);
  car.add(cabin);
  boxAt(car, M.carPaint, 1.38, 0.06, 1.5, -0.37, 1.37, 0, 0.025); // roof
  for (const s of [-1, 1]) {
    boxAt(car, M.carPaint, 0.08, 0.5, 0.06, -0.38, 1.1, s * 0.73); // B-pillar
    for (const x of [-1.4, 1.4]) {
      const w = solid(new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.26, 16), M.tire));
      w.rotation.x = Math.PI / 2;
      w.position.set(x, 0.34, s * 0.8);
      car.add(w);
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.27, 10), M.carChrome);
      hub.rotation.x = Math.PI / 2;
      hub.position.copy(w.position);
      car.add(hub);
    }
    boxAt(car, M.headlight, 0.05, 0.12, 0.34, 2.2, 0.66, s * 0.6, 0.02);
    boxAt(car, M.taillight, 0.05, 0.1, 0.3, -2.24, 0.68, s * 0.62, 0.02);
  }
  boxAt(car, M.carDark, 0.12, 0.16, 1.72, 2.2, 0.36, 0, 0.03); // bumpers
  boxAt(car, M.carDark, 0.12, 0.16, 1.72, -2.24, 0.36, 0, 0.03);
  // Door cavity (visible when the door opens), then the hinged door itself on the sidewalk side (-Z).
  boxAt(car, M.carDark, 1.36, 0.5, 0.01, 0.15, 0.6, -0.925);
  const hinge = new THREE.Group();
  hinge.name = 'carDoorHinge';
  hinge.position.set(0.85, 0, -0.96);
  car.add(hinge);
  boxAt(hinge, M.carPaint, 1.4, 0.56, 0.06, -0.7, 0.6, -0.03, 0.02);
  const win = boxAt(hinge, M.carGlass, 1.0, 0.4, 0.04, -0.82, 1.08, -0.01, 0.015);
  win.scale.x = 1;
  boxAt(hinge, M.carPaint, 1.36, 0.04, 0.06, -0.72, 0.88, -0.03, 0.01);
  const handle = boxAt(hinge, M.carChrome, 0.22, 0.05, 0.05, -1.2, 0.78, -0.08, 0.015);
  car.position.set(LAYOUT.car.x, -0.12, LAYOUT.car.z);
  return { car, hinge, handle };
}

function buildFacades(group) {
  const rand = rng(11);
  // Our building: extruded wall with real openings for the window and front door.
  const w = LAYOUT.window, d = LAYOUT.door;
  const shape = new THREE.Shape([new THREE.Vector2(-4, 0), new THREE.Vector2(4.5, 0), new THREE.Vector2(4.5, 6.5), new THREE.Vector2(-4, 6.5)]);
  const hole = (x0, y0, x1, y1) => new THREE.Path([new THREE.Vector2(x0, y0), new THREE.Vector2(x0, y1), new THREE.Vector2(x1, y1), new THREE.Vector2(x1, y0)]);
  shape.holes.push(hole(w.x0, w.y0, w.x1, w.y1), hole(d.x0, d.y0, d.x1, d.y1), hole(-0.8, 3.6, 0.8, 5.0), hole(1.6, 3.6, 2.8, 5.0), hole(-3.2, 3.6, -2.0, 5.0));
  const facade = solid(new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.3, bevelEnabled: false }), M.brick));
  facade.position.z = -0.3;
  group.add(facade);
  // Window trim + mullions + sill.
  boxAt(group, M.trim, 1.8, 0.1, 0.36, 0, w.y0 - 0.05, 0.05);
  boxAt(group, M.trim, 1.8, 0.1, 0.12, 0, w.y1 + 0.05, -0.02);
  boxAt(group, M.trim, 0.08, 1.4, 0.12, w.x0 - 0.04, 1.6, -0.02);
  boxAt(group, M.trim, 0.08, 1.4, 0.12, w.x1 + 0.04, 1.6, -0.02);
  boxAt(group, M.trim, 0.05, 1.4, 0.06, 0, 1.6, -0.16);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.4), M.glass);
  glass.position.set(0, 1.6, -0.15);
  glass.renderOrder = 1;
  group.add(glass);
  // Upper floor windows: dark glass set back inside the openings.
  for (const [x0, x1] of [[-0.8, 0.8], [1.6, 2.8], [-3.2, -2.0]]) {
    boxAt(group, M.darkWindow, x1 - x0, 1.4, 0.04, (x0 + x1) / 2, 4.3, -0.2);
    boxAt(group, M.trim, x1 - x0 + 0.2, 0.1, 0.3, (x0 + x1) / 2, 3.55, 0.05);
  }
  // Front door + 3 steps (the "doorstep").
  boxAt(group, M.door, d.x1 - d.x0, d.y1 - d.y0, 0.08, (d.x0 + d.x1) / 2, (d.y0 + d.y1) / 2, -0.2);
  boxAt(group, M.trim, d.x1 - d.x0 + 0.24, 0.12, 0.2, (d.x0 + d.x1) / 2, d.y1 + 0.06, 0.02);
  for (let i = 0; i < 3; i++) boxAt(group, M.step, 1.2, 0.18 * (i + 1), 0.4, 2.2, 0.09 * (i + 1), 1.0 - i * 0.4, 0.015);
  boxAt(group, M.trim, 8.6, 0.25, 0.4, 0.25, 0.12, 0.05); // plinth
  boxAt(group, M.trim, 8.6, 0.2, 0.4, 0.25, 3.3, 0.05); // floor band

  // Neighbouring buildings (both sides of the street) with lit/dark windows via instancing.
  const winGeo = new THREE.PlaneGeometry(0.9, 1.2);
  const lit = [], dark = [];
  const mats = [M.brick2, M.brick3, M.brick];
  const addBlock = (x0, x1, h, zFront, facing) => {
    const depth = 8;
    const b = boxAt(group, mats[Math.floor(rand() * 3)], x1 - x0, h, depth, (x0 + x1) / 2, h / 2, zFront - facing * depth / 2);
    b.castShadow = false;
    for (let y = 1.2; y < h - 1; y += 2.6) {
      for (let x = x0 + 0.9; x < x1 - 0.6; x += 1.8) {
        const mtx = new THREE.Matrix4().makeRotationY(facing > 0 ? 0 : Math.PI).setPosition(x, y + 0.6, zFront + facing * 0.02);
        (rand() < 0.38 ? lit : dark).push(mtx);
      }
    }
  };
  let x = -60;
  while (x < -4) { const wdt = 5 + rand() * 4; addBlock(x, Math.min(x + wdt, -4.05), 6 + rand() * 8, 0, 1); x += wdt + 0.05; }
  x = 4.55;
  while (x < 50) { const wdt = 5 + rand() * 4; addBlock(x, x + wdt, 6 + rand() * 8, 0, 1); x += wdt + 0.05; }
  x = -60;
  while (x < 50) { const wdt = 6 + rand() * 5; addBlock(x, x + wdt, 7 + rand() * 9, 13, -1); x += wdt + 0.05; }
  for (const [list, mat] of [[lit, M.litWindow], [dark, M.darkWindow]]) {
    const im = new THREE.InstancedMesh(winGeo, mat, list.length);
    list.forEach((m, i) => im.setMatrixAt(i, m));
    group.add(im);
  }
}

function buildInterior(group) {
  const room = new THREE.Group();
  room.name = 'apartment';
  boxAt(room, M.wood, 6, 0.1, 4.8, 0, -0.05, -2.7);
  boxAt(room, M.wall, 6, 2.9, 0.1, 0, 1.45, -5.1);
  boxAt(room, M.wall, 0.1, 2.9, 4.8, -3.05, 1.45, -2.7);
  boxAt(room, M.wall, 0.1, 2.9, 4.8, 3.05, 1.45, -2.7);
  boxAt(room, M.wall, 6.2, 0.1, 4.9, 0, 2.95, -2.7);
  // Curtains: layered folds either side of the window.
  for (const s of [-1, 1]) {
    for (let i = 0; i < 4; i++) {
      const f = boxAt(room, M.curtain, 0.16, 2.3, 0.04, s * (0.95 + i * 0.13), 1.45, -0.42 - (i % 2) * 0.05);
      f.rotation.y = (i % 2 ? 0.5 : -0.5) * s;
    }
  }
  boxAt(room, M.lampPost, 2.0, 0.04, 0.04, 0, 2.6, -0.45); // curtain rail
  // Side table + lamp (practical light source for the room).
  boxAt(room, M.wood, 0.7, 0.06, 0.5, -2.2, 0.62, -3.6, 0.02);
  for (const [dx, dz] of [[-0.3, -0.2], [0.3, -0.2], [-0.3, 0.2], [0.3, 0.2]]) boxAt(room, M.wood, 0.05, 0.6, 0.05, -2.2 + dx, 0.3, -3.6 + dz);
  const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.22, 0.26, 10), M.lampShade);
  shade.position.set(-2.2, 1.0, -3.6);
  room.add(shade);
  boxAt(room, M.lampPost, 0.03, 0.3, 0.03, -2.2, 0.78, -3.6);
  const lamp = new THREE.PointLight(0xffb060, 5, 9, 2);
  lamp.position.set(-2.2, 1.25, -3.4);
  room.add(lamp);
  // Soft fill near the window so "you" read clearly from the street.
  const fill = new THREE.PointLight(0xffc890, 2.2, 4, 2);
  fill.position.set(0.9, 2.3, -1.7);
  room.add(fill);
  // Couch block for depth
  boxAt(room, M.curtain, 2.2, 0.45, 0.9, 1.4, 0.3, -4.4, 0.08);
  boxAt(room, M.curtain, 2.2, 0.5, 0.25, 1.4, 0.7, -4.75, 0.08);
  group.add(room);
}

export function createStreet() {
  const group = new THREE.Group();
  group.name = 'street';
  const rand = rng(23);
  // Ground
  boxAt(group, M.sidewalk, 120, 0.3, 4, -5, -0.15, 2);
  boxAt(group, M.curb, 120, 0.3, 0.22, -5, -0.135, 4.0);
  boxAt(group, M.asphalt, 120, 0.3, 9, -5, -0.27, 8.6);
  boxAt(group, M.sidewalk, 120, 0.3, 3, -5, -0.15, 14.4);
  // Sidewalk slab joints (thin darker strips) give scale to the "legs on concrete" close-up.
  const joint = new THREE.InstancedMesh(new THREE.BoxGeometry(0.03, 0.004, 3.9), M.asphalt, 80);
  for (let i = 0; i < 80; i++) joint.setMatrixAt(i, new THREE.Matrix4().setPosition(-40 + i * 1.2, 0.002, 2));
  joint.receiveShadow = true;
  group.add(joint);
  const dash = new THREE.InstancedMesh(new THREE.BoxGeometry(2, 0.01, 0.15), M.laneLine, 30);
  for (let i = 0; i < 30; i++) dash.setMatrixAt(i, new THREE.Matrix4().setPosition(-45 + i * 4, -0.115, 8.6));
  group.add(dash);
  // Puddles: glossy dark discs on the road.
  const puddleMat = new THREE.MeshStandardMaterial({ color: 0x1a2130, roughness: 0.05, metalness: 0.6 });
  for (let i = 0; i < 9; i++) {
    const p = new THREE.Mesh(new THREE.CircleGeometry(0.5 + rand() * 0.9, 18), puddleMat);
    p.rotation.x = -Math.PI / 2;
    p.scale.y = 0.6;
    p.position.set(-14 + rand() * 24, -0.117 + i * 0.0002, 6.5 + rand() * 5);
    group.add(p);
  }

  buildFacades(group);
  buildInterior(group);
  const { car, hinge, handle } = buildCar();
  group.add(car);

  // Street lamps
  const lampLights = [];
  for (const [lx, lz, light] of [[-5.5, 3.5, true], [6.5, 3.5, true], [-17, 3.5, true], [-30, 3.5, false], [14, 13.6, false], [-8, 13.6, true]]) {
    const facing = lz > 8 ? -1 : 1;
    boxAt(group, M.lampPost, 0.14, 4.4, 0.14, lx, 2.2, lz, 0.03);
    boxAt(group, M.lampPost, 0.1, 0.1, 1.0, lx, 4.35, lz + facing * 0.5);
    const bulb = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.08, 0.5), M.lampBulb);
    bulb.position.set(lx, 4.27, lz + facing * 0.9);
    group.add(bulb);
    if (light) {
      const pl = new THREE.PointLight(0xffb36b, 34, 22, 2);
      pl.position.set(lx, 4.0, lz + facing * 0.9);
      group.add(pl);
      lampLights.push(pl);
    }
  }

  // Lighting: cool moonlight key (shadows) + sky fill.
  const hemi = new THREE.HemisphereLight(0x7088c0, 0x1c1a22, 1.0);
  group.add(hemi);
  const moon = new THREE.DirectionalLight(0xa9c0ff, 1.7);
  moon.position.set(-6, 14, 14);
  moon.target.position.set(0, 0, 2.5);
  moon.castShadow = true;
  moon.shadow.mapSize.set(2048, 2048);
  Object.assign(moon.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 50 });
  moon.shadow.bias = -0.0006;
  moon.shadow.normalBias = 0.03;
  group.add(moon, moon.target);
  const rim = new THREE.DirectionalLight(0x6fd8ff, 0.55);
  rim.position.set(8, 6, -4);
  group.add(rim);

  // Rain: instanced streaks with fully deterministic positions (function of t only).
  const N = 2600;
  const rain = new THREE.InstancedMesh(new THREE.BoxGeometry(0.012, 0.42, 0.012), M.rain, N);
  rain.frustumCulled = false;
  const drops = Array.from({ length: N }, () => [-30 + rand() * 42, rand() * 12, 0.4 + rand() * 12, 8 + rand() * 3]);
  group.add(rain);
  const dm = new THREE.Matrix4();
  function updateRain(t) {
    drops.forEach(([x, y0, z, v], i) => {
      const y = 12 - ((y0 + t * v) % 12.2);
      dm.makeTranslation(x, y, z);
      rain.setMatrixAt(i, dm);
    });
    rain.instanceMatrix.needsUpdate = true;
  }

  // Splash rings under the hero ant's feet.
  const rings = Array.from({ length: 6 }, () => {
    const r = new THREE.Mesh(new THREE.RingGeometry(0.09, 0.13, 20), M.splash.clone());
    r.rotation.x = -Math.PI / 2;
    r.visible = false;
    group.add(r);
    return r;
  });

  return { group, car, hinge, handle, updateRain, rings, moon };
}
