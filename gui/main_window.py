"""
Main window:
- Left panel: sequential workflow tabs
- Right panel: shared live preview (table/plot)
- Bottom dock: processing log
- Pipeline orchestration + async execution
"""

from __future__ import annotations

import logging

import pandas as pd
from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QLibraryInfo,
    QLocale,
    QSettings,
    Qt,
    QTranslator,
)
from PySide6.QtGui import QAction, QIcon, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.pipeline import MetaboAnalystPipeline
from core.utils import get_resource_path
from gui.data_import_tab import DataImportTab
from gui.filter_tab import FilterTab
from gui.missing_value_tab import MissingValueTab
from gui.norm_tab import NormTab
from gui.settings_dialog import SettingsDialog
from gui.stats_tab import StatsTab
from gui.theme import apply_flat_theme
from gui.visual_tab import VisualTab
from gui.widgets.log_handler import QLogHandler
from gui.widgets.mpl_canvas import MplWidget
from gui.widgets.pandas_model import create_sortable_model
from gui.widgets.worker import PipelineWorker

logger = logging.getLogger("pipeline")

try:
    import qtawesome as qta

    HAS_QTA = True
except ImportError:
    HAS_QTA = False


def _icon(name: str, color: str = "#1976D2") -> QIcon:
    if HAS_QTA:
        return qta.icon(name, color=color)
    return QIcon()


class ProcessingStepCommand(QUndoCommand):
    """Undo/redo a dataframe state transition."""

    def __init__(
        self,
        main_window: "MainWindow",
        step_name: str,
        new_df: pd.DataFrame,
        old_df: pd.DataFrame | None,
    ):
        super().__init__(step_name)
        self._mw = main_window
        self._new_df = new_df.copy()
        self._old_df = old_df.copy() if old_df is not None else None

    def redo(self):
        self._mw.current_data = self._new_df.copy()
        self._mw._on_data_state_changed()

    def undo(self):
        if self._old_df is None:
            return
        self._mw.current_data = self._old_df.copy()
        self._mw._on_data_state_changed()


