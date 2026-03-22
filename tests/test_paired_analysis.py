"""Tests for paired/unpaired analysis feature."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.sample_info import extract_subject_ids, align_paired_samples
from analysis.univariate import volcano_analysis


# ── Fixtures ──────────────────────────────────────────────


def _make_paired_dataset(n_subjects=10, n_features=20, seed=42):
    """Create a paired dataset with known structure."""
    rng = np.random.default_rng(seed)
    subjects = [f"BC{2257 + i}" for i in range(n_subjects)]

    tumor_names = [f"Tumor tissue {s}_DNA" for s in subjects]
    normal_names = [f"Normal tissue {s}_DNA" for s in subjects]
    control_names = [f"Benign fat BC{979 + i}_DNA" for i in range(6)]
    qc_names = ["Breast Cancer Tissue_ pooled_QC_1"]

    all_names = tumor_names + normal_names + control_names + qc_names
    all_labels = (
        ["Exposure"] * n_subjects
        + ["Normal"] * n_subjects
        + ["Control"] * 6
        + ["QC"] * 1
    )

    idx = pd.Index(all_names)
    labels = pd.Series(all_labels, index=idx)

    # Paired effect: tumor has higher values in first 3 features
    data = rng.standard_normal((len(all_names), n_features))
    data[:n_subjects, :3] += 3.0  # strong effect for first 3 features

    df = pd.DataFrame(data, index=idx, columns=[f"feat_{i}" for i in range(n_features)])
    return df, labels, subjects


# ── extract_subject_ids ───────────────────────────────────


class TestExtractSubjectIds:
    def test_basic_extraction(self):
        names = pd.Index([
            "Tumor tissue BC2257_DNA",
            "Normal tissue BC2258_DNA",
            "Benign fat BC0979_DNA",
        ])
        result = extract_subject_ids(names)
        assert result.tolist() == ["BC2257", "BC2258", "BC0979"]

    def test_special_characters_in_name(self):
        names = pd.Index([
            "Tumor tissue BC2286* DNA +RNA",
            "Tumor tissue BC2304_ DNA +RNA",
        ])
        result = extract_subject_ids(names)
        assert result.tolist() == ["BC2286", "BC2304"]

    def test_qc_samples_return_empty(self):
        names = pd.Index([
            "Breast Cancer Tissue_ pooled_QC_1",
            "Breast Cancer Tissue *pooled_QC_2",
        ])
        result = extract_subject_ids(names)
        assert result.tolist() == ["", ""]

    def test_custom_pattern(self):
        names = pd.Index(["Sample_P001_T", "Sample_P002_N"])
        result = extract_subject_ids(names, pattern=r"P\d+")
        assert result.tolist() == ["P001", "P002"]

    def test_capture_group_pattern(self):
        """When pattern has a capture group, use group(1)."""
        names = pd.Index(["Tumor tissue BC2257_DNA"])
        result = extract_subject_ids(names, pattern=r"(BC\d+)_DNA")
        assert result.tolist() == ["BC2257"]

    def test_no_match_returns_empty(self):
        names = pd.Index(["Unknown sample XYZ"])
        result = extract_subject_ids(names, pattern=r"BC\d+")
        assert result.tolist() == [""]

    def test_series_input(self):
        s = pd.Series(["Tumor tissue BC2257_DNA", "Normal tissue BC2258_DNA"])
        result = extract_subject_ids(s)
        assert len(result) == 2
        assert result.iloc[0] == "BC2257"


# ── align_paired_samples ─────────────────────────────────


class TestAlignPairedSamples:
    def test_basic_alignment(self):
        df, labels, subjects = _make_paired_dataset(n_subjects=5)
        pair_ids = extract_subject_ids(df.index)
        df1, df2, matched = align_paired_samples(
            df, labels, "Exposure", "Normal", pair_ids
        )
        assert len(matched) == 5
        assert df1.shape[0] == 5
        assert df2.shape[0] == 5
        # Verify same order
        sid1 = extract_subject_ids(df1.index)
        sid2 = extract_subject_ids(df2.index)
        assert sid1.tolist() == sid2.tolist()

    def test_partial_overlap(self):
        """Only subjects in both groups are matched."""
        names = pd.Index([
            "Tumor tissue BC2257_DNA",
            "Tumor tissue BC2258_DNA",
            "Tumor tissue BC2259_DNA",
            "Normal tissue BC2257_DNA",
            "Normal tissue BC2259_DNA",
        ])
        labels = pd.Series(
            ["Exposure", "Exposure", "Exposure", "Normal", "Normal"],
            index=names,
        )
        df = pd.DataFrame(
            np.ones((5, 2)), index=names, columns=["f1", "f2"]
        )
        pair_ids = extract_subject_ids(names)
        df1, df2, matched = align_paired_samples(
            df, labels, "Exposure", "Normal", pair_ids
        )
        # BC2258 is only in Exposure, so only 2 pairs
        assert len(matched) == 2
        assert "BC2257" in matched.tolist()
        assert "BC2259" in matched.tolist()

    def test_no_overlap_raises(self):
        names = pd.Index([
            "Tumor tissue BC2257_DNA",
            "Normal tissue BC9999_DNA",
        ])
        labels = pd.Series(["Exposure", "Normal"], index=names)
        df = pd.DataFrame(np.ones((2, 1)), index=names, columns=["f1"])
        pair_ids = extract_subject_ids(names)
        with pytest.raises(ValueError, match="No matched subjects"):
            align_paired_samples(df, labels, "Exposure", "Normal", pair_ids)

    def test_duplicate_subjects_uses_first(self):
        """When a subject has multiple samples, use the first."""
        names = pd.Index([
            "Tumor tissue BC2286_DNA",
            "Tumor tissue BC2286* DNA +RNA",
            "Normal tissue BC2286_DNA",
        ])
        labels = pd.Series(["Exposure", "Exposure", "Normal"], index=names)
        df = pd.DataFrame(
            [[1, 2], [3, 4], [5, 6]], index=names, columns=["f1", "f2"]
        )
        pair_ids = extract_subject_ids(names)
        df1, df2, matched = align_paired_samples(
            df, labels, "Exposure", "Normal", pair_ids
        )
        assert len(matched) == 1
        # First occurrence of BC2286 in Exposure group
        assert df1.iloc[0]["f1"] == 1  # BC2286_DNA, not BC2286* DNA+RNA


# ── volcano_analysis paired ──────────────────────────────


class TestVolcanoAnalysisPaired:
    def test_paired_returns_correct_metadata(self):
        df, labels, subjects = _make_paired_dataset()
        pair_ids = extract_subject_ids(df.index)
        result = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=True, pair_ids=pair_ids,
        )
        assert result.paired is True
        assert result.n_pairs == 10

    def test_unpaired_returns_correct_metadata(self):
        df, labels, _ = _make_paired_dataset()
        result = volcano_analysis(df, labels, "Exposure", "Control")
        assert result.paired is False
        assert result.n_pairs is None

    def test_paired_detects_strong_effect(self):
        df, labels, _ = _make_paired_dataset()
        pair_ids = extract_subject_ids(df.index)
        result = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=True, pair_ids=pair_ids,
            fc_thresh=1.5, p_thresh=0.05,
        )
        # First 3 features have strong paired effect
        sig_features = result.significant["Feature"].tolist()
        for f in ["feat_0", "feat_1", "feat_2"]:
            assert f in sig_features, f"{f} should be significant"

    def test_paired_without_pair_ids_raises(self):
        df, labels, _ = _make_paired_dataset()
        with pytest.raises(ValueError, match="pair_ids is required"):
            volcano_analysis(
                df, labels, "Exposure", "Normal",
                paired=True, pair_ids=None,
            )

    def test_paired_vs_unpaired_pvalues_differ(self):
        """Paired test should give different p-values than unpaired."""
        df, labels, _ = _make_paired_dataset()
        pair_ids = extract_subject_ids(df.index)

        r_paired = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=True, pair_ids=pair_ids, use_fdr=False,
        )
        r_unpaired = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=False, use_fdr=False,
        )
        # p-values should differ (paired test accounts for within-subject variance)
        p_paired = r_paired.result_df["pvalue"].values
        p_unpaired = r_unpaired.result_df["pvalue"].values
        assert not np.allclose(p_paired, p_unpaired)

    def test_paired_nonpar(self):
        """Paired non-parametric uses Wilcoxon signed-rank."""
        df, labels, _ = _make_paired_dataset()
        pair_ids = extract_subject_ids(df.index)
        result = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=True, pair_ids=pair_ids,
            nonpar=True, fc_thresh=1.5,
        )
        assert result.paired is True
        assert result.n_significant >= 1  # strong effect should be detected

    def test_fold_change_same_for_paired_and_unpaired(self):
        """FC uses group means regardless of pairing."""
        df, labels, _ = _make_paired_dataset()
        pair_ids = extract_subject_ids(df.index)

        r_paired = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=True, pair_ids=pair_ids,
        )
        r_unpaired = volcano_analysis(
            df, labels, "Exposure", "Normal",
            paired=False,
        )
        np.testing.assert_array_almost_equal(
            r_paired.result_df["log2FC"].values,
            r_unpaired.result_df["log2FC"].values,
        )


# ── parse_pair_config ─────────────────────────────────────


class TestParsePairConfig:
    def test_old_format(self):
        from scripts.run_from_config import parse_pair_config

        old = [["Exposure", "Normal"], ["Exposure", "Control"]]
        result = parse_pair_config(old)
        assert result == [
            ("Exposure", "Normal", False),
            ("Exposure", "Control", False),
        ]

    def test_new_format(self):
        from scripts.run_from_config import parse_pair_config

        new = [
            {"groups": ["Exposure", "Normal"], "paired": True},
            {"groups": ["Exposure", "Control"], "paired": False},
        ]
        result = parse_pair_config(new)
        assert result == [
            ("Exposure", "Normal", True),
            ("Exposure", "Control", False),
        ]

    def test_new_format_default_unpaired(self):
        from scripts.run_from_config import parse_pair_config

        entry = [{"groups": ["Normal", "Control"]}]
        result = parse_pair_config(entry)
        assert result == [("Normal", "Control", False)]

    def test_mixed_format(self):
        from scripts.run_from_config import parse_pair_config

        mixed = [
            {"groups": ["Exposure", "Normal"], "paired": True},
            ["Exposure", "Control"],
        ]
        result = parse_pair_config(mixed)
        assert result == [
            ("Exposure", "Normal", True),
            ("Exposure", "Control", False),
        ]
