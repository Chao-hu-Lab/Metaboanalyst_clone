"""Compact preset manager bar shown below the pipeline navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PresetBar(QFrame):
    """Display preset source, lifecycle state, and actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preset_bar")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame#preset_bar {
                background-color: #f5f8fb;
                border-top: 1px solid #d8e1ea;
                border-bottom: 1px solid #d8e1ea;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.source_label = QLabel(self.tr("Preset:"))
        top_row.addWidget(self.source_label)

        self.source_value_label = QLabel(self.tr("Not loaded"))
        self.source_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top_row.addWidget(self.source_value_label, stretch=1)

        self.state_label = QLabel(self.tr("State:"))
        top_row.addWidget(self.state_label)

        self.state_value_label = QLabel("Unsaved")
        self.state_value_label.setStyleSheet(
            "font-weight: bold; color: #0d47a1; background: transparent;"
        )
        top_row.addWidget(self.state_value_label)

        self.load_button = QPushButton(self.tr("Load Preset"))
        top_row.addWidget(self.load_button)

        self.apply_button = QPushButton(self.tr("Apply Preset"))
        top_row.addWidget(self.apply_button)

        self.save_button = QPushButton(self.tr("Save As Preset"))
        top_row.addWidget(self.save_button)

        self.reset_button = QPushButton(self.tr("Reset To Defaults"))
        top_row.addWidget(self.reset_button)

        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.summary_label = QLabel(self.tr("Summary:"))
        bottom_row.addWidget(self.summary_label)

        self.summary_value_label = QLabel(self.tr("Defaults only"))
        self.summary_value_label.setWordWrap(True)
        bottom_row.addWidget(self.summary_value_label, stretch=1)

        self.ignored_label = QLabel(self.tr("Ignored:"))
        bottom_row.addWidget(self.ignored_label)

        self.ignored_value_label = QLabel(self.tr("None"))
        self.ignored_value_label.setWordWrap(True)
        bottom_row.addWidget(self.ignored_value_label, stretch=1)

        layout.addLayout(bottom_row)

    def retranslateUi(self) -> None:
        self.source_label.setText(self.tr("Preset:"))
        self.state_label.setText(self.tr("State:"))
        self.load_button.setText(self.tr("Load Preset"))
        self.apply_button.setText(self.tr("Apply Preset"))
        self.save_button.setText(self.tr("Save As Preset"))
        self.reset_button.setText(self.tr("Reset To Defaults"))
        self.summary_label.setText(self.tr("Summary:"))
        self.ignored_label.setText(self.tr("Ignored:"))
