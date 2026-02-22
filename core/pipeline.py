"""
MetaboAnalyst-style preprocessing pipeline orchestrator.

Order (fixed):
  Step 0: Zero -> NaN
  Step 1: RemoveMissingPercent
  Step 2: ImputeMissingVar
  Step 3: FilterVariable (+ optional QC-RSD pre-filter)
  Step 4: Row-wise normalization
  Step 5: Transformation
  Step 6: Column-wise scaling
"""

from __future__ import annotations

import pandas as pd

from core.filtering import filter_by_qc_rsd, filter_features
from core.missing_values import impute_missing, remove_missing_percent, replace_zero_with_nan
from core.normalization import apply_row_norm
from core.scaling import apply_scaling
from core.transformation import apply_transform


class MetaboAnalystPipeline:
    """Run preprocessing pipeline and keep snapshots/logs."""

    def __init__(self, df: pd.DataFrame, labels):
        self.raw = df.copy()
        self.labels = labels
        self.processed: pd.DataFrame | None = None
        self.processed_labels: pd.Series | None = None
        self.steps: dict[str, pd.DataFrame] = {}
        self.log: list[str] = []

    def _coerce_labels(self, index: pd.Index) -> pd.Series | None:
        if self.labels is None:
            return None

        if isinstance(self.labels, pd.Series):
            if self.labels.index.equals(index):
                return self.labels.copy()
            # Reindex if possible, otherwise align by position.
            reindexed = self.labels.reindex(index)
            if reindexed.notna().all():
                return reindexed
            return pd.Series(self.labels.values, index=index)

        return pd.Series(self.labels, index=index)

    @staticmethod
    def _build_qc_mask(labels: pd.Series) -> pd.Series:
        return labels.astype(str).str.contains("qc", case=False, na=False)

    def run_pipeline(
        self,
        # Missing value
        missing_thresh: float = 0.5,
        impute_method: str = "min",
        # Filtering
        filter_method: str | None = "iqr",
        filter_cutoff: float | None = None,
        qc_rsd_enabled: bool = False,
        qc_rsd_threshold: float = 0.2,
        # Row normalization
        row_norm: str | None = "None",
        # Transformation
        transform: str | None = "None",
        # Scaling
        scaling: str | None = "None",
        # Optional parameters
        ref_sample=None,
        ref_feature=None,
        group_mask=None,
        factors=None,
        factor_source: str | None = None,
    ) -> pd.DataFrame:
        """Run pipeline in fixed order and return processed dataframe."""
        self.log.clear()
        self.steps.clear()

        df = self.raw.copy()
        labels = self._coerce_labels(df.index)

        # Step 0
        df = replace_zero_with_nan(df)
        self.steps["zero_to_nan"] = df.copy()
        self.log.append("Step 0: Zero values converted to NaN")

        # Step 1
        n_before = df.shape[1]
        df = remove_missing_percent(df, threshold=missing_thresh)
        self.steps["remove_missing"] = df.copy()
        self.log.append(
            "Step 1: Remove missing features "
            f"(threshold={missing_thresh:.0%}, {n_before} -> {df.shape[1]})"
        )

        # Step 2
        df = impute_missing(df, method=impute_method)
        self.steps["imputed"] = df.copy()
        self.log.append(f"Step 2: Impute missing values (method={impute_method})")

        # Step 3a: optional QC-RSD pre-filter
        if qc_rsd_enabled and labels is not None:
            qc_mask = self._build_qc_mask(labels)
            qc_count = int(qc_mask.sum())
            if qc_count > 0:
                n_feat_before_qc = df.shape[1]
                df = filter_by_qc_rsd(
                    df,
                    qc_mask=qc_mask.to_numpy(),
                    rsd_threshold=qc_rsd_threshold,
                )
                labels = labels.loc[~qc_mask].copy()
                self.log.append(
                    "Step 3a: QC-RSD filtering "
                    f"(threshold={qc_rsd_threshold:.2f}, "
                    f"removed_qc_samples={qc_count}, "
                    f"features {n_feat_before_qc} -> {df.shape[1]})"
                )
            else:
                self.log.append("Step 3a: QC-RSD enabled but no QC samples detected")

        # Step 3b: variable filtering
        if filter_method in (None, "None"):
            self.log.append("Step 3b: FilterVariable skipped")
        else:
            n_before = df.shape[1]
            df = filter_features(df, method=filter_method, cutoff=filter_cutoff)
            self.log.append(
                "Step 3b: Filter variables "
                f"(method={filter_method}, {n_before} -> {df.shape[1]})"
            )
        self.steps["filtered"] = df.copy()

        # Step 4
        row_method = row_norm if row_norm is not None else "None"
        df = apply_row_norm(
            df,
            method=row_method,
            ref_sample=ref_sample,
            ref_feature=ref_feature,
            group_mask=group_mask,
            factors=factors,
        )
        self.steps["row_normed"] = df.copy()
        if row_method == "SpecNorm" and factors is not None:
            if isinstance(factors, pd.Series):
                factor_series = factors.reindex(df.index)
            else:
                factor_series = pd.Series(factors, index=df.index)
            factor_series = pd.to_numeric(factor_series, errors="coerce").dropna()
            source_text = factor_source if factor_source else "provided factors"
            if factor_series.empty:
                self.log.append(
                    f"Step 4: Row normalization (method={row_method}, source={source_text})"
                )
            else:
                self.log.append(
                    "Step 4: Row normalization "
                    f"(method={row_method}, source={source_text}, "
                    f"n={len(factor_series)}, "
                    f"min={factor_series.min():.6g}, max={factor_series.max():.6g})"
                )
        else:
            self.log.append(f"Step 4: Row normalization (method={row_method})")

        # Step 5
        trans_method = transform if transform is not None else "None"
        df = apply_transform(df, method=trans_method)
        self.steps["transformed"] = df.copy()
        self.log.append(f"Step 5: Transformation (method={trans_method})")

        # Step 6
        scaling_method = scaling if scaling is not None else "None"
        df = apply_scaling(df, method=scaling_method)
        self.steps["scaled"] = df.copy()
        self.log.append(f"Step 6: Column-wise scaling (method={scaling_method})")

        self.processed = df
        self.processed_labels = labels if labels is not None else None
        return df
