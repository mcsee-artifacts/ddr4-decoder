#!/usr/bin/env bash

FOLDER="$1"
export XMLDIG2CSV_PATH="$HOME/git/xmldig2csv-converter/xmldig2csv"
export XMLDIG_DIR="${FOLDER%/}"
export DATA_DIR="${XMLDIG_DIR}/data"
PYTHON_BIN_DIR="../decoder/venv/bin"

# find "${XMLDIG_DIR}" -maxdepth 1 -type d -iname "it=*" -printf "%f\n" \
# 	| parallel --jobs 64 NUM_WORKERS=6 "$PYTHON_BIN_DIR/python3" ../decoder/decode.py -e `basename {}`
#
# find "${XMLDIG_DIR}" -maxdepth 2 -type f -iname "trace--00000.XMLdig" \
# 	| cut -d/ -f5 \
# 	| parallel --jobs 64 NUM_WORKERS=6 "$PYTHON_BIN_DIR/python3" ../decoder/decode.py -e {}
#
# find "${XMLDIG_DIR}" -maxdepth 1 -iname "it=*" -type d \
# 	| parallel --jobs 64 NUM_WORKERS=6 "$PYTHON_BIN_DIR/python3" ../decoder/decode.py -e {}

find "${XMLDIG_DIR}" -maxdepth 1 -iname "it=*" -type d | \
	rev | cut -d/ -f1 | rev | \
	parallel --jobs 16 NUM_WORKERS=6 "$PYTHON_BIN_DIR/python3 ../decoder/decode.py --ddr4 -e {}"
