import * as THREE from 'three';
import { M } from '../materials.js';
import { rng, clamp, lerp, smooth } from '../timeline.js';

// Giant ant rig, built in metres at "human-sized" scale (head top ~1.75 m, length ~3.4 m), facing +X.
// Legs are solved every frame with analytic two-bone IK so they always stay attached to the thorax
// and the knees always bend upward/outward (no reversed joints).

const UP = new THREE.Vector3(0, 1, 0);
const SPH = new THREE.SphereGeometry(1, 12, 9);
const SPH_HI = new THREE.SphereGeometry(1, 16, 12);
const JOINT = new THREE.SphereGeometry(1, 8, 6);
const SEG = new THREE.CylinderGeometry(1, 1, 1, 7, 1).translate(0, 0.5, 0);
const SEG_TAPER = new THREE.CylinderGeometry(0.65, 1, 1, 7, 1).translate(0, 0.5, 0);
const CONE = new THREE.ConeGeometry(1, 1, 5).translate(0, 0.5, 0);
const AIR = new THREE.IcosahedronGeometry(1, 0);

export const LEG_DEFS = [
  // side: -1 = left (-Z), +1 = right (+Z). grp = tripod gait group.
  { name: 'LF', side: -1, ax: 0.45, ay: 0.98, rx: 1.15, rz: 1.0, grp: 0 },
  { name: 'LM', side: -1, ax: 0.05, ay: 0.95, rx: 0.05, rz: 1.15, grp: 1 },
  { name: 'LR', side: -1, ax: -0.3, ay: 0.95, rx: -1.0, rz: 1.05, grp: 0 },
  { name: 'RF', side: 1, ax: 0.45, ay: 0.98, rx: 1.15, rz: 1.0, grp: 1 },
  { name: 'RM', side: 1, ax: 0.05, ay: 0.95, rx: 0.05, rz: 1.15, grp: 0 },
  { name: 'RR', side: 1, ax: -0.3, ay: 0.95, rx: -1.0, rz: 1.05, grp: 1 },
];
const L_FEMUR = 1.0, L_TIBIA = 1.15, STRIDE = 1.8;

const _v = new THREE.Vector3(), _d = new THREE.Vector3(), _p = new THREE.Vector3();

function placeSegment(mesh, a, b, r) {
  _d.subVectors(b, a);
  const len = Math.max(_d.length(), 1e-4);
  mesh.position.copy(a);
  mesh.quaternion.setFromUnitVectors(UP, _d.multiplyScalar(1 / len));
  mesh.scale.set(r, len, r);
}

// Two-bone IK: returns knee position for hip a -> foot b, bending toward `hint`.
function solveKnee(a, b, hint, out) {
  _d.subVectors(b, a);
  let d = _d.length();
  d = clamp(d, 0.05, L_FEMUR + L_TIBIA - 1e-3);
  _d.normalize();
  const x = (L_FEMUR * L_FEMUR - L_TIBIA * L_TIBIA + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, L_FEMUR * L_FEMUR - x * x));
  _p.copy(hint).addScaledVector(_d, -hint.dot(_d)).normalize();
  return out.copy(a).addScaledVector(_d, x).addScaledVector(_p, h);
}

