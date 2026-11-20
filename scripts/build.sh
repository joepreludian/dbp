#!/usr/bin/env bash
# Build bin/bp.pyz, a single-file executable, from src/. Deterministic; stdlib only.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$root/scripts/build_pyz.py" --src "$root/src" --out "$root/bin/bp.pyz"
