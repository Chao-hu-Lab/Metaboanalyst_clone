"""Dendrogram and cluster summary plots for hierarchical clustering."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.cluster.hierarchy import dendrogram

from visualization.theme import apply_publication_style, get_group_colors


def plot_dendrogram(
    clustering_result,
    orientation: str = "top",
    truncate_mode: str | None = None,
    p: int = 30,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot a sample dendrogram from hierarchical clustering results.

    Parameters
    ----------
    clustering_result : ClusteringResult
        Result object returned by ``analysis.clustering.run_clustering``.
    orientation : str, default="top"
        Dendrogram orientation: "top", "bottom", "left", "right".
    truncate_mode : str or None, default=None
        Truncation mode passed to ``scipy.cluster.hierarchy.dendrogram``.
        Use ``"lastp"`` with ``p`` to show only the last ``p`` merged clusters.
    p : int, default=30
        Number of leaf nodes to show when truncate_mode is "lastp".
    theme : str, default="light"
        Visualization theme name.
    fig : Figure or None, default=None
        Existing figure to reuse.

    Returns
    -------
    Figure
        The rendered matplotlib figure.
    """
    apply_publication_style(theme)

    if fig is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    labels_arr = clustering_result.labels
    groups = sorted(set(labels_arr))
    colors = get_group_colors(theme, len(groups))
    group_color_map = dict(zip(groups, colors))

    n_samples = len(clustering_result.sample_names)
    show_group_suffix = n_samples <= 80
    sample_labels = [
        f"{clustering_result.sample_names[i]} ({labels_arr[i]})"
        if show_group_suffix
        else str(clustering_result.sample_names[i])
        for i in range(n_samples)
    ]

    dend_kwargs = dict(
        Z=clustering_result.row_linkage,
        labels=sample_labels,
        orientation=orientation,
        leaf_rotation=90 if orientation in ("top", "bottom") else 0,
        leaf_font_size=max(6, min(9, 300 // max(n_samples, 1))),
        ax=ax,
        above_threshold_color="grey",
    )
    if truncate_mode is not None:
        dend_kwargs["truncate_mode"] = truncate_mode
        dend_kwargs["p"] = p

    dendrogram(**dend_kwargs)

    # Color leaf labels by group
    if n_samples <= 80:
        xlabels = ax.get_xticklabels() if orientation in ("top", "bottom") else ax.get_yticklabels()
        for lbl in xlabels:
            text = lbl.get_text()
            for group in groups:
                if f"({group})" in text:
                    lbl.set_color(group_color_map[group])
                    break

    ax.set_title(
        f"Dendrogram ({clustering_result.method} / {clustering_result.metric})"
    )

    # Add legend for groups
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=group_color_map[g], label=str(g)) for g in groups
    ]
    ax.legend(
        handles=legend_elements, loc="upper right", fontsize=8, title="Group"
    )

    fig.tight_layout()
    return fig


def plot_cluster_summary(
    clustering_result,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot a cluster-vs-group contingency bar chart and cophenetic info.

    Parameters
    ----------
    clustering_result : ClusteringResult
        Result object returned by ``analysis.clustering.run_clustering``.
    theme : str, default="light"
        Visualization theme name.
    fig : Figure or None, default=None
        Existing figure to reuse.

    Returns
    -------
    Figure
        The rendered matplotlib figure.
    """
    apply_publication_style(theme)

    if fig is None:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    else:
        fig.clear()
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)

    labels_arr = clustering_result.labels
    groups = sorted(set(labels_arr))
    clusters = sorted(set(clustering_result.row_clusters))
    colors = get_group_colors(theme, len(groups))

    # Stacked bar: cluster membership by group
    bar_width = 0.6
    x = np.arange(len(clusters))
    bottoms = np.zeros(len(clusters))

    for g_idx, group in enumerate(groups):
        counts = []
        for c in clusters:
            mask = (clustering_result.row_clusters == c) & (labels_arr == group)
            counts.append(int(mask.sum()))
        ax1.bar(x, counts, bar_width, bottom=bottoms, label=str(group), color=colors[g_idx])
        bottoms += np.array(counts)

    ax1.set_xticks(x)
    ax1.set_xticklabels([f"C{c}" for c in clusters])
    ax1.set_xlabel("Cluster")
    ax1.set_ylabel("Count")
    ax1.set_title("Cluster Composition by Group")
    ax1.legend(fontsize=8, title="Group")

    # Cluster size pie chart
    cluster_sizes = [int((clustering_result.row_clusters == c).sum()) for c in clusters]
    wedge_colors = get_group_colors(theme, len(clusters))
    ax2.pie(
        cluster_sizes,
        labels=[f"C{c} (n={s})" for c, s in zip(clusters, cluster_sizes)],
        colors=wedge_colors,
        autopct="%1.0f%%",
        startangle=90,
    )
    ax2.set_title(
        f"Cluster Sizes\n(cophenetic r = {clustering_result.cophenetic_corr:.3f})"
    )

    fig.tight_layout()
    return fig
