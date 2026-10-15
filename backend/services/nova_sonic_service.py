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
from .utils_audio import check_audio_dependencies, pcm_to_wav_bytes
from .utils_speaker import AudioSpeaker, check_audio_playback_available

logger = logging.getLogger(__name__)

# Audio configuration for Nova Sonic
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 16000
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
        enable_speaker: bool = True,
        inject_background_noise: bool = False
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
        self.role: Optional[str] = None

        # Lock to serialise all stream.input_stream.send() calls — prevents
        # concurrent writes that produce malformed event blobs (ValidationException).
        self._send_lock = asyncio.Lock()

        # Background noise injection: keeps the audio stream alive during silent gaps.
        # Set True only for WAV file playback (test_sonic.py); the WebSocket path
        # from a live browser microphone sends a continuous stream and does not need it.
        self.inject_background_noise = inject_background_noise
        self.background_noise_task = None
        self.active_content_name = None

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

        transport = AWSCRTHTTPClient()

        config = await AsyncBedrockRuntimeConfig.resolve(
            region=self.region,
            aws_credentials_identity_resolver=credentials_resolver,
            transport=transport
        )
        self.client = AsyncBedrockRuntimeClient(config=config)
        logger.info(f"Nova Sonic client initialized for {self.region}")

    async def send_event(self, event: dict):
        """Send an event to the bidirectional stream (serialised via _send_lock)"""
        if not self.stream:
            raise RuntimeError("Stream not initialized")

        event_type = next(iter(event['event'].keys()))
        if event_type not in ['audioInput']:
            logger.info(f'Sending: {event_type}')

        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps(event).encode('utf-8'))
        )
        async with self._send_lock:
            await self.stream.input_stream.send(chunk)

    async def start_session(self, system_prompt: str = None):
        """Start a Nova Sonic session"""
        if not self.client:
            await self._initialize_client()

        if system_prompt is None:
            system_prompt = self.system_prompt

        logger.info(f"Starting Nova Sonic session with model {self.model_id}")

        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True

        # Start processing responses BEFORE sending any events
        asyncio.create_task(self._process_responses())

        # Small delay to ensure response processor is running
        await asyncio.sleep(0.1)

        # Session start
        await self.send_event({
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "topP": 0.9,
                        "temperature": 0.7
                    }
                }
            }
        })

        # Build tool configuration if MCP tools are available
        tool_config = {}
        if self.mcp_tools:
            tools = self.mcp_tools.get_tool_definitions()
            if tools:
                nova_tools = [
                    {
                        "toolSpec": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "inputSchema": {"json": tool["input_schema"]}
                        }
                    }
                    for tool in tools
                ]
                tool_config = {
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": {"tools": nova_tools}
                }

        # Prompt start
        await self.send_event({
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 16000,
                        "sampleSizeBits": 16,
                        "channelCount": CHANNELS,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    },
                    **tool_config
                }
            }
        })

        # System prompt
        if system_prompt:
            content_name = str(uuid.uuid4())

            await self.send_event({
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "type": "TEXT",
                        "interactive": True,
                        "role": "SYSTEM",
                        "textInputConfiguration": {"mediaType": "text/plain"}
                    }
                }
            })

            await self.send_event({
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "content": system_prompt
                    }
                }
            })

            await self.send_event({
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": content_name
                    }
                }
            })

        logger.info("Nova Sonic session started successfully")

    async def start_audio_content(self) -> str:
        """Start audio input content stream and return content_name"""
        content_name = str(uuid.uuid4())

        await self.send_event({
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
        })

        # Conditionally start background noise injection (WAV playback only).
        if self.inject_background_noise:
            self.active_content_name = content_name
            self.background_noise_task = asyncio.create_task(
                self._inject_background_noise()
            )

        return content_name

    async def send_audio_chunk(self, audio_base64: str, content_name: str):
        """Send a single base64-encoded PCM audio chunk to Nova Sonic"""
        if not self.is_active:
            return

        await self.send_event({
            "event": {
                "audioInput": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": audio_base64
                }
            }
        })

        # Echo to speaker if enabled (local playback of user mic)
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
        Send a base64-encoded PCM chunk (16kHz, 16-bit, mono) to Nova Sonic.

        Args:
            pcm_base64: Base64 encoded PCM audio from browser
            content_name: Audio content stream name

        Returns:
            True if successful, False otherwise
        """
        try:
            if not hasattr(self, '_logged_first_chunk'):
                logger.info(
                    f"First PCM chunk — length: {len(pcm_base64)}, "
                    f"preview: {pcm_base64[:50]}..."
                )
                try:
                    pcm_bytes = base64.b64decode(pcm_base64)
                    logger.info(
                        f"Decoded PCM bytes: {len(pcm_bytes)} bytes, "
                        f"first 20: {pcm_bytes[:20].hex()}"
                    )
                except Exception as e:
                    logger.error(f"Failed to decode base64: {e}")
                self._logged_first_chunk = True

            await self.send_audio_chunk(pcm_base64, content_name)
            return True

        except Exception as e:
            logger.error(f"Failed to send PCM audio chunk: {e}", exc_info=True)
            return False

    async def end_audio_content(self, content_name: str):
        """End audio input content stream"""
        # Cancel background noise injection if running.
        if self.background_noise_task and not self.background_noise_task.done():
            self.background_noise_task.cancel()
            try:
                await self.background_noise_task
            except asyncio.CancelledError:
                pass

        self.background_noise_task = None
        self.active_content_name = None

        await self.send_event({
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name
                }
            }
        })

    async def send_wav_file(self, wav_file_path: str, chunk_size: int = 4096) -> str:
        """
        Send a WAV file to Nova Sonic (used by test_sonic.py).

        Args:
            wav_file_path: Path to WAV file (16kHz, mono, 16-bit PCM)
            chunk_size: Number of samples per chunk

        Returns:
            content_name: The audio content stream name
        """
        from .utils_audio import load_wav_for_streaming

        logger.info(f"Loading WAV file: {wav_file_path}")

        base64_chunks, metadata = load_wav_for_streaming(wav_file_path, chunk_size)

        logger.info(
            f"WAV: {metadata['sample_rate']}Hz, {metadata['channels']}ch, "
            f"{metadata['sample_width_bits']}bit, {metadata['duration_seconds']:.2f}s"
        )

        content_name = await self.start_audio_content()
        logger.info(f"Started audio content stream: {content_name}")

        logger.info(f"Streaming {metadata['num_chunks']} chunks to Nova Sonic...")
        for i, chunk_base64 in enumerate(base64_chunks, 1):
            success = await self.process_and_send_pcm_chunk(chunk_base64, content_name)
            if not success:
                logger.error(f"Failed to send chunk {i}/{metadata['num_chunks']}")
                break
            await asyncio.sleep(metadata['chunk_delay_seconds'])

        await self.end_audio_content(content_name)
        logger.info("Audio streaming complete")

        return content_name

    async def end_session(self):
        """End the Nova Sonic session"""
        if not self.is_active:
            return

        logger.info("Ending Nova Sonic session")

        await self.send_event({
            "event": {
                "promptEnd": {"promptName": self.prompt_name}
            }
        })

        await self.send_event({
            "event": {"sessionEnd": {}}
        })

        await self.stream.input_stream.close()
        self.is_active = False

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

                    if 'event' in json_data:
                        event_type = next(iter(json_data['event'].keys()))

                        if event_type not in ['audioOutput', 'usageEvent']:
                            logger.info(f"⭐ Received: {event_type}")

                        # Queue event for WebSocket forwarding
                        await self.event_queue.put(json_data)

                        if 'toolUse' in json_data['event']:
                            await self._handle_tool_use(json_data['event']['toolUse'])

                        elif 'contentStart' in json_data['event']:
                            role = json_data['event']['contentStart'].get('role')
                            if role:
                                self.role = role
                            logger.info(
                                f"Content start {role}: "
                                f"{json_data['event']['contentStart'].get('type')}"
                            )

                            if 'additionalModelFields' in json_data['event']['contentStart']:
                                additional_fields = json.loads(
                                    json_data['event']['contentStart']['additionalModelFields']
                                )
                                logger.info(f"Speculative content: {additional_fields}")

                        elif 'textOutput' in json_data['event']:
                            text = json_data['event']['textOutput']['content']
                            role = json_data['event']['textOutput']['role']
                            logger.info(f"⭐ {role}: {text[:100]}")

                            if '{ "interrupted" : true }' in text:
                                logger.info("Barge-in detected")

                        elif 'audioOutput' in json_data['event']:
                            audio_content = json_data['event']['audioOutput']['content']
                            audio_bytes = base64.b64decode(audio_content)
                            await self.audio_queue.put(audio_bytes)
                            n_audio += 1
                            if n_audio % 1000 == 0:
                                logger.info(f"⭐ Audio output: {n_audio} frames")

                            if self.speaker:
                                try:
                                    await self.speaker.play(audio_bytes)
                                    logger.debug(f"Output audio sent to speaker: {len(audio_bytes)} bytes")
                                except Exception as e:
                                    logger.error(f"Failed to play output audio through speaker: {e}")
                    else:
                        raise ValueError(f"Response without 'event' key: {list(json_data.keys())}")

        except StopAsyncIteration:
            logger.info("Response processor: Stream ended (StopAsyncIteration)")
        except Exception as e:
            logger.error(f"❌ Error processing Nova Sonic responses: {e}", exc_info=True)
        finally:
            logger.info("Response processor exiting")

    async def _inject_background_noise(self):
        """
        Periodically inject silence to keep the audio stream alive during gaps.

        Used only when inject_background_noise=True (WAV file playback in test_sonic.py).
        The browser microphone sends a continuous stream so this is not needed there.
        All sends go through send_event() → _send_lock, so they cannot race with
        real audio sends.
        """
        frame_size = 512
        silence_frame = base64.b64encode(b'\x00\x00' * frame_size).decode('utf-8')
        sleep_interval = frame_size / INPUT_SAMPLE_RATE  # ~32 ms

        logger.info(
            f"Background noise injection started: "
            f"{frame_size} samples every {sleep_interval * 1000:.1f}ms"
        )

        try:
            while self.is_active and self.active_content_name:
                await asyncio.sleep(sleep_interval)

                if self.is_active and self.active_content_name:
                    try:
                        await self.send_audio_chunk(silence_frame, self.active_content_name)
                        logger.debug("Injected background noise frame")
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
            # contentStart TOOL
            await self.send_event({
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
                            "textInputConfiguration": {"mediaType": "text/plain"}
                        }
                    }
                }
            })

            result = self.mcp_tools.execute_tool(tool_name, tool_input)

            # toolResult
            await self.send_event({
                "event": {
                    "toolResult": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name,
                        "content": json.dumps(result)
                    }
                }
            })

            # contentEnd — ONLY promptName + contentName
            await self.send_event({
                "event": {
                    "contentEnd": {
                        "promptName": prompt_name,
                        "contentName": tool_content_name
                    }
                }
            })

            logger.info(f"Tool {tool_name} executed successfully")

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)

            # Send error result then close the content block cleanly
            try:
                await self.send_event({
                    "event": {
                        "toolResult": {
                            "promptName": prompt_name,
                            "contentName": tool_content_name,
                            "content": json.dumps({"error": str(e)})
                        }
                    }
                })

                await self.send_event({
                    "event": {
                        "contentEnd": {
                            "promptName": prompt_name,
                            "contentName": tool_content_name
                        }
                    }
                })
            except Exception as inner_e:
                logger.error(f"Error sending tool error response: {inner_e}", exc_info=True)

    async def get_audio_chunk(self) -> Optional[bytes]:
        """Get next raw PCM audio chunk from the queue"""
        try:
            return await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def get_audio_chunk_as_wav(self) -> Optional[str]:
        """
        Get next audio chunk as WAV format (browser-compatible).

        Returns:
            Base64 encoded WAV audio, or None if no audio available.
        """
        try:
            pcm_bytes = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)

            if pcm_bytes:
                wav_bytes = pcm_to_wav_bytes(
                    pcm_bytes,
                    sample_rate=OUTPUT_SAMPLE_RATE,
                    channels=CHANNELS
                )
                return base64.b64encode(wav_bytes).decode('utf-8')

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
