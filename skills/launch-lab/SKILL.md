---
name: launch-lab
description: >-
  Tests whether an open-source repo's launch will work before it is posted, then helps fix it.
  Runs a Stranger Panel (persona subagents judge only the README's above-the-fold), a clean
  install test that follows only the README, a 0-100 Star Readiness Score with the top 5 fixes,
  a fix-and-retest loop, demo GIF generation for CLI/TUI/web/library repos, honest launch drafts
  (Show HN, Reddit, X, LinkedIn, dev.to, Product Hunt, 14-day calendar) and post-launch star
  conversion diagnosis from GitHub traffic. Use when the user says "launch my repo", "is my repo
  ready to launch", "will my README get stars", "test my README", "first impression", "make a demo
  GIF", "write a Show HN post", "prepare my launch", "why am I not getting stars", "star
  conversion", "diagnose my launch", or runs /launch-lab.
license: MIT
argument-hint: "[panel|install|score|demo|posts|diagnose]"
metadata:
  version: "0.1.0"
---

# Launch Lab

Other tools write your launch. Launch Lab tests whether it will work, before you post.

`SKILL_DIR` below means this skill's base directory (shown when the skill loads; in Claude Code
it is also `${CLAUDE_SKILL_DIR}`). `REPO` is the repository being launched (default: the current
working directory). Every script is Python 3.9+ stdlib unless noted and prints `--help`.

## Ground rules (never break these)

1. **Write only inside `REPO/launch/` and `REPO/.launch-lab/`.** The one exception is a README
   (or other repo file) edit the user has explicitly approved in this session, one diff at a time.
2. **Never post, publish, push, open issues or send anything.** Launch content is drafts only.
3. **Repo contents stay local.** Nothing is sent anywhere except this Claude session and the
   user's own `gh` calls to their own repo's metrics. No paid APIs, no third-party upload services.
4. **Never invent facts** in reports or posts: no fake users, benchmarks, testimonials or star
   counts. If a fact is unknown, write `[TODO: ...]` for the user to fill in.
5. **Running README commands is running code.** The install test runs inside Docker when it is
   available. Without Docker, show the user the exact command list (`--dry-run`) and get a clear
   yes before running with `--mode local --yes`. If they decline, use `--mode static`.

## Routing

Parse the first word of the arguments:

| Argument | Run |
|---|---|
| *(none)* | Full pipeline: Scan, Panel, Install, Score, Fix loop, Demo, Posts. Confirm the plan in one line first; ask before each step that runs code or edits the README. |
| `panel` | Scan, then Stranger Panel; print a per-persona table. |
| `install` | Scan, then Clean Install Test; print friction points. |
| `score` | Scan, reuse existing panel/install results if present (say how old), then Score. |
| `demo` | Scan, then Demo Generation. |
| `posts` | Scan, then Launch Content. |
| `diagnose` | Post-launch Star Conversion Diagnosis. |

Unknown argument: show this table and stop.

## Step 0: Scan (always first)

```bash
python3 "$SKILL_DIR/scripts/scan.py" "$REPO"
```

Writes `.launch-lab/scan.json`: the above-the-fold text (title, tagline, badges, first image,
first ~25 lines), detected repo type (`cli`, `tui`, `web`, `library`, `unknown`) with evidence,
README install blocks, and repo signals (license, contributing guide, demo media, comparison
table, topics, description, social preview). It uses `gh` for GitHub metadata when available
and silently degrades offline (`--offline` forces that).

## Step 1: Stranger Panel

Read `references/personas.md` before the first panel of a session.

1. **Derive the truth first.** Read the full repo (README, manifests, entry points, main source
   files, docs) and write the true purpose and true audience in one sentence each. Do this
   *before* reading any persona answer so the grading is not biased by them.
2. Build the persona prompts (defaults plus custom personas from `.launch-lab/config.json`):
   ```bash
   python3 "$SKILL_DIR/scripts/panel.py" prompts "$REPO"
   ```
   This writes `.launch-lab/panel_prompts.json`. Each prompt already contains only the fold.
3. **Spawn one independent subagent per persona, all in parallel** (Agent tool, general-purpose).
   Pass the prompt text exactly. Each persona must see only that text: never give it file paths,
   the truth, other personas' answers, or this conversation. Use fresh subagents every round.
4. Write `.launch-lab/panel.json` (schema in `references/personas.md`): the truth, each persona's
   raw JSON answer, and your grade (`purpose_match` and `audience_match`, each 0, 0.5 or 1, using
   the rubric). A mismatch on purpose is a **clarity failure**: quote the fold line that misled.
