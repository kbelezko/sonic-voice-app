'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  ConversationMessage,
  SonicEvent,
  VoiceButtonState,
  ConnectionStatus,
  WebSocketMessage
} from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/voice';

interface UseVoiceChatOptions {
  /** If provided, called with each base64 WAV chunk instead of the built-in
   *  AudioContext player. Use this to route audio to an external renderer
   *  (e.g. TalkingHead) so it plays exactly once and can drive lip-sync. */
  onAudio?: (audioBase64: string) => void;
}

export function useVoiceChat(options?: UseVoiceChatOptions) {
  // Keep the latest callback in a ref so the WebSocket handler never goes stale
  const onAudioRef = useRef(options?.onAudio);
  useEffect(() => { onAudioRef.current = options?.onAudio; }, [options?.onAudio]);

  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [sonicEvents, setSonicEvents] = useState<SonicEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [voiceButtonState, setVoiceButtonState] = useState<VoiceButtonState>('inactive');

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioWorkletNodeRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Separate context for playback — independent from the recording context
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef<number>(0);

  // ─── helpers ────────────────────────────────────────────────────────────────

  const addMessage = useCallback((role: 'user' | 'assistant' | 'system', content: string) => {
    const message: ConversationMessage = {
      role,
      content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  }, []);

  // Stop mic and audio graph without touching the WebSocket
  const teardownAudio = useCallback(() => {
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.disconnect();
      audioWorkletNodeRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
  }, []);

  // ─── audio playback ─────────────────────────────────────────────────────────

  const playAudioResponse = useCallback(async (audioBase64: string) => {
    try {
      const binaryString = atob(audioBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
        playbackContextRef.current = new AudioContext();
        nextPlayTimeRef.current = 0;
      }
      const ctx = playbackContextRef.current;
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }

      const audioBuffer = await ctx.decodeAudioData(bytes.buffer.slice(0));
      const startTime = Math.max(ctx.currentTime, nextPlayTimeRef.current);
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);
      source.start(startTime);
      nextPlayTimeRef.current = startTime + audioBuffer.duration;
    } catch (error) {
      console.error('Audio playback failed:', error);
    }
  }, []);

  // ─── WebSocket message handling ─────────────────────────────────────────────

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'transcription':
        if (message.is_final) {
          addMessage(message.role ?? 'user', message.text);
        }
        break;

      case 'assistant_text':
        addMessage('assistant', message.text);
        break;

      case 'assistant_voice':
        // Route to external renderer when available; fall back to built-in player
        if (onAudioRef.current) {
          onAudioRef.current(message.audio);
        } else {
          playAudioResponse(message.audio);
        }
        break;

      case 'tool_execution':
        if (message.status === 'executing') {
          addMessage('system', 'Searching for hotels...');
        }
        break;

      case 'sonic_event':
        setSonicEvents(prev => [...prev, {
          event_type: message.event_type,
          data: message.data,
          ts: new Date().toISOString()
        }]);
        break;

      case 'error':
        addMessage('system', `Error: ${message.message}`);
        setVoiceButtonState('inactive');
        break;
    }
  }, [addMessage, playAudioResponse]);

  // ─── PCM helpers ────────────────────────────────────────────────────────────

  const floatTo16BitPCM = useCallback((float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  }, []);

  const downsampleBuffer = useCallback((
    buffer: Float32Array<ArrayBuffer>,
    fromSampleRate: number,
    toSampleRate: number
  ): Float32Array<ArrayBuffer> => {
    if (fromSampleRate === toSampleRate) return buffer;

    const ratio = fromSampleRate / toSampleRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);

    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffset = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffset && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffset;
    }
    return result;
  }, []);

  const int16ToBase64 = useCallback((int16Array: Int16Array): string => {
    const uint8Array = new Uint8Array(int16Array.buffer);
    let binary = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
  }, []);

  // ─── session lifecycle ───────────────────────────────────────────────────────

  /**
   * Button ON — open a fresh WebSocket (which starts a new Nova Sonic session
   * on the backend) and begin streaming microphone audio.
   */
  const startVoiceSession = useCallback(async () => {
    try {
      setVoiceButtonState('processing');
      setMessages([]);
      setSonicEvents([]);

      // Request microphone access first so the user sees the permission prompt
      // before we open the WebSocket.
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      mediaStreamRef.current = stream;

      // Open a new WebSocket connection. Each connection triggers a fresh Nova
      // Sonic session on the backend.
      const sessionId = `session-${Date.now()}-${Math.random().toString(36).substring(7)}`;
      setConnectionStatus('connecting');

      await new Promise<void>((resolve, reject) => {
        const ws = new WebSocket(`${WS_URL}?session_id=${sessionId}`);

        ws.onopen = () => {
          setConnectionStatus('connected');
          resolve();
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            handleWebSocketMessage(message);
          } catch {
            console.error('Failed to parse WebSocket message');
          }
        };

        ws.onerror = () => {
          reject(new Error('WebSocket connection failed'));
        };

        // If the backend closes the connection unexpectedly, reset everything.
        ws.onclose = () => {
          setConnectionStatus('disconnected');
          setVoiceButtonState('inactive');
          wsRef.current = null;
          teardownAudio();
        };

        wsRef.current = ws;
      });

      // WebSocket is open — set up the audio capture pipeline.
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;

      const actualSampleRate = audioContext.sampleRate;
      const targetSampleRate = 16000;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      audioWorkletNodeRef.current = processor;

      processor.onaudioprocess = (audioEvent) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          let inputData = audioEvent.inputBuffer.getChannelData(0);
          if (actualSampleRate !== targetSampleRate) {
            inputData = downsampleBuffer(inputData, actualSampleRate, targetSampleRate);
          }
          const pcmData = floatTo16BitPCM(inputData);
          const base64 = int16ToBase64(pcmData);
          wsRef.current.send(JSON.stringify({
            type: 'audio_chunk',
            data: base64,
            format: 'pcm',
            sample_rate: targetSampleRate
          }));
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setVoiceButtonState('listening');
      wsRef.current?.send(JSON.stringify({ type: 'voice_start' }));

    } catch (error) {
      console.error('Failed to start voice session:', error);
      addMessage('system', 'Could not start session. Check microphone permissions and try again.');
      teardownAudio();
      if (wsRef.current) {
        wsRef.current.onclose = null; // don't trigger the handler on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnectionStatus('disconnected');
      setVoiceButtonState('inactive');
    }
  }, [handleWebSocketMessage, teardownAudio, addMessage, floatTo16BitPCM, int16ToBase64, downsampleBuffer]);

  /**
   * Button OFF — stop the mic, signal the backend, and close the WebSocket.
   * The backend tears down the Nova Sonic session when the connection closes.
   */
  const stopVoiceSession = useCallback(() => {
    // Stop mic and audio graph first so no more chunks are queued.
    teardownAudio();

    // Send voice_end so the backend can cleanly close the audio content stream
    // before we close the socket.
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'voice_end' }));
      // Don't let the onclose handler re-run teardownAudio — it's already done.
      wsRef.current.onclose = () => {
        setConnectionStatus('disconnected');
        wsRef.current = null;
      };
      wsRef.current.close();
    }
    wsRef.current = null;

    setVoiceButtonState('inactive');
    setConnectionStatus('disconnected');
  }, [teardownAudio]);

  const sendTextMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'text_input', text }));
      addMessage('user', text);
    }
  }, [addMessage]);

  // ─── cleanup on unmount ──────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      teardownAudio();
      if (wsRef.current) wsRef.current.close();
      if (playbackContextRef.current) playbackContextRef.current.close();
    };
  }, [teardownAudio]);

  return {
    messages,
    sonicEvents,
    connectionStatus,
    voiceButtonState,
    startVoiceSession,
    stopVoiceSession,
    sendTextMessage
  };
}
