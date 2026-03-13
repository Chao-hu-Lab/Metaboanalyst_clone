import os
import tempfile

import pandas as pd

from scripts.run_from_config import load_data


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

        data, labels = load_data(
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

        data, labels = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "sample_type_row",
                }
            }
        )

    assert list(data.index) == ["Sample_A", "Sample_B"]
    assert labels.to_dict() == {"Sample_A": "Exposure", "Sample_B": "Normal"}


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

        data, labels = load_data(
            {
                "input": {
                    "file": xlsx_path,
                    "format": "plain",
                }
            }
        )

    assert list(data.index) == ["Tumor_A", "Normal_B"]
    assert labels.to_dict() == {"Tumor_A": "Tumor", "Normal_B": "Normal"}
