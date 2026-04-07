import numpy as np
import pandas as pd
import pytest


def test_feature_boxplot_displays_ttest_and_pvalue_for_two_groups():
    from visualization.anova_plot import plot_feature_boxplot

    df = pd.DataFrame(
        {
            "FeatA": [10.0, 11.2, 9.8, 10.5, 14.5, 15.2, 16.1, 14.9],
        }
    )
    labels = pd.Series(["Tumor"] * 4 + ["Adjacent"] * 4)

    fig = plot_feature_boxplot(df, labels, "FeatA")
    # Stat annotation is placed on the figure margin (fig.texts), not ax.texts
    all_text = "\n".join(t.get_text() for t in fig.texts)

    assert "P =" in all_text
    assert "T-test" in all_text


def test_feature_boxplot_uses_kruskal_metadata_for_three_groups():
    from visualization.anova_plot import plot_feature_boxplot

    df = pd.DataFrame(
        {
            "FeatA": [10.0, 11.0, 12.0, 18.0, 19.0, 20.0, 28.0, 29.0, 30.0],
        }
    )
    labels = pd.Series(["A"] * 3 + ["B"] * 3 + ["C"] * 3)

    fig = plot_feature_boxplot(df, labels, "FeatA", annotation_method="kruskal")
    all_text = "\n".join(t.get_text() for t in fig.texts)

    assert "P =" in all_text
    assert "Kruskal-Wallis" in all_text
    assert "H =" in all_text
    assert "ANOVA" not in all_text


def test_feature_boxplot_uses_mannwhitney_metadata_for_two_groups():
    from visualization.anova_plot import plot_feature_boxplot

    df = pd.DataFrame(
        {
            "FeatA": [10.0, 10.5, 11.0, 15.0, 15.5, 16.0],
        }
    )
    labels = pd.Series(["Tumor"] * 3 + ["Adjacent"] * 3)

    fig = plot_feature_boxplot(df, labels, "FeatA", annotation_method="mannwhitney")
    all_text = "\n".join(t.get_text() for t in fig.texts)

    assert "P =" in all_text
    assert "Mann-Whitney U" in all_text
    assert "T-test" not in all_text


def test_oplsda_has_fallback_without_pyopls(monkeypatch):
    import analysis.oplsda as oplsda_mod

    monkeypatch.setattr(oplsda_mod, "HAS_PYOPLS", False)
    df = pd.DataFrame(
        np.array(
            [
                [1.0, 2.0, 1.1, 0.9],
                [1.2, 1.8, 1.0, 1.1],
                [0.9, 2.1, 1.2, 1.0],
                [2.5, 3.0, 2.2, 2.0],
                [2.8, 3.2, 2.4, 2.1],
                [2.6, 2.9, 2.3, 1.9],
            ]
        ),
        columns=["F1", "F2", "F3", "F4"],
    )
    labels = pd.Series(["A", "A", "A", "B", "B", "B"])

    result = oplsda_mod.run_oplsda(df, labels, n_components=1, cv_method="loo")

    assert result.scores_predictive.shape == (6, 1)
    assert result.scores_orthogonal.shape == (6, 1)
    assert np.isfinite(result.r2y)
    assert np.isfinite(result.q2)


def test_random_forest_uses_requested_folds_when_valid():
    from analysis.random_forest import run_random_forest

    rng = np.random.RandomState(0)
    df = pd.DataFrame(rng.randn(20, 8), columns=[f"F{i}" for i in range(8)])
    labels = pd.Series(["A"] * 10 + ["B"] * 10)

    result = run_random_forest(df, labels, n_trees=100, cv_folds=5, top_n=5)
    assert result.cv_folds_used == 5
    assert result.confusion_mat.shape == (2, 2)


def test_random_forest_cleans_invalid_feature_names():
    from analysis.random_forest import run_random_forest

    rng = np.random.RandomState(7)
    df = pd.DataFrame(
        rng.randn(20, 6),
        columns=[np.nan, "", "None", "valid_a", "valid_a", "valid_b"],
    )
    labels = pd.Series(["A"] * 10 + ["B"] * 10)

    result = run_random_forest(df, labels, n_trees=100, cv_folds=5, top_n=10)
    feature_names = result.feature_importance["Feature"].astype(str).str.lower()

    assert result.dropped_unnamed_features == 3
    assert not feature_names.isin(["nan", "", "none", "null", "na"]).any()
    assert result.feature_importance["Feature"].astype(str).str.startswith("valid_a").any()


def test_outlier_detection_handles_p_equals_k():
    from analysis.outlier import run_outlier_detection

    rng = np.random.RandomState(1)
    # n=6, p=2, n_components=2 -> k=2 -> p-k=0 edge case
    df = pd.DataFrame(rng.randn(6, 2), columns=["F1", "F2"])

    result = run_outlier_detection(df, n_components=2, alpha=0.05)
    assert np.isfinite(result.dmodx).all()
    assert np.isfinite(result.t2_values).all()


