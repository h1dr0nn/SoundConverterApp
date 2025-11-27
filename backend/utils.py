"""Utility helpers for backend workflows."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _candidate_directories() -> list[Path]:
    """Return possible locations for the bundled FFmpeg binary."""

    env_bin_dir = os.environ.get("SOUNDCONVERTER_BIN_DIR")
    env_candidates = []
    if env_bin_dir:
        env_path = Path(env_bin_dir)
        env_candidates.extend([env_path, env_path / "ffmpeg", env_path / "bin"])

    if hasattr(sys, "_MEIPASS"):
        runtime_root = Path(getattr(sys, "_MEIPASS"))
        return env_candidates + [
            runtime_root / "src-tauri" / "bin" / "ffmpeg",
            runtime_root / "src-tauri" / "bin",
            runtime_root / "backend" / "resources" / "bin",
            runtime_root / "resources" / "bin",
            runtime_root / "bin",
        ]

    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    return env_candidates + [
        project_root / "src-tauri" / "binaries",  # New binaries location
        project_root / "src-tauri" / "bin" / "ffmpeg",
        project_root / "src-tauri" / "bin",
        current_dir / "resources" / "bin",
        current_dir.parent / "resources" / "bin",
    ]


def ensure_ffmpeg() -> Optional[Path]:
    """Ensure the bundled FFmpeg binaries are discoverable at runtime.

    Returns
    -------
    Optional[Path]
        The resolved FFmpeg binary path if found.
    """
    
    # First priority: Check FFMPEG_BINARY environment variable
    ffmpeg_binary_env = os.environ.get("FFMPEG_BINARY")
    if ffmpeg_binary_env:
        ffmpeg_path = Path(ffmpeg_binary_env)
        if ffmpeg_path.is_file() and ffmpeg_path.exists():
            log_message("python", f"Using FFmpeg from FFMPEG_BINARY: {ffmpeg_path}")
            try:
                from pydub import AudioSegment  # type: ignore
                AudioSegment.converter = str(ffmpeg_path)
            except ModuleNotFoundError:
                pass
            return ffmpeg_path

    try:
        from pydub import AudioSegment  # type: ignore
    except ModuleNotFoundError:
        # ``pydub`` is optional at startup; conversion will report a clearer
        # error message if the dependency is missing.
        return

    candidate_dirs = _candidate_directories()
    binary_dir = next((d for d in candidate_dirs if d.is_dir()), None)

    if not binary_dir:
        return None

    candidates = [
        binary_dir / "ffmpeg.exe",
        binary_dir / "ffmpeg",
        binary_dir / "ffmpeg-aarch64-apple-darwin",  # macOS ARM64
        binary_dir / "ffmpeg-x86_64-apple-darwin",     # macOS Intel
        binary_dir / "ffmpeg-x86_64-pc-windows-msvc.exe",  # Windows
        binary_dir / "avconv",
    ]
    binary_path = next((path for path in candidates if path.is_file()), None)
    if binary_path is None:
        return None

    path_entries = os.environ.get("PATH", "").split(os.pathsep) if os.environ.get("PATH") else []
    binary_dir_str = str(binary_dir)
    if binary_dir_str not in path_entries:
        path_entries.insert(0, binary_dir_str)
        os.environ["PATH"] = os.pathsep.join(path_entries) if path_entries else binary_dir_str

    AudioSegment.converter = str(binary_path)
    return binary_path


def log_message(scope: str, message: str) -> None:
    """Emit structured log messages to stderr."""

    from datetime import datetime

    timestamp = f"{datetime.utcnow().isoformat()}Z"
    print(f"[{scope}] [{timestamp}] {message}", file=sys.stderr, flush=True)
