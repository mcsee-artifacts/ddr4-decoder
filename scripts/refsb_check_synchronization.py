#!/usr/bin/env python3

import os
import pathlib
import glob
from collections import defaultdict

SUMMARY = pathlib.Path("/data/projects/ddr5-scope-data/summary.txt")

try:
    os.remove(SUMMARY)
except:
    pass 

os.chdir(SUMMARY.parent)

keys = ['total_refsb_intervals',
        'refsb_intervals_out_of_sync',
        'commands_in_sync',
        'commands_out_of_sync',
        'unexpected_acts',
        'ignored_commands',
        'num_expected_addrs']

with open(SUMMARY, 'w') as result_file:
    result_file.write("directory," + ','.join(keys) + ",success_ratio\n")

for dir in glob.iglob("**/analyzed/**/*.csv", recursive=True):
    print("[>] processing", dir)
    total = defaultdict(int)
    dir = os.path.dirname(dir)
    for file in os.listdir(dir):
        with open(os.path.join(dir,file)) as f:
            for line in f.readlines():
                prop, val = line.split(',')
                total[prop] += int(val)
    with open(SUMMARY, 'a') as result_file:
        result_file.write(os.path.join(dir).replace("/data/analyzed",","))
        outstr = ','.join([str(total[k]) for k in keys]) + ","
        result_file.write(outstr)
        ratio = (total['total_refsb_intervals']-total['refsb_intervals_out_of_sync'])/total['total_refsb_intervals']
        result_file.write(str(ratio))
        result_file.write("\n")



