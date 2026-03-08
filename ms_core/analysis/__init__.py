"""Map legacy ``ms_core.analysis`` imports to local ``analysis`` modules."""

from importlib import import_module
import sys


_ALIASES = {
    "anova": "analysis.anova",
    "clustering": "analysis.clustering",
    "correlation": "analysis.correlation",
    "oplsda": "analysis.oplsda",
    "outlier": "analysis.outlier",
    "pca": "analysis.pca",
    "plsda": "analysis.plsda",
    "random_forest": "analysis.random_forest",
    "roc": "analysis.roc",
    "univariate": "analysis.univariate",
}


for legacy_name, target_name in _ALIASES.items():
    sys.modules[f"{__name__}.{legacy_name}"] = import_module(target_name)
