import * as THREE from 'three';
import { SHOTS } from './shots.js';
import { FPS, TOTAL_FRAMES, DURATION } from './timeline.js';

// Scene-graph + timeline validation, run before rendering (npm run validate).
const ANT_PARTS = { head: 1, eye: 2, mandible: 2, antennaScape: 2, antennaFun: 4, antennaClub: 2, coxa: 6, femur: 6, knee: 6, tibia: 6, tibiaTip: 6, tarsus: 6, gaster: 1, petiole: 2 };
const HUMAN_PARTS = { head: 1, torso: 1, hips: 1, neck: 1, upperArm: 2, forearm: 2, hand: 2, thigh: 2, shin: 2, foot: 2, eye: 2 };

function countParts(root) {
  const c = {};
  root.traverse((o) => { if (o.isMesh && o.userData.part) c[o.userData.part] = (c[o.userData.part] || 0) + 1; });
  return c;
}

export function validate(world, director, renderer) {
  const errors = [], warnings = [];
  const check = (root, spec, label) => {
    const c = countParts(root);
    for (const [k, n] of Object.entries(spec)) if (c[k] !== n) errors.push(`${label}: expected ${n} ${k}, found ${c[k] || 0}`);
  };
  for (const a of [world.hero, world.labAnt, ...world.bgAnts]) check(a.root, ANT_PARTS, a.root.name);
  check(world.human.root, HUMAN_PARTS, 'human');

  // Materials present on every mesh.
  world.scene.traverse((o) => { if (o.isMesh && !o.material) errors.push(`mesh without material: ${o.name}`); });

  // Timeline coverage: shots must tile [0, DURATION) with no gaps/overlaps.
  for (let i = 0; i < SHOTS.length; i++) {
    const s = SHOTS[i];
    if (i === 0 && s.start !== 0) errors.push('first shot does not start at 0');
    if (i > 0 && Math.abs(SHOTS[i - 1].end - s.start) > 1e-9) errors.push(`gap/overlap before ${s.id}`);
    if (s.end - s.start > 4.5) warnings.push(`${s.id} is long (${(s.end - s.start).toFixed(1)}s) - make sure it has internal motion`);
  }
  if (Math.abs(SHOTS[SHOTS.length - 1].end - DURATION) > 1e-9) errors.push('last shot does not end at DURATION');

  // Per-frame checks (every 2nd frame): camera inside solid geometry, duplicate visible ants.
  const box = new THREE.Box3();
  const cam = world.camera;
  const clipFrames = {};
  for (let f = 0; f < TOTAL_FRAMES; f += 2) {
    const shotId = window.renderFrame(f);
    const p = cam.position;
    world.scene.traverseVisible((o) => {
      if (!o.isMesh || !o.userData.solid) return;
      box.setFromObject(o).expandByScalar(cam.near * 1.5);
      if (box.containsPoint(p)) {
        const key = `${shotId}:${o.userData.part || o.parent?.name || o.geometry.type}`;
        (clipFrames[key] ||= []).push(f);
      }
    });
    const ants = [world.hero, ...world.bgAnts].filter((a) => a.root.visible && world.street.group.visible);
    for (let i = 0; i < ants.length; i++) for (let j = i + 1; j < ants.length; j++)
      if (ants[i].root.position.distanceTo(ants[j].root.position) < 2.5) errors.push(`frame ${f}: ants ${i},${j} overlap`);
    // Camera must stay above ground.
    if (world.street.group.visible && p.y < 0.05) errors.push(`frame ${f}: camera below ground`);
  }
  // Ant/human limbs are rotated thin segments, so their AABBs are loose: report as warnings for frame review.
  for (const [k, frames] of Object.entries(clipFrames)) {
    const msg = `camera inside bbox of ${k} at frames ${frames[0]}..${frames[frames.length - 1]} (${frames.length})`;
    if (/femur|tibia|tarsus|antenna|coxa|knee/.test(k)) warnings.push(msg); else errors.push(msg);
  }
  const info = renderer.info;
  window.renderFrame(0);
  return { ok: errors.length === 0, errors, warnings, stats: { fps: FPS, frames: TOTAL_FRAMES, duration: DURATION, shots: SHOTS.length, geometries: info.memory.geometries, textures: info.memory.textures, programs: info.programs?.length } };
}
