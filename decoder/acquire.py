#!/usr/bin/env python3

# This is the main script for making acquisition.

import argparse

from configuration.scope_setup import start_capture, stop_capture


# The main function.
def main():
    parser = argparse.ArgumentParser(
        description="Data acquisition script for TELEDYNE SDA series scope.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--start",
                        action="store_true",
                        help="capture digital data")

    parser.add_argument("--stop",
                        action="store_true",
                        help="stop capturing digital data")

    parser.add_argument("--trigger-mode",
                        help="choose one of {auto,normal,single,stopped}",
                        default="normal")

    config = vars(parser.parse_args())
    if config['start']:
        start_capture(config['trigger_mode'])
    elif config['stop']:
        stop_capture()


if __name__ == "__main__":
    main()
