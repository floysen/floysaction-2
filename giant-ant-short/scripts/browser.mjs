import { chromium } from 'playwright';

// Headless Chromium with software WebGL (SwiftShader) => identical output on any machine, no GPU needed.
export async function openPage(url) {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || undefined,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-vsync', '--force-device-scale-factor=1'],
  });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(url);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 180000 }).catch(() => {});
  await page.evaluate(() => document.fonts.ready);
  if (errors.length) throw new Error('Page errors:\n' + errors.join('\n'));
  return { browser, page, errors };
}
