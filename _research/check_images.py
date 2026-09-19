#!/usr/bin/env python3
"""Hard gate for mascot presence, bookends, palette briefs, and shipped assets."""
import ast
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "_research" / "gen_images.py"
sys.path.insert(0, str(ROOT / "_research"))
import mascots as M  # noqa: E402

LECTURE = re.compile(r"L\d+")
GREEN_OK = (
    "tübetey", "tubetey", "tubeteika", "skullcap", "no green", "never green",
    "not green", "only green", "green one", "no other green",
)


def load_jobs(text):
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "JOBS" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise SystemExit("[image-gate] JOBS not found in _research/gen_images.py")


def green_leaks(scene):
    leaks = []
    for sentence in re.split(r"(?<=[.;])\s+", scene):
        lower = sentence.lower()
        if "green" in lower and not any(token in lower for token in GREEN_OK):
            leaks.append(sentence.strip())
    return leaks


def audit(jobs):
    violations = []
    by_lecture = defaultdict(list)
    for group, filename, _aspect, has_serega, scene in jobs:
        if LECTURE.fullmatch(group):
            by_lecture[group].append((filename, bool(has_serega)))
        for leak in green_leaks(scene):
            violations.append(f"[{filename}] green outside the tübetey in brief: {leak[:100]}")
        published = ROOT / "Lectures" / "assets" / "img" / pathlib.Path(filename).with_suffix(".webp")
        if not published.exists():
            violations.append(f"[{filename}] optimized WebP is missing: {published.relative_to(ROOT)}")

    for group, entries in sorted(by_lecture.items()):
        entries.sort()
        count = sum(has_serega for _, has_serega in entries)
        ratio = count / len(entries)
        if ratio < M.SEREGA_MIN_RATIO:
            violations.append(f"[{group}] Serega ratio {ratio:.0%} < {M.SEREGA_MIN_RATIO:.0%}")
        if not entries[0][1]:
            violations.append(f"[{group}] hero plate must include Serega: {entries[0][0]}")
        if not entries[-1][1]:
            violations.append(f"[{group}] final plate must include Serega: {entries[-1][0]}")
        print(f"  {group}: {count}/{len(entries)} Serega ({ratio:.0%}); hero/final present")

    bible = M.SEREGA.lower()
    for required in ("green", "tübetey", "skullcap"):
        if required not in bible:
            violations.append(f"mascots.SEREGA no longer pins {required!r}")
    if "from mascots import SEREGA" not in GEN.read_text():
        violations.append("gen_images.py must import SEREGA from the locked mascot bible")
    return violations


def selftest():
    clean = [("L9", "L9/L9-01-x.png", "16:9", True, "No green anywhere."),
             ("L9", "L9/L9-02-x.png", "16:9", True, "The green tübetey is the only green.")]
    bad_ratio = [("L9", f"L9/L9-0{i}-x.png", "16:9", i == 1, "No green anywhere.") for i in range(1, 5)]
    # Ignore missing synthetic WebPs: the behavioral assertions target named rules.
    real_exists = pathlib.Path.exists
    pathlib.Path.exists = lambda _self: True
    try:
        ok = not audit(clean)
        bad = audit(bad_ratio)
    finally:
        pathlib.Path.exists = real_exists
    passed = ok and any("ratio" in item for item in bad) and any("final" in item for item in bad)
    print("[image-gate selftest]", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    problems = audit(load_jobs(GEN.read_text()))
    if problems:
        for problem in problems:
            print("  ✗", problem)
        raise SystemExit(1)
    print("[image-gate] PASS")
