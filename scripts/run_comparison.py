"""
Comparison analysis: evaluate MZmine alignment and DNP preprocessing effects.

Comparison 1: non-MZmine (baseline) vs MZmine -> MZmine alignment quality
Comparison 2: non-MZmine (baseline) vs DNP   -> preprocessing improvement
"""

import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure project root on path (scripts/ lives one level below project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────
RESULTS_ROOT = os.path.join(_PROJECT_ROOT, "results")
DIRS = {
    "baseline": "STEP1_program2_DNA_alignment_20260225_112532",   # non-MZmine
    "mzmine":   "mzmine_FH_aligment_NTU_DNA_AfterVBA_1",
    "dnp":      "STEP4_program2_DNA_alignment_20260227_220832",   # DNP preprocessed
}
LABELS = {
    "baseline": "non-MZmine (STEP1, 基準)",
    "mzmine":   "MZmine 對齊",
    "dnp":      "DNP 前處理 (STEP4)",
}
COLORS = {
    "baseline": "#3498db",
    "mzmine":   "#e67e22",
    "dnp":      "#2ecc71",
}

OUTPUT_DIR = os.path.join(RESULTS_ROOT, "_comparison")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Load data ─────────────────────────────────────────────
def load_result(key):
    d = os.path.join(RESULTS_ROOT, DIRS[key])
    df = pd.read_csv(os.path.join(d, "processed_data.csv"), index_col=0)
    labels = pd.read_csv(os.path.join(d, "sample_labels.csv"), index_col=0).iloc[:, 0]
    anova = pd.read_csv(os.path.join(d, "anova_results.csv"))
    return df, labels, anova


data = {}
for key in DIRS:
    data[key] = load_result(key)
    print(f"Loaded {LABELS[key]}: {data[key][0].shape}")


# ── Feature matching (fuzzy Mz/RT) ───────────────────────
def parse_mzrt(name):
    """Parse 'mz/rt' into (float, float)."""
    parts = str(name).split("/")
    return float(parts[0]), float(parts[1])


def match_features(feats_a, feats_b, mz_tol=0.01, rt_tol=0.1):
    """Match features between two sets by Mz/RT proximity."""
    parsed_a = [(f, *parse_mzrt(f)) for f in feats_a]
    parsed_b = [(f, *parse_mzrt(f)) for f in feats_b]
    matches = []
    used_b = set()
    for name_a, mz_a, rt_a in parsed_a:
        best = None
        best_dist = float("inf")
        for i, (name_b, mz_b, rt_b) in enumerate(parsed_b):
            if i in used_b:
                continue
            if abs(mz_a - mz_b) <= mz_tol and abs(rt_a - rt_b) <= rt_tol:
                dist = abs(mz_a - mz_b) + abs(rt_a - rt_b)
                if dist < best_dist:
                    best = i
                    best_dist = dist
        if best is not None:
            matches.append((name_a, parsed_b[best][0]))
            used_b.add(best)
    return matches


print("\n" + "=" * 60)
print("Feature overlap analysis")
print("=" * 60)

baseline_feats = list(data["baseline"][0].columns)
mzmine_feats = list(data["mzmine"][0].columns)
dnp_feats = list(data["dnp"][0].columns)

match_bm = match_features(baseline_feats, mzmine_feats)
match_bd = match_features(baseline_feats, dnp_feats)

print(f"\nnon-MZmine: {len(baseline_feats)} features")
print(f"MZmine:     {len(mzmine_feats)} features")
print(f"DNP:        {len(dnp_feats)} features")
print(f"\nnon-MZmine n MZmine: {len(match_bm)} shared features")
print(f"non-MZmine n DNP:    {len(match_bd)} shared features")

print("\nShared features (non-MZmine <-> MZmine):")
for a, b in match_bm:
    print(f"  {a:25s} <-> {b}")
print("\nShared features (non-MZmine <-> DNP):")
for a, b in match_bd:
    print(f"  {a:25s} <-> {b}")


# ══════════════════════════════════════════════════════════
# Figure 1: Overview dashboard
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("Generating comparison figures...")

fig1, axes = plt.subplots(2, 3, figsize=(18, 11))
fig1.suptitle("Pipeline Comparison Dashboard", fontsize=16, fontweight="bold", y=0.98)

# --- Row 1: Summary metrics ---
# 1a: Feature count bar
ax = axes[0, 0]
keys = ["baseline", "mzmine", "dnp"]
counts = [data[k][0].shape[1] for k in keys]
bars = ax.bar([LABELS[k] for k in keys], counts,
              color=[COLORS[k] for k in keys], edgecolor="white", width=0.6)
for bar, c in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
            str(c), ha="center", fontsize=14, fontweight="bold")
