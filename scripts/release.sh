#!/usr/bin/env bash
# Cut a release locally: bump the version, rebuild, test, commit, tag. Never pushes.
# Usage: bash scripts/release.sh X.Y.Z
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

die() { echo "release: $*" >&2; exit 2; }

[ $# -eq 1 ] || die "usage: release.sh X.Y.Z"
new="$1"
[[ "$new" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version must look like X.Y.Z, got '$new'"

[ -z "$(git status --porcelain)" ] || die "working tree is dirty; commit or stash first"
branch="$(git branch --show-current)"
[ "$branch" = "main" ] || die "releases are cut from main, you are on '$branch'"

# Read the version with a regex, not an import: importing writes a .pyc whose
# mtime/size check would accept the sed-edited source below as unchanged.
current="$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' src/bp/__init__.py)"
[ -n "$current" ] || die "could not read __version__ from src/bp/__init__.py"
highest="$(printf '%s\n%s\n' "$current" "$new" | sort -V | tail -n1)"
{ [ "$highest" = "$new" ] && [ "$new" != "$current" ]; } || die "new version $new must be greater than current $current"

python3 scripts/changelog_section.py "$new" >/dev/null 2>&1 || die "CHANGELOG.md has no '## [$new]' section; move the Unreleased entries there first"
unreleased="$(python3 scripts/changelog_section.py Unreleased 2>/dev/null | tr -d '[:space:]')"
[ -z "$unreleased" ] || die "CHANGELOG.md still has entries under '## [Unreleased]'; move them under '## [$new]'"

echo "release: $current -> $new"
sed -i.bak -E "s/^__version__ = \"[^\"]+\"/__version__ = \"$new\"/" src/bp/__init__.py && rm -f src/bp/__init__.py.bak
sed -i.bak -E "s/\"version\": \"[^\"]+\"/\"version\": \"$new\"/" .claude-plugin/plugin.json && rm -f .claude-plugin/plugin.json.bak
grep -q "__version__ = \"$new\"" src/bp/__init__.py || die "failed to set version in src/bp/__init__.py"
grep -q "\"version\": \"$new\"" .claude-plugin/plugin.json || die "failed to set version in plugin.json"

find src tests -name __pycache__ -type d -prune -exec rm -rf {} +
bash scripts/build.sh
BP_RELEASE_INNER=1 python3 -m pytest -q

git add src/bp/__init__.py .claude-plugin/plugin.json bin/bp.pyz
git commit -q -m "chore: release $new"
git tag -a "v$new" -m "$new"

cat <<MSG

Released $new locally. To publish, run:

  git push origin main
  git push origin v$new

MSG
