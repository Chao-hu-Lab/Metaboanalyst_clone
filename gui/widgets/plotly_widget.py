"""
Plotly 嵌入 PySide6 的 Widget — 用於互動式 3D PCA

使用 QWebEngineView 或 fallback 到檔案瀏覽
"""

import tempfile
import os
from pathlib import Path

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class PlotlyWidget(QWidget):
    """
    Plotly 互動圖表 Widget

    優先使用 QWebEngineView，若不可用則提供匯出 HTML 按鈕
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._html_path = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEBENGINE:
            self._web = QWebEngineView()
            layout.addWidget(self._web)
        else:
            self._web = None
            self._label = QLabel(self.tr("3D 互動圖表需要 PySide6-WebEngine\npip install PySide6-WebEngine"))
            self._label.setStyleSheet("padding: 20px; color: #888;")
            layout.addWidget(self._label)

            self._btn = QPushButton(self.tr("以瀏覽器開啟 3D 圖表"))
            self._btn.clicked.connect(self._open_in_browser)
            self._btn.setEnabled(False)
            layout.addWidget(self._btn)

    def show_figure(self, plotly_fig):
        """顯示 Plotly figure"""
        if plotly_fig is None:
            return

        import plotly.io as pio
        html = pio.to_html(plotly_fig, include_plotlyjs="cdn", full_html=True)

        # 存到暫存檔
        fd, path = tempfile.mkstemp(suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        self._html_path = path

        if self._web is not None:
            self._web.setHtml(html)
        else:
            self._btn.setEnabled(True)
            self._label.setText(self.tr("3D 圖表已生成 — 請點擊按鈕在瀏覽器中開啟"))

    def show_html(self, html: str):
        """直接顯示 HTML 字串"""
        if self._web is not None:
            self._web.setHtml(html)

    def _open_in_browser(self):
        """在系統預設瀏覽器開啟"""
        if self._html_path and os.path.exists(self._html_path):
            import webbrowser
            webbrowser.open(Path(self._html_path).as_uri())

    def save_html(self, path: str):
        """儲存 HTML 到指定路徑"""
        if self._html_path and os.path.exists(self._html_path):
            import shutil
            shutil.copy2(self._html_path, path)
