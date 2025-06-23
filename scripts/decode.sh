#!/usr/bin/env bash

export XMLDIG2CSV_PATH="$HOME/git/xmldig2csv-converter/xmldig2csv"
export XMLDIG_DIR="$1"
export DATA_DIR="${XMLDIG_DIR}/data"
PYTHON_BIN_DIR="../decoder/venv/bin"

for f in `find ${XMLDIG_DIR} -mindepth 1 -maxdepth 1 -type d -not -path './data' -exec basename {} \;`; do 
	"$PYTHON_BIN_DIR/python3" ../decoder/decode.py -e "$f"
done


