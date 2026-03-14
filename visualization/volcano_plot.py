"""Volcano plot visualization helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

try:
    from adjustText import adjust_text

    HAS_ADJUSTTEXT = True
except ImportError:
    HAS_ADJUSTTEXT = False

from visualization.theme import COLORS, apply_publication_style, get_group_colors


def plot_volcano(
    volcano_result,
    top_n: int = 5,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Render a static volcano plot.

    Parameters
    ----------
    volcano_result : VolcanoResult
        Result object returned by ``analysis.univariate.volcano_analysis``.
    top_n : int, default=5
        Number of top-ranked features to annotate.
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
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    result_df = volcano_result.result_df
    fc_thresh = volcano_result.fc_thresh
    p_thresh = volcano_result.p_thresh
    use_fdr = bool(getattr(volcano_result, "use_fdr", False))
    fdr_method = str(getattr(volcano_result, "fdr_method", "fdr_bh"))

    log2fc = result_df["log2FC"].to_numpy(dtype=float)
    neg_log10p = result_df["neg_log10p"].to_numpy(dtype=float)
    significant = result_df["significant"].to_numpy(dtype=bool)
    features = result_df["Feature"].astype(str).to_numpy()

    config = COLORS.get(theme, COLORS["light"])
    palette = get_group_colors(theme, 3)
    sig_label = "Significant (FDR)" if use_fdr else "Significant"
    ax.scatter(log2fc[~significant], neg_log10p[~significant], c=config["grid"], alpha=0.5, s=20, label="Not significant")
    ax.scatter(log2fc[significant], neg_log10p[significant], c=palette[0], alpha=0.75, s=30, label=sig_label)

    threshold_color = palette[1]
    log2_thresh = np.log2(fc_thresh)
    ax.axhline(-np.log10(p_thresh), ls="--", c=threshold_color, alpha=0.7, linewidth=0.9)
    ax.axvline(log2_thresh, ls="--", c=threshold_color, alpha=0.7, linewidth=0.9)
    ax.axvline(-log2_thresh, ls="--", c=threshold_color, alpha=0.7, linewidth=0.9)

    rank_col = "pvalue_adj" if use_fdr and "pvalue_adj" in result_df.columns else "pvalue"
    top_idx = np.argsort(result_df[rank_col].to_numpy(dtype=float))[:top_n]
    texts = []
    for idx in top_idx:
        name = features[idx]
        if len(name) > 20:
            name = f"{name[:18]}.."
        texts.append(ax.text(log2fc[idx], neg_log10p[idx], name, fontsize=7, ha="center"))
    if texts and HAS_ADJUSTTEXT:
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color=config["text"], lw=0.5))

    ylabel = "-log10(FDR-adjusted p-value)" if use_fdr else "-log10(p-value)"
    ax.set_xlabel("log2(Fold Change)")
    ax.set_ylabel(ylabel)
    mode_text = f"FDR={fdr_method}" if use_fdr else "raw p-value"
    ax.set_title(f"Volcano Plot ({volcano_result.group1} vs {volcano_result.group2}, {mode_text})")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return fig


def plot_volcano_interactive(
    volcano_result,
    top_n: int = 10,
    fc_threshold: float | None = None,
    pval_threshold: float | None = None,
    theme: str = "light",
) -> "plotly.graph_objects.Figure | None":
    """
    Build an interactive Plotly volcano plot.

    Parameters
    ----------
    volcano_result : VolcanoResult
        Result object returned by ``analysis.univariate.volcano_analysis``.
    top_n : int, default=10
        Number of top-ranked features to label.
    fc_threshold : float or None, default=None
        Fold-change threshold. Falls back to ``volcano_result.fc_thresh``.
    pval_threshold : float or None, default=None
        P-value threshold. Falls back to ``volcano_result.p_thresh``.
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
    palette = get_group_colors(theme, 3)
    result_df = volcano_result.result_df.copy()
    fc_threshold = fc_threshold if fc_threshold is not None else volcano_result.fc_thresh
    pval_threshold = pval_threshold if pval_threshold is not None else volcano_result.p_thresh
    log2_threshold = np.log2(fc_threshold)

    significant = result_df["significant"].to_numpy(dtype=bool)
    up_mask = significant & (result_df["log2FC"].to_numpy(dtype=float) >= 0)
    down_mask = significant & ~up_mask
    nonsig_mask = ~significant

    fig = go.Figure()
    for mask, name, color in [
        (nonsig_mask, "Not significant", config["grid"]),
        (up_mask, "Up-regulated", palette[0]),
        (down_mask, "Down-regulated", palette[1]),
    ]:
        subset = result_df.loc[mask]
        if subset.empty:
            continue
        rank_col = "pvalue_adj" if "pvalue_adj" in subset.columns else "pvalue"
        top_features = set(subset.nsmallest(min(top_n, len(subset)), rank_col)["Feature"].astype(str))
        hover_text = [
            (
                f"<b>{feature}</b><br>"
                f"log2FC: {log2_fc:.3f}<br>"
                f"-log10(p): {neg_log_p:.3f}<br>"
                f"p-value: {p_value:.3e}"
            )
            for feature, log2_fc, neg_log_p, p_value in zip(
                subset["Feature"].astype(str),
                subset["log2FC"].to_numpy(dtype=float),
                subset["neg_log10p"].to_numpy(dtype=float),
                subset["significance_pvalue"].to_numpy(dtype=float),
            )
        ]
        fig.add_trace(
            go.Scatter(
                x=subset["log2FC"],
                y=subset["neg_log10p"],
                mode="markers+text" if name != "Not significant" else "markers",
                marker=dict(color=color, size=8 if name != "Not significant" else 6, opacity=0.85 if name != "Not significant" else 0.5),
                name=name,
                text=[feature if str(feature) in top_features else "" for feature in subset["Feature"]],
                textposition="top center",
                hovertext=hover_text,
                hovertemplate="%{hovertext}<extra></extra>",
            )
        )

    fig.add_hline(y=-np.log10(pval_threshold), line_dash="dash", line_color=config["text"])
    fig.add_vline(x=log2_threshold, line_dash="dash", line_color=config["text"])
    fig.add_vline(x=-log2_threshold, line_dash="dash", line_color=config["text"])
    fig.update_layout(
        title="Volcano Plot (Interactive)",
        xaxis_title="log2(Fold Change)",
        yaxis_title="-log10(p-value)",
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
    )
    return fig
