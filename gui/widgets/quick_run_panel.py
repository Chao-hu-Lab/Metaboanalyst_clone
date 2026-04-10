"""Theme-aware quick-run surface for the simplified GUI workflow."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class QuickRunPanel(QFrame):
    """Show the primary quick-run actions with a clear information hierarchy."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("quick_run_panel")
        self._init_ui()

    def _build_value_row(self, label: QLabel, value: QLabel) -> QWidget:
        row = QWidget(self)
        layout = QGridLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(0)
        label.setObjectName("quick_run_meta_label")
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        value.setObjectName("quick_run_primary_value")
        value.setWordWrap(True)
        layout.addWidget(label, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(value, 0, 1)
        layout.setColumnStretch(1, 1)
        return row

    def _build_detail_row(self, label: QLabel, value: QLabel) -> tuple[QWidget, QGridLayout]:
        row = QWidget(self)
        layout = QGridLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(0)
        label.setObjectName("quick_run_meta_label")
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        value.setObjectName("quick_run_secondary_value")
        value.setWordWrap(True)
        layout.addWidget(label, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(value, 0, 1)
        layout.setColumnStretch(1, 1)
        return row, layout

    def _init_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.NoFrame)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)

        self.primary_card = QFrame(self)
        self.primary_card.setObjectName("quick_run_primary_card")
        primary_layout = QVBoxLayout(self.primary_card)
        primary_layout.setContentsMargins(18, 16, 18, 16)
        primary_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        self.title_label = QLabel(self)
        self.title_label.setObjectName("quick_run_title")
        title_layout.addWidget(self.title_label)

        self.hint_label = QLabel(self)
        self.hint_label.setObjectName("quick_run_hint")
        self.hint_label.setWordWrap(True)
        title_layout.addWidget(self.hint_label)

        header_layout.addLayout(title_layout, stretch=1)

        self.state_container = QWidget(self)
        state_layout = QVBoxLayout(self.state_container)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(4)
        self.state_label = QLabel(self)
        self.state_label.setObjectName("quick_run_state_label")
        self.state_value_label = QLabel(self)
        self.state_value_label.setObjectName("quick_run_state_value")
        state_layout.addWidget(self.state_label, alignment=Qt.AlignmentFlag.AlignRight)
        state_layout.addWidget(self.state_value_label, alignment=Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self.state_container, alignment=Qt.AlignmentFlag.AlignTop)

        primary_layout.addLayout(header_layout)

        self.source_label = QLabel(self)
        self.source_value_label = QLabel(self)
        self.source_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        primary_layout.addWidget(self._build_value_row(self.source_label, self.source_value_label))

        self.input_label = QLabel(self)
        self.input_value_label = QLabel(self)
        self.input_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        primary_layout.addWidget(self._build_value_row(self.input_label, self.input_value_label))

        self.data_label = QLabel(self)
        self.data_value_label = QLabel(self)
        primary_layout.addWidget(self._build_value_row(self.data_label, self.data_value_label))

        self.primary_actions = QWidget(self)
        action_layout = QHBoxLayout(self.primary_actions)
        action_layout.setContentsMargins(0, 4, 0, 0)
        action_layout.setSpacing(10)

        self.load_button = QPushButton(self)
        self.load_button.setMinimumWidth(140)
        action_layout.addWidget(self.load_button)

        self.browse_button = QPushButton(self)
        self.browse_button.setMinimumWidth(150)
        action_layout.addWidget(self.browse_button)

        self.run_button = QPushButton(self)
        self.run_button.setObjectName("quick_run_primary_button")
        self.run_button.setMinimumWidth(180)
        self.run_button.setDefault(True)
        action_layout.addWidget(self.run_button)
        action_layout.addStretch()

        primary_layout.addWidget(self.primary_actions)
        root_layout.addWidget(self.primary_card)

        self.secondary_card = QFrame(self)
        self.secondary_card.setObjectName("quick_run_secondary_card")
        secondary_layout = QVBoxLayout(self.secondary_card)
        secondary_layout.setContentsMargins(18, 14, 18, 14)
        secondary_layout.setSpacing(12)

        self.result_label = QLabel(self)
        self.result_value_label = QLabel(self)
        self.result_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.result_row, result_layout = self._build_detail_row(self.result_label, self.result_value_label)
        self.open_output_button = QPushButton(self)
        self.open_output_button.setObjectName("quick_run_secondary_button")
        self.open_output_button.setMinimumWidth(220)
        result_layout.addWidget(
            self.open_output_button,
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        secondary_layout.addWidget(self.result_row)

        self.summary_label = QLabel(self)
        self.summary_value_label = QLabel(self)
        self.summary_row, _summary_layout = self._build_detail_row(
            self.summary_label,
            self.summary_value_label,
        )
        secondary_layout.addWidget(self.summary_row)

        self.ignored_label = QLabel(self)
        self.ignored_value_label = QLabel(self)
        self.ignored_value_label.setObjectName("quick_run_warning_value")
        self.ignored_row, _ignored_layout = self._build_detail_row(
            self.ignored_label,
            self.ignored_value_label,
        )
        secondary_layout.addWidget(self.ignored_row)

        self.utility_row = QWidget(self)
        utility_layout = QHBoxLayout(self.utility_row)
        utility_layout.setContentsMargins(0, 2, 0, 0)
        utility_layout.setSpacing(10)

        self.inspect_button = QPushButton(self)
        self.inspect_button.setObjectName("quick_run_secondary_button")
        utility_layout.addWidget(self.inspect_button)

        utility_layout.addStretch()

        self.advanced_button = QPushButton(self)
        self.advanced_button.setObjectName("quick_run_subtle_button")
        self.advanced_button.setCheckable(True)
        utility_layout.addWidget(self.advanced_button)

        self.more_button = QPushButton(self)
        self.more_button.setObjectName("quick_run_subtle_button")
        utility_layout.addWidget(self.more_button)

        secondary_layout.addWidget(self.utility_row)
        root_layout.addWidget(self.secondary_card)

        self.retranslateUi()

    def retranslateUi(self) -> None:
        self.title_label.setText(self.tr("Quick Run"))
        self.hint_label.setText(
            self.tr("Load a preset, choose an input file, then run the full pipeline.")
        )
        self.source_label.setText(self.tr("Preset"))
        self.state_label.setText(self.tr("State"))
        self.input_label.setText(self.tr("Input"))
        self.data_label.setText(self.tr("Data"))
        self.load_button.setText(self.tr("Load Preset"))
        self.browse_button.setText(self.tr("Select Input"))
        self.run_button.setText(self.tr("Run Analysis"))
        self.result_label.setText(self.tr("Latest Output"))
        self.open_output_button.setText(self.tr("Open Output Folder"))
        self.summary_label.setText(self.tr("Applied"))
        self.ignored_label.setText(self.tr("Needs Attention"))
        self.inspect_button.setText(self.tr("Inspect Data"))
        self.advanced_button.setText(self.tr("Show Advanced"))
        self.more_button.setText(self.tr("More"))
