"""Shared helpers for Launch Lab scripts. Python 3.9+ stdlib only."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

STATE_DIR = ".launch-lab"
OUT_DIR = "launch"

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build",
    "target", ".next", ".nuxt", ".tox", ".mypy_cache", ".pytest_cache", ".launch-lab",
    "launch", "vendor", ".idea", ".vscode", "coverage", ".cache",
}

SHELL_LANGS = {"", "bash", "sh", "shell", "zsh", "console", "terminal", "shell-session", "shellsession"}

INSTALL_HEADING = re.compile(
    r"(install|installation|quick\s*-?\s*start|getting\s+started|setup|set\s+up|usage|try\s+it|run\s+it)",
    re.I,
)


def repo_root(path: str | None) -> Path:
    return Path(path or ".").resolve()


def state_path(root: Path, name: str) -> Path:
    p = root / STATE_DIR
    p.mkdir(exist_ok=True)
    return p / name


def out_path(root: Path, name: str) -> Path:
    p = root / OUT_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config(root: Path) -> dict:
    return read_json(root / STATE_DIR / "config.json", {}) or {}


def find_readme(root: Path) -> Path | None:
    for name in ("README.md", "readme.md", "Readme.md", "README.markdown", "README.rst", "README.txt", "README"):
        p = root / name
        if p.is_file():
            return p
    for p in root.glob("[Rr][Ee][Aa][Dd][Mm][Ee]*"):
        if p.is_file():
            return p
    return None


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def iter_files(root: Path, max_files: int = 5000):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d in (".github", ".claude-plugin")]
        for f in filenames:
            yield Path(dirpath) / f
            count += 1
            if count >= max_files:
                return


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


# ---------------------------------------------------------------- markdown

FENCE = re.compile(r"^(\s*)(```+|~~~+)\s*([\w+-]*)[^\n]*$")


def code_blocks(text: str) -> list[dict]:
    """Return fenced code blocks with language, body, start line and the heading they sit under."""
    blocks, heading, lines = [], "", text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        h = re.match(r"^(#{1,6})\s+(.*)", line)
        if h:
            heading = h.group(2).strip()
        m = FENCE.match(line)
        if m:
            fence, lang = m.group(2), m.group(3).lower()
            body, j = [], i + 1
            while j < len(lines) and not lines[j].strip().startswith(fence[:3]):
                body.append(lines[j])
                j += 1
            blocks.append({"lang": lang, "body": "\n".join(body), "line": i + 1, "heading": heading})
            i = j + 1
            continue
        i += 1
    return blocks


def sections(text: str) -> list[dict]:
    """Split markdown into heading sections: [{level, title, start, end, body}]."""
    lines = text.splitlines()
    heads, in_fence = [], False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    out = []
    for k, (i, level, title) in enumerate(heads):
        end = len(lines)
        for i2, level2, _ in heads[k + 1:]:
            if level2 <= level:
                end = i2
                break
        out.append({"level": level, "title": title, "start": i + 1, "end": end,
                    "body": "\n".join(lines[i + 1:end])})
    return out


def shell_commands(block_body: str, lang: str) -> list[str]:
    """Extract runnable commands from a shell-ish code block."""
    lines = block_body.splitlines()
    has_prompt = any(re.match(r"^\s*[$%>]\s", l) for l in lines)
    cmds, buf = [], ""
    for raw in lines:
        line = raw.rstrip()
        if has_prompt or lang in ("console", "terminal", "shell-session", "shellsession"):
            m = re.match(r"^\s*[$%>]\s+(.*)", line)
            if not m and not buf:
                continue  # output line
            if m:
                line = m.group(1)
        stripped = line.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if stripped.endswith("\\"):
            buf += stripped[:-1].rstrip() + " "
            continue
        cmds.append((buf + stripped).strip())
        buf = ""
    if buf.strip():
        cmds.append(buf.strip())
    return cmds


IMG_MD = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
IMG_HTML = re.compile(r"<img\b[^>]*>", re.I)
LINK_MD = re.compile(r"(?<!!)\[((?:[^\[\]]|\[[^\]]*\])+)\]\([^)]+\)")
BADGE_HINT = re.compile(r"(shields\.io|badge|badgen\.net|img\.shields|travis-ci|circleci|codecov|github\.com/.+/workflows/|/actions/workflows/)", re.I)


def _html_attr(tag: str, name: str) -> str:
    m = re.search(rf'{name}\s*=\s*"([^"]*)"', tag, re.I) or re.search(rf"{name}\s*=\s*'([^']*)'", tag, re.I)
    return m.group(1) if m else ""


def images(text: str) -> list[dict]:
    found = []
    for m in IMG_MD.finditer(text):
        found.append({"pos": m.start(), "alt": m.group(1), "src": m.group(2)})
    for m in IMG_HTML.finditer(text):
        found.append({"pos": m.start(), "alt": _html_attr(m.group(0), "alt"), "src": _html_attr(m.group(0), "src")})
    for m in re.finditer(r"<video\b[^>]*>", text, re.I):
        found.append({"pos": m.start(), "alt": "video", "src": _html_attr(m.group(0), "src") or "video"})
    found.sort(key=lambda d: d["pos"])
    for f in found:
        f["badge"] = bool(BADGE_HINT.search(f["src"]))
        f["animated"] = bool(re.search(r"\.(gif|mp4|webm|mov|apng)(\?|$)|asciinema|video", f["src"], re.I))
    return found


def render_for_reader(md: str) -> str:
    """Turn markdown into what a visitor perceives, with images described by alt text."""
    def img_md(m):
        alt, src = m.group(1), m.group(2)
        kind = "badge" if BADGE_HINT.search(src) else ("animated image" if re.search(r"\.(gif|mp4|webm)", src, re.I) else "image")
        return f"[{kind}: {alt or Path(src.split('?')[0]).name}]"

    def img_html(m):
        tag = m.group(0)
        alt, src = _html_attr(tag, "alt"), _html_attr(tag, "src")
        kind = "badge" if BADGE_HINT.search(src) else ("animated image" if re.search(r"\.(gif|mp4|webm)", src, re.I) else "image")
        return f"[{kind}: {alt or Path(src.split('?')[0]).name}]"

    out = IMG_MD.sub(img_md, md)
    out = IMG_HTML.sub(img_html, out)
    out = re.sub(r"<video\b[^>]*>.*?</video>", "[video]", out, flags=re.S | re.I)
    out = LINK_MD.sub(r"\1", out)
    out = re.sub(r"</?(p|div|h\d|a|picture|source|br|span|b|strong|em|i|sub|sup|center)\b[^>]*>", "", out, flags=re.I)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
