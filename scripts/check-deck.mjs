#!/usr/bin/env node
/* =========================================================
   check-deck.mjs — the deck gate. A slide ships only if it is readable from the back of the room.

     node scripts/check-deck.mjs [Lectures/00-introduction.html ...]   (default: every assembled deck)
     node scripts/check-deck.mjs --report                               (print the smallest sizes per slide)

   Renders each slide at 1920×1080 (the projector), at its LAST step, and measures what the
   audience actually sees — computed font-size × the on-screen scale (auto-fit included):

     G1 text       every visible text element ≥ TEXT_FLOOR px          (chrome like the footer is exempt)
     G2 formulas   display KaTeX ≥ DISPLAY_MATH_FLOOR px, inline KaTeX ≥ INLINE_MATH_FLOOR px
     G3 fit        no slide auto-scaled below FIT_FLOOR
     G4 preflight  the engine's own checks report nothing
     G5 console    no console errors / failed resources
     G6 agenda     every agenda link lands on a divider slide
     G7 clipping   no code block / table cell hides content horizontally (scrollWidth > clientWidth)

   Why: lecture 0 once shipped its KV-cache formula as a 24 px display equation inside a card —
   half the size of the slide-11 formula, fine on a laptop, unreadable from row 10. Nothing flagged it:
   every existing check was about overflow, none about size.
   ========================================================= */
