#!/usr/bin/env bash
# The judge runs exactly this from a clean checkout of your tag.
# Contract: OpenAI-compatible server on 0.0.0.0:8000, model name "submission", streaming chat completions.
set -euo pipefail
cd "$(dirname "$0")"
if [[ -x /runtime/.venv/bin/vllm ]]; then
  VLLM=(/runtime/.venv/bin/vllm)
else
  uv sync --frozen
  VLLM=(uv run --frozen vllm)
fi
exec "${VLLM[@]}" serve Qwen/Qwen2.5-3B-Instruct \
  --revision aa8e72537993ba99e69dfaafa59ed015b17504d1 \
  --served-model-name submission \
  --host 0.0.0.0 --port 8000 \
  --dtype half \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90
