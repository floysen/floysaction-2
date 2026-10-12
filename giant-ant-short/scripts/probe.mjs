// Debug helper: print world positions of key rig points at given times.
import { startServer } from './server.mjs';
import { openPage } from './browser.mjs';
const PORT = 5900 + Math.floor(Math.random() * 90);
const server = await startServer(PORT);
const { browser, page } = await openPage(`http://localhost:${PORT}/index.html`);
const times = process.argv.slice(2).map(Number);
const out = await page.evaluate((times) => times.map((t) => {
  window.renderFrame(Math.round(t * 30));
  const w = window.__world, h = w.hero;
  const wp = (o) => { const v = o.getWorldPosition(o.position.clone()); return v.toArray().map((n) => +n.toFixed(2)); };
  const leg = h.legs[3];
  const box = (o) => { const b = new o.position.constructor(); return null; };
  return { t, root: h.root.position.toArray().map((n) => +n.toFixed(2)), head: wp(h.head.children[0]),
    rfKnee: wp(leg.knee), rfFoot: h.root.localToWorld(leg.foot.clone()).toArray().map((n) => +n.toFixed(2)),
    handle: wp(w.street.handle), gaster: wp(h.gaster), cam: w.camera.position.toArray().map((n) => +n.toFixed(2)) };
}), times);
console.log(out.map((o) => JSON.stringify(o)).join('\n'));
await browser.close(); server.close();
