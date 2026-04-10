"""GUI annotation policy tests for ANOVA/Kruskal display wording."""

from __future__ import annotations

import pandas as pd
import pytest

from analysis.anova import ANOVAResult
from gui.main_window import MainWindow

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


def _patch_sync_runner(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    def _run_sync(job_fn, on_success, error_title):
        del error_title
        result = job_fn()
        on_success(result)
        return result

    monkeypatch.setattr(window.stats_tab, "_run_async", _run_sync)


def test_stats_tab_kruskal_uses_h_statistic_header_and_boxplot_metadata(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow()
    index = pd.Index(["S1", "S2", "S3", "S4", "S5", "S6"], name="Sample")
    data = pd.DataFrame(
        {
            "FeatA": [10.0, 11.0, 12.0, 18.0, 19.0, 20.0],
            "FeatB": [1.0, 1.2, 1.1, 2.0, 2.2, 2.1],
        },
        index=index,
    )
    labels = pd.Series(["A", "A", "A", "B", "B", "B"], index=index, name="Group")
    window.current_data = data.copy()
    window.labels = labels.copy()
    window._stats_matrix_bundle = {
        "multivariate_data": data.copy(),
        "univariate_data": data.copy(),
        "volcano_fc_data": data.copy(),
        "labels": labels.copy(),
    }
    window.stats_tab._refresh_groups()
    _patch_sync_runner(window, monkeypatch)

    result_df = pd.DataFrame(
        {
            "Feature": ["FeatA", "FeatB"],
            "statistic": [5.5, 2.2],
            "pvalue": [0.02, 0.10],
            "pvalue_adj": [0.04, 0.10],
            "neg_log10p": [1.4, 1.0],
            "significant": [True, False],
        }
    )

    def _fake_run_anova(*args, **kwargs):
        del args, kwargs
        return ANOVAResult(result_df, groups=["A", "B"], p_thresh=0.05, method_key="kruskal")

    captured: dict[str, object] = {}

    def _fake_plot_feature_boxplot(df, labels, feature_name, **kwargs):
        captured["df"] = df.copy()
        captured["labels"] = labels.copy()
        captured["feature_name"] = feature_name
        captured["kwargs"] = dict(kwargs)
        return kwargs["fig"]

    monkeypatch.setattr("analysis.anova.run_anova", _fake_run_anova)
    monkeypatch.setattr("visualization.anova_plot.plot_feature_boxplot", _fake_plot_feature_boxplot)

    window.stats_tab.anova_test.setCurrentIndex(window.stats_tab.anova_test.findData("kruskal"))
    window.stats_tab._run_anova()

    assert window.stats_tab.anova_table.horizontalHeaderItem(1).text() == "H statistic"

    window.stats_tab.anova_feat_combo.setCurrentIndex(window.stats_tab.anova_feat_combo.findData("FeatA"))
    window.stats_tab._draw_feature_boxplot()

    assert captured["feature_name"] == "FeatA"
    assert captured["kwargs"]["annotation_method"] == "mannwhitney"
    window.close()


def test_stats_tab_anova_feature_combo_change_redraws_boxplot(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow()
    index = pd.Index(["S1", "S2", "S3", "S4"], name="Sample")
    data = pd.DataFrame(
        {
            "FeatA": [1.0, 1.2, 2.0, 2.2],
            "FeatB": [5.0, 5.2, 8.0, 8.2],
        },
        index=index,
    )
    labels = pd.Series(["A", "A", "B", "B"], index=index, name="Group")
    window.current_data = data.copy()
    window.labels = labels.copy()
    window._stats_matrix_bundle = {
        "multivariate_data": data.copy(),
        "univariate_data": data.copy(),
        "volcano_fc_data": data.copy(),
        "labels": labels.copy(),
    }
    window.stats_tab._refresh_groups()
    _patch_sync_runner(window, monkeypatch)

    result_df = pd.DataFrame(
        {
            "Feature": ["FeatA", "FeatB"],
            "statistic": [9.0, 4.0],
            "pvalue": [0.01, 0.04],
            "pvalue_adj": [0.02, 0.04],
            "neg_log10p": [2.0, 1.4],
            "significant": [True, True],
        }
    )

    def _fake_run_anova(*args, **kwargs):
        del args, kwargs
        return ANOVAResult(result_df, groups=["A", "B"], p_thresh=0.05, method_key="anova")

    draw_calls: list[str] = []

    def _fake_plot_feature_boxplot(df, labels, feature_name, **kwargs):
        del df, labels, kwargs
        draw_calls.append(str(feature_name))
        return window.stats_tab.anova_feat_canvas.figure

    monkeypatch.setattr("analysis.anova.run_anova", _fake_run_anova)
    monkeypatch.setattr("visualization.anova_plot.plot_feature_boxplot", _fake_plot_feature_boxplot)

    window.stats_tab._run_anova()
    draw_calls.clear()

    window.stats_tab.anova_feat_combo.setCurrentIndex(window.stats_tab.anova_feat_combo.findData("FeatB"))

    assert draw_calls == ["FeatB"]
    window.close()
