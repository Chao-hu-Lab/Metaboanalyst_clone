from pathlib import Path

import pandas as pd
import pytest

from core.input_resolver import read_input_table, resolve_primary_sheet_name_from_names
from scripts.run_from_config import (
    _annotate_feature_table,
    _export_significant_features_excel,
    load_data,
    resolve_top_vip,
)

pytestmark = [pytest.mark.integration, pytest.mark.pr_smoke]


def _write_excel_with_sample_info(
    path: Path,
    matrix_df: pd.DataFrame,
    sample_info_df: pd.DataFrame | None,
    *,
    sheet_name: str = "Sheet1",
) -> None:
    with pd.ExcelWriter(path) as writer:
        matrix_df.to_excel(writer, sheet_name=sheet_name, index=False)
        if sample_info_df is not None:
            sample_info_df.to_excel(writer, sheet_name="SampleInfo", index=False)


def _sample_info(sample_names: list[str], sample_types: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Sample_Name": sample_names,
            "Sample_Type": sample_types,
            "Batch": ["B1" if sample_type != "QC" else "B1;B2" for sample_type in sample_types],
        }
    )


def test_load_data_accepts_featureid_column_for_sample_type_row(tmp_path: Path):
    xlsx_path = tmp_path / "test_featureid_input.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
            "Sample_A": ["Exposure", 1.0, 3.0],
            "Sample_B": ["Normal", 2.0, 4.0],
            "Original_CV%": [None, 10.0, 20.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Sample_A", "Sample_B"], ["Exposure", "Normal"]),
    )

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "sample_type_row",
            }
        }
    )

    assert list(data.index) == ["Sample_A", "Sample_B"]
    assert list(data.columns) == ["100.1/1.1", "200.2/2.2"]
    assert labels.to_dict() == {"Sample_A": "Exposure", "Sample_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_resolve_top_vip_respects_configured_value() -> None:
    assert resolve_top_vip({"top_vip": 5}) == 5
    assert resolve_top_vip({}) == 15
    assert resolve_top_vip({"top_vip": 0}) == 1


def test_load_data_sample_type_row_excludes_non_sample_columns_even_if_labeled(
    tmp_path: Path,
):
    xlsx_path = tmp_path / "test_sample_type_row_non_sample_cols.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
            "Sample_A": ["Exposure", 1.0, 3.0],
            "Sample_B": ["Normal", 2.0, 4.0],
            "Original_CV%": ["Control", 10.0, 20.0],
            "QC_CV%": ["QC", 11.0, 21.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Sample_A", "Sample_B"], ["Exposure", "Normal"]),
    )

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "sample_type_row",
            }
        }
    )

    assert list(data.index) == ["Sample_A", "Sample_B"]
    assert labels.to_dict() == {"Sample_A": "Exposure", "Sample_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_sample_type_row_preserves_step4_metadata(tmp_path: Path):
    xlsx_path = tmp_path / "test_step4_metadata.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "F_marker", "F_regular"],
            "QC_1": ["QC", 0.0, 1.2],
            "Sample_A": ["Exposure", 10.0, 3.0],
            "Sample_B": ["Normal", 0.0, 4.0],
            "Original_CV%": ["Control", 10.0, 20.0],
            "exposure_ratio": ["Control", "0.10", "0.95"],
            "normal_ratio": ["Control", "0.00", "1.00"],
            "QC_ratio": ["QC", "1.00", "1.00"],
            "is_Presence_Absence_Marker": ["is_Presence_Absence_Marker", "TRUE", "0.0"],
            "Feature_Filter_Keep_Reasons": [
                "Feature_Filter_Keep_Reasons",
                "stable|mnar",
                "stable",
            ],
            "Imputation_Tag_Reasons": [
                "Imputation_Tag_Reasons",
                "low_overall_detection",
                "",
            ],
            "Detection_Profile": ["Detection_Profile", "legacy_marker", "legacy_regular"],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["QC_1", "Sample_A", "Sample_B"], ["QC", "Exposure", "Normal"]),
    )

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "sample_type_row",
            }
        }
    )

    assert list(data.index) == ["QC_1", "Sample_A", "Sample_B"]
    assert list(data.columns) == ["F_marker", "F_regular"]
    assert labels.to_dict() == {"QC_1": "QC", "Sample_A": "Exposure", "Sample_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [True, False]
    assert feature_metadata["Feature_Filter_Keep_Reasons"].tolist() == ["stable|mnar", "stable"]
    assert feature_metadata["Imputation_Tag_Reasons"].fillna("").tolist() == [
        "low_overall_detection",
        "",
    ]
    assert feature_metadata["Detection_Profile"].tolist() == ["legacy_marker", "legacy_regular"]
    assert feature_metadata["exposure_ratio"].tolist() == [0.10, 0.95]
    assert feature_metadata["normal_ratio"].tolist() == [0.00, 1.00]
    assert feature_metadata["QC_ratio"].tolist() == [1.00, 1.00]


def test_load_data_step4_metadata_requires_marker_column(tmp_path: Path):
    xlsx_path = tmp_path / "test_step4_missing_marker.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "F1"],
            "Sample_A": ["Exposure", 1.0],
            "Sample_B": ["Normal", 2.0],
            "Feature_Filter_Keep_Reasons": ["Feature_Filter_Keep_Reasons", "stable"],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Sample_A", "Sample_B"], ["Exposure", "Normal"]),
    )

    with pytest.raises(ValueError, match="is_Presence_Absence_Marker"):
        load_data(
            {
                "input": {
                    "file": str(xlsx_path),
                    "format": "sample_type_row",
                }
            }
        )


