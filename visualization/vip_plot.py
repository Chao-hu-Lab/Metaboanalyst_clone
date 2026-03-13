"""
VIP Score Plot — MetaboAnalyst Style

Lollipop chart (horizontal lines + dots) with group-level
expression heatmap color boxes on the right side, plus a
continuous vertical colorbar gradient (Blue → Red).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
from matplotlib.colorbar import ColorbarBase


# MetaboAnalyst VIP color map: deep blue → light blue → white → pink → deep red
_VIP_CMAP = LinearSegmentedColormap.from_list(
    "ma_vip", ["#1F4E79", "#6BAED6", "#FFFFFF", "#E06666", "#B22222"]
)


def _format_mzrt_label(name: str) -> str:
    """Reformat 'mz/rt' feature name: Mz to 4 dp, RT to 2 dp.

    Falls back to the original string if the name does not follow the
    '<float>/<float>' pattern (e.g. metabolite names or plain IDs).
    """
    parts = str(name).split("/")
    if len(parts) == 2:
        try:
            mz = float(parts[0])
            rt = float(parts[1])
            return f"{mz:.4f}/{rt:.2f}"
        except ValueError:
            pass
    return name


def plot_vip(plsda_result, top_n: int = 25,
             data: pd.DataFrame = None, labels=None,
             fig=None):
    """
    Plot VIP Score lollipop chart with optional group expression heatmap.

    Parameters
    ----------
    plsda_result : PLSDAResult
        Must have get_vip_df() method.
    top_n : int
        Number of top features to display.
    data : DataFrame, optional
        Original data matrix (samples x features) for computing group means.
        If provided with labels, heatmap color boxes are drawn on the right.
    labels : array-like, optional
        Group labels aligned to data rows.
    fig : Figure or None
    """
    has_heatmap = data is not None and labels is not None

    vip_df = plsda_result.get_vip_df().head(top_n)
    vip_df = vip_df.iloc[::-1]  # reverse so highest VIP is at top

    n = len(vip_df)
    vip_vals = vip_df["VIP"].values
    feature_names = [str(f) for f in vip_df["Feature"]]
    y_pos = np.arange(n)

    # ── Figure layout ───────────────────────────────────────────────
    if fig is None:
        if has_heatmap:
            fig = plt.figure(figsize=(10, max(6, top_n * 0.32)))
        else:
            fig = plt.figure(figsize=(8, max(6, top_n * 0.32)))
    else:
        fig.clear()

    if has_heatmap:
        # Main lollipop axes + compact heatmap + thin colorbar
        ax = fig.add_axes([0.12, 0.08, 0.65, 0.87])        # lollipop (wider)
        ax_heat = fig.add_axes([0.80, 0.08, 0.06, 0.87])   # heatmap boxes (narrow)
        ax_cb = fig.add_axes([0.88, 0.25, 0.015, 0.45])    # colorbar (thin)
    else:
        ax = fig.add_subplot(111)

    # ── Lollipop chart ──────────────────────────────────────────────
    # Horizontal grid lines (behind data)
    ax.set_axisbelow(True)
    ax.grid(True, axis='y', color='#DDDDDD', linewidth=0.5, zorder=0)

    # Lines from left edge to VIP value
    for y, v in zip(y_pos, vip_vals):
        ax.hlines(y, xmin=0, xmax=v, color='#888888', linewidth=1.0, zorder=2)

    # Dots at VIP values
    ax.scatter(vip_vals, y_pos, c='#444444', s=45, zorder=3, edgecolors='none')

    ax.set_yticks(y_pos)
    formatted_labels = [_format_mzrt_label(f) for f in feature_names]
    ax.set_yticklabels(formatted_labels, fontsize=8)
    ax.set_xlabel("VIP scores", fontsize=10.5)
    ax.set_xlim(left=0)
    ax.set_ylim(-0.5, n - 0.5)

    # Clean spines — only left and bottom
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_linewidth(0.8)
    ax.tick_params(axis='both', labelsize=8, direction='out')

    # ── Heatmap color boxes ─────────────────────────────────────────
    if has_heatmap:
        labels_arr = labels.values if hasattr(labels, "values") else np.array(labels)
        groups = sorted(set(labels_arr))
        n_groups = len(groups)

        features_in_order = list(vip_df["Feature"])
        valid_features = [f for f in features_in_order if f in data.columns]

        if valid_features:
            group_means = pd.DataFrame(
                index=valid_features, columns=groups, dtype=float
            )
            for g in groups:
                mask = labels_arr == g
                group_means[g] = data.loc[mask, valid_features].mean(axis=0).values

            # Row-wise z-score for color mapping
            row_mean = group_means.mean(axis=1)
            row_std = group_means.std(axis=1).replace(0, 1)
            z_scores = group_means.sub(row_mean, axis=0).div(row_std, axis=0)

            vmin, vmax = -2.0, 2.0
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

            # Draw color boxes in ax_heat
            ax_heat.set_xlim(0, n_groups)
            ax_heat.set_ylim(-0.5, n - 0.5)

            box_w = 0.85
            for gi, g in enumerate(groups):
                for fi, feat in enumerate(features_in_order):
                    if feat in z_scores.index:
                        z_val = np.clip(z_scores.loc[feat, g], vmin, vmax)
                        fc = _VIP_CMAP(norm(z_val))
                    else:
                        fc = '#CCCCCC'
                    rect = Rectangle(
                        (gi + (1 - box_w) / 2, fi - 0.35), box_w, 0.7,
                        facecolor=fc, edgecolor='#555555', linewidth=0.4,
                        zorder=2,
                    )
                    ax_heat.add_patch(rect)

            # Group labels on top — use tick mechanism for precise alignment
            ax_heat.set_xticks([gi + 0.5 for gi in range(n_groups)])
            ax_heat.set_xticklabels(groups, fontsize=7.5, fontweight='bold')
            ax_heat.xaxis.set_ticks_position('top')
            ax_heat.xaxis.set_label_position('top')
            # Rotate with proper alignment for top ticks
            for tick_label in ax_heat.get_xticklabels():
                tick_label.set_rotation(45)
                tick_label.set_ha('left')
                tick_label.set_rotation_mode('anchor')
            ax_heat.set_yticks([])

            # Hide all spines on heatmap axes
            for spine in ax_heat.spines.values():
                spine.set_visible(False)
            ax_heat.tick_params(axis='x', length=0, pad=2)
            ax_heat.tick_params(axis='y', length=0)

            # ── Continuous colorbar ─────────────────────────────────
            cb = ColorbarBase(
                ax_cb, cmap=_VIP_CMAP, norm=norm,
                orientation='vertical',
            )
            ax_cb.set_ylabel("")
            ax_cb.tick_params(labelsize=0, length=0)
            # Add "High" / "Low" text labels
            ax_cb.text(
                1.6, 1.0, "High", transform=ax_cb.transAxes,
                fontsize=8, fontweight='bold', va='top', color='#B22222',
            )
            ax_cb.text(
                1.6, 0.0, "Low", transform=ax_cb.transAxes,
                fontsize=8, fontweight='bold', va='bottom', color='#1F4E79',
            )
            # Thin border on colorbar
            for spine in ax_cb.spines.values():
                spine.set_linewidth(0.5)

    return fig
