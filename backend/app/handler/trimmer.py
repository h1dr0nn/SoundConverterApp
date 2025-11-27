"""Silence trimming logic."""

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

try:
    from pydub import silence  # type: ignore
except ModuleNotFoundError:
    silence = None


@dataclass(frozen=True)
class TrimRequest:
    """Description of a silence trimming job."""

    input_paths: Sequence[Path]
    output_directory: Path
    silence_threshold: float = -50.0
    minimum_silence_ms: int = 500
    padding_ms: int = 0
    overwrite_existing: bool = True

    def outputs(self) -> Iterable[Tuple[Path, Path]]:
        allocated: set[Path] = set()
        for source in self.input_paths:
            suffix = source.suffix if source.suffix else ".wav"
            base_destination = self.output_directory / f"{source.stem}{suffix}"
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
class TrimResult:
    success: bool
    message: str
    outputs: Tuple[Path, ...] = ()


class SilenceTrimmer:
    """Trim leading and trailing silence from audio files using ``pydub``."""

    @classmethod
    def process(cls, request: TrimRequest) -> TrimResult:
        try:
            validate_input_paths(list(request.input_paths))
            validate_pydub_available()
            if silence is None:
                from ..ffmpeg_runner import MissingDependencyError
                raise MissingDependencyError("pydub")
            resolve_environment()
            outputs = cls._process_batch(request)
            if not outputs:
                raise NoOutputProducedError()
        except AudioProcessingError as error:
            message = format_error_message(error)
            return TrimResult(False, message, ())

        message = cls._format_success_message(request, outputs)
        return TrimResult(True, message, outputs)

    @classmethod
    def _process_batch(cls, request: TrimRequest) -> Tuple[Path, ...]:
        assert AudioSegment is not None and silence is not None

        trimmed_outputs: list[Path] = []
        request.output_directory.mkdir(parents=True, exist_ok=True)

        for input_path, output_path in request.outputs():
            try:
                audio = AudioSegment.from_file(input_path)
                trimmed = cls._trim_audio(
                    audio,
                    silence_threshold=request.silence_threshold,
                    minimum_silence=request.minimum_silence_ms,
                    padding=request.padding_ms,
                )
                output_format = input_path.suffix.lstrip(".") or "wav"
                trimmed.export(output_path, format=output_format)
            except Exception as exc:
                raise ExportFailureError(input_path, exc, len(request.input_paths))
            trimmed_outputs.append(output_path)

        return tuple(trimmed_outputs)

    @classmethod
    def _trim_audio(
        cls,
        audio: AudioSegment,
        *,
        silence_threshold: float,
        minimum_silence: int,
        padding: int,
    ) -> AudioSegment:
        assert silence is not None

        if minimum_silence < 0:
            minimum_silence = 0
        if padding < 0:
            padding = 0

        ranges = silence.detect_nonsilent(
            audio,
            min_silence_len=max(0, int(minimum_silence)),
            silence_thresh=float(silence_threshold),
        )

        if not ranges:
            return audio

        start = max(0, ranges[0][0] - padding)
        end = min(len(audio), ranges[-1][1] + padding)

        if end <= start:
            return audio

        trimmed = audio[start:end]
        if len(trimmed) == 0:
            return audio
        return trimmed

    @classmethod
    def _format_success_message(cls, request: TrimRequest, outputs: Tuple[Path, ...]) -> str:
        if len(outputs) == 1:
            return f"Saved trimmed file to {outputs[0]}"
        destination_text = (
            request.output_directory if request.output_directory else outputs[0].parent
        )
        return f"Trimmed silence from {len(outputs)} files into {destination_text}"
