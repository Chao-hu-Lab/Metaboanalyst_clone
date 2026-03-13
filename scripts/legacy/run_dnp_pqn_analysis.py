"""
Full MetaboAnalyst-style pipeline analysis script.

Input:  Normalized_PQN_SampleSpecific_20260228_050115.xlsx
Groups: Tumor_DNA / Normal_DNA / Benignfat_DNA (3-group)
QC-RSD: Enabled (threshold=0.20)
Missing: 50% threshold
Impute: min (LoD)
Transform: glog2 (LogNorm) + AutoScale (Z-score)
Row norm: None (already PQN-normalized)
"""

import os
import sys
import warnings

# Ensure project root on path (must precede project imports)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from core.pipeline import MetaboAnalystPipeline  # noqa: E402
from ms_core.analysis.pca import run_pca  # noqa: E402
from ms_core.analysis.anova import run_anova  # noqa: E402
from ms_core.analysis.univariate import volcano_analysis  # noqa: E402
from ms_core.visualization.pca_plot import plot_pca_score, plot_pca_scree, plot_pca_loading  # noqa: E402
from ms_core.visualization.heatmap import plot_heatmap  # noqa: E402
from ms_core.visualization.boxplot import plot_sample_boxplot  # noqa: E402
from ms_core.visualization.density_plot import plot_density  # noqa: E402
from ms_core.visualization.anova_plot import plot_anova_importance, plot_feature_boxplot  # noqa: E402
from ms_core.visualization.volcano_plot import plot_volcano  # noqa: E402

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────
INPUT_FILE = (
    r"C:\Users\user\Desktop\質譜數據工具箱\ms-preprocessing-toolkit"
    r"\OUTPUT\DNP\Normalized_PQN_SampleSpecific_20260228_050115.xlsx"
)

# ── Fixed output directory: results/<input_filename>/ ─────
RESULTS_ROOT = os.path.join(_PROJECT_ROOT, "results")
_input_stem = os.path.splitext(os.path.basename(INPUT_FILE))[0]
OUTPUT_DIR = os.path.join(RESULTS_ROOT, _input_stem)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Step 0: Load & reshape data ──────────────────────────
print("=" * 60)
print("Loading data...")
raw = pd.read_excel(INPUT_FILE)

# Format: Mz/RT column + sample columns, each row = one feature
feature_names = raw["Mz/RT"].values
sample_names = raw.columns[1:].values

# Build data matrix: samples (rows) x features (columns)
data_values = raw.iloc[:, 1:].values.T  # transpose
data_values = pd.DataFrame(data_values, columns=feature_names, index=sample_names)
data_values = data_values.apply(pd.to_numeric, errors="coerce")

# ── Assign groups from sample names ──────────────────────
def assign_group(name: str) -> str:
    """Infer group label from sample column name."""
    name_lower = name.lower()
    if "qc" in name_lower:
        return "QC"
    # Exclude RNA-only and DNAandRNA samples
    if name.endswith("_RNA") or name.endswith("_DNAandRNA"):
        return "__EXCLUDE__"
    if name_lower.startswith("tumor"):
        return "Tumor"
    if name_lower.startswith("normal"):
        return "Normal"
    if name_lower.startswith("benignfat"):
        return "Benignfat"
    return "__EXCLUDE__"


labels = pd.Series([assign_group(n) for n in sample_names],
                    index=sample_names, name="Group")

# Drop excluded samples (RNA, DNAandRNA, unknown)
exclude_mask = labels == "__EXCLUDE__"
if exclude_mask.any():
    excluded = list(sample_names[exclude_mask])
    print(f"  Excluding {len(excluded)} non-DNA samples: {excluded}")
    data_values = data_values.loc[~exclude_mask]
    labels = labels.loc[~exclude_mask]

print(f"  Samples: {data_values.shape[0]}, Features: {data_values.shape[1]}")
print(f"  Groups: {dict(labels.value_counts())}")
print(f"  Zeros: {(data_values == 0).sum().sum()} / {data_values.size}")
print(f"  Missing: {data_values.isna().sum().sum()} / {data_values.size}")

