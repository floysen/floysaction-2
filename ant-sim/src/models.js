// Procedural low-poly models. Every model is built from primitives at runtime.
import * as THREE from 'three';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { rng } from './util.js';
import { tex, rep } from './textures.js';

export const std = (color, o = {}) =>
  new THREE.MeshStandardMaterial({ color, roughness: o.r ?? 0.85, metalness: o.m ?? 0, flatShading: o.flat ?? false,
    map: o.map ?? null, bumpMap: o.bump ?? null, bumpScale: o.bs ?? 1 });
// Textured PBR material from a procedural texture pair.
export const pbr = (pair, o = {}) => std(o.color ?? 0xffffff, { ...o, map: pair.color, bump: pair.bump, bs: o.bs ?? 2 });
// Ant cuticle: glossy wax layer over a pitted, slightly translucent-looking shell.
const chit = (color, r) => new THREE.MeshPhysicalMaterial({ color, roughness: r, metalness: 0.05, clearcoat: 0.8, clearcoatRoughness: 0.22,
  bumpMap: tex().chitin, bumpScale: 0.6});

// A limb segment that extends along local +x from 0 to len, with a child group at its tip.
function limb(len, r0, r1, mat, radial = 8) {
  const g = new THREE.Group();
  const geo = new THREE.CylinderGeometry(r1, r0, len, radial, 1);
  geo.rotateZ(-Math.PI / 2);
  geo.translate(len / 2, 0, 0);
  const mesh = new THREE.Mesh(geo, mat);
  g.add(mesh);
  const end = new THREE.Group();
  end.position.x = len;
  g.add(end);
  g.userData = { mesh, end };
  return g;
}

