"""
Missing-value handling tab.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ms_core.processing.missing_values import IMPUTE_METHODS
from gui.state_binding import ApplyStateResult, apply_combo_data, apply_spin_value


class MissingValueTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.info_group = QGroupBox(self.tr("Missing Value Summary"))
        info_layout = QVBoxLayout()
        self.info_label = QLabel(self.tr("Please import data first."))
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        self.param_group = QGroupBox(self.tr("Parameters"))
        param_layout = QHBoxLayout()

        self.thresh_label = QLabel(self.tr("Missing threshold:"))
        param_layout.addWidget(self.thresh_label)
        self.thresh_spin = QDoubleSpinBox()
        self.thresh_spin.setRange(0.1, 1.0)
        self.thresh_spin.setSingleStep(0.05)
        self.thresh_spin.setValue(0.5)
        self.thresh_spin.setToolTip(self.tr("Remove features with missing ratio >= threshold"))
        param_layout.addWidget(self.thresh_spin)

        self.impute_label = QLabel(self.tr("Imputation:"))
        param_layout.addWidget(self.impute_label)
        self.method_combo = QComboBox()
        for key, label in IMPUTE_METHODS.items():
            self.method_combo.addItem(label, key)
        param_layout.addWidget(self.method_combo)

        self.btn_run = QPushButton(self.tr("Apply Missing-Value Step"))
        self.btn_run.clicked.connect(self._run)
        param_layout.addWidget(self.btn_run)

        self.param_group.setLayout(param_layout)
        layout.addWidget(self.param_group)

        self.log_group = QGroupBox(self.tr("Processing Log"))
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(280)
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group, stretch=1)

    def retranslateUi(self):
        self.info_group.setTitle(self.tr("Missing Value Summary"))
        self.param_group.setTitle(self.tr("Parameters"))
        self.log_group.setTitle(self.tr("Processing Log"))
        self.thresh_label.setText(self.tr("Missing threshold:"))
        self.thresh_spin.setToolTip(self.tr("Remove features with missing ratio >= threshold"))
        self.impute_label.setText(self.tr("Imputation:"))
        self.btn_run.setText(self.tr("Apply Missing-Value Step"))

    def connect_state_changed(self, callback: Callable[..., None]) -> None:
        self.thresh_spin.valueChanged.connect(callback)
        self.method_combo.currentIndexChanged.connect(callback)

    def read_state(self) -> dict[str, Any]:
        return {
            "pipeline": {
                "missing_thresh": float(self.thresh_spin.value()),
                "impute_method": self.method_combo.currentData(),
            }
        }

    def validate_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        pipeline = state.get("pipeline", {})
        result = ApplyStateResult()
        if not isinstance(pipeline, Mapping):
            return result
        result.extend(
            apply_combo_data(
                self.method_combo,
                pipeline.get("impute_method"),
                "pipeline.impute_method",
            )
        )
        return result

    def apply_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        pipeline = state.get("pipeline", {})
        if not isinstance(pipeline, Mapping):
            return ApplyStateResult()

        if "missing_thresh" in pipeline:
            apply_spin_value(self.thresh_spin, float(pipeline["missing_thresh"]))

        result = self.validate_state(state)
        return result

    def on_data_loaded(self):
        df = self.mw.current_data
        if df is None:
            return
        total = df.size
        missing = int(df.isna().sum().sum())
        zeros = int((df == 0).sum().sum())
        feat_with_mv = int((df.isna().sum() > 0).sum())
        self.info_label.setText(
            self.tr(
                "Samples: {samples} | Features: {features}\n"
                "Zero values: {zeros} ({zero_pct:.1f}%)\n"
                "Missing values: {missing} ({miss_pct:.1f}%)\n"
                "Features with missing values: {mv_feat}/{features}"
            ).format(
                samples=df.shape[0],
                features=df.shape[1],
                zeros=zeros,
                zero_pct=(zeros / total * 100) if total else 0.0,
                missing=missing,
                miss_pct=(missing / total * 100) if total else 0.0,
                mv_feat=feat_with_mv,
            )
        )

    def _run(self):
        if not self.mw.check_data_ready():
            return

        threshold = self.thresh_spin.value()
        method = self.method_combo.currentData()
        self.btn_run.setEnabled(False)
        self.log_text.setPlainText(self.tr("Running pipeline (missing-value stage)..."))

        self.mw.set_pipeline_params(
            missing_thresh=threshold,
            impute_method=method,
        )
        self.mw.run_pipeline_async(
            stage="missing",
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
            self.tr("Missing Values"),
            step_key="missing",
            labels=labels,
        )
        self.mw.filter_tab.on_data_updated()

    def _on_pipeline_error(self, error_text: str):
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, self.tr("Pipeline Error"), error_text)
