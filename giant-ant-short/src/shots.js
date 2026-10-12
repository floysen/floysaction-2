import * as THREE from 'three';
import { clamp, lerp, ramp, smooth, easeInOut, easeOut, easeOutQuad, easeIn, lerp3, pulse, rng } from './timeline.js';
import { LAB_ORIGIN } from './env/lab.js';
import { M } from './materials.js';

// Shot list: every shot maps to a narration line (see timeline.js NARRATION) and changes the
// picture every ~1.5-2.7 s. `cam(u, t)` returns world-space camera pose for normalised shot time u.
const L = (x, y, z) => [LAB_ORIGIN.x + x, LAB_ORIGIN.y + y, LAB_ORIGIN.z + z];
const move = (p0, p1, l0, l1, fov, ease = easeInOut) => (u) => ({ pos: lerp3(p0, p1, ease(u)), look: lerp3(l0, l1, ease(u)), fov });

export const SHOTS = [
  // 1 - "You hear it before you see it. Clicking." Inside the dark apartment; ants move outside.
  { id: 'S1a-room', start: 0.0, end: 1.6, scene: 'street', cam: move([-1.3, 1.62, -4.5], [-0.85, 1.62, -3.6], [0.25, 1.35, 4], [0.3, 1.3, 4], 42) },
  { id: 'S1b-glass', start: 1.6, end: 3.2, scene: 'street', cam: move([0.66, 1.6, -1.1], [0.6, 1.6, -0.85], [0.2, 1.75, 9], [-0.6, 1.75, 9], 36) },
  // 2 - "Hundreds of legs on concrete." Ground-level close-up of feet striking the wet sidewalk.
  { id: 'S2-legs', start: 3.2, end: 5.3, scene: 'street', cam: move([-1.7, 0.24, 4.45], [-2.4, 0.24, 4.4], [-5.2, 0.3, 2.6], [-2.9, 0.32, 2.6], 46) },
  // 3 - "Outside your window, an ant as tall as you grabs a car door and pulls..."
  { id: 'S3a-overshoulder', start: 5.3, end: 6.8, scene: 'street', cam: move([0.88, 1.74, -2.45], [0.82, 1.72, -2.2], [-1.0, 1.35, 2.6], [-1.1, 1.4, 2.6], 44) },
  { id: 'S3b-compare', start: 6.8, end: 8.0, scene: 'street', cam: move([5.6, 1.82, 8.3], [5.3, 1.82, 7.85], [-0.55, 1.35, 1.0], [-0.5, 1.35, 1.0], 48) },
  { id: 'S3c-reach', start: 8.0, end: 9.4, scene: 'street', cam: move([0.9, 2.75, 8.4], [0.6, 2.6, 7.6], [-0.5, 1.1, 3.0], [-0.3, 1.05, 3.2], 40) },
  { id: 'S3d-pull', start: 9.4, end: 10.8, scene: 'street', cam: move([3.4, 2.0, 1.6], [3.2, 1.85, 1.75], [0.4, 0.95, 3.5], [0.5, 0.95, 3.5], 42) },
  // 4 - "and its leg snaps." Close-up on the gripping leg; controlled shake on the break.
  { id: 'S4-snap', start: 10.8, end: 12.4, scene: 'street', cam: move([2.2, 1.55, 1.75], [2.0, 1.4, 1.9], [0.45, 0.95, 3.45], [0.35, 0.9, 3.4], 36) },
  // 5 - "Grow an ant 500x taller ... 125 million times heavier." Abstract scale lab.
  { id: 'L1-grow', start: 12.4, end: 14.6, scene: 'lab', cam: null },
  { id: 'L2-weight', start: 14.6, end: 16.6, scene: 'lab', cam: null },
  { id: 'L3-press', start: 16.6, end: 18.6, scene: 'lab', cam: move(L(2.7, 0.85, 4.3), L(2.3, 0.7, 3.7), L(-0.1, 1.5, -0.3), L(-0.15, 1.35, -0.3), 46) },
  // 6 - "Its muscles? Only a quarter-million times stronger."
  { id: 'L4-strength', start: 18.6, end: 20.2, scene: 'lab', cam: move(L(2.9, 0.07, -1.15), L(2.86, 0.06, -1.2), L(2.58, 0.014, -1.55), L(2.59, 0.013, -1.55), 40) },
  { id: 'L5-compare', start: 20.2, end: 21.8, scene: 'lab', cam: move(L(2.86, 0.06, -1.2), L(5.2, 3.6, 8.2), L(2.59, 0.013, -1.55), L(0.7, 2.3, -1.2), 44, (u) => easeInOut(u) ** 1.6) },
  // 7 - "Its shell starts to crack."
  { id: 'S5-crack', start: 21.8, end: 23.9, scene: 'street', cam: move([-4.3, 1.9, 5.7], [-3.5, 1.6, 5.3], [-2.0, 0.9, 2.6], [-1.85, 0.85, 2.6], 38) },
  // 8 - "Its body can't pull in enough air." X-ray cutaway of the breathing tubes.
  { id: 'S6-xray', start: 23.9, end: 26.6, scene: 'street', cam: move([1.5, 2.9, 4.75], [1.0, 3.1, 4.45], [-1.2, 0.85, 2.5], [-1.3, 0.85, 2.45], 42) },
  // 9 - "The invasion collapses right on your doorstep." Collapse, then crane up to reveal the street.
  {
    id: 'S7-collapse', start: 26.6, end: 31.0, scene: 'street',
    cam: (u, t) => {
      const a = easeInOut(ramp(t, 26.6, 28.6));
      const b = easeInOut(ramp(t, 28.5, 31.0));
      const pos = lerp3(lerp3([3.75, 1.15, 3.65], [4.2, 1.2, 3.95], a), [8.0, 7.6, 1.4], b);
      const look = lerp3(lerp3([0.8, 0.8, 2.2], [1.6, 0.45, 1.5], a), [-6.0, 0.0, 4.0], b);
      return { pos, look, fov: lerp(40, 44, b) };
    },
  },
];

