
import json
from typing import Dict, List
from utilities import *
import pandas as pd
from pathlib import Path
import data_processing as dp


'''
Creating time-synced dataframes for LFP and Oura data (Activity and Sleep)
    1. process raw lfp and oura data using OuraPipeline_V2, ending with a list of dicionaries for all metrics in 
    their respective folders in the "JSONs" directory
        - make sure in your working directory you have the "JSONs" folder with the relevant data to sync
          with subdirectories "Chronic LFP Data', "Sleep", and "Activity" with a json per patient

    2. merge and synchronize sleep, activity and LFP dicts. Preprocess (extract non-wear times) and save as csv
        - run synchronize_test_single('PerceptXXX') for a given patient, or synchronize_all_patients()
        - after this you will have a time synced csv saved in the JSONs/Sync directory
          (please excuse a csv being saved in a folder called JSONs)

TODO: 
    - Sync daytime heart rate
    - Come up with a better way to sync data with finer resolution than LFP rather than pulling nearest time point
      (met, sleep phase, heart rate)
'''


with open('config.json', 'r') as file:
    config = json.load(file)


SLEEP_TGT_PATH = Path('JSONs/Sleep/Hypnogram')
LFP_TGT_PATH = Path('JSONs/Chronic LFP Data')
ACTIVITY_TGT_PATH = Path('JSONs/Activity')
BOX_TGT_PATH = Path(config['box_directory'])
DEST_TGT_PATH = Path('JSONs/Sync')

def synchronize_all_patients(time='unix', override=''):
    for p_file in list(config['first_date'].keys()):
        if(p_file != 'SleepStudyJY'):
            synchronize_test_single(p_file, time)


def synchronize_test_single(p_file: str, time='unix'):
    """
    Loads and processes sleep and LFP data for a specified patient, and saves the synchronized data to a JSON file.
    
    Parameters:
    - p_file (str): The patient number as a string to specify which patient's data to load and process.
    - time (str): what time standard should be used only two options (unix, ISO)
    
    Actions:
    - Loads sleep data from a JSON file based on the patient number.
    - Loads LFP data from a corresponding JSON file.
    - Loads activity data from a corresponding JSON file.
    - Processes the three data sets to synchronize them based on timestamps.
    - Saves the processed data to a new JSON file.
    """
    patient_sleep = dp.load_json(SLEEP_TGT_PATH / f'{p_file}_Sleep.json')
    patient_lfp = dp.load_json(LFP_TGT_PATH / f'{p_file}_ChronicLFP.json')
    patient_activity = dp.load_json(ACTIVITY_TGT_PATH / f'{p_file}_ActivityData.json')
    
    data=process_data(patient_sleep, patient_lfp, patient_activity)

    unpacked_data = dp.unpack_data(data)
    data_df = pd.DataFrame(unpacked_data)
    data_df['timestamp'] = pd.to_datetime(data_df['timestamp'], format='ISO8601')
    data_df = dp.extract_non_wear_time(data_df)
    data_df.to_csv(DEST_TGT_PATH / f'{p_file}_sync.csv')


def process_data(tgt_sleep_dict: Dict, tgt_lfp_dict: Dict, tgt_activity_dict: Dict) -> Dict:
    """
    Processes and synchronizes sleep and LFP data dictionaries by timestamps.

    Parameters:
    - tgt_sleep_dict (Dict): The dictionary containing sleep data with timestamps.
    - tgt_lfp_dict (Dict): The dictionary containing LFP data with timestamps.
    - tgt_activity_dict (Dict): The dictionary containing activity data with timestamps.

    Returns:
    - Dict: A dictionary where keys are the synchronized Unix timestamps, and values are the merged attributes from both activity, sleep, and LFP data.
    
    Details:
    - Transforms sleep data timestamps into a more usable format.
    - Matches sleep and activity data with LFP data using the closest timestamp approach.
    - Returns a dictionary with combined data from the three sources for each matched timestamp.
    """
    synchronized_dict = {}
    sleep_data_dict = tgt_sleep_dict#.get('data')
    transform_sleep_data, sleep_periods = transform_sleep_dict(sleep_data_dict)
    transform_sleep_data_keyset = list(transform_sleep_data.keys())

    activity_data_dict = tgt_activity_dict#.get('data')
    transform_activity_data, activity_periods = transform_activity_dict(activity_data_dict)
    transform_activity_data_keyset = list(transform_activity_data.keys())    
    for key, value in tgt_lfp_dict.items():
        unix_time_lfp = dp.iso_to_unix(key)
        sleep = {'sleep': None}
        neural = {'neural_data': value}
        activity = {'activity': None}
        if(any(start <= unix_time_lfp <= end for start, end in sleep_periods)):
            tgt_sleep_key = dp.get_closest_unix_time(unix_time_lfp, transform_sleep_data_keyset)
            sleep['sleep'] = transform_sleep_data[tgt_sleep_key]
        
        if(any(start <= unix_time_lfp <= end for start, end in activity_periods)):
            tgt_activity_key = dp.get_closest_unix_time(unix_time_lfp, transform_activity_data_keyset)
            activity = {'activity': transform_activity_data[tgt_activity_key]}
        
        synchronized_dict[dp.unix_to_iso(unix_time_lfp)] = neural | sleep | activity
    return synchronized_dict
    
    
