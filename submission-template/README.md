# Leaderboard submission — template

Copy these files into your own **public** repository. Change anything except the contract:

| Fixed by the contract | |
|---|---|
| `prepare.sh` | networked bootstrap: install the locked environment and fetch the immutable model revision; no judge seed or hidden prompts are present |
| `serve.sh` | starts an OpenAI-compatible server on `0.0.0.0:8000` from a clean checkout |
| model name | `submission` (`--served-model-name submission`) |
| model revision | immutable commit in both `submission.yaml` and the server's `--revision` argument |
| API | streaming `/v1/chat/completions` that honours `max_tokens` and `ignore_eos`, `/v1/models`; accepts requests of up to 4096 tokens (prompt + answer) |
| `uv.lock` | pinned environment: `uv lock` after every dependency change, commit it |
| `submission.yaml` | author, model, immutable model revision, stack |
| `JOURNAL.md` | one entry per round |
| `Dockerfile` | optional alternative; it must bake in dependencies/model artifacts because the scored container has no egress |

Submit a round: `git tag round-01 && git push origin round-01` before **Thursday 23:59 Moscow time (MSK, UTC+3)**.

## Quick start (Colab or any Linux box with an NVIDIA GPU)

```bash
pip install uv                 # once
uv lock                        # after every change to pyproject.toml — commit uv.lock
bash serve.sh                  # starts the server on :8000
```

Self-check exactly like the judge: see `judge/README.md` in the course repository.

This template is the **reference implementation**. The retained round-1 Colab numbers are provisional historical calibration only; a fresh provenance-complete config-v3 run is required before grading.
