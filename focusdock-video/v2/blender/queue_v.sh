#!/usr/bin/env bash
# Vertical (9:16) render queue: every shot at 720x1280, then mattes for the text-behind shots.
cd "$(dirname "$0")"
for s in H1 N N3 M1 M2 M3 M5 M6 O1; do
  t0=$(date +%s); echo "START $s $(date +%T)" >> queue_v.log
  /opt/bpyenv/bin/python shots_v.py $s --res 720x1280 --spp 10 > logs_v_$s.txt 2>&1
  echo "END $s $(( $(date +%s) - t0 ))s frames=$(ls renders_v/$s/rgb 2>/dev/null | wc -l)" >> queue_v.log
done
for s in N N3; do
  t0=$(date +%s); echo "START matte $s $(date +%T)" >> queue_v.log
  /opt/bpyenv/bin/python shots_v.py $s --res 720x1280 --matte > logs_v_matte_$s.txt 2>&1
  echo "END matte $s $(( $(date +%s) - t0 ))s frames=$(ls renders_v/$s/matte 2>/dev/null | wc -l)" >> queue_v.log
done
echo "ALLDONE $(date +%T)" >> queue_v.log
