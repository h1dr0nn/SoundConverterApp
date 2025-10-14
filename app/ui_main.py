"""PySide6 user interface for the Sound Converter application."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

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
from .mastering import MasteringEngine, MasteringParameters, MasteringRequest
from .resources import load_stylesheet, resource_path
from .trimmer import SilenceTrimmer, TrimRequest
from .ui import AUDIO_SUFFIXES, ConvertTab, MasteringTab, SettingsTab, TrimTab
from .workers import ConversionWorker, MasteringWorker, TrimWorker


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
    def show_running(
        self,
        title: str = "Converting…",
        headline: str = "Converting audio files…",
        message: str = "Please wait while the files are processed.",
    ) -> None:
        self.setWindowTitle(title)
        self._headline.setText(headline)
        self._message.setText(message)
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

    def __init__(
        self,
        converter: SoundConverter,
        mastering_engine: Optional[MasteringEngine] = None,
        trimmer: Optional[SilenceTrimmer] = None,
    ) -> None:
        super().__init__()
        self.converter = converter
        self.mastering_engine = mastering_engine or MasteringEngine()
        self.trimmer = trimmer or SilenceTrimmer()
        self.input_files: List[Path] = []
        self.output_directory: Optional[Path] = None
        self.mastering_files: List[Path] = []
        self.mastering_output_directory: Optional[Path] = None
        self.trim_files: List[Path] = []
        self.trim_output_directory: Optional[Path] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConversionWorker] = None
        self._active_request: Optional[ConversionRequest] = None
        self._progress_dialog: Optional[ConversionDialog] = None
        self._mastering_thread: Optional[QThread] = None
        self._mastering_worker: Optional[MasteringWorker] = None
        self._active_mastering_request: Optional[MasteringRequest] = None
        self._mastering_dialog: Optional[ConversionDialog] = None
        self._trim_thread: Optional[QThread] = None
        self._trim_worker: Optional[TrimWorker] = None
        self._active_trim_request: Optional[TrimRequest] = None
        self._trim_dialog: Optional[ConversionDialog] = None
        self._mastering_parameters: MasteringParameters = (
            self.mastering_engine.parameters_for_preset(
                self.mastering_engine.default_preset()
            )
        )
        self._preset_definitions: Dict[str, MasteringParameters] = (
            self.mastering_engine.presets()
        )

        self._settings = QSettings("SoundConverterApp", "SOUND_CONVERTER")
        self._load_preferences()
        self._mastering_parameters = self.mastering_engine.parameters_for_preset(
            self._pref_mastering_preset
        )

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
        preset_value = self._settings.value("mastering_default_preset", "")
        if isinstance(preset_value, str) and preset_value in self._preset_definitions:
            self._pref_mastering_preset = preset_value
        else:
            self._pref_mastering_preset = self.mastering_engine.default_preset()
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
        suffix_value = self._settings.value("mastering_filename_suffix", "_mastered")
        if isinstance(suffix_value, str):
            self._pref_mastering_suffix = suffix_value.strip()
        else:
            self._pref_mastering_suffix = "_mastered"

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

        self.trim_tab = TrimTab()
        self.trim_tab.selectFilesRequested.connect(self._open_trim_file_dialog)
        self.trim_tab.filesDropped.connect(self._handle_trim_files)
        self.trim_tab.clearSelectionRequested.connect(self._clear_trim_selection)
        self.trim_tab.destinationRequested.connect(
            self._choose_trim_output_directory
        )
        self.trim_tab.trimmingRequested.connect(self._start_trimming)
        self.tabs.addTab(self.trim_tab, "Trim silence")

        self.mastering_tab = MasteringTab(self._preset_definitions)
        self.mastering_tab.set_current_preset(self._pref_mastering_preset)
        self.mastering_tab.set_parameters(self._mastering_parameters)
        self.mastering_tab.set_filename_suffix(self._pref_mastering_suffix)
        self.mastering_tab.selectFilesRequested.connect(
            self._open_mastering_file_dialog
        )
        self.mastering_tab.filesDropped.connect(self._handle_mastering_files)
        self.mastering_tab.clearSelectionRequested.connect(
            self._clear_mastering_selection
        )
        self.mastering_tab.destinationRequested.connect(
            self._choose_mastering_output_directory
        )
        self.mastering_tab.masteringRequested.connect(self._start_mastering)
        self.mastering_tab.presetChanged.connect(self._on_mastering_preset_changed)
        self.mastering_tab.parametersChanged.connect(
            self._on_mastering_parameters_changed
        )
        self.mastering_tab.filenameSuffixChanged.connect(
            self._on_mastering_suffix_changed
        )
        self.tabs.addTab(self.mastering_tab, "Mastering")
        self._mastering_parameters = self.mastering_tab.current_parameters

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
        self._update_conversion_preview()

        self.trim_files = []
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.trim_output_directory = self._pref_last_output_directory
        else:
            self.trim_output_directory = None
        self.trim_tab.show_no_files()
        self._update_trim_preview()

        self.mastering_files = []
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.mastering_output_directory = self._pref_last_output_directory
        else:
            self.mastering_output_directory = None
        self.mastering_tab.show_no_files()
        self._update_mastering_preview()

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

    def _open_mastering_file_dialog(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select audio files to master",
            "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.aac *.wma *.m4a *.aiff *.aif *.opus)",
        )
        if file_paths:
            self._handle_mastering_files([Path(path) for path in file_paths])

    def _open_trim_file_dialog(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select audio files to trim",
            "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.aac *.wma *.m4a *.aiff *.aif *.opus)",
        )
        if file_paths:
            self._handle_trim_files([Path(path) for path in file_paths])

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
        self._update_conversion_preview()

    def _handle_mastering_files(self, file_paths: Sequence[Path]) -> None:
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

        self.mastering_files = valid_files
        if self.mastering_output_directory is None:
            if (
                self._pref_remember_destination
                and self._pref_last_output_directory
                and self._pref_last_output_directory.exists()
            ):
                self.mastering_output_directory = self._pref_last_output_directory
            else:
                self.mastering_output_directory = self.mastering_files[0].parent
        self.mastering_tab.show_selected_files(self.mastering_files)
        self._update_mastering_preview()

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
        self._update_conversion_preview()

    def _clear_mastering_selection(self) -> None:
        self.mastering_files = []
        self.mastering_tab.show_no_files()
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.mastering_output_directory = self._pref_last_output_directory
        else:
            self.mastering_output_directory = None
        self._update_mastering_preview()

    def _clear_trim_selection(self) -> None:
        self.trim_files = []
        self.trim_tab.show_no_files()
        if (
            self._pref_remember_destination
            and self._pref_last_output_directory
            and self._pref_last_output_directory.exists()
        ):
            self.trim_output_directory = self._pref_last_output_directory
        else:
            self.trim_output_directory = None
        self._update_trim_preview()

    def _handle_trim_files(self, file_paths: Sequence[Path]) -> None:
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

        self.trim_files = valid_files
        if self.trim_output_directory is None:
            if (
                self._pref_remember_destination
                and self._pref_last_output_directory
                and self._pref_last_output_directory.exists()
            ):
                self.trim_output_directory = self._pref_last_output_directory
            else:
                self.trim_output_directory = self.trim_files[0].parent
        self.trim_tab.show_selected_files(self.trim_files)
        self._update_trim_preview()

    def _choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select destination folder"
        )
        if directory:
            self.output_directory = Path(directory)
            self._save_last_output_directory(self.output_directory)
            self._update_conversion_preview()

    def _choose_mastering_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select mastering destination"
        )
        if directory:
            self.mastering_output_directory = Path(directory)
            self._save_last_output_directory(self.mastering_output_directory)
            self._update_mastering_preview()

    def _choose_trim_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select trimming destination"
        )
        if directory:
            self.trim_output_directory = Path(directory)
            self._save_last_output_directory(self.trim_output_directory)
            self._update_trim_preview()

    def _update_conversion_preview(self) -> None:
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

    def _update_mastering_preview(self) -> None:
        if not self.mastering_output_directory and self.mastering_files:
            self.mastering_output_directory = self.mastering_files[0].parent

        if self.mastering_output_directory and (
            self.mastering_output_directory.is_file()
            or (
                self.mastering_output_directory.suffix
                and not self.mastering_output_directory.is_dir()
            )
        ):
            self.mastering_output_directory = self.mastering_output_directory.parent

        self.mastering_tab.set_output_directory(self.mastering_output_directory)

        if not self.mastering_files:
            self.mastering_tab.set_status("Ready")
            return

        preset = self.mastering_tab.current_preset
        if len(self.mastering_files) == 1:
            self.mastering_tab.set_status(
                f"Ready to master '{self.mastering_files[0].name}' ({preset})"
            )
        else:
            self.mastering_tab.set_status(
                f"{len(self.mastering_files)} files will be mastered ({preset})"
            )

    def _update_trim_preview(self) -> None:
        if not self.trim_output_directory and self.trim_files:
            self.trim_output_directory = self.trim_files[0].parent

        if self.trim_output_directory and (
            self.trim_output_directory.is_file()
            or (
                self.trim_output_directory.suffix
                and not self.trim_output_directory.is_dir()
            )
        ):
            self.trim_output_directory = self.trim_output_directory.parent

        self.trim_tab.set_output_directory(self.trim_output_directory)

        if not self.trim_files:
            self.trim_tab.set_status("Ready")
            return

        if len(self.trim_files) == 1:
            self.trim_tab.set_status(
                f"Ready to trim silence from '{self.trim_files[0].name}'"
            )
        else:
            self.trim_tab.set_status(
                f"{len(self.trim_files)} files will be trimmed"
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

        self._lock_convert_ui()
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

    def _start_trimming(self) -> None:
        if not self.trim_files:
            QMessageBox.warning(
                self,
                "No files",
                "Please choose audio files before trimming silence.",
            )
            return

        destination = self.trim_output_directory or self.trim_files[0].parent
        if destination is None:
            QMessageBox.warning(
                self,
                "No destination",
                "Please choose a folder to store the trimmed files.",
            )
            return

        self._save_last_output_directory(destination)

        request = TrimRequest(
            input_paths=tuple(self.trim_files),
            output_directory=destination,
            silence_threshold=self.trim_tab.silence_threshold,
            minimum_silence_ms=self.trim_tab.minimum_silence_ms,
            padding_ms=self.trim_tab.padding_ms,
            overwrite_existing=self._pref_overwrite_existing,
        )

        self._lock_trim_ui()
        self.trim_tab.set_status("Trimming…")

        self._active_trim_request = request
        self._trim_dialog = ConversionDialog(self)
        self._trim_dialog.show_running(
            title="Trimming…",
            headline="Trimming silence from audio files…",
            message="Please wait while the files are trimmed.",
        )
        self._trim_dialog.finished.connect(self._on_trim_dialog_closed)
        self._trim_dialog.show()

        self._trim_thread = QThread(self)
        self._trim_worker = TrimWorker(self.trimmer, request)
        self._trim_worker.moveToThread(self._trim_thread)
        self._trim_thread.started.connect(self._trim_worker.run)
        self._trim_worker.succeeded.connect(self._on_trimming_success)
        self._trim_worker.failed.connect(self._on_trimming_error)
        self._trim_worker.finished.connect(self._trim_thread.quit)
        self._trim_worker.finished.connect(self._trim_worker.deleteLater)
        self._trim_thread.finished.connect(self._trim_thread.deleteLater)
        self._trim_thread.finished.connect(self._on_trimming_finished)
        self._trim_thread.start()

    def _start_mastering(self) -> None:
        if not self.mastering_files:
            QMessageBox.warning(
                self,
                "No files",
                "Please choose audio files before starting the mastering process.",
            )
            return

        destination = (
            self.mastering_output_directory
            or self.mastering_files[0].parent
        )
        if destination is None:
            QMessageBox.warning(
                self,
                "No destination",
                "Please choose a folder to store the mastered files.",
            )
            return

        self._save_last_output_directory(destination)

        request = MasteringRequest(
            input_paths=tuple(self.mastering_files),
            output_directory=destination,
            preset=self.mastering_tab.current_preset,
            parameters=self._mastering_parameters,
            filename_suffix=self.mastering_tab.filename_suffix,
            overwrite_existing=self._pref_overwrite_existing,
        )

        self._lock_mastering_ui()
        self.mastering_tab.set_status("Mastering…")

        self._active_mastering_request = request
        self._mastering_dialog = ConversionDialog(self)
        self._mastering_dialog.show_running(
            title="Mastering…",
            headline="Mastering audio files…",
            message="Please wait while the files are mastered.",
        )
        self._mastering_dialog.finished.connect(self._on_mastering_dialog_closed)
        self._mastering_dialog.show()

        self._mastering_thread = QThread(self)
        self._mastering_worker = MasteringWorker(self.mastering_engine, request)
        self._mastering_worker.moveToThread(self._mastering_thread)
        self._mastering_thread.started.connect(self._mastering_worker.run)
        self._mastering_worker.succeeded.connect(self._on_mastering_success)
        self._mastering_worker.failed.connect(self._on_mastering_error)
        self._mastering_worker.finished.connect(self._mastering_thread.quit)
        self._mastering_worker.finished.connect(self._mastering_worker.deleteLater)
        self._mastering_thread.finished.connect(self._mastering_thread.deleteLater)
        self._mastering_thread.finished.connect(self._on_mastering_finished)
        self._mastering_thread.start()

    @Slot()
    def _on_conversion_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._active_request = None
        self._unlock_convert_ui()

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

    @Slot()
    def _on_trimming_finished(self) -> None:
        self._trim_thread = None
        self._trim_worker = None
        self._active_trim_request = None
        self._unlock_trim_ui()

    @Slot(str)
    def _on_trimming_success(self, message: str) -> None:
        self.trim_tab.set_status("Completed")
        if self._trim_dialog:
            self._trim_dialog.show_finished("Trimming completed", message)
        if self._pref_open_destination and self.trim_output_directory:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.trim_output_directory))
            )
        if self._pref_auto_clear_selection:
            self._clear_trim_selection()
            self.trim_tab.set_status("Completed")

    @Slot(str)
    def _on_trimming_error(self, message: str) -> None:
        self.trim_tab.set_status("Trimming failed")
        if self._trim_dialog:
            self._trim_dialog.show_finished("Trimming failed", message)

    def _on_trim_dialog_closed(self, _: int) -> None:
        self._trim_dialog = None

    def _on_progress_dialog_closed(self, _: int) -> None:
        self._progress_dialog = None

    def _on_format_changed(self, _: str) -> None:
        self._update_conversion_preview()

    def _on_default_format_changed(self, value: str) -> None:
        self._pref_default_format = value
        self.convert_tab.set_current_format(value)
        self._update_conversion_preview()

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

    @Slot()
    def _on_mastering_finished(self) -> None:
        self._mastering_thread = None
        self._mastering_worker = None
        self._active_mastering_request = None
        self._unlock_mastering_ui()

    @Slot(str)
    def _on_mastering_success(self, message: str) -> None:
        self.mastering_tab.set_status("Completed")
        if self._mastering_dialog:
            self._mastering_dialog.show_finished("Mastering completed", message)
        if self._pref_open_destination and self.mastering_output_directory:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.mastering_output_directory))
            )
        if self._pref_auto_clear_selection:
            self._clear_mastering_selection()
            self.mastering_tab.set_status("Completed")

    @Slot(str)
    def _on_mastering_error(self, message: str) -> None:
        self.mastering_tab.set_status("Mastering failed")
        if self._mastering_dialog:
            self._mastering_dialog.show_finished("Mastering failed", message)

    def _on_mastering_dialog_closed(self, _: int) -> None:
        self._mastering_dialog = None

    def _on_mastering_preset_changed(self, preset: str) -> None:
        if preset not in self._preset_definitions:
            return
        self._pref_mastering_preset = preset
        self._settings.setValue("mastering_default_preset", preset)
        self._update_mastering_preview()

    def _on_mastering_parameters_changed(
        self, parameters: MasteringParameters
    ) -> None:
        self._mastering_parameters = parameters

    def _on_mastering_suffix_changed(self, suffix: str) -> None:
        trimmed = suffix.strip()
        self._pref_mastering_suffix = trimmed
        self._settings.setValue("mastering_filename_suffix", trimmed)
        self._update_mastering_preview()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _lock_convert_ui(self) -> None:
        self.convert_tab.set_export_enabled(False)
        self.convert_tab.set_browse_enabled(False)
        self.convert_tab.set_clear_enabled(False)
        self.convert_tab.set_destination_enabled(False)
        self.convert_tab.set_format_enabled(False)

    def _unlock_convert_ui(self) -> None:
        self.convert_tab.set_export_enabled(True)
        self.convert_tab.set_browse_enabled(True)
        self.convert_tab.set_destination_enabled(True)
        self.convert_tab.set_format_enabled(True)
        self.convert_tab.set_clear_enabled(bool(self.input_files))

    def _lock_trim_ui(self) -> None:
        self.trim_tab.set_trim_enabled(False)
        self.trim_tab.set_browse_enabled(False)
        self.trim_tab.set_clear_enabled(False)
        self.trim_tab.set_destination_enabled(False)
        self.trim_tab.set_controls_enabled(False)

    def _unlock_trim_ui(self) -> None:
        self.trim_tab.set_trim_enabled(True)
        self.trim_tab.set_browse_enabled(True)
        self.trim_tab.set_destination_enabled(True)
        self.trim_tab.set_controls_enabled(True)
        self.trim_tab.set_clear_enabled(bool(self.trim_files))

    def _lock_mastering_ui(self) -> None:
        self.mastering_tab.set_export_enabled(False)
        self.mastering_tab.set_browse_enabled(False)
        self.mastering_tab.set_clear_enabled(False)
        self.mastering_tab.set_destination_enabled(False)
        self.mastering_tab.set_controls_enabled(False)

    def _unlock_mastering_ui(self) -> None:
        self.mastering_tab.set_export_enabled(True)
        self.mastering_tab.set_browse_enabled(True)
        self.mastering_tab.set_destination_enabled(True)
        self.mastering_tab.set_controls_enabled(True)
        self.mastering_tab.set_clear_enabled(bool(self.mastering_files))

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        if self._trim_thread and self._trim_thread.isRunning():
            self._trim_thread.quit()
            self._trim_thread.wait(2000)
        if self._mastering_thread and self._mastering_thread.isRunning():
            self._mastering_thread.quit()
            self._mastering_thread.wait(2000)
        if self._pref_remember_geometry:
            geometry = self.saveGeometry()
            self._settings.setValue("window_geometry", geometry)
            self._saved_geometry = geometry
        super().closeEvent(event)
