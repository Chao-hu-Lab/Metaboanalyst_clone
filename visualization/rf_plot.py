"""Random Forest visualizations."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.figure import Figure

from visualization.theme import apply_publication_style, get_group_colors


_INVALID_LABELS = {"", "na", "nan", "none", "null"}


def _safe_feature_label(name, idx: int) -> str:
    if name is None:
        return f"Feature_{idx + 1}"
    text = str(name).strip()
    if text.lower() in _INVALID_LABELS:
        return f"Feature_{idx + 1}"
    return text


def plot_rf_importance(
    rf_result,
    top_n: int = 25,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot the top Random Forest feature importances.

    Parameters
    ----------
    rf_result : RFResult
        Result object returned by ``analysis.random_forest.run_random_forest``.
    top_n : int, default=25
        Number of features to display.
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
    imp_df = rf_result.feature_importance.head(top_n).copy()
    if "Importance" not in imp_df.columns or "Feature" not in imp_df.columns:
        raise ValueError(
            "rf_result.feature_importance must contain 'Feature' and 'Importance' columns."
        )

    if fig is None:
        fig = plt.figure(figsize=(8, max(4, max(len(imp_df), 1) * 0.35)))
    fig.clf()
    ax = fig.add_subplot(111)

    importances = imp_df["Importance"].fillna(0.0).to_numpy(dtype=float)
    feature_labels = [
        _safe_feature_label(name, idx) for idx, name in enumerate(imp_df["Feature"])
    ]
    palette = get_group_colors(theme, 3)
    max_importance = float(np.nanmax(importances)) if len(importances) else 0.0
    if not np.isfinite(max_importance) or max_importance <= 0:
        colors = [palette[1]] * len(importances)
    else:
        colors = [
            palette[0]
            if value >= max_importance * 0.66
            else palette[1]
            if value >= max_importance * 0.33
            else palette[2]
            for value in importances
        ]

    ax.barh(range(len(imp_df)), importances, color=colors)
    ax.set_yticks(range(len(imp_df)))
    ax.set_yticklabels(feature_labels, fontsize=8)
    ax.set_xlabel("Mean Decrease Impurity (Gini)")
    ax.set_title(
        "Random Forest Feature Importance\n"
        f"OOB Acc={rf_result.oob_accuracy:.3f} | "
        f"CV Acc={rf_result.cv_accuracy:.3f} +/- {rf_result.cv_std:.3f}"
    )
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def plot_confusion_matrix(
    rf_result,
    theme: str = "light",
    fig: Figure | None = None,
    vmax: int | None = None,
) -> Figure:
    """
    Plot the Random Forest confusion matrix.

    Parameters
    ----------
    rf_result : RFResult
        Result object returned by ``analysis.random_forest.run_random_forest``.
    theme : str, default="light"
        Visualization theme name.
    fig : Figure or None, default=None
        Existing figure to reuse. When ``None``, a new figure is created.
    vmax : int or None, default=None
        Upper bound of the color scale. When provided, all confusion matrices
        in a batch share the same scale for direct visual comparison.

    Returns
    -------
    Figure
        The rendered matplotlib figure.
    """
    apply_publication_style(theme)
    if fig is None:
        fig = plt.figure(figsize=(6, 5))
    fig.clf()
    ax = fig.add_subplot(111)

    cm = rf_result.confusion_mat
    class_names = rf_result.class_names
    cmap = sns.light_palette(get_group_colors(theme, 1)[0], as_cmap=True)

    heatmap_kwargs: dict = dict(
        annot=True,
        fmt="d",
        cmap=cmap,
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
        linewidths=0.5,
        vmin=0,
    )
    if vmax is not None:
        heatmap_kwargs["vmax"] = vmax

    sns.heatmap(cm, **heatmap_kwargs)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix (CV)\nAccuracy {rf_result.cv_accuracy:.1%}")
    fig.tight_layout()
    return fig
