#!/usr/bin/env bash
# Build bin/bp.pyz, a single-file executable, from src/ using only the stdlib zipapp module.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/src"
cp -R "$root/src/bp" "$stage/src/bp"
find "$stage/src" -name __pycache__ -type d -prune -exec rm -rf {} +
mkdir -p "$root/bin"
python3 -m zipapp "$stage/src" -m "bp.cli:entry" -p "/usr/bin/env python3" -o "$root/bin/bp.pyz"
chmod +x "$root/bin/bp.pyz"
echo "built $root/bin/bp.pyz ($(wc -c < "$root/bin/bp.pyz") bytes)"
