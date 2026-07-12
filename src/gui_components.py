import numpy as np
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

import processing

NUM_OF_PLANES = 8
PLANES_ORDER = [3, 2, 7, 6, 1, 0, 5, 4]
PLANES_COLORS = ['green', 'yellow', 'black', 'violet', 'orange', 'red', 'blue', 'cyan']

MIN_ADC_VALUE = -2048
MAX_ADC_VALUE = 2048

PEDESTAL_RANGE = 30
START_SHIFT = -8
END_SHIFT = 4

class InteractiveGraph:
    """Управление интерактивным графиком с помощью мыши и интерактивной легенды."""
    
    def __init__(self, ax, canvas):
        self.ax = ax
        self.canvas = canvas
        self.lines = {}
        self.legend_map = {}  # Maps legend elements to a group [main_line, vline1, vline2]
        self.is_panning = False
        self.press_event_xdata = None
        self.press_event_ydata = None
        self.background = None
        
        # Connect mouse interactions
        self.cid_press = self.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_scroll = self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.cid_pick = self.canvas.mpl_connect('pick_event', self.on_pick)
    
    def update_legend(self, legend):
        """Maps legend components to their corresponding data lines and vertical intervals safely."""
        self.legend_map = {}
        leg_lines = legend.get_lines()
        leg_texts = legend.get_texts()
        
        for order_idx, legline in enumerate(leg_lines):
            legline.set_picker(True)
            legline.set_pickradius(5)
            
            # Start the group with just the main waveform line (which always exists)
            group_artists = [self.lines[order_idx]]
            
            # Only add vertical lines to the legend toggle if they exist!
            if f'vstart_{order_idx}' in self.lines:
                group_artists.append(self.lines[f'vstart_{order_idx}'])
            if f'vend_{order_idx}' in self.lines:
                group_artists.append(self.lines[f'vend_{order_idx}'])
                
            self.legend_map[legline] = group_artists
            
        for order_idx, legtext in enumerate(leg_texts):
            legtext.set_picker(True)
            self.legend_map[legtext] = self.legend_map[leg_lines[order_idx]]

    def on_pick(self, event):
        """Toggles visibility for the oscillogram and its vertical lines simultaneously."""
        if event.artist not in self.legend_map:
            return
            
        associated_artists = self.legend_map[event.artist]
        # Use the main oscillogram line (index 0) to determine the target visibility state
        main_line = associated_artists[0]
        is_visible = not main_line.get_visible()
        
        # NEW: Toggle visibility for ALL lines in this specific group
        for artist in associated_artists:
            artist.set_visible(is_visible)
        
        # Fade out the legend items if hidden (alpha 0.2), or make them solid if visible (alpha 1.0)
        for artist, group in self.legend_map.items():
            if group == associated_artists:
                artist.set_alpha(1.0 if is_visible else 0.2)
                
        self.canvas.draw_idle()
    
    def on_press(self, event):
        """Начало панорамирования при нажатии левой кнопки мыши."""
        if event.inaxes != self.ax or event.button != 1:
            return
        
        self.is_panning = True
        self.press_event_xdata = event.xdata
        self.press_event_ydata = event.ydata
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
    
    def on_motion(self, event):
        """Панорамирование при удержании левой кнопки мыши."""
        if not self.is_panning or event.inaxes != self.ax:
            return
        
        dx = event.xdata - self.press_event_xdata
        dy = event.ydata - self.press_event_ydata
        
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        
        self.ax.set_xlim(xmin - dx, xmax - dx)
        self.ax.set_ylim(ymin - dy, ymax - dy)
        
        self.canvas.restore_region(self.background)
        
        # Redraw all active, visible lines dynamically during panning
        for line in self.lines.values():
            if line.get_visible():
                self.ax.draw_artist(line)
                
        self.canvas.blit(self.ax.bbox)
        
        self.press_event_xdata = event.xdata
        self.press_event_ydata = event.ydata
    
    def on_release(self, event):
        """Завершение панорамирования при отпускании кнопки мыши."""
        if self.is_panning:
            self.is_panning = False
            self.background = None
            self.canvas.draw()
    
    def on_scroll(self, event):
        """Масштабирование колесиком мыши."""
        if event.inaxes != self.ax:
            return
        
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        
        scale_factor = 0.8 if event.button == 'up' else 1.25
        
        new_xmin = event.xdata - (event.xdata - xmin) * scale_factor
        new_xmax = event.xdata + (xmax - event.xdata) * scale_factor
        new_ymin = event.ydata - (event.ydata - ymin) * scale_factor
        new_ymax = event.ydata + (ymax - event.ydata) * scale_factor
        
        self.ax.set_xlim(new_xmin, new_xmax)
        self.ax.set_ylim(new_ymin, new_ymax)
        self.canvas.draw_idle()


