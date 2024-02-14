# %% Loading in Oura Patient Information
from datetime import date, timedelta
import json
from utilities import *
import pandas as pd

# Load the configuration json containing patient information
with open('config.json', 'r') as file:
    config = json.load(file)

first_date = config['first_date']
Oura_Token = config['Oura_Token']
box_directory = config['box_directory']

end_date = str(date.today())
patient_list = [key[-3:] for key in first_date.keys()]

# %% Oura API Requests

for patient in Oura_Token:
    
    oura_token = Oura_Token[patient]
    start_date = first_date[patient]
    start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
    
    
    
    #  DAILY ACTIVITY DATA
    url = 'https://api.ouraring.com/v2/usercollection/daily_activity' 
    params={ 
        'start_date': f'{start_date}', 
        'end_date': f'{end_date}' 
    }
    headers = { 
    'Authorization': 'Bearer ' + oura_token,
    }
    
    response = requests.request('GET', url, headers=headers, params=params)
    data = response.json()
    filename = f'JSONs/Activity/{patient}_Activity.json'
    save_json_to_file(data, filename)
    
    
    
    #  SLEEP DATA
    url = 'https://api.ouraring.com/v2/usercollection/sleep' 
    params={ 
        'start_date': f'{start_date}', 
        'end_date': f'{end_date}' 
    }
    headers = { 
    'Authorization': 'Bearer ' + oura_token,
    }
    
    response = requests.request('GET', url, headers=headers, params=params)
    data = response.json()
    filename = f'JSONs/Sleep/Hypnogram/{patient}_Sleep.json'
    save_json_to_file(data, filename)
        
    url = 'https://api.ouraring.com/v2/usercollection/sleep_time' 
    params={ 
        'start_date': f'{start_date}', 
        'end_date': f'{end_date}' 
    }
    headers = { 
    'Authorization': 'Bearer ' + oura_token,
    }
    
    response = requests.request('GET', url, headers=headers, params=params)
    data = response.json()
    filename = f'JSONs/Sleep/Optimal Sleep Times/{patient}_OptimalSleep.json'
    save_json_to_file(data, filename)
    
    
    
    # STRESS DATA
    url = 'https://api.ouraring.com/v2/usercollection/daily_stress' 
    params={ 
        'start_date': f'{start_date}', 
        'end_date': f'{end_date}' 
    }
    headers = { 
    'Authorization': 'Bearer ' + oura_token,
    }
    
    response = requests.request('GET', url, headers=headers, params=params)
    data = response.json()
    filename = f'JSONs/Stress/{patient}_StressScores.json'
    save_json_to_file(data, filename)    
        
        
        
    # HEART RATE DATA
    url = 'https://api.ouraring.com/v2/usercollection/heartrate'
    start_date = pd.to_datetime(end_date) - timedelta(days = 30)
    format_start_date = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    
    all_data = {'data': []}
    next_token = None
    
    # This while loop takes pagination into account for Heart Rate request
    while True:
        params={ 
        'start_datetime': f'{format_start_date}-08:00', 
        'end_datetime': f'{end_date}T00:00:00-08:00' 
        }
        
        if next_token is not None:
            params['next_token'] = next_token
            
        headers = { 
        'Authorization': 'Bearer ' + oura_token,
        }
        
        response = requests.request('GET', url, headers=headers, params=params) 
        data = response.json()
        all_data['data'].extend(data['data'])
        
        
        if next_token is None:
            break
        
        next_token = data.get('next_token')[2:]
        
    filename = f'JSONs/Daytime Heart Rate/{patient}_HeartRate.json'
    
    #If existing data is present, this will prevent overwritting and instead append to existing data
    update_heart_rate_json(all_data, filename)

# %% Chronic LFP Extraction From Box

for patient in patient_list:
    if patient == '000' or patient == 'yJY':  # Percept000 is not a clinical patient and JY is a LITT patient; skip them.
        continue

    directory = os.path.join(box_directory, patient, 'LFP', f'{patient}R')

    # Extract and combine chronic LFP data
    times, LFP, stim = extract_chronic_lfp_data(directory)

    # Convert to a single DataFrame
    neural_timeseries = pd.DataFrame({
        'Time': times,
        'Chronic_LFP_Left': LFP['Left'],
        'Chronic_LFP_Right': LFP['Right'],
        'Stimulation_Left': stim['Left'],
        'Stimulation_Right': stim['Right']
    })

    # Convert dataframe to nested dictionary and save
    nested_dict = dataframe_to_nested_dict(neural_timeseries)
    save_filename = f'JSONs/Chronic LFP Data/Percept{patient}_ChronicLFP.json'
    save_json_to_file(nested_dict, save_filename)

# %%
