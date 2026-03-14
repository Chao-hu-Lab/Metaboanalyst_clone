"""Unit tests for the Phase 2 theme manager."""

from __future__ import annotations

import pytest

from visualization.theme_manager import ThemeManager


def test_theme_manager_init():
    tm = ThemeManager("light")
    assert tm.current_theme == "light"


def test_theme_manager_invalid_theme():
    with pytest.raises(ValueError):
        ThemeManager("invalid_theme")


def test_set_theme():
    tm = ThemeManager()
    tm.set_theme("dark")
    assert tm.current_theme == "dark"

    tm.set_theme("colorblind")
    assert tm.current_theme == "colorblind"


def test_callback_triggered():
    tm = ThemeManager()
    called = []

    def callback(theme_name):
        called.append(theme_name)

    tm.register_callback(callback)
    tm.set_theme("dark")
    tm.set_theme("light")

    assert called == ["dark", "light"]


def test_multiple_callbacks():
    tm = ThemeManager()
    called1 = []
    called2 = []

    def callback1(theme_name):
        called1.append(theme_name)

    def callback2(theme_name):
        called2.append(theme_name)

    tm.register_callback(callback1)
    tm.register_callback(callback2)
    tm.set_theme("dark")

    assert called1 == ["dark"]
    assert called2 == ["dark"]


def test_get_colors():
    tm = ThemeManager("light")
    colors = tm.get_colors(3)
    assert len(colors) == 3
    assert all(isinstance(c, str) for c in colors)


def test_get_theme_config():
    tm = ThemeManager("light")
    config = tm.get_theme_config()

    assert "background" in config
    assert "text" in config
    assert "grid" in config
    assert "groups" in config


def test_supported_themes():
    tm = ThemeManager()
    themes = tm.get_supported_themes()

    assert "light" in themes
    assert "dark" in themes
    assert "colorblind" in themes
    assert len(themes) == 3
