#!/usr/bin/env python3
"""Zero-dependency terminal demo GIF renderer (Python stdlib only).

Fallback when VHS / ffmpeg / Playwright are not installed, and a fast way to render library
"code + output" demos. Commands can be executed for real (`"exec": true`) so the GIF shows
genuine output.

Usage: text_gif.py scene.json out.gif [--cwd DIR] [--preview last-frame.png]

Scene (see references/demo-pipeline.md):
{
  "title": "my-tool", "cols": 80, "rows": 20, "scale": 2, "prompt": "$ ", "typing_ms": 45,
  "end_hold_ms": 3500,
  "steps": [
    {"type": "command", "text": "mytool --help", "exec": true},           # real output
    {"type": "command", "text": "mytool run", "output": "{g}done{/}"},   # scripted output
    {"type": "output", "text": "line one\\nline two", "line_ms": 60},
    {"type": "comment", "text": "# shown dimmed, typed"},
    {"type": "sleep", "ms": 800},
    {"type": "clear"}
  ]
}
Colour tags in text: {g} green {r} red {y} yellow {c} cyan {m} magenta {bl} blue {d} dim {b} bright {/} reset.
ANSI colour codes in exec output are mapped to the same palette.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

PALETTE = [
    (0x0d, 0x11, 0x17),  # 0 background
    (0xe6, 0xed, 0xf3),  # 1 foreground
    (0x7d, 0x85, 0x90),  # 2 dim
    (0x3f, 0xb9, 0x50),  # 3 green
    (0xf8, 0x51, 0x49),  # 4 red
    (0xd2, 0x99, 0x22),  # 5 yellow
    (0x39, 0xc5, 0xcf),  # 6 cyan
    (0xbc, 0x8c, 0xff),  # 7 magenta
    (0x58, 0xa6, 0xff),  # 8 blue
    (0xff, 0xff, 0xff),  # 9 bright
    (0x16, 0x1b, 0x22),  # 10 title bar
    (0x30, 0x36, 0x3d),  # 11 border
    (0xff, 0x5f, 0x57),  # 12 dot red
    (0xfe, 0xbc, 0x2e),  # 13 dot yellow
    (0x28, 0xc8, 0x40),  # 14 dot green
    (0x01, 0x04, 0x09),  # 15 outer
]
TAGS = {"g": 3, "r": 4, "y": 5, "c": 6, "m": 7, "bl": 8, "d": 2, "b": 9, "/": 1}
ANSI = {30: 2, 31: 4, 32: 3, 33: 5, 34: 8, 35: 7, 36: 6, 37: 1, 90: 2, 91: 4, 92: 3, 93: 5, 94: 8, 95: 7, 96: 6, 97: 9}

# 5x8 bitmap font: 8 rows of 5 columns, row 7 is for descenders.
_FONT = """
  |.....|.....|.....|.....|.....|.....|.....|.....
