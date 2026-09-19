#!/usr/bin/env bash
# publish.sh — build the site and push docs/ to the gh-pages branch (GitHub Pages source).
# Used while the repo has no Actions deploy (the token lacks `workflow` scope). To switch to CI:
# move ci/deploy.yml.example → .github/workflows/deploy.yml and set Pages source to "GitHub Actions".
set -euo pipefail
cd "$(dirname "$0")/.."
npm run build
node scripts/assemble-deck.mjs check
touch docs/.nojekyll            # Astro emits _astro/; Jekyll would drop underscore dirs
tmp=$(mktemp -d)
cp -R docs/. "$tmp"
cd "$tmp"
git init -q -b gh-pages
git add -A
git -c user.name="${GIT_AUTHOR_NAME:-levshaazz}" -c user.email="${GIT_AUTHOR_EMAIL:-levshaazz@gmail.com}" commit -q -m "Publish site $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q -f "${PUBLISH_REMOTE:-https://github.com/levshaazz/llm-serving-mastery.git}" gh-pages
echo "published → https://levshaazz.github.io/llm-serving-mastery/"