ax.set_ylabel("Feature count")
ax.set_title("QC-RSD 後保留的特徵數")
ax.tick_params(axis="x", labelsize=8)

# 1b: ANOVA significant ratio
ax = axes[0, 1]
sig_ratios = []
for k in keys:
    anova_df = data[k][2]
    sig = anova_df["significant"].sum()
    total = len(anova_df)
    sig_ratios.append(sig / total * 100)
bars = ax.bar([LABELS[k] for k in keys], sig_ratios,
              color=[COLORS[k] for k in keys], edgecolor="white", width=0.6)
for bar, r in zip(bars, sig_ratios):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            f"{r:.0f}%", ha="center", fontsize=14, fontweight="bold")
ax.set_ylabel("Significant %")
ax.set_ylim(0, 100)
ax.set_title("ANOVA 顯著特徵比例 (FDR<0.05)")
ax.tick_params(axis="x", labelsize=8)

# 1c: PCA PC1 variance explained
ax = axes[0, 2]
from ms_core.analysis.pca import run_pca  # noqa: E402
pc1_vars = []
for k in keys:
    df, lab, _ = data[k]
    pca_r = run_pca(df, lab, n_components=3)
    pc1_vars.append(pca_r.explained_variance_ratio[0] * 100)
bars = ax.bar([LABELS[k] for k in keys], pc1_vars,
              color=[COLORS[k] for k in keys], edgecolor="white", width=0.6)
for bar, v in zip(bars, pc1_vars):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
            f"{v:.1f}%", ha="center", fontsize=14, fontweight="bold")
ax.set_ylabel("Variance explained (%)")
ax.set_title("PCA PC1 解釋變異量")
ax.tick_params(axis="x", labelsize=8)

# --- Row 2: Detailed comparison ---
# 2a: Feature Venn-style overlap
ax = axes[1, 0]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_aspect("equal")
# baseline circle
c1 = plt.Circle((4, 5.5), 2.5, fill=False, edgecolor=COLORS["baseline"], linewidth=2.5)
c2 = plt.Circle((6, 5.5), 2.5, fill=False, edgecolor=COLORS["mzmine"], linewidth=2.5, linestyle="--")
c3 = plt.Circle((5, 3.5), 2.5, fill=False, edgecolor=COLORS["dnp"], linewidth=2.5, linestyle=":")
ax.add_patch(c1)
ax.add_patch(c2)
ax.add_patch(c3)
# Labels
only_base_m = len(baseline_feats) - len(match_bm)
only_mzmine = len(mzmine_feats) - len(match_bm)
only_base_d = len(baseline_feats) - len(match_bd)
only_dnp = len(dnp_feats) - len(match_bd)
ax.text(2.5, 6.5, f"{only_base_m}", fontsize=13, ha="center", fontweight="bold", color=COLORS["baseline"])
ax.text(7.5, 6.5, f"{only_mzmine}", fontsize=13, ha="center", fontweight="bold", color=COLORS["mzmine"])
ax.text(5, 6, f"{len(match_bm)}", fontsize=14, ha="center", fontweight="bold", color="#333")
ax.text(3.5, 2.5, f"{len(match_bd)}", fontsize=13, ha="center", fontweight="bold", color="#333")
ax.text(5, 1.5, f"{only_dnp}", fontsize=13, ha="center", fontweight="bold", color=COLORS["dnp"])
ax.text(2.0, 8.2, f"non-MZmine ({len(baseline_feats)})", fontsize=9, color=COLORS["baseline"], fontweight="bold")
ax.text(6.5, 8.2, f"MZmine ({len(mzmine_feats)})", fontsize=9, color=COLORS["mzmine"], fontweight="bold")
ax.text(3.5, 0.5, f"DNP ({len(dnp_feats)})", fontsize=9, color=COLORS["dnp"], fontweight="bold")
ax.set_title("特徵重疊 (Mz/RT matching)")
ax.axis("off")

