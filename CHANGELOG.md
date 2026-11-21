# Changelog

All notable changes to Beautiful Prompter are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Write mode is one centered markdown editor with Write and Preview tabs
  instead of a side-by-side editor and live preview.

### Added
- The header shows the folder, git repository (from `origin`) and branch the
  process was started in; outside a repository only the folder is shown.

## [0.2.0] - 2026-11-20

### Added
- Installable as a Claude Code plugin from GitHub: `.claude-plugin/marketplace.json`
  with install instructions in the README.
- GPLv3 license.
- CI workflow: tests on Linux and macOS, Python 3.10 and 3.14, with a check
  that the committed `bin/bp.pyz` matches the source.
- Release workflow: a `v*` tag publishes a GitHub Release with `bp.pyz`,
  `SHA256SUMS` and this changelog's section as notes.
- `scripts/release.sh X.Y.Z` to bump, rebuild, test, commit and tag.
- The skill offers show mode right after producing a document, documents exit
  code 130, notes that the tool opens a browser tab itself, and uses absolute
  paths in its examples.

### Changed
- `bin/bp.pyz` is built deterministically (sorted entries, fixed timestamps
  and modes, stored compression), so rebuilds are byte-identical.
- Show mode's meta line shows the file path as given, not just its name.
- A fixed `BP_PORT` can be reused immediately after a run exits.
- The answer box in show mode is vertically resizable.

### Fixed
- `--port` outside 0..65535 is a usage error (exit 2) instead of a traceback.
- The "already answered" error no longer suggests retrying.
- Send and Cancel share one in-flight flag, so neither can race the other.

## [0.1.1] - 2026-11-20

### Fixed
- An unwritable `--output` path no longer loses the answer or exits as a
  cancel: the directory is created up front and stdout is written first.
- A missing markdown renderer shows a message and falls back to plain text
  instead of a dead page.
- The theme choice is remembered in a cookie, so it survives the per-run port.
- Browser auto-open runs in a thread and cannot block the process.
- Oversized or missing `Content-Length` is rejected before the body is read;
  stalled clients are dropped after 30 seconds.
- The Python 3.10 floor is stated and checked at startup.

## [0.1.0] - 2026-11-20

### Added
- `bp write`: a markdown editor with live preview that returns the composed
  prompt to the agent.
- `bp show FILE`: renders a markdown file with an answer box below it and
  returns the answer.
- One process per call, token-gated local HTTP server, exit codes 0/1/2/124/130,
  atomic `--output` file, `BP_BIND` / `BP_URL_HOST` / `BP_PORT` for remote
  browsers.
- Paper (light) and Ink (dark) themes with a toggle.
- The `beautiful-prompter` Claude Code skill and the single-file `bin/bp.pyz`.
