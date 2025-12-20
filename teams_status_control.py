import serial
import serial.tools.list_ports
import time

# Configuration
DEVICE_ID = "TEAMS_LAMP"
BAUD_RATE = 9600
SCAN_TIMEOUT = 3 # Seconds to wait for ID on each port
LOOP_DELAY = 2   # Seconds between status updates

# Add ctypes for Windows API calls
import ctypes

def get_active_window_title():
    """
    Returns the title of the currently active window using Windows API.
    """
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value

def teams_mic():
    """
    Checks if Google Chrome is the active window.
    Returns:
        bool: True if Chrome is active, False otherwise.
    """
    try:
        title = get_active_window_title()
        # print(f"Active Window: {title}") # Debugging
        
        # Check for Google Chrome in title
        if "Google Chrome" in title or "Chrome" in title:
            return True
            
    except Exception as e:
        print(f"Error reading window title: {e}")
        
    return False

import json
import os

# Configuration
KNOWN_DEVICES_FILE = "known_devices.json"

def get_port_signature(port):
    """Returns a dictionary signature for a serial port."""
    return {
        "vid": port.vid,
        "pid": port.pid,
        "serial_number": port.serial_number
    }

def load_known_devices():
    """Lengths known devices from JSON file."""
    if not os.path.exists(KNOWN_DEVICES_FILE):
        return []
    try:
        with open(KNOWN_DEVICES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_known_device(port):
    """Saves a confirmed device to the JSON file."""
    signature = get_port_signature(port)
    known = load_known_devices()
    
    # Check if already exists
    if signature not in known:
        known.append(signature)
        try:
            with open(KNOWN_DEVICES_FILE, 'w') as f:
                json.dump(known, f, indent=4)
        except Exception as e:
            print(f"Failed to save device cache: {e}")

def try_connect(port):
    """Attempts to handshake with a specific port."""
    try:
        print(f"Checking {port.device}...")
        s = serial.Serial(port.device, BAUD_RATE, timeout=SCAN_TIMEOUT)
        s.dtr = True
        time.sleep(2) 
        s.reset_input_buffer()
        
        # Proactive Handshake
        s.write("R\n".encode())

        start_time = time.time()
        while time.time() - start_time < SCAN_TIMEOUT:
            if s.in_waiting:
                line = s.readline().decode('utf-8', errors='ignore').strip()
                if DEVICE_ID in line:
                    print(f"Found {DEVICE_ID} on {port.device}!")
                    save_known_device(port) # Cache it!
                    return s
        s.close()
    except (OSError, serial.SerialException):
        pass
    return None

def find_device():
    print("Scanning for Teams Lamp...")
    all_ports = serial.tools.list_ports.comports()
    known_sigs = load_known_devices()

    # Pass 1: Check Known Devices
    remaining_ports = []
    for port in all_ports:
        sig = get_port_signature(port)
        if sig in known_sigs:
            print(f"Checking known device on {port.device}...")
            ser = try_connect(port)
            if ser: return ser
        else:
            remaining_ports.append(port)

    # Pass 2: Check Remaining Ports
    print("Checking other ports...")
    for port in remaining_ports:
        ser = try_connect(port)
        if ser: return ser
            
    print("Device not found.")
    return None

def main():
    while True:
        # 1. Establish Connection
        ser = find_device()
        
        if ser:
            try:
                # 2. Handshake
                print("Sending Handshake...")
                ser.write("R\n".encode())
                
                # 3. Main Control Loop
                while True:
                    is_on_call = teams_mic()
                    
                    cmd = "S:ON" if is_on_call else "S:OFF"
                    print(f"Sending {cmd}...")
                    ser.write(f"{cmd}\n".encode())
                    
                    time.sleep(LOOP_DELAY)
                    
            except (OSError, serial.SerialException):
                print("Connection lost. Retrying...")
                ser.close()
        
        # Wait before rescanning if device was not found or connection lost
        time.sleep(5)

if __name__ == "__main__":
    main()
