import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYZ = ROOT / "bin" / "bp.pyz"
SRC = ROOT / "src" / "bp"


def test_pyz_help():
    r = subprocess.run([sys.executable, str(PYZ), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "write" in r.stdout and "show" in r.stdout


def test_pyz_is_executable_with_shebang():
    assert PYZ.stat().st_mode & 0o111
    assert PYZ.read_bytes().startswith(b"#!/usr/bin/env python3\n")


def test_pyz_matches_source():
    with zipfile.ZipFile(PYZ) as zf:
        names = set(zf.namelist())
        for path in SRC.rglob("*"):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            rel = f"bp/{path.relative_to(SRC).as_posix()}"
            assert rel in names, rel
            assert zf.read(rel) == path.read_bytes(), rel
        assert not any("__pycache__" in n for n in names)


def test_pyz_write_timeout_exit_124():
    r = subprocess.run(
        [sys.executable, str(PYZ), "write", "--timeout", "0.3", "--no-open", "--port", "0"],
        capture_output=True, timeout=15,
    )
    assert r.returncode == 124 and r.stdout == b""
    assert b"Beautiful Prompter is waiting at http://localhost:" in r.stderr
