"""
Real-time Audio Equalizer and MIDI Note Sender

This script captures audio input from the default microphone, performs real-time Fourier analysis,
and adjusts MIDI note and velocity based on the audio signal. It utilizes the `soundcard`,
`numpy`, `matplotlib`, `scipy`, and `mido` libraries.

Author: SquidKid-deluxe

Requirements:
- Python 3.x
- soundcard
- numpy
- matplotlib
- scipy
- mido

Usage:
1. Connect a MIDI output device.
2. Run the script.
3. Adjust microphone sensitivity and MIDI output levels interactively.

Note: This script relies on live audio input, and the microphone should be connected and accessible.

"""

import math

import matplotlib.pyplot as plt
import mido
import numpy as np
import soundcard as sc
from scipy.fftpack import fft as ffter

WINDOW = 2048


def normalize(v):
    """
    Normalize the input array 'v' between 0 and 1.

    Parameters:
    - v (numpy.ndarray): Input array.

    Returns:
    - numpy.ndarray: Normalized array.
    """
    return v / max(np.max(v), 0.0000000001)


def get_levels(aud_data):
    """
    Perform a Fourier transform on the input audio data and return the resulting levels.

    Parameters:
    - aud_data (numpy.ndarray): Input audio data.

    Returns:
    - numpy.ndarray: Fourier transform levels.
    """
    fourier = np.abs(np.fft.fft(aud_data)[:WINDOW].real)
    return fourier


def freq_to_note(freq):
    """
    Convert frequency to MIDI note number.

    Parameters:
    - freq (numpy.ndarray): Input frequency.

    Returns:
    - float: MIDI note number.
    """
    return (12 * math.log(freq[0] / 220.0) / math.log(2.0)) + 57.01


def rms(data):
    """
    Calculate the root mean square (RMS) of the input data.

    Parameters:
    - data (numpy.ndarray): Input data.

    Returns:
    - float: RMS value.
    """
    return float(np.sqrt(np.mean(data**2)))


def pretty_data(args, eq):
    """
    Display formatted data including MIDI note, velocity, RMS, and equalizer levels.
    Not really important at all, but looks really cool on a fullscreen terminal.

    Parameters:
    - args (list): List of data values.
    - eq (numpy.ndarray): Equalizer levels.
    """
    text = ""
    for arg in args:
        if isinstance(arg, float):
            text += str(round(arg, 5)).ljust(15)
        else:
            text += str(arg).ljust(15)
    text += "\n"
    for arg in "note vel_delta velocity signal_rms multiplier min_vel max_vel".split():
        text += arg.ljust(15)
    text += "\033[A"
    print(text)
    print("\033[s", end="")
    eq_text = ""
    for idx, i in enumerate(eq):
        eq_text += f"\033[{idx};150H" + ("#" * int(i * 20)).ljust(70)
    print(eq_text)
    print("\033[u", end="")


def equalizer(fft, levels):
    """
    Adjust the Fourier transform levels using an equalizer profile.

    Parameters:
    - fft (numpy.ndarray): Input Fourier transform levels.
    - levels (numpy.ndarray): Equalizer levels.

    Returns:
    - numpy.ndarray: Adjusted Fourier transform levels.
    """
    bands = len(levels)
    fft_bands = np.array_split(fft, bands)
    result = np.empty_like(fft)
    i = 0
    for band, level in zip(fft_bands, levels):
        result[i : i + len(band)] = band * level
        i += len(band)
    return result


def norm(a, b, x):
    """
    Normalize the input array 'x' between 'a' and 'b'.

    Parameters:
    - a (float): Lower bound.
    - b (float): Upper bound.
    - x (numpy.ndarray): Input array.

    Returns:
    - numpy.ndarray: Normalized array.
    """
    return ((b - a) * ((x - np.min(x)) / (np.max(x) - np.min(x)))) + a


def get_adjustment_levels(prev_notes, bands):
    """
    Calculate adjustment levels based on previous note frequencies.

    Parameters:
    - prev_notes (list): List of previous note frequencies.
    - bands (int): Number of equalizer bands.

    Returns:
    - numpy.ndarray: Adjustment levels.
    """
    step = int(len(prev_notes) / bands)
    note_bands = np.histogram(prev_notes, bands)[0].astype(float)
    note_bands = norm(1, 0.1, note_bands)
    return note_bands


```python
def main():
    """
    Main function to capture audio input, perform analysis, and adjust MIDI output in real-time.
    """
    print("\033c")
    # Get the default microphone
    default_mic = sc.default_microphone()
    # connect to all MIDI ports
    port = mido.ports.MultiPort([mido.open_output(i) for i in mido.get_output_names()])

    # Clear the console
    note = None

    with default_mic.recorder(samplerate=48000, blocksize=32) as mic:
        level = 50
        multiplier = 2000
        prev_rms = 0
        prev_levels = [level]
        prev_notes = [i for i in range(1, 10000, 100)]
        lenprevnotes = 100
        bands = 31
        lenprevlevel = 10
        while True:
            freqs = np.fft.fftfreq(WINDOW * 2, d=1 / 48000)[:WINDOW]
            data = mic.record(numframes=WINDOW * 2)[:, 0]

            # Check if the RMS value is significant
            if (rmsdata := rms(data)) > 0.0005:
                # Calculate adjustment levels based on previous note frequencies
                eq = get_adjustment_levels(prev_notes, bands)
                
                # Perform Fourier analysis on the input data
                fft = get_levels(data)[:WINDOW]

                # Identify the frequency with the maximum amplitude before equalization
                freq_noeq = freqs[np.argwhere(fft == np.max(fft))[0]]
                
                # Apply equalization to the Fourier transform
                fft = equalizer(fft, eq)
                
                # Identify the frequency with the maximum amplitude after equalization
                freq = freqs[np.argwhere(fft == np.max(fft))[0]]

                # Adjust the multiplier based on previous MIDI levels
                if max(prev_levels) < 127 and min(prev_levels) > 0:
                    multiplier *= 1.01
                elif max(prev_levels) > 127 or min(prev_levels) < 0:
                    multiplier *= 0.99

                # Calculate velocity based on RMS change and multiplier
                vel = (rmsdata - prev_rms) * multiplier

                # Turn off the previous note (if any)
                if note is not None:
                    port.send(mido.Message("note_off", note=note, velocity=0))

                # Calculate the MIDI note number based on the adjusted frequency
                note = min(max(int(round(freq_to_note(freq + 0.000001))), 0), 127)

                # Adjust the MIDI velocity and send the note-on message
                if note:
                    level += vel
                    prev_notes.append(freq[0])
                    prev_levels.append(level)
                    level = min(max(level, 0), 127)
                    port.send(mido.Message("note_on", note=note, velocity=int(level)))

                    # Update the previous RMS value
                    prev_rms = rmsdata

                    # Keep track of the sliding window of previous MIDI levels and notes
                    if len(prev_levels) > lenprevlevel:
                        prev_levels.pop(0)
                    if len(prev_notes) > lenprevnotes:
                        prev_notes.pop(0)

                    # Display formatted data and equalizer profile
                    pretty_data(
                        [
                            note,
                            vel,
                            level,
                            rmsdata,
                            multiplier,
                            min(prev_levels),
                            max(prev_levels),
                        ],
                        eq,
                    )


if __name__ == "__main__":
    main()
