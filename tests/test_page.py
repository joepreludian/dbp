import json

from bp.page import embed_json, render_page

CONTEXT = {"folder": "src", "path": "/x/src", "repo": "joepreludian/dbp", "branch": "main"}
WRITE = {"mode": "write", "token": "T", "title": None, "version": "0", "context": CONTEXT}
SHOW = {
    "mode": "show", "token": "T", "title": None, "version": "0",
    "document": "# Hi </script><!-- x", "file_name": "a.md", "file_size": 12, "is_markdown": True,
    "context": CONTEXT,
}
IDS = ["editor", "preview", "answer", "send", "cancel", "theme-toggle", "count", "error", "idle", "document",
       "context", "tab-write", "tab-preview"]


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


def test_listeners_attach_before_any_markdown_render():
    html = render_page(SHOW)
    script = html[html.rindex("<script>"):]
    assert script.index('addEventListener("click", send)') < script.index("renderMarkdown(doc")


def test_missing_marked_is_reported_not_fatal():
    html = render_page(SHOW)
    assert 'typeof marked' in html  # the guard that makes a missing renderer non-fatal
    assert "Couldn't load the markdown renderer" in html


def test_theme_is_remembered_in_a_cookie():
    html = render_page(WRITE)
    assert "bpTheme=" in html and "document.cookie" in html


def test_409_copy_has_no_retry():
    assert "Already answered from another tab." in render_page(WRITE)


def test_answer_box_is_resizable():
    assert "#answer { resize: vertical; }" in render_page(SHOW)


def test_meta_uses_file_path():
    assert "cfg.file_path" in render_page(SHOW)


def test_single_busy_flag_gates_send_and_cancel():
    html = render_page(WRITE)
    assert "var busy = false;" in html and "var sending" not in html


def test_write_section_is_single_column_with_tabs():
    html = render_page(WRITE)
    assert "md:grid-cols-2" not in html and "md:grid-rows-1" not in html
    section = html[html.index('id="write"'):html.index('id="show"')]
    assert 'id="tab-write"' in section and 'id="tab-preview"' in section
    assert 'id="preview" hidden' in section
    assert "max-w-3xl" in section


def test_context_render_guards_missing_context():
    html = render_page({"mode": "write", "token": "T", "title": None, "version": "0"})
    assert "cfg.context || {}" in html


def test_context_truncates():
    html = render_page(WRITE)
    header = html[html.index("<header"):html.index("</header>")]
    assert 'id="context"' in header and "truncate" in header


def test_preview_tab_uses_shared_renderer():
    html = render_page(WRITE)
    script = html[html.rindex("<script>"):]
    assert 'renderMarkdown($("preview"), $("editor").value)' in script
    assert "function showTab(" in script


def test_source_is_editor_in_write_mode_regardless_of_tab():
    html = render_page(WRITE)
    script = html[html.rindex("<script>"):]
    assert 'function source() { return cfg.mode === "write" ? $("editor") : $("answer"); }' in script