class App:
    """Main GUI Application for visualizing raw binary event oscillograms."""
    
    def __init__(self, root, binary_events_data, binary_event_times, num_of_osc_points, run_number):
        """
        Initializes the Tkinter window and builds the layout.
        
        Parameters:
        - root: The Tkinter main window object.
        - binary_events_data (list): List of dictionaries containing raw binary event data.
        - binary_event_times (list/array): List of timestamps matching the binary events.
        - num_of_osc_points (int): Number of digitizer samples per oscillogram line.
        """
        self.root = root
        self.root.title("BUST Raw Event Oscillograms")
        root.geometry("1000x600")
        
        # Store raw binary input data properties
        self.binary_events_data = binary_events_data
        self.binary_event_times = binary_event_times
        self.num_of_osc_points  = num_of_osc_points
        self.run_number         = run_number
        self.current_event_index = 0
        
        # Create the main layout container frame
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Setup Matplotlib Plotting Area
        fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, master=main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky=tk.NSEW)
        
        # Connect to your external interactive graph canvas controller
        self.interactive_graph = InteractiveGraph(self.ax, self.canvas)
        
        # Setup the event selection Sidebar frame
        list_frame = tk.Frame(main_frame)
        list_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        
        # Label displays total count of raw binary data points loaded
        list_label = tk.Label(list_frame, text=f"RUN {self.run_number}", font=("Arial", 12, "bold"))
        list_label.pack(side=tk.TOP)
        
        self.scrollbar = tk.Scrollbar(list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 2. Change yscrollcommand to point to our new function below
        self.listbox = tk.Listbox(list_frame, yscrollcommand=self.enforce_handle_height, font=("Arial", 12))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        # 3. Update this line to use self.scrollbar as well
        self.scrollbar.config(command=self.listbox.yview, width=16)
        
        # Populate the listbox using sequential event indices and raw binary times
        for i, bin_time in enumerate(binary_event_times):
            display_text = f"Event {i+1}: t={bin_time:.6f}s"
            self.listbox.insert(tk.END, display_text)
        
        # Bind the listbox selection event to our display updater
        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select)
        
        # Auto-select and display the first waveform row if data array is not empty
        if len(binary_events_data) > 0:
            self.listbox.select_set(0)
            self.listbox.focus_set()
            self.display_event(0)
    
    def enforce_handle_height(self, first, last):
        """Forces the vertical grab handle to stay large enough to click easily."""
        f = float(first)
        l = float(last)
        
        # If the handle height (l - f) drops below 8% of the total track, stretch it
        if (l - f) < 0.04:
            l = f + 0.04
            # Safety check: if stretching pushes it past the bottom, bump it up
            if l > 1.0:
                l = 1.0
                f = 1.0 - 0.04
                
        # Send the final, safe sizes to the scrollbar
        self.scrollbar.set(f, l)

    def display_event(self, event_index):
        """Extracts oscillogram wave vectors and plots them to the canvas area."""
        if event_index < 0 or event_index >= len(self.binary_events_data):
            return
        
        event_info = self.binary_events_data[event_index]
        bin_time = self.binary_event_times[event_index]
        oscillograms = event_info.get('oscillograms')
        
        if oscillograms is None:
            self.ax.clear()
            self.ax.set_title(f"{event_index + 1}: No Oscillogram Data Present")
            self.canvas.draw_idle()
            return

        to_V, to_s = processing.axes_to_V_s()

        pulses_start, pulses_end, pulses_peak, pedestals_mean = processing.find_pulse(oscillograms)
        # oscillograms = processing.shift_to_zero(oscillograms, pedestals_mean) # Optional
        amplitudes, charges = processing.calc_AQ(oscillograms, pulses_start, pulses_end)

        min_value, max_value, peak_time = find_minA_maxA_peakT(oscillograms)
        ordered_planes, ordered_peaks = find_ordered_triggered_planes(pulses_peak)

        self.ax.clear()
        self.ax.set_title(f"Event {event_index + 1} / {len(self.binary_events_data)}   "
                          f"RUN Time={bin_time:.6f}s\n"
                          f"Planes: {ordered_planes}, Times: {ordered_peaks}",
                          fontsize=14, fontweight='bold')
        self.interactive_graph.lines = {}
        
        x_data = np.linspace(0, self.num_of_osc_points, self.num_of_osc_points)
        
        # Plot data lines sequentially
        for order_idx, plane_idx in enumerate(PLANES_ORDER):
            y_data = oscillograms[plane_idx]
            assigned_color = PLANES_COLORS[order_idx]
            
            # 1. Plot the primary oscillogram waveform line
            line, = self.ax.plot(x_data, y_data, label=f'{order_idx + 1}. A: {amplitudes[plane_idx]}, Q: {charges[plane_idx]}', color=assigned_color)
            self.interactive_graph.lines[order_idx] = line
            
            # 2. Plot corresponding start and end vertical lines inside the loop
            # We prefix labels with an underscore so Matplotlib doesn't create separate legend entries for them
            if pulses_start[plane_idx] is not None and pulses_end[plane_idx] is not None:
                v_start = self.ax.axvline(x=max(PEDESTAL_RANGE, pulses_start[plane_idx] + START_SHIFT), color=assigned_color, linestyle='--', linewidth=1.2, label='_v_line')
                v_end = self.ax.axvline(x=pulses_end[plane_idx] + END_SHIFT, color=assigned_color, linestyle='--', linewidth=1.2, label='_v_line')
                
                # Save them into the interactive tracking dictionary using unique text keys
                self.interactive_graph.lines[f'vstart_{order_idx}'] = v_start
                self.interactive_graph.lines[f'vend_{order_idx}'] = v_end
        
        # Capture the legend object and build our updated multi-line interaction map
        leg = self.ax.legend()
        self.interactive_graph.update_legend(leg)
        
        self.ax.set_xlabel('T, ns')
        self.ax.set_ylabel('Amplitude, mV')
        
        if peak_time > 0:
            self.ax.set_xlim(max(0, peak_time - 30), min(self.num_of_osc_points, peak_time + 50))
        else:
            self.ax.set_xlim(0, self.num_of_osc_points)
        
        if min_value < max_value:
            self.ax.set_ylim(min_value * 1.1, max_value * 1.1)
        else:
            self.ax.set_ylim(MIN_ADC_VALUE, MAX_ADC_VALUE)

        self.ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x * to_s * 10e-9:g}"))
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f"{y * to_V * 10e-3:g}"))

        self.canvas.draw_idle()
    
    def on_listbox_select(self, event):
        """Triggers immediately when a user changes row lines inside the list selection box."""
        selection_indices = self.listbox.curselection()
        if selection_indices:
            event_index = selection_indices[0]
            self.current_event_index = event_index
            self.display_event(event_index)


def find_minA_maxA_peakT(oscillograms):
    min_value = MAX_ADC_VALUE
    max_value = MIN_ADC_VALUE
    peak_time = 0
    
    for plane_idx in range(NUM_OF_PLANES):
        for point_idx in range(len(oscillograms[plane_idx])):
            value = oscillograms[plane_idx][point_idx]
            if MIN_ADC_VALUE <= value <= MAX_ADC_VALUE:
                if value < min_value:
                    min_value = value
                    peak_time = point_idx
                if value > max_value:
                    max_value = value
    
    return min_value, max_value, peak_time


def find_ordered_triggered_planes(pulses_peak):
    triggered_planes = []
    triggered_plane_peaks = []
    for order_idx, plane_idx in enumerate(PLANES_ORDER):
        if pulses_peak[plane_idx] is not None:
            triggered_planes.append(order_idx+1)
            triggered_plane_peaks.append(pulses_peak[plane_idx])

    ordered_pairs = sorted(zip(triggered_plane_peaks, triggered_planes))
    ordered_peaks = [weight for weight, item in ordered_pairs]
    ordered_planes = [item for weight, item in ordered_pairs]

    return ordered_planes, ordered_peaks