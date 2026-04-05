"""Integration and layout smoke tests for the desktop GUI."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QScrollArea

from gui.main_window import MainWindow


def test_main_window_initialization(qapp):
    window = MainWindow()
    assert window is not None
    assert hasattr(window, "theme_manager")
    assert window.theme_manager.current_theme in window.theme_manager.SUPPORTED_THEMES
    window.close()


def test_theme_combo_box_exists(qapp):
    window = MainWindow()
    assert hasattr(window, "theme_combo")
    items = [window.theme_combo.itemText(i) for i in range(window.theme_combo.count())]
    assert "light" in items
    assert "dark" in items
    assert "colorblind" in items
    window.close()


def _widget_center_in_ancestor(widget, ancestor) -> QPoint:
    return widget.mapTo(ancestor, widget.rect().center())


def test_visual_tab_initialization(qapp):
    window = MainWindow()
    visual_tab = window.visual_tab

    assert visual_tab is not None
    assert hasattr(visual_tab, "theme_manager")
    assert hasattr(visual_tab, "mpl_canvas")
    assert hasattr(visual_tab, "update_timer")
    assert visual_tab.control_dock.windowTitle() == "Parameters"
    window.close()


def test_parameter_change_triggers_debounce(qapp):
    window = MainWindow()
    visual_tab = window.visual_tab

    visual_tab.scale_spinbox.setValue(90)
    visual_tab.scale_spinbox.setValue(95)
    visual_tab.scale_spinbox.setValue(100)

    assert visual_tab.update_timer.isActive()
    window.close()


def test_theme_change_updates_plot(qapp):
    window = MainWindow()
    visual_tab = window.visual_tab

    window.theme_manager.set_theme("dark")

    assert visual_tab.theme_manager.current_theme == "dark"
    assert visual_tab.mpl_canvas.plot_toolbar.theme_value_label.text() == "Dark"
    window.close()


def test_phase6_preset_bar_buttons_stay_inside_visible_bar(qapp):
    window = MainWindow()
    original_font = qapp.font()
    larger_font = qapp.font()
    larger_font.setPointSize(original_font.pointSize() + 1)
    qapp.setFont(larger_font)
    try:
        window.resize(1024, 680)
        window.show()
        qapp.processEvents()

        for button in (
            window.preset_bar.load_button,
            window.preset_bar.apply_button,
            window.preset_bar.save_button,
            window.preset_bar.reset_button,
        ):
            center = _widget_center_in_ancestor(button, window.preset_bar)
            assert window.preset_bar.rect().contains(center), button.text()
    finally:
        qapp.setFont(original_font)
        window.close()


def test_phase6_norm_tab_action_buttons_keep_clickable_height(qapp):
    window = MainWindow()
    original_font = qapp.font()
    larger_font = qapp.font()
    larger_font.setPointSize(original_font.pointSize() + 1)
    qapp.setFont(larger_font)
    try:
        window.resize(1024, 680)
        window.show()
        window._nav_list.setCurrentRow(3)
        qapp.processEvents()

        assert window.norm_tab.btn_run.height() >= window.norm_tab.btn_run.sizeHint().height() - 4
        assert window.norm_tab.btn_reset.height() >= window.norm_tab.btn_reset.sizeHint().height() - 4
    finally:
        qapp.setFont(original_font)
        window.close()


def test_phase6_high_risk_tabs_wrap_content_in_scroll_areas(qapp):
    window = MainWindow()
    try:
        for tab in (window.mv_tab, window.filter_tab, window.norm_tab, window.stats_tab):
            scroll_areas = tab.findChildren(QScrollArea)
            assert scroll_areas, type(tab).__name__
            assert any(scroll.widgetResizable() for scroll in scroll_areas), type(tab).__name__
    finally:
        window.close()


def test_reset_button_resets_parameters(qapp):
    window = MainWindow()
    visual_tab = window.visual_tab

    visual_tab.scale_spinbox.setValue(130)
    visual_tab.hm_maxfeat.setValue(900)
    visual_tab._reset_view()

    assert visual_tab.scale_spinbox.value() == 100
    assert visual_tab.hm_maxfeat.value() == 500
    window.close()


def test_chart_type_visibility_changes(qapp):
    window = MainWindow()
    visual_tab = window.visual_tab

    visual_tab.chart_type_combo.setCurrentText("Heatmap")

    assert not visual_tab.heatmap_group.isHidden()
    assert visual_tab.boxplot_group.isHidden()
    window.close()


def test_visual_tab_exposes_interactive_chart_types(qapp):
    window = MainWindow()
    visual_tab = window.visual_tab

    items = [visual_tab.chart_type_combo.itemText(i) for i in range(visual_tab.chart_type_combo.count())]
    assert "Volcano Plot (Interactive)" in items
    assert "ROC Curves (Interactive)" in items
    window.close()


def test_visual_tab_routes_interactive_volcano_to_plotly_widget(qapp, monkeypatch):
    import visualization.volcano_plot as volcano_plot

    window = MainWindow()
    window.current_data = pd.DataFrame({"A": [1.0, 2.0], "B": [2.0, 3.0]}, index=["S1", "S2"])
    window.labels = pd.Series(["Case", "Control"], index=window.current_data.index)
    window.stats_tab._volcano_result = SimpleNamespace()

    captured = {}

    def fake_plot_volcano_interactive(volcano_result, top_n: int = 10, fc_threshold=None, pval_threshold=None, theme: str = "light"):
        captured["theme"] = theme
        captured["result"] = volcano_result
        return object()

    def fake_show_figure(fig):
        captured["figure"] = fig

    monkeypatch.setattr(volcano_plot, "plot_volcano_interactive", fake_plot_volcano_interactive)
    monkeypatch.setattr(window.visual_tab.plotly_widget, "show_figure", fake_show_figure)

    window.visual_tab.chart_type_combo.setCurrentIndex(
        window.visual_tab.chart_type_combo.findData("volcano_interactive")
    )
    window.visual_tab.redraw_plot()

    assert captured["result"] is window.stats_tab._volcano_result
    assert captured["theme"] == window.theme_manager.current_theme
    assert captured["figure"] is not None
    assert window.visual_tab.preview_stack.currentWidget() is window.visual_tab.plotly_widget
    window.close()


def test_stats_tab_passes_active_theme_to_plot_helpers(qapp, monkeypatch):
    import visualization.roc_plot as roc_plot

    window = MainWindow()
    window.theme_manager.set_theme("dark")
    stats_tab = window.stats_tab
    stats_tab._roc_result = SimpleNamespace()

    captured = {}

    def fake_plot_roc_curves(roc_result, show_multi: bool = True, top_n: int = 5, theme: str = "light", fig=None):
        captured["theme"] = theme
        return fig

    monkeypatch.setattr(roc_plot, "plot_roc_curves", fake_plot_roc_curves)
    stats_tab.roc_plot_type.setCurrentIndex(stats_tab.roc_plot_type.findData("roc"))
    stats_tab._update_roc_plot()

    assert captured["theme"] == "dark"
    window.close()
