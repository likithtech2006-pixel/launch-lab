# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-03

### Added
- `/launch-lab` skill with subcommands `panel`, `install`, `score`, `demo`, `posts`, `diagnose`.
- Stranger Panel: fold-only persona prompts (`panel.py`), 3 default personas, custom personas via `.launch-lab/config.json`, grading rubric and schema validation.
- Clean install test (`install_test.py`): Docker, approved local sandbox or static mode; friction classification; time to first success.
- Star Readiness Score (`score.py`): 9 weighted categories, provisional scoring for unmeasured categories, top-5 fixes, Markdown report and SVG score card with before/after.
- Demo pipeline: VHS, Playwright (`record_web.mjs`), library snippet page, `gif_optimize.sh` size ladder, and the zero-dependency `text_gif.py` renderer.
- Launch content templates (Show HN, Reddit, X, LinkedIn, dev.to, Product Hunt, 14-day calendar).
- Post-launch diagnosis (`github_metrics.py`): conversion per period and per referrer, readme / distribution / retention patterns, snapshot history.
- Claude Code plugin manifests, 10 eval scenarios, 17 script tests, CI workflow.
- Social preview image (`.github/social-preview.png`), rendered with `text_gif.py`.

### Fixed (found by running Launch Lab on itself)
- Env vars read only by tests, fixtures or examples were reported as undocumented.
- A social preview image inside a test fixture was credited to the repo.
- Install commands at the top of a README without an "Install" heading were missed.
- "How is this different?" comparison headings were not detected.
