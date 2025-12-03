"""Basic audio conversion example.

This script demonstrates how to use the Harmonix SE backend modules
programmatically to convert a single audio file.
"""

import sys
import os
from pathlib import Path

# Add backend to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.handler.converter import SoundConverter, ConversionRequest
from app.config.settings import AudioSettings
from app.validators.audio_validator import validate_audio_file
from utils import ensure_ffmpeg, log_message

def main():
    # 1. Setup
    print("Initializing Harmonix SE Converter...")
    ffmpeg_path = ensure_ffmpeg()
    if not ffmpeg_path:
        print("Error: FFmpeg not found!")
        return

    # 2. Define input/output
    input_file = Path("samples/input.wav")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Create dummy input if not exists
    if not input_file.exists():
        print(f"Input file {input_file} not found. Please provide a valid file.")
        return

    # 3. Validate input
    is_valid, error = validate_audio_file(input_file)
    if not is_valid:
        print(f"Validation failed: {error}")
        return

    # 4. Configure conversion
    request = ConversionRequest(
        input_paths=[input_file],
        output_directory=output_dir,
        output_format="mp3",
        ffmpeg_path=ffmpeg_path
    )

    # 5. Process
    print(f"Converting {input_file.name} to MP3...")
    
    try:
        result = SoundConverter.convert(request)
        if result.success:
            print(f"Success! Output files: {result.outputs}")
        else:
            print(f"Failed: {result.message}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
