"""
CircuitPython code to flash a common andode RGB LED or led strip
to MIDI played through the USB port of the circuitpython device

This can also be used to create an audio visualizer with a audio-to-midi
script running live on a PC or laptop.

Two buttons are required for full functionality; one is a "panic" button that
resets everything; the other is a mode button to toggle between modes

The LED strip should be connected to pins D5, D7 and D6 for R, G, and B respectively.

"""
import binascii
import json
import math
import time

import board
import digitalio
import pwmio

import usb_midi

r_pin = pwmio.PWMOut(board.D5, duty_cycle=0, frequency=500)
g_pin = pwmio.PWMOut(board.D7, duty_cycle=0, frequency=500)
b_pin = pwmio.PWMOut(board.D6, duty_cycle=0, frequency=500)

button = digitalio.DigitalInOut(board.D0)
button.switch_to_input(pull=digitalio.Pull.DOWN)
panic_button = digitalio.DigitalInOut(board.D1)
panic_button.switch_to_input(pull=digitalio.Pull.DOWN)

note_on_status = 0x90
note_off_status = 0x80
port = usb_midi.ports[0]

FADE = 0.75
MODES = ["latest", "oldest", "highest", "lowest", "average", "median", "highvel"]
VEL = True

# LEDs

def gradient(pitch):
    """
    pitch is 0-1 float
    Idea is to have something like a tri-phase motor
    Ended up not quite like that, see the commented out section below for a more accurate 
    representation, but these colors are nice
    """
    # r = (math.cos(math.pi * 4 * pitch) + 1) * 127
    # g = (math.cos(math.pi * 4 * pitch + (math.pi / 4)) + 1) * 127
    # b = (math.sin(math.pi * 8 * pitch + (math.pi / 2)) + 1) * 64
    b = pitch * 510 - 255
    r = -(pitch * 510 - 255)
    g = (math.sin((pitch-0.2) * math.pi*(5/3))) * 200 # green is brighter than red and blue, so compensate
    r = r if r >= 0 else 0
    g = g if g >= 0 else 0
    b = b if b >= 0 else 0
    # red is ~3x dimmer to the human eye; patterns with a lot of red
    # suffer from this; so the below compensates, though the whole shebang is dimmer
    g /= 3
    b /= 3
    return r, g, b


def write_rgb(prev_rgb, new_rgb, portamento):
    r, g, b = [old*portamento+(new*(1-portamento)) for old, new in zip(prev_rgb, new_rgb)]
    r_pin.duty_cycle=min(int(r*(65535/255))*2, 65535)
    g_pin.duty_cycle=min(int(g*(65535/255))*2, 65535)
    b_pin.duty_cycle=min(int(b*(65535/255))*2, 65535)
    return [r, g, b]

# MIDI

def mode_comfirm(mode):
    """
    "tap" middle C 'mode' times to confirm mode selection
    """
    for _ in range(mode+1):
        usb_midi.ports[1].write( bytearray([note_on_status, 60, 60]) )
        time.sleep(0.05)
        usb_midi.ports[1].write( bytearray([note_off_status, 60, 0]) )
        time.sleep(0.05)


def reset_tune():
    """
    play a short tune to show reset
    """
    for i in range(60, 0, -12):
        usb_midi.ports[1].write( bytearray([note_on_status, i, 60]) )
        usb_midi.ports[1].write( bytearray([note_on_status, -i+120, 60]) )
        time.sleep(0.05)
        usb_midi.ports[1].write( bytearray([note_off_status, i, 0]) )
        usb_midi.ports[1].write( bytearray([note_off_status, -i+120, 0]) )
        time.sleep(0.05)    


def panic():
    """
    all notes and leds off
    """
    for i in range(0, 127):
        usb_midi.ports[1].write( bytearray([note_off_status, i, 0]) )
    r_pin.duty_cycle=0
    g_pin.duty_cycle=0
    b_pin.duty_cycle=0


def defe(data):
    """
    My digital piano sends many "fe" (in hex) signals, I think they are a kind
    of clock pulse?  in any case, my program does not need them, so here they are
    filtered out to the best of my abilities
    """
    if len(data) > 6 and (data.startswith("fe") or data.endswith("fe")):
        if data.startswith("fe"):
            data = data[2:]
        else:
            data = data[:-2]
    if data and data.count("fe")*2 == len(data):
        data = ""
    return data

# Parse MIDI input and update active notes
def parse_midi(notes):
    """
    Parse MIDI data and update the notes dictionary.

    Parameters:
    - notes (dict): Dictionary containing active notes with their colors and timestamps.

    Returns:
    - notes (dict): Updated notes dictionary.
    """
    # Convert MIDI data to hex format
    data = binascii.hexlify(port.read()).decode()
    # Filter out unnecessary "fe" signals
    data = defe(data)

    # Process MIDI data in chunks
    while len(data) > 5:
        # Extract MIDI event and pitch information
        event = int(data[:2], 16)
        if event == 144:  # Note-On event
            pitch = int(data[2:4], 16)
            vel = int(data[-2:], 16) / 127 if VEL else 1
            # Calculate RGB color based on pitch
            r, g, b = gradient((pitch - 21) / 88)
            # Update notes dictionary with new note information
            notes[pitch] = [r * vel, g * vel, b * vel, time.monotonic(), vel]
        data = data[6:]  # Move to the next chunk

    return notes

