# Star Readiness Report: launch-lab

_Generated 2026-11-03T16:17:48+00:00 by Launch Lab. Weights: `references/scoring.md`._

## Score: **90 / 100**  (before: 87, +3)

## Categories

| Category | Weight | Score | Notes | Before |
|---|---:|---:|---|---:|
| Clarity (Stranger Panel) | 30 | 24.8 | understanding 100%, star intent 35%, 0/3 would star | 24.6 |
| Clean install | 15 | 15.0 | passed 3/3 steps (local) | 15.0 |
| Time to first success | 10 | 10.0 | 0s from first command to success | 10.0 |
| Demo | 10 | 10.0 | animated demo above the fold | 10.0 |
| Quickstart length | 8 | 5.6 | 4 commands | 5.6 |
| Description, topics, license, badges | 10 | 10.0 | description set, 7 topics; license yes, 4 badges in fold | 10.0 |
| Comparison with alternatives | 7 | 7.0 | comparison table (How is this different?) | 7.0 |
| Social preview image | 5 | 2.5 | image in repo (.github/social-preview.png) but not confirmed as the GitHub social preview | 0.0 |
| Contributing guide | 5 | 5.0 | CONTRIBUTING.md | 5.0 |

## Top 5 fixes (ranked by impact)

1. **Upload the social preview in GitHub Settings > General > Social preview** (+2.5 pts, easy, Social preview image)  
   Use .github/social-preview.png (1280x640)
2. **Shorten the quickstart to 3 commands or fewer** (+1.9 pts, easy, Quickstart length)  
   It has 4; move extras to a Configuration section
3. **Answer the panel's confusions above the fold** (+1.6 pts, easy, Clarity (Stranger Panel))  
   Personas said: "The 'visitors' are LLM-simulated personas, so the 60 -> 83 score jump is Claude grading Claude's own suggestions; unclear why that correlates with real-human stars."; "It says it is 'not a star predictor' yet the product is literally a 'Star Readiness Score'. That is mixed messaging."; "The weights of the 'published, weighted checklist' are not shown, and I can't tell how arbitrary they are."; "The demo is on pallets/itsdangerous, a mature project that already has stars; it is not evidence that the score predicts anything or that a fix round actually helped a real launch."
4. **Add the proof personas asked for** (+2.1 pts, medium, Clarity (Stranger Panel))  
   What would make them star: "Evidence that the score is validated against reality: e.g. a table of real repos with before/after READMEs and their actual star or traffic outcomes, plus the visible weighted checklist, and a clear one-line comparison against 'just paste your README into Claude and ask for feedback'."; "A plain-English one-line explanation of Claude Code and the score (with a screenshot of one real output report showing the 5 fixes) so I can see what I'd get in five minutes on my own small repo."; "Evidence that the score predicts real outcomes, such as before/after star counts from several real launches. A clear statement of who it's for and why a team or company would use it, plus visible signs of ongoing maintenance and other users, would also help."

## Stranger Panel

**True purpose:** A Claude Code skill that tests whether a GitHub repo's launch will work before posting: simulated first-time visitors judge only the top of the README, a clean environment runs the README install steps, and a 0-100 score ranks fixes and re-tests after them; it also makes demo GIFs, drafts launch posts and diagnoses post-launch star conversion.  
**True audience:** Open-source developers who use Claude Code and are about to launch (or just launched) a GitHub project and want stars/adoption.

| Persona | Understood it as | Purpose | Audience | Star? | Confidence |
|---|---|---:|---:|---|---:|
| Skeptical HN developer | A Claude Code plugin that has three simulated visitors read the top of your GitHub README, runs your install steps, and outputs a 0-100 'Star Readiness Score' with five suggested fixes, then re-tests after you make changes. | 1 | 1 | no | 65 |
| Beginner developer | It's a Claude Code add-on that pretends to be three people seeing your GitHub project for the first time, tries your install steps, and gives your repo a score out of 100 with fixes to improve it. | 1 | 1 | no | 60 |
| Busy CTO evaluating tools | A Claude Code plugin that has simulated first-time visitors read the top of your GitHub README and runs your install steps, then gives a 0-100 'Star Readiness Score' with suggested fixes. | 1 | 1 | no | 70 |

**What confused them**

