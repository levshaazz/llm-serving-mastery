#!/usr/bin/env python3
"""
score.py — turn a round's result.json files into marks, ranks and Overdrive.

    python judge/score.py --round 1 --thresholds judge/thresholds/round-01.json \
        --runs judge/rounds/round-01/runs --out data/leaderboard/round-01.json

Rules (the same text is on the slides, the syllabus and the leaderboard page):
  rerun   a run that failed because of the judge (judge_error) is never scored — it is listed for a rerun
  gates   contract + start-up + smoke ok · every quality score ≥ its gate ·
          canaries: the same prompts answered at rest and under load must match (same model) ·
          p95 TTFT at 64 clients ≤ SLO · error rate ≤ max and answers ≥ min_output_share of
          the requested length at every level
  S       geometric mean of output tok/s at 32 and 64 clients
  mark    5 × min(1, S / S_bar) if every gate passes, else 0
  points  mark × 0.8  (each round = 4% of the course grade)
  rank    among gate-passers, by S (desc); equal S → equal rank
  Overdrive  among submissions that cleared the bar (S ≥ S_bar): top 10% → +2, next 10% → +1
             (band size = ceil(0.1 × number of submissions that cleared the bar); ties at an edge share the band)
"""
import argparse, json, math, pathlib, sys

POINTS_PER_MARK = 0.8          # 5 marks → 4% of the course grade
OVERDRIVE_BANDS = ((0.10, 2), (0.10, 1))


def speed_score(speed):
    a, b = speed["32"]["output_tok_s"], speed["64"]["output_tok_s"]
    return math.sqrt(a * b) if a and b and a > 0 and b > 0 else 0.0


def gates(result, th):
    """Return (passed: bool, reasons: list[str])."""
    if not result.get("ok"):
        return False, [result.get("error") or "run failed"]
    st = result["steps"]
    why = []
    can = st.get("canary") or {}
    if can.get("similarity_mean") is None or can["similarity_mean"] < th["canary_min_similarity"]:
        why.append(f"canary: answers under load differ from answers at rest (similarity {can.get('similarity_mean')} "
                   f"< {th['canary_min_similarity']}) — the same model must serve every request")
    for task, gate in th["quality_gates"].items():
        got = st.get("quality", {}).get(task)
        if got is None:
            why.append(f"{task}: no score")
        elif got < gate:
            why.append(f"{task} {got:.3f} < gate {gate:.3f}")
    sp = st.get("speed", {})
    for lvl in ("32", "64"):
        if lvl not in sp:
            why.append(f"no speed measurement at {lvl} clients")
            continue
        m = sp[lvl]
        total = (m.get("requests_ok") or 0) + (m.get("requests_failed") or 0)
        if total == 0 or (m.get("requests_failed") or 0) / total > th["max_error_rate"]:
            why.append(f"error rate too high at {lvl} clients ({m.get('requests_failed')}/{total})")
        got, want = m.get("output_tokens_mean"), m.get("output_tokens_expected")
        if not got or not want or got < th["min_output_share"] * want:
            why.append(f"answers too short at {lvl} clients ({got} of {want} tokens) — honour max_tokens and ignore_eos")
    ttft = sp.get("64", {}).get("ttft_p95_s")
    if ttft is None:
        why.append("no p95 TTFT at 64 clients")
    elif ttft > th["ttft_p95_slo_s"]:
        why.append(f"p95 TTFT@64 {ttft:.2f} s > SLO {th['ttft_p95_slo_s']:.2f} s")
    return not why, why


def score_round(entries, th):
    """entries: list of {"student": str, "result": dict}. Returns rows sorted by rank."""
    rows = []
    for e in entries:
        if e["result"].get("judge_error"):
            rows.append({"student": e["student"], "passed": False, "needs_rerun": True, "reasons": [e["result"].get("error")],
                         "S": 0.0, "mark": None, "points": None, "rank": None, "overdrive": 0, "cleared": False})
            continue
        passed, why = gates(e["result"], th)
        S = speed_score(e["result"]["steps"]["speed"]) if passed else 0.0
        mark = round(5 * min(1.0, S / th["speed_bar_S"]), 2) if passed else 0.0
        rows.append({"student": e["student"], "passed": passed, "needs_rerun": False, "reasons": why, "S": round(S, 1),
                     "mark": mark, "points": round(mark * POINTS_PER_MARK, 2), "rank": None, "overdrive": 0,
                     "cleared": passed and S >= th["speed_bar_S"]})
    ranked = sorted([r for r in rows if r["passed"]], key=lambda r: -r["S"])
    for i, r in enumerate(ranked):
        r["rank"] = 1 + next(j for j, q in enumerate(ranked) if q["S"] == r["S"])
    top = [r for r in ranked if r["cleared"]]
    start = 0
    for share, bonus in OVERDRIVE_BANDS:
        size = math.ceil(share * len(top)) if top else 0
        band = top[start:start + size]
        if band:  # ties at the band edge get the same bonus
            edge = band[-1]["S"]
            band += [r for r in top[start + size:] if r["S"] == edge]
        for r in band:
            r["overdrive"] = bonus
        start += len(band)
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, r["student"]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--thresholds", required=True)
    ap.add_argument("--runs", required=True, help="directory with <student>/result.json")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    th = json.load(open(a.thresholds))
    entries = [{"student": p.parent.name, "result": json.load(open(p))}
               for p in sorted(pathlib.Path(a.runs).glob("*/result.json"))]
    rows = score_round(entries, th)
    out = {"round": a.round, "thresholds": th, "rows": rows}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=2)
    rerun = [r["student"] for r in rows if r["needs_rerun"]]
    if rerun:
        print("NEEDS RERUN (judge errors, not scored):", ", ".join(rerun))
    for r in rows:
        print(f"{str(r['rank'] or '—'):>3}  {r['student']:<24} S={r['S']:>8}  mark={r['mark']:<4} "
              f"OD+{r['overdrive']}  {'; '.join(r['reasons'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
