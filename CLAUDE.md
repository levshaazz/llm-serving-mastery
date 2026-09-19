# LLM Serving Mastery — repo map

Course site (Astro) + offline lecture decks + Colab seminars. Sister course and template origin:
levshaazz/deep-learning-for-search-summer-2026 (same deck engine, same mascot bible).

## Where things live
- `data/course.json` — THE source of course facts: topics (no weeks — topics only, by owner's decision),
  assessment (exam 50 / leaderboard 40 / defense 10), leaderboard rules, reading. Pages read it; the
  decks hand-type the same facts — when a rule changes, `git grep` the decks too.
- `Lectures/<slug>/parts/*.html` — editable deck source. `Lectures/<slug>.html` is BUILD OUTPUT
  (`node scripts/assemble-deck.mjs build`), gitignored. Never edit it.
  Agenda anchors `#/N` are 1-based slide POSITIONS — inserting a slide shifts every anchor after it.
- `Lectures/js/tools.js`, `preflight.js` — the engine, patched for single-language decks:
  `<html data-langs="en">` forces EN, hides the language toggle and silences the missing-pair check.
- `_research/gen_images.py` + `_research/mascots.py` — illustrations. Serega = head cook: apron,
  green tübetey, NEVER a chef's toque. Output → `_research/masters/` (gitignored), then
  `python3 scripts/optimize_images.py` → `Lectures/assets/img/**.webp`. Never optimize in place.
- `seminars/00-live-demo-pipeline-vs-vllm.ipynb` — Lecture 0 live demo (Colab T4).
- `.env` lives in the PARENT directory (outside the repo), never commit it.

## Language
EN only. Keep every deck string in `<span lang="en">` and every site string as `{ en: … }` —
that is the RU migration path; don't write bare strings.

## Verify
`npm run build` (4 pages) · `node scripts/assemble-deck.mjs check` · open the deck and check the
pre-flight badge (bottom-right) shows 0 errors/warnings · LOOK at every slide (screenshots) before calling it done.