// ---------------------------------------------------------------- ANT ----
// Unit body length = 1 (head to gaster tip). Scale the root to the target length.
// Forward is +z. Six legs, two elbowed antennae, mandibles, compound eyes, spiracles.
export function makeAnt(detail = 1) {
  const ws = detail ? 18 : 12, hs = detail ? 12 : 8, rs = detail ? 8 : 5;
  const M = {
    red: chit(0x8f3417, 0.42),
    dark: chit(0x2a120a, 0.38),
    leg: chit(0x4e2010, 0.45),
    eye: new THREE.MeshPhysicalMaterial({ color: 0x050505, roughness: 0.08, clearcoat: 1 }),
    spir: std(0x120604, { r: 0.6 }),
    muscle: new THREE.MeshStandardMaterial({ color: 0xff7a2a, emissive: 0xff5a10, emissiveIntensity: 0.7, roughness: 0.6 }),
  };
  const sphere = new THREE.SphereGeometry(1, ws, hs);
  const root = new THREE.Group();
  const body = new THREE.Group();
  body.position.y = 0.2;
  root.add(body);
  const S = (mat, s, p, rx = 0, parent = body) => {
    const m = new THREE.Mesh(sphere, mat);
    m.scale.set(...s); m.position.set(...p); m.rotation.x = rx;
    parent.add(m);
    return m;
  };
  S(M.dark, [0.17, 0.145, 0.25], [0, 0.035, -0.33], 0.18); // gaster
  S(M.red, [0.042, 0.06, 0.045], [0, 0.0, -0.105]); // petiole node
  S(M.red, [0.085, 0.08, 0.17], [0, 0.012, 0.06], -0.1); // mesosoma (thorax)
  const head = new THREE.Group();
  head.position.set(0, 0.045, 0.25);
  body.add(head);
  S(M.dark, [0.1, 0.085, 0.105], [0, 0, 0.03], 0, head);

  const muscles = [];
  const thoraxMuscle = S(M.muscle, [0.05, 0.045, 0.11], [0, 0.012, 0.06]);
  thoraxMuscle.userData.skip = true; thoraxMuscle.visible = false; muscles.push(thoraxMuscle);

  const legs = [], antennae = [], spiracles = [];
  for (const s of [1, -1]) {
    const side = new THREE.Group(); side.scale.x = s; body.add(side);
    const hside = new THREE.Group(); hside.scale.x = s; head.add(hside);
    S(M.eye, [0.026, 0.032, 0.035], [0.08, 0.03, 0.05], 0, hside);
    const mg = new THREE.Group(); mg.position.set(0.035, -0.035, 0.11); mg.rotation.y = -0.45; hside.add(mg);
    const mand = new THREE.Mesh(new THREE.ConeGeometry(0.022, 0.09, rs), M.leg);
    mand.rotation.x = Math.PI / 2; mg.add(mand);

    // Elbowed antenna: scape up-forward, funiculus bends forward-down.
    const scape = limb(0.2, 0.012, 0.01, M.leg, rs);
    scape.rotation.order = 'YZX'; scape.position.set(0.045, 0.065, 0.07); scape.rotation.set(0, -1.15, 0.95);
    hside.add(scape);
    const fun = limb(0.24, 0.01, 0.008, M.leg, rs);
    fun.rotation.order = 'YZX'; fun.rotation.set(0, -0.3, -1.5);
    scape.userData.end.add(fun);
    S(M.leg, [0.014, 0.014, 0.014], [0, 0, 0], 0, fun.userData.end);
    antennae.push({ scape, fun, s });

    // Spiracles: breathing holes along the side of thorax and gaster.
    for (const p of [[0.086, 0.0, 0.1], [0.087, -0.004, 0.02], [0.163, 0.035, -0.27], [0.166, 0.035, -0.36], [0.149, 0.035, -0.45]]) {
      const sp = S(M.spir, [0.012, 0.012, 0.012], p, 0, side);
      sp.userData.skip = true;
      spiracles.push(new THREE.Vector3(p[0] * s, p[1], p[2]));
    }

    const defs = [{ z: 0.12, yaw: -0.75 }, { z: 0.05, yaw: -0.05 }, { z: -0.02, yaw: 0.6 }];
    defs.forEach((d, k) => {
      const hip = new THREE.Group(); hip.rotation.order = 'YZX';
      hip.position.set(0.05, -0.045, d.z); hip.rotation.set(0, d.yaw, 0.52);
      side.add(hip);
      const fem = limb(0.22, 0.026, 0.019, M.leg, rs); hip.add(fem);
      const fm = new THREE.Mesh(sphere, M.muscle); fm.scale.set(0.07, 0.011, 0.011); fm.position.x = 0.1;
      fm.visible = false; fm.userData.skip = true; fem.add(fm); muscles.push(fm);
      const knee = new THREE.Group(); knee.rotation.order = 'YZX'; knee.rotation.z = -1.5;
      fem.userData.end.add(knee);
      S(M.leg, [0.022, 0.022, 0.022], [0, 0, 0], 0, knee);
      const tib = limb(0.3, 0.017, 0.011, M.leg, rs); knee.add(tib);
      const tar = limb(0.08, 0.009, 0.006, M.leg, rs); tar.rotation.z = 0.7; tib.userData.end.add(tar);
      // Tripod gait: L1, L3, R2 move together.
      const tripod = (s === 1) === (k !== 1) ? 0 : Math.PI;
      legs.push({ hip, fem, knee, s, k, yaw: d.yaw, phase: tripod });
    });
  }
  root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  const ant = { root, body, head, legs, antennae, spiracles, muscles, mats: M };
  poseAnt(ant, {});
  return ant;
}

// Pose an ant from explicit parameters only (deterministic).
export function poseAnt(a, { phase = 0, walk = 0, collapse = 0, droop = 0, headYaw = 0, buckle = 0 } = {}) {
  a.body.position.y = 0.2 + (0.075 - 0.2) * collapse - 0.04 * buckle;
  a.body.rotation.z = 0.12 * buckle * (1 - collapse);
  a.body.rotation.x = 0.06 * collapse + 0.05 * buckle;
  for (const L of a.legs) {
    const p = phase + L.phase;
    const lift = Math.max(0, Math.cos(p));
    let elev = 0.52 + walk * 0.22 * lift;
    let knee = -1.5;
    // Front leg on the -1 side buckles first (segment 5).
    const b = L.s === -1 && L.k === 0 ? buckle : 0;
    elev = elev + (0.05 - elev) * Math.max(collapse, b);
    knee = knee + (-0.45 - knee) * Math.max(collapse, b);
    L.hip.rotation.y = L.yaw + walk * 0.32 * Math.sin(p);
    L.hip.rotation.z = elev;
    L.knee.rotation.z = knee;
  }
  for (const A of a.antennae) {
    A.scape.rotation.z = 0.95 - 1.05 * droop + 0.08 * walk * Math.sin(phase * 0.5 + A.s);
    A.fun.rotation.z = -1.5 + 0.35 * droop;
  }
  a.head.rotation.y = headYaw;
  a.head.rotation.x = 0.25 * droop;
}

