"""Widgets composing the silence trimming tab."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .convert_tab import DropArea
from ..resources import resource_path


class TrimTab(QWidget):
    """Widget bundling the silence trimming controls."""

    selectFilesRequested = Signal()
    clearSelectionRequested = Signal()
    destinationRequested = Signal()
    trimmingRequested = Signal()
    filesDropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_cache: dict[tuple[str, int, int, int], tuple[QIcon, QSize]] = {}
        self._build_ui()
        self.set_status("Ready")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def silence_threshold(self) -> float:
        return self.threshold_spin.value()

    @property
    def minimum_silence_ms(self) -> int:
        return self.minimum_silence_spin.value()

    @property
    def padding_ms(self) -> int:
        return self.padding_spin.value()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show_selected_files(self, files: Sequence[Path]) -> None:
        if not files:
            self.show_no_files()
            return

        if len(files) == 1:
            selected = files[0]
            self.input_label.setText(str(selected))
            self.drop_area.set_description("File selected", selected.name)
        else:
            summary_lines = [path.name for path in files[:3]]
            remaining = len(files) - len(summary_lines)
            if remaining > 0:
                summary_lines.append(f"…and {remaining} more")
            self.input_label.setText("\n".join(summary_lines))
            self.drop_area.set_description(
                f"{len(files)} files selected",
                "Drop more files to replace the selection",
            )
        self.clear_button.setEnabled(True)

    def show_no_files(self) -> None:
        self.input_label.setText("No files selected")
        self.drop_area.set_description("Drop audio files", "…or click to browse")
        self.clear_button.setEnabled(False)

    def set_output_directory(self, directory: Path | None) -> None:
        if directory is None:
            self.output_edit.clear()
            self.output_edit.setToolTip("")
            return
        directory_text = str(directory)
        self.output_edit.setText(directory_text)
        self.output_edit.setToolTip(directory_text)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_trim_enabled(self, enabled: bool) -> None:
        self.trim_button.setEnabled(enabled)

    def set_browse_enabled(self, enabled: bool) -> None:
        self.browse_button.setEnabled(enabled)

    def set_clear_enabled(self, enabled: bool) -> None:
        self.clear_button.setEnabled(enabled)

    def set_destination_enabled(self, enabled: bool) -> None:
        self.destination_button.setEnabled(enabled)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.threshold_spin.setEnabled(enabled)
        self.minimum_silence_spin.setEnabled(enabled)
        self.padding_spin.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(20)

        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self.filesDropped.emit)
        self.drop_area.clicked.connect(self.selectFilesRequested.emit)
        layout.addWidget(self.drop_area)

        self.input_label = QLabel("No files selected")
        self.input_label.setObjectName("pathLabel")
        self.input_label.setWordWrap(True)
        layout.addWidget(self.input_label)

        file_actions = QHBoxLayout()
        file_actions.setSpacing(12)

        self.browse_button = QPushButton("Select audio files")
        self.browse_button.setObjectName("browseButton")
        self._apply_button_icon(self.browse_button, "folder.svg", QSize(22, 22), padding=8)
        self.browse_button.clicked.connect(self.selectFilesRequested.emit)
        file_actions.addWidget(self.browse_button)

        self.clear_button = QPushButton("Clear selection")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clearSelectionRequested.emit)
        self.clear_button.setEnabled(False)
        file_actions.addWidget(self.clear_button)

        file_actions.addStretch()
        layout.addLayout(file_actions)

        options_layout = QFormLayout()
        options_layout.setSpacing(12)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(-80.0, 0.0)
        self.threshold_spin.setSingleStep(1.0)
        self.threshold_spin.setSuffix(" dBFS")
        self.threshold_spin.setObjectName("thresholdSpin")
        self.threshold_spin.setValue(-50.0)
        options_layout.addRow("Silence threshold", self.threshold_spin)

        self.minimum_silence_spin = QSpinBox()
        self.minimum_silence_spin.setRange(0, 10000)
        self.minimum_silence_spin.setSingleStep(50)
        self.minimum_silence_spin.setSuffix(" ms")
        self.minimum_silence_spin.setObjectName("minimumSilenceSpin")
        self.minimum_silence_spin.setValue(500)
        options_layout.addRow("Minimum silence", self.minimum_silence_spin)

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 5000)
        self.padding_spin.setSingleStep(10)
        self.padding_spin.setSuffix(" ms")
        self.padding_spin.setObjectName("paddingSpin")
        self.padding_spin.setValue(50)
        options_layout.addRow("Padding", self.padding_spin)

        layout.addLayout(options_layout)

        destination_layout = QVBoxLayout()
        destination_layout.setSpacing(8)

        destination_header = QLabel("Destination folder")
        destination_header.setObjectName("sectionLabel")
        destination_layout.addWidget(destination_header)

        destination_controls = QHBoxLayout()
        destination_controls.setSpacing(12)

        self.output_edit = QLineEdit()
        self.output_edit.setObjectName("outputEdit")
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Trimmed files will be saved here")
        destination_controls.addWidget(self.output_edit)

        self.destination_button = QPushButton("Choose folder")
        self.destination_button.setObjectName("destinationButton")
        self._apply_button_icon(self.destination_button, "folder.svg", QSize(20, 20), padding=8)
        self.destination_button.clicked.connect(self.destinationRequested.emit)
        destination_controls.addWidget(self.destination_button)

        destination_layout.addLayout(destination_controls)
        layout.addLayout(destination_layout)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        footer_layout.addWidget(self.status_label)

        footer_layout.addStretch()

        self.trim_button = QPushButton("Trim silence")
        self.trim_button.setObjectName("trimButton")
        self._apply_button_icon(self.trim_button, "export.svg", QSize(22, 22), padding=10)
        self.trim_button.clicked.connect(self.trimmingRequested.emit)
        footer_layout.addWidget(self.trim_button)

        layout.addLayout(footer_layout)

    def _apply_button_icon(
        self, button: QPushButton, icon_name: str, base_size: QSize, padding: int
    ) -> None:
        icon, icon_size = self._load_padded_icon(icon_name, base_size, padding)
        button.setIcon(icon)
        button.setIconSize(icon_size)

    def _load_padded_icon(
        self, icon_name: str, base_size: QSize, padding: int
    ) -> tuple[QIcon, QSize]:
        key = (icon_name, base_size.width(), base_size.height(), padding)
        cached = self._icon_cache.get(key)
        if cached is not None:
            return cached

        base_icon = QIcon(str(resource_path("icons", icon_name)))
        if base_icon.isNull():
            base_icon = QIcon(str(resource_path("icons", "export.svg")))
        icon = QIcon()
        target_width = base_size.width() + padding

        modes = (
            QIcon.Mode.Normal,
            QIcon.Mode.Disabled,
            QIcon.Mode.Active,
            QIcon.Mode.Selected,
        )
        states = (QIcon.State.Off, QIcon.State.On)

        for mode in modes:
            for state in states:
                base_pixmap = base_icon.pixmap(base_size, mode, state)
                if base_pixmap.isNull():
                    base_pixmap = base_icon.pixmap(base_size, QIcon.Mode.Normal, state)
                if base_pixmap.isNull():
                    continue

                device_ratio = base_pixmap.devicePixelRatio()
                padded_width = int(round((base_size.width() + padding) * device_ratio))
                padded_height = int(round(base_size.height() * device_ratio))
                padded_pixmap = QPixmap(padded_width, padded_height)
                padded_pixmap.fill(Qt.GlobalColor.transparent)
                padded_pixmap.setDevicePixelRatio(device_ratio)

                painter = QPainter(padded_pixmap)
                painter.drawPixmap(0, 0, base_pixmap)
                painter.end()

                icon.addPixmap(padded_pixmap, mode, state)

        icon_size = QSize(target_width, base_size.height())
        self._icon_cache[key] = (icon, icon_size)
        return icon, icon_size


__all__ = ["TrimTab"]

