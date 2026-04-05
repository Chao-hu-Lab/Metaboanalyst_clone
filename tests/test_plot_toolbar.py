"""Functional tests for the custom plot toolbar."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QPushButton

from gui.widgets.mpl_canvas import MatplotlibCanvas
from gui.widgets.plot_toolbar import PlotToolbar
from visualization.theme_manager import ThemeManager

pytestmark = pytest.mark.gui


def _seed_plot(mpl_widget):
    axes = mpl_widget.figure.add_subplot(111)
    axes.plot([0, 1, 2], [1, 3, 2])


def test_plot_toolbar_initialization(qapp):
    mpl_canvas = MatplotlibCanvas()
    theme_manager = ThemeManager()
    toolbar = PlotToolbar(mpl_canvas, theme_manager)

    assert toolbar is not None
    assert toolbar.mpl_widget is mpl_canvas
    assert toolbar.theme_manager is theme_manager


def test_plot_toolbar_buttons_exist(qapp):
    mpl_canvas = MatplotlibCanvas()
    toolbar = PlotToolbar(mpl_canvas)

    buttons = toolbar.findChildren(QPushButton)
    button_texts = [btn.text() for btn in buttons]
    assert "PNG" in button_texts
    assert "SVG" in button_texts
    assert "PDF" in button_texts
    assert "Reset" in button_texts


def test_zoom_mode_toggle(qapp):
    mpl_canvas = MatplotlibCanvas()
    toolbar = PlotToolbar(mpl_canvas)

    assert not toolbar.zoom_mode_enabled
    toolbar.zoom_button.setChecked(True)
    assert toolbar.zoom_mode_enabled
    toolbar.zoom_button.setChecked(False)
    assert not toolbar.zoom_mode_enabled


def test_theme_indicator_updates(qapp):
    mpl_canvas = MatplotlibCanvas()
    theme_manager = ThemeManager("light")
    toolbar = PlotToolbar(mpl_canvas, theme_manager)

    assert toolbar.theme_value_label.text() == "Light"

    theme_manager.set_theme("dark")
    assert toolbar.theme_value_label.text() == "Dark"


def test_export_png_writes_file(qapp, monkeypatch):
    mpl_canvas = MatplotlibCanvas()
    _seed_plot(mpl_canvas)
    toolbar = PlotToolbar(mpl_canvas)
    target = Path("tests") / "_plot_toolbar_export.png"
    if target.exists():
        target.unlink()

    monkeypatch.setattr(
        "gui.widgets.plot_toolbar.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(target), "PNG Files (*.png)"),
    )

    toolbar._export_png()
    assert target.exists()
    target.unlink()


def _make_toolbar(qapp):
    mpl_canvas = MatplotlibCanvas()
    return PlotToolbar(mpl_canvas)


def test_zoom_toggle_is_idempotent(qapp):
    """Calling _toggle_zoom(True) twice must not double-toggle the nav toolbar."""
    from unittest.mock import MagicMock

    toolbar = _make_toolbar(qapp)
    mock_nav = MagicMock()
    # navigation_toolbar is a plain instance attribute on MplWidget — safe to overwrite
    toolbar.mpl_widget.navigation_toolbar = mock_nav

    # First call: should invoke nav.zoom() once
    toolbar._toggle_zoom(True)
    assert mock_nav.zoom.call_count == 1

    # Second call with same state: should NOT invoke nav.zoom() again
    toolbar._toggle_zoom(True)
    assert mock_nav.zoom.call_count == 1   # still 1, not 2

    # Toggle off: should invoke nav.zoom() once more
    toolbar._toggle_zoom(False)
    assert mock_nav.zoom.call_count == 2


def test_reset_emits_signal(qapp):
    mpl_canvas = MatplotlibCanvas()
    _seed_plot(mpl_canvas)
    toolbar = PlotToolbar(mpl_canvas)
    called = []
    toolbar.reset_requested.connect(lambda: called.append(True))

    toolbar._reset_view()

    assert called == [True]
