"""Shared helpers for GUI widget state binding."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QAbstractButton, QComboBox, QDoubleSpinBox, QSpinBox, QWidget


@dataclass(slots=True)
class ApplyStateResult:
    """Collect non-fatal binding outcomes while applying GUI state."""

    unsupported_paths: list[str] = field(default_factory=list)

    def extend(self, other: "ApplyStateResult") -> None:
        self.unsupported_paths.extend(other.unsupported_paths)


@contextmanager
def blocked(widget: QWidget) -> Iterator[None]:
    """Temporarily block Qt signals on a widget."""
    blocker = QSignalBlocker(widget)
    try:
        yield
    finally:
        del blocker


def apply_combo_data(combo: QComboBox, value: object, path: str) -> ApplyStateResult:
    """Apply combo-box value, falling back quietly and reporting unsupported data."""
    result = ApplyStateResult()
    if value is None:
        return result

    index = combo.findData(value)
    if index < 0:
        index = combo.findData(str(value))
    if index < 0:
        index = combo.findText(str(value))
    if index < 0:
        result.unsupported_paths.append(path)
        return result

    with blocked(combo):
        combo.setCurrentIndex(index)
    return result


def apply_spin_value(spin: QSpinBox | QDoubleSpinBox, value: int | float) -> None:
    """Apply spin-box value without emitting change signals."""
    with blocked(spin):
        spin.setValue(value)


def apply_checked(button: QAbstractButton, value: bool) -> None:
    """Apply checkable widget value without emitting change signals."""
    with blocked(button):
        button.setChecked(value)
