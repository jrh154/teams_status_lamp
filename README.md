# Teams Status Lamp

A smart desktop lamp that automatically syncs with your Microsoft Teams status. It turns **Red** when you are on a call and **Green** (or your chosen color) when you are available, providing a clear visual "On Air" signal to colleagues or family members.

## Overview

The system consists of two parts:
1.  **PC Application**: A Python-based system tray application that monitors your teams status.
2.  **Hardware Lamp**: An Arduino-based device that receives commands from the PC via USB Serial and changes color accordingly.

## Setup & Installation

### 1. Hardware Driver (CH341SER)
Most compatible Arduino boards (like the Nano clone used in this project) require the **CH341SER** driver to communicate with the PC.
1.  Download the CH341SER driver [available here](https://www.wch-ic.com/downloads/CH341SER_EXE.html).
2.  Run the installer / `SETUP.EXE`.
3.  Click **INSTALL**.
4.  Once finished, your Arduino should appear as a valid COM port (e.g., `COM3`, `COM4`) in Device Manager when plugged in.

### 2. Installing the Teams Lamp Driver
The PC software is packaged as a standalone portable executable.
1.  Download the latest release ZIP file (e.g., `teams_lamp_2025.3.1.zip`).
2.  Extract the contents to a permanent location of your choice (e.g., `C:\Users\YourName\Documents\TeamsLamp`).
    *   *Note: Do not run it directly from the zip file.*

### 3. Run on Startup (Optional but Recommended)
To have the lamp monitoring start automatically with Windows:
1.  Press `Win + R` on your keyboard to open the Run dialog.
2.  Type `shell:startup` and press Enter. This opens your **Startup** folder.
3.  Right-click the `teams_status_control.exe` file you extracted in Step 2.
4.  Select **Create shortcut**.
5.  Drag the newly created shortcut into the **Startup** folder.

## Usage

### Connecting
1.  Launch `teams_status_control.exe`.
2.  The application will automatically scan for the lamp on startup. It may take a while to connect if this is the first time you are connecting.
3.  If found, the status will change to **Connected** and the LEDs will briefly blink to confirm.
4.  If not found, or if you plug the lamp in later, click the **Connect** button in the app window to rescan.

### Functionality
-   **Teams Status Monitoring**: The app sits in your system tray and monitors to see if you are on a Teams call by monitoring microphone usage.
    -   **Mic Active**: Lamp turns **RED** (default "On-Call" color).
    -   **Mic Inactive**: Lamp turns **GREEN** (default "Off-Call" color).
-   **Tray Icon**: 
    -   The app minimizes to the system tray (near the clock) when you close the window.
    -   Double-click the tray icon to restore the main window.
    -   Right-click the tray icon to **Exit** completely.

### Customizing Colors
You can change the colors for both states without reprogramming the Arduino:
1.  Open the application window.
2.  Click **Set On-Call Color** to pick the color for when you are **busy/on a call**.
3.  Click **Set Off-Call Color** to pick the color for when you are **available**.
4.  The lamp will immediately update and preview the new color.
5.  The new colors will be saved to the Arduino EEPROM and will persist between restarts.

### Logs & Troubleshooting
-   **View Log**: Click the **View Log** button to see a live history of connection events and status changes.
-   **Forget Devices**: If you change COM ports or have connection issues, click **Forget All Devices** to clear the cache of known ports.
-   **Log Files**: Logs are physically stored in the `log_files` directory next to the executable.

## Created By

Created by J Hayes and Y Yahel.

Code base is available [on github](https://github.com/jrh154/teams_status_lamp)