def test_load_data_rejects_invalid_presence_absence_marker(tmp_path: Path):
    xlsx_path = tmp_path / "test_step4_invalid_marker.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "F1"],
            "Sample_A": ["Exposure", 1.0],
            "Sample_B": ["Normal", 2.0],
            "is_Presence_Absence_Marker": ["is_Presence_Absence_Marker", "maybe"],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Sample_A", "Sample_B"], ["Exposure", "Normal"]),
    )

    with pytest.raises(ValueError, match="Invalid is_Presence_Absence_Marker"):
        load_data(
            {
                "input": {
                    "file": str(xlsx_path),
                    "format": "sample_type_row",
                }
            }
        )


def test_load_data_step4_reason_columns_are_optional(tmp_path: Path):
    xlsx_path = tmp_path / "test_step4_optional_reasons.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "F1"],
            "Sample_A": ["Exposure", 1.0],
            "Sample_B": ["Normal", 2.0],
            "exposure_ratio": ["Exposure", "1.0"],
            "is_Presence_Absence_Marker": ["is_Presence_Absence_Marker", "false"],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Sample_A", "Sample_B"], ["Exposure", "Normal"]),
    )

    _data, _labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "sample_type_row",
            }
        }
    )

    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False]
    assert "Feature_Filter_Keep_Reasons" not in feature_metadata.columns
    assert "Imputation_Tag_Reasons" not in feature_metadata.columns
    assert feature_metadata["exposure_ratio"].tolist() == [1.0]


