"""Expose visualization helpers from the package root."""

from __future__ import annotations

import matplotlib
import platform


if platform.system() == "Windows":
    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei",
        "Microsoft YaHei",
        "SimHei",
        "DejaVu Sans",
    ]
elif platform.system() == "Darwin":
    matplotlib.rcParams["font.sans-serif"] = [
        "Noto Sans CJK TC",
        "PingFang TC",
        "DejaVu Sans",
    ]
else:
    matplotlib.rcParams["font.sans-serif"] = [
        "Noto Sans CJK TC",
        "WenQuanYi Micro Hei",
        "DejaVu Sans",
    ]
matplotlib.rcParams["axes.unicode_minus"] = False

from visualization.anova_plot import plot_anova_importance, plot_feature_boxplot  # noqa: E402
from visualization.boxplot import (  # noqa: E402
    plot_feature_boxplot_paired,
    plot_group_boxplot,
    plot_sample_boxplot,
)
from visualization.correlation_plot import (  # noqa: E402
    plot_correlation_heatmap,
    plot_correlation_network,
    plot_correlation_network_interactive,
)
from visualization.density_plot import plot_density  # noqa: E402
from visualization.heatmap import plot_grouped_heatmap, plot_heatmap  # noqa: E402
from visualization.norm_preview import plot_norm_comparison  # noqa: E402
from visualization.outlier_plot import plot_dmodx, plot_outlier_score  # noqa: E402
from visualization.oplsda_plot import plot_oplsda_score, plot_oplsda_splot  # noqa: E402
from visualization.pca_3d import pca_3d_to_html, plot_pca_3d, plotly_to_html  # noqa: E402
from visualization.pca_plot import plot_pca_loading, plot_pca_score, plot_pca_scree  # noqa: E402
from visualization.rf_plot import plot_confusion_matrix, plot_rf_importance  # noqa: E402
from visualization.roc_plot import plot_auc_ranking, plot_roc_curves, plot_roc_interactive  # noqa: E402
from visualization.vip_plot import plot_vip  # noqa: E402
from visualization.volcano_plot import plot_volcano, plot_volcano_interactive  # noqa: E402


__all__ = [
    "plot_anova_importance",
    "plot_auc_ranking",
    "plot_confusion_matrix",
    "plot_correlation_heatmap",
    "plot_correlation_network",
    "plot_correlation_network_interactive",
    "plot_density",
    "plot_dmodx",
    "plot_feature_boxplot",
    "plot_feature_boxplot_paired",
    "plot_group_boxplot",
    "plot_grouped_heatmap",
    "plot_heatmap",
    "plot_norm_comparison",
    "plot_oplsda_score",
    "plot_oplsda_splot",
    "plot_outlier_score",
    "plot_pca_3d",
    "plot_pca_loading",
    "plot_pca_score",
    "plot_pca_scree",
    "plot_rf_importance",
    "plot_roc_curves",
    "plot_roc_interactive",
    "plot_sample_boxplot",
    "plot_vip",
    "plot_volcano",
    "plot_volcano_interactive",
    "pca_3d_to_html",
    "plotly_to_html",
]
