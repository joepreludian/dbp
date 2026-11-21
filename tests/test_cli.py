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


def test_port_out_of_range_is_usage_error():
    for bad in ("70000", "-1"):
        with pytest.raises(UsageError):
            resolve_options(build_parser().parse_args(["write", "--port", bad]), {})


def test_build_config_show_fields(tmp_path):
    from bp.cli import Options, build_config

    f = tmp_path / "doc.markdown"
    opts = Options("show", f, "127.0.0.1", "localhost", 0, None, None, True, None)
    cfg = build_config(opts, "héllo", "T")
    assert cfg["file_size"] == 6 and cfg["is_markdown"] is True
    assert cfg["file_path"] == str(f) and cfg["file_name"] == "doc.markdown"


def test_build_config_non_markdown():
    from bp.cli import Options, build_config

    opts = Options("show", Path("notes.txt"), "127.0.0.1", "localhost", 0, None, None, True, None)
    assert build_config(opts, "x", "T")["is_markdown"] is False


def test_repo_slug_forms():
    from bp.cli import repo_slug

    assert repo_slug("git@github.com:joepreludian/dbp.git") == "joepreludian/dbp"
    assert repo_slug("https://github.com/joepreludian/dbp.git") == "joepreludian/dbp"
    assert repo_slug("https://github.com/joepreludian/dbp") == "joepreludian/dbp"
    assert repo_slug("ssh://git@host/owner/repo/") == "owner/repo"


def test_repo_slug_odd_urls():
    from bp.cli import repo_slug

    assert repo_slug("file:///repo") is None
    assert repo_slug("repo") is None
    assert repo_slug("") is None


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "init")
    return tmp_path


def test_detect_context_plain_directory(tmp_path):
    from bp.cli import detect_context

    d = tmp_path / "plain"
    d.mkdir()
    assert detect_context(d) == {"folder": "plain", "path": str(d), "repo": None, "branch": None}


def test_detect_context_repo_with_remote(tmp_path):
    from bp.cli import detect_context

    repo = _repo(tmp_path)
    _git(repo, "remote", "add", "origin", "git@github.com:joepreludian/dbp.git")
    ctx = detect_context(repo)
    assert ctx["repo"] == "joepreludian/dbp" and ctx["branch"] == "main"
    assert ctx["folder"] == tmp_path.name


def test_detect_context_repo_without_remote(tmp_path):
    from bp.cli import detect_context

    ctx = detect_context(_repo(tmp_path))
    assert ctx["repo"] is None and ctx["branch"] == "main"


def test_detect_context_detached_head(tmp_path):
    from bp.cli import detect_context

    repo = _repo(tmp_path)
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    _git(repo, "checkout", "-q", "--detach")
    assert detect_context(repo)["branch"] == sha


def test_detect_context_without_git(tmp_path, monkeypatch):
    from bp.cli import detect_context

    monkeypatch.setenv("PATH", "")
    assert detect_context(tmp_path)["repo"] is None


def test_detect_context_timeout_falls_back(tmp_path, monkeypatch):
    import bp.cli as cli

    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 0))

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli.detect_context(tmp_path) == {"folder": tmp_path.name, "path": str(tmp_path), "repo": None, "branch": None}
    assert len(calls) == 1


def test_build_config_includes_context(tmp_path):
    from bp.cli import Options, build_config

    opts = Options("write", None, "127.0.0.1", "localhost", 0, None, None, True, None)
    ctx = {"folder": "f", "path": "/f", "repo": None, "branch": None}
    assert build_config(opts, None, "T", context=ctx)["context"] == ctx
    assert set(build_config(opts, None, "T")["context"]) == {"folder", "path", "repo", "branch"}


def test_repo_slug_never_includes_userinfo_or_port():
    from bp.cli import repo_slug

    assert repo_slug("https://user:s3cret@git.example.com/repo.git") is None
    assert repo_slug("https://oauth2:tok@gitlab.com/group/project.git") == "group/project"
    assert repo_slug("ssh://git@host:22/repo") is None
    assert repo_slug("ssh://git@host:22/owner/repo.git") == "owner/repo"
    assert repo_slug("https://host/a/b/c/repo") == "c/repo"
    assert repo_slug("/home/me/repos/foo") == "repos/foo"
    assert repo_slug("git@github.com:joepreludian/dbp.git") == "joepreludian/dbp"


def test_detect_context_shares_one_deadline(tmp_path, monkeypatch):
    import bp.cli as cli

    calls = []

    class Done:
        returncode = 0
        stdout = "true\n"

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if len(calls) == 1:
            return Done()
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 0))

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    ctx = cli.detect_context(tmp_path)
    assert ctx["repo"] is None and ctx["branch"] is None
    assert len(calls) == 2
