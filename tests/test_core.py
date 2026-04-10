"""
Core 模組單元測試 — 測試 MetaboAnalyst 6.0 Clone 的所有資料處理功能
"""

import numpy as np
import pandas as pd
import pytest

# ── 測試輔助：建立模擬資料 ──

def make_test_df(n_samples=20, n_features=50, seed=42):
    """建立含部分 NaN 和 0 值的測試 DataFrame"""
    rng = np.random.RandomState(seed)
    data = rng.lognormal(mean=5, sigma=1.5, size=(n_samples, n_features))
    df = pd.DataFrame(data, columns=[f"F{i+1}" for i in range(n_features)])
    # 插入一些 0 和 NaN
    df.iloc[0, 0] = 0
    df.iloc[1, 1] = 0
    df.iloc[2, 2] = np.nan
    df.iloc[3, 3] = np.nan
    df.iloc[4, 4] = np.nan
    # 一個高缺失率特徵（60% 缺失）
    df.iloc[:12, -1] = np.nan
    return df


def make_labels(n_samples=20):
    """建立分組標籤"""
    return pd.Series(["GroupA"] * 10 + ["GroupB"] * 10)


# ═══════════════════════════════════════
# 1. Missing Values 模組
# ═══════════════════════════════════════

class TestMissingValues:

    def test_replace_zero_with_nan(self):
        from core.missing_values import replace_zero_with_nan
        df = pd.DataFrame({"A": [1, 0, 3], "B": [0, 2, 0]})
        result = replace_zero_with_nan(df)
        assert result.isna().sum().sum() == 3
        assert result["A"].iloc[1] != result["A"].iloc[1]  # NaN != NaN

    def test_remove_missing_percent_default(self):
        from core.missing_values import remove_missing_percent
        df = make_test_df()
        n_before = df.shape[1]
        result = remove_missing_percent(df, threshold=0.5)
        # 最後一欄有 60% 缺失，應被移除
        assert result.shape[1] == n_before - 1
        assert "F50" not in result.columns

    def test_remove_missing_percent_strict(self):
        from core.missing_values import remove_missing_percent
        df = make_test_df()
        result = remove_missing_percent(df, threshold=0.01)
        # 嚴格門檻，應移除更多
        assert result.shape[1] < df.shape[1]

    def test_impute_min_lod(self):
        from core.missing_values import impute_missing
        df = make_test_df()
        result = impute_missing(df, method="min")
        assert result.isna().sum().sum() == 0
        # 填補值應為 min(正值)/5
        for col in df.columns:
            if df[col].isna().any():
                pos_vals = df[col][df[col] > 0]
                if len(pos_vals) > 0:
                    expected_lod = pos_vals.min() / 5
                    filled = result[col][df[col].isna()]
                    assert np.allclose(filled, expected_lod)

    def test_impute_mean(self):
        from core.missing_values import impute_missing
        df = make_test_df()
        result = impute_missing(df, method="mean")
        assert result.isna().sum().sum() == 0

    def test_impute_median(self):
        from core.missing_values import impute_missing
        df = make_test_df()
        result = impute_missing(df, method="median")
        assert result.isna().sum().sum() == 0

    def test_impute_exclude(self):
        from core.missing_values import impute_missing
        df = make_test_df()
        result = impute_missing(df, method="exclude")
        assert result.isna().sum().sum() == 0
        assert result.shape[1] < df.shape[1]

    def test_impute_knn(self):
        from core.missing_values import impute_missing
        df = make_test_df()
        result = impute_missing(df, method="knn")
        assert result.isna().sum().sum() == 0
        assert result.shape == df.shape

    def test_impute_invalid_method(self):
        from core.missing_values import impute_missing
        df = make_test_df()
        with pytest.raises(ValueError, match="未知"):
            impute_missing(df, method="invalid_method")

    def test_impute_knn_preserves_all_nan_columns(self):
        from core.missing_values import impute_missing

        df = pd.DataFrame(
            {
                "F_knn": [1.0, np.nan, 3.0, 4.0],
                "F_all_nan": [np.nan, np.nan, np.nan, np.nan],
            }
        )

        result = impute_missing(df, method="knn")
        assert result["F_knn"].isna().sum() == 0
        assert result["F_all_nan"].isna().all()

    def test_impute_missing_by_feature_supports_marker_aware_mix(self):
        from core.missing_values import impute_missing_by_feature

        df = pd.DataFrame(
            {
                "F_marker": [10.0, np.nan, 5.0, np.nan],
                "F_regular": [1.0, np.nan, 3.0, 4.0],
            }
        )

        result, resolved = impute_missing_by_feature(
            df,
            feature_methods={"F_marker": "min", "F_regular": "knn"},
            default_method="knn",
        )

        assert result.loc[1, "F_marker"] == 1.0
        assert result.loc[3, "F_marker"] == 1.0
        assert result["F_regular"].isna().sum() == 0
        assert resolved.to_dict() == {"F_marker": "min", "F_regular": "knn"}


