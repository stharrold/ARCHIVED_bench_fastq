#!/usr/bin/env python
"""Utils to parse the terminal output from bench_compress.sh
"""


from __future__ import print_function, division, absolute_import
import os
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


def recursive_dt_to_totsec(dobj):
    """TODO
    """
    pass


def parse_compress(fin, fout=None):
    """Parse terminal output from bench_comress.sh

    Parse by filemname, file size, compression method, compresion ratio,
    compresion and decompression speed.

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
            elif catch_initial_size:
                if skip_lines > 0:
                    skip_lines -= 1
                    continue
                else:
                    line_arr = line.split()
                    parsed[fname]['size_bytes'] = int(line_arr[0])
                    assert os.path.basename(line_arr[1]) == fname
                    catch_initial_size = False
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
                catch_comp_time = True
                catch_comp_size = True
                catch_decomp_cmd = True
                catch_decomp_time = True
                catch_decomp_size = True
                continue
            elif catch_comp_cmd and line.startswith('+ sudo time'):
                parsed[fname][iteration][method]['command'] = line
                catch_comp_cmd = False
                continue
            elif catch_comp_time and ('elapsed' in line) and ('CPU' in line):
                line_arr = line.split()
                elapsed = parse_elapsed(elapsed=line_arr[2].strip('elapsed'))
                parsed[fname][iteration][method]['comp_time'] = elapsed
                pct_cpu = line_arr[3].strip('%CPU')
                if pct_cpu == '?':
                    pct_cpu = np.NaN
                else:
                    pct_cpu = float(pct_cpu)
                parsed[fname][iteration][method]['comp_cpu'] = pct_cpu
                catch_comp_time = False
    # Write out dict as json.
    if fout is not None:
        for key in parsed:
            if isinstance
        with open(fout, "wb") as fobj:
            json.dump(parsed, fobj, indent=4, sort_keys=True)
    return parsed
