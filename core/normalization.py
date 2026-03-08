"""
Row-wise normalization utilities used by the preprocessing pipeline.
"""

import numpy as np
import pandas as pd


def _load_qnorm():
    try:
        import qnorm
    except ImportError as exc:
        raise ImportError("Please install qnorm: pip install qnorm") from exc
    return qnorm


ROW_NORM_METHODS = {
    "None": "No normalization",
    "SumNorm": "Normalize by row sum",
    "MedianNorm": "Normalize by row median",
    "SamplePQN": "PQN using a reference sample",
    "GroupPQN": "PQN using a reference group",
    "CompNorm": "Normalize by internal standard",
    "QuantileNorm": "Quantile normalization",
    "SpecNorm": "Normalize by external factors",
}


class RowNormalizer:
    """MetaboAnalyst-style row normalization methods."""

    @staticmethod
    def sum_norm(df: pd.DataFrame) -> pd.DataFrame:
        row_sums = df.sum(axis=1).replace(0, np.nan)
        return df.div(row_sums, axis=0) * 1000

    @staticmethod
    def median_norm(df: pd.DataFrame) -> pd.DataFrame:
        row_medians = df.median(axis=1).replace(0, np.nan)
        return df.div(row_medians, axis=0)

    @staticmethod
    def pqn_sample(df: pd.DataFrame, ref_sample: pd.Series) -> pd.DataFrame:
        ref_sample = ref_sample.replace(0, np.nan)
        quotients = df.div(ref_sample, axis=1)
        factors = quotients.median(axis=1).replace(0, np.nan)
        return df.div(factors, axis=0)

    @staticmethod
    def pqn_group(df: pd.DataFrame, group_mask: np.ndarray) -> pd.DataFrame:
        ref_profile = df[group_mask].mean(axis=0)
        return RowNormalizer.pqn_sample(df, ref_profile)

    @staticmethod
    def comp_norm(df: pd.DataFrame, ref_feature: str) -> pd.DataFrame:
        ref_values = df[ref_feature].replace(0, np.nan)
        result = df.div(ref_values, axis=0) * 1000
        return result.drop(columns=[ref_feature])

    @staticmethod
    def quantile_norm(df: pd.DataFrame) -> pd.DataFrame:
        qnorm = _load_qnorm()
        return qnorm.quantile_normalize(df, axis=0)

    @staticmethod
    def spec_norm(df: pd.DataFrame, factors: pd.Series) -> pd.DataFrame:
        aligned = factors.reindex(df.index).replace(0, np.nan)
        return df.div(aligned, axis=0)


def apply_row_norm(
    df: pd.DataFrame,
    method: str = "None",
    ref_sample: pd.Series = None,
    ref_feature: str = None,
    group_mask: np.ndarray = None,
    factors: pd.Series = None,
) -> pd.DataFrame:
    """Apply the selected row-wise normalization method."""
    norm = RowNormalizer()

    if method in ("None", None):
        return df.copy()
    if method == "SumNorm":
        return norm.sum_norm(df)
    if method == "MedianNorm":
        return norm.median_norm(df)
    if method == "SamplePQN":
        if ref_sample is None:
            raise ValueError("SamplePQN requires ref_sample")
        return norm.pqn_sample(df, ref_sample)
    if method == "GroupPQN":
        if group_mask is None:
            raise ValueError("GroupPQN requires group_mask")
        return norm.pqn_group(df, group_mask)
    if method == "CompNorm":
        if ref_feature is None:
            raise ValueError("CompNorm requires ref_feature")
        return norm.comp_norm(df, ref_feature)
    if method == "QuantileNorm":
        return norm.quantile_norm(df)
    if method == "SpecNorm":
        if factors is None:
            raise ValueError("SpecNorm requires factors")
        return norm.spec_norm(df, factors)
    raise ValueError(f"Unsupported row normalization method: {method}")
