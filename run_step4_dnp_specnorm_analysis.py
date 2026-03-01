"""
Full MetaboAnalyst-style pipeline analysis script.

Input:  STEP4_program2_DNA_alignment_20260227_220832.xlsx
Groups: Exposure / Normal / Control (3-group)
QC-RSD: Enabled (threshold=0.20)
Missing: 50% threshold
Impute: min (LoD)
Row norm: SpecNorm (DNA concentration correction from SampleInfo sheet)
Transform: glog2 (LogNorm) + AutoScale (Z-score)
"""

import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

# ── Config ────────────────────────────────────────────────
INPUT_FILE = (
    r"C:\Users\user\Desktop\質譜數據工具箱\ms-preprocessing-toolkit"
    r"\OUTPUT\DNP\STEP4_program2_DNA_alignment_20260227_220832.xlsx"
)

# ── Fixed output directory ────────────────────────────────
RESULTS_ROOT = os.path.join(os.path.dirname(__file__), "results")
_input_stem = os.path.splitext(os.path.basename(INPUT_FILE))[0]
OUTPUT_DIR = os.path.join(RESULTS_ROOT, _input_stem + "_SpecNorm")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Step 0: Load & reshape data ──────────────────────────
print("=" * 60)
print("Loading data...")
raw = pd.read_excel(INPUT_FILE)

# Row 0 contains sample types; rows 1+ are features
feature_names = raw["Mz/RT"].iloc[1:].values
sample_types = raw.iloc[0, 1:].values
sample_names = raw.columns[1:].values

# Build data matrix: samples x features
data_values = raw.iloc[1:, 1:].values.T
data_values = pd.DataFrame(data_values, columns=feature_names, index=sample_names)
data_values = data_values.apply(pd.to_numeric, errors="coerce")

# Build labels
labels = pd.Series(sample_types, index=sample_names, name="Group")

print(f"  Samples: {data_values.shape[0]}, Features: {data_values.shape[1]}")
print(f"  Groups: {dict(labels.value_counts())}")
print(f"  Zeros: {(data_values == 0).sum().sum()} / {data_values.size}")

# ── Load SampleInfo & build concentration factors ────────
print("\n" + "=" * 60)
print("Loading SampleInfo for concentration correction...")
sample_info = read_sample_info_sheet(INPUT_FILE)
if sample_info is None:
    raise RuntimeError("SampleInfo sheet not found!")

candidates, default_col = detect_factor_columns(sample_info)
print(f"  Factor columns found: {candidates}")
print(f"  Default factor column: {default_col}")

# Use DNA_mg/20uL as concentration factor
FACTOR_COL = "DNA_mg/20uL"
factors, meta = build_aligned_factors(sample_info, data_values.index, FACTOR_COL)
print(f"  Factor column: {FACTOR_COL}")
print(f"  Aligned: {meta['n_samples']} samples")
print(f"  Range: {meta['min_factor']:.2f} ~ {meta['max_factor']:.2f}")
print(f"  Fuzzy matches: {meta['n_fuzzy_matches']}")
print(f"  QC skipped (factor=1.0): {meta['n_qc_skipped']}")

# ── Step 1: Run preprocessing pipeline ───────────────────
print("\n" + "=" * 60)
print("Running preprocessing pipeline (with SpecNorm)...")
pipeline = MetaboAnalystPipeline(data_values, labels)

processed = pipeline.run_pipeline(
    # Missing value — same as other analyses
    missing_thresh=0.50,
    impute_method="min",
    # Filtering
    filter_method="iqr",
    filter_cutoff=None,
    qc_rsd_enabled=True,
    qc_rsd_threshold=0.20,
    # Row normalization — DNA concentration correction
    row_norm="SpecNorm",
    factors=factors,
    factor_source=FACTOR_COL,
    # Transformation
    transform="LogNorm",
    # Scaling
    scaling="AutoNorm",
)

print("\nPipeline log:")
for line in pipeline.log:
    print(f"  {line}")

print(f"\nProcessed data: {processed.shape[0]} samples x {processed.shape[1]} features")

# Get labels after pipeline (QC removed)
final_labels = pipeline.processed_labels
if final_labels is None:
    final_labels = labels

# Remove any remaining QC samples
qc_mask = final_labels.astype(str).str.contains("QC", case=False, na=False)
if qc_mask.any():
    print(f"  Removing {qc_mask.sum()} remaining QC samples for analysis...")
    processed = processed.loc[~qc_mask]
    final_labels = final_labels.loc[~qc_mask]

print(f"  Final analysis set: {processed.shape[0]} samples x {processed.shape[1]} features")
print(f"  Groups: {dict(final_labels.value_counts())}")

# Save processed data
processed.to_csv(os.path.join(OUTPUT_DIR, "processed_data.csv"))
final_labels.to_csv(os.path.join(OUTPUT_DIR, "sample_labels.csv"))
print(f"  Saved processed data to {OUTPUT_DIR}")

# ── Step 2: PCA ──────────────────────────────────────────
print("\n" + "=" * 60)
print("Running PCA...")
pca_result = run_pca(processed, final_labels, n_components=5)
evr = pca_result.explained_variance_ratio
print(f"  Variance explained (PC1-5): {[f'{v*100:.1f}%' for v in evr[:5]]}")