def test_load_data_plain_excludes_summary_columns(tmp_path: Path):
    xlsx_path = tmp_path / "test_plain_non_sample_cols.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["100.1/1.1", "200.2/2.2"],
            "Tumor_A": [1.0, 3.0],
            "Normal_B": [2.0, 4.0],
            "Original_CV%": [10.0, 20.0],
            "QC_CV%": [11.0, 21.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Tumor_A", "Normal_B"], ["Tumor", "Normal"]),
    )

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
            }
        }
    )

    assert list(data.index) == ["Tumor_A", "Normal_B"]
    assert labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_plain_can_use_column_names_as_groups(tmp_path: Path):
    xlsx_path = tmp_path / "test_plain_column_name_groups.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["100.1/1.1", "200.2/2.2"],
            "control": [1.0, 3.0],
            "SBO_pre": [2.0, 4.0],
            "Original_CV%": [10.0, 20.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["control", "SBO_pre"], ["control", "SBO_pre"]),
    )

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
                "plain_label_mode": "column_names",
            }
        }
    )

    assert list(data.index) == ["control", "SBO_pre"]
    assert labels.to_dict() == {"control": "control", "SBO_pre": "SBO_pre"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_plain_extracts_presence_absence_marker_metadata(tmp_path: Path):
    xlsx_path = tmp_path / "test_plain_marker_metadata.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["100.1/1.1", "200.2/2.2", "300.3/3.3"],
            "Tumor_A": [1.0, 3.0, 0.0],
            "Normal_B": [2.0, 4.0, 0.0],
            "is_Presence_Absence_Marker": [
                False,
                True,
                False,
            ],
            "Original_CV%": [10.0, 20.0, 30.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["Tumor_A", "Normal_B"], ["Tumor", "Normal"]),
    )

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
            }
        }
    )

    assert list(data.index) == ["Tumor_A", "Normal_B"]
    assert labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
    assert feature_metadata.index.tolist() == ["100.1/1.1", "200.2/2.2", "300.3/3.3"]
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, True, False]


def test_annotate_feature_table_preserves_step4_metadata_columns():
    feature_metadata = pd.DataFrame(
        {
            "is_Presence_Absence_Marker": [True, False],
            "Feature_Filter_Keep_Reasons": ["mnar", "stable"],
            "exposure_ratio": [0.1, 1.0],
        },
        index=pd.Index(["F1", "F2"], name="Feature"),
    )
    stats_df = pd.DataFrame({"Feature": ["F2", "F1"], "pvalue": [0.2, 0.01]})

    annotated = _annotate_feature_table(stats_df, feature_metadata)

    assert annotated["is_Presence_Absence_Marker"].tolist() == [False, True]
    assert annotated["Feature_Filter_Keep_Reasons"].tolist() == ["stable", "mnar"]
    assert annotated["exposure_ratio"].tolist() == [1.0, 0.1]


def test_load_data_plain_excel_without_sample_info_falls_back_to_name_inference(tmp_path: Path):
    xlsx_path = tmp_path / "test_missing_sample_info.xlsx"
    pd.DataFrame(
        {
            "FeatureID": ["100.1/1.1", "200.2/2.2"],
            "Tumor_A": [1.0, 2.0],
            "Normal_B": [3.0, 4.0],
        }
    ).to_excel(xlsx_path, index=False)

    data, labels, feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
            }
        }
    )

    assert list(data.index) == ["Tumor_A", "Normal_B"]
    assert labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
    assert feature_metadata.index.tolist() == ["100.1/1.1", "200.2/2.2"]


def test_load_data_sample_type_row_excel_still_requires_sample_info(tmp_path: Path):
    xlsx_path = tmp_path / "test_missing_sample_info_sample_type_row.xlsx"
    pd.DataFrame(
        {
            "Mz/RT": ["Sample_Type", "100.1/1.1"],
            "TumorBC1_DNA": ["Exposure", 1.0],
            "NormalBC1_DNA": ["Normal", 2.0],
        }
    ).to_excel(xlsx_path, index=False)

    with pytest.raises(ValueError, match="SampleInfo sheet is required for Excel files with Sample_Type rows"):
        load_data(
            {
                "input": {
                    "file": str(xlsx_path),
                    "format": "plain",
                }
            }
        )


