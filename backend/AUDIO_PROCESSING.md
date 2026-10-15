# Audio Processing & Resampling

## Overview

The application handles audio format conversion and resampling to bridge the gap between browser audio formats and AWS Bedrock Nova Sonic requirements.

## Audio Flow

### Input Path: Browser → Nova Sonic

```
Browser MediaRecorder
  ↓ WebM/Opus @ 48kHz (stereo)
  ↓ base64 encoded
WebSocket
  ↓
Backend (audio_processing.py)
  ↓ Decode base64
  ↓ Convert WebM → PCM
  ↓ Stereo → Mono
  ↓ Resample 48kHz → 16kHz
  ↓ Encode base64
Nova Sonic
```

### Output Path: Nova Sonic → Browser

```
Nova Sonic
  ↓ PCM @ 24kHz (mono)
  ↓ base64 encoded
Backend (audio_processing.py)
  ↓ Decode base64
  ↓ Convert PCM → WAV
  ↓ (Optional: Resample 24kHz → 48kHz)
  ↓ Encode base64
WebSocket
  ↓
Browser AudioContext
  ↓ Decode and play
```

## Format Specifications

### Browser Audio (Input)
- **Container**: WebM
- **Codec**: Opus (typical)
- **Sample Rate**: 48000 Hz (browser default)
- **Channels**: 2 (stereo)
- **Bit Depth**: 16-bit
- **Encoding**: Base64 for transmission

### Nova Sonic Requirements

**Input:**
- **Format**: PCM (Linear Pulse Code Modulation)
- **Sample Rate**: 16000 Hz
- **Channels**: 1 (mono)
- **Bit Depth**: 16-bit (int16)
- **Encoding**: Base64

**Output:**
- **Format**: PCM
- **Sample Rate**: 24000 Hz
- **Channels**: 1 (mono)
- **Bit Depth**: 16-bit (int16)
- **Encoding**: Base64

### Browser Audio (Output)
- **Format**: WAV (for compatibility)
- **Sample Rate**: 24000 Hz (or 48000 Hz if resampled)
- **Channels**: 1 (mono)
- **Bit Depth**: 16-bit
- **Encoding**: Base64 for transmission

## Implementation

### AudioProcessor Class

Located in `services/audio_processing.py`, provides:

#### 1. Format Conversion

```python
# WebM to PCM
pcm_bytes, sample_rate = AudioProcessor.webm_to_pcm(
    webm_data,
    target_sample_rate=16000
)

# PCM to WAV
wav_bytes = AudioProcessor.pcm_to_wav(
    pcm_data,
    sample_rate=24000,
    channels=1
)
```

#### 2. Resampling

```python
# Resample audio
resampled = AudioProcessor.resample_audio(
    audio_data,      # numpy array
    original_rate=48000,
    target_rate=16000
)
```

#### 3. Stereo to Mono Conversion

Automatically performed during WebM → PCM conversion:
```python
# Average left and right channels
if audio_data.shape[1] == 2:
    audio_mono = audio_data.mean(axis=1)
```

## Dependencies

### Required Libraries

```bash
# Audio file I/O
soundfile==0.12.1

# High-quality resampling
scipy==1.15.2

# Numerical operations
numpy==2.2.3
```

### System Dependencies

**soundfile** requires libsndfile:

**macOS:**
```bash
brew install libsndfile
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libsndfile1
```

**Windows:**
```bash
# Usually bundled with soundfile package
pip install soundfile
```

## Resampling Algorithm

Uses **scipy.signal.resample** for high-quality resampling:

### Features:
- **Fourier-domain resampling** - High quality, prevents aliasing
- **Linear phase** - No phase distortion
- **Arbitrary ratios** - Any source/target rate combination

### Example:
```python
from scipy import signal

# Resample 48kHz → 16kHz
# Ratio: 16000 / 48000 = 1/3
num_samples = int(len(audio) * 16000 / 48000)
resampled = signal.resample(audio, num_samples)
```

### Fallback Method:
If scipy is unavailable, uses simple linear interpolation:
```python
def simple_resample(audio, orig_rate, target_rate):
    ratio = target_rate / orig_rate
    new_length = int(len(audio) * ratio)
    old_indices = np.linspace(0, len(audio)-1, new_length)
    return np.interp(old_indices, np.arange(len(audio)), audio)
```

## Usage in Nova Sonic Service

### Incoming Audio (WebM from Browser)

