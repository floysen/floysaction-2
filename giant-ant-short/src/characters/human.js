import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { M } from '../materials.js';

// Stylised polygon human ("you"): exactly 1 head, 1 torso, 2 arms, 2 hands, 2 legs, 2 feet.
// Height ~1.8 m. Faces +Z. Limbs hang from joint groups so they can never detach.
const box = (w, h, d, r = 0.03) => new RoundedBoxGeometry(w, h, d, 2, r);

export function createHuman(name = 'human') {
  const root = new THREE.Group();
  root.name = name;
  root.userData.kind = 'human';
  const mk = (geo, mat, parent, part, pos) => {
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.receiveShadow = true;
    m.userData.part = part;
    m.userData.solid = true;
    m.position.set(...pos);
    parent.add(m);
    return m;
  };
  const pelvis = new THREE.Group();
  pelvis.position.y = 0.92;
  root.add(pelvis);
  mk(box(0.38, 0.2, 0.24), M.pants, pelvis, 'hips', [0, 0.02, 0]);

  const chest = new THREE.Group();
  chest.position.y = 0.06;
  pelvis.add(chest);
  mk(box(0.46, 0.5, 0.27, 0.07), M.hoodie, chest, 'torso', [0, 0.25, 0]);
  mk(box(0.36, 0.16, 0.12, 0.05), M.hoodie, chest, 'hood', [0, 0.47, -0.12]);

  const neck = new THREE.Group();
  neck.position.y = 0.5;
  chest.add(neck);
  mk(box(0.1, 0.08, 0.1, 0.02), M.skin, neck, 'neck', [0, 0.03, 0]);
  const head = new THREE.Group();
  head.position.y = 0.05;
  neck.add(head);
  mk(box(0.24, 0.27, 0.25, 0.06), M.skin, head, 'head', [0, 0.135, 0]);
  mk(box(0.26, 0.1, 0.27, 0.04), M.hair, head, 'hair', [0, 0.25, -0.01]);
  mk(box(0.25, 0.16, 0.06, 0.03), M.hair, head, 'hairBack', [0, 0.17, -0.11]);
  for (const s of [-1, 1]) mk(box(0.035, 0.04, 0.02, 0.008), M.eye, head, 'eye', [s * 0.055, 0.15, 0.126]);

  const arms = [-1, 1].map((s) => {
    const shoulder = new THREE.Group();
    shoulder.position.set(s * 0.29, 0.44, 0);
    chest.add(shoulder);
    mk(box(0.12, 0.32, 0.13, 0.04), M.hoodie, shoulder, 'upperArm', [0, -0.15, 0]);
    const elbow = new THREE.Group();
    elbow.position.y = -0.3;
    shoulder.add(elbow);
    mk(box(0.11, 0.28, 0.12, 0.04), M.hoodie, elbow, 'forearm', [0, -0.14, 0]);
    mk(box(0.085, 0.11, 0.07, 0.03), M.skin, elbow, 'hand', [0, -0.33, 0]);
    return { shoulder, elbow, s };
  });

  const legs = [-1, 1].map((s) => {
    const hip = new THREE.Group();
    hip.position.set(s * 0.1, -0.04, 0);
    pelvis.add(hip);
    mk(box(0.16, 0.44, 0.18, 0.04), M.pants, hip, 'thigh', [0, -0.22, 0]);
    const knee = new THREE.Group();
    knee.position.y = -0.44;
    hip.add(knee);
    mk(box(0.14, 0.4, 0.16, 0.04), M.pants, knee, 'shin', [0, -0.2, 0]);
    mk(box(0.13, 0.08, 0.27, 0.03), M.shoe, knee, 'foot', [0, -0.4, 0.05]);
    return { hip, knee, s };
  });

  // lean > 0 leans back (startled); look turns the head; t drives subtle idle breathing.
  function update({ t = 0, lean = 0, look = 0, raise = 0 }) {
    const breath = Math.sin(t * 1.7) * 0.012;
    chest.rotation.x = -lean * 0.35 + breath;
    chest.scale.set(1, 1 + breath * 0.5, 1);
    head.rotation.set(-lean * 0.2, look, 0);
    pelvis.position.z = -lean * 0.08;
    for (const a of arms) {
      a.shoulder.rotation.set(-0.08 - raise * 0.9, 0, a.s * (0.08 + raise * 0.15));
      a.elbow.rotation.x = -0.15 - raise * 1.1;
    }
    for (const l of legs) {
      l.hip.rotation.x = lean * 0.25;
      l.knee.rotation.x = lean * 0.1;
    }
  }
  update({});
  return { root, update };
}
