"""
Audio utility functions for WAV file manipulation and PCM processing

Provides functions for:
- Loading and validating WAV files
- Converting between audio formats
- Chunking audio data for streaming
- PCM validation and processing
- Audio resampling and format conversion
"""

import wave
import base64
import logging
import io
from typing import Tuple, List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy not available - audio resampling limited")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available - audio format conversion limited")

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available - audio resampling limited")


class AudioFormat:
    """Audio format constants"""
    SAMPLE_RATE_16KHZ = 16000
    SAMPLE_RATE_24KHZ = 24000
    SAMPLE_RATE_48KHZ = 48000
    
    CHANNELS_MONO = 1
    CHANNELS_STEREO = 2
    
    SAMPLE_WIDTH_16BIT = 2  # bytes


def load_wav_file(filepath: str) -> Tuple[bytes, Dict[str, Any]]:
    """
    Load a WAV file and return raw PCM data with metadata
    
    Args:
        filepath: Path to WAV file
        
    Returns:
        Tuple of (pcm_bytes, metadata_dict)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a valid WAV
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"WAV file not found: {filepath}")
    
    with wave.open(str(filepath), 'rb') as wav_file:
        # Get WAV parameters
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        # Read raw PCM data
        pcm_bytes = wav_file.readframes(n_frames)
        
        metadata = {
            'channels': channels,
            'sample_width': sample_width,
            'sample_width_bits': sample_width * 8,
            'sample_rate': sample_rate,
            'n_frames': n_frames,
            'duration_seconds': n_frames / sample_rate if sample_rate > 0 else 0,
            'total_bytes': len(pcm_bytes)
        }
        
        logger.info(
            f"Loaded WAV: {sample_rate}Hz, {channels}ch, "
            f"{sample_width*8}bit, {metadata['duration_seconds']:.2f}s"
        )
        
        return pcm_bytes, metadata


def validate_audio_format(
    metadata: Dict[str, Any],
    expected_rate: int = AudioFormat.SAMPLE_RATE_16KHZ,
    expected_channels: int = AudioFormat.CHANNELS_MONO,
    expected_width: int = AudioFormat.SAMPLE_WIDTH_16BIT
) -> List[str]:
    """
    Validate audio format against expected parameters
    
    Args:
        metadata: Audio metadata dict from load_wav_file
        expected_rate: Expected sample rate in Hz
        expected_channels: Expected number of channels
        expected_width: Expected sample width in bytes
        
    Returns:
        List of warning messages (empty if all valid)
    """
    warnings = []
    
    if metadata['sample_rate'] != expected_rate:
        warnings.append(
            f"Sample rate is {metadata['sample_rate']}Hz, expected {expected_rate}Hz"
        )
    
    if metadata['channels'] != expected_channels:
        channel_name = "mono" if expected_channels == 1 else "stereo"
        warnings.append(
            f"Channels is {metadata['channels']}, expected {expected_channels} ({channel_name})"
        )
    
    if metadata['sample_width'] != expected_width:
        warnings.append(
            f"Sample width is {metadata['sample_width']} bytes, "
            f"expected {expected_width} ({expected_width*8}-bit)"
        )
    
    return warnings


def chunk_audio(
    pcm_bytes: bytes,
    chunk_size_samples: int,
    sample_width: int = AudioFormat.SAMPLE_WIDTH_16BIT,
    channels: int = AudioFormat.CHANNELS_MONO
) -> List[bytes]:
    """
    Split PCM audio into chunks
    
    Args:
        pcm_bytes: Raw PCM audio bytes
        chunk_size_samples: Number of samples per chunk
        sample_width: Bytes per sample (default: 2 for 16-bit)
        channels: Number of channels (default: 1 for mono)
        
    Returns:
        List of PCM byte chunks
    """
    chunk_size_bytes = chunk_size_samples * sample_width * channels
    
    chunks = []
    for i in range(0, len(pcm_bytes), chunk_size_bytes):
        chunk = pcm_bytes[i:i + chunk_size_bytes]
        chunks.append(chunk)
    
    logger.debug(
        f"Split {len(pcm_bytes)} bytes into {len(chunks)} chunks "
        f"of ~{chunk_size_bytes} bytes each"
    )
    
    return chunks


def pcm_to_base64(pcm_bytes: bytes) -> str:
    """
    Encode PCM bytes to base64 string
    
    Args:
        pcm_bytes: Raw PCM audio bytes
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(pcm_bytes).decode('utf-8')


