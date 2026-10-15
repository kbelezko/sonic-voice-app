# AWS Bedrock Nova Sonic Integration

This application now supports **AWS Bedrock Nova Sonic** for real-time, bidirectional voice conversations.

## What is Nova Sonic?

Nova Sonic is Amazon's speech-to-speech foundation model that enables:
- **Real-time voice conversations** with low latency
- **Bidirectional streaming** - simultaneous speech input and output
- **Tool calling** - Can invoke functions during conversation
- **Multi-lingual support** - English (US, UK), French, Italian, German, Spanish
- **Natural interruptions** - Handles user barge-in gracefully
- **Background noise robustness** - Works in real-world scenarios

## Architecture

### Current Implementation (Mock Sonic)
```
Frontend (WebSocket) 
    ↓ audio (webm)
Backend (FastAPI)
    ↓ audio → (mock) transcription
    ↓ text → Bedrock Claude (text-to-text)
    ↓ text → (mock) TTS
    ↓ audio (mp3)
Frontend
```

### Nova Sonic Implementation
```
Frontend (WebSocket)
    ↓ audio (PCM)
Backend (FastAPI)
    ↓ audio → Nova Sonic (speech-to-speech with tools)
    ↓ audio ← Nova Sonic
    ↓ audio (PCM)
Frontend
```

## Enabling Nova Sonic

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies include:
- `aws-sdk-bedrock-runtime` - Nova Sonic SDK
- `smithy-core` & `smithy-aws-core` - SDK dependencies
- `pyaudio` - Audio handling (requires system libraries)

### 2. Install PyAudio System Dependencies

**macOS:**
```bash
brew install portaudio
```

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

**Windows:**
```bash
# PyAudio may require manual installation
pip install pipwin
pipwin install pyaudio
```

### 3. Enable Nova Sonic

Edit `backend/.env`:
```bash
USE_NOVA_SONIC=true
NOVA_SONIC_MODEL_ID=amazon.nova-sonic-v1:0
AWS_REGION=us-east-1
```

### 4. Ensure AWS Credentials

Nova Sonic requires AWS credentials:
```bash
aws login
# or
aws configure
```

### 5. Check Model Access

Ensure Nova Sonic is available in your region:
```bash
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `nova-sonic`)]'
```

## Using Nova Sonic Service

The `NovaSonicService` class provides:

### Key Methods

```python
# Initialize with MCP tools for function calling
nova_sonic = NovaSonicService(
    model_id="amazon.nova-sonic-v1:0",
    region="us-east-1",
    mcp_tools=mcp_tools,
    bedrock_service=bedrock_service
)

# Start session with system prompt
await nova_sonic.start_session(system_prompt="You are a hotel booking assistant...")

# Start audio input stream
content_name = await nova_sonic.start_audio_content()

# Send audio chunks (base64 encoded PCM)
await nova_sonic.send_audio_chunk(audio_base64, content_name)

# End audio input
await nova_sonic.end_audio_content(content_name)

# Get response audio
audio_bytes = await nova_sonic.get_audio_chunk()

# Get events (transcriptions, tool calls, etc.)
event = await nova_sonic.get_event()

# End session
await nova_sonic.end_session()
```

### Audio Format Requirements

**Input:**
- Format: PCM (Linear Pulse Code Modulation)
- Sample Rate: 16000 Hz
- Sample Size: 16 bits
- Channels: 1 (mono)
- Encoding: base64

**Output:**
- Format: PCM
- Sample Rate: 24000 Hz
- Sample Size: 16 bits
- Channels: 1 (mono)
- Encoding: base64

### Event Types

Nova Sonic streams various events:

1. **contentStart** - Beginning of content (user/assistant)
2. **textOutput** - Transcription of speech
3. **audioOutput** - Audio response chunks
4. **toolUse** - Function/tool call request
5. **toolResult** - Tool execution result
6. **contentEnd** - End of content

## Tool Calling with Nova Sonic

Nova Sonic natively supports tool calling:

```python
# Tools are automatically integrated from MCPTools
tools = mcp_tools.get_tool_definitions()

# Nova Sonic will:
# 1. Detect when to call a tool
# 2. Pause audio output
# 3. Execute the tool
# 4. Resume conversation with tool result
# 5. Continue audio response
```

Example flow:
```
User: "Find me hotels in Miami"
Nova Sonic: [calls search_hotels tool]
Tool Result: [list of Miami hotels]
Nova Sonic: "I found 3 hotels in Miami. The Oceanview..."
```

## Frontend Integration

### WebSocket Message Format

**Audio Input (to backend):**
```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_pcm_audio",
  "format": "pcm",
  "sample_rate": 16000
}
```

**Audio Output (from backend):**
```json
{
  "type": "assistant_voice",
  "audio": "base64_encoded_pcm_audio",
  "format": "pcm",
  "sample_rate": 24000
}
```

**Transcription:**
```json
{
  "type": "transcription",
  "text": "User said this",
  "is_final": true,
  "role": "user"
}
```

**Tool Execution:**
```json
{
  "type": "tool_execution",
  "tool_name": "search_hotels",
  "status": "executing"
}
```

## Barge-in Support

Nova Sonic supports natural interruptions:

1. User starts speaking while assistant is talking
2. Nova Sonic detects interruption
3. Sends `{ "interrupted": true }` signal
4. Backend stops queuing audio output
5. Clears audio playback queue
6. Processes new user input

## Comparison: Mock vs Nova Sonic

| Feature | Mock Sonic | Nova Sonic |
|---------|-----------|------------|
| STT | Mock | Real-time ASR |
| LLM | Bedrock Claude (text) | Nova Sonic (speech) |
| TTS | Mock | Real-time TTS |
| Latency | High (multiple steps) | Low (streaming) |
| Tool Calling | Via Bedrock | Native |
| Interruptions | Not supported | Graceful barge-in |
| Languages | N/A | Multi-lingual |
| Voice Quality | N/A | Natural, expressive |

## Troubleshooting

### "Model not found" Error
- Check model ID: `amazon.nova-sonic-v1:0`
- Verify region supports Nova Sonic: `us-east-1`, `us-west-2`
- Check model access in AWS Console

### "Credentials not found" Error
- Run `aws login` or `aws configure`
- Verify credentials: `aws sts get-caller-identity`
- Check IAM permissions for Bedrock

### PyAudio Installation Fails
- macOS: `brew install portaudio`
- Ubuntu: `sudo apt-get install portaudio19-dev`
- Windows: Use `pipwin` or pre-built wheels

### Audio Not Playing
- Check audio format matches (PCM, 24000 Hz)
- Verify base64 encoding
- Test audio device availability

### High Latency
- Reduce chunk size (currently 512 bytes)
- Check network connectivity to AWS
- Consider regional proximity

## Model IDs

- **Nova Sonic v1**: `amazon.nova-sonic-v1:0`
- **Nova 2 Sonic** (newer, if available): Check AWS documentation

## References

- [Nova Sonic Documentation](https://docs.aws.amazon.com/nova/latest/userguide/speech.html)
- [Bidirectional Streaming API](https://docs.aws.amazon.com/nova/latest/userguide/speech-bidirection.html)
- [Nova Sonic GitHub Samples](https://github.com/awslabs/amazon-nova-samples)
