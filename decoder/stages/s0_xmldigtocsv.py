from multiprocessing import Pool
from pathlib import PurePath, Path
import time
from util.py_helper import checkenv, printf
import glob
import itertools
import os
import shutil
import subprocess


# Returns the output directory of this stage for a given iteration name.
# This is required by the subsequent stage.
def get_output_directory(iter_name: str):
    return Path(os.getenv("DATA_DIR")) / "trimmedcsv" / iter_name


# Run xmldig2csv for a single file.
# @param exp_name the name of the experiment, typically a timestamp followed by a random string.
def __xmldigtocsv_single(experimentname: str, xmldig_path: str) -> None:
    checkenv('DATA_DIR')
    checkenv('XMLDIG2CSV_PATH')

    # Compute the output path and create the parent dir if necessary
    basename = os.path.basename(xmldig_path)
    outpath = os.path.join(os.getenv('DATA_DIR'), 'trimmedcsv', experimentname,
                           '.'.join(os.path.basename(xmldig_path).split('.')[:-1]) + '.csv')
    Path(os.path.dirname(outpath)).mkdir(parents=True, exist_ok=True)

    # Check existence of the output path
    if os.path.exists(outpath):
        printf(f"skipping file {basename} as it has already been converted before")
        return

    # Do the conversion
    # printf(f"transforming file {basename} into {basename.replace('.XMLdig', '.csv')}")
    subprocess.run([os.getenv('XMLDIG2CSV_PATH'), xmldig_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)

    # Move the fresh CSV files to the correct place
    shutil.move(xmldig_path.replace(".XMLdig", ".csv"), outpath)


# Requires the XMLDIG_DIR and DATA_DIR env variables
# @param exp_name the name of the experiment, typically a timestamp followed by a random string.
def xmldigtocsv_all(experimentname: str, numworkers: int) -> None:
    t_start = time.time()
    checkenv('DATA_DIR')
    checkenv('XMLDIG_DIR')
    
    xmldigdirpath = os.path.join(os.getenv('XMLDIG_DIR'), experimentname)  # TODO Verify that the path is correct
    # Check that the input file exists.
    if not os.path.isdir(xmldigdirpath):
        raise Exception(f'[-] given XMLDIG path {xmldigdirpath} does not exist!')

    # Find the paths to all the single xmldigs
    all_xmldig_paths = glob.glob(str(PurePath(xmldigdirpath, "*.XMLdig")))

    # Run in parallel
    with Pool(numworkers) as p:
        p.starmap(__xmldigtocsv_single, zip(itertools.repeat(experimentname), all_xmldig_paths))
    
    t_end = time.time()
    printf(f"xmldig2csv done for all {len(all_xmldig_paths)} file(s) in {t_end - t_start:.3f} seconds.")