def transform_sleep_dict(tgt_sleep_dict: Dict) -> Dict:  
    """
    Transforms sleep data into a dictionary indexed by Unix timestamps.

    Parameters:
    - tgt_sleep_dict (Dict): The dictionary of sleep data entries, each containing various measurements and a timestamp.

    Returns:
    - Dict: A dictionary where the keys are Unix timestamps and the values are dictionaries containing heart rate, HRV, and sleep phase data.
    
    Details:
    - Each entry's timestamp is converted from ISO 8601 to Unix time.
    - Ensures each transformed data entry contains a consistent set of measurements.
    """ 
    transformed_dict = {}
    sleep_periods = []
    for sleep_dict in tgt_sleep_dict:
        sleep_dict = impute_data(sleep_dict)
        start_unix_time = dp.iso_to_unix(sleep_dict.get('bedtime_start'))
        heart_rate_items = sleep_dict.get('heart_rate').get('items')
        interval = sleep_dict.get('heart_rate').get('interval')
        hrv_items = sleep_dict.get('hrv').get('items')
        sleep_phase = sleep_dict.get('sleep_phase_5_min')
        end_unix_time = dp.iso_to_unix(sleep_dict.get('bedtime_end'))
        sleep_periods.append((start_unix_time, end_unix_time))
        for idx in range(len(sleep_phase)):
            unix_time = start_unix_time + (interval * idx)
            transformed_dict[unix_time] = {'heart_rate': heart_rate_items[idx], 'hrv': hrv_items[idx], 'sleep_phase': sleep_phase[idx]}
        
    return transformed_dict, sleep_periods
    
def transform_activity_dict(tgt_activity_dict: Dict) -> Dict: 
    transformed_dict = {}
    activity_periods = []
    for activity_dict in tgt_activity_dict:
        # activity_dict = impute_data(activity_dict)
        start_unix_time = dp.iso_to_unix(activity_dict.get('timestamp'))
        interval = activity_dict.get('met').get('interval')
        met_items = activity_dict.get('met').get('items')
        activity_periods.append((start_unix_time, start_unix_time+86400))
        for idx in range(len(met_items)):
            unix_time = start_unix_time + (interval * idx)
            transformed_dict[unix_time] = {'met': met_items[idx]}
    return transformed_dict, activity_periods
    
def impute_data(sleep_dict):
    if(sleep_dict.get('heart_rate') == None or sleep_dict.get('hrv') == None):
        LEN = len(sleep_dict.get('sleep_phase_5_min'))
        sleep_dict['heart_rate'] =  {'items': [None for _ in range(LEN)], 'interval': LEN}
        sleep_dict['hrv'] = {'items': [None for _ in range(LEN)]}
        return sleep_dict
    elif(len(sleep_dict['heart_rate']['items']) != len(sleep_dict['hrv']['items']) or (len(sleep_dict['hrv']['items']) != len(sleep_dict['sleep_phase_5_min']))):
        LEN = len(sleep_dict.get('sleep_phase_5_min'))
        heart_rate_list = sleep_dict.get('heart_rate').get('items') + [None] * (LEN - len(sleep_dict.get('heart_rate').get('items')))
        hrv_list = sleep_dict.get('hrv').get('items') + [None] * (LEN - len(sleep_dict.get('hrv').get('items'))) 
        
        sleep_dict['heart_rate']['items'] = heart_rate_list  
        sleep_dict['hrv']['items'] = hrv_list    
        
    
    return sleep_dict

            
if __name__ == "__main__":
    synchronize_all_patients()