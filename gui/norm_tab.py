"""
Normalization tab:
Row normalization -> transformation -> batch correction -> scaling
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.batch_correction import (
    BATCH_CORRECTION_METHODS,
    build_combat_design,
    evaluate_combat_design,
    identify_combat_sample_info_covariates,
    list_combat_reference_batches,
)
from ms_core.processing.normalization import ROW_NORM_METHODS
from core.sample_info import build_aligned_factors, detect_factor_columns
from ms_core.processing.scaling import SCALING_METHODS
from ms_core.processing.transformation import TRANSFORM_METHODS
from gui.state_binding import ApplyStateResult, apply_combo_data


_ROW_NORM_ZH_LABELS = {
    "None": "不做正規化",
    "SumNorm": "依列總和正規化",
    "MedianNorm": "依列中位數正規化",
    "SamplePQN": "使用參考樣本的 PQN",
    "GroupPQN": "使用參考群組的 PQN",
    "CompNorm": "依內標準正規化",
    "QuantileNorm": "分位數正規化",
    "SpecNorm": "依外部因子正規化",
}

_TRANSFORM_EN_LABELS = {
    "None": "No transformation",
    "LogNorm": "Generalized Log2 (glog2)",
    "Log10Norm": "Generalized Log10 (glog10)",
    "SrNorm": "Generalized square root (gsqrt)",
    "CrNorm": "Cube root",
}

_BATCH_CORRECTION_ZH_LABELS = {
    "None": "不做批次校正",
    "ComBat": "ComBat 經驗貝氏校正",
}

_COMBAT_MODE_EN_LABELS = {
    "none": "No biological covariates",
    "labels": "Preserve current labels",
    "sample_info": "Preserve selected SampleInfo covariates",
}

_COMBAT_MODE_ZH_LABELS = {
    "none": "不保留生物 covariates",
    "labels": "保留目前 labels",
    "sample_info": "保留選定的 SampleInfo covariates",
}

_SCALING_EN_LABELS = {
    "None": "No scaling",
    "MeanCenter": "Mean centering",
    "AutoNorm": "Auto scaling (Z-score)",
    "ParetoNorm": "Pareto scaling",
    "RangeNorm": "Range scaling",
}


class NormTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._pending_combat_covariates: list[str] = []
        self._pending_combat_ref_batch: str | None = None
        self._combat_base_status = ""
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
        self.info_label = QLabel(self.tr("Apply filtering step first."))
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        self.settings_group = QGroupBox(self.tr("Normalization Pipeline"))
        settings_layout = QGridLayout()
        settings_layout.setHorizontalSpacing(12)
        settings_layout.setVerticalSpacing(8)

        self.row_label = QLabel(self.tr("1. Row normalization:"))
        self.row_label.setWordWrap(True)
        settings_layout.addWidget(self.row_label, 0, 0)
        self.row_combo = QComboBox()
        self.row_combo.setMinimumWidth(220)
        self.row_combo.currentIndexChanged.connect(self._on_row_method_changed)
        settings_layout.addWidget(self.row_combo, 0, 1, 1, 2)

        self.factor_label = QLabel(self.tr("SampleInfo factor column:"))
        self.factor_label.setWordWrap(True)
        settings_layout.addWidget(self.factor_label, 1, 0)
        self.factor_combo = QComboBox()
        self.factor_combo.setMinimumWidth(220)
        settings_layout.addWidget(self.factor_combo, 1, 1)
        self.factor_refresh_btn = QPushButton(self.tr("Refresh SampleInfo"))
        self.factor_refresh_btn.setMinimumWidth(170)
        self.factor_refresh_btn.clicked.connect(self._refresh_factor_controls)
        settings_layout.addWidget(self.factor_refresh_btn, 1, 2)

        self.factor_status = QLabel("")
        self.factor_status.setWordWrap(True)
        settings_layout.addWidget(self.factor_status, 2, 0, 1, 3)

        self.trans_label = QLabel(self.tr("2. Transformation:"))
        self.trans_label.setWordWrap(True)
        settings_layout.addWidget(self.trans_label, 3, 0)
        self.trans_combo = QComboBox()
        self.trans_combo.setMinimumWidth(220)
        settings_layout.addWidget(self.trans_combo, 3, 1, 1, 2)

        self.batch_label = QLabel(self.tr("3. Batch correction:"))
        self.batch_label.setWordWrap(True)
        settings_layout.addWidget(self.batch_label, 4, 0)
        self.batch_combo = QComboBox()
        self.batch_combo.setMinimumWidth(220)
        self.batch_combo.currentIndexChanged.connect(self._on_batch_method_changed)
        settings_layout.addWidget(self.batch_combo, 4, 1, 1, 2)

        self.combat_mode_label = QLabel(self.tr("ComBat covariate mode:"))
        self.combat_mode_label.setWordWrap(True)
        settings_layout.addWidget(self.combat_mode_label, 5, 0)
        self.combat_mode_combo = QComboBox()
        self.combat_mode_combo.setMinimumWidth(220)
        self.combat_mode_combo.currentIndexChanged.connect(self._on_combat_mode_changed)
        settings_layout.addWidget(self.combat_mode_combo, 5, 1, 1, 2)

        self.combat_covariates_label = QLabel(self.tr("SampleInfo covariates:"))
        self.combat_covariates_label.setWordWrap(True)
        settings_layout.addWidget(self.combat_covariates_label, 6, 0)
        self.combat_covariate_list = QListWidget()
        self.combat_covariate_list.setMinimumHeight(110)
        self.combat_covariate_list.itemChanged.connect(lambda *_: self._on_combat_mode_changed())
        settings_layout.addWidget(self.combat_covariate_list, 6, 1, 1, 2)

        self.combat_mean_only_check = QCheckBox(self.tr("Mean-only correction"))
        settings_layout.addWidget(self.combat_mean_only_check, 7, 1)
        self.combat_par_prior_check = QCheckBox(self.tr("Parametric prior"))
        self.combat_par_prior_check.setChecked(True)
        settings_layout.addWidget(self.combat_par_prior_check, 7, 2)

        self.combat_ref_batch_label = QLabel(self.tr("Reference batch:"))
        self.combat_ref_batch_label.setWordWrap(True)
        settings_layout.addWidget(self.combat_ref_batch_label, 8, 0)
        self.combat_ref_batch_combo = QComboBox()
        self.combat_ref_batch_combo.setMinimumWidth(220)
        settings_layout.addWidget(self.combat_ref_batch_combo, 8, 1, 1, 2)

        self.combat_status = QLabel("")
        self.combat_status.setWordWrap(True)
        settings_layout.addWidget(self.combat_status, 9, 0, 1, 3)

        self.scale_label = QLabel(self.tr("4. Scaling:"))
        self.scale_label.setWordWrap(True)
        settings_layout.addWidget(self.scale_label, 10, 0)
        self.scale_combo = QComboBox()
        self.scale_combo.setMinimumWidth(220)
        settings_layout.addWidget(self.scale_combo, 10, 1, 1, 2)

        self.btn_run = QPushButton(self.tr("Apply Full Normalization Pipeline"))
        self.btn_run.setProperty("variant", "primary")
        self.btn_run.setMinimumWidth(240)
        self.btn_run.clicked.connect(self._run)
        settings_layout.addWidget(self.btn_run, 11, 1)

        self.btn_reset = QPushButton(self.tr("Reset to Filtered Data"))
        self.btn_reset.setMinimumWidth(220)
        self.btn_reset.clicked.connect(self._reset)
        settings_layout.addWidget(self.btn_reset, 11, 2)

        self.settings_group.setLayout(settings_layout)
        layout.addWidget(self.settings_group)

        self.log_group = QGroupBox(self.tr("Processing Log"))
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group, stretch=1)
        self.log_group.setVisible(False)
        layout.addStretch()
        self._reload_method_labels()
        self._refresh_factor_controls()
        self._on_row_method_changed()

    def retranslateUi(self):
        self.info_group.setTitle(self.tr("Current Data"))
        self.settings_group.setTitle(self.tr("Normalization Pipeline"))
        self.log_group.setTitle(self.tr("Processing Log"))
        self.row_label.setText(self.tr("1. Row normalization:"))
        self.factor_label.setText(self.tr("SampleInfo factor column:"))
        self.factor_refresh_btn.setText(self.tr("Refresh SampleInfo"))
        self.trans_label.setText(self.tr("2. Transformation:"))
        self.batch_label.setText(self.tr("3. Batch correction:"))
        self.combat_mode_label.setText(self.tr("ComBat covariate mode:"))
        self.combat_covariates_label.setText(self.tr("SampleInfo covariates:"))
        self.combat_mean_only_check.setText(self.tr("Mean-only correction"))
        self.combat_par_prior_check.setText(self.tr("Parametric prior"))
        self.combat_ref_batch_label.setText(self.tr("Reference batch:"))
        self.scale_label.setText(self.tr("4. Scaling:"))
        self.btn_run.setText(self.tr("Apply Full Normalization Pipeline"))
        self.btn_reset.setText(self.tr("Reset to Filtered Data"))
        self._reload_method_labels()
        self._refresh_factor_controls()
        self._refresh_combat_controls()
        self._on_row_method_changed()
        self._on_batch_method_changed()

    def _is_zh_locale(self) -> bool:
        locale_code = getattr(self.mw, "_current_locale", "en")
        return str(locale_code).lower().startswith("zh")

    def _row_norm_display_labels(self) -> dict[str, str]:
        if self._is_zh_locale():
            return _ROW_NORM_ZH_LABELS
        return ROW_NORM_METHODS

    def _transform_display_labels(self) -> dict[str, str]:
        if self._is_zh_locale():
            return TRANSFORM_METHODS
        return _TRANSFORM_EN_LABELS

    def _batch_correction_display_labels(self) -> dict[str, str]:
        if self._is_zh_locale():
            return _BATCH_CORRECTION_ZH_LABELS
        return BATCH_CORRECTION_METHODS

    def _combat_mode_display_labels(self) -> dict[str, str]:
        if self._is_zh_locale():
            return _COMBAT_MODE_ZH_LABELS
        return _COMBAT_MODE_EN_LABELS

    def _combat_warning_dialog_title(self) -> str:
        return "ComBat 風險提醒" if self._is_zh_locale() else "ComBat Risk Warning"

    def _combat_warning_dialog_text(self, warnings: list[str]) -> str:
        preview = "\n".join(warnings[:3])
        if len(warnings) > 3:
            preview += (
                f"\n(+{len(warnings) - 3} more warnings)"
                if not self._is_zh_locale()
                else self.tr("\n(+{n} more warnings)").format(n=len(warnings) - 3)
            )
        if self._is_zh_locale():
            return self.tr(
                "偵測到批次與類型可能高度重合，ComBat 可能洗掉 biological signal。\n\n{warnings}\n\n仍要繼續嗎？"
            ).format(warnings=preview)
        return (
            "Batch and type appear to overlap strongly, so ComBat may remove biological signal.\n\n"
            f"{preview}\n\nContinue anyway?"
        )

    def _combat_blocked_text(self, message: str) -> str:
        if self._is_zh_locale():
            return self.tr("ComBat 已阻擋：{message}").format(message=message)
        return f"ComBat blocked: {message}"

    def _combat_warning_text(self, message: str) -> str:
        if self._is_zh_locale():
            return self.tr("ComBat 警告：{message}").format(message=message)
        return f"ComBat warnings: {message}"

    def _combat_validation_passed_text(self, counts: str) -> str:
        if self._is_zh_locale():
            return self.tr("ComBat 驗證通過。批次樣本數：{counts}").format(counts=counts)
        return f"ComBat validation passed. Batch counts: {counts}"

    def _scaling_display_labels(self) -> dict[str, str]:
        if self._is_zh_locale():
            return SCALING_METHODS
        return _SCALING_EN_LABELS

    @staticmethod
    def _reload_combo_items(combo: QComboBox, labels: Mapping[str, str]) -> None:
        current_value = combo.currentData()
        blocker = QSignalBlocker(combo)
        combo.clear()
        for key, label in labels.items():
            combo.addItem(label, key)
        if current_value is not None:
            index = combo.findData(current_value)
            if index >= 0:
                combo.setCurrentIndex(index)
        del blocker

    def _reload_method_labels(self) -> None:
        self._reload_combo_items(self.row_combo, self._row_norm_display_labels())
        self._reload_combo_items(self.trans_combo, self._transform_display_labels())
        self._reload_combo_items(self.batch_combo, self._batch_correction_display_labels())
        self._reload_combo_items(self.combat_mode_combo, self._combat_mode_display_labels())
        self._reload_combo_items(self.scale_combo, self._scaling_display_labels())

    def connect_state_changed(self, callback: Callable[..., None]) -> None:
        self.row_combo.currentIndexChanged.connect(callback)
        self.trans_combo.currentIndexChanged.connect(callback)
        self.batch_combo.currentIndexChanged.connect(callback)
        self.combat_mode_combo.currentIndexChanged.connect(callback)
        self.combat_covariate_list.itemChanged.connect(lambda *_: callback())
        self.combat_mean_only_check.toggled.connect(callback)
        self.combat_par_prior_check.toggled.connect(callback)
        self.combat_ref_batch_combo.currentIndexChanged.connect(callback)
        self.scale_combo.currentIndexChanged.connect(callback)
        self.factor_combo.currentIndexChanged.connect(callback)

    def _selected_combat_covariates(self) -> list[str]:
        selected: list[str] = []
        for i in range(self.combat_covariate_list.count()):
            item = self.combat_covariate_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return selected

    def _set_selected_combat_covariates(self, columns: list[str]) -> None:
        wanted = {str(col) for col in columns}
        for i in range(self.combat_covariate_list.count()):
            item = self.combat_covariate_list.item(i)
            column = str(item.data(Qt.ItemDataRole.UserRole))
            item.setCheckState(
                Qt.CheckState.Checked if column in wanted else Qt.CheckState.Unchecked
            )

    def read_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "pipeline": {
                "row_norm": self.row_combo.currentData(),
                "transform": self.trans_combo.currentData(),
                "batch_correction": self.batch_combo.currentData(),
                "scaling": self.scale_combo.currentData(),
            },
            "combat": {
                "covariate_mode": self.combat_mode_combo.currentData(),
                "sample_info_covariates": self._selected_combat_covariates(),
                "mean_only": bool(self.combat_mean_only_check.isChecked()),
                "par_prior": bool(self.combat_par_prior_check.isChecked()),
                "ref_batch": self.combat_ref_batch_combo.currentData(),
            },
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
                    self.batch_combo,
                    pipeline.get("batch_correction"),
                    "pipeline.batch_correction",
                )
            )
            result.extend(
                apply_combo_data(
                    self.scale_combo,
                    pipeline.get("scaling"),
                    "pipeline.scaling",
                )
            )
        combat = state.get("combat", {})
        if isinstance(combat, Mapping):
            result.extend(
                apply_combo_data(
                    self.combat_mode_combo,
                    combat.get("covariate_mode"),
                    "combat.covariate_mode",
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
        combat = state.get("combat", {})
        if isinstance(combat, Mapping):
            self.combat_mean_only_check.setChecked(bool(combat.get("mean_only", False)))
            self.combat_par_prior_check.setChecked(bool(combat.get("par_prior", True)))
            self._pending_combat_covariates = [
                str(value) for value in combat.get("sample_info_covariates", []) if str(value).strip()
            ]
            ref_batch = combat.get("ref_batch")
            self._pending_combat_ref_batch = None if ref_batch is None else str(ref_batch)
            self._refresh_combat_controls()
        self._on_row_method_changed()
        self._on_batch_method_changed()
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

    def _refresh_combat_controls(self) -> None:
        blocker_list = QSignalBlocker(self.combat_covariate_list)
        blocker_ref = QSignalBlocker(self.combat_ref_batch_combo)
        self.combat_covariate_list.clear()
        self.combat_ref_batch_combo.clear()
        self.combat_ref_batch_combo.addItem(self.tr("No reference batch"), None)
        sample_info = getattr(self.mw, "sample_info", None)
        if sample_info is None or sample_info.empty:
            self._combat_base_status = self.tr(
                "SampleInfo sheet not found. ComBat covariates are unavailable."
            )
            self.combat_status.setText(self._combat_base_status)
            del blocker_list
            del blocker_ref
            return

        candidates, rejected = identify_combat_sample_info_covariates(sample_info)
        for column in candidates:
            item = QListWidgetItem(str(column))
            item.setData(Qt.ItemDataRole.UserRole, str(column))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.combat_covariate_list.addItem(item)
        if self._pending_combat_covariates:
            self._set_selected_combat_covariates(self._pending_combat_covariates)
        for batch in list_combat_reference_batches(sample_info):
            self.combat_ref_batch_combo.addItem(str(batch), str(batch))
        if self._pending_combat_ref_batch is not None:
            index = self.combat_ref_batch_combo.findData(self._pending_combat_ref_batch)
            if index >= 0:
                self.combat_ref_batch_combo.setCurrentIndex(index)

        status_text = self.tr(
            "SampleInfo loaded ({rows} x {cols}). ComBat candidate covariates: {n}. Rejected columns: {m}."
        ).format(
            rows=sample_info.shape[0],
            cols=sample_info.shape[1],
            n=len(candidates),
            m=len(rejected),
        )
        if self._pending_combat_covariates:
            missing = [
                value for value in self._pending_combat_covariates if value not in candidates
            ]
            if missing:
                status_text += " " + self.tr("Pending covariates unavailable: {cols}").format(
                    cols=", ".join(missing)
                )
        self._combat_base_status = status_text
        del blocker_list
        del blocker_ref
        self._refresh_combat_validation_status()

    def _resolve_combat_runtime(self) -> dict[str, Any]:
        sample_info = getattr(self.mw, "sample_info", None)
        if sample_info is None or sample_info.empty:
            raise ValueError("SampleInfo sheet with Batch column is required for ComBat.")

        covariate_mode = self.combat_mode_combo.currentData()
        covariate_columns = None
        labels = None
        if covariate_mode == "labels":
            labels = self.mw.labels
        elif covariate_mode == "sample_info":
            covariate_columns = self._selected_combat_covariates()
            if not covariate_columns:
                raise ValueError("Select at least one SampleInfo covariate or switch ComBat mode.")

        batch_labels, covariates, meta = build_combat_design(
            self.mw.current_data.index,
            sample_info,
            labels=labels,
            covariate_columns=covariate_columns,
        )
        validation_covariates = covariates
        if validation_covariates is None and self.mw.labels is not None:
            diagnostic_labels = self.mw.labels.reindex(self.mw.current_data.index)
            if not diagnostic_labels.isna().any() and diagnostic_labels.nunique(dropna=True) > 1:
                validation_covariates = diagnostic_labels.astype("string").rename(
                    "Current labels"
                ).to_frame()
        validation = evaluate_combat_design(batch_labels, validation_covariates)
        return {
            "batch_labels": batch_labels,
            "covariates": covariates,
            "meta": meta,
            "covariate_mode": covariate_mode,
            "validation": validation,
        }

    def _refresh_combat_validation_status(self) -> None:
        if self.batch_combo.currentData() != "ComBat":
            self.combat_status.setText(self._combat_base_status)
            return
        if self.mw.current_data is None:
            self.combat_status.setText(self._combat_base_status)
            return
        try:
            runtime = self._resolve_combat_runtime()
        except Exception as exc:
            self.combat_status.setText(
                self.tr("ComBat validation: {message}").format(message=str(exc))
            )
            return

        validation = runtime["validation"]
        if validation["blocking_errors"]:
            self.combat_status.setText(
                self._combat_blocked_text(validation["blocking_errors"][0])
            )
            return
        if validation["warnings"]:
            preview = " | ".join(validation["warnings"][:2])
            extra_count = max(0, len(validation["warnings"]) - 2)
            if extra_count:
                preview += (
                    self.tr(" (+{n} more warnings)").format(n=extra_count)
                    if self._is_zh_locale()
                    else f" (+{extra_count} more warnings)"
                )
            self.combat_status.setText(self._combat_warning_text(preview))
            return

        batch_counts = runtime["meta"]["batch_counts"]
        counts_text = ", ".join(f"{batch}={count}" for batch, count in batch_counts.items())
        self.combat_status.setText(self._combat_validation_passed_text(counts_text))

    def _on_batch_method_changed(self) -> None:
        is_combat = self.batch_combo.currentData() == "ComBat"
        self.combat_mode_label.setEnabled(is_combat)
        self.combat_mode_combo.setEnabled(is_combat)
        self.combat_mean_only_check.setEnabled(is_combat)
        self.combat_par_prior_check.setEnabled(is_combat)
        self.combat_ref_batch_label.setEnabled(is_combat)
        self.combat_ref_batch_combo.setEnabled(is_combat)
        self._on_combat_mode_changed()

    def _on_combat_mode_changed(self) -> None:
        is_combat = self.batch_combo.currentData() == "ComBat"
        uses_sample_info = self.combat_mode_combo.currentData() == "sample_info"
        self.combat_covariates_label.setEnabled(is_combat and uses_sample_info)
        self.combat_covariate_list.setEnabled(is_combat and uses_sample_info)
        if is_combat and uses_sample_info and self.combat_covariate_list.count() == 0:
            self.combat_status.setText(
                self.tr("No eligible SampleInfo covariates were detected for ComBat.")
            )
            return
        self._refresh_combat_validation_status()

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
        self._refresh_combat_controls()
        self._on_row_method_changed()
        self._on_batch_method_changed()

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
        batch_method = self.batch_combo.currentData()
        scale_method = self.scale_combo.currentData()

        params = {
            "row_norm": row_method,
            "transform": trans_method,
            "batch_correction": batch_method,
            "scaling": scale_method,
            "factors": None,
            "factor_source": None,
            "batch_labels": None,
            "combat_covariates": None,
            "combat_par_prior": bool(self.combat_par_prior_check.isChecked()),
            "combat_mean_only": bool(self.combat_mean_only_check.isChecked()),
            "combat_ref_batch": self.combat_ref_batch_combo.currentData(),
            "combat_source": None,
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

        if batch_method == "ComBat":
            try:
                runtime = self._resolve_combat_runtime()
            except Exception as exc:
                QMessageBox.warning(self, self.tr("Warning"), str(exc))
                return
            validation = runtime["validation"]
            if validation["blocking_errors"]:
                QMessageBox.warning(
                    self,
                    self.tr("Warning"),
                    "\n".join(validation["blocking_errors"]),
                )
                return
            if validation["warnings"]:
                answer = QMessageBox.question(
                    self,
                    self._combat_warning_dialog_title(),
                    self._combat_warning_dialog_text(validation["warnings"]),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            params["batch_labels"] = runtime["batch_labels"]
            params["combat_covariates"] = runtime["covariates"]
            params["combat_source"] = (
                f"{runtime['meta']['batch_source']} ({runtime['covariate_mode']})"
            )
            log_lines = [line for line in self.log_text.toPlainText().splitlines() if line]
            meta = runtime["meta"]
            covar_text = ", ".join(meta["covariate_columns"]) if meta["covariate_columns"] else "None"
            log_lines.append(
                self.tr("ComBat source: {source}; batches={n}; covariates={covars}; mode={mode}").format(
                    source=meta["batch_source"],
                    n=meta["n_batches"],
                    covars=covar_text,
                    mode=runtime["covariate_mode"],
                )
            )
            for warning in validation["warnings"]:
                log_lines.append(self.tr("ComBat warning: {message}").format(message=warning))
            self.log_text.setPlainText("\n".join(log_lines))

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
        self.mw.set_stats_matrix_bundle(payload.get("stats_matrix_bundle"))
        self.btn_run.setEnabled(True)
        self.log_text.setPlainText("\n".join(pipeline_log))
        if hasattr(self.mw, "_append_run_log"):
            self.mw._append_run_log(
                self.tr(
                    "[Normalization] row={row}, transform={transform}, batch={batch}, scaling={scaling}, output shape={samples} x {features}"
                ).format(
                    row=self.row_combo.currentText(),
                    transform=self.trans_combo.currentText(),
                    batch=self.batch_combo.currentText(),
                    scaling=self.scale_combo.currentText(),
                    samples=df.shape[0],
                    features=df.shape[1],
                )
            )
        self.mw.update_data(
            df,
            self.tr("Normalization"),
            step_key="norm",
            labels=labels,
        )

    def _on_pipeline_error(self, error_text: str):
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, self.tr("Pipeline Error"), error_text)
