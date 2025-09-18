from pydub import AudioSegment

class SoundConverter:
    @staticmethod
    def convert(input_path: str, output_path: str, format: str):
        """Convert audio file sang format khác"""
        try:
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=format)
            return True, f"Saved to {output_path}"
        except Exception as e:
            return False, str(e)
