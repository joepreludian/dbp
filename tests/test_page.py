import json

from bp.page import embed_json, render_page

WRITE = {"mode": "write", "token": "T", "title": None, "version": "0"}
SHOW = {
    "mode": "show", "token": "T", "title": None, "version": "0",
    "document": "# Hi </script><!-- x", "file_name": "a.md", "file_size": 12, "is_markdown": True,
}
IDS = ["editor", "preview", "answer", "send", "cancel", "theme-toggle", "count", "error", "idle", "document"]


def test_embed_json_escapes_script_close():
    out = embed_json({"d": "</script><!-- x"})
    assert "</" not in out and "<!--" not in out
    assert json.loads(out) == {"d": "</script><!-- x"}


def test_render_write_has_config_and_assets():
    html = render_page(WRITE)
    assert 'id="bp-config"' in html
    assert json.loads(_config_block(html)) == WRITE
    assert "https://cdn.tailwindcss.com/3.4.17?plugins=typography" in html
    assert "https://cdnjs.cloudflare.com/ajax/libs/marked/15.0.7/marked.min.js" in html


def test_render_show_embeds_document_safely():
    html = render_page(SHOW)
    block = _config_block(html)
    assert "</script>" not in block and "<!--" not in block
    assert json.loads(block)["document"] == SHOW["document"]


def test_required_elements_present():
    for cfg in (WRITE, SHOW):
        html = render_page(cfg)
        for i in IDS:
            assert f'id="{i}"' in html, i


def test_copy_from_spec_present():
    html = render_page(WRITE)
    for text in [
        "Send this to Claude? You won't be able to edit it afterwards.",
        "Cancel without sending?",
        "Sent. Go back to your terminal.",
        "Claude has your message. You can close this tab.",
        "Cancelled. Go back to your terminal.",
        "Beautiful Prompter",
    ]:
        assert text in html, text


def _config_block(html: str) -> str:
    start = html.index('id="bp-config"')
    start = html.index(">", start) + 1
    end = html.index("</script>", start)
    return html[start:end]


def test_hidden_attribute_beats_tailwind_display_classes():
    # Tailwind's preflight rule for [hidden] has the same specificity as .flex/.grid
    # and is emitted earlier, so without this override hidden blocks render anyway.
    html = render_page(WRITE)
    assert "[hidden] { display: none !important; }" in html
