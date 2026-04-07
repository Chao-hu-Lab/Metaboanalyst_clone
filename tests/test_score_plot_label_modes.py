"""Score plot label-mode consistency tests for PCA / PLS-DA / OPLS-DA."""

from __future__ import annotations

from types import SimpleNamespace

import matplotlib
import numpy as np
import pandas as pd
import pytest

from gui.main_window import MainWindow
from visualization.oplsda_plot import plot_oplsda_score
from visualization.pca_plot import plot_pca_score
from visualization.plsda_plot import plot_plsda_score

matplotlib.use("Agg")

pytestmark = [pytest.mark.gui, pytest.mark.integration]


def _make_group_scores(seed: int, shift: float) -> np.ndarray:
    rng = np.random.RandomState(seed)
    cluster = rng.normal(loc=shift, scale=0.08, size=(10, 2))
    outlier = np.array([[shift + 4.0, shift + 4.0]])
    return np.vstack([cluster, outlier])


def _make_score_plot_fixture():
    scores_a = _make_group_scores(seed=7, shift=0.0)
    scores_b = _make_group_scores(seed=11, shift=2.5)
    scores = np.vstack([scores_a, scores_b])
    sample_names = [f"S{i+1}" for i in range(len(scores))]
    labels = pd.Series(
        ["A"] * len(scores_a) + ["B"] * len(scores_b),
        index=sample_names,
        name="Group",
    )
    return scores, sample_names, labels


def _make_pca_result():
    scores, sample_names, labels = _make_score_plot_fixture()
    return SimpleNamespace(
        scores=scores,
        labels=labels,
        sample_names=sample_names,
        explained_variance_ratio=np.array([0.62, 0.21]),
    )


def _make_plsda_result():
    scores, sample_names, labels = _make_score_plot_fixture()
    return SimpleNamespace(
        scores=scores,
        labels=labels,
        sample_names=sample_names,
        explained_variance=np.array([0.57, 0.24]),
    )


class _DummyOPLSDAResult:
    def __init__(self, *, backend: str = "pyopls") -> None:
        scores, sample_names, labels = _make_score_plot_fixture()
        self._score_df = pd.DataFrame(
            {
                "T_predictive": scores[:, 0],
                "T_orthogonal": scores[:, 1],
                "Group": labels.to_numpy(),
                "Sample": sample_names,
            }
        )
        self.backend = backend

    def get_score_df(self) -> pd.DataFrame:
        return self._score_df.copy()


@pytest.mark.parametrize(
    ("plotter", "result_factory"),
    [
        (plot_pca_score, _make_pca_result),
        (plot_plsda_score, _make_plsda_result),
        (plot_oplsda_score, _DummyOPLSDAResult),
    ],
)
def test_score_plots_support_none_outlier_and_all_label_modes(plotter, result_factory) -> None:
    result = result_factory()
    total_samples = 22

    fig_none = plotter(result, show_labels="none")
    fig_outlier = plotter(result, show_labels="outlier")
    fig_all = plotter(result, show_labels="all")

    assert len(fig_none.axes[0].texts) == 0
    assert 0 < len(fig_outlier.axes[0].texts) < total_samples
    assert len(fig_all.axes[0].texts) == total_samples


def test_oplsda_plot_labels_fallback_axis_honestly() -> None:
    fig = plot_oplsda_score(_DummyOPLSDAResult(backend="pls_fallback"), show_labels="none")

    assert fig.axes[0].get_ylabel().startswith("T score [2]")
    assert any(text.get_text() == "PLS fallback axis" for text in fig.axes[0].texts)


@pytest.mark.parametrize(
    ("result_attr", "plot_type_attr", "label_mode_attr", "update_method_name", "module_path"),
    [
        ("_pca_result", "pca_plot_type", "pca_label_mode", "_update_pca_plot", "visualization.pca_plot"),
        ("_plsda_result", "pls_plot_type", "pls_label_mode", "_update_plsda_plot", "visualization.plsda_plot"),
        ("_oplsda_result", "oplsda_plot_type", "oplsda_label_mode", "_update_oplsda_plot", "visualization.oplsda_plot"),
    ],
)
def test_stats_tab_score_plots_forward_selected_label_mode(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
    result_attr: str,
    plot_type_attr: str,
    label_mode_attr: str,
    update_method_name: str,
    module_path: str,
) -> None:
    import importlib

    window = MainWindow()
    stats_tab = window.stats_tab
    captured: dict[str, object] = {}
    module = importlib.import_module(module_path)

    if result_attr == "_pca_result":
        setattr(stats_tab, result_attr, _make_pca_result())
    elif result_attr == "_plsda_result":
        setattr(stats_tab, result_attr, _make_plsda_result())
    else:
        setattr(stats_tab, result_attr, _DummyOPLSDAResult())

    plot_type_combo = getattr(stats_tab, plot_type_attr)
    score_index = plot_type_combo.findData("score")
    if score_index >= 0:
        plot_type_combo.setCurrentIndex(score_index)

    label_mode_combo = getattr(stats_tab, label_mode_attr)
    label_mode_combo.setCurrentIndex(label_mode_combo.findData("all"))

    def _fake_plot(*args, **kwargs):
        captured["show_labels"] = kwargs.get("show_labels")
        return kwargs["fig"]

    monkeypatch.setattr(module, module.__all__[0] if False else {
        "visualization.pca_plot": "plot_pca_score",
        "visualization.plsda_plot": "plot_plsda_score",
        "visualization.oplsda_plot": "plot_oplsda_score",
    }[module_path], _fake_plot)

    getattr(stats_tab, update_method_name)()

    assert captured["show_labels"] == "all"
    window.close()
