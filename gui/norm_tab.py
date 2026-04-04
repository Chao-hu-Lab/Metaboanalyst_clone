"""
Normalization tab:
Row normalization -> transformation -> scaling
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ms_core.processing.normalization import ROW_NORM_METHODS
from core.sample_info import build_aligned_factors, detect_factor_columns
from ms_core.processing.scaling import SCALING_METHODS
from ms_core.processing.transformation import TRANSFORM_METHODS
from gui.state_binding import ApplyStateResult, apply_combo_data
from gui.widgets.mpl_canvas import MplWidget


class NormTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._before_df = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.info_group = QGroupBox(self.tr("Current Data"))
        info_layout = QVBoxLayout()
        self.info_label = QLabel(self.tr("Apply filtering step first."))
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        self.settings_group = QGroupBox(self.tr("Normalization Pipeline"))
        settings_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.row_label = QLabel(self.tr("1. Row normalization:"))
        row1.addWidget(self.row_label)
        self.row_combo = QComboBox()
        for key, label in ROW_NORM_METHODS.items():
            self.row_combo.addItem(label, key)
        self.row_combo.currentIndexChanged.connect(self._on_row_method_changed)
        row1.addWidget(self.row_combo)
        settings_layout.addLayout(row1)

        factor_row = QHBoxLayout()
        self.factor_label = QLabel(self.tr("SampleInfo factor column:"))
        factor_row.addWidget(self.factor_label)
        self.factor_combo = QComboBox()
        self.factor_combo.setMinimumWidth(220)
        factor_row.addWidget(self.factor_combo)
        self.factor_refresh_btn = QPushButton(self.tr("Refresh SampleInfo"))
        self.factor_refresh_btn.clicked.connect(self._refresh_factor_controls)
        factor_row.addWidget(self.factor_refresh_btn)
        settings_layout.addLayout(factor_row)

        self.factor_status = QLabel("")
        self.factor_status.setWordWrap(True)
        settings_layout.addWidget(self.factor_status)

        row2 = QHBoxLayout()
        self.trans_label = QLabel(self.tr("2. Transformation:"))
        row2.addWidget(self.trans_label)
        self.trans_combo = QComboBox()
        for key, label in TRANSFORM_METHODS.items():
            self.trans_combo.addItem(label, key)
        row2.addWidget(self.trans_combo)
        settings_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.scale_label = QLabel(self.tr("3. Scaling:"))
        row3.addWidget(self.scale_label)
        self.scale_combo = QComboBox()
        for key, label in SCALING_METHODS.items():
            self.scale_combo.addItem(label, key)
        row3.addWidget(self.scale_combo)
        settings_layout.addLayout(row3)

        btn_row = QHBoxLayout()
        self.btn_run = QPushButton(self.tr("Apply Full Normalization Pipeline"))
        self.btn_run.clicked.connect(self._run)
        btn_row.addWidget(self.btn_run)

        self.btn_reset = QPushButton(self.tr("Reset to Filtered Data"))
        self.btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(self.btn_reset)
        settings_layout.addLayout(btn_row)

        self.settings_group.setLayout(settings_layout)
        layout.addWidget(self.settings_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.log_group = QGroupBox(self.tr("Processing Log"))
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        self.log_group.setMaximumWidth(420)
        splitter.addWidget(self.log_group)

        self.preview_group = QGroupBox(self.tr("Before / After Preview"))
        preview_layout = QVBoxLayout()
        self.preview_canvas = MplWidget(figsize=(10, 7))
        preview_layout.addWidget(self.preview_canvas)
        self.preview_group.setLayout(preview_layout)
        splitter.addWidget(self.preview_group)

        layout.addWidget(splitter, stretch=1)
        self._refresh_factor_controls()
        self._on_row_method_changed()

    def retranslateUi(self):
        self.info_group.setTitle(self.tr("Current Data"))
        self.settings_group.setTitle(self.tr("Normalization Pipeline"))
        self.log_group.setTitle(self.tr("Processing Log"))
        self.preview_group.setTitle(self.tr("Before / After Preview"))
        self.row_label.setText(self.tr("1. Row normalization:"))
        self.factor_label.setText(self.tr("SampleInfo factor column:"))
        self.factor_refresh_btn.setText(self.tr("Refresh SampleInfo"))
        self.trans_label.setText(self.tr("2. Transformation:"))
        self.scale_label.setText(self.tr("3. Scaling:"))
        self.btn_run.setText(self.tr("Apply Full Normalization Pipeline"))
        self.btn_reset.setText(self.tr("Reset to Filtered Data"))
        self._refresh_factor_controls()
        self._on_row_method_changed()

    def connect_state_changed(self, callback: Callable[..., None]) -> None:
        self.row_combo.currentIndexChanged.connect(callback)
        self.trans_combo.currentIndexChanged.connect(callback)
        self.scale_combo.currentIndexChanged.connect(callback)
        self.factor_combo.currentIndexChanged.connect(callback)

    def read_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "pipeline": {
                "row_norm": self.row_combo.currentData(),
                "transform": self.trans_combo.currentData(),
                "scaling": self.scale_combo.currentData(),
            }
        }
        factor_column = self.factor_combo.currentData()
        if self.row_combo.currentData() == "SpecNorm" and factor_column is not None:
            state["spec_norm"] = {"factor_column": str(factor_column)}
        return state

    def validate_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        result = ApplyStateResult()
        pipeline = state.get("pipeline", {})
        if isinstance(pipeline, Mapping):
            result.extend(
                apply_combo_data(self.row_combo, pipeline.get("row_norm"), "pipeline.row_norm")
            )
            result.extend(
                apply_combo_data(
                    self.trans_combo,
                    pipeline.get("transform"),
                    "pipeline.transform",
                )
            )
            result.extend(
                apply_combo_data(
                    self.scale_combo,
                    pipeline.get("scaling"),
                    "pipeline.scaling",
                )
            )
        return result

    def apply_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        result = self.validate_state(state)
        spec_norm = state.get("spec_norm", {})
        if isinstance(spec_norm, Mapping):
            factor_column = spec_norm.get("factor_column")
            if factor_column is not None:
                if not apply_combo_data(
                    self.factor_combo,
                    factor_column,
                    "spec_norm.factor_column",
                ).unsupported_paths:
                    self._on_row_method_changed()
        self._on_row_method_changed()
        return result

    def _refresh_factor_controls(self):
        blocker = QSignalBlocker(self.factor_combo)
        self.factor_combo.clear()
        sample_info = getattr(self.mw, "sample_info", None)
        if sample_info is None or sample_info.empty:
            self.factor_status.setText(
                self.tr("SampleInfo sheet not found. SpecNorm from SampleInfo is unavailable.")
            )
            del blocker
            return

        columns, default_col = detect_factor_columns(sample_info)
        for col in columns:
            self.factor_combo.addItem(str(col), str(col))

        if default_col is not None:
            idx = self.factor_combo.findData(str(default_col))
            if idx >= 0:
                self.factor_combo.setCurrentIndex(idx)

        if not columns:
            self.factor_status.setText(
                self.tr("SampleInfo loaded, but no numeric factor columns were detected.")
            )
        else:
            self.factor_status.setText(
                self.tr(
                    "SampleInfo loaded ({rows} x {cols}). Candidate factor columns: {n}. "
                    "Default selection: {default_col}"
                ).format(
                    rows=sample_info.shape[0],
                    cols=sample_info.shape[1],
                    n=len(columns),
                    default_col=default_col if default_col is not None else "-",
                )
            )
        del blocker

    def _on_row_method_changed(self):
        is_specnorm = self.row_combo.currentData() == "SpecNorm"
        has_factor_cols = self.factor_combo.count() > 0
        self.factor_label.setEnabled(is_specnorm)
        self.factor_combo.setEnabled(is_specnorm and has_factor_cols)
        self.factor_refresh_btn.setEnabled(is_specnorm)
        if is_specnorm and not has_factor_cols:
            self.factor_status.setText(
                self.tr("SpecNorm requires a numeric factor column from SampleInfo.")
            )

    def on_data_updated(self):
        df = self.mw.current_data
        if df is None:
            return
        self.info_label.setText(
            self.tr("Features: {features} | Samples: {samples}").format(
                features=df.shape[1], samples=df.shape[0]
            )
        )
        self._refresh_factor_controls()
        self._on_row_method_changed()

    def _reset(self):
        """Restore data to the post-filter checkpoint."""
        if self.mw._filtered_data is None:
            QMessageBox.information(
                self,
                self.tr("Reset"),
                self.tr("No filtered data checkpoint available. Run filtering first."),
            )
            return
        self.mw.update_data(
            self.mw._filtered_data.copy(),
            source_tab=self.tr("Reset to filtered"),
            step_key="filter",
            labels=self.mw._filtered_labels,
        )
        self.log_text.clear()
        self.on_data_updated()

    def _resolve_specnorm_factors(self):
        sample_info = getattr(self.mw, "sample_info", None)
        if sample_info is None or sample_info.empty:
            raise ValueError("SampleInfo sheet is required for SpecNorm.")
        factor_col = self.factor_combo.currentData()
        if factor_col is None:
            raise ValueError("Please choose a factor column from SampleInfo.")
        factors, meta = build_aligned_factors(
            sample_info=sample_info,
            sample_ids=self.mw.current_data.index,
            factor_column=str(factor_col),
        )
        return factors, meta

    def _run(self):
        if not self.mw.check_data_ready():
            return

        row_method = self.row_combo.currentData()
        trans_method = self.trans_combo.currentData()
        scale_method = self.scale_combo.currentData()

        params = {
            "row_norm": row_method,
            "transform": trans_method,
            "scaling": scale_method,
            "factors": None,
            "factor_source": None,
        }

        if row_method == "SpecNorm":
            try:
                factors, meta = self._resolve_specnorm_factors()
            except Exception as exc:
                QMessageBox.warning(self, self.tr("Warning"), str(exc))
                return
            source_text = (
                f"SampleInfo[{meta['factor_column']}] "
                f"(sample_id={meta['sample_id_column']})"
            )
            if int(meta.get("n_fuzzy_matches", 0)) > 0:
                source_text += f", fuzzy_matches={meta['n_fuzzy_matches']}"
            if int(meta.get("n_qc_skipped", 0)) > 0:
                source_text += f", qc_skipped={meta['n_qc_skipped']}"
            params["factors"] = factors
            params["factor_source"] = source_text
            log_lines = [
                self.tr("Running full pipeline (normalization stage)..."),
                self.tr("SpecNorm source: {source}").format(source=source_text),
            ]

            fuzzy_matches = meta.get("fuzzy_matches") or []
            if fuzzy_matches:
                fuzzy_preview = ", ".join(
                    f"{src} -> {dst}" for src, dst, _ in fuzzy_matches[:5]
                )
                extra = "" if len(fuzzy_matches) <= 5 else f" (+{len(fuzzy_matches)-5} more)"
                log_lines.append(
                    self.tr("Alignment reminder (fuzzy matched): {pairs}{extra}").format(
                        pairs=fuzzy_preview, extra=extra
                    )
                )

            if int(meta.get("n_qc_skipped", 0)) > 0:
                log_lines.append(
                    self.tr(
                        "QC factor reminder: {n} QC samples had missing factors and were skipped "
                        "(factor=1.0; intensity unchanged)."
                    ).format(n=meta["n_qc_skipped"])
                )

            self.log_text.setPlainText("\n".join(log_lines))
        else:
            self.log_text.setPlainText(
                self.tr("Running full pipeline (normalization stage)...")
            )

        self._before_df = self.mw.current_data.copy()
        self.btn_run.setEnabled(False)
        self.mw.set_pipeline_params(**params)
        self.mw.run_pipeline_async(
            stage="norm",
            on_success=self._on_pipeline_done,
            on_error=self._on_pipeline_error,
        )

    def _on_pipeline_done(self, payload):
        df = payload["data"]
        pipeline_log = payload["log"]
        labels = payload.get("labels")
        self.btn_run.setEnabled(True)
        self.log_text.setPlainText("\n".join(pipeline_log))
        self.mw.update_data(
            df,
            self.tr("Normalization"),
            step_key="norm",
            labels=labels,
        )

        if self.mw.labels is None or self._before_df is None:
            return
        try:
            from visualization.norm_preview import plot_norm_comparison

            plot_norm_comparison(
                self._before_df,
                df,
                self.mw.labels,
                fig=self.preview_canvas.figure,
            )
            self.preview_canvas.draw()
            self.mw.show_shared_plot(self.preview_canvas.figure)
        except Exception:
            pass

    def _on_pipeline_error(self, error_text: str):
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, self.tr("Pipeline Error"), error_text)
