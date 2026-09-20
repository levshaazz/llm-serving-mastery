# Reference-run status

`round-01.result.json` and `round-01.colab-run.log` are legacy config-v2 historical artifacts. The
result was reconstructed after the Colab VM disappeared, has incomplete provenance, and must not be
used for grading. The matching threshold file is deliberately marked `verified: false`.

On the judge host, follow [`../OPERATIONS.md`](../OPERATIONS.md) and run
`judge/run_reference.sh`. After manual review, its publish phase creates
`round-01.v3.result.json` and replaces the provisional threshold with a verified config-v3 file.

Machine-generated public reference results must never contain the hidden seed, prompts, tokens,
private mirror paths, or raw private evaluation artifacts. Keep the complete run under the ignored
`judge/rounds/` tree and in access-controlled audit storage.
