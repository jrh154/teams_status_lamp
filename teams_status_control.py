import serial
import serial.tools.list_ports
import time

# Configuration
DEVICE_ID = "TEAMS_LAMP"
BAUD_RATE = 9600
SCAN_TIMEOUT = 3 # Seconds to wait for ID on each port
LOOP_DELAY = 2   # Seconds between status updates

def teams_mic():
    """
    Placeholder function to check Teams microphone status.
    Returns:
        bool: True if microphone is ON (On Call), False otherwise.
    """
    # TODO: Implement actual Teams API or log checking logic here
    return False

def find_device():
    """
    Scans all available serial ports for the device broadcasting DEVICE_ID.
    Returns:
        serial.Serial: The connected serial object, or None if not found.
    """
    print("Scanning for Teams Lamp...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        try:
            print(f"Checking {port.device}...")
            s = serial.Serial(port.device, BAUD_RATE, timeout=SCAN_TIMEOUT)
            
            # Wait a moment for Arduino reset (DTR)
            time.sleep(2) 
            
            # Clear input buffer
            s.reset_input_buffer()
            
            # Read lines to look for ID
            start_time = time.time()
            while time.time() - start_time < SCAN_TIMEOUT:
                if s.in_waiting:
                    line = s.readline().decode('utf-8', errors='ignore').strip()
                    if DEVICE_ID in line:
                        print(f"Found {DEVICE_ID} on {port.device}!")
                        return s
            
            s.close()
        except (OSError, serial.SerialException):
            pass
            
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
