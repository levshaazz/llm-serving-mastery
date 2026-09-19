#!/usr/bin/env bash
# publish.sh — local preflight only. Production Pages deploys are owned by
# .github/workflows/deploy.yml after a verified push to main.
set -euo pipefail
cd "$(dirname "$0")/.."
npm run build
npm run check:site
echo "local preflight passed; push main to deploy through GitHub Actions"
