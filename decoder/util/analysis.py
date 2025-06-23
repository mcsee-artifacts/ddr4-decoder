import csv
import glob
import subprocess

import math
import os
import sys
import time
import pint
import pickle
import pint as pt
import pandas as pd

from collections import defaultdict
from enum import Enum
from pandarallel import pandarallel
from typing import List, Optional

from configure import SETUP_FILENAME
from util.dram_command import E_DDR5_DRAM_CMD, DDR5_DRAM_COMMANDS, DramCommand
from configuration.constants import ValueStr
from util.py_helper import printf
from util.units import Units

# key for the statistics dict to count the occurrence of DRAM commands
CMD_OCCURENCE_CNT = 'cmd_count'

# labels to be used in the pandas Dataframe for signals not recognized as a DRAM command
lbl_dram_cmd_unknown = "unknown"

# filename of the serialized pandas DataFrame
PICKLE_SUFFIX = "decoded.pkl"

# column 'TimeNormalized'
column_TIME_NORMALIZED = 'TimeNormalized'

# a dictionary with definitions of all DRAM commands
dram_cmds_all = dict()


class CsvParsingException(Exception):
    pass


class EmptyDataframeException(Exception):
    pass


class BankStatus(Enum):
    # bank is not doing anything
    IDLE = 0
    # the bank cannot be activated as its is busy (because of a preceding ACT)
    BLOCKED = 1
    # a row in the bank has been activated, the bank is ready to receive READ/WRITE cmds
    ACTIVE = 2
    # the bank is precharging the currently loaded row
    PRECHARGING = 3
    # the bank is reading data from a row
    READING = 4
    # the bank is writing data from a row and will be precharging that row in the next cycle
    READING_AP = 5
    # the bank is writing data to a row
    WRITING = 6
    # the bank is writing data to o row and will be precharging that row in the next cycle
    WRITING_AP = 7


def get_dram_cmd_dataframe(filter_cmds: List[E_DDR5_DRAM_CMD] = None) -> pd.DataFrame:
    # create dataframe with collected keys
    all_dfs = list()
    for k in DDR5_DRAM_COMMANDS:
        cmd_list = k.cmds if k.is_two_cycle_cmd else [k]
        for c in cmd_list:
            if filter_cmds is not None and c.identifier not in filter_cmds:
                continue
            signals = c.requirements
            signals['name'] = c.identifier
            # noinspection PyTypeChecker
            all_dfs.append(pd.DataFrame.from_dict([signals], dtype=object))
    return pd.concat(all_dfs)


def get_all_dram_cmds() -> dict:
    ret = dict()
    for c1 in DDR5_DRAM_COMMANDS:
        if c1.is_two_cycle_cmd:
            # ret[c1.identifier] = c1
            # for c2 in c1.cmds:
            #     ret[c2.identifier] = c2
            ret |= {c1.identifier: c1} | {c.identifier: c for c in c1.cmds}
        else:
            ret[c1.identifier] = c1
    return ret


def check_xmldig2csv_procs(list_of_processes: list) -> list:
    still_running_procs = list()
    for fn, proc in list_of_processes:
        return_code = proc.poll()  # non-blocking check
        if return_code is None:
            # process is still running
            still_running_procs.append([fn, proc])
        elif return_code != 0:
            # process failed to convert file
            printf(f"failed to convert {fn} to CSV: return_code = {return_code}")
        else:
            # process converted file successfully
            continue
    # remove those processes that completed successfully from the passed list (reference)
    return still_running_procs


def str2number(s: str):
    try:
        if s.isdigit():
            return int(s)
        else:
            raise ValueError
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def extract_setup_file_values(input_dir_wo_csv_filter: str, stats: dict) -> None:
    # use the line no. to extract the data quicker
    params_lines = {
        ValueStr.ACQ_HOR_SCALE: 57115,
        ValueStr.ACQ_HOR_OFFSET: 57116,
        ValueStr.ACQ_HOR_SAMPLE_RATE: 57114}

    if not os.path.exists(os.path.join(input_dir_wo_csv_filter, SETUP_FILENAME)):
        printf(f"could not find setup file {SETUP_FILENAME} to determine acquisition params")
        for param, _ in params_lines.items():
            stats[param] = ""
        return

    # extract relevant line numbers from the setup file
    for param, line_no in params_lines.items():
        file = os.path.join(input_dir_wo_csv_filter, SETUP_FILENAME)
        ss = '.'.join(param.split('.')[-2:])
        # tell grep to only return one (the first) match
        out = subprocess.check_output(['grep', '-m', '1', ss, file]).decode("utf-8")
        if out is not None and len(out) > 0 and out.count('=') == 1:
            stats[param] = str2number(out.split("=")[1].strip())
        else:
            printf(f"could not find setup param {param} in specified line {line_no} of file {SETUP_FILENAME}")
            stats[param] = ""

    print("")


def match_dram_cmd(x: pd.Series, label_unknown: str, dram_cmds: pd.DataFrame):
    # noinspection PyUnresolvedReferences
    import pandas  # needed for pandarallel as function must be self-contained
    for _, row in dram_cmds.iterrows():
        row_wo_na_name = row.dropna().drop('name')
        v_view = x[row_wo_na_name.index]
        if row_wo_na_name.astype(int).equals(v_view):
            return row['name']
    # let's keep the 'cmd' column empty for signals that might be part of a two-cycle command,
    # i.e., second cycle where CS==1
    return label_unknown if x['CS'] != 1 else ""


