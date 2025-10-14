"""Business logic layer responsible for trimming silence from audio files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Set, Tuple

try:  # pragma: no cover - exercised indirectly via integration
    from pydub import AudioSegment, silence  # type: ignore
    from pydub.utils import which as _find_executable  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled gracefully
    AudioSegment = None  # type: ignore[assignment]
    silence = None  # type: ignore[assignment]
    _find_executable = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


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
        """Yield tuples of ``(input_path, output_path)`` for the batch."""

        allocated: Set[Path] = set()

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
    """Outcome returned by :meth:`SilenceTrimmer.process`."""

    success: bool
    message: str
    outputs: Tuple[Path, ...] = ()


class _TrimError(RuntimeError):
    """Base class for internal trimming errors."""


class _NoInputError(_TrimError):
    """Raised when the request does not contain any files."""


class _MissingInputFilesError(_TrimError):
    """Raised when one or more selected files are not available."""

    def __init__(self, missing: Sequence[Path]):
        super().__init__("missing input files")
        self.missing = tuple(missing)


class _MissingDependencyError(_TrimError):
    """Raised when ``pydub`` or an optional dependency is unavailable."""

    def __init__(self, package: str):
        super().__init__(f"missing dependency: {package}")
        self.package = package


class _MissingEncoderError(_TrimError):
    """Raised when neither FFmpeg nor avconv can be located."""


class _ExportFailureError(_TrimError):
    """Raised when exporting a trimmed file fails."""

    def __init__(self, source: Path, error: Exception, total_inputs: int):
        super().__init__("export failure")
        self.source = source
        self.error = error
        self.total_inputs = total_inputs


class _NoOutputProducedError(_TrimError):
    """Raised when no files were produced despite processing input."""


class SilenceTrimmer:
    """Trim leading and trailing silence from audio files using ``pydub``."""

    @classmethod
    def process(cls, request: TrimRequest) -> TrimResult:
        """Run the trimming workflow and return a structured result."""

        try:
            cls._validate_request(request)
            cls._resolve_environment()
            outputs = cls._process_batch(request)
            if not outputs:
                raise _NoOutputProducedError()
        except _TrimError as error:
            message = cls._format_error_message(error)
            return TrimResult(False, message, ())

        message = cls._format_success_message(request, outputs)
        return TrimResult(True, message, outputs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _validate_request(cls, request: TrimRequest) -> None:
        if not request.input_paths:
            raise _NoInputError()

        missing_inputs = [path for path in request.input_paths if not path.exists()]
        if missing_inputs:
            raise _MissingInputFilesError(missing_inputs)

        if AudioSegment is None or silence is None:
            assert _IMPORT_ERROR is not None  # for type checkers
            missing_package = _IMPORT_ERROR.name or "pydub"
            raise _MissingDependencyError(missing_package)

    @classmethod
    def _resolve_environment(cls) -> None:
        if AudioSegment is None or silence is None:
            raise _MissingDependencyError("pydub")

        converter_override = getattr(AudioSegment, "converter", None)
        bundled_converter_available = False

        if converter_override:
            try:
                converter_path = Path(converter_override)
            except TypeError:  # defensive: unexpected converter value
                converter_path = None
            else:
                if converter_path.is_file():
                    bundled_converter_available = True

        if bundled_converter_available:
            return

        if _find_executable is None:
            raise _MissingEncoderError()

        encoder = next(
            (
                found
                for candidate in ("ffmpeg", "avconv")
                for found in (_find_executable(candidate),)
                if found
            ),
            None,
        )
        if encoder is None:
            raise _MissingEncoderError()

    @classmethod
    def _process_batch(cls, request: TrimRequest) -> Tuple[Path, ...]:
        assert AudioSegment is not None and silence is not None  # for type checkers

        trimmed_outputs: List[Path] = []
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
            except Exception as exc:  # pragma: no cover - thin wrapper
                raise _ExportFailureError(input_path, exc, len(request.input_paths))
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
        assert silence is not None  # for type checkers

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
    def _format_success_message(
        cls, request: TrimRequest, outputs: Tuple[Path, ...]
    ) -> str:
        if len(outputs) == 1:
            return f"Saved trimmed file to {outputs[0]}"

        destination_text = (
            request.output_directory if request.output_directory else outputs[0].parent
        )
        return f"Trimmed silence from {len(outputs)} files into {destination_text}"

    @classmethod
    def _format_error_message(cls, error: _TrimError) -> str:
        if isinstance(error, _NoInputError):
            return "No audio files were selected."

        if isinstance(error, _MissingInputFilesError):
            missing = error.missing
            if len(missing) == 1:
                return f"The file '{missing[0]}' could not be found."
            joined = ", ".join(str(path) for path in missing)
            return f"The following files are missing: {joined}"

        if isinstance(error, _MissingDependencyError):
            missing_package = error.package
            if missing_package in {"audioop", "pyaudioop"}:
                return (
                    "The current Python build is missing the optional 'audioop' module "
                    "required by pydub. Install the compatible 'audioop-lts' package "
                    "(for example run `pip install audioop-lts`) or switch to Python "
                    "3.12 or earlier where it is bundled by default."
                )

            if missing_package == "pydub":
                suggestion = "`pip install -r requirements.txt`"
            else:
                suggestion = f"`pip install {missing_package}`"

            return (
                f"The dependency '{missing_package}' is missing. Please install it "
                f"with {suggestion}."
            )

        if isinstance(error, _MissingEncoderError):
            return (
                "Neither 'ffmpeg' nor 'avconv' could be located. Install FFmpeg and "
                "ensure it is discoverable via the PATH environment variable."
            )

        if isinstance(error, _ExportFailureError):
            if error.total_inputs == 1:
                return str(error.error)
            return f"Could not trim '{error.source.name}': {error.error}"

        if isinstance(error, _NoOutputProducedError):
            return "None of the selected files could be trimmed."

        return "An unexpected error occurred while trimming audio files."


__all__ = ["TrimRequest", "TrimResult", "SilenceTrimmer"]