def test_load_data_prefers_sample_type_row_even_when_format_is_plain(tmp_path: Path):
    xlsx_path = tmp_path / "test_plain_with_sample_type.xlsx"
    df = pd.DataFrame(
        {
            "Mz/RT": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
            "TumorBC1_DNA": ["Exposure", 1.0, 2.0],
            "NormalBC1_DNA": ["Normal", 3.0, 4.0],
            "Original_CV%": [None, 10.0, 20.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(["TumorBC1_DNA", "NormalBC1_DNA"], ["Exposure", "Normal"]),
    )

    data, labels, _feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
            }
        }
    )

    assert list(data.index) == ["TumorBC1_DNA", "NormalBC1_DNA"]
    assert list(data.columns) == ["100.1/1.1", "200.2/2.2"]
    assert labels.to_dict() == {"TumorBC1_DNA": "Exposure", "NormalBC1_DNA": "Normal"}


def test_load_data_plain_keeps_dna_rna_variant_samples(tmp_path: Path):
    xlsx_path = tmp_path / "test_plain_variants.xlsx"
    df = pd.DataFrame(
        {
            "FeatureID": ["100.1/1.1", "200.2/2.2"],
            "TumorBC1_DNA": [1.0, 3.0],
            "TumorBC1_DNAandRNA": [2.0, 4.0],
            "NormalBC1_RNA": [5.0, 6.0],
            "Original_CV%": [10.0, 20.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(
            ["TumorBC1_DNA", "TumorBC1_DNAandRNA", "NormalBC1_RNA"],
            ["Tumor", "Tumor", "Normal"],
        ),
    )

    data, labels, _feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
            }
        }
    )

    assert list(data.index) == ["TumorBC1_DNA", "TumorBC1_DNAandRNA", "NormalBC1_RNA"]
    assert labels.to_dict() == {
        "TumorBC1_DNA": "Tumor",
        "TumorBC1_DNAandRNA": "Tumor",
        "NormalBC1_RNA": "Normal",
    }


