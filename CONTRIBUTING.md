# Contributing to Launch Lab

Thanks for helping. Launch Lab is small on purpose: one skill, stdlib Python scripts, no
services. Contributions that keep it that way are the easiest to merge.

## Setup

```bash
git clone https://github.com/likithtech2006-pixel/launch-lab.git
cd launch-lab
python3 -m unittest discover -s tests -v    # Python 3.9+, no installs needed
```

To try your working copy as a skill, symlink it into Claude Code:

```bash
mkdir -p ~/.claude/skills && ln -s "$PWD/skills/launch-lab" ~/.claude/skills/launch-lab
```

## Layout

| Path | What |
|---|---|
| `skills/launch-lab/SKILL.md` | The skill: routing, ground rules, the pipeline. Keep it short; details go in `references/`. |
| `skills/launch-lab/references/` | Loaded on demand: scoring weights, personas and grading rubric, demo pipeline, post templates, diagnosis rules, install test. |
| `skills/launch-lab/scripts/` | Deterministic helpers (`scripts/` at the repo root is a symlink). Python stdlib only; `record_web.mjs` is the one Node script. |
| `skills/launch-lab/assets/` | Default personas, library snippet page. |
| `evals/` | `evals.json` scenarios for the skill + fixture repos and metrics. |
| `tests/` | Unit tests for the scripts, run against the fixtures. |
| `examples/` | A real before/after run on a public repo. |

## Ground rules for changes

- **No new dependencies** in Python scripts. If you need something, write the 30 lines.
- **No network** except `gh` calls the user runs against their own repo.
- **Never post or upload anything** on the user's behalf, and never widen where the skill writes
  (`launch/`, `.launch-lab/`, approved README edits).
- **Scores must stay explainable.** If you change a weight or formula in `score.py`, update
  `references/scoring.md` in the same PR and add or adjust a test.
- **No invented numbers** in docs, examples or templates. Examples come from real runs.

## Good first contributions

- New persona presets for specific audiences (add to `references/personas.md` as examples).
- Repo-type detection for more ecosystems (Ruby gems, Elixir, Swift packages) in `scan.py`.
- More friction patterns in `install_test.py` `classify_failure()`, each with a fixture and test.
- Corrections to the comparison table in the README if a tool listed there does more than we say.

## Pull requests

1. Open an issue first for anything bigger than a bug fix.
2. Add a test (fixture + assertion) for behaviour changes.
3. Run the tests and, for skill changes, run `/launch-lab` on a fixture and paste the summary.
4. Add a line to `CHANGELOG.md` under "Unreleased".