def open_logfile(logs_dir: str, filename: str):
    p = os.path.join(logs_dir, f"decoding_{filename.replace('.csv', '.txt')}")
    log_decoding = open(p, "w")
    return log_decoding


def read_preprocess_csv(file_path: str, filter_csv: bool) -> (pd.DataFrame, float, float):
    # get column names (all_cols), and the timestamps of the first (first_line_ts) and second line (second_line_ts)
    with open(file_path, 'r', newline='') as f:
        csv_reader = csv.reader(f)
        # get the column names by reading the first row of the CSV file
        all_cols = next(csv_reader)
        first_line_ts = float(next(csv_reader)[0])
        second_line_ts = float(next(csv_reader)[0])

    # get the last timestamp of the file
    with open(file_path, 'rb', newline=None) as f:
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        last_line_ts = float(f.readline().decode().split(',')[0])

    # remove columns where all signals (except CK0) are HIGH
    # this is invalid, and it is probably the default ("default high") when no signal is sent
    if filter_csv:
        # note that we cannot combine STAGE 1 and STAGE 2 as STAGE 1 relies on pcregrep's -v flag
        # STAGE 1: remove all lines where all signals equal "1"
        rx_all_ones = "^"
        for idx, col in enumerate(all_cols):
            rx_all_ones += "," if idx > 0 else ""
            # a regex where all signals are '1' except Time and CK0
            rx_all_ones += "[^,]*" if (col == 'Time' or col == 'CK0' or col == 'CS') else "1"

        # do not append the filename as otherwise we will end up recreating over and over the same file;
        # instead, overwrite the file if it already exists
        abbrv = "noNull"
        file_path_new = f"{file_path.replace('.csv', f'_{abbrv}.csv')}" if abbrv not in file_path else file_path
        new_csv = open(file_path_new, "w")

        # we use the '-v' flag to invert our match as we want to keep all lines where the regex is false
        process = subprocess.Popen(["pcregrep", "-v", rx_all_ones, file_path], stdout=new_csv)
        process.wait()
        new_csv.close()

        # overwrite old CSV by new (minimized) CSV
        # os.replace(file_path_new, file_path)
        file_path = file_path_new

        # STAGE 2:
        # TODO: a regex catching ACT, WR[P|A], RD[A], REF[ab|sb], RFM[ab|sb], PRE[ab|sb|pb]
        rx_invalid_cmd = "^"
        # (CS==0 && CA==1) || (CS==0&&

    try:
        # define dtypes for CSV
        exceptions = {'Time': float}
        dtype = {col_name: (int if col_name not in exceptions else exceptions[col_name]) for col_name in all_cols}
        # parse the CSV file and reorder the columns
        cols = ['Time', 'CK0', 'CS',
                'CA0', 'CA1', 'CA2', 'CA3', 'CA4', 'CA5', 'CA6', 'CA7', 'CA8', 'CA9', 'CA10', 'CA11', 'CA12']
        parsed_csv = pd.read_csv(file_path, engine='c', sep=',', header=0, dtype=dtype, usecols=cols)[cols]
        # parsed_csv = pd.read_csv(file_path, engine='c', sep=',', header=0, dtype=dtype)
    except Exception as ex:
        printf(f"failed parsing {file_path} due to {sys.exc_info()[0]}, skipping this file")
        raise ex

    # some validity checks
    assert parsed_csv.shape[1] > 1, "dataframe resulting from parsing CSV has <= 1 columns!"
    if parsed_csv.loc[parsed_csv['CS'] == 1].shape[0] == parsed_csv.shape[0] \
            or parsed_csv.loc[parsed_csv['CS'] == 0].shape[0] == parsed_csv.shape[0]:
        printf(f"found always CS==0 or always CS==1: skipping this file")
        parsed_csv = pd.DataFrame()

    sample_ts_delta = (second_line_ts - first_line_ts)
    return parsed_csv, first_line_ts, last_line_ts, sample_ts_delta


def print_stats_param(name: str, value=None, newline: bool = True):
    value = '' if value is None else value
    if type(value) == str:
        value = str2number(value)

    str_format = None
    if type(value) == int:
        str_format = '{:,d}'
    elif type(value) == float:
        str_format = '{:,.3f}'

    ov = str()
    if type(value) == dict:
        for key, value in sorted(value.items(), key=lambda x: x[0]):
            ov += "('{}' : {}), ".format(key, value)
        value = ov

    if str_format is not None:
        print('  ', '{:22s}: '.format(name), str_format.format(value), end='\n' if newline else '')
    else:
        print('  ', '{:22s}: '.format(name), value, end='\n' if newline else '')


def _format_header(txt: str, width=45, filler='-', align='c'):
    assert (align in 'lcr')
    txt = f" {txt} "
    return {'l': txt.ljust, 'c': txt.center, 'r': txt.rjust}[align](width, filler)


def print_section(name: str):
    print(_format_header(name, filler='=', align='c'))


def print_subsection(name: str):
    filler = '-'
    print(_format_header(f"{filler}{filler}{filler}{filler} {name}", filler='-', align='l'))


def calculate_max_acts(record_length_sec: pint.quantity, dimm_cfg: dict, u: Units):
    # we use the calculation method of the Subarray-Level Parallelism (SALP) paper here
    # https://doi.org/10.1184/R1/6468167.v1
    t_rp = dimm_cfg['trp'] * u.ureg.picosecond
    assert dimm_cfg['trp'] > 10_000, "tRP probably not given in picoseconds"

    t_ras = dimm_cfg['tras'] * u.ureg.picosecond
    assert dimm_cfg['tras'] > 20_000, "tRAS probably not given in picoseconds"

    t_rcd = dimm_cfg['trcd'] * u.ureg.picosecond
    assert dimm_cfg['trcd'] > 10_000, "tRCD probably not given in picoseconds"

    t_act = (t_rp + t_ras + t_rcd)
    # result = math.floor((record_length_sec / t_act).magnitude)
    result = (record_length_sec.to('picosecond') / t_act).magnitude

    # we use math.ceil here because we are interested in the max
    return math.ceil(result)


