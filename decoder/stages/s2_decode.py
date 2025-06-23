import itertools
import os
import re
import time

from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from stages.s0_xmldigtocsv import get_output_directory as xmldigtocsv__get_output_directory
from util.decoded_cmd import DecodedCommand
from util.dram_command import DramCommand, DRAM_COMMANDS, E_DRAM_CMD, E_DRAM_TYPE
from util.py_helper import print_debug, checkenv, printf
from util.paths import get_input_and_output_file_paths

# 2N mode gives the system more setup and hold time on the CA bus.
# This means we need to decode the second half of a two-cycle command 2 clocks after the first half.
# The 2N mode is enabled by default. See the JEDEC standard for further details.
USE_2N_MODE = True


def get_value_by_name(csv_lines: list[str], line_no: int, signal_name: str) -> str:
    col_no = csv_lines[0].replace('\n', '').split(",").index(signal_name.strip())
    res = csv_lines[line_no].split(",")[col_no]
    return res

def get_output_directory(iter_name: str):
    return Path(os.getenv("DATA_DIR")) / "decoded" / iter_name

# Decode for a single pair csv,regex
# @dram_cmd the DRAM command
def __decode_single_csv_regex(csvlines: list, dram_cmd: DramCommand) -> list[int]:
    assert len(csvlines) > 0, "ERROR: empty CSV file found!"
    compiled_regexlist = dram_cmd.get_regexes(csvlines[0].split(','),
                                              dram_cmd.get_commands(True, False),
                                              compiled=True)
    full_matches = list()
    for line_id in range(1, len(csvlines) - len(compiled_regexlist) + 1):
        all_regexes_match = True
        for regex_id, regex in enumerate(compiled_regexlist):
            if not re.match(regex, csvlines[line_id + regex_id]):
                all_regexes_match = False
                break
        if all_regexes_match:
            full_matches.append(line_id)

    return full_matches


