#!/usr/bin/env python3.9

# This is the main script for setting up the scope.

import argparse
import os

from configuration.scope_setup import *
from configuration.dimm import extract_dimm_id_from_directoryname, get_dimm_configuration


# The main function.
def main():
    parser = argparse.ArgumentParser(
        description="Data acquisition and analysis script for TELEDYNE SDA series scope.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # program mode: configure devices for data acquisition
    parser.add_argument("-z", "--configuration",
                        type=int,
                        nargs=1,
                        help="configuration number for setting up the device")
    parser.add_argument("-ddr", "--setup-ddr",
                        action="store_true",
                        help="set up the DDR debug toolkit")
    parser.add_argument("-d", "--directory",
                        type=str,
                        nargs=1,
                        help="a suffix for the output directory")
    parser.add_argument("-s", "--setup-file",
                        type=str,
                        help="path to a scope setup file (.lss)")
    parser.add_argument("--dimm-config-dir",
                        type=str,
                        help="path to the JSON data directory of pcddr5-info scripts")

    config = vars(parser.parse_args())
    if config['setup_file']:
        instr = connect()

        # reset the device to make sure that there are no leftover settings when loading the setup file
        # reset_device(instr)

        load_setup_file(config['setup_file'], instr)
        setup_aux_trigger(instr)
        configure_autosave(instr, "R:\\")
    else:
        # use commands to configure the device from scratch
        cfg_no = 0 if (v := config['configuration']) is None else v
        scope_cfg = get_scope_configuration(cfg_no)
        if not config['directory']:
            parser.error("[-] parameter [-d|--directory] is needed!")
            exit(os.EX_USAGE)
        instr = connect()
        setup(instr, scope_cfg, config['directory'][0], False)

        # if we use the TELEDYNE DDR5 decoder we need information about the DIMM's frequency and the read/write latency
        if config['setup_ddr']:
            # load DIMM-specific details
            dimm_id = extract_dimm_id_from_directoryname(config) if not (d := config['dimm_id']) else int(d)
            printf(f"detected DIMM ID: ", dimm_id)
            dimm_config = get_dimm_configuration(dimm_id, config['dimm_config_dir'])
            setup_ddr_option(instr, config['directory'][0], dimm_config)
        save_setup_file(config['directory'][0], instr)


if __name__ == "__main__":
    main()
