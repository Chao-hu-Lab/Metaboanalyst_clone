"""Shared pytest fixtures for GUI-related tests."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import DefaultDict

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("METABO_N_JOBS", "1")  # single-process in test environment

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYTEST_BUILD_DIR = _REPO_ROOT / "build" / "pytest"
_TMP_FIXTURE_ROOT = _PYTEST_BUILD_DIR / "tmp-fixtures"


def _sanitize_tmp_name(name: str) -> str:
    """Return a filesystem-safe temp directory fragment."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return sanitized or "tmp"


class RepoTmpPathFactory:
    """Create repo-local temporary directories without pytest's temp machinery."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._counters: DefaultDict[str, int] = defaultdict(int)

    def getbasetemp(self) -> Path:
        """Return the root directory used for all temp fixtures in this session."""
        return self._base_dir

    def mktemp(self, basename: str, numbered: bool = True) -> Path:
        """Create a unique temporary directory under the repo-local base dir."""
        safe_name = _sanitize_tmp_name(basename)

        if not numbered:
            path = self._base_dir / safe_name
            path.mkdir(parents=True, exist_ok=False)
            return path

        while True:
            index = self._counters[safe_name]
            self._counters[safe_name] += 1
            path = self._base_dir / f"{safe_name}_{index}"
            if not path.exists():
                path.mkdir(parents=True, exist_ok=False)
                return path


@pytest.fixture(scope="session")
def tmp_path_factory() -> RepoTmpPathFactory:
    """Provide repo-local tmp dirs on Windows without relying on pytest internals."""
    session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    session_dir = _TMP_FIXTURE_ROOT / f"{session_name}_{os.getpid()}"
    session_dir.mkdir(parents=True, exist_ok=False)
    return RepoTmpPathFactory(session_dir)


@pytest.fixture
def tmp_path(
    request: pytest.FixtureRequest, tmp_path_factory: RepoTmpPathFactory
) -> Path:
    """Return a unique repo-local temp directory for each test."""
    return tmp_path_factory.mktemp(request.node.name)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Return a single QApplication instance for the full test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
