import os
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import matplotlib as plt

def load_sleep_data(patient):
    

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

def smooth_data(series, window=5):
    """
    This function applies a moving average smoothing to the data.

    :param series: The pandas Series to smooth.
    :param window: The window size for the moving average. Default is 5.
    :return: The smoothed pandas Series.
    """
    return series.rolling(window=window, min_periods=1, center=True).mean()