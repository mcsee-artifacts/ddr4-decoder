#!/usr/bin/env python3

import glob
import subprocess
import os
import sys

from collections import defaultdict

NUM='*'

# parse information about generated targets
print("[+] parsing data of generated targets..")
file_targets = "/mnt/scope-data/20230110_035437_ee-tik-cn115_DIMM=522_verify_dram_functions/fn_validation.txt"
paddr2all = defaultdict(dict)
with open(file_targets) as f:
    for line in f.readlines():
        raw = line.split(',')
        cluster = int(raw[0])
        bg_bk = raw[1]
        vaddr = int(raw[2],16)
        paddr = int(raw[3],16)
        paddr2all[paddr] = {
            'cluster': cluster,
            'bg_bk': f"{bg_bk}",
            'vaddr': vaddr}
        #print('paddr=', hex(paddr), 'bk=', bk, 'bg=', bg, 'vaddr=', hex(vaddr))
    
# parse information about accessed address during experiment
print("[+] parsing exp_cfg.csv files..")
it2access = defaultdict(dict)
for f_ecfg in glob.iglob(f"/mnt/scope-data/20230110_035437_ee-tik-cn115_DIMM=522_verify_dram_functions/it={NUM}/exp_cfg.csv"):
#for f_ecfg in glob.glob("/mnt/scope-data/20230110_035437_ee-tik-cn115_DIMM=522_verify_dram_functions/it=*/exp_cfg.csv"):
    print(f"    {f_ecfg}")
    it = int(f_ecfg.split('/')[-2].split('=')[1])
    with open(f_ecfg) as f:
        data = f.readlines()[1].split(',')
        vaddr = int(data[1],16)
        paddr = int(data[2],16)
        it2access[it] = {
                'vaddr': vaddr,
                'paddr': paddr }
        #print('it=', it, 'paddr=', hex(paddr))

# parse decoded signals
checked_clusters = set()
num_observable = 0
bgbk2cluster = dict()
print("[+] parsing decoded command data..")
for f_decoded in glob.iglob(f"/mnt/scope-data/20230110_035437_ee-tik-cn115_DIMM=522_verify_dram_functions/data/decoded/it={NUM}/trace--00000.csv"):
#for f_decoded in glob.glob("/mnt/scope-data/20230110_035437_ee-tik-cn115_DIMM=522_verify_dram_functions/data/decoded/it=*/trace--00000.csv"):
    print(f"    {f_decoded}")
    it = int(f_decoded.split('/')[-2].split('=')[1])
    cmd = f"grep 'act' {f_decoded} | cut -d, -f3-5 | sort -nr | uniq -c | sort -t, -k1,2 -n | tail -n 5"
    proc = subprocess.run(cmd, shell=True, check=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    #print(proc.stdout)
    any_match = False
    for line in proc.stdout.split('\n'):
        #print("line:", line)
        if len(line) == 0:
            continue
        raw = line.strip().replace(' ', ',').split(',')
        count = int(raw[0])
        bg = raw[1]
        bk = raw[2]
        row = int(raw[3], 2)
        key = f"{bg}{bk}"
        if count > 100:
            num_observable += 1 
            any_match = True
            paddr = it2access[it]['paddr']
            expected = paddr2all[paddr]
            exp_bg_bk = paddr2all[paddr]['bg_bk']
            print(hex(paddr), f"{bg}{bk}", file=sys.stderr, sep=',') 
            if key in bgbk2cluster and bgbk2cluster[key] != paddr2all[paddr]['bg_bk']:
                #print(f"[ERROR] it={it}, exp_bg={exp_bg} vs bg={bg}, exp_bk={exp_bk} vs bk={bk}")
                print(f"[ERROR] it={it}, exp_bg_bk={exp_bg_bk} vs bg_bk={bg}{bk}") 
            bgbk2cluster[key] = paddr2all[paddr]['bg_bk']
           # if bg != exp_bg or bk != exp_bk:
           #     print(f"[ERROR] it={it}, exp_bg={exp_bg} vs bg={bg}, exp_bk={exp_bk} vs bk={bk}")
           #     print(raw)
           # else:
           #     print(f"[ OK  ] it={it}") 
    #if not any_match:
    #    print(f"[SKIP ] it={it}")

print(bgbk2cluster)
print(num_observable)
