from __future__ import annotations

import pandas as pd

from visualization.heatmap import order_samples_for_grouped_heatmap, plot_grouped_heatmap


def test_grouped_heatmap_order_uses_configured_group_order_then_unknown_groups():
    data = pd.DataFrame(
        {"F1": [1.0, 2.0, 3.0, 4.0]},
        index=["N_1", "E_1", "X_1", "E_2"],
    )
    labels = pd.Series(
        ["Normal", "Exposure", "Other", "Exposure"],
        index=data.index,
        name="Group",
    )

    ordered_data, ordered_labels = order_samples_for_grouped_heatmap(
        data,
        labels,
        group_order=["Exposure", "Normal"],
    )

    assert ordered_data.index.tolist() == ["E_1", "E_2", "N_1", "X_1"]
    assert ordered_labels.tolist() == ["Exposure", "Exposure", "Normal", "Other"]


def test_grouped_heatmap_uses_left_group_labels_without_right_legend():
    data = pd.DataFrame(
        {
            "F1": [1.0, 2.0, 3.0, 4.0],
            "F2": [4.0, 3.0, 2.0, 1.0],
        },
        index=["E_1", "E_2", "N_1", "N_2"],
    )
    labels = pd.Series(
        ["Exposure", "Exposure", "Normal", "Normal"],
        index=data.index,
        name="Group",
    )

    fig = plot_grouped_heatmap(
        data,
        labels,
        group_order=["Exposure", "Normal"],
        scale=None,
    )

    assert all(ax.get_legend() is None for ax in fig.axes)
    assert fig.axes[1].get_ylabel() == ""
    group_text = {text.get_text() for text in fig.axes[0].texts}
    assert {"Exposure", "Normal"}.issubset(group_text)
