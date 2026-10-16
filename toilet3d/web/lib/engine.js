// Realistic real-time 3D engine for the cut-away explainer videos (three.js / WebGL).
// Deterministic: renderAt(t) draws the exact frame for time t, so frames can be
// rendered in any order and resumed.  Lighting: physical sky + sun with soft
// shadows, image-based ambient light from the sky, ambient occlusion (GTAO),
// aerial-perspective fog, optional depth of field, ACES/AgX tone mapping.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { N8AOPass } from 'n8ao';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { Sky } from 'three/addons/objects/Sky.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export { THREE };

// ---------------------------------------------------------------- timing helpers
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lin = (t, a, b) => (b <= a ? (t >= b ? 1 : 0) : clamp((t - a) / (b - a)));
export const smooth = (t, a, b) => { const u = lin(t, a, b); return u * u * (3 - 2 * u); };
export const ease = (t, a, b) => { const u = lin(t, a, b); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; };
export const backOut = (u, s = 1.7) => { u = clamp(u) - 1; return u * u * ((s + 1) * u + s) + 1; };
export const pop = (t, t0, d = 0.35) => (t < t0 ? 0 : backOut((t - t0) / d));
export const lerp = (a, b, u) => a + (b - a) * u;

// Seeded random so every frame is identical on every machine
export function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}

