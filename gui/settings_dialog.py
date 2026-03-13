"""
設定對話框 — 主題 / 語言 偏好設定
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QDialogButtonBox,
)


class SettingsDialog(QDialog):
    """應用程式偏好設定對話框"""

    def __init__(self, parent=None, current_theme="auto", current_locale="zh_TW"):
        super().__init__(parent)
        self.setWindowTitle(self.tr("偏好設定"))
        self.setMinimumWidth(400)
        self._current_theme = current_theme
        self._current_locale = current_locale
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ── 主題設定 ──
        theme_group = QGroupBox(self.tr("外觀"))
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel(self.tr("主題:")))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.tr("自動 (跟隨系統)"), "auto")
        self.theme_combo.addItem(self.tr("淺色模式"), "light")
        self.theme_combo.addItem(self.tr("深色模式"), "dark")
        # 設定目前值
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == self._current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # ── 語言設定 ──
        lang_group = QGroupBox(self.tr("語言"))
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.tr("介面語言:")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("繁體中文", "zh_TW")
        self.lang_combo.addItem("English", "en")
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == self._current_locale:
                self.lang_combo.setCurrentIndex(i)
                break
        lang_layout.addWidget(self.lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # ── 按鈕 ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def selected_theme(self) -> str:
        return self.theme_combo.currentData()

    @property
    def selected_locale(self) -> str:
        return self.lang_combo.currentData()
