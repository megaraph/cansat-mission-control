# ─────────────────────────────────────────────
#  CanSat Ground Station  |  dashboard_window.py
#  Main application window.
# ─────────────────────────────────────────────

import queue
import time

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import config
from data_processor import DataProcessor
from mock_generator import MockDataGenerator
from serial_reader import SerialReader
from widgets.metric_panel import MetricPanel
from widgets.plot_panel import PlotPanel
from widgets.orientation_view import OrientationView
from widgets.status_panel import StatusPanel


def _vline():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet(f"background-color: {config.COLOR_GRID};")
    line.setFixedWidth(1)
    return line


class HeaderBar(QWidget):
    """Top bar: mission name, elapsed time, mode badge, status dot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            f"""
            HeaderBar {{
                background-color: {config.COLOR_BG_PANEL};
                border-bottom: 1px solid {config.COLOR_GRID};
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(20)

        # Mission title
        title = QLabel("CANSAT  ·  GROUND STATION")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Bold)
        title.setFont(font)
        title.setStyleSheet(f"color: {config.COLOR_ACCENT}; letter-spacing: 3px;")

        # Elapsed time
        self._elapsed_label = QLabel("T+  00:00:00")
        self._elapsed_label.setFont(font)
        self._elapsed_label.setStyleSheet(
            f"color: {config.COLOR_TEXT}; letter-spacing: 2px;"
        )

        # Mode badge
        mode_text = "SIMULATION" if config.MOCK_MODE else "LIVE"
        mode_color = config.COLOR_WARN if config.MOCK_MODE else config.COLOR_ACCENT
        self._mode_badge = QLabel(mode_text)
        self._mode_badge.setStyleSheet(
            f"""
            color: {mode_color};
            background-color: transparent;
            border: 1px solid {mode_color};
            border-radius: 3px;
            padding: 2px 8px;
            font-size: 10px;
            letter-spacing: 2px;
        """
        )

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self._elapsed_label)
        layout.addWidget(self._mode_badge)

        self._t0 = time.time()

    def tick(self):
        elapsed = int(time.time() - self._t0)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._elapsed_label.setText(f"T+  {h:02d}:{m:02d}:{s:02d}")


class DashboardWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CanSat Ground Station")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)
        self.setStyleSheet(config.QSS)

        # ── Data pipeline ─────────────────────────────────────────────────────
        self._data_queue = queue.Queue(maxsize=500)

        if config.MOCK_MODE:
            self._generator = MockDataGenerator(self._data_queue)
        else:
            self._generator = SerialReader(self._data_queue)

        self._processor = DataProcessor(self._data_queue)
        self._processor.processed_data.connect(self._on_data)

        # ── Build UI ──────────────────────────────────────────────────────────
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._header = HeaderBar()
        root_layout.addWidget(self._header)

        # Main content area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        # Left: metrics
        self._metric_panel = MetricPanel()
        content_layout.addWidget(self._metric_panel)
        content_layout.addWidget(_vline())

        # Center: plots
        self._plot_panel = PlotPanel()
        self._plot_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout.addWidget(self._plot_panel)
        content_layout.addWidget(_vline())

        # Right: orientation + status
        right = QWidget()
        right.setFixedWidth(230)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self._orientation = OrientationView()
        self._orientation.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        right_layout.addWidget(self._orientation)

        self._status_panel = StatusPanel()
        self._status_panel.log_start_requested.connect(self._on_log_start)
        self._status_panel.log_stop_requested.connect(self._on_log_stop)
        right_layout.addWidget(self._status_panel)

        content_layout.addWidget(right)
        root_layout.addWidget(content)

        # ── Timers ────────────────────────────────────────────────────────────
        self._header_timer = QTimer(self)
        self._header_timer.timeout.connect(self._header.tick)
        self._header_timer.start(1000)

        # ── Start pipeline ────────────────────────────────────────────────────
        self._generator.start()
        self._processor.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_data(self, data: dict):
        self._metric_panel.update(data)
        self._plot_panel.update(data)
        self._orientation.update_orientation(
            data.get("qw", 1.0),
            data.get("qx", 0.0),
            data.get("qy", 0.0),
            data.get("qz", 0.0),
        )
        self._status_panel.update_status(data)

    def _on_log_start(self):
        path = self._processor.start_logging()
        self._status_panel.set_log_path(path)

    def _on_log_stop(self):
        self._processor.stop_logging()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._generator.stop()
        self._processor.stop()
        super().closeEvent(event)
