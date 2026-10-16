#!/usr/bin/env bash
# One command to build, render and encode the whole video.
#
#   bash render.sh                 # full quality 1080x1920 -> output/pool_final.mp4
#   bash render.sh --preview       # fast half-resolution check -> output/pool_preview.mp4
#   bash render.sh --quality medium|full|cinematic
#   bash render.sh --engine cycles # force Cycles (GPU if available, else CPU)
#   bash render.sh --device cpu    # force CPU for Cycles
#   bash render.sh --rebuild       # rebuild the 3D scene even if sources did not change
#   bash render.sh --encode-only   # skip rendering, only mix audio + encode existing frames
#   bash render.sh --clean         # delete rendered frames for the chosen quality first
#
# Interrupted?  Just run the same command again: finished frames are kept and
# rendering resumes at the first missing frame.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

QUALITY=full ENGINE=auto DEVICE=auto REBUILD=0 ENCODE_ONLY=0 CLEAN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --preview) QUALITY=preview ;;
    --quality) QUALITY="$2"; shift ;;
    --engine) ENGINE="$2"; shift ;;
    --device) DEVICE="$2"; shift ;;
    --rebuild) REBUILD=1 ;;
    --encode-only) ENCODE_ONLY=1 ;;
    --clean) CLEAN=1 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (see bash render.sh --help)"; exit 1 ;;
  esac
  shift
done

step() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m[render] ERROR:\033[0m %s\n' "$*"; exit 1; }
START=$(date +%s)

step "1/6  System check"
echo "OS: $(uname -s)   CPU threads: $(getconf _NPROCESSORS_ONLN 2>/dev/null || echo "${NUMBER_OF_PROCESSORS:-?}")"
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)"
elif command -v wmic >/dev/null 2>&1; then
  echo "GPU: $(wmic path win32_VideoController get name 2>/dev/null | sed -n 2p | tr -d '\r')"
fi
FREE_KB=$(df -Pk . | awk 'NR==2 {print $4}')
NEED_GB=9; [ "$QUALITY" = preview ] && NEED_GB=3
echo "Free disk space here: $((FREE_KB / 1048576)) GB (need about $NEED_GB GB for $QUALITY frames)"
[ "$FREE_KB" -gt $((NEED_GB * 1048576)) ] || echo "WARNING: low disk space - rendering may fail when the disk fills up"
grep -q "\"$QUALITY\"" project-config.json || die "unknown quality '$QUALITY' (see project-config.json)"

step "2/6  Dependencies"
bash install.sh
# shellcheck disable=SC1091
source tools/env.sh
export FFMPEG FFPROBE

run_blender() {  # quiet Blender run that fails loudly
  "$BLENDER" -b --factory-startup --python-exit-code 1 "$@"
}

FRAMES="output/frames_$QUALITY"
[ "$CLEAN" = 1 ] && { echo "removing $FRAMES"; rm -rf "$FRAMES"; }

if [ "$ENCODE_ONLY" = 0 ]; then
  step "3/6  Building the 3D scene"
  NEED=1
  if [ "$REBUILD" = 0 ] && [ -f build/pool.blend ]; then
    NEED=0
    for f in scenes/*.py scripts/shotplan.py data/timeline.json project-config.json; do
      [ "$f" -nt build/pool.blend ] && NEED=1
    done
  fi
  if [ "$NEED" = 1 ]; then
    run_blender --python scenes/build_scene.py
    # the scene changed: frames rendered from the old scene are stale
    if [ -d "$FRAMES" ] && ls "$FRAMES"/frame_*.png >/dev/null 2>&1; then
      echo "scene changed -> clearing old frames in $FRAMES"
      rm -rf "$FRAMES"
    fi
  else
    echo "build/pool.blend is up to date"
  fi

  step "4/6  Rendering frames ($QUALITY) - this is the long part"
  echo "Progress and ETA are printed per frame. Safe to stop with Ctrl+C and resume later."
  if ! "$BLENDER" -b build/pool.blend --python-exit-code 1 --python scenes/render_frames.py -- \
        --quality "$QUALITY" --engine "$ENGINE" --device "$DEVICE" --out "$FRAMES"; then
    if [ "$ENGINE" != cycles ]; then
      echo "EEVEE render failed (no compatible GPU/OpenGL?) - falling back to Cycles"
      "$BLENDER" -b build/pool.blend --python-exit-code 1 --python scenes/render_frames.py -- \
        --quality "$QUALITY" --engine cycles --device "$DEVICE" --out "$FRAMES" \
        || die "rendering failed - see README troubleshooting"
    else
      die "rendering failed - see README troubleshooting"
    fi
  fi
fi

step "5/6  Mixing voiceover + sound effects"
run_blender --python scripts/mix_audio.py

step "6/6  Encoding MP4 with Arabic captions + verification"
run_blender --python scripts/assemble.py -- --quality "$QUALITY" --frames "$FRAMES"

END=$(date +%s)
OUT=output/pool_final.mp4; [ "$QUALITY" != full ] && OUT="output/pool_$QUALITY.mp4"
printf '\n\033[1;32mDone in %d min.  Video: %s\033[0m\n' $(((END - START) / 60)) "$ROOT/$OUT"
