"""Business logic layer responsible for audio conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

try:  # pragma: no cover - import guarded for friendlier UX
    from pydub import AudioSegment  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    AudioSegment = None  # type: ignore[assignment]
    _IMPORT_ERROR: Optional[ModuleNotFoundError] = exc
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
    def dependencies_ready() -> Tuple[bool, str]:
        """Check whether the audio backend is available."""

        if AudioSegment is None:
            hint = (
                "Thư viện 'pydub' chưa được cài đặt.\n"
                "Hãy chạy `pip install -r requirements.txt` trước khi sử dụng ứng dụng."
            )
            if _IMPORT_ERROR is not None:
                hint += f"\n\nChi tiết lỗi: {_IMPORT_ERROR}"
            return False, hint
        return True, ""

    @staticmethod
    def convert(request: ConversionRequest) -> Tuple[bool, str]:
        """Run the conversion and return a status flag and message."""

        ready, message = SoundConverter.dependencies_ready()
        if not ready:
            return False, message

        input_path = request.input_path
        output_path = request.output_path
        output_format = request.output_format.lower()

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=output_format)
            if output_path.exists():
                return True, f"Đã lưu tệp tại {output_path}"
            return True, "Hoàn tất chuyển đổi"
        except Exception as exc:  # pragma: no cover - thin wrapper
            return False, str(exc)
