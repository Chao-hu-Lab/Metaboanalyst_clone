"""OPLS-DA visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse
from scipy.stats import chi2

from visualization.score_labeling import annotate_score_labels
from visualization.theme import apply_publication_style, get_group_colors


_MA_MARKERS = ["o", "^", "s", "D", "v"]


def _confidence_ellipse(ax, x, y, color, fill_color, confidence: float = 0.95) -> None:
    """Draw a filled confidence ellipse that wraps the given score cloud."""
    if len(x) < 3:
        return

    cov = np.cov(x, y)
    if not np.all(np.isfinite(cov)) or np.linalg.det(cov) < 1e-14:
        return

    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    chi2_val = np.sqrt(chi2.ppf(confidence, 2))
    width = 2 * chi2_val * np.sqrt(eigenvalues[0])
    height = 2 * chi2_val * np.sqrt(eigenvalues[1])

    ax.add_patch(
        Ellipse(
            xy=(np.mean(x), np.mean(y)),
            width=width,
            height=height,
            angle=angle,
            facecolor=fill_color,
            edgecolor=color,
            alpha=0.25,
            linewidth=0.8,
            zorder=1,
        )
    )


def plot_oplsda_score(
    oplsda_result,
    show_labels: str = "outlier",
    confidence: float = 0.95,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the OPLS-DA score chart.

    Parameters
    ----------
    oplsda_result : OPLSDAResult
        Result object returned by ``analysis.oplsda.run_oplsda``.
    show_labels : {"outlier", "all", "none"}, default="outlier"
        Labeling strategy for score points.
    confidence : float, default=0.95
        Confidence level used for ellipses and outlier detection.
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
        fig = plt.figure(figsize=(8, 6.5))
    fig.clf()
    ax = fig.add_subplot(111)

    score_df = oplsda_result.get_score_df()
    groups = sorted(score_df["Group"].unique())
    colors = get_group_colors(theme, len(groups))
    backend = getattr(oplsda_result, "backend", "pyopls")

    all_t = score_df["T_predictive"].values
    all_o = score_df["T_orthogonal"].values
    total_var = np.var(all_t) + np.var(all_o)
    var_t = np.var(all_t) / total_var * 100 if total_var > 0 else 0.0
    var_o = np.var(all_o) / total_var * 100 if total_var > 0 else 0.0

    legend_handles = []
    for idx, group in enumerate(groups):
        color = colors[idx % len(colors)]
        marker = _MA_MARKERS[idx % len(_MA_MARKERS)]
        mask = score_df["Group"] == group
        x = score_df.loc[mask, "T_predictive"].values
        y = score_df.loc[mask, "T_orthogonal"].values
        samples = score_df.loc[mask, "Sample"].values

        _confidence_ellipse(ax, x, y, color, color, confidence)
        ax.scatter(
            x,
            y,
            marker=marker,
            s=55,
            facecolors="none",
            edgecolors=color,
            linewidth=1.3,
            zorder=3,
        )

        annotate_score_labels(
            ax,
            x,
            y,
            samples,
            show_labels=show_labels,
            confidence=confidence,
        )

        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker=marker,
                color="w",
                markerfacecolor="none",
                markeredgecolor=color,
                markeredgewidth=1.3,
                markersize=8,
                label=str(group),
            )
        )

    ax.set_xlabel(f"T score [1] ({var_t:.1f} %)", fontsize=10.5)
    if backend == "pls_fallback":
        ax.set_ylabel(f"T score [2] ({var_o:.1f} %)", fontsize=10.5)
        ax.text(
            0.01,
            0.01,
            "PLS fallback axis",
            transform=ax.transAxes,
            fontsize=8,
            alpha=0.7,
            ha="left",
            va="bottom",
        )
    else:
        ax.set_ylabel(f"Orthogonal T score [1] ({var_o:.1f} %)", fontsize=10.5)
    ax.set_title("Scores Plot", fontsize=12, fontweight="bold", pad=10)
    ax.legend(
        handles=legend_handles,
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
        borderaxespad=0.0,
        fontsize=8.5,
        frameon=False,
    )
    fig.tight_layout()
    return fig


def plot_oplsda_splot(
    oplsda_result,
    top_n: int = 10,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the OPLS-DA S-plot.

    Parameters
    ----------
    oplsda_result : OPLSDAResult
        Result object returned by ``analysis.oplsda.run_oplsda``.
    top_n : int, default=10
        Number of top features to annotate.
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
        fig = plt.figure(figsize=(8, 6))
    fig.clf()
    ax = fig.add_subplot(111)

    imp_df = oplsda_result.get_importance_df()
    if imp_df.empty:
        ax.set_title("OPLS-DA S-Plot (no data)")
        fig.tight_layout()
        return fig

    loadings = imp_df["Loading"].to_numpy(dtype=float)
    importance = imp_df["Importance"].to_numpy(dtype=float)
    features = imp_df["Feature"].astype(str).to_numpy()
    palette = get_group_colors(theme, 2)

    ax.scatter(loadings, importance, c=palette[1], s=30, alpha=0.6, zorder=2)

    top_idx = np.argsort(importance)[-top_n:]
    for idx in top_idx:
        ax.annotate(
            features[idx][:20],
            (loadings[idx], importance[idx]),
            fontsize=7,
            alpha=0.8,
            xytext=(5, 5),
            textcoords="offset points",
        )

    ax.set_xlabel("Predictive Loading p[1]", fontsize=10)
    ax.set_ylabel("|p[1]| (Importance)", fontsize=10)
    ax.set_title("OPLS-DA S-Plot", fontsize=12, fontweight="bold")
    ax.axvline(0, color="grey", linewidth=0.5, linestyle="-")
    fig.tight_layout()
    return fig