class MainWindow(QMainWindow):
    """PyMetaboAnalyst main window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyMetaboAnalyst")
        self.resize(1360, 860)
        self.setMinimumSize(1024, 680)

        self._settings = QSettings("PyMetaboAnalyst", "PyMetaboAnalyst")

        # Data state
        self.raw_data: pd.DataFrame | None = None
        self.current_data: pd.DataFrame | None = None
        self.raw_labels: pd.Series | None = None
        self.labels = None
        self.sample_info: pd.DataFrame | None = None
        self.sample_col: str | None = None
        self.group_col: str | None = None

        # Workflow stage:
        # 0: no data, 1: import done, 2: missing done, 3: filter done, 4: norm done
        self._stage = 0
        self.pipeline_params = self._default_pipeline_params()

        # Async execution
        self._active_workers: set[PipelineWorker] = set()

        # Undo / redo
        self.undo_stack = QUndoStack(self)

        # i18n
        self._app_translator = QTranslator()
        self._qt_translator = QTranslator()
        self._current_locale = "en"
        self._current_theme = self._settings.value("theme", "auto", type=str)
        app = QApplication.instance()
        if app is not None:
            apply_flat_theme(app, self._current_theme)

        self._setup_ui()
        self._create_menu_bar()
        self._create_log_dock()
        self._setup_statusbar()
        self._update_tab_states()

        # Apply persisted language preference
        saved_locale = self._settings.value("language", "en", type=str)
        if saved_locale:
            self.switch_language(saved_locale)

    @staticmethod
    def _default_pipeline_params() -> dict:
        return {
            "missing_thresh": 0.5,
            "impute_method": "min",
            "filter_method": "iqr",
            "filter_cutoff": None,
            "qc_rsd_enabled": False,
            "qc_rsd_threshold": 0.2,
            "row_norm": "None",
            "transform": "None",
            "scaling": "None",
            "factors": None,
            "factor_source": None,
        }

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)

        self.import_tab = DataImportTab(self)
        self.mv_tab = MissingValueTab(self)
        self.filter_tab = FilterTab(self)
        self.norm_tab = NormTab(self)
        self.stats_tab = StatsTab(self)
        self.visual_tab = VisualTab(self)

        self.tabs.addTab(self.import_tab, _icon("mdi6.file-import"), "")
        self.tabs.addTab(self.mv_tab, _icon("mdi6.table-question"), "")
        self.tabs.addTab(self.filter_tab, _icon("mdi6.filter-variant"), "")
        self.tabs.addTab(self.norm_tab, _icon("mdi6.chart-bell-curve"), "")
        self.tabs.addTab(self.stats_tab, _icon("mdi6.calculator-variant"), "")
        self.tabs.addTab(self.visual_tab, _icon("mdi6.chart-scatter-plot"), "")
        self.tabs.currentChanged.connect(self._sync_shared_preview_from_active_tab)
        self._retranslate_tabs()

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.tabs)

        self._preview_title = QLabel()
        self._preview_plot = MplWidget(figsize=(8, 6))
        self._preview_table = QTableView()
        self._preview_table.setSortingEnabled(True)
        self._preview_table.setAlternatingRowColors(True)

        self._preview_stack = QStackedWidget()
        self._preview_stack.addWidget(self._preview_table)
        self._preview_stack.addWidget(self._preview_plot)
        self._preview_stack.setCurrentWidget(self._preview_table)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.addWidget(self._preview_title)
        right_layout.addWidget(self._preview_stack, stretch=1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([420, 940])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        self.setCentralWidget(splitter)

    def _create_menu_bar(self):
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu(_icon("mdi6.file-document-outline"), "")
        self.edit_menu = menubar.addMenu(_icon("mdi6.pencil"), "")
        self.view_menu = menubar.addMenu(_icon("mdi6.eye-outline"), "")
        self.tools_menu = menubar.addMenu(_icon("mdi6.cog-outline"), "")
        self.help_menu = menubar.addMenu(_icon("mdi6.help-circle-outline"), "")

        self.act_export_data = QAction(_icon("mdi6.content-save"), "", self)
        self.act_export_data.triggered.connect(self._export_data)
        self.file_menu.addAction(self.act_export_data)

        self.act_export_raw = QAction(_icon("mdi6.file-export-outline"), "", self)
        self.act_export_raw.triggered.connect(self._export_raw)
        self.file_menu.addAction(self.act_export_raw)

        self.file_menu.addSeparator()

        self.act_quit = QAction(_icon("mdi6.exit-to-app"), "", self)
        self.act_quit.setShortcut("Ctrl+Q")
        self.act_quit.triggered.connect(self.close)
        self.file_menu.addAction(self.act_quit)

        self.undo_action = self.undo_stack.createUndoAction(self)
        self.undo_action.setIcon(_icon("mdi6.undo"))
        self.undo_action.setShortcut("Ctrl+Z")
        self.edit_menu.addAction(self.undo_action)

        self.redo_action = self.undo_stack.createRedoAction(self)
        self.redo_action.setIcon(_icon("mdi6.redo"))
        self.redo_action.setShortcut("Ctrl+Y")
        self.edit_menu.addAction(self.redo_action)

        self.act_toggle_log = QAction(_icon("mdi6.text-box-outline"), "", self)
        self.act_toggle_log.triggered.connect(
            lambda: self._log_dock.setVisible(not self._log_dock.isVisible())
        )
        self.view_menu.addAction(self.act_toggle_log)

        self.act_show_table_preview = QAction(_icon("mdi6.table"), "", self)
        self.act_show_table_preview.triggered.connect(self._show_preview_table)
        self.view_menu.addAction(self.act_show_table_preview)

        self.act_show_plot_preview = QAction(_icon("mdi6.chart-line"), "", self)
        self.act_show_plot_preview.triggered.connect(self._show_preview_plot)
        self.view_menu.addAction(self.act_show_plot_preview)

        self.act_settings = QAction(_icon("mdi6.cog"), "", self)
        self.act_settings.triggered.connect(self._show_settings)
        self.tools_menu.addAction(self.act_settings)

        self.lang_menu = self.tools_menu.addMenu(_icon("mdi6.translate"), "")
        self.act_lang_zh = QAction("", self)
        self.act_lang_zh.triggered.connect(lambda: self.switch_language("zh_TW"))
        self.lang_menu.addAction(self.act_lang_zh)
        self.act_lang_en = QAction("", self)
        self.act_lang_en.triggered.connect(lambda: self.switch_language("en"))
        self.lang_menu.addAction(self.act_lang_en)

        self.act_about = QAction(_icon("mdi6.information-outline"), "", self)
        self.act_about.triggered.connect(self._show_about)
        self.help_menu.addAction(self.act_about)

        self._retranslate_menus()

    def _create_log_dock(self):
        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumBlockCount(2000)
        self.log_widget.setMaximumHeight(180)

        self._log_dock = QDockWidget(self.tr("Processing Log"), self)
        self._log_dock.setWidget(self.log_widget)
        self._log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)

        self._log_handler = QLogHandler()
        self._log_handler.log_signal.connect(self.log_widget.appendPlainText)
        logger.addHandler(self._log_handler)
        logger.setLevel(logging.INFO)

    def _setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(240)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_bar.showMessage(self.tr("Ready"))

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def _retranslate_tabs(self):
        self.tabs.setTabText(0, self.tr("1. Data Import"))
        self.tabs.setTabText(1, self.tr("2. Missing Values"))
        self.tabs.setTabText(2, self.tr("3. Filtering"))
        self.tabs.setTabText(3, self.tr("4. Normalization"))
        self.tabs.setTabText(4, self.tr("5. Statistics"))
        self.tabs.setTabText(5, self.tr("6. Visualization"))

    def _retranslate_menus(self):
        self.file_menu.setTitle(self.tr("File"))
        self.edit_menu.setTitle(self.tr("Edit"))
        self.view_menu.setTitle(self.tr("View"))
        self.tools_menu.setTitle(self.tr("Tools"))
        self.help_menu.setTitle(self.tr("Help"))

        self.act_export_data.setText(self.tr("Export Processed Data (CSV)"))
        self.act_export_raw.setText(self.tr("Export Raw Data (CSV)"))
        self.act_quit.setText(self.tr("Quit"))

        self.undo_action.setText(self.tr("Undo"))
        self.redo_action.setText(self.tr("Redo"))

        self.act_toggle_log.setText(self.tr("Toggle Log Panel"))
        self.act_show_table_preview.setText(self.tr("Show Shared Table Preview"))
        self.act_show_plot_preview.setText(self.tr("Show Shared Plot Preview"))

        self.act_settings.setText(self.tr("Settings..."))
        self.lang_menu.setTitle(self.tr("Language"))
        self.act_lang_zh.setText(self.tr("Traditional Chinese"))
        self.act_lang_en.setText(self.tr("English"))
        self.act_about.setText(self.tr("About"))

        self._preview_title.setText(self.tr("Live Preview"))

    def retranslateUi(self):
        self.setWindowTitle(self.tr("PyMetaboAnalyst"))
        self._retranslate_tabs()
        self._retranslate_menus()
        self._log_dock.setWindowTitle(self.tr("Processing Log"))
        self.status_bar.showMessage(self.tr("Ready"))

        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, "retranslateUi"):
                widget.retranslateUi()

    def changeEvent(self, event):
        if event and event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def switch_language(self, locale_code: str):
        if locale_code == self._current_locale:
            return

        app = QCoreApplication.instance()
        app.removeTranslator(self._app_translator)
        app.removeTranslator(self._qt_translator)

        self._app_translator = QTranslator()
        trans_dir = str(get_resource_path("translations"))
        if self._app_translator.load(f"app_{locale_code}", trans_dir):
            app.installTranslator(self._app_translator)

        self._qt_translator = QTranslator()
        qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if self._qt_translator.load(f"qtbase_{locale_code}", qt_path):
            app.installTranslator(self._qt_translator)

        QLocale.setDefault(QLocale(locale_code))
        self._current_locale = locale_code
        self._settings.setValue("language", locale_code)

        self._update_plot_fonts(locale_code)
        self.retranslateUi()
        logger.info("Language switched to %s", locale_code)

    @staticmethod
    def _update_plot_fonts(locale: str):
        import matplotlib.pyplot as plt

        if locale.startswith("zh"):
            plt.rcParams["font.sans-serif"] = [
                "Noto Sans CJK TC",
                "Microsoft JhengHei",
                "PingFang TC",
                "DejaVu Sans",
            ]
        else:
            plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

    # ------------------------------------------------------------------
    # Workflow state
    # ------------------------------------------------------------------

    def _update_tab_states(self):
        self.tabs.setTabEnabled(0, True)
        self.tabs.setTabEnabled(1, self._stage >= 1)
        self.tabs.setTabEnabled(2, self._stage >= 2)
        self.tabs.setTabEnabled(3, self._stage >= 3)
        self.tabs.setTabEnabled(4, self._stage >= 4)
        self.tabs.setTabEnabled(5, self._stage >= 4)

    def _show_preview_table(self):
        self._preview_stack.setCurrentWidget(self._preview_table)

    def _show_preview_plot(self):
        self._preview_stack.setCurrentWidget(self._preview_plot)

    def _sync_shared_preview_from_active_tab(self, index: int):
        widget = self.tabs.widget(index)
        if widget is None:
            return
        plot_widgets = widget.findChildren(MplWidget)
        if plot_widgets:
            self.show_shared_plot(plot_widgets[0].figure)
            return
        if self.current_data is not None:
            self.show_shared_table(self.current_data)

    def show_shared_table(self, df: pd.DataFrame):
        if df is None or df.empty:
            return

        preview_df = df.iloc[:400, :120]
        source, proxy = create_sortable_model(preview_df)
        self._preview_source_model = source
        self._preview_proxy_model = proxy
        self._preview_table.setModel(proxy)
        self._preview_table.setSortingEnabled(True)
        self._show_preview_table()

    def show_shared_plot(self, fig):
        if fig is None:
            return
        self._preview_plot.canvas.figure = fig
        self._preview_plot.canvas.draw()
        self._show_preview_plot()

    def _on_data_state_changed(self):
        if self.current_data is not None:
            self.show_shared_table(self.current_data)

    # ------------------------------------------------------------------
    # Pipeline orchestration (single source of truth)
    # ------------------------------------------------------------------

    def set_pipeline_params(self, **kwargs):
        self.pipeline_params.update(kwargs)

    def run_pipeline_until(self, stage: str):
        if self.raw_data is None:
            raise ValueError("No data loaded.")

        params = dict(self.pipeline_params)
        if stage == "missing":
            params.update(
                filter_method="None",
                row_norm="None",
                transform="None",
                scaling="None",
            )
        elif stage == "filter":
            params.update(
                row_norm="None",
                transform="None",
                scaling="None",
            )
        elif stage == "norm":
            pass
        else:
            raise ValueError(f"Unknown pipeline stage: {stage}")

        source_labels = self.raw_labels if self.raw_labels is not None else self.labels
        pipeline = MetaboAnalystPipeline(self.raw_data, source_labels)
        result = pipeline.run_pipeline(**params)
        return {
            "data": result,
            "labels": pipeline.processed_labels,
            "log": pipeline.log,
        }

    def run_pipeline_async(self, stage: str, on_success, on_error=None):
        self.show_progress(True)
        worker = PipelineWorker(self.run_pipeline_until, stage)
        self._active_workers.add(worker)

        def _handle_result(payload):
            on_success(payload)

        def _handle_error(error_text: str):
            if on_error is not None:
                on_error(error_text)
            else:
                QMessageBox.critical(self, self.tr("Pipeline Error"), error_text)

        def _handle_finished():
            self.show_progress(False)
            self._active_workers.discard(worker)

        worker.signals.result.connect(_handle_result)
        worker.signals.error.connect(_handle_error)
        worker.signals.finished.connect(_handle_finished)
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Data plumbing for tabs
    # ------------------------------------------------------------------

    def set_data(
        self,
        df: pd.DataFrame,
        labels,
        sample_col: str,
        group_col: str,
        sample_info: pd.DataFrame | None = None,
    ):
        self.raw_data = df.copy()
        self.current_data = df.copy()
        if isinstance(labels, pd.Series):
            labels_series = labels.copy()
            if not labels_series.index.equals(df.index):
                labels_series.index = df.index
        else:
            labels_series = pd.Series(labels, index=df.index)

        self.raw_labels = labels_series.copy()
        self.labels = labels_series.copy()
        self.sample_info = sample_info.copy() if sample_info is not None else None
        self.sample_col = sample_col
        self.group_col = group_col

        self.pipeline_params = self._default_pipeline_params()
        self.undo_stack.clear()
        self._stage = 1
        self._update_tab_states()

        self._on_data_state_changed()

        msg = self.tr("Loaded {n_samples} samples and {n_features} features").format(
            n_samples=df.shape[0], n_features=df.shape[1]
        )
        self.status_bar.showMessage(msg)
        logger.info(msg)

        if hasattr(self.mv_tab, "on_data_loaded"):
            self.mv_tab.on_data_loaded()
        if hasattr(self.filter_tab, "on_data_updated"):
            self.filter_tab.on_data_updated()
        if hasattr(self.norm_tab, "on_data_updated"):
            self.norm_tab.on_data_updated()
        if hasattr(self.stats_tab, "_refresh_groups"):
            self.stats_tab._refresh_groups()

        self.tabs.setCurrentIndex(1)

    def update_data(
        self,
        df: pd.DataFrame,
        source_tab: str,
        step_key: str | None = None,
        labels=None,
    ):
        old_df = self.current_data.copy() if self.current_data is not None else None
        cmd = ProcessingStepCommand(self, source_tab, df, old_df)
        self.undo_stack.push(cmd)

        if labels is not None:
            if isinstance(labels, pd.Series):
                self.labels = labels.copy()
            else:
                self.labels = pd.Series(labels, index=df.index)

        stage_map = {"missing": 2, "filter": 3, "norm": 4}
        next_tab_map = {"missing": 2, "filter": 3, "norm": 4}
        if step_key in stage_map:
            self._stage = max(self._stage, stage_map[step_key])

        self._update_tab_states()

        if step_key in next_tab_map and self.tabs.isTabEnabled(next_tab_map[step_key]):
            self.tabs.setCurrentIndex(next_tab_map[step_key])

        msg = self.tr("[{step}] Current shape: {n_samples} x {n_features}").format(
            step=source_tab, n_samples=df.shape[0], n_features=df.shape[1]
        )
        self.status_bar.showMessage(msg)
        logger.info(msg)

        if self._stage >= 4 and hasattr(self.stats_tab, "_refresh_groups"):
            self.stats_tab._refresh_groups()

    def check_data_ready(self) -> bool:
        if self.current_data is None:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Please import data before running this step."),
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def show_progress(self, visible: bool = True):
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

    def set_progress(self, value: int, maximum: int = 100):
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)

    # ------------------------------------------------------------------
    # File / dialog actions
    # ------------------------------------------------------------------

    def _export_data(self):
        if self.current_data is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No processed data to export."))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Processed Data"), "processed_data.csv", "CSV (*.csv)"
        )
        if not path:
            return

        export_df = self.current_data.copy()
        if self.labels is not None:
            label_col = self.group_col or "Group"
            values = self.labels.values if hasattr(self.labels, "values") else self.labels
            export_df.insert(0, label_col, values)
        export_df.to_csv(path)
        self.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))
        logger.info("Exported processed data to %s", path)

    def _export_raw(self):
        if self.raw_data is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No raw data to export."))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Raw Data"), "raw_data.csv", "CSV (*.csv)"
        )
        if not path:
            return

        export_df = self.raw_data.copy()
        if self.raw_labels is not None:
            label_col = self.group_col or "Group"
            values = (
                self.raw_labels.values
                if hasattr(self.raw_labels, "values")
                else self.raw_labels
            )
            export_df.insert(0, label_col, values)
        export_df.to_csv(path)
        self.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))
        logger.info("Exported raw data to %s", path)

    def _show_settings(self):
        dlg = SettingsDialog(
            self,
            current_theme=self._current_theme,
            current_locale=self._current_locale,
        )
        if not dlg.exec():
            return

        theme = dlg.selected_theme
        locale = dlg.selected_locale

        app = QApplication.instance()
        if app is not None:
            apply_flat_theme(app, theme)
        self._current_theme = theme
        self._settings.setValue("theme", theme)
        logger.info("Theme switched to %s", theme)

        self.switch_language(locale)

    def _show_about(self):
        QMessageBox.about(
            self,
            self.tr("About"),
            self.tr(
                "PyMetaboAnalyst\n\n"
                "A Python + PySide6 desktop implementation inspired by MetaboAnalyst workflow.\n"
                "Includes preprocessing pipeline, statistical analysis, and visualization."
            ),
        )
