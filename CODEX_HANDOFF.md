# Codex continuation handoff

This public, secret-free document lets the course owner continue the project from another machine or a
new Codex task without relying on chat history. It records decisions and state; executable contracts
remain in the canonical files named below.

## Start here on another machine

```bash
git clone https://github.com/levshaazz/llm-serving-mastery.git
cd llm-serving-mastery
git switch main
git pull --ff-only
npm ci
npm run check
npm run build
npm run check:site
```

Then read `AGENTS.md`, `COURSE_GOVERNANCE.md`, and the instruction document for the workstream you are
continuing. Check `git status` before editing and use `git log -1 --oneline` as the immutable starting
revision. Do not assume that a statement remembered from an earlier chat is newer than the repository.

Suggested opening prompt for a new Codex task:

> Continue LLM Serving Mastery from the checked-out repository. Read AGENTS.md and CODEX_HANDOFF.md in
> full, then inspect the current git state. Treat repository contracts as canonical, preserve unrelated
> changes, and report any conflict before changing course policy or judge semantics.

## Decisions already made by the owner

1. `LLM_Serving_Mastery_Syllabus.docx` is obsolete and archived. It must not drive content or policy.
2. The course retains 15 topics. Material that does not fit the live session becomes explicit guided
   self-study; topic coverage is not cut merely to reduce lecture size.
3. Hands-on multi-GPU and Kubernetes work remains part of the plan and will be implemented in the later
   relevant topics.
4. The selected leaderboard design is the enhanced automated judge, with reproducible measurements,
   quality and contract gates, provenance, private hidden inputs, a shadow round, and a human review
   before publication.
5. Accepted audit corrections must stay fixed: metric populations and denominators must be explicit;
   reference evidence cannot contradict claims about required precision; worked arithmetic must
   reconcile; timeout semantics and reproducibility must be executable rather than aspirational.
6. Lecture authoring uses the stable shared template. Generated mascot/narrative imagery is required
   where appropriate. Any discovered composition defect expands the guardrails.
7. A full lecture targets 80–100 substantive slides and deep learning, including concrete live examples
   and interactive diagrams. The reference bar is the owner's Deep Learning for Search course.

These decisions are mirrored in `AGENTS.md`, `COURSE_GOVERNANCE.md`, and
`narrative/LECTURE_STANDARD.md`. Change them only on an explicit new owner decision and update every
copy in the same commit.

## Current material readiness

The machine-readable status is in `data/course.json`; the portal must display that status without
inflating it.

| Topic | Slides | Lab | Assignment | Reading | Evidence | Current interpretation |
|---|---:|---:|---:|---:|---:|---|
| 00 — Introduction | ready | ready | ready | ready | ready | Canonical metric-contract-v2 rehearsal is committed with raw request records and logs. |
| 01 — Modern inference systems | ready | ready | ready | ready | ready | Deep lecture, baseline notebook, topic contract, and supporting evidence are present. |
| 02 — Inference bottlenecks | ready | ready | ready | ready | student-generated | The notebook produces the learner's evidence; no precomputed run should be implied. |
| 03–15 | not yet published | not yet published | not yet published | not yet published | not yet published | They remain curriculum commitments, not completed materials. |

Topic 00's canonical rehearsal lives at
`seminars/runs/2026-09-20-topic-00-metric-contract-v2/`. The file with
`.legacy-invalid.txt` in its name is retained only as an audit trail and must not be cited as valid
evidence.

The portal currently includes the reusable topic-page structure, student dashboard, schedule, search,
glossary, changelog, provenance explanations, mobile-table treatment, and CI-based Pages deployment.
It does not turn missing calendar dates or provisional grading infrastructure into completed work.

## Leaderboard and weekly-grading readiness

The repository is portable enough to continue judge setup, but it is **not ready for official weekly
grading yet**.

- Judge contract/config is v3.
- `judge/thresholds/round-01.json` is provisional and intentionally fails closed for grading.
- The retained Round 01 reference is a reconstructed config-v2 historical result, not valid v3
  calibration.
