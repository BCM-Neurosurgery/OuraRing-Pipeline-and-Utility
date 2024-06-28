import json
from pathlib import Path
from datetime import datetime, timezone, date
from datetime import datetime
from typing import Dict, List
import pytz
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from scipy import stats
import pandas as pd
import numpy as np
import requests
from utilities import *
import matplotlib as plt


def save_json_custom(file_path, data: json):
    """
    Saves data to a JSON file at the specified path, ensuring directory existence.

    Parameters:
    - file_path (Path or str): The file path where the data should be saved.
    - data (Dict): The dictionary data to be saved as JSON.
    
    Actions:
    - Checks and creates the directory path if it does not exist.
    - Writes the data to the file in a formatted (indented) manner.
    """
    
    
    if isinstance(file_path, str):
        file_path = Path(file_path)
    elif not isinstance(file_path, Path):
        raise TypeError("file_path must be a string or a Path object")
    
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    save_file = open(file=file_path, mode='w')
    json.dump(data, save_file, indent=3)
    save_file.close()     


def load_json(file_path) -> Dict:
    """
    Loads JSON data from a specified file path.

    Parameters:
    - file_path (Path): The path to the JSON file to be loaded.

    Returns:
    - Dict: The dictionary containing the data loaded from the JSON file.
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
    - unix_list (List[int]): A list of Unix timestamps to search within.

    Returns:
    - int: The Unix timestamp from the list that is closest to the target.
    
    Details:
    - Uses binary search to efficiently find the closest timestamp.
    - Handles edge cases where the target is beyond the ends of the list.
    """
    pos = bisect_left(unix_list, tgt_unix)
    if pos == 0:
        return unix_list[0]
    if pos == len(unix_list):
        return unix_list[-1]
    before = unix_list[pos - 1]
    after = unix_list[pos]
    if after - tgt_unix < tgt_unix - before:
        return after
    else:
        return before
    

def unpack_data(data):
    records = []
    for timestamp, values in data.items():
        neural_data = values.get("neural_data")
        sleep_data = values.get("sleep") if values.get("sleep") is not None else {}
        activity_data = values.get("activity") if values.get("activity") is not None else {}
        record = {
            "timestamp": timestamp,
            "Chronic_LFP_Left": neural_data.get("Chronic_LFP_Left"),
            "Chronic_LFP_Right": neural_data.get("Chronic_LFP_Right"),
            "Stimulation_Left": neural_data.get("Stimulation_Left"),
            "Stimulation_Right": neural_data.get("Stimulation_Right"),
            "heart_rate": sleep_data.get("heart_rate"),
            "hrv": sleep_data.get("hrv"),
            "sleep_phase": sleep_data.get("sleep_phase"),
            "met": activity_data.get("met")
        }
        records.append(record)
    return records


def filter_lfp_data(df):
    """
    Filters the lfp data from the input dataframe, removing outliers using IQR method. Creates normalized LFP columns (z-scores).

    Parameters:
    - df (DataFrame): input dataframe with chronic LFP data, with column names 'Chronic_LFP_Left' and 'Chronic_LFP_Right'.
    """

    column_name = 'Chronic_LFP_Left'
    Q1 = df[column_name].quantile(0.25)
    Q3 = df[column_name].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df[column_name] = df[column_name].apply(lambda x: None if x < lower_bound or x > upper_bound else x)
    clean_data = pd.to_numeric(df['Chronic_LFP_Left'], errors='coerce').dropna()
    df['Chronic_LFP_Left_norm'] = stats.zscore(clean_data)

    column_name = 'Chronic_LFP_Right'
    Q1 = df[column_name].quantile(0.25)
    Q3 = df[column_name].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df[column_name] = df[column_name].apply(lambda x: None if x < lower_bound or x > upper_bound else x)
    clean_data = pd.to_numeric(df['Chronic_LFP_Right'], errors='coerce').dropna()
    df['Chronic_LFP_Right_norm'] = stats.zscore(clean_data)
    
    return df


