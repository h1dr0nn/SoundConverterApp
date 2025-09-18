"""Business logic layer responsible for audio conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Tuple

# ``pydub`` is an optional dependency during runtime because the GUI should be
# able to start even if the package is missing.  The actual conversion logic
# will report a clear error message when the import is not available instead of
# crashing immediately on startup.
try:  # pragma: no cover - exercised indirectly via integration
    from pydub import AudioSegment  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled gracefully
    AudioSegment = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@dataclass(frozen=True)
class ConversionRequest:
    """Small data container describing a conversion job."""

    input_path: Path
    output_path: Path
    output_format: str


class SoundConverter:
    """Convert audio files to a different format using ``pydub``."""

    SUPPORTED_FORMATS: Sequence[str] = ("mp3", "wav", "ogg", "flac", "aac", "wma")

    @staticmethod
    def available_formats() -> Iterable[str]:
        """Return the iterable of supported formats."""

        return SoundConverter.SUPPORTED_FORMATS

    @staticmethod
    def convert(request: ConversionRequest) -> Tuple[bool, str]:
        """Run the conversion and return a status flag and message."""

        input_path = request.input_path
        output_path = request.output_path
        output_format = request.output_format.lower()

        if AudioSegment is None:
            assert _IMPORT_ERROR is not None  # for type checkers
            missing_package = _IMPORT_ERROR.name or "pydub"
            return (
                False,
                "Không tìm thấy thư viện "
                f"'{missing_package}'. Vui lòng cài đặt bằng lệnh "
                "`pip install -r requirements.txt`.",
            )

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=output_format)
            if output_path.exists():
                return True, f"Đã lưu tệp tại {output_path}"
            return True, "Hoàn tất chuyển đổi"
        except Exception as exc:  # pragma: no cover - thin wrapper
            return False, str(exc)
