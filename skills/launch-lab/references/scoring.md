# Star Readiness Score: weights and rubric

The score estimates how likely a first-time visitor is to understand, trust and star the repo.
It is a **heuristic**, not a prediction of star counts. Weights live in `scripts/score.py`
(`WEIGHTS`); keep this file in sync when you change them.

## Weights (total 100)

| Category | Weight | Measured by | Why it matters |
|---|---:|---|---|
| Clarity | 30 | Stranger Panel | If a stranger cannot say what it does in 10 seconds, nothing else matters. 22 pts understanding + 8 pts star intent. |
| Clean install | 15 | `install_test.py` (Docker or approved local run) | A failed first run is the most common reason people bounce after starring intent. |
| Time to first success | 10 | `install_test.py` | Long installs lose people even when they work. |
| Demo | 10 | README scan | A demo GIF shows value faster than prose and is what people share. |
| Description, topics, license, badges | 10 | README scan + `gh repo view` | Discovery (search, Explore, topics) and maturity signals. |
| Quickstart length | 8 | README scan | Fewer, copy-pasteable commands near the top. |
| Comparison with alternatives | 7 | README scan | "Why not X?" is the first question on HN and Reddit. |
| Social preview image | 5 | `gh` (custom OpenGraph image) or image file in repo | Shared links get a real card instead of the generic one. |
| Contributing guide | 5 | File check | Signals the project is alive and welcomes help. |

## Category formulas

Each category produces a fraction 0..1; points = weight x fraction.

**Clarity** (needs `panel.json`). Per persona: `understanding = 0.7 * purpose_match + 0.3 * audience_match`
(each graded 0 / 0.5 / 1, see `personas.md`). `p_star` = confidence/100 if the persona would star,
else 1 - confidence/100. Fraction = (22 x mean understanding + 8 x mean p_star) / 30.

**Clean install** (needs a measured run). Success: 1.0 minus 0.1 per *major* friction point
(max -0.3). Failure: 0.5 x (passed steps / runnable steps).

**Time to first success** (needs success). <= 60 s: 1.0, <= 120 s: 0.85, <= 300 s: 0.6, <= 600 s: 0.35,
slower: 0.15. Failure: 0. Time includes downloads, as a real stranger would experience it.

**Demo.** Animated (GIF/video/asciinema) above the fold: 1.0. Animated but below the fold: 0.6.
Only a static image above the fold: 0.3. None: 0.

**Quickstart length.** No section: 0. Section with no shell commands: 0.2. 1-3 commands: 1.0,
4-6: 0.7, 7-10: 0.4, more: 0.2. x0.8 if the section starts after line 80. -0.15 per placeholder step.

**Metadata** (sub-weights within the category): description 3 (>= 20 chars full, shorter half),
topics 3 (>= 3 full, 1-2 half), license 2, badges in fold 2 (1-6 full, > 6 half: a badge wall
pushes the tagline down, 0: none). When the repo is not on GitHub yet (or `gh` is unavailable),
description and topics are excluded and the category is scored on license and badges only.

**Comparison.** Section heading like "vs", "comparison", "alternatives", "why not", "how is this
different" with a table: 1.0; section without a table: 0.7; none: 0.

**Social preview.** Custom OpenGraph image on GitHub: 1.0. An image in the repo that looks like
one (`social-preview.*`, `og*`) but is not confirmed uploaded: 0.5. None: 0.

**Contributing.** `CONTRIBUTING*` at root, `.github/` or `docs/`: 1.0. Only a "Contributing" section in the README: 0.8. None: 0.

## Unmeasured categories and the provisional flag

If the panel or a measured install run is missing, those categories are excluded and the score
is `100 x earned / measured_weight`, marked **provisional**. This avoids two failure modes:
punishing a repo for a test that was not run, and inflating it by assuming a pass.
`--mode static` install runs only lint the instructions; they produce fixes but no install points.

## Ranking the top 5 fixes

Each category lists candidate fixes with a `share` of the category's lost points that the fix
would plausibly recover and an `ease` (easy 1.0, medium 0.75, hard 0.5).
`gain = weight x (1 - fraction) x share`; ranking key = `gain x ease`. Fixes that unlock an
unmeasured category ("Run the Stranger Panel") are listed but show "unlocks measurement" instead
of a gain, because the gain is unknown.

## Interpreting the number

| Score | Reading |
|---|---|
| 85-100 | Launch-ready. Remaining fixes are polish. |
| 70-84 | Good. Fix the top 2-3 items before a big launch (Show HN, Product Hunt). |
| 50-69 | Visitors will bounce. Fix clarity and install first. |
| < 50 | Not ready. Strangers cannot tell what it is or cannot run it. |

These bands are judgment calls from common launch advice, not measured thresholds. The score's
real value is the **before/after delta** and the ranked fix list.