def calculate_max_refs(record_length_sec: pt.Unit, dimm_cfg: dict, u: Units, stats: dict):
    stats['max_refab_temp_std'] = ((record_length_sec * u.ureg.seconds) / (
            dimm_cfg['t_refi_refab']['temp_std'] * u.ureg.seconds)).magnitude
    stats['max_refsb_temp_std'] = ((record_length_sec * u.ureg.seconds) / (
            dimm_cfg['t_refi_refsb']['temp_std'] * u.ureg.seconds)).magnitude
    stats['max_refab_temp_high'] = ((record_length_sec * u.ureg.seconds) / (
            dimm_cfg['t_refi_refab']['temp_high'] * u.ureg.seconds)).magnitude
    stats['max_refsb_temp_high'] = ((record_length_sec * u.ureg.seconds) / (
            dimm_cfg['t_refi_refsb']['temp_high'] * u.ureg.seconds)).magnitude


def write_statistics(u: Units, stats: dict, dimm_cfg: dict, target_file_path: str = None):
    printf(f"writing decoding summary to {target_file_path if target_file_path is not None else 'stdout'}")
    if target_file_path is not None:
        sys.stdout = open(target_file_path, 'w')

    print_section("RESULTS")
    print_stats_param('analysis time (sec)', stats['time_analysis'])

    print_subsection("DIMM SPECS (SPD)")
    print_stats_param('DIMM ID', dimm_cfg['dimm_id'])
    print_stats_param('#banks/bg', dimm_cfg['num_banks_per_bankgroup'])
    print_stats_param('#bgs', dimm_cfg['num_bankgroups'])
    # timings
    print_stats_param('tREFI REFab (us)',
                      f"{u.sec_to_us(dimm_cfg['t_refi_refab']['temp_std'])}")
    print_stats_param('tREFI REFsb (us)',
                      u.sec_to_us(dimm_cfg['t_refi_refsb']['temp_std']) if 't_refi_refsb' in dimm_cfg else 'n/a')
    print_stats_param('tRFC REFab (ns)',
                      u.sec_to_ns(dimm_cfg['t_rfc']))
    print_stats_param('tRFC REFsb (ns)',
                      u.sec_to_ns(dimm_cfg['t_rfc_sb']) if 't_rfc_sb' in dimm_cfg else 'n/a')
    print_stats_param('[FGR?]', dimm_cfg['fgr'])
    print_stats_param("[RFM REQ?]", [dimm_cfg['rfm'][a]['rfm_req'] for a in dimm_cfg['rfm']])

    print_subsection("ACQ")
    print_stats_param('dir size (MB)', f"{stats['total_filesize_mb']:.2f}")
    print_stats_param('#acqusitions', stats['total_acqs'])
    print_stats_param('sampling rate', stats['sampling_rate'])
    print_stats_param('horizontal res.', u.pp_sec(stats[ValueStr.ACQ_HOR_SCALE]))
    # print_stats_param('acq. window', [u.pp_sec(k) for k in stats['acq_window']])
    print_stats_param('acq. window', stats['acq_window_cnts'])
    print_stats_param('sample period (ns)', stats['time_btw_sampling_pts'])
    print_stats_param('total record length', u.pp_sec(stats['tot_record_dur']))
    print_stats_param('total data pts', stats['total_num_lines'])
    print_stats_param('total events', stats['total_sampled_events'])
    print_stats_param('valid cmds', stats['valid_cmds'])
    print_stats_param('total #ticks', stats['cnt_ticks'])

    print_subsection("DRAM CMDs")
    keys_with_stats = [k for k in stats['cmd_count'].keys()]

    all_defined_keys = [z.identifier.value for z in DDR5_DRAM_COMMANDS]
    # all_defined_keys = list()
    # for cmd in DDR5_DRAM_COMMANDS:
    #     all_defined_keys.append(cmd)
    # if cmd.is_two_cycle_cmd:
    #     if len(cmd.cmds) > 0:
    #         all_defined_keys.append(str(cmd.cmds[0]))

    # all_defined_keys = [z.identifier for z in DDR5_DRAM_COMMANDS]
    keys = list(set(keys_with_stats + all_defined_keys))
    keys.sort()  # sort the list to have a command-based output order (e.g., REFab, REFsb, PREab, PREsb)
    for key in keys:
        val = stats['cmd_count'][key] if key in stats['cmd_count'] else 0
        cmd_name = f'#{key}'
        print_stats_param(cmd_name, val)

    print_subsection("DRAM CMDs UPPER BOUNDS")
    print_stats_param('max. #ACTs', stats['max_acts'])
    print_stats_param('max. #REFab (std|high)',
                      f"{math.floor(stats['max_refab_temp_std']):,d} | {math.floor(stats['max_refab_temp_high']):,d}")
    print_stats_param('max. #REFsb (std|high)',
                      f"{math.floor(stats['max_refsb_temp_std']):,d} | {math.floor(stats['max_refsb_temp_high']):,d}")

    print_subsection("FREQ STATS (ACT)")
    # most frequently accessed DRAM address
    mf_addrs_sorted = sorted(stats['most_freq_addr'].items(), key=lambda x: x[1], reverse=True)[:10]
    mf_addrs_str = build_freq_cnt_string(mf_addrs_sorted)
    print_stats_param('most frq. addrs (bg,bk,row)', mf_addrs_str)

    # frequency count of bankgroup bits
    # print_stats_param('bankgroup bits', dict(stats['freq_count_bg']))
    bg_sorted = sorted(stats['freq_count_bg'].items(), key=lambda x: x[1], reverse=True)
    bg_str = build_freq_cnt_string(bg_sorted)
    print_stats_param('bankgroup bits', bg_str)

    # frequency count of bank bits
    # print_stats_param('bank bits', dict(stats['freq_count_bk']))
    bk_sorted = sorted(stats['freq_count_bk'].items(), key=lambda x: x[1], reverse=True)
    bk_str = build_freq_cnt_string(bk_sorted)
    print_stats_param('bank bits', bk_str)

    # frequency count of row bits
    rows_sorted = sorted(stats['freq_count_row'].items(), key=lambda x: x[1], reverse=True)[:50]
    rows_str = build_freq_cnt_string(rows_sorted)
    print_stats_param('row bits', rows_str)

    if target_file_path is not None:
        sys.stdout.close()
        sys.stdout = sys.__stdout__


