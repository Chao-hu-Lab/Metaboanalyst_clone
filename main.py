"""
PyMetaboAnalyst entry point.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme import apply_flat_theme


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    settings = QSettings("PyMetaboAnalyst", "PyMetaboAnalyst")
    theme = settings.value("theme", "auto", type=str)
    apply_flat_theme(app, theme)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
