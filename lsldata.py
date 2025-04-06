import pylsl
import datetime
import csv
import keyboard

# get lsl streams
streams = pylsl.resolve_streams()

# print available streams
for i, stream in enumerate(streams):
    print(f"{i}: {stream.name()} ({stream.type()})")

# get eeg data
stream_name = "EmotivDataStream-EEG"
inlet = pylsl.StreamInlet(pylsl.resolve_byprop("name", stream_name)[0])

# print stream data
info = inlet.info()
print(f"Stream name: {info.name()}")
print(f"Channels: {info.channel_count()}")
print(f"Sampling rate: {info.nominal_srate()} Hz")

# receive data
print("Receiving data...")
time_start = datetime.datetime.now()
key_start = time_start
data_file_path = 'eeg_data.csv'
key_file_path = 'downstroke_data.csv'

time_between_reels = []
data = []


while True:
    sample, timestamp = inlet.pull_sample()  # Get a single sample
    current_time = datetime.datetime.now()
    csv_file_row = [current_time, sample[3], sample[4], sample[5], sample[7]]
    data.append(csv_file_row)
    
    if (keyboard.is_pressed(on_key_down)) {
        time_between_reels.append(current_time - key_start)
        key_start = current_time
    }
    
    if ((current_time - time_start).total_seconds() > 120) {
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)

        with open(key_file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(time_between_reels)
        
        # do model stuff here
    }