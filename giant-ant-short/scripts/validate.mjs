// Runs the in-page scene-graph / timeline / camera validation and exits non-zero on errors.
import { startServer } from './server.mjs';
import { openPage } from './browser.mjs';
const PORT = 5700 + Math.floor(Math.random() * 200);
const server = await startServer(PORT);
const { browser, page } = await openPage(`http://localhost:${PORT}/index.html`);
const report = await page.evaluate(() => window.validateScene());
await browser.close();
server.close();
console.log(JSON.stringify(report, null, 2));
process.exit(report.ok ? 0 : 1);
