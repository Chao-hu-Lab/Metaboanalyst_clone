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

from visualization.pca_plot import plot_pca_score, plot_pca_scree, plot_pca_loading
from visualization.pca_3d import plot_pca_3d, pca_3d_to_html
from visualization.boxplot import plot_group_boxplot, plot_sample_boxplot
from visualization.density_plot import plot_density
from visualization.volcano_plot import plot_volcano
from visualization.heatmap import plot_heatmap
from visualization.vip_plot import plot_vip
from visualization.norm_preview import plot_norm_comparison
from visualization.anova_plot import plot_anova_importance, plot_feature_boxplot
from visualization.correlation_plot import plot_correlation_heatmap, plot_correlation_network
from visualization.roc_plot import plot_roc_curves, plot_auc_ranking
from visualization.outlier_plot import plot_outlier_score, plot_dmodx
from visualization.rf_plot import plot_rf_importance, plot_confusion_matrix

try:
    from visualization.oplsda_plot import plot_oplsda_score, plot_oplsda_splot
except ImportError:
    pass  # pyopls not installed
