"""Business logic layer responsible for audio conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

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
    """Data container describing a batch conversion job."""

    input_paths: Sequence[Path]
    output_directory: Path
    output_format: str

    def outputs(self) -> Iterable[Tuple[Path, Path]]:
        """Yield tuples of (input_path, output_path) for the batch."""

        for source in self.input_paths:
            destination = self.output_directory / f"{source.stem}.{self.output_format}"
            yield source, destination


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

        if not request.input_paths:
            return False, "Không có tệp âm thanh nào được chọn."

        output_format = request.output_format.lower()
        destination_root = request.output_directory

        missing_inputs = [path for path in request.input_paths if not path.exists()]
        if missing_inputs:
            if len(missing_inputs) == 1:
                return False, f"Không tìm thấy tệp {missing_inputs[0]}"
            joined = ", ".join(str(path) for path in missing_inputs)
            return False, f"Không tìm thấy các tệp: {joined}"

        if AudioSegment is None:
            assert _IMPORT_ERROR is not None  # for type checkers
            missing_package = _IMPORT_ERROR.name or "pydub"

            if missing_package in {"audioop", "pyaudioop"}:
                return (
                    False,
                    "Phiên bản Python hiện tại thiếu mô-đun 'audioop' mà `pydub` cần. "
                    "Bạn có thể cài đặt gói tương thích `audioop-lts` (ví dụ: chạy "
                    "`pip install audioop-lts`) hoặc chuyển sang phiên bản Python 3.12 "
                    "trở xuống vốn bao gồm sẵn 'audioop'.",
                )

            if missing_package == "pydub":
                suggestion = "`pip install -r requirements.txt`"
            else:
                suggestion = f"`pip install {missing_package}`"

            return (
                False,
                "Không tìm thấy thư viện "
                f"'{missing_package}'. Vui lòng cài đặt bằng lệnh {suggestion}.",
            )

        converted: List[Path] = []
        destination_root.mkdir(parents=True, exist_ok=True)

        for input_path, output_path in request.outputs():
            try:
                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format=output_format)
                converted.append(output_path)
            except Exception as exc:  # pragma: no cover - thin wrapper
                if len(request.input_paths) == 1:
                    return False, str(exc)
                return False, f"Không thể chuyển đổi '{input_path.name}': {exc}"

        if not converted:
            return False, "Không thể chuyển đổi các tệp đã chọn."

        if len(converted) == 1:
            return True, f"Đã lưu tệp tại {converted[0]}"

        destination_text = destination_root if destination_root else converted[0].parent
        return True, f"Đã chuyển đổi {len(converted)} tệp vào {destination_text}"
