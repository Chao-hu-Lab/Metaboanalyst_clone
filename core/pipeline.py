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

from ms_core.processing.feature_filter import filter_by_qc_rsd, filter_features
from ms_core.processing.missing_values import (
    impute_missing,
    impute_missing_by_feature,
    normalize_impute_method,
    remove_missing_percent,
    replace_zero_with_nan,
)
from ms_core.processing.normalization import apply_row_norm
from ms_core.processing.scaling import apply_scaling
from ms_core.processing.transformation import apply_transform


class MetaboAnalystPipeline:
    """Run preprocessing pipeline and keep snapshots/logs."""

    def __init__(self, df: pd.DataFrame, labels, feature_metadata: pd.DataFrame | None = None):
        self.raw = df.copy()
        self.labels = labels
        if feature_metadata is None:
            feature_metadata = pd.DataFrame(index=self.raw.columns)
        self.feature_metadata = feature_metadata.reindex(self.raw.columns).copy()
        self.processed: pd.DataFrame | None = None
        self.processed_labels: pd.Series | None = None
        self.processed_feature_metadata: pd.DataFrame | None = None
        self.steps: dict[str, pd.DataFrame] = {}
        self.step_feature_metadata: dict[str, pd.DataFrame] = {}
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
        self.step_feature_metadata.clear()

        df = self.raw.copy()
        labels = self._coerce_labels(df.index)
        feature_metadata = self.feature_metadata.reindex(df.columns).copy()

        # Step 0
        df = replace_zero_with_nan(df)
        self.steps["zero_to_nan"] = df.copy()
        self.step_feature_metadata["zero_to_nan"] = feature_metadata.copy()
        self.log.append("Step 0: Zero values converted to NaN")

        # Step 1
        n_before = df.shape[1]
        df = remove_missing_percent(df, threshold=missing_thresh)
        feature_metadata = feature_metadata.reindex(df.columns)
        pre_impute_df = df.copy()
        self.steps["remove_missing"] = df.copy()
        self.step_feature_metadata["remove_missing"] = feature_metadata.copy()
        self.log.append(
            "Step 1: Remove missing features "
            f"(threshold={missing_thresh:.0%}, {n_before} -> {df.shape[1]})"
        )

        # Step 2
        resolved_impute_method = normalize_impute_method(impute_method)
        marker_mask = pd.Series(False, index=df.columns)
        if "is_Presence_Absence_Marker" in feature_metadata.columns:
            marker_mask = (
                feature_metadata["is_Presence_Absence_Marker"]
                .reindex(df.columns)
                .fillna(False)
                .astype(bool)
            )

        if marker_mask.any():
            per_feature_methods = pd.Series(resolved_impute_method, index=df.columns, dtype=object)
            per_feature_methods.loc[marker_mask] = "min"
            df, resolved_methods = impute_missing_by_feature(
                df,
                feature_methods=per_feature_methods,
                default_method=resolved_impute_method,
            )
            feature_metadata["imputation_method"] = resolved_methods.reindex(df.columns)
            self.log.append(
                "Step 2: Impute missing values "
                f"(marker-aware, marker_features={int(marker_mask.sum())}, "
                f"marker_method=min, default_method={resolved_impute_method})"
            )
        else:
            df = impute_missing(df, method=resolved_impute_method)
            feature_metadata["imputation_method"] = resolved_impute_method
            self.log.append(f"Step 2: Impute missing values (method={resolved_impute_method})")
        self.steps["imputed"] = df.copy()
        self.step_feature_metadata["imputed"] = feature_metadata.copy()

        # Step 3a: optional QC-RSD pre-filter
        if qc_rsd_enabled and labels is not None:
            qc_mask = self._build_qc_mask(labels)
            qc_count = int(qc_mask.sum())
            if qc_count > 0:
                n_feat_before_qc = df.shape[1]
                qc_detect_ratio = (
                    pre_impute_df.loc[qc_mask, df.columns].notna().sum() / qc_count
                ).reindex(df.columns)
                exempt_mask = marker_mask.reindex(df.columns).fillna(False)
                df, qc_stats = filter_by_qc_rsd(
                    df,
                    qc_mask=qc_mask.to_numpy(),
                    rsd_threshold=qc_rsd_threshold,
                    exempt_columns=exempt_mask,
                    return_stats=True,
                )
                qc_stats["qc_detect_ratio"] = qc_detect_ratio
                zero_detect_mask = qc_stats["qc_detect_ratio"].fillna(0).eq(0)
                qc_stats.loc[zero_detect_mask, "qc_rsd"] = pd.NA
                feature_metadata = feature_metadata.join(qc_stats, how="left")
                feature_metadata = feature_metadata.reindex(df.columns)
                labels = labels.loc[~qc_mask].copy()
                self.log.append(
                    "Step 3a: QC-RSD filtering "
                    f"(threshold={qc_rsd_threshold:.2f}, "
                    f"removed_qc_samples={qc_count}, "
                    f"exempted_features={int(exempt_mask.sum())}, "
                    f"features {n_feat_before_qc} -> {df.shape[1]})"
                )
            else:
                feature_metadata["qc_rsd"] = pd.NA
                feature_metadata["qc_rsd_threshold"] = qc_rsd_threshold
                feature_metadata["qc_detect_ratio"] = pd.NA
                feature_metadata["qc_rsd_pass"] = False
                feature_metadata["qc_rsd_exempted"] = marker_mask.reindex(df.columns).fillna(False)
                feature_metadata["kept_after_qc_rsd"] = True
                self.log.append("Step 3a: QC-RSD enabled but no QC samples detected")
        else:
            feature_metadata["qc_rsd"] = pd.NA
            feature_metadata["qc_rsd_threshold"] = pd.NA
            feature_metadata["qc_detect_ratio"] = pd.NA
            feature_metadata["qc_rsd_pass"] = False
            feature_metadata["qc_rsd_exempted"] = False
            feature_metadata["kept_after_qc_rsd"] = True

        # Step 3b: variable filtering
        if filter_method in (None, "None"):
            self.log.append("Step 3b: FilterVariable skipped")
        else:
            n_before = df.shape[1]
            df = filter_features(df, method=filter_method, cutoff=filter_cutoff)
            feature_metadata = feature_metadata.reindex(df.columns)
            self.log.append(
                "Step 3b: Filter variables "
                f"(method={filter_method}, {n_before} -> {df.shape[1]})"
            )
        self.steps["filtered"] = df.copy()
        self.step_feature_metadata["filtered"] = feature_metadata.copy()

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
        self.step_feature_metadata["row_normed"] = feature_metadata.copy()
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
        self.step_feature_metadata["transformed"] = feature_metadata.copy()
        self.log.append(f"Step 5: Transformation (method={trans_method})")

        # Step 6
        scaling_method = scaling if scaling is not None else "None"
        df = apply_scaling(df, method=scaling_method)
        self.steps["scaled"] = df.copy()
        self.step_feature_metadata["scaled"] = feature_metadata.copy()
        self.log.append(f"Step 6: Column-wise scaling (method={scaling_method})")

        self.processed = df
        self.processed_labels = labels if labels is not None else None
        self.processed_feature_metadata = feature_metadata.reindex(df.columns).copy()
        return df
