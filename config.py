# ─────────────────────────────────────────────
#  CanSat Ground Station  |  config.py
# ─────────────────────────────────────────────

# ── Serial ──────────────────────────────────
SERIAL_PORT_MAC = "/dev/tty.usbserial-0001"
SERIAL_PORT_WINDOWS = "COM3"
SERIAL_BAUD = 9600
SERIAL_TIMEOUT = 2.0

# ── Data ────────────────────────────────────
MOCK_MODE = True
MOCK_RATE_HZ = 5
BUFFER_SIZE = 600  # rolling window (~2 min at 5 Hz)

# ── Madgwick ────────────────────────────────
MADGWICK_BETA = 0.1
DEG2RAD = 0.017453292519943295

# ── CSV logging ─────────────────────────────
LOG_DIR = "logs"
CSV_FIELDS = [
    "timestamp_ms",
    "pressure",
    "ntc_thermistor",
    "ntc_ms5611",
    "alt_absolute",
    "alt_relative",
    "latitude",
    "longitude",
    "gps_date",
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
    "qw",
    "qx",
    "qy",
    "qz",
    "accel_magnitude",
    "gyro_magnitude",
]

# ── Colors ───────────────────────────────────
COLOR_BG = "#0A0A0F"
COLOR_BG_PANEL = "#0F0F1A"
COLOR_BG_WIDGET = "#13131F"
COLOR_ACCENT = "#10B981"
COLOR_ACCENT_DIM = "#065F46"
COLOR_TEXT = "#E2E8F0"
COLOR_TEXT_DIM = "#64748B"
COLOR_GRID = "#1E2030"
COLOR_WARN = "#F59E0B"
COLOR_DANGER = "#EF4444"

COLOR_PLOT_AX = "#10B981"
COLOR_PLOT_AY = "#34D399"
COLOR_PLOT_AZ = "#6EE7B7"
COLOR_PLOT_GX = "#60A5FA"
COLOR_PLOT_GY = "#93C5FD"
COLOR_PLOT_GZ = "#BFDBFE"
COLOR_PLOT_ALT = "#10B981"
COLOR_PLOT_ALT_R = "#34D399"
COLOR_PLOT_TEMP1 = "#F59E0B"
COLOR_PLOT_TEMP2 = "#FCD34D"
COLOR_PLOT_PRESS = "#A78BFA"

FONT_MONO = "JetBrains Mono, Courier New, monospace"
FONT_UI = "Inter, SF Pro Display, Helvetica Neue, Arial"

QSS = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: {FONT_UI};
    font-size: 12px;
}}
QTabWidget::pane {{
    border: 1px solid {COLOR_BG_WIDGET};
    background: {COLOR_BG_PANEL};
}}
QTabBar::tab {{
    background: {COLOR_BG};
    color: {COLOR_TEXT_DIM};
    padding: 6px 18px;
    border: none;
    font-size: 11px;
    letter-spacing: 1px;
}}
QTabBar::tab:selected {{
    color: {COLOR_ACCENT};
    border-bottom: 2px solid {COLOR_ACCENT};
    background: {COLOR_BG_PANEL};
}}
QTabBar::tab:hover {{ color: {COLOR_TEXT}; }}
QPushButton {{
    background-color: {COLOR_BG_WIDGET};
    color: {COLOR_TEXT_DIM};
    border: 1px solid #1E2030;
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 11px;
    letter-spacing: 1px;
}}
QPushButton:hover {{ border-color: {COLOR_ACCENT}; color: {COLOR_TEXT}; }}
QPushButton#btn_log_start {{
    background-color: {COLOR_ACCENT_DIM};
    color: {COLOR_ACCENT};
    border: 1px solid {COLOR_ACCENT};
}}
QPushButton#btn_log_start:hover {{ background-color: {COLOR_ACCENT}; color: #000; }}
QPushButton#btn_log_stop {{
    background-color: #3B0D0D;
    color: {COLOR_DANGER};
    border: 1px solid {COLOR_DANGER};
}}
QScrollBar:vertical {{ background: {COLOR_BG}; width: 6px; }}
QScrollBar::handle:vertical {{ background: {COLOR_BG_WIDGET}; border-radius: 3px; }}
QLabel#section_header {{
    color: {COLOR_TEXT_DIM};
    font-size: 10px;
    letter-spacing: 2px;
}}
QFrame#divider {{ background-color: {COLOR_GRID}; }}
"""
