"""GUI preset manager integration tests for Phase 3."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.app_config import load_yaml_config
from gui.main_window import MainWindow


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


def test_main_window_load_preset_marks_pending_until_data_mapping_resolves(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "row_norm": "SpecNorm",
                "transform": "LogNorm",
            },
            "spec_norm": {
                "factor_column": "NormalizationFactor",
            },
        },
        require_required_sections=False,
    )

    window._load_preset_config(config, "C:/tmp/specnorm_preset.yaml")

    assert window.preset_bar.state_value_label.text() == "Pending Data Mapping"
    assert "spec_norm.factor_column" in window.preset_bar.summary_value_label.text()

    matrix = _sample_matrix()
    window.set_data(
        matrix,
        _sample_labels(matrix),
        sample_col="Sample",
        group_col="Group",
        sample_info=_sample_info(),
    )

    assert window.preset_bar.state_value_label.text() == "Local Preset"
    assert window.norm_tab.row_combo.currentData() == "SpecNorm"
    assert window.norm_tab.factor_combo.currentData() == "NormalizationFactor"

    window.close()


def test_main_window_preset_dirty_state_after_widget_change(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "missing_thresh": 0.35,
                "impute_method": "median",
            }
        },
        require_required_sections=False,
    )

    window._load_preset_config(config, "C:/tmp/local_preset.yaml")
    assert window.preset_bar.state_value_label.text() == "Local Preset"

    window.mv_tab.thresh_spin.setValue(0.40)
    qapp.processEvents()

    assert window.preset_bar.state_value_label.text() == "Modified"
    assert window.preset_bar.apply_button.isEnabled() is True

    window.close()


def test_main_window_apply_preset_restores_loaded_values(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "missing_thresh": 0.35,
                "impute_method": "median",
            }
        },
        require_required_sections=False,
    )

    window._load_preset_config(config, "C:/tmp/local_preset.yaml")
    window.mv_tab.thresh_spin.setValue(0.40)
    qapp.processEvents()

    window._apply_current_preset()

    assert window.mv_tab.thresh_spin.value() == 0.35
    assert window.mv_tab.method_combo.currentData() == "median"
    assert window.preset_bar.state_value_label.text() == "Local Preset"

    window.close()


def test_main_window_reset_to_defaults_marks_modified_against_loaded_preset(qapp) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "missing_thresh": 0.35,
            }
        },
        require_required_sections=False,
    )

    window._load_preset_config(config, "C:/tmp/local_preset.yaml")
    window._reset_preset_to_defaults()

    assert window.mv_tab.thresh_spin.value() == 0.5
    assert window.preset_bar.state_value_label.text() == "Modified"

    window.close()


def test_main_window_save_preset_to_path_round_trips_current_gui_state(
    tmp_path: Path,
    qapp,
) -> None:
    window = MainWindow()
    config = load_yaml_config(
        {
            "pipeline": {
                "missing_thresh": 0.35,
            },
            "groups": {
                "include": ["Tumor", "Normal"],
            },
            "legacy_bundle": {
                "note": "keep for ignored summary",
            },
        },
        require_required_sections=False,
    )
    save_path = tmp_path / "saved_preset.yaml"

    window._load_preset_config(config, "C:/tmp/local_preset.yaml")
    assert "legacy_bundle" in window.preset_bar.ignored_value_label.text()

    window.mv_tab.thresh_spin.setValue(0.40)
    qapp.processEvents()
    window._save_preset_to_path(save_path)

    reloaded = load_yaml_config(save_path, require_required_sections=False)

    assert reloaded.pipeline.missing_thresh == 0.40
    assert reloaded.groups["include"] == ["Tumor", "Normal"]
    assert window.preset_bar.state_value_label.text() == "Local Preset"
    assert window.preset_bar.source_value_label.text().endswith("saved_preset.yaml")

    window.close()