def base64_to_pcm(base64_string: str) -> bytes:
    """
    Decode base64 string to PCM bytes
    
    Args:
        base64_string: Base64 encoded audio
        
    Returns:
        Raw PCM audio bytes
    """
    return base64.b64decode(base64_string)


def save_wav_file(
    filepath: str,
    pcm_bytes: bytes,
    sample_rate: int = AudioFormat.SAMPLE_RATE_16KHZ,
    channels: int = AudioFormat.CHANNELS_MONO,
    sample_width: int = AudioFormat.SAMPLE_WIDTH_16BIT
) -> None:
    """
    Save PCM audio data as a WAV file
    
    Args:
        filepath: Output file path
        pcm_bytes: Raw PCM audio bytes
        sample_rate: Sample rate in Hz (default: 16000)
        channels: Number of channels (default: 1)
        sample_width: Sample width in bytes (default: 2)
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with wave.open(str(filepath), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    
    duration = len(pcm_bytes) / (sample_rate * sample_width * channels)
    logger.info(
        f"Saved WAV: {filepath} ({sample_rate}Hz, {channels}ch, "
        f"{sample_width*8}bit, {duration:.2f}s)"
    )


def get_audio_info(filepath: str) -> Dict[str, Any]:
    """
    Get audio file information without loading the entire file
    
    Args:
        filepath: Path to WAV file
        
    Returns:
        Dictionary with audio metadata
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"WAV file not found: {filepath}")
    
    with wave.open(str(filepath), 'rb') as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        comp_type = wav_file.getcomptype()
        comp_name = wav_file.getcompname()
        
        duration_seconds = n_frames / sample_rate if sample_rate > 0 else 0
        total_bytes = n_frames * sample_width * channels
        
        # Calculate bit rate
        bit_rate = (total_bytes * 8) / duration_seconds if duration_seconds > 0 else 0
        
        return {
            'filepath': str(filepath),
            'filename': filepath.name,
            'channels': channels,
            'sample_width': sample_width,
            'sample_width_bits': sample_width * 8,
            'sample_rate': sample_rate,
            'n_frames': n_frames,
            'duration_seconds': duration_seconds,
            'total_bytes': total_bytes,
            'size_bytes': filepath.stat().st_size,
            'comp_type': comp_type,
            'comp_name': comp_name,
            'bit_rate': bit_rate
        }


def print_wav_info(filepath: str) -> None:
    """
    Print comprehensive information about a WAV file
    
    Args:
        filepath: Path to WAV file
    """
    try:
        info = get_audio_info(filepath)
        
        print(f"Path: {info['filepath']}")
        
        # Codec information
        codec_name = info['comp_name'] if info['comp_name'] != 'not compressed' else 'PCM'
        if info['comp_type'] == 'NONE':
            print(f"Codec:          PCM (uncompressed)")
        else:
            print(f"Codec:          {codec_name} ({info['comp_type']})")
        
        print(f"Channels:       {info['channels']} ({'mono' if info['channels'] == 1 else 'stereo' if info['channels'] == 2 else f'{info['channels']}-channel'})")
        print(f"Sample Rate:    {info['sample_rate'] // 1000}KHz")
        print(f"Bit Depth:      {info['sample_width_bits']}-bit")
        print(f"Bit Rate:       {info['bit_rate'] / 1000:.1f} kbps")
        print(f"Duration:       {info['duration_seconds']:.3f}sec")
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
    except Exception as e:
        logger.error(f"Error reading WAV file info: {e}", exc_info=True)
        print(f"ERROR: Failed to read WAV file: {e}")


