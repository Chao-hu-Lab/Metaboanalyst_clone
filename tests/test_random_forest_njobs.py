"""Test that METABO_N_JOBS env var controls n_jobs in RandomForestClassifier."""
import importlib


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
