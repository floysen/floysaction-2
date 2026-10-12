// Segment 3 globe: stylised continents tint ant-brown as the "spread across all land"
// line plays. Continents are approximated with overlapping lat/lon blobs (illustrative).
import * as THREE from 'three';
import { rng, range, smooth, lerp, clamp } from './util.js';

const BLOBS = [
  // North America & Greenland
  [50, -100, 20], [40, -95, 15], [60, -120, 15], [65, -150, 10], [35, -110, 12], [22, -102, 8], [15, -90, 5], [68, -85, 12], [72, -40, 11], [64, -45, 8], [47, -70, 8],
  // South America
  [-5, -60, 15], [-15, -52, 13], [-28, -62, 10], [-42, -69, 6], [5, -68, 8], [-10, -75, 6],
  // Europe
  [50, 12, 11], [46, 25, 9], [60, 25, 9], [63, 12, 7], [40, -4, 6], [54, -2, 4], [43, 13, 4],
  // Africa
  [12, 2, 13], [15, 20, 14], [0, 22, 14], [-15, 26, 12], [-28, 25, 8], [25, 8, 13], [25, 28, 10], [8, 40, 7],
  // Asia
  [55, 80, 24], [60, 110, 20], [45, 100, 18], [30, 80, 11], [21, 78, 8], [30, 110, 12], [65, 140, 14], [24, 46, 9], [15, 103, 7], [42, 64, 12], [37, 137, 4],
  // Maritime SE Asia, Australia
  [0, 113, 5], [-4, 140, 6], [-25, 134, 14], [-19, 145, 7], [-42, 172, 3],
];

function landValue(lat, lon) {
  if (lat < -70) return 1;
  let best = -1;
  for (const [la, lo, r] of BLOBS) {
    const d = THREE.MathUtils.degToRad;
    const c = Math.sin(d(lat)) * Math.sin(d(la)) + Math.cos(d(lat)) * Math.cos(d(la)) * Math.cos(d(lon - lo));
    const ang = THREE.MathUtils.radToDeg(Math.acos(clamp(c, -1, 1)));
    best = Math.max(best, 1 - ang / r);
  }
  const n = 0.12 * Math.sin(lat * 0.31 + lon * 0.17) + 0.08 * Math.sin(lat * 0.73 - lon * 0.41) + 0.05 * Math.sin(lon * 1.3);
  return best + n;
}

export function buildGlobe() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x04060c);
  const camera = new THREE.PerspectiveCamera(40, 1080 / 1920, 0.1, 500);
  scene.add(new THREE.HemisphereLight(0x8fb4ff, 0x101010, 0.6));
  const sun = new THREE.DirectionalLight(0xfff0dd, 2.6); sun.position.set(-20, 10, 18); scene.add(sun);

  const geo = new THREE.SphereGeometry(5, 256, 128);
  const pos = geo.attributes.position, N = pos.count;
  const col = new Float32Array(N * 3);
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const info = [];
  const ocean = new THREE.Color(0x1c4f7c), green = new THREE.Color(0x5e8c3e), tan = new THREE.Color(0xc4a96b), ice = new THREE.Color(0xeef3f6);
  const antHi = new THREE.Color(0x5a1c0e), antLo = new THREE.Color(0xa65a32);
  for (let i = 0; i < N; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const lat = THREE.MathUtils.radToDeg(Math.asin(y / 5)), lon = THREE.MathUtils.radToDeg(Math.atan2(x, z));
    const land = landValue(lat, lon) > 0;
    let base = ocean.clone();
    let antC = null;
    if (land) {
      const desert = (lat > 15 && lat < 32 && lon > -15 && lon < 55) || (lat < -20 && lat > -32 && lon > 120 && lon < 145);
      base = lat < -66 || lat > 72 ? ice.clone() : desert ? tan.clone() : green.clone();
      // Denser tint in the tropics, where ant biomass is highest; none on ice caps.
      const w = Math.exp(-Math.pow(lat / 28, 2));
      if (!(lat < -66 || lat > 72)) antC = antLo.clone().lerp(antHi, w);
    }
    info.push({ base, antC, delay: ((lon + 180) / 360) * 1.6 });
  }
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85 });
  const earth = new THREE.Mesh(geo, mat);
  const holder = new THREE.Group(); holder.rotation.x = 0.35; holder.add(earth); scene.add(holder);

  const atm = new THREE.Mesh(new THREE.SphereGeometry(5.35, 64, 32), new THREE.ShaderMaterial({
    side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix*normal); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'varying vec3 vN; void main(){ float i = pow(0.75 - dot(vN, vec3(0,0,1.0)), 3.0); gl_FragColor = vec4(0.35,0.6,1.0,1.0)*i; }',
  }));
  scene.add(atm);
  const R = rng(9); const sp = [];
  for (let i = 0; i < 1500; i++) { const v = new THREE.Vector3(R() - 0.5, R() - 0.5, R() - 0.5).normalize().multiplyScalar(200); sp.push(v.x, v.y, v.z); }
  const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
  scene.add(new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffffff, size: 0.6, sizeAttenuation: true })));

  const c = new THREE.Color();
  function update(t) {
    earth.rotation.y = 0.9 - (t - 22) * 0.16;
    for (let i = 0; i < N; i++) {
      const f = info[i];
      c.copy(f.base);
      if (f.antC) c.lerp(f.antC, smooth(range(t, 22.6 + f.delay, 23.6 + f.delay)));
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    }
    geo.attributes.color.needsUpdate = true;
    const d = lerp(31, 27, smooth(range(t, 21.8, 26.6)));
    camera.position.set(0, 1.5, d); camera.lookAt(0, -2.6, 0);
  }
  return { scene, camera, update };
}
