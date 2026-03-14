"""Interactive PCA helpers."""

from __future__ import annotations

import numpy as np

from visualization.theme import COLORS, get_group_colors

try:
    import plotly.graph_objects as go
    import plotly.io as pio

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def plot_pca_3d(
    pca_result,
    pc_x: int = 0,
    pc_y: int = 1,
    pc_z: int = 2,
    theme: str = "light",
) -> "plotly.graph_objects.Figure | None":
    """
    Plot a 3D PCA score chart using Plotly.

    Parameters
    ----------
    pca_result : PCAResult
        Result object returned by ``analysis.pca.run_pca``.
    pc_x : int, default=0
        Zero-based component index used on the x-axis.
    pc_y : int, default=1
        Zero-based component index used on the y-axis.
    pc_z : int, default=2
        Zero-based component index used on the z-axis.
    theme : str, default="light"
        Visualization theme name.

    Returns
    -------
    plotly.graph_objects.Figure or None
        Plotly figure when Plotly is installed, otherwise ``None``.
    """
    if not HAS_PLOTLY:
        return None

    scores = pca_result.scores
    labels = pca_result.labels
    var_ratio = pca_result.explained_variance_ratio
    sample_names = pca_result.sample_names
    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    groups = sorted(set(labels_arr))
    colors = get_group_colors(theme, len(groups))
    config = COLORS.get(theme, COLORS["light"])

    fig = go.Figure()
    for idx, group in enumerate(groups):
        mask = labels_arr == group
        names = [sample_names[row_idx] for row_idx in range(len(mask)) if mask[row_idx]]
        fig.add_trace(
            go.Scatter3d(
                x=scores[mask, pc_x],
                y=scores[mask, pc_y],
                z=scores[mask, pc_z],
                mode="markers",
                marker=dict(
                    size=6,
                    color=colors[idx],
                    opacity=0.85,
                    line=dict(width=0.5, color=config["background"]),
                ),
                name=str(group),
                text=names,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"PC{pc_x + 1}: %{{x:.3f}}<br>"
                    f"PC{pc_y + 1}: %{{y:.3f}}<br>"
                    f"PC{pc_z + 1}: %{{z:.3f}}<br>"
                    f"<extra>{group}</extra>"
                ),
            )
        )

    fig.update_layout(
        title="3D PCA Score Plot",
        scene=dict(
            xaxis_title=f"PC{pc_x + 1} ({var_ratio[pc_x] * 100:.1f}%)",
            yaxis_title=f"PC{pc_y + 1} ({var_ratio[pc_y] * 100:.1f}%)",
            zaxis_title=f"PC{pc_z + 1} ({var_ratio[pc_z] * 100:.1f}%)",
            bgcolor=config["background"],
        ),
        legend=dict(title="Group"),
        width=800,
        height=600,
        margin=dict(l=0, r=0, b=0, t=40),
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
    )
    return fig


def plotly_to_html(fig, include_plotlyjs: str = "cdn") -> str:
    """
    Convert a Plotly figure into an embeddable HTML fragment.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Plotly figure to serialize.
    include_plotlyjs : str, default="cdn"
        Strategy passed through to ``plotly.io.to_html``.

    Returns
    -------
    str
        HTML snippet containing the interactive chart.
    """
    if not HAS_PLOTLY or fig is None:
        return "<p>Plotly is not installed.</p>"
    return pio.to_html(fig, full_html=False, include_plotlyjs=include_plotlyjs)


def pca_3d_to_html(fig) -> str:
    """
    Convert a PCA Plotly figure into a standalone HTML document.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure or None
        Plotly figure returned by :func:`plot_pca_3d`.

    Returns
    -------
    str
        Standalone HTML document.
    """
    if not HAS_PLOTLY or fig is None:
        return "<p>Plotly is not installed: pip install plotly</p>"
    return pio.to_html(fig, include_plotlyjs="cdn", full_html=True)
