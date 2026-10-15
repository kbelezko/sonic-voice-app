"""
FastAPI application with WebSocket voice API for AWS Bedrock Nova Sonic

Architecture:
------------
Browser → WebSocket → Nova Sonic (speech-to-speech + tools) → Browser
                         ↓ 
                    MCP tools integrated natively

Nova Sonic handles:
- Speech-to-text (STT)
- Conversation with Claude
- Tool calling via MCP
- Text-to-speech (TTS)

All in one unified speech-to-speech model.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import json
import uuid
from datetime import datetime
import traceback
import logging
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from services import NovaSonicService

# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("APP_NAME", "Hotel Booking Voice API"),
    version="1.0.0"
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections and Nova Sonic sessions
active_connections: Dict[str, WebSocket] = {}
nova_sonic_sessions: Dict[str, NovaSonicService] = {}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket, session_id: str = None):
    """WebSocket endpoint for voice interactions with Nova Sonic"""
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    logger.info(f"WebSocket connection accepted for session {session_id}")
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        # Handle Nova Sonic session
        await handle_nova_sonic_session(websocket, session_id)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"An error occurred: {str(e)}",
                "code": "INTERNAL_ERROR"
            })
        except:
            pass
    
    finally:
        # Cleanup
        if session_id in active_connections:
            del active_connections[session_id]
        
        # Cleanup Nova Sonic session if exists
        if session_id in nova_sonic_sessions:
            try:
                await nova_sonic_sessions[session_id].end_session()
            except:
                pass
            del nova_sonic_sessions[session_id]


async def handle_nova_sonic_session(websocket: WebSocket, session_id: str):
    """Handle session with Nova Sonic (real-time speech-to-speech)"""
    logger.info(f"Starting Nova Sonic session for {session_id}")
    
    # Create Nova Sonic service
    nova_sonic = NovaSonicService()
    nova_sonic_sessions[session_id] = nova_sonic
    
    # Start Nova Sonic session
    await nova_sonic.start_session()
    
    # Send welcome message
    await websocket.send_json({
        "type": "assistant_text",
        "text": "Hello! I'm your hotel booking assistant. How can I help you today?"
    })
    
    # Start audio output task
    audio_output_task = asyncio.create_task(
        stream_nova_sonic_audio(websocket, nova_sonic, session_id)
    )
    
    # Start event forwarding task
    event_forward_task = asyncio.create_task(
        forward_nova_sonic_events(websocket, nova_sonic, session_id)
    )
    
    # Track audio content stream
    audio_content_name: Optional[str] = None
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "audio_chunk":
                # Process audio chunk (PCM from browser)
                audio_data = message.get("data", "")

                try:
                    # Start audio content stream on first chunk
                    if audio_content_name is None:
                        audio_content_name = await nova_sonic.start_audio_content()
                        logger.info(f"Started audio content stream: {audio_content_name}")

                    # Forward PCM chunk to Nova Sonic
                    success = await nova_sonic.process_and_send_pcm_chunk(
                        audio_data,
                        audio_content_name
                    )
                    if not success:
                        logger.warning("Failed to send audio chunk to Nova Sonic")
                except Exception as e:
                    logger.error(f"Audio chunk error (dropping chunk): {e}", exc_info=True)
            
            elif message_type == "voice_start":
                # User started speaking
                await websocket.send_json({
                    "type": "status",
                    "message": "Listening..."
                })
            
            elif message_type == "voice_end":
                # User stopped speaking - end audio content stream
                if audio_content_name:
                    await nova_sonic.end_audio_content(audio_content_name)
                    logger.info(f"Ended audio content stream: {audio_content_name}")
                    audio_content_name = None
            
            elif message_type == "text_input":
                # Text fallback (not typical for Nova Sonic but supported)
                text = message.get("text", "")
                logger.info(f"Text input in Nova Sonic mode: {text}")
                # Could send as text content to Nova Sonic if needed
    
    finally:
        # Cancel background tasks
        audio_output_task.cancel()
        event_forward_task.cancel()
        
        try:
            await asyncio.gather(audio_output_task, event_forward_task, return_exceptions=True)
        except:
            pass


async def stream_nova_sonic_audio(websocket: WebSocket, nova_sonic: NovaSonicService, session_id: str):
    """Stream audio output from Nova Sonic to client"""
    try:
        while True:
            # Get audio chunk as WAV format
            wav_base64 = await nova_sonic.get_audio_chunk_as_wav()
            
            if wav_base64:
                await websocket.send_json({
                    "type": "assistant_voice",
                    "audio": wav_base64,
                    "format": "wav"
                })
            else:
                await asyncio.sleep(0.05)  # Small delay if no audio
    
    except asyncio.CancelledError:
        logger.info(f"Audio streaming cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Error streaming audio for session {session_id}: {e}")


async def forward_nova_sonic_events(websocket: WebSocket, nova_sonic: NovaSonicService, session_id: str):
    """Forward Nova Sonic events to the client.

    Each event is sent twice:
    - As a typed conversation message (transcription / tool_execution) for the
      centre transcript panel.
    - As a raw sonic_event for the right-hand technical events panel. Audio
      content is stripped to keep payloads small.
    """
    try:
        while True:
            event = await nova_sonic.get_event()

            if not event:
                await asyncio.sleep(0.05)
                continue

            if 'event' not in event:
                continue

            event_data = event['event']
            event_type = next(iter(event_data.keys()), None)
            if not event_type:
                continue

            # ── conversation messages (existing behaviour) ────────────────
            if 'textOutput' in event_data:
                role = event_data['textOutput'].get('role', 'ASSISTANT')
                await websocket.send_json({
                    "type": "transcription",
                    "text": event_data['textOutput']['content'],
                    "is_final": True,
                    "role": role.lower()
                })

            elif 'toolUse' in event_data:
                await websocket.send_json({
                    "type": "tool_execution",
                    "tool_name": event_data['toolUse']['toolName'],
                    "status": "executing"
                })

            # ── technical sonic_event (strip heavy audio bytes) ───────────
            # audioOutput and usageEvent are excluded — too noisy / not useful in the UI
            EXCLUDED_FROM_PANEL = {'audioOutput', 'usageEvent'}
            if event_type not in EXCLUDED_FROM_PANEL:
                summary = dict(event_data.get(event_type, {}))
                await websocket.send_json({
                    "type": "sonic_event",
                    "event_type": event_type,
                    "data": summary
                })

    except asyncio.CancelledError:
        logger.info(f"Event forwarding cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Error forwarding events for session {session_id}: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
