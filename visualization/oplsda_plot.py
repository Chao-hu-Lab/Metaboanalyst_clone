"""OPLS-DA visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse
from scipy.stats import chi2

try:
    from adjustText import adjust_text

    _HAS_ADJUSTTEXT = True
except ImportError:
    _HAS_ADJUSTTEXT = False

from visualization.interactive_score_plot import build_interactive_score_plot
from visualization.score_labeling import add_score_labels, finalize_score_labels
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
            facecolor="none",
            edgecolor=color,
            linestyle="--",
            linewidth=1.2,
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
    label_texts: list = []
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

        label_texts.extend(
            add_score_labels(
                ax,
                x,
                y,
                samples,
                show_labels=show_labels,
                confidence=confidence,
                bbox_edgecolor=color,
            )
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

    finalize_score_labels(ax, label_texts, all_t, all_o)

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
    ax.set_title("OPLS-DA Scores Plot", fontsize=12, fontweight="bold", pad=10)
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


def plot_oplsda_score_interactive(
    oplsda_result,
    show_labels: str = "outlier",
    confidence: float = 0.95,
    theme: str = "light",
):
    """Build an interactive Plotly OPLS-DA score plot."""
    score_df = oplsda_result.get_score_df().copy()
    backend = getattr(oplsda_result, "backend", "pyopls")
    total_var = np.var(score_df["T_predictive"].to_numpy(dtype=float)) + np.var(
        score_df["T_orthogonal"].to_numpy(dtype=float)
    )
    var_t = (
        np.var(score_df["T_predictive"].to_numpy(dtype=float)) / total_var * 100
        if total_var > 0
        else 0.0
    )
    var_o = (
        np.var(score_df["T_orthogonal"].to_numpy(dtype=float)) / total_var * 100
        if total_var > 0
        else 0.0
    )
    y_label = "T score [2]" if backend == "pls_fallback" else "T orthogonal [1]"
    return build_interactive_score_plot(
        pd.DataFrame(
            {
                "x": score_df["T_predictive"].to_numpy(dtype=float),
                "y": score_df["T_orthogonal"].to_numpy(dtype=float),
                "Sample": score_df["Sample"].astype(str),
                "Group": score_df["Group"].astype(str),
            }
        ),
        x_col="x",
        y_col="y",
        sample_col="Sample",
        group_col="Group",
        x_label=f"T score [1] ({var_t:.1f} %)",
        y_label=f"{y_label} ({var_o:.1f} %)",
        title="OPLS-DA Score Plot",
        show_labels=show_labels,
        confidence=confidence,
        theme=theme,
    )


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
        fig = plt.figure(figsize=(8.8, 6.8))
    fig.clf()
    ax = fig.add_subplot(111)

    imp_df = oplsda_result.get_importance_df()
    if imp_df.empty:
        ax.text(
            0.5,
            0.5,
            "OPLS-DA S-Plot\nNo importance data available.",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
        )
        ax.set_axis_off()
        fig.suptitle("OPLS-DA S-Plot", fontsize=13, fontweight="bold", y=0.97)
        fig.tight_layout()
        return fig

    loadings = imp_df["Loading"].to_numpy(dtype=float)
    if "Importance" in imp_df.columns:
        importance = imp_df["Importance"].to_numpy(dtype=float)
    else:
        importance = np.abs(loadings)
    features = imp_df["Feature"].astype(str).to_numpy()
    palette = get_group_colors(theme, 3)
    positive_color = palette[0]
    negative_color = palette[1]
    neutral_color = palette[2] if len(palette) > 2 else palette[0]

    pos_mask = loadings >= 0
    neg_mask = ~pos_mask
    ax.scatter(
        loadings[neg_mask],
        importance[neg_mask],
        c=negative_color,
        s=28,
        alpha=0.55,
        zorder=2,
        label="Negative loading",
    )
    ax.scatter(
        loadings[pos_mask],
        importance[pos_mask],
        c=positive_color,
        s=28,
        alpha=0.55,
        zorder=2,
        label="Positive loading",
    )

    top_idx = _select_balanced_annotation_indices(loadings, importance, top_n)
    texts = []
    for rank, idx in enumerate(top_idx, start=1):
        txt = ax.text(
            loadings[idx],
            importance[idx],
            features[idx][:24],
            fontsize=7.2,
            color=neutral_color,
            alpha=0.95,
            ha="left" if loadings[idx] >= 0 else "right",
            va="bottom" if rank % 2 else "top",
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": positive_color if loadings[idx] >= 0 else negative_color,
                "linewidth": 0.6,
                "alpha": 0.88,
            },
        )
        texts.append(txt)

    if texts and _HAS_ADJUSTTEXT:
        adjust_text(
            texts,
            ax=ax,
            arrowprops=dict(arrowstyle="-", color=neutral_color, lw=0.5),
        )

    ax.axvline(0, color="grey", linewidth=0.8, linestyle="-", alpha=0.6)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="-", alpha=0.35)
    ax.set_xlabel("Predictive Loading p[1]", fontsize=10)
    ax.set_ylabel("Absolute predictive loading |p[1]|", fontsize=10)
    ax.set_title("OPLS-DA S-Plot", fontsize=13, fontweight="bold", pad=10)
    ax.text(
        0.01,
        0.99,
        f"Annotated top {len(top_idx)} features by |loading|",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        alpha=0.85,
    )
    ax.legend(
        handles=[
            Patch(
                facecolor=positive_color,
                edgecolor=positive_color,
                label="Positive loading",
                alpha=0.55,
            ),
            Patch(
                facecolor=negative_color,
                edgecolor=negative_color,
                label="Negative loading",
                alpha=0.55,
            ),
        ],
        loc="upper right",
        frameon=False,
        fontsize=8.5,
    )
    ax.margins(x=0.08, y=0.12)
    fig.tight_layout()
    return fig


def _select_balanced_annotation_indices(
    loadings: np.ndarray,
    importance: np.ndarray,
    top_n: int,
) -> list[int]:
    """Pick a balanced set of positive/negative contributors for annotation."""
    if top_n <= 0 or len(loadings) == 0:
        return []

    order = np.argsort(importance)[::-1]
    positive = [int(idx) for idx in order if loadings[idx] >= 0]
    negative = [int(idx) for idx in order if loadings[idx] < 0]

    target_positive = int(np.ceil(top_n / 2))
    target_negative = top_n - target_positive
    selected = positive[:target_positive] + negative[:target_negative]

    if len(selected) < top_n:
        seen = set(selected)
        for idx in order:
            idx = int(idx)
            if idx in seen:
                continue
            selected.append(idx)
            seen.add(idx)
            if len(selected) >= top_n:
                break

    return selected[:top_n]
