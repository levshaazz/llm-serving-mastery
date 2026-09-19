# Topic 02 — Inference bottlenecks: KV cache, memory hierarchy, autoregression

This topic explains why prefill and decode stress a GPU differently and teaches students to predict a
bottleneck before profiling. The goal is not to memorize that decode is “memory-bound”, but to calculate
operations, data movement, live state, and a plausible hardware ceiling, then test the model.

## Learning outcomes

After the topic, a student can:

1. Trace one dense decoder layer and identify the serial and parallel axes of autoregressive generation.
2. Explain how prefill and decode change GEMM shapes, weight reuse, latency, and throughput.
3. Distinguish memory capacity, bandwidth, latency, and access-pattern problems.
4. Build and interpret a simple roofline model without presenting it as a complete latency predictor.
5. Derive KV-cache bytes per token from a model configuration, including MHA/GQA/MQA differences.
6. Use synchronized timers, `torch.profiler`, Nsight Systems, and Nsight Compute at the appropriate layer.
7. Reconcile a hand prediction with benchmark and profiler evidence.

## Contact-session plan

| Segment | Time | Outcome |
|---|---:|---|
| Lecture: autoregressive graph and phase-specific shapes | 20 min | Correct prefill/decode mental model |
| Lecture: hierarchy, arithmetic intensity, roofline | 25 min | Predict compute/bandwidth ceilings |
| Lecture: KV-cache capacity and traffic | 20 min | Calculate per-token state and workload fit |
| Interactive profiler triage | 10 min | Select wall clock, timeline, or kernel analysis |
| Seminar launch | 15 min | Produce the first pinned trace and calculation |

The complete 92-slide deck exceeds the live-session budget by design. Advanced derivations, hierarchical
roofline interpretation, and the second profiler trace continue as required guided self-study.

## Required artifacts

- Completed `seminars/02-gpu-profiling-and-bottlenecks.ipynb`.
- `evidence/topic-02-benchmark.json` with environment, workload, timing, memory, and token counts.
- One exported profiler trace or table with the measured region marked.
- `evidence/topic-02-analysis.md` containing weight bytes, KV bytes/token, roofline prediction, observed
  evidence, contradictions, and the next experiment.

## Acceptance checklist

- Both models use pinned revisions and the same explicit workload contract.
- Prompt and output lengths are reported after tokenization.
- Cold load, warm-up, prefill, and decode are not mixed into one unlabeled timer.
- Timings account for asynchronous CUDA execution.
- The report distinguishes allocated, reserved, peak, and device-total memory.
- KV-cache arithmetic uses the actual layer/KV-head/head-dimension/dtype values from each model config.
- The roofline result is labelled an upper-bound model and lists its omissions.
- Profiler overhead is not presented as production latency.
- A high utilization percentage is not used alone as proof of compute saturation.
- Every performance comparison includes units, denominator, trial count, and variability.

## Required reading

1. Williams, Waterman & Patterson, *Roofline* (CACM 2009), model and ridge-point sections.
2. NVIDIA CUDA C++ Best Practices Guide, bandwidth and device memory spaces.
3. Dao et al., *FlashAttention* (2022), IO-awareness argument and exact-attention claim.
4. PyTorch profiler documentation and recipe.
5. Qwen2.5-3B model configuration; verify KV dimensions directly from the pinned revision.

## Boundary with Topic 03

Topic 02 may change dtype only to illustrate bytes in a calculation. Topic 03 evaluates concrete
quantization formats, calibration, kernels, quality loss, and production trade-offs. Do not turn this
topic's profiler lab into a quantization comparison.
