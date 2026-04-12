"""ROC visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from typing import TYPE_CHECKING, Any

from visualization.theme import COLORS, apply_publication_style, get_group_colors

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure
else:
    PlotlyFigure = Any


def plot_roc_curves(
    roc_result,
    show_multi: bool = True,
    top_n: int = 5,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot ROC curves for the top-ranked biomarkers and optional multi-feature model.

    Parameters
    ----------
    roc_result : ROCResult
        Result object returned by ``analysis.roc.run_roc_analysis``.
    show_multi : bool, default=True
        Whether to overlay the multi-feature logistic regression ROC curve.
    top_n : int, default=5
        Number of single-feature ROC curves to display.
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
        fig = plt.figure(figsize=(8, 7))
    fig.clf()
    ax = fig.add_subplot(111)

    ax.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        color=config["grid"],
        alpha=0.9,
        label="Random (AUC=0.5)",
    )

    palette = get_group_colors(theme, max(1, min(top_n, len(roc_result.single_rocs))))
    for idx, roc in enumerate(roc_result.single_rocs[:top_n]):
        color = palette[idx % len(palette)]
        label = f"{roc.feature[:20]} (AUC={roc.auc_score:.3f})"
        ax.plot(roc.fpr, roc.tpr, color=color, linewidth=1.8, label=label)
        best_idx = int(np.argmax(roc.tpr - roc.fpr))
        ax.plot(roc.fpr[best_idx], roc.tpr[best_idx], "o", color=color, markersize=6)

    if (
        show_multi
        and roc_result.multi_fpr is not None
        and roc_result.multi_tpr is not None
    ):
        multi_auc = (
            roc_result.multi_auc if roc_result.multi_auc is not None else float("nan")
        )
        ax.plot(
            roc_result.multi_fpr,
            roc_result.multi_tpr,
            color=config["text"],
            linewidth=2.5,
            label=f"Multi-feature LR (AUC={multi_auc:.3f})",
        )

    ax.set_xlabel("1 - Specificity (FPR)")
    ax.set_ylabel("Sensitivity (TPR)")
    ax.set_title("ROC Curves")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    fig.tight_layout()
    return fig


def plot_auc_ranking(
    roc_result,
    top_n: int = 15,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot AUC ranking for the top biomarkers.

    Parameters
    ----------
    roc_result : ROCResult
        Result object returned by ``analysis.roc.run_roc_analysis``.
    top_n : int, default=15
        Number of ranked biomarkers to display.
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
    palette = get_group_colors(theme, 3)
    summary = roc_result.summary_df.head(top_n)

    if fig is None:
        fig = plt.figure(figsize=(8, max(4, max(len(summary), 1) * 0.35)))
    fig.clf()
    ax = fig.add_subplot(111)

    if len(summary) == 0:
        ax.text(0.5, 0.5, "No ROC summary available.", ha="center", va="center")
        ax.set_axis_off()
        return fig

    colors = [
        palette[0] if auc_val >= 0.7 else palette[1] if auc_val >= 0.5 else palette[2]
        for auc_val in summary["AUC"]
    ]
    ax.barh(range(len(summary)), summary["AUC"].values, color=colors)
    ax.set_yticks(range(len(summary)))
    ax.set_yticklabels(summary["Feature"].astype(str).values, fontsize=8)
    ax.set_xlabel("AUC")
    ax.set_title("AUC Ranking")
    ax.axvline(x=0.5, color=palette[2], linestyle="--", alpha=0.6)
    ax.axvline(x=0.7, color=palette[0], linestyle="--", alpha=0.6)
    ax.text(
        0.51, len(summary) - 0.5, "Random", color=palette[2], fontsize=7.5, va="bottom"
    )
    ax.text(
        0.71, len(summary) - 0.5, "Good", color=palette[0], fontsize=7.5, va="bottom"
    )
    ax.invert_yaxis()
    ax.set_xlim([0, 1])
    fig.tight_layout()
    return fig


def plot_roc_interactive(
    roc_result,
    top_n: int = 10,
    theme: str = "light",
) -> PlotlyFigure | None:
    """
    Build an interactive Plotly ROC chart.

    Parameters
    ----------
    roc_result : ROCResult
        Result object returned by ``analysis.roc.run_roc_analysis``.
    top_n : int, default=10
        Number of single-feature ROC curves to display.
    theme : str, default="light"
        Visualization theme name.

    Returns
    -------
    plotly.graph_objects.Figure or None
        Plotly figure when Plotly is installed, otherwise ``None``.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    config = COLORS.get(theme, COLORS["light"])
    fig = go.Figure()
    palette = get_group_colors(theme, max(1, min(top_n, len(roc_result.single_rocs))))

    for idx, roc in enumerate(roc_result.single_rocs[:top_n]):
        fig.add_trace(
            go.Scatter(
                x=roc.fpr,
                y=roc.tpr,
                mode="lines",
                name=f"{roc.feature} (AUC={roc.auc_score:.3f})",
                line=dict(color=palette[idx % len(palette)], width=2),
                hovertemplate=(
                    "Feature: %{fullData.name}<br>"
                    "FPR: %{x:.3f}<br>"
                    "TPR: %{y:.3f}<extra></extra>"
                ),
            )
        )

    if roc_result.multi_fpr is not None and roc_result.multi_tpr is not None:
        multi_auc = (
            roc_result.multi_auc if roc_result.multi_auc is not None else float("nan")
        )
        fig.add_trace(
            go.Scatter(
                x=roc_result.multi_fpr,
                y=roc_result.multi_tpr,
                mode="lines",
                name=f"Multi-feature LR (AUC={multi_auc:.3f})",
                line=dict(color=config["text"], width=3),
                hovertemplate="FPR: %{x:.3f}<br>TPR: %{y:.3f}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Random",
            line=dict(color=config["grid"], dash="dash"),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        title="ROC Curves (Interactive)",
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
    )
    return fig
