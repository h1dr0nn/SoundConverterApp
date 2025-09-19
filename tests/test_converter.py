"""Tests for :mod:`app.converter`."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SPEC = importlib.util.spec_from_file_location("tests.converter", ROOT / "app" / "converter.py")
assert _SPEC and _SPEC.loader
converter = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = converter
_SPEC.loader.exec_module(converter)

ConversionRequest = converter.ConversionRequest
ConversionResult = converter.ConversionResult
SoundConverter = converter.SoundConverter


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_convert_reports_missing_selection(tmp_path) -> None:
    request = ConversionRequest(
        input_paths=(),
        output_directory=tmp_path,
        output_format="mp3",
    )

    result = SoundConverter.convert(request)

    assert isinstance(result, ConversionResult)
    assert not result.success
    assert result.outputs == ()
    assert result.message == "No audio files were selected."


def test_convert_reports_missing_files(tmp_path) -> None:
    missing_file = tmp_path / "missing.wav"
    request = ConversionRequest(
        input_paths=(missing_file,),
        output_directory=tmp_path,
        output_format="mp3",
    )

    result = SoundConverter.convert(request)

    assert not result.success
    assert result.message == f"The file '{missing_file}' could not be found."


def test_convert_reports_missing_dependency(monkeypatch, tmp_path) -> None:
    existing_file = _touch(tmp_path / "input.wav")
    request = ConversionRequest(
        input_paths=(existing_file,),
        output_directory=tmp_path,
        output_format="mp3",
    )

    monkeypatch.setattr(converter, "AudioSegment", None)
    monkeypatch.setattr(
        converter,
        "_IMPORT_ERROR",
        ModuleNotFoundError("No module named 'pydub'", name="pydub"),
    )

    result = SoundConverter.convert(request)

    assert not result.success
    assert (
        result.message
        == "The dependency 'pydub' is missing. Please install it with `pip install -r requirements.txt`."
    )


def test_convert_reports_missing_encoder(monkeypatch, tmp_path) -> None:
    existing_file = _touch(tmp_path / "input.wav")
    request = ConversionRequest(
        input_paths=(existing_file,),
        output_directory=tmp_path,
        output_format="mp3",
    )

    class DummyAudioSegment:
        converter = None

        @staticmethod
        def from_file(path: Path):  # pragma: no cover - not exercised in this test
            raise AssertionError("from_file should not be called")

    monkeypatch.setattr(converter, "AudioSegment", DummyAudioSegment)
    monkeypatch.setattr(converter, "_IMPORT_ERROR", None)
    monkeypatch.setattr(converter, "_find_executable", lambda candidate: None)

    result = SoundConverter.convert(request)

    assert not result.success
    assert (
        result.message
        == "Neither 'ffmpeg' nor 'avconv' could be located. Install FFmpeg and ensure it is discoverable via the PATH environment variable."
    )


def test_convert_success_returns_outputs(monkeypatch, tmp_path) -> None:
    input_file = _touch(tmp_path / "input.wav")
    output_directory = tmp_path / "exports"
    ffmpeg_binary = _touch(tmp_path / "ffmpeg")

    exported_paths: list[Path] = []

    class DummyAudio:
        def export(self, output_path: Path, format: str) -> None:  # pragma: no cover - exercised
            output_path.write_bytes(b"data")
            exported_paths.append(output_path)

    class DummyAudioSegment:
        converter = str(ffmpeg_binary)

        @staticmethod
        def from_file(path: Path) -> DummyAudio:
            assert path == input_file
            return DummyAudio()

    monkeypatch.setattr(converter, "AudioSegment", DummyAudioSegment)
    monkeypatch.setattr(converter, "_IMPORT_ERROR", None)
    monkeypatch.setattr(converter, "_find_executable", lambda candidate: None)

    request = ConversionRequest(
        input_paths=(input_file,),
        output_directory=output_directory,
        output_format="ogg",
    )

    result = SoundConverter.convert(request)

    assert result.success
    assert len(result.outputs) == 1
    assert result.outputs[0].exists()
    assert result.outputs[0] in exported_paths
    assert result.message == f"Saved file to {result.outputs[0]}"


def test_convert_reports_export_failure(monkeypatch, tmp_path) -> None:
    first_input = _touch(tmp_path / "first.wav")
    second_input = _touch(tmp_path / "second.wav")
    ffmpeg_binary = _touch(tmp_path / "ffmpeg")

    class DummyAudio:
        def export(self, output_path: Path, format: str) -> None:
            raise RuntimeError("boom")

    class DummyAudioSegment:
        converter = str(ffmpeg_binary)

        @staticmethod
        def from_file(path: Path) -> DummyAudio:
            return DummyAudio()

    monkeypatch.setattr(converter, "AudioSegment", DummyAudioSegment)
    monkeypatch.setattr(converter, "_IMPORT_ERROR", None)
    monkeypatch.setattr(converter, "_find_executable", lambda candidate: None)

    request = ConversionRequest(
        input_paths=(first_input, second_input),
        output_directory=tmp_path / "exports",
        output_format="mp3",
    )

    result = SoundConverter.convert(request)

    assert not result.success
    assert result.outputs == ()
    assert result.message == "Could not convert 'first.wav': boom"
