#!/usr/bin/env bash
# run_round.sh — measure every snapshotted submission of a round, one after another, then score and publish.
#   JUDGE_SEED=<secret> judge/run_round.sh 1
# Needs: judge/rounds/round-NN/snapshot.json (judge/snapshot.py at the deadline)
#        judge/thresholds/round-NN.json      (published before the round opened)
# Private (gitignored): judge/rounds/.  Public (committed): data/leaderboard/round-NN.json and
# data/leaderboard/round-NN/<student>/ — result.json and the logs, with the secret seed and prompts removed.
set -euo pipefail
cd "$(dirname "$0")/.."
N=$(printf "%02d" "$1")
DIR=judge/rounds/round-$N
PUB=data/leaderboard/round-$N
: "${JUDGE_SEED:?set JUDGE_SEED (secret, not in git; a new one every round)}"
[ -f "$DIR/snapshot.json" ] || { echo "no $DIR/snapshot.json — run judge/snapshot.py at the deadline"; exit 1; }
[ -f "judge/thresholds/round-$N.json" ] || { echo "no judge/thresholds/round-$N.json"; exit 1; }

# the list is read from a file descriptor the submissions cannot touch (their stdin is /dev/null)
exec 3< <(python3 -c '
import json, sys
for who, s in json.load(open(sys.argv[1]))["students"].items():
    print("\x1f".join([who, s["mirror"] or "", s["commit"] or "", s["error"] or ""]))' "$DIR/snapshot.json")

# \x1f, not a tab: bash collapses consecutive whitespace separators, which would shift empty fields
while IFS=$'\x1f' read -r who mirror sha err <&3; do
  out="$DIR/runs/$who"
  mkdir -p "$out"
  if [ -z "$sha" ]; then
    python3 -c 'import json,sys; json.dump({"ok": False, "judge_error": False, "steps": {},
      "error": f"no submission at the deadline: {sys.argv[2]}"}, open(sys.argv[1], "w"))' "$out/result.json" "$err"
    continue
  fi
  for attempt in 1 2; do                      # a judge error (GPU busy, crash) is retried once, never scored
    echo "=== $who @ $sha (attempt $attempt)"
    rc=0; python3 judge/run_submission.py --repo "$mirror" --ref "$sha" --out "$out" --sandbox docker </dev/null || rc=$?
    [ "$rc" -eq 2 ] || break
  done
done
exec 3<&-

python3 judge/score.py --round "$1" --thresholds "judge/thresholds/round-$N.json" \
  --runs "$DIR/runs" --out "data/leaderboard/round-$N.json"

# publish: result.json + logs only (no src/, no prompts, no GuideLLM reports)
rm -rf "$PUB"; mkdir -p "$PUB"
for d in "$DIR"/runs/*/; do
  who=$(basename "$d"); mkdir -p "$PUB/$who"
  cp "$d/result.json" "$PUB/$who/" 2>/dev/null || true
  for f in "$d"/*.log; do [ -f "$f" ] && sed "s/$JUDGE_SEED/***/g" "$f" > "$PUB/$who/$(basename "$f")"; done
done
echo "published → $PUB (review, commit, scripts/publish.sh)"