// ---------------------------------------------------------------- renderer + environment
export class Stage {
  constructor({ width = 1080, height = 1920, scale = 1, quality = 'full' } = {}) {
    this.W = Math.round(width * scale); this.H = Math.round(height * scale);
    const r = this.renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    r.setPixelRatio(1); r.setSize(this.W, this.H);
    r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFShadowMap;
    r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 0.58;
    r.outputColorSpace = THREE.SRGBColorSpace;
    document.getElementById('stage').appendChild(r.domElement);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, this.W / this.H, 0.05, 3000);
    this.loader = new THREE.TextureLoader();
    this.textures = {};
    this.updaters = [];
    this.quality = quality;
  }

  // physical sky + sun + sky-lit ambient light
  setupSky({ elevation = 48, azimuth = 210, turbidity = 2.2, rayleigh = 2.2, sunColor = 0xfff0dc, sunIntensity = 4.2,
             fog = 0xb9cfe2, fogDensity = 0.006, envIntensity = 0.45 } = {}) {
    const sky = this.sky = new Sky();
    sky.scale.setScalar(2500);
    const u = sky.material.uniforms;
    u.turbidity.value = turbidity; u.rayleigh.value = rayleigh; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.8;
    this.sunDir = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - elevation), THREE.MathUtils.degToRad(azimuth));
    u.sunPosition.value.copy(this.sunDir);
    sky.visible = false;  // used only to light the scene (environment map below)
    // visible sky: clean blue gradient dome (the physical sky above is used for lighting only)
    const dome = new THREE.Mesh(new THREE.SphereGeometry(2400, 32, 16), new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: true, fog: false,
      uniforms: { top: { value: new THREE.Color(0x6a9ad6) }, mid: { value: new THREE.Color(0xa3c4e6) }, bottom: { value: new THREE.Color(0xdbe8f2) } },
      vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 top; uniform vec3 mid; uniform vec3 bottom; varying vec3 vP; void main(){ float h = max(vP.y, 0.0); vec3 c = mix(bottom, mid, smoothstep(0.0, 0.12, h)); c = mix(c, top, smoothstep(0.12, 0.6, h)); gl_FragColor = vec4(c, 1.0); }',
    }));
    dome.renderOrder = -1;
    this.scene.add(dome);
    const pm = new THREE.PMREMGenerator(this.renderer);
    const envScene = new THREE.Scene(); const sky2 = sky.clone(); sky2.visible = true; envScene.add(sky2);
    this.scene.environment = pm.fromScene(envScene, 0.02).texture;
    this.scene.environmentIntensity = envIntensity;
    const sun = this.sun = new THREE.DirectionalLight(sunColor, sunIntensity);
    sun.castShadow = true;
    sun.shadow.mapSize.set(this.quality === 'preview' ? 2048 : 4096, this.quality === 'preview' ? 2048 : 4096);
    sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03; sun.shadow.radius = 3;
    this.scene.add(sun); this.scene.add(sun.target);
    this.setShadowBox(new THREE.Vector3(0, 0, -4), 18);
    this.scene.fog = new THREE.FogExp2(fog, fogDensity);
    const hemi = new THREE.HemisphereLight(0xcfe3ff, 0x5a4a35, 0.2); this.scene.add(hemi);
    return this;
  }

  setShadowBox(center, half) {
    const s = this.sun;
    s.target.position.copy(center);
    s.position.copy(center).addScaledVector(this.sunDir, 60);
    Object.assign(s.shadow.camera, { left: -half, right: half, top: half, bottom: -half, near: 1, far: 160 });
    s.shadow.camera.updateProjectionMatrix();
  }

  setupPost({ ao = true, dof = false, focus = 12, aperture = 0.00012, maxblur = 0.006 } = {}) {
    const c = this.composer = new EffectComposer(this.renderer);
    c.setPixelRatio(1); c.setSize(this.W, this.H);
    if (ao) {
      // N8AO: renders the scene + screen-space ambient occlusion (handles the open sky correctly)
      const n = this.n8ao = new N8AOPass(this.scene, this.camera, this.W, this.H);
      Object.assign(n.configuration, { aoRadius: 0.9, distanceFalloff: 1.0, intensity: 2.4, aoSamples: this.quality === 'preview' ? 8 : 16,
        denoiseSamples: this.quality === 'preview' ? 4 : 8, denoiseRadius: 10, halfRes: false, gammaCorrection: false });
      c.addPass(n);
    } else {
      c.addPass(new RenderPass(this.scene, this.camera));
    }
    if (dof) { this.bokeh = new BokehPass(this.scene, this.camera, { focus, aperture, maxblur }); c.addPass(this.bokeh); }
    c.addPass(new OutputPass());
    c.addPass(new SMAAPass(this.W, this.H));
    return this;
  }

  // ---------------------------------------------------------------- materials
  tex(name, repeat = 1, srgb = false) {
    const key = name + '|' + repeat + '|' + srgb;
    if (!this.textures[key]) {
      const t = this.loader.load('textures/' + name);
      t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat, repeat);
      t.anisotropy = 8; if (srgb) t.colorSpace = THREE.SRGBColorSpace;
      this.textures[key] = t;
    }
    return this.textures[key];
  }

  // PBR material from a generated texture set; `tile` = metres per texture repeat (UVs are in metres)
  pbr(set, { tile = 2, color = 0xffffff, normalScale = 1, roughness = 1, metalness = 0, ...rest } = {}) {
    const rep = 1 / tile;
    return new THREE.MeshStandardMaterial({
      map: this.tex(set + '_albedo.jpg', rep, true), normalMap: this.tex(set + '_normal.jpg', rep),
      roughnessMap: this.tex(set + '_rough.jpg', rep), normalScale: new THREE.Vector2(normalScale, normalScale),
      color, roughness, metalness, ...rest,
    });
  }

  async ready() {
    const pending = Object.values(this.textures).filter(t => !t.image);
    await Promise.all(pending.map(t => new Promise(res => { const chk = () => (t.image ? res() : setTimeout(chk, 30)); chk(); })));
    this.renderer.compile(this.scene, this.camera);
  }

  onUpdate(fn) { this.updaters.push(fn); }

  render(t) {
    for (const fn of this.updaters) fn(t);
    if (this.bokeh && this.focusTarget) {
      this.bokeh.uniforms.focus.value = this.camera.position.distanceTo(this.focusTarget);
    }
    (this.composer || this.renderer).render(this.scene, this.camera);
  }
}

// ---------------------------------------------------------------- geometry helpers (UVs in metres)
export function worldBox(w, h, d) {
  const g = new THREE.BoxGeometry(w, h, d);
  const pos = g.attributes.position, nrm = g.attributes.normal, uv = g.attributes.uv;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const nx = Math.abs(nrm.getX(i)), ny = Math.abs(nrm.getY(i));
    if (nx > 0.5) uv.setXY(i, z, y); else if (ny > 0.5) uv.setXY(i, x, z); else uv.setXY(i, x, y);
  }
  return g;
}