// Low-detail merged ant for large instanced crowds (vertex-coloured, one draw call).
export function makeAntCrowdGeometry() {
  const a = makeAnt(0);
  a.root.updateMatrixWorld(true);
  const geos = [];
  a.root.traverse((o) => {
    if (!o.isMesh || o.userData.skip) return;
    let g = o.geometry.clone();
    if (g.index) g = g.toNonIndexed();
    g.applyMatrix4(o.matrixWorld);
    if (o.matrixWorld.determinant() < 0) { // mirrored side: flip winding
      const pos = g.attributes.position, nor = g.attributes.normal;
      for (let i = 0; i < pos.count; i += 3) {
        for (const at of [pos, nor]) {
          const x = at.getX(i + 1), y = at.getY(i + 1), z = at.getZ(i + 1);
          at.setXYZ(i + 1, at.getX(i + 2), at.getY(i + 2), at.getZ(i + 2));
          at.setXYZ(i + 2, x, y, z);
        }
      }
    }
    g.deleteAttribute('uv');
    const c = o.material.color;
    const col = new Float32Array(g.attributes.position.count * 3);
    for (let i = 0; i < col.length; i += 3) { col[i] = c.r; col[i + 1] = c.g; col[i + 2] = c.b; }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    geos.push(g);
  });
  // Weld shared vertices so normals are smooth (no faceting), then recompute.
  const merged = mergeVertices(mergeGeometries(geos), 1e-4);
  merged.computeVertexNormals();
  return merged;
}

// -------------------------------------------------------------- HUMAN ----
// One head, one torso, two arms with hands, two legs with feet.
export function makeHuman({ shirt, pants, skin = 0xd9a77f, hair = 0x2a1a10, shoe = 0x222222 }) {
  const M = { shirt: std(shirt), pants: std(pants), skin: std(skin), hair: std(hair), shoe: std(shoe) };
  const root = new THREE.Group();
  const body = new THREE.Group(); root.add(body);
  const cap = (r, l, mat) => new THREE.Mesh(new THREE.CapsuleGeometry(r, l, 3, 8), mat);
  const torso = cap(0.17, 0.34, M.shirt); torso.position.y = 1.27; torso.scale.z = 0.7; body.add(torso);
  const pelvis = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.16, 0.21), M.pants); pelvis.position.y = 0.98; body.add(pelvis);
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.1, 8), M.skin); neck.position.y = 1.54; body.add(neck);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.115, 14, 10), M.skin); head.position.y = 1.65; body.add(head);
  const hairM = new THREE.Mesh(new THREE.SphereGeometry(0.122, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.55), M.hair);
  hairM.position.set(0, 1.66, -0.01); body.add(hairM);
  const arms = [], legs = [];
  for (const s of [1, -1]) {
    const sh = new THREE.Group(); sh.position.set(s * 0.225, 1.45, 0); body.add(sh);
    const up = cap(0.055, 0.22, M.shirt); up.position.y = -0.16; sh.add(up);
    const el = new THREE.Group(); el.position.y = -0.31; sh.add(el);
    const fo = cap(0.047, 0.2, M.skin); fo.position.y = -0.14; el.add(fo);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.052, 8, 6), M.skin); hand.position.y = -0.3; el.add(hand);
    arms.push({ sh, el, s });
    const hp = new THREE.Group(); hp.position.set(s * 0.1, 0.95, 0); body.add(hp);
    const th = cap(0.075, 0.3, M.pants); th.position.y = -0.21; hp.add(th);
    const kn = new THREE.Group(); kn.position.y = -0.45; hp.add(kn);
    const sn = cap(0.062, 0.3, M.pants); sn.position.y = -0.2; kn.add(sn);
    const ft = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.07, 0.25), M.shoe); ft.position.set(0, -0.44, 0.05); kn.add(ft);
    legs.push({ hp, kn, s });
  }
  root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return { root, body, arms, legs };
}

export function poseHuman(h, { phase = 0, amt = 0, run = false, shock = 0 } = {}) {
  const sw = Math.sin(phase) * amt * (run ? 0.85 : 0.45);
  for (const L of h.legs) {
    L.hp.rotation.x = L.s * sw;
    L.kn.rotation.x = Math.max(0, -Math.sin(phase + (L.s > 0 ? 0 : Math.PI))) * amt * (run ? 1.3 : 0.5);
  }
  for (const A of h.arms) {
    A.sh.rotation.x = -A.s * sw * 0.9 - shock * 0.6;
    A.sh.rotation.z = A.s * shock * 0.35;
    A.el.rotation.x = -(run ? 1.4 : 0.25) * Math.max(amt, 0.3) - shock * 0.9;
  }
  h.body.position.y = Math.abs(Math.sin(phase)) * amt * (run ? 0.06 : 0.025);
  h.body.rotation.x = run ? 0.12 * amt : 0;
  h.body.rotation.x -= shock * 0.08;
}

