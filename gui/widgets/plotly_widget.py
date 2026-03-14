"""PySide6 widget for displaying Plotly figures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class PlotlyWidget(QWidget):
    """Display Plotly charts via ``QWebEngineView`` or a browser fallback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._html_path: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEBENGINE:
            self._web = QWebEngineView()
            layout.addWidget(self._web)
            self._label = None
            self._btn = None
        else:
            self._web = None
            self._label = QLabel(
                self.tr("Interactive charts require PySide6-WebEngine.\nInstall PySide6-WebEngine to embed them here.")
            )
            self._label.setStyleSheet("padding: 20px; color: #888;")
            layout.addWidget(self._label)

            self._btn = QPushButton(self.tr("Open Interactive Chart in Browser"))
            self._btn.clicked.connect(self._open_in_browser)
            self._btn.setEnabled(False)
            layout.addWidget(self._btn)

    def _cache_dir(self) -> Path:
        cache_dir = Path.cwd() / ".plotly_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def show_figure(self, plotly_fig) -> None:
        """Render a Plotly figure in the widget."""
        if plotly_fig is None:
            return

        import plotly.io as pio

        html = pio.to_html(plotly_fig, include_plotlyjs="cdn", full_html=True)
        fd, path = tempfile.mkstemp(suffix=".html", dir=self._cache_dir())
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(html)
        self._html_path = path

        if self._web is not None:
            self._web.setHtml(html)
        elif self._btn is not None and self._label is not None:
            self._btn.setEnabled(True)
            self._label.setText(self.tr("Interactive chart prepared. Use the button below to open it in your browser."))

    def show_html(self, html: str) -> None:
        """Render an already serialized HTML snippet."""
        if self._web is not None:
            self._web.setHtml(html)

    def _open_in_browser(self) -> None:
        """Open the cached interactive chart in the system browser."""
        if self._html_path and os.path.exists(self._html_path):
            import webbrowser

            webbrowser.open(Path(self._html_path).as_uri())

    def save_html(self, path: str) -> None:
        """Copy the cached HTML document to the requested location."""
        if self._html_path and os.path.exists(self._html_path):
            import shutil

            shutil.copy2(self._html_path, path)