export function shotAt(t) {
  return SHOTS.find((s) => t >= s.start && t < s.end) ?? SHOTS[SHOTS.length - 1];
}

// ---------------- Character state (pure functions of t) ----------------
const HERO_Z = 2.6;
function heroPath(t) {
  let x = lerp(-9, -1.9, easeOutQuad(ramp(t, 2.9, 6.0)));
  x += 1.0 * easeInOut(ramp(t, 7.75, 8.45));
  let z = HERO_Z - 0.12 * easeInOut(ramp(t, 9.2, 10.6));
  const s = easeInOut(ramp(t, 26.6, 27.9)); // stagger toward the doorstep
  x = lerp(x, 0.95, s);
  z = lerp(z, 2.1, s);
  return { x, z, yaw: 0.75 * s };
}
const speedOf = (path, t) => {
  const a = path(t - 0.05), b = path(t + 0.05);
  return Math.hypot(b.x - a.x, b.z - a.z) / 0.1 + Math.abs(b.yaw - a.yaw) / 0.1;
};

function heroPose(t) {
  const snap = smooth(ramp(t, 11.0, 11.22));
  const sag = easeOut(ramp(t, 11.05, 11.6));
  const collapse = easeIn(ramp(t, 27.45, 28.25));
  const grip = ramp(t, 8.25, 8.85) * (1 - ramp(t, 11.0, 11.12));
  const gasp = pulse(t, 21.8, 27.5, 0.3);
  return {
    t,
    gait: clamp(speedOf(heroPath, t) / 1.4),
    drop: 0.22 * sag + 0.56 * collapse,
    pitch: 0.05 * pulse(t, 6.5, 7.9) + 0.1 * ramp(t, 8.3, 8.9) * (1 - snap) - 0.08 * sag - 0.08 * collapse,
    roll: -0.07 * easeInOut(ramp(t, 9.2, 10.6)) * (1 - snap) + 0.09 * sag + 0.06 * collapse,
    headYaw: 0.55 * pulse(t, 5.7, 7.75, 0.4) - 0.35 * pulse(t, 8.0, 11.1, 0.3) - 0.2 * collapse,
    headPitch: 0.12 * pulse(t, 6.5, 8.0) + 0.25 * pulse(t, 11.0, 11.6, 0.15) - 0.15 * gasp - 0.45 * collapse,
    antennaDroop: clamp(0.35 * ramp(t, 11.1, 12) + 0.15 * gasp + 0.6 * collapse),
    splay: smooth(ramp(t, 27.45, 28.3)),
    crack: ramp(t, 21.95, 23.7),
    xray: smooth(ramp(t, 23.95, 24.35)) * (1 - smooth(ramp(t, 26.2, 26.55))),
    breathe: gasp * 0.022 * Math.sin(t * 9) * (1 - collapse),
    snap: { RF: snap },
    grip,
  };
}

