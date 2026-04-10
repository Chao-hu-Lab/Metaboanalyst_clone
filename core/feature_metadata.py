"""Shared feature-metadata helpers for CLI and GUI runtime parity."""

from __future__ import annotations

import pandas as pd

FEATURE_MARKER_COLUMN = "is_Presence_Absence_Marker"
_TRUTHY_MARKER_VALUES = frozenset({"true", "1", "yes", "y"})


def default_feature_metadata(feature_names: pd.Index) -> pd.DataFrame:
    """Return a normalized feature-metadata frame for the given features."""
    index = pd.Index(feature_names.copy(), name="Feature")
    metadata = pd.DataFrame(index=index)
    metadata[FEATURE_MARKER_COLUMN] = False
    return metadata


def normalize_presence_absence_marker(
    values: pd.Series,
    feature_names: pd.Index,
) -> pd.Series:
    """Normalize marker annotations to a strict boolean series."""
    normalized = pd.Series(False, index=feature_names, dtype=bool)
    for feature_name, value in zip(feature_names, values, strict=False):
        if pd.isna(value):
            continue
        text = str(value).strip().lower()
        if text in _TRUTHY_MARKER_VALUES:
            normalized.loc[feature_name] = True
    return normalized


def extract_feature_metadata(raw_feature_rows: pd.DataFrame, feature_names: pd.Index) -> pd.DataFrame:
    """Extract shared feature metadata from feature rows only."""
    metadata = default_feature_metadata(feature_names)
    if FEATURE_MARKER_COLUMN not in raw_feature_rows.columns:
        return metadata

    marker_values = raw_feature_rows[FEATURE_MARKER_COLUMN].reset_index(drop=True)
    metadata[FEATURE_MARKER_COLUMN] = normalize_presence_absence_marker(
        marker_values,
        metadata.index,
    )
    return metadata
