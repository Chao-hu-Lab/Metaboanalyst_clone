"""Batch correction utilities for the preprocessing pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy.stats import chi2_contingency, fisher_exact

from core.sample_interface import normalize_sample_name, parse_batch_labels


BATCH_CORRECTION_METHODS = {
    "None": "No batch correction",
    "ComBat": "ComBat empirical Bayes correction",
}

_REQUIRED_COMBAT_COLUMNS = ("Sample_Name", "Batch")
_EXCLUDED_COVARIATE_COLUMNS = {
    "sample_name",
    "batch",
    "injection_order",
    "injection_volume",
}
_EXCLUDED_COVARIATE_PATTERNS = ("order",)
_CURRENT_LABELS_DIAGNOSTIC_COLUMN = "Current labels"


def _load_pycombat_norm() -> Any:
    try:
        from inmoose.pycombat import pycombat_norm
    except ImportError as exc:
        raise ImportError(
            "ComBat requires inmoose. Install it with: uv pip install inmoose"
        ) from exc
    return pycombat_norm


def _build_sample_info_lookup(sample_info: pd.DataFrame) -> dict[str, pd.Series]:
    missing = [col for col in _REQUIRED_COMBAT_COLUMNS if col not in sample_info.columns]
    if missing:
        raise ValueError(f"SampleInfo missing required columns for ComBat: {', '.join(missing)}")

    lookup: dict[str, pd.Series] = {}
    for _, row in sample_info.iterrows():
        key = normalize_sample_name(row["Sample_Name"])
        if not key:
            continue
        if key in lookup:
            raise ValueError(
                "Duplicate SampleInfo sample names after normalization: "
                f"{lookup[key]['Sample_Name']}, {row['Sample_Name']}"
            )
        lookup[key] = row
    return lookup


def _align_sample_info_rows(sample_ids: pd.Index, sample_info: pd.DataFrame) -> pd.DataFrame:
    lookup = _build_sample_info_lookup(sample_info)
    rows: list[pd.Series] = []
    missing_names: list[str] = []
    for sample_id in sample_ids:
        key = normalize_sample_name(sample_id)
        row = lookup.get(key)
        if row is None:
            missing_names.append(str(sample_id))
            continue
        rows.append(row)
    if missing_names:
        preview = ", ".join(missing_names[:5])
        extra = "" if len(missing_names) <= 5 else f" (+{len(missing_names) - 5} more)"
        raise ValueError(
            "ComBat could not align SampleInfo rows for samples: "
            f"{preview}{extra}"
        )
    aligned = pd.DataFrame(rows).reset_index(drop=True)
    aligned.index = sample_ids
    return aligned


def list_combat_reference_batches(sample_info: pd.DataFrame) -> list[str]:
    """Return distinct single batch labels available in SampleInfo."""
    if "Batch" not in sample_info.columns:
        return []
    batches: set[str] = set()
    for raw_value in sample_info["Batch"]:
        for batch in parse_batch_labels(raw_value):
            if batch:
                batches.add(batch)
    return sorted(batches)


def _normalize_categorical_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna(pd.NA)


def _single_batch_error(source: str) -> ValueError:
    return ValueError(
        f"ComBat requires at least two distinct batches in {source}; got 1. "
        "Disable pipeline.batch_correction or provide multi-batch metadata."
    )


def _is_current_labels_diagnostic(column: object) -> bool:
    return str(column) == _CURRENT_LABELS_DIAGNOSTIC_COLUMN


def _format_design_factor(column: object) -> str:
    if _is_current_labels_diagnostic(column):
        return "current sample labels"
    return f"covariate '{column}'"


def _format_design_factor_sentence_start(column: object) -> str:
    if _is_current_labels_diagnostic(column):
        return "Current sample labels"
    return f"Covariate '{column}'"


def _design_factor_verb_has(column: object) -> str:
    return "have" if _is_current_labels_diagnostic(column) else "has"


def _relevel_single_batch_covariate(
    covariate: pd.Series,
    batch_labels: pd.Series,
) -> tuple[pd.Series, list[str]]:
    """Order batch-exclusive levels first so they act as baseline categories when possible."""
    aligned_covariate = _normalize_categorical_series(covariate)
    aligned_batches = _normalize_categorical_series(batch_labels)
    table = pd.crosstab(aligned_batches, aligned_covariate, dropna=False)
    level_batch_counts = (table > 0).sum(axis=0)
    single_batch_levels = [str(value) for value in level_batch_counts[level_batch_counts <= 1].index]
    if not single_batch_levels:
        return aligned_covariate, []

    existing_levels = [str(value) for value in aligned_covariate.dropna().unique()]
    ordered_levels = single_batch_levels + [
        level for level in existing_levels if level not in single_batch_levels
    ]
    categorical = pd.Categorical(
        aligned_covariate,
        categories=ordered_levels,
        ordered=True,
    )
    return pd.Series(categorical, index=aligned_covariate.index, name=aligned_covariate.name), single_batch_levels


def _is_excluded_covariate_column(column: str) -> bool:
    normalized = str(column).strip().lower()
    if normalized in _EXCLUDED_COVARIATE_COLUMNS:
        return True
    return any(pattern in normalized for pattern in _EXCLUDED_COVARIATE_PATTERNS)


def _looks_like_continuous_covariate(series: pd.Series) -> bool:
    if not is_numeric_dtype(series):
        return False
    unique_count = int(series.dropna().nunique())
    threshold = min(8, max(3, len(series.dropna()) // 4))
    return unique_count > threshold


def identify_combat_sample_info_covariates(
    sample_info: pd.DataFrame,
) -> tuple[list[str], dict[str, str]]:
    """Return usable SampleInfo covariates for ComBat plus rejected reasons."""
    candidates: list[str] = []
    rejected: dict[str, str] = {}
    for column in sample_info.columns:
        series = sample_info[column]
        if _is_excluded_covariate_column(column):
            rejected[str(column)] = "reserved or technical metadata"
            continue
        if series.isna().any():
            rejected[str(column)] = "contains missing values"
            continue
        if _looks_like_continuous_covariate(series):
            rejected[str(column)] = "appears continuous"
            continue
        normalized = _normalize_categorical_series(series)
        unique_count = int(normalized.nunique(dropna=True))
        if unique_count <= 1:
            rejected[str(column)] = "has only one level"
            continue
        if unique_count >= max(10, max(3, len(normalized) // 2)):
            rejected[str(column)] = "too many unique levels"
            continue
        candidates.append(str(column))
    return candidates, rejected


def _build_covariate_frame(
    sample_ids: pd.Index,
    aligned_sample_info: pd.DataFrame,
    batch_labels: pd.Series,
    *,
    labels: pd.Series | None = None,
    covariate_columns: Sequence[str] | None = None,
) -> tuple[pd.DataFrame | None, list[str], dict[str, list[str]]]:
    frames: list[pd.Series] = []
    names: list[str] = []
    reference_levels: dict[str, list[str]] = {}
    allowed_covariates, rejected_covariates = identify_combat_sample_info_covariates(aligned_sample_info)
    allowed_set = set(allowed_covariates)

    if labels is not None:
        aligned_labels = labels.reindex(sample_ids)
        if aligned_labels.isna().any():
            raise ValueError("ComBat labels could not be aligned to all samples.")
        label_series = _normalize_categorical_series(aligned_labels.rename("Condition"))
        label_series, label_reference_levels = _relevel_single_batch_covariate(
            label_series,
            batch_labels,
        )
        if label_series.nunique(dropna=True) > 1:
            frames.append(label_series)
            names.append("Condition")
            if label_reference_levels:
                reference_levels["Condition"] = label_reference_levels

    for column in covariate_columns or ():
        if column not in aligned_sample_info.columns:
            raise ValueError(f"SampleInfo missing ComBat covariate column: {column}")
        if str(column) not in allowed_set:
            reason = rejected_covariates.get(str(column), "not eligible for ComBat")
            raise ValueError(f"ComBat covariate '{column}' is invalid: {reason}.")
        covariate = _normalize_categorical_series(aligned_sample_info[column].rename(str(column)))
        if covariate.isna().any():
            raise ValueError(f"ComBat covariate '{column}' contains missing values.")
        covariate, covariate_reference_levels = _relevel_single_batch_covariate(
            covariate,
            batch_labels,
        )
        if covariate.nunique(dropna=True) <= 1:
            continue
        frames.append(covariate)
        names.append(str(column))
        if covariate_reference_levels:
            reference_levels[str(column)] = covariate_reference_levels

    if not frames:
        return None, [], reference_levels
    return pd.concat(frames, axis=1), names, reference_levels


def build_combat_design(
    sample_ids: pd.Index,
    sample_info: pd.DataFrame,
    *,
    labels: pd.Series | None = None,
    covariate_columns: Sequence[str] | None = None,
) -> tuple[pd.Series, pd.DataFrame | None, dict[str, Any]]:
    """Align ComBat batch labels and covariates to the current sample order."""
    aligned_sample_info = _align_sample_info_rows(sample_ids, sample_info)

    batch_values: list[str] = []
    for sample_id, raw_value in aligned_sample_info["Batch"].items():
        batches = parse_batch_labels(raw_value)
        if len(batches) != 1:
            raise ValueError(
                f"ComBat requires exactly one batch per sample; '{sample_id}' has '{raw_value}'."
            )
        batch_values.append(batches[0])

    batch_labels = pd.Series(batch_values, index=sample_ids, name="Batch", dtype="string")
    if batch_labels.nunique(dropna=True) < 2:
        raise _single_batch_error("SampleInfo.Batch")

    covariates, covariate_names, reference_levels = _build_covariate_frame(
        sample_ids,
        aligned_sample_info,
        batch_labels=batch_labels,
        labels=labels,
        covariate_columns=covariate_columns,
    )
    meta = {
        "batch_source": "SampleInfo.Batch",
        "covariate_columns": covariate_names,
        "covariate_reference_levels": reference_levels,
        "n_batches": int(batch_labels.nunique(dropna=True)),
        "batch_counts": batch_labels.value_counts(dropna=False).to_dict(),
    }
    return batch_labels, covariates, meta


def evaluate_combat_design(
    batch_labels: pd.Series,
    covariates: pd.DataFrame | None = None,
    *,
    strong_overlap_threshold: float = 0.90,
    strong_overlap_effect_size: float = 0.30,
    min_batch_size: int = 3,
    min_level_size: int = 3,
) -> dict[str, Any]:
    """Evaluate whether a ComBat design is obviously unsafe or imbalanced."""
    aligned_batches = _normalize_categorical_series(batch_labels.rename("Batch"))
    if aligned_batches.isna().any():
        raise ValueError("ComBat batch labels are missing for one or more samples.")

    batch_counts = aligned_batches.value_counts(dropna=False)
    warnings: list[str] = []
    blocking_errors: list[str] = []
    covariate_reports: dict[str, dict[str, Any]] = {}

    small_batches = {
        str(batch): int(count)
        for batch, count in batch_counts.items()
        if int(count) < min_batch_size
    }
    if small_batches:
        details = ", ".join(f"{batch} (n={count})" for batch, count in small_batches.items())
        warnings.append(
            f"Small batches detected for ComBat: {details}. Estimates may be unstable."
        )

    if covariates is None or covariates.empty:
        return {
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "batch_counts": {str(batch): int(count) for batch, count in batch_counts.items()},
            "small_batches": small_batches,
            "covariates": covariate_reports,
        }

    aligned_covariates = covariates.reindex(aligned_batches.index)
    if aligned_covariates.isna().any().any():
        raise ValueError("ComBat covariates are missing for one or more samples.")

    for column in aligned_covariates.columns:
        covariate = _normalize_categorical_series(aligned_covariates[column].rename(str(column)))
        table = pd.crosstab(aligned_batches, covariate, dropna=False)
        association = _evaluate_batch_covariate_association(table)
        batch_level_counts = (table > 0).sum(axis=1)
        level_batch_counts = (table > 0).sum(axis=0)
        batch_purity = (table.max(axis=1) / table.sum(axis=1)).fillna(0.0)
        level_purity = (table.max(axis=0) / table.sum(axis=0)).fillna(0.0)
        perfectly_confounded = bool(
            (batch_level_counts <= 1).all() and (level_batch_counts <= 1).all()
        )
        high_purity_batches = float((batch_purity >= strong_overlap_threshold).mean())
        high_purity_levels = float((level_purity >= strong_overlap_threshold).mean())
        strongly_overlapping = bool(
            not perfectly_confounded
            and (
                high_purity_batches >= 0.75
                or high_purity_levels >= 0.75
                or (
                    association["p_value"] is not None
                    and association["p_value"] < 0.05
                    and association["cramers_v"] is not None
                    and association["cramers_v"] >= strong_overlap_effect_size
                )
            )
        )
        single_level_batches = [str(value) for value in batch_level_counts[batch_level_counts <= 1].index]
        single_batch_levels = [str(value) for value in level_batch_counts[level_batch_counts <= 1].index]
        level_counts = covariate.value_counts(dropna=False)
        small_levels = {
            str(level): int(count)
            for level, count in level_counts.items()
            if int(count) < min_level_size
        }

        covariate_reports[str(column)] = {
            "perfectly_confounded": perfectly_confounded,
            "strongly_overlapping": strongly_overlapping,
            "association": association,
            "batch_purity": {str(idx): float(val) for idx, val in batch_purity.items()},
            "level_purity": {str(idx): float(val) for idx, val in level_purity.items()},
            "high_purity_batch_fraction": high_purity_batches,
            "high_purity_level_fraction": high_purity_levels,
            "single_level_batches": single_level_batches,
            "single_batch_levels": single_batch_levels,
            "small_levels": small_levels,
        }

        if perfectly_confounded:
            if _is_current_labels_diagnostic(column):
                blocking_errors.append(
                    "Current sample labels are perfectly confounded with Batch. "
                    "ComBat cannot safely run because labels and batches are indistinguishable."
                )
            else:
                blocking_errors.append(
                    f"ComBat covariate '{column}' is perfectly confounded with Batch "
                    "and cannot be used safely."
                )
            continue
        if strongly_overlapping:
            factor_text = _format_design_factor(column)
            if association["method"] == "fisher_exact":
                stat_text = (
                    f"Fisher exact p={association['p_value']:.3g}, odds_ratio={association['odds_ratio']:.3g}"
                )
            else:
                stat_text = (
                    f"chi-square p={association['p_value']:.3g}, "
                    f"cramers_v={association['cramers_v']:.3g}"
                )
            warnings.append(
                f"Batch and {factor_text} show strong overlap. ComBat may remove biological signal "
                f"({stat_text})."
            )
        if single_level_batches:
            factor_text = _format_design_factor_sentence_start(column)
            verb = _design_factor_verb_has(column)
            warnings.append(
                f"{factor_text} {verb} only one level inside batch(es): "
                f"{', '.join(single_level_batches)}."
            )
        if single_batch_levels:
            factor_text = _format_design_factor_sentence_start(column)
            warnings.append(
                f"{factor_text} levels present in only one batch: "
                f"{', '.join(single_batch_levels)}. These levels are ordered as baseline "
                "categories when possible."
            )
        if small_levels:
            details = ", ".join(f"{level} (n={count})" for level, count in small_levels.items())
            factor_text = _format_design_factor_sentence_start(column)
            verb = _design_factor_verb_has(column)
            warnings.append(
                f"{factor_text} {verb} sparse levels: {details}. "
                "Interpret corrected results carefully."
            )

    return {
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "batch_counts": {str(batch): int(count) for batch, count in batch_counts.items()},
        "small_batches": small_batches,
        "covariates": covariate_reports,
    }


def _evaluate_batch_covariate_association(table: pd.DataFrame) -> dict[str, Any]:
    """Summarize Batch x covariate association with an appropriate statistical test."""
    if table.empty:
        return {
            "method": "none",
            "p_value": None,
            "statistic": None,
            "cramers_v": None,
            "odds_ratio": None,
            "degrees_of_freedom": None,
        }

    observed = table.to_numpy(dtype=float)
    chi2, p_value, dof, expected = chi2_contingency(observed, correction=False)
    shape = observed.shape
    total = float(observed.sum())
    if total <= 0:
        return {
            "method": "none",
            "p_value": None,
            "statistic": None,
            "cramers_v": None,
            "odds_ratio": None,
            "degrees_of_freedom": None,
        }

    min_expected = float(expected.min()) if expected.size else 0.0
    min_observed = float(observed.min()) if observed.size else 0.0
    if shape == (2, 2) and (min_expected < 5.0 or min_observed < 5.0):
        odds_ratio, fisher_p = fisher_exact(observed)
        phi = float((chi2 / total) ** 0.5)
        cramers_v = (
            float(((chi2 / total) / min(shape[0] - 1, shape[1] - 1)) ** 0.5)
            if min(shape) > 1
            else 0.0
        )
        return {
            "method": "fisher_exact",
            "p_value": float(fisher_p),
            "statistic": float(phi),
            "cramers_v": cramers_v,
            "odds_ratio": float(odds_ratio),
            "degrees_of_freedom": int(dof),
        }

    cramers_denom = min(shape[0] - 1, shape[1] - 1)
    cramers_v = float(((chi2 / total) / cramers_denom) ** 0.5) if cramers_denom > 0 else 0.0
    return {
        "method": "chi_square",
        "p_value": float(p_value),
        "statistic": float(chi2),
        "cramers_v": cramers_v,
        "odds_ratio": None,
        "degrees_of_freedom": int(dof),
        "min_expected": min_expected,
        "min_observed": min_observed,
    }


def _validate_batch_labels(df: pd.DataFrame, batch_labels: pd.Series) -> pd.Series:
    aligned = batch_labels.reindex(df.index)
    if aligned.isna().any():
        raise ValueError("ComBat batch labels are missing for one or more samples.")
    if aligned.nunique(dropna=True) < 2:
        raise _single_batch_error("batch_labels")
    return aligned.astype("string")


def apply_batch_correction(
    df: pd.DataFrame,
    *,
    method: str = "None",
    batch_labels: pd.Series | None = None,
    covariates: pd.DataFrame | None = None,
    par_prior: bool = True,
    mean_only: bool = False,
    ref_batch: str | None = None,
) -> pd.DataFrame:
    """Apply batch correction to a samples x features matrix."""
    if method in (None, "None"):
        return df.copy()
    if method != "ComBat":
        raise ValueError(f"Unsupported batch correction method: {method}")
    if batch_labels is None:
        raise ValueError("ComBat requires batch_labels.")

    if all(is_numeric_dtype(dtype) for dtype in df.dtypes):
        numeric_df = df
    else:
        try:
            numeric_df = df.apply(pd.to_numeric, errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError("ComBat requires a numeric expression matrix.") from exc

    aligned_batches = _validate_batch_labels(numeric_df, batch_labels)
    aligned_covariates = None
    if covariates is not None:
        aligned_covariates = covariates.reindex(numeric_df.index)
        if aligned_covariates.isna().any().any():
            raise ValueError("ComBat covariates are missing for one or more samples.")

    pycombat_norm = _load_pycombat_norm()
    corrected = pycombat_norm(
        counts=numeric_df.T,
        batch=aligned_batches.tolist(),
        covar_mod=aligned_covariates,
        par_prior=par_prior,
        mean_only=mean_only,
        ref_batch=ref_batch,
        prior_plots=False,
    )
    corrected_df = pd.DataFrame(corrected, index=numeric_df.columns, columns=numeric_df.index).T
    corrected_df.index = numeric_df.index
    corrected_df.columns = numeric_df.columns
    return corrected_df
