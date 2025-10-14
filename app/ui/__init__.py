"""User interface widgets for the Sound Converter application."""

from .convert_tab import AUDIO_SUFFIXES, ConvertTab
from .mastering_tab import MasteringTab
from .settings_tab import SettingsTab
from .trim_tab import TrimTab

__all__ = [
    "AUDIO_SUFFIXES",
    "ConvertTab",
    "MasteringTab",
    "SettingsTab",
    "TrimTab",
]
