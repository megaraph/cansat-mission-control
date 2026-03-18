# ─────────────────────────────────────────────
#  CanSat Ground Station  |  widgets/metric_panel.py
#  Large engineering-style numeric readouts
# ─────────────────────────────────────────────

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import config


def _divider():
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


class MetricCard(QWidget):
    """Single large numeric readout with label and unit."""

    def __init__(
        self,
        label: str,
        unit: str,
        fmt: str = "{:.1f}",
        color: str = config.COLOR_ACCENT,
        parent=None,
    ):
        super().__init__(parent)
        self._fmt = fmt
        self._color = color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        # Section label
        self._lbl_label = QLabel(label.upper())
        self._lbl_label.setObjectName("section_header")
        self._lbl_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Big value
        self._lbl_value = QLabel("---")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(28)
        font.setWeight(QFont.Weight.Bold)
        self._lbl_value.setFont(font)
        self._lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._lbl_value.setStyleSheet(f"color: {color};")

        # Unit label
        self._lbl_unit = QLabel(unit)
        self._lbl_unit.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 11px;"
        )

        layout.addWidget(self._lbl_label)
        layout.addWidget(self._lbl_value)
        layout.addWidget(self._lbl_unit)

        self.setStyleSheet(
            f"""
            MetricCard {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
            }}
        """
        )

    def update_value(self, value):
        try:
            self._lbl_value.setText(self._fmt.format(value))
        except Exception:
            self._lbl_value.setText(str(value))

    def set_color(self, color: str):
        self._lbl_value.setStyleSheet(f"color: {color};")


class PhaseCard(QWidget):
    """Flight phase indicator."""

    PHASE_COLORS = {
        "IDLE": config.COLOR_TEXT_DIM,
        "LAUNCH": config.COLOR_WARN,
        "ASCENT": config.COLOR_ACCENT,
        "APOGEE": "#A78BFA",
        "DESCENT": "#60A5FA",
        "LANDED": config.COLOR_TEXT_DIM,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        lbl = QLabel("FLIGHT PHASE")
        lbl.setObjectName("section_header")

        self._phase = QLabel("IDLE")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(22)
        font.setWeight(QFont.Weight.Bold)
        self._phase.setFont(font)
        self._phase.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")

        layout.addWidget(lbl)
        layout.addWidget(self._phase)

        self.setStyleSheet(
            f"""
            PhaseCard {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
            }}
        """
        )

    def update_phase(self, phase: str):
        color = self.PHASE_COLORS.get(phase, config.COLOR_TEXT)
        self._phase.setText(phase)
        self._phase.setStyleSheet(f"color: {color}; letter-spacing: 2px;")


class MetricPanel(QWidget):
    """Left column: stacked metric cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Phase ─────────────────────────────────────────────────────────────
        self.phase_card = PhaseCard()
        layout.addWidget(self.phase_card)
        layout.addWidget(_divider())

        # ── Primary metrics ───────────────────────────────────────────────────
        self.card_alt_abs = MetricCard("Altitude (ABS)", "m", "{:.1f}")
        self.card_alt_rel = MetricCard(
            "Altitude (REL)", "m", "{:.1f}", color=config.COLOR_PLOT_ALT_R
        )
        self.card_velocity = MetricCard(
            "Velocity", "m/s", "{:+.2f}", color=config.COLOR_WARN
        )
        self.card_accel = MetricCard("Accel Mag", "g", "{:.3f}", color="#A78BFA")
        self.card_gyro = MetricCard(
            "Gyro Mag", "°/s", "{:.1f}", color=config.COLOR_PLOT_GX
        )
        self.card_temp1 = MetricCard(
            "Temp (NTC)", "°C", "{:.2f}", color=config.COLOR_PLOT_TEMP1
        )
        self.card_temp2 = MetricCard(
            "Temp (MS5611)", "°C", "{:.2f}", color=config.COLOR_PLOT_TEMP2
        )
        self.card_press = MetricCard(
            "Pressure", "Pa", "{:.0f}", color=config.COLOR_PLOT_PRESS
        )

        for card in [
            self.card_alt_abs,
            self.card_alt_rel,
            self.card_velocity,
            _divider(),
            self.card_accel,
            self.card_gyro,
            _divider(),
            self.card_temp1,
            self.card_temp2,
            self.card_press,
        ]:
            layout.addWidget(card)

        layout.addStretch()

    def update(self, data: dict):
        self.phase_card.update_phase(data.get("phase", "---"))
        self.card_alt_abs.update_value(data.get("alt_absolute", 0))
        self.card_alt_rel.update_value(data.get("alt_relative", 0))
        self.card_velocity.update_value(data.get("velocity", 0))

        # Color velocity by sign
        v = data.get("velocity", 0)
        if v > 0.5:
            self.card_velocity.set_color(config.COLOR_ACCENT)
        elif v < -0.5:
            self.card_velocity.set_color(config.COLOR_DANGER)
        else:
            self.card_velocity.set_color(config.COLOR_TEXT_DIM)

        self.card_accel.update_value(data.get("accel_magnitude", 0))
        self.card_gyro.update_value(data.get("gyro_magnitude", 0))
        self.card_temp1.update_value(data.get("ntc_thermistor", 0))
        self.card_temp2.update_value(data.get("ntc_ms5611", 0))
        self.card_press.update_value(data.get("pressure", 0))
