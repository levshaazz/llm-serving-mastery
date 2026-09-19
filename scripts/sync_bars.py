#!/usr/bin/env python3
"""sync_bars.py — the round-1 bars slide shows exactly judge/thresholds/round-01.json.

    python3 scripts/sync_bars.py          # rewrite the numbers on the slide from the thresholds file
    python3 scripts/sync_bars.py --check  # fail if they differ (part of `npm run check`)
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLIDE = next((ROOT / "Lectures/00-introduction/parts").glob("29b-*.html"))
TH = ROOT / "judge/thresholds/round-01.json"


def rows(th):
    q = th["quality_gates"]
    return {"GSM8K": f"≥ {q['gsm8k'] * 100:.1f}%", "IFEval": f"≥ {q['ifeval'] * 100:.1f}%",
            "MMLU-Pro": f"≥ {q['mmlu_pro'] * 100:.1f}%",
            "TTFT": f"≤ {th['ttft_p95_slo_s']:.1f} s", "SBAR": f"<strong>{th['speed_bar_S']:.1f} tok/s</strong>"}


def main():
    th = json.load(open(TH))
    want, s = rows(th), SLIDE.read_text()
    new = s
    for key, val in want.items():
        pat = {"GSM8K": r"(<tr><td>GSM8K</td><td>)(.*?)(</td></tr>)",
               "IFEval": r"(<tr><td>IFEval</td><td>)(.*?)(</td></tr>)",
               "MMLU-Pro": r"(<tr><td>MMLU-Pro</td><td>)(.*?)(</td></tr>)",
               "TTFT": r"(<tr><td><span lang=\"en\">p95 TTFT at 64 clients</span></td><td>)(.*?)(</td></tr>)",
               "SBAR": r"(<td class=\"cell-good\">\\\(S_\{\\text\{bar\}\}\\\)</td><td class=\"cell-good\">)(.*?)(</td></tr>)"}[key]
        new, n = re.subn(pat, lambda m: m.group(1) + val + m.group(3), new)
        if n != 1:
            sys.exit(f"sync_bars: row {key} not found exactly once on {SLIDE.name}")
    if "--check" in sys.argv:
        if new != s or "{{" in s:
            sys.exit(f"sync_bars: {SLIDE.name} does not match {TH.relative_to(ROOT)} — run python3 scripts/sync_bars.py")
        print("✓ round-1 bars slide matches", TH.relative_to(ROOT))
        return
    SLIDE.write_text(new)
    print("updated", SLIDE.name, want)


if __name__ == "__main__":
    main()
