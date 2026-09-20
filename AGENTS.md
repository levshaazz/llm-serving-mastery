# Repository instructions for Codex and other coding agents

This file is the mandatory entry point for automated work in this repository. Before changing
anything, read:

1. [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md) for the current state, owner decisions, known gaps, and the
   next safe actions;
2. [`COURSE_GOVERNANCE.md`](COURSE_GOVERNANCE.md) for the canonical-source order;
3. [`narrative/LECTURE_STANDARD.md`](narrative/LECTURE_STANDARD.md) before authoring or revising a
   lecture;
4. [`judge/OPERATIONS.md`](judge/OPERATIONS.md) before touching calibration, grading, or leaderboard
   publication.

`CLAUDE.md` is a detailed repository map and remains useful operational context. If documentation
disagrees, the canonical-source order in `COURSE_GOVERNANCE.md` wins; do not silently choose one
version.

## Owner decisions that must be preserved

- The old `LLM_Serving_Mastery_Syllabus.docx` is archived history, not a course contract.
- The curriculum keeps all 15 topics. Do not shorten it to fit contact hours; mark overflow as guided
  self-study inside the relevant topic.
- Practical multi-GPU and Kubernetes work remains promised for the later topics where it belongs.
- The leaderboard uses the enhanced automated judge design. A provisional or legacy calibration must
  never be presented as grading-ready.
- A full lecture targets 80–100 substantive slides, concrete production examples, worked numbers, and
  interactive diagrams. Slide count alone is not evidence of depth.
- Lecture 0 is the executable visual template. Reuse the shared shell and components; do not invent a
  lecture-specific visual system.
- Use the repository image-generation workflow and locked mascot bible for narrative art. Do not
  replace mascot artwork with improvised CSS drawings or unrelated stock imagery.
- Every newly discovered layout, interaction, link, or content-contract failure must extend a permanent
  guardrail after the immediate defect is fixed.
- The Deep Learning for Search course (`levshaazz/deep-learning-for-search-summer-2026`) is the design
  and interaction reference, but this repository's own contracts remain authoritative.

## Change discipline

- Preserve unrelated user changes and inspect the worktree before editing.
- Edit deck fragments in `Lectures/<slug>/parts/`; assembled `Lectures/<slug>.html` files are generated.
- Keep course facts in `data/course.json` and portal content in `data/portal.json`. Update every
  dependent surface required by `COURSE_GOVERNANCE.md`; do not patch only the rendered site.
- Record sources for technical and time-sensitive claims. Distinguish measured evidence, worked
  examples, and illustrative values in both wording and metadata.
- Never commit secrets, private rosters, hidden seeds or prompts, student repositories, private judge
  runs, `.env` files, credentials, or access tokens.
- A judge configuration change requires a fresh provenance-complete reference run before verified
  thresholds may be published.
- Never weaken or bypass a check merely to make a build green. Encode any legitimate exception as a
  narrow, documented rule.

## Required verification

For normal content or portal changes, run:

```bash
npm ci
npm run check
npm run build
npm run check:site
git diff --check
```

Lecture changes additionally require the full visual procedure in `narrative/LECTURE_STANDARD.md`.
Judge changes additionally require the tests and host procedures in `judge/OPERATIONS.md`. A successful
local build is not permission to label provisional thresholds verified.

Publishing is CI-driven: commit the reviewed source and push `main`; `.github/workflows/deploy.yml`
builds and deploys GitHub Pages. Verify the workflow result and the public URL after pushing.
