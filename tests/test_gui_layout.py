"""Integration and layout smoke tests for the desktop GUI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QPushButton, QScrollArea

from core.app_config import load_yaml_config
from gui.main_window import MainWindow
from gui.settings_dialog import SettingsDialog

pytestmark = [pytest.mark.gui, pytest.mark.integration]


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
    assert "colorblind" not in items
    window.close()


def test_settings_dialog_theme_options_match_gui_modes(qapp):
    dialog = SettingsDialog(current_theme="dark")
    items = [dialog.theme_combo.itemData(i) for i in range(dialog.theme_combo.count())]
    assert items == ["light", "dark"]
    dialog.close()


def _widget_center_in_ancestor(widget, ancestor) -> QPoint:
    return widget.mapTo(ancestor, widget.rect().center())


def _sample_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "F1": [1.0, 2.0],
            "F2": [3.0, 4.0],
        },
        index=pd.Index(["S1", "S2"], name="Sample"),
    )


def _sample_labels(matrix: pd.DataFrame) -> pd.Series:
    return pd.Series(["Case", "Control"], index=matrix.index, name="Group")


def _sample_info() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Sample": ["S1", "S2"],
            "NormalizationFactor": [1.1, 0.9],
        }
    )


def _configure_window_for_phase7_case(
    window: MainWindow,
    qapp,
    *,
    locale: str,
    size: tuple[int, int],
    font_delta: int,
    log_visible: bool,
) -> object:
    original_font = qapp.font()
    adjusted_font = qapp.font()
    adjusted_font.setPointSize(max(1, original_font.pointSize() + font_delta))
    qapp.setFont(adjusted_font)
    try:
        if locale != "en":
            window.switch_language(locale)
        window.resize(*size)
        window._log_dock.setVisible(log_visible)
        window.show()
        qapp.processEvents()
    except Exception:
        qapp.setFont(original_font)
        raise
    return original_font


def _restore_window_font(qapp, original_font) -> None:
    qapp.setFont(original_font)
    qapp.processEvents()


def _assert_widget_center_inside(widget, ancestor) -> None:
    center = _widget_center_in_ancestor(widget, ancestor)
    assert ancestor.rect().contains(center), widget.objectName() or widget.text() or type(widget).__name__


def _apply_phase7_preset_state(window: MainWindow, preset_state: str) -> None:
    if preset_state == "none":
        return

    if preset_state == "builtin":
        preset = next(
            preset
            for preset in window._builtin_preset_refs
            if preset.preset_id == "tissue_knn_rsd050_marker_verify"
        )
        window._load_preset_reference(preset)
        return

    if preset_state == "pending":
        config = load_yaml_config(
            {
                "pipeline": {
                    "row_norm": "SpecNorm",
                    "transform": "LogNorm",
                    "missing_thresh": 0.35,
                },
                "spec_norm": {
                    "factor_column": "NormalizationFactor",
                },
                "legacy_bundle": {
                    "note": "keep for ignored summary",
                },
            },
            require_required_sections=False,
        )
        window._load_preset_config(config, "C:/tmp/phase7_pending.yaml")
        return

    raise ValueError(f"Unsupported preset state: {preset_state}")


def _load_phase7_data(window: MainWindow) -> None:
    matrix = _sample_matrix()
    window.set_data(
        matrix,
        _sample_labels(matrix),
        sample_col="Sample",
        group_col="Group",
        sample_info=_sample_info(),
    )


def _assert_scroll_reaches_widget(scroll_area: QScrollArea, widget, qapp) -> None:
    scroll_area.verticalScrollBar().setValue(0)
    qapp.processEvents()
    scroll_area.ensureWidgetVisible(widget)
    qapp.processEvents()
    center = _widget_center_in_ancestor(widget, scroll_area.viewport())
    assert scroll_area.viewport().rect().contains(center), widget.objectName() or widget.text()


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
            window.preset_bar.browse_button,
            window.preset_bar.run_button,
            window.preset_bar.inspect_button,
            window.preset_bar.advanced_button,
            window.preset_bar.more_button,
            window.preset_bar.open_output_button,
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


@pytest.mark.parametrize(
    ("case_name", "locale", "size", "font_delta", "log_visible", "data_state", "preset_state", "expected_state"),
    [
        (
            "defaults_en_small_log_on",
            "en",
            (1024, 680),
            0,
            True,
            "unloaded",
            "none",
            "Unsaved",
        ),
        (
            "pending_zh_small_largefont",
            "zh_TW",
            (1024, 680),
            1,
            True,
            "unloaded",
            "pending",
            "Pending Data Mapping",
        ),
        (
            "builtin_en_medium_data",
            "en",
            (1280, 800),
            0,
            False,
            "loaded",
            "builtin",
            "Built-in Preset",
        ),
        (
            "pending_zh_wide_data",
            "zh_TW",
            (1366, 768),
            1,
            False,
            "loaded",
            "pending",
            "Local Preset",
        ),
    ],
)
@pytest.mark.slow
def test_phase7_preset_bar_smoke_matrix(
    case_name: str,
    locale: str,
    size: tuple[int, int],
    font_delta: int,
    log_visible: bool,
    data_state: str,
    preset_state: str,
    expected_state: str,
    gui_artifact_recorder,
    qapp,
):
    window = MainWindow()
    gui_artifact_recorder.watch(window, f"{case_name}_window")
    gui_artifact_recorder.watch(window.preset_bar, f"{case_name}_preset_bar")
    original_font = _configure_window_for_phase7_case(
        window,
        qapp,
        locale=locale,
        size=size,
        font_delta=font_delta,
        log_visible=log_visible,
    )
    try:
        _apply_phase7_preset_state(window, preset_state)
        if data_state == "loaded":
            _load_phase7_data(window)
        qapp.processEvents()

        assert window.preset_bar.isVisible()
        assert window._log_dock.isVisible() is log_visible
        assert window.preset_bar.state_value_label.text() == expected_state

        for widget in (
            window.preset_bar.load_button,
            window.preset_bar.browse_button,
            window.preset_bar.run_button,
            window.preset_bar.inspect_button,
            window.preset_bar.advanced_button,
            window.preset_bar.more_button,
            window.preset_bar.source_value_label,
            window.preset_bar.state_value_label,
            window.preset_bar.input_value_label,
            window.preset_bar.data_value_label,
            window.preset_bar.summary_value_label,
            window.preset_bar.ignored_value_label,
        ):
            assert widget.isVisible(), case_name
            _assert_widget_center_inside(widget, window.preset_bar)
    finally:
        _restore_window_font(qapp, original_font)
        window.close()


@pytest.mark.slow
def test_phase7_scroll_areas_reach_critical_controls(gui_artifact_recorder, qapp):
    window = MainWindow()
    gui_artifact_recorder.watch(window, "scroll_matrix_window")
    original_font = _configure_window_for_phase7_case(
        window,
        qapp,
        locale="zh_TW",
        size=(1024, 680),
        font_delta=1,
        log_visible=True,
    )
    try:
        _load_phase7_data(window)
        qapp.processEvents()

        cases = [
            ("missing", window.mv_tab.scroll_area, window.mv_tab.btn_run),
            ("filter", window.filter_tab.scroll_area, window.filter_tab.btn_run),
            ("norm_run", window.norm_tab.scroll_area, window.norm_tab.btn_run),
            ("norm_reset", window.norm_tab.scroll_area, window.norm_tab.btn_reset),
        ]

        for case_name, scroll_area, widget in cases:
            gui_artifact_recorder.watch(scroll_area.viewport(), case_name)
            assert scroll_area.widgetResizable(), case_name
            _assert_scroll_reaches_widget(scroll_area, widget, qapp)

        stats_tab = window.stats_tab
        stats_tab.sub_tabs.setCurrentIndex(stats_tab.sub_tabs.count() - 1)
        qapp.processEvents()
        stats_scroll = stats_tab.sub_tabs.currentWidget()
        assert isinstance(stats_scroll, QScrollArea)
        stats_buttons = stats_scroll.widget().findChildren(QPushButton)
        assert stats_buttons
        target_button = stats_buttons[-1]
        gui_artifact_recorder.watch(stats_scroll.viewport(), "stats_clustering")
        _assert_scroll_reaches_widget(stats_scroll, target_button, qapp)
    finally:
        _restore_window_font(qapp, original_font)
        window.close()


@pytest.mark.slow
def test_phase7_preset_apply_keeps_norm_controls_visible_after_data_mapping(
    gui_artifact_recorder,
    qapp,
):
    window = MainWindow()
    gui_artifact_recorder.watch(window, "preset_apply_window")
    gui_artifact_recorder.watch(window.preset_bar, "preset_apply_preset_bar")
    gui_artifact_recorder.watch(window.norm_tab.scroll_area.viewport(), "preset_apply_norm_viewport")
    original_font = _configure_window_for_phase7_case(
        window,
        qapp,
        locale="zh_TW",
        size=(1024, 680),
        font_delta=1,
        log_visible=False,
    )
    try:
        _apply_phase7_preset_state(window, "pending")
        assert window.preset_bar.state_value_label.text() == "Pending Data Mapping"

        _load_phase7_data(window)
        qapp.processEvents()

        assert window.preset_bar.state_value_label.text() == "Local Preset"
        assert window.norm_tab.row_combo.currentData() == "SpecNorm"
        assert window.norm_tab.factor_combo.currentData() == "NormalizationFactor"
        assert window.norm_tab.factor_combo.isEnabled() is True

        _assert_scroll_reaches_widget(window.norm_tab.scroll_area, window.norm_tab.factor_combo, qapp)
        _assert_scroll_reaches_widget(window.norm_tab.scroll_area, window.norm_tab.btn_run, qapp)
        _assert_scroll_reaches_widget(window.norm_tab.scroll_area, window.norm_tab.btn_reset, qapp)
        _assert_widget_center_inside(window.preset_bar.summary_value_label, window.preset_bar)
        _assert_widget_center_inside(window.preset_bar.ignored_value_label, window.preset_bar)
    finally:
        _restore_window_font(qapp, original_font)
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


def test_quick_run_panel_toggles_advanced_workspace(qapp):
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
    window.close()


def test_quick_run_enables_for_cli_compatible_sample_type_input(tmp_path, qapp):
    window = MainWindow()
    csv_path = tmp_path / "quick_run_sample_type.csv"
    pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
            "Sample_A": ["Case", 1.0, 3.0],
            "Sample_B": ["Control", 2.0, 4.0],
        }
    ).to_csv(csv_path, index=False)

    window.import_tab._load_file_for_preview(str(csv_path), auto_load=True)
    qapp.processEvents()

    assert window.current_data is not None
    assert window.quick_run_panel.run_button.isEnabled() is True
    assert str(csv_path) in window.quick_run_panel.input_value_label.text()
    window.close()


def test_quick_run_does_not_auto_switch_rows_oriented_input(tmp_path, qapp):
    window = MainWindow()
    csv_path = tmp_path / "rows_oriented.csv"
    pd.DataFrame(
        {
            "Sample": ["S1", "S2"],
            "Group": ["Case", "Control"],
            "F1": [1.0, 2.0],
            "F2": [3.0, 4.0],
        }
    ).to_csv(csv_path, index=False)

    window.import_tab._load_file_for_preview(str(csv_path), auto_load=True)
    qapp.processEvents()

    assert window.import_tab.orientation_combo.currentData() == "rows"
    assert window.quick_run_panel.run_button.isEnabled() is False
    assert window.current_data is not None
    window.close()


def test_tabs_are_no_longer_sequentially_locked(qapp):
    window = MainWindow()

    for i in range(window._nav_list.count()):
        item = window._nav_list.item(i)
        assert bool(item.flags() & Qt.ItemFlag.ItemIsEnabled)

    window.close()


def test_open_output_folder_uses_desktop_services(tmp_path, qapp, monkeypatch):
    window = MainWindow()
    window._last_run_output_dir = str(tmp_path)

    opened = {}

    def fake_open_url(url):
        opened["url"] = url
        return True

    monkeypatch.setattr(QDesktopServices, "openUrl", fake_open_url)

    window._open_output_folder()

    assert Path(opened["url"].toLocalFile()) == tmp_path
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
