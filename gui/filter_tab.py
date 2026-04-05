"""
Variable filtering tab (+ optional QC-RSD filtering).
"""

from __future__ import annotations

import pandas as pd
from typing import Any, Callable, Mapping
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ms_core.processing.feature_filter import FILTER_METHODS, get_auto_cutoff
from gui.state_binding import ApplyStateResult, apply_checked, apply_combo_data, apply_spin_value


class FilterTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._has_qc = False
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        root_layout.addWidget(self.scroll_area)

        content = QWidget()
        self.scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.info_group = QGroupBox(self.tr("Current Data"))
        info_layout = QVBoxLayout()
        self.info_label = QLabel(self.tr("Apply missing-value step first."))
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        self.param_group = QGroupBox(self.tr("Filter Parameters"))
        param_layout = QGridLayout()
        param_layout.setHorizontalSpacing(12)
        param_layout.setVerticalSpacing(8)

        self.method_label = QLabel(self.tr("Filter method:"))
        self.method_label.setWordWrap(True)
        param_layout.addWidget(self.method_label, 0, 0)
        self.method_combo = QComboBox()
        for key, label in FILTER_METHODS.items():
            if key == "None":
                continue
            self.method_combo.addItem(label, key)
        self.method_combo.setMinimumWidth(200)
        param_layout.addWidget(self.method_combo, 0, 1)

        self.auto_check = QCheckBox(self.tr("Auto cutoff"))
        self.auto_check.setChecked(True)
        self.auto_check.toggled.connect(self._toggle_auto)
        param_layout.addWidget(self.auto_check, 0, 2)

        self.cutoff_label = QLabel(self.tr("Cutoff:"))
        self.cutoff_label.setWordWrap(True)
        param_layout.addWidget(self.cutoff_label, 1, 0)
        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setRange(0.0, 0.9)
        self.cutoff_spin.setSingleStep(0.05)
        self.cutoff_spin.setValue(0.1)
        self.cutoff_spin.setEnabled(False)
        self.cutoff_spin.setMinimumWidth(160)
        param_layout.addWidget(self.cutoff_spin, 1, 1)

        self.qc_check = QCheckBox(self.tr("Enable QC-RSD pre-filter"))
        self.qc_check.setChecked(False)
        self.qc_check.setEnabled(False)
        param_layout.addWidget(self.qc_check, 2, 0, 1, 2)

        self.qc_thresh_label = QLabel(self.tr("QC-RSD threshold:"))
        self.qc_thresh_label.setWordWrap(True)
        param_layout.addWidget(self.qc_thresh_label, 2, 2)
        self.qc_thresh_spin = QDoubleSpinBox()
        self.qc_thresh_spin.setRange(0.05, 1.0)
        self.qc_thresh_spin.setSingleStep(0.05)
        self.qc_thresh_spin.setValue(0.20)
        self.qc_thresh_spin.setEnabled(False)
        self.qc_thresh_spin.setMinimumWidth(160)
        param_layout.addWidget(self.qc_thresh_spin, 2, 3)

        self.qc_check.toggled.connect(self.qc_thresh_spin.setEnabled)
        self.btn_run = QPushButton(self.tr("Apply Filtering Step"))
        self.btn_run.setMinimumWidth(220)
        self.btn_run.clicked.connect(self._run)
        param_layout.addWidget(self.btn_run, 3, 0, 1, 2)

        self.param_group.setLayout(param_layout)
        layout.addWidget(self.param_group)

        self.log_group = QGroupBox(self.tr("Processing Log"))
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(260)
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group, stretch=1)
        layout.addStretch()

    def retranslateUi(self):
        self.info_group.setTitle(self.tr("Current Data"))
        self.param_group.setTitle(self.tr("Filter Parameters"))
        self.log_group.setTitle(self.tr("Processing Log"))
        self.method_label.setText(self.tr("Filter method:"))
        self.auto_check.setText(self.tr("Auto cutoff"))
        self.cutoff_label.setText(self.tr("Cutoff:"))
        self.qc_check.setText(self.tr("Enable QC-RSD pre-filter"))
        self.qc_thresh_label.setText(self.tr("QC-RSD threshold:"))
        self.btn_run.setText(self.tr("Apply Filtering Step"))

    def connect_state_changed(self, callback: Callable[..., None]) -> None:
        self.method_combo.currentIndexChanged.connect(callback)
        self.auto_check.toggled.connect(callback)
        self.cutoff_spin.valueChanged.connect(callback)
        self.qc_check.toggled.connect(callback)
        self.qc_thresh_spin.valueChanged.connect(callback)

    def read_state(self) -> dict[str, Any]:
        return {
            "pipeline": {
                "filter_method": self.method_combo.currentData(),
                "filter_cutoff": (
                    None if self.auto_check.isChecked() else float(self.cutoff_spin.value())
                ),
                "qc_rsd_enabled": bool(
                    self.qc_check.isChecked() and self.qc_check.isEnabled()
                ),
                "qc_rsd_threshold": float(self.qc_thresh_spin.value()),
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
                pipeline.get("filter_method"),
                "pipeline.filter_method",
            )
        )
        return result

    def apply_state(self, state: Mapping[str, Any]) -> ApplyStateResult:
        pipeline = state.get("pipeline", {})
        if not isinstance(pipeline, Mapping):
            return ApplyStateResult()

        if "filter_cutoff" in pipeline:
            auto_cutoff = pipeline["filter_cutoff"] is None
            apply_checked(self.auto_check, bool(auto_cutoff))
            self._toggle_auto(auto_cutoff)
            if pipeline["filter_cutoff"] is not None:
                apply_spin_value(self.cutoff_spin, float(pipeline["filter_cutoff"]))

        if "qc_rsd_enabled" in pipeline:
            if not self.qc_check.isEnabled() and bool(pipeline["qc_rsd_enabled"]):
                self.qc_check.setEnabled(True)
            apply_checked(self.qc_check, bool(pipeline["qc_rsd_enabled"]))
        if "qc_rsd_threshold" in pipeline:
            apply_spin_value(self.qc_thresh_spin, float(pipeline["qc_rsd_threshold"]))
        self.qc_thresh_spin.setEnabled(
            bool(self.qc_check.isChecked() and self.qc_check.isEnabled())
        )

        result = self.validate_state(state)
        return result

    def _toggle_auto(self, checked: bool):
        self.cutoff_spin.setEnabled(not checked)

    def _detect_qc(self, labels) -> int:
        """Return the number of QC samples detected in labels."""
        if labels is None:
            return 0
        if isinstance(labels, pd.Series):
            values = labels.astype(str)
        else:
            values = pd.Series(labels).astype(str)
        return int(values.str.contains("qc", case=False, na=False).sum())

    def on_data_updated(self):
        df = self.mw.current_data
        if df is None:
            return

        auto_cutoff = get_auto_cutoff(df.shape[1])
        self.cutoff_spin.setValue(auto_cutoff)

        qc_count = self._detect_qc(
            self.mw.raw_labels if hasattr(self.mw, "raw_labels") else self.mw.labels
        )
        self._has_qc = qc_count >= 2
        self.qc_check.setEnabled(self._has_qc)
        if not self._has_qc:
            self.qc_check.setChecked(False)

        self.info_label.setText(
            self.tr(
                "Features: {features} | Samples: {samples}\n"
                "Recommended auto cutoff: {cutoff:.0%}\n"
                "QC samples detected: {qc_detected}"
            ).format(
                features=df.shape[1],
                samples=df.shape[0],
                cutoff=auto_cutoff,
                qc_detected=(
                    self.tr("Yes ({n})").format(n=qc_count)
                    if qc_count >= 2
                    else self.tr("No") if qc_count == 0 else self.tr("Only 1 (need >=2)")
                ),
            )
        )

    def _run(self):
        if not self.mw.check_data_ready():
            return

        method = self.method_combo.currentData()
        cutoff = None if self.auto_check.isChecked() else self.cutoff_spin.value()
        qc_enabled = bool(self.qc_check.isChecked() and self._has_qc)
        qc_threshold = self.qc_thresh_spin.value()

        self.btn_run.setEnabled(False)
        self.log_text.setPlainText(self.tr("Running pipeline (filtering stage)..."))

        self.mw.set_pipeline_params(
            filter_method=method,
            filter_cutoff=cutoff,
            qc_rsd_enabled=qc_enabled,
            qc_rsd_threshold=qc_threshold,
        )
        self.mw.run_pipeline_async(
            stage="filter",
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
            self.tr("Filtering"),
            step_key="filter",
            labels=labels,
        )
        self.mw.norm_tab.on_data_updated()

    def _on_pipeline_error(self, error_text: str):
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, self.tr("Pipeline Error"), error_text)
