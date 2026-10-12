// Deterministic frame renderer: seeks the master timeline to each exact frame, captures it at 1080x1920,
// then encodes H.264 / yuv420p / 30 fps with FFmpeg.
//   node scripts/render.mjs                  -> full render to final-animation.mp4
//   node scripts/render.mjs --frames 0,300   -> just those frames into out/stills (for inspection)
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { startServer } from './server.mjs';
import { openPage } from './browser.mjs';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const WORKERS = Number(arg('workers', 3));
const PORT = 5180 + Math.floor(Math.random() * 500);
const server = await startServer(PORT);
const url = `http://localhost:${PORT}/index.html`;

const probe = await openPage(url);
const { TOTAL_FRAMES, FPS } = await probe.page.evaluate(() => window.TIMING);
await probe.browser.close();

// --range a-b re-renders part of the full frame sequence in place (then re-encodes).
const range = arg('range')?.split('-').map(Number);
const list = arg('frames') ? arg('frames').split(',').map(Number)
  : range ? Array.from({ length: range[1] - range[0] + 1 }, (_, i) => range[0] + i) : [...Array(TOTAL_FRAMES).keys()];
const outDir = arg('frames') ? 'out/stills' : 'out/frames';
fs.mkdirSync(outDir, { recursive: true });

const t0 = Date.now();
let done = 0;
await Promise.all(Array.from({ length: Math.min(WORKERS, list.length) }, async (_, w) => {
  const { browser, page } = await openPage(url);
  for (let i = w; i < list.length; i += WORKERS) {
    const f = list[i];
    await page.evaluate((fr) => window.renderFrame(fr), f);
    await page.screenshot({ path: path.join(outDir, `frame_${String(f).padStart(5, '0')}.png`), type: 'png' });
    if (++done % 30 === 0) console.log(`${done}/${list.length} frames  (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  await browser.close();
}));
server.close();
console.log(`Rendered ${list.length} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s -> ${outDir}`);

if (!arg('frames')) {
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', `${outDir}/frame_%05d.png`,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-movflags', '+faststart', 'final-animation.mp4'], { stdio: 'inherit' });
  console.log('Wrote final-animation.mp4');
}
