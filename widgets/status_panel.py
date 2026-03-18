# ─────────────────────────────────────────────
#  CanSat Ground Station  |  widgets/status_panel.py
#  System status indicators + CSV logging control
# ─────────────────────────────────────────────

import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import config


def _divider():
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


class _StatusRow(QWidget):
    """Single row: dot indicator + label + value."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(14)
        self._dot.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;")

        lbl = QLabel(label.upper())
        lbl.setObjectName("section_header")
        lbl.setFixedWidth(100)

        self._val = QLabel("---")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(11)
        self._val.setFont(font)
        self._val.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self._dot)
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(self._val)

    def set(self, value: str, dot_color: str = config.COLOR_TEXT_DIM):
        self._val.setText(value)
        self._val.setStyleSheet(f"color: {dot_color};")
        self._dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")


class StatusPanel(QWidget):
    """
    Right-column bottom section.
    Emits log_start_requested / log_stop_requested signals.
    """

    log_start_requested = pyqtSignal()
    log_stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── System status ─────────────────────────────────────────────────────
        hdr = QLabel("SYSTEM STATUS")
        hdr.setObjectName("section_header")
        layout.addWidget(hdr)

        self._row_link = _StatusRow("Link")
        self._row_rate = _StatusRow("Pkt rate")
        self._row_packets = _StatusRow("Packets")
        self._row_mode = _StatusRow("Mode")

        for row in [self._row_link, self._row_rate, self._row_packets, self._row_mode]:
            layout.addWidget(row)

        layout.addWidget(_divider())

        # ── CSV Logging ───────────────────────────────────────────────────────
        hdr2 = QLabel("DATA LOGGING")
        hdr2.setObjectName("section_header")
        layout.addWidget(hdr2)

        self._log_status = QLabel("STOPPED")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(11)
        self._log_status.setFont(font)
        self._log_status.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        layout.addWidget(self._log_status)

        self._log_file_label = QLabel("")
        self._log_file_label.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 9px;"
        )
        self._log_file_label.setWordWrap(True)
        layout.addWidget(self._log_file_label)

        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("● REC")
        self._btn_start.setObjectName("btn_log_start")
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QPushButton("■ STOP")
        self._btn_stop.setObjectName("btn_log_stop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        layout.addLayout(btn_row)

        layout.addStretch()

        self.setStyleSheet(
            f"""
            StatusPanel {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
            }}
        """
        )

        self._logging = False

    def _on_start(self):
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._logging = True
        self._log_status.setText("● RECORDING")
        self._log_status.setStyleSheet(f"color: {config.COLOR_DANGER};")
        self.log_start_requested.emit()

    def _on_stop(self):
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._logging = False
        self._log_status.setText("STOPPED")
        self._log_status.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        self._log_file_label.setText("")
        self.log_stop_requested.emit()

    def set_log_path(self, path: str):
        self._log_file_label.setText(os.path.basename(path))

    def update_status(self, data: dict):
        phase = data.get("phase", "---")
        rate = data.get("packet_rate", 0.0)
        total = data.get("total_packets", 0)

        # Link health
        if rate >= config.MOCK_RATE_HZ * 0.8:
            self._row_link.set("NOMINAL", config.COLOR_ACCENT)
        elif rate > 0:
            self._row_link.set("DEGRADED", config.COLOR_WARN)
        else:
            self._row_link.set("LOST", config.COLOR_DANGER)

        self._row_rate.set(
            f"{rate:.1f} Hz",
            config.COLOR_ACCENT if rate > 0 else config.COLOR_DANGER,
        )
        self._row_packets.set(str(total), config.COLOR_TEXT_DIM)
        self._row_mode.set(
            "MOCK" if config.MOCK_MODE else "LIVE",
            config.COLOR_WARN if config.MOCK_MODE else config.COLOR_ACCENT,
        )
