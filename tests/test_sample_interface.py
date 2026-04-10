import pandas as pd
import pytest


pytestmark = pytest.mark.pr_smoke


def _make_matrix_df():
    return pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "100.1/1.1", "200.2/2.2"],
            "Breast_Cancer_Tissue_pooled_QC_1": ["QC", 1.0, 2.0],
            "TumorBC2286_DNAandRNA": ["Exposure", 3.0, 4.0],
            "NormalBC2257_DNA": ["Normal", 5.0, 6.0],
            "is_Presence_Absence_Marker": ["is_Presence_Absence_Marker", True, False],
            "Original_CV%": [None, 10.0, 20.0],
            "QC_CV%": [None, 11.0, 22.0],
        }
    )


def _make_sample_info_df():
    return pd.DataFrame(
        {
            "Sample_Name": [
                "Breast Cancer Tissue_ pooled_QC_1 ",
                "Tumor tissue BC2286 DNA +RNA",
                "Normal tissue BC2257 DNA",
            ],
            "Sample_Type": ["QC", "Exposure", "Normal"],
            "Batch": ["A;B", "A", "B"],
        }
    )


def _make_dnp_overlap_matrix_df():
    columns = {"FeatureID": ["Sample_Type", "100.1/1.1"]}
    sample_info_rows = []

    columns["Breast_Cancer_Tissue_pooled_QC_1"] = ["QC", 1.0]
    sample_info_rows.append(("Breast Cancer Tissue_ pooled_QC_1", "QC", "A;B"))
    columns["Breast_Cancer_Tissue_pooled_QC_2"] = ["QC", 1.0]
    sample_info_rows.append(("Breast Cancer Tissue_ pooled_QC_2", "QC", "B;C"))

    for idx in range(1, 31):
        name = f"Exposure_A_{idx}"
        columns[name] = ["Exposure", float(idx)]
        sample_info_rows.append((name, "Exposure", "A"))

    for idx in range(1, 32):
        name = f"Normal_B_{idx}"
        columns[name] = ["Normal", float(idx)]
        sample_info_rows.append((name, "Normal", "B"))

    for idx in range(1, 23):
        name = f"Control_C_{idx}"
        columns[name] = ["Control", float(idx)]
        sample_info_rows.append((name, "Control", "C"))

    matrix_df = pd.DataFrame(columns)
    sample_info = pd.DataFrame(sample_info_rows, columns=["Sample_Name", "Sample_Type", "Batch"])
    return matrix_df, sample_info


def test_build_sample_interface_exposes_required_outputs():
    from core.sample_interface import build_sample_interface

    result = build_sample_interface(_make_matrix_df(), _make_sample_info_df())

    assert result.matched_sample_columns == [
        "Breast_Cancer_Tissue_pooled_QC_1",
        "TumorBC2286_DNAandRNA",
        "NormalBC2257_DNA",
    ]
    assert hasattr(result, "unmatched_matrix_columns")
    assert hasattr(result, "unmatched_sample_info_rows")
    assert hasattr(result, "normalized_sample_types")
    assert hasattr(result, "batch_membership")
    assert hasattr(result, "batch_to_samples")
    assert hasattr(result, "batch_to_qc_samples")


def test_normalize_sample_name_matches_cross_tool_formatting():
    from core.sample_interface import normalize_sample_name

    assert normalize_sample_name("Breast Cancer Tissue_ pooled_QC_1") == normalize_sample_name(
        "Breast_Cancer_Tissue_pooled_QC_1"
    )
    assert normalize_sample_name("Tumor tissue BC2286 DNA +RNA") == normalize_sample_name(
        "TumorBC2286_DNAandRNA"
    )


def test_identify_sample_columns_excludes_summary_and_metadata_columns():
    from core.sample_interface import identify_sample_columns

    sample_columns = identify_sample_columns(_make_matrix_df())

    assert sample_columns == [
        "Breast_Cancer_Tissue_pooled_QC_1",
        "TumorBC2286_DNAandRNA",
        "NormalBC2257_DNA",
    ]


