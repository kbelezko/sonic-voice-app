"""
Audio processing utilities - DEPRECATED

All functionality has been moved to services/utils_audio.py for better organization.
This file is kept for backwards compatibility and will be removed in a future version.

Use services.utils_audio instead:
    from services.utils_audio import resample_audio, webm_to_pcm, pcm_to_wav_bytes, etc.
"""

import logging
from typing import Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Import all functions from utils_audio
from .utils_audio import (
    resample_audio,
    simple_resample,
    webm_to_pcm,
    pcm_to_wav_bytes,
    normalize_audio,
    check_audio_dependencies
)


class AudioProcessor:
    """
    Audio format conversion and resampling utilities
    
    DEPRECATED: Use functions from utils_audio directly instead.
    This class is kept for backwards compatibility.
    """
    
    @staticmethod
    def resample_audio(
        audio_data: np.ndarray,
        original_rate: int,
        target_rate: int
    ) -> np.ndarray:
        """
        Resample audio to a different sample rate
        
        DEPRECATED: Use services.utils_audio.resample_audio() directly
        """
        logger.warning(
            "AudioProcessor.resample_audio() is deprecated. "
            "Use services.utils_audio.resample_audio() directly."
        )
        return resample_audio(audio_data, original_rate, target_rate)
    
    @staticmethod
    def webm_to_pcm(
        webm_data: bytes,
        target_sample_rate: int = 16000
    ) -> Tuple[bytes, int]:
        """
        Convert WebM audio to PCM format
        
        DEPRECATED: Use services.utils_audio.webm_to_pcm() directly
        """
        logger.warning(
            "AudioProcessor.webm_to_pcm() is deprecated. "
            "Use services.utils_audio.webm_to_pcm() directly."
        )
        return webm_to_pcm(webm_data, target_sample_rate)
    
    @staticmethod
    def pcm_to_wav(
        pcm_data: bytes,
        sample_rate: int,
        channels: int = 1,
        sample_width: int = 2
    ) -> bytes:
        """
        Convert raw PCM to WAV format (for browser playback)
        
        DEPRECATED: Use services.utils_audio.pcm_to_wav_bytes() directly
        """
        logger.warning(
            "AudioProcessor.pcm_to_wav() is deprecated. "
            "Use services.utils_audio.pcm_to_wav_bytes() directly."
        )
        return pcm_to_wav_bytes(pcm_data, sample_rate, channels, sample_width)
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray, target_level: float = 0.9) -> np.ndarray:
        """
        Normalize audio to target level
        
        DEPRECATED: Use services.utils_audio.normalize_audio() directly
        """
        logger.warning(
            "AudioProcessor.normalize_audio() is deprecated. "
            "Use services.utils_audio.normalize_audio() directly."
        )
        return normalize_audio(audio_data, target_level)
    
    @staticmethod
    def check_dependencies() -> dict:
        """
        Check which audio processing libraries are available
        
        DEPRECATED: Use services.utils_audio.check_audio_dependencies() directly
        """
        logger.warning(
            "AudioProcessor.check_dependencies() is deprecated. "
            "Use services.utils_audio.check_audio_dependencies() directly."
        )
        return check_audio_dependencies()