```python
# In nova_sonic_service.py
async def process_and_send_webm_chunk(self, webm_base64, content_name):
    # Decode
    webm_bytes = base64.b64decode(webm_base64)
    
    # Convert and resample
    pcm_bytes, rate = self.audio_processor.webm_to_pcm(
        webm_bytes,
        target_sample_rate=16000  # Nova Sonic requirement
    )
    
    # Re-encode
    pcm_base64 = base64.b64encode(pcm_bytes).decode('utf-8')
    
    # Send to Nova Sonic
    await self.send_audio_chunk(pcm_base64, content_name)
```

### Outgoing Audio (PCM from Nova Sonic)

```python
# In nova_sonic_service.py
async def get_audio_chunk_as_wav(self):
    # Get PCM from Nova Sonic
    pcm_bytes = await self.audio_queue.get()
    
    # Convert to WAV for browser
    wav_bytes = self.audio_processor.pcm_to_wav(
        pcm_bytes,
        sample_rate=24000,  # Nova Sonic output rate
        channels=1
    )
    
    # Encode for transmission
    return base64.b64encode(wav_bytes).decode('utf-8')
```

## Quality Considerations

### Input Path (Browser → Nova Sonic)

**Downsampling 48kHz → 16kHz:**
- **Loss**: Some high-frequency content (8kHz+ lost)
- **Impact**: Minimal for speech (most energy < 8kHz)
- **Benefit**: Lower bandwidth, faster processing

**Stereo → Mono:**
- **Loss**: Spatial information
- **Impact**: None for speech understanding
- **Benefit**: 50% bandwidth reduction

### Output Path (Nova Sonic → Browser)

**24kHz Output:**
- **Bandwidth**: 0 - 12kHz
- **Quality**: Excellent for speech
- **Decision**: Keep at 24kHz or resample to 48kHz?

**Option 1: Keep 24kHz**
- ✅ Lower bandwidth
- ✅ No quality loss from resampling
- ⚠️ Browser may need AudioContext configuration

**Option 2: Resample to 48kHz**
- ✅ Browser hardware default
- ✅ Easier playback
- ⚠️ Slight processing overhead

## Latency Impact

### Processing Time Estimates

**WebM → PCM (48kHz → 16kHz):**
- Decoding: ~5-10ms per 1s of audio
- Resampling: ~2-5ms per 1s of audio
- Total: **~7-15ms overhead**

**PCM → WAV (24kHz):**
- Format wrapping: ~1-2ms per 1s of audio
- Total: **~1-2ms overhead**

### Real-Time Constraint

For real-time audio (1 second of audio processed in < 1 second):
- 48kHz → 16kHz downsampling: **~15ms** to process 1000ms ✅
- 24kHz WAV wrapping: **~2ms** to process 1000ms ✅

Both operations are well within real-time constraints.

## Debugging

### Check Dependencies

```python
from services.audio_processing import AudioProcessor

# Check what's available
capabilities = AudioProcessor.check_dependencies()
print(capabilities)
# {
#   "soundfile": True,
#   "scipy": True,
#   "capabilities": {
#     "webm_to_pcm": True,
#     "resampling": True,
#     "format_conversion": True
#   }
# }
```

### Test Conversion

```python
import base64
from services.audio_processing import AudioProcessor

processor = AudioProcessor()

# Test WebM → PCM
webm_data = open('test.webm', 'rb').read()
pcm_bytes, rate = processor.webm_to_pcm(webm_data, target_sample_rate=16000)
print(f"PCM output: {len(pcm_bytes)} bytes @ {rate}Hz")

# Test PCM → WAV
wav_bytes = processor.pcm_to_wav(pcm_bytes, sample_rate=16000, channels=1)
print(f"WAV output: {len(wav_bytes)} bytes")
```

### Verify Audio Quality

Use ffmpeg to inspect audio:

```bash
# Decode base64 and check format
echo "BASE64_STRING" | base64 -d > output.wav
ffmpeg -i output.wav

# Should show:
# Duration: ...
# Stream #0:0: Audio: pcm_s16le, 24000 Hz, 1 channels, s16, 384 kb/s
```

## Future Enhancements

### 1. Adaptive Quality
- Adjust resampling quality based on network conditions
- Use lower sample rates for poor connections

### 2. Noise Reduction
- Pre-process input audio to remove background noise
- Improve transcription accuracy

### 3. Voice Activity Detection (VAD)
- Only send audio when speech is detected
- Reduce bandwidth and processing

### 4. Audio Compression
- Apply codec compression before transmission
- Balance quality vs. bandwidth

## References

- [scipy.signal.resample](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample.html)
- [soundfile documentation](https://python-soundfile.readthedocs.io/)
- [Nova Sonic audio requirements](https://docs.aws.amazon.com/nova/latest/userguide/speech.html)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
