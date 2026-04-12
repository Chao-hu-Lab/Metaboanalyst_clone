"""Density plot helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy.stats import gaussian_kde

from visualization.theme import apply_publication_style, get_group_colors


def plot_density(
    df: pd.DataFrame,
    labels,
    title: str = "Density Plot",
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot per-sample density curves colored by group.

    Parameters
    ----------
    df : DataFrame
        Input data matrix with samples as rows and features as columns.
    labels : array-like
        Group labels aligned to the rows of ``df``.
    title : str, default="Density Plot"
        Figure title.
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
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    palette = get_group_colors(theme, len(groups))
    color_map = dict(zip(groups, palette))

    all_vals = df.to_numpy(dtype=float).ravel()
    all_vals = all_vals[np.isfinite(all_vals)]
    if len(all_vals) == 0:
        return fig

    x_min, x_max = np.percentile(all_vals, [1, 99])
    x_range = np.linspace(x_min, x_max, 300)

    plotted_groups: set[str] = set()
    for row_idx in range(len(df)):
        values = (
            pd.to_numeric(df.iloc[row_idx], errors="coerce")
            .dropna()
            .to_numpy(dtype=float)
        )
        if len(values) < 2:
            continue

        group = labels_arr[row_idx]
        try:
            kde = gaussian_kde(values)
        except Exception:
            continue

        label = str(group) if group not in plotted_groups else None
        ax.plot(x_range, kde(x_range), color=color_map[group], alpha=0.65, label=label)
        plotted_groups.add(group)

    ax.set_xlabel("Intensity")
    ax.set_ylabel("Density")
    ax.set_title(title)
    if plotted_groups:
        ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    return fig
