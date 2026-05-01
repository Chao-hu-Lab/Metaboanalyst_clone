from __future__ import annotations

import pandas as pd

from visualization.heatmap import order_samples_for_grouped_heatmap


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
