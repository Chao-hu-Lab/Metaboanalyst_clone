"""ANOVA visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy.stats import f_oneway, kruskal, mannwhitneyu, ttest_ind

from visualization.theme import COLORS, apply_publication_style, get_group_colors


def plot_anova_importance(
    anova_result,
    top_n: int = 25,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot ANOVA feature importance as a ranked horizontal bar chart.

    Parameters
    ----------
    anova_result : ANOVAResult
        Result object returned by ``analysis.anova.run_anova``.
    top_n : int, default=25
        Number of top-ranked features to display.
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
        fig, ax = plt.subplots(figsize=(8, max(6, top_n * 0.3)))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    df = anova_result.result_df.sort_values("neg_log10p", ascending=False).head(top_n)
    df = df.iloc[::-1]

    palette = get_group_colors(theme, 2)
    bar_colors = [palette[0] if is_sig else config["grid"] for is_sig in df["significant"]]

    ax.barh(range(len(df)), df["neg_log10p"].values, color=bar_colors, height=0.7)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([str(feature)[:25] for feature in df["Feature"]], fontsize=8)
    ax.axvline(
        x=-np.log10(anova_result.p_thresh),
        color=palette[1],
        linestyle="--",
        alpha=0.8,
        linewidth=1,
        label=f"p = {anova_result.p_thresh}",
    )
    ax.set_xlabel("-log10(adj. p-value)")
    method_key = str(getattr(anova_result, "method_key", "anova")).lower()
    title = "Kruskal-Wallis: Important Features" if method_key == "kruskal" else "ANOVA: Important Features"
    ax.set_title(title)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


def _build_stat_annotation(
    plot_data: pd.DataFrame,
    annotation_method: str | None = None,
) -> str:
    grouped_values = []
    for _, group_df in plot_data.groupby("Group"):
        values = pd.to_numeric(group_df["Value"], errors="coerce").dropna().values
        if len(values) > 0:
            grouped_values.append(values)

    if annotation_method == "mannwhitney":
        if len(grouped_values) != 2 or min(len(grouped_values[0]), len(grouped_values[1])) < 2:
            return ""
        u_stat, p_val = mannwhitneyu(grouped_values[0], grouped_values[1], alternative="two-sided")
        return f"P = {p_val:.2e}\nMann-Whitney U = {u_stat:.4f}"

    if annotation_method == "kruskal":
        if len(grouped_values) < 2 or any(len(values) < 2 for values in grouped_values):
            return ""
        h_stat, p_val = kruskal(*grouped_values)
        return f"P = {p_val:.2e}\nKruskal-Wallis H = {h_stat:.4f}"

    if annotation_method == "anova":
        if len(grouped_values) < 2 or any(len(values) < 2 for values in grouped_values):
            return ""
        f_stat, p_val = f_oneway(*grouped_values)
        return f"P = {p_val:.2e}\nANOVA F = {f_stat:.4f}"

    if len(grouped_values) == 2:
        if min(len(grouped_values[0]), len(grouped_values[1])) < 2:
            return ""
        t_stat, p_val = ttest_ind(grouped_values[0], grouped_values[1], equal_var=False)
        return f"P = {p_val:.2e}\nT-test = {t_stat:.4f}"

    if len(grouped_values) >= 3:
        if any(len(values) < 2 for values in grouped_values):
            return ""
        f_stat, p_val = f_oneway(*grouped_values)
        return f"P = {p_val:.2e}\nANOVA F = {f_stat:.4f}"

    return ""


def _draw_r_style_boxplot(
    ax,
    data_by_group: list[np.ndarray],
    group_names: list[str],
    group_colors: list[str],
    config: dict,
) -> None:
    """Draw a MetaboAnalyst-style filled boxplot on an existing axes."""
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

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)


def plot_feature_boxplot(
    df: pd.DataFrame,
    labels,
    feature_name: str,
    annotation_method: str | None = None,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot one feature by group with statistical annotation.

    Parameters
    ----------
    df : DataFrame
        Input data matrix with samples as rows and features as columns.
    labels : array-like
        Group labels aligned to the rows of ``df``.
    feature_name : str
        Feature column to visualize.
    annotation_method : str or None, default=None
        Explicit statistical annotation mode. When ``None``, fall back to the
        legacy heuristic based on group count.
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
        fig, ax = plt.subplots(figsize=(6, 5))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    feature_values = df[feature_name]
    if isinstance(feature_values, pd.DataFrame):
        feature_values = feature_values.iloc[:, 0]
    plot_data = pd.DataFrame({"Group": labels_arr, "Value": feature_values.to_numpy()})

    groups = sorted(plot_data["Group"].unique())
    data_by_group = [
        pd.to_numeric(plot_data.loc[plot_data["Group"] == group, "Value"], errors="coerce")
        .dropna()
        .to_numpy()
        for group in groups
    ]

    box_colors = get_group_colors(theme, len(groups))
    _draw_r_style_boxplot(ax, data_by_group, groups, box_colors, config)

    ax.set_title(str(feature_name), fontsize=11, fontweight="bold")
    ax.set_ylabel("Value", fontsize=10)

    stat_text = _build_stat_annotation(plot_data, annotation_method=annotation_method)
    fig.tight_layout()
    if stat_text:
        fig.text(
            0.02,
            0.98,
            stat_text,
            va="top",
            ha="left",
            fontsize=9,
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": config["background"],
                "alpha": 0.95,
                "edgecolor": config["grid"],
            },
            zorder=5,
        )

    return fig
