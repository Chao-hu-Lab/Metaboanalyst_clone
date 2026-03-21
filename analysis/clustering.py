"""
階層式分群模組 — 用於 Heatmap / Dendrogram 計算

對應 R: hclust() + pheatmap::pheatmap()
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, fcluster, linkage
from scipy.spatial.distance import pdist


def compute_linkage(data: np.ndarray, method: str = "ward", metric: str = "euclidean"):
    """
    計算階層式分群的 linkage matrix

    Parameters
    ----------
    data : 2D array
        資料矩陣
    method : str
        連結方法: ward, complete, average, single
    metric : str
        距離指標: euclidean, correlation, cosine 等
    """
    if method == "ward":
        # ward 方法只支援 euclidean
        return linkage(data, method="ward", metric="euclidean")
    else:
        dist = pdist(data, metric=metric)
        return linkage(dist, method=method)


def select_top_features(df: pd.DataFrame, max_features: int = 2000,
                        by: str = "var") -> pd.DataFrame:
    """
    選擇 top N 變異最大的特徵

    Parameters
    ----------
    df : DataFrame
    max_features : int
        最大特徵數
    by : str
        排序依據: "var" (變異數), "mad" (中位數絕對偏差)
    """
    if df.shape[1] <= max_features:
        return df

    if by == "mad":
        from scipy.stats import median_abs_deviation
        scores = df.apply(median_abs_deviation)
    else:
        scores = df.var()

    top_cols = scores.nlargest(max_features).index
    return df[top_cols]


@dataclass
class ClusteringResult:
    """Hierarchical clustering result container."""

    row_linkage: np.ndarray
    col_linkage: np.ndarray
    data: pd.DataFrame
    labels: pd.Series | np.ndarray
    method: str
    metric: str
    n_clusters: int
    row_clusters: np.ndarray
    cophenetic_corr: float
    sample_names: list[str]
    feature_names: list[str]


def run_clustering(
    data: pd.DataFrame,
    labels,
    method: str = "ward",
    metric: str = "euclidean",
    max_features: int = 2000,
    n_clusters: int | None = None,
) -> ClusteringResult:
    """
    Run hierarchical clustering on both samples and features.

    Parameters
    ----------
    data : DataFrame
        Preprocessed data matrix (samples x features).
    labels : array-like
        Group labels aligned to rows of ``data``.
    method : str, default="ward"
        Linkage method: ward, complete, average, single.
    metric : str, default="euclidean"
        Distance metric: euclidean, correlation, cosine, etc.
    max_features : int, default=2000
        Maximum number of features to cluster.
    n_clusters : int or None, default=None
        Number of clusters for fcluster. Defaults to the number of unique labels.

    Returns
    -------
    ClusteringResult
    """
    if data.shape[0] < 2:
        raise ValueError("At least 2 samples are required for clustering.")
    if data.shape[1] < 2:
        raise ValueError("At least 2 features are required for clustering.")

    labels_arr = labels.values if hasattr(labels, "values") else np.asarray(labels)
    if n_clusters is None:
        n_clusters = max(len(set(labels_arr)), 2)

    plot_df = select_top_features(data, max_features=max_features)

    # Row clustering (samples)
    row_Z = compute_linkage(plot_df.values, method=method, metric=metric)
    row_clusters = fcluster(row_Z, t=n_clusters, criterion="maxclust")

    # Cophenetic correlation for quality assessment
    if method == "ward":
        dist_vec = pdist(plot_df.values, metric="euclidean")
    else:
        dist_vec = pdist(plot_df.values, metric=metric)
    coph_corr, _ = cophenet(row_Z, dist_vec)

    # Column clustering (features)
    col_Z = compute_linkage(plot_df.values.T, method=method, metric=metric)

    return ClusteringResult(
        row_linkage=row_Z,
        col_linkage=col_Z,
        data=plot_df,
        labels=labels_arr,
        method=method,
        metric=metric,
        n_clusters=n_clusters,
        row_clusters=row_clusters,
        cophenetic_corr=coph_corr,
        sample_names=list(plot_df.index),
        feature_names=list(plot_df.columns),
    )
