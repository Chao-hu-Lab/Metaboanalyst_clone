"""GUI runtime-parity tests for feature metadata and SpecNorm context."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.feature_metadata import FEATURE_MARKER_COLUMN
from core.pipeline import MetaboAnalystPipeline
from gui.main_window import MainWindow
from scripts.run_from_config import load_data

pytestmark = [pytest.mark.gui, pytest.mark.integration, pytest.mark.pr_smoke]


def _make_column_oriented_raw_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "F_marker", "F_regular", "F_drop"],
            "QC_1": ["QC", 0.0, 1.0, 10.0],
            "QC_2": ["QC", 0.0, 1.1, 50.0],
            "S1": ["A", 10.0, 3.0, 20.0],
            "S2": ["B", 0.0, 4.0, 30.0],
            FEATURE_MARKER_COLUMN: [FEATURE_MARKER_COLUMN, True, False, False],
            "Original_CV%": [None, 10.0, 20.0, 30.0],
        }
    )


def _make_sample_info_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Sample_Name": ["QC_1", "QC_2", "S1", "S2"],
            "Sample_Type": ["QC", "QC", "A", "B"],
            "Batch": ["B1;B2", "B1;B2", "B1", "B1"],
            "DNA_ng": [1.0, 1.0, 2.0, 4.0],
        }
    )


def _set_combo_to_data(combo, value: str) -> None:
    index = combo.findData(value)
    if index < 0:
        raise AssertionError(f"Could not find combo item for {value!r}")
    combo.setCurrentIndex(index)


def _load_gui_column_dataset(
    window: MainWindow,
    raw_df: pd.DataFrame,
    *,
    sample_info: pd.DataFrame | None = None,
) -> None:
    import_tab = window.import_tab
    _set_combo_to_data(import_tab.orientation_combo, "cols")
    import_tab._raw_df = raw_df.copy()
    import_tab._sample_info_df = sample_info.copy() if sample_info is not None else None
    import_tab._populate_mapping_options()
    _set_combo_to_data(import_tab.sample_combo, "FeatureID")
    _set_combo_to_data(import_tab.group_combo, "Sample_Type")
    import_tab._load_into_main()


def _marker_aware_params() -> dict[str, object]:
    return {
        "missing_thresh": 1.0,
        "impute_method": "knn",
        "filter_method": "None",
        "filter_cutoff": None,
        "qc_rsd_enabled": True,
        "qc_rsd_threshold": 0.25,
        "row_norm": "None",
        "transform": "None",
        "scaling": "None",
    }


def test_gui_import_pipeline_retains_feature_metadata(qapp) -> None:
    window = MainWindow()
    _load_gui_column_dataset(window, _make_column_oriented_raw_df())

    assert window.raw_data is not None
    assert window.raw_data.index.tolist() == ["QC_1", "QC_2", "S1", "S2"]
    assert window.raw_data.columns.tolist() == ["F_marker", "F_regular", "F_drop"]
    assert window.raw_feature_metadata is not None
    assert window.raw_feature_metadata.index.tolist() == ["F_marker", "F_regular", "F_drop"]
    assert window.raw_feature_metadata[FEATURE_MARKER_COLUMN].tolist() == [True, False, False]

    window.set_pipeline_params(**_marker_aware_params())
    payload = window.run_pipeline_until("filter")

    assert payload["data"].index.tolist() == ["S1", "S2"]
    assert payload["data"].columns.tolist() == ["F_marker", "F_regular"]
    assert payload["feature_metadata"] is not None
    assert bool(payload["feature_metadata"].loc["F_marker", "qc_rsd_exempted"]) is True
    assert payload["feature_metadata"].loc["F_marker", "imputation_method"] == "min"
    assert payload["feature_metadata"].loc["F_regular", "imputation_method"] == "knn"

    window.close()


def test_gui_runtime_matches_cli_for_marker_aware_qc_rsd(tmp_path: Path, qapp) -> None:
    raw_df = _make_column_oriented_raw_df()
    xlsx_path = tmp_path / "gui_cli_runtime.xlsx"
    with pd.ExcelWriter(xlsx_path) as writer:
        raw_df.to_excel(writer, sheet_name="Sheet1", index=False)
        _make_sample_info_df().to_excel(writer, sheet_name="SampleInfo", index=False)

    cli_data, cli_labels, cli_feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "sample_type_row",
            }
        }
    )
    cli_pipeline = MetaboAnalystPipeline(cli_data, cli_labels, feature_metadata=cli_feature_metadata)
    cli_result = cli_pipeline.run_pipeline(**_marker_aware_params())

    window = MainWindow()
    _load_gui_column_dataset(window, raw_df)
    window.set_pipeline_params(**_marker_aware_params())
    gui_payload = window.run_pipeline_until("filter")

    pd.testing.assert_frame_equal(gui_payload["data"], cli_result, check_names=False)
    pd.testing.assert_series_equal(gui_payload["labels"], cli_pipeline.processed_labels, check_names=False)
    pd.testing.assert_frame_equal(
        gui_payload["feature_metadata"],
        cli_pipeline.processed_feature_metadata,
    )

    window.close()


def test_gui_specnorm_uses_loaded_sample_info_context(qapp) -> None:
    window = MainWindow()
    _load_gui_column_dataset(
        window,
        _make_column_oriented_raw_df(),
        sample_info=_make_sample_info_df(),
    )

    _set_combo_to_data(window.norm_tab.row_combo, "SpecNorm")
    window.norm_tab._on_row_method_changed()
    _set_combo_to_data(window.norm_tab.factor_combo, "DNA_ng")
    factors, meta = window.norm_tab._resolve_specnorm_factors()

    assert factors.to_dict() == {"QC_1": 1.0, "QC_2": 1.0, "S1": 2.0, "S2": 4.0}
    assert meta["factor_column"] == "DNA_ng"
    assert meta["sample_id_column"] == "Sample_Name"

    window.close()
