import pylsl
import datetime
import csv
from pynput import keyboard
import threading
import pandas as pd
import numpy as np
import joblib
import random
from sklearn.preprocessing import StandardScaler


def extract_features_from_averaged_eeg(data):
    """
    Extract features from already averaged EEG data
    
    Parameters:
    -----------
    data : DataFrame with columns ['time spent on this reel', 'EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4', 'Label']
    
    Returns:
    --------
    features_df : DataFrame with original and derived features
    """
    # Create a copy to avoid modifying the original
    features_df = data.copy()
    
    # 1. Channel ratios (relationship between different brain regions)
    features_df['frontal_ratio'] = features_df['EEG.AF3'] / features_df['EEG.AF4'].replace(0, np.nan)
    features_df['frontal_ratio'] = features_df['frontal_ratio'].fillna(1)  # Handle division by zero
    
    features_df['temporal_parietal_ratio'] = features_df['EEG.T7'] / features_df['EEG.Pz'].replace(0, np.nan)
    features_df['temporal_parietal_ratio'] = features_df['temporal_parietal_ratio'].fillna(1)
    
    # 2. Frontal Asymmetry (important for emotional processing)
    features_df['frontal_asymmetry'] = features_df['EEG.AF4'] - features_df['EEG.AF3']
    
    # 3. Average activity across regions
    features_df['frontal_avg'] = (features_df['EEG.AF3'] + features_df['EEG.AF4']) / 2
    features_df['overall_avg'] = features_df[['EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4']].mean(axis=1)
    
    # 4. Variance across channels (measure of overall brain synchrony)
    features_df['channel_variance'] = features_df[['EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4']].var(axis=1)
    
    # 5. Engagement measures
    # Frontal and parietal activity often associated with attention/engagement
    features_df['engagement_index'] = (features_df['EEG.AF3'] + features_df['EEG.AF4'] + features_df['EEG.Pz']) / 3
    
    # 6. Create features using squared and cubic terms (non-linear relationships)
    for channel in ['EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4']:
        features_df[f'{channel}_squared'] = features_df[channel] ** 2
    
    # 7. Interaction terms between channels
    features_df['AF3_T7_interaction'] = features_df['EEG.AF3'] * features_df['EEG.T7']
    features_df['AF4_Pz_interaction'] = features_df['EEG.AF4'] * features_df['EEG.Pz']
    
    # 8. Normalized engagement vs. time
    features_df['engagement_per_second'] = features_df['engagement_index'] / features_df['time spent on this reel']
    
    # 9. Log transformations (to handle skewed distributions)
    for channel in ['EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4']:
        # Add small constant to avoid log(0)
        features_df[f'{channel}_log'] = np.log(np.abs(features_df[channel]) + 1e-10)
    
    # 10. Simulated band power ratios based on channel locations
    # AF3 and AF4 have more beta and gamma activity (frontal executive)
    # T7 has more alpha (auditory processing)
    # Pz has more alpha and theta (sensory integration)
    features_df['simulated_theta_beta'] = (features_df['EEG.Pz'] + features_df['EEG.T7']) / (features_df['EEG.AF3'] + features_df['EEG.AF4'] + 1e-10)
    features_df['simulated_alpha_ratio'] = (features_df['EEG.T7'] + features_df['EEG.Pz']) / (features_df['overall_avg'] + 1e-10)
    
    # 11. Time-normalized features
    features_df['AF3_per_second'] = features_df['EEG.AF3'] / features_df['time spent on this reel']
    features_df['AF4_per_second'] = features_df['EEG.AF4'] / features_df['time spent on this reel']
    features_df['T7_per_second'] = features_df['EEG.T7'] / features_df['time spent on this reel']
    features_df['Pz_per_second'] = features_df['EEG.Pz'] / features_df['time spent on this reel']
    
    # 12. Custom features inspired by your plots
    # Simulating a feature that captures the delta/beta ratio pattern
    features_df['custom_activation_index'] = (features_df['EEG.AF3'] * features_df['EEG.Pz']) / (features_df['EEG.T7'] + 1e-10)
    
    return features_df

# Get LSL stream
stream_name = "EmotivDataStream-EEG"
inlet = pylsl.StreamInlet(pylsl.resolve_byprop("name", stream_name)[0])

# Print stream info
info = inlet.info()
print(f"Stream name: {info.name()}")
print(f"Channels: {info.channel_count()}")
print(f"Sampling rate: {info.nominal_srate()} Hz")

# Storage
data_file_path = 'eeg_data.csv'
key_file_path = 'downstroke_data.csv'

data = []
time_start = datetime.datetime.now()
key_start = time_start
pressed = False
stop_collecting = False

times_watched = []

# Collect EEG samples

def run_model(data):
    
    num_rows = len(data)
    num_seconds = num_rows // 128
    # generate random values from 3-40 that together will add up to num_seconds
    reel_times = []
    while num_seconds > 0:
        reel_time = random.randint(3, min(40, num_seconds))
        reel_times.append(reel_time)
        num_seconds -= reel_time
    # Ensure the last reel time is exactly the remaining seconds
    if num_seconds > 0:
        reel_times[-1] += num_seconds
    
    data = pd.DataFrame(data, columns=['EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4'])
    AF3 = []
    T7 = []
    Pz = []
    AF4 = []
    curr_ind = 0
    for time in reel_times:
        num_rows = time * 128  # 128 samples per second
        af3_avg = data.iloc[curr_ind : curr_ind + num_rows]['EEG.AF3'].mean()
        t7_avg = data.iloc[curr_ind : curr_ind + num_rows]['EEG.T7'].mean()
        pz_avg = data.iloc[curr_ind : curr_ind + num_rows]['EEG.Pz'].mean()
        af4_avg = data.iloc[curr_ind : curr_ind + num_rows]['EEG.AF4'].mean()
        AF3.append(af3_avg)
        T7.append(t7_avg)
        Pz.append(pz_avg)
        AF4.append(af4_avg)
        curr_ind += num_rows
        if curr_ind + 128 > len(data):
            break
    
    data = pd.DataFrame()
    data['time spent on this reel'] = reel_times
    data['EEG.AF3'] = AF3
    data['EEG.T7'] = T7
    data['EEG.Pz'] = Pz
    data['EEG.AF4'] = AF4

    model = joblib.load("random_forest_model_new.pkl")
    data = data.dropna()
    data = data.reset_index(drop=True)
    data = extract_features_from_averaged_eeg(data)

    scaler = StandardScaler()
    data = scaler.fit_transform(data)
    predictions = model.predict(data)

    # check if the mode of the predictions is "Excited", if so return true
    mode_prediction = pd.Series(predictions).mode()[0]
    if mode_prediction == "Excited":
        return True
    return False


print("Receiving data...")
while True:
    sample, timestamp = inlet.pull_sample()
    current_time = datetime.datetime.now()

    # Check channel count before accessing specific indices
    if len(sample) >= 8:
        row = [sample[3], sample[4], sample[5], sample[7]]
        data.append(row)

    # Stop after 120 seconds
    if (current_time - time_start).total_seconds() > 120:
        stop_collecting = run_model()
        if stop_collecting:
            break
        else:
            time_start = datetime.datetime.now()

# Save EEG data
with open(data_file_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['time', 'EEG.AF3', 'EEG.T7', 'EEG.Pz', 'EEG.AF4'])  # Optional headers
    writer.writerows(data)

#Save key press timings
with open(key_file_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['time_since_last_down'])  # Optional header
    for time in times_watched:
        writer.writerow([time])

print("Data collection complete.")