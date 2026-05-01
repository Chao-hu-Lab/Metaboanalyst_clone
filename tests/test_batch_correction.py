from __future__ import annotations

import pandas as pd
import pandas.testing as pdt
import pytest


def test_build_combat_design_aligns_sample_info_and_condition_covariate() -> None:
    from core.batch_correction import build_combat_design

    sample_ids = pd.Index(["TumorBC1_DNA", "NormalBC1_DNA", "TumorBC2_DNA"])
    sample_info = pd.DataFrame(
        {
            "Sample_Name": [
                "Tumor tissue BC1 DNA",
                "Normal tissue BC1 DNA",
                "Tumor tissue BC2 DNA",
            ],
            "Sample_Type": ["Tumor", "Normal", "Tumor"],
            "Batch": ["A", "A", "B"],
        }
    )
    labels = pd.Series(
        ["Tumor", "Normal", "Tumor"],
        index=sample_ids,
    )

    batch_labels, covariates, meta = build_combat_design(
        sample_ids,
        sample_info,
        labels=labels,
    )

    assert list(batch_labels.index) == list(sample_ids)
    assert list(batch_labels.values) == ["A", "A", "B"]
    assert covariates is not None
    assert list(covariates.columns) == ["Condition"]
    assert list(covariates.index) == list(sample_ids)
    assert list(covariates["Condition"].values) == ["Tumor", "Normal", "Tumor"]
    assert list(covariates["Condition"].cat.categories) == ["Normal", "Tumor"]
    assert meta["batch_source"] == "SampleInfo.Batch"
    assert meta["covariate_columns"] == ["Condition"]
    assert meta["covariate_reference_levels"] == {"Condition": ["Normal"]}


def test_build_combat_design_rejects_multi_batch_sample_assignment() -> None:
    from core.batch_correction import build_combat_design

    sample_ids = pd.Index(["QC_1", "S1"])
    sample_info = pd.DataFrame(
        {
            "Sample_Name": ["QC_1", "S1"],
            "Sample_Type": ["QC", "Tumor"],
            "Batch": ["A;B", "A"],
        }
    )

    with pytest.raises(ValueError, match="exactly one batch"):
        build_combat_design(sample_ids, sample_info)


