"""Widgets composing the audio conversion tab."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..resources import resource_path


AUDIO_SUFFIXES: set[str] = {
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".aac",
    ".wma",
    ".m4a",
    ".aiff",
    ".aif",
    ".opus",
}


class DropArea(QFrame):
    """Visual area that accepts drag-and-drop of multiple audio files."""

    filesDropped = Signal(list)
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("Drop audio files")
        self._title.setObjectName("dropTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        self._subtitle = QLabel("…or click to browse")
        self._subtitle.setObjectName("dropSubtitle")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._subtitle)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasUrls() and any(
            Path(url.toLocalFile()).suffix.lower() in AUDIO_SUFFIXES
            for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
            self.setProperty("dropActive", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # type: ignore[override]
        event.accept()
        self.setProperty("dropActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):  # type: ignore[override]
        event.acceptProposedAction()
        self.setProperty("dropActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

        files = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if Path(url.toLocalFile()).suffix.lower() in AUDIO_SUFFIXES
        ]
        if files:
            self.filesDropped.emit(files)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def set_description(self, title: str, subtitle: str) -> None:
        self._title.setText(title)
        self._subtitle.setText(subtitle)


class ConvertTab(QWidget):
    """Widget bundling the conversion controls and status display."""

    selectFilesRequested = Signal()
    clearSelectionRequested = Signal()
    destinationRequested = Signal()
    conversionRequested = Signal()
    filesDropped = Signal(list)
    formatChanged = Signal(str)

    def __init__(self, available_formats: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._available_formats = list(available_formats)
        self._icon_cache: dict[Tuple[str, int, int, int], Tuple[QIcon, QSize]] = {}

        self._build_ui()
        self.set_available_formats(self._available_formats)
        self.set_status("Ready")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_available_formats(self, formats: Sequence[str]) -> None:
        self._available_formats = list(formats)
        current = self.current_format
        block = self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(self._available_formats)
        self.format_combo.blockSignals(block)
        if current:
            self.set_current_format(current)

    def set_current_format(self, value: str) -> None:
        if not self._available_formats:
            return
        index = self.format_combo.findText(value)
        block = self.format_combo.blockSignals(True)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        else:
            self.format_combo.setCurrentIndex(0)
        self.format_combo.blockSignals(block)

    @property
    def current_format(self) -> str:
        return self.format_combo.currentText()

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

    def set_export_enabled(self, enabled: bool) -> None:
        self.export_button.setEnabled(enabled)

    def set_browse_enabled(self, enabled: bool) -> None:
        self.browse_button.setEnabled(enabled)

    def set_clear_enabled(self, enabled: bool) -> None:
        self.clear_button.setEnabled(enabled)

    def set_destination_enabled(self, enabled: bool) -> None:
        self.destination_button.setEnabled(enabled)

    def set_format_enabled(self, enabled: bool) -> None:
        self.format_combo.setEnabled(enabled)

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

        format_layout = QHBoxLayout()
        format_layout.setSpacing(12)

        format_label = QLabel("Output format")
        format_label.setObjectName("sectionLabel")
        format_layout.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("formatCombo")
        self.format_combo.currentTextChanged.connect(self.formatChanged.emit)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

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
        self.output_edit.setPlaceholderText("Converted files will be saved here")
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

        self.export_button = QPushButton("Start conversion")
        self.export_button.setObjectName("exportButton")
        self._apply_button_icon(self.export_button, "export.svg", QSize(22, 22), padding=10)
        self.export_button.clicked.connect(self.conversionRequested.emit)
        footer_layout.addWidget(self.export_button)

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
