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

# Ensure project root on path (scripts/ lives one level below project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

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


# ── Config loader ─────────────────────────────────────────

def load_config(path: str) -> dict:
    """Load and validate a YAML configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Validate required top-level keys
    for key in ("input", "pipeline", "groups", "analysis"):
        if key not in cfg:
            raise ValueError(f"Config missing required section: '{key}'")

    # Defaults for optional fields
    cfg.setdefault("spec_norm", None)
    cfg.setdefault("output", {})
    cfg["output"].setdefault("suffix", "")

    # Defaults for analysis sub-sections
    analysis = cfg["analysis"]
    pca = analysis.setdefault("pca", {})
    if "n_components" not in pca and "Old_Statistics_PM" in pca:
        pca["n_components"] = pca["Old_Statistics_PM"]
    pca.setdefault("n_components", 5)
    anova = analysis.setdefault("anova", {})
    anova.setdefault("p_thresh", 0.05)
    anova.setdefault("nonpar", False)
    anova.setdefault("use_fdr", True)
    anova.setdefault("posthoc", True)
    plsda = analysis.setdefault("plsda", {})
    plsda.setdefault("n_components", 2)
    plsda.setdefault("top_vip", 15)
    volcano = analysis.setdefault("volcano", {})
    volcano.setdefault("fc_thresh", 2.0)
    volcano.setdefault("p_thresh", 0.05)
    volcano.setdefault("use_fdr", True)
    hm = analysis.setdefault("heatmap", {})
    hm.setdefault("max_features", 50)
    hm.setdefault("top_by", "var")
    hm.setdefault("method", "ward")
    hm.setdefault("metric", "euclidean")
    hm.setdefault("scale", "row")

    return cfg


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


# ── Data loaders ──────────────────────────────────────────

def assign_group_from_name(name: str) -> str:
    """Infer group label from sample column name (for 'plain' format)."""
    name_lower = name.lower()
    if "qc" in name_lower:
        return "QC"
    if name.endswith("_RNA") or name.endswith("_DNAandRNA"):
        return "__EXCLUDE__"
    if name_lower.startswith("tumor"):
        return "Tumor"
    if name_lower.startswith("normal"):
        return "Normal"
    if name_lower.startswith("benignfat"):
        return "Benignfat"
    return "__EXCLUDE__"


def get_feature_id_column(raw: pd.DataFrame) -> str:
    """Return the feature identifier column for spreadsheet-style inputs."""
    for candidate in ("Mz/RT", "FeatureID"):
        if candidate in raw.columns:
            return candidate
    return raw.columns[0]


def load_data(cfg: dict) -> tuple[pd.DataFrame, pd.Series]:
    """Load Excel data and return (samples x features DataFrame, labels Series)."""
    input_file = cfg["input"]["file"]
    if not input_file:
        raise ValueError("No input file specified. Use --input <path> on the command line.")
    fmt = cfg["input"].get("format", "sample_type_row")

    print("=" * 60)
    print(f"Loading data from: {os.path.basename(input_file)}")
    raw = pd.read_excel(input_file)
    feature_col = get_feature_id_column(raw)
    sample_columns = [col for col in identify_sample_columns(raw) if col != feature_col]

    if fmt == "sample_type_row":
        # Row 0 = Sample_Type labels; rows 1+ = feature values
        sample_type_row = pd.Series(raw.iloc[0].values, index=raw.columns)
        valid_sample_cols = [col for col in sample_columns if pd.notna(sample_type_row.get(col))]
        feature_names = raw[feature_col].iloc[1:].values
        sample_types = sample_type_row.loc[valid_sample_cols].values
        sample_names = np.array(valid_sample_cols)

        data = raw.loc[1:, valid_sample_cols].values.T
        data = pd.DataFrame(data, columns=feature_names, index=sample_names)
        data = data.apply(pd.to_numeric, errors="coerce")
        labels = pd.Series(sample_types, index=sample_names, name="Group")

    elif fmt == "plain":
        # All rows are features; groups inferred from column names
        feature_names = raw[feature_col].values
        sample_names = np.array(sample_columns)

        data = raw.loc[:, sample_columns].values.T
        data = pd.DataFrame(data, columns=feature_names, index=sample_names)
        data = data.apply(pd.to_numeric, errors="coerce")
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

    print(f"  Samples: {data.shape[0]}, Features: {data.shape[1]}")
    print(f"  Groups: {dict(labels.value_counts())}")
    print(f"  Zeros: {(data == 0).sum().sum()} / {data.size}")
    print(f"  Missing: {data.isna().sum().sum()} / {data.size}")

    return data, labels


# ── Significant features Excel export ────────────────────

def _export_significant_features_excel(
    sheets: dict, output_dir: str, top_n: int = 20,
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

    # Build cross-reference summary: count how many sheets each feature appears in
    feature_counts = {}  # feature -> {sheet_name: rank_or_score}
    for sheet_name, df in sheets.items():
        if "Feature" not in df.columns:
            continue
        for idx, row in df.head(top_n).iterrows():
            feat = row["Feature"]
            if feat not in feature_counts:
                feature_counts[feat] = {}
            # Store the rank or key metric
            if "VIP" in df.columns:
                feature_counts[feat][sheet_name] = f"VIP={row['VIP']:.2f}"
            elif "pvalue_adj" in df.columns:
                feature_counts[feat][sheet_name] = f"p_adj={row['pvalue_adj']:.2e}"
            elif "Importance" in df.columns:
                feature_counts[feat][sheet_name] = f"|p|={row['Importance']:.4f}"
            else:
                feature_counts[feat][sheet_name] = "Yes"

    # Build summary DataFrame
    all_sheet_names = [s for s in sheets.keys() if "Feature" in sheets[s].columns]
    summary_rows = []
    for feat, appearances in feature_counts.items():
        row = {"Feature": feat, "Appeared_in_N_analyses": len(appearances)}
        for sn in all_sheet_names:
            row[sn] = appearances.get(sn, "")
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(
            "Appeared_in_N_analyses", ascending=False
        ).reset_index(drop=True)
        summary_df.insert(0, "Rank", range(1, len(summary_df) + 1))

    # Write all sheets
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Summary first
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Individual analysis sheets (top_n rows each)
        for sheet_name, df in sheets.items():
            # Truncate sheet name to Excel's 31-char limit
            safe_name = sheet_name[:31]
            df.head(top_n).to_excel(writer, sheet_name=safe_name, index=False)

    print(f"  Saved {excel_path}")
    print(f"  Sheets: {', '.join(['Summary'] + list(sheets.keys()))}")
    print(f"  Summary: {len(feature_counts)} unique features across "
          f"{len(all_sheet_names)} analyses (top {top_n} each)")


# ── Main analysis ─────────────────────────────────────────

def run_analysis(cfg: dict):
    """Execute the full analysis pipeline from a config dict."""

    data, labels = load_data(cfg)
    pipe_cfg = cfg["pipeline"]
    analysis_cfg = cfg["analysis"]

    # ── Resolve output directory ──────────────────────────
    results_root = os.path.join(_PROJECT_ROOT, "results")
    input_stem = os.path.splitext(os.path.basename(cfg["input"]["file"]))[0]
    suffix = cfg["output"].get("suffix", "")
    output_dir = os.path.join(results_root, input_stem + suffix)
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
    pipeline = MetaboAnalystPipeline(data, labels)

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

    # Remove QC samples
    final_labels = pipeline.processed_labels if pipeline.processed_labels is not None else labels
    qc_mask = final_labels.astype(str).str.contains("QC", case=False, na=False)
    if qc_mask.any():
        print(f"  Removing {qc_mask.sum()} remaining QC samples...")
        processed = processed.loc[~qc_mask]
        final_labels = final_labels.loc[~qc_mask]

    # Filter to included groups only
    included_groups = cfg["groups"].get("include", [])
    if included_groups:
        group_mask = final_labels.isin(included_groups)
        if not group_mask.all():
            excluded_count = (~group_mask).sum()
            print(f"  Removing {excluded_count} samples not in {included_groups}")
            processed = processed.loc[group_mask]
            final_labels = final_labels.loc[group_mask]

    # Drop zero-variance features (std=0 after QC removal causes Pareto NaN)
    feat_std = processed.std()
    zero_var_feats = feat_std[feat_std == 0].index.tolist()
    if zero_var_feats:
        print(f"  Dropping {len(zero_var_feats)} zero-variance features (constant after QC removal)")
        processed = processed.drop(columns=zero_var_feats)

    print(f"  Final: {processed.shape[0]} samples x {processed.shape[1]} features")
    print(f"  Groups: {dict(final_labels.value_counts())}")

    # Collectors for the summary Excel export
    _excel_sheets = {}  # sheet_name -> DataFrame

    # Save processed data
    processed.to_csv(os.path.join(output_dir, "processed_data.csv"))
    final_labels.to_csv(os.path.join(output_dir, "sample_labels.csv"))

    # Save a copy of the config used
    config_copy_path = os.path.join(output_dir, "config_used.yaml")
    with open(config_copy_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
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
        processed, final_labels,
        p_thresh=anova_cfg["p_thresh"],
        nonpar=anova_cfg["nonpar"],
        use_fdr=anova_cfg["use_fdr"],
        posthoc=anova_cfg["posthoc"],
    )
    print(f"  Significant (FDR < {anova_cfg['p_thresh']}): "
          f"{anova_result.n_significant} / {len(anova_result.result_df)}")

    anova_result.result_df.to_csv(os.path.join(output_dir, "anova_results.csv"))

    # Collect ANOVA significant features for Excel export
    _anova_sig = (anova_result.result_df
                  .sort_values("pvalue_adj")
                  .head(50)
                  [["Feature", "pvalue", "pvalue_adj", "neg_log10p", "significant"]]
                  .copy())
    _excel_sheets["ANOVA_Top50"] = _anova_sig

    fig = plt.figure(figsize=(10, 8))
    plot_anova_importance(anova_result, top_n=25, fig=fig)
    fig.savefig(os.path.join(output_dir, "anova_importance.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    top_features = anova_result.result_df.sort_values("pvalue_adj").head(6)["Feature"].tolist()
    for i, feat in enumerate(top_features):
        fig = plt.figure(figsize=(7, 5))
        plot_feature_boxplot(processed, final_labels, feat, fig=fig)
        fig.savefig(os.path.join(output_dir, f"anova_boxplot_top{i+1}.png"),
                    dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"  Saved ANOVA results + {len(top_features)} boxplots")

    # ── PLS-DA + VIP (pairwise, 2-group) ─────────────────────
    plsda_cfg = analysis_cfg.get("plsda", {})
    raw_plsda_pairs = cfg["groups"].get("oplsda_pairs", [])  # reuse OPLS-DA pairs
    plsda_pairs = parse_pair_config(raw_plsda_pairs)
    if plsda_cfg and plsda_pairs:
        print("\n" + "=" * 60)
        print("Running pairwise PLS-DA + VIP...")
        try:
            from ms_core.analysis.plsda import run_plsda
            from ms_core.visualization.vip_plot import plot_vip
        except ImportError as e:
            print(f"  Import error: {e}")
            plsda_pairs = []

        n_comp = plsda_cfg.get("n_components", 2)
        top_vip = plsda_cfg.get("top_vip", 15)

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
                vip_df = plsda_result.get_vip_df()
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
                imp_df = oplsda_result.get_importance_df()
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
                processed, final_labels,
                group1=g1, group2=g2,
                fc_thresh=vol_cfg["fc_thresh"],
                p_thresh=vol_cfg["p_thresh"],
                use_fdr=vol_cfg["use_fdr"],
                paired=is_paired,
                pair_ids=subject_ids if is_paired else None,
            )
            pair_info = f", Pairs: {vresult.n_pairs}" if is_paired else ""
            print(f"    Significant: {vresult.n_significant} "
                  f"(Up: {vresult.n_up}, Down: {vresult.n_down}{pair_info})")
            vresult.result_df.to_csv(
                os.path.join(output_dir, f"volcano_{g1}_vs_{g2}.csv"))

            # Collect volcano significant features for Excel export
            vol_sig = vresult.significant.copy()
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

    # ── Export significant features summary Excel ─────────
    print("\n" + "=" * 60)
    print("Exporting significant features summary...")
    export_top_n = cfg.get("output", {}).get("export_top_n", 20)
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

    cfg = load_config(args.config)
    if args.input:
        cfg["input"]["file"] = args.input
        print(f"Input overridden: {args.input}")
    if args.suffix:
        cfg["output"]["suffix"] = args.suffix
    print(f"Loaded config: {args.config}")
    run_analysis(cfg)


if __name__ == "__main__":
    main()
