// locales.js — locale list, fallback chain, resolver, base-aware paths.
// The course ships in EN only. It is built to take RU later without touching the pages:
//   1. add 'ru' to LOCALES;  2. add `ru:` next to `en:` in data/course.json and src/i18n/ui.js.
// Missing RU strings fall back to EN (see FALLBACK), so a partial translation never breaks a page.

export const LOCALES = ['en'];
export const DEFAULT_LOCALE = 'en';

export const LOCALE_LABEL = { en: 'EN', ru: 'RU' };
export const LOCALE_NAME = { en: 'English', ru: 'Русский' };
export const HTML_LANG = { en: 'en', ru: 'ru' };

// Per-locale fallback order. The resolver walks this until it finds a string.
const FALLBACK = {
  en: ['en'],
  ru: ['ru', 'en'],
};

/**
 * Resolve an i18n value for a locale.
 * @param {string|object} value  a plain string (locale-agnostic) or { en, ru }
 * @param {string} lang          target locale
 * @returns {string}
 */
export function t(value, lang) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  for (const l of FALLBACK[lang] || FALLBACK[DEFAULT_LOCALE]) {
    if (value[l] != null && value[l] !== '') return value[l];
  }
  return value.en ?? '';
}

/** True when `value` actually has a string for `lang` (no fallback used). */
export function hasTranslation(value, lang) {
  if (value == null) return false;
  if (typeof value === 'string') return true;
  return value[lang] != null && value[lang] !== '';
}

// ── base-aware path helpers (project Pages live under /<repo>/) ──────────────
const BASE = import.meta.env.BASE_URL.replace(/\/$/, ''); // e.g. "/llm-serving-mastery"

/** Prefix a root-absolute path with the deploy base. withBase('/x') -> '/<base>/x'. */
export function withBase(path = '/') {
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${BASE}${p}`;
}

/** Localized page path. localizedPath('ru','syllabus') -> '/<base>/ru/syllabus'. */
export function localizedPath(lang, page = '') {
  const clean = page.replace(/^\/|\/$/g, '');
  return withBase(`/${lang}${clean ? '/' + clean : '/'}`);
}
