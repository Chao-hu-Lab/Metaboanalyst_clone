"""Shared feature-metadata helpers for CLI and GUI runtime parity."""

from __future__ import annotations

import re

import pandas as pd

FEATURE_MARKER_COLUMN = "is_Presence_Absence_Marker"
FEATURE_KEEP_REASONS_COLUMN = "Feature_Filter_Keep_Reasons"
IMPUTATION_TAG_REASONS_COLUMN = "Imputation_Tag_Reasons"
FEATURE_DELETE_REASONS_COLUMN = "Feature_Filter_Delete_Reasons"
DETECTION_PROFILE_COLUMN = "Detection_Profile"

STEP4_STATIC_METADATA_COLUMNS = (
    FEATURE_MARKER_COLUMN,
    FEATURE_KEEP_REASONS_COLUMN,
    IMPUTATION_TAG_REASONS_COLUMN,
    FEATURE_DELETE_REASONS_COLUMN,
    DETECTION_PROFILE_COLUMN,
)
STEP4_REASON_COLUMNS = (
    FEATURE_KEEP_REASONS_COLUMN,
    IMPUTATION_TAG_REASONS_COLUMN,
)

_TRUTHY_MARKER_VALUES = frozenset({"true", "1", "1.0"})
_FALSY_MARKER_VALUES = frozenset({"false", "0", "0.0"})


def _normalize_column_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


_STATIC_METADATA_BY_NORMALIZED_NAME = {
    _normalize_column_name(column): column for column in STEP4_STATIC_METADATA_COLUMNS
}


def is_step4_ratio_column(column_name: object) -> bool:
    """Return True for Step4 dynamic ratio metadata columns."""
    text = str(column_name).strip().lower()
    return text == "qc_ratio" or text.endswith("_ratio")


def is_step4_feature_metadata_column(column_name: object) -> bool:
    """Return True when a column is Step4 feature-level metadata."""
    normalized = _normalize_column_name(column_name)
    return normalized in _STATIC_METADATA_BY_NORMALIZED_NAME or is_step4_ratio_column(column_name)


def canonical_step4_metadata_column(column_name: object) -> str:
    """Return the canonical name for static Step4 metadata columns."""
    normalized = _normalize_column_name(column_name)
    return _STATIC_METADATA_BY_NORMALIZED_NAME.get(normalized, str(column_name))


def _find_column(columns: pd.Index, target: str) -> str | None:
    target_normalized = _normalize_column_name(target)
    for column in columns:
        if _normalize_column_name(column) == target_normalized:
            return str(column)
    return None


def default_feature_metadata(feature_names: pd.Index) -> pd.DataFrame:
    """Return a normalized feature-metadata frame for the given features."""
    index = pd.Index(feature_names.copy(), name="Feature")
    metadata = pd.DataFrame(index=index)
    metadata[FEATURE_MARKER_COLUMN] = False
    metadata.attrs["step4_metadata_detected"] = False
    return metadata


def normalize_presence_absence_marker(
    values: pd.Series,
    feature_names: pd.Index,
) -> pd.Series:
    """Normalize marker annotations to a strict boolean series."""
    normalized_values: list[bool] = []
    invalid_values: list[str] = []
    for feature_name, value in zip(feature_names, values, strict=False):
        if pd.isna(value):
            invalid_values.append(f"{feature_name}=<blank>")
            continue
        text = str(value).strip().lower()
        if not text:
            invalid_values.append(f"{feature_name}=<blank>")
            continue
        if text in _TRUTHY_MARKER_VALUES:
            normalized_values.append(True)
        elif text in _FALSY_MARKER_VALUES:
            normalized_values.append(False)
        else:
            invalid_values.append(f"{feature_name}={value!r}")

    if invalid_values:
        preview = ", ".join(invalid_values[:5])
        extra = "" if len(invalid_values) <= 5 else f" (+{len(invalid_values) - 5} more)"
        raise ValueError(
            f"Invalid {FEATURE_MARKER_COLUMN} values: {preview}{extra}. "
            "Expected True/TRUE/true/1/1.0 or False/FALSE/false/0/0.0."
        )

    return pd.Series(normalized_values, index=feature_names, dtype=bool)


def extract_feature_metadata(raw_feature_rows: pd.DataFrame, feature_names: pd.Index) -> pd.DataFrame:
    """Extract shared feature metadata from feature rows only."""
    metadata = default_feature_metadata(feature_names)
    step4_columns = [
        str(column)
        for column in raw_feature_rows.columns
        if is_step4_feature_metadata_column(column)
    ]
    if not step4_columns:
        return metadata

    marker_column = _find_column(raw_feature_rows.columns, FEATURE_MARKER_COLUMN)
    if marker_column is None:
        raise ValueError(
            "Step4 feature metadata columns were detected "
            f"({', '.join(step4_columns[:5])}), but required column "
            f"{FEATURE_MARKER_COLUMN} is missing."
        )

    metadata.attrs["step4_metadata_detected"] = True
    marker_values = raw_feature_rows[marker_column].reset_index(drop=True)
    metadata[FEATURE_MARKER_COLUMN] = normalize_presence_absence_marker(
        marker_values,
        metadata.index,
    )
    for column in raw_feature_rows.columns:
        column_name = str(column)
        if column_name == marker_column or not is_step4_feature_metadata_column(column_name):
            continue

        output_column = canonical_step4_metadata_column(column_name)
        values = raw_feature_rows[column].reset_index(drop=True)
        if is_step4_ratio_column(column_name):
            try:
                metadata[output_column] = (
                    pd.to_numeric(values, errors="raise").astype(float).to_numpy()
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid numeric Step4 ratio metadata in column '{column_name}'."
                ) from exc
        else:
            blank_mask = values.astype("string").str.strip().eq("").fillna(False)
            metadata[output_column] = values.mask(blank_mask, other=float("nan")).to_numpy()
    return metadata
