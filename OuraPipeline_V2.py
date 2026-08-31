# %% Loading in Patient Information
from datetime import date, timedelta
import json
from utilities import *
import pandas as pd
import os

# loading in config.json containing patient information
with open('config.json', 'r') as file:
    config = json.load(file)

first_date = config['first_date']
oura_dir = config['oura_dir']
neural_dir = config['neural_dir']

end_date = str(date.today())
patient_list = first_date.keys()

# %% Extracting Oura Ring Data

# looping through each patient and extracting relevant Oura data
for patient in patient_list:
    
    start_date = first_date[patient]
    start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
    
    # defining path to Oura data
    cohort = get_patient_cohort(patient)
    oura_path = os.path.join(oura_dir,cohort,patient,'oura')
    
    # finding data within given timeframe
    date_folders = sorted(os.listdir(oura_path))
    valid_dates = [f for f in date_folders if start_date <= f <= end_date]
    
    # defining which files to retrieve data from
    data_types = {
        "activity": "daily_activity.json",
        "sleep": "sleep.json",
        "stress": "stress.json",
        "heartrate": "heartrate.json",
    }

    # initializing dict to store data
    all_data = {key: {"data": []} for key in data_types}

    # looping through each date folder and extracting all relevant records
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

    # saving compiled data dicts as jsons
    save_json_to_file(all_data["activity"], f"JSONs/Activity/{patient}_Activity.json")
    save_json_to_file(all_data["sleep"], f'JSONs/Sleep/Hypnogram/{patient}_Sleep.json')
    save_json_to_file(all_data["stress"], f'JSONs/Stress/{patient}_StressScores.json')
    save_json_to_file(all_data["heartrate"], f'JSONs/Daytime Heart Rate/{patient}_HeartRate.json')

# %% Extracting Chronic LFP Data

for patient in patient_list:

    # defining path to neural data
    cohort = get_patient_cohort(patient)
    neural_path = os.path.join(neural_dir,cohort,patient,'LFP','R')

    # extract and combine chronic LFP data
    times, LFP, stim = extract_chronic_lfp_data(neural_path)

    # convert to a single dataframe
    neural_timeseries = pd.DataFrame({
        'Time': times,
        'Chronic_LFP_Left': LFP['Left'],
        'Chronic_LFP_Right': LFP['Right'],
        'Stimulation_Left': stim['Left'],
        'Stimulation_Right': stim['Right']
    })

    # convert dataframe to nested dictionary and save
    nested_dict = dataframe_to_nested_dict(neural_timeseries)
    save_json_to_file(nested_dict, f'JSONs/Chronic LFP Data/Percept{patient}_ChronicLFP.json')