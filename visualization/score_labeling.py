"""Shared helpers for score-plot sample labeling policies."""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2

try:
    from adjustText import adjust_text

    HAS_ADJUSTTEXT = True
except ImportError:
    HAS_ADJUSTTEXT = False


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


def add_score_labels(
    ax,
    x: np.ndarray,
    y: np.ndarray,
    sample_names,
    show_labels: str,
    confidence: float = 0.95,
    *,
    fontsize: float = 6.5,
    color: str = "#444444",
    bbox_edgecolor: str = "#999999",
) -> list:
    """Create text labels for selected score points and return the text artists."""
    label_mask = build_score_label_mask(x, y, show_labels=show_labels, confidence=confidence)
    texts = []
    for x_val, y_val, name, should_label in zip(x, y, sample_names, label_mask):
        if not should_label:
            continue
        texts.append(
            ax.text(
                x_val,
                y_val,
                str(name),
                fontsize=fontsize,
                color=color,
                zorder=4,
                bbox={
                    "boxstyle": "round,pad=0.18",
                    "facecolor": "white",
                    "edgecolor": bbox_edgecolor,
                    "linewidth": 0.7,
                    "alpha": 0.9,
                },
            )
        )
    return texts


def finalize_score_labels(
    ax,
    texts: list,
    x_points: np.ndarray,
    y_points: np.ndarray,
    *,
    arrow_color: str = "#666666",
) -> None:
    """Resolve score-label overlap across the entire plot."""
    if not texts:
        return

    if HAS_ADJUSTTEXT:
        adjust_text(
            texts,
            x=np.asarray(x_points, dtype=float),
            y=np.asarray(y_points, dtype=float),
            ax=ax,
            arrowprops={
                "arrowstyle": "-",
                "color": arrow_color,
                "lw": 0.5,
                "alpha": 0.7,
            },
            expand=(1.15, 1.35),
            force_text=(0.2, 0.35),
            force_static=(0.15, 0.25),
            ensure_inside_axes=True,
            prevent_crossings=True,
        )
        return

    for idx, text in enumerate(texts):
        x_val, y_val = text.get_position()
        text.set_position((x_val + 0.03 * ((idx % 3) - 1), y_val + 0.04 * (idx + 1)))


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
    bbox_edgecolor: str = "#999999",
) -> None:
    """Backward-compatible wrapper that annotates and resolves one score cloud."""
    texts = add_score_labels(
        ax,
        x,
        y,
        sample_names,
        show_labels,
        confidence=confidence,
        fontsize=fontsize,
        color=color,
        bbox_edgecolor=bbox_edgecolor,
    )
    finalize_score_labels(ax, texts, x, y, arrow_color=bbox_edgecolor)
