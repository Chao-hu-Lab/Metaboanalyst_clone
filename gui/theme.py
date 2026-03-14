"""
Application theme styling for a flat, minimalist UI.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette


_LIGHT = {
    "bg": "#F3F6FB",
    "surface": "#FFFFFF",
    "surface_alt": "#ECF1F8",
    "border": "#D7DFEA",
    "text": "#1E293B",
    "muted": "#475569",
    "accent": "#2F80ED",
    "accent_hover": "#1F6FD8",
    "accent_pressed": "#165CB8",
    "selection": "#DDEBFF",
}

_DARK = {
    "bg": "#1E2633",
    "surface": "#273244",
    "surface_alt": "#324058",
    "border": "#42526E",
    "text": "#E8EEF8",
    "muted": "#C0CCDD",
    "accent": "#5CA2FF",
    "accent_hover": "#7AB4FF",
    "accent_pressed": "#438CE8",
    "selection": "#2E4F7A",
}


def _resolve_scheme(app, theme: str) -> str:
    pref = (theme or "auto").lower()
    if pref == "colorblind":
        return "light"
    if pref in {"light", "dark"}:
        return pref
    window = app.palette().color(QPalette.ColorRole.Window)
    return "dark" if window.lightness() < 128 else "light"


def _build_stylesheet(c: dict[str, str], font_size: int = 11) -> str:
    return f"""
* {{
    font-family: "Segoe UI", "Noto Sans TC", "Microsoft JhengHei";
    font-size: {font_size}pt;
    color: {c["text"]};
}}
QMainWindow, QDialog {{
    background-color: {c["bg"]};
}}
QWidget {{
    background-color: {c["bg"]};
}}
QToolTip {{
    background-color: {c["surface"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    padding: 6px;
}}
QMenuBar {{
    background-color: {c["surface"]};
    border-bottom: 1px solid {c["border"]};
}}
QMenuBar::item {{
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background-color: {c["surface_alt"]};
}}
QMenu {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {c["selection"]};
}}
QStatusBar {{
    background-color: {c["surface"]};
    border-top: 1px solid {c["border"]};
}}
QDockWidget {{
    border: 1px solid {c["border"]};
}}
QDockWidget::title {{
    background-color: {c["surface"]};
    border-bottom: 1px solid {c["border"]};
    text-align: left;
    padding: 8px 10px;
    font-weight: 600;
}}
QLabel {{
    background-color: transparent;
}}
QGroupBox {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 12px 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {c["text"]};
    font-weight: 700;
}}
QPushButton {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background-color: {c["surface_alt"]};
    border-color: {c["accent"]};
    color: {c["accent"]};
}}
QPushButton:pressed {{
    background-color: {c["selection"]};
}}
QPushButton:default {{
    background-color: {c["accent"]};
    border-color: {c["accent"]};
    color: #FFFFFF;
}}
QPushButton:default:hover {{
    background-color: {c["accent_hover"]};
    border-color: {c["accent_hover"]};
    color: #FFFFFF;
}}
QPushButton:disabled {{
    color: {c["muted"]};
    border-color: {c["border"]};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QTableView, QTableWidget {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    selection-background-color: {c["selection"]};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {c["accent"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QTabWidget::pane {{
    border: 1px solid {c["border"]};
    background: {c["surface"]};
    border-radius: 8px;
}}
QTabBar::tab {{
    background: {c["surface_alt"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    margin: 2px;
    min-width: 140px;
}}
QTabBar::tab:selected {{
    background: {c["accent"]};
    color: #FFFFFF;
    border-color: {c["accent"]};
    font-weight: 600;
}}
QTabBar::tab:!selected:hover {{
    background: {c["selection"]};
}}
QListWidget#nav_list {{
    background-color: {c["surface"]};
    border: none;
    border-right: 1px solid {c["border"]};
    outline: none;
}}
QListWidget#nav_list::item {{
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 4px;
}}
QListWidget#nav_list::item:selected {{
    background-color: {c["accent"]};
    color: #FFFFFF;
    font-weight: 600;
}}
QListWidget#nav_list::item:hover:!selected {{
    background-color: {c["selection"]};
}}
QListWidget#nav_list::item:disabled {{
    color: {c["muted"]};
}}
QHeaderView::section {{
    background-color: {c["surface_alt"]};
    border: 0;
    border-bottom: 1px solid {c["border"]};
    border-right: 1px solid {c["border"]};
    padding: 6px 8px;
    font-weight: 600;
}}
QTableView {{
    gridline-color: {c["border"]};
    alternate-background-color: {c["surface_alt"]};
}}
QProgressBar {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {c["accent"]};
    border-radius: 5px;
}}
QScrollBar:vertical {{
    background: {c["surface"]};
    width: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background: {c["border"]};
    border-radius: 6px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c["accent"]};
}}
QScrollBar:horizontal {{
    background: {c["surface"]};
    height: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {c["border"]};
    border-radius: 6px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c["accent"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}
QSplitter::handle {{
    background-color: {c["border"]};
}}
"""


def _apply_palette(app, c: dict[str, str]):
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(c["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(c["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c["surface_alt"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(c["surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(c["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(c["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


def _apply_matplotlib(c: dict[str, str]):
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    plt.rcParams["figure.facecolor"] = c["surface"]
    plt.rcParams["axes.facecolor"] = c["surface"]
    plt.rcParams["axes.edgecolor"] = c["border"]
    plt.rcParams["axes.labelcolor"] = c["text"]
    plt.rcParams["text.color"] = c["text"]
    plt.rcParams["xtick.color"] = c["text"]
    plt.rcParams["ytick.color"] = c["text"]
    plt.rcParams["grid.color"] = c["border"]
    plt.rcParams["savefig.facecolor"] = c["surface"]
    plt.rcParams["savefig.edgecolor"] = c["surface"]


def apply_flat_theme(app, theme: str = "auto", font_size: int = 11) -> str:
    """
    Apply the project flat minimalist theme.

    Returns the resolved scheme: "light" or "dark".
    """
    scheme = _resolve_scheme(app, theme)
    colors = _DARK if scheme == "dark" else _LIGHT
    _apply_palette(app, colors)
    app.setStyleSheet(_build_stylesheet(colors, font_size))
    _apply_matplotlib(colors)
    return scheme