def test_load_data_uses_sample_info_labels_when_sample_type_matches(tmp_path: Path):
    xlsx_path = tmp_path / "test_group_labels_preserved.xlsx"
    df = pd.DataFrame(
        {
            "Mz/RT": ["Sample_Type", "100.1/1.1"],
            "TumorBC1_DNA": ["Exposure", 1.0],
            "NormalBC1_DNA": ["Normal", 2.0],
            "BenignfatBC1_DNA": ["Control", 3.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(
            ["TumorBC1_DNA", "NormalBC1_DNA", "BenignfatBC1_DNA"],
            ["Exposure", "Normal", "Control"],
        ),
        sheet_name="PQN_Result",
    )

    _data, labels, _feature_metadata = load_data(
        {
            "input": {
                "file": str(xlsx_path),
                "format": "plain",
            },
        }
    )

    assert labels.to_dict() == {
        "TumorBC1_DNA": "Exposure",
        "NormalBC1_DNA": "Normal",
        "BenignfatBC1_DNA": "Control",
    }


def test_load_data_raises_when_sample_type_row_disagrees_with_sample_info(tmp_path: Path):
    xlsx_path = tmp_path / "test_group_labels_mismatch.xlsx"
    df = pd.DataFrame(
        {
            "Mz/RT": ["Sample_Type", "100.1/1.1"],
            "TumorBC1_DNA": ["Exposure", 1.0],
            "NormalBC1_DNA": ["Normal", 2.0],
            "BenignfatBC1_DNA": ["Control", 3.0],
        }
    )
    _write_excel_with_sample_info(
        xlsx_path,
        df,
        _sample_info(
            ["TumorBC1_DNA", "NormalBC1_DNA", "BenignfatBC1_DNA"],
            ["Exposure", "Normal", "Benign"],
        ),
        sheet_name="PQN_Result",
    )

    with pytest.raises(ValueError, match="Worksheet Sample_Type does not match SampleInfo.Sample_Type"):
        load_data(
            {
                "input": {
                    "file": str(xlsx_path),
                    "format": "plain",
                },
            }
        )


def test_resolve_primary_sheet_name_prefers_filename_hint_with_priority():
    resolved = resolve_primary_sheet_name_from_names(
        "demo_specnorm_export.xlsx",
        ["Overview", "PQN_Result", "SpecNorm_Result", "SampleInfo"],
    )

    assert resolved == "SpecNorm_Result"


def test_resolve_primary_sheet_name_prefers_final_dnp_batch_result():
    resolved = resolve_primary_sheet_name_from_names(
        "single_or_multi_batch_dnp_export.xlsx",
        [
            "Overview",
            "PQN_Result",
            "SpecNorm_PQN_Result",
            "QC_Batch_Scaling_result",
            "SampleInfo",
        ],
    )

    assert resolved == "QC_Batch_Scaling_result"


def test_resolve_primary_sheet_name_prefers_specnorm_pqn_when_batch_result_absent():
    resolved = resolve_primary_sheet_name_from_names(
        "single_batch_dnp_export.xlsx",
        ["Overview", "PQN_Result", "SpecNorm_PQN_Result", "SampleInfo"],
    )

    assert resolved == "SpecNorm_PQN_Result"


def test_resolve_primary_sheet_name_keeps_pqn_as_dnp_fallback():
    resolved = resolve_primary_sheet_name_from_names(
        "single_batch_dnp_export.xlsx",
        ["Overview", "PQN_Result", "SampleInfo"],
    )

    assert resolved == "PQN_Result"


def test_resolve_primary_sheet_name_keeps_legacy_batch_scaling_alias():
    resolved = resolve_primary_sheet_name_from_names(
        "legacy_batch_export.xlsx",
        ["Overview", "PQN_Result", "Batch_scaling", "SampleInfo"],
    )

    assert resolved == "Batch_scaling"


def test_read_input_table_loads_specnorm_pqn_sheet_without_fallback(tmp_path: Path):
    xlsx_path = tmp_path / "dnp_single_batch_specnorm_pqn.xlsx"
    overview_df = pd.DataFrame({"Status": ["not data"]})
    matrix_df = pd.DataFrame(
        {
            "Mz/RT": ["Sample_Type", "100.1/1.1"],
            "Sample_A": ["Exposure", 1.0],
            "Sample_B": ["Normal", 2.0],
        }
    )
    with pd.ExcelWriter(xlsx_path) as writer:
        overview_df.to_excel(writer, sheet_name="Overview", index=False)
        matrix_df.to_excel(writer, sheet_name="SpecNorm_PQN_Result", index=False)
        _sample_info(["Sample_A", "Sample_B"], ["Exposure", "Normal"]).to_excel(
            writer,
            sheet_name="SampleInfo",
            index=False,
        )

    loaded = read_input_table(str(xlsx_path))

    assert loaded.sheet_name == "SpecNorm_PQN_Result"
    assert list(loaded.table.columns) == ["Mz/RT", "Sample_A", "Sample_B"]


def test_summary_export_keeps_features_with_zero_significant_hits(tmp_path: Path):
    sheets = {
        "ANOVA_All": pd.DataFrame(
            {
                "Feature": ["F_keep", "F_zero"],
                "pvalue_adj": [0.01, 0.50],
                "pvalue": [0.01, 0.50],
                "neg_log10p": [2.0, 0.3],
                "is_Presence_Absence_Marker": [False, True],
            }
        ),
        "VIP_Tumor_vs_Normal": pd.DataFrame(
            {
                "Rank": [1, 2],
                "Feature": ["F_keep", "F_zero"],
                "VIP": [1.4, 0.2],
                "is_Presence_Absence_Marker": [False, True],
            }
        ),
    }

    _export_significant_features_excel(sheets, str(tmp_path), top_n=None)

    summary_df = pd.read_csv(tmp_path / "Summary.csv")

    assert summary_df["Feature"].tolist() == ["F_keep", "F_zero"]
    assert summary_df["Passed_in_N_analyses"].tolist() == [2, 0]
    assert summary_df["is_Presence_Absence_Marker"].tolist() == [False, True]
