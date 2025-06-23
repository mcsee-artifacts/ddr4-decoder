#!/usr/bin/env python3
from collections import Counter
import csv
from dataclasses import dataclass
import multiprocessing
import os
from pathlib import Path
import sys
from typing import Optional


"""
Checks the distribution of all bg,bk,row bits in ACTs.
"""

BG_BITS = 3
BK_BITS = 2
ROW_BITS = 16


def bit(idx: int):
    return 1 << idx


def bits_set(value: int):
    return [idx for idx in range(63, -1, -1) if (value & bit(idx)) > 0]


def addr_bits_to_str(addr_bits: tuple) -> str:
    return f"bg={addr_bits[0]:03b} bk={addr_bits[1]:02b} row={addr_bits[2]:016b}"


# Returns a list of all ACT commands, as tuples of (bg, bk, row).
def get_acts_from_trace(trace_file: Path) -> list[tuple[str, str, str]]:
    with trace_file.open("r") as f:
        reader = csv.DictReader(f)

        acts = []
        for line in reader:
            if line["cmd"] != "act":
                continue
            bg = line["bg"]
            bk = line["bk"]
            row = line["row"]
            acts.append((bg, bk, row))
    return acts


def get_counts_for_acts(acts: list[tuple[str, str, str]]):
    # {bg,bk,row}_counts[bit_idx][{0,1}]: count of {0,1} in bit position
    bg_counts = [[0, 0] for _ in range(BG_BITS)]
    bk_counts = [[0, 0] for _ in range(BK_BITS)]
    row_counts = [[0, 0] for _ in range(ROW_BITS)]
    for bg, bk, row in acts:
        for bit_idx in range(len(bg)):
            bit_char = bg[len(bg) - bit_idx - 1]
            if bit_char != "X":
                bit_value = int(bit_char)
                bg_counts[bit_idx][bit_value] += 1
        for bit_idx in range(len(bk)):
            bit_char = bk[len(bk) - bit_idx - 1]
            if bit_char != "X":
                bit_value = int(bit_char)
                bk_counts[bit_idx][bit_value] += 1
        for bit_idx in range(len(row)):
            bit_char = row[len(row) - bit_idx - 1]
            if bit_char != "X":
                bit_value = int(bit_char)
                row_counts[bit_idx][bit_value] += 1
    return bg_counts, bk_counts, row_counts


def print_counts(bg_counts, bk_counts, row_counts):
    print("NOTE: Counts indicate how often the bit was asserted (i.e., 1).")
    for idx, counts in enumerate(bg_counts):
        total_bits = counts[0] + counts[1]
        if total_bits == 0:
            continue
        percent = 100 * counts[1] / total_bits
        id = f"bg{idx}"
        print(f"  {id:<5s} {counts[1]:5d} / {total_bits:5d}    {percent:6.2f} %")
    for idx, counts in enumerate(bk_counts):
        total_bits = counts[0] + counts[1]
        if total_bits == 0:
            continue
        percent = 100 * counts[1] / total_bits
        id = f"bk{idx}"
        print(f"  {id:<5s} {counts[1]:5d} / {total_bits:5d}    {percent:6.2f} %")
    for idx, counts in enumerate(row_counts):
        total_bits = counts[0] + counts[1]
        if total_bits == 0:
            continue
        percent = 100 * counts[1] / total_bits
        id = f"row{idx}"
        print(f"  {id:<5s} {counts[1]:5d} / {total_bits:5d}    {percent:6.2f} %")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: test_bit_distributions.py [exp dir]")
        sys.exit(1)

    exp_dir = Path(sys.argv[1])
    decoded_dir = exp_dir / "data" / "decoded"
    if not decoded_dir.is_dir():
        print(f"Error: '{decoded_dir}' does not exist.")

    bg_counts = [[0, 0] for _ in range(BG_BITS)]
    bk_counts = [[0, 0] for _ in range(BK_BITS)]
    row_counts = [[0, 0] for _ in range(ROW_BITS)]

    for iter_dir in decoded_dir.iterdir():
        if not iter_dir.is_dir():
            continue
        print(f"Processing iteration '{iter_dir.name}'...")
        for trace_file in iter_dir.iterdir():
            acts = get_acts_from_trace(trace_file)
            print(f"  Loaded {len(acts)} from '{trace_file.name}'.")
            if not(acts):
                print("  No ACTs, skipping...")
                continue
            iter_bg_counts, iter_bk_counts, iter_row_counts = get_counts_for_acts(acts)
            for idx in range(BG_BITS):
                bg_counts[idx][0] += iter_bg_counts[idx][0]
                bg_counts[idx][1] += iter_bg_counts[idx][1]
            for idx in range(BK_BITS):
                bk_counts[idx][0] += iter_bk_counts[idx][0]
                bk_counts[idx][1] += iter_bk_counts[idx][1]
            for idx in range(ROW_BITS):
                row_counts[idx][0] += iter_row_counts[idx][0]
                row_counts[idx][1] += iter_row_counts[idx][1]

    print_counts(bg_counts, bk_counts, row_counts)

