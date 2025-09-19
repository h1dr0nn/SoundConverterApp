"""Business logic layer responsible for audio conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Set, Tuple

# ``pydub`` is an optional dependency during runtime because the GUI should be
# able to start even if the package is missing.  The actual conversion logic
# will report a clear error message when the import is not available instead of
# crashing immediately on startup.
try:  # pragma: no cover - exercised indirectly via integration
    from pydub import AudioSegment  # type: ignore
    from pydub.utils import which as _find_executable  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled gracefully
    AudioSegment = None  # type: ignore[assignment]
    _find_executable = None
    _IMPORT_ERROR = exc
else:
    _find_executable = _find_executable
    _IMPORT_ERROR = None


@dataclass(frozen=True)
class ConversionRequest:
    """Data container describing a batch conversion job."""

    input_paths: Sequence[Path]
    output_directory: Path
    output_format: str
    overwrite_existing: bool = True

    def outputs(self) -> Iterable[Tuple[Path, Path]]:
        """Yield tuples of ``(input_path, output_path)`` for the batch."""

        allocated: Set[Path] = set()

        for source in self.input_paths:
            base_destination = self.output_directory / f"{source.stem}.{self.output_format}"
            destination = base_destination

            if not self.overwrite_existing:
                candidate = base_destination
                index = 1
                # Avoid both on-disk conflicts and duplicates within the batch.
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


class _ConversionError(RuntimeError):
    """Base class for internal conversion errors."""


class _NoInputError(_ConversionError):
    """Raised when no input files were provided."""


class _MissingInputFilesError(_ConversionError):
    """Raised when one or more selected files are not available."""

    def __init__(self, missing: Sequence[Path]):
        super().__init__("missing input files")
        self.missing = tuple(missing)


class _MissingDependencyError(_ConversionError):
    """Raised when ``pydub`` or an optional dependency is unavailable."""

    def __init__(self, package: str):
        super().__init__(f"missing dependency: {package}")
        self.package = package


class _MissingEncoderError(_ConversionError):
    """Raised when neither FFmpeg nor avconv can be located."""


class _ExportFailureError(_ConversionError):
    """Raised when exporting a single file fails."""

    def __init__(self, source: Path, error: Exception, total_inputs: int):
        super().__init__("export failure")
        self.source = source
        self.error = error
        self.total_inputs = total_inputs


class _NoOutputProducedError(_ConversionError):
    """Raised when no files were produced despite successful processing."""


class SoundConverter:
    """Convert audio files to a different format using ``pydub``."""

    SUPPORTED_FORMATS: Sequence[str] = ("mp3", "wav", "ogg", "flac", "aac", "wma")

    @staticmethod
    def available_formats() -> Iterable[str]:
        """Return the iterable of supported formats."""

        return SoundConverter.SUPPORTED_FORMATS

    @staticmethod
    def convert(request: ConversionRequest) -> ConversionResult:
        """Run the conversion and return a structured result."""

        try:
            SoundConverter._validate_request(request)
            output_format = request.output_format.lower()
            SoundConverter._resolve_environment()
            outputs = SoundConverter._export_batch(request, output_format)
            if not outputs:
                raise _NoOutputProducedError()
        except _ConversionError as error:
            message = SoundConverter._format_error_message(error)
            return ConversionResult(False, message, ())

        message = SoundConverter._format_success_message(request, outputs)
        return ConversionResult(True, message, outputs)

    @staticmethod
    def _validate_request(request: ConversionRequest) -> None:
        if not request.input_paths:
            raise _NoInputError()

        missing_inputs = [path for path in request.input_paths if not path.exists()]
        if missing_inputs:
            raise _MissingInputFilesError(missing_inputs)

        if AudioSegment is None:
            assert _IMPORT_ERROR is not None  # for type checkers
            missing_package = _IMPORT_ERROR.name or "pydub"
            raise _MissingDependencyError(missing_package)

    @staticmethod
    def _resolve_environment() -> None:
        if AudioSegment is None:
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

    @staticmethod
    def _export_batch(request: ConversionRequest, output_format: str) -> Tuple[Path, ...]:
        assert AudioSegment is not None  # for type checkers

        converted: List[Path] = []
        request.output_directory.mkdir(parents=True, exist_ok=True)

        for input_path, output_path in request.outputs():
            try:
                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format=output_format)
            except Exception as exc:  # pragma: no cover - thin wrapper
                raise _ExportFailureError(input_path, exc, len(request.input_paths))
            converted.append(output_path)

        return tuple(converted)

    @staticmethod
    def _format_success_message(
        request: ConversionRequest, outputs: Tuple[Path, ...]
    ) -> str:
        if len(outputs) == 1:
            return f"Saved file to {outputs[0]}"

        destination_text = (
            request.output_directory if request.output_directory else outputs[0].parent
        )
        return f"Converted {len(outputs)} files into {destination_text}"

    @staticmethod
    def _format_error_message(error: _ConversionError) -> str:
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
            return f"Could not convert '{error.source.name}': {error.error}"

        if isinstance(error, _NoOutputProducedError):
            return "None of the selected files could be converted."

        return str(error)
