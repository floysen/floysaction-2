#!/usr/bin/env bash
# Verify the MP4 and build a contact sheet of representative frames.
set -euo pipefail
cd "$(dirname "$0")/.."
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,pix_fmt,nb_frames -show_entries format=duration -of default=nw=1 final-animation.mp4
ffmpeg -v error -i final-animation.mp4 -f null - && echo "decode: OK (no errors)"
ffmpeg -v error -y -i final-animation.mp4 -vf "select='not(mod(n\,60))',scale=216:384,tile=10x3" -frames:v 1 contact-sheet.jpg && echo "contact-sheet.jpg written"
# Black-frame check
ffmpeg -v info -i final-animation.mp4 -vf blackdetect=d=0.05:pix_th=0.08 -an -f null - 2>&1 | grep -i blackdetect || echo "blackdetect: no black segments"
