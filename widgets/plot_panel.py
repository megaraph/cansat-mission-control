# ─────────────────────────────────────────────
#  CanSat Ground Station  |  widgets/plot_panel.py
#  Tabbed live PyQtGraph plots
# ─────────────────────────────────────────────

import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QHBoxLayout,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import config

# ── Global PyQtGraph config ───────────────────────────────────────────────────
pg.setConfigOptions(antialias=True, foreground=config.COLOR_TEXT_DIM)


def _make_plot(title: str, y_label: str, x_label: str = "Time (s)") -> pg.PlotWidget:
    pw = pg.PlotWidget()
    pw.setBackground(config.COLOR_BG_PANEL)
    pw.showGrid(x=True, y=True, alpha=0.15)
    pw.setLabel("left", y_label, color=config.COLOR_TEXT_DIM, size="10pt")
    pw.setLabel("bottom", x_label, color=config.COLOR_TEXT_DIM, size="10pt")
    pw.getAxis("left").setTextPen(config.COLOR_TEXT_DIM)
    pw.getAxis("bottom").setTextPen(config.COLOR_TEXT_DIM)
    pw.getAxis("left").setPen(pg.mkPen(config.COLOR_GRID, width=0.5))
    pw.getAxis("bottom").setPen(pg.mkPen(config.COLOR_GRID, width=0.5))
    pw.setTitle(title, color=config.COLOR_TEXT_DIM, size="10pt")
    pw.getPlotItem().titleLabel.item.setFont(QFont("Inter, Arial", 9))
    pw.setMouseEnabled(x=False, y=True)
    pw.enableAutoRange(axis="y", enable=True)
    return pw


def _curve(plot: pg.PlotWidget, color: str, width: float = 1.5) -> pg.PlotDataItem:
    return plot.plot(pen=pg.mkPen(color=color, width=width), antialias=True)


def _legend_label(color: str, text: str) -> QLabel:
    lbl = QLabel(f"● {text}")
    lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
    return lbl


def _legend_row(*items) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(4, 0, 4, 4)
    h.setSpacing(14)
    for item in items:
        h.addWidget(item)
    h.addStretch()
    return w


# ── IMU Tab ───────────────────────────────────────────────────────────────────
class IMUTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Accelerometer
        self._plt_accel = _make_plot("ACCELEROMETER", "Acceleration (g)")
        self._c_ax = _curve(self._plt_accel, config.COLOR_PLOT_AX)
        self._c_ay = _curve(self._plt_accel, config.COLOR_PLOT_AY)
        self._c_az = _curve(self._plt_accel, config.COLOR_PLOT_AZ)

        layout.addWidget(self._plt_accel)
        layout.addWidget(
            _legend_row(
                _legend_label(config.COLOR_PLOT_AX, "ax"),
                _legend_label(config.COLOR_PLOT_AY, "ay"),
                _legend_label(config.COLOR_PLOT_AZ, "az"),
            )
        )

        # Gyroscope
        self._plt_gyro = _make_plot("GYROSCOPE", "Angular rate (°/s)")
        self._c_gx = _curve(self._plt_gyro, config.COLOR_PLOT_GX)
        self._c_gy = _curve(self._plt_gyro, config.COLOR_PLOT_GY)
        self._c_gz = _curve(self._plt_gyro, config.COLOR_PLOT_GZ)

        layout.addWidget(self._plt_gyro)
        layout.addWidget(
            _legend_row(
                _legend_label(config.COLOR_PLOT_GX, "gx"),
                _legend_label(config.COLOR_PLOT_GY, "gy"),
                _legend_label(config.COLOR_PLOT_GZ, "gz"),
            )
        )

    def update(self, data: dict):
        t = data["plot_time"]
        self._c_ax.setData(t, data["plot_ax"])
        self._c_ay.setData(t, data["plot_ay"])
        self._c_az.setData(t, data["plot_az"])
        self._c_gx.setData(t, data["plot_gx"])
        self._c_gy.setData(t, data["plot_gy"])
        self._c_gz.setData(t, data["plot_gz"])


# ── Environment Tab ───────────────────────────────────────────────────────────
class EnvironmentTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Altitude
        self._plt_alt = _make_plot("ALTITUDE", "Altitude (m)")
        self._c_alt_a = _curve(self._plt_alt, config.COLOR_PLOT_ALT, width=2.0)
        self._c_alt_r = _curve(self._plt_alt, config.COLOR_PLOT_ALT_R, width=1.5)

        layout.addWidget(self._plt_alt)
        layout.addWidget(
            _legend_row(
                _legend_label(config.COLOR_PLOT_ALT, "Absolute"),
                _legend_label(config.COLOR_PLOT_ALT_R, "Relative"),
            )
        )

        # Temperature
        self._plt_temp = _make_plot("TEMPERATURE", "Temperature (°C)")
        self._c_temp1 = _curve(self._plt_temp, config.COLOR_PLOT_TEMP1)
        self._c_temp2 = _curve(self._plt_temp, config.COLOR_PLOT_TEMP2)

        layout.addWidget(self._plt_temp)
        layout.addWidget(
            _legend_row(
                _legend_label(config.COLOR_PLOT_TEMP1, "NTC Thermistor"),
                _legend_label(config.COLOR_PLOT_TEMP2, "MS5611"),
            )
        )

        # Pressure
        self._plt_press = _make_plot("PRESSURE", "Pressure (Pa)")
        self._c_press = _curve(self._plt_press, config.COLOR_PLOT_PRESS, width=1.5)

        layout.addWidget(self._plt_press)

    def update(self, data: dict):
        t = data["plot_time"]
        self._c_alt_a.setData(t, data["plot_alt_a"])
        self._c_alt_r.setData(t, data["plot_alt_r"])
        self._c_temp1.setData(t, data["plot_temp1"])
        self._c_temp2.setData(t, data["plot_temp2"])
        self._c_press.setData(t, data["plot_press"])


