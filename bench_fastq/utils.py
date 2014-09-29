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
import matplotlib.pyplot as plt


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
    """Parse terminal output from bench_compress.sh

    Parse by filename, file size, compression method, compression ratio, compression and decompression speed.
    Note: This function is rigidly dependent upon bench_compress.sh.

    Parameters
    ----------
    fin : string
        Path to text file with terminal output.
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
            # Note: Typo in original script "Intial". Do not correct.
            elif line.startswith('Intial .fastq size:'):
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
                        # noinspection PyPep8
                        print(("WARNING: File size before and after compression test do not match.\n" +
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
        print("Writing parsed text to: {fout}".format(fout=fout))
        with open(fout, "wb") as fobj:
            json.dump(parsed_converted, fobj, indent=4, sort_keys=True)
    return parsed


def parsed_dict_to_df(parsed_dict):
    """Convert ``dict`` from parse_compress to ``pandas.dataframe``.
    
    Parameters
    ----------
    parsed_dict : dict
        ``dict`` of parsed terminal output.
    
    Returns
    -------
    parsed_df : pandas.dataframe
        ``pandas.dataframe`` with heirarchical index by filename, iteration,
        method, quantity.
    """
    # TODO: make recursive method, e.g. http://stackoverflow.com/questions/9538875/recursive-depth-of-python-dictionary
    filename_df_dict = {}
    for filename in parsed_dict:
        iteration_df_dict = {}
        for iteration in parsed_dict[filename]:
            method_df_dict = {}
            # Skip size_bytes for file since not a nested dict.
            if isinstance(parsed_dict[filename][iteration], dict):
                for method in parsed_dict[filename][iteration]:
                    method_df_dict[method] = pd.DataFrame.from_dict(parsed_dict[filename][iteration][method],
                                                                    orient='columns')
                iteration_df_dict[iteration] = pd.concat(method_df_dict, axis=1)
        filename_df_dict[filename] = pd.concat(iteration_df_dict, axis=1)
    parsed_df = pd.concat(filename_df_dict, axis=1)
    parsed_df.index.names = ['quantity']
    parsed_df.columns.names = ['filename', 'iteration', 'method', 'process']
    return parsed_df


def condense_parsed_df(parsed_df, parsed_dict):
    """Condense ``pandas.dataframe`` from parsed terminal output.
    
    Calculate compression/decompression rate in GB per minute and compression ratio, averaging over iterations and
    taking median of results.

    Parameters
    ----------
    parsed_df : pandas.DataFrame
        ``pandas.DataFrame`` from `parsed_dict_to_df`.
        Index name: quantity
        Heirarchical column names: filename, method, process, iteration
    parsed_dict : dict
        Nested ``dict`` from parse_compress.

    Returns
    -------
    condensed_df : pandas.DataFrame
        Heirarchical index names: method, process, quantity
        Column name: quantity

    See Also
    --------
    parsed_dict_to_df, parse_compress, reduce_condensed_df
    """
    # Calculate compression/decompression rate in GB per minute and compression ratio.
    # Drop quantities except for 'GB_per_minute' and 'compression_ratio'. Drop test files and incomplete tests.
    # Average over iterations. Take median of results.
    condensed_df = parsed_df.stack(['filename', 'method', 'process', 'iteration']).unstack('quantity').copy()
    condensed_df['elapsed_seconds'] = condensed_df['elapsed_time'].apply(
        lambda x: x.total_seconds() if isinstance(x, dt.timedelta) else x)
    condensed_df['elapsed_seconds'] = condensed_df['elapsed_seconds'].apply(lambda x: np.NaN if x == 0.0 else x)
    condensed_df['GB_per_minute'] = np.NaN
    condensed_df['compression_ratio'] = np.NaN
    # TODO: Use .values to vectorize
    for fname in condensed_df.index.levels[0].values:
        # TODO: remove SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame
        condensed_df.loc[fname, 'GB_per_minute'].update(
            (parsed_dict[fname]['size_bytes'] / condensed_df.loc[fname, 'elapsed_seconds']).multiply(60.0 / 1.0E9))
        condensed_df.loc[fname, 'compression_ratio'].update(
            condensed_df.loc[fname, 'size_bytes'].div(parsed_dict[fname]['size_bytes']))
    return condensed_df


def reduce_condensed_df(condensed_df):
    """Reduce ``pandas.DataFrame`` from `condense_parsed_df` by averaging over iterations and taking the median over
    file names.

    Parameters
    ----------
    condensed_df : pandas.DataFrame
        Heirarchical index names: method, process, quantity
        Column name: quantity

    Returns
    -------
    reduced_ser :  pandas.Series'
        ``pandas.Series`` from `condense_parsed_df`.
        Heirarchical index names: method, process, quantity

    See Also
    --------
    condense_parsed_df, plot_rate, plot_ratio
    """
    reduced_ser = condensed_df.stack().unstack(['filename', 'method', 'process', 'quantity']).mean()
    reduced_ser = reduced_ser.unstack(['method', 'process', 'quantity']).median()
    return reduced_ser


def plot_rate(reduced_ser, fout=None):
    """Plot processing rate vs compression method.

    Parameters
    ----------
    reduced_ser : pandas.Series
        ``pandas.Series`` from `reduce_condensed_df`.
        Heirarchical index names: method, process, quantity
    fout : {None}, string, optional
        Path to save plot as image. Extension must be supported by ``matplotlib.pyplot.savefig()``

    Returns
    -------
    None

    See Also
    --------
    reduce_condensed_df, plot_ratio
    """
    plt.figure()
    pd.DataFrame.plot(reduced_ser.unstack(['quantity'])['GB_per_minute'].unstack(['process']),
                      title="Processing rate vs compression method\nmedian results over all files",
                      sort_columns=True, kind='bar')
    legend = plt.legend(loc='best', title="Process")
    legend.get_texts()[0].set_text('Compress')
    legend.get_texts()[1].set_text('Decompress')
    xtick_labels = ('(bzip2, --fast)', '(fqz_comp, default)', '(gzip, --fast)', '(quip, default)')
    plt.xticks(xrange(len(xtick_labels)), xtick_labels, rotation=45)
    plt.xlabel("Compression method with options")
    plt.ylabel("Processing rate (GB per minute)")
    if fout is not None:
        print("Writing plot to: {fout}".format(fout=fout))
        plt.savefig(fout, bbox_inches='tight')
    plt.show()
    return None


def plot_ratio(reduced_ser, fout=None):
    """Plot compression ratio vs compression method.

    Parameters
    ----------
    reduced_ser : pandas.Series
        ``pandas.Series`` from `reduce_condensed_df`.
        Heirarchical index names: method, process, quantity
    fout : {None}, string, optional
        Path to save plot as image. Extension must be supported by ``matplotlib.pyplot.savefig()``

    Returns
    -------
    None

    See Also
    --------
    reduce_condensed_df, plot_rate
    """
    plt.figure()
    pd.Series.plot(reduced_ser.unstack(['quantity'])['compression_ratio'].unstack(['process'])['compress'],
                   title="Compression size ratio vs compression method\nmedian results over all files",
                   sort_columns=True, kind='bar')
    xtick_labels = ('(bzip2, --fast)', '(fqz_comp, default)', '(gzip, --fast)', '(quip, default)')
    plt.xticks(xrange(len(xtick_labels)), xtick_labels, rotation=45)
    plt.xlabel("Compression method with options")
    plt.ylabel("Compression size ratio\n(compressed size / decompressed size)")
    if fout is not None:
        print("Writing plot to: {fout}".format(fout=fout))
        plt.savefig(fout, bbox_inches='tight')
    plt.show()
    return None
