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

# Configuration
KNOWN_DEVICES_FILE = "known_devices.json"
DEVICE_ID = "TEAMS_LAMP"
BAUD_RATE = 9600
SCAN_TIMEOUT = 3 
LOOP_DELAY = 2   

# --- Helper Functions ---

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
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("Controller thread started.")

    def stop(self):
        self.running = False
        print("Stopping controller...")
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
                try:
                    while self.running:
                        is_on = teams_mic()
                        cmd = "S:ON" if is_on else "S:OFF"
                        ser.write(f"{cmd}\n".encode())
                        
                        # Wait LOOP_DELAY in small chunks to react to stop() faster
                        chunks = int(LOOP_DELAY / 0.1)
                        for _ in range(chunks):
                            if not self.running: break
                            time.sleep(0.1)
                except Exception as e:
                    print(f"Connection error: {e}")
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
        self.root.geometry("300x180")
        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        # UI Elements
        self.status_label = tk.Label(self.root, text="Ready", fg="gray")
        self.status_label.pack(pady=10)

        self.btn_connect = tk.Button(self.root, text="Connect", command=self.on_connect, width=20, bg="#dddddd")
        self.btn_connect.pack(pady=5)

        self.btn_disconnect = tk.Button(self.root, text="Disconnect", command=self.on_disconnect, width=20, bg="#dddddd")
        self.btn_disconnect.pack(pady=5)

        self.btn_forget = tk.Button(self.root, text="Forget All Devices", command=self.on_forget, width=20, bg="#ffcccc")
        self.btn_forget.pack(pady=5)

        # Tray Setup
        self.icon = None
        self.create_tray_icon()
        
        # Auto-start connection on launch (Optional, keeping it manual as per request)

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

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = LampGUI()
    app.run()