# ═══════════════════════════════════════
# 2. Filtering 模組
# ═══════════════════════════════════════

class TestFiltering:

    def test_auto_cutoff(self):
        from core.filtering import get_auto_cutoff
        assert get_auto_cutoff(100) == 0.05
        assert get_auto_cutoff(249) == 0.05
        assert get_auto_cutoff(250) == 0.10
        assert get_auto_cutoff(499) == 0.10
        assert get_auto_cutoff(500) == 0.25
        assert get_auto_cutoff(999) == 0.25
        assert get_auto_cutoff(1000) == 0.40
        assert get_auto_cutoff(5000) == 0.40

    def test_filter_iqr(self):
        from core.filtering import filter_features
        df = make_test_df()
        df = df.fillna(df.mean())
        result = filter_features(df, method="iqr")
        assert result.shape[1] < df.shape[1]
        assert result.shape[0] == df.shape[0]  # 樣本數不變

    def test_filter_sd(self):
        from core.filtering import filter_features
        df = make_test_df().fillna(0)
        result = filter_features(df, method="sd", cutoff=0.10)
        assert result.shape[1] <= df.shape[1]

    def test_filter_mad(self):
        from core.filtering import filter_features
        df = make_test_df().fillna(0)
        result = filter_features(df, method="mad", cutoff=0.10)
        assert result.shape[1] <= df.shape[1]

    def test_filter_max_features(self):
        from core.filtering import filter_features
        rng = np.random.RandomState(42)
        big_df = pd.DataFrame(
            rng.randn(10, 200),
            columns=[f"F{i}" for i in range(200)]
        )
        result = filter_features(big_df, method="iqr", cutoff=0.0, max_features=50)
        assert result.shape[1] <= 50

    def test_filter_invalid_method(self):
        from core.filtering import filter_features
        df = make_test_df().fillna(0)
        with pytest.raises(ValueError, match="未知"):
            filter_features(df, method="invalid")

    def test_compute_filter_scores(self):
        from core.filtering import compute_filter_scores
        df = make_test_df().fillna(0)
        scores = compute_filter_scores(df, "iqr")
        assert len(scores) == df.shape[1]
        assert scores.min() >= 0

    def test_filter_qc_rsd(self):
        from core.filtering import filter_by_qc_rsd
        df = make_test_df().fillna(1)
        qc_mask = np.array([True]*5 + [False]*15)
        result = filter_by_qc_rsd(df, qc_mask, rsd_threshold=0.5)
        assert result.shape[0] == 15  # QC 樣本被移除

    def test_filter_qc_rsd_exempts_marker_features(self):
        from core.filtering import filter_by_qc_rsd

        df = pd.DataFrame(
            {
                "F_marker": [np.nan, np.nan, 10.0, 12.0],
                "F_drop": [10.0, 50.0, 20.0, 30.0],
                "F_keep": [100.0, 110.0, 200.0, 300.0],
            },
            index=["QC_1", "QC_2", "S1", "S2"],
        )
        qc_mask = np.array([True, True, False, False])

        result, stats = filter_by_qc_rsd(
            df,
            qc_mask,
            rsd_threshold=0.25,
            exempt_columns=pd.Series(
                {"F_marker": True, "F_drop": False, "F_keep": False}
            ),
            return_stats=True,
        )

        assert list(result.columns) == ["F_marker", "F_keep"]
        assert bool(stats.loc["F_marker", "qc_rsd_exempted"]) is True
        assert pd.isna(stats.loc["F_marker", "qc_rsd"])

    def test_filter_qc_rsd_matches_population_qc_cv_boundary(self):
        from core.filtering import filter_by_qc_rsd

        df = pd.DataFrame(
            {
                "F_boundary": [
                    720679.9877340215,
                    74499149.40340534,
                    42048672.26438606,
                    67314448.69160342,
                    35049137.23416223,
                    40906353.69822981,
                    57104871.31959073,
                    1.0,
                    2.0,
                ],
            },
            index=["QC_1", "QC_2", "QC_3", "QC_4", "QC_5", "QC_6", "QC_7", "S1", "S2"],
        )
        qc_mask = np.array([True, True, True, True, True, True, True, False, False])

        result, stats = filter_by_qc_rsd(df, qc_mask, rsd_threshold=0.5, return_stats=True)

        assert "F_boundary" in result.columns
        assert stats.loc["F_boundary", "qc_rsd"] == pytest.approx(0.4996763353582288)
        assert bool(stats.loc["F_boundary", "qc_rsd_pass"]) is True


