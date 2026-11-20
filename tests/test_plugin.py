import json
from pathlib import Path

import bp

ROOT = Path(__file__).resolve().parents[1]


def test_plugin_manifest_version_matches():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "beautiful-prompter"
    assert manifest["version"] == bp.__version__


def test_skill_frontmatter_and_contract():
    text = (ROOT / "skills" / "beautiful-prompter" / "SKILL.md").read_text()
    assert text.startswith("---\nname: beautiful-prompter\ndescription: ")
    assert '${CLAUDE_PLUGIN_ROOT}/bin/bp.pyz' in text
    assert "--output" in text and "run_in_background" in text
    for code in ("124", "exit code"):
        assert code in text.lower() or code in text
    assert "--bind" in text and "--url-host" in text


def _skill():
    return (ROOT / "skills" / "beautiful-prompter" / "SKILL.md").read_text()


def test_skill_description_offers_show_after_documents():
    text = _skill()
    frontmatter = text.split("---")[1]
    assert "right after producing a document" in frontmatter


def test_skill_exit_codes_include_130():
    assert "| 130 |" in _skill()


def test_skill_mentions_auto_open():
    assert "opens a browser tab itself" in _skill()


def test_skill_show_example_is_absolute():
    text = _skill()
    show_lines = [l for l in text.splitlines() if "bp.pyz\" show " in l]
    assert show_lines and all(" show /" in l for l in show_lines), show_lines
