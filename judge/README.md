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
| `requirements.txt` | the judge's own tools, pinned. |

## What is measured, and why it is hard to game

- **Contract.** `submission.yaml` (author, model, stack) and `JOURNAL.md`. Plus either a `Dockerfile`, or `serve.sh` + `pyproject.toml` + `uv.lock`. The server must list `submission` on `/v1/models` within 30 minutes and stream a smoke answer.
- **Quality gate.** lm-eval runs GSM8K, IFEval and MMLU-Pro against your endpoint. The questions are a subset chosen with the round's secret seed, not the public first N, so you cannot pre-store the answers. Each score must be ≥ 90% of the reference.
- **Speed.** GuideLLM at 32 and 64 concurrent streams. Prompts are ~512 tokens of natural text (Wikitext) drawn with the secret seed, and answers are exactly 256 tokens (`max_completion_tokens` + `ignore_eos`). One wave of warm-up and one of cool-down are excluded, so only steady state counts. S = √(tok/s₃₂ · tok/s₆₄).
- **Same-model canaries.** A few speed-style prompts are answered at rest, then sent again in the middle of the load. The requests are byte-for-byte like GuideLLM's. If the answers under load differ from the answers at rest, a different model served the load, and the round fails.
- **Latency and honesty gates.** p95 TTFT at 64 clients ≤ SLO; errors ≤ 1%; answers really 256 tokens long.
- **Isolation (judge only, `--sandbox docker`).** Your `serve.sh` runs in a container, not as the judge's user. It gets its own Hugging Face cache and only allow-listed environment variables. The judge's tokenizer, datasets and seed are out of its reach.
- **Judge errors are never scored.** A busy GPU or a crash in the judge (`judge_error: true`) triggers one automatic rerun. If that fails too, the submission is listed as "needs rerun" and gets no 0.

## Self-check on Colab (T4)

```python
!git clone -q https://github.com/levshaazz/llm-serving-mastery /content/lsm
!pip -q install -r /content/lsm/judge/requirements.txt
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
- `judge/requirements.txt` installed.

```bash
# Friday 00:00 Moscow time (= Thursday 21:00 UTC), right after the Thursday 23:59 MSK deadline — cron
python3 judge/snapshot.py --round N --roster judge/roster.csv --dir judge/rounds/round-NN
JUDGE_SEED=<new secret> judge/run_round.sh N          # measures, scores, writes data/leaderboard/round-NN*
git add data/leaderboard && git commit -m "Round N" && scripts/publish.sh
# before the next round opens: publish its bars
python3 judge/make_thresholds.py --round N+1 --reference <run>/result.json --note "…" --out judge/thresholds/round-MM.json
```

- `judge/roster.csv` (`github,repo`) and `judge/rounds/` stay private (gitignored). That covers the mirrors, checked-out code, secret prompts and raw GuideLLM reports.
- Only `result.json` and the logs are published, with the seed removed.
- Use a new `JUDGE_SEED` every round.
