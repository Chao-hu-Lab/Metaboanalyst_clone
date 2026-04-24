"""GUI preset manager integration tests for Phase 3."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import pytest
import yaml
from PySide6.QtCore import Qt

from core.app_config import load_yaml_config
from gui.main_window import MainWindow

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


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


def _combat_sample_info() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Sample_Name": ["S1", "S2"],
            "Sample_Type": ["Case", "Control"],
            "Batch": ["A", "B"],
            "Sex": ["F", "M"],
        }
    )


def _flatten_menu_texts(actions: Iterable) -> list[str]:
    texts: list[str] = []
    for action in actions:
        text = action.text()
        if text:
            texts.append(text)
        menu = action.menu()
        if menu is not None:
            texts.extend(_flatten_menu_texts(menu.actions()))
    return texts


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
                "batch_correction": "None",
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
    window.norm_tab.batch_combo.setCurrentIndex(window.norm_tab.batch_combo.findData("ComBat"))
    qapp.processEvents()
    window._save_preset_to_path(save_path)

    reloaded = load_yaml_config(save_path, require_required_sections=False)

    assert reloaded.pipeline.missing_thresh == 0.40
    assert reloaded.pipeline.batch_correction == "ComBat"
    assert reloaded.groups["include"] == ["Tumor", "Normal"]
    assert window.preset_bar.state_value_label.text() == "Local Preset"
    assert window.preset_bar.source_value_label.text().endswith("saved_preset.yaml")

    window.close()


def test_main_window_preset_round_trip_preserves_combat_sample_info_covariates(
    tmp_path: Path,
    qapp,
) -> None:
    window = MainWindow()
    matrix = _sample_matrix()
    window.set_data(
        matrix,
        _sample_labels(matrix),
        sample_col="Sample",
        group_col="Group",
        sample_info=_combat_sample_info(),
    )
    save_path = tmp_path / "combat_preset.yaml"

    window.norm_tab.batch_combo.setCurrentIndex(window.norm_tab.batch_combo.findData("ComBat"))
    window.norm_tab.combat_mode_combo.setCurrentIndex(
        window.norm_tab.combat_mode_combo.findData("sample_info")
    )
    for i in range(window.norm_tab.combat_covariate_list.count()):
        item = window.norm_tab.combat_covariate_list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) == "Sex":
            item.setCheckState(Qt.CheckState.Checked)
    window.norm_tab.combat_mean_only_check.setChecked(True)
    qapp.processEvents()

    window._save_preset_to_path(save_path)
    reloaded = load_yaml_config(save_path, require_required_sections=False)

    assert reloaded.pipeline.batch_correction == "ComBat"
    assert reloaded.combat["covariate_mode"] == "sample_info"
    assert reloaded.combat["sample_info_covariates"] == ["Sex"]
    assert reloaded.combat["mean_only"] is True

    window.close()


def test_main_window_load_menu_lists_whitelisted_builtin_and_local_presets_only(
    tmp_path: Path,
    monkeypatch,
    qapp,
) -> None:
    app_data_dir = tmp_path / "appdata"
    local_preset_dir = app_data_dir / "presets"
    local_preset_dir.mkdir(parents=True)
    local_preset_path = local_preset_dir / "team-default.yaml"
    local_preset_path.write_text(
        yaml.safe_dump({"pipeline": {"missing_thresh": 0.45}}, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("core.app_config.get_app_data_dir", lambda: app_data_dir)

    window = MainWindow()

    menu_texts = _flatten_menu_texts(window._preset_load_menu.actions())

    assert "Tissue KNN RSD 50% Marker Verify" in menu_texts
    assert "team-default" in menu_texts
    assert "tradition_default_mzmine" not in menu_texts

    window.close()


def test_main_window_loading_builtin_preset_marks_builtin_state(qapp) -> None:
    window = MainWindow()
    preset = next(
        preset
        for preset in window._builtin_preset_refs
        if preset.preset_id == "tissue_knn_rsd050_marker_verify"
    )

    window._load_preset_reference(preset)

    assert window.preset_bar.state_value_label.text() == "Built-in Preset"
    assert window.preset_bar.source_value_label.text() == "builtin://tissue_knn_rsd050_marker_verify"
    assert window.mv_tab.method_combo.currentData() == "knn"
    assert window.stats_tab.vol_test.currentData() == "welch"

    window.close()


def test_plain_cols_auto_mapping_matches_cli_group_inference(tmp_path: Path, qapp) -> None:
    window = MainWindow()
    csv_path = tmp_path / "plain_cols.csv"
    pd.DataFrame(
        {
            "FeatureID": ["100.1/1.1", "200.2/2.2"],
            "Tumor_A": [1.0, 3.0],
            "Normal_B": [2.0, 4.0],
            "Original_CV%": [10.0, 20.0],
        }
    ).to_csv(csv_path, index=False)

    cols_index = window.import_tab.orientation_combo.findData("cols")
    window.import_tab.orientation_combo.setCurrentIndex(cols_index)
    window.import_tab._load_file_for_preview(str(csv_path), auto_load=False)
    window.import_tab._load_into_main()

    assert window.labels is not None
    assert window.labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
    assert window.import_tab.get_run_input_state() == {
        "input": {"file": str(csv_path), "format": "plain"}
    }

    window.close()
