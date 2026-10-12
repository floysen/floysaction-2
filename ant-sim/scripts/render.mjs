// Deterministic frame capture with headless Chromium (Playwright + SwiftShader WebGL).
// Usage: node scripts/render.mjs [--workers 3] [--from 0] [--to 1800] [--step 1] [--list 0,45,90] [--out frames] [--notext]
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { serve } from './server.mjs';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const workers = +arg('workers', 3), from = +arg('from', 0), to = +arg('to', 1800), step = +arg('step', 1);
const out = path.resolve(arg('out', 'frames'));
const port = 5173 + Math.floor(Math.random() * 1000);
fs.mkdirSync(out, { recursive: true });
const server = await serve(port);
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });

const list = arg('list', '');
const frames = [];
if (list) { for (const f of list.split(',').map(Number)) if (!fs.existsSync(path.join(out, `f_${String(f).padStart(5, '0')}.jpg`))) frames.push(f); }
else for (let f = from; f < to; f += step) if (!fs.existsSync(path.join(out, `f_${String(f).padStart(5, '0')}.jpg`))) frames.push(f);
console.log(`Rendering ${frames.length} frames with ${workers} workers -> ${out}`);
let done = 0; const t0 = Date.now();

async function worker(id) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error(`[w${id}] page error:`, e.message));
  await page.goto(`http://localhost:${port}/index.html?render=1${process.argv.includes('--notext') ? '&text=0' : ''}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 120000 });
  for (let i = id; i < frames.length; i += workers) {
    const f = frames[i];
    await page.evaluate((n) => window.renderFrame(n), f);
    await page.screenshot({ path: path.join(out, `f_${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 93 });
    done++;
    if (done % 30 === 0) { const s = (Date.now() - t0) / 1000; console.log(`${done}/${frames.length}  ${(s / done).toFixed(2)} s/frame  eta ${Math.round((frames.length - done) * s / done)} s`); }
  }
  await page.close();
}
await Promise.all(Array.from({ length: workers }, (_, i) => worker(i)));
await browser.close(); server.close();
console.log(`Done in ${Math.round((Date.now() - t0) / 1000)} s`);
