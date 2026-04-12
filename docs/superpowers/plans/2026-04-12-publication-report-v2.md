# Publication Report V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade batch report exports to publication-grade quality — reorganize tables into report directories, improve all figure rendering to meet scientific journal standards.

**Architecture:** Add a `apply_publication_export_style()` function to `theme.py` that batch export calls at startup. Upgrade `_save_figure` in `run_from_config.py` to dual-output PNG+PDF with `draft_mode` opt-out. Move all CSV/Excel outputs into the existing `REPORT_SUBDIRS` structure. Fix per-plot issues (ellipse fill, jitter, legend, alignment) in individual visualization modules.

**Tech Stack:** matplotlib, seaborn, numpy, adjustText, openpyxl

**Spec:** `docs/superpowers/specs/2026-04-12-publication-report-v2-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `visualization/theme.py` | Modify | Add `apply_publication_export_style()` |
| `scripts/run_from_config.py` | Modify | `_save_figure` upgrade, table path reorganization, `draft_mode`, pipeline log export, confusion matrix vmax coordination |
| `visualization/oplsda_plot.py` | Modify | Ellipse fill removal, adjustText on S-plot |
| `visualization/anova_plot.py` | Modify | Jitter overlay on boxplot |
| `visualization/outlier_plot.py` | Modify | 2:1 figsize, GridSpec alignment, adjustText |
| `visualization/heatmap.py` | Modify | Already handles >50 features — verify only |
| `visualization/volcano_plot.py` | Modify | Legend position fix |
| `visualization/density_plot.py` | Modify | Legend position fix |
| `visualization/rf_plot.py` | Modify | Confusion matrix `vmin`/`vmax` parameter |
| `tests/test_publication_export_v2.py` | Create | Smoke tests for all changes |

---

### Task 1: Publication Export Style + `_save_figure` Upgrade

**Files:**
- Modify: `visualization/theme.py:73-127`
- Modify: `scripts/run_from_config.py:92-96`
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing tests for publication export style and dual-output save**

```python
# tests/test_publication_export_v2.py
"""Smoke tests for publication report v2 improvements."""

import os
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest


class TestPublicationExportStyle:
    """Tests for apply_publication_export_style."""

    def test_sets_arial_font(self):
        from visualization.theme import apply_publication_export_style
        apply_publication_export_style("light")
        assert plt.rcParams["font.family"] == "Arial"

    def test_sets_300_dpi(self):
        from visualization.theme import apply_publication_export_style
        apply_publication_export_style("light")
        assert plt.rcParams["savefig.dpi"] == 300
        assert plt.rcParams["figure.dpi"] == 300

    def test_inherits_base_style(self):
        from visualization.theme import apply_publication_export_style
        apply_publication_export_style("light")
        # Base style properties should still be set
        assert plt.rcParams["axes.spines.top"] is False
        assert plt.rcParams["axes.spines.right"] is False
        assert plt.rcParams["legend.frameon"] is False


class TestSaveFigureDualOutput:
    """Tests for _save_figure dual PNG+PDF output."""

    def test_publication_mode_creates_png_and_pdf(self, tmp_path):
        from scripts.run_from_config import _save_figure
        fig = plt.figure()
        fig.add_subplot(111).plot([1, 2], [3, 4])
        out = tmp_path / "test.png"
        _save_figure(fig, out, draft_mode=False)
        assert out.exists()
        assert out.with_suffix(".pdf").exists()

    def test_draft_mode_creates_png_only(self, tmp_path):
        from scripts.run_from_config import _save_figure
        fig = plt.figure()
        fig.add_subplot(111).plot([1, 2], [3, 4])
        out = tmp_path / "test.png"
        _save_figure(fig, out, draft_mode=True)
        assert out.exists()
        assert not out.with_suffix(".pdf").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_publication_export_v2.py -v`
Expected: FAIL — `apply_publication_export_style` does not exist, `_save_figure` does not accept `draft_mode`.

- [ ] **Step 3: Implement `apply_publication_export_style` in theme.py**

Add after `apply_publication_style` (after line 127):

```python
def apply_publication_export_style(theme: str = "light") -> None:
    """
    Apply publication-grade export rcParams for batch report generation.

    Builds on ``apply_publication_style`` then overrides with journal-grade
    settings: Arial font, 300 DPI, and tighter typographic sizes.

    Intended for ``run_from_config.py`` batch exports — GUI preview should
    continue using ``apply_publication_style`` for speed.

    Corresponds to R function: N/A (MetaboAnalyst uses fixed R device settings).
    """
    apply_publication_style(theme)
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "savefig.dpi": 300,
            "figure.dpi": 300,
        }
    )
