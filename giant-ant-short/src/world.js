import * as THREE from 'three';
import { createStreet } from './env/street.js';
import { createLab } from './env/lab.js';
import { createAnt } from './characters/ant.js';
import { createHuman } from './characters/human.js';
import { M } from './materials.js';

export function createWorld(scene, camera, overlay) {
  const street = createStreet();
  const lab = createLab();
  scene.add(street.group, lab.group);

  const hero = createAnt('heroAnt', 7);
  street.group.add(hero.root);
  const bgAnts = [1, 2, 3].map((i) => {
    const a = createAnt('bgAnt' + i, 7); // same seed => identical design
    street.group.add(a.root);
    return a;
  });
  const labAnt = createAnt('labAnt', 7);
  labAnt.root.rotation.y = -0.55; // 3/4 view: foreshortens the long body for the vertical frame
  lab.group.add(labAnt.root);

  const human = createHuman('you');
  human.root.position.set(0.1, 0, -0.78);
  street.group.add(human.root);
  let humanHead = null;
  human.root.traverse((o) => { if (o.userData.part === 'head') humanHead = o; });


  const chips = new THREE.InstancedMesh(new THREE.TetrahedronGeometry(1, 0), M.chip, 18);
  chips.frustumCulled = false;
  chips.castShadow = true;
  street.group.add(chips);

  return {
    scene, camera, overlay, street, lab, hero, bgAnts, labAnt, human, humanHead, chips,
    bg: { street: new THREE.Color(0x0f1828), lab: new THREE.Color(0x14232c) },
    fog: { street: new THREE.FogExp2(0x0f1828, 0.03), lab: new THREE.Fog(0x14232c, 25, 70) },
  };
}
