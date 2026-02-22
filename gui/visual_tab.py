"""
Visualization tab: Boxplot / Density / Heatmap.
"""

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from matplotlib.figure import Figure

from gui.widgets.mpl_canvas import MplWidget
from gui.widgets.worker import PipelineWorker


class VisualTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._active_workers: set[PipelineWorker] = set()
        self._busy = False
        self._init_ui()

    def _init_ui(self):
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self._build_boxplot_panel(), self.tr("Boxplot"))
        self.sub_tabs.addTab(self._build_density_panel(), self.tr("Density Plot"))
        self.sub_tabs.addTab(self._build_heatmap_panel(), self.tr("Heatmap"))
        layout.addWidget(self.sub_tabs)

    def retranslateUi(self):
        current_idx = self.sub_tabs.currentIndex() if hasattr(self, "sub_tabs") else 0
        self._init_ui()
        self.sub_tabs.setCurrentIndex(min(current_idx, self.sub_tabs.count() - 1))

    def _snapshot_data(self):
        data = self.mw.current_data.copy()
        labels = self.mw.labels
        if labels is not None and hasattr(labels, "copy"):
            labels = labels.copy()
        return data, labels

    @staticmethod
    def _apply_canvas_figure(canvas_widget: MplWidget, fig: Figure):
        canvas_widget.canvas.figure = fig
        canvas_widget.canvas.axes = fig.axes[0] if fig.axes else fig.add_subplot(111)
        canvas_widget.canvas.draw()

    def _run_async(self, job_fn, on_success, error_title: str):
        if self._busy:
            self.mw.status_bar.showMessage(self.tr("Another visualization is running. Please wait."))
            return

        self._busy = True
        self.sub_tabs.setEnabled(False)
        self.mw.show_progress(True)

        worker = PipelineWorker(job_fn)
        self._active_workers.add(worker)

        def _handle_result(payload):
            try:
                on_success(payload)
            except Exception as exc:
                QMessageBox.critical(self, error_title, str(exc))

        def _handle_error(error_text: str):
            QMessageBox.critical(self, error_title, error_text)

        def _handle_finished():
            self._busy = False
            self.sub_tabs.setEnabled(True)
            self.mw.show_progress(False)
            self._active_workers.discard(worker)

        worker.signals.result.connect(_handle_result)
        worker.signals.error.connect(_handle_error)
        worker.signals.finished.connect(_handle_finished)
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Boxplot
    # ------------------------------------------------------------------

    def _build_boxplot_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Mode:")))
        self.box_mode = QComboBox()
        self.box_mode.addItem(self.tr("By Group"), "group")
        self.box_mode.addItem(self.tr("By Sample"), "sample")
        ctrl.addWidget(self.box_mode)

        btn = QPushButton(self.tr("Draw Boxplot"))
        btn.clicked.connect(self._draw_boxplot)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        self.box_canvas = MplWidget()
        layout.addWidget(self.box_canvas, stretch=1)
        return w

    def _draw_boxplot(self):
        if not self.mw.check_data_ready():
            return

        from visualization.boxplot import plot_group_boxplot, plot_sample_boxplot

        data, labels = self._snapshot_data()
        mode = self.box_mode.currentData()

        def _job():
            if mode == "group":
                fig = Figure(figsize=(8, 5), dpi=100)
                return plot_group_boxplot(data, labels, fig=fig)
            fig = Figure(figsize=(max(10, len(data) * 0.4), 5), dpi=100)
            return plot_sample_boxplot(data, labels, fig=fig)

        def _on_success(fig):
            self._apply_canvas_figure(self.box_canvas, fig)
            self.mw.show_shared_plot(self.box_canvas.figure)

        self._run_async(_job, _on_success, self.tr("Boxplot Error"))

    # ------------------------------------------------------------------
    # Density
    # ------------------------------------------------------------------

    def _build_density_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        btn = QPushButton(self.tr("Draw Density Plot"))
        btn.clicked.connect(self._draw_density)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        self.dens_canvas = MplWidget()
        layout.addWidget(self.dens_canvas, stretch=1)
        return w

    def _draw_density(self):
        if not self.mw.check_data_ready():
            return

        from visualization.density_plot import plot_density

        data, labels = self._snapshot_data()

        def _job():
            fig = Figure(figsize=(8, 5), dpi=100)
            return plot_density(data, labels, fig=fig)

        def _on_success(fig):
            self._apply_canvas_figure(self.dens_canvas, fig)
            self.mw.show_shared_plot(self.dens_canvas.figure)

        self._run_async(_job, _on_success, self.tr("Density Plot Error"))

    # ------------------------------------------------------------------
    # Heatmap
    # ------------------------------------------------------------------

    def _build_heatmap_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Linkage:")))
        self.hm_method = QComboBox()
        self.hm_method.addItem("Ward", "ward")
        self.hm_method.addItem("Complete", "complete")
        self.hm_method.addItem("Average", "average")
        self.hm_method.addItem("Single", "single")
        ctrl.addWidget(self.hm_method)

        ctrl.addWidget(QLabel(self.tr("Distance metric:")))
        self.hm_metric = QComboBox()
        self.hm_metric.addItem(self.tr("Euclidean"), "euclidean")
        self.hm_metric.addItem(self.tr("Correlation"), "correlation")
        self.hm_metric.addItem(self.tr("Cosine"), "cosine")
        ctrl.addWidget(self.hm_metric)

        ctrl.addWidget(QLabel(self.tr("Scale:")))
        self.hm_scale = QComboBox()
        self.hm_scale.addItem(self.tr("Row"), "row")
        self.hm_scale.addItem(self.tr("Column"), "col")
        self.hm_scale.addItem(self.tr("None"), "none")
        ctrl.addWidget(self.hm_scale)

        ctrl.addWidget(QLabel(self.tr("Max features:")))
        self.hm_maxfeat = QSpinBox()
        self.hm_maxfeat.setRange(10, 5000)
        self.hm_maxfeat.setValue(500)
        ctrl.addWidget(self.hm_maxfeat)

        btn = QPushButton(self.tr("Draw Heatmap"))
        btn.clicked.connect(self._draw_heatmap)
        ctrl.addWidget(btn)
        layout.addLayout(ctrl)

        self.hm_canvas = MplWidget(figsize=(12, 8))
        layout.addWidget(self.hm_canvas, stretch=1)
        return w

    def _draw_heatmap(self):
        if not self.mw.check_data_ready():
            return

        from visualization.heatmap import plot_heatmap

        data, labels = self._snapshot_data()
        method = self.hm_method.currentData()
        metric = self.hm_metric.currentData()
        scale = self.hm_scale.currentData()
        if scale == "none":
            scale = None
        max_feat = self.hm_maxfeat.value()

        def _job():
            return plot_heatmap(
                data,
                labels,
                method=method,
                metric=metric,
                scale=scale,
                max_features=max_feat,
            )

        def _on_success(fig):
            self._apply_canvas_figure(self.hm_canvas, fig)
            self.mw.show_shared_plot(self.hm_canvas.figure)

        self._run_async(_job, _on_success, self.tr("Heatmap Error"))
