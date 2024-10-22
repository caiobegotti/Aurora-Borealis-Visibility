#!/usr/bin/env python3
# license: public domain
# author: caio begotti

from datetime import datetime, timedelta
from getKpindex import getKpindex
from matplotlib import rcParams
from scipy.interpolate import CubicSpline

import csv
import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import os
import requests
import sys

# constants
KP_THRESHOLD = 5
CACHE_DIR = './cache'
SUNSPOT_FILE = f'{CACHE_DIR}/SN_y_tot_V2.0.csv'
NOAA_FORECAST_URL = 'https://services.swpc.noaa.gov/text/27-day-outlook.txt'

# colors
COLOR_WHITE = '#FFFFFF'
COLOR_YELLOW = '#FFFAA0'
COLOR_GRAY = '#DDDDDD'
COLOR_GREEN = '#AFE1AF'
COLOR_BLUE = '#1F51FF'
COLOR_RED = '#FF0000'
COLOR_ORANGE = '#FFA500'

# ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def log(message, quiet=False):
    if not quiet:
        print(message)

def load_or_fetch_kp_index(year, quiet=False, refresh=False):
    cache_file = f'{CACHE_DIR}/kp_index_{year}.json'

    current_year = datetime.now().year
    if year > current_year:
        log(f"Year {year} not supported by data or not current", quiet)
        sys.exit(1)

    if os.path.exists(cache_file) and not refresh:
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
        except Exception as error:
            log(f"Error fetching Kp index data for {year}: {error}", quiet)
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

def fetch_noaa_forecast():
    forecast_times = []
    forecast_kp = []

    try:
        response = requests.get(NOAA_FORECAST_URL)
        response.raise_for_status()
        lines = response.text.splitlines()

        for line in lines:
            if line.startswith("#") or line.startswith(":") or len(line.strip()) == 0:
                continue

            parts = line.split()
            if len(parts) >= 6: # ensure the 6th column exists for kp index
                try:
                    date_str = f"{parts[0]} {parts[1]} {parts[2]}" # e.g. "2024 Oct 22"
                    kp_value = int(parts[5]) # kp index is the 6th column
                    forecast_date = datetime.strptime(date_str, '%Y %b %d')

                    forecast_times.append(forecast_date)
                    forecast_kp.append(kp_value)
                except ValueError:
                    continue

        return forecast_times, forecast_kp

    except Exception as e:
        print(f"Error fetching NOAA forecast: {e}")
        return [], []

def generate_full_date_range(year):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

