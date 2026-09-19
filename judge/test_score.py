"""Unit tests for the scoring rules:  python3 -m pytest judge/  (or python3 judge/test_score.py)."""
import math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import score_round, speed_score  # noqa: E402
import run_submission as judge_runtime  # noqa: E402
from run_submission import Deadline, PhaseDeadline, Step, canary_evidence, parse_guidellm  # noqa: E402

TH = {"quality_gates": {"gsm8k": 0.5, "ifeval": 0.5, "mmlu_pro": 0.3},
      "speed_bar_S": 1000.0, "ttft_p95_slo_s": 2.0, "max_error_rate": 0.01, "min_output_share": 0.95,
      "canary_min_similarity": 0.5, "canary_similarity_stat": "min", "canary_max_short_outputs": 0,
      "canary_min_unique_share": 0.75}


def test_startup_phase_uses_one_shared_budget():
    original = judge_runtime.time.monotonic
    clock = [10.0]
    try:
        judge_runtime.time.monotonic = lambda: clock[0]
        parent = Deadline(100)
        startup = PhaseDeadline(parent, 30, "server setup")
        assert startup.timeout(1800, "build") == 30
        clock[0] = 25
        assert startup.timeout(1800, "readiness") == 15
        clock[0] = 40
        try:
            startup.check("readiness")
            assert False, "startup phase must expire 30 seconds after it starts"
        except Step as exc:
            assert "total budget" in str(exc)
    finally:
        judge_runtime.time.monotonic = original


def result(t32, t64, ttft=1.0, q=(0.6, 0.6, 0.4), failed=0, ok=True, out_len=256, canary=0.95,
           short=0, unique=1.0, judge_error=False):
    return {"ok": ok, "judge_error": judge_error, "error": None if ok else "boom", "steps": {
        "canary": {"similarity_mean": canary, "similarity_min": canary, "short_outputs": short,
                   "unique_output_share": unique},
        "quality": dict(zip(("gsm8k", "ifeval", "mmlu_pro"), q)),
        "speed": {"32": {"output_tok_s": t32, "ttft_p95_s": 0.5, "requests_ok": 256 - failed, "requests_failed": failed,
                         "output_tokens_mean": out_len, "output_tokens_expected": 256},
                  "64": {"output_tok_s": t64, "ttft_p95_s": ttft, "requests_ok": 256 - failed, "requests_failed": failed,
                         "output_tokens_mean": out_len, "output_tokens_expected": 256}}}}


def rows(**students):
    return {r["student"]: r for r in score_round([{"student": k, "result": v} for k, v in students.items()], TH)}


def test_speed_score_is_geometric_mean():
    assert math.isclose(speed_score(result(800, 1250)["steps"]["speed"]), 1000.0)


def test_mark_is_proportional_and_capped():
    r = rows(half=result(500, 500), bar=result(1000, 1000), over=result(3000, 3000))
    assert r["half"]["mark"] == 2.5 and r["half"]["points"] == 2.0
    assert r["bar"]["mark"] == 5 and r["bar"]["points"] == 4.0
    assert r["over"]["mark"] == 5


def test_each_gate_zeroes_the_round():
    r = rows(quality=result(2000, 2000, q=(0.4, 0.6, 0.4)),
             latency=result(2000, 2000, ttft=2.5),
             errors=result(2000, 2000, failed=10),
             crashed=result(2000, 2000, ok=False),
             short=result(4000, 4000, out_len=120, short=1),
             swapped=result(4000, 4000, canary=0.1),
             canned=result(4000, 4000, unique=0.1))
    for k in ("quality", "latency", "errors", "crashed", "short", "swapped", "canned"):
        assert r[k]["mark"] == 0 and not r[k]["passed"] and r[k]["reasons"], k


def test_overdrive_bands_only_for_mark_5():
    ss = {f"s{i:02d}": result(1000 + 100 * i, 1000 + 100 * i) for i in range(20)}  # all clear the bar
    ss["slow"] = result(900, 900)                                                    # mark < 5
    r = rows(**ss)
    assert r["s19"]["overdrive"] == 2 and r["s18"]["overdrive"] == 2               # top 10% of 20 = 2
    assert r["s17"]["overdrive"] == 1 and r["s16"]["overdrive"] == 1
    assert r["s15"]["overdrive"] == 0 and r["slow"]["overdrive"] == 0
    assert r["s19"]["rank"] == 1


def test_judge_errors_are_never_scored():
    r = rows(a=result(2000, 2000, ok=False, judge_error=True))
    assert r["a"]["needs_rerun"] and r["a"]["mark"] is None and r["a"]["points"] is None


def test_overdrive_needs_the_bar_not_a_rounded_mark():
    r = rows(almost=result(999.9, 999.9), clear=result(1000, 1000))
    assert r["almost"]["mark"] == 5.0 and r["almost"]["overdrive"] == 0   # displays 5.0, did not clear
    assert r["clear"]["overdrive"] == 2


def test_band_size_rounds_up():
    ss = {f"s{i:02d}": result(1000 + 10 * i, 1000 + 10 * i) for i in range(25)}
    r = rows(**ss)
    assert sum(1 for x in r.values() if x["overdrive"] == 2) == 3            # ceil(2.5)


def test_small_class_still_gets_a_band_and_ties_share():
    r = rows(a=result(2000, 2000), b=result(2000, 2000), c=result(1500, 1500))
    assert r["a"]["overdrive"] == r["b"]["overdrive"] == 2 and r["a"]["rank"] == r["b"]["rank"] == 1
    assert r["c"]["overdrive"] == 1 and r["c"]["rank"] == 3


def test_guidellm_parser_uses_successful_request_metrics():
    report = {"benchmarks": [{"metrics": {
        "output_tokens_per_second": {"successful": {"mean": 123.456}},
        "time_to_first_token_ms": {"successful": {"median": 100, "percentiles": {"p95": 250}}},
        "time_per_output_token_ms": {"successful": {"median": 7.5}},
        "output_token_count": {"successful": {"mean": 256}},
        "request_totals": {"successful": 10, "errored": 1, "incomplete": 2}},
        "scheduler_metrics": {"measure_start_time": 10, "measure_end_time": 20}}]}
    got = parse_guidellm(report, 256)
    assert got["output_tok_s"] == 123.46 and got["ttft_p95_s"] == 0.25
    assert got["requests_ok"] == 10 and got["requests_failed"] == 3


def test_canary_evidence_is_per_request_and_detects_canned_answers():
    class Words:
        @staticmethod
        def encode(text, add_special_tokens=False):
            return text.split()
    cfg = {"scoring": {"min_output_share": 0.75}, "speed": {"output_tokens": 4}}
    got = canary_evidence(cfg, Words(), ["a b c d", "x y z q"], {"32": [(0, "a b"), (1, "a b")]})
    assert got["short_outputs"] == 2 and got["output_tokens_min"] == 2
    assert got["unique_output_share"] == 0.5 and got["similarity_min"] < got["similarity_mean"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
