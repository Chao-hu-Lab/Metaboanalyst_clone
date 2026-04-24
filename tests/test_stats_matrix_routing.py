"""GUI statistical matrix routing contract tests."""

from __future__ import annotations

from typing import Callable

import pandas as pd
import pandas.testing as pdt
import pytest

import analysis.anova as anova_module
import analysis.oplsda as oplsda_module
import analysis.pca as pca_module
import analysis.plsda as plsda_module
import analysis.univariate as univariate_module
from core.pipeline import MetaboAnalystPipeline
from gui.main_window import MainWindow
from tests.gui_layout_support import close_window

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


def _make_stats_matrices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    index = pd.Index(["S1", "S2", "S3", "S4"], name="Sample")
    labels = pd.Series(["A", "A", "B", "B"], index=index, name="Group")

    current_data = pd.DataFrame(
        {
            "F1": [101.0, 102.0, 103.0, 104.0],
            "F2": [201.0, 202.0, 203.0, 204.0],
            "F3": [301.0, 302.0, 303.0, 304.0],
        },
        index=index,
    )
    multivariate = current_data + 1000.0
    univariate = current_data + 2000.0
    volcano_fc = current_data + 3000.0
    return current_data, multivariate, univariate, volcano_fc, labels


def _prepare_window_with_stats_bundle() -> tuple[MainWindow, dict[str, object]]:
    window = MainWindow()
    current_data, multivariate, univariate, volcano_fc, labels = _make_stats_matrices()
    window.current_data = current_data.copy()
    window.labels = labels.copy()
    window._stats_matrix_bundle = {
        "multivariate_data": multivariate.copy(),
        "univariate_data": univariate.copy(),
        "volcano_fc_data": volcano_fc.copy(),
        "labels": labels.copy(),
    }
    window.stats_tab._refresh_groups()
    return window, window._stats_matrix_bundle


def _make_positive_raw_df() -> tuple[pd.DataFrame, pd.Series]:
    index = pd.Index(["S1", "S2", "S3", "S4"], name="Sample")
    labels = pd.Series(["A", "A", "B", "B"], index=index, name="Group")
    raw_df = pd.DataFrame(
        {
            "F1": [10.0, 12.0, 20.0, 22.0],
            "F2": [3.0, 4.0, 8.0, 9.0],
            "F3": [100.0, 110.0, 150.0, 170.0],
        },
        index=index,
    )
    return raw_df, labels


def _make_three_group_bundle() -> tuple[pd.DataFrame, pd.Series]:
    index = pd.Index(["S1", "S2", "S3", "S4", "S5", "S6"], name="Sample")
    labels = pd.Series(["A", "A", "B", "B", "C", "C"], index=index, name="Group")
    data = pd.DataFrame(
        {
            "F1": [1.0, 1.1, 2.0, 2.1, 3.0, 3.1],
            "F2": [10.0, 10.2, 20.0, 20.2, 30.0, 30.2],
        },
        index=index,
    )
    return data, labels


