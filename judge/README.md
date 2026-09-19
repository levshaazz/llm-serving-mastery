# The judge

The code that measures every leaderboard submission. The same code runs on the instructor's
RTX 5070 Ti and on your Colab T4, so you can put your repository through the same pipeline
before the Thursday 23:59 MSK deadline.

| File | What |
|---|---|
| `run_submission.py` | measure one submission: fetch → contract → start → smoke → canary → quality (lm-eval) → speed (GuideLLM) → stop. Writes `result.json` + logs. |
| `config.yaml` | the measurement: timeouts, lm-eval tasks and sample sizes, GuideLLM load, canaries, scoring constants. Same for everybody in a round. |
| `score.py` | gates, speed score S, mark, rank, Overdrive. The rules are in its docstring and pinned by `test_score.py`. |
| `make_thresholds.py` | a round's bars from a reference run. |
| `thresholds/round-NN.json` | the published bars of each round. |
| `snapshot.py` | at the deadline: mirror every repository and resolve its `round-NN` tag to a commit. |
| `run_round.sh` | measure every snapshotted commit in the sandbox, retry judge errors once, score, publish the cleaned logs. |
| `dry_run.sh` | Tuesdays: start-up check of every repository's default branch on the judge GPU. |
| `requirements.txt` | readable top-level judge dependencies, exactly pinned. |
| `requirements.lock` | transitive Linux/Python 3.12 lock with hashes; install this on the judge. |

## What is measured, and why it is hard to game

- **Contract.** `submission.yaml` (author, model, immutable `model_revision`, stack) and `JOURNAL.md`. Plus either a self-contained `Dockerfile`, or `prepare.sh` + `serve.sh` + `pyproject.toml` + `uv.lock`. `prepare.sh` runs in a networked bootstrap with no judge seed/prompts and fills a per-run runtime/cache; `serve.sh` runs offline for measurement. The server must list `submission` on `/v1/models`, expose a model root matching the declaration, and stream a smoke answer.
- **Quality gate.** lm-eval runs GSM8K, IFEval and MMLU-Pro against your endpoint. Each dataset is prefetched at an immutable commit and lm-eval then runs offline. The questions are a subset chosen with the round's secret seed, not the public first N. Each score must be ≥ 90% of the reference.
- **Speed.** GuideLLM at 32 and 64 concurrent streams. Prompts are ~512 tokens of natural Wikitext drawn with the secret seed; requests ask for up to 256 output tokens with `ignore_eos`. One wave of warm-up and one of cool-down are excluded. S = √(tok/s₃₂ · tok/s₆₄).
- **Layered canaries.** Secret speed-shaped prompts run in parallel at rest and are interleaved with both load levels. Every pair—not their average—must meet the similarity floor. Every hidden response must contain at least 95% of the requested tokens, and diverse prompts must not collapse to one canned answer. These checks make shortcuts harder; they do not constitute a cryptographic proof of model identity, so suspicious runs remain auditable.
- **Unpredictable phase order.** Quality and speed phases are ordered from the secret round seed, so a submission cannot rely on a fixed quality-then-speed timeline. Content-based routing is still not cryptographically preventable; provenance, raw artifacts and manual audit remain part of enforcement.
- **Latency and honesty gates.** p95 TTFT is computed over successful requests at 64 clients and must meet the SLO; errors ≤ 1%. Output length is gated per hidden request, never by a mean.
- **Isolation (judge only, `--sandbox docker`).** The source and container root are read-only; writable state is limited to tmpfs and new per-run runtime/cache directories. Capabilities are dropped, privilege escalation is disabled, IPC is private, and PID count is bounded. Measurement uses an internal Docker network; before each run the judge inspects that network and verifies that a direct external TCP connection fails. Open egress stops the run as a judge error. The published API remains reachable from the measurement process.
- **One global budget.** Clone, build, downloads, startup, quality and speed share one wall-clock deadline. Each subprocess receives only the remaining time.
- **Provenance.** Results record the judge commit, config hash, Python/platform and judge package versions. Raw lm-eval and redacted GuideLLM reports are retained. A reconstructed or provenance-incomplete reference cannot generate grading thresholds.
- **Judge errors are never scored.** A busy GPU or a crash in the judge (`judge_error: true`) triggers one automatic rerun. If that fails too, the submission is listed as "needs rerun" and gets no 0.

## Self-check on Colab (T4)

```python
!git clone -q https://github.com/levshaazz/llm-serving-mastery /content/lsm
!pip -q install -r /content/lsm/judge/requirements.lock
!cd /content/lsm && python3 judge/run_submission.py \
    --repo https://github.com/<you>/<your-repo> --ref round-01 --out /content/runs/me
!cat /content/runs/me/result.json
# score yourself against the published bars
!mkdir -p /content/runs/all && cp -r /content/runs/me /content/runs/all/
!cd /content/lsm && python3 judge/score.py --round 1 --thresholds judge/thresholds/round-01.json \
    --runs /content/runs/all --out /content/runs/score.json
```

- A T4 is slower than the judge, so your S on Colab is a lower bound. Gates (contract, quality, canaries, answer length) behave the same on both.
- FP8 and NVFP4 paths cannot run on a T4. Neither can a `Dockerfile` submission, because Colab has no Docker. Use the Tuesday dry-run log for those.
- Your self-check uses seed 0 unless you set `JUDGE_SEED`. The round's real seed is secret.

## A round, instructor side

Requirements for the judge machine:
- the RTX 5070 Ti drives no display (headless), and nothing else runs on it;
- Docker with the NVIDIA container toolkit;
- an internal Docker network: `docker network create --internal lsm-judge-isolated` (host→published API remains available; container egress is denied);
- Python 3.12 environment synchronized from `judge/requirements.lock` (`uv pip sync judge/requirements.lock`).

```bash
# Friday 00:00 Moscow time (= Thursday 21:00 UTC), right after the Thursday 23:59 MSK deadline — cron
python3 judge/snapshot.py --round N --roster judge/roster.csv --dir judge/rounds/round-NN
JUDGE_SEED=<new secret> JUDGE_EGRESS_BLOCKED=1 judge/run_round.sh N  # after verifying the internal network
git add data/leaderboard && git commit -m "Round N" && scripts/publish.sh
# before the next round opens: publish its bars
python3 judge/make_thresholds.py --round N+1 --reference <run>/result.json --note "…" --out judge/thresholds/round-MM.json
```

- `judge/roster.csv` (`github,repo`) and `judge/rounds/` stay private (gitignored). That covers the mirrors, checked-out code, secret prompts and raw GuideLLM reports.
- Preserve the full raw run directory, including redacted GuideLLM reports and lm-eval artifacts, in private audit storage. Publish only `result.json` and redacted logs; the seed and prompt file are removed.
- Use a new `JUDGE_SEED` every round.
- Run the reference through the same clean pipeline after every config-version change. Never reconstruct a missing reference result from console output.