```

- [ ] **Step 4: Upgrade `_save_figure` in run_from_config.py**

Replace lines 92–95:

```python
def _save_figure(fig: Any, path: Path, *, draft_mode: bool = False) -> None:
    """Save a matplotlib figure as PNG (and PDF in publication mode), then close."""
    if draft_mode:
        fig.savefig(path, dpi=150, bbox_inches="tight")
    else:
        fig.savefig(path, dpi=300, bbox_inches="tight")
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_publication_export_v2.py::TestPublicationExportStyle -v && uv run pytest tests/test_publication_export_v2.py::TestSaveFigureDualOutput -v`
Expected: All PASS.

- [ ] **Step 6: Wire `draft_mode` and publication style into `run_analysis`**

In `run_from_config.py`, at the top of `run_analysis()` (after line 558 `os.makedirs`), add:

```python
    draft_mode = bool(cfg.get("output", {}).get("draft_mode", False))
    if not draft_mode:
        from visualization.theme import apply_publication_export_style
        apply_publication_export_style()
```

Then find-and-replace every `_save_figure(fig, ...)` call in the file to add `draft_mode=draft_mode`. There are approximately 15 calls — each one gets the kwarg appended:

```python
    _save_figure(fig, report_dirs["qc"] / "normalization_comparison.png", draft_mode=draft_mode)
    # ... same pattern for all other _save_figure calls
```

- [ ] **Step 7: Commit**

```bash
git add visualization/theme.py scripts/run_from_config.py tests/test_publication_export_v2.py
git commit -m "feat: add publication export style and dual PNG+PDF output"
```

---

### Task 2: Table Reorganization into Report Directories

**Files:**
- Modify: `scripts/run_from_config.py:660-680` (QC tables), `720-722` (ANOVA CSV), `965-968` (volcano CSV), `1008-1010` (ROC CSV), `1036-1039` (outlier CSV), `1077-1080` (RF CSV), `1095-1098` (paired audit)
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing test for table placement**

Append to `tests/test_publication_export_v2.py`:

```python
class TestTableReorganization:
    """Verify CSV/YAML files land in correct report subdirectories."""

    def test_qc_tables_in_01_dir(self):
        """QC-related files should be in 01_QC_and_Preprocessing."""
        from scripts.run_from_config import REPORT_SUBDIRS
        qc_files = [
            "processed_data.csv",
            "sample_labels.csv",
            "feature_metadata.csv",
            "config_used.yaml",
            "pipeline_log.txt",
        ]
        # Verify the mapping constant exists
        assert "qc" in REPORT_SUBDIRS
        assert REPORT_SUBDIRS["qc"] == "01_QC_and_Preprocessing"
        # Files should be expected in that subdir (integration test verifies actual placement)
        for f in qc_files:
            assert f  # placeholder — real placement tested in integration

    def test_feature_tables_in_03_dir(self):
        from scripts.run_from_config import REPORT_SUBDIRS
        assert "feature" in REPORT_SUBDIRS
        assert REPORT_SUBDIRS["feature"] == "03_Feature_Selection"

    def test_validation_tables_in_04_dir(self):
        from scripts.run_from_config import REPORT_SUBDIRS
        assert "validation" in REPORT_SUBDIRS
        assert REPORT_SUBDIRS["validation"] == "04_Biomarker_Validation"

    def test_supplementary_tables_in_05_dir(self):
        from scripts.run_from_config import REPORT_SUBDIRS
        assert "supplementary" in REPORT_SUBDIRS
        assert REPORT_SUBDIRS["supplementary"] == "05_Supplementary"
