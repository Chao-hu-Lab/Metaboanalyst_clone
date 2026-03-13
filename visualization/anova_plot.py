"""
ANOVA visualization helpers.

- Importance ranking bar chart (by -log10 p-value)
- Single feature boxplot with statistical annotation (MetaboAnalyst / R style)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from scipy.stats import f_oneway, ttest_ind

# MetaboAnalyst-style group colors (crimson, green, blue, orange, purple)
_MA_BOX_COLORS = [
    "#E41A1C",  # crimson/red
    "#4DAF4A",  # green
    "#377EB8",  # blue
    "#FF7F00",  # orange
    "#984EA3",  # purple
]


def plot_anova_importance(anova_result, top_n=25, fig=None):
    """Plot ANOVA importance ranking."""
    if fig is None:
        fig, ax = plt.subplots(figsize=(8, max(6, top_n * 0.3)))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    df = anova_result.result_df.sort_values("neg_log10p", ascending=False).head(top_n)
    df = df.iloc[::-1]

    colors = ["#e74c3c" if s else "#95a5a6" for s in df["significant"]]
    ax.barh(range(len(df)), df["neg_log10p"].values, color=colors, height=0.7)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([str(f)[:25] for f in df["Feature"]], fontsize=8)
    ax.axvline(
        x=-np.log10(anova_result.p_thresh),
        color="red",
        linestyle="--",
        alpha=0.5,
        linewidth=1,
        label=f"p = {anova_result.p_thresh}",
    )
    ax.set_xlabel("-log10(adj. p-value)")
    ax.set_title("ANOVA: Important Features")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


def _build_stat_annotation(plot_data: pd.DataFrame) -> str:
    grouped_values = []
    group_names = []
    for name, group_df in plot_data.groupby("Group"):
        values = pd.to_numeric(group_df["Value"], errors="coerce").dropna().values
        if len(values) > 0:
            grouped_values.append(values)
            group_names.append(name)

    if len(grouped_values) == 2:
        if min(len(grouped_values[0]), len(grouped_values[1])) < 2:
            return ""
        t_stat, p_val = ttest_ind(grouped_values[0], grouped_values[1], equal_var=False)
        return f"P = {p_val:.2e}\nT-test = {t_stat:.4f}"

    if len(grouped_values) >= 3:
        if any(len(v) < 2 for v in grouped_values):
            return ""
        f_stat, p_val = f_oneway(*grouped_values)
        return f"P = {p_val:.2e}\nANOVA F = {f_stat:.4f}"

    return ""


def _draw_r_style_boxplot(ax, data_by_group, group_names, group_colors):
    """
    Draw R/MetaboAnalyst-style boxplots on given axes.

    Features: filled colored boxes, gray outlines, yellow diamond mean,
    black outlier/jitter points. Matches MetaboAnalyst web output.
    """
    positions = list(range(len(group_names)))

    for i, (gname, values) in enumerate(zip(group_names, data_by_group)):
        values = np.array(values, dtype=float)
        values = values[np.isfinite(values)]
        if len(values) == 0:
            continue

        color = group_colors[i % len(group_colors)]
        bp = ax.boxplot(
            [values], positions=[positions[i]], widths=0.55,
            patch_artist=True, showmeans=False, showfliers=True,
            boxprops=dict(facecolor=color, edgecolor='#555555', linewidth=1.0),
            medianprops=dict(color='black', linewidth=1.5),
            whiskerprops=dict(color='#555555', linewidth=1.0),
            capprops=dict(color='#555555', linewidth=1.0),
            flierprops=dict(marker='o', markerfacecolor='black',
                            markeredgecolor='black', markersize=4, alpha=0.7),
        )

        # Yellow diamond for mean
        mean_val = np.mean(values)
        ax.plot(positions[i], mean_val, marker='D', color='#FFD700',
                markersize=6, markeredgecolor='#B8860B', markeredgewidth=0.7,
                zorder=4)

    ax.set_xticks(positions)
    ax.set_xticklabels(group_names, fontsize=9)

    # Clean spines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_linewidth(0.8)


def plot_feature_boxplot(df: pd.DataFrame, labels, feature_name: str, fig=None):
    """
    Plot one feature by group — R/MetaboAnalyst style with statistical annotation.

    Colored boxes per group, yellow diamond mean, black jittered data points.
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=(6, 5))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    labels_arr = labels.values if hasattr(labels, "values") else np.array(labels)
    plot_data = pd.DataFrame(
        {
            "Group": labels_arr,
            "Value": df[feature_name].values,
        }
    )

    groups = sorted(plot_data["Group"].unique())
    data_by_group = []
    for g in groups:
        vals = pd.to_numeric(
            plot_data.loc[plot_data["Group"] == g, "Value"], errors="coerce"
        ).dropna().values
        data_by_group.append(vals)

    _draw_r_style_boxplot(ax, data_by_group, groups, _MA_BOX_COLORS)

    ax.set_title(f"{feature_name}", fontsize=11, fontweight='bold')
    ax.set_ylabel("Value", fontsize=10)

    # Statistical annotation — placed in the figure margin above the plot
    stat_text = _build_stat_annotation(plot_data)
    if stat_text:
        fig.subplots_adjust(top=0.82)
        fig.text(
            0.02, 0.97, stat_text,
            va="top", ha="left", fontsize=9,
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": "#F5F5F5",
                "alpha": 0.9,
                "edgecolor": "#AAAAAA",
            },
        )
    else:
        fig.tight_layout()
    return fig
