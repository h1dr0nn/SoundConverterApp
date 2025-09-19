"""PySide6 user interface for the Sound Converter application."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Set

from PySide6.QtCore import QByteArray, QSettings, QThread, QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .converter import ConversionRequest, SoundConverter
from .resources import load_stylesheet, resource_path
from .ui import AUDIO_SUFFIXES, ConvertTab, SettingsTab
from .workers import ConversionWorker


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

        self._settings = QSettings("SoundConverterApp", "SOUND_CONVERTER")
        self._load_preferences()

        self._setup_ui()
        self._apply_styles()
        self._update_preferences_from_settings_tab()
        self._apply_default_format()
        self._restore_initial_state()
        self._restore_geometry()

    # ------------------------------------------------------------------
    # Preferences helpers
    # ------------------------------------------------------------------
    def _load_preferences(self) -> None:
        self._pref_default_format = "ogg"
        self._pref_overwrite_existing = True
        self._pref_open_destination = False
        self._pref_remember_destination = True
        self._pref_auto_clear_selection = False
        self._pref_remember_geometry = True
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
        self._available_formats = list(self.converter.available_formats())

        self.convert_tab = ConvertTab(self._available_formats)
        self.convert_tab.selectFilesRequested.connect(self._open_file_dialog)
        self.convert_tab.filesDropped.connect(self._handle_input_files)
        self.convert_tab.clearSelectionRequested.connect(self._clear_selection)
        self.convert_tab.destinationRequested.connect(self._choose_output_directory)
        self.convert_tab.conversionRequested.connect(self._export_audio)
        self.convert_tab.formatChanged.connect(self._on_format_changed)
        self.tabs.addTab(self.convert_tab, "Convert")

        self.settings_tab = SettingsTab(self._settings, self._available_formats)
        self.settings_tab.defaultFormatChanged.connect(self._on_default_format_changed)
        self.settings_tab.overwriteExistingChanged.connect(self._on_overwrite_toggled)
        self.settings_tab.openDestinationChanged.connect(
            self._on_open_destination_toggled
        )
        self.settings_tab.rememberDestinationChanged.connect(
            self._on_remember_destination_toggled
        )
        self.settings_tab.rememberGeometryChanged.connect(
            self._on_remember_geometry_toggled
        )
        self.settings_tab.autoClearSelectionChanged.connect(
            self._on_auto_clear_toggled
        )
        self.tabs.addTab(self.settings_tab, "Settings")

        main_layout.addWidget(self.tabs)

    def _update_preferences_from_settings_tab(self) -> None:
        self._pref_default_format = self.settings_tab.default_format
        self._pref_overwrite_existing = self.settings_tab.overwrite_existing
        self._pref_open_destination = self.settings_tab.open_destination
        self._pref_remember_destination = self.settings_tab.remember_destination
        self._pref_remember_geometry = self.settings_tab.remember_geometry
        self._pref_auto_clear_selection = self.settings_tab.auto_clear_selection
        if not self._pref_remember_destination:
            self._pref_last_output_directory = None

    def _apply_default_format(self) -> None:
        if not self._available_formats:
            return
        target = (
            self._pref_default_format
            if self._pref_default_format in self._available_formats
            else self._available_formats[0]
        )
        self._pref_default_format = target
        self.convert_tab.set_current_format(target)
        self.settings_tab.set_default_format(target)

    def _restore_initial_state(self) -> None:
        self.input_files = []
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.output_directory = self._pref_last_output_directory
        else:
            self.output_directory = None
        self.convert_tab.show_no_files()
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
        self.convert_tab.show_selected_files(self.input_files)
        self._update_output_preview()

    def _clear_selection(self) -> None:
        self.input_files = []
        self.convert_tab.show_no_files()
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.output_directory = self._pref_last_output_directory
        else:
            self.output_directory = None
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

        self.convert_tab.set_output_directory(self.output_directory)

        if not self.input_files:
            self.convert_tab.set_status("Ready")
            return

        format_name = self.convert_tab.current_format
        if len(self.input_files) == 1:
            self.convert_tab.set_status(
                f"Ready to convert '{self.input_files[0].name}' to .{format_name}"
            )
        else:
            self.convert_tab.set_status(
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
            output_format=self.convert_tab.current_format,
            overwrite_existing=self._pref_overwrite_existing,
        )

        self._lock_ui()
        self.convert_tab.set_status("Converting…")

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
        self.convert_tab.set_status("Completed")
        if self._progress_dialog:
            self._progress_dialog.show_finished("Conversion completed", message)
        if self._pref_open_destination and self.output_directory:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_directory)))
        if self._pref_auto_clear_selection:
            self._clear_selection()
            self.convert_tab.set_status("Completed")

    @Slot(str)
    def _on_conversion_error(self, message: str) -> None:
        self.convert_tab.set_status("Conversion failed")
        if self._progress_dialog:
            self._progress_dialog.show_finished("Conversion failed", message)

    def _on_progress_dialog_closed(self, _: int) -> None:
        self._progress_dialog = None

    def _on_format_changed(self, _: str) -> None:
        self._update_output_preview()

    def _on_default_format_changed(self, value: str) -> None:
        self._pref_default_format = value
        self.convert_tab.set_current_format(value)
        self._update_output_preview()

    def _on_overwrite_toggled(self, checked: bool) -> None:
        self._pref_overwrite_existing = checked

    def _on_open_destination_toggled(self, checked: bool) -> None:
        self._pref_open_destination = checked

    def _on_remember_destination_toggled(self, checked: bool) -> None:
        self._pref_remember_destination = checked
        if not checked:
            self._pref_last_output_directory = None
        elif self.output_directory:
            self._save_last_output_directory(self.output_directory)

    def _on_remember_geometry_toggled(self, checked: bool) -> None:
        self._pref_remember_geometry = checked
        if not checked:
            self._saved_geometry = None
        else:
            geometry = self.saveGeometry()
            self._saved_geometry = geometry

    def _on_auto_clear_toggled(self, checked: bool) -> None:
        self._pref_auto_clear_selection = checked

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _lock_ui(self) -> None:
        self.convert_tab.set_export_enabled(False)
        self.convert_tab.set_browse_enabled(False)
        self.convert_tab.set_clear_enabled(False)
        self.convert_tab.set_destination_enabled(False)
        self.convert_tab.set_format_enabled(False)

    def _unlock_ui(self) -> None:
        self.convert_tab.set_export_enabled(True)
        self.convert_tab.set_browse_enabled(True)
        self.convert_tab.set_destination_enabled(True)
        self.convert_tab.set_format_enabled(True)
        self.convert_tab.set_clear_enabled(bool(self.input_files))

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        if self._pref_remember_geometry:
            geometry = self.saveGeometry()
            self._settings.setValue("window_geometry", geometry)
            self._saved_geometry = geometry
        super().closeEvent(event)
