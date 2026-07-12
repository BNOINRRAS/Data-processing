import tkinter as tk

import data_reader
import processing
import gui_components

BINARY_FILE_NAME = 'BNI202529614.dat'

def main():
    # Читаем заголовок бинарного файла
    # print("Reading binary file header...")
    file_header, file_size = data_reader.read_binary_file_header(BINARY_FILE_NAME)
    # print(file_header, file_size)

    run_number = data_reader.get_current_run(file_header)

    num_of_osc_points = file_header[5]
    # print(f"Number of oscillogram points: {num_of_osc_points}")
    
    # Читаем все события из бинарного файла
    # print("Reading all events from binary file...")
    binary_events_data, binary_event_times, num_of_osc_points = data_reader.read_all_events_from_binary(
        BINARY_FILE_NAME, file_header, file_size)
    # print(f"Total events in binary file: {len(binary_events_data)}")
    
    # Графический интерфейс
    print("Starting GUI...")
    root = tk.Tk()
    app = gui_components.App(root, binary_events_data, binary_event_times, num_of_osc_points, run_number)
    root.mainloop()

if __name__ == "__main__":
    main()
