#!/usr/bin/env bash
# Post-render QA: ffprobe stream info, black-frame detection, and a contact sheet (1 frame / second).
set -euo pipefail
f=${1:-final-animation.mp4}
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_frames:format=duration -of default=nw=1 "$f"
echo "--- blackdetect (empty = no black frames) ---"
ffmpeg -v info -i "$f" -vf blackdetect=d=0.03:pix_th=0.06 -an -f null - 2>&1 | grep -i blackdetect || true
mkdir -p out
ffmpeg -y -v error -i "$f" -vf "fps=1,scale=270:480,tile=8x4" -frames:v 1 out/contact-sheet.jpg
echo "contact sheet -> out/contact-sheet.jpg"
