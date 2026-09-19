# Reference-course site audit → LLM Serving Mastery

Reference: `levshaazz/deep-learning-for-search-summer-2026` and its published Pages site, reviewed
2026-09-19. The useful lesson is the information architecture: one piece of teaching content is exposed
as a deck, a reading chapter, reusable interactive widgets, images, papers, and course logistics.

## What the reference does especially well

- The home page makes the course legible in one screen: story, lectures, schedule, assessment, and
  instructor context.
- Each lecture card offers two intentional modes: “Read in Book” and “Open slides”.
- Book chapters turn the same material into a scrollable narrative rather than dumping slide thumbnails.
- The Playground makes dozens of lecture widgets independently discoverable, searchable, and replayable.
- Gallery, Papers, Glossary, schedule, assignments, and assessment have first-class routes instead of
  being buried inside decks.
- Multilingual navigation, theme controls, deep links, and consistent visual characters make the site
  feel like one product rather than a directory of files.

## Recommended changes for this course

### P0 — make every topic an auditable learning unit

1. Add a topic hub with four explicit actions: **Read**, **Open slides**, **Run notebook**, and
   **Sources**. Show estimated live time and self-study time separately.
2. Surface lecture status (`draft`, `review`, `published`) and last-reviewed date. This prevents a polished
   card from implying that unfinished material is canonical.
3. Add stable anchors for every topic and artifact; automated checks should crawl every internal link.
4. Put the current production question and expected learner deliverable directly on each topic card.

### P1 — turn depth into site features

5. Add a Book layer for dense explanations, derivations, worked traces, and self-study material. The deck
   remains paced for teaching; the Book carries the durable reference narrative.
6. Add a Playground for reusable serving widgets: request timeline, batching simulator, KV-cache budget,
   queue/saturation explorer, parallelism topology, autoscaling delay, and SLO/error-budget calculator.
7. Add a Papers & specifications catalog, grouped by topic and tagged as required/optional/historical.
   Link claims in decks and chapters to stable bibliography IDs.
8. Add a visual Gallery, but organize it by concept (“prefill”, “decode”, “backpressure”), not only by
   lecture number, so images function as a visual glossary.
9. Add full-site search across Book, glossary, papers, notebooks, and widget titles.

### P2 — expose the production-learning loop

10. Add an experiment registry page: hardware, model, engine/version, workload, seed, command, raw result,
    and interpretation. Never show a benchmark number without its measurement contract.
11. Add a public leaderboard explainer and frozen-round archive next to the live standings so scoring and
    historical reproducibility are visible.
12. Add a “course map” connecting the 15 topics by artifact: which lecture introduces, measures,
    optimizes, deploys, and operates the same service.
13. Add progress affordances that are local and privacy-preserving: completed reading, viewed deck, run
    notebook, attempted exercise. They should never gate access.
14. Add accessibility and resilience gates: keyboard-only widget use, reduced motion, contrast, meaningful
    alt text, small-screen Book layout, and a useful no-JavaScript fallback for reading content.

## What not to copy blindly

- Do not duplicate content manually between deck and Book. Share structured facts, references, widget
  manifests, and worked-example data.
- Do not build a 90-widget Playground before the first reusable widgets exist. Lecture 1 should establish
  the contract with a small, excellent set.
- Do not make the Gallery a substitute for instructional diagrams; every visual must answer a question.
- Do not add languages until the English source and translation workflow are mechanically stable.

## Suggested delivery order

1. topic hub + status/metadata + link checker;
2. reusable widget contract and Lecture 1 widgets;
3. one Book chapter for Lecture 1 as the reference implementation;
4. sources catalog and experiment registry;
5. Gallery/search/progress after the underlying assets are consistently structured.
