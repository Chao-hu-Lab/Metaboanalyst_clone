"""Correlation visualizations."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from typing import TYPE_CHECKING, Any

from visualization.theme import COLORS, apply_publication_style, get_group_colors

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure
else:
    PlotlyFigure = Any


def plot_correlation_heatmap(
    corr_result,
    cmap: str = "RdBu_r",
    annot: bool = False,
    max_features: int = 30,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot a correlation heatmap for the selected result object.

    Parameters
    ----------
    corr_result : CorrelationResult
        Result object returned by ``analysis.correlation.run_correlation``.
    cmap : str, default="RdBu_r"
        Matplotlib colormap name.
    annot : bool, default=False
        Whether to annotate cell values.
    max_features : int, default=30
        Maximum number of features to render.
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
    corr = corr_result.corr_matrix
    if corr.shape[0] > max_features:
        corr = corr.iloc[:max_features, :max_features]

    if fig is None:
        fig = plt.figure(figsize=(10, 8))
    fig.clf()
    ax = fig.add_subplot(111)

    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        center=0,
        square=True,
        linewidths=0.5,
        annot=annot,
        fmt=".2f" if annot else "",
        ax=ax,
        cbar_kws={"shrink": 0.8},
        vmin=-1,
        vmax=1,
    )
    method_name = str(corr_result.method).capitalize()
    ax.set_title(f"{method_name} Correlation Heatmap (Top {corr.shape[0]} Features)")
    fig.tight_layout()
    return fig


def plot_correlation_network(
    corr_result,
    threshold: float = 0.8,
    top_n: int = 30,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the strongest correlated feature pairs as a ranked bar chart.

    Parameters
    ----------
    corr_result : CorrelationResult
        Result object returned by ``analysis.correlation.run_correlation``.
    threshold : float, default=0.8
        Absolute correlation threshold shown in the title and empty state.
    top_n : int, default=30
        Number of pairs to display.
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
    pairs = corr_result.high_corr_pairs

    if fig is None:
        fig = plt.figure(figsize=(8, max(4, max(len(pairs), 1) * 0.35)))
    fig.clf()
    ax = fig.add_subplot(111)

    if len(pairs) == 0:
        ax.text(
            0.5,
            0.5,
            f"No correlation pairs found with |r| >= {threshold}.",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=14,
        )
        ax.set_axis_off()
        return fig

    plot_df = pairs.head(top_n).copy()
    plot_df["Label"] = plot_df["Feature_1"].astype(str) + " vs " + plot_df["Feature_2"].astype(str)
    palette = get_group_colors(theme, 2)
    colors = [palette[0] if value > 0 else palette[1] for value in plot_df["Correlation"]]

    ax.barh(range(len(plot_df)), plot_df["Correlation"].values, color=colors)
    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels(plot_df["Label"].values, fontsize=8)
    ax.set_xlabel("Correlation")
    ax.set_title(f"Correlation Network Summary (|r| >= {threshold})")
    ax.axvline(x=0, color=COLORS.get(theme, COLORS["light"])["text"], linewidth=0.8)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def plot_correlation_network_interactive(
    df: pd.DataFrame,
    threshold: float = 0.7,
    theme: str = "light",
) -> PlotlyFigure | None:
    """
    Build an interactive correlation network using Plotly.

    Parameters
    ----------
    df : DataFrame
        Input data matrix with features as columns.
    threshold : float, default=0.7
        Minimum absolute correlation required to create an edge.
    theme : str, default="light"
        Visualization theme name.

    Returns
    -------
    plotly.graph_objects.Figure or None
        Plotly figure when Plotly is installed, otherwise ``None``.
    """
    try:
        import plotly.graph_objects as go
        import networkx as nx
    except ImportError:
        return None

    config = COLORS.get(theme, COLORS["light"])
    corr = df.corr()
    graph = nx.Graph()
    for row_idx in range(len(corr)):
        for col_idx in range(row_idx + 1, len(corr)):
            weight = float(corr.iloc[row_idx, col_idx])
            if abs(weight) >= threshold:
                graph.add_edge(corr.index[row_idx], corr.columns[col_idx], weight=weight)

    fig = go.Figure()
    if graph.number_of_nodes() == 0:
        fig.update_layout(
            title="Correlation Network (Interactive)",
            annotations=[
                dict(
                    text=f"No correlation pairs found with |r| >= {threshold}.",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color=config["text"]),
                )
            ],
            plot_bgcolor=config["background"],
            paper_bgcolor=config["background"],
            font=dict(color=config["text"]),
        )
        return fig

    positions = nx.spring_layout(graph, seed=42)
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color=config["grid"]),
            hoverinfo="none",
            showlegend=False,
        )
    )

    node_x = [positions[node][0] for node in graph.nodes()]
    node_y = [positions[node][1] for node in graph.nodes()]
    node_text = [
        f"{node}<br>Connections: {graph.degree(node)}"
        for node in graph.nodes()
    ]
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=11,
                color=get_group_colors(theme, 1)[0],
                line=dict(width=1, color=config["text"]),
            ),
            text=list(graph.nodes()),
            textposition="top center",
            hovertext=node_text,
            hoverinfo="text",
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Correlation Network (Interactive)",
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    return fig
