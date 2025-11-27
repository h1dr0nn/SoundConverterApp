"""Minimal backend entrypoint for Phase 1 foundation setup.

This module acts as the CLI entrypoint for the audio conversion backend.
It reads a JSON object from stdin, executes the conversion, and prints
JSON updates to stdout.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from app.handler.converter import SoundConverter, ConversionRequest
from app.handler.mastering import MasteringEngine, MasteringRequest, MasteringParameters
from app.handler.trimmer import SilenceTrimmer, TrimRequest
from utils import ensure_ffmpeg


def main() -> None:
    """Read JSON from stdin, run conversion, and print result."""
    
    # 1. Setup environment
    ensure_ffmpeg()

    # 2. Read input
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            # If no input, just print ready message (for health checks)
            print(json.dumps({"status": "ready", "message": "Backend ready"}))
            return

        data = json.loads(raw_input)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON input: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Input error: {e}"}))
        sys.exit(1)

    # 3. Determine operation type
    operation = data.get("operation", "convert")

    try:
        if operation == "convert":
            result = handle_conversion(data)
        elif operation == "master":
            result = handle_mastering(data)
        elif operation == "trim":
            result = handle_trimming(data)
        else:
            print(json.dumps({"status": "error", "message": f"Unknown operation: {operation}"}))
            sys.exit(1)

        print(json.dumps(result))
        
        if result["status"] != "success":
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"status": "fatal", "message": str(e), "traceback": traceback.format_exc()}))
        sys.exit(1)


def handle_conversion(data: dict) -> dict:
    """Handle audio conversion request."""
    input_paths = [Path(p) for p in data.get("input_paths", [])]
    output_directory = Path(data.get("output_directory", "."))
    output_format = data.get("output_format", "mp3")
    overwrite = data.get("overwrite_existing", True)

    request = ConversionRequest(
        input_paths=input_paths,
        output_directory=output_directory,
        output_format=output_format,
        overwrite_existing=overwrite
    )

    result = SoundConverter.convert(request)
    
    return {
        "status": "success" if result.success else "error",
        "message": result.message,
        "outputs": [str(p) for p in result.outputs]
    }


def handle_mastering(data: dict) -> dict:
    """Handle audio mastering request."""
    input_paths = [Path(p) for p in data.get("input_paths", [])]
    output_directory = Path(data.get("output_directory", "."))
    preset = data.get("preset", "Music")
    overwrite = data.get("overwrite_existing", True)
    
    # Parse parameters if provided
    params_data = data.get("parameters", {})
    parameters = MasteringParameters(
        target_lufs=params_data.get("target_lufs", -14.0),
        apply_compression=params_data.get("apply_compression", True),
        apply_limiter=params_data.get("apply_limiter", True),
        output_gain=params_data.get("output_gain", 0.0)
    )

    request = MasteringRequest(
        input_paths=input_paths,
        output_directory=output_directory,
        preset=preset,
        parameters=parameters,
        overwrite_existing=overwrite
    )

    result = MasteringEngine.process(request)
    
    return {
        "status": "success" if result.success else "error",
        "message": result.message,
        "outputs": [str(p) for p in result.outputs]
    }


def handle_trimming(data: dict) -> dict:
    """Handle silence trimming request."""
    input_paths = [Path(p) for p in data.get("input_paths", [])]
    output_directory = Path(data.get("output_directory", "."))
    silence_threshold = data.get("silence_threshold", -50.0)
    minimum_silence_ms = data.get("minimum_silence_ms", 500)
    padding_ms = data.get("padding_ms", 0)
    overwrite = data.get("overwrite_existing", True)

    request = TrimRequest(
        input_paths=input_paths,
        output_directory=output_directory,
        silence_threshold=silence_threshold,
        minimum_silence_ms=minimum_silence_ms,
        padding_ms=padding_ms,
        overwrite_existing=overwrite
    )

    result = SilenceTrimmer.process(request)
    
    return {
        "status": "success" if result.success else "error",
        "message": result.message,
        "outputs": [str(p) for p in result.outputs]
    }


if __name__ == "__main__":
    main()
