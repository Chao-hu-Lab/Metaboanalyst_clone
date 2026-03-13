"""
OPLS-DA Visualization — MetaboAnalyst / ggplot2 Style

Score Plot: filled confidence ellipses, per-group open markers, sample labels
S-Plot: Loading scatter with top feature annotations
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse
from matplotlib.lines import Line2D
from scipy.stats import chi2

# MetaboAnalyst-style: softer colors matching ggplot2 defaults
_MA_COLORS = [
    "#F8766D",  # salmon / soft red   (ggplot2 default hue 1)
    "#00BA38",  # green               (ggplot2 default hue 2)
    "#619CFF",  # periwinkle blue     (ggplot2 default hue 3)
    "#F564E3",  # pink                (ggplot2 default hue 4)
    "#FF9900",  # orange              (ggplot2 default hue 5)
]
# Fill colors for ellipses — lighter tints
_MA_FILL_COLORS = [
    "#FFB3B0",  # light pink
    "#80DD80",  # light green
    "#A8C8FF",  # light blue
    "#F5B0EC",  # light pink-purple
    "#FFCC66",  # light orange
]
_MA_MARKERS = ["o", "^", "s", "D", "v"]


def _apply_ggplot_style(ax):
    """Apply ggplot2-like theme_gray style to axes."""
    ax.set_facecolor("#EBEBEB")
    ax.grid(True, color="white", linewidth=1.0, zorder=0)
    ax.set_axisbelow(True)
    # Thin gray border
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#CCCCCC")
        spine.set_linewidth(0.6)
    ax.tick_params(colors="#333333", labelsize=9, direction="out",
                   length=0)  # ggplot2 has no tick marks


def _confidence_ellipse(ax, x, y, color, fill_color, confidence=0.95):
    """
    Draw a filled confidence ellipse that correctly wraps the data points.

    Uses eigendecomposition of the covariance matrix with proper
    width/height/angle assignment so the ellipse major axis aligns
    with the direction of greatest variance.
    """
    if len(x) < 3:
        return

    cov = np.cov(x, y)
    if not np.all(np.isfinite(cov)) or np.linalg.det(cov) < 1e-14:
        return

    # Eigendecomposition — sort descending so [0] = largest
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    # Angle of the major axis (eigenvector for largest eigenvalue)
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))

    # Radii scaled by chi-squared quantile
    chi2_val = np.sqrt(chi2.ppf(confidence, 2))
    width = 2 * chi2_val * np.sqrt(eigenvalues[0])   # major axis
    height = 2 * chi2_val * np.sqrt(eigenvalues[1])   # minor axis

    ell = Ellipse(
        xy=(np.mean(x), np.mean(y)),
        width=width, height=height, angle=angle,
        facecolor=fill_color, edgecolor=color,
        alpha=0.25, linewidth=0.8, zorder=1,
    )
    ax.add_patch(ell)


def _mahalanobis_outliers(x, y, confidence=0.95):
    """Return boolean mask of outlier points (outside confidence ellipse)."""
    if len(x) < 3:
        return np.zeros(len(x), dtype=bool)
    pts = np.column_stack([x, y])
    mean = pts.mean(axis=0)
    cov = np.cov(x, y)
    try:
        cov_inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        return np.zeros(len(x), dtype=bool)
    diff = pts - mean
    md_sq = np.sum(diff @ cov_inv * diff, axis=1)
    threshold = chi2.ppf(confidence, 2)
    return md_sq > threshold


def plot_oplsda_score(oplsda_result, fig: Figure = None,
                      show_labels: str = "outlier", confidence: float = 0.95):
    """
    OPLS-DA Score Plot — MetaboAnalyst / ggplot2 style.

    Parameters
    ----------
    show_labels : str
        "outlier" — only label points outside the confidence ellipse (default)
        "all"     — label every sample
        "none"    — no labels
    confidence : float
        Confidence level for ellipse and outlier detection (default 0.95).
    """
    if fig is None:
        fig = plt.figure(figsize=(8, 6.5))
    fig.clf()
    ax = fig.add_subplot(111)
    _apply_ggplot_style(ax)

    score_df = oplsda_result.get_score_df()
    groups = sorted(score_df['Group'].unique())

    # Compute variance explained by each score axis
    all_t = score_df['T_predictive'].values
    all_o = score_df['T_orthogonal'].values
    total_var = np.var(all_t) + np.var(all_o)
    if total_var > 0:
        var_t = np.var(all_t) / total_var * 100
        var_o = np.var(all_o) / total_var * 100
    else:
        var_t = var_o = 0.0

    legend_handles = []
    for i, g in enumerate(groups):
        color = _MA_COLORS[i % len(_MA_COLORS)]
        fill_color = _MA_FILL_COLORS[i % len(_MA_FILL_COLORS)]
        marker = _MA_MARKERS[i % len(_MA_MARKERS)]
        mask = score_df['Group'] == g
        x = score_df.loc[mask, 'T_predictive'].values
        y = score_df.loc[mask, 'T_orthogonal'].values
        samples = score_df.loc[mask, 'Sample'].values

        # Filled confidence ellipse
        _confidence_ellipse(ax, x, y, color, fill_color, confidence)

        # Open markers (unfilled, colored edge only) — matches ggplot2 style
        ax.scatter(x, y, marker=marker, s=55,
                   facecolors='none', edgecolors=color,
                   linewidth=1.3, zorder=3)

        # Sample labels — only outliers by default
        if show_labels == "all":
            label_mask = np.ones(len(x), dtype=bool)
        elif show_labels == "outlier":
            label_mask = _mahalanobis_outliers(x, y, confidence)
        else:
            label_mask = np.zeros(len(x), dtype=bool)

        for xi, yi, name, do_label in zip(x, y, samples, label_mask):
            if do_label:
                ax.annotate(
                    str(name), (xi, yi),
                    fontsize=6.5, color="#444444",
                    xytext=(5, 2), textcoords='offset points',
                    zorder=4,
                )

        # Legend entry — open marker
        legend_handles.append(
            Line2D([0], [0], marker=marker, color='w',
                   markerfacecolor='none', markeredgecolor=color,
                   markeredgewidth=1.3, markersize=8, label=str(g))
        )

    # Axis labels — match MetaboAnalyst format
    ax.set_xlabel(f"T score [1] ( {var_t:.1f} %)", fontsize=10.5)
    ax.set_ylabel(f"Orthogonal T score [1] ( {var_o:.1f} %)", fontsize=10.5)
    ax.set_title("Scores Plot", fontsize=12, fontweight='bold', pad=10)

    # Legend — outside plot area to avoid occluding data points
    ax.legend(handles=legend_handles, bbox_to_anchor=(1.05, 1), loc='upper left',
              borderaxespad=0., fontsize=8.5, frameon=False)

    fig.tight_layout()
    return fig


def plot_oplsda_splot(oplsda_result, fig: Figure = None, top_n: int = 10):
    """
    OPLS-DA S-Plot: Loading scatter.
    Marks top important features.
    """
    if fig is None:
        fig = plt.figure(figsize=(8, 6))
    fig.clf()
    ax = fig.add_subplot(111)
    _apply_ggplot_style(ax)

    imp_df = oplsda_result.get_importance_df()
    if imp_df.empty:
        ax.set_title("OPLS-DA S-Plot (no data)")
        fig.tight_layout()
        return fig

    loadings = imp_df['Loading'].values
    importance = imp_df['Importance'].values
    features = imp_df['Feature'].values

    ax.scatter(loadings, importance, c='steelblue', s=30, alpha=0.6, zorder=2)

    top_idx = np.argsort(importance)[-top_n:]
    for idx in top_idx:
        ax.annotate(
            features[idx][:20],
            (loadings[idx], importance[idx]),
            fontsize=7, alpha=0.8,
            xytext=(5, 5), textcoords='offset points',
        )

    ax.set_xlabel("Predictive Loading p[1]", fontsize=10)
    ax.set_ylabel("|p[1]| (Importance)", fontsize=10)
    ax.set_title("OPLS-DA S-Plot", fontsize=12, fontweight='bold')
    ax.axvline(0, color='grey', linewidth=0.5, linestyle='-')
    fig.tight_layout()
    return fig
