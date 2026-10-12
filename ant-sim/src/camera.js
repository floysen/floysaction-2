// Camera shot list. Each shot interpolates position/target/fov over its time range.
// Shots are contiguous; a new shot whose start differs from the previous end is a cut.
import * as THREE from 'three';
import { ease, range, lerp, smooth } from './util.js';
import { CUT_ORIGIN } from './cutaway.js';
import { F_POS } from './actors.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const C = CUT_ORIGIN;

export function buildShots(F) {
  const kneeLeg = F.a.legs.find((L) => L.s === -1 && L.k === 0);
  const knee = () => kneeLeg.knee.getWorldPosition(new THREE.Vector3());
  const fT = V(F_POS.x, 0.36, F_POS.z);
  const orbit = (a, r = 2.5, h = 1.05) => V(F_POS.x + Math.sin(a + 0) * r, h, F_POS.z + Math.cos(a + 0) * r);
  let kneeAt40 = null; // knee position frozen at the start of segment 5 so the camera never jitters
  const kn = () => kneeAt40 || V(2.8, 0.25, -1.6);

  return {
    knee,
    freezeKnee(p) { kneeAt40 = p; },
    list: [
      // Segment 1 — macro on the crack, crane up to the park, growth.
      { t0: 0, t1: 3, p: [V(0.2, 0.03, 2.27), V(0.235, 0.032, 2.28)], q: [V(0.25, 0.008, 2.18), V(0.3, 0.008, 2.2)], fov: [38, 38], e: smooth },
      { t0: 3, t1: 6.2, p: [V(0.235, 0.032, 2.28), V(-4.5, 2.6, 9.5)], q: [V(0.3, 0.008, 2.2), V(0.6, 0.5, 1.6)], fov: [38, 46], e: ease, log: true },
      { t0: 6.2, t1: 10, p: [V(-4.5, 2.6, 9.5), V(-3.6, 2.1, 8.2)], q: [V(0.6, 0.5, 1.6), V(0.6, 0.55, 2.0)], fov: [46, 46], e: smooth },
      // Segment 2 — lawn heaves, cutaway, push across the lawn.
      { t0: 10, t1: 13, p: [V(-3.6, 2.1, 8.2), V(3, 8, 16)], q: [V(0.6, 0.55, 2.0), V(0, 0.3, -4)], fov: [46, 52], e: ease },
      { t0: 13, t1: 16, p: [V(C.x - 0.4, -0.6, 9.5), V(C.x + 1.0, -0.3, 8.6)], q: [V(C.x, -1.4, 0), V(C.x, -1.1, 0)], fov: [44, 44], e: smooth },
      { t0: 16, t1: 20, p: [V(-3, 2.0, 11), V(0.5, 1.7, 5.2)], q: [V(2.5, 0.6, -2), V(3.5, 0.5, -5)], fov: [48, 48], e: smooth },
      // Segment 3 — rise overhead, globe, the pile against the building.
      { t0: 20, t1: 21.9, p: [V(0.5, 1.7, 5.2), V(0, 46, 12)], q: [V(3.5, 0.5, -5), V(0, 0, -5)], fov: [48, 50], e: ease, log: true },
      { t0: 21.9, t1: 26.6, globe: true },
      { t0: 26.6, t1: 30, p: [V(-1, 5.4, -4), V(6, 5.8, -3.6)], q: [V(2, 1.2, -18), V(9, 1.2, -18)], fov: [50, 50], e: smooth },
      // Segment 4 — move in on the fountain ant, slow orbit during the X-ray.
      { t0: 30, t1: 32.2, p: [V(6, 5.8, -3.6), orbit(0)], q: [V(9, 1.2, -18), fT], fov: [50, 42], e: ease },
      { t0: 32.2, t1: 40, p: (u) => orbit(lerp(0, 0.55, u)), q: [fT, fT], fov: [42, 40], e: smooth },
      // Segment 5 — macro on the buckling leg, then pull back over the whole park.
      { t0: 40, t1: 44.5, p: (u) => kn().clone().add(V(lerp(0.35, 0.25, u), lerp(0.18, 0.12, u), lerp(0.95, 0.75, u))), q: (u) => kn().clone().add(V(0, lerp(0.02, -0.04, u), 0)), fov: [40, 40], e: smooth },
      { t0: 44.5, t1: 50, p: (u) => kn().clone().add(V(0.25, 0.12, 0.75)).lerp(V(-7, 14, 18), u), q: (u) => kn().clone().lerp(V(2, 0, -4), u), fov: [40, 50], e: ease, log: true },
      // Segment 6 — time-lapse: wide, seeds, aphids, flowers, back to the empty crack.
      { t0: 50, t1: 53.4, p: [V(-7, 14, 18), V(-5, 9, 14)], q: [V(2, 0, -4), V(0, 0, -1)], fov: [50, 50], e: smooth },
      { t0: 53.4, t1: 55, p: [V(-1.3, 1.3, 5.4), V(-0.6, 0.9, 4.4)], q: [V(0.4, 0, 2.0), V(0.8, 0, 1.6)], fov: [45, 45], e: smooth },
      { t0: 55, t1: 56.4, p: [V(-4.2, 2.12, 8.42), V(-4.3, 2.06, 8.28)], q: [V(-4.65, 1.92, 7.8), V(-4.65, 1.92, 7.8)], fov: [40, 40], e: smooth },
      { t0: 56.4, t1: 59.2, p: [V(-3.2, 1.3, 6.6), V(0.2, 0.03, 2.27)], q: [V(-1.8, 0.15, 4.6), V(0.25, 0.008, 2.18)], fov: [45, 38], e: ease, log: true },
      { t0: 59.2, t1: 60.01, p: [V(0.2, 0.03, 2.27), V(0.2, 0.03, 2.27)], q: [V(0.25, 0.008, 2.18), V(0.25, 0.008, 2.18)], fov: [38, 38], e: smooth },
    ],
  };
}

const tmpA = new THREE.Vector3(), tmpB = new THREE.Vector3();
// "log" shots interpolate the camera's offset from its target in log-distance,
// so macro-to-wide moves feel continuous instead of rushing through the small scale.
function interp(sh, u) {
  const e = sh.e(u);
  const get = (k) => (typeof sh[k] === 'function' ? sh[k](e) : sh[k][0].clone().lerp(sh[k][1], e));
  let q = get('q');
  let p;
  if (sh.log && Array.isArray(sh.p)) {
    const o0 = tmpA.copy(sh.p[0]).sub(sh.q[0]), o1 = tmpB.copy(sh.p[1]).sub(sh.q[1]);
    const d = Math.exp(lerp(Math.log(o0.length()), Math.log(o1.length()), e));
    const dir = o0.clone().normalize().lerp(o1.clone().normalize(), e).normalize();
    const qq = sh.q[0].clone();
    const qScale = range(Math.log(d), Math.log(o0.length()), Math.log(o1.length()));
    q = qq.lerp(sh.q[1], qScale);
    p = q.clone().addScaledVector(dir, d);
  } else if (sh.log && typeof sh.p === 'function') {
    p = get('p');
  } else p = get('p');
  return { p, q, fov: lerp(sh.fov[0], sh.fov[1], e) };
}

export function cameraAt(shots, t) {
  const sh = shots.list.find((s) => t >= s.t0 && t < s.t1) || shots.list[shots.list.length - 1];
  if (sh.globe) return { globe: true };
  return interp(sh, range(t, sh.t0, sh.t1));
}
