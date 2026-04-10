"""Focused Step 5 interaction and statistics smoke tests."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from gui.main_window import MainWindow
from tests.gui_layout_support import close_window, load_phase7_data

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


def test_stats_tab_hides_result_sidebars_until_analysis_runs(qapp) -> None:
    window = MainWindow()
    try:
        window.resize(960, 720)
        window.show()
        window.quick_run_panel.advanced_button.click()
        window._nav_list.setCurrentRow(4)
        qapp.processEvents()

        assert window.stats_tab.pca_info.isHidden() is True
        assert window.stats_tab.pls_side_panel.isHidden() is True
        assert window.stats_tab.vol_side_panel.isHidden() is True
    finally:
        close_window(window, qapp)


def test_stats_tab_analysis_context_reflects_current_matrix_scope(qapp) -> None:
    window = MainWindow()
    try:
        load_phase7_data(window)
        window.resize(1180, 760)
        window.show()
        window.quick_run_panel.advanced_button.click()
        window._nav_list.setCurrentRow(4)
        qapp.processEvents()

        assert "Exposure:1" in window.stats_tab.context_groups_value.text()
        assert "Control:1" in window.stats_tab.context_groups_value.text()
        assert window.stats_tab.context_shape_value.text() == "2 / 2"
        assert window.stats_tab.context_matrix_value.text() == "Multivariate matrix"

        window.stats_tab.sub_tabs.setCurrentIndex(3)
        qapp.processEvents()
        assert window.stats_tab.context_matrix_value.text() == "Univariate matrix + FC matrix"
    finally:
        close_window(window, qapp)


def test_stats_tab_group_refresh_preserves_existing_selection(qapp) -> None:
    window = MainWindow()
    try:
        load_phase7_data(window)
        window.show()
        window.quick_run_panel.advanced_button.click()
        window._nav_list.setCurrentRow(4)
        qapp.processEvents()

        window.stats_tab.vol_pair_combo.setCurrentIndex(
            window.stats_tab.vol_pair_combo.findText("Control vs Exposure")
        )
        window.stats_tab._refresh_groups()

        assert window.stats_tab.vol_pair_combo.currentText() == "Control vs Exposure"
    finally:
        close_window(window, qapp)


def test_stats_tab_volcano_plot_click_selects_table_row(qapp) -> None:
    window = MainWindow()
    try:
        window.show()
        window.stats_tab.vol_table.setColumnCount(3)
        window.stats_tab.vol_table.setRowCount(2)
        window.stats_tab.vol_table.setItem(0, 0, QTableWidgetItem("Feature_A"))
        window.stats_tab.vol_table.setItem(1, 0, QTableWidgetItem("Feature_B"))
        window.stats_tab._volcano_feature_to_row = {"Feature_A": 0, "Feature_B": 1}

        window.stats_tab._on_volcano_plotly_event({"type": "point_click", "feature": "Feature_B"})
        qapp.processEvents()

        assert window.stats_tab.vol_table.currentRow() == 1
    finally:
        close_window(window, qapp)


def test_stats_tab_volcano_table_selection_highlights_plotly_feature(qapp, monkeypatch) -> None:
    window = MainWindow()
    try:
        captured = {}
        monkeypatch.setattr(
            window.stats_tab.vol_widget,
            "highlight_feature",
            lambda feature: captured.setdefault("feature", feature),
        )

        window.show()
        window.stats_tab.vol_table.setColumnCount(3)
        window.stats_tab.vol_table.setRowCount(1)
        window.stats_tab.vol_table.setItem(0, 0, QTableWidgetItem("Feature_A"))
        window.stats_tab.vol_table.selectRow(0)
        qapp.processEvents()

        assert captured["feature"] == "Feature_A"
    finally:
        close_window(window, qapp)


def test_main_window_cancel_requests_active_workers(qapp) -> None:
    class _DummyWorker:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    window = MainWindow()
    try:
        worker = _DummyWorker()
        window._active_workers.add(worker)
        window._on_cancel_clicked()
        assert worker.cancelled is True
    finally:
        close_window(window, qapp)


def test_execute_full_analysis_honors_cancelled_worker(monkeypatch, qapp) -> None:
    import subprocess

    from gui.widgets.worker import CancelledError

    class _CancelledWorker:
        @staticmethod
        def is_cancelled() -> bool:
            return True

    class _FakeProcess:
        def __init__(self, *args, **kwargs):
            self.returncode = None
            self.stdout = iter(())
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout=None):
            self.returncode = -15
            return self.returncode

        def kill(self):
            self.returncode = -9

    window = MainWindow()
    try:
        monkeypatch.setattr(subprocess, "Popen", _FakeProcess)
        with pytest.raises(CancelledError):
            window._execute_full_analysis(window._build_current_gui_preset_config(), _CancelledWorker())
    finally:
        close_window(window, qapp)


def test_stats_tab_pca_score_plot_routes_to_plotly_widget(qapp, monkeypatch) -> None:
    import visualization.pca_plot as pca_plot

    window = MainWindow()
    try:
        captured = {}
        window.stats_tab._pca_result = SimpleNamespace(
            scores=pd.DataFrame([[0.1, 0.2], [0.3, 0.4]]).to_numpy(),
            labels=pd.Series(["Exposure", "Control"], index=["S1", "S2"]),
            sample_names=["S1", "S2"],
            explained_variance_ratio=np.array([0.61, 0.24]),
        )

        monkeypatch.setattr(
            pca_plot,
            "plot_pca_score_interactive",
            lambda *args, **kwargs: object(),
        )
        monkeypatch.setattr(
            window.stats_tab.pca_plotly_widget,
            "show_figure",
            lambda fig, **kwargs: captured.setdefault("fig", fig),
        )

        window.stats_tab.pca_plot_type.setCurrentIndex(window.stats_tab.pca_plot_type.findData("score"))
        window.stats_tab._update_pca_plot()

        assert captured["fig"] is not None
        assert window.stats_tab.pca_plot_stack.currentWidget() is window.stats_tab.pca_plotly_widget
    finally:
        close_window(window, qapp)


def test_stats_tab_outlier_group_filter_updates_table(qapp) -> None:
    window = MainWindow()
    try:
        window.show()
        window.stats_tab._outlier_result = SimpleNamespace(
            get_outlier_df=lambda: pd.DataFrame(
                {
                    "Sample": ["S1", "S2"],
                    "T2": [1.0, 2.0],
                    "DModX": [0.1, 0.2],
                    "Any_Outlier": [False, True],
                }
            )
        )
        window.stats_tab._outlier_labels = pd.Series(["Exposure", "Control"], index=["S1", "S2"])
        window.stats_tab._sync_display_group_combo(window.stats_tab.out_group_combo, ["Exposure", "Control"])

        window.stats_tab.out_group_combo.setCurrentIndex(window.stats_tab.out_group_combo.findData("Control"))
        qapp.processEvents()

        assert window.stats_tab.out_table.rowCount() == 1
        assert window.stats_tab.out_table.item(0, 0).text() == "S2"
    finally:
        close_window(window, qapp)


def test_outlier_score_plot_all_groups_keeps_group_legend(monkeypatch) -> None:
    from analysis.outlier import OutlierResult
    from sklearn.decomposition import PCA
    from visualization.outlier_plot import plot_outlier_score

    scores = np.array([[0.1, 0.2], [0.3, 0.1], [1.4, 1.2], [1.6, 1.1]])
    result = OutlierResult(
        scores=scores,
        t2_values=np.array([0.1, 0.2, 1.5, 1.8]),
        t2_threshold=1.0,
        dmodx=np.array([0.05, 0.06, 0.2, 0.22]),
        dmodx_threshold=0.15,
        outlier_mask_t2=np.array([False, False, True, True]),
        outlier_mask_dmodx=np.array([False, False, True, True]),
        sample_names=["S1", "S2", "S3", "S4"],
        explained_variance=np.array([0.6, 0.2]),
        pca_model=PCA(n_components=2),
    )
    labels = pd.Series(["Exposure", "Exposure", "Normal", "Control"], index=result.sample_names)

    fig = plot_outlier_score(result, labels=labels, group_filter=None, theme="light")
    legend = fig.axes[0].get_legend()
    texts = [text.get_text() for text in legend.get_texts()]

    assert "Exposure" in texts
    assert "Normal" in texts
    assert "Control" in texts
    assert "Outlier" in texts


def test_stats_tab_switches_splitters_vertical_on_narrow_width(qapp) -> None:
    window = MainWindow()
    try:
        window.resize(960, 720)
        window.show()
        window.quick_run_panel.advanced_button.click()
        window._nav_list.setCurrentRow(4)
        qapp.processEvents()

        assert window.stats_tab.pca_splitter.orientation() == Qt.Orientation.Vertical
        assert window.stats_tab.pls_splitter.orientation() == Qt.Orientation.Vertical

        window.resize(1400, 900)
        qapp.processEvents()

        assert window.stats_tab.pca_splitter.orientation() == Qt.Orientation.Horizontal
        assert window.stats_tab.pls_splitter.orientation() == Qt.Orientation.Horizontal
    finally:
        close_window(window, qapp)


def test_stats_tab_passes_active_theme_to_plot_helpers(qapp, monkeypatch) -> None:
    import visualization.roc_plot as roc_plot

    window = MainWindow()
    window.theme_manager.set_theme("dark")
    stats_tab = window.stats_tab
    stats_tab._roc_result = SimpleNamespace()

    captured = {}

    def fake_plot_roc_curves(
        roc_result,
        show_multi: bool = True,
        top_n: int = 5,
        theme: str = "light",
        fig=None,
    ):
        captured["theme"] = theme
        return fig

    monkeypatch.setattr(roc_plot, "plot_roc_curves", fake_plot_roc_curves)
    stats_tab.roc_plot_type.setCurrentIndex(stats_tab.roc_plot_type.findData("roc"))
    stats_tab._update_roc_plot()

    assert captured["theme"] == "dark"
    close_window(window, qapp)


def test_stats_tab_pca_plot_update_no_longer_requires_removed_shared_preview(qapp, monkeypatch) -> None:
    import visualization.pca_plot as pca_plot

    window = MainWindow()
    stats_tab = window.stats_tab
    stats_tab._pca_result = object()

    def fake_plot_pca_score(*args, **kwargs):
        return kwargs.get("fig")

    monkeypatch.setattr(pca_plot, "plot_pca_score", fake_plot_pca_score)
    stats_tab.pca_plot_type.setCurrentIndex(stats_tab.pca_plot_type.findData("score"))
    stats_tab._update_pca_plot()
    close_window(window, qapp)