def test_parse_batch_labels_normalizes_semicolon_formatting():
    from core.sample_interface import parse_batch_labels

    assert parse_batch_labels("A") == ("A",)
    assert parse_batch_labels("A;B") == ("A", "B")
    assert parse_batch_labels("A; B") == ("A", "B")
    assert parse_batch_labels(" A ; B ") == ("A", "B")


def test_normalize_sample_type_applies_project_aliases():
    from core.sample_interface import normalize_sample_type

    assert normalize_sample_type("QC") == "QC"
    assert normalize_sample_type("Benign", {"Benign": "Control"}) == "Control"
    assert normalize_sample_type("benignfat", {"benignfat": "Control"}) == "Control"


def test_build_sample_interface_maps_qc_to_multiple_batches():
    from core.sample_interface import build_sample_interface

    result = build_sample_interface(_make_matrix_df(), _make_sample_info_df())

    assert result.batch_membership["Breast_Cancer_Tissue_pooled_QC_1"] == ("A", "B")
    assert result.batch_to_qc_samples["A"] == ["Breast_Cancer_Tissue_pooled_QC_1"]
    assert result.batch_to_qc_samples["B"] == ["Breast_Cancer_Tissue_pooled_QC_1"]


def test_build_sample_interface_applies_sample_type_aliases():
    from core.sample_interface import build_sample_interface

    sample_info = _make_sample_info_df()
    sample_info.loc[2, "Sample_Type"] = "Benign"

    result = build_sample_interface(
        _make_matrix_df(),
        sample_info,
        sample_type_aliases={"Benign": "Control"},
    )

    assert result.normalized_sample_types["NormalBC2257_DNA"] == "Control"


def test_build_sample_interface_rejects_non_qc_multi_batch_assignment():
    from core.sample_interface import build_sample_interface

    sample_info = _make_sample_info_df()
    sample_info.loc[1, "Batch"] = "A;B"

    try:
        build_sample_interface(_make_matrix_df(), sample_info)
    except ValueError as exc:
        assert "non-QC" in str(exc)
    else:
        raise AssertionError("Expected non-QC multi-batch assignment to raise")


def test_build_sample_interface_reports_dnp_style_batch_membership_counts():
    from core.sample_interface import build_sample_interface

    matrix_df, sample_info = _make_dnp_overlap_matrix_df()

    result = build_sample_interface(matrix_df, sample_info)

    assert len(result.matched_sample_columns) == 85
    assert len(result.batch_to_samples["A"]) == 31
    assert len(result.batch_to_samples["B"]) == 33
    assert len(result.batch_to_samples["C"]) == 23


def test_build_sample_interface_rejects_duplicate_normalized_sample_info_names():
    from core.sample_interface import build_sample_interface

    sample_info = pd.DataFrame(
        {
            "Sample_Name": [
                "Breast Cancer Tissue_ pooled_QC_1",
                "Breast_Cancer_Tissue_pooled_QC_1",
            ],
            "Sample_Type": ["QC", "QC"],
            "Batch": ["A", "A"],
        }
    )

    try:
        build_sample_interface(_make_matrix_df(), sample_info)
    except ValueError as exc:
        assert "Duplicate SampleInfo sample names" in str(exc)
    else:
        raise AssertionError("Expected duplicate normalized SampleInfo names to raise")


def test_build_sample_interface_rejects_duplicate_normalized_matrix_columns():
    from core.sample_interface import build_sample_interface

    matrix_df = pd.DataFrame(
        {
            "FeatureID": ["Sample_Type", "100.1/1.1"],
            "Breast_Cancer_Tissue_pooled_QC_1": ["QC", 1.0],
            "Breast Cancer Tissue pooled QC 1": ["QC", 1.5],
        }
    )

    try:
        build_sample_interface(matrix_df, _make_sample_info_df())
    except ValueError as exc:
        assert "Ambiguous matrix sample columns" in str(exc)
    else:
        raise AssertionError("Expected duplicate normalized matrix columns to raise")
