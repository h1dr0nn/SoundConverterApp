"""Business logic layer responsible for audio mastering."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

try:  # pragma: no cover - exercised through integration
    from pydub import AudioSegment, effects  # type: ignore
    from pydub.utils import which as _find_executable  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled gracefully
    AudioSegment = None  # type: ignore[assignment]
    effects = None  # type: ignore[assignment]
    _find_executable = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


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
        """Yield tuples of ``(input_path, output_path)`` for the batch."""

        allocated: Set[Path] = set()

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
    """Outcome returned by :meth:`MasteringEngine.process`."""

    success: bool
    message: str
    outputs: Tuple[Path, ...] = ()


class _MasteringError(RuntimeError):
    """Base class for internal mastering errors."""


class _NoInputError(_MasteringError):
    """Raised when the request does not contain any files."""


class _MissingInputFilesError(_MasteringError):
    """Raised when one or more selected files are not available."""

    def __init__(self, missing: Sequence[Path]):
        super().__init__("missing input files")
        self.missing = tuple(missing)


class _MissingDependencyError(_MasteringError):
    """Raised when ``pydub`` or FFmpeg are not available."""

    def __init__(self, package: str):
        super().__init__(f"missing dependency: {package}")
        self.package = package


class _MissingEncoderError(_MasteringError):
    """Raised when neither FFmpeg nor avconv can be located."""


class _ExportFailureError(_MasteringError):
    """Raised when exporting a mastered file fails."""

    def __init__(self, source: Path, error: Exception, total_inputs: int):
        super().__init__("export failure")
        self.source = source
        self.error = error
        self.total_inputs = total_inputs


class _NoOutputProducedError(_MasteringError):
    """Raised when no files were produced despite processing input."""


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
    def presets(cls) -> Dict[str, MasteringParameters]:
        """Return a copy of the bundled mastering presets."""

        return dict(cls.PRESETS)

    @classmethod
    def available_presets(cls) -> Iterable[str]:
        """Return the names of available presets."""

        return tuple(cls.PRESETS.keys())

    @classmethod
    def default_preset(cls) -> str:
        """Return the default preset name."""

        return next(iter(cls.PRESETS)) if cls.PRESETS else "Music"

    @classmethod
    def parameters_for_preset(cls, preset: str) -> MasteringParameters:
        """Return the parameters configured for the given preset."""

        if preset in cls.PRESETS:
            return cls.PRESETS[preset]
        default = cls.default_preset()
        return cls.PRESETS.get(default, MasteringParameters())

    @classmethod
    def process(cls, request: MasteringRequest) -> MasteringResult:
        """Run the mastering workflow and return a structured result."""

        try:
            cls._validate_request(request)
            cls._resolve_environment()
            outputs = cls._process_batch(request)
            if not outputs:
                raise _NoOutputProducedError()
        except _MasteringError as error:
            message = cls._format_error_message(error)
            return MasteringResult(False, message, ())

        message = cls._format_success_message(request, outputs)
        return MasteringResult(True, message, outputs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _validate_request(cls, request: MasteringRequest) -> None:
        if not request.input_paths:
            raise _NoInputError()

        missing_inputs = [path for path in request.input_paths if not path.exists()]
        if missing_inputs:
            raise _MissingInputFilesError(missing_inputs)

        if AudioSegment is None:
            assert _IMPORT_ERROR is not None  # for type checkers
            package = _IMPORT_ERROR.name or "pydub"
            raise _MissingDependencyError(package)

    @classmethod
    def _resolve_environment(cls) -> None:
        if AudioSegment is None:
            raise _MissingDependencyError("pydub")

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
    def _process_batch(cls, request: MasteringRequest) -> Tuple[Path, ...]:
        assert AudioSegment is not None  # for type checkers

        mastered: List[Path] = []
        request.output_directory.mkdir(parents=True, exist_ok=True)

        for source, destination in request.outputs():
            try:
                audio = AudioSegment.from_file(source)
                processed = cls._apply_parameters(audio, request.parameters)
                export_format = destination.suffix[1:] if destination.suffix else "wav"
                processed.export(destination, format=export_format)
            except Exception as exc:  # pragma: no cover - thin wrapper
                raise _ExportFailureError(source, exc, len(request.input_paths))
            mastered.append(destination)

        return tuple(mastered)

    @staticmethod
    def _apply_parameters(
        audio: "AudioSegment", parameters: MasteringParameters
    ) -> "AudioSegment":
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
    def _format_success_message(
        request: MasteringRequest, outputs: Sequence[Path]
    ) -> str:
        preset_name = request.preset
        if len(outputs) == 1:
            return (
                f"'{outputs[0].name}' mastered successfully using the '{preset_name}' preset."
            )
        return (
            f"{len(outputs)} files mastered successfully using the '{preset_name}' preset."
        )

    @staticmethod
    def _format_error_message(error: _MasteringError) -> str:
        if isinstance(error, _NoInputError):
            return "Please select at least one audio file to master."
        if isinstance(error, _MissingInputFilesError):
            missing = ", ".join(path.name for path in error.missing)
            return f"These files could not be found: {missing}"
        if isinstance(error, _MissingDependencyError):
            return (
                f"Missing dependency: {error.package}. Install it to enable automatic mastering."
            )
        if isinstance(error, _MissingEncoderError):
            return "FFmpeg or avconv could not be located. Please install FFmpeg."
        if isinstance(error, _ExportFailureError):
            details = str(error.error)
            if error.total_inputs == 1:
                return (
                    f"Could not export '{error.source.name}': {details}"
                )
            return (
                f"Processing stopped while exporting '{error.source.name}': {details}"
            )
        if isinstance(error, _NoOutputProducedError):
            return "No mastered files were produced."
        return str(error)


__all__ = [
    "MasteringEngine",
    "MasteringParameters",
    "MasteringRequest",
    "MasteringResult",
]
