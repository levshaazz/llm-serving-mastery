#!/usr/bin/env python3
"""
make_thresholds.py — derive a round's bars from a reference run's result.json.

    python judge/make_thresholds.py --round 1 --reference runs/reference/result.json \
        --note "reference submission on Colab T4" --out judge/thresholds/round-01.json

  quality gate  = quality_share × the reference score, per benchmark          (config.yaml → scoring)
  speed bar     = the reference S (geometric mean of tok/s at 32 and 64 clients)
  latency SLO   = the reference p95 TTFT at 64 clients × ttft_headroom, rounded up to 0.1 s
Bars are re-published every week; later rounds may use a different reference (announced).
"""
import argparse, json, math, sys, pathlib

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import speed_score  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    ap.add_argument("--allow-unverified-reference", action="store_true",
                    help="emergency override; the output remains marked unverified and must not be used for grading")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    sc = cfg["scoring"]
    ref = json.load(open(a.reference))
    if not ref.get("ok"):
        sys.exit(f"reference run failed: {ref.get('error')}")
    if ref.get("config_version") != cfg["version"]:
        sys.exit(f"reference config version {ref.get('config_version')} != current {cfg['version']}; rerun it")
    verified = bool((ref.get("provenance") or {}).get("complete"))
    if not verified and not a.allow_unverified_reference:
        sys.exit("reference has no complete machine-generated provenance; rerun it instead of reconstructing bars")
    st = ref["steps"]
    if speed_score(st["speed"]) <= 0:
        sys.exit("reference S is 0 — refusing to publish a bar that would divide by zero")
    can = st.get("canary") or {}
    if can.get("similarity_min", 0) < sc["canary_min_similarity"]:
        sys.exit(f"the reference itself fails the canary check ({st.get('canary')}) — recalibrate before publishing")
    if can.get("short_outputs", 1) > sc["canary_max_short_outputs"]:
        sys.exit(f"the reference has short hidden outputs ({can}) — fix the run before publishing")
    if can.get("unique_output_share", 0) < sc["canary_min_unique_share"]:
        sys.exit(f"the reference fails output-diversity checks ({can})")
    th = {
        "round": a.round,
        "note": a.note,
        "verified": verified,
        "judge_provenance": ref.get("provenance"),
        "reference": {"gpu": st["gpu"]["name"], "submission": st["contract"]["submission"],
                      "quality": st["quality"], "speed": st["speed"], "measured_at": ref["started_at"]},
        "quality_gates": {k: round(sc["quality_share"] * v, 4) for k, v in st["quality"].items()},
        "speed_bar_S": math.floor(10 * speed_score(st["speed"])) / 10,   # down: the reference clears its own bar
        "ttft_p95_slo_s": math.ceil(10 * sc["ttft_headroom"] * st["speed"]["64"]["ttft_p95_s"]) / 10,
        "max_error_rate": sc["max_error_rate"],
        "min_output_share": sc["min_output_share"],
        "canary_min_similarity": sc["canary_min_similarity"],
        "canary_similarity_stat": "min",
        "canary_max_short_outputs": sc["canary_max_short_outputs"],
        "canary_min_unique_share": sc["canary_min_unique_share"],
    }
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(th, open(a.out, "w"), indent=2)
    print(json.dumps({k: th[k] for k in ("quality_gates", "speed_bar_S", "ttft_p95_slo_s")}, indent=2))


if __name__ == "__main__":
    main()
