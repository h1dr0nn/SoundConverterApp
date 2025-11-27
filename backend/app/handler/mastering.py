"""Audio mastering logic."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

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
    from pydub import effects  # type: ignore
except ModuleNotFoundError:
    effects = None


@dataclass(frozen=True)
class MasteringParameters:
    """Collection of user-defined mastering adjustments."""

    target_lufs: float = -14.0
    apply_compression: bool = True
    apply_limiter: bool = True
    output_gain: float = 0.0


@dataclass(frozen=True)
class MasteringRequest:
    """Description of an automatic mastering job."""

    input_paths: Sequence[Path]
    output_directory: Path
    preset: str
    parameters: MasteringParameters
    filename_suffix: str = "_mastered"
    overwrite_existing: bool = True

    def outputs(self) -> Iterable[Tuple[Path, Path]]:
        allocated: set[Path] = set()
        for source in self.input_paths:
            suffix = source.suffix if source.suffix else ".wav"
            suffix_text = self.filename_suffix.strip()
            stem = f"{source.stem}{suffix_text}" if suffix_text else source.stem
            base_destination = self.output_directory / f"{stem}{suffix}"
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
class MasteringResult:
    success: bool
    message: str
    outputs: Tuple[Path, ...] = ()


class MasteringEngine:
    """Apply simple mastering effects to audio files using ``pydub``."""

    PRESETS: Dict[str, MasteringParameters] = {
        "Music": MasteringParameters(target_lufs=-12.0, output_gain=0.0),
        "Podcast": MasteringParameters(target_lufs=-16.0, output_gain=1.5),
        "Voice-over": MasteringParameters(
            target_lufs=-18.0,
            apply_compression=True,
            apply_limiter=True,
            output_gain=0.5,
        ),
    }

    @classmethod
    def process(cls, request: MasteringRequest) -> MasteringResult:
        try:
            validate_input_paths(list(request.input_paths))
            validate_pydub_available()
            resolve_environment()
            outputs = cls._process_batch(request)
            if not outputs:
                raise NoOutputProducedError()
        except AudioProcessingError as error:
            message = format_error_message(error)
            return MasteringResult(False, message, ())

        message = cls._format_success_message(request, outputs)
        return MasteringResult(True, message, outputs)

    @classmethod
    def _process_batch(cls, request: MasteringRequest) -> Tuple[Path, ...]:
        assert AudioSegment is not None

        mastered: list[Path] = []
        request.output_directory.mkdir(parents=True, exist_ok=True)

        for source, destination in request.outputs():
            try:
                audio = AudioSegment.from_file(source)
                processed = cls._apply_parameters(audio, request.parameters)
                export_format = destination.suffix[1:] if destination.suffix else "wav"
                processed.export(destination, format=export_format)
            except Exception as exc:
                raise ExportFailureError(source, exc, len(request.input_paths))
            mastered.append(destination)

        return tuple(mastered)

    @staticmethod
    def _apply_parameters(audio: "AudioSegment", parameters: MasteringParameters) -> "AudioSegment":
        processed = audio

        if parameters.apply_compression and effects is not None:
            processed = effects.compress_dynamic_range(
                processed,
                threshold=-20.0,
                ratio=4.0,
                attack=5,
                release=100,
            )

        if math.isfinite(parameters.target_lufs):
            current_level = processed.dBFS
            if math.isfinite(current_level):
                processed = processed.apply_gain(parameters.target_lufs - current_level)

        if parameters.apply_limiter:
            headroom = -1.0
            max_level = processed.max_dBFS
            if math.isfinite(max_level) and max_level > headroom:
                processed = processed.apply_gain(headroom - max_level)

        if parameters.output_gain:
            processed = processed.apply_gain(parameters.output_gain)

        return processed

    @staticmethod
    def _format_success_message(request: MasteringRequest, outputs: Sequence[Path]) -> str:
        preset_name = request.preset
        if len(outputs) == 1:
            return f"'{outputs[0].name}' mastered successfully using the '{preset_name}' preset."
        return f"{len(outputs)} files mastered successfully using the '{preset_name}' preset."