- The next required evidence is a clean, provenance-complete v3 reference run on the intended headless
  RTX 5070 Ti, followed by a 4–5-submission shadow round.
- Before the first cohort, the owner still needs exact round dates, publication SLA, appeal window,
  outage policy, and a deadline for resolving judge-error reruns.

Continue this work only through [`judge/OPERATIONS.md`](judge/OPERATIONS.md). That runbook contains host
requirements, preflight, secret handling, calibration, shadow-round cases, weekly operation, private
backup, recovery, and capacity bounds. Never commit `judge/roster.csv`, `judge/rounds/`, hidden seeds,
private mirrors, or raw private runs.

## Repository map

| Path | Role |
|---|---|
| `data/course.json` | Canonical curriculum, workload, assessment, leaderboard policy, and material status. |
| `data/portal.json` | Structured portal copy: topic pages, schedule, glossary, changelog, and provenance. |
| `topics/` | Per-topic outcomes, session plan, artifacts, and acceptance contract. |
| `narrative/LNN.md` | Narrative beat sheet required before authoring lecture NN. |
| `narrative/LECTURE_STANDARD.md` | Binding lecture depth, template, art, interaction, and QA rules. |
| `Lectures/<slug>/parts/` | Editable slide source. The assembled HTML is generated. |
| `seminars/` | Colab notebooks and public, sanitized evidence. |
| `_research/` | Source research and image-generation briefs/workflow. Lossless masters are local and ignored. |
| `judge/` | Automated evaluation code, locks, public configuration, provisional bars, and operations runbook. |
| `submission-template/` | Student starting point and reference submission contract. |
| `src/` | Astro course portal. |
| `scripts/` | Deck assembly, content guards, visual checks, bar synchronization, and site validation. |
| `.github/workflows/deploy.yml` | Verified GitHub Pages build and deployment. |

## Safe next work

### If continuing the judge

Use the intended Linux GPU host and execute `judge/OPERATIONS.md` from the top. The milestone is not
"the script ran"; it is reviewed v3 reference evidence, a verified threshold file, a passing shadow
round, and documented weekly policy. Commit only sanitized public outputs.

### If creating Topic 03 or later

1. Confirm the topic contract in `data/course.json` without changing the 15-topic commitment.
2. Create `narrative/LNN.md` with the incident, conceptual turns, worked numbers, interactions, failures,
   sources, lab contract, self-study boundary, and bridge to the next topic.
3. Use Lecture 0's shared visual grammar and existing interaction engines.
4. Generate required narrative art through `_research/gen_images.py` and `_research/mascots.py`;
   preserve masters outside Git and commit optimized WebP assets.
5. Add the notebook/topic page and use honest readiness states.
6. Run mechanical, build, link, and complete visual verification before publishing.

### If improving the portal

Keep structured facts in `data/`, retain usable mobile and keyboard behavior, and prefer an improvement
that serves a real student task. Search, glossary, changelog, provenance, dashboard, schedule, and topic
pages already exist; extend them instead of creating competing surfaces. Dates marked TBA require an
owner decision, not an invented value.

## Known open gaps

- Topics 03–15 are curriculum entries but their complete teaching packages are not published.
- Exact delivery and leaderboard calendar dates remain TBA.
- Round 01 has no verified v3 threshold and no completed shadow round.
- Weekly grading operations need measured capacity evidence plus the SLA, appeal, outage, and rerun
  policies listed above.
- The portal and decks are English-only today; their data and markup preserve a later RU path.
- Full visual inspection remains a human-in-the-loop requirement even when automated deck checks pass.

## Definition of a clean handoff

Before pushing work intended for another machine:

1. remove or ignore private artifacts and inspect `git status`;
2. run the verification commands from `AGENTS.md` plus workstream-specific checks;
3. commit source and public sanitized evidence with a descriptive message;
4. push `main` and verify the GitHub Actions Pages run;
5. update this file when readiness, blockers, or the next safe action materially changes.
