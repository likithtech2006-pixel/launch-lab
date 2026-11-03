#!/usr/bin/env python3
"""Clean install test: follow ONLY the README's install/quickstart commands in a fresh environment.

Usage:
  install_test.py [REPO] --dry-run             show the plan (commands, rewrites, refusals); runs nothing
  install_test.py [REPO]                       auto: Docker if available, else refuse and explain
  install_test.py [REPO] --mode docker [--image python:3.12]
  install_test.py [REPO] --mode local --yes    temp dir + isolated HOME/venv/npm prefix ON THE HOST
  install_test.py [REPO] --mode static         lint the instructions without running anything

Options: --timeout 600 (per step), --server-wait 15, --success-cmd "tool --version",
         --allow-pipe-sh (local mode only), --keep (keep sandbox), --out PATH
Writes REPO/.launch-lab/install.json.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launchlab_common as C  # noqa: E402
import scan as S  # noqa: E402

COPY_IGNORE = {"node_modules", ".venv", "venv", "__pycache__", ".launch-lab", "launch", "dist", "build",
               "target", ".next", ".tox", ".mypy_cache", ".pytest_cache", ".DS_Store"}
SERVER_RE = re.compile(
    r"\b(npm|pnpm|yarn|bun)\s+(run\s+)?(dev|start|serve|preview)\b|\b(flask\s+run|uvicorn|gunicorn|streamlit\s+run|gradio)\b"
    r"|manage\.py\s+runserver|\brails\s+s(erver)?\b|docker[- ]compose\s+up(?!.*\s-d\b)|\bnext\s+(dev|start)\b"
    r"|\bvite(\s|$)|http\.server|\bserve\s+-|\bhugo\s+server|\bjekyll\s+serve",
    re.I,
)
PLACEHOLDER_RE = re.compile(r"<[a-z][\w -]*>|\byour[-_ ]?(api[-_ ]?key|token|key|username|name|org)\b|\bYOUR_[A-Z_]+|\bxxx+\b|\.\.\.\s*$", re.I)
PIPE_SH_RE = re.compile(r"(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b")
# Tools a stranger is assumed to have for each image / any dev machine.
BASE_TOOLS = {"cd", "ls", "echo", "export", "cat", "mkdir", "cp", "mv", "rm", "source", ".", "git", "curl", "wget",
              "chmod", "touch", "set", "unset", "env", "which", "sh", "bash", "test", "[", "true", "open", "xdg-open"}
LANG_TOOLS = {
    "python": {"python", "python3", "pip", "pip3"},
    "javascript": {"node", "npm", "npx"},
    "rust": {"cargo", "rustc", "rustup"},
    "go": {"go"},
}
IMAGES = {"python": "python:3.12", "javascript": "node:22", "rust": "rust:1", "go": "golang:1", None: "buildpack-deps:bookworm"}


# ---------------------------------------------------------------- plan

def self_names(root: Path, scan: dict) -> set[str]:
    names = {root.name, root.name.replace(" ", "-"), str(scan.get("name") or ""), scan["fold"].get("title", "").replace(" ", "-")}
    slug = (scan.get("github") or {}).get("slug")
    if slug:
        names.add(slug.split("/")[-1])
    return {n.lower() for n in names if n}


CLONE_RE = re.compile(r"git\s+clone\s+((?:--?[\w-]+(?:[ =]\S+)?\s+)*)(\S+)(?:\s+(?!&&|;|\|)(\S+))?")


def plan_steps(root: Path, scan: dict) -> list[dict]:
    names = self_names(root, scan)
    steps = []
    for block in scan["quickstart"]["blocks"]:
        if not block["shell"]:
            continue
        for cmd in block["commands"]:
            step = {"cmd": cmd, "run": cmd, "line": block["line"], "heading": block["heading"], "action": "run",
                    "notes": [], "server": bool(SERVER_RE.search(cmd))}
            first = cmd.split()[0] if cmd.split() else ""
            if first.startswith("/"):
                step.update(action="manual", notes=["agent/IDE slash command, not a shell command; checked statically only"])
            elif PLACEHOLDER_RE.search(cmd):
                step.update(action="unclear", notes=["contains a placeholder the reader must replace"])
            m = CLONE_RE.search(cmd)
            if m and step["action"] == "run":
                url, target = m.group(2), m.group(3)
                base = re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1]).lower()
                if base in names:
                    dest = target or re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1])
                    step["run"] = cmd[:m.start()] + f'cp -R "$LL_SNAPSHOT" {shlex.quote(dest)}' + cmd[m.end():]
                    step["notes"].append("clone of this repo replaced by a copy of the local working tree")
                    step["clone_self"] = True
            if PIPE_SH_RE.search(cmd):
                step["notes"].append("pipes a downloaded script into a shell")
                step["pipe_sh"] = True
            if re.search(r"(^|[;&|]\s*)sudo\s", cmd):
                step["notes"].append("uses sudo")
                step["sudo"] = True
            steps.append(step)
    return steps


def static_friction(scan: dict, steps: list[dict], readme: str) -> list[dict]:
    fr = []
    sig = scan["signals"]
    if not scan["quickstart"]["section"]:
        fr.append(friction("unclear_step", "major", None, "README has no Install / Quickstart / Getting started section",
                           "Add a '## Quickstart' section with copy-pasteable commands near the top."))
    if not [s for s in steps if s["action"] in ("run", "manual")]:
        fr.append(friction("unclear_step", "blocker", None, "No runnable install commands found in shell code blocks",
                           "Put install commands in ```bash code blocks under the Quickstart heading."))
    for lang, req in (sig.get("versions_required") or {}).items():
        if req and not sig["versions_stated_in_readme"].get(lang, False):
            fr.append(friction("unstated_version", "minor", None, f"Project requires {lang} {req} but the README never says so",
                               f"State the requirement in a Prerequisites line, e.g. '{lang} {req}'."))
    for var in (sig.get("env_vars") or {}).get("undocumented", []):
        src = sig["env_vars"]["found"].get(var)
        fr.append(friction("undocumented_env_var", "major", None, f"{var} is read in {src} but not mentioned in the README or .env example",
                           f"Document {var} (what it is, whether it is required, where to get it)."))
    langs = set(scan["manifest"].get("languages") or [])
    known = set(BASE_TOOLS)
    for l in langs:
        known |= LANG_TOOLS.get(l, set())
    prereq_text = "\n".join(s["body"] for s in C.sections(readme) if re.search(r"prereq|requirement|dependencies|before you", s["title"], re.I))
    for s in steps:
        if s["action"] != "run":
            if s["action"] == "unclear":
                fr.append(friction("unclear_step", "major", s["cmd"], "Command contains a placeholder (" + PLACEHOLDER_RE.search(s["cmd"]).group(0) + ")",
                                   "Say exactly what to substitute and where to get it, or provide a working default."))
            continue
        tool = s["cmd"].split()[0]
        if "=" in tool:  # VAR=value cmd
            parts = [p for p in s["cmd"].split() if "=" not in p]
            tool = parts[0] if parts else tool
        if "/" not in tool and tool not in known and tool.lower() not in readme.lower().split(s["cmd"].lower())[0] and tool not in prereq_text:
            fr.append(friction("missing_prerequisite", "minor", s["cmd"], f"'{tool}' is used without being listed as a prerequisite",
                               f"Add '{tool}' (with a version and install link) to a Prerequisites line."))
        if s.get("pipe_sh"):
            fr.append(friction("unclear_step", "minor", s["cmd"], "Install pipes a remote script into a shell; cautious readers will stop here",
                               "Offer a package-manager alternative or link to the script source."))
    n = scan["quickstart"]["command_count"]
    if n > 6:
        fr.append(friction("unclear_step", "minor", None, f"Quickstart has {n} commands; strangers drop off after ~3",
                           "Collapse to one install command plus one run command; move the rest to docs."))
    return fr


def friction(kind, severity, step, detail, fix, evidence=None):
    return {"type": kind, "severity": severity, "step": step, "detail": detail, "fix_hint": fix, "evidence": evidence}


def classify_failure(step: dict, rc: int, output: str) -> dict:
    tail = "\n".join(output.strip().splitlines()[-12:])
    tool = step["cmd"].split()[0]
    o = output
    checks = [
        (rc == 127 or re.search(r"command not found|not recognized as|No such file or directory.*" + re.escape(tool), o),
         "missing_prerequisite", "blocker", f"'{tool}' is not available in a clean environment",
         f"List '{tool}' as a prerequisite with install instructions, or use a tool the reader already has."),
        (re.search(r"No matching distribution|Could not find a version|E404|404 Not Found|is not in this registry|not found in registry|could not find crate|no matching package", o, re.I),
         "failing_command", "blocker", "Package is not published (or the name in the README is wrong)",
         "Publish the package before launch, or tell readers to install from source."),
        (re.search(r"requires[- ]python|Requires-Python|unsupported engine|engine \"node\" is incompatible|requires (go|rust|node|python) ?[>=v]?\s*\d|minimum supported rust|go: go\.mod requires", o, re.I),
         "unstated_version", "blocker", "Toolchain version too old or wrong",
         "State the minimum version in the README's Prerequisites line."),
        (re.search(r"KeyError: '([A-Z_]{3,})'|environment variable|env var|is not set|missing (api )?key|_API_KEY|_TOKEN", o, re.I),
         "undocumented_env_var", "blocker", "Fails because an environment variable is not set",
         "Document required env vars and provide a .env.example."),
        (re.search(r"ModuleNotFoundError|No module named|Cannot find module|cannot find package|ImportError", o),
         "failing_command", "blocker", "A dependency is missing after following the install steps",
         "Make the install command install all runtime dependencies."),
        (re.search(r"Permission denied|EACCES|operation not permitted", o, re.I),
         "failing_command", "major", "Permission error",
         "Avoid global installs that need elevated permissions; suggest a user-level install."),
    ]
    for cond, kind, sev, detail, fix in checks:
        if cond:
            return friction(kind, sev, step["cmd"], detail, fix, tail)
    if rc == -9 or rc == 124:
        return friction("failing_command", "blocker", step["cmd"], "Command timed out (or waited for input)",
                        "Make the command non-interactive and say how long it takes.", tail)
    return friction("failing_command", "blocker", step["cmd"], f"Command exited with code {rc}",
                    "Re-run the README steps from scratch and fix or document this step.", tail)


# ---------------------------------------------------------------- execution

WRAPPER = """cd "$(cat "$LL_STATE/cwd" 2>/dev/null || echo "$LL_START")" 2>/dev/null || cd "$LL_START"
[ -f "$LL_STATE/env" ] && . "$LL_STATE/env" 2>/dev/null
{cmd}
__ll_rc=$?
pwd > "$LL_STATE/cwd"
export -p | grep -v -E ' (PWD|OLDPWD|SHLVL|_)=' > "$LL_STATE/env"
exit $__ll_rc
"""


def make_snapshot(root: Path, dest: Path) -> None:
    shutil.copytree(root, dest, symlinks=True, ignore=lambda d, names: [n for n in names if n in COPY_IGNORE])


class Local:
    def __init__(self, root: Path, sandbox: Path, scan: dict, langs: set[str]):
        self.sandbox = sandbox
        self.home = sandbox / "home"
        self.work = sandbox / "work"
        self.state = sandbox / "state"
        for p in (self.home, self.work, self.state):
            p.mkdir(parents=True)
        self.snapshot = sandbox / "snapshot"
        self.repo_name = root.name.replace(" ", "-")
        make_snapshot(root, self.snapshot)
        path = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
        self.env = {"HOME": str(self.home), "LANG": "en_US.UTF-8", "TERM": "xterm-256color", "TMPDIR": str(sandbox / "tmp"),
                    "LL_STATE": str(self.state), "LL_SNAPSHOT": str(self.snapshot), "CI": "1",
                    "npm_config_prefix": str(sandbox / "npm-global"), "npm_config_cache": str(sandbox / "npm-cache"),
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1", "CARGO_HOME": str(sandbox / "cargo"), "GOPATH": str(sandbox / "go")}
        (sandbox / "tmp").mkdir()
        path.insert(0, str(sandbox / "npm-global" / "bin"))
        if "python" in langs:
            subprocess.run([sys.executable, "-m", "venv", str(sandbox / "venv")], check=True, capture_output=True)
            path.insert(0, str(sandbox / "venv" / "bin"))
            self.env["VIRTUAL_ENV"] = str(sandbox / "venv")
        self.env["PATH"] = ":".join(path)

    def start_dir(self, has_clone: bool) -> str:
        if has_clone:
            return str(self.work)
        dest = self.work / self.repo_name
        shutil.copytree(self.snapshot, dest, symlinks=True)
        return str(dest)

    def exec(self, script: str, timeout: int, server: bool) -> tuple[int, str, bool]:
        f = self.state / f"step-{uuid.uuid4().hex[:6]}.sh"
        f.write_text(script)
        p = subprocess.Popen(["bash", str(f)], env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            out, _ = p.communicate(timeout=timeout)
            return p.returncode, out, False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            out, _ = p.communicate()
            return -9, out or "", True

    def close(self, keep: bool):
        if not keep:
            shutil.rmtree(self.sandbox, ignore_errors=True)


class Docker:
    def __init__(self, root: Path, sandbox: Path, image: str):
        self.sandbox = sandbox
        self.state = sandbox / "state"
        self.state.mkdir(parents=True)
        make_snapshot(root, sandbox / "snapshot")
        self.name = f"launch-lab-{uuid.uuid4().hex[:8]}"
        self.image = image
        r = subprocess.run(["docker", "run", "-d", "--name", self.name, "-v", f"{sandbox / 'snapshot'}:/ll/snapshot:ro",
                            "-v", f"{self.state}:/ll/state", "-e", "LL_STATE=/ll/state", "-e", "CI=1",
                            "-e", f"LL_SNAPSHOT=/ll/snapshot", "-w", "/root", image, "sleep", "infinity"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"docker run failed: {r.stderr.strip()}")

    def start_dir(self, has_clone: bool) -> str:
        if has_clone:
            subprocess.run(["docker", "exec", self.name, "mkdir", "-p", "/root/work"], capture_output=True)
            return "/root/work"
        subprocess.run(["docker", "exec", self.name, "bash", "-c", "mkdir -p /root/work && cp -R /ll/snapshot /root/work/repo"],
                       capture_output=True)
        return "/root/work/repo"

    def exec(self, script: str, timeout: int, server: bool) -> tuple[int, str, bool]:
        fname = f"step-{uuid.uuid4().hex[:6]}.sh"
        (self.state / fname).write_text(script)
        cmd = ["docker", "exec", self.name, "bash", f"/ll/state/{fname}"]
        if server:
            cmd = ["docker", "exec", self.name, "timeout", str(timeout), "bash", f"/ll/state/{fname}"]
        try:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout + 30)
            timed_out = server and r.returncode == 124
            return r.returncode, (r.stdout or "") + (r.stderr or ""), timed_out
        except subprocess.TimeoutExpired as e:
            return -9, (e.stdout or "") if isinstance(e.stdout, str) else "", True

    def close(self, keep: bool):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        if not keep:
            shutil.rmtree(self.sandbox, ignore_errors=True)


def docker_ok() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def primary_lang(scan: dict) -> str | None:
    langs = scan["manifest"].get("languages") or []
    return langs[0] if langs else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--mode", choices=["auto", "docker", "local", "static"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="required for --mode local: the user approved running the commands")
    ap.add_argument("--image")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--server-wait", type=int, default=15)
    ap.add_argument("--success-cmd", help="extra command that must succeed after the README steps")
    ap.add_argument("--allow-pipe-sh", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    root = C.repo_root(a.repo)
    scan_p = root / C.STATE_DIR / "scan.json"
    if not scan_p.is_file():
        subprocess.run([sys.executable, str(Path(__file__).with_name("scan.py")), str(root), "--offline"], check=True)
    scan = C.read_json(scan_p)
    readme_p = C.find_readme(root)
    readme = readme_p.read_text(encoding="utf-8", errors="replace") if readme_p else ""
    steps = plan_steps(root, scan)
    cfg = C.load_config(root)
    success_cmd = a.success_cmd or (cfg.get("install") or {}).get("success_cmd")
    if success_cmd:
        steps.append({"cmd": success_cmd, "run": success_cmd, "line": None, "heading": "(success check)", "action": "run",
                      "notes": ["success check from --success-cmd / config"], "server": False})

    mode = a.mode
    if mode == "auto":
        mode = "docker" if docker_ok() else "needs-approval"
    lang = primary_lang(scan)
    image = a.image or (cfg.get("install") or {}).get("image") or IMAGES.get(lang, IMAGES[None])

    if mode == "local":
        for s in steps:
            if s["action"] == "run" and s.get("sudo"):
                s.update(action="refused", notes=s["notes"] + ["sudo is never run on the host"])
            elif s["action"] == "run" and s.get("pipe_sh") and not a.allow_pipe_sh:
                s.update(action="refused", notes=s["notes"] + ["pipe-to-shell refused on the host (use --allow-pipe-sh after review)"])
    elif mode == "docker":
        for s in steps:
            if s.get("sudo"):
                s["run"] = re.sub(r"(^|[;&|]\s*)sudo\s+", r"\1", s["run"])
                s["notes"].append("sudo stripped (container runs as root)")

    if a.dry_run or mode == "needs-approval":
        print(f"Install test plan for {scan['name']}  (mode: {mode if mode != 'needs-approval' else 'Docker unavailable'})")
        if mode in ("docker", "needs-approval"):
            print(f"  image: {image}")
        for i, s in enumerate(steps, 1):
            print(f"  {i:>2}. [{s['action']:<7}] {s['cmd']}" + (f"   <- runs: {s['run']}" if s["run"] != s["cmd"] else ""))
            for n in s["notes"]:
                print(f"        note: {n}")
        if not steps:
            print("  (no shell commands found in the README's install/quickstart sections)")
        if mode == "needs-approval":
            print("\nDocker is not available. These commands would run on the HOST in a temp directory with an isolated")
            print("HOME, venv and npm prefix (not a security sandbox). Ask the user, then re-run with --mode local --yes,")
            print("or use --mode static to lint the instructions without running them.")
            return 3 if not a.dry_run else 0
        return 0

    if mode == "local" and not a.yes:
        print("--mode local runs README commands on the host; re-run with --yes after the user approves the --dry-run plan.",
              file=sys.stderr)
        return 3

    started = time.time()
    result = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mode": mode,
              "image": image if mode == "docker" else None, "readme_sha": scan["readme_sha"], "steps": [],
              "friction": static_friction(scan, steps, readme), "success": None, "time_to_first_success_s": None,
              "total_s": None, "measured": mode != "static", "notes": []}
    if mode == "local":
        result["notes"].append("local mode: host toolchains are visible, so missing-prerequisite detection is weaker than Docker")

    if mode != "static":
        sandbox = Path(tempfile.mkdtemp(prefix="launch-lab-install-"))
        langs = set(scan["manifest"].get("languages") or [])
        if any(re.match(r"(pip3?|python3?)\b", s["cmd"]) for s in steps):
            langs.add("python")
        try:
            env = Docker(root, sandbox, image) if mode == "docker" else Local(root, sandbox, scan, langs)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
            print(f"could not create the {mode} environment: {e}", file=sys.stderr)
            return 2
        try:
            start = env.start_dir(any(s.get("clone_self") for s in steps))
            (env.state / "cwd").write_text(start)
            ok, t0 = True, time.time()
            for i, s in enumerate(steps, 1):
                rec = {"n": i, "cmd": s["cmd"], "ran": s["run"], "action": s["action"], "notes": s["notes"]}
                if s["action"] != "run":
                    result["steps"].append(rec)
                    continue
                if not ok:
                    rec["action"] = "not-reached"
                    result["steps"].append(rec)
                    continue
                script = WRAPPER.replace("$LL_START", start).format(cmd=s["run"])
                ts = time.time()
                wait = a.server_wait if s["server"] else a.timeout
                rc, out, timed_out = env.exec(script, wait, s["server"])
                rec.update(exit_code=rc, duration_s=round(time.time() - ts, 2), output_tail="\n".join(out.strip().splitlines()[-15:]))
                if s["server"] and timed_out:
                    rec.update(exit_code=0, notes=s["notes"] + [f"long-running server stayed up for {wait}s; counted as success"])
                elif rc != 0:
                    ok = False
                    result["friction"].append(classify_failure(s, rc, out))
                rec["status"] = "ok" if rec["exit_code"] == 0 else "failed"
                print(f"  [{rec['status']:>6}] {rec['duration_s']:>6.1f}s  {s['cmd']}")
                result["steps"].append(rec)
            ran = [r for r in result["steps"] if r.get("status")]
            result["success"] = ok and bool(ran)
            if result["success"]:
                result["time_to_first_success_s"] = round(time.time() - t0, 1)
        finally:
            env.close(a.keep)
            if a.keep:
                result["notes"].append(f"sandbox kept at {sandbox}")
    else:
        result["steps"] = [{"n": i, "cmd": s["cmd"], "action": s["action"], "notes": s["notes"]} for i, s in enumerate(steps, 1)]
    result["total_s"] = round(time.time() - started, 1)
    sev = {"blocker": 0, "major": 1, "minor": 2}
    result["friction"].sort(key=lambda f: sev[f["severity"]])
    out = Path(a.out) if a.out else C.state_path(root, "install.json")
    C.write_json(out, result)
    status = {True: "SUCCESS", False: "FAILED", None: "NOT RUN (static)"}[result["success"]]
    tts = result["time_to_first_success_s"]
    print(f"install test: {status} | time-to-first-success={'n/a' if tts is None else f'{tts}s'} | "
          f"friction={len(result['friction'])} -> {out}")
    for f in result["friction"]:
        print(f"  - [{f['severity']}] {f['type']}: {f['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
