# Topic 00 canonical rehearsal — metric contract v2

This directory is the canonical Topic 00 rehearsal captured in Google Colab on a Tesla T4.
The measured notebook was the immutable repository commit
`ad08161b74ab32c296bec585e0cbd03f9f79f6fd`; the run finished at
`2026-09-20T02:25:58Z`.

## Files and integrity

| File | Purpose | SHA-256 |
|---|---|---|
| `results.json` | provenance, workload, 630 raw request records, and aggregates | `0c12e0d3864bfc34ba64a18bfcc912af8ea7bcaf2972e482fb4ca0603da46587` |
| `naive.log` | complete naive-server log | `f04b28fec9c540442e25e1425825e12343a012d31e0690d36456c6e6ba7150c9` |
| `vllm.log` | complete vLLM server log | `fb423404c535b012c5ddeb76aebeff81d416aabebb6956412f8cd727650810f6` |

## Frozen environment and launch

- GPU: Tesla T4, 15,360 MiB; driver 580.82.07; CUDA reported by the driver: 13.0.
- Naive runtime: Python 3.13.15, torch 2.11.0+cu128, transformers 5.16.1,
  FastAPI 0.116.1, Uvicorn 0.35.0, HTTPX 0.28.1.
- vLLM runtime: isolated Python 3.12 environment, vLLM 0.29.0.
- Model: `Qwen/Qwen2.5-1.5B-Instruct` at revision
  `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, FP16.
- Naive launch expression from the measured notebook:
  `[sys.executable, "naive_server.py"]`; the server serializes generation with one lock.
- vLLM launch command:
  `/content/vllm-env/bin/vllm serve Qwen/Qwen2.5-1.5B-Instruct --revision 989aa7980e4cf806f80c7fef2b1adb7bc71aa306 --port 8000 --dtype half --max-model-len 2048 --gpu-memory-utilization 0.85`.

The immutable notebook contains the generated `naive_server.py`, so the launch expression is
fully resolvable from the cited commit rather than from an untracked script.

## Workload and metric semantics

- One simultaneous closed-loop wave at 1, 8, 32, and 64 clients; three recorded repeats per
  server and concurrency; eight fixed prompts; `max_tokens=128`; 60 s client timeout.
- Both servers expose the same streaming chat-completions contract. Output tokens are estimated
  by re-tokenizing returned text with the pinned model tokenizer.
- `tok/s` below is successful-output goodput: completed output tokens divided by the complete
  wave wall time. Tokens generated for requests that later time out are deliberately excluded.
- TTFT percentiles contain successful requests only. Failures remain visible as a count and rate;
  a timeout is never inserted into the latency population as an artificial 60 s value.
- Aggregate goodput is the median of three wave-level values; its range is min–max. TTFT is pooled
  across successful requests from all three repeats. Failure counts are totals across all repeats.

## Results

| Clients | Pipeline goodput, median [min–max] tok/s | vLLM goodput, median [min–max] tok/s | Speed-up | Pipeline p95 TTFT | vLLM p95 TTFT | Pipeline failures | vLLM failures |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 19.7 [10.2–20.2] | 64.1 [60.4–64.6] | 3.3× | 0.181 s | 0.033 s | 0/3 (0%) | 0/3 (0%) |
| 8 | 22.5 [19.6–22.6] | 324.2 [323.7–325.8] | 14.4× | 25.269 s | 0.109 s | 0/24 (0%) | 0/24 (0%) |
| 32 | 19.7 [19.3–20.0] | 957.2 [950.6–978.4] | 48.6× | 50.903 s | 0.225 s | 54/96 (56.3%) | 0/96 (0%) |
| 64 | 18.7 [17.4–19.4] | 1519.3 [1405.2–1549.9] | 81.1× | 53.251 s | 0.523 s | 154/192 (80.2%) | 0/192 (0%) |

A separate, unrecorded 64-client mechanism-check wave polled vLLM's Prometheus metric
`vllm:num_requests_running`; the observed maximum was 64. This supports the batching explanation
without mixing that extra wave into the comparison table.

## Operator note and limitations

The central result is robust: the locked pipeline saturates at roughly 19–22 successful output
tokens/s, while queueing and the failure rate rise sharply. vLLM converts concurrency into batch
goodput and completes every measured request. This run demonstrates the chosen implementations on
one T4; it is not a universal estimate for all Hugging Face or vLLM configurations.

Important qualifications:

- The naive server is intentionally serial and is not a claim about an optimized Transformers
  batching server. The experiment isolates the production consequence of the common one-request-at-
  a-time baseline.
- Arrivals are simultaneous closed-loop waves, not an open-loop Poisson process. The results expose
  burst behavior but do not establish a sustainable arrival-rate SLO.
- The first pipeline single-client wave was cold (10.2 tok/s); the next two were 19.7 and 20.2.
  Reporting the median and range keeps this anomaly visible. vLLM performs compile/graph warm-up
  during startup, so the single-client comparison is not a matched cold-start experiment.
- On compute capability 7.5, vLLM logged that FlashAttention 2 is unsupported and selected its
  Triton attention backend. This is a fallback, not a failed request.
- The `EngineDeadError` at the end of `vllm.log` follows the deliberate SIGTERM/SIGKILL cleanup
  after all requests, the mechanism check, and `results.json` had completed. It is shutdown noise,
  not a benchmark failure; the raw records report zero vLLM failures.
- vLLM logged a generation-config warning. Requests explicitly set `temperature=0`; other model
  generation defaults may still differ from the naive path. This benchmark is a serving-system
  demonstration, not a strict output-quality equivalence test.

Do not copy these numbers to another GPU, model, prompt distribution, output length, engine version,
or arrival process without a new rehearsal.