// ---------------------------------------------------------------- DOG ----
export function makeDog() {
  const M = std(0xb98a52), D = std(0x3a2a1a);
  const root = new THREE.Group();
  const b = new THREE.Mesh(new THREE.CapsuleGeometry(0.12, 0.38, 3, 8), M); b.rotation.x = Math.PI / 2; b.position.y = 0.42; root.add(b);
  const h = new THREE.Mesh(new THREE.BoxGeometry(0.17, 0.17, 0.22), M); h.position.set(0, 0.58, 0.32); root.add(h);
  const sn = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.08, 0.1), M); sn.position.set(0, 0.54, 0.46); root.add(sn);
  const nose = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.035, 0.03), D); nose.position.set(0, 0.565, 0.51); root.add(nose);
  for (const s of [1, -1]) {
    const e = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.1, 0.04), D); e.position.set(s * 0.07, 0.69, 0.28); root.add(e);
  }
  const legs = [];
  for (const [x, z] of [[0.08, 0.2], [-0.08, 0.2], [0.08, -0.2], [-0.08, -0.2]]) {
    const g = new THREE.Group(); g.position.set(x, 0.38, z); root.add(g);
    const l = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.025, 0.36, 6), M); l.position.y = -0.18; g.add(l);
    legs.push(g);
  }
  const tail = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.012, 0.25, 6), M);
  tail.position.set(0, 0.52, -0.33); tail.rotation.x = -0.7; root.add(tail);
  root.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return { root, legs, tail };
}
export function poseDog(d, phase, amt) {
  d.legs.forEach((g, i) => { g.rotation.x = Math.sin(phase + (i === 0 || i === 3 ? 0 : Math.PI)) * 0.5 * amt; });
  d.tail.rotation.z = Math.sin(phase * 2) * 0.4;
}

// Lumpy foliage mass: subdivided icosphere displaced by layered sines (deterministic).
let CANOPY = null;
function canopyGeo() {
  if (CANOPY) return CANOPY;
  const g = new THREE.IcosahedronGeometry(1, 4), p = g.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i).normalize();
    const n = 0.12 * Math.sin(v.x * 7 + v.y * 3) * Math.cos(v.z * 6 - v.y * 4) + 0.06 * Math.sin(v.x * 17 + v.z * 13) + 0.04 * Math.sin(v.y * 29 + v.x * 23);
    v.multiplyScalar(1 + n); p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return (CANOPY = g);
}

// --------------------------------------------------------------- TREE ----
// Oak: tapered trunk, branches, clustered faceted canopy. Optional low branch with
// individual leaves (used for the aphid close-up).
export function makeOak(seed, { lowBranch = false } = {}) {
  const R = rng(seed);
  const root = new THREE.Group();
  const bark = pbr(rep(tex().bark, 1, 2), { color: 0x9a8a7a, bs: 4 });
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.5, 4.2, 8), bark);
  trunk.position.y = 2.1; root.add(trunk);
  const canopy = new THREE.Group(); canopy.position.y = 5.4; root.add(canopy);
  for (let i = 0; i < 3; i++) {
    const br = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.18, 2.4, 6), bark);
    const a = i * 2.1 + R();
    br.position.set(Math.cos(a) * 0.6, 4.4, Math.sin(a) * 0.6);
    br.rotation.set(Math.sin(a) * 0.6, 0, -Math.cos(a) * 0.6); root.add(br);
  }
  const greens = [0x5f7f4a, 0x6a8c50, 0x55744a, 0x75985a];
  const ico = canopyGeo();
  for (let i = 0; i < 11; i++) {
    const m = new THREE.Mesh(ico, pbr(rep(tex().leaf, 3, 3), { color: greens[i % 4], r: 0.75, bs: 6 }));
    const a = R() * Math.PI * 2, r = R() * 2.0;
    m.position.set(Math.cos(a) * r, (R() - 0.3) * 1.6, Math.sin(a) * r);
    m.scale.setScalar(1.3 + R() * 1.0);
    m.rotation.set(R() * 3, R() * 3, R() * 3);
    canopy.add(m);
  }
  let leaves = null;
  if (lowBranch) {
    // Low branch heading toward +x at ~2.4 m, ending in a cluster of leaves.
    const lb = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.1, 2.2, 6), bark);
    lb.rotation.z = Math.PI / 2 + 0.08; lb.position.set(1.25, 1.98, 0.3); root.add(lb);
    const leafGeo = new THREE.CircleGeometry(1, 7); leafGeo.scale(0.045, 0.085, 1);
    const leafMat = new THREE.MeshStandardMaterial({ color: 0x4f8a34, roughness: 0.7, side: THREE.DoubleSide });
    leaves = [];
    const cluster = new THREE.Group(); cluster.position.set(2.35, 1.92, 0.3); root.add(cluster);
    for (let i = 0; i < 46; i++) {
      const l = new THREE.Mesh(leafGeo, leafMat);
      const a = R() * Math.PI * 2, r = 0.05 + R() * 0.28;
      l.position.set(Math.cos(a) * r, (R() - 0.5) * 0.3, Math.sin(a) * r);
      l.rotation.set(-Math.PI / 2 + (R() - 0.5) * 1.2, R() * 6.28, (R() - 0.5) * 0.8);
      l.castShadow = true; cluster.add(l); leaves.push(l);
    }
    root.userData.leafCluster = cluster;
  }
  root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return { root, canopy, leaves };
}

