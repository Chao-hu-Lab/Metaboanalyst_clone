"""Tests for interactive Plotly-based visualization helpers."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


try:
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import networkx  # noqa: F401

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


def _make_volcano_result():
    result_df = pd.DataFrame(
        {
            "Feature": ["F1", "F2", "F3", "F4"],
            "log2FC": [1.8, -1.4, 0.2, -0.1],
            "neg_log10p": [3.0, 2.5, 0.5, 0.2],
            "pvalue": [0.001, 0.003, 0.4, 0.7],
            "pvalue_adj": [0.002, 0.004, 0.4, 0.7],
            "significance_pvalue": [0.002, 0.004, 0.4, 0.7],
            "significant": [True, True, False, False],
        }
    )
    return SimpleNamespace(
        result_df=result_df,
        group1="Case",
        group2="Control",
        fc_thresh=2.0,
        log2_fc_thresh=1.0,
        p_thresh=0.05,
        use_fdr=True,
        fdr_method="fdr_bh",
    )


def _make_roc_result():
    single_rocs = [
        SimpleNamespace(
            feature="MarkerA",
            fpr=np.array([0.0, 0.1, 1.0]),
            tpr=np.array([0.0, 0.8, 1.0]),
            auc_score=0.92,
            optimal_cutoff=0.7,
            sensitivity=0.8,
            specificity=0.9,
        ),
        SimpleNamespace(
            feature="MarkerB",
            fpr=np.array([0.0, 0.2, 1.0]),
            tpr=np.array([0.0, 0.7, 1.0]),
            auc_score=0.81,
            optimal_cutoff=0.65,
            sensitivity=0.7,
            specificity=0.8,
        ),
    ]
    summary_df = pd.DataFrame({"Feature": ["MarkerA", "MarkerB"], "AUC": [0.92, 0.81]})
    return SimpleNamespace(
        single_rocs=single_rocs,
        multi_fpr=np.array([0.0, 0.05, 1.0]),
        multi_tpr=np.array([0.0, 0.9, 1.0]),
        multi_auc=0.96,
        summary_df=summary_df,
    )


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
def test_volcano_interactive_returns_figure():
    from visualization.volcano_plot import plot_volcano_interactive

    fig = plot_volcano_interactive(_make_volcano_result(), theme="light")
    assert fig is not None
    assert len(fig.data) >= 2


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
def test_roc_interactive_returns_figure():
    from visualization.roc_plot import plot_roc_interactive

    fig = plot_roc_interactive(_make_roc_result(), theme="light")
    assert fig is not None
    assert len(fig.data) >= 2


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
def test_plotly_to_html_returns_string():
    from visualization import plotly_to_html

    fig = go.Figure(data=go.Scatter(x=[1, 2], y=[3, 4]))
    html = plotly_to_html(fig)
    assert isinstance(html, str)
    assert "<div" in html


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
def test_theme_affects_plotly_colors():
    from visualization.volcano_plot import plot_volcano_interactive

    fig_light = plot_volcano_interactive(_make_volcano_result(), theme="light")
    fig_dark = plot_volcano_interactive(_make_volcano_result(), theme="dark")
    assert fig_light.layout.plot_bgcolor != fig_dark.layout.plot_bgcolor


@pytest.mark.skipif(not (HAS_PLOTLY and HAS_NETWORKX), reason="plotly or networkx not installed")
def test_correlation_network_interactive_returns_figure():
    from visualization.correlation_plot import plot_correlation_network_interactive

    df = pd.DataFrame(
        {
            "A": [1.0, 2.0, 3.0, 4.0],
            "B": [1.1, 2.1, 3.1, 4.1],
            "C": [4.0, 3.0, 2.0, 1.0],
        }
    )
    fig = plot_correlation_network_interactive(df, threshold=0.7, theme="light")
    assert fig is not None
