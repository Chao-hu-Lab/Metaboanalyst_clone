"""
PandasTableModel — 零複製 pandas DataFrame → QTableView 橋接
"""

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel


class PandasTableModel(QAbstractTableModel):
    """零複製 pandas → QTableView 橋接"""

    def __init__(self, df: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self._df = df if df is not None else pd.DataFrame()

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._df.iloc[index.row(), index.column()]
            if isinstance(val, float):
                return f"{val:.4g}"
            return str(val)
        if role == Qt.ItemDataRole.UserRole:
            # Return raw Python value for sorting
            val = self._df.iloc[index.row(), index.column()]
            return val
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])

    def update_dataframe(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._df


class NumericSortProxy(QSortFilterProxyModel):
    """Sort proxy that compares raw values via UserRole for correct numeric ordering."""

    def lessThan(self, left, right):
        left_val = self.sourceModel().data(left, Qt.ItemDataRole.UserRole)
        right_val = self.sourceModel().data(right, Qt.ItemDataRole.UserRole)

        # Try numeric comparison first
        try:
            return float(left_val) < float(right_val)
        except (TypeError, ValueError):
            pass

        # Fall back to case-insensitive string comparison
        return str(left_val).lower() < str(right_val).lower()


def create_sortable_model(df: pd.DataFrame) -> tuple:
    """建立可排序的 Model + Proxy，回傳 (source_model, proxy_model)"""
    source = PandasTableModel(df)
    proxy = NumericSortProxy()
    proxy.setSourceModel(source)
    return source, proxy
