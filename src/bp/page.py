"""Render the single page: load the template, embed the run configuration safely."""

from __future__ import annotations

import json
from importlib import resources

PLACEHOLDER = "__BP_CONFIG__"


def embed_json(obj: object) -> str:
    """JSON that is safe inside <script type="application/json">.

    Every "<" becomes "\\u003c", so neither "</script>" nor "<!--" can appear in
    the output while the text still parses to the same value.
    """
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


def load_template() -> str:
    return resources.files("bp").joinpath("page.html").read_text(encoding="utf-8")


def render_page(config: dict) -> str:
    return load_template().replace(PLACEHOLDER, embed_json(config))
