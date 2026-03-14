"""Verify all visualization functions accept the theme parameter."""

from __future__ import annotations

import inspect

import pytest

import visualization


_PLOT_FUNCTIONS = [
    (name, obj)
    for name, obj in vars(visualization).items()
    if callable(obj) and name.startswith("plot_")
]


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[name for name, _ in _PLOT_FUNCTIONS])
def test_function_accepts_theme(name, func):
    """Every plot function should accept a ``theme`` keyword argument."""
    sig = inspect.signature(func)
    assert "theme" in sig.parameters, f"{name}() is missing the 'theme' parameter"


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[name for name, _ in _PLOT_FUNCTIONS])
def test_theme_default_is_light(name, func):
    """Theme parameter should default to ``light`` across the package."""
    sig = inspect.signature(func)
    param = sig.parameters.get("theme")
    assert param is not None, f"{name}() is missing the 'theme' parameter"
    assert param.default == "light", f"{name}() theme default is {param.default!r}, expected 'light'"