def extract_non_wear_time(df):
    """
    This function takes a DataFrame, replaces all occurrences of 0.1 in the "met" column with None,
    and creates a new column "ring_worn" where the value is False if "met" is 0.1 and True otherwise.

    Parameters:
    - df: Input DataFrame with merged LFP, sleep, and activity data
    """
    # Replace 0.1 with None in the "met" column
    df['met'] = df['met'].apply(lambda x: None if x == 0.1 or pd.isna(x) else x)
    
    # Create the "ring_worn" column
    df['ring_worn'] = df.apply(lambda row: True if pd.notnull(row['met']) or pd.notnull(row['sleep_phase']) else False, axis=1)
    return df
    

def mergedjson_to_df(p_file):
    """
    Takes merged json with LFP, sleep, and activity and creates a dataframe with filtered LFP data. Fully processed dataset.

    Parameters:
    - json_filepath (filepath): merged json, which is the output of the synchronize functions in "sleepsynchronizer.py"
    """    
    SYNC_TGT_PATH = Path('JSONs/Sync')
    synced_data = load_json(SYNC_TGT_PATH / f'{p_file}_sync.json')
    unpacked_data = unpack_data(synced_data)
    data_df = pd.DataFrame(unpacked_data)
    # data_df = filter_lfp_data(data_df)
    data_df['timestamp'] = pd.to_datetime(data_df['timestamp'], format='ISO8601')
    data_df = extract_non_wear_time(data_df)
    data_df.to_csv(SYNC_TGT_PATH / f'{p_file}_sync.csv')

    return data_df


