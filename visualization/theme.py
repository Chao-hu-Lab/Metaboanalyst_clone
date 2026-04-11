"""
visualization/theme.py — Publication-grade matplotlib theme system.

Provides 3 color schemes (Light, Dark, Colorblind-friendly) following
Nature Publishing Group standards and Okabe-Ito accessibility guidelines.

Corresponds to Phase 1 of the visualization design system plan
(docs/plans/2026-03-13-visualization-design-system.md).
"""

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Color palette definitions
# ---------------------------------------------------------------------------

COLORS: dict = {
    "light": {
        "background": "#FFFFFF",
        "text": "#333333",
        "grid": "#E0E0E0",
        "axes_line": "#333333",
        "groups": [
            "#E64B35",  # coral red    (disease/exposure group)
            "#4DBBD5",  # lake blue    (control group)
            "#00A087",  # jade green
            "#3C5488",  # navy blue
            "#F39B7F",  # soft orange
            "#8491B4",  # grey-blue
            "#91D1C2",  # mint green
            "#DC0000",  # accent red   (significant difference)
        ],
    },
    "dark": {
        "background": "#1E1E1E",
        "text": "#E0E0E0",
        "grid": "#424242",
        "axes_line": "#E0E0E0",
        "groups": [
            "#FF6B6B",  # bright red
            "#4ECDC4",  # neon cyan
            "#C7F464",  # lime green
            "#FFE66D",  # warm yellow
            "#FF9FF3",  # pink-purple
            "#54A0FF",  # sky blue
        ],
    },
    "colorblind": {
        # Okabe-Ito palette — universally distinguishable by color-blind viewers
        # Reference: https://jfly.uni-koeln.de/color/
        "background": "#FFFFFF",
        "text": "#333333",
        "grid": "#E0E0E0",
        "axes_line": "#333333",
        "groups": [
            "#E69F00",  # orange
            "#56B4E9",  # sky blue
            "#009E73",  # blue-green
            "#F0E442",  # yellow
            "#0072B2",  # blue
            "#D55E00",  # vermillion
            "#CC79A7",  # reddish-purple
        ],
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_publication_style(theme: str = "light") -> None:
    """
    Apply publication-grade matplotlib rcParams for the given theme.

    Sets font sizes, spine widths, legend style, and background colors
    following Nature Publishing Group figure guidelines.

    Parameters
    ----------
    theme : str
        One of "light", "dark", or "colorblind". Defaults to "light".

    Notes
    -----
    This modifies global ``plt.rcParams``. In a GUI with multiple canvases,
    call this before creating each figure, or use ``plt.style.context()`` for
    isolated scoping (planned for Phase 2 ThemeManager).
    """
    config = COLORS.get(theme, COLORS["light"])

    plt.rcParams.update(
        {
            # --- Font ---
            "font.family": "DejaVu Sans",
            # --- Title & labels ---
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "axes.labelweight": "bold",
            # --- Tick labels ---
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            # --- Spines (Tufte minimal-ink principle) ---
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.linewidth": 1.5,
            # --- Grid ---
            "axes.grid": False,
            # --- Legend ---
            "legend.frameon": False,
            "legend.fontsize": 10,
            # --- Output quality ---
            "figure.dpi": 150,
            "savefig.dpi": 300,
            # --- Colors ---
            "axes.facecolor": config["background"],
            "figure.facecolor": config["background"],
            "text.color": config["text"],
            "axes.edgecolor": config["axes_line"],
            "xtick.color": config["text"],
            "ytick.color": config["text"],
        }
    )


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


def get_group_colors(theme: str = "light", n_groups: int | None = None) -> list[str]:
    """
    Return hex color list for the given theme and number of groups.

    Parameters
    ----------
    theme : str
        One of "light", "dark", or "colorblind".
    n_groups : int or None
        Number of colors needed. If None, returns the full palette.
        If n_groups exceeds the palette length, colors are cycled.

    Returns
    -------
    list[str]
        List of hex color strings (e.g., ["#E64B35", "#4DBBD5", ...]).

    Examples
    --------
    >>> colors = get_group_colors("light", 3)
    >>> len(colors)
    3
    """
    palette = COLORS.get(theme, COLORS["light"])["groups"]
    if n_groups is None:
        return list(palette)

    # Cycle palette if more groups than colors
    return [palette[i % len(palette)] for i in range(n_groups)]
