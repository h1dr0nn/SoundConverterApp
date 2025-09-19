"""PySide6 user interface for the Sound Converter application."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Set, Tuple

from PySide6.QtCore import (
    QByteArray,
    QSettings,
    QSize,
    Qt,
    QThread,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .converter import ConversionRequest, SoundConverter
from .resources import load_stylesheet, resource_path
from .workers import ConversionWorker


AUDIO_SUFFIXES: Set[str] = {
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

    def set_description(self, title: str, subtitle: str) -> None:
        self._title.setText(title)
        self._subtitle.setText(subtitle)


class ConversionDialog(QDialog):
    """Modal dialog that communicates conversion progress and results."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("conversionDialog")
        self.setModal(True)
        self.setWindowTitle("Converting…")
        self.setWindowIcon(QIcon(str(resource_path("icons", "app.svg"))))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        self._headline = QLabel("Converting audio files…")
        self._headline.setObjectName("dialogHeadline")
        layout.addWidget(self._headline)

        self._progress = QProgressBar()
        self._progress.setObjectName("dialogProgress")
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)

        self._message = QLabel("Please wait while the files are processed.")
        self._message.setObjectName("dialogMessage")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._close_button = QPushButton("Close")
        self._close_button.setObjectName("dialogCloseButton")
        self._close_button.setEnabled(False)
        self._close_button.clicked.connect(self.accept)
        button_row.addWidget(self._close_button)

        layout.addLayout(button_row)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def show_running(self) -> None:
        self.setWindowTitle("Converting…")
        self._headline.setText("Converting audio files…")
        self._message.setText("Please wait while the files are processed.")
        self._progress.setRange(0, 0)
        self._close_button.setEnabled(False)

    def show_finished(self, title: str, message: str) -> None:
        self.setWindowTitle(title)
        self._headline.setText(title)
        self._message.setText(message)
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._close_button.setEnabled(True)


