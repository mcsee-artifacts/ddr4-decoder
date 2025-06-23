#!/usr/bin/env python3
"""
This script parses the decoded data for an entire experiment (i.e., multiple
iterations), and counts the activations to the differnt <bg,bk> tuples for each
iteration.

The analyzed data is written to a file 'bank_act_table.csv' in the experiment's
'data/' directory.

It also outputs a table with this information, as well as the most accessed
<bg,bk> (if there is a dominant one), to STDOUT.
"""

import csv
from pathlib import Path
import sys


NUM_BANKS = (2 ** 3) * (2 ** 2)


def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def get_bank_act_counts_from_decoded_csv(csv_file: Path):
    bank_acts = [0] * NUM_BANKS

    with csv_file.open("r") as f:
        reader = csv.DictReader(f, delimiter=",")
        
        for row in reader:
            if row["cmd"] != "act":
                continue
            bank_group = int(row["bg"], 2)
            bank = int(row["bk"], 2)
            full_bank = bank_group << 2 | bank
            bank_acts[full_bank] += 1

    return bank_acts


def main(exp_dir):
    decoded_dir = exp_dir / "data" / "decoded"
    dirs = [f for f in decoded_dir.iterdir() if f.is_dir()]
    dirs.sort(key=lambda x: x.name)
    out_csv = exp_dir / "data" / "bank_act_table.csv"

    # Read all input files.
    iters = []
    for iter_dir in dirs:
        log(f"Processing iteration: '{iter_dir.name}'")
        bank_acts = [0] * NUM_BANKS
        for csv_file in iter_dir.glob("*.csv"):
            log(f"  {csv_file.name}")
            file_acts = get_bank_act_counts_from_decoded_csv(csv_file)
            for idx, cnt in enumerate(file_acts):
                bank_acts[idx] += cnt
        iters.append((iter_dir.name, bank_acts))

    # Write output to CSV file.
    log(f"Writing output to '{out_csv}'...")
    with out_csv.open("w+") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_NONE)
        # write header
        banks = [f"{bank:05b}" for bank in range(NUM_BANKS)]
        writer.writerow(["iter"] + banks)
        
        for iter_name, acts in iters:
            writer.writerow([iter_name] + acts)

    # Writing table output to STDOUT.
    log("Writing table output to STDOUT...")
    print("iter     ", "sum acts", *[f"{bank:05b}" for bank in range(NUM_BANKS)], "percent", "dominant", sep="|")

    all_banks = set()
    num_with_bank = 0

    for iter_name, acts in iters:
        sum_acts = sum(acts)
        max_acts = max(acts)
        percentage = 100.0 * max_acts / max(1, sum_acts)

        max_bank = max(list(range(NUM_BANKS)), key=lambda x: acts[x])
        has_max_bank = percentage > 30
        if has_max_bank:
            all_banks.add(max_bank)
            num_with_bank += 1
        
        dominant_str = f"{max_bank:05b}" if percentage > 30 else "-----"
        print(f"{iter_name:9}", f"{sum_acts:8}", *[f"{act:5}" for act in acts], f" {percentage:5.1f}%", " "  + dominant_str, sep="|")

    print(f"{num_with_bank} iterations with dominant bank, {len(all_banks)} distinct banks indexed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} [experiment directory]", file=sys.stderr)
        sys.exit(1)
    exp_dir = Path(sys.argv[1])

    main(exp_dir)
