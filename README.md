# Beautiful Prompter

A Claude Code plugin with a tiny command-line tool, `bp`, that opens a local
web page, blocks until you answer, prints the answer and exits. Two modes:
`bp write` gives you a centered markdown editor with a Preview tab to compose a prompt;
`bp show FILE` renders a markdown file for review with an answer box below.
One process per call, standard library only, Python 3.10 or newer. The header
shows the folder, repository and branch the process was started in.

Say "open in bp" in Claude Code and the agent opens the editor for you. After
the agent writes a long document, it offers to show it there for review.

## Install

As a Claude Code plugin, from GitHub:

```
/plugin marketplace add joepreludian/dbp
/plugin install beautiful-prompter@joepreludian
```

To try a local checkout for one session without installing:

```
claude --plugin-dir /path/to/dbp
```

The plugin runs `bin/bp.pyz` with your `python3`. Nothing else to install.

## Usage

```
python3 bin/bp.pyz write [--output FILE] [--timeout SECONDS] [--no-open] [--title TEXT]
python3 bin/bp.pyz show FILE [--output FILE] [--timeout SECONDS] [--no-open] [--title TEXT]
```

The URL is printed on stderr. The answer goes to stdout, and to `--output`
when given. Exit codes: 0 answer, 1 cancelled, 2 usage error, 124 timeout,
130 interrupted.

### Remote browsers

When Claude Code runs on a machine other than the one with your browser (a
VM, a remote dev box), set `BP_BIND=0.0.0.0` and `BP_URL_HOST=<reachable host
or IP>` in that environment. `BP_PORT` fixes the port if your network setup
needs it. The skill never sets these itself; the printed URL is already the
one to open.

## Development

```
sudo apt-get install python3-pytest   # or: python3 -m pip install pytest
python3 -m pytest
bash scripts/build.sh                 # rebuilds bin/bp.pyz deterministically
```

CI runs the suite on Linux and macOS, Python 3.10 and 3.14, and fails if the
committed `bin/bp.pyz` does not match a fresh build.

## Releasing

1. Move the `[Unreleased]` entries in `CHANGELOG.md` under `## [X.Y.Z] - <date>`
   and commit.
2. Run `bash scripts/release.sh X.Y.Z`. It bumps the version in
   `src/bp/__init__.py` and `.claude-plugin/plugin.json`, rebuilds, tests,
   commits `chore: release X.Y.Z` and tags `vX.Y.Z`.
3. Push `main` and the tag. The release workflow verifies the tag against the
   version, rebuilds and checks the artifact, and publishes a GitHub Release
   with `bp.pyz`, `SHA256SUMS` and the changelog section as notes.

## License

GPL-3.0-or-later. See `LICENSE`.
