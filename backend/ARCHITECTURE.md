# Backend Architecture

## Overview
The backend is built exclusively around AWS Bedrock Nova Sonic for real-time speech-to-speech voice conversations with integrated tool calling.

## Architecture

**Single-Mode Design**:
```
Browser → WebSocket → Nova Sonic (speech-to-speech with native tools) → Browser
                         ↓
                    MCP Tools (search, book hotels)
```

**Components**:
- **NovaSonicService** (`services/nova_sonic_service.py`):
  - Real-time bidirectional streaming with AWS Bedrock
  - Native speech-to-text (built into Nova Sonic)
  - Native conversation handling (built into Nova Sonic)
  - Native tool calling (MCP tools integrated)
  - Native text-to-speech (built into Nova Sonic)
  - Uses AWS SDK for Python with `AsyncBedrockRuntimeClient`

**Advantages**:
- Single model handles entire voice conversation pipeline
- Lower latency (no separate STT/LLM/TTS steps)
- More natural conversation flow
- Native turn detection

**Audio Requirements**:
- Input: PCM, 16kHz, 16-bit, mono, base64 encoded
- Output: PCM, 16kHz, 16-bit, mono, base64 encoded (converted to WAV for browser)

---

## Service Files

### Voice Services

| File | Class | Purpose |
|------|-------|---------|
| `nova_sonic_service.py` | `NovaSonicService` | AWS Bedrock Nova Sonic integration |

### Core Services

| File | Class | Purpose |
|------|-------|---------|
| `bedrock_service.py` | `BedrockService` | Claude text conversations |
| `conversation_manager.py` | `ConversationManager` | Session and history management |
| `mcp_tools.py` | `MCPTools` | Tool definitions and execution |
| `validation.py` | Validation services | Input validation for dates, contacts, etc. |
| `audio_processing.py` | `AudioProcessor` | Audio format conversion utilities |


## WebSocket Endpoints

### `/ws/voice`
Main endpoint for voice interactions with Nova Sonic.

Handles:
- Audio streaming (PCM format)
- Transcription events
- Assistant responses
- Tool execution notifications

### Message Types (Client → Server)

```json
{
  "type": "audio_chunk",
  "data": "<base64 PCM audio>",
  "format": "pcm",
  "sample_rate": 16000
}
```

```json
{
  "type": "voice_start"
}
```

```json
{
  "type": "voice_end"
}
```

```json
{
  "type": "text_input",
  "text": "Find hotels in Seattle"
}
```

### Message Types (Server → Client)

```json
{
  "type": "transcription",
  "text": "user speech transcribed",
  "is_final": true
}
```

```json
{
  "type": "assistant_text",
  "text": "I can help you find hotels"
}
```

```json
{
  "type": "assistant_voice",
  "audio": "<base64 audio>",
  "format": "wav"
}
```

```json
{
  "type": "tool_execution",
  "status": "executing",
  "tool_name": "search_hotels"
}
```

```json
{
  "type": "error",
  "message": "error description",
  "code": "ERROR_CODE"
}
```


## Configuration (.env)

```env
# AWS Configuration
AWS_REGION=us-east-1

# Bedrock Configuration (for system prompts)
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20250122-v1:0

# Nova Sonic Configuration
NOVA_SONIC_MODEL_ID=amazon.nova-2-sonic-v1:0

# CORS Settings
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Test Scripts

- **`test_sonic.py`**: Tests Nova Sonic integration with WAV file
  - Validates PCM audio format
  - Tests speech-to-text
  - Checks event handling
  - Usage: `python test_sonic.py`

### Test Resources

- **`resources/can-t-help-me-mono-16KHz.wav`**: Sample audio file
  - Format: 16kHz, mono, 16-bit PCM
  - Duration: ~5 seconds
  - Used for Nova Sonic format validation


## Dependencies

Key Python packages:
- `fastapi` - WebSocket API
- `boto3` - AWS credentials
- `aws-sdk-bedrock-runtime` - Bedrock client
- `soundfile` - Audio file handling
- `scipy` - Audio resampling
- `python-dotenv` - Environment configuration

---

## Getting Started

### Prerequisites
- Python 3.9+
- AWS credentials configured (`aws login`)
- Access to AWS Bedrock Nova Sonic

### Installation
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running
```bash
uvicorn app.main:app --reload --port 8000
```

### Testing
```bash
python test_sonic.py
```
