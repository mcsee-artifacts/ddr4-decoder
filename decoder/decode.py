#!/usr/bin/env python3.9

# This is the main script for making decoding.

import argparse
import multiprocessing
import os

from stages.s0_xmldigtocsv import xmldigtocsv_all
from stages.s2_decode import decode_all
from stages.s3_analyze import analyze_all
from util.dram_command import E_DRAM_TYPE
from util.py_helper import printf

# The main function.
def main():
    parser = argparse.ArgumentParser(
        description="Data acquisition and analysis script for TELEDYNE SDA series scope.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--dimm-config-dir",
                        type=str,
                        help="the path to the JSON data directory of pcddr5-info scripts")
    parser.add_argument("-id", "--dimm-id",
                        type=str,
                        help="the internal DIMM ID")
    parser.add_argument("-e", '--expname',
                        type=str,
                        required=True,
                        help='the experiment name, i.e., folder name in the XMLDIG_DIR directory; e.g.: '
                             '20220919_155000_decoder_test_newScope')
    parser.add_argument("-o", "--out-file",
                        default=None,
                        type=str,
                        help="the file to write the decoder log into")
    parser.add_argument("--ddr4",
                        action="store_true",
                        help="use DDR4 mode (default: DDR5 mode)")

    # TODO: Maybe support, and check which ones are not used anymore
    # parser.add_argument("-csv", "--write-csv",
    #                     action="store_true",
    #                     help="path to write the decoder log to")

    # parser.add_argument("-pkl", "--write-pickle",
    #                     action="store_true",
    #                     help="whether to serialize the decoded trace into a Pickle file")

    # parser.add_argument("-ip", "--ignore-pickle",
    #                     action="store_true",
    #                     help="forces using raw data (CSV) rather than loading the previously computed pickle file,"
    #                          " overwrites the existing pickle file afterwards")

    # parse arguments and create dict of argparse's Namespace object
    config = vars(parser.parse_args())

    ###############################
    # Set up variables for storage and parallelism
    ###############################

    if 'DATA_DIR' not in os.environ:
        if 'XMLDIG_DIR' in os.environ:
            data_dir = os.path.join(os.getenv('XMLDIG_DIR'), config['expname'], 'data')
            os.environ['DATA_DIR'] = data_dir
            printf(f"env variable DATA_DIR not found, using DATA_DIR={data_dir}")
        else:
            raise Exception('[-] The DATA_DIR env variable or/and XMLDIG_DIR env variable must be defined.')

    # Determine the wished number of workers. If none is specified, then one per logical core.
    num_workers = int(os.getenv("NUM_WORKERS")) if "NUM_WORKERS" in os.environ else multiprocessing.cpu_count()
    printf(f"using {num_workers} workers")
    
    # Experiment name
    # the experiment name is simply a dot if we use the decode_one.sh script where we only want to decode
    # a single experiment rather than a batch of experiments
    exp_name = config['expname']
    if config['expname'] == ".":
        exp_name = ""
        exp_name_desc = os.path.dirname(os.getenv('XMLDIG_DIR')).replace("/mnt/scope-data/", "")
        printf(f"decoding experiment: {exp_name_desc}")
    else:
        printf(f"decoding experiment: {exp_name}")


    ###############################
    # Run the pipeline
    ###############################

    # TODO: Reintegrate this
    # if config['analyze']:
    #     for inp_path in config['input']:
    #         if not os.path.isdir(inp_path) and not os.path.exists(inp_path):
    #             printf(f"given input path {inp_path} does not exist!")
    #             exit(-1)
    #         analyze_trace(inp_path, '*.csv', dimm_config,
    #                       config.get('out_file', None),
    #                       config.get('ignore_pickle', False),
    #                       config.get('write_csv', False),
    #                       config.get('write_pickle', False))

    # First, transform XMLdig to CSV.
    xmldigtocsv_all(exp_name, num_workers)

    # Second, do nothing. This stage has been merged into the xmldig2csv tool.

    # Third, decode the DRAM commands.
    dram_type = E_DRAM_TYPE.ddr4 if config["ddr4"] else E_DRAM_TYPE.ddr5
    decode_all(dram_type, exp_name, num_workers)

    # Fourth, run an analysis (not for DDR4 mode)
    if not config["ddr4"]:
        analyze_all(exp_name, num_workers)


if __name__ == "__main__":
    main()
