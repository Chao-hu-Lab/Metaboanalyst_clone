"""Shared pytest fixtures for GUI-related tests."""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("METABO_N_JOBS", "1")  # single-process in test environment


@pytest.fixture(scope="session")
def qapp():
    """Return a single QApplication instance for the full test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
