"""Tests for mastering request handling."""

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

_SPEC = importlib.util.spec_from_file_location(
    "tests.mastering", ROOT / "app" / "mastering.py"
)
assert _SPEC and _SPEC.loader
mastering = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mastering
_SPEC.loader.exec_module(mastering)

MasteringParameters = mastering.MasteringParameters
MasteringRequest = mastering.MasteringRequest


def _create_source(tmp_path: Path, name: str = "song.wav") -> Path:
    source = tmp_path / name
    source.write_bytes(b"")
    return source


def test_mastering_request_uses_default_suffix(tmp_path):
    source = _create_source(tmp_path)

    request = MasteringRequest(
        input_paths=(source,),
        output_directory=tmp_path,
        preset="Music",
        parameters=MasteringParameters(),
    )

    outputs = list(request.outputs())

    assert outputs[0][1].name == "song_mastered.wav"


def test_mastering_request_respects_custom_suffix(tmp_path):
    source = _create_source(tmp_path)

    request = MasteringRequest(
        input_paths=(source,),
        output_directory=tmp_path,
        preset="Music",
        parameters=MasteringParameters(),
        filename_suffix="_final",
    )

    outputs = list(request.outputs())

    assert outputs[0][1].name == "song_final.wav"


def test_mastering_request_allows_empty_suffix(tmp_path):
    source = _create_source(tmp_path)

    request = MasteringRequest(
        input_paths=(source,),
        output_directory=tmp_path,
        preset="Music",
        parameters=MasteringParameters(),
        filename_suffix="   ",
    )

    outputs = list(request.outputs())

    assert outputs[0][1].name == "song.wav"
