"""Command-line interface: argument parsing, environment defaults, document loading."""

from __future__ import annotations

import argparse
import sys
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


def main(argv: list[str] | None = None) -> int:
    import os

    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    try:
        opts = resolve_options(args, os.environ)
        if opts.mode == "show":
            load_document(opts.file)
    except UsageError as exc:
        print(f"bp: {exc}", file=sys.stderr)
        return 2
    print("bp: not implemented yet", file=sys.stderr)
    return 2
