"""Utility helpers for backend workflows."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_ffmpeg() -> None:
    """Ensure the bundled FFmpeg binaries are discoverable at runtime."""

    try:
        from pydub import AudioSegment  # type: ignore
    except ModuleNotFoundError:
        # ``pydub`` is optional at startup; conversion will report a clearer
        # error message if the dependency is missing.
        return

    # Determine the runtime root.
    # If frozen with PyInstaller, _MEIPASS is the temp dir.
    # If running from source, we look in backend/resources/bin
    
    if hasattr(sys, "_MEIPASS"):
        runtime_root = Path(getattr(sys, "_MEIPASS"))
        candidates_dirs = [
            runtime_root / "backend" / "resources" / "bin",
            runtime_root / "resources" / "bin",
            runtime_root / "bin",
        ]
    else:
        # Running from source: backend/utils.py -> backend/ -> backend/resources/bin
        current_dir = Path(__file__).resolve().parent
        candidates_dirs = [
            current_dir / "resources" / "bin",
            current_dir.parent / "resources" / "bin",
        ]

    binary_dir = next((d for d in candidates_dirs if d.is_dir()), None)

    if not binary_dir:
        return

    candidates = [
        binary_dir / "ffmpeg.exe",
        binary_dir / "ffmpeg",
        binary_dir / "avconv",
    ]
    binary_path = next((path for path in candidates if path.is_file()), None)
    if binary_path is None:
        return

    path_entries = os.environ.get("PATH", "").split(os.pathsep) if os.environ.get("PATH") else []
    binary_dir_str = str(binary_dir)
    if binary_dir_str not in path_entries:
        path_entries.insert(0, binary_dir_str)
        os.environ["PATH"] = os.pathsep.join(path_entries) if path_entries else binary_dir_str

    AudioSegment.converter = str(binary_path)