export function box(stage, mat, w, h, d, x = 0, y = 0, z = 0, { cast = true, receive = true } = {}) {
  const m = new THREE.Mesh(worldBox(w, h, d), mat);
  m.position.set(x, y, z); m.castShadow = cast; m.receiveShadow = receive;
  stage.scene.add(m);
  return m;
}

// Cut-away ground: a soil block whose front face (z = 0) is the section plane.
// `holes` are closed outlines [[x, y], ...] cut from the front face back to `holeDepth`
// metres (pits, trenches); behind that the ground is solid.  `lawnHoles` are the
// matching openings in the lawn, as [[x, distanceBack], ...].
export function cutGround(stage, { x0 = -30, x1 = 30, depth = 14, back = 60, holes = [], holeDepth = 2, soil, lawn, lawnHoles = [] }) {
  const outline = (path) => { path.moveTo(x0, -depth); path.lineTo(x1, -depth); path.lineTo(x1, 0); path.lineTo(x0, 0); path.lineTo(x0, -depth); return path; };
  const parts = [];
  if (holes.length) {
    const sh = outline(new THREE.Shape());
    for (const h of holes) { const p = new THREE.Path(); h.forEach(([x, y], i) => (i ? p.lineTo(x, y) : p.moveTo(x, y))); sh.holes.push(p); }
    const g = new THREE.ExtrudeGeometry(sh, { depth: holeDepth, bevelEnabled: false }); g.translate(0, 0, -holeDepth);
    parts.push(g);
  }
  const d0 = holes.length ? holeDepth : 0;
  const g2 = new THREE.ExtrudeGeometry(outline(new THREE.Shape()), { depth: back - d0, bevelEnabled: false });
  g2.translate(0, 0, -back);
  parts.push(g2);
  const meshes = parts.map(g => { const m = new THREE.Mesh(g, soil); m.receiveShadow = true; m.castShadow = true; stage.scene.add(m); return m; });
  const ls = new THREE.Shape();
  ls.moveTo(x0, 0); ls.lineTo(x1, 0); ls.lineTo(x1, back); ls.lineTo(x0, back); ls.lineTo(x0, 0);
  for (const h of lawnHoles) { const p = new THREE.Path(); h.forEach(([x, z], i) => (i ? p.lineTo(x, z) : p.moveTo(x, z))); ls.holes.push(p); }
  const lg = new THREE.ShapeGeometry(ls); lg.rotateX(-Math.PI / 2);
  const uv = lg.attributes.uv, pos = lg.attributes.position;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getX(i), -pos.getZ(i));
  const lm = new THREE.Mesh(lg, lawn); lm.position.y = 0.003; lm.receiveShadow = true;
  stage.scene.add(lm);
  return { soilMeshes: meshes, lawnMesh: lm };
}

// Grass tufts along the cut edge and scattered on the lawn (instanced blades)
export function grassTufts(stage, { count = 3000, x0 = -12, x1 = 12, z0 = -0.05, z1 = -6, seed = 3, height = 0.12, edgeBias = 0.6 } = {}) {
  const blade = new THREE.ConeGeometry(0.012, 1, 3); blade.translate(0, 0.5, 0);
  const mat = new THREE.MeshStandardMaterial({ color: 0x4f8a26, roughness: 0.8 });
  const im = new THREE.InstancedMesh(blade, mat, count);
  const r = rng(seed), m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), s = new THREE.Vector3(), p = new THREE.Vector3();
  const col = new THREE.Color();
  for (let i = 0; i < count; i++) {
    const zEdge = r() < edgeBias;
    p.set(lerp(x0, x1, r()), 0, zEdge ? lerp(z0, z0 - 0.25, r()) : lerp(z0, z1, r()));
    e.set((r() - 0.5) * 0.6, r() * 6.28, (r() - 0.5) * 0.6); q.setFromEuler(e);
    const hh = height * (0.6 + r() * 0.9); s.set(1, hh, 1);
    m.compose(p, q, s); im.setMatrixAt(i, m);
    im.setColorAt(i, col.setHSL(0.24 + r() * 0.05, 0.55, 0.22 + r() * 0.15));
  }
  im.castShadow = false; im.receiveShadow = true;
  stage.scene.add(im);
  return im;
}

