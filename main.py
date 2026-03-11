"""
Entry point for Politeness Auto Refiner.

Usage:
    python main.py
"""
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from app.ai_client import AIClient
from app.floating_window import FloatingWindow
from app.main_window import MainWindow
from app.settings_manager import SettingsManager
from app.text_handler import TextHandler


def main() -> int:
    # High-DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("PolitenessAutoRefiner")
    app.setOrganizationName("PolitenessRefiner")
    # Keep the app running even when all windows are hidden (lives in tray)
    app.setQuitOnLastWindowClosed(False)

    settings = SettingsManager()
    ai_client = AIClient(settings)
    text_handler = TextHandler()

    floating = FloatingWindow(ai_client, text_handler, settings)
    main_win = MainWindow(settings, floating_window=floating)

    # Wire the floating window's settings button back to the main window
    floating.open_settings_requested.connect(main_win._show_main)

    main_win.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
