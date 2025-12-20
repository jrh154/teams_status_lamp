import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import threading
import serial
import serial.tools.list_ports
import time
import json
import os
import ctypes
import sys
import datetime

# Configuration
KNOWN_DEVICES_FILE = "known_devices.json"
LOG_FILE = "teams_status.log"
DEVICE_ID = "TEAMS_LAMP"
BAUD_RATE = 9600
SCAN_TIMEOUT = 3 
LOOP_DELAY = 2
MAX_LOG_LINES = 1000

# --- Helper Functions ---

def trim_log():
    try:
        if os.path.exists(LOG_FILE):
             with open(LOG_FILE, 'r') as f:
                 lines = f.readlines()
             if len(lines) > MAX_LOG_LINES:
                 with open(LOG_FILE, 'w') as f:
                     f.writelines(lines[-MAX_LOG_LINES:])
    except Exception as e:
        print(f"Log trim error: {e}")

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry) # Keep console output
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(entry + "\n")
        trim_log()
    except Exception as e:
        print(f"Logging error: {e}")

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))


def get_active_window_title():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value

def teams_mic():
    try:
        title = get_active_window_title()
        if "Google Chrome" in title or "Chrome" in title:
            return True
    except:
        pass
    return False

def get_port_signature(port):
    return {"vid": port.vid, "pid": port.pid, "serial_number": port.serial_number}

def load_known_devices():
    if not os.path.exists(KNOWN_DEVICES_FILE): return []
    try:
        with open(KNOWN_DEVICES_FILE, 'r') as f: return json.load(f)
    except: return []

def save_known_device(port):
    signature = get_port_signature(port)
    known = load_known_devices()
    if signature not in known:
        known.append(signature)
        try:
            with open(KNOWN_DEVICES_FILE, 'w') as f: json.dump(known, f, indent=4)
        except Exception as e: print(f"Failed to save cache: {e}")

# --- Controller Logic (Background Thread) ---

class LampController:
    def __init__(self):
        self.running = False
        self.thread = None
        self.serial_conn = None

    def start(self):
        if not self.running:
            self.running = True
            log_message("Controller started.")
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            log_message("Disconnect Status Change: Stopped")
        # The thread will exit gracefully when it checks self.running

    def forget_all_devices(self):
        if os.path.exists(KNOWN_DEVICES_FILE):
            try:
                os.remove(KNOWN_DEVICES_FILE)
                print("Known devices cleared.")
            except Exception as e:
                print(f"Error clearing cache: {e}")

    def _try_connect(self, port):
        try:
            print(f"Checking {port.device}...")
            s = serial.Serial(port.device, BAUD_RATE, timeout=SCAN_TIMEOUT)
            s.dtr = True
            time.sleep(2)
            s.reset_input_buffer()
            s.write("R\n".encode()) # Handshake

            start_time = time.time()
            while time.time() - start_time < SCAN_TIMEOUT:
                if not self.running: 
                    s.close()
                    return None
                if s.in_waiting:
                    line = s.readline().decode('utf-8', errors='ignore').strip()
                    if DEVICE_ID in line:
                        print(f"Found {DEVICE_ID} on {port.device}!")
                        log_message(f"Connected to {port.device} (VID:{port.vid} PID:{port.pid} SN:{port.serial_number})")
                        save_known_device(port)
                        return s
            s.close()
        except:
            pass
        return None

    def _find_device(self):
        print("Scanning...")
        all_ports = serial.tools.list_ports.comports()
        known_sigs = load_known_devices()

        # Pass 1
        remaining = []
        for port in all_ports:
            if not self.running: return None
            if get_port_signature(port) in known_sigs:
                print(f"Checking known: {port.device}")
                ser = self._try_connect(port)
                if ser: return ser
            else:
                remaining.append(port)
        
        # Pass 2
        for port in remaining:
            if not self.running: return None
            ser = self._try_connect(port)
            if ser: return ser
            
        print("Device not found.")
        return None

    def _run_loop(self):
        while self.running:
            ser = self._find_device()
            if ser:
                self.serial_conn = ser
                last_mic_status = None
                last_heartbeat = time.time()
                
                try:
                    while self.running:
                        is_on = teams_mic()
                        
                        # Log Mic Status Change
                        if is_on != last_mic_status:
                            status_str = "Detected Active Teams Call" if is_on else "No Active Teams Call Detected"
                            log_message(f"Status Change: {status_str}")
                            last_mic_status = is_on
                        
                        # Log Heartbeat (every 2 mins / 120s)
                        if time.time() - last_heartbeat > 120:
                            log_message("Status Update: Connected and Running")
                            last_heartbeat = time.time()
                            
                        cmd = "S:ON" if is_on else "S:OFF"
                        ser.write(f"{cmd}\n".encode())
                        
                        # Wait LOOP_DELAY in small chunks to react to stop() faster
                        chunks = int(LOOP_DELAY / 0.1)
                        for _ in range(chunks):
                            if not self.running: break
                            time.sleep(0.1)
                except Exception as e:
                    log_message(f"Disconnect Status Change: Connection lost ({e})")
                finally:
                    if self.serial_conn:
                        self.serial_conn.close()
                        self.serial_conn = None
            
            # Wait before rescan
            if self.running:
                for _ in range(50): # 5 seconds
                    if not self.running: break
                    time.sleep(0.1)

