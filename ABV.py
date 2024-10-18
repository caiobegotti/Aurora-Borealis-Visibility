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
from matplotlib import rcParams

# constants
KP_THRESHOLD = 5
CACHE_DIR = './cache'
SUNSPOT_FILE = f'{CACHE_DIR}/SN_y_tot_V2.0.csv'

# ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def log(message, quiet=False):
    if not quiet:
        print(message)

def load_or_fetch_kp_index(year, quiet=False):
    cache_file = f'{CACHE_DIR}/kp_index_{year}.json'

    current_year = datetime.now().year
    if year > current_year:
        log(f"Year {year} not supported by data or not current", quiet)
        sys.exit(1)

    if os.path.exists(cache_file):
        log(f"Loading Kp index data for {year} from cache", quiet)
        with open(cache_file, 'r') as f:
            data = json.load(f)
            times = [datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ') for t in data['times']]
            kp_values = data['kp_index']
            return times, kp_values
    else:
        try:
            log(f"Fetching Kp index data for {year} from the API", quiet)
            start_date, end_date = f'{year}-01-01', f'{year}-12-31'
            times, kp_values, status = getKpindex(start_date, end_date, 'Kp', 'def')
            times = [datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ') for t in times]

            with open(cache_file, 'w') as f:
                json.dump({'times': [t.strftime('%Y-%m-%dT%H:%M:%SZ') for t in times], 'kp_index': kp_values}, f)

            return times, kp_values
        except Exception:
            log(f"Error fetching Kp index data for {year}.", quiet)
            sys.exit(1)

def load_sunspot_data(start_year, end_year, quiet=False):
    if not os.path.exists(SUNSPOT_FILE):
        log(f"Sunspot data file not found: {SUNSPOT_FILE}", quiet)
        return None

    sunspot_data = {}
    with open(SUNSPOT_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            try:
                row_year = int(float(row[0])) # conversions to ignore the .5 float in the data
                if start_year <= row_year <= end_year:
                    sunspot_data[row_year] = float(row[1]) # second column is the sunspot value
            except (ValueError, IndexError):
                continue

    return sunspot_data

def plot_kp_index_for_year(year, quiet=False, clean=False):
    times, kp_values = load_or_fetch_kp_index(year, quiet)

    log(f"Retrieved {len(times)} entries for year {year}", quiet)

    start_year = year - 5
    sunspot_data = load_sunspot_data(start_year, year + 1, quiet)

    if not sunspot_data:
        log("Sunspot data not available, skipping sunspot plot.", quiet)
        sunspot_data = {} # set to an empty dictionary to avoid future errors

    # find the last available year for sunspot data
    last_available_year = max(sunspot_data.keys(), default=None)

    sunspot_values = [sunspot_data.get(yr) for yr in range(start_year, last_available_year + 1)] if last_available_year else None

    if last_available_year and last_available_year < year:
        log(f"Sunspot data only available up to {last_available_year}", quiet)

    plt.figure(figsize=(20, 10))

    # log sunspot data for the previous year (if available)
    if year - 1 in sunspot_data:
        log(f"Sunspots before {year}: {sunspot_data[year - 1]}", quiet)

    plt.plot(times, kp_values, color='#dddddd', linewidth=0.5, zorder=1)

    # output sunspot value for logging (only if available for the current year)
    if year in sunspot_data:
        log(f"Sunspots for {year}: {sunspot_data[year]}", quiet)

    for i, value in enumerate(kp_values):
        if value > KP_THRESHOLD:
            plt.axvline(x=times[i], color='#1F51FF', linewidth=1, zorder=3)
            plt.scatter([times[i]], [value], color='r', marker='o', linewidth=2, zorder=5)

    if year + 1 in sunspot_data or year in sunspot_data:
        next_year_sunspot = sunspot_data.get(year + 1, sunspot_data.get(year, None))
        if next_year_sunspot:
            log(f"Sunspots after {year}: {next_year_sunspot}", quiet)

    plt.ylim(0, 9)

    # draw the green band smoothly transitioning from 5 years ago to the input year (if sunspot data exists)
    if sunspot_values:
        cubic_spline = CubicSpline(np.linspace(0, len(times) - 1, len(sunspot_values)), sunspot_values)
        sunspot_curve_y = cubic_spline(np.linspace(0, len(times) - 1, len(times)))
        scaled_curve_y = 9 * (sunspot_curve_y - min(sunspot_curve_y)) / (max(sunspot_curve_y) - min(sunspot_curve_y))
        plt.plot(times, scaled_curve_y, color='#AFE1AF', linewidth=15, label=f"Sunspots trend", zorder=1)

    # set sketch parameters only for the yellow zig-zag equinox lines
    rcParams['path.sketch'] = (50, 250, 1)  # (scale, length of wiggle, randomness) - more amplitude, smoother

    # plot zig-zag yellow lines for march 21st and september 21st
    highlight_yellow = '#FFFAA0'
    for date_str in [f"{year}-03-21", f"{year}-09-21"]:
        equinox_date = datetime.strptime(date_str, '%Y-%m-%d')
        if equinox_date in times:
            plt.axvline(x=equinox_date, color=highlight_yellow, linewidth=15, label='Equinox season start', zorder=1)

    # restore normal line settings for everything else
    rcParams['path.sketch'] = None

    plt.title(f'Aurora borealis visibility throughout {year}')
    plt.ylabel(r'$\it{K}_p$ index') # k italic, p subscript, index lowercase
    plt.grid(axis='y')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %d')) # format the x-axis to show only the month and day, hide the year
    plt.xticks(times, rotation=90, fontsize=4) # keep all dates but rotate for visibility
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(nbins=365, integer=True)) # allow for all ticks with spacing
    plt.xlim([times[0] - timedelta(days=1), times[-1] + timedelta(days=1)]) # adding padding on the x-axis

    if not clean:
        legend_handles = [
            plt.Line2D([0], [0], color='#dddddd', linewidth=5, label="Magnetosphere disturbance"),
            plt.Line2D([0], [0], color='#AFE1AF', linewidth=5, label=f'Sunspots trend between {start_year}-today'),
            plt.Line2D([0], [0], color=highlight_yellow, linewidth=5, label='Equinox season start'),
            plt.Line2D([0], [0], color='#1F51FF', linewidth=5, label=f'Good visibility days this year'),
            plt.Line2D([0], [0], color='r', marker='o', linestyle='None', markersize=8, label='Aurora events')
        ]
        plt.legend(handles=legend_handles, loc='upper left', facecolor='#ffffff', framealpha=0.75)

    file_name = f'kp_index_{year}.png'
    plt.savefig(file_name, format='png', dpi=300, bbox_inches='tight')
    plt.close()

    log(f"Plot saved as {file_name}", quiet)

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
    if '--help' in sys.argv or len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    quiet = '--quiet' in sys.argv
    clean = '--clean' in sys.argv
    args = [arg for arg in sys.argv if arg not in ['--quiet', '--clean', '--help']]

    if len(args) != 2:
        print("Usage: python script.py <YEAR> [--quiet] [--clean] [--help]")
        sys.exit(1)

    try:
        YEAR = int(args[1])
        plot_kp_index_for_year(YEAR, quiet=quiet, clean=clean)
    except ValueError:
        print("Please provide a valid year (e.g., 2022).")
        sys.exit(1)