# 2b: ANOVA -log10(p) comparison for shared features (baseline vs mzmine)
ax = axes[1, 1]
if match_bm:
    base_anova = data["baseline"][2].set_index("Feature")
    mz_anova = data["mzmine"][2].set_index("Feature")
    xs, ys, feat_labels = [], [], []
    for fa, fb in match_bm:
        if fa in base_anova.index and fb in mz_anova.index:
            xs.append(base_anova.loc[fa, "neg_log10p"])
            ys.append(mz_anova.loc[fb, "neg_log10p"])
            feat_labels.append(fa.split("/")[0][:8])
    ax.scatter(xs, ys, c=COLORS["mzmine"], s=80, edgecolor="white", zorder=3)
    for i, lab in enumerate(feat_labels):
        ax.annotate(lab, (xs[i], ys[i]), fontsize=6, textcoords="offset points", xytext=(5, 5))
    lim = max(max(xs, default=1), max(ys, default=1)) * 1.15
    ax.plot([0, lim], [0, lim], "k--", alpha=0.3, linewidth=1)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
ax.set_xlabel("non-MZmine -log10(p_adj)")
ax.set_ylabel("MZmine -log10(p_adj)")
ax.set_title(f"ANOVA 顯著性比較\n(共 {len(match_bm)} 共有特徵)")

# 2c: ANOVA -log10(p) comparison for shared features (baseline vs dnp)
ax = axes[1, 2]
if match_bd:
    base_anova = data["baseline"][2].set_index("Feature")
    dnp_anova = data["dnp"][2].set_index("Feature")
    xs, ys, feat_labels = [], [], []
    for fa, fb in match_bd:
        if fa in base_anova.index and fb in dnp_anova.index:
            xs.append(base_anova.loc[fa, "neg_log10p"])
            ys.append(dnp_anova.loc[fb, "neg_log10p"])
            feat_labels.append(fa.split("/")[0][:8])
    ax.scatter(xs, ys, c=COLORS["dnp"], s=80, edgecolor="white", zorder=3)
    for i, lab in enumerate(feat_labels):
        ax.annotate(lab, (xs[i], ys[i]), fontsize=6, textcoords="offset points", xytext=(5, 5))
    lim = max(max(xs, default=1), max(ys, default=1)) * 1.15
    ax.plot([0, lim], [0, lim], "k--", alpha=0.3, linewidth=1)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
ax.set_xlabel("non-MZmine -log10(p_adj)")
ax.set_ylabel("DNP -log10(p_adj)")
ax.set_title(f"ANOVA 顯著性比較\n(共 {len(match_bd)} 共有特徵)")

fig1.tight_layout(rect=[0, 0, 1, 0.95])
fig1.savefig(os.path.join(OUTPUT_DIR, "01_dashboard.png"), dpi=150, bbox_inches="tight")
plt.close(fig1)
print("  Saved 01_dashboard.png")


# ══════════════════════════════════════════════════════════
# Figure 2: PCA score plots side-by-side
# ══════════════════════════════════════════════════════════
from ms_core.visualization.pca_plot import plot_pca_score  # noqa: E402

fig2, axes2 = plt.subplots(1, 3, figsize=(21, 6))
fig2.suptitle("PCA Score Plots — 三種處理方式比較", fontsize=14, fontweight="bold")

for i, k in enumerate(keys):
    df, lab, _ = data[k]
    pca_r = run_pca(df, lab, n_components=5)
    plot_pca_score(pca_r, pc_x=0, pc_y=1, fig=None)
    plt.close()  # close auto-created figure
    # Redraw on our axes
    ax = axes2[i]
    scores = pca_r.scores
    evr = pca_r.explained_variance_ratio
    groups = sorted(set(lab))
    group_colors = {"Exposure": "#e74c3c", "Normal": "#3498db", "Control": "#2ecc71"}
    for g in groups:
        mask = (lab.values == g) if hasattr(lab, "values") else (np.array(lab) == g)
        ax.scatter(scores[mask, 0], scores[mask, 1], label=g, s=40, alpha=0.7,
                   color=group_colors.get(g, "#999"))
        # 95% confidence ellipse
        if mask.sum() > 2:
            from matplotlib.patches import Ellipse
            from scipy.stats import chi2
            pts = scores[mask, :2]
            cov = np.cov(pts.T)
            mean = pts.mean(axis=0)
            vals, vecs = np.linalg.eigh(cov)
            order = vals.argsort()[::-1]
            vals, vecs = vals[order], vecs[:, order]
            angle = np.degrees(np.arctan2(vecs[1, 0], vecs[0, 0]))
            w, h = 2 * np.sqrt(vals * chi2.ppf(0.95, 2))
            ell = Ellipse(mean, w, h, angle=angle, fill=False,
                          edgecolor=group_colors.get(g, "#999"), linestyle="--", alpha=0.5)
            ax.add_patch(ell)
    ax.set_xlabel(f"PC1 ({evr[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({evr[1]*100:.1f}%)")
    ax.set_title(LABELS[k], color=COLORS[k], fontweight="bold")
    ax.legend(fontsize=8, loc="best")
    ax.axhline(0, color="grey", linewidth=0.5, alpha=0.3)
    ax.axvline(0, color="grey", linewidth=0.5, alpha=0.3)

