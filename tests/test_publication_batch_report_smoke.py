"""Smoke coverage for the publication-oriented batch report layout."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import ms_core.analysis.oplsda as ms_oplsda_mod
import ms_core.analysis.plsda as ms_plsda_mod
import ms_core.visualization.oplsda_plot as ms_oplsda_plot_mod
import ms_core.visualization.plsda_plot as ms_plsda_plot_mod
import ms_core.visualization.vip_plot as ms_vip_plot_mod
import scripts.run_from_config as run_mod
import visualization.volcano_plot as volcano_plot_mod

pytestmark = pytest.mark.integration


class _DummyPipeline:
    def __init__(
        self, data: pd.DataFrame, labels: pd.Series, feature_metadata: pd.DataFrame
    ) -> None:
        self._data = data
        self._labels = labels
        self._feature_metadata = feature_metadata
        self.log = ["fake pipeline"]
        self.steps: dict[str, pd.DataFrame] = {}
        self.step_feature_metadata: dict[str, pd.DataFrame] = {}
        self.processed: pd.DataFrame | None = None
        self.processed_labels: pd.Series | None = None
        self.processed_feature_metadata: pd.DataFrame | None = None

    def run_pipeline(self, **kwargs) -> pd.DataFrame:
        self.processed = self._data.copy()
        self.processed_labels = self._labels.copy()
        self.processed_feature_metadata = self._feature_metadata.copy()
        self.steps = {
            "filtered": self._data.copy(),
            "transformed": self._data.copy(),
            "batch_corrected": self._data.copy(),
            "row_normed": self._data.copy(),
        }
        self.step_feature_metadata = {"qc_rsd": pd.DataFrame()}
        return self.processed


class _DummyPCAResult:
    def __init__(self) -> None:
        self.explained_variance_ratio = np.array([0.58, 0.27, 0.15], dtype=float)


class _DummyANOVAResult:
    def __init__(self, features: list[str]) -> None:
        self.method_key = "anova"
        self.p_thresh = 0.05
        self.n_significant = 2
        self.result_df = pd.DataFrame(
            {
                "Feature": features,
                "pvalue": [0.001, 0.02, 0.50],
                "pvalue_adj": [0.003, 0.04, 0.60],
                "neg_log10p": [3.0, 1.7, 0.2],
                "significant": [True, True, False],
                "is_Presence_Absence_Marker": [False, False, True],
            }
        )


class _DummyPLSDAResult:
    def __init__(self, features: list[str], groups: list[str]) -> None:
        self.explained_variance = np.array([0.64, 0.23], dtype=float)
        self.q2 = 0.71
        self.vips = np.array([1.5, 1.1, 0.9], dtype=float)
        self.class_names = np.array(groups, dtype=object)
        self._features = features

    def get_vip_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Feature": self._features,
                "VIP": [1.5, 1.1, 0.9],
                "is_Presence_Absence_Marker": [False, False, True],
            }
        )


class _DummyOPLSDAResult:
    def __init__(self, features: list[str], groups: list[str]) -> None:
        self.r2x = 0.51
        self.r2y = 0.63
        self.q2 = 0.44
        self.backend = "pyopls"
        self.class_names = np.array(groups, dtype=object)
        self._features = features

    def get_score_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Sample": ["S1", "S2", "S3", "S4"],
                "Group": ["Exposure", "Exposure", "Normal", "Normal"],
                "T_predictive": [0.9, 0.7, -0.8, -0.6],
                "T_orthogonal": [0.2, -0.1, 0.3, 0.1],
            }
        )

    def get_importance_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Feature": self._features,
                "Loading": [0.8, -0.4, 0.2],
                "Importance": [0.8, 0.4, 0.2],
                "is_Presence_Absence_Marker": [False, False, True],
            }
        )


class _DummyVolcanoResult:
    def __init__(self, features: list[str], group1: str, group2: str) -> None:
        self.group1 = group1
        self.group2 = group2
        self.fc_thresh = 2.0
        self.log2_fc_thresh = 1.0
        self.p_thresh = 0.05
        self.use_fdr = True
        self.fdr_method = "fdr_bh"
        self.test_label = "Welch's t"
        self.n_significant = 2
        self.n_up = 1
        self.n_down = 1
        self.n_pairs = 0
        self.resolution_overrides_applied: list[dict[str, str]] = []
        self.resolution_warnings: list[str] = []
        self.result_df = pd.DataFrame(
            {
                "Feature": features,
                "log2FC": [1.4, -1.2, 0.1],
                "pvalue": [0.001, 0.02, 0.80],
                "pvalue_adj": [0.002, 0.03, 0.90],
                "significant": [True, True, False],
                "is_Presence_Absence_Marker": [False, False, True],
            }
        )
        self.significant = self.result_df.loc[self.result_df["significant"]].copy()


class _DummyOutlierResult:
    def __init__(self, sample_names: list[str]) -> None:
        self.sample_names = sample_names

    def get_outlier_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Sample": self.sample_names,
                "T2": np.linspace(0.2, 1.2, len(self.sample_names)),
                "T2_Outlier": [False] * len(self.sample_names),
                "DModX": np.linspace(0.1, 0.6, len(self.sample_names)),
                "DModX_Outlier": [False] * len(self.sample_names),
                "Any_Outlier": [False] * len(self.sample_names),
            }
        )


def _make_roc_result() -> SimpleNamespace:
    summary = pd.DataFrame(
        {
            "Feature": ["F1", "F2"],
            "AUC": [0.91, 0.82],
            "Optimal_Cutoff": [0.5, 0.5],
            "Sensitivity": [0.88, 0.80],
            "Specificity": [0.84, 0.76],
        }
    )
    return SimpleNamespace(
        single_rocs=[],
        multi_fpr=np.array([0.0, 0.3, 1.0]),
        multi_tpr=np.array([0.0, 0.8, 1.0]),
        multi_auc=0.89,
        summary_df=summary,
        single_cv_folds_used=2,
        multi_cv_folds_used=2,
    )


def _make_rf_result(features: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        feature_importance=pd.DataFrame(
            {
                "Feature": features,
                "Importance": [0.6, 0.3, 0.1],
            }
        ),
        oob_accuracy=0.83,
        cv_accuracy=0.79,
        cv_std=0.05,
        confusion_mat=np.array([[2, 0], [1, 1]]),
        class_names=["Exposure", "Normal"],
    )


def _stub_plot(label: str):
    def _plot(*args, fig=None, **kwargs):
        if fig is None:
            fig = plt.figure(figsize=(4, 3))
        fig.clf()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, label, ha="center", va="center", fontsize=11)
        ax.set_axis_off()
        ax.set_title(label)
        return fig

    return _plot


def _install_smoke_stubs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    sample_names = [
        "Exposure_A",
        "Exposure_B",
        "Normal_A",
        "Normal_B",
        "Control_A",
        "Control_B",
    ]
    features = ["F1", "F2", "F3"]
    data = pd.DataFrame(
        {
            "F1": [10.0, 11.0, 20.0, 21.0, 30.0, 31.0],
            "F2": [5.0, 4.5, 3.0, 3.5, 2.0, 2.5],
            "F3": [1.0, 1.2, 1.5, 1.7, 1.9, 2.1],
        },
        index=sample_names,
    )
    labels = pd.Series(
        ["Exposure", "Exposure", "Normal", "Normal", "Control", "Control"],
        index=sample_names,
        name="Group",
    )
    feature_metadata = pd.DataFrame(
        {
            "is_Presence_Absence_Marker": [False, False, True],
            "imputation_method": ["knn", "knn", "min"],
        },
        index=features,
    )

    monkeypatch.setattr(run_mod, "_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(
        run_mod,
        "load_data",
        lambda cfg: (data.copy(), labels.copy(), feature_metadata.copy()),
    )
    monkeypatch.setattr(run_mod, "MetaboAnalystPipeline", _DummyPipeline)
    monkeypatch.setattr(run_mod, "run_pca", lambda *args, **kwargs: _DummyPCAResult())
    monkeypatch.setattr(
        run_mod, "run_anova", lambda *args, **kwargs: _DummyANOVAResult(features)
    )
    monkeypatch.setattr(
        run_mod,
        "volcano_analysis",
        lambda *args, **kwargs: _DummyVolcanoResult(
            features, kwargs["group1"], kwargs["group2"]
        ),
    )
    monkeypatch.setattr(
        run_mod, "run_roc_analysis", lambda *args, **kwargs: _make_roc_result()
    )
    monkeypatch.setattr(
        run_mod, "run_random_forest", lambda *args, **kwargs: _make_rf_result(features)
    )
    monkeypatch.setattr(
        run_mod,
        "run_outlier_detection",
        lambda *args, **kwargs: _DummyOutlierResult(sample_names),
    )

    monkeypatch.setattr(
        run_mod, "plot_norm_comparison", _stub_plot("Normalization Comparison")
    )
    monkeypatch.setattr(run_mod, "plot_pca_score", _stub_plot("PCA Score Plot"))
    monkeypatch.setattr(
        run_mod, "plot_anova_importance", _stub_plot("ANOVA Importance Plot")
    )
    monkeypatch.setattr(
        run_mod, "plot_feature_boxplot", _stub_plot("ANOVA Feature Boxplot")
    )
    monkeypatch.setattr(run_mod, "plot_heatmap", _stub_plot("Heatmap"))
    monkeypatch.setattr(
        run_mod, "plot_grouped_heatmap", _stub_plot("Grouped Heatmap")
    )
    monkeypatch.setattr(run_mod, "plot_oplsda_splot", _stub_plot("OPLS-DA S-Plot"))
    monkeypatch.setattr(run_mod, "plot_outlier_score", _stub_plot("Outlier T2"))
    monkeypatch.setattr(run_mod, "plot_dmodx", _stub_plot("Outlier DModX"))
    monkeypatch.setattr(run_mod, "plot_roc_curves", _stub_plot("ROC Curves"))
    monkeypatch.setattr(run_mod, "plot_auc_ranking", _stub_plot("AUC Ranking"))
    monkeypatch.setattr(run_mod, "plot_rf_importance", _stub_plot("RF Importance"))
    monkeypatch.setattr(run_mod, "plot_confusion_matrix", _stub_plot("RF Confusion"))

    monkeypatch.setattr(
        ms_plsda_mod,
        "run_plsda",
        lambda *args, **kwargs: _DummyPLSDAResult(
            features, ["Exposure", "Normal", "Control"]
        ),
    )
    monkeypatch.setattr(
        ms_plsda_plot_mod, "plot_plsda_score", _stub_plot("PLS-DA Score Plot")
    )
    monkeypatch.setattr(ms_vip_plot_mod, "plot_vip", _stub_plot("PLS-DA VIP Plot"))
    monkeypatch.setattr(
        ms_oplsda_mod,
        "run_oplsda",
        lambda *args, **kwargs: _DummyOPLSDAResult(features, ["Exposure", "Normal"]),
    )
    monkeypatch.setattr(
        ms_oplsda_plot_mod, "plot_oplsda_score", _stub_plot("OPLS-DA Score Plot")
    )
    monkeypatch.setattr(volcano_plot_mod, "plot_volcano", _stub_plot("Volcano Plot"))

    return data, labels, feature_metadata


def _build_publication_config(tmp_path: Path) -> dict:
    return {
        "input": {
            "file": str(tmp_path / "demo_publication.xlsx"),
            "format": "plain",
        },
        "pipeline": {
            "missing_thresh": 1.0,
            "impute_method": "knn",
            "qc_rsd_enabled": True,
            "qc_rsd_threshold": 0.50,
            "filter_method": "None",
            "filter_cutoff": 0,
            "row_norm": "None",
            "transform": "Log10Norm",
            "scaling": "ParetoNorm",
        },
        "groups": {
            "include": ["Exposure", "Normal", "Control"],
            "pair_id_pattern": r"BC\d+",
            "volcano_pairs": [
                {"groups": ["Exposure", "Normal"], "paired": False},
                {"groups": ["Exposure", "Control"], "paired": False},
                {"groups": ["Normal", "Control"], "paired": False},
            ],
            "oplsda_pairs": [
                {"groups": ["Exposure", "Normal"], "paired": False},
                {"groups": ["Exposure", "Control"], "paired": False},
                {"groups": ["Normal", "Control"], "paired": False},
            ],
        },
        "analysis": {
            "pca": {"n_components": 3},
            "plsda": {"n_components": 2, "top_vip": 15},
            "anova": {
                "p_thresh": 0.05,
                "nonpar": False,
                "use_fdr": True,
                "posthoc": True,
            },
            "volcano": {
                "fc_thresh": 2.0,
                "log2_fc_thresh": 1.0,
                "p_thresh": 0.05,
                "use_fdr": True,
                "parametric_test_default": "welch",
            },
            "heatmap": {
                "max_features": 50,
                "top_by": "var",
                "method": "ward",
                "metric": "euclidean",
                "scale": "row",
            },
            "roc": {"top_n": 10, "multi_feature": True},
            "outlier": {"n_components": 2, "alpha": 0.05},
            "random_forest": {"n_trees": 500, "cv_folds": 5, "top_n": 25},
        },
        "output": {
            "suffix": "_publication_smoke",
            "auto_timestamp": False,
        },
    }


def test_publication_report_smoke_layout_and_pruning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_smoke_stubs(monkeypatch, tmp_path)
    cfg = _build_publication_config(tmp_path)

    result = run_mod.run_analysis(cfg)

    output_dir = Path(result["output_dir"])
    expected_dirs = [
        output_dir / "00_Review_Pack",
        output_dir / "01_QC_and_Preprocessing",
        output_dir / "02_Global_Profiling",
        output_dir / "03_Feature_Selection",
        output_dir / "04_Biomarker_Validation",
        output_dir / "05_Supplementary",
    ]
    expected_files = [
        output_dir / "01_QC_and_Preprocessing" / "config_used.yaml",
        output_dir / "01_QC_and_Preprocessing" / "processed_data.csv",
        output_dir / "01_QC_and_Preprocessing" / "sample_labels.csv",
        output_dir / "01_QC_and_Preprocessing" / "feature_metadata.csv",
        output_dir / "01_QC_and_Preprocessing" / "pipeline_log.txt",
        output_dir / "03_Feature_Selection" / "anova_results.csv",
        output_dir / "04_Biomarker_Validation" / "roc_Exposure_vs_Normal.csv",
        output_dir / "05_Supplementary" / "rf_importance_Exposure_vs_Normal.csv",
        output_dir / "05_Supplementary" / "outlier_results.csv",
        output_dir / "01_QC_and_Preprocessing" / "normalization_comparison.png",
        output_dir / "01_QC_and_Preprocessing" / "pca_score_plot.png",
        output_dir / "02_Global_Profiling" / "heatmap_top50.png",
        output_dir / "02_Global_Profiling" / "heatmap_top50_grouped.png",
        output_dir / "03_Feature_Selection" / "oplsda_score_Exposure_vs_Normal.png",
        output_dir / "03_Feature_Selection" / "oplsda_splot_Exposure_vs_Normal.png",
        output_dir / "03_Feature_Selection" / "volcano_Exposure_vs_Normal.png",
        output_dir / "03_Feature_Selection" / "plsda_vip_Exposure_vs_Normal.png",
        output_dir / "03_Feature_Selection" / "anova_importance.png",
        output_dir / "04_Biomarker_Validation" / "roc_Exposure_vs_Normal.png",
        output_dir / "04_Biomarker_Validation" / "auc_ranking_Exposure_vs_Normal.png",
        output_dir / "05_Supplementary" / "plsda_score_all_groups.png",
        output_dir / "05_Supplementary" / "outlier_t2.png",
        output_dir / "05_Supplementary" / "outlier_dmodx.png",
        output_dir / "05_Supplementary" / "rf_importance_Exposure_vs_Normal.png",
        output_dir / "05_Supplementary" / "rf_confusion_matrix_Exposure_vs_Normal.png",
        output_dir / "05_Supplementary" / "anova_boxplot_Exposure_vs_Normal_top1.png",
        output_dir / "00_Review_Pack" / "01_pca_score_plot.png",
        output_dir / "00_Review_Pack" / "02_heatmap_top50_grouped.png",
        output_dir / "00_Review_Pack" / "03_anova_importance.png",
        output_dir / "00_Review_Pack" / "04_plsda_score_all_groups.png",
        output_dir
        / "00_Review_Pack"
        / "05_oplsda_score_Exposure_vs_Normal.png",
        output_dir / "00_Review_Pack" / "06_plsda_vip_Exposure_vs_Normal.png",
        output_dir / "00_Review_Pack" / "07_volcano_Exposure_vs_Normal.png",
    ]
    legacy_files = [
        output_dir / "pca_scree_plot.png",
        output_dir / "pca_loading_plot.png",
        output_dir / "sample_boxplot.png",
        output_dir / "density_plot.png",
        output_dir / "plsda_score_Exposure_vs_Normal.png",
        output_dir / "pca_score_plot.html",
        output_dir / "oplsda_score_Exposure_vs_Normal.html",
        output_dir / "volcano_Exposure_vs_Normal.html",
    ]

    for folder in expected_dirs:
        assert folder.is_dir(), f"missing report folder: {folder}"

    for file_path in expected_files:
        assert file_path.is_file(), f"missing report file: {file_path}"

    assert not list(output_dir.rglob("*.pdf")), "PDF figures should be opt-in"

    for file_path in legacy_files:
        assert not file_path.exists(), (
            f"legacy output should not be emitted: {file_path}"
        )


def test_run_analysis_cli_combat_sample_info_mode_passes_runtime_params(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_smoke_stubs(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    sample_info = pd.DataFrame(
        {
            "Sample_Name": [
                "Exposure_A",
                "Exposure_B",
                "Normal_A",
                "Normal_B",
                "Control_A",
                "Control_B",
            ],
            "Batch": ["A", "A", "B", "B", "C", "C"],
            "Sex": ["F", "M", "F", "M", "F", "M"],
        }
    )

    class _CapturePipeline(_DummyPipeline):
        def run_pipeline(self, **kwargs) -> pd.DataFrame:
            captured.update(kwargs)
            return super().run_pipeline(**kwargs)

    monkeypatch.setattr(run_mod, "MetaboAnalystPipeline", _CapturePipeline)
    monkeypatch.setattr(run_mod, "read_sample_info_sheet", lambda _path: sample_info.copy())

    cfg = _build_publication_config(tmp_path)
    cfg["pipeline"]["batch_correction"] = "ComBat"
    cfg["combat"] = {
        "covariate_mode": "sample_info",
        "sample_info_covariates": ["Sex"],
        "mean_only": True,
        "par_prior": False,
        "ref_batch": "B",
    }

    run_mod.run_analysis(cfg)

    assert isinstance(captured["batch_labels"], pd.Series)
    assert captured["batch_labels"].tolist() == ["A", "A", "B", "B", "C", "C"]
    assert isinstance(captured["combat_covariates"], pd.DataFrame)
    assert list(captured["combat_covariates"].columns) == ["Sex"]
    assert captured["combat_covariates"]["Sex"].tolist() == ["F", "M", "F", "M", "F", "M"]
    assert captured["combat_mean_only"] is True
    assert captured["combat_par_prior"] is False
    assert captured["combat_ref_batch"] == "B"
    assert captured["combat_source"] == "SampleInfo.Batch (sample_info)"


def test_run_analysis_cli_combat_batch_only_blocks_perfect_label_confounding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_smoke_stubs(monkeypatch, tmp_path)
    sample_info = pd.DataFrame(
        {
            "Sample_Name": [
                "Exposure_A",
                "Exposure_B",
                "Normal_A",
                "Normal_B",
                "Control_A",
                "Control_B",
            ],
            "Batch": ["A", "A", "B", "B", "C", "C"],
        }
    )
    monkeypatch.setattr(run_mod, "read_sample_info_sheet", lambda _path: sample_info.copy())

    cfg = _build_publication_config(tmp_path)
    cfg["pipeline"]["batch_correction"] = "ComBat"
    cfg["combat"] = {
        "covariate_mode": "none",
        "sample_info_covariates": [],
        "mean_only": False,
        "par_prior": True,
        "ref_batch": None,
    }

    with pytest.raises(ValueError, match="Current sample labels"):
        run_mod.run_analysis(cfg)
