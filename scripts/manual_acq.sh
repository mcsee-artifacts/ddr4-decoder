#!/usr/bin/env bash

EXP_HOST="ee-tik-cn115"
DIMM_ID=502

ssh root@172.31.200.250 "rm -rf /mnt/r/*.XMLdig"

pushd $HOME/git/teledyne-scope
source decoder/venv/bin/activate

cd decoder

# ask to start acq
echo -n "Start scope acquisition in AUTO mode now? [Y/n]: "
read -n 2
echo ""

if [[ "$REPLY" == "n" ]]; then
  exit 0
fi

# start scope acquisition (AUTO mode)
python3 acquire.py --start --trigger-mode AUTO 1>/dev/null

# wait for user input before stopping
echo "Press any key to stop acquisition..."
read -n 1

# stop scope acquisition
./acquire.py --stop 

# create target directory
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
TARGET_DIR="/data/projects/ddr5-scope-data/${TIMESTAMP}_${EXP_HOST}_DIMM=${DIMM_ID}_manual_acquisition"
mkdir -p ${TARGET_DIR}

# copy files from scope to shared drive
rsync -avz root@172.31.200.250:/mnt/r/*.XMLdig "${TARGET_DIR}/"

# decode data
cd ../scripts
./decode_one.sh "${TARGET_DIR}/"

# plot rows
cd ../plotting
for f in ${TARGET_DIR}/data/decoded/*.csv;
do 
   python3 plot_rows.py $f
done

popd
