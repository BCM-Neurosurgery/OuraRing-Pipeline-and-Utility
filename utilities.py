#%% Import Libraries
import json
import csv
import requests
import os
import sys
from glob import glob
import numpy as np
from bisect import bisect_left
import pytz
from datetime import datetime, timezone, date, timedelta

def process_hemisphere(data, hemisphere, central_timezone):
    """Helper function to process data for a single hemisphere."""
    hemisphere_data = data.get('DiagnosticData', {}).get('LFPTrendLogs', {}).get(f'HemisphereLocationDef.{hemisphere}', {})

    time_data = []
    LFP_data = []
    stim_data = []

    for key in hemisphere_data.keys():
        for entry in hemisphere_data[key]:
            dt_utc = datetime.strptime(entry['DateTime'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            dt_central = dt_utc.astimezone(central_timezone)
            time_data.append(dt_central)
            LFP_data.append(entry['LFP'])
            stim_data.append(entry['AmplitudeInMilliAmps'])

    return {
        'time': time_data,
        'LFP': LFP_data,
        'stim': stim_data
    }

def align_data(all_times, data, indices):
    """Aligns data based on the given indices."""
    aligned_data = np.empty(len(all_times))
    aligned_data.fill(np.nan)
    aligned_data[indices] = data
    return aligned_data.tolist()

def extract(fileName):
    """Extracts and processes data from a given JSON file."""
    data = json.load(open(fileName))

    central_timezone = pytz.timezone('America/Chicago')

    left_data = process_hemisphere(data, 'Left', central_timezone)
    right_data = process_hemisphere(data, 'Right', central_timezone)

    times = list(set(left_data['time'] + right_data['time']))
    times.sort()

    left_idx = np.intersect1d(times, left_data['time'], return_indices=True)[2]
    right_idx = np.intersect1d(times, right_data['time'], return_indices=True)[2]

    LFP = {
        'Left': align_data(times, left_data['LFP'], left_idx),
        'Right': align_data(times, right_data['LFP'], right_idx)
    }

    stim = {
        'Left': align_data(times, left_data['stim'], left_idx),
        'Right': align_data(times, right_data['stim'], right_idx)
    }

    return times, LFP, stim

def time_difference(time1, time2):
    """Calculates the absolute difference in seconds between two datetime objects."""
    
    return abs((time1 - time2).total_seconds())

def calculate_10min_avg_MET(activity_entry):
    """Calculates the average MET value over 10-minute intervals."""
    met_values = activity_entry['met_1min']
    avg_met_10min = [sum(met_values[i:i + 10]) / 10 for i in range(0, len(met_values), 10)]
    
    return avg_met_10min

def fetch_data_from_api(endpoint, start_date, end_date, token):
    """Fetches data from the Oura Ring API for a given endpoint and date range."""
    url = f'https://api.ouraring.com/v1/{endpoint}?start={start_date}&end={end_date}&access_token={token}'
    response = requests.get(url)
    return response.json()

def fetch_heartrate_api(end_date, token):
    start_date = str(date.today() - timedelta(days = 30))
    url = 'https://api.ouraring.com/v2/usercollection/heartrate' 
    params={ 
        'start_datetime': f'{start_date}T00:00:00-08:00', 
        'end_datetime': f'{end_date}T00:00:00-08:00' 
    }
    headers = { 
    'Authorization': 'Bearer ' + token,
    }
    response = requests.request('GET', url, headers=headers, params=params) 

    return response.json()

def save_json_to_file(data, filename):
    """Saves a JSON object to a file."""
    with open(filename, 'w') as file:
        json.dump(data, file, indent=3)
        
def extract_chronic_lfp_data(directory):
    """Extract and combine chronic LFP data from multiple JSON files in a directory."""
    fileList = glob(os.path.join(directory, '*.json'))
    times = []
    LFP = {'Left': [], 'Right': []}
    stim = {'Left': [], 'Right': []}

    for fileName in fileList:
        temp_times, temp_LFP, temp_stim = extract(fileName)
        if temp_times:
            times = times + temp_times
            LFP['Left'] = np.concatenate((LFP['Left'], temp_LFP['Left']))
            LFP['Right'] = np.concatenate((LFP['Right'], temp_LFP['Right']))
            stim['Left'] = np.concatenate((stim['Left'], temp_stim['Left']))
            stim['Right'] = np.concatenate((stim['Right'], temp_stim['Right']))

    times, unique_idx = np.unique(times, return_index=True, equal_nan=False)
    times = times.tolist()

    LFP['Left'] = np.asarray(LFP['Left'])[unique_idx.astype(int)].tolist()
    LFP['Right'] = np.asarray(LFP['Right'])[unique_idx.astype(int)].tolist()
    stim['Left'] = np.asarray(stim['Left'])[unique_idx.astype(int)].tolist()
    stim['Right'] = np.asarray(stim['Right'])[unique_idx.astype(int)].tolist()

    return times, LFP, stim

def dataframe_to_nested_dict(df):
    """Converts a dataframe to a nested dictionary using the 'Time' column as the main key."""
    df['Time'] = df['Time'].astype(str)
    data_list = df.to_dict('records')
    nested_dict = {}
    for d in data_list:
        nested_dict[d['Time']] = {
            'Chronic_LFP_Left': d['Chronic_LFP_Left'],
            'Chronic_LFP_Right': d['Chronic_LFP_Right'],
            'Stimulation_Left': d['Stimulation_Left'],
            'Stimulation_Right': d['Stimulation_Right']
        }
    return nested_dict

def read_json_file(filepath):
    """Read a JSON file and return its content."""
    with open(filepath, 'r') as file:
        return json.load(file)

def convert_to_datetime(data_rows):
    """Convert the first column of a list of rows to datetime objects."""
    return [[datetime.fromisoformat(row[0])] + row[1:] for row in data_rows]

def nearest_timestamp_data(target_timestamp, data_rows):
    """Find the data row with the timestamp closest to the target timestamp using binary search."""
    timestamps = [row[0] for row in data_rows]

    # Find the position of the target timestamp in the list or where it would be inserted
    pos = bisect_left(timestamps, target_timestamp)

    if pos == 0:
        return data_rows[0]
    if pos == len(timestamps):
        return data_rows[-1]

    # Check which of the two timestamps around the position is closest to the target
    before = timestamps[pos - 1]
    after = timestamps[pos]
    
    if target_timestamp - before < after - target_timestamp:
        return data_rows[pos - 1]
    else:
        return data_rows[pos]

def combine_data(chronic_lfp_rows, sleep_data, activity_data, avg_met_data, bedtime_periods):
    """Combine chronic LFP data with sleep, activity, and avg MET data."""
    combined_data = []

    # Convert sleep data to a dictionary for direct lookup
    sleep_data_dict = {row[0]: row[1] for row in sleep_data}

    for idx, lfp_row in enumerate(chronic_lfp_rows):
        if idx % 1000 == 0:  # Log every 1000 iterations to avoid flooding the console
            print(f"Processing LFP row {idx} of {len(chronic_lfp_rows)}...")

        lfp_timestamp = lfp_row[0]

        # Check if LFP timestamp is within a bedtime period
        is_within_bedtime = any([start <= lfp_timestamp <= end for start, end in bedtime_periods])

        # Nearest Sleep Timestamp
        nearest_sleep_row = [None, None]
        if is_within_bedtime:
            # Round lfp_timestamp to the nearest 5-minute increment
            rounded_time = datetime(lfp_timestamp.year, lfp_timestamp.month, lfp_timestamp.day, lfp_timestamp.hour, 5 * (lfp_timestamp.minute // 5), tzinfo=lfp_timestamp.tzinfo)
            nearest_sleep_row = [rounded_time.isoformat(), sleep_data_dict.get(rounded_time, None)]

        nearest_activity_row = nearest_timestamp_data(lfp_timestamp, activity_data)
        nearest_avg_met_row = nearest_timestamp_data(lfp_timestamp, avg_met_data)
        combined_row = lfp_row + nearest_sleep_row + nearest_activity_row + [nearest_avg_met_row[1]]
        combined_data.append(combined_row)
        
    return combined_data

def write_to_csv(filepath, data_rows, header):
    """Write data to a CSV file."""
    with open(filepath, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(header)
        csv_writer.writerows(data_rows)

def display_progress_bar(fraction_done, bar_length=50):
    arrow = '=' * int(round(fraction_done * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    sys.stdout.write(f"\rProgress: [{arrow + spaces}] {int(fraction_done * 100)}%\n")
    sys.stdout.flush()

def update_heart_rate_json(new_data, existing_json):
    # Check to see if an existing heart rate json already exists so you can append data if so
    try:
        with open(existing_json, 'r') as file:
            current_data = json.load(file)
    except FileNotFoundError:
        current_data = {'data': []}
    
    # Convert current data to set for quicker search
    current_timestamps = {entry['timestamp'] for entry in current_data['data']}
    
    # Check new data against existing json
    for entry in new_data['data']:
        if entry['timestamp'] not in current_timestamps:
            current_data['data'].append(entry)
    
    with open(existing_json, 'w') as file:
        json.dump(current_data, file, indent = 3)