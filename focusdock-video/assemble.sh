#!/usr/bin/env bash
# Joins: new intro + original demo frames (unchanged) + new outro, with the new soundtrack.
# Usage: assemble.sh <soundtrack.wav> <out.mp4>
set -euo pipefail
cd "$(dirname "$0")"
AUDIO=${1:-soundtrack.wav}; OUT=${2:-FocusDock_remake.mp4}
IN=$(python3 -c "import json;print(json.load(open('timeline.json'))['demoIn'])")
OUTF=$(python3 -c "import json;print(json.load(open('timeline.json'))['demoOut'])")
# rendered scenes were encoded from sRGB with the BT.601 matrix; convert them to BT.709 like the camera footage
TO709="scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,format=yuv420p"
ffmpeg -hide_banner -loglevel error -y \
  -i intro.mp4 -i src/original.mp4 -i outro.mp4 -i "$AUDIO" \
  -filter_complex "[0:v]setpts=PTS-STARTPTS,${TO709}[v0];\
[1:v]trim=start_frame=${IN}:end_frame=$((OUTF + 1)),setpts=PTS-STARTPTS,format=yuv420p[v1];\
[2:v]setpts=PTS-STARTPTS,${TO709}[v2];\
[v0][v1][v2]concat=n=3:v=1:a=0,fps=30[v]" \
  -map "[v]" -map 3:a -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT"
ffmpeg -hide_banner -i "$OUT" 2>&1 | grep -E "Duration|Stream" || true
