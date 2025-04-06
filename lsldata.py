import pylsl
import datetime
import csv
import random
# from pynput import keyboard
import threading

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

# Key listener functions
# def on_press(key):
#     global pressed, key_start, time_between_reels
#     if key == keyboard.Key.down and not pressed:
#         current_time = datetime.datetime.now()
#         delta = current_time - key_start
#         key_start = current_time
#         time_between_reels.append(delta)
#         pressed = True

# def on_release(key):
#     global pressed
#     if key == keyboard.Key.down:
#         pressed = False

# Start listener thread
# listener = keyboard.Listener(on_press=on_press, on_release=on_release)
# listener.start()

times_watched = (random.uniform(3, 42) for _ in range(42))

# Collect EEG samples
print("Receiving data...")
while True:
    sample, timestamp = inlet.pull_sample()
    current_time = datetime.datetime.now()

    # Check channel count before accessing specific indices
    if len(sample) >= 8:
        row = [current_time.time(), sample[3], sample[4], sample[5], sample[7]]
        data.append(row)

    # Stop after 120 seconds
    if (current_time - time_start).total_seconds() > 5:
        stop_collecting = True
        break

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