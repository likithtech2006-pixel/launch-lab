#!/usr/bin/env python3
"""Star Readiness Score (0-100) from scan.json, panel.json and install.json.

Usage: score.py [REPO] [--round N] [--before .launch-lab/score.round0.json]
                [--report launch/report.md] [--svg launch/score-card.svg] [--json]
Writes REPO/.launch-lab/score.json (+ score.round<N>.json), the Markdown report and the SVG card.
Weights and rationale: references/scoring.md (keep the two in sync).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launchlab_common as C  # noqa: E402
from panel import summary as panel_summary, validate as panel_validate  # noqa: E402

WEIGHTS = {
    "clarity": 30,          # Stranger Panel: understanding 22 + star intent 8
    "install": 15,          # Clean install test passed
    "time_to_success": 10,  # Time to first success
    "demo": 10,             # Animated demo, ideally above the fold
    "quickstart": 8,        # Short, copy-pasteable quickstart near the top
    "metadata": 10,         # Description, topics, license, badges
    "comparison": 7,        # Honest comparison with alternatives
    "social_preview": 5,    # Custom social preview image
    "contributing": 5,      # Contributing guide
}
LABELS = {
    "clarity": "Clarity (Stranger Panel)", "install": "Clean install", "time_to_success": "Time to first success",
    "demo": "Demo", "quickstart": "Quickstart length", "metadata": "Description, topics, license, badges",
    "comparison": "Comparison with alternatives", "social_preview": "Social preview image", "contributing": "Contributing guide",
}
EASE = {"easy": 1.0, "medium": 0.75, "hard": 0.5}


def cat(fraction=None, notes="", fixes=None, measured=True, detail=None):
    return {"fraction": None if fraction is None else round(max(0.0, min(1.0, fraction)), 3), "measured": measured and fraction is not None,
            "notes": notes, "fixes": fixes or [], "detail": detail or {}}


def fix(title, why, ease="easy", share=1.0):
    return {"title": title, "why": why, "ease": ease, "share": share}


# ---------------------------------------------------------------- categories

def score_clarity(panel):
    if not panel:
        return cat(None, "Stranger Panel not run", [fix("Run the Stranger Panel", "Clarity is 30% of the score and cannot be estimated without it")], measured=False)
    errs = panel_validate(panel)
    if errs:
        return cat(None, "panel.json invalid: " + "; ".join(errs[:3]), measured=False)
    s = panel_summary(panel)
    frac = (22 * s["understanding"] + 8 * s["star_intent"]) / 30
    fixes = []
    confusions = [c for p in panel["personas"] for c in p["response"].get("confusions", [])]
    asks = [p["response"].get("would_make_me_star", "") for p in panel["personas"] if p["response"].get("would_make_me_star")]
    if s["clarity_failures"]:
        fixes.append(fix("Rewrite the tagline so a stranger can say what the project does",
                         f"{len(s['clarity_failures'])} of {s['personas']} personas misread the purpose ({', '.join(s['clarity_failures'])}). "
                         f"True purpose: {panel['truth']['purpose']}", "easy", 0.7))
    elif s["understanding"] < 0.9:
        fixes.append(fix("Sharpen the first two lines: what it is, who it is for, why it is different",
                         f"Understanding {s['understanding']:.0%}; personas were only partly right", "easy", 0.6))
    if confusions:
        fixes.append(fix("Answer the panel's confusions above the fold",
                         "Personas said: " + "; ".join(f'"{c}"' for c in confusions[:4]), "easy", 0.3))
    if s["star_intent"] < 0.6 and asks:
        fixes.append(fix("Add the proof personas asked for",
                         "What would make them star: " + "; ".join(f'"{x}"' for x in asks[:3]), "medium", 0.4))
    return cat(frac, f"understanding {s['understanding']:.0%}, star intent {s['star_intent']:.0%}, "
                     f"{s['would_star']}/{s['personas']} would star", fixes, detail=s)


def score_install(inst):
    if not inst or not inst.get("measured"):
        n = len((inst or {}).get("friction", []))
        note = "not run" if not inst else f"static check only ({n} issues); run in Docker or approve local mode to measure"
        return (cat(None, note, [fix("Run the clean install test", "15% of the score is install success")], measured=False),
                cat(None, "needs a measured install run", measured=False))
    runnable = [s for s in inst["steps"] if s.get("status")]
    passed = [s for s in runnable if s["status"] == "ok"]
    fr = inst.get("friction", [])
    fixes = [fix(f["fix_hint"], f"{f['type'].replace('_', ' ')}: {f['detail']}" + (f" (step: `{f['step']}`)" if f.get("step") else ""),
                 "easy" if f["type"] in ("unstated_version", "undocumented_env_var", "missing_prerequisite", "unclear_step") else "medium",
                 1.0 if f["severity"] == "blocker" else 0.3)
             for f in fr if f["severity"] in ("blocker", "major")][:3]
    if inst.get("success"):
        majors = sum(1 for f in fr if f["severity"] == "major")
        frac = 1 - min(0.3, 0.1 * majors)
        note = f"passed {len(passed)}/{len(runnable)} steps ({inst['mode']})"
    else:
        frac = 0.5 * (len(passed) / len(runnable)) if runnable else 0.0
        note = f"FAILED after {len(passed)}/{len(runnable)} steps ({inst['mode']})"
    t = inst.get("time_to_first_success_s")
    if t is None:
        tts = cat(0.0, "no successful run", [fix("Make the install succeed first", "Time to first success needs a passing install", "medium")])
    else:
        bands = [(60, 1.0), (120, 0.85), (300, 0.6), (600, 0.35)]
        f2 = next((v for lim, v in bands if t <= lim), 0.15)
        tts = cat(f2, f"{t:.0f}s from first command to success",
                  [] if f2 >= 1 else [fix("Cut install time (prebuilt package, fewer steps, smaller deps)", f"Currently {t:.0f}s; under 60s scores full", "hard")])
    return cat(frac, note, fixes, detail={"mode": inst["mode"], "steps": len(runnable)}), tts


def score_demo(scan):
    sig = scan["signals"]
    if sig["demo_in_fold"]:
        return cat(1.0, "animated demo above the fold")
    if sig["demo_media"]:
        return cat(0.6, "animated demo exists but below the fold",
                   [fix("Move the demo GIF to directly under the tagline", "Visitors decide before scrolling", "easy")])
    if sig["image_in_fold"]:
        return cat(0.3, "static image above the fold, no animated demo",
                   [fix("Add a short demo GIF above the fold (/launch-lab demo)", "A demo shows the value faster than prose", "medium")])
    return cat(0.0, "no demo", [fix("Add a short demo GIF above the fold (/launch-lab demo)", "No visual proof the project works", "medium")])


def score_quickstart(scan, inst):
    qs = scan["quickstart"]
    if not qs["section"]:
        return cat(0.0, "no install/quickstart section", [fix("Add a '## Quickstart' with one install and one run command", "Strangers look for it first")])
    n = qs["command_count"]
    if n == 0:
        frac, note = 0.2, "quickstart section has no shell commands"
    elif n <= 3:
        frac, note = 1.0, f"{n} command{'s' if n > 1 else ''}"
    elif n <= 6:
        frac, note = 0.7, f"{n} commands"
    elif n <= 10:
        frac, note = 0.4, f"{n} commands"
    else:
        frac, note = 0.2, f"{n} commands"
    fixes = []
    if n > 3:
        fixes.append(fix("Shorten the quickstart to 3 commands or fewer", f"It has {n}; move extras to a Configuration section", "easy", 0.8))
    if qs["section_line"] and qs["section_line"] > 80:
        frac *= 0.8
        note += f", starts at line {qs['section_line']}"
        fixes.append(fix("Move the quickstart higher (before line 80)", "Readers should not hunt for it", "easy", 0.2))
    unclear = [s for s in (inst or {}).get("steps", []) if s.get("action") == "unclear"]
    if unclear:
        frac -= 0.15 * len(unclear)
        note += f", {len(unclear)} placeholder step(s)"
    return cat(frac, note, fixes)


def score_metadata(scan):
    gh, sig = scan["github"], scan["signals"]
    parts, fixes, notes = [], [], []
    if gh["source"] != "none":
        d = gh.get("description")
        parts.append((3, 1.0 if d and len(d) >= 20 else 0.5 if d else 0.0))
        if not d:
            fixes.append(fix("Set the GitHub repo description (About)", "It appears in search results and link previews"))
        t = gh.get("topics") or []
        parts.append((3, 1.0 if len(t) >= 3 else 0.5 if t else 0.0))
        if len(t) < 3:
            fixes.append(fix("Add 3-8 GitHub topics", f"{len(t)} topics set; topics drive GitHub search and Explore"))
        notes.append(f"description {'set' if d else 'missing'}, {len(t)} topics")
    else:
        notes.append("GitHub description/topics unknown (repo not on GitHub or offline)")
        fixes.append(fix("Set the GitHub description and 3-8 topics when you publish", "Not measurable yet; set them on day one", "easy", 0.0))
    lic = sig["license_file"] or gh.get("license")
    parts.append((2, 1.0 if lic else 0.0))
    if not lic:
        fixes.append(fix("Add a LICENSE file (MIT or Apache-2.0)", "No license means legally unusable; many people will not star it", "easy"))
    b = sig["badges_in_fold"]
    parts.append((2, 0.0 if b == 0 else 1.0 if b <= 6 else 0.5))
    if b == 0:
        fixes.append(fix("Add 2-4 meaningful badges (license, CI, version)", "Cheap maturity signal for evaluators", "easy", 0.3))
    elif b > 6:
        fixes.append(fix(f"Trim the badge wall ({b} badges) to the 3-4 that matter", "Too many badges push the tagline down", "easy", 0.3))
    notes.append(f"license {'yes' if lic else 'no'}, {b} badges in fold")
    total = sum(w for w, _ in parts)
    return cat(sum(w * f for w, f in parts) / total, "; ".join(notes), fixes)


def score_social(scan):
    gh, f = scan["github"], scan["signals"]["social_preview_file"]
    if gh.get("social_preview_custom"):
        return cat(1.0, "custom social preview set on GitHub")
    if f:
        return cat(0.5, f"image in repo ({f}) but not confirmed as the GitHub social preview",
                   [fix("Upload the social preview in GitHub Settings > General > Social preview", f"Use {f} (1280x640)", "easy")])
    return cat(0.0, "no social preview", [fix("Create a 1280x640 social preview image and upload it", "Links shared on X/LinkedIn/Slack show a generic card otherwise", "medium")])


def score_comparison(scan):
    c = scan["signals"]["comparison"]
    if c["present"] and c["table"]:
        return cat(1.0, f"comparison table ({c['heading'] or 'table'})")
    if c["present"]:
        return cat(0.7, f"comparison section without a table ({c['heading']})",
                   [fix("Turn the comparison into a small honest table", "Tables are scannable; include where alternatives win", "easy")])
    return cat(0.0, "no comparison with alternatives",
               [fix("Add a 'How is this different?' table vs 2-4 alternatives", "The first question on HN is 'why not X?'", "medium")])


def score_contributing(scan):
    c = scan["signals"]["contributing"]
    if c:
        return cat(1.0, c)
    if scan["signals"].get("contributing_section"):
        return cat(0.8, "README has a Contributing section but no CONTRIBUTING.md",
                   [fix("Add a CONTRIBUTING.md (GitHub links it from issues and PRs)", "A README section is not shown in the new-issue/PR flow", "easy")])
    return cat(0.0, "no CONTRIBUTING.md", [fix("Add CONTRIBUTING.md (setup, tests, how to propose changes)", "Signals the project welcomes help", "easy")])


# ---------------------------------------------------------------- assemble

def compute(root: Path) -> dict:
    scan = C.read_json(root / C.STATE_DIR / "scan.json")
    if not scan:
        raise SystemExit("no .launch-lab/scan.json - run scan.py first")
    panel = C.read_json(root / C.STATE_DIR / "panel.json")
    inst = C.read_json(root / C.STATE_DIR / "install.json")
    stale = []
    if panel and panel.get("fold_sha") and panel["fold_sha"] != scan["fold"]["sha"]:
        stale.append("panel was run on an older README fold")
    if inst and inst.get("readme_sha") and inst["readme_sha"] != scan["readme_sha"]:
        stale.append("install test was run on an older README")
    install, tts = score_install(inst)
    cats = {
        "clarity": score_clarity(panel), "install": install, "time_to_success": tts, "demo": score_demo(scan),
        "quickstart": score_quickstart(scan, inst), "metadata": score_metadata(scan), "comparison": score_comparison(scan),
        "social_preview": score_social(scan), "contributing": score_contributing(scan),
    }
    measured_w = sum(WEIGHTS[k] for k, c in cats.items() if c["measured"])
    earned = sum(WEIGHTS[k] * c["fraction"] for k, c in cats.items() if c["measured"])
    for k, c in cats.items():
        c["weight"] = WEIGHTS[k]
        c["points"] = round(WEIGHTS[k] * c["fraction"], 1) if c["measured"] else None
    fixes = []
    for k, c in cats.items():
        lost = WEIGHTS[k] * (1 - (c["fraction"] or 0)) if c["measured"] else WEIGHTS[k] * 0.5
        for f in c["fixes"]:
            gain = lost * f["share"] * (1.0 if c["measured"] else 0.0)
            fixes.append({**f, "category": k, "gain": round(gain, 1), "rank": gain * EASE[f["ease"]] + (0.01 if not c["measured"] else 0)})
    fixes.sort(key=lambda f: -f["rank"])
    unmeasured = [k for k, c in cats.items() if not c["measured"]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": scan["name"],
        "score": round(100 * earned / measured_w) if measured_w else 0,
        "provisional": bool(unmeasured),
        "unmeasured": unmeasured,
        "measured_weight": measured_w,
        "stale": stale,
        "categories": cats,
        "top_fixes": fixes[:5],
        "all_fixes": fixes,
        "repo_type": scan["repo_type"]["type"],
        "panel": panel,
        "install": inst and {k: inst.get(k) for k in ("mode", "success", "time_to_first_success_s", "friction", "steps")},
    }


def render_report(res: dict, before: dict | None) -> str:
    L = []
    title = f"# Star Readiness Report: {res['repo']}"
    L += [title, "", f"_Generated {res['generated_at']} by Launch Lab. Weights: `references/scoring.md`._", ""]
    head = f"## Score: **{res['score']} / 100**"
    if before:
        d = res["score"] - before["score"]
        head += f"  (before: {before['score']}, {'+' if d >= 0 else ''}{d})"
    L += [head, ""]
    if res["provisional"]:
        L += [f"> Provisional: {', '.join(LABELS[k] for k in res['unmeasured'])} not measured, so the score is "
              f"computed over the {res['measured_weight']} measured points and scaled to 100.", ""]
    for s in res["stale"]:
        L += [f"> Warning: {s}. Re-run it for an accurate score.", ""]
    L += ["## Categories", "", "| Category | Weight | Score | Notes |" + (" Before |" if before else ""),
          "|---|---:|---:|---|" + ("---:|" if before else "")]
    for k, c in res["categories"].items():
        pts = f"{c['points']:.1f}" if c["measured"] else "n/a"
        row = f"| {LABELS[k]} | {c['weight']} | {pts} | {c['notes']} |"
        if before:
            bc = before["categories"].get(k, {})
            row += f" {bc['points']:.1f} |" if bc.get("measured") else " n/a |"
        L.append(row)
    L += ["", "## Top 5 fixes (ranked by impact)", ""]
    if not res["top_fixes"]:
        L.append("Nothing significant left to fix.")
    for i, f in enumerate(res["top_fixes"], 1):
        gain = f"+{f['gain']:.1f} pts" if f["gain"] else "unlocks measurement"
        L.append(f"{i}. **{f['title']}** ({gain}, {f['ease']}, {LABELS[f['category']]})  \n   {f['why']}")
    p = res.get("panel")
    if p and not panel_validate(p):
        L += ["", "## Stranger Panel", "", f"**True purpose:** {p['truth']['purpose']}  ", f"**True audience:** {p['truth']['audience']}", "",
              "| Persona | Understood it as | Purpose | Audience | Star? | Confidence |", "|---|---|---:|---:|---|---:|"]
        for x in p["personas"]:
            r, g = x["response"], x["grade"]
            L.append(f"| {x.get('name', x['id'])} | {r['what_it_does'].replace('|', '/')} | {g['purpose_match']} | {g['audience_match']} | "
                     f"{'yes' if r['would_star'] else 'no'} | {r['confidence']} |")
        L += ["", "**What confused them**", ""]
        for x in p["personas"]:
            for c in x["response"].get("confusions", []):
                L.append(f"- {x['id']}: {c}")
        L += ["", "**What would make them star it**", ""]
        for x in p["personas"]:
            L.append(f"- {x['id']}: {x['response'].get('would_make_me_star', '')}")
    inst = res.get("install")
    if inst:
        L += ["", "## Clean install test", "",
              f"Mode: `{inst['mode']}` | Result: **{ {True: 'passed', False: 'failed', None: 'not run (static)'}[inst['success']] }** | "
              f"Time to first success: {str(inst['time_to_first_success_s']) + 's' if inst['time_to_first_success_s'] is not None else 'n/a'}", ""]
        if inst["friction"]:
            L += ["| Severity | Type | Detail | Fix |", "|---|---|---|---|"]
            for f in inst["friction"]:
                L.append(f"| {f['severity']} | {f['type']} | {f['detail'].replace('|', '/')} | {f['fix_hint'].replace('|', '/')} |")
        else:
            L.append("No friction found.")
    L += ["", "---", "_Launch Lab never posts or uploads anything. All results were computed locally._", ""]
    return "\n".join(L)


def render_svg(res: dict, before: dict | None) -> str:
    W, H = 720, 360 if not before else 380
    score = res["score"]
    color = "#1a7f37" if score >= 80 else "#9a6700" if score >= 60 else "#cf222e"
    r, cx, cy = 70, 120, 170
    circ = 2 * 3.14159 * r
    dash = circ * score / 100
    rows = []
    y = 64
    for k, c in res["categories"].items():
        frac = c["fraction"] if c["measured"] else None
        bw = 250
        label = html.escape(LABELS[k])
        rows.append(f'<text x="290" y="{y + 11}" class="lbl">{label}</text>')
        rows.append(f'<rect x="530" y="{y + 1}" width="{bw * 0.5:.0f}" height="12" rx="6" class="track"/>')
        if frac is None:
            rows.append(f'<text x="660" y="{y + 11}" class="val">n/a</text>')
        else:
            rows.append(f'<rect x="530" y="{y + 1}" width="{max(2, bw * 0.5 * frac):.0f}" height="12" rx="6" fill="{color}" opacity="0.85"/>')
            if before and before["categories"].get(k, {}).get("measured"):
                bf = before["categories"][k]["fraction"]
                rows.append(f'<rect x="530" y="{y + 16}" width="{max(2, bw * 0.5 * bf):.0f}" height="4" rx="2" class="prev"/>')
            rows.append(f'<text x="660" y="{y + 11}" class="val">{c["points"]:.0f}/{c["weight"]}</text>')
        y += 30
    sub = f"before {before['score']}  →  after {score}" if before else ("provisional" if res["provisional"] else "Star Readiness Score")
    legend = ('<rect x="290" y="{0}" width="10" height="4" rx="2" transform="translate(0 3)" class="prev"/><text x="306" y="{1}" class="small">before</text>'
              '<rect x="360" y="{0}" width="10" height="10" rx="5" fill="{2}"/><text x="376" y="{1}" class="small">after</text>').format(H - 30, H - 21, color) if before else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Star Readiness Score {score} out of 100">
<style>
  .bg {{ fill: #ffffff; stroke: #d0d7de; }} .title {{ fill: #1f2328; font: 600 18px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .lbl {{ fill: #1f2328; font: 13px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .val {{ fill: #59636e; font: 600 12px ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .small {{ fill: #59636e; font: 12px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .big {{ fill: #1f2328; font: 700 44px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .track {{ fill: #eaeef2; }} .prev {{ fill: #8c959f; }} .ring {{ stroke: #eaeef2; }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ fill: #0d1117; stroke: #30363d; }} .title, .lbl, .big {{ fill: #e6edf3; }} .val, .small {{ fill: #9198a1; }}
    .track {{ fill: #21262d; }} .ring {{ stroke: #21262d; }} .prev {{ fill: #6e7681; }}
  }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" class="bg"/>
<text x="24" y="38" class="title">Launch Lab · {html.escape(res['repo'])}</text>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke-width="14" class="ring"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round"
  stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>
<text x="{cx}" y="{cy + 15}" text-anchor="middle" class="big">{score}</text>
<text x="{cx}" y="{cy + 40}" text-anchor="middle" class="small">/ 100</text>
<text x="{cx}" y="{cy + r + 42}" text-anchor="middle" class="small">{html.escape(sub)}</text>
{chr(10).join(rows)}
{legend}
</svg>
"""


