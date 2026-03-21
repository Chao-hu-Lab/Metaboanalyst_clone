"""Expose local analysis modules from the package root."""
from analysis.pca import run_pca as run_pca, PCAResult as PCAResult
from analysis.plsda import run_plsda as run_plsda, PLSDAResult as PLSDAResult
from analysis.univariate import volcano_analysis as volcano_analysis, VolcanoResult as VolcanoResult
from analysis.anova import run_anova as run_anova, ANOVAResult as ANOVAResult
from analysis.clustering import compute_linkage as compute_linkage, select_top_features as select_top_features, run_clustering as run_clustering, ClusteringResult as ClusteringResult
from analysis.correlation import run_correlation as run_correlation, CorrelationResult as CorrelationResult
from analysis.roc import run_roc_analysis as run_roc_analysis, ROCResult as ROCResult
from analysis.outlier import run_outlier_detection as run_outlier_detection, OutlierResult as OutlierResult
from analysis.random_forest import run_random_forest as run_random_forest, RFResult as RFResult

try:
    from analysis.oplsda import run_oplsda as run_oplsda, OPLSDAResult as OPLSDAResult
except ImportError:
    pass  # pyopls not installed