// Broad-leaf tree: tapered trunk + branches + leaf-card foliage clusters
export function tree(stage, x, z, { height = 6, spread = 2.6, seed = 1, leafColor = 0xffffff } = {}) {
  const g = new THREE.Group(); g.position.set(x, 0, z);
  const r = rng(seed);
  const bark = new THREE.MeshStandardMaterial({ color: 0x5b4632, roughness: 0.95 });
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.22, height * 0.55, 10), bark);
  trunk.position.y = height * 0.275; trunk.castShadow = true; g.add(trunk);
  const leafTex = stage.tex('leaves.png', 1, true);
  const leafMat = new THREE.MeshStandardMaterial({ map: leafTex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.75, color: leafColor });
  const card = new THREE.PlaneGeometry(0.9, 0.9);
  const N = 260;
  const im = new THREE.InstancedMesh(card, leafMat, N);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), s = new THREE.Vector3(), p = new THREE.Vector3();
  const blobs = Array.from({ length: 6 }, () => [(r() - 0.5) * spread, height * (0.6 + r() * 0.35), (r() - 0.5) * spread, spread * (0.35 + r() * 0.2)]);
  for (const [bx, by, bz] of blobs) {
    const br = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.07, Math.hypot(bx, by - height * 0.5, bz), 6), bark);
    br.position.set(bx / 2, (by + height * 0.5) / 2, bz / 2); br.lookAt(bx, by, bz); br.rotateX(Math.PI / 2); br.castShadow = true; g.add(br);
  }
  for (let i = 0; i < N; i++) {
    const [bx, by, bz, br] = blobs[i % blobs.length];
    const v = new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).normalize().multiplyScalar(br * Math.cbrt(r()));
    p.set(bx + v.x, by + v.y * 0.8, bz + v.z);
    e.set(r() * 6.28, r() * 6.28, r() * 6.28); q.setFromEuler(e);
    const k = 0.7 + r() * 0.6; s.set(k, k, k);
    m.compose(p, q, s); im.setMatrixAt(i, m);
  }
  im.castShadow = true; im.receiveShadow = true; g.add(im);
  stage.scene.add(g);
  return g;
}

// Date palm: ringed trunk + arching fronds (alpha-tested leaf strips)
export function palm(stage, x, z, { height = 6, seed = 2, lean = 0.15 } = {}) {
  const g = new THREE.Group(); g.position.set(x, 0, z);
  const r = rng(seed);
  const pts = []; for (let i = 0; i <= 12; i++) { const u = i / 12; pts.push(new THREE.Vector3(Math.sin(u * 1.2) * lean * height * u, u * height, 0)); }
  const path = new THREE.CatmullRomCurve3(pts);
  const trunkG = new THREE.TubeGeometry(path, 48, 0.2, 10, false);
  const pos = trunkG.attributes.position;
  for (let i = 0; i < pos.count; i++) { // ring bumps
    const y = pos.getY(i); const k = 1 + 0.08 * Math.max(0, Math.sin(y * 9));
    const c = path.getPointAt(clamp(y / height));
    pos.setX(i, c.x + (pos.getX(i) - c.x) * k); pos.setZ(i, c.z + (pos.getZ(i) - c.z) * k);
  }
  trunkG.computeVertexNormals();
  const trunk = new THREE.Mesh(trunkG, new THREE.MeshStandardMaterial({ color: 0x7a6248, roughness: 0.95 }));
  trunk.castShadow = true; g.add(trunk);
  const top = path.getPointAt(1);
  const fm = new THREE.MeshStandardMaterial({ map: stage.tex('frond.png', 1, true), alphaTest: 0.45, side: THREE.DoubleSide, roughness: 0.7 });
  for (let k = 0; k < 14; k++) {
    const len = 2.6 + r() * 0.8;
    const fg = new THREE.PlaneGeometry(len, 0.75, 16, 1); fg.translate(len / 2, 0, 0);
    const fp = fg.attributes.position;
    const droop = 0.25 + r() * 0.35;
    for (let i = 0; i < fp.count; i++) { const u = fp.getX(i) / len; fp.setY(i, fp.getY(i) * 0.6 - droop * len * u * u + 0.4 * u); fp.setZ(i, fp.getY(i) * 0.0 + (fp.getY(i) > 0 ? 0.08 : -0.08) * Math.sin(u * 3)); }
    fg.computeVertexNormals();
    const f = new THREE.Mesh(fg, fm);
    f.position.copy(top); f.rotation.y = (k / 14) * Math.PI * 2 + r() * 0.3; f.rotation.z = (r() - 0.3) * 0.4;
    f.castShadow = true; g.add(f);
  }
  stage.scene.add(g);
  return g;
}

