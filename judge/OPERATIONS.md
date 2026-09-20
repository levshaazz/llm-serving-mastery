# Judge operations and machine handoff

This is the continuation point for moving weekly grading to another machine. The public repository
contains code, locks, templates, and provisional calibration. It intentionally does **not** contain
the roster, hidden seed, submission mirrors, raw private runs, or hidden prompts.

## Current state

- Judge contract/config: v3.
- Round 01 threshold file: provisional and explicitly not valid for grading.
- Retained reference: legacy config v2 reconstructed from Colab output; historical only.
- Required next milestone: a provenance-complete v3 reference run on the headless RTX 5070 Ti,
  followed by a small shadow round.

`judge/run_round.sh` fails closed while the selected threshold file has `verified != true`.

## 1. Clone and install on the judge host

Requirements: Linux x86_64, Python 3.12, `uv`, Git, Docker, NVIDIA driver, NVIDIA Container Toolkit,
and a headless GPU. Start from a clean checkout because dirty judge source makes provenance incomplete.

```bash
git clone https://github.com/levshaazz/llm-serving-mastery.git
cd llm-serving-mastery
git switch main
git pull --ff-only

uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python judge/requirements.lock
source .venv/bin/activate

docker network inspect lsm-judge-isolated >/dev/null 2>&1 || \
  docker network create --internal lsm-judge-isolated

# Pull by the immutable digest declared in judge/config.yaml.
docker pull ghcr.io/astral-sh/uv@sha256:e31c71ce6acbe3f4b743f6773948428e6255a4eb20295a9d67a703a1c4e5f664

judge/preflight.sh reference 1
```

The preflight is read-only. It verifies the clean checkout, Python and locked packages, GPU idle
state, free port, internal Docker network, blocked container egress, NVIDIA container access, judge
tests, and—when run in `grading` mode—a verified threshold and private roster.

## 2. Keep private state private

Create the roster from the tracked example:

```bash
cp judge/roster.example.csv judge/roster.csv
```

`judge/roster.csv`, `judge/rounds/`, and `runs/` are gitignored. Store the round seed in the machine's
secret manager. Do not put it in a command, shell history, `.env` committed to Git, CI variable printed
in logs, or the public leaderboard. The same seed must be used for the reference and every submission
in that round so quality gates use the same hidden sample.

One shell-safe interactive option is:

```bash
read -rsp 'Round seed: ' JUDGE_SEED; echo
export JUDGE_SEED
export JUDGE_EGRESS_BLOCKED=1
```

Keep the seed until all judge-error reruns and appeals for that round are closed, then rotate it.

## 3. Produce the valid Round 01 calibration

```bash
judge/run_reference.sh 1 'Qwen2.5-3B-Instruct · vLLM 0.29 · FP16 · RTX 5070 Ti'
```

This creates, under the private `judge/rounds/round-01/reference/` directory:

- the generated standalone reference repository;
- the complete raw run and logs;
- `thresholds.candidate.json`.

It does not overwrite public thresholds by default. Review `result.json`, all logs, GPU identity,
quality, speed, canaries, and provenance. Then publish the reviewed result and threshold atomically:

```bash
PUBLISH_REFERENCE=1 judge/run_reference.sh 1 \
  'Qwen2.5-3B-Instruct · vLLM 0.29 · FP16 · RTX 5070 Ti'
```

The publish mode reuses the successful private run; it does not rerun the benchmark. It writes:

- `judge/reference/round-01.v3.result.json` — sanitized machine-generated reference;
- `judge/thresholds/round-01.json` — `verified: true` bars.

Review the diff, run `npm run check`, commit, and push before the round opens. Never use
`--allow-unverified-reference` for grading.

## 4. Shadow round before accepting grades

Use 4–5 private test repositories representing:

1. the reference submission;
2. a valid but slower submission;
3. a quality-gate failure;
4. a timeout/crash;
5. an egress or contract violation.

Run the exact production chain and confirm the expected outcome for every row:

```bash
judge/preflight.sh grading 1
python3 judge/snapshot.py --round 1 --roster judge/roster.csv --dir judge/rounds/round-01
judge/run_round.sh 1
```

Inspect the private raw attempts and the public candidate under `data/leaderboard/`. Confirm that the
seed, prompts, local mirror paths, tokens, and private repositories are absent from publishable files.

## 5. Weekly production sequence

### Tuesday dry run

```bash
judge/preflight.sh grading N
JUDGE_EGRESS_BLOCKED=1 judge/dry_run.sh
```

Review `data/dry-run/`, commit, and push the student-visible startup results.

### Deadline — Thursday 23:59 MSK / Friday 00:00 MSK snapshot

```bash
python3 judge/snapshot.py --round N --roster judge/roster.csv \
  --dir judge/rounds/round-NN
```

Back up `snapshot.json` and `mirrors/` to private audit storage before measurement. The snapshot,
not commit time, is the deadline record.

### Measure, score, review, publish

```bash
judge/preflight.sh grading N
JUDGE_SEED="$JUDGE_SEED" JUDGE_EGRESS_BLOCKED=1 judge/run_round.sh N
```

`judge/run_round.sh` preserves every attempt privately, retries one judge error, and emits a public
candidate under `data/leaderboard/`. Resolve every `needs_rerun` with the same seed before grades are
final. Manually audit redaction and anomalies, then:

```bash
git add data/leaderboard
git commit -m "Publish leaderboard round NN"
git push origin main
```

GitHub Actions performs the verified Pages deployment.

## 6. Private backup and recovery

After each reference, snapshot, attempt, rerun, and final score, back up `judge/rounds/round-NN/` to
access-controlled storage. Retain:

- snapshot and mirrors;
- reference and threshold candidate;
- every raw attempt, including judge errors;
- raw GuideLLM/lm-eval artifacts and logs;
- final public JSON as published;
- judge commit and threshold commit.

Do not resume by deleting successful student directories. `run_round.sh` currently runs sequentially
and is not a transactional scheduler; after interruption, make a backup and explicitly rerun only the
affected students or restart the shadow round. Before the first real cohort, document the calendar,
publication SLA, appeal window, outage policy, and the deadline for resolving `needs_rerun`.

## 7. Capacity envelope

One submission has a 90-minute hard ceiling. On one GPU, 30 students therefore have a 45 GPU-hour
worst-case main round before retries; Tuesday startup checks add up to 15 GPU-hours at the 30-minute
startup ceiling. Reserve a publication window that can absorb this bound, or reduce the cohort per
judge GPU. Do not promise same-night grades without a measured shadow-round duration.
