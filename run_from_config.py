"""
Universal analysis runner — reads a YAML config and executes the full pipeline.

Usage:
    python run_from_config.py configs/step4_dnp_specnorm.yaml
    python run_from_config.py configs/step4_dnp_no_norm.yaml
    python run_from_config.py configs/dnp_pqn_normalized.yaml
"""

import argparse
import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

# Ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

from core.pipeline import MetaboAnalystPipeline
from core.sample_info import read_sample_info_sheet, detect_factor_columns, build_aligned_factors
from analysis.pca import run_pca
from analysis.anova import run_anova
from analysis.univariate import volcano_analysis
from visualization.pca_plot import plot_pca_score, plot_pca_scree, plot_pca_loading
from visualization.heatmap import plot_heatmap
from visualization.boxplot import plot_sample_boxplot, plot_group_boxplot
from visualization.density_plot import plot_density
from visualization.anova_plot import plot_anova_importance, plot_feature_boxplot

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
    analysis.setdefault("pca", {}).setdefault("n_components", 5)
    anova = analysis.setdefault("anova", {})
    anova.setdefault("p_thresh", 0.05)
    anova.setdefault("nonpar", False)
    anova.setdefault("use_fdr", True)
    anova.setdefault("posthoc", True)
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


def load_data(cfg: dict) -> tuple[pd.DataFrame, pd.Series]:
    """Load Excel data and return (samples x features DataFrame, labels Series)."""
    input_file = cfg["input"]["file"]
    fmt = cfg["input"].get("format", "sample_type_row")

    print("=" * 60)
    print(f"Loading data from: {os.path.basename(input_file)}")
    raw = pd.read_excel(input_file)

    if fmt == "sample_type_row":
        # Row 0 = Sample_Type labels; rows 1+ = feature values
        feature_names = raw["Mz/RT"].iloc[1:].values
        sample_types = raw.iloc[0, 1:].values
        sample_names = raw.columns[1:].values

        data = raw.iloc[1:, 1:].values.T
        data = pd.DataFrame(data, columns=feature_names, index=sample_names)
        data = data.apply(pd.to_numeric, errors="coerce")
        labels = pd.Series(sample_types, index=sample_names, name="Group")

    elif fmt == "plain":
        # All rows are features; groups inferred from column names
        feature_names = raw["Mz/RT"].values
        sample_names = raw.columns[1:].values

        data = raw.iloc[:, 1:].values.T
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


# ── Main analysis ─────────────────────────────────────────

def run_analysis(cfg: dict):
    """Execute the full analysis pipeline from a config dict."""

    data, labels = load_data(cfg)
    pipe_cfg = cfg["pipeline"]
    analysis_cfg = cfg["analysis"]

    # ── Resolve output directory ──────────────────────────
    results_root = os.path.join(os.path.dirname(__file__), "results")
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

    print(f"  Final: {processed.shape[0]} samples x {processed.shape[1]} features")
    print(f"  Groups: {dict(final_labels.value_counts())}")

    # Save processed data
    processed.to_csv(os.path.join(output_dir, "processed_data.csv"))
    final_labels.to_csv(os.path.join(output_dir, "sample_labels.csv"))

    # Save a copy of the config used
    import shutil
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

    # ── Volcano ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Running pairwise volcano analyses...")
    from visualization.volcano_plot import plot_volcano

    vol_cfg = analysis_cfg["volcano"]
    pairs = cfg["groups"].get("volcano_pairs", [])
    for g1, g2 in pairs:
        print(f"  {g1} vs {g2}...")
        try:
            vresult = volcano_analysis(
                processed, final_labels,
                group1=g1, group2=g2,
                fc_thresh=vol_cfg["fc_thresh"],
                p_thresh=vol_cfg["p_thresh"],
                use_fdr=vol_cfg["use_fdr"],
            )
            print(f"    Significant: {vresult.n_significant} "
                  f"(Up: {vresult.n_up}, Down: {vresult.n_down})")
            vresult.result_df.to_csv(
                os.path.join(output_dir, f"volcano_{g1}_vs_{g2}.csv"))
            fig = plt.figure(figsize=(10, 8))
            plot_volcano(vresult, fig=fig)
            fig.savefig(os.path.join(output_dir, f"volcano_{g1}_vs_{g2}.png"),
                        dpi=150, bbox_inches="tight")
            plt.close(fig)
        except Exception as e:
            print(f"    Error: {e}")

    # ── Heatmap ───────────────────────────────────────────
    print("\n" + "=" * 60)
    hm_cfg = analysis_cfg["heatmap"]
    print(f"Generating heatmap (top {hm_cfg['max_features']} features)...")
    try:
        fig = plt.figure(figsize=(14, 10))
        plot_heatmap(
            processed, final_labels,
            method=hm_cfg["method"], metric=hm_cfg["metric"],
            scale=hm_cfg["scale"], max_features=hm_cfg["max_features"],
            top_by=hm_cfg["top_by"], fig=fig,
        )
        fig.savefig(os.path.join(output_dir, "heatmap_top50.png"),
                    dpi=150, bbox_inches="tight")
        plt.close(fig)
        print("  Saved heatmap_top50.png")
    except Exception as e:
        print(f"  Heatmap error: {e}")

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
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    cfg = load_config(args.config)
    print(f"Loaded config: {args.config}")
    run_analysis(cfg)


if __name__ == "__main__":
    main()