// Soft cumulus cloud billboards far in the sky
export function clouds(stage, { count = 14, seed = 5, distance = 700, height = [160, 320] } = {}) {
  const r = rng(seed);
  const tex = stage.tex('cloud.png', 1, true);
  const group = new THREE.Group();
  for (let i = 0; i < count; i++) {
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, fog: false, opacity: 0.95 });
    const sp = new THREE.Sprite(mat);
    const ang = (r() - 0.5) * 2.2;
    sp.position.set(Math.sin(ang) * distance, lerp(height[0], height[1], r()), -Math.cos(ang) * distance);
    const s = 220 + r() * 260; sp.scale.set(s, s * 0.5, 1);
    group.add(sp);
  }
  stage.scene.add(group);
  stage.onUpdate(t => { group.rotation.y = t * 0.002; });
  return group;
}

// Pipe along a 3D polyline with rounded bends; transparent PVC look
export function pipe(stage, points, radius, mat, { tension = 0.05, segments = 200 } = {}) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)), false, 'catmullrom', tension);
  const m = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, radius, 24, false), mat);
  m.castShadow = true; m.receiveShadow = true; stage.scene.add(m);
  m.userData.curve = curve;
  return m;
}

// ---------------------------------------------------------------- camera paths
// shots: array of shots; each shot = [{t, pos:[x,y,z], look:[x,y,z], fov}, ...] (>= 2 keys).
// Within a shot the camera glides along a smooth spline with eased timing; between shots it
// cuts.  A subtle hand-held drift keeps it alive.  A flat key list is treated as one shot.
export function cameraPath(stage, shots, { drift = 0.02 } = {}) {
  if (!Array.isArray(shots[0])) shots = [shots];
  const cam = stage.camera;
  const rigs = shots.map(keys => ({
    keys, t0: keys[0].t, t1: keys[keys.length - 1].t,
    P: new THREE.CatmullRomCurve3(keys.map(k => new THREE.Vector3(...k.pos)), false, 'centripetal'),
    L: new THREE.CatmullRomCurve3(keys.map(k => new THREE.Vector3(...k.look)), false, 'centripetal'),
  }));
  stage.onUpdate(t => {
    let rig = rigs[0];
    for (const r of rigs) if (t >= r.t0) rig = r;
    const keys = rig.keys, n = keys.length - 1;
    let i = 0; while (i < n - 1 && t > keys[i + 1].t) i++;
    const a = keys[i], b = keys[i + 1];
    const u = ease(t, a.t, b.t);
    const g = (i + u) / n;
    cam.position.copy(rig.P.getPoint(g));
    const look = rig.L.getPoint(g);
    cam.position.x += Math.sin(t * 0.7) * drift; cam.position.y += Math.sin(t * 0.53 + 1) * drift * 0.7;
    cam.lookAt(look);
    cam.fov = lerp(a.fov ?? 38, b.fov ?? 38, u); cam.updateProjectionMatrix();
    stage.focusTarget = look;
  });
}

// ---------------------------------------------------------------- captions (DOM overlay, native Arabic shaping)
export function captions(stage, words, { y = 0.27, size = 92 } = {}) {
  const el = document.getElementById('caption');
  el.style.top = (y * 100) + '%'; el.style.fontSize = (size * stage.W / 1080) + 'px';
  stage.onUpdate(t => {
    const w = words.find(w => t >= w.start && t < w.end);
    if (!w) { el.style.opacity = 0; return; }
    const k = clamp((t - w.start) / 0.16);
    const s = 0.55 + 0.45 * backOut(k);
    el.textContent = w.text; el.style.opacity = Math.min(1, k * 1.6);
    el.style.transform = `translate(-50%, -50%) scale(${s})`;
  });
}

export { mergeGeometries };
