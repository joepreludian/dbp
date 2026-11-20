#!/usr/bin/env python3
"""Build bin/bp.pyz deterministically, using only the standard library.

zipapp is not reproducible: it stamps entries with current time (and local
time zone), copies the host umask into file modes, and on Python 3.10 does not
sort entries. This writer fixes every one of those so a rebuild on any OS or
Python yields identical bytes, which lets CI prove the committed artifact
matches the source.
"""

from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path

SHEBANG = b"#!/usr/bin/env python3\n"
FIXED_DATE_TIME = (2000, 1, 1, 0, 0, 0)
MAIN_PY = "from bp.cli import entry\n\nentry()\n"
FILE_MODE = 0o644
DIR_MODE = 0o755
PACKAGE = "bp"


def _entries(src_dir: Path) -> list[tuple[str, bytes | None]]:
    """(archive name, content) pairs; content None marks a directory."""
    package_dir = src_dir / PACKAGE
    items: list[tuple[str, bytes | None]] = [(f"{PACKAGE}/", None)]
    for path in package_dir.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(src_dir).as_posix()
        if path.is_dir():
            items.append((rel + "/", None))
        else:
            items.append((rel, path.read_bytes()))
    items.append(("__main__.py", MAIN_PY.encode("utf-8")))
    return sorted(items, key=lambda item: item[0])


def build(src_dir: Path, out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(SHEBANG)
        with zipfile.ZipFile(fh, "w", compression=zipfile.ZIP_STORED) as zf:
            for name, content in _entries(Path(src_dir)):
                info = zipfile.ZipInfo(name, date_time=FIXED_DATE_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3  # Unix, so external_attr carries the mode
                if content is None:
                    info.external_attr = (DIR_MODE << 16) | 0x10
                    zf.writestr(info, b"")
                else:
                    info.external_attr = FILE_MODE << 16
                    zf.writestr(info, content)
    os.chmod(out, 0o755)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, default=Path("src"))
    parser.add_argument("--out", type=Path, default=Path("bin/bp.pyz"))
    args = parser.parse_args()
    build(args.src, args.out)
    print(f"built {args.out} ({args.out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