# ── GPS Tab ───────────────────────────────────────────────────────────────────
class GPSTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(16)

        def _header(text):
            lbl = QLabel(text)
            lbl.setObjectName("section_header")
            return lbl

        def _value_label():
            lbl = QLabel("---")
            font = QFont("JetBrains Mono, Courier New, monospace")
            font.setPixelSize(26)
            font.setWeight(QFont.Weight.Bold)
            lbl.setFont(font)
            lbl.setStyleSheet(f"color: {config.COLOR_ACCENT};")
            return lbl

        def _unit(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 11px;")
            return lbl

        def _card(label, unit):
            card = QFrame()
            card.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {config.COLOR_BG_WIDGET};
                    border: 1px solid {config.COLOR_GRID};
                    border-radius: 4px;
                }}
            """
            )
            v = QVBoxLayout(card)
            v.setContentsMargins(16, 12, 16, 12)
            v.setSpacing(3)
            h = _header(label)
            val = _value_label()
            u = _unit(unit)
            v.addWidget(h)
            v.addWidget(val)
            v.addWidget(u)
            return card, val

        # GPS Fix status
        self._fix_card = QFrame()
        self._fix_card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
            }}
        """
        )
        fix_layout = QHBoxLayout(self._fix_card)
        fix_layout.setContentsMargins(16, 12, 16, 12)
        fix_h = _header("GPS STATUS")
        self._fix_label = QLabel("NO FIX")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(16)
        font.setWeight(QFont.Weight.Bold)
        self._fix_label.setFont(font)
        self._fix_label.setStyleSheet(f"color: {config.COLOR_DANGER};")
        fix_layout.addWidget(fix_h)
        fix_layout.addStretch()
        fix_layout.addWidget(self._fix_label)

        layout.addWidget(self._fix_card)

        # Lat / Lon cards
        row = QHBoxLayout()
        self._lat_card, self._lat_val = _card("LATITUDE", "degrees N/S")
        self._lon_card, self._lon_val = _card("LONGITUDE", "degrees E/W")
        row.addWidget(self._lat_card)
        row.addWidget(self._lon_card)
        layout.addLayout(row)

        # Date card
        self._date_card, self._date_val = _card("GPS DATE", "DD/MM/YYYY")
        self._date_val.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        layout.addWidget(self._date_card)

        # Packet count
        self._pkt_card = QFrame()
        self._pkt_card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
            }}
        """
        )
        pkt_layout = QHBoxLayout(self._pkt_card)
        pkt_layout.setContentsMargins(16, 12, 16, 12)
        pkt_h = _header("TOTAL PACKETS RECEIVED")
        self._pkt_val = QLabel("0")
        self._pkt_val.setFont(font)
        self._pkt_val.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        pkt_layout.addWidget(pkt_h)
        pkt_layout.addStretch()
        pkt_layout.addWidget(self._pkt_val)
        layout.addWidget(self._pkt_card)

        layout.addStretch()

    def update(self, data: dict):
        lat = data.get("latitude", 0.0)
        lon = data.get("longitude", 0.0)
        has_fix = lat != 0.0 or lon != 0.0

        if has_fix:
            self._fix_label.setText("FIX ACQUIRED")
            self._fix_label.setStyleSheet(f"color: {config.COLOR_ACCENT};")
            self._lat_val.setText(f"{lat:+.6f}")
            self._lon_val.setText(f"{lon:+.6f}")
            self._lat_val.setStyleSheet(f"color: {config.COLOR_ACCENT};")
            self._lon_val.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        else:
            self._fix_label.setText("NO FIX")
            self._fix_label.setStyleSheet(f"color: {config.COLOR_DANGER};")
            self._lat_val.setText("---")
            self._lon_val.setText("---")
            self._lat_val.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
            self._lon_val.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")

        self._date_val.setText(data.get("gps_date", "---"))
        self._pkt_val.setText(str(data.get("total_packets", 0)))


# ── Tabbed container ──────────────────────────────────────────────────────────
class PlotPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._imu_tab = IMUTab()
        self._env_tab = EnvironmentTab()
        self._gps_tab = GPSTab()

        self._tabs.addTab(self._imu_tab, "IMU")
        self._tabs.addTab(self._env_tab, "ENVIRONMENT")
        self._tabs.addTab(self._gps_tab, "GPS")

        layout.addWidget(self._tabs)

    def update(self, data: dict):
        idx = self._tabs.currentIndex()
        if idx == 0:
            self._imu_tab.update(data)
        elif idx == 1:
            self._env_tab.update(data)
        elif idx == 2:
            self._gps_tab.update(data)
