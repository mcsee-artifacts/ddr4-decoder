import os
from pathlib import Path
import subprocess
import time

from multiprocessing import Pool
from stages.s2_decode import get_output_directory as decoded__get_output_directory
from util.decoded_cmd import DecodedCommand
from util.dram_command import E_DDR5_DRAM_CMD
from util.py_helper import checkenv, printf
from collections import defaultdict


def get_output_directory(experiment_name: str):
   return os.path.join(os.getenv('DATA_DIR'), 'analyzed', experiment_name)

def __analyze_single_csv(experimentname: str, csv_path: str, pool: Pool) -> dict:
   # Compute the output path and create the parent dir if necessary
   basename = os.path.basename(csv_path)
   outpath = os.path.join(os.getenv('DATA_DIR'), 'analyzed', experimentname, \
      '.'.join(os.path.basename(csv_path).split('.')[:-1]) + '.csv')
   
    # Check existence of the output path
   if os.path.exists(outpath):
      printf(f"skipping file {basename} as it has already been converted before")
      exit(0);
   Path(os.path.dirname(outpath)).mkdir(parents=True, exist_ok=True)

   exp_acts_within_refsb = list()

   # figure out the <bg,bk,rows> we want to check for, i.e., the ones that have
   # been accessed most frequently
   dir = decoded__get_output_directory(experimentname)
   cmd = f'cat {dir}/*.csv | grep "act" | cut -d, -f3-5 | sort -nr | uniq -c | sort -r -t, -k1 -n | tr -s "  " " " | sed "s/ /,/g" | sed "s/^,//g"'
   out = subprocess.check_output(cmd, shell=True, universal_newlines=True)

   last_key = None
   last_count = None
   # this assumes that cmd has ordered the top most frequently accessed DRAM
   # addresses in DESCENDING order
   for ln in out.splitlines():
      if len(ln) == 0:
         continue
      num_acts, bg, bk, row = ln.split(',')
      key = f"{bg},{bk}"
      if last_key is None:
         last_key = key
         last_count = num_acts
      # we demand that all addresses in our experiment have been indeed accessed at least 90% of all time
      elif key != last_key or int(num_acts) < int(int(last_count)*0.30):
         break
      exp_acts_within_refsb.append(
         DecodedCommand(
            None, 
            E_DDR5_DRAM_CMD.act,
            { 'bg': bg, 'bk': bk, 'row': row}, None))

   # build fast lookup dictionary
   exp_addrs = defaultdict(int)
   for k in exp_acts_within_refsb:
      exp_addrs[f"{k.bg},{k.bk},{k.row}"]

   total_refsb_intervals = 0
   total_refsb_intervals_out_of_sync = 0

   total_commands_out_of_sync = 0
   total_commands_in_sync = 0

   unexpected_acts = []
   ignored_commands = 0

   target_bg, target_bk = last_key.split(',')

   line_cnt = 0
   with open(csv_path, "r") as file:
      while True:
         line = file.readline()
         # stop if we finished reading all lines
         if not line:
            break
         # skip the header row
         elif line_cnt == 0:
            line_cnt += 1
            continue
         
         _, cmd, bg, bk, row, _ = line.split(',')

         # we only consider those REFsb commands where the bank matches the 
         # bank where our workload is running on
         if cmd == E_DDR5_DRAM_CMD.ref_sb.name and target_bk == bk:
            total_refsb_intervals += 1

            # check if we found all addresses
            NUM_SYNC_ROWS = 2
            v_out_of_sync = max(0,sum([1 if x == 0 else 0 for x in exp_addrs.values()])-NUM_SYNC_ROWS)
            total_commands_out_of_sync += v_out_of_sync
            total_refsb_intervals_out_of_sync += (v_out_of_sync > 0)
            
            v_in_sync = sum([1 if x > 0 else 0 for x in exp_addrs.values()])
            total_commands_in_sync += v_in_sync

            # reset statistics
            for i in exp_addrs.keys():
               exp_addrs[i] = 0

         elif cmd == E_DDR5_DRAM_CMD.act.name:
            key = f"{bg},{bk},{row}"
            if key in exp_addrs:
               exp_addrs[key] += 1
            else:
               unexpected_acts.append(line.replace("\n",""))
         
         else:
            ignored_commands += 1

         line_cnt += 1
   
   return {
     'total_refsb_intervals': total_refsb_intervals,
     'refsb_intervals_out_of_sync': total_refsb_intervals_out_of_sync,
     'commands_in_sync': total_commands_in_sync,
     'commands_out_of_sync': total_commands_out_of_sync,
     'unexpected_acts': len(unexpected_acts),
     'ignored_commands': ignored_commands,
     'num_expected_addrs': len(exp_addrs)
   }

def analyze_all(exp_name: str, num_workers: int) -> None:
   t_start = time.time()

   checkenv('DATA_DIR')

   decoded_path = decoded__get_output_directory(exp_name)
   csv_paths = list(map(lambda b: os.path.join(decoded_path, b), os.listdir(decoded_path)))

   assert (exp_name.count('/') == 0 and exp_name.count("\\") == 0), \
      "exp_name is supposed to be a folder name, not a path!"

   # Run in parallel
   with Pool(num_workers) as p:
      for csv_path in csv_paths:
         analysis_result = __analyze_single_csv(exp_name, csv_path, p)
         # write analysis to file
         outpath = os.path.join(get_output_directory(exp_name), os.path.basename(csv_path))
         with open(outpath, "w") as f:
            for prop, value in analysis_result.items():
               if type(value) == list:
                  for v in value:
                     v = v.replace('\n', '')
                     f.write(f"{prop},{v}\n")
               else:
                  f.write(f"{prop},{value}\n")
   t_end = time.time()

   printf(f"analysis done for all {len(csv_paths)} file(s) in {t_end - t_start:.3f} seconds.")
