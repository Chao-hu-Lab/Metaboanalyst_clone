"""
蝯梯????? ??PCA (2D+3D) / PLS-DA / Volcano / ANOVA / ROC / ?賊???/ RF / ?Ｙ黎?菜葫
"""

import math
from itertools import combinations
from typing import Any, Callable, Mapping

import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QSplitter,
    QAbstractItemView,
    QFileDialog, QScrollArea, QFrame, QStackedWidget,
)
from PySide6.QtCore import Qt, QThreadPool

from core.qc import align_labels_to_data, exclude_qc_samples
from gui.state_binding import ApplyStateResult, apply_checked, apply_combo_data, apply_spin_value
from gui.widgets.mpl_canvas import MplWidget
from gui.widgets.plotly_widget import PlotlyWidget
from gui.widgets.worker import PipelineWorker


class StatsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._responsive_splitters: list[tuple[QSplitter, QWidget]] = []
        self._pca_result = None
        self._plsda_result = None
        self._volcano_result = None
        self._anova_result = None
        self._anova_annotation_method: str | None = None
        self._roc_result = None
        self._corr_result = None
        self._rf_result = None
        self._outlier_result = None
        self._oplsda_result = None
        self._clustering_result = None
        self._anova_plot_data = None
        self._anova_plot_labels = None
        self._outlier_labels = None
        self._volcano_feature_to_row: dict[str, int] = {}
        self._volcano_selection_syncing = False
        self._active_workers: set[PipelineWorker] = set()
        self._current_worker: PipelineWorker | None = None
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

        self.context_group = QFrame(self)
        self.context_group.setObjectName("stats_context_group")
        context_layout = QHBoxLayout(self.context_group)
        context_layout.setContentsMargins(12, 10, 12, 10)
        context_layout.setSpacing(18)

        self.context_groups_label = QLabel(self.tr("Groups:"))
        self.context_groups_label.setObjectName("stats_context_label")
        context_layout.addWidget(self.context_groups_label)

        self.context_groups_value = QLabel("")
        self.context_groups_value.setObjectName("stats_context_value")
        self.context_groups_value.setWordWrap(True)
        context_layout.addWidget(self.context_groups_value, stretch=2)

        self.context_shape_label = QLabel(self.tr("Samples / Features:"))
        self.context_shape_label.setObjectName("stats_context_label")
        context_layout.addWidget(self.context_shape_label)

        self.context_shape_value = QLabel("")
        self.context_shape_value.setObjectName("stats_context_value")
        context_layout.addWidget(self.context_shape_value, stretch=1)

        self.context_matrix_label = QLabel(self.tr("Matrix type:"))
        self.context_matrix_label.setObjectName("stats_context_label")
        context_layout.addWidget(self.context_matrix_label)

        self.context_matrix_value = QLabel("")
        self.context_matrix_value.setObjectName("stats_context_value")
        context_layout.addWidget(self.context_matrix_value, stretch=1)

        layout.addWidget(self.context_group)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.currentChanged.connect(lambda *_: self._refresh_analysis_context())
        self.sub_tabs.addTab(self._wrap_subtab_panel(self._build_pca_panel()), self.tr("PCA"))
        self.sub_tabs.addTab(self._wrap_subtab_panel(self._build_pca3d_panel()), self.tr("3D PCA"))
        self.sub_tabs.addTab(self._wrap_subtab_panel(self._build_plsda_panel()), self.tr("PLS-DA / VIP"))
        self.sub_tabs.addTab(
            self._wrap_subtab_panel(self._build_volcano_panel()),
            self.tr("Volcano (t-test + FC)"),
        )
        self.sub_tabs.addTab(self._wrap_subtab_panel(self._build_anova_panel()), self.tr("ANOVA"))
        self.sub_tabs.addTab(self._wrap_subtab_panel(self._build_roc_panel()), self.tr("ROC"))
        self.sub_tabs.addTab(
            self._wrap_subtab_panel(self._build_corr_panel()),
            self.tr("Correlation"),
        )
        self.sub_tabs.addTab(
            self._wrap_subtab_panel(self._build_rf_panel()),
            self.tr("Random Forest"),
        )
        self.sub_tabs.addTab(
            self._wrap_subtab_panel(self._build_outlier_panel()),
            self.tr("Outlier"),
        )
        self.sub_tabs.addTab(
            self._wrap_subtab_panel(self._build_oplsda_panel()),
            self.tr("OPLS-DA"),
        )
        self.sub_tabs.addTab(
            self._wrap_subtab_panel(self._build_clustering_panel()),
            self.tr("Clustering"),
        )
        layout.addWidget(self.sub_tabs)
        self._refresh_analysis_context()

    def _wrap_subtab_panel(self, panel: QWidget) -> QScrollArea:
        scroll = QScrollArea(self)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        return scroll

    def _register_result_splitter(self, splitter: QSplitter, side_panel: QWidget) -> None:
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 5)
        if splitter.count() > 1:
            splitter.setStretchFactor(splitter.count() - 1, 1)
        side_panel.setVisible(False)
        self._responsive_splitters.append((splitter, side_panel))

    def _show_result_panel(self, side_panel: QWidget, splitter: QSplitter) -> None:
        side_panel.setVisible(True)
        self._apply_responsive_splitters()
        if splitter.count() == 3 and splitter is getattr(self, "anova_splitter", None):
            if splitter.orientation() == Qt.Orientation.Horizontal:
                splitter.setSizes([760, 260, 220])
            else:
                splitter.setSizes([420, 260, 180])
        elif splitter.orientation() == Qt.Orientation.Horizontal:
            splitter.setSizes([820, 220])
        else:
            splitter.setSizes([560, 160])

    def _apply_responsive_splitters(self) -> None:
        narrow = self.width() < 1080
        for splitter, side_panel in self._responsive_splitters:
            splitter.setOrientation(
                Qt.Orientation.Vertical if narrow else Qt.Orientation.Horizontal
            )
            if side_panel.isVisible():
                if splitter.count() == 3 and splitter is getattr(self, "anova_splitter", None):
                    if narrow:
                        splitter.setSizes([420, 260, 180])
                    else:
                        splitter.setSizes([760, 260, 220])
                elif narrow:
                    splitter.setSizes([560, 160])
                else:
                    splitter.setSizes([820, 220])
            else:
                if splitter.count() == 3 and splitter is getattr(self, "anova_splitter", None):
                    splitter.setSizes([3, 2, 0])
                else:
                    splitter.setSizes([1, 0])

    def _show_canvas_placeholder(self, canvas: MplWidget, message: str) -> None:
        fig = canvas.figure
        fig.clear()
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", wrap=True, fontsize=11)
        ax.set_axis_off()
        canvas.draw()

    @staticmethod
    def _mark_primary_action(button: QPushButton) -> QPushButton:
        button.setProperty("variant", "primary")
        return button

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_splitters()

    def retranslateUi(self):
        if not hasattr(self, "sub_tabs"):
            return
        self.context_groups_label.setText(self.tr("Groups:"))
        self.context_shape_label.setText(self.tr("Samples / Features:"))
        self.context_matrix_label.setText(self.tr("Matrix type:"))
        tab_titles = [
            self.tr("PCA"), self.tr("3D PCA"), self.tr("PLS-DA / VIP"),
            self.tr("Volcano (t-test + FC)"), self.tr("ANOVA"), self.tr("ROC"),
            self.tr("Correlation"), self.tr("Random Forest"),
            self.tr("Outlier"), self.tr("OPLS-DA"), self.tr("Clustering"),
        ]
        for i, title in enumerate(tab_titles):
            if i < self.sub_tabs.count():
                self.sub_tabs.setTabText(i, title)
        self._refresh_analysis_context()

    def connect_state_changed(self, callback: Callable[..., None]) -> None:
        self.pca_ncomp.valueChanged.connect(callback)
        self.pca_label_mode.currentIndexChanged.connect(callback)
        self.pls_ncomp.valueChanged.connect(callback)
        self.pls_label_mode.currentIndexChanged.connect(callback)
        self.vip_topn.valueChanged.connect(callback)
        self.vol_fc.valueChanged.connect(callback)
        self.vol_p.valueChanged.connect(callback)
        self.vol_test.currentIndexChanged.connect(callback)
        self.vol_fdr.toggled.connect(callback)
        self.anova_p.valueChanged.connect(callback)
        self.anova_test.currentIndexChanged.connect(callback)
        self.anova_fdr.toggled.connect(callback)
        self.oplsda_label_mode.currentIndexChanged.connect(callback)

    def read_state(self) -> dict[str, Any]:
        pca_state: dict[str, Any] = {"n_components": int(self.pca_ncomp.value())}
        if self.pca_label_mode.currentData() != "outlier":
            pca_state["score_label_mode"] = self.pca_label_mode.currentData()

        plsda_state: dict[str, Any] = {
            "n_components": int(self.pls_ncomp.value()),
            "top_vip": int(self.vip_topn.value()),
        }
        if self.pls_label_mode.currentData() != "outlier":
            plsda_state["score_label_mode"] = self.pls_label_mode.currentData()

        analysis_state: dict[str, Any] = {
            "pca": pca_state,
            "plsda": plsda_state,
            "volcano": {
                "fc_thresh": float(self.vol_fc.value()),
                "log2_fc_thresh": float(math.log2(self.vol_fc.value())),
                "p_thresh": float(self.vol_p.value()),
                "use_fdr": bool(self.vol_fdr.isChecked()),
                "test": self.vol_test.currentData(),
            },
            "anova": {
                "p_thresh": float(self.anova_p.value()),
                "nonpar": self.anova_test.currentData() == "kruskal",
                "use_fdr": bool(self.anova_fdr.isChecked()),
            },
        }
        if self.vol_test.currentData() in {"student", "welch"}:
            analysis_state["volcano"]["parametric_test_default"] = self.vol_test.currentData()
        if self.oplsda_label_mode.currentData() != "outlier":
            analysis_state["oplsda"] = {
                "score_label_mode": self.oplsda_label_mode.currentData(),
            }

        return {
            "analysis": analysis_state
        }

    def validate_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        result = ApplyStateResult()
        analysis = state.get("analysis", {})
        if not isinstance(analysis, Mapping):
            return result

        anova = analysis.get("anova", {})
        if isinstance(anova, Mapping):
            nonpar = anova.get("nonpar")
            if nonpar is not None and not isinstance(nonpar, bool):
                result.unsupported_paths.append("analysis.anova.nonpar")
        return result

    def apply_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        result = self.validate_state(state)
        analysis = state.get("analysis", {})
        if not isinstance(analysis, Mapping):
            return result

        pca = analysis.get("pca", {})
        if isinstance(pca, Mapping) and "n_components" in pca:
            apply_spin_value(self.pca_ncomp, int(pca["n_components"]))
        if isinstance(pca, Mapping) and "score_label_mode" in pca:
            result.extend(
                apply_combo_data(
                    self.pca_label_mode,
                    pca["score_label_mode"],
                    "analysis.pca.score_label_mode",
                )
            )

        plsda = analysis.get("plsda", {})
        if isinstance(plsda, Mapping):
            if "n_components" in plsda:
                apply_spin_value(self.pls_ncomp, int(plsda["n_components"]))
            if "top_vip" in plsda:
                apply_spin_value(self.vip_topn, int(plsda["top_vip"]))
            if "score_label_mode" in plsda:
                result.extend(
                    apply_combo_data(
                        self.pls_label_mode,
                        plsda["score_label_mode"],
                        "analysis.plsda.score_label_mode",
                    )
                )

        volcano = analysis.get("volcano", {})
        if isinstance(volcano, Mapping):
            if "fc_thresh" in volcano:
                apply_spin_value(self.vol_fc, float(volcano["fc_thresh"]))
            if "p_thresh" in volcano:
                apply_spin_value(self.vol_p, float(volcano["p_thresh"]))
            if "use_fdr" in volcano:
                apply_checked(self.vol_fdr, bool(volcano["use_fdr"]))
            if "test" in volcano:
                result.extend(
                    apply_combo_data(
                        self.vol_test,
                        volcano["test"],
                        "analysis.volcano.test",
                    )
                )
            elif "parametric_test_default" in volcano:
                result.extend(
                    apply_combo_data(
                        self.vol_test,
                        volcano["parametric_test_default"],
                        "analysis.volcano.parametric_test_default",
                    )
                )

        anova = analysis.get("anova", {})
        if isinstance(anova, Mapping):
            if "p_thresh" in anova:
                apply_spin_value(self.anova_p, float(anova["p_thresh"]))
            if isinstance(anova.get("nonpar"), bool):
                target = "kruskal" if anova["nonpar"] else "anova"
                result.extend(
                    apply_combo_data(self.anova_test, target, "analysis.anova.nonpar")
                )
            if "use_fdr" in anova:
                apply_checked(self.anova_fdr, bool(anova["use_fdr"]))

        oplsda = analysis.get("oplsda", {})
        if isinstance(oplsda, Mapping) and "score_label_mode" in oplsda:
            result.extend(
                apply_combo_data(
                    self.oplsda_label_mode,
                    oplsda["score_label_mode"],
                    "analysis.oplsda.score_label_mode",
                )
            )

        return result

    def _build_score_label_mode_combo(self, callback: Callable[..., None]) -> QComboBox:
        combo = QComboBox()
        combo.addItem(self.tr("Outliers"), "outlier")
        combo.addItem(self.tr("All Samples"), "all")
        combo.addItem(self.tr("None"), "none")
        combo.currentIndexChanged.connect(callback)
        return combo

    def _snapshot_data(self):
        if self.mw.current_data is None:
            return pd.DataFrame(), None
        data = self.mw.current_data.copy()
        labels = self.mw.labels
        if labels is not None and hasattr(labels, "copy"):
            labels = labels.copy()
        return data, labels

    def _current_matrix_key(self) -> str:
        current_index = self.sub_tabs.currentIndex() if hasattr(self, "sub_tabs") else 0
        if current_index == 3:
            return "volcano"
        if current_index in {4, 5, 6}:
            return "univariate"
        return "multivariate"

    def _current_matrix_label(self) -> str:
        key = self._current_matrix_key()
        if key == "volcano":
            return self.tr("Univariate matrix + FC matrix")
        if key == "univariate":
            return self.tr("Statistics matrix")
        return self.tr("Multivariate matrix")

    def _analysis_context_snapshot(self) -> tuple[pd.DataFrame | None, pd.Series | None]:
        bundle = self.mw.get_stats_matrix_bundle()
        if isinstance(bundle, Mapping):
            labels = bundle.get("labels")
            matrix_key = self._current_matrix_key()
            if matrix_key == "volcano":
                data = bundle.get("univariate_data")
            elif matrix_key == "univariate":
                data = bundle.get("univariate_data")
            else:
                data = bundle.get("multivariate_data")
            if isinstance(data, pd.DataFrame):
                aligned_labels = align_labels_to_data(data, labels)
                if aligned_labels is not None:
                    data = data.reindex(aligned_labels.index)
                return data.copy(), aligned_labels

        data, labels = self._snapshot_data()
        labels = align_labels_to_data(data, labels)
        filtered_data, filtered_labels, _ = exclude_qc_samples(data, labels)
        return filtered_data, filtered_labels

    def _refresh_analysis_context(self) -> None:
        if not hasattr(self, "context_groups_value"):
            return

        data, labels = self._analysis_context_snapshot()
        if data is None or data.empty:
            self.context_groups_value.setText(self.tr("No group labels"))
            self.context_shape_value.setText(self.tr("No dataset loaded"))
            self.context_matrix_value.setText(self._current_matrix_label())
            return

        if labels is None or len(labels) == 0:
            group_text = self.tr("No group labels")
        else:
            counts = labels.astype(str).value_counts()
            group_text = ", ".join(f"{group}:{count}" for group, count in counts.items())

        self.context_groups_value.setText(group_text)
        self.context_shape_value.setText(
            self.tr("{samples} / {features}").format(
                samples=data.shape[0],
                features=data.shape[1],
            )
        )
        self.context_matrix_value.setText(self._current_matrix_label())

    @staticmethod
    def _refresh_group_pair(
        combo_a: QComboBox,
        combo_b: QComboBox,
        groups: list[str],
    ) -> None:
        previous_a = combo_a.currentText()
        previous_b = combo_b.currentText()

        for combo in (combo_a, combo_b):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(groups)

        if groups:
            selected_a = previous_a if previous_a in groups else groups[0]
            fallback_b = groups[1] if len(groups) > 1 else groups[0]
            selected_b = previous_b if previous_b in groups and previous_b != selected_a else fallback_b
            if selected_b == selected_a and len(groups) > 1:
                selected_b = next((group for group in groups if group != selected_a), fallback_b)
            combo_a.setCurrentIndex(max(combo_a.findText(selected_a), 0))
            combo_b.setCurrentIndex(max(combo_b.findText(selected_b), 0))

        for combo in (combo_a, combo_b):
            combo.blockSignals(False)

    def _available_groups(self) -> list[str]:
        if self.mw.labels is None or self.mw.current_data is None:
            return []
        labels = align_labels_to_data(self.mw.current_data, self.mw.labels)
        _, labels_no_qc, _ = exclude_qc_samples(self.mw.current_data, labels)
        if labels_no_qc is None:
            return []
        return sorted(set(labels_no_qc.astype(str)))

    @staticmethod
    def _build_group_pairs(groups: list[str]) -> list[tuple[str, str]]:
        return [(str(left), str(right)) for left, right in combinations(groups, 2)]

    @staticmethod
    def _sync_pair_combo(
        pair_combo: QComboBox,
        hidden_a: QComboBox,
        hidden_b: QComboBox,
        groups: list[str],
    ) -> None:
        previous_pair = pair_combo.currentData()
        pairs = StatsTab._build_group_pairs(groups)

        pair_combo.blockSignals(True)
        hidden_a.blockSignals(True)
        hidden_b.blockSignals(True)

        pair_combo.clear()
        hidden_a.clear()
        hidden_b.clear()
        hidden_a.addItems(groups)
        hidden_b.addItems(groups)

        for left, right in pairs:
            pair_combo.addItem(f"{left} vs {right}", (left, right))

        selected_pair = previous_pair if previous_pair in pairs else (pairs[0] if pairs else None)
        if selected_pair is not None:
            pair_combo.setCurrentIndex(max(pair_combo.findText(f"{selected_pair[0]} vs {selected_pair[1]}"), 0))
            hidden_a.setCurrentIndex(max(hidden_a.findText(selected_pair[0]), 0))
            hidden_b.setCurrentIndex(max(hidden_b.findText(selected_pair[1]), 0))

        hidden_a.blockSignals(False)
        hidden_b.blockSignals(False)
        pair_combo.blockSignals(False)

    @staticmethod
    def _selected_pair(pair_combo: QComboBox) -> tuple[str, str] | None:
        pair = pair_combo.currentData()
        if isinstance(pair, tuple) and len(pair) == 2:
            return str(pair[0]), str(pair[1])
        return None

    @staticmethod
    def _sync_display_group_combo(combo: QComboBox, groups: list[str]) -> None:
        previous = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(combo.tr("All groups"), None)
        for group in groups:
            combo.addItem(str(group), str(group))
        index = combo.findData(previous)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _current_theme(self) -> str:
        theme_manager = getattr(self.mw, "theme_manager", None)
        return getattr(theme_manager, "current_theme", "light")

    def _resolve_anova_annotation_method(
        self,
        labels: pd.Series | None,
        result: Any | None = None,
    ) -> str | None:
        if labels is None:
            return None

        labels_arr = labels.values if hasattr(labels, "values") else pd.Series(labels).to_numpy()
        n_groups = len(set(labels_arr.astype(str)))
        method_key = str(getattr(result, "method_key", "anova")).lower() if result is not None else "anova"

        if method_key == "kruskal":
            return "mannwhitney" if n_groups == 2 else "kruskal"
        if method_key == "anova":
            return "anova"
        return None

    def _snapshot_stats_matrix_bundle(
        self,
        require_labels: bool = False,
    ) -> tuple[dict[str, Any], pd.Series | None, dict[str, int]]:
        bundle = self.mw.get_stats_matrix_bundle()
        if isinstance(bundle, Mapping):
            multivariate = bundle["multivariate_data"].copy()
            univariate = bundle["univariate_data"].copy()
            volcano_fc = bundle["volcano_fc_data"].copy()
            labels = bundle.get("labels")
            labels = align_labels_to_data(multivariate, labels)

            if require_labels and labels is None:
                raise ValueError(self.tr("Group labels are required for this analysis."))

            if labels is not None:
                multivariate = multivariate.reindex(labels.index)
                univariate = univariate.reindex(labels.index)
                volcano_fc = volcano_fc.reindex(labels.index)

            meta = {
                "removed_qc": int(bundle.get("removed_qc", 0)),
                "n_samples": int(multivariate.shape[0]),
            }
            return {
                "multivariate_data": multivariate,
                "univariate_data": univariate,
                "volcano_fc_data": volcano_fc,
            }, labels, meta

        data, labels = self._snapshot_data()
        labels = align_labels_to_data(data, labels)

        if require_labels and labels is None:
            raise ValueError(self.tr("Group labels are required for this analysis."))

        filtered_data, filtered_labels, removed_qc = exclude_qc_samples(data, labels)
        meta = {
            "removed_qc": removed_qc,
            "n_samples": int(filtered_data.shape[0]),
        }
        fallback_bundle = {
            "multivariate_data": filtered_data,
            "univariate_data": filtered_data.copy(),
            "volcano_fc_data": filtered_data.copy(),
        }
        return fallback_bundle, filtered_labels, meta

    def _snapshot_stats_data(self, require_labels: bool = False):
        bundle, labels, meta = self._snapshot_stats_matrix_bundle(require_labels=require_labels)
        return bundle["multivariate_data"], labels, meta

    def _snapshot_univariate_stats_data(self, require_labels: bool = False):
        bundle, labels, meta = self._snapshot_stats_matrix_bundle(require_labels=require_labels)
        return bundle["univariate_data"], labels, meta

    def _snapshot_volcano_inputs(self, require_labels: bool = False):
        bundle, labels, meta = self._snapshot_stats_matrix_bundle(require_labels=require_labels)
        return bundle["univariate_data"], bundle["volcano_fc_data"], labels, meta

    def _qc_scope_text(self, removed_qc: int) -> str:
        if removed_qc > 0:
            return self.tr("QC excluded from downstream statistics: {n} sample(s).").format(
                n=removed_qc
            )
        return self.tr("QC excluded from downstream statistics: none detected.")

    def _snapshot_stats_data_or_warn(self, require_labels: bool = False):
        try:
            return self._snapshot_stats_data(require_labels=require_labels)
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Warning"), str(exc))
            return None, None, None

    def _snapshot_univariate_stats_data_or_warn(self, require_labels: bool = False):
        try:
            return self._snapshot_univariate_stats_data(require_labels=require_labels)
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Warning"), str(exc))
            return None, None, None

    def _snapshot_volcano_inputs_or_warn(self, require_labels: bool = False):
        try:
            return self._snapshot_volcano_inputs(require_labels=require_labels)
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Warning"), str(exc))
            return None, None, None, None

    def _run_async(self, job_fn, on_success, error_title: str):
        if self._busy:
            self.mw.status_bar.showMessage(self.tr("Another analysis is running. Please wait."))
            return

        self._busy = True
        self.sub_tabs.setEnabled(False)
        self.mw.show_progress(True)

        worker = PipelineWorker(job_fn)
        self._active_workers.add(worker)
        self._current_worker = worker

        def _handle_result(payload):
            try:
                on_success(payload)
            except Exception as exc:
                QMessageBox.critical(self, error_title, str(exc))

        def _handle_error(error_text: str):
            if error_text == "Cancelled":
                self.mw.status_bar.showMessage(self.tr("Analysis cancelled."))
            else:
                QMessageBox.critical(self, error_title, error_text)

        def _handle_finished():
            self._busy = False
            self._current_worker = None
            self.sub_tabs.setEnabled(True)
            self.mw.show_progress(False)
            self._active_workers.discard(worker)

        worker.signals.result.connect(_handle_result)
        worker.signals.error.connect(_handle_error)
        worker.signals.finished.connect(_handle_finished)
        QThreadPool.globalInstance().start(worker)

    def cancel_running(self):
        """Cancel the currently running analysis, if any."""
        if self._current_worker is not None:
            self._current_worker.cancel()
            self.mw.status_bar.showMessage(self.tr("Cancelling..."))

    # ?????????????????? PCA 2D ??????????????????

    def _build_pca_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Components:")))
        self.pca_ncomp = QSpinBox()
        self.pca_ncomp.setRange(2, 20)
        self.pca_ncomp.setValue(5)
        ctrl.addWidget(self.pca_ncomp)

        ctrl.addWidget(QLabel(self.tr("PC X:")))
        self.pca_pcx = QSpinBox()
        self.pca_pcx.setRange(1, 20)
        self.pca_pcx.setValue(1)
        ctrl.addWidget(self.pca_pcx)

        ctrl.addWidget(QLabel(self.tr("PC Y:")))
        self.pca_pcy = QSpinBox()
        self.pca_pcy.setRange(1, 20)
        self.pca_pcy.setValue(2)
        ctrl.addWidget(self.pca_pcy)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run PCA")))
        btn_run.clicked.connect(self._run_pca)
        ctrl.addWidget(btn_run)

        ctrl.addWidget(QLabel(self.tr("Plot:")))
        self.pca_plot_type = QComboBox()
        self.pca_plot_type.addItem(self.tr("Score Plot"), "score")
        self.pca_plot_type.addItem(self.tr("Scree Plot"), "scree")
        self.pca_plot_type.addItem(self.tr("Loading Plot"), "loading")
        self.pca_plot_type.currentIndexChanged.connect(self._update_pca_plot)
        ctrl.addWidget(self.pca_plot_type)

        ctrl.addWidget(QLabel(self.tr("Labels:")))
        self.pca_label_mode = self._build_score_label_mode_combo(self._update_pca_plot)
        ctrl.addWidget(self.pca_label_mode)

        btn_save = QPushButton(self.tr("Export"))
        btn_save.clicked.connect(self._export_pca_view)
        ctrl.addWidget(btn_save)

        layout.addLayout(ctrl)

        self.pca_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.pca_plot_stack = QStackedWidget()
        self.pca_canvas = MplWidget()
        self.pca_plotly_widget = PlotlyWidget()
        self.pca_plot_stack.addWidget(self.pca_canvas)
        self.pca_plot_stack.addWidget(self.pca_plotly_widget)
        self.pca_plot_stack.setCurrentWidget(self.pca_canvas)
        self.pca_splitter.addWidget(self.pca_plot_stack)
        self.pca_info = QTextEdit()
        self.pca_info.setReadOnly(True)
        self.pca_info.setMaximumWidth(300)
        self.pca_splitter.addWidget(self.pca_info)
        self._register_result_splitter(self.pca_splitter, self.pca_info)
        self._show_canvas_placeholder(
            self.pca_canvas,
            self.tr("Run PCA to inspect score, scree, or loading plots here."),
        )
        layout.addWidget(self.pca_splitter, stretch=1)
        return w

    def _run_pca(self):
        if not self.mw.check_data_ready():
            return
        from analysis.pca import run_pca

        n = self.pca_ncomp.value()
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=False)
        if qc_meta is None:
            return

        def _job():
            return run_pca(data, labels, n_components=n)

        def _on_success(result):
            self._pca_result = result
            var = result.explained_variance_ratio
            lines = [self.tr("=== PCA Results ==="), ""]
            for i, v in enumerate(var):
                lines.append(f"PC{i+1}: {v*100:.2f}%")
            lines.append(self.tr("Cumulative: {pct}%").format(pct=f"{sum(var)*100:.2f}"))
            lines.append(self._qc_scope_text(qc_meta["removed_qc"]))
            self.pca_info.setPlainText("\n".join(lines))
            self._show_result_panel(self.pca_info, self.pca_splitter)
            self._update_pca_plot()

        self._run_async(_job, _on_success, self.tr("PCA Error"))

    def _update_pca_plot(self):
        if self._pca_result is None:
            return
        from visualization.pca_plot import (
            plot_pca_loading,
            plot_pca_score,
            plot_pca_score_interactive,
            plot_pca_scree,
        )

        plot_key = self.pca_plot_type.currentData()

        if plot_key == "score":
            interactive_fig = plot_pca_score_interactive(
                self._pca_result,
                pc_x=self.pca_pcx.value() - 1,
                pc_y=self.pca_pcy.value() - 1,
                show_labels=self.pca_label_mode.currentData(),
                theme=self._current_theme(),
            )
            if interactive_fig is not None:
                self.pca_plotly_widget.show_figure(interactive_fig, enable_selection_bridge=True)
                self.pca_plot_stack.setCurrentWidget(self.pca_plotly_widget)
                return

            fig = self.pca_canvas.figure
            plot_pca_score(
                self._pca_result,
                pc_x=self.pca_pcx.value() - 1,
                pc_y=self.pca_pcy.value() - 1,
                show_labels=self.pca_label_mode.currentData(),
                theme=self._current_theme(),
                fig=fig,
            )
        elif plot_key == "scree":
            fig = self.pca_canvas.figure
            plot_pca_scree(self._pca_result, theme=self._current_theme(), fig=fig)
        elif plot_key == "loading":
            fig = self.pca_canvas.figure
            plot_pca_loading(
                self._pca_result,
                pc=self.pca_pcx.value() - 1,
                theme=self._current_theme(),
                fig=fig,
            )
        self.pca_plot_stack.setCurrentWidget(self.pca_canvas)
        self.pca_canvas.draw()
        self.mw.show_shared_plot(self.pca_canvas.figure)

    # ?????????????????? 3D PCA ??????????????????

    def _build_pca3d_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("PC X:")))
        self.pca3d_x = QSpinBox()
        self.pca3d_x.setRange(1, 20)
        self.pca3d_x.setValue(1)
        ctrl.addWidget(self.pca3d_x)
        ctrl.addWidget(QLabel(self.tr("PC Y:")))
        self.pca3d_y = QSpinBox()
        self.pca3d_y.setRange(1, 20)
        self.pca3d_y.setValue(2)
        ctrl.addWidget(self.pca3d_y)
        ctrl.addWidget(QLabel(self.tr("PC Z:")))
        self.pca3d_z = QSpinBox()
        self.pca3d_z.setRange(1, 20)
        self.pca3d_z.setValue(3)
        ctrl.addWidget(self.pca3d_z)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run 3D PCA")))
        btn_run.clicked.connect(self._run_pca3d)
        ctrl.addWidget(btn_run)

        btn_html = QPushButton(self.tr("Export HTML"))
        btn_html.clicked.connect(self._save_pca3d_html)
        ctrl.addWidget(btn_html)
        layout.addLayout(ctrl)

        self.pca3d_widget = PlotlyWidget()
        layout.addWidget(self.pca3d_widget, stretch=1)
        return w

    def _run_pca3d(self):
        if not self.mw.check_data_ready():
            return
        max_pc = max(self.pca3d_x.value(), self.pca3d_y.value(), self.pca3d_z.value())

        if self._pca_result is not None and self._pca_result.n_components >= max_pc:
            self._render_pca3d(self._pca_result)
            return

        from analysis.pca import run_pca
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=False)
        if qc_meta is None:
            return

        def _job():
            return run_pca(data, labels, n_components=max_pc)

        def _on_success(result):
            self._pca_result = result
            self._render_pca3d(result)

        self._run_async(_job, _on_success, self.tr("3D PCA Error"))

    def _render_pca3d(self, pca_result):
        from visualization.pca_3d import plot_pca_3d
        fig = plot_pca_3d(
            pca_result,
            pc_x=self.pca3d_x.value()-1,
            pc_y=self.pca3d_y.value()-1,
            pc_z=self.pca3d_z.value()-1,
            theme=self._current_theme(),
        )
        if fig is not None:
            self.pca3d_widget.show_figure(fig)
        else:
            QMessageBox.warning(self, self.tr("Warning"),
                                self.tr("Plotly is required: pip install plotly"))

    def _save_pca3d_html(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export 3D PCA"), "pca_3d.html", "HTML (*.html)"
        )
        if path:
            self.pca3d_widget.save_html(path)

    # ?????????????????? PLS-DA ??????????????????

    def _build_plsda_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Components:")))
        self.pls_ncomp = QSpinBox()
        self.pls_ncomp.setRange(1, 10)
        self.pls_ncomp.setValue(3)
        ctrl.addWidget(self.pls_ncomp)

        ctrl.addWidget(QLabel(self.tr("CV method:")))
        self.pls_cv = QComboBox()
        self.pls_cv.addItem(self.tr("LOO (Leave-One-Out)"), "loo")
        self.pls_cv.addItem(self.tr("5-Fold"), "kfold5")
        ctrl.addWidget(self.pls_cv)

        ctrl.addWidget(QLabel(self.tr("VIP Top N:")))
        self.vip_topn = QSpinBox()
        self.vip_topn.setRange(5, 100)
        self.vip_topn.setValue(25)
        ctrl.addWidget(self.vip_topn)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run PLS-DA")))
        btn_run.clicked.connect(self._run_plsda)
        ctrl.addWidget(btn_run)

        self.pls_plot_type = QComboBox()
        self.pls_plot_type.addItem(self.tr("VIP Score Plot"), "vip")
        self.pls_plot_type.addItem(self.tr("Score Plot"), "score")
        self.pls_plot_type.currentIndexChanged.connect(self._update_plsda_plot)
        ctrl.addWidget(self.pls_plot_type)

        ctrl.addWidget(QLabel(self.tr("Labels:")))
        self.pls_label_mode = self._build_score_label_mode_combo(self._update_plsda_plot)
        ctrl.addWidget(self.pls_label_mode)

        btn_save = QPushButton(self.tr("Export"))
        btn_save.clicked.connect(self._export_plsda_view)
        ctrl.addWidget(btn_save)

        layout.addLayout(ctrl)

        self.pls_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.pls_plot_stack = QStackedWidget()
        self.pls_canvas = MplWidget()
        self.pls_plotly_widget = PlotlyWidget()
        self.pls_plot_stack.addWidget(self.pls_canvas)
        self.pls_plot_stack.addWidget(self.pls_plotly_widget)
        self.pls_plot_stack.setCurrentWidget(self.pls_canvas)
        self.pls_splitter.addWidget(self.pls_plot_stack)

        self.pls_side_panel = QWidget()
        right_layout = QVBoxLayout(self.pls_side_panel)
        self.pls_info = QTextEdit()
        self.pls_info.setReadOnly(True)
        self.pls_info.setMaximumHeight(120)
        right_layout.addWidget(self.pls_info)
        self.vip_table = QTableWidget()
        right_layout.addWidget(self.vip_table)
        self.pls_side_panel.setMaximumWidth(350)
        self.pls_splitter.addWidget(self.pls_side_panel)
        self._register_result_splitter(self.pls_splitter, self.pls_side_panel)
        self._show_canvas_placeholder(
            self.pls_canvas,
            self.tr("Run PLS-DA to inspect VIP scores and score plots here."),
        )

        layout.addWidget(self.pls_splitter, stretch=1)
        return w

    def _run_plsda(self):
        if not self.mw.check_data_ready():
            return
        from analysis.plsda import run_plsda

        n = self.pls_ncomp.value()
        cv = self.pls_cv.currentData()
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=True)
        if qc_meta is None:
            return

        def _job():
            return run_plsda(data, labels, n_components=n, cv_method=cv)

        def _on_success(result):
            self._plsda_result = result
            lines = [self.tr("=== PLS-DA Results ===")]
            for i, v in enumerate(result.explained_variance):
                lines.append(self.tr("Comp{idx}: {pct}% explained variance").format(
                    idx=i+1, pct=f"{v*100:.2f}"))
            if result.q2 is not None:
                lines.append(f"Q2 = {result.q2:.4f}")
            n_imp = (result.vips >= 1).sum()
            lines.append(self.tr("VIP >= 1 features: {n}").format(n=n_imp))
            lines.append(self._qc_scope_text(qc_meta["removed_qc"]))
            self.pls_info.setPlainText("\n".join(lines))

            vip_df = result.get_vip_df()
            self.vip_table.setRowCount(min(50, len(vip_df)))
            self.vip_table.setColumnCount(2)
            self.vip_table.setHorizontalHeaderLabels([self.tr("Feature"), self.tr("VIP")])
            for i in range(min(50, len(vip_df))):
                self.vip_table.setItem(i, 0, QTableWidgetItem(str(vip_df.iloc[i]["Feature"])))
                self.vip_table.setItem(i, 1, QTableWidgetItem(f'{vip_df.iloc[i]["VIP"]:.4f}'))
            self.vip_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self._show_result_panel(self.pls_side_panel, self.pls_splitter)
            self._update_plsda_plot()

        self._run_async(_job, _on_success, self.tr("PLS-DA Error"))

    def _update_plsda_plot(self):
        if self._plsda_result is None:
            return
        from visualization.plsda_plot import plot_plsda_score, plot_plsda_score_interactive
        from visualization.vip_plot import plot_vip

        plot_key = self.pls_plot_type.currentData()

        if plot_key == "vip":
            fig = self.pls_canvas.figure
            _data = self.mw.current_data
            _labels = align_labels_to_data(self.mw.current_data, self.mw.labels)
            plot_vip(self._plsda_result, top_n=self.vip_topn.value(),
                     data=_data, labels=_labels, theme=self._current_theme(), fig=fig)
            self.pls_plot_stack.setCurrentWidget(self.pls_canvas)
        elif plot_key == "score":
            interactive_fig = plot_plsda_score_interactive(
                self._plsda_result,
                show_labels=self.pls_label_mode.currentData(),
                theme=self._current_theme(),
            )
            if interactive_fig is not None:
                self.pls_plotly_widget.show_figure(interactive_fig, enable_selection_bridge=True)
                self.pls_plot_stack.setCurrentWidget(self.pls_plotly_widget)
                return

            fig = self.pls_canvas.figure
            plot_plsda_score(
                self._plsda_result,
                show_labels=self.pls_label_mode.currentData(),
                theme=self._current_theme(),
                fig=fig,
            )
            self.pls_plot_stack.setCurrentWidget(self.pls_canvas)
        self.pls_canvas.draw()
        self.mw.show_shared_plot(self.pls_canvas.figure)

    # ?????????????????? Volcano ??????????????????

    def _build_volcano_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl1 = QHBoxLayout()
        ctrl1.addWidget(QLabel(self.tr("Comparison:")))
        self.vol_pair_combo = QComboBox()
        self.vol_pair_combo.setMinimumWidth(220)
        ctrl1.addWidget(self.vol_pair_combo)
        self.vol_group1 = QComboBox()
        self.vol_group2 = QComboBox()

        ctrl1.addWidget(QLabel(self.tr("FC threshold:")))
        self.vol_fc = QDoubleSpinBox()
        self.vol_fc.setRange(1.0, 10.0)
        self.vol_fc.setSingleStep(0.5)
        self.vol_fc.setValue(2.0)
        ctrl1.addWidget(self.vol_fc)

        ctrl1.addWidget(QLabel(self.tr("p threshold:")))
        self.vol_p = QDoubleSpinBox()
        self.vol_p.setRange(0.001, 0.1)
        self.vol_p.setSingleStep(0.01)
        self.vol_p.setValue(0.05)
        self.vol_p.setDecimals(3)
        ctrl1.addWidget(self.vol_p)
        layout.addLayout(ctrl1)

        ctrl2 = QHBoxLayout()
        self.vol_test = QComboBox()
        self.vol_test.addItem(self.tr("Student's t (equal variance)"), "student")
        self.vol_test.addItem(self.tr("Welch's t (unequal variance)"), "welch")
        self.vol_test.addItem(self.tr("Wilcoxon (non-parametric)"), "wilcoxon")
        self.vol_test.setCurrentIndex(max(0, self.vol_test.findData("welch")))
        ctrl2.addWidget(self.vol_test)
        self.vol_fdr = QCheckBox(self.tr("FDR correction (BH)"))
        self.vol_fdr.setChecked(True)
        ctrl2.addWidget(self.vol_fdr)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run Volcano Analysis")))
        btn_run.clicked.connect(self._run_volcano)
        ctrl2.addWidget(btn_run)

        btn_save = QPushButton(self.tr("Export Interactive HTML"))
        btn_save.clicked.connect(
            lambda: self._save_plotly_html(
                self.vol_widget,
                self.tr("Export Volcano Interactive Chart"),
                "volcano_plot.html",
            )
        )
        ctrl2.addWidget(btn_save)

        btn_csv = QPushButton(self.tr("Export Results CSV"))
        btn_csv.clicked.connect(self._export_volcano_csv)
        ctrl2.addWidget(btn_csv)
        layout.addLayout(ctrl2)

        self.vol_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.vol_widget = PlotlyWidget()
        self.vol_widget.plotly_event.connect(self._on_volcano_plotly_event)
        self.vol_splitter.addWidget(self.vol_widget)

        self.vol_side_panel = QWidget()
        rl = QVBoxLayout(self.vol_side_panel)
        self.vol_info = QLabel("")
        rl.addWidget(self.vol_info)
        self.vol_table = QTableWidget()
        self.vol_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.vol_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.vol_table.itemSelectionChanged.connect(self._sync_volcano_plot_from_table)
        rl.addWidget(self.vol_table)
        self.vol_side_panel.setMaximumWidth(400)
        self.vol_splitter.addWidget(self.vol_side_panel)
        self._register_result_splitter(self.vol_splitter, self.vol_side_panel)
        layout.addWidget(self.vol_splitter, stretch=1)
        return w

    def _refresh_groups(self):
        groups = self._available_groups()
        self._sync_pair_combo(self.vol_pair_combo, self.vol_group1, self.vol_group2, groups)
        self._sync_pair_combo(self.roc_pair_combo, self.roc_group1, self.roc_group2, groups)
        self._sync_display_group_combo(self.out_group_combo, groups)
        self._refresh_analysis_context()

    def _run_volcano(self):
        if not self.mw.check_data_ready():
            return
        self._sync_pair_combo(self.vol_pair_combo, self.vol_group1, self.vol_group2, self._available_groups())
        pair = self._selected_pair(self.vol_pair_combo)
        if pair is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("At least 2 groups are required for volcano analysis."))
            return
        g1, g2 = pair
        if self.mw.labels is None:
            return

        from analysis.univariate import volcano_analysis
        from visualization.volcano_plot import plot_volcano_interactive

        test_key = self.vol_test.currentData()
        fc_thresh = self.vol_fc.value()
        p_thresh = self.vol_p.value()
        use_fdr = self.vol_fdr.isChecked()
        data, fc_data, labels, qc_meta = self._snapshot_volcano_inputs_or_warn(
            require_labels=True
        )
        if qc_meta is None:
            return

        def _job():
            return volcano_analysis(
                data, labels,
                group1=g1, group2=g2,
                fc_thresh=fc_thresh,
                p_thresh=p_thresh,
                equal_var=(test_key == "student"),
                nonpar=(test_key == "wilcoxon"),
                use_fdr=use_fdr,
                fc_df=fc_data,
            )

        def _on_success(result):
            self._volcano_result = result
            interactive_fig = plot_volcano_interactive(
                result,
                theme=self._current_theme(),
            )
            if interactive_fig is None:
                self.vol_widget.show_html(
                    "<html><body style='font-family:sans-serif; padding:24px; color:#888;'>"
                    + self.tr("Plotly is required to render the interactive volcano chart.")
                    + "</body></html>"
                )
            else:
                self.vol_widget.show_figure(interactive_fig, enable_selection_bridge=True)

            self.vol_info.setText(
                self.tr(
                    "Method: {method} | Significant features: {n_sig} | Up: {n_up} | Down: {n_down}\n{qc_note}"
                ).format(
                    method=result.test_label,
                    n_sig=result.n_significant,
                    n_up=result.n_up,
                    n_down=result.n_down,
                    qc_note=self._qc_scope_text(qc_meta["removed_qc"]),
                )
            )

            sig_df = result.significant.sort_values("pvalue_adj")
            n_show = min(100, len(sig_df))
            self.vol_table.setRowCount(n_show)
            self.vol_table.setColumnCount(3)
            self._volcano_feature_to_row = {}
            self.vol_table.setHorizontalHeaderLabels([
                self.tr("Feature"), self.tr("log2FC"), self.tr("adj.P"),
            ])
            for i in range(n_show):
                row = sig_df.iloc[i]
                feature = str(row["Feature"])
                self._volcano_feature_to_row[feature] = i
                self.vol_table.setItem(i, 0, QTableWidgetItem(feature))
                self.vol_table.setItem(i, 1, QTableWidgetItem(f'{row["log2FC"]:.3f}'))
                self.vol_table.setItem(i, 2, QTableWidgetItem(f'{row["pvalue_adj"]:.2e}'))
            self.vol_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            if n_show:
                self._volcano_selection_syncing = True
                self.vol_table.selectRow(0)
                self._volcano_selection_syncing = False
                first_feature = self.vol_table.item(0, 0).text()
                if interactive_fig is not None:
                    self.vol_widget.highlight_feature(first_feature)
            self._show_result_panel(self.vol_side_panel, self.vol_splitter)

        self._run_async(_job, _on_success, self.tr("Volcano Error"))

    def _export_volcano_csv(self):
        if self._volcano_result is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please run Volcano analysis first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Volcano Results"), "volcano_result.csv", "CSV (*.csv)"
        )
        if path:
            self._volcano_result.result_df.to_csv(path, index=False)
            self.mw.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))

    def _on_volcano_plotly_event(self, payload: object) -> None:
        if self._volcano_selection_syncing or not isinstance(payload, Mapping):
            return
        if payload.get("type") != "point_click":
            return
        feature = str(payload.get("feature", "")).strip()
        row = self._volcano_feature_to_row.get(feature)
        if row is None:
            return

        self._volcano_selection_syncing = True
        self.vol_table.selectRow(row)
        item = self.vol_table.item(row, 0)
        if item is not None:
            self.vol_table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        self._volcano_selection_syncing = False

    def _sync_volcano_plot_from_table(self) -> None:
        if self._volcano_selection_syncing:
            return
        row = self.vol_table.currentRow()
        if row < 0:
            return
        item = self.vol_table.item(row, 0)
        if item is None:
            return

        self._volcano_selection_syncing = True
        self.vol_widget.highlight_feature(item.text())
        self._volcano_selection_syncing = False

    # ?????????????????? ANOVA ??????????????????

    def _build_anova_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("p threshold:")))
        self.anova_p = QDoubleSpinBox()
        self.anova_p.setRange(0.001, 0.1)
        self.anova_p.setSingleStep(0.01)
        self.anova_p.setValue(0.05)
        self.anova_p.setDecimals(3)
        ctrl.addWidget(self.anova_p)

        self.anova_test = QComboBox()
        self.anova_test.addItem(self.tr("ANOVA (parametric)"), "anova")
        self.anova_test.addItem(self.tr("Kruskal-Wallis (non-parametric)"), "kruskal")
        ctrl.addWidget(self.anova_test)

        self.anova_fdr = QCheckBox(self.tr("FDR correction"))
        self.anova_fdr.setChecked(True)
        ctrl.addWidget(self.anova_fdr)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run ANOVA")))
        btn_run.clicked.connect(self._run_anova)
        ctrl.addWidget(btn_run)

        btn_save = QPushButton(self.tr("Export Figure"))
        btn_save.clicked.connect(lambda: self._save_figure(self.anova_canvas))
        ctrl.addWidget(btn_save)

        btn_csv = QPushButton(self.tr("Export Results CSV"))
        btn_csv.clicked.connect(self._export_anova_csv)
        ctrl.addWidget(btn_csv)
        layout.addLayout(ctrl)

        # ?孵噩 boxplot ?批
        feat_ctrl = QHBoxLayout()
        feat_ctrl.addWidget(QLabel(self.tr("Feature:")))
        self.anova_feat_combo = QComboBox()
        self.anova_feat_combo.setMinimumWidth(200)
        self.anova_feat_combo.currentIndexChanged.connect(self._on_anova_feature_changed)
        feat_ctrl.addWidget(self.anova_feat_combo)
        feat_ctrl.addStretch()
        layout.addLayout(feat_ctrl)

        self.anova_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.anova_splitter.setChildrenCollapsible(False)
        self.anova_splitter.setStretchFactor(0, 6)
        self.anova_splitter.setStretchFactor(1, 2)
        self.anova_splitter.setStretchFactor(2, 2)

        # 撌? ???扳???
        self.anova_canvas = MplWidget(figsize=(11.5, 4.6))
        self.anova_splitter.addWidget(self.anova_canvas)

        # 銝? ?孵噩 boxplot
        self.anova_feat_canvas = MplWidget(figsize=(4.2, 4.6))
        self.anova_splitter.addWidget(self.anova_feat_canvas)

        # ?? 蝯?銵冽
        self.anova_side_panel = QWidget()
        rl = QVBoxLayout(self.anova_side_panel)
        self.anova_info = QLabel("")
        rl.addWidget(self.anova_info)
        self.anova_table = QTableWidget()
        self.anova_table.itemSelectionChanged.connect(self._sync_anova_feature_from_table)
        rl.addWidget(self.anova_table)
        self.anova_side_panel.setMaximumWidth(400)
        self.anova_splitter.addWidget(self.anova_side_panel)
        self._register_result_splitter(self.anova_splitter, self.anova_side_panel)
        self._show_canvas_placeholder(
            self.anova_canvas,
            self.tr("Run ANOVA to inspect the importance plot here."),
        )
        self._show_canvas_placeholder(
            self.anova_feat_canvas,
            self.tr("Select a feature after running ANOVA to inspect its boxplot."),
        )

        layout.addWidget(self.anova_splitter, stretch=1)
        return w

    def _run_anova(self):
        if not self.mw.check_data_ready():
            return
        data, labels_snapshot, qc_meta = self._snapshot_univariate_stats_data_or_warn(
            require_labels=True
        )
        if qc_meta is None:
            return
        n_groups = len(set(labels_snapshot.astype(str)))
        if n_groups < 2:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("At least 2 groups are required."))
            return

        from analysis.anova import run_anova
        from visualization.anova_plot import plot_anova_importance
        nonpar = self.anova_test.currentData() == "kruskal"
        use_fdr = self.anova_fdr.isChecked()
        p_thresh = self.anova_p.value()

        def _job():
            return run_anova(
                data, labels_snapshot,
                p_thresh=p_thresh,
                nonpar=nonpar,
                use_fdr=use_fdr,
            )

        def _on_success(result):
            self._anova_result = result
            self._anova_plot_data = data
            self._anova_plot_labels = labels_snapshot
            self._anova_annotation_method = self._resolve_anova_annotation_method(
                labels_snapshot,
                result,
            )
            plot_anova_importance(
                result,
                theme=self._current_theme(),
                fig=self.anova_canvas.figure,
            )
            self.anova_canvas.draw()
            self.mw.show_shared_plot(self.anova_canvas.figure)

            test_name = "Kruskal-Wallis" if nonpar else "ANOVA"
            self.anova_info.setText(
                self.tr(
                    "Test: {test}\nGroups: {n_groups} | Significant features: {n_sig}\n{qc_note}"
                ).format(
                    test=test_name,
                    n_groups=len(result.groups),
                    n_sig=result.n_significant,
                    qc_note=self._qc_scope_text(qc_meta["removed_qc"]),
                )
            )

            result_sorted = result.result_df.sort_values("pvalue_adj")
            n_show = min(100, len(result_sorted))
            self.anova_table.setRowCount(n_show)
            self.anova_table.setColumnCount(3)
            stat_header = self.tr("H statistic") if getattr(result, "method_key", "anova") == "kruskal" else self.tr("F statistic")
            self.anova_table.setHorizontalHeaderLabels([
                self.tr("Feature"), stat_header, self.tr("adj.P"),
            ])
            for i in range(n_show):
                row = result_sorted.iloc[i]
                self.anova_table.setItem(i, 0, QTableWidgetItem(str(row["Feature"])))
                self.anova_table.setItem(i, 1, QTableWidgetItem(f'{row["statistic"]:.3f}'))
                self.anova_table.setItem(i, 2, QTableWidgetItem(f'{row["pvalue_adj"]:.2e}'))
            self.anova_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

            previous_feature = self.anova_feat_combo.currentData()
            combo_was_blocked = self.anova_feat_combo.blockSignals(True)
            self.anova_feat_combo.clear()
            sig_feats = result_sorted[result_sorted["significant"]]["Feature"].tolist()
            other_feats = result_sorted[~result_sorted["significant"]]["Feature"].tolist()
            for feat in sig_feats[:50]:
                self.anova_feat_combo.addItem(f"* {feat}", feat)
            for feat in other_feats[:50]:
                self.anova_feat_combo.addItem(str(feat), feat)
            self.anova_feat_combo.blockSignals(combo_was_blocked)
            self._show_result_panel(self.anova_side_panel, self.anova_splitter)

            if self.anova_feat_combo.count():
                target_index = (
                    self.anova_feat_combo.findData(previous_feature)
                    if previous_feature is not None
                    else 0
                )
                if target_index < 0:
                    target_index = 0
                self.anova_feat_combo.setCurrentIndex(target_index)
                self._draw_feature_boxplot()
            self._show_result_panel(self.anova_side_panel, self.anova_splitter)

        self._run_async(_job, _on_success, self.tr("ANOVA Error"))

    def _on_anova_feature_changed(self, _index: int) -> None:
        self._draw_feature_boxplot()

    def _sync_anova_feature_from_table(self) -> None:
        current_row = self.anova_table.currentRow()
        if current_row < 0:
            return
        feature_item = self.anova_table.item(current_row, 0)
        if feature_item is None:
            return

        target_index = self.anova_feat_combo.findData(feature_item.text())
        if target_index < 0 or target_index == self.anova_feat_combo.currentIndex():
            return

        was_blocked = self.anova_feat_combo.blockSignals(True)
        self.anova_feat_combo.setCurrentIndex(target_index)
        self.anova_feat_combo.blockSignals(was_blocked)
        self._draw_feature_boxplot()

    def _draw_feature_boxplot(self):
        if self._anova_result is None or not self.mw.check_data_ready():
            return
        feat = self.anova_feat_combo.currentData()
        if feat is None:
            return
        from visualization.anova_plot import plot_feature_boxplot
        data = self._anova_plot_data if self._anova_plot_data is not None else self.mw.current_data
        labels = (
            self._anova_plot_labels
            if self._anova_plot_labels is not None
            else align_labels_to_data(self.mw.current_data, self.mw.labels)
        )
        plot_feature_boxplot(
            data, labels, feat,
            annotation_method=self._anova_annotation_method,
            theme=self._current_theme(),
            fig=self.anova_feat_canvas.figure,
        )
        self.anova_feat_canvas.draw()
        self.mw.show_shared_plot(self.anova_feat_canvas.figure)

    def _export_anova_csv(self):
        if self._anova_result is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please run ANOVA first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export ANOVA Results"), "anova_result.csv", "CSV (*.csv)"
        )
        if path:
            self._anova_result.result_df.to_csv(path, index=False)
            if self._anova_result.posthoc_df is not None:
                posthoc_path = path.replace(".csv", "_posthoc.csv")
                self._anova_result.posthoc_df.to_csv(posthoc_path, index=False)
            self.mw.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))

    # ?????????????????? ROC ?脩? ??????????????????

    def _build_roc_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Comparison:")))
        self.roc_pair_combo = QComboBox()
        self.roc_pair_combo.setMinimumWidth(220)
        ctrl.addWidget(self.roc_pair_combo)
        self.roc_group1 = QComboBox()
        self.roc_group2 = QComboBox()

        ctrl.addWidget(QLabel(self.tr("Top N:")))
        self.roc_topn = QSpinBox()
        self.roc_topn.setRange(3, 50)
        self.roc_topn.setValue(10)
        ctrl.addWidget(self.roc_topn)

        self.roc_multi = QCheckBox(self.tr("Multi-feature LR"))
        self.roc_multi.setChecked(True)
        ctrl.addWidget(self.roc_multi)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run ROC Analysis")))
        btn_run.clicked.connect(self._run_roc)
        ctrl.addWidget(btn_run)

        btn_save = QPushButton(self.tr("Export Figure"))
        btn_save.clicked.connect(lambda: self._save_figure(self.roc_canvas))
        ctrl.addWidget(btn_save)

        btn_csv = QPushButton(self.tr("Export Results CSV"))
        btn_csv.clicked.connect(self._export_roc_csv)
        ctrl.addWidget(btn_csv)
        layout.addLayout(ctrl)

        # ?”憿?
        ctrl2 = QHBoxLayout()
        ctrl2.addWidget(QLabel(self.tr("Plot:")))
        self.roc_plot_type = QComboBox()
        self.roc_plot_type.addItem(self.tr("ROC Curve"), "roc")
        self.roc_plot_type.addItem(self.tr("AUC Bar"), "auc")
        self.roc_plot_type.currentIndexChanged.connect(self._update_roc_plot)
        ctrl2.addWidget(self.roc_plot_type)
        ctrl2.addStretch()
        layout.addLayout(ctrl2)

        self.roc_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.roc_canvas = MplWidget()
        self.roc_splitter.addWidget(self.roc_canvas)

        self.roc_side_panel = QWidget()
        rl = QVBoxLayout(self.roc_side_panel)
        self.roc_info = QLabel("")
        rl.addWidget(self.roc_info)
        self.roc_table = QTableWidget()
        rl.addWidget(self.roc_table)
        self.roc_side_panel.setMaximumWidth(450)
        self.roc_splitter.addWidget(self.roc_side_panel)
        self._register_result_splitter(self.roc_splitter, self.roc_side_panel)
        self._show_canvas_placeholder(
            self.roc_canvas,
            self.tr("Run ROC analysis to inspect the curve or AUC ranking here."),
        )
        layout.addWidget(self.roc_splitter, stretch=1)
        return w

    def _run_roc(self):
        if not self.mw.check_data_ready():
            return
        self._refresh_roc_groups()
        pair = self._selected_pair(self.roc_pair_combo)
        if pair is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("At least 2 groups are required for ROC analysis."))
            return
        g1, g2 = pair

        from analysis.roc import run_roc_analysis
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=True)
        if qc_meta is None:
            return
        top_n = self.roc_topn.value()
        multi_feature = self.roc_multi.isChecked()

        def _job():
            return run_roc_analysis(
                data, labels,
                group1=g1, group2=g2,
                top_n=top_n,
                multi_feature=multi_feature,
            )

        def _on_success(result):
            self._roc_result = result
            info_lines = [
                self.tr("Top {n} features ROC").format(n=len(result.single_rocs)),
                self.tr("Single-feature AUC uses {k}-fold CV").format(
                    k=result.single_cv_folds_used
                ),
            ]
            if result.multi_auc is not None:
                info_lines.append(
                    self.tr("Multi-feature AUC ({k}-fold CV) = {auc}").format(
                        k=result.multi_cv_folds_used,
                        auc=f"{result.multi_auc:.4f}",
                    )
                )
            info_lines.append(self._qc_scope_text(qc_meta["removed_qc"]))
            self.roc_info.setText("\n".join(info_lines))

            summary = result.summary_df
            n_show = min(50, len(summary))
            self.roc_table.setRowCount(n_show)
            self.roc_table.setColumnCount(4)
            self.roc_table.setHorizontalHeaderLabels([
                self.tr("Feature"), self.tr("AUC"),
                self.tr("Sensitivity"), self.tr("Specificity"),
            ])
            for i in range(n_show):
                row = summary.iloc[i]
                self.roc_table.setItem(i, 0, QTableWidgetItem(str(row["Feature"])))
                self.roc_table.setItem(i, 1, QTableWidgetItem(f'{row["AUC"]:.4f}'))
                self.roc_table.setItem(i, 2, QTableWidgetItem(f'{row["Sensitivity"]:.3f}'))
                self.roc_table.setItem(i, 3, QTableWidgetItem(f'{row["Specificity"]:.3f}'))
            self.roc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self._show_result_panel(self.roc_side_panel, self.roc_splitter)
            self._update_roc_plot()

        self._run_async(_job, _on_success, self.tr("ROC Error"))

    def _update_roc_plot(self):
        if self._roc_result is None:
            return
        plot_key = self.roc_plot_type.currentData()
        fig = self.roc_canvas.figure
        if plot_key == "roc":
            from visualization.roc_plot import plot_roc_curves
            plot_roc_curves(self._roc_result, theme=self._current_theme(), fig=fig)
        else:
            from visualization.roc_plot import plot_auc_ranking
            plot_auc_ranking(self._roc_result, theme=self._current_theme(), fig=fig)
        self.roc_canvas.draw()
        self.mw.show_shared_plot(self.roc_canvas.figure)

    def _refresh_roc_groups(self):
        self._sync_pair_combo(self.roc_pair_combo, self.roc_group1, self.roc_group2, self._available_groups())

    def on_data_updated(self) -> None:
        self._refresh_groups()
        self._refresh_analysis_context()

    def _export_roc_csv(self):
        if self._roc_result is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please run ROC analysis first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export ROC Results"), "roc_result.csv", "CSV (*.csv)"
        )
        if path:
            self._roc_result.summary_df.to_csv(path, index=False)
            self.mw.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))

    # ?????????????????? ?賊??批?????????????????????

    def _build_corr_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Method:")))
        self.corr_method = QComboBox()
        self.corr_method.addItem("Pearson", "pearson")
        self.corr_method.addItem("Spearman", "spearman")
        ctrl.addWidget(self.corr_method)

        ctrl.addWidget(QLabel(self.tr("Absolute correlation threshold:")))
        self.corr_thresh = QDoubleSpinBox()
        self.corr_thresh.setRange(0.5, 0.99)
        self.corr_thresh.setSingleStep(0.05)
        self.corr_thresh.setValue(0.9)
        ctrl.addWidget(self.corr_thresh)

        ctrl.addWidget(QLabel(self.tr("Top features:")))
        self.corr_topn = QSpinBox()
        self.corr_topn.setRange(10, 200)
        self.corr_topn.setValue(50)
        ctrl.addWidget(self.corr_topn)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run Correlation")))
        btn_run.clicked.connect(self._run_corr)
        ctrl.addWidget(btn_run)

        btn_save = QPushButton(self.tr("Export Figure"))
        btn_save.clicked.connect(lambda: self._save_figure(self.corr_canvas))
        ctrl.addWidget(btn_save)
        layout.addLayout(ctrl)

        ctrl2 = QHBoxLayout()
        ctrl2.addWidget(QLabel(self.tr("Plot:")))
        self.corr_plot_type = QComboBox()
        self.corr_plot_type.addItem(self.tr("Correlation Heatmap"), "heatmap")
        self.corr_plot_type.addItem(self.tr("Correlation Network"), "pairs")
        self.corr_plot_type.currentIndexChanged.connect(self._update_corr_plot)
        ctrl2.addWidget(self.corr_plot_type)
        ctrl2.addStretch()
        layout.addLayout(ctrl2)

        self.corr_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.corr_canvas = MplWidget(figsize=(10, 8))
        self.corr_splitter.addWidget(self.corr_canvas)

        self.corr_side_panel = QWidget()
        rl = QVBoxLayout(self.corr_side_panel)
        self.corr_info = QLabel("")
        rl.addWidget(self.corr_info)
        self.corr_table = QTableWidget()
        rl.addWidget(self.corr_table)
        self.corr_side_panel.setMaximumWidth(400)
        self.corr_splitter.addWidget(self.corr_side_panel)
        self._register_result_splitter(self.corr_splitter, self.corr_side_panel)
        self._show_canvas_placeholder(
            self.corr_canvas,
            self.tr("Run correlation analysis to inspect the heatmap or network here."),
        )
        layout.addWidget(self.corr_splitter, stretch=1)
        return w

    def _run_corr(self):
        if not self.mw.check_data_ready():
            return
        from analysis.correlation import run_correlation

        method = self.corr_method.currentData()
        data, _, qc_meta = self._snapshot_stats_data_or_warn(require_labels=False)
        if qc_meta is None:
            return
        threshold = self.corr_thresh.value()
        top_features = self.corr_topn.value()

        def _job():
            return run_correlation(
                data,
                method=method,
                threshold=threshold,
                top_features=top_features,
            )

        def _on_success(result):
            self._corr_result = result
            n_pairs = len(result.high_corr_pairs)
            self.corr_info.setText(
                self.tr(
                    "Method: {method}\n"
                    "Features: {n_feat}\n"
                    "High-correlation pairs (|r| >= {thresh}): {n_pairs}\n"
                    "{qc_note}"
                ).format(
                    method=method.capitalize(),
                    n_feat=result.corr_matrix.shape[0],
                    thresh=f"{threshold:.2f}",
                    n_pairs=n_pairs,
                    qc_note=self._qc_scope_text(qc_meta["removed_qc"]),
                )
            )

            pairs = result.high_corr_pairs
            n_show = min(50, len(pairs))
            self.corr_table.setRowCount(n_show)
            self.corr_table.setColumnCount(3)
            self.corr_table.setHorizontalHeaderLabels([
                self.tr("Feature 1"), self.tr("Feature 2"), self.tr("Correlation"),
            ])
            for i in range(n_show):
                row = pairs.iloc[i]
                self.corr_table.setItem(i, 0, QTableWidgetItem(str(row["Feature_1"])))
                self.corr_table.setItem(i, 1, QTableWidgetItem(str(row["Feature_2"])))
                self.corr_table.setItem(i, 2, QTableWidgetItem(f'{row["Correlation"]:.4f}'))
            self.corr_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self._show_result_panel(self.corr_side_panel, self.corr_splitter)
            self._update_corr_plot()

        self._run_async(_job, _on_success, self.tr("Correlation Error"))

    def _update_corr_plot(self):
        if self._corr_result is None:
            return
        fig = self.corr_canvas.figure
        plot_key = self.corr_plot_type.currentData()
        if plot_key == "heatmap":
            from visualization.correlation_plot import plot_correlation_heatmap
            plot_correlation_heatmap(
                self._corr_result,
                max_features=self.corr_topn.value(),
                theme=self._current_theme(),
                fig=fig,
            )
        else:
            from visualization.correlation_plot import plot_correlation_network
            plot_correlation_network(
                self._corr_result,
                threshold=self.corr_thresh.value(),
                theme=self._current_theme(),
                fig=fig,
            )
        self.corr_canvas.draw()
        self.mw.show_shared_plot(self.corr_canvas.figure)

    # ?????????????????? ?冽?璉格? ??????????????????

    def _build_rf_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Number of trees:")))
        self.rf_trees = QSpinBox()
        self.rf_trees.setRange(50, 2000)
        self.rf_trees.setSingleStep(100)
        self.rf_trees.setValue(500)
        ctrl.addWidget(self.rf_trees)

        ctrl.addWidget(QLabel(self.tr("CV folds:")))
        self.rf_cv = QSpinBox()
        self.rf_cv.setRange(3, 10)
        self.rf_cv.setValue(5)
        ctrl.addWidget(self.rf_cv)

        ctrl.addWidget(QLabel(self.tr("Top N:")))
        self.rf_topn = QSpinBox()
        self.rf_topn.setRange(5, 100)
        self.rf_topn.setValue(25)
        ctrl.addWidget(self.rf_topn)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run Random Forest")))
        btn_run.clicked.connect(self._run_rf)
        ctrl.addWidget(btn_run)

        btn_save = QPushButton(self.tr("Export Figure"))
        btn_save.clicked.connect(lambda: self._save_figure(self.rf_canvas))
        ctrl.addWidget(btn_save)

        btn_csv = QPushButton(self.tr("Export Results CSV"))
        btn_csv.clicked.connect(self._export_rf_csv)
        ctrl.addWidget(btn_csv)
        layout.addLayout(ctrl)

        ctrl2 = QHBoxLayout()
        ctrl2.addWidget(QLabel(self.tr("Plot:")))
        self.rf_plot_type = QComboBox()
        self.rf_plot_type.addItem(self.tr("Feature Importance"), "importance")
        self.rf_plot_type.addItem(self.tr("Confusion Matrix"), "confusion")
        self.rf_plot_type.currentIndexChanged.connect(self._update_rf_plot)
        ctrl2.addWidget(self.rf_plot_type)
        ctrl2.addStretch()
        layout.addLayout(ctrl2)

        self.rf_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.rf_canvas = MplWidget()
        self.rf_splitter.addWidget(self.rf_canvas)

        self.rf_side_panel = QWidget()
        rl = QVBoxLayout(self.rf_side_panel)
        self.rf_info = QTextEdit()
        self.rf_info.setReadOnly(True)
        self.rf_info.setMaximumHeight(120)
        rl.addWidget(self.rf_info)
        self.rf_table = QTableWidget()
        rl.addWidget(self.rf_table)
        self.rf_side_panel.setMaximumWidth(350)
        self.rf_splitter.addWidget(self.rf_side_panel)
        self._register_result_splitter(self.rf_splitter, self.rf_side_panel)
        self._show_canvas_placeholder(
            self.rf_canvas,
            self.tr("Run Random Forest to inspect importance or confusion plots here."),
        )
        layout.addWidget(self.rf_splitter, stretch=1)
        return w

    def _run_rf(self):
        if not self.mw.check_data_ready():
            return
        from analysis.random_forest import run_random_forest
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=True)
        if qc_meta is None:
            return
        n_trees = self.rf_trees.value()
        cv_folds = self.rf_cv.value()
        top_n = self.rf_topn.value()

        def _job():
            return run_random_forest(
                data, labels,
                n_trees=n_trees,
                cv_folds=cv_folds,
                top_n=top_n,
            )

        def _on_success(result):
            self._rf_result = result
            lines = [
                self.tr("=== Random Forest Results ==="),
                self.tr("Number of trees: {n}").format(n=n_trees),
                self.tr("OOB accuracy: {acc}").format(acc=f"{result.oob_accuracy:.4f}"),
                self.tr("CV accuracy: {acc} +/- {std}").format(
                    acc=f"{result.cv_accuracy:.4f}",
                    std=f"{result.cv_std:.4f}"),
                self.tr("Classes: {n}").format(n=len(result.class_names)),
                self._qc_scope_text(qc_meta["removed_qc"]),
            ]
            dropped = getattr(result, "dropped_unnamed_features", 0)
            if dropped:
                lines.append(
                    self.tr("Dropped unnamed/invalid features: {n}").format(n=dropped)
                )
            self.rf_info.setPlainText("\n".join(lines))

            imp = result.feature_importance
            n_show = min(50, len(imp))
            self.rf_table.setRowCount(n_show)
            self.rf_table.setColumnCount(2)
            self.rf_table.setHorizontalHeaderLabels([self.tr("Feature"), self.tr("Importance")])
            for i in range(n_show):
                row = imp.iloc[i]
                self.rf_table.setItem(i, 0, QTableWidgetItem(str(row["Feature"])))
                self.rf_table.setItem(i, 1, QTableWidgetItem(f'{row["Importance"]:.6f}'))
            self.rf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self._show_result_panel(self.rf_side_panel, self.rf_splitter)
            self._update_rf_plot()

        self._run_async(_job, _on_success, self.tr("Random Forest Error"))

    def _update_rf_plot(self):
        if self._rf_result is None:
            return
        fig = self.rf_canvas.figure
        plot_key = self.rf_plot_type.currentData()
        if plot_key == "importance":
            from visualization.rf_plot import plot_rf_importance
            plot_rf_importance(
                self._rf_result,
                top_n=self.rf_topn.value(),
                theme=self._current_theme(),
                fig=fig,
            )
        else:
            from visualization.rf_plot import plot_confusion_matrix
            plot_confusion_matrix(self._rf_result, theme=self._current_theme(), fig=fig)
        self.rf_canvas.draw()
        self.mw.show_shared_plot(self.rf_canvas.figure)

    def _export_rf_csv(self):
        if self._rf_result is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please run Random Forest analysis first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export RF Importance"), "rf_importance.csv", "CSV (*.csv)"
        )
        if path:
            self._rf_result.feature_importance.to_csv(path, index=False)
            self.mw.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))

    # ?????????????????? ?Ｙ黎?菜葫 ??????????????????

    def _build_outlier_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("PCA components:")))
        self.out_ncomp = QSpinBox()
        self.out_ncomp.setRange(2, 10)
        self.out_ncomp.setValue(2)
        ctrl.addWidget(self.out_ncomp)

        ctrl.addWidget(QLabel(self.tr("Significance level:")))
        self.out_alpha = QDoubleSpinBox()
        self.out_alpha.setRange(0.01, 0.10)
        self.out_alpha.setSingleStep(0.01)
        self.out_alpha.setValue(0.05)
        ctrl.addWidget(self.out_alpha)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run Outlier Detection")))
        btn_run.clicked.connect(self._run_outlier)
        ctrl.addWidget(btn_run)

        btn_save = QPushButton(self.tr("Export Figure"))
        btn_save.clicked.connect(lambda: self._save_figure(self.out_canvas))
        ctrl.addWidget(btn_save)

        btn_csv = QPushButton(self.tr("Export Results CSV"))
        btn_csv.clicked.connect(self._export_outlier_csv)
        ctrl.addWidget(btn_csv)
        layout.addLayout(ctrl)

        ctrl2 = QHBoxLayout()
        ctrl2.addWidget(QLabel(self.tr("Plot:")))
        self.out_plot_type = QComboBox()
        self.out_plot_type.addItem(self.tr("T2 Score Plot"), "t2")
        self.out_plot_type.addItem(self.tr("DModX"), "dmodx")
        self.out_plot_type.currentIndexChanged.connect(self._update_outlier_plot)
        ctrl2.addWidget(self.out_plot_type)
        ctrl2.addWidget(QLabel(self.tr("Display group:")))
        self.out_group_combo = QComboBox()
        self._sync_display_group_combo(self.out_group_combo, [])
        self.out_group_combo.currentIndexChanged.connect(self._on_outlier_group_changed)
        ctrl2.addWidget(self.out_group_combo)
        ctrl2.addStretch()
        layout.addLayout(ctrl2)

        self.out_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.out_canvas = MplWidget(figsize=(10, 5))
        self.out_splitter.addWidget(self.out_canvas)

        self.out_side_panel = QWidget()
        rl = QVBoxLayout(self.out_side_panel)
        self.out_info = QTextEdit()
        self.out_info.setReadOnly(True)
        self.out_info.setMaximumHeight(120)
        rl.addWidget(self.out_info)
        self.out_table = QTableWidget()
        rl.addWidget(self.out_table)
        self.out_side_panel.setMaximumWidth(350)
        self.out_splitter.addWidget(self.out_side_panel)
        self._register_result_splitter(self.out_splitter, self.out_side_panel)
        self._show_canvas_placeholder(
            self.out_canvas,
            self.tr("Run outlier detection to inspect score diagnostics here."),
        )
        layout.addWidget(self.out_splitter, stretch=1)
        return w

    def _run_outlier(self):
        if not self.mw.check_data_ready():
            return
        from analysis.outlier import run_outlier_detection
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=False)
        if qc_meta is None:
            return
        n_components = self.out_ncomp.value()
        alpha = self.out_alpha.value()

        def _job():
            return run_outlier_detection(
                data,
                n_components=n_components,
                alpha=alpha,
            )

        def _on_success(result):
            self._outlier_result = result
            self._outlier_labels = labels
            n_t2 = result.outlier_mask_t2.sum()
            n_dmodx = result.outlier_mask_dmodx.sum()
            lines = [
                self.tr("=== Outlier Detection Results ==="),
                self.tr("Hotelling T2 outliers: {n}").format(n=n_t2),
                self.tr("T2 threshold: {val}").format(val=f"{result.t2_threshold:.4f}"),
                self.tr("DModX outliers: {n}").format(n=n_dmodx),
                self.tr("DModX threshold: {val}").format(val=f"{result.dmodx_threshold:.4f}"),
                self._qc_scope_text(qc_meta["removed_qc"]),
            ]
            self.out_info.setPlainText("\n".join(lines))
            self._refresh_outlier_table()
            self._show_result_panel(self.out_side_panel, self.out_splitter)
            self._update_outlier_plot()

        self._run_async(_job, _on_success, self.tr("Outlier Detection Error"))

    def _update_outlier_plot(self):
        if self._outlier_result is None:
            return
        fig = self.out_canvas.figure
        plot_key = self.out_plot_type.currentData()
        group_filter = self.out_group_combo.currentData()
        if plot_key == "t2":
            from visualization.outlier_plot import plot_outlier_score
            plot_outlier_score(
                self._outlier_result,
                labels=self._outlier_labels,
                group_filter=group_filter,
                theme=self._current_theme(),
                fig=fig,
            )
        else:
            from visualization.outlier_plot import plot_dmodx
            plot_dmodx(
                self._outlier_result,
                labels=self._outlier_labels,
                group_filter=group_filter,
                theme=self._current_theme(),
                fig=fig,
            )
        self.out_canvas.draw()
        self.mw.show_shared_plot(self.out_canvas.figure)

    def _refresh_outlier_table(self) -> None:
        if self._outlier_result is None:
            return
        out_df = self._outlier_result.get_outlier_df()
        group_filter = self.out_group_combo.currentData()
        if group_filter is not None and self._outlier_labels is not None:
            sample_groups = self._outlier_labels.reindex(out_df["Sample"]).astype(str)
            out_df = out_df.loc[sample_groups.to_numpy() == str(group_filter)].copy()

        n_show = len(out_df)
        self.out_table.setRowCount(n_show)
        self.out_table.setColumnCount(4)
        self.out_table.setHorizontalHeaderLabels([
            self.tr("Sample"), self.tr("T2"), self.tr("DModX"), self.tr("Outlier"),
        ])
        for i in range(n_show):
            row = out_df.iloc[i]
            self.out_table.setItem(i, 0, QTableWidgetItem(str(row["Sample"])))
            self.out_table.setItem(i, 1, QTableWidgetItem(f'{row["T2"]:.3f}'))
            self.out_table.setItem(i, 2, QTableWidgetItem(f'{row["DModX"]:.4f}'))
            self.out_table.setItem(i, 3, QTableWidgetItem(
            self.tr("Yes") if row["Any_Outlier"] else ""))
        self.out_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _on_outlier_group_changed(self) -> None:
        self._refresh_outlier_table()
        self._update_outlier_plot()

    def _export_outlier_csv(self):
        if self._outlier_result is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please run Outlier detection first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Outlier Results"), "outlier_result.csv", "CSV (*.csv)"
        )
        if path:
            self._outlier_result.get_outlier_df().to_csv(path, index=False)
            self.mw.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))

    # ?????????????????? OPLS-DA ??????????????????

    def _build_oplsda_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Predictive components:")))
        self.oplsda_ncomp = QSpinBox()
        self.oplsda_ncomp.setRange(1, 5)
        self.oplsda_ncomp.setValue(1)
        ctrl.addWidget(self.oplsda_ncomp)

        ctrl.addWidget(QLabel(self.tr("CV method:")))
        self.oplsda_cv = QComboBox()
        self.oplsda_cv.addItem(self.tr("LOO (Leave-One-Out)"), "loo")
        self.oplsda_cv.addItem(self.tr("5-Fold"), "kfold5")
        ctrl.addWidget(self.oplsda_cv)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run OPLS-DA")))
        btn_run.clicked.connect(self._run_oplsda)
        ctrl.addWidget(btn_run)

        ctrl.addWidget(QLabel(self.tr("Plot:")))
        self.oplsda_plot_type = QComboBox()
        self.oplsda_plot_type.addItem(self.tr("Score Plot"), "score")
        # Keep S-Plot implementation available, but hide the selector for now.
        self.oplsda_plot_type.currentIndexChanged.connect(self._update_oplsda_plot)
        ctrl.addWidget(self.oplsda_plot_type)

        ctrl.addWidget(QLabel(self.tr("Labels:")))
        self.oplsda_label_mode = self._build_score_label_mode_combo(self._update_oplsda_plot)
        ctrl.addWidget(self.oplsda_label_mode)

        btn_save = QPushButton(self.tr("Export"))
        btn_save.clicked.connect(self._export_oplsda_view)
        ctrl.addWidget(btn_save)

        btn_csv = QPushButton(self.tr("Export Results CSV"))
        btn_csv.clicked.connect(self._export_oplsda_csv)
        ctrl.addWidget(btn_csv)
        layout.addLayout(ctrl)

        self.oplsda_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.oplsda_widget = PlotlyWidget()
        self.oplsda_splitter.addWidget(self.oplsda_widget)

        self.oplsda_side_panel = QWidget()
        rl = QVBoxLayout(self.oplsda_side_panel)
        self.oplsda_info = QTextEdit()
        self.oplsda_info.setReadOnly(True)
        self.oplsda_info.setMaximumHeight(150)
        rl.addWidget(self.oplsda_info)
        self.oplsda_table = QTableWidget()
        rl.addWidget(self.oplsda_table)
        self.oplsda_side_panel.setMaximumWidth(400)
        self.oplsda_splitter.addWidget(self.oplsda_side_panel)
        self._register_result_splitter(self.oplsda_splitter, self.oplsda_side_panel)
        layout.addWidget(self.oplsda_splitter, stretch=1)
        return w

    def _run_oplsda(self):
        if not self.mw.check_data_ready():
            return
        try:
            from analysis.oplsda import run_oplsda
        except ImportError:
            QMessageBox.warning(
                self, self.tr("Warning"),
                self.tr("OPLS-DA requires pyopls. Install: pip install pyopls"),
            )
            return

        n = self.oplsda_ncomp.value()
        cv = self.oplsda_cv.currentData()
        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=True)
        if qc_meta is None:
            return

        def _job():
            return run_oplsda(
                data, labels,
                n_components=n, cv_method=cv,
            )

        def _on_success(result):
            self._oplsda_result = result
            lines = [
                self.tr("=== OPLS-DA Results ==="),
                self.tr("R2X = {val}").format(val=f"{result.r2x:.4f}"),
                self.tr("R2Y = {val}").format(val=f"{result.r2y:.4f}"),
                self.tr("Q2 = {val}").format(val=f"{result.q2:.4f}"),
                self.tr("Backend: {name}").format(
                    name=getattr(result, "backend", "pyopls")),
                self.tr("Predictive components: {n}").format(n=n),
                self.tr("Groups: {groups}").format(
                    groups=", ".join(str(c) for c in result.class_names)),
                self._qc_scope_text(qc_meta["removed_qc"]),
            ]
            self.oplsda_info.setPlainText("\n".join(lines))

            imp_df = result.get_importance_df()
            n_show = min(50, len(imp_df))
            self.oplsda_table.setRowCount(n_show)
            self.oplsda_table.setColumnCount(3)
            self.oplsda_table.setHorizontalHeaderLabels([
                self.tr("Feature"), self.tr("Loading"), self.tr("Importance"),
            ])
            for i in range(n_show):
                row = imp_df.iloc[i]
                self.oplsda_table.setItem(i, 0, QTableWidgetItem(str(row["Feature"])))
                self.oplsda_table.setItem(i, 1, QTableWidgetItem(f'{row["Loading"]:.4f}'))
                self.oplsda_table.setItem(i, 2, QTableWidgetItem(f'{row["Importance"]:.4f}'))
            self.oplsda_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
            self._show_result_panel(self.oplsda_side_panel, self.oplsda_splitter)
            self._update_oplsda_plot()

        self._run_async(_job, _on_success, self.tr("OPLS-DA Error"))

    def _update_oplsda_plot(self):
        if self._oplsda_result is None:
            return
        plot_key = self.oplsda_plot_type.currentData()
        if plot_key == "score":
            from visualization.oplsda_plot import plot_oplsda_score_interactive

            interactive_fig = plot_oplsda_score_interactive(
                self._oplsda_result,
                show_labels=self.oplsda_label_mode.currentData(),
                theme=self._current_theme(),
            )
            if interactive_fig is not None:
                self.oplsda_widget.show_figure(interactive_fig, enable_selection_bridge=True)
                return

        self.oplsda_widget.show_html(
            "<html><body style='font-family:sans-serif; padding:24px; color:#888;'>"
            + self.tr("Plotly is required to render the interactive OPLS-DA score plot.")
            + "</body></html>"
        )

    def _export_oplsda_csv(self):
        if self._oplsda_result is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please run OPLS-DA first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export OPLS-DA Results"), "oplsda_importance.csv", "CSV (*.csv)"
        )
        if path:
            self._oplsda_result.get_importance_df().to_csv(path, index=False)
            self.mw.status_bar.showMessage(self.tr("Saved: {path}").format(path=path))

    # ?????????????????? ?梁撌亙 ??????????????????

    # ────────────────── Clustering ──────────────────

    def _build_clustering_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(self.tr("Method:")))
        self.clust_method = QComboBox()
        self.clust_method.addItem("Ward", "ward")
        self.clust_method.addItem("Complete", "complete")
        self.clust_method.addItem("Average", "average")
        self.clust_method.addItem("Single", "single")
        ctrl.addWidget(self.clust_method)

        ctrl.addWidget(QLabel(self.tr("Metric:")))
        self.clust_metric = QComboBox()
        self.clust_metric.addItem("Euclidean", "euclidean")
        self.clust_metric.addItem("Correlation", "correlation")
        self.clust_metric.addItem("Cosine", "cosine")
        ctrl.addWidget(self.clust_metric)

        ctrl.addWidget(QLabel(self.tr("Max features:")))
        self.clust_maxfeat = QSpinBox()
        self.clust_maxfeat.setRange(50, 10000)
        self.clust_maxfeat.setValue(2000)
        self.clust_maxfeat.setSingleStep(100)
        ctrl.addWidget(self.clust_maxfeat)

        btn_run = self._mark_primary_action(QPushButton(self.tr("Run Clustering")))
        btn_run.clicked.connect(self._run_clustering)
        ctrl.addWidget(btn_run)

        ctrl.addWidget(QLabel(self.tr("Plot:")))
        self.clust_plot_type = QComboBox()
        self.clust_plot_type.addItem(self.tr("Dendrogram"), "dendrogram")
        self.clust_plot_type.addItem(self.tr("Summary"), "summary")
        self.clust_plot_type.currentIndexChanged.connect(self._update_clustering_plot)
        ctrl.addWidget(self.clust_plot_type)

        btn_save = QPushButton(self.tr("Export Figure"))
        btn_save.clicked.connect(lambda: self._save_figure(self.clust_canvas))
        ctrl.addWidget(btn_save)

        layout.addLayout(ctrl)

        self.clust_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.clust_canvas = MplWidget()
        self.clust_splitter.addWidget(self.clust_canvas)
        self.clust_info = QTextEdit()
        self.clust_info.setReadOnly(True)
        self.clust_info.setMaximumWidth(300)
        self.clust_splitter.addWidget(self.clust_info)
        self._register_result_splitter(self.clust_splitter, self.clust_info)
        self._show_canvas_placeholder(
            self.clust_canvas,
            self.tr("Run clustering to inspect the dendrogram or summary view here."),
        )
        layout.addWidget(self.clust_splitter, stretch=1)
        return w

    def _run_clustering(self):
        if not self.mw.check_data_ready():
            return
        from analysis.clustering import run_clustering

        method = self.clust_method.currentData()
        metric = self.clust_metric.currentData()
        max_feat = self.clust_maxfeat.value()

        if method == "ward" and metric != "euclidean":
            metric = "euclidean"
            self.clust_metric.setCurrentIndex(0)
            self.mw.status_bar.showMessage(
                self.tr("Ward linkage requires Euclidean distance. Metric reset to Euclidean."))

        data, labels, qc_meta = self._snapshot_stats_data_or_warn(require_labels=True)
        if qc_meta is None:
            return

        def _job():
            return run_clustering(
                data, labels,
                method=method, metric=metric,
                max_features=max_feat,
            )

        def _on_success(result):
            self._clustering_result = result
            lines = [
                self.tr("=== Clustering Results ==="),
                self.tr("Method: {method}").format(method=result.method),
                self.tr("Metric: {metric}").format(metric=result.metric),
                self.tr("Samples: {n}").format(n=len(result.sample_names)),
                self.tr("Features used: {n}").format(n=len(result.feature_names)),
                self.tr("Clusters: {n}").format(n=result.n_clusters),
                self.tr("Cophenetic correlation: {val}").format(
                    val=f"{result.cophenetic_corr:.4f}"),
                self._qc_scope_text(qc_meta["removed_qc"]),
            ]
            self.clust_info.setPlainText("\n".join(lines))
            self._show_result_panel(self.clust_info, self.clust_splitter)
            self._update_clustering_plot()

        self._run_async(_job, _on_success, self.tr("Clustering Error"))

    def _update_clustering_plot(self):
        if self._clustering_result is None:
            return
        fig = self.clust_canvas.figure
        plot_key = self.clust_plot_type.currentData()
        if plot_key == "dendrogram":
            from visualization.clustering_plot import plot_dendrogram
            plot_dendrogram(self._clustering_result, theme=self._current_theme(), fig=fig)
        else:
            from visualization.clustering_plot import plot_cluster_summary
            plot_cluster_summary(self._clustering_result, theme=self._current_theme(), fig=fig)
        self.clust_canvas.draw()
        self.mw.show_shared_plot(self.clust_canvas.figure)

    # ────────────────── Common ──────────────────

    def _save_figure(self, canvas: MplWidget):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Figure"), "figure.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            canvas.figure.savefig(path, dpi=300, bbox_inches="tight")
            self.mw.status_bar.showMessage(self.tr("Saved figure: {path}").format(path=path))

    def _save_plotly_html(self, widget: PlotlyWidget, title: str, default_name: str) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            title,
            default_name,
            "HTML (*.html)",
        )
        if path:
            widget.save_html(path)
            self.mw.status_bar.showMessage(self.tr("Saved interactive chart: {path}").format(path=path))

    def _export_pca_view(self) -> None:
        if self.pca_plot_type.currentData() == "score" and self.pca_plot_stack.currentWidget() is self.pca_plotly_widget:
            self._save_plotly_html(self.pca_plotly_widget, self.tr("Export PCA Score Plot"), "pca_score_plot.html")
            return
        self._save_figure(self.pca_canvas)

    def _export_plsda_view(self) -> None:
        if self.pls_plot_type.currentData() == "score" and self.pls_plot_stack.currentWidget() is self.pls_plotly_widget:
            self._save_plotly_html(self.pls_plotly_widget, self.tr("Export PLS-DA Score Plot"), "plsda_score_plot.html")
            return
        self._save_figure(self.pls_canvas)

    def _export_oplsda_view(self) -> None:
        self._save_plotly_html(self.oplsda_widget, self.tr("Export OPLS-DA Score Plot"), "oplsda_score_plot.html")
