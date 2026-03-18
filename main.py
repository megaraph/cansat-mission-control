#!/usr/bin/env python3
# ─────────────────────────────────────────────
#  CanSat Ground Station  |  main.py
#  Entry point. Run with:  python main.py
# ─────────────────────────────────────────────

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from dashboard_window import DashboardWindow
import config


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("CanSat Ground Station")
    app.setOrganizationName("CanSat Team")
    app.setStyleSheet(config.QSS)

    window = DashboardWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
