#!/usr/bin/env bash
# Convert a video (or GIF) to a GIF that fits a size budget for GitHub READMEs.
#
# Usage: gif_optimize.sh INPUT OUTPUT.gif [--max-mb 5] [--fps 15] [--width 960] [--mp4]
#
# Two-pass palette (palettegen + paletteuse), then steps down fps, width and colors until the
# file fits. Uses gifsicle (if installed) for a final lossless/lossy squeeze. --mp4 also writes
# OUTPUT.mp4 (H.264, faststart) for platforms that prefer video.
# GitHub refuses images over 10 MB; the 5 MB default keeps READMEs fast to load.
set -euo pipefail

usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
[[ $# -ge 2 ]] || usage
IN="$1"; OUT="$2"; shift 2
MAX_MB=5; FPS=15; WIDTH=960; MP4=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-mb) MAX_MB="$2"; shift 2 ;;
    --fps) FPS="$2"; shift 2 ;;
    --width) WIDTH="$2"; shift 2 ;;
    --mp4) MP4=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1" >&2; usage ;;
  esac
done
[[ -f "$IN" ]] || { echo "input not found: $IN" >&2; exit 2; }
MAX_BYTES=$(python3 -c "print(int(float('$MAX_MB') * 1024 * 1024))")
size() { wc -c < "$1" | tr -d ' '; }
human() { python3 -c "print(f'{$1/1048576:.2f} MB')"; }
mkdir -p "$(dirname "$OUT")"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

squeeze_gifsicle() {
  command -v gifsicle >/dev/null || return 1
  gifsicle -O3 "$1" -o "$TMP/o3.gif" && cp "$TMP/o3.gif" "$1"
  local lossy
  for lossy in 30 60 90 120; do
    [[ $(size "$1") -le $MAX_BYTES ]] && return 0
    gifsicle -O3 --lossy="$lossy" "$1" -o "$TMP/lossy.gif" && cp "$TMP/lossy.gif" "$1"
    echo "  gifsicle --lossy=$lossy -> $(human "$(size "$1")")"
  done
}

if ! command -v ffmpeg >/dev/null; then
  if [[ "$IN" == *.gif ]] && command -v gifsicle >/dev/null; then
    cp "$IN" "$OUT"
    for colors in 256 128 64 32; do
      [[ $(size "$OUT") -le $MAX_BYTES ]] && break
      gifsicle -O3 --colors "$colors" --resize-fit-width "$WIDTH" "$IN" -o "$OUT"
      echo "  gifsicle colors=$colors -> $(human "$(size "$OUT")")"
    done
    squeeze_gifsicle "$OUT" || true
    echo "-> $OUT ($(human "$(size "$OUT")"))"; exit 0
  fi
  if [[ "$IN" == *.gif ]]; then
    cp "$IN" "$OUT"
    if [[ $(size "$OUT") -le $MAX_BYTES ]]; then
      echo "ffmpeg/gifsicle not installed; GIF already fits ($(human "$(size "$OUT")")) -> $OUT"; exit 0
    fi
  fi
  echo "ffmpeg is required for video input (brew install ffmpeg / apt install ffmpeg)." >&2
  exit 3
fi

# Ladder: fps width colors, best quality first. Entries wider than --width are skipped.
LADDER="$FPS $WIDTH 256
12 960 256
12 800 256
12 800 128
10 720 128
10 640 128
10 640 64
8 560 64
8 480 64
6 480 32"

fits=0
while read -r fps width colors; do
  [[ $width -gt $WIDTH || $fps -gt $FPS ]] && continue
  filters="fps=$fps,scale=$width:-1:flags=lanczos"
  ffmpeg -v error -y -i "$IN" -vf "$filters,palettegen=max_colors=$colors:stats_mode=diff" "$TMP/palette.png"
  ffmpeg -v error -y -i "$IN" -i "$TMP/palette.png" \
    -lavfi "$filters[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" "$TMP/out.gif"
  s=$(size "$TMP/out.gif")
  echo "  fps=$fps width=$width colors=$colors -> $(human "$s")"
  cp "$TMP/out.gif" "$OUT"
  if [[ $s -le $MAX_BYTES ]]; then fits=1; break; fi
done <<< "$LADDER"

if [[ $fits -eq 0 ]]; then
  squeeze_gifsicle "$OUT" || true
  [[ $(size "$OUT") -le $MAX_BYTES ]] && fits=1
fi

if [[ $MP4 -eq 1 ]]; then
  ffmpeg -v error -y -i "$IN" -vf "scale=trunc(min($WIDTH\,iw)/2)*2:-2" -c:v libx264 -pix_fmt yuv420p -movflags +faststart -crf 26 "${OUT%.gif}.mp4"
  echo "-> ${OUT%.gif}.mp4 ($(human "$(size "${OUT%.gif}.mp4")"))"
fi

if [[ $fits -eq 1 ]]; then
  echo "-> $OUT ($(human "$(size "$OUT")"), budget $MAX_MB MB)"
else
  echo "WARNING: $OUT is $(human "$(size "$OUT")"), over the $MAX_MB MB budget. Shorten the recording." >&2
  exit 1
fi
