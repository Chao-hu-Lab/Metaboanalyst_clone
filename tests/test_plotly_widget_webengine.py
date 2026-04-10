"""Targeted smoke tests for the embedded Plotly WebEngine path."""

from __future__ import annotations

import pytest

from tests.gui_layout_support import close_window

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.webengine]


def test_plotly_widget_embeds_webengine_when_explicitly_enabled(monkeypatch, qapp) -> None:
    from gui.widgets.plotly_widget import HAS_WEBENGINE, PlotlyWidget

    if not HAS_WEBENGINE:
        pytest.skip("PySide6-WebEngine not installed")

    monkeypatch.setenv("METABO_DISABLE_WEBENGINE", "0")
    widget = PlotlyWidget()
    try:
        assert widget._web is not None
        assert widget._page is not None
    finally:
        close_window(widget, qapp)


def test_plotly_widget_console_bridge_emits_python_event(monkeypatch, qapp) -> None:
    from gui.widgets.plotly_widget import HAS_WEBENGINE, PlotlyWidget

    if not HAS_WEBENGINE:
        pytest.skip("PySide6-WebEngine not installed")

    monkeypatch.setenv("METABO_DISABLE_WEBENGINE", "0")
    widget = PlotlyWidget()
    payloads: list[object] = []
    widget.plotly_event.connect(payloads.append)
    try:
        widget._handle_console_message(
            '__PLOTLY_EVENT__:{"type":"point_click","feature":"F1","pointNumber":0}'
        )
        assert payloads == [{"type": "point_click", "feature": "F1", "pointNumber": 0}]
    finally:
        close_window(widget, qapp)
