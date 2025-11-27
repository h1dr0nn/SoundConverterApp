"""Audio format conversion logic."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Tuple

from ..ffmpeg_runner import (
    AudioSegment,
    AudioProcessingError,
    ExportFailureError,
    MissingEncoderError,
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
    ffmpeg_path: Optional[Path] = None

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
    def convert(
        request: ConversionRequest,
        progress_callback: Optional[Callable[["ConversionProgress"], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> ConversionResult:
        """Run the conversion and return a structured result.

        Parameters
        ----------
        request:
            Conversion request payload.
        progress_callback:
            Optional callback invoked with :class:`ConversionProgress` updates.
        log_callback:
            Optional callback invoked with FFmpeg stderr lines.
        """
        try:
            validate_input_paths(list(request.input_paths))
            validate_pydub_available()
            resolve_environment()
            outputs = SoundConverter._export_batch(
                request, progress_callback, log_callback
            )
            if not outputs:
                raise NoOutputProducedError()
        except AudioProcessingError as error:
            message = format_error_message(error)
            return ConversionResult(False, message, ())

        message = SoundConverter._format_success_message(request, outputs)
        return ConversionResult(True, message, outputs)

    @staticmethod
    def _export_batch(
        request: ConversionRequest,
        progress_callback: Optional[Callable[[ConversionProgress], None]],
        log_callback: Optional[Callable[[str], None]],
    ) -> Tuple[Path, ...]:
        """Export all files in the batch."""
        converted = []

        for index, (input_path, output_path) in enumerate(request.outputs(), start=1):
            if progress_callback:
                progress_callback(
                    ConversionProgress(
                        status="processing",
                        index=index,
                        total=len(request.input_paths),
                        source=input_path,
                        destination=output_path,
                    )
                )

            try:
                converter = _resolve_converter_path(request)
                
                # Check for in-place conversion (input == output)
                # FFmpeg cannot read/write same file, so we write to temp file first
                use_temp_file = input_path.resolve() == output_path.resolve()
                actual_output_path = output_path
                
                if use_temp_file:
                    actual_output_path = output_path.with_suffix(f".tmp{output_path.suffix}")
                    if log_callback:
                        log_callback(f"In-place conversion detected. Using temp file: {actual_output_path}")

                _run_ffmpeg_conversion(
                    converter,
                    input_path,
                    actual_output_path,
                    request.output_format.lower(),
                    log_callback,
                )
                
                # If using temp file, move it to final destination after success
                if use_temp_file:
                    import shutil
                    shutil.move(str(actual_output_path), str(output_path))
                    if log_callback:
                        log_callback(f"Renamed temp file to: {output_path}")
            except Exception as exc:
                raise ExportFailureError(input_path, exc, len(request.input_paths))

            converted.append(output_path)

            if progress_callback:
                progress_callback(
                    ConversionProgress(
                        status="completed",
                        index=index,
                        total=len(request.input_paths),
                        source=input_path,
                        destination=output_path,
                    )
                )

        return tuple(converted)

    @staticmethod
    def _format_success_message(request: ConversionRequest, outputs: Tuple[Path, ...]) -> str:
        if len(outputs) == 1:
            return f"Saved file to {outputs[0]}"
        destination_text = (
            request.output_directory if request.output_directory else outputs[0].parent
        )
        return f"Converted {len(outputs)} files into {destination_text}"


@dataclass(frozen=True)
class ConversionProgress:
    """Progress payload for individual files."""

    status: str
    index: int
    total: int
    source: Path
    destination: Path


def _run_ffmpeg_conversion(
    converter: Path,
    input_path: Path,
    output_path: Path,
    output_format: str,
    log_callback: Optional[Callable[[str], None]],
) -> None:
    """Run FFmpeg conversion with explicit format and codec specification."""
    
    # Map output format to FFmpeg codec and format
    # This ensures proper encoding instead of relying on extension guessing
    format_codec_map = {
        "mp3": {"format": "mp3", "codec": "libmp3lame", "bitrate": "192k"},
        "aac": {"format": "adts", "codec": "aac", "bitrate": "192k"},
        "m4a": {"format": "ipod", "codec": "aac", "bitrate": "192k"},
        "wav": {"format": "wav", "codec": "pcm_s16le"},
        "flac": {"format": "flac", "codec": "flac"},
        "ogg": {"format": "ogg", "codec": "libvorbis", "bitrate": "192k"},
        "opus": {"format": "opus", "codec": "libopus", "bitrate": "128k"},
        "wma": {"format": "asf", "codec": "wmav2", "bitrate": "192k"},
    }
    
    format_lower = output_format.lower()
    codec_config = format_codec_map.get(format_lower, {})
    
    # Build FFmpeg command with explicit codec and format
    command = [
        str(converter),
        "-y",  # Overwrite output
        "-i", str(input_path),
    ]
    
    # Add codec specification
    if "codec" in codec_config:
        command.extend(["-c:a", codec_config["codec"]])
    
    # Add bitrate for lossy formats
    if "bitrate" in codec_config:
        command.extend(["-b:a", codec_config["bitrate"]])
    
    # Add format specification
    if "format" in codec_config:
        command.extend(["-f", codec_config["format"]])
    
    command.append(str(output_path))

    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert process.stderr is not None
    for line in process.stderr:
        if log_callback:
            log_callback(line.rstrip())

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with code {return_code}")


def _resolve_converter_path(request: ConversionRequest) -> Path:
    """Resolve the ffmpeg binary to use for conversion."""

    candidates = []

    if request.ffmpeg_path:
        candidates.append(request.ffmpeg_path)

    env_candidates = [
        os.environ.get("FFMPEG_BINARY"),
        os.environ.get("FFMPEG_BIN"),
    ]
    candidates.extend(Path(path) for path in env_candidates if path)

    if AudioSegment is not None:
        converter_attr = getattr(AudioSegment, "converter", None)
        if converter_attr:
            candidates.append(Path(converter_attr))

    from shutil import which

    default_path = which("ffmpeg")
    if default_path:
        candidates.append(Path(default_path))

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate

    raise MissingEncoderError()
