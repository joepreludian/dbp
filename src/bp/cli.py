"""Command-line interface: argument parsing, environment defaults, document loading."""

from __future__ import annotations

import argparse
import os
import secrets
import signal
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from bp import __version__

DEFAULT_BIND = "127.0.0.1"
DEFAULT_URL_HOST = "localhost"


class UsageError(Exception):
    """A problem with how the tool was invoked. Exit code 2."""


@dataclass
class Options:
    mode: str
    file: Path | None
    bind: str
    url_host: str
    port: int
    timeout: float | None
    output: Path | None
    open_browser: bool
    title: str | None


def _add_common(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--bind", help="address to listen on (env BP_BIND, default 127.0.0.1)")
    sub.add_argument("--url-host", help="host to print in the URL (env BP_URL_HOST, default localhost)")
    sub.add_argument("--port", type=int, help="port to listen on (env BP_PORT, default: a free port)")
    sub.add_argument("--timeout", type=float, help="give up after this many seconds")
    sub.add_argument("--output", type=Path, help="also write the answer to this file")
    sub.add_argument("--no-open", action="store_true", help="do not try to open a local browser")
    sub.add_argument("--title", help="heading shown in the page's top bar")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bp",
        description="Open a local page, wait for one answer, print it, exit.",
    )
    parser.add_argument("--version", action="version", version=f"bp {__version__}")
    subs = parser.add_subparsers(dest="mode", required=True)
    write = subs.add_parser("write", help="compose a markdown prompt in the browser")
    _add_common(write)
    show = subs.add_parser("show", help="render a file in the browser and collect an answer")
    show.add_argument("file", type=Path, help="markdown (or text) file to show")
    _add_common(show)
    return parser


def resolve_options(args: argparse.Namespace, env: Mapping[str, str]) -> Options:
    port_raw = env.get("BP_PORT", "0")
    if args.port is not None:
        port = args.port
    else:
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise UsageError(f"BP_PORT must be an integer, got {port_raw!r}") from exc
    return Options(
        mode=args.mode,
        file=getattr(args, "file", None),
        bind=args.bind or env.get("BP_BIND") or DEFAULT_BIND,
        url_host=args.url_host or env.get("BP_URL_HOST") or DEFAULT_URL_HOST,
        port=port,
        timeout=args.timeout,
        output=args.output,
        open_browser=not args.no_open,
        title=args.title,
    )


def load_document(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError as exc:
        raise UsageError(f"file not found: {path}") from exc
    except IsADirectoryError as exc:
        raise UsageError(f"not a file: {path}") from exc
    except PermissionError as exc:
        raise UsageError(f"cannot read: {path}") from exc
    except UnicodeDecodeError as exc:
        raise UsageError(f"not valid UTF-8: {path}") from exc


class _Interrupted(Exception):
    """Raised from the signal handler to unwind the wait."""


def should_open_browser(opts: Options) -> bool:
    return opts.open_browser and opts.url_host in ("localhost", "127.0.0.1")


def write_output_atomic(path: Path, text: str) -> None:
    """Write text to path so the file either exists complete or not at all."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = text.encode("utf-8")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def build_config(opts: Options, document: str | None, token: str) -> dict:
    config: dict = {"mode": opts.mode, "token": token, "title": opts.title, "version": __version__}
    if opts.mode == "show":
        assert opts.file is not None and document is not None
        config.update(
            document=document,
            file_name=opts.file.name,
            file_size=len(document.encode("utf-8")),
            is_markdown=opts.file.suffix.lower() in (".md", ".markdown"),
        )
    return config


def run(opts: Options) -> int:
    from bp.server import PrompterServer

    document = load_document(opts.file) if opts.mode == "show" else None
    token = secrets.token_urlsafe(32)
    try:
        server = PrompterServer(build_config(opts, document, token), opts.bind, opts.port)
    except OSError as exc:
        if opts.port:
            raise UsageError(f"port {opts.port} in use or unavailable on {opts.bind}") from exc
        raise UsageError(f"cannot listen on {opts.bind}: {exc}") from exc

    def on_signal(signum: int, frame: object) -> None:
        raise _Interrupted()

    previous = {sig: signal.signal(sig, on_signal) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        server.start()
        url = f"http://{opts.url_host}:{server.port}/?k={token}"
        print(f"Beautiful Prompter is waiting at {url}", file=sys.stderr, flush=True)
        if should_open_browser(opts):
            try:
                webbrowser.open(url)
            except Exception:  # noqa: BLE001 - best effort only
                pass
        outcome = server.wait(opts.timeout)
    except _Interrupted:
        return 130
    finally:
        server.close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)

    if outcome.kind == "answer":
        assert outcome.text is not None
        if opts.output is not None:
            write_output_atomic(opts.output, outcome.text)
        sys.stdout.buffer.write(outcome.text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    if outcome.kind == "cancel":
        return 1
    return 124


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    try:
        return run(resolve_options(args, os.environ))
    except UsageError as exc:
        print(f"bp: {exc}", file=sys.stderr)
        return 2


def entry() -> None:
    """Console entry point: exit with main()'s return code (zipapp discards it otherwise)."""
    sys.exit(main())