def _patch_sync_runner(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    def _run_sync(
        job_fn: Callable[[], object],
        on_success: Callable[[object], None],
        error_title: str,
    ) -> object:
        del on_success, error_title
        return job_fn()

    monkeypatch.setattr(window.stats_tab, "_run_async", _run_sync)


@pytest.mark.parametrize(
    ("module", "attr_name", "runner_name"),
    [
        (pca_module, "run_pca", "_run_pca"),
        (plsda_module, "run_plsda", "_run_plsda"),
        (oplsda_module, "run_oplsda", "_run_oplsda"),
    ],
)
def test_multivariate_stats_use_multivariate_matrix_bundle(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
    module,
    attr_name: str,
    runner_name: str,
) -> None:
    window, bundle = _prepare_window_with_stats_bundle()
    _patch_sync_runner(window, monkeypatch)
    captured: dict[str, object] = {}

    def _fake_runner(data, labels, **kwargs):
        captured["data"] = data.copy()
        captured["labels"] = labels.copy() if hasattr(labels, "copy") else labels
        captured["kwargs"] = dict(kwargs)
        return object()

    monkeypatch.setattr(module, attr_name, _fake_runner)

    getattr(window.stats_tab, runner_name)()

    pdt.assert_frame_equal(
        captured["data"],
        bundle["multivariate_data"],
        check_dtype=False,
    )
    pdt.assert_series_equal(
        captured["labels"],
        bundle["labels"],
        check_dtype=False,
        check_names=False,
    )
    close_window(window, qapp)


def test_volcano_uses_univariate_matrix_and_row_normalized_fc_bundle(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, bundle = _prepare_window_with_stats_bundle()
    _patch_sync_runner(window, monkeypatch)
    captured: dict[str, object] = {}

    window.stats_tab.vol_pair_combo.setCurrentIndex(
        window.stats_tab.vol_pair_combo.findText("A vs B")
    )

    def _fake_volcano_analysis(data, labels, **kwargs):
        captured["data"] = data.copy()
        captured["labels"] = labels.copy() if hasattr(labels, "copy") else labels
        captured["kwargs"] = dict(kwargs)
        return object()

    monkeypatch.setattr(univariate_module, "volcano_analysis", _fake_volcano_analysis)

    window.stats_tab._run_volcano()

    pdt.assert_frame_equal(
        captured["data"],
        bundle["univariate_data"],
        check_dtype=False,
    )
    pdt.assert_frame_equal(
        captured["kwargs"]["fc_df"],
        bundle["volcano_fc_data"],
        check_dtype=False,
    )
    pdt.assert_series_equal(
        captured["labels"],
        bundle["labels"],
        check_dtype=False,
        check_names=False,
    )
    close_window(window, qapp)


@pytest.mark.parametrize("test_key", ["student", "welch", "wilcoxon"])
def test_volcano_matrix_source_is_stable_across_test_modes(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
    test_key: str,
) -> None:
    window, bundle = _prepare_window_with_stats_bundle()
    _patch_sync_runner(window, monkeypatch)
    captured: dict[str, object] = {}

    window.stats_tab.vol_pair_combo.setCurrentIndex(
        window.stats_tab.vol_pair_combo.findText("A vs B")
    )
    window.stats_tab.vol_test.setCurrentIndex(window.stats_tab.vol_test.findData(test_key))

    def _fake_volcano_analysis(data, labels, **kwargs):
        captured["data"] = data.copy()
        captured["labels"] = labels.copy() if hasattr(labels, "copy") else labels
        captured["kwargs"] = dict(kwargs)
        return object()

    monkeypatch.setattr(univariate_module, "volcano_analysis", _fake_volcano_analysis)

    window.stats_tab._run_volcano()

    pdt.assert_frame_equal(captured["data"], bundle["univariate_data"], check_dtype=False)
    pdt.assert_frame_equal(captured["kwargs"]["fc_df"], bundle["volcano_fc_data"], check_dtype=False)
    pdt.assert_series_equal(
        captured["labels"],
        bundle["labels"],
        check_dtype=False,
        check_names=False,
    )
    close_window(window, qapp)


def test_anova_uses_univariate_matrix_bundle(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, bundle = _prepare_window_with_stats_bundle()
    _patch_sync_runner(window, monkeypatch)
    captured: dict[str, object] = {}

    def _fake_run_anova(data, labels, **kwargs):
        captured["data"] = data.copy()
        captured["labels"] = labels.copy() if hasattr(labels, "copy") else labels
        captured["kwargs"] = dict(kwargs)
        return object()

    monkeypatch.setattr(anova_module, "run_anova", _fake_run_anova)

    window.stats_tab._run_anova()

    pdt.assert_frame_equal(
        captured["data"],
        bundle["univariate_data"],
        check_dtype=False,
    )
    pdt.assert_series_equal(
        captured["labels"],
        bundle["labels"],
        check_dtype=False,
        check_names=False,
    )
    close_window(window, qapp)


@pytest.mark.parametrize("test_key", ["anova", "kruskal"])
def test_anova_matrix_source_is_stable_across_test_modes(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
    test_key: str,
) -> None:
    window, bundle = _prepare_window_with_stats_bundle()
    _patch_sync_runner(window, monkeypatch)
    captured: dict[str, object] = {}

    window.stats_tab.anova_test.setCurrentIndex(window.stats_tab.anova_test.findData(test_key))

    def _fake_run_anova(data, labels, **kwargs):
        captured["data"] = data.copy()
        captured["labels"] = labels.copy() if hasattr(labels, "copy") else labels
        captured["kwargs"] = dict(kwargs)
        return object()

    monkeypatch.setattr(anova_module, "run_anova", _fake_run_anova)

    window.stats_tab._run_anova()

    pdt.assert_frame_equal(captured["data"], bundle["univariate_data"], check_dtype=False)
    pdt.assert_series_equal(
        captured["labels"],
        bundle["labels"],
        check_dtype=False,
        check_names=False,
    )
    close_window(window, qapp)


def test_run_pipeline_until_norm_builds_stats_matrix_bundle_from_pipeline(qapp) -> None:
    window = MainWindow()
    raw_df, labels = _make_positive_raw_df()
    window.set_data(raw_df, labels, "Sample", "Group")
    window.set_pipeline_params(
        missing_thresh=1.0,
        impute_method="min",
        filter_method="None",
        filter_cutoff=None,
        qc_rsd_enabled=False,
        row_norm="None",
        transform="LogNorm",
        scaling="ParetoNorm",
    )

    payload = window.run_pipeline_until("norm")
    bundle = payload["stats_matrix_bundle"]

    pipeline = MetaboAnalystPipeline(window.raw_data, window.raw_labels)
    expected_processed = pipeline.run_pipeline(**window.pipeline_params)

    pdt.assert_frame_equal(
        bundle["multivariate_data"],
        expected_processed,
        check_dtype=False,
    )
    pdt.assert_frame_equal(
        bundle["univariate_data"],
        pipeline.steps["batch_corrected"],
        check_dtype=False,
    )
    pdt.assert_frame_equal(
        bundle["volcano_fc_data"],
        pipeline.steps["row_normed"],
        check_dtype=False,
    )
    pdt.assert_series_equal(
        bundle["labels"],
        pipeline.processed_labels,
        check_dtype=False,
        check_names=False,
    )
    assert bundle["removed_qc"] == 0
    close_window(window, qapp)


@pytest.mark.parametrize(
    ("transform", "scaling"),
    [
        ("LogNorm", "None"),
        ("None", "ParetoNorm"),
        ("None", "None"),
    ],
)
def test_run_pipeline_until_norm_builds_bundle_for_preprocessing_variants(
    qapp,
    transform: str,
    scaling: str,
) -> None:
    window = MainWindow()
    raw_df, labels = _make_positive_raw_df()
    window.set_data(raw_df, labels, "Sample", "Group")
    window.set_pipeline_params(
        missing_thresh=1.0,
        impute_method="min",
        filter_method="None",
        filter_cutoff=None,
        qc_rsd_enabled=False,
        row_norm="None",
        transform=transform,
        scaling=scaling,
    )

    payload = window.run_pipeline_until("norm")
    bundle = payload["stats_matrix_bundle"]

    pipeline = MetaboAnalystPipeline(window.raw_data, window.raw_labels)
    expected_processed = pipeline.run_pipeline(**window.pipeline_params)

    pdt.assert_frame_equal(bundle["multivariate_data"], expected_processed, check_dtype=False)
    pdt.assert_frame_equal(bundle["univariate_data"], pipeline.steps["batch_corrected"], check_dtype=False)
    pdt.assert_frame_equal(bundle["volcano_fc_data"], pipeline.steps["row_normed"], check_dtype=False)
    pdt.assert_series_equal(
        bundle["labels"],
        pipeline.processed_labels,
        check_dtype=False,
        check_names=False,
    )
    close_window(window, qapp)


def test_run_pipeline_until_norm_bundle_excludes_qc_and_keeps_indices_aligned(qapp) -> None:
    window = MainWindow()
    index = pd.Index(["S1", "S2", "S3", "S4", "S5"], name="Sample")
    raw_df = pd.DataFrame(
        {
            "F1": [10.0, 11.0, 12.0, 20.0, 22.0],
            "F2": [3.0, 3.5, 4.0, 8.0, 9.0],
            "F3": [100.0, 105.0, 110.0, 150.0, 170.0],
        },
        index=index,
    )
    labels = pd.Series(["A", "QC", "A", "B", "B"], index=index, name="Group")
    window.set_data(raw_df, labels, "Sample", "Group")
    window.set_pipeline_params(
        missing_thresh=1.0,
        impute_method="min",
        filter_method="None",
        filter_cutoff=None,
        qc_rsd_enabled=False,
        row_norm="None",
        transform="LogNorm",
        scaling="ParetoNorm",
    )

    payload = window.run_pipeline_until("norm")
    bundle = payload["stats_matrix_bundle"]

    expected_index = pd.Index(["S1", "S3", "S4", "S5"], name="Sample")
    assert bundle["removed_qc"] == 1
    pdt.assert_index_equal(bundle["multivariate_data"].index, expected_index)
    pdt.assert_index_equal(bundle["univariate_data"].index, expected_index)
    pdt.assert_index_equal(bundle["volcano_fc_data"].index, expected_index)
    pdt.assert_index_equal(bundle["labels"].index, expected_index)
    assert "QC" not in set(bundle["labels"].astype(str))
    close_window(window, qapp)


def test_group_refresh_preserves_existing_pairs_and_keeps_pairs_distinct(qapp) -> None:
    window = MainWindow()
    data, labels = _make_three_group_bundle()
    window.current_data = data.copy()
    window.labels = labels.copy()
    window._stats_matrix_bundle = {
        "multivariate_data": data.copy(),
        "univariate_data": data.copy(),
        "volcano_fc_data": data.copy(),
        "labels": labels.copy(),
    }

    window.stats_tab._refresh_groups()
    window.stats_tab.vol_pair_combo.setCurrentIndex(window.stats_tab.vol_pair_combo.findText("B vs C"))
    window.stats_tab.roc_pair_combo.setCurrentIndex(window.stats_tab.roc_pair_combo.findText("A vs C"))

    window.stats_tab._refresh_groups()

    assert window.stats_tab.vol_group1.currentText() == "B"
    assert window.stats_tab.vol_group2.currentText() == "C"
    assert window.stats_tab.roc_group1.currentText() == "A"
    assert window.stats_tab.roc_group2.currentText() == "C"
    assert window.stats_tab.vol_pair_combo.findText("B vs B") == -1
    assert window.stats_tab.roc_pair_combo.findText("A vs A") == -1
    close_window(window, qapp)
