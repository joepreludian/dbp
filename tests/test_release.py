import importlib.util
import json
from pathlib import Path

import pytest

import bp

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/joepreludian/dbp"

_spec = importlib.util.spec_from_file_location("changelog_section", ROOT / "scripts" / "changelog_section.py")
changelog_section = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(changelog_section)
section = changelog_section.section


def _json(rel):
    return json.loads((ROOT / rel).read_text())


def test_license_is_gplv3():
    text = (ROOT / "LICENSE").read_text()
    assert "GNU GENERAL PUBLIC LICENSE" in text and "Version 3, 29 June 2007" in text


def test_plugin_manifest_publishing_fields():
    m = _json(".claude-plugin/plugin.json")
    assert m["license"] == "GPL-3.0-or-later"
    assert m["homepage"] == REPO_URL and m["repository"] == REPO_URL
    assert m["keywords"]


def test_marketplace_matches_plugin():
    mk = _json(".claude-plugin/marketplace.json")
    plugin = _json(".claude-plugin/plugin.json")
    assert mk["name"] == "joepreludian" and mk["owner"]["name"]
    assert mk["plugins"][0]["name"] == plugin["name"] == "beautiful-prompter"
    assert mk["plugins"][0]["source"] == "./"


def test_pyproject_license():
    text = (ROOT / "pyproject.toml").read_text()
    assert 'license = "GPL-3.0-or-later"' in text and REPO_URL in text


def test_changelog_has_unreleased_and_current():
    text = (ROOT / "CHANGELOG.md").read_text()
    assert "## [Unreleased]" in text and f"## [{bp.__version__}]" in text


def test_changelog_section_extracts_and_fails():
    text = (ROOT / "CHANGELOG.md").read_text()
    body = section(text, "0.1.1")
    assert body.strip() and "## [0.1.1]" not in body and "## [0.1.0]" not in body
    with pytest.raises(KeyError):
        section(text, "9.9.9")


def test_readme_install_commands():
    readme = (ROOT / "README.md").read_text()
    for needle in [
        "/plugin marketplace add joepreludian/dbp",
        "/plugin install beautiful-prompter@joepreludian",
        "claude --plugin-dir",
        "scripts/release.sh",
        "GPL",
    ]:
        assert needle in readme, needle
