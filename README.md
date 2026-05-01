# MetaboAnalyst Clone

Desktop and CLI workflow for LC-MS metabolomics analysis. The project is
inspired by MetaboAnalyst-style analysis, but is implemented as a local,
auditable Python pipeline with explicit Excel input contracts, marker-aware
imputation, optional ComBat batch correction, and publication-oriented report
exports.

## What It Does

MetaboAnalyst Clone is designed for normalized feature matrices produced by an
upstream preprocessing workflow such as DNP. It consumes a feature matrix,
optional `SampleInfo`, and optional DNP Step4 feature metadata, then produces
statistical tables, diagnostic plots, curated review figures, and an annotated
summary workbook.

Current highlights:

- GUI and CLI execution paths share the same core pipeline.
- Excel inputs can include a `SampleInfo` sheet for group labels, pairing,
  concentration factors, and batch metadata.
- DNP Step4 metadata is recognized as feature metadata, not sample columns.
- `is_Presence_Absence_Marker` is the only routing authority for marker-aware
  imputation.
- Presence/absence marker features use min positive / 5 imputation; non-marker
  features use the configured imputation method, for example KNN.
- Optional ComBat correction runs after imputation and uses `SampleInfo.Batch`.
- CLI exports include `Summary.csv`, `significant_features_summary.xlsx`, and a
  curated PNG-only `00_Review_Pack`.
- `Evidence_Tier` summarizes cross-method statistical support across ANOVA,
  VIP, and Volcano evidence.

