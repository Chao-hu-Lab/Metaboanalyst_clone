"""Responsive visualization workspace with a theme-aware control dock."""

from __future__ import annotations

import logging

import pandas as pd
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.mpl_canvas import MatplotlibCanvas
from visualization.theme import apply_publication_style

logger = logging.getLogger(__name__)


class VisualTab(QWidget):
    """Visualization tab with a docked parameter panel and live redraws."""

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.theme_manager = main_window.theme_manager
        self._last_render_error = None

        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(300)
        self.update_timer.timeout.connect(self.redraw_plot)

        self.theme_manager.register_callback(self.on_theme_changed)
        self.destroyed.connect(lambda *_: self.theme_manager.unregister_callback(self.on_theme_changed))
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.control_dock = self._create_control_dock()
        layout.addWidget(self.control_dock)

        self.content_frame = QFrame()
        self.content_frame.setFrameShape(QFrame.Shape.NoFrame)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.header_label = QLabel("Visualization Preview")
        self.header_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        content_layout.addWidget(self.header_label)

        self.mpl_canvas = MatplotlibCanvas(
            self,
            figsize=(9, 6),
            theme_manager=self.theme_manager,
            use_default_toolbar=False,
            use_plot_toolbar=True,
        )
        content_layout.addWidget(self.mpl_canvas, stretch=1)
        layout.addWidget(self.content_frame, stretch=1)

        self._apply_control_visibility()
        self.redraw_plot()

    def _create_control_dock(self) -> QDockWidget:
        dock = QDockWidget("Parameters", self)
        dock.setObjectName("VisualControlDock")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setMinimumWidth(280)
        dock.setMaximumWidth(320)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(10)

        self.general_group = QGroupBox("General")
        general_layout = QVBoxLayout(self.general_group)
        general_layout.addWidget(QLabel("Chart Type"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.setObjectName("chart_type_combo")
        self.chart_type_combo.addItem("Boxplot", "boxplot")
        self.chart_type_combo.addItem("Density Plot", "density")
        self.chart_type_combo.addItem("Heatmap", "heatmap")
        self.chart_type_combo.addItem("PCA Score", "pca")
        self.chart_type_combo.addItem("Volcano Plot", "volcano")
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        general_layout.addWidget(self.chart_type_combo)

        general_layout.addWidget(QLabel("Scale Factor"))
        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setObjectName("scale_spinbox")
        self.scale_spinbox.setRange(25, 150)
        self.scale_spinbox.setSingleStep(5)
        self.scale_spinbox.setValue(100)
        self.scale_spinbox.valueChanged.connect(self._on_parameter_changed)
        general_layout.addWidget(self.scale_spinbox)
        panel_layout.addWidget(self.general_group)

        self.boxplot_group = QGroupBox("Boxplot")
        boxplot_layout = QVBoxLayout(self.boxplot_group)
        boxplot_layout.addWidget(QLabel("Mode"))
        self.box_mode_combo = QComboBox()
        self.box_mode_combo.setObjectName("box_mode_combo")
        self.box_mode_combo.addItem("By Group", "group")
        self.box_mode_combo.addItem("By Sample", "sample")
        self.box_mode_combo.currentIndexChanged.connect(self._on_parameter_changed)
        boxplot_layout.addWidget(self.box_mode_combo)
        panel_layout.addWidget(self.boxplot_group)

        self.heatmap_group = QGroupBox("Heatmap")
        heatmap_layout = QVBoxLayout(self.heatmap_group)
        heatmap_layout.addWidget(QLabel("Linkage"))
        self.hm_method = QComboBox()
        self.hm_method.addItem("Ward", "ward")
        self.hm_method.addItem("Complete", "complete")
        self.hm_method.addItem("Average", "average")
        self.hm_method.addItem("Single", "single")
        self.hm_method.currentIndexChanged.connect(self._on_parameter_changed)
        heatmap_layout.addWidget(self.hm_method)

        heatmap_layout.addWidget(QLabel("Distance Metric"))
        self.hm_metric = QComboBox()
        self.hm_metric.addItem("Euclidean", "euclidean")
        self.hm_metric.addItem("Correlation", "correlation")
        self.hm_metric.addItem("Cosine", "cosine")
        self.hm_metric.currentIndexChanged.connect(self._on_parameter_changed)
        heatmap_layout.addWidget(self.hm_metric)

        heatmap_layout.addWidget(QLabel("Scaling"))
        self.hm_scale = QComboBox()
        self.hm_scale.addItem("Row", "row")
        self.hm_scale.addItem("Column", "col")
        self.hm_scale.addItem("None", "none")
        self.hm_scale.currentIndexChanged.connect(self._on_parameter_changed)
        heatmap_layout.addWidget(self.hm_scale)

        heatmap_layout.addWidget(QLabel("Max Features"))
        self.hm_maxfeat = QSpinBox()
        self.hm_maxfeat.setRange(10, 5000)
        self.hm_maxfeat.setSingleStep(50)
        self.hm_maxfeat.setValue(500)
        self.hm_maxfeat.valueChanged.connect(self._on_parameter_changed)
        heatmap_layout.addWidget(self.hm_maxfeat)
        panel_layout.addWidget(self.heatmap_group)

        self.pca_group = QGroupBox("PCA")
        pca_layout = QVBoxLayout(self.pca_group)
        pca_layout.addWidget(QLabel("Components"))
        self.pca_ncomp = QSpinBox()
        self.pca_ncomp.setRange(2, 20)
        self.pca_ncomp.setValue(5)
        self.pca_ncomp.valueChanged.connect(self._on_parameter_changed)
        pca_layout.addWidget(self.pca_ncomp)

        pca_layout.addWidget(QLabel("PC X"))
        self.pca_pc_x = QSpinBox()
        self.pca_pc_x.setRange(1, 10)
        self.pca_pc_x.setValue(1)
        self.pca_pc_x.valueChanged.connect(self._on_parameter_changed)
        pca_layout.addWidget(self.pca_pc_x)

        pca_layout.addWidget(QLabel("PC Y"))
        self.pca_pc_y = QSpinBox()
        self.pca_pc_y.setRange(2, 10)
        self.pca_pc_y.setValue(2)
        self.pca_pc_y.valueChanged.connect(self._on_parameter_changed)
        pca_layout.addWidget(self.pca_pc_y)
        panel_layout.addWidget(self.pca_group)

        self.reset_button = QPushButton("Reset All")
        self.reset_button.setObjectName("visual_reset_button")
        self.reset_button.clicked.connect(self._reset_view)
        panel_layout.addWidget(self.reset_button)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setObjectName("visual_save_button")
        self.save_button.clicked.connect(self._save_settings)
        panel_layout.addWidget(self.save_button)

        panel_layout.addStretch(1)
        scroll.setWidget(panel)
        dock.setWidget(scroll)
        return dock

    def retranslateUi(self):
        self.control_dock.setWindowTitle(self.tr("Parameters"))
        self.header_label.setText(self.tr("Visualization Preview"))

    def _on_chart_type_changed(self) -> None:
        self._apply_control_visibility()
        self._on_parameter_changed()

    def _apply_control_visibility(self) -> None:
        chart_key = self.chart_type_combo.currentData()
        self.boxplot_group.setVisible(chart_key == "boxplot")
        self.heatmap_group.setVisible(chart_key == "heatmap")
        self.pca_group.setVisible(chart_key == "pca")

    def _on_parameter_changed(self) -> None:
        self.update_timer.stop()
        self.update_timer.start()

    def _snapshot_data(self):
        if getattr(self.mw, "current_data", None) is None:
            return None, None

        data = self.mw.current_data.copy()
        labels = getattr(self.mw, "labels", None)
        if labels is None:
            labels = pd.Series(["All"] * len(data), index=data.index)
        elif hasattr(labels, "reindex"):
            labels = labels.reindex(data.index)
        else:
            labels = pd.Series(labels, index=data.index)
        labels = labels.fillna("All").astype(str)
        return data, labels

    def _apply_scale(self, fig) -> None:
        scale_factor = self.scale_spinbox.value() / 100.0
        chart_key = self.chart_type_combo.currentData()
        base_sizes = {
            "boxplot": (8, 5),
            "density": (8, 5),
            "heatmap": (12, 8),
            "pca": (8, 6),
            "volcano": (8, 6),
        }
        width, height = base_sizes.get(chart_key, (8, 5))
        fig.set_size_inches(width * scale_factor, height * scale_factor, forward=True)

    def _show_placeholder(self, message: str) -> None:
        fig = self.mpl_canvas.figure
        config = self.theme_manager.get_theme_config()
        fig.clear()
        fig.set_facecolor(config["background"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(config["background"])
        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            wrap=True,
            color=config["text"],
            fontsize=11,
        )
        ax.set_axis_off()
        self.mpl_canvas.draw()

    def _set_rendered_figure(self, fig) -> None:
        if fig is not self.mpl_canvas.figure:
            self.mpl_canvas.set_figure(fig)
        self.mpl_canvas.draw()
        if hasattr(self.mw, "show_shared_plot"):
            self.mw.show_shared_plot(self.mpl_canvas.figure)

    def redraw_plot(self) -> None:
        apply_publication_style(self.theme_manager.current_theme)
        self._last_render_error = None

        data, labels = self._snapshot_data()
        if data is None or data.empty:
            self._show_placeholder("Import and preprocess data to preview visualizations.")
            return

        chart_key = self.chart_type_combo.currentData()
        try:
            if chart_key == "boxplot":
                fig = self._draw_boxplot(data, labels)
            elif chart_key == "density":
                fig = self._draw_density(data, labels)
            elif chart_key == "heatmap":
                fig = self._draw_heatmap(data, labels)
            elif chart_key == "pca":
                fig = self._draw_pca(data, labels)
            elif chart_key == "volcano":
                fig = self._draw_volcano()
            else:
                self._show_placeholder("Select a chart type to begin.")
                return
        except Exception as exc:
            logger.exception("VisualTab redraw failed")
            self._last_render_error = exc
            self._show_placeholder(f"Unable to render chart:\n{exc}")
            return

        self._set_rendered_figure(fig)

    def _draw_boxplot(self, data, labels):
        from visualization.boxplot import plot_group_boxplot, plot_sample_boxplot

        fig = self.mpl_canvas.figure
        plot_fn = plot_group_boxplot if self.box_mode_combo.currentData() == "group" else plot_sample_boxplot
        rendered_fig = plot_fn(data, labels, theme=self.theme_manager.current_theme, fig=fig)
        self._apply_scale(rendered_fig)
        return rendered_fig

    def _draw_density(self, data, labels):
        from visualization.density_plot import plot_density

        fig = self.mpl_canvas.figure
        rendered_fig = plot_density(
            data,
            labels,
            theme=self.theme_manager.current_theme,
            fig=fig,
        )
        self._apply_scale(rendered_fig)
        return rendered_fig

    def _draw_heatmap(self, data, labels):
        from visualization.heatmap import plot_heatmap

        scale = self.hm_scale.currentData()
        rendered_fig = plot_heatmap(
            data,
            labels,
            method=self.hm_method.currentData(),
            metric=self.hm_metric.currentData(),
            scale=None if scale == "none" else scale,
            max_features=self.hm_maxfeat.value(),
            theme=self.theme_manager.current_theme,
            fig=self.mpl_canvas.figure,
        )
        self._apply_scale(rendered_fig)
        return rendered_fig

    def _draw_pca(self, data, labels):
        from analysis.pca import run_pca
        from visualization.pca_plot import plot_pca_score

        stats_tab = getattr(self.mw, "stats_tab", None)
        pca_result = getattr(stats_tab, "_pca_result", None)
        max_pc = max(self.pca_ncomp.value(), self.pca_pc_x.value(), self.pca_pc_y.value())
        if pca_result is None or getattr(pca_result, "n_components", 0) < max_pc:
            pca_result = run_pca(data, labels, n_components=max_pc)

        rendered_fig = plot_pca_score(
            pca_result,
            pc_x=self.pca_pc_x.value() - 1,
            pc_y=self.pca_pc_y.value() - 1,
            theme=self.theme_manager.current_theme,
            fig=self.mpl_canvas.figure,
        )
        self._apply_scale(rendered_fig)
        return rendered_fig

    def _draw_volcano(self):
        from visualization.volcano_plot import plot_volcano

        stats_tab = getattr(self.mw, "stats_tab", None)
        volcano_result = getattr(stats_tab, "_volcano_result", None)
        if volcano_result is None:
            self._show_placeholder("Run volcano analysis in the Statistics tab to preview it here.")
            return self.mpl_canvas.figure

        rendered_fig = plot_volcano(
            volcano_result,
            theme=self.theme_manager.current_theme,
            fig=self.mpl_canvas.figure,
        )
        self._apply_scale(rendered_fig)
        return rendered_fig

    def on_theme_changed(self, theme_name: str) -> None:
        self.redraw_plot()

    def _reset_view(self) -> None:
        widgets = [
            self.chart_type_combo,
            self.box_mode_combo,
            self.hm_method,
            self.hm_metric,
            self.hm_scale,
            self.hm_maxfeat,
            self.scale_spinbox,
            self.pca_ncomp,
            self.pca_pc_x,
            self.pca_pc_y,
        ]
        for widget in widgets:
            widget.blockSignals(True)

        self.chart_type_combo.setCurrentIndex(0)
        self.box_mode_combo.setCurrentIndex(0)
        self.hm_method.setCurrentIndex(0)
        self.hm_metric.setCurrentIndex(0)
        self.hm_scale.setCurrentIndex(0)
        self.hm_maxfeat.setValue(500)
        self.scale_spinbox.setValue(100)
        self.pca_ncomp.setValue(5)
        self.pca_pc_x.setValue(1)
        self.pca_pc_y.setValue(2)

        for widget in widgets:
            widget.blockSignals(False)

        self._apply_control_visibility()
        self.redraw_plot()

    def _save_settings(self) -> None:
        settings = getattr(self.mw, "_settings", None)
        if settings is None:
            return

        settings.setValue("visual/chart_type", self.chart_type_combo.currentData())
        settings.setValue("visual/box_mode", self.box_mode_combo.currentData())
        settings.setValue("visual/scale_factor", self.scale_spinbox.value())
        settings.setValue("visual/hm_method", self.hm_method.currentData())
        settings.setValue("visual/hm_metric", self.hm_metric.currentData())
        settings.setValue("visual/hm_scale", self.hm_scale.currentData())
        settings.setValue("visual/hm_maxfeat", self.hm_maxfeat.value())
        settings.setValue("visual/pca_components", self.pca_ncomp.value())
        settings.setValue("visual/pca_x", self.pca_pc_x.value())
        settings.setValue("visual/pca_y", self.pca_pc_y.value())

        if hasattr(self.mw, "status_bar"):
            self.mw.status_bar.showMessage("Visualization settings saved.", 3000)
