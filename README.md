# Real-time Audio Equalizer and MIDI Note Sender

This Python script captures audio input from the default microphone, performs real-time Fourier analysis, and adjusts MIDI note and velocity based on the audio signal. It serves as the audio-to-MIDI script mentioned in the CircuitPython RGB LED Visualizer documentation.


## Requirements:
- Python 3.x
- soundcard
- numpy
- matplotlib
- scipy
- mido

## Usage:
1. Connect a MIDI output device.
2. Run the script.
3. Adjust microphone sensitivity and MIDI output levels interactively.

**Note:** This script relies on live audio input, and the microphone should be connected and accessible.

## Setup for Integration with CircuitPython RGB LED Visualizer:
1. Connect the MIDI output of the device running this script to the USB port of the CircuitPython device running the RGB LED Visualizer.
2. Ensure the RGB LED Visualizer script is configured to receive MIDI input through the USB port.

## Integration Steps:
1. Run the RGB LED Visualizer script on the CircuitPython device.
2. Run this audio-to-MIDI script on a computer or another compatible device.
3. Play audio through the default microphone to observe the real-time RGB LED visualizer reacting to the audio input.

## Script Details:

### Adjustable Parameters:
- `WINDOW`: Number of data points for Fourier analysis.

### Functions:
1. `normalize(v)`: Normalize the input array 'v' between 0 and 1.
2. `get_levels(aud_data)`: Perform a Fourier transform on the input audio data and return the resulting levels.
3. `freq_to_note(freq)`: Convert frequency to MIDI note number.
4. `rms(data)`: Calculate the root mean square (RMS) of the input data.
5. `pretty_data(args, eq)`: Display formatted data including MIDI note, velocity, RMS, and equalizer levels.
6. `equalizer(fft, levels)`: Adjust the Fourier transform levels using an equalizer profile.
7. `norm(a, b, x)`: Normalize the input array 'x' between 'a' and 'b'.
8. `get_adjustment_levels(prev_notes, bands)`: Calculate adjustment levels based on previous note frequencies.

### Main Function:
- `main()`: Capture audio input, perform analysis, and adjust MIDI output in real-time.

## Notes:
- Adjust parameters and equalizer profile as needed.
- Connect a MIDI source to the USB port to see the audio-to-MIDI conversion in action.

Feel free to explore and modify the script to suit your specific requirements or integrate it into larger projects.
