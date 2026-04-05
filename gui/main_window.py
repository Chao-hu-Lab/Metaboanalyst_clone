"""
Main window:
- Left panel: sequential workflow tabs
- Right panel: shared live preview (table/plot)
- Bottom dock: processing log
- Pipeline orchestration + async execution
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
from pathlib import Path

import pandas as pd
from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QLibraryInfo,
    QLocale,
    QSignalBlocker,
    QSettings,
    QSize,
    Qt,
    QTranslator,
)
from PySide6.QtGui import QAction, QIcon, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QComboBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.app_config import (
    AppConfig,
    PresetReference,
    default_pipeline_params,
    dump_yaml,
    get_local_preset_dir,
    list_builtin_presets,
    list_local_presets,
    load_preset_reference,
    load_yaml_config,
)
from core.param_specs import build_default_config
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
from gui.widgets.preset_bar import PresetBar
from gui.widgets.worker import PipelineWorker
from visualization.theme_manager import ThemeManager

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
        *,
        new_labels: pd.Series | None = None,
        old_labels: pd.Series | None = None,
        new_stage: int | None = None,
        old_stage: int | None = None,
    ):
        super().__init__(step_name)
        self._mw = main_window
        self._new_df = new_df.copy()
        self._old_df = old_df.copy() if old_df is not None else None
        self._new_labels = new_labels.copy() if new_labels is not None else None
        self._old_labels = old_labels.copy() if old_labels is not None else None
        self._new_stage = new_stage
        self._old_stage = old_stage

    def redo(self):
        self._mw.current_data = self._new_df.copy()
        if self._new_labels is not None:
            self._mw.labels = self._new_labels.copy()
        if self._new_stage is not None:
            self._mw._stage = self._new_stage
        self._mw._on_data_state_changed()

    def undo(self):
        if self._old_df is None:
            return
        self._mw.current_data = self._old_df.copy()
        if self._old_labels is not None:
            self._mw.labels = self._old_labels.copy()
        if self._old_stage is not None:
            self._mw._stage = self._old_stage
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
        self.raw_feature_metadata: pd.DataFrame | None = None
        self.sample_info: pd.DataFrame | None = None
        self.sample_col: str | None = None
        self.group_col: str | None = None
        self._filtered_data: pd.DataFrame | None = None
        self._filtered_labels: pd.Series | None = None
        self._preset_tracking_depth = 0
        self._active_preset_config: AppConfig | None = None
        self._active_preset_path: str | None = None
        self._active_preset_kind: str | None = None
        self._last_preset_apply_sections: list[str] = []
        self._last_preset_unsupported_paths: list[str] = []
        self._builtin_preset_refs: list[PresetReference] = []
        self._local_preset_refs: list[PresetReference] = []
        self._preset_load_menu: QMenu | None = None

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
        self._current_theme = self._settings.value("theme", "light", type=str)
        app = QApplication.instance()
        if app is not None:
            apply_flat_theme(app, self._current_theme)
        visual_theme = self._current_theme if self._current_theme in ThemeManager.SUPPORTED_THEMES else "light"
        self.theme_manager = ThemeManager(default_theme=visual_theme)

        self._setup_ui()
        self._reload_preset_repository()
        self._connect_preset_watchers()
        self._create_menu_bar()
        self._create_main_toolbar()
        self._create_log_dock()
        self._setup_statusbar()
        self._update_tab_states()
        self._refresh_preset_bar()
        self.theme_manager.register_callback(self._apply_selected_theme)
        self._apply_selected_theme(self.theme_manager.current_theme)

        # Apply persisted language preference
        saved_locale = self._settings.value("language", "en", type=str)
        if saved_locale:
            self.switch_language(saved_locale)

    @staticmethod
    def _default_pipeline_params() -> dict:
        return default_pipeline_params()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        # --- Sidebar navigation (QListWidget) + content pages (QStackedWidget) ---
        self.import_tab = DataImportTab(self)
        self.mv_tab = MissingValueTab(self)
        self.filter_tab = FilterTab(self)
        self.norm_tab = NormTab(self)
        self.stats_tab = StatsTab(self)
        self.visual_tab = VisualTab(self)

        self._tab_widgets = [
            self.import_tab, self.mv_tab, self.filter_tab,
            self.norm_tab, self.stats_tab, self.visual_tab,
        ]
        self._tab_icons = [
            "mdi6.file-import", "mdi6.table-question", "mdi6.filter-variant",
            "mdi6.chart-bell-curve", "mdi6.calculator-variant", "mdi6.chart-scatter-plot",
        ]

        # Sidebar list
        self._nav_list = QListWidget()
        self._nav_list.setObjectName("nav_list")
        self._nav_list.setFixedWidth(200)
        self._nav_list.setIconSize(QSize(24, 24))
        self._nav_list.setSpacing(4)
        for i, icon_name in enumerate(self._tab_icons):
            item = QListWidgetItem(_icon(icon_name), "")
            item.setSizeHint(QSize(190, 48))
            self._nav_list.addItem(item)

        # Content stack
        self._page_stack = QStackedWidget()
        for w in self._tab_widgets:
            self._page_stack.addWidget(w)

        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        self._retranslate_tabs()
        self._nav_list.setCurrentRow(0)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._nav_list)

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
        splitter.addWidget(self._page_stack)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 420, 740])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)

        # Wrap splitter with pipeline navigation bar
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._create_pipeline_nav())
        self.preset_bar = PresetBar(self)
        central_layout.addWidget(self.preset_bar)
        central_layout.addWidget(splitter, stretch=1)
        self.setCentralWidget(central)

    def _create_pipeline_nav(self) -> QFrame:
        """Create pipeline navigation bar showing overall workflow position."""
        nav = QFrame()
        nav.setFixedHeight(42)
        nav.setStyleSheet("background-color: #0d1b2a;")

        layout = QHBoxLayout(nav)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        # Project name on the left
        self._project_label = QLabel("PyMetaboAnalyst")
        self._project_label.setStyleSheet(
            "color: #FFFFFF; font-weight: bold; font-size: 13pt; "
            "background: transparent; padding: 0 16px 0 4px;"
        )
        layout.addWidget(self._project_label)
        layout.addStretch()

        self._pipeline_step_labels = []
        self._pipeline_arrows = []
        steps_current = [False, False, True]

        for i, is_current in enumerate(steps_current):
            if i > 0:
                arrow = QLabel("  →  ")
                arrow.setStyleSheet(
                    "color: #7EB0E8; font-family: Consolas; font-size: 12pt; "
                    "background: transparent;"
                )
                layout.addWidget(arrow)
                self._pipeline_arrows.append(arrow)

            lbl = QLabel("")
            if is_current:
                lbl.setStyleSheet(
                    "color: #FFFFFF; font-weight: bold; font-size: 11pt; "
                    "background-color: #1976D2; border-radius: 4px; "
                    "padding: 4px 14px;"
                )
            else:
                lbl.setStyleSheet(
                    "color: #A0B8D0; font-size: 11pt; "
                    "background: transparent; padding: 4px 14px;"
                )
            layout.addWidget(lbl)
            self._pipeline_step_labels.append(lbl)

        layout.addStretch()
        self._retranslate_pipeline_nav()
        return nav

    def _retranslate_pipeline_nav(self):
        texts = [
            self.tr("Step 1: Preprocessing"),
            self.tr("Step 2: Normalization"),
            self.tr("Step 3: Statistical Analysis"),
        ]
        for lbl, text in zip(self._pipeline_step_labels, texts):
            lbl.setText(text)

    def _create_menu_bar(self):
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu(_icon("mdi6.file-document-outline"), "")
        self.view_menu = menubar.addMenu(_icon("mdi6.eye-outline"), "")
        self.tools_menu = menubar.addMenu(_icon("mdi6.cog-outline"), "")
        self.help_menu = menubar.addMenu(_icon("mdi6.help-circle-outline"), "")

        # -- File menu --
        self.act_export_data = QAction(_icon("mdi6.content-save"), "", self)
        self.act_export_data.triggered.connect(self._export_data)
        self.file_menu.addAction(self.act_export_data)

        self.act_load_config = QAction(_icon("mdi6.file-cog-outline"), "", self)
        self.act_load_config.triggered.connect(self._load_config_yaml)
        self.file_menu.addAction(self.act_load_config)

        self.file_menu.addSeparator()

        self.act_quit = QAction(_icon("mdi6.exit-to-app"), "", self)
        self.act_quit.setShortcut("Ctrl+Q")
        self.act_quit.triggered.connect(self.close)
        self.file_menu.addAction(self.act_quit)

        # -- View menu --
        self.act_toggle_log = QAction(_icon("mdi6.text-box-outline"), "", self)
        self.act_toggle_log.triggered.connect(
            lambda: self._log_dock.setVisible(not self._log_dock.isVisible())
        )
        self.view_menu.addAction(self.act_toggle_log)

        # -- Tools menu --
        self.lang_menu = self.tools_menu.addMenu(_icon("mdi6.translate"), "")
        self.act_lang_zh = QAction("", self)
        self.act_lang_zh.triggered.connect(lambda: self.switch_language("zh_TW"))
        self.lang_menu.addAction(self.act_lang_zh)
        self.act_lang_en = QAction("", self)
        self.act_lang_en.triggered.connect(lambda: self.switch_language("en"))
        self.lang_menu.addAction(self.act_lang_en)

        self.font_menu = self.tools_menu.addMenu(_icon("mdi6.format-size"), "")
        for label, size in [("Small (9pt)", 9), ("Medium (11pt)", 11), ("Large (13pt)", 13)]:
            act = QAction(label, self)
            act.triggered.connect(lambda checked, s=size: self._set_font_size(s))
            self.font_menu.addAction(act)

        # -- Help menu --
        self.act_about = QAction(_icon("mdi6.information-outline"), "", self)
        self.act_about.triggered.connect(self._show_about)
        self.help_menu.addAction(self.act_about)

        self._retranslate_menus()

    def _create_main_toolbar(self):
        self.main_toolbar = self.addToolBar(self.tr("Main Tools"))
        self.main_toolbar.setObjectName("MainToolbar")
        self.main_toolbar.setMovable(False)

        self._theme_toolbar_label = QLabel(self.tr("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("theme_combo")
        self.theme_combo.addItems(self.theme_manager.get_supported_themes())
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_combo_changed)

        self.main_toolbar.addWidget(self._theme_toolbar_label)
        self.main_toolbar.addWidget(self.theme_combo)

    def _on_theme_combo_changed(self, theme_name: str):
        self.theme_manager.set_theme(theme_name)

    def _apply_selected_theme(self, theme_name: str):
        app = QApplication.instance()
        font_size = self._settings.value("font_size", 11, type=int)
        if app is not None:
            apply_flat_theme(app, theme_name, font_size)

        self._current_theme = theme_name
        self._settings.setValue("theme", theme_name)

        if hasattr(self, "theme_combo") and self.theme_combo.currentText() != theme_name:
            blocker = QSignalBlocker(self.theme_combo)
            self.theme_combo.setCurrentText(theme_name)
            del blocker

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

        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setMaximumWidth(80)
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.status_bar.addPermanentWidget(self.cancel_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(240)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_bar.showMessage(self.tr("Ready"))

    def _connect_preset_watchers(self) -> None:
        self.preset_bar.apply_button.clicked.connect(self._apply_current_preset)
        self.preset_bar.save_button.clicked.connect(self._save_preset_yaml)
        self.preset_bar.reset_button.clicked.connect(self._reset_preset_to_defaults)
        for tab in (
            self.mv_tab,
            self.filter_tab,
            self.norm_tab,
            self.stats_tab,
            self.visual_tab,
        ):
            if hasattr(tab, "connect_state_changed"):
                tab.connect_state_changed(self._on_preset_controls_changed)

    def _reload_preset_repository(self) -> None:
        self._builtin_preset_refs = list_builtin_presets()
        self._local_preset_refs = list_local_presets()
        self._rebuild_preset_load_menu()

    def _populate_preset_submenu(
        self,
        menu: QMenu,
        presets: list[PresetReference],
    ) -> None:
        if not presets:
            empty_action = menu.addAction(self.tr("None"))
            empty_action.setEnabled(False)
            return

        for preset in presets:
            action = menu.addAction(preset.label)
            if preset.description:
                action.setToolTip(preset.description)
                action.setStatusTip(preset.description)
            action.triggered.connect(
                lambda _checked=False, preset_ref=preset: self._load_preset_reference(preset_ref)
            )

    def _rebuild_preset_load_menu(self) -> None:
        menu = QMenu(self)
        built_in_menu = menu.addMenu(self.tr("Built-in Presets"))
        self._populate_preset_submenu(built_in_menu, self._builtin_preset_refs)

        local_menu = menu.addMenu(self.tr("Local Presets"))
        self._populate_preset_submenu(local_menu, self._local_preset_refs)

        menu.addSeparator()
        browse_action = menu.addAction(self.tr("Browse YAML..."))
        browse_action.triggered.connect(self._load_config_yaml)

        self._preset_load_menu = menu
        self.preset_bar.load_button.setMenu(menu)

    def _load_preset_reference(self, reference: PresetReference) -> list[str]:
        try:
            config = load_preset_reference(reference, require_required_sections=False)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Load Error"), str(exc))
            return []
        display_path = reference.source_uri if reference.kind == "builtin" else str(reference.path)
        return self._load_preset_config(config, display_path)

    @contextmanager
    def _suspend_preset_tracking(self):
        self._preset_tracking_depth += 1
        try:
            yield
        finally:
            self._preset_tracking_depth -= 1

    def _on_preset_controls_changed(self, *_args) -> None:
        if self._preset_tracking_depth > 0:
            return
        self.pipeline_params = self._read_pipeline_state_from_tabs()
        self._refresh_preset_bar()

    @staticmethod
    def _default_app_config() -> AppConfig:
        return AppConfig.from_mapping(
            build_default_config(include_runtime=False),
            require_required_sections=False,
        )

    @staticmethod
    def _is_builtin_preset_path(path: str | None) -> bool:
        if not path:
            return False
        normalized = path.replace("\\", "/")
        return normalized.startswith("builtin://") or "/resources/presets/" in normalized

    def _infer_preset_kind(self, path: str | None) -> str | None:
        if path is None:
            return None
        return "Built-in Preset" if self._is_builtin_preset_path(path) else "Local Preset"

    @staticmethod
    def _merge_config_fragment(target: dict, fragment: dict) -> None:
        for key, value in fragment.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                MainWindow._merge_config_fragment(target[key], value)
            else:
                target[key] = value

    def _collect_tab_state_fragments(self) -> list[dict[str, object]]:
        fragments: list[dict[str, object]] = []
        for tab in (
            self.mv_tab,
            self.filter_tab,
            self.norm_tab,
            self.stats_tab,
            self.visual_tab,
        ):
            if hasattr(tab, "read_state"):
                fragment = tab.read_state()
                if fragment:
                    fragments.append(fragment)
        return fragments

    def _read_pipeline_state_from_tabs(self) -> dict:
        merged = self._default_pipeline_params()
        for fragment in self._collect_tab_state_fragments():
            pipeline_fragment = fragment.get("pipeline")
            if isinstance(pipeline_fragment, dict):
                merged.update(pipeline_fragment)
        return merged

    def _build_current_gui_preset_config(self) -> AppConfig:
        if self._active_preset_config is not None:
            raw_config = self._active_preset_config.to_dict(include_runtime=False)
        else:
            raw_config = build_default_config(include_runtime=False)

        for fragment in self._collect_tab_state_fragments():
            self._merge_config_fragment(raw_config, fragment)
        return AppConfig.from_mapping(raw_config, require_required_sections=False)

    def _collect_pending_preset_paths(self, config: AppConfig | None) -> list[str]:
        if config is None:
            return []

        pending: list[str] = []
        factor_column = config.spec_norm.get("factor_column")
        if factor_column is not None:
            factor_text = str(factor_column)
            if self.norm_tab.factor_combo.findData(factor_text) < 0 and self.norm_tab.factor_combo.findText(factor_text) < 0:
                pending.append("spec_norm.factor_column")
        return pending

    def _collect_ignored_preset_fields(self, config: AppConfig | None) -> list[str]:
        ignored: set[str] = set(self._last_preset_unsupported_paths)
        if config is not None and config.extras:
            ignored.update(config.extras.keys())
        return sorted(ignored)

    @staticmethod
    def _remove_dotted_path(mapping: dict, path: str) -> None:
        parts = path.split(".")
        current = mapping
        for part in parts[:-1]:
            next_value = current.get(part)
            if not isinstance(next_value, dict):
                return
            current = next_value
        current.pop(parts[-1], None)

    def _refresh_preset_bar(self) -> None:
        current_config = self._build_current_gui_preset_config()
        default_config = self._default_app_config()
        pending_paths = self._collect_pending_preset_paths(self._active_preset_config)
        ignored_fields = self._collect_ignored_preset_fields(self._active_preset_config)

        if self._active_preset_config is not None:
            source_text = self._active_preset_path or self.tr("In-memory preset")
            baseline_config = self._active_preset_config
        else:
            source_text = self.tr("Not loaded")
            baseline_config = default_config

        current_state = current_config.to_dict(include_runtime=False)
        baseline_state = baseline_config.to_dict(include_runtime=False)
        for pending_path in pending_paths:
            self._remove_dotted_path(current_state, pending_path)
            self._remove_dotted_path(baseline_state, pending_path)
        for unsupported_path in self._last_preset_unsupported_paths:
            self._remove_dotted_path(current_state, unsupported_path)
            self._remove_dotted_path(baseline_state, unsupported_path)
        is_dirty = current_state != baseline_state

        if self._active_preset_config is not None:
            if is_dirty:
                state_text = "Modified"
            elif pending_paths:
                state_text = "Pending Data Mapping"
            else:
                state_text = self._active_preset_kind or "Local Preset"
        else:
            state_text = "Unsaved"

        summary_parts: list[str] = []
        if self._last_preset_apply_sections:
            summary_parts.append(", ".join(self._last_preset_apply_sections))
        else:
            summary_parts.append(self.tr("Defaults only"))
        if pending_paths:
            summary_parts.append(
                self.tr("Pending: {paths}").format(paths=", ".join(pending_paths))
            )

        if ignored_fields:
            ignored_text = ", ".join(ignored_fields)
        else:
            ignored_text = self.tr("None")

        self.preset_bar.source_value_label.setText(source_text)
        self.preset_bar.state_value_label.setText(state_text)
        self.preset_bar.summary_value_label.setText(" | ".join(summary_parts))
        self.preset_bar.ignored_value_label.setText(ignored_text)
        self.preset_bar.apply_button.setEnabled(
            self._active_preset_config is not None and (is_dirty or bool(pending_paths))
        )
        self.preset_bar.reset_button.setEnabled(True)
        self.preset_bar.save_button.setEnabled(True)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def _on_nav_changed(self, index: int):
        """Handle sidebar navigation item selection."""
        if 0 <= index < self._page_stack.count():
            self._page_stack.setCurrentIndex(index)
            self._sync_shared_preview_from_active_tab(index)

    def _retranslate_tabs(self):
        labels = [
            self.tr("1. Data Import"),
            self.tr("2. Missing Values"),
            self.tr("3. Filtering"),
            self.tr("4. Normalization"),
            self.tr("5. Statistics"),
            self.tr("6. Visualization"),
        ]
        for i, text in enumerate(labels):
            if i < self._nav_list.count():
                self._nav_list.item(i).setText(text)

    def _retranslate_menus(self):
        self.file_menu.setTitle(self.tr("File"))
        self.view_menu.setTitle(self.tr("View"))
        self.tools_menu.setTitle(self.tr("Tools"))
        self.help_menu.setTitle(self.tr("Help"))

        self.act_export_data.setText(self.tr("Export Processed Data (CSV)"))
        self.act_load_config.setText(self.tr("Load Config (YAML)"))
        self.act_quit.setText(self.tr("Quit"))

        self.act_toggle_log.setText(self.tr("Toggle Log Panel"))

        self.lang_menu.setTitle(self.tr("Language"))
        self.act_lang_zh.setText(self.tr("Traditional Chinese"))
        self.act_lang_en.setText(self.tr("English"))
        self.font_menu.setTitle(self.tr("Font Size"))
        self.act_about.setText(self.tr("About"))

        self._preview_title.setText(self.tr("Live Preview"))
        if hasattr(self, "_theme_toolbar_label"):
            self._theme_toolbar_label.setText(self.tr("Theme:"))
        if hasattr(self, "main_toolbar"):
            self.main_toolbar.setWindowTitle(self.tr("Main Tools"))

    def retranslateUi(self):
        self.setWindowTitle(self.tr("PyMetaboAnalyst"))
        self._retranslate_tabs()
        self._retranslate_menus()
        self._retranslate_pipeline_nav()
        self._rebuild_preset_load_menu()
        self.preset_bar.retranslateUi()
        self._log_dock.setWindowTitle(self.tr("Processing Log"))
        self.status_bar.showMessage(self.tr("Ready"))

        for i in range(self._page_stack.count()):
            widget = self._page_stack.widget(i)
            if hasattr(widget, "retranslateUi"):
                widget.retranslateUi()
        self._refresh_preset_bar()

    def changeEvent(self, event):
        if event and event.type() == QEvent.Type.LanguageChange:
            with self._suspend_preset_tracking():
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
        with self._suspend_preset_tracking():
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
        enabled = [True, self._stage >= 1, self._stage >= 2,
                   self._stage >= 3, self._stage >= 4, self._stage >= 4]
        for i, en in enumerate(enabled):
            if i < self._nav_list.count():
                item = self._nav_list.item(i)
                flags = item.flags()
                if en:
                    item.setFlags(flags | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                else:
                    item.setFlags(flags & ~(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable))

    def _show_preview_table(self):
        self._preview_stack.setCurrentWidget(self._preview_table)

    def _show_preview_plot(self):
        self._preview_stack.setCurrentWidget(self._preview_plot)

    def _sync_shared_preview_from_active_tab(self, index: int):
        widget = self._page_stack.widget(index)
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
        self._refresh_preset_bar()

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: object) -> bool:
        if value is None:
            return False
        index = combo.findData(value)
        if index < 0:
            index = combo.findData(str(value))
        if index < 0:
            index = combo.findText(str(value))
        if index < 0:
            return False

        blocker = QSignalBlocker(combo)
        combo.setCurrentIndex(index)
        del blocker
        return True

    def _apply_pipeline_params_to_widgets(self):
        params = dict(self.pipeline_params)

        if hasattr(self, "mv_tab"):
            blocker = QSignalBlocker(self.mv_tab.thresh_spin)
            self.mv_tab.thresh_spin.setValue(float(params["missing_thresh"]))
            del blocker
            self._set_combo_value(self.mv_tab.method_combo, params["impute_method"])

        if hasattr(self, "filter_tab"):
            self._set_combo_value(self.filter_tab.method_combo, params["filter_method"])
            auto_cutoff = params["filter_cutoff"] is None
            blocker = QSignalBlocker(self.filter_tab.auto_check)
            self.filter_tab.auto_check.setChecked(auto_cutoff)
            del blocker
            self.filter_tab._toggle_auto(auto_cutoff)
            if params["filter_cutoff"] is not None:
                blocker = QSignalBlocker(self.filter_tab.cutoff_spin)
                self.filter_tab.cutoff_spin.setValue(float(params["filter_cutoff"]))
                del blocker
            blocker = QSignalBlocker(self.filter_tab.qc_check)
            self.filter_tab.qc_check.setChecked(bool(params["qc_rsd_enabled"]))
            del blocker
            blocker = QSignalBlocker(self.filter_tab.qc_thresh_spin)
            self.filter_tab.qc_thresh_spin.setValue(float(params["qc_rsd_threshold"]))
            del blocker
            self.filter_tab.qc_thresh_spin.setEnabled(bool(self.filter_tab.qc_check.isChecked() and self.filter_tab.qc_check.isEnabled()))

        if hasattr(self, "norm_tab"):
            self._set_combo_value(self.norm_tab.row_combo, params["row_norm"])
            self._set_combo_value(self.norm_tab.trans_combo, params["transform"])
            self._set_combo_value(self.norm_tab.scale_combo, params["scaling"])
            factor_source = params.get("factor_source")
            if factor_source is not None:
                self._set_combo_value(self.norm_tab.factor_combo, factor_source)
            self.norm_tab._on_row_method_changed()

    def _apply_config_to_widgets(self, config: AppConfig) -> bool:
        state = config.to_dict(include_runtime=False)
        unsupported_paths: list[str] = []
        with self._suspend_preset_tracking():
            self.pipeline_params = config.to_pipeline_params()
            self._apply_pipeline_params_to_widgets()
            for tab in (
                self.mv_tab,
                self.filter_tab,
                self.norm_tab,
                self.stats_tab,
                self.visual_tab,
            ):
                if hasattr(tab, "apply_state"):
                    result = tab.apply_state(state)
                    unsupported_paths.extend(result.unsupported_paths)
            factor_column = config.spec_norm.get("factor_column")
            factor_column_applied = False
            if factor_column is not None and hasattr(self, "norm_tab"):
                factor_column_applied = (
                    self.norm_tab.factor_combo.findData(str(factor_column)) >= 0
                    or self.norm_tab.factor_combo.findText(str(factor_column)) >= 0
                )
        self._last_preset_unsupported_paths = sorted(set(unsupported_paths))
        return factor_column_applied

    def _describe_applied_sections(
        self,
        config: AppConfig,
        *,
        factor_column_applied: bool,
    ) -> list[str]:
        applied_sections = ["pipeline"]
        if "groups" in config.source_sections:
            applied_sections.append("groups (stored for later phases)")
        if "analysis" in config.source_sections:
            applied_sections.append("analysis (stored for later phases)")
        if "output" in config.source_sections:
            applied_sections.append("output (stored for later phases)")
        if "spec_norm" in config.source_sections:
            if factor_column_applied:
                applied_sections.append("spec_norm")
            else:
                applied_sections.append("spec_norm (stored for later phases)")
        return applied_sections

    def _apply_loaded_config(
        self,
        config: AppConfig,
        path: str,
        *,
        announce: bool = True,
    ) -> list[str]:
        factor_column_applied = self._apply_config_to_widgets(config)
        applied_sections = self._describe_applied_sections(
            config,
            factor_column_applied=factor_column_applied,
        )
        self._last_preset_apply_sections = applied_sections

        if announce:
            summary = ", ".join(applied_sections)
            self.status_bar.showMessage(
                self.tr("Config loaded: {path} ({summary})").format(path=path, summary=summary)
            )
            logger.info("Loaded shared config from %s, sections: %s", path, applied_sections)
        self._refresh_preset_bar()
        return applied_sections

    def _load_preset_config(self, config: AppConfig, path: str) -> list[str]:
        applied_sections = self._apply_loaded_config(config, path)
        self._active_preset_config = config
        self._active_preset_path = path
        self._active_preset_kind = self._infer_preset_kind(path)
        self._refresh_preset_bar()
        return applied_sections

    def _apply_current_preset(self, *_args) -> list[str]:
        if self._active_preset_config is None:
            return []
        path = self._active_preset_path or "memory://preset"
        return self._apply_loaded_config(self._active_preset_config, path)

    def _save_preset_to_path(self, path: str | Path) -> AppConfig:
        config = self._build_current_gui_preset_config()
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(dump_yaml(config, include_runtime=False), encoding="utf-8")
        saved_config = load_yaml_config(target_path, require_required_sections=False)
        self._reload_preset_repository()
        self._active_preset_config = saved_config
        self._active_preset_path = str(target_path)
        self._active_preset_kind = self._infer_preset_kind(str(target_path))
        self._last_preset_unsupported_paths = []
        self._last_preset_apply_sections = self._describe_applied_sections(
            saved_config,
            factor_column_applied=bool(
                not saved_config.spec_norm.get("factor_column")
                or self.norm_tab.factor_combo.findData(
                    str(saved_config.spec_norm.get("factor_column"))
                )
                >= 0
                or self.norm_tab.factor_combo.findText(
                    str(saved_config.spec_norm.get("factor_column"))
                )
                >= 0
            ),
        )
        self.status_bar.showMessage(self.tr("Preset saved: {path}").format(path=target_path))
        logger.info("Saved GUI preset to %s", target_path)
        self._refresh_preset_bar()
        return saved_config

    def _save_preset_yaml(self, *_args):
        local_preset_dir = get_local_preset_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Preset (YAML)"),
            str(local_preset_dir / "gui_preset.yaml"),
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        self._save_preset_to_path(path)

    def _reset_preset_to_defaults(self, *_args):
        default_config = self._default_app_config()
        self._apply_config_to_widgets(default_config)
        self._last_preset_apply_sections = [self.tr("Reset to defaults")]
        self._refresh_preset_bar()

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
        pipeline = MetaboAnalystPipeline(
            self.raw_data,
            source_labels,
            feature_metadata=self.raw_feature_metadata,
        )
        result = pipeline.run_pipeline(**params)
        return {
            "data": result,
            "labels": pipeline.processed_labels,
            "feature_metadata": (
                pipeline.processed_feature_metadata.copy()
                if pipeline.processed_feature_metadata is not None
                else None
            ),
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
        feature_metadata: pd.DataFrame | None = None,
        sample_info: pd.DataFrame | None = None,
    ):
        current_gui_config = self._build_current_gui_preset_config()
        active_pending_paths = self._collect_pending_preset_paths(self._active_preset_config)
        preserved_preset_config = (
            self._active_preset_config
            if self._active_preset_config is not None and active_pending_paths
            else current_gui_config
        )
        should_preserve_preset = (
            self._active_preset_config is not None
            or current_gui_config.to_dict(include_runtime=False)
            != self._default_app_config().to_dict(include_runtime=False)
        )

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
        self.raw_feature_metadata = (
            feature_metadata.reindex(df.columns).copy()
            if feature_metadata is not None
            else None
        )
        self.sample_info = sample_info.copy() if sample_info is not None else None
        self.sample_col = sample_col
        self.group_col = group_col

        self.undo_stack.clear()
        self._filtered_data = None
        self._filtered_labels = None
        self._stage = 1
        self._update_tab_states()

        self._on_data_state_changed()

        with self._suspend_preset_tracking():
            if hasattr(self.mv_tab, "on_data_loaded"):
                self.mv_tab.on_data_loaded()
            if hasattr(self.filter_tab, "on_data_updated"):
                self.filter_tab.on_data_updated()
            if hasattr(self.norm_tab, "on_data_updated"):
                self.norm_tab.on_data_updated()
            if hasattr(self.stats_tab, "_refresh_groups"):
                self.stats_tab._refresh_groups()

        if should_preserve_preset:
            self._apply_config_to_widgets(preserved_preset_config)
        else:
            with self._suspend_preset_tracking():
                self.pipeline_params = self._default_pipeline_params()
                self._apply_pipeline_params_to_widgets()

        msg = self.tr("Loaded {n_samples} samples and {n_features} features").format(
            n_samples=df.shape[0], n_features=df.shape[1]
        )
        self.status_bar.showMessage(msg)
        logger.info(msg)

        self._nav_list.setCurrentRow(1)
        self._refresh_preset_bar()

    def update_data(
        self,
        df: pd.DataFrame,
        source_tab: str,
        step_key: str | None = None,
        labels=None,
    ):
        old_df = self.current_data.copy() if self.current_data is not None else None
        old_labels = self.labels.copy() if self.labels is not None else None
        old_stage = self._stage

        if labels is not None:
            if isinstance(labels, pd.Series):
                new_labels = labels.copy()
            else:
                new_labels = pd.Series(labels, index=df.index)
        else:
            new_labels = self.labels

        stage_map = {"missing": 2, "filter": 3, "norm": 4}
        new_stage = (
            max(self._stage, stage_map[step_key]) if step_key in stage_map else self._stage
        )

        cmd = ProcessingStepCommand(
            self,
            source_tab,
            df,
            old_df,
            new_labels=new_labels,
            old_labels=old_labels,
            new_stage=new_stage,
            old_stage=old_stage,
        )
        # push() calls cmd.redo() internally, which sets
        # current_data, labels, and _stage on self.
        self.undo_stack.push(cmd)

        if step_key == "filter":
            self._filtered_data = df.copy()
            self._filtered_labels = new_labels.copy() if new_labels is not None else None

        self._update_tab_states()

        next_tab_map = {"missing": 2, "filter": 3, "norm": 4}
        if step_key in next_tab_map:
            next_idx = next_tab_map[step_key]
            item = self._nav_list.item(next_idx)
            if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                self._nav_list.setCurrentRow(next_idx)

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
        self.cancel_button.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

    def set_progress(self, value: int, maximum: int = 100):
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)

    def _on_cancel_clicked(self):
        if hasattr(self.stats_tab, "cancel_running"):
            self.stats_tab.cancel_running()

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

        self.theme_manager.set_theme(theme)
        logger.info("Theme switched to %s", theme)

        self.switch_language(locale)

    def _load_config_yaml(self, *_args):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Load Config (YAML)"),
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        try:
            config = load_yaml_config(path, require_required_sections=False)
            self._load_preset_config(config, path)
        except Exception as exc:
            QMessageBox.warning(
                self, self.tr("Load Error"), str(exc)
            )

    def _set_font_size(self, size: int):
        app = QApplication.instance()
        if app is not None:
            apply_flat_theme(app, self._current_theme, size)
        self._settings.setValue("font_size", size)
        self.status_bar.showMessage(
            self.tr("Font size set to {size}pt").format(size=size)
        )
        logger.info("Font size changed to %dpt", size)

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
