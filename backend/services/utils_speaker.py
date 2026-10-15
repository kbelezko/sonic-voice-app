"""
Audio speaker utilities for playing PCM audio on macOS

Provides async functions for:
- Playing PCM audio to the default audio output device
- Managing audio playback queue
- Handling audio device initialization
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Check for audio playback library
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not available - audio playback disabled")


class AudioSpeaker:
    """
    Manages audio playback to the default speaker/output device
    
    Supports asynchronous playback of PCM audio data with configurable
    sample rate, channels, and bit depth.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2  # 2 bytes = 16-bit
    ):
        """
        Initialize the audio speaker
        
        Args:
            sample_rate: Sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            sample_width: Sample width in bytes (default: 2 for 16-bit)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.audio = None
        self.stream = None
        self.is_open = False
        self.playback_queue = asyncio.Queue()
        self.playback_task = None
        
        if not PYAUDIO_AVAILABLE:
            logger.error("Cannot initialize AudioSpeaker: pyaudio not available")
            raise RuntimeError(
                "pyaudio is required for audio playback. "
                "Install with: pip install pyaudio"
            )
    
    def open(self):
        """Open the audio output stream"""
        if self.is_open:
            logger.warning("AudioSpeaker already open")
            return
        
        try:
            self.audio = pyaudio.PyAudio()
            
            # Open audio output stream
            self.stream = self.audio.open(
                format=self.audio.get_format_from_width(self.sample_width),
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024
            )
            
            self.is_open = True
            logger.info(
                f"Audio speaker opened: {self.sample_rate}Hz, "
                f"{self.channels}ch, {self.sample_width*8}-bit"
            )
            
        except Exception as e:
            logger.error(f"Failed to open audio speaker: {e}", exc_info=True)
            raise
    
    def close(self):
        """Close the audio output stream"""
        if not self.is_open:
            return
        
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.audio:
                self.audio.terminate()
                self.audio = None
            
            self.is_open = False
            logger.info("Audio speaker closed")
            
        except Exception as e:
            logger.error(f"Error closing audio speaker: {e}", exc_info=True)
    
    def play_sync(self, pcm_bytes: bytes):
        """
        Play PCM audio synchronously (blocking)
        
        Args:
            pcm_bytes: Raw PCM audio bytes
        """
        if not self.is_open:
            raise RuntimeError("AudioSpeaker not open. Call open() first.")
        
        try:
            self.stream.write(pcm_bytes)
            logger.debug(f"Played {len(pcm_bytes)} bytes")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}", exc_info=True)
            raise
    
    async def play(self, pcm_bytes: bytes):
        """
        Play PCM audio asynchronously (non-blocking)
        
        Args:
            pcm_bytes: Raw PCM audio bytes
        """
        await self.playback_queue.put(pcm_bytes)
    
    async def _playback_worker(self):
        """Background worker that processes the playback queue"""
        logger.info("Audio playback worker started")
        
        try:
            while True:
                pcm_bytes = await self.playback_queue.get()
                
                if pcm_bytes is None:
                    # Sentinel value to stop the worker
                    break
                
                try:
                    # Run blocking I/O in executor to avoid blocking event loop
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.play_sync,
                        pcm_bytes
                    )
                except Exception as e:
                    logger.error(f"Error in playback worker: {e}")
                
        except asyncio.CancelledError:
            logger.info("Audio playback worker cancelled")
        except Exception as e:
            logger.error(f"Fatal error in playback worker: {e}", exc_info=True)
        finally:
            logger.info("Audio playback worker stopped")
    
    def start_playback_worker(self):
        """Start the background playback worker"""
        if self.playback_task and not self.playback_task.done():
            logger.warning("Playback worker already running")
            return
        
        if not self.is_open:
            raise RuntimeError("AudioSpeaker not open. Call open() first.")
        
        self.playback_task = asyncio.create_task(self._playback_worker())
        logger.info("Audio playback worker started")
    
    async def stop_playback_worker(self):
        """Stop the background playback worker"""
        if not self.playback_task or self.playback_task.done():
            return
        
        # Send sentinel to stop worker
        await self.playback_queue.put(None)
        
        try:
            await self.playback_task
        except asyncio.CancelledError:
            pass
        
        self.playback_task = None
        logger.info("Audio playback worker stopped")
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Global speaker instance for simple usage
_speaker: Optional[AudioSpeaker] = None


def get_speaker(
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2
) -> AudioSpeaker:
    """
    Get or create a global AudioSpeaker instance
    
    Args:
        sample_rate: Sample rate in Hz
        channels: Number of channels
        sample_width: Sample width in bytes
        
    Returns:
        AudioSpeaker instance
    """
    global _speaker
    
    if _speaker is None:
        _speaker = AudioSpeaker(sample_rate, channels, sample_width)
        _speaker.open()
        _speaker.start_playback_worker()
    
    return _speaker


async def play_audio(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2
):
    """
    Play PCM audio asynchronously using the global speaker
    
    Args:
        pcm_bytes: Raw PCM audio bytes
        sample_rate: Sample rate in Hz
        channels: Number of channels
        sample_width: Sample width in bytes
    """
    speaker = get_speaker(sample_rate, channels, sample_width)
    await speaker.play(pcm_bytes)


async def play_wav_file(filepath: str):
    """
    Play a WAV file asynchronously
    
    Args:
        filepath: Path to WAV file
    """
    from .utils_audio import load_wav_file
    
    # Load WAV file
    pcm_bytes, metadata = load_wav_file(filepath)
    
    logger.info(
        f"Playing WAV: {metadata['sample_rate']}Hz, "
        f"{metadata['channels']}ch, {metadata['duration_seconds']:.2f}s"
    )
    
    # Play audio
    await play_audio(
        pcm_bytes,
        sample_rate=metadata['sample_rate'],
        channels=metadata['channels'],
        sample_width=metadata['sample_width']
    )


def cleanup_speaker():
    """Cleanup the global speaker instance"""
    global _speaker
    
    if _speaker:
        _speaker.close()
        _speaker = None


def check_audio_playback_available() -> bool:
    """
    Check if audio playback is available
    
    Returns:
        True if pyaudio is available and can initialize
    """
    return PYAUDIO_AVAILABLE