def plot_date_range(df, start_date_str="", end_date_str=""):
    """
    Generates a plot for Chronic_LFP_Left_norm and Chronic_LFP_Right_norm with an additional line for stimulation level on the right axis scale.
    
    Parameters:
        data (dict): Dictionary containing timestamp, Chronic_LFP_Left_norm, Chronic_LFP_Right_norm, Stimulation_Left, and sleep_phase data.
        start_date_str (str): Start date in the format 'YYYY-MM-DD HH:MM:SS'. If empty, the entire DataFrame is used.
        end_date_str (str): End date in the format 'YYYY-MM-DD HH:MM:SS'. If empty, the entire DataFrame is used.
    """

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    # Filter the DataFrame based on the provided date range
    if start_date_str and end_date_str:
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        filtered_df = df.loc[mask]
    else:
        filtered_df = df

    # Create traces for the plot
    trace1 = go.Scatter(
        x=filtered_df['timestamp'],
        y=filtered_df['Chronic_LFP_Left_norm'],
        mode='lines',
        name='Chronic LFP Left Norm',
        line=dict(color='blue', width=2)
    )

    trace2 = go.Scatter(
        x=filtered_df['timestamp'],
        y=filtered_df['Chronic_LFP_Right_norm'],
        mode='lines',
        name='Chronic LFP Right Norm',
        line=dict(color='red', width=2)
    )
    
    trace3 = go.Scatter(
        x=filtered_df['timestamp'],
        y=filtered_df['Stimulation_Left'],
        mode='lines',
        name='Stimulation Level',
        line=dict(color='green', width=2),
        yaxis='y2'
    )
    
    if start_date_str and end_date_str:
        start_date_formatted = pd.to_datetime(start_date_str).strftime('%m-%d-%Y %I %p')
        end_date_formatted = pd.to_datetime(end_date_str).strftime('%m-%d-%Y %I %p')
    else:
        start_date_formatted = filtered_df['timestamp'].min().strftime('%m-%d-%Y %I %p')
        end_date_formatted = filtered_df['timestamp'].max().strftime('%m-%d-%Y %I %p')

    # Create the layout
    layout = go.Layout(
        title=f'Chronic LFP Normalized Values from {start_date_formatted} to {end_date_formatted}',
        xaxis=dict(
            title='Time',
            titlefont=dict(size=14),
            tickfont=dict(size=12),
            showgrid=True,
            zeroline=False,
            showline=True,
            mirror=True,
            gridcolor='lightgrey'
        ),
        yaxis=dict(
            title='Normalized Values',
            titlefont=dict(size=14),
            tickfont=dict(size=12),
            showgrid=True,
            zeroline=False,
            showline=True,
            mirror=True,
            gridcolor='lightgrey'
        ),
        yaxis2=dict(
            title='Stimulation Level',
            titlefont=dict(size=14),
            tickfont=dict(size=12),
            overlaying='y',
            side='right',
            showgrid=False,
            zeroline=False,
            showline=True,
            mirror=True
        ),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255, 255, 255, 0.5)',
            bordercolor='rgba(0, 0, 0, 0.5)',
            borderwidth=1
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        hovermode='closest',
        plot_bgcolor='white'
    )

    # Create the figure and add the traces
    fig = go.Figure(data=[trace1, trace2, trace3], layout=layout)

    # Add shaded regions for sleep values that are not None
    shading_start = None

    for i in range(len(filtered_df)):
        if filtered_df['sleep_phase'].iloc[i] is not None:
            if shading_start is None:
                shading_start = filtered_df['timestamp'].iloc[i]
        else:
            if shading_start is not None:
                fig.add_shape(
                    type="rect",
                    x0=shading_start,
                    y0=min(filtered_df['Chronic_LFP_Left_norm'].min(), filtered_df['Chronic_LFP_Right_norm'].min()),
                    x1=filtered_df['timestamp'].iloc[i],
                    y1=max(filtered_df['Chronic_LFP_Left_norm'].max(), filtered_df['Chronic_LFP_Right_norm'].max()),
                    fillcolor="LightSalmon",
                    opacity=0.3,
                    layer="below",
                    line_width=0,
                )
                shading_start = None

    # Handle the case where the last value is part of a sleep phase
    if shading_start is not None:
        fig.add_shape(
            type="rect",
            x0=shading_start,
            y0=min(filtered_df['Chronic_LFP_Left_norm'].min(), filtered_df['Chronic_LFP_Right_norm'].min()),
            x1=filtered_df['timestamp'].iloc[-1],
            y1=max(filtered_df['Chronic_LFP_Left_norm'].max(), filtered_df['Chronic_LFP_Right_norm'].max()),
            fillcolor="LightSalmon",
            opacity=0.3,
            layer="below",
            line_width=0,
        )
        
    # Show the figure
    fig.show()    