def validate_pcm_chunk(
    pcm_base64: str,
    max_size_bytes: int = 100000
) -> Tuple[bool, str]:
    """
    Validate a base64-encoded PCM audio chunk
    
    Args:
        pcm_base64: Base64 encoded PCM audio
        max_size_bytes: Maximum allowed size in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pcm_base64:
        return False, "Empty audio chunk"
    
    try:
        pcm_bytes = base64.b64decode(pcm_base64)
    except Exception as e:
        return False, f"Invalid base64 encoding: {e}"
    
    if len(pcm_bytes) == 0:
        return False, "Decoded audio chunk is empty"
    
    if len(pcm_bytes) > max_size_bytes:
        return False, f"Audio chunk too large: {len(pcm_bytes)} > {max_size_bytes} bytes"
    
    # Check if size is valid for 16-bit samples (should be even number of bytes)
    if len(pcm_bytes) % 2 != 0:
        return False, f"Invalid PCM data: {len(pcm_bytes)} bytes (not divisible by 2)"
    
    return True, ""


def calculate_streaming_delay(
    chunk_size_samples: int,
    sample_rate: int = AudioFormat.SAMPLE_RATE_16KHZ
) -> float:
    """
    Calculate appropriate delay between chunks for real-time streaming
    
    Args:
        chunk_size_samples: Number of samples per chunk
        sample_rate: Sample rate in Hz
        
    Returns:
        Delay in seconds
    """
    return chunk_size_samples / sample_rate


# Convenience functions
def load_wav_for_streaming(
    filepath: str,
    chunk_size_samples: int = 4096
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Load a WAV file and prepare it for streaming
    
    Args:
        filepath: Path to WAV file
        chunk_size_samples: Samples per chunk
        
    Returns:
        Tuple of (list of base64 chunks, metadata)
    """
    # Load WAV file
    pcm_bytes, metadata = load_wav_file(filepath)
    
    # Validate format
    warnings = validate_audio_format(metadata)
    for warning in warnings:
        logger.warning(warning)
    
    # Chunk the audio
    chunks = chunk_audio(
        pcm_bytes,
        chunk_size_samples,
        metadata['sample_width'],
        metadata['channels']
    )
    
    # Convert to base64
    base64_chunks = [pcm_to_base64(chunk) for chunk in chunks]
    
    # Add chunk info to metadata
    metadata['num_chunks'] = len(base64_chunks)
    metadata['chunk_size_samples'] = chunk_size_samples
    metadata['chunk_delay_seconds'] = calculate_streaming_delay(
        chunk_size_samples,
        metadata['sample_rate']
    )
    
    return base64_chunks, metadata


# =============================================================================
# Audio Resampling and Format Conversion
# =============================================================================

def resample_audio(
    audio_data: 'np.ndarray',
    original_rate: int,
    target_rate: int
) -> 'np.ndarray':
    """
    Resample audio to a different sample rate using scipy
    
    Args:
        audio_data: Audio samples as numpy array
        original_rate: Original sample rate in Hz
        target_rate: Target sample rate in Hz
    
    Returns:
        Resampled audio as numpy array
        
    Raises:
        RuntimeError: If scipy is not available
    """
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy is required for audio resampling")
    
    if original_rate == target_rate:
        return audio_data
    
    if not SCIPY_AVAILABLE:
        logger.warning("scipy not available, using simple linear interpolation")
        return simple_resample(audio_data, original_rate, target_rate)
    
    # Calculate resampling ratio
    num_samples = int(len(audio_data) * target_rate / original_rate)
    
    # Use scipy's resample for high-quality resampling
    resampled = signal.resample(audio_data, num_samples)
    
    logger.debug(
        f"Resampled audio: {len(audio_data)} samples @ {original_rate}Hz "
        f"→ {len(resampled)} samples @ {target_rate}Hz"
    )
    
    return resampled.astype(audio_data.dtype)


def simple_resample(
    audio_data: 'np.ndarray',
    original_rate: int,
    target_rate: int
) -> 'np.ndarray':
    """
    Simple linear interpolation resampling (lower quality fallback)
    
    Args:
        audio_data: Audio samples
        original_rate: Original sample rate
        target_rate: Target sample rate
    
    Returns:
        Resampled audio
    """
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy is required for audio resampling")
    
    if original_rate == target_rate:
        return audio_data
    
    # Calculate new length
    ratio = target_rate / original_rate
    new_length = int(len(audio_data) * ratio)
    
    # Create interpolation indices
    old_indices = np.linspace(0, len(audio_data) - 1, new_length)
    
    # Linear interpolation
    resampled = np.interp(
        old_indices,
        np.arange(len(audio_data)),
        audio_data
    )
    
    return resampled.astype(audio_data.dtype)


