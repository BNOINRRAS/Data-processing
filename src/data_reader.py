import struct
import numpy as np

SHORT_INT_SIZE = 2
DELIMITER = 2

NUM_OF_PLANES = 8
NUM_OF_EVENT_HEADER_VALUES = 8

def read_binary_file_header(file_path):
    with open(file_path, "rb") as f:
        file_header = [struct.unpack('h', f.read(SHORT_INT_SIZE))[0] for _ in range(8)]
        f.seek(0, 2)
        file_size = f.tell()
    
    return file_header, file_size

def get_current_run(file_header):
    # Extract values from the file header list
    god = file_header[0]              # Year
    den = file_header[1]              # Day of the year
    # file_header[2] is ignored as it's not the hour
    msk_intervals = file_header[3] - 1  # Number of 15-minute intervals from start of day (MSK) but at the start of RUN (-1)

    unix_time_of_the_run = 0

    # 1. Calculate base seconds for preceding years
    for year in range(1970, god):
        if year % 4 != 0:
            unix_time_of_the_run += 365 * 86400
        elif year % 100 != 0:
            unix_time_of_the_run += 366 * 86400
        elif year % 400 != 0:
            unix_time_of_the_run += 365 * 86400
        else:
            unix_time_of_the_run += 366 * 86400

    # 2. Add days elapsed in the current year
    unix_time_of_the_run += (den - 1) * 86400

    # 3. Add the 15-minute intervals converted to seconds, 
    # then subtract the 3-hour MSK timezone offset (3 * 3600 = 10800 seconds)
    unix_time_of_the_run += (msk_intervals * 15 * 60) - 10800

    # 4. Integer division (// automatically floors the result in Python)
    current_run = (unix_time_of_the_run - 189290700) // (15 * 60)

    return current_run

def parse_event_time_from_header(event_header):
    minute = event_header[4]
    if minute >= 45:
        minute = minute - 45
    elif minute >= 30:
        minute = minute - 30
    elif minute >= 15:
        minute = minute - 15
    
    seconds = event_header[5]
    milliseconds = event_header[6]
    microseconds = event_header[7]
    
    time_in_seconds = minute * 60 + seconds + milliseconds / 1000.0 + microseconds / 1000000.0
    
    return time_in_seconds


def read_all_events_from_binary(file_path, file_header, file_size):
    num_of_osc_points = file_header[5] - 2
    file_header_size = len(file_header) * SHORT_INT_SIZE
    
    # 1. Define the exact layout of a single event block.
    # 'V' stands for raw bytes (void). We use it to map the delimiters so NumPy skips them.
    # np.int16 corresponds to the 'h' (short integer) in struct.unpack.
    event_dtype = np.dtype([
        ('pad1', f'V{DELIMITER}'),
        ('header', np.int16, NUM_OF_EVENT_HEADER_VALUES),
        ('pad2', f'V{DELIMITER}'),
        ('planes', np.dtype([
            ('points', np.int16, num_of_osc_points),
            ('pad3', f'V{3 * DELIMITER}')
        ]), NUM_OF_PLANES)
    ])
    
    event_block_size = event_dtype.itemsize
    total_num_of_events = int((file_size - file_header_size) / event_block_size)
    
    # Read all events from the disk in one go using C-level parsing
    with open(file_path, "rb") as f:
        f.seek(file_header_size)
        # np.fromfile reads the binary data directly into the structured array
        raw_events = np.fromfile(f, dtype=event_dtype, count=total_num_of_events)
    
    events_data = []
    event_times = []
    
    # Iterate over the parsed array to build your dictionary structure
    # This is fast because no disk I/O or byte decoding is happening here.
    for event_id in range(total_num_of_events):
        header = raw_events['header'][event_id]
        
        # Extract the shape (NUM_OF_PLANES, num_of_osc_points) instantly
        oscillograms = raw_events['planes']['points'][event_id]
        
        # Assuming parse_event_time_from_header can accept a numpy array
        event_time = parse_event_time_from_header(header)
        event_times.append(event_time)
        
        events_data.append({
            'event_id': event_id,
            'time': event_time,
            'oscillograms': oscillograms,
            'header': header.tolist() # Convert back to standard python list if needed
        })
        
    return events_data, event_times, num_of_osc_points
