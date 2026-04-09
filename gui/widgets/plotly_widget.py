"""PySide6 widget for displaying Plotly figures."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import Signal

try:
    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView

    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    QWebEnginePage = None

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


if HAS_WEBENGINE:
    class _PlotlyBridgePage(QWebEnginePage):
        """QWebEnginePage that forwards JavaScript console messages to Python."""

        console_message_emitted = Signal(str)

        def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # type: ignore[override]
            del level, line_number, source_id
            self.console_message_emitted.emit(message)


class PlotlyWidget(QWidget):
    """Display Plotly charts via ``QWebEngineView`` or a browser fallback."""

    plotly_event = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._html_path: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEBENGINE:
            self._web = QWebEngineView()
            self._page = _PlotlyBridgePage(self._web)
            self._page.console_message_emitted.connect(self._handle_console_message)
            self._web.setPage(self._page)
            layout.addWidget(self._web)
            self._label = None
            self._btn = None
        else:
            self._web = None
            self._page = None
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

    def show_figure(self, plotly_fig, *, enable_selection_bridge: bool = False) -> None:
        """Render a Plotly figure in the widget."""
        if plotly_fig is None:
            return

        import plotly.io as pio

        html = pio.to_html(plotly_fig, include_plotlyjs="cdn", full_html=True)
        if enable_selection_bridge:
            html = self._inject_selection_bridge(html)
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

    def highlight_feature(self, feature: str | None) -> None:
        """Highlight a specific Plotly point by its feature identifier."""
        if self._web is None:
            return

        feature_payload = json.dumps(feature)
        self._web.page().runJavaScript(
            f"""
            if (window.__codexPlotlySelect) {{
                window.__codexPlotlySelect({feature_payload});
            }}
            """
        )

    def _handle_console_message(self, message: str) -> None:
        prefix = "__PLOTLY_EVENT__:"
        if not message.startswith(prefix):
            return
        try:
            payload = json.loads(message[len(prefix):])
        except json.JSONDecodeError:
            return
        self.plotly_event.emit(payload)

    @staticmethod
    def _inject_selection_bridge(html: str) -> str:
        bridge_script = """
<script>
(function () {
  function normalizeKey(value) {
    if (Array.isArray(value)) {
      return value.length ? value[0] : null;
    }
    return value;
  }

  function bindBridge() {
    const gd = document.querySelector('.plotly-graph-div');
    if (!gd || gd.__codexBridgeBound || typeof Plotly === 'undefined') {
      return;
    }
    gd.__codexBridgeBound = true;

    window.__codexPlotlySelect = function (feature) {
      const target = feature == null ? null : String(feature);
      for (let traceIndex = 0; traceIndex < gd.data.length; traceIndex += 1) {
        const trace = gd.data[traceIndex];
        const custom = trace.customdata || [];
        const selected = [];
        for (let pointIndex = 0; pointIndex < custom.length; pointIndex += 1) {
          const candidate = normalizeKey(custom[pointIndex]);
          if (target !== null && String(candidate) === target) {
            selected.push(pointIndex);
          }
        }
        Plotly.restyle(gd, { selectedpoints: [selected] }, [traceIndex]);
      }
    };

    gd.on('plotly_click', function (eventData) {
      const point = eventData && eventData.points && eventData.points.length ? eventData.points[0] : null;
      if (!point) {
        return;
      }
      const feature = normalizeKey(point.customdata);
      if (feature == null) {
        return;
      }
      window.__codexPlotlySelect(feature);
      console.log('__PLOTLY_EVENT__:' + JSON.stringify({
        type: 'point_click',
        feature: String(feature),
        curveNumber: point.curveNumber,
        pointNumber: point.pointNumber
      }));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindBridge, { once: true });
  } else {
    bindBridge();
  }
  window.setTimeout(bindBridge, 250);
})();
</script>
"""
        return html.replace("</body>", f"{bridge_script}</body>")