def test_volcano_log2fc_is_finite_for_nonpositive_means():
    from analysis.univariate import volcano_analysis

    df = pd.DataFrame(
        {
            "F1": [-1.0, -2.0, -3.0, -2.5, 0.5, 1.0, 1.5, 2.0],
            "F2": [2.0, 2.1, 1.9, 2.2, -0.8, -1.0, -1.2, -0.9],
            "F3": [0.0, -0.2, 0.1, 0.3, -0.1, 0.0, 0.2, -0.3],
        }
    )
    labels = pd.Series(["A"] * 4 + ["B"] * 4)

    res = volcano_analysis(df, labels, "A", "B", fc_thresh=1.2, p_thresh=0.2)
    assert np.isfinite(res.result_df["log2FC"].values).all()


def test_volcano_accepts_log2_threshold_and_separate_fc_matrix():
    from analysis.univariate import volcano_analysis

    stats_df = pd.DataFrame(
        {
            "F1": [1.0, 1.1, 1.2, 2.0, 2.1, 2.2],
            "F2": [1.5, 1.6, 1.4, 1.6, 1.5, 1.4],
        }
    )
    fc_df = pd.DataFrame(
        {
            "F1": [10.0, 11.0, 9.5, 40.0, 42.0, 38.0],
            "F2": [20.0, 21.0, 19.0, 22.0, 21.0, 20.0],
        }
    )
    labels = pd.Series(["A"] * 3 + ["B"] * 3)

    res = volcano_analysis(
        stats_df,
        labels,
        "B",
        "A",
        log2_fc_thresh=1.0,
        p_thresh=0.2,
        fc_df=fc_df,
    )

    f1 = res.result_df.set_index("Feature").loc["F1"]
    assert res.log2_fc_thresh == pytest.approx(1.0)
    assert res.fc_thresh == pytest.approx(2.0)
    assert f1["log2FC"] > 1.0
    assert bool(f1["significant"]) is True


def test_compose_output_suffix_appends_timestamp_to_short_suffix():
    from scripts.run_from_config import compose_output_suffix

    suffix = compose_output_suffix("_vfc2p0", timestamp="20260330_120000")
    assert suffix == "_vfc2p0_20260330_120000"


def test_compose_output_suffix_uses_timestamp_even_without_base_suffix():
    from scripts.run_from_config import compose_output_suffix

    suffix = compose_output_suffix("", timestamp="20260330_120000")
    assert suffix == "_20260330_120000"


def test_volcano_fdr_mode_marks_metadata_and_columns():
    from analysis.univariate import volcano_analysis

    rng = np.random.RandomState(9)
    df = pd.DataFrame(rng.randn(24, 20), columns=[f"F{i}" for i in range(20)])
    labels = pd.Series(["A"] * 12 + ["B"] * 12)

    res = volcano_analysis(df, labels, "A", "B", use_fdr=True, fdr_method="fdr_bh")
    assert res.use_fdr is True
    assert res.fdr_method == "fdr_bh"
    assert "pvalue_raw" in res.result_df.columns
    assert "pvalue_adj" in res.result_df.columns
    assert "significance_pvalue" in res.result_df.columns


def test_roc_single_feature_uses_cross_validated_probabilities(monkeypatch):
    import analysis.roc as roc_mod

    df = pd.DataFrame(
        {
            "F1": [0.0, 1.0, 0.2, 0.8, 0.1, 0.9],
            "F2": [1.0, 2.0, 1.1, 1.9, 1.2, 2.1],
        }
    )
    labels = pd.Series(["A", "B", "A", "B", "A", "B"])

    single_prob = np.array([0.10, 0.90, 0.20, 0.80, 0.30, 0.70], dtype=float)
    multi_prob = np.array([0.15, 0.85, 0.25, 0.75, 0.35, 0.65], dtype=float)
    call_dims = []

    def _fake_cv_predict(clf, x, y, cv=None, method=None):
        call_dims.append(x.shape[1])
        prob = single_prob if x.shape[1] == 1 else multi_prob
        return np.column_stack([1 - prob, prob])

    monkeypatch.setattr(roc_mod, "cross_val_predict", _fake_cv_predict)

    result = roc_mod.run_roc_analysis(
        df,
        labels,
        group1="A",
        group2="B",
        top_n=1,
        multi_feature=True,
        cv_folds=3,
    )

    fpr, tpr, _ = roc_mod.roc_curve(np.array([0, 1, 0, 1, 0, 1]), single_prob)
    expected_auc = roc_mod.auc(fpr, tpr)

    assert call_dims.count(1) >= 1
    assert 2 in call_dims
    assert result.single_cv_folds_used == 3
    assert result.multi_cv_folds_used == 3
    assert np.isclose(result.single_rocs[0].auc_score, expected_auc)


def test_roc_requires_two_samples_per_group_for_cv():
    from analysis.roc import run_roc_analysis

    df = pd.DataFrame({"F1": [0.1, 0.2, 0.3, 0.4]})
    labels = pd.Series(["A", "A", "A", "B"])

    with pytest.raises(ValueError, match="At least 2 samples per class"):
        run_roc_analysis(df, labels, group1="A", group2="B", cv_folds=5)
