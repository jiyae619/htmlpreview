#!/usr/bin/env bash
# Composite every frame, then mux with the soundtrack.
# Usage: assemble_v2.sh [out.mp4] [crf]      (VERT=1 for the 9:16 cut)
set -euo pipefail
cd "$(dirname "$0")"
if [ "${VERT:-0}" = 1 ]; then SRC=comp/video_v.mp4; DEF=FocusDock_v2_vertical.mp4; FLAGS="--v 1"
else SRC=comp/video.mp4; DEF=FocusDock_v2.mp4; FLAGS=""; fi
OUT=${1:-$DEF}; CRF=${2:-17}
[ -f "$SRC" ] || node comp/render.mjs $FLAGS --out "$SRC"
ffmpeg -hide_banner -loglevel error -y -i "$SRC" -i soundtrack.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf "$CRF" -pix_fmt yuv420p -profile:v high \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT"
ffmpeg -hide_banner -i "$OUT" 2>&1 | grep -E "Duration|Stream" || true
