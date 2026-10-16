// Frame renderer: serves web/, drives a headless Chromium-based browser (Edge/Chrome on
// Windows, GPU accelerated) and pipes JPEG frames into FFmpeg in resumable chunks.
//
//   node tools/render.mjs --scene demo --fps 30 --scale 1 --out build/chunks_full [--frames 0-89] [--stills 1.0,3.0]
import http from 'http';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright-core';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const WEB = path.join(ROOT, 'web');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const scene = arg('scene', 'toilet'), fps = +arg('fps', 30), scale = +arg('scale', 1), quality = arg('quality', 'full');
const out = path.resolve(ROOT, arg('out', 'build/chunks_' + quality));
const chunk = +arg('chunk', 90);
const FFMPEG = process.env.FFMPEG || 'ffmpeg';

function findBrowser() {
  if (process.env.BROWSER && fs.existsSync(process.env.BROWSER)) return process.env.BROWSER;
  const c = [
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', '/usr/bin/chromium', '/usr/bin/google-chrome',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  const f = c.find(p => fs.existsSync(p));
  if (!f) throw new Error('No Chromium-based browser found (Edge or Chrome). Set BROWSER=/path/to/browser.exe');
  return f;
}

const types = { '.js': 'text/javascript', '.html': 'text/html', '.jpg': 'image/jpeg', '.png': 'image/png', '.ttf': 'font/ttf', '.json': 'application/json', '.mp3': 'audio/mpeg' };
const server = http.createServer((q, s) => {
  const u = decodeURIComponent(q.url.split('?')[0]);
  const p = (u.startsWith('/data/') || u.startsWith('/node_modules/')) ? path.join(ROOT, u) : path.join(WEB, u === '/' ? 'index.html' : u);
  fs.readFile(p, (e, d) => { if (e) { s.writeHead(404); s.end(); return; } s.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); s.end(d); });
}).listen(0);
const port = server.address().port;

const gpuArgs = process.env.NO_GPU ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
  : ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', ...(process.platform === 'win32' ? ['--use-angle=d3d11'] : [])];
const browser = await chromium.launch({ executablePath: findBrowser(), headless: true, args: ['--hide-scrollbars', '--autoplay-policy=no-user-gesture-required', ...gpuArgs] });
const W = Math.round(1080 * scale), H = Math.round(1920 * scale);
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('[page error]', e.message));
page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
await page.goto(`http://localhost:${port}/?scene=${scene}&scale=${scale}&quality=${quality}`);
await page.waitForFunction('window.ready === true', null, { timeout: 180000 });
const renderer = await page.evaluate(() => { const gl = document.createElement('canvas').getContext('webgl2'); const d = gl.getExtension('WEBGL_debug_renderer_info'); return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'; });
console.log(`[render] GPU: ${renderer}`);
const duration = await page.evaluate('window.duration');
const total = Math.round(duration * fps);

async function shot(t) {
  await page.evaluate(tt => window.renderAt(tt), t);
  return page.screenshot({ type: 'jpeg', quality: 95, clip: { x: 0, y: 0, width: W, height: H } });
}

const stills = arg('stills', null);
if (stills) {
  fs.mkdirSync(out, { recursive: true });
  for (const s of stills.split(',')) {
    const t0 = Date.now(); const buf = await shot(+s);
    fs.writeFileSync(path.join(out, `still_${(+s).toFixed(2)}.jpg`), buf);
    console.log(`[still] t=${s} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
} else {
  fs.mkdirSync(out, { recursive: true });
  const [f0, f1] = (arg('frames', `0-${total - 1}`)).split('-').map(Number);
  const t0 = Date.now(); let done = 0;
  for (let c = Math.floor(f0 / chunk); c * chunk <= f1; c++) {
    const file = path.join(out, `chunk_${String(c).padStart(4, '0')}.mp4`);
    if (fs.existsSync(file)) continue;
    const tmp = file + '.part.mp4';
    const ff = spawn(FFMPEG, ['-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-r', String(fps), '-i', '-',
      '-c:v', 'libx264', '-preset', 'fast', '-crf', '12', '-pix_fmt', 'yuv420p', tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
    const a = c * chunk, b = Math.min(total - 1, (c + 1) * chunk - 1);
    for (let f = a; f <= b; f++) {
      const buf = await shot(f / fps);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      done++;
    }
    ff.stdin.end();
    await new Promise((res, rej) => ff.on('close', code => (code === 0 ? res() : rej(new Error('ffmpeg failed')))));
    fs.renameSync(tmp, file);
    const el = (Date.now() - t0) / 1000;
    console.log(`[render] chunk ${c + 1}/${Math.ceil(total / chunk)}  ${(done / el).toFixed(2)} frames/s  ETA ${((total - (b + 1)) / (done / el) / 60).toFixed(1)} min`);
  }
}
await browser.close();
server.close();
