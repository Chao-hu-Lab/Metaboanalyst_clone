# Publication Report V2 — Figure Quality & Table Organization

**Date:** 2026-04-12
**Status:** Approved
**Scope:** `run_from_config.py` batch export pipeline + visualization modules

---

## Problem Statement

PR #8 introduced publication batch report exports but only addressed figures partially.
Remaining issues:

1. **Tables** — CSV/Excel files are scattered in the output root instead of organized into
   the report directory structure (`01_QC/`, `02_Global/`, etc.)
2. **Figures** — Legend occlusion, inconsistent proportions, print-unfriendly confidence
   ellipses, missing jitter on boxplots, and other quality gaps identified via expert review.

---

## Design Decisions

### D1: Publication Export Profile — Default On, Opt-Out via Config

Batch export (`run_from_config.py`) defaults to publication-grade settings.
A `draft_mode: true` config option downgrades to fast preview.

```yaml
output:
  # draft_mode: true   # Uncomment for 150 dpi, PNG-only quick preview
```

### D2: Dual Output Format

Non-draft mode produces **PNG (300 DPI) + PDF (vector)** for every figure.
Draft mode produces PNG (150 DPI) only.

### D3: Table Organization Follows Figure Directories

Tables land in the same report subdirectory as their companion figures.
`significant_features_summary.xlsx` and `Summary.csv` stay at root (cross-analysis).

### D4: ms-core Boxplot Jitter

Jitter is a universal boxplot best practice — fix at source in ms-core submodule,
not via a local wrapper.

---

## Section 1: Publication Export Profile

### New function in `visualization/theme.py`

```python
def apply_publication_export_style(theme: str = "light") -> None:
    apply_publication_style(theme)
    plt.rcParams.update({
        "font.family": "Arial",
        "savefig.dpi": 300,
        "figure.dpi": 300,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
    })
```

### Upgraded `_save_figure` in `run_from_config.py`

```python
def _save_figure(fig, path: Path, *, draft_mode: bool = False) -> None:
    if draft_mode:
        fig.savefig(path, dpi=150, bbox_inches="tight")
    else:
        fig.savefig(path, dpi=300, bbox_inches="tight")
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
```

`draft_mode` read from `cfg["output"].get("draft_mode", False)` and threaded
through all `_save_figure` calls in `run_analysis()`.

---

## Section 2: Table Reorganization

### Target mapping

| File | Directory | Rationale |
|------|-----------|-----------|
| `processed_data.csv` | `01_QC_and_Preprocessing/` | Core preprocessed matrix |
| `sample_labels.csv` | `01_QC_and_Preprocessing/` | Group assignments |
| `feature_metadata.csv` | `01_QC_and_Preprocessing/` | Feature annotations |
| `qc_rsd_audit.csv` | `01_QC_and_Preprocessing/` | QC audit trail |
| `config_used.yaml` | `01_QC_and_Preprocessing/` | Reproducibility record |
| `pipeline_log.txt` | `01_QC_and_Preprocessing/` | **NEW** — pipeline.log text export |
| `anova_results.csv` | `03_Feature_Selection/` | ANOVA full results |
| `volcano_{g1}_vs_{g2}.csv` | `03_Feature_Selection/` | Volcano per-pair results |
| `roc_{g1}_vs_{g2}.csv` | `04_Biomarker_Validation/` | ROC per-pair results |
| `rf_importance_{g1}_vs_{g2}.csv` | `05_Supplementary/` | Random Forest importance |
| `outlier_results.csv` | `05_Supplementary/` | Outlier detection results |
| `paired_resolution_audit.csv` | `05_Supplementary/` | Paired resolution audit |
| `significant_features_summary.xlsx` | **Root** | Cross-analysis summary |
| `Summary.csv` | **Root** | Cross-analysis summary (CSV) |

---

## Section 3: Figure Improvements

### 3a. Global Changes

