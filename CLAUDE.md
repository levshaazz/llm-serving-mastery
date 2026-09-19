# LLM Serving Mastery — repo map

Course site (Astro) + offline lecture decks + Colab seminars. Sister course and template origin:
levshaazz/deep-learning-for-search-summer-2026 (same deck engine, same mascot bible).

## Lecture authoring contract (mandatory)
Read `narrative/LECTURE_STANDARD.md` before authoring or revising any lecture. In short:
- Start from a narrative beat sheet; a full lecture targets 80–100 slides unless the owner explicitly
  sets another size. Depth, worked examples, and evidence are part of the deliverable—not optional polish.
- Use the canonical deck shell and native slide components already demonstrated by Lecture 0. Do not
  create lecture-specific layout CSS or ad-hoc replacements for native components. A genuinely missing
  pattern must become a reusable, documented template component with a fixture and a gate.
- Generate narrative/mascot artwork with the image-generation workflow and the locked mascot bible.
- Treat every discovered layout failure as a missing guardrail: first preserve a minimal reproduction,
  then fix the layout, then add or extend an automated check so the same defect cannot silently return.
- `npm run check` is only the mechanical floor. The author must render and inspect every slide at the
  target viewport in light and dark themes and verify every interactive state.

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
- `judge/` — the leaderboard infrastructure (see judge/README.md): run_submission.py measures one
  submission, score.py applies the rules, snapshot.py freezes tags at Thursday 23:59,
  thresholds/round-NN.json are the published bars; judge/reference/ keeps the reference run they came from. The scoring rules exist in FOUR places — score.py,
  data/course.json, the deck (slides 29–29c, 32) and the site — change them together.
  GuideLLM (0.7.x) and lm-eval are pinned in judge/requirements.txt; their report schemas move between
  versions, so a version bump means re-reading a real report (parse_guidellm).
- `submission-template/` — the reference submission (round-1 bars were measured with it) and the
  students' starting point. uv.lock is resolved for linux x86_64 only.
- `.env` lives in the PARENT directory (outside the repo), never commit it.

## Language
EN only. Keep every deck string in `<span lang="en">` and every site string as `{ en: … }` —
that is the RU migration path; don't write bare strings.

## Verify
`npm run check` = assemble decks + the deck gate (scripts/check-deck.mjs: text ≥ 18 px, display formulas
≥ 36 px, inline ≥ 22 px at 1920×1080, auto-fit ≥ 0.75, pre-flight clean, no console errors, agenda
anchors land on dividers, no horizontal clipping) + judge/test_score.py + scripts/sync_bars.py --check
(slide 29b must show judge/thresholds/round-01.json). Then `npm run build` and LOOK at every slide.
The gate is the floor, not the bar: a slide can pass it and still be bad.
GPU work (vLLM, the judge, notebooks) runs on Colab through the colab CLI (see ../SKILL.md).
