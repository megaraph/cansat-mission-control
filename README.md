# CanSat Ground Station

SpaceX-style real-time telemetry dashboard for CanSat missions.

## Quick start

```bash
# 1. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run in simulation mode (no hardware needed)
python main.py
```

## Switching to live serial data

1. Connect your HC-12 module via USB-TTL adapter
2. Open `config.py` and set:
    ```python
    MOCK_MODE = False
    SERIAL_PORT_MAC     = "/dev/tty.usbserial-XXXX"   # check ls /dev/tty.*
    SERIAL_PORT_WINDOWS = "COM3"                        # check Device Manager
    ```
3. Run `python main.py`

## File structure

```
cansat_dashboard/
├── main.py                  Entry point
├── config.py                All constants, colors, QSS stylesheet
├── mock_generator.py        Simulated flight arc (IDLE→LAUNCH→ASCENT→APOGEE→DESCENT)
├── data_processor.py        Madgwick filter, derived values, CSV logger (QThread)
├── dashboard_window.py      Main window, layout assembly
├── requirements.txt
├── logs/                    CSV session logs saved here
└── widgets/
    ├── metric_panel.py      Left column: large numeric readouts
    ├── plot_panel.py        Center: tabbed live plots (IMU / Environment / GPS)
    ├── orientation_view.py  Right: PyOpenGL 3D orientation viewer
    └── status_panel.py      Right: connection status + CSV logging controls
```

## CSV logging

Click **● REC** in the status panel to begin logging. A timestamped file is created
in the `logs/` directory (e.g. `logs/cansat_20240315_142305.csv`).
Click **■ STOP** to flush and close the file.

## Dependencies

| Library   | Purpose                                    |
| --------- | ------------------------------------------ |
| PyQt6     | UI framework, threading (QThread), signals |
| PyQtGraph | Real-time accelerated plotting             |
| PyOpenGL  | 3D orientation visualisation               |
| numpy     | Numerical processing, Madgwick filter math |
| pyserial  | Serial port communication (live mode)      |

## Extending to live serial

`dashboard_window.py` currently starts `MockDataGenerator`. To switch to real serial,
replace it with a `SerialReader` thread that:

1. Opens the port with `serial.Serial(port, baud, timeout=2)`
2. Reads lines with `ser.readline().decode().strip()`
3. Splits on whitespace and maps fields to the same dict schema
4. Puts packets into `self._data_queue`

The rest of the pipeline (Madgwick, CSV, UI) is hardware-agnostic.
