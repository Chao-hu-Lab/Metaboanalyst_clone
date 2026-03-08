"""Map legacy ``ms_core.visualization`` imports to local visualization modules."""

from importlib import import_module
import sys


_ALIASES = {
    "anova_plot": "visualization.anova_plot",
    "boxplot": "visualization.boxplot",
    "correlation_plot": "visualization.correlation_plot",
    "density_plot": "visualization.density_plot",
    "heatmap": "visualization.heatmap",
    "norm_preview": "visualization.norm_preview",
    "oplsda_plot": "visualization.oplsda_plot",
    "outlier_plot": "visualization.outlier_plot",
    "pca_3d": "visualization.pca_3d",
    "pca_plot": "visualization.pca_plot",
    "rf_plot": "visualization.rf_plot",
    "roc_plot": "visualization.roc_plot",
    "vip_plot": "visualization.vip_plot",
    "volcano_plot": "visualization.volcano_plot",
}


for legacy_name, target_name in _ALIASES.items():
    sys.modules[f"{__name__}.{legacy_name}"] = import_module(target_name)