! |..#..|..#..|..#..|..#..|..#..|.....|..#..|.....
" |.#.#.|.#.#.|.....|.....|.....|.....|.....|.....
# |.#.#.|.#.#.|#####|.#.#.|#####|.#.#.|.#.#.|.....
$ |..#..|.####|#.#..|.###.|..#.#|####.|..#..|.....
% |##...|##..#|...#.|..#..|.#...|#..##|...##|.....
& |.##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#|.....
' |..#..|..#..|.....|.....|.....|.....|.....|.....
( |...#.|..#..|.#...|.#...|.#...|..#..|...#.|.....
) |.#...|..#..|...#.|...#.|...#.|..#..|.#...|.....
* |.....|..#..|#.#.#|.###.|#.#.#|..#..|.....|.....
+ |.....|..#..|..#..|#####|..#..|..#..|.....|.....
, |.....|.....|.....|.....|.....|..#..|..#..|.#...
- |.....|.....|.....|#####|.....|.....|.....|.....
. |.....|.....|.....|.....|.....|.....|..#..|.....
/ |.....|....#|...#.|..#..|.#...|#....|.....|.....
0 |.###.|#...#|#..##|#.#.#|##..#|#...#|.###.|.....
1 |..#..|.##..|..#..|..#..|..#..|..#..|.###.|.....
2 |.###.|#...#|....#|...#.|..#..|.#...|#####|.....
3 |#####|...#.|..#..|...#.|....#|#...#|.###.|.....
4 |...#.|..##.|.#.#.|#..#.|#####|...#.|...#.|.....
5 |#####|#....|####.|....#|....#|#...#|.###.|.....
6 |..##.|.#...|#....|####.|#...#|#...#|.###.|.....
7 |#####|....#|...#.|..#..|.#...|.#...|.#...|.....
8 |.###.|#...#|#...#|.###.|#...#|#...#|.###.|.....
9 |.###.|#...#|#...#|.####|....#|...#.|.##..|.....
: |.....|.....|..#..|.....|.....|..#..|.....|.....
; |.....|.....|..#..|.....|.....|..#..|..#..|.#...
< |...#.|..#..|.#...|#....|.#...|..#..|...#.|.....
= |.....|.....|#####|.....|#####|.....|.....|.....
> |.#...|..#..|...#.|....#|...#.|..#..|.#...|.....
? |.###.|#...#|....#|...#.|..#..|.....|..#..|.....
@ |.###.|#...#|....#|.##.#|#.#.#|#.#.#|.###.|.....
A |.###.|#...#|#...#|#####|#...#|#...#|#...#|.....
B |####.|#...#|#...#|####.|#...#|#...#|####.|.....
C |.###.|#...#|#....|#....|#....|#...#|.###.|.....
D |###..|#..#.|#...#|#...#|#...#|#..#.|###..|.....
E |#####|#....|#....|####.|#....|#....|#####|.....
F |#####|#....|#....|####.|#....|#....|#....|.....
G |.###.|#...#|#....|#.###|#...#|#...#|.####|.....
H |#...#|#...#|#...#|#####|#...#|#...#|#...#|.....
I |.###.|..#..|..#..|..#..|..#..|..#..|.###.|.....
J |..###|...#.|...#.|...#.|...#.|#..#.|.##..|.....
K |#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#|.....
L |#....|#....|#....|#....|#....|#....|#####|.....
M |#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#|.....
N |#...#|#...#|##..#|#.#.#|#..##|#...#|#...#|.....
O |.###.|#...#|#...#|#...#|#...#|#...#|.###.|.....
P |####.|#...#|#...#|####.|#....|#....|#....|.....
Q |.###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#|.....
R |####.|#...#|#...#|####.|#.#..|#..#.|#...#|.....
S |.####|#....|#....|.###.|....#|....#|####.|.....
T |#####|..#..|..#..|..#..|..#..|..#..|..#..|.....
U |#...#|#...#|#...#|#...#|#...#|#...#|.###.|.....
V |#...#|#...#|#...#|#...#|#...#|.#.#.|..#..|.....
W |#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.|.....
X |#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#|.....
Y |#...#|#...#|.#.#.|..#..|..#..|..#..|..#..|.....
Z |#####|....#|...#.|..#..|.#...|#....|#####|.....
[ |.###.|.#...|.#...|.#...|.#...|.#...|.###.|.....
\\ |.....|#....|.#...|..#..|...#.|....#|.....|.....
] |.###.|...#.|...#.|...#.|...#.|...#.|.###.|.....
^ |..#..|.#.#.|#...#|.....|.....|.....|.....|.....
_ |.....|.....|.....|.....|.....|.....|.....|#####
` |.#...|..#..|.....|.....|.....|.....|.....|.....
a |.....|.....|.###.|....#|.####|#...#|.####|.....
b |#....|#....|#.##.|##..#|#...#|#...#|####.|.....
c |.....|.....|.###.|#....|#....|#...#|.###.|.....
d |....#|....#|.##.#|#..##|#...#|#...#|.####|.....
e |.....|.....|.###.|#...#|#####|#....|.###.|.....
f |..##.|.#..#|.#...|###..|.#...|.#...|.#...|.....
g |.....|.....|.####|#...#|#...#|.####|....#|.###.
h |#....|#....|#.##.|##..#|#...#|#...#|#...#|.....
i |..#..|.....|.##..|..#..|..#..|..#..|.###.|.....
j |...#.|.....|..##.|...#.|...#.|...#.|#..#.|.##..
k |#....|#....|#..#.|#.#..|##...|#.#..|#..#.|.....
l |.##..|..#..|..#..|..#..|..#..|..#..|.###.|.....
m |.....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#|.....
n |.....|.....|#.##.|##..#|#...#|#...#|#...#|.....
o |.....|.....|.###.|#...#|#...#|#...#|.###.|.....
p |.....|.....|####.|#...#|#...#|####.|#....|#....
q |.....|.....|.####|#...#|#...#|.####|....#|....#
r |.....|.....|#.##.|##..#|#....|#....|#....|.....
s |.....|.....|.###.|#....|.###.|....#|####.|.....
t |.#...|.#...|###..|.#...|.#...|.#..#|..##.|.....
u |.....|.....|#...#|#...#|#...#|#..##|.##.#|.....
v |.....|.....|#...#|#...#|#...#|.#.#.|..#..|.....
w |.....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.|.....
x |.....|.....|#...#|.#.#.|..#..|.#.#.|#...#|.....
y |.....|.....|#...#|#...#|#...#|.####|....#|.###.
z |.....|.....|#####|...#.|..#..|.#...|#####|.....
{ |...#.|..#..|..#..|.#...|..#..|..#..|...#.|.....
| |..#..|..#..|..#..|..#..|..#..|..#..|..#..|.....
} |.#...|..#..|..#..|...#.|..#..|..#..|.#...|.....
~ |.....|.....|.#...|#.#.#|...#.|.....|.....|.....
→ |.....|..#..|...#.|#####|...#.|..#..|.....|.....
✓ |.....|....#|...#.|#.#..|.#...|.....|.....|.....
✗ |.....|#...#|.#.#.|..#..|.#.#.|#...#|.....|.....
• |.....|.....|.###.|.###.|.###.|.....|.....|.....
· |.....|.....|.....|..#..|.....|.....|.....|.....
— |.....|.....|.....|#####|.....|.....|.....|.....
… |.....|.....|.....|.....|.....|.....|#.#.#|.....
█ |#####|#####|#####|#####|#####|#####|#####|#####
░ |#.#.#|.#.#.|#.#.#|.#.#.|#.#.#|.#.#.|#.#.#|.#.#.
❯ |##...|.##..|..##.|...##|..##.|.##..|##...|.....
★ |..#..|..#..|#####|.###.|.#.#.|#...#|.....|.....
"""


def _load_font():
    font = {}
    for line in _FONT.strip("\n").splitlines():
        font[line[0]] = [r for r in line[3:].split("|") if len(r) == 5]
    return font


FONT = _load_font()
GW, GH = 5, 8


class Term:
    def __init__(self, cols, rows, scale, title):
        self.cols, self.rows, self.s = cols, rows, scale
        self.cw, self.ch = (GW + 1) * scale, (GH + 2) * scale
        self.pad = 8 * scale
        self.bar = 14 * scale
        self.W = cols * self.cw + 2 * self.pad
        self.H = rows * self.ch + 2 * self.pad + self.bar
        self.px = bytearray([0]) * (self.W * self.H)
        self.grid = [[(" ", 1)] * cols for _ in range(rows)]
        self.cache = {}
        self.dirty = None
        self.cx = self.cy = 0
        self._chrome(title)
        self.dirty = (0, 0, self.W, self.H)

    def _rect(self, x, y, w, h, c):
        row = bytes([c]) * w
        for yy in range(y, y + h):
            o = yy * self.W + x
            self.px[o:o + w] = row

    def _chrome(self, title):
        self._rect(0, 0, self.W, self.bar, 10)
        self._rect(0, self.bar, self.W, 1, 11)
        r = 3 * self.s
        for i, c in enumerate((12, 13, 14)):
            cx, cy = self.pad + r + i * (3 * r), self.bar // 2
            for yy in range(-r, r + 1):
                for xx in range(-r, r + 1):
                    if xx * xx + yy * yy <= r * r:
                        self.px[(cy + yy) * self.W + cx + xx] = c
        if title:
            tx = (self.W - len(title) * self.cw) // 2
            ty = (self.bar - GH * self.s) // 2
            for i, chv in enumerate(title):
                self._blit(tx + i * self.cw, ty, chv, 2, 10)

    def _glyph(self, ch, fg, bg):
        key = (ch, fg, bg)
        if key not in self.cache:
            rows = FONT.get(ch) or FONT["?"]
            out = []
            for y in range(GH + 2):
                if 1 <= y <= GH:
                    bits = rows[y - 1]
                    line = b"".join(bytes([fg if b == "#" else bg]) * self.s for b in bits) + bytes([bg]) * self.s
                else:
                    line = bytes([bg]) * self.cw
                out += [line] * self.s
            self.cache[key] = out
        return self.cache[key]

    def _blit(self, x, y, ch, fg, bg):
        for i, line in enumerate(self._glyph(ch, fg, bg)):
            o = (y + i) * self.W + x
            self.px[o:o + len(line)] = line

    def _mark(self, x0, y0, x1, y1):
        if self.dirty is None:
            self.dirty = (x0, y0, x1, y1)
        else:
            d = self.dirty
            self.dirty = (min(d[0], x0), min(d[1], y0), max(d[2], x1), max(d[3], y1))

    def draw_cell(self, col, row, cursor=False):
        ch, fg = self.grid[row][col]
        x = self.pad + col * self.cw
        y = self.bar + self.pad + row * self.ch
        if cursor:
            self._blit(x, y, ch if ch != " " else " ", 0, 1)
        else:
            self._blit(x, y, ch, fg, 0)
        self._mark(x, y, x + self.cw, y + self.ch)

    def redraw_all(self):
        self._rect(0, self.bar + 1, self.W, self.H - self.bar - 1, 0)
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c][0] != " ":
                    self.draw_cell(c, r)
        self._mark(0, self.bar + 1, self.W, self.H)

    def put(self, ch, fg):
        if ch == "\n":
            self.newline()
            return
        if self.cx >= self.cols:
            self.newline()
        self.grid[self.cy][self.cx] = (ch, fg)
        self.draw_cell(self.cx, self.cy)
        self.cx += 1

    def newline(self):
        self.cx = 0
        self.cy += 1
        if self.cy >= self.rows:
            self.grid.pop(0)
            self.grid.append([(" ", 1)] * self.cols)
            self.cy = self.rows - 1
            self.redraw_all()

    def clear(self):
        self.grid = [[(" ", 1)] * self.cols for _ in range(self.rows)]
        self.cx = self.cy = 0
        self.redraw_all()

    def cursor(self, on):
        if self.cx < self.cols:
            self.draw_cell(self.cx, self.cy, cursor=on)

    def take_dirty(self):
        d, self.dirty = self.dirty, None
        return d


# ---------------------------------------------------------------- GIF encoding

def lzw(indices: bytes, min_code: int) -> bytes:
    clear, eoi = 1 << min_code, (1 << min_code) + 1
    out, bitbuf, nbits = bytearray(), 0, 0
    size = min_code + 1

    def emit(code):
        nonlocal bitbuf, nbits
        bitbuf |= code << nbits
        nbits += size
        while nbits >= 8:
            out.append(bitbuf & 0xFF)
            bitbuf >>= 8
            nbits -= 8

    table = {bytes([i]): i for i in range(clear)}
    nxt = eoi + 1
    emit(clear)
    w = b""
    for b in indices:
        wc = w + bytes([b])
        if wc in table:
            w = wc
            continue
        emit(table[w])
        if nxt < 4096:
            table[wc] = nxt
            nxt += 1
            if nxt > (1 << size) and size < 12:
                size += 1
        else:
            emit(clear)
            table = {bytes([i]): i for i in range(clear)}
            nxt, size = eoi + 1, min_code + 1
        w = bytes([b])
    if w:
        emit(table[w])
    emit(eoi)
    if nbits:
        out.append(bitbuf & 0xFF)
    blocks = bytearray()
    for i in range(0, len(out), 255):
        chunk = out[i:i + 255]
        blocks += bytes([len(chunk)]) + chunk
    return bytes(blocks) + b"\x00"


class GifWriter:
    def __init__(self, path, W, H):
        self.f = open(path, "wb")
        self.W, self.H = W, H
        self.f.write(b"GIF89a" + struct.pack("<HHBBB", W, H, 0xF3, 0, 0))  # global table, 16 colours
        for r, g, b in PALETTE:
            self.f.write(bytes([r, g, b]))
        self.f.write(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")  # loop forever
        self.pending = None

    def frame(self, px, rect, delay_ms):
        if self.pending:
            self._write(*self.pending, delay_ms=self.pending_delay)
        self.pending = (bytes(self._crop(px, rect)), rect)
        self.pending_delay = delay_ms

    def hold(self, delay_ms):
        if self.pending:
            self.pending_delay += delay_ms

    def _crop(self, px, rect):
        x0, y0, x1, y1 = rect
        out = bytearray()
        for y in range(y0, y1):
            out += px[y * self.W + x0:y * self.W + x1]
        return out

    def _write(self, data, rect, delay_ms):
        x0, y0, x1, y1 = rect
        cs = max(2, min(65535, round(delay_ms / 10)))
        self.f.write(b"\x21\xF9\x04" + struct.pack("<BHBB", 0x04, cs, 0, 0))  # disposal: leave in place
        self.f.write(b"\x2C" + struct.pack("<HHHHB", x0, y0, x1 - x0, y1 - y0, 0))
        self.f.write(b"\x04" + lzw(data, 4))

    def close(self):
        if self.pending:
            self._write(*self.pending, delay_ms=self.pending_delay)
        self.f.write(b"\x3B")
        self.f.close()


def write_png(path, px, W, H):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        for i in px[y * W:(y + 1) * W]:
            raw += bytes(PALETTE[i])
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(data)


# ---------------------------------------------------------------- scene

def parse_colored(text: str, default=1):
    """Yield (char, colour) from text with {tags} and ANSI SGR codes."""
    colour = default
    i = 0
    while i < len(text):
        if text.startswith("{{", i):
            yield "{", colour
            i += 2
            continue
        m = re.match(r"\{(g|r|y|c|m|bl|d|b|/)\}", text[i:])
        if m:
            colour = default if m.group(1) == "/" else TAGS[m.group(1)]
            i += m.end()
            continue
        m = re.match(r"\x1b\[([\d;]*)m", text[i:])
        if m:
            for code in (int(c) for c in m.group(1).split(";") if c):
                if code == 0:
                    colour = default
                elif code in ANSI:
                    colour = ANSI[code]
                elif code == 1 and colour == default:
                    colour = 9
                elif code == 2:
                    colour = 2
            i += m.end()
            continue
        m = re.match(r"\x1b\[[\d;?]*[A-Za-z]", text[i:])
        if m:
            i += m.end()
            continue
        ch = text[i]
        if ch == "\t":
            for _ in range(4):
                yield " ", colour
        elif ch == "\r":
            pass
        else:
            yield ch, colour
        i += 1


def run(cmd, cwd, cols=80):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "COLUMNS": str(cols), "FORCE_COLOR": "1", "CLICOLOR_FORCE": "1"})
    return (r.stdout + r.stderr).rstrip("\n")


def render(scene: dict, out: str, cwd: str | None, preview: str | None):
    t = Term(scene.get("cols", 80), scene.get("rows", 20), scene.get("scale", 2), scene.get("title", ""))
    gif = GifWriter(out, t.W, t.H)
    prompt = scene.get("prompt", "$ ")
    typing = scene.get("typing_ms", 45)

    def frame(ms):
        d = t.take_dirty()
        if d:
            gif.frame(t.px, d, ms)
        else:
            gif.hold(ms)

    def show_prompt():
        for ch, c in parse_colored(scene.get("prompt_color", "{g}") + prompt + "{/}"):
            t.put(ch, c)
        t.cursor(True)

    show_prompt()
    frame(600)
    for step in scene.get("steps", []):
        kind = step.get("type", "command")
        if kind in ("command", "comment"):
            colour = 2 if kind == "comment" else 1
            for ch, c in parse_colored(step["text"], colour):
                t.cursor(False)
                t.put(ch, c)
                t.cursor(True)
                frame(step.get("typing_ms", typing))
            frame(step.get("pause_ms", 350))
            t.cursor(False)
            t.newline()
            if kind == "command":
                output = run(step["text"], step.get("cwd") or cwd, t.cols) if step.get("exec") else step.get("output", "")
                if step.get("max_lines") and output:
                    output = "\n".join(output.splitlines()[:step["max_lines"]])
                if output:
                    _print_lines(t, output, step.get("line_ms", 40), frame)
                frame(step.get("after_ms", 700))
            show_prompt()
            frame(200)
        elif kind == "output":
            t.cursor(False)
            if t.cx:
                t.newline()
            _print_lines(t, step["text"], step.get("line_ms", 40), frame)
            show_prompt()
            frame(200)
        elif kind == "sleep":
            frame(step.get("ms", 800))
        elif kind == "clear":
            t.clear()
            show_prompt()
            frame(200)
        else:
            raise SystemExit(f"unknown step type: {kind}")
    frame(scene.get("end_hold_ms", 3500))
    gif.hold(scene.get("end_hold_ms", 3500))
    gif.close()
    if preview:
        write_png(preview, t.px, t.W, t.H)
    return t.W, t.H


def _print_lines(t, text, line_ms, frame):
    lines = text.split("\n")
    for line in lines:
        for ch, c in parse_colored(line):
            t.put(ch, c)
        t.newline()
        frame(line_ms)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene")
    ap.add_argument("out")
    ap.add_argument("--cwd", help="working directory for exec steps (default: scene file's directory)")
    ap.add_argument("--preview", help="also write the last frame as PNG")
    a = ap.parse_args()
    scene = json.loads(Path(a.scene).read_text(encoding="utf-8"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    scene_dir = Path(a.scene).resolve().parent
    cwd = a.cwd or str((scene_dir / scene["cwd"]).resolve() if scene.get("cwd") else scene_dir)
    W, H = render(scene, a.out, cwd, a.preview)
    size = Path(a.out).stat().st_size
    print(f"-> {a.out} ({W}x{H}, {size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
