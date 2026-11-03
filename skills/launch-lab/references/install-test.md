# Clean install test: how it works

The goal is to experience the README the way a stranger does: a fresh machine, only the steps
written in the README, no knowledge in your head.

## What gets run

`install_test.py` reads the shell code blocks (`bash`, `sh`, `shell`, `zsh`, `console` or no
language) under headings that look like Install / Installation / Quickstart / Getting started /
Setup / Usage. In `console` blocks or blocks with `$ ` prompts, only prompt lines are commands.
`\` line continuations are joined.

Plan rewrites (always shown in `--dry-run`):

| Situation | Handling |
|---|---|
| `git clone <this repo>` | Replaced by a copy of the local working tree (so unpublished changes are tested). Excludes `node_modules`, `.venv`, build output, `launch/`, `.launch-lab/`. |
| `/plugin ...` or other slash commands | Marked `manual`: checked statically, not run. |
| Placeholders (`<your-token>`, `YOUR_API_KEY`) | Marked `unclear` and reported as friction; not run. |
| `sudo` | Docker: stripped (root). Local: refused. |
| `curl ... \| sh` | Flagged. Local: refused unless `--allow-pipe-sh` after the user reviewed the script. |
| Dev servers (`npm run dev`, `flask run`, `uvicorn`, `docker compose up`) | Run for `--server-wait` seconds (15); still running = success. |

Commands run in order in one environment, so `cd`, `export` and `source .venv/bin/activate`
carry over between steps. stdin is closed: an interactive prompt fails fast and is reported.

## Environments

**Docker (preferred).** A fresh container from a language image: `python:3.12`, `node:22`,
`rust:1`, `golang:1`, or `buildpack-deps:bookworm` when unknown (override with `--image` or
`install.image` in config). The repo snapshot is mounted read-only and copied in.

**Local (fallback, needs approval).** A temp directory with its own `HOME`, a Python venv (for
Python projects), its own npm prefix and cache, `CARGO_HOME` and `GOPATH`. The environment is
reduced to a minimal whitelist so your API keys and tokens are **not** visible: an undocumented
env var shows up as a failure, as it would for a stranger. This is isolation for accuracy, **not a
security sandbox**: the commands run as you. That is why it requires `--yes`, given only after the
user approved the dry-run plan. Host toolchains (python, node, cargo) are still visible, so
missing-prerequisite detection is weaker than Docker.

**Static.** Nothing runs. Lints the instructions only. Produces friction but no install points.

## Friction types

| Type | Detected from |
|---|---|
| `missing_prerequisite` | exit 127 / "command not found"; statically: a tool used without a Prerequisites mention |
| `unstated_version` | "requires Python", engine mismatch; statically: manifest requires a version the README never states |
| `undocumented_env_var` | KeyError / "is not set"; statically: env vars read in source but absent from README and `.env.example` |
| `failing_command` | any other non-zero exit, missing module after install, unpublished package (404), timeouts |
| `unclear_step` | no install section, placeholders, pipe-to-shell, more than 6 commands |

Severity: `blocker` (the reader cannot continue), `major`, `minor`.

## Time to first success

Wall-clock time from the first command to the end of the last runnable step (plus
`--success-cmd`, if given) when every step passed. Downloads count: that is what a stranger waits
for. Set `install.success_cmd` in config (e.g. `"mytool --version"`) when the README's last step
does not prove the tool works.
