"""AWS Bedrock Nova Sonic integration for real-time voice conversations"""

import asyncio
import base64
import json
import os
import uuid
import logging
from typing import Dict, Any, Optional
import boto3
from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
from smithy_aws_core.identity import AWSCredentialsIdentity, StaticCredentialsResolver
from smithy_http.aio.crt import AWSCRTHTTPClient
from .utils_audio import check_audio_dependencies
from .utils_speaker import AudioSpeaker, check_audio_playback_available

logger = logging.getLogger(__name__)

# Audio configuration for Nova Sonic
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 16000  # Match input rate for consistency
CHANNELS = 1
CHUNK_SIZE = 512


def get_aws_credentials_resolver():
    """Get AWS credentials resolver using boto3 (supports full credential chain)"""
    try:
        logger.info("Attempting to resolve AWS credentials...")
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials:
            logger.info(f"Found AWS credentials: access_key={credentials.access_key[:10]}...")
            aws_credentials = AWSCredentialsIdentity(
                access_key_id=credentials.access_key,
                secret_access_key=credentials.secret_key,
                session_token=credentials.token
            )
            # Return a static resolver with the identity
            resolver = StaticCredentialsResolver(identity=aws_credentials)
            logger.info("Created StaticCredentialsResolver successfully")
            return resolver
        else:
            logger.error("boto3 session.get_credentials() returned None")
            return None
    except Exception as e:
        logger.error(f"Error resolving AWS credentials: {e}", exc_info=True)
        return None


