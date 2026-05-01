"""Heatmap with hierarchical clustering."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from ms_core.analysis.clustering import select_top_features
from visualization.theme import apply_publication_style, get_group_colors


def order_samples_for_grouped_heatmap(
    df: pd.DataFrame,
    labels,
    group_order: list[str] | tuple[str, ...] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return data and labels ordered by configured group order, preserving row order."""
    label_series = (
        pd.Series(labels, index=df.index, name="Group")
        .reindex(df.index)
        .fillna("Unknown")
    )
    label_series = label_series.astype(str)
    observed_groups = label_series.unique().tolist()
    configured = [str(group) for group in (group_order or [])]
    ordered_groups = [group for group in configured if group in observed_groups]
    ordered_groups.extend(
        group for group in observed_groups if group not in ordered_groups
    )

    ordered_index: list[Any] = []
    for group in ordered_groups:
        ordered_index.extend(label_series.index[label_series == group].tolist())
    ordered_index.extend(index for index in df.index if index not in ordered_index)
    return df.loc[ordered_index].copy(), label_series.loc[ordered_index].copy()


def _standard_scale_heatmap_data(df: pd.DataFrame, scale: str | None) -> pd.DataFrame:
    """Mirror seaborn clustermap standard_scale behavior for fixed-order heatmaps."""
    if scale not in {"row", "col"}:
        return df

    axis = 1 if scale == "row" else 0
    mins = df.min(axis=axis)
    shifted = df.sub(mins, axis=0 if scale == "row" else 1)
    maxes = shifted.max(axis=axis).replace(0, np.nan)
    scaled = shifted.div(maxes, axis=0 if scale == "row" else 1)
    return scaled.fillna(0.0)


def plot_grouped_heatmap(
    df: pd.DataFrame,
    labels,
    *,
    group_order: list[str] | tuple[str, ...] | None = None,
    scale: str | None = "row",
    max_features: int | None = None,
    top_by: str = "var",
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """Plot a review-friendly heatmap with samples grouped by sample class."""
    apply_publication_style(theme)
    plot_df = df.copy()
    if max_features is not None and plot_df.shape[1] > max_features:
        plot_df = select_top_features(plot_df, max_features=max_features, by=top_by)
    plot_df, ordered_labels = order_samples_for_grouped_heatmap(
        plot_df,
        labels,
        group_order=group_order,
    )
    plot_df = _standard_scale_heatmap_data(plot_df, scale)

    groups = [str(group) for group in ordered_labels.dropna().unique()]
    palette = dict(zip(groups, get_group_colors(theme, len(groups))))
    group_codes = np.array([groups.index(str(group)) for group in ordered_labels])

    if fig is None:
        fig = plt.figure(figsize=(12, 8))
    else:
        fig.clear()

    grid = GridSpec(
        1,
        3,
        width_ratios=[0.46, 5.0, 0.16],
        wspace=0.03,
        figure=fig,
    )
    ax_group = fig.add_subplot(grid[0, 0])
    ax_heat = fig.add_subplot(grid[0, 1])
    ax_cbar = fig.add_subplot(grid[0, 2])

    ax_group.imshow(
        group_codes.reshape(-1, 1),
        aspect="auto",
        cmap=ListedColormap([palette[group] for group in groups]),
        interpolation="nearest",
    )
    ax_group.set_xticks([])
    ax_group.set_yticks([])
    ax_group.set_ylabel("")

    sns.heatmap(
        plot_df,
        cmap="RdBu_r",
        ax=ax_heat,
        cbar_ax=ax_cbar,
        xticklabels=plot_df.shape[1] <= 35,
        yticklabels=plot_df.shape[0] <= 50,
        linewidths=0,
    )
    ax_heat.set_title("Grouped Heatmap: Top 50 ANOVA Features", fontsize=11)
    ax_heat.set_xlabel("Features", fontsize=9)
    ax_heat.set_ylabel("")
    ax_heat.tick_params(axis="x", labelsize=7)
    ax_heat.tick_params(axis="y", labelsize=7)
    ax_cbar.tick_params(labelsize=8)
    ax_cbar.set_ylabel("Scaled intensity", fontsize=8)

    boundaries: list[int] = []
    previous = None
    for index, group in enumerate(ordered_labels.astype(str).tolist()):
        if previous is not None and group != previous:
            boundaries.append(index)
        previous = group
    for boundary in boundaries:
        ax_group.axhline(boundary - 0.5, color="white", linewidth=1.2)
        ax_heat.axhline(boundary, color="black", linewidth=0.7)

    group_values = ordered_labels.astype(str).tolist()
    for group in groups:
        positions = [index for index, value in enumerate(group_values) if value == group]
        if not positions:
            continue
        center = (positions[0] + positions[-1]) / 2
        ax_group.text(
            0,
            center,
            group,
            ha="center",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color="black",
        )

    fig.subplots_adjust(left=0.04, right=0.95, top=0.90, bottom=0.12)
    return fig


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
