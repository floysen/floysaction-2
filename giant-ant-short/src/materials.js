import * as THREE from 'three';

// One shared palette so every shot uses identical materials.
const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, metalness: 0, ...o });

export const M = {
  // Ant: warm rust chitin pops against the cool night palette.
  antShell: std(0x9a3520, { roughness: 0.38, metalness: 0.08, flatShading: true }),
  antDark: std(0x5a1d12, { roughness: 0.45, metalness: 0.05, flatShading: true }),
  antEye: std(0x0c0c10, { roughness: 0.12, metalness: 0.3 }),
  antXray: new THREE.MeshStandardMaterial({
    color: 0xffb08a, emissive: 0x401408, roughness: 0.4, transparent: true, opacity: 0.2,
    depthWrite: false, flatShading: true,
  }),
  crack: new THREE.MeshBasicMaterial({ color: 0xffe1a8 }),
  trachea: new THREE.MeshStandardMaterial({ color: 0x67e8ff, emissive: 0x1aa6c8, emissiveIntensity: 1.1, roughness: 0.5 }),
  air: new THREE.MeshBasicMaterial({ color: 0xbff4ff, transparent: true, opacity: 1 }),
  core: new THREE.MeshBasicMaterial({ color: 0xff3b2f, transparent: true, opacity: 0.0, depthWrite: false }),
  chip: std(0x7a2a18, { roughness: 0.5, flatShading: true }),

  // Human ("you") - same outfit in every shot.
  hoodie: std(0xe0a83a, { roughness: 0.85 }),
  pants: std(0x2c3650, { roughness: 0.9 }),
  skin: std(0xe2b48c, { roughness: 0.7 }),
  hair: std(0x2a1c14, { roughness: 0.9 }),
  shoe: std(0xeeeeea, { roughness: 0.6 }),
  eye: std(0x15151a, { roughness: 0.3 }),

  // Street
  asphalt: std(0x2b2f37, { roughness: 0.42 }),
  sidewalk: std(0x6f737b, { roughness: 0.75 }),
  curb: std(0x9a9ea6, { roughness: 0.7 }),
  laneLine: std(0xd8d2b8, { roughness: 0.6 }),
  brick: std(0x6e4636, { roughness: 0.85 }),
  brick2: std(0x4d5a6b, { roughness: 0.85 }),
  brick3: std(0x5e5048, { roughness: 0.85 }),
  trim: std(0xcfc6b6, { roughness: 0.6 }),
  door: std(0x34577a, { roughness: 0.5 }),
  step: std(0xa39e94, { roughness: 0.8 }),
  glass: new THREE.MeshStandardMaterial({ color: 0x9fc4e0, roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.12, depthWrite: false }),
  litWindow: new THREE.MeshBasicMaterial({ color: 0xffc77a }),
  darkWindow: std(0x1a2230, { roughness: 0.2, metalness: 0.3 }),
  lampPost: std(0x2a2e35, { roughness: 0.5, metalness: 0.5 }),
  lampBulb: new THREE.MeshBasicMaterial({ color: 0xffd9a0 }),
  rain: new THREE.MeshBasicMaterial({ color: 0xa8c8ff, transparent: true, opacity: 0.32, depthWrite: false }),
  splash: new THREE.MeshBasicMaterial({ color: 0xcfe3ff, transparent: true, opacity: 0.6, depthWrite: false, side: THREE.DoubleSide }),

  // Car
  carPaint: std(0x2a9aa8, { roughness: 0.28, metalness: 0.35 }),
  carDark: std(0x15181d, { roughness: 0.6 }),
  carGlass: std(0x0f1a26, { roughness: 0.08, metalness: 0.6 }),
  carChrome: std(0xd8dde3, { roughness: 0.2, metalness: 0.9 }),
  tire: std(0x17181b, { roughness: 0.9 }),
  headlight: new THREE.MeshBasicMaterial({ color: 0xfff1cf }),
  taillight: new THREE.MeshBasicMaterial({ color: 0xff3d3d }),

  // Interior
  wood: std(0x7a5236, { roughness: 0.7 }),
  wall: std(0x5b5f6e, { roughness: 0.95 }),
  curtain: std(0x7a3346, { roughness: 0.95, side: THREE.DoubleSide }),
  lampShade: new THREE.MeshStandardMaterial({ color: 0xffe2b0, emissive: 0xffb860, emissiveIntensity: 0.9 }),

  // Lab
  labWall: std(0x20333f, { roughness: 0.95 }),
  weight: std(0xff8a2a, { roughness: 0.45, emissive: 0x5a2400, emissiveIntensity: 0.6 }),
  strength: std(0x45e08a, { roughness: 0.45, emissive: 0x0b5a2c, emissiveIntensity: 0.8 }),
  coin: std(0xe0b860, { roughness: 0.35, metalness: 0.35 }),
  blob: new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false }),
};
