#!/usr/bin/env python3

import sys
import os
import glob
import re
from collections import defaultdict

def main():
   nfs_path_scope_exp = sys.argv[1]
   files_exp_cfg = glob.glob(f"{nfs_path_scope_exp}/it=*/exp_cfg.csv")
   
   nfs_path_rowlist = sys.argv[2]
   f_targets = os.path.join(nfs_path_scope_exp, "targets.txt")
   f_rowlist_validation_result = os.path.join(nfs_path_rowlist, "rowlist_validation_result_rows.txt")
   f_rowlist_validation_result_bgbk = os.path.join(nfs_path_rowlist, "rowlist_validation_result_bgbk.txt")

   all_cluster_ids = set()

   # process targets.txt
   # get: cluster_id, vaddr, paddr
   targets = dict()
   with open(f_targets) as f:
      for line in f.readlines():
         line_s = line.split(',')
         cid = int(line_s[0])
         vaddr = int(line_s[1],16)
         paddr = int(line_s[2],16)
         targets[vaddr] = cid
         targets[paddr] = cid

   # process exp_cfg
   # get: iteration no.; rowname, virt, phys
   # targets.txt[vaddr] = cluster_id 
   # -> (iteration_no, cluster_id)
   cid2itid = dict()
   rx_it = re.compile('.*(it=[0-9]{5}).*')
   for p in files_exp_cfg:
      iteration_no = re.match(rx_it, p).groups()[0]
      with open(p) as f:
         f.readline()
         _, vaddr, paddr = f.readline().split(',')
      vaddr_int = int(vaddr, 16)
      cid = targets[vaddr_int]
      all_cluster_ids.add(cid)
      cid2itid[cid] = iteration_no
   print(cid2itid)

   # rowlist_validation_result.txt
   # iteration_no, bg, bk
   itid2bgbk = dict()
   with open(f_rowlist_validation_result) as f:
      for line in f.readlines()[1:]:
         line_s = line.split(',')
         itid = line_s[0]
         bg = line_s[1]
         bk = line_s[2]
         itid2bgbk[itid] = f"{bg},{bk}"

   # rowlist_validation_result_bgbk.txt
   # e.g.: it=00019,011,01,35
   itid2bgbk2actcnt = defaultdict(dict)
   with open(f_rowlist_validation_result_bgbk) as f:
      for line in f.readlines():
         if line.startswith('#'):
            continue
         line_s = line.split(',')
         itid = line_s[0]
         bg = line_s[1]
         bk = line_s[2]
         itid2bgbk2actcnt[itid][f"{bg},{bk}"] = int(line_s[3])

   added_bgbk = dict()
   for cid in all_cluster_ids:
      itid = cid2itid[cid]
      if itid not in itid2bgbk:
         print(f"[-] no bgbk information found for iteration {itid}", file = sys.stderr)
         continue
      bgbk = itid2bgbk[itid]

      # ambiguous result -> use the bgbk with the higher ACT count
      if bgbk in added_bgbk:
         itid1 = cid2itid[cid]
         cnt1 = itid2bgbk2actcnt[itid1][bgbk]
         cid2 = int(added_bgbk[bgbk].split(',')[0])
         print(cid2itid)
         itid2 = cid2itid[cid2]
         cnt2 = itid2bgbk2actcnt[itid2][bgbk]
         print(f"ambiguity found: bgbk={bgbk}")
         print(f"cid1={cid} cnt1={cnt1} [new] vs cid2={cid2} cnt2={cnt2} [existing]")
         if cnt2 > cnt1:
             # keep existing entry
            continue
         # we 'del' the existing entry first to have 'cnt1' be ordered 
         # based on its insertion time
         del added_bgbk[bgbk]
      added_bgbk[bgbk] = f"{cid},{bgbk}\n"

   # output
   # cluster_id, bg, bk
   with open("mapping.txt", "w") as out_file:
      out_file.write("#cluster_id,bg,bk\n")
      for v in added_bgbk.values():
         out_file.write(v)


if __name__  == "__main__":
    main()
