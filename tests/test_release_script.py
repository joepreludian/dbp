"""scripts/release.sh is exercised against a fresh clone so the real checkout is never touched."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# release.sh runs the suite itself; without this guard these tests would recurse.
pytestmark = pytest.mark.skipif(bool(os.environ.get("BP_RELEASE_INNER")), reason="inside release.sh")


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=check)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "r"
    subprocess.run(["git", "clone", "-q", str(ROOT), str(path)], check=True)
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "checkout", "-q", "-B", "main")
    # Exercise the scripts as they are in the working tree, not as last committed.
    shutil.copytree(ROOT / "scripts", path / "scripts", dirs_exist_ok=True)
    git(path, "add", "scripts")
    if git(path, "status", "--porcelain").stdout:
        git(path, "commit", "-q", "-m", "test: sync scripts from working tree")
    return path


def release(repo, version):
    return subprocess.run(
        ["bash", "scripts/release.sh", version], cwd=repo, capture_output=True, text=True,
    )


def prepare_changelog(repo, version):
    text = (repo / "CHANGELOG.md").read_text()
    text = text.replace("## [Unreleased]\n", f"## [Unreleased]\n\n## [{version}] - 2026-11-20\n", 1)
    (repo / "CHANGELOG.md").write_text(text)
    git(repo, "add", "CHANGELOG.md")
    git(repo, "commit", "-q", "-m", f"docs: changelog for {version}")


def current_version(repo):
    return re.search(r'__version__ = "([^"]+)"', (repo / "src/bp/__init__.py").read_text()).group(1)


def test_release_refuses_dirty_tree(repo):
    (repo / "README.md").write_text("dirty\n")
    r = release(repo, "9.0.0")
    assert r.returncode == 2 and "dirty" in r.stderr.lower()


def test_release_refuses_non_main(repo):
    git(repo, "checkout", "-q", "-b", "other")
    r = release(repo, "9.0.0")
    assert r.returncode == 2 and "main" in r.stderr


def test_release_refuses_lower_or_malformed_version(repo):
    assert release(repo, "0.0.1").returncode == 2
    assert release(repo, current_version(repo)).returncode == 2
    assert release(repo, "1.2").returncode == 2
    assert git(repo, "status", "--porcelain").stdout == ""


def test_release_refuses_missing_changelog_section(repo):
    r = release(repo, "9.0.0")
    assert r.returncode == 2 and "9.0.0" in r.stderr and "CHANGELOG" in r.stderr


def test_release_refuses_unreleased_entries(repo):
    text = (repo / "CHANGELOG.md").read_text()
    # Give Unreleased an entry of its own, then add the target section below it.
    text = text.replace("## [Unreleased]\n", "## [Unreleased]\n\n- not yet moved\n", 1)
    text = text.replace("## [0.1.1]", "## [9.0.0] - 2026-11-20\n\n- stuff\n\n## [0.1.1]", 1)
    (repo / "CHANGELOG.md").write_text(text)
    git(repo, "commit", "-q", "-am", "test")
    r = release(repo, "9.0.0")
    assert r.returncode == 2 and "Unreleased" in r.stderr


def test_release_creates_commit_and_tag(repo):
    prepare_changelog(repo, "9.0.0")
    r = release(repo, "9.0.0")
    assert r.returncode == 0, r.stderr + r.stdout[-3000:]
    assert git(repo, "describe", "--exact-match", "HEAD").stdout.strip() == "v9.0.0"
    assert git(repo, "log", "-1", "--format=%s").stdout.strip() == "chore: release 9.0.0"
    assert current_version(repo) == "9.0.0"
    assert json.loads((repo / ".claude-plugin/plugin.json").read_text())["version"] == "9.0.0"
    assert git(repo, "status", "--porcelain").stdout == ""
    assert "git push origin main" in r.stdout and "git push origin v9.0.0" in r.stdout