fig_score = plt.figure(figsize=(10, 8))
plot_pca_score(pca_result, pc_x=0, pc_y=1, fig=fig_score)
fig_score.savefig(os.path.join(OUTPUT_DIR, "pca_score_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_score)
print("  Saved pca_score_plot.png")

fig_scree = plt.figure(figsize=(8, 5))
plot_pca_scree(pca_result, fig=fig_scree)
fig_scree.savefig(os.path.join(OUTPUT_DIR, "pca_scree_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_scree)
print("  Saved pca_scree_plot.png")

fig_loading = plt.figure(figsize=(10, 6))
plot_pca_loading(pca_result, fig=fig_loading)
fig_loading.savefig(os.path.join(OUTPUT_DIR, "pca_loading_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_loading)
print("  Saved pca_loading_plot.png")

# ── Step 3: ANOVA (3-group) ─────────────────────────────
print("\n" + "=" * 60)
print("Running ANOVA (Exposure vs Normal vs Control)...")
anova_result = run_anova(
    processed, final_labels,
    p_thresh=0.05,
    nonpar=False,
    use_fdr=True,
    posthoc=True,
)
sig_count = anova_result.n_significant
print(f"  Significant features (FDR < 0.05): {sig_count} / {len(anova_result.result_df)}")

anova_result.result_df.to_csv(os.path.join(OUTPUT_DIR, "anova_results.csv"))
print("  Saved anova_results.csv")

fig_anova = plt.figure(figsize=(10, 8))
plot_anova_importance(anova_result, top_n=25, fig=fig_anova)
fig_anova.savefig(os.path.join(OUTPUT_DIR, "anova_importance.png"), dpi=150, bbox_inches="tight")
plt.close(fig_anova)
print("  Saved anova_importance.png")

top_features = anova_result.result_df.sort_values("pvalue_adj").head(6)["Feature"].tolist()
for i, feat in enumerate(top_features):
    fig_box = plt.figure(figsize=(7, 5))
    plot_feature_boxplot(processed, final_labels, feat, fig=fig_box)
    fname = f"anova_boxplot_top{i+1}.png"
    fig_box.savefig(os.path.join(OUTPUT_DIR, fname), dpi=150, bbox_inches="tight")
    plt.close(fig_box)
print(f"  Saved {len(top_features)} ANOVA boxplots")

# ── Step 4: Pairwise volcano plots ──────────────────────
print("\n" + "=" * 60)
print("Running pairwise volcano analyses...")
groups = ["Exposure", "Normal", "Control"]
pairs = [(groups[i], groups[j]) for i in range(len(groups)) for j in range(i + 1, len(groups))]

from visualization.volcano_plot import plot_volcano

for g1, g2 in pairs:
    print(f"  {g1} vs {g2}...")
    try:
        vresult = volcano_analysis(
            processed, final_labels,
            group1=g1, group2=g2,
            fc_thresh=2.0, p_thresh=0.05,
            use_fdr=True,
        )
        print(f"    Significant: {vresult.n_significant} (Up: {vresult.n_up}, Down: {vresult.n_down})")
        vresult.result_df.to_csv(os.path.join(OUTPUT_DIR, f"volcano_{g1}_vs_{g2}.csv"))

        fig_vol = plt.figure(figsize=(10, 8))
        plot_volcano(vresult, fig=fig_vol)
        fig_vol.savefig(
            os.path.join(OUTPUT_DIR, f"volcano_{g1}_vs_{g2}.png"),
            dpi=150, bbox_inches="tight",
        )
        plt.close(fig_vol)
    except Exception as e:
        print(f"    Error: {e}")

# ── Step 5: Heatmap ─────────────────────────────────────
print("\n" + "=" * 60)
print("Generating heatmap (top 50 features by variance)...")
try:
    fig_hm = plt.figure(figsize=(14, 10))
    plot_heatmap(processed, final_labels, method="ward", metric="euclidean",
                 scale="row", max_features=50, top_by="var", fig=fig_hm)
    fig_hm.savefig(os.path.join(OUTPUT_DIR, "heatmap_top50.png"), dpi=150, bbox_inches="tight")
    plt.close(fig_hm)
    print("  Saved heatmap_top50.png")
except Exception as e:
    print(f"  Heatmap error: {e}")

# ── Step 6: Sample-level overview ────────────────────────
print("\n" + "=" * 60)
print("Generating sample-level overview plots...")

fig_sbox = plt.figure(figsize=(16, 6))
plot_sample_boxplot(processed, final_labels, title="Sample Distribution (SpecNorm + glog2 + AutoScale)", fig=fig_sbox)
fig_sbox.savefig(os.path.join(OUTPUT_DIR, "sample_boxplot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_sbox)
print("  Saved sample_boxplot.png")

fig_den = plt.figure(figsize=(10, 6))
plot_density(processed, final_labels, title="Density Plot (SpecNorm + glog2 + AutoScale)", fig=fig_den)
fig_den.savefig(os.path.join(OUTPUT_DIR, "density_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_den)
print("  Saved density_plot.png")

# ── Summary ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print(f"All outputs saved to: {OUTPUT_DIR}")
print("\nGenerated files:")
for f in sorted(os.listdir(OUTPUT_DIR)):
    size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
    print(f"  {f:40s} ({size / 1024:.0f} KB)")
