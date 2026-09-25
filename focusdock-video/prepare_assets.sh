#!/usr/bin/env bash
# Pulls the real-footage assets the scenes use out of the original video.
# Usage: prepare_assets.sh <original.mp4>   (writes into scene/assets/)
set -euo pipefail
cd "$(dirname "$0")"; SRC=$1; A=scene/assets
mkdir -p $A/clip_timer $A/clip_button
IN=$(python3 -c "import json;print(json.load(open('timeline.json'))['demoIn'])")
OUT=$(python3 -c "import json;print(json.load(open('timeline.json'))['demoOut'])")
ffmpeg -loglevel error -y -i "$SRC" -vf "select=eq(n\,$IN)"  -vframes 1 -q:v 2 $A/demo_first.jpg   # intro ends on this exact frame
ffmpeg -loglevel error -y -i "$SRC" -vf "select=eq(n\,$OUT)" -vframes 1 -q:v 2 $A/demo_last.jpg    # outro starts on this exact frame
ffmpeg -loglevel error -y -ss 48.5 -i "$SRC" -t 6   -vf scale=800:-2 -q:v 3 $A/clip_timer/%03d.jpg
ffmpeg -loglevel error -y -ss 41.2 -i "$SRC" -t 3.5 -vf scale=800:-2 -q:v 3 $A/clip_button/%03d.jpg
