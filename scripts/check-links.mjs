import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, extname, join, relative, resolve } from 'node:path';

const root = join(import.meta.dirname, '..');
const out = join(root, 'docs');
const base = '/llm-serving-mastery';
const htmlFiles = [];
const walk = (dir) => {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path); else if (entry.name.endsWith('.html')) htmlFiles.push(path);
  }
};
walk(out);

const failures = [];
const attrs = /(?:href|src)=["']([^"']+)["']/g;
for (const html of htmlFiles) {
  const text = readFileSync(html, 'utf8');
  for (const [, raw] of text.matchAll(attrs)) {
    if (/^(?:https?:|mailto:|data:|javascript:|#)/.test(raw)) continue;
    let clean = raw.split('#')[0].split('?')[0];
    if (!clean) continue;
    try { clean = decodeURIComponent(clean); } catch {}
    let target;
    if (clean.startsWith('/')) {
      if (!clean.startsWith(base + '/') && clean !== base) {
        failures.push(`${relative(out, html)} -> root URL outside base: ${raw}`); continue;
      }
      target = join(out, clean.slice(base.length).replace(/^\//, ''));
    } else target = resolve(dirname(html), clean);
    const candidates = [target];
    if (clean.endsWith('/')) candidates.push(join(target, 'index.html'));
    else if (!extname(target)) candidates.push(join(target, 'index.html'), `${target}.html`);
    if (!candidates.some(existsSync)) failures.push(`${relative(out, html)} -> missing ${raw}`);
  }
}
if (failures.length) { console.error(failures.map((x) => `- ${x}`).join('\n')); process.exit(1); }
console.log(`[link-check] ${htmlFiles.length} HTML files passed`);
