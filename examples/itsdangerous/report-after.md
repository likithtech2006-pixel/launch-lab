# Star Readiness Report: itsdangerous

_Generated 2026-11-02T20:58:45+00:00 by Launch Lab. Weights: `references/scoring.md`._

## Score: **83 / 100**  (before: 60, +23)

> Provisional: Clean install, Time to first success not measured, so the score is computed over the 75 measured points and scaled to 100.

## Categories

| Category | Weight | Score | Notes | Before |
|---|---:|---:|---|---:|
| Clarity (Stranger Panel) | 30 | 25.6 | understanding 100%, star intent 45%, 1/3 would star | 25.2 |
| Clean install | 15 | n/a | static check only (0 issues); run in Docker or approve local mode to measure | n/a |
| Time to first success | 10 | n/a | needs a measured install run | n/a |
| Demo | 10 | 3.0 | static image above the fold, no animated demo | 3.0 |
| Quickstart length | 8 | 8.0 | 1 command | 0.0 |
| Description, topics, license, badges | 10 | 10.0 | description set, 6 topics; license yes, 4 badges in fold | 8.0 |
| Comparison with alternatives | 7 | 7.0 | comparison table (How is this different from JWT?) | 0.0 |
| Social preview image | 5 | 5.0 | custom social preview set on GitHub | 5.0 |
| Contributing guide | 5 | 4.0 | README has a Contributing section but no CONTRIBUTING.md | 4.0 |

## Top 5 fixes (ranked by impact)

1. **Add a short demo GIF above the fold (/launch-lab demo)** (+7.0 pts, medium, Demo)  
   A demo shows the value faster than prose
2. **Add the proof personas asked for** (+1.8 pts, medium, Clarity (Stranger Panel))  
   What would make them star: "A short comparison section showing why this beats JWT / Django signing / raw hmac (key rotation, max_age expiry, algorithm choices), an explicit note that data is signed but NOT encrypted, and proof of maturity such as who depends on it, release history, or a security model/threat description."; "A short plain-English line right under the example saying: 'This signs data, it does not hide it (anyone can read the token, but nobody can change it without the key)', plus a tiny real use, such as a 5-line password-reset link with try/except BadSignature, so I know exactly when I would use it."; "Show proof of maturity above the fold: state the license in text (e.g. BSD/MIT), last release date and maintainer or org, a line on who uses it, and one sentence on how it differs from JWT and that it signs but does not encrypt (plus expiry support)."
3. **Answer the panel's confusions above the fold** (+1.3 pts, easy, Clarity (Stranger Panel))  
   Personas said: "How is this different from JWT / PyJWT, Django's signing module, or just using hmac directly? The README doesn't say."; "Is the payload encrypted or only signed? The example token is JSON, so I assume readable, but it isn't stated and a careless user could put secrets in it."; "What are the security guarantees: which algorithm (HMAC-SHA1? SHA256?), key rotation support, expiry/timestamps, replay protection? Nothing above the fold."; "What does 'salt' actually do here and when do I need it?"
4. **Add a CONTRIBUTING.md (GitHub links it from issues and PRs)** (+1.0 pts, easy, Contributing guide)  
   A README section is not shown in the new-issue/PR flow
5. **Run the clean install test** (unlocks measurement, easy, Clean install)  
   15% of the score is install success

## Stranger Panel

**True purpose:** A Python library that cryptographically signs (HMAC) serialized data so it can be sent through untrusted places such as cookies, URLs or emailed links, and verified as untampered (optionally not expired) when it comes back.  
**True audience:** Python web developers who need tamper-proof tokens, e.g. for sessions, password-reset or account-activation links.

| Persona | Understood it as | Purpose | Audience | Star? | Confidence |
|---|---|---:|---:|---|---:|
| Skeptical HN developer | A Python library that cryptographically signs data with a secret key so you can put it in a cookie, URL or emailed link and detect on return whether it was tampered with. | 1 | 1 | no | 60 |
| Beginner developer | It lets you put a secret-key signature on some data (like a user id) so that if you give it to someone else, like in a cookie or a link, you can tell if they changed it when it comes back. | 1 | 1 | yes | 55 |
| Busy CTO evaluating tools | A Python library that signs data (like a dict) with a secret key so you can put it in a cookie, URL or emailed link and detect on return if it was tampered with. | 1 | 1 | no | 60 |

**What confused them**

- skeptical-hn: How is this different from JWT / PyJWT, Django's signing module, or just using hmac directly? The README doesn't say.
- skeptical-hn: Is the payload encrypted or only signed? The example token is JSON, so I assume readable, but it isn't stated and a careless user could put secrets in it.
- skeptical-hn: What are the security guarantees: which algorithm (HMAC-SHA1? SHA256?), key rotation support, expiry/timestamps, replay protection? Nothing above the fold.
- skeptical-hn: What does 'salt' actually do here and when do I need it?
- skeptical-hn: The badges are just names with no visible status, so I can't tell whether the tests pass or how mature or maintained it is.
- skeptical-hn: No indication of who uses it, how old it is, or whether it is audited, so I can't tell if it's a weekend project or battle-tested.
- beginner: What exactly is a 'salt' and why is it set to 'auth'? Not explained.
- beginner: What is a 'serializer' and what do dumps/loads do? I only guess from the example.
- beginner: Does this encrypt the data or only sign it? Can someone read the token? The text doesn't say.
- beginner: What is the 'secret key' supposed to be in real use, and where do I keep it? 'secret key' in the example looks like a placeholder.
- beginner: Does it work on its own or only with a web framework? I can't tell from this part.
- beginner: What do the 'Tests' and 'License' badges say? I can't see status or version, so I can't tell if it's maintained.
- beginner: Why is the name 'ItsDangerous'? Is it risky to use? A bit scary for a beginner.
- beginner: The comment 'raises BadSignature' is shown but the example doesn't show how to handle it (try/except) even though BadSignature is imported.
- busy-cto: License badge is shown but the actual license is not stated in text, so I cannot tell if it is permissive.
- busy-cto: No visible signs of maintenance (last release, activity, who maintains it), and I cannot read the badges.
- busy-cto: Unclear whether it also encrypts: it says 'not changed' but does not say the contents are hidden, so a team might wrongly assume secrecy.
- busy-cto: Unclear how it differs from JWT or what I would use it instead of; no positioning vs. alternatives.
- busy-cto: No mention of token expiry or key rotation, which matter for real adoption.
- busy-cto: Unclear whether it is a standalone library or tied to a framework.
- busy-cto: No sign of who already uses it, so adoption risk is hard to judge.

**What would make them star it**

- skeptical-hn: A short comparison section showing why this beats JWT / Django signing / raw hmac (key rotation, max_age expiry, algorithm choices), an explicit note that data is signed but NOT encrypted, and proof of maturity such as who depends on it, release history, or a security model/threat description.
- beginner: A short plain-English line right under the example saying: 'This signs data, it does not hide it (anyone can read the token, but nobody can change it without the key)', plus a tiny real use, such as a 5-line password-reset link with try/except BadSignature, so I know exactly when I would use it.
- busy-cto: Show proof of maturity above the fold: state the license in text (e.g. BSD/MIT), last release date and maintainer or org, a line on who uses it, and one sentence on how it differs from JWT and that it signs but does not encrypt (plus expiry support).

## Clean install test

Mode: `static` | Result: **not run (static)** | Time to first success: n/a

No friction found.

---
_Launch Lab never posts or uploads anything. All results were computed locally._