# Decode a single CSV.
# @param iter_name the name of the experiment, typically a timestamp followed by a random string.
def __decode_single_csv(dram_type: E_DRAM_TYPE, csv_path: Path, pool: Pool):
    print(f"__decode_single_csv({dram_type}, '{csv_path}', pool)")
    with csv_path.open("r") as f:
        csvlines = f.readlines()
    # Use one core per (CSV file, DRAM command) pair. Returns a list of matching lines for each of the commands.
    all_full_matches: list[list[int]] \
        = pool.starmap(__decode_single_csv_regex, zip(itertools.repeat(csvlines), DRAM_COMMANDS[dram_type]))

    # a dictionary: row_number -> DRAM_cmd_candidates
    # some commands need the second cycle to identify them (e.g., WR/WRA)
    res = defaultdict(list)
    for dram_command_id, dram_command in enumerate(DRAM_COMMANDS[dram_type]):
        for line_no in all_full_matches[dram_command_id]:
            res[line_no].append(dram_command.identifier)

    decoded_commands_csv = list()

    # we take the information from simply mapping the signals to the DRAM command truth table
    # and now reiterate over all decoded commands to
    #   a. determine where two-cycle commands are and then associate these two cycles, so we can later
    #      decode all relevant bits from them (e.g., ACT); or
    #   b. distinguish DRAM commands that cannot uniquely be identified in their first cycle (e.g., WR/WRA)
    for line_no in range(1, len(csvlines) - 1):
        # we did not decode any command in that CSV line (invalid or ignored)
        if line_no not in res:
            print_debug(f"skipping line {line_no}, reason: 'inv/ign'")
            continue
        # Get the cycle count for the matched line.
        cur_cycle = int(get_value_by_name(csvlines, line_no, "cycle_cnt"))
        
        # if it is a one-cycle command, then we ignore any **equal** one-cycle command in the consecutive
        # cycle; equality includes not only the command type (e.g., REFsb) but also all its metadata (e.g., targeted bk)
        last_cmd = None
        identifier = ""
        if len(decoded_commands_csv) > 0 :
            identifier = decoded_commands_csv[-1].cmd
            cycle = decoded_commands_csv[-1].cycle
            if cur_cycle == cycle+1:
                last_cmd = DramCommand.get_command(dram_type, identifier)
                print_debug(f"last_cmd.identifier={identifier}, last_cmd={last_cmd}")

        # Check if we have a match for a two-cycle command, i.e., if we have DDR5 and CA1 == 0 in the first cycle.
        is_two_cycle_command = False
        if dram_type == E_DRAM_TYPE.ddr5:
            ca1_value = get_value_by_name(csvlines, line_no, "CA1")
            print_debug(f"ca1_value={ca1_value}")
            is_two_cycle_command = (ca1_value == "0")

        dram_cmd_candidates: list[E_DRAM_CMD] = res[line_no]
        if not is_two_cycle_command:  # 1-cycle command
            assert len(dram_cmd_candidates) == 1, "1-cycle command with more than one CMD candidate detected!"
            cmd = DramCommand.get_command(dram_type, dram_cmd_candidates[0])
            print_debug(f"dram_cmd_candidates={dram_cmd_candidates}")
            regexes = cmd.get_regexes(csvlines[0].split(','), cmd.get_commands(True, False))
            print_debug(f"regexes={regexes}")
            for rx in regexes: 
                if re.match(rx, csvlines[line_no]):
                    # convert lines into DramCommand objects to extract cmd_metadata
                    metadata = cmd.extract_metadata_csv(csvlines[0].split(','), [csvlines[line_no].split(',')])
                    # save information about these two lines and the decoded command
                    ts = get_value_by_name(csvlines, line_no, "Time")

                    print_debug(f"loop: last_cmd={identifier}, last_cmd={last_cmd}")
                    cur_command_decoded = DecodedCommand(ts, cmd.identifier, metadata, cur_cycle)
                    # last command is the exact same one-cycle command -> ignore it
                    if last_cmd != None:
                        #print_debug(f"{ts}, last_cmd={decoded_commands_csv[-1].identifier}, cur_command={cur_command_decoded.identifier}")
                        if not last_cmd.is_two_cycle_cmd and cur_command_decoded.equals(decoded_commands_csv[-1], ignore_timestamp=True):
                            break 

                    # add command to list of decoded commands
                    print_debug("adding command to decoded_commands_csv")
                    decoded_commands_csv.append(cur_command_decoded)

        else:  # 2-cycle command
            # check that cur_cycle+1 is in csv file
            skip_n = 2 if USE_2N_MODE else 1
            next_cycle = cur_cycle + skip_n

            for cur_line in range(line_no, len(csvlines)-1):
                cycle_cnt = int(get_value_by_name(csvlines, cur_line, "cycle_cnt"))
                if cycle_cnt == next_cycle:
                    print_debug("found next_cycle in file")

                    # now check which of the dram_cmd_candidates is the right one
                    any_match = False
                    for candidate in dram_cmd_candidates:
                        # compare signals of cur_cycle+1 against requirements of second cycle
                        cmd = DramCommand.get_command(E_DRAM_TYPE.ddr5, candidate)
                        # assert cmd.is_two_cycle_cmd, \
                        #     "trying to decode second cycle but command detected is not a two-cycle cmd"
                        if not cmd.is_two_cycle_cmd:
                            continue

                        for rx in cmd.get_regexes(csvlines[0].split(','), cmd.get_commands(False, True)):
                            if re.match(rx, csvlines[cur_line]):
                                print_debug(f"candidates {dram_cmd_candidates}: found {candidate} to be correct")
                                # convert lines into DramCommand objects to extract cmd_metadata
                                metadata = cmd.extract_metadata_csv(csvlines[0].split(','),
                                                                    [csvlines[line_no].split(','),
                                                                     csvlines[cur_line].split(',')])
                                # save information about these two lines and the decoded command
                                ts = get_value_by_name(csvlines, line_no, "Time")
                                decoded_commands_csv.append(DecodedCommand(ts, cmd.identifier, metadata, cur_cycle))

                                any_match = True
                                # all other regexes should NOT match, but we skip checking this here to save time
                                break

                    if not any_match:
                        s = str()
                        for k, v in zip(csvlines[0].split(','), csvlines[cur_line].split(',')):
                            s += '{}={} '.format(k.replace("\n",""), v.replace("\n", ""))
                        print_debug(f"[-] none of the cmd candidates ({dram_cmd_candidates}) matched the second cycle:\n"
                              f"\t{csv_path.name}:{cur_line}: {s}")

                    # no need to iterate over all other candidates if we verified the first candidate meets all reqs.
                    break

                elif cycle_cnt > next_cycle:
                    # we did not find the next cycle in the valid samples
                    print_debug(f"[-] missing second cycle for cmd candidates '{dram_cmd_candidates}' in {csv_path.name}:{line_no}")
                    # break out of while(True)
                    break

    return decoded_commands_csv


# Requires the DATA_DIR env variable.
# Convertes the raw command bus data to named DDR commands (e.g., ACT, REF).
# @param the name of the experiment iteration
def decode_all(dram_type: E_DRAM_TYPE, iter_name: str, num_workers: int) -> None:
    assert (iter_name.count("/") == 0 and iter_name.count("\\") == 0), \
        "iter_name is supposed to be a folder name, not a path!"

    checkenv('DATA_DIR')
    data_dir = Path(os.getenv("DATA_DIR"))
    input_dir = Path(xmldigtocsv__get_output_directory(iter_name))
    output_dir = data_dir / "decoded" / iter_name
    file_paths = get_input_and_output_file_paths(input_dir, output_dir)

    # Run in parallel
    t_start = time.time()
    with Pool(num_workers) as p:
        for in_path, out_path in file_paths:
            if out_path.is_file():
                printf(f"skipping file {in_path.name} as it has already been converted before")
                break

            decoded_commands_csv = __decode_single_csv(dram_type, in_path, p)
            if len(decoded_commands_csv) == 0:
                continue
            # ensure the parent directory of the output file exists
            # write decoded commands to output CSV file
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w") as f:
                f.write(DecodedCommand.get_csv_header() + "\n")
                for line in decoded_commands_csv:
                    f.write(line.to_csv(newline=True))

    t_end = time.time()
    printf(f"decoding done for all {len(file_paths)} file(s) in {t_end - t_start:.3f} seconds.")
