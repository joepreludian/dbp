"""A token-gated HTTP server that serves one page and accepts one answer."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from bp.page import render_page

MAX_BODY_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class Outcome:
    kind: Literal["answer", "cancel", "timeout"]
    text: str | None = None


class _Handler(BaseHTTPRequestHandler):
    server: "_Server"
    timeout = 30  # seconds of socket inactivity before a stalled client is dropped

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        pass

    # --- helpers -----------------------------------------------------------

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _send_json(self, status: HTTPStatus, obj: dict) -> None:
        self._send(status, json.dumps(obj).encode("utf-8"), "application/json")

    def _content_length(self) -> int | None:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None
        return length if length >= 0 else None

    def _read_json(self, length: int) -> dict | None:
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    # --- routes ------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        parts = urlsplit(self.path)
        token = parse_qs(parts.query).get("k", [None])[0]
        if token != self.server.token:
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "forbidden"})
            return
        if parts.path != "/":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        self._send(HTTPStatus.OK, self.server.page, "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        path = urlsplit(self.path).path
        if path not in ("/answer", "/cancel"):
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        length = self._content_length()
        if length is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing or invalid Content-Length"})
            return
        if length > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": "body too large"})
            return
        body = self._read_json(length)
        if body is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "malformed JSON body"})
            return
        if body.get("k") != self.server.token:
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "forbidden"})
            return
        if path == "/answer":
            text = body.get("text")
            if not isinstance(text, str):
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "text must be a string"})
                return
            outcome = Outcome("answer", text)
        else:
            outcome = Outcome("cancel", None)
        if not self.server.resolve(outcome):
            self._send_json(HTTPStatus.CONFLICT, {"ok": False, "error": "already answered"})
            return
        self._send_json(HTTPStatus.OK, {"ok": True})
        self.server.done.set()


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True  # a fixed BP_PORT must work again right after a run exits

    def __init__(self, address: tuple[str, int], token: str, page: bytes) -> None:
        super().__init__(address, _Handler)
        self.token = token
        self.page = page
        self.done = threading.Event()
        self.outcome: Outcome | None = None
        self._lock = threading.Lock()

    def resolve(self, outcome: Outcome) -> bool:
        """Record the outcome if none is recorded yet. First caller wins."""
        with self._lock:
            if self.outcome is not None:
                return False
            self.outcome = outcome
            return True


class PrompterServer:
    """Serve the page on ``bind:port`` and wait for exactly one answer or cancel."""

    def __init__(self, config: dict, bind: str, port: int) -> None:
        self.token: str = config["token"]
        page = render_page(config).encode("utf-8")
        self._server = _Server((bind, port), self.token, page)
        self.port: int = self._server.server_address[1]
        self._thread: threading.Thread | None = None
        self._closed = False

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def wait(self, timeout: float | None) -> Outcome:
        self._server.done.wait(timeout)
        self.close()
        return self._server.outcome or Outcome("timeout", None)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._thread is not None:
            self._server.shutdown()
            self._thread.join()
        self._server.server_close()
