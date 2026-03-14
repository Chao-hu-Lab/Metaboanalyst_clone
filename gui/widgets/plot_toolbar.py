"""Custom plot toolbar used by the Phase 2 visualization UI."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QToolBar

logger = logging.getLogger(__name__)


class PlotToolbar(QToolBar):
    """A compact toolbar for exporting and interacting with plots."""

    export_requested = Signal(str)
    reset_requested = Signal()
    zoom_requested = Signal(bool)

    def __init__(self, mpl_widget, theme_manager=None, parent=None):
        super().__init__("Plot Tools", parent or mpl_widget)
        self.setObjectName("PlotToolbar")
        self.setMovable(False)

        self.mpl_widget = mpl_widget
        self.theme_manager = theme_manager
        self.zoom_mode_enabled = False

        self.theme_label = None
        self.theme_value_label = None
        self.zoom_button = None

        self._init_buttons()
        if self.theme_manager is not None:
            self.theme_manager.register_callback(self._on_theme_changed)
            self.destroyed.connect(lambda *_: self.theme_manager.unregister_callback(self._on_theme_changed))

    def _init_buttons(self) -> None:
        self.addWidget(self._make_label("Export:"))
        self.addWidget(self._make_button("PNG", "Export as PNG (300 dpi)", self._export_png, "plot_png_button"))
        self.addWidget(self._make_button("SVG", "Export as SVG", self._export_svg, "plot_svg_button"))
        self.addWidget(self._make_button("PDF", "Export as PDF", self._export_pdf, "plot_pdf_button"))
        self.addSeparator()

        self.addWidget(self._make_label("Tools:"))
        self.zoom_button = self._make_button(
            "Zoom",
            "Toggle interactive zoom mode",
            self._toggle_zoom,
            "plot_zoom_button",
            checkable=True,
        )
        self.addWidget(self.zoom_button)
        self.addWidget(self._make_button("Reset", "Reset plot view", self._reset_view, "plot_reset_button"))

        if self.theme_manager is not None:
            self.addSeparator()
            self.theme_label = self._make_label("Theme:")
            self.theme_value_label = QLabel(self.theme_manager.current_theme.capitalize())
            self.theme_value_label.setObjectName("plot_theme_value")
            self.addWidget(self.theme_label)
            self.addWidget(self.theme_value_label)

    def _make_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 600; background: transparent;")
        return label

    def _make_button(self, text: str, tooltip: str, slot, object_name: str, checkable: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setMaximumWidth(82)
        if checkable:
            button.toggled.connect(slot)
        else:
            button.clicked.connect(slot)
        return button

    def _export_png(self) -> None:
        self._export_figure("png", "plot.png", "PNG Files (*.png)")

    def _export_svg(self) -> None:
        self._export_figure("svg", "plot.svg", "SVG Files (*.svg)")

    def _export_pdf(self) -> None:
        self._export_figure("pdf", "plot.pdf", "PDF Files (*.pdf)")

    def _export_figure(self, fmt: str, default_name: str, filter_text: str) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, f"Save as {fmt.upper()}", default_name, filter_text)
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() != f".{fmt}":
            path = path.with_suffix(f".{fmt}")

        save_kwargs = {
            "bbox_inches": "tight",
            "edgecolor": "none",
            "facecolor": self.mpl_widget.figure.get_facecolor(),
        }
        if fmt == "png":
            save_kwargs["dpi"] = 300
        else:
            save_kwargs["format"] = fmt

        self.mpl_widget.figure.savefig(path, **save_kwargs)
        self.export_requested.emit(fmt)

    def _toggle_zoom(self, enabled: bool) -> None:
        self.zoom_mode_enabled = enabled
        navigation_toolbar = getattr(self.mpl_widget, "navigation_toolbar", None)
        if navigation_toolbar is not None:
            navigation_toolbar.zoom()
        self.zoom_requested.emit(enabled)

    def _reset_view(self) -> None:
        navigation_toolbar = getattr(self.mpl_widget, "navigation_toolbar", None)
        if navigation_toolbar is not None:
            try:
                navigation_toolbar.home()
            except Exception:
                logger.debug("Navigation toolbar home() was not available", exc_info=True)

        for axes in self.mpl_widget.figure.get_axes():
            try:
                axes.relim()
                axes.autoscale_view()
            except Exception:
                logger.debug("Axes autoscale failed during reset", exc_info=True)

        self.mpl_widget.draw()
        if self.zoom_button is not None and self.zoom_button.isChecked():
            self.zoom_button.setChecked(False)
        self.zoom_mode_enabled = False
        self.reset_requested.emit()

    def _on_theme_changed(self, theme_name: str) -> None:
        if self.theme_value_label is not None:
            self.theme_value_label.setText(theme_name.capitalize())
