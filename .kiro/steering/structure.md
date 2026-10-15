---
name: Project Structure
description: Folder organization and architecture patterns
---

# Project Structure

## Repository Layout

```
book-hotel-kiro/
├── frontend/          # Next.js voice UI
├── backend/           # FastAPI WebSocket server
└── README.md          # Setup instructions
```

## Frontend Structure (`frontend/`)

```
frontend/
├── app/
│   ├── page.tsx           # Main conversation page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/
│   ├── ConversationWindow.tsx  # Chat message display
│   ├── MessageBubble.tsx       # Individual message UI
│   ├── VoiceButton.tsx         # Microphone control
│   └── ErrorBoundary.tsx       # Error handling
├── lib/
│   └── useVoiceChat.ts    # WebSocket hook with audio streaming
├── package.json
└── next.config.ts
```

### Frontend Conventions

- Components use TypeScript with explicit types
- Client components marked with `"use client"`
- WebSocket logic encapsulated in `useVoiceChat` hook
- Audio handling: MediaRecorder → PCM conversion → WebSocket streaming

## Backend Structure (`backend/`)

```
backend/
├── app/
│   └── main.py                    # FastAPI app, WebSocket endpoint
├── models/
│   └── __init__.py               # Pydantic models (booking, hotel)
├── repositories/
│   ├── hotel_repository.py       # 25 mock hotels
│   └── booking_repository.py     # In-memory bookings
├── services/
│   ├── nova_sonic_service.py     # Nova Sonic integration (main)
│   ├── bedrock_service.py        # Claude text conversations
│   ├── conversation_manager.py   # Session/history management
│   ├── mcp_tools.py              # Tool definitions and execution
│   ├── validation.py             # Date/contact validation
│   ├── audio_processing.py       # Format conversion utilities
│   ├── utils_audio.py            # PCM/WAV helpers
│   └── utils_speaker.py          # Audio output helpers
├── resources/                     # Test audio files
├── tests/                         # Test suite
├── test_sonic.py                 # Nova Sonic integration test
├── requirements.txt
└── ARCHITECTURE.md               # Detailed architecture docs
```

### Backend Conventions

- Services follow single responsibility principle
- All services imported from `services/__init__.py`
- Repositories handle data access (no database, in-memory)
- MCP tools define available actions for AI assistant
- WebSocket handlers in `main.py` coordinate service calls

## Architecture Layers

1. **WebSocket Layer** (`app/main.py`)
   - Handles client connections
   - Routes messages to appropriate services
   - Manages session lifecycle

2. **Service Layer** (`services/`)
   - `NovaSonicService` - Primary voice service (speech-to-speech + tools)
   - `MCPTools` - Tool definitions and execution
   - `BedrockService` - System prompt generation
   - Audio utilities for format conversion

3. **Repository Layer** (`repositories/`)
   - Data access abstraction
   - In-memory storage for hotels and bookings

4. **Model Layer** (`models/`)
   - Pydantic schemas for validation
   - Type definitions for API contracts

## Key Files

- `backend/app/main.py` - WebSocket endpoint, session management
- `backend/services/nova_sonic_service.py` - Core voice service
- `backend/services/mcp_tools.py` - Available AI actions
- `frontend/lib/useVoiceChat.ts` - Client WebSocket hook
- `frontend/components/VoiceButton.tsx` - Audio capture

## Naming Conventions

- **Python:** snake_case for files, classes use PascalCase
- **TypeScript:** PascalCase for components, camelCase for hooks/utilities
- **Services:** Named as `[Feature]Service` (e.g., `NovaSonicService`)
- **Repositories:** Named as `[Entity]Repository` (e.g., `HotelRepository`)

## WebSocket Message Flow

```
Browser → useVoiceChat hook → WebSocket → main.py → NovaSonicService → Nova Sonic
                                                    ↓
                                                MCPTools
                                                    ↓
                                            Repositories
```
