"""Compact preset manager bar shown below the pipeline navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
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

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(10)
        top_grid.setVerticalSpacing(6)

        self.source_label = QLabel(self.tr("Preset:"))
        self.source_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        top_grid.addWidget(self.source_label, 0, 0)

        self.source_value_label = QLabel(self.tr("Not loaded"))
        self.source_value_label.setWordWrap(True)
        self.source_value_label.setMinimumWidth(220)
        self.source_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top_grid.addWidget(self.source_value_label, 0, 1, 1, 3)

        self.state_label = QLabel(self.tr("State:"))
        self.state_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        top_grid.addWidget(self.state_label, 0, 4)

        self.state_value_label = QLabel("Unsaved")
        self.state_value_label.setStyleSheet(
            "font-weight: bold; color: #0d47a1; background: transparent;"
        )
        top_grid.addWidget(self.state_value_label, 0, 5)

        self.load_button = QPushButton(self.tr("Load Preset"))
        self.load_button.setMinimumWidth(130)
        top_grid.addWidget(self.load_button, 1, 0)

        self.apply_button = QPushButton(self.tr("Apply Preset"))
        self.apply_button.setMinimumWidth(130)
        top_grid.addWidget(self.apply_button, 1, 1)

        self.save_button = QPushButton(self.tr("Save As Preset"))
        self.save_button.setMinimumWidth(130)
        top_grid.addWidget(self.save_button, 1, 2)

        self.reset_button = QPushButton(self.tr("Reset To Defaults"))
        self.reset_button.setMinimumWidth(150)
        top_grid.addWidget(self.reset_button, 1, 3)

        layout.addLayout(top_grid)

        bottom_grid = QGridLayout()
        bottom_grid.setHorizontalSpacing(10)
        bottom_grid.setVerticalSpacing(6)

        self.summary_label = QLabel(self.tr("Summary:"))
        self.summary_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        bottom_grid.addWidget(self.summary_label, 0, 0)

        self.summary_value_label = QLabel(self.tr("Defaults only"))
        self.summary_value_label.setWordWrap(True)
        bottom_grid.addWidget(self.summary_value_label, 0, 1)

        self.ignored_label = QLabel(self.tr("Ignored:"))
        self.ignored_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        bottom_grid.addWidget(self.ignored_label, 1, 0)

        self.ignored_value_label = QLabel(self.tr("None"))
        self.ignored_value_label.setWordWrap(True)
        bottom_grid.addWidget(self.ignored_value_label, 1, 1)

        layout.addLayout(bottom_grid)

    def retranslateUi(self) -> None:
        self.source_label.setText(self.tr("Preset:"))
        self.state_label.setText(self.tr("State:"))
        self.load_button.setText(self.tr("Load Preset"))
        self.apply_button.setText(self.tr("Apply Preset"))
        self.save_button.setText(self.tr("Save As Preset"))
        self.reset_button.setText(self.tr("Reset To Defaults"))
        self.summary_label.setText(self.tr("Summary:"))
        self.ignored_label.setText(self.tr("Ignored:"))