def webm_to_pcm(
    webm_data: bytes,
    target_sample_rate: int = 16000
) -> Tuple[bytes, int]:
    """
    Convert WebM audio to PCM format
    
    Args:
        webm_data: WebM audio bytes
        target_sample_rate: Target sample rate for output PCM
    
    Returns:
        Tuple of (PCM bytes, actual sample rate)
        
    Raises:
        RuntimeError: If soundfile is not available
    """
    if not SOUNDFILE_AVAILABLE:
        raise RuntimeError("soundfile is required for WebM to PCM conversion")
    
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy is required for WebM to PCM conversion")
    
    try:
        # Read WebM audio using soundfile
        audio_data, original_rate = sf.read(
            io.BytesIO(webm_data),
            dtype='int16'
        )
        
        # Convert stereo to mono if needed
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1).astype('int16')
        
        # Resample if needed
        if original_rate != target_sample_rate:
            audio_data = resample_audio(
                audio_data,
                original_rate,
                target_sample_rate
            )
        
        # Convert to bytes
        pcm_bytes = audio_data.astype('int16').tobytes()
        
        logger.debug(
            f"Converted WebM to PCM: {len(webm_data)} bytes WebM "
            f"→ {len(pcm_bytes)} bytes PCM @ {target_sample_rate}Hz"
        )
        
        return pcm_bytes, target_sample_rate
        
    except Exception as e:
        logger.error(f"Failed to convert WebM to PCM: {e}")
        raise


def pcm_to_wav_bytes(
    pcm_data: bytes,
    sample_rate: int,
    channels: int = 1,
    sample_width: int = 2
) -> bytes:
    """
    Convert raw PCM to WAV format bytes (for browser playback)
    
    Args:
        pcm_data: Raw PCM audio bytes
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        sample_width: Sample width in bytes (2 for 16-bit)
    
    Returns:
        WAV format bytes
        
    Raises:
        RuntimeError: If soundfile is not available
    """
    if not SOUNDFILE_AVAILABLE:
        raise RuntimeError("soundfile is required for PCM to WAV conversion")
    
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy is required for PCM to WAV conversion")
    
    try:
        # Convert bytes to numpy array
        audio_array = np.frombuffer(pcm_data, dtype='int16')
        
        # Reshape for channels if needed
        if channels > 1:
            audio_array = audio_array.reshape(-1, channels)
        
        # Write to WAV format in memory
        wav_buffer = io.BytesIO()
        sf.write(
            wav_buffer,
            audio_array,
            sample_rate,
            format='WAV',
            subtype='PCM_16'
        )
        
        wav_bytes = wav_buffer.getvalue()
        
        logger.debug(
            f"Converted PCM to WAV: {len(pcm_data)} bytes PCM "
            f"→ {len(wav_bytes)} bytes WAV @ {sample_rate}Hz"
        )
        
        return wav_bytes
        
    except Exception as e:
        logger.error(f"Failed to convert PCM to WAV: {e}")
        raise


def normalize_audio(
    audio_data: 'np.ndarray',
    target_level: float = 0.9
) -> 'np.ndarray':
    """
    Normalize audio to target level
    
    Args:
        audio_data: Audio samples as numpy array
        target_level: Target peak level (0.0 to 1.0)
    
    Returns:
        Normalized audio
    """
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy is required for audio normalization")
    
    max_val = np.abs(audio_data).max()
    
    if max_val > 0:
        scale = target_level / max_val
        normalized = audio_data * scale
        return normalized.astype(audio_data.dtype)
    
    return audio_data


def check_audio_dependencies() -> dict:
    """
    Check which audio processing libraries are available
    
    Returns:
        Dictionary of library availability and capabilities
    """
    return {
        "numpy": NUMPY_AVAILABLE,
        "soundfile": SOUNDFILE_AVAILABLE,
        "scipy": SCIPY_AVAILABLE,
        "capabilities": {
            "webm_to_pcm": SOUNDFILE_AVAILABLE and NUMPY_AVAILABLE,
            "resampling": NUMPY_AVAILABLE,
            "high_quality_resampling": SCIPY_AVAILABLE and NUMPY_AVAILABLE,
            "format_conversion": SOUNDFILE_AVAILABLE and NUMPY_AVAILABLE,
            "normalization": NUMPY_AVAILABLE
        }
    }
