"""Outlier visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse
from scipy.stats import chi2

from visualization.theme import COLORS, apply_publication_style, get_group_colors


def plot_outlier_score(
    outlier_result,
    labels=None,
    group_filter: str | None = None,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the PCA score scatter and Hotelling's T2 bar chart for outlier review.

    Parameters
    ----------
    outlier_result : OutlierResult
        Result object returned by ``analysis.outlier.run_outlier_detection``.
    labels : array-like or None, default=None
        Optional labels for compatibility with existing callers.
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
        fig = plt.figure(figsize=(10, 5))
    fig.clf()

    scores = outlier_result.scores
    t2_values = outlier_result.t2_values
    outlier_mask = outlier_result.outlier_mask_t2
    var_ratio = outlier_result.explained_variance

    x = scores[:, 0]
    y = scores[:, 1] if scores.shape[1] > 1 else np.zeros_like(x)
    sample_names = np.asarray(outlier_result.sample_names, dtype=object)
    labels_arr = None
    mask = np.ones(len(x), dtype=bool)
    if labels is not None:
        labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
        if group_filter is not None:
            mask = labels_arr.astype(str) == str(group_filter)

    x = x[mask]
    y = y[mask]
    t2_values = t2_values[mask]
    outlier_mask = outlier_mask[mask]
    sample_names = sample_names[mask]

    ax1 = fig.add_subplot(121)
    if labels_arr is not None:
        filtered_labels = labels_arr[mask].astype(str)
        groups = sorted(set(filtered_labels))
        group_colors = get_group_colors(theme, len(groups))
        legend_handles: list[Line2D] = []
        for idx, group in enumerate(groups):
            group_mask = filtered_labels == group
            ax1.scatter(
                x[group_mask],
                y[group_mask],
                c=[group_colors[idx]],
                alpha=0.78,
                s=42,
                label=str(group),
            )
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    linestyle="None",
                    markerfacecolor=group_colors[idx],
                    markeredgecolor=group_colors[idx],
                    markersize=7,
                    label=str(group),
                )
            )
        if np.any(outlier_mask):
            ax1.scatter(
                x[outlier_mask],
                y[outlier_mask],
                facecolors="none",
                edgecolors=config["text"],
                marker="o",
                s=120,
                linewidths=1.6,
                label="Outlier",
            )
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    linestyle="None",
                    markerfacecolor="none",
                    markeredgecolor=config["text"],
                    markeredgewidth=1.4,
                    markersize=9,
                    label="Outlier",
                )
            )
        ax1.legend(handles=legend_handles, fontsize=8)
    else:
        palette = get_group_colors(theme, 2)
        normal = ~outlier_mask
        ax1.scatter(x[normal], y[normal], c=palette[1], alpha=0.75, s=40, label="Normal")
        ax1.scatter(
            x[outlier_mask],
            y[outlier_mask],
            c=palette[0],
            marker="x",
            s=80,
            linewidths=2,
            label="Outlier",
        )
        ax1.legend(fontsize=8)

    for idx in np.where(outlier_mask)[0]:
        ax1.annotate(
            str(sample_names[idx]),
            (x[idx], y[idx]),
            fontsize=7,
            color=config["text"],
            alpha=0.9,
        )

    if len(x) > 2 and scores.shape[1] > 1:
        cov = np.cov(x, y)
        if np.all(np.isfinite(cov)) and np.linalg.det(cov) > 0:
            eig_vals, eig_vecs = np.linalg.eigh(cov)
            eig_vals = np.maximum(eig_vals, 0)
            angle = np.degrees(np.arctan2(*eig_vecs[:, 1][::-1]))
            n_std = np.sqrt(chi2.ppf(0.95, 2))
            width, height = 2 * n_std * np.sqrt(eig_vals)
            ellipse = Ellipse(
                xy=(x.mean(), y.mean()),
                width=width,
                height=height,
                angle=angle,
                edgecolor=config["grid"],
                facecolor="none",
                linestyle="--",
                linewidth=1.5,
            )
            ax1.add_patch(ellipse)

    pc1 = var_ratio[0] * 100 if len(var_ratio) > 0 else 0
    pc2 = var_ratio[1] * 100 if len(var_ratio) > 1 else 0
    ax1.set_xlabel(f"PC1 ({pc1:.1f}%)")
    ax1.set_ylabel(f"PC2 ({pc2:.1f}%)" if len(var_ratio) > 1 else "Pseudo-PC2")
    scope_text = f" - {group_filter}" if group_filter is not None else ""
    ax1.set_title(f"PCA Score Plot - Outlier Detection{scope_text}")

    ax2 = fig.add_subplot(122)
    palette = get_group_colors(theme, 2)
    bar_colors = [palette[0] if is_outlier else palette[1] for is_outlier in outlier_mask]
    ax2.bar(range(len(t2_values)), t2_values, color=bar_colors, alpha=0.75)
    ax2.axhline(
        y=outlier_result.t2_threshold,
        color=palette[0],
        linestyle="--",
        linewidth=1.5,
        label=f"95% threshold ({outlier_result.t2_threshold:.2f})",
    )
    ax2.set_xlabel("Sample index")
    ax2.set_ylabel("Hotelling T2")
    ax2.set_title("Hotelling's T2")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    return fig


def plot_dmodx(
    outlier_result,
    labels=None,
    group_filter: str | None = None,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the DModX outlier chart.

    Parameters
    ----------
    outlier_result : OutlierResult
        Result object returned by ``analysis.outlier.run_outlier_detection``.
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
    palette = get_group_colors(theme, 2)

    if fig is None:
        fig = plt.figure(figsize=(8, 5))
    fig.clf()
    ax = fig.add_subplot(111)

    dmodx = outlier_result.dmodx
    outlier_mask = outlier_result.outlier_mask_dmodx
    sample_names = np.asarray(outlier_result.sample_names, dtype=object)
    if labels is not None and group_filter is not None:
        labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
        mask = labels_arr.astype(str) == str(group_filter)
        dmodx = dmodx[mask]
        outlier_mask = outlier_mask[mask]
        sample_names = sample_names[mask]
    colors = [palette[0] if is_outlier else palette[1] for is_outlier in outlier_mask]

    ax.bar(range(len(dmodx)), dmodx, color=colors, alpha=0.75)
    ax.axhline(
        y=outlier_result.dmodx_threshold,
        color=palette[0],
        linestyle="--",
        linewidth=1.5,
        label=f"95% threshold ({outlier_result.dmodx_threshold:.4f})",
    )
    ax.set_xlabel("Sample index")
    ax.set_ylabel("DModX")
    scope_text = f" - {group_filter}" if group_filter is not None else ""
    ax.set_title(f"DModX (Distance to Model){scope_text}")
    ax.legend(fontsize=8)

    for idx in np.where(outlier_mask)[0]:
        ax.annotate(
            str(sample_names[idx]),
            (idx, dmodx[idx]),
            fontsize=7,
            color=palette[0],
            ha="center",
            va="bottom",
        )

    fig.tight_layout()
    return fig
