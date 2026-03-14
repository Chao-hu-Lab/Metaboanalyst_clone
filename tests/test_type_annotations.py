"""Verify return type annotations on all visualization plot functions."""

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
def test_has_return_annotation(name, func):
    """Every plot function should have a return type annotation."""
    sig = inspect.signature(func)
    assert sig.return_annotation is not inspect.Signature.empty, (
        f"{name}() is missing a return type annotation"
    )


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[name for name, _ in _PLOT_FUNCTIONS])
def test_fig_parameter_typed_when_present(name, func):
    """Any ``fig`` parameter should include a type annotation."""
    sig = inspect.signature(func)
    if "fig" in sig.parameters:
        param = sig.parameters["fig"]
        assert param.annotation is not inspect.Signature.empty, (
            f"{name}() 'fig' parameter is missing a type annotation"
        )
