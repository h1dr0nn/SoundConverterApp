"""Audio format conversion logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Tuple

from ..ffmpeg_runner import (
    AudioSegment,
    AudioProcessingError,
    ExportFailureError,
    NoOutputProducedError,
    format_error_message,
    resolve_environment,
    validate_input_paths,
    validate_pydub_available,
)


@dataclass(frozen=True)
class ConversionRequest:
    """Data container describing a batch conversion job."""

    input_paths: Sequence[Path]
    output_directory: Path
    output_format: str
    overwrite_existing: bool = True

    def outputs(self) -> Iterable[Tuple[Path, Path]]:
        """Yield tuples of ``(input_path, output_path)`` for the batch."""
        allocated: set[Path] = set()

        for source in self.input_paths:
            base_destination = self.output_directory / f"{source.stem}.{self.output_format}"
            destination = base_destination

            if not self.overwrite_existing:
                candidate = base_destination
                index = 1
                while candidate.exists() or candidate in allocated:
                    candidate = base_destination.with_stem(
                        f"{base_destination.stem} ({index})"
                    )
                    index += 1
                destination = candidate

            allocated.add(destination)
            yield source, destination


@dataclass(frozen=True)
class ConversionResult:
    """Outcome returned by :meth:`SoundConverter.convert`."""

    success: bool
    message: str
    outputs: Tuple[Path, ...] = ()


class SoundConverter:
    """Convert audio files to a different format using ``pydub``."""

    SUPPORTED_FORMATS: Sequence[str] = ("mp3", "wav", "ogg", "flac", "aac", "wma")

    @staticmethod
    def available_formats() -> Iterable[str]:
        return SoundConverter.SUPPORTED_FORMATS

    @staticmethod
    def convert(request: ConversionRequest) -> ConversionResult:
        """Run the conversion and return a structured result."""
        try:
            validate_input_paths(list(request.input_paths))
            validate_pydub_available()
            output_format = request.output_format.lower()
            resolve_environment()
            outputs = SoundConverter._export_batch(request, output_format)
            if not outputs:
                raise NoOutputProducedError()
        except AudioProcessingError as error:
            message = format_error_message(error)
            return ConversionResult(False, message, ())

        message = SoundConverter._format_success_message(request, outputs)
        return ConversionResult(True, message, outputs)

    @staticmethod
    def _export_batch(request: ConversionRequest, output_format: str) -> Tuple[Path, ...]:
        assert AudioSegment is not None

        converted: list[Path] = []
        request.output_directory.mkdir(parents=True, exist_ok=True)

        for input_path, output_path in request.outputs():
            try:
                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format=output_format)
            except Exception as exc:
                raise ExportFailureError(input_path, exc, len(request.input_paths))
            converted.append(output_path)

        return tuple(converted)

    @staticmethod
    def _format_success_message(request: ConversionRequest, outputs: Tuple[Path, ...]) -> str:
        if len(outputs) == 1:
            return f"Saved file to {outputs[0]}"
        destination_text = (
            request.output_directory if request.output_directory else outputs[0].parent
        )
        return f"Converted {len(outputs)} files into {destination_text}"
