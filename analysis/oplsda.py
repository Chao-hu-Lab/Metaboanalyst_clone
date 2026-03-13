"""
OPLS-DA analysis.

When `pyopls` is unavailable, this module falls back to a PLS-based path so
the UI can still run and export score/loading information.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder

try:
    from pyopls import OPLS

    HAS_PYOPLS = True
except ImportError:
    HAS_PYOPLS = False


@dataclass
class OPLSDAResult:
    """OPLS-DA analysis result container."""

    scores_predictive: np.ndarray
    scores_orthogonal: np.ndarray
    labels: object
    r2x: float = 0.0
    r2y: float = 0.0
    q2: float = 0.0
    feature_names: list = field(default_factory=list)
    loadings_predictive: np.ndarray | None = None
    vip_scores: np.ndarray | None = None
    class_names: list = field(default_factory=list)
    sample_names: list = field(default_factory=list)
    backend: str = "pyopls"

    def get_score_df(self) -> pd.DataFrame:
        labels_arr = self.labels.values if hasattr(self.labels, "values") else np.array(self.labels)
        df = pd.DataFrame(
            {
                "T_predictive": self.scores_predictive[:, 0],
                "T_orthogonal": self.scores_orthogonal[:, 0],
                "Group": labels_arr,
            }
        )
        if self.sample_names:
            df["Sample"] = list(self.sample_names)
        else:
            df["Sample"] = [f"S{i}" for i in range(len(df))]
        return df

    def get_importance_df(self) -> pd.DataFrame:
        if self.loadings_predictive is None:
            return pd.DataFrame()
        importance = np.abs(self.loadings_predictive[:, 0])
        df = pd.DataFrame(
            {
                "Feature": self.feature_names,
                "Loading": self.loadings_predictive[:, 0],
                "Importance": importance,
            }
        )
        return df.sort_values("Importance", ascending=False).reset_index(drop=True)


def _to_single_component(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    if arr.ndim == 2:
        return arr[:, :1]
    raise ValueError("Expected 1D or 2D array for score matrix.")


def _build_cv(y: np.ndarray, cv_method: str):
    if cv_method == "loo":
        return LeaveOneOut()

    class_counts = np.bincount(y)
    min_count = int(class_counts.min()) if len(class_counts) > 0 else 0
    n_splits = min(5, min_count)
    if n_splits < 2:
        return LeaveOneOut()
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)


def _safe_q2(pls_model: PLSRegression, x_data: np.ndarray, y_data: np.ndarray, cv) -> float:
    """
    Compute Q² via PRESS/TSS using cross_val_predict.

    Works correctly for both LOO and K-Fold. Standard formula used by
    SIMCA and MetaboAnalyst: Q² = 1 - PRESS / TSS.
    """
    try:
        y_pred = cross_val_predict(pls_model, x_data, y_data, cv=cv)
        press = np.sum((y_data - y_pred) ** 2)
        tss = np.sum((y_data - np.mean(y_data)) ** 2)
        if tss == 0:
            return 0.0
        return float(1.0 - press / tss)
    except Exception as e:
        print(f"    Q2 calculation failed: {e}")
        return 0.0


def run_oplsda(data, labels, n_components=1, cv_method="loo") -> OPLSDAResult:
    """
    Run OPLS-DA analysis.

    Falls back to PLS when `pyopls` is not installed.
    """
    x_data = data.values.astype(float)
    encoder = LabelEncoder()
    y_data = encoder.fit_transform(labels)
    feature_names = list(data.columns)
    class_names = list(encoder.classes_)

    backend = "pyopls" if HAS_PYOPLS else "pls_fallback"
    r2x = 0.0

    if HAS_PYOPLS:
        opls = OPLS(n_components=max(1, int(n_components)))
        z_data = opls.fit_transform(x_data, y_data)
        x_for_pls = z_data
        orth_scores = _to_single_component(opls.T_ortho_)
        if np.var(x_data) > 0:
            r2x = float(1.0 - (np.var(z_data) / np.var(x_data)))
    else:
        x_for_pls = x_data
        orth_scores = np.zeros((x_data.shape[0], 1), dtype=float)

    pls = PLSRegression(n_components=1, scale=False)
    pls.fit(x_for_pls, y_data)
    pred_scores = _to_single_component(pls.x_scores_)

    cv = _build_cv(y_data, cv_method=cv_method)
    q2 = _safe_q2(pls, x_for_pls, y_data, cv)
    r2y = float(pls.score(x_for_pls, y_data))

    loadings_pred = _to_single_component(pls.x_loadings_)
    vip_scores = np.abs(loadings_pred[:, 0])

    return OPLSDAResult(
        scores_predictive=pred_scores,
        scores_orthogonal=orth_scores,
        labels=labels,
        r2x=r2x,
        r2y=r2y,
        q2=q2,
        feature_names=feature_names,
        loadings_predictive=loadings_pred,
        vip_scores=vip_scores,
        class_names=class_names,
        sample_names=list(data.index),
        backend=backend,
    )
