"""Expose local analysis modules from the package root."""
from analysis.pca import run_pca, PCAResult
from analysis.plsda import run_plsda, PLSDAResult
from analysis.univariate import volcano_analysis, VolcanoResult
from analysis.anova import run_anova, ANOVAResult
from analysis.clustering import compute_linkage, select_top_features
from analysis.correlation import run_correlation, CorrelationResult
from analysis.roc import run_roc_analysis, ROCResult
from analysis.outlier import run_outlier_detection, OutlierResult
from analysis.random_forest import run_random_forest, RFResult

try:
    from analysis.oplsda import run_oplsda, OPLSDAResult
except ImportError:
    pass  # pyopls not installed
