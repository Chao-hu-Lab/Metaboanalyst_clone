"""
Tier analysis of significant features across control/loose/default/strict versions.

Tier 1 = significant in all 4 versions (most robust)
Tier 2 = significant in exactly 3 versions
Tier 3 = significant in exactly 2 versions
Tier 4 = significant in exactly 1 version
Tier 5 = never significant in any version (background)

A feature is counted as "significant in a version" if it is significant in
ANY of these analyses within that version:
  - ANOVA (3-group, FDR < 0.05)
  - Volcano: Exposure vs Normal (paired, FC≥2, FDR<0.05)
  - Volcano: Exposure vs Control (unpaired, FC≥2, FDR<0.05)
  - Volcano: Normal vs Control  (unpaired, FC≥2, FDR<0.05)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from upsetplot import UpSet, from_memberships

# ── Config ─────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = _PROJECT_ROOT / "results"

VERSIONS = ["Control", "Loose", "Default", "Strict"]
SUFFIXES = ["control", "loose", "default", "strict"]
FOLDER_PREFIX = "Step4_Normalized_PQN_SampleSpecific"

ANALYSES = {
    "ANOVA":    "anova_results.csv",
    "ExpNor":   "volcano_Exposure_vs_Normal.csv",
    "ExpCon":   "volcano_Exposure_vs_Control.csv",
    "NorCon":   "volcano_Normal_vs_Control.csv",
}

OUTPUT_DIR = RESULTS_ROOT / "_tier_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = {
    "Control": "#1F77B4",
    "Loose":   "#FF7F0E",
    "Default": "#2CA02C",
    "Strict":  "#D62728",
}
TIER_COLORS = {
    1: "#2ecc71",   # green  — most robust
    2: "#3498db",   # blue
    3: "#f39c12",   # orange
    4: "#e74c3c",   # red
    5: "#95a5a6",   # grey   — never significant
}

# ── Data loading ────────────────────────────────────────────────────────────

def load_significant_features(suffix: str) -> dict[str, set[str]]:
    """
    Return {analysis_name: set_of_significant_feature_names} for one version.
    """
    folder = RESULTS_ROOT / f"{FOLDER_PREFIX}{suffix}"
    result: dict[str, set[str]] = {}
    for name, filename in ANALYSES.items():
        path = folder / filename
        if not path.exists():
            result[name] = set()
            continue
        df = pd.read_csv(path)
        if "Feature" not in df.columns or "significant" not in df.columns:
            result[name] = set()
            continue
        sig = df.loc[df["significant"].astype(bool), "Feature"]
        result[name] = set(sig.tolist())
    return result


def build_presence_matrix() -> pd.DataFrame:
    """
    Build a DataFrame where rows = features, columns = versions.
    Cell value = True if the feature is significant in ≥1 analysis for that version.
    """
    version_sig: dict[str, set[str]] = {}
    all_features: set[str] = set()

    for version, suffix in zip(VERSIONS, SUFFIXES):
        by_analysis = load_significant_features(suffix)
        union = set().union(*by_analysis.values())
        version_sig[version] = union
        all_features.update(union)

        # Print per-version breakdown
        print(f"\n{version}:")
        for a_name, feats in by_analysis.items():
            print(f"  {a_name}: {len(feats)} significant")
        print(f"  → Union: {len(union)} unique significant features")

    # Build presence matrix
    features_sorted = sorted(all_features)
    mat = pd.DataFrame(
        {v: [f in version_sig[v] for f in features_sorted] for v in VERSIONS},
        index=features_sorted,
    )
    mat.index.name = "Feature"
    return mat, version_sig


def assign_tiers(mat: pd.DataFrame) -> pd.DataFrame:
    """Add Tier column based on how many versions feature is significant in."""
    mat = mat.copy()
    mat["n_versions"] = mat[VERSIONS].sum(axis=1)
    mat["Tier"] = mat["n_versions"].apply(lambda n: max(1, 5 - int(n)) if n > 0 else 5)
    # Tier = 5 - n_versions + 1 clamped: n=4→T1, n=3→T2, n=2→T3, n=1→T4
    tier_map = {4: 1, 3: 2, 2: 3, 1: 4}
    mat["Tier"] = mat["n_versions"].map(tier_map).fillna(5).astype(int)
    return mat


# ── Visualizations ──────────────────────────────────────────────────────────

def plot_tier_summary(mat: pd.DataFrame) -> plt.Figure:
    """Horizontal bar chart of tier counts with annotation."""
    tier_counts = mat.groupby("Tier").size()
    total = len(mat)

    fig, ax = plt.subplots(figsize=(9, 4.5))

    tier_labels = {
        1: "Tier 1\n(all 4 versions)",
        2: "Tier 2\n(3 versions)",
        3: "Tier 3\n(2 versions)",
        4: "Tier 4\n(1 version)",
    }
    tiers = [1, 2, 3, 4]
    counts = [tier_counts.get(t, 0) for t in tiers]
    colors = [TIER_COLORS[t] for t in tiers]
    labels = [tier_labels[t] for t in tiers]

    bars = ax.barh(labels[::-1], counts[::-1], color=colors[::-1],
                   edgecolor="white", linewidth=1.5, height=0.55)

    for bar, count in zip(bars, counts[::-1]):
        pct = count / total * 100
        ax.text(bar.get_width() + total * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{count}  ({pct:.1f}%)", va="center", fontsize=11, fontweight="bold")

    ax.set_xlim(0, max(counts) * 1.3)
    ax.set_xlabel("Number of features", fontsize=12)
    ax.set_title(
        f"Feature Stability Across Filtering Versions\n"
        f"(Total: {total} unique significant features)",
        fontsize=13, fontweight="bold",
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_tick_params(labelsize=10)
    plt.tight_layout()
    return fig


def plot_venn_diagram(version_sig: dict[str, set[str]]) -> plt.Figure:
    """3-set Venn (Loose/Default/Strict) + annotation for Control."""
    from matplotlib_venn import venn3

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Loose / Default / Strict (3-way)
    ax = axes[0]
    plt.sca(ax)
    sets = (
        version_sig["Loose"],
        version_sig["Default"],
        version_sig["Strict"],
    )
    venn3(
        sets,
        set_labels=("Loose", "Default", "Strict"),
        set_colors=("#FF7F0E", "#2CA02C", "#D62728"),
        alpha=0.55,
    )
    ax.set_title("Overlap: Loose / Default / Strict", fontsize=12, fontweight="bold")

    # Right: Control / Loose / Strict (another view)
    ax2 = axes[1]
    plt.sca(ax2)
    sets2 = (
        version_sig["Control"],
        version_sig["Loose"],
        version_sig["Strict"],
    )
    venn3(
        sets2,
        set_labels=("Control", "Loose", "Strict"),
        set_colors=("#1F77B4", "#FF7F0E", "#D62728"),
        alpha=0.55,
    )
    ax2.set_title("Overlap: Control / Loose / Strict", fontsize=12, fontweight="bold")

    fig.suptitle("Venn Diagrams of Significant Features", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    return fig


def plot_upset(mat: pd.DataFrame) -> plt.Figure:
    """UpSet plot showing all intersection combinations."""
    memberships = []
    for _, row in mat[VERSIONS].iterrows():
        membership = [v for v in VERSIONS if row[v]]
        if membership:
            memberships.append(membership)

    upset_data = from_memberships(memberships)

    # Assign colors per tier (subset size maps roughly to tier)
    fig = plt.figure(figsize=(12, 7))
    upset = UpSet(
        upset_data,
        subset_size="count",
        show_counts=True,
        sort_by="cardinality",
        sort_categories_by=None,
    )
    upset.plot(fig=fig)
    fig.suptitle(
        "UpSet Plot: Significant Feature Intersections Across Filtering Versions",
        fontsize=13, fontweight="bold", y=1.01,
    )
    return fig


def plot_presence_heatmap(mat: pd.DataFrame, top_n: int = 80) -> plt.Figure:
    """Heatmap showing feature × version presence, sorted by tier."""
    mat_sorted = mat.sort_values(["Tier", "Feature"])
    # Show top N: prefer Tier1, then Tier2, etc.
    display = mat_sorted.head(top_n)

    fig, ax = plt.subplots(figsize=(7, max(6, top_n * 0.18)))
    data = display[VERSIONS].values.astype(float)

    ax.imshow(data, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1, interpolation="nearest")

    # Color left edge by tier
    for i, (_, row) in enumerate(display.iterrows()):
        tier = row["Tier"]
        ax.add_patch(plt.Rectangle((-0.5, i - 0.5), 0.3, 1.0,
                                   color=TIER_COLORS[tier], clip_on=False))

    ax.set_xticks(range(len(VERSIONS)))
    ax.set_xticklabels(VERSIONS, fontsize=11, fontweight="bold")
    ax.set_yticks(range(len(display)))
    ax.set_yticklabels(display.index, fontsize=6.5)
    ax.set_title(f"Top {top_n} Significant Features by Tier\n(colored bar = Tier)",
                 fontsize=12, fontweight="bold")

    # Legend
    handles = [mpatches.Patch(color=TIER_COLORS[t], label=f"Tier {t}") for t in [1, 2, 3, 4]]
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.22, 1), fontsize=9,
              title="Tier", title_fontsize=9)

    plt.tight_layout()
    return fig


def plot_analysis_breakdown(version_sig: dict[str, set[str]], mat: pd.DataFrame) -> plt.Figure:
    """Stacked bar showing how many features per tier come from each version."""
    tier_version_counts = {}
    for tier in [1, 2, 3, 4]:
        tier_feats = mat[mat["Tier"] == tier].index.tolist()
        tier_version_counts[tier] = {v: sum(1 for f in tier_feats if f in version_sig[v])
                                     for v in VERSIONS}

    fig, ax = plt.subplots(figsize=(10, 5))
    tiers = [1, 2, 3, 4]
    x = np.arange(len(tiers))
    bar_width = 0.18

    for i, version in enumerate(VERSIONS):
        counts = [tier_version_counts[t].get(version, 0) for t in tiers]
        bars = ax.bar(x + i * bar_width, counts, bar_width,
                      label=version, color=PALETTE[version], alpha=0.85,
                      edgecolor="white", linewidth=0.8)
        for bar, c in zip(bars, counts):
            if c > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        str(c), ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x + bar_width * 1.5)
    ax.set_xticklabels(
        [f"Tier {t}\n({mat[mat['Tier']==t].shape[0]} features)" for t in tiers],
        fontsize=11,
    )
    ax.set_ylabel("Count of significant features in each version", fontsize=11)
    ax.set_title("Tier Distribution by Version", fontsize=13, fontweight="bold")
    ax.legend(title="Version", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    return fig


def plot_analysis_type_heatmap(mat: pd.DataFrame, version_sig: dict) -> plt.Figure:
    """
    Per-analysis-type breakdown: how many Tier-1 features are found in ANOVA vs Volcano.
    """
    # Load per-analysis sets for each version
    per_analysis: dict[str, dict[str, set]] = {}
    for version, suffix in zip(VERSIONS, SUFFIXES):
        per_analysis[version] = load_significant_features(suffix)

    tier1_feats = mat[mat["Tier"] == 1].index.tolist()

    analysis_names = list(ANALYSES.keys())
    data = np.zeros((len(tier1_feats), len(VERSIONS) * len(analysis_names)))
    col_labels = []
    for v in VERSIONS:
        for a in analysis_names:
            col_labels.append(f"{v}\n{a}")

    for row_i, feat in enumerate(tier1_feats):
        col_i = 0
        for v in VERSIONS:
            for a in analysis_names:
                data[row_i, col_i] = int(feat in per_analysis[v][a])
                col_i += 1

    if not tier1_feats:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No Tier 1 features", ha="center", transform=ax.transAxes)
        return fig

    fig, ax = plt.subplots(figsize=(max(10, len(col_labels) * 0.9),
                                    max(4, len(tier1_feats) * 0.32)))
    ax.imshow(data, aspect="auto", cmap="Blues", vmin=0, vmax=1, interpolation="nearest")

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=8, rotation=45, ha="right")
    ax.set_yticks(range(len(tier1_feats)))
    ax.set_yticklabels(tier1_feats, fontsize=7)
    ax.set_title("Tier 1 Features: Per-Analysis-Type Presence", fontsize=12, fontweight="bold")

    # Vertical dividers between versions
    for i in range(1, len(VERSIONS)):
        ax.axvline(i * len(analysis_names) - 0.5, color="white", linewidth=2)

    plt.tight_layout()
    return fig


# ── Excel export ────────────────────────────────────────────────────────────

def export_excel(mat: pd.DataFrame, version_sig: dict[str, set[str]]) -> Path:
    path = OUTPUT_DIR / "tier_analysis.xlsx"

    # Per-analysis breakdown for each feature
    per_analysis_data: dict[str, dict[str, set]] = {}
    for version, suffix in zip(VERSIONS, SUFFIXES):
        per_analysis_data[version] = load_significant_features(suffix)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Sheet 1: Summary counts
        summary = []
        for tier in [1, 2, 3, 4]:
            tier_feats = mat[mat["Tier"] == tier]
            row = {"Tier": f"Tier {tier}", "Feature_count": len(tier_feats)}
            for v in VERSIONS:
                row[f"Significant_in_{v}"] = int(mat.loc[mat["Tier"] == tier, v].sum())
            summary.append(row)
        pd.DataFrame(summary).to_excel(writer, sheet_name="Summary", index=False)

        # Sheet 2: Full matrix
        full = mat.reset_index()
        full.to_excel(writer, sheet_name="Full_Matrix", index=False)

        # Sheet 3-6: Per-tier feature lists
        for tier in [1, 2, 3, 4]:
            tier_feats = mat[mat["Tier"] == tier].index.tolist()
            rows = []
            for feat in tier_feats:
                row = {"Feature": feat, "Tier": tier, "n_versions": mat.loc[feat, "n_versions"]}
                for v in VERSIONS:
                    row[f"In_{v}"] = bool(mat.loc[feat, v])
                    for a in ANALYSES:
                        row[f"{v}_{a}"] = feat in per_analysis_data[v].get(a, set())
                rows.append(row)
            sheet_name = f"Tier{tier}_features"
            if rows:
                pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                pd.DataFrame(columns=["Feature"]).to_excel(writer, sheet_name=sheet_name, index=False)

    return path


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Tier Analysis: Significant Features Across Filtering Versions")
    print("=" * 60)

    mat, version_sig = build_presence_matrix()
    mat = assign_tiers(mat)

    print("\n" + "=" * 60)
    print("Tier Summary:")
    for tier in [1, 2, 3, 4]:
        n = (mat["Tier"] == tier).sum()
        desc = {1: "all 4 versions", 2: "3 versions", 3: "2 versions", 4: "1 version"}[tier]
        print(f"  Tier {tier} ({desc}): {n} features")
    print(f"  Total unique significant features: {len(mat)}")
    print("  Total unique features tested: —")

    # Save figures
    print("\nGenerating visualizations...")

    fig1 = plot_tier_summary(mat)
    fig1.savefig(OUTPUT_DIR / "1_tier_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig1)
    print("  Saved 1_tier_summary.png")

    fig2 = plot_venn_diagram(version_sig)
    fig2.savefig(OUTPUT_DIR / "2_venn_diagrams.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print("  Saved 2_venn_diagrams.png")

    fig3 = plot_upset(mat)
    fig3.savefig(OUTPUT_DIR / "3_upset_plot.png", dpi=150, bbox_inches="tight")
    plt.close(fig3)
    print("  Saved 3_upset_plot.png")

    fig4 = plot_presence_heatmap(mat, top_n=min(80, len(mat)))
    fig4.savefig(OUTPUT_DIR / "4_presence_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig4)
    print("  Saved 4_presence_heatmap.png")

    fig5 = plot_analysis_breakdown(version_sig, mat)
    fig5.savefig(OUTPUT_DIR / "5_tier_by_version.png", dpi=150, bbox_inches="tight")
    plt.close(fig5)
    print("  Saved 5_tier_by_version.png")

    if (mat["Tier"] == 1).sum() > 0:
        fig6 = plot_analysis_type_heatmap(mat, version_sig)
        fig6.savefig(OUTPUT_DIR / "6_tier1_analysis_breakdown.png", dpi=150, bbox_inches="tight")
        plt.close(fig6)
        print("  Saved 6_tier1_analysis_breakdown.png")

    excel_path = export_excel(mat, version_sig)
    print(f"\nExcel exported: {excel_path}")

    # Also copy to NTU cancer location
    import shutil
    ntu_dir = Path(r"C:\Users\user\Desktop\NTU cancer\version_comparison_new\toolkit_DNP_MA\_tier_analysis")
    ntu_dir.mkdir(parents=True, exist_ok=True)
    for f in OUTPUT_DIR.iterdir():
        shutil.copy2(f, ntu_dir / f.name)
    print(f"Copied to: {ntu_dir}")

    print("\nDone!")
    return mat


if __name__ == "__main__":
    mat = main()
