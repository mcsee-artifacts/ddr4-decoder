#!/usr/bin/env python3

from glob import glob
import sys
import subprocess

watch_dir = sys.argv[1]
print(f"[>] watching dir: {watch_dir}")

decoded_dirs = set()

while True:
   for f in glob(f"/mnt/scope-data/{watch_dir}/it=*"):
      # folder has been decoded before
      if f in decoded_dirs:
         continue
      # decode folder
      rc = subprocess.call(f"./decode_parallel.sh {f}", shell=True)
      decoded_dirs.add(f)
   sleep(30)

