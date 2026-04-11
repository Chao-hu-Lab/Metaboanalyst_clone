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