def write_outputs(root, res, before, a):
    C.write_json(C.state_path(root, "score.json"), res)
    if a.round is not None:
        C.write_json(C.state_path(root, f"score.round{a.round}.json"), res)
    report = Path(a.report) if a.report else C.out_path(root, "report.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_report(res, before), encoding="utf-8")
    svg = Path(a.svg) if a.svg else C.out_path(root, "score-card.svg")
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(render_svg(res, before), encoding="utf-8")
    return report, svg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--round", type=int)
    ap.add_argument("--before", help="earlier score JSON to compare against")
    ap.add_argument("--report")
    ap.add_argument("--svg")
    ap.add_argument("--json", action="store_true", help="print the full result JSON")
    ap.add_argument("--print-only", action="store_true", help="print the score; write no files")
    a = ap.parse_args()
    root = C.repo_root(a.repo)
    res = compute(root)
    res["round"] = a.round
    before = C.read_json(Path(a.before) if Path(a.before or "").is_absolute() else root / (a.before or ""), None) if a.before else None
    if a.before and not before:
        print(f"warning: could not read {a.before}", file=sys.stderr)
    if before:
        res["before"] = {"score": before["score"], "round": before.get("round")}
    if a.print_only:
        report = svg = None
    else:
        report, svg = write_outputs(root, res, before, a)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    width = shutil.get_terminal_size((110, 24)).columns
    flag = " (provisional)" if res["provisional"] else ""
    tty = (sys.stdout.isatty() or os.environ.get("FORCE_COLOR")) and not os.environ.get("NO_COLOR")
    sc = res["score"]
    col = ("\x1b[32m" if sc >= 80 else "\x1b[33m" if sc >= 60 else "\x1b[31m") if tty else ""
    print(f"Star Readiness Score: {col}{sc}/100{chr(27) + '[0m' if tty else ''}{flag}" + (f"  [before {before['score']}]" if before else ""))
    for k, c in res["categories"].items():
        pts = f"{c['points']:>5.1f}" if c["measured"] else "  n/a"
        line = f"  {LABELS[k]:<37} {pts} / {c['weight']:<3} {c['notes']}"
        print(line if len(line) <= width else line[:width - 1] + "…")
    print("Top fixes:")
    for i, f in enumerate(res["top_fixes"], 1):
        gain = f"+{f['gain']} pts" if res["categories"][f["category"]]["measured"] else "unlocks measurement"
        line = f"  {i}. {f['title']}  ({gain}, {f['ease']})"
        print(line if len(line) <= width else line[:width - 1] + "…")
    if report:
        print(f"-> {report}\n-> {svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
