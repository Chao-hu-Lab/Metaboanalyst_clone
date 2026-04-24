"""Fast GUI shell and layout smoke tests."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QBoxLayout, QPushButton, QScrollArea

from gui.main_window import MainWindow
from gui.widgets.log_handler import QLogHandler
from gui.settings_dialog import SettingsDialog
from tests.gui_layout_support import (
    assert_widget_center_inside,
    close_window,
    sample_labels,
    sample_matrix,
)

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


def test_main_window_initialization(qapp) -> None:
    window = MainWindow()
    assert window is not None
    assert hasattr(window, "theme_manager")
    assert window.theme_manager.current_theme in window.theme_manager.SUPPORTED_THEMES
    close_window(window, qapp)


def test_theme_combo_box_exists(qapp) -> None:
    window = MainWindow()
    assert hasattr(window, "theme_combo")
    items = [window.theme_combo.itemText(i) for i in range(window.theme_combo.count())]
    assert "light" in items
    assert "dark" in items
    assert "colorblind" not in items
    close_window(window, qapp)


def test_main_window_close_removes_pipeline_log_handler(qapp) -> None:
    pipeline_logger = logging.getLogger("pipeline")
    baseline = sum(isinstance(handler, QLogHandler) for handler in pipeline_logger.handlers)

    window = MainWindow()
    opened = sum(isinstance(handler, QLogHandler) for handler in pipeline_logger.handlers)

    assert opened == baseline + 1

    close_window(window, qapp)

    closed = sum(isinstance(handler, QLogHandler) for handler in pipeline_logger.handlers)
    assert closed == baseline


def test_settings_dialog_theme_options_match_gui_modes(qapp) -> None:
    dialog = SettingsDialog(current_theme="dark")
    items = [dialog.theme_combo.itemData(i) for i in range(dialog.theme_combo.count())]
    assert items == ["light", "dark"]
    dialog.close()


def test_visual_tab_initialization(qapp) -> None:
    window = MainWindow()
    visual_tab = window.visual_tab

    assert visual_tab is not None
    assert hasattr(visual_tab, "theme_manager")
    assert hasattr(visual_tab, "mpl_canvas")
    assert hasattr(visual_tab, "update_timer")
    assert visual_tab.control_dock.windowTitle() == "Parameters"
    close_window(window, qapp)


def test_parameter_change_triggers_debounce(qapp) -> None:
    window = MainWindow()
    visual_tab = window.visual_tab

    visual_tab.scale_spinbox.setValue(90)
    visual_tab.scale_spinbox.setValue(95)
    visual_tab.scale_spinbox.setValue(100)

    assert visual_tab.update_timer.isActive()
    close_window(window, qapp)


def test_theme_change_updates_plot(qapp) -> None:
    window = MainWindow()
    visual_tab = window.visual_tab

    window.theme_manager.set_theme("dark")

    assert visual_tab.theme_manager.current_theme == "dark"
    assert visual_tab.mpl_canvas.plot_toolbar.theme_value_label.text() == "Dark"
    close_window(window, qapp)


def test_phase6_preset_bar_buttons_stay_inside_visible_bar(qapp) -> None:
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
            window.preset_bar.browse_button,
            window.preset_bar.run_button,
            window.preset_bar.inspect_button,
            window.preset_bar.advanced_button,
            window.preset_bar.more_button,
            window.preset_bar.open_output_button,
        ):
            assert_widget_center_inside(button, window.preset_bar)
    finally:
        qapp.setFont(original_font)
        close_window(window, qapp)


def test_phase6_norm_tab_action_buttons_keep_clickable_height(qapp) -> None:
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
        close_window(window, qapp)


def test_phase6_high_risk_tabs_wrap_content_in_scroll_areas(qapp) -> None:
    window = MainWindow()
    try:
        for tab in (window.mv_tab, window.filter_tab, window.norm_tab, window.stats_tab):
            scroll_areas = tab.findChildren(QScrollArea)
            assert scroll_areas, type(tab).__name__
            assert any(scroll.widgetResizable() for scroll in scroll_areas), type(tab).__name__
    finally:
        close_window(window, qapp)


def test_data_import_tab_wraps_content_in_scroll_area(qapp) -> None:
    window = MainWindow()
    try:
        scroll_areas = window.import_tab.findChildren(QScrollArea)
        assert scroll_areas
        assert any(scroll.widgetResizable() for scroll in scroll_areas)
    finally:
        close_window(window, qapp)


def test_normalization_tab_no_longer_renders_embedded_preview(qapp) -> None:
    window = MainWindow()
    try:
        assert hasattr(window.norm_tab, "preview_group") is False
        assert "Preview" not in window.norm_tab.log_group.title()
    finally:
        close_window(window, qapp)


def test_reset_button_resets_parameters(qapp) -> None:
    window = MainWindow()
    visual_tab = window.visual_tab

    visual_tab.scale_spinbox.setValue(130)
    visual_tab.hm_maxfeat.setValue(900)
    visual_tab._reset_view()

    assert visual_tab.scale_spinbox.value() == 100
    assert visual_tab.hm_maxfeat.value() == 500
    close_window(window, qapp)


def test_quick_run_panel_toggles_advanced_workspace(qapp) -> None:
    window = MainWindow()

    assert window._advanced_container.isHidden() is True

    window.quick_run_panel.advanced_button.click()
    qapp.processEvents()

    assert window._advanced_container.isHidden() is False
    assert window.quick_run_panel.advanced_button.text() == "Hide Advanced"

    window.quick_run_panel.advanced_button.click()
    qapp.processEvents()

    assert window._advanced_container.isHidden() is True
    assert window.quick_run_panel.advanced_button.text() == "Show Advanced"
    close_window(window, qapp)


def test_workflow_scroll_preserves_quick_run_height_when_advanced_is_visible(qapp) -> None:
    window = MainWindow()
    window.resize(1181, 768)
    window.quick_run_panel.advanced_button.click()
    window.show()
    qapp.processEvents()

    assert isinstance(window._workflow_scroll, QScrollArea)
    assert window._workflow_scroll.widgetResizable() is True
    assert window.quick_run_panel.height() >= window.quick_run_panel.minimumSizeHint().height() - 12
    close_window(window, qapp)


def test_log_dock_defaults_to_compact_height(qapp) -> None:
    window = MainWindow()
    try:
        window.resize(1181, 768)
        window.show()
        qapp.processEvents()

        assert window._log_dock.height() <= 180
        assert window.log_widget.maximumHeight() == 140
    finally:
        close_window(window, qapp)


def test_normalization_method_labels_follow_active_locale(qapp) -> None:
    window = MainWindow()
    try:
        window.switch_language("en")
        assert (
            window.norm_tab.row_combo.itemText(window.norm_tab.row_combo.findData("MedianNorm"))
            == "Normalize by row median"
        )
        assert (
            window.norm_tab.trans_combo.itemText(window.norm_tab.trans_combo.findData("LogNorm"))
            == "Generalized Log2 (glog2)"
        )
        assert (
            window.norm_tab.scale_combo.itemText(window.norm_tab.scale_combo.findData("ParetoNorm"))
            == "Pareto scaling"
        )

        window.switch_language("zh_TW")
        row_label = window.norm_tab.row_combo.itemText(window.norm_tab.row_combo.findData("MedianNorm"))
        trans_label = window.norm_tab.trans_combo.itemText(window.norm_tab.trans_combo.findData("LogNorm"))
        scale_label = window.norm_tab.scale_combo.itemText(window.norm_tab.scale_combo.findData("ParetoNorm"))
        assert row_label != "Normalize by row median"
        assert "glog2" in trans_label
        assert "Pareto" in scale_label
    finally:
        close_window(window, qapp)


def test_missing_value_method_labels_follow_active_locale(qapp) -> None:
    window = MainWindow()
    try:
        window.switch_language("en")
        assert (
            window.mv_tab.method_combo.itemText(window.mv_tab.method_combo.findData("min"))
            == "Minimum positive / 5 (LoD)"
        )
        assert (
            window.mv_tab.method_combo.itemText(window.mv_tab.method_combo.findData("median"))
            == "Median"
        )

        window.switch_language("zh_TW")
        min_label = window.mv_tab.method_combo.itemText(window.mv_tab.method_combo.findData("min"))
        median_label = window.mv_tab.method_combo.itemText(window.mv_tab.method_combo.findData("median"))
        assert "LoD" in min_label
        assert median_label != "Median"
    finally:
        close_window(window, qapp)


def test_combat_warning_text_follows_active_locale(qapp) -> None:
    window = MainWindow()
    try:
        window._current_locale = "en"
        assert window.norm_tab._combat_warning_dialog_title() == "ComBat Risk Warning"
        english_text = window.norm_tab._combat_warning_dialog_text(
            ["Batch and type show strong overlap."]
        )
        assert "Batch and type appear to overlap strongly" in english_text
        assert "Continue anyway?" in english_text

        window._current_locale = "zh_TW"
        assert window.norm_tab._combat_warning_dialog_title() == "ComBat 風險提醒"
        chinese_text = window.norm_tab._combat_warning_dialog_text(
            ["Batch and type show strong overlap."]
        )
        assert "批次與類型可能高度重合" in chinese_text
        assert "仍要繼續嗎" in chinese_text
    finally:
        close_window(window, qapp)


def test_missing_value_tab_displays_marker_aware_imputation_note(qapp) -> None:
    window = MainWindow()
    try:
        window.switch_language("en")
        assert "non-marker features only" in window.mv_tab.marker_note.text()

        window.switch_language("zh_TW")
        assert "marker" in window.mv_tab.marker_note.text().lower()
    finally:
        close_window(window, qapp)


def test_quick_run_enables_for_cli_compatible_sample_type_input(tmp_path: Path, qapp) -> None:
    window = MainWindow()
    csv_path = tmp_path / "quick_run_sample_type.csv"
    pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
            "Sample_A": ["Exposure", 1.0, 3.0],
            "Sample_B": ["Control", 2.0, 4.0],
        }
    ).to_csv(csv_path, index=False)

    window.import_tab._load_file_for_preview(str(csv_path), auto_load=True)
    qapp.processEvents()

    assert window.current_data is not None
    assert window.quick_run_panel.run_button.isEnabled() is True
    assert str(csv_path) in window.quick_run_panel.input_value_label.text()
    close_window(window, qapp)


def test_quick_run_does_not_auto_switch_rows_oriented_input(tmp_path: Path, qapp) -> None:
    window = MainWindow()
    csv_path = tmp_path / "rows_oriented.csv"
    pd.DataFrame(
        {
            "Sample": ["S1", "S2"],
            "Group": ["Exposure", "Control"],
            "F1": [1.0, 2.0],
            "F2": [3.0, 4.0],
        }
    ).to_csv(csv_path, index=False)

    window.import_tab._load_file_for_preview(str(csv_path), auto_load=True)
    qapp.processEvents()

    assert window.import_tab.orientation_combo.currentData() == "rows"
    assert window.quick_run_panel.run_button.isEnabled() is False
    assert window.current_data is not None
    close_window(window, qapp)


def test_tabs_are_no_longer_sequentially_locked(qapp) -> None:
    window = MainWindow()

    for i in range(window._nav_list.count()):
        item = window._nav_list.item(i)
        assert bool(item.flags() & Qt.ItemFlag.ItemIsEnabled)

    close_window(window, qapp)


def test_open_output_folder_uses_desktop_services(tmp_path: Path, qapp, monkeypatch) -> None:
    window = MainWindow()
    window._last_run_output_dir = str(tmp_path)

    opened = {}

    def fake_open_url(url):
        opened["url"] = url
        return True

    monkeypatch.setattr(QDesktopServices, "openUrl", fake_open_url)

    window._open_output_folder()

    assert Path(opened["url"].toLocalFile()) == tmp_path
    close_window(window, qapp)


def test_chart_type_visibility_changes(qapp) -> None:
    window = MainWindow()
    visual_tab = window.visual_tab

    visual_tab.chart_type_combo.setCurrentText("Heatmap")

    assert not visual_tab.heatmap_group.isHidden()
    assert visual_tab.boxplot_group.isHidden()
    close_window(window, qapp)


def test_visual_tab_exposes_interactive_chart_types(qapp) -> None:
    window = MainWindow()
    visual_tab = window.visual_tab

    items = [visual_tab.chart_type_combo.itemText(i) for i in range(visual_tab.chart_type_combo.count())]
    assert "Volcano Plot (Interactive)" in items
    assert "ROC Curves (Interactive)" in items
    close_window(window, qapp)


def test_plotly_widget_defaults_to_browser_fallback_in_test_mode(qapp) -> None:
    from gui.widgets.plotly_widget import PlotlyWidget

    widget = PlotlyWidget()
    try:
        assert widget._web is None
        assert widget._btn is not None
    finally:
        widget.close()
        qapp.processEvents()


def test_visual_tab_routes_interactive_volcano_to_plotly_widget(qapp, monkeypatch) -> None:
    import visualization.volcano_plot as volcano_plot

    window = MainWindow()
    window.current_data = pd.DataFrame({"A": [1.0, 2.0], "B": [2.0, 3.0]}, index=["S1", "S2"])
    window.labels = sample_labels(sample_matrix())
    window.stats_tab._volcano_result = SimpleNamespace()

    captured = {}

    def fake_plot_volcano_interactive(
        volcano_result,
        top_n: int = 10,
        fc_threshold=None,
        pval_threshold=None,
        theme: str = "light",
    ):
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
    close_window(window, qapp)


def test_visual_tab_stacks_controls_above_preview_on_narrow_width(qapp) -> None:
    window = MainWindow()
    try:
        window.resize(960, 720)
        window.show()
        window.quick_run_panel.advanced_button.click()
        window._nav_list.setCurrentRow(5)
        qapp.processEvents()

        assert window.visual_tab._root_layout.direction() == QBoxLayout.Direction.TopToBottom
        assert window.visual_tab.control_dock.maximumHeight() == 280
        assert window.visual_tab.control_dock.maximumWidth() == 16777215

        window.resize(1440, 900)
        qapp.processEvents()

        assert window.visual_tab._root_layout.direction() == QBoxLayout.Direction.LeftToRight
        assert window.visual_tab.control_dock.maximumWidth() == 320
    finally:
        close_window(window, qapp)


def test_primary_action_buttons_are_tagged_for_emphasis(qapp) -> None:
    window = MainWindow()
    try:
        assert window.mv_tab.btn_run.property("variant") == "primary"
        assert window.filter_tab.btn_run.property("variant") == "primary"
        assert window.norm_tab.btn_run.property("variant") == "primary"
        assert any(
            button.property("variant") == "primary"
            for button in window.stats_tab.findChildren(QPushButton)
        )
    finally:
        close_window(window, qapp)