# MODES

def average(notes, current, _):
    """
    this averages the colors of the on notes;
    makes a white color most of the time, though
    """
    color = list(notes.values())
    rs = []
    gs = []
    bs = []
    for i in color:
        fadeout = max(-(current - i[3]) + FADE, 0) / FADE
        rs.append(i[0] * fadeout)
        gs.append(i[1] * fadeout)
        bs.append(i[2] * fadeout)
    ln = len(notes)
    r = sum(rs) / ln
    g = sum(gs) / ln
    b = sum(bs) / ln
    return r, g, b


# Calculate the median color of active notes
def median(notes, current, _):
    """
    Calculate the median color of active notes.

    Parameters:
    - notes (dict): Dictionary containing active notes with their colors and timestamps.
    - current (float): Current time.

    Returns:
    - (float, float, float): RGB color values.
    """
    rs = []
    gs = []
    bs = []
    ln = len(notes)

    # Create a reversed dictionary for sorting
    rev_notes = {json.dumps(v): k for k, v in notes.items()}
    # Sort colors based on their order in the original dictionary
    colors = sorted(
        list(notes.values()), key=lambda x: rev_notes[json.dumps(x)]
    )

    # Get the color at the median position
    color = colors[ln // 2]
    fadeout = max(-(current - color[3]) + FADE, 0) / FADE
    rs.append(color[0] * fadeout)
    gs.append(color[1] * fadeout)
    bs.append(color[2] * fadeout)

    # If the number of notes is odd, calculate the median of the next position
    if ln // 2 != ln / 2 and ln != 1:
        color = colors[ln // 2 + 1]
        fadeout = max(-(current - color[3]) + FADE, 0) / FADE
        rs.append(color[0] * fadeout)
        gs.append(color[1] * fadeout)
        bs.append(color[2] * fadeout)

    # Calculate the median RGB values
    r = sum(rs) / ln
    g = sum(gs) / ln
    b = sum(bs) / ln

    return r, g, b


def new_old_high(notes, current, mode):
    """
    handles three modes:

    latest, oldest and highvel

    latest sorts the notes by time and uses that latest one (my preferred!)
    oldest is similar but backwards (not good for much, but it's here)
    highvel uses the loudest note that is currently being played (good for slow songs)
    """
    if MODES[mode] == "highvel":
        color = sorted(
            list(notes.values()),
            key=lambda x: x[4],
        )
    else:
        color = sorted(
            list(notes.values()),
            key=lambda x: x[3],
            reverse=MODES[mode] == "oldest",
        )
    r, g, b, ago, _ = color[-1]
    fadeout = (max(-(current - ago) + FADE, 0) / FADE) * (
        1 + ((len(notes) / (88 * 2)))
    )
    r *= fadeout
    g *= fadeout
    b *= fadeout
    return r, g, b


def high_low(notes, current, mode):
    """
    This sorts which notes get played by pitch, either highest first, or lowest first.
    neither is very nice, but they where easy to make, so why not?
    """
    r, g, b, ago, _ = notes[
        sorted(list(notes.keys()))[-1 if MODES[mode] == "highest" else 0]
    ]
    fadeout = max(-(current - ago) + FADE, 0) / FADE
    r *= fadeout
    g *= fadeout
    b *= fadeout
    return r, g, b

# MAIN

def main():
    """
    Main loop for the RGB LED visualizer.
    """
    # Define functions for different visualizer modes
    mode_funcs = [
        new_old_high,  # New/Old/High velocity mode
        average,       # Average mode
        median,        # Median mode
        high_low       # High/Low pitch mode
    ]
    
    # Initialize mode and portamento (blending between colors)
    mode = 0
    portamento = 0.9
    
    # Dictionary to store active notes with their colors and timestamps
    notes = {}
    
    # Previous RGB values to smoothly transition between colors
    prev_rgb = [0, 0, 0]
    
    # Variable to track the state of the mode toggle button
    pbv = False
    
    # Perform panic/reset and play a tune to indicate reset
    panic()
    reset_tune()
    
    # Main loop
    while True:
        # Check for panic button press
        if panic_button.value:
            panic()
            mode = 0
            time.sleep(2)
            main()
        
        # Check for mode toggle button press
        if button.value and button.value != pbv:
            mode += 1
            if mode >= len(MODES):
                mode = 0
            mode_confirm(mode)
        
        # Update button state for next iteration
        pbv = button.value
        
        # Parse MIDI input and update active notes
        notes = parse_midi(notes)
        
        # Get current time for fading calculations
        current = time.monotonic()
        
        # Remove inactive notes (older than FADE duration)
        for pitch, color in list(notes.items())[:]:
            if time.monotonic() - color[3] > FADE:
                del notes[pitch]
        
        # If there are active notes, calculate and display the color based on the selected mode
        if notes:
            r, g, b = mode_funcs[mode](notes, current, mode)
            prev_rgb = write_rgb(prev_rgb, [r, g, b], portamento)
        else:
            # If no active notes, turn off the LEDs
            prev_rgb = write_rgb(prev_rgb, [0, 0, 0], portamento)
        
        # Aim for approximately 100fps
        time.sleep(max(0.01 - (time.monotonic() - current), 0))


main()
