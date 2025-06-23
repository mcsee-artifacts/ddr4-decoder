#!/usr/bin/env bash

# echo "processing dir $1"

export XMLDIG2CSV_PATH="$HOME/git/xmldig2csv-converter/xmldig2csv"
export XMLDIG_DIR="$(realpath "$1")"
export DATA_DIR="${XMLDIG_DIR}/data"

# enable to see print_debug messages
#export DEBUG="1"

cd "$HOME/git/teledyne-scope/decoder"
source ../decoder/venv/bin/activate
python3 ../decoder/decode.py -e .

