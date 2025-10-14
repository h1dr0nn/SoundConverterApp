"""Application bootstrap helpers for the Sound Converter GUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple

from PySide6.QtWidgets import QApplication

from .converter import SoundConverter
from .mastering import MasteringEngine
from .trimmer import SilenceTrimmer
from .ui_main import MainWindow


def ensure_ffmpeg() -> None:
    """Ensure the bundled FFmpeg binaries are discoverable at runtime."""

    try:
        from pydub import AudioSegment  # type: ignore
    except ModuleNotFoundError:
        # ``pydub`` is optional at startup; conversion will report a clearer
        # error message if the dependency is missing.
        return

    runtime_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if hasattr(sys, "_MEIPASS"):
        binary_dir = runtime_root / "app" / "resources" / "bin"
    else:
        binary_dir = runtime_root / "resources" / "bin"

    if not binary_dir.is_dir():
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


def create_application() -> Tuple[QApplication, MainWindow]:
    """Instantiate the Qt application and main window."""

    ensure_ffmpeg()
    app = QApplication(sys.argv)
    window = MainWindow(SoundConverter(), MasteringEngine(), SilenceTrimmer())
    return app, window


def run() -> int:
    """Create the application and start the Qt event loop."""

    app, window = create_application()
    window.show()
    return app.exec()


__all__ = ["create_application", "ensure_ffmpeg", "run"]
