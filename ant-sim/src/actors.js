// Ants, people and the tram: everything that moves in the park.
import * as THREE from 'three';
import { rng, lerp, range, smooth, ease, clamp, easeOut } from './util.js';
import { makeAnt, poseAnt, makeAntCrowdGeometry, makeHuman, poseHuman, makeDog, poseDog, makeTram, std } from './models.js';
import { CRACK, FOUNTAIN, TREES, pathZ } from './world.js';

export const ANT_LEN = 1.7; // human-sized body length in metres
const TINY = 0.006;         // real wood-ant length (~6 mm)
export const F_POS = new THREE.Vector3(3, 0, -2); // the "fountain ant" studied in segments 4-5

const Ry = (x, z, a) => [x * Math.cos(a) + z * Math.sin(a), -x * Math.sin(a) + z * Math.cos(a)];

// Distance walked by a hero ant: constant speed until 30 s, decelerating to a stop by 40 s.
function walked(t, te, v) {
  if (t < te) return 0;
  const a = Math.max(0, Math.min(t, 30) - te);
  const tau = clamp(t - 30, 0, 10);
  return v * a + (t > 30 ? v * (tau - tau * tau / 20) : 0);
}
const walkAmt = (t) => (t < 30 ? 1 : clamp(1 - (t - 30) / 10));

