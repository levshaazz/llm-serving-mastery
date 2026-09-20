#!/usr/bin/env bash
# Read-only judge-host preflight.
# Usage: judge/preflight.sh reference 1 | judge/preflight.sh grading 1
set -euo pipefail
cd "$(dirname "$0")/.."

MODE=${1:-reference}
ROUND=${2:-1}
[[ "$MODE" == reference || "$MODE" == grading ]] || { echo "mode must be reference or grading" >&2; exit 2; }
[[ "$ROUND" =~ ^[0-9]+$ ]] || { echo "round must be an integer" >&2; exit 2; }
N=$(printf '%02d' "$ROUND")

fail() { echo "[FAIL] $*" >&2; exit 1; }
ok() { echo "[ OK ] $*"; }
need() { command -v "$1" >/dev/null || fail "missing command: $1"; }

[[ "$(uname -s)" == Linux ]] || fail "judge requires Linux"
[[ "$(uname -m)" == x86_64 ]] || fail "judge lock targets Linux x86_64"
for cmd in git uv python3 docker nvidia-smi ss; do need "$cmd"; done
ok "required host commands"

python3 - <<'PY' || exit 1
import importlib.metadata, sys
assert sys.version_info[:2] == (3, 12), f"judge requires Python 3.12, got {sys.version.split()[0]}"
expected = {"lm_eval": "0.4.13", "guidellm": "0.7.4", "datasets": "4.4.1",
            "transformers": "4.51.3", "PyYAML": "6.0.2"}
for distribution, version in expected.items():
    got = importlib.metadata.version(distribution)
    assert got == version, f"{distribution}: expected {version}, got {got}"
print("[ OK ] Python 3.12 and pinned top-level judge packages")
PY

git diff --quiet && git diff --cached --quiet || fail "tracked judge checkout is dirty"
[[ -z "$(git ls-files --others --exclude-standard)" ]] || fail "untracked files present; provenance would be ambiguous"
ok "clean judge checkout at $(git rev-parse --short HEAD)"

docker info >/dev/null 2>&1 || fail "Docker daemon unavailable"
python3 - <<'PY' || exit 1
import subprocess
r = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,display_active',
                    '--format=csv,noheader,nounits'], text=True, capture_output=True)
assert r.returncode == 0 and r.stdout.strip(), 'NVIDIA GPU unavailable'
rows = [line.split(', ') for line in r.stdout.strip().splitlines()]
assert len(rows) == 1, f'judge contract requires exactly one visible GPU, got {len(rows)}'
name, total, used, display = rows[0]
assert 'RTX 5070 Ti' in name, f'judge contract expects RTX 5070 Ti, got {name}'
assert int(used) <= 600, f'GPU is not idle: {used} MiB in use'
assert display.lower() in ('disabled', 'off', 'no'), f'judge GPU drives a display: {display}'
print(f'[ OK ] {name}: {total} MiB total, {used} MiB used, display {display}')
PY
[[ -z "$(ss -ltnH 'sport = :8000')" ]] || fail "port 8000 is already in use"
ok "judge GPU contract and port 8000"

python3 - <<'PY' || exit 1
import json, subprocess, yaml
cfg = yaml.safe_load(open('judge/config.yaml'))
network = cfg['server']['measurement_network']
r = subprocess.run(['docker', 'network', 'inspect', network], text=True, capture_output=True)
assert r.returncode == 0, f"missing Docker network {network!r}; create it with --internal"
assert json.loads(r.stdout)[0].get('Internal') is True, f"Docker network {network!r} is not internal"
image = cfg['server']['sandbox_image']
r = subprocess.run(['docker', 'image', 'inspect', image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
assert r.returncode == 0, f"missing pinned sandbox image {image}; docker pull it"
print(f"[ OK ] internal network {network} and pinned sandbox image")
PY

IMAGE=$(python3 - <<'PY'
import yaml
print(yaml.safe_load(open('judge/config.yaml'))['server']['sandbox_image'])
PY
)
NETWORK=$(python3 - <<'PY'
import yaml
print(yaml.safe_load(open('judge/config.yaml'))['server']['measurement_network'])
PY
)
docker run --rm --gpus all --network none "$IMAGE" nvidia-smi -L >/dev/null \
  || fail "NVIDIA Container Toolkit preflight failed"
if docker run --rm --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit 64 --network "$NETWORK" "$IMAGE" python -c \
  "import socket; s=socket.create_connection(('1.1.1.1',80),5); s.close()" >/dev/null 2>&1; then
  fail "measurement container has external TCP egress"
fi
ok "NVIDIA containers work and measurement egress is blocked"

python3 judge/test_score.py >/dev/null
ok "judge unit tests"

python3 - "$MODE" "$N" <<'PY'
import json, pathlib, sys, yaml
mode, n = sys.argv[1:]
cfg = yaml.safe_load(open('judge/config.yaml'))
assert cfg['version'] == 3, f"expected config v3, got {cfg['version']}"
if mode == 'grading':
    roster = pathlib.Path('judge/roster.csv')
    assert roster.is_file(), 'missing private judge/roster.csv'
    th = json.load(open(f'judge/thresholds/round-{n}.json'))
    assert th.get('verified') is True, f'round {n} thresholds are not verified'
    assert th.get('judge_provenance', {}).get('complete') is True, 'threshold provenance is incomplete'
print(f"[ OK ] config v{cfg['version']} and {mode} contract for round {n}")
PY

echo "preflight passed"
