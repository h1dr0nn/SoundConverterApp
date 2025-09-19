"""Background worker classes used by the UI."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from .converter import ConversionRequest, ConversionResult, SoundConverter
from .mastering import MasteringEngine, MasteringRequest, MasteringResult


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


class MasteringWorker(QObject):
    """QObject-based worker that executes mastering in a thread."""

    finished = Signal()
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self, engine: MasteringEngine, request: MasteringRequest
    ) -> None:
        super().__init__()
        self._engine = engine
        self._request = request
        self._result: Optional[MasteringResult] = None

    @property
    def result(self) -> Optional[MasteringResult]:
        """Return the result of the most recent mastering job, if available."""

        return self._result

    @Slot()
    def run(self) -> None:
        result = self._engine.process(self._request)
        self._result = result
        if result.success:
            self.succeeded.emit(result.message)
        else:
            self.failed.emit(result.message)
        self.finished.emit()
