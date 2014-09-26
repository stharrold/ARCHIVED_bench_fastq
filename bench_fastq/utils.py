#!/usr/bin/env python
"""Utils to parse the terminal output from bench_compress.sh
"""


from __future__ import print_function, division, absolute_import
import os
import sys
import json
import datetime as dt
import numpy as np
import pandas as pd


def parse_elapsed(elapsed):
    """Parse string of elapsed time from output of Unix 'time' command into
    `datetime.timedelta`.

    Parameters
    ----------
    elapsed : string
        Elapsed time field output from Unix 'time' command.
        Format: [HH:]MM:SS[.SSS]

    Returns
    -------
    elapsed_dt : datetime.timedelta
        Elapsed time as ``datetime.timedelta``.
    """
    elapsed_arr = elapsed.split(':')
    if len(elapsed_arr) == 2:
        hours = '0'
        [minutes, seconds] = elapsed_arr
    elif len(elapsed_arr) == 3:
        [hours, minutes, seconds] = elapsed_arr
    else:
        raise AssertionError(("Program error. Elapsed time does not have 2 or 3 fields:\n" +
                              "{ea}").format(ea=elapsed_arr))
    hours_int = int(float(hours))
    minutes_int = int(float(minutes))
    seconds_int = int(float(seconds))
    milliseconds_int = int((float(seconds) - seconds_int) / 0.001)
    elapsed_dt = dt.timedelta(hours=hours_int,
                              minutes=minutes_int,
                              seconds=seconds_int,
                              milliseconds=milliseconds_int)
    return elapsed_dt


def recursive_timedelta_to_totsec(dobj):
    """Recursively convert ``datetime.timedelta`` elements to total seconds
    in a ``dict``.

    Call this function before writing the ``dict`` to JSON.

    Parameters
    ----------
    dobj : dict
        ``dict`` that may contain ``datetime.timedelta`` elements. ``dict`` may
        be nested.

    Returns
    -------
    dobj_converted : dict
        ``dict`` with ``datetime.timedelta`` elements converted to
        total seconds.
    """
    dobj_converted = {}
    for key in dobj:
        if isinstance(dobj[key], dt.timedelta):
            dobj_converted[key] = dobj[key].total_seconds()
        elif isinstance(dobj[key], dict):
            dobj_converted[key] = recursive_timedelta_to_totsec(dobj=dobj[key])
        else:
            dobj_converted[key] = dobj[key]
    return dobj_converted


