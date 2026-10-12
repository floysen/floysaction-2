// The park: one persistent location reused across all segments.
// Layout (metres): path curves through z≈2 at x=0; fountain (7,-5); bench (-4,-0.5);
// sidewalk z -11..-13; road/tram z -13..-20; brick block front at z -23.
import * as THREE from 'three';
import { rng, lerp, range, smooth, clamp } from './util.js';
import { std, makeOak, makeBench, makeLamp, makeFountain, makeTram, makeBuilding } from './models.js';

export const CRACK = new THREE.Vector3(0.3, 0.0, 2.2);
export const FOUNTAIN = new THREE.Vector3(7, 0, -5);
export const TREES = [[-10, -6, 11], [13, 7, 23], [-7, 7.5, 37]];

const pathCurve = new THREE.CatmullRomCurve3(
  [[-45, 11], [-30, 8], [-15, 4], [0, 2], [15, -1], [30, -3], [45, -4]].map(([x, z]) => new THREE.Vector3(x, 0, z)));
const pathSamples = pathCurve.getSpacedPoints(400);
export function pathZ(x) {
  for (let i = 1; i < pathSamples.length; i++) {
    const a = pathSamples[i - 1], b = pathSamples[i];
    if (x <= b.x) return lerp(a.z, b.z, clamp((x - a.x) / (b.x - a.x)));
  }
  return pathSamples[pathSamples.length - 1].z;
}