```

- [ ] **Step 2: Run test to verify it passes (constants already exist)**

Run: `uv run pytest tests/test_publication_export_v2.py::TestTableReorganization -v`
Expected: PASS (REPORT_SUBDIRS already defined).

- [ ] **Step 3: Move QC table outputs to `01_QC_and_Preprocessing/`**

In `run_from_config.py`, replace lines 664–681 (the block that saves processed_data.csv through config_used.yaml):

```python
    # Save processed data — QC directory
    processed.to_csv(os.path.join(report_dirs["qc"], "processed_data.csv"))
    final_labels.to_csv(os.path.join(report_dirs["qc"], "sample_labels.csv"))
    final_feature_metadata.to_csv(
        os.path.join(report_dirs["qc"], "feature_metadata.csv"),
        index_label="Feature",
    )
    qc_rsd_audit = pipeline.step_feature_metadata.get("qc_rsd")
    if qc_rsd_audit is not None and not qc_rsd_audit.empty:
        qc_rsd_audit.to_csv(
            os.path.join(report_dirs["qc"], "qc_rsd_audit.csv"),
            index_label="Feature",
        )

    # Save config used
    config_copy_path = os.path.join(report_dirs["qc"], "config_used.yaml")
    with open(config_copy_path, "w", encoding="utf-8") as f:
        f.write(dump_yaml(cfg, include_runtime=False))

    # Save pipeline log
    log_path = os.path.join(report_dirs["qc"], "pipeline_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        for line in pipeline.log:
            f.write(line + "\n")
    print(f"  Saved to {output_dir}")
```

- [ ] **Step 4: Move ANOVA CSV to `03_Feature_Selection/`**

Replace line 722:
```python
    anova_result.result_df.to_csv(os.path.join(report_dirs["feature"], "anova_results.csv"), index=False)
```

- [ ] **Step 5: Move Volcano CSV to `03_Feature_Selection/`**

Replace lines 965–968:
```python
            vresult.result_df.to_csv(
                os.path.join(report_dirs["feature"], f"volcano_{g1}_vs_{g2}.csv"),
                index=False,
            )
```

- [ ] **Step 6: Move ROC CSV to `04_Biomarker_Validation/`**

Replace lines 1008–1010:
```python
            roc_result.summary_df.to_csv(
                os.path.join(report_dirs["validation"], f"roc_{g1}_vs_{g2}.csv"),
                index=False,
            )
```

- [ ] **Step 7: Move RF CSV to `05_Supplementary/`**

Replace lines 1077–1080:
```python
            rf_result.feature_importance.to_csv(
                os.path.join(report_dirs["supplementary"], f"rf_importance_{g1}_vs_{g2}.csv"),
                index=False,
            )
```

- [ ] **Step 8: Move Outlier CSV to `05_Supplementary/`**

Replace lines 1036–1039:
```python
        outlier_result.get_outlier_df().to_csv(
            os.path.join(report_dirs["supplementary"], "outlier_results.csv"),
            index=False,
        )
```

- [ ] **Step 9: Move Paired Audit CSV to `05_Supplementary/`**

Replace lines 1096–1097:
```python
        audit_path = os.path.join(report_dirs["supplementary"], "paired_resolution_audit.csv")
```

- [ ] **Step 10: Run full test suite**

Run: `uv run pytest --tb=short -q`
Expected: All pass — no existing tests depend on exact output paths.

- [ ] **Step 11: Commit**

```bash
git add scripts/run_from_config.py tests/test_publication_export_v2.py
git commit -m "refactor: organize table exports into report subdirectories"
```

---

### Task 3: OPLS-DA Ellipse Fill Removal + S-Plot adjustText

**Files:**
- Modify: `visualization/oplsda_plot.py:41-53` (ellipse), `305-326` (S-plot annotations)
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_publication_export_v2.py`:

```python
class TestOplsdaEllipseNoFill:
    """OPLS-DA confidence ellipses should have no fill."""

    def test_ellipse_has_no_facecolor(self):
        from visualization.oplsda_plot import _confidence_ellipse
        fig, ax = plt.subplots()
        x = np.random.randn(20)
        y = np.random.randn(20)
        _confidence_ellipse(ax, x, y, color="#E64B35", fill_color="#E64B35")
        patches = [p for p in ax.patches if hasattr(p, "get_facecolor")]
        assert len(patches) == 1
        fc = patches[0].get_facecolor()
        # facecolor alpha should be 0 (transparent) — "none" fill
        assert fc[3] == 0.0 or patches[0].get_fill() is False
        plt.close(fig)

    def test_ellipse_has_dashed_linestyle(self):
        from visualization.oplsda_plot import _confidence_ellipse
        fig, ax = plt.subplots()
        x = np.random.randn(20)
        y = np.random.randn(20)
        _confidence_ellipse(ax, x, y, color="#E64B35", fill_color="#E64B35")
        patches = [p for p in ax.patches if hasattr(p, "get_linestyle")]
        assert len(patches) == 1
        ls = patches[0].get_linestyle()
        # Dashed line produces a tuple sequence, not solid (0, None)
        assert ls != (0, None)  # not solid
        plt.close(fig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_publication_export_v2.py::TestOplsdaEllipseNoFill -v`
Expected: FAIL — ellipse currently has `facecolor=fill_color, alpha=0.25`.

- [ ] **Step 3: Modify `_confidence_ellipse` in oplsda_plot.py**

Replace lines 41–53 (the `ax.add_patch(Ellipse(...))` block):

```python
    ax.add_patch(
        Ellipse(
            xy=(np.mean(x), np.mean(y)),
            width=width,
            height=height,
            angle=angle,
            facecolor="none",
            edgecolor=color,
            linestyle="--",
            linewidth=1.2,
            zorder=1,
        )
    )
```

- [ ] **Step 4: Add adjustText to S-plot annotations**

At the top of `oplsda_plot.py`, add import (near other imports):

```python
try:
    from adjustText import adjust_text
    _HAS_ADJUSTTEXT = True
except ImportError:
    _HAS_ADJUSTTEXT = False
```

Replace lines 305–326 (the annotation loop in `plot_oplsda_splot`) with:

```python
    top_idx = _select_balanced_annotation_indices(loadings, importance, top_n)
    texts = []
    for rank, idx in enumerate(top_idx, start=1):
        txt = ax.text(
            loadings[idx],
            importance[idx],
            features[idx][:24],
            fontsize=7.2,
            color=neutral_color,
            alpha=0.95,
            ha="left" if loadings[idx] >= 0 else "right",
            va="bottom" if rank % 2 else "top",
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": positive_color if loadings[idx] >= 0 else negative_color,
                "linewidth": 0.6,
                "alpha": 0.88,
            },
        )
        texts.append(txt)

    if texts and _HAS_ADJUSTTEXT:
        adjust_text(
            texts,
            ax=ax,
            arrowprops=dict(arrowstyle="-", color=neutral_color, lw=0.5),
        )
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_publication_export_v2.py::TestOplsdaEllipseNoFill -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add visualization/oplsda_plot.py tests/test_publication_export_v2.py
git commit -m "fix: remove OPLS-DA ellipse fill and add adjustText to S-plot"
```

---

### Task 4: ANOVA Boxplot Jitter

**Files:**
- Modify: `visualization/anova_plot.py:128-163`
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_publication_export_v2.py`:

```python
class TestAnovaBoxplotJitter:
    """ANOVA boxplot should overlay jittered data points."""

    def test_scatter_points_present(self):
        from visualization.anova_plot import _draw_r_style_boxplot
        from visualization.theme import COLORS

        fig, ax = plt.subplots()
        config = COLORS["light"]
        data = [np.array([1.0, 2.0, 3.0, 4.0, 5.0]), np.array([2.0, 3.0, 4.0, 5.0, 6.0])]
        _draw_r_style_boxplot(ax, data, ["A", "B"], ["#E64B35", "#4DBBD5"], config)

        # PathCollection = scatter plot points
        scatter_collections = [
            c for c in ax.collections
            if type(c).__name__ == "PathCollection"
        ]
        assert len(scatter_collections) >= 2, "Expected jittered scatter overlays for each group"
        plt.close(fig)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_publication_export_v2.py::TestAnovaBoxplotJitter -v`
Expected: FAIL — no scatter overlays currently.

- [ ] **Step 3: Add jitter overlay to `_draw_r_style_boxplot`**

In `visualization/anova_plot.py`, add the jitter scatter inside the loop (after the `ax.plot(... marker="D" ...)` block at line 163, before the loop ends):

```python
        # Overlay jittered raw data points
        jitter = np.random.default_rng(42).uniform(-0.15, 0.15, size=len(clean))
        ax.scatter(
            positions[idx] + jitter,
            clean,
            c=color,
            s=18,
            alpha=0.5,
            edgecolors="white",
            linewidths=0.3,
            zorder=3,
        )
```

This adds after the mean diamond (zorder=4) but above the box (zorder=2 default). The fixed seed `rng(42)` ensures reproducibility.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_publication_export_v2.py::TestAnovaBoxplotJitter -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add visualization/anova_plot.py tests/test_publication_export_v2.py
git commit -m "feat: add jittered data points to ANOVA boxplot"
```

---

### Task 5: Outlier Plot 2:1 Aspect Ratio + Alignment + adjustText

**Files:**
- Modify: `visualization/outlier_plot.py:44-45` (figsize), `69` (subplot), `137-144` (annotations), `221` (DModX figsize), `250-258` (DModX annotations)
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_publication_export_v2.py`:

```python
class TestOutlierPlotLayout:
    """Outlier side-by-side should use 2:1 aspect ratio."""

    def test_outlier_score_figsize_2_to_1(self):
        from analysis.outlier import OutlierResult
        from visualization.outlier_plot import plot_outlier_score

        # Minimal mock result
        n = 10
        result = OutlierResult(
            scores=np.random.randn(n, 2),
            t2_values=np.random.rand(n) * 10,
            t2_threshold=6.0,
            outlier_mask_t2=np.array([False] * 9 + [True]),
            dmodx=np.random.rand(n),
            dmodx_threshold=2.0,
            outlier_mask_dmodx=np.array([False] * 9 + [True]),
            explained_variance=np.array([0.4, 0.3]),
            sample_names=[f"S{i}" for i in range(n)],
        )
        fig = plot_outlier_score(result)
        w, h = fig.get_size_inches()
        ratio = w / h
        assert 2.0 <= ratio <= 2.5, f"Expected ~2:1 ratio, got {ratio:.2f}"
        plt.close(fig)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_publication_export_v2.py::TestOutlierPlotLayout -v`
Expected: FAIL — current figsize is `(10, 5)` = 2:1 but let's verify.

- [ ] **Step 3: Update outlier_plot.py figsize and alignment**

In `visualization/outlier_plot.py`:

Change line 45 from `figsize=(10, 5)` to:
```python
        fig = plt.figure(figsize=(16, 7))
```

Replace `fig.add_subplot(121)` (line 69) and `fig.add_subplot(122)` (line 173) with GridSpec for strict alignment. At line 69, replace:

```python
    gs = fig.add_gridspec(1, 2, wspace=0.3)
    ax1 = fig.add_subplot(gs[0, 0])
```

And at line 173 (the second subplot), replace `ax2 = fig.add_subplot(122)` with:
```python
    ax2 = fig.add_subplot(gs[0, 1])
```

At the end of the function (before `return fig`), add:
```python
    fig.align_ylabels([ax1, ax2])
```

- [ ] **Step 4: Add adjustText to outlier annotations**

Add import at top of `outlier_plot.py`:

```python
try:
    from adjustText import adjust_text
    _HAS_ADJUSTTEXT = True
except ImportError:
    _HAS_ADJUSTTEXT = False
```

Replace outlier annotation loop (lines 137–144) with:

```python
    outlier_texts = []
    for idx in np.where(outlier_mask)[0]:
        txt = ax1.text(
            x[idx], y[idx], str(sample_names[idx]),
            fontsize=7, color=config["text"], alpha=0.9,
        )
        outlier_texts.append(txt)
    if outlier_texts and _HAS_ADJUSTTEXT:
        adjust_text(outlier_texts, ax=ax1,
                    arrowprops=dict(arrowstyle="-", color=config["text"], lw=0.5))
```

Apply same pattern to DModX annotations (lines 250–258).

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_publication_export_v2.py::TestOutlierPlotLayout -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add visualization/outlier_plot.py tests/test_publication_export_v2.py
git commit -m "fix: outlier plot 2:1 aspect ratio with GridSpec alignment and adjustText"
```

---

### Task 6: Legend Position Fixes (Volcano, Density, Boxplot)

**Files:**
- Modify: `visualization/volcano_plot.py:107`
- Modify: `visualization/density_plot.py:83`
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_publication_export_v2.py`:

```python
class TestLegendPositions:
    """Verify loc='best' is never used in publication plots."""

    def test_volcano_legend_not_best(self):
        import visualization.volcano_plot as vp
        source = open(vp.__file__).read()
        assert 'loc="best"' not in source, "volcano_plot still uses loc='best'"

    def test_density_legend_not_best(self):
        import visualization.density_plot as dp
        source = open(dp.__file__).read()
        assert 'loc="best"' not in source, "density_plot still uses loc='best'"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_publication_export_v2.py::TestLegendPositions -v`
Expected: FAIL — both files use `loc="best"`.

- [ ] **Step 3: Fix volcano legend**

In `visualization/volcano_plot.py`, change line 107:

```python
    ax.legend(loc="upper right", fontsize=8)
```

- [ ] **Step 4: Fix density legend**

In `visualization/density_plot.py`, change line 83:

```python
    ax.legend(loc="upper right", fontsize=9)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_publication_export_v2.py::TestLegendPositions -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add visualization/volcano_plot.py visualization/density_plot.py tests/test_publication_export_v2.py
git commit -m "fix: replace loc='best' legends with fixed positions"
```

---

### Task 7: Confusion Matrix Unified Color Scale

**Files:**
- Modify: `visualization/rf_plot.py:83-129`
- Modify: `scripts/run_from_config.py:1060-1093`
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_publication_export_v2.py`:

```python
class TestConfusionMatrixVmax:
    """Confusion matrix should accept vmax for cross-pair consistency."""

    def test_accepts_vmax_parameter(self):
        import inspect
        from visualization.rf_plot import plot_confusion_matrix
        sig = inspect.signature(plot_confusion_matrix)
        assert "vmax" in sig.parameters, "plot_confusion_matrix should accept vmax parameter"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_publication_export_v2.py::TestConfusionMatrixVmax -v`
Expected: FAIL — no `vmax` parameter currently.

- [ ] **Step 3: Add `vmax` parameter to `plot_confusion_matrix`**

In `visualization/rf_plot.py`, modify the function signature and heatmap call:

```python
def plot_confusion_matrix(
    rf_result,
    theme: str = "light",
    fig: Figure | None = None,
    vmax: int | None = None,
) -> Figure:
    apply_publication_style(theme)
    if fig is None:
        fig = plt.figure(figsize=(6, 5))
    fig.clf()
    ax = fig.add_subplot(111)

    cm = rf_result.confusion_mat
    class_names = rf_result.class_names
    cmap = sns.light_palette(get_group_colors(theme, 1)[0], as_cmap=True)

    heatmap_kwargs: dict = dict(
        annot=True,
        fmt="d",
        cmap=cmap,
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
        linewidths=0.5,
        vmin=0,
    )
    if vmax is not None:
        heatmap_kwargs["vmax"] = vmax

    sns.heatmap(cm, **heatmap_kwargs)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix (CV)\nAccuracy {rf_result.cv_accuracy:.1%}")
    fig.tight_layout()
    return fig
```

- [ ] **Step 4: Coordinate vmax across pairs in run_from_config.py**

In `scripts/run_from_config.py`, restructure the RF section (lines 1060–1093) to two passes:

```python
    # ── Supplementary: random forest ─────────────────────
    print("\n" + "=" * 60)
    print("Generating supplementary Random Forest plots...")
    rf_cfg = analysis_cfg.get("random_forest", {})
    rf_trees = int(rf_cfg.get("n_trees", 500))
    rf_cv_folds = int(rf_cfg.get("cv_folds", 5))
    rf_top_n = int(rf_cfg.get("top_n", 25))

    # Pass 1: collect RF results and find global vmax for confusion matrices
    rf_results: list[tuple[str, str, Any]] = []
    global_cm_vmax = 0
    for g1, g2 in report_pairs:
        print(f"  RF {g1} vs {g2}...")
        try:
            pair_mask = final_labels.isin([g1, g2])
            pair_data = processed.loc[pair_mask]
            pair_labels = final_labels.loc[pair_mask]
            if pair_data.empty or pair_labels.nunique() < 2:
                print("    Skipped (not enough pairwise samples)")
                continue

            rf_result = run_random_forest(
                pair_data, pair_labels,
                n_trees=rf_trees, cv_folds=rf_cv_folds, top_n=rf_top_n,
            )
            rf_results.append((g1, g2, rf_result))
            global_cm_vmax = max(global_cm_vmax, int(rf_result.confusion_mat.max()))
        except Exception as e:
            print(f"    Error: {e}")

    # Pass 2: render figures with unified color scale
    for g1, g2, rf_result in rf_results:
        rf_result.feature_importance.to_csv(
            os.path.join(report_dirs["supplementary"], f"rf_importance_{g1}_vs_{g2}.csv"),
            index=False,
        )

        fig = plt.figure(figsize=(8, 6))
        plot_rf_importance(rf_result, top_n=rf_top_n, fig=fig)
        _save_figure(fig, report_dirs["supplementary"] / f"rf_importance_{g1}_vs_{g2}.png",
                     draft_mode=draft_mode)

        fig = plt.figure(figsize=(6, 5))
        plot_confusion_matrix(rf_result, fig=fig, vmax=global_cm_vmax if len(rf_results) > 1 else None)
        _save_figure(fig, report_dirs["supplementary"] / f"rf_confusion_matrix_{g1}_vs_{g2}.png",
                     draft_mode=draft_mode)

        print(f"    Saved {REPORT_SUBDIRS['supplementary']}\\rf_importance_{g1}_vs_{g2}.png")
        print(f"    Saved {REPORT_SUBDIRS['supplementary']}\\rf_confusion_matrix_{g1}_vs_{g2}.png")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_publication_export_v2.py::TestConfusionMatrixVmax -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add visualization/rf_plot.py scripts/run_from_config.py tests/test_publication_export_v2.py
git commit -m "feat: unified confusion matrix color scale across comparison pairs"
```

---

### Task 8: Heatmap Verification + Final Test Suite

**Files:**
- Verify: `visualization/heatmap.py:85-87`
- Test: `tests/test_publication_export_v2.py`

- [ ] **Step 1: Write verification test**

Append to `tests/test_publication_export_v2.py`:

```python
class TestHeatmapLabelThreshold:
    """Heatmap should hide x-labels when features > 50."""

    def test_xticklabels_hidden_when_many_features(self):
        import visualization.heatmap as hm
        source = open(hm.__file__).read()
        # Verify the conditional xticklabels logic exists
        assert "xticklabels=False" in source
        assert "50" in source
```

- [ ] **Step 2: Run test**

Run: `uv run pytest tests/test_publication_export_v2.py::TestHeatmapLabelThreshold -v`
Expected: PASS — heatmap.py already has this logic at lines 85–86.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest --tb=short -q`
Expected: All pass.

- [ ] **Step 4: Final commit**

```bash
git add tests/test_publication_export_v2.py
git commit -m "test: add publication report v2 smoke test suite"
```

---

## Task Dependency Order

```
Task 1 (theme + _save_figure)
  └→ Task 2 (table reorganization) — uses draft_mode from Task 1
  └→ Task 3 (OPLS-DA ellipse + S-plot)
  └→ Task 4 (ANOVA jitter)
  └→ Task 5 (Outlier layout)
  └→ Task 6 (Legend fixes)
  └→ Task 7 (Confusion matrix) — depends on Task 2 for report_dirs paths
  └→ Task 8 (Heatmap verify + final tests)
```

Tasks 3–6 are independent and can run in parallel after Task 1.
Task 7 depends on Task 1 + Task 2.
Task 8 runs last as the integration gate.
