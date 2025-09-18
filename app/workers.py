"""Background worker classes used by the UI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .converter import ConversionRequest, SoundConverter


class ConversionWorker(QObject):
    """QObject-based worker that executes the conversion in a thread."""

    finished = Signal()
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, converter: SoundConverter, request: ConversionRequest) -> None:
        super().__init__()
        self._converter = converter
        self._request = request

    @Slot()
    def run(self) -> None:
        success, message = self._converter.convert(self._request)
        if success:
            self.succeeded.emit(message)
        else:
            self.failed.emit(message)
        self.finished.emit()
