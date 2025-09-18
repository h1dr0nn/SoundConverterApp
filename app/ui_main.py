"""PySide6 user interface for the Sound Converter application."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Set

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
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

        self._title = QLabel("Kéo và thả tệp âm thanh")
        self._title.setObjectName("dropTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        self._subtitle = QLabel("hoặc bấm để chọn từ máy của bạn")
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


class MainWindow(QWidget):
    """The primary window managing user interaction."""

    def __init__(self, converter: SoundConverter) -> None:
        super().__init__()
        self.converter = converter
        self.input_files: List[Path] = []
        self.output_directory: Optional[Path] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConversionWorker] = None

        self._setup_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setWindowTitle("Sound Converter")
        self.setWindowIcon(QIcon(str(resource_path("icons", "app.svg"))))
        self.resize(620, 480)
        self.setMinimumWidth(520)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(20)

        header = QLabel("Sound Converter")
        header.setObjectName("titleLabel")
        main_layout.addWidget(header)

        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self._handle_input_files)
        self.drop_area.clicked.connect(self._open_file_dialog)
        main_layout.addWidget(self.drop_area)

        self.input_label = QLabel("Chưa chọn tệp")
        self.input_label.setObjectName("pathLabel")
        self.input_label.setWordWrap(True)
        main_layout.addWidget(self.input_label)

        file_actions = QHBoxLayout()
        file_actions.setSpacing(12)

        self.browse_button = QPushButton("Chọn tệp âm thanh")
        self.browse_button.setObjectName("browseButton")
        self.browse_button.clicked.connect(self._open_file_dialog)
        file_actions.addWidget(self.browse_button)

        self.clear_button = QPushButton("Xóa lựa chọn")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self._clear_selection)
        self.clear_button.setEnabled(False)
        file_actions.addWidget(self.clear_button)

        file_actions.addStretch()
        main_layout.addLayout(file_actions)

        format_layout = QHBoxLayout()
        format_layout.setSpacing(12)

        format_label = QLabel("Định dạng xuất")
        format_label.setObjectName("sectionLabel")
        format_layout.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("formatCombo")
        self.format_combo.addItems(self.converter.available_formats())
        self.format_combo.currentTextChanged.connect(self._update_output_preview)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        main_layout.addLayout(format_layout)

        destination_layout = QVBoxLayout()
        destination_layout.setSpacing(8)

        destination_header = QLabel("Nơi lưu kết quả")
        destination_header.setObjectName("sectionLabel")
        destination_layout.addWidget(destination_header)

        destination_controls = QHBoxLayout()
        destination_controls.setSpacing(12)

        self.output_edit = QLineEdit()
        self.output_edit.setObjectName("outputEdit")
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Đường dẫn file xuất sẽ hiển thị tại đây")
        destination_controls.addWidget(self.output_edit)

        self.destination_button = QPushButton("Chọn thư mục")
        self.destination_button.setObjectName("destinationButton")
        self.destination_button.clicked.connect(self._choose_output_directory)
        destination_controls.addWidget(self.destination_button)

        destination_layout.addLayout(destination_controls)
        main_layout.addLayout(destination_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        main_layout.addWidget(self.progress_bar)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)

        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setObjectName("statusLabel")
        footer_layout.addWidget(self.status_label)

        footer_layout.addStretch()

        self.export_button = QPushButton("Xuất file")
        self.export_button.setObjectName("exportButton")
        self.export_button.clicked.connect(self._export_audio)
        footer_layout.addWidget(self.export_button)

        main_layout.addLayout(footer_layout)

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
            "Chọn tệp âm thanh",
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
                "Không thể tìm thấy: " + ", ".join(path.name for path in missing)
            )

        if unsupported:
            skipped_messages.append(
                "Định dạng không hỗ trợ: "
                + ", ".join(path.name for path in unsupported)
            )

        if skipped_messages:
            QMessageBox.warning(
                self,
                "Một số tệp bị bỏ qua",
                "\n".join(skipped_messages),
            )

        if not valid_files:
            QMessageBox.warning(
                self,
                "Không có tệp hợp lệ",
                "Vui lòng chọn ít nhất một tệp âm thanh hợp lệ.",
            )
            return

        self.input_files = valid_files
        if self.output_directory is None and self.input_files:
            self.output_directory = self.input_files[0].parent

        if len(self.input_files) == 1:
            selected = self.input_files[0]
            self.input_label.setText(str(selected))
            self.drop_area.set_description("Tệp đã được chọn", selected.name)
        else:
            summary_lines = [path.name for path in self.input_files[:3]]
            remaining = len(self.input_files) - len(summary_lines)
            if remaining > 0:
                summary_lines.append(f"... và {remaining} tệp khác")
            self.input_label.setText("\n".join(summary_lines))
            self.drop_area.set_description(
                f"Đã chọn {len(self.input_files)} tệp", "Kéo thêm tệp để thay đổi"
            )

        self.clear_button.setEnabled(True)
        self._update_output_preview()

    def _clear_selection(self) -> None:
        self.input_files = []
        self.output_directory = None
        self.drop_area.set_description("Kéo và thả tệp âm thanh", "hoặc bấm để chọn từ máy của bạn")
        self.input_label.setText("Chưa chọn tệp")
        self.output_edit.clear()
        self.clear_button.setEnabled(False)

    def _choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu")
        if directory:
            self.output_directory = Path(directory)
            self._update_output_preview()

    def _update_output_preview(self) -> None:
        if not self.input_files:
            self.output_edit.clear()
            return

        destination = self.output_directory or self.input_files[0].parent
        output_format = self.format_combo.currentText()
        if len(self.input_files) == 1:
            output_path = destination / f"{self.input_files[0].stem}.{output_format}"
            self.output_edit.setText(str(output_path))
        else:
            self.output_edit.setText(
                f"Sẽ lưu {len(self.input_files)} tệp vào {destination}"
            )

    def _export_audio(self) -> None:
        if not self.input_files:
            QMessageBox.warning(self, "Thiếu tệp", "Vui lòng chọn tệp âm thanh trước.")
            return

        destination = self.output_directory or self.input_files[0].parent
        if not destination:
            QMessageBox.warning(self, "Thiếu nơi lưu", "Vui lòng chọn thư mục lưu kết quả.")
            return

        request = ConversionRequest(
            input_paths=tuple(self.input_files),
            output_directory=destination,
            output_format=self.format_combo.currentText(),
        )

        self._lock_ui()
        self.status_label.setText("Đang chuyển đổi...")
        self.progress_bar.setVisible(True)

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
        self.progress_bar.setVisible(False)
        self._unlock_ui()

    @Slot(str)
    def _on_conversion_success(self, message: str) -> None:
        self.status_label.setText("Hoàn tất")
        QMessageBox.information(self, "Hoàn tất", message)

    @Slot(str)
    def _on_conversion_error(self, message: str) -> None:
        self.status_label.setText("Có lỗi xảy ra")
        QMessageBox.critical(self, "Lỗi", message)

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
        super().closeEvent(event)
