# Leaderboard submission — template

Copy these files into your own **public** repository. Change anything except the contract:

| Fixed by the contract | |
|---|---|
| `serve.sh` | starts an OpenAI-compatible server on `0.0.0.0:8000` from a clean checkout |
| model name | `submission` (`--served-model-name submission`) |
| API | streaming `/v1/chat/completions` that honours `max_tokens` and `ignore_eos`, `/v1/models`; accepts requests of up to 4096 tokens (prompt + answer) |
| `uv.lock` | pinned environment: `uv lock` after every dependency change, commit it |
| `submission.yaml` | author, model, stack |
| `JOURNAL.md` | one entry per round |
| `Dockerfile` | optional; if present the judge builds and runs it instead of `serve.sh` (must expose 8000) |

Submit a round: `git tag round-01 && git push origin round-01` before **Thursday 23:59 Moscow time (MSK, UTC+3)**.

## Quick start (Colab or any Linux box with an NVIDIA GPU)

```bash
pip install uv                 # once
uv lock                        # after every change to pyproject.toml — commit uv.lock
bash serve.sh                  # starts the server on :8000
```

Self-check exactly like the judge: see `judge/README.md` in the course repository.

This template is also the **reference submission**: round-1 bars were measured by running it through the judge on Colab T4.
