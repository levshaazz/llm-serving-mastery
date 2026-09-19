#!/usr/bin/env bash
# The judge runs exactly this from a clean checkout of your tag.
# Contract: OpenAI-compatible server on 0.0.0.0:8000, model name "submission", streaming chat completions.
set -euo pipefail
cd "$(dirname "$0")"
uv sync --frozen
exec uv run --frozen vllm serve Qwen/Qwen2.5-3B-Instruct \
  --served-model-name submission \
  --host 0.0.0.0 --port 8000 \
  --dtype half \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90
