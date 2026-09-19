# LLM Serving Mastery: vLLM, Multi-GPU, and Production Deployment

Course site and lecture decks. Published at **https://levshaazz.github.io/llm-serving-mastery/**.

| Path | What |
|---|---|
| `data/course.json` | Single source of truth: topics, assessment, leaderboard rules, reading. Site pages render from it. |
| `Lectures/<slug>/parts/*.html` | Editable deck source, one fragment per slide. `npm run deck` assembles `Lectures/<slug>.html` (build output, gitignored). |
| `Lectures/{css,js,vendor}` | Offline deck engine (from the Deep Learning for Search template). Decks open over `file://`. |
| `seminars/` | Colab notebooks. `00-live-demo-pipeline-vs-vllm.ipynb` is the Lecture 0 live demo. |
| `src/` | Astro site: home, syllabus, leaderboard. |
| `_research/gen_images.py` | Serega illustrations (kitchen setting). Masters go to `_research/masters/` (gitignored); `scripts/optimize_images.py` makes the shipped WebP. |

```bash
npm ci
npm run build        # site → docs/, decks assembled and copied into docs/Lectures/
npm run dev          # local site
scripts/publish.sh   # build + push docs/ to gh-pages (the Pages source)
open Lectures/00-introduction.html   # after `npm run deck`
```

Language: English only for now. Everything is shaped for adding Russian later. Decks keep every string in `<span lang="en">` (add a `lang="ru"` sibling and set `data-langs="en,ru"` on `<html>`). Site strings are `{ en }` objects (add `ru:` and put `'ru'` into `LOCALES`).