def build_freq_cnt_string(list_of_tuples: list[tuple]):
    out_str = ""
    for k, v in list_of_tuples:
        out_str += f"\n\t\t{k} x{v}"
    return out_str


def update_banks(bank_st: dict, status: BankStatus, cmd_metadata: dict):
    # not explicitly passing a target_bank means we assume an ALL BANK command (e.g., REFab)
    if (cmd_metadata is None) or (cmd_metadata is not None and 'bk' not in cmd_metadata):
        banks = list(bank_st.keys())
    else:
        banks = [cmd_metadata['bk']]

    for bk in banks:
        bank_st[bk]['status'] = status


def target_bank_is_blocked(metadata: dict, bk_status: dict) -> bool:
    target_bk = metadata['bk']
    return bk_status[target_bk]['status'] == BankStatus.BLOCKED


def wccount(filename: str):
    out = subprocess.Popen(['wc', '-l', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
    var = out.partition(b' ')
    return int(var[2].decode('utf-8').strip().split(' ')[0], 10)


def process_command(stats: dict, row: pd.Series, bank_status: dict, pending_cmds: list) -> (float, bool):
    cur_cmd = dram_cmds_all[row['cmd']] if row['cmd'] != '' else None
    valid_cmd: bool = True

    # no pending commands, i.e., we are not in the middle of a two-cycle commands
    if len(pending_cmds) == 0 and cur_cmd is not None:
        # extract the command's metadata if the command includes any metadata (e.g., bk, bg, row bits)
        cmd_metadata = cur_cmd.extract_metadata(dict(row)) if cur_cmd.has_metadata() else None

        # =================
        # commands that are two-cycle commands need to store the potential command of the first cycle here
        # it might be that we find out in the second cycle that the first cycle command was WRONG

        # ACTIVATE
        if cur_cmd.identifier == E_DDR5_DRAM_CMD.act1:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            # the ACT2 must come two ticks after (i.e., on the next positive edge)
            # stats['max_tick_age'] = stats['cnt_ticks'] + 2
            update_banks(bank_status, BankStatus.ACTIVE, cmd_metadata)
            pending_cmds.append(cur_cmd)
            # avoids printing CMD in the caller as it has not been committed yet
            cur_cmd = None

        # READ
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.rd1:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            update_banks(bank_status, BankStatus.READING, cmd_metadata)
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # READ with auto-precharge
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.rda1:
            # TODO do no expect a PRECHARGE command after READ as this cmd does auto-precharge
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            update_banks(bank_status, BankStatus.READING_AP, cmd_metadata)
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # WRITE
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.wr1:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            update_banks(bank_status, BankStatus.WRITING, cmd_metadata)
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # WRITE with auto-precharge
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.wra1:
            # TODO do no expect a PRECHARGE command after WRITE as this cmd does auto-precharge
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            update_banks(bank_status, BankStatus.WRITING_AP, cmd_metadata)
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # MODE REGISTER READ
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.mrr1:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # MODE REGISTER WRITE
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.mrw1:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # RESERVED FOR FUTURE USE
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.rfu1:
            stats[CMD_OCCURENCE_CNT][E_DDR5_DRAM_CMD.rfu.value] += 1
            pending_cmds.append(cur_cmd)
            cur_cmd = None

        # =================
        # "normal" one-cycle commands

        # REFRESH all banks
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.ref_ab:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            update_banks(bank_status, BankStatus.BLOCKED, cmd_metadata)

        # REFRESH same bank
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.ref_sb:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1
            update_banks(bank_status, BankStatus.BLOCKED, cmd_metadata)

        # REFRESH MANAGEMENT all banks
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.rfm_ab:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

        # REFRESH MANAGEMENT same bank
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.rfm_sb:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

        # PRECHARGE all banks
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.pre_ab:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

        # PRECHARGE same bank
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.pre_sb:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

        # PRECHARGE per bank
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.pre_pb:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

        # commands where we do not take any special actions but just count their occurrence
        # VOLTAGE REFERENCE COMMAND/ADDRESS
        # VOLTAGE REFERENCE COLUMN SELECT
        # SELF-REFRESH ENTRY
        # SELF-REFRESH ENTRY with frequency change
        # POWER-DOWN-ENTRY
        # MULTIPURPOSE COMMAND
        # NOP or POWER-DOWN EXIT
        elif cur_cmd.identifier == E_DDR5_DRAM_CMD.vref_ca \
                or cur_cmd.identifier == E_DDR5_DRAM_CMD.vref_cs \
                or cur_cmd.identifier == E_DDR5_DRAM_CMD.sre \
                or cur_cmd.identifier == E_DDR5_DRAM_CMD.sre_f \
                or cur_cmd.identifier == E_DDR5_DRAM_CMD.pde \
                or cur_cmd.identifier == E_DDR5_DRAM_CMD.mpc \
                or cur_cmd.identifier == E_DDR5_DRAM_CMD.nop_pdx:
            stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

        else:
            # this should never happen as we skipped all unknown commands before  calling process_command
            # raise Exception(f"UNKNOWN COMMAND FOUND:\n{row.to_dict()}")
            printf(f"skipping command {cur_cmd.identifier} "
                  f"(typically because no corresponding first-cycle CMD was found)")

    # len(pending_cmds) > 0: we need to take the previous command into account when decoding the current command
    # => decode the second cycle of two-cycle commands
    elif len(pending_cmds) > 0:
        # FIXME: this assertion fails but I don't know why..
        # assert len(pending_cmds) > 1, "more than 1 CMD in pending_cmds, this should NEVER happen!"

        last_cmd = pending_cmds[-1]
        candidate_cmds = {
            E_DDR5_DRAM_CMD.act1: E_DDR5_DRAM_CMD.act2,
            E_DDR5_DRAM_CMD.wr1: E_DDR5_DRAM_CMD.wr2,
            E_DDR5_DRAM_CMD.rd1: E_DDR5_DRAM_CMD.rd2,
            E_DDR5_DRAM_CMD.wra1: E_DDR5_DRAM_CMD.wra2,
            E_DDR5_DRAM_CMD.rda1: E_DDR5_DRAM_CMD.rda2,
            E_DDR5_DRAM_CMD.rfu1: E_DDR5_DRAM_CMD.rfu2,
            E_DDR5_DRAM_CMD.mrr1: E_DDR5_DRAM_CMD.mrr2,
            E_DDR5_DRAM_CMD.mrw1: E_DDR5_DRAM_CMD.mrw2
        }

        if last_cmd.identifier not in candidate_cmds:
            print("not found!")
            print(last_cmd)

        candidate = candidate_cmds[last_cmd.identifier]
        if dram_cmds_all[candidate].satisfies_reqs(row):
            cmd_metadata = dram_cmds_all[candidate].extract_metadata_csv(dict(row))
            cur_cmd = dram_cmds_all[candidate]

            if candidate == E_DDR5_DRAM_CMD.act2:
                cur_cmd = create_two_cycle_cmd(cur_cmd, cmd_metadata, pending_cmds, bank_status, BankStatus.IDLE)
                stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

                # as we changed the command, we need to call get_metadata again
                cmd_metadata = cur_cmd.get_metadata()
                target_bg = cmd_metadata['bg']
                target_row = cmd_metadata['row']
                target_bk = cmd_metadata['bk']
                stats['freq_count_bg'][target_bg] += 1
                stats['freq_count_bk'][target_bk] += 1
                stats['freq_count_row'][target_row] += 1
                stats['most_freq_addr'][(target_bg, target_bk, target_row)] += 1

                assert (False)

            elif candidate in [E_DDR5_DRAM_CMD.wr2, E_DDR5_DRAM_CMD.rd2]:
                cur_cmd = create_two_cycle_cmd(cur_cmd, cmd_metadata, pending_cmds, bank_status, BankStatus.IDLE)
                stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

            elif candidate in [E_DDR5_DRAM_CMD.wra2, E_DDR5_DRAM_CMD.rda2]:
                cur_cmd = create_two_cycle_cmd(cur_cmd, cmd_metadata, pending_cmds, bank_status, BankStatus.PRECHARGING)
                stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

            elif candidate in [E_DDR5_DRAM_CMD.rfu2, E_DDR5_DRAM_CMD.mrr2, E_DDR5_DRAM_CMD.mrw2]:
                cur_cmd = create_two_cycle_cmd(cur_cmd, cmd_metadata, pending_cmds, bank_status, None)
                stats[CMD_OCCURENCE_CNT][cur_cmd.identifier.value] += 1

            print(cur_cmd.identifier, cur_cmd.get_metadata_str)

        # now we clear the accumulator list as process_cmd is only called once per 0-1 transition
        pending_cmds.clear()

    return cur_cmd, valid_cmd


def create_two_cycle_cmd(cmd: DramCommand, cmd_metadata: dict, pending_cmds: list[DramCommand],
                         bank_status: dict, target_bank_status: Optional[BankStatus]):
    # save the original cmd, (e.g., an ACT2)
    orig_cmd = cmd

    # create a top command (e.g., ACT), then combine the add both subcommands (e.g., ACT1 and ACT2)
    cmd = dram_cmds_all[E_DDR5_DRAM_CMD.act]
    cmd.cmds.clear()
    cmd.add_subcommand(pending_cmds[0])
    pending_cmds.clear()
    cmd.add_subcommand(orig_cmd)

    if target_bank_status is not None:
        # we ignore the fact here that in reality the bank wouldn't become idle immediately afterwards
        update_banks(bank_status, target_bank_status, cmd_metadata)

    return cmd


def load_preprocess_write_pickle(file_path: str, file_name: str, ignore_pickle: bool, stats: dict,
                                 u: Units, dram_cmds_decode: pd.DataFrame, write_pickle: bool):
    file_parent_dir = os.path.dirname(file_path)
    file_pickle_name = f"{file_name.replace('.csv', '')}_{PICKLE_SUFFIX}"
    file_pickle_path = os.path.join(file_parent_dir, file_pickle_name)

    # if a pickle file exists, there is no need to preprocess and load the CSV
    if os.path.exists(file_pickle_path) and not ignore_pickle:
        printf(f"loading preprocessed data from Pickle file {file_pickle_name}")
        decoded_df, first_ts, last_ts, ts_delta = pickle.load(open(file_pickle_path, "rb"))
    else:
        # preprocess and parse the CSV
        printf(f"parsing CSV file from {file_path}")
        try:
            csv_df, first_ts, last_ts, ts_delta = read_preprocess_csv(file_path, True)
        # forward the exception to the caller
        except Exception as _:
            raise
        # decode the data
        decoded_df = preprocess_decode(dram_cmds_decode, csv_df)
        if decoded_df.empty:
            raise EmptyDataframeException

        if write_pickle:
            # serialize data for future analysis of the same file
            printf(f"serializing parsed, preprocessed, and decoded data into Pickle file")
            pickle.dump((decoded_df, first_ts, last_ts, ts_delta), open(file_pickle_path, "wb"))

    stats['time_btw_sampling_pts'] = (ts_delta * u.ureg.seconds).to("nanoseconds").magnitude
    return decoded_df, first_ts, last_ts


def analyze_trace(input_path: str, file_filter: str, dimm_cfg: dict, out_file: str, ign_pickle: bool, write_csv: bool,
                  write_pickle: bool):
    u = Units()
    t_analysis_start = time.time()

    # get all DRAM commands that we want to decode
    # all commands except the second cycle of 2-cycle commands (as they are not distinguishable by their signals only)
    dram_cmds_decode = get_dram_cmd_dataframe(
        [E_DDR5_DRAM_CMD.act1, E_DDR5_DRAM_CMD.pre_ab, E_DDR5_DRAM_CMD.pre_sb, E_DDR5_DRAM_CMD.pre_pb, E_DDR5_DRAM_CMD.ref_ab,
         E_DDR5_DRAM_CMD.ref_sb,
         E_DDR5_DRAM_CMD.rfm_sb, E_DDR5_DRAM_CMD.rfm_ab, E_DDR5_DRAM_CMD.wr, E_DDR5_DRAM_CMD.wr1, E_DDR5_DRAM_CMD.wra, E_DDR5_DRAM_CMD.wra1,
         E_DDR5_DRAM_CMD.rd, E_DDR5_DRAM_CMD.rd1,
         E_DDR5_DRAM_CMD.rda, E_DDR5_DRAM_CMD.rda1, E_DDR5_DRAM_CMD.nop_pdx, E_DDR5_DRAM_CMD.mpc, E_DDR5_DRAM_CMD.pde, E_DDR5_DRAM_CMD.sre,
         E_DDR5_DRAM_CMD.sre_f,
         E_DDR5_DRAM_CMD.rfu1c, E_DDR5_DRAM_CMD.rfu, E_DDR5_DRAM_CMD.rfu1, E_DDR5_DRAM_CMD.vref_ca, E_DDR5_DRAM_CMD.vref_cs, E_DDR5_DRAM_CMD.mrr,
         E_DDR5_DRAM_CMD.mrr1,
         E_DDR5_DRAM_CMD.mrw, E_DDR5_DRAM_CMD.mrw1]
    )
    global dram_cmds_all
    dram_cmds_all = get_all_dram_cmds()

    # statistics to be collected across all files
    stats = {
        'acq_window': list(),
        'cmd_count': defaultdict(int),
        'cnt_ticks': 0,
        'freq_count_bg': defaultdict(int),
        'freq_count_bk': defaultdict(int),
        'freq_count_row': defaultdict(int),
        'most_freq_addr': defaultdict(int),
        'total_acqs': 0,
        'total_filesize': 0,
        'total_num_lines': 0,
        'total_sampled_events': 0,
        'valid_cmds': 0
    }

    # this makes sure that following code works for single files and also folders
    input_is_file = input_path.endswith('.csv') or input_path.endswith('.XMLdig')
    inp_dir = input_path if input_is_file else os.path.join(input_path, file_filter)

    # now we iterate over the CSV files in the folder
    for file_path in glob.glob(inp_dir):
        # skip files containing "_decoded" in it (those are CSVs for export into Excel)
        file_name = os.path.basename(file_path)
        if "_decoded.csv" in str(file_path) or "_exp_cfg.csv" in str(file_path):
            printf(f"skipping Excel export file: {file_name}")
            continue

        # skip empty files
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            printf(f"skipping empty file: {file_name}")
            continue

        # collect some statistics
        stats['total_num_lines'] += (wccount(file_path) - 1)
        stats['total_filesize'] += file_size
        stats['total_acqs'] += 1

        # if a pickle file exists with the decoded commands, load it to save time
        try:
            decoded_df, first_ts, last_ts = load_preprocess_write_pickle(file_path, file_name, ign_pickle, stats, u,
                                                                         dram_cmds_decode, write_pickle)
            stats['acq_window'].append(last_ts - first_ts)
        except CsvParsingException as _:
            printf(f"parsing CSV file failed! skipping file {file_name}...")
            continue
        except EmptyDataframeException as _:
            printf(f"skipping empty dataframe: {file_name}")
            continue

        # create logging directory
        logs_dir = os.path.join(input_path, "../logs")
        os.makedirs(logs_dir, exist_ok=True)

        # validation of signals, for example: set column error to 1 whenever any signal changes while CLK is high
        validate_signal_consistency(decoded_df, logs_dir, file_name)

        # create a structure to keep track of each bank's status, this is needed for commands targeting a specific bank
        bank_status = dict()
        initialize_bank_status(bank_status, dimm_cfg)

        # open logfile
        # log_decoding = open_logfile(logs_dir, file_name)
        # log_decoding.write("idx, time, time_norm, t_last_ref, cmd, [ign_reason]\n")

        # iterate over decoded commands and mark those that are actually valid (e.g., respect tRFC), collect stats
        pending_cmds = list()

        last_cmd = None
        same_cmd_active_since_samples = 0

        cnt_stable_01 = 0
        cnt_stable_10 = 0

        iterator = zip(decoded_df.iterrows(), decoded_df.iloc[1:].iterrows())
        for (_, rowLast), (idx, row) in iterator:

            # for (_, rowLast), (idx, row) in zip(decoded_df.iterrows(), decoded_df.iloc[1:].iterrows()):
            stats['total_sampled_events'] += 1
            stats['cnt_ticks'] += (rowLast['CK0'] != row['CK0'])

            if (rowLast['CK0'] == 0 and row['CK0'] == 1) and (rowLast['cmd'] == row['cmd']):
                cnt_stable_01 += 1
            elif (rowLast['CK0'] == 1 and row['CK0'] == 0) and (rowLast['cmd'] == row['cmd']):
                cnt_stable_10 += 1

            if last_cmd is not None and row['cmd'] == last_cmd['cmd']:
                same_cmd_active_since_samples += 1
            else:
                same_cmd_active_since_samples = 0
            decoded_df.loc[idx, 'same_cmd_cnt'] = same_cmd_active_since_samples
            last_cmd = row

            # TODO: require that row['cmd'] is the same before at the point CLK=0 -> CLK=1

            # we only care about 0->1 CLK transitions, that means we do *not* care about:
            # (i) falling edges, (ii) unchanged HIGH or LOW
            if not (rowLast['CK0'] == 0 and row['CK0'] == 1):
                decoded_df.loc[idx, 'error_dontcare'] = 1
                continue

            #  skip unknown commands
            if row['cmd'] == lbl_dram_cmd_unknown:
                decoded_df.loc[idx, 'error_invalidCmd'] = 1
                continue

            # make sure that [REF,RFM]sb only appear if FGR is enabled
            if row['cmd'] != '':
                cmd_identifier = dram_cmds_all[row['cmd']].identifier
                assert cmd_identifier != E_DDR5_DRAM_CMD.rfm_sb or dimm_cfg['fgr'], "REFsb detected but FGR not enabled"
                assert cmd_identifier != E_DDR5_DRAM_CMD.ref_sb or dimm_cfg['fgr'], "RFMsb detected but FGR not enabled"

            # command-specific actions ##########################################
            cmd, valid_cmd = process_command(stats, row, bank_status, pending_cmds)
            stats['valid_cmds'] += int(valid_cmd)

            # omit writing non-decodable "unknown" commands into the decoding log
            # note: two-cycle commands return cmd=None from process_command but valid_cmd=True
            if not valid_cmd or (cmd is not None and cmd.identifier == lbl_dram_cmd_unknown):
                decoded_df.loc[idx, 'error_invalidCmd'] = 1
            if cmd is None:
                continue

            # now write the decoded command back to the dataframe to also have 2-cycle commands in the output
            decoded_df.loc[idx, 'cmd'] = cmd.identifier

            # general stuff to do for each matched command ##########################################

            out_str = f"{idx:08d}, {row['Time']:.13f}, {row[column_TIME_NORMALIZED]:8.13f}, "
            cmd_data = f"{str(cmd):>6s}"
            str_length = 12
            if cmd.has_metadata():
                cmd_data += f" ({cmd.get_metadata_str()})"
                str_length = 20
            out_str += f"{cmd_data:{str_length}s}"
            # out_str += ", IGN_tRFC" if all_banks_blocked or target_bank_blocked else ""

            # log_decoding.write(out_str + '\n')

        # log_decoding.close()

        print("cnt_stable_01:", cnt_stable_01)
        print("cnt_stable_10:", cnt_stable_10)

        # write decoded dataframe into CSV file (e.g., to import and manually analyze in Excel)
        if write_csv:
            abbrv = "noNull_decoded"
            target_path = file_path.replace('.csv', f'_{abbrv}.csv') if abbrv not in file_path else file_path
            decoded_df.to_csv(target_path)

    # extract scope configuration data from setup file
    extract_setup_file_values(input_path, stats)

    # calculate and convert some more statistics
    stats['time_analysis'] = time.time() - t_analysis_start
    stats['total_filesize_mb'] = stats['total_filesize'] / 1024 / 1024
    stats['sampling_rate'] = get_sample_rate_pp(stats[ValueStr.ACQ_HOR_SAMPLE_RATE])
    stats['tot_record_dur'] = sum(stats['acq_window'])
    stats['max_acts'] = calculate_max_acts(stats['tot_record_dur'] * u.ureg.seconds, dimm_cfg, u)
    stats['acq_window_cnts'] = [f"({v}x,{k})" for k, v in get_acq_window_occurrence_cnt(stats, u).items()]
    calculate_max_refs(stats['tot_record_dur'] * u.ureg.seconds, dimm_cfg, u, stats)

    # write statistics into file
    write_statistics(u, stats, dimm_cfg, out_file)


def get_acq_window_occurrence_cnt(stats, u):
    aw = defaultdict(int)
    for k in stats['acq_window']:
        aw[u.pp_sec(k)] += 1
    return aw


def validate_signal_consistency(decoded_df: pd.DataFrame, logs_dir: str, filename: str, write_logfile: bool = False):
    file_path = os.path.join(logs_dir, f"mismatch_{filename.replace('.csv', '.txt')}")
    if write_logfile:
        printf(f"writing signal consistency log into {file_path}")
        log = open(file_path, "w")

    indices = list()
    last_clk = None
    out_str = ""

    for (i1, r1), (i2, r2) in zip(decoded_df.iterrows(), decoded_df.iloc[1:].iterrows()):
        # flush the buffer as the CLK changed -> there's no more to accumulate
        if last_clk != r2['CK0'] and out_str != "":
            if write_logfile:
                # noinspection PyUnboundLocalVariable
                log.write(out_str + "\n")
            out_str = ""

        # ignore this iteration if there is a gap in time or the CLK changed in between
        if i2 != (i1 + 1) or r1['CK0'] != r2['CK0']:
            continue

        # now iterate over all csvfile_line of both rows
        for (k1, v1), (k2, v2) in zip(r1.iteritems(), r2.iteritems()):
            if k1 == "CK0" and ((v1 != v2) or (v1 == 0)):
                break
            if k1 in ["Time", "TimeNormalized"]:
                continue
            # this is an error we are interested in: the CLK stays 1 but one of the CA signals changed
            elif v1 != v2:
                out_str += "\n" if len(out_str) > 0 else ""
                out_str += f"[!] {r1['cmd']}: mismatch between rows ({i1},{i2}): ({k1}: {v1}) vs ({k2}: {v2})"
                # we only care about the signal consistency while the CLK is high
                if last_clk == 1:
                    indices.append(i2)

        last_clk = r2['CK0']

    # now we set column 'error' to 1 for each collected row index (as writing while iterating over the rows is bad)
    orig = pd.options.mode.chained_assignment
    pd.options.mode.chained_assignment = None
    decoded_df.loc[list(set(indices)), 'error_consistencyHigh'] = 1
    pd.options.mode.chained_assignment = orig

    if write_logfile:
        log.close()


def get_all_blocked_banks(bank_status: dict):
    return [k for k, v in bank_status.items() if v['status'] == BankStatus.BLOCKED]


def compute_t_last_ref(bank_status: dict, row: pd.Series, target_bk: str = None):
    banks = [target_bk] if target_bk is not None else list(bank_status.keys())
    result = list()
    for bk in banks:
        if bank_status[bk]['last_ref'] is None:
            continue
        result.append(row[column_TIME_NORMALIZED] - bank_status[bk]['last_ref'])
    return min(result) if len(result) > 0 else 0


def initialize_bank_status(bank_status: dict, dimm_cfg: dict):
    # check how many bits we need to represent the different banks
    nbits_lg = math.log2(dimm_cfg['num_banks_per_bankgroup'])
    # the result must always be a power-of-two, i.e., lg(X)
    assert (nbits_lg == math.ceil(nbits_lg))
    nbits = math.ceil(nbits_lg)

    # store for each bank the time of its last REF
    # - whenever a REFsb(x) happens, we update the timestamp of bank x;
    # - whenever a REFab happens, we update the timestamp of all banks
    # by default all banks are idle and just waiting to accept commands
    for target_bk in range(0, (2 ** nbits)):
        bank_status[f"{target_bk:0{nbits}b}"] = {
            'status': BankStatus.IDLE,
            'last_ref': None,
            'blocked_until': None,
            'blocking_cmd': None,
            'max_tick_age': None
        }


def preprocess_decode(dram_cmds: pd.DataFrame, parsed: pd.DataFrame) -> (pd.DataFrame, float, float):
    pandarallel.initialize(nb_workers=os.cpu_count() - 2, verbose=False)

    # update the timestamp to make it always increasing and start by 0
    # as we still use the original timestamp to check for tRFC, we do not overwrite it but add another column
    smallest = abs(parsed['Time'].min(axis=0))
    parsed.loc[:, column_TIME_NORMALIZED] = (parsed.loc[:, 'Time'] + smallest)

    printf(f"decoding signals to DRAM commands")

    # create a new column that we compute with apply/apply_parallel to determine the decoded command for each row
    # this ignores tRFC constraints, i.e., some commands must later be discarded

    # columns to consider for command decoding
    cols = ['CS', 'CA0', 'CA1', 'CA2', 'CA3', 'CA4', 'CA6', 'CA7', 'CA8', 'CA9', 'CA10', 'CA11', 'CA12']
    pd.options.mode.chained_assignment = None  # default='warn'
    parsed.loc[:, 'cmd'] = parsed[cols].parallel_apply(match_dram_cmd, axis=1, args=(lbl_dram_cmd_unknown, dram_cmds,))
    pd.options.mode.chained_assignment = 'warn'

    # FIXME add this again
    # remove all "unknown" commands
    # parsed = parsed.loc[parsed.loc[:, 'cmd'] != lbl_dram_cmd_unknown]

    return parsed


def get_sample_rate_pp(sr_int: int):
    sample_rates = [20_000_000_000, 10_000_000_000, 5_000_000_000, 2_500_000_000, 1_000_000_000, 1_000_000]
    output_strings = ['12.5 GS/s', '6.25 GS/s', '3.13 GS/s', '2.5 GS/s', '500 MS/s', None]
    for sr, out_str in zip(sample_rates, output_strings):
        if sr_int >= sr:
            return f"{sr_int} MS/s" if out_str is None else out_str
    return f"{sr_int} kS/s"  # default