# ── Step 1: Run preprocessing pipeline ───────────────────
print("\n" + "=" * 60)
print("Running preprocessing pipeline...")
pipeline = MetaboAnalystPipeline(data_values, labels)

processed = pipeline.run_pipeline(
    # Missing value
    missing_thresh=0.50,
    impute_method="min",
    # Filtering
    filter_method="iqr",
    filter_cutoff=None,         # auto-adaptive
    qc_rsd_enabled=True,
    qc_rsd_threshold=0.20,
    # Row normalization (skip — already PQN-normalized)
    row_norm="None",
    # Transformation
    transform="LogNorm",        # glog2 (generalized log)
    # Scaling
    scaling="AutoNorm",         # auto-scaling (z-score)
)

print("\nPipeline log:")
for line in pipeline.log:
    print(f"  {line}")

print(f"\nProcessed data: {processed.shape[0]} samples x {processed.shape[1]} features")

# Get labels after pipeline (QC removed)
final_labels = pipeline.processed_labels
if final_labels is None:
    final_labels = labels

# Remove any remaining QC samples from labels/data if not already removed
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

# PCA Score plot
fig_score = plt.figure(figsize=(10, 8))
plot_pca_score(pca_result, pc_x=0, pc_y=1, fig=fig_score)
fig_score.savefig(os.path.join(OUTPUT_DIR, "pca_score_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_score)
print("  Saved pca_score_plot.png")

# PCA Scree plot
fig_scree = plt.figure(figsize=(8, 5))
plot_pca_scree(pca_result, fig=fig_scree)
fig_scree.savefig(os.path.join(OUTPUT_DIR, "pca_scree_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_scree)
print("  Saved pca_scree_plot.png")

# PCA Loading plot
fig_loading = plt.figure(figsize=(10, 6))
plot_pca_loading(pca_result, fig=fig_loading)
fig_loading.savefig(os.path.join(OUTPUT_DIR, "pca_loading_plot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_loading)
print("  Saved pca_loading_plot.png")

# ── Step 3: ANOVA (3-group) ─────────────────────────────
print("\n" + "=" * 60)
print("Running ANOVA (Tumor vs Normal vs Benignfat)...")
anova_result = run_anova(
    processed, final_labels,
    p_thresh=0.05,
    nonpar=False,
    use_fdr=True,
    posthoc=True,
)
sig_count = anova_result.n_significant
print(f"  Significant features (FDR < 0.05): {sig_count} / {len(anova_result.result_df)}")

# Save ANOVA results
anova_result.result_df.to_csv(os.path.join(OUTPUT_DIR, "anova_results.csv"))
print("  Saved anova_results.csv")

# ANOVA importance plot
fig_anova = plt.figure(figsize=(10, 8))
plot_anova_importance(anova_result, top_n=25, fig=fig_anova)
fig_anova.savefig(os.path.join(OUTPUT_DIR, "anova_importance.png"), dpi=150, bbox_inches="tight")
plt.close(fig_anova)
print("  Saved anova_importance.png")

# Top feature boxplots
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
groups = ["Tumor", "Normal", "Benignfat"]
pairs = [(groups[i], groups[j]) for i in range(len(groups)) for j in range(i + 1, len(groups))]

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

# Sample boxplot
fig_sbox = plt.figure(figsize=(16, 6))
plot_sample_boxplot(processed, final_labels, title="Sample Distribution (after processing)", fig=fig_sbox)
fig_sbox.savefig(os.path.join(OUTPUT_DIR, "sample_boxplot.png"), dpi=150, bbox_inches="tight")
plt.close(fig_sbox)
print("  Saved sample_boxplot.png")

# Density plot
fig_den = plt.figure(figsize=(10, 6))
plot_density(processed, final_labels, title="Density Plot (after processing)", fig=fig_den)
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