function ribbon(curve, width, y, n = 300) {
  const pts = curve.getSpacedPoints(n), pos = [], idx = [];
  for (let i = 0; i <= n; i++) {
    const tan = curve.getTangentAt(i / n); const nx = -tan.z, nz = tan.x;
    const p = pts[i];
    pos.push(p.x + nx * width / 2, y, p.z + nz * width / 2, p.x - nx * width / 2, y, p.z - nz * width / 2);
    if (i < n) { const k = i * 2; idx.push(k, k + 2, k + 1, k + 1, k + 2, k + 3); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  return g;
}

const decal = (geo, mat, y) => { const m = new THREE.Mesh(geo, mat); m.rotation.x = -Math.PI / 2; m.position.y = y; m.receiveShadow = true; return m; };

export function buildWorld() {
  const scene = new THREE.Scene();
  const R = rng(1234);

  // Sky dome with a vertical gradient (drawn first, never depth-tested).
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthTest: false, depthWrite: false, fog: false,
    uniforms: { top: { value: new THREE.Color() }, horizon: { value: new THREE.Color() }, bottom: { value: new THREE.Color() } },
    vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'uniform vec3 top; uniform vec3 horizon; uniform vec3 bottom; varying vec3 vP; void main(){ float h=vP.y; vec3 c = h>0.0 ? mix(horizon, top, pow(clamp(h,0.0,1.0),0.6)) : mix(horizon,bottom,clamp(-h*4.0,0.0,1.0)); gl_FragColor=vec4(c,1.0);}',
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(1000, 32, 16), skyMat);
  sky.renderOrder = -10; sky.frustumCulled = false; scene.add(sky);

  scene.fog = new THREE.Fog(0xf3c99a, 60, 260);
  const hemi = new THREE.HemisphereLight(0xbcd3ff, 0x5a4a2a, 0.9); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffc98a, 3);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0004;
  scene.add(sun, sun.target);

  // Ground, lawn and far fields.
  const lawnMat = std(0x5f8f3a, { r: 0.95 });
  const ground = decal(new THREE.PlaneGeometry(600, 600), lawnMat, 0); scene.add(ground);

  // Gravel path.
  const pathMat = std(0xbfae8c, { r: 1 });
  scene.add(new THREE.Mesh(ribbon(pathCurve, 3.4, 0.012), pathMat));
  const edge = new THREE.Mesh(ribbon(pathCurve, 3.7, 0.008), std(0x8d7f66)); scene.add(edge);
  scene.children.slice(-2).forEach((m) => { m.receiveShadow = true; });

  // Pebbles: coarse on the whole path, fine around the crack (macro shot).
  const peb = new THREE.DodecahedronGeometry(1, 0);
  const pebMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9, flatShading: true });
  const pebCols = [0xcfc2a4, 0xa89a7c, 0xe2d6bc, 0x8e8068, 0xb6a888].map((c) => new THREE.Color(c));
  const NP = 5200, pebbles = new THREE.InstancedMesh(peb, pebMat, NP);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3(), sc = new THREE.Vector3();
  for (let i = 0; i < NP; i++) {
    let x, z, s;
    if (i < 1400) { x = CRACK.x + (R() - 0.5) * 0.7; z = CRACK.z + (R() - 0.5) * 0.6; s = 0.0012 + R() * 0.0022; }
    else { x = -30 + R() * 60; z = pathZ(x) + (R() - 0.5) * 3.2; s = 0.008 + R() * 0.02; }
    e.set(R() * 3, R() * 3, R() * 3); q.setFromEuler(e);
    m4.compose(v.set(x, 0.012 + s * 0.3, z), q, sc.set(s, s * 0.6, s * 1.2));
    pebbles.setMatrixAt(i, m4); pebbles.setColorAt(i, pebCols[i % 5]);
  }
  pebbles.receiveShadow = true; pebbles.castShadow = true; scene.add(pebbles);

  // The crack in the gravel: a jagged dark seam.
  const crackMat = new THREE.MeshStandardMaterial({ color: 0x1a120b, roughness: 1, polygonOffset: true, polygonOffsetFactor: -2 });
  let cx = CRACK.x - 0.12, cz = CRACK.z - 0.05;
  for (let i = 0; i < 9; i++) {
    const a = 0.35 + Math.sin(i * 1.7) * 0.6, len = 0.025 + R() * 0.02;
    const seg = decal(new THREE.PlaneGeometry(len, 0.0045 + R() * 0.004), crackMat, 0.0135);
    seg.position.x = cx + Math.cos(a) * len / 2; seg.position.z = cz + Math.sin(a) * len / 2; seg.rotation.z = -a;
    scene.add(seg); cx += Math.cos(a) * len; cz += Math.sin(a) * len;
  }

  // Sidewalk slabs (instanced), road, markings, tram rails, far sidewalk.
  const slabMat = std(0xb9b4aa, { r: 0.9 });
  const slabs = new THREE.InstancedMesh(new THREE.BoxGeometry(1.46, 0.12, 0.96), slabMat, 220);
  let si = 0;
  for (let x = -60; x < 60; x += 1.5) for (const z of [-11.5, -12.5]) {
    if (x > -4.6 && x < -0.5) continue; // dynamic slabs live here
    m4.makeTranslation(x, 0.06, z); slabs.setMatrixAt(si++, m4);
  }
  slabs.count = si; slabs.receiveShadow = true; scene.add(slabs);
  const dynSlabs = [];
  for (const x of [-4.0, -2.5, -1.0]) for (const z of [-11.5, -12.5]) {
    const pivot = new THREE.Group(); pivot.position.set(x + (x < -2.5 ? -0.73 : x > -2.5 ? 0.73 : 0), 0.06, z);
    const sl = new THREE.Mesh(new THREE.BoxGeometry(1.46, 0.12, 0.96), slabMat); sl.castShadow = sl.receiveShadow = true;
    sl.position.x = x - pivot.position.x; pivot.add(sl); scene.add(pivot);
    dynSlabs.push({ pivot, x, z });
  }
  const curb = new THREE.Mesh(new THREE.BoxGeometry(200, 0.18, 0.25), std(0x9a958c)); curb.position.set(0, 0.09, -13.05); scene.add(curb);
  const road = decal(new THREE.PlaneGeometry(200, 7), std(0x3a3c40, { r: 0.95 }), 0.01); road.position.z = -16.5; scene.add(road);
  for (let x = -90; x < 90; x += 6) { const d = decal(new THREE.PlaneGeometry(2.4, 0.15), std(0xe8e4d8), 0.015); d.position.set(x, 0.015, -14.4); scene.add(d); }
  const railMat = std(0x9aa0a6, { m: 0.8, r: 0.35 });
  for (const z of [-15.8, -17.2]) { const r = new THREE.Mesh(new THREE.BoxGeometry(200, 0.06, 0.08), railMat); r.position.set(0, 0.04, z); scene.add(r); }
  const walk2 = decal(new THREE.PlaneGeometry(200, 3), std(0xaaa59b), 0.02); walk2.position.z = -21.5; scene.add(walk2);
  for (let x = -40; x <= 40; x += 20) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 6.5, 6), std(0x30343a, { m: 0.5 })); p.position.set(x, 3.25, -19.6); p.castShadow = true; scene.add(p); }
  const wire = new THREE.Mesh(new THREE.BoxGeometry(200, 0.02, 0.02), std(0x222222)); wire.position.set(0, 5.6, -16.5); scene.add(wire);

  // Buildings: the brick block plus a varied skyline behind it.
  const block = makeBuilding({ w: 46, h: 16, d: 10, color: 0x9a4a35 }); block.position.set(0, 0, -28); scene.add(block);
  const RB = rng(99);
  const cols = [0xc7b59a, 0x8d6a52, 0xa9a49a, 0xb8806a, 0x7f8a8f];
  for (let i = 0; i < 14; i++) {
    const w = 10 + RB() * 12, h = 10 + RB() * 22;
    const b = makeBuilding({ w, h, d: 10, color: cols[i % 5], floors: Math.max(3, Math.floor(h / 3.4)) });
    const side = i % 2 ? 1 : -1;
    b.position.set(side * (30 + Math.floor(i / 2) * 7 + RB() * 4), 0, -30 - RB() * 30 - (i > 7 ? 25 : 0));
    if (i > 9) b.position.set((RB() - 0.5) * 120, 0, 50 + RB() * 30);
    scene.add(b);
  }

  // Trees, bench, lamps, fountain.
  const trees = TREES.map(([x, z, seed], i) => { const t = makeOak(seed, { lowBranch: i === 2 }); t.root.position.set(x, 0, z); scene.add(t.root); return t; });
  const bench = makeBench(); bench.position.set(-4, 0, -0.6); scene.add(bench);
  for (const x of [-18, -6, 6, 18]) { const l = makeLamp(); l.position.set(x, 0, pathZ(x) - 2.3); scene.add(l); }
  const fountain = makeFountain(); fountain.position.copy(FOUNTAIN); scene.add(fountain);

  // Grass tufts (instanced, coloured per instance).
  const grassGeo = new THREE.ConeGeometry(0.03, 0.16, 3); grassGeo.translate(0, 0.08, 0);
  const grassMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 });
  const NG = 7000, grass = new THREE.InstancedMesh(grassGeo, grassMat, NG);
  const gcols = [0x4f8a30, 0x6a9a3a, 0x3e7428, 0x7aa848].map((c) => new THREE.Color(c));
  let gi = 0;
  while (gi < NG) {
    const near = gi < 2500;
    const x = near ? (R() - 0.5) * 16 : (R() - 0.5) * 60, z = near ? 1 + (R() - 0.5) * 12 : -10 + R() * 26;
    if (Math.abs(z - pathZ(x)) < 1.9 || v.set(x, 0, z).distanceTo(FOUNTAIN) < 2.4) continue;
    e.set((R() - 0.5) * 0.5, R() * 6, (R() - 0.5) * 0.5); q.setFromEuler(e);
    const s = 0.6 + R() * 0.9;
    m4.compose(v.set(x, 0, z), q, sc.set(s, s, s)); grass.setMatrixAt(gi, m4); grass.setColorAt(gi, gcols[gi % 4]); gi++;
  }
  grass.receiveShadow = true; scene.add(grass);

  // Flower beds (wilt in segment 6).
  const NF = 150;
  const stems = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.008, 0.01, 1, 4).translate(0, 0.5, 0), std(0x3f7a2a), NF);
  const heads = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.045, 0), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.6, flatShading: true }), NF);
  const fcols = [0xf2d23a, 0xe8573e, 0xf4f0e8, 0xb056c8].map((c) => new THREE.Color(c));
  const flowers = [];
  for (let i = 0; i < NF; i++) {
    const bed = i < 80 ? [-1.8, 4.7] : [-4, -2.6];
    const a = R() * 6.28, r = Math.sqrt(R()) * 1.1;
    flowers.push({ x: bed[0] + Math.cos(a) * r, z: bed[1] + Math.sin(a) * r * 0.7, h: 0.22 + R() * 0.18, lean: R() * 6.28, w: R() });
    heads.setColorAt(i, fcols[i % 4]);
  }
  for (const bed of [[-1.8, 4.7], [-4, -2.6]]) { const s = decal(new THREE.CircleGeometry(1.25, 20), std(0x4a3524), 0.006); s.position.set(bed[0], 0.006, bed[1]); s.scale.y = 0.75; scene.add(s); }
  stems.castShadow = heads.castShadow = true; scene.add(stems, heads);

  // Segment 6 assets: dry patches, seeds, aphids.
  const patchMat = std(0xc2a85a, { r: 1 }), bareMat = std(0x8a6a44, { r: 1 });
  const patches = [];
  for (let i = 0; i < 40; i++) {
    const x = -16 + R() * 32, z = -9 + R() * 18;
    if (Math.abs(z - pathZ(x)) < 2.0) continue;
    const pm = decal(new THREE.CircleGeometry(1, 9), i % 3 ? patchMat : bareMat, 0.004 + i * 0.00005);
    pm.position.set(x, pm.position.y, z); pm.rotation.z = R() * 6; pm.userData = { s: 0.8 + R() * 2.2, d: R() };
    pm.scale.setScalar(0.0001); scene.add(pm); patches.push(pm);
  }
  const NS = 420;
  const seeds = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 6, 4), std(0x6a4524, { r: 0.6 }), NS);
  const seedData = [];
  for (let i = 0; i < NS; i++) seedData.push({ x: -3.5 + R() * 6.5, z: 0.2 + R() * 5.2, rz: R() * 6, d: R(), s: 0.013 + R() * 0.01 });
  seeds.castShadow = true; scene.add(seeds);
  const NA = 260;
  const aphids = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 6, 5), std(0x9ad13a, { r: 0.5 }), NA);
  const aphidData = []; const leaves = trees[2].leaves;
  for (let i = 0; i < NA; i++) { const leaf = leaves[i % leaves.length]; aphidData.push({ leaf, x: (R() - 0.5) * 0.05, y: (R() - 0.5) * 0.12, d: R() }); }
  aphids.frustumCulled = false; scene.add(aphids);

  // ------------------------------------------------------- per-frame update
  const sunDir = new THREE.Vector3();
  const golden = { sun: new THREE.Color(0xffc48a), top: new THREE.Color(0x6f9ccf), hor: new THREE.Color(0xf6c99a) };
  const noon = { sun: new THREE.Color(0xfff2df), top: new THREE.Color(0x4f86c6), hor: new THREE.Color(0xd6e2ea) };
  const tmpC = new THREE.Color(), lawnA = new THREE.Color(0x5f8f3a), lawnB = new THREE.Color(0x8f9a48);

  function env(t) {
    // Sun elevation/azimuth as pure functions of t.
    let el = 0.2, az = -1.23;
    if (t >= 40 && t < 50) el = lerp(0.2, 0.65, smooth(range(t, 40, 49)));
    if (t >= 50) {
      const u = range(t, 50, 57);
      el = 0.2 + 0.45 * (0.5 - 0.5 * Math.cos(u * 5 * Math.PI + Math.PI));
      az = -1.23 + u * 6 * Math.PI;
    }
    sunDir.set(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
    const k = clamp((el - 0.2) / 0.45);
    sun.color.copy(golden.sun).lerp(noon.sun, k);
    sun.intensity = lerp(3.0, 3.4, k);
    hemi.intensity = lerp(0.85, 1.1, k);
    skyMat.uniforms.top.value.copy(golden.top).lerp(noon.top, k);
    skyMat.uniforms.horizon.value.copy(golden.hor).lerp(noon.hor, k);
    skyMat.uniforms.bottom.value.set(0x55603a);
    scene.fog.color.copy(skyMat.uniforms.horizon.value);
    return sunDir;
  }

  function update(t, cam, camTarget) {
    const dir = env(t);
    sky.position.copy(cam.position);
    // Shadow frustum follows the subject so macro and wide shots both get crisp shadows.
    const dist = cam.position.distanceTo(camTarget);
    const size = clamp(dist * 1.1, 0.25, 48);
    sun.target.position.copy(camTarget);
    sun.position.copy(camTarget).addScaledVector(dir, size * 3 + 5);
    const sc2 = sun.shadow.camera;
    sc2.left = -size; sc2.right = size; sc2.top = size; sc2.bottom = -size;
    sc2.near = 0.05; sc2.far = size * 6 + 20; sc2.updateProjectionMatrix();
    sun.shadow.normalBias = size * 0.002;
    scene.fog.near = dist < 2 ? 30 : 60; scene.fog.far = 260;

    fountain.userData.update(t);
    for (const tr of trees) tr.canopy.rotation.z = Math.sin(t * 0.7 + tr.root.position.x) * 0.012;

    // Sidewalk slabs lift as the sidewalk ant emerges (segment 2).
    const lift = smooth(range(t, 11.0, 12.3));
    for (const s of dynSlabs) {
      const dirSign = s.x < -2.5 ? 1 : s.x > -2.5 ? -1 : 0;
      s.pivot.rotation.z = dirSign * 0.55 * lift;
      if (dirSign === 0) { s.pivot.position.y = 0.06 + 0.25 * lift; s.pivot.rotation.x = (s.z > -12 ? 1 : -1) * 0.4 * lift; }
    }

    // Segment 6 time-lapse: lawn dries, seeds lie uncollected, aphids multiply, flowers wilt.
    const soil = smooth(range(t, 52.0, 56.5));
    grassMat.color.copy(lawnA.clone().set(0xffffff)).lerp(tmpC.set(0xd8c070), soil * 0.8);
    lawnMat.color.copy(lawnA).lerp(lawnB, soil * 0.7);
    for (const p of patches) { const g = smooth(range(t, 52.2 + p.userData.d * 1.2, 55.5 + p.userData.d)); p.scale.setScalar(Math.max(0.0001, g * p.userData.s)); }
    for (let i = 0; i < NS; i++) {
      const d = seedData[i], g = smooth(range(t, 53.6 + d.d * 1.6, 54.0 + d.d * 1.6));
      e.set(0, d.rz, Math.PI / 2); q.setFromEuler(e);
      m4.compose(v.set(d.x, 0.012 + d.s * 0.5, d.z), q, sc.set(d.s * 0.6 * g + 1e-5, d.s * 1.4 * g + 1e-5, d.s * 0.6 * g + 1e-5));
      seeds.setMatrixAt(i, m4);
    }
    seeds.instanceMatrix.needsUpdate = true;
    const cl = trees[2].root.userData.leafCluster; cl.updateMatrixWorld(true);
    for (let i = 0; i < NA; i++) {
      const a = aphidData[i], g = smooth(range(t, 54.6 + a.d * 1.6, 54.9 + a.d * 1.6));
      v.set(a.x, a.y, 0.008).applyMatrix4(a.leaf.matrixWorld);
      m4.compose(v, q.identity(), sc.set(0.007 * g + 1e-5, 0.006 * g + 1e-5, 0.009 * g + 1e-5));
      aphids.setMatrixAt(i, m4);
    }
    aphids.instanceMatrix.needsUpdate = true;
    const wilt = smooth(range(t, 55.8, 57.5));
    for (let i = 0; i < NF; i++) {
      const f = flowers[i], sway = Math.sin(t * 1.3 + i) * 0.04;
      const lean = 0.08 + sway + wilt * (0.9 + f.w * 0.5);
      e.set(Math.cos(f.lean) * lean, 0, Math.sin(f.lean) * lean); q.setFromEuler(e);
      const h = f.h * (1 - wilt * 0.35);
      m4.compose(v.set(f.x, 0, f.z), q, sc.set(1, h, 1)); stems.setMatrixAt(i, m4);
      const top = new THREE.Vector3(0, h, 0).applyQuaternion(q).add(v);
      const hs = 1 - wilt * 0.6;
      m4.compose(top, q, sc.set(hs, hs * 0.7, hs)); heads.setMatrixAt(i, m4);
    }
    stems.instanceMatrix.needsUpdate = heads.instanceMatrix.needsUpdate = true;
  }

  return { scene, update, sun, pathZ, trees };
}
