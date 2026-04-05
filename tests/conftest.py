"""Shared pytest fixtures for GUI-related tests."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass
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


@dataclass(slots=True)
class _GuiArtifactTarget:
    widget: object
    label: str


class GuiArtifactRecorder:
    """Capture widget screenshots when a GUI test fails."""

    def __init__(self, artifact_dir: Path, test_name: str) -> None:
        self._artifact_dir = artifact_dir
        self._test_name = _sanitize_tmp_name(test_name)
        self._targets: list[_GuiArtifactTarget] = []

    def watch(self, widget: object, label: str) -> None:
        """Register a widget to capture if the test fails."""
        self._targets.append(_GuiArtifactTarget(widget=widget, label=label))

    def save_failure_artifacts(self) -> list[Path]:
        """Save screenshots for every registered widget."""
        saved_paths: list[Path] = []
        for target in self._targets:
            if not hasattr(target.widget, "grab"):
                continue
            path = self._artifact_dir / (
                f"{self._test_name}_{_sanitize_tmp_name(target.label)}.png"
            )
            pixmap = target.widget.grab()
            if pixmap.save(str(path), "PNG"):
                saved_paths.append(path)
        return saved_paths


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


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    """Expose per-phase test results to fixtures during teardown."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def gui_artifact_recorder(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> GuiArtifactRecorder:
    """Record GUI widgets and save screenshots only when the test fails."""
    recorder = GuiArtifactRecorder(tmp_path, request.node.name)
    yield recorder

    report = getattr(request.node, "rep_call", None)
    if report is None or not report.failed:
        return

    saved_paths = recorder.save_failure_artifacts()
    if saved_paths:
        print("\nSaved GUI artifacts:")
        for path in saved_paths:
            print(f" - {path}")
