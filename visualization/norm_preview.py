"""Normalization preview charts."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy.stats import gaussian_kde

from visualization.theme import apply_publication_style, get_group_colors


def plot_norm_comparison(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    labels,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Compare distributions before and after normalization.

    Parameters
    ----------
    before_df : DataFrame
        Input data before normalization.
    after_df : DataFrame
        Input data after normalization.
    labels : array-like
        Group labels aligned to the rows of the input data.
    theme : str, default="light"
        Visualization theme name.
    fig : Figure or None, default=None
        Existing figure to reuse. When ``None``, a new figure is created.

    Returns
    -------
    Figure
        The rendered matplotlib figure.
    """
    apply_publication_style(theme)
    if fig is None:
        fig = plt.figure(figsize=(12, 8))
    else:
        fig.clear()

    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    palette = get_group_colors(theme, len(groups))
    color_map = dict(zip(groups, palette))

    ax1 = fig.add_subplot(2, 2, 1)
    _draw_group_box(ax1, before_df, labels_arr, groups, color_map, "Before Normalization")

    ax2 = fig.add_subplot(2, 2, 2)
    _draw_group_box(ax2, after_df, labels_arr, groups, color_map, "After Normalization")

    ax3 = fig.add_subplot(2, 2, 3)
    _draw_density(ax3, before_df, labels_arr, groups, color_map, "Before Density")

    ax4 = fig.add_subplot(2, 2, 4)
    _draw_density(ax4, after_df, labels_arr, groups, color_map, "After Density")

    fig.suptitle("Normalization Comparison", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


def _draw_group_box(ax, df, labels_arr, groups, color_map, title: str) -> None:
    """Draw grouped boxplots on an existing axes."""
    data_by_group = []
    colors = []
    for group in groups:
        mask = labels_arr == group
        values = df.loc[mask].to_numpy(dtype=float).ravel()
        values = values[np.isfinite(values)]
        data_by_group.append(values)
        colors.append(color_map[group])

    if not data_by_group:
        ax.set_title(title)
        return

    boxplot = ax.boxplot(data_by_group, patch_artist=True, showfliers=False)
    for patch, color in zip(boxplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_xticklabels([str(group)[:10] for group in groups], fontsize=8)
    ax.set_title(title, fontsize=10)
    ax.set_ylabel("Intensity")


def _draw_density(ax, df, labels_arr, groups, color_map, title: str) -> None:
    """Draw grouped density curves on an existing axes."""
    all_vals = df.to_numpy(dtype=float).ravel()
    all_vals = all_vals[np.isfinite(all_vals)]
    if len(all_vals) < 2:
        ax.set_title(title)
        return

    x_min, x_max = np.percentile(all_vals, [1, 99])
    x_range = np.linspace(x_min, x_max, 200)

    for group in groups:
        mask = labels_arr == group
        values = df.loc[mask].to_numpy(dtype=float).ravel()
        values = values[np.isfinite(values)]
        if len(values) < 2:
            continue
        try:
            kde = gaussian_kde(values)
        except Exception:
            continue
        ax.plot(x_range, kde(x_range), color=color_map[group], alpha=0.7, label=str(group))

    ax.set_xlabel("Intensity")
    ax.set_ylabel("Density")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=7)
