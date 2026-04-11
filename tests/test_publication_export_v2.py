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
    def test_sets_arial_font(self):
        from visualization.theme import apply_publication_export_style

        apply_publication_export_style("light")
        assert "Arial" in plt.rcParams["font.family"]

    def test_sets_300_dpi(self):
        from visualization.theme import apply_publication_export_style

        apply_publication_export_style("light")
        assert plt.rcParams["savefig.dpi"] == 300
        assert plt.rcParams["figure.dpi"] == 300

    def test_inherits_base_style(self):
        from visualization.theme import apply_publication_export_style

        apply_publication_export_style("light")
        assert plt.rcParams["axes.spines.top"] is False
        assert plt.rcParams["axes.spines.right"] is False
        assert plt.rcParams["legend.frameon"] is False


class TestSaveFigureDualOutput:
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


class TestOplsdaEllipseNoFill:
    def test_ellipse_has_no_facecolor(self):
        from visualization.oplsda_plot import _confidence_ellipse

        fig, ax = plt.subplots()
        x = np.random.randn(20)
        y = np.random.randn(20)
        _confidence_ellipse(ax, x, y, color="#E64B35", fill_color="#E64B35")
        patches = [p for p in ax.patches if hasattr(p, "get_facecolor")]
        assert len(patches) == 1
        fc = patches[0].get_facecolor()
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
        assert ls != (0, None)  # not solid
        plt.close(fig)


class TestAnovaBoxplotJitter:
    def test_scatter_points_present(self):
        from visualization.anova_plot import _draw_r_style_boxplot
        from visualization.theme import COLORS

        fig, ax = plt.subplots()
        config = COLORS["light"]
        data = [
            np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            np.array([2.0, 3.0, 4.0, 5.0, 6.0]),
        ]
        _draw_r_style_boxplot(ax, data, ["A", "B"], ["#E64B35", "#4DBBD5"], config)

        scatter_collections = [
            c for c in ax.collections if type(c).__name__ == "PathCollection"
        ]
        assert len(scatter_collections) >= 2, (
            "Expected jittered scatter overlays for each group"
        )
        plt.close(fig)


class TestOutlierPlotLayout:
    def test_outlier_score_figsize_2_to_1(self):
        from unittest.mock import MagicMock

        from analysis.outlier import OutlierResult
        from visualization.outlier_plot import plot_outlier_score

        n = 10
        rng = np.random.default_rng(42)
        result = OutlierResult(
            scores=rng.standard_normal((n, 2)),
            t2_values=rng.random(n) * 10,
            t2_threshold=6.0,
            outlier_mask_t2=np.array([False] * 9 + [True]),
            dmodx=rng.random(n),
            dmodx_threshold=2.0,
            outlier_mask_dmodx=np.array([False] * 9 + [True]),
            explained_variance=np.array([0.4, 0.3]),
            sample_names=[f"S{i}" for i in range(n)],
            pca_model=MagicMock(),
        )
        fig = plot_outlier_score(result)
        w, h = fig.get_size_inches()
        ratio = w / h
        assert 2.0 <= ratio <= 2.5, f"Expected ~2:1 ratio, got {ratio:.2f}"
        plt.close(fig)


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


class TestConfusionMatrixVmax:
    def test_accepts_vmax_parameter(self):
        import inspect

        from visualization.rf_plot import plot_confusion_matrix

        sig = inspect.signature(plot_confusion_matrix)
        assert "vmax" in sig.parameters, (
            "plot_confusion_matrix should accept vmax parameter"
        )