def parse_compress(fin, fout=None):
    """Parse terminal output from bench_comress.sh

    Parse by filemname, file size, compression method, compresion ratio,
    compresion and decompression speed. Note: This function is rigidly
    dependent upon bench_compress.sh.

    Parameters
    ----------
    fin : string
        Path to text file with terinal output.
    fout : {None}, string, optional
        Path to output .json file of parsed terminal output.

    Returns
    -------
    parsed : dict
        ``dict`` of parsed terminal output.
    """
    # Check input.
    fpath = os.path.abspath(fin)
    if not os.path.isfile(fpath):
        raise IOError("File does not exist:\n{fpath}".format(fpath=fpath))
    if fout is not None:
        if not os.path.splitext(fout)[1] == '.json':
            raise IOError(("File extension is not '.json':\n" +
                           "{fout}").format(fout=fout))
    # Parse text file into dict.
    parsed = {}
    skip_lines = None
    catch_initial_size = None
    catch_comp_cmd = None
    catch_comp_time = None
    catch_comp_size = None
    catch_decomp_cmd = None
    catch_decomp_time = None
    catch_decomp_size = None
    with open(fpath, 'rb') as fobj:
        for line in fobj:
            line = line.rstrip()
            if line.startswith('Begin processing:'):
                line_arr = line.split(':')
                fname = os.path.splitext(os.path.basename(line_arr[1]))[0]
                parsed[fname] = {}
                continue
            elif line == 'Intial .fastq size:':
                catch_initial_size = True
                skip_lines = 1
                continue
            elif catch_initial_size and skip_lines >= 0:
                if skip_lines > 0:
                    skip_lines -= 1
                    continue
                elif skip_lines == 0:
                    line_arr = line.split()
                    parsed[fname]['size_bytes'] = int(line_arr[0])
                    assert os.path.basename(line_arr[1]) == fname
                    catch_initial_size = False
                    skip_lines = None
                    continue
            elif line.startswith('Iteration:'):
                line_arr = line.split(':')
                iteration = int(line_arr[1])
                parsed[fname][iteration] = {}
                continue
            elif line.startswith('Testing'):
                line_arr = line.rstrip(':').split()
                method = line_arr[1]
                parsed[fname][iteration][method] = {}
                catch_comp_cmd = True
                continue
            elif catch_comp_cmd and line.startswith('+ sudo time'):
                parsed[fname][iteration][method]['compress'] = {}
                parsed[fname][iteration][method]['compress']['command'] = line
                catch_comp_cmd = False
                catch_comp_time = True
                continue
            elif catch_comp_time and ('elapsed' in line) and ('CPU' in line):
                line_arr = line.split()
                elapsed = parse_elapsed(elapsed=line_arr[2].strip('elapsed'))
                parsed[fname][iteration][method]['compress']['elapsed_time'] = elapsed
                pct_cpu = line_arr[3].strip('%CPU')
                if pct_cpu == '?':
                    pct_cpu = np.NaN
                else:
                    pct_cpu = float(pct_cpu)
                parsed[fname][iteration][method]['compress']['CPU_percent'] = pct_cpu
                catch_comp_time = False
                catch_comp_size = True
                continue
            elif catch_comp_size:
                if line.startswith('+ du --bytes'):
                    skip_lines = 0
                    continue
                elif skip_lines == 0:
                    line_arr = line.split()
                    parsed[fname][iteration][method]['compress']['size_bytes'] = int(line_arr[0])
                    catch_comp_size = False
                    skip_lines = None
                    catch_decomp_cmd = True
                    continue
            elif catch_decomp_cmd and line.startswith('+ sudo time'):
                parsed[fname][iteration][method]['decompress'] = {}
                parsed[fname][iteration][method]['decompress']['command'] = line
                catch_decomp_cmd = False
                catch_decomp_time = True
                continue
            elif catch_decomp_time and ('elapsed' in line) and ('CPU' in line):
                line_arr = line.split()
                elapsed = parse_elapsed(elapsed=line_arr[2].strip('elapsed'))
                parsed[fname][iteration][method]['decompress']['elapsed_time'] = elapsed
                pct_cpu = line_arr[3].strip('%CPU')
                if pct_cpu == '?':
                    pct_cpu = np.NaN
                else:
                    pct_cpu = float(pct_cpu)
                parsed[fname][iteration][method]['decompress']['CPU_percent'] = pct_cpu
                catch_decomp_time = False
                catch_decomp_size = True
                continue
            elif catch_decomp_size:
                if line.startswith('+ du --bytes'):
                    skip_lines = 0
                    continue
                elif skip_lines == 0:
                    line_arr = line.split()
                    parsed[fname][iteration][method]['decompress']['size_bytes'] = int(line_arr[0])
                    if parsed[fname]['size_bytes'] != parsed[fname][iteration][method]['decompress']['size_bytes']:
                        print(("WARNING: File size before and after compresion test do not match.\n" +
                               "file name = {fname}\n" +
                               "method = {method}\n" +
                               "initial size (bytes) = {init_size}\n" +
                               "final size (bytes) = {finl_size}").format(fname=fname, method=method,
                                                                          init_size=parsed[fname]['size_bytes'],
                                                                          finl_size=parsed[fname][iteration][method]['decompress']['size_bytes']),
                              file=sys.stderr)
                    catch_decomp_size = False
                    skip_lines = None
                    continue
    # Write out dict as JSON.
    if fout is not None:
        parsed_converted = recursive_timedelta_to_totsec(dobj=parsed)
        with open(fout, "wb") as fobj:
            json.dump(parsed_converted, fobj, indent=4, sort_keys=True)
    return parsed


def parsed_dict_to_df(parsed):
    """Convert ``dict`` from parse_compress to ``pandas.dataframe``.
    
    Parameters
    ----------
    parsed : dict
        ``dict`` of parsed terminal output.
    
    Returns
    -------
    parsed_df : pandas.dataframe
        ``pandas.dataframe`` with heirarchical index by filename, iteration,
        method, quantity.
    """
    # TODO: make into recursive method, e.g. http://stackoverflow.com/questions/9538875/recursive-depth-of-python-dictionary
    filename_df_dict = {}
    for filename in parsed:
        iteration_df_dict = {}
        for iteration in parsed[filename]:
            method_df_dict = {}
            # Skip size_bytes for file.
            if isinstance(parsed[filename][iteration], dict):
                for method in parsed[filename][iteration]:
                    compress_df_dict = {}
                    for compress in parsed[filename][iteration][method]:
                        if isinstance(parsed[filename][iteration][method][compress], dict):
                            compress_df_dict[compress] = pd.DataFrame.from_dict(parsed[filename][iteration][method][compress], orient='index')
                    method_df_dict[method] = pd.concat(compress_df_dict, axis=0)
                iteration_df_dict[iteration] = pd.concat(method_df_dict, axis=0)
        filename_df_dict[filename] = pd.concat(iteration_df_dict, axis=0)
    parsed_df = pd.concat(filename_df_dict, axis=0)
    parsed_df.index.names = ['filename', 'iteration', 'method', 'compress', 'quantity']
    parsed_df.columns = ['value']
    return parsed_df
