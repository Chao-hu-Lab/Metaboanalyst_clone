"""
Missing-value handling tab.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from PySide6.QtWidgets import (
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

from ms_core.processing.missing_values import IMPUTE_METHODS
from gui.state_binding import ApplyStateResult, apply_combo_data, apply_spin_value

_IMPUTE_ZH_LABELS: dict[str, str] = dict(IMPUTE_METHODS)
_IMPUTE_EN_LABELS: dict[str, str] = {
    "min": "Minimum positive / 5 (LoD)",
    "mean": "Mean",
    "median": "Median",
    "exclude": "Remove features with missing values",
    "knn": "KNN (k=10)",
    "ppca": "PPCA (nPcs=2)",
    "bpca": "BPCA (nPcs=2)",
    "svd": "SVD (rank=2)",
}


class MissingValueTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
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

        self.info_group = QGroupBox(self.tr("Missing Value Summary"))
        info_layout = QVBoxLayout()
        self.info_label = QLabel(self.tr("Please import data first."))
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        self.param_group = QGroupBox(self.tr("Parameters"))
        param_layout = QGridLayout()
        param_layout.setHorizontalSpacing(12)
        param_layout.setVerticalSpacing(8)

        self.thresh_label = QLabel(self.tr("Missing threshold:"))
        self.thresh_label.setWordWrap(True)
        param_layout.addWidget(self.thresh_label, 0, 0)
        self.thresh_spin = QDoubleSpinBox()
        self.thresh_spin.setRange(0.1, 1.0)
        self.thresh_spin.setSingleStep(0.05)
        self.thresh_spin.setValue(0.5)
        self.thresh_spin.setMinimumWidth(160)
        self.thresh_spin.setToolTip(self.tr("Remove features with missing ratio >= threshold"))
        param_layout.addWidget(self.thresh_spin, 0, 1)

        self.impute_label = QLabel(self.tr("Imputation:"))
        self.impute_label.setWordWrap(True)
        param_layout.addWidget(self.impute_label, 1, 0)
        self.method_combo = QComboBox()
        self._reload_method_labels()
        self.method_combo.setMinimumWidth(200)
        param_layout.addWidget(self.method_combo, 1, 1)

        self.marker_note = QLabel(self._marker_rule_text())
        self.marker_note.setObjectName("missing_value_marker_note")
        self.marker_note.setWordWrap(True)
        param_layout.addWidget(self.marker_note, 2, 0, 1, 2)

        self.btn_run = QPushButton(self.tr("Apply Missing-Value Step"))
        self.btn_run.setProperty("variant", "primary")
        self.btn_run.setMinimumWidth(220)
        self.btn_run.clicked.connect(self._run)
        param_layout.addWidget(self.btn_run, 3, 0, 1, 2)

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
        self.log_group.setVisible(False)
        layout.addStretch()

    def retranslateUi(self):
        self.info_group.setTitle(self.tr("Missing Value Summary"))
        self.param_group.setTitle(self.tr("Parameters"))
        self.log_group.setTitle(self.tr("Processing Log"))
        self.thresh_label.setText(self.tr("Missing threshold:"))
        self.thresh_spin.setToolTip(self.tr("Remove features with missing ratio >= threshold"))
        self.impute_label.setText(self.tr("Imputation:"))
        self._reload_method_labels()
        self.marker_note.setText(self._marker_rule_text())
        self.btn_run.setText(self.tr("Apply Missing-Value Step"))

    def _is_zh_locale(self) -> bool:
        locale = getattr(self.mw, "_current_locale", "en")
        return str(locale).lower().startswith("zh")

    def _reload_method_labels(self) -> None:
        current_method = self.method_combo.currentData()
        labels = _IMPUTE_ZH_LABELS if self._is_zh_locale() else _IMPUTE_EN_LABELS
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        for key in IMPUTE_METHODS:
            self.method_combo.addItem(labels.get(key, key), key)
        if current_method is not None:
            index = self.method_combo.findData(current_method)
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
        self.method_combo.blockSignals(False)

    def _marker_rule_text(self) -> str:
        if self._is_zh_locale():
            return (
                "Presence/absence marker 特徵一律使用 min (LoD) 補值；"
                "你選擇的方法只會套用在非 marker 特徵。"
            )
        return (
            "Presence/absence marker features always use min (LoD) imputation. "
            "The selected method applies to non-marker features only."
        )

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
        if hasattr(self.mw, "_append_run_log"):
            self.mw._append_run_log(
                self.tr(
                    "[Missing Values] threshold={threshold:.0%}, method={method}, output shape={samples} x {features}"
                ).format(
                    threshold=self.thresh_spin.value(),
                    method=self.method_combo.currentText(),
                    samples=df.shape[0],
                    features=df.shape[1],
                )
            )
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
