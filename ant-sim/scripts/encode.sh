#!/usr/bin/env bash
# Assemble frames into an H.264 MP4 (yuv420p, 30 fps). Mux narration if voiceover.(wav|mp3|m4a) exists.
set -euo pipefail
cd "$(dirname "$0")/.."
AUDIO=$(ls voiceover.{wav,mp3,m4a} 2>/dev/null | head -1 || true)
if [ -n "$AUDIO" ]; then
  ffmpeg -y -framerate 30 -i frames/f_%05d.jpg -i "$AUDIO" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart final-animation.mp4
else
  ffmpeg -y -framerate 30 -i frames/f_%05d.jpg -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart final-animation.mp4
fi
