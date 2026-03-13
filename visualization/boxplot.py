"""
Boxplot — 按組別顯示特徵分佈

Includes:
- plot_group_boxplot: overall intensity distribution by group
- plot_sample_boxplot: per-sample boxplot colored by group
- plot_feature_boxplot_paired: side-by-side Original/Normalized boxplot for a single feature
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def plot_group_boxplot(df: pd.DataFrame, labels, title="Feature Distribution", fig=None):
    """
    按組別顯示整體強度分佈 boxplot

    每個樣本計算所有特徵的 summary 後按組別繪製
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    if hasattr(labels, "values"):
        labels_arr = labels.values
    else:
        labels_arr = np.array(labels)

    plot_df = df.copy()
    plot_df["_Group"] = labels_arr
    melted = plot_df.melt(id_vars="_Group", var_name="Feature", value_name="Value")

    sns.boxplot(data=melted, x="_Group", y="Value", hue="_Group", ax=ax,
                palette="Set1", fliersize=2, linewidth=0.8, legend=False)
    ax.set_xlabel("組別")
    ax.set_ylabel("數值")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_sample_boxplot(df: pd.DataFrame, labels, title="Sample Distribution", fig=None):
    """
    每個樣本一個 boxplot，顏色依組別
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=(max(10, len(df) * 0.4), 5))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    if hasattr(labels, "values"):
        labels_arr = labels.values
    else:
        labels_arr = np.array(labels)

    groups = sorted(set(labels_arr))
    palette = dict(zip(groups, sns.color_palette("Set1", len(groups))))
    colors = [palette[g] for g in labels_arr]

    bp = ax.boxplot(
        [df.iloc[i].values for i in range(len(df))],
        patch_artist=True,
        showfliers=False,
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xticklabels(
        [str(s)[:12] for s in df.index],
        rotation=90, fontsize=7,
    )
    ax.set_ylabel("數值")
    ax.set_title(title)

    # 圖例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=palette[g], label=str(g)) for g in groups]
    ax.legend(handles=legend_elements, loc="best", fontsize=8)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# MetaboAnalyst-style group colors (reuse from anova_plot)
# ---------------------------------------------------------------------------
_MA_BOX_COLORS = [
    "#E41A1C",  # crimson/red
    "#4DAF4A",  # green
    "#377EB8",  # blue
    "#FF7F00",  # orange
    "#984EA3",  # purple
]


def _draw_r_boxplot_on_ax(ax, data_by_group, group_names, group_colors, subtitle=None):
    """R/MetaboAnalyst-style boxplot on a single axes: colored fill, gray outlines,
    yellow diamond mean, black outlier dots."""
    positions = list(range(len(group_names)))

    for i, (gname, values) in enumerate(zip(group_names, data_by_group)):
        values = np.array(values, dtype=float)
        values = values[np.isfinite(values)]
        if len(values) == 0:
            continue

        color = group_colors[i % len(group_colors)]
        ax.boxplot(
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
    if subtitle:
        ax.set_title(subtitle, fontsize=10)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_linewidth(0.8)


def plot_feature_boxplot_paired(
    df_original: pd.DataFrame,
    df_normalized: pd.DataFrame,
    labels,
    feature_name: str,
    fig=None,
):
    """
    Side-by-side boxplot: Original Conc. | Normalized Conc.

    Replicates the MetaboAnalyst / R style seen in PPT pages 15-16:
    colored boxes per group, yellow diamond mean, black jittered points,
    feature name as suptitle.

    Parameters
    ----------
    df_original : DataFrame
        Pre-normalization data (samples x features).
    df_normalized : DataFrame
        Post-normalization data (samples x features).
    labels : array-like
        Group labels aligned to data rows.
    feature_name : str
        Column name to plot.
    fig : Figure or None
    """
    if fig is None:
        fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(10, 5))
    else:
        fig.clear()
        ax_l = fig.add_subplot(121)
        ax_r = fig.add_subplot(122)

    labels_arr = labels.values if hasattr(labels, "values") else np.array(labels)
    groups = sorted(set(labels_arr))

    for ax, df, subtitle in [
        (ax_l, df_original, "Original Conc."),
        (ax_r, df_normalized, "Normalized Conc."),
    ]:
        data_by_group = []
        for g in groups:
            mask = labels_arr == g
            vals = pd.to_numeric(df.loc[mask, feature_name], errors="coerce").dropna().values
            data_by_group.append(vals)
        _draw_r_boxplot_on_ax(ax, data_by_group, groups, _MA_BOX_COLORS, subtitle=subtitle)

    fig.suptitle(f"{feature_name}", fontsize=13, fontweight='bold', y=1.02)
    fig.tight_layout()
    return fig
