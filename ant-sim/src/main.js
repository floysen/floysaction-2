// Entry point: builds everything once, exposes a deterministic renderFrame(frameIndex).
import * as THREE from 'three';
import { FPS, TOTAL_FRAMES } from './timeline.js';
import { buildWorld } from './world.js';
import { buildActors } from './actors.js';
import { buildCutaway } from './cutaway.js';
import { buildGlobe } from './globe.js';
import { buildXray } from './xray.js';
import { buildShots, cameraAt } from './camera.js';
import { buildOverlay } from './overlay.js';

const W = 1080, H = 1920;
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, logarithmicDepthBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const world = buildWorld();
const actors = buildActors(world.scene);
const cut = buildCutaway(world.scene);
const globe = buildGlobe();
const xray = buildXray(actors.F.a);
const shots = buildShots(actors.F);
const overlay = buildOverlay(document.getElementById('overlay'));
const camera = new THREE.PerspectiveCamera(45, W / H, 0.003, 3000);

// Freeze the segment-5 knee anchor from the pose at t = 40 s (deterministic, order-independent).
actors.update(40);
world.scene.updateMatrixWorld(true);
shots.freezeKnee(shots.knee());

export function renderFrame(frameIndex) {
  const t = frameIndex / FPS;
  overlay(t);
  const cam = cameraAt(shots, t);
  if (cam.globe) {
    globe.update(t);
    renderer.render(globe.scene, globe.camera);
    return t;
  }
  actors.update(t);
  cut.update(t);
  xray.update(t);
  camera.position.copy(cam.p);
  camera.fov = cam.fov;
  camera.near = Math.max(0.003, cam.p.distanceTo(cam.q) * 0.02);
  camera.updateProjectionMatrix();
  camera.lookAt(cam.q);
  world.update(t, camera, cam.q);
  renderer.render(world.scene, camera);
  return t;
}
window.renderFrame = renderFrame;
window.TOTAL_FRAMES = TOTAL_FRAMES;

const params = new URLSearchParams(location.search);
if (!params.has('render')) {
  // Preview: fit the 1080x1920 stage to the window; ?t=SECONDS to hold a frame.
  const stage = document.getElementById('stage');
  const fit = () => { stage.style.transform = `scale(${Math.min(innerWidth / W, innerHeight / H)})`; };
  fit(); addEventListener('resize', fit);
  if (params.has('t')) renderFrame(Math.round(parseFloat(params.get('t')) * FPS));
  else {
    const start = performance.now();
    const loop = () => { const f = Math.floor(((performance.now() - start) / 1000) * FPS) % TOTAL_FRAMES; renderFrame(f); requestAnimationFrame(loop); };
    loop();
  }
}
await document.fonts.ready;
window.__ready = true;
