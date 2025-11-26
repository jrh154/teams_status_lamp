import time
import serial
import serial.tools.list_ports

BAUD_RATE = 115200
PC_MESSAGE = "R"
HEARTBEAT_TIMEOUT = 10 # in seconds
MAX_LISTEN_TIME = 6

def sendCommand(ser, command, **kwargs):
    valid_args = ["status", "value_type", "value"]
    valid_commands = ["SET_COLOR", "SET_STATUS"]
    valid_value_types = ["HEX", "RGB", "NAME"]
    valid_status = ["ON_CALL", "OFF_CALL"]

    for key in kwargs:
        if key not in valid_args:
            print(f"Invalid variable passed: {key}")
            return None
        
    if command not in valid_commands:
        print(f"Invalid command: {command}")
        return None
    elif command == "SET_STATUS":
        if kwargs["status"] not in valid_status:
            print(f"Invalid status: {kwargs["status"]}")
        else:
            send_text = ":".join([command, kwargs['status']])
    elif command == "SET_COLOR":
        # Check for command validity
        if kwargs["status"] not in valid_status:
            print(f"Invalid status: {kwargs["status"]}")
            return None
        elif kwargs["value_type"] not in valid_value_types:
            print(f"Invalid Value Type: {kwargs['value_type']}")
            return None
        elif "value" not in kwargs.keys():
            print("No color value provided")
            return None
        else:
            send_text = ":".join([command, kwargs['status'], kwargs['value_type'], kwargs['value']])
    print(send_text)
    ser.write(send_text.encode('utf-8'))
    ser.flush()
    time.sleep(0.5)

def connectToSerial():
    ports = serial.tools.list_ports.comports()

    ser = None

    for port in ports:
        try:
            print(f"Trying port {port.device}")
            ser = serial.Serial(port=port.device, baudrate=BAUD_RATE, timeout=HEARTBEAT_TIMEOUT)
            time.sleep(1)
            print(f"Connected to {port.device}")
        except serial.SerialException as e:
            print(f"Could not connect to {port.device}: {e}")
        
        if ser:
            i = 0
            while i <= MAX_LISTEN_TIME: # LISTENING TIME = MAX_LISTEN_TIME*0.5...more a loop counter
                ser_data = ser.readline().strip()
                print(ser_data.strip())
                if ser_data == b"TEAMS_LAMP":
                    print("Teams lamp found")
                    ser.write(b"R\n")
                    time.sleep(5) # need to add a rest period in here otherwise loop does not break
                    ser.flushInput()
                    return ser
                time.sleep(0.5)
                i +=1 
def read_mcu_updates(ser):
    if ser.in_waiting > 0:
        mcu_message = ser.readline().strip()
        print(f"The MCU Message was: {mcu_message}")

        if mcu_message == b"TEAMS_LAMP":
            return False
    return True        

def __main__():
    connected = False
    ser = None
    on_call = True
    while True:
        while not ser:
            ser = connectToSerial()
        while ser:
            # Read in a non-blocking way to see if lamp has reset
            if not read_mcu_updates(ser):
                break
           
            # send heartbeat to keep connection
            ser.write(b"R\n")
            ser.flush() 
            
            # Quick test script, should flash between Red and  Green every 1 s
            if on_call:
                sendCommand(ser, command="SET_STATUS", status="ON_CALL")
                on_call = not on_call

__main__()