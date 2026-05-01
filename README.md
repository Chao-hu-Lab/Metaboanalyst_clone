# MetaboAnalyst Clone

Desktop and CLI metabolomics analysis workflow inspired by MetaboAnalyst, with a focus on transparent preprocessing, marker-aware imputation, statistical reporting, and publication-oriented exports.

## Current Status

The current implementation includes the MA consumer for DNP Step4 feature metadata and the current CLI report workflow:

- Step4 feature metadata is parsed and preserved instead of being mistaken for sample columns.
- `is_Presence_Absence_Marker` is the only routing field for marker-aware imputation.
- Presence/absence marker features use min positive / 5 imputation; other features use the configured method, for example KNN.
- `Feature_Filter_Keep_Reasons` and `Imputation_Tag_Reasons` are retained as feature metadata and exported for audit.
- ComBat is available as an optional batch-correction method using `SampleInfo.Batch`, with label-preserving or SampleInfo covariate modes.
- CLI outputs are organized into a publication-oriented folder layout with `Summary.csv`, `significant_features_summary.xlsx`, and a curated `00_Review_Pack`.

## Quick Start

Run the pipeline with an input workbook and YAML config:

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

Outputs are written under `results\<input-stem><output.suffix>_<timestamp>\`.

## Input Contract

The recommended Excel input is a feature matrix with samples as columns and features as rows. If the workbook contains a `SampleInfo` sheet, MA uses it for group labels, pairing, concentration factors, and ComBat batch metadata where configured.

DNP Step4 metadata columns are treated as feature metadata, not sample columns:

- `is_Presence_Absence_Marker`
- `Feature_Filter_Keep_Reasons`
- `Imputation_Tag_Reasons`
- `Feature_Filter_Delete_Reasons`
- `Detection_Profile`
- `*_ratio`, including `QC_ratio`

If any Step4 metadata column is detected, `is_Presence_Absence_Marker` is required. Legacy MA inputs without Step4 metadata remain supported and default all marker flags to `False`.

## Imputation And Feature Metadata

The imputation router uses only `is_Presence_Absence_Marker`:

| Marker value | Imputation route |
|---|---|
| `True` | min positive / 5 |
| `False` | configured method, for example `pipeline.impute_method: "knn"` |

Reason and ratio fields are audit metadata only. They are not used to infer marker status.

`feature_metadata.csv` keeps the final feature metadata after preprocessing. Downstream result tables and workbook sheets preserve relevant Step4 metadata so the statistical results can be traced back to DNP Step4 decisions.

## ComBat Batch Correction

ComBat is opt-in through config:

```yaml
pipeline:
  batch_correction: "ComBat"

combat:
  covariate_mode: "labels"          # or "sample_info"
  sample_info_covariates: []        # required when covariate_mode is "sample_info"
  mean_only: false
  par_prior: true
  ref_batch: null
```

Current behavior:

- Batch labels come from `SampleInfo.Batch`.
- `covariate_mode: "labels"` preserves the current biological sample labels.
- `covariate_mode: "sample_info"` preserves selected SampleInfo covariates, such as `Sex`.
- The design is validated before running. Perfect or unsafe batch-label confounding blocks ComBat; strong overlap emits warnings in CLI and GUI.
- Missing-value imputation runs before ComBat.

## CLI Report Output

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

Key folders:

- `00_Review_Pack`: curated PNG-only quick review pack.
- `01_QC_and_Preprocessing`: processed data, sample labels, feature metadata, config copy, normalization comparison, PCA score plot.
- `02_Global_Profiling`: clustered `heatmap_top50.png` and grouped `heatmap_top50_grouped.png`.
- `03_Feature_Selection`: ANOVA, VIP, Volcano, OPLS-DA figures and CSV outputs.
- `04_Biomarker_Validation`: ROC and AUC ranking outputs.
- `05_Supplementary`: all-groups PLS-DA, outlier plots, Random Forest plots, ANOVA feature boxplots, paired-resolution audit.

When `pipeline.qc_rsd_enabled: false`, QC-RSD audit columns and `qc_rsd_audit.csv` are not emitted as fake disabled placeholders.

## Review Pack

`00_Review_Pack` contains the high-signal PNGs intended for fast review:

- PCA score plot
- grouped heatmap top 50
- ANOVA importance
- PLS-DA all-groups score plot
- for each configured comparison pair: OPLS-DA score, PLS-DA VIP, Volcano

The grouped heatmap is the Review Pack heatmap because it is easier to read by biological group. The clustered heatmap remains in `02_Global_Profiling` as a diagnostic view.

## Summary And Evidence Tier

`Summary.csv` and the `Summary` sheet in `significant_features_summary.xlsx` summarize feature-level evidence across ANOVA, VIP, and Volcano results.

`Evidence_Tier` is feature-level statistical evidence, not Step4 metadata:

| Tier | Meaning |
|---|---|
| `Tier1_ConcordantPairwise` | Same comparison pair is supported by VIP and Volcano top-15 evidence, or by VIP + Volcano plus ANOVA significance |
| `Tier2_MultiMethod` | At least two evidence families pass among ANOVA, VIP, and Volcano |
| `Tier3_SingleMethod` | Exactly one evidence family passes |
| `Tier0_NoStatEvidence` | No summary-eligible statistical evidence passes |

In `significant_features_summary.xlsx`, `Evidence_Tier` is color-coded:

- Tier1: green
- Tier2: blue
- Tier3: yellow
- Tier0: gray

Step4 detail columns such as reason and ratio metadata are preserved in the workbook and are collapsed by default in Excel. Use Excel's outline controls to expand them.

## Built-In Presets

GUI built-in presets live in `resources\presets\` and are whitelisted by `resources\presets\manifest.yaml`.

CLI configs live in `configs\`. Some configs are historical or validation profiles and are not automatically exposed as GUI presets.

Use `configs\Tissue_knn_rsd050_marker_verify.yaml` as the tracked tissue marker-verification CLI profile. For workflows where QC-RSD should be disabled because QC samples are not truly shared across batches, use or create a config with:

```yaml
pipeline:
  qc_rsd_enabled: false
```

## Development

Install dependencies:

```powershell
uv pip install -r requirements.txt
```

Run targeted tests:

```powershell
uv run pytest tests\test_run_from_config_input_formats.py -q
uv run pytest tests\test_publication_batch_report_smoke.py -q
uv run pytest tests\test_grouped_heatmap.py -q
```

See `AGENT.md` and `claude.md` for development workflow, architecture rules, and CI/test strategy.