// ------------------------------------------------------------ PROPS ------
export function makeBench() {
  const g = new THREE.Group();
  const wood = std(0x8a5a33), iron = std(0x2b2b2b, { m: 0.5, r: 0.5 });
  for (let i = 0; i < 3; i++) { const s = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.04, 0.12), wood); s.position.set(0, 0.45, -0.15 + i * 0.15); g.add(s); }
  for (let i = 0; i < 2; i++) { const s = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.11, 0.035), wood); s.position.set(0, 0.62 + i * 0.15, -0.26); s.rotation.x = -0.15; g.add(s); }
  for (const x of [-0.8, 0.8]) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.45, 0.45), iron); l.position.set(x, 0.225, 0); g.add(l);
    const b = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.4, 0.05), iron); b.position.set(x, 0.65, -0.27); g.add(b);
  }
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}

export function makeLamp() {
  const g = new THREE.Group();
  const iron = std(0x22262a, { m: 0.6, r: 0.45 });
  const p = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.1, 4, 8), iron); p.position.y = 2; g.add(p);
  const h = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.28, 0.4, 6), iron); h.position.y = 4.15; g.add(h);
  const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.14, 0.3, 6), std(0xfff1c8, { r: 0.3 })); glass.position.y = 3.85; g.add(glass);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

export function makeFountain() {
  const g = new THREE.Group();
  const stone = pbr(rep(tex().stone, 4, 1), { r: 0.7, bs: 1.5 });
  const pts = [[0, 0], [2.2, 0], [2.3, 0.15], [2.3, 0.55], [2.05, 0.6], [2.0, 0.3], [0, 0.3]].map(([x, y]) => new THREE.Vector2(x, y));
  const basin = new THREE.Mesh(new THREE.LatheGeometry(pts, 32), stone); g.add(basin);
  const water = new THREE.Mesh(new THREE.CircleGeometry(2.0, 32), new THREE.MeshPhysicalMaterial({ color: 0x3f7f98, roughness: 0.05, metalness: 0, clearcoat: 1, transmission: 0, ior: 1.33 }));
  water.rotation.x = -Math.PI / 2; water.position.y = 0.45; g.add(water);
  const col = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.3, 1.4, 12), stone); col.position.y = 0.9; g.add(col);
  const bowlPts = [[0, 0], [0.9, 0.05], [1.0, 0.25], [0.88, 0.28], [0.2, 0.12], [0, 0.12]].map(([x, y]) => new THREE.Vector2(x, y));
  const bowl = new THREE.Mesh(new THREE.LatheGeometry(bowlPts, 28), stone); bowl.position.y = 1.55; g.add(bowl);
  const top = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 0.5, 8), stone); top.position.y = 1.9; g.add(top);
  // Water jet droplets (instanced), animated deterministically.
  const drops = new THREE.InstancedMesh(new THREE.SphereGeometry(0.035, 5, 4), new THREE.MeshStandardMaterial({ color: 0xcfeaff, roughness: 0.1 }), 72);
  g.add(drops);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = o !== water; o.receiveShadow = true; } });
  const m = new THREE.Matrix4();
  g.userData.update = (t) => {
    for (let i = 0; i < 72; i++) {
      const a = (i % 12) / 12 * Math.PI * 2, u = ((t * 0.9 + Math.floor(i / 12) / 6) % 1);
      const r = 0.15 + u * 0.75, y = 2.15 + u * 0.9 - u * u * 1.5;
      m.makeTranslation(Math.cos(a) * r, y, Math.sin(a) * r);
      drops.setMatrixAt(i, m);
    }
    drops.instanceMatrix.needsUpdate = true;
  };
  return g;
}

