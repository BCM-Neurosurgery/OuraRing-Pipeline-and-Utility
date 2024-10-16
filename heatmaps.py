import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import json
from datetime import timedelta
import os

# Load the configuration json containing patient information
with open('config.json', 'r') as file:
    config = json.load(file)

Oura_Token = config['Oura_Token']

for patient in Oura_Token:
    output_dir = f'Heatmaps/{patient}'
    os.makedirs(output_dir, exist_ok=True)

    filepath_activity = f'JSONs/Activity/{patient}_ActivityData.json'
    with open(filepath_activity, 'r') as file:
        data_activity = json.load(file)

    filepath_sleep = f'JSONs/Sleep/Hypnogram/{patient}_Sleep.json'
    with open(filepath_sleep, 'r') as file:
        data_sleep = json.load(file)

    # filepath_LFP = f'JSONs/Sync/{patient}_sync.csv'
    # data_LFP = pd.read_csv(filepath_LFP, index_col=0)
    # data_LFP.index = pd.to_datetime(data_LFP.index)
    # data_LFP.index = data_LFP.index.floor('min')

    # converting JSON data to pandas DataFrame
    df_act = pd.DataFrame(data_activity)
    df_sleep = pd.DataFrame(data_sleep)

    # populating activity data
    data_populate_act = []
    for day in df_act['data']:
        day['timestamp'] = pd.to_datetime(day['timestamp'])

        met_vals = day['met']['items']
        class_5_min = [int(num) for num in day['class_5_min'] for i in range(5)]
        timestamps = [day['timestamp'] + timedelta(minutes=i) for i in range(len(met_vals))]

        day_data_act = [{
            'timestamp':ts, 'date': ts.date(), 'time': ts.time(), 'met': met, 'activity': act}
            for ts, met, act in zip(timestamps, met_vals, class_5_min)]
        data_populate_act.extend(day_data_act)

    # populating sleep data
    data_populate_sleep = []
    for day in df_sleep['data']:
        day['timestamp'] = pd.to_datetime(day['bedtime_start'])

        movement = [int(num) for num in day['movement_30_sec']] # 30 sec resolution
        movement = movement[::2] # decreasing to 1 min resolution
        sleep_phase_5_min = [int(num) for num in day['sleep_phase_5_min'] for i in range(5)]
        heart_rate_5_min = [item for item in day['heart_rate']['items'] for i in range(5)]
        hrv_5_min = [item for item in day['hrv']['items'] for i in range(5)]
        timestamps = [day['timestamp'] + timedelta(minutes=i) for i in range(len(movement))]

        day_data_sleep = [{
            'timestamp':ts, 'date': ts.date(), 'time': ts.time().strftime('%H:%M'), 
            'move': move, 'sleep phase': phase, 'heart rate': hr, 'hrv': hrv}
            for ts, move, phase, hr, hrv in 
            zip(timestamps, movement, sleep_phase_5_min, heart_rate_5_min, hrv_5_min)]
        data_populate_sleep.extend(day_data_sleep)

    # populating LFP data
    # data_populate_LFP = []
    # for index, row in data_LFP.iterrows():
    #     chronic_lfp_left = [row['Chronic_LFP_Left_norm'] for i in range(10)]
    #     chronic_lfp_right = [row['Chronic_LFP_Right_norm'] for i in range(10)]
    #     timestamps = [index + timedelta(minutes=i) for i in range(10)]

    #     day_data_LFP = [{
    #     'timestamp':ts, 'date': ts.date(), 'time': ts.time().strftime('%H:%M'), 
    #     'chronic lfp left norm': lfp_left, 'chronic lfp right norm': lfp_right}
    #     for ts, lfp_left, lfp_right in zip(timestamps, chronic_lfp_left, chronic_lfp_right)]
    #     data_populate_LFP.extend(day_data_LFP)

    # %% Activity heatmaps
    # plotting met values (met = metabolic equivalent)
    # color_scheme = 'YlGnBu'
    color_scheme = 'Blues'
    df_met = pd.DataFrame(data_populate_act)
    met = df_met.pivot(index='time', columns='date', values='met')
    sns.heatmap(met, annot=False, cmap=color_scheme)
    plt.title(f'{patient}: MET')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'MET.jpeg'))
    plt.close()

    # plotting met values: classified in 5 min intervals
    # 5-minute activity classification for the activity period
    # 0 = non-wear, 1 = rest, 2 = inactive, 3 = low activity, 4= med activity, 5 = high activity
    act = df_met.pivot(index='time', columns='date', values='activity')
    sns.heatmap(act, annot=False, cmap=color_scheme)
    plt.title(f'{patient}: MET Classified')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'MET Classified.jpeg'))
    plt.close()

    # %% Sleep heatmaps
    df_sleep = pd.DataFrame(data_populate_sleep)
    df_sleep.set_index('timestamp', inplace=True)
    # for index in df_sleep.index:
    #     index = index.floor('min')
    df_sleep.index = df_sleep.index.floor('min')

    # Reindexing to include times during the day where no sleep data (better plot visualization purposes)
    start_time = df_sleep.index.min()
    end_time = df_sleep.index.max()
    time_range = pd.date_range(start = start_time, end = end_time, freq='1min')
    df_sleep = df_sleep.reindex(time_range)

    for index, row in df_sleep.iterrows():
        df_sleep.at[index, 'date'] = index.date()
        df_sleep.at[index, 'time'] = index.time()

    # df_sleep.to_csv('/Users/saichamarthi/Desktop/sleep_test.csv', index=True)
    # plotting movement, sleep phase, heart rate, and heart rate variability values while asleep
    # movement classification: 1 = no motion, 2 = restless, 3 = tossing and turning, 4 = active
    # sleep phase: 1 = deep sleep, 2 = light sleep, 3 = REM sleep, 4 = awake.
    titles = ['Movement','Sleep Phase','Heart Rate','Heart Rate Variability']
    for m,metric in enumerate(['move','sleep phase','heart rate','hrv']):
        sleep = df_sleep.pivot(index='time', columns='date', values=metric)

        # plotting heatmaps
        sns.heatmap(sleep, annot=False, cmap=color_scheme)
        plt.title(f'{patient}: {titles[m]}')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{titles[m]}.jpeg'))
        plt.close()

    # %% LFP heatmaps
    # df_LFP = pd.DataFrame(data_populate_LFP)
    # df_LFP = df_LFP[(df_LFP['timestamp'] >= start_time) & (df_LFP['timestamp'] <= end_time)]
    # # df_LFP.to_csv('/Users/saichamarthi/Desktop/lfp_test.csv', index=True)

    # LFP_left = df_LFP.pivot(index='time', columns='date', values="chronic lfp left norm")
    # sns.heatmap(LFP_left, annot=False, cmap='YlGnBu')
    # plt.title(f'{patient}: Chronic LFP Norm - Left')
    # plt.tight_layout()
    # plt.savefig(os.path.join(output_dir, 'Chronic LFP Norm - Left.jpeg'))
    # plt.close()

    # LFP_right = df_LFP.pivot(index='time', columns='date', values="chronic lfp right norm")
    # sns.heatmap(LFP_right, annot=False, cmap='YlGnBu')
    # plt.title(f'{patient}: Chronic LFP Norm - Right')
    # plt.tight_layout()
    # plt.savefig(os.path.join(output_dir, 'Chronic LFP Norm - Right.jpeg'))
    # plt.close()