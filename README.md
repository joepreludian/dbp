# Beautiful Prompter

A Claude Code plugin with a tiny command-line tool, `bp`, that opens a local
web page, blocks until you answer, prints the answer and exits. Two modes:
`bp write` gives you a markdown editor with live preview to compose a prompt;
`bp show FILE` renders a markdown file for review with an answer box below.
One process per call, standard library only.

## Usage

```
python3 bin/bp.pyz write [--output FILE] [--timeout SECONDS] [--no-open]
python3 bin/bp.pyz show FILE [--output FILE] [--timeout SECONDS] [--no-open]
```

The URL is printed on stderr. The answer goes to stdout (and to `--output`
when given). Exit codes: 0 answer, 1 cancelled, 2 usage error, 124 timeout,
130 interrupted.

Environment overrides for remote browsers: `BP_BIND` (default `127.0.0.1`),
`BP_URL_HOST` (default `localhost`), `BP_PORT` (default: a free port).

## Development

```
sudo apt-get install python3-pytest   # one-time, no pip needed
python3 -m pytest
bash scripts/build.sh                 # rebuilds bin/bp.pyz
```
