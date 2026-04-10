"""Shared helpers for GUI layout and interaction tests."""

from __future__ import annotations

import gc

from PySide6.QtCore import QCoreApplication, QEvent, QPoint
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

import pandas as pd

from core.app_config import load_yaml_config
from gui.main_window import MainWindow


def widget_center_in_ancestor(widget, ancestor) -> QPoint:
    return widget.mapTo(ancestor, widget.rect().center())


def sample_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "F1": [1.0, 2.0],
            "F2": [3.0, 4.0],
        },
        index=pd.Index(["S1", "S2"], name="Sample"),
    )


def sample_labels(matrix: pd.DataFrame) -> pd.Series:
    return pd.Series(["Exposure", "Control"], index=matrix.index, name="Group")


def sample_info() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Sample": ["S1", "S2"],
            "NormalizationFactor": [1.1, 0.9],
        }
    )


def configure_window_for_phase7_case(
    window: MainWindow,
    qapp,
    *,
    locale: str,
    size: tuple[int, int],
    font_delta: int,
    log_visible: bool,
) -> object:
    original_font = qapp.font()
    adjusted_font = qapp.font()
    adjusted_font.setPointSize(max(1, original_font.pointSize() + font_delta))
    qapp.setFont(adjusted_font)
    try:
        if locale != "en":
            window.switch_language(locale)
        window.resize(*size)
        window._log_dock.setVisible(log_visible)
        window.show()
        qapp.processEvents()
    except Exception:
        qapp.setFont(original_font)
        raise
    return original_font


def restore_window_font(qapp, original_font) -> None:
    qapp.setFont(original_font)
    qapp.processEvents()


def close_window(window: QWidget, qapp: QApplication) -> None:
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
    qapp.processEvents()
    gc.collect()


def assert_widget_center_inside(widget, ancestor) -> None:
    center = widget_center_in_ancestor(widget, ancestor)
    assert ancestor.rect().contains(center), (
        widget.objectName() or widget.text() or type(widget).__name__
    )


def apply_phase7_preset_state(window: MainWindow, preset_state: str) -> None:
    if preset_state == "none":
        return

    if preset_state == "builtin":
        preset = next(
            preset
            for preset in window._builtin_preset_refs
            if preset.preset_id == "tissue_knn_rsd050_marker_verify"
        )
        window._load_preset_reference(preset)
        return

    if preset_state == "pending":
        config = load_yaml_config(
            {
                "pipeline": {
                    "row_norm": "SpecNorm",
                    "transform": "LogNorm",
                    "missing_thresh": 0.35,
                },
                "spec_norm": {
                    "factor_column": "NormalizationFactor",
                },
                "legacy_bundle": {
                    "note": "keep for ignored summary",
                },
            },
            require_required_sections=False,
        )
        window._load_preset_config(config, "C:/tmp/phase7_pending.yaml")
        return

    raise ValueError(f"Unsupported preset state: {preset_state}")


def load_phase7_data(window: MainWindow) -> None:
    matrix = sample_matrix()
    window.set_data(
        matrix,
        sample_labels(matrix),
        sample_col="Sample",
        group_col="Group",
        sample_info=sample_info(),
    )


def assert_scroll_reaches_widget(scroll_area: QScrollArea, widget, qapp) -> None:
    scroll_area.verticalScrollBar().setValue(0)
    qapp.processEvents()
    scroll_area.ensureWidgetVisible(widget)
    qapp.processEvents()
    center = widget_center_in_ancestor(widget, scroll_area.viewport())
    assert scroll_area.viewport().rect().contains(
        center
    ), widget.objectName() or widget.text()
