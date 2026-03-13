"""Expose local visualization modules from the package root."""
import matplotlib
import platform
import seaborn as sns

# 設定中文字體（依平台 fallback）
if platform.system() == "Windows":
    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "SimHei", "DejaVu Sans"
    ]
elif platform.system() == "Darwin":
    matplotlib.rcParams["font.sans-serif"] = [
        "Noto Sans CJK TC", "PingFang TC", "DejaVu Sans"
    ]
else:
    matplotlib.rcParams["font.sans-serif"] = [
        "Noto Sans CJK TC", "WenQuanYi Micro Hei", "DejaVu Sans"
    ]
matplotlib.rcParams["axes.unicode_minus"] = False

# Colorblind-safe 預設色盤
COLORBLIND_PALETTE = sns.color_palette("colorblind")
matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(color=COLORBLIND_PALETTE)

from visualization.pca_plot import plot_pca_score as plot_pca_score, plot_pca_scree as plot_pca_scree, plot_pca_loading as plot_pca_loading  # noqa: E402
from visualization.pca_3d import plot_pca_3d as plot_pca_3d, pca_3d_to_html as pca_3d_to_html  # noqa: E402
from visualization.boxplot import plot_group_boxplot as plot_group_boxplot, plot_sample_boxplot as plot_sample_boxplot, plot_feature_boxplot_paired as plot_feature_boxplot_paired  # noqa: E402
from visualization.density_plot import plot_density as plot_density  # noqa: E402
from visualization.volcano_plot import plot_volcano as plot_volcano  # noqa: E402
from visualization.heatmap import plot_heatmap as plot_heatmap  # noqa: E402
from visualization.vip_plot import plot_vip as plot_vip  # noqa: E402
from visualization.norm_preview import plot_norm_comparison as plot_norm_comparison  # noqa: E402
from visualization.anova_plot import plot_anova_importance as plot_anova_importance, plot_feature_boxplot as plot_feature_boxplot  # noqa: E402
from visualization.correlation_plot import plot_correlation_heatmap as plot_correlation_heatmap, plot_correlation_network as plot_correlation_network  # noqa: E402
from visualization.roc_plot import plot_roc_curves as plot_roc_curves, plot_auc_ranking as plot_auc_ranking  # noqa: E402
from visualization.outlier_plot import plot_outlier_score as plot_outlier_score, plot_dmodx as plot_dmodx  # noqa: E402
from visualization.rf_plot import plot_rf_importance as plot_rf_importance, plot_confusion_matrix as plot_confusion_matrix  # noqa: E402

try:
    from visualization.oplsda_plot import plot_oplsda_score as plot_oplsda_score, plot_oplsda_splot as plot_oplsda_splot  # noqa: E402
except ImportError:
    pass  # pyopls not installed
