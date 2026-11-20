---
name: beautiful-prompter
description: Use when the user says "open in bp", "open in the beautiful prompter", "let me write this in bp", wants to write a long or structured prompt somewhere better than the terminal, or when a generated document (a spec, a plan, a long report) should be reviewed in the browser with the answer returned to the agent.
---

# Beautiful Prompter

`bp` opens a tiny local web page, blocks until the user sends one answer,
writes that answer to a file, and exits. Two modes:

| Mode | Command | The user sees | You get back |
|------|---------|---------------|--------------|
| write | `bp write` | a markdown editor with live preview | the prompt they wrote |
| show | `bp show FILE` | FILE rendered, an answer box below | their answer about FILE |

The executable is `${CLAUDE_PLUGIN_ROOT}/bin/bp.pyz`. It needs only `python3`.

## Running it

"Open in bp" with no file named means write mode. A file named, or a
document you just wrote that the user wants to review, means show mode.

The user may take longer than a foreground shell call allows, so the process
runs in the background and you wait for its exit notification. Always pass
`--output` with a literal path you choose before running (the scratchpad
plus a timestamped name). Write the path into the command itself, not into a
shell variable: the shell is gone when the process exits, and you must still
know the path. The answer file is the reliable channel; the background
capture merges stdout and stderr and is not.

```bash
# write mode (answer path chosen up front, written literally)
python3 "${CLAUDE_PLUGIN_ROOT}/bin/bp.pyz" write --output /path/to/scratchpad/bp-answer-1763600000.md

# show mode (the file path as the user would type it)
python3 "${CLAUDE_PLUGIN_ROOT}/bin/bp.pyz" show docs/specs/design.md --output /path/to/scratchpad/bp-answer-1763600000.md
```

Run the command with `run_in_background: true`. Then:

1. Read the background command's output file (the Bash tool returns its
   path). Its first line is
   `Beautiful Prompter is waiting at http://HOST:PORT/?k=TOKEN`.
   If the line is not there yet, read the file once more; if it is still
   missing, say so and end your turn anyway. The exit notification will
   report a failed start.
   Relay that URL to the user verbatim, with the token. Tell them to open it
   in their browser and come back when they have sent their answer.
2. End your turn and wait for the exit notification. Do not poll.
3. On exit code 0, read the answer file and treat its content as the user's
   next message (write mode) or as their answer about the file (show mode).

Optional flags: `--timeout SECONDS` (exit 124 when it expires; without it
the process waits indefinitely), `--title TEXT` (heading in the page),
`--no-open` (skip opening a local browser).

## Exit codes

| Code | Meaning | What to do |
|------|---------|------------|
| 0 | answered; the answer file holds the text | continue with it |
| 1 | user pressed Cancel; no file | say so, ask how to proceed |
| 2 | usage error; message on stderr | fix the invocation (missing file, bad port) |
| 124 | `--timeout` expired; no file | say so, ask whether to open it again |

Never re-run `bp` on your own after 1 or 124. The user made that choice or
walked away; ask.

## Remote browsers

Never pass `--bind` or `--url-host` yourself. When the browser is not on the
machine running the process, the environment sets `BP_BIND` and
`BP_URL_HOST` (and optionally `BP_PORT`), and the printed URL is already the
right one. Relay it as printed.

## Offering show mode

After writing a document the user will want to read in full (a design spec,
an implementation plan, a long report), offer once: "Want to read this in the
Beautiful Prompter and answer there?" Only run `show` when they say yes.
