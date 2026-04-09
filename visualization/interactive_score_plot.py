"""Shared Plotly builders for interactive score plots."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy.stats import chi2

from visualization.theme import COLORS, get_group_colors

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure
else:
    PlotlyFigure = Any

try:
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def _label_mask(coords: np.ndarray, mode: str, confidence: float) -> np.ndarray:
    n_points = len(coords)
    if mode == "all":
        return np.ones(n_points, dtype=bool)
    if mode == "none" or n_points == 0:
        return np.zeros(n_points, dtype=bool)

    if n_points < 3:
        mask = np.zeros(n_points, dtype=bool)
        mask[int(np.argmax(np.linalg.norm(coords - coords.mean(axis=0), axis=1)))] = True
        return mask

    centered = coords - coords.mean(axis=0)
    cov = np.cov(centered, rowvar=False)
    if not np.all(np.isfinite(cov)) or np.linalg.det(cov) <= 1e-12:
        distances = np.linalg.norm(centered, axis=1)
        threshold = np.quantile(distances, confidence)
        return distances >= threshold

    inv_cov = np.linalg.pinv(cov)
    md2 = np.einsum("ij,jk,ik->i", centered, inv_cov, centered)
    threshold = float(chi2.ppf(confidence, df=2))
    return md2 >= threshold


def _confidence_ellipse_points(coords: np.ndarray, confidence: float) -> tuple[np.ndarray, np.ndarray] | None:
    if len(coords) < 3:
        return None
    centered = coords - coords.mean(axis=0)
    cov = np.cov(centered, rowvar=False)
    if not np.all(np.isfinite(cov)) or np.linalg.det(cov) <= 1e-12:
        return None

    eig_vals, eig_vecs = np.linalg.eigh(cov)
    eig_vals = np.maximum(eig_vals, 0.0)
    order = eig_vals.argsort()[::-1]
    eig_vals = eig_vals[order]
    eig_vecs = eig_vecs[:, order]

    angles = np.linspace(0.0, 2.0 * np.pi, 120)
    unit_circle = np.column_stack((np.cos(angles), np.sin(angles)))
    scale = np.sqrt(chi2.ppf(confidence, 2))
    transform = eig_vecs @ np.diag(np.sqrt(eig_vals) * scale)
    ellipse = unit_circle @ transform.T
    ellipse += coords.mean(axis=0)
    return ellipse[:, 0], ellipse[:, 1]


def build_interactive_score_plot(
    score_df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    sample_col: str,
    group_col: str,
    x_label: str,
    y_label: str,
    title: str,
    show_labels: str = "outlier",
    confidence: float = 0.95,
    theme: str = "light",
) -> PlotlyFigure | None:
    """Build an interactive Plotly score chart with per-group traces."""
    if not HAS_PLOTLY:
        return None

    config = COLORS.get(theme, COLORS["light"])
    groups = sorted(score_df[group_col].astype(str).unique().tolist())
    colors = get_group_colors(theme, len(groups))

    fig = go.Figure()
    for idx, group in enumerate(groups):
        subset = score_df.loc[score_df[group_col].astype(str) == group].copy()
        coords = subset[[x_col, y_col]].to_numpy(dtype=float)
        ellipse = _confidence_ellipse_points(coords, confidence)
        label_mask = _label_mask(coords, show_labels, confidence)
        label_text = [
            str(sample) if is_visible else ""
            for sample, is_visible in zip(subset[sample_col].astype(str), label_mask)
        ]
        hover_text = [
            (
                f"<b>{sample}</b><br>"
                f"{group_col}: {group}<br>"
                f"{x_label}: {x_val:.3f}<br>"
                f"{y_label}: {y_val:.3f}"
            )
            for sample, x_val, y_val in zip(
                subset[sample_col].astype(str),
                subset[x_col].to_numpy(dtype=float),
                subset[y_col].to_numpy(dtype=float),
            )
        ]

        if ellipse is not None:
            fig.add_trace(
                go.Scatter(
                    x=ellipse[0],
                    y=ellipse[1],
                    mode="lines",
                    line=dict(color=colors[idx], width=1.4, dash="dash"),
                    name=f"{group} 95% CI",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scatter(
                x=subset[x_col],
                y=subset[y_col],
                mode="markers+text" if any(label_text) else "markers",
                name=str(group),
                text=label_text,
                textposition="top center",
                customdata=subset[sample_col].astype(str).tolist(),
                hovertext=hover_text,
                hovertemplate="%{hovertext}<extra></extra>",
                marker=dict(
                    size=8.5,
                    color=colors[idx],
                    opacity=0.9,
                    line=dict(color=config["background"], width=0.7),
                ),
                selected=dict(marker=dict(size=11, color=colors[idx], opacity=1.0)),
                unselected=dict(marker=dict(opacity=0.55)),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
        hovermode="closest",
        dragmode="zoom",
        margin=dict(l=50, r=20, t=50, b=45),
        legend=dict(title=group_col),
    )
    fig.add_hline(y=0.0, line_dash="dot", line_color=config["grid"])
    fig.add_vline(x=0.0, line_dash="dot", line_color=config["grid"])
    return fig
