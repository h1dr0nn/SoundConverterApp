"""Background worker classes used by the UI."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from .converter import ConversionRequest, ConversionResult, SoundConverter


class ConversionWorker(QObject):
    """QObject-based worker that executes the conversion in a thread."""

    finished = Signal()
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, converter: SoundConverter, request: ConversionRequest) -> None:
        super().__init__()
        self._converter = converter
        self._request = request
        self._result: Optional[ConversionResult] = None

    @property
    def result(self) -> Optional[ConversionResult]:
        """Return the result of the most recent conversion, if available."""

        return self._result

    @Slot()
    def run(self) -> None:
        result = self._converter.convert(self._request)
        self._result = result
        if result.success:
            self.succeeded.emit(result.message)
        else:
            self.failed.emit(result.message)
        self.finished.emit()
