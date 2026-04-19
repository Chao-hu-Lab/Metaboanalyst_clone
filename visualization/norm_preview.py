"""Normalization preview charts."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy.stats import gaussian_kde

from visualization.theme import apply_publication_style, get_group_colors


def plot_norm_comparison(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    labels,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Compare distributions before and after normalization.

    Parameters
    ----------
    before_df : DataFrame
        Input data before normalization.
    after_df : DataFrame
        Input data after normalization.
    labels : array-like
        Group labels aligned to the rows of the input data.
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
        fig = plt.figure(figsize=(13.5, 8.6))
    else:
        fig.clear()

    before_df = _coerce_frame(before_df, "before_df")
    after_df = _coerce_frame(after_df, "after_df")
    labels_arr = _coerce_labels(labels)
    if len(labels_arr) != len(before_df) or len(labels_arr) != len(after_df):
        raise ValueError("labels must align with both before_df and after_df rows.")

    groups = _unique_preserve_order(labels_arr)
    if not groups:
        _draw_empty_norm_figure(
            fig, "Normalization Comparison", "No samples available."
        )
        return fig

    palette = get_group_colors(theme, len(groups))
    color_map = dict(zip(groups, palette))

    before_min, before_max = _shared_value_limits(before_df)
    after_min, after_max = _shared_value_limits(after_df)
    before_density_x = np.linspace(before_min, before_max, 240)
    after_density_x = np.linspace(after_min, after_max, 240)

    gs = fig.add_gridspec(
        2,
        2,
        height_ratios=(1.0, 1.05),
        hspace=0.30,
        wspace=0.18,
    )

    ax1 = fig.add_subplot(gs[0, 0])
    _draw_group_box(
        ax1, before_df, labels_arr, groups, color_map, "Before normalization"
    )
    ax1.set_title("Before normalization", fontsize=10.5, fontweight="bold", pad=8)

    ax2 = fig.add_subplot(gs[0, 1])
    _draw_group_box(ax2, after_df, labels_arr, groups, color_map, "After normalization")
    ax2.set_title("After normalization", fontsize=10.5, fontweight="bold", pad=8)

    ax3 = fig.add_subplot(gs[1, 0])
    _draw_density(
        ax3,
        before_df,
        labels_arr,
        groups,
        color_map,
        before_density_x,
        "Before density",
    )
    ax3.set_title("Before density", fontsize=10.5, fontweight="bold", pad=8)

    ax4 = fig.add_subplot(gs[1, 1])
    _draw_density(
        ax4,
        after_df,
        labels_arr,
        groups,
        color_map,
        after_density_x,
        "After density",
    )
    ax4.set_title("After density", fontsize=10.5, fontweight="bold", pad=8)

    handles = [
        Patch(
            facecolor=color_map[group],
            edgecolor=color_map[group],
            label=str(group),
            alpha=0.7,
        )
        for group in groups
    ]
    fig.suptitle("Normalization Comparison", fontsize=14, fontweight="bold", y=0.98)
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.0),
        ncol=min(len(handles), 4),
        frameon=False,
        fontsize=8.5,
    )
    fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.95])
    return fig


def _coerce_labels(labels) -> np.ndarray:
    if hasattr(labels, "to_numpy"):
        return np.asarray(labels.to_numpy())
    if hasattr(labels, "values"):
        return np.asarray(labels.values)
    return np.asarray(labels)


def _coerce_frame(df: pd.DataFrame, name: str) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    if df.empty:
        raise ValueError(f"{name} must not be empty.")
    return df


def _unique_preserve_order(values: np.ndarray) -> list:
    seen = set()
    ordered = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _shared_value_limits(*frames: pd.DataFrame) -> tuple[float, float]:
    values = []
    for df in frames:
        arr = df.to_numpy(dtype=float).ravel()
        arr = arr[np.isfinite(arr)]
        if arr.size:
            values.append(arr)
    if not values:
        return 0.0, 1.0

    combined = np.concatenate(values)
    if combined.size == 0:
        return 0.0, 1.0

    low, high = np.percentile(combined, [1, 99])
    if not np.isfinite(low) or not np.isfinite(high):
        low = float(np.nanmin(combined))
        high = float(np.nanmax(combined))
    if low == high:
        pad = 1.0 if low == 0 else abs(low) * 0.1
        low -= pad
        high += pad
    return float(low), float(high)


def _draw_group_box(ax, df, labels_arr, groups, color_map, title: str) -> None:
    """Draw grouped boxplots on an existing axes."""
    data_by_group = []
    colors = []
    for group in groups:
        mask = labels_arr == group
        values = df.loc[mask].to_numpy(dtype=float).ravel()
        values = values[np.isfinite(values)]
        data_by_group.append(values)
        colors.append(color_map[group])

    if not data_by_group:
        ax.set_title(title)
        ax.set_axis_off()
        return

    positions = np.arange(1, len(groups) + 1)
    boxplot = ax.boxplot(data_by_group, patch_artist=True, showfliers=False)
    for patch, color in zip(boxplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    for median in boxplot["medians"]:
        median.set_color("#2F2F2F")
        median.set_linewidth(1.0)

    ax.set_xticks(positions)
    ax.set_xticklabels([str(group)[:12] for group in groups], fontsize=8)
    ax.tick_params(axis="x", pad=2)
    ax.grid(axis="y", alpha=0.12, linewidth=0.6)
    ax.set_xlabel("Group", fontsize=9)
    ax.set_xlim(0.5, len(groups) + 0.5)
    _fold_scientific_axis_label(ax, axis="y", label="Intensity", fontsize=9.5)


def _fold_scientific_axis_label(
    ax,
    *,
    axis: str,
    label: str,
    fontsize: float | None = None,
) -> None:
    """Move visible scientific scaling into an axis label."""
    if axis == "x":
        values = np.asarray(ax.get_xlim(), dtype=float)
        formatter_axis = ax.xaxis
        set_label = ax.set_xlabel
    elif axis == "y":
        values = np.asarray(ax.get_ylim(), dtype=float)
        formatter_axis = ax.yaxis
        set_label = ax.set_ylabel
    else:
        raise ValueError("axis must be 'x' or 'y'.")

    max_abs = float(np.max(np.abs(values[np.isfinite(values)])))
    use_scientific = max_abs >= 1e4 or 0 < max_abs < 1e-3
    if not use_scientific:
        set_label(label, fontsize=fontsize)
        return

    exponent = int(np.floor(np.log10(max_abs)))
    scale = 10.0**exponent
    formatter_axis.set_major_formatter(
        FuncFormatter(lambda value, _position: f"{value / scale:g}")
    )
    formatter_axis.offsetText.set_visible(False)
    set_label(fr"{label} ($\times 10^{{{exponent}}}$)", fontsize=fontsize)


def _draw_density(ax, df, labels_arr, groups, color_map, x_range, title: str) -> None:
    """Draw grouped density curves on an existing axes."""
    all_vals = df.to_numpy(dtype=float).ravel()
    all_vals = all_vals[np.isfinite(all_vals)]
    if len(all_vals) < 2:
        ax.set_title(title)
        ax.set_axis_off()
        return

    y_max = 0.0
    density_cache = []

    for group in groups:
        mask = labels_arr == group
        values = df.loc[mask].to_numpy(dtype=float).ravel()
        values = values[np.isfinite(values)]
        if len(values) < 2:
            continue
        try:
            kde = gaussian_kde(values)
        except Exception:
            continue
        y_vals = kde(x_range)
        density_cache.append((group, y_vals))
        finite_y = y_vals[np.isfinite(y_vals)]
        if finite_y.size:
            y_max = max(y_max, float(np.nanmax(finite_y)))

    if not density_cache:
        ax.set_title(title)
        ax.set_axis_off()
        return

    for group, y_vals in density_cache:
        ax.plot(x_range, y_vals, color=color_map[group], alpha=0.85, linewidth=1.35)

    ax.set_xlabel("Intensity")
    ax.set_ylabel("Density")
    ax.grid(axis="y", alpha=0.12, linewidth=0.6)
    ax.set_xlim(float(x_range[0]), float(x_range[-1]))
    if y_max > 0:
        ax.set_ylim(0, y_max * 1.08)
    _fold_scientific_axis_label(ax, axis="x", label="Intensity")
    _fold_scientific_axis_label(ax, axis="y", label="Density")


def _draw_empty_norm_figure(fig: Figure, title: str, message: str) -> None:
    fig.clf()
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
    ax.set_axis_off()
    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.96)
