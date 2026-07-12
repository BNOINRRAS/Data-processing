import numpy as np
import math

MIN_ADC_VALUE = -2048
MAX_ADC_VALUE = 2048

PEDESTAL_RANGE = 30
START_SHIFT = -8
END_SHIFT = 4

PLANES_ORDER = [3, 2, 7, 6, 1, 0, 5, 4]

def find_pulse(oscillograms):
    pulses_start   = []
    pulses_end     = []
    pulses_peak    = []
    pedestals_mean = []

    for i in range(len(oscillograms)):
        # Slicing out first points for the pre-trigger window
        pre_trigger_window = oscillograms[i][0:PEDESTAL_RANGE]
        N = len(pre_trigger_window)
        # Calculating the Mean
        sum_adc = sum(pre_trigger_window)
        pedestal_mean = sum_adc / N
        pedestals_mean.append(pedestal_mean)

        # Calculating the Sample Standard Deviation
        # Sum up the squared deviations from the mean
        sum_squared_deviations = 0
        for adc_value in pre_trigger_window:
            deviation = adc_value - pedestal_mean
            sum_squared_deviations += deviation ** 2

        # Divide by N - 1 and take the square root
        variance = sum_squared_deviations / (N - 1)
        noise_sigma = math.sqrt(variance)

        # print(f"Pedestal Mean: {pedestal_mean:.2f} ADC counts")
        # print(f"Noise Sigma:   {noise_sigma:.2f} ADC counts")

        start_threshold = pedestal_mean - (4 * noise_sigma)
        stop_threshold = pedestal_mean - (1 * noise_sigma)

        pulse_start_index = None
        # Loop from index 30 to the end of the array.
        # We stop 2 samples before the absolute end to avoid an "IndexError" when looking ahead!
        for j in range(30, len(oscillograms[i]) - 2):
            
            # Check if this sample AND the next two samples are ALL below the threshold
            if (oscillograms[i][j] < start_threshold and 
                oscillograms[i][j+1] < start_threshold and 
                oscillograms[i][j+2] < start_threshold):
                
                # We found it! The pulse officially starts at index i
                pulse_start_index = j
                break  # Exit the loop immediately so we don't keep looking

        # if pulse_start_index is not None:
        #     print(f"Pulse safely detected starting at sample index: {pulse_start_index}")
        # else:
        #     print("No pulse found in this event.")
        pulses_start.append(pulse_start_index)

        # If pulse start is found: finding peak time
        pulse_peak_index = None
        if pulse_start_index is not None:
            min_value = MAX_ADC_VALUE
            for j in range(len(oscillograms[i])):
                value = oscillograms[i][j]
                if MIN_ADC_VALUE <= value <= MAX_ADC_VALUE:
                    if value < min_value:
                        min_value = value
                        pulse_peak_index = j
        pulses_peak.append(pulse_peak_index)

        pulse_end_index = None
        # Set a hard safety timeout (e.g., stop looking after 150 samples no matter what)
        if pulse_start_index is not None:
            max_search_limit = min(pulse_peak_index + 150, len(oscillograms[i]) - 2)

            # Loop forward starting from the peak of the pulse
            for j in range(pulse_peak_index, max_search_limit):
                # Check if this sample AND the next two samples have all climbed back 
                # ABOVE (or equal to) the stop threshold
                if (oscillograms[i][j] >= stop_threshold and 
                    oscillograms[i][j+1] >= stop_threshold and 
                    oscillograms[i][j+2] >= stop_threshold):
                    
                    # We found it! The pulse has successfully returned to baseline
                    pulse_end_index = j
                    break

            # if pulse_end_index is not None:
                # print(f"Pulse ends cleanly at sample index: {pulse_end_index}")
            # else:
                # If it hit the safety timeout, force-set the end to the max limit
                # pulse_end_index = max_search_limit
                # print(f"Warning: Pulse did not return to baseline in time. Cut off at index: {pulse_end_index}")
            if pulse_end_index is None:
                # If it hit the safety timeout, force-set the end to the max limit
                pulse_end_index = max_search_limit

        pulses_end.append(pulse_end_index)

    return pulses_start, pulses_end, pulses_peak, pedestals_mean


def shift_to_zero(oscillograms, pedestals_mean):
    for i in range(len(oscillograms)):
        for j in range(0, len(oscillograms[i])):
            oscillograms[i][j] = oscillograms[i][j] - pedestals_mean[i]
    return oscillograms


def axes_to_V_s():
    to_V = 1
    to_s = 1



    return to_V, to_s


def calc_AQ(oscillograms, pulses_start, pulses_end, pulses_peak, pedestals_mean):
    amplitudes = []
    charges = []
    for i in range(len(oscillograms)):
        amplitude = None
        charge = None
        if pulses_start[i] is not None and pulses_end[i] is not None:
            left_border = 0
            right_border = 0

            # Integrate here (from left_border to right_border)
            left_border = max(PEDESTAL_RANGE, pulses_start[i] + START_SHIFT)
            right_border = pulses_end[i] + END_SHIFT




        amplitudes.append(amplitude)
        charges.append(charge)

    return amplitudes, charges
