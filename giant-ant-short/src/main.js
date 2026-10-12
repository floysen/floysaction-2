import * as THREE from 'three';
import { FPS, TOTAL_FRAMES, WIDTH, HEIGHT, DURATION } from './timeline.js';
import { createWorld } from './world.js';
import { createDirector, SHOTS } from './shots.js';
import { createOverlay } from './overlay.js';
import { validate } from './validate.js';

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(WIDTH, HEIGHT);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.getElementById('stage').appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, WIDTH / HEIGHT, 0.05, 140);
const overlay = createOverlay(document.getElementById('overlay'));
const world = createWorld(scene, camera, overlay);
const director = createDirector(world);

// Deterministic entry point used by the renderer: seek to an exact frame and draw it.
window.renderFrame = (frame) => {
  const t = frame / FPS;
  const shot = director.apply(t);
  renderer.render(scene, camera);
  return shot.id;
};
window.TIMING = { FPS, TOTAL_FRAMES, DURATION, SHOTS: SHOTS.map(({ id, start, end, scene }) => ({ id, start, end, scene })) };
window.__world = world;
window.validateScene = () => validate(world, director, renderer);

// Warm up: compile shaders for both environments before the first captured frame.
for (const f of [0, 400, 700]) window.renderFrame(f);
window.renderFrame(0);
window.READY = true;

const params = new URLSearchParams(location.search);
if (params.has('preview')) {
  // Real-time preview: wall-clock only chooses WHICH frame to show; the frame itself is deterministic.
  const t0 = performance.now();
  const hud = document.getElementById('hud');
  const loop = () => {
    const f = Math.floor(((performance.now() - t0) / 1000) * FPS) % TOTAL_FRAMES;
    hud.textContent = `${(f / FPS).toFixed(2)}s  ${window.renderFrame(f)}`;
    requestAnimationFrame(loop);
  };
  loop();
}
if (params.has('frame')) window.renderFrame(Number(params.get('frame')));