import { chromium } from 'playwright';
import { readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const TEXT_FLOOR = 18;   // px at 1920×1080
const DISPLAY_MATH_FLOOR = 36;  // px — a display formula is the focus of its slide
const INLINE_MATH_FLOOR = 22;   // px — inline math sits in running text
const FIT_FLOOR = 0.75;
// chrome and presenter-only elements, not content
const EXEMPT = [
  '.slide-footer', '.slide-num', '.course-tag', '.slide-notes', 'aside', '.toolbar', '.kbd-hint',
  '.progress', '.preflight', '.qr-url', '.breadcrumbs', '.slide-chrome', '.logo-mark', '[data-logo-slot]',
  '.step-controls', '.step-counter', '.eyebrow', '.meta-label', '.cameo', '.pause-controls',
  '.misc-reveal-btn', '.misc-truth', '.hidden-answer', '.devil-overlay', '.toc-sub',
];

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const report = args.includes('--report');
let decks = args.filter((a) => !a.startsWith('--'));
if (!decks.length) decks = readdirSync(join(ROOT, 'Lectures')).filter((f) => /^\d\d-.*\.html$/.test(f)).map((f) => join(ROOT, 'Lectures', f));

const browser = await chromium.launch();
let failures = 0;
for (const deck of decks) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('requestfailed', (r) => errors.push(`failed ${r.url()}`));
  await page.goto(pathToFileURL(resolve(deck)).href);
  await page.waitForTimeout(1500);
  const meta = await page.$$eval('.slide', (s) => s.map((x) => ({ steps: +(x.dataset.maxStep || 0), type: x.dataset.type, label: x.dataset.screenLabel })));
  const problems = [];
  const structuralProblems = await page.$$eval('.slide', (slides) => {
    const required = {
      title: ['.title-header', '.title-body', '.title-footer'],
      agenda: ['.agenda-grid', '.agenda-grid .toc-item', '.toc-item .toc-num', '.toc-item .toc-text', '.toc-item .toc-title', '.toc-item .toc-sub'],
      objectives: ['.obj-list'],
      divider: ['.divider-content'],
      formula: ['.formula-stage', '.formula-caption'],
      'two-col': [':is(.twocol, .def-card)'],
      quote: ['.quote-mark', 'blockquote'],
      refs: ['.ref-list'],
      final: ['.final-body'],
      table: ['.cmp-table'],
      walkthrough: ['.walk-flow'],
      archflow: ['.af-stage', '.af-canvas', '.af-panel', '.af-note[data-step="0"]', '.af-node[data-from="0"]'],
      sequence: ['.seq-stage', '.seq-canvas', '.seq-actors', '.seq-msgs', '.seq-budget'],
    };
    return slides.flatMap((slide, index) => (required[slide.dataset.type] || [])
      .filter((selector) => !slide.querySelector(selector))
      .map((selector) => `${String(index + 1).padStart(2, '0')} ${slide.dataset.screenLabel}: template structure missing ${selector}`));
  });
  problems.push(...structuralProblems);
  const deckContract = await page.$eval('.slides', (el) => ({
    min: Number(el.dataset.slideMin || 0),
    max: Number(el.dataset.slideMax || 0),
  }));
  if (deckContract.min && meta.length < deckContract.min) problems.push(`deck contract: ${meta.length} slides < declared minimum ${deckContract.min}`);
  if (deckContract.max && meta.length > deckContract.max) problems.push(`deck contract: ${meta.length} slides > declared maximum ${deckContract.max}`);
  const localLayoutSheets = await page.$$eval('link[rel="stylesheet"]', (links) => links
    .map((link) => link.getAttribute('href') || '')
    .filter((href) => /css\/(?:topic|lecture)[-_]?\d/i.test(href)));
  for (const href of localLayoutSheets) problems.push(`template contract: lecture-specific layout stylesheet is forbidden — ${href}`);
  for (let i = 1; i <= meta.length; i++) {
    const m = meta[i - 1];
    /* A stepped slide is several layouts sharing one URL. Audit every state:
       checking only the final reveal missed blank/overlapping intermediate
       states in Lecture 1's first archflow. */
    const states = m.steps ? Array.from({ length: m.steps + 1 }, (_, step) => step) : [null];
    for (const step of states) {
      await page.evaluate((h) => { location.hash = h; }, step == null ? `#/${i}` : `#/${i}/${step}`);
      await page.waitForTimeout(450);
      const r = await page.evaluate(({ EXEMPT, DISPLAY_MATH_FLOOR, INLINE_MATH_FLOOR }) => {
      const slide = document.querySelector('.slide.is-active, .slide.active, .slide[aria-hidden="false"]') ||
        [...document.querySelectorAll('.slide')].find((s) => s.getBoundingClientRect().width > 0 && getComputedStyle(s).visibility !== 'hidden' && getComputedStyle(s).display !== 'none');
      if (!slide) return { err: 'no active slide' };
      const exempt = (el) => EXEMPT.some((sel) => el.closest(sel));
      const scaleOf = (el) => { const r = el.getBoundingClientRect(); return el.offsetWidth ? r.width / el.offsetWidth : 1; };
      const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity !== 0; };
      let minText = { px: 1e9 }, minMath = { px: 1e9, floor: 1 };
      for (const el of slide.querySelectorAll('*')) {
        if (exempt(el) || !visible(el) || el.closest('.katex')) continue;
        const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
        if (!own) continue;
        const px = parseFloat(getComputedStyle(el).fontSize) * scaleOf(el);
        if (px < minText.px) minText = { px, text: el.textContent.trim().slice(0, 50) };
      }
      for (const k of slide.querySelectorAll('.katex')) {
        if (exempt(k) || !visible(k)) continue;
        const px = parseFloat(getComputedStyle(k).fontSize) * scaleOf(k);
        const display = !!k.closest('.katex-display');
        const floor = display ? DISPLAY_MATH_FLOOR : INLINE_MATH_FLOOR;
        if (px / floor < minMath.px / minMath.floor || minMath.px === 1e9) minMath = { px, floor, display, text: (k.querySelector('annotation')?.textContent || '').slice(0, 50) };
      }
      const body = slide.querySelector('.slide-body') || slide;
      const fit = scaleOf(body);
      const clipped = [...slide.querySelectorAll('pre, code, td, th, .walk-detail, .def-body')]
        .filter((el) => visible(el) && !exempt(el) && el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflowX !== 'visible')
        .map((el) => el.textContent.trim().slice(0, 40));
      return { minText, minMath, fit, clipped };
    }, { EXEMPT, DISPLAY_MATH_FLOOR, INLINE_MATH_FLOOR });
      const tag = `${String(i).padStart(2, '0')} ${m.label}${step == null ? '' : ` [step ${step}/${m.steps}]`}`;
      if (r.err) { problems.push(`${tag}: ${r.err}`); continue; }
      if (report) console.log(`${tag.padEnd(44)} text ${r.minText.px < 1e9 ? r.minText.px.toFixed(1) : '—'}  math ${r.minMath.px < 1e9 ? r.minMath.px.toFixed(1) : '—'}  fit ${r.fit.toFixed(2)}`);
      if (r.minText.px < TEXT_FLOOR) problems.push(`${tag}: text ${r.minText.px.toFixed(1)} px < ${TEXT_FLOOR} — "${r.minText.text}"`);
      if (r.minMath.px < r.minMath.floor) problems.push(`${tag}: ${r.minMath.display ? 'display' : 'inline'} formula ${r.minMath.px.toFixed(1)} px < ${r.minMath.floor} — ${r.minMath.text}`);
      for (const c of r.clipped) problems.push(`${tag}: content cut off horizontally — "${c}"`);
      if (r.fit < FIT_FLOOR) problems.push(`${tag}: auto-fit ${r.fit.toFixed(2)} < ${FIT_FLOOR} — split the slide`);
    }
  }
  // G4 preflight
  const pf = await page.evaluate(() => { try { return window.__preflight ? window.__preflight.runChecks() : []; } catch (e) { return [{ msg: String(e) }]; } });
  for (const x of pf || []) problems.push(`preflight: ${x.slide || ''} ${x.msg}`);
  // G4b theme contract — changing only data-theme is insufficient because
  // tweak preferences may leave light inline background tokens behind. Use
  // the same event as the toolbar and fail if the resolved dark palette is not dark.
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.dispatchEvent(new CustomEvent('lecture:themechanged'));
  });
  await page.waitForTimeout(100);
  const darkTokens = await page.evaluate(() => {
    const cs = getComputedStyle(document.documentElement);
    const rgb = (name) => {
      const probe = document.createElement('span');
      probe.style.color = `var(${name})`; document.body.appendChild(probe);
      const value = getComputedStyle(probe).color; probe.remove();
      return (value.match(/[\d.]+/g) || ['255','255','255']).slice(0, 3).map(Number);
    };
    const lum = ([r,g,b]) => (0.2126*r + 0.7152*g + 0.0722*b) / 255;
    return { bg: cs.getPropertyValue('--bg').trim(), bgLum: lum(rgb('--bg')), inkLum: lum(rgb('--ink')) };
  });
  if (darkTokens.bgLum > 0.25 || darkTokens.inkLum < 0.65) problems.push(`theme contract: dark palette did not resolve (bg ${darkTokens.bg}, luminance ${darkTokens.bgLum.toFixed(2)}, ink ${darkTokens.inkLum.toFixed(2)})`);
  // G5 console
  for (const e of errors) problems.push(`console: ${e}`);
  // G6 agenda anchors
  const anchors = await page.$$eval('.slide[data-type="agenda"] a[href^="#/"]', (as) => as.map((a) => a.getAttribute('href')));
  for (const h of anchors) {
    const n = +h.slice(2).split('/')[0];
    if (!meta[n - 1] || meta[n - 1].type !== 'divider') problems.push(`agenda: ${h} → ${meta[n - 1] ? meta[n - 1].label : 'nothing'} (not a divider)`);
  }
  console.log(`${problems.length ? '✗' : '✓'} ${deck.replace(ROOT + '/', '')}: ${meta.length} slides, ${problems.length} problem(s)`);
  for (const p of problems) console.log('   ' + p);
  failures += problems.length;
  await page.close();
}
await browser.close();
process.exit(failures ? 1 : 0);
