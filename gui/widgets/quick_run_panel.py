"""Compact quick-run surface for the simplified GUI workflow."""

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


class QuickRunPanel(QFrame):
    """Show preset/input status and expose the primary run action."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("quick_run_panel")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame#quick_run_panel {
                background-color: #f5f8fb;
                border-top: 1px solid #d8e1ea;
                border-bottom: 1px solid #d8e1ea;
            }
            QLabel#quick_run_state_value {
                font-weight: 700;
                color: #0d47a1;
                background: transparent;
            }
            QPushButton#quick_run_primary_button {
                background-color: #1976d2;
                color: white;
                font-weight: 700;
                padding: 6px 18px;
                border-radius: 4px;
            }
            QPushButton#quick_run_primary_button:disabled {
                background-color: #9fb7d1;
                color: #eef4fb;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(10)
        top_grid.setVerticalSpacing(6)

        self.source_label = QLabel()
        self.source_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        top_grid.addWidget(self.source_label, 0, 0)

        self.source_value_label = QLabel()
        self.source_value_label.setWordWrap(True)
        self.source_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top_grid.addWidget(self.source_value_label, 0, 1, 1, 3)

        self.state_label = QLabel()
        self.state_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        top_grid.addWidget(self.state_label, 0, 4)

        self.state_value_label = QLabel()
        self.state_value_label.setObjectName("quick_run_state_value")
        top_grid.addWidget(self.state_value_label, 0, 5)

        self.input_label = QLabel()
        self.input_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        top_grid.addWidget(self.input_label, 1, 0)

        self.input_value_label = QLabel()
        self.input_value_label.setWordWrap(True)
        self.input_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top_grid.addWidget(self.input_value_label, 1, 1, 1, 5)

        self.data_label = QLabel()
        self.data_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        top_grid.addWidget(self.data_label, 2, 0)

        self.data_value_label = QLabel()
        self.data_value_label.setWordWrap(True)
        top_grid.addWidget(self.data_value_label, 2, 1, 1, 5)

        layout.addLayout(top_grid)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(10)
        action_grid.setVerticalSpacing(6)

        self.load_button = QPushButton()
        self.load_button.setMinimumWidth(130)
        action_grid.addWidget(self.load_button, 0, 0)

        self.browse_button = QPushButton()
        self.browse_button.setMinimumWidth(130)
        action_grid.addWidget(self.browse_button, 0, 1)

        self.run_button = QPushButton()
        self.run_button.setObjectName("quick_run_primary_button")
        self.run_button.setMinimumWidth(150)
        action_grid.addWidget(self.run_button, 0, 2)

        self.inspect_button = QPushButton()
        self.inspect_button.setMinimumWidth(130)
        action_grid.addWidget(self.inspect_button, 0, 3)

        self.advanced_button = QPushButton()
        self.advanced_button.setCheckable(True)
        self.advanced_button.setMinimumWidth(150)
        action_grid.addWidget(self.advanced_button, 0, 4)

        self.more_button = QPushButton()
        self.more_button.setMinimumWidth(100)
        action_grid.addWidget(self.more_button, 0, 5)

        self.open_output_button = QPushButton()
        self.open_output_button.setMinimumWidth(170)
        action_grid.addWidget(self.open_output_button, 1, 0, 1, 2)

        self.result_value_label = QLabel()
        self.result_value_label.setWordWrap(True)
        self.result_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        action_grid.addWidget(self.result_value_label, 1, 2, 1, 4)

        layout.addLayout(action_grid)

        bottom_grid = QGridLayout()
        bottom_grid.setHorizontalSpacing(10)
        bottom_grid.setVerticalSpacing(6)

        self.summary_label = QLabel()
        self.summary_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        bottom_grid.addWidget(self.summary_label, 0, 0)

        self.summary_value_label = QLabel()
        self.summary_value_label.setWordWrap(True)
        bottom_grid.addWidget(self.summary_value_label, 0, 1)

        self.ignored_label = QLabel()
        self.ignored_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        bottom_grid.addWidget(self.ignored_label, 1, 0)

        self.ignored_value_label = QLabel()
        self.ignored_value_label.setWordWrap(True)
        bottom_grid.addWidget(self.ignored_value_label, 1, 1)

        layout.addLayout(bottom_grid)

        self.retranslateUi()

    def retranslateUi(self) -> None:
        self.source_label.setText(self.tr("Preset:"))
        self.state_label.setText(self.tr("State:"))
        self.input_label.setText(self.tr("Input:"))
        self.data_label.setText(self.tr("Data:"))
        self.load_button.setText(self.tr("Load Preset"))
        self.browse_button.setText(self.tr("Select Input"))
        self.run_button.setText(self.tr("Run Analysis"))
        self.inspect_button.setText(self.tr("Inspect Data"))
        self.advanced_button.setText(self.tr("Show Advanced"))
        self.more_button.setText(self.tr("More"))
        self.open_output_button.setText(self.tr("Open Output Folder"))
        self.summary_label.setText(self.tr("Summary:"))
        self.ignored_label.setText(self.tr("Ignored:"))

