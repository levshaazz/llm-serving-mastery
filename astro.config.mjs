// @ts-check
import { defineConfig } from 'astro/config';

// GitHub Pages project site: https://levshaazz.github.io/llm-serving-mastery/
// `site` = origin, `base` = repo subpath. Build output → docs/ (uploaded by the Pages workflow).
export default defineConfig({
  site: 'https://levshaazz.github.io',
  base: '/llm-serving-mastery',
  trailingSlash: 'ignore',
  outDir: './docs',
  build: { format: 'directory' },
  // i18n routing is explicit via the [lang] segment + getStaticPaths (src/i18n/locales.js).
});
