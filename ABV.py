#!/usr/bin/env python3
# license: public domain
# author: caio begotti

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import csv

from getKpindex import getKpindex
from datetime import datetime, timedelta

import sys
import os
import json

# Constants
KP_THRESHOLD = 5  # Threshold for KP Index to highlight
CACHE_DIR = './cache'  # Directory to store cached data
SUNSPOT_FILE = f'{CACHE_DIR}/SN_y_tot_V2.0.csv'  # Path to the sunspot CSV file

# Ensure the cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def load_or_fetch_kp_index(year):
    """Load KP index data from a local JSON file or fetch from API if not cached."""
    cache_file = f'{CACHE_DIR}/kp_index_{year}.json'

    # Check if cache file exists
    if os.path.exists(cache_file):
        print(f"Loading KP index data for {year} from cache...")
        with open(cache_file, 'r') as f:
            data = json.load(f)
            times = [datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ') for t in data['times']]
            kp_index = data['kp_index']
            return times, kp_index
    else:
        # Fetch KP index data from the API
        print(f"Fetching KP index data for {year} from the API...")
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'

        # Get KP index data using the external script
        times, kp_index, status = getKpindex(start_date, end_date, 'Kp', 'def')

        # Convert time strings to datetime objects
        times = [datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ') for t in times]

        # Save the data to the cache file
        with open(cache_file, 'w') as f:
            json.dump({'times': [t.strftime('%Y-%m-%dT%H:%M:%SZ') for t in times], 'kp_index': kp_index}, f)

        return times, kp_index

def load_sunspot_data(year):
    """Load sunspot data for a specific year from the CSV file."""
    if not os.path.exists(SUNSPOT_FILE):
        print(f"Sunspot data file not found: {SUNSPOT_FILE}")
        return None

    # Read the CSV file without skipping the header (since it's crude and headerless)
    with open(SUNSPOT_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')

        for row in reader:
            row_year = float(row[0])  # Use float to capture the `.5`
            int_year = int(row_year)  # Convert to integer to ignore the `.5`
            if int_year == year:
                sunspot_value = float(row[1])  # Second column is the sunspot value
                return sunspot_value

    # If the year is not found, return None
    print(f"Sunspot data for year {year} not found.")
    return None

def plot_kp_index_for_year(year):
    """Plot KP index for a specific year with local cache support and overlay sunspot data."""
    # Load or fetch KP index data
    times, kp_index = load_or_fetch_kp_index(year)

    # Debugging: Print the retrieved data length
    print(f"Retrieved {len(times)} entries for year {year}.")

    # Load sunspot data for the year
    sunspot_value = load_sunspot_data(year)
    if sunspot_value is None:
        print("Sunspot data not available, skipping sunspot plot.")
    else:
        print(f"Sunspot value for {year}: {sunspot_value}")

    # Prepare a figure with increased size for better visibility
    plt.figure(figsize=(20, 10))  # Larger figure size

    # Plot all KP Index values (line) in light gray
    plt.plot(times, kp_index, color='#dddddd', linewidth=0.5)  # Base line in light gray

    # Highlight values above threshold in blue and mark them with red dashes
    for i in range(len(kp_index)):
        if kp_index[i] > KP_THRESHOLD:
            plt.axvline(x=times[i], color='b', linewidth=3, zorder=3)  # Draw vertical line for values > threshold
            # Add horizontal markers for the KP index level
            plt.scatter([times[i]], [kp_index[i]], color='r', marker='o', zorder=5)  # Red markers

    # Keep the y-axis fixed at 0-9 as requested
    plt.ylim(0, 9)

    # Overlay the sunspot line (purely visual, no effect on y-axis)
    if sunspot_value is not None:
        # We'll plot a line overlay across the entire graph, ignoring the y-axis scale
        plt.plot(times, [7.5] * len(times), color='g', linewidth=2, linestyle='-', zorder=2)  # Overlay green line at constant y=7.5 for visibility

    # Create custom legend handles for KP index and events (no legend for sunspot line)
    line_handle = plt.Line2D([0], [0], color='b', linewidth=2, label='Good visibility days')
    event_handle = plt.Line2D([0], [0], color='r', marker='o', linestyle='None', markersize=5, label='Events')

    plt.title(f'Aurora borealis visibility in {year}')  # Dynamic year in title
    plt.ylabel('Kp Index')
    plt.grid(axis='y')  # Enable only horizontal grid lines

    # Format the x-axis to show only the month and day, hide the year
    date_format = mdates.DateFormatter('%b %d')  # e.g., 'Jan 01'
    plt.gca().xaxis.set_major_formatter(date_format)

    # Set x-ticks for every day in the year with padding
    plt.xticks(times, rotation=90, fontsize=4)  # Keep all dates but rotate for visibility
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(nbins=365, integer=True))  # Allow for all ticks with spacing

    # Adjust x-axis limits to add space around the plot
    plt.xlim([times[0] - timedelta(days=1), times[-1] + timedelta(days=1)])  # Adding padding on the x-axis

    # Hide the x-axis label
    plt.xlabel('')

    # Add a custom legend with a white background, no sunspot line legend
    legend = plt.legend(handles=[line_handle, event_handle], loc='upper left', facecolor='#ffffff', framealpha=0.75)
    legend.get_frame().set_edgecolor('#000000')  # Add a border to the legend box

    # Save the plot as a PNG file without showing it
    file_name = f'kp_index_{year}.png'
    plt.savefig(file_name, format='png', dpi=300, bbox_inches='tight')

    # Close the plot to avoid display
    plt.close()

    print(f"Plot saved as {file_name}")

if __name__ == '__main__':
    # Check if the user provided a year argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <YEAR>")
        sys.exit(1)

    try:
        YEAR = int(sys.argv[1])
        plot_kp_index_for_year(YEAR)
    except ValueError:
        print("Please provide a valid year (e.g., 2022).")
        sys.exit(1)