def plot_sleep_phase_distribution(data_df, start_date_str, end_date_str):

    # Filter the DataFrame based on the provided date range
    if start_date_str and end_date_str:
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        mask = (data_df['timestamp'] >= start_date) & (data_df['timestamp'] <= end_date)
        filtered_df = data_df.loc[mask]
    else:
        filtered_df = data_df

    # Filter out None values in sleep_phase
    sleep_df = filtered_df[filtered_df['sleep_phase'].notna()]

    # Count occurrences of each sleep phase
    sleep_phase_counts = sleep_df['sleep_phase'].value_counts()

    # Define custom colors
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    # Create a pie chart
    fig = go.Figure(data=[go.Pie(
        labels=sleep_phase_counts.index,
        values=sleep_phase_counts.values,
        hoverinfo='label+percent+value',
        textinfo='label+percent',
        textfont_size=14,
        marker=dict(colors=colors, line=dict(color='#000000', width=2))
    )])

    start_date_formatted = start_date.strftime('%m-%d-%Y %-I %p')
    end_date_formatted = end_date.strftime('%m-%d-%Y %-I %p')   
    # Set the layout for the pie chart
    fig.update_layout(
        title=f"Distribution of Sleep Phases from {start_date_formatted} to {end_date_formatted}",
        legend=dict(x=0, y=1),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    # Show the figure
    fig.show()
    

def create_heatmap(df, start_date_str, end_date_str):
    """
    Generates heatmaps for Chronic_LFP_Left_norm and Chronic_LFP_Right_norm values over time.
    
    Parameters:
        data (dict): Dictionary containing timestamp, Chronic_LFP_Left_norm, Chronic_LFP_Right_norm, and sleep_phase data.
        start_date_str (str): Start date in the format 'YYYY-MM-DD HH:MM:SS'.
        end_date_str (str): End date in the format 'YYYY-MM-DD HH:MM:SS'.
    """

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    # Convert string dates to datetime objects
    start_date = pd.to_datetime(start_date_str)
    end_date = pd.to_datetime(end_date_str)

    # Filter the DataFrame based on the provided date range
    if start_date_str and end_date_str:
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        filtered_df = df.loc[mask]
    else:
        filtered_df = df

    # Create the heatmaps
    heatmap_left = go.Heatmap(
        x=filtered_df['timestamp'],
        y=np.linspace(filtered_df['Chronic_LFP_Left_norm'].min(), filtered_df['Chronic_LFP_Left_norm'].max(), len(filtered_df)),
        z=[filtered_df['Chronic_LFP_Left_norm'].values] * len(filtered_df),
        colorscale='Viridis'
    )

    heatmap_right = go.Heatmap(
        x=filtered_df['timestamp'],
        y=np.linspace(filtered_df['Chronic_LFP_Right_norm'].min(), filtered_df['Chronic_LFP_Right_norm'].max(), len(filtered_df)),
        z=[filtered_df['Chronic_LFP_Right_norm'].values] * len(filtered_df),
        colorscale='Viridis'
    )

    # Create the layout
    layout_left = go.Layout(
        title='Heatmap of Chronic LFP Left Norm Over Time',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Chronic LFP Left Norm'),
        plot_bgcolor='white'
    )

    layout_right = go.Layout(
        title='Heatmap of Chronic LFP Right Norm Over Time',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Chronic LFP Right Norm'),
        plot_bgcolor='white'
    )

    # Create figures
    fig_left = go.Figure(data=[heatmap_left], layout=layout_left)
    fig_right = go.Figure(data=[heatmap_right], layout=layout_right)

    # Show the figures
    fig_left.show()
    fig_right.show()
    

def get_sleep_data():
    
    with open('config.json', 'r') as file:
        config = json.load(file)

    first_date = config['first_date']
    Oura_Token = config['Oura_Token']
    box_directory = Path(config['box_directory'])
    TGT_PATH = Path(config['Oura_data_save_dir'])
    patient_list = [key[-3:] for key in first_date.keys()]
    end_date = str(date.today())
    
    for patient in Oura_Token:
        
        oura_token = Oura_Token[patient]
        start_date = first_date[patient]
        start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
        
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
        filename = Path(TGT_PATH / f'Sleep/Hypnogram/{patient}_Sleep.json')
        save_json_custom(file_path=filename, data=data)
            
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
        filename = Path(TGT_PATH / f'Sleep/Optimal Sleep Times/{patient}_OptimalSleep.json')
        save_json_custom(file_path=filename, data=data)


def get_neural_data():
    
    with open('config.json', 'r') as file:
        config = json.load(file)

    first_date = config['first_date']
    Oura_Token = config['Oura_Token']
    box_directory = Path(config['box_directory'])
    TGT_PATH = Path(config['Oura_data_save_dir'])
    patient_list = [key[-3:] for key in first_date.keys()]
    end_date = str(date.today())
    
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
        save_filename = Path(TGT_PATH / f'Chronic LFP Data/Percept{patient}_ChronicLFP.json')
        save_json_custom(file_path=save_filename, data=nested_dict)


def get_activity_data():
    
    with open('config.json', 'r') as file:
        config = json.load(file)

    first_date = config['first_date']
    Oura_Token = config['Oura_Token']
    box_directory = Path(config['box_directory'])
    TGT_PATH = Path(config['Oura_data_save_dir'])
    patient_list = [key[-3:] for key in first_date.keys()]
    end_date = str(date.today())
    
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
        filename = Path(TGT_PATH / f'Activity/{patient}_Activity.json')
        save_json_custom(file_path=filename, data=data)
        

def analyze_non_wear_time(data_list):
    """
    This function iterates through a list of dictionaries, performing multiple calculations:
    - Counting the number of '0's in "class_5_min" and calculating the percentage difference with "non_wear_time".
    - Summing instances of the value 0.1 in "items" from "met" and calculating the percentage difference with "non_wear_time".
    - Calculating lengths of both "class_5_min" and "items".

    :param data_list: Activity data, list of dictionaries with keys "class_5_min", "non_wear_time", and "met"
    :return: List of results for each dictionary
    """
    results = []

    for data in data_list:
        non_wear_time = data.get("non_wear_time", 0)
        met = data.get("met", {})
        items = met.get("items", [])


        # Calculate for "met" -> "items"
        zero_one_count_met = items.count(0.1)
        zero_time_met = zero_one_count_met * 60
        items_length = len(items)
        percentage_difference_met = None
        if non_wear_time != 0:
            percentage_difference_met = round(((zero_time_met - non_wear_time) / non_wear_time) * 100,1)

        # Append results
        results.append({
            "non_wear_time": non_wear_time,
            "zero_time_met": zero_time_met,
            "percentage_difference_met": percentage_difference_met,
            "items_length": items_length
        })

    return results

def collect_json_data_from_directories(parent_directory):

    """
    Collect data from daily_activity.json and sleep.json files from directories within a parent directory.

    :param parent_directory: The path to the parent directory containing subdirectories to process.
    :return: Two flattened lists containing data from daily_activity.json and sleep.json.
    """
    daily_activity_data = []
    sleep_data = []

    # Get list of subdirectories
    directories = [os.path.join(parent_directory, d) for d in os.listdir(parent_directory) if os.path.isdir(os.path.join(parent_directory, d))]

    # Iterate over each directory
    for directory in directories:
        daily_activity_path = os.path.join(directory, 'daily_activity.json')
        sleep_path = os.path.join(directory, 'sleep.json')

        # Process daily_activity.json
        if os.path.exists(daily_activity_path):
            with open(daily_activity_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    daily_activity_data.extend(data)  # Flatten the list by extending
                else:
                    daily_activity_data.append(data)

        # Process sleep.json
        if os.path.exists(sleep_path):
            with open(sleep_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    sleep_data.extend(data)  # Flatten the list by extending
                else:
                    sleep_data.append(data)
    
    with open('Percept013_ActivityData.json', 'w', encoding='utf-8') as f:
        save_file = open("savedata.json", "w")  
        json.dump(daily_activity_data, f, ensure_ascii=False, indent=4)
        save_file.close()  
    with open('Percept013_Sleep.json', 'w', encoding='utf-8') as f:
        save_file = open("savedata.json", "w")  
        json.dump(sleep_data, f, ensure_ascii=False, indent=4)
        save_file.close()  

    return daily_activity_data, sleep_data


def filter_z_score(df, threshold=2):
    """
    This function replaces 'Chronic_LFP_Left_norm' and 'Chronic_LFP_Right_norm' values with None
    if their z-score exceeds the given threshold.
    
    :param df: Input DataFrame with 'Chronic_LFP_Left_norm' and 'Chronic_LFP_Right_norm' columns.
    :param threshold: Z-score threshold for filtering. Default is 2.
    :return: DataFrame with outliers replaced by None.
    """
    df['Chronic_LFP_Left_norm'] = df['Chronic_LFP_Left_norm'].where(df['Chronic_LFP_Left_norm'].abs() <= threshold, None)
    df['Chronic_LFP_Right_norm'] = df['Chronic_LFP_Right_norm'].where(df['Chronic_LFP_Right_norm'].abs() <= threshold, None)
    return df


def smooth_data(series, window=5):
    """
    This function applies a moving average smoothing to the data.

    :param series: The pandas Series to smooth.
    :param window: The window size for the moving average. Default is 5.
    :return: The smoothed pandas Series.
    """
    return series.rolling(window=window, min_periods=1, center=True).mean()


def plot_intervals(df, patient):
    """
    This function plots 'Chronic_LFP_Left_norm' and 'Chronic_LFP_Right_norm' over time for one-day, two-day, and one-week intervals.
    It highlights periods when 'ring_worn' is False with light red areas and greys out 'sleep_phase' periods.
    It also plots the 'met' value on a separate y-axis with a dotted line.
    Each plot is saved as a JPEG in a subdirectory titled 'LFP Plots Percept{patient}', with folders for '1Day', '2Days', and '1Week'.

    :param df: Input DataFrame with 'timestamp', 'ring_worn', 'Chronic_LFP_Left_norm', 'Chronic_LFP_Right_norm', 'sleep_phase', and 'met' columns.
    :param patient: String containing the patient ID number.
    """
    # Define base folder name
    base_folder = f'LFP Plots Percept{patient}'
    # Define folder names for each interval within the base folder
    folder_1day = os.path.join(base_folder, '1Day')
    folder_2days = os.path.join(base_folder, '2Days')
    folder_1week = os.path.join(base_folder, '1Week')

    # Create directories if they do not exist
    for folder in [folder_1day, folder_2days, folder_1week]:
        os.makedirs(folder, exist_ok=True)

    # Convert 'timestamp' to datetime if not already
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter to start at the first instance of 'ring_worn' == True
    start_index = df[df['ring_worn']].index[0]
    df = df.loc[start_index:].reset_index(drop=True)

    # Apply smoothing to LFP data
    df['Chronic_LFP_Left_norm'] = smooth_data(df['Chronic_LFP_Left_norm'])
    df['Chronic_LFP_Right_norm'] = smooth_data(df['Chronic_LFP_Right_norm'])
    df['met'] = smooth_data(df['met'])

    # Define colors and labels for sleep stages
    sleep_colors = {
        'Awake': (0.800, 0.800, 0.800, 0.6),
        'REM': (0.300, 0.800, 0.700, 0.6),
        'NREM': (0.100, 0.100, 0.350, 0.6)  # Combined color for N3 and non-sleep phases
    }
    sleep_label = {
        1: 'Awake',
        2: 'REM',
        3: 'NREM',
        4: 'NREM'
    }

    # Set 'timestamp' as the DataFrame index for resampling
    df.set_index('timestamp', inplace=True)

    # Define resampling intervals and corresponding folders
    intervals = {
        '1D': folder_1day,
        '2D': folder_2days,
        '1W': folder_1week
    }

    # Plot for each interval
    for interval, folder in intervals.items():
        for start, interval_data in df.resample(interval):
            if interval_data.empty:
                continue

            fig, ax1 = plt.subplots(figsize=(15, 8))

            # Apply more aggressive smoothing for 1-week data
            # if interval == '1W':
                # interval_data.loc[:, 'Chronic_LFP_Left_norm'] = smooth_data(interval_data['Chronic_LFP_Left_norm'])
                # interval_data.loc[:, 'Chronic_LFP_Right_norm'] = smooth_data(interval_data['Chronic_LFP_Right_norm'])
                # interval_data.loc[:, 'met'] = smooth_data(interval_data['met'])

            # Plot Chronic_LFP_Left_norm and Chronic_LFP_Right_norm
            lfp_left_line, = ax1.plot(interval_data.index, interval_data['Chronic_LFP_Left_norm'], label='Chronic_LFP_Left_norm', color='blue')
            lfp_right_line, = ax1.plot(interval_data.index, interval_data['Chronic_LFP_Right_norm'], label='Chronic_LFP_Right_norm', color='green')

            # Create a secondary y-axis for the 'met' values
            ax2 = ax1.twinx()
            met_line, = ax2.plot(interval_data.index, interval_data['met'], label='met', color='black', linestyle='dotted')
            ax2.set_ylabel('met')
            ax2.set_ylim(0.8, 4)  # Normalize the y-axis for 'met'

            if interval == '1W':
                # For one-week intervals, use a solid color for any sleep phase (1-4)
                sleep_mask = interval_data['sleep_phase'].isin([1, 2, 3, 4])
                ax1.fill_between(interval_data.index, -2, 3, where=sleep_mask, color='lightgray', alpha=0.35, step='post', edgecolor='none')
            else:
                # Plot sleep phases step-wise for 1-day and 2-day intervals
                previous_index = None
                for current_index in interval_data.index:
                    sleep_stage = interval_data.loc[current_index, 'sleep_phase']
                    if sleep_stage in sleep_label:
                        stage_label = sleep_label[sleep_stage]
                        color = sleep_colors[stage_label]

                        if previous_index is not None:
                            ax1.fill_between([previous_index, current_index], -2, 3, color=color, alpha=0.35, step='post', edgecolor='none')
                    previous_index = current_index

            # Highlight periods when ring is not worn with light red shading and no edge lines
            previous_index = None
            for current_index in interval_data.index:
                if interval_data.loc[current_index, 'ring_worn'] == False:
                    if previous_index is not None:
                        ax1.fill_between([previous_index, current_index], -2, 3, color='lightcoral', alpha=0.35, step='post', edgecolor='none')
                previous_index = current_index

            # Add labels and legend for the first y-axis
            ax1.set_xlabel('Time')
            ax1.set_ylabel('Normalized LFP')
            ax1.set_ylim(-2, 3)  # Set y-axis limit

            # Legends
            line_legends = [lfp_left_line, lfp_right_line, met_line]
            line_labels = ['Chronic_LFP_Left_norm', 'Chronic_LFP_Right_norm', 'met']
            ax2.legend(line_legends, line_labels, loc='upper right')

            if interval == '1W':
                sleep_stage_labels = ['Sleep', 'Non-Wear']
                sleep_stage_legend = [plt.Line2D([0], [0], color='lightgray', lw=4), plt.Line2D([0], [0], color='lightcoral', lw=4)]
            else:
                # Manually create the legend to match the colors and labels used
                sleep_stage_legend = [
                    plt.Line2D([0], [0], color=sleep_colors['Awake'], lw=4),
                    plt.Line2D([0], [0], color=sleep_colors['REM'], lw=4),
                    plt.Line2D([0], [0], color=sleep_colors['NREM'], lw=4),
                    plt.Line2D([0], [0], color='lightcoral', lw=4)  # Non-Wear
                ]
                sleep_stage_labels = ['Awake', 'REM', 'NREM', 'Non-Wear']

            # Plot the sleep stages legend below the chart
            ax1.legend(sleep_stage_legend, sleep_stage_labels, loc='upper left')

            plt.title(f'Chronic LFP Norms Over {interval} Interval Starting {start.date()}')
            plt.tight_layout()

            # Save the plot as a JPEG file
            plot_filename = os.path.join(folder, f'LFP_Plot_{interval}_Start_{start.date()}.jpeg')
            plt.savefig(plot_filename, format='jpeg')
            plt.close()

def find_first_worn_date(df):
    """
    Finds the first instance where 'ring_worn' equals True in the DataFrame and pulls the corresponding date.

    :param df: DataFrame containing 'timestamp' and 'ring_worn' columns.
    :return: The date of the first 'ring_worn' True instance, or None if not found.
    """
    # Ensure 'timestamp' column is in datetime format
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Find the first instance where 'ring_worn' is True
    first_true_index = df[df['ring_worn'] == True].index.min()
    
    # Check if there was no True instance
    if pd.isna(first_true_index):
        return None
    
    # Pull the corresponding date
    first_worn_date = df.at[first_true_index, 'timestamp']
    
    return first_worn_date

