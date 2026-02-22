"""
QC label helpers used by downstream statistical analysis.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd


def is_qc_label(value: object) -> bool:
    """Return True if a label should be treated as QC."""
    return "qc" in str(value).strip().lower()


def align_labels_to_data(
    data: pd.DataFrame,
    labels: pd.Series | Sequence | None,
) -> pd.Series | None:
    """Align labels to dataframe index without changing label order semantics."""
    if labels is None:
        return None

    if isinstance(labels, pd.Series):
        label_series = labels.copy()
    else:
        label_series = pd.Series(list(labels), index=data.index)

    if label_series.index.equals(data.index):
        return label_series

    aligned = label_series.reindex(data.index)
    if aligned.notna().all():
        aligned.name = label_series.name
        return aligned

    if len(label_series) == len(data):
        return pd.Series(label_series.to_numpy(), index=data.index, name=label_series.name)

    missing = [str(idx) for idx in data.index if idx not in label_series.index]
    preview = ", ".join(missing[:5])
    raise ValueError(f"Cannot align labels to data index. Missing sample labels: {preview}")


def exclude_qc_samples(
    data: pd.DataFrame,
    labels: pd.Series | Sequence | None,
) -> tuple[pd.DataFrame, pd.Series | None, int]:
    """
    Remove QC samples by label and return filtered data, labels, and removed count.
    """
    label_series = align_labels_to_data(data, labels)
    if label_series is None:
        return data.copy(), None, 0

    qc_mask = label_series.astype(str).map(is_qc_label)
    removed = int(qc_mask.sum())
    if removed == 0:
        return data.copy(), label_series.copy(), 0

    keep_mask = ~qc_mask
    filtered_data = data.loc[keep_mask].copy()
    filtered_labels = label_series.loc[keep_mask].copy()
    return filtered_data, filtered_labels, removed