def plot_kp_index_for_year(year, quiet=False, simplified=False, refresh=False):
    times, kp_values = load_or_fetch_kp_index(year, quiet, refresh)

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

    plt.plot(times, kp_values, color=COLOR_GRAY, linewidth=0.5, zorder=1)

    # output sunspot value for logging (only if available for the current year)
    if year in sunspot_data:
        log(f"Sunspots for {year}: {sunspot_data[year]}", quiet)

    for i, value in enumerate(kp_values):
        if value > KP_THRESHOLD:
            plt.axvline(x=times[i], color=COLOR_BLUE, linewidth=1, zorder=3)
            plt.scatter([times[i]], [value], color=COLOR_RED, marker='o', linewidth=2, zorder=5)

    if year + 1 in sunspot_data or year in sunspot_data:
        next_year_sunspot = sunspot_data.get(year + 1, sunspot_data.get(year, None))
        if next_year_sunspot:
            log(f"Sunspots after {year}: {next_year_sunspot}", quiet)

    plt.ylim(0, 9)

    # generate full date range for the year
    full_dates = generate_full_date_range(year)

    # align Kp values and forecast data with full_dates
    kp_values_full = [kp_values[times.index(date)] if date in times else np.nan for date in full_dates]

    # check if current year data is incomplete and fetch forecast data
    if year == datetime.now().year:
        last_data_date = max(times)
        if last_data_date < datetime.now():
            log(f"Year {year} is not over, fetching forecast data", quiet)
            forecast_times, forecast_kp = fetch_noaa_forecast()

            # filter forecast data to only include future dates after the last available Kp index data
            forecast_times = [t for t in forecast_times if t > last_data_date]
            forecast_kp = forecast_kp[:len(forecast_times)] # adjust kp values to match the number of valid times

            if forecast_times:
                # align forecast values with full_dates
                for f_time, f_kp in zip(forecast_times, forecast_kp):
                    idx = full_dates.index(f_time)
                    kp_values_full[idx] = f_kp
                    for i, value in enumerate([f_kp]):
                        if value > KP_THRESHOLD:
                            plt.axvline(x=f_time, color=COLOR_BLUE, linewidth=1, zorder=3)
                        plt.scatter([f_time], [value], color=COLOR_ORANGE, marker='o', linewidth=2, zorder=5)

    # plot the full date range
    plt.plot(full_dates, kp_values_full, color=COLOR_GRAY, linewidth=0.5)

    # draw green band smoothly transitioning from 5 years ago to the input year (if sunspot data exists),
    # adjusting the green band to match the full range of dates, i.e. observed + forecast
    if sunspot_values:
        cubic_spline = CubicSpline(np.linspace(0, len(full_dates) - 1, len(sunspot_values)), sunspot_values)
        sunspot_curve_y = cubic_spline(np.linspace(0, len(full_dates) - 1, len(full_dates)))
        scaled_curve_y = 9 * (sunspot_curve_y - min(sunspot_curve_y)) / (max(sunspot_curve_y) - min(sunspot_curve_y))
        plt.plot(full_dates, scaled_curve_y, color=COLOR_GREEN, linewidth=15, label=f"Sunspots trend", zorder=1)

    # set sketch parameters only for the yellow zig-zag equinox lines
    rcParams['path.sketch'] = (50, 250, 1) # (scale, length of wiggle, randomness) - more amplitude, smoother

    # plot zig-zag yellow lines for march 21st and september 21st
    for date_str in [f"{year}-03-21", f"{year}-09-21"]:
        equinox_date = datetime.strptime(date_str, '%Y-%m-%d')
        if equinox_date in full_dates:
            plt.axvline(x=equinox_date, color=COLOR_YELLOW, linewidth=15, label='Equinox season start', zorder=1)

    # restore normal line settings for everything else
    rcParams['path.sketch'] = None

    plt.title(f'Aurora borealis visibility throughout {year}')
    plt.ylabel(r'$\it{K}_p$ index') # k italic, p subscript, index lowercase
    plt.grid(axis='y')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %d')) # format the x-axis to show only the month and day, hide the year
    plt.xticks(full_dates, rotation=90, fontsize=4) # keep all dates but rotate for visibility
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(nbins=365, integer=True)) # allow for all ticks with spacing
    plt.xlim([full_dates[0] - timedelta(days=1), full_dates[-1] + timedelta(days=1)]) # adding padding on the x-axis

    if not simplified:
        legend_handles = [
            plt.Line2D([0], [0], color=COLOR_GRAY, linewidth=5, label="Magnetosphere disturbance"),
            plt.Line2D([0], [0], color=COLOR_GREEN, linewidth=5, label=f'Sunspots trend between {start_year}-today'),
            plt.Line2D([0], [0], color=COLOR_YELLOW, linewidth=5, label='Equinox season start'),
            plt.Line2D([0], [0], color=COLOR_BLUE, linewidth=5, label=f'Good visibility days this year'),
            plt.Line2D([0], [0], color=COLOR_RED, marker='o', linestyle='None', markersize=8, label='Aurora events')
        ]
        if year == datetime.now().year:
            legend_handles.append(plt.Line2D([0], [0], color=COLOR_ORANGE, marker='o', linestyle='None', markersize=8, label='Aurora forecasted'))
        plt.legend(handles=legend_handles, loc='upper left', facecolor=COLOR_WHITE, framealpha=0.75)

    file_name = f'kp_index_{year}.png'
    plt.savefig(file_name, format='png', dpi=300, bbox_inches='tight')
    plt.close()

    log(f"Plot saved as {file_name}", quiet)

def print_help():
    help_message = """
    Usage: python script.py <YEAR> [--quiet] [--simplified] [--refresh] [--help]

    Options:
    <YEAR>         The year for which the Kp index data should be plotted.
    --quiet        Suppress all logs and outputs.
    --simplified   Hide the legend box on the plot, makes graphs bigger.
    --refresh      Force fetching the remote data (refreshing local cache).
    --help         Show this help message.
    """
    print(help_message)

if __name__ == '__main__':
    if '--help' in sys.argv or len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    quiet = '--quiet' in sys.argv
    simplified = '--simplified' in sys.argv
    refresh = '--refresh' in sys.argv
    args = [arg for arg in sys.argv if arg not in ['--quiet', '--simplified', '--refresh', '--help']]

    if len(args) != 2:
        print("Usage: python script.py <YEAR> [--quiet] [--simplified] [--refresh] [--help]")
        sys.exit(1)

    try:
        YEAR = int(args[1])
        plot_kp_index_for_year(YEAR, quiet=quiet, simplified=simplified, refresh=refresh)
    except ValueError:
        print("Please provide a valid year (e.g., 2022).")
        sys.exit(1)
