# %% 0. Loading in Patient Information
import os
import json
import pandas as pd
from datetime import date
from pathlib import Path
from data_utils import *
from sync_utils import *

# Loading in config.json containing patient information
with open('config.json', 'r') as file:
    config = json.load(file)

OURA_DIR = config['oura_dir']
NEURAL_DIR = config['neural_dir']

first_date = config['first_date']
last_date = config['last_date']
patient_list = first_date.keys()

# %% 1. Extracting Oura Ring Data

# Looping through each patient and extracting relevant Oura data
print('Extracting Oura Ring Data for...')
for patient in patient_list:
    print(patient)
    
    # Converting start and end dates to datetimes
    start_date = first_date[patient]
    start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
    
    end_date = last_date[patient]
    end_date = pd.to_datetime(end_date).strftime('%Y-%m-%d')
    
    # Defining path to Oura data
    cohort = get_patient_cohort(patient)
    oura_path = os.path.join(OURA_DIR,cohort,patient,'oura')
    
    # Finding data within given timeframe
    date_folders = sorted(os.listdir(oura_path))
    valid_dates = [f for f in date_folders if start_date <= f <= end_date]
    
    # Defining which files to retrieve data from
    data_types = {
        "activity": "daily_activity.json",
        "sleep": "sleep.json",
        "stress": "stress.json",
        "heartrate": "heartrate.json",
    }

    # Initializing dict to store data
    all_data = {key: {"data": []} for key in data_types}

    # Looping through each date folder and extracting all relevant records
    for date_folder in valid_dates:
        date_path = os.path.join(oura_path, date_folder)

        for data_type, filename in data_types.items():
            full_path = os.path.join(date_path, filename)

            if not os.path.exists(full_path):
                continue

            with open(full_path, "r") as f:
                try:
                    records = json.load(f)
                    if isinstance(records, list):
                        all_data[data_type]["data"].extend(records)
                except json.JSONDecodeError:
                    pass

    # Saving compiled data dicts as jsons
    save_json_to_file(all_data["activity"], f"data/activity/{patient}_activity.json")
    save_json_to_file(all_data["sleep"], f'data/sleep/{patient}_sleep.json')
    save_json_to_file(all_data["stress"], f'data/stress/{patient}_stress.json')
    save_json_to_file(all_data["heartrate"], f'data/daytime heart rate/{patient}_heartrate.json')

# %% 2. Extracting Chronic LFP Data

print('Extracting Chronic LFP Data for...')
for patient in patient_list:
    print(patient)

    # Defining path to neural data
    cohort = get_patient_cohort(patient)
    neural_path = os.path.join(NEURAL_DIR,cohort,patient,'LFP','R')

    # Extracting and combining chronic LFP data
    times, LFP, stim = extract_chronic_lfp_data(neural_path)

    # Converting to a single dataframe
    neural_timeseries = pd.DataFrame({
        'Time': times,
        'Chronic_LFP_Left': LFP['Left'],
        'Chronic_LFP_Right': LFP['Right'],
        'Stimulation_Left': stim['Left'],
        'Stimulation_Right': stim['Right']
    })
    
    # Apply OvER correction to chronic LFP data and interpolate any gaps with PCHIP
    over_corrected = fill_outliers_OvER(neural_timeseries, cols_to_fill=['Chronic_LFP_Left', 'Chronic_LFP_Right'])
    interpolated = interpolate_holes(over_corrected, cols_to_fill=['Chronic_LFP_Left_OvER', 'Chronic_LFP_Right_OvER'])
    
    neural_timeseries['Chronic_LFP_Left'] = interpolated['Chronic_LFP_Left_OvER_interpolate']
    neural_timeseries['Chronic_LFP_Right'] = interpolated['Chronic_LFP_Right_OvER_interpolate']

    # Converting dataframe to nested dictionary and saving
    nested_dict = dataframe_to_nested_dict(neural_timeseries)
    save_json_to_file(nested_dict, f'data/chronic lfp/{patient}_chronicLFP.json')
    
# %% 3. Synchronizing Sleep, Activity, and Neural Data

SLEEP_TGT_PATH = Path('data/sleep/')
LFP_TGT_PATH = Path('data/chronic lfp')
ACTIVITY_TGT_PATH = Path('data/activity')
DEST_TGT_PATH = Path('data/sync')
DEST_TGT_PATH.mkdir(parents=True, exist_ok=True)

print('Synchronizing data for...')
for patient in patient_list:
    print(patient)
    
    # Loading in the three data streams
    patient_sleep = load_json(SLEEP_TGT_PATH / f'{patient}_sleep.json')
    patient_lfp = load_json(LFP_TGT_PATH / f'{patient}_chronicLFP.json')
    patient_activity = load_json(ACTIVITY_TGT_PATH / f'{patient}_activity.json')
    
    # Synchronizing data streams and organizing into a DataFrame 
    data = process_data(patient_sleep, patient_lfp, patient_activity)
    unpacked_data = unpack_data(data) # restructures data to enable conversion to DataFrame
    data_df = pd.DataFrame(unpacked_data)
    
    # Identifying non-wear periods
    data_df = extract_non_wear_time(data_df)
    
    # Saving synchronized data as a csv
    data_df.to_csv(DEST_TGT_PATH / f'{patient}_sync.csv')
    
print('Finished synchronization.')