fig2.tight_layout(rect=[0, 0, 1, 0.93])
fig2.savefig(os.path.join(OUTPUT_DIR, "02_pca_comparison.png"), dpi=150, bbox_inches="tight")
plt.close(fig2)
print("  Saved 02_pca_comparison.png")


# ══════════════════════════════════════════════════════════
# Figure 3: Shared-feature ANOVA F-statistic comparison
# ══════════════════════════════════════════════════════════
fig3, axes3 = plt.subplots(1, 2, figsize=(16, 7))
fig3.suptitle("共有特徵 ANOVA F-statistic 比較", fontsize=14, fontweight="bold")

# baseline vs mzmine
ax = axes3[0]
if match_bm:
    base_anova = data["baseline"][2].set_index("Feature")
    mz_anova = data["mzmine"][2].set_index("Feature")
    feat_short, f_base, f_mz = [], [], []
    for fa, fb in sorted(match_bm, key=lambda x: base_anova.loc[x[0], "F_statistic"] if x[0] in base_anova.index else 0, reverse=True):
        if fa in base_anova.index and fb in mz_anova.index:
            feat_short.append(fa.split("/")[0][:10])
            f_base.append(base_anova.loc[fa, "F_statistic"])
            f_mz.append(mz_anova.loc[fb, "F_statistic"])
    y = np.arange(len(feat_short))
    h = 0.35
    ax.barh(y + h/2, f_base, h, label="non-MZmine", color=COLORS["baseline"], edgecolor="white")
    ax.barh(y - h/2, f_mz, h, label="MZmine", color=COLORS["mzmine"], edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(feat_short, fontsize=9)
    ax.legend(fontsize=9)
    ax.set_xlabel("F-statistic")
ax.set_title("non-MZmine vs MZmine\n(共有特徵 F-statistic)")

# baseline vs dnp
ax = axes3[1]
if match_bd:
    base_anova = data["baseline"][2].set_index("Feature")
    dnp_anova = data["dnp"][2].set_index("Feature")
    feat_short, f_base, f_dnp = [], [], []
    for fa, fb in sorted(match_bd, key=lambda x: base_anova.loc[x[0], "F_statistic"] if x[0] in base_anova.index else 0, reverse=True):
        if fa in base_anova.index and fb in dnp_anova.index:
            feat_short.append(fa.split("/")[0][:10])
            f_base.append(base_anova.loc[fa, "F_statistic"])
            f_dnp.append(dnp_anova.loc[fb, "F_statistic"])
    y = np.arange(len(feat_short))
    h = 0.35
    ax.barh(y + h/2, f_base, h, label="non-MZmine", color=COLORS["baseline"], edgecolor="white")
    ax.barh(y - h/2, f_dnp, h, label="DNP", color=COLORS["dnp"], edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(feat_short, fontsize=9)
    ax.legend(fontsize=9)
    ax.set_xlabel("F-statistic")
ax.set_title("non-MZmine vs DNP\n(共有特徵 F-statistic)")

fig3.tight_layout(rect=[0, 0, 1, 0.93])
fig3.savefig(os.path.join(OUTPUT_DIR, "03_f_statistic_comparison.png"), dpi=150, bbox_inches="tight")
plt.close(fig3)
print("  Saved 03_f_statistic_comparison.png")


# ══════════════════════════════════════════════════════════
# Figure 4: Density plot comparison (data distribution)
# ══════════════════════════════════════════════════════════
fig4, axes4 = plt.subplots(1, 3, figsize=(18, 5))
fig4.suptitle("處理後數據分布 (Density)", fontsize=14, fontweight="bold")

for i, k in enumerate(keys):
    ax = axes4[i]
    df, lab, _ = data[k]
    for g in sorted(set(lab)):
        mask = lab == g
        vals = df.loc[mask].values.flatten()
        vals = vals[np.isfinite(vals)]
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(vals)
        x_grid = np.linspace(vals.min(), vals.max(), 300)
        ax.plot(x_grid, kde(x_grid), label=g, alpha=0.8, linewidth=1.5)
        ax.fill_between(x_grid, kde(x_grid), alpha=0.15)
    ax.set_title(LABELS[k], color=COLORS[k], fontweight="bold")
    ax.set_xlabel("Value (glog + AutoScale)")
    ax.legend(fontsize=8)

fig4.tight_layout(rect=[0, 0, 1, 0.93])
fig4.savefig(os.path.join(OUTPUT_DIR, "04_density_comparison.png"), dpi=150, bbox_inches="tight")
plt.close(fig4)
print("  Saved 04_density_comparison.png")


# ══════════════════════════════════════════════════════════
# Figure 5: Comprehensive summary table
# ══════════════════════════════════════════════════════════
fig5, ax5 = plt.subplots(figsize=(14, 8))
ax5.axis("off")

# Build summary table
metrics = [
    "原始輸入特徵數",
    "QC-RSD 後特徵數",
    "最終特徵數 (pipeline後)",
    "ANOVA 顯著特徵 (FDR<0.05)",
    "ANOVA 顯著比例",
    "PCA PC1 解釋量",
    "PCA PC1+PC2 解釋量",
    "Volcano: Expo vs Norm 顯著",
    "Volcano: Expo vs Ctrl 顯著",
    "Volcano: Norm vs Ctrl 顯著",
    "與 non-MZmine 共有特徵數",
]

# Read original feature counts from raw data
raw_counts = {"baseline": 1575, "mzmine": 823, "dnp": 297}
# Read volcano results
vol_data = {}
for k in keys:
    vol_data[k] = {}
    d = os.path.join(RESULTS_ROOT, DIRS[k])
    for pair in ["Exposure_vs_Normal", "Exposure_vs_Control", "Normal_vs_Control"]:
        try:
            vdf = pd.read_csv(os.path.join(d, f"volcano_{pair}.csv"))
            vol_data[k][pair] = vdf["significant"].sum() if "significant" in vdf.columns else "N/A"
        except FileNotFoundError:
            vol_data[k][pair] = "N/A"

table_data = []
for k in keys:
    df, lab, anova_df = data[k]
    pca_r = run_pca(df, lab, n_components=5)
    evr = pca_r.explained_variance_ratio
    sig = anova_df["significant"].sum()
    total = len(anova_df)
    overlap = len(match_bm) if k == "mzmine" else (len(match_bd) if k == "dnp" else "—(基準)")
    row = [
        str(raw_counts[k]),
        "—",  # QC-RSD count not stored; use final
        str(df.shape[1]),
        f"{sig}/{total}",
        f"{sig/total*100:.0f}%",
        f"{evr[0]*100:.1f}%",
        f"{(evr[0]+evr[1])*100:.1f}%",
        str(vol_data[k].get("Exposure_vs_Normal", "N/A")),
        str(vol_data[k].get("Exposure_vs_Control", "N/A")),
        str(vol_data[k].get("Normal_vs_Control", "N/A")),
        str(overlap),
    ]
    table_data.append(row)

col_labels = [LABELS[k] for k in keys]
table = ax5.table(
    cellText=list(zip(*table_data)),  # transpose for row-per-metric
    rowLabels=metrics,
    colLabels=col_labels,
    cellLoc="center",
    rowLoc="right",
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.0, 1.8)

# Color header
for j, k in enumerate(keys):
    table[0, j].set_facecolor(COLORS[k])
    table[0, j].set_text_props(color="white", fontweight="bold")
for i in range(len(metrics)):
    for j in range(len(keys)):
        table[i + 1, j].set_facecolor("#f8f9fa" if i % 2 == 0 else "white")

ax5.set_title("三種處理方式綜合比較", fontsize=14, fontweight="bold", pad=20)
fig5.tight_layout()
fig5.savefig(os.path.join(OUTPUT_DIR, "05_summary_table.png"), dpi=150, bbox_inches="tight")
plt.close(fig5)
print("  Saved 05_summary_table.png")


# ══════════════════════════════════════════════════════════
# Text summary report
# ══════════════════════════════════════════════════════════
report = []
report.append("=" * 60)
report.append("COMPARISON REPORT")
report.append("=" * 60)
report.append("")
report.append("【比較 1】non-MZmine vs MZmine（MZmine 對齊效果評估）")
report.append("-" * 40)
report.append(f"  共有特徵: {len(match_bm)}/{len(baseline_feats)} (non-MZmine) = {len(match_bm)/len(baseline_feats)*100:.0f}%")
report.append(f"  共有特徵: {len(match_bm)}/{len(mzmine_feats)} (MZmine) = {len(match_bm)/len(mzmine_feats)*100:.0f}%")
report.append(f"  MZmine 獨有: {len(mzmine_feats) - len(match_bm)} 特徵")
report.append(f"  non-MZmine 獨有: {len(baseline_feats) - len(match_bm)} 特徵")

# Compare F-stats for shared features
if match_bm:
    base_a = data["baseline"][2].set_index("Feature")
    mz_a = data["mzmine"][2].set_index("Feature")
    f_base_list = [base_a.loc[fa, "F_statistic"] for fa, fb in match_bm if fa in base_a.index]
    f_mz_list = [mz_a.loc[fb, "F_statistic"] for fa, fb in match_bm if fb in mz_a.index]
    avg_f_base = np.mean(f_base_list)
    avg_f_mz = np.mean(f_mz_list)
    better = "MZmine" if avg_f_mz > avg_f_base else "non-MZmine"
    report.append(f"  共有特徵平均 F-stat: non-MZmine={avg_f_base:.2f}, MZmine={avg_f_mz:.2f}")
    report.append(f"  -> 共有特徵上 {better} 的組間差異更大")

report.append("")
report.append("【比較 2】non-MZmine vs DNP（前處理效果評估）")
report.append("-" * 40)
report.append(f"  共有特徵: {len(match_bd)}/{len(baseline_feats)} (non-MZmine) = {len(match_bd)/len(baseline_feats)*100:.0f}%")
report.append(f"  共有特徵: {len(match_bd)}/{len(dnp_feats)} (DNP) = {len(match_bd)/len(dnp_feats)*100:.0f}%")
report.append(f"  DNP 獨有: {len(dnp_feats) - len(match_bd)} 特徵")
report.append(f"  non-MZmine 獨有: {len(baseline_feats) - len(match_bd)} 特徵")

if match_bd:
    base_a = data["baseline"][2].set_index("Feature")
    dnp_a = data["dnp"][2].set_index("Feature")
    f_base_list = [base_a.loc[fa, "F_statistic"] for fa, fb in match_bd if fa in base_a.index]
    f_dnp_list = [dnp_a.loc[fb, "F_statistic"] for fa, fb in match_bd if fb in dnp_a.index]
    avg_f_base = np.mean(f_base_list)
    avg_f_dnp = np.mean(f_dnp_list)
    better = "DNP" if avg_f_dnp > avg_f_base else "non-MZmine"
    report.append(f"  共有特徵平均 F-stat: non-MZmine={avg_f_base:.2f}, DNP={avg_f_dnp:.2f}")
    report.append(f"  -> 共有特徵上 {better} 的組間差異更大")

report.append("")
report.append("【結論】")
report.append("-" * 40)

# PC1 comparison
pc1_base = pc1_vars[0]
pc1_mz = pc1_vars[1]
pc1_dnp = pc1_vars[2]
report.append(f"  PCA 分離度 (PC1): non-MZmine={pc1_base:.1f}%, MZmine={pc1_mz:.1f}%, DNP={pc1_dnp:.1f}%")
if pc1_dnp > pc1_base > pc1_mz:
    report.append("  -> DNP 前處理提升了 PCA 分離度，MZmine 對齊未提升")
elif pc1_mz > pc1_base:
    report.append("  -> MZmine 對齊提升了 PCA 分離度")
elif pc1_dnp > pc1_base:
    report.append("  -> DNP 前處理提升了 PCA 分離度")

report_text = "\n".join(report)
print(report_text)

with open(os.path.join(OUTPUT_DIR, "comparison_report.txt"), "w", encoding="utf-8") as f:
    f.write(report_text)
print("\n  Saved comparison_report.txt")

print("\n" + "=" * 60)
print("ALL COMPARISON FILES:")
for fn in sorted(os.listdir(OUTPUT_DIR)):
    size = os.path.getsize(os.path.join(OUTPUT_DIR, fn))
    print(f"  {fn:45s} ({size / 1024:.0f} KB)")
