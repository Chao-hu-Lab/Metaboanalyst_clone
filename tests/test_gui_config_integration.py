"""GUI integration tests for shared config loading."""

from __future__ import annotations

import pytest

from core.app_config import default_pipeline_params, load_yaml_config
from gui.main_window import MainWindow

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


def test_main_window_uses_shared_default_pipeline_params(qapp) -> None:
    window = MainWindow()

    assert window.pipeline_params == default_pipeline_params()

    window.close()


def test_main_window_apply_loaded_config_updates_pipeline_widgets(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "missing_thresh": 0.35,
                "impute_method": "median",
                "filter_method": "mad",
                "filter_cutoff": 0.15,
                "qc_rsd_enabled": True,
                "qc_rsd_threshold": 0.30,
                "row_norm": "MedianNorm",
                "transform": "LogNorm",
                "batch_correction": "ComBat",
                "scaling": "ParetoNorm",
            },
            "combat": {
                "covariate_mode": "labels",
                "mean_only": True,
                "par_prior": False,
            },
            "groups": {"include": ["Tumor", "Normal"]},
            "analysis": {"pca": {"n_components": 4}},
            "output": {"suffix": "gui_phase1"},
        },
        require_required_sections=False,
    )

    applied_sections = window._apply_loaded_config(config, "memory://preset")

    assert window.pipeline_params["missing_thresh"] == 0.35
    assert window.pipeline_params["impute_method"] == "median"
    assert window.pipeline_params["filter_method"] == "mad"
    assert window.pipeline_params["filter_cutoff"] == 0.15
    assert window.pipeline_params["qc_rsd_enabled"] is True
    assert window.pipeline_params["qc_rsd_threshold"] == 0.30
    assert window.pipeline_params["row_norm"] == "MedianNorm"
    assert window.pipeline_params["transform"] == "LogNorm"
    assert window.pipeline_params["batch_correction"] == "ComBat"
    assert window.pipeline_params["scaling"] == "ParetoNorm"

    assert window.mv_tab.thresh_spin.value() == 0.35
    assert window.mv_tab.method_combo.currentData() == "median"
    assert window.filter_tab.method_combo.currentData() == "mad"
    assert window.filter_tab.auto_check.isChecked() is False
    assert window.filter_tab.cutoff_spin.value() == 0.15
    assert window.filter_tab.qc_check.isChecked() is True
    assert window.filter_tab.qc_thresh_spin.value() == 0.30
    assert window.norm_tab.row_combo.currentData() == "MedianNorm"
    assert window.norm_tab.trans_combo.currentData() == "LogNorm"
    assert window.norm_tab.batch_combo.currentData() == "ComBat"
    assert window.norm_tab.combat_mode_combo.currentData() == "labels"
    assert window.norm_tab.combat_mean_only_check.isChecked() is True
    assert window.norm_tab.combat_par_prior_check.isChecked() is False
    assert window.norm_tab.scale_combo.currentData() == "ParetoNorm"
    assert applied_sections[0] == "pipeline"
    assert "groups (stored for later phases)" in applied_sections
    assert "analysis (stored for later phases)" in applied_sections
    assert "output (stored for later phases)" in applied_sections
    assert "memory://preset" in window.statusBar().currentMessage()

    window.close()


def test_main_window_apply_loaded_config_only_reports_explicit_sections(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "missing_thresh": 0.4,
            }
        },
        require_required_sections=False,
    )

    applied_sections = window._apply_loaded_config(config, "memory://pipeline-only")

    assert applied_sections == ["pipeline"]

    window.close()
