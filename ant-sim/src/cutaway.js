// Segment 2 cutaway: a cross-section of lawn soil with a nest's narrow tunnels,
// and a human-sized ant forcing its way up through it. Built far from the park (x=400).
import * as THREE from 'three';
import { rng, range, smooth, easeOut, lerp } from './util.js';
import { std, makeAnt, poseAnt } from './models.js';
import { ANT_LEN } from './actors.js';

export const CUT_ORIGIN = new THREE.Vector3(400, 0, 0);

export function buildCutaway(scene) {
  const R = rng(55);
  const g = new THREE.Group(); g.position.copy(CUT_ORIGIN); scene.add(g);
  const W = 7, D = 3;
  const layer = (y0, y1, color) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(W, y1 - y0, D), std(color, { r: 1 }));
    m.position.set(0, (y0 + y1) / 2, -D / 2); m.receiveShadow = m.castShadow = true; g.add(m); return m;
  };
  layer(-3.4, -1.3, 0x8a6a45);
  layer(-1.3, -0.22, 0x6b4a2e);
  // Turf on top, split into three pieces so the middle one can be heaved up.
  const turf = [];
  for (const [x0, x1] of [[-3.5, -0.9], [-0.9, 0.9], [0.9, 3.5]]) {
    const piv = new THREE.Group(); piv.position.set(x0 < 0 && x1 <= -0.9 ? -0.9 : x0 >= 0.9 ? 0.9 : 0, -0.11, 0); g.add(piv);
    const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, 0.22, D), std(0x5f8f3a, { r: 1 }));
    m.position.set((x0 + x1) / 2 - piv.position.x, 0, -D / 2); m.castShadow = m.receiveShadow = true; piv.add(m);
    for (let i = 0; i < 40; i++) {
      const b = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.15, 3), std(0x4f8a30));
      b.position.set(x0 - piv.position.x + R() * (x1 - x0), 0.18, -R() * D); piv.add(b);
    }
    turf.push(piv);
  }
  // Nest tunnels and chambers drawn on the cut face: built for ~6 mm ants.
  const tunMat = new THREE.MeshStandardMaterial({ color: 0x1e1209, roughness: 1 });
  const tunnels = new THREE.Group(); g.add(tunnels);
  const paths = [
    [[-1.6, -0.2], [-1.4, -0.8], [-1.7, -1.4], [-1.2, -2.0], [-1.5, -2.8]],
    [[0.3, -0.2], [0.1, -0.7], [0.5, -1.3], [0.2, -1.9], [0.6, -2.6], [0.3, -3.1]],
    [[1.9, -0.2], [2.2, -0.9], [1.8, -1.6], [2.3, -2.4]],
    [[-1.6, -1.4], [-0.6, -1.5], [0.5, -1.3], [1.8, -1.6]],
    [[-1.2, -2.0], [-0.2, -2.3], [0.6, -2.6]],
  ];
  for (const p of paths) {
    const c = new THREE.CatmullRomCurve3(p.map(([x, y]) => new THREE.Vector3(x, y, 0.005)));
    tunnels.add(new THREE.Mesh(new THREE.TubeGeometry(c, 40, 0.025, 6), tunMat));
  }
  for (const [x, y] of [[-1.7, -1.4], [0.5, -1.3], [-1.2, -2.0], [0.6, -2.6], [2.2, -0.9], [-1.5, -2.8], [1.8, -1.6]]) {
    const ch = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8), tunMat); ch.scale.set(0.16, 0.06, 0.02); ch.position.set(x, y, 0.005); tunnels.add(ch);
  }
  // Cracks spreading across the face from the rising ant.
  const cracks = [];
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2 + R() * 0.3, len = 0.6 + R() * 1.4;
    const cr = new THREE.Mesh(new THREE.BoxGeometry(1, 0.03, 0.02), tunMat);
    cr.geometry.translate(0.5, 0, 0);
    cr.position.set(Math.cos(a) * 0.5, -1.5 + Math.sin(a) * 0.4, 0.01); cr.rotation.z = a;
    g.add(cr); cracks.push({ cr, len, d: R() });
  }
  // Dark backdrop floor so the diorama reads as a cutaway.
  const floor = new THREE.Mesh(new THREE.CircleGeometry(30, 32), std(0x2e2a24));
  floor.rotation.x = -Math.PI / 2; floor.position.y = -3.4; floor.receiveShadow = true; g.add(floor);

  const ant = makeAnt(1);
  const wrap = new THREE.Group(); wrap.position.set(0, -2.6, 0.55); g.add(wrap);
  ant.root.scale.setScalar(ANT_LEN); ant.root.rotation.y = Math.PI / 2; wrap.add(ant.root);

  // Chunks of soil thrown up at the surface.
  const NC = 26;
  const chunks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1, 0), std(0x5a3e26, { flat: true }), NC);
  chunks.castShadow = true; g.add(chunks);
  const cd = Array.from({ length: NC }, () => ({ x: (R() - 0.5) * 1.6, vx: (R() - 0.5) * 3, vy: 2 + R() * 3, s: 0.05 + R() * 0.09, r: R() * 6 }));
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3(), sc = new THREE.Vector3();

  function update(t) {
    const rise = easeOut(range(t, 13.0, 15.7));
    wrap.position.y = lerp(-2.7, -0.15, rise);
    wrap.rotation.z = 0.45 * (1 - smooth(range(t, 15.0, 16.0)));
    poseAnt(ant, { phase: t * 14, walk: 1 - smooth(range(t, 15.4, 16)) * 0.6 });
    const heave = smooth(range(t, 14.4, 15.6));
    turf[1].position.y = -0.11 + heave * 0.9; turf[1].rotation.z = heave * 0.5;
    turf[0].rotation.z = heave * 0.25; turf[2].rotation.z = -heave * 0.25;
    turf[1].visible = heave < 0.98 || true;
    for (const c of cracks) c.cr.scale.set(Math.max(0.001, smooth(range(t, 13.2 + c.d, 14.6 + c.d)) * c.len), 1, 1);
    // Tunnels near the ant's path are crushed (shrink) as it passes.
    tunnels.scale.z = 1;
    for (let i = 0; i < NC; i++) {
      const c = cd[i], tau = t - 14.6;
      if (tau < 0) { m4.makeScale(0, 0, 0); chunks.setMatrixAt(i, m4); continue; }
      const tt = Math.min(tau, (2 * c.vy) / 9.8 + 0.08);
      v.set(c.x + c.vx * tt, Math.max(c.s * 0.5, 0.1 + c.vy * tt - 4.9 * tt * tt), 0.4 - (i % 5) * 0.5);
      e.set(c.r + tt * 4, c.r, tt * 3); q.setFromEuler(e);
      m4.compose(v, q, sc.setScalar(c.s)); chunks.setMatrixAt(i, m4);
    }
    chunks.instanceMatrix.needsUpdate = true;
  }
  return { update };
}
