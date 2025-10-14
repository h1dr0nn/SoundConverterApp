import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]

_SPEC = importlib.util.spec_from_file_location(
    "tests.trimmer", ROOT / "app" / "trimmer.py"
)
assert _SPEC and _SPEC.loader
trimmer = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = trimmer
_SPEC.loader.exec_module(trimmer)

TrimRequest = trimmer.TrimRequest
TrimResult = trimmer.TrimResult
SilenceTrimmer = trimmer.SilenceTrimmer


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_trim_reports_missing_selection(tmp_path) -> None:
    request = TrimRequest(
        input_paths=(),
        output_directory=tmp_path,
    )

    result = SilenceTrimmer.process(request)

    assert isinstance(result, TrimResult)
    assert not result.success
    assert result.outputs == ()
    assert result.message == "No audio files were selected."


def test_trim_reports_missing_files(tmp_path) -> None:
    missing_file = tmp_path / "missing.wav"
    request = TrimRequest(
        input_paths=(missing_file,),
        output_directory=tmp_path,
    )

    result = SilenceTrimmer.process(request)

    assert not result.success
    assert result.message == f"The file '{missing_file}' could not be found."


def test_trim_reports_missing_dependency(monkeypatch, tmp_path) -> None:
    existing_file = _touch(tmp_path / "input.wav")
    request = TrimRequest(
        input_paths=(existing_file,),
        output_directory=tmp_path,
    )

    monkeypatch.setattr(trimmer, "AudioSegment", None)
    monkeypatch.setattr(trimmer, "silence", None)
    monkeypatch.setattr(
        trimmer,
        "_IMPORT_ERROR",
        ModuleNotFoundError("No module named 'pydub'", name="pydub"),
    )

    result = SilenceTrimmer.process(request)

    assert not result.success
    assert (
        result.message
        == "The dependency 'pydub' is missing. Please install it with `pip install -r requirements.txt`."
    )


def test_trim_reports_missing_encoder(monkeypatch, tmp_path) -> None:
    existing_file = _touch(tmp_path / "input.wav")
    request = TrimRequest(
        input_paths=(existing_file,),
        output_directory=tmp_path,
    )

    class DummyAudioSegment:
        converter = None

        @staticmethod
        def from_file(path: Path):  # pragma: no cover - not exercised
            raise AssertionError("from_file should not be called")

    monkeypatch.setattr(trimmer, "AudioSegment", DummyAudioSegment)
    monkeypatch.setattr(trimmer, "silence", SimpleNamespace(detect_nonsilent=lambda *_, **__: []))
    monkeypatch.setattr(trimmer, "_IMPORT_ERROR", None)
    monkeypatch.setattr(trimmer, "_find_executable", lambda candidate: None)

    result = SilenceTrimmer.process(request)

    assert not result.success
    assert (
        result.message
        == "Neither 'ffmpeg' nor 'avconv' could be located. Install FFmpeg and ensure it is discoverable via the PATH environment variable."
    )


def test_trim_success_returns_outputs(monkeypatch, tmp_path) -> None:
    input_file = _touch(tmp_path / "input.wav")
    output_directory = tmp_path / "trimmed"
    ffmpeg_binary = _touch(tmp_path / "ffmpeg")

    class DummyAudio:
        def export(self, output_path: Path, format: str) -> None:  # pragma: no cover - exercised
            output_path.write_bytes(b"data")

        def __len__(self) -> int:  # pragma: no cover - exercised
            return 2000

        def __getitem__(self, key):  # pragma: no cover - exercised
            return self

    class DummyAudioSegment:
        converter = str(ffmpeg_binary)

        @staticmethod
        def from_file(path: Path) -> DummyAudio:
            assert path == input_file
            return DummyAudio()

    def _detect_nonsilent(audio, **_):  # pragma: no cover - exercised
        return [(100, 1900)]

    monkeypatch.setattr(trimmer, "AudioSegment", DummyAudioSegment)
    monkeypatch.setattr(trimmer, "silence", SimpleNamespace(detect_nonsilent=_detect_nonsilent))
    monkeypatch.setattr(trimmer, "_IMPORT_ERROR", None)
    monkeypatch.setattr(trimmer, "_find_executable", lambda candidate: None)

    request = TrimRequest(
        input_paths=(input_file,),
        output_directory=output_directory,
        silence_threshold=-40.0,
        minimum_silence_ms=300,
        padding_ms=50,
    )

    result = SilenceTrimmer.process(request)

    assert result.success
    assert len(result.outputs) == 1
    assert result.outputs[0].exists()
    assert result.message == f"Saved trimmed file to {result.outputs[0]}"


def test_trim_reports_export_failure(monkeypatch, tmp_path) -> None:
    first_input = _touch(tmp_path / "first.wav")
    second_input = _touch(tmp_path / "second.wav")
    ffmpeg_binary = _touch(tmp_path / "ffmpeg")

    class DummyAudio:
        def export(self, output_path: Path, format: str) -> None:
            raise RuntimeError("boom")

        def __len__(self) -> int:  # pragma: no cover - exercised
            return 1000

        def __getitem__(self, key):  # pragma: no cover - exercised
            return self

    class DummyAudioSegment:
        converter = str(ffmpeg_binary)

        @staticmethod
        def from_file(path: Path) -> DummyAudio:
            return DummyAudio()

    monkeypatch.setattr(trimmer, "AudioSegment", DummyAudioSegment)
    monkeypatch.setattr(trimmer, "silence", SimpleNamespace(detect_nonsilent=lambda *_, **__: [(0, 1000)]))
    monkeypatch.setattr(trimmer, "_IMPORT_ERROR", None)
    monkeypatch.setattr(trimmer, "_find_executable", lambda candidate: None)

    request = TrimRequest(
        input_paths=(first_input, second_input),
        output_directory=tmp_path / "exports",
    )

    result = SilenceTrimmer.process(request)

    assert not result.success
    assert result.outputs == ()
    assert result.message == "Could not trim 'first.wav': boom"

