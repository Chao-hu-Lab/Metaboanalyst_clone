# Publication-Oriented Batch Report V1

## Goal

Refactor the `run.cmd` / `scripts\run_from_config.py` batch output into a
publication-oriented report layout that:

- removes low-value or redundant figures
- adds a small set of high-value figures already supported by the codebase
- groups outputs by analysis narrative instead of dumping every artifact into one folder
- keeps the existing `run.cmd "<input.xlsx>" "<config.yaml>"` contract unchanged

## Scope

This iteration targets the CLI batch report only.

Included:

- batch output folder restructuring
- figure selection cleanup
- new core figures wired into batch export
- supplementary figure export for secondary evidence

Excluded:

- GUI changes
- HTML dashboard / report index
- new report-profile schema
- interactive-only charts as part of batch defaults

## Output Policy

### Remove From Default Batch Output

- `PCA Scree Plot`
- `PCA Loading Plot`
- standalone `Sample Boxplot`
- standalone `Density Plot`
- `PLS-DA Pairwise Score Plot`

### Core Report

- `Normalization Comparison Plot`
- `PCA Score Plot`
- `OPLS-DA Pairwise Score Plot`
- `OPLS-DA S-Plot`
- `Volcano Plot`
- `PLS-DA VIP Plot`
- `Heatmap`
- `ROC Curve`
- `AUC Ranking Bar Plot`
- `ANOVA Importance Plot`

### Supplementary / Advanced

- `PLS-DA All-Groups Score Plot`
- `Outlier T2 Plot`
- `DModX Plot`
- `Random Forest Feature Importance Plot`
- `Random Forest Confusion Matrix`
- `ANOVA Feature Boxplots`

### Not Included In Batch V1

- `3D PCA Plot`
- `Correlation Network`
- `Correlation Heatmap`
- `Clustering Dendrogram`
- `Clustering Summary Plot`

## Folder Structure

The output directory should be reorganized into these subfolders:

```text
<output_dir>/
  01_QC_and_Preprocessing/
  02_Global_Profiling/
  03_Feature_Selection/
  04_Biomarker_Validation/
  05_Supplementary/
```

### 01_QC_and_Preprocessing

- `normalization_comparison.png`
- `pca_score_plot.png`

### 02_Global_Profiling

- `heatmap_top50.png`

### 03_Feature_Selection

- `oplsda_score_{g1}_vs_{g2}.png`
- `oplsda_splot_{g1}_vs_{g2}.png`
- `volcano_{g1}_vs_{g2}.png`
- `plsda_vip_{g1}_vs_{g2}.png`
- `anova_importance.png`

### 04_Biomarker_Validation

- `roc_{g1}_vs_{g2}.png`
- `auc_ranking_{g1}_vs_{g2}.png`

### 05_Supplementary

- `plsda_score_all_groups.png`
- `outlier_t2.png`
- `outlier_dmodx.png`
- `rf_importance_{g1}_vs_{g2}.png`
- `rf_confusion_matrix_{g1}_vs_{g2}.png`
- `anova_boxplot_{g1}_vs_{g2}_top{n}.png`

## Export Limits

- Heatmap should be limited to `Top 30-50` features.
  - V1 default: `Top 50`
- ANOVA boxplots should be limited.
  - V1 default: `Top 10`
- ROC / AUC / Random Forest should be pairwise only.
- OPLS-DA remains the pairwise supervised score plot used in the core report.
- PLS-DA all-groups score plot remains supplementary only.

## Implementation Notes

### 1. Batch Runner

Primary integration point:

- `scripts\run_from_config.py`

Required changes:

- add a helper that creates the new report subdirectories
- route figure outputs into the new subdirectories
- stop exporting removed default figures
- keep CSV / Excel / config artifacts at the report root unless a better grouping is obvious

### 2. Normalization Comparison

Primary module:

- `visualization\norm_preview.py`

Requirements:

- show a real before/after comparison
- prefer compact, publication-friendly layout
- compare preprocessing state before normalization-related operations against the final processed matrix
- replace the old standalone sample distribution figures in the default report

### 3. Heatmap

Primary module:

- `visualization\heatmap.py`

Requirements:

- batch export only
- static figure only
- use a stable feature-selection rule

V1 feature-selection rule:

- prefer ANOVA-significant features when available
- otherwise fall back to top variable features
- cap the rendered features at 50

### 4. OPLS-DA S-Plot

Primary module:

- `visualization\oplsda_plot.py`

Requirements:

- export alongside each pairwise OPLS-DA score plot
- stable annotation behavior
- readable labels even with dense feature clouds

### 5. ROC / AUC

Primary module:

- `visualization\roc_plot.py`

Requirements:

- export both `ROC Curve` and `AUC Ranking`
- pairwise only
- output into `04_Biomarker_Validation`

### 6. Supplementary Figures

Supplementary exports should be informative but not overwhelm the core report.

V1 contents:

- all-groups PLS-DA score
- outlier plots
- random forest plots
- top-10 ANOVA feature boxplots

## Validation Targets

Use `configs\Tissue_knn_rsd050_marker_verify.yaml` as the first validation profile.

Validation should confirm:

- new folder structure exists
- removed default figures are no longer produced
- core report figures exist in the expected subfolders
- supplementary figures exist in the expected subfolder
- existing tabular outputs still exist

## Suggested Work Split

### Main Rollout

- write this plan document
- refactor `scripts\run_from_config.py`
- integrate new export layout and figure calls

### Worker A

- improve `visualization\norm_preview.py`
- harden `visualization\oplsda_plot.py` for batch S-plot export

### Worker B

- add smoke-style tests for new folder structure and output selection

## Future Follow-Ups

Potential V2 items:

- `--report-profile publication|full`
- HTML summary index
- optional interactive export bundle
- report manifest JSON for downstream automation