class MainWindow(QWidget):
    """The primary window managing user interaction."""

    def __init__(self, converter: SoundConverter) -> None:
        super().__init__()
        self.converter = converter
        self.input_files: List[Path] = []
        self.output_directory: Optional[Path] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConversionWorker] = None
        self._active_request: Optional[ConversionRequest] = None
        self._progress_dialog: Optional[ConversionDialog] = None
        self._icon_cache: dict[Tuple[str, int, int, int], Tuple[QIcon, QSize]] = {}

        self._settings = QSettings("SoundConverterApp", "SOUND_CONVERTER")
        self._load_preferences()

        self._setup_ui()
        self._apply_styles()
        self._restore_initial_state()
        self._restore_geometry()

    # ------------------------------------------------------------------
    # Preferences helpers
    # ------------------------------------------------------------------
    def _load_preferences(self) -> None:
        self._pref_default_format = str(
            self._settings.value("default_format", "ogg")
        )
        self._pref_overwrite_existing = self._get_bool_setting(
            "overwrite_existing", True
        )
        self._pref_open_destination = self._get_bool_setting(
            "open_destination", False
        )
        self._pref_remember_destination = self._get_bool_setting(
            "remember_destination", True
        )
        self._pref_auto_clear_selection = self._get_bool_setting(
            "auto_clear_selection", False
        )
        self._pref_remember_geometry = self._get_bool_setting(
            "remember_window_geometry", True
        )
        last_directory = self._settings.value("last_output_directory", "")
        self._pref_last_output_directory: Optional[Path]
        if last_directory:
            self._pref_last_output_directory = Path(str(last_directory))
        else:
            self._pref_last_output_directory = None
        self._saved_geometry: Optional[QByteArray]
        self._saved_geometry = self._coerce_geometry_value(
            self._settings.value("window_geometry")
        )

    def _get_bool_setting(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).lower() in {"1", "true", "yes", "on"}

    def _coerce_geometry_value(self, value: object) -> Optional[QByteArray]:
        if isinstance(value, QByteArray):
            return value
        if isinstance(value, (bytes, bytearray)):
            return QByteArray(value)
        if isinstance(value, str):
            try:
                raw = QByteArray.fromHex(value.encode())
            except Exception:
                return None
            return raw if len(raw) > 0 else None
        return None

    def _save_last_output_directory(self, directory: Path) -> None:
        self._pref_last_output_directory = directory
        if self._pref_remember_destination:
            self._settings.setValue("last_output_directory", str(directory))

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setWindowTitle("SOUND CONVERTER")
        self.setWindowIcon(QIcon(str(resource_path("icons", "app.svg"))))
        self.resize(720, 520)
        self.setMinimumWidth(560)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(20)

        header = QLabel("SOUND CONVERTER")
        header.setObjectName("titleLabel")
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.addTab(self._build_convert_tab(), "Convert")
        self.tabs.addTab(self._build_settings_tab(), "Settings")
        main_layout.addWidget(self.tabs)

        self._apply_default_format()
        self._sync_settings_controls()

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

    def _build_convert_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(20)

        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self._handle_input_files)
        self.drop_area.clicked.connect(self._open_file_dialog)
        layout.addWidget(self.drop_area)

        self.input_label = QLabel("No files selected")
        self.input_label.setObjectName("pathLabel")
        self.input_label.setWordWrap(True)
        layout.addWidget(self.input_label)

        file_actions = QHBoxLayout()
        file_actions.setSpacing(12)

        self.browse_button = QPushButton("Select audio files")
        self.browse_button.setObjectName("browseButton")
        self._apply_button_icon(
            self.browse_button, "folder.svg", QSize(22, 22), padding=8
        )
        self.browse_button.clicked.connect(self._open_file_dialog)
        file_actions.addWidget(self.browse_button)

        self.clear_button = QPushButton("Clear selection")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self._clear_selection)
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
        self._available_formats = list(self.converter.available_formats())
        self.format_combo.addItems(self._available_formats)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
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
        self._apply_button_icon(
            self.destination_button, "folder.svg", QSize(20, 20), padding=8
        )
        self.destination_button.clicked.connect(self._choose_output_directory)
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
        self._apply_button_icon(
            self.export_button, "export.svg", QSize(22, 22), padding=10
        )
        self.export_button.clicked.connect(self._export_audio)
        footer_layout.addWidget(self.export_button)

        layout.addLayout(footer_layout)

        return tab

    def _build_settings_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(18)

        default_format_label = QLabel("Default output format")
        default_format_label.setObjectName("settingsLabel")
        layout.addWidget(default_format_label)

        self.default_format_combo = QComboBox()
        self.default_format_combo.setObjectName("settingsCombo")
        self.default_format_combo.addItems(self._available_formats)
        self.default_format_combo.currentTextChanged.connect(
            self._on_default_format_changed
        )
        layout.addWidget(self.default_format_combo)

        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        self.overwrite_checkbox.setObjectName("settingsCheckBox")
        self.overwrite_checkbox.toggled.connect(self._on_overwrite_toggled)
        layout.addWidget(self.overwrite_checkbox)

        self.open_destination_checkbox = QCheckBox(
            "Open the destination folder when conversion completes"
        )
        self.open_destination_checkbox.setObjectName("settingsCheckBox")
        self.open_destination_checkbox.toggled.connect(
            self._on_open_destination_toggled
        )
        layout.addWidget(self.open_destination_checkbox)

        self.remember_destination_checkbox = QCheckBox(
            "Remember the last destination folder"
        )
        self.remember_destination_checkbox.setObjectName("settingsCheckBox")
        self.remember_destination_checkbox.toggled.connect(
            self._on_remember_destination_toggled
        )
        layout.addWidget(self.remember_destination_checkbox)

        self.remember_geometry_checkbox = QCheckBox(
            "Remember window size and position"
        )
        self.remember_geometry_checkbox.setObjectName("settingsCheckBox")
        self.remember_geometry_checkbox.toggled.connect(
            self._on_remember_geometry_toggled
        )
        layout.addWidget(self.remember_geometry_checkbox)

        self.auto_clear_checkbox = QCheckBox(
            "Clear file selection after a successful conversion"
        )
        self.auto_clear_checkbox.setObjectName("settingsCheckBox")
        self.auto_clear_checkbox.toggled.connect(self._on_auto_clear_toggled)
        layout.addWidget(self.auto_clear_checkbox)

        layout.addStretch()

        return tab

    def _apply_default_format(self) -> None:
        target = (
            self._pref_default_format
            if self._pref_default_format in self._available_formats
            else self._available_formats[0]
        )
        self._set_combo_value(self.format_combo, target)
        self._set_combo_value(self.default_format_combo, target)

    def _sync_settings_controls(self) -> None:
        self.overwrite_checkbox.setChecked(self._pref_overwrite_existing)
        self.open_destination_checkbox.setChecked(self._pref_open_destination)
        self.remember_destination_checkbox.setChecked(
            self._pref_remember_destination
        )
        if hasattr(self, "remember_geometry_checkbox"):
            self.remember_geometry_checkbox.setChecked(self._pref_remember_geometry)
        if hasattr(self, "auto_clear_checkbox"):
            self.auto_clear_checkbox.setChecked(self._pref_auto_clear_selection)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            block = combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(block)

    def _restore_initial_state(self) -> None:
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.output_directory = self._pref_last_output_directory
        else:
            self.output_directory = None
        self.clear_button.setEnabled(False)
        self._update_output_preview()

    def _restore_geometry(self) -> None:
        if not self._pref_remember_geometry or not self._saved_geometry:
            return
        try:
            self.restoreGeometry(self._saved_geometry)
        except Exception:
            pass

    def _apply_styles(self) -> None:
        try:
            self.setStyleSheet(load_stylesheet())
        except Exception as exc:  # pragma: no cover - style fallback
            print("Could not load styles:", exc)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _open_file_dialog(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select audio files",
            "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.aac *.wma *.m4a *.aiff *.aif *.opus)",
        )
        if file_paths:
            self._handle_input_files([Path(path) for path in file_paths])

    def _handle_input_files(self, file_paths: Sequence[Path]) -> None:
        valid_files: List[Path] = []
        unsupported: List[Path] = []
        missing: List[Path] = []
        seen: Set[Path] = set()

        for file_path in file_paths:
            resolved = file_path.resolve(strict=False)
            if not file_path.exists():
                missing.append(file_path)
                continue
            if file_path.suffix.lower() not in AUDIO_SUFFIXES:
                unsupported.append(file_path)
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            valid_files.append(file_path)

        skipped_messages = []
        if missing:
            skipped_messages.append(
                "Missing files: " + ", ".join(path.name for path in missing)
            )

        if unsupported:
            skipped_messages.append(
                "Unsupported formats: " + ", ".join(path.name for path in unsupported)
            )

        message_lines = list(skipped_messages)

        if not valid_files:
            if message_lines:
                message_lines.append("")
            message_lines.append("Please select at least one supported audio file.")

        if message_lines:
            title = "Some files were skipped"
            if not valid_files:
                title = "No valid files"
            QMessageBox.warning(
                self,
                title,
                "\n".join(message_lines),
            )
            if not valid_files:
                return

        self.input_files = valid_files
        if self.output_directory is None:
            if (
                self._pref_remember_destination
                and self._pref_last_output_directory
                and self._pref_last_output_directory.exists()
            ):
                self.output_directory = self._pref_last_output_directory
            else:
                self.output_directory = self.input_files[0].parent

        if len(self.input_files) == 1:
            selected = self.input_files[0]
            self.input_label.setText(str(selected))
            self.drop_area.set_description("File selected", selected.name)
        else:
            summary_lines = [path.name for path in self.input_files[:3]]
            remaining = len(self.input_files) - len(summary_lines)
            if remaining > 0:
                summary_lines.append(f"…and {remaining} more")
            self.input_label.setText("\n".join(summary_lines))
            self.drop_area.set_description(
                f"{len(self.input_files)} files selected",
                "Drop more files to replace the selection",
            )

        self.clear_button.setEnabled(True)
        self._update_output_preview()

    def _clear_selection(self) -> None:
        self.input_files = []
        self.drop_area.set_description("Drop audio files", "…or click to browse")
        self.input_label.setText("No files selected")
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.output_directory = self._pref_last_output_directory
        else:
            self.output_directory = None
        self.clear_button.setEnabled(False)
        self._update_output_preview()

    def _choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select destination folder"
        )
        if directory:
            self.output_directory = Path(directory)
            self._save_last_output_directory(self.output_directory)
            self._update_output_preview()

    def _update_output_preview(self) -> None:
        if not self.output_directory and self.input_files:
            self.output_directory = self.input_files[0].parent

        if self.output_directory and (
            self.output_directory.is_file()
            or (
                self.output_directory.suffix
                and not self.output_directory.is_dir()
            )
        ):
            self.output_directory = self.output_directory.parent

        if not self.output_directory:
            self.output_edit.clear()
            self.output_edit.setToolTip("")
        else:
            directory_text = str(self.output_directory)
            self.output_edit.setText(directory_text)
            self.output_edit.setToolTip(directory_text)

        if not self.input_files:
            self.status_label.setText("Ready")
            return

        format_name = self.format_combo.currentText()
        if len(self.input_files) == 1:
            self.status_label.setText(
                f"Ready to convert '{self.input_files[0].name}' to .{format_name}"
            )
        else:
            self.status_label.setText(
                f"{len(self.input_files)} files will be converted to .{format_name}"
            )

    def _export_audio(self) -> None:
        if not self.input_files:
            QMessageBox.warning(
                self,
                "No files",
                "Please choose audio files before starting the conversion.",
            )
            return

        destination = self.output_directory or self.input_files[0].parent
        if destination is None:
            QMessageBox.warning(
                self,
                "No destination",
                "Please choose a folder to store the converted files.",
            )
            return

        self._save_last_output_directory(destination)

        request = ConversionRequest(
            input_paths=tuple(self.input_files),
            output_directory=destination,
            output_format=self.format_combo.currentText(),
            overwrite_existing=self.overwrite_checkbox.isChecked(),
        )

        self._lock_ui()
        self.status_label.setText("Converting…")

        self._active_request = request
        self._progress_dialog = ConversionDialog(self)
        self._progress_dialog.show_running()
        self._progress_dialog.finished.connect(self._on_progress_dialog_closed)
        self._progress_dialog.show()

        self._thread = QThread(self)
        self._worker = ConversionWorker(self.converter, request)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._on_conversion_success)
        self._worker.failed.connect(self._on_conversion_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_conversion_finished)
        self._thread.start()

    @Slot()
    def _on_conversion_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._active_request = None
        self._unlock_ui()

    @Slot(str)
    def _on_conversion_success(self, message: str) -> None:
        self.status_label.setText("Completed")
        if self._progress_dialog:
            self._progress_dialog.show_finished("Conversion completed", message)
        if self.open_destination_checkbox.isChecked() and self.output_directory:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_directory)))
        if getattr(self, "auto_clear_checkbox", None) and self.auto_clear_checkbox.isChecked():
            self._clear_selection()
            self.status_label.setText("Completed")

    @Slot(str)
    def _on_conversion_error(self, message: str) -> None:
        self.status_label.setText("Conversion failed")
        if self._progress_dialog:
            self._progress_dialog.show_finished("Conversion failed", message)

    def _on_progress_dialog_closed(self, _: int) -> None:
        self._progress_dialog = None

    def _on_format_changed(self, _: str) -> None:
        self._update_output_preview()

    def _on_default_format_changed(self, value: str) -> None:
        self._pref_default_format = value
        self._settings.setValue("default_format", value)
        self._set_combo_value(self.format_combo, value)
        self._update_output_preview()

    def _on_overwrite_toggled(self, checked: bool) -> None:
        self._pref_overwrite_existing = checked
        self._settings.setValue("overwrite_existing", checked)

    def _on_open_destination_toggled(self, checked: bool) -> None:
        self._pref_open_destination = checked
        self._settings.setValue("open_destination", checked)

    def _on_remember_destination_toggled(self, checked: bool) -> None:
        self._pref_remember_destination = checked
        self._settings.setValue("remember_destination", checked)
        if not checked:
            self._settings.remove("last_output_directory")
            self._pref_last_output_directory = None
        elif self.output_directory:
            self._save_last_output_directory(self.output_directory)

    def _on_remember_geometry_toggled(self, checked: bool) -> None:
        self._pref_remember_geometry = checked
        self._settings.setValue("remember_window_geometry", checked)
        if not checked:
            self._settings.remove("window_geometry")
            self._saved_geometry = None
        else:
            geometry = self.saveGeometry()
            self._saved_geometry = geometry
            self._settings.setValue("window_geometry", geometry)

    def _on_auto_clear_toggled(self, checked: bool) -> None:
        self._pref_auto_clear_selection = checked
        self._settings.setValue("auto_clear_selection", checked)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _lock_ui(self) -> None:
        self.export_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.destination_button.setEnabled(False)
        self.format_combo.setEnabled(False)

    def _unlock_ui(self) -> None:
        self.export_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.destination_button.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.clear_button.setEnabled(bool(self.input_files))

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        if self._pref_remember_geometry:
            geometry = self.saveGeometry()
            self._settings.setValue("window_geometry", geometry)
            self._saved_geometry = geometry
        super().closeEvent(event)
