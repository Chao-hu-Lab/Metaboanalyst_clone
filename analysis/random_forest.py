"""
Random Forest analysis:
- feature importance
- OOB accuracy
- CV accuracy
- confusion matrix
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.preprocessing import LabelEncoder

# Respect METABO_N_JOBS env var for parallelism control.
# Defaults to -1 (all cores). Set to 1 in restricted environments (CI, PyInstaller).
_N_JOBS: int = int(os.environ.get("METABO_N_JOBS", "-1"))

_INVALID_FEATURE_TOKENS = {"", "na", "nan", "none", "null"}


@dataclass
class RFResult:
    feature_importance: pd.DataFrame
    oob_accuracy: float
    cv_accuracy: float
    cv_std: float
    cv_folds_used: int
    confusion_mat: np.ndarray
    class_names: List[str]
    model: RandomForestClassifier
    dropped_unnamed_features: int = 0

    def get_top_features(self, n: int = 25) -> pd.DataFrame:
        return self.feature_importance.head(n)


def _get_cv_folds(y: np.ndarray, requested_folds: int) -> int:
    """Choose valid StratifiedKFold split count from class distribution."""
    class_counts = np.bincount(y)
    min_class_count = int(class_counts.min()) if len(class_counts) > 0 else 0
    if min_class_count < 2:
        return 0
    return max(2, min(requested_folds, min_class_count))


def _is_invalid_feature_name(name) -> bool:
    if pd.isna(name):
        return True
    text = str(name).strip().lower()
    return text in _INVALID_FEATURE_TOKENS


def _clean_feature_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop unnamed/invalid feature columns and normalize duplicate names."""
    kept_positions: list[int] = []
    clean_names: list[str] = []
    dropped = 0
    seen: dict[str, int] = {}

    for pos, col in enumerate(df.columns):
        if _is_invalid_feature_name(col):
            dropped += 1
            continue

        base = str(col).strip()
        count = seen.get(base, 0) + 1
        seen[base] = count
        clean = base if count == 1 else f"{base}_{count}"

        kept_positions.append(pos)
        clean_names.append(clean)

    out = df.iloc[:, kept_positions].copy()
    out.columns = clean_names
    return out, dropped


def _build_rf_model(
    *,
    n_trees: int,
    random_state: int,
    n_jobs: int,
) -> RandomForestClassifier:
    """Build a Random Forest classifier with a specific parallelism setting."""
    return RandomForestClassifier(
        n_estimators=n_trees,
        oob_score=True,
        random_state=random_state,
        n_jobs=n_jobs,
    )


def _run_rf_with_n_jobs(
    *,
    X: np.ndarray,
    y: np.ndarray,
    class_names: list[str],
    feature_names: list[str],
    dropped_unnamed: int,
    n_trees: int,
    cv_folds: int,
    top_n: int,
    random_state: int,
    n_jobs: int,
) -> RFResult:
    """Execute Random Forest analysis with an explicit n_jobs setting."""
    rf = _build_rf_model(
        n_trees=n_trees,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    rf.fit(X, y)
    oob_acc = float(rf.oob_score_)

    used_folds = _get_cv_folds(y, cv_folds)
    if used_folds >= 2:
        cv = StratifiedKFold(
            n_splits=used_folds,
            shuffle=True,
            random_state=random_state,
        )
        cv_scores = cross_val_score(
            _build_rf_model(
                n_trees=n_trees,
                random_state=random_state,
                n_jobs=n_jobs,
            ),
            X,
            y,
            cv=cv,
            scoring="accuracy",
            n_jobs=n_jobs,
        )
        cv_acc = float(cv_scores.mean())
        cv_std = float(cv_scores.std())
        y_pred = cross_val_predict(
            _build_rf_model(
                n_trees=n_trees,
                random_state=random_state,
                n_jobs=n_jobs,
            ),
            X,
            y,
            cv=cv,
            n_jobs=n_jobs,
        )
        cm = confusion_matrix(y, y_pred)
    else:
        # Not enough samples per class for CV; fall back to in-sample prediction.
        cv_acc = float("nan")
        cv_std = float("nan")
        cm = confusion_matrix(y, rf.predict(X))

    feature_cap = int(max(1, min(top_n, len(feature_names))))
    importance_df = (
        pd.DataFrame(
            {
                "Feature": feature_names,
                "Importance": rf.feature_importances_,
            }
        )
        .sort_values("Importance", ascending=False)
        .reset_index(drop=True)
        .head(feature_cap)
    )

    return RFResult(
        feature_importance=importance_df,
        oob_accuracy=oob_acc,
        cv_accuracy=cv_acc,
        cv_std=cv_std,
        cv_folds_used=used_folds,
        confusion_mat=cm,
        class_names=class_names,
        model=rf,
        dropped_unnamed_features=dropped_unnamed,
    )


def run_random_forest(
    df: pd.DataFrame,
    labels: pd.Series,
    n_trees: int = 500,
    cv_folds: int = 5,
    top_n: int = 30,
    random_state: int = 42,
) -> RFResult:
    """
    Run Random Forest classification and return importance + performance summary.
    """
    clean_df, dropped_unnamed = _clean_feature_dataframe(df)
    if clean_df.shape[1] == 0:
        raise ValueError("No valid feature columns remain after dropping unnamed features.")

    le = LabelEncoder()
    y = le.fit_transform(labels)
    X = clean_df.values
    class_names = list(le.classes_)
    requested_n_jobs = _N_JOBS

    try:
        return _run_rf_with_n_jobs(
            X=X,
            y=y,
            class_names=class_names,
            feature_names=clean_df.columns.astype(str).tolist(),
            dropped_unnamed=dropped_unnamed,
            n_trees=n_trees,
            cv_folds=cv_folds,
            top_n=top_n,
            random_state=random_state,
            n_jobs=requested_n_jobs,
        )
    except PermissionError:
        # Windows sandboxed or packaged environments can deny the internal
        # multiprocessing queue creation used by joblib when n_jobs != 1.
        if requested_n_jobs == 1:
            raise
        return _run_rf_with_n_jobs(
            X=X,
            y=y,
            class_names=class_names,
            feature_names=clean_df.columns.astype(str).tolist(),
            dropped_unnamed=dropped_unnamed,
            n_trees=n_trees,
            cv_folds=cv_folds,
            top_n=top_n,
            random_state=random_state,
            n_jobs=1,
        )
