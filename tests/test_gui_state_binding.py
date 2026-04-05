"""Phase 4 widget binding integration tests."""

from __future__ import annotations

import pytest

from core.app_config import load_yaml_config
from gui.main_window import MainWindow

pytestmark = [pytest.mark.gui, pytest.mark.integration]


def _set_combo_to_data(combo, value: object) -> None:
    index = combo.findData(value)
    assert index >= 0, f"Unable to find combo data {value!r}"
    combo.setCurrentIndex(index)


def test_gui_state_round_trip_restores_shared_widget_state(qapp) -> None:
    window = MainWindow()

    window.mv_tab.thresh_spin.setValue(0.35)
    _set_combo_to_data(window.mv_tab.method_combo, "median")

    _set_combo_to_data(window.filter_tab.method_combo, "mad")
    window.filter_tab.auto_check.setChecked(False)
    window.filter_tab.cutoff_spin.setValue(0.25)
    window.filter_tab.qc_check.setEnabled(True)
    window.filter_tab.qc_check.setChecked(True)
    window.filter_tab.qc_thresh_spin.setValue(0.30)

    _set_combo_to_data(window.norm_tab.row_combo, "MedianNorm")
    _set_combo_to_data(window.norm_tab.trans_combo, "LogNorm")
    _set_combo_to_data(window.norm_tab.scale_combo, "ParetoNorm")

    window.stats_tab.pca_ncomp.setValue(4)
    window.stats_tab.pls_ncomp.setValue(2)
    window.stats_tab.vip_topn.setValue(18)
    window.stats_tab.vol_fc.setValue(3.5)
    window.stats_tab.vol_p.setValue(0.01)
    window.stats_tab.vol_fdr.setChecked(False)
    window.stats_tab.anova_p.setValue(0.02)
    _set_combo_to_data(window.stats_tab.anova_test, "kruskal")
    window.stats_tab.anova_fdr.setChecked(False)

    _set_combo_to_data(window.visual_tab.hm_method, "complete")
    _set_combo_to_data(window.visual_tab.hm_metric, "cosine")
    _set_combo_to_data(window.visual_tab.hm_scale, "col")
    window.visual_tab.hm_maxfeat.setValue(1500)

    config = window._build_current_gui_preset_config()

    reloaded_window = MainWindow()
    reloaded_window._load_preset_config(config, "memory://roundtrip")

    assert reloaded_window.mv_tab.thresh_spin.value() == 0.35
    assert reloaded_window.mv_tab.method_combo.currentData() == "median"
    assert reloaded_window.filter_tab.method_combo.currentData() == "mad"
    assert reloaded_window.filter_tab.auto_check.isChecked() is False
    assert reloaded_window.filter_tab.cutoff_spin.value() == 0.25
    assert reloaded_window.filter_tab.qc_check.isChecked() is True
    assert reloaded_window.filter_tab.qc_thresh_spin.value() == 0.30
    assert reloaded_window.norm_tab.row_combo.currentData() == "MedianNorm"
    assert reloaded_window.norm_tab.trans_combo.currentData() == "LogNorm"
    assert reloaded_window.norm_tab.scale_combo.currentData() == "ParetoNorm"

    assert reloaded_window.stats_tab.pca_ncomp.value() == 4
    assert reloaded_window.stats_tab.pls_ncomp.value() == 2
    assert reloaded_window.stats_tab.vip_topn.value() == 18
    assert reloaded_window.stats_tab.vol_fc.value() == 3.5
    assert reloaded_window.stats_tab.vol_p.value() == 0.01
    assert reloaded_window.stats_tab.vol_fdr.isChecked() is False
    assert reloaded_window.stats_tab.anova_p.value() == 0.02
    assert reloaded_window.stats_tab.anova_test.currentData() == "kruskal"
    assert reloaded_window.stats_tab.anova_fdr.isChecked() is False

    assert reloaded_window.visual_tab.hm_method.currentData() == "complete"
    assert reloaded_window.visual_tab.hm_metric.currentData() == "cosine"
    assert reloaded_window.visual_tab.hm_scale.currentData() == "col"
    assert reloaded_window.visual_tab.hm_maxfeat.value() == 1500

    window.close()
    reloaded_window.close()


def test_gui_state_binding_reports_invalid_combo_fallbacks(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "impute_method": "mystery-imputer",
                "filter_method": "unknown-filter",
                "row_norm": "unknown-row-norm",
            },
            "analysis": {
                "anova": {"nonpar": "sometimes"},
                "heatmap": {
                    "method": "mystery-linkage",
                    "metric": "mystery-metric",
                    "scale": "mystery-scale",
                },
            },
        },
        require_required_sections=False,
    )

    window._load_preset_config(config, "memory://invalid-combos")

    assert window.mv_tab.method_combo.currentData() == "min"
    assert window.filter_tab.method_combo.currentData() == "iqr"
    assert window.norm_tab.row_combo.currentData() == "None"
    assert window.visual_tab.hm_method.currentData() == "ward"
    assert window.visual_tab.hm_metric.currentData() == "euclidean"
    assert window.visual_tab.hm_scale.currentData() == "row"

    ignored_text = window.preset_bar.ignored_value_label.text()
    assert "pipeline.impute_method" in ignored_text
    assert "pipeline.filter_method" in ignored_text
    assert "pipeline.row_norm" in ignored_text
    assert "analysis.heatmap.method" in ignored_text
    assert "analysis.heatmap.metric" in ignored_text
    assert "analysis.heatmap.scale" in ignored_text

    window.close()