## Table Of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Input Workbook Contract](#input-workbook-contract)
- [Pipeline Overview](#pipeline-overview)
- [Configuration](#configuration)
- [Report Outputs](#report-outputs)
- [Review Pack](#review-pack)
- [Summary And Evidence Tier](#summary-and-evidence-tier)
- [GUI Workflow](#gui-workflow)
- [Project Layout](#project-layout)
- [Testing](#testing)
- [Documentation](#documentation)
- [License](#license)

## Installation

Recommended Windows / PowerShell setup:

```powershell
uv venv
uv pip install -r requirements.txt
```

If you already have a compatible environment, install the dependencies directly:

```powershell
python -m pip install -r requirements.txt
```

Core runtime dependencies include `numpy`, `pandas`, `scipy`,
`scikit-learn`, `statsmodels`, `matplotlib`, `seaborn`, `openpyxl`,
`PySide6`, `pyyaml`, `plotly`, `qnorm`, `fancyimpute`, and `inmoose`.

## Quick Start

Run the CLI pipeline with an input workbook and YAML config:

```powershell
run.cmd "C:\path\to\Step3_Normalized_SpecNorm_PQN.xlsx" "configs\Tissue_knn_rsd050_marker_verify.yaml"
```

Equivalent explicit wrapper:

```powershell
scripts\run_pipeline.cmd -Config "configs\Tissue_knn_rsd050_marker_verify.yaml" -Input "C:\path\to\Step3_Normalized_SpecNorm_PQN.xlsx"
```

Direct Python entry point:

```powershell
uv run python scripts\run_from_config.py configs\Tissue_knn_rsd050_marker_verify.yaml --input "C:\path\to\Step3_Normalized_SpecNorm_PQN.xlsx"
```

Launch the desktop GUI:

```powershell
uv run python main.py
```

CLI outputs are written under:

```text
results\<input-stem><output.suffix>_<timestamp>\
```

The suffix comes from `output.suffix` in the selected YAML config. Keep config
names and suffixes semantically aligned with the enabled options, for example
avoid an `_rsd050` suffix when QC-RSD filtering is disabled.

## Input Workbook Contract

The recommended input is an Excel workbook with:

- A feature matrix sheet with features as rows and samples as columns.
- A feature identifier column that can be used as the row index.
- Optional `SampleInfo` sheet with sample-level metadata.

`SampleInfo` is used for:

- group labels and GUI/CLI sample alignment;
- paired analysis identifiers;
- concentration metadata where configured;
- batch labels for ComBat through `SampleInfo.Batch`;
- future covariates such as sex or other study design variables.

### DNP Step4 Feature Metadata

DNP Step4 metadata columns are preserved as feature metadata and excluded from
the analysis matrix:

| Column pattern | Behavior |
|---|---|
| `is_Presence_Absence_Marker` | Required routing field when any Step4 metadata is present |
| `Feature_Filter_Keep_Reasons` | Optional audit metadata |
| `Imputation_Tag_Reasons` | Optional audit metadata |
| `Feature_Filter_Delete_Reasons` | Optional audit metadata if present in the main matrix |
| `Detection_Profile` | Optional audit metadata |
| `*_ratio`, `QC_ratio` | Parsed as numeric feature metadata and excluded from samples |

If any Step4 metadata column is detected, `is_Presence_Absence_Marker` must be
present and must use a supported boolean encoding. Legacy MA inputs with no
Step4 metadata remain supported and default all marker flags to `False`.

Supported marker encodings:

| True | False |
|---|---|
| `True`, `TRUE`, `true`, `1`, `1.0` | `False`, `FALSE`, `false`, `0`, `0.0` |

Blank or unknown marker values are validation errors because they would make
imputation routing ambiguous.

## Pipeline Overview

The CLI and GUI use the same high-level processing sequence:

1. Load the Excel matrix and optional `SampleInfo`.
2. Detect sample columns while excluding known feature metadata.
3. Convert zero-like missing values where configured.
4. Remove features by missingness threshold.
5. Apply marker-aware imputation.
6. Apply optional QC-RSD filtering when enabled.
7. Apply row normalization, transformation, optional ComBat, and scaling.
8. Run global profiling and statistical analyses.
9. Export annotated tables, plots, summary workbooks, and review figures.

Imputation routing is intentionally simple:

| Marker value | Imputation route |
|---|---|
| `True` | min positive / 5 |
| `False` | configured method, for example `pipeline.impute_method: "knn"` |

Reason and ratio metadata are not used to infer marker status.

## Configuration

CLI configs live in `configs\`. GUI built-in presets live in
`resources\presets\` and are whitelisted by `resources\presets\manifest.yaml`.
Not every CLI config is exposed as a GUI preset.

Use the tracked tissue marker-verification profile as a starting point:

```powershell
configs\Tissue_knn_rsd050_marker_verify.yaml
```

Common pipeline keys:

```yaml
pipeline:
  missing_thresh: 1.0
  impute_method: "knn"
  qc_rsd_enabled: true
  qc_rsd_threshold: 0.50
  row_norm: "None"
  transform: "Log10Norm"
  batch_correction: "None"
  scaling: "ParetoNorm"
```

When QC samples are not truly shared across batches, prefer disabling QC-RSD
filtering rather than emitting disabled placeholder columns:

```yaml
pipeline:
  qc_rsd_enabled: false
```

### ComBat

ComBat is opt-in and runs after missing-value imputation:

```yaml
pipeline:
  batch_correction: "ComBat"

combat:
  covariate_mode: "labels"          # "labels", "sample_info", or "none"
  sample_info_covariates: []        # required when covariate_mode is "sample_info"
  mean_only: false
  par_prior: true
  ref_batch: null
```

Current behavior:

- Batch labels come from `SampleInfo.Batch`.
- `covariate_mode: "labels"` preserves the configured biological labels.
- `covariate_mode: "sample_info"` preserves selected `SampleInfo` covariates.
- `covariate_mode: "none"` performs batch-only correction.
- Perfect or unsafe batch-label confounding blocks ComBat.
- Strong batch-label overlap emits warnings in both CLI and GUI.
- Single-batch data should leave ComBat disabled.

## Report Outputs

The CLI report is organized by analysis purpose:

```text
<output_dir>\
  00_Review_Pack\
  01_QC_and_Preprocessing\
  02_Global_Profiling\
  03_Feature_Selection\
  04_Biomarker_Validation\
  05_Supplementary\
  Summary.csv
  significant_features_summary.xlsx
```

| Output | Purpose |
|---|---|
| `Summary.csv` | Feature-level evidence summary for quick filtering and review |
| `significant_features_summary.xlsx` | Annotated workbook with summary and method-specific sheets |
| `feature_metadata.csv` | Final feature metadata after preprocessing |
| `00_Review_Pack\` | Curated PNG-only review set |
| `01_QC_and_Preprocessing\` | Processed data, labels, config copy, PCA, normalization comparison |
| `02_Global_Profiling\` | Clustered heatmap and grouped heatmap |
| `03_Feature_Selection\` | ANOVA, VIP, Volcano, OPLS-DA figures and CSV outputs |
| `04_Biomarker_Validation\` | ROC and AUC ranking outputs |
| `05_Supplementary\` | PLS-DA all-groups, outlier plots, Random Forest, boxplots, paired audit |

When `pipeline.qc_rsd_enabled: false`, QC-RSD audit columns and
`qc_rsd_audit.csv` are not emitted as fake disabled placeholders.

## Review Pack

`00_Review_Pack` contains high-signal PNGs intended for first-pass review:

- PCA score plot.
- Grouped heatmap top 50.
- ANOVA importance.
- PLS-DA all-groups score plot.
- For each configured comparison pair: OPLS-DA score, PLS-DA VIP, and Volcano.

The grouped heatmap is optimized for biological group readability:

- samples are ordered by `groups.include`;
- unknown groups are placed last;
- group-internal sample order follows the input matrix;
- group labels are shown in the left strip;
- feature order follows ANOVA ranking and is not column-clustered.

The original clustered `heatmap_top50.png` remains in `02_Global_Profiling` as
a diagnostic clustering view.

## Summary And Evidence Tier

`Summary.csv` and the `Summary` sheet in
`significant_features_summary.xlsx` summarize feature-level evidence across
ANOVA, VIP, and Volcano results.

`Evidence_Tier` is statistical evidence only. It is not derived from DNP Step4
reason or ratio metadata.

| Tier | Meaning |
|---|---|
| `Tier1_ConcordantPairwise` | Same comparison pair is supported by VIP and Volcano top-15 evidence, or by VIP + Volcano plus ANOVA significance |
| `Tier2_MultiMethod` | At least two evidence families pass among ANOVA, VIP, and Volcano |
| `Tier3_SingleMethod` | Exactly one evidence family passes |
| `Tier0_NoStatEvidence` | No summary-eligible statistical evidence passes |

Evidence family thresholds:

| Family | Rule |
|---|---|
| ANOVA | `pvalue_adj < 0.05` |
| VIP | `VIP > 1.0` |
| Volcano | `pvalue_adj < 0.05` and `abs(log2FC) >= 1.0` |

In `significant_features_summary.xlsx`, `Evidence_Tier` is color-coded:

| Tier | Color |
|---|---|
| Tier1 | green |
| Tier2 | blue |
| Tier3 | yellow |
| Tier0 | gray |

Step4 detail columns such as reason and ratio metadata are preserved in the
workbook and collapsed by default in Excel. Use Excel outline controls to
expand them when audit details are needed.

## GUI Workflow

Start the GUI with:

```powershell
uv run python main.py
```

The GUI supports:

- workbook import and sample alignment;
- Step4 metadata detection summary;
- presence/absence marker count;
- ratio and reason metadata validation;
- shared config/preset behavior with the CLI;
- ComBat controls and validation warnings;
- report generation through the same pipeline backend.

GUI import does not add new Step4 settings. It validates, summarizes, and
passes feature metadata into the shared pipeline.

## Project Layout

```text
analysis\        Statistical analysis modules
configs\         CLI YAML profiles
core\            Shared data loading, metadata, preprocessing, and validation
docs\            Specs, plans, testing notes, and implementation records
gui\             PySide6 desktop interface
resources\       GUI resources and built-in presets
scripts\         CLI entry points and utility scripts
tests\           Pytest regression and smoke coverage
translations\    i18n resources
visualization\   Plotting and report figure generation
```

## Testing

Run focused tests for the current metadata/report workflow:

```powershell
uv run pytest tests\test_run_from_config_input_formats.py -q
uv run pytest tests\test_grouped_heatmap.py -q
uv run pytest tests\test_publication_batch_report_smoke.py -q
```

Useful additional checks:

```powershell
uv run pytest -m "gui and not slow" -q
uv run pytest tests\test_publication_export_v2.py -q
python -m py_compile scripts\run_from_config.py visualization\heatmap.py visualization\__init__.py
```

For broader testing strategy, see `docs\testing\pytest-guidelines.md` and
`docs\testing\full-suite-strategy.md`.

## Documentation

Important project docs:

- `docs\specs\01-algorithms.md`
- `docs\specs\02-visualization.md`
- `docs\specs\03-gui.md`
- `docs\specs\06-compatibility.md`
- `docs\plans\2026-04-11-publication-batch-report-v1.md`
- `docs\plans\2026-04-24-ma-combat-preset-ui-validation-design.md`
- `resources\presets\README.md`
- `claude.md`

The root README is intended to stay concise enough for first-time users. Keep
long design notes, implementation plans, and test strategy details under
`docs\`.

## License

No repository license file is currently included. Add an explicit license file
before public redistribution or external reuse.
