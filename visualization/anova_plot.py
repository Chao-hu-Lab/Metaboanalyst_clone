"""
ANOVA visualization helpers.

- Importance ranking bar chart (by -log10 p-value)
- Single feature boxplot with statistical annotation
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import f_oneway, ttest_ind


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
    for _, group_df in plot_data.groupby("Group"):
        values = pd.to_numeric(group_df["Value"], errors="coerce").dropna().values
        if len(values) > 0:
            grouped_values.append(values)

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


def plot_feature_boxplot(df: pd.DataFrame, labels, feature_name: str, fig=None):
    """Plot one feature by group and annotate t-test / p-value (or ANOVA p-value)."""
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

    sns.boxplot(
        data=plot_data,
        x="Group",
        y="Value",
        hue="Group",
        palette="Set1",
        ax=ax,
        legend=False,
    )
    sns.stripplot(
        data=plot_data,
        x="Group",
        y="Value",
        color="black",
        alpha=0.4,
        size=4,
        ax=ax,
    )

    stat_text = _build_stat_annotation(plot_data)
    if stat_text:
        ax.text(
            0.02,
            0.98,
            stat_text,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "alpha": 0.75,
                "edgecolor": "#888888",
            },
        )

    ax.set_title(f"Feature: {feature_name}", fontsize=10)
    ax.set_xlabel("Group")
    ax.set_ylabel("Value")
    fig.tight_layout()
    return fig
