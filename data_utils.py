import json
from datetime import datetime, timezone
import numpy as np
import pytz
import os
from glob import glob
import pandas as pd
from scipy.interpolate import PchipInterpolator

def get_patient_cohort(patient):
    """
    Determines the cohort directory for a given patient.

    Parameters:
    - patient (str): Patient identifier.

    Returns:
    - str: Cohort name corresponding to the patient identifier.
    """
    if patient[:1] == 'P':
        cohort = 'PerceptOCD-48392'
    elif patient[:2] == 'AA':
        cohort = 'AA-56119'
    else:
        print(f'Warning: no valid cohort assignment for {patient}')
        
    return cohort

def process_hemisphere(data, hemisphere, central_timezone):
    """
    Extracts and processes LFP and stimulation data for one hemisphere.

    Parameters:
    - data (dict): Raw JSON data from the Percept device.
    - hemisphere (str): Hemisphere to process (e.g., 'Left' or 'Right').
    - central_timezone: Timezone used to convert timestamps to Central Time.

    Returns:
    - dict: A dictionary containing timestamps, LFP measurements, and stimulation amplitudes.
    """
    hemisphere_data = data.get('DiagnosticData', {}).get('LFPTrendLogs', {}).get(f'HemisphereLocationDef.{hemisphere}', {})

    time_data = []
    LFP_data = []
    stim_data = []

    for key in hemisphere_data.keys():
        for entry in hemisphere_data[key]:
            # Convert timestamps from UTC to Central Time
            dt_utc = datetime.strptime(entry['DateTime'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            dt_central = dt_utc.astimezone(central_timezone)
            
            # Store the timestamp and corresponding measurements
            time_data.append(dt_central)
            LFP_data.append(entry['LFP'])
            stim_data.append(entry['AmplitudeInMilliAmps'])

    return {
        'time': time_data,
        'LFP': LFP_data,
        'stim': stim_data
    }

def align_data(all_times, data, indices):
    """
    Aligns measurements to a common set of timestamps.

    Parameters:
    - all_times (list): Complete list of timestamps.
    - data (array): Measurements corresponding to the provided indices.
    - indices (array): Indices mapping the measurements to the common timestamps.

    Returns:
    - list: Measurements aligned to all timestamps, with NaN for missing values.
    """
    aligned_data = np.empty(len(all_times))
    aligned_data.fill(np.nan)
    aligned_data[indices] = data
    
    return aligned_data.tolist()

def extract(fileName):
    """
    Extracts and processes LFP data from a given JSON file.
    
    Parameters:
    - fileName (str): Path to the JSON file containing chronic LFP data.

    Returns:
    - list: Timestamps for each LFP measurement.
    - dict: L and R hemisphere chronic LFP data.
    - dict: L and R hemisphere stimulation data.
    """
    data = json.load(open(fileName))

    central_timezone = pytz.timezone('America/Chicago')

    # Extract LFP and stimulation data for each hemisphere
    left_data = process_hemisphere(data, 'Left', central_timezone)
    right_data = process_hemisphere(data, 'Right', central_timezone)

    # Combine and sort timestamps from both hemispheres
    times = list(set(left_data['time'] + right_data['time']))
    times.sort()

    # Find the positions of each hemisphere's timestamps in the combined timeline
    left_idx = np.intersect1d(times, left_data['time'], return_indices=True)[2]
    right_idx = np.intersect1d(times, right_data['time'], return_indices=True)[2]

    # Align LFP and stim data to the combined timestamp list
    LFP = {
        'Left': align_data(times, left_data['LFP'], left_idx),
        'Right': align_data(times, right_data['LFP'], right_idx)
    }

    stim = {
        'Left': align_data(times, left_data['stim'], left_idx),
        'Right': align_data(times, right_data['stim'], right_idx)
    }

    return times, LFP, stim

def save_json_to_file(data, filename):
    """
    Saves a JSON object to a file, creating the directory if necessary.
    
    Parameters:
    - data: JSON-serializable data to save.
    - filename (str): Path and filename for the output JSON file.

    Returns:
    - None
    """
    directory = os.path.dirname(filename)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(filename, 'w') as file:
        json.dump(data, file, indent=3)
        
def extract_chronic_lfp_data(directory):
    """
    Extract and combine chronic LFP data from multiple JSON files in a directory.
    
    Parameters:
    - directory (str): Path to the directory containing the chronic LFP JSON files.

    Returns:
    - list: Timestamps for each LFP measurement.
    - dict: L and R hemisphere chronic LFP data.
    - dict: L and R hemisphere stimulation data.
    """
    # Find all JSON files containing hcronic LFP data
    fileList = glob(os.path.join(directory, '*.json'))
    
    times = []
    LFP = {'Left': [], 'Right': []}
    stim = {'Left': [], 'Right': []}

    # Extract and combine data from each JSON file
    for fileName in fileList:
        temp_times, temp_LFP, temp_stim = extract(fileName)
        if temp_times:
            times = times + temp_times
            LFP['Left'] = np.concatenate((LFP['Left'], temp_LFP['Left']))
            LFP['Right'] = np.concatenate((LFP['Right'], temp_LFP['Right']))
            stim['Left'] = np.concatenate((stim['Left'], temp_stim['Left']))
            stim['Right'] = np.concatenate((stim['Right'], temp_stim['Right']))

    # Remove duplicate timestamps while preserving corresponding measurements
    times, unique_idx = np.unique(times, return_index=True, equal_nan=False)
    times = times.tolist()

    LFP['Left'] = np.asarray(LFP['Left'])[unique_idx.astype(int)].tolist()
    LFP['Right'] = np.asarray(LFP['Right'])[unique_idx.astype(int)].tolist()
    stim['Left'] = np.asarray(stim['Left'])[unique_idx.astype(int)].tolist()
    stim['Right'] = np.asarray(stim['Right'])[unique_idx.astype(int)].tolist()

    return times, LFP, stim

def dataframe_to_nested_dict(df):
    """
    Converts a dataframe to a nested dictionary using the 'Time' column as the main key.
    
    Parameters:
    - df (DataFrame): DataFrame containing a 'Time' column and LFP and stimulation measurements.

    Returns:
    - dict: A nested dictionary where each timestamp is a key containing the corresponding LFP and stimulation measurements.
    """
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

def fill_outliers_OvER(group: pd.DataFrame, cols_to_fill: list):
    """
    Replaces outliers in the group DataFrame caused by overvoltage readings. Based on the OvER method described in:
    Hanish et al., "Artifact Identification and Mitigation Strategies for Longitudinal Neural Data Collection 
    Onboard the Medtronic Percept DBS Device," IEEE NER 2025.

    Parameters:
        - group (DataFrame): DataFrame containing contiguous LFP data, potentially with outliers and holes.
        - cols_to_fill (list): List of column names to fill outliers in.

    Returns:
        - DataFrame: DataFrame with outliers filled and containing number of overages in each cell.
    """
    new_filled_cols = [(col[:-4] if col.endswith('_raw') else col) + '_OvER' for col in cols_to_fill]
    new_num_overages_cols = [(col[:-4] if col.endswith('_raw') else col) + '_num_overages' for col in cols_to_fill]
    result_df = pd.DataFrame(index=group.index, columns=new_filled_cols + new_num_overages_cols)
    n = 60 # Number of samples per 10 minute average
    v = 2**32 - 1

    for col, new_filled_col, new_num_overages_col in zip(cols_to_fill, new_filled_cols, new_num_overages_cols):
        data = group[col].values
        num_overages = data // (v/n) # Estimate how many voltage overages we had during each 10 minute interval

        # If all samples within the interval are overages, place a NAN in. This will be filled in later when the missing values are filled.
        # This edge case never actually happens in our dataset, but we handle it just in case.
        valid_mask = num_overages < n
        corrected_data = np.empty_like(data, dtype=float)
        corrected_data[valid_mask] = (n * data[valid_mask] - v * num_overages[valid_mask]) / (n - num_overages[valid_mask])
        corrected_data[~valid_mask] = np.nan
        # print(corrected_data)

        result_df[new_filled_col] = corrected_data
        result_df[new_num_overages_col] = num_overages

    return result_df

def interpolate_holes(group: pd.DataFrame, cols_to_fill: list, max_gap: int=12) -> pd.DataFrame:
    """
    Fill missing values (NaNs) in the specified columns of the group DataFrame using PCHIP interpolation, 
    for gaps up to max_gap size.
    
    Parameters:
        group (DataFrame): Input DataFrame with missing values (NaNs).
        cols_to_fill (list): List of column names to fill.
        max_gap (int, optional): Maximum gap size to fill. Default is 12 (2 hours).
    
    Returns:
        DataFrame: DataFrame with missing values filled in the specified columns.
    """
    new_cols = [col + '_interpolate' for col in cols_to_fill]
    filled_df = pd.DataFrame(index=group.index, columns=new_cols)
    filled_df[new_cols] = group[cols_to_fill].values.copy()  # Copy original values to filled DataFrame
    for new_col in new_cols:
        # Identify NaN indices
        nan_indices = np.where(filled_df[new_col].isna())[0]
        not_nan_indices = np.where(filled_df[new_col].notna())[0]
        valid_values = filled_df.loc[filled_df.index[not_nan_indices], new_col].values

        if len(not_nan_indices) < 2: # Not enough data to interpolate
            filled_df[new_col] = np.nan
            continue
        if len(nan_indices) == 0: # Nothing to interpolate
            continue

        # Create the PCHIP interpolator
        interpolator = PchipInterpolator(not_nan_indices, valid_values)
        gaps = np.split(nan_indices, np.where(np.diff(nan_indices) != 1)[0] + 1)
        if len(filled_df) - 1 in gaps[-1]:
            gaps = gaps[:-1]
        if (len(gaps) > 0) and (0 in gaps[0]):
            gaps = gaps[1:]

        for gap in gaps:
            if len(gap) <= max_gap:
                filled_df.loc[filled_df.index[gap], new_col] = interpolator(gap)
        
    return filled_df