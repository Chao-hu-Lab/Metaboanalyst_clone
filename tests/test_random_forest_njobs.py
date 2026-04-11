"""Test that METABO_N_JOBS env var controls n_jobs in RandomForestClassifier."""
import importlib

import numpy as np
import pandas as pd


def test_random_forest_respects_metabo_n_jobs(monkeypatch):
    """METABO_N_JOBS env var must propagate to RandomForestClassifier n_jobs."""
    import analysis.random_forest as rf_mod

    monkeypatch.setenv("METABO_N_JOBS", "2")
    importlib.reload(rf_mod)           # re-read module-level constant
    assert rf_mod._N_JOBS == 2

    monkeypatch.delenv("METABO_N_JOBS", raising=False)
    importlib.reload(rf_mod)
    assert rf_mod._N_JOBS == -1        # default when env var absent

    # Restore CI-safe default (conftest sets METABO_N_JOBS=1 at session start
    # via setdefault, but monkeypatch.delenv removed it from os.environ).
    monkeypatch.setenv("METABO_N_JOBS", "1")
    importlib.reload(rf_mod)
    assert rf_mod._N_JOBS == 1


def test_random_forest_falls_back_to_single_process_on_permission_error(monkeypatch):
    """Permission errors in parallel backends should fall back to n_jobs=1."""
    import analysis.random_forest as rf_mod

    fit_calls: list[int] = []
    score_calls: list[tuple[int, int]] = []
    predict_calls: list[tuple[int, int]] = []

    class DummyRF:
        def __init__(self, *, n_estimators, oob_score, random_state, n_jobs):
            self.n_estimators = n_estimators
            self.oob_score = oob_score
            self.random_state = random_state
            self.n_jobs = n_jobs
            self.oob_score_ = 0.91
            self.feature_importances_ = np.array([0.7, 0.3], dtype=float)

        def fit(self, X, y):
            fit_calls.append(self.n_jobs)
            if self.n_jobs != 1:
                raise PermissionError(5, "denied")
            return self

        def predict(self, X):
            return np.zeros(len(X), dtype=int)

    def fake_cross_val_score(estimator, X, y, cv, scoring, n_jobs):
        score_calls.append((estimator.n_jobs, n_jobs))
        return np.array([0.8, 0.9], dtype=float)

    def fake_cross_val_predict(estimator, X, y, cv, n_jobs):
        predict_calls.append((estimator.n_jobs, n_jobs))
        return np.zeros(len(y), dtype=int)

    monkeypatch.setattr(rf_mod, "_N_JOBS", 2)
    monkeypatch.setattr(rf_mod, "RandomForestClassifier", DummyRF)
    monkeypatch.setattr(rf_mod, "cross_val_score", fake_cross_val_score)
    monkeypatch.setattr(rf_mod, "cross_val_predict", fake_cross_val_predict)

    df = pd.DataFrame(
        np.array(
            [
                [1.0, 2.0],
                [1.1, 2.1],
                [0.9, 1.9],
                [3.0, 4.0],
                [3.1, 4.1],
                [2.9, 3.9],
            ]
        ),
        columns=["F1", "F2"],
    )
    labels = pd.Series(["A", "A", "A", "B", "B", "B"])

    result = rf_mod.run_random_forest(df, labels, n_trees=10, cv_folds=3, top_n=2)

    assert fit_calls == [2, 1]
    assert score_calls == [(1, 1)]
    assert predict_calls == [(1, 1)]
    assert result.oob_accuracy == 0.91
    assert result.cv_folds_used == 3
