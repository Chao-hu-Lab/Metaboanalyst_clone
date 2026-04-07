"""Shared helpers for score-plot sample labeling policies."""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2


def mahalanobis_outlier_mask(
    x: np.ndarray,
    y: np.ndarray,
    confidence: float = 0.95,
) -> np.ndarray:
    """Return a boolean mask for points outside the confidence ellipse."""
    if len(x) < 3:
        return np.zeros(len(x), dtype=bool)

    points = np.column_stack([x, y])
    mean = points.mean(axis=0)
    cov = np.cov(x, y)
    try:
        cov_inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        return np.zeros(len(x), dtype=bool)

    diff = points - mean
    md_sq = np.sum(diff @ cov_inv * diff, axis=1)
    threshold = chi2.ppf(confidence, 2)
    return md_sq > threshold


def build_score_label_mask(
    x: np.ndarray,
    y: np.ndarray,
    show_labels: str,
    confidence: float = 0.95,
) -> np.ndarray:
    """Return the labeling mask for a score plot."""
    if show_labels == "all":
        return np.ones(len(x), dtype=bool)
    if show_labels == "outlier":
        return mahalanobis_outlier_mask(x, y, confidence=confidence)
    return np.zeros(len(x), dtype=bool)


def annotate_score_labels(
    ax,
    x: np.ndarray,
    y: np.ndarray,
    sample_names,
    show_labels: str,
    confidence: float = 0.95,
    *,
    fontsize: float = 6.5,
    color: str = "#444444",
) -> None:
    """Annotate selected score points with sample names."""
    label_mask = build_score_label_mask(x, y, show_labels=show_labels, confidence=confidence)
    for x_val, y_val, name, should_label in zip(x, y, sample_names, label_mask):
        if not should_label:
            continue
        ax.annotate(
            str(name),
            (x_val, y_val),
            fontsize=fontsize,
            color=color,
            xytext=(5, 2),
            textcoords="offset points",
            zorder=4,
        )
