"""
Two-group univariate analysis for volcano plot:
- Student's / Welch's t-test  (unpaired)
- Paired t-test               (paired)
- Wilcoxon rank-sum test       (unpaired, non-parametric)
- Wilcoxon signed-rank test    (paired, non-parametric)
- Fold change
- Optional FDR correction (Benjamini-Hochberg by default)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, ttest_ind, ttest_rel, wilcoxon
from statsmodels.stats.multitest import multipletests


class VolcanoResult:
    def __init__(
        self,
        result_df: pd.DataFrame,
        group1: str,
        group2: str,
        fc_thresh: float,
        p_thresh: float,
        use_fdr: bool,
        fdr_method: str,
        paired: bool = False,
        n_pairs: int | None = None,
    ):
        self.result_df = result_df
        self.group1 = group1
        self.group2 = group2
        self.fc_thresh = fc_thresh
        self.p_thresh = p_thresh
        self.use_fdr = use_fdr
        self.fdr_method = fdr_method
        self.paired = paired
        self.n_pairs = n_pairs

    @property
    def significant(self) -> pd.DataFrame:
        return self.result_df[self.result_df["significant"]]

    @property
    def n_significant(self) -> int:
        return int(self.result_df["significant"].sum())

    @property
    def n_up(self) -> int:
        df = self.result_df
        return int(((df["significant"]) & (df["log2FC"] > 0)).sum())

    @property
    def n_down(self) -> int:
        df = self.result_df
        return int(((df["significant"]) & (df["log2FC"] < 0)).sum())

    @property
    def significance_column(self) -> str:
        return "pvalue_adj" if self.use_fdr else "pvalue"


def _robust_log2fc(mean1: pd.Series, mean2: pd.Series) -> pd.Series:
    """
    Robust fold-change transform for non-positive means.
    Uses a small offset and directional sign from mean difference.
    """
    combined = pd.concat([mean1.abs(), mean2.abs()], axis=0)
    positive = combined[combined > 0]
    offset = (positive.min() / 10) if len(positive) else 1e-12

    ratio = (mean1.abs() + offset) / (mean2.abs() + offset)
    direction = np.sign(mean1 - mean2)
    return np.log2(ratio) * direction


def volcano_analysis(
    df: pd.DataFrame,
    labels,
    group1: str,
    group2: str,
    fc_thresh: float = 2.0,
    p_thresh: float = 0.05,
    equal_var: bool = True,
    nonpar: bool = False,
    use_fdr: bool = True,
    fdr_method: str = "fdr_bh",
    paired: bool = False,
    pair_ids: pd.Series | None = None,
) -> VolcanoResult:
    """
    Two-group univariate analysis for volcano plot.

    Parameters
    ----------
    paired : bool
        If True, use paired tests (ttest_rel / wilcoxon signed-rank).
        Requires *pair_ids* to align samples between groups.
    pair_ids : Series, optional
        Subject IDs aligned to ``df.index``.  Required when ``paired=True``.
        Samples are matched by subject ID across the two groups.
    """
    if hasattr(labels, "values"):
        labels_arr = labels.values
    else:
        labels_arr = np.array(labels)

    n_pairs = None

    if paired:
        if pair_ids is None:
            raise ValueError("pair_ids is required for paired analysis.")

        # Align samples by subject ID
        from core.sample_info import align_paired_samples

        g1, g2, matched = align_paired_samples(
            df, pd.Series(labels_arr, index=df.index),
            group1, group2, pair_ids,
        )
        n_pairs = len(matched)
    else:
        g1 = df[labels_arr == group1]
        g2 = df[labels_arr == group2]

    # Fold change uses group means (consistent with MetaboAnalyst)
    mean1 = g1.mean()
    mean2 = g2.mean()
    log2fc = _robust_log2fc(mean1, mean2)

    pvals_raw = []
    for col in df.columns:
        if paired:
            # Paired: use aligned arrays directly (same order by subject)
            v1 = g1[col].values
            v2 = g2[col].values
            # Drop pairs where either value is NaN
            valid = ~(np.isnan(v1) | np.isnan(v2))
            v1, v2 = v1[valid], v2[valid]
            if len(v1) < 2:
                pvals_raw.append(1.0)
                continue
            try:
                if nonpar:
                    _, pvalue = wilcoxon(v1, v2, alternative="two-sided")
                else:
                    _, pvalue = ttest_rel(v1, v2)
                pvals_raw.append(float(pvalue))
            except Exception:
                pvals_raw.append(1.0)
        else:
            v1 = g1[col].dropna().values
            v2 = g2[col].dropna().values
            if len(v1) < 2 or len(v2) < 2:
                pvals_raw.append(1.0)
                continue
            try:
                if nonpar:
                    _, pvalue = mannwhitneyu(v1, v2, alternative="two-sided")
                else:
                    _, pvalue = ttest_ind(v1, v2, equal_var=equal_var)
                pvals_raw.append(float(pvalue))
            except Exception:
                pvals_raw.append(1.0)

    pvals_raw = np.array(pvals_raw, dtype=float)
    # Guard: NaN p-values (e.g. from constant features) break multipletests entirely
    pvals_raw = np.where(np.isnan(pvals_raw), 1.0, pvals_raw)

    if use_fdr:
        _, pvals_adj, _, _ = multipletests(pvals_raw, method=fdr_method)
    else:
        pvals_adj = pvals_raw.copy()

    significance_p = pvals_adj if use_fdr else pvals_raw
    neg_log10p = -np.log10(np.clip(significance_p, 1e-300, 1.0))
    sig_mask = (np.abs(log2fc) >= np.log2(fc_thresh)) & (significance_p < p_thresh)

    result_df = pd.DataFrame(
        {
            "Feature": df.columns,
            "log2FC": log2fc.values,
            "pvalue": pvals_raw,
            "pvalue_raw": pvals_raw,
            "pvalue_adj": pvals_adj,
            "significance_pvalue": significance_p,
            "neg_log10p": neg_log10p,
            "significant": sig_mask.values if hasattr(sig_mask, "values") else sig_mask,
        }
    )

    return VolcanoResult(
        result_df=result_df,
        group1=group1,
        group2=group2,
        fc_thresh=fc_thresh,
        p_thresh=p_thresh,
        use_fdr=use_fdr,
        fdr_method=fdr_method,
        paired=paired,
        n_pairs=n_pairs,
    )

