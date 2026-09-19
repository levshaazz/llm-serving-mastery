# Topic 01 — Modern LLM inference systems & production challenges

This topic establishes the system boundary and measurement language used by every later optimization. It does not treat a successful `generate()` call as evidence of production readiness.

## Learning outcomes

After the topic, a student can:

1. Trace a streaming request through client, gateway, router, scheduler, model worker and GPU execution.
2. Separate lifecycle time, queue time, prefill, first-token time, decode cadence and end-to-end time.
3. Define TTFT, TPOT/ITL, E2E latency, throughput and goodput without mixing their denominators.
4. Distinguish open-loop arrivals from closed-loop concurrency and explain why the difference affects conclusions.
5. Specify a workload and SLO that make a capacity claim falsifiable.
6. Produce a pinned, machine-readable single-GPU baseline and identify what it cannot prove.

## Contact-session plan

| Segment | Time | Outcome |
|---|---:|---|
| Lecture: request lifecycle and inference phases | 25 min | Shared end-to-end system model |
| Lecture: production objectives and failure modes | 25 min | Metric and overload vocabulary |
| Lecture: component responsibilities and experiment contract | 20 min | Reviewable architecture and workload specification |
| Pair exercise: repair an underspecified capacity claim | 10 min | A falsifiable experiment design |
| Seminar launch and environment check | 10 min | Every student starts from the same pinned baseline |

The times are a teaching guide, not a promise that all exercises finish in class. The required notebook and boundary trace continue as guided self-study.

## Required artifacts

- Completed `seminars/01-serving-system-baseline.ipynb`.
- `evidence/topic-01-baseline.json` produced by the notebook.
- `evidence/topic-01-reflection.md` answering the notebook interpretation questions.
- One end-to-end streaming boundary trace with observed facts separated from inference.
- A `round-01` repository tag that passes the current Colab self-check in `submission-template/README.md`.

## Acceptance checklist

- The model revision, tokenizer source, runtime versions, GPU and dtype are recorded.
- Cold lifecycle timing is not presented as request latency.
- Warm-up is outside the measured request interval.
- CUDA timing is synchronized.
- Prompt and output sizes are reported in tokens.
- Streaming chunks are not mislabeled as one token each.
- Failed or missing observations are not silently dropped.
- The conclusion is limited to a single-request baseline; it makes no unsupported concurrency claim.
- No secrets, model weights or caches are committed.

## Required reading

1. Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP 2023), sections 1–2.
2. Yu et al., *Orca: A Distributed Serving System for Transformer-Based Generative Models* (OSDI 2022), introduction and iteration-level scheduling overview.
3. Dean and Barroso, *The Tail at Scale* (CACM 2013), motivation and latency variability.
4. The repository's `judge/README.md` and `submission-template/README.md`; these are authoritative for course submission mechanics.

## Boundary with Topic 02

Topic 01 names prefill, decode, KV-cache occupancy and memory categories so measurements are interpretable. Topic 02 derives their computational and memory behavior, performs GPU profiling and reconciles measurements with hand calculations. Do not move the roofline, detailed KV-cache sizing or profiler lab into this topic.
