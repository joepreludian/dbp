import json
import os
import re
import signal
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from bp.cli import Options, should_open_browser, write_output_atomic

SRC = Path(__file__).resolve().parents[1] / "src"
URL_RE = re.compile(r"Beautiful Prompter is waiting at (http://([^:/]+):(\d+)/\?k=([A-Za-z0-9_-]+))\n")


def start(*args, env=None):
    full_env = dict(os.environ, PYTHONUNBUFFERED="1", **(env or {}))
    for key in ("BP_BIND", "BP_URL_HOST", "BP_PORT"):
        full_env.pop(key, None) if not (env and key in env) else None
    proc = subprocess.Popen(
        [sys.executable, "-m", "bp", *args, "--no-open"],
        cwd=SRC, env=full_env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    line = proc.stderr.readline().decode()
    m = URL_RE.fullmatch(line)
    assert m, f"unexpected stderr line: {line!r}"
    return proc, m.group(1), m.group(2), int(m.group(3)), m.group(4)


def post(port, path, obj):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return res.status


def finish(proc):
    out, err = proc.communicate(timeout=10)
    return proc.returncode, out, err


def test_write_answer_to_stdout_and_file(tmp_path):
    answer_file = tmp_path / "a.md"
    proc, _, _, port, token = start("write", "--output", str(answer_file))
    assert post(port, "/answer", {"k": token, "text": "olá 🚀\n"}) == 200
    code, out, err = finish(proc)
    assert code == 0
    assert out == "olá 🚀\n".encode("utf-8")
    assert answer_file.read_bytes() == out


def test_url_line_format():
    proc, url, host, port, token = start("write")
    assert host == "localhost" and port > 0 and len(token) >= 32
    proc.send_signal(signal.SIGINT)
    finish(proc)


def test_url_host_from_env():
    proc, url, host, port, _ = start("write", env={"BP_URL_HOST": "box.local"})
    assert host == "box.local"
    proc.send_signal(signal.SIGINT)
    finish(proc)


def test_cancel_exit_1_no_output(tmp_path):
    answer_file = tmp_path / "a.md"
    proc, _, _, port, token = start("write", "--output", str(answer_file))
    assert post(port, "/cancel", {"k": token}) == 200
    code, out, _ = finish(proc)
    assert code == 1 and out == b"" and not answer_file.exists()


def test_timeout_exit_124(tmp_path):
    answer_file = tmp_path / "a.md"
    proc, *_ = start("write", "--timeout", "0.3", "--output", str(answer_file))
    code, out, _ = finish(proc)
    assert code == 124 and out == b"" and not answer_file.exists()


def test_sigint_exit_130():
    proc, *_ = start("write")
    proc.send_signal(signal.SIGINT)
    code, out, _ = finish(proc)
    assert code == 130 and out == b""


def test_port_in_use_exit_2():
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    port = holder.getsockname()[1]
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "bp", "write", "--port", str(port), "--no-open"],
            cwd=SRC, capture_output=True, timeout=10,
        )
    finally:
        holder.close()
    assert proc.returncode == 2 and b"port" in proc.stderr


def test_show_mode_serves_document(tmp_path):
    doc = tmp_path / "spec.md"
    doc.write_text("# Spec\n\nHello </script>", encoding="utf-8")
    proc, url, _, port, token = start("show", str(doc))
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/?k={token}", timeout=5) as res:
        html = res.read().decode()
    assert '"mode": "show"' in html and "\\u003c/script>" in html and "spec.md" in html
    assert post(port, "/answer", {"k": token, "text": "fine"}) == 200
    code, out, _ = finish(proc)
    assert code == 0 and out == b"fine"


def test_write_output_atomic_replaces_existing(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("old")
    write_output_atomic(target, "new ✓")
    assert target.read_text(encoding="utf-8") == "new ✓"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    "url_host,open_flag,expected",
    [("localhost", True, True), ("127.0.0.1", True, True), ("box.local", True, False), ("localhost", False, False)],
)
def test_should_open_browser(url_host, open_flag, expected):
    opts = Options("write", None, "127.0.0.1", url_host, 0, None, None, open_flag, None)
    assert should_open_browser(opts) is expected


def test_output_parent_dir_is_created(tmp_path):
    answer_file = tmp_path / "missing" / "deeper" / "a.md"
    proc, _, _, port, token = start("write", "--output", str(answer_file))
    assert post(port, "/answer", {"k": token, "text": "kept"}) == 200
    code, out, _ = finish(proc)
    assert code == 0 and out == b"kept" and answer_file.read_bytes() == b"kept"


def test_unwritable_output_is_usage_error_before_serving():
    proc = subprocess.run(
        [sys.executable, "-m", "bp", "write", "--no-open", "--output", "/dev/null/sub/a.md"],
        cwd=SRC, capture_output=True, timeout=10,
    )
    assert proc.returncode == 2
    assert b"output" in proc.stderr and b"waiting at" not in proc.stderr


def test_open_browser_does_not_block(monkeypatch):
    import time
    from bp import cli

    def slow_open(url):
        time.sleep(2)
        return True

    monkeypatch.setattr(cli.webbrowser, "open", slow_open)
    started = time.monotonic()
    cli.open_browser("http://localhost:1/")
    assert time.monotonic() - started < 0.5


@pytest.mark.parametrize("info,ok", [((3, 10, 0), True), ((3, 14, 4), True), ((3, 9, 6), False), ((3, 8, 10), False)])
def test_python_version_ok(info, ok):
    from bp.cli import python_version_ok
    assert python_version_ok(info) is ok
