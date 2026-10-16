#!/usr/bin/env bash
# One command to render the whole video (2D engine, no Blender).
#
#   bash render.sh              # full 1080x1920 -> output/toilet_final.mp4
#   bash render.sh --preview    # half-resolution quick check -> output/toilet_preview.mp4
#   bash render.sh --clean      # throw away previously rendered chunks first
#   bash render.sh --workers 4  # number of parallel render processes (default: CPU threads - 1)
#   bash render.sh --realign    # re-run the speech-recognition caption timing
#   bash render.sh --no-align   # skip it and keep the current caption timing
#
# Interrupted with Ctrl+C?  Run the same command again: finished chunks are kept.
set -euo pipefail
cd "$(dirname "$0")"

QUALITY=full CLEAN=0 EXTRA=() ALIGN=auto
while [ $# -gt 0 ]; do
  case "$1" in
    --preview) QUALITY=preview ;;
    --quality) QUALITY="$2"; shift ;;
    --clean) CLEAN=1 ;;
    --realign) ALIGN=force ;;
    --no-align) ALIGN=off ;;
    --workers) EXTRA+=(--workers "$2"); shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (see bash render.sh --help)"; exit 1 ;;
  esac
  shift
done

printf '\n\033[1;35m==> Dependencies\033[0m\n'
bash install.sh
# shellcheck disable=SC1091
source tools/env.sh
export FFMPEG FFPROBE PYTHONIOENCODING=utf-8

# exact caption/word timing from the voiceover (speech recognition, runs once)
if [ "$ALIGN" != off ]; then
  if [ "$ALIGN" = force ] || ! grep -q '"alignment": "whisper' data/timeline.json; then
    printf '\n\033[1;35m==> Word timing from the voiceover (one time)\033[0m\n'
    if "$PY" -c "import faster_whisper" >/dev/null 2>&1 || "$UV" pip install --python "$PY" -r requirements-align.txt; then
      "$PY" scripts/word_align.py || echo "WARNING: word alignment failed - using the previous caption timing"
    else
      echo "WARNING: could not install faster-whisper - using the previous caption timing"
    fi
  fi
fi

# rendered chunks are only valid for the current code/timing: clear them when sources change
STAMP="build/chunks_$QUALITY/.stamp"
if [ "$CLEAN" = 1 ]; then rm -rf "build/chunks_$QUALITY"; fi
if [ -f "$STAMP" ]; then
  for f in engine/*.py scripts/shotplan.py data/*.json project-config.json; do
    if [ "$f" -nt "$STAMP" ]; then echo "sources changed since the last render -> re-rendering"; rm -rf "build/chunks_$QUALITY"; break; fi
  done
fi
mkdir -p "build/chunks_$QUALITY"; [ -f "$STAMP" ] || touch "$STAMP"

printf '\n\033[1;35m==> Rendering (%s)\033[0m\n' "$QUALITY"
"$PY" engine/render.py --quality "$QUALITY" ${EXTRA[@]+"${EXTRA[@]}"}

OUT=output/toilet_final.mp4; [ "$QUALITY" != full ] && OUT="output/toilet_$QUALITY.mp4"
printf '\n\033[1;32mDone. Video: %s\033[0m\n' "$(pwd)/$OUT"
