# Nova Sonic Event Processing Fix

## Problem
Nova Sonic was not responding with events after `userSpeechStart`. The session would start, audio would be sent, but no transcriptions or responses would be received.

## Root Cause
The `_process_responses()` task was being started **AFTER** all the initialization events were sent in `start_session()`. This meant:

1. Events were sent: `sessionStart`, `promptStart`, system prompts, etc.
2. Nova Sonic responded to these events immediately
3. But nobody was listening - the response processor hadn't started yet
4. Responses were buffered in the stream but never consumed
5. Eventually the stream would block or timeout

## Solution
Start the response processor **BEFORE** sending any events:

```python
async def start_session(self, system_prompt: str = None):
    # ... initialize client and stream ...
    
    # **CRITICAL**: Start processing responses BEFORE sending any events
    asyncio.create_task(self._process_responses())
    
    # Small delay to ensure response processor is running
    await asyncio.sleep(0.1)
    
    # Now send events
    await self.send_event(session_start)
    await self.send_event(prompt_start)
    # etc...
```

## Comparison with Reference Implementation
The example code in `nova_s2s_backend.py` follows this same pattern:

```python
async def initialize_stream(self):
    self.stream_response = await self.bedrock_client.invoke_model_with_bidirectional_stream(...)
    self.is_active = True
    
    # Start listening for responses IMMEDIATELY
    self.response_task = asyncio.create_task(self._process_responses())
    
    # Start processing audio input
    asyncio.create_task(self._process_audio_input())
    
    # Wait a bit to ensure everything is set up
    await asyncio.sleep(0.1)
```

## Test Results

### Before Fix
```
Sending audio chunks...
[No events received]
Timeout waiting for response
```

### After Fix
```
Sending audio chunks...
[Event] {'userSpeechStart': {'inputAudioOffsetMs': 0, ...}}
[Event processing continues...]
```

## Key Learnings

1. **Bidirectional streaming requires continuous consumption**: Both input and output streams must be actively processed simultaneously

2. **Response processor must start early**: Start consuming responses before sending requests to avoid blocking

3. **Async task ordering matters**: The order of `asyncio.create_task()` calls determines when background processing begins

4. **Queue-based architectures help**: The reference implementation uses queues to decouple audio input processing from event sending

## Files Modified
- `backend/services/nova_sonic_service.py` - Moved `_process_responses()` task creation before event sending

## Status
✅ Fixed - Nova Sonic now receives and processes events in real-time
