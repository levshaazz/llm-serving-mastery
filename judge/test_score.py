"""Unit tests for the scoring rules:  python3 -m pytest judge/  (or python3 judge/test_score.py)."""
import math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import score_round, speed_score  # noqa: E402

TH = {"quality_gates": {"gsm8k": 0.5, "ifeval": 0.5, "mmlu_pro": 0.3},
      "speed_bar_S": 1000.0, "ttft_p95_slo_s": 2.0, "max_error_rate": 0.01, "min_output_share": 0.95,
      "canary_min_similarity": 0.5}


def result(t32, t64, ttft=1.0, q=(0.6, 0.6, 0.4), failed=0, ok=True, out_len=256, canary=0.95, judge_error=False):
    return {"ok": ok, "judge_error": judge_error, "error": None if ok else "boom", "steps": {
        "canary": {"similarity_mean": canary},
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
             short=result(4000, 4000, out_len=120),
             swapped=result(4000, 4000, canary=0.1))
    for k in ("quality", "latency", "errors", "crashed", "short", "swapped"):
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
