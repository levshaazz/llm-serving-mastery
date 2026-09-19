#!/usr/bin/env node
/* Render a deck at projector resolution for human QA.
   Usage: node scripts/render-deck.mjs Lectures/02-foo.html /tmp/render [--all-steps]
   Every slide is captured in light and dark themes; --all-steps also captures
   every intermediate state of stepped slides. The deck gate is numeric; these
   images are the complementary visual-review artifact. */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [deckArg, outArg, ...flags] = process.argv.slice(2);
if (!deckArg || !outArg) {
  console.error('usage: render-deck.mjs <deck.html> <output-dir> [--all-steps]');
  process.exit(2);
}
const allSteps = flags.includes('--all-steps');
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve(deckArg)).href);
await page.waitForTimeout(1200);
const slides = await page.$$eval('.slide', (els) => els.map((el) => Number(el.dataset.maxStep || 0)));

for (const theme of ['light', 'dark']) {
  await page.evaluate((nextTheme) => {
    document.documentElement.setAttribute('data-theme', nextTheme);
    document.dispatchEvent(new CustomEvent('lecture:themechanged'));
  }, theme);
  await page.waitForTimeout(150);
  for (let index = 0; index < slides.length; index += 1) {
    const max = slides[index];
    const states = allSteps && max ? Array.from({ length: max + 1 }, (_, i) => i) : [max];
    for (const step of states) {
      await page.evaluate((hash) => { location.hash = hash; }, `#/${index + 1}/${step}`);
      await page.waitForTimeout(120);
      const nn = String(index + 1).padStart(3, '0');
      const ss = String(step).padStart(2, '0');
      await page.screenshot({ path: `${out}/${theme}-${nn}-s${ss}.png` });
    }
  }
}
await browser.close();
console.log(`rendered ${slides.length} slides (${allSteps ? 'all states' : 'final states'}) × 2 themes → ${out}`);
