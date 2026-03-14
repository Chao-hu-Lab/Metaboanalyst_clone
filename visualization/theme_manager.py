"""Centralized visualization theme state management."""

from __future__ import annotations

import logging
from typing import Callable

from visualization.theme import COLORS, apply_publication_style, get_group_colors

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manage the active visualization theme and notify subscribers."""

    SUPPORTED_THEMES = ["light", "dark", "colorblind"]

    def __init__(self, default_theme: str = "light"):
        """Initialize the theme manager."""
        if default_theme not in self.SUPPORTED_THEMES:
            raise ValueError(f"Invalid theme: {default_theme}")

        self.current_theme = default_theme
        self.callbacks: list[Callable[[str], None]] = []
        apply_publication_style(default_theme)

    def set_theme(self, theme_name: str) -> None:
        """Switch to a new theme and notify registered callbacks."""
        if theme_name not in self.SUPPORTED_THEMES:
            raise ValueError(f"Invalid theme: {theme_name}")
        if theme_name == self.current_theme:
            return

        self.current_theme = theme_name
        apply_publication_style(theme_name)

        for callback in list(self.callbacks):
            try:
                callback(theme_name)
            except Exception:
                logger.exception("Theme callback failed for theme '%s'", theme_name)

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback that receives the new theme name."""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str], None]) -> None:
        """Remove a previously-registered callback if it exists."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def get_colors(self, n_groups: int | None = None) -> list[str]:
        """Return group colors for the current theme."""
        return get_group_colors(self.current_theme, n_groups)

    def get_theme_config(self) -> dict:
        """Return the full theme configuration dictionary."""
        return COLORS[self.current_theme]

    def get_supported_themes(self) -> list[str]:
        """Return a copy of the supported theme names."""
        return self.SUPPORTED_THEMES.copy()
