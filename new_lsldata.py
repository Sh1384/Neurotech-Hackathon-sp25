import pylsl
import datetime
import csv
from pynput import keyboard
import threading
import pandas as pd
import numpy as np
import joblib
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
data_file_path = 'live_eeg_data.csv'
key_file_path = 'downstroke_data.csv'

data = []
time_between_reels = []
time_start = datetime.datetime.now()
key_start = time_start
pressed = False
stop_collecting = False

# Key listener functions
def on_press(key):
    global pressed, key_start, time_between_reels
    if key == keyboard.Key.down and not pressed:
        current_time = datetime.datetime.now()
        delta = current_time - key_start
        key_start = current_time
        time_between_reels.append(delta)
        pressed = True

def on_release(key):
    global pressed
    if key == keyboard.Key.down:
        pressed = False

# Start listener thread
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# Collect EEG samples
print("Receiving data...")

def run_model():
    with open(data_file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'ch3', 'ch4', 'ch5', 'ch7'])  # Optional headers
        writer.writerows(data)

    data = pd.read_csv(data_file_path)
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

while True:
    sample, timestamp = inlet.pull_sample()
    current_time = datetime.datetime.now()

    # Check channel count before accessing specific indices
    if len(sample) >= 8:
        row = [current_time, sample[3], sample[4], sample[5], sample[7]]
        data.append(row)

    # Stop after 120 seconds
    if (current_time - time_start).total_seconds() > 120:
        stop_collecting = run_model()
        if stop_collecting:
            break

# Save key press timings
with open(key_file_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['time_since_last_down'])  # Optional header
    writer.writerows([[delta.total_seconds()] for delta in time_between_reels])

print("Data collection complete.")