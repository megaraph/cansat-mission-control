# ─────────────────────────────────────────────
#  CanSat Ground Station  |  widgets/serial_monitor.py
#  Live serial monitor for debugging.
#  Shows raw incoming lines, validation result,
#  and parsed field count.
# ─────────────────────────────────────────────

from collections import deque
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCursor
import config


class SerialMonitor(QWidget):
    """
    Drop-in debug panel. Wire it up by calling:
        monitor.append_raw(raw_line, valid=True/False)
    from SerialReader on every line received.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Header row ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()

        title = QLabel("SERIAL MONITOR")
        title.setObjectName("section_header")

        self._count_ok = QLabel("OK: 0")
        self._count_ok.setStyleSheet(f"color: {config.COLOR_ACCENT}; font-size: 10px;")
        self._count_bad = QLabel("SKIP: 0")
        self._count_bad.setStyleSheet(f"color: {config.COLOR_DANGER}; font-size: 10px;")

        self._chk_autoscroll = QCheckBox("Autoscroll")
        self._chk_autoscroll.setChecked(True)
        self._chk_autoscroll.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;"
        )

        self._chk_skip_only = QCheckBox("Show skipped only")
        self._chk_skip_only.setChecked(False)
        self._chk_skip_only.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;"
        )

        btn_clear = QPushButton("CLR")
        btn_clear.setFixedWidth(36)
        btn_clear.clicked.connect(self._clear)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self._count_ok)
        header_row.addWidget(self._count_bad)
        header_row.addWidget(self._chk_skip_only)
        header_row.addWidget(self._chk_autoscroll)
        header_row.addWidget(btn_clear)
        layout.addLayout(header_row)

        # ── Text area ─────────────────────────────────────────────────────────
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(11)
        self._text.setFont(font)
        self._text.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: #07070F;
                color: {config.COLOR_TEXT};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
                padding: 4px;
            }}
        """
        )
        layout.addWidget(self._text)

        # ── Field inspector (shows last valid packet fields) ──────────────────
        self._inspector = QLabel("Awaiting first valid packet…")
        self._inspector.setWordWrap(True)
        self._inspector.setStyleSheet(
            f"""
            color: {config.COLOR_TEXT_DIM};
            font-size: 10px;
            background-color: {config.COLOR_BG_WIDGET};
            border: 1px solid {config.COLOR_GRID};
            border-radius: 4px;
            padding: 6px;
        """
        )
        self._inspector.setFont(font)
        layout.addWidget(self._inspector)

        # Internal counters
        self._ok_count = 0
        self._bad_count = 0
        self._max_lines = 200  # cap to avoid memory growth

    # ── Public API ────────────────────────────────────────────────────────────

    @pyqtSlot(str, bool, list)
    def append_raw(self, line: str, valid: bool, fields: list):
        """
        Call this from the UI thread (via signal) whenever a line is received.
        line   — raw decoded string
        valid  — whether it passed _is_valid_line()
        fields — line.split() result
        """
        if valid:
            self._ok_count += 1
            self._count_ok.setText(f"OK: {self._ok_count}")
        else:
            self._bad_count += 1
            self._count_bad.setText(f"SKIP: {self._bad_count}")

        # Filter if "show skipped only" is checked
        if self._chk_skip_only.isChecked() and valid:
            return

        # Trim old lines
        doc = self._text.document()
        if doc.blockCount() > self._max_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                doc.blockCount() - self._max_lines,
            )
            cursor.removeSelectedText()

        # Color-coded prefix
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if valid:
            prefix_color = config.COLOR_ACCENT
            prefix = "✓ "
        else:
            prefix_color = config.COLOR_DANGER
            prefix = "✗ "

        # Write prefix in color
        fmt = cursor.charFormat()
        fmt.setForeground(QColor(prefix_color))
        cursor.setCharFormat(fmt)
        cursor.insertText(prefix)

        # Write line in normal color
        fmt.setForeground(QColor(config.COLOR_TEXT if valid else config.COLOR_TEXT_DIM))
        cursor.setCharFormat(fmt)

        # Show field count alongside the raw line
        field_info = f"[{len(fields)} fields]  " if not valid else ""
        cursor.insertText(f"{field_info}{line}\n")

        if self._chk_autoscroll.isChecked():
            self._text.setTextCursor(cursor)
            self._text.ensureCursorVisible()

        # Update field inspector on valid packets
        if valid and len(fields) == 15:
            labels = [
                "pressure",
                "ntc_therm",
                "ntc_ms5611",
                "alt_abs",
                "alt_rel",
                "lat",
                "lon",
                "date",
                "ax",
                "ay",
                "az",
                "gx",
                "gy",
                "gz",
                "time_ms",
            ]
            lines = []
            for i, (lbl, val) in enumerate(zip(labels, fields)):
                lines.append(f"{lbl:>12} = {val}")
            self._inspector.setText("\n".join(lines))

    def _clear(self):
        self._text.clear()
        self._ok_count = 0
        self._bad_count = 0
        self._count_ok.setText("OK: 0")
        self._count_bad.setText("SKIP: 0")
        self._inspector.setText("Awaiting first valid packet…")
