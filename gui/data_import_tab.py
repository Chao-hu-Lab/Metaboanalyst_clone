"""
Data import tab.

Features:
- File picker: CSV / TSV / Excel
- QTableView preview (sortable Pandas model)
- Orientation switch (samples as rows / samples as columns)
- Mapping selectors for sample and group metadata
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.feature_metadata import default_feature_metadata, extract_feature_metadata
from core.sample_interface import identify_sample_columns
from core.sample_info import read_sample_info_sheet
from gui.widgets.pandas_model import create_sortable_model


class DataImportTab(QWidget):
    """Load tabular metabolomics data and hand off parsed matrix to MainWindow."""

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._raw_df: pd.DataFrame | None = None
        self._sample_info_df: pd.DataFrame | None = None
        self._preview_source_model = None
        self._preview_proxy_model = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        file_group = QGroupBox()
        file_layout = QVBoxLayout()
        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(self.tr("Select CSV/TSV/Excel file..."))
        file_row.addWidget(self.path_edit, stretch=1)

        self.btn_browse = QPushButton()
        self.btn_browse.clicked.connect(self._browse_file)
        file_row.addWidget(self.btn_browse)

        self.btn_preview = QPushButton()
        self.btn_preview.clicked.connect(self._preview_current_path)
        file_row.addWidget(self.btn_preview)

        self.btn_import_dnp = QPushButton()
        self.btn_import_dnp.clicked.connect(self._import_from_dnp)
        self.btn_import_dnp.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #1557b0; }"
        )
        file_row.addWidget(self.btn_import_dnp)

        file_layout.addLayout(file_row)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        mapping_group = QGroupBox()
        mapping_layout = QVBoxLayout()

        orientation_row = QHBoxLayout()
        self.orientation_label = QLabel()
        orientation_row.addWidget(self.orientation_label)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem(self.tr("Samples as rows"), "rows")
        self.orientation_combo.addItem(self.tr("Samples as columns"), "cols")
        self.orientation_combo.currentIndexChanged.connect(self._on_orientation_changed)
        orientation_row.addWidget(self.orientation_combo)
        orientation_row.addStretch()
        mapping_layout.addLayout(orientation_row)

        sample_row = QHBoxLayout()
        self.sample_label = QLabel()
        sample_row.addWidget(self.sample_label)
        self.sample_combo = QComboBox()
        self.sample_combo.currentIndexChanged.connect(self._on_sample_mapping_changed)
        sample_row.addWidget(self.sample_combo)
        mapping_layout.addLayout(sample_row)

        group_row = QHBoxLayout()
        self.group_label = QLabel()
        group_row.addWidget(self.group_label)
        self.group_combo = QComboBox()
        group_row.addWidget(self.group_combo)
        mapping_layout.addLayout(group_row)

        action_row = QHBoxLayout()
        self.btn_load = QPushButton()
        self.btn_load.clicked.connect(self._load_into_main)
        action_row.addWidget(self.btn_load)
        action_row.addStretch()
        mapping_layout.addLayout(action_row)

        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)

        preview_group = QGroupBox()
        preview_layout = QVBoxLayout()

        self.preview_table = QTableView()
        self.preview_table.setSortingEnabled(True)
        self.preview_table.setAlternatingRowColors(True)
        preview_layout.addWidget(self.preview_table, stretch=1)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(120)
        preview_layout.addWidget(self.info_text)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, stretch=1)

        self.file_group = file_group
        self.mapping_group = mapping_group
        self.preview_group = preview_group
        self.retranslateUi()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslateUi(self):
        self.file_group.setTitle(self.tr("File Selection"))
        self.mapping_group.setTitle(self.tr("Column Mapping"))
        self.preview_group.setTitle(self.tr("Preview"))
        self.btn_browse.setText(self.tr("Browse..."))
        self.btn_preview.setText(self.tr("Preview"))
        self.btn_import_dnp.setText(self.tr("Import from DNP"))
        self.orientation_label.setText(self.tr("Data orientation:"))
        self.btn_load.setText(self.tr("Load Data"))
        self._update_mapping_labels()

    # ------------------------------------------------------------------
    # File loading + preview
    # ------------------------------------------------------------------

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select data file"),
            "",
            "Data files (*.csv *.tsv *.txt *.xlsx *.xls);;All files (*.*)",
        )
        if not path:
            return
        self.path_edit.setText(path)
        self._load_file_for_preview(path)

    def _import_from_dnp(self):
        """Import DNP output file and convert to Metaboanalyst format."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select DNP output file"),
            "",
            "Excel files (*.xlsx *.xls);;All files (*.*)",
        )
        if not path:
            return

        # Show loading state
        original_text = self.btn_import_dnp.text()
        self.btn_import_dnp.setText(self.tr("⏳ Importing..."))
        self.btn_import_dnp.setEnabled(False)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

        try:
            try:
                from metabolomics.adapters.dnp_to_metaboanalyst import (
                    convert_dnp_to_metaboanalyst,
                )
            except ImportError:
                desktop = Path.home() / "Desktop"
                dnp_candidates = [
                    desktop / "Data_Normalization_project_v2" / "src",
                    Path(__file__).resolve().parent.parent.parent
                    / "Data_Normalization_project_v2"
                    / "src",
                ]

                dnp_src = None
                for candidate in dnp_candidates:
                    if candidate.exists():
                        dnp_src = candidate
                        break

                if dnp_src is None:
                    raise ImportError(
                        "DNP adapter module not found. Searched:\n"
                        + "\n".join(f"  - {c}" for c in dnp_candidates)
                    )

                path_str = str(dnp_src)
                sys.path.insert(0, path_str)
                try:
                    from metabolomics.adapters.dnp_to_metaboanalyst import (
                        convert_dnp_to_metaboanalyst,
                    )
                finally:
                    try:
                        sys.path.remove(path_str)
                    except ValueError:
                        pass

            # Convert to temp file in same directory
            input_dir = Path(path).parent
            base_name = Path(path).stem
            output_path = str(input_dir / f"Metaboanalyst_import_{base_name}.xlsx")

            result_path = convert_dnp_to_metaboanalyst(path, output_path)

            # Load converted file into the import tab
            self.path_edit.setText(result_path)
            self._load_file_for_preview(result_path)

            QMessageBox.information(
                self,
                self.tr("Import Successful"),
                self.tr("DNP file converted and loaded:\n{path}").format(
                    path=Path(result_path).name
                ),
            )
        except ImportError:
            QMessageBox.critical(
                self,
                self.tr("Adapter Not Found"),
                self.tr(
                    "Could not find DNP adapter module.\n"
                    "Ensure Data_Normalization_project_v2 project is in the expected location."
                ),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self.tr("Import Failed"),
                self.tr("Conversion error:\n{err}").format(err=str(exc)),
            )
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_import_dnp.setText(original_text)
            self.btn_import_dnp.setEnabled(True)

    def _preview_current_path(self):
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please choose a file first."))
            return
        self._load_file_for_preview(path)

    def _load_file_for_preview(self, path: str):
        self._sample_info_df = None
        try:
            df = self._read_table(path)
            self._sample_info_df = read_sample_info_sheet(path)
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Import Error"), str(exc))
            return

        if df.empty:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("File contains no rows."))
            return

        self._raw_df = df
        self._populate_mapping_options()
        self._update_preview(df)

        sample_info_msg = self.tr("SampleInfo sheet: not found")
        if self._sample_info_df is not None and not self._sample_info_df.empty:
            sample_info_msg = self.tr(
                "SampleInfo sheet loaded.\nRows: {rows}\nColumns: {cols}"
            ).format(
                rows=self._sample_info_df.shape[0],
                cols=self._sample_info_df.shape[1],
            )

        self.info_text.setPlainText(
            self.tr(
                "Raw table loaded.\nRows: {rows}\nColumns: {cols}\n"
                "{sample_info}\n"
                "Select orientation and mapping, then click 'Load Data'."
            ).format(rows=df.shape[0], cols=df.shape[1], sample_info=sample_info_msg)
        )

    @staticmethod
    def _read_table(path: str) -> pd.DataFrame:
        ext = Path(path).suffix.lower()
        if ext in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        if ext in {".tsv", ".txt"}:
            return pd.read_csv(path, sep="\t")
        if ext == ".csv":
            try:
                return pd.read_csv(path)
            except Exception:
                return pd.read_csv(path, sep=None, engine="python")
        return pd.read_csv(path, sep=None, engine="python")

    def _update_preview(self, df: pd.DataFrame):
        source, proxy = create_sortable_model(df)
        self._preview_source_model = source
        self._preview_proxy_model = proxy
        self.preview_table.setModel(proxy)
        self.preview_table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    # Mapping selectors
    # ------------------------------------------------------------------

    def _on_orientation_changed(self):
        self._update_mapping_labels()
        self._populate_mapping_options()

    def _on_sample_mapping_changed(self):
        if self.orientation_combo.currentData() == "cols":
            self._populate_group_row_options()

    def _update_mapping_labels(self):
        mode = self.orientation_combo.currentData()
        if mode == "cols":
            self.sample_label.setText(self.tr("Feature ID column:"))
            self.group_label.setText(self.tr("Group row key:"))
        else:
            self.sample_label.setText(self.tr("Sample ID column:"))
            self.group_label.setText(self.tr("Group column:"))

    def _populate_mapping_options(self):
        if self._raw_df is None:
            return

        mode = self.orientation_combo.currentData()
        columns = list(self._raw_df.columns)

        self.sample_combo.blockSignals(True)
        self.group_combo.blockSignals(True)
        self.sample_combo.clear()
        self.group_combo.clear()

        for col in columns:
            self.sample_combo.addItem(str(col), col)

        sample_guess = self._guess_sample_column(columns)
        self.sample_combo.setCurrentIndex(max(0, sample_guess))

        if mode == "cols":
            self._populate_group_row_options()
        else:
            for col in columns:
                self.group_combo.addItem(str(col), col)
            group_guess = self._guess_group_column(columns, sample_guess)
            self.group_combo.setCurrentIndex(max(0, group_guess))

        self.sample_combo.blockSignals(False)
        self.group_combo.blockSignals(False)

    def _populate_group_row_options(self):
        self.group_combo.clear()
        if self._raw_df is None:
            return
        id_col = self.sample_combo.currentData()
        if id_col not in self._raw_df.columns:
            return

        keys = self._raw_df[id_col].astype(str).tolist()
        unique_keys = list(dict.fromkeys(keys))
        for key in unique_keys:
            self.group_combo.addItem(key, key)

        guess = 0
        for idx, key in enumerate(unique_keys):
            lower = key.lower().replace(" ", "").replace("_", "")
            if "group" in lower or "class" in lower or "label" in lower:
                guess = idx
                break
            if lower in {"sampletype", "type", "category", "condition", "treatment"}:
                guess = idx
                break
        self.group_combo.setCurrentIndex(guess)

    @staticmethod
    def _guess_sample_column(columns: list) -> int:
        for idx, col in enumerate(columns):
            lower = str(col).strip().lower()
            if lower in {"sample", "sampleid", "sample_id", "name", "id"}:
                return idx
        return 0

    @staticmethod
    def _guess_group_column(columns: list, sample_idx: int) -> int:
        # Priority 1: exact-ish group/class/label keywords
        for idx, col in enumerate(columns):
            lower = str(col).strip().lower()
            if "group" in lower or "class" in lower or "label" in lower:
                return idx
        # Priority 2: sample-type / category keywords
        for idx, col in enumerate(columns):
            lower = str(col).strip().lower().replace(" ", "").replace("_", "")
            if lower in {"sampletype", "type", "category", "condition", "treatment"}:
                return idx
        # No confident guess — return -1 so combo stays at 0 via max(0, -1)
        return -1

    # ------------------------------------------------------------------
    # Parse + send to MainWindow
    # ------------------------------------------------------------------

    def _load_into_main(self):
        if self._raw_df is None:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please load and preview a file first."))
            return

        try:
            mode = self.orientation_combo.currentData()
            if mode == "cols":
                matrix, labels, feature_metadata, sample_col, group_col = self._parse_samples_as_columns()
            else:
                matrix, labels, feature_metadata, sample_col, group_col = self._parse_samples_as_rows()
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Import Error"), str(exc))
            return

        self.mw.set_data(
            matrix,
            labels,
            feature_metadata=feature_metadata,
            sample_col=sample_col,
            group_col=group_col,
            sample_info=self._sample_info_df,
        )
        self.mw.show_shared_table(matrix)
        self.info_text.setPlainText(
            self.tr(
                "Dataset loaded into pipeline.\n"
                "Samples: {samples}\nFeatures: {features}\n"
                "Groups: {groups}"
            ).format(
                samples=matrix.shape[0],
                features=matrix.shape[1],
                groups=", ".join(sorted(set(labels.astype(str)))),
            )
        )

    def _parse_samples_as_rows(self):
        df = self._raw_df.copy()
        sample_col = self.sample_combo.currentData()
        group_col = self.group_combo.currentData()

        if sample_col not in df.columns:
            raise ValueError(self.tr("Invalid sample ID column selection."))
        if group_col not in df.columns:
            raise ValueError(self.tr("Invalid group column selection."))
        if sample_col == group_col:
            raise ValueError(self.tr("Sample ID column and group column must be different."))

        sample_ids = df[sample_col].astype(str)
        if sample_ids.duplicated().any():
            dup = sample_ids[sample_ids.duplicated()].iloc[0]
            raise ValueError(
                self.tr("Duplicate sample ID detected: {sample}").format(sample=dup)
            )

        feature_cols = [c for c in df.columns if c not in {sample_col, group_col}]
        if not feature_cols:
            raise ValueError(self.tr("No feature columns found after metadata columns are removed."))

        matrix = df.loc[:, feature_cols].apply(pd.to_numeric, errors="coerce")
        matrix = matrix.dropna(axis=1, how="all")
        if matrix.empty:
            raise ValueError(self.tr("No numeric feature columns found."))

        matrix.index = pd.Index(sample_ids.values, name=str(sample_col))
        feature_index = pd.Index(self._make_unique(matrix.columns), name="Feature")
        matrix.columns = feature_index
        feature_metadata = default_feature_metadata(feature_index)

        labels = pd.Series(df[group_col].astype(str).values, index=matrix.index, name=str(group_col))
        return matrix, labels, feature_metadata, str(sample_col), str(group_col)

    def _parse_samples_as_columns(self):
        df = self._raw_df.copy()
        id_col = self.sample_combo.currentData()
        group_key = self.group_combo.currentData()

        if id_col not in df.columns:
            raise ValueError(self.tr("Invalid feature ID column selection."))
        if group_key is None:
            raise ValueError(self.tr("Please select a group row key."))

        sample_columns = [col for col in identify_sample_columns(df) if col != id_col]
        if not sample_columns:
            raise ValueError(self.tr("No sample columns found."))

        id_values = df[id_col].astype(str)
        group_rows = df[id_values == str(group_key)]
        if group_rows.empty:
            raise ValueError(self.tr("Selected group row key was not found."))
        if len(group_rows) > 1:
            raise ValueError(self.tr("Group row key must be unique."))

        group_row = group_rows.iloc[0]
        feature_rows = df[id_values != str(group_key)].copy()
        if feature_rows.empty:
            raise ValueError(self.tr("No feature rows remain after removing group row."))

        feature_index = pd.Index(
            self._make_unique(feature_rows[id_col].astype(str).tolist()),
            name="Feature",
        )
        matrix = feature_rows.loc[:, sample_columns].apply(pd.to_numeric, errors="coerce").T
        matrix.index = pd.Index([str(col) for col in sample_columns], name=self.tr("Sample"))
        matrix.columns = feature_index
        matrix = matrix.dropna(axis=1, how="all")
        if matrix.empty:
            raise ValueError(self.tr("No numeric feature columns found after transpose."))
        feature_metadata = extract_feature_metadata(
            feature_rows.reset_index(drop=True),
            feature_index,
        )

        labels = pd.Series(
            group_row.loc[sample_columns].astype(str).values,
            index=matrix.index,
            name=str(group_key),
        )
        return matrix, labels, feature_metadata, str(id_col), str(group_key)

    @staticmethod
    def _make_unique(values) -> list[str]:
        counts: dict[str, int] = {}
        output: list[str] = []
        for raw in values:
            key = str(raw)
            n = counts.get(key, 0)
            counts[key] = n + 1
            output.append(key if n == 0 else f"{key}_{n+1}")
        return output
