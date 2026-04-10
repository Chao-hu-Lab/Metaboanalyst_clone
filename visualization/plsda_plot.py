"""PLS-DA score plot with per-group confidence ellipses."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse
from scipy.stats import chi2

from visualization.score_labeling import add_score_labels, finalize_score_labels
from visualization.theme import apply_publication_style, get_group_colors


def plot_plsda_score(
    plsda_result,
    comp_x: int = 0,
    comp_y: int = 1,
    show_labels: str = "outlier",
    confidence: float = 0.95,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot PLS-DA score chart with per-group 95% confidence ellipses.

    Parameters
    ----------
    plsda_result : PLSDAResult
        Result object returned by ``analysis.plsda.run_plsda``.
    comp_x : int, default=0
        Zero-based component index for x-axis.
    comp_y : int, default=1
        Zero-based component index for y-axis.
    show_labels : {"outlier", "all", "none"}, default="outlier"
        Labeling strategy for sample names on the score plot.
    confidence : float, default=0.95
        Confidence level used for ellipse drawing and outlier labeling.
    theme : str, default="light"
        Visualization theme name.
    fig : Figure or None, default=None
        Existing figure to reuse.  When ``None``, a new figure is created.

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

    scores = plsda_result.scores
    labels = plsda_result.labels
    sample_names = np.asarray(
        getattr(plsda_result, "sample_names", [f"S{i+1}" for i in range(len(scores))]),
        dtype=object,
    )
    ev = plsda_result.explained_variance
    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    colors = get_group_colors(theme, len(groups))
    label_texts: list = []
    all_x = scores[:, comp_x]
    all_y = scores[:, comp_y]

    for idx, group in enumerate(groups):
        mask = labels_arr == group
        x = scores[mask, comp_x]
        y = scores[mask, comp_y]
        group_names = sample_names[mask]
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
                n_std = np.sqrt(chi2.ppf(confidence, 2))
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

        label_texts.extend(
            add_score_labels(
                ax,
                x,
                y,
                group_names,
                show_labels=show_labels,
                confidence=confidence,
                bbox_edgecolor=colors[idx],
            )
        )

    finalize_score_labels(ax, label_texts, all_x, all_y)

    x_label = f"Comp{comp_x + 1} ({ev[comp_x] * 100:.1f}%)" if len(ev) > comp_x else f"Comp{comp_x + 1}"
    y_label = f"Comp{comp_y + 1} ({ev[comp_y] * 100:.1f}%)" if len(ev) > comp_y else f"Comp{comp_y + 1}"
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title("PLS-DA Score Plot")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.0, fontsize=9)
    ax.axhline(0, color="grey", linewidth=0.5, linestyle=":")
    ax.axvline(0, color="grey", linewidth=0.5, linestyle=":")
    fig.tight_layout()
    return fig
