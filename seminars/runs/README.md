# Canonical rehearsal evidence

A rehearsal is **canonical** only when its directory contains all of the following:

- the exact repository commit and UTC timestamp;
- GPU, CUDA, driver, Python, framework, engine, model revision, and launch command;
- the workload definition and metric-contract version;
- one raw record per request, including failures and timeout reason;
- aggregate latency over successful requests only, reported beside the failure rate;
- generated throughput and latency tables plus an operator note explaining anomalies.

Plain-text summaries without this provenance are historical artifacts, not evidence. The
2026-09-19 rehearsal is intentionally named `.legacy-invalid.txt`: it used timeout-capped
latencies and cannot validate the current lecture.

The current canonical run is
[`2026-09-20-topic-00-metric-contract-v2/`](2026-09-20-topic-00-metric-contract-v2/README.md).
Its JSON preserves 630 raw request records and complete runtime provenance; its operator note
states the metric population, results, anomalies, and limits.