| Item | Change |
|------|--------|
| **Legend placement** | Score plots: `bbox_to_anchor=(1.05, 1)` outside right. Others: fixed position per plot type. Ban `loc="best"`. |
| **figsize standardization** | Score plots `(8, 8)` 1:1. Side-by-side `(16, 7)` ~2:1. Bar/lollipop: dynamic height. |
| **Confidence ellipses** | Remove fill entirely. Dashed border only (`linestyle="--"`, `fill=False`). Matches PLS-DA style. |

### 3b. Per-Plot Fixes

#### OPLS-DA Score Plot (`visualization/oplsda_plot.py`)
- Remove `fill_alpha` from confidence ellipses → dashed border only
- Confirm `adjustText` label repel is active

#### Heatmap (`visualization/heatmap.py`)
- When features > 50: hide X-axis tick labels entirely
- When features <= 50: keep 90-degree vertical labels
- Threshold constant: `_HEATMAP_XLABEL_THRESHOLD = 50`

#### Outlier Side-by-Side (`visualization/outlier_plot.py`)
- Change figsize to `(16, 7)` for 2:1 aspect ratio
- Use `GridSpec` or `constrained_layout` for strict top/bottom alignment
- `fig.align_ylabels()` to align Y-axis labels
- Confirm `adjustText` on outlier labels in both subplots

#### ANOVA Boxplot (`ms-core: visualization/anova_plot.py`)
- Add horizontal jitter to raw data points (stripplot or manual uniform offset)
- Prevents point overlap when sample counts are high or values are close
- **Cross-repo**: commit in ms-core first, then update submodule pointer

#### Confusion Matrix (`visualization/rf_plot.py` + `run_from_config.py`)
- When multiple confusion matrices are generated in the same report,
  lock `vmin=0` and `vmax=max_count_across_all_pairs`
- Implementation: `run_from_config.py` collects all RF results first, computes
  `global_vmax = max(cm.max() for cm in all_confusion_matrices)`, then passes
  `vmax=global_vmax` to each `plot_confusion_matrix()` call in the rendering pass

#### Volcano Plot (`visualization/volcano_plot.py`)
- Legend: `loc="best"` → `loc="upper right"`

#### Density Plot (`visualization/density_plot.py`)
- Legend: `loc="best"` → `loc="upper right"`

#### Boxplot (`visualization/boxplot.py`)
- Legend: `loc="best"` → `loc="upper left"`

#### S-Plot (`visualization/oplsda_plot.py`)
- Confirm `adjustText` label repel is active for top-N annotations

#### DModX / PCA Outlier (`visualization/outlier_plot.py`)
- Confirm `adjustText` label repel is active; fallback to offset if not installed

#### ROC / AUC Ranking
- No changes needed (already meets publication standards)

---

## Files Changed

### This repo (Metaboanalyst_clone)

| File | Changes |
|------|---------|
| `visualization/theme.py` | Add `apply_publication_export_style()` |
| `visualization/oplsda_plot.py` | Ellipse fill removal, adjustText confirm |
| `visualization/heatmap.py` | X-axis label auto-hide threshold |
| `visualization/outlier_plot.py` | 2:1 GridSpec, adjustText confirm |
| `visualization/volcano_plot.py` | Legend position fix |
| `visualization/density_plot.py` | Legend position fix |
| `visualization/boxplot.py` | Legend position fix |
| `visualization/rf_plot.py` | Confusion matrix vmin/vmax parameter |
| `scripts/run_from_config.py` | `_save_figure` upgrade, table reorganization, draft_mode, pipeline_log.txt, confusion matrix vmax coordination |

### ms-core (submodule)

| File | Changes |
|------|---------|
| `visualization/anova_plot.py` | Add jitter to boxplot data points |

---

## Out of Scope

- GUI-side rendering changes (stays at 150 DPI, DejaVu Sans)
- Interactive Plotly plot styling (HTML exports unchanged)
- New plot types
- Excel formatting/styling changes to `significant_features_summary.xlsx`
