import glob
import json
import os
import re

from util.py_helper import printf
from util.units import Units


def extract_dimm_id_from_directoryname(config: dict):
    file_filter = '*.XMLdig'
    files = glob.glob(os.path.join(config['input'][0], file_filter))
    if len(files) < 1:
        printf(f"could not determine DIMM ID from input files (no {file_filter} files found)")
        exit(os.EX_USAGE)

    first_hit = files[0]
    dimm_id_confstr = "dimmId"
    if dimm_id_confstr not in first_hit:
        printf(f"could not determine DIMM ID from input files (no matches to dimmId=NUMBER)")
        exit(os.EX_USAGE)

    dimm_id_match = re.search(f"{dimm_id_confstr}=(\\d*)", first_hit)
    if dimm_id_match is None or len(dimm_id_match.group(0)) < 1:
        printf(f"could not determine DIMM ID from input files (no matches to dimmId=NUMBER)")
        exit(os.EX_USAGE)

    dimm_id_val = int(dimm_id_match.group(1))
    printf(f"detected DIMM ID {dimm_id_val} from given data files")

    if dimm_id_val < 500:
        printf(f"DIMM ID is smaller than 500: are you sure that's a DDR5 DIMM?")
        exit(-1)

    return dimm_id_val


def get_dimm_configuration(dimm_id: int, dimm_cfg_dir: str) -> dict:
    # consume JSON generated by SPD reader here and create dict out of it
    dimm_cfg_glob_pattern = os.path.join(dimm_cfg_dir, f"{dimm_id}_*")
    output_dict = dict()
    try:
        dimm_cfg_filepath = next(glob.iglob(dimm_cfg_glob_pattern))
        output_dict = json.load(open(dimm_cfg_filepath, "r"))
    except StopIteration:
        printf(f"could not find DRAM configuration file using glob pattern {dimm_cfg_glob_pattern}")
        exit(-1)

    u = Units()
    # We now assume that FGR is something static, but it could be that the device switches between normal REFs
    # and FGR in which case we would need to detect whether FGR is enabled dynamically;
    # maybe we can increase the operating temperature to force the system to go into FGR and then try to learn how
    # it looks like when the device is in FGR (e.g., less time between consecutive REFs)
    output_dict['dimm_id'] = dimm_id
    dimm_fgr = {
        504: True,
        513: True
    }

    # tck_avg_min allows us to determine which speed the device supports
    tckminPs_speedMhz = {
        625: "3200",
        555: "3600",
        500: "4000",
        454: "4400",
        416: "4800",
        384: "5200",
        357: "5600",
        333: "6000",
        312: "6400"
    }
    output_dict['speedgrade'] = tckminPs_speedMhz[int(output_dict['tckavg_min'])]

    # fail if we lack information for this DIMM
    if dimm_id not in dimm_fgr:
        printf(f"given DIMM ID {dimm_id} was not found in dimm_fgr")
        exit(os.EX_CONFIG)

    # build the result, the dimm_cfg dictionary
    output_dict['fgr'] = dimm_fgr[dimm_id]

    # database of all possible tRFC csvfile_line (in seconds) according to the DDR5 standard
    t_rfc_db_sec = {
        'tRFC1': {8: u.ns_to_sec_val(195), 16: u.ns_to_sec_val(295)},  # REFab
        'tRFC2': {8: u.ns_to_sec_val(130), 16: u.ns_to_sec_val(160)},  # REFab FGR
        'tRFCsb': {8: u.ns_to_sec_val(115), 16: u.ns_to_sec_val(130)},  # REFsb
    }

    # the refresh rate (tREFI) for normal operation temperature (0 <= TCASE <= 85°C), see JESD79-5, page 156
    t_refi_db_sec = {
        'REFab': {
            # no FGR
            0: {
                'temp_std': u.ns_to_sec_val(3900),
                'temp_high': u.ns_to_sec_val(1950),
            },
            # FGR
            1: {
                'temp_std': u.ns_to_sec_val(1950),
                'temp_high': u.ns_to_sec_val(975),
            }
        },
        # always FGR because *sb commands not supported in normal REF mode
        'REFsb': {
            'temp_std': u.ns_to_sec_val(1950 / output_dict['num_banks_per_bankgroup']),
            'temp_high': u.ns_to_sec_val(975 / output_dict['num_banks_per_bankgroup']),
        }
    }

    # decide which is the correct tRFC value
    device_size = output_dict['total_size_gb']
    fgr_mode_en = output_dict['fgr']
    if 'fgr' in output_dict:
        output_dict['t_rfc'] = t_rfc_db_sec['tRFC2'][device_size]
        output_dict['t_rfc_sb'] = t_rfc_db_sec['tRFCsb'][device_size]
        output_dict['t_refi_refab'] = t_refi_db_sec['REFab'][fgr_mode_en]
        output_dict['t_refi_refsb'] = t_refi_db_sec['REFsb']
    else:
        output_dict['t_rfc'] = t_rfc_db_sec['tRFC1'][device_size]
        output_dict['t_refi_refab'] = t_refi_db_sec['REFab'][fgr_mode_en]

    return output_dict
