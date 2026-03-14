"""Integration tests for the Phase 2 visualization workspace."""

from __future__ import annotations

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
