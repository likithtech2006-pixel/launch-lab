# Demo pipeline

One pipeline for every repo type. Every demo keeps a **reproducible source file** in
`launch/demo/` so it can be regenerated after the next release.

## 1. Detect the repo type

`scan.py` scores evidence and writes `repo_type.type`, `confidence`, `evidence` and
`demo_pipeline` to `.launch-lab/scan.json`:

| Evidence | Points |
|---|---|
| `bin` in package.json, `[project.scripts]`/console_scripts, `src/main.rs`, `main.go`/`cmd/*/main.go` | cli +4 |
| ink / blessed / textual / urwid / prompt_toolkit / ratatui / bubbletea / tview dependency | tui +5 |
| next / react-dom / vue / svelte / vite / express / flask / django / fastapi / streamlit / gin… | web +4 (+1 with a dev/start script) |
| `index.html` at root or in `public/` | web +2 |
| README mentions `localhost:PORT` or a deploy URL (vercel, netlify, pages, fly, render…) | web +2 |
| Package exports a library with no executables | library +3 |
| README shows `import` / `require` / `use` | library +2 |
| `SKILL.md` / `.claude-plugin` (agent skill or plugin) | skill +5/+2 (uses the terminal pipeline) |

If confidence is under 0.5, ask the user which type fits before recording.

## 2. Plan the demo (all types)

- **One idea, under 20 seconds.** Show the single moment that makes someone want it.
- Use **real commands with real output**. Never script fake output for a command that exists.
  If a command is slow, cut the waiting (VHS `Hide`/`Show`, or `"exec": true` plus shorter `after_ms`).
- Prefer a small sample project or fixture in `launch/demo/` over the user's private data.
- Sizes: 1000-1280 px wide source, GIF at 800-960 px, readable 14-16 px text.

## 3. CLI / TUI / skill: VHS

Install: `brew install vhs` (or see github.com/charmbracelet/vhs). Write `launch/demo/demo.tape`:

```tape
Output launch/demo/demo.gif
Set Shell "bash"
Set FontSize 16
Set Width 1100
Set Height 600
Set Theme "GitHub Dark"
Set TypingSpeed 45ms
Set Padding 20

Type "mytool init my-project" Sleep 300ms Enter
Sleep 2s
Type "mytool run" Sleep 300ms Enter
Sleep 3s
```

Run `vhs launch/demo/demo.tape`, then `scripts/gif_optimize.sh launch/demo/demo.gif launch/demo/demo.gif`
(GIF input is re-encoded through the palette ladder when ffmpeg is available). For TUIs, add key
presses (`Down`, `Tab`, `Enter`) with `Sleep` between them so viewers can follow.

## 4. Web app: Playwright + ffmpeg

Install once in the target repo (or a scratch dir): `npm i -D playwright && npx playwright install chromium`,
and `brew install ffmpeg`. Write `launch/demo/scenario.json` (format documented at the top of
`scripts/record_web.mjs`). For a local app use `start.command` (e.g. `npm run dev`) and
`start.wait_for`; for a deployed app just set `url`. Then:

```bash
node scripts/record_web.mjs launch/demo/scenario.json --out launch/demo/web.webm
scripts/gif_optimize.sh launch/demo/web.webm launch/demo/demo.gif --mp4
```

Keep the viewport at 1280x720, click with intent (no wandering cursor), and end on the result.

## 5. Library / SDK: animated snippet

1. Write a minimal, runnable example (10-15 lines) using the public API.
2. **Run it** and capture the real output.
3. Save `launch/demo/snippet.json`: `{"title": "example.py", "lang": "python", "code": "...", "output": "...", "typing_ms": 28}`.
4. Copy `assets/snippet.html` to `launch/demo/snippet.html` and write `launch/demo/scenario.json`:
   `{"url": "file:///ABS/PATH/launch/demo/snippet.html", "inject": "snippet.json", "viewport": {"width": 1200, "height": 680}, "steps": [{"action": "waitForDone"}]}`
5. `node scripts/record_web.mjs launch/demo/scenario.json` then `gif_optimize.sh`.

## 6. Zero-dependency fallback: text_gif.py

When VHS, ffmpeg or Playwright are missing (or for a quick draft), `scripts/text_gif.py` renders
a terminal session straight to GIF with the Python stdlib (built-in bitmap font, 16-colour palette,
frame differencing, so files are usually tens of KB). Write `launch/demo/scene.json`:

```json
{
  "title": "mytool", "cols": 80, "rows": 18, "typing_ms": 40,
  "steps": [
    {"type": "command", "text": "mytool --version", "exec": true},
    {"type": "command", "text": "mytool check .", "exec": true, "max_lines": 12},
    {"type": "sleep", "ms": 1500}
  ]
}
```

`"exec": true` runs the command (in `--cwd` or the scene's directory) and renders its real
output, mapping ANSI colours. `"output"` is allowed for steps that cannot run in the demo
environment (agent slash commands, interactive prompts); in that case the text must be copied
from a real run, not invented. Colour tags: `{g} {r} {y} {c} {m} {bl} {d} {b} {/}`.

`--preview last.png` writes the final frame as PNG for a quick visual check. Library demos can
also use it: a `comment` step for the file name, `output` steps for the code and the real output.

## 7. Size budget (gif_optimize.sh)

GitHub refuses image uploads over 10 MB and large GIFs load slowly through its image proxy, so the
default budget is **5 MB** (`--max-mb`). The script:

1. Generates a palette per attempt (`palettegen stats_mode=diff`), then applies it
   (`paletteuse dither=bayer diff_mode=rectangle`): the two-pass method gives far smaller, cleaner GIFs.
2. Walks the ladder `fps/width/colors`: 15/960/256, 12/960/256, 12/800/256, 12/800/128, 10/720/128,
   10/640/128, 10/640/64, 8/560/64, 8/480/64, 6/480/32, stopping at the first that fits.
3. If still too big and `gifsicle` exists: `-O3`, then `--lossy` 30→120.
4. `--mp4` also writes an H.264 MP4 (better for X/LinkedIn uploads).

If nothing fits, shorten the recording rather than shipping an unreadable GIF.

## 8. Embed

```markdown
<p align="center"><img src="launch/demo/demo.gif" alt="mytool scanning a repo and printing a 78/100 score" width="800"></p>
```

Write alt text that says what happens; the Stranger Panel reads it. Commit the GIF next to its
source file so it can be regenerated.
