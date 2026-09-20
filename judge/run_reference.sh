#!/usr/bin/env bash
# Create or publish a config-v3 reference calibration from submission-template.
# First run: judge/run_reference.sh 1 'note'
# After review: PUBLISH_REFERENCE=1 judge/run_reference.sh 1 'same note'
set -euo pipefail
cd "$(dirname "$0")/.."

ROUND=${1:?usage: judge/run_reference.sh ROUND NOTE}
NOTE=${2:?usage: judge/run_reference.sh ROUND NOTE}
[[ "$ROUND" =~ ^[0-9]+$ ]] || { echo "round must be an integer" >&2; exit 2; }
N=$(printf '%02d' "$ROUND")
: "${JUDGE_SEED:?set the private round seed; use the same value for reference and submissions}"
: "${JUDGE_EGRESS_BLOCKED:?verify the internal network, then set JUDGE_EGRESS_BLOCKED=1}"

BASE="judge/rounds/round-$N/reference"
REPO="$BASE/repository"
RUN="$BASE/run"
CANDIDATE="$BASE/thresholds.candidate.json"

if [[ "${PUBLISH_REFERENCE:-0}" == 1 ]]; then
  [[ -f "$RUN/result.json" && -f "$CANDIDATE" ]] || {
    echo "no reviewed private reference for round $N; run without PUBLISH_REFERENCE first" >&2; exit 1; }
  judge/preflight.sh reference "$ROUND"
  python3 - "$RUN/result.json" "$CANDIDATE" <<'PY'
import json, sys
result, threshold = map(lambda p: json.load(open(p)), sys.argv[1:])
assert result.get('ok') is True and result.get('judge_error') is False, 'reference run did not succeed'
assert result.get('config_version') == 3, 'reference is not config v3'
assert result.get('provenance', {}).get('complete') is True, 'reference provenance is incomplete'
assert threshold.get('verified') is True, 'candidate threshold is not verified'
PY
  python3 - "$RUN/result.json" "judge/reference/round-$N.v3.result.json" <<'PY'
import copy, json, sys
result = json.load(open(sys.argv[1]))
public = copy.deepcopy(result)
fetch = public.get('steps', {}).get('fetch', {})
if 'repo' in fetch:
    fetch['repo'] = '<generated from tracked submission-template>'
json.dump(public, open(sys.argv[2], 'w'), indent=2)
PY
  cp "$CANDIDATE" "judge/thresholds/round-$N.json"
  echo "published reviewed reference and verified thresholds for round $N"
  echo "run npm run check, review git diff, commit, and push before opening the round"
  exit 0
fi

[[ ! -e "$BASE" ]] || {
  echo "$BASE already exists; review it, publish it, or move it aside before a new expensive run" >&2; exit 1; }

judge/preflight.sh reference "$ROUND"
mkdir -p "$REPO"
cp -R submission-template/. "$REPO/"
git -C "$REPO" init -q
git -C "$REPO" config user.name 'LLM Serving Mastery reference'
git -C "$REPO" config user.email 'reference@localhost'
git -C "$REPO" add .
git -C "$REPO" commit -q -m 'Frozen reference submission'
SHA=$(git -C "$REPO" rev-parse HEAD)

python3 judge/run_submission.py --repo "$REPO" --ref "$SHA" --out "$RUN" --sandbox docker
python3 - "$RUN/result.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
assert r.get('ok') is True and r.get('judge_error') is False, r.get('error')
assert r.get('config_version') == 3, 'reference is not config v3'
assert r.get('provenance', {}).get('complete') is True, 'reference provenance is incomplete'
canary = r.get('steps', {}).get('canary', {})
for key in ('similarity_min', 'short_outputs', 'unique_output_share'):
    assert key in canary, f'missing canary evidence: {key}'
print('reference result passed structural validation')
PY

python3 judge/make_thresholds.py --round "$ROUND" --reference "$RUN/result.json" \
  --note "$NOTE" --out "$CANDIDATE"
python3 - "$CANDIDATE" <<'PY'
import json, sys
t = json.load(open(sys.argv[1]))
assert t.get('verified') is True
assert t.get('judge_provenance', {}).get('complete') is True
print('verified threshold candidate created')
PY

echo "private reference complete: $RUN"
echo "candidate thresholds: $CANDIDATE"
echo "review every artifact, then rerun with PUBLISH_REFERENCE=1 to promote the reviewed files"
