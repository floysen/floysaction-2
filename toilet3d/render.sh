#!/usr/bin/env bash
# One command: realistic 3D render of the toilet video.
#   bash render.sh              -> output/toilet_final.mp4   (1080x1920)
#   bash render.sh --preview    -> output/toilet_preview.mp4 (half resolution, fast check)
#   bash render.sh --clean      re-render from scratch
#   bash render.sh --realign    re-run the speech-based word timing
#   bash render.sh --no-align   skip the word timing step
# Interrupted? Run the same command again - finished chunks are kept.
set -euo pipefail
cd "$(dirname "$0")"
QUALITY=full CLEAN=0 ALIGN=auto
while [ $# -gt 0 ]; do
  case "$1" in
    --preview) QUALITY=preview ;; --clean) CLEAN=1 ;; --realign) ALIGN=force ;; --no-align) ALIGN=off ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac; shift
done
step() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
step "Dependencies"; bash install.sh; source tools/env.sh; export FFMPEG FFPROBE BROWSER PYTHONIOENCODING=utf-8
if [ "$ALIGN" != off ] && { [ "$ALIGN" = force ] || ! grep -q '"alignment": "whisper' data/timeline.json; }; then
  step "Word timing from the voiceover (one time)"
  if "$PY" -c "import faster_whisper" >/dev/null 2>&1 || "$UV" pip install --python "$PY" -r requirements-align.txt; then
    "$PY" scripts/word_align.py || echo "WARNING: word alignment failed - keeping the previous timing"
  else echo "WARNING: could not install faster-whisper - keeping the previous timing"; fi
fi
"$PY" scripts/shotplan.py --export
CH="build/chunks_$QUALITY"; STAMP="$CH/.stamp"
[ "$CLEAN" = 1 ] && rm -rf "$CH"
if [ -f "$STAMP" ]; then for f in web/scenes/*.js web/lib/*.js web/index.html data/events.json; do
  if [ "$f" -nt "$STAMP" ]; then echo "scene or timing changed -> re-rendering"; rm -rf "$CH"; break; fi; done; fi
mkdir -p "$CH"; [ -f "$STAMP" ] || touch "$STAMP"
SCALE=1; [ "$QUALITY" = preview ] && SCALE=0.5
step "Rendering 3D frames ($QUALITY) through the GPU"
"$NODE" tools/render.mjs --scene toilet --scale "$SCALE" --quality "$QUALITY" --out "$CH"
step "Audio: voiceover + sound effects"; "$PY" scripts/mix_audio.py
step "Encoding + checks"; "$PY" scripts/assemble.py --quality "$QUALITY"
OUT=output/toilet_final.mp4; [ "$QUALITY" = preview ] && OUT=output/toilet_preview.mp4
printf '\n\033[1;32mDone: %s\033[0m\n' "$(pwd)/$OUT"
