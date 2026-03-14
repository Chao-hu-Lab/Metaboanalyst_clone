"""Boxplot visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from visualization.theme import COLORS, apply_publication_style, get_group_colors


def plot_group_boxplot(
    df: pd.DataFrame,
    labels,
    title: str = "Feature Distribution",
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot overall feature distributions grouped by class.

    Parameters
    ----------
    df : DataFrame
        Input data matrix with samples as rows and features as columns.
    labels : array-like
        Group labels aligned to the rows of ``df``.
    title : str, default="Feature Distribution"
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
    palette = dict(zip(groups, get_group_colors(theme, len(groups))))

    plot_df = df.copy()
    plot_df["_Group"] = labels_arr
    melted = plot_df.melt(id_vars="_Group", var_name="Feature", value_name="Value")

    sns.boxplot(
        data=melted,
        x="_Group",
        y="Value",
        hue="_Group",
        ax=ax,
        palette=palette,
        fliersize=2,
        linewidth=0.8,
        legend=False,
    )
    ax.set_xlabel("Group")
    ax.set_ylabel("Intensity")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_sample_boxplot(
    df: pd.DataFrame,
    labels,
    title: str = "Sample Distribution",
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot a per-sample boxplot colored by group.

    Parameters
    ----------
    df : DataFrame
        Input data matrix with samples as rows and features as columns.
    labels : array-like
        Group labels aligned to the rows of ``df``.
    title : str, default="Sample Distribution"
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
        fig, ax = plt.subplots(figsize=(max(10, len(df) * 0.4), 5))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    palette = dict(zip(groups, get_group_colors(theme, len(groups))))
    colors = [palette[group] for group in labels_arr]

    boxplot = ax.boxplot(
        [df.iloc[idx].values for idx in range(len(df))],
        patch_artist=True,
        showfliers=False,
    )
    for patch, color in zip(boxplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xticklabels([str(sample)[:12] for sample in df.index], rotation=90, fontsize=7)
    ax.set_ylabel("Intensity")
    ax.set_title(title)

    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=palette[group], label=str(group)) for group in groups]
    ax.legend(handles=legend_elements, loc="best", fontsize=8)

    fig.tight_layout()
    return fig


def _draw_r_boxplot_on_ax(
    ax,
    data_by_group: list[np.ndarray],
    group_names: list[str],
    group_colors: list[str],
    config: dict,
    subtitle: str | None = None,
) -> None:
    """Draw a MetaboAnalyst-style boxplot on an existing axes."""
    positions = list(range(len(group_names)))

    for idx, values in enumerate(data_by_group):
        clean = np.asarray(values, dtype=float)
        clean = clean[np.isfinite(clean)]
        if len(clean) == 0:
            continue

        color = group_colors[idx % len(group_colors)]
        ax.boxplot(
            [clean],
            positions=[positions[idx]],
            widths=0.55,
            patch_artist=True,
            showmeans=False,
            showfliers=True,
            boxprops=dict(facecolor=color, edgecolor=config["axes_line"], linewidth=1.0),
            medianprops=dict(color=config["text"], linewidth=1.5),
            whiskerprops=dict(color=config["axes_line"], linewidth=1.0),
            capprops=dict(color=config["axes_line"], linewidth=1.0),
            flierprops=dict(
                marker="o",
                markerfacecolor=config["text"],
                markeredgecolor=config["text"],
                markersize=4,
                alpha=0.7,
            ),
        )
        ax.plot(
            positions[idx],
            np.mean(clean),
            marker="D",
            color="#FFD700",
            markersize=6,
            markeredgecolor="#B8860B",
            markeredgewidth=0.7,
            zorder=4,
        )

    ax.set_xticks(positions)
    ax.set_xticklabels(group_names, fontsize=9)
    if subtitle:
        ax.set_title(subtitle, fontsize=10)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)


def plot_feature_boxplot_paired(
    df_original: pd.DataFrame,
    df_normalized: pd.DataFrame,
    labels,
    feature_name: str,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot side-by-side boxplots for one feature before and after normalization.

    Parameters
    ----------
    df_original : DataFrame
        Data before normalization.
    df_normalized : DataFrame
        Data after normalization.
    labels : array-like
        Group labels aligned to the rows of the input matrices.
    feature_name : str
        Feature column to visualize.
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
    config = COLORS.get(theme, COLORS["light"])

    if fig is None:
        fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10, 5))
    else:
        fig.clear()
        ax_left = fig.add_subplot(121)
        ax_right = fig.add_subplot(122)

    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    box_colors = get_group_colors(theme, len(groups))

    for ax, frame, subtitle in [
        (ax_left, df_original, "Original Conc."),
        (ax_right, df_normalized, "Normalized Conc."),
    ]:
        data_by_group = []
        for group in groups:
            mask = labels_arr == group
            values = pd.to_numeric(frame.loc[mask, feature_name], errors="coerce").dropna().values
            data_by_group.append(values)
        _draw_r_boxplot_on_ax(ax, data_by_group, groups, box_colors, config, subtitle=subtitle)

    fig.suptitle(str(feature_name), fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig
