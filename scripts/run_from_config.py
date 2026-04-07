"""
Universal analysis runner — reads a YAML config and executes the full pipeline.

Usage (from project root):
    python scripts/run_from_config.py configs/step4_dnp_specnorm.yaml
    python scripts/run_from_config.py configs/step4_dnp_no_norm.yaml
    python scripts/run_from_config.py configs/dnp_pqn_normalized.yaml
"""

import argparse
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

# Ensure project root on path (scripts/ lives one level below project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl.styles import PatternFill  # noqa: E402

from core.app_config import apply_cli_overrides, dump_yaml, load_yaml_config  # noqa: E402
from core.feature_metadata import FEATURE_MARKER_COLUMN, extract_feature_metadata  # noqa: E402
from core.input_resolver import (  # noqa: E402
    build_labels_from_sample_info,
    detect_sample_type_row_key,
    get_feature_id_column,
    read_input_table,
    require_sample_info_sheet,
    validate_label_consistency,
    validate_sample_info_alignment,
)
from core.pipeline import MetaboAnalystPipeline  # noqa: E402
from core.sample_interface import identify_sample_columns  # noqa: E402
from core.sample_info import read_sample_info_sheet, build_aligned_factors, extract_subject_ids  # noqa: E402
from ms_core.analysis.pca import run_pca  # noqa: E402
from ms_core.analysis.anova import run_anova  # noqa: E402
from ms_core.analysis.univariate import volcano_analysis  # noqa: E402
from ms_core.visualization.pca_plot import plot_pca_score, plot_pca_scree, plot_pca_loading  # noqa: E402
from ms_core.visualization.boxplot import plot_sample_boxplot  # noqa: E402
from ms_core.visualization.density_plot import plot_density  # noqa: E402
from ms_core.visualization.anova_plot import plot_anova_importance, plot_feature_boxplot  # noqa: E402

warnings.filterwarnings("ignore")

TRUE_FILL = PatternFill(fill_type="solid", start_color="C6EFCE", end_color="C6EFCE")
FALSE_FILL = PatternFill(fill_type="solid", start_color="FCE4D6", end_color="FCE4D6")
REDUNDANT_EXPORT_COLUMNS = {
    "qc_rsd_exempted",
    "qc_rsd_threshold",
    "kept_after_qc_rsd",
    "qc_rsd_pass",
    "pvalue_raw",
    "significance_pvalue",
}


# ── Config loader ─────────────────────────────────────────

def load_config(path: str) -> dict:
    """Load and validate a YAML configuration file."""
    return load_yaml_config(path, require_required_sections=True).to_dict(include_runtime=True)


def parse_pair_config(
    raw_pairs: list,
) -> list[tuple[str, str, bool]]:
    """
    Parse volcano_pairs / oplsda_pairs config supporting both formats:
      Old: [["Exposure", "Normal"], ...]
      New: [{"groups": ["Exposure", "Normal"], "paired": true}, ...]
    Returns list of (group1, group2, paired) tuples.
    """
    result = []
    for entry in raw_pairs:
        if isinstance(entry, dict):
            groups = entry["groups"]
            paired = entry.get("paired", False)
        else:
            groups = entry
            paired = False
        result.append((groups[0], groups[1], paired))
    return result


def resolve_volcano_parametric_equal_var(volcano_cfg: Mapping[str, Any]) -> bool:
    """Return the equal-variance flag for unpaired parametric volcano tests."""
    default_key = str(volcano_cfg.get("parametric_test_default", "welch")).strip().lower()
    return default_key == "student"


# ── Data loaders ──────────────────────────────────────────

def assign_group_from_name(name: str) -> str:
    """Infer group label from sample column name (for 'plain' format)."""
    name_lower = name.lower()
    if "qc" in name_lower:
        return "QC"
    if name_lower.startswith("tumor"):
        return "Tumor"
    if name_lower.startswith("normal"):
        return "Normal"
    if name_lower.startswith("benignfat"):
        return "Benignfat"
    if name_lower.startswith("exposure"):
        return "Exposure"
    if name_lower.startswith("control"):
        return "Control"
    return "__EXCLUDE__"


def _annotate_feature_table(
    df: pd.DataFrame,
    feature_metadata: pd.DataFrame | None,
    feature_column: str = "Feature",
) -> pd.DataFrame:
    if feature_metadata is None or feature_metadata.empty or feature_column not in df.columns:
        return df

    meta = feature_metadata.copy()
    if meta.index.name != feature_column:
        meta.index.name = feature_column
    extra_cols = [col for col in meta.columns if col not in df.columns]
    if not extra_cols:
        return df
    return df.merge(meta[extra_cols].reset_index(), on=feature_column, how="left")


