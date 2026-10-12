// Segment 4: X-ray of the fountain ant. Spiracles open into branching tracheae;
// oxygen (blue particles) diffuses in slowly and fades before reaching deep muscle,
// which dims from orange to grey.
import * as THREE from 'three';
import { range, smooth, win } from './util.js';

export function buildXray(ant) {
  const tubes = new THREE.Group(); ant.body.add(tubes);
  const tubeMat = new THREE.MeshStandardMaterial({ color: 0xf3e7c6, emissive: 0x6a5a3a, emissiveIntensity: 0.4, roughness: 0.5 });
  const curves = [];
  const thorax = new THREE.Vector3(0, 0.012, 0.06), gaster = new THREE.Vector3(0, 0.035, -0.33);
  ant.spiracles.forEach((sp, i) => {
    const sgn = Math.sign(sp.x);
    const inThorax = sp.z > -0.1;
    const target = inThorax ? thorax.clone().add(new THREE.Vector3(sgn * 0.02, -0.01, (i % 2 ? -0.05 : 0.05))) : gaster.clone().add(new THREE.Vector3(sgn * 0.04, 0, sp.z + 0.33));
    const outside = sp.clone().add(new THREE.Vector3(sgn * 0.16, 0.02, 0));
    const mid = sp.clone().lerp(target, 0.45).add(new THREE.Vector3(0, 0.02, 0));
    const main = new THREE.CatmullRomCurve3([outside, sp.clone(), mid, target]);
    curves.push(main);
    const inner = new THREE.CatmullRomCurve3([sp.clone(), mid, target]);
    tubes.add(new THREE.Mesh(new THREE.TubeGeometry(inner, 24, 0.009, 6), tubeMat));
    // Branching tracheoles from the main trunk.
    for (let b = 0; b < 3; b++) {
      const p0 = inner.getPoint(0.35 + b * 0.22);
      const p1 = p0.clone().add(new THREE.Vector3(-sgn * 0.03, (b - 1) * 0.03, (b % 2 ? 1 : -1) * 0.04));
      const p2 = p1.clone().add(new THREE.Vector3(-sgn * 0.015, (b - 1) * 0.02, (b % 2 ? 1 : -1) * 0.03));
      tubes.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([p0, p1, p2]), 8, 0.004, 5), tubeMat));
    }
  });
  // Tracheae continue into the legs (to the femur muscles).
  tubes.visible = false;

  const PER = 7;
  const o2Mat = new THREE.MeshStandardMaterial({ color: 0x59b8ff, emissive: 0x2a8cff, emissiveIntensity: 1.4, roughness: 0.3 });
  const parts = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6), o2Mat, curves.length * PER);
  parts.frustumCulled = false; ant.body.add(parts);
  const shell = [ant.mats.red, ant.mats.dark, ant.mats.leg, ant.mats.eye];
  const orange = new THREE.Color(0xff7a2a), grey = new THREE.Color(0x6d6a66), eo = new THREE.Color(0xff5a10), eg = new THREE.Color(0x000000);
  const m4 = new THREE.Matrix4(), v = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();

  function update(t) {
    const x = win(t, 32.2, 40.4, 0.6); // X-ray amount
    const on = x > 0.001;
    for (const m of shell) {
      // Toggling transparency changes the shader (OPAQUE define), so recompile on change.
      if (m.transparent !== on) { m.transparent = on; m.depthWrite = !on; m.needsUpdate = true; }
      m.opacity = 1 - 0.55 * x;
    }
    tubes.visible = on; parts.visible = on;
    tubes.scale.setScalar(Math.max(0.001, smooth(range(t, 32.4, 33.6))));
    for (const mu of ant.muscles) mu.visible = on;
    const dim = smooth(range(t, 36.8, 39.6));
    ant.mats.muscle.color.copy(orange).lerp(grey, dim);
    ant.mats.muscle.emissive.copy(eo).lerp(eg, dim);
    ant.mats.muscle.opacity = 1;
    let k = 0;
    curves.forEach((c, ci) => {
      for (let j = 0; j < PER; j++) {
        const u = ((t * 0.16 + j / PER + ci * 0.137) % 1);
        // Diffusion is slow: particles only make it ~55% of the way in, shrinking as they go.
        const reach = u * 0.62;
        const size = on && t > 33.2 ? 0.011 * Math.max(0, 1 - Math.pow(reach / 0.62, 1.6)) : 0;
        c.getPoint(reach, v);
        m4.compose(v, q, s.setScalar(size + 1e-6)); parts.setMatrixAt(k++, m4);
      }
    });
    parts.instanceMatrix.needsUpdate = true;
  }
  return { update };
}
