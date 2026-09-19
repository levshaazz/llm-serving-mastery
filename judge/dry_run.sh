#!/usr/bin/env bash
# dry_run.sh — the weekly dry run (Tuesdays): does each student's CURRENT default branch start on the judge?
#   judge/dry_run.sh
# Contract + start-up + smoke test only (no quality, no speed, nothing scored), on the judge GPU in the
# sandbox, so FP8 / NVFP4 / Blackwell-only paths get a real start-up check before Thursday. Logs are
# published to data/dry-run/<student>/.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f judge/roster.csv ] || { echo "no judge/roster.csv"; exit 1; }
PUB=data/dry-run; rm -rf "$PUB"; mkdir -p "$PUB"
exec 3< <(tail -n +2 judge/roster.csv)
while IFS=, read -r who repo <&3; do
  out="judge/rounds/dry-run/$who"
  echo "=== $who"
  python3 judge/run_submission.py --repo "$repo" --out "$out" --sandbox docker --skip-quality --skip-speed </dev/null || true
  mkdir -p "$PUB/$who"; cp "$out/result.json" "$out/serve.log" "$PUB/$who/" 2>/dev/null || true
done
exec 3<&-
echo "published → $PUB"
