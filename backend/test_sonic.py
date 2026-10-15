"""
Test script for Nova Sonic integration using a pre-recorded WAV file

Usage:
    python test_sonic.py [path/to/audio.wav]
    
Note: All events are logged by NovaSonicService._process_responses()
Check the console output for transcriptions, assistant responses, and audio events.
"""

import asyncio
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.nova_sonic_service import NovaSonicService
from services.utils_audio import print_wav_info

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s() - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_nova_sonic(wav_file: Path = None):
    """Test Nova Sonic with a WAV file"""
    
    # Default WAV file if none provided
    if not wav_file:
        # wav_file = Path("resources/can-t-help-me-mono-16KHz.wav")
        wav_file = Path("resources/how-are-you-doing-today-4.wav")
    else:
        wav_file = Path(wav_file)
    
    # Check if file exists
    if not wav_file.exists():
        print(f"ERROR: WAV file not found: {wav_file}")
        return
    
    # Display audio file information
    print_wav_info(str(wav_file))
    print()
    
    print("="*60)
    print("Nova Sonic Test")
    print("="*60 + "\n")
    
    # Initialize Nova Sonic service (speaker enabled by default)
    print("Initializing Nova Sonic service...")
    
    nova_sonic = NovaSonicService(
        system_prompt="You are a helpful assistant. Listen to the user and respond naturally.",
        enable_speaker=True
    )

    if nova_sonic.speaker:
        print("✓ Audio speaker initialized and ready\n")
    else:
        print("⚠️  Audio speaker not available\n")

    # Start session
    print("Starting Nova Sonic session...")
    await nova_sonic.start_session()
    print("✓ Session started\n")

    # Enable background noise injection to keep the stream alive during silent
    # gaps between WAV chunks. Not used in the normal WebSocket path from main.py.
    nova_sonic.start_background_noise()
    print("✓ Background noise injection enabled\n")
    
    # Send WAV file (audio will be automatically played through speaker)
    print(f"Sending WAV file: {wav_file}")
    print("(Audio will play through speaker automatically)\n")
    await nova_sonic.send_wav_file(str(wav_file))
    print("✓ Audio sent\n")
    
    # Wait for responses (output audio plays automatically through speaker)
    print("Waiting for responses...")
    print("(Check logs for transcription and assistant responses)\n")
    await asyncio.sleep(30.0)
    
    # End session (speaker will be automatically closed)
    print("\nEnding Nova Sonic session...")
    await nova_sonic.end_session()
    print("✓ Session ended")
    print("✓ Speaker cleaned up")
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Get WAV file from command line argument
    wav_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        asyncio.run(test_nova_sonic(wav_file))
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
