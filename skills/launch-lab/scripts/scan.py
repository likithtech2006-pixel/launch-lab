#!/usr/bin/env python3
"""Scan a repo: above-the-fold README, repo type, install blocks and launch signals.

Usage: scan.py [REPO] [--fold-lines 25] [--offline] [--out PATH] [--print]
Writes REPO/.launch-lab/scan.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launchlab_common as C  # noqa: E402

SOURCE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".java", ".kt", ".sh", ".php", ".cs", ".swift"}
ENV_PATTERNS = [
    r"os\.environ\[\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]",
    r"os\.environ\.get\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]",
    r"os\.getenv\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]",
    r"process\.env\.([A-Z][A-Z0-9_]{2,})",
    r"process\.env\[\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]",
    r"env::var\(\s*\"([A-Z][A-Z0-9_]{2,})\"",
    r"os\.Getenv\(\s*\"([A-Z][A-Z0-9_]{2,})\"",
    r"ENV\[\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]",
]
# Env vars that are normal to read and never need documenting.
COMMON_ENV = {"HOME", "PATH", "USER", "SHELL", "TERM", "PWD", "TMPDIR", "NODE_ENV", "DEBUG", "CI", "LANG",
              "PORT", "HOST", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "APPDATA", "LOCALAPPDATA",
              "USERPROFILE", "NO_COLOR", "FORCE_COLOR", "COLUMNS", "LINES", "EDITOR", "VIRTUAL_ENV", "GITHUB_ACTIONS"}

# Code here is not what a user of the project runs, so its env vars need no README entry.
NON_PRODUCT_DIRS = {"test", "tests", "__tests__", "spec", "fixtures", "examples", "example", "evals", "e2e", "docs", "benchmarks"}

WEB_DEPS = {"next", "react-dom", "vue", "nuxt", "svelte", "@sveltejs/kit", "vite", "express", "fastify", "koa",
            "astro", "remix", "@remix-run/react", "angular", "@angular/core", "gatsby", "solid-js", "hono"}
TUI_DEPS_JS = {"ink", "blessed", "neo-blessed", "terminal-kit"}
WEB_PY = {"flask", "django", "fastapi", "streamlit", "gradio", "starlette", "dash", "sanic", "aiohttp", "nicegui"}
TUI_PY = {"textual", "urwid", "npyscreen", "prompt_toolkit", "prompt-toolkit", "curses", "asciimatics", "pytermgui"}
TUI_RS = {"ratatui", "tui", "cursive"}
TUI_GO = {"github.com/charmbracelet/bubbletea", "github.com/rivo/tview", "github.com/gdamore/tcell"}
WEB_GO = {"github.com/gin-gonic/gin", "github.com/labstack/echo", "github.com/gofiber/fiber"}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- fold

def extract_fold(readme_text: str, n_lines: int) -> dict:
    text = C.strip_html_comments(readme_text)
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    fold_lines = lines[:n_lines]
    fold_md = "\n".join(fold_lines)
    imgs = C.images(fold_md)
    title = ""
    for l in fold_lines:
        m = re.match(r"^#\s+(.*)", l) or re.match(r"^\s*<h1[^>]*>(.*?)</h1>", l, re.I)
        if m:
            title = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)", "", m.group(1)).strip()
            break
    tagline = ""
    for l in fold_lines:
        s = l.strip()
        if not s or s.startswith("#") or s.startswith("<") or s.startswith("[!") or s.startswith("!") or s.startswith("|") or s.startswith("```"):
            continue
        tagline = C.render_for_reader(s).strip("> *_")
        if len(tagline) > 8:
            break
    first_image = next((i for i in imgs if not i["badge"]), None)
    return {
        "lines": len(fold_lines),
        "markdown": fold_md,
        "rendered": C.render_for_reader(fold_md),
        "title": title,
        "tagline": tagline,
        "badges": [i["alt"] or Path(i["src"].split("?")[0]).name for i in imgs if i["badge"]],
        "first_image": first_image and {"alt": first_image["alt"], "src": first_image["src"], "animated": first_image["animated"]},
        "sha": sha(fold_md),
    }


# ---------------------------------------------------------------- manifests

def load_toml_light(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def manifests(root: Path) -> dict:
    info: dict = {"languages": [], "name": None, "description": None, "keywords": [], "versions": {},
                  "deps": set(), "bins": [], "scripts": {}, "lib": False}
    pj = C.read_json(root / "package.json")
    if isinstance(pj, dict):
        info["languages"].append("javascript")
        info["name"] = info["name"] or pj.get("name")
        info["description"] = info["description"] or pj.get("description")
        info["keywords"] += pj.get("keywords") or []
        for k in ("dependencies", "devDependencies", "peerDependencies"):
            info["deps"].update((pj.get(k) or {}).keys())
        b = pj.get("bin")
        if b:
            info["bins"] += [b] if isinstance(b, str) else list(b.keys())
        info["scripts"] = pj.get("scripts") or {}
        if pj.get("main") or pj.get("exports") or pj.get("module") or pj.get("types"):
            info["lib"] = True
        if (pj.get("engines") or {}).get("node"):
            info["versions"]["node"] = pj["engines"]["node"]
    py = root / "pyproject.toml"
    if py.is_file():
        t = load_toml_light(py)
        info["languages"].append("python")
        m = re.search(r'^name\s*=\s*"([^"]+)"', t, re.M)
        info["name"] = info["name"] or (m and m.group(1))
        m = re.search(r'^description\s*=\s*"([^"]+)"', t, re.M)
        info["description"] = info["description"] or (m and m.group(1))
        m = re.search(r'^requires-python\s*=\s*"([^"]+)"', t, re.M)
        if m:
            info["versions"]["python"] = m.group(1)
        if re.search(r"^\[project\.scripts\]|^\[tool\.poetry\.scripts\]|console_scripts", t, re.M):
            info["bins"].append("(python console script)")
        deps = re.findall(r'["\']([A-Za-z0-9_.\-]+)\s*(?:[<>=!~\[;].*?)?["\']', t)
        info["deps"].update(d.lower() for d in deps)
        info["lib"] = True
    for f in ("setup.py", "setup.cfg"):
        p = root / f
        if p.is_file():
            t = load_toml_light(p)
            if "python" not in info["languages"]:
                info["languages"].append("python")
            if "console_scripts" in t or "entry_points" in t:
                info["bins"].append("(python console script)")
            m = re.search(r"python_requires\s*=\s*['\"]?([^'\"\n,]+)", t)
            if m:
                info["versions"]["python"] = m.group(1).strip()
            info["deps"].update(d.lower() for d in re.findall(r"['\"]([A-Za-z0-9_.\-]+)[<>=~!]", t))
            info["lib"] = True
    req = root / "requirements.txt"
    if req.is_file():
        if "python" not in info["languages"]:
            info["languages"].append("python")
        for line in load_toml_light(req).splitlines():
            m = re.match(r"^\s*([A-Za-z0-9_.\-]+)", line)
            if m:
                info["deps"].add(m.group(1).lower())
    cargo = root / "Cargo.toml"
    if cargo.is_file():
        t = load_toml_light(cargo)
        info["languages"].append("rust")
        m = re.search(r'^name\s*=\s*"([^"]+)"', t, re.M)
        info["name"] = info["name"] or (m and m.group(1))
        m = re.search(r'^description\s*=\s*"([^"]+)"', t, re.M)
        info["description"] = info["description"] or (m and m.group(1))
        m = re.search(r'^rust-version\s*=\s*"([^"]+)"', t, re.M)
        if m:
            info["versions"]["rust"] = m.group(1)
        info["deps"].update(re.findall(r"^([a-z0-9_\-]+)\s*=", t.split("[dependencies]")[-1], re.M))
        if (root / "src/main.rs").is_file() or "[[bin]]" in t:
            info["bins"].append("(cargo bin)")
        if (root / "src/lib.rs").is_file():
            info["lib"] = True
    gomod = root / "go.mod"
    if gomod.is_file():
        t = load_toml_light(gomod)
        info["languages"].append("go")
        m = re.search(r"^module\s+(\S+)", t, re.M)
        info["name"] = info["name"] or (m and m.group(1).split("/")[-1])
        m = re.search(r"^go\s+(\S+)", t, re.M)
        if m:
            info["versions"]["go"] = m.group(1)
        info["deps"].update(re.findall(r"^\s*(\S+)\s+v\d", t, re.M))
        main_files = list(root.glob("main.go")) + list(root.glob("cmd/*/main.go"))
        if main_files:
            info["bins"].append("(go main)")
        else:
            info["lib"] = True
    for f, lang in ((".nvmrc", "node"), (".node-version", "node"), (".python-version", "python"), ("rust-toolchain", "rust")):
        p = root / f
        if p.is_file() and lang not in info["versions"]:
            info["versions"][lang] = load_toml_light(p).strip().splitlines()[0] if load_toml_light(p).strip() else ""
    plugin = C.read_json(root / ".claude-plugin" / "plugin.json")
    if isinstance(plugin, dict):
        info["name"] = info["name"] or plugin.get("name")
        info["description"] = info["description"] or plugin.get("description")
        info["keywords"] += plugin.get("keywords") or []
    info["deps"] = sorted(info["deps"])
    return info


def detect_type(root: Path, man: dict, readme: str) -> dict:
    score = {"cli": 0.0, "tui": 0.0, "web": 0.0, "library": 0.0, "skill": 0.0}
    ev: list[str] = []
    deps = set(man["deps"])

    def add(kind, pts, why):
        score[kind] += pts
        ev.append(f"{kind} +{pts}: {why}")

    if list(root.glob("skills/*/SKILL.md")) or (root / "SKILL.md").is_file():
        add("skill", 5, "SKILL.md present (Claude agent skill)")
    if (root / ".claude-plugin" / "plugin.json").is_file():
        add("skill", 2, ".claude-plugin/plugin.json present")
    if man["bins"]:
        add("cli", 4, f"executable entry points: {', '.join(map(str, man['bins']))[:80]}")
    if deps & TUI_DEPS_JS or deps & TUI_PY or deps & TUI_RS or deps & TUI_GO:
        add("tui", 5, f"TUI dependency: {', '.join(sorted(deps & (TUI_DEPS_JS | TUI_PY | TUI_RS | TUI_GO)))}")
    web_hits = deps & (WEB_DEPS | WEB_PY | WEB_GO)
    if web_hits:
        add("web", 4, f"web framework dependency: {', '.join(sorted(web_hits))}")
    if any(k in man["scripts"] for k in ("dev", "start", "serve", "preview")) and web_hits:
        add("web", 1, "dev/start script")
    if (root / "index.html").is_file() or (root / "public" / "index.html").is_file():
        add("web", 2, "index.html")
    if man["lib"] and not man["bins"]:
        add("library", 3, "package exports a library and no executables")
    elif man["lib"]:
        add("library", 1, "package also exports a library")
    if re.search(r"localhost:\d{2,5}|open .*in your browser|https?://[\w.-]+\.(vercel|netlify|pages|fly|onrender|herokuapp)\.", readme, re.I):
        add("web", 2, "README mentions a local or deployed URL")
    if re.search(r"^\s*(\$\s+)?(npx|pipx|brew install|cargo install|go install|uvx)\s", readme, re.M | re.I):
        add("cli", 2, "README installs or runs an executable")
    if re.search(r"^\s*(\$\s+)?(\./[\w.-]+|(ba)?sh\s+[\w./-]+\.sh|python3?\s+[\w./-]+\.py|node\s+[\w./-]+\.m?js)\b", readme, re.M):
        add("cli", 3, "README runs a script or program directly")
    if re.search(r"^\s*(import|from)\s+\w+|require\(['\"]|^\s*use\s+\w+::", readme, re.M):
        add("library", 2, "README shows import/require usage")
    best = max(score, key=score.get)
    total = sum(score.values()) or 1
    kind = best if score[best] > 0 else "unknown"
    demo_pipeline = {"cli": "vhs", "tui": "vhs", "skill": "vhs", "web": "playwright", "library": "snippet", "unknown": "text_gif"}[kind]
    return {"type": kind, "confidence": round(score[best] / total, 2) if score[best] else 0.0,
            "scores": score, "evidence": ev, "demo_pipeline": demo_pipeline}


# ---------------------------------------------------------------- signals

def find_file(root: Path, patterns: list[str]) -> str | None:
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                return str(p.relative_to(root))
    return None


def github_slug(root: Path, cfg: dict) -> str | None:
    if cfg.get("github_repo"):
        return cfg["github_repo"]
    code, out = C.run(["git", "remote", "get-url", "origin"], cwd=root)
    if code == 0:
        m = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?\s*$", out.strip())
        if m:
            return m.group(1)
    return None


def github_meta(slug: str) -> dict | None:
    if not shutil.which("gh"):
        return None
    code, out = C.run(["gh", "repo", "view", slug, "--json",
                       "description,repositoryTopics,homepageUrl,openGraphImageUrl,usesCustomOpenGraphImage,stargazerCount,licenseInfo"],
                      timeout=20)
    if code != 0:
        return None
    try:
        d = json.loads(out)
    except ValueError:
        return None
    topics = [t.get("name") for t in (d.get("repositoryTopics") or []) if isinstance(t, dict)]
    return {"description": d.get("description"), "topics": topics, "homepage": d.get("homepageUrl"),
            "social_preview_custom": d.get("usesCustomOpenGraphImage"), "stars": d.get("stargazerCount"),
            "license": (d.get("licenseInfo") or {}).get("spdxId")}


def quickstart_info(readme: str) -> dict:
    secs = C.sections(readme)
    qs = next((s for s in secs if C.INSTALL_HEADING.search(s["title"])), None)
    blocks = C.code_blocks(readme)
    install_blocks = []
    for b in blocks:
        in_section = any(s["start"] <= b["line"] <= s["end"] and C.INSTALL_HEADING.search(s["title"]) for s in secs)
        if in_section or (not secs and b["lang"] in C.SHELL_LANGS):
            install_blocks.append({**b, "shell": b["lang"] in C.SHELL_LANGS,
                                   "commands": C.shell_commands(b["body"], b["lang"]) if b["lang"] in C.SHELL_LANGS else []})
    commands = [c for b in install_blocks if b["shell"] for c in b["commands"]]
    first_line = qs["start"] if qs else None
    title = qs and qs["title"]
    if not commands:
        # No heading needed: an install command near the top is the best quickstart there is.
        top = [b for b in blocks if b["line"] <= 40 and b["lang"] in C.SHELL_LANGS
               and re.search(r"\b(pip3?|pipx|uv|npm|pnpm|yarn|cargo|go|brew|gem)\s+(install|add)\b|\bnpx\s|\buvx\s|git\s+clone", b["body"])]
        if top:
            install_blocks = [{**b, "shell": True, "commands": C.shell_commands(b["body"], b["lang"])} for b in top]
            commands = [c for b in install_blocks for c in b["commands"]]
            title, first_line = "(top of README, no heading)", top[0]["line"]
    return {
        "section": title,
        "section_line": first_line,
        "section_lines": qs and len([l for l in qs["body"].splitlines() if l.strip()]),
        "blocks": install_blocks,
        "commands": commands,
        "command_count": len(commands),
    }


def has_comparison(readme: str) -> dict:
    for s in C.sections(readme):
        if re.search(r"\b(vs\.?|versus|comparison|compare[ds]?|alternatives?|why not|how (is|does) .* differ\w*|different from|instead of|prior art|related (work|projects))\b", s["title"], re.I):
            has_table = bool(re.search(r"^\s*\|.*\|\s*$", s["body"], re.M))
            return {"present": True, "heading": s["title"], "table": has_table}
    if re.search(r"^\s*\|[^\n]*\b(vs\.?|alternative)\b[^\n]*\|", readme, re.M | re.I):
        return {"present": True, "heading": None, "table": True}
    return {"present": False, "heading": None, "table": False}


def env_vars_in_code(root: Path, readme: str) -> dict:
    found: dict[str, str] = {}
    for p in C.iter_files(root):
        if p.suffix not in SOURCE_EXT or NON_PRODUCT_DIRS & set(p.relative_to(root).parts[:-1]):
            continue
        try:
            if p.stat().st_size > 400_000:
                continue
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in ENV_PATTERNS:
            for m in re.finditer(pat, t):
                name = m.group(1)
                if name not in COMMON_ENV and name not in found:
                    found[name] = str(p.relative_to(root))
    env_example = find_file(root, [".env.example", ".env.sample", "env.example", ".env.template"])
    example_text = (root / env_example).read_text(errors="ignore") if env_example else ""
    undocumented = sorted(n for n in found if n not in readme and n not in example_text)
    return {"found": found, "env_example": env_example, "undocumented": undocumented}


def version_mentions(readme: str) -> dict:
    pats = {
        "python": r"python\s*(version\s*)?(>=|≥|\^|~=)?\s*v?3(\.\d+)?|python\s*3\.\d+",
        "node": r"node(\.js)?\s*(version\s*)?(>=|≥|\^)?\s*v?\d{2}|node\s*\d{2}\+",
        "go": r"\bgo\s*(>=|≥)?\s*1\.\d+",
        "rust": r"rust\s*(>=|≥)?\s*1\.\d+|msrv",
    }
    return {k: bool(re.search(v, readme, re.I)) for k, v in pats.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--fold-lines", type=int, default=None, help="lines counted as above the fold (default 25 or config)")
    ap.add_argument("--offline", action="store_true", help="skip gh calls")
    ap.add_argument("--out", help="output path (default REPO/.launch-lab/scan.json)")
    ap.add_argument("--print", action="store_true", help="also print the JSON")
    a = ap.parse_args()

    root = C.repo_root(a.repo)
    cfg = C.load_config(root)
    readme_p = C.find_readme(root)
    readme = readme_p.read_text(encoding="utf-8", errors="replace") if readme_p else ""
    n = a.fold_lines or int(cfg.get("fold_lines", 25))
    man = manifests(root)
    slug = None if a.offline else github_slug(root, cfg)
    gh = github_meta(slug) if slug else None
    local_gh = cfg.get("github") or {}
    all_imgs = C.images(readme)
    fold = extract_fold(readme, n)
    demo_imgs = [i for i in all_imgs if i["animated"] and not i["badge"]]
    social_file = find_file(root, [".github/social-preview.*", "social-preview.*", "assets/social*", "docs/social*",
                                   ".github/og*", "assets/og*", "**/social-preview.png"])

    scan = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo_root": str(root),
        "name": cfg.get("name") or man["name"] or root.name,
        "readme_path": readme_p and str(readme_p.relative_to(root)),
        "readme_lines": len(readme.splitlines()),
        "readme_sha": sha(readme),
        "fold": fold,
        "repo_type": detect_type(root, man, readme),
        "manifest": {k: v for k, v in man.items() if k != "deps"} | {"dependency_count": len(man["deps"])},
        "quickstart": quickstart_info(readme),
        "signals": {
            "license_file": find_file(root, ["LICENSE*", "LICENCE*", "COPYING*"]),
            "contributing": find_file(root, ["CONTRIBUTING*", ".github/CONTRIBUTING*", "docs/CONTRIBUTING*"]),
            "code_of_conduct": find_file(root, ["CODE_OF_CONDUCT*", ".github/CODE_OF_CONDUCT*"]),
            "changelog": find_file(root, ["CHANGELOG*", "HISTORY*", "CHANGES*"]),
            "badges_in_fold": len(fold["badges"]),
            "demo_media": [i["src"] for i in demo_imgs],
            "demo_in_fold": bool(fold["first_image"] and fold["first_image"]["animated"]),
            "image_in_fold": bool(fold["first_image"]),
            "comparison": has_comparison(readme),
            "contributing_section": bool(re.search(r"^#{1,6}\s*contribut", readme, re.I | re.M)),
            "has_faq": bool(re.search(r"^#{1,6}\s*(faq|frequently asked)", readme, re.I | re.M)),
            "social_preview_file": social_file,
            "env_vars": env_vars_in_code(root, readme),
            "versions_required": man["versions"],
            "versions_stated_in_readme": version_mentions(readme),
        },
        "github": {
            "slug": slug,
            "available": gh is not None,
            "description": (gh or {}).get("description") or local_gh.get("description"),
            "topics": (gh or {}).get("topics") or local_gh.get("topics") or [],
            "homepage": (gh or {}).get("homepage") or local_gh.get("homepage"),
            "social_preview_custom": (gh or {}).get("social_preview_custom", local_gh.get("social_preview_custom")),
            "stars": (gh or {}).get("stars"),
            "source": "gh" if gh else ("config" if local_gh else "none"),
        },
    }
    out = Path(a.out) if a.out else C.state_path(root, "scan.json")
    C.write_json(out, scan)
    if a.print:
        print(json.dumps(scan, indent=2))
    else:
        rt = scan["repo_type"]
        print(f"scan: {scan['name']} | type={rt['type']} ({rt['confidence']:.0%}) | fold={fold['lines']} lines | "
              f"install commands={scan['quickstart']['command_count']} | demo={'yes' if demo_imgs else 'no'} | "
              f"github={scan['github']['source']} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
