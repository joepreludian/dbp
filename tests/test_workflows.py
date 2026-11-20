import os
import subprocess
from pathlib import Path

import bp

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"

REQUIRED_CI = [
    "ubuntu-latest", "macos-latest", '"3.10"', '"3.14"', "python -m pytest -q",
    "git diff --exit-code bin/bp.pyz", "actions/checkout@v4", "actions/setup-python@v5",
]
REQUIRED_RELEASE = [
    '- "v*"', "contents: write", "GITHUB_REF_NAME", "SHA256SUMS", "changelog_section.py",
    "softprops/action-gh-release@v2", "git diff --exit-code bin/bp.pyz", "python -m pytest -q",
]

TAG_CHECK = (
    '[ "v$(python3 -c \'import sys; sys.path.insert(0, "src"); import bp; print(bp.__version__)\')"'
    ' = "$GITHUB_REF_NAME" ]'
)


def test_ci_workflow_contents():
    text = CI.read_text()
    for needle in REQUIRED_CI:
        assert needle in text, needle


def test_release_workflow_contents():
    text = RELEASE.read_text()
    for needle in REQUIRED_RELEASE:
        assert needle in text, needle
    assert TAG_CHECK in text


def test_workflows_have_sane_yaml_shape():
    for path in (CI, RELEASE):
        for line in path.read_text().splitlines():
            assert "\t" not in line, (path.name, line)
            indent = len(line) - len(line.lstrip(" "))
            assert indent % 2 == 0, (path.name, line)


def test_release_tag_check_shell():
    def run(tag):
        return subprocess.run(
            ["bash", "-c", TAG_CHECK], cwd=ROOT, env={**os.environ, "GITHUB_REF_NAME": tag},
        ).returncode

    assert run(f"v{bp.__version__}") == 0
    assert run("v9.9.9") == 1
