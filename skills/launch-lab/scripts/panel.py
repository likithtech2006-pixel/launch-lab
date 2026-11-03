#!/usr/bin/env python3
"""Stranger Panel helper: build fold-only persona prompts and validate panel results.

Usage:
  panel.py prompts [REPO]     write .launch-lab/panel_prompts.json from scan.json + personas
  panel.py validate [REPO]    check .launch-lab/panel.json against the schema; print a summary

Custom personas: add a "personas" list to REPO/.launch-lab/config.json, each with
id, name, brief and star_bar. Set "replace_default_personas": true to drop the defaults.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launchlab_common as C  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
RESPONSE_KEYS = {
    "what_it_does": str,
    "who_its_for": str,
    "would_star": bool,
    "confidence": int,
    "confusions": list,
    "would_make_me_star": str,
}
GRADE_VALUES = {0, 0.5, 1}

PROMPT = """You are role-playing a first-time visitor to a GitHub repository. Stay in character.

PERSONA: {name}
{brief}
Star bar: {star_bar}

You have about 10 seconds. You see ONLY the part of the README that is visible before scrolling,
reproduced between the markers below. Images are described in brackets because you cannot see
pixels: [badge: ...], [image: ...] or [animated image: ...] with their alt text or filename.

Rules:
- Judge only from the text between the markers. Do not use any tools, do not browse, do not look
  anything up, and do not guess from the project name what it "probably" is beyond what the text says.
- If something is unclear, say so instead of filling the gap.

=== ABOVE THE FOLD (start) ===
{fold}
=== ABOVE THE FOLD (end) ===

Reply with ONLY a JSON object, no prose and no code fence, with exactly these keys:
{{
  "what_it_does": "one sentence in your own words",
  "who_its_for": "who you think the target user is",
  "would_star": true or false,
  "confidence": integer 0-100 (how sure you are of your would_star answer),
  "confusions": ["each thing that confused you or that you could not tell"],
  "would_make_me_star": "the single change or proof that would make you star it"
}}"""


def personas(root: Path) -> list[dict]:
    defaults = C.read_json(SKILL_DIR / "assets" / "personas.default.json", [])
    cfg = C.load_config(root)
    custom = cfg.get("personas") or []
    chosen = ([] if cfg.get("replace_default_personas") else defaults) + custom
    seen, out = set(), []
    for p in chosen:
        missing = {"id", "name", "brief"} - set(p)
        if missing:
            raise SystemExit(f"persona {p.get('id', '?')} is missing {sorted(missing)} in .launch-lab/config.json")
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        out.append({"star_bar": "Stars what they would want to find again.", **p})
    return out


def cmd_prompts(root: Path) -> int:
    scan = C.read_json(root / C.STATE_DIR / "scan.json")
    if not scan:
        print("no .launch-lab/scan.json - run scan.py first", file=sys.stderr)
        return 2
    fold = scan["fold"]["rendered"]
    prompts = [{"id": p["id"], "name": p["name"], "prompt": PROMPT.format(fold=fold, **p)} for p in personas(root)]
    out = C.state_path(root, "panel_prompts.json")
    C.write_json(out, {"fold_sha": scan["fold"]["sha"], "fold_lines": scan["fold"]["lines"], "prompts": prompts})
    print(f"{len(prompts)} persona prompts -> {out}")
    for p in prompts:
        print(f"  - {p['id']}: {p['name']}")
    return 0


def validate(panel: dict) -> list[str]:
    errs = []
    truth = panel.get("truth") or {}
    for k in ("purpose", "audience"):
        if not isinstance(truth.get(k), str) or not truth[k].strip():
            errs.append(f"truth.{k} missing")
    ps = panel.get("personas")
    if not isinstance(ps, list) or len(ps) < 3:
        errs.append("need at least 3 personas")
        return errs
    for p in ps:
        pid = p.get("id", "?")
        r = p.get("response") or {}
        for k, t in RESPONSE_KEYS.items():
            if k not in r:
                errs.append(f"{pid}: response.{k} missing")
            elif t is int and not (isinstance(r[k], (int, float)) and 0 <= r[k] <= 100):
                errs.append(f"{pid}: response.confidence must be 0-100")
            elif t is not int and not isinstance(r[k], t):
                errs.append(f"{pid}: response.{k} must be {t.__name__}")
        g = p.get("grade") or {}
        for k in ("purpose_match", "audience_match"):
            if g.get(k) not in GRADE_VALUES:
                errs.append(f"{pid}: grade.{k} must be 0, 0.5 or 1")
    return errs


def p_star(r: dict) -> float:
    c = max(0, min(100, float(r.get("confidence", 50)))) / 100
    return c if r.get("would_star") else 1 - c


def summary(panel: dict) -> dict:
    ps = panel["personas"]
    und = [0.7 * p["grade"]["purpose_match"] + 0.3 * p["grade"]["audience_match"] for p in ps]
    stars = [p_star(p["response"]) for p in ps]
    return {
        "personas": len(ps),
        "understanding": round(sum(und) / len(und), 3),
        "star_intent": round(sum(stars) / len(stars), 3),
        "clarity_failures": [p["id"] for p in ps if p["grade"]["purpose_match"] == 0],
        "would_star": sum(1 for p in ps if p["response"]["would_star"]),
    }


def cmd_validate(root: Path) -> int:
    panel = C.read_json(root / C.STATE_DIR / "panel.json")
    if not panel:
        print("no .launch-lab/panel.json", file=sys.stderr)
        return 2
    errs = validate(panel)
    if errs:
        print("panel.json is invalid:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    scan = C.read_json(root / C.STATE_DIR / "scan.json") or {}
    if scan and panel.get("fold_sha") and panel["fold_sha"] != scan["fold"]["sha"]:
        print("warning: panel was run on a different fold than the current README (re-run the panel)", file=sys.stderr)
    s = summary(panel)
    print(f"{'persona':<16} {'purpose':>7} {'audience':>8} {'star?':>6} {'conf':>5}")
    for p in panel["personas"]:
        g, r = p["grade"], p["response"]
        print(f"{p['id']:<16} {g['purpose_match']:>7} {g['audience_match']:>8} {('yes' if r['would_star'] else 'no'):>6} {r['confidence']:>5}")
    print(f"\nunderstanding {s['understanding']:.0%} | star intent {s['star_intent']:.0%} | "
          f"{s['would_star']}/{s['personas']} would star | clarity failures: {', '.join(s['clarity_failures']) or 'none'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["prompts", "validate"])
    ap.add_argument("repo", nargs="?", default=".")
    a = ap.parse_args()
    root = C.repo_root(a.repo)
    return cmd_prompts(root) if a.command == "prompts" else cmd_validate(root)


if __name__ == "__main__":
    sys.exit(main())
