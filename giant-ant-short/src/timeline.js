// Master timeline. Every animated value in the project is a pure function of time t (seconds),
// so seeking to any frame always produces the identical image.
export const FPS = 30;
export const DURATION = 31.0;
export const TOTAL_FRAMES = Math.round(FPS * DURATION); // 930
export const WIDTH = 1080;
export const HEIGHT = 1920;

// Estimated narration timing (~2.7 words/s, natural Shorts pace). Used for shot sync + the VO guide.
export const NARRATION = [
  { start: 0.0, end: 3.2, text: 'You hear it before you see it. Clicking.' },
  { start: 3.2, end: 5.3, text: 'Hundreds of legs on concrete.' },
  { start: 5.3, end: 10.8, text: 'Outside your window, an ant as tall as you grabs a car door and pulls…' },
  { start: 10.8, end: 12.4, text: 'and its leg snaps.' },
  { start: 12.4, end: 18.6, text: 'Grow an ant five hundred times taller, and its body becomes a hundred and twenty-five million times heavier.' },
  { start: 18.6, end: 21.8, text: 'Its muscles? Only a quarter-million times stronger.' },
  { start: 21.8, end: 23.9, text: 'Its shell starts to crack.' },
  { start: 23.9, end: 26.6, text: "Its body can't pull in enough air." },
  { start: 26.6, end: 30.4, text: 'The invasion collapses right on your doorstep.' },
];

export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, u) => a + (b - a) * u;
export const ramp = (t, a, b) => clamp((t - a) / (b - a));
export const smooth = (u) => u * u * (3 - 2 * u);
export const easeInOut = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
export const easeOut = (u) => 1 - Math.pow(1 - u, 3);
export const easeOutQuad = (u) => 1 - (1 - u) * (1 - u);
export const easeIn = (u) => u * u * u;
export const lerp3 = (a, b, u) => [lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
// Window helper: rises over [a,a+f], holds, falls over [b-f,b].
export const pulse = (t, a, b, f = 0.25) => Math.min(ramp(t, a, a + f), 1 - ramp(t, b - f, b));

// Seeded PRNG (mulberry32) - only used at build time so geometry is identical every run.
export function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
