# Codebase Simplification - Removed Mock/Text-Based Mode

## Date
October 7, 2026

## Changes Made

### 1. Deleted Mock Voice Service
- **Removed**: `backend/services/mock_voice_service.py`
- **Reason**: Always using Nova Sonic, no need for mock STT/TTS

### 2. Simplified main.py
**Removed**:
- `USE_NOVA_SONIC` environment variable check
- `handle_text_based_session()` function
- `handle_audio_chunk()` function
- `handle_text_input()` function
- `process_user_message()` function (with text-based tool orchestration)
- Import of `MockVoiceService` and `ConversationManager`

**Kept**:
- `handle_nova_sonic_session()` - now the only session handler
- Nova Sonic integration
- MCP tools integration
- BedrockService (used only for system prompts)

### 3. Updated Configuration
**`.env` changes**:
- Removed `USE_NOVA_SONIC=true` flag (always true now)
- Removed `SONIC_API_URL` and `SONIC_API_KEY` (unused)
- Kept Nova Sonic model configuration

### 4. Updated Services
**`services/__init__.py` changes**:
- Removed `MockVoiceService` export
- Removed `ConversationManager` export (Nova Sonic handles conversation internally)

### 5. Updated Documentation
**`ARCHITECTURE.md` changes**:
- Removed two-mode architecture explanation
- Removed mock service documentation
- Simplified to single Nova Sonic mode
- Updated configuration examples
- Added getting started guide

## Architecture Before

```
Two Modes:
┌─────────────────────────────────────────────────────────────┐
│ Text-Based Mode (USE_NOVA_SONIC=false)                       │
│ Browser → WebSocket → Mock STT → Bedrock Claude → Mock TTS  │
│                         ↓ MCP Tools                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Nova Sonic Mode (USE_NOVA_SONIC=true)                        │
│ Browser → WebSocket → Nova Sonic (all-in-one)                │
│                         ↓ MCP Tools                          │
└─────────────────────────────────────────────────────────────┘
```

## Architecture After

```
Single Mode:
┌─────────────────────────────────────────────────────────────┐
│ Browser → WebSocket → Nova Sonic (all-in-one)                │
│                         ↓ MCP Tools                          │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

1. **Simpler codebase**: Removed ~300 lines of unused code
2. **Clearer intent**: No confusion about which mode to use
3. **Less configuration**: One less environment variable to manage
4. **Easier maintenance**: Single code path to test and debug
5. **Better performance**: Always using the optimal Nova Sonic pipeline

## Files Modified

- ✅ `backend/services/mock_voice_service.py` - DELETED
- ✅ `backend/services/__init__.py` - Updated exports
- ✅ `backend/app/main.py` - Simplified, removed text-based mode
- ✅ `backend/.env` - Removed USE_NOVA_SONIC flag
- ✅ `backend/ARCHITECTURE.md` - Updated documentation

## Files Unchanged

- `backend/services/nova_sonic_service.py` - Core service
- `backend/services/bedrock_service.py` - Still used for system prompts
- `backend/services/mcp_tools.py` - Tool definitions
- `backend/test_sonic.py` - Test script
- `frontend/` - No changes needed

## Testing

After these changes, the backend was verified to:
- ✅ Import successfully
- ✅ Run without errors
- ✅ Connect to Nova Sonic
- ✅ Process PCM audio correctly

## Migration Notes

For any existing deployments:
1. Remove `USE_NOVA_SONIC` from environment variables (no longer used)
2. Ensure AWS credentials are configured
3. Restart backend service

No other changes needed!