def test_build_combat_design_rejects_single_batch_with_config_guidance() -> None:
    from core.batch_correction import build_combat_design

    sample_ids = pd.Index(["S1", "S2", "S3"])
    sample_info = pd.DataFrame(
        {
            "Sample_Name": sample_ids,
            "Batch": ["A", "A", "A"],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        build_combat_design(sample_ids, sample_info)

    message = str(exc_info.value)
    assert "at least two distinct batches in SampleInfo.Batch" in message
    assert "pipeline.batch_correction" in message


def test_apply_batch_correction_transposes_matrix_and_restores_shape(monkeypatch) -> None:
    from core.batch_correction import apply_batch_correction

    captured: dict[str, object] = {}

    def _fake_pycombat_norm(
        counts,
        batch,
        covar_mod=None,
        par_prior=True,
        prior_plots=False,
        mean_only=False,
        ref_batch=None,
        **_kwargs,
    ):
        captured["counts"] = counts.copy()
        captured["batch"] = list(batch)
        captured["covar_mod"] = None if covar_mod is None else covar_mod.copy()
        captured["par_prior"] = par_prior
        captured["mean_only"] = mean_only
        captured["ref_batch"] = ref_batch
        return counts + 10.0

    monkeypatch.setattr("core.batch_correction._load_pycombat_norm", lambda: _fake_pycombat_norm)

    df = pd.DataFrame(
        {
            "F1": [1.0, 2.0, 3.0],
            "F2": [4.0, 5.0, 6.0],
        },
        index=["S1", "S2", "S3"],
    )
    batch_labels = pd.Series(["A", "A", "B"], index=df.index)
    covariates = pd.DataFrame({"Condition": ["Tumor", "Normal", "Tumor"]}, index=df.index)

    corrected = apply_batch_correction(
        df,
        method="ComBat",
        batch_labels=batch_labels,
        covariates=covariates,
        par_prior=False,
        mean_only=True,
        ref_batch="A",
    )

    pdt.assert_frame_equal(
        captured["counts"],
        df.T,
        check_dtype=False,
    )
    assert captured["batch"] == ["A", "A", "B"]
    pdt.assert_frame_equal(captured["covar_mod"], covariates, check_dtype=False)
    assert captured["par_prior"] is False
    assert captured["mean_only"] is True
    assert captured["ref_batch"] == "A"
    pdt.assert_frame_equal(corrected, df + 10.0, check_dtype=False)


def test_apply_batch_correction_uses_numeric_dtype_fast_path(monkeypatch) -> None:
    import core.batch_correction as batch_correction

    def _fake_pycombat_norm(counts, batch, **_kwargs):
        return counts + 1.0

    def _fail_to_numeric(*_args, **_kwargs):
        raise AssertionError("pd.to_numeric should not be called for numeric matrices")

    monkeypatch.setattr(batch_correction, "_load_pycombat_norm", lambda: _fake_pycombat_norm)
    monkeypatch.setattr(batch_correction.pd, "to_numeric", _fail_to_numeric)

    df = pd.DataFrame(
        {
            "F1": [1.0, 2.0, 3.0],
            "F2": [4.0, 5.0, 6.0],
        },
        index=["S1", "S2", "S3"],
    )
    batch_labels = pd.Series(["A", "A", "B"], index=df.index)

    corrected = batch_correction.apply_batch_correction(
        df,
        method="ComBat",
        batch_labels=batch_labels,
    )

    pdt.assert_frame_equal(corrected, df + 1.0, check_dtype=False)


def test_identify_combat_sample_info_covariates_filters_reserved_and_continuous_columns() -> None:
    from core.batch_correction import identify_combat_sample_info_covariates

    sample_info = pd.DataFrame(
        {
            "Sample_Name": ["S1", "S2", "S3", "S4"],
            "Batch": ["A", "A", "B", "B"],
            "Sample_Type": ["Tumor", "Tumor", "Normal", "Normal"],
            "Sex": ["F", "M", "F", "M"],
            "Injection_Order": [1, 2, 3, 4],
            "DNA_mg/20uL": [1.2, 1.8, 2.1, 2.9],
        }
    )

    candidates, rejected = identify_combat_sample_info_covariates(sample_info)

    assert candidates == ["Sample_Type", "Sex"]
    assert "Sample_Name" in rejected
    assert "Batch" in rejected
    assert "Injection_Order" in rejected
    assert "DNA_mg/20uL" in rejected


def test_evaluate_combat_design_blocks_perfect_confounding() -> None:
    from core.batch_correction import evaluate_combat_design

    batch_labels = pd.Series(["A", "A", "B", "B"], index=["S1", "S2", "S3", "S4"])
    covariates = pd.DataFrame(
        {"Current labels": ["Tumor", "Tumor", "Normal", "Normal"]},
        index=batch_labels.index,
    )

    report = evaluate_combat_design(batch_labels, covariates)

    assert report["blocking_errors"] == [
        "Current sample labels are perfectly confounded with Batch. "
        "ComBat cannot safely run because labels and batches are indistinguishable."
    ]
    assert any("Small batches detected for ComBat" in warning for warning in report["warnings"])
    assert report["covariates"]["Current labels"]["perfectly_confounded"] is True
    assert report["covariates"]["Current labels"]["association"]["method"] == "fisher_exact"


def test_evaluate_combat_design_warns_on_small_batches_and_overlap() -> None:
    from core.batch_correction import evaluate_combat_design

    batch_labels = pd.Series(
        ["A"] * 7 + ["B"] * 7,
        index=[f"S{i}" for i in range(1, 15)],
    )
    covariates = pd.DataFrame(
        {
            "Sample_Type": [
                "Tumor",
                "Tumor",
                "Tumor",
                "Tumor",
                "Tumor",
                "Tumor",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Normal",
                "Tumor",
            ]
        },
        index=batch_labels.index,
    )

    report = evaluate_combat_design(batch_labels, covariates)

    assert report["blocking_errors"] == []
    assert any("strong overlap" in warning for warning in report["warnings"])
    assert report["covariates"]["Sample_Type"]["association"]["method"] == "fisher_exact"
    assert report["covariates"]["Sample_Type"]["association"]["p_value"] is not None
    assert report["covariates"]["Sample_Type"]["association"]["cramers_v"] is not None


def test_evaluate_batch_covariate_association_reports_correct_fisher_phi() -> None:
    from core.batch_correction import _evaluate_batch_covariate_association

    table = pd.DataFrame(
        [[1, 9], [8, 2]],
        index=["A", "B"],
        columns=["Tumor", "Normal"],
    )

    association = _evaluate_batch_covariate_association(table)

    assert association["method"] == "fisher_exact"
    assert association["statistic"] == pytest.approx(association["cramers_v"])
    assert 0.0 <= association["statistic"] <= 1.0


def test_build_combat_design_prioritizes_single_batch_covariate_levels_as_baseline() -> None:
    from core.batch_correction import build_combat_design

    sample_ids = pd.Index(
        [
            "QC_A",
            "Tumor_A",
            "Normal_A",
            "Tumor_B",
            "Normal_B",
            "Control_A",
        ]
    )
    sample_info = pd.DataFrame(
        {
            "Sample_Name": sample_ids,
            "Sample_Type": ["QC", "Tumor", "Normal", "Tumor", "Normal", "Control"],
            "Batch": ["A", "A", "A", "B", "B", "A"],
        }
    )

    _, covariates, meta = build_combat_design(
        sample_ids,
        sample_info,
        covariate_columns=["Sample_Type"],
    )

    assert covariates is not None
    assert list(covariates["Sample_Type"].cat.categories) == [
        "Control",
        "QC",
        "Tumor",
        "Normal",
    ]
    assert meta["covariate_reference_levels"] == {"Sample_Type": ["Control", "QC"]}
