import * as THREE from 'three';
import { M } from '../materials.js';

// Scale-comparison "lab": a clean measuring stage, deliberately abstract so it reads as an explainer
// diagram, not a real place. Lives far from the street; only one environment is visible at a time.
export const LAB_ORIGIN = new THREE.Vector3(0, 0, -400);

export function createLab() {
  const group = new THREE.Group();
  group.name = 'lab';
  group.position.copy(LAB_ORIGIN);

  const floor = new THREE.Mesh(new THREE.CircleGeometry(30, 64), new THREE.MeshStandardMaterial({ color: 0x1b2c35, roughness: 0.85 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  floor.userData.solid = true;
  group.add(floor);

  // Multi-scale measuring grid (1 cm / 10 cm / 1 m) - each fades in only when the camera is close
  // enough for it to be readable, so the grid itself communicates the change of scale.
  const grids = [
    { cell: 0.01, size: 0.6, color: 0x5d8798, y: 0.00012 },
    { cell: 0.1, size: 6, color: 0x4b7384, y: 0.00024 },
    { cell: 1, size: 40, color: 0x3b6070, y: 0.0005 },
  ].map((g) => {
    const n = Math.round(g.size / g.cell);
    const grid = new THREE.GridHelper(g.size, n, g.color, g.color);
    grid.material.transparent = true;
    grid.material.depthWrite = false;
    grid.position.y = g.y;
    group.add(grid);
    return { ...g, grid };
  });

  const wall = new THREE.Mesh(new THREE.CylinderGeometry(22, 22, 30, 48, 1, true, Math.PI * 0.55, Math.PI * 0.9), M.labWall);
  wall.material = M.labWall.clone();
  wall.material.side = THREE.BackSide;
  wall.position.y = 15;
  group.add(wall);

  // Coin (24 mm) as the real-world size reference next to the 3-4 mm ant.
  const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.0018, 32), M.coin.clone());
  coin.material.transparent = true;
  coin.position.set(-0.004, 0.0009, -0.026);
  coin.castShadow = true;
  group.add(coin);

  // Blob contact shadow under the ant (real shadow maps can't resolve a 7 mm ant).
  const blob = new THREE.Mesh(new THREE.CircleGeometry(1, 32), M.blob);
  blob.rotation.x = -Math.PI / 2;
  blob.position.y = 0.0003;
  group.add(blob);

  // Weight vs strength bars (heights in metres, base on the floor).
  const barGeo = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);
  const weightBar = new THREE.Mesh(barGeo, M.weight);
  weightBar.position.set(1.9, 0, -2.2);
  weightBar.castShadow = true;
  group.add(weightBar);
  const strengthBar = new THREE.Mesh(barGeo, M.strength);
  strengthBar.position.set(2.6, 0, -1.5);
  strengthBar.castShadow = true;
  group.add(strengthBar);

  // Downward "weight" arrow pressing on the ant's back.
  const arrow = new THREE.Group();
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.7, 12), M.weight);
  shaft.position.y = 0.55;
  const tip = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.38, 12), M.weight);
  tip.rotation.x = Math.PI;
  tip.position.y = 0.0;
  arrow.add(shaft, tip);
  group.add(arrow);

  const hemi = new THREE.HemisphereLight(0xa8dcff, 0x1a2630, 1.25);
  const key = new THREE.DirectionalLight(0xfff0dc, 2.4);
  key.position.set(5, 9, 7);
  key.target.position.set(0, 0, 0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 30 });
  key.shadow.bias = -0.0005;
  key.shadow.normalBias = 0.02;
  const rim = new THREE.DirectionalLight(0x66d9ff, 1.2);
  rim.position.set(-6, 4, -6);
  group.add(hemi, key, key.target, rim);

  return { group, grids, coin, blob, weightBar, strengthBar, arrow };
}