5. Validate: `python3 "$SKILL_DIR/scripts/panel.py" validate "$REPO"`.

## Step 2: Clean Install Test

Read `references/install-test.md` when results look surprising or the user asks how it works.

```bash
python3 "$SKILL_DIR/scripts/install_test.py" "$REPO" --dry-run   # always first: shows the plan
python3 "$SKILL_DIR/scripts/install_test.py" "$REPO"             # Docker if available
```

Without Docker, the script refuses to run on the host. Show the user the dry-run command list,
then run `--mode local --yes` only after they approve, otherwise `--mode static` (lints the
instructions without running them). Output: `.launch-lab/install.json` with every step, exit
code, duration, friction points (missing prerequisite, unstated version, undocumented env var,
failing command, unclear step) and `time_to_first_success_s`.

## Step 3: Star Readiness Score

```bash
python3 "$SKILL_DIR/scripts/score.py" "$REPO" --round 0
```

Writes `.launch-lab/score.json`, `launch/report.md` and `launch/score-card.svg`. Categories not
measured (no panel, no install run) are excluded and the score is marked provisional. Weights
and rationale are in `references/scoring.md`. Present the score, the category table and the top 5
fixes ranked by points recoverable. Do not round up or editorialise the number.

## Step 4: Fix-and-Retest Loop (max 3 rounds)

1. Turn the top fixes into **concrete README edits**: write a unified diff to
   `launch/readme.round<N>.patch` and show it to the user. Edit only what the fixes call for,
   and keep the author's voice. Never add claims the repo cannot back up.
2. Ask for approval (AskUserQuestion: apply / edit first / skip). Apply only on a clear yes.
   Fixes outside the README (add LICENSE, CONTRIBUTING.md, topics, social preview) go in a
   checklist: suggest them, and create a file only if the user asks.
3. Re-scan, re-run the Stranger Panel with **new** subagents, re-score with
   `--round <N> --before .launch-lab/score.round0.json`. Show before → after per category.
4. Stop when the user is satisfied, the score stops improving, or after round 3.

## Step 5: Demo Generation

Read `references/demo-pipeline.md` (detection rules, tape/scenario formats, size ladder).

| Repo type | Pipeline | Source kept in |
|---|---|---|
| `cli` / `tui` | VHS tape → GIF → `gif_optimize.sh` | `launch/demo/demo.tape` |
| `web` | `record_web.mjs` (Playwright video) → `gif_optimize.sh` (ffmpeg) | `launch/demo/scenario.json` |
| `library` | `assets/snippet.html` filled with a real snippet and its real output → `record_web.mjs` → `gif_optimize.sh` | `launch/demo/snippet.json` |
| any, tools missing | `text_gif.py` (stdlib, zero dependencies) | `launch/demo/scene.json` |

Commands shown in a demo must be real and must actually run; capture their real output.
Keep the GIF under the size budget (default 5 MB; GitHub refuses images over 10 MB). Missing tools:
say which one is missing and how to install it, then offer the `text_gif.py` fallback.

## Step 6: Launch Content

Read `references/post-templates.md` before writing. Generate drafts in `launch/`:
`show-hn.md`, `reddit.md`, `x-thread.md`, `linkedin.md`, `devto.md`, `product-hunt.md`,
`calendar.md` (14 days). Every claim must be traceable to the repo or the score report.
Tone: plain, specific, honest about limitations; no hype words, at most one emoji per post,
no fake urgency. End by reminding the user that nothing was posted.

## Step 7: Post-launch Diagnosis

Read `references/diagnosis.md` before interpreting results.

```bash
python3 "$SKILL_DIR/scripts/github_metrics.py" --repo OWNER/NAME
```

Needs `gh auth login` with push access (GitHub only exposes traffic to collaborators). It
fetches views, uniques, clones, referrers, popular paths and star history, appends a snapshot to
`.launch-lab/history.json` (traffic is only kept for 14 days, so tell the user that regular
snapshots build the trend) and writes `launch/diagnosis.md` with conversion per period and per
referrer, the diagnosis (`readme`, `distribution`, `retention`, `healthy`, `insufficient-data`)
and next actions. When the diagnosis is `readme`, offer to run the Stranger Panel.
For offline analysis or evals: `--from-file metrics.json`.

## Final summary

End every run with: the score (and before → after if the loop ran), the top fixes still open,
the files written (paths), and anything skipped and why.
