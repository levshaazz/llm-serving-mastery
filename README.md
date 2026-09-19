# LLM Serving Mastery: vLLM, Multi-GPU, and Production Deployment

Course site and lecture decks. Published at **https://levshaazz.github.io/llm-serving-mastery/**.

The canonical-source order and archive policy are documented in [`COURSE_GOVERNANCE.md`](COURSE_GOVERNANCE.md). The old standalone DOCX syllabus and stale PDF lecturer notes are archived and are not normative.

| Path | What |
|---|---|
| `data/course.json` | Course contract: topics, assessment, leaderboard rules, reading, and per-material readiness. |
| `data/portal.json` | Student-facing topic pages, dashboard, glossary, changelog, and provenance policy. |
| `Lectures/<slug>/parts/*.html` | Editable deck source, one fragment per slide. `npm run deck` assembles `Lectures/<slug>.html` (build output, gitignored). |
| `Lectures/{css,js,vendor}` | Offline deck engine (from the Deep Learning for Search template). Decks open over `file://`. |
| `seminars/` | Colab notebooks. Topics 0–2 have separate measurement and evidence contracts. |
| `topics/` | Per-topic outcomes, contact-session plan, required artifacts and acceptance checklist. |
| `src/` | Astro portal: dashboard, topics, schedule, syllabus, leaderboard, search, glossary, changelog, and provenance. |
| `_research/gen_images.py` | Serega illustrations (kitchen setting). Masters go to `_research/masters/` (gitignored); `scripts/optimize_images.py` makes the shipped WebP. |

```bash
npm ci
npm run build        # site → docs/, decks assembled and copied into docs/Lectures/
npm run check        # content contracts + deck QA + judge tests
npm run check:site   # internal links in the built docs/ artifact
npm run dev          # local site
scripts/publish.sh   # local deployment preflight; push main for CI deploy
open Lectures/01-modern-inference-systems.html   # after `npm run deck`
```

Production publishing is handled by `.github/workflows/deploy.yml`: every push to `main`
builds from source, verifies content and links, uploads one immutable artifact, and deploys
through GitHub Pages. Repository Pages settings must use **GitHub Actions** as the source.

Language: English only for now. Everything is shaped for adding Russian later. Decks keep every string in `<span lang="en">` (add a `lang="ru"` sibling and set `data-langs="en,ru"` on `<html>`). Site strings are `{ en }` objects (add `ru:` and put `'ru'` into `LOCALES`).
