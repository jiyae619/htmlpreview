#!/usr/bin/env bash
# Second queue: waits for the running H1 render, then renders the rest with faster settings.
cd "$(dirname "$0")"
for s in N N3 M1 M2 M3 M5 M6 O1; do
  t0=$(date +%s); echo "START $s $(date +%T)" >> queue.log
  /opt/bpyenv/bin/python shots.py $s --res 1280x720 --spp 10 > logs_$s.txt 2>&1
  echo "END $s $(( $(date +%s) - t0 ))s frames=$(ls renders/$s/rgb 2>/dev/null | wc -l)" >> queue.log
done
for s in N N3 O1; do
  t0=$(date +%s); echo "START matte $s $(date +%T)" >> queue.log
  /opt/bpyenv/bin/python shots.py $s --res 1280x720 --matte > logs_matte_$s.txt 2>&1
  echo "END matte $s $(( $(date +%s) - t0 ))s frames=$(ls renders/$s/matte 2>/dev/null | wc -l)" >> queue.log
done
echo "ALLDONE $(date +%T)" >> queue.log
