#!/usr/bin/env node
// Record a web demo with Playwright from a reproducible scenario file.
//
// Usage: node record_web.mjs scenario.json [--out launch/demo/web.webm] [--headed]
// Needs Playwright:  npm i -D playwright && npx playwright install chromium
// Then convert:      gif_optimize.sh launch/demo/web.webm launch/demo/demo.gif
//
// Scenario (see references/demo-pipeline.md):
// {
//   "url": "http://localhost:3000",                 // or file:///abs/path/page.html
//   "start": {"command": "npm run dev", "wait_for": "http://localhost:3000", "timeout_ms": 60000},
//   "viewport": {"width": 1280, "height": 720},
//   "inject": "launch/demo/snippet.json",           // optional: exposed as window.__SNIPPET__
//   "steps": [
//     {"action": "wait", "ms": 800},
//     {"action": "click", "selector": "text=Get started"},
//     {"action": "type", "selector": "#search", "text": "hello", "delay": 80},
//     {"action": "press", "key": "Enter"},
//     {"action": "scroll", "y": 600},
//     {"action": "hover", "selector": ".card"},
//     {"action": "waitFor", "selector": ".result"},
//     {"action": "waitForDone"},                     // waits for window.__DONE__ === true
//     {"action": "goto", "url": "/about"}
//   ],
//   "out": "launch/demo/web.webm"
// }
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
if (!args[0] || args.includes("--help")) {
  console.log("usage: node record_web.mjs scenario.json [--out file.webm] [--headed]");
  process.exit(args[0] ? 0 : 2);
}
const scenarioPath = path.resolve(args[0]);
const scenario = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
const outIdx = args.indexOf("--out");
const out = path.resolve(outIdx >= 0 ? args[outIdx + 1] : scenario.out || "launch/demo/web.webm");
const headed = args.includes("--headed");
const viewport = scenario.viewport || { width: 1280, height: 720 };

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  console.error("Playwright is not installed. Run:\n  npm i -D playwright && npx playwright install chromium\n" +
    "or use the zero-dependency fallback: python3 scripts/text_gif.py scene.json demo.gif");
  process.exit(3);
}

async function waitForUrl(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(url);
      if (r.status < 500) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`server did not respond at ${url} within ${timeoutMs}ms`);
}

let server;
if (scenario.start?.command) {
  server = spawn(scenario.start.command, { shell: true, stdio: "inherit", detached: true });
  await waitForUrl(scenario.start.wait_for || scenario.url, scenario.start.timeout_ms || 60000);
}

const videoDir = fs.mkdtempSync(path.join(path.dirname(out), ".rec-"));
const browser = await chromium.launch({ headless: !headed });
const context = await browser.newContext({ viewport, recordVideo: { dir: videoDir, size: viewport }, deviceScaleFactor: 1 });
if (scenario.inject) {
  const data = JSON.parse(fs.readFileSync(path.resolve(path.dirname(scenarioPath), scenario.inject), "utf8"));
  await context.addInitScript((d) => { window.__SNIPPET__ = d; }, data);
}
const page = await context.newPage();
const base = scenario.url;
const abs = (u) => (u && !/^[a-z]+:/i.test(u) ? new URL(u, base).toString() : u);

try {
  await page.goto(base, { waitUntil: "load" });
  for (const s of scenario.steps || []) {
    switch (s.action) {
      case "wait": await page.waitForTimeout(s.ms ?? 1000); break;
      case "goto": await page.goto(abs(s.url), { waitUntil: "load" }); break;
      case "click": await page.click(s.selector); break;
      case "type": await page.locator(s.selector).pressSequentially(s.text, { delay: s.delay ?? 70 }); break;
      case "fill": await page.fill(s.selector, s.text); break;
      case "press": await page.keyboard.press(s.key); break;
      case "hover": await page.hover(s.selector); break;
      case "scroll": await page.mouse.wheel(0, s.y ?? 500); await page.waitForTimeout(400); break;
      case "waitFor": await page.waitForSelector(s.selector, { timeout: s.timeout_ms ?? 15000 }); break;
      case "waitForDone": await page.waitForFunction(() => window.__DONE__ === true, null, { timeout: s.timeout_ms ?? 60000 }); break;
      default: throw new Error(`unknown action: ${s.action}`);
    }
  }
  await page.waitForTimeout(scenario.end_hold_ms ?? 1200);
} finally {
  const video = page.video();
  await context.close();
  await browser.close();
  if (server) { try { process.kill(-server.pid); } catch {} }
  if (video) {
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.renameSync(await video.path(), out);
    console.log(`recorded -> ${out}`);
  }
  fs.rmSync(videoDir, { recursive: true, force: true });
}
