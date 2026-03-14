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

_PLOTLY_ONLY_FUNCTIONS = {
    "plot_pca_3d",
    "plot_volcano_interactive",
    "plot_roc_interactive",
    "plot_correlation_network_interactive",
}


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


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[name for name, _ in _PLOT_FUNCTIONS])
def test_theme_parameter_precedes_fig_when_present(name, func):
    """Theme should appear before ``fig`` for a consistent public API."""
    sig = inspect.signature(func)
    params = list(sig.parameters)
    if "fig" in params:
        assert params.index("theme") < params.index("fig"), (
            f"{name}() should place 'theme' before 'fig' in the signature"
        )


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[name for name, _ in _PLOT_FUNCTIONS])
def test_theme_parameter_is_actually_used(name, func):
    """Theme-aware plot helpers should apply the requested theme in their implementation."""
    if name in _PLOTLY_ONLY_FUNCTIONS:
        return

    source = inspect.getsource(func)
    assert "apply_publication_style(theme)" in source, (
        f"{name}() accepts 'theme' but does not apply the publication style"
    )
