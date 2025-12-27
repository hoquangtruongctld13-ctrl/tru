"""
VN TTS - Vietnamese Text-to-Speech Module
=========================================

This module provides Vietnamese TTS capabilities using the VieNeu-TTS engine.
"""

from .vieneu_tts import VieNeuTTS, FastVieNeuTTS

__all__ = ["VieNeuTTS", "FastVieNeuTTS"]
__version__ = "0.1.0"
