#!/bin/bash
# usage: render/batch.sh prefix "shot res samples aspect laps" ...
B=/Applications/Blender.app/Contents/MacOS/Blender
prefix=$1; shift
for spec in "$@"; do
  set -- $spec
  $B -b -P render/scene.py -- --shot $1 --res $2 --samples $3 --aspect $4 --laps $5 --out out/renders/${prefix}_$1.png > out/renders/log_$1.txt 2>&1
  grep -E "Traceback|Error|rror:" out/renders/log_$1.txt | head -5
  echo "finished $1"
done
