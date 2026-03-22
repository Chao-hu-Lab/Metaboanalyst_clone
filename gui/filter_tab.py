"""
Variable filtering tab (+ optional QC-RSD filtering).
"""

from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import (
    QCheckBox,
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

from ms_core.processing.feature_filter import FILTER_METHODS, get_auto_cutoff


class FilterTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._has_qc = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.info_group = QGroupBox(self.tr("Current Data"))
        info_layout = QVBoxLayout()
        self.info_label = QLabel(self.tr("Apply missing-value step first."))
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        self.param_group = QGroupBox(self.tr("Filter Parameters"))
        param_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.method_label = QLabel(self.tr("Filter method:"))
        row1.addWidget(self.method_label)
        self.method_combo = QComboBox()
        for key, label in FILTER_METHODS.items():
            if key == "None":
                continue
            self.method_combo.addItem(label, key)
        row1.addWidget(self.method_combo)

        self.auto_check = QCheckBox(self.tr("Auto cutoff"))
        self.auto_check.setChecked(True)
        self.auto_check.toggled.connect(self._toggle_auto)
        row1.addWidget(self.auto_check)

        self.cutoff_label = QLabel(self.tr("Cutoff:"))
        row1.addWidget(self.cutoff_label)
        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setRange(0.0, 0.9)
        self.cutoff_spin.setSingleStep(0.05)
        self.cutoff_spin.setValue(0.1)
        self.cutoff_spin.setEnabled(False)
        row1.addWidget(self.cutoff_spin)
        param_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.qc_check = QCheckBox(self.tr("Enable QC-RSD pre-filter"))
        self.qc_check.setChecked(False)
        self.qc_check.setEnabled(False)
        row2.addWidget(self.qc_check)

        self.qc_thresh_label = QLabel(self.tr("QC-RSD threshold:"))
        row2.addWidget(self.qc_thresh_label)
        self.qc_thresh_spin = QDoubleSpinBox()
        self.qc_thresh_spin.setRange(0.05, 1.0)
        self.qc_thresh_spin.setSingleStep(0.05)
        self.qc_thresh_spin.setValue(0.20)
        self.qc_thresh_spin.setEnabled(False)
        row2.addWidget(self.qc_thresh_spin)

        self.qc_check.toggled.connect(self.qc_thresh_spin.setEnabled)
        param_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_run = QPushButton(self.tr("Apply Filtering Step"))
        self.btn_run.clicked.connect(self._run)
        row3.addWidget(self.btn_run)
        row3.addStretch()
        param_layout.addLayout(row3)

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