# ═══════════════════════════════════════
# 3. Normalization 模組
# ═══════════════════════════════════════

class TestNormalization:

    def _get_clean_df(self):
        df = make_test_df().fillna(1)
        df = df.clip(lower=0.01)  # 避免零值
        return df

    def test_sum_norm(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        result = apply_row_norm(df, method="SumNorm")
        # 每行加總應約為 1000
        row_sums = result.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1000, rtol=1e-10)

    def test_median_norm(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        result = apply_row_norm(df, method="MedianNorm")
        assert result.shape == df.shape
        assert not result.isna().any().any()

    def test_quantile_norm(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        try:
            result = apply_row_norm(df, method="QuantileNorm")
            assert result.shape == df.shape
        except ImportError:
            pytest.skip("qnorm 未安裝")

    def test_none_norm(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        result = apply_row_norm(df, method="None")
        pd.testing.assert_frame_equal(result, df)

    def test_comp_norm(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        ref_feature = df.columns[0]
        result = apply_row_norm(df, method="CompNorm", ref_feature=ref_feature)
        assert ref_feature not in result.columns
        assert result.shape[1] == df.shape[1] - 1

    def test_pqn_sample(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        ref = df.iloc[0]
        result = apply_row_norm(df, method="SamplePQN", ref_sample=ref)
        assert result.shape == df.shape

    def test_invalid_norm(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        with pytest.raises(ValueError, match="Unsupported"):
            apply_row_norm(df, method="InvalidMethod")

    def test_missing_ref_raises(self):
        from core.normalization import apply_row_norm
        df = self._get_clean_df()
        with pytest.raises(ValueError, match="ref_sample"):
            apply_row_norm(df, method="SamplePQN")


# ═══════════════════════════════════════
# 4. Transformation 模組
# ═══════════════════════════════════════

class TestTransformation:

    def _get_clean_df(self):
        return make_test_df().fillna(1).clip(lower=0.01)

    def test_glog2_basic(self):
        from core.transformation import apply_transform
        df = self._get_clean_df()
        result = apply_transform(df, method="LogNorm")
        assert result.shape == df.shape
        assert not result.isna().any().any()
        # 所有值都是有限的
        assert np.isfinite(result.values).all()

    def test_glog2_handles_zero(self):
        from core.transformation import DataTransformer
        df = pd.DataFrame({"A": [0.0, 1.0, 10.0, 100.0]})
        result = DataTransformer.glog2(df)
        assert np.isfinite(result.values).all()  # 0 值不會產生 -inf

    def test_glog2_handles_negative(self):
        from core.transformation import DataTransformer
        df = pd.DataFrame({"A": [-5.0, -1.0, 0.0, 1.0, 5.0]})
        result = DataTransformer.glog2(df)
        assert np.isfinite(result.values).all()

    def test_glog2_large_x_approx_log2(self):
        """x >> lambda 時，glog2(x) ≈ log2(x)"""
        from core.transformation import DataTransformer
        df = pd.DataFrame({"A": [1000.0, 10000.0, 100000.0]})
        result = DataTransformer.glog2(df)
        expected = np.log2(df)
        np.testing.assert_allclose(result.values, expected.values, rtol=1e-3)

    def test_glog10(self):
        from core.transformation import apply_transform
        df = self._get_clean_df()
        result = apply_transform(df, method="Log10Norm")
        assert np.isfinite(result.values).all()

    def test_gsqrt(self):
        from core.transformation import apply_transform
        df = self._get_clean_df()
        result = apply_transform(df, method="SrNorm")
        assert np.isfinite(result.values).all()
        assert (result.values >= 0).all()

    def test_cube_root(self):
        from core.transformation import apply_transform
        df = pd.DataFrame({"A": [-8.0, -1.0, 0.0, 1.0, 8.0]})
        result = apply_transform(df, method="CrNorm")
        expected = pd.DataFrame({"A": [-2.0, -1.0, 0.0, 1.0, 2.0]})
        np.testing.assert_allclose(result.values, expected.values, atol=1e-10)

    def test_none_transform(self):
        from core.transformation import apply_transform
        df = self._get_clean_df()
        result = apply_transform(df, method="None")
        pd.testing.assert_frame_equal(result, df)

    def test_lambda_calculation(self):
        from core.transformation import DataTransformer
        df = pd.DataFrame({"A": [0.1, 1.0, 10.0], "B": [0.5, 5.0, 50.0]})
        lam = DataTransformer._get_lambda(df)
        assert lam == 0.1 / 10  # min non-zero abs / 10

    def test_invalid_transform(self):
        from core.transformation import apply_transform
        df = self._get_clean_df()
        with pytest.raises(ValueError, match="未知"):
            apply_transform(df, method="InvalidTransform")


# ═══════════════════════════════════════
# 5. Scaling 模組
# ═══════════════════════════════════════

class TestScaling:

    def _get_clean_df(self):
        return make_test_df().fillna(1).clip(lower=0.01)

    def test_mean_center(self):
        from core.scaling import apply_scaling
        df = self._get_clean_df()
        result = apply_scaling(df, method="MeanCenter")
        # 每欄均值應為 0
        col_means = result.mean()
        np.testing.assert_allclose(col_means, 0, atol=1e-10)

    def test_auto_scale(self):
        from core.scaling import apply_scaling
        df = self._get_clean_df()
        result = apply_scaling(df, method="AutoNorm")
        # 每欄均值 ≈ 0，標準差 ≈ 1
        np.testing.assert_allclose(result.mean(), 0, atol=1e-10)
        np.testing.assert_allclose(result.std(), 1, atol=1e-10)

    def test_pareto_scale(self):
        from core.scaling import apply_scaling
        df = self._get_clean_df()
        result = apply_scaling(df, method="ParetoNorm")
        np.testing.assert_allclose(result.mean(), 0, atol=1e-10)
        assert result.shape == df.shape

    def test_range_scale(self):
        from core.scaling import apply_scaling
        df = self._get_clean_df()
        result = apply_scaling(df, method="RangeNorm")
        np.testing.assert_allclose(result.mean(), 0, atol=1e-10)

    def test_none_scaling(self):
        from core.scaling import apply_scaling
        df = self._get_clean_df()
        result = apply_scaling(df, method="None")
        pd.testing.assert_frame_equal(result, df)

    def test_constant_feature_auto_scale(self):
        """常數特徵（sd=0）不應產生 inf"""
        from core.scaling import apply_scaling
        df = pd.DataFrame({"A": [5.0]*10, "B": np.arange(10, dtype=float)})
        result = apply_scaling(df, method="AutoNorm")
        # 常數欄位應為 NaN（sd=0），不是 inf
        assert not np.isinf(result.values).any()

    def test_invalid_scaling(self):
        from core.scaling import apply_scaling
        df = self._get_clean_df()
        with pytest.raises(ValueError, match="未知"):
            apply_scaling(df, method="InvalidScale")


# ═══════════════════════════════════════
# 6. Pipeline 模組
# ═══════════════════════════════════════

class TestPipeline:

    def test_full_pipeline(self):
        from core.pipeline import MetaboAnalystPipeline
        df = make_test_df()
        labels = make_labels()
        pipe = MetaboAnalystPipeline(df, labels)
        result = pipe.run_pipeline(
            missing_thresh=0.5,
            impute_method="min",
            filter_method="iqr",
            row_norm="SumNorm",
            transform="LogNorm",
            scaling="AutoNorm",
        )
        assert result.shape[0] == df.shape[0]
        assert result.shape[1] <= df.shape[1]
        assert result.isna().sum().sum() == 0
        assert len(pipe.log) == 7  # 7 步驟日誌
        assert pipe.processed is not None

    def test_pipeline_none_options(self):
        from core.pipeline import MetaboAnalystPipeline
        df = make_test_df()
        labels = make_labels()
        pipe = MetaboAnalystPipeline(df, labels)
        result = pipe.run_pipeline(
            row_norm="None",
            transform="None",
            scaling="None",
        )
        assert result.isna().sum().sum() == 0

    def test_pipeline_steps_saved(self):
        from core.pipeline import MetaboAnalystPipeline
        df = make_test_df()
        labels = make_labels()
        pipe = MetaboAnalystPipeline(df, labels)
        pipe.run_pipeline()
        expected_steps = [
            "zero_to_nan", "remove_missing", "imputed",
            "filtered", "row_normed", "transformed", "scaled"
        ]
        for step in expected_steps:
            assert step in pipe.steps

    def test_pipeline_median_impute(self):
        from core.pipeline import MetaboAnalystPipeline
        df = make_test_df()
        labels = make_labels()
        pipe = MetaboAnalystPipeline(df, labels)
        result = pipe.run_pipeline(impute_method="median")
        assert result.isna().sum().sum() == 0

    def test_pipeline_preserves_index(self):
        from core.pipeline import MetaboAnalystPipeline
        df = make_test_df()
        df.index = [f"Sample_{i}" for i in range(len(df))]
        labels = make_labels()
        pipe = MetaboAnalystPipeline(df, labels)
        result = pipe.run_pipeline()
        assert list(result.index) == list(df.index)

    def test_pipeline_qc_rsd_removes_qc_rows_and_high_rsd_features(self):
        from core.pipeline import MetaboAnalystPipeline

        df = pd.DataFrame(
            {
                "F_keep": [100.0, 110.0, 90.0, 95.0, 120.0, 130.0],
                "F_drop": [10.0, 30.0, 12.0, 11.0, 9.0, 10.0],
            },
            index=["QC_1", "QC_2", "S1", "S2", "S3", "S4"],
        )
        labels = pd.Series(
            ["QC", "QC", "A", "A", "B", "B"],
            index=df.index,
        )

        pipe = MetaboAnalystPipeline(df, labels)
        result = pipe.run_pipeline(
            filter_method="None",
            row_norm="None",
            transform="None",
            scaling="None",
            qc_rsd_enabled=True,
            qc_rsd_threshold=0.2,
        )

        assert result.shape[0] == 4
        assert list(result.index) == ["S1", "S2", "S3", "S4"]
        assert "F_keep" in result.columns
        assert "F_drop" not in result.columns
        assert pipe.processed_labels is not None
        assert len(pipe.processed_labels) == 4
        assert not pipe.processed_labels.astype(str).str.contains("qc", case=False).any()
        assert "qc_rsd" in pipe.step_feature_metadata
        assert bool(pipe.step_feature_metadata["qc_rsd"].loc["F_drop", "kept_after_qc_rsd"]) is False
        assert any("Step 3a: QC-RSD filtering" in line for line in pipe.log)

    def test_pipeline_marker_aware_imputation_and_qc_rsd_exemption(self):
        from core.pipeline import MetaboAnalystPipeline

        df = pd.DataFrame(
            {
                "F_marker": [0.0, 0.0, 10.0, 0.0],
                "F_regular": [1.0, 1.1, 3.0, 4.0],
                "F_drop": [10.0, 50.0, 20.0, 30.0],
            },
            index=["QC_1", "QC_2", "S1", "S2"],
        )
        labels = pd.Series(["QC", "QC", "A", "B"], index=df.index)
        feature_metadata = pd.DataFrame(
            {"is_Presence_Absence_Marker": [True, False, False]},
            index=["F_marker", "F_regular", "F_drop"],
        )

        pipe = MetaboAnalystPipeline(df, labels, feature_metadata=feature_metadata)
        result = pipe.run_pipeline(
            missing_thresh=1.0,
            impute_method="knn",
            filter_method="None",
            row_norm="None",
            transform="None",
            scaling="None",
            qc_rsd_enabled=True,
            qc_rsd_threshold=0.25,
        )

        assert list(result.index) == ["S1", "S2"]
        assert "F_marker" in result.columns
        assert "F_regular" in result.columns
        assert "F_drop" not in result.columns
        assert result.loc["S2", "F_marker"] == 2.0
        assert pipe.processed_feature_metadata is not None
        assert bool(pipe.processed_feature_metadata.loc["F_marker", "qc_rsd_exempted"]) is True
        assert pipe.processed_feature_metadata.loc["F_marker", "qc_detect_ratio"] == 0
        assert pd.isna(pipe.processed_feature_metadata.loc["F_marker", "qc_rsd"])
        assert pipe.processed_feature_metadata.loc["F_marker", "imputation_method"] == "min"
        assert pipe.processed_feature_metadata.loc["F_regular", "imputation_method"] == "knn"


class TestSampleInfoFactors:

    def _make_sample_info(self):
        return pd.DataFrame(
            {
                "MetaA": ["x", "x", "x"],
                "MetaB": ["x", "x", "x"],
                "MetaC": ["x", "x", "x"],
                "MetaD": ["x", "x", "x"],
                "SampleName": ["S1", "S2", "S3"],
                "FactorColF": [0.5, 1.0, 2.0],  # Column F (index 5)
                "OtherNumeric": [100, 200, 300],
            }
        )

    def test_detect_factor_columns_prefers_column_f(self):
        from core.sample_info import detect_factor_columns

        sample_info = self._make_sample_info()
        columns, default_col = detect_factor_columns(sample_info)
        assert "FactorColF" in columns
        assert default_col == "FactorColF"

    def test_build_aligned_factors_success(self):
        from core.sample_info import build_aligned_factors

        sample_info = self._make_sample_info()
        sample_ids = pd.Index(["S1", "S2", "S3"])
        factors, meta = build_aligned_factors(
            sample_info=sample_info,
            sample_ids=sample_ids,
            factor_column="FactorColF",
        )
        assert list(factors.index) == list(sample_ids)
        np.testing.assert_allclose(factors.values, [0.5, 1.0, 2.0])
        assert meta["sample_id_column"] == "SampleName"
        assert meta["factor_column"] == "FactorColF"

    def test_build_aligned_factors_missing_sample_raises(self):
        from core.sample_info import build_aligned_factors

        sample_info = self._make_sample_info()
        sample_ids = pd.Index(["S1", "S2", "S4"])
        with pytest.raises(ValueError, match="missing factor values"):
            build_aligned_factors(
                sample_info=sample_info,
                sample_ids=sample_ids,
                factor_column="FactorColF",
            )

    def test_build_aligned_factors_matches_normalized_sample_names(self):
        from core.sample_info import build_aligned_factors

        sample_info = pd.DataFrame(
            {
                "Sample_Name": [
                    "Breast Cancer Tissue_ pooled_QC_1",
                    "Tumor tissue BC2286 DNA +RNA",
                    "Normal tissue BC2257 DNA",
                ],
                "FactorColF": [1.0, 2.0, 3.0],
            }
        )
        sample_ids = pd.Index(
            [
                "Breast_Cancer_Tissue_pooled_QC_1",
                "TumorBC2286_DNAandRNA",
                "NormalBC2257_DNA",
            ]
        )

        factors, meta = build_aligned_factors(
            sample_info=sample_info,
            sample_ids=sample_ids,
            factor_column="FactorColF",
        )

        np.testing.assert_allclose(factors.values, [1.0, 2.0, 3.0])
        assert meta["n_fuzzy_matches"] == 0

    def test_build_aligned_factors_does_not_guess_nearby_sample_ids(self):
        from core.sample_info import build_aligned_factors

        sample_info = pd.DataFrame(
            {
                "Sample_Name": ["Tumor tissue BC2287 DNA"],
                "FactorColF": [2.0],
            }
        )

        with pytest.raises(ValueError, match="no sample ID column matches"):
            build_aligned_factors(
                sample_info=sample_info,
                sample_ids=pd.Index(["TumorBC2286_DNA"]),
                factor_column="FactorColF",
            )

    def test_build_aligned_factors_does_not_use_fuzzy_substitution_for_partial_overlap(self):
        from core.sample_info import build_aligned_factors

        sample_info = pd.DataFrame(
            {
                "Sample_Name": [
                    "Tumor tissue BC2287 DNA",
                    "Tumor tissue BC2290 DNA",
                ],
                "FactorColF": [2.0, 4.0],
            }
        )

        with pytest.raises(ValueError, match="missing factor values"):
            build_aligned_factors(
                sample_info=sample_info,
                sample_ids=pd.Index(["TumorBC2286_DNA", "TumorBC2290_DNA"]),
                factor_column="FactorColF",
            )

    def test_pipeline_log_records_specnorm_source(self):
        from core.pipeline import MetaboAnalystPipeline

        df = pd.DataFrame(
            {
                "F1": [10.0, 20.0, 30.0],
                "F2": [5.0, 10.0, 15.0],
            },
            index=["S1", "S2", "S3"],
        )
        labels = pd.Series(["A", "A", "B"], index=df.index)
        factors = pd.Series([0.5, 1.0, 2.0], index=df.index)

        pipe = MetaboAnalystPipeline(df, labels)
        result = pipe.run_pipeline(
            missing_thresh=1.0,
            filter_method="None",
            row_norm="SpecNorm",
            transform="None",
            scaling="None",
            factors=factors,
            factor_source="SampleInfo[FactorColF]",
        )
        assert result.shape == df.shape
        assert any("SampleInfo[FactorColF]" in line for line in pipe.log)
        assert any("method=SpecNorm" in line for line in pipe.log)


class TestQCUtils:

    def test_align_labels_to_data_by_index(self):
        from core.qc import align_labels_to_data

        data = pd.DataFrame(
            {"F1": [1.0, 2.0, 3.0]},
            index=["S1", "S2", "S3"],
        )
        labels = pd.Series(
            ["B", "A", "QC"],
            index=["S3", "S1", "S2"],
        )

        aligned = align_labels_to_data(data, labels)
        assert list(aligned.index) == ["S1", "S2", "S3"]
        assert list(aligned.values) == ["A", "QC", "B"]

    def test_exclude_qc_samples(self):
        from core.qc import exclude_qc_samples

        data = pd.DataFrame(
            {"F1": [10.0, 20.0, 30.0, 40.0]},
            index=["S1", "S2", "S3", "S4"],
        )
        labels = pd.Series(
            ["Case", "QC_pool", "Control", "qc_02"],
            index=data.index,
        )

        filtered_data, filtered_labels, removed = exclude_qc_samples(data, labels)
        assert removed == 2
        assert list(filtered_data.index) == ["S1", "S3"]
        assert list(filtered_labels.values) == ["Case", "Control"]


class TestQCRSDEdgeCases:

    def test_single_qc_raises_value_error(self):
        """Single QC replicate should raise, not silently empty all features."""
        from core.filtering import filter_by_qc_rsd

        df = pd.DataFrame(
            {"F1": [100.0, 200.0, 300.0], "F2": [10.0, 20.0, 30.0]},
            index=["QC_1", "S1", "S2"],
        )
        qc_mask = np.array([True, False, False])

        with pytest.raises(ValueError, match="at least 2"):
            filter_by_qc_rsd(df, qc_mask, rsd_threshold=0.25)

    def test_two_qc_works_normally(self):
        """Two QC replicates should work fine."""
        from core.filtering import filter_by_qc_rsd

        df = pd.DataFrame(
            {
                "F_keep": [100.0, 110.0, 200.0, 300.0],
                "F_drop": [10.0, 50.0, 20.0, 30.0],
            },
            index=["QC_1", "QC_2", "S1", "S2"],
        )
        qc_mask = np.array([True, True, False, False])

        result = filter_by_qc_rsd(df, qc_mask, rsd_threshold=0.25)
        assert result.shape[0] == 2
        assert "F_keep" in result.columns
        assert "F_drop" not in result.columns


class TestPLSDAEdgeCases:

    def test_single_feature_raises_value_error(self):
        """PLS-DA with a single feature should raise a clear error."""
        from analysis.plsda import run_plsda

        df = pd.DataFrame({"F1": [1.0, 2.0, 3.0, 4.0]})
        labels = pd.Series(["A", "A", "B", "B"])

        with pytest.raises(ValueError, match="at least 2 features"):
            run_plsda(df, labels, n_components=2)

    def test_two_features_works(self):
        """PLS-DA with 2 features should work (n_components clamped to 1)."""
        from analysis.plsda import run_plsda

        rng = np.random.RandomState(42)
        df = pd.DataFrame(
            rng.randn(20, 2),
            columns=["F1", "F2"],
            index=[f"S{i}" for i in range(20)],
        )
        labels = pd.Series(["A"] * 10 + ["B"] * 10, index=df.index)

        result = run_plsda(df, labels, n_components=3)
        assert result.scores.shape[1] == 1


class TestNormResetCheckpoint:

    def test_reset_restores_filtered_data(self):
        """After normalization, reset should restore to post-filter state."""
        from core.pipeline import MetaboAnalystPipeline

        rng = np.random.RandomState(42)
        df = pd.DataFrame(
            rng.lognormal(5, 1.5, (20, 50)),
            columns=[f"F{i}" for i in range(50)],
        )
        labels = pd.Series(["A"] * 10 + ["B"] * 10)

        pipe = MetaboAnalystPipeline(df, labels)
        filtered = pipe.run_pipeline(
            filter_method="iqr",
            row_norm="None",
            transform="None",
            scaling="None",
        )
        checkpoint = filtered.copy()
        assert filtered.shape[1] <= df.shape[1]

        pipe2 = MetaboAnalystPipeline(filtered, labels)
        normed = pipe2.run_pipeline(
            filter_method="None",
            row_norm="None",
            transform="LogNorm",
            scaling="AutoNorm",
        )
        assert not normed.equals(checkpoint)

        restored = checkpoint.copy()
        pd.testing.assert_frame_equal(restored, filtered)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
