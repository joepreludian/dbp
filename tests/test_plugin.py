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
