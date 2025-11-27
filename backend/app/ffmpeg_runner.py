"""Shared FFmpeg execution helpers and common audio processing utilities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydub import AudioSegment as AudioSegmentType

# Import handling for optional pydub dependency
try:
    from pydub import AudioSegment  # type: ignore
    from pydub.utils import which as _find_executable  # type: ignore
except ModuleNotFoundError as exc:
    AudioSegment = None  # type: ignore[assignment]
    _find_executable = None
    _IMPORT_ERROR = exc
else:
    _find_executable = _find_executable
    _IMPORT_ERROR = None


# ----------------------------------------------------------------------
# Shared Exceptions
# ----------------------------------------------------------------------

class AudioProcessingError(RuntimeError):
    """Base class for internal audio processing errors."""


class NoInputError(AudioProcessingError):
    """Raised when no input files were provided."""


class MissingInputFilesError(AudioProcessingError):
    """Raised when one or more selected files are not available."""

    def __init__(self, missing: list[Path]):
        super().__init__("missing input files")
        self.missing = tuple(missing)


class MissingDependencyError(AudioProcessingError):
    """Raised when ``pydub`` or an optional dependency is unavailable."""

    def __init__(self, package: str):
        super().__init__(f"missing dependency: {package}")
        self.package = package


class MissingEncoderError(AudioProcessingError):
    """Raised when neither FFmpeg nor avconv can be located."""


class ExportFailureError(AudioProcessingError):
    """Raised when exporting a single file fails."""

    def __init__(self, source: Path, error: Exception, total_inputs: int):
        super().__init__("export failure")
        self.source = source
        self.error = error
        self.total_inputs = total_inputs


class NoOutputProducedError(AudioProcessingError):
    """Raised when no files were produced despite successful processing."""


# ----------------------------------------------------------------------
# Environment Resolution
# ----------------------------------------------------------------------

def resolve_environment() -> None:
    """Verify that pydub and FFmpeg are available."""
    if AudioSegment is None:
        raise MissingDependencyError("pydub")

    converter_override = getattr(AudioSegment, "converter", None)
    bundled_converter_available = False

    if converter_override:
        try:
            converter_path = Path(converter_override)
        except TypeError:
            converter_path = None
        else:
            if converter_path.is_file():
                bundled_converter_available = True

    if bundled_converter_available:
        return

    if _find_executable is None:
        raise MissingEncoderError()

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
        raise MissingEncoderError()


# ----------------------------------------------------------------------
# Error Formatting
# ----------------------------------------------------------------------

def format_error_message(error: AudioProcessingError) -> str:
    """Format a user-friendly error message from an exception."""
    if isinstance(error, NoInputError):
        return "No audio files were selected."

    if isinstance(error, MissingInputFilesError):
        missing = error.missing
        if len(missing) == 1:
            return f"The file '{missing[0]}' could not be found."
        joined = ", ".join(str(path) for path in missing)
        return f"The following files are missing: {joined}"

    if isinstance(error, MissingDependencyError):
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

    if isinstance(error, MissingEncoderError):
        return (
            "Neither 'ffmpeg' nor 'avconv' could be located. Install FFmpeg and "
            "ensure it is discoverable via the PATH environment variable."
        )

    if isinstance(error, ExportFailureError):
        if error.total_inputs == 1:
            return str(error.error)
        return f"Could not process '{error.source.name}': {error.error}"

    if isinstance(error, NoOutputProducedError):
        return "None of the selected files could be processed."

    return str(error)


# ----------------------------------------------------------------------
# Validation Helpers
# ----------------------------------------------------------------------

def validate_input_paths(input_paths: list[Path]) -> None:
    """Validate that input paths exist and are accessible."""
    if not input_paths:
        raise NoInputError()

    missing_inputs = [path for path in input_paths if not path.exists()]
    if missing_inputs:
        raise MissingInputFilesError(missing_inputs)


def validate_pydub_available() -> None:
    """Validate that pydub is available."""
    if AudioSegment is None:
        assert _IMPORT_ERROR is not None
        missing_package = _IMPORT_ERROR.name or "pydub"
        raise MissingDependencyError(missing_package)