export function createAnt(name = 'ant', seed = 7) {
  const rand = rng(seed);
  const root = new THREE.Group();
  root.name = name;
  root.userData.kind = 'ant';
  const body = new THREE.Group();
  body.name = name + ':body';
  root.add(body);

  // Per-ant material instances so one ant can fade to x-ray without affecting the others.
  const mats = { shell: M.antShell.clone(), dark: M.antDark.clone(), eye: M.antEye.clone() };
  const shellMeshes = [];
  const mk = (geo, mat, parent, part, solid = true) => {
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.receiveShadow = true;
    m.userData.part = part;
    m.userData.solid = solid;
    parent.add(m);
    shellMeshes.push(m);
    return m;
  };
  const ell = (parent, part, mat, s, p, rz = 0, geo = SPH) => {
    const m = mk(geo, mat, parent, part);
    m.scale.set(...s);
    m.position.set(...p);
    m.rotation.z = rz;
    return m;
  };

  // --- Body (mesosoma, petiole, gaster) ---
  const pronotum = ell(body, 'thorax', mats.shell, [0.42, 0.36, 0.34], [0.38, 1.1, 0], -0.2);
  const meso = ell(body, 'thorax', mats.shell, [0.5, 0.3, 0.3], [-0.12, 1.02, 0], 0.05, SPH_HI);
  ell(body, 'thorax', mats.shell, [0.2, 0.18, 0.22], [-0.42, 1.08, 0]);
  ell(body, 'neck', mats.dark, [0.15, 0.12, 0.12], [0.68, 1.2, 0]);
  ell(body, 'petiole', mats.dark, [0.3, 0.08, 0.08], [-0.66, 0.99, 0]);
  ell(body, 'petiole', mats.shell, [0.11, 0.21, 0.14], [-0.66, 1.1, 0]);
  const gaster = ell(body, 'gaster', mats.shell, [0.88, 0.66, 0.64], [-1.5, 1.08, 0], 0.12, SPH_HI);
  // Darker segment bands give the abdomen a readable, layered silhouette.
  for (const dx of [0.36, 0.0]) {
    const r = Math.sqrt(1 - (dx / 0.88) ** 2);
    const band = mk(SPH_HI, mats.dark, gaster, 'gasterBand');
    band.scale.set(0.035, r * 1.03, r * 1.03);
    band.position.set(dx, 0, 0);
  }

  // --- Head ---
  const head = new THREE.Group();
  head.name = name + ':headGroup';
  head.position.set(0.78, 1.38, 0);
  body.add(head);
  ell(head, 'head', mats.shell, [0.36, 0.34, 0.33], [0.12, 0, 0]);
  for (const s of [-1, 1]) {
    const eye = mk(SPH, mats.eye, head, 'eye');
    eye.scale.set(0.085, 0.1, 0.06);
    eye.position.set(0.2, 0.1, s * 0.29);
    const md = mk(CONE, mats.dark, head, 'mandible');
    md.scale.set(0.06, 0.3, 0.05);
    md.position.set(0.4, -0.16, s * 0.1);
    md.rotation.set(0, 0, -Math.PI / 2);
    md.rotation.y = -s * 0.35;
  }
  // Antennae: scape + 2 funiculus segments + club, solved each frame in head space.
  const antennae = [-1, 1].map((s) => ({
    s,
    scape: mk(SEG, mats.dark, head, 'antennaScape'),
    elbow: mk(JOINT, mats.dark, head, 'antennaJoint'),
    fun1: mk(SEG_TAPER, mats.dark, head, 'antennaFun'),
    fun2: mk(SEG_TAPER, mats.dark, head, 'antennaFun'),
    club: mk(JOINT, mats.shell, head, 'antennaClub'),
    socket: new THREE.Vector3(0.36, 0.14, s * 0.12),
  }));

  // --- Legs (children of root, positioned by IK) ---
  const legs = LEG_DEFS.map((def) => ({
    def,
    coxa: mk(JOINT, mats.shell, root, 'coxa'),
    femur: mk(SEG, mats.shell, root, 'femur'),
    knee: mk(JOINT, mats.dark, root, 'knee'),
    tibiaA: mk(SEG, mats.dark, root, 'tibia'),
    tibiaB: mk(SEG_TAPER, mats.dark, root, 'tibiaTip'),
    tarsus: mk(SEG_TAPER, mats.dark, root, 'tarsus'),
    foot: new THREE.Vector3(),
    kneeP: new THREE.Vector3(),
    stanceU: 0,
  }));

  // --- Cracks (grow along the shell when crack > 0) ---
  const cracks = [];
  const crackOn = (mesh, n, bias) => {
    for (let c = 0; c < n; c++) {
      const pts = [];
      let p = new THREE.Vector3(bias.x + (rand() - 0.5) * 0.6, bias.y + (rand() - 0.2) * 0.6, bias.z).normalize();
      let dir = new THREE.Vector3(rand() - 0.5, rand() - 0.5, rand() - 0.5).cross(p).normalize();
      for (let i = 0; i < 9; i++) {
        pts.push(p.clone().multiplyScalar(1.022));
        dir.add(new THREE.Vector3(rand() - 0.5, rand() - 0.5, rand() - 0.5).multiplyScalar(0.9)).cross(p).cross(p).negate().normalize();
        p = p.clone().addScaledVector(dir, 0.16).normalize();
      }
      const geo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 32, 0.009, 4, false);
      const m = new THREE.Mesh(geo, M.crack);
      m.userData.part = 'crack';
      m.userData.delay = c / n * 0.45;
      m.visible = false;
      mesh.add(m);
      cracks.push(m);
    }
  };
  crackOn(gaster, 6, new THREE.Vector3(0.1, 0.5, 1));
  crackOn(meso, 3, new THREE.Vector3(0.0, 0.6, 1));
  crackOn(pronotum, 2, new THREE.Vector3(0.2, 0.5, 1));

  // --- Tracheae (x-ray cutaway): two trunks + spiracle branches; air stalls before the core ---
  const tracheae = new THREE.Group();
  tracheae.name = name + ':tracheae';
  tracheae.visible = false;
  body.add(tracheae);
  const airPaths = [];
  for (const s of [-1, 1]) {
    const trunk = new THREE.CatmullRomCurve3([
      [0.85, 1.32, 0.1], [0.4, 1.12, 0.18], [-0.1, 1.03, 0.15], [-0.66, 1.08, 0.05], [-1.1, 1.1, 0.22], [-1.6, 1.08, 0.24], [-2.1, 1.04, 0.12],
    ].map(([x, y, z]) => new THREE.Vector3(x, y, z * s)));
    tracheae.add(new THREE.Mesh(new THREE.TubeGeometry(trunk, 64, 0.03, 6, false), M.trachea));
    const spiracles = [[0.36, 1.06, 0.33], [-0.1, 0.98, 0.29], [-1.15, 1.18, 0.6], [-1.55, 1.12, 0.63], [-1.92, 1.06, 0.52]];
    spiracles.forEach(([x, y, z], i) => {
      const inner = new THREE.Vector3(x - 0.02, y, s * (z * 0.45));
      const core = new THREE.Vector3(i < 2 ? -0.05 : -1.5, i < 2 ? 1.04 : 1.08, 0);
      const path = new THREE.CatmullRomCurve3([new THREE.Vector3(x, y, z * s), inner, inner.clone().lerp(core, 0.5), core]);
      const branch = new THREE.CatmullRomCurve3([new THREE.Vector3(x, y, z * s), inner, inner.clone().lerp(core, 0.42)]);
      tracheae.add(new THREE.Mesh(new THREE.TubeGeometry(branch, 20, 0.022, 5, false), M.trachea));
      airPaths.push(path);
    });
  }
  const cores = [
    [[-1.5, 1.08, 0], 0.3],
    [[-0.05, 1.04, 0], 0.17],
  ].map(([p, r]) => {
    const m = new THREE.Mesh(JOINT, M.core.clone());
    m.position.set(...p);
    m.scale.setScalar(r);
    m.renderOrder = 2;
    tracheae.add(m);
    return m;
  });
  const AIR_PER = 4;
  const air = new THREE.InstancedMesh(AIR, M.air, airPaths.length * AIR_PER);
  air.frustumCulled = false;
  tracheae.add(air);
  const dummy = new THREE.Object3D();

  let xrayState = 0;
  const setXray = (x) => {
    for (const k of ['shell', 'dark', 'eye']) {
      const m = mats[k];
      const tr = x > 0.001;
      if (m.transparent !== tr) { m.transparent = tr; m.needsUpdate = true; }
      m.opacity = lerp(1, k === 'eye' ? 0.35 : 0.16, x);
      m.depthWrite = x < 0.5;
    }
    tracheae.visible = x > 0.02;
    xrayState = x;
  };

  const hint = new THREE.Vector3();
  const attach = new THREE.Vector3();
  const target = new THREE.Vector3();

  // Pose input (all optional): see shots.js for how each is driven from the master timeline.
  function update(p) {
    const t = p.t ?? 0;
    body.position.set(0, -(p.drop ?? 0), 0);
    body.rotation.set(p.roll ?? 0, 0, p.pitch ?? 0);
    const br = p.breathe ?? 0;
    body.scale.set(1, 1 + br, 1 + br * 0.6);
    body.updateMatrix();

    head.rotation.set(0, p.headYaw ?? 0, p.headPitch ?? 0);
    head.rotation.order = 'YZX';

    // Antennae: elbowed, with a slow searching wiggle; `droop` lowers them.
    const droop = p.antennaDroop ?? 0;
    for (const a of antennae) {
      const w1 = Math.sin(t * 3.1 + a.s * 1.3) * 0.18 * (1 - droop);
      const w2 = Math.sin(t * 4.3 + a.s * 0.7) * 0.22 * (1 - droop);
      const elbow = _v.set(0.3 * Math.cos(w1), lerp(0.48, 0.12, droop), a.s * (0.22 + 0.1 * Math.sin(w1))).add(a.socket);
      placeSegment(a.scape, a.socket, elbow, 0.035);
      a.elbow.position.copy(elbow);
      a.elbow.scale.setScalar(0.045);
      const mid = elbow.clone().add(new THREE.Vector3(0.36, lerp(0.08, -0.22, droop) + w2 * 0.3, a.s * (0.08 + w2 * 0.2)));
      const tip = mid.clone().add(new THREE.Vector3(0.32, lerp(-0.1, -0.3, droop) + w2 * 0.2, a.s * 0.05));
      placeSegment(a.fun1, elbow, mid, 0.03);
      placeSegment(a.fun2, mid, tip, 0.03);
      a.club.position.copy(tip);
      a.club.scale.set(0.06, 0.045, 0.045);
    }

    const walk = p.walk ?? 0; // distance walked (m), drives gait phase
    const gait = p.gait ?? 0; // 0 = standing still, 1 = full stride
    const splay = p.splay ?? 0;
    const phase = walk / STRIDE;
    for (const leg of legs) {
      const d = leg.def;
      attach.set(d.ax, d.ay, d.side * 0.17).applyMatrix4(body.matrix);
      // Tripod gait: stance for half the cycle (foot planted, slides back relative to body), swing for the other half.
      const u = (((phase + d.grp * 0.5) % 1) + 1) % 1;
      let off, lift = 0;
      if (u < 0.5) off = STRIDE / 4 - (u / 0.5) * (STRIDE / 2);
      else { const w = smooth((u - 0.5) / 0.5); off = -STRIDE / 4 + w * (STRIDE / 2); lift = Math.sin(Math.PI * w) * 0.38; }
      leg.stanceU = u < 0.5 ? u / 0.5 : -1;
      target.set(d.rx + off * gait, 0.05 + lift * gait, d.side * d.rz * (1 + 0.35 * splay));
      target.x += (d.rx > 0 ? 0.2 : d.rx < -0.5 ? -0.25 : 0) * splay;

      // Optional per-leg override (grip): blend toward a target point given in root space.
      const ov = p.legOverride?.[d.name];
      if (ov && ov.amt > 0) target.lerp(ov.target, ov.amt);

      hint.set(0, 1.0 + splay * 0.6, d.side * 0.75);
      solveKnee(attach, target, hint, leg.kneeP);
      leg.coxa.position.copy(attach);
      leg.coxa.scale.setScalar(0.1);
      placeSegment(leg.femur, attach, leg.kneeP, 0.075);
      leg.knee.position.copy(leg.kneeP);
      leg.knee.scale.setScalar(0.082);
      // Tibia is two collinear pieces so it can visibly snap at its midpoint while staying attached.
      _d.subVectors(target, leg.kneeP);
      const tl = Math.min(_d.length(), L_TIBIA);
      _d.normalize();
      const brk = leg.kneeP.clone().addScaledVector(_d, tl * 0.5);
      placeSegment(leg.tibiaA, leg.kneeP, brk, 0.062);
      const snap = p.snap?.[d.name] ?? 0;
      const tipDir = _d.clone();
      if (snap > 0) {
        const hang = new THREE.Vector3(-0.35, -1, d.side * 0.25).normalize();
        tipDir.lerp(hang, snap).normalize();
      }
      const footP = brk.clone().addScaledVector(tipDir, tl * 0.5);
      placeSegment(leg.tibiaB, brk, footP, 0.055);
      // Tarsus lies outward/forward from the foot along the ground (or hangs when snapped).
      const tarDir = new THREE.Vector3(d.rx > 0.5 ? 0.6 : d.rx < -0.5 ? -0.6 : 0, -0.15, d.side * 0.8).normalize();
      if (snap > 0) tarDir.lerp(tipDir, snap).normalize();
      placeSegment(leg.tarsus, footP, footP.clone().addScaledVector(tarDir, 0.3), 0.032);
      leg.foot.copy(footP);
    }

    // Cracks grow along their tube in sequence.
    const crack = p.crack ?? 0;
    for (const c of cracks) {
      const u = clamp((crack - c.userData.delay) / 0.55);
      c.visible = u > 0;
      const per = c.geometry.parameters.radialSegments * 6;
      c.geometry.setDrawRange(0, Math.ceil(u * 32) * per);
    }

    setXray(p.xray ?? 0);
    if (tracheae.visible) {
      // Air enters through the spiracles but fades out before ~45% of the way to the core.
      let k = 0;
      airPaths.forEach((path, i) => {
        for (let j = 0; j < AIR_PER; j++) {
          const f = ((t * 0.45 + j / AIR_PER + i * 0.137) % 1);
          const reach = f * 0.5;
          path.getPoint(reach, dummy.position);
          const fade = 1 - smooth(clamp((reach - 0.3) / 0.2));
          dummy.scale.setScalar(0.045 * fade * xrayState);
          dummy.updateMatrix();
          air.setMatrixAt(k++, dummy.matrix);
        }
      });
      air.instanceMatrix.needsUpdate = true;
      const pulse = 0.5 + 0.5 * Math.sin(t * 6);
      for (const c of cores) c.material.opacity = xrayState * (0.35 + 0.35 * pulse);
    }
  }

  // Exposed helpers
  return {
    root, body, head, legs, cracks, tracheae, gaster, meso, update,
    headWorld: (out) => head.getWorldPosition(out),
  };
}