- skeptical-hn: The 'visitors' are LLM-simulated personas, so the 60 -> 83 score jump is Claude grading Claude's own suggestions; unclear why that correlates with real-human stars.
- skeptical-hn: It says it is 'not a star predictor' yet the product is literally a 'Star Readiness Score'. That is mixed messaging.
- skeptical-hn: The weights of the 'published, weighted checklist' are not shown, and I can't tell how arbitrary they are.
- skeptical-hn: The demo is on pallets/itsdangerous, a mature project that already has stars; it is not evidence that the score predicts anything or that a fix round actually helped a real launch.
- skeptical-hn: 'Other tools write your launch' is vague. Which tools? How is this different from just asking Claude to review my README?
- skeptical-hn: It is unclear what the 17 tests cover, since the visitor reading (the core value) is an LLM call and is not deterministic.
- skeptical-hn: It bundles several things (demo GIFs, launch post drafts, post-launch star diagnosis), so I can't tell what the core product is, and it reads like scope creep.
- skeptical-hn: Running install steps in Docker or on my machine after 'approval' raises a security question and a trust question I can't resolve from this view.
- skeptical-hn: It's v0.1.0 and a Claude Code skill, i.e. essentially a prompt plus a small Python script. I can't tell whether there is real code behind it or whether it's a wrapper.
- beginner: I don't know what 'Claude Code' is or whether I need a paid account; it says no API keys or paid services but also 'You need: Claude Code'
- beginner: What is a 'skill' vs a 'plugin' vs a 'marketplace'? The install uses terms I don't know
- beginner: 'Star Readiness Score' is not explained simply; I can't tell what the 100 points are made of
- beginner: 'Simulated visitors' - not clear how that works or how trustworthy it is, given the 'not a star predictor' disclaimer
- beginner: Jargon: 'stdlib', 'weighted checklist', 'Docker', 'temp folder', 'above the fold'-style README talk
- beginner: The demo is on pallets/itsdangerous, a library I haven't heard of, so I can't judge the result
- beginner: Unclear whether it is for me: I have no launched project with users yet, so I can't tell if it helps beginners
- beginner: It says 'Install (10 seconds)' but the 'Manual install' section is empty in what I can see
- beginner: Is it safe to let it run my install commands? It mentions approving an exact list but I'm not sure what that looks like
- beginner: Also included: 'launch post drafts', 'post-launch star diagnosis' - listed without explanation
- busy-cto: Is this useful for a 40-person engineering team? It looks like a tool for maintainers chasing GitHub stars, not for solving an engineering problem.
- busy-cto: The 'simulated visitors' are LLM-generated, so I can't tell whether their opinions mean anything. The README says it is not a star predictor, but I can't tell what the score is actually validated against.
- busy-cto: The only evidence is one demo on a different repo (itsdangerous, 60 to 83), and I can't tell whether the author's own tweaks to that README were what moved the score.
- busy-cto: It depends on Claude Code, and the README doesn't say what it costs to run (tokens, usage). It says 'no paid services', which seems to conflict with needing Claude Code.
- busy-cto: It runs install commands from the repo. Docker is mentioned, but the alternative is a temp folder on my machine after approval. I can't judge the security risk in 10 seconds.
- busy-cto: Maintenance signals are thin: version 0.1.0, no visible commit activity, no sign of other users, and no team or company behind it.
- busy-cto: '17 tests passing' is a small number and says nothing about how good the scoring is.
- busy-cto: The 'Manual install' heading is cut off, so I can't see what that path involves.

**What would make them star it**

- skeptical-hn: Evidence that the score is validated against reality: e.g. a table of real repos with before/after READMEs and their actual star or traffic outcomes, plus the visible weighted checklist, and a clear one-line comparison against 'just paste your README into Claude and ask for feedback'.
- beginner: A plain-English one-line explanation of Claude Code and the score (with a screenshot of one real output report showing the 5 fixes) so I can see what I'd get in five minutes on my own small repo.
- busy-cto: Evidence that the score predicts real outcomes, such as before/after star counts from several real launches. A clear statement of who it's for and why a team or company would use it, plus visible signs of ongoing maintenance and other users, would also help.

## Clean install test

Mode: `local` | Result: **passed** | Time to first success: 0.1s

No friction found.

---
_Launch Lab never posts or uploads anything. All results were computed locally._
