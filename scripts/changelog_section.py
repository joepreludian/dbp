#!/usr/bin/env python3
"""Print the body of one version's section from CHANGELOG.md (used for release notes)."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str:
    """Return the body under ``## [version]`` up to the next ``## `` heading.

    Raises KeyError when the section is missing.
    """
    heading = re.compile(rf"^## \[{re.escape(version)}\].*$", re.MULTILINE)
    match = heading.search(text)
    if match is None:
        raise KeyError(version)
    rest = text[match.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    body = rest if nxt is None else rest[: nxt.start()]
    return body.strip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: changelog_section.py X.Y.Z", file=sys.stderr)
        return 2
    path = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
    try:
        sys.stdout.write(section(path.read_text(encoding="utf-8"), argv[1]))
    except KeyError:
        print(f"changelog_section: no section '## [{argv[1]}]' in {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
