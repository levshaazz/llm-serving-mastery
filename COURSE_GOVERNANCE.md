# Course source of truth

This repository is the canonical course source. When two artifacts disagree, use this order:

1. [`data/course.json`](data/course.json) for the curriculum, workload, assessment and published leaderboard policy;
2. `Lectures/*/parts/` and `seminars/` for the instructional implementation;
3. `judge/` and `submission-template/` for the executable evaluation contract;
4. generated site pages, assembled decks and PDF/handout exports as derived artifacts.

Generated artifacts must carry the source revision used to create them or be treated as unverified. Historical files live in the parent `archive/` directory and are not course requirements.

## Change rule

A change to scoring, workload or topic coverage is complete only when the canonical data, the relevant teaching material, the executable judge and public wording agree. A new judge configuration version requires a fresh reference run; reconstructed or provenance-incomplete results cannot publish new thresholds.
