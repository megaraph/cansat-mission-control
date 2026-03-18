# ─────────────────────────────────────────────
#  CanSat Ground Station  |  serial_reader.py
#  Reads raw lines from the HC-12 serial port,
#  validates format, and pushes parsed dicts
#  into the shared data queue.
#  Also emits line_received signal for the
#  live serial monitor debug panel.
# ─────────────────────────────────────────────

import queue
import threading
import time
import platform

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, pyqtSignal

import config

# Expected number of whitespace-delimited fields in a valid packet
EXPECTED_FIELDS = (15, 16)


def _detect_port() -> str:
    """Auto-detect the most likely HC-12 / USB-TTL port."""
    ports = list(serial.tools.list_ports.comports())
    keywords = ["usbserial", "usbmodem", "ch340", "cp210", "ftdi", "uart"]
    for p in ports:
        desc = (p.description + p.device).lower()
        if any(k in desc for k in keywords):
            return p.device
    if platform.system() == "Windows":
        return config.SERIAL_PORT_WINDOWS
    return config.SERIAL_PORT_MAC


def _is_valid_line(fields: list) -> bool:
    """
    Validate that a split line matches the expected CanSat packet schema:

    pressure | ntc_therm | ntc_ms5611 | alt_abs | alt_rel |
    lat | lon | DD/MM/YYYY | ax | ay | az | gx | gy | gz | timestamp_ms

    Rules:
    - Exactly 15 fields
    - Fields 0-6, 8-14 must be numeric
    - Field 7 must have two '/' separators (date)
    - Pressure in plausible range (80000-110000 Pa)
    - Timestamp must be non-negative
    """
    if len(fields) not in EXPECTED_FIELDS:
        return False

    try:
        numeric_indices = list(range(0, 7)) + list(range(8, 15))
        values = {}
        for i in numeric_indices:
            values[i] = float(fields[i])

        date_parts = fields[7].split("/")
        if len(date_parts) != 3:
            return False

        pressure = values[0]
        if not (80000 <= pressure <= 110000):
            return False

        if values[14] < 0:
            return False

        return True

    except (ValueError, IndexError):
        return False


def _parse_line(fields: list) -> dict:
    """Convert validated field list into a typed packet dict."""
    return {
        "phase": "LIVE",
        "pressure": float(fields[0]),
        "ntc_thermistor": float(fields[1]),
        "ntc_ms5611": float(fields[2]),
        "alt_absolute": float(fields[3]),
        "alt_relative": float(fields[4]),
        "latitude": float(fields[5]),
        "longitude": float(fields[6]),
        "gps_date": fields[7],
        "ax": float(fields[8]),
        "ay": float(fields[9]),
        "az": float(fields[10]),
        "gx": float(fields[11]),
        "gy": float(fields[12]),
        "gz": float(fields[13]),
        "timestamp_ms": int(float(fields[14])),
    }


class _Signaller(QObject):
    """Carries Qt signal for cross-thread serial monitor updates."""

    line_received = pyqtSignal(str, bool, list)


class SerialReader(threading.Thread):
    """
    Background thread that reads from the serial port and pushes
    validated packets into out_queue.

    Gracefully handles:
    - Port not found / device unplugged  -> retries every 3 seconds
    - Malformed / non-data lines         -> silently skipped
    - Encoding errors                    -> line dropped

    Every received line (valid or not) is also emitted via
    signaller.line_received(raw_line, valid, fields) so the
    SerialMonitor debug widget can display it live.
    """

    def __init__(self, out_queue: queue.Queue, port: str = None):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self.port = port or _detect_port()
        self._stop_event = threading.Event()
        self.signaller = _Signaller()  # connect to SerialMonitor.append_raw

        self.connected = False
        self.bad_lines = 0
        self.good_lines = 0
        self.last_error = ""

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                self._connect_and_read()
            except serial.SerialException as e:
                self.connected = False
                self.last_error = str(e)
                self._stop_event.wait(timeout=3.0)
            except Exception as e:
                self.connected = False
                self.last_error = f"Unexpected: {e}"
                self._stop_event.wait(timeout=3.0)

    def _connect_and_read(self):
        print(f"[SerialReader] Attempting: {self.port}")
        print(
            f"[SerialReader] Connecting to {self.port} @ {config.SERIAL_BAUD} baud..."
        )

        with serial.Serial(
            port=self.port,
            baudrate=config.SERIAL_BAUD,
            timeout=config.SERIAL_TIMEOUT,
        ) as ser:
            self.connected = True
            self.last_error = ""
            print(f"[SerialReader] Connected.")

            while not self._stop_event.is_set():
                try:
                    raw = ser.readline()
                    if not raw:
                        continue

                    line = raw.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    fields = line.split()
                    valid = _is_valid_line(fields)

                    # Always emit to serial monitor (valid or not)
                    self.signaller.line_received.emit(line, valid, fields)

                    if not valid:
                        self.bad_lines += 1
                        continue

                    packet = _parse_line(fields)
                    self.good_lines += 1

                    try:
                        self.out_queue.put_nowait(packet)
                    except queue.Full:
                        pass

                except serial.SerialException:
                    self.connected = False
                    raise
