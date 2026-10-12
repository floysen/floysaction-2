// Time a few representative frames: node scripts/bench.mjs ["&query=params"]
import { chromium } from 'playwright';
import { serve } from './server.mjs';
const port = 6100 + Math.floor(Math.random() * 500);
const server = await serve(port);
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
p.on('pageerror', (e) => console.log(e.message));
await p.goto(`http://localhost:${port}/index.html?render=1${process.argv[2] || ''}`);
await p.waitForFunction(() => window.__ready);
for (const f of [45, 300, 840, 1440]) {
  await p.evaluate((n) => window.renderFrame(n), f);
  const t = Date.now();
  for (let i = 0; i < 2; i++) { await p.evaluate((n) => window.renderFrame(n), f + i); await p.screenshot({ type: 'jpeg' }); }
  console.log(`frame ${f}: ${((Date.now() - t) / 2000).toFixed(2)} s`);
}
await b.close(); server.close();