# --- GUI Logic ---

class LampGUI:
    def __init__(self):
        self.controller = LampController()
        
        # Tkinter Setup
        self.root = tk.Tk()
        self.root.title("Teams Lamp Control")
        # Adjust geometry for grid layout
        self.root.geometry("350x200") 
        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        # Configure Grid Weights so it looks decent
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        # UI Elements
        
        # Status Label (Top)
        self.status_label = tk.Label(self.root, text="Ready", fg="gray")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Row 1: Connect | Disconnect
        self.btn_connect = tk.Button(self.root, text="Connect", command=self.on_connect, width=20, bg="#dddddd")
        self.btn_connect.grid(row=1, column=0, padx=5, pady=5)

        self.btn_disconnect = tk.Button(self.root, text="Disconnect", command=self.on_disconnect, width=20, bg="#dddddd", state="disabled")
        self.btn_disconnect.grid(row=1, column=1, padx=5, pady=5)

        # Row 2: View Log | Forget All Devices
        self.btn_log = tk.Button(self.root, text="View Log", command=self.open_log_viewer, width=20, bg="#dddddd")
        self.btn_log.grid(row=2, column=0, padx=5, pady=5)

        self.btn_forget = tk.Button(self.root, text="Forget All Devices", command=self.on_forget, width=20, bg="#ffcccc")
        self.btn_forget.grid(row=2, column=1, padx=5, pady=5)

        # Row 3: Set On Color | Set Off Color
        self.btn_on_color = tk.Button(self.root, text="Set On-Call Color", command=lambda: self.pick_color("ON"), width=20, bg="#ddddff")
        self.btn_on_color.grid(row=3, column=0, padx=5, pady=5)

        self.btn_off_color = tk.Button(self.root, text="Set Off-Call Color", command=lambda: self.pick_color("OFF"), width=20, bg="#ddddff")
        self.btn_off_color.grid(row=3, column=1, padx=5, pady=5)

        # Tray Setup
        self.icon = None
        self.create_tray_icon()
        
    def create_tray_icon(self):
        # Generate a simple icon image
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill="white")
        
        menu = pystray.Menu(
            pystray.MenuItem('Open', self.restore_from_tray),
            pystray.MenuItem('Exit', self.quit_app)
        )
        
        self.icon = pystray.Icon("teams_lamp", image, "Teams Lamp", menu)

    def minimize_to_tray(self):
        self.root.withdraw()
        threading.Thread(target=self.icon.run, daemon=True).start()

    def restore_from_tray(self, icon, item):
        self.icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon=None, item=None):
        if self.icon: 
            self.icon.stop()
        self.controller.stop()
        self.root.quit()

    def on_connect(self):
        self.controller.start()
        self.status_label.config(text="Running...", fg="green")
        self.btn_connect.config(state="disabled")
        self.btn_disconnect.config(state="normal")

    def on_disconnect(self):
        self.controller.stop()
        self.status_label.config(text="Stopped", fg="red")
        self.btn_connect.config(state="normal")
        self.btn_disconnect.config(state="disabled")

    def on_forget(self):
        self.controller.forget_all_devices()
        messagebox.showinfo("Success", "Known devices cleared.")

    def open_log_viewer(self):
        log_window = tk.Toplevel(self.root)
        log_window.title("Teams Status Log")
        log_window.geometry("600x400")
        
        from tkinter import scrolledtext
        text_area = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, width=40, height=10)
        text_area.pack(expand=True, fill='both', padx=10, pady=10)
        text_area.config(state='disabled') # Read-only
        
        log_window.last_mtime = 0
        
        def refresh_log():
            try:
                # Check if window still exists
                if not log_window.winfo_exists():
                    return

                log_file_path = LOG_FILE
                if os.path.exists(log_file_path):
                    mtime = os.path.getmtime(log_file_path)
                    if mtime > log_window.last_mtime:
                        log_window.last_mtime = mtime
                        with open(log_file_path, 'r') as f:
                            content = f.read()
                            
                        text_area.config(state='normal')
                        text_area.delete('1.0', tk.END)
                        text_area.insert(tk.INSERT, content)
                        text_area.see(tk.END) # Auto-scroll to bottom
                        text_area.config(state='disabled')
            except Exception as e:
                print(f"Log refresh error: {e}")
            
            # Schedule next refresh
            log_window.after(1000, refresh_log)
            
        # Start polling
        refresh_log()

    def pick_color(self, target):
        try:
            from tkinter import colorchooser
            color = colorchooser.askcolor(title=f"Choose {target} Color")
            if color[1]: # color is ((r,g,b), hex)
                hex_code = color[1]
                rgb = hex_to_rgb(hex_code)
                log_message(f"Color Change: Set {target} to {hex_code} (RGB: {rgb})")
                
                print(f"TODO: Set {target} to {hex_code}")
                # We will add the backend call here in the next step
        except Exception as e:
            print(f"Color picker error: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    log_message("Starting Teams Status Lamp...")
    app = LampGUI()
    app.run()
