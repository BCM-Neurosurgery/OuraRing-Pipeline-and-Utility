import json
import pandas as pd
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone, timedelta
import pytz
from bisect import bisect_left

def load_json(file_path) -> Dict:
    """
    Loads JSON data from a specified file path.

    Parameters:
    - file_path (path): The path to the JSON file to be loaded.

    Returns:
    - dict: The dictionary containing the data loaded from the JSON file.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
    elif not isinstance(file_path, Path):
        raise TypeError("file_path must be a string or a Path object")
    
    with open(file_path, 'r') as file:
        ret = json.load(file)
        
    return ret


def iso_to_unix(date_str):
    """
    Converts an ISO 8601 formatted date string to Unix time.

    Parameters:
    - date_str (str): The ISO 8601 date string.

    Returns:
    - int: The Unix timestamp.
    """
    # Parse the ISO 8601 date string into a datetime object
    dt = datetime.fromisoformat(date_str)
    
    # Convert the datetime object to UTC and then to Unix time
    unix_time = int(dt.astimezone(timezone.utc).timestamp())
    
    return unix_time


def unix_to_iso(unix_timestamp):
    """
    Converts a Unix timestamp to an ISO 8601 formatted string.

    Parameters:
    - unix_timestamp (int): The Unix timestamp to convert.

    Returns:
    - str: The ISO 8601 formatted date string.
    """
    # Convert the Unix timestamp to a datetime object in UTC
    dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    
    # Convert the datetime object to an ISO 8601 formatted string
    iso_date = dt.isoformat()
    
    return iso_date

def iso_to_cst(iso_date_str):
    """
    Converts an ISO 8601 formatted date string from UTC to CST.

    Parameters:
    - iso_date_str (str): The ISO 8601 date string in UTC.

    Returns:
    - str: The ISO 8601 formatted date string in CST.
    """
    # Define the timezone for CST (Central Standard Time)
    cst = pytz.timezone('US/Central')

    # Parse the ISO 8601 date string to a datetime object
    dt_utc = datetime.fromisoformat(iso_date_str)

    # Ensure the datetime object is aware and set to UTC
    dt_utc = dt_utc.replace(tzinfo=pytz.utc)

    # Convert the datetime object to CST
    dt_cst = dt_utc.astimezone(cst)

    # Format the datetime object back to an ISO 8601 string
    iso_date_cst = dt_cst.isoformat()

    return iso_date_cst

def get_closest_unix_time(tgt_unix: int, unix_list: List[int]):
    """
    Finds the closest Unix timestamp in a list to a given target Unix timestamp.

    Parameters:
    - tgt_unix (int): The target Unix timestamp to find the closest match for.
    - unix_list (list[int]): A list of Unix timestamps to search within.

    Returns:
    - int: The Unix timestamp from the list that is closest to the target.
    
    Details:
    - Uses binary search to efficiently find the closest timestamp.
    - Handles edge cases where the target is beyond the ends of the list.
    """
    # Finding the target timestamp's insertion position
    pos = bisect_left(unix_list, tgt_unix)
    
    if pos == 0:
        return unix_list[0]
    if pos == len(unix_list):
        return unix_list[-1]
    
    before = unix_list[pos - 1]
    after = unix_list[pos]
    
    # Returning the closer timestamp
    if after - tgt_unix < tgt_unix - before:
        return after
    else:
        return before

def process_data(tgt_sleep_dict: Dict, tgt_lfp_dict: Dict, tgt_activity_dict: Dict) -> Dict:
    """
    Processes and synchronizes sleep, activity, and LFP data dictionaries by timestamps.

    Parameters:
    - tgt_sleep_dict (dict): The dictionary containing sleep data with timestamps.
    - tgt_lfp_dict (dict): The dictionary containing LFP data with timestamps.
    - tgt_activity_dict (dict): The dictionary containing activity data with timestamps.

    Returns:
    - dict: A dictionary where keys are the synchronized Unix timestamps, and values are the merged attributes from activity, sleep, and LFP datastreams.
    
    Details:
    - Transforms the sleep and activity data structures to index measurements by Unix timestamps.
    - Matches sleep and activity data with LFP data using the closest timestamp approach.
    - Returns a dictionary with combined data from the three sources for each matched timestamp.
    """
    synchronized_dict = {}
    
    # Extract & index sleep data by timestamp (i.e., transform)
    sleep_data_dict = tgt_sleep_dict.get('data')
    transform_sleep_data, sleep_periods = transform_sleep_dict(sleep_data_dict)
    transform_sleep_data_keyset = sorted(transform_sleep_data.keys())

    # Extract & index activity data by timestamp
    activity_data_dict = tgt_activity_dict.get('data')
    transform_activity_data, activity_periods = transform_activity_dict(activity_data_dict)
    transform_activity_data_keyset = sorted(transform_activity_data.keys())
    
    # Align sleep and activity data to each LFP timestamp
    for key, value in tgt_lfp_dict.items():
        unix_time_lfp = iso_to_unix(key)
        local_time = {'timestamp_local': None, 'utc_offset': None} # saving for downstream analyses that require the pt's tz
        
        sleep = {'sleep': None}
        neural = {'neural': value}
        activity = {'activity': None}
        
        # Check whether the LFP timestamp falls within a sleep period
        if(any(start <= unix_time_lfp <= end for start, end in sleep_periods)):
            tgt_sleep_key = get_closest_unix_time(unix_time_lfp, transform_sleep_data_keyset)
            sleep['sleep'] = transform_sleep_data[tgt_sleep_key]
            
            local_time['utc_offset'] = transform_sleep_data[tgt_sleep_key].get('utc_offset')
        
        # Check whether the LFP timestamp falls within an activity period
        if(any(start <= unix_time_lfp <= end for start, end in activity_periods)):
            tgt_activity_key = get_closest_unix_time(unix_time_lfp, transform_activity_data_keyset)
            activity = {'activity': transform_activity_data[tgt_activity_key]}
            
            activity_offset = transform_activity_data[tgt_activity_key].get('utc_offset')
            if local_time['utc_offset'] is None:
                local_time['utc_offset'] = activity_offset
                
        # Add in local time
        if local_time['utc_offset'] is not None:
            local_tz = datetime.strptime(local_time['utc_offset'], '%z').tzinfo
            local_time['timestamp_local'] = datetime.fromtimestamp(unix_time_lfp, tz=local_tz).isoformat()
        
        # Combine neural, sleep, activity, and local tz info for the current timestamp
        synchronized_dict[unix_to_iso(unix_time_lfp)] = neural | sleep | activity | local_time

    return synchronized_dict
    
def transform_sleep_dict(tgt_sleep_dict: Dict) -> Dict:  
    """
    Transforms sleep data into a dictionary indexed by Unix timestamps.

    Parameters:
    - tgt_sleep_dict (dict): The dictionary of sleep data entries, each containing various measurements and a timestamp.

    Returns:
    - dict: A dictionary where the keys are Unix timestamps and the values are dictionaries containing heart rate, HRV, and sleep phase data.
    - list[tuple[int, int]]: A list of tuples containing the Unix start and end timestamps for each sleep period.
    
    Details:
    - Each entry's timestamp is converted from ISO 8601 to Unix time.
    - Ensures each transformed data entry contains a consistent set of measurements.
    """ 
    transformed_dict = {}
    sleep_periods = []
    for sleep_dict in tgt_sleep_dict:
        sleep_dict = align_sleep_metrics(sleep_dict)
        
        # For tracking local time as well
        bedtime_start = datetime.fromisoformat(sleep_dict.get('bedtime_start'))
        offset = bedtime_start.strftime('%z')
        utc_offset = f'{offset[:3]}:{offset[3:]}'
        
        # Convert sleep period boundaries to Unix timestamps
        start_unix_time = iso_to_unix(sleep_dict.get('bedtime_start'))
        end_unix_time = iso_to_unix(sleep_dict.get('bedtime_end'))
        sleep_periods.append((start_unix_time, end_unix_time))
        
        # Extract metrics and their sampling intervals (all three have same sampling freq)
        heart_rate_items = sleep_dict.get('heart_rate').get('items')
        hrv_items = sleep_dict.get('hrv').get('items')
        sleep_phase = sleep_dict.get('sleep_phase_5_min')
        sleep_type = sleep_dict.get('type')
        interval = sleep_dict.get('heart_rate').get('interval')
        
        # Assign data points to their corresponding Unix timestamps
        for idx in range(len(sleep_phase)):
            unix_time = start_unix_time + (interval * idx)
            
            transformed_dict[unix_time] = {
                'heart_rate': heart_rate_items[idx], 
                'hrv': hrv_items[idx], 
                'sleep_phase': sleep_phase[idx], 
                'sleep_type': sleep_type,
                'utc_offset': utc_offset
                }
        
    return transformed_dict, sleep_periods
    
def transform_activity_dict(tgt_activity_dict: Dict) -> Dict:
    """
    Transforms activity data into a dictionary indexed by Unix timestamps.

    Parameters:
    - tgt_activity_dict (dict): The dictionary of activity data entries, each containing various measurements and a timestamp.

    Returns:
    - dict: A dictionary where the keys are Unix timestamps and the values are dictionaries containing MET data.
    - list[tuple[int, int]]: A list of tuples containing the Unix start and end timestamps for each activity period.
    """
    transformed_dict = {}
    activity_periods = []
    for activity_dict in tgt_activity_dict:
        # For tracking local time as well
        activity_start = datetime.fromisoformat(activity_dict.get('timestamp'))
        offset = activity_start.strftime('%z')
        utc_offset = f'{offset[:3]}:{offset[3:]}'
        
        # Convert timestamps to Unix time
        start_unix_time = iso_to_unix(activity_dict.get('timestamp'))
        activity_periods.append((start_unix_time, start_unix_time+86400))
        
        # Extract MET measurements and their sampling interval
        met_items = activity_dict.get('met').get('items')
        interval = activity_dict.get('met').get('interval')
        
        # Assign data points to their corresponding Unix timestamps
        for idx in range(len(met_items)):
            unix_time = start_unix_time + (interval * idx)
            
            transformed_dict[unix_time] = {
                'met': met_items[idx],
                'utc_offset': utc_offset               
                }
            
    return transformed_dict, activity_periods
    
def align_sleep_metrics(sleep_dict: Dict) -> Dict:
    """
    Ensures heart rate, HRV, and sleep phase data are of the same length.

    Parameters:
    - sleep_dict (dict): A dictionary containing sleep phase, heart rate, and HRV data for a single sleep period.

    Returns:
    - dict: The sleep data dictionary with heart rate, HRV, and sleep phase measurements aligned to the same length.

    Details:
    - Fills missing heart rate or HRV data with None values.
    - Ensures heart rate and HRV data have matching lengths.
    - Resolves one-sample discrepancies between sleep phase and heart rate/HRV data by removing the extra endpoint.
    - Raises an error when data lengths differ by more than one sample or when heart rate and HRV lengths do not match.
    """
    sleep_phase = sleep_dict['sleep_phase_5_min']
    LEN = len(sleep_phase)

    # If HR or HRV is completely missing, fill with None
    if sleep_dict.get('heart_rate') is None:
        sleep_dict['heart_rate'] =  {'interval': 300.0, 'items': [None for _ in range(LEN)]}
    if sleep_dict.get('hrv') is None:
        sleep_dict['hrv'] = {'interval': 300.0, 'items': [None for _ in range(LEN)]}

    heart_rate = sleep_dict['heart_rate']['items']
    hrv = sleep_dict['hrv']['items']

    # HR and HRV should have the same length
    if len(heart_rate) != len(hrv):
        raise ValueError(f"HR and HRV lengths don't match: HR={len(heart_rate)}, HRV={len(hrv)}")

    # Handling one-sample endpoint discrepancies
    if len(sleep_phase) == len(heart_rate) + 1:
        sleep_dict['sleep_phase_5_min'] = sleep_phase[:-1]
    elif len(heart_rate) == len(sleep_phase) + 1:
        sleep_dict['heart_rate']['items'] = heart_rate[:-1]
        sleep_dict['hrv']['items'] = hrv[:-1]

    # Anything larger than a one-sample difference is unexpected
    elif len(sleep_phase) != len(heart_rate):
        raise ValueError(
            f"Unexpected sleep data lengths: "
            f"sleep_phase={len(sleep_phase)}, "
            f"HR={len(heart_rate)}, "
            f"HRV={len(hrv)}"
        )

    return sleep_dict

def unpack_data(data):
    """
    Converts synchronized data into a list of records (i.e. restructuring the dict)

    Parameters:
    - data (dict): A dictionary indexed by timestamps containing neural, sleep, and activity data.

    Returns:
    - list[dict]: A list of records containing the timestamp and corresponding data.
    """
    records = []
    for timestamp, values in data.items():
        # Get neural, sleep, and activity data for the current timestamp
        neural_data = values.get("neural")
        sleep_data = values.get("sleep") if values.get("sleep") is not None else {}
        activity_data = values.get("activity") if values.get("activity") is not None else {}
        
        # Combine all measurements into a single record
        record = {
            "timestamp_utc": pd.to_datetime(timestamp, format='ISO8601'),
            "timestamp_local": pd.to_datetime(values.get("timestamp_local"), format='ISO8601'),
            "utc_offset": values.get("utc_offset"),
            
            "Chronic_LFP_Left": neural_data.get("Chronic_LFP_Left"),
            "Chronic_LFP_Right": neural_data.get("Chronic_LFP_Right"),
            "Stimulation_Left": neural_data.get("Stimulation_Left"),
            "Stimulation_Right": neural_data.get("Stimulation_Right"),
            
            "heart_rate": sleep_data.get("heart_rate"),
            "hrv": sleep_data.get("hrv"),
            "sleep_phase": sleep_data.get("sleep_phase"),
            "sleep_type": sleep_data.get("sleep_type"),
            "met": activity_data.get("met")
        }
        records.append(record)
        
    return records

def extract_non_wear_time(df):
    """
    Takes a DataFrame, replaces all occurrences of <0.9 in the "met" column with None, and creates 
    a new column "ring_worn" where the value is False if "met" is <0.9 and True otherwise.

    Parameters:
    - df: Input DataFrame with merged LFP, sleep, and activity data
    Returns:
    - df: Input DataFrame with <0.9 MET values replaced with None and a new "ring_worn" column.
    """
    # Replace values of <0.9 with None in the "met" column
    df['met'] = df['met'].apply(lambda x: None if pd.isna(x) or x < 0.9 else x)
    
    # Create the "ring_worn" column
    df['ring_worn'] = df.apply(lambda row: True if pd.notnull(row['met']) or pd.notnull(row['sleep_phase']) else False, axis=1)
    
    return df