// Background ants - the "hundreds of legs". Same rig, so they look identical to the hero.
const BG = [
  { x0: 6, x1: -7.5, z: 9.0, yaw: Math.PI, t0: 0.4, t1: 5.4 },
  { x0: -27, x1: -13, z: 2.4, yaw: 0, t0: 0.0, t1: 7.0 },
  { x0: -33, x1: -21, z: 9.6, yaw: 0, t0: 0.0, t1: 7.5 },
];
const bgPath = (b) => (t) => ({ x: lerp(b.x0, b.x1, ramp(t, b.t0, b.t1)), z: b.z, yaw: b.yaw });

// ---------------- Frame application ----------------
const _v = new THREE.Vector3(), _w = new THREE.Vector3();

export function createDirector(world) {
  const { street, lab, hero, bgAnts, labAnt, human, scene, camera, overlay, chips } = world;

  const applyHero = (t) => {
    const p = heroPath(t);
    hero.root.position.set(p.x, 0, p.z);
    hero.root.rotation.y = p.yaw;
    // Car door swings open as the ant pulls; small tug-jerks sell the effort.
    const door = 0.5 * easeInOut(ramp(t, 9.25, 10.7)) + 0.035 * Math.sin((t - 9.25) * 13) * pulse(t, 9.3, 10.9, 0.2) - 0.05 * easeOut(ramp(t, 11.0, 11.6));
    street.hinge.rotation.y = -Math.max(0, door);
    const pose = heroPose(t);
    street.group.updateMatrixWorld(true);
    street.handle.getWorldPosition(_v);
    _v.y += 0.02;
    hero.root.updateMatrixWorld(true);
    pose.legOverride = { RF: { amt: pose.grip, target: hero.root.worldToLocal(_v.clone()) } };
    hero.update(pose);
    return pose;
  };

  // Precompute fixed origins for debris (evaluated once => deterministic).
  applyHero(11.05);
  hero.root.updateMatrixWorld(true);
  const snapOrigin = hero.legs[3].tibiaA.localToWorld(new THREE.Vector3(0, 1, 0));
  applyHero(22.5);
  hero.root.updateMatrixWorld(true);
  const crackOrigin = hero.gaster.localToWorld(new THREE.Vector3(0.1, 0.4, 0.9));
  const r = rng(99);
  const chipVel = Array.from({ length: chips.count }, () => [(r() - 0.5) * 2.2, 0.8 + r() * 2.2, (r() - 0.2) * 2.0, r() * 6]);

  function applyStreet(t) {
    street.updateRain(t);
    applyHero(t);
    BG.forEach((b, i) => {
      const ant = bgAnts[i];
      const path = bgPath(b);
      const p = path(t);
      ant.root.position.set(p.x, 0, p.z);
      ant.root.rotation.y = p.yaw;
      const dead = t >= 26.6 ? 1 : 0; // they are only seen collapsed after the cut at 26.6 s
      ant.update({ t: t + i * 1.7, walk: p.x * Math.cos(p.yaw), gait: clamp(speedOf(path, t) / 1.4), drop: 0.78 * dead, splay: dead, antennaDroop: dead, pitch: -0.08 * dead, headPitch: -0.45 * dead, roll: 0.05 * dead });
    });
    // "You" at the window: startled lean-back when the ant turns to look.
    human.update({ t, lean: 0.6 * easeOut(ramp(t, 6.0, 6.6)) * (1 - ramp(t, 9.0, 10.0)), look: -0.3 * pulse(t, 5.3, 8.5, 0.5), raise: 0.35 * easeOut(ramp(t, 6.1, 6.6)) * (1 - ramp(t, 9.0, 10.0)) });

    // Splash rings where the hero's feet strike the wet concrete.
    hero.root.updateMatrixWorld(true);
    const pose = heroPose(t);
    hero.legs.forEach((leg, i) => {
      const ring = street.rings[i];
      const u = leg.stanceU;
      const on = pose.gait > 0.3 && u >= 0 && u < 0.4 && leg.def.name !== 'RF';
      ring.visible = on;
      if (on) {
        hero.root.localToWorld(_w.copy(leg.foot));
        ring.position.set(_w.x, 0.006 + i * 0.0004, _w.z);
        ring.scale.setScalar(1 + u * 6);
        ring.material.opacity = 0.65 * (1 - u / 0.4);
      }
    });

    // Chitin chips: leg snap (11.0 s) and shell cracking (22.3 s+). Simple ballistic arcs, fixed seeds.
    const dm = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
    for (let i = 0; i < chips.count; i++) {
      const crackChip = i >= 10;
      const t0 = crackChip ? 22.3 + (i - 10) * 0.18 : 11.02;
      const o = crackChip ? crackOrigin : snapOrigin;
      const [vx, vy, vz, spin] = chipVel[i];
      const dt = t - t0;
      const alive = dt > 0 && dt < 2.4 && (crackChip ? t < 23.95 : t < 12.4);
      if (!alive) { dm.makeScale(0, 0, 0); chips.setMatrixAt(i, dm); continue; }
      const k = crackChip ? 0.3 : 1;
      const y = Math.max(0.02, o.y + vy * k * dt - 4.9 * dt * dt);
      const settle = y <= 0.021 ? 1 : 0;
      const tg = settle ? (vy * k + Math.sqrt((vy * k) ** 2 + 19.6 * (o.y - 0.02))) / 9.8 : dt;
      e.set(spin * Math.min(dt, tg), spin * 0.7 * Math.min(dt, tg), 0);
      q.setFromEuler(e);
      dm.compose(_v.set(o.x + vx * k * Math.min(dt, tg), y, o.z + vz * k * Math.min(dt, tg)), q, _w.setScalar(crackChip ? 0.05 : 0.07));
      chips.setMatrixAt(i, dm);
    }
    chips.instanceMatrix.needsUpdate = true;

    // "As tall as you": the S3b camera sits at head height (1.82 m), so both head tops project onto
    // the same screen row; the overlay draws a dashed guide between them.
    const showLine = pulse(t, 6.9, 8.0, 0.2);
    if (showLine > 0.01 && t < 8.0) {
      const a = world.humanHead.getWorldPosition(new THREE.Vector3());
      a.y = new THREE.Box3().setFromObject(world.humanHead).max.y;
      const hb = new THREE.Box3().setFromObject(hero.head.children[0]);
      const b = hb.getCenter(new THREE.Vector3());
      b.y = hb.max.y;
      overlay.setGuide(a, b, showLine, camera);
    } else overlay.setGuide(null);
  }

  function labScale(t) {
    return Math.exp(lerp(Math.log(1 / 500), 0, easeInOut(ramp(t, 12.55, 14.45))));
  }

  function applyLab(t, camDist) {
    const s = labScale(t);
    labAnt.root.scale.setScalar(s);
    const press = easeInOut(ramp(t, 16.75, 18.2));
    labAnt.update({
      t, gait: 0, drop: 0.36 * press, splay: 0.55 * press,
      pitch: -0.05 * press + 0.012 * Math.sin(t * 37) * press,
      headPitch: -0.22 * press, antennaDroop: 0.5 * press, roll: 0.01 * Math.sin(t * 29) * press,
    });
    const h = 9 * easeOut(ramp(t, 14.7, 16.3));
    lab.weightBar.visible = h > 0.001;
    lab.weightBar.scale.set(0.8, Math.max(h, 0.001), 0.8);
    const hs = 0.018 * easeOut(ramp(t, 18.7, 19.1));
    lab.strengthBar.visible = hs > 0.0001;
    lab.strengthBar.scale.set(0.06, Math.max(hs, 0.0001), 0.06);
    const ar = pulse(t, 16.6, 18.7, 0.2);
    lab.arrow.visible = ar > 0.01;
    lab.arrow.scale.setScalar(ar);
    lab.arrow.position.set(-0.085, 1.8 - 0.35 * press + 0.06 * Math.sin(t * 8) + 0.4 * (1 - easeOut(ramp(t, 16.6, 17.1))), 0);
    const coinFade = 1 - ramp(s * 500, 3.2, 5.0);
    lab.coin.visible = coinFade > 0;
    lab.coin.material.opacity = coinFade;
    lab.blob.scale.set(2.0 * s, 1.25 * s, 1);
    lab.blob.position.set(-0.38 * s, 0.0003, -0.23 * s);
    lab.blob.rotation.z = 0.55;
    lab.blob.material.opacity = 0.4 * (1 - 0.6 * ramp(s, 0.3, 1));
    lab.grids[0].grid.material.opacity = clamp(1.3 - camDist / 0.25) * 0.8;
    lab.grids[1].grid.material.opacity = clamp((camDist - 0.04) / 0.06) * clamp(1.6 - camDist / 4) * 0.8;
    lab.grids[2].grid.material.opacity = clamp((camDist - 0.4) / 1.0) * 0.8;
    return s;
  }

  function labCam(shot, u, t) {
    const s = labScale(t);
    if (shot.id === 'L1-grow') {
      // Camera pulls back as (scale)^0.68 - slower than the ant grows - so it visibly swells in frame.
      const dist = 0.075 * Math.pow(s * 500, 0.68);
      const c = [-0.6 * 0.85 * s, 0.75 * s, -0.6 * 0.52 * s];
      const look = L(c[0], c[1] + 0.12 * dist, c[2]);
      const dir = new THREE.Vector3(0.42, 0.42, 1).normalize();
      return { pos: [look[0] + dir.x * dist, look[1] + dir.y * dist, look[2] + dir.z * dist], look, fov: 40 };
    }
    // L2: follow the weight bar as it shoots up past the frame.
    const h = 9 * easeOut(ramp(t, 14.7, 16.3));
    const e = easeInOut(u);
    return { pos: L(lerp(1.6, 2.0, e), lerp(1.3, 1.7, e), lerp(9.4, 10.4, e)), look: L(lerp(0.3, 0.6, e), clamp(0.4 * h, 1.0, 2.7), -1.0), fov: 50 };
  }

  const fmt = (n) => Math.round(n).toLocaleString('en-US');

  function applyText(t) {
    const T = [];
    if (t >= 6.8 && t < 8.0) T.push({ main: 'AS TALL AS YOU', o: pulse(t, 6.8, 8.0, 0.15) });
    if (t >= 12.4 && t < 14.6) T.push({ main: '×' + fmt(labScale(t) * 500), sub: labScale(t) * 500 < 1.5 ? 'A 3 MM ANT' : 'TALLER', o: pulse(t, 12.4, 14.6, 0.15) });
    if (t >= 14.6 && t < 18.6) T.push({ main: '×' + fmt(1 + (125e6 - 1) * easeOut(ramp(t, 14.7, 16.3))), sub: 'HEAVIER', subColor: '#ffab5c', o: pulse(t, 14.6, 18.6, 0.15) });
    if (t >= 18.6 && t < 21.8) T.push({ main: '×' + fmt(1 + 249999 * easeOut(ramp(t, 18.65, 19.4))), sub: t > 20.3 ? '= 500× WEAKER FOR ITS WEIGHT' : 'STRONGER', subColor: '#6cf0a2', o: pulse(t, 18.6, 21.8, 0.15) });
    if (t >= 24.1 && t < 26.5) T.push({ main: 'NO LUNGS', sub: 'AIR ONLY DRIFTS IN THROUGH TUBES', color: '#8fefff', o: pulse(t, 24.1, 26.5, 0.2) });
    if (t >= 29.2) T.push({ main: 'TOO BIG', sub: 'TO SURVIVE', o: ramp(t, 29.2, 29.6) });
    overlay.setText(T[0] ?? null);

    const labels = [];
    if (t >= 14.9 && t < 16.6) labels.push({ text: 'WEIGHT', pos: new THREE.Vector3(...L(1.9, 0.9, -1.8)), color: '#ffab5c', o: pulse(t, 14.9, 16.6, 0.2) });
    if (t >= 18.8 && t < 21.8) labels.push({ text: 'STRENGTH', pos: new THREE.Vector3(...L(2.6, 0.03, -1.5)), color: '#6cf0a2', o: pulse(t, 18.8, 21.8, 0.2) });
    if (t >= 20.6 && t < 21.8) labels.push({ text: 'WEIGHT', pos: new THREE.Vector3(...L(1.9, 1.0, -1.8)), color: '#ffab5c', o: pulse(t, 20.6, 21.8, 0.2) });
    if (t >= 24.4 && t < 26.4) {
      hero.root.updateMatrixWorld(true);
      labels.push({ text: 'AIR STOPS HERE', pos: hero.body.localToWorld(new THREE.Vector3(-1.5, 1.3, 0.3)), color: '#ff8a7a', o: pulse(t, 24.4, 26.4, 0.2) });
    }
    overlay.setLabels(labels, camera);
  }

  // Controlled shake only on the two impacts (leg snap, final collapse).
  function shake(t) {
    const a = 0.045 * Math.exp(-Math.max(0, t - 11.02) * 7) * (t >= 11.02 ? 1 : 0) + 0.025 * Math.exp(-Math.max(0, t - 28.2) * 6) * (t >= 28.2 ? 1 : 0);
    return [a * Math.sin(t * 61), a * Math.sin(t * 47 + 1), a * 0.5 * Math.sin(t * 53 + 2)];
  }

  function apply(t) {
    const shot = shotAt(t);
    const u = clamp((t - shot.start) / (shot.end - shot.start));
    const isLab = shot.scene === 'lab';
    street.group.visible = !isLab;
    lab.group.visible = isLab;
    scene.background = isLab ? world.bg.lab : world.bg.street;
    scene.fog = isLab ? world.fog.lab : world.fog.street;

    const c = shot.cam ? shot.cam(u, t) : labCam(shot, u, t);
    const sh = shake(t);
    camera.position.set(c.pos[0] + sh[0], c.pos[1] + sh[1], c.pos[2] + sh[2]);
    camera.fov = c.fov;
    camera.lookAt(c.look[0], c.look[1], c.look[2]);
    const camDist = camera.position.distanceTo(_v.set(...c.look));
    camera.near = isLab ? clamp(camDist * 0.02, 0.0004, 0.1) : 0.05;
    camera.far = isLab ? 200 : 140;
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld(); // labels/guide project with this frame's camera, not last frame's

    overlay.setGuide(null);
    if (isLab) applyLab(t, camDist);
    else applyStreet(t);
    scene.updateMatrixWorld(true);
    applyText(t);
    return shot;
  }

  return { apply };
}
