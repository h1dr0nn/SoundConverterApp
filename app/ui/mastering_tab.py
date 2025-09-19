"""Widgets composing the automatic mastering tab."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Sequence, Tuple

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..mastering import MasteringParameters
from ..resources import resource_path
from .convert_tab import DropArea


class MasteringTab(QWidget):
    """Widget bundling the mastering controls and status display."""

    selectFilesRequested = Signal()
    clearSelectionRequested = Signal()
    destinationRequested = Signal()
    masteringRequested = Signal()
    filesDropped = Signal(list)
    presetChanged = Signal(str)
    parametersChanged = Signal(object)

    def __init__(
        self, presets: Dict[str, MasteringParameters], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._preset_definitions = dict(presets)
        self._icon_cache: dict[Tuple[str, int, int, int], Tuple[QIcon, QSize]] = {}
        self._parameters = MasteringParameters()

        self._build_ui()
        self.set_parameters(self._parameters)
        self.set_available_presets(self._preset_definitions)
        self.show_no_files()
        self.set_status("Ready")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_available_presets(self, presets: Dict[str, MasteringParameters]) -> None:
        self._preset_definitions = dict(presets)
        block = self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(list(self._preset_definitions.keys()))
        self.preset_combo.blockSignals(block)

    def set_current_preset(self, preset: str) -> None:
        if not self._preset_definitions:
            return
        index = self.preset_combo.findText(preset)
        block = self.preset_combo.blockSignals(True)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
            chosen = preset
        else:
            self.preset_combo.setCurrentIndex(0)
            chosen = self.preset_combo.currentText()
        self.preset_combo.blockSignals(block)
        self._apply_preset(chosen, emit=False)

    @property
    def current_preset(self) -> str:
        return self.preset_combo.currentText()

    def set_parameters(
        self, parameters: MasteringParameters, *, emit: bool = False
    ) -> None:
        self._parameters = parameters
        blockers = [
            QSignalBlocker(self.target_lufs_spin),
            QSignalBlocker(self.compression_check),
            QSignalBlocker(self.limiter_check),
            QSignalBlocker(self.output_gain_spin),
        ]
        self.target_lufs_spin.setValue(parameters.target_lufs)
        self.compression_check.setChecked(parameters.apply_compression)
        self.limiter_check.setChecked(parameters.apply_limiter)
        self.output_gain_spin.setValue(parameters.output_gain)
        del blockers
        if emit:
            self.parametersChanged.emit(parameters)

    @property
    def current_parameters(self) -> MasteringParameters:
        return MasteringParameters(
            target_lufs=float(self.target_lufs_spin.value()),
            apply_compression=self.compression_check.isChecked(),
            apply_limiter=self.limiter_check.isChecked(),
            output_gain=float(self.output_gain_spin.value()),
        )

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
        self.drop_area.set_description("Drop audio mixes", "…or click to browse")
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

    def set_export_enabled(self, enabled: bool) -> None:
        self.master_button.setEnabled(enabled)

    def set_browse_enabled(self, enabled: bool) -> None:
        self.browse_button.setEnabled(enabled)

    def set_clear_enabled(self, enabled: bool) -> None:
        self.clear_button.setEnabled(enabled)

    def set_destination_enabled(self, enabled: bool) -> None:
        self.destination_button.setEnabled(enabled)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.preset_combo.setEnabled(enabled)
        self.target_lufs_spin.setEnabled(enabled)
        self.compression_check.setEnabled(enabled)
        self.limiter_check.setEnabled(enabled)
        self.output_gain_spin.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(20)

        self.drop_area = DropArea()
        self.drop_area.set_description("Drop audio mixes", "…or click to browse")
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

        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(12)

        preset_label = QLabel("Mastering preset")
        preset_label.setObjectName("sectionLabel")
        preset_layout.addWidget(preset_label)

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        parameters_frame = QFrame()
        parameters_layout = QVBoxLayout(parameters_frame)
        parameters_layout.setSpacing(12)

        target_layout = QHBoxLayout()
        target_layout.setSpacing(12)
        target_label = QLabel("Target loudness (LUFS)")
        target_label.setObjectName("sectionLabel")
        target_layout.addWidget(target_label)
        target_layout.addStretch()

        self.target_lufs_spin = QDoubleSpinBox()
        self.target_lufs_spin.setRange(-30.0, -6.0)
        self.target_lufs_spin.setDecimals(1)
        self.target_lufs_spin.setSingleStep(0.5)
        self.target_lufs_spin.valueChanged.connect(self._emit_parameters_changed)
        target_layout.addWidget(self.target_lufs_spin)
        parameters_layout.addLayout(target_layout)

        toggles_layout = QHBoxLayout()
        toggles_layout.setSpacing(12)
        self.compression_check = QCheckBox("Apply compression")
        self.compression_check.setChecked(True)
        self.compression_check.toggled.connect(self._emit_parameters_changed)
        toggles_layout.addWidget(self.compression_check)

        self.limiter_check = QCheckBox("Enable limiter")
        self.limiter_check.setChecked(True)
        self.limiter_check.toggled.connect(self._emit_parameters_changed)
        toggles_layout.addWidget(self.limiter_check)
        toggles_layout.addStretch()
        parameters_layout.addLayout(toggles_layout)

        gain_layout = QHBoxLayout()
        gain_layout.setSpacing(12)
        gain_label = QLabel("Output gain (dB)")
        gain_label.setObjectName("sectionLabel")
        gain_layout.addWidget(gain_label)
        gain_layout.addStretch()

        self.output_gain_spin = QDoubleSpinBox()
        self.output_gain_spin.setRange(-12.0, 12.0)
        self.output_gain_spin.setDecimals(1)
        self.output_gain_spin.setSingleStep(0.5)
        self.output_gain_spin.valueChanged.connect(self._emit_parameters_changed)
        gain_layout.addWidget(self.output_gain_spin)
        parameters_layout.addLayout(gain_layout)

        layout.addWidget(parameters_frame)

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
        self.output_edit.setPlaceholderText("Mastered files will be saved here")
        destination_controls.addWidget(self.output_edit)

        self.destination_button = QPushButton("Choose folder")
        self.destination_button.setObjectName("destinationButton")
        self._apply_button_icon(
            self.destination_button, "folder.svg", QSize(20, 20), padding=8
        )
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

        self.master_button = QPushButton("Start mastering")
        self.master_button.setObjectName("exportButton")
        self._apply_button_icon(
            self.master_button, "export.svg", QSize(22, 22), padding=10
        )
        self.master_button.clicked.connect(self.masteringRequested.emit)
        footer_layout.addWidget(self.master_button)

        layout.addLayout(footer_layout)

    def _apply_button_icon(
        self, button: QPushButton, icon_name: str, base_size: QSize, padding: int
    ) -> None:
        icon, icon_size = self._load_padded_icon(icon_name, base_size, padding)
        button.setIcon(icon)
        button.setIconSize(icon_size)

    def _load_padded_icon(
        self, icon_name: str, base_size: QSize, padding: int
    ) -> Tuple[QIcon, QSize]:
        key = (icon_name, base_size.width(), base_size.height(), padding)
        cached = self._icon_cache.get(key)
        if cached is not None:
            return cached

        base_icon = QIcon(str(resource_path("icons", icon_name)))
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

    def _on_preset_changed(self, preset: str) -> None:
        if not preset:
            return
        self._apply_preset(preset, emit=True)

    def _apply_preset(self, preset: str, *, emit: bool) -> None:
        parameters = self._preset_definitions.get(preset)
        if parameters is None:
            return
        self.set_parameters(parameters, emit=emit)
        if emit:
            self.presetChanged.emit(preset)

    def _emit_parameters_changed(self) -> None:
        parameters = self.current_parameters
        if parameters != self._parameters:
            self._parameters = parameters
            self.parametersChanged.emit(parameters)
