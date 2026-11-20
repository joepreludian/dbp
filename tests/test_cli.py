import subprocess
import sys
from pathlib import Path

import pytest

from bp.cli import UsageError, build_parser, main, resolve_options

SRC = Path(__file__).resolve().parents[1] / "src"


def test_write_defaults():
    opts = resolve_options(build_parser().parse_args(["write"]), {})
    assert (opts.mode, opts.bind, opts.url_host, opts.port, opts.timeout, opts.open_browser) == (
        "write", "127.0.0.1", "localhost", 0, None, True,
    )
    assert opts.file is None and opts.output is None and opts.title is None


def test_env_overrides_and_flag_wins():
    args = build_parser().parse_args(["write", "--port", "5000"])
    env = {"BP_BIND": "0.0.0.0", "BP_URL_HOST": "box.local", "BP_PORT": "4000"}
    opts = resolve_options(args, env)
    assert (opts.bind, opts.url_host, opts.port) == ("0.0.0.0", "box.local", 5000)


def test_show_sets_file_and_options(tmp_path):
    f = tmp_path / "doc.md"
    args = build_parser().parse_args(
        ["show", str(f), "--timeout", "2.5", "--output", "o.md", "--no-open", "--title", "T"]
    )
    opts = resolve_options(args, {})
    assert (opts.mode, opts.file, opts.timeout, opts.output, opts.open_browser, opts.title) == (
        "show", f, 2.5, Path("o.md"), False, "T",
    )


def test_show_requires_file(capsys):
    assert main(["show"]) == 2


def test_show_missing_file(capsys, tmp_path):
    assert main(["show", str(tmp_path / "nope.md")]) == 2
    assert "nope.md" in capsys.readouterr().err


def test_show_non_utf8(tmp_path):
    p = tmp_path / "bin.md"
    p.write_bytes(b"\xff\xfe")
    assert main(["show", str(p)]) == 2


def test_bad_port_env():
    with pytest.raises(UsageError):
        resolve_options(build_parser().parse_args(["write"]), {"BP_PORT": "abc"})


def test_module_help():
    out = subprocess.run(
        [sys.executable, "-m", "bp", "--help"], capture_output=True, text=True, cwd=SRC
    )
    assert out.returncode == 0 and "write" in out.stdout and "show" in out.stdout
