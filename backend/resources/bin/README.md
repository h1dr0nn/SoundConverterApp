# FFmpeg binaries

Place platform-specific FFmpeg executables in this directory when running the
application from source. During packaged execution (PyInstaller), the
``ensure_ffmpeg`` helper will automatically add this directory to ``PATH`` and
configure ``pydub`` to use the bundled binary.

Expected file names include:

- `ffmpeg` (Linux/macOS)
- `ffmpeg.exe` (Windows)

You may also provide other compatible encoder binaries such as `avconv`.
