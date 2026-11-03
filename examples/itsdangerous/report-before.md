# Star Readiness Report: itsdangerous

_Generated 2026-11-02T20:58:23+00:00 by Launch Lab. Weights: `references/scoring.md`._

## Score: **60 / 100**

> Provisional: Clean install, Time to first success not measured, so the score is computed over the 75 measured points and scaled to 100.

## Categories

| Category | Weight | Score | Notes |
|---|---:|---:|---|
| Clarity (Stranger Panel) | 30 | 25.2 | understanding 100%, star intent 40%, 0/3 would star |
| Clean install | 15 | n/a | static check only (3 issues); run in Docker or approve local mode to measure |
| Time to first success | 10 | n/a | needs a measured install run |
| Demo | 10 | 3.0 | static image above the fold, no animated demo |
| Quickstart length | 8 | 0.0 | no install/quickstart section |
| Description, topics, license, badges | 10 | 8.0 | description set, 6 topics; license yes, 0 badges in fold |
| Comparison with alternatives | 7 | 0.0 | no comparison with alternatives |
| Social preview image | 5 | 5.0 | custom social preview set on GitHub |
| Contributing guide | 5 | 4.0 | README has a Contributing section but no CONTRIBUTING.md |

## Top 5 fixes (ranked by impact)

1. **Add a '## Quickstart' with one install and one run command** (+8.0 pts, easy, Quickstart length)  
   Strangers look for it first
2. **Add a short demo GIF above the fold (/launch-lab demo)** (+7.0 pts, medium, Demo)  
   A demo shows the value faster than prose
3. **Add a 'How is this different?' table vs 2-4 alternatives** (+7.0 pts, medium, Comparison with alternatives)  
   The first question on HN is 'why not X?'
4. **Add the proof personas asked for** (+1.9 pts, medium, Clarity (Stranger Panel))  
   What would make them star: "A short comparison against JWT and similar signing libraries (what it does differently and why), plus a complete round trip example (dumps then loads, including expiry/bad-signature handling) and a clear statement of the algorithm and security guarantees (signed, not encrypted)."; "A short, complete example right at the top with pip install, creating a token, printing it, and loading it back (plus what happens if someone changes it), with plain-English explanation and maintenance badges so I know I could run it in five minutes."; "Show a badge row with license, latest release, CI status and Python versions, plus a one-line install command and a complete sign-and-verify example in the visible area."
5. **Answer the panel's confusions above the fold** (+1.4 pts, easy, Clarity (Stranger Panel))  
   Personas said: "The code snippet is cut off: it never shows verifying/loading the token, so I can't see the full usage"; "What the 'auth' second argument to URLSafeSerializer does (salt?) is not explained"; "How this differs from JWT/PyJWT or Django's/other signing utilities is not stated"; "What crypto is used (HMAC? which hash?) is not stated; 'cryptographically signed' is vague"

## Stranger Panel

**True purpose:** A Python library that cryptographically signs (HMAC) serialized data so it can be sent through untrusted places such as cookies, URLs or emailed links, and verified as untampered (optionally not expired) when it comes back.  
**True audience:** Python web developers who need tamper-proof tokens, e.g. for sessions, password-reset or account-activation links.

| Persona | Understood it as | Purpose | Audience | Star? | Confidence |
|---|---|---:|---:|---|---:|
| Skeptical HN developer | A Python library that signs data (e.g. a dict) with a secret key so you can hand it to an untrusted client as a token and later verify it wasn't tampered with, with optional timestamps and compression. | 1 | 1 | no | 60 |
| Beginner developer | It's a Python library that signs data (like a user id and name) so you can hand it to an untrusted place, like a browser, and later check it hasn't been changed. | 1 | 1 | no | 60 |
| Busy CTO evaluating tools | A Python library that cryptographically signs data (like a user id and name) into a token so you can hand it to an untrusted party and detect tampering when it comes back, with optional timestamps and custom serialization. | 1 | 1 | no | 60 |

**What confused them**

- skeptical-hn: The code snippet is cut off: it never shows verifying/loading the token, so I can't see the full usage
- skeptical-hn: What the 'auth' second argument to URLSafeSerializer does (salt?) is not explained
- skeptical-hn: How this differs from JWT/PyJWT or Django's/other signing utilities is not stated
- skeptical-hn: What crypto is used (HMAC? which hash?) is not stated; 'cryptographically signed' is vague
- skeptical-hn: Is data encrypted or only signed? Readers might assume secrecy; text doesn't clarify
- skeptical-hn: No badges or text showing maturity, maintenance, or tests; the name and tagline 'so better sign this' are cutesy
- skeptical-hn: 'Data is compressed as needed' is vague
- beginner: No install command (pip install?) visible, so I can't tell how to get it running
- beginner: The code example is cut off: it makes a token but I don't see what comes out or how to check/load it
- beginner: Words like 'cryptographically signed', 'serialized', 'untrusted environments' and 'tampered' are jargon to me
- beginner: Not sure how signing differs from encrypting, or whether the data is hidden or just protected from changes
- beginner: 'URLSafeSerializer', 'secret key' and the 'auth' argument aren't explained
- beginner: No sign it's maintained: no badges, version, or docs link visible
- beginner: The tagline '... so better sign this' is cute but doesn't tell me anything
- beginner: Can't tell if it needs a web framework or works on its own
- busy-cto: No license shown above the fold, so I cannot tell if it is permissive.
- busy-cto: No maintenance signals visible: no release, CI, or activity badges, only a logo image.
- busy-cto: Which signing algorithm and crypto it uses, and how secure it is, is not stated.
- busy-cto: The code example is cut off; I do not see how to verify/load the token or install it.
- busy-cto: Unclear how this compares to JWT or what my team would use it for compared to existing auth libraries.
- busy-cto: No install command, supported Python versions, or adoption/user info.
- busy-cto: The tagline '... so better sign this' is cute but tells me nothing concrete.

**What would make them star it**

- skeptical-hn: A short comparison against JWT and similar signing libraries (what it does differently and why), plus a complete round trip example (dumps then loads, including expiry/bad-signature handling) and a clear statement of the algorithm and security guarantees (signed, not encrypted).
- beginner: A short, complete example right at the top with pip install, creating a token, printing it, and loading it back (plus what happens if someone changes it), with plain-English explanation and maintenance badges so I know I could run it in five minutes.
- busy-cto: Show a badge row with license, latest release, CI status and Python versions, plus a one-line install command and a complete sign-and-verify example in the visible area.

## Clean install test

Mode: `static` | Result: **not run (static)** | Time to first success: n/a

| Severity | Type | Detail | Fix |
|---|---|---|---|
| blocker | unclear_step | No runnable install commands found in shell code blocks | Put install commands in ```bash code blocks under the Quickstart heading. |
| major | unclear_step | README has no Install / Quickstart / Getting started section | Add a '## Quickstart' section with copy-pasteable commands near the top. |
| minor | unstated_version | Project requires python >=3.10 but the README never says so | State the requirement in a Prerequisites line, e.g. 'python >=3.10'. |

---
_Launch Lab never posts or uploads anything. All results were computed locally._
