"""VIP score plot helpers."""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle

from visualization.theme import COLORS, apply_publication_style, get_group_colors


_VIP_CMAP = LinearSegmentedColormap.from_list(
    "ma_vip", ["#1F4E79", "#6BAED6", "#FFFFFF", "#E06666", "#B22222"]
)


def _format_mzrt_label(name: str) -> str:
    """Format ``mz/rt`` feature names with consistent precision."""
    parts = str(name).split("/")
    if len(parts) == 2:
        try:
            mz = float(parts[0])
            rt = float(parts[1])
            return f"{mz:.4f}/{rt:.2f}"
        except ValueError:
            pass
    return str(name)


def plot_vip(
    plsda_result,
    top_n: int = 25,
    data: pd.DataFrame | None = None,
    labels=None,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot VIP scores as a lollipop chart with optional group mean heatmap.

    Parameters
    ----------
    plsda_result : PLSDAResult
        Result object returned by ``analysis.plsda.run_plsda``.
    top_n : int, default=25
        Number of top features to display.
    data : DataFrame or None, default=None
        Original data matrix used to compute group mean heatmap values.
    labels : array-like or None, default=None
        Group labels aligned to ``data``.
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
    palette = get_group_colors(theme, 3)
    has_heatmap = data is not None and labels is not None

    vip_df = plsda_result.get_vip_df().head(top_n).iloc[::-1]
    n_rows = len(vip_df)
    vip_vals = vip_df["VIP"].to_numpy(dtype=float)
    feature_names = [str(feature) for feature in vip_df["Feature"]]
    y_pos = np.arange(n_rows)

    if fig is None:
        fig = plt.figure(figsize=(10 if has_heatmap else 8, max(6, top_n * 0.32)))
    else:
        fig.clear()

    if has_heatmap:
        gs = GridSpec(
            1, 3, figure=fig,
            width_ratios=[10, 1.2, 0.3],
            wspace=0.08,
        )
        ax = fig.add_subplot(gs[0, 0])
        ax_heat = fig.add_subplot(gs[0, 1])
        ax_cb = fig.add_subplot(gs[0, 2])
    else:
        ax = fig.add_subplot(111)
        ax_heat = None
        ax_cb = None

    ax.set_axisbelow(True)
    ax.grid(True, axis="y", color=config["grid"], linewidth=0.5, zorder=0)

    for y_idx, value in zip(y_pos, vip_vals):
        ax.hlines(y_idx, xmin=0, xmax=value, color=config["grid"], linewidth=1.0, zorder=2)

    ax.scatter(vip_vals, y_pos, c=palette[0], s=45, zorder=3, edgecolors="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels([_format_mzrt_label(name) for name in feature_names], fontsize=8)
    ax.set_xlabel("VIP scores", fontsize=10.5)
    ax.set_xlim(left=0)
    ax.set_ylim(-0.5, max(n_rows - 0.5, 0.5))

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", labelsize=8, direction="out")

    if has_heatmap and ax_heat is not None and ax_cb is not None:
        labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
        groups = sorted(set(labels_arr))
        features_in_order = list(vip_df["Feature"])
        valid_features = [feature for feature in features_in_order if feature in data.columns]

        if valid_features:
            group_means = pd.DataFrame(index=valid_features, columns=groups, dtype=float)
            for group in groups:
                mask = labels_arr == group
                group_means[group] = data.loc[mask, valid_features].mean(axis=0).values

            row_mean = group_means.mean(axis=1)
            row_std = group_means.std(axis=1).replace(0, 1)
            z_scores = group_means.sub(row_mean, axis=0).div(row_std, axis=0)

            vmin, vmax = -2.0, 2.0
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

            ax_heat.set_xlim(0, len(groups))
            ax_heat.set_ylim(-0.5, max(n_rows - 0.5, 0.5))
            box_width = 0.85
            for group_idx, group in enumerate(groups):
                for feature_idx, feature in enumerate(features_in_order):
                    if feature in z_scores.index:
                        z_val = float(np.clip(z_scores.loc[feature, group], vmin, vmax))
                        facecolor = _VIP_CMAP(norm(z_val))
                    else:
                        facecolor = config["grid"]
                    ax_heat.add_patch(
                        Rectangle(
                            (group_idx + (1 - box_width) / 2, feature_idx - 0.35),
                            box_width,
                            0.7,
                            facecolor=facecolor,
                            edgecolor=config["axes_line"],
                            linewidth=0.4,
                            zorder=2,
                        )
                    )

            ax_heat.set_xticks([group_idx + 0.5 for group_idx in range(len(groups))])
            ax_heat.set_xticklabels(groups, fontsize=7.5, fontweight="bold")
            ax_heat.xaxis.set_ticks_position("top")
            ax_heat.xaxis.set_label_position("top")
            for tick_label in ax_heat.get_xticklabels():
                tick_label.set_rotation(45)
                tick_label.set_ha("left")
                tick_label.set_rotation_mode("anchor")
            ax_heat.set_yticks([])
            for spine in ax_heat.spines.values():
                spine.set_visible(False)
            ax_heat.tick_params(axis="x", length=0, pad=2)
            ax_heat.tick_params(axis="y", length=0)

            ColorbarBase(ax_cb, cmap=_VIP_CMAP, norm=norm, orientation="vertical")
            ax_cb.set_ylabel("")
            ax_cb.tick_params(labelsize=0, length=0)
            ax_cb.text(
                1.6,
                1.0,
                "High",
                transform=ax_cb.transAxes,
                fontsize=8,
                fontweight="bold",
                va="top",
                color="#B22222",
            )
            ax_cb.text(
                1.6,
                0.0,
                "Low",
                transform=ax_cb.transAxes,
                fontsize=8,
                fontweight="bold",
                va="bottom",
                color="#1F4E79",
            )
            for spine in ax_cb.spines.values():
                spine.set_linewidth(0.5)

    if not has_heatmap:
        fig.tight_layout()
    return fig
