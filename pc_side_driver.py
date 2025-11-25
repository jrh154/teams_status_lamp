import time
import serial
import serial.tools.list_ports

BAUD_RATE = 9600
PC_MESSAGE = "R"
HEARTBEAT_TIMEOUT = 10 # in seconds
MAX_LISTEN_TIME = 3

def sendCommand(command, **kwargs):
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
            send_text = ":".join[command, kwargs['status']]
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
    
    send_text += "\n" # add new line
    print(send_text)
    #ser.write(send_text.encode('utf-8'))

def connectToSerial():
    ports = serial.tools.list_ports.comports()

    ser = None

    for port in ports:
        try:
            print(f"Trying port {port.device}")
            ser = serial.Serial(port=port.device, baudrate=BAUD_RATE)
            time.sleep(1)
            print(f"Connected to {port.device}")
        except serial.SerialException as e:
            print(f"Could not connect to {port.device}: {e}")
        
        if ser:
            i = 0
            while i <= MAX_LISTEN_TIME:
                ser_data = ser.readline().strip()
                print(ser_data.strip())
                if ser_data == b"TEAMS_LAMP":
                    print("Teams lamp found")
                    ser.write(b"R\n")
                    time.sleep(0.5)
                    return ser
                time.sleep(0.5)
                #i +=1 
        
def __main__():
    connected = False
    while not connected:
        pass

sendCommand("SET_COLOR", status="ON_CALL", value="RED", value_type="NAME")
ser = connectToSerial()