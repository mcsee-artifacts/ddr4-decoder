import datetime
import os
import inspect
import os.path


def get_caller_info():
    # first get the full filename (including path and file extension)
    caller_frame = inspect.stack()[1]
    caller_filename_full = caller_frame.filename

    # now get rid of the directory (via basename)
    # then split filename and extension (via splitext)
    caller_filename_only = os.path.splitext(os.path.basename(caller_filename_full))[0]

    # return both filename versions as tuple
    return caller_filename_full, caller_filename_only


def print_debug(*args):
    if 'DEBUG' in os.environ and int(os.getenv('DEBUG')) == 1:
        print("[DEBUG]", *args)


def checkenv(env_var: str, verbose: bool = False):
    if f"{env_var}" not in os.environ:
        raise Exception(f"[-] The env variable '{env_var}' must be defined.")
    elif verbose:
        print(f'[+] found env variable: {env_var}={os.getenv(env_var)}')


def printf(*args):
    fn, _ = get_caller_info()
    fn = fn.split('/')[-1]
    now = str(datetime.datetime.now()).split(' ')[1]
    print('\033[1;35m', f"[{fn}|{now}] ", '\033[0;0m', *args, sep='')
