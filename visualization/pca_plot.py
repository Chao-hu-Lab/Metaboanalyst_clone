"""PCA score, scree, and loading plots."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse
from scipy.stats import chi2

from visualization.theme import apply_publication_style, get_group_colors
from visualization.vip_plot import _format_mzrt_label


def plot_pca_score(
    pca_result,
    pc_x: int = 0,
    pc_y: int = 1,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the PCA score chart with per-group confidence ellipses.

    Parameters
    ----------
    pca_result : PCAResult
        Result object returned by ``analysis.pca.run_pca``.
    pc_x : int, default=0
        Zero-based component index used on the x-axis.
    pc_y : int, default=1
        Zero-based component index used on the y-axis.
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
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    scores = pca_result.scores
    labels = pca_result.labels
    var_ratio = pca_result.explained_variance_ratio
    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    colors = get_group_colors(theme, len(groups))

    for idx, group in enumerate(groups):
        mask = labels_arr == group
        x = scores[mask, pc_x]
        y = scores[mask, pc_y]
        ax.scatter(
            x,
            y,
            c=[colors[idx]],
            label=str(group),
            s=60,
            alpha=0.8,
            edgecolors="white",
            linewidth=0.5,
        )

        if len(x) > 2:
            cov = np.cov(x, y)
            if np.linalg.det(cov) > 1e-10:
                eig_vals, eig_vecs = np.linalg.eigh(cov)
                angle = np.degrees(np.arctan2(*eig_vecs[:, 1][::-1]))
                n_std = np.sqrt(chi2.ppf(0.95, 2))
                width, height = 2 * n_std * np.sqrt(np.abs(eig_vals))
                ax.add_patch(
                    Ellipse(
                        xy=(x.mean(), y.mean()),
                        width=width,
                        height=height,
                        angle=angle,
                        edgecolor=colors[idx],
                        facecolor="none",
                        linestyle="--",
                        linewidth=1.5,
                    )
                )

    ax.set_xlabel(f"PC{pc_x + 1} ({var_ratio[pc_x] * 100:.1f}%)")
    ax.set_ylabel(f"PC{pc_y + 1} ({var_ratio[pc_y] * 100:.1f}%)")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.0, fontsize=9)
    ax.set_title("PCA Score Plot")
    ax.axhline(0, color="grey", linewidth=0.5, linestyle=":")
    ax.axvline(0, color="grey", linewidth=0.5, linestyle=":")
    fig.tight_layout()
    return fig


def plot_pca_scree(
    pca_result,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the PCA scree chart.

    Parameters
    ----------
    pca_result : PCAResult
        Result object returned by ``analysis.pca.run_pca``.
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
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    var = pca_result.explained_variance_ratio
    x = np.arange(1, len(var) + 1)
    colors = get_group_colors(theme, 2)

    ax.bar(x, var * 100, color=colors[0], alpha=0.8, label="Explained")
    ax.plot(x, np.cumsum(var) * 100, "o-", color=colors[1], markersize=5, label="Cumulative")
    ax.set_xlabel("Principal Component")
    ax.set_ylabel("Explained Variance (%)")
    ax.set_title("Scree Plot")
    ax.set_xticks(x)
    ax.set_xticklabels([f"PC{i}" for i in x])
    ax.legend()
    fig.tight_layout()
    return fig


def plot_pca_loading(
    pca_result,
    pc: int = 0,
    top_n: int = 20,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the highest-magnitude PCA loadings for one component.

    Parameters
    ----------
    pca_result : PCAResult
        Result object returned by ``analysis.pca.run_pca``.
    pc : int, default=0
        Zero-based component index to visualize.
    top_n : int, default=20
        Number of features to display.
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
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    loading_df = pca_result.get_loading_df()
    col = loading_df.columns[pc]
    vals = loading_df[col].abs().nlargest(top_n).sort_values(ascending=True)
    palette = get_group_colors(theme, 2)

    colors = [palette[0] if loading_df.loc[feature, col] > 0 else palette[1] for feature in vals.index]
    actual_vals = [loading_df.loc[feature, col] for feature in vals.index]

    ax.barh(range(len(vals)), actual_vals, color=colors)
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels([_format_mzrt_label(str(feature)) for feature in vals.index], fontsize=8)
    ax.set_xlabel(f"Loading ({col})")
    ax.set_title(f"PCA Loading Plot - Top {top_n} Features")
    ax.axvline(0, color="grey", linewidth=0.5)
    fig.tight_layout()
    return fig
