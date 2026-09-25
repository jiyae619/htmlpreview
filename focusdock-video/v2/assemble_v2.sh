#!/usr/bin/env bash
# Composite every frame, then mux with the soundtrack.
# Usage: assemble_v2.sh [out.mp4] [crf]
set -euo pipefail
cd "$(dirname "$0")"
OUT=${1:-FocusDock_v2.mp4}; CRF=${2:-17}
[ -f comp/video.mp4 ] || node comp/render.mjs --out comp/video.mp4
ffmpeg -hide_banner -loglevel error -y -i comp/video.mp4 -i soundtrack.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf "$CRF" -pix_fmt yuv420p -profile:v high \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT"
ffmpeg -hide_banner -i "$OUT" 2>&1 | grep -E "Duration|Stream" || true
