"""Deterministic tests for Launch Lab's scripts, run against evals/fixtures.

    python3 -m unittest discover -s tests -v

Stdlib only. Nothing here touches the network; the one local install run executes the
great-readme fixture's own one-line shell script inside a temp directory.
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "launch-lab" / "scripts"
FIXTURES = ROOT / "evals" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import text_gif  # noqa: E402


def run(script, *args, check=True):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(f"{script} {args} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="launch-lab-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def repo(self, name):
        dest = self.tmp / name
        shutil.copytree(FIXTURES / name, dest)
        return dest

    def scan(self, name):
        repo = self.repo(name)
        run("scan.py", repo, "--offline")
        return repo, json.loads((repo / ".launch-lab" / "scan.json").read_text())


class TestScan(FixtureCase):
    def test_repo_types(self):
        expected = {"cli-repo": "cli", "web-app": "web", "library": "library", "broken-install": "cli",
                    "confusing-readme": "library", "great-readme": "cli", "no-demo": "cli"}
        for name, kind in expected.items():
            with self.subTest(name):
                _, scan = self.scan(name)
                self.assertEqual(scan["repo_type"]["type"], kind, scan["repo_type"]["evidence"])

    def test_fold_and_signals(self):
        _, great = self.scan("great-readme")
        self.assertTrue(great["signals"]["demo_in_fold"])
        self.assertTrue(great["signals"]["comparison"]["table"])
        self.assertEqual(great["fold"]["title"], "greet")
        self.assertIn("[animated image:", great["fold"]["rendered"])
        _, confusing = self.scan("confusing-readme")
        self.assertEqual(confusing["signals"]["badges_in_fold"], 8)
        self.assertEqual(confusing["quickstart"]["command_count"], 0)
        self.assertIn("REDIS_URL", confusing["signals"]["env_vars"]["undocumented"])
        _, lib = self.scan("library")
        self.assertEqual(lib["quickstart"]["commands"], ["npm install tinyretry"])
        tests_dir = self.repo("cli-repo") / "tests"
        tests_dir.mkdir()
        (tests_dir / "t.py").write_text("import os\nos.environ['FIXTURE_ONLY_TOKEN']\n")
        run("scan.py", tests_dir.parent, "--offline")
        scan = json.loads((tests_dir.parent / ".launch-lab" / "scan.json").read_text())
        self.assertNotIn("FIXTURE_ONLY_TOKEN", scan["signals"]["env_vars"]["found"])
        _, nodemo = self.scan("no-demo")
        self.assertFalse(nodemo["signals"]["demo_media"])


class TestPanel(FixtureCase):
    def test_prompts_contain_only_the_fold(self):
        repo, scan = self.scan("confusing-readme")
        run("panel.py", "prompts", repo)
        prompts = json.loads((repo / ".launch-lab" / "panel_prompts.json").read_text())["prompts"]
        self.assertGreaterEqual(len(prompts), 3)
        for p in prompts:
            self.assertIn("synergy-driven", p["prompt"])
            self.assertNotIn("ioredis", p["prompt"])  # source code never reaches a persona

    def test_custom_personas(self):
        repo, _ = self.scan("library")
        cfg = {"personas": [{"id": "sre", "name": "SRE on call", "brief": "Wants reliable retries."}]}
        (repo / ".launch-lab" / "config.json").write_text(json.dumps(cfg))
        run("panel.py", "prompts", repo)
        ids = [p["id"] for p in json.loads((repo / ".launch-lab" / "panel_prompts.json").read_text())["prompts"]]
        self.assertEqual(ids, ["skeptical-hn", "beginner", "busy-cto", "sre"])

    def test_validate_rejects_bad_grades(self):
        repo, _ = self.scan("great-readme")
        panel = json.loads((FIXTURES / "great-readme" / "panel.sample.json").read_text())
        panel["personas"][0]["grade"]["purpose_match"] = 0.7
        (repo / ".launch-lab" / "panel.json").write_text(json.dumps(panel))
        r = run("panel.py", "validate", repo, check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("must be 0, 0.5 or 1", r.stderr)


class TestInstall(FixtureCase):
    def test_static_friction(self):
        repo, _ = self.scan("broken-install")
        run("install_test.py", repo, "--mode", "static")
        res = json.loads((repo / ".launch-lab" / "install.json").read_text())
        kinds = {(f["type"], f["detail"].split()[0]) for f in res["friction"]}
        self.assertIn(("undocumented_env_var", "WEATHER_API_KEY"), kinds)
        self.assertTrue(any(f["type"] == "unstated_version" for f in res["friction"]))
        self.assertTrue(any(f["type"] == "unclear_step" for f in res["friction"]))
        self.assertIsNone(res["success"])
        self.assertFalse(res["measured"])

    def test_plan_rewrites_self_clone(self):
        repo, _ = self.scan("web-app")
        r = run("install_test.py", repo, "--dry-run")
        self.assertIn('cp -R "$LL_SNAPSHOT" pinboard-lite', r.stdout)

    def test_local_requires_yes(self):
        repo, _ = self.scan("great-readme")
        r = run("install_test.py", repo, "--mode", "local", check=False)
        self.assertEqual(r.returncode, 3)

    def test_local_run_succeeds_and_keeps_cwd(self):
        repo, _ = self.scan("great-readme")
        run("install_test.py", repo, "--mode", "local", "--yes")
        res = json.loads((repo / ".launch-lab" / "install.json").read_text())
        self.assertTrue(res["success"], res)
        self.assertEqual(res["steps"][-1]["output_tail"], "Hello, World!")
        self.assertIsNotNone(res["time_to_first_success_s"])


class TestScore(FixtureCase):
    def score(self, name, panel=True, install_local=False):
        repo, _ = self.scan(name)
        if panel:
            shutil.copy(FIXTURES / name / "panel.sample.json", repo / ".launch-lab" / "panel.json")
        if install_local:
            run("install_test.py", repo, "--mode", "local", "--yes")
        run("score.py", repo, "--round", "0")
        return repo, json.loads((repo / ".launch-lab" / "score.json").read_text())

    def test_great_beats_confusing(self):
        _, great = self.score("great-readme", install_local=True)
        _, confusing = self.score("confusing-readme")
        self.assertGreaterEqual(great["score"], 80)
        self.assertLess(confusing["score"], 30)
        self.assertFalse(great["provisional"])
        self.assertTrue(confusing["provisional"])
        self.assertEqual(confusing["top_fixes"][0]["category"], "clarity")

    def test_unmeasured_categories_are_excluded(self):
        _, res = self.score("no-demo", panel=False)
        self.assertIn("clarity", res["unmeasured"])
        self.assertEqual(res["measured_weight"], 45)
        self.assertEqual(res["top_fixes"][0]["category"], "demo")

    def test_report_svg_and_before_after(self):
        repo, first = self.score("great-readme")
        (repo / "README.md").write_text((repo / "README.md").read_text().replace("## How is this different?", "## Notes"))
        run("scan.py", repo, "--offline")
        run("score.py", repo, "--round", "1", "--before", ".launch-lab/score.round0.json")
        res = json.loads((repo / ".launch-lab" / "score.json").read_text())
        self.assertLess(res["score"], first["score"])
        self.assertEqual(res["before"]["score"], first["score"])
        self.assertIn("panel was run on an older README fold", res["stale"]) if res["stale"] else None
        report = (repo / "launch" / "report.md").read_text()
        self.assertIn("Top 5 fixes", report)
        self.assertIn("before:", report)
        svg = (repo / "launch" / "score-card.svg").read_text()
        self.assertTrue(svg.startswith("<svg") and "prefers-color-scheme" in svg)


class TestDiagnose(FixtureCase):
    def diagnose(self, fixture):
        out = self.tmp / fixture
        out.mkdir()
        run("github_metrics.py", "--from-file", FIXTURES / "post-launch-data" / f"{fixture}.json", "--repo-dir", out, "--no-save")
        return json.loads((out / ".launch-lab" / "diagnosis.json").read_text())

    def test_patterns(self):
        for fixture, expected in {"readme-problem": "readme", "distribution-problem": "distribution",
                                  "spike-then-flat": "retention"}.items():
            with self.subTest(fixture):
                self.assertEqual(self.diagnose(fixture)["diagnosis"]["primary"], expected)

    def test_referrer_conversion_needs_three_snapshots(self):
        res = self.diagnose("three-snapshots")
        conv = {r["referrer"]: r["est_conversion"] for r in res["referrers"]}
        self.assertGreater(conv["reddit.com"], conv["news.ycombinator.com"])
        single = self.diagnose("readme-problem")
        self.assertTrue(all(r["est_conversion"] is None for r in single["referrers"]))

    def test_history_is_saved(self):
        out = self.tmp / "hist"
        out.mkdir()
        for _ in range(2):
            run("github_metrics.py", "--from-file", FIXTURES / "post-launch-data" / "readme-problem.json", "--repo-dir", out)
        hist = json.loads((out / ".launch-lab" / "history.json").read_text())
        self.assertEqual(len(hist["snapshots"]), 2)


# ---------------------------------------------------------------- GIF decoding (verifies the encoder)

def lzw_decode(data: bytes, min_code: int) -> bytes:
    clear, eoi = 1 << min_code, (1 << min_code) + 1
    size, pos, out = min_code + 1, 0, bytearray()
    table = [bytes([i]) for i in range(clear)] + [b"", b""]
    prev = None
    nbits = len(data) * 8
    while pos + size <= nbits:
        code = 0
        for i in range(size):
            if data[(pos + i) >> 3] >> ((pos + i) & 7) & 1:
                code |= 1 << i
        pos += size
        if code == clear:
            table = [bytes([i]) for i in range(clear)] + [b"", b""]
            size, prev = min_code + 1, None
            continue
        if code == eoi:
            break
        if code < len(table):
            entry = table[code]
            if prev is not None and len(table) < 4096:
                table.append(prev + entry[:1])
        else:
            entry = prev + prev[:1]
            table.append(entry)
        out += entry
        prev = entry
        if len(table) == (1 << size) and size < 12:
            size += 1
    return bytes(out)


def gif_frames(path: Path):
    b = path.read_bytes()
    assert b[:6] == b"GIF89a"
    w, h, packed = int.from_bytes(b[6:8], "little"), int.from_bytes(b[8:10], "little"), b[10]
    i = 13 + 3 * (2 << (packed & 7))
    frames = []
    while b[i] != 0x3B:
        if b[i] == 0x21:  # extension: skip sub-blocks
            i += 2
            while b[i]:
                i += b[i] + 1
            i += 1
        elif b[i] == 0x2C:
            fw, fh = int.from_bytes(b[i + 5:i + 7], "little"), int.from_bytes(b[i + 7:i + 9], "little")
            min_code, i = b[i + 10], i + 11
            data = bytearray()
            while b[i]:
                data += b[i + 1:i + 1 + b[i]]
                i += b[i] + 1
            i += 1
            frames.append((fw, fh, lzw_decode(bytes(data), min_code)))
        else:
            raise AssertionError(f"bad block 0x{b[i]:02x}")
    return w, h, frames


class TestTextGif(unittest.TestCase):
    def test_lzw_roundtrip(self):
        rng = random.Random(7)
        for n in (1, 2, 300, 5000, 70000):
            data = bytes(rng.choice([0, 0, 0, 1, 2, 3, 9, 15]) for _ in range(n))
            raw = text_gif.lzw(data, 4)
            joined, i = bytearray(), 0
            while raw[i]:
                joined += raw[i + 1:i + 1 + raw[i]]
                i += raw[i] + 1
            self.assertEqual(lzw_decode(bytes(joined), 4), data)

    def test_render_decodes(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            scene = {"title": "t", "cols": 30, "rows": 5, "steps": [
                {"type": "command", "text": "echo hi", "exec": True}, {"type": "output", "text": "{g}ok{/}"}]}
            (tmp / "s.json").write_text(json.dumps(scene))
            subprocess.run([sys.executable, str(SCRIPTS / "text_gif.py"), tmp / "s.json", tmp / "o.gif"], check=True, capture_output=True)
            w, h, frames = gif_frames(tmp / "o.gif")
            self.assertGreater(len(frames), 5)
            fw, fh, px = frames[0]
            self.assertEqual((fw, fh), (w, h))
            self.assertEqual(len(px), w * h)
            for fw, fh, px in frames:
                self.assertEqual(len(px), fw * fh)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
