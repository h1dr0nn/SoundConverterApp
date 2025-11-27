"""Converter package for audio processing."""

from __future__ import annotations

from .handler.converter import ConversionRequest, ConversionResult, SoundConverter
from .handler.mastering import (
    MasteringEngine,
    MasteringParameters,
    MasteringRequest,
    MasteringResult,
)
from .handler.trimmer import SilenceTrimmer, TrimRequest, TrimResult

__all__ = [
    "SoundConverter",
    "ConversionRequest",
    "ConversionResult",
    "MasteringEngine",
    "MasteringRequest",
    "MasteringResult",
    "MasteringParameters",
    "SilenceTrimmer",
    "TrimRequest",
    "TrimResult",
]