export function makeTram() {
  const g = new THREE.Group();
  const yel = new THREE.MeshPhysicalMaterial({ color: 0xe8b520, roughness: 0.35, metalness: 0.1, clearcoat: 0.9, clearcoatRoughness: 0.1 }), dark = std(0x1d2a33, { r: 0.2, m: 0.3 }), grey = std(0x555a60);
  const body = new THREE.Mesh(new THREE.BoxGeometry(14, 2.6, 2.5), yel); body.position.y = 1.7; g.add(body);
  const win = new THREE.Mesh(new THREE.BoxGeometry(13.4, 0.9, 2.54), dark); win.position.y = 2.15; g.add(win);
  const skirt = new THREE.Mesh(new THREE.BoxGeometry(14, 0.35, 2.3), grey); skirt.position.y = 0.38; g.add(skirt);
  for (const x of [-7.05, 7.05]) { const n = new THREE.Mesh(new THREE.BoxGeometry(0.25, 2.2, 2.3), yel); n.position.set(x, 1.7, 0); g.add(n);
    const w = new THREE.Mesh(new THREE.BoxGeometry(0.12, 1.0, 2.0), dark); w.position.set(x * 1.012, 2.2, 0); g.add(w); }
  for (const x of [-4.5, 0, 4.5]) { const d = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.7, 2.56), std(0x3a3f45)); d.position.set(x, 1.3, 0); g.add(d); }
  const roof = new THREE.Mesh(new THREE.BoxGeometry(5, 0.3, 1.4), grey); roof.position.y = 3.15; g.add(roof);
  const pan = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.1, 1.2), grey); pan.position.set(0, 3.7, 0); pan.rotation.z = 0.5; g.add(pan);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}

// Brick apartment block with instanced windows.
export function makeBuilding({ w = 46, h = 16, d = 10, color = 0x9a4a35, seed = 1, floors = 5 } = {}) {
  const g = new THREE.Group();
  const tint = new THREE.Color(color).lerp(new THREE.Color(0xffffff), 0.45);
  const mass = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), pbr(rep(tex().brick, w / 2.6, h / 1.3), { color: tint, r: 0.92, bs: 3 })); mass.position.y = h / 2; g.add(mass);
  const cornice = new THREE.Mesh(new THREE.BoxGeometry(w + 0.6, 0.5, d + 0.6), std(0xd8cfc0)); cornice.position.y = h + 0.1; g.add(cornice);
  const base = new THREE.Mesh(new THREE.BoxGeometry(w + 0.2, 1.2, d + 0.2), std(0x6b625a)); base.position.y = 0.6; g.add(base);
  const cols = Math.floor(w / 3.2);
  const n = cols * floors;
  const winGeo = new THREE.BoxGeometry(1.3, 1.7, 0.2);
  const wins = new THREE.InstancedMesh(winGeo, new THREE.MeshPhysicalMaterial({ color: 0x1d2a35, roughness: 0.05, metalness: 0.1, clearcoat: 1 }), n);
  const sills = new THREE.InstancedMesh(new THREE.BoxGeometry(1.6, 0.15, 0.35), std(0xe2d8c8), n);
  const m = new THREE.Matrix4(); let i = 0;
  for (let f = 0; f < floors; f++) for (let c = 0; c < cols; c++) {
    const x = -w / 2 + 1.6 + c * (w - 3.2) / (cols - 1), y = 2.8 + f * (h - 3.5) / floors;
    m.makeTranslation(x, y + 0.9, d / 2 + 0.02); wins.setMatrixAt(i, m);
    m.makeTranslation(x, y, d / 2 + 0.1); sills.setMatrixAt(i, m); i++;
  }
  g.add(wins, sills);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}