export function buildActors(scene) {
  const R = rng(4242);

  // ----------------------------------------------------------- hero ants
  const heroes = [];
  const addHero = (o) => { const a = makeAnt(1); scene.add(a.root); heroes.push({ ...o, a }); return heroes[heroes.length - 1]; };
  const A0 = addHero({ name: 'A0', x: 0.42, z: 2.25, yaw: 1.2, te: 9.7, v: 0.45, sigma: -1, rad: 5, grow: true });
  const F = addHero({ name: 'F', x: F_POS.x, z: F_POS.z, yaw: Math.PI / 2, te: 12.6, v: 0, stationary: true });
  addHero({ name: 'SW', x: -2.5, z: -12.0, yaw: 2.4, te: 12.2, v: 0.5, sigma: 1, rad: 4 });
  let guard = 0;
  while (heroes.length < 30 && guard++ < 5000) {
    const x = -15 + R() * 31, z = -9.5 + R() * 18.5;
    if (Math.abs(z - pathZ(x)) < 2.4) continue;
    if (Math.hypot(x - FOUNTAIN.x, z - FOUNTAIN.z) < 3.8) continue;
    if (Math.hypot(x + 4, z + 0.6) < 2.2) continue;
    if (TREES.some(([tx, tz]) => Math.hypot(x - tx, z - tz) < 2)) continue;
    if (heroes.some((h) => Math.hypot(h.x - x, h.z - z) < 2.8)) continue;
    if (Math.hypot(x - F_POS.x, z - F_POS.z) < 5) continue;
    const late = heroes.length % 4 === 0;
    const h = { name: 'H' + heroes.length, x, z, yaw: R() * 6.28, te: late ? 16.0 + R() * 1.6 : 10.5 + R() * 2.4, v: 0.35 + R() * 0.25, sigma: R() < 0.5 ? 1 : -1, rad: 3 + R() * 3 };
    // Keep heroes away from F so the segment 4-5 close-ups stay clear.
    const end = heroPos(h, 40);
    if (Math.hypot(end.x - F_POS.x, end.z - F_POS.z) < 4.2 || Math.hypot(end.x - FOUNTAIN.x, end.z - FOUNTAIN.z) < 3.2) continue;
    addHero(h);
  }
  function heroPos(h, t) {
    if (h.stationary) { const u = smooth(range(t, h.te + 0.3, h.te + 3.0)); return { x: h.x - 1.9 * (1 - u), z: h.z, yaw: h.yaw, s: u * 1.9 }; }
    if (!h.v) return { x: h.x, z: h.z, yaw: h.yaw, s: 0 };
    const s = walked(t, h.te + 0.8, h.v);
    const hx = Math.sin(h.yaw), hz = Math.cos(h.yaw);
    const v0 = h.sigma > 0 ? [-hz * h.rad, hx * h.rad] : [hz * h.rad, -hx * h.rad];
    const cx = h.x - v0[0], cz = h.z - v0[1];
    const phi = h.sigma * s / h.rad;
    const [rx, rz] = Ry(v0[0], v0[1], phi);
    return { x: cx + rx, z: cz + rz, yaw: h.yaw + phi, s };
  }

  // Emergence props: lawn mound, crater ring, flying dirt chunks.
  const soilMat = std(0x5a3e26, { r: 1, flat: true }), grassMound = std(0x5c8a37, { r: 1, flat: true });
  const moundGeo = new THREE.SphereGeometry(1, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2);
  const ringGeo = new THREE.TorusGeometry(0.85, 0.11, 6, 14); ringGeo.rotateX(Math.PI / 2);
  const holeGeo = new THREE.CircleGeometry(0.8, 14); holeGeo.rotateX(-Math.PI / 2);
  const holeMat = new THREE.MeshStandardMaterial({ color: 0x24170d, roughness: 1, polygonOffset: true, polygonOffsetFactor: -3 });
  const CH = 9;
  const chunks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1, 0), soilMat, heroes.length * CH);
  chunks.castShadow = true; scene.add(chunks);
  { const z = new THREE.Matrix4().makeScale(0, 0, 0); for (let i = 0; i < chunks.count; i++) chunks.setMatrixAt(i, z); }
  for (const h of heroes) {
    if (h.grow) continue;
    h.mound = new THREE.Mesh(moundGeo, grassMound); h.mound.castShadow = h.mound.receiveShadow = true;
    h.ring = new THREE.Mesh(ringGeo, soilMat); h.ring.receiveShadow = h.ring.castShadow = true;
    h.hole = new THREE.Mesh(holeGeo, holeMat);
    const ox = h.stationary ? -1.9 : 0;
    for (const m of [h.mound, h.ring, h.hole]) { m.position.set(h.x + ox, 0, h.z); scene.add(m); }
    h.hole.position.y = 0.02; h.ring.position.y = 0.02;
    if (h.name === 'SW') { h.mound.material = soilMat; }
    h.chunk = Array.from({ length: CH }, () => ({ a: R() * 6.28, sp: 1.5 + R() * 2.2, up: 3 + R() * 3, s: 0.06 + R() * 0.1, r: R() * 6 }));
  }

  // Tiny ants at the crack (segment 1 macro).
  const tiny = [];
  for (let i = 0; i < 4; i++) {
    const a = makeAnt(1); a.root.scale.setScalar(TINY); scene.add(a.root);
    tiny.push({ a, x0: CRACK.x + 0.12 - i * 0.05, z0: CRACK.z - 0.1 + i * 0.07, ang: 2.4 + i * 0.5, sp: 0.022 + i * 0.004 });
  }

  // Pulse ring at the moment of growth.
  const pulseMat = new THREE.MeshBasicMaterial({ color: 0xfff1c4, transparent: true, opacity: 0, depthWrite: false });
  const pulseRing = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 64).rotateX(-Math.PI / 2), pulseMat);
  pulseRing.position.set(A0.x, 0.03, A0.z); scene.add(pulseRing);

  // ------------------------------------------------------- crowd (instanced)
  const crowdGeo = makeAntCrowdGeometry();
  const crowdMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.38, metalness: 0.1 });
  const crowdData = [];
  const RC = rng(777);
  const tramStopX = 14.1;
  for (let gx = -30; gx <= 30; gx += 1.55) for (let gz = -22.5; gz <= 13; gz += 1.45) {
    const x = gx + (RC() - 0.5) * 0.9, z = gz + (RC() - 0.5) * 0.8;
    if (Math.hypot(x - FOUNTAIN.x, z - FOUNTAIN.z) < 3.0) continue;
    if (Math.hypot(x - F_POS.x, z - F_POS.z) < 3.6) continue;
    if (TREES.some(([tx, tz]) => Math.hypot(x - tx, z - tz) < 1.4)) continue;
    if (Math.abs(x - tramStopX) < 7.6 && Math.abs(z + 16.5) < 1.7) continue;
    if (x > 13 && x < 25 && z < -10 && z > -15 && false) continue;
    const ta = 20.0 + 1.6 * clamp(Math.hypot(x, z + 4) / 34) + RC() * 0.3;
    crowdData.push({ x, z, yaw: RC() * 6.28, L: 0, ta, pitch: (RC() - 0.5) * 0.15, roll: (RC() - 0.5) * 0.15, d: RC() });
    // Extra layers pile up toward the road and the building.
    const maxL = z < -9 ? Math.floor(lerp(1, 4.6, range(-z, 9, 22))) : 0;
    for (let L = 1; L <= maxL; L++) {
      crowdData.push({ x: x + (RC() - 0.5) * 0.7, z: z + (RC() - 0.5) * 0.7, yaw: RC() * 6.28, L, ta: 26.6 + RC() * 2.8 + L * 0.15,
        pitch: (RC() - 0.5) * 0.7, roll: (RC() - 0.5) * 0.7, d: RC() });
    }
  }
  const crowd = new THREE.InstancedMesh(crowdGeo, crowdMat, crowdData.length);
  crowd.castShadow = crowd.receiveShadow = true; crowd.frustumCulled = false; scene.add(crowd);

  // -------------------------------------------------------------- people
  const people = [];
  const addPerson = (o) => { const h = o.dog ? makeDog() : makeHuman(o.look); scene.add(h.root); people.push({ ...o, h }); };
  // keys: [t, x, z, mode]  mode: 'run' | 'walk' | 'stand'
  addPerson({ look: { shirt: 0x2f7fd0, pants: 0x222831, hair: 0x2a1a10 }, keys: [[0, -24, 7.4, 'run'], [7.4, -2.9, 2.8, 'stand'], [10.6, -2.9, 2.8, 'run'], [15, -24, 8.0, 'run']], face: Math.PI / 2 });
  addPerson({ look: { shirt: 0xc94f3d, pants: 0x3b4a5c, hair: 0x6b4a2a }, keys: [[0, 13, -1.6, 'walk'], [8, 6.4, -0.1, 'stand'], [10.4, 6.4, -0.1, 'walk'], [15, 22, -3.6, 'run']], face: -Math.PI / 2 });
  addPerson({ dog: true, keys: [[0, 12.2, -1.0, 'walk'], [8, 5.5, 0.6, 'stand'], [10.4, 5.5, 0.6, 'walk'], [15, 21, -2.8, 'run']], face: -Math.PI / 2 });
  addPerson({ look: { shirt: 0xe8c44a, pants: 0x2d2d2d, hair: 0x111111 }, keys: [[0, -16, -11.9, 'walk'], [11.2, -6.2, -11.9, 'walk'], [11.9, -6.2, -11.9, 'stand'], [12.6, -6.4, -11.9, 'run'], [17, -26, -11.9, 'run']], face: Math.PI / 2 });
  addPerson({ look: { shirt: 0x5a8a5a, pants: 0x4a3b2c, hair: 0x9a7a4a }, keys: [[0, 9, -21.4, 'walk'], [12, 18, -21.4, 'walk'], [16, 26, -21.4, 'run']], face: Math.PI / 2 });

  const tram = makeTram(); tram.position.set(0, 0, -16.5); scene.add(tram);
  const tramX = (t) => (t < 9 ? -45 + 5.5 * t : -45 + 49.5 + 5.5 * Math.min(t - 9, 3.5) - 0.5 * (5.5 / 3.5) * Math.pow(Math.min(t - 9, 3.5), 2));

  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(0, 0, 0, 'YXZ'), v = new THREE.Vector3(), sc = new THREE.Vector3();

  function update(t) {
    // Tram glides, then brakes to a stop as the ground erupts.
    tram.position.x = tramX(t);

    // People: follow keyframes, face direction of travel.
    for (const p of people) {
      const k = p.keys; let i = 0;
      while (i < k.length - 2 && t > k[i + 1][0]) i++;
      const [t0, x0, z0, mode] = k[i], [t1, x1, z1] = k[i + 1];
      const u = clamp((t - t0) / (t1 - t0));
      const x = lerp(x0, x1, u), z = lerp(z0, z1, u);
      p.h.root.position.set(x, 0, z);
      const moving = mode !== 'stand' && (x1 !== x0 || z1 !== z0) && u < 1;
      if (moving) p.h.root.rotation.y = Math.atan2(x1 - x0, z1 - z0);
      else if (mode === 'stand') p.h.root.rotation.y = p.face + (p.dog ? 0 : 0);
      const spd = moving ? Math.hypot(x1 - x0, z1 - z0) / (t1 - t0) : 0;
      const phase = t * (mode === 'run' ? 11 : 7);
      p.h.root.visible = t < 17.5;
      if (p.dog) poseDog(p.h, phase * 1.4, moving ? 1 : 0);
      else poseHuman(p.h, { phase, amt: moving ? clamp(spd / 2) : 0, run: mode === 'run' && moving, shock: mode === 'stand' ? smooth(range(t, t0, t0 + 0.6)) : 0 });
    }

    // Tiny ants (segment 1 macro): wander, then slip into the crack before the change.
    for (const ta of tiny) {
      const s = t * ta.sp;
      const x = ta.x0 + Math.cos(ta.ang) * s * -1, z = ta.z0 + Math.sin(ta.ang) * s;
      ta.a.root.position.set(x, 0.012 - smooth(range(t, 3.6, 5)) * 0.01, z);
      ta.a.root.rotation.y = Math.atan2(-Math.cos(ta.ang), Math.sin(ta.ang));
      ta.a.root.visible = t < 5.2;
      poseAnt(ta.a, { phase: t * 22, walk: 1 });
    }

    // Pulse ring at the growth moment.
    const pr = range(t, 6.2, 7.8);
    pulseRing.scale.setScalar(0.05 + pr * 9);
    pulseMat.opacity = pr > 0 && pr < 1 ? 0.75 * (1 - pr) : 0;

    // Hero ants.
    const decay = smooth(range(t, 50.2, 52.8));
    heroes.forEach((h, idx) => {
      const a = h.a, root = a.root;
      let scale = ANT_LEN, y = 0, pitch = 0;
      let pos = heroPos(h, t);
      if (h.grow) {
        // A0: a real ant walking by the crack, then growing to 1.7 m (log-space ease).
        if (t < 6.5) {
          const u = t / 6.5;
          pos = { x: lerp(0.22, h.x, u), z: lerp(2.16, h.z, u), yaw: Math.atan2(h.x - 0.22, h.z - 2.16), s: t * 0.03 };
        } else if (t < 10.5) pos = { x: h.x, z: h.z, yaw: Math.atan2(h.x - 0.22, h.z - 2.16), s: 0 };
        const g = ease(range(t, 6.5, 8.3));
        scale = Math.exp(lerp(Math.log(TINY), Math.log(ANT_LEN), g));
        root.visible = true;
      } else {
        // Emerge from below ground, nose first.
        const em = range(t, h.te - 0.25, h.te + 0.7);
        y = lerp(-0.7, 0, easeOut(em));
        pitch = -0.6 * (1 - smooth(range(t, h.te + 0.2, h.te + 1.0))) * (em > 0 ? 1 : 0);
        root.visible = t > h.te - 0.25;
        // Mound swells before the burst, then the crater remains.
        const sw = smooth(range(t, h.te - 1.4, h.te - 0.15));
        const burst = t > h.te - 0.15;
        h.mound.visible = !burst && sw > 0;
        h.mound.scale.set(0.2 + sw * 1.0, 0.02 + sw * 0.5, 0.2 + sw * 1.0);
        h.ring.visible = h.hole.visible = burst;
        h.ring.scale.setScalar(burst ? 0.8 + 0.3 * easeOut(range(t, h.te - 0.15, h.te + 0.4)) : 0.01);
        const fade = 1 - smooth(range(t, 56, 58)) * 0.35;
        h.ring.scale.y = fade;
      }
      if (h.grow) y = 0.012 * (1 - smooth(range(t, 6.5, 7.5))); // stand on the gravel surface while tiny
      // Decay in segment 6: bodies sink and are gone.
      y -= decay * 0.45;
      root.visible = root.visible && decay < 1;
      root.position.set(pos.x, y, pos.z);
      root.rotation.set(0, 0, 0); root.rotation.order = 'YXZ';
      root.rotation.y = pos.yaw; root.rotation.x = pitch;
      root.scale.set(scale, scale * (1 - decay * 0.5), scale);

      // Gait and segment 5 collapse (staggered across ants; F buckles first).
      const ph = pos.s / (0.42 * ANT_LEN) * Math.PI * 2;
      let walk = h.grow && t < 6.5 ? 1 : (pos.s > 0 ? walkAmt(t) : 0);
      let phase = h.grow && t < 6.5 ? t * 22 : ph;
      let buckle = 0, collapse = smooth(range(t, 44.8 + (idx % 7) * 0.5, 46.3 + (idx % 7) * 0.5));
      let droop = Math.max(collapse, smooth(range(t, 37, 40)) * 0.3);
      if (h.stationary) {
        // F: restless legs until 30 s, weakening through segment 4, buckles at 43.3 s.
        const vig = t < 30 ? 1 : clamp(1 - (t - 30) / 9);
        const step = range(t, h.te + 0.3, h.te + 3.0) > 0 && t < h.te + 3.0;
        phase = step ? ph : t * 5; walk = step ? 1 : 0.35 * vig;
        buckle = smooth(range(t, 43.2, 44.0));
        collapse = smooth(range(t, 44.6, 46.0));
        droop = Math.max(collapse, smooth(range(t, 36.5, 40)) * 0.35);
      }
      if (h.grow && t >= 6.5 && t < 10.5) { walk = 0; droop = 0; }
      poseAnt(a, { phase, walk, collapse, droop, buckle, headYaw: h.stationary ? Math.sin(t * 0.7) * 0.15 * (1 - collapse) : 0 });

      if (h.chunk) {
        h.chunk.forEach((c, j) => {
          const tau = t - (h.te - 0.15);
          const ii = idx * CH + j;
          if (tau < 0 || t > 52.5) { m4.makeScale(0, 0, 0); chunks.setMatrixAt(ii, m4); return; }
          const tl = (2 * c.up) / 9.8; const tt = Math.min(tau, tl);
          const r = 0.6 + c.sp * tt;
          v.set(h.x + Math.cos(c.a) * r, Math.max(c.s * 0.5, c.up * tt - 4.9 * tt * tt), h.z + Math.sin(c.a) * r);
          e.set(c.r + tt * 5, c.r * 2 + tt * 3, 0); q.setFromEuler(e);
          m4.compose(v, q, sc.setScalar(c.s)); chunks.setMatrixAt(ii, m4);
        });
      }
    });
    chunks.instanceMatrix.needsUpdate = true;

    // Crowd: base layer emerges 20-22 s, upper layers climb into piles 26.6-30 s,
    // everyone sags in segment 5, and decays in segment 6.
    const sag = (d) => smooth(range(t, 44.8 + d * 3.5, 46.6 + d * 3.5));
    for (let i = 0; i < crowdData.length; i++) {
      const c = crowdData[i];
      const ap = range(t, c.ta, c.ta + (c.L ? 1.1 : 0.7));
      if (ap <= 0 || decay >= 1) { m4.makeScale(0, 0, 0); crowd.setMatrixAt(i, m4); continue; }
      const k = easeOut(ap);
      const s = ANT_LEN * (c.L ? clamp(ap * 3) : 1);
      const restY = c.L * 0.36;
      let y = c.L ? lerp(restY - 0.4, restY, k) : lerp(-0.8, 0, k);
      const g = sag(c.d);
      y -= g * 0.18 * ANT_LEN * (c.L ? 0.6 : 1) + decay * 0.5;
      const wob = t < 44 ? Math.sin(t * 3 + i) * 0.03 : 0;
      e.set(c.pitch + (c.L ? 0 : (1 - k) * -0.6), c.yaw + wob, c.roll * (1 + g * 0.5)); q.setFromEuler(e);
      m4.compose(v.set(c.x, y, c.z), q, sc.set(s, s * (1 - g * 0.3) * (1 - decay * 0.6), s));
      crowd.setMatrixAt(i, m4);
    }
    crowd.instanceMatrix.needsUpdate = true;
  }

  return { update, heroes, F, A0, crowdCount: crowdData.length };
}