class NovaSonicService:
    """Service for AWS Bedrock Nova Sonic voice interactions"""

    def __init__(
        self,
        system_prompt: str = None,
        mcp_tools=None,
        bedrock_service=None,
        enable_speaker: bool = True
    ):
        self.model_id = os.environ["NOVA_SONIC_MODEL_ID"]
        self.region = os.environ["AWS_REGION"]
        self.system_prompt = system_prompt
        self.mcp_tools = mcp_tools
        self.bedrock_service = bedrock_service
        self.client = None
        self.stream = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.audio_queue = asyncio.Queue()
        self.event_queue = asyncio.Queue()
        self.background_noise_task = None
        self.active_content_name = None
        self.role: Optional[str] = None
        
        # Initialize speaker component
        self.enable_speaker = enable_speaker and check_audio_playback_available()
        self.speaker = None
        
        if self.enable_speaker:
            try:
                self.speaker = AudioSpeaker(
                    sample_rate=INPUT_SAMPLE_RATE,
                    channels=CHANNELS,
                    sample_width=2  # 16-bit
                )
                self.speaker.open()
                self.speaker.start_playback_worker()
                logger.info("Audio speaker initialized and ready")
            except Exception as e:
                logger.warning(f"Failed to initialize speaker: {e}")
                self.speaker = None
                self.enable_speaker = False
        else:
            logger.info("Audio speaker disabled or not available")
        
        # Check audio processing capabilities
        capabilities = check_audio_dependencies()
        if not capabilities["soundfile"] or not capabilities["scipy"]:
            logger.warning(
                "Audio processing libraries not fully available. "
                f"Capabilities: {capabilities}"
            )
        
    async def _initialize_client(self):
        """Initialize the Bedrock Nova Sonic client"""
        credentials_resolver = get_aws_credentials_resolver()
        if not credentials_resolver:
            raise RuntimeError("Unable to resolve AWS credentials")
        
        # Create CRT transport for bidirectional streaming
        transport = AWSCRTHTTPClient()
        
        config = await AsyncBedrockRuntimeConfig.resolve(
            region=self.region,
            aws_credentials_identity_resolver=credentials_resolver,
            transport=transport
        )
        self.client = AsyncBedrockRuntimeClient(config=config)
        logger.info(f"Nova Sonic client initialized for {self.region}")
    
    async def send_event(self, event: dict):
        """Send an event to the bidirectional stream"""
        if not self.stream:
            raise RuntimeError("Stream not initialized")
            
        event_type = next(iter(event['event'].keys()))
        if event_type not in ['audioInput']:
            logger.info(f'Sending: {event_type}')

        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps(event).encode('utf-8'))
        )
        await self.stream.input_stream.send(event)
    
    async def start_session(self, system_prompt: str = None):
        """Start a Nova Sonic session"""
        if not self.client:
            await self._initialize_client()
        
        # Use provided system_prompt or fall back to instance system_prompt
        if system_prompt is None:
            system_prompt = self.system_prompt
        
        logger.info(f"Starting Nova Sonic session with model {self.model_id}")
        
        # Initialize the bidirectional stream
        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True
        
        # **CRITICAL**: Start processing responses BEFORE sending any events
        # This ensures we consume Nova Sonic's responses in real-time
        asyncio.create_task(self._process_responses())
        
        # Small delay to ensure response processor is running
        await asyncio.sleep(0.1)
        
        # Send session start event
        session_start = {
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "topP": 0.9,
                        "temperature": 0.7
                    }
                }
            }
        }
        await self.send_event(session_start)
        
        # Build tool configuration if MCP tools are available
        tool_config = {}
        if self.mcp_tools:
            tools = self.mcp_tools.get_tool_definitions()
            if tools:
                # Convert MCP tool format to Nova Sonic format
                nova_tools = []
                for tool in tools:
                    nova_tool = {
                        "toolSpec": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "inputSchema": {
                                "json": tool["input_schema"]
                            }
                        }
                    }
                    nova_tools.append(nova_tool)
                
                tool_config = {
                    "toolUseOutputConfiguration": {
                        "mediaType": "application/json"
                    },
                    "toolConfiguration": {
                        "tools": nova_tools
                    }
                }
        
        # Send prompt start event
        prompt_start = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {
                        "mediaType": "text/plain"
                    },
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 16000,  # Match input rate
                        "sampleSizeBits": 16,
                        "channelCount": CHANNELS,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    },
                    **tool_config
                }
            }
        }
        await self.send_event(prompt_start)
        
        # Send system prompt if provided
        if system_prompt:
            content_name = str(uuid.uuid4())
            
            # Content start
            content_start = {
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "type": "TEXT",
                        "interactive": True,
                        "role": "SYSTEM",
                        "textInputConfiguration": {
                            "mediaType": "text/plain"
                        }
                    }
                }
            }
            await self.send_event(content_start)
            
            # Text input
            text_input = {
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "content": system_prompt
                    }
                }
            }
            await self.send_event(text_input)
            
            # Content end
            content_end = {
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": content_name
                    }
                }
            }
            await self.send_event(content_end)
        
        logger.info("Nova Sonic session started successfully")
    
    async def send_audio_chunk(self, audio_base64: str, content_name: str):
        """
        Send audio chunk to Nova Sonic and optionally to speaker
        
        Args:
            audio_base64: Base64 encoded audio
            content_name: Audio content stream name
        """
        if not self.is_active:
            return
        
        # Send to Nova Sonic
        audio_input = {
            "event": {
                "audioInput": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": audio_base64
                }
            }
        }
        await self.send_event(audio_input)
        
        # Also send to speaker if enabled (decode base64 first)
        if self.speaker:
            try:
                pcm_bytes = base64.b64decode(audio_base64)
                await self.speaker.play(pcm_bytes)
            except Exception as e:
                logger.error(f"Failed to play audio through speaker: {e}")
    
    async def process_and_send_pcm_chunk(
        self,
        pcm_base64: str,
        content_name: str
    ) -> bool:
        """
        Send PCM audio chunk to Nova Sonic
        
        Args:
            pcm_base64: Base64 encoded PCM audio from browser (16kHz, 16-bit, mono)
            content_name: Audio content stream name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Log first chunk for debugging
            if not hasattr(self, '_logged_first_chunk'):
                logger.info(f"First PCM chunk - length: {len(pcm_base64)}, preview: {pcm_base64[:50]}...")
                
                # Decode and check the raw bytes
                try:
                    pcm_bytes = base64.b64decode(pcm_base64)
                    logger.info(f"Decoded PCM bytes length: {len(pcm_bytes)}, first 20 bytes: {pcm_bytes[:20].hex()}")
                except Exception as e:
                    logger.error(f"Failed to decode base64: {e}")
                
                self._logged_first_chunk = True
            
            # PCM is already in the correct format, just send it
            await self.send_audio_chunk(pcm_base64, content_name)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send PCM audio chunk: {e}", exc_info=True)
            return False
    
    async def start_audio_content(self) -> str:
        """Start audio input content stream and background noise injection"""
        content_name = str(uuid.uuid4())
        
        content_start = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": INPUT_SAMPLE_RATE,
                        "sampleSizeBits": 16,
                        "channelCount": CHANNELS,
                        "audioType": "SPEECH",
                        "encoding": "base64"
                    }
                }
            }
        }
        await self.send_event(content_start)
        
        # Store active content name and start background noise injection
        self.active_content_name = content_name
        self.background_noise_task = asyncio.create_task(self._inject_background_noise())
        
        return content_name
    
    async def send_wav_file(self, wav_file_path: str, chunk_size: int = 4096, keep_listening: bool = True) -> str:
        """
        Send a WAV file to Nova Sonic
        
        Args:
            wav_file_path: Path to WAV file (16kHz, mono, 16-bit PCM)
            chunk_size: Number of samples per chunk
            keep_listening: If True, keeps background noise running after file is sent (default: True)
            
        Returns:
            content_name: The audio content stream name
        """
        from .utils_audio import load_wav_for_streaming, calculate_streaming_delay
        
        logger.info(f"Loading WAV file: {wav_file_path}")
        
        # Load and prepare WAV file for streaming
        base64_chunks, metadata = load_wav_for_streaming(wav_file_path, chunk_size)
        
        logger.info(
            f"WAV: {metadata['sample_rate']}Hz, {metadata['channels']}ch, "
            f"{metadata['sample_width_bits']}bit, {metadata['duration_seconds']:.2f}s"
        )
        
        # Start audio content stream
        content_name = await self.start_audio_content()
        logger.info(f"Started audio content stream: {content_name}")
        
        # Send audio chunks
        logger.info(f"Streaming {metadata['num_chunks']} chunks to Nova Sonic...")
        
        for i, chunk_base64 in enumerate(base64_chunks, 1):
            success = await self.process_and_send_pcm_chunk(chunk_base64, content_name)
            if not success:
                logger.error(f"Failed to send chunk {i}/{metadata['num_chunks']}")
                break
            
            # Small delay to simulate real-time streaming
            await asyncio.sleep(metadata['chunk_delay_seconds'])
        
        logger.info(f"Audio file sent completely")
        
        # Only end audio content if keep_listening is False
        # Otherwise, background noise keeps running to keep session alive for response
        if not keep_listening:
            await self.end_audio_content(content_name)
            logger.info(f"Audio streaming complete (session closed)")
        else:
            logger.info(f"Audio streaming complete (keeping session alive for response)")
        
        return content_name
    
    async def end_audio_content(self, content_name: str):
        """End audio input content stream and stop background noise injection"""
        # Stop background noise injection
        if self.background_noise_task and not self.background_noise_task.done():
            self.background_noise_task.cancel()
            try:
                await self.background_noise_task
            except asyncio.CancelledError:
                pass
        
        self.active_content_name = None
        self.background_noise_task = None
        
        # Send content end event
        content_end = {
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name
                }
            }
        }
        await self.send_event(content_end)
    
    async def end_session(self):
        """End the Nova Sonic session"""
        if not self.is_active:
            return
        
        logger.info("Ending Nova Sonic session")
        
        # Send prompt end
        prompt_end = {
            "event": {
                "promptEnd": {
                    "promptName": self.prompt_name
                }
            }
        }
        await self.send_event(prompt_end)
        
        # Send session end
        session_end = {
            "event": {
                "sessionEnd": {}
            }
        }
        await self.send_event(session_end)
        
        # Close the stream
        await self.stream.input_stream.close()
        self.is_active = False
        
        # Cleanup speaker
        if self.speaker:
            try:
                await self.speaker.stop_playback_worker()
                self.speaker.close()
                logger.info("Speaker closed")
            except Exception as e:
                logger.error(f"Error closing speaker: {e}")
        
        logger.info("Nova Sonic session ended")
    
    async def _process_responses(self):
        """Process responses from Nova Sonic"""

        n_audio = 0 

        logger.info("Response processor started")
        try:
            while self.is_active:
                logger.debug("Waiting for output...")
                output = await self.stream.await_output()
                result = await output[1].receive()
                
                logger.debug(f"Received result: has_value={result.value is not None}")
                
                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode('utf-8')
                    json_data = json.loads(response_data)
                    
                    # Log ALL events for debugging
                    if 'event' in json_data:
                        event_type = next(iter((json_data['event'].keys())))
                        
                        if event_type not in ['audioOutput', 'usageEvent']:
                            logger.info(f"⭐ Received: {event_type}")
                        
                        # Queue event for WebSocket forwarding
                        await self.event_queue.put(json_data)
                        
                        # Handle tool use events
                        if 'toolUse' in json_data['event']:
                            await self._handle_tool_use(json_data['event']['toolUse'])
                        
                        # Handle content start
                        elif 'contentStart' in json_data['event']:
                            role = json_data['event']['contentStart'].get('role')
                            logger.info(f"Content start {role}: {json_data['event']['contentStart'].get('type')}")
                            
                            # Check for speculative content
                            if 'additionalModelFields' in json_data['event']['contentStart']:
                                additional_fields = json.loads(
                                    json_data['event']['contentStart']['additionalModelFields']
                                )
            
                                logger.info(f"Speculative content: {additional_fields}")
                        
                        # Handle text output
                        elif 'textOutput' in json_data['event']:
                            text = json_data['event']['textOutput']['content']
                            role = json_data['event']['textOutput']['role']
                            
                            logger.info(f"⭐ {role}: {text[:100]}")
                            
                            # Check for barge-in signal
                            if '{ "interrupted" : true }' in text:
                                logger.info("Barge-in detected")
                            
        
                        
                        # Handle audio output
                        elif 'audioOutput' in json_data['event']:
                            audio_content = json_data['event']['audioOutput']['content']
                            audio_bytes = base64.b64decode(audio_content)
                            await self.audio_queue.put(audio_bytes)
                            n_audio += 1
                            if n_audio > 1000:
                                n_audio = 0
                                logger.info(f"⭐ Audio output: {n_audio} frames")
                            
                            # Send output audio to speaker
                            if self.speaker:
                                try:
                                    await self.speaker.play(audio_bytes)
                                    logger.debug(f"Output audio sent to speaker: {len(audio_bytes)} bytes")
                                except Exception as e:
                                    logger.error(f"Failed to play output audio through speaker: {e}")
                    else:
                        raise ValueError(f"⭐ Response without 'event' key: {list(json_data.keys())}")
        
        except StopAsyncIteration:
            logger.info("Response processor: Stream ended (StopAsyncIteration)")
        except Exception as e:
            logger.error(f"❌ Error processing Nova Sonic responses: {e}", exc_info=True)
        finally:
            logger.info("Response processor exiting")
    
    async def _inject_background_noise(self):
        """
        Periodically inject background noise to keep the session alive
        
        This sends small frames of silence/noise at regular intervals based on the
        sample rate to maintain the connection and ensure Nova Sonic continues processing.
        """
        # Generate a small frame of low-level background noise (silence)
        # 512 samples at 16kHz = 32ms of audio
        frame_size = 512
        silence_frame = base64.b64encode(b'\x00\x00' * frame_size).decode('utf-8')
        
        # Calculate sleep interval: frame duration in seconds
        # 512 samples / 16000 Hz = 0.032 seconds = 32ms
        sleep_interval = frame_size / INPUT_SAMPLE_RATE
        
        logger.info(
            f"Background noise injection started: "
            f"{frame_size} samples every {sleep_interval*1000:.1f}ms"
        )
        
        try:
            while self.is_active and self.active_content_name:
                await asyncio.sleep(sleep_interval)
                
                if self.is_active and self.active_content_name:
                    try:
                        await self.send_audio_chunk(silence_frame, self.active_content_name)
                        logger.debug(f"Injected background noise frame")
                    except Exception as e:
                        logger.error(f"Failed to inject background noise: {e}")
                        break
        
        except asyncio.CancelledError:
            logger.info("Background noise injection cancelled")
        except Exception as e:
            logger.error(f"Error in background noise injection: {e}", exc_info=True)
        finally:
            logger.info("Background noise injection stopped")
    
    async def _handle_tool_use(self, tool_use: Dict[str, Any]):
        """Handle tool execution requested by Nova Sonic"""
        if not self.mcp_tools:
            logger.warning("Tool use requested but no MCP tools available")
            return
        
        tool_name = tool_use['toolName']
        tool_use_id = tool_use['toolUseId']
        prompt_name = tool_use['promptName']
        tool_input = json.loads(tool_use['content'])
        tool_content_name = str(uuid.uuid4())
        
        logger.info(f"Executing tool: {tool_name}")
        
        try:
            # Send tool content start event
            tool_start = {
                "event": {
                    "contentStart": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name,
                        "type": "TOOL",
                        "role": "TOOL",
                        "interactive": False,
                        "toolResultInputConfiguration": {
                            "toolUseId": tool_use_id,
                            "type": "TEXT",
                            "textInputConfiguration": {
                                "mediaType": "text/plain"
                            }
                        }
                    }
                }
            }
            await self.send_event(tool_start)
            
            # Execute the tool
            result = self.mcp_tools.execute_tool(tool_name, tool_input)
            
            # Send tool result
            tool_result = {
                "event": {
                    "toolResult": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name,
                        "content": json.dumps(result)
                    }
                }
            }
            await self.send_event(tool_result)
            
            # Send tool content end
            tool_end = {
                "event": {
                    "contentEnd": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name
                    }
                }
            }
            await self.send_event(tool_end)
            
            logger.info(f"Tool {tool_name} executed successfully")
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            
            # Send error result
            error_result = {
                "event": {
                    "toolResult": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name,
                        "content": json.dumps({"error": str(e)})
                    }
                }
            }
            await self.send_event(error_result)
            
            # Send content end even on error
            tool_end = {
                "event": {
                    "contentEnd": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name
                    }
                }
            }
            await self.send_event(tool_end)
    
    async def get_audio_chunk(self) -> Optional[bytes]:
        """Get next audio chunk from the queue"""
        try:
            return await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    async def get_audio_chunk_as_wav(self) -> Optional[str]:
        """
        Get next audio chunk as WAV format (browser-compatible)
        
        Returns:
            Base64 encoded WAV audio or None
        """
        try:
            pcm_bytes = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
            
            if pcm_bytes:
                # Convert PCM to WAV for browser playback
                wav_bytes = self.audio_processor.pcm_to_wav(
                    pcm_bytes,
                    sample_rate=OUTPUT_SAMPLE_RATE,
                    channels=CHANNELS
                )
                
                # Encode to base64
                wav_base64 = base64.b64encode(wav_bytes).decode('utf-8')
                
                return wav_base64
            
            return None
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Failed to convert audio to WAV: {e}", exc_info=True)
            return None
    
    async def get_event(self) -> Optional[Dict[str, Any]]:
        """Get next event from the queue"""
        try:
            return await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
