#!/usr/bin/env python3
# license: public domain
# author: caio begotti

import csv
import json
import os
import sys
from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import CubicSpline

# constants
KP_THRESHOLD = 5  # threshold for kp index to highlight
CACHE_DIR = './cache'  # directory to store cached data
SUNSPOT_FILE = f'{CACHE_DIR}/SN_y_tot_V2.0.csv'  # path to the sunspot csv file

# ensure the cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# function to handle logging, respects --quiet flag
def log(message, quiet=False):
    if not quiet:
        print(message)

# load kp index data from a local json file or fetch from api if not cached
def load_or_fetch_kp_index(year, quiet=False):
    cache_file = f'{CACHE_DIR}/kp_index_{year}.json'

    # check if the year is in the future
    current_year = datetime.now().year
    if year > current_year:
        log(f"Year {year} not supported by data or not current", quiet)
        sys.exit(1)

    # check if cache file exists
    if os.path.exists(cache_file):
        log(f"Loading Kp index data for {year} from cache", quiet)
        with open(cache_file, 'r') as f:
            data = json.load(f)
            times = [datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ') for t in data['times']]
            kp_index = data['kp_index']
            return times, kp_index
    else:
        try:
            # fetch kp index data from the api
            log(f"Fetching Kp index data for {year} from the API", quiet)
            start_date = f'{year}-01-01'
            end_date = f'{year}-12-31'

            # get kp index data using the external script
            times, kp_index, status = getKpindex(start_date, end_date, 'Kp', 'def')

            # convert time strings to datetime objects
            times = [datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ') for t in times]

            # save the data to the cache file
            with open(cache_file, 'w') as f:
                json.dump({'times': [t.strftime('%Y-%m-%dT%H:%M:%SZ') for t in times], 'kp_index': kp_index}, f)

            return times, kp_index
        except NameError:
            log(f"Year {year} not supported by data or not current", quiet)
            sys.exit(1)

# load sunspot data for a range of years from the csv file
def load_sunspot_data(start_year, end_year, quiet=False):
    if not os.path.exists(SUNSPOT_FILE):
        log(f"Sunspot data file not found: {SUNSPOT_FILE}", quiet)
        return None

    sunspot_data = {}
    # read the csv file without skipping the header (since it's crude and headerless)
    with open(SUNSPOT_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')

        for row in reader:
            row_year = float(row[0])  # use float to capture the `.5`
            int_year = int(row_year)  # convert to integer to ignore the `.5`
            if start_year <= int_year <= end_year:
                sunspot_value = float(row[1])  # second column is the sunspot value
                sunspot_data[int_year] = sunspot_value

    return sunspot_data

# plot kp index for a specific year with local cache support and overlay sunspot data
def plot_kp_index_for_year(year, quiet=False, clean=False):
    # load or fetch kp index data
    times, kp_index = load_or_fetch_kp_index(year, quiet)

    # debugging: print the retrieved data length
    log(f"Retrieved {len(times)} entries for year {year}", quiet)

    # load sunspot data for the current year, the previous 5 years, and the next year
    start_year = year - 5
    prev_year = year - 1  # fetch the previous year's value
    next_year = year + 1  # fetch the next year's value
    sunspot_data = load_sunspot_data(start_year, next_year, quiet)

    # handle missing sunspot data
    if not sunspot_data:
        log("Sunspot data not available, skipping sunspot plot.", quiet)
        sunspot_data = {}  # set to an empty dictionary to avoid future errors

    # find the last available year for sunspot data
    last_available_year = max(sunspot_data.keys(), default=None)

    if last_available_year and last_available_year < year:
        log(f"Sunspot data only available up to {last_available_year}", quiet)
    else:
        last_available_year = year  # use the current year if data exists for it

    # get the sunspot values in the range [start_year, last_available_year]
    sunspot_years = [yr for yr in range(start_year, last_available_year + 1) if yr in sunspot_data]  # only use years with data
    sunspot_values = [sunspot_data.get(yr) for yr in sunspot_years]  # skip years without sunspot data

    # log sunspot data for the previous year (if available)
    if prev_year in sunspot_data:
        log(f"Previous year sunspot: {sunspot_data[prev_year]}", quiet)

    # output sunspot value for logging (only if available for the current year)
    if year in sunspot_data:
        log(f"Sunspot value for {year}: {sunspot_data[year]}", quiet)

    # handle next year's sunspot value with fallback to the current year if missing
    if last_available_year == year:
        next_year_sunspot = sunspot_data.get(next_year, sunspot_data.get(year, None))
        if next_year_sunspot:
            log(f"Next year sunspot: {next_year_sunspot}", quiet)

    # use cubic spline interpolation for a smooth transition between sunspot values (if data exists)
    if sunspot_years and sunspot_values:
        cubic_spline = CubicSpline(np.linspace(0, len(times) - 1, len(sunspot_values)), sunspot_values)
        sunspot_curve_y = cubic_spline(np.linspace(0, len(times) - 1, len(times)))
    else:
        sunspot_curve_y = None  # no sunspot data to plot

    # prepare a figure with increased size for better visibility
    plt.figure(figsize=(20, 10))  # larger figure size

    # plot all kp index values (line) in light gray
    plt.plot(times, kp_index, color='#dddddd', linewidth=0.5)  # base line in light gray

    # highlight values above threshold in blue and mark them with red dashes
    for i in range(len(kp_index)):
        if kp_index[i] > KP_THRESHOLD:
            plt.axvline(x=times[i], color='b', linewidth=3, zorder=3)  # draw vertical line for values > threshold
            # add horizontal markers for the kp index level
            plt.scatter([times[i]], [kp_index[i]], color='r', marker='o', zorder=5)  # red markers

    # keep the y-axis fixed at 0-9 as requested
    plt.ylim(0, 9)

    # overlay the green line smoothly transitioning from 5 years ago to the input year (if sunspot data exists)
    if sunspot_curve_y is not None:
        scaled_curve_y = 9 * (sunspot_curve_y - min(sunspot_curve_y)) / (max(sunspot_curve_y) - min(sunspot_curve_y))
        plt.plot(times, scaled_curve_y, color='g', linewidth=2, linestyle='-', zorder=2, label=f"Sunspot activity trend between {start_year} and {last_available_year}")

    # create custom legend handles for kp index, sunspot, and events
    base_line_handle = plt.Line2D([], [], color='#dddddd', linewidth=2, label="Magnetosphere disturbance")
    line_handle = plt.Line2D([0], [0], color='b', linewidth=2, label=f'Good visibility days in {year}')
    sunspot_handle = plt.Line2D([0], [0], color='g', linewidth=2, label=f'Sunspot activity trend between {start_year} and {last_available_year}' if sunspot_curve_y is not None else '')
    event_handle = plt.Line2D([0], [0], color='r', marker='o', linestyle='None', markersize=5, label='Aurora events')

    plt.title(f'Aurora borealis visibility throughout {year}')  # dynamic year in title
    plt.ylabel(r'$\it{K}_p$ index')  # k italic, p subscript, index lowercase
    plt.grid(axis='y')  # enable only horizontal grid lines

    # format the x-axis to show only the month and day, hide the year
    date_format = mdates.DateFormatter('%b %d')  # e.g., 'jan 01'
    plt.gca().xaxis.set_major_formatter(date_format)

    # set x-ticks for every day in the year with padding
    plt.xticks(times, rotation=90, fontsize=4)  # keep all dates but rotate for visibility
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(nbins=365, integer=True))  # allow for all ticks with spacing

    # adjust x-axis limits to add space around the plot
    plt.xlim([times[0] - timedelta(days=1), times[-1] + timedelta(days=1)])  # adding padding on the x-axis

    # hide the x-axis label
    plt.xlabel('')

    # if --clean option is set, skip adding the legend
    if not clean:
        # add a custom legend with a white background, including the green line for sunspot activity
        legend_handles = [sunspot_handle, base_line_handle, line_handle, event_handle]  # adjust order of handles
        legend = plt.legend(handles=legend_handles, loc='upper left', facecolor='#ffffff', framealpha=0.75)
        legend.get_frame().set_edgecolor('#000000')  # add a border to the legend box

    # save the plot as a png file without showing it
    file_name = f'kp_index_{year}.png'
    plt.savefig(file_name, format='png', dpi=300, bbox_inches='tight')

    # close the plot to avoid display
    plt.close()

    log(f"Plot saved as {file_name}", quiet)

# print the help message for script usage
def print_help():
    help_message = """
    Usage: python script.py <YEAR> [--quiet] [--clean] [--help]

    Options:
    <YEAR>         The year for which the Kp index data should be plotted.
    --quiet        Suppress all logs and outputs (quiet mode).
    --clean        Hide the legend box on the plot (clean mode).
    --help         Show this help message.
    """
    print(help_message)

if __name__ == '__main__':
    # check for the --quiet, --clean, and --help flags
    quiet = '--quiet' in sys.argv
    clean = '--clean' in sys.argv
    show_help = '--help' in sys.argv

    # remove --quiet, --clean, and --help from arguments
    args = [arg for arg in sys.argv if arg not in ['--quiet', '--clean', '--help']]

    # show help message if --help is provided or no arguments are given
    if show_help or len(args) == 1:
        print_help()
        sys.exit(0)

    # check if the user provided a year argument
    if len(args) != 2:
        print("Usage: python script.py <YEAR> [--quiet] [--clean] [--help]")
        sys.exit(1)

    try:
        YEAR = int(args[1])
        plot_kp_index_for_year(YEAR, quiet=quiet, clean=clean)
    except ValueError:
        print("Please provide a valid year (e.g., 2022).")
        sys.exit(1)
