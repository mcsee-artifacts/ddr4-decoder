from pathlib import Path


# Returns a list of tuples (in_file, out_file).
def get_input_and_output_file_paths(in_dir: Path, out_dir: Path):
    in_files = list(in_dir.iterdir())
    out_files = [out_dir / in_file.name for in_file in in_files]
    return list(zip(in_files, out_files))
