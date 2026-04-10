"""
tests/test_visualization_theme.py — Unit tests for the theme system.

Validates color palette structure, format, and apply_publication_style()
without requiring a display (uses matplotlib's Agg backend).
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, safe in CI

import pytest
import matplotlib.pyplot as plt

from visualization.theme import COLORS, apply_publication_style, get_group_colors

pytestmark = [pytest.mark.pr_smoke]


# ---------------------------------------------------------------------------
# COLORS dict structure
# ---------------------------------------------------------------------------

class TestColorsStructure:
    def test_all_themes_present(self):
        assert set(COLORS.keys()) == {"light", "dark", "colorblind"}

    def test_each_theme_has_required_keys(self):
        for theme_name, config in COLORS.items():
            assert "background" in config, f"{theme_name} missing 'background'"
            assert "text" in config, f"{theme_name} missing 'text'"
            assert "grid" in config, f"{theme_name} missing 'grid'"
            assert "groups" in config, f"{theme_name} missing 'groups'"

    def test_hex_format_background(self):
        for theme_name, config in COLORS.items():
            assert config["background"].startswith("#"), \
                f"{theme_name} background not hex"
            assert len(config["background"]) == 7, \
                f"{theme_name} background hex wrong length"

    def test_hex_format_all_group_colors(self):
        for theme_name, config in COLORS.items():
            for color in config["groups"]:
                assert color.startswith("#"), \
                    f"{theme_name} group color '{color}' not hex"
                assert len(color) == 7, \
                    f"{theme_name} group color '{color}' wrong length"

    def test_colorblind_is_okabe_ito_7_colors(self):
        """Okabe-Ito standard palette has exactly 7 colors."""
        assert len(COLORS["colorblind"]["groups"]) == 7

    def test_light_has_8_group_colors(self):
        assert len(COLORS["light"]["groups"]) == 8

    def test_light_dark_text_contrast(self):
        """Light and dark themes must have different text/background combos."""
        light = COLORS["light"]
        dark = COLORS["dark"]
        assert light["text"] != dark["text"]
        assert light["background"] != dark["background"]

    def test_dark_text_not_background(self):
        dark = COLORS["dark"]
        assert dark["text"] != dark["background"]


# ---------------------------------------------------------------------------
# get_group_colors()
# ---------------------------------------------------------------------------

class TestGetGroupColors:
    def test_returns_list(self):
        result = get_group_colors("light", 3)
        assert isinstance(result, list)

    def test_correct_length(self):
        for n in [1, 3, 5, 8]:
            colors = get_group_colors("light", n)
            assert len(colors) == n, f"Expected {n} colors, got {len(colors)}"

    def test_none_returns_full_palette(self):
        colors = get_group_colors("light", None)
        assert len(colors) == len(COLORS["light"]["groups"])

    def test_cycles_when_exceeds_palette(self):
        """If more groups than palette colors, should cycle (not error)."""
        colors = get_group_colors("light", 20)
        assert len(colors) == 20
        # First color should repeat at offset palette_len
        palette_len = len(COLORS["light"]["groups"])
        assert colors[0] == colors[palette_len]

    def test_colorblind_theme(self):
        colors = get_group_colors("colorblind", 7)
        assert len(colors) == 7
        assert colors == COLORS["colorblind"]["groups"]

    def test_dark_theme(self):
        colors = get_group_colors("dark", 3)
        assert len(colors) == 3
        assert all(c.startswith("#") for c in colors)

    def test_unknown_theme_falls_back_to_light(self):
        """Unknown theme should not raise — falls back to light."""
        colors = get_group_colors("nonexistent_theme", 3)
        assert len(colors) == 3


# ---------------------------------------------------------------------------
# apply_publication_style()
# ---------------------------------------------------------------------------

class TestApplyPublicationStyle:
    def setup_method(self):
        """Reset rcParams before each test."""
        plt.rcdefaults()

    def test_light_sets_white_background(self):
        apply_publication_style("light")
        assert plt.rcParams["figure.facecolor"] == "#FFFFFF"
        assert plt.rcParams["axes.facecolor"] == "#FFFFFF"

    def test_dark_sets_dark_background(self):
        apply_publication_style("dark")
        assert plt.rcParams["figure.facecolor"] == "#1E1E1E"

    def test_colorblind_sets_white_background(self):
        apply_publication_style("colorblind")
        assert plt.rcParams["figure.facecolor"] == "#FFFFFF"

    def test_title_size_14(self):
        apply_publication_style("light")
        assert plt.rcParams["axes.titlesize"] == 14

    def test_label_size_12(self):
        apply_publication_style("light")
        assert plt.rcParams["axes.labelsize"] == 12

    def test_legend_no_frame(self):
        apply_publication_style("light")
        assert plt.rcParams["legend.frameon"] is False

    def test_top_right_spines_removed(self):
        apply_publication_style("light")
        assert plt.rcParams["axes.spines.top"] is False
        assert plt.rcParams["axes.spines.right"] is False

    def test_left_bottom_spines_present(self):
        apply_publication_style("light")
        assert plt.rcParams["axes.spines.left"] is True
        assert plt.rcParams["axes.spines.bottom"] is True

    def test_savefig_dpi_300(self):
        apply_publication_style("light")
        assert plt.rcParams["savefig.dpi"] == 300

    def test_unknown_theme_does_not_raise(self):
        """Should silently fall back to light theme."""
        apply_publication_style("unknown_theme")
        assert plt.rcParams["figure.facecolor"] == "#FFFFFF"
