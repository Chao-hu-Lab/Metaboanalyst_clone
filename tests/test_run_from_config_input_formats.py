import os
import tempfile

import pandas as pd

from scripts.run_from_config import _export_significant_features_excel, load_data


def test_load_data_accepts_featureid_column_for_sample_type_row():
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "test_featureid_input.xlsx")
        df = pd.DataFrame(
            {
                "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
                "Sample_A": ["Exposure", 1.0, 3.0],
                "Sample_B": ["Normal", 2.0, 4.0],
                "Original_CV%": [None, 10.0, 20.0],
            }
        )
        df.to_excel(xlsx_path, index=False)

        data, labels, feature_metadata = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "sample_type_row",
                }
            }
        )

    assert list(data.index) == ["Sample_A", "Sample_B"]
    assert list(data.columns) == ["100.1/1.1", "200.2/2.2"]
    assert labels.to_dict() == {"Sample_A": "Exposure", "Sample_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_sample_type_row_excludes_non_sample_columns_even_if_labeled():
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "test_sample_type_row_non_sample_cols.xlsx")
        df = pd.DataFrame(
            {
                "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
                "Sample_A": ["Exposure", 1.0, 3.0],
                "Sample_B": ["Normal", 2.0, 4.0],
                "Original_CV%": ["Control", 10.0, 20.0],
                "QC_CV%": ["QC", 11.0, 21.0],
            }
        )
        df.to_excel(xlsx_path, index=False)

        data, labels, feature_metadata = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "sample_type_row",
                }
            }
        )

    assert list(data.index) == ["Sample_A", "Sample_B"]
    assert labels.to_dict() == {"Sample_A": "Exposure", "Sample_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_plain_excludes_summary_columns():
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "test_plain_non_sample_cols.xlsx")
        df = pd.DataFrame(
            {
                "FeatureID": ["100.1/1.1", "200.2/2.2"],
                "Tumor_A": [1.0, 3.0],
                "Normal_B": [2.0, 4.0],
                "Original_CV%": [10.0, 20.0],
                "QC_CV%": [11.0, 21.0],
            }
        )
        df.to_excel(xlsx_path, index=False)

        data, labels, feature_metadata = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "plain",
                }
            }
        )

    assert list(data.index) == ["Tumor_A", "Normal_B"]
    assert labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_plain_can_use_column_names_as_groups():
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "test_plain_column_name_groups.xlsx")
        df = pd.DataFrame(
            {
                "FeatureID": ["100.1/1.1", "200.2/2.2"],
                "control": [1.0, 3.0],
                "SBO_pre": [2.0, 4.0],
                "Original_CV%": [10.0, 20.0],
            }
        )
        df.to_excel(xlsx_path, index=False)

        data, labels, feature_metadata = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "plain",
                    "plain_label_mode": "column_names",
                }
            }
        )

    assert list(data.index) == ["control", "SBO_pre"]
    assert labels.to_dict() == {"control": "control", "SBO_pre": "SBO_pre"}
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, False]


def test_load_data_plain_extracts_presence_absence_marker_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "test_plain_marker_metadata.xlsx")
        df = pd.DataFrame(
            {
                "FeatureID": ["100.1/1.1", "200.2/2.2", "300.3/3.3"],
                "Tumor_A": [1.0, 3.0, 0.0],
                "Normal_B": [2.0, 4.0, 0.0],
                "is_Presence_Absence_Marker": [
                    "is_Presence_Absence_Marker",
                    True,
                    False,
                ],
                "Original_CV%": [10.0, 20.0, 30.0],
            }
        )
        df.to_excel(xlsx_path, index=False)

        data, labels, feature_metadata = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "plain",
                }
            }
        )

    assert list(data.index) == ["Tumor_A", "Normal_B"]
    assert labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
    assert feature_metadata.index.tolist() == ["100.1/1.1", "200.2/2.2", "300.3/3.3"]
    assert feature_metadata["is_Presence_Absence_Marker"].tolist() == [False, True, False]


def test_summary_export_keeps_features_with_zero_significant_hits():
    with tempfile.TemporaryDirectory() as tmpdir:
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

        _export_significant_features_excel(sheets, tmpdir, top_n=None)

        summary_df = pd.read_csv(os.path.join(tmpdir, "Summary.csv"))

    assert summary_df["Feature"].tolist() == ["F_keep", "F_zero"]
    assert summary_df["Passed_in_N_analyses"].tolist() == [2, 0]
    assert summary_df["is_Presence_Absence_Marker"].tolist() == [False, True]
