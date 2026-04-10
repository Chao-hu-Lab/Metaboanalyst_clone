"""Slow Phase 7 GUI smoke coverage kept outside the default PR path."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QPushButton, QScrollArea

from gui.main_window import MainWindow
from tests.gui_layout_support import (
    apply_phase7_preset_state,
    assert_scroll_reaches_widget,
    assert_widget_center_inside,
    close_window,
    configure_window_for_phase7_case,
    load_phase7_data,
    restore_window_font,
)

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.slow]


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
) -> None:
    window = MainWindow()
    gui_artifact_recorder.watch(window, f"{case_name}_window")
    gui_artifact_recorder.watch(window.preset_bar, f"{case_name}_preset_bar")
    original_font = configure_window_for_phase7_case(
        window,
        qapp,
        locale=locale,
        size=size,
        font_delta=font_delta,
        log_visible=log_visible,
    )
    try:
        apply_phase7_preset_state(window, preset_state)
        if data_state == "loaded":
            load_phase7_data(window)
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
            assert_widget_center_inside(widget, window.preset_bar)
    finally:
        restore_window_font(qapp, original_font)
        close_window(window, qapp)


def test_phase7_scroll_areas_reach_critical_controls(gui_artifact_recorder, qapp) -> None:
    window = MainWindow()
    gui_artifact_recorder.watch(window, "scroll_matrix_window")
    original_font = configure_window_for_phase7_case(
        window,
        qapp,
        locale="zh_TW",
        size=(1024, 680),
        font_delta=1,
        log_visible=True,
    )
    try:
        load_phase7_data(window)
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
            assert_scroll_reaches_widget(scroll_area, widget, qapp)

        stats_tab = window.stats_tab
        stats_tab.sub_tabs.setCurrentIndex(stats_tab.sub_tabs.count() - 1)
        qapp.processEvents()
        stats_scroll = stats_tab.sub_tabs.currentWidget()
        assert isinstance(stats_scroll, QScrollArea)
        stats_buttons = stats_scroll.widget().findChildren(QPushButton)
        assert stats_buttons
        target_button = stats_buttons[-1]
        gui_artifact_recorder.watch(stats_scroll.viewport(), "stats_clustering")
        assert_scroll_reaches_widget(stats_scroll, target_button, qapp)
    finally:
        restore_window_font(qapp, original_font)
        close_window(window, qapp)


def test_phase7_preset_apply_keeps_norm_controls_visible_after_data_mapping(
    gui_artifact_recorder,
    qapp,
) -> None:
    window = MainWindow()
    gui_artifact_recorder.watch(window, "preset_apply_window")
    gui_artifact_recorder.watch(window.preset_bar, "preset_apply_preset_bar")
    gui_artifact_recorder.watch(window.norm_tab.scroll_area.viewport(), "preset_apply_norm_viewport")
    original_font = configure_window_for_phase7_case(
        window,
        qapp,
        locale="zh_TW",
        size=(1024, 680),
        font_delta=1,
        log_visible=False,
    )
    try:
        apply_phase7_preset_state(window, "pending")
        assert window.preset_bar.state_value_label.text() == "Pending Data Mapping"

        load_phase7_data(window)
        qapp.processEvents()

        assert window.preset_bar.state_value_label.text() == "Local Preset"
        assert window.norm_tab.row_combo.currentData() == "SpecNorm"
        assert window.norm_tab.factor_combo.currentData() == "NormalizationFactor"
        assert window.norm_tab.factor_combo.isEnabled() is True

        assert_scroll_reaches_widget(window.norm_tab.scroll_area, window.norm_tab.factor_combo, qapp)
        assert_scroll_reaches_widget(window.norm_tab.scroll_area, window.norm_tab.btn_run, qapp)
        assert_scroll_reaches_widget(window.norm_tab.scroll_area, window.norm_tab.btn_reset, qapp)
        assert_widget_center_inside(window.preset_bar.summary_value_label, window.preset_bar)
        assert_widget_center_inside(window.preset_bar.ignored_value_label, window.preset_bar)
    finally:
        restore_window_font(qapp, original_font)
        close_window(window, qapp)
