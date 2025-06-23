#!/bin/bash

shopt -s extglob

DIR=`find /Volumes/scope-data -mindepth 1 -maxdepth 1 -type d | sort -nr | head -1`
echo "Using DIR=$DIR"

pushd $DIR

FN=`echo ${DIR}/data/decoded/*/trace.csv`
echo "Using FN=$FN"

echo "ACT"
cat $FN | grep -E "(act)" | cut -d',' -f 3-5 | sort -nr | uniq -c | sort -t' ' -k 1

echo "WR|WRA"
cat $FN | grep -E "(wr|wra)" | cut -d',' -f3-5,6 | sort -n | uniq -c | sort -t' ' -k 1

echo "RD|RDA"
cat $FN | grep -E "(rd|rda)" | cut -d',' -f3-5,6 | sort -n | uniq -c | sort -t' ' -k 1

popd
