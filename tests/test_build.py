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


import importlib.util
import time

_spec = importlib.util.spec_from_file_location("build_pyz", ROOT / "scripts" / "build_pyz.py")
build_pyz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_pyz)
build = build_pyz.build


def test_build_is_reproducible(tmp_path):
    a, b = tmp_path / "a.pyz", tmp_path / "b.pyz"
    build(ROOT / "src", a)
    time.sleep(1.1)
    build(ROOT / "src", b)
    assert a.read_bytes() == b.read_bytes()


def test_entries_are_normalized():
    with zipfile.ZipFile(PYZ) as zf:
        names = zf.namelist()
        assert names == sorted(names)
        for info in zf.infolist():
            assert info.date_time == (2000, 1, 1, 0, 0, 0), info.filename
            assert info.compress_type == zipfile.ZIP_STORED, info.filename
            mode = (info.external_attr >> 16) & 0o777
            expected = 0o755 if info.filename.endswith("/") else 0o644
            assert mode == expected, (info.filename, oct(mode))
        assert zf.read("__main__.py") == b"from bp.cli import entry\n\nentry()\n"


def test_committed_pyz_matches_fresh_build(tmp_path):
    fresh = tmp_path / "f.pyz"
    build(ROOT / "src", fresh)
    assert fresh.read_bytes() == PYZ.read_bytes()