def load_data(cfg: dict) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Load Excel data and return (samples x features, labels, feature metadata)."""
    input_cfg = cfg["input"]
    input_file = input_cfg["file"]
    if not input_file:
        raise ValueError("No input file specified. Use --input <path> on the command line.")
    fmt = input_cfg.get("format", "sample_type_row")

    print("=" * 60)
    print(f"Loading data from: {os.path.basename(input_file)}")
    loaded_input = read_input_table(input_file)
    raw = loaded_input.table
    if loaded_input.sheet_name:
        print(f"  Selected worksheet: {loaded_input.sheet_name}")
    feature_col = get_feature_id_column(raw)
    sample_columns = [col for col in identify_sample_columns(raw) if col != feature_col]
    sample_info = require_sample_info_sheet(input_file) if Path(input_file).suffix.lower() in {".xlsx", ".xls"} else None
    sample_type_key = detect_sample_type_row_key(raw, feature_column=feature_col)

    if sample_type_key is not None:
        # Row 0 = Sample_Type labels; rows 1+ = feature values
        id_values = raw[feature_col].astype(str)
        group_rows = raw[id_values == str(sample_type_key)]
        if group_rows.empty:
            raise ValueError("Sample_Type row could not be resolved from the selected worksheet.")
        if len(group_rows) > 1:
            raise ValueError("Sample_Type row must be unique in the selected worksheet.")
        sample_type_row = group_rows.iloc[0]
        valid_sample_cols = [col for col in sample_columns if pd.notna(sample_type_row.get(col))]
        feature_rows = raw[id_values != str(sample_type_key)].copy()
        feature_names = pd.Index(feature_rows[feature_col].astype(str), name="Feature")
        sample_types = sample_type_row.loc[valid_sample_cols].values
        sample_names = np.array(valid_sample_cols)

        data = feature_rows.loc[:, valid_sample_cols].values.T
        data = pd.DataFrame(data, columns=feature_names, index=sample_names)
        data = data.apply(pd.to_numeric, errors="coerce")
        labels = pd.Series(sample_types, index=sample_names, name="Group")
        if sample_info is not None:
            labels = validate_label_consistency(
                data.index,
                labels,
                sample_info,
                observed_label_name="Worksheet Sample_Type",
            )
        feature_metadata = extract_feature_metadata(feature_rows.reset_index(drop=True), feature_names)

    elif fmt == "plain":
        # All rows are features; groups inferred from column names
        feature_names = pd.Index(raw[feature_col].astype(str), name="Feature")
        sample_names = np.array(sample_columns)

        data = raw.loc[:, sample_columns].values.T
        data = pd.DataFrame(data, columns=feature_names, index=sample_names)
        data = data.apply(pd.to_numeric, errors="coerce")
        feature_metadata = extract_feature_metadata(raw.reset_index(drop=True), feature_names)
        if sample_info is not None:
            labels = build_labels_from_sample_info(data.index, sample_info, label_name="Group")
        elif input_cfg.get("plain_label_mode") == "column_names":
            labels = pd.Series(sample_names, index=sample_names, name="Group")
        else:
            labels = pd.Series(
                [assign_group_from_name(n) for n in sample_names],
                index=sample_names, name="Group",
            )

        # Drop excluded samples
        exclude_mask = labels == "__EXCLUDE__"
        if exclude_mask.any():
            excluded = list(sample_names[exclude_mask])
            print(f"  Excluding {len(excluded)} samples: {excluded}")
            data = data.loc[~exclude_mask]
            labels = labels.loc[~exclude_mask]
    else:
        raise ValueError(f"Unknown input format: '{fmt}'. Use 'sample_type_row' or 'plain'.")

    if sample_info is not None:
        validate_sample_info_alignment(data.index, sample_info)

    print(f"  Samples: {data.shape[0]}, Features: {data.shape[1]}")
    print(f"  Groups: {dict(labels.value_counts())}")
    print(f"  Zeros: {(data == 0).sum().sum()} / {data.size}")
    print(f"  Missing: {data.isna().sum().sum()} / {data.size}")
    marker_count = int(feature_metadata[FEATURE_MARKER_COLUMN].sum())
    print(f"  Presence/absence markers: {marker_count}")

    return data, labels, feature_metadata


def _finalize_analysis_matrix(
    df: pd.DataFrame,
    labels: pd.Series,
    included_groups: list[str],
) -> tuple[pd.DataFrame, pd.Series]:
    """Apply the same sample/feature filtering used before downstream analyses."""
    qc_mask = labels.astype(str).str.contains("QC", case=False, na=False)
    if qc_mask.any():
        df = df.loc[~qc_mask]
        labels = labels.loc[~qc_mask]

    if included_groups:
        group_mask = labels.isin(included_groups)
        df = df.loc[group_mask]
        labels = labels.loc[group_mask]

    feat_std = df.std()
    zero_var_feats = feat_std[feat_std == 0].index.tolist()
    if zero_var_feats:
        df = df.drop(columns=zero_var_feats)

    return df, labels


def compose_output_suffix(
    base_suffix: str = "",
    *,
    include_timestamp: bool = True,
    timestamp: str | None = None,
) -> str:
    """Build the final output suffix, appending a timestamp by default."""
    base = (base_suffix or "").strip()
    if base and not base.startswith("_"):
        base = f"_{base}"

    if not include_timestamp:
        return base

    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{ts}" if base else f"_{ts}"


# ── Significant features Excel export ────────────────────

def _export_significant_features_excel(
    sheets: dict, output_dir: str, top_n: int | None = None,
):
    """
    Write a consolidated Excel workbook with significant features from all analyses.

    Sheets collected during the pipeline are written as-is, then a 'Summary'
    sheet is generated that cross-references feature appearances across methods.
    """
    if not sheets:
        print("  No significant feature data collected — skipping Excel export.")
        return

    excel_path = os.path.join(output_dir, "significant_features_summary.xlsx")
    summary_csv_path = os.path.join(output_dir, "Summary.csv")
    summary_sheet_filter = {
        sheet_name: df for sheet_name, df in sheets.items()
        if "oplsda" not in sheet_name.lower()
    }
    feature_tags: dict[str, bool] = {}

    def passes_threshold(sheet_name: str, row: pd.Series) -> bool:
        name = sheet_name.lower()
        p_adj = pd.to_numeric(row.get("pvalue_adj"), errors="coerce")
        vip = pd.to_numeric(row.get("VIP"), errors="coerce")
        log2fc = pd.to_numeric(row.get("log2FC"), errors="coerce")
        importance = pd.to_numeric(row.get("Importance"), errors="coerce")
        loading = pd.to_numeric(row.get("Loading"), errors="coerce")

        if "anova" in name:
            return pd.notna(p_adj) and p_adj < 0.05
        if "vip" in name:
            return pd.notna(vip) and vip > 1.0
        if "volcano" in name:
            return (
                pd.notna(p_adj)
                and p_adj < 0.05
                and pd.notna(log2fc)
                and abs(log2fc) >= 1.0
            )
        if "oplsda" in name:
            if pd.notna(vip):
                return vip > 1.0
            if pd.notna(importance):
                return abs(importance) > 0.05
            if pd.notna(loading):
                return abs(loading) > 0.05
            return False
        return False

    def prepare_export_sheet(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
        sheet_df = df.copy()
        if "Feature" not in sheet_df.columns:
            return sheet_df

        if "significant" not in sheet_df.columns:
            sheet_df["significant"] = sheet_df.apply(
                lambda row: passes_threshold(sheet_name, row),
                axis=1,
            )

        drop_cols = [col for col in REDUNDANT_EXPORT_COLUMNS if col in sheet_df.columns]
        if drop_cols:
            sheet_df = sheet_df.drop(columns=drop_cols)

        preferred_order = [
            "Rank",
            "Feature",
            FEATURE_MARKER_COLUMN,
            "imputation_method",
            "VIP",
            "Importance",
            "Loading",
            "log2FC",
            "pvalue",
            "pvalue_adj",
            "neg_log10p",
            "statistic",
            "qc_detect_ratio",
            "qc_rsd",
            "significant",
        ]
        existing = [col for col in preferred_order if col in sheet_df.columns]
        remainder = [col for col in sheet_df.columns if col not in existing]
        return sheet_df.loc[:, existing + remainder]

    def score_text(sheet_name: str, row: pd.Series) -> str:
        name = sheet_name.lower()
        if "vip" in name and pd.notna(row.get("VIP")):
            return f"VIP={float(row['VIP']):.2f}"
        if "volcano" in name and pd.notna(row.get("pvalue_adj")) and pd.notna(row.get("log2FC")):
            return f"p_adj={float(row['pvalue_adj']):.2e};log2FC={float(row['log2FC']):.2f}"
        if "anova" in name and pd.notna(row.get("pvalue_adj")):
            return f"p_adj={float(row['pvalue_adj']):.2e}"
        if "oplsda" in name:
            if pd.notna(row.get("Importance")):
                return f"|p|={float(row['Importance']):.4f}"
            if pd.notna(row.get("Loading")):
                return f"loading={float(row['Loading']):.4f}"
        return "Pass"

    # Build cross-reference summary with complete feature coverage.
    feature_counts = {}  # feature -> {sheet_name: score_text}
    all_features: set[str] = set()
    prepared_sheets = {
        sheet_name: prepare_export_sheet(sheet_name, df)
        for sheet_name, df in sheets.items()
    }

    for sheet_name, df in {
        name: prepared_sheets[name] for name in summary_sheet_filter
    }.items():
        if "Feature" not in df.columns:
            continue
        sheet_df = df if top_n in (None, 0) else df.head(top_n)
        for idx, row in sheet_df.iterrows():
            feat = row["Feature"]
            all_features.add(feat)
            if feat not in feature_tags and "is_Presence_Absence_Marker" in row.index:
                feature_tags[feat] = bool(row.get("is_Presence_Absence_Marker", False))
            if not passes_threshold(sheet_name, row):
                continue
            if feat not in feature_counts:
                feature_counts[feat] = {}
            feature_counts[feat][sheet_name] = score_text(sheet_name, row)

    # Build summary DataFrame
    all_sheet_names = [
        s for s in summary_sheet_filter.keys() if "Feature" in summary_sheet_filter[s].columns
    ]
    summary_rows = []
    for feat in sorted(all_features):
        appearances = feature_counts.get(feat, {})
        row = {
            "Feature": feat,
            "is_Presence_Absence_Marker": feature_tags.get(feat, False),
            "Passed_in_N_analyses": len(appearances),
        }
        for sn in all_sheet_names:
            row[sn] = appearances.get(sn, "")
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(
            ["Passed_in_N_analyses", "Feature"], ascending=[False, True]
        ).reset_index(drop=True)
        summary_df.insert(0, "Rank", range(1, len(summary_df) + 1))
        summary_df.to_csv(summary_csv_path, index=False)

    # Write all sheets
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Summary first
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Individual analysis sheets (top_n rows each)
        for sheet_name, df in prepared_sheets.items():
            # Truncate sheet name to Excel's 31-char limit
            safe_name = sheet_name[:31]
            sheet_df = df if top_n in (None, 0) else df.head(top_n)
            sheet_df.to_excel(writer, sheet_name=safe_name, index=False)

        workbook = writer.book
        for sheet_name, df in prepared_sheets.items():
            sheet_df = df if top_n in (None, 0) else df.head(top_n)
            if "significant" not in sheet_df.columns:
                continue
            safe_name = sheet_name[:31]
            worksheet = workbook[safe_name]
            significant_col = sheet_df.columns.get_loc("significant") + 1
            for row_idx, value in enumerate(sheet_df["significant"], start=2):
                cell = worksheet.cell(row=row_idx, column=significant_col)
                cell.fill = TRUE_FILL if bool(value) else FALSE_FILL

    print(f"  Saved {excel_path}")
    if not summary_df.empty:
        print(f"  Saved {summary_csv_path}")
    print(f"  Sheets: {', '.join(['Summary'] + list(sheets.keys()))}")
    scope_text = "all rows" if top_n in (None, 0) else f"top {top_n} each"
    print(f"  Summary: {len(summary_df)} unique features across "
          f"{len(all_sheet_names)} analyses ({scope_text})")


# ── Main analysis ─────────────────────────────────────────

def run_analysis(cfg: dict):
    """Execute the full analysis pipeline from a config dict."""

    data, labels, feature_metadata = load_data(cfg)
    pipe_cfg = cfg["pipeline"]
    analysis_cfg = cfg["analysis"]

    # ── Resolve output directory ──────────────────────────
    results_root = os.path.join(_PROJECT_ROOT, "results")
    input_stem = os.path.splitext(os.path.basename(cfg["input"]["file"]))[0]
    base_suffix = cfg["output"].get("suffix", "")
    auto_timestamp = bool(cfg["output"].get("auto_timestamp", True))
    resolved_suffix = compose_output_suffix(base_suffix, include_timestamp=auto_timestamp)
    cfg["output"]["base_suffix"] = base_suffix
    cfg["output"]["suffix"] = resolved_suffix
    output_dir = os.path.join(results_root, input_stem + resolved_suffix)
    os.makedirs(output_dir, exist_ok=True)

    # ── Build SpecNorm factors if needed ──────────────────
    factors = None
    factor_source = None
    if pipe_cfg.get("row_norm") == "SpecNorm":
        spec_cfg = cfg.get("spec_norm")
        if not spec_cfg or "factor_column" not in spec_cfg:
            raise ValueError(
                "row_norm='SpecNorm' requires a 'spec_norm' section with 'factor_column'."
            )
        print("\n" + "=" * 60)
        print("Loading SampleInfo for concentration correction...")
        sample_info = read_sample_info_sheet(cfg["input"]["file"])
        if sample_info is None:
            raise RuntimeError("SampleInfo sheet not found in Excel file!")

        factor_col = spec_cfg["factor_column"]
        factor_source = spec_cfg.get("factor_source", factor_col)
        factors, meta = build_aligned_factors(sample_info, data.index, factor_col)
        print(f"  Factor column: {factor_col}")
        print(f"  Aligned: {meta['n_samples']} samples")
        print(f"  Range: {meta['min_factor']:.2f} ~ {meta['max_factor']:.2f}")
        print(f"  Fuzzy matches: {meta['n_fuzzy_matches']}")
        print(f"  QC skipped (factor=1.0): {meta['n_qc_skipped']}")

    # ── Run pipeline ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("Running preprocessing pipeline...")
    pipeline = MetaboAnalystPipeline(data, labels, feature_metadata=feature_metadata)

    processed = pipeline.run_pipeline(
        missing_thresh=pipe_cfg.get("missing_thresh", 0.5),
        impute_method=pipe_cfg.get("impute_method", "min"),
        filter_method=pipe_cfg.get("filter_method", "iqr"),
        filter_cutoff=pipe_cfg.get("filter_cutoff"),
        qc_rsd_enabled=pipe_cfg.get("qc_rsd_enabled", False),
        qc_rsd_threshold=pipe_cfg.get("qc_rsd_threshold", 0.20),
        row_norm=pipe_cfg.get("row_norm", "None"),
        transform=pipe_cfg.get("transform", "None"),
        scaling=pipe_cfg.get("scaling", "None"),
        factors=factors,
        factor_source=factor_source,
    )

    print("\nPipeline log:")
    for line in pipeline.log:
        print(f"  {line}")
    print(f"\nProcessed data: {processed.shape[0]} samples x {processed.shape[1]} features")

    included_groups = cfg["groups"].get("include", [])
    final_labels = pipeline.processed_labels if pipeline.processed_labels is not None else labels
    final_feature_metadata = (
        pipeline.processed_feature_metadata
        if pipeline.processed_feature_metadata is not None
        else feature_metadata
    ).copy()

    qc_mask = final_labels.astype(str).str.contains("QC", case=False, na=False)
    if qc_mask.any():
        print(f"  Removing {qc_mask.sum()} remaining QC samples...")

    if included_groups:
        group_mask = final_labels.isin(included_groups)
        if not group_mask.all():
            excluded_count = int((~group_mask).sum())
            print(f"  Removing {excluded_count} samples not in {included_groups}")

    feat_std = processed.std()
    zero_var_feats = feat_std[feat_std == 0].index.tolist()
    if zero_var_feats:
        print(f"  Dropping {len(zero_var_feats)} zero-variance features (constant after QC removal)")

    processed, final_labels = _finalize_analysis_matrix(processed, final_labels, included_groups)
    final_feature_metadata = final_feature_metadata.reindex(processed.columns).copy()
    volcano_matrix, _ = _finalize_analysis_matrix(
        pipeline.steps["transformed"].copy(),
        (pipeline.processed_labels if pipeline.processed_labels is not None else labels).copy(),
        included_groups,
    )
    anova_matrix = volcano_matrix.copy()
    volcano_fc_matrix, _ = _finalize_analysis_matrix(
        pipeline.steps["row_normed"].copy(),
        (pipeline.processed_labels if pipeline.processed_labels is not None else labels).copy(),
        included_groups,
    )

    print(f"  Final: {processed.shape[0]} samples x {processed.shape[1]} features")
    print(f"  Groups: {dict(final_labels.value_counts())}")

    # Collectors for the summary Excel export
    _excel_sheets = {}  # sheet_name -> DataFrame
    paired_resolution_audit_rows: list[dict[str, Any]] = []

    # Save processed data
    processed.to_csv(os.path.join(output_dir, "processed_data.csv"))
    final_labels.to_csv(os.path.join(output_dir, "sample_labels.csv"))
    final_feature_metadata.to_csv(
        os.path.join(output_dir, "feature_metadata.csv"),
        index_label="Feature",
    )
    qc_rsd_audit = pipeline.step_feature_metadata.get("qc_rsd")
    if qc_rsd_audit is not None and not qc_rsd_audit.empty:
        qc_rsd_audit.to_csv(
            os.path.join(output_dir, "qc_rsd_audit.csv"),
            index_label="Feature",
        )

    # Save a copy of the config used
    config_copy_path = os.path.join(output_dir, "config_used.yaml")
    with open(config_copy_path, "w", encoding="utf-8") as f:
        f.write(dump_yaml(cfg, include_runtime=False))
    print(f"  Saved to {output_dir}")

    # ── PCA ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Running PCA...")
    n_comp = analysis_cfg["pca"]["n_components"]
    pca_result = run_pca(processed, final_labels, n_components=n_comp)
    evr = pca_result.explained_variance_ratio
    print(f"  Variance explained (PC1-{min(n_comp,5)}): "
          f"{[f'{v*100:.1f}%' for v in evr[:5]]}")

    fig = plt.figure(figsize=(10, 8))
    plot_pca_score(pca_result, pc_x=0, pc_y=1, fig=fig)
    fig.savefig(os.path.join(output_dir, "pca_score_plot.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(8, 5))
    plot_pca_scree(pca_result, fig=fig)
    fig.savefig(os.path.join(output_dir, "pca_scree_plot.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(10, 6))
    plot_pca_loading(pca_result, fig=fig)
    fig.savefig(os.path.join(output_dir, "pca_loading_plot.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved PCA plots (score, scree, loading)")

    # ── ANOVA ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    anova_cfg = analysis_cfg["anova"]
    group_list = sorted(final_labels.unique())
    print(f"Running ANOVA ({' vs '.join(group_list)})...")
    anova_result = run_anova(
        anova_matrix, final_labels,
        p_thresh=anova_cfg["p_thresh"],
        nonpar=anova_cfg["nonpar"],
        use_fdr=anova_cfg["use_fdr"],
        posthoc=anova_cfg["posthoc"],
    )
    print(f"  Significant (FDR < {anova_cfg['p_thresh']}): "
          f"{anova_result.n_significant} / {len(anova_result.result_df)}")

    anova_result.result_df = _annotate_feature_table(anova_result.result_df, final_feature_metadata)
    anova_result.result_df.to_csv(os.path.join(output_dir, "anova_results.csv"), index=False)

    # Collect full ANOVA table for Excel export and summary scoring.
    _anova_sig = (anova_result.result_df
                  .sort_values("pvalue_adj")
                  [[
                      "Feature",
                      "pvalue",
                      "pvalue_adj",
                      "neg_log10p",
                      "significant",
                      FEATURE_MARKER_COLUMN,
                  ]]
                  .copy())
    _excel_sheets["ANOVA_All"] = _anova_sig

    fig = plt.figure(figsize=(10, 8))
    plot_anova_importance(anova_result, top_n=25, fig=fig)
    fig.savefig(os.path.join(output_dir, "anova_importance.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    anova_ranked = anova_result.result_df.sort_values("pvalue_adj").copy()
    anova_feature_pool = anova_ranked["Feature"].tolist()
    sig_feature_pool = anova_ranked.loc[anova_ranked["significant"], "Feature"].tolist()
    anova_pairs = parse_pair_config(cfg["groups"].get("volcano_pairs", []))
    saved_anova_boxplots = 0
    seen_anova_pairs = set()
    for g1, g2, _paired in anova_pairs:
        pair_key = (g1, g2)
        if pair_key in seen_anova_pairs:
            continue
        seen_anova_pairs.add(pair_key)

        pair_mask = final_labels.isin([g1, g2])
        pair_data = anova_matrix.loc[pair_mask]
        pair_labels = final_labels.loc[pair_mask]
        if pair_data.empty or pair_labels.nunique() < 2:
            continue

        candidate_features = sig_feature_pool if sig_feature_pool else anova_feature_pool
        pair_means = pair_data.groupby(pair_labels).mean(numeric_only=True)
        if g1 not in pair_means.index or g2 not in pair_means.index:
            continue

        ranked_features = sorted(
            candidate_features,
            key=lambda feat: abs(pair_means.loc[g1, feat] - pair_means.loc[g2, feat]),
            reverse=True,
        )[:5]

        for i, feat in enumerate(ranked_features, start=1):
            fig = plt.figure(figsize=(7, 5))
            plot_feature_boxplot(pair_data, pair_labels, feat, fig=fig)
            fig.savefig(
                os.path.join(output_dir, f"anova_boxplot_{g1}_vs_{g2}_top{i}.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig)
            saved_anova_boxplots += 1
    print(f"  Saved ANOVA results + {saved_anova_boxplots} pairwise boxplots")

    # ── PLS-DA + VIP (pairwise, 2-group) ─────────────────────
    plsda_cfg = analysis_cfg.get("plsda", {})
    raw_plsda_pairs = cfg["groups"].get("oplsda_pairs", [])  # reuse OPLS-DA pairs
    plsda_pairs = parse_pair_config(raw_plsda_pairs)
    if plsda_cfg and plsda_pairs:
        print("\n" + "=" * 60)
        print("Running pairwise PLS-DA + VIP...")
        try:
            from ms_core.analysis.plsda import run_plsda
            from ms_core.visualization.plsda_plot import plot_plsda_score
            from ms_core.visualization.vip_plot import plot_vip
        except ImportError as e:
            print(f"  Import error: {e}")
            plsda_pairs = []

        n_comp = plsda_cfg.get("n_components", 2)
        top_vip = max(int(plsda_cfg.get("top_vip", 15)), 20)

        try:
            all_plsda_result = run_plsda(processed, final_labels, n_components=n_comp)
            fig = plt.figure(figsize=(8, 6))
            plot_plsda_score(all_plsda_result, fig=fig)
            fig.savefig(
                os.path.join(output_dir, "plsda_score_all_groups.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig)
            print("  Saved plsda_score_all_groups.png")
        except Exception as e:
            print(f"  All-group PLS-DA error: {e}")

        for g1, g2, _paired in plsda_pairs:
            print(f"  {g1} vs {g2}...")
            try:
                pair_mask = final_labels.isin([g1, g2])
                pair_data = processed.loc[pair_mask]
                pair_labels = final_labels.loc[pair_mask]

                plsda_result = run_plsda(pair_data, pair_labels, n_components=n_comp)
                print(f"    VIP range: {plsda_result.vips.min():.2f} - "
                      f"{plsda_result.vips.max():.2f}")

                # Collect VIP scores for Excel export
                vip_df = _annotate_feature_table(plsda_result.get_vip_df(), final_feature_metadata)
                vip_df.insert(0, "Rank", range(1, len(vip_df) + 1))
                _excel_sheets[f"VIP_{g1}_vs_{g2}"] = vip_df

                fig = plt.figure(figsize=(10, max(6, top_vip * 0.32)))
                plot_vip(plsda_result, top_n=top_vip,
                         data=pair_data, labels=pair_labels, fig=fig)
                fig.savefig(os.path.join(output_dir, f"plsda_vip_{g1}_vs_{g2}.png"),
                            dpi=150, bbox_inches="tight")
                plt.close(fig)
                print(f"    Saved plsda_vip_{g1}_vs_{g2}.png")
            except Exception as e:
                print(f"    Error: {e}")

    # ── OPLS-DA (pairwise, 2-group only) ──────────────────
    raw_oplsda_pairs = cfg["groups"].get("oplsda_pairs", [])
    oplsda_parsed = parse_pair_config(raw_oplsda_pairs)
    if oplsda_parsed:
        print("\n" + "=" * 60)
        print("Running pairwise OPLS-DA...")
        try:
            from ms_core.analysis.oplsda import run_oplsda
            from ms_core.visualization.oplsda_plot import plot_oplsda_score
        except ImportError as e:
            print(f"  Import error: {e}")
            oplsda_parsed = []

        for g1, g2, _paired in oplsda_parsed:
            print(f"  {g1} vs {g2}...")
            try:
                pair_mask = final_labels.isin([g1, g2])
                pair_data = processed.loc[pair_mask]
                pair_labels = final_labels.loc[pair_mask]

                oplsda_result = run_oplsda(pair_data, pair_labels)
                print(f"    R2Y={oplsda_result.r2y:.3f}, Q2={oplsda_result.q2:.3f}, "
                      f"backend={oplsda_result.backend}")

                # Collect OPLS-DA loadings for Excel export
                imp_df = _annotate_feature_table(oplsda_result.get_importance_df(), final_feature_metadata)
                if not imp_df.empty:
                    imp_df.insert(0, "Rank", range(1, len(imp_df) + 1))
                    _excel_sheets[f"OPLSDA_{g1}_vs_{g2}"] = imp_df

                # Score plot
                fig = plt.figure(figsize=(8, 6))
                plot_oplsda_score(oplsda_result, fig=fig)
                fig.savefig(os.path.join(output_dir, f"oplsda_score_{g1}_vs_{g2}.png"),
                            dpi=150, bbox_inches="tight")
                plt.close(fig)

                print("    Saved score plot")
            except Exception as e:
                print(f"    Error: {e}")

    # ── Volcano ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Running pairwise volcano analyses...")
    from visualization.volcano_plot import plot_volcano

    vol_cfg = analysis_cfg["volcano"]
    raw_pairs = cfg["groups"].get("volcano_pairs", [])
    volcano_pairs = parse_pair_config(raw_pairs)
    volcano_equal_var = resolve_volcano_parametric_equal_var(vol_cfg)
    paired_resolution_cfg = cfg["groups"].get("paired_resolution")

    # Extract subject IDs if any pair is paired
    pair_id_pattern = cfg["groups"].get("pair_id_pattern", r"BC\d+")
    has_any_paired = any(p for _, _, p in volcano_pairs)
    subject_ids = None
    if has_any_paired:
        subject_ids = extract_subject_ids(processed.index, pattern=pair_id_pattern)
        n_with_id = (subject_ids != "").sum()
        print(f"  Subject IDs extracted: {n_with_id}/{len(subject_ids)} "
              f"(pattern: {pair_id_pattern})")

    for g1, g2, is_paired in volcano_pairs:
        test_label = "paired" if is_paired else "unpaired"
        print(f"  {g1} vs {g2} ({test_label})...")
        try:
            vresult = volcano_analysis(
                volcano_matrix, final_labels,
                group1=g1, group2=g2,
                fc_thresh=vol_cfg["fc_thresh"],
                log2_fc_thresh=vol_cfg.get("log2_fc_thresh"),
                p_thresh=vol_cfg["p_thresh"],
                equal_var=volcano_equal_var,
                use_fdr=vol_cfg["use_fdr"],
                paired=is_paired,
                pair_ids=subject_ids if is_paired else None,
                fc_df=volcano_fc_matrix,
                pair_resolution=paired_resolution_cfg if is_paired else None,
            )
            pair_info = f", Pairs: {vresult.n_pairs}" if is_paired else ""
            print(f"    Method: {vresult.test_label}")
            print(f"    Significant: {vresult.n_significant} "
                  f"(Up: {vresult.n_up}, Down: {vresult.n_down}{pair_info})")
            if is_paired and vresult.resolution_overrides_applied:
                print(f"    Paired overrides applied: {len(vresult.resolution_overrides_applied)}")
                for record in vresult.resolution_overrides_applied:
                    paired_resolution_audit_rows.append(
                        {
                            "pair": f"{g1}_vs_{g2}",
                            "audit_kind": "override",
                            "group": record.get("group", ""),
                            "subject_id": record.get("subject_id", ""),
                            "selected_sample": record.get("selected_sample", ""),
                            "message": "",
                            "candidates": " | ".join(record.get("candidates", [])),
                        }
                    )
            if is_paired and vresult.resolution_warnings:
                print(f"    Paired resolution warnings: {len(vresult.resolution_warnings)}")
                for warning in vresult.resolution_warnings:
                    print(f"      - {warning}")
                    paired_resolution_audit_rows.append(
                        {
                            "pair": f"{g1}_vs_{g2}",
                            "audit_kind": "warning",
                            "group": "",
                            "subject_id": "",
                            "selected_sample": "",
                            "message": warning,
                            "candidates": "",
                        }
                    )
            vresult.result_df = _annotate_feature_table(vresult.result_df, final_feature_metadata)
            vresult.result_df.to_csv(
                os.path.join(output_dir, f"volcano_{g1}_vs_{g2}.csv"),
                index=False,
            )

            # Collect volcano significant features for Excel export
            vol_sig = _annotate_feature_table(vresult.significant.copy(), final_feature_metadata)
            if not vol_sig.empty:
                vol_sig = vol_sig.sort_values("pvalue_adj").head(50)
                _excel_sheets[f"Volcano_{g1}_vs_{g2}"] = vol_sig
            fig = plt.figure(figsize=(10, 8))
            plot_volcano(vresult, fig=fig)
            fig.savefig(os.path.join(output_dir, f"volcano_{g1}_vs_{g2}.png"),
                        dpi=150, bbox_inches="tight")
            plt.close(fig)
        except Exception as e:
            print(f"    Error: {e}")

    # ── Sample overview ───────────────────────────────────
    print("\n" + "=" * 60)
    print("Generating sample-level overview plots...")
    fig = plt.figure(figsize=(16, 6))
    plot_sample_boxplot(processed, final_labels,
                        title="Sample Distribution (after processing)", fig=fig)
    fig.savefig(os.path.join(output_dir, "sample_boxplot.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(10, 6))
    plot_density(processed, final_labels,
                 title="Density Plot (after processing)", fig=fig)
    fig.savefig(os.path.join(output_dir, "density_plot.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved sample_boxplot.png + density_plot.png")

    if paired_resolution_audit_rows:
        audit_path = os.path.join(output_dir, "paired_resolution_audit.csv")
        pd.DataFrame(paired_resolution_audit_rows).to_csv(audit_path, index=False)
        print(f"  Saved {audit_path}")

    # ── Export significant features summary Excel ─────────
    print("\n" + "=" * 60)
    print("Exporting significant features summary...")
    export_top_n = cfg.get("output", {}).get("export_top_n")
    try:
        _export_significant_features_excel(
            _excel_sheets, output_dir, top_n=export_top_n,
        )
    except Exception as e:
        print(f"  Excel export error: {e}")

    # ── Summary ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print(f"All outputs saved to: {output_dir}")
    print("\nGenerated files:")
    for f in sorted(os.listdir(output_dir)):
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"  {f:40s} ({size / 1024:.0f} KB)")


# ── CLI entry point ───────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run MetaboAnalyst pipeline from a YAML config file.",
        epilog="Example: python run_from_config.py configs/step4_dnp_specnorm.yaml",
    )
    parser.add_argument(
        "config",
        help="Path to YAML configuration file (e.g., configs/step4_dnp_specnorm.yaml)",
    )
    parser.add_argument(
        "--input", "-i",
        help="Override the input file path from config (e.g., path/to/data.xlsx)",
        default=None,
    )
    parser.add_argument(
        "--suffix", "-s",
        help="Append a suffix to the output folder name (e.g., _control, _strict)",
        default=None,
    )
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    app_config = load_yaml_config(args.config, require_required_sections=True)
    app_config = apply_cli_overrides(
        app_config,
        input_file=args.input,
        suffix=args.suffix,
    )
    cfg = app_config.to_dict(include_runtime=True)
    if args.input:
        print(f"Input overridden: {args.input}")
    print(f"Loaded config: {args.config}")
    run_analysis(cfg)


if __name__ == "__main__":
    main()
