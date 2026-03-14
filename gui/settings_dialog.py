"""Application settings dialog for theme and language preferences."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    """Dialog used to update application appearance and language."""

    def __init__(self, parent=None, current_theme="light", current_locale="zh_TW"):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumWidth(400)
        self._current_theme = current_theme
        self._current_locale = current_locale
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        theme_group = QGroupBox(self.tr("Appearance"))
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel(self.tr("Theme:")))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.tr("Auto"), "auto")
        self.theme_combo.addItem(self.tr("Light"), "light")
        self.theme_combo.addItem(self.tr("Dark"), "dark")
        self.theme_combo.addItem(self.tr("Colorblind-friendly"), "colorblind")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == self._current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        lang_group = QGroupBox(self.tr("Language"))
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.tr("Display language:")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Traditional Chinese", "zh_TW")
        self.lang_combo.addItem("English", "en")
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == self._current_locale:
                self.lang_combo.setCurrentIndex(i)
                break
        lang_layout.addWidget(self.lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

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
