#!/usr/bin/env python3
"""Post-launch star conversion diagnosis from GitHub traffic + star history.

Usage:
  github_metrics.py --repo OWNER/NAME [--repo-dir .] [--no-save]
  github_metrics.py --from-file metrics.json [--repo-dir .]    offline (evals, saved exports)

Needs `gh auth login` with push access to the repo (GitHub only shows traffic to collaborators).
Appends a snapshot to REPO/.launch-lab/history.json and writes REPO/launch/diagnosis.md.
Rules and thresholds: references/diagnosis.md.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launchlab_common as C  # noqa: E402

DEFAULTS = {"high_traffic_per_day": 30, "low_conversion": 0.02, "high_conversion": 0.04,
            "spike_factor": 4.0, "flat_ratio": 0.25, "min_uniques": 10, "max_star_pages": 100}


# ---------------------------------------------------------------- fetch

def gh_json(path: str, accept: str | None = None, paginate: bool = False):
    cmd = ["gh", "api", path]
    if accept:
        cmd += ["-H", f"Accept: {accept}"]
    if paginate:
        cmd += ["--paginate", "--slurp"]  # --slurp: one JSON array of pages (gh >= 2.48)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {path}: {(r.stderr or r.stdout).strip()[:300]}")
    data = json.loads(r.stdout.strip() or "null")
    if paginate and isinstance(data, list):
        data = [item for page in data for item in (page if isinstance(page, list) else [page])]
    return data


def fetch(slug: str, max_pages: int) -> dict:
    if not shutil.which("gh"):
        raise RuntimeError("gh CLI not found; install it from https://cli.github.com and run `gh auth login`")
    repo = gh_json(f"repos/{slug}")
    views = gh_json(f"repos/{slug}/traffic/views")
    clones = gh_json(f"repos/{slug}/traffic/clones")
    referrers = gh_json(f"repos/{slug}/traffic/popular/referrers")
    paths = gh_json(f"repos/{slug}/traffic/popular/paths")
    stars = []
    if repo.get("stargazers_count", 0) <= max_pages * 100:
        stars = gh_json(f"repos/{slug}/stargazers?per_page=100", accept="application/vnd.github.star+json", paginate=True) or []
    return {"repo": slug, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stars_total": repo.get("stargazers_count"), "views": views, "clones": clones,
            "referrers": referrers, "paths": paths, "stargazers": [{"starred_at": s.get("starred_at")} for s in stars],
            "star_history_complete": bool(stars) or repo.get("stargazers_count", 0) == 0}


# ---------------------------------------------------------------- snapshot + history

def day(ts: str) -> str:
    return ts[:10]


def to_snapshot(raw: dict) -> dict:
    star_days = defaultdict(int)
    for s in raw.get("stargazers") or []:
        if s.get("starred_at"):
            star_days[day(s["starred_at"])] += 1
    return {
        "fetched_at": raw.get("fetched_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": raw.get("repo"),
        "stars_total": raw.get("stars_total", sum(star_days.values())),
        "views_daily": {day(v["timestamp"]): {"count": v["count"], "uniques": v["uniques"]} for v in (raw.get("views") or {}).get("views", [])},
        "clones_daily": {day(v["timestamp"]): {"count": v["count"], "uniques": v["uniques"]} for v in (raw.get("clones") or {}).get("clones", [])},
        "referrers": [{"referrer": r["referrer"], "count": r["count"], "uniques": r["uniques"]} for r in raw.get("referrers") or []],
        "paths": [{"path": p["path"], "count": p["count"], "uniques": p["uniques"]} for p in (raw.get("paths") or [])][:10],
        "stars_daily": dict(sorted(star_days.items())),
        "star_history_complete": raw.get("star_history_complete", True),
    }


def merged_series(history: list[dict]) -> tuple[dict, dict, dict]:
    views, clones, stars = {}, {}, {}
    for snap in sorted(history, key=lambda s: s["fetched_at"]):
        views.update(snap.get("views_daily", {}))
        clones.update(snap.get("clones_daily", {}))
        if snap.get("stars_daily"):
            stars = dict(snap["stars_daily"])  # latest full star history wins
    return views, clones, stars


# ---------------------------------------------------------------- analysis

def period_stats(views: dict, stars: dict, start: date, end: date) -> dict:
    days = [(start + timedelta(d)).isoformat() for d in range((end - start).days + 1)]
    u = sum(views.get(d, {}).get("uniques", 0) for d in days)
    v = sum(views.get(d, {}).get("count", 0) for d in days)
    s = sum(stars.get(d, 0) for d in days)
    return {"from": days[0], "to": days[-1], "days": len(days), "views": v, "uniques": u, "stars": s,
            "conversion": round(s / u, 4) if u else None}


def referrer_conversion(history: list[dict], stars: dict) -> tuple[list[dict], str]:
    snaps = sorted(history, key=lambda s: s["fetched_at"])
    latest = snaps[-1]
    if len(snaps) < 2:
        window_end = date.fromisoformat(latest["fetched_at"][:10])
        window = period_stats({}, stars, window_end - timedelta(13), window_end)["stars"]
        total_u = sum(r["uniques"] for r in latest["referrers"]) or 1
        rows = [{**r, "est_stars": round(window * r["uniques"] / total_u, 1), "est_conversion": None} for r in latest["referrers"]]
        return rows, ("single snapshot: stars cannot be attributed to referrers yet (GitHub does not link them). "
                      "Showing traffic share only; run diagnose again in a few days to get per-referrer estimates.")
    attributed = defaultdict(float)
    visitors = defaultdict(float)
    for prev, cur in zip(snaps, snaps[1:]):
        p = {r["referrer"]: r["uniques"] for r in prev["referrers"]}
        deltas = {r["referrer"]: max(0, r["uniques"] - p.get(r["referrer"], 0)) for r in cur["referrers"]}
        a, b = date.fromisoformat(prev["fetched_at"][:10]), date.fromisoformat(cur["fetched_at"][:10])
        s = sum(stars.get((a + timedelta(d + 1)).isoformat(), 0) for d in range((b - a).days))
        tot = sum(deltas.values())
        for ref, dlt in deltas.items():
            visitors[ref] += dlt
            if tot:
                attributed[ref] += s * dlt / tot
    rows = []
    for r in latest["referrers"]:
        ref = r["referrer"]
        rows.append({**r, "new_visitors_tracked": visitors[ref], "est_stars": round(attributed[ref], 1),
                     "est_conversion": round(attributed[ref] / visitors[ref], 4) if visitors[ref] and len(snaps) >= 3 else None})
    if len(snaps) < 3:
        # One interval splits stars in proportion to visitors, so every referrer would get the same rate.
        return rows, ("2 snapshots: stars are split across referrers by their new visitors, but per-referrer conversion "
                      "needs at least 3 snapshots (one interval gives every referrer the same rate). Run diagnose again later.")
    return rows, (f"estimated from {len(snaps)} snapshots: stars gained between snapshots are split across referrers in "
                  "proportion to each referrer's new unique visitors. Referrers that dominate different intervals separate "
                  "over time. Treat as directional, not exact.")


def diagnose(views: dict, stars: dict, today: date, th: dict) -> dict:
    days = sorted(views)
    uniq = [views[d]["uniques"] for d in days]
    total_u = sum(uniq)
    if not days or total_u == 0:
        return {"primary": "insufficient-data" if not days else "distribution", "signals": ["no visitor traffic recorded"],
                "confidence": "low" if not days else "high"}
    window_stars = sum(stars.get(d, 0) for d in days)
    conv = window_stars / total_u if total_u else 0
    per_day = total_u / len(days)
    sig, found = [], []
    peak_i = max(range(len(uniq)), key=lambda i: uniq[i])
    med = statistics.median(uniq) or 1
    last7 = uniq[-7:]
    spike = uniq[peak_i] >= th["spike_factor"] * med and uniq[peak_i] >= 20
    if spike and peak_i < len(uniq) - 2:
        post = uniq[peak_i + 1:]
        post_stars = sum(stars.get(d, 0) for d in days[peak_i + 2:])
        if statistics.mean(last7) <= th["flat_ratio"] * uniq[peak_i]:
            found.append("retention")
            sig.append(f"spike of {uniq[peak_i]} uniques on {days[peak_i]} ({uniq[peak_i] / med:.0f}x median), then "
                       f"{statistics.mean(post):.0f}/day; {post_stars} stars after the spike")
    high_traffic = per_day >= th["high_traffic_per_day"]
    if high_traffic and conv < th["low_conversion"]:
        found.insert(0, "readme")
        sig.append(f"{per_day:.0f} uniques/day but only {conv:.1%} convert to stars (< {th['low_conversion']:.0%})")
    elif not high_traffic and conv >= th["high_conversion"]:
        found.insert(0, "distribution")
        sig.append(f"{conv:.1%} of visitors star it (strong) but only {per_day:.0f} uniques/day")
    elif not high_traffic and conv < th["low_conversion"]:
        found += ["readme", "distribution"]
        sig.append(f"low traffic ({per_day:.0f}/day) and low conversion ({conv:.1%}); fix the README before buying more traffic")
    elif high_traffic:
        sig.append(f"{per_day:.0f} uniques/day converting at {conv:.1%}")
    else:
        found.append("distribution")
        sig.append(f"{per_day:.0f} uniques/day at {conv:.1%}: conversion is fine, reach is the bottleneck")
    primary = found[0] if found else "healthy"
    conf = "low" if total_u < th["min_uniques"] or len(days) < 5 else "medium" if total_u < 200 else "high"
    return {"primary": primary, "secondary": [f for f in found[1:] if f != primary], "signals": sig, "confidence": conf,
            "uniques": total_u, "stars": window_stars, "conversion": round(conv, 4), "uniques_per_day": round(per_day, 1)}


ACTIONS = {
    "readme": [
        "Run `/launch-lab panel`: visitors arrive but do not star, so the first screen is not convincing them.",
        "Put a demo GIF and a one-sentence 'what + for whom' directly under the title.",
        "Match the first line to your top referrer's audience (e.g. HN readers want specifics and a 'why not X' answer).",
        "Add a one-command quickstart and an honest comparison table; check the top-fixes list in launch/report.md.",
    ],
    "distribution": [
        "Your README converts; you need more of the right visitors. Post the next unused channel from launch/calendar.md.",
        "Answer existing questions (Stack Overflow, GitHub issues/discussions of adjacent tools) where the project is a genuine fit.",
        "Ask to be listed in 1-2 relevant awesome-lists (one PR each, following their rules).",
        "Write one technical post about a hard problem the project solved and link the repo at the end.",
    ],
    "retention": [
        "The spike faded with nothing to come back to. Ship a visible follow-up: a release with notes, a 'v0.2: what changed' post.",
        "Turn launch-day questions into a FAQ and docs pages; reply to every issue opened during the spike.",
        "Add 3-5 'good first issue' tickets so spike visitors can become contributors.",
        "Schedule a second, different-angle post 2-3 weeks out (tutorial, benchmark with method, case study) rather than a repost.",
    ],
    "healthy": ["Traffic and conversion both look good. Keep the cadence: regular releases, changelog posts, and reply to issues fast."],
    "insufficient-data": ["No traffic data yet. Check `gh auth status` has push access, then snapshot daily for a week."],
}


def render(res: dict) -> str:
    d = res["diagnosis"]
    L = [f"# Star conversion diagnosis: {res['repo']}", "", f"_Snapshot {res['fetched_at']}; {res['snapshots']} snapshot(s) in history._", "",
         f"## Diagnosis: **{d['primary']}** (confidence: {d['confidence']})", ""]
    for s in d["signals"]:
        L.append(f"- {s}")
    if d.get("secondary"):
        L.append(f"- also: {', '.join(d['secondary'])}")
    L += ["", "## Next actions", ""]
    for kind in [d["primary"]] + d.get("secondary", []):
        for a in ACTIONS.get(kind, []):
            L.append(f"- {a}")
    L += ["", "## Conversion by period", "", "| Period | Views | Unique visitors | New stars | Conversion |", "|---|---:|---:|---:|---:|"]
    for name, p in res["periods"].items():
        c = f"{p['conversion']:.1%}" if p["conversion"] is not None else "n/a"
        L.append(f"| {name} ({p['from']} to {p['to']}) | {p['views']} | {p['uniques']} | {p['stars']} | {c} |")
    L += ["", "_Unique visitors are summed per day, so one person visiting on two days counts twice; conversion is a lower bound._", "",
          "## Referrers (last 14 days)", "", res["referrer_method"], "", "| Referrer | Views | Uniques | Est. stars | Est. conversion |", "|---|---:|---:|---:|---:|"]
    for r in res["referrers"]:
        c = f"{r['est_conversion']:.1%}" if r.get("est_conversion") is not None else "n/a"
        L.append(f"| {r['referrer']} | {r['count']} | {r['uniques']} | {r['est_stars']} | {c} |")
    if res.get("paths"):
        L += ["", "## Popular pages", "", "| Path | Views | Uniques |", "|---|---:|---:|"]
        for p in res["paths"]:
            L.append(f"| {p['path']} | {p['count']} | {p['uniques']} |")
    L += ["", "## Daily", "", "| Date | Views | Uniques | Clones | Stars |", "|---|---:|---:|---:|---:|"]
    for row in res["daily"][-21:]:
        L.append(f"| {row['date']} | {row['views']} | {row['uniques']} | {row['clones']} | {row['stars']} |")
    L += ["", "_GitHub keeps traffic for 14 days only. Run `/launch-lab diagnose` every few days to build a longer trend._", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="OWNER/NAME (default: from .launch-lab/scan.json or git remote)")
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--from-file", help="raw metrics JSON (same shape this script fetches)")
    ap.add_argument("--no-save", action="store_true", help="do not append to history.json")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for evals")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = C.repo_root(a.repo_dir)
    cfg = C.load_config(root)
    th = {**DEFAULTS, **(cfg.get("diagnosis") or {})}

    if a.from_file:
        raw = C.read_json(Path(a.from_file))
        if raw is None:
            print(f"cannot read {a.from_file}", file=sys.stderr)
            return 2
    else:
        slug = a.repo or (C.read_json(root / C.STATE_DIR / "scan.json", {}) or {}).get("github", {}).get("slug") or cfg.get("github_repo")
        if not slug:
            print("no repo slug: pass --repo OWNER/NAME", file=sys.stderr)
            return 2
        try:
            raw = fetch(slug, th["max_star_pages"])
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as e:
            print(f"fetch failed: {e}", file=sys.stderr)
            return 2

    raws = raw if isinstance(raw, list) else [raw]  # a fixture may hold several snapshots
    hist_p = root / C.STATE_DIR / "history.json"
    # Offline runs with --no-save analyse the file alone; everything else builds on the stored trend.
    history = [] if (a.from_file and a.no_save) else (C.read_json(hist_p, {}) or {}).get("snapshots", [])
    for r in raws:
        history.append(to_snapshot(r))
    views, clones, stars = merged_series(history)
    latest = history[-1]
    today = date.fromisoformat(a.today) if a.today else date.fromisoformat(latest["fetched_at"][:10])
    periods = {
        "Last 7 days": period_stats(views, stars, today - timedelta(6), today),
        "Previous 7 days": period_stats(views, stars, today - timedelta(13), today - timedelta(7)),
    }
    if views:
        first = date.fromisoformat(min(views))
        periods["All tracked"] = period_stats(views, stars, first, today)
    refs, method = referrer_conversion(history, stars)
    all_days = sorted(set(views) | set(clones) | {d for d in stars if d >= (min(views) if views else d)})
    daily = [{"date": d, "views": views.get(d, {}).get("count", 0), "uniques": views.get(d, {}).get("uniques", 0),
              "clones": clones.get(d, {}).get("count", 0), "stars": stars.get(d, 0)} for d in all_days]
    res = {"repo": latest.get("repo") or root.name, "fetched_at": latest["fetched_at"], "snapshots": len(history),
           "stars_total": latest.get("stars_total"), "periods": periods, "referrers": refs, "referrer_method": method,
           "paths": latest.get("paths", []), "daily": daily, "diagnosis": diagnose(views, stars, today, th), "thresholds": th}
    clone_u, star_n = sum(c.get("uniques", 0) for c in clones.values()), sum(stars.get(d, 0) for d in clones)
    if clone_u > 2 * max(star_n, 1) and clone_u >= 10:
        res["diagnosis"]["signals"].append(f"{clone_u} unique cloners vs {star_n} stars on the same days: people try it "
                                           "but do not come back to star (a closing 'if this helped' line can help)")
    if not a.no_save:
        C.write_json(hist_p, {"snapshots": history})
    C.out_path(root, "diagnosis.md").write_text(render(res), encoding="utf-8")
    C.write_json(C.state_path(root, "diagnosis.json"), res)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        d = res["diagnosis"]
        print(f"diagnosis: {d['primary']} ({d['confidence']} confidence) | " + " | ".join(d["signals"]))
        print(f"-> {C.out_path(root, 'diagnosis.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
