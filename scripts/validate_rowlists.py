#!/usr/bin/env python3

import os
import glob
import sys
import re
import statistics

from collections import OrderedDict, defaultdict

def main():
    path_decoded_dir = os.sys.argv[1]
    print("path_decoded_dir =", path_decoded_dir)
    
    num_expected_rows = int(os.sys.argv[2])
    print("num_expected_rows =", num_expected_rows)

    f_result =  open("rowlist_validation_result.txt", "w")
    f_details = open("rowlist_validation_result_details.txt", "w")
    f_rows =    open("rowlist_validation_result_rows.txt", "w")
    f_bgbk =    open("rowlist_validation_result_bgbk.txt", "w")
    f_rows.write("#filename,bg,bk,min_row,max_row,num_missing_rows,num_consecutive_rows\n")
    
    rx_it = re.compile('.*(it=[0-9]{5}).*')

    # counts for each iteration how often each <bg,bk,row> has been activated
    itid2bgbkrow = defaultdict(OrderedDict)
    # counts for each iteration how often each <bg,bk> has been activated
    itid2bgbk = defaultdict(OrderedDict)

    for csv in glob.glob(os.path.join(path_decoded_dir, "**/*.csv")):
        iteration_no = re.match(rx_it, csv).groups()[0]
        d = itid2bgbkrow[iteration_no]
        e = itid2bgbk[iteration_no]
        with open(csv) as f:
            for l in f.readlines():
                if 'act' in l:
                    key = ','.join(l.split(",")[2:5])
                    if key in d:
                        d[key] += 1
                    else:
                        d[key] = 1

                    key = ','.join(l.split(",")[2:4])
                    if key in e:
                        e[key] += 1
                    else:
                        e[key] = 1
    
    for itid, bgbk_dict in itid2bgbk.items():
        f_bgbk.write(f"### {itid}\n") 
        for bgbk, cnt in bgbk_dict.items():
            f_bgbk.write(f"{itid},{bgbk},{cnt}\n")

    invalid_clusters = 0
    for filename in sorted(itid2bgbkrow.keys()):
        d = itid2bgbkrow[filename]
        e = itid2bgbk[filename]

        f_details.write(f"### {filename}\n")
        print(f"### {filename}\n")

        if (len(d.items()) == 0):
            continue

        # find the <bg,bk> with the highest activation count
        top = list(e.items())[0]
        top_bgbk = ','.join(top[0].split(',')[0:2])

        # compute the threshold based on this bank
        th = statistics.median([v for k,v in d.items() if top_bgbk in k])

        # go over rows of all <bk,bg> to see which rows have been activated more than th
        top_rows = list()
        count = 0
        for k,v in d.items():
            if top_bgbk in k:
                print(k)
                top_rows.append(int(k.split(',')[2],2))
            if int(v) >= th: 
                count += 1
            f_details.write(f"{filename},{k},{v}\n")

        # top = list(d.items())[0]
        # top_bgbk = ','.join(top[0].split(',')[0:2])
        # print("top_bgbk=", top_bgbk)
        # top_rows = list()

        # th = statistics.median([v for k,v in d.items() if top_bgbk in k])
        # #th = int(top[1])*0.6
        # count = 0
        # for k,v in d.items():
        #     if top_bgbk in k:
        #         print(k)
        #         top_rows.append(int(k.split(',')[2],2))
        #     if int(v) >= th: 
        #         count += 1
        #     f_details.write(f"{filename},{k},{v}\n")

        f_result.write(f"{filename},")
        if count >= num_expected_rows:
            f_result.write(f"success ({count})\n")
        else:
            f_result.write(f"failure ({count})\n")
            invalid_clusters += 1
        
        top_rows.sort()

        num_missing_rows = 0
        num_consecutive_rows = 0
        for rid_last, rid in zip(top_rows, top_rows[1:]):
            if (rid-rid_last > 1):
                num_missing_rows += rid-rid_last-1
            else:
                num_consecutive_rows += 1
        f_rows.write(f"{filename},{top_bgbk},{top_rows[0]},{top_rows[-1]},{num_missing_rows},{num_consecutive_rows}\n")
        
        
    f_result.close()
    f_details.close()
    f_rows.close()
    f_bgbk.close()

    sys.exit(0)

if __name__  == "__main__":
    main()
