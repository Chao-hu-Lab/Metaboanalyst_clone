"""Heatmap with hierarchical clustering."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from ms_core.analysis.clustering import select_top_features
from visualization.theme import apply_publication_style, get_group_colors


def plot_heatmap(
    df: pd.DataFrame,
    labels,
    method: str = "ward",
    metric: str = "euclidean",
    scale: str | None = "row",
    max_features: int = 2000,
    top_by: str = "var",
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot a clustered heatmap using the MetaboAnalyst-style defaults.

    Parameters
    ----------
    df : DataFrame
        Input data matrix with samples as rows and features as columns.
    labels : array-like
        Group labels aligned to the rows of ``df``.
    method : str, default="ward"
        Hierarchical clustering linkage method.
    metric : str, default="euclidean"
        Distance metric used by the clustering algorithm.
    scale : {"row", "col", None}, default="row"
        Scaling mode passed to seaborn's ``standard_scale``.
    max_features : int, default=2000
        Maximum number of features to display.
    top_by : str, default="var"
        Strategy used by ``select_top_features``.
    theme : str, default="light"
        Visualization theme name.
    fig : Figure or None, default=None
        Existing figure to reuse for the fallback heatmap path.

    Returns
    -------
    Figure
        The rendered matplotlib figure.
    """
    apply_publication_style(theme)
    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)

    plot_df = select_top_features(df, max_features=max_features, by=top_by)

    if scale == "row":
        standard_scale = 0
    elif scale == "col":
        standard_scale = 1
    else:
        standard_scale = None

    groups = sorted(set(labels_arr))
    palette = dict(zip(groups, get_group_colors(theme, len(groups))))
    row_colors = pd.Series(labels_arr, index=plot_df.index).map(palette)

    if method == "ward":
        metric = "euclidean"

    try:
        cluster_grid = sns.clustermap(
            plot_df,
            method=method,
            metric=metric,
            standard_scale=standard_scale,
            cmap="RdBu_r",
            figsize=(12, 8),
            row_colors=row_colors,
            dendrogram_ratio=(0.12, 0.12),
            linewidths=0,
            xticklabels=False if plot_df.shape[1] > 50 else True,
            yticklabels=False if plot_df.shape[0] > 50 else True,
            cbar_pos=(0.02, 0.82, 0.03, 0.14),
        )
        cluster_grid.fig.suptitle(
            "Heatmap with Hierarchical Clustering", y=1.01, fontsize=12
        )

        # Move colorbar to right side, below the Group legend, avoiding x-axis labels.
        # cbar_pos is in figure coordinates; repositioning after layout avoids
        # guessing where rotated x-tick labels end up.
        cluster_grid.fig.canvas.draw()
        hm_pos = cluster_grid.ax_heatmap.get_position()
        cb_left = hm_pos.x1 + 0.01
        cluster_grid.cax.set_position(
            [cb_left, hm_pos.y0 + 0.02, 0.022, hm_pos.height * 0.35]
        )

        from matplotlib.patches import Patch

        legend_elements = [
            Patch(facecolor=palette[group], label=str(group)) for group in groups
        ]
        cluster_grid.ax_heatmap.legend(
            handles=legend_elements,
            loc="upper left",
            bbox_to_anchor=(1.02, 1),
            fontsize=8,
            title="Group",
        )
        return cluster_grid.fig
    except Exception as exc:
        if fig is None:
            fig, ax = plt.subplots(figsize=(12, 8))
        else:
            fig.clear()
            ax = fig.add_subplot(111)
        sns.heatmap(plot_df, cmap="RdBu_r", ax=ax, xticklabels=False)
        ax.set_title(f"Heatmap (clustering failed: {exc})")
        fig.tight_layout()
        return fig
